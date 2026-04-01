#!/usr/bin/env python3
"""
BeeAgent 基础测试
覆盖：ToolRegistry 注册/查找、Bash 工具执行、BeeAgent 单轮对话循环
"""

import pytest
from mycelium import ToolRegistry, Tool
from mycelium.tools.bash import bash_tool


def test_tool_registry_register_and_get():
    """工具注册表应支持链式注册和按名查找。"""
    registry = ToolRegistry()
    dummy = Tool(name="Dummy", description="A dummy tool", parameters={}, execute=lambda x: "ok")

    result = registry.register(dummy)

    assert result is registry  # 链式返回自身
    assert registry.get("Dummy") is dummy
    assert registry.get("Missing") is None


def test_tool_registry_definitions_format():
    """definitions() 应生成 OpenAI 兼容的 tools 格式。"""
    registry = ToolRegistry().register(bash_tool)
    defs = registry.definitions()

    assert len(defs) == 1
    assert defs[0]["type"] == "function"
    assert defs[0]["function"]["name"] == "Bash"
    assert "properties" in defs[0]["function"]["parameters"]


def test_bash_tool_success():
    """Bash 工具应正确执行命令并返回输出。"""
    result = bash_tool.execute({"command": "echo hello"})
    assert result == "hello"


def test_bash_tool_empty_command():
    """Bash 工具应对空命令返回友好错误。"""
    result = bash_tool.execute({"command": "   "})
    assert "为空" in result


def test_bash_tool_blocked():
    """PermissionGuard 应对高危 Bash 命令触发安全拦截。"""
    from mycelium.permissions import default_guard

    guard = default_guard()
    result = guard.evaluate("Bash", {"command": "rm -rf /some/path"})
    assert result.behavior == "deny"

    # 通过 registry 包裹后的工具应在执行层返回拦截信息
    wrapped = guard.wrap(bash_tool)
    wrapped_result = wrapped.execute({"command": "rm -rf /some/path"})
    assert "拦截" in wrapped_result


class FakeLLMClient:
    """
    假 LLM 客户端，用于测试 BeeAgent 的对话循环和工具调用逻辑，
    避免对真实 OpenRouter API 产生依赖。
    """

    def __init__(self, responses):
        self.responses = responses
        self.call_index = 0

    async def chat(self, messages, tools=None):
        resp = self.responses[self.call_index]
        self.call_index += 1
        return resp


@pytest.mark.asyncio
async def test_bee_agent_text_only():
    """当 LLM 直接返回文本时，BeeAgent 应直接 yield 内容。"""
    from mycelium.agent import BeeAgent

    fake_llm = FakeLLMClient([
        {
            "choices": [{
                "message": {"content": "直接回答"}
            }]
        }
    ])
    bee = BeeAgent(llm_client=fake_llm, registry=ToolRegistry())

    outputs = [chunk async for chunk in bee.run("你好")]
    assert outputs == ["直接回答"]


@pytest.mark.asyncio
async def test_bee_agent_with_tool_call():
    """当 LLM 请求调用工具时，BeeAgent 应执行工具并返回最终答案。"""
    from mycelium.agent import BeeAgent

    fake_llm = FakeLLMClient([
        # 第一次：LLM 要求调用 Bash
        {
            "choices": [{
                "message": {
                    "content": "",
                    "tool_calls": [{
                        "id": "call_1",
                        "function": {
                            "name": "Bash",
                            "arguments": '{"command": "echo test"}'
                        }
                    }]
                }
            }]
        },
        # 第二次：LLM 拿到工具结果后给出最终回答
        {
            "choices": [{
                "message": {"content": "最终答案"}
            }]
        }
    ])

    registry = ToolRegistry().register(bash_tool)
    bee = BeeAgent(llm_client=fake_llm, registry=registry)

    outputs = [chunk async for chunk in bee.run("执行 echo test")]

    # 第一个 chunk 是工具调用进度提示，第二个 chunk 是最终答案
    assert len(outputs) == 2
    assert "第1轮·第1个" in outputs[0]
    assert "Bash" in outputs[0]
    assert outputs[1] == "最终答案"

    # 验证上下文里包含了工具执行结果
    tool_message = [m for m in bee.messages if m.get("role") == "tool"]
    assert len(tool_message) == 1
    assert tool_message[0]["content"] == "test"
