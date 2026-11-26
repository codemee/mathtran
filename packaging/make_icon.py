"""產生 App 圖示：白色文件（右上角有摺角）上壓一條紅色橫向長條（像 PDF 圖示），長條裡是白色粗體 f(x)。

白色文件當底，圖示在深色工作列 / 深色背景上才清楚；文件外圍有一圈淡灰藍的邊線，
在白色背景上也看得出輪廓。紅底白字的 f(x) 是整個圖示對比最強、最醒目的地方。

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

import io

import pymupdf
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SIZE = 256
WHITE = (1, 1, 1)
RED = (0.86, 0.16, 0.18)        # 長條的紅色
EDGE = (0.55, 0.62, 0.74)       # 文件邊線：淡灰藍（白色背景上才看得出文件的輪廓）
FOLD = (0.88, 0.91, 0.96)       # 摺角的顏色
TEXT, FONT = "f(x)", "tibi"     # Times 粗斜體
BOLD = 0.035                    # 字形加粗（相對字級的描邊粗細）

# 文件（256 的畫布）：瘦窄的直式文件，左 56、右 200（寬 144），上 12、下 244（高 232，約 0.62:1），右上角摺 44
DOC_L, DOC_R, DOC_T, DOC_B, FOLD_SIZE = 56, 200, 12, 244, 44
# 紅色長條：比文件寬，兩端各突出約 32，才有「壓在文件上」的 PDF 圖示味道；位置在文件偏下，避開摺角。
# 長條夠高，可顯示文字的空間大，f(x) 才能放大、小尺寸時也看得清楚。
# （注意：PyMuPDF 內建字型雖然 has_glyph 說有積分符號 ∫，實際畫出來卻是一個白色圓點，不能用。）
BAR = pymupdf.Rect(24, 88, 232, 228)
TEXT_HEIGHT = 86                # f(x) 墨跡的高度（長條高 140，上下各留 27；寬度約 149，左右各留約 30）


def _draw(page: pymupdf.Page, fontsize: float, x: float, y: float, color=WHITE) -> None:
    # render_mode=2：填色 + 描邊（字形變粗）。描邊色用 color、填色用 fill（兩個都要設，否則填色會是預設的黑色）
    page.insert_text((x, y), TEXT, fontname=FONT, fontsize=fontsize,
                     color=color, fill=color, render_mode=2, border_width=BOLD)


def _draw_bar(page: pymupdf.Page) -> None:
    """紅色長條，純色、沒有邊線。"""
    sh = page.new_shape()
    sh.draw_rect(BAR, radius=0.22)
    sh.finish(fill=RED, color=None)   # color=None → 不畫邊線
    sh.commit()


def _draw_document(page: pymupdf.Page) -> None:
    """白色文件，右上角有摺角；外圍一圈淡灰藍邊線。"""
    sh = page.new_shape()
    sh.draw_polyline([
        (DOC_L, DOC_T), (DOC_R - FOLD_SIZE, DOC_T), (DOC_R, DOC_T + FOLD_SIZE), (DOC_R, DOC_B), (DOC_L, DOC_B),
    ])
    sh.finish(fill=WHITE, color=EDGE, width=7, closePath=True, lineJoin=1)
    sh.commit()
    sh = page.new_shape()   # 摺角：往內折的三角形
    sh.draw_polyline([(DOC_R - FOLD_SIZE, DOC_T), (DOC_R - FOLD_SIZE, DOC_T + FOLD_SIZE), (DOC_R, DOC_T + FOLD_SIZE)])
    sh.finish(fill=FOLD, color=EDGE, width=7, closePath=True, lineJoin=1)
    sh.commit()


def _ink_bbox(fontsize: float) -> tuple[int, int, int, int, int, int]:
    """在試畫頁面上量字形「實際的墨跡範圍」。

    斜體的 f 尾巴會往左下伸出去，只用字寬 / 字級置中會把它切掉，所以要量真正畫出來的範圍。
    回傳 (左, 上, 右, 下, 原點x, 原點y)。
    """
    ox, oy = 150, 350
    doc = pymupdf.open()
    page = doc.new_page(width=SIZE * 2, height=SIZE * 2)
    _draw(page, fontsize, ox, oy)
    pix = page.get_pixmap(alpha=True)
    img = Image.frombytes("RGBA", (pix.width, pix.height), pix.samples)
    left, top, right, bottom = img.getchannel("A").getbbox()
    return left, top, right, bottom, ox, oy


def build_page() -> tuple[pymupdf.Document, pymupdf.Page]:
    """透明底；白色文件上壓著紅色長條，長條裡是白色 f(x)。"""
    fontsize = 80.0
    for _ in range(2):   # 縮放到墨跡的高度剛好等於 TEXT_HEIGHT（量兩次，字級與墨跡大小不是完全成正比）
        left, top, right, bottom, _, _ = _ink_bbox(fontsize)
        fontsize *= TEXT_HEIGHT / (bottom - top)
    left, top, right, bottom, ox, oy = _ink_bbox(fontsize)
    # 把墨跡的中心移到紅色長條的正中央
    cx, cy = (BAR.x0 + BAR.x1) / 2, (BAR.y0 + BAR.y1) / 2
    x = ox + (cx - (left + right) / 2)
    y = oy + (cy - (top + bottom) / 2)

    doc = pymupdf.open()
    page = doc.new_page(width=SIZE, height=SIZE)
    _draw_document(page)
    _draw_bar(page)
    _draw(page, fontsize, x, y)
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
    big = Image.open(io.BytesIO(png_at(page, 1024))).convert("RGBA")
    big.save(
        ROOT / "src/mathtran/icon.icns",
        format="ICNS",
        sizes=[(16, 16), (32, 32), (64, 64), (128, 128), (256, 256), (512, 512), (1024, 1024)],
    )
    print("icon generated")


if __name__ == "__main__":
    main()
