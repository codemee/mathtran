"""FastAPI 後端：提供 Web UI 與 OCR / 匯出 API。"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .core import config, ocr, render

WEB_DIR = Path(__file__).parent / "web"

app = FastAPI(title="mathtran")


class LatexIn(BaseModel):
    latex: str


class KeyIn(BaseModel):
    api_key: str


@app.get("/api/health")
def health():
    import shutil

    return {
        "api_key": bool(config.get_api_key()),
        "tectonic": bool(shutil.which("tectonic")),
    }


@app.post("/api/config")
def set_key(body: KeyIn):
    config.save_api_key(body.api_key.strip())
    return {"ok": True}


@app.post("/api/ocr")
async def api_ocr(file: UploadFile = File(...)):
    data = await file.read()
    try:
        return {"latex": ocr.image_to_latex(data)}
    except ocr.OcrError as e:
        raise HTTPException(400, str(e))


@app.post("/api/export/{fmt}")
def api_export(fmt: str, body: LatexIn):
    if fmt not in ("svg", "pdf"):
        raise HTTPException(404, "fmt 必須是 svg 或 pdf")
    try:
        pdf = render.to_pdf(body.latex)
    except render.RenderError as e:
        raise HTTPException(400, str(e))
    if fmt == "pdf":
        return Response(pdf, media_type="application/pdf")
    return Response(render.pdf_to_svg(pdf), media_type="image/svg+xml")


@app.get("/")
def index():
    return FileResponse(WEB_DIR / "index.html")


@app.get("/icon.svg")
def icon():
    return FileResponse(WEB_DIR / "icon.svg", media_type="image/svg+xml")


app.mount("/vendor", StaticFiles(directory=WEB_DIR / "vendor"), name="vendor")
