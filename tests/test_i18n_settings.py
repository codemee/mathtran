import io
import json
import zipfile
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from mathtran.core import config, i18n, render
from mathtran.server import app

c = TestClient(app)
PNG = b"\x89PNG\r\n\x1a\n" + b"fake"


# ---------- 設定的存取與驗證 ----------
def test_settings_defaults():
    assert config.get_settings() == config.DEFAULT_SETTINGS


def test_settings_partial_update_keeps_others_and_api_key():
    config.save_api_key("sk-test")
    out = config.update_settings({"lang": "en"})
    assert out["lang"] == "en" and out["theme"] == "system" and out["thumb"] == 170
    out = config.update_settings({"theme": "dark", "thumb": 220})
    assert (out["lang"], out["theme"], out["thumb"]) == ("en", "dark", 220)   # 先前的 lang 仍保留
    assert config.get_api_key() == "sk-test"                                  # 沒有蓋掉 API key


def test_settings_validation_is_atomic():
    config.update_settings({"lang": "zh-TW"})
    for bad in ({"lang": "fr"}, {"theme": "blue"}, {"thumb": 5}, {"thumb": 9999}, {"thumb": True},
                {"thumb": "170"}, {"formats": []}, {"formats": ["svg", "png"]}, {"formats": "svg"}, {"nope": 1}):
        with pytest.raises(ValueError):
            config.update_settings(bad)
    with pytest.raises(ValueError):                       # 一項不合法 → 整批不寫入
        config.update_settings({"lang": "en", "thumb": 1})
    assert config.get_settings()["lang"] == "zh-TW"


def test_settings_formats_deduped_and_ordered():
    assert config.update_settings({"formats": ["tex", "svg", "tex"]})["formats"] == ["svg", "tex"]


def test_corrupt_settings_fall_back_to_defaults():
    config.CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    config.CONFIG_PATH.write_text(json.dumps({"settings": {
        "lang": "xx", "theme": "dark", "thumb": "big", "formats": ["svg", "bogus"], "extra": 1}}), encoding="utf-8")
    s = config.get_settings()
    assert (s["lang"], s["theme"], s["thumb"], s["formats"]) == ("system", "dark", 170, ["svg"])
    config.CONFIG_PATH.write_text("{broken", encoding="utf-8")
    assert config.get_settings() == config.DEFAULT_SETTINGS     # 檔案壞掉也不會出錯


def test_api_settings_roundtrip_and_validation():
    assert c.get("/api/settings").json() == config.DEFAULT_SETTINGS
    r = c.put("/api/settings", json={"lang": "en", "theme": "light"})
    assert r.status_code == 200 and r.json()["lang"] == "en"
    assert c.get("/api/settings").json()["theme"] == "light"
    r = c.put("/api/settings", json={"lang": "klingon"})
    assert r.status_code == 400 and "lang" in r.json()["detail"]
    assert c.get("/api/settings").json()["lang"] == "en"                 # 失敗的請求不會改動設定


# ---------- 語言解析 ----------
def test_normalize():
    assert [i18n.normalize(x) for x in ("zh", "zh-Hant", "zh_TW", "ZH-tw", "en", "en-US", "EN_gb")] == \
        ["zh-TW"] * 4 + ["en"] * 3
    assert i18n.normalize("fr") is None and i18n.normalize("") is None and i18n.normalize(None) is None


def test_system_lang_is_supported():
    assert i18n.system_lang() in i18n.LANGS


def test_lang_resolution_order(monkeypatch):
    monkeypatch.delenv("MATHTRAN_LANG")
    monkeypatch.setattr(i18n, "system_lang", lambda: "en")
    assert i18n.current_lang() == "en"                                   # 沒有任何設定 → 系統語言
    config.update_settings({"lang": "zh-TW"})
    assert i18n.current_lang() == "zh-TW"                                # 介面偏好優先於系統
    config.update_settings({"lang": "system"})
    assert i18n.current_lang() == "en"                                   # 「跟隨系統」不算偏好
    config.update_settings({"lang": "zh-TW"})
    monkeypatch.setenv("MATHTRAN_LANG", "en")
    assert i18n.current_lang() == "en"                                   # 環境變數優先於介面偏好
    token = i18n.set_lang("zh-TW")
    assert i18n.current_lang() == "zh-TW"                                # 請求標頭最優先
    i18n.reset_lang(token)
    assert i18n.current_lang() == "en"


def test_unknown_lang_header_is_ignored():
    r = c.post("/api/ocr", files={"file": ("a.png", PNG, "image/png")}, headers={"X-Lang": "fr"})
    assert "未設定 API key" in r.json()["detail"]                        # 退回環境變數（zh-TW）


def test_all_messages_have_both_languages_and_same_placeholders():
    import re
    zh, en = i18n.MESSAGES["zh-TW"], i18n.MESSAGES["en"]
    assert zh.keys() == en.keys()
    for k in zh:
        assert set(re.findall(r"\{(\w+)\}", zh[k])) == set(re.findall(r"\{(\w+)\}", en[k])), k


# ---------- 後端訊息跟隨 X-Lang ----------
def test_error_messages_follow_x_lang_header():
    files = {"file": ("a.png", PNG, "image/png")}
    en = c.post("/api/ocr", files=files, headers={"X-Lang": "en"}).json()["detail"]
    zh = c.post("/api/ocr", files=files, headers={"X-Lang": "zh-TW"}).json()["detail"]
    assert en.startswith("No API key set") and zh.startswith("未設定 API key")
    assert "API key" in en and "API key" in zh                           # 前端靠這個判斷「致命錯誤」，兩種語言都要有


def test_lang_does_not_leak_between_requests():
    files = {"file": ("a.png", PNG, "image/png")}
    assert c.post("/api/ocr", files=files, headers={"X-Lang": "en"}).json()["detail"].startswith("No API key")
    assert c.post("/api/ocr", files=files).json()["detail"].startswith("未設定")   # 沒標頭 → 回到環境變數


def test_concurrent_requests_keep_their_own_language():
    files = {"file": ("a.png", PNG, "image/png")}

    def call(i):
        lang = "en" if i % 2 else "zh-TW"
        d = TestClient(app).post("/api/ocr", files=files, headers={"X-Lang": lang}).json()["detail"]
        return lang, d

    with ThreadPoolExecutor(8) as ex:
        results = list(ex.map(call, range(24)))
    assert all(("No API key" in d) == (lang == "en") for lang, d in results)


def test_http_error_details_are_localized():
    en = c.post("/api/export/batch", json={"formats": ["svg"], "items": []}, headers={"X-Lang": "en"})
    assert en.status_code == 400 and en.json()["detail"] == "Nothing to export"
    zh = c.post("/api/export/batch", json={"formats": ["svg"], "items": []}, headers={"X-Lang": "zh-TW"})
    assert zh.json()["detail"] == "沒有要匯出的項目"
    assert c.put("/api/cache/xyz", json={"latex": "x"}, headers={"X-Lang": "en"}).json()["detail"] == "Invalid hash format"
    assert c.post("/api/export/png", json={"latex": "x"}, headers={"X-Lang": "en"}).json()["detail"] == "fmt must be svg, pdf or tex"


def test_batch_errors_txt_and_tex_header_are_localized():
    items = [{"name": "empty.png", "latex": " "}, {"name": "ok.png", "latex": "x"}]
    r = c.post("/api/export/batch", json={"formats": ["tex"], "items": items}, headers={"X-Lang": "en"})
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        assert zf.read("errors.txt").decode() == "empty: no LaTeX content, skipped"
    r = c.post("/api/export/batch", json={"formats": ["tex"], "items": items}, headers={"X-Lang": "zh-TW"})
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        assert zf.read("errors.txt").decode() == "empty：沒有 LaTeX 內容，已略過"
    en_tex = c.post("/api/export/tex", json={"latex": "x=答案"}, headers={"X-Lang": "en"}).text
    zh_tex = c.post("/api/export/tex", json={"latex": "x=答案"}, headers={"X-Lang": "zh-TW"}).text
    assert "compile with XeLaTeX" in en_tex and "請以 XeLaTeX 編譯" in zh_tex


def test_render_error_message_localized(monkeypatch):
    monkeypatch.setattr(render.shutil, "which", lambda _: None)
    for lang, needle in (("en", "tectonic not found"), ("zh-TW", "找不到 tectonic")):
        token = i18n.set_lang(lang)
        try:
            with pytest.raises(render.RenderError, match=needle):
                render.find_tectonic()
        finally:
            i18n.reset_lang(token)


# ---------- 命令列 ----------
def test_cli_messages_follow_language(monkeypatch):
    from mathtran.cli import app as cli_app
    runner = CliRunner()
    monkeypatch.setenv("MATHTRAN_LANG", "en")
    assert "cached result" in runner.invoke(cli_app, ["cache"]).output
    assert "API key: not set" in runner.invoke(cli_app, ["config"]).output
    monkeypatch.setenv("MATHTRAN_LANG", "zh-TW")
    assert "筆快取" in runner.invoke(cli_app, ["cache"]).output
    assert "API key：未設定" in runner.invoke(cli_app, ["config"]).output
    monkeypatch.delenv("MATHTRAN_LANG")
    config.update_settings({"lang": "en"})                               # 沒有環境變數 → 用介面偏好
    assert "API key: not set" in runner.invoke(cli_app, ["config"]).output
