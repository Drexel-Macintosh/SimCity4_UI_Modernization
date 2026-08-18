# Regression: every id in SCALED_WINDOW_IDS has a born-correct route.
#
# WHY THIS EXISTS
# ---------------
# The law (UiSpike.cpp, search "IF WE SHIP 2x ART FOR A PANEL"): if the data
# builder ships 2x art/scripts for a window id, the DLL must scale that window
# BEFORE the user can see it at 1x - via one of the born-correct routes or via
# a mechanism of its own (flyout open-funnel / born-at-Place). Task #90 found
# the law had been violated silently: 0xABC619D2 (Building Style Control) was
# in SCALED_WINDOW_IDS with NO route at all, so its first-ever open flashed 1x.
# Nothing caught it because nothing cross-checked the two files. This test is
# that cross-check.
#
# WHAT COUNTS AS COVERED
# ----------------------
#   born-correct  kAlwaysScaleCityIds / kRegionPanelIds / kGodPanelIds
#                 (sweep visibility-gate bypass, generation 2) and
#                 kDataScaledSubtreeIds (data pre-scale, generation 3).
#   own mechanism kSubFlyoutIds, kGodToolFlyoutIds, kMayorFlyoutDock - these
#                 are scaled by the flyout open-funnel / dock machinery, NOT
#                 born-correct. They pass but are LABELED, so a future id
#                 that is only skip-listed does not get silently blessed.
#
# PARSING RULES (each one is a measured trap, do not "simplify")
# --------------------------------------------------------------
#   * SCALED_WINDOW_IDS must be AST-parsed via python. Comments inside the set
#     literal embed hex ids (e.g. "{46a006b0,14415870}") - a naive regex read
#     16 ids instead of 50 (measured 2026-08-01).
#   * UiSpike.cpp arrays: strip // comments BEFORE harvesting hex - comment
#     text cites OTHER windows' ids.
#   * kMayorFlyoutDock rows are structs { id, buttonId, dx, dy, ... } - only
#     the FIRST hex per row is a window id; the second is a BUTTON id.
#   * Hard-fail on any empty parse (the anti-drift guard, per
#     Test-ThirdPartyGates.ps1).
#
# OFFLINE. Never launches, attaches to or kills SimCity 4. Reads only.
# PASS = exit 0, "ALL PASS".
$ErrorActionPreference = "Stop"
$proj = Split-Path $PSScriptRoot -Parent
$pyFile  = Join-Path $proj "tools\selective-safe\build_selective_safe.py"
$cppFile = Join-Path $proj "src\UiSpike.cpp"

foreach ($f in @($pyFile, $cppFile)) {
    if (-not (Test-Path $f)) { Write-Output "FAIL: $f not found"; exit 1 }
}

# --- 1. SCALED_WINDOW_IDS via python AST (comments are invisible to ast) ----
# Single quotes ONLY inside the python code: PS 5.1 native-arg passing eats
# unescaped double quotes (measured - the first run got "unterminated string").
$astScript = @'
import ast, sys
tree = ast.parse(open(sys.argv[1], encoding='utf-8').read())
out = []
for node in ast.walk(tree):
    if isinstance(node, ast.Assign):
        for t in node.targets:
            if getattr(t, 'id', '') == 'SCALED_WINDOW_IDS':
                for c in ast.walk(node.value):
                    if isinstance(c, ast.Constant) and isinstance(c.value, int):
                        out.append(c.value)
print(chr(10).join('%08X' % v for v in out))
'@
$scaledRaw = & python -c $astScript $pyFile
if ($LASTEXITCODE -ne 0) { Write-Output "FAIL: python AST parse errored"; exit 1 }
$scaledAll = @($scaledRaw | Where-Object { $_ -match '^[0-9A-F]{8}$' })
if ($scaledAll.Count -eq 0) { Write-Output "FAIL: SCALED_WINDOW_IDS parsed as empty"; exit 1 }
# A duplicate literal is invisible to python (set dedups) but means two
# comment blocks claim the same id - drift bait. Warn, don't fail.
$scaled = @($scaledAll | Select-Object -Unique)
if ($scaledAll.Count -ne $scaled.Count) {
    $scaledAll | Group-Object | Where-Object Count -gt 1 | ForEach-Object {
        Write-Output ("  WARN: 0x{0} appears {1}x in the SCALED_WINDOW_IDS literal - remove the duplicate entry" -f $_.Name, $_.Count)
    }
}
# Truncation guard: the set held 50 ids when this test was written. A count
# far below that means the parse silently broke, not that the set shrank.
if ($scaled.Count -lt 40) {
    Write-Output ("FAIL: SCALED_WINDOW_IDS parsed only {0} ids (expected ~50) - parse truncated?" -f $scaled.Count); exit 1
}
Write-Output ("Parsed SCALED_WINDOW_IDS: {0} ids (python AST)" -f $scaled.Count)

# --- 2. UiSpike.cpp id arrays ----------------------------------------------
$cpp = Get-Content $cppFile -Raw

function Get-CppArrayIds {
    param([string]$Name, [switch]$FirstPerRow)
    # Multi-line arrays close with "\n\t};" (one-tab indent). That terminator
    # is immune to "};" INSIDE comments (real: UiSpike.cpp ~:3223 embeds
    # "{46a006b0,82b99d9d};" in a comment), which is why the generic "};" is
    # only a fallback. But it cannot match a SINGLE-LINE array (kSubFlyoutIds)
    # - the first run of this test overran into the NEXT array and parsed 34
    # ids from a 1-entry list. The overrun guard below catches that shape.
    $m = [regex]::Match($script:cpp, [regex]::Escape($Name) + '\[\]\s*=\s*\{(?<body>.*?)\n\t\};', 'Singleline')
    if ($m.Success -and $m.Groups['body'].Value -match '\[\]\s*=\s*\{') { $m = $null }  # overran into the next array
    if (-not $m -or -not $m.Success) {
        $m = [regex]::Match($script:cpp, [regex]::Escape($Name) + '\[\]\s*=\s*\{(?<body>.*?)\};', 'Singleline')
    }
    if (-not $m -or -not $m.Success) { Write-Output "FAIL: could not find array $Name in UiSpike.cpp"; exit 1 }
    if ($m.Groups['body'].Value -match '\[\]\s*=\s*\{') { Write-Output "FAIL: parse of $Name overran into another array"; exit 1 }
    $ids = @()
    foreach ($line in ($m.Groups['body'].Value -split "`n")) {
        $code = ($line -replace '//.*$', '')          # comments cite other ids
        if ($FirstPerRow) {
            $r = [regex]::Match($code, '\{\s*0[xX]([0-9A-Fa-f]{4,8})')
            if ($r.Success) { $ids += $r.Groups[1].Value.PadLeft(8, '0').ToUpper() }
        } else {
            foreach ($r in [regex]::Matches($code, '0[xX]([0-9A-Fa-f]{4,8})')) {
                $ids += $r.Groups[1].Value.PadLeft(8, '0').ToUpper()
            }
        }
    }
    if ($ids.Count -eq 0) { Write-Output "FAIL: array $Name parsed as empty"; exit 1 }
    return $ids
}

$bornLists = [ordered]@{
    kAlwaysScaleCityIds   = Get-CppArrayIds kAlwaysScaleCityIds
    kRegionPanelIds       = Get-CppArrayIds kRegionPanelIds
    kGodPanelIds          = Get-CppArrayIds kGodPanelIds
    kDataScaledSubtreeIds = Get-CppArrayIds kDataScaledSubtreeIds
}
$ownLists = [ordered]@{
    kSubFlyoutIds    = Get-CppArrayIds kSubFlyoutIds
    kGodToolFlyoutIds = Get-CppArrayIds kGodToolFlyoutIds
    kMayorFlyoutDock = Get-CppArrayIds kMayorFlyoutDock -FirstPerRow
}
foreach ($k in $bornLists.Keys) { Write-Output ("Parsed {0}: {1} ids" -f $k, $bornLists[$k].Count) }
foreach ($k in $ownLists.Keys)  { Write-Output ("Parsed {0}: {1} ids" -f $k, $ownLists[$k].Count) }

# --- 3. coverage ------------------------------------------------------------
$born = New-Object 'System.Collections.Generic.HashSet[string]'
foreach ($k in $bornLists.Keys) { foreach ($i in $bornLists[$k]) { [void]$born.Add($i) } }
$own = @{}
foreach ($k in $ownLists.Keys) { foreach ($i in $ownLists[$k]) { if (-not $own.ContainsKey($i)) { $own[$i] = $k } } }

$nBorn = 0; $ownOnly = @(); $violations = @()
foreach ($id in $scaled) {
    if ($born.Contains($id)) { $nBorn++ }
    elseif ($own.ContainsKey($id)) { $ownOnly += ("0x{0} - covered by its OWN mechanism only ({1})" -f $id, $own[$id]) }
    else { $violations += $id }
}

Write-Output ""
Write-Output ("born-correct: {0}   own-mechanism only: {1}   uncovered: {2}" -f $nBorn, $ownOnly.Count, $violations.Count)
$ownOnly | ForEach-Object { Write-Output ("  NOTE: " + $_) }

if ($violations.Count) {
    Write-Output ""
    foreach ($v in $violations) {
        Write-Output ("FAIL: 0x{0} is in SCALED_WINDOW_IDS but has NO born-correct route and NO own mechanism - its first appearance will flash 1x. Add it to a born-correct list (gen 2/3) or give it a labeled mechanism. Law: UiSpike.cpp `"IF WE SHIP 2x ART FOR A PANEL`"." -f $v)
    }
    exit 1
}
Write-Output ("ALL PASS ({0} scaled ids all covered)" -f $scaled.Count)
exit 0
