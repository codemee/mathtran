"""辨識模型的選擇：設定檔、環境變數鎖定、API、命令列。"""

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from mathtran.cli import app as cli_app
from mathtran.core import config
from mathtran.server import app

c = TestClient(app)


@pytest.fixture(autouse=True)
def _no_env_model(monkeypatch):
    monkeypatch.delenv("MATHTRAN_MODEL", raising=False)


def test_default_and_choices():
    m = c.get("/api/models").json()
    assert m["current"] == m["default"] == config.DEFAULT_MODEL
    assert config.DEFAULT_MODEL in m["choices"] and m["locked"] is False
    assert len(m["choices"]) == len(set(m["choices"])) >= 2


def test_save_and_clear():
    assert c.post("/api/config", json={"model": "claude-opus-5-5"}).status_code == 200
    assert config.get_model() == "claude-opus-5-5"
    assert c.get("/api/models").json()["current"] == "claude-opus-5-5"
    assert c.post("/api/config", json={"model": ""}).status_code == 200      # 空字串 = 恢復預設
    assert config.get_model() == config.DEFAULT_MODEL
    assert "model" not in config._load()


def test_custom_model_id_is_accepted():
    assert c.post("/api/config", json={"model": "claude-future-9"}).status_code == 200
    assert config.get_model() == "claude-future-9"


@pytest.mark.parametrize("bad", ["has space", "a;b", "引號", "x" * 101, "-leading"])
def test_bad_model_rejected(bad):
    c.post("/api/config", json={"model": "claude-opus-5-5"})
    r = c.post("/api/config", json={"model": bad})
    assert r.status_code == 400
    assert config.get_model() == "claude-opus-5-5"          # 失敗不會動到原本的設定


def test_key_and_model_are_independent():
    c.post("/api/config", json={"api_key": "sk-test-1"})
    c.post("/api/config", json={"model": "claude-haiku-5-5"})
    assert config.get_api_key() == "sk-test-1" and config.get_model() == "claude-haiku-5-5"
    c.post("/api/config", json={"api_key": "   "})              # 空白的 key 不會覆蓋原本的
    assert config.get_api_key() == "sk-test-1"


def test_env_var_locks_the_model(monkeypatch):
    c.post("/api/config", json={"model": "claude-opus-5-5"})
    monkeypatch.setenv("MATHTRAN_MODEL", "from-env")
    m = c.get("/api/models").json()
    assert m["locked"] is True and m["current"] == "from-env"


def test_ocr_uses_the_selected_model(monkeypatch):
    from mathtran.core import ocr

    seen = {}

    class FakeMessages:
        def create(self, **kw):
            seen["model"] = kw["model"]

            class R:
                content = [type("B", (), {"type": "text", "text": "x"})()]
            return R()

    class FakeClient:
        messages = FakeMessages()

    monkeypatch.setattr(ocr, "get_api_key", lambda: "k")
    monkeypatch.setattr(ocr.anthropic, "Anthropic", lambda **kw: FakeClient())
    config.save_model("claude-opus-5-5")
    ocr._call_api(b"\x89PNG\r\n\x1a\n" + b"0" * 20, FakeClient())
    assert seen["model"] == "claude-opus-5-5"


def test_cli_model_option():
    runner = CliRunner()
    r = runner.invoke(cli_app, ["config", "--model", "claude-opus-5-5"])
    assert r.exit_code == 0 and config.get_model() == "claude-opus-5-5"
    assert "claude-opus-5-5" in runner.invoke(cli_app, ["config"]).output
    assert runner.invoke(cli_app, ["config", "--model", "bad id"]).exit_code == 1
    assert runner.invoke(cli_app, ["config", "--model", ""]).exit_code == 0
    assert config.get_model() == config.DEFAULT_MODEL


def test_health_reports_current_model():
    assert c.get("/api/health").json()["model"] == config.DEFAULT_MODEL
    c.post("/api/config", json={"model": "claude-opus-5-5"})
    assert c.get("/api/health").json()["model"] == "claude-opus-5-5"
