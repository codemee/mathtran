"""mathtran 命令列介面。"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import typer

from .core import config, ocr, render
from .core.i18n import tr

app = typer.Typer(help="MathTran：圖片數學公式 → LaTeX，並匯出 SVG / PDF / LaTeX", no_args_is_help=True)


def _fail(e: Exception):
    typer.secho(str(e), fg="red", err=True)
    raise typer.Exit(1)


def _write(path: Path, latex: str):
    ext = path.suffix.lower()
    try:
        if ext == ".pdf":
            path.write_bytes(render.to_pdf(latex))
        elif ext == ".svg":
            path.write_text(render.to_svg(latex), encoding="utf-8")
        else:
            raise typer.BadParameter(tr("bad_ext"))
    except render.RenderError as e:
        _fail(e)
    typer.echo(tr("out_written", path=path), err=True)


NO_CACHE = typer.Option(False, "--no-cache", help="忽略辨識快取，強制重新辨識")


@app.command("ocr")
def ocr_cmd(
    image: Path = typer.Argument(..., exists=True, help="圖片路徑"),
    no_cache: bool = NO_CACHE,
):
    """圖片 → 印出 LaTeX（辨識過的圖片會直接使用快取）。"""
    try:
        typer.echo(ocr.image_to_latex(image.read_bytes(), use_cache=not no_cache))
    except ocr.OcrError as e:
        _fail(e)


@app.command("cache")
def cache_cmd(clear: bool = typer.Option(False, "--clear", help="清除所有快取")):
    """查看或清除辨識快取。"""
    from .core import cache

    if clear:
        typer.echo(tr("cache_cleared", n=cache.clear()))
    else:
        s = cache.stats()
        typer.echo(tr("cache_stats", count=s["count"], edited=s["edited"], kb=f"{s['bytes'] / 1024:.1f}", path=s["path"]))


@app.command("render")
def render_cmd(
    latex: str = typer.Argument(..., help='LaTeX 公式，"-" 表示從 stdin 讀取'),
    output: Path = typer.Option(..., "-o", "--output", help=".svg 或 .pdf"),
):
    """LaTeX → SVG / PDF。"""
    _write(output, sys.stdin.read() if latex == "-" else latex)


@app.command("convert")
def convert_cmd(
    image: Path = typer.Argument(..., exists=True),
    output: Path = typer.Option(..., "-o", "--output", help=".svg 或 .pdf"),
    no_cache: bool = NO_CACHE,
):
    """圖片 → LaTeX → SVG / PDF（一步完成）。"""
    try:
        latex = ocr.image_to_latex(image.read_bytes(), use_cache=not no_cache)
    except ocr.OcrError as e:
        _fail(e)
    typer.echo(latex)
    _write(output, latex)


@app.command("config")
def config_cmd(
    api_key: Optional[str] = typer.Option(None, "--api-key"),
    model: Optional[str] = typer.Option(None, "--model", help="辨識用的模型 ID；空字串 = 預設"),
):
    """儲存 Anthropic API key 與辨識模型（不帶選項就顯示目前狀態）。"""
    if api_key or model is not None:
        if api_key:
            config.save_api_key(api_key)
        if model is not None:
            try:
                config.save_model(model)
            except ValueError as e:
                typer.echo(tr("bad_setting", key=e), err=True)
                raise typer.Exit(1)
        typer.echo(tr("config_saved", path=config.CONFIG_PATH))
    else:
        typer.echo(tr("key_set" if config.get_api_key() else "key_unset"))
    typer.echo(tr("model_now", model=config.get_model()))


@app.command("serve")
def serve_cmd(port: int = 8765, open_browser: bool = typer.Option(True, "--open/--no-open")):
    """啟動 Web 介面。"""
    import threading
    import webbrowser

    import uvicorn

    if open_browser:
        threading.Timer(1.0, lambda: webbrowser.open(f"http://127.0.0.1:{port}")).start()
    uvicorn.run("mathtran.server:app", host="127.0.0.1", port=port, log_level="warning")


@app.command("gui")
def gui_cmd():
    """啟動桌面視窗。"""
    from .desktop import main

    main()


if __name__ == "__main__":
    app()
