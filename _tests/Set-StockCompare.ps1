# Paths are RESOLVED, not hard-coded: Documents may be redirected by
# OneDrive, and the repo may be cloned anywhere (task #108).
<#
  Set-StockCompare.ps1 - flip SC4 between STOCK (vanilla UI) and OURS (2x UI)
  for side-by-side comparison, WITHOUT touching dgVoodoo, the game exe, or
  SC4TouchControls.dll (hard rule: touch DLL is separate + shipped).

  STOCK mode disables ONLY our scaling layer, by renaming to .compare-off:
    Documents\Plugins : SC4UIScale.dll, every ACTIVE z_SC4UIScale_*.dat,
                        FontStyle.ini (the 2x font)
    <install>\Plugins : FontStyle.ini   <- the copy the game actually probes
                        (probe order: <install>\Plugins -> <install> -> DBPF)
  ...and sets a stock resolution in SC4GraphicsOptions.ini (Windowed, so the
  DirectX+dgVoodoo path renders at the REQUESTED size instead of panel-native).

  OURS mode restores every renamed file and the saved graphics settings.

  Usage:
    .\Set-StockCompare.ps1 -Mode Stock              # 1024x768 windowed, vanilla UI
    .\Set-StockCompare.ps1 -Mode Stock -Width 1280 -Height 1024
    .\Set-StockCompare.ps1 -Mode Ours               # back to 2400x1600 fullscreen, 2x UI
    .\Set-StockCompare.ps1 -Status                  # show what is currently active

  v4.5.0 - PRESENCE OF A .dat IS NO LONGER EVIDENCE OF SCALING.
  Through v4.4.0 the armed tier lived in the FILENAME (`<pkg>-2x.dat` live, the
  other tiers `.dat.x1-disabled`), so "a z_SC4UIScale_*.dat exists" really did
  mean some tier was armed, and -Status said "OURS (2x scaling active)". From
  v4.5.0 arming is a CONTENT SWAP at a stable filename (src\ScaleTier.cpp:
  ArmOne): `z_SC4UIScale_<Pkg>.dat` exists at EVERY tier, including tier 1, and
  including for a package the dependency gate has switched off - "off" is that
  same file holding the inert `.off` payload's bytes. So the old -Status line
  was doubly wrong under the new layout: "2x" was hard-coded, and "active" was
  inferred from a file that is now always there. The armed tier is read from
  `z_SC4UIScale_STATE.txt` instead, and when that file is absent -Status says
  UNKNOWN rather than guessing.

  THE STOCK CLAIM STILL HOLDS, and it holds for a reason worth writing down:
  this script renames SC4UIScale.dll aside too. If it did not, the DLL would
  boot, find every live .dat missing, and RECREATE all of them from their
  payloads - a "stock" run with the whole scaling layer restored underneath it.
  Assert-StockClean already refuses when the DLL is live; that check is now
  load-bearing for the dats as well, not just for the DLL's own patches.
#>
[CmdletBinding()]
param(
    [ValidateSet("Stock", "Ours")] [string] $Mode,
    [int] $Width  = 1024,
    [int] $Height = 768,
    [switch] $Status
)

$ErrorActionPreference = "Stop"

$DocPlugins  = (Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'SimCity 4\Plugins')
$InstallRoot = "C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe"
$InstPlugins = Join-Path $InstallRoot "Plugins"
$GfxIni      = Join-Path $DocPlugins "SC4GraphicsOptions.ini"
# v4.2.0 (subfolder move): our home inside Plugins.
$OurDir      = Join-Path $DocPlugins "010-SC4UIScale"
$StateFile   = Join-Path $OurDir "SC4UIScale.compare-state.txt"
$OffSuffix   = ".compare-off"

# EVERY directory this script may rename a file in. Both directions read this
# list, so they cannot drift apart again.
$TouchedDirs = @(
    $DocPlugins
    $OurDir
    (Join-Path $DocPlugins "zzz-SC4UIScale")
    $InstPlugins
    $InstallRoot
    (Join-Path $InstallRoot "Apps")
)

# Our scaling layer. NOTE: SC4TouchControls.dll is deliberately NOT here.
# Only files WITHOUT an existing gating suffix (.x1-disabled) are touched.
#
# v4.5.0: `.uipay` PAYLOADS ARE DELIBERATELY NOT TOUCHED, and that is not an
# oversight to tidy up later. A payload is inert BY EXTENSION - measured, not
# assumed: probe #202 copied a real DBPF to `.uipay`, booted, and it did not
# appear in the registered-segment census while 13 of our live `.dat` files
# did, so the census could have seen it and did not. Renaming them would make
# the -Mode Ours restore harder for no gain. The `*.dat` filters below already
# skip them, and Get-OurLiveArtifacts (the positive control) skips them for the
# same measured reason.
function Get-OurLiveFiles {
    $files = @()
    $files += Get-ChildItem -Path $DocPlugins -Filter "SC4UIScale.dll" -ErrorAction SilentlyContinue
    $files += Get-ChildItem -Path $OurDir -Filter "z_SC4UIScale_*.dat" -ErrorAction SilentlyContinue
    # legacy root copies (pre-4.2.0 layout) still come off if present:
    $files += Get-ChildItem -Path $DocPlugins -Filter "z_SC4UIScale_*.dat" -ErrorAction SilentlyContinue
    # zzz-SC4UIScale subfolder: our 2x copies of OTHER MODS' scripts
    # (ThirdPartyUI / CamUI / SaveWarningUI). These MUST come off in stock
    # mode too - found 2026-08-02 when the #58 stock capture would otherwise
    # have kept our 2x Building Styles script live under an otherwise 1x UI
    # (a Franken-capture of exactly the panel being measured). The .dat
    # filter already excludes .x1-disabled files, same as the root scan.
    $files += Get-ChildItem -Path (Join-Path $DocPlugins "zzz-SC4UIScale") -Filter "z_SC4UIScale_*.dat" -ErrorAction SilentlyContinue
    $files += Get-ChildItem -Path $OurDir -Filter "FontStyle.ini" -ErrorAction SilentlyContinue
    $files += Get-ChildItem -Path $DocPlugins -Filter "FontStyle.ini" -ErrorAction SilentlyContinue
    $files += Get-ChildItem -Path $InstPlugins -Filter "FontStyle.ini" -ErrorAction SilentlyContinue
    # 2026-08-05: THE THIRD COPY, and it was missing for months. Our own font
    # file's header says it plainly - "Deploy as: <install root>\FontStyle.ini
    # ... Plugins\FontStyle.ini would take priority". The game probes
    #     <install>\Plugins  ->  <install>  ->  the DBPF
    # so disabling only the two Plugins copies left OUR 2x table live as the
    # FALLBACK, and "stock" mode still had doubled fonts. <install> here means
    # where the exe lives = the Apps folder.
    $files += Get-ChildItem -Path $InstallRoot -Filter "FontStyle.ini" -ErrorAction SilentlyContinue
    $appsDir = Join-Path $InstallRoot "Apps"
    $files += Get-ChildItem -Path $appsDir -Filter "FontStyle.ini" -ErrorAction SilentlyContinue
    return $files
}

function Assert-GameClosed {
    $p = Get-Process -Name "SimCity 4" -ErrorAction SilentlyContinue
    if ($p) { throw "SimCity 4 is running (pid $($p.Id)). Close it first - files are locked while it runs." }
}

# #105/#107's law, learned AGAIN 2026-08-17: SC4UIScale.log is recreated on
# every launch, and a mode flip is usually followed by a launch - this is the
# last safe moment. The 40-thin THINBLT capture (#162's first real signal) was
# destroyed because the ad-hoc flip scripts lacked this step while the deploy
# script had it. Named by the log's OWN mtime, so it keeps its run's identity.
function Preserve-Log {
    $srcLog = Join-Path $DocPlugins "010-SC4UIScale\SC4UIScale.log"   # v4.4.0
    if (-not (Test-Path $srcLog)) { return }
    $capDir = Join-Path (Split-Path -Parent $PSScriptRoot) "_tests\captures"
    if (-not (Test-Path $capDir)) { New-Item -ItemType Directory $capDir | Out-Null }
    $stamp = (Get-Item $srcLog).LastWriteTime.ToString("yyyy-MM-dd-HHmmss")
    $dest = Join-Path $capDir ("SC4UIScale-{0}.log" -f $stamp)
    if (-not (Test-Path $dest)) {
        Copy-Item $srcLog $dest -Force
        Write-Output ("preserved previous run log -> {0}" -f (Split-Path $dest -Leaf))
    }
}

function Set-IniValue {
    param([string] $Path, [string] $Key, [string] $Value)
    $lines = Get-Content -Path $Path
    $hit = $false
    $out = foreach ($line in $lines) {
        if ($line -match "^\s*$([regex]::Escape($Key))\s*=") { $hit = $true; "$Key=$Value" } else { $line }
    }
    if (-not $hit) { throw "Key '$Key' not found in $Path" }
    # NO BOM. PowerShell 5.1's `Set-Content -Encoding utf8` writes a UTF-8 BOM;
    # SC4GraphicsOptions.dll then fails to parse the ini and the game silently
    # falls back to its own SimCity 4.cfg (this stranded the game at the stock
    # 1024x768 after a restore, 2026-07-28). Write UTF8-no-BOM explicitly.
    [System.IO.File]::WriteAllLines($Path, $out, (New-Object System.Text.UTF8Encoding($false)))
}

function Get-IniValue {
    param([string] $Path, [string] $Key)
    foreach ($line in (Get-Content -Path $Path)) {
        if ($line -match "^\s*$([regex]::Escape($Key))\s*=\s*(.*)$") { return $Matches[1].Trim() }
    }
    return $null
}

# POSITIVE CONTROL for a "stock" claim - a MEASUREMENT, not bookkeeping.
# RECURSIVE, because SC4 scans Plugins recursively at any depth: a copy of ours
# in a subfolder nobody remembered keeps loading, and a non-recursive listing
# is a probe that could not have seen it (2026-08-05: 132 dats "stashed" inside
# Plugins\ went on loading through an entire stock investigation AND a game
# reinstall, while the user said so repeatedly and was right every time).
# Also covers <install>\Plugins and the two loose-font probe sites, because the
# game's FontStyle order is <install>\Plugins -> <install> -> DBPF.
function Get-OurLiveArtifacts {
    $hits = @()
    foreach ($dir in @($DocPlugins, $InstPlugins)) {
        if (-not (Test-Path $dir)) { continue }
        $hits += Get-ChildItem -Path $dir -Recurse -File -ErrorAction SilentlyContinue |
            Where-Object {
                $_.Name -eq "SC4UIScale.dll" -or
                $_.Name -like "z_SC4UIScale_*.dat" -or
                $_.Name -eq "FontStyle.ini"
            }
    }
    foreach ($dir in @($InstallRoot, (Join-Path $InstallRoot "Apps"))) {
        if (-not (Test-Path $dir)) { continue }
        $hits += Get-ChildItem -Path $dir -File -Filter "FontStyle.ini" -ErrorAction SilentlyContinue
    }
    return $hits
}

# Called after -Mode Stock. A claim of "stock" that this refuses is a FALSE
# claim, and any capture taken under it is a Franken-capture - so it fails
# loudly rather than printing a warning nobody reads.
function Assert-StockClean {
    $live = @(Get-OurLiveArtifacts)
    if ($live.Count -eq 0) {
        Write-Host "STOCK VERIFIED: recursive scan of both Plugins trees + the two"
        Write-Host "  loose-font probe sites found 0 live SC4UIScale artifacts."
        # Named so nobody reads the leftover payloads as a hole in the claim,
        # and nobody 'fixes' it by renaming them (which -Mode Ours would then
        # have to undo). Inert by EXTENSION, measured by probe #202.
        $pay = @(Get-ChildItem -Path $DocPlugins -Recurse -File -Filter 'z_SC4UIScale_*.uipay' -ErrorAction SilentlyContinue)
        if ($pay.Count) {
            Write-Host ("  ({0} .uipay payload(s) left in place on purpose - inert by extension," -f $pay.Count)
            Write-Host "   measured by probe #202, and the DLL that would arm them is disabled.)"
        }
        return
    }
    Write-Host ""
    Write-Host "!! NOT STOCK. $($live.Count) of our artifact(s) are STILL LIVE:"
    $live | ForEach-Object { Write-Host "     $($_.FullName)" }
    Write-Host ""
    throw ("Refusing to report STOCK. SC4 loads Plugins recursively, so these " +
           "would load and any comparison taken now would be a Franken-capture. " +
           "Disable them (rename the extension or move them OUT of the Plugins " +
           "tree - a subfolder disables nothing) and re-run.")
}

# ---- WHAT IS ACTUALLY ARMED --------------------------------------------------
# The one question a directory listing can no longer answer. Reads the DLL's own
# per-folder record (ScaleTier.cpp: WriteArmState), whose format is two `#`
# header lines then TSV:
#   base <TAB> tag <TAB> reason <TAB> paySize <TAB> payTime <TAB> liveSize <TAB> liveTime
# `tag` is the armed payload tag (15x/2x/3x/1x/on) or `off`.
function Read-ArmState {
    $rows = @()
    foreach ($d in @($DocPlugins, $OurDir, (Join-Path $DocPlugins "zzz-SC4UIScale"))) {
        $s = Join-Path $d 'z_SC4UIScale_STATE.txt'
        if (-not (Test-Path -LiteralPath $s)) { continue }
        foreach ($line in (Get-Content -LiteralPath $s)) {
            if (-not $line -or $line -match '^\s*#') { continue }
            $c = $line -split "`t"
            if ($c.Count -lt 3) { continue }
            $rows += [pscustomobject]@{ Base = $c[0]; Tag = $c[1]; Reason = $c[2]; Dir = $d }
        }
    }
    return $rows
}

# ⛔ NEVER PRINT A TIER THIS FUNCTION DID NOT READ SOMEWHERE. The line it
# replaces said "OURS (2x scaling active)" from the mere presence of a .dat -
# hard-coded at 2x (wrong for anyone on 1.5x or 3x) and, since v4.5.0, wrong
# about "active" too: the live file exists at tier 1 and for every gated-off
# package as well. Both errors point the same way, towards "looks fine".
function Get-ArmedSummary {
    $rows = @(Read-ArmState)
    if ($rows.Count) {
        $armed = @($rows | Where-Object { $_.Tag -ne 'off' })
        $tags  = @($armed | ForEach-Object { $_.Tag } | Sort-Object -Unique)
        if (-not $armed.Count) {
            return ("installed but INERT - all {0} package(s) hold .off content (stock tier, or every gate closed). Read from z_SC4UIScale_STATE.txt." -f $rows.Count)
        }
        if ($tags.Count -eq 1) {
            return ("scaling ACTIVE at tier '{0}' - {1} of {2} package(s) armed. Read from z_SC4UIScale_STATE.txt." -f $tags[0], $armed.Count, $rows.Count)
        }
        return ("INCOHERENT - armed packages disagree on the tier ({0}). Two tiers cannot both be right; check z_SC4UIScale_STATE.txt." -f ($tags -join ', '))
    }
    # Pre-4.5.0 tree: the filename still carries the tier, so read it there and
    # SAY that is where it came from.
    $legacy = @()
    foreach ($d in @($DocPlugins, $OurDir, (Join-Path $DocPlugins "zzz-SC4UIScale"))) {
        if (-not (Test-Path $d)) { continue }
        $legacy += @(Get-ChildItem -Path $d -File -Filter "z_SC4UIScale_*.dat" -ErrorAction SilentlyContinue |
                     Where-Object { $_.BaseName -match '-(15x|2x|3x|4x|1x)$' })
    }
    if ($legacy.Count) {
        $t = @($legacy | ForEach-Object { ($_.BaseName -replace '^.*-(15x|2x|3x|4x|1x)$', '$1') } | Sort-Object -Unique)
        return ("scaling active at tier(s) {0} - read from the PRE-4.5.0 tier-tagged filenames ({1} file(s)); this tree has not been converted to the payload layout." -f ($t -join ', '), $legacy.Count)
    }
    return ("ARMED TIER UNKNOWN - no z_SC4UIScale_STATE.txt and no tier-tagged filenames. " +
            "Under the v4.5.0 content swap the live filename is a CONSTANT, so the files " +
            "below prove INSTALLATION and nothing about what is armed. Launch the game " +
            "once (the DLL rewrites that file every boot) and re-run -Status.")
}

function Show-Status {
    $off = @(Get-ChildItem -Path $DocPlugins -Filter "*$OffSuffix" -ErrorAction SilentlyContinue)
    $off += @(Get-ChildItem -Path $OurDir -Filter "*$OffSuffix" -ErrorAction SilentlyContinue)
    $off += @(Get-ChildItem -Path $InstPlugins -Filter "*$OffSuffix" -ErrorAction SilentlyContinue)
    $off += @(Get-ChildItem -Path (Join-Path $DocPlugins "zzz-SC4UIScale") -Filter "*$OffSuffix" -ErrorAction SilentlyContinue)
    # MEASURED, not inferred from how many files this script renamed. Those
    # two answers disagreed for months in the sibling script, and the renamed
    # count is the one that cannot see a copy it never knew about.
    $live = @(Get-OurLiveArtifacts)
    $mode = if ($live.Count -eq 0) { "STOCK (verified: 0 live artifacts)" }
            elseif ($off.Count -gt 0) { "MIXED - $($live.Count) still live, see below" }
            else { "OURS - " + (Get-ArmedSummary) }
    Write-Host "Mode      : $mode"
    if ($live.Count -gt 0 -and $off.Count -gt 0) {
        $live | ForEach-Object { Write-Host "    STILL LIVE: $($_.FullName)" }
    }
    Write-Host "Resolution: $(Get-IniValue $GfxIni 'WindowWidth')x$(Get-IniValue $GfxIni 'WindowHeight') $(Get-IniValue $GfxIni 'WindowMode') / $(Get-IniValue $GfxIni 'Driver')"
    if ($off.Count -gt 0) {
        Write-Host "Disabled  : $($off.Count) file(s)"
        $off | ForEach-Object { Write-Host "            $($_.Name)" }
    }
}

if ($Status -or -not $Mode) { Show-Status; return }

Assert-GameClosed
Preserve-Log

if ($Mode -eq "Stock") {
    # Save what we are leaving, so -Mode Ours restores it exactly.
    if (-not (Test-Path $StateFile)) {
        @(
            "WindowWidth=$(Get-IniValue $GfxIni 'WindowWidth')"
            "WindowHeight=$(Get-IniValue $GfxIni 'WindowHeight')"
            "WindowMode=$(Get-IniValue $GfxIni 'WindowMode')"
        ) | Set-Content -Path $StateFile -Encoding utf8
    }

    $n = 0
    foreach ($f in Get-OurLiveFiles) {
        Rename-Item -Path $f.FullName -NewName ($f.Name + $OffSuffix) -Force
        $n++
    }
    # Windowed so DirectX renders at the REQUESTED size (fullscreen+dgVoodoo
    # renders panel-native and ignores sub-native requests).
    Set-IniValue $GfxIni "WindowWidth"  $Width
    Set-IniValue $GfxIni "WindowHeight" $Height
    Set-IniValue $GfxIni "WindowMode"   "Windowed"

    Write-Host "STOCK MODE: disabled $n of our files; ${Width}x${Height} requested."
    Write-Host "dgVoodoo + SC4TouchControls untouched."
    # ⛔ THIS SCRIPT CANNOT DELIVER "Windowed" ON ITS OWN, and it used to SAY
    # Windowed anyway. WindowMode in SC4GraphicsOptions.ini is overridden by the
    # dgVoodoo wrapper: with FullScreenMode=true the game comes up borderless
    # fullscreen at panel size, so the requested WxH is not what renders and
    # there is no title bar to drag. Deliberately still not touching the
    # wrapper (that is this script's stated contract) - but a banner that
    # claims a mode it did not set is worse than no banner, so REPORT it.
    $dgConf = Join-Path $InstallRoot "Apps\dgVoodoo.conf"
    if (Test-Path $dgConf) {
        $dgTxt = Get-Content $dgConf -Raw
        $fsm = [regex]::Match($dgTxt, '(?mi)^\s*FullScreenMode\s*=\s*(\S+)')
        $cap = [regex]::Match($dgTxt, '(?mi)^\s*CaptureMouse\s*=\s*(\S+)')
        if ($fsm.Success -and $fsm.Groups[1].Value -match 'true') {
            Write-Host ""
            Write-Host "  WARNING: dgVoodoo.conf has FullScreenMode=true, which OVERRIDES" -ForegroundColor Yellow
            Write-Host "  WindowMode=Windowed. The game will come up borderless-fullscreen at" -ForegroundColor Yellow
            Write-Host "  panel size, NOT ${Width}x${Height}, so this is not a valid stock-resolution" -ForegroundColor Yellow
            Write-Host "  reference. For a real window set BOTH in $dgConf :" -ForegroundColor Yellow
            Write-Host "      FullScreenMode = false" -ForegroundColor Yellow
            Write-Host "      CaptureMouse   = false   (true traps the cursor off the title bar)" -ForegroundColor Yellow
            Write-Host "  Write it WITHOUT a BOM, and back it up - dgVoodooCpl.exe rewrites it." -ForegroundColor Yellow
        } elseif ($fsm.Success) {
            $capNote = if ($cap.Success -and $cap.Groups[1].Value -match 'true') { " (CaptureMouse=true - cursor is trapped)" } else { "" }
            Write-Host "  dgVoodoo FullScreenMode=false - a real window WILL appear.$capNote"
        }
    }
    Assert-StockClean
    Write-Host "Launch and compare."
    Write-Host "Restore with:  .\Set-StockCompare.ps1 -Mode Ours"
}
else {
    $n = 0
    foreach ($dir in $TouchedDirs) {
        if (-not (Test-Path $dir)) { continue }
        Get-ChildItem -Path $dir -Filter "*$OffSuffix" -ErrorAction SilentlyContinue | ForEach-Object {
            $orig = $_.Name.Substring(0, $_.Name.Length - $OffSuffix.Length)
            Move-Item -Path $_.FullName -Destination (Join-Path $dir $orig) -Force
            $n++
        }
    }
    if (Test-Path $StateFile) {
        foreach ($line in (Get-Content $StateFile)) {
            if ($line -match "^(\w+)=(.*)$") { Set-IniValue $GfxIni $Matches[1] $Matches[2] }
        }
        Remove-Item $StateFile -Force
    }
    Write-Host "OURS MODE: restored $n file(s) + saved graphics settings."
    Write-Host "Check the 'AutoScale: ... -> tier' line in SC4UIScale.log on next boot -
the tier follows the RESTORED resolution, so it is 3.00 at 3840x2160.
(This line used to hard-code 'tier 2.00' and was wrong for anyone not
running the 2x tier.)"
}

Write-Host ""
Show-Status
