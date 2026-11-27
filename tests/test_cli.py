"""命令列：--version、.tex 輸出、多張圖片 / 資料夾的批次處理（辨識用替身，編譯用真的 tectonic）。"""

import json

import pytest
from typer.testing import CliRunner

import mathtran
from mathtran.cli import app
from mathtran.core import batch, ocr
from mathtran.core.i18n import tr

runner = CliRunner()


@pytest.fixture
def fake_ocr(monkeypatch):
    """替身：圖片的內容就是它的 LaTeX；內容是 FAIL 就丟辨識錯誤，NOKEY 就丟「沒有 API key」。"""
    calls = []

    def fake(image, client=None, use_cache=True):
        calls.append(image)
        text = image.decode()
        if text == "FAIL":
            raise ocr.OcrError("辨識失敗了")
        if text == "NOKEY":
            raise ocr.OcrError(tr("api_key_missing"))
        return text

    monkeypatch.setattr(ocr, "image_to_latex", fake)
    return calls


def make_images(tmp_path, **named):
    d = tmp_path / "imgs"
    d.mkdir(exist_ok=True)
    for name, latex in named.items():
        (d / name.replace("_png", ".png")).write_bytes(latex.encode())
    return d


def test_version():
    r = runner.invoke(app, ["--version"])
    assert r.exit_code == 0 and r.output.strip() == mathtran.APP_TITLE
    assert runner.invoke(app, ["-V"]).output.strip() == mathtran.APP_TITLE


def test_render_tex_needs_no_tectonic(tmp_path, monkeypatch):
    monkeypatch.setattr("mathtran.core.render.find_tectonic", lambda: (_ for _ in ()).throw(AssertionError("不該呼叫 tectonic")))
    out = tmp_path / "f.tex"
    r = runner.invoke(app, ["render", "E=mc^2", "-o", str(out)])
    assert r.exit_code == 0, r.output
    assert "\\documentclass" in out.read_text(encoding="utf-8") and "E=mc^2" in out.read_text(encoding="utf-8")


def test_render_several_outputs_and_stdin(tmp_path):
    svg, tex, pdf = tmp_path / "a.svg", tmp_path / "sub" / "a.tex", tmp_path / "a.pdf"
    r = runner.invoke(app, ["render", "-", "-o", str(svg), "-o", str(tex), "-o", str(pdf)], input="x^2+y^2")
    assert r.exit_code == 0, r.output
    assert svg.read_text(encoding="utf-8").lstrip().startswith("<")
    assert "x^2+y^2" in tex.read_text(encoding="utf-8")
    assert pdf.read_bytes().startswith(b"%PDF")


def test_render_bad_extension(tmp_path):
    r = runner.invoke(app, ["render", "x", "-o", str(tmp_path / "a.png")])
    assert r.exit_code == 2


def test_convert_single_image_to_files(tmp_path, fake_ocr):
    d = make_images(tmp_path, a_png="a^2")
    r = runner.invoke(app, ["convert", str(d / "a.png"), "-o", str(tmp_path / "a.svg"), "-o", str(tmp_path / "a.tex")])
    assert r.exit_code == 0, r.output
    assert "a^2" in r.stdout                                     # 單張時照舊把 LaTeX 印出來
    assert (tmp_path / "a.svg").exists() and "a^2" in (tmp_path / "a.tex").read_text(encoding="utf-8")


def test_convert_batch_to_folder(tmp_path, fake_ocr):
    d = make_images(tmp_path, a_png="a^2", b_png="b^2")
    out = tmp_path / "out"
    r = runner.invoke(app, ["convert", str(d / "a.png"), str(d / "b.png"), "-o", str(out), "-f", "svg", "-f", "tex"])
    assert r.exit_code == 0, r.output
    assert sorted(p.name for p in out.iterdir()) == ["a.svg", "a.tex", "b.svg", "b.tex"]
    assert "2 張成功" in r.output and "4 個檔案" in r.output
    assert "b^2" in (out / "b.tex").read_text(encoding="utf-8")


def test_convert_folder_default_format_and_recursive(tmp_path, fake_ocr):
    d = make_images(tmp_path, a_png="a^2")
    (d / "notes.txt").write_text("not an image")
    sub = d / "sub"
    sub.mkdir()
    (sub / "c.png").write_bytes(b"c^2")
    out = tmp_path / "out"
    assert runner.invoke(app, ["convert", str(d), "-o", str(out)]).exit_code == 0
    assert [p.name for p in out.iterdir()] == ["a.svg"]          # 預設 svg；只收圖片；不進子資料夾
    out2 = tmp_path / "out2"
    assert runner.invoke(app, ["convert", str(d), "-r", "-o", str(out2), "-f", "tex"]).exit_code == 0
    assert sorted(p.name for p in out2.iterdir()) == ["a.tex", "c.tex"]


def test_convert_same_names_do_not_overwrite(tmp_path, fake_ocr):
    a = tmp_path / "x"; a.mkdir(); (a / "p.png").write_bytes(b"one")
    b = tmp_path / "y"; b.mkdir(); (b / "p.png").write_bytes(b"two")
    out = tmp_path / "out"
    assert runner.invoke(app, ["convert", str(a / "p.png"), str(b / "p.png"), "-o", str(out), "-f", "tex"]).exit_code == 0
    assert sorted(p.name for p in out.iterdir()) == ["p.tex", "p_2.tex"]


def test_convert_one_failure_does_not_stop_the_rest(tmp_path, fake_ocr):
    d = make_images(tmp_path, a_png="a^2", b_png="FAIL", c_png="c^2")
    out = tmp_path / "out"
    r = runner.invoke(app, ["convert", str(d), "-o", str(out), "-f", "tex"])
    assert r.exit_code == 1
    assert sorted(p.name for p in out.iterdir()) == ["a.tex", "c.tex"]
    assert "2 張成功、1 張失敗" in r.output and "辨識失敗了" in r.output


def test_convert_missing_api_key_aborts(tmp_path, fake_ocr):
    d = make_images(tmp_path, a_png="NOKEY", b_png="NOKEY", c_png="NOKEY")
    r = runner.invoke(app, ["convert", str(d), "-o", str(tmp_path / "out"), "-j", "1"])
    assert r.exit_code == 1 and tr("api_key_missing") in r.output
    assert len(fake_ocr) < 3                                       # 知道沒有 key 就中止，不會把每張都試完（頂多多跑一張正在進行的）


def test_convert_argument_errors(tmp_path, fake_ocr):
    d = make_images(tmp_path, a_png="a", b_png="b")
    assert runner.invoke(app, ["convert", str(d), "-o", str(tmp_path / "o.svg")]).exit_code == 2     # 多張要資料夾
    assert runner.invoke(app, ["convert", str(d / "a.png"), "-o", str(tmp_path / "o.svg"), "-f", "pdf"]).exit_code == 2
    assert runner.invoke(app, ["convert", str(d), "-o", str(tmp_path / "o"), "-f", "gif"]).exit_code == 2
    empty = tmp_path / "empty"; empty.mkdir()
    r = runner.invoke(app, ["convert", str(empty), "-o", str(tmp_path / "o")])
    assert r.exit_code == 1 and str(empty) in r.output


def test_ocr_single_and_multiple(tmp_path, fake_ocr):
    d = make_images(tmp_path, a_png="a^2", b_png="b^2")
    assert runner.invoke(app, ["ocr", str(d / "a.png")]).stdout.strip() == "a^2"       # 單張：只有 LaTeX
    out = runner.invoke(app, ["ocr", str(d)]).stdout
    assert "% a.png\na^2" in out and "% b.png\nb^2" in out


def test_ocr_json(tmp_path, fake_ocr):
    d = make_images(tmp_path, a_png="a^2", b_png="FAIL")
    r = runner.invoke(app, ["ocr", str(d), "--json"])
    assert r.exit_code == 1                                                       # 有失敗就回傳 1，但 JSON 仍完整
    data = json.loads(r.stdout)
    assert [(Path_name(x["file"]), x["latex"], bool(x["error"])) for x in data] == [("a.png", "a^2", False), ("b.png", None, True)]
    single = json.loads(runner.invoke(app, ["ocr", str(d / "a.png"), "--json"]).stdout)
    assert len(single) == 1 and single[0]["latex"] == "a^2"


def Path_name(p):
    return p.replace("\\", "/").split("/")[-1]


def test_batch_helpers(tmp_path):
    (tmp_path / "a.PNG").write_bytes(b"1")
    (tmp_path / "b.txt").write_text("x")
    assert [p.name for p in batch.collect_images([tmp_path])] == ["a.PNG"]
    assert len(batch.collect_images([tmp_path, tmp_path / "a.PNG"])) == 1           # 重複的只留一個
    with pytest.raises(ValueError):
        batch.clean_formats(["svg", "png"])
    files, err = batch.render_formats("x^2", ["tex"])
    assert err is None and list(files) == ["tex"]
