<#
.SYNOPSIS
  Windows 安裝包的「開視窗」煙霧測試：模擬使用者「用瀏覽器下載 ZIP → 解壓縮 → 雙擊」。

.DESCRIPTION
  自我檢查（MATHTRAN_SELFTEST）不會開視窗，所以抓不到「視窗那一層」的問題。
  這個腳本會：
    1. 把 ZIP 解壓縮到暫存資料夾
    2. 替每個檔案加上「來自網際網路」標記（Zone.Identifier，ZoneId=3），就像瀏覽器下載的 ZIP 被檔案總管解壓縮
    3. 直接啟動 MathTran.exe（CreateProcess；不經過 shell，才不會跳出「無法驗證發行者」的對話框而卡住）
    4. 等視窗標題變成 "MathTran"；如果出現 "Unhandled exception" 之類的錯誤視窗、程式提早結束、或逾時，就失敗
  結束代碼：0 = 視窗正常開啟，1 = 失敗。

.EXAMPLE
  pwsh packaging/smoke_window.ps1 -Zip dist\MathTran-0.1.0-windows-x64.zip
  pwsh packaging/smoke_window.ps1 -Zip dist\MathTran-0.1.0-windows-x64.zip -NoMotw   # 對照組：不加標記
#>
param(
  [Parameter(Mandatory = $true)][string]$Zip,
  [switch]$NoMotw,
  [int]$TimeoutSeconds = 60
)
$ErrorActionPreference = "Stop"

$dir = Join-Path ([System.IO.Path]::GetTempPath()) ("mathtran-smoke-" + [guid]::NewGuid().ToString("N").Substring(0, 8))
Expand-Archive -Path $Zip -DestinationPath $dir
$exe = Join-Path $dir "MathTran\MathTran.exe"
if (-not (Test-Path $exe)) { Write-Host "找不到 $exe"; exit 1 }

if (-not $NoMotw) {
  Get-ChildItem $dir -Recurse -File | ForEach-Object {
    Set-Content -Path $_.FullName -Stream Zone.Identifier -Value "[ZoneTransfer]`r`nZoneId=3"
  }
}
$marked = (Get-ChildItem $dir -Recurse -File | Where-Object { Get-Item $_.FullName -Stream Zone.Identifier -ErrorAction SilentlyContinue }).Count
Write-Host "解壓縮到 $dir；帶 Mark of the Web 的檔案：$marked 個"

$psi = New-Object System.Diagnostics.ProcessStartInfo $exe
$psi.UseShellExecute = $false
$psi.WorkingDirectory = Split-Path $exe
$proc = [System.Diagnostics.Process]::Start($psi)

$ok = $false; $title = ""
for ($i = 0; $i -lt $TimeoutSeconds; $i++) {
  Start-Sleep -Seconds 1
  $proc.Refresh()
  if ($proc.HasExited) { Write-Host "程式提早結束，結束代碼 $($proc.ExitCode)"; break }
  $title = $proc.MainWindowTitle
  if ($title -eq "MathTran") { $ok = $true; break }
  if ($title -match "Unhandled|exception|Error") { break }
}
Write-Host "視窗標題：'$title'  已結束：$($proc.HasExited)"
if (-not $proc.HasExited) {
  # 視窗出現後再多等幾秒，確認沒有隨後跳出錯誤視窗（錯誤視窗屬於同一個行程，標題會被換掉）
  if ($ok) { Start-Sleep -Seconds 5; $proc.Refresh(); $title = $proc.MainWindowTitle; if ($title -ne "MathTran") { $ok = $false; Write-Host "視窗標題後來變成 '$title'" } }
  Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
}
Remove-Item $dir -Recurse -Force -ErrorAction SilentlyContinue
if ($ok) { Write-Host "OK：視窗正常開啟"; exit 0 } else { Write-Host "FAIL：視窗沒有正常開啟"; exit 1 }
