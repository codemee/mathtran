"""產生 README 用的真實畫面（開桌面視窗、載入範例、擷取視窗）。

輸出：
  docs/images/sample-formula.png   範例公式圖（用 tectonic 產生，不涉及任何人像或版權圖片）
  docs/images/app-main.png         主畫面（含精準預覽與狀態列）

用法：uv run python packaging/screenshots.py
需要 tectonic 與 Pillow（dev 相依）。
"""

from __future__ import annotations

import base64
import ctypes
import json
import threading
import time
from pathlib import Path

import pymupdf
import uvicorn
import webview
from PIL import ImageGrab

from mathtran.core import render
from mathtran.desktop import TITLE, _free_port, _set_window_icon
from mathtran.server import app

ROOT = Path(__file__).resolve().parent.parent
IMAGES = ROOT / "docs" / "images"
FORMULA = r"x = \frac{-b \pm \sqrt{b^{2} - 4ac}}{2a}"


def make_sample_image() -> bytes:
    """把公式編譯成 PDF 再轉成帶白底的 PNG，當作「要辨識的圖片」。"""
    pdf = render.to_pdf(FORMULA)
    with pymupdf.open(stream=pdf, filetype="pdf") as doc:
        png = doc[0].get_pixmap(matrix=pymupdf.Matrix(4, 4), alpha=False).tobytes("png")
    (IMAGES / "sample-formula.png").write_bytes(png)
    return png


def capture(path: Path) -> None:
    user32 = ctypes.windll.user32
    user32.FindWindowW.restype = ctypes.c_void_p
    user32.SetForegroundWindow.argtypes = [ctypes.c_void_p]
    user32.GetWindowRect.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    hwnd = user32.FindWindowW(None, TITLE)
    user32.SetForegroundWindow(hwnd)
    time.sleep(0.8)
    rect = ctypes.wintypes.RECT()
    # 取「可見」邊界（排除 Windows 10/11 的隱形陰影邊框），否則兩側會露出背景
    DWMWA_EXTENDED_FRAME_BOUNDS = 9
    ctypes.windll.dwmapi.DwmGetWindowAttribute(
        ctypes.c_void_p(hwnd), DWMWA_EXTENDED_FRAME_BOUNDS, ctypes.byref(rect), ctypes.sizeof(rect)
    )
    ImageGrab.grab(
        bbox=(rect.left, rect.top, rect.right, rect.bottom), all_screens=True
    ).save(path)


def script(window: webview.Window, png: bytes) -> None:
    _set_window_icon()
    time.sleep(2.5)
    data_url = "data:image/png;base64," + base64.b64encode(png).decode()
    window.evaluate_js(
        f"""(() => {{
          const img = document.createElement('img'); img.src = {json.dumps(data_url)};
          document.getElementById('drop').replaceChildren(img);
          document.getElementById('ocrBtn').disabled = false;
          document.getElementById('latex').value = {json.dumps(FORMULA)};
          renderKatex();
          document.getElementById('accBtn').click();
        }})()"""
    )
    for _ in range(120):  # 等精準預覽（tectonic 編譯）完成
        time.sleep(0.5)
        if "完成" in window.evaluate_js("document.getElementById('msg').textContent"):
            break
    time.sleep(1.0)
    capture(IMAGES / "app-main.png")
    window.destroy()


def main() -> None:
    import ctypes.wintypes  # noqa: F401  (載入 wintypes)

    ctypes.windll.user32.SetProcessDPIAware()  # 以實際像素擷取，避免縮放造成裁切
    IMAGES.mkdir(parents=True, exist_ok=True)
    png = make_sample_image()
    port = _free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    threading.Thread(target=server.run, daemon=True).start()
    while not server.started:
        time.sleep(0.05)
    window = webview.create_window(TITLE, f"http://127.0.0.1:{port}", width=1100, height=640)
    webview.start(script, (window, png))
    server.should_exit = True
    print("screenshots done")


if __name__ == "__main__":
    main()
