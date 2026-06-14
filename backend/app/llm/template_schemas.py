"""
AI 模板生成 - Pydantic 结构化输出模型

配合 LangChain .with_structured_output() 使用，
确保 LLM 输出严格符合预定义的数据结构。
"""

from pydantic import BaseModel, Field


# =====================================================================
#  世界观 (World) 模板
# =====================================================================

class WorldTemplateOutput(BaseModel):
    """AI 生成的世界观模板数据"""
    name: str = Field(description="模板名称，简洁有吸引力")
    description: str = Field(description="模板的简短描述，一两句话概括世界观特色")
    era: str = Field(description="时代背景，如中世纪、近未来、上古仙侠纪元")
    genre: list[str] = Field(description="类型标签列表，如 ['奇幻', '冒险', '魔法']")
    setting_description: str = Field(description="详细的世界设定描述，包括历史、地理、文化等")
    rules: list[str] = Field(description="世界规则列表，每条规则独立一行")


# =====================================================================
#  角色 (Character) 模板
# =====================================================================

class SpeechStyle(BaseModel):
    """角色的说话风格"""
    tone: str = Field(description="说话风格描述，如 '温柔但偶尔毒舌'、'礼貌而疏离'")


class Personality(BaseModel):
    """角色的性格特征"""
    archetype: str = Field(description="性格原型，如 '傲娇'、'温柔学姐'、'腹黑王子'")
    mbti: str = Field(description="MBTI 类型，如 INTJ、ENFP")
    likes: list[str] = Field(description="喜好列表")
    dislikes: list[str] = Field(description="厌恶列表")
    speech_style: SpeechStyle = Field(description="说话风格")


class CharacterData(BaseModel):
    """角色核心数据"""
    full_name: str = Field(description="角色全名")
    personality: Personality = Field(description="性格特征")
    relationships: dict = Field(default_factory=dict, description="人际关系配置")


class AffectionConfig(BaseModel):
    """好感度初始配置"""
    initial_value: int = Field(default=0, description="好感度初始值")


class CharacterTemplateOutput(BaseModel):
    """AI 生成的角色模板数据"""
    name: str = Field(description="模板名称")
    description: str = Field(description="模板的简短描述，概括角色特色")
    character: CharacterData = Field(description="角色核心数据")
    affection_config: AffectionConfig = Field(
        default_factory=lambda: AffectionConfig(initial_value=0),
        description="好感度初始配置",
    )


# =====================================================================
#  剧本 (Scenario) 模板
# =====================================================================

class OpeningScene(BaseModel):
    """开场场景"""
    location: str = Field(description="开场地点")
    time: str = Field(description="开场时间，如 '春日清晨'、'深夜'")
    weather: str = Field(default="", description="天气状况")


class ScenarioData(BaseModel):
    """剧本核心数据"""
    premise: str = Field(description="故事前提，描述核心冲突和背景")
    opening_scene: OpeningScene = Field(description="开场场景")
    chapter_beats: list[str] = Field(
        default_factory=list,
        description="章节节奏大纲",
    )
    plot_hooks: list[str] = Field(description="剧情钩子列表，吸引玩家继续阅读")
    estimated_chapters: int = Field(default=5, description="预计章节数")


class ScenarioTemplateOutput(BaseModel):
    """AI 生成的剧本模板数据"""
    name: str = Field(description="模板名称")
    description: str = Field(description="模板的简短描述，概括剧本特色")
    scenario: ScenarioData = Field(description="剧本核心数据")


# =====================================================================
#  类型映射
# =====================================================================

TEMPLATE_TYPE_TO_MODEL = {
    "world": WorldTemplateOutput,
    "character": CharacterTemplateOutput,
    "scenario": ScenarioTemplateOutput,
}
