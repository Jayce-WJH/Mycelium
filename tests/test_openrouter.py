#!/usr/bin/env python3
"""
OpenRouter API 测试脚本
测试模型: qwen/qwen3.6-plus-preview:free

Usage:
    export OPENROUTER_API_KEY=your_key_here
    python tests/test_openrouter.py
"""

import os
import sys
import json

# 尝试导入 requests，如果没有则使用标准库 urllib
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    import urllib.request
    import urllib.error


API_URL = "https://openrouter.ai/api/v1/chat/completions"


def get_config():
    """从环境变量获取配置"""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("❌ 错误: 请设置 OPENROUTER_API_KEY 环境变量")
        print("   export OPENROUTER_API_KEY=your_key_here")
        sys.exit(1)

    return {
        "api_key": api_key,
        "model": os.getenv("OPENROUTER_MODEL", "qwen/qwen3.6-plus-preview:free"),
        "site_url": os.getenv("SITE_URL", "https://github.com/Jayce-WJH/Mycelium"),
        "site_name": os.getenv("SITE_NAME", "Mycelium Agent Framework")
    }


def test_with_requests(config):
    """使用 requests 库调用 API"""
    headers = {
        "Authorization": f"Bearer {config['api_key']}",
        "Content-Type": "application/json",
        "HTTP-Referer": config["site_url"],
        "X-Title": config["site_name"]
    }

    data = {
        "model": config["model"],
        "messages": [
            {"role": "user", "content": "你好，请用一句话介绍自己。你叫什么？"}
        ],
        "max_tokens": 100,
        "temperature": 0.7
    }

    print(f"🚀 正在调用 OpenRouter API...")
    print(f"📡 模型: {config['model']}")
    print(f"🔗 URL: {API_URL}")
    print("-" * 50)

    try:
        response = requests.post(API_URL, headers=headers, json=data, timeout=30)

        print(f"📊 HTTP 状态码: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(f"✅ API 调用成功!")
            print(f"\n📝 响应内容:")
            print(json.dumps(result, indent=2, ensure_ascii=False))

            # 提取回复文本
            if "choices" in result and len(result["choices"]) > 0:
                content = result["choices"][0].get("message", {}).get("content", "")
                print(f"\n💬 AI 回复:")
                print(content)

            return True
        else:
            print(f"❌ API 调用失败")
            print(f"错误响应: {response.text}")
            return False

    except requests.exceptions.Timeout:
        print(f"⏱️ 请求超时")
        return False
    except requests.exceptions.RequestException as e:
        print(f"❌ 请求异常: {e}")
        return False


def test_with_urllib(config):
    """使用标准库 urllib 调用 API（无依赖方案）"""
    headers = {
        "Authorization": f"Bearer {config['api_key']}",
        "Content-Type": "application/json",
        "HTTP-Referer": config["site_url"],
        "X-Title": config["site_name"]
    }

    data = {
        "model": config["model"],
        "messages": [
            {"role": "user", "content": "你好，请用一句话介绍自己。你叫什么？"}
        ],
        "max_tokens": 100,
        "temperature": 0.7
    }

    print(f"🚀 正在调用 OpenRouter API (使用 urllib)...")
    print(f"📡 模型: {config['model']}")
    print(f"🔗 URL: {API_URL}")
    print("-" * 50)

    try:
        req = urllib.request.Request(
            API_URL,
            data=json.dumps(data).encode('utf-8'),
            headers=headers,
            method='POST'
        )

        with urllib.request.urlopen(req, timeout=30) as response:
            print(f"📊 HTTP 状态码: {response.status}")

            body = response.read().decode('utf-8')
            result = json.loads(body)

            print(f"✅ API 调用成功!")
            print(f"\n📝 响应内容:")
            print(json.dumps(result, indent=2, ensure_ascii=False))

            # 提取回复文本
            if "choices" in result and len(result["choices"]) > 0:
                content = result["choices"][0].get("message", {}).get("content", "")
                print(f"\n💬 AI 回复:")
                print(content)

            return True

    except urllib.error.HTTPError as e:
        print(f"❌ HTTP 错误: {e.code}")
        print(f"错误信息: {e.read().decode('utf-8')}")
        return False
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        return False


def main():
    print("=" * 60)
    print("OpenRouter API 测试")
    print("=" * 60)
    print()

    config = get_config()
    success = False

    if HAS_REQUESTS:
        print("📦 检测到 requests 库，使用 requests 进行测试\n")
        success = test_with_requests(config)
    else:
        print("📦 未检测到 requests 库，使用标准库 urllib 进行测试\n")
        success = test_with_urllib(config)

    print()
    print("=" * 60)
    if success:
        print("✅ 测试通过! API 连接正常")
    else:
        print("❌ 测试失败! 请检查 API Key 和网络连接")
    print("=" * 60)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
