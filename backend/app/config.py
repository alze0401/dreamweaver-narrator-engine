"""
织梦绮谭 - 全局配置模块

从 .env 文件和环境变量中加载所有配置项。
支持 MySQL + Redis + ChromaDB + DeepSeek API。
"""

from pathlib import Path
from functools import lru_cache

from pydantic_settings import BaseSettings
from pydantic import Field


# 项目根目录（backend/ 所在目录）
BASE_DIR = Path(__file__).resolve().parent.parent


class AppSettings(BaseSettings):
    """应用全局配置，自动从 .env 文件和环境变量加载"""

    # ---- DeepSeek API ----
    deepseek_api_key: str = Field(
        default="sk-placeholder",
        description="DeepSeek API 密钥"
    )
    deepseek_base_url: str = Field(
        default="https://api.deepseek.com",
        description="DeepSeek API 基础 URL"
    )
    deepseek_model: str = Field(
        default="deepseek-v4-pro",
        description="使用的模型名称"
    )

    # ---- 应用服务 ----
    app_host: str = Field(default="0.0.0.0")
    app_port: int = Field(default=8000, ge=1, le=65535)
    app_debug: bool = Field(default=True)

    # ---- MySQL 数据库 ----
    mysql_host: str = Field(default="127.0.0.1")
    mysql_port: int = Field(default=3306)
    mysql_user: str = Field(default="narrator")
    mysql_password: str = Field(default="narrator2024")
    mysql_database: str = Field(default="narrator_engine")

    @property
    def database_url(self) -> str:
        """构建 MySQL 异步连接字符串"""
        return (
            f"mysql+aiomysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"
            f"?charset=utf8mb4"
        )

    # ---- Redis ----
    redis_host: str = Field(default="127.0.0.1")
    redis_port: int = Field(default=6379)
    redis_password: str = Field(default="narrator2024")
    redis_db: int = Field(default=0)

    @property
    def redis_url(self) -> str:
        """构建 Redis 连接字符串"""
        return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"

    # ---- ChromaDB ----
    chroma_persist_dir: str = Field(
        default=str(BASE_DIR / "data" / "chroma"),
        description="ChromaDB 向量数据持久化目录"
    )

    # ---- LLM 生成参数 ----
    llm_temperature: float = Field(default=0.75, ge=0.0, le=2.0)
    llm_max_tokens: int = Field(default=2048, ge=256, le=8192)
    llm_top_p: float = Field(default=0.9, ge=0.0, le=1.0)

    # ---- 记忆系统 ----
    memory_max_working_turns: int = Field(default=12)
    memory_max_episodic_summaries: int = Field(default=30)
    memory_min_importance: int = Field(default=6, ge=1, le=10)
    memory_vector_search_top_k: int = Field(default=8)

    # ---- Redis 缓存 TTL（秒） ----
    cache_ttl_game_session: int = Field(default=3600)
    cache_ttl_template: int = Field(default=1800)
    cache_ttl_dialogue: int = Field(default=300)

    # ---- JWT 认证 ----
    jwt_secret_key: str = Field(default="dreamweaver-jwt-secret-key-2026-change-me")
    jwt_algorithm: str = Field(default="HS256")
    jwt_expire_minutes: int = Field(default=1440)  # 24 小时

    # ---- MinIO 对象存储 ----
    minio_endpoint: str = Field(default="127.0.0.1:9000", description="MinIO 服务地址")
    minio_access_key: str = Field(default="minioadmin", description="MinIO 访问密钥")
    minio_secret_key: str = Field(default="minioadmin123", description="MinIO 密钥")
    minio_secure: bool = Field(default=False, description="是否使用 HTTPS")
    minio_bucket: str = Field(default="dreamweaver-assets", description="存储桶名称")
    minio_public_url: str = Field(
        default="http://127.0.0.1:9000/dreamweaver-assets",
        description="公开访问的基础 URL（拼接 object_name 即可访问）"
    )

    # ---- 文件上传限制 ----
    upload_max_image_mb: int = Field(default=5, description="图片上传大小限制 (MB)")
    upload_max_audio_mb: int = Field(default=20, description="音频上传大小限制 (MB)")

    # ---- 路径配置 ----
    @property
    def prompts_dir(self) -> Path:
        """Prompt 模板文件目录"""
        return BASE_DIR / "prompts"

    @property
    def saves_dir(self) -> Path:
        """存档文件目录"""
        return BASE_DIR / "data" / "saves"

    class Config:
        env_file = str(BASE_DIR / ".env")
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> AppSettings:
    """获取全局配置单例"""
    return AppSettings()
