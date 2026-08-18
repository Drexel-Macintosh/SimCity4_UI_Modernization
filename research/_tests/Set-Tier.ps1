# Set-Tier.ps1 - force a specific scale tier for an eyes-on test, DATA AND ALL.
#
# ⛔ WHY THIS EXISTS. To test a tier by hand the obvious move is to set
# AutoScale=0 and ScaleFactor=1.5 in the ini. THAT DOES NOT WORK, and it fails
# in the most misleading way available:
#
#     AutoScale off: manual ScaleFactor 1.50, layers untouched.
#
# "layers untouched" means the DLL scales the WINDOW GEOMETRY to 1.5x and
# leaves the 2x art packages and the 2x FontStyle in place. You get 2x artwork
# inside 1.5x boxes - every panel crushed, text overlapping, boxes clipped -
# and it looks exactly like a catastrophic tier bug. It is not. It is the test
# rig. (2026-08-06: a full launch and two screenshots were spent on this.)
#
# The AutoScale=1 path calls SyncStaticLayers + SyncFont, which rename the
# tier packages and copy the matching font. Manual mode skips both. So a manual
# tier test has to do that part itself - which is this script.
#
#   .\_tests\Set-Tier.ps1 -Tier 1        1x BASELINE: all packages off, stock font
#   .\_tests\Set-Tier.ps1 -Tier 1.5      force 1.5x, art and font included
#   .\_tests\Set-Tier.ps1 -Tier 2        back to 2x
#   .\_tests\Set-Tier.ps1 -Auto          hand control back to AutoScale
#   .\_tests\Set-Tier.ps1 -Status        report only, change nothing
#
# Waits for the game to close first - it runs ELEVATED and holds the dats open.
# NEVER kills it (standing order).

[CmdletBinding()]
param(
    [ValidateSet("1", "1.5", "2", "3")] [string] $Tier,
    [switch] $Auto,
    [switch] $Status
)

$ErrorActionPreference = "Stop"
$plug = (Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'SimCity 4\Plugins')
$zzz = Join-Path $plug "zzz-SC4UIScale"
$ini = Join-Path $plug "SC4UIScale.ini"
# Tier "1" has NO package tag on purpose: a 1x baseline means EVERY
# tier package is disabled and the game runs on its own stock art. It is
# the honest control for a before/after comparison - and the reason this
# script previously refused 1x is that a bare ScaleFactor=1 edit leaves
# the scaled art and font live, which looks like stock but is not.
$TAG = @{ "1" = $null; "1.5" = "15x"; "2" = "2x"; "3" = "3x" }
$ALLTAGS = @("15x", "2x", "3x")

function Get-Families {
    # A "family" is one package across its three tiers, in one folder.
    $fam = @{}
    $script:_dupTiers = @()
    foreach ($dir in @($plug, $zzz)) {
        if (-not (Test-Path $dir)) { continue }
        Get-ChildItem $dir -File -Filter "z_SC4UIScale_*" -ErrorAction SilentlyContinue |
            ForEach-Object {
                if ($_.Name -match '^(z_SC4UIScale_[A-Za-z]+)-(15x|2x|3x)\.dat(\.x1-disabled)?$') {
                    $key = "$dir|$($Matches[1])"
                    $tier = $Matches[2]
                    $isActive = -not $Matches[3]
                    if (-not $fam.ContainsKey($key)) { $fam[$key] = @{} }
                    # ⛔ A TIER CAN HAVE BOTH FILES AT ONCE. Deploy-OnGameClose
                    # writes the bare .dat AND refreshes the .x1-disabled twin,
                    # so "X-15x.dat" and "X-15x.dat.x1-disabled" routinely
                    # coexist. This slot used to be a plain assignment, and
                    # since ".dat" enumerates BEFORE ".dat.x1-disabled" the
                    # disabled twin overwrote the active one - every family
                    # then read as active=false, i.e. "(none - dependency-gated
                    # off)", and the rename loop skipped all nine.
                    #
                    # 2026-08-06: -Status reported ALL NINE packages gated off
                    # while all nine were in fact loading. A tier report that
                    # is wrong in the SAFE-LOOKING direction is worse than no
                    # report - it says "nothing of ours is live" when
                    # everything is. THE ACTIVE FILE ALWAYS WINS.
                    $prev = $fam[$key][$tier]
                    if ($prev) {
                        $script:_dupTiers += ,("{0} [{1}]" -f $Matches[1], $tier)
                        if ($prev.active) { return }   # keep the active one
                    }
                    $fam[$key][$tier] = @{ path = $_.FullName; active = $isActive }
                }
            }
    }
    return $fam
}

function Show-State {
    $fam = Get-Families
    $font = Join-Path $plug "FontStyle.ini"
    Write-Output ""
    Write-Output ("{0,-34} {1}" -f "package", "active tier")
    Write-Output ("-" * 52)
    foreach ($key in ($fam.Keys | Sort-Object)) {
        $name = $key.Split("|")[1]
        $on = @($ALLTAGS | Where-Object { $fam[$key][$_] -and $fam[$key][$_].active })
        $label = if ($on.Count -eq 0) { "(none - dependency-gated off)" } else { $on -join "," }
        Write-Output ("{0,-34} {1}" -f $name, $label)
    }
    if ($script:_dupTiers.Count -gt 0) {
        $u = $script:_dupTiers | Sort-Object -Unique
        Write-Output ""
        # ⚠ -f BINDS TIGHTER THAN +. Build the whole string first, THEN format,
        # or only the last fragment gets the arguments and the rest prints its
        # literal {0}/{1} placeholders (which is exactly what shipped first).
        $msg = "{0} tier slot(s) have BOTH a .dat and a .dat.x1-disabled file: {1}. " +
               "The active file wins here, but this is what made -Status report every " +
               "package as gated off on 2026-08-06. Harmless while the twins are identical."
        Write-Warning ($msg -f @($u).Count, ($u -join ", "))
    }
    if (Test-Path $ini) {
        $t = Get-Content $ini -Raw
        $a = if ($t -match '(?m)^AutoScale\s*=\s*(\S+)') { $Matches[1] } else { "?" }
        $f = if ($t -match '(?m)^ScaleFactor\s*=\s*(\S+)') { $Matches[1] } else { "?" }
        Write-Output ""
        Write-Output ("ini: AutoScale={0} ScaleFactor={1}" -f $a, $f)
    }
    if (Test-Path $font) {
        $h = (Get-FileHash $font -Algorithm SHA256).Hash
        $which = "unrecognised"
        foreach ($t in $ALLTAGS) {
            $c = Join-Path $plug ("FontStyle-{0}.ini" -f $t)
            if ((Test-Path $c) -and (Get-FileHash $c -Algorithm SHA256).Hash -eq $h) { $which = $t }
        }
        Write-Output ("FontStyle.ini matches: {0}" -f $which)
    }
}

if ($Status) { Show-State; exit 0 }
if (-not $Tier -and -not $Auto) { throw "give -Tier 1|1.5|2|3, or -Auto, or -Status" }

# --- the game holds these files open; wait, never kill --------------------
$waited = 0
while ($p = Get-Process -Name "SimCity 4" -ErrorAction SilentlyContinue) {
    if ($waited % 30 -eq 0) {
        # ⚠ -f BINDS TIGHTER THAN +, so it formatted only the LAST string of the
        # parenthesised concatenation and the earlier {0}/{1} shipped through
        # LITERALLY - observed here 2026-08-15 as "pid {0} ... waiting {1}s".
        # Deploy-OnGameClose.ps1 already carried this exact fix and the note
        # explaining it; this sibling script was never updated, so the same bug
        # sat in the same shape two files apart. Build the message FIRST, format
        # LAST. A wait loop that cannot say what it is waiting on is the defect
        # the warning exists to cure.
        $msg = "SimCity 4 (pid {0}) is running - waiting {1}s. Close it; " +
            "NOT killing it, it is elevated and holds the dats open."
        Write-Warning ($msg -f $p.Id, $waited)
    }
    Start-Sleep -Seconds 5; $waited += 5
}

# --- ini ------------------------------------------------------------------
# ⚠ NEVER write this file with a BOM (standing order).
$raw = [System.IO.File]::ReadAllBytes($ini)
if ($raw.Length -ge 3 -and $raw[0] -eq 0xEF -and $raw[1] -eq 0xBB -and $raw[2] -eq 0xBF) {
    throw "SC4UIScale.ini has a BOM - refusing to touch it"
}
$txt = [System.Text.Encoding]::UTF8.GetString($raw)
if ($Auto) {
    $txt = $txt -replace '(?m)^(AutoScale\s*=\s*).*$', '${1}1'
    Write-Output "ini: AutoScale=1 (the DLL picks the tier and syncs the layers itself)"
} else {
    $txt = $txt -replace '(?m)^(AutoScale\s*=\s*).*$', '${1}0'
    $txt = $txt -replace '(?m)^(ScaleFactor\s*=\s*).*$', ('${1}' + $Tier)
    Write-Output ("ini: AutoScale=0 ScaleFactor={0}" -f $Tier)
}
[System.IO.File]::WriteAllText($ini, $txt, (New-Object System.Text.UTF8Encoding($false)))

if ($Auto) {
    Write-Output "layers left as they are - the DLL will re-sync them at next boot."
    Show-State; exit 0
}

# --- packages -------------------------------------------------------------
$want = $TAG[$Tier]
$fam = Get-Families
$switched = 0; $gated = 0

# ⛔ THE 1x BASELINE IS A ONE-WAY TRIP WITHOUT THIS MANIFEST.
# The loop below skips any family with NO active tier, reading that as
# "the mod this package patches is not installed - leave it alone". That
# heuristic is correct for dependency gating and WRONG after a 1x baseline,
# which deliberately disables everything: every family then looks gated off
# and `-Tier 3` renames nothing at all. Observed 2026-08-18, first use of
# -Tier 1: "packages: 0 rename(s); 11 family(ies) left dependency-gated off",
# i.e. the 3x tier silently had no art. So 1x RECORDS what it switched off,
# and the next real tier uses that record instead of guessing.
$restoreFile = Join-Path $plug ".sc4uiscale-tier1-restore.txt"
$forced = New-Object System.Collections.Generic.HashSet[string]
if (-not $want) {
    $live = @()
    foreach ($key in ($fam.Keys | Sort-Object)) {
        if (@($ALLTAGS | Where-Object { $fam[$key][$_] -and $fam[$key][$_].active }).Count -gt 0) {
            $live += $key
        }
    }
    Set-Content -Path $restoreFile -Value $live -Encoding UTF8
    Write-Output ("1x: recorded {0} live package(s) so a later tier can restore them." -f $live.Count)
} elseif (Test-Path $restoreFile) {
    foreach ($line in (Get-Content $restoreFile)) {
        if ($line.Trim()) { [void]$forced.Add($line.Trim()) }
    }
    Write-Output ("restoring {0} package(s) recorded by the 1x baseline." -f $forced.Count)
}
foreach ($key in ($fam.Keys | Sort-Object)) {
    $tiers = $fam[$key]
    $name = $key.Split("|")[1]
    # ⚠ IF NO TIER IS ACTIVE, THIS PACKAGE IS DEPENDENCY-GATED OFF (its mod is
    # not installed). Leave it alone. Re-enabling it here would inject our
    # frozen copy of someone else's UI into a game that does not have that mod
    # - exactly what Test-ThirdPartyGates.ps1 exists to catch.
    $anyActive = @($ALLTAGS | Where-Object { $tiers[$_] -and $tiers[$_].active }).Count
    if ($anyActive -eq 0 -and -not $forced.Contains($key)) { $gated++; continue }
    foreach ($t in $ALLTAGS) {
        if (-not $tiers[$t]) { continue }
        $cur = $tiers[$t].path
        $bare = $cur -replace '\.x1-disabled$', ''
        $target = if ($t -eq $want) { $bare } else { "$bare.x1-disabled" }
        if ($cur -ne $target) {
            if (Test-Path $target) { Remove-Item $target -Force }
            Rename-Item $cur $target -Force
            $switched++
        }
    }
}
Write-Output ("packages: {0} rename(s); {1} family(ies) left dependency-gated off" -f $switched, $gated)
if ($want -and (Test-Path $restoreFile)) { Remove-Item $restoreFile -Force }

# --- font -----------------------------------------------------------------
# ⛔ THE GAME READS THE FONT TABLE FROM <install>\Plugins, **NOT** FROM
# Documents. This script's first version copied it next to the packages in
# Documents - where nothing ever reads it - so two full 1.5x test launches ran
# with the 2x table live: 2x point sizes inside 1.5x boxes, a 33% oversize.
# Every clipped label in those screenshots was that, and it sent an entire
# investigation after a 4.8% rounding overshoot that was not what was on
# screen.
#
# ScaleTier::SyncFont has always written to the install root and says so in its
# own comment. This script did not read it.
#
# ⚠ There are THREE probe sites and the order is
# <install>\Plugins -> <install> (i.e. Apps) -> the DBPF. Writing the wrong one
# leaves an older table winning silently.
if (-not $want) {
    # 1x BASELINE. Restore the user's ORIGINAL font table rather than any of
    # ours. The .user-original snapshot is what the installer preserved; if it
    # is absent the stock game table is simply the absence of a file, so we
    # remove ours rather than leave a scaled one winning silently (the exact
    # failure this file's own comment above describes).
    $gameDir = $env:SC4_GAME_DIR
    if (-not $gameDir) { $gameDir = "C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe" }
    $fontLive = Join-Path $gameDir "Plugins\FontStyle.ini"
    $orig = Join-Path $plug "FontStyle.ini.user-original"
    try {
        if (Test-Path $orig) {
            Copy-Item $orig $fontLive -Force -ErrorAction Stop
            Write-Output "font: restored FontStyle.ini.user-original (1x baseline)"
        } elseif (Test-Path $fontLive) {
            Remove-Item $fontLive -Force -ErrorAction Stop
            Write-Output "font: removed our FontStyle.ini - the game falls back to its own table"
        }
    } catch {
        Write-Warning ("could not restore the font at {0} ({1}). Run as Administrator." -f $fontLive, $_.Exception.Message)
    }
    # Keep the Documents copy in step, or -Status reports the LAST tier's font
    # while the game is running on its own table. That is the same class of
    # wrong-in-the-safe-direction report this file already warns about above:
    # it would read "FontStyle.ini matches: 15x" during a 1x baseline.
    $docFont = Join-Path $plug "FontStyle.ini"
    if (Test-Path $orig) { Copy-Item $orig $docFont -Force }
    elseif (Test-Path $docFont) { Remove-Item $docFont -Force }
    Show-State
    Write-Output ""
    Write-Output "1x BASELINE armed: every tier package disabled, stock font, ScaleFactor=1."
    Write-Output "The log should say ScaleFactor=1.00 and every code patch should be INERT"
    Write-Output "(they all gate on factor > 1.01). This is the control to compare 3x against."
    exit 0
}
$src = Join-Path $plug ("FontStyle-{0}.ini" -f $want)
$gameDir = $env:SC4_GAME_DIR
if (-not $gameDir) { $gameDir = "C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe" }
$fontLive = Join-Path $gameDir "Plugins\FontStyle.ini"
if (-not (Test-Path $src)) {
    Write-Warning ("FontStyle-{0}.ini missing - text will be wrong for this tier" -f $want)
} elseif (-not (Test-Path (Split-Path $fontLive -Parent))) {
    Write-Warning ("install Plugins folder not found at {0} - set SC4_GAME_DIR" -f $gameDir)
} else {
    try {
        Copy-Item $src $fontLive -Force -ErrorAction Stop
        Write-Output ("font: FontStyle-{0}.ini -> {1}" -f $want, $fontLive)
    } catch {
        Write-Warning ("could not write {0} ({1}). Run this shell as Administrator - " +
            "Program Files is ACL-protected and the game reads the font from THERE." -f $fontLive, $_.Exception.Message)
    }
    # Keep the Documents copy in step too, so -Status reports the truth.
    Copy-Item $src (Join-Path $plug "FontStyle.ini") -Force
}

Show-State
Write-Output ""
Write-Output "Launch the game. The log should say ScaleFactor=$Tier, and the"
Write-Output "packages above should show only that tier active."
