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
    # Files the DLL created or re-armed while running, plus its log - scoped
    # to the THREE places a zip install can put them (the Plugins root and
    # our two folders). NEVER -Recurse over all of Plugins: a package-manager
    # (sc4pac) copy of this mod lives inside *.sc4pac package folders, and a
    # recursive sweep would strip those bare while sc4pac still lists the
    # package as installed.
    $sweepDirs = @($plug,
                   (Join-Path $plug "010-SC4UIScale"),
                   (Join-Path $plug "zzz-SC4UIScale")) | Where-Object { Test-Path $_ }
    foreach ($d in $sweepDirs) {
        Get-ChildItem $d -Filter "z_SC4UIScale_*" -File -ErrorAction SilentlyContinue |
            ForEach-Object {
                if ($PSCmdlet.ShouldProcess($_.FullName, "remove")) { Remove-Item $_.FullName -Force }
                $removed++
            }
    }
    $sc4pacCopies = @(Get-ChildItem $plug -Directory -Recurse -Filter "*.sc4pac" -ErrorAction SilentlyContinue |
        Where-Object { Get-ChildItem $_.FullName -Recurse -Filter "z_SC4UIScale_*" -ErrorAction SilentlyContinue |
                       Select-Object -First 1 })
    if ($sc4pacCopies) {
        Write-Output "NOTE: a package-manager (sc4pac) copy of this mod exists under:"
        $sc4pacCopies | ForEach-Object { Write-Output "  $($_.FullName)" }
        Write-Output "This uninstaller leaves it alone. Remove it with:"
        Write-Output "  sc4pac remove a-drexel:sc4-ui-scale a-drexel:sc4-ui-scale-mod-overrides"
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
    # ---- THE GAME'S OWN FOLDER, which nothing used to clean --------------
    # The mod puts its font in the SimCity 4 install folder while the game runs
    # and removes it on a normal shutdown. IF THE GAME CRASHED, that removal
    # never happened and the file is still there - and uninstalling the mod
    # would strand it permanently, because until now this uninstaller only ever
    # looked at your Documents Plugins folder.
    #
    # A stranded copy is harmless (the mod redirects the game's font lookup at
    # RUN TIME, in memory only - the game executable on disk is never modified,
    # so with the mod gone the game does not read our file at all). It is still
    # ours, and leaving 23 KB of ours in someone's game folder after they asked
    # us to uninstall is not acceptable.
    #
    # ONLY files we can PROVE are ours are removed: our own filename, or a
    # stock-named leftover from a pre-redirect version that still carries our
    # generated-file header. A third party's font is never touched.
    $gameDir = $env:SC4_GAME_DIR
    if (-not $gameDir) {
        $gameDir = "C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe"
    }
    $gamePlug = Join-Path $gameDir "Plugins"
    if (Test-Path $gamePlug) {
        foreach ($cand in @("z_SC4UIScale_FontStyle.ini",
                            "z_SC4UIScale_FontStyle.ini.x1-disabled",
                            "FontStyle.ini",
                            "FontStyle.ini.x1-disabled")) {
            $t = Join-Path $gamePlug $cand
            if (-not (Test-Path $t)) { continue }
            $ours = $cand.StartsWith("z_SC4UIScale_")
            if (-not $ours) {
                # A stock-named file is only ours if it says so.
                $head = ""
                try { $head = (Get-Content $t -TotalCount 3 -ErrorAction Stop) -join "`n" } catch { }
                $ours = ($head -match "SC4UIScale:")
            }
            if ($ours) {
                if ($PSCmdlet.ShouldProcess($t, "remove our file from the game folder")) {
                    Remove-Item $t -Force
                }
                Write-Output "  removed from the GAME folder: $cand"
                $removed++
            } else {
                Write-Output "  left alone (not ours): $t"
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
# v4.4.0 ROOT CLEANUP: the log, gcap and #104 csv live in 010-SC4UIScale/
# so the folder carries everything a user (or a package manager) would
# remove. The INI IS NOT IN THIS LIST: v4.5.0 moved it back to the Plugins
# root (a package manager deletes its package folder on every update,
# taking an ini kept there with it - measured), and v4.5.1's installer
# still moving it INTO the folder re-created the exact ping-pong the
# deploy script's own comment warns about. The DLL reads the ROOT copy.
foreach ($keep in @("FontStyle.ini.user-original",
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
# v4.5.0 REVERSAL: a 010-resident ini from a v4.4.x install migrates BACK
# to the root, or it would sit unread forever while the DLL seeds a fresh
# default beside the DLL and the user wonders where their settings went.
$iniOld = Join-Path $ourDir "SC4UIScale.ini"
$iniNew = Join-Path $plug "SC4UIScale.ini"
if (Test-Path $iniOld) {
    if (-not (Test-Path $iniNew)) {
        if ($PSCmdlet.ShouldProcess($iniOld, "migrate ini back to the Plugins root")) {
            Move-Item $iniOld $iniNew -Force
        }
    } else {
        if ($PSCmdlet.ShouldProcess($iniOld, "remove shadowed 010- ini (root copy wins)")) {
            Remove-Item $iniOld -Force
        }
    }
    $legacyMoved++
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
    # (The bundle ships NO ini since v4.5.0. The DLL seeds one at the
    # Plugins root on its first run and never overwrites an existing one,
    # so user settings survive upgrades without installer involvement.)
    if ($PSCmdlet.ShouldProcess($to, "copy")) { Copy-Item $from $to -Force }
    $copied++
}

Write-Output "installed $copied file(s)."
Write-Output ""
Write-Output "Start SimCity 4. The UI should be visibly larger at the main menu."
Write-Output "If it is not, read $plug\010-SC4UIScale\SC4UIScale.log - the first"
Write-Output "lines say which resolution was detected and which tier was chosen."
