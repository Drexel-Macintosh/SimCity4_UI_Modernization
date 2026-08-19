# Paths are RESOLVED, not hard-coded: Documents may be redirected by
# OneDrive, and the repo may be cloned anywhere (task #108).
# Regression: the deployed packages match their expected entry counts and
# the built artifacts still exist. Update EXPECTED when packages change
# (that's a deliberate act - see REGRESSION.md).
# PASS = exit 0, "ALL PASS".
$ErrorActionPreference = "Stop"
$proj = Split-Path $PSScriptRoot -Parent
$packer = Join-Path $proj "tools\dbpf\DbpfPack.exe"
$plugins = (Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'SimCity 4\Plugins')

# name pattern (live or gated), expected entry count
$EXPECTED = @(
  # SelectiveArt: 696 at EVERY tier (1.5x / 2x / 3x).
# 2026-08-19: 693 -> 696. The DEFAULT/PLACEHOLDER sim faces {EA32F100,
# EA32F101} in both portrait groups - 4 TGIs, 3 of them new (one was already
# staged via a .UI reference). They are the same 36x41 contract as the 19
# named portraits, and the category-3 indicator divides its UVs by ONE
# texture side - so a 36x41 fallback beside a 72x82 named face cannot both
# be right, and the fallback sims drew magnified. Staging the family, not
# the set.
  # ⭐ #190 (2026-08-19): 655 -> 693. The delta is EXACTLY 38 = the 19 runtime
  # Sim portraits (0xFA8CDFBF..0xFA8CDFD2, with 0xFA8CDFCF absent, so 19 not 20)
  # shipped under BOTH groups the archive carries, 0x46A006B0 and 0x1ABE787D.
  # That the arithmetic lands exactly on 38 with no remainder IS the check: a
  # staging change that also dragged in strays would not.
  # Verified from the DBPF ENTRY PAYLOADS, not the builder's own count (law:
  # presence is not execution) - 36x41 source, 54x62 / 72x82 / 108x123 at
  # 1.5x / 2x / 3x, i.e. exactly 36x41*f at every tier.
  # ⛔ If this number moves again, the portraits are NOT the explanation twice.
  # Find the new delta before editing this line.
  # ⚠ #136 (v2.88.0) ENDED THE TIER SPLIT. This block used to read "651 at 3x,
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
  # ⚠ STILL A HARD COUPLING. build_selective_safe.py stages the X glyphs
  # unconditionally now, and that is only valid while the wide re-encode
  # actually applies. If it is removed, or the log says "advice row wide
  # re-encode REFUSED", the builder filter AND this count must go back to 651
  # for 3x in the SAME build - otherwise the budget describes art that did not
  # ship and the row X is clipped again.
  # ⚠ THESE GLYPHS ARE INVALID WITHOUT CodePatches::ApplyAdviceRowScale.
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
  # tools\selective-safe\superseded\ - exactly the shadowing hazard that the
  # untagged DialogStatic.dat had.
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
  @{ name = "z_SC4UIScale_SelectiveArt-2x.dat";  entries = 696 },
  # DialogStatic 255 -> 259 (2026-07-29, Batch A, task #54): the last three
  # bucket-D text-bearing roots joined TARGETS in build_dialog_static.py -
  # I-6b704690 Label Tool (root 0x8A8DFCF5, shared with the generic message
  # box - per-script TGI, so both are doubled independently), I-ca539343
  # narrow region city-bubble stub (0x0A551C53), I-ebd0d36d Select A Bridge
  # sibling button (0x000A0000). All three roots are ALSO in kNeverScaleIds.
  # +4 not +3: the three scripts plus one art asset that became referenced.
  # Same 259 at every tier by construction (one builder, --factor only).
  @{ name = "z_SC4UIScale_DialogStatic-2x.dat";  entries = 265 },  # 262 -> 261 2026-08-16: #178 CAM splash {ea7f0eae} now ships ONLY in gated CamUI, ALL tiers consistent. USER DECISION STILL OWED on 262 (ship ungated); flip back if decided
  @{ name = "z_SC4UIScale_ItemIcons-2x.dat";     entries = 356 },
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
  @{ name = "zzz-SC4UIScale\z_SC4UIScale_ItemIconsSub-2x.dat"; entries = 130 },
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
  # TIER-INDEPENDENT: a string has no geometry, so there is no -15x/-3x pair.
  # Built by tools\itemicons\build_cam_graph_labels.py.
  # DELETE when CAM fixes the id upstream (reported: UPSTREAM-CAM-REPORT.md #4).
  @{ name = "zzz-SC4UIScale\z_SC4UIScale_CamGraphLabels.dat"; entries = 1 },
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
  @{ name = "zzz-SC4UIScale\z_SC4UIScale_ThirdPartyUI-2x.dat"; entries = 2 },
  # WarriorUI (task #94): 2 scripts (mayor LANDSCAPE flyout 09923283 + SIGNS &
  # LABELS column cb95403e, both replaced from 150-mods\ by warrior's
  # god-terraforming-in-mayor-mode) + 2 art (the MOD's own 14215E27/EB7C4D3B,
  # upscaled from ITS bitmaps). Gated on both mod dats by exact name+size.
  @{ name = "zzz-SC4UIScale\z_SC4UIScale_WarriorUI-2x.dat"; entries = 4 },
  @{ name = "zzz-SC4UIScale\z_SC4UIScale_WarriorUI-15x.dat"; entries = 4 },
  @{ name = "zzz-SC4UIScale\z_SC4UIScale_WarriorUI-3x.dat"; entries = 4 },
  @{ name = "z_SC4UIScale_SelectiveArt-15x.dat"; entries = 696 },
  @{ name = "z_SC4UIScale_DialogStatic-15x.dat"; entries = 265 }, # #178: see the -2x row note (2026-08-16)
  @{ name = "z_SC4UIScale_SelectiveArt-3x.dat";  entries = 696 },   # #136: was 651; #190: was 655
  @{ name = "z_SC4UIScale_DialogStatic-3x.dat";  entries = 265 }, # #178: see the -2x row note (2026-08-16)
  # TIER MATH PASS (2026-07-29, v2.24.0): ItemIcons + ItemIconsSub now exist at
  # every tier (audit finding A1 - they were -2x only, so ALL ~266+130 menu
  # icons silently reverted to 1x in scaled cells at 1.5x/3x). Built by
  # tools\itemicons\stage_icons.py --factor / build_itemicons_sub.py --factor;
  # the Sub builder verifies its name set against the shipped 2x pack-sub, so
  # counts are 266/130 at every tier by construction. ScaleTier.cpp already
  # synced these bases for all four package tags - the packages were the gap.
  @{ name = "z_SC4UIScale_ItemIcons-15x.dat";    entries = 356 },
  @{ name = "z_SC4UIScale_ItemIcons-3x.dat";     entries = 356 },
  @{ name = "zzz-SC4UIScale\z_SC4UIScale_ItemIconsSub-15x.dat"; entries = 130 },
  @{ name = "zzz-SC4UIScale\z_SC4UIScale_ItemIconsSub-3x.dat";  entries = 130 },
  # UNCOVERED THIRD-PARTY ITEM ICONS (#149, 2026-08-15). Icons a custom LOT
  # ships that no package of ours covered. The count is NOT a constant of the
  # project - it is however many uncovered icons this install has - so it is
  # asserted at the value the current build produced and must be updated when
  # build_uncovered_icons.py reports a different UNCOVERED number.
  # ⛔ NO FIXED ENTRY COUNT FOR UncoveredIcons - IT IS NOT A CONSTANT.
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
  # ⚠ ScaleTier GATES this package on the mod still being installed and
  # unchanged (2408 bytes), so a "NOT FOUND (live or gated)" here after the mod
  # is removed is CORRECT behaviour, not a regression - the check below accepts
  # either the live or the .x1-disabled name.
  @{ name = "zzz-SC4UIScale\z_SC4UIScale_SaveWarningUI-2x.dat";  entries = 2 },
  @{ name = "zzz-SC4UIScale\z_SC4UIScale_SaveWarningUI-15x.dat"; entries = 2 },
  @{ name = "zzz-SC4UIScale\z_SC4UIScale_SaveWarningUI-3x.dat";  entries = 2 },
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
  # two of CAM's dats; a half-present set would be half stale), so
  # "NOT FOUND (live or gated)" after removing CAM is CORRECT behaviour.
  # 10 -> 22 in v2.97.0 (#154): the THREE CAM-ONLY dialogs joined the set -
  # the city info screen {96a006b0,9b868f68} (the Village Hall / Town Hall
  # query) plus the civic and school query panels 12121201 / 12121205 - and
  # the info screen brought NINE of CAM's own bitmaps with it (9 scripts +
  # 13 art = 22). They are not overrides of any stock script, so they have no
  # stock twin to fall back to, and that is exactly why they hid: every check
  # in the builder asked "has a mod taken over one of OUR targets?", never
  # "is a mod's OWN dialog scaled?"
  @{ name = "zzz-SC4UIScale\z_SC4UIScale_CamUI-2x.dat";  entries = 22 },
  @{ name = "zzz-SC4UIScale\z_SC4UIScale_CamUI-15x.dat"; entries = 22 },
  @{ name = "zzz-SC4UIScale\z_SC4UIScale_CamUI-3x.dat";  entries = 22 },
  # ALWAYS-ON (untagged, never gated): LTEXT overrides matching WebRedirect
  @{ name = "z_SC4UIScale_WebText.dat";          entries = 3 }
)
# Font package sources must exist beside the DLL
$FONT_SOURCES = @("FontStyle-2x.ini", "FontStyle-15x.ini", "FontStyle-3x.ini")

$failures = @()
foreach ($e in $EXPECTED) {
  $p = Join-Path $plugins $e.name
  if (-not (Test-Path $p)) { $p = "$p.x1-disabled" }
  if (-not (Test-Path $p)) { $failures += ($e.name + ": NOT FOUND (live or gated)"); continue }
  $list = & $packer --list $p 2>$null
  $n = ($list | Where-Object { $_ -match "^0x[0-9A-Fa-f]{8} 0x[0-9A-Fa-f]{8} 0x[0-9A-Fa-f]{8} " }).Count
  if ($n -ne $e.entries) { $failures += ($e.name + ": $n entries, expected $($e.entries)") }
}

foreach ($f in $FONT_SOURCES) {
  if (-not (Test-Path (Join-Path $plugins $f))) { $failures += ("missing font source " + $f) }
}

# SC4UIScale.dll must be present.
#
# ⚠ THE SC4TouchControls QUARANTINE WAS LIFTED BY THE USER ON 2026-08-09.
# This block used to assert its ABSENCE (task #133: "it does not go back in
# until it is rebuilt independent of UI scaling"). The user reinstalled it
# deliberately - the DLL reappeared in Plugins at 09-Aug 00:09 and
# _touch-QUARANTINE-do-not-reinstall\ is now empty - and confirmed on being
# asked that this was intentional. The absence assertion is therefore retired
# IN THE SAME CHANGE as the reinstall, which is what the old comment demanded.
#
# ⛔ WHAT THIS COSTS, SO NOBODY IS SURPRISED LATER: SC4TouchControls is the one
# component that was NOT independent of UI scaling, and its ini still carries
# dead pre-split scaling keys the touch-only DLL never reads (law 50). It is
# now a LIVE VARIABLE in every UI-scaling observation. When a scaling defect is
# reported and the cause is not obvious, "is touch loaded?" belongs on the
# triage list - see _tests\SCENARIOS.md AXIS 2 (mod state).
#
# We do NOT assert its presence either: the user may pull it again at any time,
# and a red line for a file this project does not own would be exactly the
# "trained to ignore a failure" problem the old comment warned about. It is
# REPORTED, not gated.
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
if (Test-Path "$plugins\SC4TouchControls.dll") {
  Write-Host ("  note: SC4TouchControls.dll is loaded (quarantine lifted " +
    "2026-08-09, user order). It is a live variable in any UI-scaling result.")
}
# ⛔ THE FROZEN-BUNDLE HASH ASSERTIONS WERE REMOVED 2026-08-06.
# They checked another project's shipped artifacts, which now live in the
# sibling folder ..\SC4Touch\dist\. A test suite that fails because a DIFFERENT
# project's files moved is not testing this project - and a standing red makes
# every later red look pre-excused, which is the failure mode this repo has
# already paid for twice.
# The freeze itself still stands; it is that project's to assert. The
# quarantine check above stays here, because "is a foreign DLL sitting in the
# Plugins folder we deploy into" IS this project's business.

# DEPLOYED == BUILT (task #58 root cause, 2026-08-02). The ThirdPartyUI
# package was absent from Deploy-OnGameClose.ps1, so its deployed copy froze
# at the 2026-07-29 build epoch; when the art classification later changed,
# the frozen script kept clone refs (470261e8/47026240) that no longer
# shipped anywhere = the grey radio rows. Entry COUNTS and byte SIZES were
# both identical between stale and fresh (the rewrite swaps equal-length hex
# strings), so only a content hash catches this class. Every package with a
# canonical build output is asserted here; add a row whenever a new package
# is added to the deploy script.
$BUILT_PAIRS = @(
  @{ b = "build\Release\SC4UIScale.dll";                              d = "SC4UIScale.dll" }
  @{ b = "tools\selective-safe\z_SC4UIScale_SelectiveArt.dat";        d = "z_SC4UIScale_SelectiveArt-2x.dat" }
  @{ b = "tools\packages\15x\z_SC4UIScale_SelectiveArt-15x.dat";      d = "z_SC4UIScale_SelectiveArt-15x.dat" }
  @{ b = "tools\packages\3x\z_SC4UIScale_SelectiveArt-3x.dat";        d = "z_SC4UIScale_SelectiveArt-3x.dat" }
  @{ b = "tools\dialog-static\z_SC4UIScale_DialogStatic.dat";         d = "z_SC4UIScale_DialogStatic-2x.dat" }
  @{ b = "tools\packages\15x\z_SC4UIScale_DialogStatic-15x.dat";      d = "z_SC4UIScale_DialogStatic-15x.dat" }
  @{ b = "tools\packages\3x\z_SC4UIScale_DialogStatic-3x.dat";        d = "z_SC4UIScale_DialogStatic-3x.dat" }
  @{ b = "tools\dialog-static\z_SC4UIScale_SaveWarningUI.dat";        d = "zzz-SC4UIScale\z_SC4UIScale_SaveWarningUI-2x.dat" }
  @{ b = "tools\packages\15x\z_SC4UIScale_SaveWarningUI-15x.dat";     d = "zzz-SC4UIScale\z_SC4UIScale_SaveWarningUI-15x.dat" }
  @{ b = "tools\packages\3x\z_SC4UIScale_SaveWarningUI-3x.dat";       d = "zzz-SC4UIScale\z_SC4UIScale_SaveWarningUI-3x.dat" }
  @{ b = "tools\dialog-static\z_SC4UIScale_CamUI.dat";                d = "zzz-SC4UIScale\z_SC4UIScale_CamUI-2x.dat" }
  @{ b = "tools\packages\15x\z_SC4UIScale_CamUI-15x.dat";             d = "zzz-SC4UIScale\z_SC4UIScale_CamUI-15x.dat" }
  @{ b = "tools\packages\3x\z_SC4UIScale_CamUI-3x.dat";               d = "zzz-SC4UIScale\z_SC4UIScale_CamUI-3x.dat" }
  @{ b = "tools\selective-safe\z_SC4UIScale_ThirdPartyUI.dat";        d = "zzz-SC4UIScale\z_SC4UIScale_ThirdPartyUI-2x.dat" }
  @{ b = "tools\packages\15x\z_SC4UIScale_ThirdPartyUI-15x.dat";      d = "zzz-SC4UIScale\z_SC4UIScale_ThirdPartyUI-15x.dat" }
  @{ b = "tools\packages\3x\z_SC4UIScale_ThirdPartyUI-3x.dat";        d = "zzz-SC4UIScale\z_SC4UIScale_ThirdPartyUI-3x.dat" }
  @{ b = "tools\selective-safe\z_SC4UIScale_WarriorUI.dat";           d = "zzz-SC4UIScale\z_SC4UIScale_WarriorUI-2x.dat" }
  @{ b = "tools\packages\15x\z_SC4UIScale_WarriorUI-15x.dat";         d = "zzz-SC4UIScale\z_SC4UIScale_WarriorUI-15x.dat" }
  @{ b = "tools\packages\3x\z_SC4UIScale_WarriorUI-3x.dat";           d = "zzz-SC4UIScale\z_SC4UIScale_WarriorUI-3x.dat" }
  # NamIcons (task #139, 2026-08-05). Hand-placed on the day they were built
  # and therefore absent from BOTH manifests until Build-Dist noticed the
  # bundle was missing them - the #58 / #116 shape a third time. All three
  # tiers come out of tools\itemicons\out\.
  @{ b = "tools\itemicons\out\z_SC4UIScale_NamIcons-2x.dat";          d = "zzz-SC4UIScale\z_SC4UIScale_NamIcons-2x.dat" }
  @{ b = "tools\itemicons\out\z_SC4UIScale_NamIcons-15x.dat";         d = "zzz-SC4UIScale\z_SC4UIScale_NamIcons-15x.dat" }
  @{ b = "tools\itemicons\out\z_SC4UIScale_NamIcons-3x.dat";          d = "zzz-SC4UIScale\z_SC4UIScale_NamIcons-3x.dat" }
  # ⛔ UncoveredIcons ROWS DELIBERATELY ABSENT FROM THIS LIST.
  # Unlike every other package here, this one only EXISTS when the player has
  # third-party icons we do not cover. On a clean install there is nothing to
  # build and nothing to deploy - a built-vs-deployed row would then fail on a
  # correct machine, which is how a gate teaches people to ignore it.
  # Its correctness is asserted where it can be: build_uncovered_icons.py
  # refuses to pack unless every strip measures zero drift and carries the
  # hover border, and tools\uimap\emu\sim_itemicon_states.py sweeps whatever
  # IS deployed across tier x icon x state.
  @{ b = "tools\itemicons\z_SC4UIScale_ItemIcons.dat";                d = "z_SC4UIScale_ItemIcons-2x.dat" }
  @{ b = "tools\itemicons\_work\z_SC4UIScale_ItemIconsSub-2x.dat";    d = "zzz-SC4UIScale\z_SC4UIScale_ItemIconsSub-2x.dat" }
  @{ b = "tools\webtext\z_SC4UIScale_WebText.dat";                    d = "z_SC4UIScale_WebText.dat" }
  # FONTS (#57 phase 4, 2026-08-02). Fonts were the ONE asset family with no
  # deployed-vs-built assertion - existence-checked only, a few lines above -
  # and that is precisely why they drifted unnoticed: the deployed 1.5x/3x
  # files were the raw .gen.ini side-outputs (62 styles, no HTML clone
  # styles) while the repo packages carried a stale ChartTickText. Same
  # lesson as #58, one family later.
  # ⚠ 2x builds from tools\fonts\FontStyle.candidate.ini - there is no
  # tools\packages\2x\. Do NOT add a row for the live FontStyle.ini: the DLL
  # writes that at boot from the active tier's file (ScaleTier::SyncFont), so
  # it is a runtime product, not a deployed artifact.
  @{ b = "tools\fonts\FontStyle.candidate.ini";                       d = "FontStyle-2x.ini" }
  @{ b = "tools\packages\15x\FontStyle-15x.ini";                      d = "FontStyle-15x.ini" }
  @{ b = "tools\packages\3x\FontStyle-3x.ini";                        d = "FontStyle-3x.ini" }
)
$nHash = 0
foreach ($pair in $BUILT_PAIRS) {
  $bp = Join-Path $proj $pair.b
  $dp = Join-Path $plugins $pair.d
  if (-not (Test-Path $dp)) { $dp = "$dp.x1-disabled" }
  if (-not (Test-Path $bp)) { $failures += ("built artifact missing: " + $pair.b); continue }
  if (-not (Test-Path $dp)) { $failures += ("deployed artifact missing (live or gated): " + $pair.d); continue }
  if ((Get-FileHash $bp -Algorithm SHA256).Hash -ne (Get-FileHash $dp -Algorithm SHA256).Hash) {
    $failures += ("DEPLOYED != BUILT: " + $pair.d + " does not match " + $pair.b + " - a rebuild was never deployed (run Deploy-OnGameClose.ps1), or the deployed file was edited in place")
  } else { $nHash++ }
}

# ---------------------------------------------------------------------------
# #100 - THE 4x BUBBLE ASSERTION. A PAYLOAD CHECK, NOT A FILE CHECK.
#
# ⛔ THE HAZARD. The U-Drive-It mission bubble {856DDBAC,46A006B0,094AC89A} is
# 32x32 at 1x. #100 established that flipping its art flag alone would ship it
# at 4x and, at the 2x tier, produce the exact 8x shape that #98 had already
# cost a launch to diagnose. The investigation ended in "DO NOT SHIP" - a
# SENTENCE IN A DOC, which is the weakest possible guard (law 52: a gate must
# be a live expression, never a sentence in a comment).
#
# So this asserts the pixels, per tier, out of the SHIPPED package: the entry
# must decode as a PNG whose width and height are both exactly 32 * factor.
# ⚠ SUPERSEDED, kept only to date the change: the 2026-08-16 measurement
# below read 15x 48x48 / 2x 64x64 / 3x 96x96, i.e. 32*factor. The 2026-08-17
# USER DECISION replaced that with the flat 96 pin the assertion now uses.
# A stale comment that contradicts the assertion under it is how a correct
# gate gets 'fixed' back into a wrong one.
#
# ⚠ It reads the DBPF INDEX and hashes nothing: a dat FILE hash is useless here
# because two builds of identical content differ in 2 bytes at offsets 25/29
# (the header timestamp, #170). Payload or nothing.
# ⚠ PARSE THESE UNSIGNED. PowerShell reads a hex literal above 0x7FFFFFFF as a
# NEGATIVE Int32 (0x856DDBAC -> -2056159316), so comparing it against a UInt32
# read out of the index matches NOTHING and the gate fails claiming the TGI is
# absent - which is what it did on its first run here. A gate that fails for
# its own reason is worse than no gate; it must be able to PASS before it is
# allowed to fail (law 50b).
# ⚠ #197 (2026-08-18) SUPERSEDES #186's PIN - AND IT SUPERSEDES A USER
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
# ⛔ IF CLICKABILITY IS NOW TOO SMALL AT 1.5x, that is a HIT-BOX question, not
# a size question - grow the hit box, do not re-pin the art, or the arithmetic
# breaks again and #100 comes back.
$BUBBLE = @{ T = [Convert]::ToUInt32("856DDBAC", 16)
             G = [Convert]::ToUInt32("46A006B0", 16)
             I = [Convert]::ToUInt32("094AC89A", 16)
             Design = 32 }
$BUBBLE_TIERS = @{ "15x" = 1.5; "2x" = 2.0; "3x" = 3.0 }
# ===========================================================================
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
$scaleTierSrc = Get-Content (Join-Path $proj "src\ScaleTier.cpp") -Raw
$deploySrc    = Get-Content (Join-Path $proj "_tests\Deploy-OnGameClose.ps1") -Raw

$cppGated = [regex]::Matches($scaleTierSrc, 'DepOkByName[^)]*?(z_SC4UIScale_[A-Za-z0-9]+)') |
            ForEach-Object { $_.Groups[1].Value } | Sort-Object -Unique
$psBlock  = [regex]::Match($deploySrc, '(?s)\$DEPENDENCY_GATED\s*=\s*@\((.*?)\)')
if (-not $psBlock.Success) {
  $failures += "Deploy-OnGameClose.ps1: no `$DEPENDENCY_GATED list found - the dependency gate reverted to a filename pattern, which disarms tier-gated-only packages"
} elseif ($cppGated.Count -eq 0) {
  # A parse that finds nothing is a REFUSAL, not a pass (NULL IS NOT EVIDENCE).
  $failures += "dependency-gate drift check: parsed ZERO DepOkByName call sites out of ScaleTier.cpp - the regex no longer matches the source, so this gate proved nothing"
} else {
  $psGated = [regex]::Matches($psBlock.Groups[1].Value, '"(z_SC4UIScale_[A-Za-z0-9]+)"') |
             ForEach-Object { $_.Groups[1].Value } | Sort-Object -Unique
  $missing = @($cppGated | Where-Object { $psGated -notcontains $_ })
  $extra   = @($psGated  | Where-Object { $cppGated -notcontains $_ })
  foreach ($m in $missing) {
    $failures += ("dependency-gate drift: " + $m + " is DepOkByName-gated in ScaleTier.cpp but absent from `$DEPENDENCY_GATED - the deploy will re-arm it with its mod uninstalled")
  }
  foreach ($e in $extra) {
    $failures += ("dependency-gate drift: " + $e + " is in `$DEPENDENCY_GATED but has NO DepOkByName gate in ScaleTier.cpp - the deploy will silently refuse to arm it at every tier")
  }
  if ($missing.Count -eq 0 -and $extra.Count -eq 0) {
    Write-Output ("  dependency-gate list matches ScaleTier.cpp (" + $cppGated.Count + " gated packages).")
  }
}

# ARMED-TIER AGREEMENT (added 2026-08-19 after CsiIcons shipped 1.5x art to a
# 2x install for a day).
#
# ⭐ PRESENCE IS NOT ARMING. Every existing assertion here asks whether a
# package EXISTS. CsiIcons existed at all three tiers, correct sizes, and was
# still wrong - because the deploy armed the 15x file (plain .dat name) while
# every other family armed 2x. No "is it present" test can see that, and the
# runtime SyncDat repairs the disk at launch, so the log cannot see it either.
#
# The question this asks instead: across every tier-managed family, is the SAME
# tier the armed one? A family that disagrees with the majority is the defect,
# and it does not matter which tier the machine is set to - only that they
# agree. That makes the gate independent of ScaleFactor/AutoScale, which is the
# point: a gate keyed on the tier would have to be right about the tier too.
$tierFamilies = @(
  @{ Dir = $plugins;                          Base = "z_SC4UIScale_SelectiveArt" },
  @{ Dir = $plugins;                          Base = "z_SC4UIScale_DialogStatic" },
  @{ Dir = $plugins;                          Base = "z_SC4UIScale_ItemIcons"    },
  @{ Dir = "$plugins\zzz-SC4UIScale";         Base = "z_SC4UIScale_ItemIconsSub" },
  @{ Dir = "$plugins\zzz-SC4UIScale";         Base = "z_SC4UIScale_CsiIcons"     }
)
$armed = @{}
foreach ($fam in $tierFamilies) {
  if (-not (Test-Path $fam.Dir)) { continue }
  $plainTiers = @()
  foreach ($tier in @("15x","2x","3x")) {
    if (Test-Path (Join-Path $fam.Dir ($fam.Base + "-" + $tier + ".dat"))) {
      $plainTiers += $tier
    }
  }
  if ($plainTiers.Count -eq 0) { continue }   # family not installed: fine
  if ($plainTiers.Count -gt 1) {
    $failures += ($fam.Base + ": MORE THAN ONE armed tier (" +
      ($plainTiers -join ", ") + ") - two copies of the same TGIs race on " +
      "load order and the winner is whichever sorts last")
  }
  $armed[$fam.Base] = $plainTiers[0]
}
if ($armed.Count -gt 1) {
  $distinct = @($armed.Values | Sort-Object -Unique)
  if ($distinct.Count -gt 1) {
    $majority = ($armed.Values | Group-Object | Sort-Object Count -Descending |
                 Select-Object -First 1).Name
    foreach ($k in @($armed.Keys)) {
      if ($armed[$k] -ne $majority) {
        $failures += ($k + ": armed at " + $armed[$k] +
          " while the rest of the install is armed at " + $majority +
          " - this family ships the wrong tier's art")
      }
    }
  } else {
    Write-Output ("  armed-tier agreement: all " + $armed.Count +
      " tier-managed families armed at " + $distinct[0] + ".")
  }
}

$nBubble = 0
foreach ($tag in $BUBBLE_TIERS.Keys) {
  # #197: expected size is now the FACTOR times design, not a constant, and
  # it is computed with the project's one rounding convention (law 89,
  # RoundHalfUp) so the gate and the builder cannot drift apart.
  $want = [int][Math]::Floor($BUBBLE.Design * $BUBBLE_TIERS[$tag] + 0.5)
  $p = Join-Path $plugins ("z_SC4UIScale_SelectiveArt-{0}.dat" -f $tag)
  if (-not (Test-Path $p)) { $p = "$p.x1-disabled" }
  if (-not (Test-Path $p)) { $failures += ("#100 bubble: no SelectiveArt-$tag package deployed"); continue }
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
    if (-not $hit) { $failures += ("#100 bubble: TGI absent from SelectiveArt-$tag"); continue }
    # PNG IHDR: 8-byte signature, 4-byte length, "IHDR", then big-endian w,h.
    $o = [int]$hit.o
    if ($b[$o] -ne 0x89 -or $b[$o + 1] -ne 0x50) { $failures += ("#100 bubble: entry in SelectiveArt-$tag is not a PNG"); continue }
    $w = ($b[$o + 16] -shl 24) -bor ($b[$o + 17] -shl 16) -bor ($b[$o + 18] -shl 8) -bor $b[$o + 19]
    $h = ($b[$o + 20] -shl 24) -bor ($b[$o + 21] -shl 16) -bor ($b[$o + 22] -shl 8) -bor $b[$o + 23]
    if ($w -ne $want -or $h -ne $want) {
      $failures += ("#100 BUBBLE WRONG SIZE in SelectiveArt-{0}: {1}x{2}, expected {3}x{3}. This is the DO-NOT-SHIP art from #100 - at the 2x tier it reproduces #98's 8x shape." -f $tag, $w, $h, $want)
    } else { $nBubble++ }
  } catch {
    $failures += ("#100 bubble: could not read SelectiveArt-$tag - " + $_.Exception.Message)
  }
}

if ($failures.Count -eq 0) { Write-Output "ALL PASS ($($EXPECTED.Count) dats + $($FONT_SOURCES.Count) font sources + DLL presence/quarantine + $nHash deployed==built hashes + $nBubble/3 bubble payload sizes)"; exit 0 }
$failures | ForEach-Object { Write-Output ("FAIL: " + $_) }
exit 1
