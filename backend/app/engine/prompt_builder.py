"""
Narrator Engine - Prompt 构建器

职责：
  1. 加载 Jinja2 Prompt 模板文件
  2. 将世界观、角色、记忆、场景等上下文注入模板
  3. 组装出完整的 System Prompt 发送给 LLM

这是影响 AI 输出质量的最关键模块——
好的 Prompt = 好的叙事。
"""

from jinja2 import Environment, FileSystemLoader
from loguru import logger

from app.config import get_settings


class PromptBuilder:
    """
    Prompt 构建器。

    使用 Jinja2 模板引擎动态组装 System Prompt。
    模板文件存放在 backend/prompts/ 目录下。

    主要模板:
      - system_prompt.j2: 主系统提示词（每轮都发送）
      - memory_extract.j2: 记忆提取提示词（对话结束后异步调用）
      - affection_eval.j2: 好感度评估提示词（每轮对话后调用）
    """

    def __init__(self):
        """初始化 Jinja2 模板环境"""
        settings = get_settings()
        prompts_dir = settings.prompts_dir

        # 如果 prompts 目录不存在，创建它
        prompts_dir.mkdir(parents=True, exist_ok=True)

        self._env = Environment(
            loader=FileSystemLoader(str(prompts_dir)),
            # 不自动转义（Prompt 不需要 HTML 转义）
            autoescape=False,
            # 去除多余空白，保持 Prompt 紧凑
            trim_blocks=True,
            lstrip_blocks=True,
        )

        logger.info(f"Prompt 构建器已初始化，模板目录: {prompts_dir}")

    def build_system_prompt(
        self,
        world_context: dict,
        character_context: list[dict],
        scene_context: dict,
        memory_context: dict,
        player_profile: dict,
        recent_narration_summary: str = "",
    ) -> str:
        """
        构建完整的 System Prompt。

        这是每轮对话都发送的核心提示词，由多个上下文拼接而成。

        Args:
            world_context: 世界观信息 (设定、规则、当前地点)
            character_context: 当前出场角色列表 (每人含性格、好感度等)
            scene_context: 当前场景信息 (地点、时间、氛围、剧情钩子)
            memory_context: 记忆上下文 (关键事实、场景摘要、最近对话)
            player_profile: 玩家画像 (角色名、性格特征、游玩风格)
            recent_narration_summary: 近期叙事摘要 (用于防重复)

        Returns:
            完整的 System Prompt 文本
        """
        try:
            template = self._env.get_template("system_prompt.j2")
        except Exception:
            # 如果模板文件不存在，使用内置的默认 Prompt
            logger.warning("system_prompt.j2 模板不存在，使用内置默认")
            return self._default_system_prompt(
                world_context, character_context, scene_context,
                memory_context, player_profile
            )

        # JSON 输出格式的 Schema 描述（嵌入 Prompt 中让 LLM 知道格式要求）
        output_schema = self._get_output_schema()

        return template.render(
            world_context=world_context,
            active_characters=character_context,
            scene_context=scene_context,
            memory_context=memory_context,
            player_profile=player_profile,
            output_schema=output_schema,
            recent_narration_summary=recent_narration_summary,
        )

    # ------------------------------------------------------------------
    #  内置默认 Prompt（模板文件不存在时的降级方案）
    # ------------------------------------------------------------------

    def _default_system_prompt(
        self, world_ctx, char_ctx, scene_ctx, memory_ctx, player_ctx
    ) -> str:
        """内置的默认 System Prompt（简化版）"""
        parts = [
            "你是一个专业的互动叙事引擎，负责扮演角色、描述场景、推进剧情。",
            "你需要像一位优秀的 Galgame 编剧 + 地下城主(DM)那样即兴创作。",
            "",
            "## 核心规则",
            "1. 保持角色性格一致性，每个角色的言行必须符合其性格设定",
            "2. 不要一次性揭露太多信息，保持悬念，让玩家通过互动逐步发现真相",
            "3. 好感度变化应渐进自然，高好感度解锁更亲密的互动",
            "4. 使用五感描写（视觉、听觉、触觉）增强画面感和沉浸感",
            "5. 每个角色单次发言控制在 2-4 句，避免长篇独白",
            "6. 提供 2-4 个选项，各有侧重，没有明显的「正确答案」",
            "7. 禁止空洞填充：narration 每句话必须有实际信息。"
            "禁止写「四周陷入沉默」「只剩微风」「空气凝固」等拖延剧情的废话。直接承接玩家行动。",
            "",
            "## 剧情推进（极重要）",
            "1. 每个选项必须推动剧情发展，包含具体行动或决策。",
            "   ✗ 禁止：「继续」「继续探索」「看看周围」等空泛选项",
            "   ✓ 正确：「质问她为何出现在禁地」「跟随黑影进入暗巷」「回屋翻阅古籍寻找线索」",
            "2. 每 4-6 轮对话应有明显的剧情推进或场景变化",
            "3. 主动引导玩家接触 plot_hooks 中的剧情钩子",
            "4. 随章节推进逐步揭示秘密，不要一次性全部暴露",
            "",
        ]

        # 世界观
        if world_ctx:
            parts.append(f"## 世界设定\n- 名称: {world_ctx.get('name', '未知')}")
            if world_ctx.get('description'):
                parts.append(f"- 设定: {world_ctx['description'][:300]}")
            rules = world_ctx.get('rules', [])
            if rules:
                parts.append("- 规则:")
                for r in rules[:5]:
                    parts.append(f"  · {r}")
            if world_ctx.get('current_location'):
                parts.append(f"- 当前地点: {world_ctx['current_location']}")
            if world_ctx.get('current_time'):
                parts.append(f"- 当前时间: {world_ctx['current_time']}")
            parts.append("")

        # 当前场景 + 章节指引
        if scene_ctx:
            parts.append(f"## 当前场景 (第{scene_ctx.get('chapter', 1)}章 / 共{scene_ctx.get('total_chapters', '?')}章)")
            if scene_ctx.get('premise'):
                parts.append(f"- 故事前提: {scene_ctx['premise']}")
            if scene_ctx.get('chapter_guide'):
                parts.append(f"- **章节指引**: {scene_ctx['chapter_guide']}")
            hooks = scene_ctx.get('plot_hooks', [])
            if hooks:
                parts.append("- 剧情钩子（逐步引导玩家接触，不要一次性揭露）:")
                for h in hooks:
                    parts.append(f"  · {h}")
            parts.append("")

        # 角色
        for char in (char_ctx or []):
            name = char.get('name', '?')
            parts.append(f"## 角色: {name}")
            if char.get('personality_summary'):
                parts.append(f"- 性格: {char['personality_summary']}")
            if char.get('speech_style'):
                parts.append(f"- 说话风格: {char['speech_style']}")
            if char.get('attitude_towards_player'):
                parts.append(f"- 对玩家态度: {char['attitude_towards_player']}")
            parts.append("")

        # 记忆
        if memory_ctx:
            facts = memory_ctx.get('key_facts', [])
            if facts:
                parts.append("## 关键记忆")
                for f in facts:
                    parts.append(f"- {f}")
            parts.append("")

        # 玩家
        if player_ctx:
            parts.append("## 玩家信息")
            parts.append(f"- 角色名: {player_ctx.get('name', '主角')}")
            traits = player_ctx.get('traits', [])
            if traits:
                parts.append(f"- 已展现特征: {', '.join(str(t) for t in traits)}")
            if player_ctx.get('play_style'):
                parts.append(f"- 游玩风格: {player_ctx['play_style']}")
            parts.append("")

        # 输出格式
        parts.append(f"## 输出格式\n{self._get_output_schema()}")

        return "\n".join(parts)

    def _get_output_schema(self) -> str:
        """返回结构化输出的行为规则（Pydantic schema 已通过 function calling 传递格式，此处仅补充行为约束）"""
        return (
            "你必须输出 JSON 格式的结构化数据，严格遵守以下规则：\n"
            "\n"
            "【极重要 — narration 与 dialogues 必须严格分离】\n"
            "1. narration 只能包含：环境描写、旁白叙述、动作过渡、场景切换。绝对不要在里面写角色台词。\n"
            "2. 角色的所有台词/对白必须放在 dialogues 数组中。每条包含 speaker（角色名）、text（台词）、emotion（情感）、action（动作）。\n"
            "3. 禁止在 narration 中使用 [角色名] 或 【角色名】 标签来写台词——那是错误的格式。\n"
            "4. 禁止在 narration 中附加 [场景:] 标签——场景信息已在 scene_state 中。\n"
            "5. 当有角色说话时，dialogues 数组不能为空。如果故事中有角色对白，必须拆分到 dialogues 中。\n"
            "6. 正确示例:\n"
            '   narration: "晨光洒落，雾气渐散。凝光收回烟斗，嘴角微扬。"\n'
            '   dialogues: [{"speaker": "凝光", "text": "倒是直爽。", "emotion": "略带赞许", "action": "捋了捋袖口"}]\n'
            "7. 错误示例（绝对禁止）:\n"
            '   narration: "[凝光] (捋了捋袖口) 倒是直爽... [甘雨] 若你决定前往..."  ← 台词不能写在 narration 中！\n'
            '   dialogues: []  ← 有角色对白时 dialogues 不能为空！\n'
            "\n"
            "【speaker 字段规则】\n"
            "1. speaker 只能是角色名字（如「甘雨」「凝光」「酒馆老板」）。\n"
            "2. 禁止用情感词（如「温和」「从容」）、动作词（如「微笑」「叹气」）作为 speaker。\n"
            "3. emotion 字段使用中文情感标签：温和、冷淡、从容、惊讶、愤怒等。\n"
            "\n"
            "【choices 选项规则】\n"
            "1. 提供 3-4 个与剧情相关的具体选项，禁止空泛选项（如「环顾四周」「继续探索」）。\n"
            "2. 选项只能放在 choices 数组中，禁止写在 dialogues.text 中。\n"
            "3. 选项之间应有不同语气/态度倾向（如坦诚 vs 谨慎 vs 大胆）。\n"
            "\n"
            "【affection_changes 规则】\n"
            "1. 不能为空数组，每轮至少 1 条好感度变化记录。\n"
            "2. dimension 只能是: intimacy, trust, respect, curiosity, fear 之一。\n"
            "3. delta 范围 -5 到 +5，需要有明确原因。\n"
            "\n"
            "【scene_state 规则】\n"
            "1. location 是具体地点名称，time 是具体时间，mood 是氛围词（不能为空）。\n"
            "2. 如果场景没有变化，保持上一轮的值。\n"
        )
