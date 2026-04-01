#!/usr/bin/env python3
"""
PermissionGuard 手动测试
"""

import json
import tempfile
from pathlib import Path

from mycelium.permissions import PermissionGuard, default_guard


def test_default_guard_blocks_dangerous_bash():
    g = default_guard()

    # 应拦截
    assert g.evaluate("Bash", {"command": "rm -rf /"}).behavior == "deny"
    assert g.evaluate("Bash", {"command": "> /dev/sda"}).behavior == "deny"
    assert g.evaluate("Bash", {"command": "mkfs.ext4 /dev/sdb1"}).behavior == "deny"
    assert g.evaluate("Bash", {"command": "dd if=/dev/zero of=/dev/sda"}).behavior == "deny"

    # 应放行
    assert g.evaluate("Bash", {"command": "ls -la"}).behavior == "allow"
    assert g.evaluate("Bash", {"command": "git status"}).behavior == "allow"

    print("✅ test_default_guard_blocks_dangerous_bash 通过")


def test_exact_match():
    g = PermissionGuard(deny=["Bash(pwd)"])
    assert g.evaluate("Bash", {"command": "pwd"}).behavior == "deny"
    assert g.evaluate("Bash", {"command": "pwdx"}).behavior == "allow"
    print("✅ test_exact_match 通过")


def test_prefix_match():
    g = PermissionGuard(deny=["Bash(git:*)"])
    assert g.evaluate("Bash", {"command": "git status"}).behavior == "deny"
    assert g.evaluate("Bash", {"command": "git"}).behavior == "deny"
    # git:* 前缀匹配只要 command 以 "git" 开头即命中（与 Claude 的 :* 语义一致）
    assert g.evaluate("Bash", {"command": "gitcommit"}).behavior == "deny"
    print("✅ test_prefix_match 通过")


def test_wildcard_match():
    g = PermissionGuard(deny=["Bash(rm -rf *)"])
    assert g.evaluate("Bash", {"command": "rm -rf /tmp"}).behavior == "deny"
    assert g.evaluate("Bash", {"command": "rm -rf"}).behavior == "allow"  # 无尾部参数，不匹配
    print("✅ test_wildcard_match 通过")


def test_tool_level_rule():
    g = PermissionGuard(deny=["Bash"])
    assert g.evaluate("Bash", {"command": "echo hello"}).behavior == "deny"
    assert g.evaluate("ReadFile", {"path": "foo.txt"}).behavior == "allow"
    print("✅ test_tool_level_rule 通过")


def test_priority_deny_over_allow():
    g = PermissionGuard(deny=["Bash(git *)"], allow=["Bash(git status)"])
    # deny 优先级高于 allow
    assert g.evaluate("Bash", {"command": "git status"}).behavior == "deny"
    print("✅ test_priority_deny_over_allow 通过")


def test_ask_downgraded_to_deny():
    g = PermissionGuard(ask=["Bash(curl *)"])
    result = g.evaluate("Bash", {"command": "curl https://example.com"})
    assert result.behavior == "deny"
    assert "需要确认" in result.message
    print("✅ test_ask_downgraded_to_deny 通过")


def test_config_file_override():
    with tempfile.TemporaryDirectory() as tmp_dir:
        cfg = Path(tmp_dir) / "perms.json"
        cfg.write_text(
            json.dumps({"deny": ["Bash(ls)"], "allow": ["Bash(pwd)"]}),
            encoding="utf-8",
        )
        g = PermissionGuard(config_path=cfg)

        assert g.evaluate("Bash", {"command": "ls"}).behavior == "deny"
        assert g.evaluate("Bash", {"command": "pwd"}).behavior == "allow"
        assert g.evaluate("Bash", {"command": "whoami"}).behavior == "allow"

    print("✅ test_config_file_override 通过")


def test_write_file_system_paths_blocked_by_default():
    g = default_guard()

    assert g.evaluate("WriteFile", {"path": "/etc/passwd"}).behavior == "deny"
    assert g.evaluate("WriteFile", {"path": "/sys/kernel/debug"}).behavior == "deny"
    assert g.evaluate("WriteFile", {"path": "/proc/cpuinfo"}).behavior == "deny"
    assert g.evaluate("WriteFile", {"path": "/dev/sda"}).behavior == "deny"

    # 普通项目文件放行
    assert g.evaluate("WriteFile", {"path": "src/main.py"}).behavior == "allow"

    print("✅ test_write_file_system_paths_blocked_by_default 通过")


def test_wrap_tool():
    from mycelium.tools.base import Tool

    def dummy_execute(args):
        return "executed"

    tool = Tool(name="TestTool", description="test", parameters={}, execute=dummy_execute)
    g = PermissionGuard(deny=["TestTool"])
    wrapped = g.wrap(tool)

    # 被拦截时不调用原 execute
    assert wrapped.execute({}) == "错误：权限策略拦截：规则 'TestTool' 命中。"
    # 放行时正常调用
    g2 = PermissionGuard(allow=["TestTool"])
    wrapped2 = g2.wrap(tool)
    assert wrapped2.execute({}) == "executed"

    print("✅ test_wrap_tool 通过")


def test_bash_compound_command_blocked():
    """复合命令中只要有一个 segment 命中 deny 就应该拦截。"""
    g = PermissionGuard(deny=["Bash(rm -rf *)"])

    assert g.evaluate("Bash", {"command": "echo 1; rm -rf /tmp"}).behavior == "deny"
    assert g.evaluate("Bash", {"command": "echo 1 && rm -rf /tmp"}).behavior == "deny"
    assert g.evaluate("Bash", {"command": "echo 1 || rm -rf /tmp"}).behavior == "deny"
    #  safe compound should still pass
    assert g.evaluate("Bash", {"command": "echo 1; echo 2"}).behavior == "allow"
    print("✅ test_bash_compound_command_blocked 通过")


def test_default_guard_auto_load_config():
    """default_guard 应在当前目录下自动探测 .mycelium/permissions.json。"""
    import os

    original_cwd = os.getcwd()
    with tempfile.TemporaryDirectory() as tmp_dir:
        os.chdir(tmp_dir)
        config_dir = Path(tmp_dir) / ".mycelium"
        config_dir.mkdir()
        cfg = config_dir / "permissions.json"
        cfg.write_text(json.dumps({"deny": ["Bash(ls)"]}), encoding="utf-8")

        g = default_guard()
        assert g.evaluate("Bash", {"command": "ls"}).behavior == "deny"

    os.chdir(original_cwd)
    print("✅ test_default_guard_auto_load_config 通过")


if __name__ == "__main__":
    test_default_guard_blocks_dangerous_bash()
    test_exact_match()
    test_prefix_match()
    test_wildcard_match()
    test_tool_level_rule()
    test_priority_deny_over_allow()
    test_ask_downgraded_to_deny()
    test_config_file_override()
    test_write_file_system_paths_blocked_by_default()
    test_wrap_tool()
    test_bash_compound_command_blocked()
    test_default_guard_auto_load_config()
    print("\n所有 PermissionGuard 测试通过 🎉")
