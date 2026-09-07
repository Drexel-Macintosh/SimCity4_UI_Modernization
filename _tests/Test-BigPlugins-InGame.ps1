# Test-BigPlugins-InGame.ps1 - the 20 GB question, measured on the running game.
#
# Launches SimCity 4 against a SYNTHETIC UserDir (built by New-SyntheticPlugins.py,
# staged as <Root>\Plugins) and samples the process every 2 s from an UNELEVATED
# shell: private bytes, peak paged bytes, working set, Responding, main window.
# Those counters come from NtQuerySystemInformation and are readable without
# elevation (thread times / modules are NOT - REGRESSION.md 2026-08 notes).
#
#   .\_tests\Test-BigPlugins-InGame.ps1 -Root C:\dev\_scale\UserDir-50000            DLL run
#   .\_tests\Test-BigPlugins-InGame.ps1 -Root C:\dev\_scale\UserDir-50000 -Control   DLL aside (renamed .dll.control)
#
# Milestone common to both runs: the first sample with a main window that is
# Responding. PASS/FAIL is the plan's table: window milestone DLL - control
# <= 3.0 s at 50k on an SSD; peak private bytes DLL - control <= 64 MB on the
# wrap path. The DLL run's own numbers are in <Root>\Plugins\010-SC4UIScale\
# SC4UIScale.log: `BootIndex:`, `ScaleTier: boot phases`, `IconSynth: scanned`,
# `stage 2 done`, `IconSynth: address space`.
#
# POSITIVE CONTROL ON THE INSTRUMENT: the first sample must read > 50 MB and a
# later sample must differ, else the reading is bogus and no verdict is printed.
# Never kills the game; stops sampling when the process exits or after -Seconds.
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string] $Root,
    [switch] $Control,
    [int] $Seconds = 600,
    [string] $Exe = "C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Apps\SimCity 4.exe"
)
$ErrorActionPreference = 'Stop'
if (-not (Test-Path (Join-Path $Root 'Plugins'))) { throw "no Plugins folder under $Root - stage the synthetic tree first" }
if (Get-Process 'SimCity 4' -ErrorAction SilentlyContinue) { throw "SimCity 4 is already running - close it from its own menu first (never force-kill)" }
$dll = Join-Path $Root 'Plugins\SC4UIScale.dll'
$aside = "$dll.control"
if ($Control) {
    if (Test-Path $dll) { Move-Item $dll $aside -Force }
    Write-Output "CONTROL run: SC4UIScale.dll set aside as $aside"
} else {
    if (-not (Test-Path $dll) -and (Test-Path $aside)) { Move-Item $aside $dll -Force }
    if (-not (Test-Path $dll)) { throw "no SC4UIScale.dll in $Root\Plugins - copy build\Release\SC4UIScale.dll there" }
    Write-Output ("DLL run: {0} ({1} bytes)" -f $dll, (Get-Item $dll).Length)
}
$label = if ($Control) { 'control' } else { 'dll' }
$out = Join-Path $PSScriptRoot ("bigplugins-{0}-{1}.csv" -f $label, (Get-Date -Format 'yyyyMMdd-HHmmss'))
"t_s,privMB,peakPagedMB,wsMB,responding,mainWindow" | Set-Content -Encoding ASCII $out
$t0 = Get-Date
Start-Process -FilePath $Exe -WorkingDirectory (Split-Path $Exe) -ArgumentList ('-UserDir:"{0}"' -f $Root) | Out-Null
Write-Output ("launched {0} with -UserDir:{1} at {2:HH:mm:ss}; sampling every 2 s to {3}" -f (Split-Path $Exe -Leaf), $Root, $t0, $out)
$first = $null; $milestone = $null; $peak = 0; $samples = 0; $differs = $false
while (((Get-Date) - $t0).TotalSeconds -lt $Seconds) {
    Start-Sleep -Seconds 2
    $p = Get-Process 'SimCity 4' -ErrorAction SilentlyContinue
    if (-not $p) { if ($samples -gt 0) { Write-Output "process exited"; break } else { continue } }
    $p.Refresh()
    $priv = [math]::Round($p.PrivateMemorySize64 / 1MB); $pk = [math]::Round($p.PeakPagedMemorySize64 / 1MB); $ws = [math]::Round($p.WorkingSet64 / 1MB)
    $resp = $p.Responding; $mw = ($p.MainWindowHandle -ne 0)
    $ts = [math]::Round(((Get-Date) - $t0).TotalSeconds, 1)
    "$ts,$priv,$pk,$ws,$resp,$mw" | Add-Content -Encoding ASCII $out
    $samples++
    if ($null -eq $first) { $first = $priv } elseif ($priv -ne $first) { $differs = $true }
    if ($pk -gt $peak) { $peak = $pk }
    if ($null -eq $milestone -and $mw -and $resp) { $milestone = $ts; Write-Output ("MILESTONE: main window responding at +{0} s (priv {1} MB)" -f $ts, $priv) }
}
Write-Output ("samples {0}; peak paged {1} MB; milestone {2}" -f $samples, $peak, ($(if ($null -ne $milestone) { "+$milestone s" } else { 'NOT SEEN' })))
if ($null -eq $first -or $first -lt 50 -or -not $differs) {
    Write-Output "INSTRUMENT CONTROL FAILED: first sample <= 50 MB or no sample ever changed - the reading is bogus; no verdict."
    exit 2
}
Write-Output ("{0} run recorded to {1}. Compare the two runs' MILESTONE and peak paged MB (plan: delta <= 3.0 s, <= 64 MB on the wrap path)." -f $label, $out)
if ($Control -and (Test-Path $aside)) { Write-Output "NOTE: the DLL stays aside; run without -Control to put it back for the DLL run." }
