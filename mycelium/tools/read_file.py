"""
ReadFile 工具实现

蜜蜂的眼睛：读取文件内容。
这是 Agent 最基础的能力之一，几乎所有任务都需要先"看"再"动手"。
"""

from pathlib import Path
from mycelium.tools.base import Tool


def _execute_read_file(args: dict) -> str:
    """
    读取指定文件的内容。

    设计要点：
    - 使用 pathlib 而不是裸字符串操作，避免 Windows / Linux 路径差异
    - 对不存在的文件返回友好错误，而不是抛异常中断对话循环
    - 对二进制文件做简单防御（虽然第一版只处理文本）
    """
    path_str = args.get("path", "").strip()
    if not path_str:
        return "错误：path 参数为空。"

    path = Path(path_str)

    if not path.exists():
        return f"错误：文件 '{path}' 不存在。"
    if path.is_dir():
        return f"错误：'{path}' 是一个目录，不是文件。"

    # 防止误读超大文件导致内存或上下文爆炸
    MAX_SIZE_BYTES = 1_000_000  # 1 MB
    try:
        stat = path.stat()
        if stat.st_size > MAX_SIZE_BYTES:
            return (
                f"错误：文件 '{path}' 大小为 {stat.st_size} 字节，"
                f"超过安全限制 ({MAX_SIZE_BYTES} 字节)。"
                f"如需处理大文件，请使用专门的分块读取工具。"
            )
    except Exception:
        pass  # 某些特殊路径可能无法 stat，交给 read_text 处理

    try:
        content = path.read_text(encoding="utf-8", errors="replace")
        return content
    except Exception as e:
        return f"错误：读取文件失败 {type(e).__name__}: {e}"


read_file_tool = Tool(
    name="ReadFile",
    description="读取指定文本文件的内容，返回完整字符串。适用于查看代码、配置文件、日志等场景。",
    parameters={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "要读取的文件路径（相对路径或绝对路径）",
            }
        },
        "required": ["path"],
    },
    execute=_execute_read_file,
)
