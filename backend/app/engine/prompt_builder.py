"""
Narrator Engine - Prompt 构建器

职责：
  1. 加载 Jinja2 Prompt 模板文件
  2. 将世界观、角色、记忆、场景等上下文注入模板
  3. 组装出完整的 System Prompt 发送给 LLM

这是影响 AI 输出质量的最关键模块——
好的 Prompt = 好的叙事。
"""

from pathlib import Path

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

    def build_memory_extract_prompt(self, dialogue_text: str) -> str:
        """
        构建记忆提取的 Prompt。

        在每轮对话结束后异步调用，让 LLM 从对话中提取关键信息。

        Args:
            dialogue_text: 本轮对话的完整文本

        Returns:
            记忆提取 Prompt 文本
        """
        try:
            template = self._env.get_template("memory_extract.j2")
            return template.render(dialogue_text=dialogue_text)
        except Exception:
            logger.warning("memory_extract.j2 不存在，使用内置默认")
            return self._default_memory_prompt(dialogue_text)

    def build_affection_eval_prompt(
        self,
        dialogue_text: str,
        character_info: dict,
    ) -> str:
        """
        构建好感度评估的 Prompt。

        让 LLM 分析玩家本轮对话对各角色好感度的影响。

        Args:
            dialogue_text: 本轮对话文本
            character_info: 当前角色的好感度配置信息

        Returns:
            好感度评估 Prompt 文本
        """
        try:
            template = self._env.get_template("affection_eval.j2")
            return template.render(
                dialogue_text=dialogue_text,
                character_info=character_info,
            )
        except Exception:
            logger.warning("affection_eval.j2 不存在，使用内置默认")
            return self._default_affection_prompt(dialogue_text, character_info)

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
            real = char.get('real_name', '')
            name_note = ""
            if not char.get('name_revealed') and real and real != name:
                name_note = f"（真名: {real}，尚未揭示——请在合适的剧情时机让角色自我介绍）"
            parts.append(f"## 角色: {name}{name_note}")
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

    def _default_memory_prompt(self, dialogue_text: str) -> str:
        """内置的默认记忆提取 Prompt"""
        return (
            "分析以下对话，提取需要长期记忆的信息。\n\n"
            f"对话内容:\n{dialogue_text}\n\n"
            "请输出 JSON 格式:\n"
            "{\n"
            '  "episodic_summary": "场景摘要",\n'
            '  "new_facts": [{"content": "事实", "importance": 7, "category": "other"}],\n'
            '  "relationship_changes": [],\n'
            '  "player_traits_observed": [],\n'
            '  "plot_threads": []\n'
            "}"
        )

    def _default_affection_prompt(self, dialogue_text: str, char_info: dict) -> str:
        """内置的默认好感度评估 Prompt"""
        return (
            f"分析以下对话对角色好感度的影响。\n\n"
            f"角色信息: {char_info}\n\n"
            f"对话:\n{dialogue_text}\n\n"
            "请输出 JSON:\n"
            '[{"character": "角色名", "dimension": "intimacy", "delta": 2, "reason": "原因"}]'
        )

    def _get_output_schema(self) -> str:
        """返回 JSON 输出格式的 Schema 描述文本"""
        return (
            "你必须输出如下 JSON 格式:\n"
            "{\n"
            '  "narration": "叙事文本（环境描写、旁白、角色间的过渡动作）",\n'
            '  "dialogues": [\n'
            '    {"speaker": "角色显示名", "text": "台词", "emotion": "中文情感标签", "action": "动作描写"}\n'
            "  ],\n"
            '  "choices": [\n'
            '    {"id": "c1", "text": "选项文本", "tone": "语气标签", "hint": "简短提示"}\n'
            "  ],\n"
            '  "scene_state": {"location": "地点", "time": "时间", "mood": "氛围"},\n'
            '  "affection_changes": [\n'
            '    {"character": "角色显示名", "dimension": "intimacy/trust/respect/curiosity/fear", '
            '"delta": 2, "reason": "变化原因"}\n'
            "  ]\n"
            "}\n"
            "【重要格式要求】\n"
            "1. emotion 字段必须使用中文，如: 温和、冷淡、不屑、害羞、惊讶、悲伤、玩味、认真、好奇。禁止使用英文。\n"
            "2. speaker 字段必须使用角色的「显示名」（见角色列表中的 name 字段）。如果显示名是 ???，就使用 ???。\n"
            "3. narration 和 dialogues 至少有一个非空。choices 提供 2-4 个选项。\n"
            "4. dialogues 中每个角色的台词之间应有叙事过渡（在 narration 中描写），不要让角色像排队一样轮流发言。\n"
            "5. 每轮最多 2-3 个角色的对话，不要在一轮内让所有角色都发言。\n"
            "\n"
            "【角色名字揭示规则】\n"
            "1. 如果角色的 name 显示为 ???，说明玩家还不知道这个角色的真名。\n"
            "2. 在叙事和对话中，你应该用外貌描写来代替名字（如「银发女子」「黑衣剑客」「温柔学姐」）。speaker 字段必须写 ???。\n"
            "3. **重要**: 在第 2-3 轮对话内，至少让一个角色自然地自我介绍。可以在对话中让角色说出自己的真名（即 real_name 字段中的确切名字）。\n"
            "4. 自我介绍时，speaker 字段必须从 ??? 切换为 real_name 中的确切名字。不要使用头衔（如「班长」「学姐」）代替真名。\n"
            "5. 说出真名后，后续所有对话的 speaker 都使用该真名。\n"
            "6. 其他未揭示名字的角色仍使用 ???，在后续轮次中逐步揭示。\n"
            "\n"
            "【剧情推进规则】\n"
            "1. 每个选项都应该推动剧情发展，有具体的行动或决策，禁止只出现「继续」「继续探索」等空泛选项。\n"
            "2. 选项应包含：明确的行动意图、对话选择、或关键决策。例如：「询问她为什么会在这里」「跟随她进入禁地」「转身离开此处」。\n"
            "3. 每 4-6 轮对话后应该有明显的剧情转折或场景切换。\n"
            "4. 注意当前章节和剧情钩子（plot_hooks），主动引导玩家接触核心剧情。\n"
            "5. 随着章节推进，逐步揭示世界秘密和角色背景，不要一次性全部揭露。\n"
            "\n"
            "【好感度变化规则】\n"
            "1. 每轮都必须在 affection_changes 中评估玩家行为对各角色好感度的影响。\n"
            "2. character 字段使用角色的显示名（如果尚未揭示名字就写 ???）。\n"
            "3. 每次变化 delta 范围 -5 到 +5，需要有明确原因。\n"
        )
