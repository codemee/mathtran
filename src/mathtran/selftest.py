"""打包版的自我檢查（給 CI 用）：不開視窗，啟動內建伺服器並檢查主要功能。

用法：
    MATHTRAN_SELFTEST=<結果檔路徑> MathTran(.exe)          # 打包版（packaging/app_entry.py 會呼叫）
    uv run python -m mathtran.selftest <結果檔路徑>         # 開發環境

打包版在 Windows 是「無主控台」的程式，標準輸出看不到，所以結果寫進檔案（JSON），
結束代碼 0 表示全部通過、1 表示有失敗。
"""

from __future__ import annotations

import json
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path


def _call(base: str, path: str, body: dict | None = None, timeout: int = 600) -> tuple[int, bytes]:
    req = urllib.request.Request(
        base + path,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Content-Type": "application/json", "X-Lang": "en"},
        method="POST" if body is not None else "GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:   # 第一次編譯 tectonic 要下載套件，可能很久
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def run(result_path: str | Path) -> int:
    import uvicorn

    from . import APP_TITLE, UNKNOWN_VERSION
    from .core import render
    from .desktop import _free_port
    from .server import app

    frozen = bool(getattr(sys, "frozen", False))
    results: dict[str, object] = {}

    def check(name: str, ok: bool, detail: str = "") -> None:
        results[name] = {"ok": bool(ok), **({"detail": detail} if detail else {})}

    port = _free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    threading.Thread(target=server.run, daemon=True).start()
    t0 = time.time()
    while not server.started and time.time() - t0 < 30:
        time.sleep(0.05)
    base = f"http://127.0.0.1:{port}"
    try:
        check("server_started", server.started)

        code, body = _call(base, "/api/health")
        health = json.loads(body) if code == 200 else {}
        check("health", code == 200 and health.get("tectonic") is True, f"HTTP {code} {health}")
        if frozen:   # 打包版必須用安裝包附帶的 tectonic，不能靠系統上剛好有裝
            check("bundled_tectonic", render.bundled_tectonic() is not None, str(render.bundled_tectonic()))

        # 版本號必須讀得到（打包版要有 copy_metadata 帶進去的套件資訊），而且標題列 / 網頁標題要顯示它
        version = health.get("version", "")
        check("version", bool(version) and version != UNKNOWN_VERSION, version)
        check("window_title_has_version", APP_TITLE == f"MathTran {version}", APP_TITLE)

        code, body = _call(base, "/")
        check("index_page", code == 200 and b"MathTran" in body and b'id="toolbar"' in body, f"HTTP {code}")
        check("page_title_has_version", f"<title>{APP_TITLE}</title>".encode() in body, APP_TITLE)
        for path in ("/vendor/katex.min.js", "/vendor/katex.min.css",
                     "/vendor/fonts/KaTeX_Main-Regular.woff2", "/icon.svg"):
            code, body = _call(base, path)
            check(f"asset {path}", code == 200 and len(body) > 100, f"HTTP {code}")

        code, body = _call(base, "/api/settings")
        check("settings", code == 200 and {"lang", "theme", "thumb", "formats"} <= set(json.loads(body)), f"HTTP {code}")

        code, body = _call(base, "/api/export/svg", {"latex": r"\int_0^1 x^2\,dx=\frac13"})
        check("export_svg", code == 200 and b"<svg" in body, f"HTTP {code} {body[:120]!r}" if code != 200 else "")
        code, body = _call(base, "/api/export/pdf", {"latex": r"\frac{a}{b}"})
        check("export_pdf", code == 200 and body.startswith(b"%PDF"), f"HTTP {code}")
        code, body = _call(base, "/api/export/tex", {"latex": "x^2"})
        check("export_tex", code == 200 and b"\\documentclass" in body, f"HTTP {code}")

        # 中文公式需要系統上有中文字型；CI 的 Windows 機器可能沒有，所以「找不到字型」只標記為略過，不算失敗
        code, body = _call(base, "/api/export/pdf", {"latex": "x=答案"})
        if code == 200:
            check("export_cjk_pdf", body.startswith(b"%PDF"))
        elif b"CJK font" in body:
            results["export_cjk_pdf"] = {"ok": True, "skipped": "no CJK font installed on this machine"}
        else:
            check("export_cjk_pdf", False, f"HTTP {code} {body[:200]!r}")
    except Exception as e:   # 任何意外都記錄下來，不要讓自我檢查自己當掉
        check("unexpected_error", False, repr(e))
    finally:
        server.should_exit = True

    ok = all(v["ok"] for v in results.values())
    Path(result_path).write_text(
        json.dumps({"ok": ok, "frozen": frozen, "python": sys.version, "checks": results},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return 0 if ok else 1


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("用法：python -m mathtran.selftest <結果檔路徑>")
    raise SystemExit(run(sys.argv[1]))
