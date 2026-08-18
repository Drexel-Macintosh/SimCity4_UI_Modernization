<#
  Trace-CityOpen.ps1 - sample SimCity 4's CPU / disk / memory while you open
  cities, so "the FIRST city open of a session is slow" becomes a measurement
  instead of folklore.

  WHY THIS SHAPE. The question is not "is it slow" but "slow doing WHAT".
  Three candidates produce very different traces:

    * DISK-bound   -> ReadTransferCount climbs hard, CPU stays low
    * CPU-bound    -> UserModeTime climbs, disk quiet (note: SC4CPUOptions
                      pins the game to ONE core, so 100% of one core is the
                      ceiling and will look like ~6% of a 16-thread machine)
    * PAGE-FAULTS  -> PageFaults climbs (memory pressure / first touch of the
                      1.2 GB of plugin data NAM loads)

  A first-open-only cost is a ONE-TIME WARM-UP: something built on first use
  and reused afterwards. The trace shows which resource pays for it.

  ⚠ NEVER kills or touches the game - it only READS counters. The game runs
  elevated; this script does not need to.

    .\Trace-CityOpen.ps1                      trace until you press Q
    .\Trace-CityOpen.ps1 -IntervalMs 250
    .\Trace-CityOpen.ps1 -Summarize <csv>     re-analyse an earlier run

  SUGGESTED RUN: start this, launch the game, open a city (that's OPEN #1),
  go back to region, open a DIFFERENT city (OPEN #2). Two opens in one
  session is the whole experiment - #1 vs #2 is the answer.
#>
[CmdletBinding()]
param(
    [int]    $IntervalMs = 500,
    # Non-interactive runs (background / redirected stdin) cannot read a
    # keypress - Console.KeyAvailable THROWS there. Use a duration instead and
    # the trace ends on its own.
    [int]    $DurationSeconds = 0,
    [string] $Summarize,
    # $PSScriptRoot is EMPTY when a param default is evaluated under some
    # `powershell -File` invocations, which silently wrote the first trace to
    # C:\captures instead of the project. Resolve it at runtime with a fallback.
    [string] $OutDir
)

if (-not $OutDir) {
    $root = $PSScriptRoot
    if (-not $root) { $root = Split-Path -Parent $MyInvocation.MyCommand.Path }
    if (-not $root) { $root = (Get-Location).Path }
    $OutDir = Join-Path $root "captures"
}

$ErrorActionPreference = "Stop"

function Show-Summary($rows) {
    if ($rows.Count -lt 3) { Write-Output "not enough samples"; return }
    Write-Output ""
    Write-Output "=== BUSIEST 500ms WINDOWS (top 12 by CPU+disk) ==="
    Write-Output ("{0,-12} {1,8} {2,10} {3,12} {4,10} {5,10}" -f `
        "t(s)", "cpu_ms", "readOps", "readMB", "pgFaults", "wsMB")
    $rows | Sort-Object { -($_.dCpuMs + $_.dReadMB * 10) } | Select-Object -First 12 |
        Sort-Object t | ForEach-Object {
            Write-Output ("{0,-12:N1} {1,8:N0} {2,10:N0} {3,12:N2} {4,10:N0} {5,10:N0}" -f `
                $_.t, $_.dCpuMs, $_.dReadOps, $_.dReadMB, $_.dFaults, $_.wsMB)
        }

    $tot = [pscustomobject]@{
        cpu    = ($rows | Measure-Object dCpuMs  -Sum).Sum
        readMB = ($rows | Measure-Object dReadMB -Sum).Sum
        ops    = ($rows | Measure-Object dReadOps -Sum).Sum
        faults = ($rows | Measure-Object dFaults -Sum).Sum
    }
    $span = $rows[-1].t - $rows[0].t
    Write-Output ""
    Write-Output ("=== TOTALS over {0:N0}s: cpu {1:N0}ms  read {2:N0}MB in {3:N0} ops  pageFaults {4:N0} ===" -f `
        $span, $tot.cpu, $tot.readMB, $tot.ops, $tot.faults)

    # A "burst" = consecutive samples doing real work. First burst vs later
    # bursts is the first-open-vs-rest comparison.
    $burst = @(); $bursts = @()
    foreach ($r in $rows) {
        $busy = ($r.dCpuMs -gt 80) -or ($r.dReadMB -gt 1)
        if ($busy) { $burst += $r }
        elseif ($burst.Count -ge 3) { $bursts += ,$burst; $burst = @() }
        else { $burst = @() }
    }
    if ($burst.Count -ge 3) { $bursts += ,$burst }
    Write-Output ""
    Write-Output "=== WORK BURSTS (>=1.5s of sustained activity) ==="
    $i = 0
    foreach ($b in $bursts) {
        $i++
        $dur = $b[-1].t - $b[0].t
        if ($dur -lt 1.5) { continue }
        Write-Output ("  burst {0}: start {1,7:N1}s  dur {2,6:N1}s  cpu {3,7:N0}ms  read {4,8:N1}MB  ops {5,7:N0}  faults {6,9:N0}" -f `
            $i, $b[0].t, $dur,
            ($b | Measure-Object dCpuMs  -Sum).Sum,
            ($b | Measure-Object dReadMB -Sum).Sum,
            ($b | Measure-Object dReadOps -Sum).Sum,
            ($b | Measure-Object dFaults -Sum).Sum)
    }
    Write-Output ""
    Write-Output "READ IT LIKE THIS: compare the FIRST long burst (city open #1)"
    Write-Output "against the SECOND (city open #2). If #1 has far more readMB/ops"
    Write-Output "the cost is DISK; if far more cpu_ms it is PARSING/BUILDING; if"
    Write-Output "far more pageFaults it is first-touch of already-loaded data."
}

if ($Summarize) {
    Show-Summary (Import-Csv $Summarize | ForEach-Object {
        [pscustomobject]@{
            t = [double]$_.t; dCpuMs = [double]$_.dCpuMs; dReadOps = [double]$_.dReadOps
            dReadMB = [double]$_.dReadMB; dFaults = [double]$_.dFaults; wsMB = [double]$_.wsMB
        }
    })
    return
}

if (-not (Test-Path $OutDir)) { New-Item -ItemType Directory -Path $OutDir -Force | Out-Null }
$csv = Join-Path $OutDir ("cityopen-trace-{0}.csv" -f (Get-Date -Format "yyyyMMdd-HHmmss"))

Write-Output "Waiting for SimCity 4 ... (start the game now; Ctrl+C to abort)"
while (-not (Get-Process "SimCity 4" -ErrorAction SilentlyContinue)) { Start-Sleep -Milliseconds 400 }
$proc = Get-Process "SimCity 4"
Write-Output ("attached to pid {0}. Sampling every {1}ms -> {2}" -f $proc.Id, $IntervalMs, $csv)
Write-Output "Open a city (#1), return to region, open another (#2). Press Q here when done."

$rows = @()
$prev = $null
$t0 = Get-Date
while ($true) {
    if ($DurationSeconds -gt 0) {
        if (((Get-Date) - $t0).TotalSeconds -ge $DurationSeconds) {
            Write-Output "duration reached - stopping."
            break
        }
    } else {
        # guarded: throws when stdin is redirected
        try { if ([Console]::KeyAvailable) {
                $k = [Console]::ReadKey($true)
                if ($k.Key -eq 'Q') { break }
        } } catch { }
    }
    $w = Get-CimInstance Win32_Process -Filter "ProcessId=$($proc.Id)" -ErrorAction SilentlyContinue
    if (-not $w) { Write-Output "process gone - stopping."; break }
    $now = [pscustomobject]@{
        t      = ((Get-Date) - $t0).TotalSeconds
        cpuMs  = ([double]$w.KernelModeTime + [double]$w.UserModeTime) / 10000.0
        kernMs = ([double]$w.KernelModeTime) / 10000.0
        userMs = ([double]$w.UserModeTime) / 10000.0
        rdOps  = [double]$w.ReadOperationCount
        rdMB   = [double]$w.ReadTransferCount / 1MB
        faults = [double]$w.PageFaults
        wsMB   = [double]$w.WorkingSetSize / 1MB
    }
    if ($prev) {
        $rows += [pscustomobject]@{
            t        = [math]::Round($now.t, 2)
            dCpuMs   = [math]::Round($now.cpuMs  - $prev.cpuMs, 1)
            dKernMs  = [math]::Round($now.kernMs - $prev.kernMs, 1)
            dUserMs  = [math]::Round($now.userMs - $prev.userMs, 1)
            dReadOps = [math]::Round($now.rdOps  - $prev.rdOps, 0)
            dReadMB  = [math]::Round($now.rdMB   - $prev.rdMB, 3)
            dFaults  = [math]::Round($now.faults - $prev.faults, 0)
            wsMB     = [math]::Round($now.wsMB, 0)
        }
    }
    $prev = $now
    Start-Sleep -Milliseconds $IntervalMs
}

$rows | Export-Csv $csv -NoTypeInformation
Write-Output ("`nwrote {0} samples -> {1}" -f $rows.Count, $csv)
Show-Summary $rows
