"""
AI 叙事引擎 - Pydantic 结构化输出模型

配合 LangChain .with_structured_output() 使用，
确保 LLM 输出严格符合预定义的数据结构，每个字段不为空。
"""

from pydantic import BaseModel, Field, field_validator


class DialogueLine(BaseModel):
    """
    一句角色台词。

    角色的所有对白/台词都必须放在这里，绝对不能写在 narration 中。
    """
    speaker: str = Field(
        description="角色名（只能是具体角色名字，如「凝光」「甘雨」「酒馆老板」。禁止使用情感词、动作词、描述词作为 speaker）"
    )
    text: str = Field(
        min_length=1,
        description="角色的台词/对白内容。这是角色说的话，不能为空。例如：「这里是璃月，契约与贸易之都。」"
    )
    emotion: str = Field(
        description="角色说话时的情感/语气标签（中文）。如：温和、冷淡、害羞、惊讶、愤怒、从容、玩味、认真"
    )
    action: str = Field(
        default="",
        description="角色说话时的动作/表情描写。如：双手交叠身前、微微侧首、捋了捋袖口"
    )

    @field_validator("speaker")
    @classmethod
    def speaker_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("speaker 不能为空")
        return v.strip()

    @field_validator("emotion")
    @classmethod
    def emotion_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            return "平静"
        return v.strip()


class Choice(BaseModel):
    """玩家选项"""
    id: str = Field(default="", description="选项 ID，如 c1、c2、c3。可省略，系统会自动生成")
    text: str = Field(min_length=1, description="选项文本，必须与当前剧情相关，不能是空泛的通用选项")
    tone: str = Field(default="认真", description="语气标签，如：坦诚、谨慎、大胆、幽默")
    hint: str = Field(default="", alias="affection_hint", description="简短提示，帮助玩家理解选项的影响方向")

    @field_validator("id", mode="before")
    @classmethod
    def coerce_id_to_str(cls, v) -> str:
        if v is None or (isinstance(v, str) and not v.strip()):
            return ""  # parse_response_node 中 ensure_choices 会补充
        return str(v).strip()

    @field_validator("hint", mode="before")
    @classmethod
    def normalize_hint(cls, v) -> str:
        if v is None:
            return ""
        return str(v).strip()


class SceneState(BaseModel):
    """当前场景状态"""
    location: str = Field(description="当前具体地点名称，如：教室走廊、神社石阶")
    time: str = Field(description="当前具体时间，如：黄昏、深夜、清晨")
    mood: str = Field(default="平静", description="氛围描述，如：紧张、温馨、神秘")

    @field_validator("mood")
    @classmethod
    def mood_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            return "平静"
        return v.strip()


class AffectionChange(BaseModel):
    """好感度变化记录"""
    character: str = Field(description="角色显示名（与 speaker 一致）")
    dimension: str = Field(description="维度，只能是: intimacy, trust, respect, curiosity, fear 之一")
    delta: int = Field(description="变化值，范围 -5 到 +5")
    reason: str = Field(min_length=1, description="变化原因，不能为空")


class NarratorOutput(BaseModel):
    """
    AI 叙事引擎的完整输出。

    【最重要的规则】narration 和 dialogues 必须严格分离:
    - narration: 只放环境描写、旁白叙述、动作过渡、场景切换。禁止包含任何角色台词。
    - dialogues: 角色的所有对白/台词必须放在这里。禁止在 narration 中写角色台词。

    正确示例:
      narration: "晨光洒落，雾气渐散。凝光收回烟斗，嘴角微扬。甘雨轻轻颔首。"
      dialogues: [
        {"speaker": "凝光", "text": "倒是直爽。璃月港近来确实有几桩事务需要人手。", "emotion": "略带赞许", "action": "捋了捋袖口"},
        {"speaker": "甘雨", "text": "若你决定前往璃月，我可以作为向导带你入城。", "emotion": "温和而正式", "action": "轻声补充"}
      ]

    错误示例（绝对禁止）:
      narration: "[凝光] (捋了捋袖口) 倒是直爽... [甘雨] 若你决定前往璃月..."
      dialogues: []  ← 这是错误的！台词必须放在 dialogues 中！
    """
    narration: str = Field(
        description=(
            "纯叙事文本：仅包含环境描写、旁白叙述、动作过渡、场景切换描写。"
            "绝对禁止包含角色台词/对白。"
            "禁止使用 [角色名] 或 【角色名】 标签。"
            "禁止出现 [场景:] 标签（场景信息放在 scene_state 字段）。"
            "角色的所有说话内容必须放在 dialogues 数组中。"
        )
    )
    dialogues: list[DialogueLine] = Field(
        default_factory=list,
        description=(
            "角色的台词/对白列表。角色说的每一句话都必须放在这里，不能写在 narration 中。"
            "每条的 text 不能为空。"
            "当角色有说话/对白时，此数组不能为空。"
        ),
    )
    choices: list[Choice] = Field(
        default_factory=list,
        description="玩家选项列表（3-4 个），必须与当前剧情相关，不能是空泛通用选项",
    )
    scene_state: SceneState = Field(description="当前场景状态（地点、时间、氛围）")
    affection_changes: list[AffectionChange] = Field(
        default_factory=list,
        description="好感度变化记录，不能为空数组，每轮至少 1 条",
    )
