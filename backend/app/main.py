"""
织梦绮谭 - FastAPI 应用入口

职责：
  1. 创建 FastAPI 实例，配置 CORS、元数据
  2. 注册所有 API 路由
  3. 管理应用生命周期（启动时初始化数据库）
  4. 提供健康检查端点

启动方式：
  cd backend
  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
"""

import sys
import io
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

# 修复 Windows 控制台 GBK 编码问题：让 loguru 使用 utf-8 输出
# uvicorn reload 模式下 sys.stderr.buffer 可能已关闭，需要容错处理
if sys.platform == "win32":
    logger.remove()
    try:
        _stderr_wrapper = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
        logger.add(
            _stderr_wrapper,
            level="DEBUG",
            format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        )
    except (ValueError, OSError):
        # reload 子进程中 stderr 可能已关闭，回退到默认输出
        logger.add(sys.stderr, level="DEBUG")

from app.config import get_settings
from app.database import init_db, get_db
from app.cache import cache
from app.api import game, character, template, save, dialogue, category


# ---------------------------------------------------------------------------
# 应用生命周期管理 —— 启动和关闭时执行的逻辑
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan 事件处理器。
    - 启动时：初始化数据库、检查模板目录
    - 关闭时：清理资源（当前无需额外操作）
    """
    settings = get_settings()

    # ---- 启动阶段 ----
    logger.info("[织梦绮谭] starting...")

    # 确保数据目录存在
    settings.saves_dir.mkdir(parents=True, exist_ok=True)
    Path(settings.chroma_persist_dir).mkdir(parents=True, exist_ok=True)

    # 初始化数据库（自动建表）
    try:
        await init_db()
        logger.info("MySQL database initialized")
    except Exception as e:
        logger.error(f"数据库初始化失败（后端仍可启动，但API调用可能报错）: {e}")

    # 初始化 Redis
    try:
        await cache.connect()
    except Exception as e:
        logger.warning(f"Redis 连接失败（缓存功能不可用）: {e}")

    logger.info("[织梦绮谭] started!")

    yield  # ← 应用运行中...

    # ---- 关闭阶段 ----
    await cache.close()
    logger.info("[织梦绮谭] shutting down...")


# ---------------------------------------------------------------------------
# 创建 FastAPI 实例
# ---------------------------------------------------------------------------
app = FastAPI(
    title="织梦绮谭 API",
    description=(
        "Galgame + AI 大模型叙事引擎。\n\n"
        "提供游戏流程管理、角色管理、模板管理、存档管理和对话交互等 API。"
    ),
    version="0.1.0",
    lifespan=lifespan,
    # 自动生成 OpenAPI 文档
    docs_url="/docs",         # Swagger UI
    redoc_url="/redoc",       # ReDoc
)


# ---------------------------------------------------------------------------
# CORS 中间件 —— 允许前端跨域访问
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],           # 开发阶段允许所有来源，生产环境需限制
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# 注册 API 路由
# ---------------------------------------------------------------------------
app.include_router(game.router,      prefix="/api/game",      tags=["游戏流程"])
app.include_router(character.router, prefix="/api/game",      tags=["角色管理"])
app.include_router(category.router,  prefix="/api/categories", tags=["模板分类"])
app.include_router(template.router,  prefix="/api/templates", tags=["模板管理"])
app.include_router(save.router,      prefix="/api/saves",     tags=["存档管理"])
app.include_router(dialogue.router,  prefix="/api/dialogue",  tags=["对话交互"])


# ---------------------------------------------------------------------------
# 根路径 —— 健康检查
# ---------------------------------------------------------------------------
@app.get("/", tags=["系统"])
async def root():
    """健康检查端点，确认服务正在运行"""
    return {
        "name": "织梦绮谭",
        "version": "0.1.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/api/health", tags=["系统"])
async def health_check(db: AsyncSession = Depends(get_db)):
    """详细健康检查：检测 MySQL 连接 + Redis 连接"""
    from sqlalchemy import text

    result = {"mysql": "unknown", "redis": "unknown", "tables": []}

    # MySQL
    try:
        row = await db.execute(text("SELECT 1"))
        result["mysql"] = "ok"
    except Exception as e:
        result["mysql"] = f"error: {e}"

    # 检查关键表是否存在
    try:
        row = await db.execute(text("SHOW TABLES"))
        result["tables"] = [r[0] for r in row.fetchall()]
    except Exception as e:
        result["tables_error"] = str(e)

    # Redis
    try:
        from app.cache import cache
        if cache._redis:
            await cache._redis.ping()
            result["redis"] = "ok"
        else:
            result["redis"] = "not connected"
    except Exception as e:
        result["redis"] = f"error: {e}"

    return result



if __name__ == "__main__":
    import os
    import uvicorn

    # 确保 backend/ 目录在 Python 路径中，这样 app.xxx 才能被正确导入
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)

    settings = get_settings()
    print("=" * 50)
    print("  织梦绮谭")
    print("=" * 50)
    print(f"  http://{settings.app_host}:{settings.app_port}")
    print(f"  http://{settings.app_host}:{settings.app_port}/docs")
    print("=" * 50)
    print()
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_debug,
    )
