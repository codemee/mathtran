"""批次匯出：多個公式 × 多種格式 → 一個 zip。"""

from __future__ import annotations

import io
import re
import zipfile
from dataclasses import dataclass, field

from . import render
from .i18n import tr

FORMATS = ("svg", "pdf", "tex")

_ILLEGAL = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_IMAGE_EXT = re.compile(r"\.(png|jpe?g|webp|gif|bmp)$", re.I)


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


def export_zip(items: list[dict], formats: list[str]) -> BatchResult:
    """items: [{"name": 圖檔名, "latex": LaTeX}]；formats: svg / pdf / tex 的任意組合。

    每個項目最多編譯一次（svg 與 pdf 共用同一份 PDF）。個別失敗不會中斷整批：
    失敗原因寫進 zip 內的 errors.txt。純 tex 不需要 tectonic。
    """
    formats = [f for f in dict.fromkeys(formats)]  # 去重、保留順序
    if not formats or any(f not in FORMATS for f in formats):
        raise ValueError("formats 必須是 svg / pdf / tex 的非空組合")
    stems = unique_stems([safe_stem(it.get("name", "")) for it in items])
    buf = io.BytesIO()
    ok, errors = 0, []
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for item, stem in zip(items, stems):
            latex = (item.get("latex") or "").strip()
            if not latex:
                errors.append(tr("empty_skipped", name=stem))
                continue
            if "tex" in formats:
                zf.writestr(f"{stem}.tex", render.to_tex(latex).encode("utf-8"))
                ok += 1
            if "pdf" in formats or "svg" in formats:
                try:
                    pdf = render.to_pdf(latex)
                except render.RenderError as e:
                    errors.append(f"{stem}: {e}")
                    continue
                if "pdf" in formats:
                    zf.writestr(f"{stem}.pdf", pdf)
                    ok += 1
                if "svg" in formats:
                    zf.writestr(f"{stem}.svg", render.pdf_to_svg(pdf).encode("utf-8"))
                    ok += 1
        if errors:
            zf.writestr("errors.txt", "\n\n".join(errors))
    return BatchResult(buf.getvalue(), ok, len(errors), errors)
