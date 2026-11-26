import tomllib
from pathlib import Path

from fastapi.testclient import TestClient

import mathtran
from mathtran import UNKNOWN_VERSION, make_title
from mathtran.server import app

ROOT = Path(__file__).resolve().parent.parent
c = TestClient(app)


def pyproject_version() -> str:
    return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]


def test_version_comes_from_pyproject():
    """版本號只有 pyproject.toml 一個來源；若這裡失敗，通常是改了版本卻還沒執行 `uv sync`。"""
    assert mathtran.__version__ == pyproject_version()


def test_make_title():
    assert make_title("0.1.1") == "MathTran 0.1.1"
    assert make_title("1.2.3rc1") == "MathTran 1.2.3rc1"
    assert make_title(UNKNOWN_VERSION) == "MathTran"        # 讀不到版本時不要顯示奇怪的字
    assert mathtran.APP_TITLE == make_title(mathtran.__version__)


def test_desktop_window_title_shows_version():
    from mathtran import desktop

    assert desktop.TITLE == mathtran.APP_TITLE
    assert desktop.TITLE.startswith("MathTran ") and mathtran.__version__ in desktop.TITLE


def test_health_reports_version():
    assert c.get("/api/health").json()["version"] == mathtran.__version__


def test_browser_tab_title_shows_version():
    html = c.get("/").text
    assert html.count("<title>") == 1
    assert f"<title>{mathtran.APP_TITLE}</title>" in html


def test_openapi_version():
    assert c.get("/openapi.json").json()["info"]["version"] == mathtran.__version__


def test_selftest_checks_the_version():
    """打包版若沒帶進套件資訊，版本會讀不到，自我檢查必須能抓到。"""
    import json

    from mathtran import selftest

    out = ROOT / "build" / "selftest-version.json"
    out.parent.mkdir(exist_ok=True)
    selftest.run(out)
    checks = json.loads(out.read_text(encoding="utf-8"))["checks"]
    for name in ("version", "window_title_has_version", "page_title_has_version"):
        assert checks[name]["ok"] is True, (name, checks[name])


def test_pyinstaller_spec_bundles_the_package_metadata():
    """少了 copy_metadata，打包後的程式讀不到版本，標題列就少了版本號。"""
    spec = (ROOT / "packaging" / "mathtran.spec").read_text(encoding="utf-8")
    assert 'copy_metadata("mathtran")' in spec
