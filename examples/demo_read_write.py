#!/usr/bin/env python3
"""
BeeAgent 读写文件演示

任务：让蜜蜂先读取 README，然后写一个总结到新文件里。
"""

import asyncio
from dotenv import load_dotenv

from mycelium import BeeAgent, ToolRegistry
from mycelium.llm import LLMClient
from mycelium.tools import bash_tool, read_file_tool, write_file_tool


async def main():
    load_dotenv()

    # 注册三只工具：Bash + ReadFile + WriteFile
    registry = (
        ToolRegistry()
        .register(bash_tool)
        .register(read_file_tool)
        .register(write_file_tool)
    )

    llm = LLMClient()
    print(f"📡 使用模型: {llm.model}\n")

    bee = BeeAgent(llm_client=llm, registry=registry, compat_mode=False)

    prompt = "读取 AGENTS.md 的内容，写一个 one-page 总结到 summary.md"
    print(f"🐝 用户：{prompt}\n")

    async for chunk in bee.run(prompt):
        print(f"🐝 蜜蜂：{chunk}")


if __name__ == "__main__":
    asyncio.run(main())
