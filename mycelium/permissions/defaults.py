"""
默认权限规则配置。

把过去散落在各工具里的硬编码安全边界收敛到这里，
作为 PermissionGuard 的出厂默认值。
"""

from mycelium.permissions.guard import PermissionGuard


import os
from pathlib import Path


def default_guard(config_path=None) -> PermissionGuard:
    """
    返回带默认安全规则的 PermissionGuard。

    当前默认规则：
    - Bash 禁止明显高危前缀（与早期 bash.py 的 blocked_prefixes 等价）
    - 其它工具默认不设限（fail-open），由用户通过配置文件追加

    若未显式传入 config_path，会自动探测当前目录下的
    .mycelium/permissions.json 或 .mycelium/permissions.yaml。
    """
    if config_path is None:
        cwd = Path(os.getcwd())
        config_dir = cwd / ".mycelium"
        for filename in ("permissions.json", "permissions.yaml", "permissions.yml"):
            candidate = config_dir / filename
            if candidate.exists():
                config_path = candidate
                break

    return PermissionGuard(
        deny=[
            # 与早期 bash.py 中 blocked_prefixes 等价
            # :* 前缀规则 = 以该字符串开头的任何命令
            "Bash(rm -rf /:*)",
            "Bash(> /dev/sda:*)",
            "Bash(mkfs.:*)",
            "Bash(dd if=*)",
            # 写系统敏感目录
            "WriteFile(/etc/*)",
            "WriteFile(/sys/*)",
            "WriteFile(/proc/*)",
            "WriteFile(/dev/*)",
        ],
        ask=[],
        allow=[],
        config_path=config_path,
    )
