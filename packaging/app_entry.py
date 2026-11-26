"""PyInstaller 打包版的進入點。

- 雙擊（沒有參數）→ 開桌面視窗
- 有參數 → 當命令列用（例如 `MathTran.exe render "E=mc^2" -o out.svg`）
  打包版是「無主控台」的視窗程式，所以在 Windows 上命令列的輸出看不到；
  要用命令列請改用 `uv tool install mathtran`。
"""

import multiprocessing
import os
import sys


def run() -> None:
    multiprocessing.freeze_support()
    selftest_result = os.environ.get("MATHTRAN_SELFTEST")
    if selftest_result:   # CI 用：不開視窗，檢查打包出來的程式能不能用（見 mathtran/selftest.py）
        from mathtran.selftest import run as selftest

        sys.exit(selftest(selftest_result))
    if len(sys.argv) > 1:
        from mathtran.cli import app

        app(prog_name="MathTran")
    else:
        from mathtran.desktop import main

        main()


if __name__ == "__main__":
    run()
