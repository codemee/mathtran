# Third-party notices / 第三方授權聲明

| 元件 Component | 用途 Use | 授權 License | 是否隨本專案散布 Bundled |
|---|---|---|---|
| [KaTeX](https://katex.org/) 0.16.11 | 即時預覽 Live preview (`src/mathtran/web/vendor/`) | MIT（全文 full text：[LICENSE-KaTeX.txt](src/mathtran/web/vendor/LICENSE-KaTeX.txt)）；KaTeX 字型 fonts: SIL OFL 1.1 / MIT | 是 Yes |
| [Tectonic](https://tectonic-typesetting.github.io/) | 編譯 LaTeX Compile LaTeX | MIT | 否 No（另行安裝 install separately） |
| [PyMuPDF](https://pymupdf.readthedocs.io/) | PDF → SVG | AGPL-3.0 / commercial | 否 No（Python 相依 Python dependency） |
| [pywebview](https://pywebview.flowrl.com/) | 桌面視窗 Desktop window | BSD-3-Clause | 否 No |
| [FastAPI](https://fastapi.tiangolo.com/)、[Uvicorn](https://www.uvicorn.org/)、[Typer](https://typer.tiangolo.com/)、[Anthropic SDK](https://github.com/anthropics/anthropic-sdk-python) | 後端、CLI、OCR | MIT / BSD | 否 No |

> **PyMuPDF 為 AGPL-3.0**：若你把 mathtran 與 PyMuPDF 一起打包散布成桌面 App，需遵守 AGPL-3.0（或向 Artifex 取得商業授權）。
> **PyMuPDF is AGPL-3.0**: if you distribute a packaged build that includes PyMuPDF, you must comply with AGPL-3.0 (or obtain a commercial license from Artifex).
