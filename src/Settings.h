#pragma once
#include <cstdint>

// All values are read once at startup from the DLL's ini file beside it
// (SC4UIScale.ini). Missing keys keep the defaults below.
struct Settings
{
	// Input-layer settings that used to live in this struct were
	// REMOVED 2026-08-06. They belonged to a different plugin that once shared
	// this struct; this DLL parsed them and consumed none of them. Dead config
	// is not harmless - it documents keys that do nothing, and it made a
	// UI-scaling project look like it owned an input layer it does not.

	// [Scaling] - input remap for wrapper-scaled rendering (dgVoodoo presents
	// the game's small internal frame upscaled to the physical panel; exactly
	// one owner of the coordinate transform: this DLL).
	bool scalingEnabled = true;       // master switch for the remap layer
	// INERT (audited v2.69.0): the next four are parsed from the ini and then
	// read by nothing - ScaleRemap derives the present rect from the client
	// rect and the internal size from SC4GraphicsOptions.ini. They are kept
	// only so an existing user ini does not warn on unknown keys, and they MUST
	// NOT appear in the shipped ini: a documented key that does nothing is a
	// lie to the player.
	bool scalingAutoConfig = true;    // INERT - no consumer
	int internalWidth = 0;            // 0 = read from SC4GraphicsOptions.ini
	int internalHeight = 0;
	int presentWidth = 0;             // INERT - no consumer
	int presentHeight = 0;            // INERT - no consumer
	bool hookGetCursorPos = true;     // per-hook bisection toggles
	bool hookSetCursorPos = true;
	bool hookClipCursor = true;
	bool hookWindowMetrics = true;    // GetSystemMetrics/GetDeviceCaps/rect lies - REQUIRED: the game's
	                                  // UI compositor sizes surfaces from screen metrics (corrupts without)
	bool logCoordTraffic = false;     // verbose transform tracing

	// [UiSpike] - research spike toward runtime UI-element scaling
	bool spikeDumpTree = false;       // dump the cIGZWin tree at city init
	unsigned int spikeLiveDumpMs = 0; // >0: while in a city, every N ms dump
	                                  // each VISIBLE direct child of the 3D
	                                  // view + its subtree (geometry+vis), so
	                                  // an open query/tool panel is captured
	                                  // live. Diagnostic only; 0 = off.
	unsigned int spikeScaleWindowId = 0; // window ID (hex ok) to resize; 0 = off
	float spikeScaleFactor = 2.0f;    // resize factor for the chosen window
	bool spikeScaleAll = false;       // geometry-first: scale EVERY city-view
	                                  // panel subtree and re-anchor it to its
	                                  // nearest screen edge (art unchanged)
	bool spikeScaleRegion = false;    // extend ScaleAll to the region screen
	                                  // (host 0xEA659793 cSC4WinRegionScreen;
	                                  // timer-polled - no city message fires
	                                  // on the region). 
	                                  // this said 0x2AAB8CC1 for weeks, which
	                                  // is the TOOLTIP layer, not the region.
	// #131: region-map camera scale. The region TERRAIN is renderer-drawn at a
	// fixed 98 px per region cell regardless of resolution, so at 3x it holds
	// a third of the screen fraction it holds at stock and the city tiles get
	// too small to click. <0 = follow the UI tier factor (the default), 0 =
	// leave the region map stock, >0 = explicit multiplier on the game's own
	// 0.25 camera scale. Only consulted when ScaleRegion=1.
	float spikeRegionMapScale = -1.0f;
	// #132 region ZOOM (mouse wheel on the region screen). The region has no
	// camera - a full decompile of the module finds zero zoom/rotate/angle
	// references - so this drives #131's own levers: the isometric basis and
	// the tile-rebuild hook. ROTATION is NOT offered: the tiles are bitmaps
	// baked at a fixed angle when each city was last saved, so rotating would
	// need every thumbnail re-rendered, which only the city view can do.
	// v2.82.0-.2 CRASHED THE GAME TWICE and this key was default-off until
	// v2.83.0. Keep the history: it is the reason the mechanism looks the way
	// it does. Two ACCESS_VIOLATIONs at 0x0082653B (inside GetPixel, which has
	// NO bounds check), both with ESI = 0x00AC1400 and EBP = the ORIGINAL 260px
	// tile width, the second one on MOUSE MOVE i.e. during hit-testing.
	//
	// CAUSE: a region item owns FOUR source bitmaps (+0x1C, +0x20 alpha,
	// +0x24/+0x28) plus the composite (+0x2C), plus THREE derived run lists -
	// +0x44 (the CLICK MASK), +0x50, +0x5C - and the screen-blit list +0x38.
	// The mask is built from [+0x20] by sub_7AD400 INSIDE sub_7AE510's rebuild
	// and is never regenerated otherwise, so resizing a subset leaves the rest
	// describing the old size and the blit/hit-test walk off the end. Clearing
	// byte[+0x34] regenerates the run list but NOT the mask: there is no
	// in-place sequence that leaves all of them consistent.
	//
	// v2.83.0 does what #131 does - changes the factor and lets the GAME
	// rebuild through sub_7AE510, which regenerates every buffer AND the mask
	// coherently. A zoom TRIGGERS A REBUILD; it never resizes anything.
	// Requires the sub_7AE510 snapshot hook, installed at PostAppInit, without
	// which a rebuild would compound the tiles and crash on the null mask that
	// sub_7B13C0 leaves behind.
	bool spikeRegionZoom = true;
	// DISCRETE LEVELS, not a free range. Each level multiplies the base factor
	// by RegionZoomStepRatio; you get RegionZoomLevels steps in EACH direction
	// and no more. 2 levels x 1.25 => base/1.5625 .. base*1.5625.
	//
	// WHY LIMITS EXIST: a rebuild is 8-10 full-image passes PER ITEM, two of
	// them ~3 virtual calls per pixel and two more one unreserved vector insert
	// per opaque pixel - and BOTH cost and memory are QUADRATIC in the factor.
	// The user FROZE the game by scrolling fast (2026-08-05). Levels bound the
	// size; the settle debounce (kRegionZoomSettleMs) bounds the RATE.
	//
	// 5 each way (v2.85.0, was 2). The two directions are NOT symmetric in
	// cost, which is why one number is generous: a level below the base costs
	// a QUARTER the pixels of one above it, so zoom-out is nearly free while
	// zoom-in is bounded by the byte budget. MEASURED on a 48-city region,
	// pristine tile 260x160: +2 = 149 MB, +3 = 233 MB, +4 = 363 MB. Levels
	// that do not fit are refused WHOLE and logged, and the level counter
	// holds - so the player simply feels a stop, exactly like the range end.
	int spikeRegionZoomLevels = 5;        // steps each way from the base
	float spikeRegionZoomStepRatio = 1.25f;
	// Hard ceiling on a single tile bitmap edge. A step that would put ANY tile
	// past this is refused whole - half the map at the wrong scale is worse
	// than no zoom.
	int spikeRegionZoomMaxEdge = 2048;
	// #131b: neutralise the game's tent filter over region tiles and re-apply
	// its sub-pixel alignment in DEST space instead. Measured worth up to 2.5
	// screen px of smear at zoom (81% blend at f=3.125) and ~0.4 px unzoomed,
	// so it is close to a no-op at the base tier and does its work exactly
	// where the softness was reported. 0 restores v2.83.1 byte-for-byte.
	bool spikeRegionTileSharp = true;
	bool spikeMenuFlyouts = false;    // scale transient flyouts appearing
	                                  // under the menu container 0xAA32BCE6;
	                                  // the container + baseline strip are
	                                  // never touched
	bool spikeCenterSmallLeaves = false; // GLOBAL: small leaf windows keep
	                                  // their 1x size, centered in the 2x
	                                  // slot (for 1x art that cannot grow);
	                                  // flyout scaling always does this
	int spikeCenterLeafMaxPx = 48;    // "small" threshold (original W and H)
	bool useScaleRemap = false;       // ScaleRemap = the REJECTED whole-frame
	                                  // approach (internal!=present metric
	                                  // lies). Default OFF: the game renders
	                                  // at its TRUE resolution, the UI scaler
	                                  // enlarges elements, dgVoodoo presents
	                                  // the frame. Active ScaleRemap garbles
	                                  // (proven 1600x1200: giant blurry UI).
	bool spikeAutoScale = true;       // pick the scale factor from the
	                                  // resolution via the ScaleTier fit
	                                  // function (and enable/stash the
	                                  // static data layers to match); 0 =
	                                  // manual ScaleFactor, layers untouched
	// IN-GAME SCALE SELECTOR at the STOCK tier (2026-08-19). The selector
	// itself always ships; this key decides whether the stock tier installs a
	// tick source to service it.
	//   1 (default) - 1x keeps the Graphic Options selector, so the player can
	//                 climb back to a scaled tier without editing an ini. The
	//                 subclass + WM_TIMER are the ONLY things installed, and
	//                 the timer body services the dialog and nothing else.
	//   0           - the pre-existing absolute isolation: no window attach,
	//                 no subclass, no timer, indistinguishable from a no-DLL
	//                 install. This is what a stock REFERENCE CAPTURE needs,
	//                 and Set-Tier.ps1 -Tier 1 writes it.
	// The two ways of arriving at 1x want opposite things; the key is how they
	// say which one they are.
	bool spikeSelectorAtStock = true;
	bool spikeRatingArrowPatch = true; // byte-patch the Mayor-rating arrow
	// v2.76.0: ARMED (2). The log-only run ADJUDICATED the model - the player's
	// 3x capture shows the arrow at L/T=(294,174) while its cached seat is
	// (98,58), i.e. EXACTLY cached*3, and it alternates with correct (98,58)
	// fires. So the detached case is the game re-seating from the pre-sweep
	// cache and our sweep having already scaled the container: the arrow lands
	// at f x its own correct seat. Writing the cached seat back is the fix, and
	// the detour computes no coordinates of its own. Still no-op below f=2.5.
	int spikeRatingArrowAnchor = 2;   // 0 = off, 1 = log only, 2 = log + fix
	                                  // adversarial verifier - one 3x run
	                                  // adjudicates the model, then flip the
	                                  // ini key RatingArrowAnchor=2 to arm.   // #130 decline-arrow anchor: 0 = off,
	                                  // 1 = log only (inert at ANY tier, use
	                                  // it to measure 2x without changing it),
	                                  // 2 = log + re-anchor, which the
	                                  // installer itself refuses below factor
	                                  // 2.5 so the 2x tier installs nothing
	int spikeMissionBubbleFx = 2;      // #188 U-Drive-It start bubbles:
	                                   // 0 = off, 1 = log only, 2 = log +
	                                   // scale (signpost imms + effect
	                                   // instances), 3 = 2 + live SPPROBE
	                                   // draw-path diagnosis (dev only)
	float spikeMissionBubbleScale = 0.0f; // #188: <= 0 = follow the tier
	                                   // factor; > 0 = literal multiplier
	                                   // (1.0 = stock size; must be <= 8).
	                                   // ONE knob for the whole feature: it
	                                   // scales the signpost balloon quad
	                                   // (and the police/fire dispatch
	                                   // signs that share it) AND the
	                                   // in-mission target glow.
	bool spikeTooltipWrapPatch = true; // byte-patch the tooltip 250px wrap
	                                   // width to 250*factor (task #41)
	bool spikeParentFrameRounding = true; // #161: round a child's edges in its
	                                  // PARENT's absolute design frame so a
	                                  // child edge that equals the parent's
	                                  // extent lands on it. 0 restores the
	                                  // pre-#161 local-origin rounding - the
	                                  // revert path for a change that touches
	                                  // EVERY scaled child at fractional tiers.
	bool spikeCostBoxPatch = true;    // byte-patch the placement cost readout's
	                                  // 128x32 runtime buffer to 128f x 32f so
	                                  // scaled glyphs are not rasterised
	                                  // clipped (#159). Separate from the
	                                  // tooltip wrap: different constant,
	                                  // different subsystem.
	bool spikeHtmlSizePatch = true;   // scale the HTML engine's two .rdata
	                                  // font-size tables (SIZE=1..7 + H1..H7)
	                                  // by the factor and retarget the message
	                                  // popup style GUIDs (task #42 news text)
	                                  // reveal (hardcoded 7px/point) to match
	                                  // the 2x face art; verify-before-write,
	                                  // skipped silently on byte mismatch
	bool spikeAdviceRowPatch = true;  // rewrite the advice/news row column
	                                  // budget at 0x0079388F so a 2x arrow
	                                  // glyph does not push the dismiss X off
	                                  // the row (task #88)
	                                  // WARNING - NOT A SAFE KILL SWITCH. The
	                                  // 2x row glyphs are DATA in the
	                                  // SelectiveArt package. Setting this to
	                                  // 0 while they are staged REPRODUCES the
	                                  // missing X; that is its only diagnostic
	                                  // value. The real revert is a data
	                                  // rebuild -
	bool spikeBudgetButtonPatch = true; // byte-patch the budget detail-dialog
	                                  // Accept/Cancel builders (5 departments):
	                                  // SetSize(180,30) + anchors W-195/H-40
	                                  // scale by the factor
	bool spikeOrdinanceInsetPatch = true; // byte-patch the Ordinances builder's
	                                  // left-column x consts (18/34) by the
	                                  // factor so 2x icons clear the text
	bool spikeBudgetDeptPatch = true; // byte-patch the slider-department
	                                  // builder's column consts + the
	                                  // Business Deals empty box
	int  spikeSpinFix = 1;            // #104 THE FIX, default ON. When the
	                                  // sampler MEASURES the shutdown spin,
	                                  // make the stuck child list report empty
	                                  // (two 4-byte writes, no game code
	                                  // called) so ChildDeleteAll can return.
	                                  // Requires SpinProbe > 0 to detect it.
	bool webRedirect = true;          // v2.69.0: the dead-link fix installs a
	                                  // PROCESS-WIDE ShellExecuteA/W hook. It is
	                                  // the one thing this DLL does that is not
	                                  // scaling, it runs at EVERY tier including
	                                  // stock, and until now it had no off
	                                  // switch. Default on (the EA URL really is
	                                  // dead); [UiSpike] WebRedirect=0 declines it.
	int  spikeSpinProbe = 0;          // task #105, PROBE not a fix, default OFF.
	                                  // >0: after PreAppShutdown returns, sample
	                                  // every other thread's EIP at 20Hz for this
	                                  // many seconds and log a histogram. #104's
	                                  // spin starts exactly there, so a hot EIP
	                                  // NAMES the loop instead of us deducing it.
	int  spikeSubFlyoutBorn2x = 0;    // task #50: build nested sub-flyouts at
	                                  // round(stock*f) so their PAINT BUFFER is
	                                  // allocated correct on Plot #1 (the flash
	                                  // is the buffer, not the sweep). Fuses the
	                                  // constant patch AND neutralising our own
	                                  // runtime doubling - neither half is
	                                  // shippable alone. 0 = off (escape hatch)
	int  spikeSubFlyoutBornScale = 1; // v2.36.0 task #50: scale the nested
	                                  // sub-flyout's FINISHED rects in a
	                                  // detour on its Place (0x0079AD00), so
	                                  // the first paint is already correct.
	                                  // Same arithmetic as the sweep, one tick
	                                  // earlier - NOT the dead constants path
	                                  // above. 0 = off (escape hatch)
	int  spikeSubFlyoutBornDock = 1;  // dock it at birth too: the sweep can
	                                  // only dock one tick AFTER it scales
	                                  // (its law needs a ring blit at the new
	                                  // size), which is the second settle.
	                                  // 0 = size at birth, dock via the sweep
	int  spikeRestoreToolbarsPatch = 1; // v4.5.3: the button that brings the
	                                  // HUD back is sized by its own art
	                                  // strip (which we enlarge) but placed
	                                  // by two 1x constants, so it is born
	                                  // below the screen edge at every scaled
	                                  // tier - +10 px at 2x, measured. Fixes
	                                  // the origin at the source and stands
	                                  // the panel sweep down on it. 0 leaves
	                                  // both halves off together.
	int  spikeDataViewLegendPatch = 1; // v2.37.0 task #78: scale the Data
	                                  // Views legend ORIGINS inside the
	                                  // game's own re-lay (sub_007A04F0) so
	                                  // the legend is born correct on every
	                                  // view selection instead of being
	                                  // pinned back a tick later. Also stands
	                                  // the DVPIN table down, which is what
	                                  // stops it flattening a wrapped label's
	                                  // taller row. 0 = off (escape hatch:
	                                  // reverts to the v2.36 pin behaviour)
	int  spikeFlyoutBornOnOpen = 1;   // v2.36.1 task #50: run the god/mayor
	                                  // flyout pass at the instant a tool
	                                  // flyout is opened (hook on the single
	                                  // opener sub_7E5C10) instead of on the
	                                  // next sweep tick. Same pass, earlier -
	                                  // it is idempotent via scaleMap.
	                                  // 0 = off (escape hatch)
	int  spikeShowHook = 1;           // v2.32.0 task #50: scale a subtree the
	                                  // instant the game shows it, before its
	                                  // first paint. 0=off 1=log only 2=scale
	                                  // REFUTED for the city HUD (task #89,
	                                  // measured): cGZWin::SetFlag fires only on
	                                  // a 0->1 transition and HUD windows are
	                                  // BORN visible, so mode 2 never sees them
	int  spikeEarlyDock = 1;          // v2.41.17 task #89: scale the dock from
	                                  // inside the cGZWin::SetFlag detour once
	                                  // its subtree has STOPPED CHANGING, so it
	                                  // is never painted at 1x.
	                                  //   0 = off
	                                  //   1 = LOG ONLY - report exactly when it
	                                  //       WOULD scale (SHIPPING DEFAULT)
	                                  //   2 = actually scale
	                                  //
	                                  // WHY THIS SITE, when two others failed:
	                                  // the message queue is dead (the game does
	                                  // not pump during the load tail) and
	                                  // mutating geometry INSIDE PostCityInit
	                                  // crashed (v2.41.15). SetFlag is neither:
	                                  // it fires constantly on the GAME'S OWN
	                                  // stack, and - crucially - it keeps firing
	                                  // AFTER city init has finished, so we can
	                                  // wait for the tree to settle instead of
	                                  // racing it.
	                                  //
	                                  // The gate is the SAME stability test
	                                  // RegionWatchTick already uses: act only
	                                  // after the dock's child count is
	                                  // unchanged across consecutive checks, so
	                                  // we never touch a half-built subtree -
	                                  // which is the most likely shape of the
	                                  // v2.41.15 crash.
	                                  //
	                                  // Ships at 1 ON PURPOSE (law 38: an
	                                  // escape hatch is not a safe default).
	                                  // Read the EARLYDOCK lines, THEN set 2.
	int  spikeEarlyBake = 1;          // 0 = off, 1 = bake flags only (SHIPPING
	                                  // DEFAULT), 2 = flags + scale the dock at
	                                  // PostCityInit.
	                                  //
	                                  // MODE 2 CRASHED AT CITY OPEN on its
	                                  // first run (v2.41.15, 2026-08-01,
	                                  // reported). It shipped defaulted to
	                                  // 2, which would have crashed anyone
	                                  // without the ini key - the ini protected
	                                  // one machine, not the product. Default
	                                  // is 1 and mode 2 stays OFF until a
	                                  // different approach exists.
	                                  //
	                                  // WHAT THE CRASH DISPROVED - my reasoning,
	                                  // not the game's: I argued mode 2 was safe
	                                  // because the PostCityInit ban is about
	                                  // the 456-window FULL WALK and this was
	                                  // one subtree of ~25. Wrong. The log shows
	                                  // the early scale AND the whole later
	                                  // sweep completing ("ScaleAll done, 431
	                                  // windows" - 25 fewer, so scaleMap's
	                                  // idempotence worked exactly as designed)
	                                  // and the process died after. So the
	                                  // threshold is NOT window count: two byte
	                                  // writes are safe here, 25 geometry
	                                  // mutations are not. MUTATING WINDOW
	                                  // GEOMETRY during city init is
	                                  // categorically different from writing
	                                  // flags, at any size.
	                                  //
	                                  // v2.41.10 task #89: at PostCityInit, ask
	                                  // the DOCK MINIMAP to re-bake, by setting
	                                  // its two dirty bytes [+0xFD]/[+0xFE] and
	                                  // calling InvalidateSelf. 0 = off.
	                                  //
	                                  // WHY: the bake runs from 0x7A8640, which
	                                  // is driven by the GAME'S OWN message
	                                  // server (ids 0x99EF1142/0x99EF1143) -
	                                  // NOT the Windows queue. Measured before
	                                  // our sweep: raster blank grey, fd=0
	                                  // fe=0, i.e. no re-bake is even pending,
	                                  // while the surface still shows pre-bake
	                                  // content. Setting the flags this early
	                                  // lets the bake happen on an internal
	                                  // message during load, before reveal.
	                                  //
	                                  // THIS RUNS INSIDE PostCityInit, which
	                                  // is the region carrying the hang lesson.
	                                  // It is deliberately TINY: two scoped
	                                  // lookups, two byte writes, one
	                                  // InvalidateSelf. NO tree walk, NO
	                                  // scaling, NO surface work. If the game
	                                  // ever hangs at city open, set this to 0
	                                  // and it is fully inert.
	// NO EarlyPass KEY - the posted-WM_APP channel was built, MEASURED and
	// REVERTED on 2026-08-01 (task #89, v2.41.0). It beat WM_TIMER by 15ms
	// (+2016ms vs +2031ms after arm): ONE timer period. The game does not pump
	// messages AT ALL during the city load tail, so there is no queue to jump
	// and EVERY message-queue lever is dead - WM_TIMER tuning, ShowHook, and
	// WM_APP alike. Do not re-derive this.
	bool spikePopupWrap = true;       // wrap the ordinance/deal description
	                                  // ourselves (cIGZFont) - the engine
	                                  // lays that text out once, at creation,
	                                  // against an unscaled 1000px bound
	bool spikeDockDialogs = false;    // EXPERIMENTAL runtime region-dialog
	                                  // scale+dock; malforms list/slider
	                                  // dialogs (proven) - static .UI scaling
	                                  // is the shipping path

	// [Logging]
	int logLevel = 1; // 0 = error, 1 = info, 2 = debug, 3 = trace

	void Load(const wchar_t* iniPath);
};
