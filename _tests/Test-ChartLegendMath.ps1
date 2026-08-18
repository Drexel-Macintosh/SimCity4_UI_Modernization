<#
  Test-ChartLegendMath.ps1 - #57 Graphs chart legend: the ACCEPTANCE ORACLE.

  WHY THIS FILE EXISTS (law 42). Four rect-patches shipped for the Graphs
  legend (v2.54.2/.3/.4) and every one moved the collision somewhere else,
  because there was no model and therefore no way to know a fix was wrong
  BEFORE it was built. tools\uimap\emu\prove_chart_legend.py is that model.
  This is its gate: it runs the prover, runs the prover's OWN mutation audit,
  and refuses to go green on either a red gate or a gate that cannot go red.

  SCOPE. IN: the acceptance CONDITIONS - the exact rects a fix must produce at
  every shipped tier, for both legend kinds. OUT: the MECHANISM - nothing here
  says which function to detour or which field to write.

  WHAT IT PROVES
    1  THE PROVER IS GREEN         every declared expectation held: each
                                   defective candidate violated the invariants
                                   it is known to violate, and the certified
                                   candidate passed every DECIDABLE check under
                                   both font hypotheses with no UNDECIDED check.
    2  IT IS STILL CALIBRATED      candidate A-FROZEN must still reproduce the
                                   live v2.54.4 2x layout 11/11 exact and then
                                   FAIL. An oracle that does not flag the known,
                                   user-confirmed defect cannot certify a fix.
    3  IT CAN STILL GO RED         --mutate: 22 mutations - delete each
                                   invariant, corrupt each measurement, and
                                   PERTURB EVERY FIELD OF THE CERTIFIED
                                   CANDIDATE - must all behave correctly.
                                   The perturbation family is the one that
                                   would have caught the I4 hole that let two
                                   counterexamples through the old gate.
    4  SKIPS ARE NOT PASSES        the gate must still print its four-status
                                   accounting (PASS / FAIL / SKIP / UNDECIDED)
                                   and the named reason for every non-pass.
    5  THE SIBLING MODELS AGREE    emu_text_extent.py --selfcheck must pass;
                                   the prover imports it live, so a drift in
                                   the font model silently changes every
                                   verdict here.

  WHEN IT GOES RED, see _tests\REGRESSION.md -> "CHART LEGEND MATH (#57)".

  Pure PowerShell + python. OFFLINE: never launches, attaches to or kills
  SimCity 4, reads no game file, writes nothing outside stdout.
  PASS = exit 0 + "ALL PASS".
#>
$ErrorActionPreference = 'Stop'
$script:Fail = 0
$script:Pass = 0

function Assert-True($cond, $what) {
    if ($cond) { $script:Pass++ }
    else { $script:Fail++; Write-Host ("  FAIL  {0}" -f $what) -ForegroundColor Red }
}

$proj = Split-Path $PSScriptRoot -Parent
$emu  = Join-Path $proj 'tools\uimap\emu'
$prover = Join-Path $emu 'prove_chart_legend.py'
$text   = Join-Path $emu 'emu_text_extent.py'

foreach ($f in @($prover, $text)) {
    if (-not (Test-Path $f)) {
        Write-Host ("FAIL: {0} not found" -f $f) -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "Test-ChartLegendMath - #57 Graphs legend acceptance oracle" -ForegroundColor Cyan
Write-Host "=========================================================="

# ---- 5: the font model the prover imports LIVE ---------------------------
Write-Host ""
Write-Host "5  sibling model: emu_text_extent --selfcheck" -ForegroundColor Yellow
$txOut = & python $text --selfcheck
$txRc  = $LASTEXITCODE
Assert-True ($txRc -eq 0) "emu_text_extent --selfcheck exits 0 (got $txRc)"
if ($txRc -ne 0) { $txOut | Select-Object -Last 20 | ForEach-Object { Write-Host ("    " + $_) } }

# ---- 1 + 2 + 4: the gate itself ------------------------------------------
Write-Host ""
Write-Host "1/2/4  the prover" -ForegroundColor Yellow
$out = & python $prover
$rc  = $LASTEXITCODE
Assert-True ($rc -eq 0) "prove_chart_legend.py exits 0 (got $rc)"

$joined = ($out -join "`n")
Assert-True ($joined -match 'OVERALL: PASS') "prover prints OVERALL: PASS"

# 2 - the calibration line. It must be present AND exact. If A-FROZEN stops
# reproducing the live 2x layout, the "known defect" the gate is calibrated
# against is not the one on the user's screen and no verdict means anything.
$calLine = $out | Where-Object { $_ -match 'calibration\s+(\d+)/(\d+) exact' } | Select-Object -First 1
Assert-True ($null -ne $calLine) "gate prints the calibration tally"
if ($calLine -match 'calibration\s+(\d+)/(\d+) exact') {
    $calOk = [int]$Matches[1]; $calN = [int]$Matches[2]
    Assert-True ($calN -ge 11) "calibration covers at least 11 measured values (got $calN)"
    Assert-True ($calOk -eq $calN) "calibration is exact ($calOk/$calN)"
    Write-Host ("   calibration {0}/{1} exact" -f $calOk, $calN)
}

# --- harvest the per-candidate verdicts ------------------------------------
# The candidate key is on its own header line ("  A-FROZEN  -- note"); the four
# verdict lines that follow carry only hypothesis/kind. Walk the block and
# attach each verdict to the candidate it belongs to. (A naive per-line match
# finds nothing - measured on the first run of this test.)
$verdicts = @{}          # "KEY|hyp|kind" -> failing invariants at f>=1.5
$cur = $null
foreach ($line in $out) {
    if ($line -match '^\s{2}([A-Z0-9][A-Za-z0-9-]+)\s+--\s') { $cur = $Matches[1]; continue }
    if ($null -ne $cur -and $line -match '^\s+(SQUEEZED|RAW)\s+(checkbox|plain)\s+f=1 fails\s+(\S+)\s+f>=1\.5 fails\s+(\S+)') {
        $verdicts[("{0}|{1}|{2}" -f $cur, $Matches[1], $Matches[2])] = @{
            f1 = $Matches[3]; hi = $Matches[4] }
    }
}
Assert-True ($verdicts.Count -ge 40) "parsed the per-candidate verdict table (got $($verdicts.Count) rows)"

# 2b - A-FROZEN must then FAIL. A calibration candidate that reproduces the
# defect and passes anyway would mean the invariants are decorative.
$frozen = @($verdicts.Keys | Where-Object { $_ -like 'A-FROZEN|*' })
Assert-True ($frozen.Count -eq 4) "A-FROZEN verdict rows present (got $($frozen.Count))"
$frozenClean = @($frozen | Where-Object { $verdicts[$_].hi -eq 'none' })
Assert-True ($frozenClean.Count -eq 0) `
    "A-FROZEN (the live v2.54.4 layout) must FAIL at every tier above 1x"

# 2c - the two counterexamples that passed the PREVIOUS revision with zero
# failures must now fail I4. Losing either one means the plot-clearance clause
# has regressed to reading the wrong edge - the exact hole that let them
# through, and the fifth instance of "a reserve that does not match what is
# drawn", which is #57 itself.
foreach ($k in @('H-EARLYCHART', 'G-CBOXFREE')) {
    $rows = @($verdicts.Keys | Where-Object { $_ -like "$k|*checkbox" })
    Assert-True ($rows.Count -eq 2) "$k checkbox verdict rows present"
    foreach ($r in $rows) {
        $inv = ($verdicts[$r].hi + ',' + $verdicts[$r].f1) -split ','
        Assert-True ($inv -contains 'I4') "$k must FAIL I4 ($r -> $($verdicts[$r].hi))"
    }
}

# 2d - the CERTIFIED candidate must be clean at every tier and both
# hypotheses. This is the line the acceptance targets rest on.
$e2 = @($verdicts.Keys | Where-Object { $_ -like 'E2-FONTBOX|*' })
Assert-True ($e2.Count -eq 4) "E2-FONTBOX verdict rows present"
foreach ($r in $e2) {
    Assert-True ($verdicts[$r].hi -eq 'none' -and $verdicts[$r].f1 -eq 'none') `
        "E2-FONTBOX must pass everything ($r -> f1=$($verdicts[$r].f1) hi=$($verdicts[$r].hi))"
}

# 4 - the four-status accounting must still be printed, and SKIP/UNDECIDED
# must never be folded into PASS.
$cnt = $out | Where-Object { $_ -match 'invariant checks\s+(\d+)\s+\(PASS (\d+), FAIL (\d+), SKIP (\d+), UNDECIDED (\d+)\)' } | Select-Object -First 1
Assert-True ($null -ne $cnt) "gate prints PASS/FAIL/SKIP/UNDECIDED counts"
if ($cnt -match 'invariant checks\s+(\d+)\s+\(PASS (\d+), FAIL (\d+), SKIP (\d+), UNDECIDED (\d+)\)') {
    $tot = [int]$Matches[1]; $p = [int]$Matches[2]; $fl = [int]$Matches[3]
    $sk = [int]$Matches[4]; $ud = [int]$Matches[5]
    Assert-True (($p + $fl + $sk + $ud) -eq $tot) `
        "the four statuses account for every check ($p+$fl+$sk+$ud vs $tot)"
    Assert-True ($fl -gt 0) `
        "the gate must still be FAILING the defective candidates (fail=$fl)"
    Write-Host ("   checks {0}: pass {1}, fail {2}, skip {3}, undecided {4}" -f $tot, $p, $fl, $sk, $ud)
}

# 4b - every non-pass must carry a NAMED reason. A bare skip count is a place
# for an unknown to hide.
Assert-True ($joined -match 'U1 lineH unknown at this tier') "U1 skips are named"
Assert-True ($joined -match 'R3 no measured advance for a glyph') "R3 skips are named"
Assert-True ($joined -match 'U8 winW\(1\.5\) frame ambiguity') "U8 skips are named"

# ---- the acceptance targets, echoed so a red run is actionable -----------
Write-Host ""
Write-Host "   ACCEPTANCE TARGETS (chart-local px):" -ForegroundColor Yellow
$inT = $false
foreach ($line in $out) {
    if ($line -match 'ACCEPTANCE TARGETS') { $inT = $true; continue }
    if ($inT) {
        if ($line -match '^\s*$') { break }
        if ($line -match '^\s*(tier|1x|1\.5x|2x|3x)\s') { Write-Host ("   " + $line.Trim()) }
    }
}

# ---- 3: is it an instrument? --------------------------------------------
Write-Host ""
Write-Host "3  the mutation audit (--mutate)" -ForegroundColor Yellow
$mut = & python $prover --mutate
$mrc = $LASTEXITCODE
Assert-True ($mrc -eq 0) "prove_chart_legend.py --mutate exits 0 (got $mrc)"
$mline = $mut | Where-Object { $_ -match 'mutations behaving correctly: (\d+)/(\d+)' } | Select-Object -First 1
Assert-True ($null -ne $mline) "mutation suite prints its tally"
if ($mline -match 'mutations behaving correctly: (\d+)/(\d+)') {
    $mok = [int]$Matches[1]; $mn = [int]$Matches[2]
    Assert-True ($mn -ge 22) "mutation suite still covers >=22 mutations (got $mn)"
    Assert-True ($mok -eq $mn) "every mutation behaves correctly ($mok/$mn)"
    Write-Host ("   mutations {0}/{1}" -f $mok, $mn)
}
$wrong = @($mut | Where-Object { $_ -match 'WRONG WAY' })
Assert-True ($wrong.Count -eq 0) "no mutation went the wrong way"
$crash = @($mut | Where-Object { $_ -match 'CRASHED' })
Assert-True ($crash.Count -eq 0) "no mutation crashed (a crash is not a pass)"

Write-Host ""
if ($script:Fail -eq 0) {
    Write-Host ("ALL PASS ({0} assertions)" -f $script:Pass) -ForegroundColor Green
    exit 0
} else {
    Write-Host ("{0} FAILED / {1} passed" -f $script:Fail, $script:Pass) -ForegroundColor Red
    Write-Host "See _tests\REGRESSION.md -> CHART LEGEND MATH (#57) for the runbook." -ForegroundColor Red
    exit 1
}
