"""
织梦绮谭 - DeepSeek LLM 适配器 (LangChain 版)

基于 LangChain ChatOpenAI 实现（DeepSeek API 兼容 OpenAI 协议）。
支持同步和流式两种调用方式。

依赖:
  - langchain, langchain-openai (pip install langchain langchain-openai)
  - 环境变量 DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL
"""

from typing import AsyncGenerator

from langchain_openai import ChatOpenAI
from langchain_core.messages import (
    SystemMessage,
    HumanMessage,
    AIMessage,
    BaseMessage,
)
from loguru import logger

from app.config import get_settings
from app.llm.base import BaseLLMProvider, LLMMessage


def _to_langchain_messages(messages: list[LLMMessage]) -> list[BaseMessage]:
    """将内部 LLMMessage 转为 LangChain 消息格式"""
    result = []
    for msg in messages:
        if msg.role == "system":
            result.append(SystemMessage(content=msg.content))
        elif msg.role == "assistant":
            result.append(AIMessage(content=msg.content))
        else:
            result.append(HumanMessage(content=msg.content))
    return result


class DeepSeekProvider(BaseLLMProvider):
    """
    DeepSeek API 适配器 (LangChain 实现)。

    使用 LangChain 的 ChatOpenAI 调用 DeepSeek。
    支持:
      - 标准对话补全 (chat completion)
      - 流式输出 (streaming)
      - JSON Mode (强制输出 JSON 格式)
    """

    def __init__(self):
        """初始化 DeepSeek 客户端，从配置中读取 API 参数"""
        settings = get_settings()

        self._llm = ChatOpenAI(
            model=settings.deepseek_model,
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
            top_p=settings.llm_top_p,
            # 禁用 LangChain 自带的回调追踪，避免额外网络请求
            disable_streaming=False,
        )
        self._model = settings.deepseek_model

        logger.info(
            f"DeepSeek (LangChain) 已初始化: model={self._model}, "
            f"base_url={settings.deepseek_base_url}"
        )

    async def chat_completion(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.75,
        max_tokens: int = 2048,
        top_p: float = 0.9,
        response_format: dict | None = None,
    ) -> str:
        """
        同步调用 DeepSeek API，返回完整回复。

        使用 LangChain ChatOpenAI.ainvoke() 进行异步调用。
        """
        lc_messages = _to_langchain_messages(messages)

        # 构建临时覆盖参数
        kwargs = {
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": top_p,
        }
        if response_format:
            kwargs["response_format"] = response_format

        try:
            # 使用 with_config 传递临时参数
            llm_with_params = self._llm.bind(**kwargs)
            response = await llm_with_params.ainvoke(lc_messages)

            content = response.content
            if not content:
                logger.warning("DeepSeek 返回了空回复")
                return ""

            # 记录 token 使用情况
            if hasattr(response, "response_metadata"):
                usage = response.response_metadata.get("token_usage", {})
                if usage:
                    logger.debug(
                        f"Token 使用: prompt={usage.get('prompt_tokens', '?')}, "
                        f"completion={usage.get('completion_tokens', '?')}, "
                        f"total={usage.get('total_tokens', '?')}"
                    )

            return content.strip()

        except Exception as e:
            logger.error(f"DeepSeek (LangChain) API 调用失败: {type(e).__name__}: {e}")
            raise

    async def chat_completion_stream(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.75,
        max_tokens: int = 2048,
        top_p: float = 0.9,
        response_format: dict | None = None,
    ) -> AsyncGenerator[str, None]:
        """
        流式调用 DeepSeek API，逐 chunk 返回。

        使用 LangChain ChatOpenAI.astream() 进行异步流式调用。

        注意: 流式模式下 response_format 可能不被支持。
        """
        lc_messages = _to_langchain_messages(messages)

        kwargs = {
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": top_p,
        }

        if response_format:
            logger.warning("流式模式不支持 response_format，将忽略此参数")

        try:
            llm_with_params = self._llm.bind(**kwargs)
            async for chunk in llm_with_params.astream(lc_messages):
                if chunk.content:
                    yield chunk.content

        except Exception as e:
            logger.error(f"DeepSeek (LangChain) 流式调用失败: {type(e).__name__}: {e}")
            raise


# ---------------------------------------------------------------------------
# 工厂函数 —— 获取当前配置的 LLM 提供商实例
# ---------------------------------------------------------------------------
_provider_instance: BaseLLMProvider | None = None


def get_llm_provider() -> BaseLLMProvider:
    """
    获取 LLM 提供商单例。

    当前固定返回 DeepSeekProvider (LangChain 实现)。
    未来可以在这里根据配置切换不同的提供商。
    """
    global _provider_instance
    if _provider_instance is None:
        _provider_instance = DeepSeekProvider()
    return _provider_instance
