# Paths are RESOLVED, not hard-coded: Documents may be redirected by
# OneDrive, and the repo may be cloned anywhere (task #108).
# Wait for SimCity 4 to close, then deploy the freshly built SC4UIScale.dll
# plus the SelectiveArt AND DialogStatic tier dats. The game runs ELEVATED
# and holds these files open - never kill it (standing order). Polls 5 s.
$ErrorActionPreference = "Stop"
$proj = (Split-Path -Parent $PSScriptRoot)
$plug = (Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'SimCity 4\Plugins')
# v4.2.0 (subfolder move): OUR files live in Plugins\010-SC4UIScale\ - the
# number prefix keeps us loading BEFORE 050-load-first\ and 150-mods\, so the
# root packages keep LOSING to the mods they are designed to lose to (that
# losing is the compatibility gate). zzz-SC4UIScale\ stays a TOP-LEVEL folder,
# unchanged - its whole purpose is sorting after those same mod folders.
$our = Join-Path $plug '010-SC4UIScale'

# REFUSE A SC4PAC-MANAGED TREE (v4.5.2). This dev deploy hand-places the whole
# install; run against a tree that also carries the sc4pac packages it would
# create a SECOND copy of every TGI (and the hand copy in 010-\ out-sorts the
# managed one in 050-load-first\), then the converter would rewrite files
# sc4pac's manifest owns. The two install channels must never share a tree.
$sc4pacDirs = @(Get-ChildItem $plug -Directory -Recurse -Filter '*.sc4pac' -ErrorAction SilentlyContinue |
    Where-Object { Get-ChildItem $_.FullName -Recurse -Filter 'z_SC4UIScale_*' -ErrorAction SilentlyContinue |
                   Select-Object -First 1 })
if ($sc4pacDirs.Count) {
    Write-Output "REFUSING to deploy: this Plugins tree carries a sc4pac-managed copy of the mod:"
    $sc4pacDirs | ForEach-Object { Write-Output "  $($_.FullName)" }
    Write-Output "Remove it first (sc4pac remove a-drexel:sc4-ui-scale a-drexel:sc4-ui-scale-mod-overrides)"
    Write-Output "or deploy into a different tree. A dual install is two live providers per TGI."
    exit 1
}
if (-not (Test-Path $our)) { New-Item -ItemType Directory $our | Out-Null }

# #104: the game HANGS ON SHUTDOWN often enough that this loop blocked twice in
# one session (2026-08-03) - the window closes, the PROCESS does not exit, and
# the wait spun silently until the user noticed and used End Task. Silence was
# the real defect: the operator could not tell "still playing" from "hung".
#
# We do NOT kill the process. Standing order: the game runs ELEVATED and holds
# the DLL and the dats open; killing it risks a half-written file. This only
# reports, and keeps waiting, so the deploy remains safe to leave running.
$waited = 0
$nagAt = 60
while ($p = Get-Process -Name "SimCity 4" -ErrorAction SilentlyContinue) {
    if ($waited -ge $nagAt) {
        # -f binds tighter than +, so it formatted only the LAST string of a
        # parenthesised concatenation and the earlier {0}/{1} shipped through
        # literally (observed 2026-08-03: "pid {0} still running after {1}s").
        # A wait-loop that cannot say what it is waiting on is the exact defect
        # this warning exists to cure, so build the message first, format last.
        $msg = "SimCity 4 (pid {0}) still running after {1}s. If you have already " +
            "closed the window this is task #104 - the process outlives it. " +
            "End Task on 'SimCity 4' and this deploy will continue by itself. " +
            "NOT killing it here: the game is elevated and holds the dats open."
        Write-Warning ($msg -f $p.Id, $waited)
        $nagAt += 60
    }
    Start-Sleep -Seconds 5
    $waited += 5
}
if ($waited -ge 60) {
    Write-Output ("game exited after {0}s of waiting - deploying now." -f $waited)
}
# ---- ONE-TIME LEGACY-LAYOUT MIGRATION (v4.2.0) ------------------------------
# Before v4.2.0 all of these lived at the Plugins ROOT. Two classes:
#   MOVE  - user state the deploy never writes (settings, history, snapshots):
#           carried into 010-SC4UIScale\ if not already there.
#   DELETE - build products the deploy/DLL recreate in the new home. The root
#           DLL is the critical one: left behind, BOTH copies would load as
#           two directors. Runs only when legacy files exist; logs each file.
# MEASURED on the maiden boot: the game's DLL LOADER IS TOP-LEVEL ONLY
# (recursive for dats, NOT for DLLs - no log, no director from a subfolder).
# So the DLL - and ONLY the DLL - lives at the root.
#
# v4.4.0 ROOT CLEANUP reversed the rest of that set. Through 4.3.1 the ini,
# log, gcap and #104 csv resolved 'beside the DLL' and so piled up at the
# Plugins root, where every other DLL mod leaves two or three files and we
# left five. They now resolve through ScaleTier::GetOurFilePath into
# 010-SC4UIScale\, so the folder carries everything a user (or sc4pac)
# would want to remove. The DLL itself has no choice and stays.
$MIGRATE_MOVE = @("SC4UIScale.compare-state.txt", ".sc4uiscale-tier1-restore.txt",
    "FontStyle.ini.user-original")
$MIGRATE_DELETE = @("FontStyle.ini",
    "FontStyle.ini.x1-disabled", "FontStyle-2x.ini", "FontStyle-15x.ini",
    "FontStyle-3x.ini")
# v4.4.0: move the loose files OFF the root into 010-SC4UIScale\. The DLL
# does this itself at boot too (ScaleTier::MigrateRootLooseFiles); doing it
# here as well means a deploy leaves a clean root even when the game is
# never launched afterwards, so the root-is-clean check can run at once.
# v4.5.0: SC4UIScale.ini IS NOT IN THIS LIST ANY MORE. It belongs at the
# Plugins root - a package manager wipes the versioned package folder on every
# update, so an ini kept inside it loses the player's tier on each version bump.
# Leaving it here made the ini PING-PONG: the deploy moved it into
# 010-SC4UIScale\, the DLL's own migration moved it back out on the next launch,
# forever. Worse, the "subfolder copy wins" branch below DELETES the root copy
# when both exist - which discards the settings the game is actually using in
# favour of a stale one. The log and gcap do still belong in the folder.
foreach ($name in @("SC4UIScale-104.csv", "SC4UIScale.gcap")) {
    $old = Join-Path $plug $name
    if (Test-Path $old) {
        $new = Join-Path $our $name
        if (Test-Path $new) {
            Remove-Item $old -Force
            Write-Output ("  ROOT CLEANUP (subfolder copy wins): " + $name)
        } else {
            Move-Item $old $new -Force
            Write-Output ("  ROOT CLEANUP root -> 010-SC4UIScale: " + $name)
        }
    }
}
# Build/dev leftovers and the regenerated log: delete, never carry forward.
foreach ($name in @("SC4UIScale.ini.bak2", "SC4UIScale.log")) {
    $old = Join-Path $plug $name
    if (Test-Path $old) {
        Remove-Item $old -Force
        Write-Output ("  ROOT CLEANUP (removed stale root copy): " + $name)
    }
}
foreach ($name in $MIGRATE_MOVE) {
    $old = Join-Path $plug $name
    if (Test-Path $old) {
        $new = Join-Path $our $name
        if (Test-Path $new) {
            Remove-Item $old -Force
            Write-Output ("  MIGRATED (root copy dropped, new home already has it): " + $name)
        } else {
            Move-Item $old $new -Force
            Write-Output ("  MIGRATED root -> 010-SC4UIScale: " + $name)
        }
    }
}
foreach ($name in $MIGRATE_DELETE) {
    $old = Join-Path $plug $name
    if (Test-Path $old) {
        if ($name -eq "SC4UIScale.log") {
            # Preserve the legacy log's capture before dropping it.
            $capDir = "$proj\_tests\captures"
            if (-not (Test-Path $capDir)) { New-Item -ItemType Directory $capDir | Out-Null }
            $stamp = (Get-Item $old).LastWriteTime.ToString("yyyy-MM-dd-HHmmss")
            $dst = Join-Path $capDir ("SC4UIScale-{0}.log" -f $stamp)
            if (-not (Test-Path $dst)) { Copy-Item $old $dst -Force }
        }
        Remove-Item $old -Force
        Write-Output ("  MIGRATED (legacy root copy removed): " + $name)
    }
}
# Legacy root packages: any remaining z_SC4UIScale_* at the root. Fresh copies
# land in 010-SC4UIScale\ below; a same-named root leftover would only confuse
# audits (root loads EARLIER, so it cannot even shadow the new copy). MenuFix
# and other hand-placed strays are MOVED, not deleted - they are user
# decisions, not build products.
Get-ChildItem $plug -Filter "z_SC4UIScale_*" -File -ErrorAction SilentlyContinue |
    ForEach-Object {
        $new = Join-Path $our $_.Name
        if (Test-Path $new) {
            Remove-Item $_.FullName -Force
            Write-Output ("  MIGRATED (stale root package removed): " + $_.Name)
        } else {
            Move-Item $_.FullName $new -Force
            Write-Output ("  MIGRATED root package -> 010-SC4UIScale: " + $_.Name)
        }
    }
# (v4.2.0: this snapshot MOVED here, AFTER the migration - it reads the
# 010-SC4UIScale folder, and on a legacy install the families are not
# THERE until the migration runs. Snapshotting first recorded nothing
# and the restore left two tiers armed - caught by Test-DatIntegrity
# on the migration's first run.)
# ---- ARMED-TIER SNAPSHOT (2026-08-19) --------------------------------------
# Which tier is LIVE right now, per tier-managed family, recorded BEFORE any
# copy runs. The family blocks below each hard-code 2x as the armed tier; on a
# 1.5x or 3x machine that leaves TWO armed packages and the load order decides
# which art the player gets. Restored verbatim at the end of this script.
# The DLL owns this decision (ScaleTier resolves the factor from the screen
# when AutoScale=1); this script owns only whether the bytes are current.
# SelectiveArt EXCLUDED (v4.0.3): it no longer has a tier-tagged LIVE
# filename to detect ("z_SC4UIScale_SelectiveArt-2x.dat" never exists any
# more - see the STABLE-FILENAME PILOT block below). It gets its own
# dedicated snapshot/restore, not this generic by-filename one.
# ⚠ MEASURED 2026-08-30: on a payload-layout tree (every v4.5.x install) the
# START-of-run snapshot below always comes up EMPTY - live files are stable
# `<base>.dat` names, never the `-<tier>.dat` names this list matches - so
# $ARMED_BEFORE only ever describes the MID-RUN rename-layout state the
# Copy-Item blocks create, and the payload converter at the end of this
# script supersedes whatever the restore decided (stable-dat content comes
# from the converter's tier fallback, and the DLL re-arms from the ini at
# next boot regardless). The block is kept because Build-Dist regex-parses
# this file and because removing live-tree-touching machinery deserves its
# own measured session - but do NOT extend this list: it is not the tier
# authority (ScaleTier.cpp's SyncDat sites are), and it covers 5 of ~20
# tier-managed packages by design of its era, not by decision.
$TIER_FAMILIES = @(
    @{ Sub = "";                 Base = "z_SC4UIScale_DialogStatic" },
    @{ Sub = "";                 Base = "z_SC4UIScale_ItemIcons"    },
    @{ Sub = "zzz-SC4UIScale";   Base = "z_SC4UIScale_ItemIconsSub" },
    @{ Sub = "zzz-SC4UIScale";   Base = "z_SC4UIScale_CsiIcons"     },
    @{ Sub = "zzz-SC4UIScale";   Base = "z_SC4UIScale_UncoveredIcons" }
)
# THE FILES ARE NOT A RELIABLE SOURCE FOR THIS. Reading "which tier is
# armed" off disk works only while exactly one is armed - and the very bug this
# block exists to fix leaves TWO armed, at which point a first-match scan picks
# whichever tier sorts first and locks in the wrong answer. That happened on the
# first run of this code: a 3x install had 2x and 3x both live, the scan chose
# 2x, and the deploy dutifully disarmed the correct tier.
#
# The DLL RECORDS its decision, so ask it instead. ScaleTier logs one line per
# package as it arms the tier it resolved:
#     ScaleTier: zzz-SC4UIScale\z_SC4UIScale_CsiIcons-3x.dat -> ACTIVE.
# The newest log wins; this script preserves the previous log before every
# deploy, so there is always at least one to read.
$TIER_FROM_LOG = $null
$logs = @(Get-ChildItem $plug -Filter "SC4UIScale*.log" -File -ErrorAction SilentlyContinue |
          Sort-Object LastWriteTime -Descending)
foreach ($lg in $logs) {
    $m = [regex]::Matches((Get-Content $lg.FullName -Raw -ErrorAction SilentlyContinue),
                          '-(15x|2x|3x)\.dat -> ACTIVE')
    if ($m.Count) {
        $TIER_FROM_LOG = $m[$m.Count-1].Groups[1].Value
        Write-Output ("  armed tier per the DLL's own log (" + $lg.Name + "): " + $TIER_FROM_LOG)
        break
    }
}

$ARMED_BEFORE = @{}
foreach ($fam in $TIER_FAMILIES) {
    $dir = if ($fam.Sub) { Join-Path $plug $fam.Sub } else { $our }
    if (-not (Test-Path $dir)) { continue }
    $live = @()
    foreach ($tier in @("15x","2x","3x")) {
        if (Test-Path (Join-Path $dir ($fam.Base + "-" + $tier + ".dat"))) { $live += $tier }
    }
    if ($live.Count -eq 0) { continue }
    if ($live.Count -eq 1) {
        # Unambiguous on disk. Trust it even if the log disagrees - the user may
        # have armed a tier by hand since the last run.
        $ARMED_BEFORE[$fam.Base] = $live[0]
    } elseif ($TIER_FROM_LOG -and $live -contains $TIER_FROM_LOG) {
        $ARMED_BEFORE[$fam.Base] = $TIER_FROM_LOG
        Write-Output ("  " + $fam.Base + ": " + ($live -join "+") +
                      " both armed - the log says " + $TIER_FROM_LOG + "; using that")
    } else {
        # Ambiguous AND no log to break the tie. Say so rather than guessing -
        # a silent pick here is what produced the wrong answer the first time.
        $ARMED_BEFORE[$fam.Base] = $live[0]
        Write-Output ("  " + $fam.Base + ": " + ($live -join "+") +
                      " both armed and no log to arbitrate - keeping " + $live[0])
    }
}
if ($ARMED_BEFORE.Count) {
    Write-Output ("  armed tier before deploy: " +
        (($ARMED_BEFORE.GetEnumerator() | Sort-Object Name |
          ForEach-Object { $_.Value }) | Sort-Object -Unique) -join ", ")
}
# SelectiveArt's own snapshot (STABLE-FILENAME PILOT): the stable file is
# either present-and-armed or absent-and-stashed, no tier tag to read - so
# the only question worth asking beforehand is whether it was armed AT ALL,
# matching $anyArmedBefore's role for the tag-based families below.
$selectiveArtArmedBefore = Test-Path (Join-Path $our "z_SC4UIScale_SelectiveArt.dat")

# #105/#107: PRESERVE THE LOG BEFORE THE NEXT LAUNCH DESTROYS IT.
# SC4UIScale.log is RECREATED on every game launch. On 2026-08-03 that silently
# destroyed the run-14 SPINPROBE capture - the only recording of the spinning
# thread we had - because the next run overwrote it before it was copied. Every
# deploy is immediately followed by a launch, so this is the last safe moment.
# Named by the log's OWN mtime, not "now", so the file keeps the timestamp of
# the run it came from.
$srcLog = "$our\SC4UIScale.log"   # v4.4.0: the log lives in 010-SC4UIScale
if (Test-Path $srcLog) {
    $capDir = "$proj\_tests\captures"
    if (-not (Test-Path $capDir)) { New-Item -ItemType Directory $capDir | Out-Null }
    $stamp = (Get-Item $srcLog).LastWriteTime.ToString("yyyy-MM-dd-HHmmss")
    $dest = Join-Path $capDir ("SC4UIScale-{0}.log" -f $stamp)
    if (-not (Test-Path $dest)) {
        Copy-Item $srcLog $dest -Force
        Write-Output ("preserved previous run log -> {0}" -f (Split-Path $dest -Leaf))
    }
}
Copy-Item "$proj\build\Release\SC4UIScale.dll" "$plug\SC4UIScale.dll" -Force
# SelectiveArt (v4.0.3, STABLE-FILENAME PILOT): all three tier sources ship
# PERMANENTLY suffixed - none of them is "the active one" by filename any
# more. The DLL's SyncDatStable copies the right tier's bytes onto the one
# stable name below at boot, so sc4pac (or a manual deploy re-run) always
# finds z_SC4UIScale_SelectiveArt.dat under the SAME name regardless of tier.
Copy-Item "$proj\tools\selective-safe\z_SC4UIScale_SelectiveArt.dat" "$our\z_SC4UIScale_SelectiveArt-2x.dat.x1-disabled" -Force
Copy-Item "$proj\tools\packages\15x\z_SC4UIScale_SelectiveArt-15x.dat" "$our\z_SC4UIScale_SelectiveArt-15x.dat.x1-disabled" -Force
Copy-Item "$proj\tools\packages\3x\z_SC4UIScale_SelectiveArt-3x.dat" "$our\z_SC4UIScale_SelectiveArt-3x.dat.x1-disabled" -Force
# The STABLE file itself: ships as the 2x content by default (today's
# out-of-the-box tier), and SyncDatStable rewrites it to match whatever the
# player's own AutoScale/selector choice resolves to on next boot.
Copy-Item "$proj\tools\selective-safe\z_SC4UIScale_SelectiveArt.dat" "$our\z_SC4UIScale_SelectiveArt.dat" -Force
Copy-Item "$proj\tools\dialog-static\z_SC4UIScale_DialogStatic.dat" "$our\z_SC4UIScale_DialogStatic-2x.dat" -Force
Copy-Item "$proj\tools\packages\15x\z_SC4UIScale_DialogStatic-15x.dat" "$our\z_SC4UIScale_DialogStatic-15x.dat.x1-disabled" -Force
Copy-Item "$proj\tools\packages\3x\z_SC4UIScale_DialogStatic-3x.dat" "$our\z_SC4UIScale_DialogStatic-3x.dat.x1-disabled" -Force

# ITEM ICONS - ADDED 2026-08-03 (#116). These were MISSING from this script
# for its whole life, and ScaleTier actively tier-manages them
# (ScaleTier.cpp: the SyncDat "z_SC4UIScale_ItemIcons" site), so the deployed copies
# had frozen at whatever build epoch last hand-placed them. CAUGHT IN THE ACT
# tonight: a PNG re-deflate pass rebuilt every package, this script reported
# "SelectiveArt + DialogStatic tiers", and the live ItemIcons silently stayed
# on the pre-optimization bytes.
# This is EXACTLY the #58 failure class recorded further down this file
# ("this package was NEVER in this list, so the deployed copy froze at the
# 2026-07-29 build epoch"). A deploy script that is not a complete manifest is
# a slow-acting bug generator: everything looks green and the artifact is old.
# SOURCE IS THE **UNTAGGED** FILE. tools\itemicons\ holds BOTH
# z_SC4UIScale_ItemIcons.dat and z_SC4UIScale_ItemIcons-2x.dat, and they are
# not the same build. Test-DatIntegrity treats the UNTAGGED one as canonical
# (it is what SelectiveArt/DialogStatic do too - the 2x tier's source carries
# no tag). Deploying from the tagged copy makes DatIntegrity FAIL, which is
# how this was caught rather than shipped.
Copy-Item "$proj\tools\itemicons\z_SC4UIScale_ItemIcons.dat" "$our\z_SC4UIScale_ItemIcons-2x.dat" -Force
Copy-Item "$proj\tools\packages\15x\z_SC4UIScale_ItemIcons-15x.dat" "$our\z_SC4UIScale_ItemIcons-15x.dat.x1-disabled" -Force
Copy-Item "$proj\tools\packages\3x\z_SC4UIScale_ItemIcons-3x.dat" "$our\z_SC4UIScale_ItemIcons-3x.dat.x1-disabled" -Force
# SaveWarningUI (v2.38.0, task #79c): 2x copies of the two in-city quit/exit
# confirm scripts built from the save-warning MOD's versions. MUST land in the
# zzz-SC4UIScale SUBFOLDER - root Plugins files load BEFORE subfolders, so a
# root copy could never beat the mod in 150-mods\ (the load-order law, and the
# whole reason those dialogs opened 1x). ScaleTier gates it on that mod still
# being installed; deploy it live and let the DLL disable it if it should not
# be active.
$zzz = Join-Path $plug "zzz-SC4UIScale"
# ItemIconsSub - ADDED 2026-08-03 (#116), same omission as ItemIcons above.
# ScaleTier.cpp's SyncDat site tier-manages this one too.
Copy-Item "$proj\tools\itemicons\_work\z_SC4UIScale_ItemIconsSub-2x.dat" "$zzz\z_SC4UIScale_ItemIconsSub-2x.dat" -Force
Copy-Item "$proj\tools\packages\15x\z_SC4UIScale_ItemIconsSub-15x.dat" "$zzz\z_SC4UIScale_ItemIconsSub-15x.dat.x1-disabled" -Force
Copy-Item "$proj\tools\packages\3x\z_SC4UIScale_ItemIconsSub-3x.dat" "$zzz\z_SC4UIScale_ItemIconsSub-3x.dat.x1-disabled" -Force

# CsiIcons - ADDED 2026-08-18 (#188). The U-Drive-It offer balloon icons
# (City Situation Indicators). THIS BLOCK EXISTS BECAUSE OF THE STANDING LAW:
# a package is not done until it is in the MANIFEST. Three packages have
# already rotted by being hand-placed into Plugins and never wired here -
# each looked fine locally and was simply absent on a clean install.
# Tier suffixes follow the ItemIconsSub pattern: the ACTIVE tier keeps its
# plain .dat name, the other two ship .x1-disabled and ScaleTier renames.
# THESE THREE LINES SHIPPED INVERTED (2026-08-18 -> 2026-08-19). 15x was
# copied to the PLAIN name and 2x to .x1-disabled, so a 2x install deployed
# 1.5x offer-balloon icons. The comment above was right the whole time; the
# code under it was written during a 1.5x test session and never swapped back.
# It passed every gate because every gate asked "is the package present?" and
# all three were - and because ScaleTier's SyncDat re-arms the correct tier at
# launch with MOVEFILE_REPLACE_EXISTING, erasing the evidence before anyone
# reads a log. Written as the same $ACTIVE_TIER-driven loop the other families
# use, so the tier can no longer be typed in by hand per package.
foreach ($t in @(@("2x",""), @("15x",".x1-disabled"), @("3x",".x1-disabled"))) {
  Copy-Item ("$proj\tools\packages\" + $t[0] + "\z_SC4UIScale_CsiIcons-" + $t[0] + ".dat") `
            (Join-Path $zzz ("z_SC4UIScale_CsiIcons-" + $t[0] + ".dat" + $t[1])) -Force
}
# A CsiIcons-specific "remove any armed 15x/3x" sweep used to sit here. It
# was written when 2x was assumed to be the active tier always, and it DELETED
# THE CORRECT FILE on a 3x install - the armed-tier restore at the end of this
# script would re-arm 3x and this block would remove it again, every run. The
# armed tier is now snapshot-and-restored generically for every family (see the
# ARMED-TIER SNAPSHOT block at the top), so a per-package sweep can only
# disagree with it. Deleted rather than repaired: two things deciding the same
# question is the bug, not the tie-break.

# UncoveredIcons - ADDED 2026-08-15 (#149). ItemIcons a third-party LOT ships
# that no package of ours covered; at any tier > 1 the strip's cell is scaled
# but that art is not, so the four-state read over-runs the bitmap and the icon
# draws wrong and vanishes on hover. Rebuild with:
#     python tools\itemicons\build_uncovered_icons.py
# which rediscovers the set from the player's OWN Plugins tree, so this is not
# a list that can go stale - re-run it after installing new lots.
# OPTIONAL BY CONSTRUCTION - a hard Copy-Item here was a RELEASE BUG.
# This package holds however many uncovered third-party icons THIS install
# has, so on a clean install - which is exactly what a first-time player and
# the #148 vanilla check both are - it does not exist at all, and the deploy
# would have died on a missing file. ABSENT IS A VALID STATE, NOT AN ERROR.
foreach ($t in @(@("2x",""), @("15x",".x1-disabled"), @("3x",".x1-disabled"))) {
  $srcU = Join-Path $proj ("tools\itemicons\out\z_SC4UIScale_UncoveredIcons-" + $t[0] + ".dat")
  if (Test-Path $srcU) { Copy-Item $srcU (Join-Path $zzz ("z_SC4UIScale_UncoveredIcons-" + $t[0] + ".dat" + $t[1])) -Force }
}

# SelectorUI-1x - ADDED 2026-08-19. The in-game scale selector at the STOCK
# tier, and the ONLY package whose gate is the ABSENCE of a tier. It carries a
# single script: Graphic Options at stock geometry with our four selector nodes
# injected. Rebuild with:
#     python tools\dialog-static\build_selector_1x.py
#
# WHY IT EXISTS: at 1x the DLL stashes every art package, which is right - and
# it would also stash the one control that lets a player LEAVE 1x. Without this
# package the stock tier is a one-way door out of the mod.
#
# IT MUST NOT BE LIVE AT A SCALED TIER. It lives in zzz-SC4UIScale\, and
# SUBFOLDERS load AFTER root files, so a live copy would beat the root
# DialogStatic-<tier> and hand a 2x player a 1x Graphic Options. The DLL's
# SyncDat corrects the state at PreAppInit - before any dat is read - but the
# file is placed in the CORRECT state here anyway: deploying a package armed
# and trusting a later repair is precisely the shape #196 shipped.
$selSrc = Join-Path $proj ("tools\packages\1x\z_SC4UIScale_SelectorUI-1x.dat")
if (Test-Path $selSrc) {
  # NOT $TIER_FROM_LOG. That variable is null whenever no log line matched,
  # which is the common case - gating on it armed this package on a live 1.5x
  # install (2026-08-19), and because it sits in zzz-SC4UIScale\ it would have
  # beaten the root DialogStatic-15x and served a 1x Graphic Options at 1.5x.
  # $ARMED_BEFORE is the variable that OWNS this question: it is the snapshot
  # block's answer, log first and files as a documented fallback. Ask the thing
  # that owns the question, not the nearest thing that looks like it.
  $anyTierArmed = ($ARMED_BEFORE.Count -gt 0) -or $TIER_FROM_LOG
  $selSuffix = if ($anyTierArmed) { ".x1-disabled" } else { "" }
  Copy-Item $selSrc (Join-Path $zzz ("z_SC4UIScale_SelectorUI-1x.dat" + $selSuffix)) -Force
  # Remove the opposite form so exactly one exists (PRESENCE IS NOT ARMING).
  $selOther = Join-Path $zzz ("z_SC4UIScale_SelectorUI-1x.dat" + $(if ($selSuffix) { "" } else { ".x1-disabled" }))
  if (Test-Path $selOther) { Remove-Item $selOther -Force }
  Write-Output ("  SelectorUI-1x -> " + $(if ($selSuffix) { "stashed (scaled tier live)" } else { "ARMED (stock tier - 1x keeps the selector)" }))
} else {
  Write-Output "  SelectorUI-1x source MISSING - run tools\dialog-static\build_selector_1x.py"
}

# THE COMMENT THAT USED TO SIT HERE WAS FALSE ON BOTH COUNTS (2026-08-05).
# It said WebText and MenuFix were "hand-placed, no build source in the repo"
# and could never be rebuilt. Both statements are wrong:
#   tools\webtext\z_SC4UIScale_WebText.dat        + build_webtext.py that makes it
#   tools\itemicons\_work\z_SC4UIScale_MenuFix.dat
# and the repo copy of WebText is byte-identical (sha256 5cd27889...) to the
# live one, so it has been reproducible the whole time.
#
# WORSE, AND THE REAL DEFECT: Test-DatIntegrity.ps1 asserts BOTH deployed
# copies match those repo files (lines 331-332) while this script copied
# NEITHER. Those assertions passed only because the live files were hand-placed
# once and never regenerated - the instant the builder produced different bytes,
# DatIntegrity would fail with no explanation and no deploy to blame. That is
# the #58 / #116 failure class exactly, sitting in the very file whose comments
# describe it.
#
# WebText is now deployed here (user decision 2026-08-05: ship it - it makes the
# visible text match the WebRedirect the DLL already performs at every tier).
Copy-Item "$proj\tools\webtext\z_SC4UIScale_WebText.dat" "$our\z_SC4UIScale_WebText.dat" -Force
# MenuFix is STILL NOT DEPLOYED, and now for the honest reason rather than a
# wrong one: it rewrites CAM's gameplay submenu data rather than scaling any
# UI, so shipping it is a decision about a THIRD-PARTY mod's content, not about
# this mod. It remains slated to be dropped. If that decision is ever reversed,
# add the Copy-Item here - do not hand-place it, or the assertion above goes
# back to passing by luck.
# CAM GRAPH LABELS (#147, 2026-08-06). ONE 20-byte LTEXT, TIER-INDEPENDENT.
# CAM's Power and Water chart exemplars declare four series and bind label
# 0xFF5D2E9F for the fourth - an id that exists in NO installed archive (0 hits
# in 118,896 records across 107 DBPF files, with 0x0A5D2E9D / 0xFF5D2E98 /
# 0xFF5D2E9E found as positive controls). The row therefore renders with a
# working checkbox and a cyan swatch and NO CAPTION. We supply the missing
# resource; we never touch CAM's file. Built by
# tools\itemicons\build_cam_graph_labels.py. Deliberately WITHOUT the trailing
# CRLF that CAM's 0xFF5D2E98 carries - "Imported", the row directly above ours
# in the same legend, has no CRLF either, and copying it would make the row two
# lines tall. Reported upstream in tools\research\UPSTREAM-CAM-REPORT.md #4;
# DELETE THIS LINE and the dat if CAM ever fixes the id.
# Inert without CAM: nothing else binds that instance.
Copy-Item "$proj\tools\packages\shared\z_SC4UIScale_CamGraphLabels.dat" "$zzz\z_SC4UIScale_CamGraphLabels.dat" -Force
Copy-Item "$proj\tools\dialog-static\z_SC4UIScale_SaveWarningUI.dat" "$zzz\z_SC4UIScale_SaveWarningUI-2x.dat" -Force
Copy-Item "$proj\tools\packages\15x\z_SC4UIScale_SaveWarningUI-15x.dat" "$zzz\z_SC4UIScale_SaveWarningUI-15x.dat.x1-disabled" -Force
Copy-Item "$proj\tools\packages\3x\z_SC4UIScale_SaveWarningUI-3x.dat" "$zzz\z_SC4UIScale_SaveWarningUI-3x.dat.x1-disabled" -Force
# CamUI (v2.38.3): the SIX dialog-static targets CAM replaces, built from CAM's
# own scripts. Same zzz- subfolder rule and same dependency gate.
# + v2.97.0 (#154): THREE more scripts that are not overrides at all - CAM's
# own city info screen {96a006b0,9b868f68} (the Village Hall / Town Hall
# query) and its civic + school query panels 12121201 / 12121205 - plus the
# nine CAM bitmaps the info screen draws. 22 entries per tier, not 10.
Copy-Item "$proj\tools\dialog-static\z_SC4UIScale_CamUI.dat" "$zzz\z_SC4UIScale_CamUI-2x.dat" -Force
Copy-Item "$proj\tools\packages\15x\z_SC4UIScale_CamUI-15x.dat" "$zzz\z_SC4UIScale_CamUI-15x.dat.x1-disabled" -Force
Copy-Item "$proj\tools\packages\3x\z_SC4UIScale_CamUI-3x.dat" "$zzz\z_SC4UIScale_CamUI-3x.dat.x1-disabled" -Force
# ThirdPartyUI (task #58 root cause, found 2026-08-02): this package was
# NEVER in this list, so the deployed copy froze at the 2026-07-29 build
# epoch. When the art classification later changed (SHARED->EXCLUSIVE), the
# frozen script kept referencing clone TGIs (470261e8/47026240) that stopped
# shipping - the grey radio rows on Building Style Control. Byte sizes of
# stale and fresh dats are IDENTICAL (the rewrite swaps equal-length hex),
# so no size check can catch this class - only content/hash comparison.
Copy-Item "$proj\tools\selective-safe\z_SC4UIScale_ThirdPartyUI.dat" "$zzz\z_SC4UIScale_ThirdPartyUI-2x.dat" -Force
Copy-Item "$proj\tools\packages\15x\z_SC4UIScale_ThirdPartyUI-15x.dat" "$zzz\z_SC4UIScale_ThirdPartyUI-15x.dat.x1-disabled" -Force
Copy-Item "$proj\tools\packages\3x\z_SC4UIScale_ThirdPartyUI-3x.dat" "$zzz\z_SC4UIScale_ThirdPartyUI-3x.dat.x1-disabled" -Force
# WarriorUI (task #94, 2026-08-02): 2x copies of warrior's god-terraforming-in-
# mayor-mode scripts + ITS art. Same zzz- subfolder rule (must beat 150-mods\)
# and same dependency gate. Added here IN THE SAME CHANGE as the package
# (law 40: a package missing from this script rots into a live bug).
Copy-Item "$proj\tools\selective-safe\z_SC4UIScale_WarriorUI.dat" "$zzz\z_SC4UIScale_WarriorUI-2x.dat" -Force
Copy-Item "$proj\tools\packages\15x\z_SC4UIScale_WarriorUI-15x.dat" "$zzz\z_SC4UIScale_WarriorUI-15x.dat.x1-disabled" -Force
Copy-Item "$proj\tools\packages\3x\z_SC4UIScale_WarriorUI-3x.dat" "$zzz\z_SC4UIScale_WarriorUI-3x.dat.x1-disabled" -Force
# RaiseUI (2026-08-30): warrior's "Raise the UI Mod" ships only SCRIPTS, no
# art - so the game runs its 1x `imagerect` source rects against OUR 2x art
# sheets and reads the top-left quarter of every one (the magenta and black
# the player photographed). Our copies carry the MOD'S scripts with imagerect
# scaled and `area=` untouched, so the raise survives. Same zzz- rule (must
# beat 150-mods\) and same dependency gate.
Copy-Item "$proj\tools\selective-safe\z_SC4UIScale_RaiseUI.dat" "$zzz\z_SC4UIScale_RaiseUI-2x.dat" -Force
Copy-Item "$proj\tools\packages\15x\z_SC4UIScale_RaiseUI-15x.dat" "$zzz\z_SC4UIScale_RaiseUI-15x.dat.x1-disabled" -Force
Copy-Item "$proj\tools\packages\3x\z_SC4UIScale_RaiseUI-3x.dat" "$zzz\z_SC4UIScale_RaiseUI-3x.dat.x1-disabled" -Force
# ZCarbonRaiseUI (2026-08-30): Scoty's OPTIONAL composed Carbon+Raise scripts,
# for the one combination neither RaiseUI nor ZCarbonArt can serve. Sorts after
# ZCarbonArt so it wins both contested scripts when its gate is open, and is
# gated on the composed file itself - which only exists when both mods are
# installed, so its presence is the conjunction.
Copy-Item "$proj\tools\selective-safe\z_SC4UIScale_ZCarbonRaiseUI.dat" "$zzz\z_SC4UIScale_ZCarbonRaiseUI-2x.dat" -Force
Copy-Item "$proj\tools\packages\15x\z_SC4UIScale_ZCarbonRaiseUI-15x.dat" "$zzz\z_SC4UIScale_ZCarbonRaiseUI-15x.dat.x1-disabled" -Force
Copy-Item "$proj\tools\packages\3x\z_SC4UIScale_ZCarbonRaiseUI-3x.dat" "$zzz\z_SC4UIScale_ZCarbonRaiseUI-3x.dat.x1-disabled" -Force
# ZCarbonPauseOff (2026-08-30): a fully transparent sheet over the carbon gold
# pause border, sorting after ZCarbonArt and armed ONLY when a pause remover is
# installed. Built by tools\itemicons\build_carbonpauseoff.py, which verifies
# the transparency before packing.
Copy-Item "$proj\tools\itemicons\out\z_SC4UIScale_ZCarbonPauseOff-2x.dat" "$zzz\z_SC4UIScale_ZCarbonPauseOff-2x.dat" -Force
Copy-Item "$proj\tools\itemicons\out\z_SC4UIScale_ZCarbonPauseOff-15x.dat" "$zzz\z_SC4UIScale_ZCarbonPauseOff-15x.dat.x1-disabled" -Force
Copy-Item "$proj\tools\itemicons\out\z_SC4UIScale_ZCarbonPauseOff-3x.dat" "$zzz\z_SC4UIScale_ZCarbonPauseOff-3x.dat.x1-disabled" -Force
# RegionCensusUI (2026-08-30): null-45's mod-ONLY region census dialog, which
# never scales itself while our 2x fonts scale its text - 5 of 40 labels
# overflow at 2x. Built by dialog-static (static/never-swept window, so its
# area= is ours to scale), unlike RaiseUI just above which is imagerect-only.
Copy-Item "$proj\tools\dialog-static\z_SC4UIScale_RegionCensusUI.dat" "$zzz\z_SC4UIScale_RegionCensusUI-2x.dat" -Force
Copy-Item "$proj\tools\packages\15x\z_SC4UIScale_RegionCensusUI-15x.dat" "$zzz\z_SC4UIScale_RegionCensusUI-15x.dat.x1-disabled" -Force
Copy-Item "$proj\tools\packages\3x\z_SC4UIScale_RegionCensusUI-3x.dat" "$zzz\z_SC4UIScale_RegionCensusUI-3x.dat.x1-disabled" -Force
# NamIcons (task #139, 2026-08-05): 1.5x/2x/3x copies of the Network Addon
# Mod's OWN 392 menu ItemIcons, gated in ScaleTier on the presence of
# NetworkAddonMod_Controller.dat. Same zzz- rule as its siblings - NAM lives
# in 770-network-addon-mod\ and only zzz- sorts after it.
# THESE THREE FILES WERE PLACED BY HAND during the session that built them,
# and were caught missing here by Build-Dist.ps1 the same day: the bundle came
# out without them. That is task #58 and task #116's failure verbatim - a
# package outside this manifest freezes at the build epoch it was hand-copied
# at and rots into a live bug, silently, because nothing compares it to source.
# The generator is tools\itemicons\rebuild_namicons.py; its output lands in
# tools\itemicons\out\ (all three tiers, unlike the older packages which split
# 2x from tools\packages\{15x,3x}\).
Copy-Item "$proj\tools\itemicons\out\z_SC4UIScale_NamIcons-2x.dat" "$zzz\z_SC4UIScale_NamIcons-2x.dat" -Force
Copy-Item "$proj\tools\itemicons\out\z_SC4UIScale_NamIcons-15x.dat" "$zzz\z_SC4UIScale_NamIcons-15x.dat.x1-disabled" -Force
Copy-Item "$proj\tools\itemicons\out\z_SC4UIScale_NamIcons-3x.dat" "$zzz\z_SC4UIScale_NamIcons-3x.dat.x1-disabled" -Force
# WebButtonUI (2026-08-21): 1.5x/2x/3x copies of the cyclone-boom Web Button
# Improvement Mod's web-button bitmap {856DDBAC,46A006B0,14416302}, gated in
# ScaleTier on the mod's presence. Same zzz- rule as its siblings. Generator is
# tools\itemicons\rebuild_webbutton.py; output lands in tools\itemicons\out\.
Copy-Item "$proj\tools\itemicons\out\z_SC4UIScale_WebButtonUI-2x.dat" "$zzz\z_SC4UIScale_WebButtonUI-2x.dat" -Force
Copy-Item "$proj\tools\itemicons\out\z_SC4UIScale_WebButtonUI-15x.dat" "$zzz\z_SC4UIScale_WebButtonUI-15x.dat.x1-disabled" -Force
Copy-Item "$proj\tools\itemicons\out\z_SC4UIScale_WebButtonUI-3x.dat" "$zzz\z_SC4UIScale_WebButtonUI-3x.dat.x1-disabled" -Force
# ---- ZCarbon* (v4.3.0, 2026-08-25): Scoty Carbon Skin adaptations ----------
# Carbon-sourced scaled twins of every TGI the skin and our packages both
# cover; gated in ScaleTier on the skin's dats at exact sizes. Z-late base
# names are LOAD-BEARING (must sort after every sibling in zzz- to win shared
# TGIs; REGRESSION.md 2026-08-25 "zzz-INTERNAL SORT TRAP").
# ⚠ DELIBERATELY parser-invisible to Build-Dist (named-parameter Copy-Item):
# these dats are built FROM the skin author's pixels and MUST NEVER enter the
# public dist bundle ("ship the GENERATOR, never the art" — and never another
# modder's art). Build-Dist carries a hard assert that no ZCarbon file lands
# in a bundle; if you rewrite these lines into the bare positional form the
# parser WILL bundle them and that assert is the only net.
# PRESENCE-GATED like Test-Builders' --carbon (review finding 3): on a
# machine without the carbon builds (fresh clone, no skin) these sources do
# not exist, and under $ErrorActionPreference=Stop an unguarded Copy-Item
# would ABORT the deploy mid-way - skipping the FontStyle sources, the
# gate-honour block, the stale-twin cleanup and the armed-tier restore.
$zcarbonBuilt = Test-Path "$proj\tools\selective-safe\z_SC4UIScale_ZCarbonArt.dat"
if ($zcarbonBuilt) {
Copy-Item -Path "$proj\tools\dialog-static\z_SC4UIScale_ZCarbonUI.dat" -Destination "$zzz\z_SC4UIScale_ZCarbonUI-2x.dat" -Force
Copy-Item -Path "$proj\tools\packages\15x\z_SC4UIScale_ZCarbonUI-15x.dat" -Destination "$zzz\z_SC4UIScale_ZCarbonUI-15x.dat.x1-disabled" -Force
Copy-Item -Path "$proj\tools\packages\3x\z_SC4UIScale_ZCarbonUI-3x.dat" -Destination "$zzz\z_SC4UIScale_ZCarbonUI-3x.dat.x1-disabled" -Force
Copy-Item -Path "$proj\tools\dialog-static\z_SC4UIScale_ZCarbonCamUI.dat" -Destination "$zzz\z_SC4UIScale_ZCarbonCamUI-2x.dat" -Force
Copy-Item -Path "$proj\tools\packages\15x\z_SC4UIScale_ZCarbonCamUI-15x.dat" -Destination "$zzz\z_SC4UIScale_ZCarbonCamUI-15x.dat.x1-disabled" -Force
Copy-Item -Path "$proj\tools\packages\3x\z_SC4UIScale_ZCarbonCamUI-3x.dat" -Destination "$zzz\z_SC4UIScale_ZCarbonCamUI-3x.dat.x1-disabled" -Force
Copy-Item -Path "$proj\tools\dialog-static\z_SC4UIScale_ZCarbonSaveWarning.dat" -Destination "$zzz\z_SC4UIScale_ZCarbonSaveWarning-2x.dat" -Force
Copy-Item -Path "$proj\tools\packages\15x\z_SC4UIScale_ZCarbonSaveWarning-15x.dat" -Destination "$zzz\z_SC4UIScale_ZCarbonSaveWarning-15x.dat.x1-disabled" -Force
Copy-Item -Path "$proj\tools\packages\3x\z_SC4UIScale_ZCarbonSaveWarning-3x.dat" -Destination "$zzz\z_SC4UIScale_ZCarbonSaveWarning-3x.dat.x1-disabled" -Force
Copy-Item -Path "$proj\tools\selective-safe\z_SC4UIScale_ZCarbonArt.dat" -Destination "$zzz\z_SC4UIScale_ZCarbonArt-2x.dat" -Force
Copy-Item -Path "$proj\tools\packages\15x\z_SC4UIScale_ZCarbonArt-15x.dat" -Destination "$zzz\z_SC4UIScale_ZCarbonArt-15x.dat.x1-disabled" -Force
Copy-Item -Path "$proj\tools\packages\3x\z_SC4UIScale_ZCarbonArt-3x.dat" -Destination "$zzz\z_SC4UIScale_ZCarbonArt-3x.dat.x1-disabled" -Force
Copy-Item -Path "$proj\tools\selective-safe\z_SC4UIScale_ZCarbonStyles.dat" -Destination "$zzz\z_SC4UIScale_ZCarbonStyles-2x.dat" -Force
Copy-Item -Path "$proj\tools\packages\15x\z_SC4UIScale_ZCarbonStyles-15x.dat" -Destination "$zzz\z_SC4UIScale_ZCarbonStyles-15x.dat.x1-disabled" -Force
Copy-Item -Path "$proj\tools\packages\3x\z_SC4UIScale_ZCarbonStyles-3x.dat" -Destination "$zzz\z_SC4UIScale_ZCarbonStyles-3x.dat.x1-disabled" -Force
Copy-Item -Path "$proj\tools\selective-safe\z_SC4UIScale_ZCarbonNam.dat" -Destination "$zzz\z_SC4UIScale_ZCarbonNam-2x.dat" -Force
Copy-Item -Path "$proj\tools\packages\15x\z_SC4UIScale_ZCarbonNam-15x.dat" -Destination "$zzz\z_SC4UIScale_ZCarbonNam-15x.dat.x1-disabled" -Force
Copy-Item -Path "$proj\tools\packages\3x\z_SC4UIScale_ZCarbonNam-3x.dat" -Destination "$zzz\z_SC4UIScale_ZCarbonNam-3x.dat.x1-disabled" -Force
Copy-Item -Path "$proj\tools\selective-safe\z_SC4UIScale_ZCarbonGodMod.dat" -Destination "$zzz\z_SC4UIScale_ZCarbonGodMod-2x.dat" -Force
Copy-Item -Path "$proj\tools\packages\15x\z_SC4UIScale_ZCarbonGodMod-15x.dat" -Destination "$zzz\z_SC4UIScale_ZCarbonGodMod-15x.dat.x1-disabled" -Force
Copy-Item -Path "$proj\tools\packages\3x\z_SC4UIScale_ZCarbonGodMod-3x.dat" -Destination "$zzz\z_SC4UIScale_ZCarbonGodMod-3x.dat.x1-disabled" -Force
Copy-Item -Path "$proj\tools\research\carbon\z_SC4UIScale_ZCarbonIcons.dat" -Destination "$zzz\z_SC4UIScale_ZCarbonIcons-2x.dat" -Force
Copy-Item -Path "$proj\tools\packages\15x\z_SC4UIScale_ZCarbonIcons-15x.dat" -Destination "$zzz\z_SC4UIScale_ZCarbonIcons-15x.dat.x1-disabled" -Force
Copy-Item -Path "$proj\tools\packages\3x\z_SC4UIScale_ZCarbonIcons-3x.dat" -Destination "$zzz\z_SC4UIScale_ZCarbonIcons-3x.dat.x1-disabled" -Force
} else {
    Write-Output "  ZCarbon packages NOT built on this machine (no carbon inputs) - skipped; gates leave any deployed copies disarmed"
}
# FONT TIER SOURCES (#57 phase 4, 2026-08-02). These were NEVER in this
# script - the three FontStyle-*.ini files in Plugins were placed BY HAND, and
# they rotted exactly as task #58's dats did. MEASURED: the deployed
# FontStyle-15x.ini and FontStyle-3x.ini were the raw .gen.ini side-outputs,
# carrying only 62 styles and NO MessageHeaderHtml/MessageBodyHtml, so
# CodePatches' popup retarget (0x52CCEE, src/CodePatches.cpp:56-62) pointed at
# styles that did not exist at those tiers - a silent regression shipped since
# v2.25.2. The DLL's ScaleTier::SyncFont copies the active tier's file over
# FontStyle.ini at boot, so ONLY these three sources belong here; never copy
# FontStyle.ini itself.
# The 2x source is tools\fonts\FontStyle.candidate.ini - there is no
# tools\packages\2x\ directory. It is byte-identical to make_fontstyle.py's
# factor-2 output apart from its hand-written ";;" banner (asserted by
# --selfcheck).
Copy-Item "$proj\tools\fonts\FontStyle.candidate.ini" "$our\FontStyle-2x.ini" -Force
Copy-Item "$proj\tools\packages\15x\FontStyle-15x.ini" "$our\FontStyle-15x.ini" -Force
Copy-Item "$proj\tools\packages\3x\FontStyle-3x.ini" "$our\FontStyle-3x.ini" -Force
# ---- REFRESH THE *ACTIVE* TIER (2026-08-05) --------------------------------
# Every non-2x tier above is deployed to "<name>.x1-disabled". The DLL ACTIVATES
# a tier at boot by RENAMING it - dropping the .x1-disabled suffix. So once the
# game has run at 1.5x or 3x, the live file is the unsuffixed one and every
# later deploy wrote only the disabled copy beside it. The stale active file
# then survived indefinitely while deploy still reported success.
#
# MEASURED 2026-08-05 (#136): SelectiveArt-3x.dat was the 651-entry Aug-4 build
# while .x1-disabled beside it was the fresh 655-entry one; ThirdPartyUI-3x and
# WarriorUI-3x were stale the same way. Test-DatIntegrity's deployed==built
# hashes are what caught it - a size check alone would have missed the two
# same-size files.
#
# So: wherever BOTH names exist, the unsuffixed one is live and must be
# refreshed from the copy we just wrote.
#
# .x1-disabled IS AN OVERLOADED SUFFIX, AND THAT BIT THIS LOOP (2026-08-05).
# The DLL writes it for TWO unrelated reasons:
#   (a) TIER selection - "this is not the active tier"      -> only ever -15x/-3x
#   (b) DEPENDENCY gate - "the mod this package patches is not installed"
#                                                            -> ANY tier, incl. -2x
# This loop assumed (a). With WarriorUI's mod absent, the live tree held a
# gate-disabled `WarriorUI-2x.dat.x1-disabled` from an OLD build; the deploy
# then wrote a fresh `WarriorUI-2x.dat`, both names existed, and the loop
# copied the STALE disabled file over the fresh one - a refresh that moved
# BACKWARDS in time. Test-DatIntegrity's deployed==built hash caught it.
# Restricting to -15x/-3x removes the collision: case (b) on a non-active tier
# leaves no unsuffixed twin, so `Test-Path $active` is already false.
foreach ($dir in @($our, "$plug\zzz-SC4UIScale")) {
    if (-not (Test-Path $dir)) { continue }
    Get-ChildItem $dir -Filter "*.x1-disabled" -File -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -match '-(15x|3x)\.dat\.x1-disabled$' } |
        ForEach-Object {
            $active = $_.FullName -replace '\.x1-disabled$', ''
            if (Test-Path $active) {
                Copy-Item $_.FullName $active -Force
                Write-Output ("  refreshed ACTIVE tier file: " + (Split-Path $active -Leaf))
            }
        }
}
# ---- HONOUR AN EXISTING DEPENDENCY GATE (2026-08-05) ------------------------
# A `-2x.dat.x1-disabled` twin means the DLL's DEPENDENCY gate turned that
# package off: the mod it patches is not installed. The copies above always
# write the ACTIVE name, so after them BOTH names exist and the package is
# live again for a mod that is not there - which is precisely the failure
# Test-ThirdPartyGates.ps1 exists to catch ("our frozen copy of another mod's
# UI is still winning").
#
# THE DEPLOY REFRESHES CONTENT. IT MUST NOT CHANGE GATE STATE. Those are two
# different authorities: this script owns "are the bytes current", the DLL owns
# "should this be loaded at all". A previous approach deleted the
# disabled twin instead, which silently overrode the DLL's decision and turned
# the third-party gate red - self-healing at the next launch, but red in the
# meantime, and a standing red makes every later red look pre-excused.
#
# So: push the fresh bytes into the DISABLED name and remove the active one.
# Content current, gate decision untouched. On a machine where the mod IS
# installed there is no twin and none of this runs.
# MEMBERSHIP, NOT PATTERN. Only these packages have a DEPENDENCY gate in
# ScaleTier.cpp - each is conditioned on a third-party mod being installed.
# Every other package is TIER-gated only, and for those a -2x.x1-disabled twin
# means "not the active tier" or "stale from an earlier deploy", never "turn it
# off". Matching on the filename alone disarmed CsiIcons completely (2026-08-19)
# because ScaleTier.cpp's kThirdPartyDeps table has no row for it at all.
$DEPENDENCY_GATED = @(
    "z_SC4UIScale_CamUI",         # CAM
    "z_SC4UIScale_WarriorUI",     # Warrior's UI mod
    "z_SC4UIScale_RaiseUI",       # Warrior's Raise the UI Mod
    "z_SC4UIScale_RegionCensusUI",# null-45's Region View Census UI
    "z_SC4UIScale_ZCarbonRaiseUI",# Scoty's composed Carbon+Raise scripts
    "z_SC4UIScale_ZCarbonPauseOff",# carbon pause border, off when a remover is in
    "z_SC4UIScale_ThirdPartyUI",  # assorted third-party UI overrides
    "z_SC4UIScale_SaveWarningUI", # save-warning mod
    "z_SC4UIScale_NamIcons",      # NAM
    "z_SC4UIScale_WebButtonUI",   # cyclone-boom Web Button Improvement Mod
    "z_SC4UIScale_ZCarbonUI",          # Scoty Carbon Skin core dats
    "z_SC4UIScale_ZCarbonArt",         # Scoty Carbon Skin core dats
    "z_SC4UIScale_ZCarbonIcons",       # Scoty Carbon Skin core dats
    "z_SC4UIScale_ZCarbonSaveWarning", # Carbon's save-warning redeclaration dat
    "z_SC4UIScale_ZCarbonCamUI",       # Carbon's CAM redeclaration dat
    "z_SC4UIScale_ZCarbonStyles",      # Carbon's BuildingStyles redeclaration dat
    "z_SC4UIScale_ZCarbonNam",         # Carbon's NAM redeclaration dat
    "z_SC4UIScale_ZCarbonGodMod"       # Carbon's GodMod redeclaration dat - warrior twin
    # NOTE: WebButtonUI was added 2026-08-21 in ScaleTier.cpp and this list was
    # never updated to match - caught by Test-DatIntegrity.ps1's drift check,
    # 2026-08-23. Keep every entry ABOVE this comment: the drift check's lazy
    # regex captures the array only up to the FIRST close-paren, and a comment
    # containing one hides everything after it. Measured 2026-08-25 - seven
    # entries placed below this comment were invisible to the check.
)
foreach ($dir in @($our, "$plug\zzz-SC4UIScale")) {
    if (-not (Test-Path $dir)) { continue }
    Get-ChildItem $dir -Filter "*-2x.dat.x1-disabled" -File -ErrorAction SilentlyContinue |
        ForEach-Object {
            $base = $_.Name -replace '-2x\.dat\.x1-disabled$', ''
            if ($DEPENDENCY_GATED -notcontains $base) { return }
            $active = $_.FullName -replace '\.x1-disabled$', ''
            if (Test-Path $active) {
                Copy-Item $active $_.FullName -Force
                Remove-Item $active -Force
                Write-Output ("  package is dependency-GATED OFF; refreshed in place: " + $_.Name)
            }
        }
}
# Tier-gated-only packages: a stale -2x.x1-disabled twin beside an armed -2x.dat
# is leftover state, not a decision. The armed file is correct; drop the twin so
# the next run cannot mistake it for a gate again.
foreach ($dir in @($our, "$plug\zzz-SC4UIScale")) {
    if (-not (Test-Path $dir)) { continue }
    Get-ChildItem $dir -Filter "*-2x.dat.x1-disabled" -File -ErrorAction SilentlyContinue |
        ForEach-Object {
            $base = $_.Name -replace '-2x\.dat\.x1-disabled$', ''
            if ($DEPENDENCY_GATED -contains $base) { return }
            $active = $_.FullName -replace '\.x1-disabled$', ''
            if (Test-Path $active) {
                Remove-Item $_.FullName -Force
                Write-Output ("  dropped stale disabled twin (tier-gated only): " + $_.Name)
            }
        }
}

# ---- RESTORE THE ARMED TIER (2026-08-19) -----------------------------------
# The family blocks above always write their 2x package to the plain name. Put
# back whatever WAS armed, so a 1.5x or 3x install is not left with two live
# copies of the same TGIs racing on load order. Bytes refreshed, decision
# untouched - the same split of authority the dependency-gate block uses.
# A family with nothing recorded was not armed before (clean install): its 2x
# stays armed, which is the historical default.
# "NOTHING ARMED" IS A STATE, NOT A GAP. Set-Tier.ps1 -Tier 1 disarms every
# tier package on purpose - that IS the 1x baseline. This restore used to treat
# an empty snapshot as "no information" and leave whatever the family blocks had
# just armed (2x), so running a deploy during a 1x reference session silently
# put 2x ART under 1x GEOMETRY. Measured 2026-08-19: after a deploy, Set-Tier
# -Status showed six families at 2x while the ini still read ScaleFactor=1.
# A half-state like that is worse than either tier, and it is invisible unless
# someone happens to run -Status.
$anyArmedBefore = $ARMED_BEFORE.Count -gt 0
if (-not $anyArmedBefore) {
    Write-Output "  NOTHING was armed before this deploy - honouring the 1x baseline (Set-Tier -Tier 1)."
}
foreach ($fam in $TIER_FAMILIES) {
    $want = $ARMED_BEFORE[$fam.Base]
    if (-not $want -and -not $anyArmedBefore) {
        # Deliberate 1x baseline: disarm everything the copies above re-armed.
        $dir = if ($fam.Sub) { Join-Path $plug $fam.Sub } else { $our }
        if (-not (Test-Path $dir)) { continue }
        foreach ($tier in @("15x","2x","3x")) {
            $live = Join-Path $dir ($fam.Base + "-" + $tier + ".dat")
            if (Test-Path $live) {
                Move-Item $live ($live + ".x1-disabled") -Force
                Write-Output ("  kept disarmed (1x baseline): " + (Split-Path $live -Leaf))
            }
        }
        continue
    }
    if (-not $want) { continue }
    $dir = if ($fam.Sub) { Join-Path $plug $fam.Sub } else { $our }
    if (-not (Test-Path $dir)) { continue }
    foreach ($tier in @("15x","2x","3x")) {
        $live  = Join-Path $dir ($fam.Base + "-" + $tier + ".dat")
        $stash = $live + ".x1-disabled"
        if ($tier -eq $want) {
            if (-not (Test-Path $live) -and (Test-Path $stash)) {
                Move-Item $stash $live -Force
                Write-Output ("  re-armed " + (Split-Path $live -Leaf) + " (was armed before deploy)")
            }
        } elseif (Test-Path $live) {
            # MOVE, not delete: the bytes were just refreshed and the disabled
            # name is where the DLL expects to find them if the tier changes.
            Move-Item $live $stash -Force
            Write-Output ("  disarmed " + (Split-Path $live -Leaf) + " (not the armed tier)")
        }
    }
}

# SelectiveArt's own restore (STABLE-FILENAME PILOT). The Copy-Item block
# above always ships the stable file ARMED (2x content, bare .dat) - correct
# for a normal deploy, wrong for a 1x reference-capture session: the DLL
# will still fix its CONTENT on the next launch either way, but leaving it
# bare between deploy and launch is exactly the "file, game and selector
# disagree" half-state $anyArmedBefore exists to prevent for every other
# family, and Test-DatIntegrity's armed-tier check inspects this window.
$selArtStable = Join-Path $our "z_SC4UIScale_SelectiveArt.dat"
$selArtStash = $selArtStable + ".x1-disabled"
if (-not $selectiveArtArmedBefore -and -not $anyArmedBefore) {
    if (Test-Path $selArtStable) {
        Move-Item $selArtStable $selArtStash -Force
        Write-Output "  kept disarmed (1x baseline): z_SC4UIScale_SelectiveArt.dat"
    }
} elseif ($selectiveArtArmedBefore -and -not (Test-Path $selArtStable) -and (Test-Path $selArtStash)) {
    Move-Item $selArtStash $selArtStable -Force
    Write-Output "  re-armed z_SC4UIScale_SelectiveArt.dat (was armed before deploy)"
}
# CONTENT must match the armed tier too (v4.2.0): the copies above always
# ship the stable file as 2x CONTENT, which on a 1.5x/3x machine leaves the
# gate's window red until the next launch re-syncs. Swap the armed tier's
# source bytes in now - same split of authority: bytes current, decision
# untouched.
$armedTierNow = ($ARMED_BEFORE.GetEnumerator() | ForEach-Object { $_.Value } |
                 Sort-Object -Unique | Select-Object -First 1)
if ($armedTierNow -and $armedTierNow -ne "2x" -and (Test-Path $selArtStable)) {
    $tierSrc = Join-Path $our ("z_SC4UIScale_SelectiveArt-{0}.dat.x1-disabled" -f $armedTierNow)
    if (Test-Path $tierSrc) {
        Copy-Item $tierSrc $selArtStable -Force
        Write-Output ("  SelectiveArt stable content-swapped to the armed tier ({0})" -f $armedTierNow)
    }
}

# ---- v4.5.0: NORMALISE TO THE PAYLOAD LAYOUT ------------------------------
# Everything above still writes the tier-tagged rename layout, unchanged - and
# that is deliberate. _packaging\Build-Dist.ps1 derives the bundle by REGEX-
# PARSING the Copy-Item lines above, and 30 of them are invisible to that regex
# (named-parameter form, expression-built paths, Join-Path), compensated by
# hardcoded blocks inside Build-Dist. Editing the copy lines here would make
# the parsed ones emit payloads while those hardcoded blocks still emitted
# tier-tagged live dats - two live providers for every TGI they own, with the
# file count identical either way so nothing would go red.
#
# So neither side edits its copies. BOTH call the same converter last, and it
# converts whatever it finds. Two callers, one conversion, nothing to drift.
# SCOPED TO OUR TWO FOLDERS, never the whole Plugins root (v4.5.2): the
# converter recursively deletes and rewrites tier-tagged files, and pointed at
# $plug it would walk every third-party folder too - on a tree that ever
# carried a sc4pac install, that rewrites checksummed package-folder content
# the manager's manifest owns. Our files live only in these two dirs.
# -Tier is resolved HERE from the root ini: the converter's own lookup only
# searches inside -Tree, and the ini moved to the Plugins root in v4.5.0 -
# without this a 1.5x/3x machine would get 2x-seeded live files for the
# window between deploy and the next boot's re-arm.
$seedTier = ''
$rootIniPath = Join-Path $plug 'SC4UIScale.ini'
if (Test-Path $rootIniPath) {
    $mSF = [regex]::Match((Get-Content $rootIniPath -Raw), '(?m)^\s*ScaleFactor\s*=\s*([\d.]+)')
    if ($mSF.Success) {
        switch ([double]$mSF.Groups[1].Value) {
            1.5 { $seedTier = '15x' } 2 { $seedTier = '2x' }
            3   { $seedTier = '3x' }  4 { $seedTier = '4x' }
        }
    }
}
if ($seedTier) { Write-Output ("  seeding live files at " + $seedTier + " (root ini ScaleFactor)") }
foreach ($convTree in @($our, (Join-Path $plug "zzz-SC4UIScale"))) {
    if ($seedTier) { & (Join-Path $PSScriptRoot "Convert-ToPayloadLayout.ps1") -Tree $convTree -Tier $seedTier }
    else           { & (Join-Path $PSScriptRoot "Convert-ToPayloadLayout.ps1") -Tree $convTree }
}

$a = (Get-Item "$proj\build\Release\SC4UIScale.dll").Length
$b = (Get-Item "$plug\SC4UIScale.dll").Length
if ($a -ne $b) { Write-Output "DEPLOY SIZE MISMATCH src=$a dst=$b"; exit 1 }
# The old line here named only SelectiveArt + DialogStatic and was how the
# ItemIcons omission stayed invisible - it read as a complete manifest.
# WebText IS deployed (the Copy-Item at the tools\webtext block above, since
# v4.5.0) - the old summary still listed it as hand-placed, the exact
# stale-manifest shape the comment above this line warns about.
Write-Output ("deployed SC4UIScale.dll + SelectiveArt/DialogStatic/ItemIcons/ItemIconsSub tiers " +
    "+ 3rd-party gated dats + WebText + 3 FontStyle tier sources at " + (Get-Date -Format "HH:mm:ss") +
    "   (NOT deployed, hand-placed: MenuFix)")
