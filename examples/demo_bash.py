#!/usr/bin/env python3
"""
BeeAgent 最小运行示例
任务：让蜜蜂调用 Bash 工具，统计当前目录下的文件数量。

运行前请确保已安装项目依赖：
    uv pip install -e ".[dev]"
"""

import asyncio
from dotenv import load_dotenv

from mycelium import BeeAgent, ToolRegistry
from mycelium.llm import LLMClient
from mycelium.tools.bash import bash_tool


async def main():
    # 加载 .env 文件中的环境变量（API Key、Base URL、Model）
    load_dotenv()

    # 1. 创建工具注册表，并注册 Bash 工具
    registry = ToolRegistry().register(bash_tool)

    # 2. 创建 LLM 客户端（自动从 .env 读取 OPENAI_COMPATIBLE_API_KEY 等变量）
    llm = LLMClient()
    print(f"📡 使用模型: {llm.model}")
    print(f"🔗 API Base: {llm.base_url}\n")

    # 3. 孵化一只蜜蜂，注入它的能力（使用标准 OpenAI 格式）
    bee = BeeAgent(llm_client=llm, registry=registry, compat_mode=False)

    # 4. 给它一个需要工具才能完成的任务
    prompt = "帮我统计当前目录下一共有多少个文件夹（不包括子目录）,并且告诉我文件名"
    print(f"🐝 用户：{prompt}\n")

    async for chunk in bee.run(prompt):
        print(f"🐝 蜜蜂：{chunk}")


if __name__ == "__main__":
    asyncio.run(main())
