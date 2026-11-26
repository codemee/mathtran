import sys
import tomllib
from pathlib import Path

import pytest

from mathtran.core import render

ROOT = Path(__file__).resolve().parent.parent
EXE = "tectonic.exe" if sys.platform == "win32" else "tectonic"


@pytest.fixture
def frozen_app(tmp_path, monkeypatch):
    """模擬 PyInstaller 打包版：sys.frozen、sys.executable 在資料夾 tmp_path 裡。"""
    monkeypatch.delenv("MATHTRAN_TECTONIC", raising=False)
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "MathTran"))
    monkeypatch.delattr(sys, "_MEIPASS", raising=False)
    return tmp_path


def test_not_frozen_never_uses_bundled(monkeypatch, tmp_path):
    monkeypatch.delattr(sys, "frozen", raising=False)
    (tmp_path / EXE).write_text("")
    monkeypatch.setattr(sys, "executable", str(tmp_path / "python"))
    assert render.bundled_tectonic() is None          # 開發環境不會誤用旁邊的檔案


def test_bundled_tectonic_next_to_executable(frozen_app):
    assert render.bundled_tectonic() is None          # 旁邊還沒有
    (frozen_app / EXE).write_text("")
    assert render.bundled_tectonic() == str(frozen_app / EXE)


def test_bundled_tectonic_in_meipass(frozen_app, monkeypatch, tmp_path_factory):
    meipass = tmp_path_factory.mktemp("meipass")
    (meipass / EXE).write_text("")
    monkeypatch.setattr(sys, "_MEIPASS", str(meipass), raising=False)
    assert render.bundled_tectonic() == str(meipass / EXE)


def test_find_tectonic_order(frozen_app, monkeypatch, tmp_path_factory):
    monkeypatch.setattr(render.shutil, "which", lambda _: "/usr/bin/tectonic-on-path")
    assert render.find_tectonic() == "/usr/bin/tectonic-on-path"           # 只有 PATH
    (frozen_app / EXE).write_text("")
    assert render.find_tectonic() == str(frozen_app / EXE)                 # 附帶的優先於 PATH
    custom = tmp_path_factory.mktemp("custom") / "my-tectonic"
    custom.write_text("")
    monkeypatch.setenv("MATHTRAN_TECTONIC", str(custom))
    assert render.find_tectonic() == str(custom)                           # 環境變數最優先
    monkeypatch.setenv("MATHTRAN_TECTONIC", str(custom) + "-missing")
    assert render.find_tectonic() == str(frozen_app / EXE)                 # 指到不存在的檔案就忽略


def test_tectonic_missing_everywhere(frozen_app, monkeypatch):
    monkeypatch.setattr(render.shutil, "which", lambda _: None)
    assert render.tectonic_available() is False
    with pytest.raises(render.RenderError):
        render.find_tectonic()


def test_health_reports_bundled_tectonic(frozen_app, monkeypatch):
    from fastapi.testclient import TestClient

    from mathtran.server import app

    monkeypatch.setattr(render.shutil, "which", lambda _: None)            # PATH 上沒有
    assert TestClient(app).get("/api/health").json()["tectonic"] is False
    (frozen_app / EXE).write_text("")                                      # 但安裝包附帶了
    assert TestClient(app).get("/api/health").json()["tectonic"] is True


# ---------- 自我檢查（CI 用來驗證打包出來的程式）----------
def test_selftest_passes_in_dev_environment(tmp_path):
    import json

    from mathtran import selftest

    result = tmp_path / "result.json"
    code = selftest.run(result)
    data = json.loads(result.read_text(encoding="utf-8"))
    failed = {k: v for k, v in data["checks"].items() if not v["ok"]}
    assert code == 0 and data["ok"] is True and not failed, failed
    assert {"health", "index_page", "export_svg", "export_pdf", "export_tex", "settings"} <= set(data["checks"])
    assert data["frozen"] is False and "bundled_tectonic" not in data["checks"]   # 只有打包版才要求附帶 tectonic


def test_selftest_reports_failure(tmp_path, monkeypatch):
    import json

    from mathtran import selftest

    monkeypatch.setattr(render.shutil, "which", lambda _: None)             # 假裝系統上沒有 tectonic
    result = tmp_path / "result.json"
    code = selftest.run(result)
    data = json.loads(result.read_text(encoding="utf-8"))
    assert code == 1 and data["ok"] is False
    assert data["checks"]["health"]["ok"] is False and data["checks"]["export_svg"]["ok"] is False


# ---------- 專案中繼資料（發布到 PyPI 前的把關）----------
def test_pyproject_metadata_is_ready_for_pypi():
    meta = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert meta["name"] == "mathtran"
    assert meta["license"] == "GPL-3.0-or-later"
    assert meta["scripts"]["mathtran"] == "mathtran.cli:app"
    assert meta["readme"] == "README.md" and (ROOT / "README.md").is_file()
    assert meta["license-files"]
    for f in meta["license-files"]:
        assert (ROOT / f).is_file(), f
    assert meta["urls"]["Homepage"].startswith("https://github.com/")


def test_readme_links_are_absolute():
    """README 會原樣顯示在 PyPI 上，相對路徑的圖片和連結在那裡會壞掉。"""
    import re

    for name in ("README.md", "README.en.md"):
        text = (ROOT / name).read_text(encoding="utf-8")
        for target in re.findall(r"\]\(([^)\s]+)\)", text) + re.findall(r'src="([^"]+)"', text):
            assert target.startswith(("http://", "https://", "#", "mailto:")), (name, target)
