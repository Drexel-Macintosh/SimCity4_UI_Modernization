# Test-Builders.ps1 - do the eight package builders actually RUN?
#
# WHY THIS EXISTS. On 2026-08-18 an audit verified that all eight builders were
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

# name, script, args. Order is a dependency chain, not a preference.
$BUILDERS = @(
    @{ n = "selective-safe";   s = "selective-safe\build_selective_safe.py"; a = $fArgs },
    @{ n = "dialog-static";    s = "dialog-static\build_dialog_static.py";   a = $fArgs },
    @{ n = "itemicons-stage";  s = "itemicons\stage_icons.py";               a = $fArgs },
    @{ n = "itemicons-sub";    s = "itemicons\build_itemicons_sub.py";       a = $fArgs },
    @{ n = "uncovered-icons";  s = "itemicons\build_uncovered_icons.py";     a = $fArgs },
    @{ n = "cam-graph-labels"; s = "itemicons\build_cam_graph_labels.py";    a = $fArgs },
    @{ n = "webtext";          s = "webtext\build_webtext.py";               a = $fArgs },
    @{ n = "mission-bubble-fx"; s = "effdir\build_mission_bubble_fx.py";     a = @("--all") }
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
