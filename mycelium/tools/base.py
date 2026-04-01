"""
Tool 协议与注册表

这是整个 Agent Harness 的核心接口层。
BeeAgent 不认识任何具体工具，它只通过这里的 protocol 与工具交互。
这样做的好处：新增工具无需修改 agent 核心代码，天然支持蜂群差异化。
"""

from dataclasses import dataclass
from typing import Callable, Dict, List


@dataclass(frozen=True)
class Tool:
    """
    单个工具的契约定义。

    参考 Claude Code 的 Tool<Input, Output, Progress> 设计，
    但第一版做极致简化：只保留 name / description / schema / execute。
    execute 的输入是 dict（由 LLM 根据 schema 生成的参数），
    输出是 str（直接回填到对话上下文中）。
    """
    name: str
    description: str
    parameters: dict
    execute: Callable[[dict], str]


class ToolRegistry:
    """
    工具注册表。

    每只蜜蜂在初始化时都会被注入一个 ToolRegistry。
    未来蜂群里不同的蜜蜂可以携带不同的注册表，实现分工。
    """

    def __init__(self, guard=None):
        # 用字典保证 O(1) 按名称查找，同时避免同名工具冲突（后者覆盖前者）
        self._tools: Dict[str, Tool] = {}
        self._guard = guard

    def register(self, tool: Tool) -> "ToolRegistry":
        """链式注册，方便在初始化时连续调用。"""
        # 如果存在权限守卫，先对工具进行包装
        wrapped_tool = self._guard.wrap(tool) if self._guard else tool
        self._tools[tool.name] = wrapped_tool
        return self

    def get(self, name: str) -> Tool | None:
        """按名称获取工具，找不到返回 None（让调用层决定如何处理）。"""
        return self._tools.get(name)

    def list_tools(self) -> List[Tool]:
        """返回当前注册的所有工具列表，供构造 LLM system prompt 使用。"""
        return list(self._tools.values())

    def definitions(self) -> List[dict]:
        """
        生成 OpenAI / Anthropic 兼容的 functions/tools 格式。
        这样 LLM Client 层可以直接把结果丢进 API 调用里。
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                },
            }
            for tool in self._tools.values()
        ]
