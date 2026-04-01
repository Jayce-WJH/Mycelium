#!/usr/bin/env python3
"""
BeeAgent 手动测试（无需 pytest）

运行方式：
    python3 tests/test_bee_manual.py
"""

import asyncio
from mycelium import BeeAgent, ToolRegistry, Tool
from mycelium.tools.bash import bash_tool


class FakeLLMClient:
    """假 LLM 客户端，用于离线测试对话循环。"""

    def __init__(self, responses):
        self.responses = responses
        self.call_index = 0

    async def chat(self, messages, tools=None):
        resp = self.responses[self.call_index]
        self.call_index += 1
        return resp


async def test_text_only():
    fake_llm = FakeLLMClient([
        {"choices": [{"message": {"content": "直接回答"}}]}
    ])
    bee = BeeAgent(llm_client=fake_llm, registry=ToolRegistry())
    outputs = [chunk async for chunk in bee.run("你好")]
    assert outputs == ["直接回答"], f"期望 ['直接回答']，实际 {outputs}"
    print("✅ test_text_only 通过")


async def test_with_tool_call():
    fake_llm = FakeLLMClient([
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
        {
            "choices": [{"message": {"content": "最终答案"}}]
        }
    ])

    registry = ToolRegistry().register(bash_tool)
    bee = BeeAgent(llm_client=fake_llm, registry=registry)
    outputs = [chunk async for chunk in bee.run("执行 echo test")]

    assert len(outputs) == 2, f"期望 2 条输出，实际 {len(outputs)}"
    assert "第1轮·第1个" in outputs[0], f"第一条应包含轮次标记，实际 {outputs[0]}"
    assert outputs[1] == "最终答案", f"第二条应为'最终答案'，实际 {outputs[1]}"

    tool_msgs = [m for m in bee.messages if m.get("role") == "tool"]
    assert len(tool_msgs) == 1
    assert tool_msgs[0]["content"] == "test"
    print("✅ test_with_tool_call 通过")


async def main():
    print("开始运行 BeeAgent 手动测试...\n")
    await test_text_only()
    await test_with_tool_call()
    print("\n所有测试通过 🎉")


if __name__ == "__main__":
    asyncio.run(main())
