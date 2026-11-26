"""設定：API key 以環境變數優先，其次使用者設定檔。"""

from __future__ import annotations

import json
import os
from pathlib import Path

CONFIG_PATH = Path.home() / ".mathtran" / "config.json"
DEFAULT_MODEL = "claude-sonnet-5-5"


def _load() -> dict:
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def get_api_key() -> str | None:
    return os.environ.get("ANTHROPIC_API_KEY") or _load().get("api_key")


def save_api_key(key: str) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    data = _load()
    data["api_key"] = key
    CONFIG_PATH.write_text(json.dumps(data), encoding="utf-8")


def get_model() -> str:
    return os.environ.get("MATHTRAN_MODEL") or _load().get("model") or DEFAULT_MODEL
