#!/usr/bin/env python3
"""
调试脚本：查看 minimax-m2.5 对 tool 调用的响应行为
"""

import json
import asyncio
from dotenv import load_dotenv
from mycelium.llm import LLMClient
from mycelium.tools.bash import bash_tool

load_dotenv()

llm = LLMClient()

messages = [
    {"role": "system", "content": "你是一个智能体助手，可以通过工具与环境交互。当前可用工具：Bash"},
    {"role": "user", "content": "帮我统计当前目录下一共有多少个文件（不包括子目录）,并且告诉我文件名"},
]

async def main():
    print("=" * 60)
    print("第一次调用：让模型决定是否需要工具")
    print("=" * 60)

    tools = [{
        "type": "function",
        "function": {
            "name": bash_tool.name,
            "description": bash_tool.description,
            "parameters": bash_tool.parameters,
        }
    }]

    resp1 = await llm.chat(messages, tools=tools)
    print(json.dumps(resp1, indent=2, ensure_ascii=False))

    choice1 = resp1["choices"][0]["message"]
    messages.append({
        "role": "assistant",
        "content": choice1.get("content", ""),
        "tool_calls": choice1.get("tool_calls", []),
    })

    if choice1.get("tool_calls"):
        call = choice1["tool_calls"][0]
        args = json.loads(call["function"]["arguments"])
        result = bash_tool.execute(args)
        print(f"\n工具执行结果: {result}")

        messages.append({
            "role": "tool",
            "tool_call_id": call["id"],
            "name": call["function"]["name"],
            "content": result,
        })

        print("=" * 60)
        print("第二次调用：把工具结果还给模型，观察它如何回答")
        print("=" * 60)
        resp2 = await llm.chat(messages, tools=None)
        print(json.dumps(resp2, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    asyncio.run(main())
