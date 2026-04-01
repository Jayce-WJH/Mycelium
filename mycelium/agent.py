"""
BeeAgent —— 第一只蜜蜂

参考 Claude Code 的 Agent Harness 架构：
- 对话循环驱动（while True async generator）
- 工具系统通过 Protocol 解耦
- 上下文状态保存在内存中的 messages 列表

这是蜂群的最小原子单元。
"""

from typing import AsyncIterator
from mycelium.llm.openrouter import OpenRouterClient
from mycelium.tools.base import ToolRegistry


class BeeAgent:
    """
    单只蜜蜂智能体。

    它的核心职责只有一个：维护对话上下文，并在 LLM 与普通文本、
    工具调用之间来回切换，直到产生最终答案。

    设计要点：
    - 不硬编码任何具体工具能力
    - 所有外部能力通过 ToolRegistry 注入
    - 这样蜂群里的不同蜜蜂可以携带不同的工具包
    """

    def __init__(
        self,
        llm_client: OpenRouterClient,
        registry: ToolRegistry,
        system_prompt: str | None = None,
        compat_mode: bool = False,
    ):
        self.llm = llm_client
        self.registry = registry
        self.compat_mode = compat_mode
        self.messages: list[dict] = []

        # 初始化系统提示词，告诉 LLM 它可以调用哪些工具
        default_system = self._build_system_prompt()
        self.messages.append({
            "role": "system",
            "content": system_prompt or default_system,
        })

    def _build_system_prompt(self) -> str:
        """
        构造默认 system prompt。
        把当前Registry里所有工具的名字和用途列出来，让 LLM 知道它能做什么。
        """
        tool_names = [t.name for t in self.registry.list_tools()]
        tools_text = "\n".join(
            f"- {t.name}: {t.description}" for t in self.registry.list_tools()
        )
        return (
            "你是一个智能体助手，可以通过工具与环境交互。\n"
            f"当前可用工具：{', '.join(tool_names) or '无'}\n"
            f"工具详情：\n{tools_text}\n\n"
            "如果用户的问题需要工具才能完成，请使用对应工具；"
            "否则直接回答。"
        )

    async def run(self, user_input: str) -> AsyncIterator[str]:
        """
        蜜蜂的心跳：异步生成器对话循环。

        生命周期：
        1. 接收用户输入，追加到上下文
        2. 调用 LLM
        3. 若返回普通文本 -> yield 给用户，结束
        4. 若返回 tool_calls -> yield 进度提示 -> 执行工具 -> 把结果追加回上下文 -> 回到 2
        """
        # 1. 把用户消息加入上下文
        self.messages.append({"role": "user", "content": user_input})
        turn = 0  # 记录对话轮次，用于更清晰的日志展示

        while True:
            turn += 1
            # 2. 调用 LLM，传入可用工具列表
            tools = self.registry.definitions() or None
            response = await self.llm.chat(self.messages, tools=tools)

            # OpenRouter / OpenAI 格式：choices[0].message
            choice = response.get("choices", [{}])[0]
            message = choice.get("message", {})
            content = message.get("content", "")
            tool_calls = message.get("tool_calls", [])

            # 先把 assistant 的回复（无论是文本还是工具调用意图）追加到上下文
            assistant_msg: dict = {"role": "assistant"}
            if content:
                assistant_msg["content"] = content
            if tool_calls:
                assistant_msg["tool_calls"] = tool_calls
            self.messages.append(assistant_msg)

            # 3. 如果没有工具调用，直接输出答案并结束
            if not tool_calls:
                yield content or "（无回复）"
                break

            # 4. 执行工具调用，并将结果回填，然后回到循环开头继续
            for idx, call in enumerate(tool_calls, start=1):
                call_id = call.get("id", "")
                function_info = call.get("function", {})
                tool_name = function_info.get("name", "")
                tool_args_raw = function_info.get("arguments", "{}")

                # 清晰展示：第几轮、第几个工具、工具名、参数
                yield f"🛠️  [第{turn}轮·第{idx}个] {tool_name}({tool_args_raw})"

                tool = self.registry.get(tool_name)
                if tool is None:
                    result_text = f"错误：未找到工具 '{tool_name}'。"
                else:
                    import json
                    try:
                        args = json.loads(tool_args_raw) if isinstance(tool_args_raw, str) else tool_args_raw
                    except json.JSONDecodeError:
                        args = {}
                    result_text = tool.execute(args)

                if self.compat_mode:
                    # 兼容模式：部分国产 OpenAI 兼容端点不支持 role="tool"，
                    # 把结果包装成 user 消息，让模型继续理解上下文。
                    self.messages.append({
                        "role": "user",
                        "content": f"[工具 {tool_name} 执行结果]\n{result_text}",
                    })
                else:
                    self.messages.append({
                        "role": "tool",
                        "tool_call_id": call_id,
                        "name": tool_name,
                        "content": result_text,
                    })

            # 继续循环（continue 是显式的，为了可读性保留注释）
            # 之前这里有一段硬编码的 final_response + break，改成了真正的循环
