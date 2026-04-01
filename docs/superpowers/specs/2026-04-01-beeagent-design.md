# BeeAgent Lv.2 设计文档

## 目标
构建第一只"协议蜜蜂"——一个最小但可扩展的 Python Agent Harness，具备对话循环和工具注册能力。

## 核心设计

### 1. 架构
- `BeeAgent` 不认识任何具体工具，只通过 `Tool` 协议和 `ToolRegistry` 与工具交互。
- 工具是"插件式"注册的，未来扩展工具只需新增一个文件并向 Registry 注册。
- 不同蜜蜂实例可以通过注入不同 Registry 实现能力差异化（蜂群扩展的基础）。

### 2. Tool 协议
```python
@dataclass
class Tool:
    name: str
    description: str
    parameters: dict        # JSON Schema 子集
    execute: Callable[[dict], str]
```
返回 `str` 可直接塞回 LLM messages，第一版保持最简。

### 3. 对话循环
`BeeAgent.run(user_input)` 执行以下步骤：
1. 将用户消息 append 到 `messages` 列表
2. 调用 OpenRouter API
3. 若返回普通文本 → yield 出来，结束
4. 若要调用工具 → yield 调用提示 → 执行工具 → 把结果 append 回 messages → 回到步骤 2

第一版只支持单轮工具调用（调用一次工具后直接返回最终答案）。

### 4. 目录结构
```
mycelium/
├── __init__.py
├── agent.py              # BeeAgent 类
├── tools/
│   ├── __init__.py
│   ├── base.py           # Tool + ToolRegistry
│   └── bash.py           # Bash 工具实现
├── llm/
│   ├── __init__.py
│   └── openrouter.py     # OpenRouter 客户端封装
examples/
└── demo_bash.py          # 运行示例
tests/
└── test_bee.py           # 基础测试
```

### 5. 第一版功能范围
- 注册并使用 `Bash` 工具
- 能完成如"统计当前目录下文件数量"之类的简单任务
- 代码必须有清晰注释，解释"为什么"这样设计

## 参考
- Claude Code Agent Harness 架构（`temp_info/claude-code-book`）
- 设计原则见 `AGENTS.md`
