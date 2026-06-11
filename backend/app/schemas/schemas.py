"""
Narrator Engine - Pydantic 请求/响应模型

定义 API 层的数据传输对象 (DTO)。
请求体用 Request 后缀，响应用 Response 后缀。
所有模型使用 Pydantic v2 语法。
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# =====================================================================
#  游戏会话 (Game)
# =====================================================================

class GameStartRequest(BaseModel):
    """开始新游戏的请求体"""
    world_template_id: str = Field(..., description="世界观模板ID")
    scenario_template_id: str = Field(..., description="剧本模板ID")
    player_name: str = Field(default="主角", max_length=64, description="玩家角色名")
    player_data: dict = Field(default_factory=dict, description="玩家自定义信息 (年龄/背景等)")
    character_template_ids: list[str] = Field(
        default_factory=list,
        description="要启用的角色模板ID列表"
    )


class GameStartResponse(BaseModel):
    """新游戏创建后的响应"""
    session_id: str = Field(..., description="游戏会话ID")
    opening_narration: str = Field(..., description="开场叙事文本")
    opening_dialogues: list[dict] = Field(default_factory=list, description="开场对话列表")
    choices: list[dict] = Field(default_factory=list, description="开场选项列表")
    scene_state: dict = Field(default_factory=dict, description="当前场景状态")
    updated_characters: list[dict] = Field(
        default_factory=list,
        description="角色列表（含好感度数据和名字揭示状态），用于前端刷新角色面板"
    )
    progress: dict = Field(
        default_factory=lambda: {"chapter": 1, "total_chapters": 5, "current_turn": 0},
        description="进度信息 {chapter, total_chapters, current_turn}"
    )


class GameStateResponse(BaseModel):
    """游戏状态查询的响应"""
    session_id: str
    player_name: str
    chapter: int
    total_chapters: int = Field(default=4, description="剧本预估总章节数")
    current_scene: str
    world_state: dict
    character_count: int = Field(description="当前角色数量")
    dialogue_count: int = Field(description="对话总轮次")
    total_turns: int = Field(default=0, description="总对话轮次")
    created_at: datetime
    updated_at: datetime


# =====================================================================
#  对话交互 (Dialogue)
# =====================================================================

class DialogueAdvanceRequest(BaseModel):
    """推进对话的请求体"""
    input_type: str = Field(
        ..., pattern="^(choice|free)$",
        description="输入类型: choice=选择选项, free=自由输入"
    )
    content: str = Field(
        ..., min_length=1,
        description="选项ID 或 自由输入的文本"
    )
    metadata: dict = Field(
        default_factory=dict,
        description="附加元数据 (如玩家情绪标签)"
    )


class DialogueChoice(BaseModel):
    """AI 生成的一个选项"""
    id: str = Field(..., description="选项ID (如 c1, c2)")
    text: str = Field(..., description="选项文本")
    tone: str = Field(default="", description="选项的语气/风格标签")
    hint: str = Field(default="", description="选项的简短提示")


class DialogueLine(BaseModel):
    """一句角色台词"""
    speaker: str = Field(..., description="说话人: narrator / 角色名")
    text: str = Field(..., description="台词文本")
    emotion: str = Field(default="", description="情感标签")
    action: str = Field(default="", description="动作/表情描写")


class DialogueAdvanceResponse(BaseModel):
    """AI 生成的完整对话轮次响应"""
    narration: str = Field(..., description="叙事文本 (环境描写、旁白)")
    dialogues: list[DialogueLine] = Field(default_factory=list, description="角色台词列表")
    choices: list[DialogueChoice] = Field(default_factory=list, description="玩家可选选项")
    scene_state: dict = Field(default_factory=dict, description="场景状态更新")
    affection_changes: list[dict] = Field(
        default_factory=list,
        description="本轮好感度变化 [{character, dimension, delta, reason}]"
    )
    updated_characters: list[dict] = Field(
        default_factory=list,
        description="更新后的角色列表（含最新好感度数据），用于前端刷新雷达图"
    )
    progress: dict = Field(
        default_factory=lambda: {"chapter": 1, "total_chapters": 5, "current_turn": 0},
        description="进度信息 {chapter, total_chapters, current_turn}"
    )


# =====================================================================
#  角色 (Character)
# =====================================================================

class CharacterSummary(BaseModel):
    """角色摘要信息 (列表展示用, 含五维数值供雷达图)"""
    character_id: str
    character_name: str
    current_rank: str
    relationship_label: str
    overall_score: float
    intimacy: float = 0.0
    trust: float = 0.0
    respect: float = 0.0
    curiosity: float = 0.0
    fear: float = 0.0


class CharacterDetail(BaseModel):
    """角色详细信息 (含好感度数值)"""
    character_id: str
    character_name: str
    intimacy: float
    trust: float
    respect: float
    curiosity: float
    fear: float
    current_rank: str
    relationship_label: str
    overall_score: float
    triggered_events: list
    known_secrets: list


# =====================================================================
#  模板 (Template)
# =====================================================================

class TemplateSummary(BaseModel):
    """模板摘要 (列表展示用)"""
    template_id: str
    template_type: str = Field(description="模板类型: world / character / scenario")
    name: str
    is_preset: bool
    description: str = ""
    tags: list[str] = Field(default_factory=list)


class TemplateDetail(BaseModel):
    """模板完整详情"""
    template_id: str
    template_type: str
    name: str
    version: str
    is_preset: bool
    description: str = ""
    data: dict = Field(description="模板的完整数据 (世界观/角色/剧本配置)")


class TemplateCreateRequest(BaseModel):
    """创建自定义模板的请求"""
    template_type: str = Field(..., pattern="^(world|character|scenario)$")
    name: str = Field(..., max_length=128)
    description: str = Field(default="")
    data: dict = Field(..., description="模板配置数据")
    clone_from: Optional[str] = Field(None, description="从哪个模板克隆 (可选)")


# =====================================================================
#  存档 (Save)
# =====================================================================

class SaveCreateRequest(BaseModel):
    """创建存档的请求"""
    slot_number: int = Field(..., ge=1, le=20, description="存档位 (1-20)")
    title: str = Field(default="", max_length=128)


class SaveSlotResponse(BaseModel):
    """存档位信息"""
    id: str
    slot_number: int
    auto_save: bool
    title: str
    description: str
    session_id: str
    created_at: datetime


class SaveLoadRequest(BaseModel):
    """加载存档的请求"""
    save_id: str = Field(..., description="要加载的存档ID")


# =====================================================================
#  通用响应
# =====================================================================

class MessageResponse(BaseModel):
    """通用消息响应"""
    success: bool = True
    message: str = ""
    data: Optional[dict] = None
