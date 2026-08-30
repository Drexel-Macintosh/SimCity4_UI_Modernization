# Verify the v4.5.0 content-swap arming after a boot.
#
# WHAT IT IS CHECKING. Through v4.4.0 a tier was armed by RENAMING dats
# (`.dat` <-> `.dat.x1-disabled`), which is the single reason sc4pac cannot
# uninstall this mod - it removes files by manifest name. From v4.5.0 every
# live filename is CONSTANT and the DLL swaps the file's CONTENT from an inert
# `.<tag>.uipay` payload the game never loads (measured: the plugin scan is
# extension-gated, probe #202).
#
# EVERY CHECK REFUSES RATHER THAN WARNS where a pass could be vacuous. This
# suite exists because a green gate has twice this week been read as a working
# feature - once when a probe measured a case that could not fail, and once
# when the mechanism under test never ran at all.
#
#   .\_tests\Verify-Arming.ps1
#   .\_tests\Verify-Arming.ps1 -Restore     # put the pre-4.5.0 layout back
[CmdletBinding()]
param(
    [string]$Plugins = (Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'SimCity 4\Plugins'),
    [string]$RestorePoint = (Join-Path $PSScriptRoot 'restore-point-pre-armone'),
    [switch]$Restore
)

$ErrorActionPreference = 'Stop'

if ($Restore) {
    if (-not (Test-Path $RestorePoint)) { throw "no restore point at $RestorePoint" }
    # NEVER plant a hand install over a sc4pac-managed one: 010-SC4UIScale\
    # at the top level out-sorts the managed copy in 050-load-first\, so a
    # restore into such a tree silently doubles every TGI.
    $managed = @(Get-ChildItem $Plugins -Directory -Recurse -Filter '*.sc4pac' -ErrorAction SilentlyContinue |
        Where-Object { Get-ChildItem $_.FullName -Recurse -Filter 'z_SC4UIScale_*' -ErrorAction SilentlyContinue |
                       Select-Object -First 1 })
    if ($managed.Count) {
        throw "REFUSING -Restore: this tree carries a sc4pac-managed copy of the mod ($($managed[0].FullName)) - a restored hand install would out-sort it and double every TGI"
    }
    foreach ($d in '010-SC4UIScale','zzz-SC4UIScale') {
        $t = Join-Path $Plugins $d
        if (Test-Path $t) { Remove-Item -LiteralPath $t -Recurse -Force }
        Copy-Item (Join-Path $RestorePoint $d) $t -Recurse -Force
    }
    Copy-Item (Join-Path $RestorePoint 'SC4UIScale.dll') (Join-Path $Plugins 'SC4UIScale.dll') -Force
    Write-Output "restored the pre-4.5.0 layout from $RestorePoint"
    exit 0
}

$fail = @()
$note = @()

# ---- folder discovery, BY CONTENT (v4.5.2) ----------------------------------
# Through v4.5.1 this script hard-coded 010-SC4UIScale\ / zzz-SC4UIScale\, so
# it could not run on the very tree Test-Sc4pacInstall.ps1 tells you to point
# it at (sc4pac renames both folders and nests the early one one level
# deeper). Markers are parsed out of the DLL's own ClassifyDir table - the
# single authority - and the walk mirrors its depth-3 cap.
$tierSrc = Get-Content (Join-Path (Split-Path -Parent $PSScriptRoot) 'src\ScaleTier.cpp') -Raw
$mTable = [regex]::Match($tierSrc, 'const Marker markers\[\] = \{(.*?)\};', 'Singleline')
if (-not $mTable.Success) { throw 'could not read the ClassifyDir marker table from ScaleTier.cpp - refusing (zero markers would pass vacuously)' }
$markerEarly = @(); $markerOverride = @()
foreach ($m in [regex]::Matches($mTable.Groups[1].Value, 'L"([^"]+)",\s*(\d)')) {
    if ($m.Groups[2].Value -eq '1') { $markerEarly += $m.Groups[1].Value }
    else { $markerOverride += $m.Groups[1].Value }
}
if ($markerEarly.Count -lt 2 -or $markerOverride.Count -lt 2) { throw "marker parse too thin (early=$($markerEarly.Count) override=$($markerOverride.Count)) - refusing" }
function Test-DirMarkers([string]$dir, [string[]]$pats) {
    foreach ($p in $pats) {
        if (@(Get-ChildItem -LiteralPath $dir -Filter $p -File -ErrorAction SilentlyContinue).Count) { return $true }
    }
    return $false
}
$lvl1 = @(Get-ChildItem -LiteralPath $Plugins -Directory -ErrorAction SilentlyContinue)
$lvl2 = @($lvl1 | ForEach-Object { Get-ChildItem -LiteralPath $_.FullName -Directory -ErrorAction SilentlyContinue })
$lvl3 = @($lvl2 | ForEach-Object { Get-ChildItem -LiteralPath $_.FullName -Directory -ErrorAction SilentlyContinue })
$ourDir = $null; $zzzDir = $null
foreach ($d in ($lvl1 + $lvl2 + $lvl3)) {
    if (-not $ourDir -and (Test-DirMarkers $d.FullName $markerEarly)) { $ourDir = $d.FullName }
    if (-not $zzzDir -and (Test-DirMarkers $d.FullName $markerOverride)) { $zzzDir = $d.FullName }
    if ($ourDir -and $zzzDir) { break }
}
if (-not $ourDir -or -not $zzzDir) {
    throw "could not discover both folders by content (early=$(if($ourDir){$ourDir}else{'NOT FOUND'}), override=$(if($zzzDir){$zzzDir}else{'NOT FOUND'})) - nothing below would be evidence"
}
Write-Output "folders: early=$ourDir"
Write-Output "         override=$zzzDir"
Write-Output ''

$log = Join-Path $ourDir 'SC4UIScale.log'
if (-not (Test-Path $log)) { throw "no log at $log - has the game been launched?" }
$logText = Get-Content $log -Raw

# ---- CONTROL FIRST -----------------------------------------------------------
# Without evidence the arming pass actually ran, every count below is a
# statement about a boot that never happened.
if ($logText -notmatch 'CommitArming:') {
    Write-Output 'CONTROL FAILED: the log has no CommitArming line.'
    Write-Output 'The arming pass did not run this boot, so nothing below would'
    Write-Output 'be evidence about it. Check the DLL actually deployed.'
    exit 1
}
$commit = ([regex]'CommitArming: .*').Match($logText).Value
Write-Output "CONTROL PASSED - the arming pass ran:"
Write-Output "  $commit"
Write-Output ''

if ($commit -match '(\d+) FAILED') {
    if ([int]$matches[1] -gt 0) { $fail += "ArmOne reported $($matches[1]) failure(s) - a package is holding bytes we did not choose" }
}

# ---- the layout the design promises -----------------------------------------
$tagged   = @(Get-ChildItem $Plugins -Recurse -File -Filter 'z_SC4UIScale_*.dat' |
              Where-Object { $_.BaseName -match '-(15x|2x|3x|1x)$' })
# FontStyle is a DIFFERENT mechanism and still legitimately renames: SyncFont
# stashes the user's own FontStyle.ini as FontStyle.ini.x1-disabled and copies a
# tier source over the live name. That is not the dat-arming rename layout this
# check exists to catch, and counting it made a healthy install read RED.
$disabled = @(Get-ChildItem $Plugins -Recurse -File -Filter '*.x1-disabled' |
              Where-Object { $_.Name -notlike 'FontStyle*' })
$payloads = @(Get-ChildItem $Plugins -Recurse -File -Filter 'z_SC4UIScale_*.uipay')
$stable   = @(Get-ChildItem $Plugins -Recurse -File -Filter 'z_SC4UIScale_*.dat' |
              Where-Object { $_.BaseName -notmatch '-(15x|2x|3x|1x)$' })
$tmp      = @(Get-ChildItem $Plugins -Recurse -File -Filter '*.dat.tmp')

Write-Output "live stable .dat   : $($stable.Count)"
Write-Output "payloads (.uipay)  : $($payloads.Count)"
Write-Output "tier-tagged .dat   : $($tagged.Count)   (must be 0 - the rename layout is gone)"
Write-Output ".x1-disabled       : $($disabled.Count)   (must be 0)"
Write-Output "stray .dat.tmp     : $($tmp.Count)   (must be 0 - a staged copy was orphaned)"
Write-Output ''

if ($tagged.Count   -ne 0) { $fail += "$($tagged.Count) tier-tagged .dat file(s) remain - migration did not complete" }
if ($disabled.Count -ne 0) { $fail += "$($disabled.Count) .x1-disabled file(s) remain - the rename layout survives" }
if ($tmp.Count      -ne 0) { $fail += "$($tmp.Count) orphaned .dat.tmp - ArmOne staged a copy it never committed" }
if ($payloads.Count -lt 40) { $fail += "only $($payloads.Count) payloads - expected ~80; migration looks partial" }
if ($stable.Count   -lt 10) { $fail += "only $($stable.Count) live packages - expected ~20" }

# ---- the state file, which is the diagnosis a constant filename destroys -----
$armed = @(); $off = @()
foreach ($d in $ourDir, $zzzDir) {
    $s = Join-Path $d 'z_SC4UIScale_STATE.txt'
    if (-not (Test-Path $s)) { $fail += "no z_SC4UIScale_STATE.txt in $d"; continue }
    foreach ($line in (Get-Content $s | Where-Object { $_ -notmatch '^#' -and $_.Trim() })) {
        $c = $line -split "`t"
        # 7 columns is the written format (base/tag/reason/4 stamps) - the
        # other three parsers of this file already required it, and a >=3
        # floor here silently accepted truncated rows the DLL never wrote.
        if ($c.Count -lt 7) { continue }
        if ($c[1] -eq 'off') { $off += $c[0] } else { $armed += "$($c[0])=$($c[1])" }
    }
}
Write-Output "STATE.txt: $($armed.Count) armed, $($off.Count) inert"
if ($armed.Count) { Write-Output ('  armed : ' + (($armed | Select-Object -First 8) -join ', ')) }
if ($off.Count)   { Write-Output ('  inert : ' + (($off   | Select-Object -First 8) -join ', ')) }
Write-Output ''

# Every armed package must agree on ONE tier. A split here is the exact defect
# that put stock 1x art into a 3x runtime this morning.
# INVERSE-GATED packages are not tiers and must not vote. SelectorUI's call
# site passes L"-1x" and WebText's passes L"" (-> "on"); both are armed by the
# ABSENCE or PRESENCE of something other than a scale factor. Counting "on" as
# a tier reported a disagreement on a perfectly healthy install.
$INVERSE_TAGS = @('on', '1x')
$tiers = @($armed |
           ForEach-Object { ($_ -split '=')[1] } |
           Where-Object { $INVERSE_TAGS -notcontains $_ } |
           Sort-Object -Unique)
if ($tiers.Count -gt 1) {
    $fail += "armed packages disagree on the tier: $($tiers -join ', ')"
} elseif ($tiers.Count -eq 1) {
    Write-Output "all armed packages agree on tier '$($tiers[0])'"
}

# ---- every live file must still be a parseable DBPF -------------------------
$bad = @()
foreach ($f in $stable) {
    $fs = [System.IO.File]::OpenRead($f.FullName)
    try {
        $b = New-Object byte[] 4
        $null = $fs.Read($b, 0, 4)
        if ([System.Text.Encoding]::ASCII.GetString($b) -ne 'DBPF') { $bad += $f.Name }
    } finally { $fs.Dispose() }
}
if ($bad.Count) { $fail += "not a DBPF after the swap: $($bad -join ', ')" }
else { Write-Output "all $($stable.Count) live file(s) still begin DBPF" }

Write-Output ''
if ($fail.Count) {
    Write-Output 'RED:'
    $fail | ForEach-Object { Write-Output "  - $_" }
    Write-Output ''
    Write-Output 'Undo with:  .\_tests\Verify-Arming.ps1 -Restore'
    exit 1
}
Write-Output 'ALL PASS - the content swap armed cleanly and the rename layout is gone.'
Write-Output 'This is a FILE-LEVEL result only. It says nothing about how the UI'
Write-Output 'looks; that still needs eyes on the game.'
exit 0
