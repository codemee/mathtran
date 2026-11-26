"""LaTeX 公式 → PDF / SVG（使用 tectonic 編譯）。"""

from __future__ import annotations

import os
import re
import shutil
import sys
import subprocess
import tempfile
from pathlib import Path

import pymupdf

TEMPLATE = r"""\documentclass[border=4pt,varwidth=true]{standalone}
\usepackage{amsmath,amssymb,amsfonts,mathtools}
%s\begin{document}
%s
\end{document}
"""

_CJK_RE = re.compile(r"[\u2e80-\u9fff\uf900-\ufaff\uff00-\uffef\u3000-\u303f]")

# tectonic 以字型名稱向系統查詢（用檔案路徑會失敗），依平台選預設 CJK 字型
_CJK_FONTS = {
    "win32": "Microsoft JhengHei",
    "darwin": "PingFang TC",
}


def cjk_font() -> str:
    return os.environ.get("MATHTRAN_CJK_FONT") or _CJK_FONTS.get(sys.platform, "Noto Sans CJK TC")


_CJK_RUN_RE = re.compile(r"[\u2e80-\u9fff\uf900-\ufaff\uff00-\uffef\u3000-\u303f]+")
_TEXT_CMD_RE = re.compile(r"\\(?:text\w*|mbox|hbox)\s*\{")


def _in_text_cmd(prefix: str) -> bool:
    """prefix 結尾處是否仍在 \\text{...} 之類的大括號內。"""
    last = None
    for last in _TEXT_CMD_RE.finditer(prefix):
        pass
    if last is None:
        return False
    return prefix[last.end() :].count("{") - prefix[last.end() :].count("}") >= 0


def wrap_cjk_in_text(latex: str) -> str:
    """數學模式不會畫中文：把不在 \\text{} 內的中日韓字元包進 \\text{}。"""

    def repl(m: re.Match) -> str:
        if _in_text_cmd(latex[: m.start()]):
            return m.group(0)
        return "\\text{" + m.group(0) + "}"

    return _CJK_RUN_RE.sub(repl, latex)


def _preamble(latex: str) -> str:
    """內容含中日韓字元時才載入 xeCJK，避免沒有必要的字型相依。"""
    if _CJK_RE.search(latex):
        return "\\usepackage{xeCJK}\n\\setCJKmainfont{%s}\n" % cjk_font()
    return ""


# 這些環境自帶數學模式，不能再包 \[ \]；pmatrix、aligned 等需要外層包裹
_STANDALONE_ENV = re.compile(
    r"\\begin\{(equation|align|alignat|gather|multline|flalign|eqnarray|displaymath|math)\*?\}"
)


class RenderError(RuntimeError):
    pass


def find_tectonic() -> str:
    path = shutil.which("tectonic")
    if not path:
        raise RenderError("找不到 tectonic，請先執行：scoop install tectonic")
    return path


def wrap_latex(latex: str) -> str:
    """把公式包成可編譯的文件內容；已含數學環境者原樣使用。"""
    s = latex.strip()
    if s.startswith(("$", r"\[", r"\(")) or _STANDALONE_ENV.match(s):
        body = s
    else:
        body = "\\[\n" + s + "\n\\]"
    body = wrap_cjk_in_text(body)
    return TEMPLATE % (_preamble(body), body)


def to_pdf(latex: str) -> bytes:
    exe = find_tectonic()
    with tempfile.TemporaryDirectory() as tmp:
        tex = Path(tmp) / "formula.tex"
        tex.write_text(wrap_latex(latex), encoding="utf-8")
        proc = subprocess.run(
            [exe, "-X", "compile", "--untrusted", "formula.tex"],
            cwd=tmp,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        pdf = Path(tmp) / "formula.pdf"
        if proc.returncode != 0 or not pdf.exists():
            msg = (proc.stderr or proc.stdout)[-1500:]
            if "cannot be found" in msg and "xeCJK" in tex.read_text(encoding="utf-8"):
                msg = (
                    f"找不到中文字型「{cjk_font()}」，"
                    "請安裝該字型，或設定環境變數 MATHTRAN_CJK_FONT 指定其他字型名稱。\n" + msg
                )
            raise RenderError("LaTeX 編譯失敗：\n" + msg)
        return pdf.read_bytes()


def pdf_to_svg(pdf: bytes) -> str:
    with pymupdf.open(stream=pdf, filetype="pdf") as doc:
        return doc[0].get_svg_image(text_as_path=True)


def to_svg(latex: str) -> str:
    return pdf_to_svg(to_pdf(latex))
