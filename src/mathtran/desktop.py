"""桌面 App：pywebview 視窗載入本機 FastAPI。"""

from __future__ import annotations

import base64
import io
import socket
import sys
import threading
import time
import zipfile
from pathlib import Path

import uvicorn
import webview

from . import APP_TITLE
from .server import app


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _unique_path(path: Path) -> Path:
    """檔案已存在就改成「名稱 (2).副檔名」，避免覆蓋使用者的檔案。"""
    if not path.exists():
        return path
    n = 2
    while (candidate := path.with_name(f"{path.stem} ({n}){path.suffix}")).exists():
        n += 1
    return candidate


def extract_zip(data: bytes, folder: Path) -> list[str]:
    """把 zip 內的檔案解到 folder，回傳實際寫入的檔名。

    只取檔名（避免 ../ 路徑穿越），已存在的檔案不覆蓋（改名為「名稱 (2)」）。
    """
    names = []
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        for member in zf.namelist():
            name = Path(member).name
            if not name:
                continue
            target = _unique_path(folder / name)
            target.write_bytes(zf.read(member))
            names.append(target.name)
    return names


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

    def save_zip_to_folder(self, zip_b64: str) -> dict | None:
        """批次匯出：讓使用者選資料夾，把 zip 內的檔案解開放進去（不覆蓋既有檔案）。"""
        result = self._window.create_file_dialog(webview.FileDialog.FOLDER)
        if not result:
            return None
        folder = Path(result if isinstance(result, str) else result[0])
        names = extract_zip(base64.b64decode(zip_b64), folder)
        return {"dir": str(folder), "count": len(names), "names": names}


TITLE = APP_TITLE   # 標題列顯示版本號（例如 "MathTran 0.1.1"）；設定圖示、截圖也用這個字串找視窗
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
