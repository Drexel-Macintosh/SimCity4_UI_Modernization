# Test-DistInstall.ps1 - round-trip the PUBLIC zip installer, offline.
#
# WHY THIS EXISTS. The zip is the path most users take, and until 2026-08-30
# it had ZERO test coverage - the sc4pac path had a full install/uninstall
# harness while dist-template\Install.ps1 shipped three defects nothing could
# see: a -Recurse uninstall that would strip a coexisting sc4pac package
# folder bare, a migrate list still moving the root ini INTO 010-SC4UIScale\
# (reversing the v4.5.0 decision every other tool follows), and a dead
# keep-your-ini branch for a file the bundle no longer contains.
#
# The bundle here is SYNTHESIZED (stub files): this tests Install.ps1's file
# LOGIC, not DBPF content - Test-DatIntegrity owns content. The installer is
# run as a CHILD process because it calls `exit`.
#
#   .\_tests\Test-DistInstall.ps1
[CmdletBinding()]
param([string]$Work = (Join-Path $env:TEMP 'sc4uiscale-distinstall-test'))

$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
$tpl = Join-Path $repo '_packaging\dist-template\Install.ps1'
if (-not (Test-Path $tpl)) { throw "no installer template at $tpl" }

$fail = @()
function Fail($m) { $script:fail += $m; Write-Output ("  FAIL " + $m) }
function Pass($m) { Write-Output ("  ok   " + $m) }
function Run-Installer([string]$inst, [string[]]$args2) {
    # Write-Host, NOT the output stream: a function returns everything its
    # pipeline emits, and the first run of this test returned the child's
    # whole transcript as the "exit code".
    & powershell -NoProfile -ExecutionPolicy Bypass -File $inst @args2 2>&1 |
        ForEach-Object { Write-Host ("    | " + $_) }
    return $LASTEXITCODE
}

# The installer itself refuses while the game runs; refuse here too so a red
# run cannot be blamed on that.
if (Get-Process 'SimCity 4' -ErrorAction SilentlyContinue) {
    Write-Output 'REFUSING: SimCity 4 is running - the installer would refuse and every assertion below would be vacuous.'
    exit 2
}

if (Test-Path $Work) { Remove-Item -LiteralPath $Work -Recurse -Force }

# ---- synthesize the bundle ---------------------------------------------------
$bundle = Join-Path $Work 'bundle'
New-Item -ItemType Directory "$bundle\Plugins\010-SC4UIScale" -Force | Out-Null
New-Item -ItemType Directory "$bundle\Plugins\zzz-SC4UIScale" -Force | Out-Null
Set-Content "$bundle\Plugins\SC4UIScale.dll" 'stub-dll' -Encoding ascii
Set-Content "$bundle\Plugins\010-SC4UIScale\z_SC4UIScale_SelectiveArt.dat" 'stub' -Encoding ascii
Set-Content "$bundle\Plugins\010-SC4UIScale\z_SC4UIScale_SelectiveArt.2x.uipay" 'stub' -Encoding ascii
Set-Content "$bundle\Plugins\zzz-SC4UIScale\z_SC4UIScale_CamUI.dat" 'stub' -Encoding ascii
Set-Content "$bundle\Plugins\zzz-SC4UIScale\z_SC4UIScale_CamUI.off.uipay" 'stub' -Encoding ascii
$inst = Join-Path $bundle 'Install.ps1'
(Get-Content $tpl -Raw) -replace '@VERSION@', '0.0.0-test' | Set-Content $inst -Encoding utf8

# ---- A. fresh install + uninstall --------------------------------------------
Write-Output 'A. fresh tree: install, then uninstall, leaves nothing'
$plugA = Join-Path $Work 'A\Plugins'
$rc = Run-Installer $inst @('-PluginsPath', $plugA)
if ($rc -ne 0) { Fail "A: install exited $rc" }
if (-not (Test-Path "$plugA\SC4UIScale.dll")) { Fail 'A: no DLL at the Plugins root after install' } else { Pass 'DLL at the root' }
if (-not (Test-Path "$plugA\010-SC4UIScale\z_SC4UIScale_SelectiveArt.2x.uipay")) { Fail 'A: payload missing from 010-' } else { Pass 'payloads landed' }
$rc = Run-Installer $inst @('-Uninstall', '-PluginsPath', $plugA)
if ($rc -ne 0) { Fail "A: uninstall exited $rc" }
$left = @(Get-ChildItem $plugA -Recurse -File -ErrorAction SilentlyContinue)
if ($left.Count) { Fail ("A: uninstall left {0} file(s): {1}" -f $left.Count, (($left | Select-Object -First 5 | ForEach-Object Name) -join ', ')) }
else { Pass 'uninstall left zero files' }

# ---- B. v4.4.x layout: the ini migrates back to the ROOT ---------------------
Write-Output 'B. v4.4.x tree: 010-resident ini migrates OUT to the root, legacy root files cleaned'
$plugB = Join-Path $Work 'B\Plugins'
New-Item -ItemType Directory "$plugB\010-SC4UIScale" -Force | Out-Null
Set-Content "$plugB\010-SC4UIScale\SC4UIScale.ini" 'user-settings-marker=1' -Encoding ascii
Set-Content "$plugB\FontStyle-2x.ini" 'legacy' -Encoding ascii
Set-Content "$plugB\z_SC4UIScale_OldRootPackage.dat" 'legacy' -Encoding ascii
$rc = Run-Installer $inst @('-PluginsPath', $plugB)
if ($rc -ne 0) { Fail "B: install exited $rc" }
$rootIni = Join-Path $plugB 'SC4UIScale.ini'
if (-not (Test-Path $rootIni)) { Fail 'B: the 010-resident ini did NOT migrate to the root - v4.5.1 installer direction (into the folder) is back' }
elseif ((Get-Content $rootIni -Raw) -notmatch 'user-settings-marker') { Fail 'B: the root ini is not the USER''S ini - settings were lost in migration' }
else { Pass 'ini migrated 010- -> root, user content intact' }
if (Test-Path "$plugB\010-SC4UIScale\SC4UIScale.ini") { Fail 'B: a second ini remains in 010- (two inis, one read)' } else { Pass 'no shadow ini left in 010-' }
if (Test-Path "$plugB\FontStyle-2x.ini") { Fail 'B: legacy root FontStyle-2x.ini survived' } else { Pass 'legacy root font source cleaned' }
if (Test-Path "$plugB\z_SC4UIScale_OldRootPackage.dat") { Fail 'B: legacy root package survived' } else { Pass 'legacy root package cleaned' }

# ---- C. sc4pac coexistence: uninstall must not reach into *.sc4pac -----------
Write-Output 'C. sc4pac coexistence: uninstall touches OUR three locations only'
$plugC = Join-Path $Work 'C\Plugins'
$rc = Run-Installer $inst @('-PluginsPath', $plugC)
if ($rc -ne 0) { Fail "C: install exited $rc" }
$managedA = "$plugC\050-load-first\a-drexel.sc4-ui-scale.9.9.9.sc4pac\010-SC4UIScale"
$managedB = "$plugC\900-overrides\a-drexel.sc4-ui-scale-mod-overrides.9.9.9.sc4pac"
New-Item -ItemType Directory $managedA -Force | Out-Null
New-Item -ItemType Directory $managedB -Force | Out-Null
Set-Content "$managedA\z_SC4UIScale_Managed.dat" 'sc4pac-owned' -Encoding ascii
Set-Content "$managedB\z_SC4UIScale_Managed2.dat" 'sc4pac-owned' -Encoding ascii
# POSITIVE CONTROL: a stray z_ file at the root MUST be removed - otherwise
# "the managed files survived" could just mean the sweep never ran at all.
Set-Content "$plugC\z_SC4UIScale_Stray.dat" 'stray' -Encoding ascii
$out = & powershell -NoProfile -ExecutionPolicy Bypass -File $inst -Uninstall -PluginsPath $plugC 2>&1
$rc = $LASTEXITCODE
if ($rc -ne 0) { Fail "C: uninstall exited $rc" }
if (-not (Test-Path "$managedA\z_SC4UIScale_Managed.dat")) { Fail 'C: uninstall DELETED a sc4pac-managed file (050-load-first) - the -Recurse sweep is back' } else { Pass 'sc4pac 050- package untouched' }
if (-not (Test-Path "$managedB\z_SC4UIScale_Managed2.dat")) { Fail 'C: uninstall DELETED a sc4pac-managed file (900-overrides)' } else { Pass 'sc4pac 900- package untouched' }
if (Test-Path "$plugC\z_SC4UIScale_Stray.dat") { Fail 'C: positive control - the root stray SURVIVED, so the sweep never ran and the two passes above are vacuous' } else { Pass 'positive control: root stray removed (the sweep ran)' }
if (-not (($out | Out-String) -match 'sc4pac')) { Fail 'C: no sc4pac notice printed - the user is not told the managed copy needs sc4pac remove' } else { Pass 'sc4pac notice printed' }

Write-Output ''
if ($fail.Count) {
    Write-Output ("RED: {0} failure(s)" -f $fail.Count)
    $fail | ForEach-Object { Write-Output ("  - " + $_) }
    exit 1
}
Remove-Item -LiteralPath $Work -Recurse -Force -ErrorAction SilentlyContinue
Write-Output 'ALL PASS - install, uninstall, v4.4.x ini migration and sc4pac coexistence all behave.'
exit 0
