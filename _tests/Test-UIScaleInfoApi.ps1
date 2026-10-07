<#
.SYNOPSIS
  The cIUIScaleInfo contract (api\cIUIScaleInfo.h), checked from outside the DLL.

.DESCRIPTION
  Builds _tests\api-harness\ApiHarness.cpp against the PUBLIC header only (the
  way another plugin author builds), loads the built SC4UIScale.dll from a
  throwaway tree under %TEMP%, and checks what the game's COM would see: the
  class ID is registered once, GetClassObject hands out the object, the values
  are the "unsupported build" answers (1.0 / manual / region 1.0 - the host is
  not SimCity 4, so the DLL's version gate refuses to scale), QueryInterface
  and reference counting follow GZCOM rules, unknown IIDs and CLSIDs are
  refused.

  MUTATION CONTROL: the harness is run a second time expecting the WRONG
  version and must FAIL - otherwise a PASS would prove nothing.

  FREEZE: the header's IDs, base class and method list (in order) must equal
  the frozen contract - a DLL built against an older copy calls the slots by
  position. A swapped-method copy must fail the same check.

  The throwaway tree never touches Documents, OneDrive or the game install:
  the DLL resolves its Plugins root from its own path and the install folder
  from the host exe's path, and both live under the temp tree.

  The in-game half (the lookup through the GAME's COM) is the
  "API: cIUIScaleInfo answered through the game's COM" line in SC4UIScale.log.

.PARAMETER Dll
  The DLL to test. Default: build\Release\SC4UIScale.dll.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File _tests\Test-UIScaleInfoApi.ps1
#>
param(
    [string]$Dll = ''
)
$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
if (-not $Dll) { $Dll = Join-Path $repo 'build\Release\SC4UIScale.dll' }
if (-not (Test-Path $Dll)) { Write-Host "NO DLL at $Dll - build first."; exit 2 }

# The version the DLL must report, read from the one string it is derived from.
$director = Get-Content (Join-Path $repo 'src\SC4UIScaleDllDirector.cpp') -Raw
if ($director -notmatch '#define UISCALE_VERSION_STR "(\d+)\.(\d+)\.(\d+)"') {
    Write-Host 'Could not read UISCALE_VERSION_STR.'; exit 2
}
$ver = ([int]$Matches[1] -shl 16) -bor ([int]$Matches[2] -shl 8) -bor [int]$Matches[3]
$wrongHex = '{0:X6}' -f ($ver + 1)
$verHex = '{0:X6}' -f $ver

# THE CONTRACT IS FROZEN (api\cIUIScaleInfo.h says so to every author who
# copies it): the IDs, the base class and the methods IN ORDER. A DLL built
# against an older copy calls slots by position, so an edit here breaks it
# silently - anything new needs a NEW interface with a NEW IID.
$frozen = @(
    'static const uint32_t GZCLSID_cIUIScaleInfo = 0xB54643B5;'
    'static const uint32_t GZIID_cIUIScaleInfo = 0xA9885499;'
    'class cIUIScaleInfo : public cIGZUnknown'
    'virtual uint32_t GetModVersion() = 0;'
    'virtual float GetUIScaleFactor() = 0;'
    'virtual bool IsAutoScale() = 0;'
    'virtual float GetRegionMapScale() = 0;'
)
function Get-ContractLines([string]$text) {
    # Code lines only: comments carry no ABI, so they may be reworded freely.
    @($text -split "`r?`n" | ForEach-Object { ($_ -replace '//.*$', '').Trim() } |
        Where-Object { $_ -match '^(static const uint32_t GZ|class |virtual )' })
}
function Test-Frozen([string]$text) {
    $got = Get-ContractLines $text
    if ($got.Count -ne $frozen.Count) { return $false }
    for ($i = 0; $i -lt $frozen.Count; $i++) { if ($got[$i] -ne $frozen[$i]) { return $false } }
    return $true
}
$headerText = Get-Content (Join-Path $repo 'api\cIUIScaleInfo.h') -Raw
$frozenOk = Test-Frozen $headerText
# Mutation control: the same check on the header with two methods swapped
# must fail, or a pass above would prove nothing.
$swapped = $headerText -replace 'virtual bool IsAutoScale\(\) = 0;', '@@A@@' `
    -replace 'virtual float GetRegionMapScale\(\) = 0;', 'virtual bool IsAutoScale() = 0;' `
    -replace '@@A@@', 'virtual float GetRegionMapScale() = 0;'
$frozenControl = -not (Test-Frozen $swapped)
Write-Host ("  {0}  api\cIUIScaleInfo.h matches the frozen contract ({1} lines)" -f $(if ($frozenOk) { 'PASS' } else { 'FAIL' }), $frozen.Count)
Write-Host ("  {0}  freeze check catches a reordered method (mutation control)" -f $(if ($frozenControl) { 'PASS' } else { 'FAIL' }))
if (-not $frozenOk) {
    Write-Host '  The header now reads:'
    Get-ContractLines $headerText | ForEach-Object { Write-Host "    $_" }
}
Write-Host ''

$vcvars = Get-ChildItem 'C:\Program Files\Microsoft Visual Studio\*\*\VC\Auxiliary\Build\vcvarsall.bat' -ErrorAction SilentlyContinue |
    Select-Object -First 1
if (-not $vcvars) { Write-Host 'vcvarsall.bat not found - Visual Studio C++ tools needed.'; exit 2 }

$tmp = Join-Path $env:TEMP ("SC4UIScaleApiTest-" + $PID)
$apps = Join-Path $tmp 'Game\Apps'
$ours = Join-Path $tmp 'Docs\Plugins\010-SC4UIScale'
New-Item -ItemType Directory -Force $apps, $ours | Out-Null
try {
    Copy-Item $Dll (Join-Path $ours 'SC4UIScale.dll')
    $exe = Join-Path $apps 'ApiHarness.exe'
    $src = Join-Path $repo '_tests\api-harness\ApiHarness.cpp'
    $incGz = Join-Path $repo 'vendor\gzcom-dll\gzcom-dll\include'
    $incApi = Join-Path $repo 'api'
    # An object FILE, not a folder: cl reads a quoted path ending in a
    # backslash as an escaped quote.
    $obj = Join-Path $tmp 'ApiHarness.obj'
    # stderr is merged INSIDE cmd: Windows PowerShell 5.1 turns any native
    # stderr line into a terminating error under 'Stop' (vcvarsall prints one
    # when vswhere is not on PATH, so the installer folder is put there too).
    $installer = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio\Installer'
    $cl = "set `"PATH=$installer;%PATH%`" && call `"$($vcvars.FullName)`" x86 >nul 2>&1 && cl /nologo /EHsc /std:c++17 /W4 /I`"$incGz`" /I`"$incApi`" `"$src`" /Fo`"$obj`" /Fe`"$exe`" 2>&1"
    $buildOut = cmd /c $cl
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $exe)) {
        $buildOut | ForEach-Object { Write-Host $_ }
        Write-Host 'HARNESS BUILD FAILED - no verdict.'; exit 2
    }
    $warn = @($buildOut | Where-Object { $_ -match 'warning' })
    if ($warn.Count -gt 0) { $warn | ForEach-Object { Write-Host "  build: $_" } }

    $dllPath = Join-Path $ours 'SC4UIScale.dll'
    Write-Host "Run 1 - the contract (expect PASS):"
    & $exe $dllPath $verHex | ForEach-Object { Write-Host $_ }
    $run1 = $LASTEXITCODE

    Write-Host ''
    Write-Host "Run 2 - MUTATION CONTROL, expecting version 0x$wrongHex (expect FAIL):"
    & $exe $dllPath $wrongHex | ForEach-Object { Write-Host $_ }
    $run2 = $LASTEXITCODE

    # The DLL's own log: the gate must have refused (that is what makes this
    # the unsupported-build row), and the refused-IID lookup must be logged.
    $log = Get-ChildItem $tmp -Recurse -Filter 'SC4UIScale.log' | Select-Object -First 1
    $logText = if ($log) { Get-Content $log.FullName -Raw } else { '' }
    $gateRefused = $logText -match 'minimum supported is'
    $refusalLogged = $logText -match ('lookup REFUSED - IID 0x{0:X8}' -f (0xA9885499 -bxor 1))

    Write-Host ''
    Write-Host ("  log: {0}" -f $(if ($log) { $log.FullName } else { 'NOT FOUND' }))
    Write-Host ("  {0}  the DLL's version gate refused the non-SC4 host" -f $(if ($gateRefused) { 'PASS' } else { 'FAIL' }))
    Write-Host ("  {0}  the refused-IID lookup is in the DLL's log" -f $(if ($refusalLogged) { 'PASS' } else { 'FAIL' }))

    $ok = ($run1 -eq 0) -and ($run2 -eq 1) -and $gateRefused -and $refusalLogged `
        -and $frozenOk -and $frozenControl
    Write-Host ''
    if ($ok) {
        Write-Host 'Test-UIScaleInfoApi: PASS (contract holds; the mutation control failed as it must).'
        exit 0
    }
    Write-Host ("Test-UIScaleInfoApi: FAIL (run1={0} want 0, run2={1} want 1, gate={2}, refusal log={3}, frozen={4}, freeze control={5})" -f $run1, $run2, $gateRefused, $refusalLogged, $frozenOk, $frozenControl)
    exit 1
}
finally {
    Remove-Item -Recurse -Force $tmp -ErrorAction SilentlyContinue
}
