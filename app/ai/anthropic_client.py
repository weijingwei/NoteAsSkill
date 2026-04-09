"""Anthropic 客户端实现"""

import json
from typing import Any, Iterator

from anthropic import Anthropic

from .client import AIClient, ChatResponse, MCPToolSchema, ToolCall


class AnthropicClient(AIClient):
    """Anthropic API 客户端"""

    def __init__(
        self,
        api_key: str = "",
        base_url: str = "https://api.anthropic.com",
        model: str = "claude-3-opus-20240229",
    ):
        super().__init__(api_key, base_url, model)
        self._client: Anthropic | None = None

    def _get_client(self) -> Anthropic:
        """获取或创建 Anthropic 客户端"""
        if self._client is None:
            # 清理 API Key，移除可能导致 HTTP Header 错误的字符
            clean_api_key = self._clean_api_key(self.api_key)
            self._client = Anthropic(
                api_key=clean_api_key,
                base_url=self.base_url if self.base_url else None,
            )
        return self._client

    def _clean_api_key(self, api_key: str) -> str:
        """清理 API Key，移除非法字符

        HTTP Header 只能包含 ASCII 字符，需要移除或替换非 ASCII 字符
        """
        if not api_key:
            return api_key

        # 移除常见的错误前缀（如 "公司:" 等）
        import re
        # 如果包含冒号，只取冒号后的部分
        if ':' in api_key:
            parts = api_key.split(':', 1)
            if len(parts) == 2:
                # 检查冒号前是否包含非 ASCII 字符
                prefix = parts[0]
                try:
                    prefix.encode('ascii')
                    # 前缀是 ASCII，可能是合法格式（如 "Bearer"）
                    return api_key.strip()
                except UnicodeEncodeError:
                    # 前缀包含非 ASCII 字符，丢弃前缀
                    api_key = parts[1].strip()

        # 确保只保留 ASCII 字符
        try:
            # 尝试编码为 ASCII，如果失败则移除非 ASCII 字符
            return api_key.encode('ascii', errors='ignore').decode('ascii')
        except Exception:
            return api_key.strip()

    def _ensure_utf8_encoding(self, messages: list[dict[str, str]]) -> list[dict[str, str]]:
        """确保消息编码为 UTF-8"""
        encoded_messages = []
        for msg in messages:
            encoded_msg = {}
            for key, value in msg.items():
                if isinstance(value, str):
                    # 确保字符串是 UTF-8 编码
                    encoded_msg[key] = value.encode('utf-8').decode('utf-8')
                else:
                    encoded_msg[key] = value
            encoded_messages.append(encoded_msg)
        return encoded_messages

    def validate_config(self) -> bool:
        """验证配置是否有效"""
        return bool(self.api_key and self.model)

    def _format_tools_for_api(self, tools: list[MCPToolSchema] | None) -> list[dict] | None:
        """将工具列表转换为 Anthropic API 格式"""
        if not tools:
            return None
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.input_schema,
            }
            for tool in tools
        ]

    def chat(
        self,
        messages: list[dict[str, str]],
        tools: list[MCPToolSchema] | None = None,
        **kwargs: Any,
    ) -> ChatResponse:
        """发送聊天消息"""
        client = self._get_client()

        # 确保消息编码正确
        encoded_messages = self._ensure_utf8_encoding(messages)

        # 提取 system 消息
        system_message = ""
        chat_messages = []
        for msg in encoded_messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                chat_messages.append(msg)

        api_params = {
            "model": self.model,
            "max_tokens": kwargs.get("max_tokens", 4096),
            "system": system_message if system_message else None,
            "messages": chat_messages,
        }

        # 添加工具参数
        formatted_tools = self._format_tools_for_api(tools)
        if formatted_tools:
            api_params["tools"] = formatted_tools

        response = client.messages.create(**api_params)

        # 处理响应内容
        content = ""
        tool_calls = []
        finish_reason = "stop"

        if response.content:
            for block in response.content:
                # 文本块
                if hasattr(block, 'text'):
                    content += block.text
                # 工具使用块
                elif hasattr(block, 'type') and block.type == 'tool_use':
                    tool_calls.append(ToolCall(
                        id=block.id,
                        name=block.name,
                        arguments=block.input if hasattr(block, 'input') else {},
                    ))

        # 判断结束原因
        if tool_calls:
            finish_reason = "tool_calls"
        elif response.stop_reason == "tool_use":
            finish_reason = "tool_calls"

        return ChatResponse(
            content=content,
            tool_calls=tool_calls if tool_calls else None,
            finish_reason=finish_reason,
        )

    def chat_stream(
        self,
        messages: list[dict[str, str]],
        tools: list[MCPToolSchema] | None = None,
        **kwargs: Any,
    ) -> Iterator[ChatResponse]:
        """发送聊天消息（流式响应）"""
        client = self._get_client()

        # 确保消息编码正确
        encoded_messages = self._ensure_utf8_encoding(messages)

        # 提取 system 消息
        system_message = ""
        chat_messages = []
        for msg in encoded_messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                chat_messages.append(msg)

        api_params = {
            "model": self.model,
            "max_tokens": kwargs.get("max_tokens", 4096),
            "system": system_message if system_message else None,
            "messages": chat_messages,
        }

        # 添加工具参数
        formatted_tools = self._format_tools_for_api(tools)
        if formatted_tools:
            api_params["tools"] = formatted_tools

        # 收集工具调用数据
        tool_calls_data: dict[str, dict] = {}  # id -> {name, arguments}

        with client.messages.stream(**api_params) as stream:
            for event in stream:
                # 文本内容
                if event.type == "content_block_delta" and hasattr(event, 'delta'):
                    if hasattr(event.delta, 'text'):
                        yield ChatResponse(content=event.delta.text)

                # 工具调用开始
                elif event.type == "content_block_start":
                    block = getattr(event, 'content_block', None)
                    if block and hasattr(block, 'type') and block.type == 'tool_use':
                        tool_calls_data[block.id] = {
                            "name": block.name,
                            "arguments": "",
                        }

                # 工具调用参数
                elif event.type == "content_block_delta":
                    delta = getattr(event, 'delta', None)
                    if delta and hasattr(delta, 'type') and delta.type == 'input_json_delta':
                        block_index = getattr(event, 'index', None)
                        if block_index is not None and hasattr(stream, 'content_blocks'):
                            blocks = stream.content_blocks
                            if block_index < len(blocks):
                                block = blocks[block_index]
                                if hasattr(block, 'id') and block.id in tool_calls_data:
                                    partial_json = getattr(delta, 'partial_json', '')
                                    tool_calls_data[block.id]["arguments"] += partial_json

                # 消息结束
                elif event.type == "message_stop":
                    if tool_calls_data:
                        tool_calls = [
                            ToolCall(
                                id=tool_id,
                                name=data["name"],
                                arguments=json.loads(data["arguments"]) if data["arguments"] else {},
                            )
                            for tool_id, data in tool_calls_data.items()
                        ]
                        yield ChatResponse(
                            content="",
                            tool_calls=tool_calls,
                            finish_reason="tool_calls",
                        )
                    else:
                        yield ChatResponse(content="", finish_reason="stop")

    def list_models(self) -> list[str]:
        """列出可用的模型

        Anthropic 没有公开的模型列表 API，这里返回已知的模型列表。
        实际可用模型请参考 Anthropic 官方文档。
        """
        return [
            "claude-sonnet-4-20250514",
            "claude-sonnet-4-20250507",
            "claude-3-5-sonnet-20240620",
            "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022",
            "claude-3-5-haiku-20240620",
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307",
        ]
