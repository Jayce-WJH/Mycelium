# Mycelium 项目进度记录

> 最后更新：2026-04-02
> 状态：Phase A (ReadFile/WriteFile) + Phase C (PermissionGuard) 已完成，29 项测试全绿。

---

## 一、当前已完成的架构

### 1.1 核心模块 (`mycelium/`)

| 文件 | 职责 | 状态 |
|------|------|------|
| `agent.py` | `BeeAgent`：异步生成器对话循环（`while True`），支持多轮 tool_calls | 已完成 |
| `llm/openrouter.py` | `LLMClient`：OpenAI 兼容 API 客户端，支持自定义 `base_url` 和模型 | 已完成 |
| `tools/base.py` | `Tool` dataclass + `ToolRegistry`：链式注册、OpenAI functions 格式导出 | 已完成 |
| `tools/bash.py` | `Bash` 工具：执行 shell 命令，带 UTF-8 编码容错和超时 | 已完成 |
| `tools/read_file.py` | `ReadFile` 工具：读取文本文件，带 **1MB 大小限制** | 已完成 |
| `tools/write_file.py` | `WriteFile` 工具：写入文件，自动创建父目录 | 已完成 |
| `permissions/guard.py` | `PermissionGuard`：权限管线核心，支持 deny / ask / allow 三态 | 已完成 |
| `permissions/defaults.py` | `default_guard()`：出厂默认规则 + 自动加载 `.mycelium/permissions.json` | 已完成 |

### 1.2 已解决的关键问题

1. **国产端点兼容 (`compat_mode`)**
   - 部分国产 OpenAI 兼容端点不支持 `role: tool`。
   - `compat_mode=True` 时会把工具结果包装成 `role: user` 消息，并附带 `call_id`，帮助模型对应上下文。

2. **多轮 tool_call 循环**
   - 早期版本在第一次 tool_call 后就硬编码 `break`，导致 LLM 想调用第二轮时被截断。
   - 已修复为真正的 `while True` 循环，只有 `tool_calls` 为空时才输出并结束。

3. **Windows GBK 编码问题**
   - `Bash` 工具的 `subprocess.run` 显式指定 `encoding="utf-8", errors="replace"`。

4. **权限系统安全补丁**
   - Bash 复合命令（如 `echo 1; rm -rf /`）会被按 `; && ||` 拆分检查，防止绕过 deny 规则。
   - ReadFile 增加 1MB 大小上限，防止误读超大日志/二进制文件。
   - BeeAgent 增加 `required` 字段校验，缺失必填参数时不调用工具。

---

## 二、PermissionGuard 设计要点

### 2.1 集成方式

采用 **Registry 中间件（方案 A）**，最贴合 Claude Code Agent Harness 的架构思想：

- `ToolRegistry` 初始化时可注入 `guard`。
- `register(tool)` 时，`guard.wrap(tool)` 自动包裹一层权限检查。
- `BeeAgent` 核心代码完全零改动。

### 2.2 规则语法

参考 Claude Code 的 `permissionRuleValue` 格式：

```text
ToolName                -> 工具级规则，命中整个工具
ToolName(exact_cmd)     -> 精确匹配
ToolName(prefix:*)      -> 前缀匹配（向后兼容语法）
ToolName(wild*card)     -> fnmatch 通配符匹配
```

### 2.3 优先级铁律（与 Claude Code 一致）

`deny > ask > allow > 默认放行`

- 第一版 `ask` 降级为 `deny`，暂不支持交互式终端确认。
- 配置文件中的规则追加在代码默认规则之后（`deny` 在前者优先）。

### 2.4 默认安全规则

```python
deny=[
    "Bash(rm -rf /:*)",
    "Bash(> /dev/sda:*)",
    "Bash(mkfs.:*)",
    "Bash(dd if=*)",
    "WriteFile(/etc/*)",
    "WriteFile(/sys/*)",
    "WriteFile(/proc/*)",
    "WriteFile(/dev/*)",
]
```

---

## 三、测试覆盖

| 测试文件 | 覆盖内容 |
|----------|----------|
| `tests/test_bee.py` | ToolRegistry、Bash 执行、BeeAgent 对话循环、必填参数校验、compat_mode_call_id |
| `tests/test_permissions.py` | 默认规则、精确/前缀/通配符匹配、优先级、复合命令、配置自动加载、wrap 机制 |
| `tests/test_read_write.py` | ReadFile 成功/失败/目录、WriteFile 创建/更新、1MB 大小限制 |
| `tests/test_bee_manual.py` | 手动运行示例的自动化断言 |

运行方式：

```bash
uv run pytest tests/ -v --ignore=tests/test_openrouter.py
```

（`test_openrouter.py` 依赖外部 fixture，已知 ERROR，不影响核心功能。）

---

## 四、中优先级待办（审计发现，未修复）

以下问题已在审计阶段识别，当前暂不深究，留待后续迭代：

| # | 问题 | 影响 | 未来修复方向 |
|---|------|------|--------------|
| 1 | **上下文无限增长** | `BeeAgent.messages` 只追加不压缩，长会话必爆上下文 | 引入 compaction / 摘要策略 |
| 2 | **WriteFile 无破坏性标记** | 无法按"是否覆盖"做差异化权限策略 | 给 `Tool` 加 `isDestructive(input)` 方法 |
| 3 | **Tool 缺 aliases / searchHint** | 工具换名无法向后兼容；未来 ToolSearch 需要关键词 | 扩展 `Tool` dataclass |
| 4 | **Bash 输出重定向未单独解析** | `> /etc/passwd` 只能按原始字符串匹配，精细度不足 | 参考 Claude Code 的 `extractOutputRedirections` |
| 5 | **无 AI classifier auto 模式** | 所有 ask 都降级为 deny，无法自动审批低风险操作 | 未来引入 YOLO / 规则分类器 |
| 6 | **无子 Agent / bubble 模式** | 蜂群架构尚未开始 | 待 BeeAgent 稳定后再扩展 |

---

## 五、近期可继续的方向（按优先级排序）

1. **上下文压缩 (`compaction`)**
   - 当 `messages` 长度或 token 数超过阈值时，对早期轮次进行摘要替换。
   - 这是蜂群化的前置条件（子 Agent 需要把结果摘要传回父 Agent）。

2. **Grep / Glob 工具**
   - 让蜜蜂能"搜索代码"而不仅是"读取单个文件"。
   - 参考 Claude Code 的 `Grep` 和 `Glob` 实现。

3. **EditFile 工具（基于 diff）**
   - 从只读的 `ReadFile` + 全量写的 `WriteFile` 进化到行级/块级编辑。
   - 这是 Agent 做代码重构的核心能力。

4. **Auto 模式 / 分类器**
   - 用轻量级规则或本地小模型，对常见的 `ask` 场景自动放行/拒绝。

---

## 六、关键技术参考

- **Claude Code Agent Harness 资料**：`temp_info/claude-code-book/`
  - 第2章：对话循环
  - 第3章：工具系统
  - 第4章：权限管线（Permission Pipeline）
- **Claude Code 类型定义参考**：`temp_info/claude-code-haha/src/Tool.ts`、`src/types/permissions.ts`、`src/utils/permissions/`

---

## 七、快速启动命令

```bash
# 安装依赖
uv pip install -e ".[dev]"

# 运行测试
uv run pytest tests/ -v --ignore=tests/test_openrouter.py

# 运行示例（需先配置 .env）
uv run python examples/demo_bash.py
uv run python examples/demo_read_write.py
```
