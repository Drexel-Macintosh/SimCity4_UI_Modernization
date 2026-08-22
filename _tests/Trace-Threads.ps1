<#
  Trace-Threads.ps1 - PER-THREAD CPU during a SimCity 4 city load.

  THE QUESTION THIS ANSWERS, AND WHY IT COMES FIRST.
  Trace-CityOpen.ps1 measured the first city open at 54s wall / 53s CPU /
  934 MB in 1.9M reads. It summed CPU PROCESS-WIDE, which cannot distinguish
  "one thread pegged" from "four threads busy". That difference decides
  whether unpinning the CPU affinity can help AT ALL:

    * ONE hot thread  -> more cores change NOTHING for load time. The loader
                         is serial and no switch will parallelise it.
    * SEVERAL busy    -> the 1-core pin is a real serial bottleneck and
                         -CPUCount:2 is worth testing.

  Do not flip the affinity before running this. Unpinning SC4 has a long
  reputation for instability (it was pinned because 2003-era CPUs had
  unsynchronised RDTSC across cores), so it is only worth the risk if there
  is measurable concurrency to win.

  Samples every thread's UserModeTime+KernelModeTime via Win32_Thread, and
  reports how the busy time is DISTRIBUTED - the top thread's share is the
  whole answer.

  Read-only. Never touches the game.

    .\Trace-Threads.ps1 -DurationSeconds 600
    .\Trace-Threads.ps1 -Summarize <csv>
#>
[CmdletBinding()]
param(
    [int]    $IntervalMs = 1000,
    [int]    $DurationSeconds = 600,
    [string] $Summarize,
    [string] $OutDir
)

$ErrorActionPreference = "Stop"
if (-not $OutDir) {
    $root = $PSScriptRoot
    if (-not $root) { $root = Split-Path -Parent $MyInvocation.MyCommand.Path }
    if (-not $root) { $root = (Get-Location).Path }
    $OutDir = Join-Path $root "captures"
}

function Show-ThreadSummary($rows, $procCpuMs) {
    if (-not $rows -or $rows.Count -lt 2) { Write-Output "not enough samples"; return }

    # ⛔ POSITIVE CONTROL - ADDED 2026-08-05 AFTER THIS SCRIPT LIED.
    # Win32_Thread's KernelModeTime/UserModeTime return ~0 when the querying
    # shell is NOT elevated and the target process IS (SC4 runs under a
    # RUNASADMIN shim). The first run summed 20ms across 20 threads while the
    # process had burned 186,000ms - and this function then printed a
    # confident "ONE thread does all the work; unpinning CANNOT help".
    # That verdict was fabricated from noise.
    # A summary must RECONCILE against the process total or refuse to speak.
    $sum = ($rows | ForEach-Object { [double]$_.dCpuMs } | Measure-Object -Sum).Sum
    if ($procCpuMs -and $procCpuMs -gt 0) {
        $ratio = $sum / $procCpuMs
        Write-Output ("reconciliation: threads {0:N0}ms vs process {1:N0}ms = {2:P0}" -f $sum, $procCpuMs, $ratio)
        if ($ratio -lt 0.5) {
            Write-Output ""
            Write-Output "⛔ BROKEN INSTRUMENT - NO VERDICT."
            Write-Output "   Per-thread CPU is unreadable: the sums do not reconcile with the"
            Write-Output "   process total. Almost certainly because this shell is NOT elevated"
            Write-Output "   while SimCity 4 IS (RUNASADMIN shim), so per-thread times read 0."
            Write-Output "   RERUN THIS FROM AN ELEVATED POWERSHELL. Any thread split printed"
            Write-Output "   below would be noise divided by noise - do not use it."
            Write-Output ""
        }
    } else {
        Write-Output "reconciliation: process CPU total unavailable - treat the split as UNVERIFIED."
    }
    $byThread = @{}
    foreach ($r in $rows) {
        $k = [string]$r.tid
        if (-not $byThread.ContainsKey($k)) { $byThread[$k] = 0.0 }
        $byThread[$k] += [double]$r.dCpuMs
    }
    $total = ($byThread.Values | Measure-Object -Sum).Sum
    if ($total -le 0) { Write-Output "no CPU recorded"; return }

    Write-Output ""
    Write-Output "=== CPU BY THREAD (whole capture) ==="
    Write-Output ("{0,-12} {1,12} {2,9}" -f "tid", "cpu_ms", "share")
    $ranked = $byThread.GetEnumerator() | Sort-Object Value -Descending
    $i = 0
    foreach ($e in $ranked) {
        $i++
        if ($i -gt 12) { break }
        Write-Output ("{0,-12} {1,12:N0} {2,8:N1}%" -f $e.Key, $e.Value, (100 * $e.Value / $total))
    }
    $top = ($ranked | Select-Object -First 1).Value
    $top3 = (($ranked | Select-Object -First 3) | Measure-Object Value -Sum).Sum
    Write-Output ""
    Write-Output ("threads seen: {0}   total cpu {1:N0}ms" -f $byThread.Count, $total)
    Write-Output ("TOP THREAD SHARE : {0:N1}%" -f (100 * $top / $total))
    Write-Output ("TOP-3 SHARE      : {0:N1}%" -f (100 * $top3 / $total))
    Write-Output ""
    if ((100 * $top / $total) -gt 85) {
        Write-Output "VERDICT: ONE thread does essentially all the work."
        Write-Output "         Unpinning the CPU affinity CANNOT speed up the load."
        Write-Output "         The loader is serial; -CPUCount:2 would only add risk."
    } elseif ((100 * $top / $total) -lt 60) {
        Write-Output "VERDICT: work IS spread across threads. The 1-core pin is a real"
        Write-Output "         serial bottleneck - -CPUCount:2 is worth a careful test."
    } else {
        Write-Output "VERDICT: mixed. One dominant thread plus real secondary work;"
        Write-Output "         an extra core might win the secondary share only."
    }
}

if ($Summarize) { Show-ThreadSummary (Import-Csv $Summarize) $null; return }

if (-not (Test-Path $OutDir)) { New-Item -ItemType Directory -Path $OutDir -Force | Out-Null }
$csv = Join-Path $OutDir ("threads-{0}.csv" -f (Get-Date -Format "yyyyMMdd-HHmmss"))

Write-Output "Waiting for SimCity 4 ..."
while (-not (Get-Process "SimCity 4" -ErrorAction SilentlyContinue)) { Start-Sleep -Milliseconds 400 }
$pidSC = (Get-Process "SimCity 4").Id
Write-Output ("attached pid {0}; sampling threads every {1}ms for {2}s -> {3}" -f $pidSC, $IntervalMs, $DurationSeconds, $csv)

$rows = @()
$prev = @{}
$procCpu0 = $null
try { $procCpu0 = (Get-Process -Id $pidSC).TotalProcessorTime.TotalMilliseconds } catch {}
$procCpu1 = $procCpu0
$t0 = Get-Date
while (((Get-Date) - $t0).TotalSeconds -lt $DurationSeconds) {
    $th = Get-CimInstance Win32_Thread -Filter "ProcessHandle='$pidSC'" -ErrorAction SilentlyContinue
    if (-not $th) { Write-Output "process gone - stopping."; break }
    $t = ((Get-Date) - $t0).TotalSeconds
    foreach ($x in $th) {
        $tid = [string]$x.Handle
        $cpu = ([double]$x.KernelModeTime + [double]$x.UserModeTime) / 10000.0
        if ($prev.ContainsKey($tid)) {
            $d = $cpu - $prev[$tid]
            if ($d -gt 0) {
                $rows += [pscustomobject]@{ t = [math]::Round($t,1); tid = $tid; dCpuMs = [math]::Round($d,1) }
            }
        }
        $prev[$tid] = $cpu
    }
    try { $procCpu1 = (Get-Process -Id $pidSC -ErrorAction Stop).TotalProcessorTime.TotalMilliseconds } catch {}
    Start-Sleep -Milliseconds $IntervalMs
}

$rows | Export-Csv $csv -NoTypeInformation
Write-Output ("`nwrote {0} rows -> {1}" -f $rows.Count, $csv)
$procDelta = $null
if ($procCpu0 -ne $null -and $procCpu1 -ne $null) { $procDelta = $procCpu1 - $procCpu0 }
Show-ThreadSummary $rows $procDelta
