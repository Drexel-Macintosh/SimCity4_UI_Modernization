# Build-PublicRepo.ps1 - assemble the PUBLISHABLE repo. Curated, not swept.
#
# ⛔ WHY THIS REPLACED EXPORT-PUBLIC.ps1's FILE LIST (2026-08-06).
# EXPORT-PUBLIC.ps1 was built for task #108, whose question was "what is SAFE
# to publish" - a privacy sweep. Its allowlist was written to be generous:
# every .py, .md and .ps1 under tools\ and _tests\ passed, because none of them
# leaked anything. Using that list as the repo contents published 623 files -
# the deploy harnesses, the reverse-engineering apparatus, a 6,500-line
# engineering diary, a 4,900-line changelog, the publish plan itself, and a
# README paragraph about an unrelated Microsoft Surface project.
#
# "Safe to publish" and "belongs in a release" are DIFFERENT QUESTIONS. Passing
# a privacy audit is not an argument for inclusion.
#
# So this file is an EXPLICIT MANIFEST, not a filter. Every path is named. If
# something is not written here it does not ship, and adding to it is a
# deliberate act rather than a side effect of the file having a safe extension.
#
#   .\_packaging\Build-PublicRepo.ps1 [-Dest <dir>] [-WhatIfOnly]
#
# Reuses the leak scan from EXPORT-PUBLIC.ps1's approach and refuses on any hit.

param(
    [string] $Dest,
    [switch] $WhatIfOnly,
    [string[]] $PiiToken = @()
)

$ErrorActionPreference = "Stop"
$proj = Split-Path -Parent $PSScriptRoot
if (-not $Dest) { $Dest = Join-Path $env:USERPROFILE "sc4uiscale-release" }
$destFull = [System.IO.Path]::GetFullPath($Dest)
if ($destFull -like "$proj*") { throw "Dest is inside the repo: $destFull" }
if ($destFull -match '(?i)onedrive|dropbox|google drive') {
    throw "Dest is inside a cloud-synced folder ($destFull)."
}

# --- THE MANIFEST -----------------------------------------------------------
# src: SC4UIScale ONLY. SC4TouchControls is a SEPARATE PROJECT and does not
# appear here in any form - not its sources, not its project file, not its
# version header, not a mention in a doc.
$SRC = @(
    "CodePatches.cpp", "CodePatches.h",
    "Logger.cpp", "Logger.h",
    "SC4UIScaleDllDirector.cpp",
    "SC4VersionDetection.cpp", "SC4VersionDetection.h",
    "ScaleRemap.cpp", "ScaleRemap.h",
    "ScaleTier.cpp", "ScaleTier.h",
    "Settings.cpp", "Settings.h",
    "SpinProbe.cpp", "SpinProbe.h",
    "UiSpike.cpp", "UiSpike.h",
    "WebRedirect.cpp", "WebRedirect.h",
    "SC4UIScale.vcxproj", "SC4UIScale.sln"
)

# tools: the BUILD PIPELINE only - what someone needs to regenerate the .dat
# packages from their own installation. NOT the research corpus, NOT the
# disassembly apparatus, NOT the offline gates, NOT one-off probes.
$TOOLS = @(
    "sc4paths.py",
    "dbpf\DbpfExtract.cs", "dbpf\DbpfPack.cs", "dbpf\find_tgi.py",
    "dbpf\who_owns_tgi.py", "dbpf\NOTES.md", "dbpf\NOTES-PACK.md",
    # ⛔ THE DERIVED LISTS SHIP WITH THE UPSCALER OR THE UPSCALER IS WRONG.
    # Upscale2x without --cell-strips (#156) and --nine-slice (#157) regenerates
    # the 1.5x tier with the exact defects those two issues cured. The .cs alone
    # was listed here for both of them; a public rebuild would have produced
    # bled state strips and short 9-slice corners with every gate green.
    "upscale\Upscale2x.cs",
    "upscale\find_cell_strips.py", "upscale\cell-strips.txt",
    "upscale\find_nine_slice.py", "upscale\nine-slice.txt",
    # Review finding 2 (2026-08-17): build_selective_safe.py's #186 step and
    # Rebuild-Corpus.ps1's mandatory-list preflight consume ALL the derived
    # lists - a public build died on the first missing one. Ship the full set
    # plus the two post-step tools the corpus command now runs.
    "upscale\find_no_snap.py", "upscale\no-snap.txt",
    "upscale\make_no_smooth.py", "upscale\no-smooth.txt",
    "upscale\height-exact-strips.txt", "upscale\height-exact-slabs.txt",
    "upscale\redraw_ladder.py", "upscale\gate_key_integrity.py",
    "upscale\Rebuild-Corpus.ps1",
    "selective-safe\build_selective_safe.py", "selective-safe\refmap.csv",
    "selective-safe\refmap-15x.csv", "selective-safe\refmap-3x.csv",
    "selective-safe\html-image-refs.txt",
    "dialog-static\build_dialog_static.py",
    "itemicons\build_itemicons_sub.py", "itemicons\build_menu_patches.py",
    "itemicons\rebuild_namicons.py", "itemicons\scan_thirdparty_icons.py",
    "itemicons\stage_icons.py",
    "fonts\make_fontstyle.py",
    "webtext\build_webtext.py",
    "oddballs\OddballConvert.cs"
)

$ROOT = @("README.md", "LICENSE", "THIRD-PARTY-NOTICES.md", "CHANGELOG.md",
          ".gitignore")
$DOCS = @("WHAT-IT-SCALES.md", "HOW-IT-WORKS.md", "BUILDING.md",
          "COMPATIBILITY.md")

# --- the research corpus ----------------------------------------------------
# SC4 shipped no SDK. These files are the reference that had to be written from
# measurement to build this mod, and they are the repository's most reusable
# content. They ship; the working notes that produced them do not.
#
# ABSENT BY DECISION and not by omission - anything that describes work in
# progress rather than the product: the engineering ledger, the regression
# diary, session state, open-defect and backlog lists, one-off probes, and
# generated pipeline output. A public repository states what is true now.
$RESEARCH = @("KNOWN-LIMITATIONS.md")
$RESEARCH_LAWS = "*.md"     # research\laws\ ships whole, after the scrub
$TOOLS_RESEARCH = @(
    "SC4-UI-ENGINE.md", "SC4-WORLD-OVERLAYS.md", "SDK-GAPS.md",
    "UI-ART-BINDING.md", "SCALING-AXES.md", "FONTS-AND-DIALOGS.md",
    "ITEMICONS.md", "REGION-SCREEN.md", "REGION-SWITCH.md", "MAYOR-MODE.md",
    "GOD-MODE-FLYOUTS.md", "DYNAMIC-CONTROLS.md", "STOCK-PARITY.md",
    "CITY-SITUATION-INDICATORS.md", "CITY-DOCK-OVERLAP.md",
    "BUDGET-DETAIL-ANATOMY.md", "MECHANISM-GENERATIONS.md",
    "METHOD.md", "TRIAGE.md",
    "UPSTREAM-CAM-REPORT.md", "UPSTREAM-NAM-REPORT.md",
    "UPSTREAM-WARRIOR-REPORT.md", "UPSTREAM-SAVEWARNING-REPORT.md",
    "UPSTREAM-BUILDINGSTYLES-REPORT.md"
)
# The offline simulator: it reproduces the engine's layout arithmetic without
# launching the game, which is what makes a change testable at all. Gates and
# emulators ship; the one-off scans and probes that answered a single question
# once do not.
$UIMAP_DOCS = @("BLIT-BEHAVIOUR.md", "CONSTANT-MAP.md", "SUBFLYOUT-BUILDER.md",
                "SUBFLYOUT-CONSTANTS.md", "SUBFLYOUT-ART-VERDICT.md",
                "SUBFLYOUT-LIVE-EVIDENCE.md")
$UIMAP_EMU_GLOBS = @("gate_*.py", "emu_*.py", "render_*.py", "scale_rules.py",
                     "sim_itemicon_states.py")
# The regression net. Every one of these runs without the game and exits 0/1,
# so a stranger can prove the source is intact before building it.
$TESTS = @("Test-BootStateValidate.py", "Test-SelectorDerive.py",
           "Test-SelectorContract.py", "Test-StockTierContract.py",
           "Test-MutationCountInvariant.py", "Test-PackageGating.py",
           "Test-ShippingIniKeys.py", "Test-MiniMapX8Bake.py",
           "Test-RegionZoomSizes.py", "Test-BinaryPii.py",
           "Test-DatIntegrity.ps1", "Deploy-OnGameClose.ps1", "Set-Tier.ps1",
           "README.md")

# vendor ships whole: required to COMPILE, and gzcom-dll's LGPL-2.1 obliges us
# to provide its source alongside any binary we distribute.
$VENDOR_EXT = @(".h", ".c", ".cpp", ".txt", ".md")

$staged = Join-Path $proj "_packaging\public-repo"

$items = New-Object System.Collections.Generic.List[object]
function Add-Item2([string]$from, [string]$rel) {
    if (-not (Test-Path $from)) { Write-Warning "MISSING $rel"; return }
    $items.Add([pscustomobject]@{ full = $from; rel = $rel })
}
# ROOT and DOCS come from the REPOSITORY, not from a staged copy. A staged
# copy is a second version of the same file that goes stale silently, which is
# how a release once shipped a README nobody had edited in weeks.
foreach ($f in $ROOT) { Add-Item2 (Join-Path $proj $f) $f }
foreach ($f in $DOCS) { Add-Item2 (Join-Path $proj "docs\$f") "docs\$f" }
foreach ($f in $RESEARCH) { Add-Item2 (Join-Path $proj "research\$f") "research\$f" }
Get-ChildItem (Join-Path $proj "research\laws") -Filter $RESEARCH_LAWS -File |
    ForEach-Object { Add-Item2 $_.FullName ("research\laws\" + $_.Name) }
foreach ($f in $TOOLS_RESEARCH) {
    Add-Item2 (Join-Path $proj "tools\research\$f") "tools\research\$f"
}
foreach ($f in $UIMAP_DOCS) {
    Add-Item2 (Join-Path $proj "tools\uimap\$f") "tools\uimap\$f"
}
foreach ($g in $UIMAP_EMU_GLOBS) {
    Get-ChildItem (Join-Path $proj "tools\uimap\emu") -Filter $g -File -ErrorAction SilentlyContinue |
        ForEach-Object { Add-Item2 $_.FullName ("tools\uimap\emu\" + $_.Name) }
}
foreach ($f in $TESTS) { Add-Item2 (Join-Path $proj "_tests\$f") "_tests\$f" }
foreach ($f in $SRC)  { Add-Item2 (Join-Path $proj "src\$f") "src\$f" }
foreach ($f in $TOOLS){ Add-Item2 (Join-Path $proj "tools\$f") "tools\$f" }
Get-ChildItem (Join-Path $proj "vendor") -Recurse -File |
    Where-Object { $VENDOR_EXT -contains $_.Extension.ToLower() -and
                   $_.FullName -notlike "*\.git\*" } |
    ForEach-Object { Add-Item2 $_.FullName $_.FullName.Substring($proj.Length + 1) }

$bytes = 0
foreach ($i in $items) { $bytes += (Get-Item $i.full).Length }
$ours = ($items | Where-Object { $_.rel -notlike "vendor\*" }).Count
Write-Output ("manifest: {0} file(s) total - {1} ours + {2} vendored SDK - {3:N2} MB" -f
    $items.Count, $ours, ($items.Count - $ours), ($bytes / 1MB))

# --- leak scan, before any copy ---------------------------------------------
$rxUserPath = [regex]'(?i)[A-Za-z]:\\+Users\\+[^\\\s"''<>|]+'
$rxHost     = [regex]("(?i)\b" + [regex]::Escape($env:COMPUTERNAME) + "\b")
# Other projects that live in the same working tree and must never appear here.
$rxForeign  = [regex]'(?i)\b(PixelSense|MeetSurface|SC4TouchControls|InjectTouchInput|HydraX64|Milan)\b'
$leaks = New-Object System.Collections.Generic.List[string]
foreach ($x in $items) {
    if ($x.rel -like "vendor\*") { continue }
    $txt = Get-Content $x.full -Raw -ErrorAction SilentlyContinue
    if (-not $txt) { continue }
    foreach ($m in $rxUserPath.Matches($txt)) { $leaks.Add(("USERPATH {0}: {1}" -f $x.rel, $m.Value)) }
    foreach ($m in $rxHost.Matches($txt))     { $leaks.Add(("HOSTNAME {0}: {1}" -f $x.rel, $m.Value)) }
    foreach ($m in $rxForeign.Matches($txt))  { $leaks.Add(("FOREIGN  {0}: {1}" -f $x.rel, $m.Value)) }
    foreach ($t in $PiiToken) {
        if ($t -and $txt -match [regex]::Escape($t)) { $leaks.Add(("TOKEN    {0}: {1}" -f $x.rel, $t)) }
    }
}
if ($leaks.Count) {
    Write-Output ""
    Write-Output ("SCAN FAILED - {0} hit(s), NOTHING COPIED:" -f $leaks.Count)
    $leaks | Select-Object -First 40 | ForEach-Object { Write-Output ("   " + $_) }
    exit 1
}
Write-Output "scan: clean (user paths, hostname, other-project names, supplied tokens)"
if ($WhatIfOnly) { Write-Output "-WhatIfOnly: stopping before the copy."; exit 0 }

if (Test-Path $destFull) { Remove-Item -Recurse -Force $destFull }
New-Item -ItemType Directory -Path $destFull -Force | Out-Null
foreach ($x in $items) {
    $target = Join-Path $destFull $x.rel
    $dir = Split-Path -Parent $target
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
    Copy-Item $x.full $target -Force
}
Write-Output ("built {0} file(s) -> {1}" -f $items.Count, $destFull)
