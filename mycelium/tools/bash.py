"""
Bash 工具实现

蜜蜂的第一项能力：执行 Shell 命令。
这是 Agent Harness 里最基础、也最危险的工具，所以第一版就加上安全边界。
"""

import subprocess
from mycelium.tools.base import Tool


def _execute_bash(args: dict) -> str:
    """
    执行 Bash 命令并返回标准输出。

    注意：这里使用了 capture_output 来同时捕获 stdout 和 stderr。
    如果命令返回非 0 退出码，我们也把 stderr 一起返回给 LLM，
    让它自己判断是重试还是换策略——这和 Claude Code 的错误恢复逻辑一致。
    """
    command = args.get("command", "").strip()
    if not command:
        return "错误：command 参数为空。"

    # 安全边界已迁移到 PermissionGuard（权限管线），
    # 工具层不再维护硬编码拦截列表。

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
        output = result.stdout.strip()
        if result.returncode != 0:
            err = result.stderr.strip()
            return f"命令退出码 {result.returncode}。\nstdout:\n{output}\nstderr:\n{err}"
        return output if output else "（命令执行成功，无输出）"
    except subprocess.TimeoutExpired:
        return "错误：命令执行超时（30 秒）。"
    except Exception as e:
        return f"错误：执行异常 {type(e).__name__}: {e}"


# Bash 工具的全局单例实例
# 参数 schema 使用简化版 JSON Schema，兼容 OpenRouter / OpenAI 格式
bash_tool = Tool(
    name="Bash",
    description="在操作系统的默认 shell 中执行命令，返回标准输出。适用于文件操作、代码运行、系统查询等场景。",
    parameters={
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "要执行的 shell 命令",
            }
        },
        "required": ["command"],
    },
    execute=_execute_bash,
)
