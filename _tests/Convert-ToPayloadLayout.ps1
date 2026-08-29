# Convert a Plugins-style tree from the RENAME layout to the PAYLOAD layout.
#
# ONE script, called from BOTH _tests\Deploy-OnGameClose.ps1 and
# _packaging\Build-Dist.ps1 — and that is the entire point of it existing.
#
# WHY NOT EDIT THE COPY LINES IN BOTH. Build-Dist derives most of the bundle by
# REGEX-PARSING Deploy's Copy-Item lines, but 30 of them are invisible to that
# regex (named-parameter form, expression-built paths, Join-Path) and are
# compensated by HARDCODED blocks inside Build-Dist. Convert Deploy's copy
# lines alone and the parsed ones would emit payloads while the hardcoded
# blocks still emit tier-tagged live dats — a bundle carrying both
# z_SC4UIScale_ZCarbonUI.dat AND z_SC4UIScale_ZCarbonUI-2x.dat, i.e. TWO LIVE
# PROVIDERS of all 197 TGIs that package owns. Nothing would go red: the file
# count is identical either way.
#
# So neither caller's copy lines change at all. Both keep writing the
# tier-tagged layout they always did, and both then call THIS, which converts
# whatever it finds. Two callers, one conversion, nothing to drift.
#
# WHAT THE LAYOUT IS:
#   LIVE     z_SC4UIScale_<Pkg>.dat            the only thing SC4 loads; the
#                                              name never changes, at any tier
#   PAYLOAD  z_SC4UIScale_<Pkg>.<tag>.uipay    inert. Measured, not assumed:
#                                              probe #202 showed the plugin
#                                              scan is EXTENSION-gated, with 13
#                                              of our live .dat files named in
#                                              the same census as the control.
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$Tree,
    # Which tier to seed the live files with. The DLL re-arms from its own
    # fingerprint on the next boot regardless; seeding just means the tree is
    # coherent BEFORE anything launches, so the gates can read it.
    [string]$Tier = '',
    [switch]$WhatIf
)

$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
$gen  = Join-Path $repo 'tools\payload\build_payloads.py'
if (-not (Test-Path $Tree)) { throw "tree not found: $Tree" }
if (-not (Test-Path $gen))  { throw "payload generator not found: $gen" }

# ---- resolve the tier to seed ------------------------------------------------
if (-not $Tier) {
    $ini = Get-ChildItem $Tree -Recurse -Filter 'SC4UIScale.ini' -File -EA SilentlyContinue |
           Select-Object -First 1
    if ($ini) {
        $m = [regex]::Match((Get-Content $ini.FullName -Raw), '(?m)^\s*ScaleFactor\s*=\s*([\d.]+)')
        if ($m.Success) {
            switch ([double]$m.Groups[1].Value) {
                1.5     { $Tier = '15x' }
                2       { $Tier = '2x' }
                3       { $Tier = '3x' }
                4       { $Tier = '4x' }
                default { $Tier = '' }
            }
        }
    }
}
if (-not $Tier) {
    $Tier = '2x'
    Write-Output "  no ScaleFactor found - seeding live files at 2x (the DLL re-arms on boot)"
}

# ---- resolve stale twins BEFORE generating -----------------------------------
# The generator REFUSES when a base+tag has both `X-3x.dat` and
# `X-3x.dat.x1-disabled` - it will not guess which one's bytes ship, and that
# refusal is right. But the deploy legitimately produces that pair: it writes
# the armed tier as `X-3x.dat` and leaves an older run's `X-3x.dat.x1-disabled`
# sitting beside it.
#
# Only ONE reading is defensible. The bare `.dat` is what the deploy just
# wrote, this run, from `build\Release`; the suffixed twin is by definition the
# older copy of the SAME tier. So the twin goes. Scoped deliberately to an
# exact base+tag collision - a `.x1-disabled` with no bare counterpart is a
# normal stashed tier and is left completely alone.
$twins = 0
foreach ($live in (Get-ChildItem $Tree -Recurse -File -Filter 'z_SC4UIScale_*.dat')) {
    if ($live.BaseName -notmatch '-(15x|2x|3x|4x|1x)$') { continue }
    $stash = "$($live.FullName).x1-disabled"
    if (Test-Path $stash) {
        Remove-Item $stash -Force
        $twins++
    }
}
if ($twins) {
    Write-Output "  resolved $twins stale twin(s): kept the freshly deployed .dat, dropped the older .x1-disabled"
}

# ---- build the payloads ------------------------------------------------------
$stage = Join-Path $env:TEMP ("uipay-stage-" + [System.IO.Path]::GetRandomFileName())
New-Item -ItemType Directory $stage -Force | Out-Null
try {
    $out = & python $gen --src $Tree --out $stage 2>&1
    if ($LASTEXITCODE -ne 0) {
        $out | ForEach-Object { Write-Output "    $_" }
        throw "payload generation FAILED (exit $LASTEXITCODE) - the tree is unchanged"
    }
    $census = $out | Where-Object { $_ -match 'merged index census|CONTROL' }
    $census | ForEach-Object { Write-Output "  $_" }

    $made = @(Get-ChildItem $stage -Recurse -File -Filter '*.uipay')
    if ($made.Count -lt 10) {
        throw ("payload generation produced only $($made.Count) file(s) - refusing " +
               "to convert. A near-empty result means the source layout was not " +
               "what the generator expected, and deleting the tier files now would " +
               "destroy the only copy.")
    }

    if ($WhatIf) {
        Write-Output "  WHATIF: would place $($made.Count) payload(s) and seed live files at $Tier"
        return
    }

    # ---- place payloads, THEN remove the sources --------------------------
    # Order is not negotiable: never delete a file before its replacement
    # exists on disk.
    $placed = 0
    foreach ($f in $made) {
        $rel = $f.FullName.Substring($stage.Length).TrimStart('\')
        $dst = Join-Path $Tree $rel
        $dir = Split-Path $dst -Parent
        if (-not (Test-Path $dir)) { New-Item -ItemType Directory $dir -Force | Out-Null }
        Copy-Item $f.FullName $dst -Force
        $placed++
    }

    # ---- seed the live files -----------------------------------------------
    $seeded = 0
    foreach ($p in (Get-ChildItem $Tree -Recurse -File -Filter "*.$Tier.uipay")) {
        $base = $p.Name -replace "\.$Tier\.uipay$", ''
        $live = Join-Path $p.DirectoryName "$base.dat"
        Copy-Item $p.FullName $live -Force
        $seeded++
    }

    # ---- drop the rename layout --------------------------------------------
    $removed = 0
    foreach ($f in (Get-ChildItem $Tree -Recurse -File)) {
        $isStash  = $f.Name -like '*.x1-disabled'
        $isTagged = ($f.Extension -eq '.dat') -and ($f.BaseName -match '-(15x|2x|3x|4x|1x)$')
        if ($isStash -or $isTagged) { Remove-Item $f.FullName -Force; $removed++ }
    }

    # ---- refuse to leave a mixture behind -----------------------------------
    $leftOld = @(Get-ChildItem $Tree -Recurse -File | Where-Object {
        $_.Name -like '*.x1-disabled' -or
        (($_.Extension -eq '.dat') -and ($_.BaseName -match '-(15x|2x|3x|4x|1x)$')) })
    if ($leftOld.Count) {
        throw ("MIXTURE LEFT BEHIND: $($leftOld.Count) rename-layout file(s) survived " +
               "the conversion, e.g. $($leftOld[0].Name). Every package present under " +
               "both names has two live providers for every TGI it owns.")
    }

    Write-Output ("  payload layout: {0} payload(s) placed, {1} live file(s) seeded at {2}, {3} rename-layout file(s) removed" -f `
        $placed, $seeded, $Tier, $removed)
}
finally {
    if (Test-Path $stage) { Remove-Item -LiteralPath $stage -Recurse -Force -EA SilentlyContinue }
}
