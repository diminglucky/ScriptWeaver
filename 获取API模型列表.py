#!/usr/bin/env python3
"""获取 OpenAI 兼容 API 的模型列表。

用法:
1) 在环境变量中设置 API_KEY 和 BASE_URL（推荐）
2) 或设置 MODEL_LIST_API_KEY / MODEL_LIST_BASE_URL
"""

from __future__ import annotations

import json
import os

import requests
from dotenv import load_dotenv


def main() -> int:
    load_dotenv()
    api_key = os.getenv("MODEL_LIST_API_KEY") or os.getenv("API_KEY")
    base_url = os.getenv("MODEL_LIST_BASE_URL") or os.getenv("BASE_URL")

    if not api_key:
        print("ERROR: missing API key. Set MODEL_LIST_API_KEY or API_KEY.")
        return 1
    if not base_url:
        print("ERROR: missing BASE_URL. Set MODEL_LIST_BASE_URL or BASE_URL.")
        return 1

    base_url = base_url.rstrip("/")
    print("=" * 80)
    print("Fetching models from:", base_url)
    print("=" * 80)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "User-Agent": "Mozilla/5.0",
    }

    try:
        response = requests.get(f"{base_url}/models", headers=headers, timeout=10)
        response.raise_for_status()
        result = response.json()
    except Exception as e:
        print(f"ERROR: request failed: {e}")
        return 2

    data = result.get("data") if isinstance(result, dict) else None
    if not isinstance(data, list):
        print(f"ERROR: unexpected response format: {result}")
        return 3

    models = [m.get("id", "") for m in data if isinstance(m, dict) and m.get("id")]
    print(f"\nOK: fetched {len(models)} model(s)\n")
    for i, model in enumerate(models, 1):
        print(f"{i:3d}. {model}")

    with open("available_models.json", "w", encoding="utf-8") as f:
        json.dump({"models": models}, f, indent=2, ensure_ascii=False)
    print("\nSaved to available_models.json")
    print("models =", models)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
