"""
Narrator Engine - LLM 结构化输出解析器

将 LLM 返回的文本解析为结构化的游戏数据。
引擎要求 LLM 输出 JSON 格式，此模块负责：
  1. 尝试直接 JSON 解析
  2. 如果失败，用正则从文本中提取 JSON 块
  3. 如果仍失败，用宽松模式从纯文本中构建结构
  4. 校验必要字段，缺失时用默认值填充
"""

import json
import re

from loguru import logger


class ResponseParser:
    """
    LLM 响应解析器。

    将 LLM 的原始文本输出解析为结构化的 DialogueAdvanceResponse。

    期望的 JSON 格式:
    {
        "narration": "叙事文本...",
        "dialogues": [
            {"speaker": "角色名", "text": "台词", "emotion": "情感", "action": "动作"}
        ],
        "choices": [
            {"id": "c1", "text": "选项文本", "tone": "风格", "hint": "提示"}
        ],
        "scene_state": {
            "location": "当前地点",
            "time": "时间",
            "mood": "氛围"
        },
        "affection_changes": [
            {"character": "角色名", "dimension": "维度", "delta": 3, "reason": "原因"}
        ]
    }
    """

    # LLM 可能返回的最大重试次数
    MAX_RETRY = 2

    # 英文 emotion → 中文翻译映射（兜底用，防止 LLM 输出英文标签）
    _EMOTION_EN_TO_ZH = {
        "amused": "玩味",
        "warm": "温和",
        "cold": "冷淡",
        "disdainful": "不屑",
        "contemptuous": "不屑",
        "scornful": "不屑",
        "shy": "害羞",
        "embarrassed": "害羞",
        "surprised": "惊讶",
        "shocked": "震惊",
        "sad": "悲伤",
        "grief": "悲伤",
        "angry": "愤怒",
        "furious": "暴怒",
        "annoyed": "不耐烦",
        "irritated": "恼怒",
        "curious": "好奇",
        "interested": "感兴趣",
        "serious": "认真",
        "determined": "坚定",
        "playful": "俏皮",
        "teasing": "戏谑",
        "mysterious": "神秘",
        "enigmatic": "神秘",
        "gentle": "温柔",
        "tender": "温柔",
        "cheerful": "开朗",
        "happy": "开心",
        "joyful": "喜悦",
        "confused": "困惑",
        "worried": "担忧",
        "nervous": "紧张",
        "calm": "平静",
        "neutral": "平静",
        "indifferent": "冷漠",
        "apathetic": "淡漠",
        "smug": "得意",
        "proud": "骄傲",
        "humble": "谦逊",
        "fearful": "恐惧",
        "terrified": "恐惧",
        "disgusted": "厌恶",
        "disappointed": "失望",
        "hopeful": "期待",
        "nostalgic": "怀念",
        "melancholic": "忧郁",
        "resigned": "无奈",
        "relieved": "释然",
        "suspicious": "怀疑",
        "wary": "警惕",
        "thoughtful": "沉思",
        "pensive": "沉思",
        "excited": "兴奋",
    }

    def parse(self, raw_text: str) -> dict:
        """
        解析 LLM 的原始输出文本为结构化字典。

        解析策略（按优先级）:
          1. 直接 json.loads 解析
          2. 正则提取 ```json ... ``` 代码块
          3. 正则提取第一个 { ... } 块
          4. 宽松模式：将全文作为叙事文本

        Args:
            raw_text: LLM 返回的原始文本

        Returns:
            结构化的响应字典，保证包含 narration, dialogues, choices 等字段
        """
        if not raw_text or not raw_text.strip():
            logger.warning("收到空的 LLM 响应，返回降级响应")
            return self._default_response("")

        # ---- 策略 1: 直接 JSON 解析 ----
        result = self._try_json_parse(raw_text)
        if result:
            parsed = self._validate_and_fill(result)
            return self._ensure_narration(parsed)

        # ---- 策略 2: 提取 ```json ... ``` 代码块 ----
        result = self._try_code_block_extract(raw_text)
        if result:
            parsed = self._validate_and_fill(result)
            return self._ensure_narration(parsed)

        # ---- 策略 3: 提取第一个 { ... } 块 ----
        result = self._try_brace_extract(raw_text)
        if result:
            parsed = self._validate_and_fill(result)
            return self._ensure_narration(parsed)

        # ---- 策略 4: 宽松模式，全部作为叙事文本 ----
        logger.warning("无法从 LLM 响应中提取 JSON，使用宽松模式")
        return self._default_response(raw_text)

    # ------------------------------------------------------------------
    #  内部解析方法
    # ------------------------------------------------------------------

    def _try_json_parse(self, text: str) -> dict | None:
        """尝试直接 JSON 解析"""
        try:
            data = json.loads(text.strip())
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass
        return None

    def _try_code_block_extract(self, text: str) -> dict | None:
        """从 Markdown 代码块中提取 JSON"""
        # 匹配 ```json ... ``` 或 ``` ... ```
        pattern = r"```(?:json)?\s*\n?(.*?)\n?```"
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1).strip())
            except json.JSONDecodeError:
                pass
        return None

    def _try_brace_extract(self, text: str) -> dict | None:
        """从文本中提取第一个完整的 {...} 块"""
        # 找到第一个 { 和最后一个 } 之间的内容
        first_brace = text.find("{")
        last_brace = text.rfind("}")
        if first_brace != -1 and last_brace > first_brace:
            try:
                return json.loads(text[first_brace:last_brace + 1])
            except json.JSONDecodeError:
                pass
        return None

    def _validate_and_fill(self, data: dict) -> dict:
        """
        校验解析出的字典，确保所有必要字段存在。
        缺失的字段用合理的默认值填充。
        """
        result = {
            "narration": data.get("narration", ""),
            "dialogues": [],
            "choices": [],
            "scene_state": data.get("scene_state", {}),
            "affection_changes": data.get("affection_changes", []),
        }

        # 校验 dialogues（含 emotion 英转中兜底）
        raw_dialogues = data.get("dialogues", [])
        for d in raw_dialogues:
            if isinstance(d, dict):
                emotion = d.get("emotion", "")
                # 兜底：如果 emotion 是英文，自动翻译为中文
                emotion = self._normalize_emotion(emotion)
                result["dialogues"].append({
                    "speaker": d.get("speaker", "旁白"),
                    "text": d.get("text", ""),
                    "emotion": emotion,
                    "action": d.get("action", ""),
                })

        # 校验 choices
        raw_choices = data.get("choices", [])
        for i, c in enumerate(raw_choices):
            if isinstance(c, dict):
                result["choices"].append({
                    "id": c.get("id", f"c{i + 1}"),
                    "text": c.get("text", ""),
                    "tone": c.get("tone", ""),
                    "hint": c.get("hint", ""),
                })

        return result

    def _normalize_emotion(self, emotion: str) -> str:
        """
        将 emotion 标签规范化为中文。
        
        如果 emotion 是英文，查表翻译为中文。
        如果已经是中文或无法识别，保持原样。
        """
        if not emotion:
            return ""
        
        stripped = emotion.strip().lower()
        
        # 如果全是 ASCII 字符（即英文），尝试翻译
        if stripped.isascii() and stripped.isalpha():
            translated = self._EMOTION_EN_TO_ZH.get(stripped)
            if translated:
                return translated
            # 未命中映射表时，保留原文并记录警告
            logger.debug(f"未知的英文 emotion 标签: '{emotion}'，保留原值")
        
        return emotion

    def _ensure_narration(self, parsed: dict) -> dict:
        """
        确保响应中有有效的叙事文本。

        如果 narration 为空但 dialogues 存在，用第一个对话的角色和动作
        生成一段过渡叙事，避免出现「叙事引擎暂时沉默」。
        """
        narration = parsed.get("narration", "").strip()
        dialogues = parsed.get("dialogues", [])

        if narration:
            return parsed  # narration 已经有内容，无需修改

        if dialogues:
            # 从对话中提取上下文来构建一段过渡叙事
            first = dialogues[0]
            speaker = first.get("speaker", "某人")
            action = first.get("action", "")
            if action:
                parsed["narration"] = f"{speaker}{action}。"
            else:
                parsed["narration"] = f"{speaker}转过身来，看向你。"
            logger.debug(f"narration 为空但有对话，补充过渡叙事: {parsed['narration'][:50]}...")
        else:
            # 完全没有内容 — 返回一个简短但有画面感的默认叙事
            parsed["narration"] = "四周陷入了片刻的沉默，空气中只剩下微风拂过的声音。"
            logger.warning("narration 和 dialogues 均为空，使用通用过渡叙事")

        return parsed

    def _default_response(self, narration_text: str) -> dict:
        """
        构建默认的 fallback 响应。
        当所有解析策略都失败时使用。
        """
        narration = narration_text.strip() if narration_text else ""
        if not narration:
            narration = "四周陷入了片刻的沉默，空气中只剩下微风拂过的声音。"

        return {
            "narration": narration,
            "dialogues": [],
            "choices": [
                {"id": "c1", "text": "环顾四周，寻找下一步的线索", "tone": "neutral", "hint": ""},
                {"id": "c2", "text": "回忆刚才发生的事情", "tone": "thoughtful", "hint": ""},
            ],
            "scene_state": {},
            "affection_changes": [],
        }


class MemoryExtractParser:
    """
    记忆提取响应的解析器。

    解析 LLM 从对话中提取记忆时返回的结构化 JSON。
    """

    def parse(self, raw_text: str) -> dict:
        """
        解析记忆提取的 LLM 输出。

        期望格式:
        {
            "episodic_summary": "场景摘要文本",
            "new_facts": [{"content": "...", "importance": 8, "category": "..."}],
            "relationship_changes": [{"character": "...", "change_description": "..."}],
            "player_traits_observed": ["特征1", "特征2"],
            "plot_threads": ["剧情线索1"]
        }
        """
        # 复用 ResponseParser 的 JSON 提取逻辑
        parser = ResponseParser()

        result = parser._try_json_parse(raw_text)
        if not result:
            result = parser._try_code_block_extract(raw_text)
        if not result:
            result = parser._try_brace_extract(raw_text)

        if not result:
            logger.warning("记忆提取解析失败，返回空结果")
            return {
                "episodic_summary": "",
                "new_facts": [],
                "relationship_changes": [],
                "player_traits_observed": [],
                "plot_threads": [],
            }

        # 确保字段存在
        return {
            "episodic_summary": result.get("episodic_summary", ""),
            "new_facts": result.get("new_facts", []),
            "relationship_changes": result.get("relationship_changes", []),
            "player_traits_observed": result.get("player_traits_observed", []),
            "plot_threads": result.get("plot_threads", []),
        }


# ---------------------------------------------------------------------------
# 便捷单例
# ---------------------------------------------------------------------------
response_parser = ResponseParser()
memory_parser = MemoryExtractParser()
