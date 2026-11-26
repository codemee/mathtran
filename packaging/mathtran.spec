# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 設定：Windows（資料夾，之後壓成 ZIP）與 macOS（.app，之後做成 DMG）共用。

用法（通常由 packaging/build_dist.py 呼叫）：
    TECTONIC_BIN=<tectonic 執行檔路徑> pyinstaller packaging/mathtran.spec

安裝包會把 Tectonic 一起帶上，使用者不必另外安裝（見 mathtran.core.render.bundled_tectonic）。
"""

import os
import sys
import tomllib
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata

ROOT = Path(SPECPATH).parent
SRC = ROOT / "src"
VERSION = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]

tectonic = os.environ.get("TECTONIC_BIN")
if not tectonic or not Path(tectonic).is_file():
    raise SystemExit("請用環境變數 TECTONIC_BIN 指定要一起打包的 tectonic 執行檔路徑")

datas = [
    (str(SRC / "mathtran" / "web"), "mathtran/web"),       # 前端（含離線的 KaTeX）
    (str(SRC / "mathtran" / "icon.ico"), "mathtran"),       # 視窗圖示（Windows）
]
datas += collect_data_files("anthropic")                    # SDK 的型別 / 資料檔
# 版本號（標題列顯示 "MathTran 0.1.1"）是從「已安裝套件的資訊」讀的，打包時要一起帶進去，
# 否則打包後的程式讀不到版本、標題會少掉版本號（自我檢查會抓這件事）
datas += copy_metadata("mathtran")

# 這些套件是靠字串在執行時才載入的，PyInstaller 看不出來，要明確列出
hiddenimports = []
for pkg in ("uvicorn", "anyio", "multipart", "python_multipart", "pydantic_core"):
    try:
        hiddenimports += collect_submodules(pkg)
    except Exception:
        pass
if sys.platform == "win32":
    hiddenimports += ["webview.platforms.edgechromium", "webview.platforms.winforms"]
elif sys.platform == "darwin":
    hiddenimports += ["webview.platforms.cocoa"]

a = Analysis(
    [str(ROOT / "packaging" / "app_entry.py")],
    pathex=[str(SRC)],
    binaries=[(tectonic, ".")],
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=["tkinter", "pytest", "PIL"],
    noarchive=False,
)
pyz = PYZ(a.pure)

icon = str(SRC / "mathtran" / ("icon.icns" if sys.platform == "darwin" else "icon.ico"))
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="MathTran",
    console=False,          # 視窗程式，不要跳出黑色主控台
    icon=icon,
)
coll = COLLECT(exe, a.binaries, a.datas, name="MathTran")

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="MathTran.app",
        icon=icon,
        bundle_identifier="io.github.codemee.mathtran",
        version=VERSION,
        info_plist={
            "CFBundleName": "MathTran",
            "CFBundleDisplayName": "MathTran",
            "CFBundleShortVersionString": VERSION,
            "NSHighResolutionCapable": True,
            # 視窗載入的是本機的 http://127.0.0.1（FastAPI），WKWebView 預設會擋明文 http
            "NSAppTransportSecurity": {"NSAllowsLocalNetworking": True},
            "LSMinimumSystemVersion": "11.0",
        },
    )
