# Set-Tier.ps1 - force a specific scale tier for an eyes-on test, DATA AND ALL.
#
# WHY THIS EXISTS. To test a tier by hand the obvious move is to set
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
# THE WHOLE TRANSITION IN ONE CALL - tier AND the screen it is judged on:
#
#   .\_tests\Set-Tier.ps1 -Tier 1 -Windowed              1x in a 1024x768 window
#   .\_tests\Set-Tier.ps1 -Tier 1 -Windowed -Width 1280 -Height 1024
#   .\_tests\Set-Tier.ps1 -Auto -FullScreen -Width 2400 -Height 1600
#
# WHY THE SCREEN IS PART OF THE TIER, and why this was three manual steps
# and a wrong turn before it was one flag: a 1x baseline at 3840x2160 is NOT a
# reference. Every stock widget is correct-but-tiny on a huge desktop, so it
# answers nothing about FORMATTING - which is the only reason anyone asks for
# 1x. The useful control is 1x at a resolution the stock UI was drawn for.
#
# AND `WindowMode=Windowed` ALONE DOES NOTHING. dgVoodoo overrides it:
# with FullScreenMode=true the game comes up borderless-fullscreen at panel
# size, so the requested WxH never renders. -Windowed sets BOTH halves, plus
# CaptureMouse=false (true traps the cursor so you cannot reach the title bar).
# Both files are written WITHOUT a BOM and backed up once, because
# dgVoodooCpl.exe rewrites the conf if it is ever launched.
#
# Waits for the game to close first - it runs ELEVATED and holds the dats open.
# NEVER kills it (standing order).

[CmdletBinding()]
param(
    [ValidateSet("1", "1.5", "2", "3")] [string] $Tier,
    [switch] $Auto,
    [switch] $Status,
    [switch] $Windowed,
    [switch] $FullScreen,
    [int] $Width,
    [int] $Height
)

$ErrorActionPreference = "Stop"
$plug = (Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'SimCity 4\Plugins')
$zzz = Join-Path $plug "zzz-SC4UIScale"
# v4.2.0 (subfolder move): our files live in Plugins-SC4UIScale\;
# SC4GraphicsOptions.ini and dgVoodoo.conf stay at the REAL Plugins root
# (they belong to other components).
$our = Join-Path $plug '010-SC4UIScale'
if (-not (Test-Path $our)) { New-Item -ItemType Directory $our | Out-Null }

# AUTHORITATIVE dependency-gated package list (2026-08-23 fix - see the
# family loop below for why). Parsed from src\ScaleTier.cpp the SAME way
# Test-DatIntegrity.ps1's drift check does, rather than a fourth hand-kept
# copy of a list that has already rotted twice (Deploy-OnGameClose.ps1's
# own $DEPENDENCY_GATED array was missing WebButtonUI until this same
# session). A package NOT in this list has no dependency at all - it is
# tier-gated only, and "currently disarmed" never means "its mod is
# absent" for it.
$DEPENDENCY_GATED_NAMES = New-Object System.Collections.Generic.HashSet[string]
try {
    $scaleTierSrc = Get-Content (Join-Path (Split-Path -Parent $PSScriptRoot) "src\ScaleTier.cpp") -Raw -ErrorAction Stop
    [regex]::Matches($scaleTierSrc, 'DepOkByName[^)]*?(z_SC4UIScale_[A-Za-z0-9]+)') |
        ForEach-Object { [void]$DEPENDENCY_GATED_NAMES.Add($_.Groups[1].Value) }
} catch {
    Write-Warning "could not read src\ScaleTier.cpp to derive the dependency-gated package list - falling back to the old 'no active tier = gated' heuristic for every family, which is known to misfire after a deploy leaves everything at the 1x baseline."
}
$ini = Join-Path $plug "SC4UIScale.ini"
# Tier "1" has NO package tag on purpose: a 1x baseline means EVERY
# tier package is disabled and the game runs on its own stock art. It is
# the honest control for a before/after comparison - and the reason this
# script previously refused 1x is that a bare ScaleFactor=1 edit leaves
# the scaled art and font live, which looks like stock but is not.
$TAG = @{ "1" = $null; "1.5" = "15x"; "2" = "2x"; "3" = "3x" }
$ALLTAGS = @("15x", "2x", "3x")

# THIS RUNS BEFORE ANY TIER BRANCH, ON PURPOSE. It used to sit at the
# bottom and never executed for -Tier 1, because that path `exit 0`s at its
# own banner - so the one transition most likely to want a window (the 1x
# baseline) was the one that silently skipped the screen change. The screen
# is independent of the tier; it must not live behind a tier's early return.
# ---- THE SCREEN HALF (2026-08-19) ------------------------------------------
# A tier is only meaningful against the resolution it is judged on, so setting
# one without the other is half a transition. Both files are ini-shaped but
# live in different places and one of them silently overrides the other.
if ($Windowed -or $FullScreen -or $Width -or $Height) {
    $gfx = Join-Path $plug "SC4GraphicsOptions.ini"
    $dg  = "C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Apps\dgVoodoo.conf"
    if ($Windowed -and -not $Width)  { $Width  = 1024 }
    if ($Windowed -and -not $Height) { $Height = 768  }

    function Set-IniKeyNoBom([string] $path, [hashtable] $pairs) {
        # NEVER a BOM (standing order for every SC4 ini) and never
        # Set-Content, whose default encoding is the ANSI codepage. Read bytes,
        # assert, write UTF8 with no preamble.
        $bytes = [IO.File]::ReadAllBytes($path)
        if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
            throw "$path already has a BOM - refusing to rewrite it"
        }
        $txt = [Text.Encoding]::UTF8.GetString($bytes)
        foreach ($k in $pairs.Keys) {
            $rx = New-Object Text.RegularExpressions.Regex(
                ('(?mi)^(\s*' + [Regex]::Escape($k) + '\s*=\s*).*$'))
            $m = $rx.Matches($txt)
            if ($m.Count -ne 1) { Write-Warning ("{0}: matched {1}x - not written" -f $k, $m.Count); continue }
            $txt = $rx.Replace($txt, ('${1}' + $pairs[$k]), 1)
            Write-Output ("  {0,-16} = {1}" -f $k, $pairs[$k])
        }
        [IO.File]::WriteAllBytes($path, (New-Object Text.UTF8Encoding $false).GetBytes($txt))
    }

    if ($Width -and $Height) {
        Write-Output "screen: SC4GraphicsOptions.ini"
        $mode = if ($FullScreen) { "FullScreen" } elseif ($Windowed) { "Windowed" } else { $null }
        $kv = @{ "WindowWidth" = "$Width"; "WindowHeight" = "$Height" }
        if ($mode) { $kv["WindowMode"] = $mode }
        Set-IniKeyNoBom $gfx $kv
    }

    if (($Windowed -or $FullScreen) -and (Test-Path $dg)) {
        $bak = "$dg.before-set-tier"
        if (-not (Test-Path $bak)) { Copy-Item $dg $bak -Force; Write-Output "  backed up dgVoodoo.conf" }
        Write-Output "screen: dgVoodoo.conf (the setting that ACTUALLY decides windowing)"
        try {
            Set-IniKeyNoBom $dg @{
                "FullScreenMode" = $(if ($FullScreen) { "true" } else { "false" })
                "CaptureMouse"   = $(if ($FullScreen) { "true" } else { "false" })
            }
        } catch {
            Write-Warning ("could not write dgVoodoo.conf ({0}). It is under Program Files - " +
                "run this shell as Administrator, or the window mode will NOT change." -f $_.Exception.Message)
        }
    }
}


function Get-Families {
    # A "family" is one package across its three tiers, in one folder.
    $fam = @{}
    $script:_dupTiers = @()
    foreach ($dir in @($our, $zzz)) {
        if (-not (Test-Path $dir)) { continue }
        Get-ChildItem $dir -File -Filter "z_SC4UIScale_*" -ErrorAction SilentlyContinue |
            ForEach-Object {
                if ($_.Name -match '^(z_SC4UIScale_[A-Za-z]+)-(15x|2x|3x)\.dat(\.x1-disabled)?$') {
                    $key = "$dir|$($Matches[1])"
                    $tier = $Matches[2]
                    $isActive = -not $Matches[3]
                    if (-not $fam.ContainsKey($key)) { $fam[$key] = @{} }
                    # A TIER CAN HAVE BOTH FILES AT ONCE. Deploy-OnGameClose
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
    $font = Join-Path $our "FontStyle.ini"
    Write-Output ""
    Write-Output ("{0,-34} {1}" -f "package", "active tier")
    Write-Output ("-" * 52)
    foreach ($key in ($fam.Keys | Sort-Object)) {
        $name = $key.Split("|")[1]
        $on = @($ALLTAGS | Where-Object { $fam[$key][$_] -and $fam[$key][$_].active })
        $label = if ($on.Count -eq 0) { "(none - dependency-gated off)" } else { $on -join "," }
        Write-Output ("{0,-34} {1}" -f $name, $label)
    }
    # SelectiveArt (v4.0.3 STABLE-FILENAME PILOT): its own row above always
    # reads "(none - dependency-gated off)" now - all three sources are
    # PERMANENTLY suffixed, so Get-Families' generic by-filename scan can
    # never see it as active. That is not a report of its real state; ask
    # by CONTENT instead, same technique Test-DatIntegrity.ps1 uses.
    $selArtStable = Join-Path $our "z_SC4UIScale_SelectiveArt.dat"
    if (-not (Test-Path $selArtStable)) { $selArtStable = "$selArtStable.x1-disabled" }
    if (Test-Path $selArtStable) {
        $h = (Get-FileHash $selArtStable -Algorithm SHA256).Hash
        $which = "unrecognised"
        foreach ($t in $ALLTAGS) {
            $src = Join-Path $our ("z_SC4UIScale_SelectiveArt-{0}.dat.x1-disabled" -f $t)
            if ((Test-Path $src) -and (Get-FileHash $src -Algorithm SHA256).Hash -eq $h) { $which = $t }
        }
        $isArmed = $selArtStable -notlike "*.x1-disabled"
        $label = if ($isArmed) { $which } else { "(disarmed - stock)" }
        Write-Output ("{0,-34} {1}  [stable file, by content]" -f "z_SC4UIScale_SelectiveArt", $label)
    }
    if ($script:_dupTiers.Count -gt 0) {
        $u = $script:_dupTiers | Sort-Object -Unique
        Write-Output ""
        # -f BINDS TIGHTER THAN +. Build the whole string first, THEN format,
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
            $c = Join-Path $our ("FontStyle-{0}.ini" -f $t)
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
        # -f BINDS TIGHTER THAN +, so it formatted only the LAST string of the
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
# NEVER write this file with a BOM (standing order).
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
# SelectorAtStock - THE TWO WAYS OF BEING AT 1x WANT OPPOSITE THINGS.
# This script is the MEASUREMENT path: -Tier 1 exists to produce a true stock
# reference, so it asks for absolute isolation (no subclass, no timer, nothing
# installed) and writes 0. Every other tier writes 1, so a player who later
# picks 1x from the in-game selector still has the selector to climb back with.
# Without this, taking one reference capture would silently remove the control
# from every subsequent 1x session.
$wantSel = if ($Tier -eq 1 -and -not $Auto) { "0" } else { "1" }
if ($txt -match '(?m)^SelectorAtStock\s*=') {
    $txt = $txt -replace '(?m)^(SelectorAtStock\s*=\s*).*$', ('${1}' + $wantSel)
} else {
    # Absent means the DLL is using its default (1). Add it under [UiSpike] so
    # the state is visible rather than implied - a setting you cannot see is a
    # setting nobody will think to check.
    $txt = $txt -replace '(?m)^(\[UiSpike\]\s*)$', ("`${1}`r`nSelectorAtStock=" + $wantSel)
}
Write-Output ("ini: SelectorAtStock={0}{1}" -f $wantSel,
    $(if ($wantSel -eq "0") { "  (stock reference: the DLL installs NOTHING)" }
      else { "  (1x keeps the in-game scale selector)" }))
[System.IO.File]::WriteAllText($ini, $txt, (New-Object System.Text.UTF8Encoding($false)))

if ($Auto) {
    Write-Output "layers left as they are - the DLL will re-sync them at next boot."
    Show-State; exit 0
}

# --- packages -------------------------------------------------------------
$want = $TAG[$Tier]
$fam = Get-Families
$switched = 0; $gated = 0

# THE 1x BASELINE IS A ONE-WAY TRIP WITHOUT THIS MANIFEST.
# The loop below skips any family with NO active tier, reading that as
# "the mod this package patches is not installed - leave it alone". That
# heuristic is correct for dependency gating and WRONG after a 1x baseline,
# which deliberately disables everything: every family then looks gated off
# and `-Tier 3` renames nothing at all. Observed 2026-08-18, first use of
# -Tier 1: "packages: 0 rename(s); 11 family(ies) left dependency-gated off",
# i.e. the 3x tier silently had no art. So 1x RECORDS what it switched off,
# and the next real tier uses that record instead of guessing.
$restoreFile = Join-Path $our ".sc4uiscale-tier1-restore.txt"
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
        $rec = $line.Trim()
        if (-not $rec) { continue }
        # v4.2.0 migration: records are keyed "dir|name", and pre-move
        # records carry the OLD Plugins-root dir for the Sub="" families.
        # Rewrite those to the new home so a restore file written before the
        # move still restores instead of silently matching nothing.
        if ($rec.StartsWith("$plug|")) {
            $rec = "$our|" + $rec.Substring("$plug|".Length)
        }
        [void]$forced.Add($rec)
    }
    Write-Output ("restoring {0} package(s) recorded by the 1x baseline." -f $forced.Count)
}
foreach ($key in ($fam.Keys | Sort-Object)) {
    $tiers = $fam[$key]
    $name = $key.Split("|")[1]
    # IF NO TIER IS ACTIVE **AND THIS PACKAGE IS ACTUALLY DEPENDENCY-GATED**
    # (per src\ScaleTier.cpp's own DepOkByName calls, not a guess), leave it
    # alone - its mod may not be installed, and re-enabling it here would
    # inject our frozen copy of someone else's UI into a game that does not
    # have that mod, exactly what Test-ThirdPartyGates.ps1 exists to catch.
    #
    # FIX (2026-08-23): this used to apply "no active tier -> gated off" to
    # EVERY family, tier-only ones included. A package with NO dependency at
    # all (DialogStatic, ItemIcons, ItemIconsSub, CsiIcons, UncoveredIcons,
    # SelectiveArt) has no "mod absent" state to protect - being fully
    # disarmed just means it is sitting at the 1x baseline for some OTHER
    # reason (Deploy-OnGameClose.ps1 preserving a baseline it found, not
    # this script's own -Tier 1 run - the ONLY case the $forced/restore-file
    # mechanism below was built for). MEASURED 2026-08-23: a deploy that
    # preserved a 1x baseline left DialogStatic/ItemIcons/ItemIconsSub/
    # CsiIcons/UncoveredIcons all fully disarmed with no restore-file ever
    # written, so `-Tier 2` reported "0 rename(s)" and silently left 2x
    # running with 1x art - the exact "wrong in the safe-looking direction"
    # failure this file's own header warns about, just via a new trigger.
    # SELECTIVEART IS A STABLE-FILENAME PACKAGE - NEVER RENAME ITS SOURCES
    # (2026-08-23, caught by Test-DatIntegrity the same day the fix above
    # shipped): its three -<tier>.dat.x1-disabled files are CONTENT SOURCES
    # for the stable z_SC4UIScale_SelectiveArt.dat and must stay stashed at
    # every tier; the dedicated block below content-swaps the stable file.
    # The 2026-08-23 fix above stopped skipping tier-only families here,
    # which let this generic rename loop arm SelectiveArt's -2x SOURCE at a
    # live name - two copies of the same TGIs racing on load order.
    if ($name -eq "z_SC4UIScale_SelectiveArt") { $gated++; continue }
    $anyActive = @($ALLTAGS | Where-Object { $tiers[$_] -and $tiers[$_].active }).Count
    $isDependencyGated = $DEPENDENCY_GATED_NAMES.Contains($name)
    if ($anyActive -eq 0 -and $isDependencyGated -and -not $forced.Contains($key)) { $gated++; continue }
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

# SelectiveArt (v4.0.3 STABLE-FILENAME PILOT): the generic rename loop above
# cannot touch it - there is no per-tier bare name to rename into any more,
# only a fixed name whose CONTENT must be overwritten. Same two branches as
# SyncDatStable in ScaleTier.cpp (kept in sync by hand; this is a dev tool,
# not the shipped sync path).
$selArtStable = Join-Path $our "z_SC4UIScale_SelectiveArt.dat"
$selArtOff = "$selArtStable.x1-disabled"
if (-not $want) {
    if (Test-Path $selArtStable) {
        Move-Item $selArtStable $selArtOff -Force
        Write-Output "SelectiveArt: disarmed (stock)."
    }
} else {
    if ((-not (Test-Path $selArtStable)) -and (Test-Path $selArtOff)) {
        Move-Item $selArtOff $selArtStable -Force
    }
    $selArtSrc = Join-Path $our ("z_SC4UIScale_SelectiveArt-{0}.dat.x1-disabled" -f $want)
    if (-not (Test-Path $selArtSrc)) {
        Write-Warning ("SelectiveArt: source for tier {0} not found ({1}) - stable file left as-is." -f $want, $selArtSrc)
    } else {
        $needCopy = $true
        if (Test-Path $selArtStable) {
            $needCopy = (Get-FileHash $selArtStable -Algorithm SHA256).Hash -ne
                        (Get-FileHash $selArtSrc -Algorithm SHA256).Hash
        }
        if ($needCopy) {
            Copy-Item $selArtSrc $selArtStable -Force
            Write-Output ("SelectiveArt: stable file now matches tier {0}." -f $want)
        } else {
            Write-Output ("SelectiveArt: already matches tier {0}." -f $want)
        }
    }
}

# --- font -----------------------------------------------------------------
# THE GAME READS THE FONT TABLE FROM <install>\Plugins, **NOT** FROM
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
# There are THREE probe sites and the order is
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
    $orig = Join-Path $our "FontStyle.ini.user-original"
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
    $docFont = Join-Path $our "FontStyle.ini"
    if (Test-Path $orig) { Copy-Item $orig $docFont -Force }
    elseif (Test-Path $docFont) { Remove-Item $docFont -Force }
    Show-State
    Write-Output ""
    Write-Output "1x BASELINE armed: every tier package disabled, stock font, ScaleFactor=1."
    Write-Output "The log should say ScaleFactor=1.00 and every code patch should be INERT"
    Write-Output "(they all gate on factor > 1.01). This is the control to compare 3x against."
    exit 0
}
$src = Join-Path $our ("FontStyle-{0}.ini" -f $want)
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
    Copy-Item $src (Join-Path $our "FontStyle.ini") -Force
}

Show-State
Write-Output ""
Write-Output "Launch the game. The log should say ScaleFactor=$Tier, and the"
Write-Output "packages above should show only that tier active."
