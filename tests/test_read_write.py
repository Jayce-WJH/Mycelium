#!/usr/bin/env python3
"""
ReadFile / WriteFile 手动测试
"""

import tempfile
from pathlib import Path
from mycelium.tools.read_file import read_file_tool
from mycelium.tools.write_file import write_file_tool


def test_read_file_success():
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False) as f:
        f.write("hello world")
        tmp_path = f.name

    result = read_file_tool.execute({"path": tmp_path})
    assert result == "hello world"

    Path(tmp_path).unlink()
    print("✅ test_read_file_success 通过")


def test_read_file_not_exists():
    result = read_file_tool.execute({"path": "/tmp/this_file_does_not_exist_12345.txt"})
    assert "不存在" in result
    print("✅ test_read_file_not_exists 通过")


def test_read_file_is_directory():
    with tempfile.TemporaryDirectory() as tmp_dir:
        result = read_file_tool.execute({"path": tmp_dir})
        assert "是一个目录" in result
    print("✅ test_read_file_is_directory 通过")


def test_write_file_create():
    with tempfile.TemporaryDirectory() as tmp_dir:
        target = Path(tmp_dir) / "subdir" / "test.txt"
        result = write_file_tool.execute({"path": str(target), "content": "abc"})
        assert "已创建" in result
        assert target.read_text(encoding="utf-8") == "abc"
    print("✅ test_write_file_create 通过")


def test_write_file_update():
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False) as f:
        f.write("old")
        tmp_path = f.name

    result = write_file_tool.execute({"path": tmp_path, "content": "new"})
    assert "已更新" in result
    assert Path(tmp_path).read_text(encoding="utf-8") == "new"

    Path(tmp_path).unlink()
    print("✅ test_write_file_update 通过")


def test_read_file_size_limit():
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False) as f:
        # 写入超过 1MB 的内容
        f.write("x" * (1_000_000 + 1))
        tmp_path = f.name

    result = read_file_tool.execute({"path": tmp_path})
    assert "超过安全限制" in result

    Path(tmp_path).unlink()
    print("✅ test_read_file_size_limit 通过")


if __name__ == "__main__":
    test_read_file_success()
    test_read_file_not_exists()
    test_read_file_is_directory()
    test_write_file_create()
    test_write_file_update()
    test_read_file_size_limit()
    print("\n所有 Read/Write 测试通过 🎉")
