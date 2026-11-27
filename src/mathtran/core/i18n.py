"""後端訊息的多語系（繁體中文 / English）。

前端每個請求都會帶 `X-Lang` 標頭（已解析好的 zh-TW 或 en），由 server 的 middleware 存進
contextvar，核心函式（ocr / render / batch）丟錯誤時用 tr() 取當下語言的訊息。
沒有標頭（例如命令列）時，依序用環境變數 MATHTRAN_LANG、系統語言。
"""

from __future__ import annotations

import contextvars
import locale
import os
import sys

LANGS = ("zh-TW", "en")

_current: contextvars.ContextVar[str | None] = contextvars.ContextVar("mathtran_lang", default=None)


def normalize(code: str | None) -> str | None:
    """把 zh、zh-Hant、zh_TW、en-US… 對應到支援的語言；不認得則 None。"""
    if not code:
        return None
    c = code.strip().replace("_", "-").lower()
    if c.startswith("zh"):
        return "zh-TW"
    if c.startswith("en"):
        return "en"
    return None


def system_lang() -> str:
    """作業系統的介面語言：中文系統 → zh-TW，其他 → en。"""
    if sys.platform == "win32":
        try:
            import ctypes

            lang_id = ctypes.windll.kernel32.GetUserDefaultUILanguage()
            return "zh-TW" if (lang_id & 0xFF) == 0x04 else "en"   # 0x04 = LANG_CHINESE
        except Exception:
            pass
    for var in ("LC_ALL", "LC_MESSAGES", "LANG"):
        found = normalize(os.environ.get(var))
        if found:
            return found
    try:
        return normalize(locale.getlocale()[0]) or "en"
    except Exception:
        return "en"


def set_lang(code: str | None):
    """設定目前請求的語言，回傳 token（用 reset_lang 還原）。不認得的語言會被忽略。"""
    return _current.set(normalize(code))


def reset_lang(token) -> None:
    _current.reset(token)


def _saved_lang() -> str | None:
    """使用者在介面選的語言偏好（選「跟隨系統」時為 None）。"""
    try:
        from . import config

        return normalize(config.get_settings().get("lang"))
    except Exception:
        return None


def current_lang() -> str:
    """順序：請求標頭 → 環境變數 MATHTRAN_LANG → 介面偏好 → 系統語言。"""
    return _current.get() or normalize(os.environ.get("MATHTRAN_LANG")) or _saved_lang() or system_lang()


MESSAGES: dict[str, dict[str, str]] = {
    "zh-TW": {
        # ocr
        "api_key_missing": "未設定 API key：請設定環境變數 ANTHROPIC_API_KEY，或執行 mathtran config --api-key <KEY>",
        "unsupported_image": "不支援的圖片格式（支援 PNG / JPEG / WebP / GIF）",
        "api_failed": "Claude API 呼叫失敗：{err}",
        # render
        "tectonic_missing": "找不到 tectonic，請先執行：scoop install tectonic（macOS / Linux：brew install tectonic）",
        "compile_failed": "LaTeX 編譯失敗：\n{log}",
        "cjk_font_missing": "找不到中文字型「{font}」，請安裝該字型，或設定環境變數 MATHTRAN_CJK_FONT 指定其他字型名稱。\n",
        "tex_cjk_note": "% 含中日韓字元：請以 XeLaTeX 編譯（xelatex），並確認系統有對應字型",
        # batch
        "empty_skipped": "{name}：沒有 LaTeX 內容，已略過",
        # server
        "bad_fmt": "fmt 必須是 svg、pdf 或 tex",
        "bad_hash": "hash 格式不正確",
        "bad_formats": "formats 必須是 svg / pdf / tex 的非空組合",
        "no_items": "沒有要匯出的項目",
        "all_failed": "全部匯出失敗：\n{details}",
        "bad_setting": "設定值不正確：{key}",
        # cli
        "out_written": "已輸出 {path}",
        "bad_ext": "輸出副檔名必須是 .svg、.pdf 或 .tex",
        "no_images": "找不到圖片：{path}",
        "need_dir_output": "多張圖片（或資料夾）時，-o 要指定一個輸出資料夾（不能是 .svg / .pdf / .tex 檔）",
        "format_needs_dir": "--format 只用在輸出到資料夾；輸出成檔案時，副檔名就是格式",
        "batch_summary": "完成：{ok} 張成功、{failed} 張失敗，共輸出 {files} 個檔案到 {dir}",
        "config_saved": "已儲存至 {path}",
        "key_set": "API key：已設定",
        "key_unset": "API key：未設定",
        "model_now": "辨識模型：{model}",
        "cache_cleared": "已清除 {n} 筆快取",
        "cache_stats": "{count} 筆快取（其中 {edited} 筆為手動修改，{kb} KB）：{path}",
    },
    "en": {
        "api_key_missing": "No API key set: set the ANTHROPIC_API_KEY environment variable, or run mathtran config --api-key <KEY>",
        "unsupported_image": "Unsupported image format (PNG / JPEG / WebP / GIF are supported)",
        "api_failed": "Claude API call failed: {err}",
        "tectonic_missing": "tectonic not found. Install it first: scoop install tectonic (macOS / Linux: brew install tectonic)",
        "compile_failed": "LaTeX compilation failed:\n{log}",
        "cjk_font_missing": "CJK font \"{font}\" not found. Install it, or set the MATHTRAN_CJK_FONT environment variable to another font name.\n",
        "tex_cjk_note": "% Contains CJK characters: compile with XeLaTeX (xelatex) and make sure a matching font is installed",
        "empty_skipped": "{name}: no LaTeX content, skipped",
        "bad_fmt": "fmt must be svg, pdf or tex",
        "bad_hash": "Invalid hash format",
        "bad_formats": "formats must be a non-empty combination of svg / pdf / tex",
        "no_items": "Nothing to export",
        "all_failed": "All exports failed:\n{details}",
        "bad_setting": "Invalid setting: {key}",
        "out_written": "Wrote {path}",
        "bad_ext": "Output extension must be .svg, .pdf or .tex",
        "no_images": "No images found: {path}",
        "need_dir_output": "With several images (or a folder), -o must be an output folder (not an .svg / .pdf / .tex file)",
        "format_needs_dir": "--format only applies when writing to a folder; when writing files, the extension is the format",
        "batch_summary": "Done: {ok} succeeded, {failed} failed; {files} file(s) written to {dir}",
        "config_saved": "Saved to {path}",
        "key_set": "API key: set",
        "key_unset": "API key: not set",
        "model_now": "Recognition model: {model}",
        "cache_cleared": "Cleared {n} cached result(s)",
        "cache_stats": "{count} cached result(s) ({edited} hand-edited, {kb} KB): {path}",
    },
}


def tr(message_id: str, /, **kw) -> str:
    # message_id 是 positional-only：訊息裡的佔位符可以叫 key / name… 而不會跟參數名稱撞名
    text = MESSAGES[current_lang()].get(message_id) or MESSAGES["zh-TW"][message_id]
    return text.format(**kw) if kw else text
