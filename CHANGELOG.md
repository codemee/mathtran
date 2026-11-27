# Changelog / 更新紀錄

格式依循 [Keep a Changelog](https://keepachangelog.com/)；版本號採 [語意化版本](https://semver.org/lang/zh-TW/)。
Format follows [Keep a Changelog](https://keepachangelog.com/); versions follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1.7] - 2026-11-28

命令列的一輪補強：版本、`.tex` 輸出、批次處理。 / Command-line upgrades: version, `.tex` output and batch jobs.

### 繁體中文

- 命令列新增 **`mathtran --version`**（`-V`）
- `render`、`convert` 可以輸出 **`.tex`**（完整、可自行編譯的文件），`-o` 可重複，一次輸出多種格式
- **批次處理**：`ocr` 與 `convert` 可以一次給多張圖片或整個資料夾（`-r` 含子資料夾）；`convert` 輸出到資料夾並用 `-f` 選格式（`svg` / `pdf` / `tex`，可重複）；`-j` 設定同時辨識的張數（預設 3）；`ocr --json` 輸出 JSON；個別失敗不會中斷整批，沒有 API key 時立刻停止

### English

- The command line gets **`mathtran --version`** (`-V`)
- `render` and `convert` can write **`.tex`** (a complete, self-compilable document), and `-o` can be repeated to write several formats at once
- **Batch jobs**: `ocr` and `convert` accept several images or a whole folder (`-r` includes subfolders); `convert` writes to a folder and `-f` picks the formats (`svg` / `pdf` / `tex`, repeatable); `-j` sets how many are recognized at once (default 3); `ocr --json` prints JSON; one failure does not stop the batch, and a missing API key stops it at once

## [0.1.6] - 2026-11-27

配色調整：淺色多了黃色點綴，深色的初始畫面也有 EVA 的主要配色。 / Theme polish: the light theme gets yellow accents, and the dark theme's first screen shows Evangelion's main colors.

### 繁體中文

- 淺色配色（鋼彈 RX-78-2）**增加黃色點綴**：只用在步驟編號的圓圈（黃底藍字）；全部是純色平面，沒有立體效果
- 深色配色（福音戰士）的初始畫面**多了初號機的配色**：步驟編號的圓圈改成螢光綠底深色字、鑰匙上「尚未設定」的提醒點改成橘色，不再只有紫色
- 還沒有圖片時，原圖區改用背景色，不再是一塊突兀的白色（深色配色下特別明顯）
- 縮圖大小滑桿的進度與手把改用主題的主色（淺色＝鋼彈藍、深色＝EVA 紫），不再是瀏覽器預設的藍色

### English

- The light theme (Gundam RX-78-2) gets **yellow accents**: used only for the step-number circles (blue on yellow); everything stays flat, with no 3D effects
- The dark theme (Evangelion) shows **more of Unit-01's colors on the first screen**: the step-number circles are now neon green with dark digits and the "not set yet" dot on the key is orange, instead of purple only
- With no image yet, the original-image area uses the background color instead of a stark white block (most noticeable in the dark theme)
- The thumbnail-size slider's progress and handle now use the theme's main color (Gundam blue in the light theme, EVA purple in the dark one) instead of the browser's default blue

## [0.1.5] - 2026-11-27

圖形編輯器的一輪修正，並可以選擇辨識用的模型。 / A round of visual-editor fixes, and you can now choose the recognition model.

### 繁體中文

- **可以選擇辨識用的模型**：API key 對話框新增「辨識用的模型」下拉選單（Haiku 5.5 / Sonnet 5.5（預設）/ Opus 5.5 / Fable 5.2，或自訂模型 ID）；命令列新增 `mathtran config --model`；環境變數 `MATHTRAN_MODEL` 仍優先（對話框會鎖住並說明）
- 狀態列右側顯示**目前辨識用的模型**（例如 `模型：claude-sonnet-5-5`），更換模型後立即更新
- 修正桌面版圖形編輯器**無法用滑鼠點選位置**的問題（可以點公式移動游標、拖曳選取）：桌面視窗預設禁止選取文字，圖形編輯器因此不處理滑鼠；0.1.3、0.1.4 都有這個問題
- 圖形編輯器的長公式**不再折行**，改成顯示**水平捲軸**：折行後的公式很難辨識，含分數、根號的公式折行後上下兩行還會疊在一起（0.1.3、0.1.4 的問題）
- 修正圖形編輯器新增列 / 欄後，LaTeX 裡多出 `\placeholder{}`（預覽會壞、也無法編譯），而且原本的換行全部消失的問題：現在空的儲存格會清成空白（圖形編輯器裡也不再畫 ▢ 方框，與切換模式後重新載入的外觀一致；游標所在的空格仍會反白），並在每個 `\\`、`\begin{…}`、`\end{…}` 後面補回換行
- 圖形編輯器的選單、虛擬鍵盤與提示**跟著介面語言**（繁體中文 / English）；MathLive 內建的繁中翻譯缺的「插入」子選單等項目已補上
- 主視窗**不再整頁捲動**：左右兩個窗格各自使用捲軸（右邊內容多時用自己的捲軸），狀態列固定在底部；視窗很窄、上下堆疊時才整頁捲動

### English

- **Choose the recognition model**: the API key dialog gets a "Recognition model" drop-down (Haiku 5.5 / Sonnet 5.5 (default) / Opus 5.5 / Fable 5.2, or a custom model ID); new `mathtran config --model`; the `MATHTRAN_MODEL` environment variable still takes priority (the dialog locks and says why)
- The right side of the status bar shows the **model currently used for recognition** (for example `Model: claude-sonnet-5-5`) and updates as soon as you change it
- Fixed the desktop visual editor **not reacting to mouse clicks** (click to place the caret, drag to select): the desktop window disables text selection by default, so the editor ignored the mouse; present in 0.1.3 and 0.1.4
- Long formulas in the visual editor are **no longer wrapped**; the field shows a **horizontal scrollbar** instead: a wrapped formula is hard to read, and with fractions and roots the wrapped lines even overlapped (an issue in 0.1.3 and 0.1.4)
- Fixed the visual editor leaving `\placeholder{}` in the LaTeX after adding a row / column (which broke the preview and compilation) and flattening all line breaks: empty cells are now cleaned to blanks (and no longer drawn as ▢ boxes in the visual editor, matching how they look after switching modes; the cell under the caret is still highlighted) and a line break is restored after every `\\`, `\begin{…}` and `\end{…}`
- The visual editor's menu, virtual keyboard and tooltips **follow the interface language** (Traditional Chinese / English); the `Insert` submenu and a few other items missing from MathLive's built-in zh-TW strings are filled in
- The main window **no longer scrolls as a whole**: the left and right panes each use their own scrollbar (the right one scrolls by itself when its content is long) and the status bar stays at the bottom; only a very narrow window, where the panes stack, scrolls as a page

## [0.1.4] - 2026-11-26

### 繁體中文

- 辨識與匯出的「選取的」按鈕改名為「**目前檢視**」（English：Current），避免和「勾選的」混淆；提示文字、確認訊息與文件一併更新

### English

- The "Selected" scope button for recognition and export is renamed "**Current**" (繁中：目前檢視) so it can't be confused with "Checked"; hints, confirmations and docs updated

## [0.1.3] - 2026-11-26

### 繁體中文

- 新增**圖形化編輯器**：編輯區上方的「LaTeX 文字 / 圖形編輯」切換鈕，按「圖形編輯」可直接在公式上點選、輸入，或用虛擬鍵盤插入分數、根號、積分等；長公式會自動換行；與 LaTeX 文字框同步，完全離線（內建 MathLive，第一次按下時才載入）
- LaTeX 編輯區新增**語法標色**：指令、大括號、上下標、數字、`\text{}` 內的文字與註解各有顏色（淺色 / 深色配色都有對應）；游標在括號旁時成對的括號會反白，沒有配對的括號會畫紅色波浪底線

### English

- New **visual editor**: use the "LaTeX text / Visual editor" switch above the editor, and "Visual editor" lets you click and type right on the formula, or insert fractions, roots and integrals from a virtual keyboard; long formulas wrap onto the next line; it stays in sync with the LaTeX text box and works fully offline (MathLive is bundled and loaded on first use)
- The LaTeX editor now has **syntax highlighting**: commands, braces, super/subscripts, numbers, text inside `\text{}` and comments each get a color (for both light and dark themes); the matching brace is highlighted next to the caret and unmatched braces get a red wavy underline

## [0.1.2] - 2026-11-26

### 繁體中文

- 視窗標題列顯示版本號（例如 `MathTran 0.1.1`）；瀏覽器版的分頁標題與 `/api/health` 也有版本號
- 程式圖示改為「瘦窄的白色文件（右上角有摺角）上壓一條紅色橫向長條，長條裡是白色粗體 f(x)」（像 PDF 圖示）；紅色長條是純色、沒有白邊，夠高，f(x) 可以放得很大，小尺寸也看得清楚；白色文件當底，在深色工作列上也清楚，淡灰藍的邊線讓它在白色背景上也有輪廓

### English

- The window title bar now shows the version (for example `MathTran 0.1.1`); the browser tab title and `/api/health` carry it too
- The app icon is now a slim white document with a folded corner, with a red horizontal bar across it (like a PDF icon) that holds a bold white f(x); the bar is solid red with no white border and tall enough for a large f(x) that stays readable at small sizes; the white page keeps it clear on dark taskbars, and a pale grey-blue edge gives it an outline on white backgrounds

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
- **辨識（Claude 視覺模型）**：可針對「目前檢視 / 勾選的 / 全部」辨識，批次時 3 張並行、可中途停止；圖上的**中文標題與說明文字**也會一併轉錄
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
- **Recognition (Claude vision model)** for the current / checked / all images, 3 in parallel with a Stop button; **Chinese titles and notes in the image** are transcribed too
- **Recognition cache** keyed by the SHA-256 of the image, so nothing is recognized twice; your manual edits are kept; the cache can be viewed and cleared in the UI
- **Preview**: switch back and forth between the live preview (KaTeX, offline) and the accurate preview (real LaTeX); long formulas shrink automatically so the whole formula stays visible
- **Export**: SVG / PDF / LaTeX (.tex), multi-select; one file goes through "Save as", several files go to a folder you choose (a zip in the browser version)
- **Chinese formulas** are compiled with a CJK font automatically
- **Toolbar**: language (follow system / Traditional Chinese / English), theme (follow system / light / dark) and API key; your choices are remembered
- **Themes**: light uses a Gundam RX-78-2 palette, dark an Evangelion palette (colors only, no logos)
- **Three ways to use it**: desktop window, browser, command line (`mathtran ocr / render / convert / cache / config / serve / gui`)
- **Installation**: Windows ZIP, macOS DMG (Tectonic included, nothing else to install), or `uv tool install mathtran`

[0.1.7]: https://github.com/codemee/mathtran/releases/tag/v0.1.7
[0.1.6]: https://github.com/codemee/mathtran/releases/tag/v0.1.6
[0.1.5]: https://github.com/codemee/mathtran/releases/tag/v0.1.5
[0.1.4]: https://github.com/codemee/mathtran/releases/tag/v0.1.4
[0.1.3]: https://github.com/codemee/mathtran/releases/tag/v0.1.3
[0.1.2]: https://github.com/codemee/mathtran/releases/tag/v0.1.2
[0.1.1]: https://github.com/codemee/mathtran/releases/tag/v0.1.1
[0.1.0]: https://github.com/codemee/mathtran/releases/tag/v0.1.0
