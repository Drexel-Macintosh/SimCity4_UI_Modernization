# Install-CarbonSkin.ps1 - copy the PRUNED Scoty Carbon Skin 1.5 into live
# Plugins. The pruned set (10 dats whose target mods are installed, per the
# author's own delete-what-you-don't-have rule) is staged by the carbon
# analysis arc at tools\research\carbon\install-staged\.
#
#   powershell -ExecutionPolicy Bypass -File C:\dev\SC4UIScale\_tests\Install-CarbonSkin.ps1
#
# Safe to re-run (idempotent copy). Refuses while the game is running.
# NOTE: installing the skin BEFORE the ZCarbon packages are deployed leaves
# the UI carbon-1x-in-scaled-cells on 473 TGIs - install as part of the
# ZCarbon implementation arc, not standalone (CARBON-COMPAT.md).

$ErrorActionPreference = "Stop"

if (Get-Process -Name "SimCity 4" -ErrorAction SilentlyContinue) {
    Write-Host "REFUSED: SimCity 4 is running. Close it first (never killed)." -ForegroundColor Red
    exit 1
}

$staged = "C:\dev\SC4UIScale\tools\research\carbon\install-staged\z____scoty_mods"
$plug   = Join-Path ([Environment]::GetFolderPath("MyDocuments")) "SimCity 4\Plugins"
if (-not (Test-Path "$staged\z__Scoty_Carbon_Skin")) { Write-Host "REFUSED: staged folder missing at $staged" -ForegroundColor Red; exit 1 }
if (-not (Test-Path $plug)) { Write-Host "REFUSED: Plugins not found at $plug" -ForegroundColor Red; exit 1 }

Copy-Item $staged $plug -Recurse -Force

$dest = "$plug\z____scoty_mods\z__Scoty_Carbon_Skin"
$files = Get-ChildItem $dest -File
Write-Host ("installed {0} files into {1}:" -f $files.Count, $dest)
$files | ForEach-Object { Write-Host ("  {0,-46} {1,9}" -f $_.Name, $_.Length) }

if ($files.Count -ne 13) {
    Write-Host "WARNING: expected 13 files (12 dats + PDF), got $($files.Count)" -ForegroundColor Yellow
}

# Load-order sanity: the skin folder must sort AFTER the mod folders it
# redeclares (050-/150-/770-) and BEFORE zzz-SC4UIScale.
$names = Get-ChildItem $plug -Directory | Sort-Object Name | Select-Object -ExpandProperty Name
$i = [array]::IndexOf($names, "z____scoty_mods")
$z = [array]::IndexOf($names, "zzz-SC4UIScale")
if ($i -lt 0 -or $z -lt 0 -or $i -ge $z) {
    Write-Host "WARNING: folder order unexpected: $($names -join ' | ')" -ForegroundColor Yellow
} else {
    Write-Host ("folder order OK: ...{0} < zzz-SC4UIScale" -f $names[$i]) -ForegroundColor Green
}
Write-Host "DONE. Do NOT launch the game until the ZCarbon packages are deployed." -ForegroundColor Cyan
