# Third-party notices / 第三方授權聲明

本專案採用 **GPL-3.0-or-later**（見 [LICENSE](LICENSE)）。
This project is licensed under **GPL-3.0-or-later** (see [LICENSE](LICENSE)).

| 元件 Component | 用途 Use | 授權 License | 與 GPL-3.0 相容 Compatible | 隨專案散布 Bundled |
|---|---|---|---|---|
| [KaTeX](https://katex.org/) 0.16.11 | 即時預覽 Live preview (`src/mathtran/web/vendor/`) | MIT（全文 full text：[LICENSE-KaTeX.txt](src/mathtran/web/vendor/LICENSE-KaTeX.txt)）；KaTeX 字型 fonts: SIL OFL 1.1 / MIT | 是 Yes | 是 Yes |
| [Tectonic](https://tectonic-typesetting.github.io/) | 編譯 LaTeX Compile LaTeX | MIT | 是 Yes（獨立程式 separate program） | 否 No（另行安裝 install separately） |
| [PyMuPDF](https://pymupdf.readthedocs.io/) | PDF → SVG | AGPL-3.0 / commercial | 是 Yes（見下 see below） | 否 No（Python 相依 Python dependency） |
| [pywebview](https://pywebview.flowrl.com/) | 桌面視窗 Desktop window | BSD-3-Clause | 是 Yes | 否 No |
| [FastAPI](https://fastapi.tiangolo.com/)、[Uvicorn](https://www.uvicorn.org/)、[Typer](https://typer.tiangolo.com/)、[Anthropic SDK](https://github.com/anthropics/anthropic-sdk-python) | 後端、CLI、OCR | MIT / BSD | 是 Yes | 否 No |

## PyMuPDF（AGPL-3.0）與 GPL-3.0

- GPL-3.0 第 13 條允許把 GPL-3.0 的作品與 AGPL-3.0 的作品連結、合併後散布；各自的授權仍適用於各自的部分，但 **AGPL 第 13 條（網路互動須提供原始碼）會套用到合併後的整體**。
- 因此：散布 mathtran（含打包版本）時，須以 GPL-3.0 以上授權並提供原始碼；若把它當成網路服務提供給他人使用，須讓使用者能取得對應原始碼。
- 若不想受 AGPL 第 13 條約束，可向 Artifex 取得 PyMuPDF 商業授權，或替換 PDF → SVG 的實作。
- 本專案**不**相容 GPL-2.0-only。

GPL-3.0 section 13 permits combining a GPL-3.0 work with an AGPL-3.0 work and conveying the result. Each license keeps applying to its own part, but **AGPL section 13 (offer source to users who interact over a network) applies to the combined work as a whole**. Distribute mathtran (including packaged builds) under GPL-3.0 or later with source; if you offer it as a network service, users must be able to obtain the corresponding source. To avoid AGPL section 13, obtain a commercial PyMuPDF license from Artifex or replace the PDF → SVG step. This project is **not** compatible with GPL-2.0-only.

> 以上為對授權條文的整理，不構成法律意見。This is a summary of license terms, not legal advice.
