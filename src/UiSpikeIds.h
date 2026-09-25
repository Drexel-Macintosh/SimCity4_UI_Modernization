#pragma once
#include <cstddef>
#include <cstdint>

// UiSpike's window-id tables (audit B11, 2026-09-25): the k...Ids lists, the
// dock tables and the Is...Id predicates over them, moved verbatim out of
// UiSpike.cpp. Pure data and pure lookups: nothing here reads a setting or
// any state of the scaler, which is what lets it stand alone. The two
// predicates that do read state stayed in UiSpike.cpp: IsGodPanelId (a
// setting) and IsNeverScaleId (the ForceRuntimeScaleId dev lever).
//
// An anonymous namespace ON PURPOSE: each file that includes this keeps its
// own internal-linkage copy, exactly as when the tables lived in
// UiSpike.cpp, so moving them changed no generated code. The tables are
// read by offline tools too (Test-BornCorrectCoverage.ps1,
// tools/uimap/coverage_rederive.py, idcollide.py, check_marker_fit.py,
// tools/sdk/lookup.py); they read this file now.
namespace
{

	const uint32_t kGZWin_WinSC4App = 0x6104489A;
	const uint32_t kGZWin_SC4View3DWin = 0x9A47B417;
	const uint32_t kGZWin_MenuContainer = 0xAA32BCE6;
	// kGZWin_RegionScreen: UiSpikeInternal.h (audit B11).

	// Is `id` one of `table`? The one membership loop every Is...Id
	// predicate below shares (audit B9).
	template <size_t N>
	inline bool IdIn(const uint32_t (&table)[N], uint32_t id)
	{
		for (uint32_t known : table)
		{
			if (id == known) { return true; }
		}
		return false;
	}

	// Region panels scaled even while HIDDEN: the flyouts (0x09EBEE45 top
	// menu, 0x09EBEE60 options) and the mini button are pre-scaled before
	// they ever show, so opening them cannot pop from 1x to 2x on screen.
	// These IDs only exist under the region host - the city pass never
	// matches them.
	const uint32_t kRegionPanelIds[] = {
		0x0BB0F5E7, 0x09EBE9EE, 0x6A91DC15, 0x6A91DC16, 0xEA8CAD19,
		0x6A91DC14, 0x09EBEE45, 0x09EBEE60, 0x6BB92BCA,
	};
	inline bool IsRegionPanelId(uint32_t id)
	{
		return IdIn(kRegionPanelIds, id);
	}

	// NEVER scaled (user click-through 2026-07-21): windows whose content is
	// game-tiled or exemplar-art-bound at 1x, where doubling the frame makes
	// things WORSE until that art can be doubled. They stay stock size, and
	// stock-positioned by the game (flyouts hug their spawn button).
	//
	// READ THE NAME AS "NEVER SCALED **BY THE SWEEP**" (clarified v2.39.12,
	// task #85; consult sites CORRECTED v2.39.13). IsNeverScaleId is
	// consulted in exactly two places - UiSpike::ScaleOnShow (dormant at the
	// shipped ShowHook=1 log-only default) and the city sweep's panel loop
	// (direct view children only; NOT ScaleSubtree, so membership does not
	// protect against recursive descent) - and this list's own Establish-City
	// note below states the invariant that way ("so THE SWEEP must leave it
	// alone"). It is NOT a global "nothing may ever size this window" flag.
	// Three ids here are ALSO in kCityDialogIds, and that is INTENDED, not a
	// contradiction: that block is the mechanism for main-window transients
	// the sweep cannot reach, and it is held off by its own Fresh+width guard.
	// The full reasoning + the measured per-tier ownership table lives beside
	// kCityDialogIds; a `DLGLISTS` line names the overlap once per session.
	// Taking a member of this list OUT of kCityDialogIds would delete the
	// belt-and-braces that covers a package-load failure - do not do it as a
	// tidy-up.
	const uint32_t kNeverScaleIds[] = {
		// Removed from this list, with the reasons: the zoning/utilities flyout
		// columns (2026-07-22) and 0x698894D3 My Sims (v2.22.0) -
		// REGRESSION.md [CC-09].
		// STATIC-DAT DIALOGS inside the swept tree (2026-07-28). Establish City
		// is the Mayor-mode entry popup. Runtime-scaling it gives the right
		// SIZE but renders its GZWinText nodes (title/labels/warning) in a
		// wrong colour (purple) while TextEdit+button captions stay black -
		// runtime geometry scaling does not carry the text/art path the way a
		// doubled .UI does. It is served by z_SC4UIScale_DialogStatic (script +
		// 2x art + GUID fonts), so the sweep MUST leave it alone; when both ran
		// it also double-scaled to ~4x (log: 868x468 -> 1736x936). Any other
		// popup added to the static dat that lives inside the swept tree needs
		// its root id listed here too.
		0x6A414973, // Establish City (script I-2a41436b)
		// U-DRIVE-IT DRIVING-MODE STATUS PANEL (2026-07-29 night, task #46,
		// user report "the flyout opens in a broken way"). EXACTLY the
		// Establish City failure repeating - and this time we shipped it
		// without noticing, because the panel entered the static dat
		// AUTOMATICALLY: build_dialog_static.py's discover_query_family()
		// adopts every script containing id=0x10000005 + clsid 0x89e1567c,
		// and all eleven U-Drive-It status scripts (I-ac1d544d Car Control,
		// the nine vehicle variants I-0c1d*/I-2c1d73cb, timer I-2c02ba84)
		// use 0x10000005 as their INNER container under root 0x10000006.
		// So the .UI ships doubled (212x325 -> 424x650) AND, unlike the
		// query panels the discovery was written for, this root is parented
		// at the 3D VIEW (DPROBE: par=0x9A47B417 depth 1) so the city sweep
		// scales it too: log "panel 0x10000006 (1968,8 424x650) ->
		// (1536,16 848x1300)" = 4x frame around 2x content, which is the
		// huge-empty-panel look the player reported.
		// LESSON: an auto-discovery rule can enrol windows the rule's author
		// never checked the parentage of. Anything the static dat serves
		// that lives in the swept tree MUST be listed here.
		0x10000006, // U-Drive-It status panel (all 11 vehicle scripts)
		// STATIC-DAT DIALOGS added v2.22.2 (Sim picker, U-Drive-It vehicle +
		// pedestrian pickers, missing-plugin-pack warning). Evidence says all
		// are main-window transients the sweep never reaches, in which case
		// these entries are inert; listing them is free insurance against the
		// Establish-City 4x double-scale if any is in fact view-parented.
		0x6A243D9E, // Select A My Sim (script I-0a243d80, root 1)
		0x6A243D9F, // Select A My Sim (root 2)
		0xCBF32603, // U-Drive-It vehicle + pedestrian pickers (shared root)
		0x2A5CFB2C, // missing plugin-packs warning (I-ea89b6c3) + Game Over
		            // (I-0a5cf71d shares this root)
		// TEXT-SWEEP BATCH roots (v2.23.1) - same free-insurance rationale.
		0xAA8DEF97, // generic notification popup (I-ca8cbf0f)
		0x0C525B9E, // Select A Bridge (I-ebd0d36c; has an 0x0000AAAA marker,
		            // which is evidence it may be view-parented - hence this)
		// Batch C (v2.25.5): the static-doubled generic prompt boxes; the
		// standard parentage-undetermined insurance (Establish-City rule).
		0xC9264BE2, // "Text Entry" prompt / Save City confirm (I-e9263d4c)
		0x8926EEBE, // Set Lot Size (I-e9263de5)
		// v2.25.24: the budget roots left this list entirely - the budget is
		// a MULTI-ROOT COMPOSED PANEL (Graphs-class); all four roots live in
		// kDataScaledSubtreeIds with children-only data doubling.
		0x4A35B0F2, // tutorial page (I-0a2dd355)
		0xEA5E748C, // tutorial exit confirm (I-6a5e73c0)
		0xAAA9C9D9, // startup splash, both variants (I-8aa9aa14/I-aaaaf3d1)
		0xCA5E6261, // clock time popup (I-aa5e60d1)
		// BATCH A roots (v2.24.1, task #54) - same free-insurance rationale as
		// the TEXT-SWEEP BATCH above: these three joined the static dat
		// (build_dialog_static.py TARGETS) and their parentage is undetermined
		// from data (none ever appeared in a dump), so list them here or a
		// view-parented one would double-scale to 4x (the Establish-City trap).
		0x8A8DFCF5, // Label Tool (I-6b704690) - ALSO the generic message-box
		            // root (I-ea8cc3c6): one id, two static-doubled scripts,
		            // and this single entry covers both.
		0x0A551C53, // region city-bubble stub, narrow 42x159 (I-ca539343)
		0x000A0000, // Select A Bridge sibling button (I-ebd0d36d)
		// v2.65.0 (#54 census): the last three MODE C roots - a doubled
		// frame over 1x art. Never-scale is the SAFE direction for Mode C:
		// worst case the control stays stock-sized, whereas the alternative
		// the coverage matrix proposed ("stage art + list id") is EXACTLY
		// the shape #100 says predicts 8x at the 2x tier and is how #98
		// shipped a 4x legend. Inert if the window is never instantiated.
		0x0A41C7B2, // Disaster Tools button container 62x49 (I-0a41be3e):
		0x0A41C7B3, //   GZWinGen holding ONE GZWinBtn 0xEA496354 sized by
		            //   its own art {46a006b0,14416230}. An art-sized
		            //   control is already right once art is 2x (law 2);
		            //   doubling this frame can only break it. Twin pair
		            //   I-0a41be3e / I-0a41be3f, both 62x49.
		0x85202C0E, // THE SNAPSHOT / CAMERA MODE CAPTURE FRAME. Added
		            // 2026-09-01. SCALING THIS WINDOW IS THE DEFECT, not a
		            // gap: it is the 1:1 frame the game uses to define what
		            // gets captured, so its width and height ARE the export
		            // resolution in real pixels. Enlarging it would enlarge
		            // the picture the player takes.
		            //
		            // It was already skipped, but only INCIDENTALLY - it opens
		            // full-screen (measured live at (0,0 2400x1600) on a
		            // 2400x1600 view) and the sweep's >=90%-of-screen guard at
		            // :12010 continued past it. That is coverage by geometry,
		            // and the geometry is not fixed: its own OnCreate builds
		            // presets from 160x120 up, and the player can cycle them
		            // with the spacebar (the window's own LTEXT says "Press
		            // the spacebar to change size"). At a small preset it
		            // drops under the 90% guard and the sweep would be free to
		            // double it. This entry makes the exclusion ENFORCED
		            // rather than a side effect of the current default.
		            //
		            // BLAST RADIUS CHECKED, and against the one law that could
		            // have made this wrong. :5879 records a regression this
		            // project shipped THREE TIMES - "a skip list skips the
		            // FUNCTION, not the line", because the child walk lives
		            // inside ScalePanelRoot. It does not bite here: the whole
		            // 1,050-byte OnCreate sub_7B7A80 contains no
		            // `call [reg+0x38]`, so THE WINDOW HAS NO CHILDREN. Its
		            // three instruction strings are one string member at
		            // [this+0xFC], painted by the class's own Plot 0x7B6B30.
		            // There is no child walk to lose. At the shipped default
		            // preset behaviour is bit-identical to today.
		            //
		            // Reached by the camera button 0x8A1DA655 on the city dock,
		            // two byte-verified routes, and by the command the game's
		            // own registry names kCommandID_OpenSnapshotDialog
		            // (0x6A935E4B). Its class vtable is 0x00AB9BF8 - NOT the
		            // 0xAB9980 three docs recorded; the ctor stamps AB9BF8 at
		            // 0x7B748B and the live log agrees.
		0x27DF05BE, // #191 Move In My Sim marker, green twin - born
		            // correct from the data-scaled I-6a9455c9
		0x27DF05BF, // 46x97 tiled plaque (I-6a9455c9), backing image
		            // {46a006b0,13f15214} + a 36x41 icon inset at (5,5).
		            //
		            // CORRECTED 2026-09-01. This comment used to read "ONLY
		            // the ...BF twin. 0x27DF05BE is NOT here on purpose" -
		            // while 0x27DF05BE sits four lines ABOVE it, listed.
		            // The comment described a state the array had left, and
		            // it was actively dangerous: it told the next reader
		            // that a listed line should not be there, inviting its
		            // deletion.
		            //
		            // The entry is CORRECT and the old reasoning inverted
		            // the conclusion. Read the array name literally - "never
		            // scaled BY THE SWEEP". Both windows behind this id are
		            // DATA-SCALED: the Move In My Sim marker is "born
		            // correct from the data-scaled I-6a9455c9", and the
		            // Obliterate City confirm (I-2a41436c) ships data-scaled
		            // via build_dialog_static.py:280. A data-scaled window
		            // is precisely the case that needs the sweep to stand
		            // down, or it gets scaled twice. "One id, two windows"
		            // is true, but here both want the SAME treatment, so
		            // reaching both is the desired outcome, not the hazard.
		            //
		            // MEASURED 2026-09-01: the user confirmed the Move In My
		            // Sim marker renders correctly at the 2x tier with this
		            // entry present - #191 has NOT re-opened.
		            //
		            // ONE CONSUMER REMAINS UNTESTED, stated rather than
		            // assumed: nobody has opened the OBLITERATE CITY CONFIRM
		            // at 2x since this entry landed. The argument above says
		            // it should be fine, but that is inference. Also note
		            // what the marker observation does NOT settle: a correct
		            // marker WITH the entry present is consistent both with
		            // "the entry is load-bearing" and with "the entry is
		            // inert", so it does not decide that question. Deciding
		            // it needs an A/B build with the id removed, which is
		            // not worth shipping a risky build to answer - the live
		            // configuration is correct either way.
		// NOTE (2026-07-23): the god-mode tool UI (toolbar 0xC991EDA8 +
		// flyouts) is NOT excluded - northstar is EVERYTHING SCALES. The
		// toolbar scales cleanly (bottom-left column); the flyouts scale but
		// are re-positioned by the god-flyout DOCK below (Phase 2 flow), not
		// the generic center/edge anchor which mislocated them.
	};

	// GOD-MODE TOOL FLYOUTS (Phase 2 FLOW). Stock reference (vanilla dump
	// 2026-07-23, _vanilla-reference\FINDINGS.md): each flyout is
	// GAME-POSITIONED glued to its spawn button in the god toolbar. The
	// generic ScalePanelRoot MOVES the root (edge/center anchor) and
	// teleported them (day/night "right size wrong place"; terrain-fx
	// clamped to y=0). CORRECT approach = the same one ScaleMenuFlyouts uses
	// for plop-menu flyouts: SIZE-ONLY subtree scale, NO ROOT MOVE - the
	// flyout stays where the game glued it and grows in place. These ids are
	// scaled by ScaleGodFlyouts (NOT the generic sweep, which skips them).
	// Two of four are NESTED (not direct view children) so they are found by
	// GetChildWindowFromIDRecursive.
	const uint32_t kGodToolFlyoutIds[] = {
		0xCA35CBED, // terrain-effect flyout   (direct view child)
		0x49923239, // terraform tool flyout   (direct view child)
		// NOT flyouts, do not add: 0x0A78827A (the founded-city god toolbar,
		// v2.12.2) and 0xABB26B0E (a bottom-anchored god panel, v2.12.1); both
		// are in kGodPanelIds. History: REGRESSION.md [CC-10].
	};
	inline bool IsGodToolFlyoutId(uint32_t id)
	{
		return IdIn(kGodToolFlyoutIds, id);
	}

	// GOD-MODE TOOLBAR TWINS (2026-07-23, user-diagnosed duplication): the
	// god toolbar always DOUBLE-DRAWS as two sibling panels that overlap
	// pixel-perfect at stock: 0x69E40A1F (stock-layout panel: rail 157x488,
	// five 64x50 buttons, the two small sun toggles) + 0xC991EDA8 (the tile
	// strip). 0x69E40A1F reports vis=0 in god mode while its children still
	// draw, so the visibility gate skipped it -> only its twin scaled ->
	// the "duplicate sun / 1x rail". Scale BOTH by id even while hidden
	// (the kRegionPanelIds lesson). Both are bottom-left anchored, so the
	// shared transform (x'=fx, y'=fy-(f-1)*frameH) keeps them overlapped.
	// Bonus: the game positions tool flyouts off 0x69E40A1F's buttons, so
	// scaling it puts future flyout spawns at the SCALED buttons.
	const uint32_t kGodPanelIds[] = {
		0x69E40A1F, // god/mayor left-toolbar stock-layout panel
		0xC991EDA8, // god toolbar tile strip
		// FOUNDED-CITY god panel (added v2.12.1). Same stock size as
		// 0x69E40A1F (157x488) but anchored lower, at stock (3,1045). It was
		// previously treated as a hidden day/night template and scaled
		// size-only (no root move), which pushed it 421px off the bottom of
		// the screen once a city existed and it became the panel god mode
		// actually shows. Like its twins it reports vis=0 while its children
		// draw, so it must be scaled BY ID even while hidden.
		0xABB26B0E,
		// THE FOUNDED-CITY GOD TOOLBAR (added v2.12.2). Its .UI script
		// I-aa53e3ea carries Obliterate City / Reconcile Edges / Disaster /
		// Day-Night - confirmed against a STOCK founded-city capture
		// (2026-07-28): god mode is COLLAPSED by default there too, and the
		// expand tab reveals exactly those four tools.
		// It had been dismissed as "a HIDDEN god sub-tool strip" where
		// "docking/scaling changes nothing on screen", with an explicit
		// do-not-re-add note. That was measured BEFORE a city is founded,
		// where those four tools do not exist and the strip really is inert.
		// In a founded city it IS the god toolbar, and being listed in
		// kGodToolFlyoutIds made the sweep skip it -> it stayed at stock
		// 74x291 at (5,1071) while the rest of the UI was 2x, which is the
		// "god mode never loads / everything is crushed" report.
		// Bottom-anchored (stock bottom gap 238, same as 0xC991EDA8), so the
		// panel transform lands it on the dock position recorded for it on
		// 2026-07-24: 2*5=10, 2*1071-1600=542 -> (10,542) 148x582.
		0x0A78827A,
	};

	// ---- MAYOR-MODE FLYOUT DOCK TABLE ------------------------------------
	// At namespace scope because TWO functions need it: ScaleGodFlyouts docks
	// these, and ScalePanelsUnder must SKIP the mayor-only ones so the generic
	// center-anchor does not fight the dock.
	//
	// *** THE ALIGNMENT-MARKER RULE (discovered 2026-07-28) ***
	// Every tool-flyout script carries a hidden child id=0x0000AAAA sized
	// exactly like its SPAWN BUTTON, and the game places the flyout at
	//     flyoutPos = spawnButtonAbs - markerOffset
	// so once the subtree is scaled the correct target is
	//     target = spawnButtonAbs - markerOffset(live)
	// Equivalently, with R = nativePlacement - spawnButtonAbs = -marker(1x):
	//     target = spawnButtonAbs + f*R          <- what this table stores
	//
	// NOT a theory: it reproduces all three LOCKED, hand-tuned god docks to the
	// pixel - terraform (22,262), terrain-fx (22,502), day/night (22,742) - and
	// it predicted the measured mayor native placement exactly. It also explains
	// the one thing the god constant table needed a special case for: the shared
	// window 0xCA35CBED needs two offsets because swapping script MOVES its
	// marker.
	//
	// Spawn buttons are identified by POSITION in the live dump, never by
	// enumeration order - the dump enumerates children in REVERSE of .UI add
	// order (CITY-DOCK-OVERLAP.md 1.2).
	// ===== PANEL-TO-PANEL DOCK TABLE (#127, v2.76.0) =====================
	// REQUIREMENT: "ALL OF THE UI ELEMENTS SHOULD BE DOCKED VIA
	// MAP" - i.e. a panel whose position is defined RELATIVE TO ANOTHER PANEL
	// belongs in a table, exactly like kMayorFlyoutDock, not in a one-off pin.
	//
	// WHY THIS EXISTS. Our per-panel anchor (ScalePanelRoot) places each root
	// independently from ITS OWN design gaps. That is right for a panel that
	// docks to a screen edge, and WRONG for a panel that must sit against a
	// SIBLING: the game's own native seat between the two is not identical at
	// every resolution, and scaling each panel separately multiplies that
	// native drift by f. MEASURED for the Graphs pair: the game seats the
	// checkbox band 1px left of the chart at 2400x1600 but 7px left at
	// 3840x2160, so at f=3 the band lands 18px left + 12px UP of where it
	// stacks - into the chart's bottom-right corner (user screenshot).
	//
	// THE OFFSET IS MEASURED AT THE CONFIRMED ON SCREEN TIER AND SCALED. offX/offY
	// are in the anchor's own SCALED pixels at f=2 (the tier the player has
	// confirmed good), and are applied as offset * (f/2). At f=2 that is the
	// identity, so every entry is BIT-IDENTICAL at 2x by construction - the
	// same discipline as the disaster ring's seat-scaling (law 53: extrapolate
	// a tuned correction the way the thing it corrects is PLACED).
	struct PanelDock
	{
		uint32_t childId;    // the panel that must follow
		uint32_t anchorId;   // the panel it docks against
		// #137: these are 1x DESIGN units read from the .UI, NOT f=2 screen px.
		int32_t  offX;       // child.left  - anchor.left    (scales by f)
		int32_t  offY;       // anchor.bottom - child.bottom (scales by f, UP)
		const char* what;    // for the log line
	};
	const PanelDock kPanelDock[] = {
		// GRAPHS radio band. #137 (2026-08-05) REPLACED the previous entry
		//     { 0x0A4A8176, 0x8A8B5B71, -2, 640, ... }
		// which anchored the band to the CHART'S TOP with an offset eye-measured
		// off a 2x screenshot. Scaling a wrong relationship keeps it wrong at
		// every tier, and it was wrong: the band overlapped the "Graphs" title
		// and the expansion arrow at 2x AND 3x (reported).
		//
		// THE DESIGN SAYS BOTTOM-DOCK, and the .UI proves it. Comparing the two
		// scripts that share this band id - Graphs I-6bc9065a vs Data Views
		// I-ea2871aa, the panel the player pointed at as correct:
		//     Data Views  band 546x122  dLeft 0   band.bottom - parent.bottom = -2
		//     Graphs      band 503x107  dLeft +5  band.bottom - parent.bottom = -16
		// Both are BOTTOM-referenced against parent 0x8A8B5B72, not top-referenced
		// against the chart. Measured live at f=3 the old rule produced a gap of
		// 81 where the design demands RoundHalfUp(16*3) = 48 - the band sat 33px
		// too high, exactly the overlap on screen.
		//
		// So the target is now computed from the parent's BOTTOM edge:
		//     tx = anchor.L + rhu(dLeft * f)
		//     ty = (anchor.T + anchor.H) - child.H - rhu(gapBottom * f)
		// offX/offY are therefore 1x DESIGN units here, not f=2 screen px.
		// ANCHOR LIFETIME IS PART OF THE DOCK. v2.89.0 briefly anchored this
		// to 0x8A8B5B72 - correct arithmetic, wrong window. ApplyPanelDocks
		// bails on !pAnchor->IsVisible(), and the log shows 0x8A8B5B72 opening
		// NINETEEN SECONDS after the band:
		//     13:45:04.291  open #1 of 0x8A8B5B71  <- chart, opens WITH the band
		//     13:45:04.291  open #1 of 0x0A4A8176  <- the band
		//     13:45:23.845  open #1 of 0x8A8B5B72  <- the bad anchor
		// so the band painted undocked until the player clicked something. An
		// anchor must be alive whenever its child is, or the dock is born late
		// by construction - the #50/#76 born-correct law applied to the ANCHOR.
		//
		// 0x8A8B5B71 carries the SAME bottom relationship in the design
		// (band.bottom - chart.bottom = -10) and opens simultaneously, so it
		// gives an identical target: at f=3, 2004 - 321 - rhu(10*3) = 1653,
		// the value the 0x8A8B5B72 route produced and the player confirmed.
		{ 0x0A4A8176, 0x8A8B5B71, 5, 10, "graphs radio band" },
	};
	const int kPanelDockCount =
		static_cast<int>(sizeof(kPanelDock) / sizeof(kPanelDock[0]));

	// True if this id takes part in kPanelDock (either side). Lets the SHOWHOOK
	// dock a pair the instant either member becomes visible, so the panel is
	// BORN seated - the same born-correct discipline as #50/#76.
	bool IsPanelDockMember(uint32_t id)
	{
		for (int i = 0; i < kPanelDockCount; i++)
		{
			if (kPanelDock[i].childId == id || kPanelDock[i].anchorId == id)
			{
				return true;
			}
		}
		return false;
	}

	struct MayorFlyoutDock
	{
		uint32_t flyoutId;
		uint32_t buttonId;
		int32_t  offX;      // R = -marker(1x)
		int32_t  offY;
		bool     derived;   // false = report via MCAL only, do not move
		bool     mayorOnly; // true = never reaches the god flyout loop; the
		                    // generic sweep must skip it (see below)
		bool     anyMode;   // v2.25.4 (law 4, the v2.25.3 regression): true =
		                    // process WITHOUT the mayor-HUD gate. The Sim-mode
		                    // sidebar's flyouts open while the mayor HUD
		                    // 0xE9889775 is HIDDEN (the My Sims panel replaces
		                    // it), so gating them on mayorModeActive left them
		                    // skipped-but-never-docked = a raw 1x window. The
		                    // entry's own anchor search is the state gate: no
		                    // spawn button found -> no scale, no move.
	};
	const MayorFlyoutDock kMayorFlyoutDock[] = {
		// 1 LANDSCAPE 0x49923239 off button 1 - MEASURED via MCAL:
		//   native(25,371) - button(28,398) = R(-3,-27) -> target (22,344).
		//   Cross-checks against marker (3,27): (28,398)-(6,54) = (22,344).
		//   CONFIRMED ON SCREEN 2026-07-28. Shares its id with the GOD terraform
		//   flyout but a DIFFERENT script (250x498 here vs 250x582 there), so
		//   the mayor-mode gate is what keeps the two apart.
		{ 0x49923239, 0x8991EE08, -3, -27, true, false },
		// 2 ZONES 0x69923479 off button 2 0x0991EE13 abs(28,498).
		//   Marker (3,77) -> R(-3,-77) -> target (28,498)-(6,154) = (22,344).
		{ 0x69923479, 0x0991EE13, -3, -77, true, true },
		// 3 TRANSPORTATION 0xC99237A0 off button 3 0xA994824D abs(28,598).
		//   Marker (3,77) -> R(-3,-77) -> target (28,598)-(6,154) = (22,444).
		{ 0xC99237A0, 0xA994824D, -3, -77, true, true },
		// 4 UTILITIES 0xE992F711 off button 4 0xE991EE2F abs(28,698).
		//   Marker (3,77) -> R(-3,-77) -> target (28,698)-(6,154) = (22,544).
		{ 0xE992F711, 0xE991EE2F, -3, -77, true, true },
		// 5 CIVIC 0x699306ED off button 5 0x0991EE39 abs(28,798).
		//   Marker (3,227) - NOT (3,77): this flyout is taller and its marker
		//   sits lower, which is the rule working, not an anomaly.
		//   R(-3,-227) -> target (28,798)-(6,454) = (22,344).
		{ 0x699306ED, 0x0991EE39, -3, -227, true, true },
		// 7 EMERGENCY 0x0992FD17 off button 7 0x6991EE42 abs(28,1010).
		//   Marker (3,234) -> R(-3,-234) -> target (28,1010)-(6,468) = (22,542).
		//   v2.39.5: marker VERIFIED exact against the shipped script
		//   (I-899302fc.ui `id=0x0000aaaa area=(3,234,53,274)`) - the old
		//   "predicted, not measured" caveat is retired. ALSO verified: this
		//   flyout IS on the sub_7E5C10 open funnel (exe site 0x7F4C80), so it
		//   is scaled+docked at OPEN, not on the next sweep tick.
		{ 0x0992FD17, 0x6991EE42, -3, -234, true, true },
		// U-DRIVE-IT column 0x8BB27C12 (script I-6bb27447: Earned Vehicles /
		// Watercraft / Aircraft / Mission Indicators) off the Sim-mode
		// sidebar's "U Drive It" button 0xABB27A7A (sidebar 0xABB26B0E).
		// Marker (4,150) -> R(-4,-150). RULE CONFIRMED against the
		// 2026-07-30 live log with ZERO fitting: btn design (12,216) 74x58
		// on the scaled sidebar (6,490) -> btnAbs (30,922); minus marker
		// (4,150) = (26,772) = the logged native flyout position EXACTLY
		// ("panel 0x8BB27C12 (26,772 125x249)"). Target = btnAbs - f*marker.
		// (task #48; the generic sweep had CENTER-ANCHORED it to (52,647).)
		// anyMode: opens from the SIM-mode sidebar while the mayor HUD is
		// hidden - the spawn-button search is the state gate.
		{ 0x8BB27C12, 0xABB27A7A, -4, -150, true, true, true },
		// SIGNS & LABELS column 0xAB954023 (script I-cb95403e: Place
		// Signpost/Label, Remove, On/Off) - a NESTED flyout: its spawn
		// button 0xAB9537B7 "Signs & Labels Tools" lives INSIDE the
		// Landscape flyout 0x49923239, so the anchor exists only while
		// Landscape is open (recursive search fails otherwise = no move,
		// fail-safe). Marker (3,183) -> R(-3,-183). Marker-predicted like
		// Emergency was; MCAL is the correction path if it docks wrong.
		// v2.39.5: this is the ONE flyout still on GENERATION 1 - it opens
		// through sub_7E5D80 (exe site 0x7F50A7), a byte-identical TWIN of
		// the sub_7E5C10 funnel (latch [edi+0x204] vs [edi+0x200], ret 0x14)
		// that we never hooked, so OnFlyoutOpened does not fire for it and it
		// is scaled a sweep tick AFTER first paint. Before hooking the twin,
		// identify its OTHER call site's flyout 0x09DE8798 (script 0x09DE3002
		// - in no list here and in no extracted corpus). See
		// tools\research\MECHANISM-GENERATIONS.md.
		{ 0xAB954023, 0xAB9537B7, -3, -183, true, true, true },
	};
	inline const MayorFlyoutDock* FindMayorDock(uint32_t id)
	{
		for (const MayorFlyoutDock& m : kMayorFlyoutDock)
		{
			if (m.flyoutId == id) { return &m; }
		}
		return nullptr;
	}
	// Mayor flyouts that the generic city sweep would otherwise CENTER-ANCHOR.
	// ScalePanelRoot centers a panel when both gapT and gapB exceed frameH/4,
	// which is true for these, so it repositions them with no reference to their
	// spawn button (zones: 421+180-360 = 241, exactly the wrong logged value).
	// They only exist in mayor mode, so skipping them unconditionally is safe.
	inline bool IsMayorOnlyFlyoutId(uint32_t id)
	{
		const MayorFlyoutDock* m = FindMayorDock(id);
		return (m != nullptr && m->mayorOnly);
	}

	// ---- SHARED SUB-FLYOUT CONTAINER (v2.13.3) ----------------------------
	// 0x8A6E61E0 is the SECOND-LEVEL menu host: the strip that opens when you
	// pick a tool inside a flyout (zone density, road types, ...). It is a
	// DIRECT child of the 3D view, not a child of the flyout that spawned it,
	// so it inherits nothing from that flyout's dock.
	//
	// It is SHARED by every tool - observed this session at 258x482, 258x874,
	// 258x776, 258x384 and 258x580, resizing per content - so it must NEVER be
	// given a hardcoded per-tool anchor: that would fix one tool's sub-menu and
	// break the other four. Whatever rule we apply has to work for all of them.
	//
	// SIZE was already correct via the generic sweep (129x241 -> 258x482).
	// POSITION was not: ScalePanelRoot took its left/top edge-anchor branch and
	// simply DOUBLED the coordinates from the screen origin (178->356,
	// 274->548), which has nothing to do with the button that spawned it.
	//
	// Unlike the toolbar flyouts this container carries NO 0x0000AAAA alignment
	// marker, so the marker rule cannot supply an offset - the relationship has
	// to be measured. The game positions it from LIVE window positions, i.e. it
	// already accounts for our docked parent flyout, so the leading hypothesis
	// is that its own placement is right and only our re-positioning is wrong.
	// Hence: scale the size, KEEP the game's position (SubDock=0, default), and
	// log SCAL with the parent flyout and its buttons so the true rule can be
	// derived from data if this proves wrong.
	const uint32_t kSubFlyoutIds[] = { 0x8A6E61E0 };
	inline bool IsSubFlyoutId(uint32_t id)
	{
		return IdIn(kSubFlyoutIds, id);
	}

	// CITY panels that must be scaled BY ID even while they report vis=0 -
	// same lesson as kRegionPanelIds and the god twins, but for ordinary
	// city-mode windows. Added v2.12.3.
	//
	// 0xAA231508 (the NEWS READER) scaled only INTERMITTENTLY: it was caught
	// once ((130,174 440x228) -> (260,348 880x456)) and NOT ONCE across a full
	// grand-tour session, because the sweep's visibility gate only scales it if
	// it happens to report vis=1 at the moment a sweep runs. Meanwhile its
	// content pane is sized from the 2x FONTS and always renders large, so a
	// frame left at 1x gets a hugely oversized pane inside it - the "visual
	// error / too small font" report.
	// Pre-scaling it while hidden also means it can never pop 1x->2x on open,
	// the same reason the region flyouts are scaled before they are shown.
	const uint32_t kAlwaysScaleCityIds[] = {
		0xAA231508, // News reader (script I-2a2aed99)
		// Budget sub-dialogs (2026-07-29 evening): measured 1x while hidden
		// (500x464 / 500x353 in the live dump) while their siblings - the
		// compact bar 0xAA3AC000 and expanded panel 0xAA3AC001 - were swept
		// to 2x. Same vis-gate intermittency as the news reader. Their 2x
		// art ships in SelectiveArt (scripts I-aa3acdfe/I-cbc3c2b9), so a
		// 1x window would draw quarter-art + black fill.
		// #197 U-DRIVE-IT / RIGHT-DRAG MARKER 0x48E945B4 - STAYS ON THIS LIST.
		// Membership here forces the panel loop to reach it even while vis=0
		// and arms gRelatchArmed for its subtree; both are wanted. What is NOT
		// wanted is the root's own geometry write, and that is suppressed
		// inside ScalePanelRoot rather than by excluding the window here.
		//
		// DO NOT MOVE THIS TO kNeverScaleIds. That was tried on
		// 2026-08-19. The panel loop's IsNeverScaleId test does `continue`,
		// which skips the whole ScalePanelRoot CALL - and the CHILD WALK LIVES
		// INSIDE ScalePanelRoot. Excluding the window drops the resize we want
		// dropped AND the child walk we need, i.e. the "numbers are gone from
		// the deploy icons" regression for a third time by a third route.
		// A skip list skips the FUNCTION, not the line.
		0x48E945B4, // U-Drive-It / right-drag marker (root write refused in
		            // ScalePanelRoot; art is f-scaled offline)
		0xAA3AC002, // Taxes editor popup
		0xCA4C332D, // Take Out A Loan popup
		// Advisors (2026-07-29 late): the console strip's 2x face art in
		// 1x buttons showed quarter-zoomed faces on FIRST open (user
		// report; settles only after the sweep catches the strip). The two
		// briefing panels join SelectiveArt in the same fix and need the
		// same pre-scale so they never first-paint 1x with 2x art.
		0x6A15C767, // Advisors console strip (7 face buttons)
		0xAA15EF06, // advisor briefing panel (compact)
		0x2A1D96B1, // advisor briefing panel (expanded)
		// MY SIMS family (v2.22.0): three top-level roots in script
		// I-aa1f1f57 composing via the 0x0000AAAA marker; hidden until Sim
		// mode, so pre-scale while hidden (the news-reader lesson) or the
		// 2x art meets 1x windows on first entry.
		0x698894D3, // My Sims outer root (title + marker + slot buttons)
		0xCA1F1D9C, // My Sims content panel (was already swept when visible)
		0xAA1F1EC5, // My Sims dialog (add-sim / details, 695x380 design)
		// v2.22.2 CORRECTION: I-aa1f1f57 has NINE top-level roots, not three.
		// v2.22.0 covered the CATALOG side only and left the whole DETAIL side
		// 1x while its marker-glued siblings went 2x - the same tear-apart the
		// deferral itself caused. 0xABBAA2D3 even ships winflag_visible=yes, so
		// the generic sweep was already doubling it against 1x art.
		0xEA1F1E4D, // Sim detail / news strip (hosts AdviceList 0xAA1F1EB5)
		0x6A61E29F, // Sim detail / profile strip
		0xABBAA2D3, // Sim detail / actions strip (visible=yes in the .UI)
		0xEA1F1E4E, // find-sim overlay
		0xEA1F1E5E, // evict confirm (v2.22.3: the ninth root, last one out)
		// ====== v2.22.4: THE MODE-TRANSITION FLASH FIX (task #50) ==========
		// User: "our biggest issue... everything from God Mode to Mayor Mode
		// to My Sims flashes the old unscaled menus for a split second".
		//
		// MEASURED MECHANISM (not inferred): IncrementalPass already runs
		// EVERY tick (~16ms, see TickCheck) - so the flash is NOT sweep
		// latency. It is the VISIBILITY GATE in ScalePanelsUnder: a panel
		// that is hidden is skipped, so a panel that spends city-load hidden
		// is still 1x when a mode switch shows it. It paints 1x, and only the
		// NEXT tick scales it. That is the flash, and it is why it appears on
		// "almost every field we've touched": every panel we scale is hidden
		// in some other mode.
		//
		// THE FIX IS THE ONE ALREADY PROVEN FOUR TIMES (news reader, budget
		// popups, advisors, region flyouts): pre-scale while HIDDEN so the
		// window is BORN 2x and the first paint is already correct. The
		// principled rule, which also keeps art and runtime coupled:
		//   IF WE SHIP 2x ART FOR A PANEL, IT MUST BE PRE-SCALED WHILE HIDDEN.
		// Every id below is already in SCALED_WINDOW_IDS (2x art ships for
		// it) and is already scaled by this same code path when visible - so
		// this changes only the TIMING, never the geometry. That is what
		// makes it safe: it is not new scaling, it is earlier scaling.
		//
		// NOT paint suppression - FlashGuard stays 0 forever (it blanked HUD
		// windows). Fix the timing, never the painting.
		0xC991EDA8, // god toolbar cluster (both twin scripts)
		0x69E40A1F, // mayor toolbar column
		0x0A78827A, // god-mode panel (founded city)
		0xE9889775, // composite status panel
		0x0987B48F, // HUD dock / minimap cluster
		0xEA8CAD14, // mode-transition overlay (the literal transition window)
		0x6A64E3C0, // opinion polls
		0xCA2AEDC0, // news ticker strip
		0xAA32BCE6, // Data Views panel
		0xAA3AC000, // budget compact bar
		0xAA3AC001, // budget expanded
		0x8A8B5B71, // graphs/data panel root A
		0x8A8B5B72, // graphs/data panel MIDDLE root (v2.22.3 art fix)
		0x0A4A8176, // graphs/data panel root C
		0xC98F49F1, // city panel variant
		// Not listed: 0x699306ED (civic) and 0xCA35CBED (terrain-fx / day-night).
		// Each is covered by its own mechanism (kMayorFlyoutDock / kGodFlyoutDock)
		// and is skipped earlier in the loop. #95 phase 4, REGRESSION.md [CC-11].
		0x4BCB938A, // U-Drive-It dashboard console (43 vehicle scripts)
		0xABB26B0E, // Sim-mode left sidebar
		// #90 (v2.42.0): ships 2x art (SCALED_WINDOW_IDS) but had NO
		// born-correct route - the only one of the 50, caught by the audit
		// and now guarded by _tests\Test-BornCorrectCoverage.ps1. The gen-2
		// precondition is MEASURED, not assumed: both golden dumps show it
		// resident as a direct view child from city load, pos(489,894)
		// 532x640 vis=0 (live script = CoriBoom's 36-slot 532x640, not stock
		// 531x406; the #44 ThirdPartyUI gate still governs which art ships).
		// Opened by button 0xABC54125 on composite 0xE9889775. The panel
		// carries open #58 - this changes its birth timing, so #58 must be
		// re-measured AFTER this, never from pre-v2.42.0 captures.
		0xABC619D2, // Building Style Control
		// #93 (v2.48.1): the console variant, added ONLY after its first
		// live sighting - v2.48.0's UDVAR probe fired on its first outing
		// and reported the fix NOT working, which is the whole reason the
		// probe printed 2x-vs-1x instead of just "seen":
		//   UDVAR 0xEC1A5CBF rel(968,1468) 463x132 vis=0 par=0x9A47B417
		//   SIBLING of the dashboard ... still 1x - insurance did NOT take
		// THREE THINGS THAT MEASUREMENT SETTLED:
		//  1. It EXISTS. No dump had ever contained it.
		//  2. NOTHING SPAWNS IT. The task said "identify which vehicle
		//     spawns it"; it was vis=0 at BOTH sightings across a session
		//     of driving, parented to the VIEW ROOT 0x9A47B417 - it is a
		//     RESIDENT HIDDEN window sitting in the console slot at the
		//     screen bottom (y 1468..1600), not a spawned one. Premise
		//     refuted; the answer is "no vehicle".
		//  3. Its child is 2x in DATA (v2.48.0) but the root stayed 1x,
		//     because the city sweep SKIPS vis=0 windows - only this list
		//     grants the visibility exception. So v2.48.0 shipped a HALF
		//     state: 2x child inside a 1x root. This line is the other half.
		// Exactly the #90 shape and the same cure (0xABC619D2 above was
		// also resident vis=0 from load), and the pre-scale-while-hidden
		// law: scale it while it is hidden so it can never flash.
		0xEC1A5CBF, // U-Drive-It console VARIANT (resident, vis=0, 463x132)
	};
	inline bool IsAlwaysScaleCityId(uint32_t id)
	{
		return IdIn(kAlwaysScaleCityIds, id);
	}
	// DATA-PRE-SCALED SUBTREES (task #43, v2.20.0): scale the ROOT at runtime
	// (so its HUD edge-anchoring keeps working at any resolution) but NEVER
	// recurse - the children ship already scaled inside the .UI script
	// (build_selective_safe.py double_subtree_areas).
	//
	// Advisor strip only. Its 7 faces are LIVE 3D head renders, and the game
	// frames each head ONCE when it binds it to its viewport window - during
	// CITY LOAD, before our first sweep. Runtime doubling was therefore
	// always too late: the heads stayed framed for 1x buttons (quarter-zoomed
	// faces) until an advisor view switch re-bound them. Pre-scaled data
	// means the buttons are already 2x AT BIND TIME. Verified exact: every
	// child's live 2x geometry equals 2 x its design area.
	const uint32_t kDataScaledSubtreeIds[] = {
		0x6A15C767, // Advisors console strip (scripts I-cbc905cd/I-4a160034)
		// GRAPHS panel, all three roots (v2.25.1, 2026-07-30). Log-proven
		// double-scale: the game RE-CREATES a chart child per data refresh
		// (log: "incremental panel 0x8A8B5B71 - 1 windows scaled" every
		// 1-2 s), born at live already-2x size, and the recursing sweep
		// doubled it again - the 4x canvas was the off-screen white sheet
		// and the radio columns sat at 4x offsets. Children now ship BORN
		// 2x in the data (double_subtree_areas on I-6bc9065a/I-ea2871aa in
		// build_selective_safe.py); the sweep scales only the roots, so a
		// game-created child inherits correct 2x metrics and is never
		// touched. Roots' own placement was verified correct in the same
		// log (5b72 = 5b71+(0,604), band = +(10,648)).
		0x8A8B5B71, // Graphs chart root
		0x8A8B5B72, // Graphs lower root
		0x0A4A8176, // Graphs radio band
		// U-DRIVE-IT DASHBOARD (v2.25.14, "duplicate dials"). The gauge
		// pbuffs ([win+0x6c]) are allocated at first paint from the window's
		// then-current size; runtime-sweeping the consoles let the game
		// paint once at 1x first, so every gauge buffer was born 71x71 and
		// the correct 136x120 needle draws CLIPPED into it (the at-rest
		// small top-left dial; GBLT proved all Plot draws are scaled). All
		// 43 console scripts now ship born-2x (double_subtree_areas in
		// build_selective_safe.py); the sweep must stop at the root.
		0x4BCB938A, // U-Drive-It dashboard root (43 console scripts)
		// #93 (v2.48.0): THE FIFTH CONSOLE VARIANT, insured. 0xEC1A5CBF
		// (script I-8c1a5c9f) is a U-Drive-It console root that is NOT in
		// the 43-script family and was in NO list on either side - so it
		// carried the v2.21.0 shape uninsured. MEASURED from the script,
		// not assumed: root area=(18,15,481,147) = 463x132, the exact
		// console-family footprint the builder comments describe, and like
		// them winflag_pbuff=yes.
		// THE MECHANISM, STATED NO STRONGER THAN THE EVIDENCE. The task
		// called this an "uninsured v2.21.0 heap-overrun shape". The ROOT
		// half of that is REFUTED by its own sibling: 0x4BCB938A is also
		// 463x132 and also pbuff, and it has shipped for many versions
		// under exactly this treatment (sweep scales the root), user
		// confirmed. So a swept pbuff ROOT is demonstrably fine. What was
		// genuinely uninsured is narrower: this id was in NO list on EITHER
		// side, so its CHILDREN never got the born-2x data treatment while
		// the sweep would still scale the root - a 2x root over 1x children,
		// which is the clipped-buffer defect the 43 siblings had before
		// v2.25.14 (child pbuffs allocated at first paint from 1x geometry,
		// the correct 2x draws clipping into them).
		// The cure is the one its 43 siblings already have, BOTH HALVES
		// TOGETHER (law 43): born 2x in DATA (added to SCALED_WINDOW_IDS in
		// build_selective_safe.py in the same change) and the runtime sweep
		// STOPS at the root, so it is never rescaled after first paint.
		// INSURANCE, NOT A SIGHTING. No dump in the repo contains this id
		// and no session has logged it, so which vehicle/mode spawns it is
		// still unknown - the UDVAR probe below makes it report itself the
		// first time it ever appears. Listing it is safe under BOTH
		// parentage hypotheses: as a sibling root it gets the full cure; as
		// a child of 0x4BCB938A the sweep already stopped above it and the
		// data doubling merely makes it match its parent instead of sitting
		// 1x inside a 2x console.
		0xEC1A5CBF, // U-Drive-It console VARIANT (I-8c1a5c9f, 463x132 pbuff)
		// v2.25.24: the MONTHLY BUDGET family - a MULTI-ROOT COMPOSED PANEL
		// (Graphs-class, measured): BOTH scripts I-aa3acdfe/I-cbc3c2b9 carry
		// these FOUR top-level roots, composed/anchored by the game at
		// runtime, children re-laid from script-cached geometry. Children
		// are born 2x in data (double_subtree_areas on all four roots in
		// build_selective_safe.py); the sweep scales + anchors each root
		// and never descends. Full static doubling broke the composition
		// ("undocked budget window"); runtime child passes never stuck.
		// #102 COMMENT-ONLY CORRECTION (2026-08-03). The three labels
		// below were wrong and contradicted kAlwaysScaleCityIds above, which
		// calls 0xAA3AC002 the "Taxes editor popup". MEMBERSHIP AND
		// TREATMENT ARE UNCHANGED - only the names.
		// Deciding evidence, in this project's own order of authority:
		//  (a) LIVE, 14 capture runs across 2 dates, identical every time:
		//      "panel 0xAA3AC002 (158,40 500x464) -> (316,80 1000x928)"
		//      (158,40 500x464) is I-cbc3c2b9's declaration TO THE PIXEL;
		//      I-aa3acdfe declares this id 500x202 at the same origin, and
		//      500x202 has NEVER been logged. So the LIVE copy is I-cbc3c2b9.
		//      SCOPED HONESTLY: that loop walks a POINTER snapshot of the 3D
		//      view's direct children and is not id-deduped, so one line = one
		//      such instance - and there is exactly one per run. It says
		//      nothing about instances elsewhere in the tree (cf. the v2.25.20
		//      note below that the budget ids also exist as hidden templates
		//      under the MAIN window). What is measured: the two-SCRIPT corpus
		//      collision does not reach this id-keyed rule.
		//  (b) I-cbc3c2b9's 0xAA3AC002 subtree, read out of the script: first
		//      child GZWinText caption="Taxes", then "Residential"/
		//      "Commercial"/"Industrial Monthly Income" bands with a rate
		//      TextEdit ("20.0") + "%" + spinner on every RCI row, and
		//      0xAA4C353B "Accept" / 0xCA4C352F "Cancel". That is the TAXES
		//      EDITOR, not a "section" of the composed panel. The word
		//      "Income" in its row captions is where the misnomer came from.
		// 0xAA3AC001 is a DIFFERENT window - live 558x505 at (483,1044), 16
		// checkbox+label button pairs (0xAA3AC400..40F / 0xAA3AC500..50F)
		// filled with department names at runtime. The "(Taxes etc.)" that
		// used to sit on that line put the Taxes dialog on the wrong id.
		0xAA3AC002, // Taxes editor popup (LIVE I-cbc3c2b9, 500x464 design)
		0xCA4C332D, // "Take Out A Loan" popup (500x353) - see NOTE below
		0xAA3AC001, // budget expanded / department detail frame (558x505)
		0xAA3AC000, // budget balance bar (833x137)
		// NOTE, stated no stronger than the evidence: 0xCA4C332D carries the
		// identical two-name split ("Take Out A Loan popup" in
		// kAlwaysScaleCityIds and in build_selective_safe.py's
		// SCALED_WINDOW_IDS, vs "expense section" here and in SpinProbe.cpp).
		// #102 did NOT adjudicate it: neither script gives that subtree a
		// caption, so the only tell is its 0x8A4C34D4 spinner defaulting to
		// "$5,000" - suggestive, not decisive. Do not quote either name as
		// settled until a capture or the disassembly says which it is.
		// THE HUD DOCK 0x0987B48F IS **NOT** A MEMBER, AND MUST NEVER BE.
		// v2.41.1 added it and BROKE THE DOCK AND EVERY FLYOUT (reported,
		// same session, reverted in v2.41.2). Membership makes ScalePanelRoot
		// RETURN EARLY at the dock root - and the god/mayor flyout DOCKING
		// logic lives inside that child recursion, so the flyouts lost the
		// machinery that positions them against their spawn buttons.
		// The dock's minimap is instead born 2x as a SINGLE WINDOW; see
		// kDataScaledWindowIds below.
	};
	// THERE IS NO kDataScaledWindowIds, AND THE DOCK MUST NOT GET ONE.
	// v2.41.2 added a single-window form (minimap 0x0BC3B559 born 2x in data,
	// sweep skips just that window, recursion continues) specifically to avoid
	// v2.41.1's flyout breakage. It fixed the flyouts and BROKE THE MINIMAP A
	// DIFFERENT WAY: the dock's rect is the UNION OF ITS CHILDREN WITH NO
	// CLAMP (CITY-DOCK-OVERLAP.md), so a child pre-doubled to (36,144)-(164,272)
	// hangs past the 235x223 design frame, the union grows, and the
	// bottom-anchored dock drags the map outside the window (reported).
	// Both forms reverted in v2.41.3. Any future attempt must answer what the
	// union rect does AT LOAD TIME before touching the data at all.
	// FONT-SIZED CONTROLS (task #44, v2.20.3): a control whose SIZE is computed
	// from its RENDERED CAPTION - by the game or by a mod's DLL - is ALREADY
	// correct once the fonts are 2x, so scaling it again makes it twice too
	// big. MEASURED: SC4MoreBuildingStyles sizes "Change style every" to fit
	// its 2x caption (263x32) and our sweep then doubled that to 526x64, so
	// its radio glyph sat ~16px below the three rows above it while its
	// fixed-size siblings (238x18 -> 476x36) lined up correctly.
	// Scale POSITION only; never touch the size.
	const uint32_t kFontSizedIds[] = {
		0xCBC61559, // "Change style every" (Building Style Control options)
		// The years SPINNER beside it (v2.20.4). Same family, art-derived
		// instead of font-derived: GZWinSpinner sizes itself from its arrow
		// strip {46a006b0,82b99d9d}, which we ship 2x, so it is already the
		// right size - and our extra scaling pushed it to 60x72 inside a
		// parent FlatRect only 98x44, clipping the DOWN arrow off the bottom
		// (user could raise the year count but never lower it). MEASURED:
		// spinner abs(1374,1428) 60x72 vs parent abs(1310,1424) 98x44.
		0xABC61550, // years spinner
		// v2.25.21 (Taxes "crushed arrows"): the BUDGET dialogs' GZWinSpinners
		// - same art-sized law (a spinner sizes itself from its 2x arrow
		// strip {46a006b0,82b99d9d}; doubling it again crushes/clips the
		// arrows, the years-spinner bug at scale). All spinner ids from the
		// two master scripts, corpus-collision-checked: every id below is
		// unique to these scripts EXCEPT 0x00000202, which is ALSO a 271-wide
		// GZWinCombo in I-e9a56248 and is therefore EXCLUDED (that one
		// Neighbor Deals spinner keeps the old behavior; note in checkpoint).
		0xAA3ACB00, 0xAA3ACB01, 0xAA3ACB02, 0xAA3ACB03, 0xAA3ACB04,
		0xAA3ACB05, 0xAA3ACB06, 0xAA3ACB07, 0xAA3ACB08, 0x8A4C34D4,
		0x00000200, 0x00000201, 0x00000203, 0x00000204, 0x00000205,
		0x00000206, 0x00000207, 0x00000208, 0x00000209, 0x0000020A,
		0x0000020B,
	};
	inline bool IsFontSizedId(uint32_t id)
	{
		return IdIn(kFontSizedIds, id);
	}
	inline bool IsDataScaledSubtreeId(uint32_t id)
	{
		return IdIn(kDataScaledSubtreeIds, id);
	}

	// ADVICELIST (cSC4WinAdviceList, clsid 0xca1492ac) windows: scale the
	// window ITSELF, never its children. The class sizes every item it
	// creates to SetArea(0,0,GetW,GetH) of the container (item-create
	// 0x7931F1), so items are born at the already-scaled container size and
	// scaling them again double-scales (the news reader's item ballooned to
	// 1648x708 inside its 824x354 list, v2.18.6). Item TEXT is HTML - scaled
	// by CodePatches::ApplyHtmlSizeScale, not by geometry.
	//
	// v2.19.0 replaces the old ROOT-ONLY rule for the ticker panel
	// 0xCA2AEDC0, which was too broad: it also left the ticker's background
	// BMP and clip strip at 1x (a 676x33 text hole in the 1514x86 ticker).
	const uint32_t kAdviceListScaleSelfIds[] = {
		0x6A231531, // news reader headline list (script I-2a2aed99)
		// Advisor briefing headline lists (scripts I-cbc905cd/I-4a160034,
		// 2026-07-29 late): same cSC4WinAdviceList class - their items are
		// game-sized to the container and must never be recursed into, or
		// they double-scale exactly like the news reader's item did.
		// MY SIMS story lists (v2.22.2). An explicit
		// warning about these two BEFORE v2.22.0 lifted the My Sims deferral,
		// and the lift did not honour it: the sweep recursed into the list and
		// double-scaled its runtime item (the 13-vs-12 window count logged for
		// 0xAA1F1EC5 is that extra item) - a 540x341 design list became
		// 1080x682 with its item at 2160x1364 = the big blank grey area.
		// STRUCTURAL WEAKNESS (noted, not fixed): this guard is keyed on ID,
		// so any NEW clsid 0xCA1492AC window is unprotected by default.
		0xAA1F1EB5, // My Sims detail-strip story list (in 0xEA1F1E4D)
		0x6A1F1F4A, // My Sims expanded-dialog story list (in 0xAA1F1EC5)
		0x00100100, // briefing panel (compact) headline list
		0x00100101, // briefing panel (expanded) headline list
	};
	inline bool IsAdviceListScaleSelfId(uint32_t id)
	{
		return IdIn(kAdviceListScaleSelfIds, id);
	}
	// The ticker MARQUEE is an AdviceList the game re-imposes geometry on
	// EVERY roll tick from values cached at ticker init (0x77258B) - a
	// runtime SetW is undone within a frame (proven live 2026-07-29: one
	// "width 676 -> 1352" apply in the log, 676x90 again in the next dump,
	// so the 2x HTML headline wrapped mid-word). The scaled width ships in
	// the EDITED .UI script instead (SelectiveArt I-2a2aed99: marquee design
	// area width x factor - the init cache then STARTS scaled); the height
	// is font-derived (3 x lineHeight of the 2x AdvisorHeadline), and the
	// items are game-sized to the marquee. So at runtime: NEVER touch,
	// NEVER recurse.
	const uint32_t kAdviceListNeverTouchIds[] = {
		0xAA12F33C, // ticker marquee (child of clip strip 0xCA2AEEC0)
	};
	inline bool IsAdviceListNeverTouchId(uint32_t id)
	{
		return IdIn(kAdviceListNeverTouchIds, id);
	}

	// ---- #101 v2.56.0: THE CITY BOTTOM-HUD CO-ANCHOR ---------------------
	// ScalePanelRoot's generic anchor picks its branch by comparing a
	// FRAME-INDEPENDENT design gap against a FRAME-RELATIVE threshold
	// (frameW/4). MEASURED, not assumed: the game leaves this cluster at a
	// fixed design x - 0xE9889775 reports l=139 and 0x6A64E3C0 reports l=501
	// in BOTH the 1400x1050 capture and the 2400x1600 capture; only t moves,
	// because the game bottom-anchors. So the branch a panel gets depends on
	// the MONITOR, not on the panel: at any render width in 1386..2003 the
	// polls panel crossed frameW/4 and flipped to the f-free CENTER law while
	// the composite it RIDES ON stayed EDGE-L. Measured shear -256px at
	// 1400x1050; -385px at 1920x1080, which is the mainstream 1.5x
	// resolution. The polls panel then painted over the RCI meter and the
	// entire button column, and Graphs could not be opened at all.
	//
	// Cure = what this file's own anchor comment already promises: "both must
	// transform identically for their relative layout to survive". The family
	// co-anchors off ONE leader, so relative layout is exactly x f at every
	// frame width and the branch heuristic never gets a vote.
	//
	// TWO CONSTANTS, BOTH FROM ONE WINDOW (so `python tools\sdk\lookup.py
	// 0xE9889775` verifies the whole table): design l = 139, and design right
	// edge = 139 + 880 = 1019 where 880x180 is the .UI root of the LIVE
	// declaring script T-00000000_G-96a006b0_I-2bc90671.ui. That the LIVE
	// script is 2bc90671 and not the other 880-wide variant 898897de is
	// MEASURED from three of its children: at f=1.5 with the composite at
	// x=80 this script predicts 0xAA9211B3 abs(464,793) 63x177 and
	// 0x09D27EB0 abs(475,853) 12x107, and the log's DPROBE prints exactly
	// those. 898897de predicts 407/417 and is refuted.
	const int32_t kCityHudLeaderL = 139;
	const int32_t kCityHudLeaderR = 1019;

	// Every city root the game places at a frame-independent design x on the
	// dashboard row. MEASURED membership: each id below reports the SAME
	// design l in the 1400x1050 capture and in the 2400x1600 capture. The
	// leader is a member of its own family, so its own x is unchanged by
	// definition - nothing that docks against it (the minimap cluster) moves.
	const uint32_t kCityHudFamilyIds[] = {
		0xE9889775, // composite status HUD  <-- LEADER (design l 139)
		0x698894D3, // My Sims outer root                          139
		0xCA1F1D9C, // My Sims content panel                       149
		0xEA1F1E4E, // find-sim overlay                            153
		0xEA1F1E4D, // Sim detail / news strip                     195
		0x6A15C767, // Advisors console strip                      209
		0xAA15EF06, // advisor briefing (compact)                  209
		0xAA3AC000, // budget compact bar                          210
		0xC98F49F1, // city panel variant                          232
		0xCA2AEDC0, // news ticker strip                           232
		0xAA1F1EC5, // My Sims dialog                              263
		0xABBAA2D3, // Sim actions strip                           321
		0x6A61E29F, // Sim profile strip                           321
		0x2A1D96B1, // advisor briefing (expanded)                 482
		0xAA3AC001, // budget expanded                             483
		0xABC619D2, // Building Style Control  489 - 1.5x capture ONLY. Its
		            // 2x placement is a MODEL prediction (978 = the generic
		            // law's own EDGE-L output at 2400), never observed.
		0xAA32BCE6, // Data Views panel                            494
		0x0A4A8176, // graphs/data root C                          494
		0x8A8B5B71, // graphs/data root A                          495
		0x8A8B5B72, // graphs/data MIDDLE root                     495
		0x6A64E3C0, // City Opinion Polls                          501
	};
	inline bool IsCityHudFamilyId(uint32_t id)
	{
		return IdIn(kCityHudFamilyIds, id);
	}

	// The three cSC4WinRCI demand columns, logged by the RCI diagnostics
	// at city init and again ~30 s later (one table, audit B9).
	const uint32_t kRciColumnIds[] = { 0x09D27EB0, 0x29D27EC0, 0x49D27ED0 };
}
