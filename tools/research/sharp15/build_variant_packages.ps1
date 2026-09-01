<#
.SYNOPSIS
    Build the 1.5x art packages from a LAB VARIANT preview tree, for the
    in-game A/B (2026-09-01 edge-quality arc). Lab tooling, not a release step.

.DESCRIPTION
    build_variant_tree.py writes tools\upscale\preview-15x-<Variant>\SimCity_1
    with the shipped tree's names and DIMENSIONS. This script points the four
    preview-tree consumers at it (env SC4UI_UPSCALE_DIR) and runs them in
    Test-Builders.ps1's dependency order:

        selective-safe -> dialog-static -> itemicons-stage -> itemicons-sub

    The shipped packages\15x\*.dat are parked FIRST in
    packages\15x-variants\baseline\ (once; never overwritten), and the variant
    result is copied to packages\15x-variants\<Variant>\. packages\15x\ is left
    holding the VARIANT so Deploy-OnGameClose / Test-DatIntegrity see it - run
    with -Restore to put the baseline back.

    Side-builders that resample on their own (uncovered-icons, namicons,
    webbutton, csi, carbon) are NOT run: round 1 of the A/B is about the corpus
    and those stay nearest, by design (plan Phase 2.1).

.EXAMPLE
    .\build_variant_packages.ps1 -Variant thin_h
    .\build_variant_packages.ps1 -Restore
#>
[CmdletBinding()]
param(
    [string] $Variant,
    [switch] $Restore
)
$ErrorActionPreference = 'Stop'
$here  = Split-Path -Parent $MyInvocation.MyCommand.Path
$repo  = (Resolve-Path (Join-Path $here '..\..\..')).Path
$pkg15 = Join-Path $repo 'tools\packages\15x'
$vars  = Join-Path $repo 'tools\packages\15x-variants'
$base  = Join-Path $vars 'baseline'

if ($Restore) {
    if (-not (Test-Path $base)) { throw "no baseline parked at $base" }
    Get-ChildItem $base -Filter '*.dat' | ForEach-Object {
        Copy-Item $_.FullName (Join-Path $pkg15 $_.Name) -Force
        Write-Host ("restored {0}" -f $_.Name)
    }
    exit 0
}
if (-not $Variant) { throw "-Variant <name> or -Restore" }
$tree = Join-Path $repo ("tools\upscale\preview-15x-{0}\SimCity_1" -f $Variant)
if (-not (Test-Path $tree)) { throw "variant tree missing: $tree (run build_variant_tree.py $Variant)" }
$n = (Get-ChildItem $tree -Filter '*.png').Count
if ($n -lt 2000) { throw "variant tree has only $n sheets - refusing (shipped tree has 2206)" }

# park the shipped set once
if (-not (Test-Path $base)) {
    New-Item -ItemType Directory -Force $base | Out-Null
    Get-ChildItem $pkg15 -Filter '*.dat' | ForEach-Object {
        Copy-Item $_.FullName (Join-Path $base $_.Name)
        Write-Host ("parked baseline {0} ({1:N0} B)" -f $_.Name, $_.Length)
    }
}

$env:SC4UI_UPSCALE_DIR = $tree
Write-Host ("SC4UI_UPSCALE_DIR = {0}  ({1} sheets)" -f $tree, $n)
$steps = @(
    @('tools\selective-safe\build_selective_safe.py', '--factor', '1.5'),
    @('tools\dialog-static\build_dialog_static.py',   '--factor', '1.5'),
    @('tools\itemicons\stage_icons.py',               '--factor', '1.5'),
    @('tools\itemicons\build_itemicons_sub.py',       '--factor', '1.5')
)
foreach ($s in $steps) {
    $script = Join-Path $repo $s[0]
    Write-Host ("`n=== python {0} {1}" -f $s[0], ($s[1..($s.Count-1)] -join ' '))
    # A python SyntaxWarning on stderr is an ErrorRecord to PowerShell 5.1 and
    # would terminate under 'Stop' - judge the builder by its EXIT CODE only.
    $ErrorActionPreference = 'Continue'
    & python $script $s[1..($s.Count-1)]
    $code = $LASTEXITCODE
    $ErrorActionPreference = 'Stop'
    if ($code -ne 0) { throw ("builder failed: {0} (exit {1})" -f $s[0], $code) }
}
Remove-Item Env:SC4UI_UPSCALE_DIR

$out = Join-Path $vars $Variant
New-Item -ItemType Directory -Force $out | Out-Null
Get-ChildItem $pkg15 -Filter '*.dat' | ForEach-Object {
    Copy-Item $_.FullName (Join-Path $out $_.Name) -Force
    $b = Get-Item (Join-Path $base $_.Name) -ErrorAction SilentlyContinue
    $bl = if ($b) { $b.Length } else { 0 }
    Write-Host ("{0,-44} variant {1,12:N0} B   baseline {2,12:N0} B" -f $_.Name, $_.Length, $bl)
}
Write-Host ("`nvariant packages in {0}; packages\15x\ now holds the VARIANT (-Restore to undo)" -f $out)
