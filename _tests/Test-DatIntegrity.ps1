# Paths are RESOLVED, not hard-coded: Documents may be redirected by
# OneDrive, and the repo may be cloned anywhere (task #108).
# Regression: the deployed packages match their expected entry counts and
# the built artifacts still exist. Update EXPECTED when packages change
# (that's a deliberate act - see REGRESSION.md).
# PASS = exit 0, "ALL PASS".
#
# ===========================================================================
# v4.5.0 REWRITE - THE LAYOUT UNDER THIS SUITE CHANGED (2026-08-29)
#
# Through v4.4.0 a scale tier was ARMED BY RENAMING dats: the active tier sat
# as `z_SC4UIScale_<Pkg>-<tag>.dat` and its siblings as
# `...-<tag>.dat.x1-disabled`. From v4.5.0 (src\ScaleTier.cpp: ArmOne /
# CommitArming / WriteArmState) arming is a CONTENT SWAP at a stable filename:
#
#   LIVE     z_SC4UIScale_<Pkg>.dat            the only thing SC4 loads. Its
#                                              CONTENT changes; the name never
#                                              does, at any tier, under any
#                                              gate verdict, ever.
#   PAYLOAD  z_SC4UIScale_<Pkg>.<tag>.uipay    inert, never renamed, never
#                                              loaded. tag is one of
#                                              15x / 2x / 3x / 1x / on / off.
#                                              (Measured, not assumed: probe
#                                              #202 proved the plugin scan is
#                                              EXTENSION-gated, with 13 live
#                                              .dat files as the positive
#                                              control.)
#   STATE    z_SC4UIScale_STATE.txt            written by the DLL every boot,
#                                              per folder. TSV, two '#' header
#                                              lines, then
#                                              base<TAB>tag<TAB>reason<TAB>
#                                              paySize<TAB>payTime<TAB>
#                                              liveSize<TAB>liveTime.
#
# EVERY ASSERTION HERE THAT USED TO NAME A TIER-TAGGED FILE IS THEREFORE DEAD
# BY CONSTRUCTION - it would look for a name that no longer exists and fail
# for its own reason, which is worse than no gate (law 50b). So every path is
# resolved through Resolve-PkgFile, which knows BOTH layouts and SAYS WHICH IT
# FOUND. That is not politeness: this repo's own deploy script is still on the
# rename layout today, so a run against a live install legitimately reports the
# OLD layout, and a suite that crashed or went red on that would be untrusted
# exactly when it is needed.
#
# TWO THINGS THE FILENAME USED TO TELL US AND NO LONGER CAN, both now sourced
# from evidence instead:
#   "which tier is armed"       -> STATE.txt's tag column, CROSS-CHECKED against
#                                  the live file's content hash. Two independent
#                                  instruments; disagreement is red.
#   "is this package gated off" -> STATE.txt's reason/tag columns. A gated-off
#                                  package is a LIVE .dat holding `.off` content,
#                                  indistinguishable on a directory listing from
#                                  an armed one.
# ===========================================================================
$ErrorActionPreference = "Stop"
$proj = Split-Path $PSScriptRoot -Parent
$packer = Join-Path $proj "tools\dbpf\DbpfPack.exe"
$plugins = (Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'SimCity 4\Plugins')
# v4.2.0 (subfolder move): our files live in the 010-SC4UIScale subfolder;
# zzz-SC4UIScale stays top-level. Row names below carry their folder.
$our = Join-Path $plugins '010-SC4UIScale'
$zzz = Join-Path $plugins 'zzz-SC4UIScale'
$OUR_DIRS = @($our, $zzz)

$failures = @()

# The packer is the instrument every entry-count assertion below is measured
# with. NULL IS NOT EVIDENCE: without it, every count check would either throw
# or silently score zero, and "no counts were wrong" would mean "no counts were
# taken". Refuse up front and say so.
if (-not (Test-Path $packer)) {
  Write-Output ("FAIL: no DbpfPack.exe at " + $packer + " - every entry-count " +
    "assertion in this suite is measured with it, so none of them could run. " +
    "This is a REFUSAL, not a pass (build tools\dbpf).")
  exit 1
}

# ---------------------------------------------------------------------------
# LAYOUT CENSUS - RUN FIRST, AND IT MAY REFUSE.
#
# Everything below resolves paths through one of two naming schemes. Which one
# is on disk is a FACT to be measured, not a version number to be assumed: an
# install part-way through migration carries both, and the DLL's own
# MigrateRenamesToPayloads converts a folder at a time. Counting first means
# the report can NAME the layout instead of emitting 60 "NOT FOUND" lines that
# all have the same single cause.
#
# GOES RED WHEN: zero of our package files are found at all (wrong Plugins
# path, or the mod is not deployed - either way nothing below would be
# evidence about anything).
# ---------------------------------------------------------------------------
$censusPayload  = @()
$censusTagged   = @()   # bare tier-tagged .dat (RENAME layout, armed)
$censusDisabled = @()   # .x1-disabled          (RENAME layout, stashed)
$censusStable   = @()   # untagged .dat         (both layouts: the live file)
foreach ($d in $OUR_DIRS) {
  if (-not (Test-Path $d)) { continue }
  foreach ($f in @(Get-ChildItem $d -File -ErrorAction SilentlyContinue |
                   Where-Object { $_.Name -like 'z_SC4UIScale_*' })) {
    if ($f.Name -like '*.uipay')       { $censusPayload  += $f; continue }
    if ($f.Name -like '*.x1-disabled') { $censusDisabled += $f; continue }
    if ($f.Extension -ne '.dat')       { continue }
    if ($f.BaseName -match '-(15x|2x|3x|4x|1x)$') { $censusTagged += $f }
    else                                          { $censusStable += $f }
  }
}
$nOurFiles = $censusPayload.Count + $censusTagged.Count + $censusDisabled.Count + $censusStable.Count
if ($nOurFiles -eq 0) {
  Write-Output ("FAIL: ZERO z_SC4UIScale_* files under " + $plugins +
    " (looked in 010-SC4UIScale and zzz-SC4UIScale). Nothing was examined, so " +
    "nothing below could have gone red. REFUSAL, not a pass - check the " +
    "Documents redirect and that the mod is deployed.")
  exit 1
}
$layout = 'unknown'
if ($censusPayload.Count -gt 0 -and ($censusTagged.Count + $censusDisabled.Count) -gt 0) { $layout = 'MIXED' }
elseif ($censusPayload.Count -gt 0) { $layout = 'PAYLOAD' }
elseif (($censusTagged.Count + $censusDisabled.Count) -gt 0) { $layout = 'RENAME' }
Write-Host ("  layout on disk: " + $layout + "  (" + $censusPayload.Count +
  " .uipay payload(s), " + $censusTagged.Count + " tier-tagged .dat, " +
  $censusDisabled.Count + " .x1-disabled, " + $censusStable.Count +
  " stable .dat)")
if ($layout -eq 'RENAME') {
  Write-Host ("  note: this install is on the PRE-4.5.0 RENAME layout. That is " +
    "the expected state until _tests\Convert-ToPayloadLayout.ps1 has run over " +
    "it (or the DLL has booted once and migrated it). Checks that only exist " +
    "in the payload layout say so individually rather than passing silently.")
}
if ($layout -eq 'MIXED') {
  # Not automatically fatal here - the per-package BOTH-LAYOUTS gate further
  # down decides that, because a folder mid-migration is only dangerous when
  # ONE PACKAGE has live files under both schemes.
  Write-Host ("  note: BOTH layouts are present in this tree. Per-package " +
    "overlap is gated below; a clean split (one folder migrated, one not) is " +
    "survivable, a per-package overlap is not.")
}

# ---------------------------------------------------------------------------
# THE RESOLVER. One place that knows both naming schemes, so no assertion below
# has to.
#
#   Rel = "<folder>\z_SC4UIScale_<Pkg>"   (no tag, no extension)
#   Tag = "15x" | "2x" | "3x" | "1x" | "on" | "off"
#
# Returns @{ Path; Layout; Live } or $null. `Live` means "SC4 loads this file
# as it stands" - true only for a bare tier-tagged .dat in the rename layout.
# Payloads are never live by construction; that is the whole point of .uipay.
# ---------------------------------------------------------------------------
function Resolve-PkgFile {
  param([string]$Rel, [string]$Tag)
  $stem = Join-Path $plugins $Rel
  # PAYLOAD layout first: it is the target state, and where both exist the
  # payload is the authority (the tier-tagged file is migration leftover).
  $pay = "$stem.$Tag.uipay"
  if (Test-Path $pay) { return @{ Path = $pay; Layout = 'payload'; Live = $false } }
  # RENAME layout. "on" was the untagged always-on form; tiers carried -<tag>.
  if ($Tag -eq 'on') { $cand = "$stem.dat" } else { $cand = "$stem-$Tag.dat" }
  if (Test-Path $cand)               { return @{ Path = $cand; Layout = 'rename'; Live = $true } }
  if (Test-Path "$cand.x1-disabled") { return @{ Path = "$cand.x1-disabled"; Layout = 'rename'; Live = $false } }
  return $null
}
# The one file SC4 actually loads for a package. Same name in both layouts - in
# the rename layout it only exists for the v4.0.3 stable-name pilot
# (SelectiveArt) and for the untagged always-on packages.
function Resolve-LiveFile {
  param([string]$Rel)
  $p = (Join-Path $plugins $Rel) + ".dat"
  if (Test-Path $p) { return $p }
  return $null
}

# ---------------------------------------------------------------------------
# rel = folder + package base (NO tier tag, NO extension - the tag is its own
# column now, because it is no longer part of any filename in the target
# layout). tag: 15x/2x/3x/1x/on, or "plain" for a package the arming pass
# never touches. entries = expected DBPF entry count.
# ---------------------------------------------------------------------------
$EXPECTED = @(
  # SelectiveArt: 696 at EVERY tier (1.5x / 2x / 3x).
# 2026-08-19: 693 -> 696. The DEFAULT/PLACEHOLDER sim faces {EA32F100,
# EA32F101} in both portrait groups - 4 TGIs, 3 of them new (one was already
# staged via a .UI reference). They are the same 36x41 contract as the 19
# named portraits, and the category-3 indicator divides its UVs by ONE
# texture side - so a 36x41 fallback beside a 72x82 named face cannot both
# be right, and the fallback sims drew magnified. Staging the family, not
# the set.
  # #190 (2026-08-19): 655 -> 693. The delta is EXACTLY 38 = the 19 runtime
  # Sim portraits (0xFA8CDFBF..0xFA8CDFD2, with 0xFA8CDFCF absent, so 19 not 20)
  # shipped under BOTH groups the archive carries, 0x46A006B0 and 0x1ABE787D.
  # That the arithmetic lands exactly on 38 with no remainder IS the check: a
  # staging change that also dragged in strays would not.
  # Verified from the DBPF ENTRY PAYLOADS, not the builder's own count (law:
  # presence is not execution) - 36x41 source, 54x62 / 72x82 / 108x123 at
  # 1.5x / 2x / 3x, i.e. exactly 36x41*f at every tier.
  # If this number moves again, the portraits are NOT the explanation twice.
  # Find the new delta before editing this line.
  # #136 (v2.88.0) ENDED THE TIER SPLIT. This block used to read "651 at 3x,
  # THE TIER SPLIT IS DELIBERATE ... forced by an encoding ceiling", and that
  # was true only for as long as nobody widened the encoding.
  #   639 baseline
  # + 12  news/advice row <IMG> glyphs {46a006b0,0x1441625x, (i&3)!=3}
  # +  4  the dismiss-X glyphs (...53/57/5B/5F) -- now at ALL tiers
  # The row's width budget lives at 0x0079388F. Scaling the X needs
  # S = 2*round(18f)+9+round(16f) = 87 at 1.5x, 113 at 2x, 165 at 3x. 165 does
  # not fit a sign-extended imm8, so 3x used to hold the X at stock size.
  # CodePatches now REWRITES the 19-byte window at 0x0079388B when S > 127,
  # turning `sub esi,imm8` into `lea esi,[eax-imm32]` and paying for the extra
  # bytes with a folded `mov` and a store proven dead by liveness. 1.5x and 2x
  # still take the untouched 3-byte path.
  # STILL A HARD COUPLING. build_selective_safe.py stages the X glyphs
  # unconditionally now, and that is only valid while the wide re-encode
  # actually applies. If it is removed, or the log says "advice row wide
  # re-encode REFUSED", the builder filter AND this count must go back to 651
  # for 3x in the SAME build - otherwise the budget describes art that did not
  # ship and the row X is clipped again.
  # THESE GLYPHS ARE INVALID WITHOUT CodePatches::ApplyAdviceRowScale.
  # The row is a three-column HTML table [arrow | headline | X] whose middle
  # column is GetW() - 61, where 61 = 18 + 18 + 9 + 16 (arrow, X, fixed
  # chrome, and the STOCK SCROLLBAR CELL - the reserve is not one number).
  # The glyphs are <IMG> tags with no declared size, so 2x art grows its
  # column and pushes the dismiss X past the pane's content edge. The patch
  # re-derives the 61 from the shipped art so the declared total returns to
  # GetW() - 9 - round(16f). If that patch is ever skipped or removed, drop
  # these glyphs in the SAME build - art without the patch IS the #88 defect.
  # History (all user eyes-on, same city and headlines): all 16 at 2x ->
  # arrows correct, X gone; 12 at 2x -> arrows correct, X STILL gone (which
  # refuted "the X's own size moved it" and pointed at the ARROW column);
  # then v2.40.0's flat 25px reserve passed COLLAPSED rows and clipped the X
  # on EXPANDED ones, because expanding raises the scrollbar and the usable
  # width is GetW() - 2*gutter - scrollbarW with scrollbarW read LIVE.
  # Also reverted this session and still out: {46a006b0,0xE2B66DB8} 2x - no
  # visible change at all; its premise (a cloned button born at art size)
  # was refuted.
  # 639 SelectiveArt = 638 + (2026-07-31, task #59) the GOLD PAUSE alert-border
  # sheet {46a006b0,0x14315E61}. There are THREE alert borders - red
  # (disaster) 14315E60, gold (paused) 14315E61, green (situation) 14315E62,
  # swapped by UpdateAlertBorder 0x007E8A90 - and the first and third were
  # staged in 2026-07 MISLABELLED as "Mayor rating face state A/B" while the
  # middle one was dropped. cSC4WinAlertBorder draws nine-slice with
  # cell = img/3 and UNSTRETCHED corners, so stroke and badge are exactly the
  # art pixels: 120x120 gave a 3px frame, 240x240 gives 6px.
  # 638 SelectiveArt = 637 + (2026-07-31, task #72) the REGION city-bubble
  # Mayor Rating bar sheet {46a006b0,0x14416327}. cSC4WinAuraBar (clsid
  # 0xAA5D16A9) draws src.L = (imgW-winW)>>1 and src.R = winW+src.L - the
  # source WIDTH comes from the WINDOW - so the stock 102-wide sheet in the
  # correctly-doubled 204-wide window read TWO image-widths and drew the
  # segment ladder twice. Code-bound (SetImage at VA 0x7B517E), one reference
  # image-wide, zero .UI refs, so only CODE_BOUND_TGIS could reach it.
  # 637 SelectiveArt = 632 + (v2.26.1) the 5 master-budget band arts
  # 2BFEB0CB-CF (the eye-icon Master Power/Police/... sub-dialogs: dialog
  # size = sum of band art sizes, so unstaged 1x bands = a 1x window).
  # 632 = 616 + (2026-07-30, "split/swapped dials") the 16
  # U-Drive-It gauge NEEDLE STRIPS (vehicle-exemplar property 0x2BE8E6CB,
  # binder VA 0x5646AE; 2805-3740 px wide = past the 2048 texture tile,
  # so the DLL must never STRETCH them - 2x data makes every draw a pure
  # cell copy again, and the gauge hook snaps to 1.0).
  # 616 SelectiveArt = 506 + (2026-07-30, task #55/#47) the ENTIRE 42x42
  # thumbnail group 0x4C06F888 as code-bound 2x-in-place (112 members in
  # SimCity_1.dat; 110 new - 2 were already EXCLUSIVE via the My Sims style
  # thumbs). The U-Drive-It picker cells are GZWinBMP placeholders with
  # DANGLING image= refs ({46a006b0,ea32f104}/{6b998f30} exist in NO shipped
  # archive); binder VA 0x76FDB0 SetImages {0x4C06F888, vehicle-exemplar
  # property 0xEBFC5E5E} at runtime, so the art pass could never see them
  # ("picker icons duplicated"). Same group backs the My Sims car/bike style
  # thumbs. DialogStatic stays 259 entries but the two picker scripts'
  # placeholder imagerects are now scaled (RUNTIME_BOUND_2X) to match.
  # 215 = 214 + audio playlist checkbox strip {46a006b0,14416244} (2026-07-23)
  # 43 = region-screen set (see 2026-07-23 history). 51 = +3 city building
  # query panels (ca56783a/4a5672bf/2a567dc1) + 5 shared art clones; the
  # query family renders 1x stock (main-window children, outside the sweep)
  # so static-doubling is collision-free (task #36 validation batch)
  # 328 SelectiveArt = 271 + (2026-07-29 evening, task #42 news) 57 more
  # code-bound entries: the news reader/advisor page art the exe binds at
  # VA 0x77A495+/0x780952+ (0x140155b4..f7 span; newspaper page backgrounds,
  # advisor mugs) + the sc4://image HTML-page art harvested from the 189
  # story/tutorial LTEXTs into tools\selective-safe\html-image-refs.txt.
  # NOT included (permanent, deliberate): {46a006b0,14416264}
  # html_TextBG_General - 3 unscaled city-HUD panels (Map/Data View,
  # I-0b72f276/I-ea287193/I-2bc9060f) slice it as a 16px-inset edgeimage;
  # a 2x in-place would corrupt their frames. HTML pages tile it 1x =
  # slightly finer paper texture, invisible. Audio Options uses its own
  # 2x clone {46a006b0,47026265} (DialogStatic).
  # 271 SelectiveArt = 264 + (2026-07-29) Emergency Tools 0x0992FD17 (script
  # I-899302fc + its art incl. the ring bitmap {46a006b0,14215e2c}) - the
  # LAST missed mayor flyout, same 1x-art-in-2x-window symptom as the three
  # below; its GZWinBMP class draws dst = src size, so 2x art = 2x draw.
  # 264 SelectiveArt = 240 + (2026-07-28) the news ticker/reader art
  # (0xCA2AEDC0 + 0xAA231508, script I-2a2aed99) and the three mayor-mode
  # toolbar flyouts that had been missed when their siblings were added:
  # Zones 0x69923479, Transportation 0xC99237A0, Utilities 0xE992F711.
  # Their 1x art + 1x imagerect inside correctly-placed 2x windows is what
  # drew the Zone flyout's ring at half size in the WRONG button's band.
  # ALSO 2026-07-28: the stray UNTAGGED z_SC4UIScale_SelectiveArt.dat that had
  # been loading alongside -2x all along is retired to
  # tools\selective-safe\replaced\ - exactly the shadowing hazard that the
  # untagged DialogStatic.dat had. (v4.5.0 FOOTNOTE: that hazard is now a
  # FIRST-CLASS GATE - see BOTH LAYOUTS below. An untagged .dat beside a live
  # tagged one is the same two-live-providers shape, and it is what a
  # half-run migration can now reintroduce wholesale.)
  # 240 SelectiveArt = 215 + god-mode toolbar cluster art (0xC991EDA8 twins
  # + terrain-fx/day-night flyouts) 2026-07-24 - the ghost-sun fix.
  # 195 = 51 (region + 3 validation queries) + the auto-discovered rest of
  # the 117-script query family (main-window children, sweep-safe). All
  # building/network query panels now static-double 2026-07-23 (task #36).
  # 206 = +6 (2026-07-28): can't-save-during-disaster confirm 4a89b3f2 +
  # Establish City 2a41436b (scripts + exclusive art), same in all tiers.
  # ItemIcons stays 266 = the STOCK pool only. The submenus mod's 55 own
  # icons (2026-07-29; un-overridden they render DUPLICATED - two 1x states
  # per doubled 88px cell) CANNOT be overridden from the Plugins root:
  # LOAD ORDER LAW (proven live): root FILES load BEFORE subfolders, so a
  # root dat never beats a subfolder dat (the mod's 150-mods\ dats). They
  # ship in zzz-SC4UIScale\ below. Sources: tools/itemicons/_work/.
  # 358 = 345 + the Data Views panel (task #45, root 0xAA32BCE6, live
  # script I-2bc9060f). v2.21.0 landed it, v2.21.1 reverted (crash on
  # expand), v2.21.2 RE-LANDED with the DVMAP surface recreate in the DLL
  # (the map child 0x00004203 is a second cSC4WinMiniMap; its one-shot
  # display surface must be recreated after scaling or the window-sized
  # render buffer overruns it - REGRESSION.md "DATA VIEWS PANEL"). This
  # count and the DVMAP block in UiSpike.cpp MOVE TOGETHER: 358 without
  # the DLL lever = the crash build.
  # 461 = 358 + 9 U-Drive-It code-bound arts (v2.21.4: bubble base
  # 094ac89a + the mission icon table from VA 0x44DEC7; 46a006a4/a6
  # conflict-skipped) + 94 from the U-Drive-It DASHBOARD family (v2.21.5:
  # root 0x4BCB938A is the root of ALL 43 per-vehicle console scripts -
  # verified: every file containing it has it as ROOT, none overlap the
  # static dat - so the whole family's shell/gauge art ships 2x).
  # 476 = 461 + 15 My Sims family arts (v2.22.0: roots 0x698894D3 /
  # 0xCA1F1D9C / 0xAA1F1EC5, script I-aa1f1f57 - the panel came OFF the
  # kNeverScaleIds deferral; see REGRESSION.md "MY SIMS").
  #
  # WHY EVERY TIER STILL GETS ITS OWN ROW even though the count is the same at
  # all three: the row asserts THAT TIER'S FILE EXISTS AND PARSES. Under the
  # payload layout that file is `.15x.uipay` / `.2x.uipay` / `.3x.uipay`, and a
  # package missing one of them goes INERT the moment the player switches to
  # that tier (ArmOne: "MISSING PAYLOAD ... falling back to .off. This is a
  # packaging defect"). One shared count, three separate existence facts.
  @{ rel = "010-SC4UIScale\z_SC4UIScale_SelectiveArt";  tag = "2x";  entries = 696 },
  # DialogStatic 255 -> 259 (2026-07-29, Batch A, task #54): the last three
  # bucket-D text-bearing roots joined TARGETS in build_dialog_static.py -
  # I-6b704690 Label Tool (root 0x8A8DFCF5, shared with the generic message
  # box - per-script TGI, so both are doubled independently), I-ca539343
  # narrow region city-bubble stub (0x0A551C53), I-ebd0d36d Select A Bridge
  # sibling button (0x000A0000). All three roots are ALSO in kNeverScaleIds.
  # +4 not +3: the three scripts plus one art asset that became referenced.
  # Same 259 at every tier by construction (one builder, --factor only).
  # 265 -> 266 (2026-08-30): enrolling null-45's Region Census dialog in
  # dialog-static made the builder stage the art that script references,
  # {46A006B0,6BB93CB5}, into this package. MEASURED BENIGN, not assumed:
  # the staged copy is byte-identical to the one SelectiveArt already
  # ships (394x496, same md5), both live in 010-SC4UIScale\ and
  # DialogStatic sorts FIRST, so SelectiveArt still wins and the pixels
  # are the same either way. It is a redundant copy, not a behaviour
  # change. FOLLOW-UP: the census script's art belongs in the
  # RegionCensusUI package or nowhere - suppressing the duplicate is
  # builder surgery that deserves its own measured session.
  @{ rel = "010-SC4UIScale\z_SC4UIScale_DialogStatic";  tag = "2x";  entries = 266 },  # 262 -> 261 2026-08-16: #178 CAM splash {ea7f0eae} now ships ONLY in gated CamUI, ALL tiers consistent. USER DECISION STILL OWED on 262 (ship ungated); flip back if decided
  @{ rel = "010-SC4UIScale\z_SC4UIScale_ItemIcons";     tag = "2x";  entries = 356 },
  # 124 = 55 submenus-mod + 69 other-plugin icons (2026-07-29 landmarks
  # pass): CAM System Integration Module (73: submenu-extended + DLC/Maxis
  # landmark buildings; NOTE ~half its exemplars are TEXT format - the
  # binary-only parse missed 30 of these) + the Maxis Buildings landmark
  # plugins (one each).
  # 125 = 124 + the submenus DLL's Missing Thumb icon 0x144161EC (2026-07-29,
  # never exemplar-bound so the stock-pool derivation missed it). KEPT as
  # defensive cover for a genuinely art-less icon, but it is NOT what the
  # Grutzehaus report was - see below.
  # 130 = 125 + 5 Maxis Buildings landmark icons (2026-07-29, the Grutzehaus
  # report, task #49): 0d1d6acb StoneHouse, 2d1e7a9e TempleOfGrutz,
  # 2d217719 GrutzeIndustries, 4d50ba18 LongfellowCastle, ed2174a0
  # Grutzehaus. These were previously recorded as "NO icon art anywhere",
  # covered by the missing-thumb fallback. THAT WAS WRONG: all five DO have
  # 176x44 art, and it lives inside `.SC4Lot` DBPF archives under
  # `Maxis Buildings\<name>\`, which the plugin sweep never opened because it
  # globbed `*.dat` only. So the submenus DLL's TestForKey SUCCEEDS, the
  # missing-thumb fallback never fires, and the game drew the 1x strip into
  # the doubled 88px cell = two 44px states side by side (the reported
  # "duplicated icon"). See REGRESSION.md "DUPLICATED MENU ICON /
  # MISSING-THUMB FALLBACK". ANY future item-icon sweep MUST scan
  # .SC4Lot/.SC4Desc/.SC4Model, not just .dat.
  @{ rel = "zzz-SC4UIScale\z_SC4UIScale_ItemIconsSub"; tag = "2x"; entries = 130 },
  # THIRD-PARTY DATA PATCH (see tools\research\UPSTREAM-CAM-REPORT.md +
  # memory project-sc4-thirdparty-patches): 6 exemplar-patch cohorts fixing
  # CAM 4.0.1's ten broken submenu parents (police/fire/jail/prison/
  # lifeguard). DELETE when CAM fixes upstream, then re-run
  # tools\itemicons\scan_unreachable_items.py to confirm.
  # THIRD-PARTY DATA GAP (#147, 2026-08-06): CAM's Power/Water chart exemplars
  # bind label LTEXT 0xFF5D2E9F for their 4th series, and that id exists in NO
  # installed archive (0 hits in 118,896 records / 107 DBPF files; 0x0A5D2E9D,
  # 0xFF5D2E98 and 0xFF5D2E9E found as positive controls). The row rendered with
  # a checkbox, a cyan swatch and NO CAPTION. We SUPPLY the missing resource -
  # one 20-byte LTEXT, "Exported" - and never touch CAM's file.
  # TIER-INDEPENDENT: a string has no geometry, so there is no 15x/3x pair.
  # Built by tools\itemicons\build_cam_graph_labels.py.
  # DELETE when CAM fixes the id upstream (reported: UPSTREAM-CAM-REPORT.md #4).
  # tag "plain": build_payloads.py categorises this as TIER-INDEPENDENT and
  # invents NO payload for it, and ScaleTier.cpp never SyncDats it. So its
  # `.dat` is a plain always-live file in BOTH layouts, and it must NOT be
  # dragged into any armed-tier or payload-completeness reasoning below.
  @{ rel = "zzz-SC4UIScale\z_SC4UIScale_CamGraphLabels"; tag = "plain"; entries = 1 },
  # THIRD-PARTY .UI OVERRIDE (task #44, 2026-07-29): CoriBoom's 36 Slot
  # Building Styles UI (inside the allow-more-building-styles-dll sc4pac)
  # REPLACES the stock Building Style Control script {0,96A006B0,6BC61F19}
  # from 150-mods\, so by the LOAD-ORDER LAW our root SelectiveArt copy never
  # won and the panel rendered corrupted. This ships the MOD's script (never
  # the stock one - that would revert its 36-slot UI) with imagerects scaled
  # and shared art retargeted at our clones. 2 entries = that script + the
  # mod's OWN background art {856DDBAC,46A006B0,CBC3C2B9}, which the mod also
  # ships from 150-mods\ at 516x654 (TALLER than the stock 516x396, for its 36
  # slots) and which therefore shadowed our root 2x copy as well - the drawn
  # background covered only a 516x654 corner of the correctly-doubled
  # 1038x1308 window. Upscaled from the MOD's bitmap via Upscale2x.exe.
  @{ rel = "zzz-SC4UIScale\z_SC4UIScale_ThirdPartyUI"; tag = "2x"; entries = 2 },
  # WarriorUI (task #94): 2 scripts (mayor LANDSCAPE flyout 09923283 + SIGNS &
  # LABELS column cb95403e, both replaced from 150-mods\ by warrior's
  # god-terraforming-in-mayor-mode) + 2 art (the MOD's own 14215E27/EB7C4D3B,
  # upscaled from ITS bitmaps). Gated on both mod dats by exact name+size.
  @{ rel = "zzz-SC4UIScale\z_SC4UIScale_WarriorUI"; tag = "2x";  entries = 4 },
  @{ rel = "zzz-SC4UIScale\z_SC4UIScale_WarriorUI"; tag = "15x"; entries = 4 },
  @{ rel = "zzz-SC4UIScale\z_SC4UIScale_WarriorUI"; tag = "3x";  entries = 4 },
  # CsiIcons (v4.5.2): the U-Drive-It offer-balloon icons - the package that
  # shipped the WRONG TIER twice (#196) yet had no entry-count row and no
  # built-vs-deployed row; the 2026-08-30 audit found it was the only live
  # SyncDat package with neither. 16 entries at every tier, measured off the
  # DBPF headers of tools\packages\<tier>\ (matches PACKAGE-MANIFEST.md).
  # RaiseUI (2026-08-30): warrior's "Raise the UI Mod" ships ONLY the two HUD
  # scripts and no art, so our copy is exactly 2 entries at every tier - the
  # mod's own scripts with imagerect scaled and area= untouched.
  # RegionCensusUI (2026-08-30): null-45's mod-only census dialog - ONE script,
  # no art, so exactly 1 entry at every tier.
  @{ rel = "zzz-SC4UIScale\z_SC4UIScale_RegionCensusUI"; tag = "2x";  entries = 1 },
  @{ rel = "zzz-SC4UIScale\z_SC4UIScale_RegionCensusUI"; tag = "15x"; entries = 1 },
  @{ rel = "zzz-SC4UIScale\z_SC4UIScale_RegionCensusUI"; tag = "3x";  entries = 1 },
  @{ rel = "zzz-SC4UIScale\z_SC4UIScale_RaiseUI"; tag = "2x";  entries = 2 },
  @{ rel = "zzz-SC4UIScale\z_SC4UIScale_RaiseUI"; tag = "15x"; entries = 2 },
  @{ rel = "zzz-SC4UIScale\z_SC4UIScale_RaiseUI"; tag = "3x";  entries = 2 },
  @{ rel = "zzz-SC4UIScale\z_SC4UIScale_CsiIcons"; tag = "2x";  entries = 16 },
  @{ rel = "zzz-SC4UIScale\z_SC4UIScale_CsiIcons"; tag = "15x"; entries = 16 },
  @{ rel = "zzz-SC4UIScale\z_SC4UIScale_CsiIcons"; tag = "3x";  entries = 16 },
  @{ rel = "010-SC4UIScale\z_SC4UIScale_SelectiveArt"; tag = "15x"; entries = 696 },
  @{ rel = "010-SC4UIScale\z_SC4UIScale_DialogStatic"; tag = "15x"; entries = 266 }, # #178: see the 2x row note (2026-08-16)
  @{ rel = "010-SC4UIScale\z_SC4UIScale_SelectiveArt"; tag = "3x";  entries = 696 },   # #136: was 651; #190: was 655
  @{ rel = "010-SC4UIScale\z_SC4UIScale_DialogStatic"; tag = "3x";  entries = 266 }, # #178: see the 2x row note (2026-08-16)
  # SelectorUI (2026-08-19): the scale selector at the STOCK tier. ONE
  # entry by design - Graphic Options and nothing else. If this count ever
  # moves, the stock tier has started shipping scaled art, which is the
  # one thing this package must never do.
  # THE TAG IS THE INTERESTING PART. This is the ONE package armed by the
  # ABSENCE of a tier, and the two halves of the project disagree about what
  # its payload is called - see the PAYLOAD TAG COVERAGE gate below, which is
  # where that disagreement is measured rather than assumed. The row here
  # resolves through both candidate names so this existence check cannot fail
  # for the naming reason instead of the missing-file reason.
  @{ rel = "zzz-SC4UIScale\z_SC4UIScale_SelectorUI"; tag = "1x"; tagAlt = "on"; entries = 1 },
  # TIER MATH PASS (2026-07-29, v2.24.0): ItemIcons + ItemIconsSub now exist at
  # every tier (audit finding A1 - they were 2x only, so ALL ~266+130 menu
  # icons silently reverted to 1x in scaled cells at 1.5x/3x). Built by
  # tools\itemicons\stage_icons.py --factor / build_itemicons_sub.py --factor;
  # the Sub builder verifies its name set against the shipped 2x pack-sub, so
  # counts are 266/130 at every tier by construction. ScaleTier.cpp already
  # synced these bases for all four package tags - the packages were the gap.
  @{ rel = "010-SC4UIScale\z_SC4UIScale_ItemIcons";    tag = "15x"; entries = 356 },
  @{ rel = "010-SC4UIScale\z_SC4UIScale_ItemIcons";    tag = "3x";  entries = 356 },
  @{ rel = "zzz-SC4UIScale\z_SC4UIScale_ItemIconsSub"; tag = "15x"; entries = 130 },
  @{ rel = "zzz-SC4UIScale\z_SC4UIScale_ItemIconsSub"; tag = "3x";  entries = 130 },
  # UNCOVERED THIRD-PARTY ITEM ICONS (#149, 2026-08-15). Icons a custom LOT
  # ships that no package of ours covered.
  # NO FIXED ENTRY COUNT FOR UncoveredIcons - IT IS NOT A CONSTANT.
  # This package holds however many uncovered icons THIS install has, so the
  # count changes the moment the player adds a lot. Asserting "2" would turn
  # a correct rebuild into a red gate and train us to ignore it. The property
  # that actually matters - deployed == what the builder produced - is
  # asserted by the built-vs-deployed comparison further down, which is exact
  # and count-independent.
  # THIRD-PARTY .UI OVERRIDE #2 (task #79c, 2026-07-31): the cyclone-boom
  # save-warning mod REPLACES both in-city quit/exit confirm scripts
  # ({0,96A006B0,6A553AA4} and {0,96A006B0,0A55161D}) from 150-mods\, so by the
  # same LOAD-ORDER LAW our root DialogStatic copies never won and those two
  # dialogs opened at stock 1x - which we misdiagnosed for five days as "the
  # game bypasses the DBPF override". The live +1px height (270x162 vs the
  # stock 270x161) is what finally identified the owner.
  # 2 entries = the two scripts, built from the MOD's versions so its
  # "Option Disabled" button survives. NO art: {46a006b0,144161e4/eb} are
  # already 2x in place in the root DialogStatic package and the mod does not
  # override them.
  # ScaleTier GATES this package on the mod still being installed and
  # unchanged (2408 bytes). v4.5.0: A GATE VERDICT IS NO LONGER VISIBLE IN THE
  # FILENAME - a gated-off package is a live `.dat` holding `.off` content,
  # under the same name as an armed one. So a "NOT FOUND" here now means the
  # PAYLOAD is missing (a packaging defect), and the gate verdict is read from
  # STATE.txt in the DEPENDENCY-GATE VERDICT section instead.
  @{ rel = "zzz-SC4UIScale\z_SC4UIScale_SaveWarningUI"; tag = "2x";  entries = 2 },
  @{ rel = "zzz-SC4UIScale\z_SC4UIScale_SaveWarningUI"; tag = "15x"; entries = 2 },
  @{ rel = "zzz-SC4UIScale\z_SC4UIScale_SaveWarningUI"; tag = "3x";  entries = 2 },
  # THIRD-PARTY .UI OVERRIDE #3 (v2.38.3): CAM replaces NINE stock .UI scripts,
  # and SIX of them are dialog-static TARGETS - so we were shipping doubled
  # copies of scripts the game never loads. Found by
  # tools\uiscripts\winning_corpus.py, which resolves the real load-order
  # winner per TGI; the builder now ASSERTS that a target's winning script is
  # the one it read. Shapes measured: the generic one-button popup is 500x175
  # in CAM vs stock 300x166 (wrong SHAPE, not merely shadowed), the startup
  # splash gains two text lines, and four building-query panels differ by up to
  # 21 -> 45 nodes.
  # 10 entries = the six scripts + FOUR of CAM's own bitmaps. The art is not
  # optional: the splash root is blttype=tiled, so a 1536x1200 root over CAM's
  # 768x600 background TILED IT 2x2 (reported live, v2.38.3 -> fixed v2.38.4).
  # Every image= ref across the six scripts was then audited against the stock
  # PNG store in one pass, which found all four at once. Gated by ScaleTier
  # on BOTH CAM_Extended_Essentials.dat and CAM_Intro.dat (the six come from
  # two of CAM's dats; a half-present set would be half stale).
  # 10 -> 22 in v2.97.0 (#154): the THREE CAM-ONLY dialogs joined the set -
  # the city info screen {96a006b0,9b868f68} (the Village Hall / Town Hall
  # query) plus the civic and school query panels 12121201 / 12121205 - and
  # the info screen brought NINE of CAM's own bitmaps with it (9 scripts +
  # 13 art = 22). They are not overrides of any stock script, so they have no
  # stock twin to fall back to, and that is exactly why they hid: every check
  # in the builder asked "has a mod taken over one of OUR targets?", never
  # "is a mod's OWN dialog scaled?"
  @{ rel = "zzz-SC4UIScale\z_SC4UIScale_CamUI"; tag = "2x";  entries = 22 },
  @{ rel = "zzz-SC4UIScale\z_SC4UIScale_CamUI"; tag = "15x"; entries = 22 },
  @{ rel = "zzz-SC4UIScale\z_SC4UIScale_CamUI"; tag = "3x";  entries = 22 },
  # ALWAYS-ON (untagged): LTEXT overrides matching WebRedirect. ScaleTier.cpp
  # DOES SyncDat this one (inverse gate on the Web Button Improvement Mod),
  # with tag L"" -> payload tag "on"; build_payloads.py classifies it
  # TIER-INDEPENDENT and invents no payload. That disagreement is measured by
  # the PAYLOAD TAG COVERAGE gate, not assumed here - the row itself only
  # asserts the file exists and holds 3 entries.
  @{ rel = "010-SC4UIScale\z_SC4UIScale_WebText"; tag = "on"; entries = 3 },
  # ---- ZCarbon* (v4.3.0, 2026-08-25): Scoty Carbon Skin adaptations ----
  # Carbon-sourced scaled twins, gated on the skin's dats at exact sizes.
  # Z-late names are load-bearing (REGRESSION.md "zzz-INTERNAL SORT TRAP").
  # ZCarbonUI: 109 carbon scripts + 87 enrolled art + 1 carbon-styled clone.
  @{ rel = "zzz-SC4UIScale\z_SC4UIScale_ZCarbonUI"; tag = "2x";  entries = 197 },
  @{ rel = "zzz-SC4UIScale\z_SC4UIScale_ZCarbonUI"; tag = "15x"; entries = 197 },
  @{ rel = "zzz-SC4UIScale\z_SC4UIScale_ZCarbonUI"; tag = "3x";  entries = 197 },
  # ZCarbonCamUI: carbon's 7 CAM-dialog redeclarations + 3 CAM sheets.
  @{ rel = "zzz-SC4UIScale\z_SC4UIScale_ZCarbonCamUI"; tag = "2x";  entries = 10 },
  @{ rel = "zzz-SC4UIScale\z_SC4UIScale_ZCarbonCamUI"; tag = "15x"; entries = 10 },
  @{ rel = "zzz-SC4UIScale\z_SC4UIScale_ZCarbonCamUI"; tag = "3x";  entries = 10 },
  # ZCarbonSaveWarning: carbon's two confirm-dialog scripts (art rides ZCarbonUI).
  @{ rel = "zzz-SC4UIScale\z_SC4UIScale_ZCarbonSaveWarning"; tag = "2x";  entries = 2 },
  @{ rel = "zzz-SC4UIScale\z_SC4UIScale_ZCarbonSaveWarning"; tag = "15x"; entries = 2 },
  @{ rel = "zzz-SC4UIScale\z_SC4UIScale_ZCarbonSaveWarning"; tag = "3x";  entries = 2 },
  # ZCarbonIcons: 8 CSI balloons x BOTH twin groups + 2 item strips.
  @{ rel = "zzz-SC4UIScale\z_SC4UIScale_ZCarbonIcons"; tag = "2x";  entries = 18 },
  @{ rel = "zzz-SC4UIScale\z_SC4UIScale_ZCarbonIcons"; tag = "15x"; entries = 18 },
  @{ rel = "zzz-SC4UIScale\z_SC4UIScale_ZCarbonIcons"; tag = "3x";  entries = 18 },
  # ZCarbonNam / ZCarbonStyles: 1 script + 1 art each.
  @{ rel = "zzz-SC4UIScale\z_SC4UIScale_ZCarbonNam"; tag = "2x";  entries = 2 },
  @{ rel = "zzz-SC4UIScale\z_SC4UIScale_ZCarbonNam"; tag = "15x"; entries = 2 },
  @{ rel = "zzz-SC4UIScale\z_SC4UIScale_ZCarbonNam"; tag = "3x";  entries = 2 },
  # Styles = 1 script + 1 art + 2 carbon-styled CLONE sheets (the clone pass
  # was a false zero until 2026-08-25; see REGRESSION.md).
  @{ rel = "zzz-SC4UIScale\z_SC4UIScale_ZCarbonStyles"; tag = "2x";  entries = 4 },
  @{ rel = "zzz-SC4UIScale\z_SC4UIScale_ZCarbonStyles"; tag = "15x"; entries = 4 },
  @{ rel = "zzz-SC4UIScale\z_SC4UIScale_ZCarbonStyles"; tag = "3x";  entries = 4 },
  # ZCarbonArt / ZCarbonGodMod entry counts land with the final build
  # (rows added in the same session - see the deploy manifest).
  # Art = 23 scripts + 246 art + 11 carbon-styled CLONE sheets.
  @{ rel = "zzz-SC4UIScale\z_SC4UIScale_ZCarbonArt"; tag = "2x";  entries = 280 },
  @{ rel = "zzz-SC4UIScale\z_SC4UIScale_ZCarbonArt"; tag = "15x"; entries = 280 },
  @{ rel = "zzz-SC4UIScale\z_SC4UIScale_ZCarbonArt"; tag = "3x";  entries = 280 },
  @{ rel = "zzz-SC4UIScale\z_SC4UIScale_ZCarbonGodMod"; tag = "2x";  entries = 4 },
  @{ rel = "zzz-SC4UIScale\z_SC4UIScale_ZCarbonGodMod"; tag = "15x"; entries = 4 },
  @{ rel = "zzz-SC4UIScale\z_SC4UIScale_ZCarbonGodMod"; tag = "3x";  entries = 4 }
)
# Font package sources must exist beside the DLL. NOT renamed by anything -
# SyncFont copies a tier's table ONTO the live FontStyle.ini, so these three
# are ordinary files under both layouts.
$FONT_SOURCES = @("010-SC4UIScale\FontStyle-2x.ini", "010-SC4UIScale\FontStyle-15x.ini", "010-SC4UIScale\FontStyle-3x.ini")

# ZCarbon* ARE ABSENT BY DESIGN ON A NORMAL INSTALL (2026-08-25). They are
# built from another author's skin on the player's own machine, so the
# release bundle ships none (Build-Dist asserts that) and a cold clone has
# none either. Gating on the built artifact - not on the deployed one -
# keeps "you never built them" separate from "they are deployed and wrong":
# once they exist in the repo, every row below is enforced exactly as before.
$carbonBuilt = Test-Path (Join-Path $proj "tools\selective-safe\z_SC4UIScale_ZCarbonArt.dat")
if (-not $carbonBuilt) {
  Write-Host "  note: no carbon packages built on this machine - ZCarbon rows skipped (they are local-only by design; see CARBON-COMPAT.md)."
}

# Base -> expected entry count, harvested from the rows above. Used by the LIVE
# FILE check further down: the count is the same at every tier by construction
# for every package here, so one number per base is enough to assert that the
# stable `.dat` the game actually opens holds a whole package rather than a
# truncated or half-copied one.
$EXPECTED_BY_BASE = @{}

$nExamined = 0
foreach ($e in $EXPECTED) {
  if (-not $carbonBuilt -and $e.rel -match 'ZCarbon') { continue }
  $leaf = Split-Path $e.rel -Leaf
  if (-not $EXPECTED_BY_BASE.ContainsKey($leaf)) { $EXPECTED_BY_BASE[$leaf] = $e.entries }
  if ($e.tag -eq 'plain') {
    # Never armed, never a payload: one plain file, same in both layouts.
    $hit = $null
    $pp = Resolve-LiveFile $e.rel
    if ($pp) { $hit = @{ Path = $pp; Layout = 'plain'; Live = $true } }
  } else {
    $hit = Resolve-PkgFile $e.rel $e.tag
    if (-not $hit -and $e.tagAlt) { $hit = Resolve-PkgFile $e.rel $e.tagAlt }
  }
  if (-not $hit) {
    $failures += ($e.rel + " [" + $e.tag + "]: NOT FOUND under EITHER layout (looked for " +
      "<base>." + $e.tag + ".uipay, <base>-" + $e.tag + ".dat and its .x1-disabled twin)")
    continue
  }
  $list = & $packer --list $hit.Path 2>$null
  $n = ($list | Where-Object { $_ -match "^0x[0-9A-Fa-f]{8} 0x[0-9A-Fa-f]{8} 0x[0-9A-Fa-f]{8} " }).Count
  $nExamined++
  if ($n -ne $e.entries) {
    $failures += ($e.rel + " [" + $e.tag + "] (" + (Split-Path $hit.Path -Leaf) + "): $n entries, expected $($e.entries)")
  }
}
# NULL IS NOT EVIDENCE. If the resolver matched nothing, every count above was
# skipped and "no count was wrong" would be a statement about zero measurements.
if ($nExamined -eq 0) {
  $failures += ("entry-count pass examined ZERO packages - every row failed to " +
    "resolve under either layout. That is a refusal, not a pass: the naming " +
    "scheme changed under this suite, or the Plugins path is wrong.")
}

foreach ($f in $FONT_SOURCES) {
  if (-not (Test-Path (Join-Path $plugins $f))) { $failures += ("missing font source " + $f) }
}

# SC4UIScale.dll must be present.
if (-not (Test-Path "$plugins\SC4UIScale.dll")) {
  $failures += "missing $plugins\SC4UIScale.dll"
}
# MENUFIX: REPORTED, NOT GATED (2026-08-18).
# Deploy-OnGameClose deliberately does not copy it - it rewrites CAM's GAMEPLAY
# submenu data rather than scaling any UI, so shipping it is a decision about a
# third-party mod's content, and it is slated to be dropped. This suite used to
# assert the deployed copy matched tools\itemicons\_work\, which is a promise
# the deploy never makes; it passed for months only because the live file was
# hand-placed once and never regenerated, and it went red the first time the
# builder produced different bytes. Deploy-OnGameClose.ps1 predicted that
# failure in writing. Asserting it back would restore passing-by-luck.
# It is REPORTED because a hand-placed file in the tree we deploy into is our
# business, and because it is live input to the #146 provenance audit.
$menuFix = "$plugins\zzz-SC4UIScale\z_SC4UIScale_MenuFix.dat"
if (Test-Path $menuFix) {
  $mfDate = (Get-Item $menuFix).LastWriteTime.ToString("yyyy-MM-dd")
  Write-Host ("  note: a HAND-PLACED z_SC4UIScale_MenuFix.dat is live in " +
    "Plugins (dated $mfDate). This deploy does not manage it and this suite " +
    "does not gate it. It rewrites CAM's gameplay submenu data - see #146.")
}
# Any OTHER gzcom plugin in the same folder is a live variable in a UI-scaling
# observation: it can add windows, replace art, or hook the same engine calls.
# Discovered rather than listed - a written-down inventory of "mods to watch
# for" is wrong the first time somebody installs one that is not on it.
$others = @(Get-ChildItem $plugins -Filter *.dll -File -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -ne "SC4UIScale.dll" })
if ($others.Count) {
  Write-Host ("  note: " + $others.Count + " other plugin DLL(s) load from this " +
    "folder (" + (($others | ForEach-Object { $_.Name }) -join ", ") + "). Any of " +
    "them can affect a UI-scaling result; rule them out before blaming this mod.")
}
# ---------------------------------------------------------------------------
# ROOT GATE (v4.4.0; amended v4.5.0 for the ini move).
#
# EXACTLY TWO FILES OF OURS MAY SIT AT THE PLUGINS ROOT:
#
#   SC4UIScale.dll  - the game loads DLLs from the top level and nowhere else
#                     (measured on the v4.2.0 maiden boot: a DLL in a subfolder
#                     produces no log and no director). That matches every one
#                     of the 30 sc4pac DLL packages in a typical tree.
#   SC4UIScale.ini  - MOVED HERE v4.5.0, measured against sc4pac 0.10.0 with a
#                     throwaway channel, not inferred:
#                       * inside the package folder it is DESTROYED by every
#                         package UPDATE - sc4pac deletes
#                         <group>.<name>.<oldver>.sc4pac wholesale and creates a
#                         new versioned folder, so the player's tier choice
#                         would not survive one version bump;
#                       * shipping it with isIni:true is worse - it lands at the
#                         root RENAMED to <stem>_sc4pacnew.ini, is never
#                         activated, and is deleted on uninstall even after the
#                         user has edited it;
#                       * a ROOT ini came through a measured v1->v2 update
#                         BYTE-IDENTICAL while the versioned folder was wiped.
#                     So the bundle ships NO ini at all: the DLL creates it at
#                     the root on first run, and reverse-migrates a v4.4.0 ini
#                     out of the folder carrying the user's settings. It is
#                     therefore a RUNTIME PRODUCT, which is also why it has no
#                     $EXPECTED or $BUILT_PAIRS row - _packaging\SC4UIScale.ini
#                     is now a DEFAULTS REFERENCE only, never a shipped file.
#
# ANY OTHER file of ours at the root is RED, not a note. Through 4.3.1 the log,
# gcap and #104 csv were resolved beside the DLL and piled up here; this gate is
# what stops that coming back by accident, because a stray root file is exactly
# the kind of thing that passes unnoticed for months. Matched by PREFIX, not by
# a written-down list: an inventory of names is wrong the first time a new one
# appears. The exception is on the EXACT name `SC4UIScale.ini`, so
# SC4UIScale.log, SC4UIScale.gcap and any future SC4UIScaleAnything.ini all stay
# red.
#
# v4.5.0 NOTE, DELIBERATELY EXPLICIT (this gate now has a new way to fire).
# WriteArmState writes `z_SC4UIScale_STATE.txt` into each folder it armed
# packages in, and CommitArming derives those folders from the SyncDat call
# sites - today `OurPackagesDir()` (010-SC4UIScale\) and `PluginsRoot()` +
# "zzz-SC4UIScale\", both of which are subfolders. So no state file lands at the
# root and this gate is quiet. BUT the `zzz-SC4UIScale\...` bases are resolved
# via `ResolveOurRelative`, and IF that ever falls back to the bare PluginsRoot
# for a package - or a new SyncDat call site passes pluginsRoot with an
# unprefixed base - then WriteArmState WILL drop z_SC4UIScale_STATE.txt AT THE
# ROOT and this gate will go red naming it. THAT IS THE CORRECT OUTCOME, not a
# false positive: a state file at the root means a PACKAGE is being armed at the
# root, and a package at the root can never override a subfolder dat (the LOAD
# ORDER LAW). Fix the resolution; do not exempt the filename.
# ---------------------------------------------------------------------------
$ROOT_ALLOWED = @("SC4UIScale.dll", "SC4UIScale.ini")
$legacyRoot = @(Get-ChildItem $plugins -File -ErrorAction SilentlyContinue |
  Where-Object { $ROOT_ALLOWED -notcontains $_.Name -and (
                 $_.Name -like "SC4UIScale*" -or
                 $_.Name -like "z_SC4UIScale_*" -or
                 $_.Name -like "FontStyle-*.ini" -or
                 $_.Name -eq "FontStyle.ini.user-original" -or
                 $_.Name -eq ".sc4uiscale-tier1-restore.txt") })
foreach ($lf in $legacyRoot) {
  $extra = ""
  if ($lf.Name -eq "z_SC4UIScale_STATE.txt") {
    $extra = " THIS ONE IS SPECIFIC: WriteArmState only writes into folders " +
             "CommitArming armed packages in, so a STATE file here means a " +
             "PACKAGE is being armed at the Plugins root - where it can never " +
             "beat a subfolder dat. Fix ResolveOurRelative / the SyncDat dir; " +
             "do not delete the file."
  }
  $failures += ("OUR FILE AT THE PLUGINS ROOT: " + $lf.Name +
    " - only SC4UIScale.dll and SC4UIScale.ini belong there (run " +
    "_tests\Deploy-OnGameClose.ps1; its root-cleanup block moves or removes " +
    "these)." + $extra)
}

# ===========================================================================
# NEW RED GATE (v4.5.0): NO PACKAGE MAY EXIST UNDER BOTH LAYOUTS.
#
# THE DAMAGE. `z_SC4UIScale_X.dat` and `z_SC4UIScale_X-2x.dat` in the same
# folder are TWO LIVE PROVIDERS of every TGI that package owns. Both enter the
# plugin scan, both register segments, and the winner is decided by scan order
# inside one directory - which nothing in this project controls or measures.
# The result renders SILENTLY WRONG: no crash, no log line, identical file
# counts either way. Convert-ToPayloadLayout.ps1 names this exact shape as the
# reason it exists as ONE converter called by both Deploy and Build-Dist rather
# than as edited copy lines in each.
#
# WHY IT BELONGS *HERE* AND NOWHERE ELSE. That converter refuses to leave a
# mixture behind in the tree IT converted, which covers a bundle it built. It
# cannot cover a REAL INSTALL, where the mixture arrives by a different road:
# an old deploy writing tier-tagged files into a folder the DLL already
# migrated, an sc4pac update restoring shipped names beside migrated ones, or a
# user unzipping a 4.4.0 bundle over a 4.5.0 install. This suite is the only
# thing that runs against that tree.
#
# GOES RED WHEN: any package base has BOTH a live untagged `<base>.dat` AND a
# live bare `<base>-<tag>.dat`; or a `.uipay` payload sits beside a live
# tier-tagged twin. `.x1-disabled` files are NOT live and do not count - that
# stash beside a stable file is the v4.0.3 pilot's normal state, and flagging it
# would be the gate crying wolf on a correct install.
# ===========================================================================
$nOverlapChecked = 0
foreach ($d in $OUR_DIRS) {
  if (-not (Test-Path $d)) { continue }
  $liveDats = @(Get-ChildItem $d -File -Filter 'z_SC4UIScale_*.dat' -ErrorAction SilentlyContinue)
  $stableNames = @{}
  foreach ($f in $liveDats) {
    if ($f.BaseName -notmatch '-(15x|2x|3x|4x|1x)$') { $stableNames[$f.BaseName] = $f.Name }
  }
  foreach ($f in $liveDats) {
    if ($f.BaseName -match '^(?<b>.+)-(?<t>15x|2x|3x|4x|1x)$') {
      $nOverlapChecked++
      $b = $matches['b']
      if ($stableNames.ContainsKey($b)) {
        $failures += ("BOTH LAYOUTS LIVE for " + $b + " in " + (Split-Path $d -Leaf) +
          ": " + $stableNames[$b] + " AND " + $f.Name + " are both loadable .dat " +
          "files. That is TWO LIVE PROVIDERS for every TGI this package owns; the " +
          "winner is scan order and the screen is silently wrong with no log line " +
          "and no count change. Delete the tier-tagged one (the stable name is the " +
          "v4.5.0 target) or finish the migration with " +
          "_tests\Convert-ToPayloadLayout.ps1.")
      }
    }
  }
  # The other half of the same hazard, and the one the payload layout can
  # create: a payload whose tier-tagged source was never removed. `.uipay` is
  # inert by extension (probe #202), so the tagged .dat is the live one and the
  # DLL is arming from a file the game is ALSO loading directly.
  foreach ($p in @(Get-ChildItem $d -File -Filter 'z_SC4UIScale_*.uipay' -ErrorAction SilentlyContinue)) {
    $nOverlapChecked++
    if ($p.BaseName -match '^(?<b>.+)\.(?<t>15x|2x|3x|4x|1x|on|off)$') {
      $twin = Join-Path $d ($matches['b'] + "-" + $matches['t'] + ".dat")
      if (Test-Path $twin) {
        $failures += ("BOTH LAYOUTS for " + $matches['b'] + " in " + (Split-Path $d -Leaf) +
          ": payload " + $p.Name + " coexists with the live tier-tagged " +
          (Split-Path $twin -Leaf) + ". The migration half-ran - the tier file is " +
          "still being loaded by the game while the DLL arms the stable name from " +
          "the payload, so that package has two live providers.")
      }
    }
  }
}
if ($nOverlapChecked -eq 0 -and $nOurFiles -gt 0) {
  # Cannot happen with files present unless the naming assumptions are wrong,
  # and a scan that examined nothing must never read as a clean scan.
  $failures += ("BOTH-LAYOUTS gate examined ZERO candidate files while " +
    $nOurFiles + " of our files exist - the name patterns it matches on no " +
    "longer describe what is on disk, so it proved nothing.")
}

# DEPLOYED == BUILT (task #58 root cause, 2026-08-02). The ThirdPartyUI
# package was absent from Deploy-OnGameClose.ps1, so its deployed copy froze
# at the 2026-07-29 build epoch; when the art classification later changed,
# the frozen script kept clone refs (470261e8/47026240) that no longer
# shipped anywhere = the grey radio rows. Entry COUNTS and byte SIZES were
# both identical between stale and fresh (the rewrite swaps equal-length hex
# strings), so only a content hash catches this class. Every package with a
# canonical build output is asserted here; add a row whenever a new package
# is added to the deploy script.
#
# v4.5.0: THE DEPLOYED SIDE NOW POINTS AT THE PAYLOAD, NOT THE LIVE .dat -
# AND THAT IS AN IMPROVEMENT, not a translation.
# The live `z_SC4UIScale_<Pkg>.dat` is REWRITTEN BY THE DLL at every boot
# (ArmOne copies a payload onto it). Hashing it against a build output would be
# racing the arming pass: equal only while the armed tier happens to be the tier
# the row names, and unequal - loudly, wrongly - the moment the player is on any
# other tier, or the package is gated off and the live file holds `.off`
# content. The PAYLOAD is never written by the DLL, ever, at any tier, under any
# gate verdict. So `deployed == built` becomes an EXACT, tier-independent,
# gate-independent identity instead of a conditional one, and #58's actual
# question - "is this package frozen at a stale build epoch?" - is answered for
# ALL THREE TIERS AT ONCE rather than only for whichever one is armed.
# Under the rename layout the resolver falls back to the tier-tagged file, which
# is the same bytes, so one row shape works on both.
#   rel/tag = a package payload;  file = a literal deployed path (DLL, fonts).
$BUILT_PAIRS = @(
  @{ b = "build\Release\SC4UIScale.dll";                              file = "SC4UIScale.dll" }
  @{ b = "tools\selective-safe\z_SC4UIScale_SelectiveArt.dat";        rel = "010-SC4UIScale\z_SC4UIScale_SelectiveArt"; tag = "2x" }
  @{ b = "tools\packages\15x\z_SC4UIScale_SelectiveArt-15x.dat";      rel = "010-SC4UIScale\z_SC4UIScale_SelectiveArt"; tag = "15x" }
  @{ b = "tools\packages\3x\z_SC4UIScale_SelectiveArt-3x.dat";        rel = "010-SC4UIScale\z_SC4UIScale_SelectiveArt"; tag = "3x" }
  @{ b = "tools\dialog-static\z_SC4UIScale_DialogStatic.dat";         rel = "010-SC4UIScale\z_SC4UIScale_DialogStatic"; tag = "2x" }
  @{ b = "tools\packages\15x\z_SC4UIScale_DialogStatic-15x.dat";      rel = "010-SC4UIScale\z_SC4UIScale_DialogStatic"; tag = "15x" }
  @{ b = "tools\packages\3x\z_SC4UIScale_DialogStatic-3x.dat";        rel = "010-SC4UIScale\z_SC4UIScale_DialogStatic"; tag = "3x" }
  # SelectorUI: the inverse-gated package. Its payload tag is the one place the
  # two halves of the project disagree (ScaleTier.cpp asks ArmOne for `1x`,
  # build_payloads.py emits `on`), so the row carries BOTH candidate names and
  # the disagreement itself is gated separately below. Resolving either here
  # keeps THIS row measuring what it is for - stale bytes - instead of failing
  # for the naming reason.
  @{ b = "tools\packages\1x\z_SC4UIScale_SelectorUI-1x.dat";          rel = "zzz-SC4UIScale\z_SC4UIScale_SelectorUI"; tag = "1x"; tagAlt = "on" }
  @{ b = "tools\dialog-static\z_SC4UIScale_SaveWarningUI.dat";        rel = "zzz-SC4UIScale\z_SC4UIScale_SaveWarningUI"; tag = "2x" }
  @{ b = "tools\packages\15x\z_SC4UIScale_SaveWarningUI-15x.dat";     rel = "zzz-SC4UIScale\z_SC4UIScale_SaveWarningUI"; tag = "15x" }
  @{ b = "tools\packages\3x\z_SC4UIScale_SaveWarningUI-3x.dat";       rel = "zzz-SC4UIScale\z_SC4UIScale_SaveWarningUI"; tag = "3x" }
  @{ b = "tools\dialog-static\z_SC4UIScale_CamUI.dat";                rel = "zzz-SC4UIScale\z_SC4UIScale_CamUI"; tag = "2x" }
  @{ b = "tools\packages\15x\z_SC4UIScale_CamUI-15x.dat";             rel = "zzz-SC4UIScale\z_SC4UIScale_CamUI"; tag = "15x" }
  @{ b = "tools\packages\3x\z_SC4UIScale_CamUI-3x.dat";               rel = "zzz-SC4UIScale\z_SC4UIScale_CamUI"; tag = "3x" }
  @{ b = "tools\selective-safe\z_SC4UIScale_ThirdPartyUI.dat";        rel = "zzz-SC4UIScale\z_SC4UIScale_ThirdPartyUI"; tag = "2x" }
  @{ b = "tools\packages\15x\z_SC4UIScale_ThirdPartyUI-15x.dat";      rel = "zzz-SC4UIScale\z_SC4UIScale_ThirdPartyUI"; tag = "15x" }
  @{ b = "tools\packages\3x\z_SC4UIScale_ThirdPartyUI-3x.dat";        rel = "zzz-SC4UIScale\z_SC4UIScale_ThirdPartyUI"; tag = "3x" }
  @{ b = "tools\selective-safe\z_SC4UIScale_WarriorUI.dat";           rel = "zzz-SC4UIScale\z_SC4UIScale_WarriorUI"; tag = "2x" }
  @{ b = "tools\packages\15x\z_SC4UIScale_WarriorUI-15x.dat";         rel = "zzz-SC4UIScale\z_SC4UIScale_WarriorUI"; tag = "15x" }
  @{ b = "tools\packages\3x\z_SC4UIScale_WarriorUI-3x.dat";           rel = "zzz-SC4UIScale\z_SC4UIScale_WarriorUI"; tag = "3x" }
  # NamIcons (task #139, 2026-08-05). Hand-placed on the day they were built
  # and therefore absent from BOTH manifests until Build-Dist noticed the
  # bundle was missing them - the #58 / #116 shape a third time. All three
  # tiers come out of tools\itemicons\out\.
  @{ b = "tools\itemicons\out\z_SC4UIScale_NamIcons-2x.dat";          rel = "zzz-SC4UIScale\z_SC4UIScale_NamIcons"; tag = "2x" }
  @{ b = "tools\itemicons\out\z_SC4UIScale_NamIcons-15x.dat";         rel = "zzz-SC4UIScale\z_SC4UIScale_NamIcons"; tag = "15x" }
  @{ b = "tools\itemicons\out\z_SC4UIScale_NamIcons-3x.dat";          rel = "zzz-SC4UIScale\z_SC4UIScale_NamIcons"; tag = "3x" }
  # WebButtonUI (2026-08-21): cyclone-boom Web Button Improvement Mod's web
  # button bitmap, gated on the mod's presence. All three tiers from
  # tools\itemicons\out\ (generator rebuild_webbutton.py).
  @{ b = "tools\itemicons\out\z_SC4UIScale_WebButtonUI-2x.dat";       rel = "zzz-SC4UIScale\z_SC4UIScale_WebButtonUI"; tag = "2x" }
  @{ b = "tools\itemicons\out\z_SC4UIScale_WebButtonUI-15x.dat";      rel = "zzz-SC4UIScale\z_SC4UIScale_WebButtonUI"; tag = "15x" }
  @{ b = "tools\itemicons\out\z_SC4UIScale_WebButtonUI-3x.dat";       rel = "zzz-SC4UIScale\z_SC4UIScale_WebButtonUI"; tag = "3x" }
  # CsiIcons (v4.5.2): hand-rescued in Build-Dist (parser blind spot) and
  # hand-copied in Deploy, but tracked by NEITHER manifest gate until the
  # 2026-08-30 audit - for the package that shipped the wrong tier twice
  # (#196). All three tiers from tools\packages\<tier>\.
  @{ b = "tools\dialog-static\z_SC4UIScale_RegionCensusUI.dat";       rel = "zzz-SC4UIScale\z_SC4UIScale_RegionCensusUI"; tag = "2x" }
  @{ b = "tools\packages\15x\z_SC4UIScale_RegionCensusUI-15x.dat";    rel = "zzz-SC4UIScale\z_SC4UIScale_RegionCensusUI"; tag = "15x" }
  @{ b = "tools\packages\3x\z_SC4UIScale_RegionCensusUI-3x.dat";      rel = "zzz-SC4UIScale\z_SC4UIScale_RegionCensusUI"; tag = "3x" }
  @{ b = "tools\selective-safe\z_SC4UIScale_RaiseUI.dat";             rel = "zzz-SC4UIScale\z_SC4UIScale_RaiseUI"; tag = "2x" }
  @{ b = "tools\packages\15x\z_SC4UIScale_RaiseUI-15x.dat";           rel = "zzz-SC4UIScale\z_SC4UIScale_RaiseUI"; tag = "15x" }
  @{ b = "tools\packages\3x\z_SC4UIScale_RaiseUI-3x.dat";             rel = "zzz-SC4UIScale\z_SC4UIScale_RaiseUI"; tag = "3x" }
  @{ b = "tools\packages\2x\z_SC4UIScale_CsiIcons-2x.dat";            rel = "zzz-SC4UIScale\z_SC4UIScale_CsiIcons"; tag = "2x" }
  @{ b = "tools\packages\15x\z_SC4UIScale_CsiIcons-15x.dat";          rel = "zzz-SC4UIScale\z_SC4UIScale_CsiIcons"; tag = "15x" }
  @{ b = "tools\packages\3x\z_SC4UIScale_CsiIcons-3x.dat";            rel = "zzz-SC4UIScale\z_SC4UIScale_CsiIcons"; tag = "3x" }
  # UncoveredIcons ROWS DELIBERATELY ABSENT FROM THIS LIST.
  # Unlike every other package here, this one only EXISTS when the player has
  # third-party icons we do not cover. On a clean install there is nothing to
  # build and nothing to deploy - a built-vs-deployed row would then fail on a
  # correct machine, which is how a gate teaches people to ignore it.
  # Its correctness is asserted where it can be: build_uncovered_icons.py
  # refuses to pack unless every strip measures zero drift and carries the
  # hover border, and tools\uimap\emu\sim_itemicon_states.py sweeps whatever
  # IS deployed across tier x icon x state.
  @{ b = "tools\itemicons\z_SC4UIScale_ItemIcons.dat";                rel = "010-SC4UIScale\z_SC4UIScale_ItemIcons"; tag = "2x" }
  @{ b = "tools\itemicons\_work\z_SC4UIScale_ItemIconsSub-2x.dat";    rel = "zzz-SC4UIScale\z_SC4UIScale_ItemIconsSub"; tag = "2x" }
  # WebText is TIER-INDEPENDENT: build_payloads.py invents no payload for it, so
  # the resolver falls through to the plain `.dat` under both layouts. That file
  # IS however a SyncDat target in ScaleTier.cpp (inverse gate on the web button
  # mod), which is the disagreement the PAYLOAD TAG COVERAGE gate reports - not
  # this row's business.
  @{ b = "tools\webtext\z_SC4UIScale_WebText.dat";                    rel = "010-SC4UIScale\z_SC4UIScale_WebText"; tag = "on" }
  # FONTS (#57 phase 4, 2026-08-02). Fonts were the ONE asset family with no
  # deployed-vs-built assertion - existence-checked only, a few lines above -
  # and that is precisely why they drifted unnoticed: the deployed 1.5x/3x
  # files were the raw .gen.ini side-outputs (62 styles, no HTML clone
  # styles) while the repo packages carried a stale ChartTickText. Same
  # lesson as #58, one family later.
  # 2x builds from tools\fonts\FontStyle.candidate.ini - there is no
  # tools\packages\2x\. Do NOT add a row for the live FontStyle.ini: the DLL
  # writes that at boot from the active tier's file (ScaleTier::SyncFont), so
  # it is a runtime product, not a deployed artifact - the same reason the live
  # `.dat` files and SC4UIScale.ini are not rows here.
  @{ b = "tools\fonts\FontStyle.candidate.ini";                       file = "010-SC4UIScale\FontStyle-2x.ini" }
  @{ b = "tools\packages\15x\FontStyle-15x.ini";                      file = "010-SC4UIScale\FontStyle-15x.ini" }
  @{ b = "tools\packages\3x\FontStyle-3x.ini";                        file = "010-SC4UIScale\FontStyle-3x.ini" }
  # ---- ZCarbon* (v4.3.0): carbon-sourced, gated, local-only (never in the
  # public bundle - Build-Dist asserts that). 2x untagged from the emitting
  # builder's dir, 15x/3x from tools\packages\<tag>\, same as their siblings.
  # NOTE the DbpfPack timestamp law (REGRESSION.md 2026-08-25): these hashes
  # match only because deploy COPIES the built file; any rebuild must be
  # redeployed before this suite runs.
  @{ b = "tools\dialog-static\z_SC4UIScale_ZCarbonUI.dat";            rel = "zzz-SC4UIScale\z_SC4UIScale_ZCarbonUI"; tag = "2x" }
  @{ b = "tools\packages\15x\z_SC4UIScale_ZCarbonUI-15x.dat";         rel = "zzz-SC4UIScale\z_SC4UIScale_ZCarbonUI"; tag = "15x" }
  @{ b = "tools\packages\3x\z_SC4UIScale_ZCarbonUI-3x.dat";           rel = "zzz-SC4UIScale\z_SC4UIScale_ZCarbonUI"; tag = "3x" }
  @{ b = "tools\dialog-static\z_SC4UIScale_ZCarbonCamUI.dat";         rel = "zzz-SC4UIScale\z_SC4UIScale_ZCarbonCamUI"; tag = "2x" }
  @{ b = "tools\packages\15x\z_SC4UIScale_ZCarbonCamUI-15x.dat";      rel = "zzz-SC4UIScale\z_SC4UIScale_ZCarbonCamUI"; tag = "15x" }
  @{ b = "tools\packages\3x\z_SC4UIScale_ZCarbonCamUI-3x.dat";        rel = "zzz-SC4UIScale\z_SC4UIScale_ZCarbonCamUI"; tag = "3x" }
  @{ b = "tools\dialog-static\z_SC4UIScale_ZCarbonSaveWarning.dat";   rel = "zzz-SC4UIScale\z_SC4UIScale_ZCarbonSaveWarning"; tag = "2x" }
  @{ b = "tools\packages\15x\z_SC4UIScale_ZCarbonSaveWarning-15x.dat"; rel = "zzz-SC4UIScale\z_SC4UIScale_ZCarbonSaveWarning"; tag = "15x" }
  @{ b = "tools\packages\3x\z_SC4UIScale_ZCarbonSaveWarning-3x.dat";  rel = "zzz-SC4UIScale\z_SC4UIScale_ZCarbonSaveWarning"; tag = "3x" }
  @{ b = "tools\selective-safe\z_SC4UIScale_ZCarbonArt.dat";          rel = "zzz-SC4UIScale\z_SC4UIScale_ZCarbonArt"; tag = "2x" }
  @{ b = "tools\packages\15x\z_SC4UIScale_ZCarbonArt-15x.dat";        rel = "zzz-SC4UIScale\z_SC4UIScale_ZCarbonArt"; tag = "15x" }
  @{ b = "tools\packages\3x\z_SC4UIScale_ZCarbonArt-3x.dat";          rel = "zzz-SC4UIScale\z_SC4UIScale_ZCarbonArt"; tag = "3x" }
  @{ b = "tools\selective-safe\z_SC4UIScale_ZCarbonNam.dat";          rel = "zzz-SC4UIScale\z_SC4UIScale_ZCarbonNam"; tag = "2x" }
  @{ b = "tools\packages\15x\z_SC4UIScale_ZCarbonNam-15x.dat";        rel = "zzz-SC4UIScale\z_SC4UIScale_ZCarbonNam"; tag = "15x" }
  @{ b = "tools\packages\3x\z_SC4UIScale_ZCarbonNam-3x.dat";          rel = "zzz-SC4UIScale\z_SC4UIScale_ZCarbonNam"; tag = "3x" }
  @{ b = "tools\selective-safe\z_SC4UIScale_ZCarbonStyles.dat";       rel = "zzz-SC4UIScale\z_SC4UIScale_ZCarbonStyles"; tag = "2x" }
  @{ b = "tools\packages\15x\z_SC4UIScale_ZCarbonStyles-15x.dat";     rel = "zzz-SC4UIScale\z_SC4UIScale_ZCarbonStyles"; tag = "15x" }
  @{ b = "tools\packages\3x\z_SC4UIScale_ZCarbonStyles-3x.dat";       rel = "zzz-SC4UIScale\z_SC4UIScale_ZCarbonStyles"; tag = "3x" }
  @{ b = "tools\selective-safe\z_SC4UIScale_ZCarbonGodMod.dat";       rel = "zzz-SC4UIScale\z_SC4UIScale_ZCarbonGodMod"; tag = "2x" }
  @{ b = "tools\packages\15x\z_SC4UIScale_ZCarbonGodMod-15x.dat";     rel = "zzz-SC4UIScale\z_SC4UIScale_ZCarbonGodMod"; tag = "15x" }
  @{ b = "tools\packages\3x\z_SC4UIScale_ZCarbonGodMod-3x.dat";       rel = "zzz-SC4UIScale\z_SC4UIScale_ZCarbonGodMod"; tag = "3x" }
  @{ b = "tools\research\carbon\z_SC4UIScale_ZCarbonIcons.dat";       rel = "zzz-SC4UIScale\z_SC4UIScale_ZCarbonIcons"; tag = "2x" }
  @{ b = "tools\packages\15x\z_SC4UIScale_ZCarbonIcons-15x.dat";      rel = "zzz-SC4UIScale\z_SC4UIScale_ZCarbonIcons"; tag = "15x" }
  @{ b = "tools\packages\3x\z_SC4UIScale_ZCarbonIcons-3x.dat";        rel = "zzz-SC4UIScale\z_SC4UIScale_ZCarbonIcons"; tag = "3x" }
)
$nHash = 0
$nHashRows = 0
foreach ($pair in $BUILT_PAIRS) {
  # Same carbon presence gate as $EXPECTED above: unbuilt carbon packages are
  # the normal state, and their build outputs are gitignored, so a cold clone
  # would otherwise fail on 24 "built artifact missing" rows before anyone had
  # done a single thing wrong.
  if (-not $carbonBuilt -and $pair.b -match 'ZCarbon') { continue }
  $nHashRows++
  $bp = Join-Path $proj $pair.b
  if ($pair.file) {
    $dp = Join-Path $plugins $pair.file
    $label = $pair.file
  } else {
    $hit = Resolve-PkgFile $pair.rel $pair.tag
    if (-not $hit -and $pair.tagAlt) { $hit = Resolve-PkgFile $pair.rel $pair.tagAlt }
    if ($hit) { $dp = $hit.Path } else { $dp = $null }
    $label = $pair.rel + " [" + $pair.tag + "]"
  }
  if (-not (Test-Path $bp)) { $failures += ("built artifact missing: " + $pair.b); continue }
  if (-not $dp -or -not (Test-Path $dp)) {
    $failures += ("deployed artifact missing under either layout: " + $label)
    continue
  }
  if ((Get-FileHash $bp -Algorithm SHA256).Hash -ne (Get-FileHash $dp -Algorithm SHA256).Hash) {
    $failures += ("DEPLOYED != BUILT: " + $label + " (" + (Split-Path $dp -Leaf) +
      ") does not match " + $pair.b + " - a rebuild was never deployed (run " +
      "Deploy-OnGameClose.ps1), or the deployed file was edited in place")
  } else { $nHash++ }
}
# NULL IS NOT EVIDENCE: rows that all skipped would print "0 hashes" and pass.
if ($nHashRows -gt 0 -and $nHash -eq 0) {
  $failures += ("deployed==built pass compared ZERO pairs out of " + $nHashRows +
    " eligible rows - every one failed to resolve. Refusal, not a pass.")
}

# ===========================================================================
# PAYLOAD TAG COVERAGE - DERIVED FROM ScaleTier.cpp, MEASURED ON DISK.
#
# WHAT BREAKS WITHOUT IT. ArmOne asks the filesystem for
# `<base>.<tag>.uipay`, where <tag> comes from PayloadTagOf(). If that exact
# file is absent it logs "MISSING PAYLOAD ... falling back to .off. This is a
# packaging defect; the package will be inert." - and then the package IS inert
# with a live, valid, parseable `.dat` sitting there. Nothing in a directory
# listing, an entry count, or a hash comparison can see that. The only visible
# consequence is on screen, at one tier, for one package.
#
# TWO INDEPENDENT INSTRUMENTS, which is the whole point (two blind instruments
# agreeing is one instrument):
#   what the DLL will ASK for  <- parsed out of src\ScaleTier.cpp's SyncDat call
#                                 sites plus the PayloadTagOf rule
#   what is ON DISK            <- the filesystem
# Neither is a hand-kept list, so neither can rot into agreement with the other.
#
# GOES RED WHEN: (a) the SyncDat parse yields zero call sites - the source shape
# changed and this gate proved nothing; (b) PayloadTagOf's rule text is no
# longer in ScaleTier.cpp, so the mapping this mirrors is not the mapping in
# force; (c) a package's `.off.uipay` is missing - reachable at the stock tier
# and whenever a dependency gate turns the package off, i.e. always; (d) a
# package's tier payload is missing under the exact name the DLL asks for.
# ===========================================================================
$scaleTierSrc = Get-Content (Join-Path $proj "src\ScaleTier.cpp") -Raw
$deploySrc    = Get-Content (Join-Path $proj "_tests\Deploy-OnGameClose.ps1") -Raw

# Mirrors ScaleTier.cpp's PayloadTagOf(): "-15x" -> "15x", "-1x" -> "1x",
# "" -> "on". Three lines of rule, hand-mirrored, so its SOURCE TEXT is
# asserted below rather than trusted.
function ConvertTo-PayloadTag {
  param([string]$CppTag)
  if ([string]::IsNullOrEmpty($CppTag)) { return "on" }
  if ($CppTag.StartsWith('-')) { return $CppTag.Substring(1) }
  return $CppTag
}
$payloadRuleOk = ($scaleTierSrc -match 'void\s+PayloadTagOf') -and
                 ($scaleTierSrc -match 'wcscpy_s\(out,\s*outLen,\s*L"on"\)') -and
                 ($scaleTierSrc -match "tag\[0\] == L'-' \? tag \+ 1 : tag")
if (-not $payloadRuleOk) {
  $failures += ("PayloadTagOf's rule text is no longer in ScaleTier.cpp in the " +
    "shape this suite mirrors (empty -> 'on', leading hyphen stripped). Every " +
    "payload-name assertion below would be checking the WRONG names, so they " +
    "are refused rather than run.")
}

# tools\payload\build_payloads.py owns which tiers a complete payload set must
# carry. Read it rather than restating it - a second copy of that tuple is a
# second authority (law 94).
$reqSrc = Get-Content (Join-Path $proj "tools\payload\build_payloads.py") -Raw
$reqMatch = [regex]::Match($reqSrc, 'REQUIRED_TIERS\s*=\s*\(([^)]*)\)')
$REQUIRED_TIERS = @()
if ($reqMatch.Success) {
  $REQUIRED_TIERS = @([regex]::Matches($reqMatch.Groups[1].Value, '"([^"]+)"') |
                      ForEach-Object { $_.Groups[1].Value })
}
if ($REQUIRED_TIERS.Count -eq 0) {
  $failures += ("could not read REQUIRED_TIERS out of tools\payload\build_payloads.py " +
    "- the payload-completeness gate has no tier list and was not run (refusal).")
}

# Parse the SyncDat call sites: (base, literal-tag-or-pkg.tag).
$syncSites = [regex]::Matches($scaleTierSrc,
  '(?s)SyncDat\(\s*\w+\s*,\s*L"([^"]*)"\s*,\s*(pkg\.tag|L"[^"]*")')
if ($syncSites.Count -eq 0) {
  $failures += ("parsed ZERO SyncDat call sites out of ScaleTier.cpp - the " +
    "payload-coverage gate could not see the package list it is built on, so " +
    "it proved nothing (NULL IS NOT EVIDENCE).")
}
$wantTags = @{}   # rel -> the payload tags the DLL can ask ArmOne for
foreach ($m in $syncSites) {
  $cppBase = $m.Groups[1].Value -replace '\\\\', '\'
  if ($cppBase -like '*\*') { $rel = $cppBase } else { $rel = "010-SC4UIScale\$cppBase" }
  $tagExpr = $m.Groups[2].Value
  $tags = @('off')   # ALWAYS reachable: the stock tier, or any dependency gate
  if ($tagExpr -eq 'pkg.tag') {
    $tags += $REQUIRED_TIERS
  } else {
    $tags += (ConvertTo-PayloadTag (($tagExpr -replace '^L"', '') -replace '"$', ''))
  }
  if ($wantTags.ContainsKey($rel)) { $wantTags[$rel] = @(($wantTags[$rel] + $tags) | Sort-Object -Unique) }
  else                             { $wantTags[$rel] = @($tags | Sort-Object -Unique) }
}
$nPayloadChecked = 0
if ($layout -eq 'RENAME') {
  Write-Host ("  note: payload tag coverage NOT CHECKED - this tree is on the " +
    "rename layout, where no .uipay exists to be complete or incomplete. It " +
    "becomes a live gate the moment the tree is converted. " +
    $wantTags.Count + " SyncDat-managed package(s) were identified in ScaleTier.cpp.")
} elseif ($payloadRuleOk -and $REQUIRED_TIERS.Count -gt 0) {
  foreach ($rel in ($wantTags.Keys | Sort-Object)) {
    if (-not $carbonBuilt -and $rel -match 'ZCarbon') { continue }
    $stem = Join-Path $plugins $rel
    $stemDir = Split-Path $stem -Parent
    if (-not (Test-Path $stemDir)) { continue }
    # Only judge packages this install actually carries. NOT INSTALLED means
    # no payloads AND no live file - UncoveredIcons on a clean machine, which
    # has nothing to build and nothing to deploy; inventing a red for it
    # teaches people to ignore reds.
    #
    # A LIVE .dat WITH NO PAYLOADS IS NOT THAT CASE, and skipping it on the
    # payload count alone was a silent pass: it is ArmOne's "NO PAYLOAD AT ALL
    # for %ls (not even .off). Leaving %ls.dat exactly as found" branch, where
    # the package permanently holds whatever bytes it was shipped with and
    # follows neither the tier nor its gate. Measured on the v4.5.0-dev bundle:
    # z_SC4UIScale_WebText is exactly this - SyncDat'd in ScaleTier.cpp with
    # tag L"" (payload tag "on") while build_payloads.py classifies it
    # TIER-INDEPENDENT and invents no payload for it.
    $anyPayload = @(Get-ChildItem $stemDir -File -Filter ((Split-Path $stem -Leaf) + '.*.uipay') -ErrorAction SilentlyContinue)
    if ($anyPayload.Count -eq 0 -and -not (Resolve-LiveFile $rel)) { continue }
    $nPayloadChecked++
    foreach ($t in $wantTags[$rel]) {
      if (-not (Test-Path "$stem.$t.uipay")) {
        $failures += ("MISSING PAYLOAD: " + $rel + "." + $t + ".uipay - ScaleTier.cpp " +
          "can ask ArmOne for tag '" + $t + "' on this package, and ArmOne's own log " +
          "line for that case reads 'MISSING PAYLOAD ... falling back to .off. This " +
          "is a packaging defect; the package will be inert.' The live file stays " +
          "valid and parseable while holding the wrong content, so nothing else in " +
          "this suite can see it.")
      }
    }
  }
  if ($nPayloadChecked -eq 0 -and $censusPayload.Count -gt 0) {
    $failures += ("payload tag coverage examined ZERO packages while " +
      $censusPayload.Count + " .uipay files exist on disk - the SyncDat parse and " +
      "the filesystem do not agree on where packages live, so this gate proved " +
      "nothing.")
  } elseif ($nPayloadChecked -gt 0) {
    Write-Host ("  payload tag coverage: " + $nPayloadChecked + " package(s) checked " +
      "against the tags ScaleTier.cpp can ask for.")
  }
}

# ===========================================================================
# DEPENDENCY-GATE LIST DRIFT (added 2026-08-19, same defect as below).
#
# Deploy-OnGameClose.ps1 now decides "is this package dependency-gated?" from an
# explicit $DEPENDENCY_GATED list instead of a filename pattern. The AUTHORITY
# for that answer is ScaleTier.cpp: a package is dependency-gated exactly when
# its SyncDat call is passed a DepOkByName(...) argument. A hand-kept copy of an
# authority rots (law 94), so compare the two and fail on drift IN EITHER
# DIRECTION - they fail differently and both matter:
#   in C++ but not the deploy -> deploy RE-ARMS a third-party package whose mod
#                                is absent (loud: Test-ThirdPartyGates goes red)
#   in the deploy but not C++ -> deploy REFUSES to arm a package that should be
#                                live, at every tier, with no output. Silent.
#                                That is exactly how CsiIcons shipped disarmed.
#
# THE EXTRACTION IS NO LONGER LAZY (fixed 2026-08-29). It used to be
# '(?s)\$DEPENDENCY_GATED\s*=\s*@\((.*?)\)' - lazy, so it stopped at the FIRST
# ')' inside the array. Deploy-OnGameClose.ps1 documents in its own comment that
# SEVEN entries once sat below a comment containing a paren and were therefore
# INVISIBLE to this check: a drift gate silently examining half its list, which
# is the same class of defect it exists to catch. Making the regex GREEDY would
# be worse - it would swallow to the last ')' in the file - so the array is now
# extracted by MATCHING PARENS, skipping '#' comments and quoted strings. That
# is the only form that stays right regardless of what anyone writes inside the
# list. The "keep every entry above this comment" instruction over in the deploy
# script is now obsolete; it does no harm.
# ===========================================================================
function Get-PsArrayBody {
  param([string]$Text, [string]$VarName)
  $m = [regex]::Match($Text, ('\$' + [regex]::Escape($VarName) + '\s*=\s*@\('))
  if (-not $m.Success) { return $null }
  $i = $m.Index + $m.Length
  $start = $i
  $depth = 1
  $inComment = $false
  $quote = $null
  while ($i -lt $Text.Length) {
    $c = $Text[$i]
    if ($inComment) {
      if ($c -eq "`n") { $inComment = $false }
    } elseif ($null -ne $quote) {
      if ($c -eq $quote) { $quote = $null }
    } else {
      if     ($c -eq '#')                { $inComment = $true }
      elseif ($c -eq '"' -or $c -eq "'") { $quote = $c }
      elseif ($c -eq '(')                { $depth++ }
      elseif ($c -eq ')')                { $depth--; if ($depth -eq 0) { return $Text.Substring($start, $i - $start) } }
    }
    $i++
  }
  return $null   # unterminated: refused by the caller, never silently trimmed
}

$cppGated = @([regex]::Matches($scaleTierSrc, 'DepOkByName[^)]*?(z_SC4UIScale_[A-Za-z0-9]+)') |
              ForEach-Object { $_.Groups[1].Value } | Sort-Object -Unique)
$psBody   = Get-PsArrayBody $deploySrc 'DEPENDENCY_GATED'
if ($null -eq $psBody) {
  $failures += "Deploy-OnGameClose.ps1: no `$DEPENDENCY_GATED list found (or its @( ... ) never closes) - the dependency gate reverted to a filename pattern, which disarms tier-gated-only packages"
} elseif ($cppGated.Count -eq 0) {
  # A parse that finds nothing is a REFUSAL, not a pass (NULL IS NOT EVIDENCE).
  $failures += "dependency-gate drift check: parsed ZERO DepOkByName call sites out of ScaleTier.cpp - the regex no longer matches the source, so this gate proved nothing"
} else {
  $psGated = @([regex]::Matches($psBody, '"(z_SC4UIScale_[A-Za-z0-9]+)"') |
               ForEach-Object { $_.Groups[1].Value } | Sort-Object -Unique)
  if ($psGated.Count -eq 0) {
    $failures += "dependency-gate drift check: the `$DEPENDENCY_GATED body parsed to ZERO package names - the extraction found the array but not its contents, so this gate proved nothing"
  }
  $missing = @($cppGated | Where-Object { $psGated -notcontains $_ })
  $extra   = @($psGated  | Where-Object { $cppGated -notcontains $_ })
  foreach ($m in $missing) {
    $failures += ("dependency-gate drift: " + $m + " is DepOkByName-gated in ScaleTier.cpp but absent from `$DEPENDENCY_GATED - the deploy will re-arm it with its mod uninstalled")
  }
  foreach ($e in $extra) {
    $failures += ("dependency-gate drift: " + $e + " is in `$DEPENDENCY_GATED but has NO DepOkByName gate in ScaleTier.cpp - the deploy will silently refuse to arm it at every tier")
  }
  if ($missing.Count -eq 0 -and $extra.Count -eq 0) {
    Write-Output ("  dependency-gate list matches ScaleTier.cpp (" + $cppGated.Count +
      " gated packages; " + $psGated.Count + " read from the deploy list by " +
      "paren-matched extraction, not the old lazy regex).")
  }
}

# COMPARATOR-AMBIGUOUS FOLDER BOUNDARY (2026-08-25, adversarial sweep).
#
# "Subfolders load alphabetically, last wins" is COMPARATOR-SPECIFIC, and the
# project never noticed because every folder pair it had ever measured sorts
# the same way under all of them. '_' (0x5F) sits BETWEEN the upper-case
# letters (0x41-0x5A) and the lower-case ones (0x61-0x7A), so `z____name`
# vs `zzz-SC4UIScale` INVERTS depending on whether the comparator upcases or
# lowercases - and under the inverted order our override folder loses and
# every package in it is silently inert. That shipped once (the Carbon skin's
# own `z____scoty_mods`, caught in review, renamed to `zz-scoty-mods`).
#
# The invariant: NO folder carrying DBPF archives may sort at-or-after
# zzz-SC4UIScale under ANY candidate comparator. Checked against the LIVE
# folder set so a mod installed next week is checked too, and scoped to
# folders that actually carry loadable archives - a docs folder sorting late
# (e.g. ~Documents, tilde 0x7E) cannot take a TGI and is only noted.
$OUR_LAST = "zzz-SC4UIScale"
$DBPF_GLOB = @("*.dat", "*.sc4lot", "*.sc4desc", "*.sc4model", "*.sc4")
foreach ($d in @(Get-ChildItem $plugins -Directory -ErrorAction SilentlyContinue)) {
  if ($d.Name -eq $OUR_LAST) { continue }
  $cmps = @{
    "ordinal"   = [string]::CompareOrdinal($d.Name, $OUR_LAST)
    "upcased"   = [string]::CompareOrdinal($d.Name.ToUpperInvariant(), $OUR_LAST.ToUpperInvariant())
    "lowercased" = [string]::CompareOrdinal($d.Name.ToLowerInvariant(), $OUR_LAST.ToLowerInvariant())
  }
  $late = @($cmps.Keys | Where-Object { $cmps[$_] -ge 0 })
  if (-not $late.Count) { continue }
  $hasDbpf = @(Get-ChildItem $d.FullName -Recurse -File -Include $DBPF_GLOB -ErrorAction SilentlyContinue | Select-Object -First 1).Count -gt 0
  $how = ($late | Sort-Object) -join ","
  if ($hasDbpf) {
    $failures += ("comparator boundary: folder '" + $d.Name + "' carries DBPF archives and sorts AT/AFTER " +
                  $OUR_LAST + " under comparator(s): " + $how + " - under that ordering every package in " +
                  $OUR_LAST + " is silently OUT-SORTED (armed but never rendered). Rename the folder so it " +
                  "sorts earlier under ALL comparators (a leading hyphen or digit is unambiguous).")
  } else {
    Write-Host ("  note: folder '" + $d.Name + "' sorts at/after " + $OUR_LAST + " under " + $how +
      " but carries no DBPF archive, so it cannot win a TGI.")
  }
}

# ===========================================================================
# ARMED-TIER AGREEMENT (added 2026-08-19 after CsiIcons shipped 1.5x art to a
# 2x install for a day; REBUILT 2026-08-29 for the content-swap layout).
#
# PRESENCE IS NOT ARMING. Every assertion above asks whether a package EXISTS.
# CsiIcons existed at all three tiers, correct sizes, and was still wrong -
# because the deploy armed the 15x file while every other family armed 2x. No
# "is it present" test can see that.
#
# THE OLD IMPLEMENTATION IS OBSOLETE BY CONSTRUCTION, not merely stale: it read
# bare `<base>-<tier>.dat` names, and in the target layout NO SUCH NAME EXISTS
# for any package. It would have found zero armed families, fallen through the
# `$armed.Count -gt 1` guard, and passed silently forever - the worst possible
# failure for a gate whose entire job is to notice a silent split.
#
# WHAT REPLACES IT. The v4.0.3 pilot already answered "which tier is this?" for
# SelectiveArt BY CONTENT HASH, because its stable filename could not answer it.
# That is now the general case, so the method is generalised to every package -
# and a SECOND, INDEPENDENT source is added:
#
#   (A) z_SC4UIScale_STATE.txt - written by WriteArmState every boot, per
#       folder. Says what the DLL BELIEVES it armed.
#   (B) the content hash of the live `<base>.dat` against every payload / tier
#       source. Says what the bytes on disk ACTUALLY are.
#
# They are independent: (A) is the DLL's own bookkeeping, (B) is the filesystem.
# TWO BLIND INSTRUMENTS AGREEING IS ONE INSTRUMENT - so this does not merely
# union them, it CROSS-CHECKS them and reds on disagreement. A STATE.txt saying
# 3x over a live file whose bytes are the 15x payload is precisely the shape
# that put stock 1x art into a 3x runtime.
#
# GOES RED WHEN: two packages report different tiers; STATE.txt and the bytes
# disagree for one package; the live bytes match NO known source; the live bytes
# match more than one (converged sources hide a real mismatch); the stock
# selector is armed at the same time as a scaled tier; or nothing at all could
# be determined while packages are present (a refusal, not a pass).
# ===========================================================================
$state = @{}          # base -> @{ tag; reason; dir }
$stateFilesFound = 0
foreach ($d in $OUR_DIRS) {
  $sp = Join-Path $d 'z_SC4UIScale_STATE.txt'
  if (-not (Test-Path $sp)) { continue }
  $stateFilesFound++
  $rows = 0
  foreach ($line in (Get-Content $sp)) {
    if ($line -match '^\s*#' -or -not $line.Trim()) { continue }
    $c = $line -split "`t"
    # WriteArmState emits SEVEN columns; anything else is a format change and
    # must not be half-read into a verdict.
    if ($c.Count -lt 7) { continue }
    $rows++
    $state[$c[0]] = @{ tag = $c[1]; reason = $c[2]; dir = $d }
  }
  if ($rows -eq 0) {
    $failures += ("z_SC4UIScale_STATE.txt in " + (Split-Path $d -Leaf) +
      " exists but yielded ZERO parseable rows (expected 7 tab-separated columns " +
      "after two '#' header lines, per WriteArmState). The file format moved and " +
      "every verdict sourced from it below is blind.")
  }
}
if ($stateFilesFound -eq 0) {
  Write-Host ("  note: no z_SC4UIScale_STATE.txt in either folder. The DLL writes " +
    "one per folder on EVERY boot (WriteArmState), so this means the game has not " +
    "launched since this layout was placed. The armed-tier verdict below therefore " +
    "rests on content hashing alone - one instrument, not two - and the " +
    "dependency-gate verdict cannot be sourced at all.")
}

$armed   = @{}        # base -> tag, from whichever instrument spoke
$armedBy = @{}        # base -> "state" / "content" / "state+content"
$TIER_TAGS = @('15x', '2x', '3x')
$ALL_TAGS  = @('15x', '2x', '3x', '1x', 'on', 'off')
$nArmDetected = 0
foreach ($rel in ($wantTags.Keys | Sort-Object)) {
  if (-not $carbonBuilt -and $rel -match 'ZCarbon') { continue }
  $base = Split-Path $rel -Leaf
  $contentTag = $null
  $live = Resolve-LiveFile $rel
  if ($live) {
    # (B) the bytes. Compare the live file against every candidate source.
    $lh = (Get-FileHash $live -Algorithm SHA256).Hash
    $matchTags = @()
    $availTags = @()
    foreach ($t in $ALL_TAGS) {
      $src = Resolve-PkgFile $rel $t
      if (-not $src) { continue }
      if ($src.Path -eq $live) { continue }   # never compare a file to itself
      $availTags += $t
      if ((Get-FileHash $src.Path -Algorithm SHA256).Hash -eq $lh) { $matchTags += $t }
    }
    if ($matchTags.Count -eq 1) { $contentTag = $matchTags[0] }
    elseif ($matchTags.Count -gt 1) {
      $failures += ($base + ": the live .dat is byte-identical to MORE THAN ONE " +
        "source (" + ($matchTags -join ", ") + ") - the sources have converged, " +
        "which hides a real tier mismatch from this check. Rebuild the tiers.")
    }
    elseif ($availTags.Count -gt 0) {
      $failures += ($base + ": the live .dat matches NONE of its " + $availTags.Count +
        " available source(s) (" + ($availTags -join ", ") + ") - it was not written " +
        "by ArmOne, or a source has drifted since the boot that wrote it. The game " +
        "is loading bytes nothing in this tree can account for.")
    }
  } else {
    # No stable live file: the rename layout's normal state for a tier package.
    # Armed tier = the tier whose bare `<base>-<tag>.dat` exists.
    $plainTiers = @()
    foreach ($t in @('15x','2x','3x','1x')) {
      if (Test-Path ((Join-Path $plugins $rel) + "-$t.dat")) { $plainTiers += $t }
    }
    if ($plainTiers.Count -gt 1) {
      $failures += ($base + ": MORE THAN ONE armed tier (" + ($plainTiers -join ", ") +
        ") - two copies of the same TGIs race on load order and the winner is " +
        "whichever sorts last")
    } elseif ($plainTiers.Count -eq 1) { $contentTag = $plainTiers[0] }
  }

  $stateTag = $null
  if ($state.ContainsKey($base)) { $stateTag = $state[$base].tag }

  # THE CROSS-CHECK. Both instruments present and disagreeing is the defect.
  if ($stateTag -and $contentTag -and $stateTag -ne $contentTag) {
    $failures += ($base + ": STATE.txt says tag '" + $stateTag + "' but the live " +
      ".dat's bytes are the '" + $contentTag + "' source. The DLL believes it armed " +
      "one tier and the game is loading another - the exact shape that put stock 1x " +
      "art into a 3x runtime. The bytes win; do not trust STATE.txt here.")
  }
  $pick = $null
  if ($contentTag)     { $pick = $contentTag }
  elseif ($stateTag)   { $pick = $stateTag }
  if ($pick) {
    $nArmDetected++
    $armed[$base] = $pick
    if ($stateTag -and $contentTag) { $armedBy[$base] = 'state+content' }
    elseif ($contentTag)            { $armedBy[$base] = 'content' }
    else                            { $armedBy[$base] = 'state' }
  }
}

# One tier, across every package that reports one.
$tierArmed = @{}
foreach ($k in $armed.Keys) { if ($TIER_TAGS -contains $armed[$k]) { $tierArmed[$k] = $armed[$k] } }
if ($tierArmed.Count -gt 1) {
  $distinct = @($tierArmed.Values | Sort-Object -Unique)
  if ($distinct.Count -gt 1) {
    $majority = ($tierArmed.Values | Group-Object | Sort-Object Count -Descending |
                 Select-Object -First 1).Name
    foreach ($k in @($tierArmed.Keys)) {
      if ($tierArmed[$k] -ne $majority) {
        $failures += ($k + ": armed at " + $tierArmed[$k] +
          " while the rest of the install is armed at " + $majority +
          " - this family ships the wrong tier's art (detected by " + $armedBy[$k] + ")")
      }
    }
  } else {
    Write-Output ("  armed-tier agreement: all " + $tierArmed.Count +
      " tier-managed package(s) armed at " + $distinct[0] + ".")
  }
}
# THE INVERSE PACKAGE. SelectorUI is armed by the ABSENCE of a tier - it is what
# keeps 1x from being a one-way door. Armed at the same time as a scaled tier is
# a contradiction: stock-geometry selector art loading beside scaled art.
$selBase = 'z_SC4UIScale_SelectorUI'
if ($armed.ContainsKey($selBase)) {
  $selTag = $armed[$selBase]
  if (($selTag -eq '1x' -or $selTag -eq 'on') -and $tierArmed.Count -gt 0) {
    $failures += ($selBase + " is ARMED (" + $selTag + ") while " + $tierArmed.Count +
      " package(s) are armed at a scale tier. That package exists only for the " +
      "STOCK tier; both live at once means stock-geometry selector art inside a " +
      "scaled UI.")
  }
  if ($selTag -eq 'off' -and $tierArmed.Count -eq 0 -and $nArmDetected -gt 1) {
    $failures += ($selBase + " is OFF and NO package is armed at any tier - the " +
      "install is at stock with no way back up except editing the ini by hand. " +
      "That is the 1x one-way door this package exists to prevent.")
  }
}
# NULL IS NOT EVIDENCE. Zero determinations must never read as agreement.
if ($nArmDetected -eq 0) {
  $failures += ("armed-tier agreement determined NOTHING for any of the " +
    $wantTags.Count + " SyncDat-managed package(s): no STATE.txt row and no " +
    "content match. The gate whose entire job is to notice a tier split saw " +
    "nothing at all - a refusal, not a pass.")
} else {
  Write-Host ("  armed-tier sources: " + $nArmDetected + " package(s) determined (" +
    ((@($armedBy.Values | Group-Object | ForEach-Object { "$($_.Count) by $($_.Name)" })) -join ", ") + ").")
}

# ===========================================================================
# DEPENDENCY-GATE VERDICT - NO LONGER READABLE FROM A FILENAME.
#
# Through v4.4.0 "this package is gated off" was visible on a directory
# listing: every tier sat as `.x1-disabled` and nothing was live. From v4.5.0 a
# gated-off package is a LIVE `.dat` holding `.off` content, indistinguishable
# in a listing from an armed one. So the verdict is sourced from STATE.txt: the
# tag column ('off') plus the reason column, which CommitArming writes as
# "armed" or "gated off or no tier match".
#
# THE REASON STRING CANNOT DISTINGUISH THOSE TWO CASES ON ITS OWN - both reach
# ArmOne through the same `w.wanted == false` branch - so the distinction is
# MADE HERE, from the one extra fact the reason column lacks: whether any OTHER
# package is armed at a tier. If a tier is armed install-wide then "no tier
# match" is not available as an explanation for a tier-managed package, and
# 'off' can only mean a gate turned it off.
#
#   in $DEPENDENCY_GATED and off  -> its mod is absent or changed. NOTE. That is
#                                    correct behaviour; Test-ThirdPartyGates.ps1
#                                    owns the deeper verdict.
#   NOT gated and off, tier armed -> RED. A tier-gated-only package must be
#                                    armed whenever a tier is armed. This is the
#                                    #196 CsiIcons shape exactly: present,
#                                    correct, and never following the tier.
#   SelectorUI / WebText          -> inverse gates, excluded and noted.
# ===========================================================================
$INVERSE_BASES = @('z_SC4UIScale_SelectorUI', 'z_SC4UIScale_WebText')
$anyTierArmed = ($tierArmed.Count -gt 0)
$nGateVerdicts = 0
if ($stateFilesFound -eq 0) {
  Write-Host ("  note: dependency-gate verdicts NOT CHECKED - they can only be " +
    "sourced from z_SC4UIScale_STATE.txt (a gated-off package is a live .dat " +
    "under the same name as an armed one) and no state file exists yet. This is " +
    "the one verdict the v4.5.0 layout made unreadable from disk alone.")
} else {
  foreach ($base in ($state.Keys | Sort-Object)) {
    if (-not $carbonBuilt -and $base -match 'ZCarbon') { continue }
    $nGateVerdicts++
    if ($state[$base].tag -ne 'off') { continue }
    if ($INVERSE_BASES -contains $base) {
      Write-Host ("  note: " + $base + " is inert (tag off, reason '" +
        $state[$base].reason + "'). That package is armed by the ABSENCE of its " +
        "condition, so inert here is the normal scaled-tier / mod-present state.")
      continue
    }
    if ($cppGated -contains $base) {
      Write-Host ("  note: " + $base + " is DEPENDENCY-GATED OFF (STATE.txt reason: '" +
        $state[$base].reason + "'). Its third-party mod is absent or has changed " +
        "size; the live .dat holds the inert .off payload. Correct behaviour - " +
        "Test-ThirdPartyGates.ps1 owns the deeper verdict.")
      continue
    }
    if ($anyTierArmed) {
      $failures += ($base + ": INERT (STATE.txt tag 'off') while the install is " +
        "armed at a scale tier. This package has NO DepOkByName gate in " +
        "ScaleTier.cpp, so 'no tier match' cannot explain it - it is simply not " +
        "following the tier. That is #196 (CsiIcons) exactly: present at every " +
        "tier, correct sizes, and silently stuck.")
    }
  }
  if ($nGateVerdicts -eq 0) {
    $failures += ("dependency-gate verdict pass read ZERO rows out of the " +
      $stateFilesFound + " STATE.txt file(s) found - a refusal, not a pass.")
  }
}

# ===========================================================================
# THE LIVE FILE IS A WHOLE PACKAGE.
#
# Every count assertion at the top of this suite measures a SOURCE (a payload,
# or a tier-tagged dat). None of them measures the file SC4 actually opens.
# Under the rename layout those were the same file; under the content swap they
# are not, and ArmOne rewrites the live one with CopyFileW + MoveFileEx every
# boot. A half-written live file is a real, reachable state (disk full, an
# antivirus holding the handle, OneDrive rehydrating): the commit fails INERT
# only if MoveFileEx is refused - a copy that half-succeeds leaves a truncated
# DBPF under the name the game opens.
#
# GOES RED WHEN: the live .dat's entry count is neither the package's expected
# count (armed) nor 1 (the one-entry `.off` payload, which build_payloads.py
# verifies is a valid single-TGI DBPF contesting nothing).
# ===========================================================================
$nLiveChecked = 0
foreach ($rel in ($wantTags.Keys | Sort-Object)) {
  if (-not $carbonBuilt -and $rel -match 'ZCarbon') { continue }
  $base = Split-Path $rel -Leaf
  if (-not $EXPECTED_BY_BASE.ContainsKey($base)) { continue }
  $live = Resolve-LiveFile $rel
  if (-not $live) { continue }
  $nLiveChecked++
  $list = & $packer --list $live 2>$null
  $n = ($list | Where-Object { $_ -match "^0x[0-9A-Fa-f]{8} 0x[0-9A-Fa-f]{8} 0x[0-9A-Fa-f]{8} " }).Count
  $want = $EXPECTED_BY_BASE[$base]
  if ($n -ne $want -and $n -ne 1) {
    $failures += ("LIVE FILE WRONG SIZE: " + $rel + ".dat holds $n entries; expected " +
      "$want (armed - the same at every tier by construction) or 1 (the inert .off " +
      "payload). The file the game opens is neither a whole package nor an inert one.")
  }
}
if ($nLiveChecked -eq 0) {
  if ($layout -eq 'RENAME') {
    Write-Host ("  note: live-file entry counts NOT CHECKED - on the rename layout " +
      "only the stable-name pilot packages have a live untagged .dat, and their " +
      "tier files were already counted above. This becomes a live gate on " +
      "conversion.")
  } else {
    $failures += ("live-file check examined ZERO packages in the " + $layout +
      " layout, where EVERY package must have a live untagged .dat. Refusal, not " +
      "a pass.")
  }
}

# ---------------------------------------------------------------------------
# #100 - THE 4x BUBBLE ASSERTION. A PAYLOAD CHECK, NOT A FILE CHECK.
#
# THE HAZARD. The U-Drive-It mission bubble {856DDBAC,46A006B0,094AC89A} is
# 32x32 at 1x. #100 established that flipping its art flag alone would ship it
# at 4x and, at the 2x tier, produce the exact 8x shape that #98 had already
# cost a launch to diagnose. The investigation ended in "DO NOT SHIP" - a
# SENTENCE IN A DOC, which is the weakest possible guard (law 52: a gate must
# be a live expression, never a sentence in a comment).
#
# So this asserts the pixels, per tier, out of the SHIPPED package: the entry
# must decode as a PNG whose width and height are both exactly 32 * factor.
# the 2026-08-16 measurement
# below read 15x 48x48 / 2x 64x64 / 3x 96x96, i.e. 32*factor. The 2026-08-17
# USER DECISION replaced that with the flat 96 pin the assertion now uses.
# A stale comment that contradicts the assertion under it is how a correct
# gate gets 'fixed' back into a wrong one.
#
# It reads the DBPF INDEX and hashes nothing: a dat FILE hash is useless here
# because two builds of identical content differ in 2 bytes at offsets 25/29
# (the header timestamp, #170). Payload or nothing.
# PARSE THESE UNSIGNED. PowerShell reads a hex literal above 0x7FFFFFFF as a
# NEGATIVE Int32 (0x856DDBAC -> -2056159316), so comparing it against a UInt32
# read out of the index matches NOTHING and the gate fails claiming the TGI is
# absent - which is what it did on its first run here. A gate that fails for
# its own reason is worse than no gate; it must be able to PASS before it is
# allowed to fail (law 50b).
#
# v4.5.0: the tier is now reached through Resolve-PkgFile, so this measures the
# `.15x/.2x/.3x.uipay` PAYLOAD under the new layout and the tier-tagged dat
# under the old one. IT MUST NEVER MEASURE THE LIVE `<base>.dat`: that file
# holds exactly ONE tier's bytes, so two of the three assertions would then be
# made against the wrong tier's art and fail for their own reason.
#
# #197 (2026-08-18) replaces #186's PIN - AND IT replaces A USER
# DECISION, so it is spelled out rather than quietly swapped.
#   #186, 2026-08-17, USER: "grow at all tiers for clickability" -> art pinned
#     at 96px (3x design) in EVERY tier package.
#   #197, 2026-08-18, USER: "we overdid it with scaling on our UDriveIt
#     buttons ... 1.5X should truly just be 1.5X, 2X=2X etc."
# The later rule wins. The pin was not wrong about clickability - it was wrong
# about ARITHMETIC: the window is BORN at the art's pixel size and the sweep
# then multiplies by f, so on-screen = 32 * a * f. With a pinned at 3 the
# marker was a flat 3x oversize at EVERY tier, which is what the user saw.
#
# Art is now staged at RoundHalfUp(32*f) - 48 / 64 / 96 - and 0x48E945B4 is in
# kNeverScaleIds so the sweep cannot apply f a second time. The draw clamp
# then self-cancels (source == window => m = 1), giving 32*f exactly, crisp.
# The #100 hazard is still caught: a 4x flag would stage 128 at f=2 and fail
# the 64 expected here.
#
# IF CLICKABILITY IS NOW TOO SMALL AT 1.5x, that is a HIT-BOX question, not
# a size question - grow the hit box, do not re-pin the art, or the arithmetic
# breaks again and #100 comes back.
# ---------------------------------------------------------------------------
$BUBBLE = @{ T = [Convert]::ToUInt32("856DDBAC", 16)
             G = [Convert]::ToUInt32("46A006B0", 16)
             I = [Convert]::ToUInt32("094AC89A", 16)
             Design = 32 }
$BUBBLE_TIERS = @{ "15x" = 1.5; "2x" = 2.0; "3x" = 3.0 }
$nBubble = 0
foreach ($tag in $BUBBLE_TIERS.Keys) {
  # #197: expected size is now the FACTOR times design, not a constant, and
  # it is computed with the project's one rounding convention (law 89,
  # RoundHalfUp) so the gate and the builder cannot drift apart.
  $want = [int][Math]::Floor($BUBBLE.Design * $BUBBLE_TIERS[$tag] + 0.5)
  $srcHit = Resolve-PkgFile "010-SC4UIScale\z_SC4UIScale_SelectiveArt" $tag
  if (-not $srcHit) { $failures += ("#100 bubble: no SelectiveArt $tag source deployed (payload or tier-tagged)"); continue }
  $p = $srcHit.Path
  try {
    $b = [System.IO.File]::ReadAllBytes($p)
    if ([System.Text.Encoding]::ASCII.GetString($b, 0, 4) -ne "DBPF") { throw "not a DBPF" }
    $cnt = [BitConverter]::ToUInt32($b, 36); $off = [BitConverter]::ToUInt32($b, 40)
    $hit = $null
    for ($k = 0; $k -lt $cnt; $k++) {
      $r = $off + $k * 20
      if ([BitConverter]::ToUInt32($b, $r) -eq $BUBBLE.T -and
          [BitConverter]::ToUInt32($b, $r + 4) -eq $BUBBLE.G -and
          [BitConverter]::ToUInt32($b, $r + 8) -eq $BUBBLE.I) {
        $hit = @{ o = [BitConverter]::ToUInt32($b, $r + 12); s = [BitConverter]::ToUInt32($b, $r + 16) }
        break
      }
    }
    if (-not $hit) { $failures += ("#100 bubble: TGI absent from SelectiveArt $tag (" + (Split-Path $p -Leaf) + ")"); continue }
    # PNG IHDR: 8-byte signature, 4-byte length, "IHDR", then big-endian w,h.
    $o = [int]$hit.o
    if ($b[$o] -ne 0x89 -or $b[$o + 1] -ne 0x50) { $failures += ("#100 bubble: entry in SelectiveArt $tag is not a PNG"); continue }
    $w = ($b[$o + 16] -shl 24) -bor ($b[$o + 17] -shl 16) -bor ($b[$o + 18] -shl 8) -bor $b[$o + 19]
    $h = ($b[$o + 20] -shl 24) -bor ($b[$o + 21] -shl 16) -bor ($b[$o + 22] -shl 8) -bor $b[$o + 23]
    if ($w -ne $want -or $h -ne $want) {
      $failures += ("#100 BUBBLE WRONG SIZE in SelectiveArt {0}: {1}x{2}, expected {3}x{3}. This is the DO-NOT-SHIP art from #100 - at the 2x tier it reproduces #98's 8x shape." -f $tag, $w, $h, $want)
    } else { $nBubble++ }
  } catch {
    $failures += ("#100 bubble: could not read SelectiveArt $tag - " + $_.Exception.Message)
  }
}
# The bubble gate must MEASURE three tiers or say it did not. Zero passes with
# zero failures would mean the loop never ran at all.
if ($nBubble -eq 0 -and $failures.Count -eq 0) {
  $failures += ("#100 bubble: ZERO tiers measured and no failure recorded - the " +
    "loop did not run. Refusal, not a pass.")
}

# ---- SHA256SUMS.txt vs THE BUNDLE (v4.5.2) ----------------------------------
# v4.5.1 shipped a manifest written BEFORE the payload converter ran: 66 rows
# for 106 files, zero rows for the 80 payloads, and rows naming deleted files.
# Build-Dist now writes it after conversion; this re-verifies INDEPENDENTLY -
# a manifest correct by construction is one refactor away from wrong again.
# Runs only when a bundle for the CURRENT DLL version exists (dist is not
# always present; absence is reported, never silently skipped).
$verSrc2 = Get-Content (Join-Path $proj "src\SC4UIScaleDllDirector.cpp") -Raw
$nSums = 0
if ($verSrc2 -match '#define\s+UISCALE_VERSION_STR\s+"([0-9.]+(?:-[A-Za-z0-9]+)?)"') {
  $bundleDir = Join-Path $proj ("dist\SC4UIScale-v" + $Matches[1])
  $sumsFile = Join-Path $bundleDir "SHA256SUMS.txt"
  if (-not (Test-Path $sumsFile)) {
    Write-Output ("note: no dist bundle for v" + $Matches[1] + " - SHA256SUMS check skipped (build one with _packaging\Build-Dist.ps1)")
  } else {
    $sumRows = @{}
    foreach ($ln in (Get-Content $sumsFile | Where-Object { $_ -match '^[0-9A-Fa-f]{64}\s+\S' })) {
      $h2, $rel2 = $ln -split '\s+', 2
      $sumRows[$rel2.Trim()] = $h2.ToUpperInvariant()
    }
    $bundleFiles2 = @(Get-ChildItem (Join-Path $bundleDir "Plugins") -Recurse -File)
    foreach ($f2 in $bundleFiles2) {
      $rel2 = $f2.FullName.Substring($bundleDir.Length + 1)
      if (-not $sumRows.ContainsKey($rel2)) {
        $failures += ("SHA256SUMS.txt has NO row for bundle file " + $rel2 + " - the manifest describes a different layout than the bundle (the v4.5.1 defect)")
        continue
      }
      if ((Get-FileHash $f2.FullName -Algorithm SHA256).Hash -ne $sumRows[$rel2]) {
        $failures += ("SHA256SUMS.txt hash MISMATCH for " + $rel2)
      } else { $nSums++ }
      $sumRows.Remove($rel2)
    }
    foreach ($orphanRow in $sumRows.Keys) {
      $failures += ("SHA256SUMS.txt names a file the bundle does not have: " + $orphanRow)
    }
    if ($nSums -eq 0 -and $failures.Count -eq 0) {
      $failures += "SHA256SUMS check verified ZERO files with zero failures - the loop never ran; refusal, not a pass"
    }
    # Visible even when other sections fail: "ran and clean" must be
    # distinguishable from "never ran" without reading the code.
    Write-Output ("SHA256SUMS check: " + $nSums + " bundle file(s) re-verified against the manifest")
  }
}

if ($failures.Count -eq 0) {
  Write-Output ("ALL PASS (layout $layout; $nExamined tier sources counted + " +
    "$($FONT_SOURCES.Count) font sources + DLL presence/root quarantine + " +
    "$nOverlapChecked both-layout candidates + $nHash deployed==built hashes + " +
    "$nPayloadChecked payload sets + $nArmDetected armed-tier determinations + " +
    "$nLiveChecked live files + $nBubble/3 bubble payload sizes + " +
    "$nSums SHA256SUMS rows re-verified)")
  exit 0
}
$failures | ForEach-Object { Write-Output ("FAIL: " + $_) }
exit 1
