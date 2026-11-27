"""mathtran 命令列介面。"""

from __future__ import annotations

import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Optional

import typer

from . import APP_TITLE
from .core import batch, config, ocr, render
from .core.i18n import tr

app = typer.Typer(help="MathTran：圖片數學公式 → LaTeX，並匯出 SVG / PDF / LaTeX", no_args_is_help=True)


def _version(value: bool):
    if value:
        typer.echo(APP_TITLE)
        raise typer.Exit()


@app.callback()
def _main(
    version: bool = typer.Option(False, "--version", "-V", callback=_version, is_eager=True, help="顯示版本後結束"),
):
    pass


def _fail(e: Exception | str):
    typer.secho(str(e), fg="red", err=True)
    raise typer.Exit(1)


FILE_EXTS = (".svg", ".pdf", ".tex")


def _is_file_target(p: Path) -> bool:
    return p.suffix.lower() in FILE_EXTS


def _write_files(paths: list[Path], latex: str):
    """把一個公式寫成 paths 指定的檔案（依副檔名：.svg / .pdf / .tex）；svg 與 pdf 只編譯一次。"""
    bad = [p for p in paths if not _is_file_target(p)]
    if bad:
        raise typer.BadParameter(tr("bad_ext"))
    formats = batch.clean_formats([p.suffix.lower().lstrip(".") for p in paths])
    files, err = batch.render_formats(latex, formats)
    for p in paths:
        data = files.get(p.suffix.lower().lstrip("."))
        if data is not None:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(data)
            typer.echo(tr("out_written", path=p), err=True)
    if err:
        _fail(err)


NO_CACHE = typer.Option(False, "--no-cache", help="忽略辨識快取，強制重新辨識")
JOBS = typer.Option(3, "--jobs", "-j", min=1, max=16, help="同時辨識幾張圖片（多張時）")
RECURSIVE = typer.Option(False, "--recursive", "-r", help="圖片參數是資料夾時，連子資料夾一起找")


def _images(paths: list[Path], recursive: bool) -> list[Path]:
    try:
        images = batch.collect_images(paths, recursive)
    except FileNotFoundError as e:
        _fail(tr("no_images", path=e))
    return images


def _recognize_all(images: list[Path], use_cache: bool, jobs: int) -> list[tuple[Path, str | None, str | None]]:
    """辨識多張圖片，依原順序回傳 (圖片, LaTeX, 錯誤)；進度寫到 stderr。

    沒有設定 API key 時，每張都會失敗得一樣，所以遇到就立刻中止。
    """
    results: dict[int, tuple[str | None, str | None]] = {}
    total = len(images)
    key_missing = tr("api_key_missing")

    def work(i: int):
        try:
            return i, ocr.image_to_latex(images[i].read_bytes(), use_cache=use_cache), None
        except (ocr.OcrError, OSError) as e:
            return i, None, str(e)

    with ThreadPoolExecutor(min(jobs, total)) as ex:
        futures = [ex.submit(work, i) for i in range(total)]
        for n, fut in enumerate(as_completed(futures), 1):
            i, latex, err = fut.result()
            results[i] = (latex, err)
            if err == key_missing:
                ex.shutdown(wait=False, cancel_futures=True)
                _fail(err)
            typer.echo(f"[{n}/{total}] {images[i].name}" + (f"  ✗ {err.splitlines()[0]}" if err else ""), err=True)
    return [(images[i], *results[i]) for i in range(total)]


@app.command("ocr")
def ocr_cmd(
    images: list[Path] = typer.Argument(..., exists=True, help="圖片或資料夾路徑（可以多個）"),
    no_cache: bool = NO_CACHE,
    jobs: int = JOBS,
    recursive: bool = RECURSIVE,
    as_json: bool = typer.Option(False, "--json", help='輸出 JSON：[{"file", "latex", "error"}, ...]'),
):
    """圖片 → 印出 LaTeX（辨識過的圖片會直接使用快取）。

    只有一張圖片時只印 LaTeX；多張（或資料夾）時每張前面加一行 "% 檔名"，方便分辨。
    """
    files = _images(images, recursive)
    single = len(files) == 1 and not as_json
    if single:
        try:
            typer.echo(ocr.image_to_latex(files[0].read_bytes(), use_cache=not no_cache))
        except ocr.OcrError as e:
            _fail(e)
        return
    results = _recognize_all(files, not no_cache, jobs)
    if as_json:
        typer.echo(json.dumps([{"file": str(f), "latex": latex, "error": err} for f, latex, err in results], ensure_ascii=False, indent=2))
    else:
        for f, latex, err in results:
            if latex is not None:
                typer.echo(f"% {f.name}\n{latex}\n")
    if any(err for _, _, err in results):
        raise typer.Exit(1)


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
    output: list[Path] = typer.Option(..., "-o", "--output", help=".svg、.pdf 或 .tex；可重複，一次輸出多種格式"),
):
    """LaTeX → SVG / PDF / .tex（完整、可自行編譯的文件）。"""
    _write_files(output, sys.stdin.read() if latex == "-" else latex)


@app.command("convert")
def convert_cmd(
    images: list[Path] = typer.Argument(..., exists=True, help="圖片或資料夾路徑（可以多個）"),
    output: list[Path] = typer.Option(
        ..., "-o", "--output",
        help="單張圖片：.svg / .pdf / .tex 檔（可重複）；多張或資料夾：輸出資料夾（檔名 = 圖檔名）",
    ),
    format: list[str] = typer.Option(None, "--format", "-f", help="輸出到資料夾時的格式：svg / pdf / tex（可重複，預設 svg）"),
    no_cache: bool = NO_CACHE,
    jobs: int = JOBS,
    recursive: bool = RECURSIVE,
):
    """圖片 → LaTeX → SVG / PDF / .tex（一步完成）；多張圖片或資料夾會批次處理。

    \b
    mathtran convert a.png -o a.svg -o a.tex     單張，輸出多個檔案
    mathtran convert a.png b.png -o out/ -f svg -f pdf   多張，輸出到 out/
    mathtran convert notes/ -o out/ -f tex       資料夾裡的所有圖片
    """
    files = _images(images, recursive)
    folder_mode = len(files) > 1 or any(p.is_dir() for p in images) or not all(_is_file_target(o) for o in output)
    if not folder_mode:
        if format:
            raise typer.BadParameter(tr("format_needs_dir"), param_hint="--format")
        try:
            latex = ocr.image_to_latex(files[0].read_bytes(), use_cache=not no_cache)
        except ocr.OcrError as e:
            _fail(e)
        typer.echo(latex)
        _write_files(output, latex)
        return

    if len(output) != 1 or _is_file_target(output[0]):
        raise typer.BadParameter(tr("need_dir_output"), param_hint="-o")
    try:
        formats = batch.clean_formats(format or ["svg"])
    except ValueError:
        raise typer.BadParameter(tr("bad_formats"), param_hint="--format")
    out_dir = output[0]
    out_dir.mkdir(parents=True, exist_ok=True)
    results = _recognize_all(files, not no_cache, jobs)
    stems = batch.unique_stems([batch.safe_stem(f.name) for f, _, _ in results])
    ok_images, failed, written = 0, 0, 0
    for (f, latex, err), stem in zip(results, stems):
        if err or not (latex or "").strip():
            failed += 1
            if not err:
                typer.secho(tr("empty_skipped", name=f.name), fg="red", err=True)
            continue
        out_files, render_err = batch.render_formats(latex.strip(), formats)
        for ext, data in out_files.items():
            (out_dir / f"{stem}.{ext}").write_bytes(data)
            written += 1
        if render_err:
            failed += 1
            typer.secho(f"{f.name}: {render_err}", fg="red", err=True)
        else:
            ok_images += 1
    typer.echo(tr("batch_summary", ok=ok_images, failed=failed, files=written, dir=out_dir), err=True)
    if failed:
        raise typer.Exit(1)


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
