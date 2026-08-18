# Regression: the STAGE 4 diff harness (tools\uimap\diff) still runs, still
# agrees with the DLL's own scale arithmetic, and still reports no NEW
# unexplained 1x/over-scaled window in the current session log.
#
# OFFLINE. Never launches, attaches to or kills SimCity 4; the game's log is
# read only. Safe to run at any time, including while the game is running.
#
# WHAT IT PROVES (reasoning + findings:
# tools\research\_checkpoints\uimap-stage4-diff.md):
#   1. parse_log.py still understands the log format. If a UiSpike.cpp printf
#      changes, the instrument count collapses and this fails LOUDLY instead
#      of silently measuring nothing.
#   2. Every `panel`/`dialog scaled` transition satisfies the sweep's own
#      edge-derived law  newW = round(f*(l+w)) - round(f*l)  (UiSpike.cpp:6478).
#      A failure here is an arithmetic defect, not a cosmetic one.
#   3. No window is left at stock size, or scaled twice, without an
#      explanation (pre-sweep timing, a never-scale list, a generic id, or
#      the render resolution).
#
# The $KNOWN list below is deliberate, exactly like Test-DatIntegrity.ps1's
# EXPECTED table: extending it is an act, not an accident, and every entry
# carries its reason. Remove an entry in the same commit as the fix that
# settles it.
#
# PASS = exit 0, "ALL PASS".
$ErrorActionPreference = "Stop"
$proj = Split-Path $PSScriptRoot -Parent
$diff = Join-Path $proj "tools\uimap\diff"

# ---- BASELINE ---------------------------------------------------------------
# Known-and-explained window ids, keyed BY ID rather than by a count. A count
# is worthless here: the log is rewritten every launch and grows while the
# user plays, so which windows happen to be captured varies per session. An
# id list is stable, and it forces every entry to carry its reason - the same
# discipline as Test-DatIntegrity.ps1's EXPECTED table.
#
# ANY id not listed here is a FAILURE. Adding one is a deliberate act: state
# the evidence, and remove it when the finding is settled.
$KNOWN = @{
  # Building Style Control content window, seen once at the MOD's 1x 519x654
  # where f=2 demands 1038x1308 (checkpoint FINDING 2). ONE DPROBE sample,
  # flagged NEW, no later sighting - so pre-sweep is not ruled out and this is
  # HYPOTHESIS, not a confirmed defect. Settle it by aiming the [Probe] band at
  # the panel and doing a FIRST-open per city load; then delete this entry.
  "0xEBC619DC" = "Building Style Control at mod-1x 519x654 - unconfirmed, see checkpoint FINDING 2"
}
# Instruments that must still parse out of the current log. A DROP means a
# printf changed in UiSpike.cpp and the harness has gone blind.
$REQUIRE_INSTRUMENTS = @("MWKID", "VWKID", "RGKID", "DPROBE")

$failures = @()
$notes = @()

# ---- pre-flight -------------------------------------------------------------
$py = (Get-Command python -ErrorAction SilentlyContinue)
if (-not $py) {
  Write-Output "SKIP: python not on PATH - the diff harness cannot run."
  exit 0
}
foreach ($f in @("parse_log.py", "diff.py")) {
  if (-not (Test-Path (Join-Path $diff $f))) { $failures += "missing tools\uimap\diff\$f" }
}
if ($failures.Count -gt 0) {
  $failures | ForEach-Object { Write-Output ("FAIL: " + $_) }
  exit 1
}

# The log lives under the user's Documents, which is OneDrive-REDIRECTED on
# this machine (C:\Users\<u>\Documents does not exist). Resolve it.
$docs = [Environment]::GetFolderPath('MyDocuments')
$log = Join-Path $docs "SimCity 4\Plugins\SC4UIScale.log"
if (-not (Test-Path $log)) {
  Write-Output "SKIP: no SC4UIScale.log at $log - play a session first."
  exit 0
}

# The log is REWRITTEN each launch and grows while the user plays, so a run
# taken mid-session is a snapshot of a moving target. Say so rather than let a
# transient mid-sweep capture look like a regression.
$age = (Get-Date) - (Get-Item $log).LastWriteTime
if ($age.TotalMinutes -lt 2) {
  $notes += ("NOTE: SC4UIScale.log was written " +
             [int]$age.TotalSeconds + "s ago - a session is probably LIVE. " +
             "Mid-sweep captures can appear here and clear on the next run.")
}

# ---- run it -----------------------------------------------------------------
Push-Location $diff
try {
  $out = & python diff.py --auto --resume --write-findings 2>&1
  $rc = $LASTEXITCODE
} finally {
  Pop-Location
}
if ($rc -ne 0) {
  $failures += "diff.py exited $rc"
  $out | ForEach-Object { Write-Output ("  | " + $_) }
}

$reportPath = Join-Path $diff "report.json"
if (-not (Test-Path $reportPath)) {
  Write-Output "FAIL: diff.py produced no report.json"
  exit 1
}
$report = Get-Content $reportPath -Raw | ConvertFrom-Json

# ---- 1. the parser still understands the log --------------------------------
$current = $report.inputs.logs | Where-Object { $_.name -eq "SC4UIScale.log" }
if (-not $current) {
  $failures += "the current SC4UIScale.log is not in the report inputs"
} else {
  $notes += ("log " + $current.name + " " + $current.version +
             " f=" + $current.factor + " (" + $current.records + " records, " +
             $current.events + " events)")
  if ($current.records -lt 1) { $failures += "SC4UIScale.log parsed to ZERO window records - the log format may have changed" }
}

$censusPath = Join-Path $diff "census\SC4UIScale_log.census.json"
if (Test-Path $censusPath) {
  $census = Get-Content $censusPath -Raw | ConvertFrom-Json
  $seen = @($census.counts.PSObject.Properties.Name)
  foreach ($i in $REQUIRE_INSTRUMENTS) {
    if ($seen -notcontains $i) {
      $failures += "instrument $i produced no lines - check its printf in src\UiSpike.cpp"
    }
  }
}

# ---- 2. the DLL's own scale arithmetic --------------------------------------
$evMismatch = 0
if ($report.summary.event_check.PSObject.Properties.Name -contains "MISMATCH") {
  $evMismatch = [int]$report.summary.event_check.MISMATCH
}
$evMatch = 0
if ($report.summary.event_check.PSObject.Properties.Name -contains "MATCH") {
  $evMatch = [int]$report.summary.event_check.MATCH
}
$notes += "scale-event transitions: $evMatch MATCH, $evMismatch MISMATCH"
if ($evMismatch -gt 0) {
  $failures += "$evMismatch scale event(s) do NOT satisfy the sweep's edge-derived law"
  $report.event_check | Where-Object { $_.verdict -eq "MISMATCH" } |
    Select-Object -First 10 | ForEach-Object {
      $failures += ("  " + $_.id + " " + $_.kind + " stock " +
                    $_.stock_rect.w + "x" + $_.stock_rect.h + " -> live " +
                    $_.live_rect.w + "x" + $_.live_rect.h + " expected " +
                    $_.expect_edge[0] + "x" + $_.expect_edge[1])
    }
}

# ---- 3. unexplained geometry in the CURRENT log -----------------------------
$bad = @($report.live_vs_stock | Where-Object {
  $_.log -eq "SC4UIScale.log" -and
  ($_.verdict -eq "STOCK-1X" -or $_.verdict -eq "OVER-SCALED" -or
   $_.verdict -eq "MISMATCH" -or $_.verdict -like "RECURRING-*")
})
$new = @($bad | Where-Object { -not $KNOWN.ContainsKey($_.id) })
$notes += ("unexplained geometry: " + $bad.Count + " row(s), " +
           $new.Count + " on ids NOT in the known list")
if ($new.Count -gt 0) {
  $failures += ("" + $new.Count + " unexplained window(s) on ids not in `$KNOWN")
  $new | Select-Object -First 15 | ForEach-Object {
    $failures += ("  " + $_.verdict + " " + $_.id + " " + $_.instr +
                  " live " + $_.live[0] + "x" + $_.live[1] +
                  " stock " + $_.stock[0] + "x" + $_.stock[1] +
                  " expected " + $_.expected[0] + "x" + $_.expected[1])
  }
  $failures += ("  (if one of these is a known-good content-sized or " +
                "pre-sweep window, add it to `$KNOWN WITH ITS REASON - " +
                "never raise a bare count)")
}
# A RECURRING row is the law-14 revert class and is never acceptable at any
# baseline - it means a window was correct and went back to 1x.
$recur = @($bad | Where-Object { $_.verdict -like "RECURRING-*" })
if ($recur.Count -gt 0) {
  $failures += ("" + $recur.Count + " RECURRING row(s) - a window reverted " +
                "AFTER being scaled (REGRESSION.md law 14). Never baseline these.")
}

# ---- 4. tier generality (offline, no game, no 1.5x session) -----------------
# The runtime sweep's edge law and the data generators' direct law are the
# same function at integer f and diverge at 1.5x. Assert that stays true: a
# divergence appearing at 2x or 3x would mean one of the two laws changed.
foreach ($t in @("1", "2", "3")) {
  $s = $report.tier_sweep.$t
  if ($s -and [int]$s.divergent_pairs -ne 0) {
    $failures += ("tier " + $t + "x: edge and direct laws diverge on " +
                  $s.divergent_pairs + " pairs - they must agree at integer f")
  }
}
$s15 = $report.tier_sweep."1.5"
if ($s15) { $notes += ("1.5x edge-vs-direct divergent pairs: " + $s15.divergent_pairs +
                       " (expected non-zero - this is the tier trap)") }

# ---- 5. the predicted model (stages 1-3) ------------------------------------
# MUST NOT FAIL when the model does not exist yet - this suite has to be
# addable to the runbook before stages 1-3 land.
if (-not $report.summary.model_available) {
  $notes += ("model join SKIPPED: " + $report.inputs.model.reason)
} else {
  $notes += ("model join: " + $report.summary.missing_from_model +
             " live windows absent from the model, " +
             $report.summary.missing_from_live + " modelled windows never seen live")
}

# ---- verdict ----------------------------------------------------------------
$notes | ForEach-Object { Write-Output ("  " + $_) }
if ($failures.Count -eq 0) {
  Write-Output ("ALL PASS (" + $evMatch + " scale events verified, " +
                $bad.Count + " unexplained row(s), all on known ids, " +
                "tier laws consistent)")
  exit 0
}
$failures | ForEach-Object { Write-Output ("FAIL: " + $_) }
exit 1
