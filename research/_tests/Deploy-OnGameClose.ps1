# Paths are RESOLVED, not hard-coded: Documents may be redirected by
# OneDrive, and the repo may be cloned anywhere (task #108).
# Wait for SimCity 4 to close, then deploy the freshly built SC4UIScale.dll
# plus the SelectiveArt AND DialogStatic tier dats. The game runs ELEVATED
# and holds these files open - never kill it (standing order). Polls 5 s.
$ErrorActionPreference = "Stop"
$proj = (Split-Path -Parent $PSScriptRoot)
$plug = (Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'SimCity 4\Plugins')
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
# #105/#107: PRESERVE THE LOG BEFORE THE NEXT LAUNCH DESTROYS IT.
# SC4UIScale.log is RECREATED on every game launch. On 2026-08-03 that silently
# destroyed the run-14 SPINPROBE capture - the only recording of the spinning
# thread we had - because the next run overwrote it before it was copied. Every
# deploy is immediately followed by a launch, so this is the last safe moment.
# Named by the log's OWN mtime, not "now", so the file keeps the timestamp of
# the run it came from.
$srcLog = "$plug\SC4UIScale.log"
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
Copy-Item "$proj\tools\selective-safe\z_SC4UIScale_SelectiveArt.dat" "$plug\z_SC4UIScale_SelectiveArt-2x.dat" -Force
Copy-Item "$proj\tools\packages\15x\z_SC4UIScale_SelectiveArt-15x.dat" "$plug\z_SC4UIScale_SelectiveArt-15x.dat.x1-disabled" -Force
Copy-Item "$proj\tools\packages\3x\z_SC4UIScale_SelectiveArt-3x.dat" "$plug\z_SC4UIScale_SelectiveArt-3x.dat.x1-disabled" -Force
Copy-Item "$proj\tools\dialog-static\z_SC4UIScale_DialogStatic.dat" "$plug\z_SC4UIScale_DialogStatic-2x.dat" -Force
Copy-Item "$proj\tools\packages\15x\z_SC4UIScale_DialogStatic-15x.dat" "$plug\z_SC4UIScale_DialogStatic-15x.dat.x1-disabled" -Force
Copy-Item "$proj\tools\packages\3x\z_SC4UIScale_DialogStatic-3x.dat" "$plug\z_SC4UIScale_DialogStatic-3x.dat.x1-disabled" -Force

# ITEM ICONS - ADDED 2026-08-03 (#116). These were MISSING from this script
# for its whole life, and ScaleTier actively tier-manages them
# (ScaleTier.cpp:530 SyncDat "z_SC4UIScale_ItemIcons"), so the deployed copies
# had frozen at whatever build epoch last hand-placed them. CAUGHT IN THE ACT
# tonight: a PNG re-deflate pass rebuilt every package, this script reported
# "SelectiveArt + DialogStatic tiers", and the live ItemIcons silently stayed
# on the pre-optimization bytes.
# This is EXACTLY the #58 failure class recorded further down this file
# ("this package was NEVER in this list, so the deployed copy froze at the
# 2026-07-29 build epoch"). A deploy script that is not a complete manifest is
# a slow-acting bug generator: everything looks green and the artifact is old.
# ⚠ SOURCE IS THE **UNTAGGED** FILE. tools\itemicons\ holds BOTH
# z_SC4UIScale_ItemIcons.dat and z_SC4UIScale_ItemIcons-2x.dat, and they are
# not the same build. Test-DatIntegrity treats the UNTAGGED one as canonical
# (it is what SelectiveArt/DialogStatic do too - the 2x tier's source carries
# no tag). Deploying from the tagged copy makes DatIntegrity FAIL, which is
# how this was caught rather than shipped.
Copy-Item "$proj\tools\itemicons\z_SC4UIScale_ItemIcons.dat" "$plug\z_SC4UIScale_ItemIcons-2x.dat" -Force
Copy-Item "$proj\tools\packages\15x\z_SC4UIScale_ItemIcons-15x.dat" "$plug\z_SC4UIScale_ItemIcons-15x.dat.x1-disabled" -Force
Copy-Item "$proj\tools\packages\3x\z_SC4UIScale_ItemIcons-3x.dat" "$plug\z_SC4UIScale_ItemIcons-3x.dat.x1-disabled" -Force
# SaveWarningUI (v2.38.0, task #79c): 2x copies of the two in-city quit/exit
# confirm scripts built from the save-warning MOD's versions. MUST land in the
# zzz-SC4UIScale SUBFOLDER - root Plugins files load BEFORE subfolders, so a
# root copy could never beat the mod in 150-mods\ (the load-order law, and the
# whole reason those dialogs opened 1x). ScaleTier gates it on that mod still
# being installed; deploy it live and let the DLL disable it if it should not
# be active.
$zzz = Join-Path $plug "zzz-SC4UIScale"
# ItemIconsSub - ADDED 2026-08-03 (#116), same omission as ItemIcons above.
# ScaleTier.cpp:537 tier-manages this one too.
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
Copy-Item "$proj\tools\packages\15x\z_SC4UIScale_CsiIcons-15x.dat" "$zzz\z_SC4UIScale_CsiIcons-15x.dat" -Force
Copy-Item "$proj\tools\packages\2x\z_SC4UIScale_CsiIcons-2x.dat" "$zzz\z_SC4UIScale_CsiIcons-2x.dat.x1-disabled" -Force
Copy-Item "$proj\tools\packages\3x\z_SC4UIScale_CsiIcons-3x.dat" "$zzz\z_SC4UIScale_CsiIcons-3x.dat.x1-disabled" -Force

# UncoveredIcons - ADDED 2026-08-15 (#149). ItemIcons a third-party LOT ships
# that no package of ours covered; at any tier > 1 the strip's cell is scaled
# but that art is not, so the four-state read over-runs the bitmap and the icon
# draws wrong and vanishes on hover. Rebuild with:
#     python tools\itemicons\build_uncovered_icons.py
# which rediscovers the set from the player's OWN Plugins tree, so this is not
# a list that can go stale - re-run it after installing new lots.
# ⛔ OPTIONAL BY CONSTRUCTION - a hard Copy-Item here was a RELEASE BUG.
# This package holds however many uncovered third-party icons THIS install
# has, so on a clean install - which is exactly what a first-time player and
# the #148 vanilla check both are - it does not exist at all, and the deploy
# would have died on a missing file. ABSENT IS A VALID STATE, NOT AN ERROR.
foreach ($t in @(@("2x",""), @("15x",".x1-disabled"), @("3x",".x1-disabled"))) {
  $srcU = Join-Path $proj ("tools\itemicons\out\z_SC4UIScale_UncoveredIcons-" + $t[0] + ".dat")
  if (Test-Path $srcU) { Copy-Item $srcU (Join-Path $zzz ("z_SC4UIScale_UncoveredIcons-" + $t[0] + ".dat" + $t[1])) -Force }
}

# ⛔ THE COMMENT THAT USED TO SIT HERE WAS FALSE ON BOTH COUNTS (2026-08-05).
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
Copy-Item "$proj\tools\webtext\z_SC4UIScale_WebText.dat" "$plug\z_SC4UIScale_WebText.dat" -Force
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
# NamIcons (task #139, 2026-08-05): 1.5x/2x/3x copies of the Network Addon
# Mod's OWN 392 menu ItemIcons, gated in ScaleTier on the presence of
# NetworkAddonMod_Controller.dat. Same zzz- rule as its siblings - NAM lives
# in 770-network-addon-mod\ and only zzz- sorts after it.
# ⚠ THESE THREE FILES WERE PLACED BY HAND during the session that built them,
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
# ⚠ The 2x source is tools\fonts\FontStyle.candidate.ini - there is no
# tools\packages\2x\ directory. It is byte-identical to make_fontstyle.py's
# factor-2 output apart from its hand-written ";;" banner (asserted by
# --selfcheck).
Copy-Item "$proj\tools\fonts\FontStyle.candidate.ini" "$plug\FontStyle-2x.ini" -Force
Copy-Item "$proj\tools\packages\15x\FontStyle-15x.ini" "$plug\FontStyle-15x.ini" -Force
Copy-Item "$proj\tools\packages\3x\FontStyle-3x.ini" "$plug\FontStyle-3x.ini" -Force
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
# ⛔ .x1-disabled IS AN OVERLOADED SUFFIX, AND THAT BIT THIS LOOP (2026-08-05).
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
foreach ($dir in @($plug, "$plug\zzz-SC4UIScale")) {
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
# ⚠ THE DEPLOY REFRESHES CONTENT. IT MUST NOT CHANGE GATE STATE. Those are two
# different authorities: this script owns "are the bytes current", the DLL owns
# "should this be loaded at all". An earlier version of this block deleted the
# disabled twin instead, which silently overrode the DLL's decision and turned
# the third-party gate red - self-healing at the next launch, but red in the
# meantime, and a standing red makes every later red look pre-excused.
#
# So: push the fresh bytes into the DISABLED name and remove the active one.
# Content current, gate decision untouched. On a machine where the mod IS
# installed there is no twin and none of this runs.
foreach ($dir in @($plug, "$plug\zzz-SC4UIScale")) {
    if (-not (Test-Path $dir)) { continue }
    Get-ChildItem $dir -Filter "*-2x.dat.x1-disabled" -File -ErrorAction SilentlyContinue |
        ForEach-Object {
            $active = $_.FullName -replace '\.x1-disabled$', ''
            if (Test-Path $active) {
                Copy-Item $active $_.FullName -Force
                Remove-Item $active -Force
                Write-Output ("  package is dependency-GATED OFF; refreshed in place: " + $_.Name)
            }
        }
}

$a = (Get-Item "$proj\build\Release\SC4UIScale.dll").Length
$b = (Get-Item "$plug\SC4UIScale.dll").Length
if ($a -ne $b) { Write-Output "DEPLOY SIZE MISMATCH src=$a dst=$b"; exit 1 }
# The old line here named only SelectiveArt + DialogStatic and was how the
# ItemIcons omission stayed invisible - it read as a complete manifest.
Write-Output ("deployed SC4UIScale.dll + SelectiveArt/DialogStatic/ItemIcons/ItemIconsSub tiers " +
    "+ 3rd-party gated dats + 3 FontStyle tier sources at " + (Get-Date -Format "HH:mm:ss") +
    "   (NOT deployed, hand-placed: WebText, MenuFix)")
