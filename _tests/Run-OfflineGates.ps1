# Run-OfflineGates.ps1 - run the offline source/byte gates in one pass and print
# one line per gate (exit code + its last output line). Needs no game.
#
# WHY THIS EXISTS (2026-09-25, audit follow-up). The suites table in
# REGRESSION.md lists the gates, but nothing ran them together, so a change had
# to pick its gates by hand. This runs every gate that is offline and fast.
# The game-dependent suites (Test-BootMatrix, Test-BigPlugins-InGame) and the
# slow or environment-bound ones (Test-Builders, Test-Sc4pacInstall,
# Test-BootWalk, Test-FolderDiscovery) are opt-in with -Slow.
#
# PASS = every gate exits 0. Compare against a run on the parent commit before
# calling a red one new: some gates carry known, documented states.
param([switch]$Slow)

$ErrorActionPreference = 'Continue'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$py = @(
    '_tests\Test-MutationCountInvariant.py', '_tests\Test-ProbeDerefGuards.py',
    '_tests\Test-CensusDistinct.py', '_tests\Test-PatchSiteBytes.py',
    '_tests\Test-ShippingIniKeys.py', '_tests\Test-SubBirthOwnsDock.py',
    '_tests\Test-SubFlyoutPlacement.py', '_tests\Test-RegionZoomSizes.py',
    '_tests\Test-MiniMapX8Bake.py', '_tests\Test-GZWinHeaderSlots.py',
    '_tests\Test-StockTierContract.py', '_tests\Test-SelectorContract.py',
    '_tests\Test-SelectorDerive.py', '_tests\Test-PackageGating.py',
    '_tests\Test-BootStateValidate.py', '_tests\Test-GodDockRule.py',
    '_tests\Test-ScaleDimParity.py', '_tests\Test-DisasterDrawRebuild.py',
    'tools\uimap\emu\emu_subplacetopmb_model.py', 'tools\uimap\crosscheck.py'
)
$ps = @('_tests\Test-ScaleTierDecide.ps1', '_tests\Test-SubRingLock.ps1',
        '_tests\Test-BornCorrectCoverage.ps1', '_tests\Test-ThirdPartyGates.ps1',
        '_tests\Test-DatIntegrity.ps1')
if ($Slow) { $ps += @('_tests\Test-FolderDiscovery.ps1', '_tests\Test-BootWalk.ps1') }

$red = 0
function Show($name, $code, $lines) {
    $last = ($lines | Where-Object { "$_".Trim() -ne '' } | Select-Object -Last 1)
    $last = "$last".Trim(); if ($last.Length -gt 110) { $last = $last.Substring(0, 110) }
    '{0,-4} {1,-44} {2}' -f $(if ($code -eq 0) { 'ok' } else { 'RED' }), (Split-Path $name -Leaf), $last
}
foreach ($t in $py) {
    $o = & python $t 2>&1; $c = $LASTEXITCODE; if ($c -ne 0) { $red++ }; Show $t $c $o
}
foreach ($t in $ps) {
    $o = & powershell -NoProfile -ExecutionPolicy Bypass -File $t 2>&1; $c = $LASTEXITCODE
    if ($c -ne 0) { $red++ }; Show $t $c $o
}
"OFFLINE GATES: $red red of $($py.Count + $ps.Count)"
exit $red
