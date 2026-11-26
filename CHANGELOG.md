# Changelog / 更新紀錄

格式依循 [Keep a Changelog](https://keepachangelog.com/)；版本號採 [語意化版本](https://semver.org/lang/zh-TW/)。
Format follows [Keep a Changelog](https://keepachangelog.com/); versions follow [Semantic Versioning](https://semver.org/).

## [0.1.1] - 2026-11-26

修正 Windows 安裝包的啟動問題。 / Fixes the Windows package failing to start.

### 繁體中文

- **修正 Windows 安裝包一開啟就當掉**：用瀏覽器下載 ZIP 再解壓縮後，檔案會帶「來自網際網路」標記，.NET 因此拒絕載入 `Python.Runtime.dll`，出現 `Failed to resolve Python.Runtime.Loader.Initialize …`。安裝包現在附帶 `MathTran.exe.config` 允許載入這些元件
- 雲端發布流程新增「開視窗」煙霧測試：模擬瀏覽器下載的 ZIP（每個檔案帶標記）並實際開啟視窗，這類問題今後會在發布前被擋下
- macOS 安裝包從這個版本起只提供 Apple Silicon（arm64）；Intel Mac 請用 `uv tool install mathtran`
- 只影響 Windows 的 ZIP；用 `uv tool install mathtran` 安裝的人不受影響

### English

- **Fixed the Windows package crashing on launch**: files extracted from a browser-downloaded ZIP carry the "downloaded from the Internet" mark, so .NET refused to load `Python.Runtime.dll` (`Failed to resolve Python.Runtime.Loader.Initialize …`). The package now ships a `MathTran.exe.config` that allows loading these components
- The release workflow gains a windowed smoke test: it simulates a browser-downloaded ZIP (every file marked) and really opens the window, so this kind of problem is caught before publishing
- From this version the macOS package is Apple Silicon (arm64) only; on an Intel Mac use `uv tool install mathtran`
- Only the Windows ZIP was affected; installing with `uv tool install mathtran` was never affected

## [0.1.0] - 2026-11-26

第一個公開版本。 / First public release.

### 繁體中文

- **多張圖片一次處理**：貼上、加入檔案、加入資料夾、拖曳都可以；內容相同的圖片自動略過
- **辨識（Claude 視覺模型）**：可針對「選取的 / 勾選的 / 全部」辨識，批次時 3 張並行、可中途停止；圖上的**中文標題與說明文字**也會一併轉錄
- **辨識快取**：以圖片內容的 SHA-256 為鍵，辨識過的圖片不會重複呼叫 API；你手動修改的結果也會保留；介面內可查看與清除快取
- **預覽**：即時預覽（KaTeX，離線）與精準預覽（真 LaTeX 編譯）可來回切換；太長的公式會自動縮小到完整可見
- **匯出**：SVG / PDF / LaTeX（.tex）可複選；單張直接另存新檔，多個檔案則由你選資料夾（瀏覽器版下載 zip）
- **中文公式**：自動使用中文字型編譯
- **工具列**：語言（跟隨系統 / 繁體中文 / English）、配色（跟隨系統 / 淺色 / 深色）、API key；設定會被記住
- **配色**：淺色採鋼彈 RX-78-2、深色採新世紀福音戰士的配色（只借用配色，不含任何標誌）
- **三種使用方式**：桌面視窗、瀏覽器、命令列（`mathtran ocr / render / convert / cache / config / serve / gui`）
- **安裝方式**：Windows ZIP、macOS DMG（內附 Tectonic，不必另外安裝），或 `uv tool install mathtran`

### English

- **Work on many images at once**: paste, add files, add a folder, or drag and drop; identical images are skipped automatically
- **Recognition (Claude vision model)** for the selected / checked / all images, 3 in parallel with a Stop button; **Chinese titles and notes in the image** are transcribed too
- **Recognition cache** keyed by the SHA-256 of the image, so nothing is recognized twice; your manual edits are kept; the cache can be viewed and cleared in the UI
- **Preview**: switch back and forth between the live preview (KaTeX, offline) and the accurate preview (real LaTeX); long formulas shrink automatically so the whole formula stays visible
- **Export**: SVG / PDF / LaTeX (.tex), multi-select; one file goes through "Save as", several files go to a folder you choose (a zip in the browser version)
- **Chinese formulas** are compiled with a CJK font automatically
- **Toolbar**: language (follow system / Traditional Chinese / English), theme (follow system / light / dark) and API key; your choices are remembered
- **Themes**: light uses a Gundam RX-78-2 palette, dark an Evangelion palette (colors only, no logos)
- **Three ways to use it**: desktop window, browser, command line (`mathtran ocr / render / convert / cache / config / serve / gui`)
- **Installation**: Windows ZIP, macOS DMG (Tectonic included, nothing else to install), or `uv tool install mathtran`

[0.1.1]: https://github.com/codemee/mathtran/releases/tag/v0.1.1
[0.1.0]: https://github.com/codemee/mathtran/releases/tag/v0.1.0
