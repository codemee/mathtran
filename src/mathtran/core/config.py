"""設定：API key 以環境變數優先，其次使用者設定檔；另外保存介面偏好（語系、配色…）。"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

CONFIG_PATH = Path.home() / ".mathtran" / "config.json"
DEFAULT_MODEL = "claude-sonnet-5-5"

# 介面偏好。存在伺服器端的設定檔，而不是瀏覽器的 localStorage：
# 桌面版每次啟動的本機埠號都不同，localStorage 以「來源（含埠號）」區分，重開就會遺失。
DEFAULT_SETTINGS: dict = {
    "lang": "system",        # system | zh-TW | en
    "theme": "system",       # system | light | dark
    "thumb": 170,            # 縮圖大小（px）
    "formats": ["svg"],      # 匯出格式（複選）
}
LANG_CHOICES = ("system", "zh-TW", "en")
THEME_CHOICES = ("system", "light", "dark")
FORMAT_CHOICES = ("svg", "pdf", "tex")
THUMB_RANGE = (100, 320)


def _load() -> dict:
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _write(data: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def get_api_key() -> str | None:
    return os.environ.get("ANTHROPIC_API_KEY") or _load().get("api_key")


def save_api_key(key: str) -> None:
    data = _load()
    data["api_key"] = key
    _write(data)


# 辨識可用的模型（需要支援圖片輸入）。介面上以下拉選單列出，也可以自己輸入其他模型 ID（例如之後新發布的模型）
MODEL_CHOICES = ("claude-haiku-5-5", "claude-sonnet-5-5", "claude-opus-5-5", "claude-fable-5-2")
_MODEL_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,99}")


def get_model() -> str:
    return os.environ.get("MATHTRAN_MODEL") or _load().get("model") or DEFAULT_MODEL


def model_locked() -> bool:
    """模型是否由環境變數 MATHTRAN_MODEL 指定（環境變數優先，設定檔的值不會生效）。"""
    return bool(os.environ.get("MATHTRAN_MODEL"))


def save_model(model: str) -> str:
    """儲存要用的模型；空字串 = 恢復預設。格式不合法就丟 ValueError("model")。"""
    model = model.strip()
    if model and not _MODEL_ID.fullmatch(model):
        raise ValueError("model")
    data = _load()
    if model and model != DEFAULT_MODEL:
        data["model"] = model
    else:
        data.pop("model", None)
    _write(data)
    return get_model()


def _clean_setting(key: str, value):
    """驗證並正規化單一設定值；不合法就丟 ValueError(key)。"""
    if key == "lang" and value in LANG_CHOICES:
        return value
    if key == "theme" and value in THEME_CHOICES:
        return value
    if key == "thumb" and isinstance(value, int) and not isinstance(value, bool) \
            and THUMB_RANGE[0] <= value <= THUMB_RANGE[1]:
        return value
    if key == "formats" and isinstance(value, list) and value \
            and all(v in FORMAT_CHOICES for v in value):
        return [f for f in FORMAT_CHOICES if f in value]   # 去重並固定順序
    raise ValueError(key)


def get_settings() -> dict:
    """已儲存的偏好；缺少或損毀的項目退回預設值（設定檔被手動改壞也不會讓程式出錯）。"""
    out = {k: (list(v) if isinstance(v, list) else v) for k, v in DEFAULT_SETTINGS.items()}
    saved = _load().get("settings")
    if isinstance(saved, dict):
        for key, value in saved.items():
            try:
                out[key] = _clean_setting(key, value)
            except ValueError:
                pass
    return out


def update_settings(patch: dict) -> dict:
    """只更新 patch 裡的項目（其餘保留）；任何一項不合法就整批不寫入並丟 ValueError(key)。"""
    cleaned = {k: _clean_setting(k, v) for k, v in patch.items()}
    data = _load()
    settings = data.get("settings") if isinstance(data.get("settings"), dict) else {}
    settings.update(cleaned)
    data["settings"] = settings
    _write(data)
    return get_settings()
