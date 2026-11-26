"""產生 README 用的真實畫面（開桌面視窗、載入範例、擷取視窗）。

輸出：
  docs/images/sample-formula.png   範例公式圖（用 tectonic 產生，不涉及任何人像或版權圖片）
  docs/images/app-main.png         主畫面（淺色＝鋼彈 RX-78-2 配色、繁體中文）：多張圖片、勾選、辨識狀態、精準預覽
  docs/images/app-dark.png         同一畫面的深色（新世紀福音戰士配色）
  docs/images/app-en.png           同一畫面的 English 介面
  docs/images/toolbar-states.png   工具列（語言 / 配色 / API key）三組狀態的真實按鈕

注意：為了不需要 API key 也能產生截圖，這支腳本
  - 把設定 / 快取目錄指到暫存資料夾（不碰你真正的 ~/.mathtran）
  - 預先把 3 張圖放進快取（顯示「已快取」），並用替身取代 Claude API，
    讓其中 1 張顯示「已辨識」、其餘維持「未辨識」。
所以截圖裡的 LaTeX 是範例公式的原始碼，不是真的 API 回傳結果。

用法：uv run python packaging/screenshots.py
需要 tectonic 與 Pillow（dev 相依）。
"""

from __future__ import annotations

import base64
import ctypes
import ctypes.wintypes
import json
import tempfile
import threading
import time
from pathlib import Path

import pymupdf
import uvicorn
import webview
from PIL import ImageGrab

from mathtran.core import cache, config, ocr, render
from mathtran.desktop import TITLE, _free_port, _set_window_icon
from mathtran.server import app

ROOT = Path(__file__).resolve().parent.parent
IMAGES = ROOT / "docs" / "images"

# 檔名 → LaTeX（第一個也是 sample-formula.png）
SAMPLES = {
    "二次公式.png": r"x = \frac{-b \pm \sqrt{b^{2} - 4ac}}{2a}",
    "積分.png": r"\int_0^1 x^2\,dx = \frac{1}{3}",
    "歐拉恆等式.png": r"e^{i\pi} + 1 = 0",
    "級數.png": r"\sum_{k=1}^{n} k = \frac{n(n+1)}{2}",
    "畢氏定理.png": r"a^{2} + b^{2} = c^{2}",
    "極限.png": r"\lim_{x \to 0} \frac{\sin x}{x} = 1",
}
CACHED = ["二次公式.png", "積分.png", "歐拉恆等式.png"]   # 預先放進快取
OCR_NOW = ["級數.png"]                                      # 用替身「辨識」一次


def png_of(latex: str) -> bytes:
    """把公式編譯成 PDF 再轉成帶白底的 PNG，當作「要辨識的圖片」。"""
    with pymupdf.open(stream=render.to_pdf(latex), filetype="pdf") as doc:
        return doc[0].get_pixmap(matrix=pymupdf.Matrix(4, 4), alpha=False).tobytes("png")


def capture(path: Path) -> None:
    grab_window().save(path)


def grab_window():
    """擷取整個視窗並回傳 PIL 影像（視窗不在最前面就報錯，不回傳）。"""
    user32 = ctypes.windll.user32
    user32.FindWindowW.restype = ctypes.c_void_p
    user32.SetForegroundWindow.argtypes = [ctypes.c_void_p]
    user32.GetForegroundWindow.restype = ctypes.c_void_p
    user32.SetWindowPos.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int, ctypes.c_int,
                                    ctypes.c_int, ctypes.c_int, ctypes.c_uint]
    hwnd = user32.FindWindowW(None, TITLE)
    HWND_TOPMOST, SWP_NOMOVE, SWP_NOSIZE, SWP_SHOWWINDOW = ctypes.c_void_p(-1), 0x2, 0x1, 0x40
    # 螢幕擷取是「抓螢幕上看到的」：視窗被別的視窗蓋住就會拍到別人的畫面（可能含隱私內容）。
    # 所以先設成最上層，並確認真的在最前面才擷取；做不到就報錯，絕不寫檔。
    for _ in range(20):
        user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)
        # Windows 的「前景鎖定」會擋下背景程式的 SetForegroundWindow；先送一下 Alt 鍵是常見的繞過方式
        user32.keybd_event(0x12, 0, 0, 0)
        user32.keybd_event(0x12, 0, 2, 0)
        user32.SetForegroundWindow(hwnd)
        time.sleep(0.4)
        if user32.GetForegroundWindow() == hwnd:
            break
    else:
        raise RuntimeError("無法把視窗帶到最前面，已放棄擷取（避免拍到其他視窗的內容）")
    rect = ctypes.wintypes.RECT()
    # 取「可見」邊界（排除 Windows 10/11 的隱形陰影邊框），否則兩側會露出背景
    DWMWA_EXTENDED_FRAME_BOUNDS = 9
    ctypes.windll.dwmapi.DwmGetWindowAttribute(
        ctypes.c_void_p(hwnd), DWMWA_EXTENDED_FRAME_BOUNDS, ctypes.byref(rect), ctypes.sizeof(rect)
    )
    user32.SetCursorPos(rect.right + 40, rect.bottom - 40)  # 滑鼠移到視窗外，避免拍到 hover 的提示框
    time.sleep(1.5)
    return ImageGrab.grab(bbox=(rect.left, rect.top, rect.right, rect.bottom), all_screens=True)


def toolbar_states_image(window) -> None:
    """把工具列三組狀態的真實按鈕截下來，疊成一張圖：

    ① 語言「跟隨系統」(地球) ＋ 配色「跟隨系統」(半黑半白圓)
    ② 語言「繁體中文」(中)   ＋ 配色「淺色」(太陽)
    ③ 語言「English」(En)    ＋ 配色「深色」(月亮)
    每一列右邊都是 API key 鑰匙（有紅點＝尚未設定）。
    """
    from PIL import Image

    rows = []
    for lang, theme in (("system", "system"), ("zh-TW", "light"), ("en", "dark")):
        window.evaluate_js(
            f"S.settings.lang={json.dumps(lang)}; S.settings.theme={json.dumps(theme)};"
            "applyTheme(); renderToolbar();"
        )
        time.sleep(0.6)
        img = grab_window()
        w = img.width
        rows.append(img.crop((w - 170, 34, w - 4, 66)))   # 標題列下方、工具列右側，只含按鈕（視窗寬度固定，座標固定）
    sep = 6
    out = Image.new("RGB", (rows[0].width, sum(r.height for r in rows) + sep * (len(rows) - 1)), (128, 128, 128))
    y = 0
    for r in rows:
        out.paste(r, (0, y))
        y += r.height + sep
    out = out.resize((out.width * 2, out.height * 2), Image.LANCZOS)
    out.save(IMAGES / "toolbar-states.png")


def script(window: webview.Window, pngs: dict[str, bytes]) -> None:
    """pywebview 在另一個執行緒跑這裡；任何錯誤都要印出來並關閉視窗，否則程式會卡住不結束。"""
    try:
        _script(window, pngs)
    except Exception:
        import traceback

        traceback.print_exc()
        FAILED.append(True)
    finally:
        window.destroy()


FAILED: list[bool] = []


def _script(window: webview.Window, pngs: dict[str, bytes]) -> None:
    def ev(expr: str):
        return window.evaluate_js(expr)

    def js(code: str, timeout: float = 120) -> None:
        ev(
            "window.__done=false;(async()=>{try{" + code + "}finally{window.__done=true}})()"
        )
        t0 = time.time()
        while not ev("window.__done"):
            if time.time() - t0 > timeout:
                raise TimeoutError(code[:60])
            time.sleep(0.15)

    _set_window_icon()
    time.sleep(2.5)
    # 視窗預設可能比螢幕可用高度還高，底部（含狀態列）會被工作列蓋住：縮小並移到左上方
    window.resize(1100, 870)
    window.move(30, 10)
    time.sleep(1.0)
    entries = ",".join(
        f"mk({json.dumps(base64.b64encode(b).decode())},{json.dumps(n)})" for n, b in pngs.items()
    )
    js(
        "const mk=(b64,name)=>{const bin=atob(b64);const u=new Uint8Array(bin.length);"
        "for(let i=0;i<bin.length;i++)u[i]=bin.charCodeAt(i);"
        "return {file:new File([u],name,{type:'image/png'}),name}};"
        f"await addFiles([{entries}], {{sort:false}});"
    )
    # 勾選「級數」並辨識（替身 API），其餘保持原狀
    js(
        f"S.items.forEach(i=>i.checked=false); S.items.find(i=>i.name==={json.dumps(OCR_NOW[0])}).checked=true;"
        "renderList(); document.getElementById('ocrChk').click();"
        "while(S.busy||S.items.some(i=>i.state==='running'||i.state==='queued')) await new Promise(r=>setTimeout(r,100));"
        # 展示「勾選」：勾 2 張、選取第 1 張並做精準預覽
        "S.items.forEach(i=>i.checked=false); S.items[0].checked=true; S.items[3].checked=true;"
        "select(S.items[0].id); document.getElementById('pvAcc').click();"
    )
    for _ in range(120):  # 等精準預覽（tectonic 編譯）完成
        time.sleep(0.5)
        if "精準預覽完成" in ev("document.getElementById('msg').textContent"):
            break
    time.sleep(1.0)
    capture(IMAGES / "app-main.png")                       # 淺色（鋼彈 RX-78-2）、繁體中文
    # 深色（EVA）：只換配色，其餘狀態不變
    js("S.settings.theme='dark'; applyTheme(); renderToolbar();")
    time.sleep(0.8)
    capture(IMAGES / "app-dark.png")
    # English 介面（淺色）：連狀態列訊息也會用新語言重新翻譯
    js("S.settings.theme='light'; S.settings.lang='en'; applyTheme(); applyLanguage();")
    time.sleep(0.8)
    capture(IMAGES / "app-en.png")
    toolbar_states_image(window)                          # 工具列三態按鈕的真實圖示（README 用）


def main() -> None:
    ctypes.windll.user32.SetProcessDPIAware()  # 以實際像素擷取，避免縮放造成裁切
    IMAGES.mkdir(parents=True, exist_ok=True)
    config.CONFIG_PATH = Path(tempfile.mkdtemp()) / ".mathtran" / "config.json"  # 隔離快取
    config.update_settings({"lang": "zh-TW", "theme": "light"})                     # 第一張固定為「淺色 + 繁體中文」

    pngs = {name: png_of(latex) for name, latex in SAMPLES.items()}
    (IMAGES / "sample-formula.png").write_bytes(pngs["二次公式.png"])
    by_hash = {cache.sha256_hex(pngs[n]): SAMPLES[n] for n in SAMPLES}
    for name in CACHED:
        cache.put(cache.sha256_hex(pngs[name]), SAMPLES[name], model="demo", prompt=ocr.PROMPT_VERSION)
    ocr._call_api = lambda image, client: by_hash[cache.sha256_hex(image)]  # 替身，僅供截圖

    port = _free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    threading.Thread(target=server.run, daemon=True).start()
    while not server.started:
        time.sleep(0.05)
    window = webview.create_window(TITLE, f"http://127.0.0.1:{port}", width=1180, height=760)
    webview.start(script, (window, pngs))
    server.should_exit = True
    if FAILED:
        raise SystemExit("截圖失敗（見上方錯誤）")
    print("screenshots done")


if __name__ == "__main__":
    main()
