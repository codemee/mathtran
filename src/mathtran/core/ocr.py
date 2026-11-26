"""圖片 → LaTeX（Claude 視覺 API）。"""

from __future__ import annotations

import base64
import re

import anthropic

from .config import get_api_key, get_model

PROMPT = (
    "Transcribe the mathematical formula(s) in this image into LaTeX. "
    "Output ONLY the raw LaTeX code: no explanation, no markdown fences, "
    "no surrounding $ or \\[ \\] delimiters. For multiple lines use an "
    "aligned environment."
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
    raise OcrError("不支援的圖片格式（支援 PNG / JPEG / WebP / GIF）")


def clean_latex(text: str) -> str:
    t = text.strip()
    t = re.sub(r"^```(?:latex|tex)?\s*|\s*```$", "", t).strip()
    for left, right in (("$$", "$$"), (r"\[", r"\]"), ("$", "$"), (r"\(", r"\)")):
        if t.startswith(left) and t.endswith(right) and len(t) > len(left) + len(right):
            t = t[len(left) : -len(right)].strip()
            break
    return t


def image_to_latex(image: bytes, client: anthropic.Anthropic | None = None) -> str:
    if client is None:
        key = get_api_key()
        if not key:
            raise OcrError(
                "未設定 API key：請設定環境變數 ANTHROPIC_API_KEY，"
                "或執行 mathtran config --api-key <KEY>"
            )
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
        raise OcrError(f"Claude API 呼叫失敗：{e}") from e
    text = "".join(b.text for b in msg.content if b.type == "text")
    return clean_latex(text)
