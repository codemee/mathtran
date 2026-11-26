import pytest

from mathtran.core import config


@pytest.fixture(autouse=True)
def isolated_config(tmp_path, monkeypatch):
    """所有測試都使用暫存的設定 / 快取目錄，不碰使用者真正的 ~/.mathtran。

    語言固定為繁體中文，測試結果才不會因為執行環境的系統語言而不同
    （要測英文的測試自己用 X-Lang 標頭或 monkeypatch 環境變數）。
    """
    monkeypatch.setattr(config, "CONFIG_PATH", tmp_path / ".mathtran" / "config.json")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("MATHTRAN_LANG", "zh-TW")
