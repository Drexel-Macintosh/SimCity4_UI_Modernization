# SC4UIScale v@VERSION@ - installer
#
# Copies this bundle's Plugins\ tree into Documents\SimCity 4\Plugins\.
# Refuses to run while the game is open, because SimCity 4 holds these files
# and a half-written dat is worse than no install.
#
#   .\Install.ps1              install
#   .\Install.ps1 -WhatIf      show what would be copied, change nothing
#   .\Install.ps1 -Uninstall   remove everything this bundle installed
#   .\Install.ps1 -PluginsPath <dir>   install into a folder you name
#
# -PluginsPath exists for two reasons: a Documents folder this script cannot
# find (unusual redirection, a second install), and testing an install and
# uninstall round-trip against a scratch tree without touching your real one.

[CmdletBinding(SupportsShouldProcess = $true)]
param([switch]$Uninstall, [string]$PluginsPath)

$ErrorActionPreference = "Stop"
$src = Join-Path $PSScriptRoot "Plugins"

# --- find the game's Plugins folder ------------------------------------------
$docs = [Environment]::GetFolderPath("MyDocuments")
$plug = if ($PluginsPath) { $PluginsPath } else { Join-Path $docs "SimCity 4\Plugins" }
if ($PluginsPath -and -not (Test-Path $plug)) {
    New-Item -ItemType Directory $plug -Force | Out-Null
}
if (-not (Test-Path $plug)) {
    # OneDrive-redirected Documents is common and GetFolderPath usually follows
    # it, but check the obvious fallback before giving up.
    $alt = Join-Path $env:USERPROFILE "OneDrive\Documents\SimCity 4\Plugins"
    if (Test-Path $alt) { $plug = $alt }
}
if (-not (Test-Path $plug)) {
    Write-Output "Could not find your SimCity 4 Plugins folder."
    Write-Output "Looked in: $plug"
    Write-Output ""
    Write-Output "Run the game once so it creates Documents\SimCity 4\, or copy the"
    Write-Output "contents of this bundle's Plugins\ folder there by hand."
    exit 1
}

# --- the game must be closed --------------------------------------------------
if (Get-Process "SimCity 4" -ErrorAction SilentlyContinue) {
    Write-Output "SimCity 4 is RUNNING. Close it first - it holds these files open."
    Write-Output "Do not force-kill it; quit from the game's own menu."
    exit 1
}

Write-Output "SimCity 4 Plugins: $plug"
Write-Output ""

# Everything this bundle owns, so uninstall is exact rather than a guess.
$owned = Get-ChildItem $src -Recurse -File | ForEach-Object {
    $_.FullName.Substring($src.Length + 1)
}

if ($Uninstall) {
    $removed = 0
    foreach ($rel in $owned) {
        $t = Join-Path $plug $rel
        if (Test-Path $t) {
            if ($PSCmdlet.ShouldProcess($t, "remove")) { Remove-Item $t -Force }
            $removed++
        }
    }
    # tier files the DLL renamed while running, plus its log
    Get-ChildItem $plug -Filter "z_SC4UIScale_*" -Recurse -File -ErrorAction SilentlyContinue |
        ForEach-Object {
            if ($PSCmdlet.ShouldProcess($_.FullName, "remove")) { Remove-Item $_.FullName -Force }
            $removed++
        }
    # DLL-generated files in the mod folder, and any pre-v4.2.0 leftovers at
    # the Plugins root (older releases installed everything there).
    $ourDir = Join-Path $plug "010-SC4UIScale"
    foreach ($base in @($ourDir, $plug)) {
        foreach ($extra in @("SC4UIScale.dll", "SC4UIScale.ini", "SC4UIScale.log",
                             "SC4UIScale.gcap", "SC4UIScale-104.csv", "FontStyle.ini",
                             # -4x is a real tier in ScaleTier.cpp's kPackages
                             # table; omitting its font source left one file
                             # behind and so defeated the empty-folder removal
                             # below (found 2026-08-25 by the uninstall audit).
                             "FontStyle-2x.ini", "FontStyle-15x.ini", "FontStyle-3x.ini",
                             "FontStyle-4x.ini")) {
            $t = Join-Path $base $extra
            if (Test-Path $t) {
                if ($PSCmdlet.ShouldProcess($t, "remove")) { Remove-Item $t -Force }
                $removed++
            }
        }
    }
    foreach ($dirName in @("010-SC4UIScale", "zzz-SC4UIScale")) {
        # Only remove a folder that is now EMPTY - anything left (the
        # preserved FontStyle.ini.user-original above all) stays visible for
        # the user to recover.
        $d = Join-Path $plug $dirName
        if ((Test-Path $d) -and -not (Get-ChildItem $d -Recurse -File)) {
            if ($PSCmdlet.ShouldProcess($d, "remove empty folder")) { Remove-Item $d -Recurse -Force }
        }
    }
    Write-Output "removed $removed file(s)."
    Write-Output ""
    Write-Output "If you had your own FontStyle.ini before installing, it was preserved"
    Write-Output "as FontStyle.ini.user-original - rename it back now."
    exit 0
}

# --- install ------------------------------------------------------------------
# v4.2.0 LAYOUT MIGRATION: releases before 4.2.0 installed ~20 files at the
# Plugins ROOT; this release lives entirely in Plugins\010-SC4UIScale\ (+ the
# zzz-SC4UIScale overrides folder). Clean the old root files first - the root
# DLL especially, which would otherwise load as a SECOND copy of this mod.
$legacyMoved = 0
$ourDir = Join-Path $plug "010-SC4UIScale"
# v4.4.0 ROOT CLEANUP: only the DLL stays at the Plugins root now - the
# game loads DLLs from the top level only, so it has no choice. The ini,
# log, gcap and #104 csv moved into 010-SC4UIScale/ so the folder carries
# everything a user (or a package manager) would remove. Matches what the
# 30 sc4pac DLL packages already do: .dll at the root, data in a folder.
foreach ($keep in @("FontStyle.ini.user-original", "SC4UIScale.ini",
                    "SC4UIScale.gcap", "SC4UIScale-104.csv")) {
    # user state from the old layout: carry it into the new home
    $old = Join-Path $plug $keep
    if (Test-Path $old) {
        if (-not (Test-Path $ourDir)) { New-Item -ItemType Directory $ourDir -Force | Out-Null }
        $new = Join-Path $ourDir $keep
        if (-not (Test-Path $new)) {
            if ($PSCmdlet.ShouldProcess($old, "migrate to 010-SC4UIScale")) { Move-Item $old $new -Force }
        } else {
            if ($PSCmdlet.ShouldProcess($old, "remove legacy root copy")) { Remove-Item $old -Force }
        }
        $legacyMoved++
    }
}
# Regenerated or dev-only: never carried forward.
foreach ($stale in @("FontStyle.ini", "FontStyle.ini.x1-disabled",
                     "FontStyle-2x.ini", "FontStyle-15x.ini", "FontStyle-3x.ini",
                     "z_SC4UIScale_FontStyle.ini", "SC4UIScale.log",
                     "SC4UIScale.ini.bak2")) {
    $old = Join-Path $plug $stale
    if (Test-Path $old) {
        if ($PSCmdlet.ShouldProcess($old, "remove legacy root file")) { Remove-Item $old -Force }
        $legacyMoved++
    }
}
Get-ChildItem $plug -Filter "z_SC4UIScale_*" -File -ErrorAction SilentlyContinue |
    ForEach-Object {
        if ($PSCmdlet.ShouldProcess($_.FullName, "remove legacy root package")) { Remove-Item $_.FullName -Force }
        $legacyMoved++
    }
if ($legacyMoved) { Write-Output "migrated/removed $legacyMoved file(s) from the pre-4.2.0 root layout." }

# Never clobber a user's existing FontStyle.ini; the DLL has its own
# preservation logic but an installer should not create the situation.
$copied = 0
foreach ($rel in $owned) {
    $from = Join-Path $src $rel
    $to = Join-Path $plug $rel
    $toDir = Split-Path -Parent $to
    if (-not (Test-Path $toDir)) {
        if ($PSCmdlet.ShouldProcess($toDir, "create folder")) {
            New-Item -ItemType Directory -Path $toDir -Force | Out-Null
        }
    }
    # The user's SETTINGS survive an upgrade: the bundle ini installs only
    # when no ini exists yet (fresh install, or the migration above already
    # carried the old one into place). Every other file is ours to replace.
    if ((Split-Path $rel -Leaf) -eq "SC4UIScale.ini" -and (Test-Path $to)) {
        Write-Output "kept your existing SC4UIScale.ini (settings preserved)"
        continue
    }
    if ($PSCmdlet.ShouldProcess($to, "copy")) { Copy-Item $from $to -Force }
    $copied++
}

Write-Output "installed $copied file(s)."
Write-Output ""
Write-Output "Start SimCity 4. The UI should be visibly larger at the main menu."
Write-Output "If it is not, read $plug\010-SC4UIScale\SC4UIScale.log - the first"
Write-Output "lines say which resolution was detected and which tier was chosen."
