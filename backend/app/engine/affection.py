"""
Narrator Engine - 好感度计算器

职责：
  1. 根据玩家行为计算好感度变化
  2. 判定好感度等级 (陌生→友好→亲密→...)
  3. 检查是否触发好感度事件
  4. 管理秘密的渐进揭露

好感度变化有两个来源：
  - LLM 评估：让 AI 分析对话对好感度的影响（更自然）
  - 选项预设：选项自带的好感度效果（更可控）
  两者叠加，并限制单次变化幅度防止跳变。
"""

from loguru import logger

from app.models.affection import AffectionState


# =====================================================================
#  好感度等级定义（默认配置，角色模板可覆盖）
# =====================================================================
DEFAULT_RANKS = [
    {"range": [-50, -20], "label": "敌对",  "description": "充满警惕和敌意"},
    {"range": [-20, 0],   "label": "冷漠",  "description": "几乎不会注意到你"},
    {"range": [0, 20],    "label": "陌生",  "description": "礼貌但保持距离"},
    {"range": [20, 40],   "label": "认识",  "description": "会主动打招呼"},
    {"range": [40, 60],   "label": "友好",  "description": "愿意分享想法"},
    {"range": [60, 80],   "label": "亲密",  "description": "展露真实的一面"},
    {"range": [80, 100],  "label": "挚爱",  "description": "深层的信任与羁绊"},
]

# 单次好感度变化的最大绝对值（防止跳变）
MAX_DELTA_PER_TURN = 8


class AffectionCalculator:
    """
    好感度计算器。

    处理好感度变化的完整流程：
      1. 接收 LLM 评估的变化值
      2. 叠加选项预设的变化值
      3. 限制幅度（单次不超过 MAX_DELTA_PER_TURN）
      4. 应用到 AffectionState 模型
      5. 重新计算好感度等级
      6. 检查事件触发条件
    """

    def apply_changes(
        self,
        affection_state: AffectionState,
        llm_changes: list[dict],
        choice_effects: list[dict] | None = None,
    ) -> list[dict]:
        """
        应用好感度变化并返回变化明细。

        Args:
            affection_state: 角色的当前好感度状态 (ORM 模型)
            llm_changes: LLM 评估的变化列表
                [{"dimension": "trust", "delta": 3, "reason": "..."}]
            choice_effects: 选项预设的变化列表 (可选)
                [{"dimension": "intimacy", "delta": 5}]

        Returns:
            实际应用的变化列表 (含合并后的 delta)
        """
        # 合并 LLM 评估和选项预设的变化
        merged = self._merge_changes(llm_changes, choice_effects or [])

        applied_changes = []

        for change in merged:
            dimension = change.get("dimension", "")
            raw_delta = change.get("delta", 0)
            reason = change.get("reason", "")

            # 限制单次变化幅度
            clamped_delta = max(-MAX_DELTA_PER_TURN, min(MAX_DELTA_PER_TURN, raw_delta))

            if clamped_delta != raw_delta:
                logger.debug(
                    f"好感度变化被限制: {dimension} {raw_delta} → {clamped_delta}"
                )

            # 应用到模型
            if dimension in ("intimacy", "trust", "respect", "curiosity", "fear"):
                old_value = getattr(affection_state, dimension)
                new_value = affection_state.apply_delta(dimension, clamped_delta)

                applied_changes.append({
                    "character": affection_state.character_name,
                    "dimension": dimension,
                    "delta": round(new_value - old_value, 1),
                    "old_value": round(old_value, 1),
                    "new_value": round(new_value, 1),
                    "reason": reason,
                })

        # 重新计算好感度等级
        old_rank = affection_state.current_rank
        new_rank = self._calculate_rank(affection_state)
        affection_state.current_rank = new_rank

        if old_rank != new_rank:
            logger.info(
                f"🎭 {affection_state.character_name} 好感度等级变化: "
                f"{old_rank} → {new_rank}"
            )

        return applied_changes

    def _merge_changes(
        self,
        llm_changes: list[dict],
        choice_effects: list[dict],
    ) -> list[dict]:
        """
        合并两个来源的好感度变化。

        策略：同一维度的变化值相加。
        """
        # 以维度为 key 聚合
        merged_map: dict[str, dict] = {}

        for change in llm_changes + choice_effects:
            dim = change.get("dimension", "")
            delta = change.get("delta", 0)
            reason = change.get("reason", "")

            if dim in merged_map:
                merged_map[dim]["delta"] += delta
                if reason:
                    merged_map[dim]["reason"] += f"; {reason}"
            else:
                merged_map[dim] = {
                    "dimension": dim,
                    "delta": delta,
                    "reason": reason,
                }

        return list(merged_map.values())

    def _calculate_rank(self, state: AffectionState) -> str:
        """
        根据五维数值计算综合好感度等级。

        使用综合分数 (overall_score) 与等级区间匹配。
        """
        score = state.overall_score

        for rank_def in DEFAULT_RANKS:
            low, high = rank_def["range"]
            if low <= score < high:
                return rank_def["label"]

        # 分数超出范围时的边界处理
        if score >= 100:
            return DEFAULT_RANKS[-1]["label"]
        return DEFAULT_RANKS[0]["label"]

    def check_event_triggers(
        self,
        affection_state: AffectionState,
        available_events: list[dict],
    ) -> list[dict]:
        """
        检查是否有好感度事件被触发。

        Args:
            affection_state: 当前好感度状态
            available_events: 可用事件列表，每个事件包含 trigger_conditions

        Returns:
            被触发的事件列表
        """
        triggered = []

        for event in available_events:
            event_id = event.get("event_id", "")

            # 跳过已经触发过的事件
            if event_id in affection_state.triggered_events:
                continue

            conditions = event.get("trigger_conditions", {})
            if self._check_conditions(affection_state, conditions):
                triggered.append(event)
                # 记录为已触发
                affection_state.triggered_events.append(event_id)

        return triggered

    def _check_conditions(
        self,
        state: AffectionState,
        conditions: dict,
    ) -> bool:
        """
        检查好感度状态是否满足事件的触发条件。

        条件格式:
          {"intimacy": {"min": 40}, "trust": {"min": 35}}
        所有条件必须同时满足 (AND 逻辑)。
        """
        for dim, req in conditions.items():
            if dim not in ("intimacy", "trust", "respect", "curiosity", "fear"):
                continue

            current_value = getattr(state, dim, 0)
            min_val = req.get("min", 0)
            max_val = req.get("max", 100)

            if not (min_val <= current_value <= max_val):
                return False

        return True
