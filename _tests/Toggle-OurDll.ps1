# Paths are RESOLVED, not hard-coded: Documents may be redirected by
# OneDrive, and the repo may be cloned anywhere (task #108).
<#
  Toggle-OurDll.ps1 - the control we keep failing to run.

  Renames SC4UIScale.dll aside (and back) so the game loads with NO code of
  ours at all. Art dats and fonts are left alone by default because they
  cannot execute; pass -IncludeArt to stand those down too for a fully
  inert run.

  WHY THIS EXISTS. On 2026-08-05 an entire session was spent reasoning about
  a fault without ever running the one measurement that separates "ours" from
  "the game's". Do this FIRST next time. See
  feedback-sc4-plugins-scan-is-recursive: a stash INSIDE Plugins disables
  nothing, so the aside folder here is a SIBLING of Plugins, not a child.

    .\Toggle-OurDll.ps1 -Off    game runs with no SC4UIScale.dll
    .\Toggle-OurDll.ps1 -On     put it back
    .\Toggle-OurDll.ps1         report current state
#>
[CmdletBinding()]
param([switch]$Off, [switch]$On, [switch]$IncludeArt)

$ErrorActionPreference = "Stop"

$Plugins = (Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'SimCity 4\Plugins')
$Aside   = (Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'SimCity 4\_control-aside')   # SIBLING of Plugins, never a child

if (Get-Process "SimCity 4" -ErrorAction SilentlyContinue) {
    Write-Output "SimCity 4 is RUNNING - close it from its own menu first (never force-kill; it runs elevated)."
    exit 1
}

$names = @("SC4UIScale.dll")
if ($IncludeArt) {
    $names += (Get-ChildItem $Plugins -Recurse -File -Filter "z_SC4UIScale_*.dat" |
               ForEach-Object { $_.FullName.Substring($Plugins.Length + 1) })
    $names += "FontStyle.ini"
}

function Show-State {
    $live = @(); $parked = @()
    foreach ($n in $names) {
        if (Test-Path (Join-Path $Plugins $n)) { $live += $n }
        elseif (Test-Path (Join-Path $Aside (Split-Path $n -Leaf))) { $parked += $n }
    }
    Write-Output ("live in Plugins : {0}" -f $(if ($live) { $live -join ', ' } else { '(none)' }))
    Write-Output ("parked aside    : {0}" -f $(if ($parked) { $parked -join ', ' } else { '(none)' }))
    Write-Output ("DLL state       : {0}" -f $(if (Test-Path (Join-Path $Plugins 'SC4UIScale.dll')) { 'LOADED - our code runs' } else { 'ABSENT - control run, none of our code executes' }))
}

if (-not $Off -and -not $On) { Show-State; exit 0 }

if (-not (Test-Path $Aside)) { New-Item -ItemType Directory -Path $Aside -Force | Out-Null }

foreach ($n in $names) {
    $leaf = Split-Path $n -Leaf
    $inPlugins = Join-Path $Plugins $n
    $inAside   = Join-Path $Aside $leaf
    if ($Off -and (Test-Path $inPlugins)) {
        Move-Item $inPlugins $inAside -Force
        Write-Output "parked : $n"
    } elseif ($On -and (Test-Path $inAside)) {
        $dir = Split-Path $inPlugins -Parent
        if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
        Move-Item $inAside $inPlugins -Force
        Write-Output "restored: $n"
    }
}
Write-Output ""
Show-State
