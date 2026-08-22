# SC4UIScale v@VERSION@ - installer
#
# Copies this bundle's Plugins\ tree into Documents\SimCity 4\Plugins\.
# Refuses to run while the game is open, because SimCity 4 holds these files
# and a half-written dat is worse than no install.
#
#   .\Install.ps1              install
#   .\Install.ps1 -WhatIf      show what would be copied, change nothing
#   .\Install.ps1 -Uninstall   remove everything this bundle installed

[CmdletBinding(SupportsShouldProcess = $true)]
param([switch]$Uninstall)

$ErrorActionPreference = "Stop"
$src = Join-Path $PSScriptRoot "Plugins"

# --- find the game's Plugins folder ------------------------------------------
$docs = [Environment]::GetFolderPath("MyDocuments")
$plug = Join-Path $docs "SimCity 4\Plugins"
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
    foreach ($extra in @("SC4UIScale.log", "FontStyle-2x.ini", "FontStyle-15x.ini", "FontStyle-3x.ini")) {
        $t = Join-Path $plug $extra
        if (Test-Path $t) {
            if ($PSCmdlet.ShouldProcess($t, "remove")) { Remove-Item $t -Force }
            $removed++
        }
    }
    $zzz = Join-Path $plug "zzz-SC4UIScale"
    if ((Test-Path $zzz) -and -not (Get-ChildItem $zzz -Recurse -File)) {
        if ($PSCmdlet.ShouldProcess($zzz, "remove empty folder")) { Remove-Item $zzz -Recurse -Force }
    }
    Write-Output "removed $removed file(s)."
    Write-Output ""
    Write-Output "If you had your own FontStyle.ini before installing, it was preserved"
    Write-Output "as FontStyle.ini.user-original - rename it back now."
    exit 0
}

# --- install ------------------------------------------------------------------
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
    if ($PSCmdlet.ShouldProcess($to, "copy")) { Copy-Item $from $to -Force }
    $copied++
}

Write-Output "installed $copied file(s)."
Write-Output ""
Write-Output "Start SimCity 4. The UI should be visibly larger at the main menu."
Write-Output "If it is not, read $plug\SC4UIScale.log - the first lines say which"
Write-Output "resolution was detected and which scale tier was chosen."
