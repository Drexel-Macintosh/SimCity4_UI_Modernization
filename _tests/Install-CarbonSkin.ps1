# Install-CarbonSkin.ps1 - copy the PRUNED Scoty Carbon Skin 1.5 into live
# Plugins. The pruned set (12 dats whose target mods are installed, per the
# author's own delete-what-you-don't-have rule, + the PDF) is staged by the
# carbon analysis arc at tools\research\carbon\install-staged\.
#
#   powershell -ExecutionPolicy Bypass -File C:\dev\SC4UIScale\_tests\Install-CarbonSkin.ps1
#
# Safe to re-run (idempotent copy). Refuses while the game is running.
#
# ⚠ FOLDER NAME IS LOAD-BEARING AND DELIBERATELY NOT THE AUTHOR'S.
# The zip ships `z____scoty_mods`, but "z____" vs "zzz-SC4UIScale" is the
# ONE pair in this tree where candidate comparators disagree ('Z' 0x5A < '_'
# 0x5F upcased, '_' 0x5F < 'z' 0x7A lowercased) - under an upcasing
# comparator the skin would load AFTER our overrides and every ZCarbon
# package would be inert. `zz-scoty-mods` sorts before zzz-SC4UIScale under
# EVERY comparator (hyphen 0x2D < any letter in all foldings) and still
# after every mod folder it must beat. See REGRESSION.md 2026-08-25
# "THE COMPARATOR-AMBIGUOUS BOUNDARY".
#
# NOTE: installing the skin BEFORE the ZCarbon packages are deployed leaves
# the UI carbon-1x-in-scaled-cells on ~490 TGIs - install as part of the
# ZCarbon arc, not standalone (CARBON-COMPAT.md).

$ErrorActionPreference = "Stop"

if (Get-Process -Name "SimCity 4" -ErrorAction SilentlyContinue) {
    Write-Host "REFUSED: SimCity 4 is running. Close it first (never killed)." -ForegroundColor Red
    exit 1
}

$staged = "C:\dev\SC4UIScale\tools\research\carbon\install-staged\zz-scoty-mods"
$plug   = Join-Path ([Environment]::GetFolderPath("MyDocuments")) "SimCity 4\Plugins"
if (-not (Test-Path "$staged\z__Scoty_Carbon_Skin")) { Write-Host "REFUSED: staged folder missing at $staged" -ForegroundColor Red; exit 1 }
if (-not (Test-Path $plug)) { Write-Host "REFUSED: Plugins not found at $plug" -ForegroundColor Red; exit 1 }

# Migrate a legacy author-named install if one exists (the ambiguous name).
if (Test-Path "$plug\z____scoty_mods") {
    if (Test-Path "$plug\zz-scoty-mods") {
        Remove-Item "$plug\z____scoty_mods" -Recurse -Force
        Write-Host "removed legacy z____scoty_mods (zz-scoty-mods already present)"
    } else {
        Rename-Item "$plug\z____scoty_mods" "zz-scoty-mods"
        Write-Host "migrated legacy z____scoty_mods -> zz-scoty-mods (comparator-ambiguity fix)"
    }
}

Copy-Item $staged $plug -Recurse -Force

$dest = "$plug\zz-scoty-mods\z__Scoty_Carbon_Skin"
$files = Get-ChildItem $dest -File
Write-Host ("installed {0} files into {1}:" -f $files.Count, $dest)
$files | ForEach-Object { Write-Host ("  {0,-46} {1,9}" -f $_.Name, $_.Length) }

if ($files.Count -ne 13) {
    Write-Host "WARNING: expected 13 files (12 dats + PDF), got $($files.Count)" -ForegroundColor Yellow
}

# Load-order MEASUREMENT, not a constant compare: the skin folder must sort
# before zzz-SC4UIScale under EVERY candidate comparator the engine might
# use (raw ordinal, upcase ordinal, lowercase ordinal). Any divergence
# between the three on the LIVE folder set is itself a red flag.
$names = (Get-ChildItem $plug -Directory | Select-Object -ExpandProperty Name)
$orders = @{}
$orders["raw"]   = [string[]]($names | Sort-Object { $_ } )
$orders["upper"] = [string[]]($names | Sort-Object { $_.ToUpperInvariant() })
$orders["lower"] = [string[]]($names | Sort-Object { $_.ToLowerInvariant() })
$bad = $false
foreach ($k in $orders.Keys) {
    $o = $orders[$k]
    $i = [array]::IndexOf($o, "zz-scoty-mods")
    $z = [array]::IndexOf($o, "zzz-SC4UIScale")
    if ($i -lt 0 -or $z -lt 0 -or $i -ge $z) {
        Write-Host ("FAIL: comparator '{0}' orders the skin AFTER zzz-SC4UIScale: {1}" -f $k, ($o -join " | ")) -ForegroundColor Red
        $bad = $true
    }
}
if (-not $bad) {
    Write-Host "folder order OK under raw/upcase/lowercase comparators: zz-scoty-mods < zzz-SC4UIScale" -ForegroundColor Green
}
Write-Host "DONE. Do NOT launch the game until the ZCarbon packages are deployed." -ForegroundColor Cyan
