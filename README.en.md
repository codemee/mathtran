<p align="center"><img src="https://raw.githubusercontent.com/codemee/mathtran/main/docs/images/icon.png" width="96" alt="Mathtran icon"></p>

# Mathtran

**Math formula in an image → LaTeX → preview → export SVG / PDF**

🌐 English ｜ [繁體中文](https://github.com/codemee/mathtran/blob/main/README.md) ｜ Technical docs: [Architecture & design (English)](https://github.com/codemee/mathtran/blob/main/docs/en/architecture.md)

![Mathtran main window](https://raw.githubusercontent.com/codemee/mathtran/main/docs/images/app-main.png)

## What it does

| Step | Description |
|---|---|
| ① Add an image | Paste a screenshot (Ctrl+V), drag a file in, or click to pick one. PNG / JPEG / WebP / GIF |
| ② Recognize as LaTeX | A Claude vision model turns it into LaTeX; you can edit the result |
| ③ Preview | Instant live preview (works offline), plus an "accurate preview" compiled with real LaTeX |
| ④ Export | Export **SVG** (text converted to outlines) or **PDF**; or copy the LaTeX source |

Three ways to use it, all sharing one core:

| Mode | Command | Best for |
|---|---|---|
| Desktop window | `mathtran gui` | Everyday use; exports open a "Save as" dialog |
| Browser | `mathtran serve` | Working in a browser tab |
| Command line | `mathtran ocr / render / convert` | Batch jobs, scripting |

## Installation

### Requirements

| Item | Notes |
|---|---|
| Python | 3.14+, [uv](https://docs.astral.sh/uv/) recommended |
| Tectonic | Compiles LaTeX (needed for export and accurate preview) |
| Anthropic API key | Needed for image recognition; not needed for LaTeX → SVG/PDF only |
| CJK font | Used when the formula contains Chinese; Windows ships "Microsoft JhengHei" |

### Steps

1. Install Tectonic:
   - Windows: `scoop install tectonic`
   - macOS / Linux: `brew install tectonic`
2. Install Mathtran:
   ```bash
   uv tool install git+https://github.com/codemee/mathtran
   ```
3. Set your API key (any one):
   - Environment variable: `ANTHROPIC_API_KEY`
   - Command: `mathtran config --api-key <YOUR_KEY>`
   - The "API key" button at the top right of the desktop / web UI
4. Launch: `mathtran gui`

> ⚠️ **The first compile is slow**: Tectonic downloads LaTeX packages over the network (a few minutes). Later runs are fast.
> ⚠️ Only tested on **Windows 11** so far; macOS / Linux should work but are unverified.

## Usage

### Desktop / web UI

1. Paste or drop an image containing a formula into the left panel
2. Click **辨識為 LaTeX** (Recognize as LaTeX)
3. Fix the LaTeX on the right; the preview below updates live
4. Click **精準預覽** (Accurate preview) to see the real LaTeX typesetting
5. Click **匯出 SVG** or **匯出 PDF** (Export)

The **status bar** at the bottom of the window shows what is happening:

| Area | Content |
|---|---|
| Left | Progress, success messages (e.g. "Saved: C:\\…\\formula.pdf"), errors (in red) |
| Right | `API key ✓`, `tectonic ✓`; a red warning when something is missing |

> The UI labels are currently in Traditional Chinese.

### Command line

| Command | What it does |
|---|---|
| `mathtran ocr image.png` | Recognize an image and print the LaTeX |
| `mathtran render "E=mc^2" -o out.svg` | LaTeX → SVG or PDF (extension picks the format) |
| `mathtran convert image.png -o out.pdf` | Recognize and export in one step |
| `mathtran config --api-key KEY` | Save the API key (stored under `~/.mathtran/`) |
| `mathtran serve [--port 8765]` | Start the web UI |
| `mathtran gui` | Start the desktop window |

Examples:

```bash
# image -> PDF
mathtran convert formula.png -o formula.pdf

# read LaTeX from stdin
echo '\begin{pmatrix}a&b\\c&d\end{pmatrix}' | mathtran render - -o matrix.svg
```

### Formula tips

- No need to add `$…$` or `\[…\]`; Mathtran wraps the formula for you
- Environments like `pmatrix` and `aligned` work as-is; environments that bring their own math mode (`align`, `equation`, …) are used unchanged
- **Chinese** text in formulas is handled automatically (CJK font + `\text{}`); set the `MATHTRAN_CJK_FONT` environment variable to use a different font

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| Status bar shows "⚠ 未設定 API key" | Set the key (Installation, step 3) |
| Status bar shows "⚠ 找不到 tectonic" | Run `scoop install tectonic` (or `brew install tectonic`) and restart Mathtran |
| First export takes very long | Tectonic is downloading packages; stay online and wait |
| CJK font not found | Install the font, or set `MATHTRAN_CJK_FONT` to a font name on your system |
| Wrong recognition result | Edit it in the text box; crop the image to just the formula and use a higher resolution |

## Privacy

- **For recognition, the image is uploaded to the Anthropic API.** Don't use it for content that must not leave your machine
- Preview and export run locally; nothing is uploaded
- Your API key is stored only in `~/.mathtran/config.json` on your machine

## License

[MIT License](https://github.com/codemee/mathtran/blob/main/LICENSE). See [THIRD_PARTY_NOTICES.md](https://github.com/codemee/mathtran/blob/main/THIRD_PARTY_NOTICES.md) for third-party components; note that **PyMuPDF is AGPL-3.0**, which matters if you distribute a packaged build that includes it.
