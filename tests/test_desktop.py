import io
import zipfile

from mathtran.desktop import extract_zip


def make_zip(files: dict) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for n, d in files.items():
            zf.writestr(n, d)
    return buf.getvalue()


def test_extract_zip_writes_files(tmp_path):
    names = extract_zip(make_zip({"a.svg": "1", "b.svg": "2"}), tmp_path)
    assert names == ["a.svg", "b.svg"]
    assert (tmp_path / "a.svg").read_text() == "1"


def test_extract_zip_never_overwrites(tmp_path):
    (tmp_path / "a.svg").write_text("mine")
    names = extract_zip(make_zip({"a.svg": "new"}), tmp_path)
    assert names == ["a (2).svg"]
    assert (tmp_path / "a.svg").read_text() == "mine"  # 原檔不動


def test_extract_zip_blocks_path_traversal(tmp_path):
    sub = tmp_path / "out"
    sub.mkdir()
    extract_zip(make_zip({"../evil.svg": "x", "d/../../evil2.svg": "y"}), sub)
    assert not (tmp_path / "evil.svg").exists() and not (tmp_path / "evil2.svg").exists()
    assert (sub / "evil.svg").exists() and (sub / "evil2.svg").exists()
