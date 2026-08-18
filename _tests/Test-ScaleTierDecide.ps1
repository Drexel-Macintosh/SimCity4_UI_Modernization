# Offline regression: the ScaleTier fit function (mirrors src\ScaleTier.cpp
# Decide()). Asserts the expected tier for every named target resolution and
# the fit invariant over a deterministic random sweep. No game needed.
# PASS = exit 0 and "ALL PASS" on stdout.
param(
  # Installed package factors to evaluate against. Default = what currently
  # ships. Update alongside kPackages/package deployments.
  [double[]]$Installed = @(2.0)
)

$ErrorActionPreference = "Stop"
$failures = @()

function Decide([int]$w, [int]$h, [double[]]$installed) {
  if ($w -le 0 -or $h -le 0) { return 1.0 }
  $cap = [Math]::Min($w / 800.0, $h / 600.0)
  foreach ($n in ($installed | Sort-Object -Descending)) {
    if ((880 * $n -le $w) -and (558 * $n -le $h) -and ($n -le $cap)) { return $n }
  }
  return 1.0
}

# Expected outcomes with the DEFAULT installed set {2.0}. If you pass a
# different -Installed, use -SkipNamed to only run the invariant sweep.
$named = @(
  @{ w = 800;  h = 600;  expect = 1.0 },
  @{ w = 1024; h = 768;  expect = 1.0 },
  @{ w = 1280; h = 1024; expect = 1.0 },
  @{ w = 1600; h = 1200; expect = 1.0 },
  @{ w = 1920; h = 1080; expect = 1.0 },
  @{ w = 2400; h = 1600; expect = 2.0 },
  @{ w = 2560; h = 1440; expect = 2.0 },
  @{ w = 3840; h = 2160; expect = 2.0 },
  @{ w = 7680; h = 4320; expect = 2.0 }
)
# Expected outcomes once the full package set {1.5,2,3,4} ships:
$namedFuture = @(
  @{ w = 1600; h = 1200; expect = 1.5 },
  @{ w = 1920; h = 1080; expect = 1.5 },
  @{ w = 2560; h = 1440; expect = 2.0 },
  @{ w = 3840; h = 2160; expect = 3.0 },
  @{ w = 7680; h = 4320; expect = 4.0 }
)

# NOTE: as of 2026-07-22 the SHIPPED set is {1.5, 2, 3} - the $named table
# below documents the historical {2}-only expectations and still validates
# the function's behavior for that configuration.
foreach ($t in $named) {
  $got = Decide $t.w $t.h @(2.0)
  if ($got -ne $t.expect) { $failures += "named {0}x{1} installed={{2}}: got $got expect $($t.expect)" -f $t.w, $t.h }
}
# The shipped set {1.5, 2, 3}:
$namedShipped = @(
  @{ w = 800;  h = 600;  expect = 1.0 },
  @{ w = 1280; h = 1024; expect = 1.0 },
  @{ w = 1600; h = 1200; expect = 1.5 },
  @{ w = 1920; h = 1080; expect = 1.5 },
  @{ w = 2400; h = 1600; expect = 2.0 },
  @{ w = 2560; h = 1440; expect = 2.0 },
  @{ w = 3840; h = 2160; expect = 3.0 },
  @{ w = 7680; h = 4320; expect = 3.0 }
)
foreach ($t in $namedShipped) {
  $got = Decide $t.w $t.h @(1.5, 2.0, 3.0)
  if ($got -ne $t.expect) { $failures += "shipped {0}x{1}: got $got expect $($t.expect)" -f $t.w, $t.h }
}
foreach ($t in $namedFuture) {
  $got = Decide $t.w $t.h @(1.5, 2.0, 3.0, 4.0)
  if ($got -ne $t.expect) { $failures += "future {0}x{1}: got $got expect $($t.expect)" -f $t.w, $t.h }
}

# Fit invariant: a chosen factor > 1 must always FIT (never overflow).
$rng = New-Object System.Random 42
for ($i = 0; $i -lt 5000; $i++) {
  $w = $rng.Next(320, 9000); $h = $rng.Next(240, 6000)
  foreach ($set in @(, @(2.0)), @(, @(1.5, 2.0, 3.0, 4.0))) {
    $n = Decide $w $h $set[0]
    if ($n -gt 1.0 -and ((880 * $n -gt $w) -or (558 * $n -gt $h))) {
      $failures += "fit violation ${w}x${h} set=$($set[0] -join ',') chose $n"
    }
  }
}

if ($failures.Count -eq 0) {
  Write-Output "ALL PASS (14 named cases + 5000x2 random fit sweep)"
  exit 0
} else {
  $failures | ForEach-Object { Write-Output ("FAIL: " + $_) }
  exit 1
}
