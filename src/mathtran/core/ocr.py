"""圖片 → LaTeX（Claude 視覺 API）。"""

from __future__ import annotations

import base64
import re
from dataclasses import dataclass

import anthropic

from . import cache
from .config import get_api_key, get_model
from .i18n import tr

# 提示詞改版時要把 PROMPT_VERSION +1：舊版本辨識出的（未被使用者修改的）快取會視為過期。
# v1：只轉錄數學公式（會漏掉圖上的中文標題與說明文字）
# v2：連同圖上所有文字（含中文）一起轉錄
PROMPT_VERSION = 2
PROMPT = (
    "Transcribe EVERYTHING written in this image into LaTeX: the mathematical formulas "
    "AND all text, including Chinese (or any other language) titles, labels, captions "
    "and notes. Do not skip, translate or summarize anything.\n"
    "Rules:\n"
    "- Put every piece of ordinary text (any language) inside \\text{...}, "
    "e.g. \\text{正弦定理}. Keep the original characters exactly as written.\n"
    "- Keep the original reading order (top to bottom, left to right). "
    "Use one \\\\ line break per visual line and wrap the whole thing in an "
    "aligned (or gathered) environment when there is more than one line.\n"
    "- Output ONLY the raw LaTeX code: no explanation, no markdown fences, "
    "no surrounding $ or \\[ \\] delimiters."
)


class OcrError(RuntimeError):
    pass


def sniff_media_type(data: bytes) -> str:
    if data.startswith(b"\x89PNG"):
        return "image/png"
    if data.startswith(b"\xff\xd8"):
        return "image/jpeg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    if data[:3] == b"GIF":
        return "image/gif"
    raise OcrError(tr("unsupported_image"))


def clean_latex(text: str) -> str:
    t = text.strip()
    t = re.sub(r"^```(?:latex|tex)?\s*|\s*```$", "", t).strip()
    for left, right in (("$$", "$$"), (r"\[", r"\]"), ("$", "$"), (r"\(", r"\)")):
        if t.startswith(left) and t.endswith(right) and len(t) > len(left) + len(right):
            t = t[len(left) : -len(right)].strip()
            break
    return t


@dataclass
class OcrResult:
    latex: str
    hash: str
    cached: bool  # True 表示直接取自快取，沒有呼叫 API


def recognize(
    image: bytes,
    *,
    use_cache: bool = True,
    client: anthropic.Anthropic | None = None,
) -> OcrResult:
    """辨識圖片；use_cache=True 時，已辨識過（或使用者修改過）的圖片直接回傳快取。"""
    h = cache.sha256_hex(image)
    if use_cache:
        hit = cache.get(h, min_prompt=PROMPT_VERSION)  # 舊提示詞辨識出的結果視為過期
        if hit and hit.get("latex"):
            return OcrResult(hit["latex"], h, True)
    latex = _call_api(image, client)
    # 重新辨識會覆蓋舊結果（含手動修改）
    cache.put(h, latex, model=get_model(), prompt=PROMPT_VERSION)
    return OcrResult(latex, h, False)


def image_to_latex(
    image: bytes, client: anthropic.Anthropic | None = None, use_cache: bool = True
) -> str:
    return recognize(image, use_cache=use_cache, client=client).latex


def _call_api(image: bytes, client: anthropic.Anthropic | None) -> str:
    if client is None:
        key = get_api_key()
        if not key:
            raise OcrError(tr("api_key_missing"))
        client = anthropic.Anthropic(api_key=key)
    media_type = sniff_media_type(image)
    try:
        msg = client.messages.create(
            model=get_model(),
            max_tokens=2048,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": base64.b64encode(image).decode(),
                            },
                        },
                        {"type": "text", "text": PROMPT},
                    ],
                }
            ],
        )
    except anthropic.APIError as e:
        raise OcrError(tr("api_failed", err=e)) from e
    text = "".join(b.text for b in msg.content if b.type == "text")
    return clean_latex(text)
