"""
Narrator Engine - 数据库 ORM 模型包

统一导出所有模型，确保 SQLAlchemy 在建表时能发现它们。
PyCharm 提示: 在 Projects 面板中可以展开此包查看所有模型文件。

使用方式:
    from app.models import GameSession, DialogueLog, AffectionState, ...
"""

# 导入所有模型，确保它们被 SQLAlchemy 的 metadata 注册
from app.models.game_session import GameSession
from app.models.dialogue_log import DialogueLog
from app.models.affection import AffectionState
from app.models.scene_summary import SceneSummary
from app.models.memory import Memory
from app.models.player_profile import PlayerProfile
from app.models.save_slot import SaveSlot
from app.models.template_models import Template, TemplateCategory, TemplateCategoryMapping, User

# 导出列表，支持 from app.models import * 的写法
__all__ = [
    "GameSession",
    "DialogueLog",
    "AffectionState",
    "SceneSummary",
    "Memory",
    "PlayerProfile",
    "SaveSlot",
    "Template",
    "TemplateCategory",
    "TemplateCategoryMapping",
    "User",
]
