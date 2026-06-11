"""
织梦绮谭 - LangGraph 叙事工作流

使用 LangGraph 的 StateGraph 编排叙事生成的完整流程:
  1. gather_context  — 收集世界/角色/记忆上下文
  2. build_prompt    — 构建 System Prompt + 消息列表
  3. call_llm        — 调用 LLM (通过 LangChain)
  4. parse_response  — 解析 JSON 输出为结构化数据
  5. update_state    — 更新游戏状态 (好感度/场景)

将原来 _generate_narration 中的线性流程变为可视化的有向图，
便于未来扩展 (加入条件分支、重试逻辑、多步骤叙事等)。
"""

from typing import TypedDict, Optional
from dataclasses import dataclass, field

from langgraph.graph import StateGraph, END
from loguru import logger

from app.llm.base import LLMMessage
from app.llm.response_parser import response_parser

# PromptBuilder 单例缓存
_prompt_builder_instance = None


# =====================================================================
#  图状态定义
# =====================================================================

class NarrationState(TypedDict, total=False):
    """LangGraph 工作流的状态类型"""
    # ---- 输入 ----
    world_data: dict
    scenario_data: dict
    character_contexts: list
    player_profile: Optional[object]
    player_input: Optional[str]
    memory_context: dict
    session_id: str
    session: object  # GameSession ORM 实例
    db: object       # AsyncSession

    # ---- 中间产物 ----
    world_ctx: dict
    scene_ctx: dict
    player_ctx: dict
    recent_narration_summary: str
    system_prompt: str
    messages: list  # list[LLMMessage]

    # ---- 输出 ----
    raw_response: str
    parsed_result: dict


# =====================================================================
#  工作流节点
# =====================================================================

def build_prompt_node(state: NarrationState) -> dict:
    """
    节点: 构建 System Prompt + 组装消息列表
    
    从状态中取出 world_ctx / scene_ctx / character_contexts / memory_context，
    通过 PromptBuilder 生成 System Prompt，再拼接对话历史。
    """
    from app.engine.prompt_builder import PromptBuilder

    # 使用模块级缓存的 PromptBuilder 单例
    global _prompt_builder_instance
    if _prompt_builder_instance is None:
        _prompt_builder_instance = PromptBuilder()
    prompt_builder = _prompt_builder_instance

    world_ctx = state.get("world_ctx", {})
    scene_ctx = state.get("scene_ctx", {})
    character_contexts = state.get("character_contexts", [])
    memory_context = state.get("memory_context", {})
    player_ctx = state.get("player_ctx", {})
    recent_narration_summary = state.get("recent_narration_summary", "")

    # 构建 System Prompt
    system_prompt = prompt_builder.build_system_prompt(
        world_context=world_ctx,
        character_context=character_contexts,
        scene_context=scene_ctx,
        memory_context=memory_context,
        player_profile=player_ctx,
        recent_narration_summary=recent_narration_summary,
    )

    # 组装消息列表
    messages = [LLMMessage(role="system", content=system_prompt)]

    # 添加最近对话历史
    for dialogue in memory_context.get("recent_dialogues", []):
        role = "assistant" if dialogue["speaker"] != "player" else "user"
        messages.append(LLMMessage(role=role, content=dialogue["content"]))

    # 添加玩家输入（避免与 recent_dialogues 中最后一条重复）
    player_input = state.get("player_input")
    last_user_msg = None
    for m in reversed(messages):
        if m.role == "user":
            last_user_msg = m.content
            break

    if player_input:
        # 如果 recent_dialogues 的最后一条 user 消息和 player_input 相同，跳过重复
        if last_user_msg and last_user_msg.strip() == player_input.strip():
            logger.debug("[LangGraph] build_prompt: 跳过重复的玩家输入")
        else:
            messages.append(LLMMessage(role="user", content=player_input))
    else:
        # 开场叙事（无玩家输入）
        if not last_user_msg:
            messages.append(LLMMessage(
                role="user",
                content="请生成故事的开场场景。"
            ))

    logger.debug(f"[LangGraph] build_prompt: {len(messages)} 条消息")

    return {
        "system_prompt": system_prompt,
        "messages": messages,
    }


async def call_llm_node(state: NarrationState) -> dict:
    """
    节点: 调用 LLM (通过 LangChain ChatOpenAI)
    
    使用 DeepSeekProvider 发送消息并获取完整回复。
    空响应时自动重试（最多 2 次）。
    """
    from app.llm.deepseek import get_llm_provider
    from app.config import get_settings

    llm = get_llm_provider()
    settings = get_settings()
    messages = state.get("messages", [])

    max_attempts = 3  # 首次 + 最多 2 次重试
    raw_response = ""

    for attempt in range(1, max_attempts + 1):
        logger.debug(f"[LangGraph] call_llm: 第{attempt}次调用 LLM...")

        raw_response = await llm.chat_completion(
            messages=messages,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
            top_p=settings.llm_top_p,
            response_format={"type": "json_object"},
        )

        if raw_response and raw_response.strip():
            logger.debug(f"[LangGraph] call_llm: 收到 {len(raw_response)} 字符")
            break

        # 空响应 → 重试
        logger.warning(f"[LangGraph] call_llm: 第{attempt}次收到空响应")
        if attempt < max_attempts:
            # 重试时微调温度以提高输出概率
            import asyncio
            await asyncio.sleep(0.5 * attempt)  # 简单退避
        else:
            logger.error("[LangGraph] call_llm: 多次重试后仍收到空响应")

    return {"raw_response": raw_response}


def parse_response_node(state: NarrationState) -> dict:
    """
    节点: 解析 LLM 输出
    
    使用 ResponseParser 将原始文本解析为结构化数据:
    {narration, dialogues, choices, scene_state, affection_changes}
    """
    raw_response = state.get("raw_response", "")
    parsed = response_parser.parse(raw_response)

    logger.debug(
        f"[LangGraph] parse: narration={len(parsed.get('narration', ''))}字, "
        f"dialogues={len(parsed.get('dialogues', []))}, "
        f"choices={len(parsed.get('choices', []))}"
    )

    return {"parsed_result": parsed}


# =====================================================================
#  图构建
# =====================================================================

def build_narration_graph() -> StateGraph:
    """
    构建叙事生成的 LangGraph 工作流。

    流程: build_prompt → call_llm → parse_response → END
    """
    graph = StateGraph(NarrationState)

    # 添加节点
    graph.add_node("build_prompt", build_prompt_node)
    graph.add_node("call_llm", call_llm_node)
    graph.add_node("parse_response", parse_response_node)

    # 设置入口
    graph.set_entry_point("build_prompt")

    # 添加边
    graph.add_edge("build_prompt", "call_llm")
    graph.add_edge("call_llm", "parse_response")
    graph.add_edge("parse_response", END)

    return graph


# 编译图（单例）
_compiled_graph = None


def get_narration_graph():
    """获取编译好的叙事工作流单例"""
    global _compiled_graph
    if _compiled_graph is None:
        graph = build_narration_graph()
        _compiled_graph = graph.compile()
        logger.info("LangGraph 叙事工作流已编译")
    return _compiled_graph


# =====================================================================
#  便捷执行函数
# =====================================================================

async def run_narration(
    world_data: dict,
    scenario_data: dict,
    character_contexts: list,
    player_profile,
    player_input: str | None,
    memory_context: dict,
    session,
    db,
    world_ctx: dict,
    scene_ctx: dict,
    player_ctx: dict,
    recent_narration_summary: str = "",
) -> dict:
    """
    执行一次完整的叙事生成工作流。

    这是 narrator.py 调用的入口函数。
    将各上下文打包为初始状态，通过 LangGraph 运行。

    Returns:
        解析后的结构化结果字典
    """
    app = get_narration_graph()

    initial_state: NarrationState = {
        "world_data": world_data,
        "scenario_data": scenario_data,
        "character_contexts": character_contexts,
        "player_profile": player_profile,
        "player_input": player_input,
        "memory_context": memory_context,
        "session_id": session.id,
        "session": session,
        "db": db,
        "world_ctx": world_ctx,
        "scene_ctx": scene_ctx,
        "player_ctx": player_ctx,
        "recent_narration_summary": recent_narration_summary,
    }

    # 运行工作流
    final_state = await app.ainvoke(initial_state)

    return final_state.get("parsed_result", {})
