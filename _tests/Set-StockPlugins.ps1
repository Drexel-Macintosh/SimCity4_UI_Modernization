# Paths are RESOLVED, not hard-coded: Documents may be redirected by
# OneDrive, and the repo may be cloned anywhere (task #108).
<#
  Set-StockPlugins.ps1 - pull EVERY visual-affecting plugin so the game runs
  as close to vanilla as this install allows, at a chosen resolution.

  This is BROADER than Set-StockCompare.ps1, which disables only OUR scaling
  layer. This one also stashes NAM, CAM/Maxis content folders, the null45 and
  memo DLL families, MoreBuildingStyles, thumbnail/texture fixes - anything
  that can change a pixel.

    .\Set-StockPlugins.ps1                     stash, 1024x768 windowed
    .\Set-StockPlugins.ps1 -Width 1280 -Height 1024
    .\Set-StockPlugins.ps1 -Restore            put everything back
    .\Set-StockPlugins.ps1 -Status             what is stashed right now

  NOTHING IS DELETED. Files are MOVED into
      Documents\SimCity 4\_stock-stash\
  with their relative paths preserved, and a manifest is written so -Restore
  is exact rather than a guess.

  ⛔ NOTE THE PATH: the stash is a sibling of Plugins, NOT a child of it.
     SC4 scans Plugins RECURSIVELY. A "stash" inside Plugins disables nothing.

  DELIBERATELY KEPT (say so out loud rather than silently leaving them):
    * SC4GraphicsOptions.dll/.ini - this IS the resolution lever. Without it
      there is no reliable way to force a windowed 1024x768 on this setup.
      It changes resolution/renderer only, no UI geometry and no art.
    * SC4TouchControls.dll/.ini - touch INPUT, not visuals, and on a touch
      table removing it can leave the game awkward to drive. Pass
      -IncludeTouch to stash it too.
    * dgVoodoo (DDraw.dll in the GAME INSTALL dir) is NOT touched at all.
      SC4 on Win11 generally needs it to start; removing it risks not
      launching rather than launching stock. It is a wrapper, not a mod.

  Log/backup files (*.log, *.bak*, *.csv, *.bin, *-backup, *.x1-disabled,
  *.compare-off) are left alone - the game does not load them.
#>
[CmdletBinding()]
param(
    [int]    $Width  = 1024,
    [int]    $Height = 768,
    [switch] $Restore,
    [switch] $Status,
    [switch] $IncludeTouch
)

$ErrorActionPreference = "Stop"

$DocPlugins  = (Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'SimCity 4\Plugins')
$InstallRoot = "C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe"
$InstPlugins = Join-Path $InstallRoot "Plugins"
# ⛔ THE STASH MUST LIVE OUTSIDE THE PLUGINS TREE. Fixed 2026-08-05 after this
#    script shipped with $Stash = "$DocPlugins\_stock-stash" - INSIDE Plugins.
#    SC4 scans Plugins RECURSIVELY, so every "stashed" .dat/.dll kept loading:
#    132 dats (98 MB) + 30 DLLs were live through an entire stock-baseline
#    investigation and through a fresh reinstall. Moving a plugin to a
#    SUBFOLDER of Plugins does not disable it - only an extension rename or a
#    move OUT of the tree does. Same failure class as the zzz- subfolder gap
#    (2026-08-02), one directory further out. Do not "tidy" this back inside.
$SC4Docs     = Split-Path $DocPlugins -Parent
$Stash       = Join-Path $SC4Docs "_stock-stash"
$Manifest    = Join-Path $Stash "MANIFEST.txt"
$GfxIni      = Join-Path $DocPlugins "SC4GraphicsOptions.ini"
$GfxBak      = Join-Path $Stash "SC4GraphicsOptions.ini.pre-stock"

# Files that must STAY so the game launches and the resolution can be set.
$KeepNames = @("SC4GraphicsOptions.dll", "SC4GraphicsOptions.ini")

# ============================================================================
# TOUCH QUARANTINE - USER ORDER, 2026-08-05. DO NOT SOFTEN THIS.
# SC4TouchControls does NOT go back into Plugins until it has been REBUILT to
# be 100% independent of the UI-scaling product (task #133). It is stashed
# OUTSIDE the Plugins tree, in
#     Documents\SimCity 4\_touch-QUARANTINE-do-not-reinstall\
# and removed from the manifest, so -Restore cannot bring it back. This list
# is the second lock: even a hand-edited manifest is refused by NAME.
# -IncludeTouch is deliberately NOT an escape hatch for this.
# ============================================================================
$Quarantined = @("SC4TouchControls.dll", "SC4TouchControls.ini")

function Assert-GameClosed {
    $p = Get-Process -Name "SimCity 4" -ErrorAction SilentlyContinue
    if ($p) {
        throw "SimCity 4 is running (pid $($p.Id)). Close it from the game's own menu - it holds these files open, and it runs ELEVATED so do not force-kill it."
    }
}

function Set-IniValue([string]$path, [string]$key, [string]$value) {
    if (-not (Test-Path $path)) { return }
    $lines = Get-Content $path
    $hit = $false
    $out = foreach ($l in $lines) {
        if ($l -match "^\s*$key\s*=") { $hit = $true; "$key=$value" } else { $l }
    }
    if (-not $hit) { $out += "$key=$value" }
    # utf8 WITHOUT BOM: the DLL abandons a BOM'd ini and boots windowed.
    [System.IO.File]::WriteAllLines($path, $out, (New-Object System.Text.UTF8Encoding($false)))
}

function Get-IniValue([string]$path, [string]$key) {
    if (-not (Test-Path $path)) { return "?" }
    foreach ($l in Get-Content $path) {
        if ($l -match "^\s*$key\s*=\s*(.*)$") { return $Matches[1].Trim() }
    }
    return "?"
}

# ---- STATUS ---------------------------------------------------------------
if ($Status) {
    if (Test-Path $Manifest) {
        $n = (Get-Content $Manifest | Where-Object { $_ -and $_ -notmatch '^#' }).Count
        Write-Output "STOCK-PLUGINS MODE ACTIVE - $n item(s) stashed."
        Write-Output "Stash: $Stash"
    } else {
        Write-Output "Not stashed (no manifest) - plugins are live."
    }
    Write-Output ("Resolution: {0}x{1} {2} / {3}" -f (Get-IniValue $GfxIni 'WindowWidth'),
        (Get-IniValue $GfxIni 'WindowHeight'), (Get-IniValue $GfxIni 'WindowMode'),
        (Get-IniValue $GfxIni 'Driver'))
    exit 0
}

# ---- RESTORE --------------------------------------------------------------
if ($Restore) {
    Assert-GameClosed
    if (-not (Test-Path $Manifest)) { Write-Output "Nothing to restore (no manifest)."; exit 0 }
    $restored = 0; $missing = 0
    foreach ($rel in (Get-Content $Manifest | Where-Object { $_ -and $_ -notmatch '^#' })) {
        $from = Join-Path $Stash $rel
        # rel is prefixed DOC\ or INST\ to say which tree it came from
        if ($rel -like "INST\*") {
            $to = Join-Path $InstPlugins ($rel -replace '^INST\\', '')
        } elseif ($rel -like "APPS\*") {
            $to = Join-Path (Join-Path $InstallRoot "Apps") ($rel -replace '^APPS\\', '')
        } elseif ($rel -like "ROOT\*") {
            $to = Join-Path $InstallRoot ($rel -replace '^ROOT\\', '')
        } else {
            $to = Join-Path $DocPlugins ($rel -replace '^DOC\\', '')
        }
        if ($Quarantined -contains (Split-Path $rel -Leaf)) {
            Write-Output ("  REFUSED (quarantined by user order): " + (Split-Path $rel -Leaf))
            continue
        }
        if (-not (Test-Path $from)) { $missing++; continue }
        $dir = Split-Path -Parent $to
        if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
        Move-Item $from $to -Force
        $restored++
    }
    if (Test-Path $GfxBak) {
        Copy-Item $GfxBak $GfxIni -Force
        Remove-Item $GfxBak -Force
        Write-Output "graphics settings restored."
    }
    Remove-Item $Manifest -Force
    Get-ChildItem $Stash -Recurse -Directory -ErrorAction SilentlyContinue |
        Sort-Object { $_.FullName.Length } -Descending |
        ForEach-Object { if (-not (Get-ChildItem $_.FullName -Force)) { Remove-Item $_.FullName -Force } }
    if ((Test-Path $Stash) -and -not (Get-ChildItem $Stash -Force)) { Remove-Item $Stash -Force }
    Write-Output "RESTORED $restored item(s)."
    if ($missing) { Write-Output "WARNING: $missing manifest entries were not in the stash." }
    exit 0
}

# ---- STASH ----------------------------------------------------------------
Assert-GameClosed
if (Test-Path $Manifest) { throw "Already stashed - run -Restore first (or -Status to see what)." }
New-Item -ItemType Directory -Path $Stash -Force | Out-Null

# Back up the graphics ini before we touch the resolution.
Copy-Item $GfxIni $GfxBak -Force

$rows = @()

# 1. Loose loadable files in the Documents Plugins ROOT.
#    The game loads .dat/.dll and reads FontStyle.ini directly; everything
#    else in the root is logs and backups it never opens.
Get-ChildItem $DocPlugins -File -ErrorAction SilentlyContinue | ForEach-Object {
    $n = $_.Name
    if ($KeepNames -contains $n) { return }
    # quarantined names are ALWAYS stashed, never kept
    $isLoadable = ($n -like "*.dll") -or ($n -like "*.dat") -or ($n -eq "FontStyle.ini")
    if (-not $isLoadable) { return }
    # already-gated copies are inert; leave them where they are
    if ($n -like "*.x1-disabled" -or $n -like "*.compare-off") { return }
    $rows += ,@("DOC\$n", $_.FullName, (Join-Path $Stash "DOC\$n"))
}

# 2. Content SUBFOLDERS (NAM, the numbered load-order folders, Maxis
#    Buildings, our zzz- overrides). Moved whole - these are pure content.
Get-ChildItem $DocPlugins -Directory -ErrorAction SilentlyContinue | ForEach-Object {
    $n = $_.Name
    if ($n -eq "_stock-stash") { return }
    if ($n -eq "_dllstash") { return }      # pre-existing, already inert
    $rows += ,@("DOC\$n", $_.FullName, (Join-Path $Stash "DOC\$n"))
}

# 3. The INSTALL-dir Plugins FontStyle.ini. The game probes
#    <install>\Plugins BEFORE Documents, so a stock font pass must move this
#    one too (learned the hard way - see the golden-backup memory).
$instFont = Join-Path $InstPlugins "FontStyle.ini"
if (Test-Path $instFont) {
    $rows += ,@("INST\FontStyle.ini", $instFont, (Join-Path $Stash "INST\FontStyle.ini"))
}

# 3b. AND THE INSTALL-ROOT FALLBACK. The probe order is
#         <install>\Plugins  ->  <install>  ->  the DBPF
#     and <install> is where the exe lives = Apps\. Our own font file's header
#     says "Deploy as: <install root>\FontStyle.ini ... Plugins\FontStyle.ini
#     would take priority", so moving only the Plugins copies promotes THIS one
#     and leaves stock mode running 2x fonts. Found 2026-08-05.
$appsDir = Join-Path $InstallRoot "Apps"
foreach ($cand in @((Join-Path $InstallRoot "FontStyle.ini"), (Join-Path $appsDir "FontStyle.ini"))) {
    if (Test-Path $cand) {
        $leaf = Split-Path $cand -Leaf
        $tag  = if ($cand -like "*\Apps\*") { "APPS" } else { "ROOT" }
        $rows += ,@("$tag\$leaf", $cand, (Join-Path $Stash "$tag\$leaf"))
    }
}

$manifestLines = @(
    "# Set-StockPlugins.ps1 manifest - $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')",
    "# One relative path per line. DOC\ = Documents Plugins, INST\ = install Plugins.",
    "# Restore with:  .\Set-StockPlugins.ps1 -Restore"
)

$moved = 0
foreach ($r in $rows) {
    $rel, $from, $to = $r
    $dir = Split-Path -Parent $to
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
    Move-Item $from $to -Force
    $manifestLines += $rel
    $moved++
}

[System.IO.File]::WriteAllLines($Manifest, $manifestLines, (New-Object System.Text.UTF8Encoding($false)))

# Windowed so the renderer honours the REQUESTED size instead of the panel's.
Set-IniValue $GfxIni "WindowWidth"  $Width
Set-IniValue $GfxIni "WindowHeight" $Height
Set-IniValue $GfxIni "WindowMode"   "Windowed"

Write-Output "STOCK-PLUGINS MODE: stashed $moved item(s); ${Width}x${Height} Windowed."
Write-Output "KEPT ON PURPOSE: SC4GraphicsOptions (the resolution lever)$(if (-not $IncludeTouch) { ' + SC4TouchControls (touch input, not visual)' })."
Write-Output "dgVoodoo in the game install dir is untouched - SC4 needs it to start."
Write-Output ""
Write-Output "Restore everything with:  .\Set-StockPlugins.ps1 -Restore"
