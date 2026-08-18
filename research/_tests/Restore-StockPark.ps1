# Paths are RESOLVED, not hard-coded: Documents may be redirected by
# OneDrive, and the repo may be cloned anywhere (task #108).
# Restore-StockPark.ps1 - undo the 2026-07-30 stock-reference capture setup.
# Reverses EXACTLY what was parked for the budget-dialog stock capture:
# scaler DLL + active 2x dats + zzz-SC4UIScale + both FontStyle.ini copies
# back into place, dgVoodoo DLLs re-enabled, SC4GraphicsOptions.ini back to
# DirectX 2400x1600 FullScreen. Run with the game CLOSED.
# Success check after next launch: SC4UIScale.log header shows the current
# version and "AutoScale: 2400x1600 -> tier 2.00 (scaling active)".

$doc  = (Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'SimCity 4\Plugins')
$inst = "C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe"
$park = (Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'SimCity 4\_stockpark')

if (Get-Process -Name "SimCity 4" -ErrorAction SilentlyContinue) {
    Write-Host "GAME RUNNING - close it first." -ForegroundColor Red; exit 1
}
if (-not (Test-Path $park)) {
    Write-Host "Park dir missing ($park) - nothing to restore?" -ForegroundColor Red; exit 1
}

Move-Item "$park\SC4UIScale.dll" "$doc\SC4UIScale.dll"
Move-Item "$park\z_SC4UIScale_DialogStatic-2x.dat" "$doc\z_SC4UIScale_DialogStatic-2x.dat"
Move-Item "$park\z_SC4UIScale_ItemIcons-2x.dat" "$doc\z_SC4UIScale_ItemIcons-2x.dat"
Move-Item "$park\z_SC4UIScale_SelectiveArt-2x.dat" "$doc\z_SC4UIScale_SelectiveArt-2x.dat"
Move-Item "$park\z_SC4UIScale_WebText.dat" "$doc\z_SC4UIScale_WebText.dat"
Move-Item "$park\FontStyle-Documents.ini" "$doc\FontStyle.ini"
Move-Item "$park\zzz-SC4UIScale" "$doc\zzz-SC4UIScale"
Move-Item "$park\FontStyle-Install.ini" "$inst\Plugins\FontStyle.ini"
Rename-Item "$inst\Apps\DDraw.dll.off" "DDraw.dll"
Rename-Item "$inst\Apps\D3DImm.dll.off" "D3DImm.dll"

# Graphics config back to the golden production values.
$ini = "$doc\SC4GraphicsOptions.ini"
(Get-Content $ini) `
    -replace '^Driver=Software$', 'Driver=DirectX' `
    -replace '^WindowWidth=1024$', 'WindowWidth=2400' `
    -replace '^WindowHeight=768$', 'WindowHeight=1600' `
    -replace '^WindowMode=Windowed$', 'WindowMode=FullScreen' |
    Set-Content $ini -Encoding ASCII

Remove-Item "$park\SC4GraphicsOptions.ini.stockcap-prev" -ErrorAction SilentlyContinue
if (-not (Get-ChildItem $park -ErrorAction SilentlyContinue)) { Remove-Item $park }

Write-Host "RESTORED. Launch and expect 'tier 2.00 (scaling active)' in SC4UIScale.log." -ForegroundColor Green
