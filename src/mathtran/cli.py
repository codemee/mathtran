"""mathtran 命令列介面。"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import typer

from .core import config, ocr, render

app = typer.Typer(help="圖片數學公式 → LaTeX，並匯出 SVG / PDF", no_args_is_help=True)


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
            raise typer.BadParameter("輸出副檔名必須是 .svg 或 .pdf")
    except render.RenderError as e:
        _fail(e)
    typer.echo(f"已輸出 {path}", err=True)


@app.command("ocr")
def ocr_cmd(image: Path = typer.Argument(..., exists=True, help="圖片路徑")):
    """圖片 → 印出 LaTeX。"""
    try:
        typer.echo(ocr.image_to_latex(image.read_bytes()))
    except ocr.OcrError as e:
        _fail(e)


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
):
    """圖片 → LaTeX → SVG / PDF（一步完成）。"""
    try:
        latex = ocr.image_to_latex(image.read_bytes())
    except ocr.OcrError as e:
        _fail(e)
    typer.echo(latex)
    _write(output, latex)


@app.command("config")
def config_cmd(api_key: Optional[str] = typer.Option(None, "--api-key")):
    """儲存 Anthropic API key。"""
    if api_key:
        config.save_api_key(api_key)
        typer.echo(f"已儲存至 {config.CONFIG_PATH}")
    else:
        typer.echo("API key：" + ("已設定" if config.get_api_key() else "未設定"))


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
