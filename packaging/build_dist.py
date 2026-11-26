"""建立可散布的安裝包：Windows → ZIP，macOS → DMG。

    uv run python packaging/build_dist.py

需要的環境變數：
    TECTONIC_BIN       要一起打包的 tectonic 執行檔路徑（必填）
    TECTONIC_LICENSE   tectonic 的授權全文檔案路徑（建議；安裝包要附上 MIT 授權聲明）

輸出在 dist/：
    MathTran-<版本>-windows-x64.zip
    MathTran-<版本>-macos-arm64.dmg  或  MathTran-<版本>-macos-x64.dmg

安裝包裡一定會附上：LICENSE、THIRD_PARTY_NOTICES.md、TECTONIC_LICENSE.txt、SOURCE.txt
（GPL / AGPL 要求隨散布提供授權與取得原始碼的方式）。
"""

from __future__ import annotations

import os
import platform
import shutil
import stat
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
PYI_DIST = DIST / "pyi"
PYI_WORK = ROOT / "build" / "pyi"
REPO = "https://github.com/codemee/mathtran"


def version() -> str:
    return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]


def run(cmd: list[str], **kw) -> None:
    print("+", " ".join(str(c) for c in cmd), flush=True)
    subprocess.run(cmd, check=True, **kw)


def notice_files(ver: str, target: Path) -> None:
    """把授權相關檔案放進 target 資料夾。"""
    for name in ("LICENSE", "THIRD_PARTY_NOTICES.md"):
        shutil.copy2(ROOT / name, target / name)
    lic = os.environ.get("TECTONIC_LICENSE")
    if lic and Path(lic).is_file():
        shutil.copy2(lic, target / "TECTONIC_LICENSE.txt")
    else:
        print("警告：沒有 TECTONIC_LICENSE，安裝包不會附 tectonic 的授權全文", file=sys.stderr)
    (target / "SOURCE.txt").write_text(
        f"MathTran {ver}\n"
        "License: GPL-3.0-or-later (see LICENSE). Third-party components: see THIRD_PARTY_NOTICES.md.\n"
        f"Corresponding source code: {REPO}/tree/v{ver}\n"
        f"Source archive:            {REPO}/archive/refs/tags/v{ver}.zip\n"
        "對應的原始碼：上面的網址（對應此版本的 tag）。\n",
        encoding="utf-8",
    )


def build_pyinstaller() -> None:
    shutil.rmtree(PYI_DIST, ignore_errors=True)
    shutil.rmtree(PYI_WORK, ignore_errors=True)
    run([sys.executable, "-m", "PyInstaller", str(ROOT / "packaging" / "mathtran.spec"),
         "--noconfirm", "--distpath", str(PYI_DIST), "--workpath", str(PYI_WORK)])


def make_zip_windows(ver: str) -> Path:
    folder = PYI_DIST / "MathTran"
    notice_files(ver, folder)
    out = DIST / f"MathTran-{ver}-windows-x64"
    return Path(shutil.make_archive(str(out), "zip", root_dir=PYI_DIST, base_dir="MathTran"))


def make_dmg_macos(ver: str) -> Path:
    arch = "arm64" if platform.machine().lower() in ("arm64", "aarch64") else "x64"
    app = PYI_DIST / "MathTran.app"
    # tectonic 要有執行權限（保險起見再設一次）
    for exe in app.rglob("tectonic"):
        exe.chmod(exe.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    # 沒有 Apple 開發者憑證：做 ad-hoc 簽章，Apple Silicon 才能執行（使用者第一次開啟仍需手動允許）
    run(["codesign", "--force", "--deep", "--sign", "-", str(app)])
    stage = DIST / "dmg-stage"
    shutil.rmtree(stage, ignore_errors=True)
    stage.mkdir(parents=True)
    run(["ditto", str(app), str(stage / "MathTran.app")])        # ditto 會保留符號連結與屬性
    (stage / "Applications").symlink_to("/Applications")
    notice_files(ver, stage)
    out = DIST / f"MathTran-{ver}-macos-{arch}.dmg"
    out.unlink(missing_ok=True)
    run(["hdiutil", "create", "-volname", f"MathTran {ver}", "-srcfolder", str(stage),
         "-ov", "-format", "UDZO", str(out)])
    return out


def main() -> None:
    ver = version()
    DIST.mkdir(exist_ok=True)
    build_pyinstaller()
    if sys.platform == "win32":
        result = make_zip_windows(ver)
    elif sys.platform == "darwin":
        result = make_dmg_macos(ver)
    else:
        raise SystemExit("目前只支援 Windows（ZIP）與 macOS（DMG）的安裝包")
    print(f"\n完成：{result}  ({result.stat().st_size / 1024 / 1024:.1f} MB)")


if __name__ == "__main__":
    main()
