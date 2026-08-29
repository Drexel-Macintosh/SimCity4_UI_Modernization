# Build a throwaway mirror of the live Plugins tree with OUR two folders moved
# into the sc4pac layout, so tools\uimap\winner_table.py can diff the per-TGI
# winners between the two.
#
# WHY A MIRROR AND NOT A COPY. The tree is gigabytes. Every third-party folder
# is junctioned and every root file hard-linked, so the mirror costs seconds and
# no disk. Only the two folders whose POSITION is under test are placed
# differently - and they are junctioned too, because their CONTENTS are not what
# changes; their sort position is.
#
# WHAT IS BEING TESTED. sc4pac names package folders itself:
#   <subfolder>\<group>.<name>.<version>.sc4pac\
# The proposed shape is
#   050-load-first\a-drexel.sc4-ui-scale.<ver>.sc4pac\     (was 010-SC4UIScale)
#   900-overrides\zz-drexel.sc4-ui-scale-mod-overrides...  (was zzz-SC4UIScale)
# The group id "a-drexel" is load-bearing: inside one subfolder sc4pac sorts by
# <group>.<name>, so it is what keeps us loading BEFORE cam.* and therefore
# LOSING to CAM per-TGI, which is the compatibility gate. "drexel" would invert
# it silently.
#
# Junctions need no elevation; hard links need the file on the same volume.
[CmdletBinding()]
param(
    [string]$Live = (Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'SimCity 4\Plugins'),
    [string]$Out,
    [string]$Version = '4.5.0',
    [string]$EarlyGroup = 'a-drexel',
    [switch]$Force
)

$ErrorActionPreference = 'Stop'

if (-not $Out) {
    $Out = Join-Path $env:TEMP 'sc4uiscale-proposed\Plugins'
}
if (-not (Test-Path $Live)) { throw "live tree not found: $Live" }

$OUR_EARLY    = '010-SC4UIScale'
$OUR_OVERRIDE = 'zzz-SC4UIScale'
$EARLY_DEST   = "050-load-first\$EarlyGroup.sc4-ui-scale.$Version.sc4pac"
$OVR_DEST     = "900-overrides\zz-drexel.sc4-ui-scale-mod-overrides.$Version.sc4pac"

if (Test-Path $Out) {
    if (-not $Force) { throw "$Out exists - pass -Force to rebuild it" }
    # Remove junctions without following them into the real tree.
    Get-ChildItem $Out -Recurse -Force -Directory -ErrorAction SilentlyContinue |
        Where-Object { $_.LinkType -eq 'Junction' } |
        ForEach-Object { [System.IO.Directory]::Delete($_.FullName, $false) }
    Remove-Item $Out -Recurse -Force
}
New-Item -ItemType Directory $Out -Force | Out-Null

function Link-Dir($target, $linkPath) {
    $parent = Split-Path $linkPath -Parent
    if (-not (Test-Path $parent)) { New-Item -ItemType Directory $parent -Force | Out-Null }
    cmd /c mklink /J "`"$linkPath`"" "`"$target`"" | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "junction failed: $linkPath" }
}

$linked = 0; $files = 0
foreach ($e in Get-ChildItem $Live -Force) {
    if ($e.PSIsContainer) {
        if ($e.Name -eq $OUR_EARLY -or $e.Name -eq $OUR_OVERRIDE) { continue }
        if ($e.Name -eq '050-load-first') {
            # must be a REAL directory so our package can be placed inside it
            $real = Join-Path $Out $e.Name
            New-Item -ItemType Directory $real -Force | Out-Null
            foreach ($c in Get-ChildItem $e.FullName -Force) {
                if ($c.PSIsContainer) { Link-Dir $c.FullName (Join-Path $real $c.Name); $linked++ }
                else { New-Item -ItemType HardLink -Path (Join-Path $real $c.Name) -Target $c.FullName | Out-Null; $files++ }
            }
            continue
        }
        Link-Dir $e.FullName (Join-Path $Out $e.Name); $linked++
    }
    else {
        New-Item -ItemType HardLink -Path (Join-Path $Out $e.Name) -Target $e.FullName -ErrorAction SilentlyContinue | Out-Null
        $files++
    }
}

Link-Dir (Join-Path $Live $OUR_EARLY)    (Join-Path $Out $EARLY_DEST)
Link-Dir (Join-Path $Live $OUR_OVERRIDE) (Join-Path $Out $OVR_DEST)

Write-Output "proposed layout built: $Out"
Write-Output "  $linked junction(s), $files hard-linked file(s)"
Write-Output "  $OUR_EARLY    -> $EARLY_DEST"
Write-Output "  $OUR_OVERRIDE -> $OVR_DEST"
Write-Output ''
Write-Output 'Now diff the per-TGI winners:'
Write-Output "  python tools\uimap\winner_table.py --diff `"$Live`" `"$Out`" --ignore-moves"
