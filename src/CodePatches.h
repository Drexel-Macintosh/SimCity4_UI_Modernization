#pragma once

// Targeted byte patches into SimCity 4.exe (1.1.641) for controls whose
// geometry is hardcoded in the drawing code and unreachable through the
// cIGZWin tree or data files. Every site is byte-verified before writing;
// a mismatch (wrong exe build) skips that patch with a log line.
namespace CodePatches
{
	// Mayor-rating change-arrows: the HUD controller reveals arrow art by
	// SetW(delta * 7) - 7px per rating point at three imul sites
	// (DYNAMIC-CONTROLS.md). With 2x face/arrow art the multiplier must
	// scale identically or the clip reveals half the arrows.
	void ApplyRatingArrowScale(float factor);
	// Tooltip 250px hardcoded wrap width -> 250*factor (tip layer Plot
	// 0x798710, two `push 0xfa` sites). Verify-before-write; skips itself
	// on any unexpected exe bytes.
	void ApplyTooltipWrapScale(float factor);

	// #159: the placement cost readout is rasterised into a 128x32 runtime
	// buffer sized for the 1x font, so scaled glyphs are clipped before any
	// draw hook can see them. Scales that buffer at its Init (0x007EEF59).
	void ApplyCostBoxScale(float factor);
	// Intro video surface (#138). cSC4WinIntroVideoScreen::Init (0x0079CFE0)
	// hardcodes a 768x384 centred window, so the clip is a postage stamp at
	// high resolutions. Scales the two SetArea operands and the two centring
	// subtrahends (all imm32, verify-before-write). Returns the number of
	// sites patched (0..4).
	// MUST be called from the EARLY tier block, NOT PostAppInit - the game
	// creates the video screen during app-init, ~16s before PostAppInit runs.
	int ApplyIntroVideoScale(float factor);
	// News/rich-text (task #42): every news surface (ticker, reader
	// headlines, story pages, message popups, tutorials) renders through the
	// game's HTML engine, whose SIZE=1..7 / H1..H7 indexes resolve via two
	// .rdata point-size tables that FontStyle.ini never reaches. Scales both
	// tables in place (each rich window COPIES them at creation - setter
	// 0x8FEEB8 - so patching at PostAppInit reaches every instance) and
	// retargets the message-popup builders' MessageHeader/Body style GUIDs
	// at stock-size clones so their derived indexes are not double-scaled.
	void ApplyHtmlSizeScale(float factor);
	// Advice/news row column budget (task #88). Every advice list in the
	// game - news reader, advisor briefings, My Sims stories, the briefing
	// panels and the ticker marquee - has its rows emitted by ONE function,
	// cSC4WinAdviceList::Refresh (0x00793810), as a three-column HTML table
	// [arrow | headline | dismiss-X] whose middle column is GetW() - 61 and
	// whose two glyph columns are hard-coded 18. The row glyphs are <IMG>
	// tags with no declared size, so 2x art grows the arrow column and
	// pushes the X cell past the pane's content edge - the control vanishes.
	// Rewrites the subtrahend to round(18*f) + 43 so the row's declared
	// total returns to the stock GetW() - 25 with the extra width taken out
	// of the HEADLINE column instead.
	// PRECONDITION CONTRACT: this patch and the twelve staged glyphs
	// {46a006b0, 0x1441625x with (i & 3) != 3} are one change. NEVER ship
	// the art without the patch - that combination is exactly the bug.
	// Returns 1 if the site took, 0 if it was skipped (see the log line).
	int ApplyAdviceRowScale(float factor);
	// Budget detail-dialog Accept/Cancel buttons (2026-07-30): the five
	// department builders hardcode SetSize(180,30) and anchors x=W-195 /
	// y=H-40 while the frame content-fits from (factor-sized) font metrics.
	// Scales all 35 verified sites by the factor.
	void ApplyBudgetButtonScale(float factor);
	// Ordinances dialog left-column insets (2026-07-30): the builder lays
	// section headers/checkboxes at x=18 and row text at x=34 as push-imm8
	// constants; with 2x icon art they crowd the text. Scales the six
	// verified sites by the factor (task-#41 tooltip pattern).
	void ApplyOrdinanceInsetScale(float factor);
	// v2.74.0: the ordinance NAME-label x, the one member of the inset family
	// whose scaled value cannot fit a push imm8. lround(68*f) is 136 at f=2 and
	// 204 at f=3, and the imm8 applier ships 127 for BOTH - which clears the eye
	// icon by 23px at 2x (confirmed on screen) and lands 29px INSIDE it at 3x
	// ("Buying Parking" reads "ying Parking"). Re-encodes the two 43-byte windows
	// at 0x0077CBFC (income) and 0x0077D0B9 (expense) in place, same length, same
	// ten arguments in the same order, same net ESP, same frame slot - buying the
	// three bytes push-imm32 costs from neighbours proven dead across the seam.
	//
	// GATED TO f >= 2.50 (integer percent). 2x is CONFIRMED ON SCREEN at the clamped
	// 127 and must not move: below the gate this writes NOTHING and the two sites
	// stay on ApplyOrdinanceInsetScale's imm8 clamp path, byte-identical to
	// v2.73.3. COUPLED PAIR (law 43): call it in the same if-block as
	// ApplyOrdinanceInsetScale, immediately after it. If it is never called at
	// f >= 2.5 the two labels stay at the STOCK 68, which is worse than the
	// clamp - the missing "ordinance name column" log line is the tell.
	// Bytes round-tripped offline by tools\uimap\emu\gate_ordinance_namex.py and
	// independently by tools\ordinance_namex_verify_probe.py. Returns the number
	// of blocks that took; 2 = both sections.
	int ApplyOrdinanceNameColumnScale(float factor);
	// The slider-department builder (Public Safety / H&E / Utilities /
	// City Beautification / Government) + the Business Deals empty box
	// (2026-07-30): scales the builder's column constants (strips, names,
	// counts, sliders, Subtotal label) and the 300x100 box by the factor.
	void ApplyBudgetFamilyScale(float factor);

	// #131: the REGION MAP itself. Unlike every other patch in this header
	// this one has nothing to do with 2x art - the region terrain has no art
	// and is not drawn through the cIGZWin tree at all. cSC4WinRegionView's
	// draw slot (0x00648F00) is `mov al,1 / ret`, a no-op stub; the slab is
	// drawn by the 3D renderer under an orthographic projection whose
	// world-units-per-pixel = R / (Z * camScale) carries NO RESOLUTION TERM.
	// The region therefore draws at a fixed 98 px per region cell at EVERY
	// resolution, so 3840-wide shows 3.75x more sea around the same slab and
	// the city tiles become too small to click.
	//
	// Scales the ONE immediate that seeds it - `push 0.25f` at 0x007AD0BB,
	// the argument to cSC4CameraControl::SetScale inside the region screen's
	// own Init. SetScale recomputes the projection AND its inverse in the
	// same call, so the hit mask moves with the picture; there is no second
	// half to keep in sync (contrast law 43's usual coupled pairs).
	// Verify-before-write identifies the site by the push imm32 AND the call
	// target that consumes it. Never writes at factor 1. Returns 1 if it took.
	// DISARMED v2.78.4 - MEASURED DEAD, returns 0 without writing. The
	// camera at [regionScreen+0x164] accepted our scale, recomputed its
	// projection, and pushed OUR frustum to its device - and the screen never
	// moved across 20 samples / 5s. The region slab is not drawn through it.
	// Kept only as a tombstone. Use ApplyRegionIsoScale instead.
	int ApplyRegionCameraScale(float factor);

	// #131 THE REAL LEVER. The region lays its city tiles out from a 2x2
	// ISOMETRIC BASIS of four .data floats - pixels per region cell:
	//   0xB0DBA4 = +90.51 (= 64*sqrt2)   0xB0DBAC = -37.49
	//   0xB0DBA8 = +18.75                0xB0DBB0 = +45.25 (= 32*sqrt2)
	// written into each tile's precomputed screen position at 0x007B15D8 /
	// 0x007B15EF. 90.51 + 37.49 = 128.0 exactly: one region cell is 128
	// screen px wide at EVERY resolution, which IS the defect.
	// Found by following the city-info bubble, which docks to the tile you
	// click - so the game must already map a cell to a screen point
	// (sub_7B3030, reached from the click handler sub_7ACAD0 via sub_7B3A80).
	// SCOPE: a byte scan finds 12 references, all in region code, none in the
	// city view - verified against a positive control. Scales all four or
	// none (a partial write would shear the basis). Never writes at factor 1.
	// Returns the number of sites written; 4 = complete.
	// #131 COUPLED HALF of ApplyRegionIsoScale. The basis moves tile POSITIONS;
	// this makes the tiles that big. Ship both or neither - the basis alone
	// spreads them apart with gaps (confirmed on screen, worse than the defect).
	//
	// Hooks sub_7AE3D0 (__cdecl, the per-buffer builder inside sub_7AE510's
	// rebuild) and enlarges its output before it returns, so the growth happens
	// INSIDE the game's own rebuild. That is what makes it hold: v2.80.0
	// resized from our tick and the game restored it every frame (total climbed
	// 9/18/27/36 unbounded) AND broke clicking, because the click mask
	// [item+0x44] is built from [item+0x20] by sub_7AD400 during the rebuild and
	// so disagreed with the picture. Riding the rebuild fixes both: the
	// composite is sized from [item+0x1C] and the mask from [item+0x20], both
	// already grown by the time the game reads them.
	// Returns 1 if the hook installed. Never installs at factor 1.
	int ApplyRegionTileScale(float factor);
	// INSTALLED != EXECUTED (law 47). Grown must be non-zero after a region
	// visit, and it must STOP CLIMBING once the tiles are built - a counter that
	// rises forever is the v2.80.0 thrash, not a fix.
	int RegionTileGrown();
	int RegionTileDeclined();

	// #132 region ZOOM. Writes BOTH isometric bases as stock*factor every time
	// (ApplyRegionIsoScale declines on a second call by design, so it cannot
	// drive a live zoom). Clamps to [0.25, 8.0]; returns the factor written.
	float SetRegionIsoScaleLive(float factor);
	// The factor the sub_7AE3D0 hook applies to buffers the game rebuilds from
	// now on - set this so a rebuild lands at the new zoom.
	void SetRegionTileFactor(float factor);
	// #131b SHARPNESS. The game runs a 2-tap tent over every tile purely to
	// align it to the pixel grid at 1:1. MEASURED: at the base tier its phase
	// is 1.00 on every tile vertically, so it is a near-identity and the map is
	// sharp - but ZOOM puts the scaled positions on arbitrary fractions, the
	// blend reaches 81%, and edges smear ~2.5 SCREEN px at f=3.125. On: hand
	// the tent phase 1.0 (a bit-exact copy) and re-apply the alignment as whole
	// DEST pixels, which is finer than the source pixel it worked in.
	// Off restores v2.83.1 byte-for-byte. [UiSpike] RegionTileSharp.
	void SetRegionTileSharp(bool on);
	bool RegionTileSharp();
	float RegionTileFactor();

	// #132 THE ZOOM MECHANISM. Two crashes proved an item's seven structures
	// cannot be kept consistent by resizing anything: the click mask [+0x44]
	// is only ever rebuilt inside sub_7AE510, so a zoom must TRIGGER THAT
	// REBUILD, never perform a resize. See the block comment in the .cpp.
	//
	// Hooks sub_7AE510 to snapshot each item's four PRISTINE bitmaps and its
	// position on the way in - the last moment the un-shifted savegame art
	// exists. Without this a replay would (a) compound, since sub_7AE510 reads
	// the current bitmaps and adds +2 px each time, and (b) crash, because
	// sub_7B13C0 nulls [item+0x20] after the first build and sub_7ABCD0
	// dereferences it. Install once at PostAppInit, alongside the tile hook.
	int ApplyRegionZoomHook();
	// Rebuild every item at an ABSOLUTE factor: restore pristine art, rescale
	// the cached positions, re-run the game's builder, re-derive the pan clamp,
	// carry the scroll, invalidate. Refuses outright (writing nothing) if any
	// tile would pass maxEdge - half the map at the wrong scale is worse than
	// no zoom. Returns the number of items rebuilt; 0 = did not run.
	int RegionZoomRebuild(void* screen, float factor, int maxEdge, int* outSkipped);
	// Drop the snapshot when the region screen goes away - the items and their
	// bitmaps die with it.
	void ClearRegionPristine();
	// INSTALLED != EXECUTED (law 47). Zero after a region visit means the hook
	// never fired and zoom will skip every item rather than compound them.
	int RegionPristineCount();
	// Can a zoom produce a COHERENT result right now? Requires all three halves
	// live: the verified iso patch, the sub_7AE3D0 tile-growth hook, and the
	// sub_7AE510 snapshot hook. With any one missing a zoom is a known-bad
	// shape - most sharply, no tile hook means the lattice grows and the tiles
	// do not, which is the gaps-between-diamonds failure #131 exists to prevent.
	bool RegionZoomOperable();

	int ApplyRegionIsoScale(float factor);
	// How many of the four are live. 0 = the region map is stock.
	int RegionIsoPatchedSites();
	// The camera scale we actually wrote, or 0 if the patch declined. Stock
	// is 0.25. INSTALLED != EXECUTED (law 47): non-zero here means the byte
	// went in, not that a region screen has been built since.
	float RegionCameraScaleApplied();


	// v2.34.0 task #50: scale the NESTED sub-flyout builder's provider metrics
	// (cell 44/44, gap 5) so its strip - and therefore its container - is BORN
	// at round(stock*f). sub_7EAEB0 sites ONLY; the first-level twin sub_7E7270
	// must stay stock or it double-scales.
	void ApplySubFlyoutProviderScale(float factor);

	// v2.37.0 task #78: the Data Views legend. The game re-lays it on EVERY
	// view selection (sub_007A04F0 - the one choke point in the image) from
	// 1x origin constants, so it painted wrong for a frame and only the next
	// sweep tick pinned it back. Scales the four origins (x/y of the label
	// rows and of the colour chips, each in its two encodings = 8 sites) so
	// the game lays the legend down already scaled. The vertical PITCH is
	// composed at runtime from the measured text height and must never be
	// patched - that is also what lets a two-line label keep its taller slot.
	// Returns the number of sites that took; 8 = fully born correct.
	int ApplyDataViewLegendScale(float factor);
	// How many of those eight sites are live. UiSpike's DVPIN pass reads this
	// to decide whether the legend belongs to the game now.
	int DataViewLegendPatchedSites();

	// v2.55.0 task #57: the GRAPHS legend, the same cure one panel over. The
	// chart does not lay out its legend - the panel builder sub_76D3D0 does,
	// once per chart build, from a six-constant right-margin budget measured
	// off winW that has never scaled. Our own 2x checkbox window and 2x font
	// then had to fit inside that unchanged 110px budget, so the swatch's slot
	// collapsed to zero (invisible colour) and every label wrapped until 2 of
	// 9 rows fell off the bottom. Patches five in-place immediates plus three
	// equal-length block re-encodings so the column is BORN at f.
	//
	// The strip is TABLED from the acceptance oracle, never computed: a box of
	// round(72*f) wraps MORE than stock because the measured ink ratio is
	// 2.121, not 2.00. Certified for f = 1.5 / 2 / 3 only; any other factor
	// DECLINES and leaves the stock budget in place.
	//
	// COUPLED PAIR (law 43): the plot's right margin must clear this strip by
	// sc(2,f), and that margin belongs to EARLYCHART's ChartStoreThunk. The
	// oracle's H-EARLYCHART candidate is exactly "take the strip, keep the old
	// plot margin" and it FAILS - the plot border paints inside the checkbox
	// column. Arm both halves together or neither.
	// Returns the number of sites that took; 8 = fully born correct.
	int ApplyGraphLegendBudgetScale(float factor);
	// How many of those eight are live. UiSpike reads this to decide whether
	// to run its LEGENDFIX sweep fallback at all.
	int GraphLegendPatchedSites();
	// The plot's right margin that goes with the patched budget, or 0 if the
	// full set did not take. EARLYCHART's ChartStoreThunk reads this: a non-zero
	// value is the ONLY thing that lets it abandon its proportional margin, so
	// the strip and the plot edge can never move independently.
	int GraphLegendPlotRightMargin(float factor);

	// #121: extend the cSC4WinMiniMap terrain bake to x8 (zoom -3), so the
	// Data Views map can bake a real terrain base at FULL SIZE on small city
	// tiles instead of leaving it black. The game's bake dispatch at 0x7A8560
	// is a 5-entry jump table indexed zoom+2 with an UNSIGNED bound, so zoom
	// -3 falls through to the skip; the dest math either side of it is fully
	// general. We re-point that one dispatch at a 6-entry table whose entries
	// 1..5 are the game's own stubs (zoom -2..+2 stays bit-identical) and
	// whose entry 0 is our x8 blitter. IN-MEMORY ONLY - the exe on disk is
	// never written. Declines loudly on any byte mismatch, and never writes
	// at all at factor 1.
	void ApplyMiniMapX8Bake(float factor);
	// INSTALLED != EXECUTED (law 47): how many x8 tiles we have actually
	// blitted. UiSpike prints this so a silent no-op cannot be mistaken for
	// a working patch.
	int MiniMapX8Blits();
	// Non-zero means a blit had to be CLIPPED - the map's blitSize is not an
	// exact power-of-two multiple of the terrain dimension, which is the
	// #109 crash family (1.5x's 384, 3x's 768). The clip keeps it safe; the
	// counter says the sizing policy leaked.
	int MiniMapX8Clips();
	// True once the dispatch write is live. With a real bake at zoom -3
	// there is nothing to heal: the v2.69.x dock-seed and v2.70.x per-sweep
	// heal it displaced were retired outright in v2.71.4. The DVMAP clamp is
	// the surviving fallback and gates on this flag.
	bool MiniMapX8Active();

	// #130: the Mayor-rating DECLINE arrow (window 0xCA5A415E). sub_7E8510
	// is the sole mover of that window (a .text scan finds exactly four
	// references to the id: three MoveTo sites in that function plus the
	// builder's snapshot). It places it at `[this+0x378] + (3-mag)*step`,
	// `[this+0x37C]` - two fields the panel BUILDER sub_7ECF60 snapshots from
	// the arrow's own GetL/GetT at 0x7ED2F9 / 0x7ED312, i.e. at construction,
	// from the DESIGN rect area=(98,58,119,67). Every rating change therefore
	// teleports the arrow back to an unscaled anchor, (98(f-1), 58(f-1)) px
	// up-and-left of the bar - 196x116 at f=3.
	//
	// The cure is the game's OWN snapshot, taken later: re-read GetL/GetT off
	// the arrow once, at the first update after our sweep has moved it. No
	// coordinate is computed here. If the sweep never scaled the arrow, the
	// read returns what is already cached and the write is bit-identical -
	// which is what makes it safe to arm before the on-screen adjudication.
	// mode: 0 = off, 1 = log only (inert at any tier), 2 = log + re-anchor,
	// and mode 2 is REFUSED below factor 2.5 so f=2.00 installs nothing.
	void InstallRatingArrowAnchor(float factor, int mode);
	// INSTALLED != EXECUTED (law 47): how many times the anchor was actually
	// rewritten. 0 with the hook installed means the arrow was never scaled,
	// which relocates the bug to sweep coverage instead of the anchor.
	int RatingArrowAnchorArms();

	// #188: the U-Drive-It start bubbles (mission_selection_* Swarm effects,
	// spawned by name at five exe sites) get the tier scale written into the
	// effect INSTANCE's transform block right after CreateEffectByName
	// returns - the activation math multiplies it into every child spawn.
	// A data-side EFFDIR override was proven inert from both plugin trees,
	// so this is the lever. mode: 0 = off, 1 = log only, 2 = log + scale.
	// overrideScale: 0 = follow the tier factor; > 1 = explicit multiplier
	// (ini MissionBubbleScale, the no-rebuild tuning knob).
	void InstallMissionBubbleScale(float factor, int mode, float overrideScale);
	// INSTALLED != EXECUTED (law 47): how many instances were actually
	// SCALED. Equals "no mission_selection spawn ran" only in mode 2 with
	// every spawn pristine: mode 1 (log-only) always reads 0, and a
	// non-pristine refusal also leaves it 0 (refusals are always logged,
	// uncapped, so the log adjudicates which case a 0 is).
	int MissionBubbleFxHits();

	// #188 elimination instrument (MissionBubbleFx=3): hooks the renderer's
	// Pick at PostCityInit (runtime-resolved from the [0xB43DD0] singleton)
	// and logs every hit's model-instance VTABLE - the hovered/clicked
	// object names its own class instead of us guessing its drawer.
	// Idempotent; safe to call every PostCityInit.
	void InstallPickProbe();

	// #188 ARTFETCH. Installed from the DIRECTOR CONSTRUCTOR, not PostAppInit:
	// the signpost FRAME sheets never appeared in a PostAppInit-armed capture
	// even though our 2x override of them demonstrably moved a balloon on
	// screen - so the fetch happens EARLIER than the hook did. A probe armed
	// after the event it is meant to observe is a guaranteed null (law 91).
	void InstallArtFetchProbe();
}
