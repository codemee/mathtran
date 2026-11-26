"""FastAPI 後端：提供 Web UI 與 OCR / 匯出 API。"""

from __future__ import annotations

import re
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import APP_NAME, APP_TITLE, __version__
from .core import batch, cache, config, i18n, ocr, render
from .core.i18n import tr

WEB_DIR = Path(__file__).parent / "web"

app = FastAPI(title=APP_NAME, version=__version__)


class LangMiddleware:
    """讀取前端送來的 X-Lang 標頭（zh-TW / en），讓這個請求裡的錯誤訊息用該語言。

    寫成純 ASGI middleware（而不是 BaseHTTPMiddleware），contextvar 才能正確傳到
    FastAPI 在執行緒池裡跑的同步端點。
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        token = None
        if scope["type"] == "http":
            for key, value in scope["headers"]:
                if key == b"x-lang":
                    token = i18n.set_lang(value.decode("latin-1"))
                    break
        try:
            await self.app(scope, receive, send)
        finally:
            if token is not None:
                i18n.reset_lang(token)


app.add_middleware(LangMiddleware)


class LatexIn(BaseModel):
    latex: str


class SettingsIn(BaseModel):
    lang: str | None = None
    theme: str | None = None
    thumb: int | None = None
    formats: list[str] | None = None


@app.get("/api/settings")
def get_settings():
    return config.get_settings()


@app.put("/api/settings")
def put_settings(body: SettingsIn):
    """部分更新介面偏好（語系、配色、縮圖大小、匯出格式）；任何一項不合法就整批拒絕。"""
    try:
        return config.update_settings(body.model_dump(exclude_none=True))
    except ValueError as e:
        raise HTTPException(400, tr("bad_setting", key=e))


class KeyIn(BaseModel):
    api_key: str


@app.get("/api/health")
def health():
    return {
        "api_key": bool(config.get_api_key()),
        "tectonic": render.tectonic_available(),   # 含安裝包附帶的 tectonic
        "version": __version__,
    }


@app.post("/api/config")
def set_key(body: KeyIn):
    config.save_api_key(body.api_key.strip())
    return {"ok": True}


@app.post("/api/ocr")
def api_ocr(file: UploadFile = File(...), force: bool = False):
    """同步端點（跑在執行緒池），批次辨識時才能真正並行。force=true 忽略快取。"""
    data = file.file.read()
    try:
        r = ocr.recognize(data, use_cache=not force)
    except ocr.OcrError as e:
        raise HTTPException(400, str(e))
    return {"latex": r.latex, "hash": r.hash, "cached": r.cached}


class LookupIn(BaseModel):
    hashes: list[str]


class CachePutIn(BaseModel):
    latex: str


@app.post("/api/cache/lookup")
def cache_lookup(body: LookupIn):
    """回傳 {hash: {latex, edited}}，只含命中的項目。"""
    hits = cache.lookup(body.hashes, min_prompt=ocr.PROMPT_VERSION)  # 過期的（舊提示詞）不回傳
    return {h: {"latex": e["latex"], "edited": bool(e.get("edited"))} for h, e in hits.items()}


@app.get("/api/cache")
def cache_stats():
    return cache.stats()


@app.delete("/api/cache")
def cache_clear():
    """清除所有快取（含手動修改的結果）。"""
    return {"removed": cache.clear()}


@app.post("/api/cache/remove")
def cache_remove(body: LookupIn):
    """只清除指定圖片（雜湊）的快取。"""
    return {"removed": cache.remove(body.hashes)}


@app.put("/api/cache/{h}")
def cache_put(h: str, body: CachePutIn):
    """使用者手動修改 LaTeX 後存回快取（標記為 edited）。"""
    if not re.fullmatch(r"[0-9a-f]{64}", h):
        raise HTTPException(400, tr("bad_hash"))
    cache.put(h, body.latex, edited=True)
    return {"ok": True}


class BatchItem(BaseModel):
    name: str
    latex: str


class BatchIn(BaseModel):
    formats: list[str]
    items: list[BatchItem]


@app.post("/api/export/batch")  # 必須在 /api/export/{fmt} 之前註冊
def api_export_batch(body: BatchIn):
    if not body.formats or any(f not in batch.FORMATS for f in body.formats):
        raise HTTPException(400, tr("bad_formats"))
    if not body.items:
        raise HTTPException(400, tr("no_items"))
    r = batch.export_zip([i.model_dump() for i in body.items], body.formats)
    if r.ok == 0:
        raise HTTPException(400, tr("all_failed", details="\n".join(r.errors)[:1500]))
    return Response(
        r.data,
        media_type="application/zip",
        headers={"X-Ok-Count": str(r.ok), "X-Fail-Count": str(r.failed)},
    )


@app.post("/api/export/{fmt}")
def api_export(fmt: str, body: LatexIn):
    if fmt not in batch.FORMATS:
        raise HTTPException(404, tr("bad_fmt"))
    if fmt == "tex":
        return Response(render.to_tex(body.latex), media_type="text/plain; charset=utf-8")
    try:
        pdf = render.to_pdf(body.latex)
    except render.RenderError as e:
        raise HTTPException(400, str(e))
    if fmt == "pdf":
        return Response(pdf, media_type="application/pdf")
    return Response(render.pdf_to_svg(pdf), media_type="image/svg+xml")


@app.get("/")
def index():
    # 瀏覽器分頁標題也顯示版本號（桌面視窗的標題由 desktop.py 設定，用同一個 APP_TITLE）
    html = (WEB_DIR / "index.html").read_text(encoding="utf-8")
    html = html.replace(f"<title>{APP_NAME}</title>", f"<title>{APP_TITLE}</title>", 1)
    return HTMLResponse(html)


@app.get("/icon.svg")
def icon():
    return FileResponse(WEB_DIR / "icon.svg", media_type="image/svg+xml")


app.mount("/vendor", StaticFiles(directory=WEB_DIR / "vendor"), name="vendor")
