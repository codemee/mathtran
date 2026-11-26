"""MathTran：圖片中的數學公式 → LaTeX → 預覽 → 匯出 SVG / PDF / .tex。"""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _installed_version

APP_NAME = "MathTran"
UNKNOWN_VERSION = "0+unknown"

# 版本號只有一個來源：pyproject.toml。執行時從「已安裝套件的資訊」讀取
# （PyInstaller 打包版要在 mathtran.spec 用 copy_metadata 把這份資訊帶進去，否則這裡會讀不到）。
try:
    __version__ = _installed_version("mathtran")
except PackageNotFoundError:  # 沒有安裝資訊（例如直接從原始碼資料夾執行）
    __version__ = UNKNOWN_VERSION


def make_title(version: str) -> str:
    """視窗 / 網頁標題："MathTran 0.1.1"；版本讀不到時只顯示名稱。"""
    return APP_NAME if version == UNKNOWN_VERSION else f"{APP_NAME} {version}"


APP_TITLE = make_title(__version__)
