# Paths are RESOLVED, not hard-coded: Documents may be redirected by
# OneDrive, and the repo may be cloned anywhere (task #108).
# #104 rate table. Reads the append-only SC4UIScale-104.csv the DLL writes and
# reports SPUN/total per CONFIGURATION.
#
# WHY THIS EXISTS: #104 is INTERMITTENT. On 2026-08-03 two runs with identical
# patch flags and identical user actions gave opposite outcomes. The original
# 13-run bisect gave each config ONE trial, so its "CLEAN" verdicts were coin
# flips, not evidence, and the culprit pair it named is NOT established. Only
# rates can decide it, and rates only get collected if ordinary play supplies
# them.
#
# READING THE ROWS (two-row protocol, see SpinProbe.h):
#   pending + a later 'spun' row for the same launchId -> SPUN
#   pending with NO spun row                           -> CLEAN (process exited)
#   unknown                                            -> probe was DISARMED;
#       nothing could have detected a spin, so it is NOT counted either way.
#       Counting a disarmed launch as clean is exactly the bias that made the
#       bisect wrong.
param(
    [string]$Csv = (Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'SimCity 4\Plugins-SC4UIScale\SC4UIScale-104.csv')
)
$ErrorActionPreference = "Stop"

if (-not (Test-Path $Csv)) {
    Write-Output "no data yet: $Csv"
    Write-Output "Set [UiSpike] SpinProbe to a nonzero number of seconds and play normally."
    exit 0
}

$rows = Import-Csv $Csv
# v2.59.0 and earlier re-emitted the header before every row (an _ftelli64
# quirk on "ab" handles, fixed in v2.59.2). Import-Csv then hands those back as
# DATA rows whose fields are the column names, which blew up the [int] cast.
# Drop them rather than requiring the old files to be edited - the historical
# rows are real measurements and must stay readable.
$rows = $rows | Where-Object { $_.launchId -and $_.launchId -ne 'launchId' }
if (-not $rows -or @($rows).Count -eq 0) { Write-Output "file present but no data rows"; exit 0 }

$byLaunch = $rows | Group-Object launchId
$records = foreach ($g in $byLaunch) {
    $first = $g.Group[0]
    $spun = @($g.Group | Where-Object { $_.verdict -eq 'spun' }).Count -gt 0
    $armed = @($g.Group | Where-Object { $_.verdict -eq 'pending' }).Count -gt 0
    [pscustomobject]@{
        launchId = $g.Name
        localTime = $first.localTime
        version = $first.version
        config = ("ord={0} dept={1} btn={2} all={3}" -f `
            $first.ordinanceInset, $first.budgetDept, $first.budgetButton, $first.scaleAll)
        budgetSeen = [int]$first.budgetSeen
        armed = $armed
        outcome = if (-not $armed) { "UNCOUNTED(probe off)" } elseif ($spun) { "SPUN" } else { "CLEAN" }
        detail = (($g.Group | Where-Object { $_.verdict -eq 'spun' } | Select-Object -First 1).detail)
    }
}

Write-Output "=== per-launch ==="
$records | Sort-Object localTime | Format-Table localTime, version, config, budgetSeen, outcome, detail -AutoSize | Out-String -Width 200

$counted = $records | Where-Object { $_.armed }
Write-Output "=== rate by config x budgetSeen (armed launches only) ==="
if ($counted.Count -eq 0) {
    Write-Output "NO ARMED LAUNCHES YET - every row had the probe disabled, so nothing is decidable."
} else {
    $counted | Group-Object { "$($_.config) budgetSeen=$($_.budgetSeen)" } | ForEach-Object {
        $n = $_.Count
        $s = @($_.Group | Where-Object { $_.outcome -eq 'SPUN' }).Count
        $pct = if ($n) { [math]::Round(100.0 * $s / $n, 0) } else { 0 }
        "{0,-52}  {1,2}/{2,-2} spun ({3}%)" -f $_.Name, $s, $n, $pct
    }
    Write-Output ""
    $tot = $counted.Count
    $totSpun = @($counted | Where-Object { $_.outcome -eq 'SPUN' }).Count
    Write-Output ("overall: {0}/{1} armed launches spun" -f $totSpun, $tot)
    Write-Output ""
    Write-Output "NOTE ON SAMPLE SIZE: with an intermittent failure, a config with 0 spins in"
    Write-Output "a handful of trials is NOT established clean. At a true 50% rate, 4 clean"
    Write-Output "runs in a row happen 6% of the time; at 25%, 32% of the time. Do not repeat"
    Write-Output "the bisect's mistake of reading a small clean streak as a verdict."
}
