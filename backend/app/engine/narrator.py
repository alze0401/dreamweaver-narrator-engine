"""
织梦绮谭 - 叙事引擎 (调度中心)

Narrator 是整个引擎的核心调度器，负责：
  1. 开始新游戏（初始化会话、加载模板、生成开场）
  2. 推进剧情（组装上下文 → LangGraph 工作流 → 更新状态）
  3. 协调 PromptBuilder、LLM (LangChain)、记忆系统、好感度系统

LLM 交互通过 LangGraph 工作流编排（见 narrator_graph.py），
底层使用 LangChain ChatOpenAI 调用 DeepSeek API。
"""

import json
import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.config import get_settings
from app.models import (
    GameSession, DialogueLog, AffectionState,
    PlayerProfile,
)
from app.models.template_models import Template
from app.engine.affection import AffectionCalculator
from app.engine.memory import memory_manager
from app.engine.narrator_graph import run_narration
from app.cache import cache


class Narrator:
    """
    叙事引擎 —— Galgame 的心脏。

    每次玩家做出选择或输入文字时，Narrator 负责：
      1. 收集所有上下文（世界/角色/记忆/场景）
      2. 通过 PromptBuilder 组装 System Prompt
      3. 调用 LLM 生成响应
      4. 用 ResponseParser 解析结构化输出
      5. 更新游戏状态（好感度、记忆、对话记录）
      6. 返回前端可渲染的数据
    """

    def __init__(self):
        """初始化叙事引擎及其子模块"""
        self._settings = get_settings()
        self._affection_calc = AffectionCalculator()

        logger.info("📖 Narrator 叙事引擎已初始化")

    # =================================================================
    #  开始新游戏
    # =================================================================

    async def start_game(
        self,
        db: AsyncSession,
        world_template_id: str,
        scenario_template_id: str,
        player_name: str,
        player_data: dict,
        character_template_ids: list[str],
        user_id: str | None = None,
    ) -> dict:
        """
        开始一局新游戏。

        流程:
          1. 创建 GameSession 记录
          2. 加载世界观和剧本模板
          3. 初始化角色好感度
          4. 创建玩家画像
          5. 生成开场叙事

        Args:
            db: 数据库会话
            world_template_id: 世界观模板ID
            scenario_template_id: 剧本模板ID
            player_name: 玩家角色名
            player_data: 玩家自定义信息
            character_template_ids: 启用的角色模板ID列表

        Returns:
            包含 session_id 和开场内容的字典
        """
        logger.info(f"🎮 开始新游戏: player={player_name}, world={world_template_id}")

        # ---- 1. 加载模板数据（从 MySQL） ----
        world_data = await self._load_template_from_db(db, world_template_id)
        scenario_data = await self._load_template_from_db(db, scenario_template_id)

        # ---- 2. 创建游戏会话 ----
        session = GameSession(
            user_id=user_id,
            world_template_id=world_template_id,
            scenario_template_id=scenario_template_id,
            player_name=player_name,
            player_data=player_data,
            chapter=1,
            current_scene=scenario_data.get("scenario", {}).get(
                "opening_scene", {}
            ).get("location", "未知地点"),
            world_state={
                "location": scenario_data.get("scenario", {}).get(
                    "opening_scene", {}
                ).get("location", ""),
                "time": scenario_data.get("scenario", {}).get(
                    "opening_scene", {}
                ).get("time", ""),
                "weather": scenario_data.get("scenario", {}).get(
                    "opening_scene", {}
                ).get("weather", ""),
                "global_flags": {},
            },
        )
        db.add(session)
        await db.flush()

        # ---- 3. 初始化角色好感度 ----
        character_contexts = []
        for char_id in character_template_ids:
            char_data = await self._load_template_from_db(db, char_id)
            if char_data:
                char_info = char_data.get("character", {})
                aff_config = char_data.get("affection_config", {})
                char_name = self._extract_canonical_name(
                    char_info.get("full_name", char_data.get("name", ""))
                )
                # 如果模板没有名字，使用占位符（AI 将在叙事中根据世界观生成合适的名字）
                if not char_name or char_name == "未知":
                    char_name = "某位角色"

                affection = AffectionState(
                    session_id=session.id,
                    character_id=char_id,
                    character_name=char_name,
                    intimacy=aff_config.get("initial_value", 0),
                    trust=aff_config.get("initial_value", 0),
                    respect=aff_config.get("initial_value", 0),
                    curiosity=aff_config.get("initial_value", 0),
                    fear=0,
                    current_rank="陌生",
                    relationship_label="陌生人",
                )
                db.add(affection)
                character_contexts.append(self._build_character_context(char_data, affection))

        # ---- 4. 创建玩家画像 ----
        profile = PlayerProfile(
            session_id=session.id,
            name=player_name,
            age=player_data.get("age", ""),
            background=player_data.get("background", ""),
        )
        db.add(profile)
        await db.flush()

        # ---- 5. 生成开场叙事 ----
        opening = await self._generate_narration(
            db=db,
            session=session,
            world_data=world_data,
            scenario_data=scenario_data,
            character_contexts=character_contexts,
            player_profile=profile,
            player_input=None,  # 开场无玩家输入
        )

        # ---- 5.5 将开场叙事写入对话历史（关键：确保后续轮次 LLM 能看到开场内容） ----
        opening_content = json.dumps(opening, ensure_ascii=False)
        opening_log = DialogueLog(
            session_id=session.id,
            turn_number=0,
            speaker="narrator",
            content=opening_content,
            choices_offered=opening.get("choices", []),
            metadata_json={
                "scene_state": opening.get("scene_state", {}),
                "affection_changes": opening.get("affection_changes", []),
            },
        )
        db.add(opening_log)

        # 同步更新场景状态
        opening_scene_state = opening.get("scene_state", {}) or {}
        if opening_scene_state.get("location"):
            session.current_scene = opening_scene_state["location"]
            session.world_state["location"] = opening_scene_state["location"]
        if opening_scene_state.get("time"):
            session.world_state["time"] = opening_scene_state["time"]

        # 确保 scene_state 始终包含 location（兜底到模板中的 opening_scene 或 current_scene）
        merged_opening_scene = {
            "location": opening_scene_state.get("location") or session.current_scene or "",
            "time": opening_scene_state.get("time") or session.world_state.get("time") or "",
            "mood": opening_scene_state.get("mood") or "",
        }

        session.total_turns = 1

        await db.flush()

        logger.info(f"✅ 游戏已创建: session_id={session.id}")

        # 获取最新的角色列表
        updated_chars = await self._get_character_summaries(db, session.id)

        return {
            "session_id": session.id,
            "opening_narration": opening.get("narration", ""),
            "opening_dialogues": opening.get("dialogues", []),
            "choices": opening.get("choices", []),
            "scene_state": merged_opening_scene,
            "updated_characters": updated_chars,
            "progress": {
                "chapter": 1,
                "total_chapters": scenario_data.get("scenario", {}).get("estimated_chapters", 5),
                "current_turn": 0,
            },
        }

    # =================================================================
    #  推进剧情
    # =================================================================

    async def advance(
        self,
        db: AsyncSession,
        session_id: str,
        input_type: str,
        content: str,
    ) -> dict:
        """
        推进一轮对话/剧情。

        流程:
          1. 记录玩家输入
          2. 收集所有上下文
          3. 构建 System Prompt + User Message
          4. 调用 LLM
          5. 解析响应
          6. 更新好感度
          7. 更新场景状态
          8. 返回结果

        Args:
            db: 数据库会话
            session_id: 游戏会话ID
            input_type: "choice" 或 "free"
            content: 选项ID 或 自由输入文本

        Returns:
            结构化的对话响应字典
        """
        # ---- 1. 获取游戏会话 ----
        session = await self._get_session(db, session_id)

        # ---- 2. 记录玩家输入到对话历史 ----
        current_turn = await self._get_next_turn(db, session_id)

        player_log = DialogueLog(
            session_id=session_id,
            turn_number=current_turn,
            speaker="player",
            content=content,
            input_type=input_type,
        )
        db.add(player_log)
        await db.flush()

        # ---- 3. 收集上下文 ----
        world_data = await self._load_template_from_db(db, session.world_template_id)
        scenario_data = await self._load_template_from_db(db, session.scenario_template_id)

        # 获取角色好感度状态
        character_contexts = await self._get_character_contexts(db, session_id)

        # 获取玩家画像
        profile = await self._get_player_profile(db, session_id)

        # 获取记忆上下文
        memory_ctx = await memory_manager.build_memory_context(
            db, session_id, session.chapter, content
        )

        # ---- 4. 构建 Prompt 并调用 LLM ----
        result = await self._generate_narration(
            db=db,
            session=session,
            world_data=world_data,
            scenario_data=scenario_data,
            character_contexts=character_contexts,
            player_profile=profile,
            player_input=content,
            memory_context=memory_ctx,
        )

        # ---- 5. 记录 AI 响应到对话历史 ----
        ai_content = json.dumps(result, ensure_ascii=False)
        ai_log = DialogueLog(
            session_id=session_id,
            turn_number=current_turn + 1,
            speaker="narrator",
            content=ai_content,
            choices_offered=result.get("choices", []),
            metadata_json={
                "scene_state": result.get("scene_state", {}),
                "affection_changes": result.get("affection_changes", []),
            },
        )
        db.add(ai_log)

        # ---- 6. 更新好感度 ----
        affection_changes = result.get("affection_changes", [])
        if affection_changes:
            await self._apply_affection_changes(db, session_id, affection_changes)

        # ---- 7. 更新场景状态 ----
        scene_state = result.get("scene_state", {}) or {}
        if scene_state:
            session.current_scene = scene_state.get("location", session.current_scene)
            if scene_state.get("location"):
                session.world_state["location"] = scene_state["location"]
            if scene_state.get("time"):
                session.world_state["time"] = scene_state["time"]

        # 确保返回的 scene_state 始终包含 session 中已存储的 location/time（兜底）
        merged_scene_state = {
            "location": scene_state.get("location") or session.world_state.get("location") or session.current_scene or "",
            "time": scene_state.get("time") or session.world_state.get("time") or "",
            "mood": scene_state.get("mood") or "",
        }

        # 章节推进：根据剧情发展自动推进章节
        total_turns = current_turn + 1
        chapter_beats = scenario_data.get("scenario", {}).get("chapter_beats", [])
        total_chapters_est = scenario_data.get("scenario", {}).get("estimated_chapters", 5)
        # 每 6-8 轮对话推进一章（如果有章节节拍则按节拍推进）
        turns_per_chapter = max(6, total_turns // max(total_chapters_est, 1))
        if chapter_beats and session.chapter < total_chapters_est:
            # 检查是否达到章节推进条件
            beat_idx = session.chapter - 1  # 当前章节对应的 beat 索引
            if beat_idx < len(chapter_beats):
                beat = chapter_beats[beat_idx]
                trigger_turn = beat.get("trigger_turn", beat_idx * turns_per_chapter + 1)
                if current_turn >= trigger_turn:
                    session.chapter = min(session.chapter + 1, total_chapters_est)
                    logger.info(f"📖 章节推进 → 第{session.chapter}章: {beat.get('title', '')}")
        elif total_turns > 0 and total_turns % turns_per_chapter == 0 and session.chapter < total_chapters_est:
            session.chapter += 1
            logger.info(f"📖 章节自动推进 → 第{session.chapter}章")

        # 更新对话轮次计数
        session.total_turns = current_turn + 1

        await db.flush()

        # ---- 8. 获取最新的角色列表（含好感度变化和名字揭示后的更新） ----
        updated_chars = await self._get_character_summaries(db, session_id)

        logger.info(f"📖 剧情推进完成: session={session_id[:8]} turn={current_turn}")

        return {
            "narration": result.get("narration", ""),
            "dialogues": result.get("dialogues", []),
            "choices": result.get("choices", []),
            "scene_state": merged_scene_state,
            "affection_changes": result.get("affection_changes", []),
            "updated_characters": updated_chars,
            "progress": {
                "chapter": session.chapter,
                "total_chapters": total_chapters_est,
                "current_turn": current_turn + 1,
            },
        }

    # =================================================================
    #  内部方法
    # =================================================================

    async def _generate_narration(
        self,
        db: AsyncSession,
        session: GameSession,
        world_data: dict,
        scenario_data: dict,
        character_contexts: list[dict],
        player_profile: PlayerProfile | None,
        player_input: str | None,
        memory_context: dict | None = None,
    ) -> dict:
        """
        生成一段叙事（开场或推进都用这个方法）。

        通过 LangGraph 工作流执行:
          build_prompt → call_llm → parse_response
        """
        # 构建世界观上下文
        world_ctx = self._build_world_context(world_data, session)

        # 构建场景上下文
        scene_ctx = self._build_scene_context(scenario_data, session)

        # 构建记忆上下文
        if memory_context is None:
            memory_context = {
                "recent_dialogues": [],
                "scene_summaries": [],
                "key_facts": [],
            }

        # 构建玩家画像上下文
        player_ctx = {}
        if player_profile:
            player_ctx = {
                "name": player_profile.name,
                "age": player_profile.age,
                "background": player_profile.background,
                "traits": player_profile.observed_traits,
                "play_style": player_profile.play_style,
            }

        # 构建近期叙事摘要（防重复用）
        recent_narration_summary = self._build_recent_narration_summary(
            memory_context
        )

        # ---- 通过 LangGraph 工作流执行叙事生成 ----
        result = await run_narration(
            world_data=world_data,
            scenario_data=scenario_data,
            character_contexts=character_contexts,
            player_profile=player_profile,
            player_input=player_input,
            memory_context=memory_context,
            session=session,
            db=db,
            world_ctx=world_ctx,
            scene_ctx=scene_ctx,
            player_ctx=player_ctx,
            recent_narration_summary=recent_narration_summary,
        )

        return result

    def _build_recent_narration_summary(self, memory_context: dict) -> str:
        """
        从近期对话和场景摘要中构建一份"已发生内容"摘要。
        
        这份摘要会嵌入 System Prompt，帮助 LLM 避免重复描写。
        只提取关键叙事元素（动作、场景描写、情感表达），不保留完整对话。
        """
        parts = []

        # 从场景摘要中提取
        for summary in memory_context.get("scene_summaries", [])[:3]:
            scene_name = summary.get("scene_name", "")
            text = summary.get("summary", "")
            if text:
                parts.append(f"- 【{scene_name}】{text[:120]}")

        # 从最近对话中提取 AI 叙事部分（截取关键描写）
        recent = memory_context.get("recent_dialogues", [])
        narrator_turns = [
            d for d in recent
            if d.get("speaker") == "narrator"
        ]
        for turn in narrator_turns[-4:]:
            content = turn.get("content", "")
            # 截取前 150 字符作为叙事回顾
            if content:
                # 尝试提取 narration 字段
                try:
                    data = json.loads(content)
                    narration = data.get("narration", "")
                    dialogues = data.get("dialogues", [])
                    if narration:
                        parts.append(f"- 叙事: {narration[:100]}...")
                    for d in dialogues[:2]:
                        speaker = d.get("speaker", "")
                        text = d.get("text", "")
                        if speaker and text:
                            parts.append(f"- {speaker}说: {text[:60]}...")
                except (json.JSONDecodeError, TypeError):
                    parts.append(f"- 对话: {content[:100]}...")

        if not parts:
            return ""

        return "\n".join(parts[:12])  # 最多 12 条，控制 prompt 长度

    def _load_template(self, template_type: str, template_id: str) -> dict:
        """
        从文件系统加载 JSON 模板（同步降级方案）。

        仅作为 MySQL 加载失败时的后备。
        主加载路径请使用 async _load_template_from_db()。
        """
        templates_dir = self._settings.prompts_dir.parent / "templates" / template_type
        filepath = templates_dir / f"{template_id}.json"
        if filepath.exists():
            return json.loads(filepath.read_text(encoding="utf-8"))

        if templates_dir.exists():
            for f in templates_dir.glob("*.json"):
                try:
                    data = json.loads(f.read_text(encoding="utf-8"))
                    if data.get("template_id") == template_id:
                        return data
                except Exception:
                    continue

        logger.warning(f"模板未找到（文件系统降级）: {template_type}/{template_id}")
        return {}

    async def _load_template_from_db(
        self, db: AsyncSession, template_id: str
    ) -> dict:
        """
        从 MySQL 加载模板数据，优先使用 Redis 缓存。

        Template 表的 data 列（JSON）存储了模板的全部业务字段
        （如 world / character / scenario 的配置），直接返回给叙事引擎。

        Args:
            db: 数据库会话
            template_id: 模板唯一标识

        Returns:
            模板业务数据字典；未找到时回退到文件系统
        """
        # ---- 1. 尝试 Redis 缓存 ----
        try:
            cached = await cache.get_template(template_id)
            if cached is not None:
                logger.debug(f"模板缓存命中: {template_id}")
                return cached
        except Exception:
            pass  # Redis 不可用时静默跳过

        # ---- 2. 查询 MySQL ----
        stmt = select(Template).where(Template.template_id == template_id)
        result = await db.execute(stmt)
        template = result.scalar_one_or_none()

        if template is not None:
            # data 列是 JSON，存储了模板的所有业务字段
            data = template.data if isinstance(template.data, dict) else {}

            # 补充顶层字段，保证向后兼容
            data.setdefault("template_id", template.template_id)
            data.setdefault("name", template.name)
            data.setdefault("template_type", template.template_type)

            # 写入 Redis 缓存（容错）
            try:
                await cache.cache_template(template_id, data)
            except Exception:
                pass
            return data

        # ---- 3. 降级到文件系统 ----
        logger.warning(f"模板未在 MySQL 中找到，降级到文件系统: {template_id}")
        template_type_guess = "characters"  # 默认
        if "world" in template_id:
            template_type_guess = "worlds"
        elif "scenario" in template_id or "storm" in template_id or "intrigue" in template_id or "path" in template_id:
            template_type_guess = "scenarios"
        return self._load_template(template_type_guess, template_id)

    def _build_world_context(self, world_data: dict, session: GameSession) -> dict:
        """从模板和会话状态构建世界观上下文"""
        world = world_data.get("world", {})
        return {
            "name": world_data.get("name", "未知世界"),
            "era": world.get("era", ""),
            "genre": world.get("genre", []),
            "description": world.get("setting_description", ""),
            "rules": world.get("rules", []),
            "current_location": session.world_state.get("location", ""),
            "current_time": session.world_state.get("time", ""),
        }

    def _build_scene_context(self, scenario_data: dict, session: GameSession) -> dict:
        """从模板和会话状态构建场景上下文"""
        scenario = scenario_data.get("scenario", {})
        opening = scenario.get("opening_scene", {})

        # 构建章节节拍指引（告诉 LLM 当前章节应该发生什么）
        chapter_beats = scenario.get("chapter_beats", [])
        current_chapter_guide = ""
        if chapter_beats and session.chapter - 1 < len(chapter_beats):
            beat = chapter_beats[session.chapter - 1]
            current_chapter_guide = (
                f"当前是第{session.chapter}章「{beat.get('title', '')}」—— "
                f"{beat.get('description', '')} "
                f"关键事件: {', '.join(beat.get('key_events', []))}"
            )
        elif session.chapter > 1:
            # 超出预定义节拍时，基于章节数给出通用指引
            total_est = scenario.get("estimated_chapters", 5)
            ratio = session.chapter / max(total_est, 1)
            if ratio < 0.4:
                current_chapter_guide = "故事仍在铺垫阶段，应加深角色关系、埋设伏笔、揭示世界秘密。"
            elif ratio < 0.7:
                current_chapter_guide = "故事进入发展阶段，应出现冲突升级、角色秘密揭露、关键抉择。"
            else:
                current_chapter_guide = "故事接近高潮/结局，应收束伏笔、爆发核心冲突、呈现角色成长。"

        return {
            "premise": scenario.get("premise", ""),
            "location": session.current_scene or opening.get("location", ""),
            "chapter": session.chapter,
            "total_chapters": scenario.get("estimated_chapters", 5),
            "plot_hooks": scenario.get("plot_hooks", []),
            "key_choices_theme": scenario.get("key_choices_theme", []),
            "chapter_guide": current_chapter_guide,
        }

    @staticmethod
    def _extract_canonical_name(full_name: str) -> str:
        """
        从 full_name 字段中提取规范角色名。

        模板中的 full_name 可能是:
          - "自定义 (参考: 高宫凛 / 白雪·克劳蒂亚 / 莉娜·冯·艾尔斯坦)"  → 取第一个 "高宫凛"
          - "雪之下冰华"  → 直接返回
        """
        if not full_name:
            return "未知"
        # 匹配 "自定义 (参考: X / Y / Z)" 格式
        match = re.match(r"自定义\s*[\(（]\s*参考[：:]\s*([^/\)）]+)", full_name)
        if match:
            return match.group(1).strip()
        # 否则直接返回原名
        return full_name.strip()

    def _build_character_context(
        self, char_data: dict, affection: AffectionState
    ) -> dict:
        """从模板和好感度状态构建角色上下文"""
        char = char_data.get("character", {})
        personality = char.get("personality", {})
        relationships = char.get("relationships", {})

        return {
            "name": affection.character_name,
            "personality_summary": personality.get("archetype", ""),
            "mbti": personality.get("mbti", ""),
            "likes": personality.get("likes", []),
            "dislikes": personality.get("dislikes", []),
            "speech_style": personality.get("speech_style", {}).get("tone", ""),
            "attitude_towards_player": affection.current_rank,
            "affection_summary": (
                f"亲密度:{affection.intimacy:.0f} "
                f"信任:{affection.trust:.0f} "
                f"尊重:{affection.respect:.0f} "
                f"好奇:{affection.curiosity:.0f}"
            ),
            "relationships": relationships,
            "scene_presence": "active",
            "known_player_info": [],
        }

    async def _get_character_summaries(
        self, db: AsyncSession, session_id: str
    ) -> list[dict]:
        """
        获取会话中所有角色的摘要信息（含最新好感度数据和头像 URL）。
        用于返回给前端刷新角色面板和雷达图。
        """
        stmt = select(AffectionState).where(AffectionState.session_id == session_id)
        result = await db.execute(stmt)
        affections = result.scalars().all()

        # 批量查询 Template 表获取 avatar_url
        char_ids = [aff.character_id for aff in affections]
        avatar_map: dict[str, str | None] = {}
        if char_ids:
            tpl_stmt = select(Template.template_id, Template.avatar_url).where(
                Template.template_id.in_(char_ids)
            )
            tpl_result = await db.execute(tpl_stmt)
            avatar_map = {row.template_id: row.avatar_url for row in tpl_result.all()}

        return [
            {
                "character_id": aff.character_id,
                "character_name": aff.character_name,
                "current_rank": aff.current_rank,
                "relationship_label": aff.relationship_label,
                "overall_score": aff.overall_score,
                "intimacy": aff.intimacy,
                "trust": aff.trust,
                "respect": aff.respect,
                "curiosity": aff.curiosity,
                "fear": aff.fear,
                "avatar_url": avatar_map.get(aff.character_id),
            }
            for aff in affections
        ]

    async def _get_session(self, db: AsyncSession, session_id: str) -> GameSession:
        """获取游戏会话，不存在则抛异常"""
        stmt = select(GameSession).where(GameSession.id == session_id)
        result = await db.execute(stmt)
        session = result.scalar_one_or_none()
        if session is None:
            raise ValueError(f"游戏会话不存在: {session_id}")
        return session

    async def _get_next_turn(self, db: AsyncSession, session_id: str) -> int:
        """获取下一个对话轮次编号"""
        stmt = (
            select(DialogueLog.turn_number)
            .where(DialogueLog.session_id == session_id)
            .order_by(DialogueLog.turn_number.desc())
            .limit(1)
        )
        result = await db.execute(stmt)
        last_turn = result.scalar_one_or_none()
        return (last_turn or 0) + 1

    async def _get_character_contexts(
        self, db: AsyncSession, session_id: str
    ) -> list[dict]:
        """获取当前会话所有角色的上下文信息"""
        stmt = select(AffectionState).where(AffectionState.session_id == session_id)
        result = await db.execute(stmt)
        affections = result.scalars().all()

        contexts = []
        for aff in affections:
            char_data = await self._load_template_from_db(db, aff.character_id)
            if char_data:
                contexts.append(self._build_character_context(char_data, aff))
            else:
                # 模板不存在时用基本信息
                contexts.append({
                    "name": aff.character_name,
                    "real_name": aff.character_name,
                    "name_revealed": aff.character_name != "???",
                    "personality_summary": "",
                    "attitude_towards_player": aff.current_rank,
                    "affection_summary": f"综合分数:{aff.overall_score:.0f}",
                })

        return contexts

    async def _get_player_profile(
        self, db: AsyncSession, session_id: str
    ) -> PlayerProfile | None:
        """获取玩家画像"""
        stmt = select(PlayerProfile).where(PlayerProfile.session_id == session_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def _apply_affection_changes(
        self,
        db: AsyncSession,
        session_id: str,
        changes: list[dict],
    ):
        """将 LLM 评估的好感度变化应用到数据库"""
        # 获取所有角色的好感度状态
        stmt = select(AffectionState).where(AffectionState.session_id == session_id)
        result = await db.execute(stmt)
        affections = result.scalars().all()

        applied_any = False
        for aff in affections:
            char_changes = []
            for change in changes:
                change_char = change.get("character", "").strip()
                # 按 display name 或 character_id 匹配
                if change_char == aff.character_name or change_char == aff.character_id:
                    char_changes.append(change)
            if char_changes:
                self._affection_calc.apply_changes(aff, char_changes)
                applied_any = True

                logger.info(
                    f"💗 好感度变化: {aff.character_name} ({aff.character_id}) "
                    f"应用了 {len(char_changes)} 项变化"
                )

        if not applied_any and changes:
            logger.warning(
                f"⚠️ 好感度变化未能匹配任何角色: "
                f"LLM 返回的角色名 = {[c.get('character', '?') for c in changes]}, "
                f"现有角色 = {[(a.character_name, a.character_id) for a in affections]}"
            )


# ---------------------------------------------------------------------------
# 单例
# ---------------------------------------------------------------------------
narrator = Narrator()
