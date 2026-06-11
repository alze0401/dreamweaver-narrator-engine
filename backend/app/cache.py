"""
织梦绮谭 - Redis 缓存层

使用 redis.asyncio 实现热数据缓存：
  - 游戏会话状态缓存（避免频繁查 MySQL）
  - 最近对话历史缓存
  - 模板数据缓存
  - 分类列表缓存
"""

import json
from typing import Any

import redis.asyncio as aioredis
from loguru import logger

from app.config import get_settings


class RedisCache:
    """Redis 缓存管理器"""

    def __init__(self):
        self._pool: aioredis.Redis | None = None
        self._settings = get_settings()

    async def connect(self):
        """建立 Redis 连接池"""
        self._pool = aioredis.from_url(
            self._settings.redis_url,
            decode_responses=True,
            max_connections=20,
        )
        # 测试连接
        await self._pool.ping()
        logger.info(f"Redis 已连接: {self._settings.redis_host}:{self._settings.redis_port}")

    async def close(self):
        """关闭连接池"""
        if self._pool:
            await self._pool.aclose()
            logger.info("Redis 连接已关闭")

    @property
    def client(self) -> aioredis.Redis:
        if self._pool is None:
            raise RuntimeError("Redis 未初始化，请先调用 connect()")
        return self._pool

    # ======================== 通用操作 ========================

    async def get(self, key: str) -> Any:
        """获取缓存值（自动 JSON 反序列化）"""
        raw = await self.client.get(key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return raw

    async def set(self, key: str, value: Any, ttl: int | None = None):
        """设置缓存值（自动 JSON 序列化）"""
        serialized = json.dumps(value, ensure_ascii=False, default=str) if not isinstance(value, str) else value
        if ttl:
            await self.client.set(key, serialized, ex=ttl)
        else:
            await self.client.set(key, serialized)

    async def delete(self, key: str):
        """删除缓存"""
        await self.client.delete(key)

    async def delete_pattern(self, pattern: str):
        """批量删除匹配模式的缓存"""
        cursor = 0
        while True:
            cursor, keys = await self.client.scan(cursor=cursor, match=pattern, count=100)
            if keys:
                await self.client.delete(*keys)
            if cursor == 0:
                break

    # ======================== 业务缓存 ========================

    # --- 游戏会话 ---
    async def cache_game_session(self, session_id: str, data: dict):
        """缓存游戏会话状态"""
        ttl = self._settings.cache_ttl_game_session
        await self.set(f"session:{session_id}", data, ttl=ttl)

    async def get_game_session(self, session_id: str) -> dict | None:
        """获取缓存的游戏会话"""
        return await self.get(f"session:{session_id}")

    async def invalidate_session(self, session_id: str):
        """使游戏会话缓存失效"""
        await self.delete(f"session:{session_id}")

    # --- 对话历史 ---
    async def cache_recent_dialogues(self, session_id: str, dialogues: list):
        """缓存最近对话（用于工作记忆）"""
        ttl = self._settings.cache_ttl_dialogue
        await self.set(f"dialogues:{session_id}", dialogues, ttl=ttl)

    async def get_recent_dialogues(self, session_id: str) -> list | None:
        """获取缓存的最近对话"""
        return await self.get(f"dialogues:{session_id}")

    async def invalidate_dialogues(self, session_id: str):
        """使对话缓存失效"""
        await self.delete(f"dialogues:{session_id}")

    # --- 模板数据 ---
    async def cache_template(self, template_id: str, data: dict):
        """缓存单个模板"""
        ttl = self._settings.cache_ttl_template
        await self.set(f"template:{template_id}", data, ttl=ttl)

    async def get_template(self, template_id: str) -> dict | None:
        """获取缓存的模板"""
        return await self.get(f"template:{template_id}")

    async def invalidate_templates(self):
        """使所有模板相关缓存失效"""
        await self.delete_pattern("template:*")

    # --- 分类列表 ---
    async def cache_categories(self, data: list):
        """缓存分类列表"""
        await self.set("categories:all", data, ttl=3600)

    async def get_categories(self) -> list | None:
        return await self.get("categories:all")


# ---------------------------------------------------------------------------
# 全局单例
# ---------------------------------------------------------------------------
cache = RedisCache()
