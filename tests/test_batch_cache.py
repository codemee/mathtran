import io
import zipfile
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from mathtran.core import batch, cache, ocr
from mathtran.server import app

PNG = b"\x89PNG\r\n\x1a\n" + b"fake-image-bytes"
PNG2 = b"\x89PNG\r\n\x1a\n" + b"another-image"


def fake_client(counter: list, text="x^2"):
    class M:
        def create(self, **kw):
            counter.append(1)
            return SimpleNamespace(content=[SimpleNamespace(type="text", text=text)])

    return SimpleNamespace(messages=M())


# ---------- cache ----------
def test_cache_roundtrip_and_clear():
    h = cache.sha256_hex(PNG)
    assert cache.get(h) is None
    cache.put(h, "a+b", model="m")
    assert cache.get(h)["latex"] == "a+b"
    assert cache.lookup([h, "nope"]).keys() == {h}
    assert cache.count() == 1
    assert cache.clear() == 1 and cache.count() == 0


def test_cache_stats_and_remove():
    assert cache.stats()["count"] == 0 and cache.stats()["bytes"] == 0  # 還沒有檔案
    cache.put("a" * 64, "x", prompt=2)
    cache.put("b" * 64, "y", edited=True)
    cache.put("c" * 64, "z", prompt=2)
    s = cache.stats()
    assert (s["count"], s["edited"]) == (3, 1) and s["bytes"] > 0 and s["path"].endswith("cache.json")
    assert cache.remove(["a" * 64, "nope", "a" * 64]) == 1  # 只算實際刪掉的、重複的不重複計
    assert cache.get("a" * 64) is None and cache.get("b" * 64) is not None
    assert cache.remove(["nope"]) == 0
    assert cache.clear() == 2 and cache.stats()["count"] == 0


def test_api_cache_stats_clear_and_remove():
    c2 = TestClient(app)
    h1, h2, h3 = "1" * 64, "2" * 64, "3" * 64
    cache.put(h1, "a", prompt=2); cache.put(h2, "b", edited=True); cache.put(h3, "c", prompt=2)
    s = c2.get("/api/cache").json()
    assert (s["count"], s["edited"]) == (3, 1)
    assert c2.post("/api/cache/remove", json={"hashes": [h1, h2]}).json() == {"removed": 2}
    assert c2.get("/api/cache").json()["count"] == 1
    assert c2.delete("/api/cache").json() == {"removed": 1}
    assert c2.get("/api/cache").json()["count"] == 0
    assert c2.delete("/api/cache").json() == {"removed": 0}  # 已經空的也不會出錯


def test_cache_survives_corrupt_file():
    cache.put("k", "v")
    cache.cache_path().write_text("{not json", encoding="utf-8")
    assert cache.get("k") is None  # 損毀時視為空，不會當掉
    cache.put("k2", "v2")
    assert cache.get("k2")["latex"] == "v2"


# ---------- recognize 使用快取 ----------
def test_recognize_skips_api_when_cached():
    calls: list = []
    c = fake_client(calls)
    r1 = ocr.recognize(PNG, client=c)
    r2 = ocr.recognize(PNG, client=c)
    assert (r1.cached, r2.cached) == (False, True)
    assert len(calls) == 1 and r1.hash == r2.hash


def test_recognize_force_refreshes_cache():
    calls: list = []
    ocr.recognize(PNG, client=fake_client(calls, "old"))
    r = ocr.recognize(PNG, client=fake_client(calls, "new"), use_cache=False)
    assert r.latex == "new" and not r.cached and len(calls) == 2
    assert ocr.recognize(PNG, client=fake_client(calls)).latex == "new"


def test_stale_prompt_version_cache_is_ignored():
    """舊提示詞（會漏掉中文）辨識出的結果不能當有效快取，必須重新辨識。"""
    h = cache.sha256_hex(PNG)
    cache.put(h, "old-without-chinese", model="m", prompt=ocr.PROMPT_VERSION - 1)
    calls: list = []
    r = ocr.recognize(PNG, client=fake_client(calls, "新結果"))
    assert r.latex == "新結果" and not r.cached and len(calls) == 1
    assert cache.get(h, min_prompt=ocr.PROMPT_VERSION)["latex"] == "新結果"


def test_legacy_entry_without_prompt_field_is_stale():
    h = cache.sha256_hex(PNG)
    cache.put(h, "legacy")  # 沒有 prompt 欄位 = 0 版
    assert cache.get(h, min_prompt=ocr.PROMPT_VERSION) is None
    assert cache.get(h) is not None  # 不指定版本時仍讀得到（相容）


def test_edited_entry_survives_prompt_upgrade():
    """使用者手動修改過的結果，不因提示詞升級而作廢。"""
    h = cache.sha256_hex(PNG)
    cache.put(h, "my-edit", edited=True)
    calls: list = []
    r = ocr.recognize(PNG, client=fake_client(calls))
    assert r.latex == "my-edit" and r.cached and not calls


def test_editing_does_not_refresh_prompt_version():
    h = cache.sha256_hex(PNG)
    cache.put(h, "old", prompt=0)
    cache.put(h, "edited", edited=True)  # 手動修改不應把版本偷偷升級
    assert cache.get(h)["prompt"] == 0 and cache.get(h)["edited"]


def test_prompt_asks_for_all_text_including_chinese():
    assert "\\text{" in ocr.PROMPT and "Chinese" in ocr.PROMPT and "EVERYTHING" in ocr.PROMPT


def test_api_lookup_hides_stale_entries():
    h1, h2, h3 = "a" * 64, "b" * 64, "c" * 64
    cache.put(h1, "stale", prompt=0)
    cache.put(h2, "fresh", prompt=ocr.PROMPT_VERSION)
    cache.put(h3, "mine", edited=True, prompt=0)
    hits = c.post("/api/cache/lookup", json={"hashes": [h1, h2, h3]}).json()
    assert set(hits) == {h2, h3}


def test_different_images_not_confused():
    calls: list = []
    ocr.recognize(PNG, client=fake_client(calls, "A"))
    assert ocr.recognize(PNG2, client=fake_client(calls, "B")).latex == "B"


# ---------- batch 檔名 ----------
def test_safe_stem():
    assert batch.safe_stem("folder/sub/eq1.png") == "eq1"
    assert batch.safe_stem(r"C:\x\y\公式 一.JPG") == "公式 一"
    assert batch.safe_stem('a<b>:"c".png') == "a_b___c_"
    assert batch.safe_stem("...") == "formula"


def test_unique_stems_case_insensitive():
    assert batch.unique_stems(["a", "A", "b", "a"]) == ["a", "A_2", "b", "a_3"]


# ---------- server ----------
c = TestClient(app)


def test_api_cache_lookup_and_put():
    h = cache.sha256_hex(PNG)
    assert c.post("/api/cache/lookup", json={"hashes": [h]}).json() == {}
    assert c.put(f"/api/cache/{h}", json={"latex": "z^3"}).status_code == 200
    hit = c.post("/api/cache/lookup", json={"hashes": [h]}).json()
    assert hit[h] == {"latex": "z^3", "edited": True}
    assert c.put("/api/cache/not-a-hash", json={"latex": "x"}).status_code == 400


def test_api_ocr_uses_cache_and_force(monkeypatch):
    calls: list = []
    monkeypatch.setattr(ocr, "_call_api", lambda image, client: (calls.append(1), "q")[1])
    files = {"file": ("a.png", PNG, "image/png")}
    r1 = c.post("/api/ocr", files=files).json()
    r2 = c.post("/api/ocr", files=files).json()
    r3 = c.post("/api/ocr?force=true", files=files).json()
    assert [r1["cached"], r2["cached"], r3["cached"]] == [False, True, False]
    assert len(calls) == 2
    assert r1["hash"] == cache.sha256_hex(PNG)


def test_api_ocr_error_is_400():
    # 沒有 API key（conftest 已清掉環境變數與設定檔）
    r = c.post("/api/ocr", files={"file": ("a.png", PNG, "image/png")})
    assert r.status_code == 400 and "API key" in r.json()["detail"]


def test_api_export_batch_real_tectonic():
    items = [
        {"name": "dir/eq1.png", "latex": "x^2"},
        {"name": "eq1.jpg", "latex": r"\frac{a}{b}"},  # 同名 → eq1_2
        {"name": "empty.png", "latex": "  "},          # 空內容 → 略過
        {"name": "bad.png", "latex": r"\undefinedmacro{"},  # 編譯失敗 → 記錄
    ]
    r = c.post("/api/export/batch", json={"formats": ["svg"], "items": items})
    assert r.status_code == 200
    assert (r.headers["X-Ok-Count"], r.headers["X-Fail-Count"]) == ("2", "2")
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        names = sorted(zf.namelist())
        assert names == ["eq1.svg", "eq1_2.svg", "errors.txt"]
        assert b"<svg" in zf.read("eq1.svg")
        err = zf.read("errors.txt").decode()
        assert err.startswith("empty：") and "\n\nbad: " in err


def test_api_export_batch_all_fail_and_validation():
    r = c.post("/api/export/batch", json={"formats": ["pdf"], "items": [{"name": "a", "latex": ""}]})
    assert r.status_code == 400
    ok_item = [{"name": "a", "latex": "x"}]
    assert c.post("/api/export/batch", json={"formats": ["png"], "items": ok_item}).status_code == 400
    assert c.post("/api/export/batch", json={"formats": [], "items": ok_item}).status_code == 400
    assert c.post("/api/export/batch", json={"formats": ["svg"], "items": []}).status_code == 400


# ---------- LaTeX (.tex) 匯出與多格式 ----------
def test_to_tex_is_complete_document():
    from mathtran.core import render

    tex = render.to_tex(r"\frac{a}{b}")
    assert r"\documentclass" in tex and r"\frac{a}{b}" in tex and r"\end{document}" in tex
    assert "XeLaTeX" not in tex  # 沒有中文就不需要提醒
    assert "XeLaTeX" in render.to_tex("x=答案") and "xeCJK" in render.to_tex("x=答案")


def test_api_export_single_tex():
    r = c.post("/api/export/tex", json={"latex": "x^2"})
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/plain")
    assert r"\documentclass" in r.text and "x^2" in r.text


def test_batch_tex_only_does_not_need_tectonic(monkeypatch):
    from mathtran.core import render

    def boom(_):
        raise AssertionError("純 .tex 匯出不應該呼叫 tectonic")

    monkeypatch.setattr(render, "to_pdf", boom)
    r = c.post("/api/export/batch", json={"formats": ["tex"], "items": [
        {"name": "a.png", "latex": "x"}, {"name": "b.png", "latex": "y"}]})
    assert r.status_code == 200 and (r.headers["X-Ok-Count"], r.headers["X-Fail-Count"]) == ("2", "0")
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        assert sorted(zf.namelist()) == ["a.tex", "b.tex"]


def test_batch_multiple_formats_compile_once_per_item(monkeypatch):
    from mathtran.core import render

    calls = []
    real = render.to_pdf
    monkeypatch.setattr(render, "to_pdf", lambda latex: (calls.append(latex), real(latex))[1])
    r = c.post("/api/export/batch", json={"formats": ["svg", "pdf", "tex"], "items": [
        {"name": "eq.png", "latex": "a+b"}]})
    assert r.status_code == 200 and r.headers["X-Ok-Count"] == "3"
    assert len(calls) == 1  # svg 與 pdf 共用同一次編譯
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        assert sorted(zf.namelist()) == ["eq.pdf", "eq.svg", "eq.tex"]


def test_batch_compile_failure_still_writes_tex():
    r = c.post("/api/export/batch", json={"formats": ["pdf", "tex"], "items": [
        {"name": "bad.png", "latex": r"\undefinedmacro{"}]})
    assert r.status_code == 200
    assert (r.headers["X-Ok-Count"], r.headers["X-Fail-Count"]) == ("1", "1")
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        assert sorted(zf.namelist()) == ["bad.tex", "errors.txt"]
