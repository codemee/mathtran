"""產生 App 圖示：左上為圓角框內的藍色 f(x)，右下為紅色 PDF 橫條（透明底，接近正方形）。

輸出：
  src/mathtran/web/icon.svg   網頁 favicon（文字已轉外框）
  src/mathtran/icon.ico       桌面視窗 / 打包 exe 圖示（16~256 多尺寸）
  src/mathtran/icon.icns      macOS .app 圖示（16~1024）
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
    """透明底；左上是框起來的藍色 f(x)，右下是紅色 PDF 橫條，整體排成接近正方形。"""
    doc = pymupdf.open()
    page = doc.new_page(width=SIZE, height=SIZE)

    # 左上：不填色的圓角框 + 藍色 f(x)（Times 粗斜體）。藍色在亮 / 暗背景都看得清楚
    frame = pymupdf.Rect(12, 12, 178, 132)
    sh = page.new_shape()
    sh.draw_rect(frame, radius=0.22)
    sh.finish(fill=None, color=BLUE, width=10)   # fill=None → 不填色
    sh.commit()
    text, size = "f(x)", 78
    width = pymupdf.get_text_length(text, fontname="tibi", fontsize=size)
    page.insert_text(
        (frame.x0 + (frame.width - width) / 2, 90), text, fontname="tibi", fontsize=size, color=BLUE
    )

    # 右下：紅色 PDF 橫條，大幅壓在框的右下角上（白邊把兩者分開），
    # 疊得夠多，兩者看起來才是同一個圖示而不是分開的兩個東西
    bar = pymupdf.Rect(78, 102, 244, 226)
    sh = page.new_shape()
    sh.draw_rect(bar, radius=0.22)
    sh.finish(fill=RED, color=WHITE, width=6)
    sh.commit()
    fs = 54
    tw = pymupdf.get_text_length("PDF", fontname="hebo", fontsize=fs)
    page.insert_text(
        (bar.x0 + (bar.width - tw) / 2, bar.y0 + (bar.height + fs * 0.72) / 2),
        "PDF", fontname="hebo", fontsize=fs, color=WHITE,
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
    # macOS 的 .app 圖示（.icns）：從向量原稿直接畫 1024px 再縮小，Retina 螢幕才清楚
    import io

    from PIL import Image

    big = Image.open(io.BytesIO(png_at(page, 1024))).convert("RGBA")
    big.save(
        ROOT / "src/mathtran/icon.icns",
        format="ICNS",
        sizes=[(16, 16), (32, 32), (64, 64), (128, 128), (256, 256), (512, 512), (1024, 1024)],
    )
    print("icon generated")


if __name__ == "__main__":
    main()
