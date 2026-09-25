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
# ---- GATE-VERDICT SNAPSHOT (2026-08-30) ------------------------------------
# Which packages are INERT right now, recorded BEFORE any copy runs, and put
# back at the very end.
#
# ⛔ THE DEFECT THIS EXISTS FOR. A deploy copies fresh built .dat files over
# the live tree and then seeds every live file at the ini's tier. Neither step
# knows about dependency gates, so a package the DLL had turned OFF came back
# holding its 2x payload - and for a third-party override that means our
# scaled copy of ANOTHER MOD's UI sitting in a game that does not have that
# mod. Set-Tier refuses to do exactly this without -ArmGated, and says why:
# "arming our frozen copy of someone else's UI into a game without that mod is
# precisely what Test-ThirdPartyGates.ps1 exists to catch." This script kept a
# $DEPENDENCY_GATED list and honoured it when copying, then handed the tree to
# a seeder that did not. One script, two stages, one aware of the gates and one
# blind.
#
# MEASURED 2026-08-30: five packages left armed at 2x with every gate verdict
# for them reading off, including two mods that are not installed.
#
# WHY A SNAPSHOT RATHER THAN A TEST. This script cannot evaluate the gates -
# they depend on which third-party mods are installed and at what byte size,
# which only ScaleTier.cpp knows. But it does not need to: an inert live file
# IS the last verdict, already computed by the DLL at the previous boot. So
# preserve it rather than recompute it. If the condition has since changed, the
# DLL re-arms at the next boot, which is the only place that decision belongs.
$INERT_BEFORE = @{}
foreach ($dir in @($our, (Join-Path $plug 'zzz-SC4UIScale'))) {
    if (-not (Test-Path $dir)) { continue }
    Get-ChildItem $dir -Filter "*.off.uipay" -File -ErrorAction SilentlyContinue |
        ForEach-Object {
            $base = $_.Name -replace '\.off\.uipay$', ''
            $live = Join-Path $dir "$base.dat"
            if ((Test-Path $live) -and
                (Get-Item $live).Length -eq $_.Length -and
                (Get-FileHash $live -Algorithm SHA256).Hash -eq
                (Get-FileHash $_.FullName -Algorithm SHA256).Hash) {
                $INERT_BEFORE[$live] = $_.FullName
            }
        }
}
if ($INERT_BEFORE.Count) {
    Write-Output ("  gate-verdict snapshot: " + $INERT_BEFORE.Count +
        " package(s) inert before this deploy; will be restored at the end")
}

# ---- ARMED-TIER SNAPSHOT (2026-08-19) --------------------------------------
# Which tier is LIVE right now, per tier-managed family, recorded BEFORE any
# copy runs. The package copy below writes 2x as the armed tier; on a
# 1.5x or 3x machine that leaves TWO armed packages and the load order decides
# which art the player gets. Restored verbatim at the end of this script.
# The DLL owns this decision (ScaleTier resolves the factor from the screen
# when AutoScale=1); this script owns only whether the bytes are current.
# SelectiveArt EXCLUDED (v4.0.3): it no longer has a tier-tagged LIVE
# filename to detect ("z_SC4UIScale_SelectiveArt-2x.dat" never exists any
# more - see its rows in _packaging\PackageFiles.psd1). It gets its own
# dedicated snapshot/restore, not this generic by-filename one.
# ⚠ MEASURED 2026-08-30: on a payload-layout tree (every v4.5.x install) the
# START-of-run snapshot below always comes up EMPTY - live files are stable
# `<base>.dat` names, never the `-<tier>.dat` names this list matches - so
# $ARMED_BEFORE only ever describes the MID-RUN rename-layout state the
# package copy creates, and the payload converter at the end of this
# script supersedes whatever the restore decided (stable-dat content comes
# from the converter's tier fallback, and the DLL re-arms from the ini at
# next boot regardless). The block is kept because removing
# live-tree-touching machinery deserves its own measured session - but do
# NOT extend this list: it is not the tier
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
# ---- COPY THE PACKAGE FILES (audit B12, 2026-09-25) ------------------------
# _packaging\PackageFiles.psd1 names every file a working install holds -
# source, folder and name - with each package's history beside its rows.
# _packaging\Build-Dist.ps1 copies from the same list, so a package cannot be
# in the install and missing from the bundle. ADD A PACKAGE THERE, NOT HERE.
# (Until B12 this script carried 73 literal Copy-Item lines and three loops,
# and Build-Dist regex-parsed them; see REGRESSION.md, audit B12.)
#
# The rows write the tier-tagged rename layout: 2x armed, 1.5x and 3x
# .x1-disabled. The blocks below put back the tier and gate state the
# snapshots above recorded, and the payload converter at the end turns the
# names into the payload layout.
$zzz = Join-Path $plug "zzz-SC4UIScale"
$PACKAGE_FILES = @((Import-PowerShellDataFile (Join-Path $proj "_packaging\PackageFiles.psd1")).Files)
if ($PACKAGE_FILES.Count -lt 40) {
    throw ("_packaging\PackageFiles.psd1 lists only " + $PACKAGE_FILES.Count +
           " file(s) - refusing to deploy a partial install")
}
# Carbon rows are PRESENCE-GATED like Test-Builders' --carbon (review finding
# 3): on a machine without the carbon builds (fresh clone, no skin) their
# sources do not exist, and under $ErrorActionPreference=Stop an unguarded
# Copy-Item would ABORT the deploy mid-way - skipping the gate-honour block,
# the stale-twin cleanup and the armed-tier restore.
$zcarbonBuilt = Test-Path "$proj\tools\selective-safe\z_SC4UIScale_ZCarbonArt.dat"
foreach ($f in $PACKAGE_FILES) {
    if ($f.Selector) { continue }                        # the SelectorUI block below
    if ($f.Carbon -and -not $zcarbonBuilt) { continue }
    $src = Join-Path $proj $f.Src
    if ($f.Optional -and -not (Test-Path $src)) { continue }   # absent is a valid state
    $dstDir = switch ($f.Dir) { "zzz" { $zzz } "our" { $our } default { $plug } }
    Copy-Item $src (Join-Path $dstDir $f.Name) -Force
}
if (-not $zcarbonBuilt) {
    Write-Output "  ZCarbon packages NOT built on this machine (no carbon inputs) - skipped; gates leave any deployed copies disarmed"
}
# A CsiIcons-specific "remove any armed 15x/3x" sweep used to sit here. It
# was written when 2x was assumed to be the active tier always, and it DELETED
# THE CORRECT FILE on a 3x install - the armed-tier restore at the end of this
# script would re-arm 3x and this block would remove it again, every run. The
# armed tier is now snapshot-and-restored generically for every family (see the
# ARMED-TIER SNAPSHOT block at the top), so a per-package sweep can only
# disagree with it. Deleted rather than repaired: two things deciding the same
# question is the bug, not the tie-break.

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
$selRow = @($PACKAGE_FILES | Where-Object { $_.Selector })
if ($selRow.Count -ne 1) {
  throw ("_packaging\PackageFiles.psd1 must have exactly one Selector row, found " + $selRow.Count)
}
$selSrc = Join-Path $proj $selRow[0].Src
$selName = $selRow[0].Name
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
  Copy-Item $selSrc (Join-Path $zzz ($selName + $selSuffix)) -Force
  # Remove the opposite form so exactly one exists (PRESENCE IS NOT ARMING).
  $selOther = Join-Path $zzz ($selName + $(if ($selSuffix) { "" } else { ".x1-disabled" }))
  if (Test-Path $selOther) { Remove-Item $selOther -Force }
  Write-Output ("  SelectorUI-1x -> " + $(if ($selSuffix) { "stashed (scaled tier live)" } else { "ARMED (stock tier - 1x keeps the selector)" }))
} else {
  Write-Output "  SelectorUI-1x source MISSING - run tools\dialog-static\build_selector_1x.py"
}
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
# The package copy above always writes each family's 2x file to the plain name. Put
# back whatever WAS armed, so a 1.5x or 3x install is not left with two live
# copies of the same TGIs racing on load order. Bytes refreshed, decision
# untouched - the same split of authority the dependency-gate block uses.
# A family with nothing recorded was not armed before (clean install): its 2x
# stays armed, which is the historical default.
# "NOTHING ARMED" IS A STATE, NOT A GAP. Set-Tier.ps1 -Tier 1 disarms every
# tier package on purpose - that IS the 1x baseline. This restore used to treat
# an empty snapshot as "no information" and leave whatever the package copy had
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

# SelectiveArt's own restore (STABLE-FILENAME PILOT). The package copy
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
# Everything above writes the tier-tagged rename layout that
# _packaging\PackageFiles.psd1 names. Build-Dist.ps1 copies the same rows and
# calls this same converter last, so the two cannot drift: one list, one
# conversion. (Before audit B12 the converter was the only thing the two
# scripts shared: Build-Dist regex-parsed this script's copy lines, 30 of them
# were invisible to it, and it re-listed those by hand.)
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

# ---- RESTORE THE GATE VERDICTS (2026-08-30) --------------------------------
# Put back every package that was inert before this run. See the GATE-VERDICT
# SNAPSHOT block at the top for why this is a restore and not a re-computation.
$restoredOff = 0
foreach ($live in $INERT_BEFORE.Keys) {
    $off = $INERT_BEFORE[$live]
    if (-not (Test-Path $off)) { continue }
    if ((Test-Path $live) -and
        (Get-Item $live).Length -eq (Get-Item $off).Length -and
        (Get-FileHash $live -Algorithm SHA256).Hash -eq
        (Get-FileHash $off  -Algorithm SHA256).Hash) { continue }
    Copy-Item $off $live -Force
    $restoredOff++
}
if ($restoredOff) {
    Write-Output ("  restored " + $restoredOff + " gate-off package(s) the " +
        "copy/seed stages had re-armed (they stay inert until the DLL's own " +
        "gate says otherwise)")
}

$a = (Get-Item "$proj\build\Release\SC4UIScale.dll").Length
$b = (Get-Item "$plug\SC4UIScale.dll").Length
if ($a -ne $b) { Write-Output "DEPLOY SIZE MISMATCH src=$a dst=$b"; exit 1 }
# The old line here named only SelectiveArt + DialogStatic and was how the
# ItemIcons omission stayed invisible - it read as a complete manifest.
# WebText IS deployed (its row in _packaging\PackageFiles.psd1, since
# v4.5.0) - the old summary still listed it as hand-placed, the exact
# stale-manifest shape the comment above this line warns about.
Write-Output ("deployed SC4UIScale.dll + SelectiveArt/DialogStatic/ItemIcons/ItemIconsSub tiers " +
    "+ 3rd-party gated dats + WebText + 3 FontStyle tier sources at " + (Get-Date -Format "HH:mm:ss") +
    "   (NOT deployed, hand-placed: MenuFix)")
