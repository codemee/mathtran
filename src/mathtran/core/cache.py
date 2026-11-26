"""辨識結果快取：以圖片內容的 SHA-256 為鍵，存在使用者目錄的 cache.json。

只存 LaTeX 文字（以及模型名稱、是否被使用者手動修改），不存圖片本身。
CLI、網頁、桌面共用同一份快取。
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from pathlib import Path

from . import config

_lock = threading.Lock()


def cache_path() -> Path:
    # 每次呼叫才計算，測試時可用 monkeypatch 改 config.CONFIG_PATH
    return config.CONFIG_PATH.parent / "cache.json"


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _load() -> dict:
    try:
        data = json.loads(cache_path().read_text(encoding="utf-8"))
        entries = data.get("entries")
        return entries if isinstance(entries, dict) else {}
    except (OSError, ValueError, AttributeError):
        return {}


def _save(entries: dict) -> None:
    path = cache_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(
        json.dumps({"version": 1, "entries": entries}, ensure_ascii=False), encoding="utf-8"
    )
    os.replace(tmp, path)  # 原子替換，避免寫到一半損毀


def _valid(entry: dict, min_prompt: int) -> bool:
    """使用者手動修改過的永遠有效；其餘要求是用不低於 min_prompt 版的提示詞辨識出來的。"""
    return bool(entry.get("edited")) or entry.get("prompt", 0) >= min_prompt


def get(h: str, *, min_prompt: int = 0) -> dict | None:
    """回傳 {"latex", "edited", "model", "prompt", "ts"}；沒有或已過期則 None。"""
    with _lock:
        entry = _load().get(h)
    return entry if entry and _valid(entry, min_prompt) else None


def lookup(hashes: list[str], *, min_prompt: int = 0) -> dict[str, dict]:
    with _lock:
        entries = _load()
    return {h: entries[h] for h in hashes if h in entries and _valid(entries[h], min_prompt)}


def put(
    h: str,
    latex: str,
    *,
    model: str | None = None,
    edited: bool = False,
    prompt: int | None = None,
) -> None:
    """prompt：辨識時用的提示詞版本。手動修改（edited=True）時沿用舊值，不更新。"""
    with _lock:
        entries = _load()
        old = entries.get(h, {})
        entries[h] = {
            "latex": latex,
            "edited": edited,
            "model": model or old.get("model"),
            "prompt": prompt if prompt is not None else old.get("prompt", 0),
            "ts": int(time.time()),
        }
        _save(entries)


def count() -> int:
    with _lock:
        return len(_load())


def stats() -> dict:
    """{"count": 筆數, "edited": 其中手動修改過的筆數, "bytes": 檔案大小, "path": 檔案位置}。"""
    with _lock:
        entries = _load()
    path = cache_path()
    try:
        size = path.stat().st_size
    except OSError:
        size = 0
    return {
        "count": len(entries),
        "edited": sum(1 for e in entries.values() if e.get("edited")),
        "bytes": size,
        "path": str(path),
    }


def remove(hashes: list[str]) -> int:
    """刪除指定雜湊的快取，回傳實際刪掉幾筆。"""
    with _lock:
        entries = _load()
        gone = [h for h in set(hashes) if h in entries]
        for h in gone:
            del entries[h]
        if gone:
            _save(entries)
        return len(gone)


def clear() -> int:
    with _lock:
        n = len(_load())
        _save({})
        return n
