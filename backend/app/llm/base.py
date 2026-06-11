"""
Narrator Engine - LLM 抽象基类

定义所有 LLM 提供商的统一接口。
后续如果要接入其他模型（如通义千问、文心一言、本地 Ollama），
只需实现此基类即可无缝切换。
"""

from abc import ABC, abstractmethod
from typing import AsyncGenerator


class LLMMessage:
    """
    LLM 消息封装，兼容 OpenAI Chat Completion 格式。

    Attributes:
        role: 消息角色 ("system" / "user" / "assistant")
        content: 消息文本内容
    """

    def __init__(self, role: str, content: str):
        self.role = role
        self.content = content

    def to_dict(self) -> dict:
        """转为 OpenAI API 所需的字典格式"""
        return {"role": self.role, "content": self.content}


class BaseLLMProvider(ABC):
    """
    LLM 提供商的抽象基类。

    所有具体的 LLM 实现（DeepSeek、OpenAI、本地模型等）
    都必须继承此类并实现以下方法。
    """

    @abstractmethod
    async def chat_completion(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.75,
        max_tokens: int = 2048,
        top_p: float = 0.9,
        response_format: dict | None = None,
    ) -> str:
        """
        同步调用 —— 等待完整响应后返回。

        Args:
            messages: 对话消息列表 (含 system prompt)
            temperature: 温度参数 (0-2)
            max_tokens: 最大生成 token 数
            top_p: 核采样参数
            response_format: 响应格式约束 (如 {"type": "json_object"})

        Returns:
            完整的模型回复文本
        """
        ...

    @abstractmethod
    async def chat_completion_stream(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.75,
        max_tokens: int = 2048,
        top_p: float = 0.9,
        response_format: dict | None = None,
    ) -> AsyncGenerator[str, None]:
        """
        流式调用 —— 逐 token/chunk 返回，用于 SSE 推送。

        Args:
            参数同 chat_completion

        Yields:
            每次 yield 一个文本片段 (str)
        """
        ...
