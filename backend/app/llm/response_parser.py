"""
Narrator Engine - LLM 结构化输出解析器

将 LLM 返回的文本解析为结构化的游戏数据。
引擎主要通过 Pydantic structured output 获得结构化数据，此模块作为兜底：
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
    LLM 响应解析器（兜底解析）。

    主路径通过 Pydantic structured output 直接获得结构化数据，
    本解析器仅在 structured output 失败、降级为 JSON mode 时使用。

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
            logger.warning("收到空 LLM 响应，返回降级响应")
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
    #  安全网：防止格式漂移
    # ------------------------------------------------------------------

    # 匹配 [角色名] 或 【角色名】 标签
    _SPEAKER_TAG_RE = re.compile(r'[\[【]([^】\]]{1,40})[\]】]\s*')
    # 匹配 (动作描写) 或 （动作描写）
    _ACTION_RE = re.compile(r'^[\(（]([^）\)]+)[\)）]\s*')
    # 匹配 [情感标签]: 或 【情感标签】:
    _INLINE_EMOTION_RE = re.compile(r'^[\[【]([^】\]]{1,10})[\]】][:：]?\s*')

    # 场景/元数据标签前缀（这些不是角色名，应留在 narration 中）
    _SCENE_PREFIXES = ("场景", "Scene", "scene", "环境", "氛围", "BGM", "bgm", "音乐")

    # 常见情感/状态词（用于识别情感标签 vs 角色名）
    _EMOTION_KEYWORDS = {
        "温和", "冷淡", "从容", "平静", "愤怒", "惊讶", "害羞", "好奇",
        "认真", "玩味", "不屑", "悲伤", "坚定", "紧张", "微笑", "沉思",
        "开心", "失落", "期待", "无奈", "骄傲", "警惕", "神秘", "戏谑",
        "俏皮", "严肃", "关怀", "担忧", "嘲讽", "冷漠", "热情", "安慰",
        "感激", "感动", "欣慰", "愧疚", "抱歉", "心疼", "关切", "焦急",
        "诚恳", "郑重", "恳切", "淡定", "镇定", "沉着", "坦然", "悠然",
        "愕然", "怅然", "茫然", "恍然", "肃然", "默然", "黯然", "莞尔",
        # 补充常见 2 字情感/语气词
        "谨慎", "小心", "坦然", "冷静", "沉思", "犹豫", "果断", "诚恳",
        "低沉", "高亢", "柔和", "生硬", "急切", "从容", "淡定", "释然",
        "意味深长", "若有所思", "欲言又止", "不置可否",
        "略带赞许", "温和而正式", "温和而感激", "平静而坚定",
    }

    def ensure_dialogues(self, parsed: dict) -> dict:
        """
        安全网：当 narration 含 [角色名] 台词但 dialogues 为空时，自动提取。

        仅在「narration 有角色标签 + dialogues 为空」时触发，
        正常结构化输出不受影响。
        """
        narration = parsed.get("narration", "").strip()
        dialogues = parsed.get("dialogues", [])

        # 只在 dialogues 为空 且 narration 含 [标签] 时触发
        if dialogues or not narration:
            return parsed
        if not self._SPEAKER_TAG_RE.search(narration):
            return parsed

        logger.warning(
            "安全网触发: narration 含角色标签但 dialogues 为空，自动提取对话"
        )

        # --- 第一轮：提取所有标签的原始数据 ---
        matches = list(self._SPEAKER_TAG_RE.finditer(narration))
        raw_entries = []  # [(tag, action, emotion_inline, text, is_scene, is_narrator)]
        narration_parts = []
        pos = 0

        for i, m in enumerate(matches):
            tag = m.group(1).strip()
            next_start = matches[i + 1].start() if i + 1 < len(matches) else len(narration)
            before = narration[pos:m.start()].strip()

            # 场景标签 → 留在 narration
            if self._is_scene_tag(tag):
                if before:
                    narration_parts.append(before)
                narration_parts.append(narration[m.start():next_start].strip())
                pos = next_start
                continue

            # 旁白标签 → 留在 narration
            if tag == "旁白":
                if before:
                    narration_parts.append(before)
                raw = narration[m.end():next_start].strip()
                if raw:
                    narration_parts.append(raw)
                pos = next_start
                continue

            # 角色/情感标签 → 先记录原始数据
            if before:
                narration_parts.append(before)

            raw_text = narration[m.end():next_start].strip()
            action = ""
            emotion_inline = ""

            action_match = self._ACTION_RE.match(raw_text)
            if action_match:
                action = action_match.group(1)
                raw_text = raw_text[action_match.end():]

            emotion_match = self._INLINE_EMOTION_RE.match(raw_text)
            if emotion_match:
                emotion_inline = emotion_match.group(1)
                raw_text = raw_text[emotion_match.end():]

            raw_text = re.sub(r'^[:：]\s*', '', raw_text).strip()

            raw_entries.append({
                "tag": tag,
                "action": action,
                "emotion_inline": emotion_inline,
                "text": raw_text,
            })
            pos = next_start

        tail = narration[pos:].strip()
        if tail:
            narration_parts.append(tail)

        # --- 第二轮：合并情感标签到前一条对话 ---
        dialogues = []
        i = 0
        while i < len(raw_entries):
            entry = raw_entries[i]
            tag = entry["tag"]

            # 判断是否为情感标签
            is_emotion = (
                len(tag) <= 8
                and not entry["action"]
                and (tag in self._EMOTION_KEYWORDS or self._looks_like_emotion(tag))
            )

            if is_emotion and dialogues:
                # 归入前一条对话的 emotion
                prev = dialogues[-1]
                if not prev["emotion"]:
                    prev["emotion"] = self._normalize_emotion(tag)
                # 情感标签后面附带的文本实际上属于该对话角色的台词
                # 合并到前一条对话的 text（因为情感标签紧跟在动作后面，属于同一角色）
                if entry["text"]:
                    prev["text"] = (prev["text"] + entry["text"]) if prev["text"] else entry["text"]
                i += 1
                continue

            dialogues.append({
                "speaker": tag,
                "text": entry["text"],
                "emotion": self._normalize_emotion(entry["emotion_inline"]),
                "action": entry["action"],
            })
            i += 1

        if dialogues:
            parsed["dialogues"] = dialogues
            cleaned = "\n\n".join(p for p in narration_parts if p.strip())
            if cleaned.strip():
                parsed["narration"] = cleaned.strip()
            else:
                first = dialogues[0]
                sp, act = first.get("speaker", "某人"), first.get("action", "")
                parsed["narration"] = f"{sp}{act}。" if act else f"{sp}开口说道。"
            logger.debug(
                f"安全网提取完成: {len(dialogues)} 条对话, "
                f"narration={len(parsed['narration'])}字"
            )

        return parsed

    # ------------------------------------------------------------------
    #  安全网：确保 choices 永不为空
    # ------------------------------------------------------------------

    def ensure_choices(self, parsed: dict) -> dict:
        """
        安全网：当 choices 为空或全部是通用选项时，根据上下文生成贴合剧情的选项。

        检测条件:
          1. choices 为空数组
          2. choices 全部是通用/空泛文本（如"主动搭话""保持警惕"）
        """
        choices = parsed.get("choices", [])

        # 检查是否全部是通用选项
        if choices and not self._all_generic(choices):
            return parsed

        if choices:
            logger.warning(f"安全网触发: {len(choices)} 个选项全是通用文本，替换为剧情选项")
        else:
            logger.warning("安全网触发: choices 为空，自动生成选项")

        narration = parsed.get("narration", "")
        dialogues = parsed.get("dialogues", [])
        generated = self._infer_choices(narration, dialogues)
        parsed["choices"] = generated
        return parsed

    # 通用选项关键词（匹配这些文本的选项视为通用/空泛）
    _GENERIC_PATTERNS = [
        "主动搭话", "主动和对方", "尝试了解更多", "尝试拉近",
        "保持警惕", "确认自己的处境", "先确认",
        "环顾四周", "看看周围", "继续探索", "仔细观察",
        "回忆刚才", "思考接下来", "继续前进",
        "保持沉默", "观察对方", "转移话题",
        "主动向对方搭话", "冷静分析当前",
    ]

    def _all_generic(self, choices: list) -> bool:
        """检查是否所有选项都是通用文本"""
        if not choices:
            return True
        generic_count = 0
        for c in choices:
            text = (c.get("text", "") or "").strip()
            if any(p in text for p in self._GENERIC_PATTERNS):
                generic_count += 1
            elif len(text) < 6:
                generic_count += 1
        return generic_count >= len(choices)

    def _infer_choices(self, narration: str, dialogues: list) -> list:
        """根据上下文动态生成贴合剧情的选项"""
        # 收集上下文关键信息
        last_speaker = ""
        last_text = ""
        has_question = False
        all_text = narration

        for d in dialogues:
            text = d.get("text", "")
            speaker = d.get("speaker", "")
            all_text += " " + text
            if speaker and speaker not in ("旁白", "???"):
                last_speaker = speaker
                last_text = text
            if "？" in text or "?" in text:
                has_question = True

        # 从文本中提取关键话题词
        topics = self._extract_topics(all_text)

        # 有角色提问 → 回应对方问题的选项
        if has_question and last_speaker:
            topic_hint = topics[0] if topics else "这件事"
            return [
                {"id": "c1", "text": f"坦诚告诉{last_speaker}你所知道的关于{topic_hint}的事", "tone": "坦诚", "hint": ""},
                {"id": "c2", "text": "含糊其辞，不轻易透露自己的底牌", "tone": "谨慎", "hint": ""},
                {"id": "c3", "text": f"反过来追问{last_speaker}为何关心{topic_hint}", "tone": "大胆", "hint": ""},
            ]

        # 有角色对话但没提问 → 根据话题推进
        if last_speaker and last_text:
            topic_hint = topics[0] if topics else "当前的状况"
            return [
                {"id": "c1", "text": f"顺着{last_speaker}的话题继续深入{topic_hint}", "tone": "认真", "hint": ""},
                {"id": "c2", "text": "沉默片刻，观察在场其他人的反应", "tone": "谨慎", "hint": ""},
                {"id": "c3", "text": f"主动提出一个关于{topic_hint}的新线索或想法", "tone": "大胆", "hint": ""},
            ]

        # 只有旁白 → 探索/行动选项
        location_hint = ""
        for kw in ["城", "镇", "村", "山", "林", "湖", "海", "殿", "塔", "街", "路", "桥"]:
            if kw in narration:
                idx = narration.index(kw)
                start = max(0, idx - 4)
                location_hint = narration[start:idx + 1]
                break

        if location_hint:
            return [
                {"id": "c1", "text": f"仔细探索{location_hint}附近的环境", "tone": "好奇", "hint": ""},
                {"id": "c2", "text": "寻找可以交流的人，打听情况", "tone": "友善", "hint": ""},
                {"id": "c3", "text": "保持警惕，先确认自己的处境", "tone": "谨慎", "hint": ""},
            ]

        return [
            {"id": "c1", "text": "环顾四周，寻找值得注意的线索", "tone": "好奇", "hint": ""},
            {"id": "c2", "text": "冷静分析当前的处境和可用资源", "tone": "谨慎", "hint": ""},
            {"id": "c3", "text": "主动行动，尝试与周围的人或事物互动", "tone": "积极", "hint": ""},
        ]

    def _extract_topics(self, text: str) -> list:
        """从文本中提取关键话题词（简单启发式）"""
        topics = []
        # 提取「」和 "" 中的关键词（通常是重要名词/概念）
        for pattern in [r'[「「]([^」」]{1,10})[」」]', r'["""]([^"""]{1,10})["""]']:
            matches = re.findall(pattern, text)
            for m in matches:
                clean = m.strip()
                if 2 <= len(clean) <= 6:
                    topics.append(clean)

        # 提取带特殊标记的词（如 "天理"、"深渊" 等被强调的概念）
        for kw in ["力量", "秘密", "真相", "线索", "遗迹", "契约", "使命", "使命",
                    "危险", "机遇", "威胁", "预言", "传说", "禁令", "约定"]:
            if kw in text and kw not in topics:
                topics.append(kw)

        # 去重并保持顺序
        seen = set()
        unique = []
        for t in topics:
            if t not in seen:
                seen.add(t)
                unique.append(t)
        return unique[:3]  # 最多返回 3 个话题

    def _looks_like_emotion(self, tag: str) -> bool:
        """模糊判断标签是否为情感描述（而非角色名）"""
        if len(tag) > 8:
            return False
        # 含已知情感词的短标签
        if any(kw in tag for kw in self._EMOTION_KEYWORDS):
            return True
        # "X而Y" 结构
        if re.match(r'^[\u4e00-\u9fff]{1,3}而[\u4e00-\u9fff]{1,4}$', tag):
            return True
        # 以 "地" 结尾的描述词
        if tag.endswith(("地", "的")) and len(tag) <= 6:
            return True
        return False

    def _is_scene_tag(self, tag: str) -> bool:
        """判断标签是否为场景/元数据标签（而非角色名）"""
        clean = tag.rstrip(":：").strip()
        return any(clean == p or clean.startswith(p) for p in self._SCENE_PREFIXES)

    # ------------------------------------------------------------------
    #  安全网：修复 JSON 泄漏到文本字段
    # ------------------------------------------------------------------

    # 匹配 JSON 对象 {"speaker":...} 或 {"id":...}
    _JSON_OBJ_RE = re.compile(r'\{[^{}]*"(?:speaker|id|text|emotion|action)"[^{}]*\}')

    def sanitize_json_leakage(self, parsed: dict) -> dict:
        """
        修复 LLM 将 JSON 结构数据泄漏到文本字段的问题。

        处理三种情况:
        1. narration 包含完整的 JSON（dialogues/choices 的 JSON 文本）
        2. dialogues 数组中混入 JSON 字符串（而非 dict 对象）
        3. choices 数组中混入 JSON 字符串
        """
        narration = parsed.get("narration", "")
        dialogues = parsed.get("dialogues", [])
        choices = parsed.get("choices", [])
        changed = False

        # ---- 1. 修复 dialogues 中的 JSON 字符串条目 ----
        if dialogues:
            fixed_dialogues = []
            for item in dialogues:
                if isinstance(item, str):
                    # 尝试解析 JSON 字符串
                    try:
                        obj = json.loads(item.strip())
                        if isinstance(obj, dict) and "speaker" in obj:
                            fixed_dialogues.append(obj)
                            changed = True
                            continue
                    except (json.JSONDecodeError, TypeError):
                        pass
                    # 不是有效 JSON，检查是否包含 JSON 片段
                    json_matches = self._JSON_OBJ_RE.findall(item)
                    for jm in json_matches:
                        try:
                            obj = json.loads(jm)
                            if isinstance(obj, dict) and "speaker" in obj:
                                fixed_dialogues.append(obj)
                                changed = True
                        except (json.JSONDecodeError, TypeError):
                            pass
                    if not json_matches:
                        fixed_dialogues.append(item)
                elif isinstance(item, dict):
                    # 检查 dict 的 text 字段是否包含 JSON
                    text = item.get("text", "")
                    if text and self._JSON_OBJ_RE.search(text):
                        # text 包含 JSON — 提取并追加到 dialogues
                        json_matches = self._JSON_OBJ_RE.findall(text)
                        clean_text = self._JSON_OBJ_RE.sub("", text).strip()
                        if clean_text:
                            item["text"] = clean_text
                            fixed_dialogues.append(item)
                        for jm in json_matches:
                            try:
                                obj = json.loads(jm)
                                if isinstance(obj, dict) and "speaker" in obj:
                                    fixed_dialogues.append(obj)
                                    changed = True
                            except (json.JSONDecodeError, TypeError):
                                pass
                    else:
                        fixed_dialogues.append(item)
                else:
                    fixed_dialogues.append(item)
            if changed or len(fixed_dialogues) != len(dialogues):
                parsed["dialogues"] = fixed_dialogues
                dialogues = fixed_dialogues

        # ---- 2. 修复 choices 中的 JSON 字符串条目 ----
        if choices:
            fixed_choices = []
            for item in choices:
                if isinstance(item, str):
                    try:
                        obj = json.loads(item.strip())
                        if isinstance(obj, dict) and ("text" in obj or "id" in obj):
                            fixed_choices.append(obj)
                            changed = True
                            continue
                    except (json.JSONDecodeError, TypeError):
                        pass
                    json_matches = self._JSON_OBJ_RE.findall(item)
                    for jm in json_matches:
                        try:
                            obj = json.loads(jm)
                            if isinstance(obj, dict):
                                fixed_choices.append(obj)
                                changed = True
                        except (json.JSONDecodeError, TypeError):
                            pass
                    if not json_matches:
                        fixed_choices.append(item)
                elif isinstance(item, dict):
                    fixed_choices.append(item)
                else:
                    fixed_choices.append(item)
            if changed or len(fixed_choices) != len(choices):
                parsed["choices"] = fixed_choices

        # ---- 3. 修复 narration 包含 JSON 结构 ----
        if narration and self._JSON_OBJ_RE.search(narration):
            logger.warning("安全网触发: narration 包含 JSON 结构数据，正在提取")

            # 优先尝试完整 JSON 解析
            full_json_parsed = False
            clean_narration = ""
            try:
                full_json = self._try_json_parse(narration)
                if full_json and isinstance(full_json, dict):
                    if isinstance(full_json.get("dialogues"), list):
                        for d in full_json["dialogues"]:
                            if isinstance(d, dict) and d.get("speaker"):
                                parsed.setdefault("dialogues", []).append(d)
                                changed = True
                    if isinstance(full_json.get("choices"), list):
                        for c in full_json["choices"]:
                            if isinstance(c, dict):
                                parsed.setdefault("choices", []).append(c)
                                changed = True
                    if isinstance(full_json.get("narration"), str):
                        clean_narration = full_json["narration"]
                    full_json_parsed = True
            except Exception:
                pass

            # 完整解析失败 → 用正则逐个提取散落的 JSON 对象
            if not full_json_parsed:
                json_matches = self._JSON_OBJ_RE.findall(narration)
                clean_narration = self._JSON_OBJ_RE.sub("", narration).strip()
                for jm in json_matches:
                    try:
                        obj = json.loads(jm)
                        if isinstance(obj, dict):
                            if "speaker" in obj:
                                parsed.setdefault("dialogues", []).append(obj)
                                changed = True
                            elif "id" in obj or "text" in obj:
                                parsed.setdefault("choices", []).append(obj)
                                changed = True
                    except (json.JSONDecodeError, TypeError):
                        pass

                # 清理 narration 中残留的 JSON 键值对文本
                clean_narration = re.sub(r'"narration"\s*:\s*"[^"]*"', '', clean_narration)
                clean_narration = re.sub(r'"dialogues"\s*:\s*\[.*?\]', '', clean_narration, flags=re.DOTALL)
                clean_narration = re.sub(r'"choices"\s*:\s*\[.*?\]', '', clean_narration, flags=re.DOTALL)
                clean_narration = re.sub(r'[{}\[\],:"]+', '', clean_narration)
                clean_narration = clean_narration.strip()

            if clean_narration and len(clean_narration) > 5:
                parsed["narration"] = clean_narration
            elif not dialogues and parsed.get("dialogues"):
                # narration 被清空了但提取出了 dialogues
                parsed["narration"] = "故事继续发展。"
            elif not clean_narration:
                parsed["narration"] = "故事继续发展。"

            if changed:
                logger.debug(
                    f"安全网: 从 narration JSON 中提取了 "
                    f"{len(parsed.get('dialogues', []))} 条对话, "
                    f"{len(parsed.get('choices', []))} 个选项"
                )

        return parsed

    # ------------------------------------------------------------------
    #  安全网：清洗 dialogue 字段中混入的场景标签
    # ------------------------------------------------------------------

    _SCENE_TAG_RE = re.compile(
        r'\s*\[(?:场景|Scene|scene)[^]]*\][^\n]*',
        re.IGNORECASE,
    )

    def clean_dialogue_fields(self, parsed: dict) -> dict:
        """
        清洗 dialogue 的 text 和 action 字段中混入的 [场景:...] 标签。

        LLM 有时会在台词末尾附加场景元数据，这些应该只出现在 scene_state 中。
        """
        dialogues = parsed.get("dialogues", [])
        for d in dialogues:
            if not isinstance(d, dict):
                continue
            for field in ("text", "action"):
                val = d.get(field, "")
                if val and self._SCENE_TAG_RE.search(val):
                    cleaned = self._SCENE_TAG_RE.sub('', val).strip()
                    if cleaned != val:
                        d[field] = cleaned
                        logger.debug(f"清洗 dialogue.{field} 中的场景标签")
        # 也清洗 narration 中的场景标签
        narration = parsed.get("narration", "")
        if narration and self._SCENE_TAG_RE.search(narration):
            parsed["narration"] = self._SCENE_TAG_RE.sub('', narration).strip()
            logger.debug("清洗 narration 中的场景标签")
        return parsed

    # ------------------------------------------------------------------
    #  安全网：移除 narration 中的空洞填充句
    # ------------------------------------------------------------------

    _FILLER_PATTERNS = [
        # 沉默类
        r'四周陷入了?片刻的?沉默[，,。]?[^。\n]*',
        r'一阵沉默(?:笼罩|弥漫|降临|覆盖)了?[^。\n]*',
        r'空气(?:仿佛)?(?:凝固|凝结|静止)了?[^。\n]*',
        r'时间(?:仿佛)?(?:静止|停滞|凝固)了?[^。\n]*',
        # 只剩环境音类
        r'(?:空气中|四周)?只剩下?(?:微风拂过|风声|风声呼啸|鸟鸣|虫鸣|溪水声)[^。\n]*(?:的声音|的声响|的声音)?',
        r'只有微风[^。\n]*',
        r'唯有(?:微风|风)[^。\n]*',
        # 气氛类
        r'气氛变得?(?:微妙|凝重|紧张|沉重|诡异)[^。\n]*',
        r'空气中弥漫着(?:某种|一种)?(?:说不清的|微妙的|难以言喻的)?[^。\n]*气息[^。\n]*',
        r'一种(?:说不清的|微妙的|难以言喻的)?(?:感觉|氛围|气息)[^。\n]*',
    ]

    _FILLER_RE = re.compile(
        r'(?:' + '|'.join(_FILLER_PATTERNS) + r')[。？！\n]*',
        re.IGNORECASE,
    )

    def remove_narration_filler(self, parsed: dict) -> dict:
        """
        移除 narration 中的空洞填充句。

        LLM 经常输出"四周陷入了片刻的沉默，空气中只剩下微风拂过的声音"
        这类毫无信息量的填充句来拖延剧情。检测并移除这些句子。
        如果移除后 narration 为空，保留原内容（不删除全部叙事）。
        """
        narration = parsed.get("narration", "")
        if not narration:
            return parsed

        cleaned = self._FILLER_RE.sub('', narration).strip()
        # 清理残留的连续换行或标点
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        cleaned = re.sub(r'[，,。]{2,}', '', cleaned).strip()

        if cleaned != narration:
            if cleaned and len(cleaned) > 5:
                # 有实质内容剩下，使用清理后的版本
                parsed["narration"] = cleaned
                logger.debug(
                    f"安全网触发: 移除 narration 填充句 "
                    f"({len(narration)}字 → {len(cleaned)}字)"
                )
            else:
                # 移除填充句后几乎为空 — 用有意义的过渡句替代
                # 尝试从 dialogues/choices 构建上下文相关的过渡
                replacement = self._build_filler_replacement(parsed)
                parsed["narration"] = replacement
                logger.warning(
                    f"安全网触发: narration 全是填充句，已替换为过渡句 "
                    f"({len(narration)}字 → {len(replacement)}字)"
                )
        return parsed

    def _build_filler_replacement(self, parsed: dict) -> str:
        """
        当 narration 全是填充句时，构建一个有上下文意义的过渡句。

        优先从 dialogues 中提取角色动作/台词作为过渡，
        如果连 dialogues 也为空则使用通用但不空洞的过渡句。
        """
        dialogues = parsed.get("dialogues", [])
        choices = parsed.get("choices", [])

        # 如果有角色台词，用角色动作做过渡
        if dialogues:
            speakers = list(dict.fromkeys(
                d.get("speaker", "") for d in dialogues if d.get("speaker")
            ))
            if speakers:
                names = "、".join(speakers[:2])
                return f"{names}的反应打破了短暂的僵局。"

        # 如果有选项，暗示玩家的选择产生了影响
        if choices:
            return "你的决定引发了新的变化。"

        # 最后的降级：通用过渡（比"沉默"好得多）
        return "事态在暗中推进着。"

    # ------------------------------------------------------------------
    #  安全网：合并被 LLM 拆分的对话条目
    # ------------------------------------------------------------------

    def merge_split_dialogues(self, parsed: dict) -> dict:
        """
        合并被 LLM 拆分的对话条目。

        LLM 常见拆分模式（错误）:
          条目1: speaker="凝光", text="", action="眯起眼睛"
          条目2: speaker="意味深长", text="台词...", emotion=""
        应合并为:
          speaker="凝光", text="台词...", emotion="意味深长", action="眯起眼睛"

        仅在检测到拆分模式时触发，正常输出不受影响。
        """
        dialogues = parsed.get("dialogues", [])
        if len(dialogues) < 2:
            return parsed

        merged = []
        i = 0
        did_merge = False

        while i < len(dialogues):
            curr = dialogues[i]
            curr_speaker = (curr.get("speaker", "") or "").strip()
            curr_text = (curr.get("text", "") or "").strip()
            curr_action = (curr.get("action", "") or "").strip()

            # 检测拆分模式：当前条目有 action 无 text，下一条有 text 且 speaker 像情感词
            if (
                not curr_text
                and curr_action
                and i + 1 < len(dialogues)
            ):
                nxt = dialogues[i + 1]
                nxt_speaker = (nxt.get("speaker", "") or "").strip()
                nxt_text = (nxt.get("text", "") or "").strip()

                if nxt_text and self._is_likely_emotion(nxt_speaker):
                    # 合并：当前 speaker + 当前 action + 下一条 text + 下一条 speaker 作为 emotion
                    merged.append({
                        "speaker": curr_speaker,
                        "text": nxt_text,
                        "emotion": self._normalize_emotion(nxt_speaker) or (nxt.get("emotion", "") or "").strip(),
                        "action": curr_action,
                    })
                    did_merge = True
                    i += 2
                    continue

            # 检测拆分模式2：当前条目 text 非空但 speaker 像情感词 → 归入前一条
            if curr_text and self._is_likely_emotion(curr_speaker) and merged:
                prev = merged[-1]
                if not prev.get("emotion"):
                    prev["emotion"] = self._normalize_emotion(curr_speaker)
                # 合并文本（如果前一条有 text 则拼接）
                if prev.get("text"):
                    prev["text"] = prev["text"] + curr_text
                else:
                    prev["text"] = curr_text
                # 合并 action
                nxt_action = (curr.get("action", "") or "").strip()
                if nxt_action:
                    prev["action"] = (prev.get("action", "") + nxt_action).strip()
                did_merge = True
                i += 1
                continue

            # 过滤 text 和 action 都为空的空条目
            if not curr_text and not curr_action:
                i += 1
                continue

            merged.append(curr)
            i += 1

        if did_merge:
            logger.debug(
                f"安全网合并: dialogues {len(dialogues)} → {len(merged)} 条"
            )
            parsed["dialogues"] = merged

        return parsed

    def _is_likely_emotion(self, speaker: str) -> bool:
        """判断 speaker 是否为情感词/描述词（非角色名）"""
        if not speaker:
            return False
        if len(speaker) > 10:
            return False
        # 在已知情感词表中
        if speaker in self._EMOTION_KEYWORDS:
            return True
        # 模糊匹配
        if self._looks_like_emotion(speaker):
            return True
        # 额外检测：含 "着" / "地" 的描述短语（如 "带着几分思索"）
        if "着" in speaker and len(speaker) <= 8:
            return True
        # 2-4 字且无明显人名特征的短词（大概率是情感/语气描述）
        if 2 <= len(speaker) <= 4:
            # 排除常见姓氏开头
            _COMMON_SURNAMES = "赵钱孙李周吴郑王冯陈褚卫蒋沈韩杨朱秦尤许何吕施张孔曹严华金魏陶姜"
            if speaker[0] not in _COMMON_SURNAMES:
                return True
        return False

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

        # 过滤非法 speaker 的元标签
        _INVALID_SPEAKERS = {
            "choices", "选项", "choice", "narration", "旁白",
            "narrator", "系统", "system", "player", "玩家",
        }
        raw_dialogues = data.get("dialogues", [])
        for d in raw_dialogues:
            if isinstance(d, dict):
                speaker = (d.get("speaker", "") or "").strip()
                if speaker.lower() in _INVALID_SPEAKERS:
                    logger.warning(f"过滤非法 speaker: '{speaker}'，跳过该条对话")
                    continue
                emotion = d.get("emotion", "")
                emotion = self._normalize_emotion(emotion)
                result["dialogues"].append({
                    "speaker": speaker or "旁白",
                    "text": d.get("text", ""),
                    "emotion": emotion,
                    "action": d.get("action", ""),
                })

        # 校验 choices
        raw_choices = data.get("choices", [])
        for i, c in enumerate(raw_choices):
            if isinstance(c, dict):
                result["choices"].append({
                    "id": str(c.get("id", "") or f"c{i + 1}"),
                    "text": c.get("text", ""),
                    "tone": c.get("tone", ""),
                    "hint": c.get("hint", "") or c.get("affection_hint", ""),
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

        if stripped.isascii() and stripped.isalpha():
            translated = self._EMOTION_EN_TO_ZH.get(stripped)
            if translated:
                return translated
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
            return parsed

        if dialogues:
            first = dialogues[0]
            speaker = first.get("speaker", "某人")
            action = first.get("action", "")
            if action:
                parsed["narration"] = f"{speaker}{action}。"
            else:
                parsed["narration"] = f"{speaker}转过身来，看向你。"
            logger.debug(f"narration 为空但有对话，补充过渡叙事: {parsed['narration'][:50]}...")
        else:
            parsed["narration"] = "故事暂时陷入了停滞，等待着新的变数。"
            logger.warning("narration 和 dialogues 均为空，使用通用过渡叙事")

        return parsed

    def _default_response(self, narration_text: str) -> dict:
        """
        构建默认的 fallback 响应。
        当所有解析策略都失败时使用。
        """
        narration = narration_text.strip() if narration_text else ""
        if not narration:
            narration = "故事暂时陷入了停滞，等待着新的变数。"

        return {
            "narration": narration,
            "dialogues": [],
            "choices": [
                {"id": "c1", "text": "主动向对方搭话，尝试了解更多", "tone": "友善", "hint": ""},
                {"id": "c2", "text": "保持警惕，先确认自己的处境", "tone": "谨慎", "hint": ""},
            ],
            "scene_state": {},
            "affection_changes": [],
        }


# ---------------------------------------------------------------------------
# 便捷单例
# ---------------------------------------------------------------------------
response_parser = ResponseParser()
