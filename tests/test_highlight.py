"""LaTeX 編輯區的語法標色：配色對比、標記器的行為（標記器是前端 JS，用 node 執行；沒有 node 就略過）。"""

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

HTML = (Path(__file__).resolve().parent.parent / "src/mathtran/web/index.html").read_text(encoding="utf-8")
TOKENS = ["cmd", "text", "op", "num", "brace", "cmt"]


def _lum(hex_color: str) -> float:
    h = hex_color.lstrip("#")
    c = [int(h[i : i + 2], 16) / 255 for i in (0, 2, 4)]
    c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def _contrast(a: str, b: str) -> float:
    hi, lo = sorted([_lum(a), _lum(b)], reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def _theme_blocks() -> dict[str, str]:
    """回傳三個定義配色的區塊：淺色（:root）、跟隨系統的深色、手動深色。"""
    light = re.search(r"\n  :root \{(.*?)\}", HTML, re.S).group(1)
    media = re.search(r':root:not\(\[data-theme="light"\]\) \{(.*?)\}', HTML, re.S).group(1)
    dark = re.search(r':root\[data-theme="dark"\] \{(.*?)\}', HTML, re.S).group(1)
    return {"light": light, "system-dark": media, "dark": dark}


@pytest.mark.parametrize("theme", ["light", "system-dark", "dark"])
def test_token_colors_are_readable(theme):
    block = _theme_blocks()[theme]
    bg = re.search(r"--bg:(#[0-9a-fA-F]{6})", block).group(1)
    for name in TOKENS:
        color = re.search(rf"--tk-{name}:(#[0-9a-fA-F]{{6}})", block).group(1)
        assert _contrast(color, bg) >= 4.5, f"{theme} --tk-{name} 對比不足"


def test_dark_blocks_agree():
    blocks = _theme_blocks()
    for name in TOKENS:
        pick = lambda b: re.search(rf"--tk-{name}:(#[0-9a-fA-F]+)", b).group(1)
        assert pick(blocks["system-dark"]) == pick(blocks["dark"])


@pytest.mark.skipif(shutil.which("node") is None, reason="需要 node 才能執行前端的標記器")
def test_tokenizer(tmp_path):
    start, end = HTML.index("const HL_TEXT_CMDS"), HTML.index("function hlRender")
    script = tmp_path / "t.js"
    script.write_text(
        HTML[start:end]
        + "\nconst cases = JSON.parse(process.argv[2]);"
        + "\nconsole.log(JSON.stringify(cases.map(s => hlTokens(s).map(k => [k.cls, k.text, !!k.bad]))));",
        encoding="utf-8",
    )
    cases = [r"\frac{a^2}{b}+3.5", r"\text{面積 {x}}=1 % 註解", "a}{b", r"\{x\}", r"\text{未關"]
    out = subprocess.run(["node", str(script), json.dumps(cases)], capture_output=True, text=True, check=True, encoding="utf-8")
    frac, text, bad, esc, unclosed = json.loads(out.stdout)

    assert ["c", r"\frac", False] in frac and ["o", "^", False] in frac and ["n", "3.5", False] in frac
    assert "".join(k[1] for k in frac) == cases[0]                      # 標色不能吃掉任何字元
    assert ["t", "面積 {x}", False] in text and ["k", "% 註解", False] in text   # \text 內容是文字；註解到行尾
    assert [k[2] for k in bad if k[0] == "b"] == [True, True]            # 沒有配對的括號
    assert ["c", r"\{", False] in esc and not any(k[0] == "b" for k in esc)  # 跳脫的括號不算括號
    assert [k for k in unclosed if k[0] == "b"] == [["b", "{", True]]
