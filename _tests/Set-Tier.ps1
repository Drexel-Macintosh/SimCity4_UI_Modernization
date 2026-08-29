# Set-Tier.ps1 - force a specific scale tier for an eyes-on test, DATA AND ALL.
#
# WHY THIS EXISTS. To test a tier by hand the obvious move is to set
# AutoScale=0 and ScaleFactor=1.5 in the ini. THAT DOES NOT WORK, and it fails
# in the most misleading way available:
#
#     AutoScale off: manual ScaleFactor 1.50, layers untouched.
#
# "layers untouched" means the DLL scales the WINDOW GEOMETRY to 1.5x and
# leaves the 2x art packages and the 2x FontStyle in place. You get 2x artwork
# inside 1.5x boxes - every panel crushed, text overlapping, boxes clipped -
# and it looks exactly like a catastrophic tier bug. It is not. It is the test
# rig. (2026-08-06: a full launch and two screenshots were spent on this.)
#
#   .\_tests\Set-Tier.ps1 -Tier 1        1x BASELINE: all packages off, stock font
#   .\_tests\Set-Tier.ps1 -Tier 1.5      force 1.5x, art and font included
#   .\_tests\Set-Tier.ps1 -Tier 2        back to 2x
#   .\_tests\Set-Tier.ps1 -Auto          hand control back to AutoScale
#   .\_tests\Set-Tier.ps1 -Status        report only, change nothing
#   .\_tests\Set-Tier.ps1 -ShowState     read the DLL's OWN z_SC4UIScale_STATE.txt
#
# THE WHOLE TRANSITION IN ONE CALL - tier AND the screen it is judged on:
#
#   .\_tests\Set-Tier.ps1 -Tier 1 -Windowed              1x in a 1024x768 window
#   .\_tests\Set-Tier.ps1 -Tier 1 -Windowed -Width 1280 -Height 1024
#   .\_tests\Set-Tier.ps1 -Auto -FullScreen -Width 2400 -Height 1600
#
# ============================================================================
# v4.5.0 REWRITE: THIS SCRIPT NO LONGER RENAMES ANYTHING.
# ============================================================================
# Through v4.4.0 a tier was armed by RENAMING dats: `z_SC4UIScale_<Pkg>-<tag>
# .dat` was live and the other tiers wore `.dat.x1-disabled`. From v4.5.0
# (src\ScaleTier.cpp: ArmOne / CommitArming / WriteArmState) arming is a
# CONTENT SWAP AT A STABLE FILENAME:
#
#   LIVE     z_SC4UIScale_<Pkg>.dat            the only thing SC4 loads. Its
#                                              CONTENT changes; the name never
#                                              does, at any tier, under any
#                                              gate verdict, ever.
#   PAYLOAD  z_SC4UIScale_<Pkg>.<tag>.uipay    inert. Never renamed, never
#                                              loaded. MEASURED, not assumed:
#                                              probe #202 copied a real DBPF to
#                                              `.uipay`, booted, and it did NOT
#                                              appear in the registered-segment
#                                              census while 13 of our live .dat
#                                              files did - the plugin scan is
#                                              EXTENSION-gated.
#   STATE    z_SC4UIScale_STATE.txt            written by the DLL into EACH of
#                                              our folders every boot. It is
#                                              the diagnosis a constant
#                                              filename destroys: with every
#                                              name fixed, `dir` can no longer
#                                              tell you the armed tier or a
#                                              gate verdict. -ShowState reads it.
#
# WHY THE REWRITE WAS FORCED, and it is the same failure this file's header has
# warned about since 2026-08-06. The old package scan was
#
#     '^(z_SC4UIScale_[A-Za-z]+)-(15x|2x|3x)\.dat(\.x1-disabled)?$'
#
# and under the payload layout it MATCHES NOTHING. The family list came back
# empty, the script printed "packages: 0 rename(s)" and EXITED 0. A silent
# no-op, wrong in the safe-looking direction, in the one instrument every other
# test is verified with. It failed that way twice on 2026-08-29 before anyone
# looked at the regex. So:
#
#   * ZERO IS NOW A RED REFUSAL, never a pass. Every path that could find
#     nothing to do says so in red and exits 1. This is the single most
#     important behaviour in this file.
#   * NOTHING IS HAND-LISTED. The tier tags, the package roster, which folder
#     each package lives in, whether a package is tier-gated / inverse-gated /
#     not tier-gated at all, and the dependency-gated set are ALL parsed out of
#     src\ScaleTier.cpp at run time. A hand-kept copy of any of them is a
#     second rule that drifts - $ALLTAGS in the previous version had drifted
#     already: it read @("15x","2x","3x") while kPackages had carried a 4.0 row
#     for months.
#   * THE PAYLOAD LAYOUT IS A PRECONDITION, and a tree still on the rename
#     layout is REFUSED rather than half-converted. The live install on this
#     machine is deliberately still on renames (measured 2026-08-29: 0 .uipay,
#     61 .x1-disabled, 9 tier-tagged .dat); running a content swap into that
#     tree would leave two live providers of every TGI.
#
# Waits for the game to close first - it runs ELEVATED and holds the dats open.
# NEVER kills it (standing order).
#
# AND `WindowMode=Windowed` ALONE DOES NOTHING. dgVoodoo overrides it:
# with FullScreenMode=true the game comes up borderless-fullscreen at panel
# size, so the requested WxH never renders. -Windowed sets BOTH halves, plus
# CaptureMouse=false (true traps the cursor so you cannot reach the title bar).
# Both files are written WITHOUT a BOM and backed up once, because
# dgVoodooCpl.exe rewrites the conf if it is ever launched.

[CmdletBinding()]
param(
    # NO ValidateSet ANY MORE, and that is deliberate. A ValidateSet is a
    # hand-written literal list of tiers, i.e. exactly the thing that drifted
    # from kPackages. The accepted set is DERIVED from the C++ table below and
    # a bad value is refused by name, printing the derived list. Everything the
    # old set accepted ("1", "1.5", "2", "3") still works; "4" now works too if
    # a 4x payload is ever built.
    [string] $Tier,
    [switch] $Auto,
    [switch] $Status,
    [switch] $ShowState,
    [switch] $Windowed,
    [switch] $FullScreen,
    [int] $Width,
    [int] $Height,
    # NEW. Point the whole script at a scratch tree instead of the live
    # install. This exists so the rewrite could be dry-run without touching
    # the player's Plugins folder - a test rig you cannot test is the same
    # class of instrument this file keeps being burnt by.
    [string] $Plugins = (Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'SimCity 4\Plugins'),
    # NEW. Arm dependency-gated packages even though they are currently inert.
    # Default is to leave them alone: their owning mod may be absent, and
    # arming our frozen copy of someone else's UI into a game without that mod
    # is precisely what Test-ThirdPartyGates.ps1 exists to catch.
    [switch] $ArmGated,
    # NEW. Plan only - report every swap it would make and touch nothing.
    [switch] $DryRun
)

$ErrorActionPreference = "Stop"

# ---------------------------------------------------------------------------
# REFUSALS ARE LOUD AND RED, and they exit 1.
# ---------------------------------------------------------------------------
function Deny {
    param([string] $Title, [string[]] $Lines = @())
    Write-Host ""
    Write-Host ("=" * 74) -ForegroundColor Red
    Write-Host ("REFUSED: " + $Title) -ForegroundColor Red
    Write-Host ("=" * 74) -ForegroundColor Red
    foreach ($l in $Lines) { Write-Host ("  " + $l) -ForegroundColor Red }
    Write-Host ""
    exit 1
}

$isLiveTree = -not $PSBoundParameters.ContainsKey('Plugins')
if (-not (Test-Path $Plugins)) {
    Deny "no Plugins tree at $Plugins" @(
        "Nothing below could be evidence about an install that is not there.",
        "Pass -Plugins <path> to point at a scratch tree.")
}

# ===========================================================================
# 1. CALIBRATION - everything this script knows is PARSED FROM src\ScaleTier.cpp
# ===========================================================================
# ONE read, several answers. This is the same technique the previous version
# used for the dependency-gated list only (and Test-DatIntegrity.ps1 uses for
# its drift check); the lesson of the 4x drift is that the OTHER lists needed
# it just as much. If this parse comes back empty the script REFUSES: an empty
# calibration makes every count below zero, and a zero that looks like a pass
# is the defect this rewrite exists to remove.
$repo = Split-Path -Parent $PSScriptRoot
$scaleTierPath = Join-Path $repo "src\ScaleTier.cpp"
if (-not (Test-Path $scaleTierPath)) {
    Deny "cannot find src\ScaleTier.cpp at $scaleTierPath" @(
        "Every tier tag, package name and folder rule this script uses is",
        "derived from that file. Without it there is nothing to derive and a",
        "hand-written fallback list is what put 4x out of step in the first",
        "place. Run this from a checkout of the repo.")
}
$cpp = [System.IO.File]::ReadAllText($scaleTierPath)

# --- 1a. the tier table -----------------------------------------------------
#   const Package kPackages[] = { { 4.0f, L"-4x" }, ... };
# The C++ TAG carries a hyphen ("-15x"); the PAYLOAD suffix does not ("15x"),
# because there it is a filename extension component and not a tier tag. That
# transform is ScaleTier.cpp's PayloadTagOf(), mirrored below.
function ConvertTo-PayloadTag([string] $cppTag) {
    if ([string]::IsNullOrEmpty($cppTag)) { return "on" }
    if ($cppTag.StartsWith("-")) { return $cppTag.Substring(1) }
    return $cppTag
}
$tierTable = @()   # rows: Factor (double), Label ("1.5"), CppTag ("-15x"), Tag ("15x")
$tblMatch = [regex]::Match($cpp, '(?s)const\s+Package\s+kPackages\s*\[\s*\]\s*=\s*\{(.*?)\}\s*;')
if ($tblMatch.Success) {
    foreach ($r in [regex]::Matches($tblMatch.Groups[1].Value, '\{\s*([0-9.]+)f\s*,\s*L"([^"]*)"\s*\}')) {
        $f = [double]::Parse($r.Groups[1].Value, [Globalization.CultureInfo]::InvariantCulture)
        $tierTable += [PSCustomObject]@{
            Factor = $f
            Label  = $f.ToString([Globalization.CultureInfo]::InvariantCulture)
            CppTag = $r.Groups[2].Value
            Tag    = (ConvertTo-PayloadTag $r.Groups[2].Value)
        }
    }
}
if ($tierTable.Count -eq 0) {
    Deny "could not parse kPackages out of src\ScaleTier.cpp" @(
        "The tier set is this script's calibration. Deriving nothing and",
        "carrying on would arm nothing and report a clean zero - the exact",
        "silent no-op this rewrite exists to make impossible.")
}
# Sorted largest-first, the same order the DLL tries them in.
$tierTable = @($tierTable | Sort-Object -Property Factor -Descending)
$TIER_TAGS = @($tierTable | ForEach-Object { $_.Tag })

# --- 1b. the package roster -------------------------------------------------
# Every SyncDat() call site, with the folder it targets and the SHAPE of its
# tag. Three shapes exist and they want opposite things at 1x:
#   tier     tag is `pkg.tag` - armed at its own tier, `.off` at every other.
#   inverse  tag is a literal L"-1x" - z_SC4UIScale_SelectorUI, THE ONE PACKAGE
#            ARMED BY THE ABSENCE OF A TIER. It carries Graphic Options at
#            stock geometry with the scale-selector nodes injected, and it is
#            what keeps 1x from being a one-way door.
#   plain    tag is a literal L"" - z_SC4UIScale_WebText. Its gate is the Web
#            Button Improvement Mod's presence, NOT the tier, so this script
#            must not touch it at any tier. Listed and reported, never armed.
$roster = @()
$rxSyncDat = '(?s)SyncDat\s*\(\s*(\w+)\s*,\s*L"((?:[^"\\]|\\.)*)"\s*,\s*(?:(pkg\.tag)|L"((?:[^"\\]|\\.)*)")'
foreach ($m in [regex]::Matches($cpp, $rxSyncDat)) {
    $rel = $m.Groups[2].Value -replace '\\\\', '\'
    $leaf = $rel
    $folderRole = "early"
    if ($rel.Contains("\")) {
        $prefix = $rel.Substring(0, $rel.IndexOf("\"))
        $leaf = $rel.Substring($rel.IndexOf("\") + 1)
        # ResolveOurRelative(): ONLY the exact "zzz-SC4UIScale" prefix means
        # the override folder; anything else resolves into the early folder.
        if ($prefix -ieq "zzz-SC4UIScale") { $folderRole = "override" }
    }
    if ($m.Groups[3].Success) {
        $kind = "tier"; $litTag = $null
    } else {
        $litTag = ConvertTo-PayloadTag $m.Groups[4].Value
        $kind = if ($litTag -eq "on") { "plain" } else { "inverse" }
    }
    if ($roster | Where-Object { $_.Base -eq $leaf -and $_.Role -eq $folderRole }) { continue }
    $roster += [PSCustomObject]@{
        Base = $leaf; Role = $folderRole; Kind = $kind; LiteralTag = $litTag
    }
}
if ($roster.Count -eq 0) {
    Deny "parsed src\ScaleTier.cpp but found no SyncDat() call sites" @(
        "The roster is what tells this script which packages follow the tier.",
        "An empty roster arms nothing and reports zero - a red failure, not a",
        "pass. The regex is probably stale against a refactor of SyncDat.")
}

# --- 1c. the dependency-gated set ------------------------------------------
# AUTHORITATIVE, from src\ScaleTier.cpp's own DepOkByName calls rather than a
# fourth hand-kept copy of a list that has already rotted twice. A package NOT
# in this set has no dependency at all - it is tier-gated only, and "currently
# inert" never means "its mod is absent" for it.
$DEPENDENCY_GATED = New-Object System.Collections.Generic.HashSet[string]
foreach ($m in [regex]::Matches($cpp, 'DepOkByName[^)]*?(z_SC4UIScale_[A-Za-z0-9]+)')) {
    [void]$DEPENDENCY_GATED.Add($m.Groups[1].Value)
}

# --- 1d. the folder markers -------------------------------------------------
# v4.5.0 finds our folders BY CONTENT, never by name: sc4pac names package
# folders itself, with the version baked in, so the v4.2.0 literals
# "010-SC4UIScale" / "zzz-SC4UIScale" resolve to nothing under a
# package-manager install. Same markers, same two roles, same fallback - and
# the fallback SAYS SO, because a silently wrong folder here disarms every
# package we own.
$markerEarly = @(); $markerOverride = @()
$mk = [regex]::Match($cpp, '(?s)const\s+Marker\s+markers\s*\[\s*\]\s*=\s*\{(.*?)\}\s*;')
if ($mk.Success) {
    foreach ($r in [regex]::Matches($mk.Groups[1].Value, '\{\s*L"([^"]+)"\s*,\s*([12])\s*\}')) {
        if ($r.Groups[2].Value -eq "1") { $markerEarly += $r.Groups[1].Value }
        else { $markerOverride += $r.Groups[1].Value }
    }
}

Write-Output ("calibration: {0} tier(s) [{1}], {2} package call site(s), {3} dependency-gated, from src\ScaleTier.cpp" -f `
    $tierTable.Count, (($tierTable | ForEach-Object { $_.Label }) -join "/"), $roster.Count, $DEPENDENCY_GATED.Count)

# ===========================================================================
# 2. FOLDER DISCOVERY - by content, exactly like ResolveOurDirs()
# ===========================================================================
function Test-DirMarkers([string] $dir, [string[]] $pats) {
    foreach ($p in $pats) {
        if (@(Get-ChildItem -LiteralPath $dir -Filter $p -File -ErrorAction SilentlyContinue).Count -gt 0) { return $true }
    }
    return $false
}
function Find-OurDirs([string] $root) {
    $early = $null; $override = $null
    # Two levels: our own top-level layout, and <subfolder>\<pkg> as sc4pac
    # lays it out.
    $cands = @(Get-ChildItem -LiteralPath $root -Directory -ErrorAction SilentlyContinue)
    $cands += @($cands | ForEach-Object { Get-ChildItem -LiteralPath $_.FullName -Directory -ErrorAction SilentlyContinue })
    foreach ($d in $cands) {
        if (-not $early -and (Test-DirMarkers $d.FullName $markerEarly)) { $early = $d.FullName }
        if (-not $override -and (Test-DirMarkers $d.FullName $markerOverride)) { $override = $d.FullName }
        if ($early -and $override) { break }
    }
    return @{ Early = $early; Override = $override }
}
$found = Find-OurDirs $Plugins
$earlyFound = [bool]$found.Early
$overrideFound = [bool]$found.Override
$our = if ($earlyFound) { $found.Early } else { Join-Path $Plugins "010-SC4UIScale" }
$zzz = if ($overrideFound) { $found.Override } else { Join-Path $Plugins "zzz-SC4UIScale" }
$msg = "folders: early={0} ({1}), override={2} ({3})"
Write-Output ($msg -f $our, $(if ($earlyFound) { "discovered by content" } else { "FALLBACK to the v4.2.0 name" }),
    $zzz, $(if ($overrideFound) { "discovered by content" } else { "FALLBACK to the v4.2.0 name" }))
$ourDirs = [ordered]@{ early = $our; override = $zzz }
$ini = Join-Path $our "SC4UIScale.ini"
$STATE_FILE = "z_SC4UIScale_STATE.txt"

# ===========================================================================
# 3. LAYOUT GUARD - refuse a tree still on the rename layout
# ===========================================================================
# The tag alternation is BUILT FROM the derived set plus `1x`, so a tier added
# to kPackages tomorrow is caught by this guard without an edit here.
$allKnownTags = @($TIER_TAGS + @("1x")) | Sort-Object -Unique
$rxTagged = '^z_SC4UIScale_.*-(' + (($allKnownTags | ForEach-Object { [regex]::Escape($_) }) -join '|') + ')\.dat$'
$legacy = @()
foreach ($d in $ourDirs.Values) {
    if (-not (Test-Path $d)) { continue }
    $legacy += @(Get-ChildItem -LiteralPath $d -File -Filter "z_SC4UIScale_*" -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -like "*.x1-disabled" -or $_.Name -match $rxTagged })
}
if ($legacy.Count -gt 0 -and -not $Status -and -not $ShowState) {
    $lines = @(
        "$($legacy.Count) file(s) in this tree are still the pre-4.5.0 RENAME layout,",
        "e.g. $($legacy[0].Name).",
        "",
        "This script speaks CONTENT SWAP only: it copies z_SC4UIScale_<Pkg>.<tag>.uipay",
        "over the stable z_SC4UIScale_<Pkg>.dat. Doing that in a rename-layout tree",
        "leaves BOTH z_SC4UIScale_<Pkg>.dat and z_SC4UIScale_<Pkg>-<tag>.dat live -",
        "two providers of every TGI that package owns, and nothing goes red.",
        "",
        "Convert first, then re-run:",
        "    .\_tests\Convert-ToPayloadLayout.ps1 -Tree `"$Plugins`"",
        "or boot the game once with a v4.5.0 DLL - MigrateRenamesToPayloads()",
        "converts the layout in place, no download needed.")
    Deny "this tree is on the RENAME layout, not the payload layout" $lines
}

# ===========================================================================
# 4. CENSUS - what is actually on disk
# ===========================================================================
# $pkg[base] = @{ Role; Dir; Live; Payloads = @{tag -> path} }
function Get-Census {
    $pkg = [ordered]@{}
    foreach ($role in @("early", "override")) {
        $dir = $ourDirs[$role]
        if (-not (Test-Path $dir)) { continue }
        foreach ($f in (Get-ChildItem -LiteralPath $dir -File -Filter "z_SC4UIScale_*" -ErrorAction SilentlyContinue)) {
            $base = $null; $tag = $null
            if ($f.Name -match '^(z_SC4UIScale_[^.]+)\.([A-Za-z0-9]+)\.uipay$') {
                $base = $Matches[1]; $tag = $Matches[2]
            } elseif ($f.Name -match '^(z_SC4UIScale_[^.]+)\.dat$') {
                $base = $Matches[1]
            } else { continue }
            if ($base -eq "z_SC4UIScale_STATE") { continue }
            if (-not $pkg.Contains($base)) {
                $pkg[$base] = @{ Role = $role; Dir = $dir; Live = $null; Payloads = @{} }
            }
            if ($tag) { $pkg[$base].Payloads[$tag] = $f.FullName }
            else { $pkg[$base].Live = $f.FullName }
        }
    }
    return $pkg
}

# Which payload does the live file currently hold? SIZE FIRST, hash only to
# break a tie - the 3x set is ~88 MB and the live install sits on OneDrive
# cloud placeholders, so hashing everything on every -Status is a real cost.
# A single size match is reported as INFERRED, because that is what it is.
function Get-LiveTag {
    param([hashtable] $Entry)
    if (-not $Entry.Live -or -not (Test-Path $Entry.Live)) {
        return @{ Tag = "(no live file)"; How = "absent" }
    }
    $len = (Get-Item -LiteralPath $Entry.Live).Length
    $cand = @($Entry.Payloads.Keys | Where-Object { (Get-Item -LiteralPath $Entry.Payloads[$_]).Length -eq $len })
    if ($cand.Count -eq 0) { return @{ Tag = "unrecognised"; How = "no payload of this size" } }
    if ($cand.Count -eq 1) { return @{ Tag = $cand[0]; How = "inferred from size" } }
    $h = (Get-FileHash -LiteralPath $Entry.Live -Algorithm SHA256).Hash
    foreach ($t in $cand) {
        if ((Get-FileHash -LiteralPath $Entry.Payloads[$t] -Algorithm SHA256).Hash -eq $h) {
            return @{ Tag = $t; How = "by content" }
        }
    }
    return @{ Tag = "unrecognised"; How = "size matched but content did not" }
}

# ===========================================================================
# 5. THE STATE FILE - the diagnosis a constant filename destroys
# ===========================================================================
# TSV written by WriteArmState(): two `#` header lines, then one row per
# package - base, tag, reason, paySize, payTime, liveSize, liveTime. The two
# time columns are Windows FILETIMEs, which is exactly LastWriteTimeUtc
# .ToFileTimeUtc(), so a row can be checked against the file it describes.
function Read-ArmState {
    $rows = @()
    foreach ($role in @("early", "override")) {
        $dir = $ourDirs[$role]
        $p = Join-Path $dir $STATE_FILE
        if (-not (Test-Path $p)) { continue }
        foreach ($line in (Get-Content -LiteralPath $p)) {
            if ($line -match '^\s*#' -or -not $line.Trim()) { continue }
            $c = $line -split "`t"
            if ($c.Count -lt 7) { continue }
            $rows += [PSCustomObject]@{
                Role = $role; Dir = $dir; Base = $c[0]; Tag = $c[1]; Reason = $c[2]
                PaySize = [uint64]$c[3]; PayTime = [uint64]$c[4]
                LiveSize = [uint64]$c[5]; LiveTime = [uint64]$c[6]
            }
        }
    }
    return $rows
}

function Show-ArmState {
    $rows = @(Read-ArmState)
    Write-Output ""
    Write-Output "z_SC4UIScale_STATE.txt - what the DLL armed on its LAST BOOT"
    Write-Output ("-" * 78)
    if ($rows.Count -eq 0) {
        Deny "no z_SC4UIScale_STATE.txt in either of our folders" @(
            "Looked in:",
            ("  " + (Join-Path $ourDirs.early $STATE_FILE)),
            ("  " + (Join-Path $ourDirs.override $STATE_FILE)),
            "",
            "The DLL rewrites this file on EVERY boot (WriteArmState, called at",
            "the end of CommitArming). Its absence means one of:",
            "  - the game has not been launched since a v4.5.0 DLL was deployed;",
            "  - the deployed DLL is older than v4.5.0;",
            "  - CommitArming returned early because gWantCount was 0, i.e. not",
            "    one SyncDat call ran - which is a DLL defect, not a user state.",
            "Nothing here is evidence about the armed tier either way.")
    }
    Write-Output ("{0,-38} {1,-6} {2}" -f "package", "tag", "reason / freshness")
    foreach ($r in ($rows | Sort-Object Role, Base)) {
        $live = Join-Path $r.Dir ($r.Base + ".dat")
        $fresh = "live file MISSING"
        if (Test-Path $live) {
            $fi = Get-Item -LiteralPath $live
            if ([uint64]$fi.Length -eq $r.LiveSize -and [uint64]$fi.LastWriteTimeUtc.ToFileTimeUtc() -eq $r.LiveTime) {
                $fresh = "live file still matches this row"
            } else {
                # NOT cosmetic. The DLL's steady-state check is exactly these
                # four stats, so a mismatch means the next boot WILL re-copy -
                # and it also means something (an installer, an sc4pac package
                # update, or this script) has moved the bytes since that boot.
                $fresh = "STALE - live file changed since that boot"
            }
        }
        Write-Output ("{0,-38} {1,-6} {2}" -f $r.Base, $r.Tag, ($r.Reason + " [" + $fresh + "]"))
    }
    $armed = @($rows | Where-Object { $_.Tag -ne "off" })
    $tiers = @($armed | Where-Object { $TIER_TAGS -contains $_.Tag } | ForEach-Object { $_.Tag } | Sort-Object -Unique)
    Write-Output ""
    Write-Output ("STATE: {0} row(s) - {1} armed, {2} inert" -f $rows.Count, $armed.Count, ($rows.Count - $armed.Count))
    if ($tiers.Count -gt 1) {
        Write-Warning ("armed packages DISAGREE on the tier: {0}. That split is the defect that put stock art into a scaled runtime on 2026-08-29." -f ($tiers -join ", "))
    } elseif ($tiers.Count -eq 1) {
        Write-Output ("all tier packages agree on '{0}'" -f $tiers[0])
    }
}

# ===========================================================================
# 6. -Status - the CONTENT-derived report
# ===========================================================================
function Show-State {
    $pkg = Get-Census
    $state = @{}
    foreach ($r in (Read-ArmState)) { $state[$r.Base] = $r }
    Write-Output ""
    Write-Output ("{0,-38} {1,-13} {2,-26} {3}" -f "package", "live", "how", "STATE.txt")
    Write-Output ("-" * 92)
    $shown = 0
    $disagree = @()
    foreach ($base in ($pkg.Keys | Sort-Object)) {
        $e = $pkg[$base]
        if ($e.Payloads.Count -eq 0 -and -not $e.Live) { continue }
        $got = Get-LiveTag $e
        $st = "-"
        if ($state.ContainsKey($base)) {
            $st = $state[$base].Tag
            if ($got.Tag -ne $st -and $got.How -ne "absent" -and $st -ne "-") { $disagree += $base }
        }
        Write-Output ("{0,-38} {1,-13} {2,-26} {3}" -f $base, $got.Tag, $got.How, $st)
        $shown++
    }
    if ($shown -eq 0) {
        Deny "found NO SC4UIScale packages in this tree" @(
            "Looked in:",
            ("  " + $ourDirs.early),
            ("  " + $ourDirs.override),
            "",
            "A package census of zero is a broken instrument, never a clean",
            "install. This is the exact shape of the 2026-08-06 (#144) and",
            "2026-08-29 failures: a scan that matched nothing reported",
            "'nothing of ours is live' while everything was.")
    }
    if ($disagree.Count -gt 0) {
        # TWO INDEPENDENT INSTRUMENTS. The content scan reads the bytes on disk
        # now; STATE.txt records what the DLL armed at last boot. They disagree
        # exactly when something moved the bytes since - which is normal right
        # after this script runs, and a real finding at any other time.
        Write-Warning ("{0} package(s) where the bytes on disk disagree with STATE.txt: {1}. Expected right after this script arms a tier (the DLL re-stamps at next boot); suspicious otherwise." -f $disagree.Count, ($disagree -join ", "))
    }
    # Packages the DLL drives that have NO payload on disk: a shipping gap, and
    # the shape of #119 / #196 - a package wired in one list but not the other.
    $missing = @($roster | Where-Object {
        $_.Kind -ne "plain" -and (-not $pkg.Contains($_.Base) -or $pkg[$_.Base].Payloads.Count -eq 0) })
    if ($missing.Count -gt 0) {
        Write-Warning ("{0} package(s) have a SyncDat call in ScaleTier.cpp but NO .uipay payload on disk: {1}. ArmOne falls back to .off for these, so they are inert at every tier." -f $missing.Count, (($missing | ForEach-Object { $_.Base }) -join ", "))
    }
    # ...and the inverse: bytes on disk that no call site drives. That package
    # will sit at whatever it was last given, forever.
    $orphan = @($pkg.Keys | Where-Object { $b = $_; -not ($roster | Where-Object { $_.Base -eq $b }) })
    if ($orphan.Count -gt 0) {
        Write-Warning ("{0} package(s) on disk have NO SyncDat call site in ScaleTier.cpp: {1}. Nothing follows the tier for them - this is the #119/#196 shape." -f $orphan.Count, ($orphan -join ", "))
    }
    if (Test-Path $ini) {
        $t = Get-Content -LiteralPath $ini -Raw
        $a = if ($t -match '(?m)^AutoScale\s*=\s*(\S+)') { $Matches[1] } else { "?" }
        $f = if ($t -match '(?m)^ScaleFactor\s*=\s*(\S+)') { $Matches[1] } else { "?" }
        Write-Output ""
        Write-Output ("ini: AutoScale={0} ScaleFactor={1}   ({2})" -f $a, $f, $ini)
    } else {
        Write-Warning ("no SC4UIScale.ini at {0} - the tier cannot be set without it." -f $ini)
    }
    $font = Join-Path $our "FontStyle.ini"
    if (Test-Path $font) {
        $h = (Get-FileHash -LiteralPath $font -Algorithm SHA256).Hash
        $which = "unrecognised"
        foreach ($t in $TIER_TAGS) {
            $c = Join-Path $our ("FontStyle-{0}.ini" -f $t)
            if ((Test-Path $c) -and (Get-FileHash -LiteralPath $c -Algorithm SHA256).Hash -eq $h) { $which = $t }
        }
        Write-Output ("FontStyle.ini matches: {0}" -f $which)
    }
    if ($legacy.Count -gt 0) {
        Write-Warning ("{0} pre-4.5.0 rename-layout file(s) are still in this tree (e.g. {1}). Arming is REFUSED until they are converted." -f $legacy.Count, $legacy[0].Name)
    }
}

if ($ShowState) { Show-ArmState; exit 0 }
if ($Status) { Show-State; exit 0 }
if (-not $Tier -and -not $Auto) {
    $labels = (($tierTable | ForEach-Object { $_.Label }) + @("1")) | Sort-Object -Unique
    Deny "nothing asked for" @(
        ("Give -Tier <" + ($labels -join "|") + ">, or -Auto, or -Status, or -ShowState."))
}

# --- resolve the requested tier against the DERIVED table -------------------
$wantTag = $null      # payload tag for the tier packages; $null means stock
$isStock = $false
if ($Tier) {
    $f = 0.0
    if (-not [double]::TryParse($Tier, [Globalization.NumberStyles]::Float,
            [Globalization.CultureInfo]::InvariantCulture, [ref]$f)) {
        Deny "-Tier '$Tier' is not a number" @()
    }
    if ($f -le 1.01) {
        $isStock = $true
    } else {
        # Same +/-0.01 window the DLL matches with, so "2.0" and "2" and "1.50"
        # all land where the player expects.
        $row = $tierTable | Where-Object { $f -ge ($_.Factor - 0.01) -and $f -le ($_.Factor + 0.01) } | Select-Object -First 1
        if (-not $row) {
            Deny "-Tier $Tier matches no row in kPackages" @(
                "Supported tiers, DERIVED from src\ScaleTier.cpp right now:",
                ("  " + ((($tierTable | ForEach-Object { $_.Label }) + @("1 (stock baseline)")) -join ", ")),
                "",
                "This is the same refusal BootState's C5 check makes in the DLL:",
                "an unsupported factor scales the geometry while the art layer",
                "stays on whatever was armed last boot.")
        }
        $wantTag = $row.Tag
    }
}

# --- EVERY REFUSAL THAT CAN BE MADE, IS MADE, BEFORE ANYTHING IS WRITTEN ----
# The census and both of its guards run HERE and not beside the swap loop, so
# a refusal cannot leave the ini naming a tier this run then declined to arm.
# That mixed state is worse than either half: the geometry scales by the ini's
# number while the art sits at whatever the last successful run left, which is
# the "2x artwork inside 1.5x boxes" screen this file's own header opens with.
$census = Get-Census
if ($census.Count -eq 0) {
    Deny "found NO SC4UIScale packages in this tree" @(
        "Looked in:", ("  " + $ourDirs.early), ("  " + $ourDirs.override),
        "",
        "Arming zero packages is a broken instrument, never a clean install.")
}

# REFUSE BEFORE WRITING when nothing in this tree can be armed at all. The
# post-swap check at the end of the run is the backstop; this one exists so the
# ini is not left naming a tier that was never armed.
$armable = @($census.Keys | Where-Object {
    $b = $_
    $census[$b].Payloads.Count -gt 0 -and
    ($roster | Where-Object { $_.Base -eq $b -and $_.Kind -ne "plain" })
})
if ($armable.Count -eq 0) {
    Deny "nothing in this tree can be armed" @(
        ("$($census.Count) package name(s) are on disk and $($roster.Count) SyncDat call sites were"),
        "parsed out of ScaleTier.cpp, but not one package is BOTH driven by the",
        "tier AND carrying a .uipay payload.",
        "",
        "That is a broken instrument, not a clean install - and it is the exact",
        "state the old regex produced silently on 2026-08-29 before printing",
        "'packages: 0 rename(s)' and exiting 0.")
}

# REFUSE A TIER NOTHING IS BUILT FOR. This is the same check as the DLL's
# BootState C6: kPackages carries a 4.0 row that no package has ever been built
# for, so ScaleFactor=4 passes every other test, arms nothing, and takes the
# in-game selector down with it.
if ($wantTag) {
    $havePay = @($census.Keys | Where-Object { $census[$_].Payloads.ContainsKey($wantTag) })
    if ($havePay.Count -eq 0) {
        $built = @($census.Keys | ForEach-Object { $census[$_].Payloads.Keys } | Sort-Object -Unique)
        Deny "tier $Tier is a supported factor but NO package on disk carries a .$wantTag.uipay payload" @(
            ("Payload tags actually present in this tree: " + ($built -join ", ")),
            "",
            "Arming it anyway would fall every package back to .off - every",
            "package inert while the geometry still scales by $Tier, and the",
            "stock-tier selector gone with them. Same refusal the DLL's",
            "BootState C6 check makes.")
    }
}

# --- the game holds these files open; wait, never kill ----------------------
# Only for the LIVE tree. A scratch tree is not open in anything, and making a
# dry run block on a running game would mean the rig can only be tested when
# the thing it tests is not running.
if ($isLiveTree) {
    $waited = 0
    while ($p = Get-Process -Name "SimCity 4" -ErrorAction SilentlyContinue) {
        if ($waited % 30 -eq 0) {
            # -f BINDS TIGHTER THAN +, so a parenthesised concatenation gets
            # formatted only on its LAST fragment and the earlier {0}/{1} ship
            # through LITERALLY - observed 2026-08-15 as "pid {0} ... waiting
            # {1}s". Build the message FIRST, format LAST.
            $msg = "SimCity 4 (pid {0}) is running - waiting {1}s. Close it; " +
                "NOT killing it, it is elevated and holds the dats open."
            Write-Warning ($msg -f $p.Id, $waited)
        }
        Start-Sleep -Seconds 5; $waited += 5
    }
}

# ===========================================================================
# 7. THE SCREEN HALF
# ===========================================================================
# A tier is only meaningful against the resolution it is judged on, so setting
# one without the other is half a transition. Both files are ini-shaped but
# live in different places and one of them silently overrides the other.
#
# THIS RUNS BEFORE ANY TIER BRANCH, ON PURPOSE. It used to sit at the bottom
# and never executed for -Tier 1, because that path exits at its own banner -
# so the one transition most likely to want a window (the 1x baseline) was the
# one that silently skipped the screen change.
function Set-IniKeyNoBom([string] $path, [hashtable] $pairs) {
    # NEVER a BOM (standing order for every SC4 ini) and never Set-Content,
    # whose default encoding is the ANSI codepage. Read bytes, assert, write
    # UTF8 with no preamble.
    $bytes = [IO.File]::ReadAllBytes($path)
    if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
        throw "$path already has a BOM - refusing to rewrite it"
    }
    $txt = [Text.Encoding]::UTF8.GetString($bytes)
    foreach ($k in $pairs.Keys) {
        $rx = New-Object Text.RegularExpressions.Regex(
            ('(?mi)^(\s*' + [Regex]::Escape($k) + '\s*=\s*).*$'))
        $m = $rx.Matches($txt)
        if ($m.Count -ne 1) { Write-Warning ("{0}: matched {1}x - not written" -f $k, $m.Count); continue }
        $txt = $rx.Replace($txt, ('${1}' + $pairs[$k]), 1)
        Write-Output ("  {0,-16} = {1}" -f $k, $pairs[$k])
    }
    [IO.File]::WriteAllBytes($path, (New-Object Text.UTF8Encoding $false).GetBytes($txt))
}

if ($Windowed -or $FullScreen -or $Width -or $Height) {
    # SC4GraphicsOptions.ini and dgVoodoo.conf belong to OTHER components, so
    # they stay at the REAL Plugins root / the game's Apps folder - they did
    # not move into our folder at v4.2.0 and they are not payloads.
    $gfx = Join-Path $Plugins "SC4GraphicsOptions.ini"
    $dg = "C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Apps\dgVoodoo.conf"
    if ($Windowed -and -not $Width) { $Width = 1024 }
    if ($Windowed -and -not $Height) { $Height = 768 }

    if ($Width -and $Height) {
        if (-not (Test-Path $gfx)) {
            Write-Warning ("no SC4GraphicsOptions.ini at {0} - resolution NOT changed." -f $gfx)
        } else {
            Write-Output "screen: SC4GraphicsOptions.ini"
            $mode = if ($FullScreen) { "FullScreen" } elseif ($Windowed) { "Windowed" } else { $null }
            $kv = @{ "WindowWidth" = "$Width"; "WindowHeight" = "$Height" }
            if ($mode) { $kv["WindowMode"] = $mode }
            Set-IniKeyNoBom $gfx $kv
        }
    }

    if (($Windowed -or $FullScreen) -and (Test-Path $dg)) {
        $bak = "$dg.before-set-tier"
        if (-not (Test-Path $bak)) { Copy-Item $dg $bak -Force; Write-Output "  backed up dgVoodoo.conf" }
        Write-Output "screen: dgVoodoo.conf (the setting that ACTUALLY decides windowing)"
        try {
            Set-IniKeyNoBom $dg @{
                "FullScreenMode" = $(if ($FullScreen) { "true" } else { "false" })
                "CaptureMouse"   = $(if ($FullScreen) { "true" } else { "false" })
            }
        } catch {
            # -f BINDS TIGHTER THAN +. Build the whole string first, THEN
            # format, or only the last fragment is formatted and the earlier
            # {0} ships LITERALLY (the same defect recorded in the wait loop
            # above; it was live in BOTH of this file's Program-Files warnings
            # until this rewrite).
            $m = "could not write dgVoodoo.conf ({0}). It is under Program Files - " +
                "run this shell as Administrator, or the window mode will NOT change."
            Write-Warning ($m -f $_.Exception.Message)
        }
    }
}

# ===========================================================================
# 8. THE INI
# ===========================================================================
if (-not (Test-Path $ini)) {
    # The old version went straight to [IO.File]::ReadAllBytes() under
    # $ErrorActionPreference = "Stop" and died on a terse .NET exception that
    # named neither the file's purpose nor the fix. Two Set-Tier runs failed
    # that way on 2026-08-29 before anyone read the stack.
    Deny "no SC4UIScale.ini at $ini" @(
        "That path is <our early folder>\SC4UIScale.ini - v4.4.0 moved the ini,",
        "log and gcap INTO the mod folder; the Plugins root carries the DLL and",
        "nothing else.",
        "",
        "If the folder above is a FALLBACK guess (see the 'folders:' line at the",
        "top of this run), the real one was not discovered by content - check",
        "that the tree really holds our packages.")
}
# NEVER write this file with a BOM (standing order).
$raw = [System.IO.File]::ReadAllBytes($ini)
if ($raw.Length -ge 3 -and $raw[0] -eq 0xEF -and $raw[1] -eq 0xBB -and $raw[2] -eq 0xBF) {
    Deny "SC4UIScale.ini has a BOM - refusing to touch it" @($ini)
}
$txt = [System.Text.Encoding]::UTF8.GetString($raw)
if ($Auto) {
    $txt = $txt -replace '(?m)^(AutoScale\s*=\s*).*$', '${1}1'
    Write-Output "ini: AutoScale=1 (the DLL picks the tier and syncs the layers itself)"
} else {
    $txt = $txt -replace '(?m)^(AutoScale\s*=\s*).*$', '${1}0'
    $txt = $txt -replace '(?m)^(ScaleFactor\s*=\s*).*$', ('${1}' + $Tier)
    Write-Output ("ini: AutoScale=0 ScaleFactor={0}" -f $Tier)
}
# SelectorAtStock - THE TWO WAYS OF BEING AT 1x WANT OPPOSITE THINGS.
# This script is the MEASUREMENT path: -Tier 1 exists to produce a true stock
# reference, so it asks for absolute isolation (no subclass, no timer, nothing
# installed) and writes 0. Every other tier writes 1, so a player who later
# picks 1x from the in-game selector still has the selector to climb back with.
$wantSel = if ($isStock -and -not $Auto) { "0" } else { "1" }
if ($txt -match '(?m)^SelectorAtStock\s*=') {
    $txt = $txt -replace '(?m)^(SelectorAtStock\s*=\s*).*$', ('${1}' + $wantSel)
} else {
    # Absent means the DLL is using its default (1). Add it under [UiSpike] so
    # the state is visible rather than implied - a setting you cannot see is a
    # setting nobody will think to check.
    $txt = $txt -replace '(?m)^(\[UiSpike\]\s*)$', ("`${1}`r`nSelectorAtStock=" + $wantSel)
}
Write-Output ("ini: SelectorAtStock={0}{1}" -f $wantSel,
    $(if ($wantSel -eq "0") { "  (stock reference: the DLL installs NOTHING)" }
      else { "  (1x keeps the in-game scale selector)" }))
if ($DryRun) {
    Write-Output "DRYRUN: ini NOT written."
} else {
    [System.IO.File]::WriteAllText($ini, $txt, (New-Object System.Text.UTF8Encoding($false)))
}

if ($Auto) {
    Write-Output "layers left as they are - the DLL will re-sync them at next boot."
    Show-State; exit 0
}

# ===========================================================================
# 9. ARMING - the content swap, one package at a time
# ===========================================================================
# THE PRIMITIVE, mirroring ScaleTier.cpp's ArmOne() step for step. Two rules
# it must not break, both of them the reason ArmOne is shaped the way it is:
#
#   ATOMIC. A bare Copy-Item fails MIXED - a truncated dat under this tier's
#   geometry, which is precisely the screen the redesign exists to eliminate.
#   Stage to `<base>.dat.tmp`, then MOVE over the live name. The rename it
#   replaces failed inert; so must this.
#
#   NEVER DESTROY A LIVE FILE WE CANNOT REPLACE. A missing payload falls back
#   to `.off` (inert is the only safe wrong answer) and says so out loud; with
#   no payload at all the live file is left EXACTLY as found and the package is
#   counted FAILED, never silently skipped.
function Invoke-ArmOne {
    param([hashtable] $Entry, [string] $Base, [string] $Tag, [string] $Reason)
    $live = Join-Path $Entry.Dir ($Base + ".dat")
    $usedTag = $Tag
    $src = $null
    if ($Entry.Payloads.ContainsKey($Tag)) { $src = $Entry.Payloads[$Tag] }
    if (-not $src) {
        $alt = "(none)"
        # NAME THE NEAR MISS. Two spellings of the inverse package's payload
        # exist in this repo today and they disagree: the DLL asks ArmOne for
        # `1x` (PayloadTagOf("-1x") strips the hyphen) while
        # tools\payload\build_payloads.py maps `-1x` to `on` (TIER_TAGS /
        # INVERSE_TAG, read 2026-08-29). MigrateRenamesToPayloads writes `1x`.
        # So an UPGRADED install has .1x.uipay and a FRESHLY BUILT bundle has
        # .on.uipay, and only one of them is the name the DLL looks up. This
        # script does NOT paper over that by substituting - a rig that quietly
        # accepts either spelling would go green while the shipped path stays
        # broken. It arms what the DLL would arm (.off) and names both files.
        $near = @($Entry.Payloads.Keys | Where-Object { $_ -ne "off" })
        if ($near.Count -gt 0) { $alt = ($near -join ", ") }
        Write-Warning ("{0}: MISSING PAYLOAD {0}.{1}.uipay - falling back to .off, exactly as ArmOne does. This is a packaging defect; the package will be INERT. Payloads present: {2}" -f $Base, $Tag, $alt)
        if ($Entry.Payloads.ContainsKey("off")) { $src = $Entry.Payloads["off"]; $usedTag = "off" }
    }
    $was = (Get-LiveTag $Entry).Tag
    if (-not $src) {
        # NAME WHAT IT IS HOLDING. "failed" alone does not tell you whether the
        # screen will be wrong - the live file's current content does, and that
        # is the whole point of the warning two lines down.
        Write-Warning ("{0}: NO PAYLOAD AT ALL (not even .off). Leaving {0}.dat exactly as found (it currently holds '{1}') - never destroy a live file we cannot replace." -f $Base, $was)
        return [PSCustomObject]@{ Base = $Base; Status = "failed"; Tag = $Tag; Was = $was; Note = "no payload" }
    }
    if ((Test-Path $live) -and $was -eq $usedTag) {
        return [PSCustomObject]@{ Base = $Base; Status = "current"; Tag = $usedTag; Was = $was; Note = $Reason }
    }
    if ($DryRun) {
        return [PSCustomObject]@{ Base = $Base; Status = "would-copy"; Tag = $usedTag; Was = $was; Note = $Reason }
    }
    $tmp = $live + ".tmp"
    try {
        Copy-Item -LiteralPath $src -Destination $tmp -Force -ErrorAction Stop
    } catch {
        Write-Warning ("{0}: could not stage .{1}.uipay ({2}) - {0}.dat left untouched." -f $Base, $usedTag, $_.Exception.Message)
        return [PSCustomObject]@{ Base = $Base; Status = "failed"; Tag = $usedTag; Was = $was; Note = "stage failed" }
    }
    try {
        Move-Item -LiteralPath $tmp -Destination $live -Force -ErrorAction Stop
    } catch {
        Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue
        Write-Warning ("{0}: could not commit {0}.dat ({1}) - staged copy discarded, previous content intact." -f $Base, $_.Exception.Message)
        return [PSCustomObject]@{ Base = $Base; Status = "failed"; Tag = $usedTag; Was = $was; Note = "commit failed" }
    }
    $Entry.Live = $live
    return [PSCustomObject]@{ Base = $Base; Status = "copied"; Tag = $usedTag; Was = $was; Note = $Reason }
}

# ---------------------------------------------------------------------------
# THE 1x BASELINE IS A ONE-WAY TRIP WITHOUT THIS MANIFEST.
# ---------------------------------------------------------------------------
# A dependency-gated package that is currently inert is ambiguous: its mod may
# be absent (leave it alone), or it may simply be sitting at a 1x baseline
# (arm it). STATE.txt cannot settle it - CommitArming writes only "armed" or
# "gated off or no tier match" into the reason column (read 2026-08-29), so the
# two cases share one string. So -Tier 1 RECORDS what it switched off and the
# next real tier restores exactly that set, instead of guessing. Observed
# 2026-08-18 without it: "0 rename(s); 11 family(ies) left dependency-gated
# off", i.e. the 3x tier silently had no art.
$restoreFile = Join-Path $our ".sc4uiscale-tier1-restore.txt"
$forced = New-Object System.Collections.Generic.HashSet[string]
if ($isStock) {
    $live = @()
    foreach ($base in ($census.Keys | Sort-Object)) {
        $e = $census[$base]
        if ($e.Payloads.Count -eq 0) { continue }
        $t = (Get-LiveTag $e).Tag
        if ($TIER_TAGS -contains $t) { $live += $base }
    }
    if (-not $DryRun) { Set-Content -LiteralPath $restoreFile -Value $live -Encoding UTF8 }
    Write-Output ("1x: recorded {0} armed package(s) so a later tier can restore them." -f $live.Count)
} elseif (Test-Path $restoreFile) {
    foreach ($line in (Get-Content -LiteralPath $restoreFile)) {
        $rec = $line.Trim()
        if (-not $rec) { continue }
        # Tolerate the pre-4.5.0 record format, which was keyed "dir|name".
        if ($rec.Contains("|")) { $rec = $rec.Substring($rec.LastIndexOf("|") + 1) }
        [void]$forced.Add($rec)
    }
    Write-Output ("restoring {0} package(s) recorded by the 1x baseline." -f $forced.Count)
}

# ---------------------------------------------------------------------------
# The swap itself.
# ---------------------------------------------------------------------------
$results = @()
$gated = @()
$notTierGated = @()
foreach ($base in ($census.Keys | Sort-Object)) {
    $e = $census[$base]
    if ($e.Payloads.Count -eq 0) { continue }   # nothing to swap from; reported below
    $r = $roster | Where-Object { $_.Base -eq $base } | Select-Object -First 1
    $kind = if ($r) { $r.Kind } else { $null }
    if (-not $kind) {
        # Payloads on disk, no SyncDat call site. The DLL will never move this
        # package, so neither will we - but it is named, loudly, because that
        # is the #119 / #196 shape (WarriorUI, CsiIcons: wired into the deploy
        # and never into the tier list, so they froze at one tier for months).
        $notTierGated += ("{0} (no SyncDat call site in ScaleTier.cpp)" -f $base)
        continue
    }
    if ($kind -eq "plain") {
        # WebText. Its gate is the Web Button Improvement Mod's presence, not
        # the tier - SyncDat(docPlugins, L"z_SC4UIScale_WebText", L"",
        # !webBtnPresent). Touching it here would arm it against a mod that
        # owns the region website button.
        $notTierGated += ("{0} (gated on a mod, not on the tier)" -f $base)
        continue
    }
    if ($kind -eq "inverse") {
        # THE ONE PACKAGE ARMED BY THE ABSENCE OF A TIER.
        $tag = if ($isStock) { $r.LiteralTag } else { "off" }
        $results += (Invoke-ArmOne $e $base $tag $(if ($isStock) { "armed (inverse gate: stock tier)" } else { "inverse gate: a tier is active" }))
        continue
    }
    # tier package
    if ($isStock) {
        $results += (Invoke-ArmOne $e $base "off" "stock baseline: every tier package inert")
        continue
    }
    $currently = (Get-LiveTag $e).Tag
    if ($DEPENDENCY_GATED.Contains($base) -and $currently -eq "off" -and
        -not $forced.Contains($base) -and -not $ArmGated) {
        $gated += $base
        continue
    }
    $results += (Invoke-ArmOne $e $base $wantTag "armed")
}

# ---------------------------------------------------------------------------
# REPORT, then the zero-refusal.
# ---------------------------------------------------------------------------
Write-Output ""
Write-Output ("{0,-38} {1,-6} {2,-12} {3}" -f "package", "tag", "result", "was")
Write-Output ("-" * 78)
foreach ($r in $results) {
    Write-Output ("{0,-38} {1,-6} {2,-12} {3}" -f $r.Base, $r.Tag, $r.Status, $r.Was)
}
foreach ($g in ($gated | Sort-Object)) {
    Write-Output ("{0,-38} {1,-6} {2,-12} {3}" -f $g, "off", "left inert", "dependency-gated; -ArmGated overrides")
}
foreach ($n in ($notTierGated | Sort-Object)) { Write-Output ("  not tier-gated: " + $n) }

$copied = @($results | Where-Object { $_.Status -eq "copied" -or $_.Status -eq "would-copy" }).Count
$current = @($results | Where-Object { $_.Status -eq "current" }).Count
$failed = @($results | Where-Object { $_.Status -eq "failed" }).Count
$summary = "packages: {0} swapped, {1} already correct, {2} FAILED, {3} left dependency-gated, {4} not tier-gated"
Write-Output ""
Write-Output ($summary -f $copied, $current, $failed, $gated.Count, $notTierGated.Count)

# ZERO IS A RED FAILURE. Not a pass, not a warning, not exit 0. The whole
# reason this file was rewritten is that its predecessor printed
# "packages: 0 rename(s)" and exited 0 while arming nothing at all, twice in
# one day, in the instrument every other test is verified with.
if (($copied + $current + $failed) -eq 0) {
    Deny "arming touched ZERO packages" @(
        "$($census.Count) package name(s) were found on disk, $($roster.Count) call sites were",
        "parsed out of ScaleTier.cpp, and not one package was armed, confirmed",
        "or failed. That is a broken instrument, not a clean run.",
        "",
        "Look at: are there any .uipay payloads at all? (a tree that was never",
        "converted has none); did folder discovery fall back to the v4.2.0",
        "names and land somewhere empty? (see the 'folders:' line above).")
}
if ($failed -gt 0) {
    Write-Warning ("{0} package(s) FAILED to arm - each is holding bytes we did not choose. Read the lines above; a failure here is a wrong tier on screen, not a missing feature." -f $failed)
}
if ($wantTag -and (Test-Path $restoreFile) -and -not $DryRun) { Remove-Item -LiteralPath $restoreFile -Force }

# ===========================================================================
# 10. THE FONT
# ===========================================================================
# THE GAME READS THE FONT TABLE FROM <install>\Plugins, **NOT** FROM Documents.
# This script's first version copied it next to the packages in Documents -
# where nothing ever reads it - so two full 1.5x test launches ran with the 2x
# table live: 2x point sizes inside 1.5x boxes, a 33% oversize. Every clipped
# label in those screenshots was that.
#
# There are THREE probe sites and the order is
# <install>\Plugins -> <install> (i.e. Apps) -> the DBPF. Writing the wrong one
# leaves an older table winning silently.
#
# THE FONT IS NOT PAYLOADED. SyncFont still reads FontStyle<tag>.ini sources
# by their tagged names (ScaleTier.cpp: MatchesAnyTierFontSource /
# "%sFontStyle%s.ini"), so this half is unchanged by v4.5.0 - only the tag list
# is derived now instead of hand-written.
$gameDir = $env:SC4_GAME_DIR
if (-not $gameDir) { $gameDir = "C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe" }
$fontLive = Join-Path $gameDir "Plugins\FontStyle.ini"
if ($isStock) {
    # 1x BASELINE. Restore the user's ORIGINAL font table rather than any of
    # ours. The .user-original snapshot is what the installer preserved; if it
    # is absent the stock game table is simply the absence of a file, so we
    # remove ours rather than leave a scaled one winning silently.
    $orig = Join-Path $our "FontStyle.ini.user-original"
    try {
        if ($DryRun) {
            Write-Output "DRYRUN: font untouched."
        } elseif (Test-Path $orig) {
            Copy-Item -LiteralPath $orig -Destination $fontLive -Force -ErrorAction Stop
            Write-Output "font: restored FontStyle.ini.user-original (1x baseline)"
        } elseif (Test-Path $fontLive) {
            Remove-Item -LiteralPath $fontLive -Force -ErrorAction Stop
            Write-Output "font: removed our FontStyle.ini - the game falls back to its own table"
        }
    } catch {
        Write-Warning ("could not restore the font at {0} ({1}). Run as Administrator." -f $fontLive, $_.Exception.Message)
    }
    # Keep the Documents copy in step, or -Status reports the LAST tier's font
    # while the game runs on its own table - wrong in the safe-looking
    # direction, again.
    $docFont = Join-Path $our "FontStyle.ini"
    if (-not $DryRun) {
        if (Test-Path $orig) { Copy-Item -LiteralPath $orig -Destination $docFont -Force }
        elseif (Test-Path $docFont) { Remove-Item -LiteralPath $docFont -Force }
    }
    Show-State
    Write-Output ""
    Write-Output "1x BASELINE armed: every tier package holds its .off payload, stock font,"
    Write-Output "ScaleFactor=1. The log should say ScaleFactor=1.00 and every code patch"
    Write-Output "should be INERT (they all gate on factor > 1.01). This is the control to"
    Write-Output "compare a scaled tier against."
    exit 0
}

$src = Join-Path $our ("FontStyle-{0}.ini" -f $wantTag)
if (-not (Test-Path $src)) {
    Write-Warning ("FontStyle-{0}.ini missing from {1} - text will be wrong for this tier." -f $wantTag, $our)
} elseif (-not (Test-Path (Split-Path $fontLive -Parent))) {
    Write-Warning ("install Plugins folder not found at {0} - set SC4_GAME_DIR" -f $gameDir)
} elseif ($DryRun) {
    Write-Output ("DRYRUN: would copy {0} -> {1}" -f $src, $fontLive)
} else {
    try {
        Copy-Item -LiteralPath $src -Destination $fontLive -Force -ErrorAction Stop
        Write-Output ("font: FontStyle-{0}.ini -> {1}" -f $wantTag, $fontLive)
    } catch {
        # -f BINDS TIGHTER THAN + - build first, format last (see above).
        $m = "could not write {0} ({1}). Run this shell as Administrator - " +
            "Program Files is ACL-protected and the game reads the font from THERE."
        Write-Warning ($m -f $fontLive, $_.Exception.Message)
    }
    # Keep the Documents copy in step too, so -Status reports the truth.
    Copy-Item -LiteralPath $src -Destination (Join-Path $our "FontStyle.ini") -Force
}

Show-State
Write-Output ""
Write-Output "Launch the game. The log should say ScaleFactor=$Tier, every package above"
Write-Output "should read '$wantTag', and CommitArming should report 0 FAILED."
