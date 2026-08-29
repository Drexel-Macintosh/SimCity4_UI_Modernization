# EXPORT-PUBLIC.ps1 - build the publishable repo as an ALLOWLIST EXPORT.
#
# WHY AN EXPORT AND NOT `git init` IN PLACE (task #108, section 5).
# The working tree is ~988 MB and ~30,000 files, of which about 6 MB and ~550
# files are publishable: an excluded-to-shipped ratio near 200:1. A .gitignore
# is a DENYLIST, and one gap in a denylist at that ratio ships a leak that is
# then in the history forever. Two further traps make in-place init worse:
#
#   * tools\research\submenus-dll-src\ contains memo33's FULL .git clone. A
#     `git init` at the repo root embeds a foreign repository.
#   * The tree lives in OneDrive, so anything committed is also sitting in
#     someone's cloud account with its own sync history.
#
# So: copy an explicit ALLOWLIST into a fresh directory outside OneDrive, run
# the leak scan THERE, and git init THERE. The .gitignore still ships (it is
# the second line of defence for whatever is added later), but it is not the
# thing being trusted tonight.
#
#   .\_packaging\EXPORT-PUBLIC.ps1                     -> %USERPROFILE%\sc4uiscale-public
#   .\_packaging\EXPORT-PUBLIC.ps1 -Dest D:\pub
#   .\_packaging\EXPORT-PUBLIC.ps1 -WhatIfOnly         list, copy nothing
#
# EXIT 1 IF THE LEAK SCAN FINDS ANYTHING. An exporter that ships on a warning
# is a denylist wearing a hat.

param(
    [string] $Dest,
    [switch] $WhatIfOnly,
    # Identity tokens to refuse. Supply your own; they are deliberately NOT
    # baked into this file - see tools\privacy_audit.py for why that mistake
    # made the auditor the leak.
    [string[]] $PiiToken = @()
)

$ErrorActionPreference = "Stop"
$proj = Split-Path -Parent $PSScriptRoot
if (-not $Dest) { $Dest = Join-Path $env:USERPROFILE "sc4uiscale-public" }

# --- refuse to export into somewhere that defeats the point ------------------
$destFull = [System.IO.Path]::GetFullPath($Dest)
if ($destFull -like "$proj*") { throw "Dest is inside the repo: $destFull" }
if ($destFull -match '(?i)onedrive|dropbox|google drive') {
    throw "Dest is inside a cloud-synced folder ($destFull). The whole point is to leave one."
}

# --- ALLOWLIST ---------------------------------------------------------------
# (relative dir, extensions). An empty extension list means "every file".
$ALLOW = @(
    @{ dir = "src";                  ext = @(".cpp", ".h", ".vcxproj", ".filters", ".sln", ".ini") }
    @{ dir = "vendor";               ext = @(".h", ".c", ".cpp", ".txt", ".md", ".cs") }
    @{ dir = "tools";                ext = @(".py", ".md", ".txt", ".ps1", ".cs", ".c", ".h") }
    @{ dir = "_tests";               ext = @(".ps1", ".py", ".md") }
    @{ dir = "_packaging";           ext = @(".ps1", ".md", ".ini", ".txt") }
    @{ dir = "_vanilla-reference";   ext = @(".md") }
)
$ROOT_FILES = @("README.md", "VERSION-HISTORY.txt", "LICENSE",
                "THIRD-PARTY-NOTICES.md", ".gitignore")
# ⛔ DROPPED 2026-08-06, user direction:
#   HANDOFF-TO-QWEN.md  - a stale internal hand-off to a delegation lane.
#                         Nothing a downloader or contributor needs.
#   FRESH-INSTALL.md    - a machine-restore checklist for ONE workstation
#                         ("what to preserve when this box is wiped"). Internal
#                         ops, and it described the touch quarantine.

# --- DENYLIST applied ON TOP (belt AND braces, deliberately) -----------------
# Every rule here duplicates something the allowlist should already exclude.
# That redundancy is the design: the two disagree loudly rather than quietly.
$DENY_DIR = @(
    "tools\research\submenus-dll-src",      # memo33's clone, incl. its .git
    "tools\research\morebuildingstyles",
    "tools\research\_checkpoints", "tools\research\_incoming",
    "tools\itemicons\_work", "tools\uimap\_work", "tools\uimap\emu\cache",
    "tools\uimap\diff\census", "tools\capture\out", "tools\upscale\test",
    "tools\dialog-static\src-credits", "tools\dialog-static\thirdparty-src",
    "tools\flyout-sim\renders",
    "_tests\captures", "_tests\golden", "_reviews",
    "__pycache__"
)
$DENY_NAME = @(
    # ---- SC4TouchControls is a SEPARATE PROJECT (2026-08-06, user direction).
    # This repository is SC4UIScale only. The touch plugin shares a git-less
    # working tree here for historical reasons - the two were one DLL until the
    # v2.30 split - but it is its own product, currently quarantined pending a
    # rewrite that is independent of UI scaling, and it does not belong in a
    # public SC4UIScale repo.
    # ⚠ These are EXCLUDED FROM THE EXPORT, NOT DELETED. The working tree keeps
    # them; the published repo never sees them.
    "SC4TouchControls.ini", "SC4TouchControls.sln", "SC4TouchControls.vcxproj",
    "SC4TouchControlsDllDirector.cpp",
    "TouchInputHandler.cpp", "TouchInputHandler.h",
    "GestureEngine.cpp", "GestureEngine.h",
    "CameraController.cpp", "CameraController.h",
    "version.h",                      # PLUGIN_VERSION_STR - the touch DLL's
    "HANDOFF-TO-QWEN.md", "FRESH-INSTALL.md",
    "HANDOFF.md", "RUN-SHEET-NEXT-SESSION.md",
    "HANDOFF-god-mode-flyouts.md", "BUILDER-CENSUS.md", "CONSTANT-MAP.md",
    "extracted-png-tgi.csv", "art-dims.csv", "idcollide.py",
    "FontStyle.default.ini", "FontStyle.candidate.ini",
    ".pii-tokens"
)
$DENY_PATTERN = @(
    "*_probe.py.throwaway",            # placeholder; the named ones follow
    # (dock_*_probe.py + the lane1/2 probes were deleted from the tree 2026-08-23)
    "lane1_*_probe.py", "lane2_*_probe.py", "lane4_*_probe.py",
    "*.log", "*.bak", "*.bak-*", "state.json", "*.dat", "*.ui", "*.png",
    "*.dll", "*.exe", "*.pdb", "package-list*.txt"
)
# ⚠ Directories whose *staged content* is third-party or game-derived. The
# extension rules above already drop the art; these drop the folders whole so
# a stray .txt inside one cannot ride along.
$DENY_DIR += @(
    "tools\itemicons\stage", "tools\itemicons\stage-15x", "tools\itemicons\stage-3x",
    "tools\itemicons\nam-1x", "tools\itemicons\nam-src", "tools\itemicons\nam-qfs",
    "tools\itemicons\nam2-1x", "tools\itemicons\nam2-qfs", "tools\itemicons\out",
    "tools\itemicons\nam-up-1.5", "tools\itemicons\nam-up-2", "tools\itemicons\nam-up-3",
    "tools\itemicons\t1", "tools\itemicons\t2",
    "tools\selective-safe\stage", "tools\selective-safe\stage-15x",
    "tools\selective-safe\stage-3x", "tools\selective-safe\superseded",
    "tools\selective-safe\bubble4x", "tools\selective-safe\bubble4x-15x",
    "tools\selective-safe\bubble4x-3x", "tools\selective-safe\thirdparty-ui",
    "tools\dialog-static\stage", "tools\dialog-static\stage-15x",
    "tools\dialog-static\stage-3x", "tools\dialog-static\superseded",
    "tools\oddballs\native2x", "tools\oddballs\converted2x",
    "tools\webtext\stage", "tools\packages\15x", "tools\packages\3x",
    "tools\uiscripts\extracted", "tools\uiscripts\extracted-plugins",
    "tools\dbpf\extracted", "tools\dbpf\extracted-submenus",
    "tools\upscale\preview", "tools\upscale\preview-15x",
    "tools\upscale\preview-3x", "tools\upscale\preview-hq"
)

function Test-Denied([string]$rel, [string]$name) {
    foreach ($d in $DENY_DIR)   { if ($rel -like "$d\*" -or $rel -eq $d) { return $true } }
    foreach ($d in $DENY_DIR)   { if ($rel -like "*\$d\*") { return $true } }
    if ($rel -like "*\stage-thirdparty*" -or $rel -like "*\stage-tp-*" -or
        $rel -like "*\thirdparty-art*" -or $rel -like "*extracted-exemplars-*") { return $true }
    if ($DENY_NAME -contains $name) { return $true }
    foreach ($p in $DENY_PATTERN) { if ($name -like $p) { return $true } }
    if ($rel -like "*\.git\*" -or $name -eq ".git") { return $true }
    return $false
}

# --- collect -----------------------------------------------------------------
$picked = New-Object System.Collections.Generic.List[object]
foreach ($f in $ROOT_FILES) {
    $p = Join-Path $proj $f
    if (Test-Path $p) { $picked.Add([pscustomobject]@{ full = $p; rel = $f }) }
    else { Write-Warning "root file missing: $f" }
}
foreach ($a in $ALLOW) {
    $base = Join-Path $proj $a.dir
    if (-not (Test-Path $base)) { continue }
    Get-ChildItem $base -Recurse -File | ForEach-Object {
        $rel = $_.FullName.Substring($proj.Length + 1)
        if (Test-Denied $rel $_.Name) { return }
        if ($a.ext.Count -and ($a.ext -notcontains $_.Extension.ToLower())) { return }
        $picked.Add([pscustomobject]@{ full = $_.FullName; rel = $rel })
    }
}
# ⚠ NOT `Measure-Object { ... } -Sum` - a scriptblock property silently
# returns nothing in PS 5.1 (it threw here, and elsewhere in this repo it has
# printed blank columns instead). Sum it in the open.
$totalBytes = 0
foreach ($x in $picked) { $totalBytes += (Get-Item $x.full).Length }
Write-Output ("allowlist: {0} file(s), {1:N2} MB" -f $picked.Count, ($totalBytes / 1MB))

# --- LEAK SCAN, BEFORE ANY COPY ---------------------------------------------
# Runs on the SELECTED set, not the whole tree: what is about to be published
# is the only thing whose cleanliness matters, and scanning it directly means
# no rule has to be trusted twice.
$rxUserPath = [regex]'(?i)[A-Za-z]:\\+Users\\+[^\\\s"''<>|]+'
$rxEmail    = [regex]'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}'
# ⚠ ADDED 2026-08-05 AFTER A SECOND, INDEPENDENT SWEEP FOUND WHAT THIS ONE
# COULD NOT SEE. The scan above had no hostname pattern, and SHIP-MANIFEST.md
# named this machine outright - inside a table row reporting ZERO hostname
# hits. The report of the leak was the leak, for the second time in one
# session (privacy_audit.py was the first).
# The lesson generalises: a scanner only finds the classes someone thought of,
# so its clean result means "none of THESE", never "nothing". Every class added
# here came from something a different instrument caught.
$rxHost     = [regex]("(?i)\b" + [regex]::Escape($env:COMPUTERNAME) + "\b")
$rxSteamId  = [regex]'\b7656119\d{10}\b'
$rxProdKey  = [regex]'\b[A-Z0-9]{5}-[A-Z0-9]{5}-[A-Z0-9]{5}-[A-Z0-9]{5}\b'
$leaks = New-Object System.Collections.Generic.List[string]
$vendorEmails = 0
foreach ($x in $picked) {
    $txt = Get-Content $x.full -Raw -ErrorAction SilentlyContinue
    if (-not $txt) { continue }
    foreach ($m in $rxUserPath.Matches($txt)) { $leaks.Add(("USERPATH {0}: {1}" -f $x.rel, $m.Value)) }
    # ⚠ EMAILS UNDER vendor\ ARE ATTRIBUTION, NOT A LEAK. nsgomez's own address
    # sits in his own LGPL headers; stripping it would break the notice we are
    # legally required to preserve. The exemption is scoped to vendor\ and
    # REPORTED below, never silent - an unannounced exemption is a hole.
    if ($x.rel -like "vendor\*") { $vendorEmails++ }
    else { foreach ($m in $rxEmail.Matches($txt)) { $leaks.Add(("EMAIL    {0}: {1}" -f $x.rel, $m.Value)) } }
    foreach ($m in $rxHost.Matches($txt))    { $leaks.Add(("HOSTNAME {0}: {1}" -f $x.rel, $m.Value)) }
    foreach ($m in $rxSteamId.Matches($txt)) { $leaks.Add(("STEAMID  {0}: {1}" -f $x.rel, $m.Value)) }
    foreach ($m in $rxProdKey.Matches($txt)) { $leaks.Add(("PRODKEY  {0}: {1}" -f $x.rel, $m.Value)) }
    # A binary that slipped past the extension rules would be unreadable as
    # text and could hide anything; refuse rather than guess.
    if ($txt -match "\x00\x00\x00\x00") { $leaks.Add(("BINARY?  {0}: contains NUL runs - not a text file" -f $x.rel)) }
    foreach ($t in $PiiToken) {
        if ($t -and $txt -match [regex]::Escape($t)) { $leaks.Add(("TOKEN    {0}: {1}" -f $x.rel, $t)) }
    }
}
if ($PiiToken.Count -eq 0) {
    Write-Warning ("no -PiiToken supplied: the by-NAME check did NOT run. " +
        "Path and email checks did. A scan that cannot see the thing is not " +
        "evidence the thing is gone.")
}
if ($leaks.Count) {
    Write-Output ""
    Write-Output ("LEAK SCAN FAILED - {0} hit(s), NOTHING COPIED:" -f $leaks.Count)
    $leaks | Select-Object -First 40 | ForEach-Object { Write-Output ("   " + $_) }
    if ($leaks.Count -gt 40) { Write-Output ("   ... and {0} more" -f ($leaks.Count - 40)) }
    exit 1
}
# ⚠ -f binds tighter than +, so formatting a parenthesised concatenation
# formats only the LAST string and the earlier {0} ships through literally.
# This repo has now hit that twice. Build the message, THEN format it.
$msg = "leak scan: clean (paths checked in every selected file; emails checked " +
       "in every file EXCEPT the {0} under vendor\ , where an upstream author's " +
       "address is required attribution)"
Write-Output ($msg -f $vendorEmails)

if ($WhatIfOnly) { Write-Output "-WhatIfOnly: stopping before the copy."; exit 0 }

# --- copy --------------------------------------------------------------------
if (Test-Path $destFull) { throw "Dest already exists: $destFull (remove it, or pass a new -Dest)" }
New-Item -ItemType Directory -Path $destFull -Force | Out-Null
foreach ($x in $picked) {
    $target = Join-Path $destFull $x.rel
    $dir = Split-Path -Parent $target
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
    Copy-Item $x.full $target -Force
}
Write-Output ("exported {0} file(s) -> {1}" -f $picked.Count, $destFull)
Write-Output ""
Write-Output "NEXT, in the exported directory (NOT in the working tree):"
Write-Output "    git init && git add -A && git commit -m ""SC4UIScale: initial public release"""
Write-Output ""
Write-Output "⚠ Do NOT commit binaries. Releases are freshly built, byte-scanned"
Write-Output "  artifacts attached to a GitHub Release - never tracked files."
