from types import SimpleNamespace

import pytest

from mathtran.core import ocr, render


def test_clean_latex_strips_fences_and_delimiters():
    assert ocr.clean_latex("```latex\n$$E=mc^2$$\n```") == "E=mc^2"
    assert ocr.clean_latex(r"\[ x^2 \]") == "x^2"
    assert ocr.clean_latex("a+b") == "a+b"


def test_sniff_media_type():
    assert ocr.sniff_media_type(b"\x89PNG\r\n") == "image/png"
    with pytest.raises(ocr.OcrError):
        ocr.sniff_media_type(b"nope")


def test_image_to_latex_with_mock_client():
    class FakeMessages:
        def create(self, **kw):
            return SimpleNamespace(content=[SimpleNamespace(type="text", text="$$\\frac{a}{b}$$")])

    client = SimpleNamespace(messages=FakeMessages())
    assert ocr.image_to_latex(b"\x89PNG....", client=client) == r"\frac{a}{b}"


def test_wrap_latex():
    assert "\\[" in render.wrap_latex("x^2")
    assert "\\[" not in render.wrap_latex("$x^2$")


def test_render_real_tectonic():
    pdf = render.to_pdf(r"\int_0^1 x^2\,dx = \frac13")
    assert pdf.startswith(b"%PDF")
    svg = render.pdf_to_svg(pdf)
    assert "<svg" in svg


def test_render_error():
    with pytest.raises(render.RenderError):
        render.to_pdf(r"\undefinedmacro{")


def test_wrap_matrix_and_align_env():
    assert '\\[' in render.wrap_latex(r'\begin{pmatrix}a&b\end{pmatrix}')
    assert '\\[' not in render.wrap_latex(r'\begin{align}a&=b\end{align}')


def test_cjk_preamble_only_when_needed():
    assert 'xeCJK' not in render.wrap_latex('x^2')
    assert 'xeCJK' in render.wrap_latex(r'x = \text{答案}')


def test_render_cjk_real_tectonic():
    pdf = render.to_pdf(r'\int_0^1 x^3dx = 答案')
    import pymupdf
    with pymupdf.open(stream=pdf, filetype='pdf') as d:
        assert '答案' in d[0].get_text()


def test_wrap_cjk_in_text():
    w = render.wrap_cjk_in_text
    assert w('x=答案') == r'x=\text{答案}'
    assert w(r'\text{答案}') == r'\text{答案}'
    assert w(r'\text{a {b} 答案}') == r'\text{a {b} 答案}'
    assert w(r'\text{甲}+乙') == r'\text{甲}+\text{乙}'
