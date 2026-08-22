# Paths are RESOLVED, not hard-coded: Documents may be redirected by
# OneDrive, and the repo may be cloned anywhere (task #108).
# LIVE regression: boots the game at each matrix resolution and asserts the
# AutoScale tier decision, on-disk package gating, and (at scaled tiers) the
# 9/9 region-panel scale from the log. Restores native 2400x1600 at the end.
# Takes ~10 minutes (kills/relaunches the game repeatedly - run only when
# that's acceptable). Log-based: works even when the screen is locked.
# PASS = exit 0, "ALL PASS".
$ErrorActionPreference = "Stop"
$plugins = (Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'SimCity 4\Plugins')
$gfx = "$plugins\SC4GraphicsOptions.ini"
$log = "$plugins\SC4UIScale.log"
$exe = "C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Apps\SimCity 4.exe"

# resolution -> expected tier + active package tag with the CURRENTLY
# shipped package set {1.5, 2, 3}. UPDATE when packages change.
$MATRIX = @(
  @{ w = 800;  h = 600;  tier = "1.00"; tag = $null },
  @{ w = 1920; h = 1080; tier = "1.50"; tag = "-15x" },
  @{ w = 1600; h = 1200; tier = "1.50"; tag = "-15x" },
  @{ w = 2400; h = 1600; tier = "2.00"; tag = "-2x" }
)
$ALL_TAGS = @("-15x", "-2x", "-3x")

function Read-Log {
  if (-not (Test-Path $log)) { return "" }
  $fs = [System.IO.FileStream]::new($log, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::ReadWrite)
  $sr = [System.IO.StreamReader]::new($fs); $c = $sr.ReadToEnd(); $sr.Close()
  return $c
}

function Boot-At([int]$w, [int]$h) {
  $p = Get-Process | Where-Object { $_.ProcessName -match "SimCity" }
  if ($p) { $p.Kill(); Start-Sleep -Seconds 4 }
  (Get-Content $gfx -Raw) -replace "WindowWidth=\d+", "WindowWidth=$w" -replace "WindowHeight=\d+", "WindowHeight=$h" | Set-Content $gfx -Encoding ASCII
  if (Test-Path $log) { Remove-Item $log -Force }
  Start-Process -FilePath $exe -WorkingDirectory (Split-Path $exe)
}

$failures = @()
foreach ($m in $MATRIX) {
  $scaled = $m.tier -ne "1.00"
  # NOTE: -match is case-insensitive; a short "Stock tier" marker falsely
  # matches ScaleTier's "(stock tier)" constructor line and samples the log
  # before PostAppInit. Use the full PostAppInit sentence.
  $doneMarker = if ($scaled) { "region panel 0x6A91DC14" } else { "Stock tier: UI-scaling subsystems not installed" }
  $label = "$($m.w)x$($m.h)"
  # Sub-native boots are flaky on the dev panel (known dgVoodoo issue, not
  # ours): retry the boot ONCE before failing - flake vs regression.
  $c = ""
  for ($attempt = 1; $attempt -le 2; $attempt++) {
    Boot-At $m.w $m.h
    $deadline = (Get-Date).AddSeconds(150)
    while ((Get-Date) -lt $deadline) {
      Start-Sleep -Seconds 3
      $c = Read-Log
      if ($c -match [regex]::Escape($doneMarker)) { break }
    }
    if ($c -match [regex]::Escape($doneMarker)) { break }
    Write-Output ("  $label attempt $attempt did not reach '$doneMarker' - " + $(if ($attempt -eq 1) { "retrying" } else { "giving up" }))
  }
  if ($c -notmatch ("AutoScale: $($m.w)x$($m.h) -> tier " + [regex]::Escape($m.tier))) {
    $failures += "$label - tier line missing/incorrect (expected $($m.tier))"
  }
  if ($scaled) {
    $panels = (($c -split "`r?`n") | Where-Object { $_ -match "region panel 0x" }).Count
    if ($panels -ne 9) { $failures += "$label - $panels/9 region panels" }
    foreach ($t in $ALL_TAGS) {
      $live = Test-Path "$plugins\z_SC4UIScale_SelectiveArt$t.dat"
      if ($t -eq $m.tag -and -not $live) { $failures += "$label - $t art dat should be LIVE" }
      if ($t -ne $m.tag -and $live) { $failures += "$label - $t art dat should be GATED" }
    }
    if (-not (Test-Path "$plugins\FontStyle.ini")) { $failures += "$label - FontStyle.ini not live" }
    elseif ($m.tag) {
      $liveHash = (Get-FileHash "$plugins\FontStyle.ini" -Algorithm SHA256).Hash
      $srcHash = (Get-FileHash "$plugins\FontStyle$($m.tag).ini" -Algorithm SHA256).Hash
      if ($liveHash -ne $srcHash) { $failures += "$label - live FontStyle.ini is not the $($m.tag) table" }
    }
  } else {
    if ($c -notmatch "Stock tier: UI-scaling subsystems not installed") {
      $failures += "$label - stock-inert line missing"
    }
    foreach ($t in $ALL_TAGS) {
      if (Test-Path "$plugins\z_SC4UIScale_SelectiveArt$t.dat") { $failures += "$label - $t art dat NOT gated at stock" }
    }
    if (Test-Path "$plugins\FontStyle.ini") { $failures += "$label - FontStyle.ini NOT removed at stock" }
  }
  Write-Output ("checked " + $label + " -> " + $(if ($failures.Count -eq 0) { "ok so far" } else { "issues: " + $failures.Count }))
}

# Restore native and confirm reactivation
Boot-At 2400 1600
$deadline = (Get-Date).AddSeconds(150)
$c = ""
while ((Get-Date) -lt $deadline) {
  Start-Sleep -Seconds 3
  $c = Read-Log
  if ($c -match "region panel 0x6A91DC14") { break }
}
$panels = (($c -split "`r?`n") | Where-Object { $_ -match "region panel 0x" }).Count
if ($panels -ne 9) { $failures += "final native restore - $panels/9 panels" }

if ($failures.Count -eq 0) { Write-Output "ALL PASS (boot matrix + native restore)"; exit 0 }
$failures | ForEach-Object { Write-Output ("FAIL: " + $_) }
exit 1
