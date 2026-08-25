# Build-Dist.ps1 - assemble a plug-and-play SC4UIScale bundle.
#
# WHY THIS PARSES Deploy-OnGameClose.ps1 INSTEAD OF LISTING FILES ITSELF:
# a second hand-maintained copy of "what a working install contains" is a
# slow-acting bug generator, and this project has already been bitten twice by
# exactly that. Task #58: ThirdPartyUI was never in the deploy list, so the
# live copy froze at an old build epoch and shipped dangling clone refs. Task
# #116: ItemIcons and ItemIconsSub had the same omission for the whole life of
# the script. Both looked green the entire time.
#
# So the deploy script is the ONE manifest. It is the thing that produces a
# known-good install - the one the user actually tests against - and this
# packager derives from it. Add a package there and it appears here for free;
# forget to, and the bundle is wrong in the same way the install is, which is
# at least a single failure instead of two that disagree.
#
# Usage:   .\_packaging\Build-Dist.ps1              (build into dist\)
#          .\_packaging\Build-Dist.ps1 -IncludeUnbuildable
#
# The game must NOT be running for the hashes to be meaningful against a live
# install, but this script never touches the live Plugins folder.

param(
    [switch]$IncludeUnbuildable,   # also pull WebText/MenuFix from the live install
    [string]$OutRoot               # override the dist root
)

$ErrorActionPreference = "Stop"
$proj = Split-Path -Parent $PSScriptRoot
$deployScript = Join-Path $proj "_tests\Deploy-OnGameClose.ps1"
if (-not (Test-Path $deployScript)) { throw "deploy manifest not found: $deployScript" }

# --- version comes from the code, never from a doc ---------------------------
$verSrc = Get-Content (Join-Path $proj "src\SC4UIScaleDllDirector.cpp") -Raw
if ($verSrc -notmatch '#define\s+UISCALE_VERSION_STR\s+"([0-9.]+)"') {
    throw "could not read UISCALE_VERSION_STR from SC4UIScaleDllDirector.cpp"
}
$version = $Matches[1]
if (-not $OutRoot) { $OutRoot = Join-Path $proj "dist" }
$bundle = Join-Path $OutRoot "SC4UIScale-v$version"
$plugOut = Join-Path $bundle "Plugins"
# v4.2.0 (subfolder move): the bundle ships TWO folders under Plugins\ -
# 010-SC4UIScale (everything of ours that used to sit at the root) and
# zzz-SC4UIScale (the overrides, unchanged). Install/uninstall = two folders.
$ourOut = Join-Path $plugOut "010-SC4UIScale"
$zzzOut = Join-Path $plugOut "zzz-SC4UIScale"

Write-Output "SC4UIScale v$version  ->  $bundle"

# --- parse the deploy manifest ----------------------------------------------
$lines = Get-Content $deployScript
$rx = '^\s*Copy-Item\s+"\$proj\\([^"]+)"\s+"\$(plug|our|zzz)\\([^"]+)"'
$items = @()
foreach ($l in $lines) {
    if ($l -match $rx) {
        $items += [pscustomobject]@{
            Src  = $Matches[1]
            Dest = $Matches[2]      # "plug" or "zzz"
            Name = $Matches[3]
        }
    }
}
if ($items.Count -lt 10) {
    throw ("parsed only $($items.Count) Copy-Item entries from the deploy script - " +
           "the manifest format changed and this packager is now blind. Fix the regex " +
           "rather than shipping a partial bundle.")
}
Write-Output "  parsed $($items.Count) file(s) from the deploy manifest"

# --- assemble ----------------------------------------------------------------
if (Test-Path $bundle) { Remove-Item $bundle -Recurse -Force }
New-Item -ItemType Directory -Path $plugOut -Force | Out-Null
New-Item -ItemType Directory -Path $ourOut -Force | Out-Null
New-Item -ItemType Directory -Path $zzzOut -Force | Out-Null

$missing = @()
$copied = 0
foreach ($it in $items) {
    $src = Join-Path $proj $it.Src
    if (-not (Test-Path $src)) { $missing += $it.Src; continue }
    $dstDir = switch ($it.Dest) { "zzz" { $zzzOut } "our" { $ourOut } default { $plugOut } }
    Copy-Item $src (Join-Path $dstDir $it.Name) -Force
    $copied++
}
if ($missing.Count -gt 0) {
    Write-Output ""
    Write-Output "FAIL: $($missing.Count) source file(s) named by the deploy manifest do not exist:"
    $missing | ForEach-Object { Write-Output "    $_" }
    throw "refusing to ship a partial bundle"
}

# --- INVISIBLE TO THE PARSER, AND THAT IS THE BUG IT CLOSES -----------------
# The deploy script copies SelectorUI-1x through VARIABLES:
#     Copy-Item $selSrc (Join-Path $zzz ("z_SC4UIScale_SelectorUI-1x.dat" + $selSuffix))
# so the literal-path regex above cannot see it and the bundle shipped WITHOUT
# the stock-tier scale selector. That made 1x a ONE-WAY DOOR for anyone
# installing from a bundle: at stock every other package is stashed, and the
# only control that could raise the tier again lives in that dat.
#
# ⭐ THE PARSER IS A DERIVED LIST, WHICH IS THE RIGHT SHAPE - but a derived
# list only sees what it can parse, and "not matched" is indistinguishable
# from "not present". The assertion below is what makes that difference
# visible, because the next package copied through a variable will be invisible
# in exactly the same way.
$selectorSrc = Join-Path $proj ("tools" + [IO.Path]::DirectorySeparatorChar + "packages" + [IO.Path]::DirectorySeparatorChar + "1x" + [IO.Path]::DirectorySeparatorChar + "z_SC4UIScale_SelectorUI-1x.dat")
if (-not (Test-Path $selectorSrc)) {
    throw ("the stock-tier selector package is missing: $selectorSrc - " +
           "without it a bundle install cannot leave 1x from inside the game")
}
Copy-Item $selectorSrc (Join-Path $zzzOut "z_SC4UIScale_SelectorUI-1x.dat") -Force
$copied++
Write-Output "  + z_SC4UIScale_SelectorUI-1x.dat (stock-tier selector; the DLL arms or stashes it at boot)"

# CsiIcons: SAME parser blindness, found 2026-08-24 - the deploy copies it
# through an expression-built loop, so the regex never saw it and it was
# ABSENT FROM EVERY DIST BUNDLE since 2026-08-18. Rescued exactly like
# SelectorUI: explicit copies + a hard assert. (UncoveredIcons is the loop's
# other member and stays OUT by design - it is rebuilt per-install from the
# player's own Plugins tree, so a shipped copy would be someone else's.)
foreach ($t in @(@("2x",""), @("15x",".x1-disabled"), @("3x",".x1-disabled"))) {
    $csiSrc = Join-Path $proj ("tools\packages\" + $t[0] + "\z_SC4UIScale_CsiIcons-" + $t[0] + ".dat")
    if (-not (Test-Path $csiSrc)) {
        throw "CsiIcons source missing: $csiSrc - the U-Drive-It offer-balloon icons would silently drop out of the bundle again"
    }
    Copy-Item $csiSrc (Join-Path $zzzOut ("z_SC4UIScale_CsiIcons-" + $t[0] + ".dat" + $t[1])) -Force
    $copied++
}
Write-Output "  + z_SC4UIScale_CsiIcons tiers (rescued from the parser blind spot - see comment)"

# PARSED-COUNT GATE: the next expression-built Copy-Item drops a package
# invisibly; keep a floor under the total so the drop goes red not silent.
if ($copied -lt 40) {
    throw ("bundle holds only $copied files - the deploy manifest parse has gone " +
           "blind to something (floor is 40). Diff the deploy script against the " +
           "parse before shipping.")
}

# the shipping user ini - the packaging copy, not the developer one
Copy-Item (Join-Path $proj "_packaging\SC4UIScale.ini") (Join-Path $plugOut "SC4UIScale.ini") -Force
$copied++

# --- an EMPTY z_SC4UIScale_FontStyle.ini placeholder, so a package manager --
# --- can own something, WITHOUT ever shipping a live-named FontStyle.ini ---
# FontStyle.ini itself is never in this bundle by build - the DLL GENERATES it
# at boot by copying one of the three tier sources (FontStyle-2x.ini etc.)
# over it, and the dat-integrity gate deliberately has no row for it (see its
# comment at the FONT_SOURCES table). That is correct for a hand-managed
# Plugins folder: the DLL owns the file from the first launch on.
#
# It is NOT correct for a package manager (sc4pac) install. A manager only
# knows how to remove files IT put there; since the real FontStyle.ini never
# shipped in any package, sc4pac cannot track it, so uninstalling this mod
# leaves an orphaned FontStyle.ini behind forever - reported by an sc4pac
# maintainer: "Since FontStyle.ini is generated by the mod's DLL, it is not
# included in the package, so SC4pac cannot uninstall it. Ideally, an empty
# FontStyle.ini file should be included in the ZIP file, and then the mod
# would overwrite that file."
#
# #182 (2026-08-23): shipping that placeholder AT THE LIVE NAME is what
# caused a real, severe, shipped crash. SyncFont's own preservation logic
# (#115/#118) saw the empty file on first boot, could not byte-match it to
# any tier source, and - before the #182 fix - wrongly snapshotted it as the
# PLAYER'S OWN font (".user-original"). Any later trip to stock tier restored
# that empty snapshot over the live FontStyle.ini, and the game crashed
# (ACCESS_VIOLATION in sub_7B4150) loading the city-select screen. The
# runtime now recognizes an empty file as ours by construction and never
# snapshots or restores one (IsEmptyFile, ScaleTier.cpp) - but that only
# repairs installs that already have the DLL. A user who deletes this mod
# BY HAND (rather than through sc4pac, or before ever launching the game
# again) has no DLL left to run that repair, and a loose, unbranded
# "FontStyle.ini" sitting in Plugins is easy to miss - it carries none of
# this mod's z_SC4UIScale_/zzz-SC4UIScale naming, so nothing marks it as
# ours to a person cleaning up by hand. Left behind empty, it is a landmine
# that crashes a COMPLETELY VANILLA game (no DLL involved at all) the next
# time any city loads.
#
# THE FIX: never ship a file at the literal live name. The placeholder is
# renamed to z_SC4UIScale_FontStyle.ini - a name the game engine never reads
# (only <install>\Plugins\FontStyle.ini is probed), so sc4pac still gets a
# real file it installed and can delete on uninstall, a manual cleanup that
# greps for "z_SC4UIScale_" now catches it like every other package, and
# Install.ps1's existing "z_SC4UIScale_*" uninstall sweep (dist-template\
# Install.ps1) already removes it for free. Being empty is now harmless
# regardless of whether the mod is present, absent, or half-removed, because
# nothing - not the game, not our own DLL - ever reads this exact filename;
# it exists purely so a package manager has something of ours to own.
New-Item -ItemType File -Path (Join-Path $ourOut "z_SC4UIScale_FontStyle.ini") -Force | Out-Null
if ((Get-Item (Join-Path $ourOut "z_SC4UIScale_FontStyle.ini")).Length -ne 0) {
    throw "z_SC4UIScale_FontStyle.ini placeholder is not empty - sc4pac needs a zero-byte file, not a real one"
}
if ((Test-Path (Join-Path $plugOut "FontStyle.ini")) -or (Test-Path (Join-Path $ourOut "FontStyle.ini"))) {
    # #182's exact failure mode reintroduced: a literal live-named FontStyle.ini
    # in the bundle is a landmine for anyone who removes this mod by hand.
    # Refuse to ship it rather than silently repeat the incident.
    throw ("a literal FontStyle.ini exists in the bundle output - this must " +
           "never ship (see the #182 comment above this check); only " +
           "z_SC4UIScale_FontStyle.ini belongs here")
}
$copied++
Write-Output ("  + z_SC4UIScale_FontStyle.ini (empty placeholder, so sc4pac can track and " +
    "uninstall a file of ours - never the live FontStyle.ini the DLL generates, per #182)")

# --- the two files with no build source --------------------------------------
# Deploy-OnGameClose deliberately does not touch these; neither can be rebuilt,
# so a bundle that silently contains them is unreproducible.
# WebText moved into the deploy manifest 2026-08-05 and now arrives through the
# normal parse, from tools\webtext\ - it was never actually unbuildable.
# MenuFix stays out: it rewrites CAM's gameplay data, so shipping it is a
# decision about a third-party mod's content, not about this one.
$unbuildable = @(
    @{ Name = "z_SC4UIScale_MenuFix.dat"; Sub = "zzz-SC4UIScale" }
)
$livePlug = Join-Path $env:USERPROFILE "OneDrive\Documents\SimCity 4\Plugins"
$notes = @()
foreach ($u in $unbuildable) {
    $from = if ($u.Sub) { Join-Path (Join-Path $livePlug $u.Sub) $u.Name } else { Join-Path $livePlug $u.Name }
    if ($IncludeUnbuildable -and (Test-Path $from)) {
        $to = if ($u.Sub) { $zzzOut } else { $plugOut }
        Copy-Item $from (Join-Path $to $u.Name) -Force
        $copied++
        $notes += "INCLUDED FROM THE LIVE INSTALL (third-party mod content): $($u.Name)"
    } else {
        $notes += "omitted BY DECISION (rewrites CAM gameplay data, not UI): $($u.Name)"
    }
}

# ⭐ PROVE THE ESCAPE HATCH IS IN THE BUNDLE. A missing selector does not
# break anything visibly - it removes the only way back from 1x, which nobody
# discovers until they are already there.
$selectorOut = Join-Path $zzzOut "z_SC4UIScale_SelectorUI-1x.dat"
if (-not (Test-Path $selectorOut)) {
    throw "the bundle has no stock-tier selector - 1x would be a one-way door"
}

# --- docs --------------------------------------------------------------------
Copy-Item (Join-Path $proj "LICENSE") (Join-Path $bundle "LICENSE.txt") -Force
Copy-Item (Join-Path $proj "THIRD-PARTY-NOTICES.md") (Join-Path $bundle "THIRD-PARTY-NOTICES.md") -Force

# README + installer, version-stamped from the code so the bundle can never
# claim a version the DLL does not carry.
$tpl = Join-Path $proj "_packaging\dist-template"
foreach ($f in @("README.txt", "Install.ps1")) {
    $text = Get-Content (Join-Path $tpl $f) -Raw
    $text = $text -replace "@VERSION@", $version
    if ($text -match "@VERSION@") { throw "unsubstituted token left in $f" }
    Set-Content -Path (Join-Path $bundle $f) -Value $text -Encoding utf8 -NoNewline
}

# --- hash manifest -----------------------------------------------------------
$manifest = Join-Path $bundle "SHA256SUMS.txt"
$rows = Get-ChildItem $plugOut -Recurse -File | Sort-Object FullName | ForEach-Object {
    $rel = $_.FullName.Substring($bundle.Length + 1)
    "{0}  {1}" -f (Get-FileHash $_.FullName -Algorithm SHA256).Hash, $rel
}
$header = @(
    "SC4UIScale v$version - SHA256 of every file in Plugins\",
    "Generated by the packaging script from the project deploy manifest.",
    ""
)
Set-Content -Path $manifest -Value ($header + $rows) -Encoding utf8

$dllHash = (Get-FileHash (Join-Path $plugOut "SC4UIScale.dll") -Algorithm SHA256).Hash
$total = (Get-ChildItem $plugOut -Recurse -File | Measure-Object -Property Length -Sum).Sum

Write-Output ""
Write-Output "  copied      : $copied file(s)"
Write-Output ("  bundle size : {0:N1} MB" -f ($total / 1MB))
Write-Output "  DLL sha256  : $dllHash"
foreach ($n in $notes) { Write-Output "  note        : $n" }
Write-Output ""
# ---- FOREIGN-CONTENT GATE, ON THE BUNDLE ITSELF -----------------------------
# The gate existed but was only ever aimed at the exported REPO tree, so the
# shipped bundle was never checked by it. Measured 2026-08-14: the as-shipped
# dist\SC4UIScale-v2.93.1 HARD-FAILS with 5 hits - two SC4TouchControls strings
# in LICENSE.txt, one in THIRD-PARTY-NOTICES.md, a dangling SHIP-MANIFEST.md
# path, and this script's own SHA256SUMS header. A gate pointed at the wrong
# channel is not a gate. No code change was needed in the scanner: SKIP_DIRS
# only suppresses a subdirectory NAMED dist during a walk, so aiming it
# directly at the bundle scans normally.
$gate = Join-Path $PSScriptRoot "Test-NoForeignContent.py"
if (Test-Path $gate) {
    Write-Output ""
    Write-Output "  gate        : Test-NoForeignContent on the bundle ..."
    & python $gate $bundle
    if ($LASTEXITCODE -ne 0) {
        throw "FOREIGN CONTENT IN THE BUNDLE (exit $LASTEXITCODE) - refusing to ship $bundle"
    }
} else {
    throw "Test-NoForeignContent.py not found at $gate - refusing to ship unchecked"
}

Write-Output "BUILT: $bundle"
