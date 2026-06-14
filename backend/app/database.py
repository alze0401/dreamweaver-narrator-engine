"""
织梦绮谭 - 数据库连接与会话管理 (MySQL 版)

职责：
  1. 创建异步 SQLAlchemy 引擎 (aiomysql)
  2. 管理异步会话 (AsyncSession) 的生命周期
  3. 提供 FastAPI 依赖注入用的 get_db() 生成器
  4. 应用启动时自动建表 + 自动补充缺失列
"""

from sqlalchemy import text, inspect as sa_inspect
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
)
from sqlalchemy.orm import DeclarativeBase
from loguru import logger

from app.config import get_settings


# ---------------------------------------------------------------------------
# 1. 声明式基类
# ---------------------------------------------------------------------------
class Base(DeclarativeBase):
    """SQLAlchemy 2.0 声明式基类"""
    pass


# ---------------------------------------------------------------------------
# 2. 异步引擎 (MySQL + aiomysql)
# ---------------------------------------------------------------------------
_settings = get_settings()

engine = create_async_engine(
    _settings.database_url,
    echo=_settings.app_debug,
    pool_size=10,
    max_overflow=20,
    pool_recycle=3600,       # MySQL 默认 8h 超时，1h 回收连接
    pool_pre_ping=False,     # aiomysql 兼容问题，关闭自动 ping
)


# ---------------------------------------------------------------------------
# 3. 异步会话工厂
# ---------------------------------------------------------------------------
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ---------------------------------------------------------------------------
# 4. FastAPI 依赖注入
# ---------------------------------------------------------------------------
async def get_db():
    """
    每个请求获得独立的 Session，请求结束后自动关闭。
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ---------------------------------------------------------------------------
# 5. 初始化函数（建表 + 自动补充缺失列）
# ---------------------------------------------------------------------------

def _get_column_type_string(col):
    """将 SQLAlchemy Column 对象转换为 MySQL 兼容的类型字符串"""
    try:
        from sqlalchemy.dialects import mysql
        compiled = col.type.compile(dialect=mysql.dialect())
        return compiled
    except Exception:
        return "TEXT"


async def _auto_migrate_columns(conn):
    """
    检测已有表中缺失的列，并自动补充。
    解决 CREATE TABLE IF NOT EXISTS 不会修改已有表结构的问题。
    """
    # 先确保所有 ORM model 都已导入（这样 Base.metadata 才完整）
    try:
        import app.models  # noqa: F401
    except Exception:
        pass

    # 获取数据库中已有的表和列信息
    result = await conn.execute(text(
        "SELECT TABLE_NAME, COLUMN_NAME "
        "FROM INFORMATION_SCHEMA.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE()"
    ))
    db_columns = {}  # {table_name: set(column_names)}
    for row in result.fetchall():
        table_name = row[0]
        col_name = row[1]
        if table_name not in db_columns:
            db_columns[table_name] = set()
        db_columns[table_name].add(col_name)

    # 遍历 ORM 中定义的所有表和列
    for table in Base.metadata.sorted_tables:
        table_name = table.name
        if table_name not in db_columns:
            # 整张表不存在，create_all 应该已经创建了
            continue

        existing_cols = db_columns[table_name]
        for col in table.columns:
            col_name = col.name
            if col_name not in existing_cols:
                # 该列在数据库中不存在，需要 ALTER TABLE 添加
                type_str = _get_column_type_string(col)

                # 构建 NULL / NOT NULL 子句
                nullable = col.nullable
                if nullable:
                    null_clause = "NULL"
                else:
                    null_clause = "NOT NULL"

                # 构建 DEFAULT 子句
                default_clause = ""
                if col.default is not None and col.default.is_scalar:
                    val = col.default.arg
                    if isinstance(val, str):
                        default_clause = f"DEFAULT '{val}'"
                    elif isinstance(val, bool):
                        default_clause = f"DEFAULT {1 if val else 0}"
                    elif isinstance(val, (int, float)):
                        default_clause = f"DEFAULT {val}"
                    elif val is None:
                        default_clause = "DEFAULT NULL"
                elif nullable:
                    default_clause = "DEFAULT NULL"

                # JSON 类型特殊处理
                if "JSON" in type_str.upper():
                    type_str = "JSON"
                    if nullable or (col.default is not None and col.default.is_scalar and col.default.arg is None):
                        null_clause = "NULL"
                        default_clause = "DEFAULT NULL"
                    elif col.default is not None and col.default.is_scalar:
                        # JSON 列 NOT NULL 需要有默认值
                        val = col.default.arg
                        if callable(val):
                            try:
                                val = val()
                            except Exception:
                                val = []
                        import json
                        json_str = json.dumps(val) if not isinstance(val, str) else val
                        default_clause = f"DEFAULT ('{json_str}')"
                        null_clause = "NOT NULL"
                    else:
                        null_clause = "NULL"
                        default_clause = "DEFAULT NULL"

                comment_str = ""
                if col.comment:
                    # 清理注释中的特殊字符（换行、单引号）
                    cleaned = col.comment.replace("\n", " ").replace("\r", "").replace("'", "\\'")
                    comment_str = f"COMMENT '{cleaned}'"

                alter_sql = (
                    f"ALTER TABLE `{table_name}` "
                    f"ADD COLUMN `{col_name}` {type_str} "
                    f"{null_clause} {default_clause} {comment_str}"
                ).strip()

                logger.info(f"[auto-migrate] {table_name}.{col_name} => {type_str}")
                try:
                    await conn.execute(text(alter_sql))
                except Exception as e:
                    logger.warning(f"[auto-migrate] 添加列失败 {table_name}.{col_name}: {e}")

    logger.info("[auto-migrate] 列检查完成")


async def init_db():
    """
    创建数据库中所有表（如果不存在），并自动补充已有表中缺失的列。
    正式环境建议使用 init.sql 初始化。
    """
    async with engine.begin() as conn:
        # 第一步：建表（CREATE TABLE IF NOT EXISTS）
        await conn.run_sync(Base.metadata.create_all)
        # 第二步：检测并补充缺失的列
        await _auto_migrate_columns(conn)

    # 第三步：确保"自定义&其他"分类存在
    await _ensure_custom_category()


async def _ensure_custom_category():
    """确保 template_categories 中存在 '自定义&其他' 分类"""
    try:
        async with async_session_factory() as session:
            from app.models.template_models import TemplateCategory
            from sqlalchemy import select

            stmt = select(TemplateCategory).where(TemplateCategory.code == "custom")
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()

            if not existing:
                new_cat = TemplateCategory(
                    code="custom",
                    name="自定义&其他",
                    description="用户自定义模板或不属于其他分类的模板",
                    icon="Palette",
                    sort_order=99,
                )
                session.add(new_cat)
                await session.commit()
                logger.info("[seed] 已自动插入 '自定义&其他' 分类")
            else:
                logger.debug("[seed] '自定义&其他' 分类已存在，跳过")
    except Exception as e:
        logger.warning(f"[seed] 插入 '自定义&其他' 分类失败: {e}")
