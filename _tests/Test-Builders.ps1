# Test-Builders.ps1 - do the package builders actually RUN?
#
# WHY THIS EXISTS. On 2026-08-18 an audit verified that eight builders were
# PRESENT in the repo and called it done. A cold-clone test then ran them and
# five failed. Presence is not execution, and only execution found:
#
#   * tools\dbpf\extracted-png-tgi.csv         derived by nothing
#   * tools\uiscripts\extracted\               derived by nothing
#   * tools\dialog-static\thirdparty-src\      derived by nothing
#   * tools\dialog-static\thirdparty-art\      derived by nothing
#   * a dependency ORDER nothing enforced (itemicons needs selective-safe's dat)
#
# All four inputs are correctly absent from the repo - they are the player's own
# game and mod files. The defect was that nothing rebuilt them and no error said
# how. tools\Bootstrap-Corpus.ps1 is that step; this file is the gate that keeps
# it honest.
#
# THE COUNT WAS ALSO WRONG. A "prove it all" pass the same day, cross-checked
# against the actual deploy manifest (_tests\Deploy-OnGameClose.ps1, which is
# authoritative per its own header comment), found THREE more real, deployed
# packages nobody had ever gated: MenuFix, CsiIcons, NamIcons. NamIcons has the
# same "presence is not execution" shape as ItemIconsSub - its 1x sources are
# another mod's (NAM's) files, not derivable on a machine without NAM
# installed, recovered here the same way (invert our own shipped 2x package,
# proven exact on 392/392 icons before being trusted).
#
# ORDER IS PART OF THE TEST. selective-safe emits refmap-<tag>.csv and the
# SelectiveArt dat that dialog-static and stage_icons both read. Running these
# as a flat list passes or fails for the wrong reason.
#
# Run from a machine with the game installed, AFTER:
#     tools\Bootstrap-Corpus.ps1
#     tools\upscale\Rebuild-Corpus.ps1 -Factor <f>

[CmdletBinding()]
param(
    [string]$Factor = "",          # "" = the untagged 2x default
    [switch]$StopOnFirstFailure
)

$ErrorActionPreference = "Continue"
$root  = Split-Path -Parent $PSScriptRoot
$tools = Join-Path $root "tools"

$fArgs = @()
$tag   = "2x default"
if ($Factor) { $fArgs = @("--factor", $Factor); $tag = ($Factor + "x") }

# --carbon (v4.3.0): the two layout builders also emit the ZCarbon* packages
# when the Scoty Carbon Skin inputs are staged. PRESENCE-GATED on the derived
# input tree, not on the flag: a machine without the skin (most users) builds
# plain and stays green; a machine with the staged payloads must exercise the
# carbon path or the gate proves nothing about it.
$carbonArgs = @()
if (Test-Path (Join-Path $tools "research\carbon\builder-inputs\thirdparty-src")) {
    $carbonArgs = @("--carbon")
    Write-Output "Carbon inputs present - ZCarbon packages included in this gate"
}

# name, script, args. Order is a dependency chain, not a preference.
$BUILDERS = @(
    @{ n = "selective-safe";   s = "selective-safe\build_selective_safe.py"; a = $fArgs + $carbonArgs },
    @{ n = "dialog-static";    s = "dialog-static\build_dialog_static.py";   a = $fArgs + $carbonArgs },
    @{ n = "itemicons-stage";  s = "itemicons\stage_icons.py";               a = $fArgs },
    @{ n = "itemicons-sub";    s = "itemicons\build_itemicons_sub.py";       a = $fArgs },
    # Both of these are genuinely factor-INDEPENDENT, not an oversight:
    # build_uncovered_icons.py loops over every tier internally in one run
    # (see its own TIERS table); build_cam_graph_labels.py emits a single
    # caption LTEXT with no scaled geometry at all. Passing --factor to
    # either is a caller error, not a builder defect - confirmed by reading
    # both scripts, not assumed.
    @{ n = "uncovered-icons";  s = "itemicons\build_uncovered_icons.py";     a = @() },
    @{ n = "cam-graph-labels"; s = "itemicons\build_cam_graph_labels.py";    a = @() },
    @{ n = "webtext";          s = "webtext\build_webtext.py";               a = $fArgs },
    @{ n = "mission-bubble-fx"; s = "effdir\build_mission_bubble_fx.py";     a = @("--all") },
    # Factor-independent, same reasoning as the two above.
    @{ n = "menu-patches";     s = "itemicons\build_menu_patches.py";        a = @() }
)

Write-Output ("Builder execution gate - factor {0}" -f $tag)
Write-Output ("Repo: {0}" -f $root)
Write-Output ""

$results = @()
foreach ($b in $BUILDERS) {
    $script = Join-Path $tools $b.s
    if (-not (Test-Path $script)) {
        Write-Output ("MISSING  {0}  ({1})" -f $b.n, $b.s)
        $results += @{ n = $b.n; ok = $false; why = "script not in repo" }
        if ($StopOnFirstFailure) { break }
        continue
    }
    Push-Location $tools
    $out = & python $script @($b.a) 2>&1
    $code = $LASTEXITCODE
    Pop-Location
    if ($code -eq 0) {
        Write-Output ("PASS     {0}" -f $b.n)
        $results += @{ n = $b.n; ok = $true; why = "" }
    } else {
        Write-Output ("FAIL     {0}  (exit {1})" -f $b.n, $code)
        # The last few lines carry the FATAL; the rest is progress chatter.
        @($out) | Select-Object -Last 6 | ForEach-Object { Write-Output ("    " + $_) }
        $results += @{ n = $b.n; ok = $false; why = ("exit " + $code) }
        if ($StopOnFirstFailure) { break }
    }
}

# ---- CsiIcons: positional factor, writes to research\udriveit\build\, then
# copies to tools\packages\<tag>\ - not the --factor convention every other
# builder uses, so it gets its own invocation rather than forcing $fArgs onto
# a script that does not accept it.
$csiFactor = if ($Factor) { $Factor } else { "2" }
$csiTag = if ($Factor -eq "1.5") { "15x" } elseif ($Factor -eq "3") { "3x" } else { "2x" }
Push-Location (Join-Path $tools "research\udriveit")
$out = & python "build_csi_scaled.py" $csiFactor 2>&1
$code = $LASTEXITCODE
if ($code -eq 0) {
    $pkgDir = Join-Path $tools ("packages\" + $csiTag)
    New-Item -ItemType Directory -Force -Path $pkgDir | Out-Null
    Copy-Item "build\SC4UIScale_CsiIcons.dat" (Join-Path $pkgDir ("z_SC4UIScale_CsiIcons-" + $csiTag + ".dat")) -Force
    Write-Output "PASS     csi-icons"
    $results += @{ n = "csi-icons"; ok = $true; why = "" }
} else {
    Write-Output ("FAIL     csi-icons  (exit {0})" -f $code)
    @($out) | Select-Object -Last 6 | ForEach-Object { Write-Output ("    " + $_) }
    $results += @{ n = "csi-icons"; ok = $false; why = ("exit " + $code) }
}
Pop-Location

# ---- ZCarbonIcons (v4.3.0): carbon-sourced CSI balloons + item strips.
# Positional factor like csi-icons; emits straight into the house locations
# so no copy step. Runs only when the carbon inputs are staged.
if ($carbonArgs.Count -gt 0) {
    Push-Location (Join-Path $tools "research\carbon")
    $zciFactor = if ($Factor) { $Factor } else { "2" }
    $out = & python "build_carbon_icons.py" $zciFactor 2>&1
    $code = $LASTEXITCODE
    if ($code -eq 0) {
        Write-Output "PASS     zcarbon-icons"
        $results += @{ n = "zcarbon-icons"; ok = $true; why = "" }
    } else {
        Write-Output ("FAIL     zcarbon-icons  (exit {0})" -f $code)
        @($out) | Select-Object -Last 6 | ForEach-Object { Write-Output ("    " + $_) }
        $results += @{ n = "zcarbon-icons"; ok = $false; why = ("exit " + $code) }
    }
    Pop-Location
}

# ---- NamIcons: needs its 1x sources recovered first (another mod's files,
# same shape as ItemIconsSub), then always builds all three tiers in one run.
Push-Location (Join-Path $tools "itemicons")
$out = & python "recover_nam_sources.py" 2>&1
$recovOk = ($LASTEXITCODE -eq 0)
if (-not $recovOk) {
    Write-Output "FAIL     namicons  (recover_nam_sources.py failed)"
    @($out) | Select-Object -Last 6 | ForEach-Object { Write-Output ("    " + $_) }
    $results += @{ n = "namicons"; ok = $false; why = "recovery failed" }
} else {
    $out = & python "rebuild_namicons.py" 2>&1
    $code = $LASTEXITCODE
    if ($code -eq 0) {
        Write-Output "PASS     namicons"
        $results += @{ n = "namicons"; ok = $true; why = "" }
    } else {
        Write-Output ("FAIL     namicons  (exit {0})" -f $code)
        @($out) | Select-Object -Last 6 | ForEach-Object { Write-Output ("    " + $_) }
        $results += @{ n = "namicons"; ok = $false; why = ("exit " + $code) }
    }
}
Pop-Location

# ---- ItemIcons pack step: at the untagged 2x default, stage_icons.py
# deliberately stops at staging (documented, not a bug - the shipped 2x dat
# embeds no build metadata worth re-touching on every run). Tagged tiers pack
# themselves. Without this the deploy manifest's expected
# tools\itemicons\z_SC4UIScale_ItemIcons.dat never exists on a cold clone.
if (-not $Factor) {
    Push-Location (Join-Path $tools "itemicons")
    $out = & (Join-Path $tools "dbpf\DbpfPack.exe") "stage" "z_SC4UIScale_ItemIcons.dat" 2>&1
    $code = $LASTEXITCODE
    if ($code -eq 0) {
        Write-Output "PASS     itemicons-pack-2x"
        $results += @{ n = "itemicons-pack-2x"; ok = $true; why = "" }
    } else {
        Write-Output ("FAIL     itemicons-pack-2x  (exit {0})" -f $code)
        $results += @{ n = "itemicons-pack-2x"; ok = $false; why = ("exit " + $code) }
    }
    Pop-Location
}

# The font table is generated, not a dat builder, but it ships in every tier
# and its --selfcheck is the only proof that factor 2 still reproduces
# candidate.ini byte-for-byte. A tier without it is not a tier.
Push-Location $tools
$null = & python "fonts\make_fontstyle.py" --selfcheck 2>&1
$fontOk = ($LASTEXITCODE -eq 0)
Pop-Location
if ($fontOk) { Write-Output "PASS     fontstyle --selfcheck" }
else { Write-Output "FAIL     fontstyle --selfcheck" }
$results += @{ n = "fontstyle"; ok = $fontOk; why = "selfcheck" }

$passed = @($results | Where-Object { $_.ok }).Count
$total  = $results.Count
Write-Output ""
Write-Output ("BUILDERS: {0}/{1} executed clean" -f $passed, $total)
if ($passed -ne $total) {
    Write-Output "GATE: FAIL"
    exit 1
}
Write-Output "GATE: PASS"
