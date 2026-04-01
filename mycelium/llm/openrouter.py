"""
LLM 客户端封装（OpenAI 兼容格式）

职责单一：把 messages 列表丢给 LLM API（支持 OpenRouter、火山引擎、MiniMax 等 OpenAI 兼容端点），
返回原始响应。不处理 Tool 解析、不处理对话状态——这些属于 agent 层的职责。
"""

import os
import json
from typing import List
import asyncio

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    import urllib.request
    import urllib.error


class LLMClient:
    """
    极简 OpenAI 兼容格式异步客户端。

    由于项目目前只保证有 requests（同步库），我们用 asyncio.to_thread 做异步桥接。
    后续如果引入 httpx/aiohttp，可以无缝替换这里的 _post 实现。
    """

    DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        site_url: str = "https://github.com/Jayce-WJH/Mycelium",
        site_name: str = "Mycelium Agent Framework",
    ):
        self.api_key = api_key or os.getenv("OPENAI_COMPATIBLE_API_KEY") or os.getenv("OPENROUTER_API_KEY", "")
        self.base_url = (base_url or os.getenv("OPENAI_COMPATIBLE_API_BASE") or self.DEFAULT_BASE_URL).rstrip("/")
        self.model = model or os.getenv("MAIN_LLM_MODEL") or os.getenv("OPENROUTER_MODEL", "qwen/qwen3.6-plus-preview:free")
        self.site_url = site_url
        self.site_name = site_name

    @property
    def chat_completions_url(self) -> str:
        return f"{self.base_url}/chat/completions"

    def _post(self, messages: List[dict], tools: List[dict] | None = None) -> dict:
        """同步 HTTP POST，被异步层包裹。"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": self.site_url,
            "X-Title": self.site_name,
        }

        data = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 2048,
        }
        if tools:
            data["tools"] = tools
            # 强制让模型在需要时调用工具（qwen 等部分模型需要显式指定）
            data["tool_choice"] = "auto"

        if HAS_REQUESTS:
            response = requests.post(self.chat_completions_url, headers=headers, json=data, timeout=60)
            response.raise_for_status()
            return response.json()

        # 无 requests 时的 fallback（几乎不会走到这里）
        req = urllib.request.Request(
            self.chat_completions_url,
            data=json.dumps(data).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))

    async def chat(self, messages: List[dict], tools: List[dict] | None = None) -> dict:
        """异步入口。把同步请求丢到线程池里，避免阻塞事件循环。"""
        return await asyncio.to_thread(self._post, messages, tools)


# 向后兼容别名：旧代码里可能还在用 OpenRouterClient
OpenRouterClient = LLMClient
