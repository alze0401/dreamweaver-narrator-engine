"""
织梦绮谭 - DeepSeek LLM 适配器 (LangChain 版)

基于 LangChain ChatOpenAI 实现（DeepSeek API 兼容 OpenAI 协议）。
支持同步和流式两种调用方式。

依赖:
  - langchain, langchain-openai (pip install langchain langchain-openai)
  - 环境变量 DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL
"""

from typing import AsyncGenerator, TypeVar, Type

from langchain_openai import ChatOpenAI
from langchain_core.messages import (
    SystemMessage,
    HumanMessage,
    AIMessage,
    BaseMessage,
)
from pydantic import BaseModel
from loguru import logger

from app.config import get_settings
from app.llm.base import BaseLLMProvider, LLMMessage

T = TypeVar("T", bound=BaseModel)


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
            disable_streaming=False,
        )
        self._model = settings.deepseek_model
        self._api_key = settings.deepseek_api_key
        self._base_url = settings.deepseek_base_url

        logger.info(
            f"DeepSeek (LangChain) 已初始化: model={self._model}, "
            f"base_url={settings.deepseek_base_url}"
        )

    def _create_llm(
        self,
        temperature: float = 0.75,
        max_tokens: int = 2048,
        top_p: float = 0.9,
        response_format: dict | None = None,
        thinking: bool | None = None,
    ) -> ChatOpenAI:
        """
        创建带指定参数的临时 ChatOpenAI 实例。

        不使用 bind() 因为 bind 不支持 response_format 等某些参数。
        通过构造器直接传参确保参数正确送达 API。

        Args:
            thinking: 是否启用 thinking 模式。
                      None = 使用模型默认行为,
                      False = 禁用 thinking（用于结构化输出/JSON模式，节省 token 并避免空响应）。
                      通过 extra_body 传递，直接注入 API 请求体。
        """
        kwargs = {
            "model": self._model,
            "api_key": self._api_key,
            "base_url": self._base_url,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": top_p,
            "disable_streaming": False,
        }
        if response_format:
            kwargs["response_format"] = response_format
        if thinking is not None:
            # DeepSeek thinking 参数是结构体: {"type": "enabled"|"disabled"}
            thinking_type = "disabled" if not thinking else "enabled"
            kwargs["extra_body"] = {"thinking": {"type": thinking_type}}
        return ChatOpenAI(**kwargs)

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

        使用构造器方式传参（非 bind），确保 response_format 等参数正确送达 API。
        当使用 JSON mode 时，自动禁用 thinking 模式以避免 thinking tokens 占用全部 token 额度。
        """
        lc_messages = _to_langchain_messages(messages)
        # JSON mode 下禁用 thinking，避免 thinking tokens 消耗全部额度导致空响应
        llm = self._create_llm(
            temperature, max_tokens, top_p, response_format,
            thinking=False if response_format else None,
        )

        try:
            response = await llm.ainvoke(lc_messages)

            content = response.content or ""

            # Thinking mode 模型可能把内容放在 additional_kwargs 中
            if hasattr(response, "additional_kwargs"):
                reasoning = response.additional_kwargs.get("reasoning_content", "")
                if reasoning:
                    logger.debug(
                        f"Thinking mode: 检测到 {len(reasoning)} 字 reasoning_content"
                    )

                if not content:
                    # 某些 provider 把答案放在 refusal / message / content 键中
                    for key in ("refusal", "message", "content"):
                        val = response.additional_kwargs.get(key, "")
                        if isinstance(val, str) and val.strip():
                            content = val
                            logger.debug(
                                f"Thinking mode: 从 additional_kwargs['{key}'] 获取到内容"
                            )
                            break

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
        """
        lc_messages = _to_langchain_messages(messages)

        if response_format:
            logger.warning("流式模式不支持 response_format，将忽略此参数")

        try:
            llm = self._create_llm(temperature, max_tokens, top_p)
            async for chunk in llm.astream(lc_messages):
                if chunk.content:
                    yield chunk.content

        except Exception as e:
            logger.error(f"DeepSeek (LangChain) 流式调用失败: {type(e).__name__}: {e}")
            raise

    async def structured_completion(
        self,
        messages: list[LLMMessage],
        output_model: Type[T],
        temperature: float = 0.75,
        max_tokens: int = 2048,
        top_p: float = 0.9,
    ) -> T:
        """
        结构化输出 —— 使用 LangChain with_structured_output 强制 LLM 按 Pydantic 模型输出。

        优先使用 function_calling，如果模型不支持（如 thinking mode）
        则降级为 json_mode。
        始终禁用 thinking 模式以避免 tool_choice 冲突和空响应。
        """
        lc_messages = _to_langchain_messages(messages)

        # 尝试两种 method：function_calling → json_mode
        for method in ("function_calling", "json_mode"):
            try:
                # 禁用 thinking：function_calling 不兼容 thinking mode，
                # json_mode 下 thinking 会浪费 token 额度
                llm = self._create_llm(
                    temperature, max_tokens, top_p, thinking=False,
                )
                structured_llm = llm.with_structured_output(
                    output_model,
                    method=method,
                )
                result = await structured_llm.ainvoke(lc_messages)
                logger.debug(
                    f"DeepSeek structured output ({method}): "
                    f"{output_model.__name__} 解析成功"
                )
                return result

            except Exception as e:
                err_msg = str(e)
                if method == "function_calling" and "tool_choice" in err_msg:
                    logger.info(
                        f"structured output: {self._model} 不支持 function_calling，"
                        f"自动切换 json_mode"
                    )
                    continue  # 尝试 json_mode
                logger.error(
                    f"DeepSeek structured output ({method}) 失败: "
                    f"{type(e).__name__}: {e}"
                )
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
