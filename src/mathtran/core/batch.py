"""批次匯出：多個公式 × 多種格式 → 一個 zip（網頁 / 桌面版），或寫進資料夾（命令列）。"""

from __future__ import annotations

import io
import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from . import render
from .i18n import tr

FORMATS = ("svg", "pdf", "tex")

_ILLEGAL = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_IMAGE_EXT = re.compile(r"\.(png|jpe?g|webp|gif|bmp)$", re.I)
_OCR_IMAGE_EXT = re.compile(r"\.(png|jpe?g|webp|gif)$", re.I)   # 辨識支援的格式（資料夾掃描只收這些）


def safe_stem(name: str, fallback: str = "formula") -> str:
    """從圖檔名（可能含資料夾路徑）產生安全的檔名主體。"""
    base = re.split(r"[\\/]", name.strip())[-1]
    base = _IMAGE_EXT.sub("", base)
    base = _ILLEGAL.sub("_", base).strip(" .")
    return base[:80] or fallback


def unique_stems(stems: list[str]) -> list[str]:
    """同名時加上 _2、_3…，比對時不分大小寫（Windows 檔名不分大小寫）。"""
    seen: dict[str, int] = {}
    out = []
    for stem in stems:
        key = stem.lower()
        seen[key] = seen.get(key, 0) + 1
        out.append(stem if seen[key] == 1 else f"{stem}_{seen[key]}")
    return out


@dataclass
class BatchResult:
    data: bytes
    ok: int  # 成功寫入的檔案數
    failed: int  # 失敗（或略過）的項目數
    errors: list[str] = field(default_factory=list)


def clean_formats(formats: list[str]) -> list[str]:
    """去重、保留順序；空的或有不認得的格式就丟 ValueError。"""
    formats = [f for f in dict.fromkeys(formats)]
    if not formats or any(f not in FORMATS for f in formats):
        raise ValueError("formats 必須是 svg / pdf / tex 的非空組合")
    return formats


def render_formats(latex: str, formats: list[str]) -> tuple[dict[str, bytes], render.RenderError | None]:
    """把一個公式輸出成多種格式：回傳 ({副檔名: 內容}, 編譯錯誤)。

    每個公式最多編譯一次（svg 與 pdf 共用同一份 PDF）。純 tex 不需要 tectonic；
    編譯失敗時已經產生的 tex 仍然保留，錯誤另外回傳。
    """
    files: dict[str, bytes] = {}
    if "tex" in formats:
        files["tex"] = render.to_tex(latex).encode("utf-8")
    if "pdf" in formats or "svg" in formats:
        try:
            pdf = render.to_pdf(latex)
        except render.RenderError as e:
            return files, e
        if "pdf" in formats:
            files["pdf"] = pdf
        if "svg" in formats:
            files["svg"] = render.pdf_to_svg(pdf).encode("utf-8")
    return files, None


def export_zip(items: list[dict], formats: list[str]) -> BatchResult:
    """items: [{"name": 圖檔名, "latex": LaTeX}]；formats: svg / pdf / tex 的任意組合。

    個別失敗不會中斷整批：失敗原因寫進 zip 內的 errors.txt。
    """
    formats = clean_formats(formats)
    stems = unique_stems([safe_stem(it.get("name", "")) for it in items])
    buf = io.BytesIO()
    ok, errors = 0, []
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for item, stem in zip(items, stems):
            latex = (item.get("latex") or "").strip()
            if not latex:
                errors.append(tr("empty_skipped", name=stem))
                continue
            files, err = render_formats(latex, formats)
            for ext, data in files.items():
                zf.writestr(f"{stem}.{ext}", data)
                ok += 1
            if err:
                errors.append(f"{stem}: {err}")
        if errors:
            zf.writestr("errors.txt", "\n\n".join(errors))
    return BatchResult(buf.getvalue(), ok, len(errors), errors)


def collect_images(paths: list[Path], recursive: bool = False) -> list[Path]:
    """命令列的圖片參數：檔案照用，資料夾展開成裡面的圖片（排序；recursive 才進子資料夾）。

    資料夾裡沒有任何圖片就丟 FileNotFoundError(資料夾)；重複的路徑只留一個。
    """
    out: list[Path] = []
    seen: set[Path] = set()
    for p in paths:
        if p.is_dir():
            found = sorted(
                f for f in (p.rglob("*") if recursive else p.iterdir())
                if f.is_file() and _OCR_IMAGE_EXT.search(f.name)
            )
            if not found:
                raise FileNotFoundError(str(p))
        else:
            found = [p]
        for f in found:
            key = f.resolve()
            if key not in seen:
                seen.add(key)
                out.append(f)
    return out
