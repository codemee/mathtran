"""產生 App 圖示：藍色 f(x) 上面壓一條紅色 PDF 橫條（透明底）。

輸出：
  src/mathtran/web/icon.svg   網頁 favicon（文字已轉外框）
  src/mathtran/icon.ico       桌面視窗 / 打包 exe 圖示（16~256 多尺寸）
  docs/images/icon.png        文件用預覽圖

用法：uv run python packaging/make_icon.py
"""

from __future__ import annotations

import struct
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parent.parent
SIZE = 256
BLUE = (0.18, 0.44, 0.93)
WHITE = (1, 1, 1)
RED = (0.90, 0.22, 0.21)


def build_page() -> tuple[pymupdf.Document, pymupdf.Page]:
    """透明底；藍色 f(x) 上面壓一條紅色 PDF 橫條。"""
    doc = pymupdf.open()
    page = doc.new_page(width=SIZE, height=SIZE)

    # f(x)（Times 粗斜體），藍色在亮 / 暗背景都看得清楚
    text = "f(x)"
    size = 136
    width = pymupdf.get_text_length(text, fontname="tibi", fontsize=size)
    page.insert_text(((SIZE - width) / 2, 152), text, fontname="tibi", fontsize=size, color=BLUE)

    # 紅色 PDF 橫條，壓在 f(x) 下半部
    bar = pymupdf.Rect(16, 136, 240, 208)
    sh = page.new_shape()
    sh.draw_rect(bar, radius=0.22)
    sh.finish(fill=RED, color=WHITE, width=5)
    sh.commit()
    tw = pymupdf.get_text_length("PDF", fontname="hebo", fontsize=52)
    page.insert_text(
        ((SIZE - tw) / 2, bar.y0 + 52), "PDF", fontname="hebo", fontsize=52, color=WHITE
    )
    return doc, page


def png_at(page: pymupdf.Page, px: int) -> bytes:
    z = px / SIZE
    return page.get_pixmap(matrix=pymupdf.Matrix(z, z), alpha=True).tobytes("png")


def write_ico(path: Path, pngs: dict[int, bytes]) -> None:
    sizes = sorted(pngs)
    head = struct.pack("<HHH", 0, 1, len(sizes))
    offset = 6 + 16 * len(sizes)
    entries, blobs = b"", b""
    for s in sizes:
        data = pngs[s]
        entries += struct.pack(
            "<BBBBHHII", s % 256, s % 256, 0, 0, 1, 32, len(data), offset + len(blobs)
        )
        blobs += data
    path.write_bytes(head + entries + blobs)


def main() -> None:
    doc, page = build_page()
    (ROOT / "docs" / "images").mkdir(parents=True, exist_ok=True)
    (ROOT / "src/mathtran/web/icon.svg").write_text(
        page.get_svg_image(text_as_path=True), encoding="utf-8"
    )
    (ROOT / "docs/images/icon.png").write_bytes(png_at(page, 256))
    write_ico(
        ROOT / "src/mathtran/icon.ico",
        {s: png_at(page, s) for s in (16, 24, 32, 48, 64, 128, 256)},
    )
    print("icon generated")


if __name__ == "__main__":
    main()
