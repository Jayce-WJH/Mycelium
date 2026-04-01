"""
PermissionGuard —— Agent 的护栏

参考 Claude Code 的 Permission Pipeline，但做最小可行实现：
- 规则优先级：deny > ask > allow
- 匹配语法：精确匹配、前缀匹配(:*)、通配符匹配(*)
- 第一版：ask 降级为 deny（无交互式确认）
- 支持代码内置默认规则 + JSON/YAML 配置文件覆盖
"""

from __future__ import annotations

import fnmatch
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable


@dataclass(frozen=True)
class PermissionResult:
    """权限检查结果。"""

    behavior: str  # "allow" | "deny" | "ask"
    message: str = ""


class PermissionGuard:
    """
    统一权限检查器。

    设计原则：
    - 规则按 deny → ask → allow 顺序匹配，命中即短路
    - 支持工具级规则（如 "Bash"）和参数级规则（如 "Bash(rm -rf *)"）
    - 默认规则写在代码里，配置文件可增量覆盖
    """

    def __init__(
        self,
        deny: list[str] | None = None,
        ask: list[str] | None = None,
        allow: list[str] | None = None,
        config_path: str | Path | None = None,
    ):
        self._deny: list[str] = list(deny or [])
        self._ask: list[str] = list(ask or [])
        self._allow: list[str] = list(allow or [])

        if config_path:
            self._load_config(Path(config_path))

    # ------------------------------------------------------------------
    # 规则解析与匹配
    # ------------------------------------------------------------------
    @staticmethod
    def _parse_rule(rule: str) -> tuple[str, str | None]:
        """
        解析规则字符串。

        示例：
        - "Bash"            -> ("Bash", None)         # 工具级
        - "Bash(git:*)"     -> ("Bash", "git:*")      # 前缀匹配
        - "Bash(rm -rf *)" -> ("Bash", "rm -rf *")   # 通配符匹配
        """
        stripped = rule.strip()
        if "(" in stripped and stripped.endswith(")"):
            tool_name = stripped[: stripped.find("(")]
            pattern = stripped[stripped.find("(") + 1 : -1]
            return tool_name, pattern
        return stripped, None

    def _match(self, rule_str: str, tool_name: str, args: dict) -> bool:
        """判断某条规则是否命中当前工具调用。"""
        rule_tool, rule_pattern = self._parse_rule(rule_str)
        if rule_tool != tool_name:
            return False
        if rule_pattern is None:
            return True  # 工具级规则，直接命中

        # 提取用于匹配的参数内容
        content = self._extract_match_content(tool_name, args)

        # 前缀匹配（向后兼容的 :* 语法）
        if rule_pattern.endswith(":*"):
            prefix = rule_pattern[:-2]
            return content.startswith(prefix)

        # 通配符匹配（只支持 * 和 ?，与 fnmatch 语义一致）
        if "*" in rule_pattern or "?" in rule_pattern:
            return fnmatch.fnmatch(content, rule_pattern)

        # 精确匹配
        return content == rule_pattern

    @staticmethod
    def _extract_match_content(tool_name: str, args: dict) -> str:
        """根据工具名提取用于规则匹配的核心参数字符串。"""
        if tool_name == "Bash":
            return args.get("command", "")
        if tool_name in ("ReadFile", "WriteFile"):
            return args.get("path", "")
        # 对于未知工具，回退到拼接全部参数
        return str(args)

    # ------------------------------------------------------------------
    # 核心决策接口
    # ------------------------------------------------------------------
    def evaluate(self, tool_name: str, args: dict) -> PermissionResult:
        """
        对一次工具调用进行权限判定。

        优先级：deny > ask > allow > 默认放行
        """
        for rule in self._deny:
            if self._match(rule, tool_name, args):
                return PermissionResult(
                    behavior="deny",
                    message=f"权限策略拦截：规则 '{rule}' 命中。",
                )

        for rule in self._ask:
            if self._match(rule, tool_name, args):
                # 第一版没有交互式确认，ask 降级为 deny
                return PermissionResult(
                    behavior="deny",
                    message=f"权限策略需要确认（暂按拒绝处理）：规则 '{rule}' 命中。",
                )

        for rule in self._allow:
            if self._match(rule, tool_name, args):
                return PermissionResult(behavior="allow")

        # 默认放行：在没有匹配到任何规则时，选择 fail-open
        # 原因：第一版没有交互式 ask，如果 fail-close 会导致大量正常操作被误杀
        return PermissionResult(behavior="allow")

    # ------------------------------------------------------------------
    # 配置加载
    # ------------------------------------------------------------------
    def _load_config(self, path: Path) -> None:
        """从配置文件加载覆盖规则。支持 JSON 和 YAML（若已安装 PyYAML）。"""
        if not path.exists():
            return

        content = path.read_text(encoding="utf-8")
        suffix = path.suffix.lower()

        if suffix == ".json":
            data = json.loads(content)
        elif suffix in (".yaml", ".yml"):
            try:
                import yaml
                data = yaml.safe_load(content)
            except ImportError:
                return  # 静默忽略，避免强制依赖 PyYAML
        else:
            # 未知后缀，尝试按 JSON 解析
            try:
                data = json.loads(content)
            except json.JSONDecodeError:
                return

        if not isinstance(data, dict):
            return

        # 配置文件中的规则追加到默认规则之后（deny 在前面，所以默认规则优先）
        self._deny.extend(data.get("deny", []))
        self._ask.extend(data.get("ask", []))
        self._allow.extend(data.get("allow", []))

    # ------------------------------------------------------------------
    # 与 Tool 系统集成的便捷方法
    # ------------------------------------------------------------------
    def wrap(self, tool) -> "Tool":
        """
        为某个 Tool 实例包裹一层权限检查。

        返回的新 Tool 在执行前会先调用 evaluate；
        若被拦截，则直接返回错误字符串而不触发原 execute。
        """
        from mycelium.tools.base import Tool

        original_execute: Callable[[dict], str] = tool.execute

        def guarded_execute(args: dict) -> str:
            result = self.evaluate(tool.name, args)
            if result.behavior in ("deny", "ask"):
                return f"错误：{result.message}"
            return original_execute(args)

        return Tool(
            name=tool.name,
            description=tool.description,
            parameters=tool.parameters,
            execute=guarded_execute,
        )
