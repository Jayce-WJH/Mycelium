"""
WriteFile 工具实现

蜜蜂的手：向文件系统写入内容。
这是 Agent 从"只读观察"迈向"动手改造"的关键能力。
"""

from pathlib import Path
from mycelium.tools.base import Tool


def _execute_write_file(args: dict) -> str:
    """
    将内容写入指定文件。

    安全与工程细节：
    - 自动创建父目录（mkdir parents=True），减少 LLM 因目录不存在而反复试错
    - 覆盖已有文件时返回提示，方便对话回溯
    - 所有异常转换为字符串返回，避免打断对话循环
    """
    path_str = args.get("path", "").strip()
    content = args.get("content", "")

    if not path_str:
        return "错误：path 参数为空。"

    path = Path(path_str)

    try:
        # 如果父目录不存在，自动创建（这是 LLM 最容易踩的坑之一）
        path.parent.mkdir(parents=True, exist_ok=True)

        existed = path.exists()
        path.write_text(content, encoding="utf-8")

        action = "已更新" if existed else "已创建"
        return f"{action} 文件 '{path}'（{len(content)} 字符）。"
    except Exception as e:
        return f"错误：写入文件失败 {type(e).__name__}: {e}"


write_file_tool = Tool(
    name="WriteFile",
    description="将内容写入指定文件，必要时自动创建父目录。适用于生成代码、修改配置、记录日志等场景。",
    parameters={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "要写入的文件路径（相对路径或绝对路径）",
            },
            "content": {
                "type": "string",
                "description": "要写入的文件内容",
            },
        },
        "required": ["path", "content"],
    },
    execute=_execute_write_file,
)
