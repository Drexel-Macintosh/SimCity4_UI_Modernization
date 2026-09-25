# Build-Dist.ps1 - assemble a plug-and-play SC4UIScale bundle.
#
# THE FILE LIST IS _packaging\PackageFiles.psd1, the same list
# _tests\Deploy-OnGameClose.ps1 copies from (audit B12, 2026-09-25). A second
# hand-maintained copy of "what a working install contains" is a slow-acting
# bug generator, and this project has been bitten by exactly that: task #58
# (ThirdPartyUI was never in the deploy list) and task #116 (ItemIcons and
# ItemIconsSub). Until B12 this script REGEX-PARSED Deploy's Copy-Item lines,
# could not see the 30 written another way, and re-listed those by hand;
# bundles shipped without SelectorUI and without CsiIcons through that gap.
# One list read by both scripts removes the class: a package is in the
# install and the bundle, or in neither.
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
$listFile = Join-Path $proj "_packaging\PackageFiles.psd1"
if (-not (Test-Path $listFile)) { throw "package list not found: $listFile" }

# --- version comes from the code, never from a doc ---------------------------
$verSrc = Get-Content (Join-Path $proj "src\SC4UIScaleDllDirector.cpp") -Raw
# Suffixed dev versions ("4.3.0-dev") are legal here - a dev bundle is how
# the ZCarbon inclusion step gets exercised before a release exists.
if ($verSrc -notmatch '#define\s+UISCALE_VERSION_STR\s+"([0-9.]+(?:-[A-Za-z0-9]+)?)"') {
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

# --- the package list -------------------------------------------------------
# Every row except DeployOnly (UncoveredIcons: rebuilt per install from the
# player's own Plugins tree, so a shipped copy would be someone else's).
$items = @(@((Import-PowerShellDataFile $listFile).Files) | Where-Object { -not $_.DeployOnly })
if ($items.Count -lt 40) {
    throw ("the package list gave only $($items.Count) bundle file(s) - refusing to " +
           "ship a partial bundle (the floor is 40)")
}
Write-Output "  $($items.Count) file(s) from the package list"

# --- assemble ----------------------------------------------------------------
if (Test-Path $bundle) { Remove-Item $bundle -Recurse -Force }
New-Item -ItemType Directory -Path $plugOut -Force | Out-Null
New-Item -ItemType Directory -Path $ourOut -Force | Out-Null
New-Item -ItemType Directory -Path $zzzOut -Force | Out-Null

$missing = @()
$copied = 0
foreach ($it in $items) {
    $src = Join-Path $proj $it.Src
    if (-not (Test-Path $src)) { $missing += $it; continue }
    $dstDir = switch ($it.Dir) { "zzz" { $zzzOut } "our" { $ourOut } default { $plugOut } }
    Copy-Item $src (Join-Path $dstDir $it.Name) -Force
    $copied++
}
if ($missing.Count -gt 0) {
    Write-Output ""
    Write-Output "FAIL: $($missing.Count) source file(s) named by the package list do not exist:"
    $missing | ForEach-Object { Write-Output "    $($_.Src)" }
    if (@($missing | Where-Object { $_.Carbon }).Count) {
        Write-Output ("  ZCarbon: build all three tiers (_tests\Test-Builders.ps1 -Factor 1.5 / 2 / 3); " +
                      "without them reskin users get 1x art in a scaled UI")
    }
    if (@($missing | Where-Object { $_.Selector }).Count) {
        Write-Output ("  SelectorUI-1x: run tools\dialog-static\build_selector_1x.py; without it " +
                      "a bundle install cannot leave 1x from inside the game")
    }
    throw "refusing to ship a partial bundle"
}

# ZCarbon: Scoty Carbon Skin support, shipped since v4.3.1 and inert without
# the skin (see its rows in the package list and THIRD-PARTY-NOTICES.md).
$zcWant = @($items | Where-Object { $_.Name -match 'ZCarbon' }).Count
$zcShipped = @(Get-ChildItem $zzzOut -File | Where-Object { $_.Name -match 'ZCarbon' })
if ($zcShipped.Count -ne $zcWant) {
    throw ("expected $zcWant ZCarbon files in the bundle, found $($zcShipped.Count)")
}
Write-Output ("  + " + $zcShipped.Count + " ZCarbon file(s) (Scoty Carbon Skin support; gated, inert without the skin - see THIRD-PARTY-NOTICES.md)")

# the shipping user ini - the packaging copy, not the developer one.
# v4.4.0 ROOT CLEANUP: it goes in 010-SC4UIScale/ with the rest of our
# loose files. The DLL resolves it there and migrates any pre-4.4.0 root
# copy on first boot, so an upgrading user keeps their settings.
# v4.5.0: WE SHIP NO INI. Measured against sc4pac 0.10.0: in the package
# folder it is destroyed by every package UPDATE (the versioned folder is
# deleted wholesale), and shipping it with isIni:true lands it at the root
# RENAMED to _sc4pacnew.ini, never activated, and deleted on uninstall even
# after the user edits it. The DLL creates SC4UIScale.ini at the Plugins
# root on first run instead, which is the only copy that survives both.
# _packaging/SC4UIScale.ini is kept as the DEFAULTS reference, not shipped.

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
# The package list deliberately does not name these; neither can be rebuilt,
# so a bundle that silently contains them is unreproducible.
# WebText moved into the deploy manifest 2026-08-05 and now arrives with the
# package list's other rows, from tools\webtext\ - it was never actually
# unbuildable.
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
# A SECOND copy INSIDE zzz-SC4UIScale: the override package's description
# points at THIRD-PARTY-NOTICES.md, but sc4pac's default excludes drop every
# non-DBPF file - a bundle-root copy never installs, so channel users got an
# attribution pointer to a file they did not have. Inside the dir root it
# rides the package's withChecksum entry WITHOUT changing the package's
# longest-common-prefix (a bundle-root extra file would re-root the whole
# install one level deeper - the v4.5.0 discovery trap again). SC4's plugin
# scan is extension-gated (probe #202), so a .md in Plugins is inert.
Copy-Item (Join-Path $proj "THIRD-PARTY-NOTICES.md") (Join-Path $zzzOut "THIRD-PARTY-NOTICES.md") -Force
$copied++

# README + installer, version-stamped from the code so the bundle can never
# claim a version the DLL does not carry.
$tpl = Join-Path $proj "_packaging\dist-template"
# THE BUNDLE NO LONGER SHIPS AN INSTALLER (2026-08-31, user decision).
# Installing this mod is "copy two folders and two files into Plugins", which
# the README states in five lines. A script that does that is not worth the
# questions it raises: the one we shipped was blamed for creating a
# FontStyle.ini it had never touched, and answering that took a full
# investigation before the real cause - the DLL - was found. The README is now
# the only install path, and it covers the uninstall cases the script handled,
# including the game-folder leftover after a crash.
foreach ($f in @("README.txt")) {
    $text = Get-Content (Join-Path $tpl $f) -Raw
    $text = $text -replace "@VERSION@", $version
    if ($text -match "@VERSION@") { throw "unsubstituted token left in $f" }
    Set-Content -Path (Join-Path $bundle $f) -Value $text -Encoding utf8 -NoNewline
}

Write-Output ""
Write-Output "  copied      : $copied file(s)"
# ---- v4.5.0: NORMALISE TO THE PAYLOAD LAYOUT ------------------------------
# The SAME converter the deploy script calls. Both copy the package list's
# tier-tagged rows and convert at the end, so the install and the bundle
# cannot be converted differently.
# -Tier is EXPLICIT, not left to the converter's fallback. The bundle no
# longer ships an ini, so there is no ScaleFactor for it to read, and an
# unstated default is the kind of thing that is discovered a release later.
# It only decides which bytes the live files hold BEFORE the first launch:
# the bundle ships no STATE file, so ArmOne has no row for any package and
# copies the chosen payload over every live .dat on that launch (an sc4pac
# update misses the stamp the same way).
#
# "off", not "2x" (audit A3, 2026-09-25). Seeded at 2x, 13 live files were
# byte-identical to their .2x.uipay: 27.6 of the 123.7 MB zip was a second
# copy of bytes the DLL overwrites anyway. The .off stubs are one-entry DBPFs
# (25 of them, 4.6 KB in all), valid for sc4pac's DBPF parse. It is also the
# safer wrong answer: when the DLL does not load, the install is stock-looking
# (inert) instead of 2x art inside 1x windows - ArmOne's own rule, "inert is
# the only safe wrong answer".
& (Join-Path $proj "_tests\Convert-ToPayloadLayout.ps1") -Tree $plugOut -Tier "off"

# ---- LAYOUT MIXTURE TRIPWIRE (v4.5.0) ---------------------------------------
# The bundle must carry ONE arming layout, never both. This is a no-op under
# the rename scheme and under the payload scheme; it fires only on a MIXTURE,
# which is the one state that ships silently broken.
#
# WHY IT EXISTS. Before audit B12 this script re-listed 30 files by hand beside
# the rows it regex-parsed out of Deploy, and converting one set without the
# other would have put a stable z_SC4UIScale_ZCarbonUI.dat AND a live
# z_SC4UIScale_ZCarbonUI-2x.dat in the zip: two live providers of all 197 TGIs,
# at an identical file count. One shared list removes that route, but a row
# written in the payload layout would still produce a mixture, and this check
# costs nothing.
$bundleFiles = @(Get-ChildItem $plugOut -Recurse -File)
$oldLayout = @($bundleFiles | Where-Object {
    $_.Name -like '*.x1-disabled' -or
    ($_.Extension -eq '.dat' -and $_.BaseName -match '-(15x|2x|3x|4x|1x)$') })
$newLayout = @($bundleFiles | Where-Object { $_.Extension -eq '.uipay' })
if ($oldLayout.Count -and $newLayout.Count) {
    # The concatenation is parenthesised BEFORE -f: -f binds tighter than +,
    # and without the parentheses it formatted only the last string, so the
    # {0}..{3} above printed literally.
    throw (("LAYOUT MIXTURE: the bundle carries {0} rename-layout file(s) AND " +
            "{1} payload file(s). Every package present under both names has TWO " +
            "live providers for every TGI it owns. First of each: {2} / {3}. " +
            "Every row of _packaging\PackageFiles.psd1 must use the rename layout; " +
            "Convert-ToPayloadLayout.ps1 alone writes payloads.") -f $oldLayout.Count,
           $newLayout.Count, $oldLayout[0].Name, $newLayout[0].Name)
}
Write-Output ("  layout      : {0} (mixture tripwire clear)" -f
    $(if ($newLayout.Count) { 'payload' } else { 'rename' }))

# --- hash manifest -----------------------------------------------------------
# AFTER the payload converter, never before. v4.5.1 shipped a manifest written
# BEFORE Convert-ToPayloadLayout ran: 66 rows for 106 files, 0 rows for the 80
# .uipay payloads, and rows naming files the converter had deleted. A manifest
# of a layout the bundle no longer has is worse than none - it verifies clean
# against nothing and teaches the user the wrong file list.
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
Write-Output ("  manifest    : {0} row(s) in SHA256SUMS.txt (post-conversion)" -f $rows.Count)

$dllHash = (Get-FileHash (Join-Path $plugOut "SC4UIScale.dll") -Algorithm SHA256).Hash
$total = (Get-ChildItem $plugOut -Recurse -File | Measure-Object -Property Length -Sum).Sum

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

# ---- RELEASE ZIP ------------------------------------------------------------
# The script cuts the zip ITSELF. Before v4.5.2 nothing in the repo created
# the release asset: gen_channel.py hashed the bundle DIRECTORY while the
# yaml's url pointed at a hand-made zip nobody compared against those hashes.
# sc4pac verifies per-file sha256 at install time, so a directory/zip
# divergence is a hard install failure for every channel user - cutting the
# zip from the gated bundle makes the asset the bundle by construction.
# Wrapper folder included (Compress-Archive -Path <dir> keeps it); both the
# wrapped and unwrapped forms match the yaml's substring include patterns.
$zip = "$bundle.zip"
if (Test-Path $zip) { Remove-Item $zip -Force }
Compress-Archive -Path $bundle -DestinationPath $zip
$zipHash = (Get-FileHash $zip -Algorithm SHA256).Hash
Write-Output ("  release zip : {0} ({1:N1} MB, sha256 {2})" -f
    (Split-Path $zip -Leaf), ((Get-Item $zip).Length / 1MB), $zipHash)

Write-Output "BUILT: $bundle"
