"""
织梦绮谭 - 记忆管理器

职责：
  1. 管理三层记忆架构（工作记忆 / 情景记忆 / 语义记忆）
  2. 对话结束后异步提取和存储记忆
  3. 构建 Prompt 时检索相关记忆作为上下文
  4. 管理记忆衰减和遗忘机制

三层记忆:
  Layer 1 - 工作记忆: 最近 N 轮对话（直接取数据库）
  Layer 2 - 情景记忆: 场景压缩摘要（SceneSummary 表）
  Layer 3 - 语义记忆: 关键事实向量检索（ChromaDB + Memory 表）
"""

import json
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.config import get_settings
from app.models.dialogue_log import DialogueLog
from app.models.scene_summary import SceneSummary
from app.models.memory import Memory


class MemoryManager:
    """
    记忆管理器。

    负责记忆的存储、检索和生命周期管理。
    """

    def __init__(self):
        """初始化记忆管理器"""
        self._settings = get_settings()
        self._chroma_collection = None  # 延迟初始化 ChromaDB

    # =================================================================
    #  Layer 1: 工作记忆 —— 最近 N 轮对话
    # =================================================================

    async def get_working_memory(
        self,
        db: AsyncSession,
        session_id: str,
    ) -> list[dict]:
        """
        获取工作记忆（最近 N 轮对话）。

        这是最直接的记忆层，直接作为 LLM 的 messages 发送。
        narrator 的 JSON 响应会被转为可读的叙事文本，确保 LLM 看到的是
        自然语言而非机器格式，从而维持多角色场景的连贯性。

        Args:
            db: 数据库会话
            session_id: 游戏会话ID

        Returns:
            最近对话记录列表，每条含 speaker/content/emotion/action
        """
        limit = self._settings.memory_max_working_turns

        stmt = (
            select(DialogueLog)
            .where(DialogueLog.session_id == session_id)
            .order_by(DialogueLog.turn_number.desc())
            .limit(limit * 2)  # 每轮有 AI 和 Player 两条记录，所以乘2
        )
        result = await db.execute(stmt)
        dialogues = list(reversed(result.scalars().all()))

        # 格式化为 Prompt 可用的格式
        formatted = []
        for d in dialogues:
            content = d.content or ""

            if d.speaker == "narrator":
                # 将 narrator 的 JSON 响应转为可读叙事文本
                content = self._format_narrator_content(content)

            formatted.append({
                "speaker": d.speaker,
                "content": content,
                "emotion": d.emotion or "",
                "action": d.action or "",
            })

        return formatted

    @staticmethod
    def _format_narrator_content(raw_content: str) -> str:
        """
        将 narrator 的 JSON 响应转换为可读的叙事文本。
        
        这样 LLM 在对话历史中看到的是自然语言，而不是原始 JSON，
        能更好地理解之前发生了什么、哪些角色说了什么话。
        """
        if not raw_content:
            return ""
        
        try:
            data = json.loads(raw_content)
        except (json.JSONDecodeError, TypeError):
            # 不是 JSON，直接返回原文
            return raw_content

        parts = []

        # 叙事描写
        narration = data.get("narration", "")
        if narration:
            parts.append(f"[旁白] {narration}")

        # 角色台词
        for d in data.get("dialogues", []):
            speaker = d.get("speaker", "???")
            text = d.get("text", "")
            emotion = d.get("emotion", "")
            action = d.get("action", "")
            line = f"[{speaker}]"
            if action:
                line += f" ({action})"
            if emotion:
                line += f" [{emotion}]"
            line += f": {text}"
            parts.append(line)

        # 场景状态变化
        scene = data.get("scene_state", {})
        if scene:
            loc = scene.get("location", "")
            time = scene.get("time", "")
            mood = scene.get("mood", "")
            scene_parts = []
            if loc:
                scene_parts.append(f"地点:{loc}")
            if time:
                scene_parts.append(f"时间:{time}")
            if mood:
                scene_parts.append(f"氛围:{mood}")
            if scene_parts:
                parts.append(f"[场景: {', '.join(scene_parts)}]")

        return "\n".join(parts) if parts else raw_content

    # =================================================================
    #  Layer 2: 情景记忆 —— 场景压缩摘要
    # =================================================================

    async def get_episodic_memory(
        self,
        db: AsyncSession,
        session_id: str,
        current_chapter: int = 1,
    ) -> list[dict]:
        """
        获取情景记忆（场景摘要）。

        优先返回当前章节的摘要，然后是最近章节的。

        Args:
            db: 数据库会话
            session_id: 游戏会话ID
            current_chapter: 当前章节号

        Returns:
            场景摘要列表
        """
        limit = self._settings.memory_max_episodic_summaries

        stmt = (
            select(SceneSummary)
            .where(SceneSummary.session_id == session_id)
            .order_by(SceneSummary.chapter.desc())
            .limit(limit)
        )
        result = await db.execute(stmt)
        summaries = result.scalars().all()

        return [
            {
                "chapter": s.chapter,
                "scene_name": s.scene_name,
                "summary": s.summary_text,
                "key_events": s.key_events,
            }
            for s in summaries
        ]

    async def store_episodic_summary(
        self,
        db: AsyncSession,
        session_id: str,
        chapter: int,
        scene_name: str,
        summary_text: str,
        characters_present: list[str],
        key_events: list[str],
        turn_start: int,
        turn_end: int,
    ) -> SceneSummary:
        """
        存储一条情景记忆（场景摘要）。

        通常在一轮对话结束后、或场景切换时调用。

        Args:
            db: 数据库会话
            session_id: 游戏会话ID
            chapter: 章节编号
            scene_name: 场景名称
            summary_text: 摘要文本 (200-500 tokens)
            characters_present: 在场角色列表
            key_events: 关键事件列表
            turn_start: 起始对话轮次
            turn_end: 结束对话轮次

        Returns:
            创建的 SceneSummary ORM 实例
        """
        summary = SceneSummary(
            session_id=session_id,
            chapter=chapter,
            scene_name=scene_name,
            summary_text=summary_text,
            characters_present=characters_present,
            key_events=key_events,
            turn_range_start=turn_start,
            turn_range_end=turn_end,
        )
        db.add(summary)
        await db.flush()

        logger.info(f"📝 情景记忆已存储: [{scene_name}] ch={chapter}")
        return summary

    # =================================================================
    #  Layer 3: 语义记忆 —— 关键事实 (ChromaDB 向量检索)
    # =================================================================

    def _get_chroma_collection(self):
        """
        获取或创建 ChromaDB collection。

        延迟初始化，避免在没有安装 chromadb 时启动失败。
        """
        if self._chroma_collection is None:
            try:
                import chromadb

                client = chromadb.PersistentClient(
                    path=self._settings.chroma_persist_dir
                )
                self._chroma_collection = client.get_or_create_collection(
                    name="narrator_memories",
                    metadata={"description": "Narrator Engine 语义记忆"},
                )
                logger.info("ChromaDB collection 已就绪")
            except ImportError:
                logger.warning("chromadb 未安装，语义记忆功能不可用")
                return None
        return self._chroma_collection

    async def store_semantic_memory(
        self,
        db: AsyncSession,
        session_id: str,
        content: str,
        importance: int,
        category: str = "other",
        related_characters: list[str] | None = None,
        chapter: int = 1,
        metadata: dict | None = None,
    ) -> Memory | None:
        """
        存储一条语义记忆（关键事实）。

        同时写入 SQLite（结构化查询）和 ChromaDB（向量检索）。
        重要度低于阈值的记忆不会存入 ChromaDB。

        Args:
            db: 数据库会话
            session_id: 游戏会话ID
            content: 记忆文本
            importance: 重要度 (1-10)
            category: 类别
            related_characters: 相关角色
            chapter: 章节
            metadata: 附加元数据

        Returns:
            创建的 Memory ORM 实例（低于阈值时返回 None）
        """
        min_importance = self._settings.memory_min_importance

        # 低于最低重要度的事实不存储到长期记忆
        if importance < min_importance:
            logger.debug(f"记忆重要度 {importance} < {min_importance}，跳过存储")
            return None

        memory = Memory(
            session_id=session_id,
            content=content,
            importance=importance,
            category=category,
            related_characters=related_characters or [],
            chapter=chapter,
            metadata_json=metadata or {},
        )
        db.add(memory)
        await db.flush()

        # 同步写入 ChromaDB 向量索引
        collection = self._get_chroma_collection()
        if collection:
            embedding_id = uuid.uuid4().hex
            collection.add(
                ids=[embedding_id],
                documents=[content],
                metadatas=[{
                    "session_id": session_id,
                    "importance": importance,
                    "category": category,
                    "chapter": chapter,
                    "characters": ",".join(related_characters or []),
                }],
            )
            memory.embedding_id = embedding_id
            await db.flush()

        logger.info(f"🧠 语义记忆已存储: [{content[:40]}...] imp={importance}")
        return memory

    async def search_semantic_memory(
        self,
        db: AsyncSession,
        session_id: str,
        query: str,
        top_k: int | None = None,
    ) -> list[dict]:
        """
        通过向量相似度搜索语义记忆。

        Args:
            db: 数据库会话
            session_id: 游戏会话ID（只搜索当前会话的记忆）
            query: 查询文本
            top_k: 返回结果数量（默认使用配置值）

        Returns:
            相关记忆列表，按相关度排序
        """
        if top_k is None:
            top_k = self._settings.memory_vector_search_top_k

        collection = self._get_chroma_collection()
        if collection is None:
            return []

        try:
            results = collection.query(
                query_texts=[query],
                n_results=top_k,
                where={"session_id": session_id},
            )

            memories = []
            if results and results["documents"]:
                for doc, meta in zip(
                    results["documents"][0],
                    results["metadatas"][0] if results["metadatas"] else [{}] * len(results["documents"][0]),
                ):
                    memories.append({
                        "content": doc,
                        "importance": meta.get("importance", 5),
                        "category": meta.get("category", "other"),
                    })

            return memories

        except Exception as e:
            logger.error(f"ChromaDB 检索失败: {e}")
            return []

    # =================================================================
    #  综合上下文构建 —— 为 Prompt 组装记忆
    # =================================================================

    async def build_memory_context(
        self,
        db: AsyncSession,
        session_id: str,
        current_chapter: int = 1,
        current_query: str = "",
    ) -> dict:
        """
        构建完整的记忆上下文，供 PromptBuilder 使用。

        汇总三层记忆，返回一个结构化的字典。

        Args:
            db: 数据库会话
            session_id: 游戏会话ID
            current_chapter: 当前章节
            current_query: 当前玩家输入（用于语义检索）

        Returns:
            {
                "recent_dialogues": [...],   # Layer 1
                "scene_summaries": [...],     # Layer 2
                "key_facts": [...],           # Layer 3
            }
        """
        # 三层记忆并行获取
        recent = await self.get_working_memory(db, session_id)
        summaries = await self.get_episodic_memory(db, session_id, current_chapter)

        # 语义记忆需要查询文本，单独获取
        facts = []
        if current_query:
            semantic_results = await self.search_semantic_memory(
                db, session_id, current_query
            )
            facts = [r["content"] for r in semantic_results]

        return {
            "recent_dialogues": recent,
            "scene_summaries": summaries,
            "key_facts": facts,
        }


# ---------------------------------------------------------------------------
# 单例
# ---------------------------------------------------------------------------
memory_manager = MemoryManager()
