"""桌面 App：pywebview 視窗載入本機 FastAPI。"""

from __future__ import annotations

import base64
import socket
import sys
import threading
import time
from pathlib import Path

import uvicorn
import webview

from .server import app


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class Api:
    """暴露給前端的桌面專用功能（pywebview 預設擋下載，所以改用另存新檔對話框）。

    注意：pywebview 會遞迴走訪這個物件所有「不以底線開頭」的屬性。
    若把 window 放成公開屬性，會走進 WinForms 原生控制項而間歇性卡死，
    所以必須用 _window。
    """

    def __init__(self) -> None:
        self._window: webview.Window | None = None

    def save_file(self, name: str, data_b64: str) -> str | None:
        ext = Path(name).suffix.lstrip(".")
        result = self._window.create_file_dialog(
            webview.FileDialog.SAVE,
            save_filename=name,
            file_types=(f"{ext.upper()} (*.{ext})",),
        )
        if not result:
            return None
        path = Path(result if isinstance(result, str) else result[0])
        path.write_bytes(base64.b64decode(data_b64))
        return str(path)


TITLE = "Mathtran"
ICON_PATH = Path(__file__).parent / "icon.ico"


def _set_window_icon() -> None:
    """Windows：把標題列與工作列圖示換成 icon.ico（pywebview 沒有提供此參數）。"""
    if sys.platform != "win32":
        return
    import ctypes

    user32 = ctypes.windll.user32
    user32.FindWindowW.restype = ctypes.c_void_p
    user32.LoadImageW.restype = ctypes.c_void_p
    user32.SendMessageW.argtypes = [
        ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p, ctypes.c_void_p,
    ]
    hwnd = None
    for _ in range(50):  # 等視窗建立，最多約 5 秒
        hwnd = user32.FindWindowW(None, TITLE)
        if hwnd:
            break
        time.sleep(0.1)
    if not hwnd:
        return
    IMAGE_ICON, LR_LOADFROMFILE, WM_SETICON = 1, 0x10, 0x80
    for kind, px in ((0, 16), (1, 32)):  # ICON_SMALL, ICON_BIG
        h = user32.LoadImageW(None, str(ICON_PATH), IMAGE_ICON, px, px, LR_LOADFROMFILE)
        if h:
            user32.SendMessageW(hwnd, WM_SETICON, kind, h)


def main() -> None:
    port = _free_port()
    server = uvicorn.Server(
        uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    )
    threading.Thread(target=server.run, daemon=True).start()
    while not server.started:
        time.sleep(0.05)
    api = Api()
    api._window = webview.create_window(
        TITLE, f"http://127.0.0.1:{port}", width=1100, height=720, js_api=api
    )
    webview.start(_set_window_icon)
    server.should_exit = True


if __name__ == "__main__":
    main()
