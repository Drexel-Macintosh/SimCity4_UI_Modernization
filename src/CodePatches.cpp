#include "CodePatches.h"
#include "Logger.h"
#include "MinHook.h"

#define WIN32_LEAN_AND_MEAN
#include <Windows.h>

#include <cmath>
#include <cstdint>
#include <cstring>
#include <intrin.h>
#include <cstdlib>     // _wtof - the #188 BalloonSpriteScale ini knob
#include <cstdio>      // sscanf_s - the #188 CsiAim re-aimable patch list

// The DLL's own base, so the #188 sprite knobs can be read from the ini that
// sits beside this DLL (same idiom as SC4UIScaleDllDirector.cpp).
extern "C" IMAGE_DOS_HEADER __ImageBase;

#pragma intrinsic(_ReturnAddress)

namespace
{
	// Instruction-start VAs of the three "imul r32, r/m32, 7" sites in the
	// Mayor-rating HUD controller (image base 0x400000). The imm8 operand
	// sits at +2. Source: DYNAMIC-CONTROLS.md disassembly of 1.1.641.
	const uintptr_t kRatingImulSites[] = { 0x7E87B1, 0x7E89D7, 0x7E8A02 };
	const uintptr_t kImageBase = 0x400000;
	const uint8_t kImulOpcode = 0x6B;
	const uint8_t kStockMultiplier = 0x07;

	// TOOLTIP WRAP WIDTH (task #41, 2026-07-29). The tip layer (window
	// 0x2AAB8CC1, class 0x00AB6770) code-paints the whole tooltip; its Plot
	// override 0x798710 wraps/measures the tip text against a HARDCODED
	// 250px width - `push 0xfa` at these two instruction-start VAs (measure
	// + layout). With 2x fonts the text wraps narrow-and-tall and crowds the
	// frame's right edge, painting over the rounded-corner arcs (the
	// "unfinished" clipped corners). Scaling 250 -> 250*factor restores the
	// designed proportions. push imm32: opcode 0x68, operand dword at +1.
	const uintptr_t kTipWrapSites[] = { 0x79880A, 0x7988A9 };
	const uint8_t kPushImm32 = 0x68;
	const uint32_t kStockTipWrap = 250;

	// PLACEMENT COST READOUT BUFFER (#159, 2026-08-15). The figure shown while
	// placing a lot is drawn into a RUNTIME BUFFER allocated 128x32 - sized for
	// the 1x font - so a 2x font is rasterised CLIPPED on the left and bottom
	// before anything downstream can see it. USER-REPORTED: "look how it's
	// cutoff when placing an object ... the display box is too small".
	//
	// ⛔ THE WINDOW IS NOT THE LEVER, THE BUFFER IS. The readout is a GZWinBMP
	// (vt 0x00ADF6A0) parented straight to the 3D view, and GZWinBMP is
	// dst-follows-src: its draw computes dst from the SOURCE BITMAP and never
	// reads the window rect (BLIT-BEHAVIOUR.md). The 128x32 WINDOW is a
	// consequence of the 128x32 buffer, which is why scaling the window did
	// nothing: MEASURED, the game re-sizes it to 128x32 every time it shows it
	// (caught parked off-screen at (-20286,-20030) carrying our 256x64, reset
	// 80ms later), our sweep fought it 4x and ScaleRecord correctly tombstoned
	// it as "game-managed geometry" - and the fight FLASHED (FLASHSET #9).
	//
	// HOW THE SITE WAS FOUND, and why it is believed:
	//   * 832 SetArea/SetSize/SetW call sites carry no literal 128x32 rect;
	//   * of 5540 `call [reg+0x0C]` (cIGZBuffer::Init is slot 3) sites, exactly
	//     THREE carry both 128 and 32, and two are false positives - 0x490F82
	//     builds flags (`or eax,0x80` / `or edi,0x20`) and passes a GUID, and
	//     0x796E93 takes no arguments at all (its pushes belong to earlier
	//     calls). 0x7EEF59 is the ONLY genuine Init(128,32) in the image.
	// Positive control for that scan: it resolves 50 other distinct constant
	// Init sizes, so it can see the ones that are there.
	//
	//   0x7EEF43  6A 20              push 32     <- height
	//   0x7EEF54  68 80 00 00 00     push 128    <- width
	//   0x7EEF59  FF 50 0C           call [eax+0xC] = cIGZBuffer::Init
	//
	// ⚠ THE HEIGHT SITE IS A 2-BYTE push imm8 AND CANNOT BE WIDENED IN PLACE.
	// 32*f must stay <= 0x7F or the patch is REFUSED, never truncated: at the
	// shipped tiers 32*3 = 96 fits, but a hypothetical 4x would need 128, which
	// is not encodable here. This is #136's lesson pointed the other way -
	// there the imm8 could be widened because there was room; here there is
	// not, so the honest move is to decline and say so.
	const uintptr_t kCostBoxHeightSite = 0x7EEF43;   // 6A 20      push 32
	const uintptr_t kCostBoxWidthSite = 0x7EEF54;    // 68 80..    push 128
	const uint8_t kPushImm8 = 0x6A;
	const uint32_t kStockCostBoxW = 128;
	const uint8_t kStockCostBoxH = 32;

	// #159 PART TWO — THE TEXT ORIGIN INSIDE THAT BUFFER.
	//
	// Widening the buffer alone is provably NOT enough, and the user saw exactly
	// why: "still cut off and it has shifted really far to the left". The string
	// is RIGHT-ALIGNED against a second 1x constant, so a wider buffer moved the
	// box without moving the text's anchor.
	//
	// PROVEN, not inferred, by normalising the frame slots of the composer
	// 0x007EAC70 (callee-cleanup modelled - the first attempt at this analysis
	// did NOT model it and produced garbage offsets):
	//
	//   0x7EACBC..0x7EACC8   four dwords zeroed  = a cRZRect at slots -20..-8
	//   0x7EAD19             &that rect passed to the text MEASURE call
	//   0x7EAD33             call [vt+0xB8]      = measure, fills the rect
	//   0x7EAD3D  ebx = slot(-20)                = rect.left
	//   0x7EAD39  edx = slot(-12)                = rect.right
	//   0x7EAD47  sub ebx, edx                   = left - right = -textWidth
	//   0x7EAD4B  add ebx, 0x7c                  = 124 - textWidth  <- X ORIGIN
	//
	// 124 is 128-4: the string's RIGHT edge sits 4px inside the 128 buffer. At
	// 2x the figure measures ~140px, so x = -16 and precisely the leading
	// simoleon glyph is cut - which is the reported symptom. At 1x it is ~70px,
	// x = +54, clean. Scaled the anchor is 124*f: 248 in a 256 buffer, 186 in
	// 192, 372 in 384 - each keeping the same 4*f inset.
	//
	// ⛔ WHY A TRAMPOLINE AND NOT AN IMMEDIATE. `83 C3 7C` is `add r/m32, imm8`
	// in THREE bytes; 186/248/372 all exceed the signed imm8 range and the
	// imm32 form needs six. Neighbouring instructions leave no slack either
	// (7 bytes available, 10 required). Unlike #136 there is nothing to widen,
	// so the 8 bytes spanning `add ebx,0x7c` + `push 0x8001` are replaced with a
	// jump to a cave that does both with a full imm32 and returns.
	const uintptr_t kCostOriginSite = 0x7EAD4B;   // 83 C3 7C 68 01 80 00 00
	const uintptr_t kCostOriginBack = 0x7EAD53;   // resume here
	const uint8_t kCostOriginStock[8] = {
		0x83, 0xC3, 0x7C,              // add ebx, 0x7c
		0x68, 0x01, 0x80, 0x00, 0x00   // push 0x8001
	};
	const int kStockCostOrigin = 124;
	void* gCostCave = nullptr;         // one cave per process, never freed
	// #189: one cave per bizbox size site. Same discipline as gCostCave -
	// allocated once, never freed, because the patched bytes jump into it
	// for the life of the process.
	void* gBizBoxCaves[5] = {};

	// INTRO VIDEO SURFACE (#138, 2026-08-05). The intro clip draws 768x384
	// centred no matter the screen size, so at 2400x1600 it is a postage
	// stamp - and the wrong SHAPE too, since the source (Intro.dat
	// I-00000001) is 800x608 while the window is 2:1. The EA-logo clip
	// (I-00000002) is 512x384, whose height matches the window exactly,
	// which is why THAT one looks right and was the user's own clue.
	//
	// HOW IT WAS FOUND (all static, tools\research\find_intro_video.py +
	// disasm_at.py): the '-intro' switch string 0x00A93184 has ONE xref, at
	// 0x004E11CC; the branch below it calls 0x004E0C20 (play) or 0x004E0CB0
	// (skip). 0x4E0C20 does `new(0x108)` + ctor 0x0079CED0, which writes
	// vtable 0x00AB78F0 = cSC4WinIntroVideoScreen. Its init (slot 4,
	// 0x0079CFE0) builds the surface with the four constants below.
	// The skip path builds cSC4WinSplashScreen instead (ctor 0x007BE4E0,
	// size 0x118) - a DIFFERENT class, which is why the static splash and
	// the video behave independently.
	//
	//   0079D063  68 80 01 00 00   push 0x180   ; height 384
	//   0079D068  68 00 03 00 00   push 0x300   ; width  768
	//   0079D071  call [eax+0xDC]  SetArea(0, 0, 768, 384)
	//   0079D089  2D 80 01 00 00   sub eax,0x180 ; (GetH - 384)/2  -> Y
	//   0079D0A4  2D 00 03 00 00   sub eax,0x300 ; (GetW - 768)/2  -> X
	//   0079D0AF  call [edi+0xE0]  SetPosition(X, Y)
	//
	// [vt+0xA4]=GetW and [vt+0xA8]=GetH were CONFIRMED against the known
	// getters 0x0099C81B/0x0099C82A rather than inferred from the pairing -
	// getting that backwards would centre the video off-screen.
	//
	// The centring maths reads the parent at RUNTIME, so scaling the four
	// constants keeps it correct at any resolution: no new arithmetic.
	// All four operands are imm32 - no imm8 ceiling (contrast #136).
	//
	// ⚠ TIMING (law 47, installed != executed): this MUST be applied before
	// the game's app-init runs 0x4E0C20, which is long before PostAppInit
	// where every other patch lives. Measured 2026-08-05: PostAppInit ran
	// +16.4s after the tier was decided. It is called from the tier block
	// instead - see SC4UIScaleDllDirector.
	const uint8_t kSubEaxImm32 = 0x2D;
	struct IntroVidSite
	{
		uintptr_t va;
		uint8_t opcode;
		uint32_t stock;
		const char* what;
	};
	const IntroVidSite kIntroVidSites[] = {
		{ 0x79D063, kPushImm32,   384, "SetArea height" },
		{ 0x79D068, kPushImm32,   768, "SetArea width" },
		{ 0x79D089, kSubEaxImm32, 384, "centre-Y subtrahend" },
		{ 0x79D0A4, kSubEaxImm32, 768, "centre-X subtrahend" },
	};

	// REGION-VIEW CAMERA SCALE (#131, 2026-08-04). The region terrain is NOT
	// drawn through the cIGZWin tree: cSC4WinRegionView's own draw slot
	// (vt 0x00AB9658, slot 88 = vt+0x160 -> 0x00648F00) is literally
	// `B0 01 C3` = `mov al,1 / ret`, a no-op stub followed by int3 padding.
	// The slab is drawn by the 3D renderer under an ORTHOGRAPHIC projection
	// built in sub_7CBE40:
	//     worldUnitsPerPixel = R / (Z * camScale)        -> [cam+0x134]
	//     pixelsPerWorldUnit = (Z * camScale) / R        -> [cam+0x138]
	//     halfW = 0.5 * viewportW * worldUnitsPerPixel   (0x007CBF61..0x007CBF6D)
	//     halfH = 0.5 * viewportH * worldUnitsPerPixel   (0x007CBF7B..0x007CBF85)
	// R = 16*(sin|T|+cos|T|) = 20.905007 and is CONSTANT (the tilt table at
	// 0x00ABCFC4 holds -0.392699 at every level); Z = 8 at the region's zoom
	// level 0 (table 0x00ABACE0 = {8,16,32,73,146}).
	//
	// THERE IS NO RESOLUTION TERM IN worldUnitsPerPixel. That is the defect:
	// the region draws at a fixed 1024 world-units-per-cell / 10.4525
	// units-per-pixel = 98 px per region cell at EVERY resolution, so at 3840
	// wide the camera simply shows 3.75x more empty sea around the same slab.
	//
	// cSC4WinRegionScreen::Init (sub_7B1900) builds the region scene through
	// sub_7ACC90, which sets the camera scale ONCE via
	//     0x007AD0BB  68 00 00 80 3E   push 0.25f
	//     0x007AD0C0  E8 1B 06 02 00   call 0x7CD6E0   (cSC4CameraControl::SetScale)
	// Scaling that ONE immediate is the entire fix. SetScale recomputes
	// [cam+0x134] AND its inverse [cam+0x138] in the same call
	// (0x007CD73D -> sub_7CBE40), so PICKING FOLLOWS THE PICTURE - the hit
	// box cannot drift from the sprite (law 43, the coupled pair). It also
	// dedups on equality (fucompp at 0x007CD6ED) and re-broadcasts
	// 0xA6B79621 camera-updated, so nothing is left stale.
	//
	// We patch the ARGUMENT, never the shared setter: sub_7CD6E0, sub_7CBE40,
	// the Z table and the tilt table are all shared with the CITY camera
	// (which drives the same setter at 0.9f), and touching any of them would
	// change the city view too. 0.25*f stays well inside the band the engine
	// already uses on this very camera.
	//
	// Positive identification is BOTH halves (law 3: never act on a class or
	// a constant alone) - the push imm32 must carry exactly 0.25f AND the
	// call that consumes it must resolve to SetScale. A bare `push 0.25f`
	// occurs elsewhere in the image; this pair does not.
	const uintptr_t kRegionCamScaleSite = 0x7AD0BB;      // push imm32 (0.25f)
	const uint32_t kRegionCamScaleStock = 0x3E800000;    // 0.25f
	const uintptr_t kRegionCamSetScale = 0x7CD6E0;       // cSC4CameraControl::SetScale
	const uint8_t kCallRel32 = 0xE8;
	// SetScale's range guard reads the CURRENT value, not the incoming one
	// (0x007CD6FA loads [cam+0xF0] BEFORE the store at 0x007CD72C), so it
	// will not catch a wild argument. The clamp has to be ours.
	const float kRegionCamScaleMin = 0.05f;
	const float kRegionCamScaleMax = 8.0f;
	// Geometry of the region mesh, for the log line only: 1 region cell = 16
	// samples * 64.0 world units (sub_7AACE0 stores 64.0f at [grid+0x20]).
	const float kRegionWorldUnitsPerCell = 1024.0f;
	const float kRegionCamR = 20.905007f;   // 16*(sin|T|+cos|T|), T = -0.392699
	const float kRegionCamZ = 8.0f;         // zoom level 0
	float gRegionCamScaleApplied = 0.0f;

	// ============================================================
	// #131 THE REAL LEVER — THE REGION ISOMETRIC BASIS
	// ============================================================
	// Found 2026-08-04 by following the USER'S observation that the city-info
	// bubble is docked to the tile you click: if the bubble tracks the tile,
	// the game must already compute a SCREEN POSITION for a region cell.
	//
	// The trace: region click handler sub_7ACAD0 calls sub_7B3A80(screenX,
	// screenY) at 0x007ACAF7 = screen -> city. That walks the region item list
	// and for each item calls sub_7B3030 = item -> SCREEN POSITION:
	//     screenX = round(item[+0x10]) - [this+0xE8]      (integer pan)
	//     screenY = round(item[+0x14]) - [this+0xEC] - h
	// NO MULTIPLY. The items carry PRECOMPUTED float screen positions, which
	// is precisely why moving a 3D camera changed nothing.
	//
	// Those floats are written at 0x007B15D8 / 0x007B15EF from a 2x2
	// ISOMETRIC BASIS held as four .data floats - pixels per region cell:
	//     screenX = (cellX + size) * [0xB0DBA4] + cellY * [0xB0DBAC]
	//     screenY = (cellY + size) * [0xB0DBA8] +  ...  * [0xB0DBB0]
	// with 90.51 = 64*sqrt(2) and 45.25 = 32*sqrt(2), and
	// 90.51 + 37.49 = 128.0 EXACTLY: one region cell is 128 screen px wide,
	// hard-coded, with no resolution term anywhere. That is the whole defect.
	//
	// SCOPING IS AUTOMATIC. A byte scan of the image for references to these
	// four addresses returns 12 sites, ALL inside the region code
	// (0x007AB829-0x007AB8DA, 0x007B15C3-0x007B15E9, 0x007B1F8D-0x007B1F93)
	// and NONE in the city view - verified with a positive control (the same
	// scan finds the zoom table 0x00ABACE0). Nothing else in the game reads
	// this basis, so scaling it cannot leak into the city.
	//
	// The 0x007AB8xx cluster is the region's own draw/extent code, so the
	// tile QUAD should follow the basis too. If it does not, the tiles will
	// spread apart with gaps rather than growing - which the screen will say
	// immediately, and which is the one thing to look for on the first run.
	const uintptr_t kRegionIsoSites[] = { 0xB0DBA4, 0xB0DBA8, 0xB0DBAC, 0xB0DBB0 };
	const uint32_t kRegionIsoStock[] = {
		0x42B5051F, // +90.51  = 64*sqrt(2)
		0x41960000, // +18.75
		0xC215F5C3, // -37.49
		0x42350000, // +45.25 = 32*sqrt(2)
	};
	const int kRegionIsoCount = 4;
	int gRegionIsoSitesApplied = 0;
	// The factor the basis currently holds. Item positions are computed ONCE,
	// from the basis live at that moment, so a later zoom needs to know what
	// they were computed against. 0 = still stock.
	float gRegionIsoLiveFactor = 0.0f;

	// #132 THE SECOND BASIS. A 3x2 companion matrix, L1/1024 plus an elevation
	// column, read ONLY by sub_7B5430 (0x7B5580..0x7B5670) to project the
	// airport/seaport overlay icons and 3-D props into TILE space. Because the
	// projection is relative to the thumbnail, growing the thumbnail without
	// growing this de-registers the icons from the picture it sits on.
	// #131 shipped L1 alone, so this has been stale at 2x/3x all along; it goes
	// unseen only because the overlay pass is gated on view+0x118 != 0 and the
	// default view mode is 0. The zoom replay CALLS sub_7B5430, so fix it here.
	// ⚠ NOT contiguous with L1: 0xB0DBB4/0xB0DBB8 in between hold POINTERS
	// (0x00A806E8 / 0x00A806E0), not floats. Read out of the .data section of
	// the shipped 1.1.641 exe, not copied from a note.
	const uintptr_t kRegionIso2Sites[] = {
		0xB0DBBC, 0xB0DBC0, 0xB0DBC4, 0xB0DBC8, 0xB0DBCC, 0xB0DBD0,
	};
	const uint32_t kRegionIso2Stock[] = {
		0x3DB504F3, // +0.08838835 = +90.51 / 1024
		0x3C95F619, // +0.01830583 = +18.75 / 1024
		0x00000000, //  0.0         (scales to itself; kept so the set is whole)
		0xBDA9AF0A, // -0.08285339   the ELEVATION term (~ -84.84 / 1024)
		0xBD15F619, // -0.03661165 = -37.49 / 1024
		0x3D3504F3, // +0.04419417 = +45.25 / 1024
	};
	const int kRegionIso2Count = 6;

	// NEWS / RICH-TEXT SIZE TABLES (task #42, 2026-07-29). All news text -
	// ticker roll, reader headlines ('<FONT FACE="Arta" SIZE=3>' templates in
	// .rdata), story pages, advisor/message popups and the 189 tutorial
	// LTEXTs with embedded <font size="N"> - renders through the game's HTML
	// engine. SIZE indexes 1..7 resolve through the FONT table at 0xACD4A0
	// and <H1>..<H7> through the HEADING table at 0xAB4AD0. FontStyle.ini
	// sizes never reach this path (why the community's font mods could not
	// grow news text). Each rich window COPIES the tables at creation
	// (setter 0x8FEEB8 -> this+0x1A8), so scaling the .rdata source at
	// PostAppInit reaches every instance the game will ever build.
	const uintptr_t kHtmlFontSizeTable = 0xACD4A0;
	const uint32_t kStockHtmlFontSizes[7] = { 8, 10, 12, 14, 18, 24, 36 };
	const uintptr_t kHtmlHeadingSizeTable = 0xAB4AD0;
	const uint32_t kStockHtmlHeadingSizes[7] = { 8, 10, 12, 16, 19, 24, 48 };

	// The advisor/news MESSAGE POPUP builders derive an HTML SIZE index from
	// the MessageHeader/MessageBody style sizes (idx = (4*size+8)/18, sites
	// 0x762F30 / 0x52CC70 regions). Our FontStyle files DOUBLE those styles,
	// so with the tables also scaled the popups would compound to 4x.
	// Retarget the four `push <guid>` immediates at stock-size clone styles
	// (MessageHeaderHtml/MessageBodyHtml) that our FontStyle files add: the
	// index derivation then returns stock indexes and the scaled table
	// applies the factor exactly once. The builders null-check the fetch and
	// fall back to sane defaults, so a missing clone style degrades softly.
	struct GuidRetarget { uintptr_t site; uint32_t from; uint32_t to; };
	const GuidRetarget kPopupStyleRetargets[] = {
		{ 0x52CCEE, 0x4A809914, 0x5C4B0914 }, // MessageHeader -> ...Html
		{ 0x52CD01, 0x4A809915, 0x5C4B0915 }, // MessageBody   -> ...Html
		{ 0x762F85, 0x4A809914, 0x5C4B0914 },
		{ 0x762F98, 0x4A809915, 0x5C4B0915 },
	};

	// ADVICE/NEWS ROW COLUMN BUDGET (task #88, measured 2026-07-31).
	//
	// `cSC4WinAdviceList::Refresh` (0x00793810) is the SINGLE emitter for
	// every advice list in the process - news reader 0x6A231531, advisor
	// briefings 0x00100100/0x00100101, My Sims 0xAA1F1EB5/0x6A1F1F4A, the
	// briefing panels, AND the never-touch ticker marquee 0xAA12F33C. One
	// dword xref image-wide (the vtable slot at 0xAB5894), so one static
	// write reaches the whole family and there is no twin builder.
	//
	// It emits each row as one <TR> of a three-column HTML table:
	//   0x00AB5794  '<TR><TD WIDTH="18">'                    <- arrow glyph
	//   0x00AB5868  '</TD><TD WIDTH="%d">'                   <- headline
	//   0x00AB56B0  '</TD><TD WIDTH="18"><A NAME="item%d"
	//                HREF="sc4://action/close?item=%d">'     <- the dismiss X
	// The X cell is emitted UNCONDITIONALLY - there is no dismissible flag
	// and no fit test anywhere between 0x00793B1C and 0x00793BA5.
	//
	// The %d is `pane->GetW() - 61` from `83 EE 3D` at 0x0079388F, where
	// 61 = 18 (arrow) + 18 (X) + a flat 25px right-hand reserve. Both glyph
	// columns are hard-coded 18 and never scale, so the row's declared total
	// is always GetW() - 25.
	//
	// The glyphs are <IMG> tags with NO width/height (task #87), so they
	// draw at the art's intrinsic size, and the table's column width is the
	// MEASURED cell rect (0x0090A0A3 -> 0x00909A47), not the declared one:
	// the declared WIDTH= reaches only col+0x08/+0x0C, which the width
	// distribution loop never reads. A container's rect is the UNION of its
	// children with no clamp (vt+0x10 = 0x00909A0C -> 0x009092BE), so 2x
	// glyph art really does grow its cell.
	//
	// WHY THIS PATCH EXISTS: shipping 2x arrow art without it moves the X
	// cell 18px right, past the pane's content edge, and the dismiss control
	// disappears. This restores the declared total to GetW() - 25 - the
	// exact geometry of the user-confirmed-good stock row - by taking the
	// arrow's extra width out of the HEADLINE column instead of out of the
	// X's position. It is a RESTORE-THE-KNOWN-GOOD-TOTAL patch, which is
	// why it does not depend on where precisely the content edge falls.
	//
	// ⚠ THE 25 IS NOT A MAGIC NUMBER, AND IT DOES NOT ALL STAY FIXED
	// (v2.40.1, measured from a live eyes-on that v2.40.0's flat reserve
	// could not survive). The pane's usable width is NOT GetW(): the text
	// class computes it as `GetW() - 2*gutter - scrollbarW` (sub_9BCBC5 @
	// 0x009BCBC5, gutter default 5 @0x009BFFCC), and it fetches scrollbarW
	// LIVE from the scrollbar window's own GetW() - it is not baked. The
	// stock reserve decomposes exactly:
	//     25 ~= 2*gutter (10) + stock scrollbar cell (16)
	// and 16 is `cGZWinScrollbar::SetImage` (0x9C45F0) sizing the bar from
	// its art width / 12 - our shipping a6 strip is 384x32 at 2x, so the
	// scrollbar really is 32px wide (that is task #82 working as intended).
	// Consequence: an advice list with NO scrollbar has 15px to spare, but
	// the moment a row EXPANDS the scrollbar appears and the usable width
	// drops to GetW()-42 while a flat-25 reserve still declares GetW()-25 -
	// 17px short, which clips 17 of the X's 18px. Collapsed rows pass and
	// expanded rows fail, which is precisely what eyes-on showed.
	// So the scrollbar half of the reserve MUST scale with the tier:
	//
	//   S(f) = round(18*f) + 18 + 9 + round(16*f)
	//          ^arrow col    ^X   ^fixed ^scrollbar cell
	//        f=1.0 -> 61 (EXACTLY the stock constant - the decomposition is
	//                     self-checking; if this ever stops reducing to 61,
	//                     the split is wrong)
	//        f=1.5 -> 78    f=2.0 -> 95    f=3.0 -> 129 (clamped, see below)
	//
	// We budget for the scrollbar UNCONDITIONALLY rather than detouring
	// Refresh to ask whether one exists: a static worst-case reserve costs a
	// slightly wider right margin on scrollbar-less lists (invisible) and is
	// correct in BOTH states, where any single flat value cannot be.
	//
	// THE X COLUMN SCALES TOO, BUT ONLY UP TO f=2.0 (v2.40.2). With both
	// glyphs scaled, S = 2*round(18f) + 9 + round(16f) = 61 / 87 / 113 / 165
	// at 1x / 1.5x / 2x / 3x - and 165 blows the SIGN-EXTENDED imm8 of
	// `83 EE ib` beyond any clamp worth having. With the X held at stock,
	// S = round(18f) + 18 + 9 + round(16f) = 61 / 78 / 95 / 129.
	// So: scale the X at <=2x (a 36px dismiss X is a real tap target on a
	// high-DPI screen; an 18px one is not), hold it at stock at 3x.
	// Both forms declare the SAME row total, W - kAdviceRowFixedPx - bar, so
	// this choice only moves width BETWEEN the X and the headline column -
	// it can never change whether the row fits its pane.
	//
	// COUPLED TO DATA, AND THE CONDITION IS DUPLICATED: the X ids
	// {46a006b0, 0x1441625x with (i & 3) == 3} are staged by
	// build_selective_safe.py under the SAME `factor <= 2.0` test. Art and
	// budget must describe each other; change one and you change both in the
	// same build. They ship together and revert together.
	const uintptr_t kAdviceRowMidSite = 0x79388F;
	const uint8_t kAdviceRowMidStock = 0x3D;      // 61
	// #136: the 19-byte window that CONTAINS kAdviceRowMidSite. Rewritten
	// whole when the subtrahend will not fit in the sign-extended imm8, so
	// `sub esi, imm8` becomes `lea esi, [eax - imm32]`. Starts 4 bytes before
	// the imm8 site because the folded `mov esi, eax` is part of the payment.
	// Proven by tools\uimap\emu\gate_advice_rowx.py (4 positive controls).
	const uintptr_t kAdviceRowWinSite = 0x79388B;
	const int kAdviceGlyphStockPx = 18;           // both hard-coded glyph columns
	const int kAdviceScrollbarStockPx = 16;       // a6 cell = art width / 12; SCALES
	const int kAdviceRowFixedPx = 9;              // 61 - 18 - 18 - 16; does NOT scale
	const float kAdviceXScaleMaxFactor = 2.0f;    // above this the X stays stock

	// BUDGET DETAIL-DIALOG BUTTONS (2026-07-30). The five department
	// builders (Ordinances/Neighbor Deals/Transportation/Taxes families,
	// 0x77D3xx/0x7818xx/0x7855xx/0x7872xx/0x7893xx) size every Accept/
	// Cancel button pair by `push 0x1e; push 0xb4; call [vt+0xD4]`
	// (SetSize(180,30)) and place them through sub_77B960 at x=14 /
	// x = W-0xC3 (195 = 180+15) and y = H-0x28 (40 = 30+10). The dialog
	// frame itself content-fits from font metrics (already factor-sized),
	// so ONLY these constants stay 1x. All 35 sites are exclusive to the
	// budget family (whole-exe byte scan, 2026-07-30 checkpoint).
	const uintptr_t kBudgetBtnSizeSites[] = { // 6a 1e 68 b4 00 00 00
		0x77D33F, 0x77D35F, 0x77D4BF, 0x77D4DF,
		0x7818B6, 0x7818D7, 0x7819D3, 0x7819F4,
		0x785512, 0x785532, 0x78562C, 0x78564C,
		0x7872AC, 0x7872CC, 0x7873EE, 0x78740E,
		0x7893A5, 0x7893C6, 0x7894BB, 0x7894DC,
	};
	const uintptr_t kBudgetBtnXSites[] = { // 81 e9 c3 00 00 00 (sub ecx, 195)
		0x77D4A0, 0x7819AD, 0x785607, 0x7873CF, 0x78949B,
	};
	const uintptr_t kBudgetBtnYSites[] = { // 83 /5 28 (sub r32, 40 imm8)
		0x77D31B, 0x77D49C, 0x781897, 0x7819A9, 0x7854F4,
		0x785603, 0x78728E, 0x7873CB, 0x789386, 0x789497,
	};
	const uint32_t kStockBudgetBtnW = 180, kStockBudgetBtnH = 30;
	const uint32_t kStockBudgetBtnXInset = 195, kStockBudgetBtnYInset = 40;

	// ORDINANCES ROW INSETS (2026-07-30, the task-#41 tooltip pattern:
	// 2x content in 1x-const geometry -> scale the hardcoded constant).
	// The Ordinances builder lays its left column with `push imm8` x
	// constants: section headers + checkboxes at x=18, the row text/strip
	// windows at x=34. With 2x checkbox art (32px, ours) and the eye
	// glyph those pile onto the text start. Doubling the constants
	// restores the stock indent proportions; the frame's content-fit
	// width grows with them automatically. Sites are Ordinances-only
	// (income section 0x77C9xx/0x77CAxx, expense 0x77CExx/0x77CFxx);
	// other departments have their own layouts - extend one at a time
	// after eyes-on, per the flyout law.
	struct InsetSite { uintptr_t site; uint8_t stock; uint8_t ctx; };
	const InsetSite kOrdinanceInsetSites[] = {
		{ 0x77C998, 0x12, 0x68 }, // income "Monthly Income" header x
		{ 0x77CA88, 0x12, 0x51 }, // income checkbox x
		{ 0x77CAE0, 0x22, 0x41 }, // income row text/strip x
		{ 0x77CE3E, 0x12, 0x55 }, // expense "Monthly Expense" header x
		{ 0x77CF16, 0x12, 0x51 }, // expense checkbox x
		{ 0x77CF6E, 0x22, 0x41 }, // expense row text/strip x
		// v2.74.0: the two ordinance NAME-label x sites that used to live here
		// (income 0x77CC23, expense 0x77D0E0) have MOVED OUT of this table.
		// They were its only members whose scaled value overflows imm8, and
		// BOTH lie INSIDE the two 43-byte windows re-encoded by
		// ApplyOrdinanceNameColumnScale below. Leaving them here would make the
		// per-site loop fight the block patch and poison the "(n of N)" health
		// line, which has previously reported a REAL decline. See
		// kOrdinanceNameXImm8Sites (the f < 2.5 path) immediately below.
	};

	// THE ORDINANCE NAME COLUMN. The name labels are SEPARATE windows (ids
	// 0xABCDE03+k via sub_779660) created at their own x const 68; the v2.25.27
	// row move landed the row's eye component on them (MWKID 12:12:09 +
	// screenshot). Both sites are `push imm8`, so the applier's 127 clamp is the
	// whole story and it is the SAME wrong pixel at every tier above 2x:
	//   f=2  ideal 136 -> ships 127, still 23px clear of the eye
	//        [chk 36..68][eye ~84..104][name 127+]      USER-CONFIRMED GOOD
	//   f=3  ideal 204 -> ships 127, i.e. 29px INSIDE the eye
	//        [chk 54..102][eye ~126..156][name 127]     "ying Parking"
	// The v2.25.28 comment that justified the clamp reasoned entirely in 2x
	// numbers - law 53: a tuned correction is only proven in the state it was
	// tuned in, and 2x was that state.
	//
	// BELOW x2.50 nothing changes: these two keep the imm8 clamp path, in the
	// same loop body, in the same order, emitting the same three bytes as
	// v2.73.3. AT OR ABOVE x2.50 they belong to ApplyOrdinanceNameColumnScale
	// and this array is not iterated at all.
	const InsetSite kOrdinanceNameXImm8Sites[] = {
		{ 0x77CC23, 0x44, 0x55 }, // income ordinance-name text x
		{ 0x77D0E0, 0x44, 0x55 }, // expense ordinance-name text x
	};

	// ONE predicate owns the split, so the imm8 path and the block path are
	// exactly complementary - they can never both write and can never both
	// decline. Integer percent, not a float compare, so an ini-parsed "2.50"
	// cannot land on the wrong side of its own gate.
	const int kOrdinanceNameXBlockMinPct = 250;
	bool OrdinanceNameXUsesBlock(float factor)
	{
		return static_cast<int>(std::lround(factor * 100.0f)) >= kOrdinanceNameXBlockMinPct;
	}

	// THE EQUAL-LENGTH BLOCK RE-ENCODE. No imm8 holds 204, and there is no
	// trampoline and no code cave inside sub_77C660, so each site is re-encoded
	// as part of a 43-byte window that buys the 3 bytes `push imm32` costs by
	// shortening three neighbours proven dead across the seam:
	//   mov ecx,eax                  -> xchg eax,ecx            (-1)
	//   mov eax,[esi+d]; push eax    -> push dword [esi+d]      (-1)
	//   mov ecx,[esp+0x28]; push ecx -> push dword [esp+0x38]   (-1)
	// PUSH r/m32 computes its memory operand from the PRE-decrement ESP, which
	// is why 0x28 becomes 0x38 and still names frame slot +20 - the very slot
	// the untouched `mov [esp+0x24]` spill wrote. eax is dead across the seam
	// (the call at [edx+0x1C] returns into it), so the xchg's extra write is
	// unobservable, and the callee pops nothing - which is exactly what stock's
	// own store/reload pair proves.
	//
	// ROUND-TRIPPED OFFLINE, TWICE, BY TWO INDEPENDENT INSTRUMENTS:
	//   python tools\uimap\emu\gate_ordinance_namex.py     GREEN (exit 0)
	//   python tools\ordinance_namex_verify_probe.py       GREEN (exit 0)
	// Both assert, against the shipped exe: 43 == 43 bytes; 10 arguments in the
	// same order with only arg3 changed (sub_779660 is `ret 0x28` = 10 dwords);
	// net ESP -40; the spill AND the parent reload both resolve to frame slot
	// +20; no branch anywhere in .text and no dword anywhere in the image points
	// inside either window. Do not hand-edit these bytes without re-running both.
	enum OrdinanceNameXKind { kOnxIncome, kOnxExpense };
	struct OrdinanceNameXBlock {
		uintptr_t site; int len; int immOff; OrdinanceNameXKind kind; const char* name;
	};
	const OrdinanceNameXBlock kOrdinanceNameXBlocks[] = {
		{ 0x0077CBFC, 43, 34, kOnxIncome,  "N1 income  name-x"  },
		{ 0x0077D0B9, 43, 34, kOnxExpense, "N2 expense name-x"  },
	};
	const int kOrdinanceNameXStockX = 68;          // both sites are `push 0x44`
	const uint8_t kOnxStockIncome[43] = {
		0x8B,0x56,0x10, 0x6A,0x66, 0x6A,0x55, 0x6A,0x44,
		0x68,0x05,0xD3,0x85,0xEA, 0x89,0x54,0x24,0x24, 0x8B,0x10,
		0x6A,0x00, 0x8B,0xC8, 0xFF,0x52,0x1C, 0x8B,0x4C,0x24,0x28,
		0x50, 0x8B,0x86,0x98,0x00,0x00,0x00, 0x50, 0x6A,0x44, 0x55, 0x51 };
	const uint8_t kOnxStockExpense[43] = {
		0x8B,0x4E,0x10, 0x8B,0x10, 0x6A,0x66, 0x6A,0x55, 0x6A,0x44,
		0x68,0x05,0xD3,0x85,0xEA, 0x89,0x4C,0x24,0x24,
		0x6A,0x00, 0x8B,0xC8, 0xFF,0x52,0x1C, 0x8B,0x4C,0x24,0x28,
		0x50, 0x8B,0x86,0x9C,0x00,0x00,0x00, 0x50, 0x6A,0x44, 0x55, 0x51 };

	// How many of the two took. Also the idempotence latch: a second call must
	// never log "does not match the shipped exe" about bytes WE wrote.
	int gOrdinanceNameXBlocks = 0;

	// THE SLIDER-DEPARTMENT BUILDER (v2.25.29, tasks #63-#69). One exe
	// builder (0x7883xx-0x7896xx, Accept/Cancel ids 0x67/0x6D) lays out
	// Public Safety / Health&Education / Utilities / City Beautification /
	// Government: category strips (style 140155B7, the eye rides them) at
	// x=18, category+item names at x=48 (the eye-on-"(eye)ealth" overlap),
	// building-count column at x=258 ("Large Medical Cente7"), sliders at
	// x=260 w=110 (track through "Parks and Recreation"), Subtotal label
	// at x=250. Full creation census: checkpoint v2.25.29 section. Plus
	// the Business Deals empty box (record-free: SetSize(300,100) x5 +
	// close-X at (269,11) - kCityDialogIds is BANNED for its window id).
	struct Imm8Site { uintptr_t site; uint8_t stock; };
	// v2.34.0 SUB-FLYOUT PROVIDER METRICS (task #50). The nested sub-flyout's
	// strip height is stripH = count*(cellH + gap) - gap, and that feeds the
	// container height H = max(stripH, 53) + 50. So the container cannot be
	// BORN at the right height unless the cell and gap are scaled too.
	// These three sites are inside sub_7EAEB0 ONLY - the first-level flyout
	// builder sub_7E7270 carries its OWN copies and must NOT be patched (it is
	// already scaled after birth; patching both double-scales it). Patch by
	// VA, never by pattern - sub_7F4690 calls both builders.
	const Imm8Site kSubFlyoutProviderSites[] = {
		{ 0x7EAEF3, 0x2C }, // cell W  (44)
		{ 0x7EAEF1, 0x2C }, // cell H  (44)
		{ 0x7EAEEF, 0x05 }, // row gap (5)
	};

	const Imm8Site kDeptImm8Sites[] = {
		{ 0x788395, 0x14 }, // department title x (20)
		{ 0x7883DD, 0x12 }, // "Monthly Expense" header x (18)
		{ 0x788ABF, 0x12 }, // category strip+eye row x (18)
		{ 0x788F94, 0x12 }, // category strip+eye row x, 2nd path (18)
		{ 0x788527, 0x30 }, // name column x (48)
		{ 0x78874D, 0x30 }, // name column x (48)
		{ 0x788B3C, 0x30 }, // name column x (48)
		{ 0x788FD3, 0x30 }, // name column x (48)
		{ 0x788D1B, 0x6E }, // slider width (110; 220 clamps to 127)
		// v2.25.30: Business Deals empty-box interior texts (both created
		// via sub_779660 at 0x77C26C / 0x77C292): the TITLE 0xABCE000 at
		// (10,5) and the BODY 0xABCE001 at (15,25). With 2x fonts the
		// ~32px title glyphs run over a body starting at y=25 - the
		// "title isn't fixed" report. Doubling the four coordinates
		// separates them inside the 600x127 box.
		{ 0x77C262, 0x0A }, // bizbox title x (10)
		{ 0x77C260, 0x05 }, // bizbox title y (5)
		{ 0x77C288, 0x0F }, // bizbox body text x (15)
		{ 0x77C286, 0x19 }, // bizbox body text y (25)
		// v2.27.0: the ORDINANCE DESCRIPTION popup ("crushed box") is the
		// SAME window (0x0423278D + content 0x0423278F + texts 0x0ABCE000/
		// 0x0ABCE001) but built by a SECOND code path at 0x78BA2D/0x78BA79,
		// which carries its own copies of the very constants patched above -
		// so the bizbox fix never reached it. MEASURED (POPKID 16:2x):
		// title (10,5 556x37) and body (15,25 795x75), i.e. exact stock. At
		// 2x the title is 37 tall but the body still starts at y=25, so the
		// description runs through the title. Doubling all four separates
		// them (title 10..47, body from 50) and the popup's height, which is
		// computed from body.y + body.height + margin, grows to match.
		{ 0x78BA2B, 0x0A }, // ordinance popup title x (10)
		{ 0x78BA29, 0x05 }, // ordinance popup title y (5)
		{ 0x78BA77, 0x0F }, // ordinance popup body x (15)
		{ 0x78BA75, 0x19 }, // ordinance popup body y (25)
		// v2.26.0 (the full-decode pass, BUDGET-DETAIL-ANATOMY.md): the
		// slider departments run the band stacker's GROUP-2 branch - every
		// group-1 create has a DEAD TWIN, and the earlier header patch hit
		// the twin (0x7883DD). This is the LIVE "Monthly Expense" x:
		{ 0x78898B, 0x12 }, // LIVE dept header x (18), group-2 create 0x788991
		// Hidden ITEM-row slider (vis=0 today, patched for correctness):
		// twin of the category-level 0x788D1B/0x788D1E pair.
		{ 0x78916A, 0x6E }, // item slider width (110; 220 clamps to 127)
		// NEIGHBOR DEALS builder (0x77E600-0x781C8E): deal-name labels x=18,
		// one per deal slot (13 row blocks).
		{ 0x77F711, 0x12 }, { 0x77F949, 0x12 }, { 0x77FC6F, 0x12 },
		{ 0x77FEAD, 0x12 }, { 0x7801CD, 0x12 }, { 0x78040B, 0x12 },
		{ 0x780773, 0x12 }, { 0x780862, 0x12 }, { 0x780AA0, 0x12 },
		{ 0x780DC3, 0x12 }, { 0x781001, 0x12 }, { 0x781323, 0x12 },
		{ 0x781561, 0x12 },
		// Neighbor Deals dept title (x=20, y=8) + its "Monthly ..." header x.
		{ 0x77F5B4, 0x14 }, // deals title x (20)
		// v2.28.2 ADDRESS FIX: the y stanza is at 0x77F5B2 (`6A 08`), NOT
		// 0x77F5B9 - that lands inside the following `push 0xABCDE00` and the
		// shipping build logged "site 0x0077F5B9 bytes unexpected - skipped"
		// at EVERY launch, so this title never doubled its y. Confirmed by
		// byte-dump and by the Master builder's byte-identical stanza at
		// 0x786CA2 (`6A 08 6A 14 68 00 DE BC 0A`): y sits 2 bytes BEFORE x.
		{ 0x77F5B2, 0x08 }, // deals title y (8)
		{ 0x77F60E, 0x12 }, // deals header x (18)
		{ 0x78B9D7, 0x1E }, // v2.28.2 shared text popup x (30) - see the
		                    // right-margin note in the sub-imm8 table
		// v2.29.0 census EXTRAS. Titles: the Ordinances and slider-department
		// dialogs both have a title the deals dialog's equivalent has had
		// scaled since v2.26.0 - these two were simply never in the table.
		// Buttons: the Accept/Cancel PAIR is sized (360x60) and the right
		// button's W-195 anchor is scaled, but the LEFT button's x=14 never
		// was, in any of the five builders.
		{ 0x77C926, 0x08 }, // Ordinances title y (8)
		{ 0x77C928, 0x14 }, // Ordinances title x (20)
		{ 0x788393, 0x08 }, // slider-department title y (8)
		{ 0x77D31F, 0x0E }, // Ordinances button x (14)
		{ 0x78189B, 0x0E }, // Neighbor Deals button x
		{ 0x7854F8, 0x0E }, // refresh-pass button x
		{ 0x787292, 0x0E }, // 650-wide band-set dialog button x
		{ 0x78938A, 0x0E }, // slider-department button x
		{ 0x78BAAD, 0x0B }, // shared text popup close-X y (11)
		// v2.26.1 MASTER BUDGET builder (0x786C00-0x787A00; the eye-icon
		// sub-dialogs Master Power/Police/Fire/...). Its band art family
		// 0x2BFEB0CB-CF now ships 2x so the FRAME doubles; these are its
		// interior columns. Its buttons + scroll arrows are already covered
		// by the button/sub-imm8 tables.
		{ 0x786CA4, 0x14 }, // master title x (20)
		{ 0x786CA2, 0x08 }, // master title y (8)
		{ 0x786E00, 0x15 }, // master header x (21)
		{ 0x787021, 0x5A }, // master funding slider 1 width (90; 180 clamps 127)
		{ 0x787072, 0x5A }, // master funding slider 2 width (90; clamps 127)
		// v2.26.2 the master ROW LOOP, measured live (MWKID 14:41:56: name
		// text 0x0ABCDE06 at (21,y 177x30) = still stock while the sliders
		// had moved to 400/610 - the collision the user photographed).
		// Helper arg order proven by that dump: earlier push = WIDTH,
		// later push = X.
		{ 0x786FAA, 0x15 }, // row building-name x (21)
		{ 0x7870DD, 0x78 }, // row capacity text width (120; 240 clamps 127)
		{ 0x787165, 0x55 }, // row monthly text width (85; 170 clamps 127)
		{ 0x78724A, 0x55 }, // subtotal value width (85; clamps 127)
	};
	struct Imm32Site { uintptr_t site; uint32_t stock; };
	const Imm32Site kDeptImm32Sites[] = {
		// v2.29.0 census EXTRAS: two unpatched column-x twin PAIRS. Each pair
		// is one column written twice in the same builder (law 15) - patching
		// one and not the other would have split the column in half.
		{ 0x77CD9A, 150 }, { 0x77D2B2, 150 }, // Ordinances column x
		{ 0x7806D3, 250 }, { 0x781820, 250 }, // Neighbor Deals column x
		{ 0x788621, 0x102 }, // building-count column x (258)
		{ 0x7887FB, 0x102 },
		{ 0x788C36, 0x102 },
		{ 0x789089, 0x102 },
		{ 0x7888F9, 0x0FA }, // "Subtotal" label x (250)
		{ 0x78931B, 0x0FA },
		{ 0x788D1E, 0x104 }, // slider x (260)
		// v2.26.0: hidden ITEM-row slider x (twin of 0x788D1E).
		{ 0x78916D, 0x104 },
		// NEIGHBOR DEALS: value-text column x=218 (12 row blocks).
		{ 0x77F774, 0x0DA }, { 0x77F98D, 0x0DA }, { 0x77FCD2, 0x0DA },
		{ 0x77FEF1, 0x0DA }, { 0x780230, 0x0DA }, { 0x78044F, 0x0DA },
		{ 0x7808C5, 0x0DA }, { 0x780AE4, 0x0DA }, { 0x780E26, 0x0DA },
		{ 0x781045, 0x0DA }, { 0x781386, 0x0DA }, { 0x7815A5, 0x0DA },
		// NEIGHBOR DEALS: combo BACKING plate x=206 (12; width is art
		// 0x140155B8, already shipped 2x).
		{ 0x77F7F5, 0x0CE }, { 0x77FA4F, 0x0CE }, { 0x77FD59, 0x0CE },
		{ 0x77FFB3, 0x0CE }, { 0x7802B7, 0x0CE }, { 0x780511, 0x0CE },
		{ 0x78094C, 0x0CE }, { 0x780BA6, 0x0CE }, { 0x780EAD, 0x0CE },
		{ 0x781107, 0x0CE }, { 0x78140D, 0x0CE }, { 0x781667, 0x0CE },
		// NEIGHBOR DEALS: combo x=218 (12). Width 120 is a lea disp8 inside
		// sub_7798C0 (max 127 - cannot hold 240): widened by the runtime
		// combo pin in UiSpike instead; the combo class re-lays its own
		// drop arrow from its area, so no arrow patch exists or is needed.
		{ 0x77F815, 0x0DA }, { 0x77FA6F, 0x0DA }, { 0x77FD79, 0x0DA },
		{ 0x77FFD3, 0x0DA }, { 0x7802D7, 0x0DA }, { 0x780531, 0x0DA },
		{ 0x78096C, 0x0DA }, { 0x780BC6, 0x0DA }, { 0x780ECD, 0x0DA },
		{ 0x781127, 0x0DA }, { 0x78142D, 0x0DA }, { 0x781687, 0x0DA },
		// v2.26.1 MASTER BUDGET interior columns (imm32, free of encoding
		// limits): the two funding-slider x positions and the right-hand
		// "Capacity/Monthly" text column.
		{ 0x787024, 0x0C8 }, // master slider 1 x (200)
		{ 0x787075, 0x131 }, // master slider 2 x (305)
		{ 0x7871FB, 0x159 }, // master right column x (345)
		// v2.26.2 master COLUMN HEADERS ("Funding"/"Capacity"/"Monthly",
		// sub_779B80 creates at 0x786E83/0x786EC1/0x786EFE) and the row
		// text columns. Widths and x both imm32 here.
		// v2.26.6: the master header row has FIVE windows, not four - the
		// "Funding" caption lives in 0x0ABCDE02 (create 0x786E48), which
		// stayed at its stock (150,w190) while everything around it moved,
		// so the word sat far left of the sliders it labels (user report).
		// Measured live: BHDR 0x0ABCDE02 (150,68 190x30) = the stock pair.
		{ 0x786E3B, 0x096 }, // header "Funding" x (150)
		{ 0x786E33, 0x0BE }, // header "Funding" width (190)
		{ 0x786E6E, 0x0BE }, // header (DE03) width (190)
		{ 0x786E76, 0x0FF }, // header (DE03) x (255)
		{ 0x786EAC, 0x0DC }, // header "Capacity" width (220)
		{ 0x786EB4, 0x15E }, // header "Capacity" x (350)
		{ 0x786EE6, 0x087 }, // header "Monthly" width (135)
		{ 0x786EF1, 0x1D6 }, // header "Monthly" x (470)
		{ 0x786FA4, 0x0B1 }, // row building-name width (177 - measured live)
		{ 0x7870E0, 0x190 }, // row capacity text x (400 - collided w/ slider 1)
		{ 0x787168, 0x208 }, // row monthly text x (520)
		// v2.26.3: the SUBTOTAL VALUE is its own create (sub_779B80 at
		// 0x787262, align 6 = right edge lands on x) - separate from the
		// "Subtotal" LABEL at 0x7871FB. Patching only the label left the
		// red figure right-aligned at the stock column, i.e. sitting to
		// the LEFT of its own label and outside the subtotal box (user
		// report). Stock relation: right edge = W-130 (650-520), so 2x =
		// 1300-260 = 1040.
		{ 0x78724D, 0x208 }, // subtotal value right-edge x (520)
	};

	// v2.26.2: the master row loop reuses the SLIDER X CONSTANTS in two
	// non-push encodings to place each row's funding NOTCH:
	//   0x786F26  lea ecx,[eax+0xC8]   (notch 1 = base + slider1 x)
	//   0x786F2C  add eax,0x131        (notch 2 = base + slider2 x)
	// Measured proof (MWKID 14:41:56): sliders sat at the patched 400/610
	// while their notches stayed at 263/368 = base 63 + the STOCK 200/305.
	// Scaling these two keeps every notch on its own track.
	struct RawImm32Site { uintptr_t site; int immOff; uint8_t op0; uint8_t op1; uint32_t stock; };
	const RawImm32Site kMasterNotchSites[] = {
		{ 0x786F26, 2, 0x8D, 0x88, 0x0C8 }, // lea ecx,[eax+200]
		{ 0x786F2C, 1, 0x05, 0x00, 0x131 }, // add eax,305 (no modrm byte)
	};

	// v2.26.0: `sub r32, imm8` geometry constants (opcode 0x83, modrm /5).
	// - 0x21 (33) = the SCROLL-ARROW window anchor W-33. The windows the
	//   anatomy doc once called "subtotal plates" (live ids 0x551-0x554)
	//   are the per-section scroll arrows (exe ids 0x451-0x454, 4-state
	//   strip art 140155CB=up/140155CC=down). Stock ink sits at
	//   sectionRight-17; our 2x strips put the drawn cell at +16f inside
	//   the window, so anchoring at W-33f restores ink at R-17f exactly.
	//   14 sites = every arrow create across the four builders.
	// - 0x26 (38) = right-column margin W-38 (the LIVE dept "Monthly
	//   Estimate" header + Neighbor Deals' 14 value-column sites).
	// v2.29.0 PREDICTIVE BATCH. Every site below came from the OFFLINE
	// BUILDER CENSUS (tools\uimap: 192 primitive call sites, 292 geometry
	// constants, 55 twin groups) cross-checked against this file - these are
	// its "EXTRAS": constants the model proved feed a create's x/y/w/h that
	// nothing here patched. NONE of them was reported as a visible defect;
	// they are the ones small enough to read as "slightly off" rather than
	// broken. Values are round(stock * f) as always, expected bytes verified
	// before write. Encodings and twin sets are the model's, not hand-found -
	// which is the point: laws 15/16 (missed encodings, dead twins, second
	// code paths) are what the census exists to kill.
	struct LeaDisp8Site { uintptr_t site; int immOff; int8_t stock; };
	const LeaDisp8Site kBudgetLeaDisp8Sites[] = {
		// Scroll-arrow Y offsets - `lea r32,[r32+4]`. Their X (W-33) has been
		// scaled since v2.26.0; the Y never was, so every arrow sat half a
		// step high inside a doubled section.
		{ 0x77D618, 2, 4 }, { 0x77D65C, 3, 4 },
		{ 0x77D6A2, 2, 4 }, { 0x77D6E6, 3, 4 },   // Ordinances
		{ 0x781AC9, 2, 4 }, { 0x781B0C, 3, 4 },
		{ 0x781B4E, 2, 4 }, { 0x781B91, 3, 4 },   // Neighbor Deals
		{ 0x78750D, 2, 4 }, { 0x78754F, 3, 4 },   // 650-wide band-set dialog
		{ 0x7895A9, 2, 4 }, { 0x7895EE, 3, 4 },
		{ 0x789635, 2, 4 }, { 0x78967A, 3, 4 },   // slider departments
		// Shared text popup close-X: x = W-31.
		{ 0x78BAAF, 2, -31 },
		// SHARED FACTORY heights (bounded: 4 slider + 1 combo consumer).
		// Both fit disp8 at every shipping tier; the combo's WIDTH cannot
		// (240 > 127) and stays a runtime pin.
		{ 0x779548, 2, 14 },   // slider height, factory sub_7794E0
		{ 0x779927, 2, 15 },   // combo height, factory sub_7798C0
	};

	struct SubImm8Site { uintptr_t site; uint8_t stock; };
	const SubImm8Site kBudgetSubImm8Sites[] = {
		{ 0x77D61C, 0x21 }, { 0x77D661, 0x21 }, { 0x77D6A6, 0x21 },
		{ 0x77D6EB, 0x21 }, // Ordinances-family arrows
		{ 0x781ACD, 0x21 }, { 0x781B11, 0x21 }, { 0x781B52, 0x21 },
		{ 0x781B96, 0x21 }, // Neighbor Deals arrows
		{ 0x787511, 0x21 }, { 0x787554, 0x21 }, // Transportation arrows
		{ 0x7895AD, 0x21 }, { 0x7895F3, 0x21 }, { 0x789639, 0x21 },
		{ 0x78967F, 0x21 }, // slider-department arrows
		// v2.28.2 SHARED TEXT POPUP 0x0423278D (ordinance description +
		// Business Deals box). Offline emulation of the builder proved the
		// box's OWN geometry was never scaled: `sub ebx,0x3c` makes it
		// dialogW-60 wide, and the height/x/y-clamp constants sit beside it
		// (0x78B99F push 0x7d = 125 tall, 0x78B9C3 add eax,-0x7d, 0x78B9D7
		// push 0x1e = x 30). At 2x that is 840x125 where stock*2 is 780x250 -
		// and the body, sized parentH-2y by the fill branch, lands 25px tall,
		// which cannot hold ONE line of Arta 28. That is the "cut off"
		// description. 250 and -250 exceed the imm8 ceiling, so the height and
		// the clamp are corrected by the POPBOX sweep pin in UiSpike instead.
		{ 0x78B9A1, 0x3C }, // popup right margin (dialogW - 60)
		// v2.29.0 census EXTRAS - right margins (W-38) and label y offsets
		// that the same builders apply, in the same encodings, never patched.
		{ 0x77C9D6, 0x26 }, { 0x77CCD7, 0x26 }, { 0x77CDE6, 0x26 },
		{ 0x77CE78, 0x26 }, { 0x77D1E5, 0x26 }, { 0x77D2FD, 0x26 },
		{ 0x77C994, 0x02 }, { 0x77C9D2, 0x02 }, { 0x77CE3A, 0x02 },
		{ 0x77CE74, 0x02 },                        // Ordinances
		{ 0x77F658, 0x26 }, { 0x781879, 0x26 },
		{ 0x77F60A, 0x02 }, { 0x77F654, 0x02 },
		{ 0x78076F, 0x02 }, { 0x7807B5, 0x02 },    // Neighbor Deals
		{ 0x788416, 0x26 }, { 0x7885CD, 0x26 }, { 0x7887AE, 0x26 },
		{ 0x788948, 0x26 }, { 0x788BDA, 0x26 }, { 0x789038, 0x26 },
		{ 0x789369, 0x26 },                        // slider departments
		                                           // (0x7889C0 already above)
		{ 0x7889C0, 0x26 }, // LIVE dept "Monthly Estimate" right margin
		{ 0x77F7DB, 0x26 }, { 0x77FA35, 0x26 }, { 0x77FD3F, 0x26 },
		{ 0x77FF99, 0x26 }, { 0x78029D, 0x26 }, { 0x7804F7, 0x26 },
		{ 0x78072D, 0x26 }, { 0x7807B9, 0x26 }, { 0x780932, 0x26 },
		{ 0x780B8C, 0x26 }, { 0x780E93, 0x26 }, { 0x7810ED, 0x26 },
		{ 0x7813F3, 0x26 }, { 0x78164D, 0x26 }, // deals right columns
	};
	// Business Deals empty box: push h(imm8); push w(imm32); SetSize.
	const uintptr_t kBizBoxSizeSites[] = {
		0x77C19E, 0x77C1B0, 0x77C1D9, 0x77C2E0, 0x77C301,
	};
	const uint32_t kStockBizBoxW = 300, kStockBizBoxH = 100;
	const uintptr_t kBizBoxCloseX = 0x77C2BC;  // push 0x10D (269 = 300-31)
	const uintptr_t kBizBoxCloseY = 0x77C2BA;  // push 0x0B  (11)

	// ================= DATA VIEWS LEGEND ORIGINS (v2.37.0, task #78) ======
	// The Data Views legend JUMPS on every view switch: the game re-lays it
	// on each selection from 1x origin constants, and our DVPIN sweep pass
	// could only correct it a tick later, so the wrong frame is presented
	// first (SC4-UI-ENGINE.md 4.7 - the cure is always "born correct").
	//
	// DECODED OFFLINE 2026-07-31. sub_007A04F0 (__thiscall, ret 4, arg =
	// data-view id) is provably the ONE choke point: a whole-image scan of
	// the 7,876,608-byte exe finds the window-id literals 0x8A909E00 /
	// 0x8A909E10 at exactly four addresses, ALL inside it, and it has 13
	// direct callers with no vtable slot. Per legend entry k it does
	//   chip[0x8A909E10+k].SetArea(371, edi+61, GetW()+371, GetH()+edi+61)
	//   row [0x8A909E00+k].SetArea(278, edi+24, GetW()+278, GetH()+edi+24)
	//   edi += 18 * ceil(h/18)          ; h = MEASURED text height
	// so this is 4.7 ROW 3 (patch the builder's constants), not row 4.
	//
	// TWO RULES THIS FAMILY TEACHES:
	// 1. The PITCH IS NOT A CONSTANT and must NEVER be patched - edi grows
	//    by the measured row height rounded up to 18, which already lands on
	//    36 with the 2x font and self-scales at every tier. Only the ORIGIN
	//    is a 1x literal. (Patching the pitch would double-scale it.)
	// 2. Each origin appears in TWO encodings (law 15) - once written into
	//    the rect's L/T, once in the add/lea that computes R/B from
	//    GetW()/GetH(). Patch one and every row is split from its chip.
	//
	// This is also why the DVPIN table must stand down once these land: its
	// fixed 18px pitch FLATTENS any view whose label wraps to two lines
	// (measured 09:32:19.577 - the game left a 72px gap after index 4 and
	// the pin dragged eight windows up by 36px). Patching the origin leaves
	// the game's own per-row deltas untouched, so it is correct there too.
	//
	// NOTE the chip L is the game's 371, not the .UI script's 370, so the
	// patched value is round(371*f)=742 at 2x where the old DVPIN target was
	// 740. 2px, and 742 is the law-correct round(stock*f) - they never both
	// run (see the dvBorn gate in UiSpike).
	//
	// All eight expected byte strings were dumped from the shipping exe and
	// matched before this table was written.
	const LeaDisp8Site kDataViewLegendLeaSites[] = {
		{ 0x7A07D4, 2, 61 }, // chip T   8D 57 3D       lea edx,[edi+0x3D]
		{ 0x7A080B, 3, 61 }, // chip B   8D 44 38 3D    lea eax,[eax+edi+0x3D]
		{ 0x7A08F4, 2, 24 }, // row  T   8D 4F 18       lea ecx,[edi+0x18]
		{ 0x7A0922, 3, 24 }, // row  B   8D 4C 38 18    lea ecx,[eax+edi+0x18]
	};
	const RawImm32Site kDataViewLegendImm32Sites[] = {
		// chip L  C7 84 24 90 00 00 00 73 01 00 00  mov [esp+0x90],0x173
		{ 0x7A07D9, 7, 0xC7, 0x84, 371 },
		// chip R  05 73 01 00 00                    add eax,0x173
		{ 0x7A07F3, 1, 0x05, 0x00, 371 },
		// row  L  C7 44 24 3C 16 01 00 00           mov [esp+0x3C],0x116
		{ 0x7A08FD, 4, 0xC7, 0x44, 278 },
		// row  R  05 16 01 00 00                    add eax,0x116
		{ 0x7A090B, 1, 0x05, 0x00, 278 },
	};
	const int kDataViewLegendSiteCount =
		static_cast<int>(sizeof(kDataViewLegendLeaSites) / sizeof(kDataViewLegendLeaSites[0]) +
			sizeof(kDataViewLegendImm32Sites) / sizeof(kDataViewLegendImm32Sites[0]));
	// How many of the eight actually took. Read by UiSpike's DVPIN pass to
	// decide whether the legend is the GAME's to lay out now.
	int gDataViewLegendPatched = 0;

	// ---------------------------------------------------------------------
	// #57 GRAPHS LEGEND BUDGET (v2.55.0) - the same #78 cure, one panel over.
	//
	// The Graphs chart does NOT lay out its legend. The PANEL builder
	// sub_76D3D0 (0x0076D3D0..0x0076E420) does, once per chart build, from
	// hard-coded literals plus the chart window's WIDTH - and it rebuilds the
	// chart on every graph switch, which is why there is exactly one build per
	// switch and why patching the builder is born-correct for free.
	//
	// The whole legend column is a SIX-CONSTANT right-margin budget measured
	// from winW, and NONE of it scales:
	//     plot right reserve 110 | checkbox left 108 | swatch left 90 (cbox)
	//     or 106 (plain) | swatch 10x6 | swatch->text gap 4 | text right 4
	// Stock packs 16+2+10+3 = 31 px into that 110. At 2x the checkbox WINDOW
	// alone became 32 and the 2x font needed a wider box, so 52 px of content
	// went into the SAME 110 px: checkboxRight == textLeft, the 17 px slot the
	// swatch lives in collapsed to zero, and the 72 px text box wrapped every
	// label 2-4 lines until 2 of 9 rows fell off the bottom.
	// The swatch never moved. Its BUDGET was eaten. Four previous fixes each
	// rewrote an output rect inside that unchanged budget, so the collision
	// only ever moved (v2.54.2/.3/.4, all reverted or superseded).
	//
	// THE STRIP IS TABLED, NEVER COMPUTED. The acceptance oracle
	// (tools\uimap\emu\prove_chart_legend.py) derives it as
	//     strip(f) = sc(16,f)+sc(2,f)+sc(10,f)+sc(4,f)+box(f)+sc(4,f)
	// where box(f) is sized from a PROVABLE glyph bound rather than from f -
	// because the measured 1x->2x ink ratio is 2.121, not 2.00, so a box of
	// round(72*f) wraps MORE than stock. Re-deriving that here by hand is the
	// exact habit that produced the four failed patches, so these numbers are
	// COPIED from the oracle's ACCEPTANCE TARGETS block. A factor with no
	// certified strip DECLINES - it does not guess.
	struct GraphLegendTier { int pct; int strip; };
	const GraphLegendTier kGraphLegendStrips[] = {
		{ 150, 178 }, { 200, 240 }, { 300, 371 },
	};
	int GraphLegendStripFor(float factor)
	{
		const int pct = static_cast<int>(std::lround(factor * 100.0f));
		for (const GraphLegendTier& t : kGraphLegendStrips)
		{
			if (t.pct == pct) { return t.strip; }
		}
		return 0;
	}

	// The five in-place immediates. Every one is a 1-byte field at offset 2,
	// and every one still fits imm8 at f=3 (max is SWATCH_B = 27).
	enum GraphLegendImmKind { kGlDy, kGlBottom, kGlSwatchW, kGlGap, kGlTextR };
	struct GraphLegendImmSite {
		uintptr_t site; uint8_t b0; uint8_t b1; uint8_t stock;
		GraphLegendImmKind kind; const char* name;
	};
	const GraphLegendImmSite kGraphLegendImmSites[] = {
		{ 0x0076E233, 0x8D, 0x48,  3, kGlDy,      "swatch dy   lea ecx,[eax+3]" },
		{ 0x0076E239, 0x83, 0xC0,  9, kGlBottom,  "swatch bot  add eax,9"       },
		{ 0x0076E23C, 0x83, 0xC3, 10, kGlSwatchW, "swatch w    add ebx,0xA"     },
		{ 0x0076E2AF, 0x83, 0xC1,  4, kGlGap,     "swatch->txt add ecx,4"       },
		{ 0x0076E2C8, 0x83, 0xEA,  4, kGlTextR,   "text right  sub edx,4"       },
	};

	// The three equal-length block re-encodings. The four winW margins overflow
	// imm8 at f=2, so they need imm32 forms - but there is NO trampoline and NO
	// code cave: each replacement is byte-for-byte the same LENGTH as the stock
	// block, built by dropping instructions proven dead across the seam. Every
	// one of these bytes is verified offline by
	//   python tools\uimap\emu\gate_graphlegend_leftanchor.py --emit
	// which disassembles the replacement back with capstone and asserts the
	// length, the instruction boundary, the certified imm32, and that both
	// branch targets survive verbatim. Do not hand-edit these without re-running
	// that gate: a wrong rel32 here is a CRASH, not a layout bug.
	enum GraphLegendBlockKind { kGlbPlainSwatch, kGlbCheckbox, kGlbCboxSwatch };
	struct GraphLegendBlock {
		uintptr_t site; int len; GraphLegendBlockKind kind; const char* name;
	};
	const GraphLegendBlock kGraphLegendBlocks[] = {
		{ 0x0076E0E8, 25, kGlbPlainSwatch, "B1 plain swatch anchor"    },
		{ 0x0076E145, 41, kGlbCheckbox,    "B2 checkbox rect"          },
		{ 0x0076E1D6, 42, kGlbCboxSwatch,  "B3 AddChild + cbox swatch" },
	};
	const uint8_t kGlStockB1[25] = {
		0x8B,0x5C,0x24,0x50, 0x8B,0x54,0x24,0x48, 0x8B,0x41,0x44, 0x2B,0xDA,
		0x83,0xEB,0x6A, 0x83,0xF8,0x02, 0x0F,0x86,0xFF,0x00,0x00,0x00 };
	const uint8_t kGlStockB2[41] = {
		0x8B,0x5C,0x24,0x48, 0x8B,0x54,0x24,0x50, 0x8B,0x4C,0x24,0x18,
		0x83,0xC1,0x10, 0x51, 0x2B,0xD3, 0x8B,0x18, 0x8D,0x4A,0xA4, 0x51,
		0x8B,0x4C,0x24,0x20, 0x51, 0x83,0xC2,0x94, 0x52, 0x8B,0xC8,
		0xFF,0x93,0xDC,0x00,0x00,0x00 };
	const uint8_t kGlStockB3[42] = {
		0x8B,0x1E, 0x8B,0x17, 0x8B,0x2B, 0x8B,0xCF, 0xFF,0x52,0x0C, 0x50,
		0x8B,0xCB, 0xFF,0x55,0x38, 0x8B,0x4C,0x24,0x48, 0x8B,0x5C,0x24,0x50,
		0x2B,0xD9, 0x8D,0x8C,0x24,0xF8,0x00,0x00,0x00, 0x83,0xEB,0x5A,
		0xE8,0xE0,0x49,0xE9,0xFF };

	// ROW0_TOP - the legend column's first-row top, 0x0076DE79. STOCK BYTES
	// READ FROM THE SHIPPED EXE (tools\lane3_graphs_vert_probe.py, 7/7 control):
	//   C7 44 24 18 14 00 00 00   mov dword ptr [esp+0x18], 0x14
	// 8 bytes, imm32 at offset 4 (no imm8 ceiling: 60 fits trivially), and the
	// slot [esp+0x18] is DEAD after the row loop - nothing past the loop exit
	// 0x0076E379 reads it, verified in the same listing. The site is outside
	// all three re-encoded blocks (0x0076E0E8+25, 0x0076E145+41, 0x0076E1D6+42:
	// 0x0076DE79+8 = 0x0076DE81 < 0x0076E0E8), so there is no span overlap and
	// gate_patch_families_combined.py stays at zero byte overlaps.
	const uintptr_t kGlRow0Site = 0x0076DE79;
	const uint8_t kGlStockRow0[8] = {
		0xC7,0x44,0x24,0x18, 0x14,0x00,0x00,0x00 };

	// How many of the eight took. UiSpike reads this to decide whether the
	// legend is the GAME's to lay out now (the dvBorn pattern from #78).
	int gGraphLegendPatched = 0;
}

namespace CodePatches
{
	void ApplyRatingArrowScale(float factor)
	{
		const long scaled = std::lround(kStockMultiplier * factor);
		if (scaled == kStockMultiplier)
		{
			return; // identity factor: nothing to do
		}
		if (scaled < 1 || scaled > 127)
		{
			Logger::Get().WriteLine(
				LogLevel::Info,
				"CodePatches: rating multiplier %ld out of imm8 range - patch skipped.",
				scaled);
			return;
		}

		const uintptr_t base = reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
		const uintptr_t delta = base - kImageBase;

		for (uintptr_t site : kRatingImulSites)
		{
			uint8_t* p = reinterpret_cast<uint8_t*>(site + delta);

			// Verify-before-write: opcode must be IMUL imm8 and the operand
			// the stock 7. Anything else means a different exe build - leave
			// the code alone (the arrows stay 1x garnish, nothing breaks).
			if (p[0] != kImulOpcode || p[2] != kStockMultiplier)
			{
				Logger::Get().WriteLine(
					LogLevel::Info,
					"CodePatches: rating site 0x%08X bytes %02X %02X %02X unexpected - skipped.",
					static_cast<uint32_t>(site), p[0], p[1], p[2]);
				continue;
			}

			DWORD oldProtect = 0;
			if (!VirtualProtect(p, 3, PAGE_EXECUTE_READWRITE, &oldProtect))
			{
				Logger::Get().WriteLine(
					LogLevel::Info,
					"CodePatches: VirtualProtect failed at 0x%08X - skipped.",
					static_cast<uint32_t>(site));
				continue;
			}
			p[2] = static_cast<uint8_t>(scaled);
			VirtualProtect(p, 3, oldProtect, &oldProtect);
			FlushInstructionCache(GetCurrentProcess(), p, 3);

			Logger::Get().WriteLine(
				LogLevel::Info,
				"CodePatches: rating arrow multiplier %u -> %ld at 0x%08X.",
				kStockMultiplier, scaled, static_cast<uint32_t>(site));
		}
	}

	void ApplyTooltipWrapScale(float factor)
	{
		const long scaled = std::lround(kStockTipWrap * factor);
		if (scaled == static_cast<long>(kStockTipWrap))
		{
			return; // identity factor: nothing to do
		}

		const uintptr_t base = reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
		const uintptr_t delta = base - kImageBase;

		for (uintptr_t site : kTipWrapSites)
		{
			uint8_t* p = reinterpret_cast<uint8_t*>(site + delta);
			uint32_t cur = 0;
			memcpy(&cur, p + 1, 4);
			// Verify-before-write: must be `push 250`. Anything else means a
			// different exe build - leave it alone (tips stay narrow, nothing
			// breaks).
			if (p[0] != kPushImm32 || cur != kStockTipWrap)
			{
				Logger::Get().WriteLine(
					LogLevel::Info,
					"CodePatches: tip wrap site 0x%08X bytes %02X imm %u unexpected - skipped.",
					static_cast<uint32_t>(site), p[0], cur);
				continue;
			}

			DWORD oldProtect = 0;
			if (!VirtualProtect(p, 5, PAGE_EXECUTE_READWRITE, &oldProtect))
			{
				Logger::Get().WriteLine(
					LogLevel::Info,
					"CodePatches: VirtualProtect failed at 0x%08X - skipped.",
					static_cast<uint32_t>(site));
				continue;
			}
			const uint32_t val = static_cast<uint32_t>(scaled);
			memcpy(p + 1, &val, 4);
			VirtualProtect(p, 5, oldProtect, &oldProtect);
			FlushInstructionCache(GetCurrentProcess(), p, 5);

			Logger::Get().WriteLine(
				LogLevel::Info,
				"CodePatches: tooltip wrap %u -> %ld at 0x%08X.",
				kStockTipWrap, scaled, static_cast<uint32_t>(site));
		}
	}

	// #159. Scale the placement cost readout's runtime buffer so the 2x/3x
	// glyphs are rasterised with room instead of clipped. See the constants
	// above for how the site was identified and why the window was the wrong
	// lever. BOTH sites must take, or NEITHER does: a doubled width with a 1x
	// height would simply move the clip from two edges to one and read as a
	// partial fix.
	void ApplyCostBoxScale(float factor)
	{
		const long newW = std::lround(kStockCostBoxW * factor);
		const long newH = std::lround(kStockCostBoxH * factor);
		if (newW == static_cast<long>(kStockCostBoxW)
			&& newH == static_cast<long>(kStockCostBoxH))
		{
			return; // identity factor: nothing to do
		}
		// The height site is `push imm8`; there is no room to widen it.
		if (newH > 0x7F)
		{
			Logger::Get().WriteLine(
				LogLevel::Info,
				"CodePatches: cost box height %ld exceeds the push imm8 range at "
				"0x%08X and the 2-byte encoding cannot be widened in place - "
				"REFUSING both sites (the readout stays 1x rather than half-"
				"patched).",
				newH, static_cast<uint32_t>(kCostBoxHeightSite));
			return;
		}

		const uintptr_t base = reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
		const uintptr_t delta = base - kImageBase;
		uint8_t* pw = reinterpret_cast<uint8_t*>(kCostBoxWidthSite + delta);
		uint8_t* ph = reinterpret_cast<uint8_t*>(kCostBoxHeightSite + delta);

		// Verify-before-write, BOTH sites, before touching either. A different
		// exe build must leave the game exactly as shipped.
		uint32_t curW = 0;
		memcpy(&curW, pw + 1, 4);
		if (pw[0] != kPushImm32 || curW != kStockCostBoxW
			|| ph[0] != kPushImm8 || ph[1] != kStockCostBoxH)
		{
			Logger::Get().WriteLine(
				LogLevel::Info,
				"CodePatches: cost box sites unexpected (w %02X imm %u @0x%08X, "
				"h %02X %02X @0x%08X) - skipped, readout stays 1x.",
				pw[0], curW, static_cast<uint32_t>(kCostBoxWidthSite),
				ph[0], ph[1], static_cast<uint32_t>(kCostBoxHeightSite));
			return;
		}

		// ONE VirtualProtect spanning both sites (same page). The previous
		// nested pair captured the second "old" protection AFTER the first
		// flip had made the page RWX, so the final restore left live game
		// code writable for the rest of the process (found by the #188
		// signpost review, 2026-08-17, finding 2 - this was its twin).
		uint8_t* lo = (pw < ph) ? pw : ph;
		uint8_t* hi = (pw < ph) ? (ph + 2) : (pw + 5);
		const SIZE_T span = static_cast<SIZE_T>(hi - lo);
		DWORD oldProt = 0;
		if (!VirtualProtect(lo, span, PAGE_EXECUTE_READWRITE, &oldProt))
		{
			Logger::Get().WriteLine(LogLevel::Info,
				"CodePatches: VirtualProtect failed at 0x%08X - cost box skipped.",
				static_cast<uint32_t>(kCostBoxWidthSite));
			return;
		}
		const uint32_t wv = static_cast<uint32_t>(newW);
		memcpy(pw + 1, &wv, 4);
		ph[1] = static_cast<uint8_t>(newH);
		VirtualProtect(lo, span, oldProt, &oldProt);
		FlushInstructionCache(GetCurrentProcess(), lo, span);

		Logger::Get().WriteLine(
			LogLevel::Info,
			"CodePatches: cost box buffer %ux%u -> %ldx%ld (Init at 0x007EEF59; "
			"width 0x%08X, height 0x%08X).",
			kStockCostBoxW, kStockCostBoxH, newW, newH,
			static_cast<uint32_t>(kCostBoxWidthSite),
			static_cast<uint32_t>(kCostBoxHeightSite));

		// --- part two: the right-align anchor, via a cave --------------------
		const long newOrigin = std::lround(kStockCostOrigin * factor);
		uint8_t* po = reinterpret_cast<uint8_t*>(kCostOriginSite + delta);
		if (memcmp(po, kCostOriginStock, sizeof(kCostOriginStock)) != 0)
		{
			Logger::Get().WriteLine(
				LogLevel::Info,
				"CodePatches: cost origin site 0x%08X does not hold the expected "
				"`add ebx,0x7c; push 0x8001` - skipped. The buffer is wider but "
				"the text stays right-aligned at %d, so it will still clip.",
				static_cast<uint32_t>(kCostOriginSite), kStockCostOrigin);
			return;
		}
		if (!gCostCave)
		{
			gCostCave = VirtualAlloc(nullptr, 64, MEM_COMMIT | MEM_RESERVE,
				PAGE_EXECUTE_READWRITE);
		}
		if (!gCostCave)
		{
			Logger::Get().WriteLine(LogLevel::Info,
				"CodePatches: cost origin cave alloc FAILED - skipped (buffer "
				"widened, text still clipped).");
			return;
		}
		uint8_t* cave = static_cast<uint8_t*>(gCostCave);
		int n = 0;
		cave[n++] = 0x81; cave[n++] = 0xC3;                 // add ebx, imm32
		const uint32_t ov = static_cast<uint32_t>(newOrigin);
		memcpy(cave + n, &ov, 4); n += 4;
		memcpy(cave + n, kCostOriginStock + 3, 5); n += 5;  // push 0x8001
		cave[n] = 0xE9;                                     // jmp back
		const int32_t relBack = static_cast<int32_t>(
			(kCostOriginBack + delta) - (reinterpret_cast<uintptr_t>(cave) + n + 5));
		memcpy(cave + n + 1, &relBack, 4); n += 5;

		DWORD oldO = 0;
		if (!VirtualProtect(po, sizeof(kCostOriginStock),
			PAGE_EXECUTE_READWRITE, &oldO))
		{
			Logger::Get().WriteLine(LogLevel::Info,
				"CodePatches: VirtualProtect failed at 0x%08X - cost origin "
				"skipped (buffer widened, text still clipped).",
				static_cast<uint32_t>(kCostOriginSite));
			return;
		}
		const int32_t relTo = static_cast<int32_t>(
			reinterpret_cast<uintptr_t>(cave) - (kCostOriginSite + delta + 5));
		po[0] = 0xE9;
		memcpy(po + 1, &relTo, 4);
		po[5] = 0x90; po[6] = 0x90; po[7] = 0x90;   // pad the 8-byte span
		VirtualProtect(po, sizeof(kCostOriginStock), oldO, &oldO);
		FlushInstructionCache(GetCurrentProcess(), po, sizeof(kCostOriginStock));

		Logger::Get().WriteLine(
			LogLevel::Info,
			"CodePatches: cost text right-align anchor %d -> %ld via cave at %p "
			"(site 0x%08X, resume 0x%08X). Text right edge now sits %ld px inside "
			"a %ld px buffer.",
			kStockCostOrigin, newOrigin, cave,
			static_cast<uint32_t>(kCostOriginSite),
			static_cast<uint32_t>(kCostOriginBack), newW - newOrigin, newW);
	}

	int ApplyIntroVideoScale(float factor)
	{
		if (factor <= 1.01f)
		{
			return 0; // stock tier: leave the game exactly as shipped
		}

		const uintptr_t base = reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
		const uintptr_t delta = base - kImageBase;
		int patched = 0;

		for (const IntroVidSite& s : kIntroVidSites)
		{
			uint8_t* p = reinterpret_cast<uint8_t*>(s.va + delta);
			uint32_t cur = 0;
			memcpy(&cur, p + 1, 4);
			// Verify-before-write: opcode AND operand must both match the
			// 1.1.641 bytes. Any other build leaves the video stock-sized,
			// which is merely small - never wrong.
			if (p[0] != s.opcode || cur != s.stock)
			{
				Logger::Get().WriteLine(
					LogLevel::Info,
					"CodePatches: intro-video site 0x%08X (%s) is %02X imm %u, "
					"expected %02X imm %u - skipped.",
					static_cast<uint32_t>(s.va), s.what, p[0], cur,
					s.opcode, s.stock);
				continue;
			}

			const long scaled = std::lround(s.stock * factor);
			DWORD oldProtect = 0;
			if (!VirtualProtect(p, 5, PAGE_EXECUTE_READWRITE, &oldProtect))
			{
				Logger::Get().WriteLine(
					LogLevel::Info,
					"CodePatches: VirtualProtect failed at 0x%08X - skipped.",
					static_cast<uint32_t>(s.va));
				continue;
			}
			const uint32_t val = static_cast<uint32_t>(scaled);
			memcpy(p + 1, &val, 4);
			VirtualProtect(p, 5, oldProtect, &oldProtect);
			FlushInstructionCache(GetCurrentProcess(), p, 5);
			patched++;

			Logger::Get().WriteLine(
				LogLevel::Info,
				"CodePatches: intro video %s %u -> %ld at 0x%08X.",
				s.what, s.stock, scaled, static_cast<uint32_t>(s.va));
		}

		// ONE summary line naming the resulting surface, so "did the intro
		// patch actually take" is answerable from the log without adding up
		// four lines by hand (law 54: no log line = did not run).
		Logger::Get().WriteLine(
			LogLevel::Info,
			"CodePatches: INTROVID x%.2f - %d of 4 sites patched; video "
			"surface %ld x %ld (stock 768 x 384), still centred at runtime.",
			factor, patched,
			std::lround(768 * factor), std::lround(384 * factor));
		return patched;
	}

	// ============================================================
	// #131 REGIONTILE v2.81.0 — RIDE THE REBUILD, DO NOT FIGHT IT
	// ============================================================
	// v2.80.0 resized the tile buffers from our own tick. It worked (9/9,
	// 260x160 -> 520x320) and the game put them back EVERY FRAME - `total`
	// climbed 9/18/27/36 without bound, the tiles never changed on screen,
	// and clicking died because the hit rect came from a buffer whose size
	// was thrashing. Disarmed same night.
	//
	// The decompile (tools\research\REGION-SCREEN.md) explains it: the buffers
	// are OWNED by sub_7AE510's rebuild, which calls
	//     sub_7AE3D0(srcBuf, &out, double fx, double fy)          __cdecl
	// once per buffer, each time creating a NEW bitmap at Init(srcW+2, srcH+2)
	// (0x007AE439/0x007AE43C) and resampling into it through sub_7AE160.
	// Anything we do outside that call is undone by the next rebuild.
	//
	// So we hook THAT call and enlarge its output before it returns.
	// Everything downstream then follows the game's own rules:
	//   * the composite [item+0x2C] is sized from [item+0x1C]'s rect at
	//     0x007AE6D9 - which we have already grown, so it comes out big;
	//   * the CLICK MASK [item+0x44] is built by sub_7AD400 from [item+0x20]
	//     LATER IN THE SAME REBUILD - so it is generated at the new size and
	//     the hit box cannot disagree with the picture. That is precisely
	//     what v2.80.0 got wrong;
	//   * sub_7B3670 rebuilds the alpha run list from the composite's rect.
	// No latch clearing, no per-tick pass, nothing to fight.
	//
	// ⚠ The game has a real 16.16 tent-filter resampler here (sub_7AE160) but
	// its scale is a literal push 0x3F800000 (1.0f) at 0x7AE186/0x7AE1FD and
	// its step a literal add ecx,0x10000 - it can shift sub-pixel, never
	// resize. We must write the pixels ourselves.
	const uintptr_t kRegionBuildFn = 0x7AE3D0;
	const uintptr_t kTileBufVt = 0x00AC1400;
	typedef void(__cdecl* RegionBuildFn)(void*, void**, double, double);
	RegionBuildFn gRegionBuildOrig = nullptr;
	float gRegionTileFactor = 0.0f;
	int gRegionTileGrown = 0;
	int gRegionTileDeclined = 0;
	bool gRegionTileLoggedFirst = false;
	// #131b: neutralise the game's tent filter and re-apply its alignment in
	// dest space. false restores v2.83.1 behaviour byte-for-byte, for A/B.
	bool gRegionTileSharp = true;

	// Enlarge one freshly-built tile bitmap in place, carrying its pixels.
	// In place matters: the pointer is already stored in the item, and
	// re-Init preserves the refcount at +0x2C and the parent at +0x48.
	// dx,dy: the sub-pixel alignment the game's tent filter used to carry,
	// re-applied as WHOLE DEST pixels. Identical for all four buffers of an
	// item, because sub_7AE510 computes fx/fy ONCE (0x7AE548..0x7AE590) and
	// pushes the same pair to all four sub_7AE3D0 calls - so the colour and the
	// silhouette cannot drift apart, which would put a black rim down one side
	// of every city (sub_7ABCD0 stamps them pixel-for-pixel with no rect
	// intersection - it reads GetRect off the MASK twice, 0x7ABD0D/0x7ABD17).
	bool GrowTileBitmap(void* buf, float f, int32_t dx, int32_t dy)
	{
		__try
		{
			void** vt = *reinterpret_cast<void***>(buf);
			if (reinterpret_cast<uintptr_t>(vt) != kTileBufVt) { return false; }
			uint8_t* b = static_cast<uint8_t*>(buf);
			// Still locked -> the game is mid-read; leave it alone.
			if (*reinterpret_cast<const uint16_t*>(b + 0x38) != 0) { return false; }

			const int32_t w = *reinterpret_cast<const int32_t*>(b + 0x1C);
			const int32_t h = *reinterpret_cast<const int32_t*>(b + 0x20);
			const uint32_t fmt = *reinterpret_cast<const uint32_t*>(b + 0x0C);
			const uint32_t bpp = *reinterpret_cast<const uint32_t*>(b + 0x10);
			// 32bpp only. sub_7B5EF0 picks fmt 4 / bpp 0x10 at <=16-bit video
			// depth; never assume the format, read it back.
			if (bpp != 0x20 || w <= 0 || h <= 0 || w > 4096 || h > 4096)
			{
				return false;
			}
			const int32_t nw = static_cast<int32_t>(w * f + 0.5f);
			const int32_t nh = static_cast<int32_t>(h * f + 0.5f);
			// Zoom-out must be allowed too (#132), so only reject a no-op or an
			// out-of-range result - not a shrink.
			if (nw <= 0 || nh <= 0 || nw > 8192 || nh > 8192) { return false; }
			if (nw == w && nh == h) { return false; }

			const uint8_t* oldBits = *reinterpret_cast<uint8_t* const*>(b + 0x3C);
			const int32_t oldPitch = *reinterpret_cast<const int32_t*>(b + 0x40);
			if (!oldBits || oldPitch < w * 4) { return false; }

			const size_t keep = static_cast<size_t>(w) * h * 4;
			uint8_t* saved = static_cast<uint8_t*>(malloc(keep));
			if (!saved) { return false; }
			for (int32_t y = 0; y < h; y++)
			{
				memcpy(saved + static_cast<size_t>(y) * w * 4,
					oldBits + static_cast<size_t>(y) * oldPitch,
					static_cast<size_t>(w) * 4);
			}

			// Shutdown (vt+0x10) frees the bits AND clears the ready latch at
			// +0x08. Without it Init returns false at its first instruction -
			// that latch was the whole of the five-build initFailed=9.
			reinterpret_cast<char(__thiscall*)(void*)>(vt[0x10 / 4])(buf);
			reinterpret_cast<char(__thiscall*)(void*, uint32_t, uint32_t, uint32_t, uint32_t)>(
				vt[0x0C / 4])(buf, static_cast<uint32_t>(nw), static_cast<uint32_t>(nh), fmt, bpp);

			uint8_t* nb = *reinterpret_cast<uint8_t* const*>(b + 0x3C);
			const int32_t np = *reinterpret_cast<const int32_t*>(b + 0x40);
			const int32_t gw = *reinterpret_cast<const int32_t*>(b + 0x1C);
			const int32_t gh = *reinterpret_cast<const int32_t*>(b + 0x20);
			if (!nb || gw != nw || gh != nh || np < nw * 4)
			{
				// ⛔ RETURNING FALSE IS NOT ENOUGH - PUT THE BUFFER BACK.
				// Init (0x008269B0) writes the new width and height at
				// 0x008269CC/0x008269D3 and sets the ready latch at 0x008269F6
				// even when AllocBits stored a NULL, because AllocBits returns
				// true regardless. So a failed grow leaves a correctly-SIZED
				// bitmap with NO PIXELS wired into the live item; sub_7AE510
				// then sizes the composite from it and the next paint reads its
				// bits. Re-Init at the original size - the memory we just freed
				// makes that overwhelmingly likely to succeed - and restore the
				// pixels we saved. (adversarial review, 2026-08-05)
				reinterpret_cast<char(__thiscall*)(void*)>(vt[0x10 / 4])(buf);
				reinterpret_cast<char(__thiscall*)(void*, uint32_t, uint32_t, uint32_t, uint32_t)>(
					vt[0x0C / 4])(buf, static_cast<uint32_t>(w), static_cast<uint32_t>(h), fmt, bpp);
				uint8_t* rb = *reinterpret_cast<uint8_t* const*>(b + 0x3C);
				const int32_t rp = *reinterpret_cast<const int32_t*>(b + 0x40);
				const bool restored =
					rb && rp >= w * 4 &&
					*reinterpret_cast<const int32_t*>(b + 0x1C) == w &&
					*reinterpret_cast<const int32_t*>(b + 0x20) == h;
				if (restored)
				{
					for (int32_t y = 0; y < h; y++)
					{
						memcpy(rb + static_cast<size_t>(y) * rp,
							saved + static_cast<size_t>(y) * w * 4,
							static_cast<size_t>(w) * 4);
					}
				}
				Logger::Get().WriteLine(
					LogLevel::Info,
					"CodePatches: REGIONTILE grow %dx%d -> %dx%d FAILED (bits=%p"
					" %dx%d pitch %d) - original %s.",
					w, h, nw, nh, nb, gw, gh, np,
					restored ? "restored" : "COULD NOT BE RESTORED");
				free(saved);
				return false;
			}
			// NEAREST NEIGHBOUR IS DELIBERATE AND IS THE SHARPEST RECONSTRUCTION
			// THAT EXISTS. No kernel can add detail a 258x158 bake does not
			// carry, and every smooth kernel is strictly softer - so a smoother
			// filter would make the reported symptom worse, not better. The
			// blur being removed is the GAME's, upstream of here.
			//
			// Half-pixel sample phase: ((2x+1)*w) / (2*nw) instead of (x*w)/nw.
			// The latter systematically displaces the whole image half a dest
			// pixel up and left. Uniform across every buffer of every item, so
			// no two tiles move relative to each other.
			for (int32_t y = 0; y < nh; y++)
			{
				int32_t sy = ((2 * (y - dy) + 1) * h) / (2 * nh);
				if (sy < 0) { sy = 0; }
				if (sy > h - 1) { sy = h - 1; }
				const uint32_t* srow = reinterpret_cast<const uint32_t*>(
					saved + static_cast<size_t>(sy) * w * 4);
				uint32_t* drow = reinterpret_cast<uint32_t*>(nb + static_cast<size_t>(y) * np);
				for (int32_t x = 0; x < nw; x++)
				{
					int32_t sx = ((2 * (x - dx) + 1) * w) / (2 * nw);
					if (sx < 0) { sx = 0; }
					if (sx > w - 1) { sx = w - 1; }
					drow[x] = srow[sx];
				}
			}
			free(saved);

			if (!gRegionTileLoggedFirst)
			{
				gRegionTileLoggedFirst = true;
				Logger::Get().WriteLine(
					LogLevel::Info,
					"CodePatches: REGIONTILE first grow %dx%d -> %dx%d (f=%.2f,"
					" pitch %d->%d) inside the game's own rebuild.",
					w, h, nw, nh, f, oldPitch, np);
			}
			return true;
		}
		__except (EXCEPTION_EXECUTE_HANDLER)
		{
			return false;
		}
	}

	void __cdecl RegionBuildThunk(void* srcBuf, void** ppOut, double fx, double fy)
	{
		// #131b SHARPNESS. sub_7AE3D0 runs the game's 2-tap tent (sub_7AE160)
		// at scale 1.0 with phase (1 - frac(pos)) purely to align the tile to
		// the pixel grid at 1:1. MEASURED on the live positions: at the base
		// tier the phase is 1.00 on every tile in Y and >= 0.80 in X, so the
		// tent is a near-identity and the map is sharp. ZOOM is what breaks
		// that - scaled positions land on arbitrary fractions, the blend
		// reaches 81%, and an edge smears across ~2.5 SCREEN px at f=3.125,
		// roughly doubling the blur of the magnification itself.
		//
		// So hand the tent a phase of exactly 1.0, where its kernel is
		// (tent(-1), tent(0)) = (0, 1) - normalised (0, 16384), and
		// (c*16384 + 8192) >> 14 == c, i.e. a BIT-EXACT copy. Then re-apply
		// the alignment ourselves as whole DEST pixels, which is finer than
		// the source pixel the tent was working in: residual <= 0.5 screen px
		// against 0..2.5 today. Not an exotic path - the game itself produces
		// phase 1.0 on 9 of 9 tiles in Y at the base tier.
		const bool sharpen = gRegionTileSharp && gRegionTileFactor > 0.01f;
		int32_t dx = 0;
		int32_t dy = 0;
		if (sharpen)
		{
			const double fracX = 1.0 - fx; // fx = 1 - frac(posX)
			const double fracY = 1.0 - fy;
			dx = static_cast<int32_t>(fracX * gRegionTileFactor + 0.5);
			dy = static_cast<int32_t>(fracY * gRegionTileFactor + 0.5);
			const int32_t cap = static_cast<int32_t>(gRegionTileFactor) + 1;
			if (dx < 0) { dx = 0; } if (dx > cap) { dx = cap; }
			if (dy < 0) { dy = 0; } if (dy > cap) { dy = cap; }
			gRegionBuildOrig(srcBuf, ppOut, 1.0, 1.0);
		}
		else
		{
			gRegionBuildOrig(srcBuf, ppOut, fx, fy);
		}
		// SHRINK IS A SUPPORTED RANGE, not just growth. This used to early-out
		// at <= 1.001, which is what made stock a hard floor for zoom-out: the
		// basis would shrink the LATTICE while the tiles stayed baked-size,
		// i.e. gaps between the diamonds. GrowTileBitmap has always handled
		// f < 1 (it rejects only a no-op or an out-of-range result), so the
		// whole floor was this one comparison. Zoom-out is also nearly free -
		// a level below stock costs a QUARTER the pixels of one above it.
		// The 0.01 guard is for "factor never set", which is not a zoom.
		if (!ppOut || !*ppOut || gRegionTileFactor <= 0.01f) { return; }
		if (gRegionTileFactor > 0.995f && gRegionTileFactor < 1.005f) { return; } // exact no-op
		if (GrowTileBitmap(*ppOut, gRegionTileFactor, dx, dy)) { gRegionTileGrown++; }
		else
		{
			// The tile kept the game's own tent phase only if we did NOT
			// neutralise it. If we did and the grow declined, this tile lost
			// its sub-pixel alignment - worth knowing, so count it.
			gRegionTileDeclined++;
		}
	}

	int ApplyRegionTileScale(float factor)
	{
		if (factor <= 1.001f) { return 0; }
		gRegionTileFactor = factor;

		const uintptr_t base = reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
		void* target = reinterpret_cast<void*>(kRegionBuildFn + (base - kImageBase));

		MH_Initialize(); // harmless if already initialised
		if (MH_CreateHook(target, reinterpret_cast<void*>(&RegionBuildThunk),
				reinterpret_cast<void**>(&gRegionBuildOrig)) != MH_OK ||
			MH_EnableHook(target) != MH_OK)
		{
			Logger::Get().WriteLine(
				LogLevel::Info,
				"CodePatches: REGIONTILE failed to hook sub_7AE3D0 at %p - region"
				" tiles stay stock.", target);
			gRegionTileFactor = 0.0f;
			return 0;
		}
		Logger::Get().WriteLine(
			LogLevel::Info,
			"CodePatches: REGIONTILE hook installed on sub_7AE3D0 %p (factor %.2f)."
			" Tiles grow inside the game's own rebuild, so the composite and the"
			" click mask are generated at the new size too.",
			target, factor);
		return 1;
	}

	int RegionTileGrown() { return gRegionTileGrown; }
	int RegionTileDeclined() { return gRegionTileDeclined; }

	// #132 ZOOM: write the isometric basis as stock*factor, ALWAYS.
	// ApplyRegionIsoScale verifies the sites still hold their stock values and
	// declines otherwise - right for a one-shot tier patch, useless for a live
	// zoom because the second call would always decline. This one recomputes
	// from the stored stock every time, so it is idempotent and re-appliable.
	// Returns the factor actually written after clamping.
	// Write one .data float as stock*factor. Returns false only if the page
	// could not be made writable.
	bool WriteScaledFloat(uintptr_t va, uint32_t stockBits, float factor, uintptr_t delta)
	{
		uint8_t* p = reinterpret_cast<uint8_t*>(va + delta);
		float stockVal = 0.0f;
		memcpy(&stockVal, &stockBits, 4);
		const float want = stockVal * factor;
		DWORD oldProtect = 0;
		if (!VirtualProtect(p, 4, PAGE_READWRITE, &oldProtect)) { return false; }
		memcpy(p, &want, 4);
		VirtualProtect(p, 4, oldProtect, &oldProtect);
		return true;
	}

	float SetRegionIsoScaleLive(float factor)
	{
		// ⛔ ONLY EVER RE-WRITE FLOATS WE ALREADY OWN. ApplyRegionIsoScale
		// verifies all ten sites against stock and declines the whole set if a
		// third-party mod holds any of them - then logs "NOTHING written,
		// region map stays stock". Without this guard the first wheel notch
		// would blow straight past that contract and overwrite the other mod's
		// values, with no check and no log. (adversarial review, 2026-08-05)
		if (gRegionIsoSitesApplied != kRegionIsoCount)
		{
			return 0.0f;
		}
		if (factor < 0.25f) { factor = 0.25f; }
		if (factor > 8.0f) { factor = 8.0f; }
		const uintptr_t base = reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
		const uintptr_t delta = base - kImageBase;
		for (int i = 0; i < kRegionIsoCount; i++)
		{
			if (!WriteScaledFloat(kRegionIsoSites[i], kRegionIsoStock[i], factor, delta))
			{
				return 0.0f;
			}
		}
		// L2 ships with L1 or not at all (law 43): they are one projection
		// expressed twice, and a mismatched pair puts the overlay icons
		// somewhere other than the thumbnail they belong to.
		for (int i = 0; i < kRegionIso2Count; i++)
		{
			if (!WriteScaledFloat(kRegionIso2Sites[i], kRegionIso2Stock[i], factor, delta))
			{
				return 0.0f;
			}
		}
		gRegionIsoSitesApplied = kRegionIsoCount;
		gRegionIsoLiveFactor = factor;
		return factor;
	}

	// The factor the tile hook will use for buffers the game rebuilds from now
	// on. Zoom changes this so a rebuild lands at the new size.
	void SetRegionTileFactor(float factor)
	{
		gRegionTileFactor = factor;
	}

	void SetRegionTileSharp(bool on) { gRegionTileSharp = on; }
	bool RegionTileSharp() { return gRegionTileSharp; }

	float RegionTileFactor() { return gRegionTileFactor; }

	// ============================================================
	// #132 REGION ZOOM v2.83.0 — TRIGGER THE REBUILD, NEVER RESIZE
	// ============================================================
	// v2.82.0-.2 resized [item+0x1C] and [item+0x2C] in place and CRASHED THE
	// GAME TWICE - both 0xC0000005 at 0x0082653B inside GetPixel, which has no
	// bounds check. The second fired on MOUSE MOVE with EBP = 260, the ORIGINAL
	// tile width: the hit test was still reading a stock-sized structure.
	//
	// An item owns FOUR source bitmaps (+0x1C source, +0x20 alpha mask, +0x24
	// and +0x28 the alternate pair), a composite (+0x2C), and THREE DERIVED run
	// lists - +0x44 (which doubles as the CLICK MASK), +0x50, +0x5C - plus the
	// screen-blit run list +0x38. Resizing the bitmaps leaves the derived
	// structures describing the old size. Clearing byte[+0x34] regenerates
	// +0x38 and nothing else, so there is NO in-place sequence that leaves all
	// of them consistent. That is a design fault, not a bug to patch.
	//
	// sub_7AE510 - the game's own item builder - rebuilds every one of them:
	//   4x sub_7AE3D0 (where #131's hook already grows the output)
	//   composite Init() sized from the NEW +0x1C          0x007AE706
	//   3x sub_7AD400 from the NEW +0x20 -> +0x44/+0x50/+0x5C
	//   sub_7AA6A0 -> the label anchor +0x68/+0x6C
	// So zoom re-runs THAT, exactly as #131 rides it. Three measured facts
	// shape the replay, each of which would crash or corrupt if ignored:
	//
	// 1. sub_7AE510 NEVER READS THE BASIS. Positions are cached in
	//    +0x10/+0x14, written once by sub_7B13C0 at Init. Patching the basis
	//    alone moves nothing - we must write the positions ourselves, BEFORE
	//    the call, because sub_7AE510 reads them for its sub-pixel shift.
	// 2. AFTER THE INITIAL BUILD, [item+0x20] IS NULL. sub_7B13C0 deinits and
	//    releases the mask the moment sub_7AE510 returns. A naive second call
	//    hands NULL to sub_7AE3D0, which leaves it NULL, and sub_7ABCD0 then
	//    dereferences it. A replay that does not restore the mask CRASHES.
	// 3. sub_7ABB80 IS NOT THE FIX FOR (2). It re-seeds +0x1C/+0x20 from the
	//    screen's DEFAULT PLACEHOLDER ART - right for the establish-city path
	//    that calls it (a new city has no thumbnail), fatal here: every city
	//    would lose its picture. Only sub_5DDA40, inside sub_7B13C0, loads the
	//    real savegame thumbnail.
	//
	// One thing answers all three, and also kills a fourth problem (sub_7AE510
	// compounds - it reads the CURRENT bitmaps and adds +2 px, so with our hook
	// armed each call is (size+2)*F on top of the last, and nearest-neighbour
	// cannot undo it): SNAPSHOT THE PRISTINE ART. We hook sub_7AE510 and, on
	// entry, AddRef the four bitmaps and record the position. That is the last
	// moment the un-shifted savegame art exists. Every zoom level is then
	// rebuilt from that same origin at an ABSOLUTE factor - no drift, no
	// placeholder art, no null mask, and zoom-out is exact rather than lossy.
	const uintptr_t kRegionItemBuildFn = 0x7AE510;   // __thiscall(screen, item)
	const uintptr_t kRegionPanClampFn = 0x7AB7C0;    // __thiscall(screen)
	const uintptr_t kRegionInvalidateFn = 0x7B29E0;  // __thiscall(view)
	const uintptr_t kRegionOverlayFn = 0x7B5430;     // __thiscall(view, item)

	const int kScreenViewOff = 0xE0;
	const int kScreenItemsBeg = 0x118;
	const int kScreenItemsEnd = 0x11C;
	const int kScreenScrollX = 0x178;
	const int kScreenScrollY = 0x17C;
	const int kItemStride = 0x80;
	const int kItemCellX = 0x08;
	const int kItemCellY = 0x0C;
	const int kItemPosX = 0x10;
	const int kItemPosY = 0x14;
	const int kItemMaskOff = 0x20;
	const int kItemBmpOff[4] = { 0x1C, 0x20, 0x24, 0x28 };

	// Total tile-bitmap budget for one zoom step, across every item. The
	// per-edge cap (RegionZoomMaxEdge) bounds ONE bitmap; this bounds the
	// WORKING SET, which is what actually exhausts an address space.
	// 512 MB, not the 256 MB first shipped: SimCity 4.exe carries
	// IMAGE_FILE_LARGE_ADDRESS_AWARE (characteristics 0x012F), so it gets 4 GB
	// of user space on 64-bit Windows rather than 2 GB - checked, not assumed.
	// MEASURED: a 48-city region at the old +2 limit holds 149 MB of tiles.
	const double kRegionZoomByteBudget = 512.0 * 1024.0 * 1024.0;

	// AddRef is vt+0x04 and Release is vt+0x08 - read off sub_7AE510's own
	// prologue (call [eax+4] at 0x7AE532, call [eax+8] at 0x7AE59E), not
	// assumed from the IUnknown layout.
	typedef void(__fastcall* ItemBuildFn)(void*, void*, void*);
	typedef void(__fastcall* ViewInvalidateFn)(void*, void*);
	typedef void(__fastcall* PanClampFn)(void*, void*);
	typedef void(__fastcall* ItemOverlayFn)(void*, void*, void*);
	ItemBuildFn gItemBuildOrig = nullptr;

	struct PristineItem
	{
		int32_t cellX;
		int32_t cellY;
		void* bmp[4];
		float posX;
		float posY;
		float factor; // the basis factor posX/posY were computed against
	};
	// Keyed by REGION CELL, never by item pointer: sub_7B13C0 push_backs one
	// item per city and the vector reallocates as it grows, so any pointer
	// captured during the build is stale by the end of it. The cell is the
	// item's true identity and survives the move.
	const int kPristineMax = 1024;
	PristineItem gPristine[kPristineMax];
	int gPristineCount = 0;
	int gPristineOverflow = 0;
	int gPristineFaults = 0;
	int gPristineDeclinedRefs = 0;
	int gRegionZoomRebuilt = 0;
	int gRegionZoomSkipped = 0;

	// Returns false if the ref was NOT taken - the caller must then not hold
	// the pointer. AddRef is vt+0x04, read off sub_7AE510's own prologue
	// (call [eax+4] at 0x7AE532), not assumed from the IUnknown layout.
	bool BmpAddRefChecked(void* b)
	{
		if (!b) { return false; }
		__try
		{
			void** vt = *reinterpret_cast<void***>(b);
			if (reinterpret_cast<uintptr_t>(vt) != kTileBufVt) { return false; }
			reinterpret_cast<void(__thiscall*)(void*)>(vt[0x04 / 4])(b);
			return true;
		}
		__except (EXCEPTION_EXECUTE_HANDLER) { return false; }
	}

	void BmpAddRef(void* b) { BmpAddRefChecked(b); }

	void BmpRelease(void* b)
	{
		if (!b) { return; }
		__try
		{
			void** vt = *reinterpret_cast<void***>(b);
			if (reinterpret_cast<uintptr_t>(vt) != kTileBufVt) { return; }
			reinterpret_cast<void(__thiscall*)(void*)>(vt[0x08 / 4])(b);
		}
		__except (EXCEPTION_EXECUTE_HANDLER) {}
	}

	// Deinit (vt+0x10) frees the pixels and clears the ready latch, exactly as
	// sub_7B13C0 does to the mask once the run lists have consumed it.
	void BmpDeinit(void* b)
	{
		if (!b) { return; }
		__try
		{
			void** vt = *reinterpret_cast<void***>(b);
			if (reinterpret_cast<uintptr_t>(vt) != kTileBufVt) { return; }
			reinterpret_cast<char(__thiscall*)(void*)>(vt[0x10 / 4])(b);
		}
		__except (EXCEPTION_EXECUTE_HANDLER) {}
	}

	// Read one bitmap's width/height. Returns false if it is not one of ours.
	bool BmpSize(void* b, int32_t* w, int32_t* h)
	{
		if (!b) { return false; }
		__try
		{
			void** vt = *reinterpret_cast<void***>(b);
			if (reinterpret_cast<uintptr_t>(vt) != kTileBufVt) { return false; }
			const uint8_t* p = static_cast<const uint8_t*>(b);
			*w = *reinterpret_cast<const int32_t*>(p + 0x1C);
			*h = *reinterpret_cast<const int32_t*>(p + 0x20);
			return true;
		}
		__except (EXCEPTION_EXECUTE_HANDLER) { return false; }
	}

	PristineItem* FindPristine(int32_t cx, int32_t cy)
	{
		for (int i = 0; i < gPristineCount; i++)
		{
			if (gPristine[i].cellX == cx && gPristine[i].cellY == cy)
			{
				return &gPristine[i];
			}
		}
		return nullptr;
	}

	void ReleasePristineSlot(PristineItem* slot)
	{
		for (int i = 0; i < 4; i++)
		{
			BmpRelease(slot->bmp[i]);
			slot->bmp[i] = nullptr;
		}
	}

	void CapturePristine(void* item)
	{
		int32_t cx = 0;
		int32_t cy = 0;
		void* bmp[4] = { nullptr, nullptr, nullptr, nullptr };
		float px = 0.0f;
		float py = 0.0f;
		__try
		{
			const uint8_t* it = static_cast<const uint8_t*>(item);
			cx = *reinterpret_cast<const int32_t*>(it + kItemCellX);
			cy = *reinterpret_cast<const int32_t*>(it + kItemCellY);
			for (int i = 0; i < 4; i++)
			{
				bmp[i] = *reinterpret_cast<void* const*>(it + kItemBmpOff[i]);
			}
			px = *reinterpret_cast<const float*>(it + kItemPosX);
			py = *reinterpret_cast<const float*>(it + kItemPosY);
		}
		__except (EXCEPTION_EXECUTE_HANDLER)
		{
			// A capture that silently fails would show up later only as "zoom
			// skipped that tile", with no way to tell why. Say it once.
			if (gPristineFaults++ == 0)
			{
				Logger::Get().WriteLine(
					LogLevel::Info,
					"CodePatches: REGIONZOOM snapshot FAULTED reading item %p -"
					" that tile will be skipped by any zoom.", item);
			}
			return;
		}

		PristineItem* slot = FindPristine(cx, cy);
		if (!slot)
		{
			if (gPristineCount >= kPristineMax)
			{
				if (gPristineOverflow++ == 0)
				{
					Logger::Get().WriteLine(
						LogLevel::Info,
						"CodePatches: REGIONZOOM snapshot table FULL at %d items -"
						" this region has more cities than the table holds, and"
						" the rest will not zoom. Raise kPristineMax.",
						kPristineMax);
				}
				return;
			}
			slot = &gPristine[gPristineCount++];
			memset(slot, 0, sizeof(PristineItem));
		}
		else
		{
			// Re-capture (the establish-city path legitimately replaces an
			// item's art). Drop our refs on the old set first.
			ReleasePristineSlot(slot);
		}
		slot->cellX = cx;
		slot->cellY = cy;
		for (int i = 0; i < 4; i++)
		{
			// STORE ONLY WHAT WE MANAGED TO REF. BmpAddRef declines silently on
			// any object whose vtable is not 0x00AC1400, and a stashed pointer
			// we do not hold a ref to is one the game frees at 0x7AE7A0 - which
			// ReplayOneItem would later write straight back into the live item,
			// where sub_7AE510 calls through it. Currently unreachable (the
			// only other IGZBuffer vtable, 0x00ADB418, is built at exactly one
			// device-surface site) but the cost of being wrong is a
			// use-after-free, so make the invariant structural.
			if (bmp[i] && !BmpAddRefChecked(bmp[i]))
			{
				gPristineDeclinedRefs++;
				slot->bmp[i] = nullptr;
				continue;
			}
			slot->bmp[i] = bmp[i];
		}
		slot->posX = px;
		slot->posY = py;
		slot->factor = (gRegionIsoLiveFactor > 0.0f) ? gRegionIsoLiveFactor : 1.0f;

		// INSTALLED != EXECUTED (law 47). One affirmative line proving the hook
		// actually fired and what it caught, so "zoom did nothing" can never be
		// diagnosed from an absence.
		if (gPristineCount == 1)
		{
			int32_t w = 0;
			int32_t h = 0;
			const bool got = BmpSize(slot->bmp[0], &w, &h);
			Logger::Get().WriteLine(
				LogLevel::Info,
				"CodePatches: REGIONZOOM first snapshot - cell (%d,%d), pristine"
				" source %s, mask %s, alt pair %s, basis factor %.2f.",
				cx, cy,
				got ? "captured" : "MISSING",
				slot->bmp[1] ? "captured" : "none",
				(slot->bmp[2] && slot->bmp[3]) ? "captured" : "none",
				slot->factor);
			if (got)
			{
				Logger::Get().WriteLine(
					LogLevel::Info,
					"CodePatches: REGIONZOOM   pristine tile is %dx%d - every"
					" zoom level rebuilds from this, never from the last one.",
					w, h);
			}
		}
	}

	// The detour. __thiscall passes `this` in ECX and the arg on the stack,
	// which is exactly __fastcall with an unused EDX.
	void __fastcall ItemBuildThunk(void* screen, void* edx, void* item)
	{
		CapturePristine(item);
		gItemBuildOrig(screen, edx, item);
	}

	int ApplyRegionZoomHook()
	{
		const uintptr_t base = reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
		void* target = reinterpret_cast<void*>(kRegionItemBuildFn + (base - kImageBase));
		MH_Initialize(); // harmless if already initialised
		if (MH_CreateHook(target, reinterpret_cast<void*>(&ItemBuildThunk),
				reinterpret_cast<void**>(&gItemBuildOrig)) != MH_OK ||
			MH_EnableHook(target) != MH_OK)
		{
			Logger::Get().WriteLine(
				LogLevel::Info,
				"CodePatches: REGIONZOOM failed to hook sub_7AE510 at %p - zoom"
				" stays off (the tier scale is unaffected).", target);
			gItemBuildOrig = nullptr;
			return 0;
		}
		Logger::Get().WriteLine(
			LogLevel::Info,
			"CodePatches: REGIONZOOM hook installed on sub_7AE510 %p. It snapshots"
			" each item's four pristine bitmaps so every zoom level rebuilds from"
			" the same origin instead of compounding.", target);
		return 1;
	}

	void ClearRegionPristine()
	{
		for (int i = 0; i < gPristineCount; i++) { ReleasePristineSlot(&gPristine[i]); }
		gPristineCount = 0;
		gPristineOverflow = 0;
	}

	int RegionPristineCount() { return gPristineCount; }

	// Is a zoom capable of producing a COHERENT result right now? All three
	// halves must be live, because each one alone is a known-bad shape:
	//   * the iso patch verified and took   -> or we would be overwriting
	//     another mod's basis floats;
	//   * the sub_7AE3D0 tile hook          -> or the lattice grows and the
	//     tiles do not, i.e. gaps between the diamonds;
	//   * the sub_7AE510 snapshot hook      -> or a rebuild compounds and
	//     crashes on the mask sub_7B13C0 nulls.
	bool RegionZoomOperable()
	{
		return gRegionIsoSitesApplied == kRegionIsoCount &&
			gRegionBuildOrig != nullptr &&
			gItemBuildOrig != nullptr;
	}

	bool ReadPtr(const void* obj, int off, void** out)
	{
		__try
		{
			*out = *reinterpret_cast<void* const*>(
				static_cast<const uint8_t*>(obj) + off);
			return true;
		}
		__except (EXCEPTION_EXECUTE_HANDLER) { return false; }
	}

	// Restore one item to its pristine art at the new position, then let the
	// game rebuild every derived structure from it.
	bool ReplayOneItem(void* screen, void* view, uint8_t* it, const PristineItem* pr,
		float factor)
	{
		__try
		{
			const float ratio = (pr->factor > 0.0f) ? (factor / pr->factor) : factor;
			// POSITIONS FIRST - sub_7AE510 reads +0x10/+0x14 for its sub-pixel
			// shift. Both are linear and homogeneous in the basis
			// (x = cellX*B0 + (cellY+span)*B2), so scaling the stored value is
			// exactly what recomputing from the scaled basis would give.
			*reinterpret_cast<float*>(it + kItemPosX) = pr->posX * ratio;
			*reinterpret_cast<float*>(it + kItemPosY) = pr->posY * ratio;

			for (int i = 0; i < 4; i++)
			{
				void** slot = reinterpret_cast<void**>(it + kItemBmpOff[i]);
				void* cur = *slot;
				if (cur == pr->bmp[i]) { continue; }
				*slot = pr->bmp[i];
				BmpAddRef(pr->bmp[i]);
				BmpRelease(cur);
			}
		}
		__except (EXCEPTION_EXECUTE_HANDLER) { return false; }

		// The trampoline, not the hooked address - re-entering the detour
		// would overwrite the pristine snapshot with the art we just restored.
		gItemBuildOrig(screen, nullptr, it);

		// Unconditionally, exactly as the establish-city path does at
		// 0x007B0106. It reprojects the airport/seaport overlays from the L2
		// basis into item+0x74/+0x78/+0x7C, clears byte[it+0x34], and marks
		// every cache cell dirty. Skipping it when the overlay pass is
		// currently off would leave those icons at pre-zoom offsets for
		// whenever the user next switches view mode - nothing else rebuilds
		// them. Do what the game does.
		{
			const uintptr_t base = reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
			ItemOverlayFn fn = reinterpret_cast<ItemOverlayFn>(
				kRegionOverlayFn + (base - kImageBase));
			fn(view, nullptr, it);
		}

		// Mirror sub_7B13C0: once the three run lists have consumed the mask it
		// is dead weight, and at 3x it is the largest buffer on the item.
		__try
		{
			void** slot = reinterpret_cast<void**>(it + kItemMaskOff);
			void* mask = *slot;
			if (mask)
			{
				*slot = nullptr;
				BmpDeinit(mask);
				BmpRelease(mask);
			}
		}
		__except (EXCEPTION_EXECUTE_HANDLER) { return false; }
		return true;
	}

	int RegionZoomRebuild(void* screen, float factor, int maxEdge, int* outSkipped)
	{
		gRegionZoomRebuilt = 0;
		gRegionZoomSkipped = 0;
		if (outSkipped) { *outSkipped = 0; }
		if (!screen || !RegionZoomOperable())
		{
			// Refusing here rather than proceeding is the point: with the tile
			// hook missing we could still move the basis, and that produces the
			// gaps-between-diamonds failure #131 exists to prevent.
			Logger::Get().WriteLine(
				LogLevel::Info,
				"CodePatches: REGIONZOOM not operable (iso %d/4, tile hook %s, snapshot"
				" hook %s) - nothing written.",
				gRegionIsoSitesApplied,
				gRegionBuildOrig ? "live" : "MISSING",
				gItemBuildOrig ? "live" : "MISSING");
			return 0;
		}
		// No floor at stock any more - the tile hook shrinks as well as grows,
		// so the basis and the tiles stay coupled below 1.0. SetRegionIsoScaleLive
		// still clamps the basis to [0.25, 8.0].
		if (factor < 0.25f) { factor = 0.25f; }

		void* view = nullptr;
		uint8_t* beg = nullptr;
		uint8_t* end = nullptr;
		if (!ReadPtr(screen, kScreenViewOff, &view) || !view) { return 0; }
		if (!ReadPtr(screen, kScreenItemsBeg, reinterpret_cast<void**>(&beg)) ||
			!ReadPtr(screen, kScreenItemsEnd, reinterpret_cast<void**>(&end)) ||
			!beg || end < beg)
		{
			return 0;
		}
		const int count = static_cast<int>((end - beg) / kItemStride);
		if (count <= 0 || count > 4096) { return 0; }

		// ============================================================
		// VALIDATE EVERYTHING BEFORE WRITING ANYTHING.
		// ============================================================
		// The basis is a GLOBAL: once written, every item's lattice position has
		// moved whether or not that item's tiles were rebuilt. So a per-item skip
		// discovered halfway through the loop is not recoverable by skipping - it
		// IS the "half the map at one scale" state. Every reason to decline has
		// to be found up front, over the LIVE item list, not over the snapshot
		// table. (adversarial review, 2026-08-05: the previous order checked the
		// size cap against gPristine[] and then committed the basis regardless.)
		double totalBytes = 0.0;
		double transientBytes = 0.0;
		for (int i = 0; i < count; i++)
		{
			const uint8_t* it = beg + static_cast<size_t>(i) * kItemStride;
			int32_t cx = 0;
			int32_t cy = 0;
			__try
			{
				cx = *reinterpret_cast<const int32_t*>(it + kItemCellX);
				cy = *reinterpret_cast<const int32_t*>(it + kItemCellY);
			}
			__except (EXCEPTION_EXECUTE_HANDLER)
			{
				Logger::Get().WriteLine(
					LogLevel::Info,
					"CodePatches: REGIONZOOM REFUSED - item %d of %d is unreadable."
					" Nothing written.", i, count);
				return 0;
			}
			const PristineItem* pr = FindPristine(cx, cy);
			if (!pr || !pr->bmp[0])
			{
				// No snapshot means we never saw this item built, so we cannot
				// rebuild it from its origin - and rebuilding it from its CURRENT
				// bitmaps would compound. One uncovered item disqualifies the
				// whole step.
				Logger::Get().WriteLine(
					LogLevel::Info,
					"CodePatches: REGIONZOOM REFUSED - cell (%d,%d) has no pristine"
					" snapshot (%d live items, %d snapshots%s). Nothing written.",
					cx, cy, count, gPristineCount,
					gPristineOverflow ? ", table OVERFLOWED" : "");
				return 0;
			}
			// Every bitmap the rebuild will produce, not just the source: the
			/// mask and the alternate pair are grown by the same hook and cost
			// the same memory, and the composite is sized from the new source.
			// COUNT WHAT IS ACTUALLY RESIDENT. Only the source (+0x1C) and the
			// composite (+0x2C) persist; ReplayOneItem Deinits and releases the
			// mask (+0x20) as soon as the run lists have consumed it, exactly
			// as sub_7B13C0 does, so at most ONE mask is live at a time. The
			// first accounting charged for every slot as though it persisted
			// and over-stated the working set by ~50%, which would have refused
			// zoom levels that fit comfortably.
			for (int k = 0; k < 4; k++)
			{
				int32_t w = 0;
				int32_t h = 0;
				if (!BmpSize(pr->bmp[k], &w, &h)) { continue; }
				const int32_t nw = static_cast<int32_t>((w + 2) * factor + 0.5f);
				const int32_t nh = static_cast<int32_t>((h + 2) * factor + 0.5f);
				if (maxEdge > 0 && (nw > maxEdge || nh > maxEdge))
				{
					Logger::Get().WriteLine(
						LogLevel::Info,
						"CodePatches: REGIONZOOM REFUSED x%.2f - a %dx%d bitmap would"
						" become %dx%d, past the %d px edge cap. Nothing written.",
						factor, w, h, nw, nh, maxEdge);
					return 0;
				}
				if (k == 0)
				{
					// source + the composite sized from it, both resident
					totalBytes += 2.0 * static_cast<double>(nw) * nh * 4.0;
				}
				else if (k == 1)
				{
					// the mask: transient, so charge for exactly one of them
					const double one = static_cast<double>(nw) * nh * 4.0;
					if (one > transientBytes) { transientBytes = one; }
				}
				else
				{
					// the alternate pair does persist when present
					totalBytes += static_cast<double>(nw) * nh * 4.0;
				}
			}
		}

		// A PER-EDGE CAP DOES NOT BOUND THE WORKING SET. 30 cities at factor 7.6
		// each want ~16MB of source plus ~16MB of composite - about a gigabyte,
		// inside a 32-bit process. And an allocation failure is not clean: Init
		// (0x008269B0) sets the width, height AND the ready latch even when
		// AllocBits stored a NULL, so a failed grow leaves a correctly-sized
		// bitmap with no pixels wired into the live item.
		totalBytes += transientBytes;
		if (totalBytes > kRegionZoomByteBudget)
		{
			Logger::Get().WriteLine(
				LogLevel::Info,
				"CodePatches: REGIONZOOM REFUSED x%.2f - %d items would need %.0f MB"
				" of tile bitmaps, past the %.0f MB budget. Nothing written.",
				factor, count, totalBytes / (1024.0 * 1024.0),
				kRegionZoomByteBudget / (1024.0 * 1024.0));
			return 0;
		}

		const float prevFactor =
			(gRegionIsoLiveFactor > 0.0f) ? gRegionIsoLiveFactor : 1.0f;
		const float applied = SetRegionIsoScaleLive(factor);
		if (applied <= 0.0f)
		{
			Logger::Get().WriteLine(
				LogLevel::Info,
				"CodePatches: REGIONZOOM basis write FAILED - the map may now be"
				" sheared. Nothing rebuilt.");
			return 0;
		}
		SetRegionTileFactor(applied);

		for (int i = 0; i < count; i++)
		{
			uint8_t* it = beg + static_cast<size_t>(i) * kItemStride;
			int32_t cx = 0;
			int32_t cy = 0;
			__try
			{
				cx = *reinterpret_cast<const int32_t*>(it + kItemCellX);
				cy = *reinterpret_cast<const int32_t*>(it + kItemCellY);
			}
			__except (EXCEPTION_EXECUTE_HANDLER)
			{
				gRegionZoomSkipped++;
				continue;
			}
			const PristineItem* pr = FindPristine(cx, cy);
			// No snapshot means we never saw this item built. Rebuilding it
			// from its CURRENT bitmaps would compound; leaving it alone is the
			// honest failure.
			if (!pr || !pr->bmp[0]) { gRegionZoomSkipped++; continue; }
			if (ReplayOneItem(screen, view, it, pr, applied))
			{
				gRegionZoomRebuilt++;
			}
			else
			{
				gRegionZoomSkipped++;
			}
		}

		// ROLL THE BASIS BACK IF NOTHING WAS REBUILT. The basis is global and
		// was committed above; leaving it moved with every tile still at the
		// old size is the gaps-between-diamonds state, and the caller's log
		// would have said "nothing changed" while the lattice had in fact
		// moved. A lying log line is worse than the defect it hides.
		if (gRegionZoomRebuilt == 0)
		{
			SetRegionIsoScaleLive(prevFactor);
			SetRegionTileFactor(prevFactor);
			Logger::Get().WriteLine(
				LogLevel::Info,
				"CodePatches: REGIONZOOM 0 of %d items rebuilt - basis rolled back"
				" to x%.3f. The map is unchanged.", count, prevFactor);
			if (outSkipped) { *outSkipped = gRegionZoomSkipped; }
			return 0;
		}
		if (gRegionZoomSkipped != 0)
		{
			// Pre-validation should have made this unreachable, so if it fires
			// the map really is mixed and the honest thing is to say so loudly
			// rather than roll back over tiles that HAVE been rebuilt.
			Logger::Get().WriteLine(
				LogLevel::Info,
				"CodePatches: ⚠ REGIONZOOM PARTIAL - %d rebuilt, %d skipped after"
				" pre-validation passed. The map is now MIXED-SCALE; leave the"
				" region and return to rebuild it cleanly.",
				gRegionZoomRebuilt, gRegionZoomSkipped);
		}

		const uintptr_t base = reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
		const uintptr_t delta = base - kImageBase;

		// The pan clamp is derived from the basis and the cell bounding box,
		// and the game computes it in exactly ONE place - inside sub_7B13C0 at
		// Init. Without this call the clamp keeps the old map's extent and the
		// view scrolls off the enlarged region.
		reinterpret_cast<PanClampFn>(kRegionPanClampFn + delta)(screen, nullptr);

		// Keep the same ground under the viewport. This is the authoritative
		// scroll accumulator; view+0xE8/+0xEC is derived from the camera every
		// frame, so writing that instead would be overwritten immediately.
		__try
		{
			const float r = applied / prevFactor;
			float* sx = reinterpret_cast<float*>(static_cast<uint8_t*>(screen) + kScreenScrollX);
			float* sy = reinterpret_cast<float*>(static_cast<uint8_t*>(screen) + kScreenScrollY);
			*sx *= r;
			*sy *= r;
		}
		__except (EXCEPTION_EXECUTE_HANDLER) {}

		// Every cache cell dirty, every +0x34 cleared - which is what makes the
		// draw path recopy each composite and rebuild the +0x38 run list at the
		// new size on the next paint.
		reinterpret_cast<ViewInvalidateFn>(kRegionInvalidateFn + delta)(view, nullptr);

		if (outSkipped) { *outSkipped = gRegionZoomSkipped; }
		return gRegionZoomRebuilt;
	}

	int ApplyRegionIsoScale(float factor)
	{
		gRegionIsoSitesApplied = 0;
		if (factor <= 1.001f)
		{
			return 0; // reduces to stock at f=1, like every other patch here
		}

		const uintptr_t base = reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
		const uintptr_t delta = base - kImageBase;

		// VERIFY ALL TEN BEFORE WRITING ANY. A partial write would shear the
		// isometric basis into a skewed parallelogram - far worse than the
		// defect. All or nothing (law 43, the coupled set), and L2 is part of
		// that set: it is the same projection at 1/1024 and it positions the
		// overlay icons ON the thumbnails L1 places.
		for (int i = 0; i < kRegionIsoCount; i++)
		{
			const uint32_t* p =
				reinterpret_cast<const uint32_t*>(kRegionIsoSites[i] + delta);
			uint32_t cur = 0;
			memcpy(&cur, p, 4);
			if (cur != kRegionIsoStock[i])
			{
				Logger::Get().WriteLine(
					LogLevel::Info,
					"CodePatches: region iso basis site %d (0x%08X) reads 0x%08X,"
					" expected 0x%08X - NOTHING written, region map stays stock.",
					i, static_cast<uint32_t>(kRegionIsoSites[i]), cur, kRegionIsoStock[i]);
				return 0;
			}
		}
		for (int i = 0; i < kRegionIso2Count; i++)
		{
			const uint32_t* p =
				reinterpret_cast<const uint32_t*>(kRegionIso2Sites[i] + delta);
			uint32_t cur = 0;
			memcpy(&cur, p, 4);
			if (cur != kRegionIso2Stock[i])
			{
				Logger::Get().WriteLine(
					LogLevel::Info,
					"CodePatches: region iso-2 (overlay) site %d (0x%08X) reads"
					" 0x%08X, expected 0x%08X - NOTHING written, region map stays"
					" stock.",
					i, static_cast<uint32_t>(kRegionIso2Sites[i]), cur,
					kRegionIso2Stock[i]);
				return 0;
			}
		}

		for (int i = 0; i < kRegionIsoCount; i++)
		{
			if (!WriteScaledFloat(kRegionIsoSites[i], kRegionIsoStock[i], factor, delta))
			{
				Logger::Get().WriteLine(
					LogLevel::Info,
					"CodePatches: VirtualProtect failed at 0x%08X - region iso basis"
					" is now PARTIAL (%d of 4). Expect a skewed region.",
					static_cast<uint32_t>(kRegionIsoSites[i]), gRegionIsoSitesApplied);
				return gRegionIsoSitesApplied;
			}
			gRegionIsoSitesApplied++;
		}
		int iso2Written = 0;
		for (int i = 0; i < kRegionIso2Count; i++)
		{
			if (!WriteScaledFloat(kRegionIso2Sites[i], kRegionIso2Stock[i], factor, delta))
			{
				Logger::Get().WriteLine(
					LogLevel::Info,
					"CodePatches: VirtualProtect failed at 0x%08X - overlay basis is"
					" now PARTIAL (%d of 6). Airport/seaport icons may sit off their"
					" tiles in the non-default view modes.",
					static_cast<uint32_t>(kRegionIso2Sites[i]), iso2Written);
				break;
			}
			iso2Written++;
		}
		gRegionIsoLiveFactor = factor;

		Logger::Get().WriteLine(
			LogLevel::Info,
			"CodePatches: REGIONISO x%.2f - basis 90.51/18.75/-37.49/45.25 ->"
			" %.2f/%.2f/%.2f/%.2f (%d of 4 sites, plus %d of 6 overlay sites)."
			" One region cell was 128.0 px wide at EVERY resolution; now %.1f px.",
			factor, 90.51f * factor, 18.75f * factor, -37.49f * factor,
			45.25f * factor, gRegionIsoSitesApplied, iso2Written, 128.0f * factor);
		return gRegionIsoSitesApplied;
	}

	int RegionIsoPatchedSites()
	{
		return gRegionIsoSitesApplied;
	}

	int ApplyRegionCameraScale(float factor)
	{
		gRegionCamScaleApplied = 0.0f;

		// ⛔ DISARMED 2026-08-04, v2.78.4. MEASURED DEAD, do not re-arm.
		// The patch WORKED as a patch - the camera held our 0.7500, its
		// [cam+0x134] held the correctly recomputed 3.4842, and its device
		// ortho frustum held OUR halfW 6689.6 (stock 20068.8), all held
		// steady across 20 samples / 5s while the region was on screen
		// (v2.78.3 REGIONWATCH STEADY) - AND THE SCREEN NEVER CHANGED.
		// The region slab is not drawn through that camera at all; it is
		// laid out from the .data isometric basis that ApplyRegionIsoScale
		// now patches. Kept as a tombstone so the four builds it cost are
		// not spent again. See _tests\REGRESSION.md "#131 ... CAMERA LEVER
		// IS MEASURED DEAD".
		return 0;

#if 0
		// Identity tier: leave the stock camera exactly alone. "Reduces to
		// stock at f=1" applies to this patch like every other.
		if (factor <= 1.001f)
		{
			return 0;
		}

		float want = 0.25f * factor;
		if (want < kRegionCamScaleMin) { want = kRegionCamScaleMin; }
		if (want > kRegionCamScaleMax) { want = kRegionCamScaleMax; }

		const uintptr_t base = reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
		const uintptr_t delta = base - kImageBase;
		uint8_t* p = reinterpret_cast<uint8_t*>(kRegionCamScaleSite + delta);

		// HALF ONE of the identification: `push imm32` carrying exactly 0.25f.
		uint32_t cur = 0;
		memcpy(&cur, p + 1, 4);
		if (p[0] != kPushImm32 || cur != kRegionCamScaleStock)
		{
			Logger::Get().WriteLine(
				LogLevel::Info,
				"CodePatches: region camera site 0x%08X bytes %02X imm 0x%08X unexpected"
				" - skipped (region map stays stock).",
				static_cast<uint32_t>(kRegionCamScaleSite), p[0], cur);
			return 0;
		}

		// HALF TWO: the call that CONSUMES that push must resolve to
		// cSC4CameraControl::SetScale. A bare `push 0.25f` is not rare; this
		// pair is unique. Without this check we could scale some unrelated
		// constant and never know (law 3 - never act on one signal alone).
		if (p[5] != kCallRel32)
		{
			Logger::Get().WriteLine(
				LogLevel::Info,
				"CodePatches: region camera site 0x%08X not followed by a call (%02X)"
				" - skipped.",
				static_cast<uint32_t>(kRegionCamScaleSite), p[5]);
			return 0;
		}
		int32_t rel = 0;
		memcpy(&rel, p + 6, 4);
		const uintptr_t targetVa =
			reinterpret_cast<uintptr_t>(p + 10) + static_cast<uintptr_t>(rel) - delta;
		if (targetVa != kRegionCamSetScale)
		{
			Logger::Get().WriteLine(
				LogLevel::Info,
				"CodePatches: region camera site 0x%08X calls 0x%08X, expected SetScale"
				" 0x%08X - skipped.",
				static_cast<uint32_t>(kRegionCamScaleSite),
				static_cast<uint32_t>(targetVa),
				static_cast<uint32_t>(kRegionCamSetScale));
			return 0;
		}

		DWORD oldProtect = 0;
		if (!VirtualProtect(p, 5, PAGE_EXECUTE_READWRITE, &oldProtect))
		{
			Logger::Get().WriteLine(
				LogLevel::Info,
				"CodePatches: VirtualProtect failed at 0x%08X - region camera skipped.",
				static_cast<uint32_t>(kRegionCamScaleSite));
			return 0;
		}
		uint32_t bits = 0;
		memcpy(&bits, &want, 4);
		memcpy(p + 1, &bits, 4);
		VirtualProtect(p, 5, oldProtect, &oldProtect);
		FlushInstructionCache(GetCurrentProcess(), p, 5);

		gRegionCamScaleApplied = want;

		// Report the EFFECT, not just the constant: px-per-region-cell is the
		// number a human can check against the screen. Stock is 98 px at every
		// resolution, which is the whole defect in one figure.
		const float stockPx =
			kRegionWorldUnitsPerCell * kRegionCamZ * 0.25f / kRegionCamR;
		const float wantPx =
			kRegionWorldUnitsPerCell * kRegionCamZ * want / kRegionCamR;
		Logger::Get().WriteLine(
			LogLevel::Info,
			"CodePatches: REGIONCAM scale 0.2500 -> %.4f at 0x%08X"
			" (region cell %.0f px -> %.0f px, factor %.2f).",
			want, static_cast<uint32_t>(kRegionCamScaleSite), stockPx, wantPx, factor);
		return 1;
#endif
	}

	float RegionCameraScaleApplied()
	{
		return gRegionCamScaleApplied;
	}

	namespace
	{
		// Scale one 7-dword .rdata size table in place. Verify-before-write
		// against the exact stock values; any mismatch (different exe build,
		// or another mod already patched it) leaves the table alone.
		void ScaleSizeTable(
			const char* name, uintptr_t siteVa, const uint32_t (&stock)[7], float factor)
		{
			const uintptr_t base = reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
			uint32_t* p = reinterpret_cast<uint32_t*>(siteVa + (base - kImageBase));

			for (int i = 0; i < 7; i++)
			{
				if (p[i] != stock[i])
				{
					Logger::Get().WriteLine(
						LogLevel::Info,
						"CodePatches: %s table entry %d is %u (expected %u) - table skipped.",
						name, i, p[i], stock[i]);
					return;
				}
			}

			DWORD oldProtect = 0;
			if (!VirtualProtect(p, 7 * sizeof(uint32_t), PAGE_READWRITE, &oldProtect))
			{
				Logger::Get().WriteLine(
					LogLevel::Info,
					"CodePatches: VirtualProtect failed for %s table - skipped.", name);
				return;
			}
			for (int i = 0; i < 7; i++)
			{
				p[i] = static_cast<uint32_t>(std::lround(stock[i] * factor));
			}
			VirtualProtect(p, 7 * sizeof(uint32_t), oldProtect, &oldProtect);

			Logger::Get().WriteLine(
				LogLevel::Info,
				"CodePatches: %s table x%.2f -> {%u,%u,%u,%u,%u,%u,%u} at 0x%08X.",
				name, factor, p[0], p[1], p[2], p[3], p[4], p[5], p[6],
				static_cast<uint32_t>(siteVa));
		}
	}

	namespace
	{
		// One verified in-place write. Returns false (with a log line) on any
		// byte mismatch - wrong exe build or another mod got there first.
		bool VerifiedWrite(
			const char* what, uintptr_t site, uintptr_t delta,
			const uint8_t* expect, const uint8_t* repl, size_t n)
		{
			uint8_t* p = reinterpret_cast<uint8_t*>(site + delta);
			if (memcmp(p, expect, n) != 0)
			{
				Logger::Get().WriteLine(
					LogLevel::Info,
					"CodePatches: %s site 0x%08X bytes unexpected - skipped.",
					what, static_cast<uint32_t>(site));
				return false;
			}
			DWORD oldProtect = 0;
			if (!VirtualProtect(p, n, PAGE_EXECUTE_READWRITE, &oldProtect))
			{
				Logger::Get().WriteLine(
					LogLevel::Info,
					"CodePatches: VirtualProtect failed at 0x%08X - skipped.",
					static_cast<uint32_t>(site));
				return false;
			}
			memcpy(p, repl, n);
			VirtualProtect(p, n, oldProtect, &oldProtect);
			FlushInstructionCache(GetCurrentProcess(), p, n);
			return true;
		}
	}

	void ApplyBudgetButtonScale(float factor)
	{
		const uint32_t w = static_cast<uint32_t>(std::lround(kStockBudgetBtnW * factor));
		const uint32_t h = static_cast<uint32_t>(std::lround(kStockBudgetBtnH * factor));
		const uint32_t xi = static_cast<uint32_t>(std::lround(kStockBudgetBtnXInset * factor));
		const uint32_t yi = static_cast<uint32_t>(std::lround(kStockBudgetBtnYInset * factor));
		if (w == kStockBudgetBtnW)
		{
			return; // identity factor: nothing to do
		}
		// h and yi land in push/sub imm8 slots; the geometry is only coherent
		// as a set, so any out-of-range member skips the whole patch.
		if (h > 127 || yi > 127)
		{
			Logger::Get().WriteLine(
				LogLevel::Info,
				"CodePatches: budget button h=%u yi=%u exceed imm8 - patch skipped.",
				h, yi);
			return;
		}

		const uintptr_t base = reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
		const uintptr_t delta = base - kImageBase;
		int nSize = 0, nX = 0, nY = 0;

		for (uintptr_t site : kBudgetBtnSizeSites)
		{
			// push imm8 h; push imm32 w
			const uint8_t expect[7] = { 0x6A, 0x1E, 0x68, 0xB4, 0x00, 0x00, 0x00 };
			uint8_t repl[7] = { 0x6A, static_cast<uint8_t>(h), 0x68, 0, 0, 0, 0 };
			memcpy(repl + 3, &w, 4);
			if (VerifiedWrite("budget btn size", site, delta, expect, repl, 7)) nSize++;
		}
		for (uintptr_t site : kBudgetBtnXSites)
		{
			const uint8_t expect[6] = { 0x81, 0xE9, 0xC3, 0x00, 0x00, 0x00 };
			uint8_t repl[6] = { 0x81, 0xE9, 0, 0, 0, 0 };
			memcpy(repl + 2, &xi, 4);
			if (VerifiedWrite("budget btn x-anchor", site, delta, expect, repl, 6)) nX++;
		}
		for (uintptr_t site : kBudgetBtnYSites)
		{
			// sub r32, imm8 - the modrm register varies per site (ecx/edx/eax),
			// so verify opcode + /5 reg-form + stock imm8, keep the modrm.
			uint8_t* p = reinterpret_cast<uint8_t*>(site + delta);
			const uint8_t modrm = p[1];
			if (p[0] != 0x83 || (modrm & 0xF8) != 0xE8 || p[2] != kStockBudgetBtnYInset)
			{
				Logger::Get().WriteLine(
					LogLevel::Info,
					"CodePatches: budget btn y-anchor 0x%08X bytes %02X %02X %02X unexpected - skipped.",
					static_cast<uint32_t>(site), p[0], p[1], p[2]);
				continue;
			}
			const uint8_t expect[3] = { 0x83, modrm, 0x28 };
			const uint8_t repl[3] = { 0x83, modrm, static_cast<uint8_t>(yi) };
			if (VerifiedWrite("budget btn y-anchor", site, delta, expect, repl, 3)) nY++;
		}

		Logger::Get().WriteLine(
			LogLevel::Info,
			"CodePatches: budget buttons %ux%u anchors W-%u/H-%u (%d size + %d x + %d y sites).",
			w, h, xi, yi, nSize, nX, nY);
	}

	// ONE loop body, TWO arrays (v2.74.0). Splitting the name-x pair out of
	// kOrdinanceInsetSites would otherwise have duplicated the clamp path, and a
	// duplicated clamp is how the two halves of a coupled set drift apart.
	int ApplyInsetSiteArray(const char* what, const InsetSite* sites,
		size_t count, float factor, uintptr_t delta)
	{
		int n = 0;
		for (size_t i = 0; i < count; ++i)
		{
			const InsetSite& s = sites[i];
			long v = std::lround(s.stock * factor);
			if (v == s.stock)
			{
				continue; // identity factor: nothing to do
			}
			if (v < 1)
			{
				continue;
			}
			if (v > 127)
			{
				// push imm8 ceiling: clamp rather than skip - a slightly
				// tighter indent beats the icon-on-text overlap. This is the
				// f < 2.5 path ONLY: the name column's ideal 136 at f=2 becomes
				// 127 and still clears the measured eye by 23px, which is the
				// USER-CONFIRMED 2x state. At f >= 2.5 the name-x sites are in
				// no array this helper is handed - ApplyOrdinanceNameColumnScale
				// owns them, because 204 clamped to 127 lands the label 29px
				// INSIDE the eye.
				Logger::Get().WriteLine(
					LogLevel::Info,
					"CodePatches: ordinance inset %ld clamped to 127 at 0x%08X.",
					v, static_cast<uint32_t>(s.site));
				v = 127;
			}
			// push imm8 with the stock inset, pinned by the next opcode byte.
			const uint8_t expect[3] = { 0x6A, s.stock, s.ctx };
			const uint8_t repl[3] = { 0x6A, static_cast<uint8_t>(v), s.ctx };
			if (VerifiedWrite(what, s.site, delta, expect, repl, 3)) n++;
		}
		return n;
	}

	void ApplyOrdinanceInsetScale(float factor)
	{
		const uintptr_t base = reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
		const uintptr_t delta = base - kImageBase;
		const size_t cInset = sizeof(kOrdinanceInsetSites) / sizeof(kOrdinanceInsetSites[0]);
		const size_t cName = sizeof(kOrdinanceNameXImm8Sites) / sizeof(kOrdinanceNameXImm8Sites[0]);

		const int n = ApplyInsetSiteArray("ordinance inset",
			kOrdinanceInsetSites, cInset, factor, delta);

		// The name-x pair takes the imm8 clamp ONLY below the block gate. At
		// f = 2.00 that reproduces v2.73.3 byte for byte (136 -> clamp 127),
		// which is the state 2x is USER-CONFIRMED in.
		int nx = 0;
		if (!OrdinanceNameXUsesBlock(factor))
		{
			nx = ApplyInsetSiteArray("ordinance name-x imm8",
				kOrdinanceNameXImm8Sites, cName, factor, delta);
		}

		if (n || nx || OrdinanceNameXUsesBlock(factor))
		{
			// HONEST HEALTH LINE (v2.74.0): the two families are counted
			// SEPARATELY, and the denominators are their own array sizes. The
			// old "(n of 8)" merged them, so a real decline in one could be
			// masked by the other.
			Logger::Get().WriteLine(
				LogLevel::Info,
				"CodePatches: ordinance row insets x%.2f (%d of %d insets, "
				"%d of %d name-x imm8). At or above x2.50 the name-x pair is "
				"ApplyOrdinanceNameColumnScale's and reports its own line.",
				factor, n, static_cast<int>(cInset), nx, static_cast<int>(cName));
		}
	}

	int ApplyOrdinanceNameColumnScale(float factor)
	{
		// Idempotent: a second call must not log "does not match the shipped
		// exe" about bytes WE wrote.
		if (gOrdinanceNameXBlocks > 0) { return gOrdinanceNameXBlocks; }

		// THE GATE (law 53). 2x is USER-CONFIRMED at the imm8 clamp of 127 and
		// must not move; only f >= 2.5 re-encodes. At f = 1.00 / 1.50 / 2.00
		// this returns before its first write and all 86 bytes stay stock.
		if (!OrdinanceNameXUsesBlock(factor)) { return 0; }

		const long x = std::lround(kOrdinanceNameXStockX * factor);
		if (x <= 127 || x > 4096)
		{
			// Unreachable behind the gate (170 at 2.5, 204 at 3.0). A value that
			// still FITS imm8 would mean the gate and the arithmetic disagree,
			// and that is a source bug, not a bad exe - so say so and decline
			// rather than write a 43-byte block to move a label 1px.
			Logger::Get().WriteLine(
				LogLevel::Info,
				"CodePatches: ordinance name-x %ld at x%.2f is not a value this "
				"block re-encode should ship - declined, imm8 path stands.",
				x, factor);
			return 0;
		}
		const uint32_t imm = static_cast<uint32_t>(x);

		const uintptr_t base = reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
		const uintptr_t delta = base - kImageBase;

		// ---- PASS 1: verify BOTH windows before writing EITHER. ------------
		// The income and expense name columns are ONE visual column. A
		// half-applied pair would leave the two sections 77px apart, which
		// reads as a layout bug rather than as a declined patch - so any
		// mismatch declines the WHOLE set (the ApplyGraphLegendBudgetScale
		// rule, and the v2.54.3 failure that produced it).
		for (const OrdinanceNameXBlock& b : kOrdinanceNameXBlocks)
		{
			const uint8_t* stock = (b.kind == kOnxIncome) ? kOnxStockIncome : kOnxStockExpense;
			const uint8_t* p = reinterpret_cast<const uint8_t*>(b.site + delta);
			if (memcmp(p, stock, static_cast<size_t>(b.len)) != 0)
			{
				Logger::Get().WriteLine(
					LogLevel::Info,
					"CodePatches: ordinance name-x block 0x%08X (%s) does not "
					"match the shipped exe - WHOLE SET declined (wrong build, "
					"another mod inside sub_77C660, or the per-site imm8 path "
					"reached it first).",
					static_cast<uint32_t>(b.site), b.name);
				return 0;
			}
		}

		// ---- PASS 2: write. Every window verified above; VerifiedWrite still
		// re-checks (cheap, and it is the only thing that can report a
		// VirtualProtect refusal).
		int n = 0;
		for (const OrdinanceNameXBlock& b : kOrdinanceNameXBlocks)
		{
			uint8_t repl[43] = {};
			int len = 0;
			if (b.kind == kOnxIncome)
			{
				const uint8_t t[] = {
					0x8B,0x56,0x10,                 // mov edx,[esi+0x10]  parent
					0x6A,0x66,                      // arg10 c3
					0x6A,0x55,                      // arg9  c2
					0x6A,0x44,                      // arg8  c1
					0x68,0x05,0xD3,0x85,0xEA,       // arg7  style GUID
					0x89,0x54,0x24,0x24,            // mov [esp+0x24],edx  spill
					0x8B,0x10,                      // mov edx,[eax]       vtable
					0x6A,0x00,                      // arg6  0
					0x91,                           // xchg eax,ecx        this
					0xFF,0x52,0x1C,                 // call [edx+0x1C]     name
					0x50,                           // arg5  string
					0xFF,0xB6,0x98,0x00,0x00,0x00,  // arg4  push [esi+0x98] y
					0x68,0x00,0x00,0x00,0x00,       // arg3  push imm32 x  <- +34
					0x55,                           // arg2  push ebp      id
					0xFF,0x74,0x24,0x38 };          // arg1  push [esp+0x38] parent
				len = static_cast<int>(sizeof(t)); memcpy(repl, t, sizeof(t));
			}
			else
			{
				const uint8_t t[] = {
					0x8B,0x4E,0x10,                 // mov ecx,[esi+0x10]  parent
					0x8B,0x10,                      // mov edx,[eax]       vtable
					0x6A,0x66, 0x6A,0x55, 0x6A,0x44,
					0x68,0x05,0xD3,0x85,0xEA,
					0x89,0x4C,0x24,0x24,            // mov [esp+0x24],ecx  spill
					0x6A,0x00,
					0x91,                           // xchg eax,ecx        this
					0xFF,0x52,0x1C,
					0x50,
					0xFF,0xB6,0x9C,0x00,0x00,0x00,  // arg4  push [esi+0x9C] y
					0x68,0x00,0x00,0x00,0x00,       // arg3  push imm32 x  <- +34
					0x55,
					0xFF,0x74,0x24,0x38 };
				len = static_cast<int>(sizeof(t)); memcpy(repl, t, sizeof(t));
			}
			memcpy(repl + b.immOff, &imm, 4);

			// The imm32 must land immediately after its own opcode. STRUCTURAL
			// self-check, not a defensive nicety: the first draft of the graph
			// legend's equivalent wrote an immediate one byte off, which would
			// have shifted the operand into the middle of an instruction and
			// produced a CRASH rather than a bad rect.
			{
				uint32_t back = 0;
				memcpy(&back, repl + b.immOff, 4);
				if (repl[b.immOff - 1] != 0x68 || back != imm)
				{
					Logger::Get().WriteLine(
						LogLevel::Info,
						"CodePatches: ordinance name-x block %s malformed "
						"(byte %02X at +%d is not push-imm32, imm %u != %u) - "
						"NOT written.",
						b.name, repl[b.immOff - 1], b.immOff - 1, back, imm);
					continue;
				}
			}
			if (len != b.len)
			{
				// Structural: a length drift would shift every instruction
				// boundary after the block. Never write it.
				Logger::Get().WriteLine(
					LogLevel::Info,
					"CodePatches: ordinance name-x block %s built %d bytes, "
					"stock is %d - NOT written (source bug, not a bad exe).",
					b.name, len, b.len);
				continue;
			}
			const uint8_t* stock = (b.kind == kOnxIncome) ? kOnxStockIncome : kOnxStockExpense;
			if (VerifiedWrite("ordinance name-x block", b.site, delta, stock, repl,
				static_cast<size_t>(b.len)))
			{
				n++;
			}
		}

		gOrdinanceNameXBlocks = n;
		Logger::Get().WriteLine(
			LogLevel::Info,
			"CodePatches: ordinance name column x%.2f -> x=%ld as imm32 "
			"(%d of %d blocks, 43 bytes each, arg list and net ESP unchanged). "
			"Below x2.50 this never runs and the imm8 clamp of 127 stands.",
			factor, x, n,
			static_cast<int>(sizeof(kOrdinanceNameXBlocks) / sizeof(kOrdinanceNameXBlocks[0])));
		return n;
	}

	void ApplySubFlyoutProviderScale(float factor)
	{
		const uintptr_t base = reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
		const uintptr_t delta = base - kImageBase;
		int n = 0;
		for (const Imm8Site& s : kSubFlyoutProviderSites)
		{
			long v = std::lround(s.stock * factor);
			if (v == s.stock) continue;
			if (v < 1 || v > 127)
			{
				Logger::Get().WriteLine(LogLevel::Info,
					"CodePatches: sub-flyout provider %ld at 0x%08X will not fit "
					"imm8 - skipped.", v, static_cast<uint32_t>(s.site));
				continue;
			}
			const uint8_t expect[2] = { 0x6A, s.stock };
			const uint8_t repl[2] = { 0x6A, static_cast<uint8_t>(v) };
			if (VerifiedWrite("sub-flyout provider", s.site, delta, expect, repl, 2)) n++;
		}
		if (n)
		{
			Logger::Get().WriteLine(LogLevel::Info,
				"CodePatches: sub-flyout provider metrics x%.2f (%d of %d sites) "
				"- strip born %g*n-%g.",
				factor, n, static_cast<int>(sizeof(kSubFlyoutProviderSites) / sizeof(kSubFlyoutProviderSites[0])),
				std::lround(44 * factor) + std::lround(5 * factor), (double)std::lround(5 * factor));
		}
	}

	// v2.37.0 task #78. Scale the four Data Views legend ORIGINS inside the
	// game's own re-lay sub_007A04F0, so the legend is laid down already
	// scaled on every view selection and no correction pass is needed.
	// Returns how many of the eight sites took (8 = fully born correct).
	int ApplyDataViewLegendScale(float factor)
	{
		gDataViewLegendPatched = 0;
		if (std::lround(factor * 100.0f) == 100)
		{
			return 0; // identity factor: the stock origins are already right
		}

		const uintptr_t base = reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
		const uintptr_t delta = base - kImageBase;
		int n = 0;

		// The two Y origins ride `lea r32,[... + disp8]`, so they are capped
		// at +127: 24 and 61 fit at 1.5x and 2x, but 61*3 = 183 does NOT, and
		// at that tier the chip column keeps the sweep pin instead (see the
		// dvBorn gate in UiSpike::ScalePanelsUnder). Skipping is LOUD.
		for (const LeaDisp8Site& s : kDataViewLegendLeaSites)
		{
			const long v = std::lround(static_cast<double>(s.stock) * factor);
			if (v == s.stock) { continue; }
			uint8_t* p = reinterpret_cast<uint8_t*>(s.site + delta);
			if (v > 127 || v < -128)
			{
				Logger::Get().WriteLine(
					LogLevel::Info,
					"CodePatches: data-view legend lea-disp8 %ld at 0x%08X exceeds "
					"the 1-byte field - skipped (that axis keeps the DVPIN pin).",
					v, static_cast<uint32_t>(s.site));
				continue;
			}
			if (p[0] != 0x8D || p[s.immOff] != static_cast<uint8_t>(s.stock))
			{
				Logger::Get().WriteLine(
					LogLevel::Info,
					"CodePatches: data-view legend lea-disp8 0x%08X bytes %02X ... %02X "
					"unexpected - skipped.",
					static_cast<uint32_t>(s.site), p[0], p[s.immOff]);
				continue;
			}
			const int len = s.immOff + 1;
			uint8_t expect[4] = {}, repl[4] = {};
			for (int i = 0; i < len; i++) { expect[i] = p[i]; repl[i] = p[i]; }
			repl[s.immOff] = static_cast<uint8_t>(static_cast<int8_t>(v));
			if (VerifiedWrite("data-view legend lea", s.site, delta, expect, repl, len)) { n++; }
		}

		// The two X origins are imm32 and fit at every tier.
		for (const RawImm32Site& s : kDataViewLegendImm32Sites)
		{
			const uint32_t v = static_cast<uint32_t>(std::lround(s.stock * factor));
			if (v == s.stock) { continue; }
			uint8_t* p = reinterpret_cast<uint8_t*>(s.site + delta);
			uint32_t cur = 0;
			memcpy(&cur, p + s.immOff, 4);
			const bool opOk = (p[0] == s.op0) && (s.op1 == 0 || p[1] == s.op1);
			if (!opOk || cur != s.stock)
			{
				Logger::Get().WriteLine(
					LogLevel::Info,
					"CodePatches: data-view legend imm32 0x%08X bytes %02X %02X imm %u "
					"unexpected - skipped.",
					static_cast<uint32_t>(s.site), p[0], p[1], cur);
				continue;
			}
			DWORD oldProtect = 0;
			const size_t nb = static_cast<size_t>(s.immOff) + 4;
			if (!VirtualProtect(p, nb, PAGE_EXECUTE_READWRITE, &oldProtect))
			{
				continue;
			}
			memcpy(p + s.immOff, &v, 4);
			VirtualProtect(p, nb, oldProtect, &oldProtect);
			FlushInstructionCache(GetCurrentProcess(), p, nb);
			n++;
		}

		gDataViewLegendPatched = n;
		Logger::Get().WriteLine(
			LogLevel::Info,
			"CodePatches: data-view legend x%.2f (%d of %d sites) - rows (%ld,%ld) "
			"chips (%ld,%ld), pitch left to the game.",
			factor, n, kDataViewLegendSiteCount,
			std::lround(278.0 * factor), std::lround(24.0 * factor),
			std::lround(371.0 * factor), std::lround(61.0 * factor));
		return n;
	}

	int DataViewLegendPatchedSites()
	{
		return gDataViewLegendPatched;
	}

	int ApplyGraphLegendBudgetScale(float factor)
	{
		gGraphLegendPatched = 0;

		// Identity guard. This runs BEFORE the tier-active isolation bail in
		// SC4UIScaleDllDirector, and the three block re-encodings are
		// STRUCTURAL - they must never go into a stock-tier process.
		if (std::lround(factor * 100.0f) == 100) { return 0; }

		const int strip = GraphLegendStripFor(factor);
		if (strip == 0)
		{
			Logger::Get().WriteLine(
				LogLevel::Info,
				"CodePatches: graph legend x%.2f has no CERTIFIED strip "
				"(oracle certifies 1.5/2/3 only) - declined, legend keeps the "
				"stock budget and UiSpike's LEGENDFIX fallback stays live.",
				factor);
			return 0;
		}

		const long r2 = std::lround(2.0 * factor);
		const long r4 = std::lround(4.0 * factor);
		const long r16 = std::lround(16.0 * factor);
		// The three winW-relative anchors, ALL derived from the one strip so
		// they cannot drift apart (law 43 - the column is a coupled set).
		const uint32_t cboxLMargin = static_cast<uint32_t>(strip);
		const uint32_t swMarginCbox = static_cast<uint32_t>(strip - r16 - r2);
		const uint32_t swMarginPlain = static_cast<uint32_t>(strip - r2);

		const uintptr_t base = reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
		const uintptr_t delta = base - kImageBase;

		// ---- PASS 1: verify EVERY site before writing ANY of them. --------
		// The legend is only coherent as a whole: a half-applied budget puts
		// the swatch back under the checkbox, which is exactly the v2.54.3
		// failure. So this declines the WHOLE set on any mismatch.
		for (const GraphLegendImmSite& s : kGraphLegendImmSites)
		{
			const uint8_t* p = reinterpret_cast<const uint8_t*>(s.site + delta);
			if (p[0] != s.b0 || p[1] != s.b1 || p[2] != s.stock)
			{
				Logger::Get().WriteLine(
					LogLevel::Info,
					"CodePatches: graph legend imm 0x%08X bytes %02X %02X %02X "
					"unexpected (%s) - WHOLE SET declined.",
					static_cast<uint32_t>(s.site), p[0], p[1], p[2], s.name);
				return 0;
			}
		}
		for (const GraphLegendBlock& b : kGraphLegendBlocks)
		{
			const uint8_t* stock =
				(b.kind == kGlbPlainSwatch) ? kGlStockB1 :
				(b.kind == kGlbCheckbox) ? kGlStockB2 : kGlStockB3;
			const uint8_t* p = reinterpret_cast<const uint8_t*>(b.site + delta);
			if (memcmp(p, stock, static_cast<size_t>(b.len)) != 0)
			{
				Logger::Get().WriteLine(
					LogLevel::Info,
					"CodePatches: graph legend block 0x%08X (%s) does not match "
					"the shipped exe - WHOLE SET declined (wrong build, or "
					"another mod patched sub_76D3D0 first).",
					static_cast<uint32_t>(b.site), b.name);
				return 0;
			}
		}

		// ---- PASS 2: write. Every site verified, so none of these can fail
		// on a byte mismatch; VerifiedWrite still re-checks (cheap, and it is
		// the only thing that can report a VirtualProtect refusal).
		int n = 0;
		for (const GraphLegendImmSite& s : kGraphLegendImmSites)
		{
			long v = 0;
			switch (s.kind)
			{
			case kGlDy:      v = std::lround(3.0 * factor); break;
			case kGlBottom:  v = std::lround(3.0 * factor)
								+ std::lround(6.0 * factor); break;
			case kGlSwatchW: v = std::lround(10.0 * factor); break;
			case kGlGap:     v = r4; break;
			case kGlTextR:   v = r4; break;
			}
			if (v < 0 || v > 127)
			{
				// Unreachable at 1.5/2/3 (max 27) - asserted by the offline
				// gate - but a silent truncation here would be a wrong rect.
				Logger::Get().WriteLine(
					LogLevel::Info,
					"CodePatches: graph legend imm %s -> %ld exceeds imm8 - "
					"set abandoned mid-write, %d sites live.", s.name, v, n);
				break;
			}
			const uint8_t expect[3] = { s.b0, s.b1, s.stock };
			const uint8_t repl[3] = { s.b0, s.b1, static_cast<uint8_t>(v) };
			if (VerifiedWrite("graph legend imm", s.site, delta, expect, repl, 3))
			{
				n++;
			}
		}

		for (const GraphLegendBlock& b : kGraphLegendBlocks)
		{
			uint8_t repl[42] = {};
			uint32_t imm = 0;
			int len = 0;
			if (b.kind == kGlbPlainSwatch)
			{
				imm = swMarginPlain;
				const uint8_t t[] = {
					0x8B,0x5C,0x24,0x50,             // mov ebx,[esp+0x50]
					0x2B,0x5C,0x24,0x48,             // sub ebx,[esp+0x48]  winW
					0x81,0xEB,0,0,0,0,               // sub ebx, imm32
					0x83,0x79,0x44,0x02,             // cmp [ecx+0x44],2
					0x0F,0x86,0x00,0x01,0x00,0x00,   // jbe 0x0076E200
					0x90 };
				len = sizeof(t); memcpy(repl, t, len);
				memcpy(repl + 10, &imm, 4);
			}
			else if (b.kind == kGlbCheckbox)
			{
				imm = cboxLMargin;
				const uint8_t t[] = {
					0x8B,0x54,0x24,0x50,             // mov edx,[esp+0x50]
					0x2B,0x54,0x24,0x48,             // sub edx,[esp+0x48]  winW
					0x81,0xEA,0,0,0,0,               // sub edx, imm32
					0x8B,0x4C,0x24,0x18,             // mov ecx,[esp+0x18]  rowY
					0x83,0xC1,0x10,                  // add ecx,0x10   bottom=y+16
					0x51,                            // push ecx
					0x8D,0x4A,0x10,                  // lea ecx,[edx+0x10] R=L+16
					0x51,                            // push ecx
					0xFF,0x74,0x24,0x20,             // push [esp+0x20]    top
					0x52,                            // push edx           left
					0x8B,0x10, 0x8B,0xC8,            // mov edx,[eax]; mov ecx,eax
					0xFF,0x92,0xDC,0x00,0x00,0x00 }; // call [edx+0xdc]
				len = sizeof(t); memcpy(repl, t, len);
				memcpy(repl + 10, &imm, 4);
			}
			else
			{
				imm = swMarginCbox;
				const uint8_t t[] = {
					0x8B,0x17, 0x8B,0xCF, 0xFF,0x52,0x0C, 0x50,
					0x8B,0x0E, 0x8B,0x11, 0xFF,0x52,0x38, // AddChildWindow
					0x8B,0x5C,0x24,0x50,             // mov ebx,[esp+0x50]
					0x2B,0x5C,0x24,0x48,             // sub ebx,[esp+0x48]  winW
					0x81,0xEB,0,0,0,0,               // sub ebx, imm32
					0x8D,0x8C,0x24,0xF8,0x00,0x00,0x00,
					0xE8,0xE1,0x49,0xE9,0xFF,        // call 0x00602BE0
					0x90 };
				len = sizeof(t); memcpy(repl, t, len);
				memcpy(repl + 25, &imm, 4);
			}
			// The imm32 must land immediately after its own opcode. This is a
			// STRUCTURAL self-check, not a defensive nicety: the first draft of
			// this function wrote B3's immediate at offset 26 instead of 25,
			// which would have shifted the operand into the middle of the
			// instruction and produced a crash rather than a bad rect. Verify
			// the two bytes in front of every immediate really are the
			// sub-with-imm32 opcode we think we placed there.
			{
				const int immOff = (b.kind == kGlbCboxSwatch) ? 25 : 10;
				const uint8_t r0 = repl[immOff - 2];
				const uint8_t r1 = repl[immOff - 1];
				const bool wellFormed = (r0 == 0x81)
					&& (r1 == (b.kind == kGlbCheckbox ? 0xEA : 0xEB));
				uint32_t back = 0;
				memcpy(&back, repl + immOff, 4);
				if (!wellFormed || back != imm)
				{
					Logger::Get().WriteLine(
						LogLevel::Info,
						"CodePatches: graph legend block %s malformed (opcode "
						"%02X %02X, imm %u != %u) - NOT written.",
						b.name, r0, r1, back, imm);
					continue;
				}
			}
			if (len != b.len)
			{
				// Structural: a length drift would shift every instruction
				// boundary after the block. Never write it.
				Logger::Get().WriteLine(
					LogLevel::Info,
					"CodePatches: graph legend block %s built %d bytes, stock is "
					"%d - NOT written (this is a source bug, not a bad exe).",
					b.name, len, b.len);
				continue;
			}
			const uint8_t* stock =
				(b.kind == kGlbPlainSwatch) ? kGlStockB1 :
				(b.kind == kGlbCheckbox) ? kGlStockB2 : kGlStockB3;
			if (VerifiedWrite("graph legend block", b.site, delta, stock, repl,
				static_cast<size_t>(b.len)))
			{
				n++;
			}
		}

		gGraphLegendPatched = n;
		Logger::Get().WriteLine(
			LogLevel::Info,
			"CodePatches: graph legend budget x%.2f (%d of 8 sites) - strip %d, "
			"cboxL winW-%u, swatch winW-%u (cbox) / winW-%u (plain), "
			"gap %ld, textR %ld. Plot right stays EARLYCHART's.",
			factor, n, strip, cboxLMargin, swMarginCbox, swMarginPlain, r4, r4);

		// ---- ROW0_TOP: the OTHER half of EARLYCHART's coupled pair ---------
		// MEASURED on two independent instruments, not inferred:
		//  (a) STOCK 1x PIXELS (_tests\captures\graphs-stock-ref.png). The chart
		//      client top is y=338 (outerFill FFDAE0E5 = (218,224,229) starts
		//      there, matching CHARTDIAG); the plot fill FFEFF3F7 =
		//      (239,243,247) starts at y=359 with its border row at 358, so
		//      plot.top = 20. The row-0 swatch spans y=361..366 and this builder
		//      writes swatch.top = rowY + 3 (0x0076E233), so rowY = 20. Row 0's
		//      top is FLUSH with the plot's top border, exactly, at f=1.
		//  (b) LIVE 3x LOG (_tests\captures\SC4UIScale-2026-08-04-185426.log):
		//      "EARLYCHART store (45,20,1354,748) -> (135,60,1087,708) in
		//      1464x768" - we already write plot.top = 20*f = 60 - while
		//      "LEGENDCBOX id=0x04000000 rect=(1093,20,1141,68)" shows row 0
		//      still sitting at 20.
		// So EARLYCHART shipped one half of the pair scaled and left the other
		// at its 1x literal (law 43). The legend column floats 20*(f-1) px ABOVE
		// the plot it annotates: 0 at 1x, 20 at 2x, 40 at 3x.
		// NOT AN OVERFLOW FIX. The measured 3x column uses 20 + rows*46 of 768;
		// after this it uses 60 + rows*46 (474 of 768 for the 9-label chart,
		// the same 62% utilisation 2x ships today). Nothing can fall off.
		// GATED TO f >= 2.5 ON PURPOSE. The derivation 20*f reduces to the stock
		// 20 at f=1, NOT at f=2, so writing it at 2.00 would move a layout the
		// user has confirmed good (#57). At f=2.00 this branch is not entered
		// and 0x0076DE79 keeps its stock bytes, byte for byte.
		if (n == 8 && std::lround(factor * 100.0f) >= 250)
		{
			const long row0 = std::lround(20.0 * factor);
			if (row0 > 0 && row0 < 4096)
			{
				uint8_t repl[8];
				memcpy(repl, kGlStockRow0, sizeof(repl));
				const uint32_t v = static_cast<uint32_t>(row0);
				memcpy(repl + 4, &v, 4);
				if (VerifiedWrite("graph legend ROW0_TOP", kGlRow0Site, delta,
					kGlStockRow0, repl, sizeof(repl)))
				{
					Logger::Get().WriteLine(
						LogLevel::Info,
						"CodePatches: graph legend ROW0_TOP 20 -> %ld at "
						"0x%08X - row 0 is flush with EARLYCHART's plot top "
						"again (f>=2.5 only; 2x deliberately untouched).",
						row0, static_cast<uint32_t>(kGlRow0Site));
				}
			}
		}
		return n;
	}

	int GraphLegendPatchedSites()
	{
		return gGraphLegendPatched;
	}

	int GraphLegendPlotRightMargin(float factor)
	{
		// The coupled half of the pair. Returns 0 unless the FULL set of eight
		// took, so EARLYCHART cannot adopt the new plot margin against a legend
		// that is still at the stock budget (that pairing is the oracle's
		// H-EARLYCHART candidate, and it paints the plot border inside the
		// checkbox column). Either both halves move or neither does.
		if (gGraphLegendPatched != 8) { return 0; }
		const int strip = GraphLegendStripFor(factor);
		if (strip == 0) { return 0; }
		return strip + static_cast<int>(std::lround(2.0 * factor));
	}

	void ApplyBudgetFamilyScale(float factor)
	{
		const uintptr_t base = reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
		const uintptr_t delta = base - kImageBase;
		int n8 = 0, n32 = 0, nBox = 0;

		for (const Imm8Site& s : kDeptImm8Sites)
		{
			long v = std::lround(s.stock * factor);
			if (v == s.stock) continue;
			if (v < 1) continue;
			if (v > 127) v = 127; // push imm8 ceiling (slider width at f=2)
			uint8_t* p = reinterpret_cast<uint8_t*>(s.site + delta);
			const uint8_t expect[2] = { 0x6A, s.stock };
			const uint8_t repl[2] = { 0x6A, static_cast<uint8_t>(v) };
			(void)p;
			if (VerifiedWrite("dept imm8", s.site, delta, expect, repl, 2)) n8++;
		}
		for (const Imm32Site& s : kDeptImm32Sites)
		{
			const uint32_t v = static_cast<uint32_t>(std::lround(s.stock * factor));
			if (v == s.stock) continue;
			uint8_t expect[5] = { 0x68, 0, 0, 0, 0 };
			memcpy(expect + 1, &s.stock, 4);
			uint8_t repl[5] = { 0x68, 0, 0, 0, 0 };
			memcpy(repl + 1, &v, 4);
			if (VerifiedWrite("dept imm32", s.site, delta, expect, repl, 5)) n32++;
		}
		int nSub = 0;
		for (const SubImm8Site& s : kBudgetSubImm8Sites)
		{
			long v = std::lround(s.stock * factor);
			if (v == s.stock) continue;
			if (v < 1) continue;
			if (v > 127) v = 127; // sub imm8 ceiling (f > ~3.3 for 0x26)
			uint8_t* p = reinterpret_cast<uint8_t*>(s.site + delta);
			const uint8_t modrm = p[1];
			if (p[0] != 0x83 || (modrm & 0xF8) != 0xE8 || p[2] != s.stock)
			{
				Logger::Get().WriteLine(
					LogLevel::Info,
					"CodePatches: budget sub-imm8 0x%08X bytes %02X %02X %02X unexpected - skipped.",
					static_cast<uint32_t>(s.site), p[0], p[1], p[2]);
				continue;
			}
			const uint8_t expect[3] = { 0x83, modrm, s.stock };
			const uint8_t repl[3] = { 0x83, modrm, static_cast<uint8_t>(v) };
			if (VerifiedWrite("budget sub-imm8", s.site, delta, expect, repl, 3)) nSub++;
		}

		// v2.29.0: `lea r32,[r32+disp8]` sites. A constant reaching a create
		// through a lea is the encoding that hid the master-budget notches
		// for two builds (law 15), so the census enumerates them explicitly.
		// The displacement is SIGNED (the popup close-X is -31), and the
		// instruction length varies with the addressing form, so the modrm/
		// sib bytes are read from memory and pinned as context exactly like
		// the sub-imm8 loop above.
		int nLea = 0;
		int nBoxCave = 0;   // #189: sites taking the widened imm32 cave path
		for (const LeaDisp8Site& s : kBudgetLeaDisp8Sites)
		{
			const long v = std::lround(static_cast<double>(s.stock) * factor);
			if (v == s.stock) continue;
			uint8_t* p = reinterpret_cast<uint8_t*>(s.site + delta);
			if (v > 127 || v < -128)
			{
				Logger::Get().WriteLine(
					LogLevel::Info,
					"CodePatches: budget lea-disp8 %ld at 0x%08X exceeds the "
					"1-byte field - skipped (needs a pin at this tier).",
					v, static_cast<uint32_t>(s.site));
				continue;
			}
			if (p[0] != 0x8D ||
				p[s.immOff] != static_cast<uint8_t>(s.stock))
			{
				Logger::Get().WriteLine(
					LogLevel::Info,
					"CodePatches: budget lea-disp8 0x%08X bytes %02X ... %02X "
					"unexpected - skipped.",
					static_cast<uint32_t>(s.site), p[0], p[s.immOff]);
				continue;
			}
			const int len = s.immOff + 1;
			uint8_t expect[4] = {}, repl[4] = {};
			for (int i = 0; i < len; i++) { expect[i] = p[i]; repl[i] = p[i]; }
			repl[s.immOff] = static_cast<uint8_t>(static_cast<int8_t>(v));
			if (VerifiedWrite("budget lea-disp8", s.site, delta, expect, repl, len)) nLea++;
		}

		// ================= #189 THE BUDGET DEPARTMENT OPEN-JUMP ==============
		// USER, all evening: a department popup "opens for a split second then
		// resizes to the correct size", at 1.5x AND 2x AND 3x, on EVERY open.
		//
		// IT WAS THIS LINE, and it was ours:
		//     if (bh > 127) bh = 127;   // push imm8 ceiling
		// A SILENT clamp. Width took the factor (300 -> 450) and height did
		// not (100 -> 150 wanted, 127 written), so we shipped a HALF-PATCHED
		// create size and the box was born 23px short at 1.5x. Our own log
		// line said so in plain sight the whole time - "bizbox 450x127" - and
		// BUDGETTICK finally measured the consequence on the live window:
		//     0x0423278F (0,0 0x0) -> (975,736 450x127)   [built at the clamp]
		//     0x0423278F ...450x127 -> ...450x150         [corrected after]
		// three opens, identical each time. 150 = 100 * 1.5 exactly, which is
		// what the height should have been at creation.
		//
		// WHY EVERY TIER, and why it got WORSE with the factor: the clamp is a
		// constant while the target is not. 1.5x wants 150 (23px jump), 2x
		// wants 200 (73px), 3x wants 300 (173px). "This was an issue at 2x and
		// 3x as well" is that arithmetic.
		//
		// THE CLAMP ALSO BROKE THIS FILE'S OWN RULE. ApplyCostBoxScale, ~40
		// lines up, hits the identical imm8 ceiling and REFUSES both sites
		// rather than half-patch, saying so in the log. This site clamped
		// silently instead. A patch that cannot express the value must refuse
		// or widen - never truncate quietly.
		//
		// THE CURE IS #159's, NOT A RUNTIME PIN. A pin IS the flash: it
		// corrects after creation by construction, which is the thing we are
		// removing. The 7-byte span `push imm8 h; push imm32 w` cannot hold
		// two imm32 pushes (10 needed), and #136-style in-place widening has
		// no room - so the span becomes a jmp into a cave that pushes both
		// full-width and returns, exactly like kCostOriginSite. The window is
		// then BORN at the right size and nothing has to correct it.
		const uint32_t bw = static_cast<uint32_t>(std::lround(kStockBizBoxW * factor));
		const long bh = std::lround(kStockBizBoxH * factor);
		if (bw != kStockBizBoxW)
		{
			int caveIdx = 0;
			for (uintptr_t site : kBizBoxSizeSites)
			{
				const uint8_t expect[7] = { 0x6A, 0x64, 0x68, 0x2C, 0x01, 0x00, 0x00 };
				if (bh <= 127)
				{
					// Fits the stock encoding - keep the cheap in-place write.
					// Unreachable at every shipped tier (100*1.5 already
					// exceeds it); kept so a hypothetical small factor takes
					// the simplest path rather than allocating a cave.
					uint8_t repl[7] = { 0x6A, static_cast<uint8_t>(bh), 0x68, 0, 0, 0, 0 };
					memcpy(repl + 3, &bw, 4);
					if (VerifiedWrite("bizbox size", site, delta, expect, repl, 7)) nBox++;
					caveIdx++;
					continue;
				}

				// --- cave path -------------------------------------------
				// Verify the stock bytes BEFORE allocating or writing
				// anything: a different exe build must be left exactly as
				// shipped, and an unverified site must not consume a cave.
				const uint8_t* pchk = reinterpret_cast<const uint8_t*>(site + delta);
				if (memcmp(pchk, expect, 7) != 0)
				{
					Logger::Get().WriteLine(LogLevel::Info,
						"CodePatches: bizbox size site 0x%08X unexpected "
						"(%02X %02X ...) - skipped, no cave allocated.",
						static_cast<uint32_t>(site), pchk[0], pchk[1]);
					caveIdx++;
					continue;
				}
				if (!gBizBoxCaves[caveIdx])
				{
					gBizBoxCaves[caveIdx] = VirtualAlloc(
						nullptr, 64, MEM_COMMIT | MEM_RESERVE,
						PAGE_EXECUTE_READWRITE);
				}
				if (!gBizBoxCaves[caveIdx])
				{
					Logger::Get().WriteLine(LogLevel::Error,
						"CodePatches: bizbox cave alloc FAILED for 0x%08X - "
						"site left STOCK (a 1x create is better than a "
						"half-patched one).",
						static_cast<uint32_t>(site));
					caveIdx++;
					continue;
				}
				uint8_t* cave = static_cast<uint8_t*>(gBizBoxCaves[caveIdx]);
				const uint32_t bh32 = static_cast<uint32_t>(bh);
				int n = 0;
				cave[n++] = 0x68;                         // push imm32 h
				memcpy(cave + n, &bh32, 4); n += 4;
				cave[n++] = 0x68;                         // push imm32 w
				memcpy(cave + n, &bw, 4); n += 4;
				cave[n] = 0xE9;                           // jmp back to site+7
				const uint32_t relBack = static_cast<uint32_t>(
					(site + 7 + delta)
					- (reinterpret_cast<uintptr_t>(cave) + n + 5));
				memcpy(cave + n + 1, &relBack, 4); n += 5;

				// 5-byte jmp + two NOPs so the span stays exactly 7 bytes and
				// any instruction that targets site+7 still lands correctly.
				uint8_t repl[7] = { 0xE9, 0, 0, 0, 0, 0x90, 0x90 };
				const uint32_t relTo = static_cast<uint32_t>(
					reinterpret_cast<uintptr_t>(cave) - (site + delta + 5));
				memcpy(repl + 1, &relTo, 4);
				if (VerifiedWrite("bizbox size (cave)", site, delta, expect, repl, 7))
				{
					nBox++;
					nBoxCave++;
				}
				caveIdx++;
			}
			// Close-X: keep the stock right/top insets, scaled.
			const uint32_t cx = bw - static_cast<uint32_t>(std::lround(31 * factor));
			{
				const uint8_t expect[5] = { 0x68, 0x0D, 0x01, 0x00, 0x00 };
				uint8_t repl[5] = { 0x68, 0, 0, 0, 0 };
				memcpy(repl + 1, &cx, 4);
				if (VerifiedWrite("bizbox closeX", kBizBoxCloseX, delta, expect, repl, 5)) nBox++;
			}
			{
				long cy = std::lround(11 * factor);
				if (cy > 127) cy = 127;
				const uint8_t expect[2] = { 0x6A, 0x0B };
				const uint8_t repl[2] = { 0x6A, static_cast<uint8_t>(cy) };
				if (VerifiedWrite("bizbox closeY", kBizBoxCloseY, delta, expect, repl, 2)) nBox++;
			}
		}

		int nRaw = 0;
		for (const RawImm32Site& s : kMasterNotchSites)
		{
			const uint32_t v = static_cast<uint32_t>(std::lround(s.stock * factor));
			if (v == s.stock) continue;
			uint8_t* p = reinterpret_cast<uint8_t*>(s.site + delta);
			uint32_t cur = 0;
			memcpy(&cur, p + s.immOff, 4);
			const bool opOk = (p[0] == s.op0) && (s.op1 == 0 || p[1] == s.op1);
			if (!opOk || cur != s.stock)
			{
				Logger::Get().WriteLine(
					LogLevel::Info,
					"CodePatches: master notch site 0x%08X bytes %02X %02X imm %u unexpected - skipped.",
					static_cast<uint32_t>(s.site), p[0], p[1], cur);
				continue;
			}
			DWORD oldProtect = 0;
			const size_t n = static_cast<size_t>(s.immOff) + 4;
			if (!VirtualProtect(p, n, PAGE_EXECUTE_READWRITE, &oldProtect))
			{
				continue;
			}
			memcpy(p + s.immOff, &v, 4);
			VirtualProtect(p, n, oldProtect, &oldProtect);
			FlushInstructionCache(GetCurrentProcess(), p, n);
			nRaw++;
		}

		Logger::Get().WriteLine(
			LogLevel::Info,
			"CodePatches: budget family x%.2f (%d imm8 + %d imm32 + %d sub-imm8 + %d lea-disp8 + %d notch sites), bizbox %ux%ld (%d sites, %d via the #189 imm32 cave - the height is no longer clamped to 127, so the department popup is BORN at its final size).",
			factor, n8, n32, nSub, nLea, nRaw, bw, bh, nBox, nBoxCave);
	}

	void ApplyHtmlSizeScale(float factor)
	{
		if (std::lround(factor * 100.0f) == 100)
		{
			return; // identity factor: nothing to do
		}

		ScaleSizeTable("HTML font-size", kHtmlFontSizeTable, kStockHtmlFontSizes, factor);
		ScaleSizeTable("HTML heading", kHtmlHeadingSizeTable, kStockHtmlHeadingSizes, factor);

		const uintptr_t base = reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
		const uintptr_t delta = base - kImageBase;

		for (const GuidRetarget& r : kPopupStyleRetargets)
		{
			uint8_t* p = reinterpret_cast<uint8_t*>(r.site + delta);
			uint32_t cur = 0;
			memcpy(&cur, p + 1, 4);
			if (p[0] != kPushImm32 || cur != r.from)
			{
				Logger::Get().WriteLine(
					LogLevel::Info,
					"CodePatches: popup style site 0x%08X bytes %02X imm 0x%08X unexpected - skipped.",
					static_cast<uint32_t>(r.site), p[0], cur);
				continue;
			}

			DWORD oldProtect = 0;
			if (!VirtualProtect(p, 5, PAGE_EXECUTE_READWRITE, &oldProtect))
			{
				Logger::Get().WriteLine(
					LogLevel::Info,
					"CodePatches: VirtualProtect failed at 0x%08X - skipped.",
					static_cast<uint32_t>(r.site));
				continue;
			}
			memcpy(p + 1, &r.to, 4);
			VirtualProtect(p, 5, oldProtect, &oldProtect);
			FlushInstructionCache(GetCurrentProcess(), p, 5);

			Logger::Get().WriteLine(
				LogLevel::Info,
				"CodePatches: popup style 0x%08X -> 0x%08X at 0x%08X.",
				r.from, r.to, static_cast<uint32_t>(r.site));
		}
	}

	int ApplyAdviceRowScale(float factor)
	{
		// Both glyph columns scale, AND the scrollbar half of the right-hand
		// reserve scales - see the constant block above.
		//
		// ⚠ THE X COLUMN IS SCALED ONLY AT factor <= 2.0, AND THIS CONDITION
		// IS MIRRORED IN build_selective_safe.py (the X ids are staged under
		// the same test). The two MUST agree: the budget has to describe the
		// art that actually shipped, or the X is clipped again. The reason is
		// the sign-extended imm8 - a scaled X needs S = 165 at 3x, which
		// cannot be encoded, while the stock-X form needs only 129.
		// Note both forms declare the SAME total (W - fixed - bar), so this
		// choice moves width BETWEEN the X and the headline; it cannot change
		// whether the row fits.
		// #136 (2026-08-05): THE TIER CEILING IS GONE. The comment above is kept
		// because it explains why the split existed, but it no longer applies:
		// the imm8 is not a law of nature, it is an ENCODING, and the encoding
		// is now widened when it has to be (see the two-form write below). So
		// the X column scales at EVERY tier and glyphX == glyph unconditionally.
		// ⚠ The mirrored `FACTOR <= 2.0` test in build_selective_safe.py was
		// removed in the SAME commit - that coupling is hard, and art without
		// the patch (or patch without the art) is exactly the task-#88 defect.
		// 3x SelectiveArt therefore goes 651 -> 655 entries, matching 1.5x/2x.
		const long glyph = std::lround(kAdviceGlyphStockPx * factor);
		const long bar = std::lround(kAdviceScrollbarStockPx * factor);
		const bool xScaled = true;
		const long glyphX = glyph;
		long s = glyph + glyphX + kAdviceRowFixedPx + bar;

		if (s == kAdviceRowMidStock)
		{
			return 0; // identity factor: the row is already stock-correct
		}
		if (s < 1)
		{
			return 0;
		}
		const uintptr_t base = reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
		const uintptr_t delta = base - kImageBase;

		if (s <= 127)
		{
			// NARROW FORM - unchanged, and deliberately still the path for
			// 1.5x (87) and 2x (113). Those two tiers are user-confirmed, so
			// they keep writing the exact 3 bytes they have always written;
			// gate_advice_rowx asserts "1.5x/2x untouched" for this reason.
			// `sub esi, 0x3d`, pinned by its own opcode+modrm so a different
			// exe build or another mod's detour cannot be silently overwritten.
			const uint8_t expect[3] = { 0x83, 0xEE, kAdviceRowMidStock };
			const uint8_t repl[3] = { 0x83, 0xEE, static_cast<uint8_t>(s) };
			if (!VerifiedWrite("advice row mid-column", kAdviceRowMidSite,
				delta, expect, repl, 3))
			{
				return 0;
			}
		}
		else
		{
			// WIDE FORM (#136) - only 3x reaches here (S = 165).
			//
			// `83 EE ib` sign-extends, so 128+ would flip SUB into ADD and
			// wreck every advice list. The old code clamped to 127 and shipped
			// a stock-size dismiss X at 3x. Clamping was never the only option:
			// re-encode the whole 19-byte window at 0x0079388B so the
			// subtraction becomes a 6-byte `lea esi, [eax - S]` with a full
			// imm32, and pay for the extra bytes out of neighbours proven dead.
			//
			// The 19 bytes, and where each byte goes (gate_advice_rowx.py):
			//   stock  8b f0            mov esi, eax        <- folded into lea
			//          6a 08            push 8
			//          83 ee 3d         sub esi, 0x3D       <- the imm8 ceiling
			//          89 5c 24 58      mov [esp+0x58], ebx <- LIVE, kept
			//          89 5c 24 5c      mov [esp+0x5C], ebx <- kept
			//          89 5c 24 60      mov [esp+0x60], ebx <- DEAD, dropped
			//   ours   6a 08            push 8              <- MUST stay first:
			//                                the stores' disp8s assume the push
			//          8d b0 imm32      lea esi, [eax - S]  <- folds mov+sub
			//          89 5c 24 58      mov [esp+0x58], ebx
			//          89 5c 24 5c      mov [esp+0x5C], ebx
			//          90 90 90         pad to exactly 19
			//
			// Same technique as ApplyOrdinanceNameColumnScale (0x0077CBFC /
			// 0x0077D0B9): same window discipline, net ESP unchanged, no branch
			// target inside the window. The dropped [esp+0x60] store is dead by
			// liveness, NOT by inspection - the gate walks the reads and fails
			// if any read of that slot exists, and one of its four positive
			// controls deliberately drops the LIVE [esp+0x58] instead to prove
			// the check can fail. `lea` sets no flags where `sub` did; the gate
			// also proves the flags are dead here.
			const uint8_t expect[19] = {
				0x8B, 0xF0, 0x6A, 0x08, 0x83, 0xEE, kAdviceRowMidStock,
				0x89, 0x5C, 0x24, 0x58, 0x89, 0x5C, 0x24, 0x5C,
				0x89, 0x5C, 0x24, 0x60
			};
			uint8_t repl[19] = {
				0x6A, 0x08,                     // push 8   (first - see above)
				0x8D, 0xB0, 0, 0, 0, 0,         // lea esi, [eax - S]
				0x89, 0x5C, 0x24, 0x58,
				0x89, 0x5C, 0x24, 0x5C,
				0x90, 0x90, 0x90
			};
			const int32_t neg = -static_cast<int32_t>(s);
			std::memcpy(&repl[4], &neg, sizeof(neg));

			if (!VerifiedWrite("advice row mid-column (wide)", kAdviceRowWinSite,
				delta, expect, repl, 19))
			{
				// Refused = the window is not what we expect (another mod, or
				// a different exe). Leave the row STOCK rather than clamp: a
				// clamped reserve was the old defect, and a stock row is at
				// least self-consistent with the stock art.
				Logger::Get().WriteLine(
					LogLevel::Info,
					"CodePatches: advice row wide re-encode REFUSED at 0x%08X "
					"- row left stock at x%.2f (S would have been %ld).",
					static_cast<uint32_t>(kAdviceRowWinSite), factor, s);
				return 0;
			}
			Logger::Get().WriteLine(
				LogLevel::Info,
				"CodePatches: advice row WIDE re-encode at 0x%08X - "
				"sub imm8 -> lea imm32, S=%ld (the imm8 ceiling no longer "
				"caps the dismiss X; 3x now scales it like 1.5x/2x).",
				static_cast<uint32_t>(kAdviceRowWinSite), s);
		}

		Logger::Get().WriteLine(
			LogLevel::Info,
			"CodePatches: advice row x%.2f - arrow %ldpx, X %ldpx (%s), "
			"scrollbar %ldpx, middle W-%u -> W-%ld.",
			factor, glyph, glyphX, xScaled ? "scaled" : "stock - tier ceiling",
			bar, static_cast<uint32_t>(kAdviceRowMidStock), s);
		return 1;
	}

	// ===== #121: MINIMAP TERRAIN BAKE x8 (zoom -3) =========================
	// WHY: at our 2x tier a 64-cell city tile drives the Data Views map's
	// surface to 512, i.e. zoom -3 (x8 upscale). MEASURED in game: the data
	// CELLS paint fine there, the terrain BASE does not, and the surface is
	// re-cleared every sim-day - so the cells end up alpha-blended onto black
	// and read as "wrong colours + a flash". No post-hoc pixel repair can fix
	// that (v2.69.5 / v2.69.6 / v2.70.0 each failed on it): the base must
	// exist BEFORE the game paints its cells.
	//
	// THE CAUSE, decoded from the shipped exe (every VA and byte below is
	// re-verified against SimCity 4.exe 1.1.641 by
	// _tests\Test-MiniMapX8Bake.py, and again at runtime before any write):
	//   0x7A852C  mov edx,[ebx+0x104]     ; zoom
	//   0x7A853D  lea ecx,[edx+4]         ; the dest math is FULLY GENERAL:
	//   0x7A8540  sar eax,cl              ;   destY = cellY*16 >> (zoom+4)
	//   0x7A855E  sar eax,cl              ;   tile side = 256 >> (zoom+4)
	//   0x7A8560  lea ecx,[edx+2]         ; <- index = zoom+2
	//   0x7A8563  cmp ecx,4               ; <- 5-entry table
	//   0x7A8566  ja  0x7A85B0            ; <- UNSIGNED: zoom -3 -> 0xFFFFFFFF
	//   0x7A8568  jmp [ecx*4+0x7A8628]    ;    -> SKIPS the tile, then clears
	//                                     ;    the dirty flags and reports done
	// Only the DISPATCH stops at -2. Its five blitters are x4 up, x2 up, 1:1,
	// /2, /4 - there is simply no x8 entry. That one unsigned compare is the
	// whole defect.
	//
	// THE FIX: re-point the dispatch at a 6-entry DLL table. Entries 1..5 are
	// the game's own stubs in their original relative order (so zoom -2..+2 is
	// bit-identical), entry 0 is ours (zoom -3) -> an x8 tile blitter. zoom
	// <= -4 and >= +3 keep the stock skip. The ONLY behavioural delta in the
	// entire reachable space is zoom -3: stock draws nothing, patched draws.
	// IN-MEMORY ONLY: the game's exe on disk is never written.
	//
	// BLAST RADIUS (enumerated by full-image scan; only the TABLE-VA item is
	// asserted by the gate - the other three were verified by hand and by an
	// independent audit scan, and remain UNASSERTED by any automated check): the
	// bake 0x7A7FF0 has exactly ONE caller (0x7A8721); the table 0x7A8628 is
	// referenced exactly ONCE (the jmp we replace); no branch target lands
	// inside the 15-byte window; the stubs and blitters are not modified.
	namespace
	{
		const uintptr_t kX8DispatchSite = 0x007A8560;
		const uint8_t kX8DispatchStock[15] = {
			0x8D,0x4A,0x02,                          // lea ecx,[edx+2]
			0x83,0xF9,0x04,                          // cmp ecx,4
			0x77,0x48,                               // ja  0x7A85B0
			0xFF,0x24,0x8D,0x28,0x86,0x7A,0x00 };    // jmp [ecx*4+0x7A8628]

		const uintptr_t kX8StubBlock = 0x007A856F;
		const uint8_t kX8StubStock[0x21] = {
			0xB9,0xD0,0x6B,0x7A,0x00, 0xEB,0x1A,     // /4   (zoom +2)
			0xB9,0xD0,0x6A,0x7A,0x00, 0xEB,0x13,     // /2   (zoom +1)
			0xB9,0x70,0x6A,0x7A,0x00, 0xEB,0x0C,     // 1:1  (zoom  0)
			0xB9,0x60,0x6E,0x7A,0x00, 0xEB,0x05,     // x2   (zoom -1)
			0xB9,0xE0,0x6E,0x7A,0x00 };              // x4   (zoom -2)
		const uintptr_t kX8TableVa = 0x007A8628;
		const uint32_t kX8TableStock[5] = {
			0x007A858B, 0x007A8584, 0x007A857D, 0x007A8576, 0x007A856F };
		const uintptr_t kX8TailVa = 0x007A8590;  // test ecx,ecx; pushes; call ecx

		void*         gX8BakeThis = nullptr;
		const void*   gX8Tail = nullptr;
		uint32_t      gX8DispatchTable[6] = { 0, 0, 0, 0, 0, 0 };
		volatile LONG gX8Blits = 0;   // EXECUTED counter (law 47)
		volatile LONG gX8Clips = 0;   // sizing-policy alarm (#109 family)
		int           gX8Applied = 0; // 0 = not tried, 1 = live, -1 = declined

		// Stock contract, measured at the tail 0x7A8594..0x7A85AA:
		//   cdecl(dst, dstPitchBytes, src16x16, srcPitchBytes=0x40, w, h)
		// with w == h == 256>>(zoom+4) == 128 at zoom -3.
		extern "C" void __cdecl X8TileBlit(
			uint32_t* dst, int dstPitchBytes,
			const uint32_t* src, int srcPitchBytes, int destW, int destH)
		{
			const int dstPitch = dstPitchBytes >> 2;
			const int srcPitch = srcPitchBytes >> 2;
			const int srcW = destW >> 3, srcH = destH >> 3;   // 16 x 16 cells
			// CLIP against the raster of the instance being baked. The bake's
			// addressing assumes blit == terrain << -zoom EXACTLY; an inexact
			// ratio (1.5x's 384, 3x's 768 - the #109 family) would otherwise
			// run off the heap block. This turns a sizing-policy leak into a
			// clipped draw plus a loud counter instead of corruption.
			int maxRows = destH, maxCols = destW;
			const uint8_t* mm = static_cast<const uint8_t*>(gX8BakeThis);
			if (mm)
			{
				uint32_t* rBase = *reinterpret_cast<uint32_t* const*>(mm + 0x114);
				const int rW = *reinterpret_cast<const int32_t*>(mm + 0x118);
				const int rH = *reinterpret_cast<const int32_t*>(mm + 0x11C);
				if (rBase && rW > 0 && rH > 0 && dst >= rBase && dstPitch == rW)
				{
					const ptrdiff_t off = dst - rBase;
					const int row0 = static_cast<int>(off / rW);
					const int col0 = static_cast<int>(off % rW);
					if (rH - row0 < maxRows || rW - col0 < maxCols)
					{
						maxRows = (rH - row0 < maxRows) ? rH - row0 : maxRows;
						maxCols = (rW - col0 < maxCols) ? rW - col0 : maxCols;
						if (maxRows < 0) { maxRows = 0; }
						if (maxCols < 0) { maxCols = 0; }
						InterlockedIncrement(&gX8Clips);
					}
				}
			}
			for (int sy = 0; sy < srcH; ++sy)
			{
				const uint32_t* srow = src + sy * srcPitch;
				for (int by = 0; by < 8; ++by)
				{
					const int dy = sy * 8 + by;
					if (dy >= maxRows) { break; }
					uint32_t* drow = dst + dy * dstPitch;
					for (int sx = 0; sx < srcW; ++sx)
					{
						const uint32_t c = srow[sx];
						const int dx0 = sx * 8;
						for (int bx = 0; bx < 8; ++bx)
						{
							if (dx0 + bx >= maxCols) { break; }
							drow[dx0 + bx] = c;
						}
					}
				}
			}
			InterlockedIncrement(&gX8Blits);
		}

		// Jump-table target for index 0 (zoom -3). Register contract at
		// 0x7A8568: ebx = minimap this, eax = destW/destH; the tail performs
		// every push. The five stock stubs only set ecx and fall through, so
		// everything else must be preserved; flags are dead (the tail starts
		// with test ecx,ecx) and mov does not touch them anyway.
		__declspec(naked) void X8DispatchStub()
		{
			__asm {
				mov dword ptr [gX8BakeThis], ebx
				mov ecx, offset X8TileBlit
				jmp dword ptr [gX8Tail]
			}
		}
	}

	void ApplyMiniMapX8Bake(float factor)
	{
		if (gX8Applied != 0) { return; }
		if (factor <= 1.01f)
		{
			// f = 1 reduction in its strongest form: the exe is never written.
			return;
		}
		const uintptr_t base =
			reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
		const uintptr_t delta = base - kImageBase;

		// PASS 1 - verify EVERYTHING before writing ANYTHING.
		if (memcmp(reinterpret_cast<void*>(kX8DispatchSite + delta),
				kX8DispatchStock, sizeof(kX8DispatchStock)) != 0
			|| memcmp(reinterpret_cast<void*>(kX8StubBlock + delta),
				kX8StubStock, sizeof(kX8StubStock)) != 0)
		{
			Logger::Get().WriteLine(LogLevel::Info,
				"CodePatches: x8 bake dispatch/stubs do not match the shipped "
				"exe - DECLINED (wrong build, or another mod patched the "
				"minimap bake first). Data Views keeps stock behaviour.");
			gX8Applied = -1;
			return;
		}
		const uint32_t* tbl = reinterpret_cast<const uint32_t*>(kX8TableVa + delta);
		for (int i = 0; i < 5; ++i)
		{
			if (tbl[i] != kX8TableStock[i] + static_cast<uint32_t>(delta))
			{
				Logger::Get().WriteLine(LogLevel::Info,
					"CodePatches: x8 bake table entry %d is 0x%08X (expected "
					"0x%08X) - DECLINED.", i, tbl[i],
					kX8TableStock[i] + static_cast<uint32_t>(delta));
				gX8Applied = -1;
				return;
			}
		}

		// PASS 2 - build our side first, then one verified write.
		gX8Tail = reinterpret_cast<const void*>(kX8TailVa + delta);
		gX8DispatchTable[0] = reinterpret_cast<uint32_t>(&X8DispatchStub);
		for (int i = 0; i < 5; ++i)
		{
			gX8DispatchTable[i + 1] =
				kX8TableStock[i] + static_cast<uint32_t>(delta);
		}

		uint8_t repl[15];
		memcpy(repl, kX8DispatchStock, sizeof(repl));
		repl[2] = 0x03;   // lea ecx,[edx+3]
		repl[5] = 0x05;   // cmp ecx,5
		const uint32_t tableAddr =
			reinterpret_cast<uint32_t>(&gX8DispatchTable[0]);
		memcpy(repl + 11, &tableAddr, 4);

		if (VerifiedWrite("x8 bake dispatch", kX8DispatchSite, delta,
				kX8DispatchStock, repl, sizeof(repl)))
		{
			gX8Applied = 1;
			Logger::Get().WriteLine(LogLevel::Info,
				"CodePatches: minimap bake extended to x8 (zoom -3) - dispatch "
				"0x%08X -> 6-entry table at 0x%08X (stub %p, blitter %p). The "
				"Data Views map can now bake at FULL SIZE on small tiles.",
				static_cast<uint32_t>(kX8DispatchSite), tableAddr,
				&X8DispatchStub, &X8TileBlit);
		}
		else
		{
			gX8Applied = -1;
		}
	}

	int MiniMapX8Blits() { return static_cast<int>(gX8Blits); }
	int MiniMapX8Clips() { return static_cast<int>(gX8Clips); }
	bool MiniMapX8Active() { return gX8Applied == 1; }

	// ============ #130 RATING DECLINE-ARROW ANCHOR =======================
	// Every offset below was read out of the shipped 1.1.641 image, and the
	// vtable slots were confirmed by disassembling the IMPLEMENTATIONS, never
	// by header order (the community cIGZWin header drifts by one slot above
	// +0xE0 - ShowWindow is really +0x114, Hide +0x118):
	//   this+0x0C  = the controller's EMBEDDED cIGZWin subobject. MEASURED:
	//                sub_7E8510 does `mov edx,[ebp+0xC]` (that is the VTABLE)
	//                and `lea edi,[ebp+0xC]; mov ecx,edi; call [edx+0x94]`,
	//                so this+0xC is the object, not a pointer to it. The
	//                builder agrees: `lea ebx,[esi+0xC]` at 0x7ECFA0.
	//   this+0x378 / +0x37C = the cached arrow anchor (L,T).
	//   vt+0x8C  GetChildWindowFromIDRecursive - PROVEN by composition:
	//            vt+0x94 (GetChildAsRecursive, the call the game itself makes)
	//            is literally `call [vt+0x8C]` then QueryInterface.
	//   vt+0xA4 GetW = [+0xB0]-[+0xA8]   vt+0xA8 GetH = [+0xB4]-[+0xAC]
	//   vt+0xAC GetL = [+0xA8]           vt+0xB0 GetT = [+0xAC]
	namespace
	{
		typedef void (__fastcall* RatingUpdateFn)(void*, void*);
		typedef void* (__thiscall* WinChildRecFn)(void*, uint32_t);
		typedef int32_t (__thiscall* WinGetIntFn)(void*);

		RatingUpdateFn gRatingUpdateOrig = nullptr;
		bool gAnchorWrite = false;
		int  gAnchorLogs = 0;
		int  gAnchorArms = 0;

		// sub_7E8510, the rating updater. It is __thiscall with NO stack args
		// (both call sites pass only ecx; the epilogue is a plain `ret`).
		const uintptr_t kRatingUpdateVa = 0x7E8510;
		const uintptr_t kDeclineStepVa = 0x7E8A02;   // imul ecx, ecx, step
		const uint32_t  kDeclineArrowId = 0xCA5A415E;
		// STOCK BYTES read from the shipped exe at 0x007E8510:
		//   83 EC 64 | 53 | 55   = sub esp,0x64 / push ebx / push ebp
		// 3+1+1 = exactly 5, so MinHook's 5-byte JMP lands on an instruction
		// boundary and never straddles one.
		const uint8_t kRatingUpdateStock[5] = { 0x83, 0xEC, 0x64, 0x53, 0x55 };

		void __fastcall RatingUpdateDetour(void* self, void* edx)
		{
			do
			{
				if (!self) { break; }
				uint8_t* ctl = static_cast<uint8_t*>(self);
				void* win = static_cast<void*>(ctl + 0x0C);
				void** wvt = *reinterpret_cast<void***>(win);
				if (!wvt) { break; }
				void* arrow = reinterpret_cast<WinChildRecFn>(
					wvt[0x8C / 4])(win, kDeclineArrowId);
				if (!arrow) { break; }
				void** avt = *reinterpret_cast<void***>(arrow);
				const int32_t liveL = reinterpret_cast<WinGetIntFn>(avt[0xAC / 4])(arrow);
				const int32_t liveT = reinterpret_cast<WinGetIntFn>(avt[0xB0 / 4])(arrow);
				const int32_t liveW = reinterpret_cast<WinGetIntFn>(avt[0xA4 / 4])(arrow);
				const int32_t liveH = reinterpret_cast<WinGetIntFn>(avt[0xA8 / 4])(arrow);
				int32_t* cachedL = reinterpret_cast<int32_t*>(ctl + 0x378);
				int32_t* cachedT = reinterpret_cast<int32_t*>(ctl + 0x37C);

				// THE ARMING TEST, and it carries no tier constant: the game
				// writes y = *cachedT at ALL THREE of its GZWinMoveTo sites
				// (0x7E883B, 0x7E8939, 0x7E8A0A), so it can never change T.
				// A T that differs was moved by OUR sweep and by nothing else.
				// Precondition (measured): the builder seeds [this+0x36C] with
				// the current rating at 0x7ED284 right before calling the
				// updater, so the panel's first update is a ZERO delta and
				// parks the arrow at exactly (cachedL, cachedT). Our sweep
				// therefore scales it from home, and the first armed call
				// reads a clean scaled home.
				const bool stale = (liveT != *cachedT);

				int step = -1;
				const uintptr_t d =
					reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr)) - kImageBase;
				const uint8_t* opc = reinterpret_cast<const uint8_t*>(kDeclineStepVa + d);
				if (opc[0] == kImulOpcode) { step = opc[2]; }

				if (stale || gAnchorLogs < 4)
				{
					++gAnchorLogs;
					Logger::Get().WriteLine(LogLevel::Info,
						"CodePatches: RATEANCHOR ctl=%p cached=(%d,%d) arrow "
						"L/T=(%d,%d) %dx%d step=%d stale=%d write=%d arms=%d.",
						self, *cachedL, *cachedT, liveL, liveT, liveW, liveH,
						step, stale ? 1 : 0, gAnchorWrite ? 1 : 0, gAnchorArms);
				}
				if (stale && gAnchorWrite && liveL > 0 && liveT > 0)
				{
					*cachedL = liveL;
					*cachedT = liveT;
					++gAnchorArms;
					// Self-latching: with the anchor rewritten, liveT now
					// equals *cachedT, so this never re-fires until the sweep
					// moves the window again (new city) - which is exactly
					// when re-anchoring is wanted. No epoch bookkeeping.
				}
			} while (false);

			if (gRatingUpdateOrig) { gRatingUpdateOrig(self, edx); }
		}
	}

	void InstallRatingArrowAnchor(float factor, int mode)
	{
		if (mode <= 0) { return; }
		// v2.77.0: 2x INCLUDED, by user direction after the 3x fix was confirmed
		// ("make sure you apply that fix to 2x as well"). The f>=2.5 gate was a
		// v2.74.0 precaution for an UNPROVEN model; the model is now proven on
		// screen at 3x, and the defect is tier-general by construction - the
		// arrow is re-seated from a cache the sweep has already invalidated, so
		// it lands at f x its own correct seat at ANY scaled tier.
		//
		// WHY THIS CANNOT DISTURB THE CONFIRMED 2x LAYOUT: the detour is
		// SELF-GATING ON THE ACTUAL DEFECT. It compares the arrow's LIVE L/T
		// against the cached seat and writes only when they differ (the `stale`
		// flag in the RATEANCHOR line). If 2x seats the arrow correctly, live
		// == cached, the write is skipped, and the frame is untouched. It also
		// computes no coordinates of its own - it writes back the game's own
		// cached value - so there is no arithmetic that could be wrong at 2x.
		// Still off entirely at f<=1.01 (stock) via the factor test below.
		const bool wantFix = (mode >= 2 && factor > 1.01f);
		const bool wantLog = (mode == 1);
		if (!wantFix && !wantLog)
		{
			// v2.77.0: this branch is now reached only at STOCK (f<=1.01) or
			// with the feature switched off (mode 0). The old comment here
			// claimed it was the f=2.00 proof; that stopped being true when
			// the gate widened to include 2x, and a stale comment describing
			// code that no longer behaves that way is the law-48 defect.
			// 2x safety now rests on the detour's OWN stale-check, documented
			// at the gate above, not on never installing.
			Logger::Get().WriteLine(LogLevel::Info,
				"CodePatches: RATEANCHOR declined at factor %.2f (mode %d) - "
				"nothing installed; this tier is byte-identical.",
				static_cast<double>(factor), mode);
			return;
		}

		const uintptr_t base = reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
		void* target = reinterpret_cast<void*>(base - kImageBase + kRatingUpdateVa);

		// Verify-before-write, same law as every byte patch in this file.
		if (memcmp(target, kRatingUpdateStock, sizeof(kRatingUpdateStock)) != 0)
		{
			Logger::Get().WriteLine(LogLevel::Info,
				"CodePatches: RATEANCHOR prologue mismatch at %p - skipped.", target);
			return;
		}

		const MH_STATUS init = MH_Initialize();
		if (init != MH_OK && init != MH_ERROR_ALREADY_INITIALIZED)
		{
			Logger::Get().WriteLine(LogLevel::Error,
				"CodePatches: RATEANCHOR MH_Initialize failed (%d).", init);
			return;
		}
		if (MH_CreateHook(target, reinterpret_cast<void*>(&RatingUpdateDetour),
				reinterpret_cast<void**>(&gRatingUpdateOrig)) != MH_OK
			|| MH_EnableHook(target) != MH_OK)
		{
			Logger::Get().WriteLine(LogLevel::Error,
				"CodePatches: RATEANCHOR failed to hook sub_7E8510 at %p.", target);
			return;
		}
		gAnchorWrite = wantFix;
		Logger::Get().WriteLine(LogLevel::Info,
			"CodePatches: RATEANCHOR installed on sub_7E8510 %p (factor %.2f, "
			"mode %d: %s).", target, static_cast<double>(factor), mode,
			wantFix ? "log + re-anchor" : "log only");
	}

	int RatingArrowAnchorArms() { return gAnchorArms; }

	// ============ #188 U-DRIVE-IT START-BUBBLE SCALE =====================
	// The start bubbles are the mission_selection_* SWARM EFFECTS, spawned
	// BY NAME by the mission manager (name table 0xB09AE0; the five sites:
	// 0x52C6C1/0x52C6B9 offer, 0x529DA8/0x529D9C shrink, 0x528BC9 red).
	// There is NO size constant in the exe for them, and a DBPF override of
	// the EFFDIR resource {EA5118B0,EA5118B1,1} carrying a 3x scale was
	// proven INERT from BOTH plugin trees (two control launches,
	// 2026-08-17) - the effects service binds the base archive's copy. So
	// the lever is the INSTANCE: CreateEffectByName (0x5939B0) returns a
	// 0x14C-byte effect instance whose 4th transform block (+0xE0 rot 3x3,
	// +0x104 trans, +0x110 scale; flag byte +0xDD) the record bind
	// (0x5BFF80) has just reset to identity with flags 0. The activation
	// math (0x5919D0) tests that flag byte (`mov dl,[ebp+0xDD]; test
	// dl,dl` at 0x591DFE/0x591E0A) and, when set, multiplies the instance
	// scale into EVERY child spawn (`fld [esp+0x58]; fmul [esi+0x48]` at
	// 0x591FDE/0x591FEA - the fmul operand is the child's own file scale).
	// We set scale + flag on mission_selection instances only, AFTER the
	// original returns; the game does all the math itself, at every zoom,
	// including the _shrink despawn animation (the name prefix covers all
	// 18 variants). The click side needs nothing: the offer control's hit
	// test is a renderer ray-pick against the DRAWN geometry (slot 65 on
	// cISC43DRender at 0x4B8A38, no radius constant), so a bigger visual
	// is a bigger click target by construction.
	namespace
	{
		typedef uint32_t (__fastcall* CreateEffectFn)(void*, void*,
			const char*, void**);
		CreateEffectFn gCreateEffectOrig = nullptr;
		float gBubbleScale = 0.0f;   // <= 1.01 = disarmed (log-only or off)

		// #188 BALLOONSPRITE tuning. Deliberately ini-driven and NOT compiled
		// in: once the field dump names the size field we re-aim by editing a
		// text file, not by rebuilding. The loop that burned 2026-08-17 was
		// one-launch-per-yes/no; these three knobs collapse it.
		int   gSpriteOffset = 0;     // byte offset into the sprite; 0 = OFF
		int   gSpriteKind = 0;       // 0 = float, 1 = int32, 2 = two int16
		float gSpriteScale = 0.0f;   // <= 1.01 = disarmed
		int   gBubbleHits = 0;
		int   gBubbleLogs = 0;
		bool  gBubbleStack = false;  // mode >= 3: log the caller stack
		int   gBubbleStackLogs = 0;
		int   gBubbleAllLogs = 0;    // mode >= 3: unfiltered spawn census
		int   gBubbleBandLogs = 0;   // offer-band (0x49xxxx-0x4Axxxx) spawns

		// TEN drawer identifications from static analysis never executed
		// (every hooked VA armed clean and fired zero). This instrument
		// uses NO analysis: when the PROVEN-LIVE click spawn fires, the
		// real resolution path is ON THE STACK. Scan up-stack for values
		// that (a) lie in .text and (b) directly follow a call encoding -
		// a conservative return-address walk without frame-pointer
		// assumptions. The logged VAs are EXECUTING code by construction.
		void LogBubbleCallStack(void* frameAnchor)
		{
			const uintptr_t base =
				reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
			const uintptr_t lo = base + 0x1000;
			const uintptr_t hi = base + 0xA20000;
			const uintptr_t* p =
				reinterpret_cast<const uintptr_t*>(frameAnchor);
			char line[420];
			int used = 0, found = 0;
			line[0] = 0;
			for (int k = 0; k < 1024 && found < 14; ++k)
			{
				const uintptr_t v = p[k];
				if (v < lo || v >= hi) { continue; }
				// return addresses immediately follow a call: E8 rel32,
				// FF /2 (reg/[disp8]/[disp32]), or 9A far (never used).
				const uint8_t* c = reinterpret_cast<const uint8_t*>(v);
				const bool isRet = (c[-5] == 0xE8)
					|| (c[-2] == 0xFF) || (c[-3] == 0xFF) || (c[-6] == 0xFF)
					|| (c[-7] == 0xFF);
				if (!isRet) { continue; }
				const uint32_t va =
					static_cast<uint32_t>(v - base + kImageBase);
				static const char kHex[] = "0123456789ABCDEF";
				line[used++] = ' ';
				for (int s = 28; s >= 0; s -= 4)
				{
					line[used++] = kHex[(va >> s) & 0xF];
				}
				line[used] = 0;
				++found;
				if (used > 380) { break; }
			}
			Logger::Get().WriteLine(LogLevel::Info,
				"CodePatches: BUBBLESTACK%s.", line);
		}

		// CreateEffectByName 0x5939B0: __thiscall, TWO stack args
		// (name, ppOut), result in eax. STOCK PROLOGUE read from the
		// shipped exe: 83 EC 10 | 57 | 8B F9 | 8B 4C 24 18
		//              sub esp,0x10 / push edi / mov edi,ecx / mov ecx,[esp+0x18]
		const uintptr_t kCreateEffectVa = 0x5939B0;
		const uint8_t kCreateEffectStock[10] =
			{ 0x83, 0xEC, 0x10, 0x57, 0x8B, 0xF9, 0x8B, 0x4C, 0x24, 0x18 };
		const size_t kInstFlagOff  = 0xDD;
		const size_t kInstScaleOff = 0x110;
		// ReadTransform's (0x5DA930) bit convention: bit1 = scale != 1,
		// bit2 = rotation present. The activation gate only tests nonzero;
		// the bits describe what the block holds (identity rot + our scale).
		const uint8_t kInstFlagBits = 0x06;

		// THE SIGNPOST FAMILY (attribution CORRECTED 2026-08-17 by screen
		// evidence): quad builder 0x5F20A0 does `push 44.0f` (0x5F20AF,
		// 68 00 00 30 42) into the px->world helper 0x7F6690, with
		// `push 150.0f` (0x5F20BF, 68 00 00 16 43) as the pole raise. The
		// family this draws is the POLE BALLOONS (mayor-hat sign over the
		// mayor's house, dispatch lollipops) - proven live when the v3.0.23
		// 2x sheet + cell doubling visibly moved the mayor-hat balloon.
		// It is NOT the U-Drive-It offer balloon: this patch plus the 2x
		// sheet plus doubled cells all ran in the same build and the blue
		// offer discs never moved (15th elimination). The earlier claim
		// here that the offer-click filter accepts the signpost occupant
		// (0x4B8947) described the CLICK path, not the drawer. Scaling
		// stays: pixel-fixed markers shrink at scaled tiers, so the 1.5x
		// signpost quad is the intended tier behavior for THIS family.
		const uintptr_t kSignpostSizeSite  = 0x5F20AF; // push 44.0f
		const uintptr_t kSignpostRaiseSite = 0x5F20BF; // push 150.0f
		const uint32_t kStockSignpostSizeBits  = 0x42300000; // 44.0f
		const uint32_t kStockSignpostRaiseBits = 0x43160000; // 150.0f

		// #188 BALLOONCELL: REVERTED 2026-08-17 (v3.0.24). The v3.0.23 pair -
		// a 2x sheet dat for {856DDBAC,AB7E5421,2BB075B4/2BB06F3F} plus a
		// doubling of the composer cell constants (0x34 at
		// 0x5F1455/0x5F1475/0x5F159B, 0xD0 at 0x5F15A6) - visibly MOVED the
		// mayor-hat pole balloon (regression: glyph misaligned) while the
		// U-Drive-It offer discs never changed. That closes the art route
		// for #188 and pins those sheets to the POLE-balloon family. Both
		// halves are withdrawn together: the dat is removed from Plugins
		// and the cell patch deleted (both-or-neither, same law that
		// shipped them together).

		// ---- #188 PIXTABLE ------------------------------------------------
		// Ten .rdata floats: five are a per-zoom ramp (20/30/40/50/60), the
		// rest are sibling sizes (60/14/32/35/64). Verify-before-write on the
		// WHOLE table, all-or-nothing, single-span VirtualProtect, and a loud
		// refusal if any value is not what we measured - the table being
		// exactly as dumped is the condition this patch depends on.
		// ⭐ THE CSI CONSTANTS. The balloon is a City Situation Indicator
		// drawn by cSC4DispatchVehicleView::Draw (0x0046D990); the manager is
		// cSC4CitySituationManager (vtable 0x00A97E58), and its view object is
		// [0x00B43D04]->vt+0x58 = cISC4DispatchManager::GetDispatchVehicleView.
		// Category 4 == CSI (special-cased at 0x0046DD6C), keyed on the
		// AUTOMATON (QI 0xA9B40F05 at 0x0046DDBD) - which is exactly why the
		// user could see it floats above the helicopter and the car.
		//
		// 0x00A8819C = 42.0f is THE indicator quad edge in SCREEN PIXELS, with
		// exactly four reads in the whole binary, all inside that Draw:
		//   0x0046E04E / 0x0046E05C  (radial / stacked path: x1=x0+42, y1=y0+42)
		//   0x0046E392 / 0x0046E3A0  (single-indicator path)
		// Nothing on this path multiplies by the UI factor - which IS the
		// symptom. And the user's two screenshots (same res, same tier, very
		// different zoom, identical balloon pixel size) independently prove the
		// thing is pixel-fixed, which is what a raw px constant produces.
		//
		// ⛔ 0x00A881AC is a per-category STYLE BYTE TABLE (01 01 01 01 02 02
		// 03 FF) - never scale it.
		const uintptr_t kPixTableVa = 0x00A88170;
		const float kPixStock[10] =
			{ 20.0f, 30.0f, 40.0f, 50.0f, 60.0f, 60.0f, 14.0f, 32.0f, 35.0f, 64.0f };
		// The CSI block proper: {VA, stock value}.
		struct CsiConst { uintptr_t va; float stock; };
		const CsiConst kCsiConsts[4] =
		{
			{ 0x00A8819C, 42.0f },   // indicator quad edge (px)  <- THE ONE
			{ 0x00A881A0, 50.0f },   // orbit radius when >1 indicator on a vehicle
			{ 0x00A88260, 43.0f },   // outline / leader offset
			{ 0x00A88268, 21.0f },   // half of 42 - the centring offset
		};

		// ---- #188 CSIKILL: subtraction test on the CSI DRAWER -------------
		// v3.0.34 scaled the four CSI pixel constants (42/50/43/21). The log
		// proves the write landed ("quad 42 -> 63 px") and NOTHING moved on
		// screen - so those constants are the hit/clip box, not the drawn quad
		// (which is exactly the caveat the research flagged: 42.0 is the
		// persisted per-item screen rect, and the textured blit goes through
		// 0x007D4070 / 0x007D2990 / 0x007D4530 / 0x007D2A20 / 0x007D4420 /
		// 0x007D2D20 / 0x007D2A30 / 0x007F78E0, none of them decoded yet).
		//
		// Before decoding eight blit helpers, settle whether this drawer draws
		// the balloon AT ALL. Suppressing a whole draw is the cheapest possible
		// discriminator and its expected result is an ABSENCE, which cannot be
		// misread as "no change" - the shape that has worked every time today
		// (0xAA8314, 0xA9F250, 0xA88248 were all closed this way).
		//   balloons GONE -> cSC4DispatchVehicleView::Draw IS the drawer; the
		//                    size is inside it, in the blit args
		//   balloons STAY -> CSI is out, and it joins the other eliminations
		typedef bool(__fastcall* CsiDrawFn)(void*, void*, void*);
		CsiDrawFn gCsiDrawOrig = nullptr;
		volatile LONG gCsiDrawCalls = 0;
		int gCsiKill = 0;
		const uintptr_t kCsiDrawVa = 0x0046D990;

		bool __fastcall CsiDrawDetour(void* self, void* edx, void* a1)
		{
			const LONG n = InterlockedIncrement(&gCsiDrawCalls);
			if (n == 1 || n == 400)
			{
				Logger::Get().WriteLine(LogLevel::Info,
					"CodePatches: CSIDRAW call #%ld this=%p (kill=%d).",
					n, self, gCsiKill);
			}
			if (gCsiKill) { return true; }   // draw nothing at all
			return gCsiDrawOrig(self, edx, a1);
		}

		void InstallCsiDrawProbe()
		{
			wchar_t ini[MAX_PATH] = {};
			GetModuleFileNameW(reinterpret_cast<HMODULE>(&__ImageBase), ini,
				MAX_PATH);
			wchar_t* sl = wcsrchr(ini, 92);   // L'\' written as its code unit
			if (sl) { wcscpy_s(sl + 1, 32, L"SC4UIScale.ini"); }
			gCsiKill = static_cast<int>(GetPrivateProfileIntW(
				L"UiSpike", L"CsiKill", 0, ini));
			const uintptr_t base =
				reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
			void* t = reinterpret_cast<void*>(base - kImageBase + kCsiDrawVa);
			const MH_STATUS init = MH_Initialize();
			if (init != MH_OK && init != MH_ERROR_ALREADY_INITIALIZED) { return; }
			if (MH_CreateHook(t, reinterpret_cast<void*>(&CsiDrawDetour),
					reinterpret_cast<void**>(&gCsiDrawOrig)) != MH_OK
				|| MH_EnableHook(t) != MH_OK)
			{
				Logger::Get().WriteLine(LogLevel::Error,
					"CodePatches: CSIDRAW failed to hook 0x0046D990.");
				return;
			}
			Logger::Get().WriteLine(LogLevel::Info,
				"CodePatches: CSIDRAW armed on cSC4DispatchVehicleView::Draw "
				"0x0046D990 (kill=%d). A call count of ZERO means this drawer "
				"never runs and the kill result is VOID.", gCsiKill);
		}

		// ------------------------------------------------------------------
		// #188 THE U-DRIVE-IT OFFER BALLOON (City Situation Indicator).
		//
		// The balloon is TWO independently sized quads, which is why every
		// single-number attempt produced a half-fix for a whole day:
		//
		//   QUAD A - the pin / backing plate. Eight +/-32.0f INLINE
		//     immediates in cSC4DispatchVehicleView::Draw (0x0046D990),
		//     written as `mov [esp+disp32], imm32` (C7 84 24 ...). 64x64,
		//     UV pinned 0..1, rotated to point at the vehicle.
		//
		//   QUAD B - the ICON (blue disc + glyph) AND ITS CLICK BOX.
		//     `mov eax, 0x420C0000` (35.0f) at 0x0046CC47, inside the
		//     CSI-only branch `cmp [esi+4],4` of the billboard builder
		//     0x0046C8B0. Stored to the indicator record's width AND height
		//     (+0xD0/+0xD4); Draw halves them to +/-17.5 half-extents.
		//     The hit box comes from the same pair, so art and tap target
		//     cannot drift apart - user-observed: "only the inner glyph is
		//     clickable".
		//
		//   QUAD B-PRIME - THE SAME ICON SIZE FOR CATEGORY 3.
		//     0x0046CC45 is `jne 0x0046CCB9`, which reads like a plain two-way
		//     else - and that reading is WRONG. Exhaustive branch-target
		//     enumeration over the whole builder 0x0046C8B0..0x0046D110 shows
		//     0x0046CC41 has exactly ONE inbound edge, from a straight-line
		//     block entered only from 0x0046CB52, which is itself entered from
		//     BOTH `cmp [esi+4],3` and `cmp [esi+4],4`. So 3 and 4 SHARE the
		//     path and then split: 4 takes 35.0f, 3 takes 32.0f. The store at
		//     0x0046CCB9 executes for category 3 and nothing else.
		//
		// ⛔ SO THE BLAST RADIUS IS CATEGORY 3 ALONE, not "every non-4 type".
		// The wider claim came from eyeballing one `jne` and assuming the
		// obvious control flow; it took enumerating every jcc target in the
		// function to see that two categories merge before they split. Reading
		// ONE branch tells you where that branch goes, never who arrives.
		//
		// ⛔ AND THIS IS NOT THE CURE FOR #195. The 3x run PROVED it: the
		// patch applied (log: "32.0 -> 96.0 px", 10 immediates) and the split
		// marker did not change. #195 is the marker's ROOT being moved by
		// ScalePanelRoot away from where the game places the count - see
		// UiSpike.cpp's ARTSIZED-ROOT block. This entry stays because it is
		// independently correct (category 3's plate scales while its icon did
		// not), but it never was that defect.
		// ⭐ A PATCH THAT PROVABLY RAN AND CHANGED NOTHING ON SCREEN
		// ELIMINATES ITS WHOLE LAYER - worth more than most positive findings.
		//
		// ⭐ THE OLD NOTE HERE SAID TO LEAVE THIS ALONE - "it would resize
		// unrelated indicators". That reasoning inverted the day the pin quad
		// was scaled: the pin verts live in cSC4DispatchVehicleView::Draw,
		// which is SHARED by every indicator regardless of type, so once the
		// pin scaled, category 3 was not being spared - it was HALF-PATCHED,
		// scaled plate on a stock icon. Scaling this puts it back in step.
		// A caution written about one lever goes stale the moment a SECOND
		// lever starts firing on the same object; re-read every such note when
		// the set of patched sites grows.
		// ⚠ But note what the old caution got RIGHT and this correction had
		// to walk back: the affected set really is narrow (category 3), not
		// "everything that is not 4". Being right about the direction of a
		// change does not make you right about its reach.
		//
		// ⛔ 0x0046CCB9 IS THE OPCODE BYTE (B8). THE IMMEDIATE IS AT
		// 0x0046CCBA. This table stores IMMEDIATE addresses - 0x0046CC48 is the
		// imm of the B8 at 0x0046CC47, one past it, same as here. Entering the
		// opcode address instead would read 00 00 00 42 89 = 2.58e-43, miss the
		// 32.0f the all-or-none verify expects, and REFUSE THE ENTIRE TABLE -
		// silently reverting the balloon that already works. The failure would
		// present as "the new fix did nothing AND the old one broke", which is
		// the most expensive way to be wrong. Bytes were read out of the shipped
		// exe, not out of this comment.
		//
		// ⭐ WHY THIS TOOK SO LONG, recorded so it is not repeated: every
		// sweep searched .rdata for a constant. BOTH levers are inline
		// immediates in .text. A ".rdata constant is inert" verdict is a
		// FILTERED NULL unless inline immediates were scanned too.
		//
		// The 42.0f at 0x00A8819C is NOT a size: it reaches the quad
		// TRANSLATION (centre = x0 + 42/2). Scaling it moved the balloon
		// ~10px and changed nothing visible - which is exactly how a LIVE
		// constant can look dead. Left alone here.
		struct CsiQuadConst { uintptr_t va; float stock; const char* what; };
		const CsiQuadConst kCsiQuad[] = {
			{ 0x0046CC48, 35.0f, "icon+hitbox" },   // mov eax,imm32  (B8)
			// #195: the ELSE of `cmp [esi+4],4`. Same instruction, same
			// `mov [esi+0xD0/0xD4],eax` store pair, 32.0f instead of 35.0f.
			// Covers every non-type-4 indicator - including the U-Drive-It
			// deployment marker, whose count was rendering at stock size under
			// an already-scaled pin.
			{ 0x0046CCBA, 32.0f, "icon+hitbox (category 3)" },
			// ⛔ 0x0046CB09 (the text-indicator HEIGHT, 14.0f) WAS HERE AND WAS
			// REMOVED THE SAME DAY. It is a real unscaled constant and it is
			// still NOT a lever, for a reason worth keeping:
			//
			//   the TEXT categories size themselves as
			//       0x0046CAF0  fild [esp+0x48]        ; measured text width
			//       0x0046CAFD  fstp [esi+0xD0]        ; WIDTH  = computed
			//       0x0046CB03  mov  [esi+0xD4], 14.0f ; HEIGHT = immediate
			//   but the content quad's UVs come from the measured pixel extents
			//   and the POWER-OF-TWO texture size ([esp+0x18], set at
			//   0x0046C8EA / 0x0046CA04 / 0x0046CC65) - NOT from +0xD0/+0xD4.
			//
			// So scaling the height alone stretches the digits VERTICALLY and
			// nothing else: a new defect wearing the shape of a fix. Both
			// numbers have to move together and the width is not a constant at
			// all, so no entry in this table can do it.
			//
			// ⭐ THIS WAS MEASURED BEFORE IT WAS SHIPPED, AND SHIPPED ANYWAY.
			// The finding that says "scaling 14.0f alone is a new defect, not a
			// fix" was already written when the entry was added; it was applied
			// off the first half of the report without reading to the end. The
			// user confirmed "not fixed" on the very next run. READ THE WHOLE
			// MEASUREMENT BEFORE ACTING ON ITS FIRST PARAGRAPH.
			{ 0x0046EABD, -32.0f, "pin V0.x" },     // C7 84 24 ... imm at +7
			{ 0x0046EACA, -32.0f, "pin V0.y" },
			{ 0x0046EAF6, -32.0f, "pin V1.x" },
			{ 0x0046EB01,  32.0f, "pin V1.y" },
			{ 0x0046EB2D,  32.0f, "pin V2.x" },
			{ 0x0046EB38,  32.0f, "pin V2.y" },
			{ 0x0046EB64,  32.0f, "pin V3.x" },
			{ 0x0046EB6F, -32.0f, "pin V3.y" },
		};

		void ApplyCsiIndicatorScale(float factor)
		{
			const uintptr_t base =
				reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
			const int n = static_cast<int>(
				sizeof(kCsiQuad) / sizeof(kCsiQuad[0]));
			// BOTH-OR-NEITHER. A partial application is the one outcome we
			// must never ship: the pin at 1.5x with the icon at 1x is the
			// exact broken state this task spent a day inside.
			for (int k = 0; k < n; ++k)
			{
				const float cur = *reinterpret_cast<float*>(
					kCsiQuad[k].va + base - kImageBase);
				if (cur != kCsiQuad[k].stock)
				{
					Logger::Get().WriteLine(LogLevel::Info,
						"CodePatches: CSI 0x%08X (%s) reads %.2f, expected "
						"%.2f - REFUSED, nothing written (all %d or none).",
						static_cast<unsigned>(kCsiQuad[k].va),
						kCsiQuad[k].what, cur, kCsiQuad[k].stock, n);
					return;
				}
			}
			for (int k = 0; k < n; ++k)
			{
				float* p = reinterpret_cast<float*>(
					kCsiQuad[k].va + base - kImageBase);
				DWORD old = 0;
				if (!VirtualProtect(p, sizeof(float), PAGE_READWRITE, &old))
				{
					Logger::Get().WriteLine(LogLevel::Info,
						"CodePatches: CSI VirtualProtect failed at 0x%08X.",
						static_cast<unsigned>(kCsiQuad[k].va));
					return;
				}
				*p = kCsiQuad[k].stock * factor;
				VirtualProtect(p, sizeof(float), old, &old);
			}
			Logger::Get().WriteLine(LogLevel::Info,
				"CodePatches: CSI indicators x%.2f - icon+hitbox %.1f -> %.1f px "
				"(type 4) and %.1f -> %.1f px (type 3), pin quad 64 -> %.0f px. "
				"%d immediates, all inline in .text. #188/#195.",
				factor, 35.0f, 35.0f * factor, 32.0f, 32.0f * factor,
				64.0f * factor, n);
		}

		// ---- #191 MY SIM WORLD MARKER: the icon's UV divisor is a 64 -------
		// The framed sim face floating over a house is CATEGORY 3 of THIS same
		// dispatch-indicator system, not a window and not the signpost
		// lollipop. cSC4MySim (CID 0x4A1DBBBF, GetGZCLSID 0x00424AF0) ->
		// cSC4MySimDispatch (CID 0xCBC14674, GetGZCLSID 0x00433D40) ->
		// AddIndicator(..., 3, ...). Only two of the seven AddIndicator call
		// sites pass 3 and BOTH are in the MySim module: 0x004356F5 and
		// 0x0043E711. Its face is fetched at 0x0046CB7B as
		// {T=0x856DDBAC, G=0x46A006B0, I=<the sim's own instance>} - the SAME
		// 19 portraits #190 restaged.
		//
		// The icon quad's UVs are pixelExtent / [esp+0x18], where [esp+0x18]
		// is the SQUARE power-of-two texture side. Category 4 COMPUTES it
		// (0x0046CC4C push width; 0x0046CC59 call 0x006046B0 = NextPow2).
		// Category 3 HARD-CODES it:
		//     0x0046CCCA  C7 44 24 18 40 00 00 00  mov [esp+0x18], 64
		// consumed at 0x0046CD9E (fild; fdivr 1.0f) and written into the
		// record UVs at 0x0046CDDC / 0x0046CDE7 / 0x0046CE18.
		//
		// The uploader 0x006046D0 makes the texture SQUARE, side =
		// max(NextPow2(w), NextPow2(h)) - two loops at 0x0060474D/0x0060475C,
		// max picked at 0x0060477A. MEASURED from the shipped payloads, all 38
		// staged portraits (19 ids x 2 groups):
		//     1x    36x41  -> side  64   (the stock 64 is CORRECT)
		//     1.5x  54x62  -> side  64   (still CORRECT - must stay 64)
		//     2x    72x82  -> side 128
		//     3x   108x123 -> side 128
		// So from 2x up the divisor is HALF the real texture side, every UV is
		// 2x too large, and the face draws at 50% of its quad anchored to the
		// corner (u0 = 0, forced by the fmul against 0.0f at 0x00A81054) -
		// i.e. exactly 1x-sized and off-centre inside a pin our own kCsiQuad
		// correctly doubled. THIS IS A #190 REGRESSION: with the stock 36x41
		// art the constant was right at every tier.
		//
		// SCOPE, byte-proven: 0x0046CCB9 is reached ONLY by `cmp [esi+4],4 ;
		// jne` at 0x0046CC45, and 0x0046CB52 ONLY by `cmp eax,3 ; je`
		// (0x0046C928) and `cmp eax,4 ; je` (0x0046C931). A capstone branch
		// sweep of 0x0046C8B0-0x0046D200 found no other edge, and no rel32
		// call/jmp in .text targets either address. Category 3 is MySim and
		// nothing else - the 32 at 0x0046C8EA and the computed store at
		// 0x0046CA04 belong to the TEXT categories and are NOT touched.
		void ApplyMySimMarkerTexSide(float factor)
		{
			const uintptr_t kVa = 0x0046CCCE;  // imm32 of the C7 at 0x0046CCCA
			const uintptr_t base =
				reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
			uint32_t* p =
				reinterpret_cast<uint32_t*>(kVa + base - kImageBase);
			if (*p != 64u)
			{
				Logger::Get().WriteLine(LogLevel::Info,
					"CodePatches: MYSIMTEX 0x%08X reads %u, expected 64 - "
					"REFUSED, nothing written (#191).",
					static_cast<unsigned>(kVa), static_cast<unsigned>(*p));
				return;
			}
			// DERIVE FROM THE ART, NEVER FROM THE FACTOR. The staged portrait
			// is round(36*f) x round(41*f) and the uploader squares it up.
			const int w = static_cast<int>(36.0f * factor + 0.5f);
			const int h = static_cast<int>(41.0f * factor + 0.5f);
			const int big = (w > h) ? w : h;
			uint32_t side = 1u;
			while (side < static_cast<uint32_t>(big)) { side <<= 1; }
			if (side == 64u)
			{
				Logger::Get().WriteLine(LogLevel::Info,
					"CodePatches: MYSIMTEX INERT at x%.2f - the staged "
					"portrait %dx%d still fits a 64px square texture, so the "
					"stock constant is already correct (#191).",
					factor, w, h);
				return;
			}
			DWORD old = 0;
			if (!VirtualProtect(p, sizeof(uint32_t), PAGE_READWRITE, &old))
			{
				Logger::Get().WriteLine(LogLevel::Info,
					"CodePatches: MYSIMTEX VirtualProtect failed at 0x%08X - "
					"skipped (#191).", static_cast<unsigned>(kVa));
				return;
			}
			*p = side;
			VirtualProtect(p, sizeof(uint32_t), old, &old);
			Logger::Get().WriteLine(LogLevel::Info,
				"CodePatches: MYSIMTEX x%.2f - My Sim marker icon UV divisor "
				"64 -> %u to match the staged %dx%d portrait's square texture "
				"(category 3 only, imm32 at 0x%08X). #191.",
				factor, static_cast<unsigned>(side), w, h,
				static_cast<unsigned>(kVa));
		}

		// ------------------------------------------------------------------
		// CSIAIM - re-aim the CSI size hunt from the INI, with NO REBUILD.
		//
		// #188 burned seventeen launches at roughly one yes/no answer each.
		// The art is now PROVEN live (we shipped the eight icons red and the
		// discs rendered red), and PROVEN not to carry the size (the same
		// icons at 228x57 drew pixel-identical). So the size is a number in
		// the code - and the only question left is WHICH number. That is a
		// question with many candidates and one launch per answer, which is
		// exactly the shape that has to stop costing a build each time.
		//
		// Grammar, comma or semicolon separated:
		//     VA ':' TYPE EXPECTED [ ':' MULT ]
		//   TYPE  f=float32  d=int32  w=int16  b=uint8
		//   EXPECTED is the STOCK value; we refuse the entry unless it reads
		//   back exactly that (verify-before-write, the house idiom - it is
		//   what proved the MARKERSIZE write landed even when nothing moved).
		//   MULT defaults to the tier factor, so entries stay tier-general.
		//
		// Example:  CsiAim = 0x0046E0C1:b38, 0x00A8819C:f42:2.0
		//
		// Entries are INDEPENDENT: one refusal does not suppress the others,
		// because the whole point is to aim several candidates at one launch.
		// Every entry logs pre AND post value - a write with no read-back is
		// how a "successful" patch hides being dead code.
		void ApplyCsiAimList(float factor)
		{
			wchar_t ini[MAX_PATH] = {};
			GetModuleFileNameW(reinterpret_cast<HMODULE>(&__ImageBase), ini,
				MAX_PATH);
			wchar_t* sl = wcsrchr(ini, 92);   // L'\' as its code unit
			if (sl) { wcscpy_s(sl + 1, 32, L"SC4UIScale.ini"); }
			wchar_t spec[512] = {};
			GetPrivateProfileStringW(L"UiSpike", L"CsiAim", L"", spec, 512, ini);
			if (spec[0] == 0) { return; }

			char buf[512] = {};
			WideCharToMultiByte(CP_ACP, 0, spec, -1, buf, 512, nullptr, nullptr);
			const uintptr_t base =
				reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));

			int applied = 0, refused = 0;
			char* ctx = nullptr;
			for (char* tok = strtok_s(buf, ",;", &ctx); tok;
				tok = strtok_s(nullptr, ",;", &ctx))
			{
				while (*tok == ' ' || *tok == '\t') { ++tok; }
				unsigned va = 0; char type = 0; double expect = 0.0, mult = 0.0;
				const int n = sscanf_s(tok, "%x : %c %lf : %lf", &va,
					&type, static_cast<unsigned>(sizeof(type)), &expect, &mult);
				if (n < 3)
				{
					Logger::Get().WriteLine(LogLevel::Info,
						"CodePatches: CSIAIM cannot parse '%s' - expected "
						"VA:TYPE_EXPECTED[:MULT], e.g. 0x0046E0C1:b38.", tok);
					++refused;
					continue;
				}
				if (n < 4 || mult <= 0.0) { mult = factor; }
				if (va < kImageBase || va > kImageBase + 0x00800000)
				{
					Logger::Get().WriteLine(LogLevel::Info,
						"CodePatches: CSIAIM 0x%08X is outside the image - "
						"REFUSED.", va);
					++refused;
					continue;
				}
				void* p = reinterpret_cast<void*>(va + base - kImageBase);
				size_t width = 0;
				double cur = 0.0;
				switch (type)
				{
				case 'f': width = 4; cur = *static_cast<float*>(p); break;
				case 'd': width = 4; cur = *static_cast<int*>(p); break;
				case 'w': width = 2; cur = *static_cast<short*>(p); break;
				case 'b': width = 1; cur = *static_cast<unsigned char*>(p); break;
				default:
					Logger::Get().WriteLine(LogLevel::Info,
						"CodePatches: CSIAIM unknown type '%c' at 0x%08X "
						"(want f/d/w/b) - REFUSED.", type, va);
					++refused;
					continue;
				}
				if (cur != expect)
				{
					// The refusal is the VALUABLE outcome here: it means the
					// address is not what the disassembly said it was, and
					// writing it would corrupt something unrelated.
					Logger::Get().WriteLine(LogLevel::Info,
						"CodePatches: CSIAIM 0x%08X reads %.4f, expected "
						"%.4f - REFUSED (nothing written).", va, cur, expect);
					++refused;
					continue;
				}
				// floor(v*f+0.5) for the integer widths: ONE rounding
				// convention across sweep, upscaler and builders (law #89).
				const double want = cur * mult;
				DWORD old = 0;
				if (!VirtualProtect(p, width, PAGE_READWRITE, &old))
				{
					Logger::Get().WriteLine(LogLevel::Info,
						"CodePatches: CSIAIM VirtualProtect failed at 0x%08X.",
						va);
					++refused;
					continue;
				}
				switch (type)
				{
				case 'f': *static_cast<float*>(p) =
					static_cast<float>(want); break;
				case 'd': *static_cast<int*>(p) =
					static_cast<int>(want + 0.5); break;
				case 'w': *static_cast<short*>(p) =
					static_cast<short>(want + 0.5); break;
				case 'b': *static_cast<unsigned char*>(p) =
					static_cast<unsigned char>(want + 0.5); break;
				}
				VirtualProtect(p, width, old, &old);
				double post = 0.0;
				switch (type)
				{
				case 'f': post = *static_cast<float*>(p); break;
				case 'd': post = *static_cast<int*>(p); break;
				case 'w': post = *static_cast<short*>(p); break;
				case 'b': post = *static_cast<unsigned char*>(p); break;
				}
				Logger::Get().WriteLine(LogLevel::Info,
					"CodePatches: CSIAIM 0x%08X [%c] %.4f -> %.4f (read back "
					"%.4f, x%.3f).", va, type, cur, want, post, mult);
				++applied;
			}
			Logger::Get().WriteLine(LogLevel::Info,
				"CodePatches: CSIAIM %d applied, %d refused. A refusal means "
				"the ADDRESS is wrong, not that the idea is.", applied, refused);
		}

		void ApplyCsiScale(float want)
		{
			const uintptr_t base =
				reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
			// Verify ALL FOUR before touching any (both-or-neither).
			for (int k = 0; k < 4; ++k)
			{
				const float cur = *reinterpret_cast<float*>(
					kCsiConsts[k].va + base - kImageBase);
				if (cur != kCsiConsts[k].stock)
				{
					Logger::Get().WriteLine(LogLevel::Info,
						"CodePatches: CSI 0x%08X reads %d, expected %d - REFUSED "
						"(nothing written).",
						static_cast<unsigned>(kCsiConsts[k].va),
						static_cast<int>(cur),
						static_cast<int>(kCsiConsts[k].stock));
					return;
				}
			}
			for (int k = 0; k < 4; ++k)
			{
				float* p = reinterpret_cast<float*>(
					kCsiConsts[k].va + base - kImageBase);
				DWORD old = 0;
				if (!VirtualProtect(p, sizeof(float), PAGE_READWRITE, &old))
				{
					Logger::Get().WriteLine(LogLevel::Info,
						"CodePatches: CSI VirtualProtect failed at 0x%08X.",
						static_cast<unsigned>(kCsiConsts[k].va));
					return;
				}
				*p = kCsiConsts[k].stock * want;
				VirtualProtect(p, sizeof(float), old, &old);
			}
			Logger::Get().WriteLine(LogLevel::Info,
				"CodePatches: CSI indicator x%d.%02d - quad 42 -> %d px, orbit "
				"50 -> %d, leader 43 -> %d, centre 21 -> %d (drawer 0x0046D990).",
				static_cast<int>(want),
				static_cast<int>((want - static_cast<int>(want)) * 100),
				static_cast<int>(42.0f * want), static_cast<int>(50.0f * want),
				static_cast<int>(43.0f * want), static_cast<int>(21.0f * want));
		}

		void ApplyPixelTable(float want)
		{
			const uintptr_t base =
				reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
			float* t = reinterpret_cast<float*>(kPixTableVa + base - kImageBase);
			for (int k = 0; k < 10; ++k)
			{
				if (t[k] != kPixStock[k])
				{
					Logger::Get().WriteLine(LogLevel::Info,
						"CodePatches: PIXTABLE slot %d is %d.%02d, expected %d - "
						"table not as measured, REFUSED (nothing written).", k,
						static_cast<int>(t[k]),
						static_cast<int>((t[k] - static_cast<int>(t[k])) * 100),
						static_cast<int>(kPixStock[k]));
					return;
				}
			}
			DWORD old = 0;
			if (!VirtualProtect(t, 10 * sizeof(float), PAGE_READWRITE, &old))
			{
				Logger::Get().WriteLine(LogLevel::Info,
					"CodePatches: PIXTABLE VirtualProtect failed.");
				return;
			}
			for (int k = 0; k < 10; ++k) { t[k] = kPixStock[k] * want; }
			VirtualProtect(t, 10 * sizeof(float), old, &old);
			Logger::Get().WriteLine(LogLevel::Info,
				"CodePatches: PIXTABLE 0x00A88170 x%d.%02d -> "
				"{%d,%d,%d,%d,%d, %d,%d,%d,%d,%d} px.",
				static_cast<int>(want),
				static_cast<int>((want - static_cast<int>(want)) * 100),
				static_cast<int>(t[0]), static_cast<int>(t[1]),
				static_cast<int>(t[2]), static_cast<int>(t[3]),
				static_cast<int>(t[4]), static_cast<int>(t[5]),
				static_cast<int>(t[6]), static_cast<int>(t[7]),
				static_cast<int>(t[8]), static_cast<int>(t[9]));
		}

		void ApplySignpostScale(float want)
		{
			const uintptr_t base = reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
			const uintptr_t delta = base - kImageBase;
			uint8_t* ps = reinterpret_cast<uint8_t*>(kSignpostSizeSite + delta);
			uint8_t* pr = reinterpret_cast<uint8_t*>(kSignpostRaiseSite + delta);

			// Verify-before-write, BOTH sites before touching EITHER (the
			// cost-box law: a scaled disc on a 1x pole reads as half-patched).
			uint32_t curS = 0, curR = 0;
			memcpy(&curS, ps + 1, 4);
			memcpy(&curR, pr + 1, 4);
			if (ps[0] != kPushImm32 || curS != kStockSignpostSizeBits
				|| pr[0] != kPushImm32 || curR != kStockSignpostRaiseBits)
			{
				Logger::Get().WriteLine(LogLevel::Info,
					"CodePatches: SIGNPOST sites unexpected (%02X %08X @0x%08X, "
					"%02X %08X @0x%08X) - skipped, balloons stay 44px.",
					ps[0], curS, static_cast<uint32_t>(kSignpostSizeSite),
					pr[0], curR, static_cast<uint32_t>(kSignpostRaiseSite));
				return;
			}

			const float newSize = 44.0f * want;
			const float newRaise = 150.0f * want;
			uint32_t sizeBits = 0, raiseBits = 0;
			memcpy(&sizeBits, &newSize, 4);
			memcpy(&raiseBits, &newRaise, 4);

			// ONE VirtualProtect spanning both sites (16 bytes apart, same
			// page). A nested per-site pair captures the second "old"
			// protection AFTER the first flip has already made the page
			// RWX, so the final restore would leave live game code
			// writable for the rest of the process (review 2026-08-17,
			// finding 2 - the cost-box patch carried the same defect and
			// was reshaped identically).
			const SIZE_T span = static_cast<SIZE_T>((pr + 5) - ps);
			DWORD oldProt = 0;
			if (!VirtualProtect(ps, span, PAGE_EXECUTE_READWRITE, &oldProt))
			{
				Logger::Get().WriteLine(LogLevel::Info,
					"CodePatches: VirtualProtect failed at 0x%08X - SIGNPOST skipped.",
					static_cast<uint32_t>(kSignpostSizeSite));
				return;
			}
			memcpy(ps + 1, &sizeBits, 4);
			memcpy(pr + 1, &raiseBits, 4);
			VirtualProtect(ps, span, oldProt, &oldProt);
			FlushInstructionCache(GetCurrentProcess(), ps, span);

			Logger::Get().WriteLine(LogLevel::Info,
				"CodePatches: SIGNPOST balloon 44 -> %.1f px, raise 150 -> %.1f "
				"px at 0x%08X/0x%08X.",
				static_cast<double>(newSize), static_cast<double>(newRaise),
				static_cast<uint32_t>(kSignpostSizeSite),
				static_cast<uint32_t>(kSignpostRaiseSite));
		}

		// ---- #188 PROBE MODE (ini MissionBubbleFx=3) -----------------------
		// Four byte-true patches produced no visual change on the balloon;
		// static analysis has mis-identified its draw path that many times.
		// These two LOG-ONLY hooks settle it from the RUNNING game: does the
		// signpost quad builder (0x5F20A0) execute at all while balloons are
		// on screen, for which kind ([this+0x70]; 4 = mission balloon), and
		// with which size imm actually live in the code page. The texture-
		// ensure fn (0x5F1610) fires per signpost draw and names the kinds
		// that exist. Unknown arity -> naked log-and-relay (the thiscall
		// law: never guess a convention); zero writes, capped log lines,
		// uncapped counters.
		void* gSpQuadTramp = nullptr;
		void* gSpTexTramp = nullptr;
		volatile LONG gSpQuadCalls = 0;
		volatile LONG gSpTexCalls = 0;
		int gSpQuadLogs = 0;
		int gSpTexLogs = 0;

		const uintptr_t kSpQuadVa = 0x5F20A0;
		const uint8_t kSpQuadStock[5] = { 0x83, 0xEC, 0x48, 0x53, 0x55 };
		const uintptr_t kSpTexVa = 0x5F1610;
		const uint8_t kSpTexStock[5] = { 0x83, 0xEC, 0x10, 0x53, 0x56 };

		// THE LIVE BALLOON BUILDER (third disassembly pass, 2026-08-17,
		// model PREDICTS the user's measured 45-48px: 64px body x
		// zoomTable[2]=0.75 = 48). The offer balloon is a MARKER attachment
		// (occupant marker type 0xCB79919B) whose billboard strip is
		// code-generated by 0x5F5FB0: content icons (default 24px) + 8px
		// margins + 64px disc, every pixel dimension multiplied by the
		// per-zoom float table at .rdata 0xAA523C = {0.5,0.75,1.0,1.5,2.0}
		// (read at 0x5F6067 `fld [ecx*4+0xAA523C]`; the only other .text
		// ref, 0x5F74AD, is a texture-loop END BOUND compare, not a read -
		// sole-consumer PROVEN). The renderer pick tests the very verts
		// this builder writes, so scaling the table grows the click target
		// with the visual. Dispatch markers share the builder and co-scale
		// (desired). The 44px lollipop path patched above is this system's
		// DORMANT twin (SPPROBE measured zero calls) - left patched,
		// harmless.
		const uintptr_t kMarkerZoomTableVa = 0xAA523C;
		const uint32_t kStockMarkerZoom[5] =
			{ 0x3F000000, 0x3F400000, 0x3F800000, 0x3FC00000, 0x40000000 };
		const uintptr_t kMarkerStripVa = 0x5F5FB0;
		const uint8_t kMarkerStripStock[6] = { 0x55, 0x8B, 0xEC, 0x83, 0xE4, 0xF8 };

		void ApplyMarkerZoomScale(float want)
		{
			const uintptr_t base =
				reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
			uint8_t* pt = reinterpret_cast<uint8_t*>(base - kImageBase + kMarkerZoomTableVa);
			if (memcmp(pt, kStockMarkerZoom, sizeof(kStockMarkerZoom)) != 0)
			{
				Logger::Get().WriteLine(LogLevel::Info,
					"CodePatches: MARKERZOOM table at 0x%08X unexpected - "
					"skipped, balloons stay stock.",
					static_cast<uint32_t>(kMarkerZoomTableVa));
				return;
			}
			float scaled[5];
			for (int k = 0; k < 5; ++k)
			{
				float v = 0.0f;
				memcpy(&v, &kStockMarkerZoom[k], 4);
				scaled[k] = v * want;
			}
			DWORD oldProt = 0;
			if (!VirtualProtect(pt, sizeof(scaled), PAGE_READWRITE, &oldProt))
			{
				Logger::Get().WriteLine(LogLevel::Info,
					"CodePatches: VirtualProtect failed at 0x%08X - MARKERZOOM "
					"skipped.", static_cast<uint32_t>(kMarkerZoomTableVa));
				return;
			}
			memcpy(pt, scaled, sizeof(scaled));
			VirtualProtect(pt, sizeof(scaled), oldProt, &oldProt);
			Logger::Get().WriteLine(LogLevel::Info,
				"CodePatches: MARKERZOOM table x%.2f -> {%.2f, %.3f, %.2f, "
				"%.2f, %.2f} at 0x%08X.",
				static_cast<double>(want), static_cast<double>(scaled[0]),
				static_cast<double>(scaled[1]), static_cast<double>(scaled[2]),
				static_cast<double>(scaled[3]), static_cast<double>(scaled[4]),
				static_cast<uint32_t>(kMarkerZoomTableVa));
		}

		void* gSpStripTramp = nullptr;
		volatile LONG gSpStripCalls = 0;
		int gSpStripLogs = 0;

		void __stdcall SpStripLog(void* self)
		{
			InterlockedIncrement(&gSpStripCalls);
			if (gSpStripLogs >= 16) { return; }
			++gSpStripLogs;
			const uintptr_t base =
				reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
			const uintptr_t d = base - kImageBase;
			uint32_t zoom = 0xFFFFFFFFu;
			float tv = 0.0f;
			void* vu = *reinterpret_cast<void**>(d + 0xB43DD8);
			if (vu)
			{
				zoom = *reinterpret_cast<uint32_t*>(
					static_cast<uint8_t*>(vu) + 0xC);
				if (zoom < 5)
				{
					memcpy(&tv, reinterpret_cast<void*>(
						d + kMarkerZoomTableVa + zoom * 4), 4);
				}
			}
			Logger::Get().WriteLine(LogLevel::Info,
				"CodePatches: SPSTRIP #%ld this=%p zoom=%u table=%.3f.",
				gSpStripCalls, self, zoom, static_cast<double>(tv));
		}
		__declspec(naked) void SpStripDetour()
		{
			__asm {
				pushad
				pushfd
				push ecx
				call SpStripLog
				popfd
				popad
				jmp dword ptr [gSpStripTramp]
			}
		}

		// The marker ATTACH helper 0x5F7C80 - the choke point BOTH marker
		// flavors traverse when a marker occupant gains its view object
		// (callers: signpost 0x5F7F6F-family, balloon 0x5F8074/0x5F8182/
		// 0x5F8265 per the fourth disassembly pass). Fires at city load for
		// every existing marker - no user interaction needed. The log line
		// carries the view object's VTABLE (its class names itself) and the
		// RETURN ADDRESS (which caller/flavor attached it).
		void* gSpAttachTramp = nullptr;
		volatile LONG gSpAttachCalls = 0;
		int gSpAttachLogs = 0;
		const uintptr_t kSpAttachVa = 0x5F7C80;
		const uint8_t kSpAttachStock[10] =
			{ 0x53, 0x56, 0x8B, 0xF1, 0x8B, 0x86, 0x84, 0x00, 0x00, 0x00 };

		void __stdcall SpAttachLog(void* self, void* retaddr)
		{
			InterlockedIncrement(&gSpAttachCalls);
			if (gSpAttachLogs >= 24) { return; }
			++gSpAttachLogs;
			const uintptr_t base =
				reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
			uint32_t vtVa = 0;
			if (self)
			{
				const uintptr_t vt = *reinterpret_cast<uintptr_t*>(self);
				vtVa = static_cast<uint32_t>(vt - base + kImageBase);
			}
			const uint32_t retVa = static_cast<uint32_t>(
				reinterpret_cast<uintptr_t>(retaddr) - base + kImageBase);
			Logger::Get().WriteLine(LogLevel::Info,
				"CodePatches: SPATTACH #%ld this=%p vt=0x%08X ret=0x%08X.",
				gSpAttachCalls, self, vtVa, retVa);
		}
		__declspec(naked) void SpAttachDetour()
		{
			__asm {
				pushad
				pushfd
				mov eax, [esp + 36]
				push eax
				push ecx
				call SpAttachLog
				popfd
				popad
				jmp dword ptr [gSpAttachTramp]
			}
		}

		// SetTrackedTarget 0x528580 - STACK-PROVEN LIVE (frame 0x52B1B0 =
		// its caller's ret addr, captured on both balloon clicks). The
		// clicked offer OCCUPANT crosses this threshold as [esp+4] on
		// every click. Log its vtable (the balloon-host class names
		// itself), GetType, and which of the three candidate interfaces
		// it exposes - with each QI'd interface's OWN vtable (the leads
		// to the drawer). QI AddRefs; Release via vt[2].
		typedef uint32_t (__thiscall* ObjGetTypeFn)(void*);
		typedef bool (__thiscall* ObjQiFn)(void*, uint32_t, void**);
		typedef void (__thiscall* ObjRelFn)(void*);

		void* gSpTargetTramp = nullptr;
		volatile LONG gSpTargetCalls = 0;
		int gSpTargetLogs = 0;
		const uintptr_t kSpTargetVa = 0x528580;
		const uint8_t kSpTargetStock[8] =
			{ 0x81, 0xEC, 0xC0, 0x00, 0x00, 0x00, 0x53, 0x8B };

		void __stdcall SpTargetLog(void* self, void* occ)
		{
			InterlockedIncrement(&gSpTargetCalls);
			if (gSpTargetLogs >= 8 || !occ) { return; }
			++gSpTargetLogs;
			const uintptr_t base =
				reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
			void** vt = *reinterpret_cast<void***>(occ);
			const uint32_t vtVa = static_cast<uint32_t>(
				reinterpret_cast<uintptr_t>(vt) - base + kImageBase);
			const uint32_t type =
				reinterpret_cast<ObjGetTypeFn>(vt[0x1C / 4])(occ);
			const uint32_t iids[3] =
				{ 0xE9793A65, 0x4B44FBE2, 0xA9B40F05 };
			uint32_t ivt[3] = { 0, 0, 0 };
			for (int k = 0; k < 3; ++k)
			{
				void* p = nullptr;
				if (reinterpret_cast<ObjQiFn>(vt[0])(occ, iids[k], &p) && p)
				{
					void** pv = *reinterpret_cast<void***>(p);
					ivt[k] = static_cast<uint32_t>(
						reinterpret_cast<uintptr_t>(pv) - base + kImageBase);
					reinterpret_cast<ObjRelFn>(pv[2])(p);
				}
			}
			Logger::Get().WriteLine(LogLevel::Info,
				"CodePatches: OFFERTARGET #%ld occ=%p vt=0x%08X type=0x%08X "
				"qiE979=0x%08X qi4B44=0x%08X qiA9B4=0x%08X.",
				gSpTargetCalls, occ, vtVa, type, ivt[0], ivt[1], ivt[2]);

			// ---- #188 OFFERBOX: the clicked object's OWN world box --------
			// The user's insight: "a physical button appears and we click
			// it" - so something must hit-test it, and a hit test needs
			// geometry. Class 0xA87238 (this object, captured 6x) overrides
			// exactly the geometry slots, and the bytes say where it keeps
			// them:
			//   0x458C30 GetBoundingBox: min <- [this+0x38/0x3C/0x40],
			//                            max <- [this+0x44/0x48/0x4C]
			//   0x458BA0 GetPosition:    returns (min+max) * 0.5f
			//                            (0.5f lives at .rdata 0xA84D2C)
			//   0x458BD0 SetPosition:    preserves half-extents, re-centres
			// So its SIZE is a plain float AABB on the object - readable and,
			// unlike the marker's byte-encoded SetSize, not obviously a
			// spatial-index key.
			//
			// ⚠ READ ONLY FOR NOW, and the reading decides the next step:
			// the pick can legitimately return the BALLOON or the occupant
			// in the cell BENEATH it (the 16 m cell fallback is proven).
			// A balloon floats: expect a small box well ABOVE terrain
			// (~y>410 here, terrain reads ~400). A building sits ON terrain
			// with lot-sized x/z. The numbers tell us which we caught, and
			// no theory has to be right first.
			__try
			{
				const float* b = reinterpret_cast<const float*>(
					static_cast<uint8_t*>(occ) + 0x38);
				Logger::Get().WriteLine(LogLevel::Info,
					"CodePatches: OFFERBOX #%ld min=(%d.%02d, %d.%02d, "
					"%d.%02d) max=(%d.%02d, %d.%02d, %d.%02d) "
					"extent=(%d.%02d x %d.%02d x %d.%02d).",
					gSpTargetCalls,
					static_cast<int>(b[0]),
					static_cast<int>((b[0] - static_cast<int>(b[0])) * 100),
					static_cast<int>(b[1]),
					static_cast<int>((b[1] - static_cast<int>(b[1])) * 100),
					static_cast<int>(b[2]),
					static_cast<int>((b[2] - static_cast<int>(b[2])) * 100),
					static_cast<int>(b[3]),
					static_cast<int>((b[3] - static_cast<int>(b[3])) * 100),
					static_cast<int>(b[4]),
					static_cast<int>((b[4] - static_cast<int>(b[4])) * 100),
					static_cast<int>(b[5]),
					static_cast<int>((b[5] - static_cast<int>(b[5])) * 100),
					static_cast<int>(b[3] - b[0]),
					static_cast<int>(((b[3] - b[0])
						- static_cast<int>(b[3] - b[0])) * 100),
					static_cast<int>(b[4] - b[1]),
					static_cast<int>(((b[4] - b[1])
						- static_cast<int>(b[4] - b[1])) * 100),
					static_cast<int>(b[5] - b[2]),
					static_cast<int>(((b[5] - b[2])
						- static_cast<int>(b[5] - b[2])) * 100));
			}
			__except (EXCEPTION_EXECUTE_HANDLER)
			{
				Logger::Get().WriteLine(LogLevel::Info,
					"CodePatches: OFFERBOX #%ld faulted reading %p+0x38.",
					gSpTargetCalls, occ);
			}
		}
		__declspec(naked) void SpTargetDetour()
		{
			__asm {
				pushad
				pushfd
				mov eax, [esp + 40]
				push eax
				push ecx
				call SpTargetLog
				popfd
				popad
				jmp dword ptr [gSpTargetTramp]
			}
		}

		// The mayor-view hover HANDLER 0x4D7950 - byte-verified this
		// session and PROVEN LIVE (it is the code that stores the picked
		// marker into [this+0x2C] and applies the 0.7f hover highlight via
		// QI 0x2B3B7D86 vt+0x28). Hovering the balloon executes it by
		// construction. The hook interrogates the incoming object: GetType
		// (vt+0x1C, __thiscall no-arg - the handler's own call shape), and
		// for marker type 0xCB79919B, QI 0x2B3B7D86 to obtain the DRAWABLE
		// and log ITS vtable - the balloon's visual class names itself on
		// a guaranteed-live path. QI AddRefs; we Release (vt+8) exactly as
		// the handler itself does.
		void* gSpHoverTramp = nullptr;
		volatile LONG gSpHoverCalls = 0;
		int gSpHoverLogs = 0;
		const uintptr_t kSpHoverVa = 0x4D7950;
		const uint8_t kSpHoverStock[8] =
			{ 0x51, 0x55, 0x56, 0x8B, 0xF1, 0x8B, 0x4E, 0x2C };

		// The offer PROXY's two outbound links ([+0x30] owner, [+0x38]
		// companion) hide the balloon's drawer one pointer away. Its
		// getter slots (+0x4C = 0x6AAC50 `mov eax,[ecx+0x30]; ret`, +0x98
		// = 0x80BC00 `mov eax,[ecx+0x38]; ret` - byte-verified 4-byte
		// bodies, too short for MinHook) are replaced by VTABLE-SLOT SWAP
		// with logging reimplementations. Any caller that fires EVERY
		// FRAME while the balloons idle on screen IS the draw path - its
		// return address lands us inside the true drawer. Distinct-caller
		// dedupe, 12 each; the linked object's vtable is logged too.
		struct SpCallerSlot { uint32_t ret; uint32_t cnt; };
		SpCallerSlot gSpGet30[12];
		SpCallerSlot gSpGet38[12];
		int gSpGet30N = 0;
		int gSpGet38N = 0;

		void __stdcall SpGetterLog(uint32_t which, void* self, void* retaddr)
		{
			SpCallerSlot* tab = which ? gSpGet38 : gSpGet30;
			int* n = which ? &gSpGet38N : &gSpGet30N;
			const uintptr_t base =
				reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
			const uint32_t retVa = static_cast<uint32_t>(
				reinterpret_cast<uintptr_t>(retaddr) - base + kImageBase);
			for (int k = 0; k < *n; ++k)
			{
				if (tab[k].ret == retVa) { ++tab[k].cnt; return; }
			}
			if (*n >= 12) { return; }
			tab[*n].ret = retVa;
			tab[*n].cnt = 1;
			++*n;
			// CRASH FIX 2026-08-18. Both reads below are speculative: `self`
			// is whatever ECX held at a swapped vtable slot, and the field at
			// +0x30/+0x38 is a GUESS about that object's layout. `if (linked)`
			// only proves the field is non-zero; it says nothing about whether
			// it is a valid pointer. Placing a power plant reached this getter
			// with a self whose +0x38 held 0xC9FBC2CD, and the deref took the
			// game down with an ACCESS_VIOLATION inside our own DLL (two
			// exception reports, identical EIP 0x01:0x00028a29, ECX=0x38,
			// ESI=0). A probe that can kill the process is worse than no
			// probe: it destroys the very session it was meant to observe.
			// Both dereferences are now guarded, and a failure is REPORTED
			// rather than swallowed (law 54: a silent probe cannot be told
			// apart from one that never ran).
			void* linked = nullptr;
			uint32_t linkVt = 0;
			bool selfBad = false;
			bool linkBad = false;
			__try
			{
				linked = *reinterpret_cast<void**>(
					static_cast<uint8_t*>(self) + (which ? 0x38 : 0x30));
			}
			__except (EXCEPTION_EXECUTE_HANDLER) { selfBad = true; }
			if (linked && !selfBad)
			{
				__try
				{
					linkVt = static_cast<uint32_t>(
						*reinterpret_cast<uintptr_t*>(linked) - base + kImageBase);
				}
				__except (EXCEPTION_EXECUTE_HANDLER) { linkBad = true; }
			}
			if (selfBad || linkBad)
			{
				Logger::Get().WriteLine(LogLevel::Info,
					"CodePatches: PROXYGET%s caller 0x%08X - %s NOT READABLE "
					"(self=%p linked=%p). Probe survived; the layout guess at "
					"+0x%02X is wrong for this object.",
					which ? "38" : "30", retVa,
					selfBad ? "self field" : "linked vtable",
					self, linked, which ? 0x38 : 0x30);
				return;
			}
			Logger::Get().WriteLine(LogLevel::Info,
				"CodePatches: PROXYGET%s caller 0x%08X linked=%p linkVt=0x%08X.",
				which ? "38" : "30", retVa, linked, linkVt);
		}
		__declspec(naked) void SpGet30Detour()
		{
			__asm {
				pushad
				pushfd
				mov eax, [esp + 36]
				push eax
				push ecx
				push 0
				call SpGetterLog
				popfd
				popad
				mov eax, [ecx + 0x30]
				ret
			}
		}
		__declspec(naked) void SpGet38Detour()
		{
			__asm {
				pushad
				pushfd
				mov eax, [esp + 36]
				push eax
				push ecx
				push 1
				call SpGetterLog
				popfd
				popad
				mov eax, [ecx + 0x38]
				ret
			}
		}

		void InstallProxyGetterProbe()
		{
			const uintptr_t base =
				reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
			const uintptr_t delta = base - kImageBase;
			// vtable 0xA87238 (the captured iface vtable): slot +0x4C must
			// hold 0x6AAC50, +0x98 must hold 0x80BC00 - verify both, swap
			// both or neither.
			uintptr_t* s30 = reinterpret_cast<uintptr_t*>(0xA87238 + 0x4C + delta);
			uintptr_t* s38 = reinterpret_cast<uintptr_t*>(0xA87238 + 0x98 + delta);
			if (*s30 != 0x6AAC50 + delta || *s38 != 0x80BC00 + delta)
			{
				Logger::Get().WriteLine(LogLevel::Info,
					"CodePatches: PROXYGET slots unexpected (0x%08X/0x%08X) - "
					"not installed.",
					static_cast<uint32_t>(*s30 - delta),
					static_cast<uint32_t>(*s38 - delta));
				return;
			}
			DWORD oldProt = 0;
			// one span covers both slots (+0x4C..+0x9C within one page)
			uint8_t* lo = reinterpret_cast<uint8_t*>(s30);
			const SIZE_T span = static_cast<SIZE_T>(
				reinterpret_cast<uint8_t*>(s38) + 4 - lo);
			if (!VirtualProtect(lo, span, PAGE_READWRITE, &oldProt))
			{
				Logger::Get().WriteLine(LogLevel::Info,
					"CodePatches: PROXYGET VirtualProtect failed - not installed.");
				return;
			}
			*s30 = reinterpret_cast<uintptr_t>(&SpGet30Detour);
			*s38 = reinterpret_cast<uintptr_t>(&SpGet38Detour);
			VirtualProtect(lo, span, oldProt, &oldProt);
			Logger::Get().WriteLine(LogLevel::Info,
				"CodePatches: PROXYGET armed (vtable 0xA87238 slots +0x4C/+0x98 "
				"swapped). Idle with balloons on screen; per-frame callers "
				"name the drawer.");
		}

		// The PROP BINDER 0x496950 (live band; gates GetType==0xA823821E,
		// reads exemplar property 0x2977AA47): where offers attach to the
		// REAL prop occupant - the balloon. Hooking it logs the prop's
		// pointer + vtable at city load; from that class the exemplar key
		// (the balloon's data identity) is one static read, and the fix
		// becomes tier-scaled S3D overrides - pure data.
		void* gSpBindTramp = nullptr;
		volatile LONG gSpBindCalls = 0;
		int gSpBindLogs = 0;
		const uintptr_t kSpBindVa = 0x496950;
		const uint8_t kSpBindStock[9] =
			{ 0x83, 0xEC, 0x0C, 0x53, 0x56, 0x8B, 0x74, 0x24, 0x18 };

		// ---- #188 MARKERSIZE: the marker's OWN per-object size ------------
		// Found 2026-08-17 by decoding vt0 (0xAA4900) end to end. Slot 13
		// (0x5ED400) is SetSize(float,float): each arg `fmul [0xA94D50]`
		// (=10.0f) -> ftol -> `mov [this+0x5E], al` / `[this+0x5F], al`.
		// Slot 14 (0x5ECA10) is GetSize: those two bytes `fild` x [0xA8C950]
		// (=0.1f) -> out floats. So the marker carries a per-object size in
		// TENTHS of a world unit, and the byte encoding CAPS it at 25.5.
		//
		// THE POINTER THE BINDER HANDS US IS NOT THE OBJECT BASE. Anchored
		// three ways in the live 190644 capture: the ctor's default +0x62=100
		// appears at occ+0x5A in all 12 markers; the ctor's 0xA823821E at
		// +0x2C appears at occ+0x24; and occ+96 holds 0x00AA4900 because the
		// markers sit 0x68 apart in one array and that is the NEXT object's
		// vt0. All three give the same answer: base = occ - 8 (occ is the
		// embedded occupant sub-object). Marker #1 read 0x96/0x5A there =
		// 15.0 x 9.0 world units.
		//
		// We call the game's OWN getter/setter through the object's vtable
		// rather than poking the bytes: no offset arithmetic can be wrong,
		// and any subclass override is honoured. Gate on vt0 == 0xAA4900 -
		// the condition this whole decode depends on (law: gate on the
		// condition you depend on).
		typedef void (__thiscall *MarkerGetSizeFn)(void*, float*, float*);
		typedef void (__thiscall *MarkerSetSizeFn)(void*, float, float);
		const uint32_t kMarkerVt0Va = 0xAA4900;
		const float kMarkerSizeMax = 25.5f;  // 255 tenths - the byte cap
		int gMarkerSizeHits = 0;
		int gMarkerSizeLogs = 0;   // LOG budget only - never gates the work

		// ⛔ WRITES DISABLED 2026-08-17 (v3.0.26) - THIS HUNG THE GAME.
		// v3.0.25 called the marker's own SetSize to push 15.0x9.0 up to the
		// 25.5 byte cap. The size is not cosmetic: an occupant is registered
		// with the view's occupant manager by its extent, so inflating it to
		// 25.5 world units (vs a 16 m cell) makes each marker span many more
		// cells and the per-cycle occupant enumeration - the hot vt1+0x64
		// traffic VTCAP measured at 128 calls/cycle - grows with it. The
		// user's game hung on the next run. Reverted to LOG-ONLY: the
		// measurement was the valuable half anyway, and it is what identifies
		// which marker is the balloon.
		//
		// LAW: a "size" field on a world object is also a SPATIAL INDEX key.
		// Changing it changes how much work the engine does every cycle, not
		// just how big something looks. Never inflate one to probe a visual.
		const bool kMarkerSizeWriteEnabled = false;

		// ---- #188 MARKERID: name every marker, WITHOUT touching it ---------
		// The v3.0.25 lesson: we scaled 3 markers that were probably not
		// balloons because we had no way to tell them apart, and the write
		// hung the game. This is the instrument that was missing, and it is
		// READ-ONLY by construction - it cannot hang or corrupt anything.
		//
		// A marker's identity is a resource key on the sub-object at obj+0x28:
		// dwords +0x10/+0x14/+0x18 = {type, group, instance}. The live capture
		// reads {0x6534284A, 0xC977C536, 0x1E680000} for marker #1, and the
		// sibling family's exemplar (neighbour-connection arrows) is
		// {0x6534284A, 0xC977C536, 0x29F10000} named "UI8x1x3_ConnectArrow_29F1"
		// - so the INSTANCE dword names the object, and the exemplar census
		// turns that number into a name. RAW HEX only: the PROPBIND dump's
		// float coercion silently ate the size bytes once already.
		void MarkerIdLog(void* occ)
		{
			if (gMarkerSizeLogs >= 20) { return; }
			uint8_t* obj = static_cast<uint8_t*>(occ) - 8;
			__try
			{
				const uint32_t* sub =
					*reinterpret_cast<const uint32_t**>(obj + 0x28);
				uint32_t t = 0, g = 0, i = 0;
				if (reinterpret_cast<uintptr_t>(sub) > 0x10000)
				{
					t = sub[4]; g = sub[5]; i = sub[6];
				}
				const uint8_t w = obj[0x5E];
				const uint8_t h = obj[0x5F];
				const float* pos = reinterpret_cast<const float*>(obj + 0x3C);
				Logger::Get().WriteLine(LogLevel::Info,
					"CodePatches: MARKERID obj=%p exemplar={0x%08X,0x%08X,"
					"0x%08X} sizeBytes=%u/%u (%d.%d x %d.%d) pos=(%d,%d,%d).",
					obj, t, g, i, w, h, w / 10, w % 10, h / 10, h % 10,
					static_cast<int>(pos[0]), static_cast<int>(pos[1]),
					static_cast<int>(pos[2]));
			}
			__except (EXCEPTION_EXECUTE_HANDLER)
			{
				Logger::Get().WriteLine(LogLevel::Info,
					"CodePatches: MARKERID faulted on %p.", occ);
			}
		}

		void MarkerSizeApply(void* occ, float scale)
		{
			MarkerIdLog(occ);
			const bool say = (gMarkerSizeLogs < 20);
			if (say) { ++gMarkerSizeLogs; }
			uint8_t* obj = static_cast<uint8_t*>(occ) - 8;
			const uintptr_t base =
				reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
			__try
			{
				void** vt0 = *reinterpret_cast<void***>(obj);
				const uint32_t vt0Va = static_cast<uint32_t>(
					reinterpret_cast<uintptr_t>(vt0) - base + kImageBase);
				if (vt0Va != kMarkerVt0Va)
				{
					if (say)
					{
						Logger::Get().WriteLine(LogLevel::Info,
							"CodePatches: MARKERSIZE #%ld obj=%p vt0=0x%08X != "
							"0x00AA4900 - not the decoded class, skipped.",
							gSpBindCalls, obj, vt0Va);
					}
					return;
				}
				float w = 0.0f, h = 0.0f;
				reinterpret_cast<MarkerGetSizeFn>(vt0[14])(obj, &w, &h);
				// A zero size is the class default (never sized) - scaling 0
				// is still 0, so say so instead of pretending we acted.
				if (!(w > 0.01f) && !(h > 0.01f))
				{
					if (say)
					{
						Logger::Get().WriteLine(LogLevel::Info,
							"CodePatches: MARKERSIZE #%ld obj=%p size=0x0 "
							"(never sized) - nothing to scale.",
							gSpBindCalls, obj);
					}
					return;
				}
				if (!kMarkerSizeWriteEnabled || !(scale > 1.01f))
				{
					if (say)
					{
					Logger::Get().WriteLine(LogLevel::Info,
						"CodePatches: MARKERSIZE #%ld obj=%p size=%d.%02d x "
						"%d.%02d - log only.", gSpBindCalls, obj,
						static_cast<int>(w),
						static_cast<int>((w - static_cast<int>(w)) * 100.0f),
						static_cast<int>(h),
						static_cast<int>((h - static_cast<int>(h)) * 100.0f));
					}
					return;
				}
				float nw = w * scale;
				float nh = h * scale;
				const bool clamped = (nw > kMarkerSizeMax)
					|| (nh > kMarkerSizeMax);
				if (nw > kMarkerSizeMax) { nw = kMarkerSizeMax; }
				if (nh > kMarkerSizeMax) { nh = kMarkerSizeMax; }
				reinterpret_cast<MarkerSetSizeFn>(vt0[13])(obj, nw, nh);
				// Read BACK through the getter: the byte quantisation is the
				// game's, so only a re-read proves what actually landed.
				float rw = 0.0f, rh = 0.0f;
				reinterpret_cast<MarkerGetSizeFn>(vt0[14])(obj, &rw, &rh);
				++gMarkerSizeHits;
				Logger::Get().WriteLine(LogLevel::Info,
					"CodePatches: MARKERSIZE #%ld obj=%p %d.%02d x %d.%02d -> "
					"%d.%02d x %d.%02d (x%d.%02d%s).", gSpBindCalls, obj,
					static_cast<int>(w),
					static_cast<int>((w - static_cast<int>(w)) * 100.0f),
					static_cast<int>(h),
					static_cast<int>((h - static_cast<int>(h)) * 100.0f),
					static_cast<int>(rw),
					static_cast<int>((rw - static_cast<int>(rw)) * 100.0f),
					static_cast<int>(rh),
					static_cast<int>((rh - static_cast<int>(rh)) * 100.0f),
					static_cast<int>(scale),
					static_cast<int>((scale - static_cast<int>(scale)) * 100.0f),
					clamped ? ", CLAMPED at the 25.5 byte cap" : "");
			}
			__except (EXCEPTION_EXECUTE_HANDLER)
			{
				Logger::Get().WriteLine(LogLevel::Info,
					"CodePatches: MARKERSIZE #%ld faulted on %p - skipped.",
					gSpBindCalls, occ);
			}
		}

		void __stdcall SpBindLog(void* occ)
		{
			InterlockedIncrement(&gSpBindCalls);
			if (!occ) { return; }
			// THE FIX RUNS FOR EVERY BOUND MARKER, not just the logged ones:
			// the 12-line dump cap is a LOG budget, and gating a cure on a
			// log budget is how a fix silently covers only the first N (the
			// census-cap law, learned the hard way on BUBBLEALL). Its own
			// lines are capped separately inside.
			if (gMarkerSizeHits < 24) { MarkerSizeApply(occ, gBubbleScale); }
			if (gSpBindLogs >= 12) { return; }
			++gSpBindLogs;
			const uintptr_t base =
				reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
			uint32_t vtVa = 0;
			uint32_t type = 0;
			__try
			{
				void** vt = *reinterpret_cast<void***>(occ);
				vtVa = static_cast<uint32_t>(
					reinterpret_cast<uintptr_t>(vt) - base + kImageBase);
				type = reinterpret_cast<ObjGetTypeFn>(vt[0x1C / 4])(occ);
			}
			__except (EXCEPTION_EXECUTE_HANDLER)
			{
				vtVa = 0xBADBADBA;
			}
			// FIELD DUMP: the balloon is an OCCUPANT batched into the world
			// render (12 eliminations proved no dedicated drawer exists,
			// and the class's only per-cycle traffic is QI/AddRef/validity/
			// Release = enumeration). An occupant's on-screen size lives in
			// its own fields: model key (a TGI triple) and/or scale/bounds
			// floats. Object is 0x68 bytes = 26 dwords; dump all of them,
			// float-decoding plausible values.
			char line[640];
			int used = 0;
			line[0] = 0;
			__try
			{
				const uint32_t* w = static_cast<const uint32_t*>(occ);
				static const char kHex[] = "0123456789ABCDEF";
				for (int k = 0; k < 26 && used < 560; ++k)
				{
					const uint32_t v = w[k];
					float f = 0.0f;
					memcpy(&f, &v, 4);
					const bool plaus = (f > 0.001f && f < 100000.0f)
						|| (f < -0.001f && f > -100000.0f);
					line[used++] = ' ';
					used += wsprintfA(line + used, "%d:", k * 4);
					if (plaus)
					{
						const int whole = static_cast<int>(f);
						int frac = static_cast<int>((f - whole) * 100.0f);
						if (frac < 0) { frac = -frac; }
						used += wsprintfA(line + used, "%d.%02df", whole, frac);
					}
					else
					{
						for (int s = 28; s >= 0; s -= 4)
						{
							line[used++] = kHex[(v >> s) & 0xF];
						}
						line[used] = 0;
					}
				}
			}
			__except (EXCEPTION_EXECUTE_HANDLER)
			{
				used += wsprintfA(line + used, " <fault>");
			}
			Logger::Get().WriteLine(LogLevel::Info,
				"CodePatches: PROPBIND #%ld occ=%p vt=0x%08X type=0x%08X"
				" |%s.", gSpBindCalls, occ, vtVa, type, line);

			// The occupant's AABB (fields 52..72) is world geometry, but
			// the DRAWN size comes from its model instance's transform -
			// behind one of the two object pointers at +0x20 and +0x30.
			// Dump both (vtable + 16 dwords, floats decoded): a transform
			// shows up unmistakably as an identity-ish 3x3 + translation.
			const uint32_t* occw = static_cast<const uint32_t*>(occ);
			for (int which = 0; which < 2; ++which)
			{
				const uint32_t ptr = occw[which == 0 ? 8 : 12];
				if (ptr < 0x10000) { continue; }
				char sub[440];
				int su = 0;
				sub[0] = 0;
				uint32_t svt = 0;
				__try
				{
					const uint32_t* p =
						reinterpret_cast<const uint32_t*>(ptr);
					svt = static_cast<uint32_t>(p[0] - base + kImageBase);
					static const char kHex2[] = "0123456789ABCDEF";
					for (int k = 0; k < 16 && su < 380; ++k)
					{
						const uint32_t v = p[k];
						float f = 0.0f;
						memcpy(&f, &v, 4);
						const bool pl = (f > 0.001f && f < 100000.0f)
							|| (f < -0.001f && f > -100000.0f);
						sub[su++] = ' ';
						su += wsprintfA(sub + su, "%d:", k * 4);
						if (pl)
						{
							const int wh = static_cast<int>(f);
							int fr = static_cast<int>((f - wh) * 100.0f);
							if (fr < 0) { fr = -fr; }
							su += wsprintfA(sub + su, "%d.%02df", wh, fr);
						}
						else
						{
							for (int s = 28; s >= 0; s -= 4)
							{
								sub[su++] = kHex2[(v >> s) & 0xF];
							}
							sub[su] = 0;
						}
					}
				}
				__except (EXCEPTION_EXECUTE_HANDLER)
				{
					su += wsprintfA(sub + su, " <fault>");
				}
				Logger::Get().WriteLine(LogLevel::Info,
					"CodePatches: PROPSUB #%ld p%d=0x%08X vt=0x%08X |%s.",
					gSpBindCalls, which == 0 ? 32 : 48, ptr, svt, sub);
			}
		}
		__declspec(naked) void SpBindDetour()
		{
			__asm {
				pushad
				pushfd
				mov eax, [esp + 40]
				push eax
				call SpBindLog
				popfd
				popad
				jmp dword ptr [gSpBindTramp]
			}
		}

		// ---- #188 VTCAP: per-slot capture on the CAPTURED balloon class -
		// vtables 0xAA4900 (main) + 0xAA4868 (iface). Every slot is
		// replaced by a runtime-emitted 25-byte thunk that logs (slot,
		// caller) then jumps to the original impl. The per-frame slot IS
		// the draw path; its impl + caller close builder and sizer. A
		// one-shot summary at 300 total calls prints per-slot counts.
		struct VtCapPair { uint32_t key; uint32_t ret; };
		VtCapPair gVtSeen[96];
		int gVtSeenN = 0;
		uint32_t gVtCounts[6][64];
		volatile LONG gVtTotal = 0;
		void* gVtOrig[6][64];
		bool gVtSummary = false;

		void __stdcall SpVtHit(uint32_t key, void* retaddr, uint32_t arg1)
		{
			const LONG total = InterlockedIncrement(&gVtTotal);
			const uint32_t vtIdx = key >> 8;
			const uint32_t slot = key & 0xFF;
			if (vtIdx < 6 && slot < 64) { ++gVtCounts[vtIdx][slot]; }
			const uintptr_t base =
				reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
			const uint32_t retVa = static_cast<uint32_t>(
				reinterpret_cast<uintptr_t>(retaddr) - base + kImageBase);
			bool known = false;
			for (int k = 0; k < gVtSeenN; ++k)
			{
				if (gVtSeen[k].key == key && gVtSeen[k].ret == retVa)
				{
					known = true; break;
				}
			}
			if (!known && gVtSeenN < 96)
			{
				gVtSeen[gVtSeenN].key = key;
				gVtSeen[gVtSeenN].ret = retVa;
				++gVtSeenN;
				// For QI (slot 0) arg1 is the requested IID - the datum
				// that names WHICH interface the renderer wants.
				Logger::Get().WriteLine(LogLevel::Info,
					"CodePatches: VTCAP vt%u slot=+0x%02X caller=0x%08X "
					"arg1=0x%08X.", vtIdx, slot * 4, retVa, arg1);
			}
			if (total == 900 && !gVtSummary)
			{
				gVtSummary = true;
				for (int v = 0; v < 6; ++v)
				{
					for (int s = 0; s < 64; ++s)
					{
						if (gVtCounts[v][s] > 10)
						{
							Logger::Get().WriteLine(LogLevel::Info,
								"CodePatches: VTCAP-HOT vt%d slot=+0x%02X "
								"count=%u.", v, s * 4, gVtCounts[v][s]);
						}
					}
				}
			}
		}

		void InstallVtCap()
		{
			const uintptr_t base =
				reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
			const uintptr_t delta = base - kImageBase;
			// ALL SIX family vtables (ctor 0x5EE050 writes them): the
			// renderer's 75x/cycle QI (caller 0x90E00D) returns one of the
			// four previously-unthunked subs - the draw path runs there.
			const uintptr_t vts[6] = { 0xAA4900, 0xAA4868, 0xAA48F0,
				0xAA484C, 0xAA47E8, 0xAA47D0 };
			const uintptr_t txtLo = base + 0x1000, txtHi = base + 0xA20000;
			uint8_t* pool = static_cast<uint8_t*>(VirtualAlloc(nullptr,
				16384, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE));
			if (!pool)
			{
				Logger::Get().WriteLine(LogLevel::Info,
					"CodePatches: VTCAP pool alloc failed - not installed.");
				return;
			}
			// The six vtables are ADJACENT in .rdata; bound each slot-walk
			// by the nearest OTHER table start so a long table never
			// overruns into (and re-thunks) its neighbor (v3.0.18 vt2 was
			// lost this way - vt1's 38-slot walk ran through it).
			int emitted = 0;
			for (int v = 0; v < 6; ++v)
			{
				uintptr_t va = vts[v] + delta;
				uintptr_t nextTbl = va + 64 * 4;
				for (int u = 0; u < 6; ++u)
				{
					const uintptr_t o = vts[u] + delta;
					if (o > va && o < nextTbl) { nextTbl = o; }
				}
				const int maxN = static_cast<int>((nextTbl - va) / 4);
				uintptr_t* vt = reinterpret_cast<uintptr_t*>(va);
				int n = 0;
				while (n < maxN && vt[n] >= txtLo && vt[n] < txtHi) { ++n; }
				DWORD oldProt = 0;
				if (!VirtualProtect(vt, n * 4, PAGE_READWRITE, &oldProt))
				{
					continue;
				}
				for (int s = 0; s < n; ++s)
				{
					gVtOrig[v][s] = reinterpret_cast<void*>(vt[s]);
					uint8_t* t = pool + emitted * 30;
					// pushad; pushfd; mov eax,[esp+40](arg1); push eax;
					// mov eax,[esp+40](ret, esp moved); push eax;
					// push key; call SpVtHit(3); popfd; popad; jmp [orig]
					t[0] = 0x60; t[1] = 0x9C;
					t[2] = 0x8B; t[3] = 0x44; t[4] = 0x24; t[5] = 0x28;
					t[6] = 0x50;
					t[7] = 0x8B; t[8] = 0x44; t[9] = 0x24; t[10] = 0x28;
					t[11] = 0x50;
					t[12] = 0x68;
					const uint32_t key = (static_cast<uint32_t>(v) << 8)
						| static_cast<uint32_t>(s);
					memcpy(t + 13, &key, 4);
					t[17] = 0xE8;
					const int32_t rel = static_cast<int32_t>(
						reinterpret_cast<uintptr_t>(&SpVtHit)
						- reinterpret_cast<uintptr_t>(t + 17) - 5);
					memcpy(t + 18, &rel, 4);
					t[22] = 0x9D; t[23] = 0x61;
					t[24] = 0xFF; t[25] = 0x25;
					const uintptr_t slotAddr =
						reinterpret_cast<uintptr_t>(&gVtOrig[v][s]);
					memcpy(t + 26, &slotAddr, 4);
					vt[s] = reinterpret_cast<uintptr_t>(t);
					++emitted;
				}
				VirtualProtect(vt, n * 4, oldProt, &oldProt);
				Logger::Get().WriteLine(LogLevel::Info,
					"CodePatches: VTCAP vt%d (0x%08X) %d slots thunked.",
					v, static_cast<uint32_t>(vts[v]), n);
			}
			FlushInstructionCache(GetCurrentProcess(), pool, 16384);
		}

		// ---- #188 DRAWCAP: the drawable's DRAW FORWARDER 0x5FD2D0 --------
		// vt4(0xAA47E8)+0x18. Byte-verified: mov edx,[esp+4]; mov eax,[ecx];
		// push edx; call [eax+0x24] (get render target); test/je; call
		// [edx+0x14] ... - it inserts this object into the render context.
		// Hooked DIRECTLY (not via vtable) so it catches the balloon no
		// matter which instance/vtable draws it. Logs call counts + the
		// object's first 16 dwords, decoded as floats where plausible -
		// the balloon's live geometry (its SIZE) is in those fields.
		void* gDrawTramp = nullptr;
		volatile LONG gDrawCalls = 0;
		int gDrawLogs = 0;
		const uintptr_t kDrawVa = 0x5FD2D0;
		const uint8_t kDrawStock[6] =
			{ 0x8B, 0x54, 0x24, 0x04, 0x8B, 0x01 };

		void __stdcall SpDrawLog(void* self)
		{
			const LONG n = InterlockedIncrement(&gDrawCalls);
			// log the first few, then one sample every 512 calls
			if (!(n <= 6 || (n % 512) == 0) || gDrawLogs >= 14) { return; }
			++gDrawLogs;
			const uintptr_t base =
				reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
			char line[400];
			int used = 0;
			line[0] = 0;
			__try
			{
				const uint32_t* w = static_cast<const uint32_t*>(self);
				static const char kHex[] = "0123456789ABCDEF";
				for (int k = 0; k < 16 && used < 340; ++k)
				{
					const uint32_t v = w[k];
					float f = 0.0f;
					memcpy(&f, &v, 4);
					const bool plausible = (f > 0.0009f && f < 100000.0f)
						|| (f < -0.0009f && f > -100000.0f);
					line[used++] = ' ';
					if (plausible)
					{
						// print as float with 2 decimals via integer math
						const int whole = static_cast<int>(f);
						int frac = static_cast<int>((f - whole) * 100.0f);
						if (frac < 0) { frac = -frac; }
						used += wsprintfA(line + used, "%d.%02d", whole, frac);
					}
					else
					{
						for (int s = 28; s >= 0; s -= 4)
						{
							line[used++] = kHex[(v >> s) & 0xF];
						}
					}
					line[used] = 0;
				}
			}
			__except (EXCEPTION_EXECUTE_HANDLER)
			{
				used += wsprintfA(line + used, " <fault>");
			}
			const uint32_t vtVa = static_cast<uint32_t>(
				*reinterpret_cast<uintptr_t*>(self) - base + kImageBase);
			Logger::Get().WriteLine(LogLevel::Info,
				"CodePatches: DRAWCAP #%ld this=%p vt=0x%08X f:%s.",
				n, self, vtVa, line);
		}
		__declspec(naked) void SpDrawDetour()
		{
			__asm {
				pushad
				pushfd
				push ecx
				call SpDrawLog
				popfd
				popad
				jmp dword ptr [gDrawTramp]
			}
		}

		void __stdcall SpHoverLog(void* self, void* obj)
		{
			InterlockedIncrement(&gSpHoverCalls);
			if (gSpHoverLogs >= 20 || !obj) { return; }
			++gSpHoverLogs;
			const uintptr_t base =
				reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
			void** vt = *reinterpret_cast<void***>(obj);
			const uint32_t vtVa = static_cast<uint32_t>(
				reinterpret_cast<uintptr_t>(vt) - base + kImageBase);
			const uint32_t type =
				reinterpret_cast<ObjGetTypeFn>(vt[0x1C / 4])(obj);
			uint32_t drawVtVa = 0;
			void* draw = nullptr;
			if (type == 0xCB79919B || type == 0xAB72FBB3)
			{
				if (reinterpret_cast<ObjQiFn>(vt[0])(obj, 0x2B3B7D86, &draw)
					&& draw)
				{
					void** dvt = *reinterpret_cast<void***>(draw);
					drawVtVa = static_cast<uint32_t>(
						reinterpret_cast<uintptr_t>(dvt) - base + kImageBase);
					reinterpret_cast<ObjRelFn>(dvt[2])(draw);
				}
			}
			Logger::Get().WriteLine(LogLevel::Info,
				"CodePatches: SPHOVER #%ld obj=%p vt=0x%08X type=0x%08X "
				"drawVt=0x%08X.", gSpHoverCalls, obj, vtVa, type, drawVtVa);
		}
		__declspec(naked) void SpHoverDetour()
		{
			__asm {
				pushad
				pushfd
				mov eax, [esp + 40]
				push eax
				push ecx
				call SpHoverLog
				popfd
				popad
				jmp dword ptr [gSpHoverTramp]
			}
		}

		void __stdcall SpQuadLog(void* self)
		{
			InterlockedIncrement(&gSpQuadCalls);
			if (gSpQuadLogs >= 24) { return; }
			++gSpQuadLogs;
			const uint32_t kind = self
				? *reinterpret_cast<const uint32_t*>(
					static_cast<const uint8_t*>(self) + 0x70)
				: 0xFFFFFFFFu;
			const uintptr_t base =
				reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
			float imm = 0.0f;
			memcpy(&imm, reinterpret_cast<const void*>(
				base - kImageBase + kSignpostSizeSite + 1), 4);
			Logger::Get().WriteLine(LogLevel::Info,
				"CodePatches: SPQUAD #%ld this=%p kind=%u imm=%.1f.",
				gSpQuadCalls, self, kind, static_cast<double>(imm));
		}
		__declspec(naked) void SpQuadDetour()
		{
			__asm {
				pushad
				pushfd
				push ecx
				call SpQuadLog
				popfd
				popad
				jmp dword ptr [gSpQuadTramp]
			}
		}
		void __stdcall SpTexLog(void* self)
		{
			InterlockedIncrement(&gSpTexCalls);
			if (gSpTexLogs >= 24) { return; }
			++gSpTexLogs;
			const uint32_t kind = self
				? *reinterpret_cast<const uint32_t*>(
					static_cast<const uint8_t*>(self) + 0x70)
				: 0xFFFFFFFFu;
			Logger::Get().WriteLine(LogLevel::Info,
				"CodePatches: SPTEX #%ld this=%p kind=%u.",
				gSpTexCalls, self, kind);
		}
		__declspec(naked) void SpTexDetour()
		{
			__asm {
				pushad
				pushfd
				push ecx
				call SpTexLog
				popfd
				popad
				jmp dword ptr [gSpTexTramp]
			}
		}

		// ---- #188 ARTFETCH: name the balloon's OWN two art resources -------
		// The signpost composer fetches its two sheets through ONE helper,
		// 0x602B70(type, group, instance, flags), and BOTH instances are
		// VARIABLES, not the constants v3.0.23 guessed (byte-proof):
		//   0x5F12E8  push ecx                 ; FRAME instance <- variable
		//   0x5F12E9  push 0xAB7E5421          ; frame group
		//   0x5F12EE  push 0x856DDBAC          ; type
		//   0x5F12FB  call 0x602B70            ; -> ret 0x005F1300
		//   0x5F1327  mov eax,[ebx+0x1A8]      ; ICON instance  <- variable
		//   0x5F1339  push 0x46A006B0          ; icon group
		//   0x5F134A  call 0x602B70            ; -> ret 0x005F134F
		// That single fact explains BOTH v3.0.23 outcomes at once: shipping
		// 2x art for the two frames we happened to have (2BB075B4/2BB06F3F)
		// moved the MAYOR-HAT balloon (and misaligned its glyph, because the
		// icon sheet was not scaled with it) while the U-Drive-It offer discs
		// never changed - they simply use different instances.
		//
		// Hooking the shared FETCH rather than the composer avoids the trap
		// that made SPQUAD/SPTEX read zero: those sat on 0x5F20A0/0x5F1610,
		// two functions this path never calls. Read-only; logs the caller so
		// frame vs icon is unambiguous.
		void* gArtFetchTramp = nullptr;
		int gArtFetchLogs = 0;
		int gCsiFetchCount = 0;
		const uintptr_t kArtFetchVa = 0x602B70;

		void __stdcall ArtFetchLog(uint32_t ret, uint32_t t, uint32_t g,
			uint32_t inst)
		{
			// ⛔ FILTER ON THE RESOURCE, NEVER ON THE CALLER. The first cut of
			// this probe gated on `ret` being inside 0x5F1000-0x5F2200 (the
			// composer we had disassembled) and logged ZERO fetches - the
			// same FILTERED NULL that cost this project months on BUBBLEFX.
			// A caller filter can only ever confirm the caller you already
			// suspected; it is structurally blind to the one you are looking
			// for. The signpost art groups are the thing we actually care
			// about, so key on them and let the caller be the DISCOVERY.
			// Two INDEPENDENT channels, so neither can hide the other:
			//   (a) the signpost art groups, any caller  - the resource key;
			//   (b) any caller inside the signpost module 0x5Fxxxx, any
			//       resource - catches the composer using a group we have
			//       not predicted.
			// (b) is a caller filter, but it is ADDITIVE - it can only ever
			// reveal more, never suppress (a). That is the difference
			// between a scope and a blindfold.
			const bool signpostArt = (g == 0xAB7E5421) || (g == 0x46A006B0);
			const bool signpostCode = (ret >= 0x5F0000 && ret <= 0x5FFFFF);
			// (c) THE CSI CHANNEL - the eight city-situation indicator icons
			// named by the automata scripts' `csi_image` field. UNCAPPED and
			// key-only: if the offer balloon is drawn from art at all, the
			// drawer must fetch one of these ids, and a cap must never be
			// what makes that look like a null (the BUBBLEFX lesson).
			// A silent zero here says the drawer never consults the resource
			// system, which is a DIFFERENT failure from "our override lost".
			const bool csiIcon =
				(inst == 0x4BB1305D) || (inst == 0x4BB1305E) ||
				(inst == 0x4BB1305F) || (inst == 0x4BB13060) ||
				(inst == 0x0C0305C3) || (inst == 0x0C0305C4) ||
				(inst == 0x0C0305C5) || (inst == 0x0C0305C6);
			if (csiIcon) {
				++gCsiFetchCount;
				if (gCsiFetchCount <= 12) {
					Logger::Get().WriteLine(LogLevel::Info,
						"CodePatches: CSIFETCH #%d ret=0x%08X "
						"{T=0x%08X,G=0x%08X,I=0x%08X} <== the drawer DID ask "
						"the resource system for a CSI icon.",
						gCsiFetchCount, ret, t, g, inst);
				}
				return;
			}
			if (!signpostArt && !signpostCode) { return; }
			if (gArtFetchLogs >= 64) { return; }
			++gArtFetchLogs;
			Logger::Get().WriteLine(LogLevel::Info,
				"CodePatches: ARTFETCH ret=0x%08X %s {T=0x%08X,G=0x%08X,"
				"I=0x%08X}.", ret,
				(g == 0x46A006B0) ? "ICON " : ((g == 0xAB7E5421) ? "FRAME" : "?????"),
				t, g, inst);
		}

		__declspec(naked) void ArtFetchDetour()
		{
			__asm {
				pushad
				pushfd
				mov eax, [esp + 48]     // instance (arg3)
				push eax
				mov eax, [esp + 48]     // group    (arg2)
				push eax
				mov eax, [esp + 48]     // type     (arg1)
				push eax
				mov eax, [esp + 48]     // return address
				push eax
				call ArtFetchLog
				popfd
				popad
				jmp dword ptr [gArtFetchTramp]
			}
		}

		bool gArtFetchArmed = false;

		void InstallArtFetchProbeImpl()
		{
			if (gArtFetchArmed) { return; }   // constructor + PostAppInit both call
			gArtFetchArmed = true;
			const uintptr_t base =
				reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
			void* f = reinterpret_cast<void*>(base - kImageBase + kArtFetchVa);
			const MH_STATUS init = MH_Initialize();
			if (init != MH_OK && init != MH_ERROR_ALREADY_INITIALIZED)
			{
				Logger::Get().WriteLine(LogLevel::Error,
					"CodePatches: ARTFETCH MH_Initialize failed (%d).", init);
				return;
			}
			if (MH_CreateHook(f, reinterpret_cast<void*>(&ArtFetchDetour),
					&gArtFetchTramp) != MH_OK
				|| MH_EnableHook(f) != MH_OK)
			{
				Logger::Get().WriteLine(LogLevel::Error,
					"CodePatches: ARTFETCH failed to hook 0x00602B70.");
				return;
			}
			Logger::Get().WriteLine(LogLevel::Info,
				"CodePatches: ARTFETCH armed on 0x00602B70 (logs signpost "
				"FRAME + ICON instances; band 0x5F1000-0x5F2200).");
		}

		// ---- #188 BALLOONSPRITE: measure the balloon's own sprite object ---
		// THE BALLOON HAS NO ART. Its exemplar (Tag1x1x3_Helicopter_2BF60000
		// + 24 siblings incl. MarinaUDISpawn / SeaportSpawnPoint) binds
		// ResourceKeyType0 = {0x5AD0E817,0xBADB57F1,0x00000000} - a
		// deliberate NULL model - and carries a TagKind byte (exemplar
		// property 0xABB90E58) instead. That is why every PNG / FSH / S3D /
		// EFFDIR / window census returned an honest null: there is no asset.
		//
		// Draw spine, byte-verified (REGRESSION.md 2026-08-17):
		//   TagKind read      0x004FBFFC (the ONLY read in the whole exe)
		//   builder           0x004FBFE0, jump table 0x004FC410 on kind-1
		//                     -> icon id 0x4301/0x4305/0x4304/0x4307/0x4308
		//   FACTORY           0x00505370  (manager primary vt+0x3C)
		//                     called (0x4300, &dir, 0x10002, ...) @0x4FC1AB
		//                     and RETURNS THE SPRITE in eax
		//   creator           0x00510690  (vt+0xB8) -> GZCOM + QI 0xA9B40F05
		//
		// The one thing still unknown is WHICH FIELD of that sprite is its
		// size, so this measures instead of deriving. Today's record is
		// unambiguous: every measurement was right, every derivation needed
		// correcting - including my reading of 0x510360's duplicate write as
		// a "uniform extent" when tracing its argument proved it is the
		// orientation vector (values 0/+1/-1 at sprite+0x11C..0x128, which
		// therefore serve as a NEGATIVE control in the dump below).
		//
		// A real detour (not a naked jmp) because we need the return value.
		typedef void* (__fastcall *SpriteFactoryFn)(void* self, void* edx,
			uint32_t id, void* dir, uint32_t flags, uint32_t a4, uint32_t a5,
			uint32_t a6, void* a7);
		SpriteFactoryFn gSpriteFactoryOrig = nullptr;
		const uintptr_t kSpriteFactoryVa = 0x00505370;
		volatile LONG gSpriteCalls = 0;
		int gSpriteLogs = 0;

		void DumpSpriteFields(void* sprite, uint32_t id)
		{
			const uintptr_t base =
				reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
			static const char kHex[] = "0123456789ABCDEF";
			__try
			{
				const uint32_t* w = static_cast<const uint32_t*>(sprite);
				uint32_t vtVa = static_cast<uint32_t>(
					reinterpret_cast<uintptr_t>(*static_cast<void**>(sprite))
					- base + kImageBase);
				Logger::Get().WriteLine(LogLevel::Info,
					"CodePatches: BALLOONSPRITE #%ld obj=%p id=0x%04X "
					"vt=0x%08X.", gSpriteCalls, sprite, id, vtVa);
				// RAW HEX ONLY, 0x140 bytes in rows of 8 dwords. The PROPBIND
				// dump's float coercion silently ate the size bytes once
				// already today - never let a formatter decide what matters.
				for (int row = 0; row < 10; ++row)
				{
					char line[200];
					int u = 0;
					u += wsprintfA(line + u, "+%03X:", row * 32);
					for (int k = 0; k < 8; ++k)
					{
						const uint32_t v = w[row * 8 + k];
						line[u++] = ' ';
						for (int s = 28; s >= 0; s -= 4)
						{
							line[u++] = kHex[(v >> s) & 0xF];
						}
					}
					line[u] = 0;
					Logger::Get().WriteLine(LogLevel::Info,
						"CodePatches: BALLOONSPRITE #%ld %s", gSpriteCalls,
						line);
				}
				// Float view of the same words - a size is as likely to be a
				// float as an int, and printing BOTH costs nothing.
				for (int row = 0; row < 10; ++row)
				{
					char line[220];
					int u = 0;
					u += wsprintfA(line + u, "+%03X:", row * 32);
					for (int k = 0; k < 8; ++k)
					{
						float f = 0.0f;
						memcpy(&f, &w[row * 8 + k], 4);
						const bool pl = (f > 0.0009f && f < 100000.0f)
							|| (f < -0.0009f && f > -100000.0f);
						if (pl)
						{
							const int wh = static_cast<int>(f);
							int fr = static_cast<int>((f - wh) * 1000.0f);
							if (fr < 0) { fr = -fr; }
							u += wsprintfA(line + u, " %d.%03d", wh, fr);
						}
						else
						{
							u += wsprintfA(line + u, " -");
						}
					}
					line[u] = 0;
					Logger::Get().WriteLine(LogLevel::Info,
						"CodePatches: BALLOONFLT #%ld %s", gSpriteCalls, line);
				}
			}
			__except (EXCEPTION_EXECUTE_HANDLER)
			{
				Logger::Get().WriteLine(LogLevel::Info,
					"CodePatches: BALLOONSPRITE #%ld faulted dumping %p.",
					gSpriteCalls, sprite);
			}
		}

		void ApplySpriteScale(void* sprite)
		{
			const uint32_t off = static_cast<uint32_t>(gSpriteOffset);
			if (off == 0 || sprite == nullptr) { return; }
			// ⛔ sprite+0x124 is 0x510360's OWN "already configured" guard
			// (`if (src[8] && this[0x124]==0)`). We only ever run AFTER the
			// trampoline, so the game has finished its setup - but never
			// move this call before it.
			if (off + 8 > 0x140)
			{
				Logger::Get().WriteLine(LogLevel::Info,
					"CodePatches: BALLOONFIX offset 0x%X outside the dumped "
					"0x140 window - REFUSED.", off);
				return;
			}
			const float mul = gSpriteScale;
			if (!(mul > 1.01f) || !(mul <= 8.0f))
			{
				Logger::Get().WriteLine(LogLevel::Info,
					"CodePatches: BALLOONFIX multiplier %.2f outside (1,8] - "
					"REFUSED.", static_cast<double>(mul));
				return;
			}
			__try
			{
				uint8_t* p = static_cast<uint8_t*>(sprite) + off;
				if (gSpriteKind == 1)          // int32
				{
					int32_t pre = 0;
					memcpy(&pre, p, 4);
					int32_t post =
						static_cast<int32_t>(pre * mul + 0.5f);
					memcpy(p, &post, 4);
					int32_t rd = 0;
					memcpy(&rd, p, 4);
					Logger::Get().WriteLine(LogLevel::Info,
						"CodePatches: BALLOONFIX +0x%X int32 %d -> %d "
						"(read back %d).", off, pre, post, rd);
				}
				else if (gSpriteKind == 2)     // two int16 (w,h)
				{
					int16_t a = 0, b = 0;
					memcpy(&a, p, 2);
					memcpy(&b, p + 2, 2);
					int16_t na = static_cast<int16_t>(a * mul + 0.5f);
					int16_t nb = static_cast<int16_t>(b * mul + 0.5f);
					memcpy(p, &na, 2);
					memcpy(p + 2, &nb, 2);
					Logger::Get().WriteLine(LogLevel::Info,
						"CodePatches: BALLOONFIX +0x%X i16 (%d,%d) -> "
						"(%d,%d).", off, a, b, na, nb);
				}
				else                            // float (default)
				{
					float pre = 0.0f;
					memcpy(&pre, p, 4);
					float post = pre * mul;
					memcpy(p, &post, 4);
					float rd = 0.0f;
					memcpy(&rd, p, 4);
					Logger::Get().WriteLine(LogLevel::Info,
						"CodePatches: BALLOONFIX +0x%X float %d.%03d -> "
						"%d.%03d (read back %d.%03d).", off,
						static_cast<int>(pre),
						static_cast<int>((pre - static_cast<int>(pre)) * 1000),
						static_cast<int>(post),
						static_cast<int>((post - static_cast<int>(post)) * 1000),
						static_cast<int>(rd),
						static_cast<int>((rd - static_cast<int>(rd)) * 1000));
				}
			}
			__except (EXCEPTION_EXECUTE_HANDLER)
			{
				Logger::Get().WriteLine(LogLevel::Info,
					"CodePatches: BALLOONFIX faulted writing %p+0x%X.",
					sprite, off);
			}
		}

		void* __fastcall SpriteFactoryDetour(void* self, void* edx,
			uint32_t id, void* dir, uint32_t flags, uint32_t a4, uint32_t a5,
			uint32_t a6, void* a7)
		{
			void* r = gSpriteFactoryOrig(self, edx, id, dir, flags, a4, a5,
				a6, a7);
			InterlockedIncrement(&gSpriteCalls);
			if (r)
			{
				if (gSpriteLogs < 8)
				{
					++gSpriteLogs;
					DumpSpriteFields(r, id);
				}
				// The FIX runs for every sprite, not just the logged ones -
				// gating a cure on a log budget is how a fix silently covers
				// only the first N (the cap law, learned twice today).
				ApplySpriteScale(r);
			}
			return r;
		}

		// ---- #188 BALLOONKIND: the POSITIVE CONTROL I failed to ship ------
		// v3.0.27 armed the factory hook on 0x505370 and logged ZERO calls.
		// That is NOT evidence the factory is wrong - without a control it is
		// evidence of nothing at all, which is the single most expensive
		// mistake made today (five times). This hooks the BUILDER 0x4FBFE0 -
		// the only reader of TagKind in the exe - so the next capture can
		// distinguish:
		//   BALLOONKIND lines + no BALLOONSPRITE -> builder runs, my
		//       primary-vtable slot indexing (0xA94850+0x3C) is wrong
		//   neither                              -> the builder never runs
		//       for these balloons; the visitor/messages are the wrong path
		// One of those is a real finding. A bare null is not.
		typedef void* (__fastcall *BalloonBuildFn)(void* self, void* edx,
			void* occupant);
		BalloonBuildFn gBalloonBuildOrig = nullptr;
		const uintptr_t kBalloonBuildVa = 0x004FBFE0;
		volatile LONG gBuildCalls = 0;
		int gBuildLogs = 0;

		void* __fastcall BalloonBuildDetour(void* self, void* edx,
			void* occupant)
		{
			InterlockedIncrement(&gBuildCalls);
			void* r = gBalloonBuildOrig(self, edx, occupant);
			if (gBuildLogs < 12)
			{
				++gBuildLogs;
				const uintptr_t base =
					reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
				uint32_t primaryVt = 0;
				uint32_t slot3C = 0;
				__try
				{
					void** vt = *reinterpret_cast<void***>(self);
					primaryVt = static_cast<uint32_t>(
						reinterpret_cast<uintptr_t>(vt) - base + kImageBase);
					// Print what the builder's OWN vtable+0x3C actually holds,
					// so a wrong slot guess names itself instead of hiding.
					slot3C = static_cast<uint32_t>(
						reinterpret_cast<uintptr_t>(vt[0x3C / 4])
						- base + kImageBase);
				}
				__except (EXCEPTION_EXECUTE_HANDLER)
				{
					primaryVt = 0xBADBADBA;
				}
				Logger::Get().WriteLine(LogLevel::Info,
					"CodePatches: BALLOONKIND #%ld this=%p occ=%p vt=0x%08X "
					"vt+0x3C=0x%08X ret=%p.", gBuildCalls, self, occupant,
					primaryVt, slot3C, r);
			}
			return r;
		}

		void InstallBalloonBuildProbe()
		{
			const uintptr_t base =
				reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
			void* f = reinterpret_cast<void*>(
				base - kImageBase + kBalloonBuildVa);
			const MH_STATUS init = MH_Initialize();
			if (init != MH_OK && init != MH_ERROR_ALREADY_INITIALIZED) { return; }
			if (MH_CreateHook(f, reinterpret_cast<void*>(&BalloonBuildDetour),
					reinterpret_cast<void**>(&gBalloonBuildOrig)) != MH_OK
				|| MH_EnableHook(f) != MH_OK)
			{
				Logger::Get().WriteLine(LogLevel::Error,
					"CodePatches: BALLOONKIND failed to hook 0x004FBFE0.");
				return;
			}
			Logger::Get().WriteLine(LogLevel::Info,
				"CodePatches: BALLOONKIND armed on 0x004FBFE0 (the TagKind "
				"builder - the control for BALLOONSPRITE).");
		}

		void InstallBalloonSpriteProbe()
		{
			InstallBalloonBuildProbe();
			const uintptr_t base =
				reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
			void* f = reinterpret_cast<void*>(
				base - kImageBase + kSpriteFactoryVa);
			const MH_STATUS init = MH_Initialize();
			if (init != MH_OK && init != MH_ERROR_ALREADY_INITIALIZED)
			{
				Logger::Get().WriteLine(LogLevel::Error,
					"CodePatches: BALLOONSPRITE MH_Initialize failed (%d).",
					init);
				return;
			}
			if (MH_CreateHook(f, reinterpret_cast<void*>(&SpriteFactoryDetour),
					reinterpret_cast<void**>(&gSpriteFactoryOrig)) != MH_OK
				|| MH_EnableHook(f) != MH_OK)
			{
				Logger::Get().WriteLine(LogLevel::Error,
					"CodePatches: BALLOONSPRITE failed to hook 0x00505370.");
				return;
			}
			Logger::Get().WriteLine(LogLevel::Info,
				"CodePatches: BALLOONSPRITE armed on 0x00505370 (sprite "
				"factory; fix offset 0x%X kind %d scale %.2f).",
				static_cast<unsigned>(gSpriteOffset), gSpriteKind,
				static_cast<double>(gSpriteScale));
		}

		void InstallSignpostProbe()
		{
			InstallArtFetchProbeImpl();
			InstallBalloonSpriteProbe();
			const uintptr_t base =
				reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
			void* q = reinterpret_cast<void*>(base - kImageBase + kSpQuadVa);
			void* t = reinterpret_cast<void*>(base - kImageBase + kSpTexVa);
			if (memcmp(q, kSpQuadStock, sizeof(kSpQuadStock)) != 0
				|| memcmp(t, kSpTexStock, sizeof(kSpTexStock)) != 0)
			{
				Logger::Get().WriteLine(LogLevel::Info,
					"CodePatches: SPPROBE prologue mismatch - not installed.");
				return;
			}
			const MH_STATUS init = MH_Initialize();
			if (init != MH_OK && init != MH_ERROR_ALREADY_INITIALIZED)
			{
				Logger::Get().WriteLine(LogLevel::Error,
					"CodePatches: SPPROBE MH_Initialize failed (%d).", init);
				return;
			}
			if (MH_CreateHook(q, reinterpret_cast<void*>(&SpQuadDetour),
					&gSpQuadTramp) != MH_OK
				|| MH_EnableHook(q) != MH_OK
				|| MH_CreateHook(t, reinterpret_cast<void*>(&SpTexDetour),
					&gSpTexTramp) != MH_OK
				|| MH_EnableHook(t) != MH_OK)
			{
				Logger::Get().WriteLine(LogLevel::Error,
					"CodePatches: SPPROBE failed to hook - probe absent "
					"(the fix itself is unaffected).");
				return;
			}
			// The proxy getter swap - per-frame callers = the draw path.
			InstallProxyGetterProbe();
			// Per-slot capture on the captured balloon class vtables.
			InstallVtCap();
			// The drawable's draw forwarder - hooked directly.
			void* dw = reinterpret_cast<void*>(base - kImageBase + kDrawVa);
			if (memcmp(dw, kDrawStock, sizeof(kDrawStock)) == 0
				&& MH_CreateHook(dw, reinterpret_cast<void*>(&SpDrawDetour),
					&gDrawTramp) == MH_OK
				&& MH_EnableHook(dw) == MH_OK)
			{
				Logger::Get().WriteLine(LogLevel::Info,
					"CodePatches: DRAWCAP armed on 0x005FD2D0 (vt4+0x18 draw "
					"forwarder).");
			}
			else
			{
				Logger::Get().WriteLine(LogLevel::Info,
					"CodePatches: DRAWCAP NOT armed.");
			}
			// The prop binder - the balloon prop names itself at city load.
			void* bd = reinterpret_cast<void*>(base - kImageBase + kSpBindVa);
			if (memcmp(bd, kSpBindStock, sizeof(kSpBindStock)) == 0
				&& MH_CreateHook(bd, reinterpret_cast<void*>(&SpBindDetour),
					&gSpBindTramp) == MH_OK
				&& MH_EnableHook(bd) == MH_OK)
			{
				Logger::Get().WriteLine(LogLevel::Info,
					"CodePatches: SPPROBE bind hook armed on 0x00496950.");
			}
			else
			{
				Logger::Get().WriteLine(LogLevel::Info,
					"CodePatches: SPPROBE bind hook NOT armed.");
			}
			// SetTrackedTarget - the STACK-PROVEN click threshold; the
			// clicked occupant names its class here on every click.
			void* tg = reinterpret_cast<void*>(base - kImageBase + kSpTargetVa);
			if (memcmp(tg, kSpTargetStock, sizeof(kSpTargetStock)) == 0
				&& MH_CreateHook(tg, reinterpret_cast<void*>(&SpTargetDetour),
					&gSpTargetTramp) == MH_OK
				&& MH_EnableHook(tg) == MH_OK)
			{
				Logger::Get().WriteLine(LogLevel::Info,
					"CodePatches: SPPROBE target hook armed on 0x00528580.");
			}
			else
			{
				Logger::Get().WriteLine(LogLevel::Info,
					"CodePatches: SPPROBE target hook NOT armed.");
			}
			// The mayor hover handler - GUARANTEED-LIVE path (proven by the
			// resolved balloon clicks); hovering the balloon logs its
			// drawable's class.
			void* hv = reinterpret_cast<void*>(base - kImageBase + kSpHoverVa);
			if (memcmp(hv, kSpHoverStock, sizeof(kSpHoverStock)) == 0
				&& MH_CreateHook(hv, reinterpret_cast<void*>(&SpHoverDetour),
					&gSpHoverTramp) == MH_OK
				&& MH_EnableHook(hv) == MH_OK)
			{
				Logger::Get().WriteLine(LogLevel::Info,
					"CodePatches: SPPROBE hover hook armed on 0x004D7950.");
			}
			else
			{
				Logger::Get().WriteLine(LogLevel::Info,
					"CodePatches: SPPROBE hover hook NOT armed.");
			}
			// The marker ATTACH choke point - fires at city load for every
			// marker; the balloon's view class names itself in the log.
			void* at = reinterpret_cast<void*>(base - kImageBase + kSpAttachVa);
			if (memcmp(at, kSpAttachStock, sizeof(kSpAttachStock)) == 0
				&& MH_CreateHook(at, reinterpret_cast<void*>(&SpAttachDetour),
					&gSpAttachTramp) == MH_OK
				&& MH_EnableHook(at) == MH_OK)
			{
				Logger::Get().WriteLine(LogLevel::Info,
					"CodePatches: SPPROBE attach hook armed on 0x005F7C80.");
			}
			else
			{
				Logger::Get().WriteLine(LogLevel::Info,
					"CodePatches: SPPROBE attach hook NOT armed.");
			}
			// The LIVE balloon builder (the strip at 0x5F5FB0) - the probe
			// that adjudicates the MARKERZOOM lever.
			void* st = reinterpret_cast<void*>(base - kImageBase + kMarkerStripVa);
			if (memcmp(st, kMarkerStripStock, sizeof(kMarkerStripStock)) == 0
				&& MH_CreateHook(st, reinterpret_cast<void*>(&SpStripDetour),
					&gSpStripTramp) == MH_OK
				&& MH_EnableHook(st) == MH_OK)
			{
				Logger::Get().WriteLine(LogLevel::Info,
					"CodePatches: SPPROBE strip hook armed on 0x005F5FB0.");
			}
			else
			{
				Logger::Get().WriteLine(LogLevel::Info,
					"CodePatches: SPPROBE strip hook NOT armed (prologue or "
					"MinHook) - MARKERZOOM adjudication limited to eyes-on.");
			}
			Logger::Get().WriteLine(LogLevel::Info,
				"CodePatches: SPPROBE armed on 0x005F20A0 (quad) + "
				"0x005F1610 (texture).");
		}

		// ---- #188 PICK PROBE (mode 3, installed at PostCityInit) ----------
		// SIX drawer systems eliminated by armed probes (window census,
		// effects, signpost quad+texture, S3D name sweep, marker strip).
		// The eliminative instrument that CANNOT miss: hook
		// cISC43DRender::Pick(x, y, filter, &instance) itself (vendor
		// header cISC43DRender.h:129, slot +0x104 - the call the balloon
		// click PROVABLY traverses: mission_selection_red fired on click).
		// Every HIT logs the model instance and its VTABLE VA: whatever the
		// user hovers or clicks names its own class - no more guessing.
		// Runtime-resolved from the render singleton [0xB43DD0] (set during
		// city init), so the install rides PostCityInit, once.
		typedef uint32_t (__fastcall* PickFn)(void*, void*, int32_t,
			int32_t, void*, void**);
		PickFn gPickOrig = nullptr;
		volatile LONG gPickCalls = 0;
		volatile LONG gPickHits = 0;
		int gPickLogs = 0;
		bool gPickInstalled = false;

		uint32_t __fastcall PickDetour(void* self, void* edx,
			int32_t x, int32_t y, void* filter, void** out)
		{
			const uint32_t r = gPickOrig
				? gPickOrig(self, edx, x, y, filter, out) : 0;
			InterlockedIncrement(&gPickCalls);
			do
			{
				if (!(r & 0xFF) || !out || !*out) { break; }
				InterlockedIncrement(&gPickHits);
				if (gPickLogs >= 40) { break; }
				++gPickLogs;
				void* inst = *out;
				const uintptr_t base =
					reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
				const uintptr_t vt = *reinterpret_cast<uintptr_t*>(inst);
				const uint32_t vtVa =
					static_cast<uint32_t>(vt - base + kImageBase);
				Logger::Get().WriteLine(LogLevel::Info,
					"CodePatches: PICKHIT #%ld (%d,%d) inst=%p vt=0x%08X "
					"filter=%p.", gPickHits, x, y, inst, vtVa, filter);
			} while (false);
			return r;
		}

		uint32_t __fastcall CreateEffectDetour(void* self, void* edx,
			const char* name, void** out)
		{
			const uint32_t r = gCreateEffectOrig
				? gCreateEffectOrig(self, edx, name, out) : 0;
			// v3.0.16 UNFILTERED census (the mission_selection filter made
			// every earlier "zero spawns" verdict a FILTERED NULL - the
			// balloon's own effect name passed through unlogged). Mode 3:
			// log every spawn's name + call-site; offer-band call sites
			// (0x490000-0x4B0000, where offer creation lives) logged on
			// their own uncapped-ish channel.
			const uintptr_t base0 =
				reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
			const uint32_t rv = static_cast<uint32_t>(
				reinterpret_cast<uintptr_t>(_ReturnAddress())
				- base0 + kImageBase);
			if (gBubbleStack && name)
			{
				const bool band = (rv >= 0x490000 && rv < 0x4B0000);
				if (band && gBubbleBandLogs < 16)
				{
					++gBubbleBandLogs;
					Logger::Get().WriteLine(LogLevel::Info,
						"CodePatches: BUBBLEBAND %s ret=0x%08X ok=%u.",
						name, rv, r & 0xFF);
				}
				else if (!band && gBubbleAllLogs < 40)
				{
					++gBubbleAllLogs;
					Logger::Get().WriteLine(LogLevel::Info,
						"CodePatches: BUBBLEALL %s ret=0x%08X ok=%u.",
						name, rv, r & 0xFF);
				}
			}
			do
			{
				// Success flag first (AL: mov al,1 at 0x593AC5 / xor al,al
				// at 0x593A79), then the cheap name filter - *out is
				// dereferenced ONLY for an intended, successful spawn. On
				// every failure path the exe never writes *ppOut (its sole
				// store is 0x593AB9 on success), so the slot may hold
				// caller garbage (review 2026-08-17, finding 1).
				if (!(r & 0xFF)) { break; }
				if (!name || !out) { break; }
				// v3.0.17 THE FIX: the unfiltered census (18:43 capture)
				// proved the offer visual is an effect COMPOSITE spawned by
				// the marker class ITSELF from 0x5E8917's call (ret
				// 0x5E891C) under per-vehicle names (cargopu/motorcycle/
				// rotor/heliblade/...), plus the aircraftindicate indicator
				// family. Scale everything the marker spawn site creates +
				// the indicator family + the original selection glows. The
				// site gate keeps city scenery (same band's natural_gas_
				// smoke at 0x5EEA73 etc.) untouched.
				const bool markerSpawn = (rv == 0x5E891C)
					|| (strncmp(name, "aircraftindicate", 16) == 0);
				if (strncmp(name, "mission_selection", 17) != 0
					&& !markerSpawn) { break; }
				if (gBubbleStack && gBubbleStackLogs < 4)
				{
					++gBubbleStackLogs;
					LogBubbleCallStack(&name);
				}
				if (!*out) { break; }
				uint8_t* inst = static_cast<uint8_t*>(*out);
				float* scale = reinterpret_cast<float*>(inst + kInstScaleOff);
				uint8_t* flag = inst + kInstFlagOff;
				// Pristine = the CONSTRUCTOR's state (0x5C0150 writes
				// 0x3F800000 to +0x110 at 0x5C047E and 0 to +0xDD at
				// 0x5C0496) - NOT the bind: 0x5BFF80 resets the block only
				// when the mask byte is already nonzero (0x5C008F). An
				// instance outside that state is one this model does not
				// describe - refuse to write. The refusal is the
				// INTERESTING event, so it is never capped; only the
				// routine lines share the cap (the RATEANCHOR idiom).
				const bool pristine = (*flag == 0 && *scale == 1.0f);
				const bool arm = (gBubbleScale > 1.01f) && pristine;
				// ⛔ THE CAP THAT BLINDED THE CLICK TEST (2026-08-17). This
				// read `gBubbleLogs < 12`, and city load spawns EXACTLY 12
				// pristine effects - so the budget was spent before the user
				// could click, and the mission_selection_red line at the
				// click printed NOTHING. The user said "I clicked", the log
				// showed no click, and I believed the log. It was wrong.
				//
				// The cap only ever silenced the LOG; the scale write below
				// still ran, which is why the click was a valid experiment
				// with an invisible record. Cure: the click-time names get
				// their OWN unconditional channel, and the census budget can
				// never eat it. NULL IS NOT EVIDENCE - a probe whose budget
				// is consumed by an unrelated burst is not reporting a null,
				// it is reporting nothing at all.
				const bool clickEvent =
					(strncmp(name, "mission_selection", 17) == 0);
				if (!pristine || clickEvent || gBubbleLogs < 40)
				{
					if (!clickEvent) { ++gBubbleLogs; }
					Logger::Get().WriteLine(LogLevel::Info,
						"CodePatches: BUBBLEFX %s inst=%p pre(scale=%.2f "
						"flag=%u) %s.", name, *out,
						static_cast<double>(*scale), *flag,
						arm ? "-> scaled" : (pristine ? "log-only"
							: "NOT PRISTINE, skipped"));
				}
				if (!arm) { break; }
				*scale = gBubbleScale;
				// ⛔ DO NOT SET THE FLAG. Writing kInstFlagBits (0x06) here is
				// what made every effect-scale attempt inert, and it was our
				// own doing:
				//   * activation 0x591DF5 branches on the CHILD's flags byte
				//     (+0x15). For flags==0 - which is 2860 of 3420 stock
				//     children, INCLUDING both aircraftindicate children and
				//     both mission_selection_red children - it takes ARM 1 at
				//     0x59207A, which delivers the INSTANCE scale (+0x110)
				//     verbatim and never examines +0xDD at all.
				//   * but bind 0x5BFF80 RESETS the whole transform block when
				//     the mask byte +0xDD is ALREADY NONZERO (test at
				//     0x5C008F). By setting it to 0x06 we asked for exactly
				//     that reset, wiping the scale we had just written.
				// So the flag was never needed for this population, and
				// setting it actively destroyed the write. Leave +0xDD at its
				// constructor value of 0: the pristine gate above already
				// guarantees it, ARM 1 reads our scale, and no reset fires.
				//
				// (kInstFlagBits is kept only as documentation of
				// ReadTransform's bit convention - bit1 = scale != 1,
				// bit2 = rotation present - for the flags != 0 population,
				// which takes a different arm entirely.)
				++gBubbleHits;
			} while (false);
			return r;
		}
	}

	void InstallMissionBubbleScale(float factor, int mode, float overrideScale)
	{
		if (mode <= 0) { return; }
		// overrideScale is the no-rebuild tuning knob (ini
		// MissionBubbleScale): <= 0 follows the tier factor (the general
		// form); > 0 is taken LITERALLY, so 1.0 means "stock size" and is
		// declined below rather than silently replaced by the tier factor
		// (review 2026-08-17, finding 5).
		const float want = (overrideScale > 0.0f) ? overrideScale : factor;
		const bool wantFix = (mode >= 2 && want > 1.01f);
		const bool wantLog = (mode == 1);
		if (!wantFix && !wantLog)
		{
			Logger::Get().WriteLine(LogLevel::Info,
				"CodePatches: BUBBLEFX declined at factor %.2f (mode %d) - "
				"nothing installed; effect spawns are byte-identical.",
				static_cast<double>(want), mode);
			return;
		}
		// An unclamped ini float must never become a code imm: inf or an
		// absurd multiplier declines the WHOLE feature loudly (review
		// 2026-08-17, finding 3). NaN never reaches here - NaN > 1.01f is
		// false, so wantFix is already off and the decline above fired.
		if (wantFix && !(want <= 8.0f))
		{
			Logger::Get().WriteLine(LogLevel::Info,
				"CodePatches: BUBBLEFX multiplier %.2f outside (1,8] - REFUSED, "
				"nothing installed.", static_cast<double>(want));
			return;
		}

		// THE PRIMARY LEVER FIRST, gated only on its OWN site bytes (gate on
		// the condition you depend on - review finding 1: this call
		// previously sat behind the HOOK's prologue check below, so an
		// unrelated byte mismatch at 0x5939B0 - another mod hooking
		// CreateEffectByName, say - would have silently killed the balloon
		// fix). ApplySignpostScale logs its own outcome either way; the
		// effect-glow hook below succeeds or fails independently of it.
		// THESE TWO TAKE THE TIER FACTOR, NEVER THE OVERRIDE. They scale the
		// POLE-balloon family (mayor-hat sign, dispatch lollipops) - shipping
		// tier behaviour, user-visible, and NOT the #188 target (proven by
		// the v3.0.23 regression). MissionBubbleScale is the balloon-hunt
		// diagnostic knob: feeding a 5.0 probe value into the pole quad
		// would blow the mayor-hat sign to 220px and read as a new bug.
		if (factor > 1.01f && mode >= 2) { ApplySignpostScale(factor); }
		// The LIVE lever (the two above are the dormant twin + the glow):
		// the marker per-zoom table, sole consumer = the balloon strip
		// builder. This is the patch that moves the on-screen balloon.
		if (factor > 1.01f && mode >= 2) { ApplyMarkerZoomScale(factor); }
		// (v3.0.23's ApplyBalloonCellScale(2) + 2x sheet dat lived here -
		// reverted v3.0.24 after regressing the mayor-hat pole balloon; see
		// the BALLOONCELL ledger comment above ApplySignpostScale.)
		// #188 BALLOONSPRITE knobs, read straight from the live ini so the
		// size field can be re-aimed without a rebuild. Arm them BEFORE
		// InstallSignpostProbe below, which installs the hook that reads them.
		{
			wchar_t iniPath[MAX_PATH] = {};
			GetModuleFileNameW(reinterpret_cast<HMODULE>(&__ImageBase),
				iniPath, MAX_PATH);
			wchar_t* slash = wcsrchr(iniPath, L'\\');
			if (slash) { wcscpy_s(slash + 1, 32, L"SC4UIScale.ini"); }
			gSpriteOffset = static_cast<int>(GetPrivateProfileIntW(
				L"UiSpike", L"BalloonSpriteOffset", 0, iniPath));
			gSpriteKind = static_cast<int>(GetPrivateProfileIntW(
				L"UiSpike", L"BalloonSpriteKind", 0, iniPath));
			wchar_t buf[32] = {};
			GetPrivateProfileStringW(L"UiSpike", L"BalloonSpriteScale", L"0",
				buf, 32, iniPath);
			gSpriteScale = static_cast<float>(_wtof(buf));
			// <= 0 means "follow the tier", matching MissionBubbleScale.
			if (gSpriteScale <= 0.0f) { gSpriteScale = factor; }
		}
		// #188 PIXTABLE: the per-zoom SCREEN-PIXEL size table at .rdata
		// 0x00A88170 {20,30,40,50,60, 60,14,32,35,64}, sole consumer
		// 0x0046CD03 -> px->world helper 0x007F6690 -> billboard builder
		// 0x0046C8B0 (cos-corrected, half-extents). The user's own two
		// screenshots PROVE the balloons are pixel-fixed: same resolution,
		// same tier, very different zoom, identical balloon pixel size. A
		// per-zoom pixel table feeding a billboard is exactly that behaviour,
		// and this module (0x46Cxxx-0x46Fxxx) is untouched by all ten
		// eliminations. Scaling the table is the test.
		if (factor > 1.01f && mode >= 2) { ApplyPixelTable(factor); }
		// THE CSI QUAD - the actual balloon size (0x00A8819C = 42 px).
		if (factor > 1.01f && mode >= 2) { ApplyCsiScale(factor); }
		// #188 SHIPS ON BY DEFAULT (mode 2). The offer balloon is the
		// only in-world overlay a player interacts with, so an unscaled
		// one is both ugly AND a tiny tap target at 1.5x/2x/3x.
		if (factor > 1.01f && mode >= 2) { ApplyCsiIndicatorScale(factor); }
		// #191 - MUST ride the same gate as the line above. ApplyCsiIndicatorScale
		// doubles the category-3 icon QUAD; this fixes the UV divisor that decides
		// how much of the (now larger) portrait texture that quad shows. Arming
		// one without the other is the exact half-patched state #191 reported.
		if (factor > 1.01f && mode >= 2) { ApplyMySimMarkerTexSide(factor); }
		// Ungated by mode on purpose: CSIAIM is inert unless [UiSpike]CsiAim
		// names an address, and it must be aimable without touching any
		// other knob (that is the whole point - one launch, many candidates).
		ApplyCsiAimList(factor > 1.01f ? factor : 1.5f);
		if (mode >= 2) { InstallCsiDrawProbe(); }
		// ARM THE SCALE BEFORE ANY HOOK THAT CONSUMES IT. This assignment
		// used to sit AFTER the CreateEffectByName prologue check below, so
		// an unrelated byte mismatch at 0x5939B0 would have left
		// gBubbleScale at 0 and silently demoted the MARKERSIZE lever to
		// log-only - the same gate-on-an-unrelated-condition defect review
		// already caught once in this function.
		gBubbleScale = wantFix ? want : 0.0f;
		// Mode 3 = fix + live probe: adjudicates WHERE the balloon actually
		// draws (see the SPPROBE block). The prop-binder hook it installs
		// also carries the MARKERSIZE lever (the marker's own per-object
		// size), so this is a FIX path now, not only diagnosis.
		if (mode >= 3) { InstallSignpostProbe(); }

		const uintptr_t base = reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
		void* target = reinterpret_cast<void*>(base - kImageBase + kCreateEffectVa);
		if (memcmp(target, kCreateEffectStock, sizeof(kCreateEffectStock)) != 0)
		{
			Logger::Get().WriteLine(LogLevel::Info,
				"CodePatches: BUBBLEFX prologue mismatch at %p - skipped.",
				target);
			return;
		}
		const MH_STATUS init = MH_Initialize();
		if (init != MH_OK && init != MH_ERROR_ALREADY_INITIALIZED)
		{
			Logger::Get().WriteLine(LogLevel::Error,
				"CodePatches: BUBBLEFX MH_Initialize failed (%d).", init);
			return;
		}
		if (MH_CreateHook(target, reinterpret_cast<void*>(&CreateEffectDetour),
				reinterpret_cast<void**>(&gCreateEffectOrig)) != MH_OK
			|| MH_EnableHook(target) != MH_OK)
		{
			Logger::Get().WriteLine(LogLevel::Error,
				"CodePatches: BUBBLEFX failed to hook CreateEffectByName at "
				"%p.", target);
			return;
		}
		gBubbleStack = (mode >= 3);
		Logger::Get().WriteLine(LogLevel::Info,
			"CodePatches: BUBBLEFX installed on CreateEffectByName %p "
			"(scale %.2f, mode %d: %s).", target,
			static_cast<double>(want), mode,
			wantFix ? "log + scale" : "log only");
	}

	int MissionBubbleFxHits() { return gBubbleHits; }

	// Public forwarder: the impl lives in the anonymous namespace with the
	// rest of the #188 probes, but the DIRECTOR CONSTRUCTOR needs to arm this
	// one - it is the only probe that must beat app init.
	void InstallArtFetchProbe() { InstallArtFetchProbeImpl(); }

	// ---- #188 VIEWOBJ: the LAST drawing channel in the game --------------
	// Eight subsystems are now closed with controls that fired: windows, PNG
	// art, EFFDIR decals, effect instance scale, effect child scale, the
	// marker-family S3D, the marker occupant size, and the TagKind manager.
	// One channel remains, and it is the only one with no data behind it and
	// therefore no name to mislead:
	//
	//   cISC43DRender::AddViewObject(cISC4ViewObject3D*, int32_t, uint32_t)
	//
	// cISC4ViewObject3D is FORWARD-DECLARED ONLY in the whole SDK
	// (cISC43DRender.h:32) - there is no header, no exemplar, no resource.
	// That is exactly the shape of a thing that draws a clickable,
	// pixel-fixed sprite over a moving vehicle.
	//
	// SLOT DERIVATION, anchored twice against code this project already
	// trusts: counting the 3 inherited cIGZUnknown slots, the header order in
	// cISC43DRender.h puts Pick(int32,int32,filter,model&) at +0x104 and
	// PickTerrain(int32,...) at +0xF0 - and our own notes independently record
	// the model pick at [0xB43DD0] vt+0x104 and PickTerrain at vt+0xF0. Two
	// anchors agreeing fixes AddViewObject at **vt+0x80**.
	//
	// Log-only. Positive control built in: two balloons on screen must
	// produce registrations, and the count must fall when an offer expires.
	typedef bool(__fastcall* AddViewObjFn)(void* self, void* edx, void* obj,
		int32_t a2, uint32_t a3);
	AddViewObjFn gAddViewOrig = nullptr;
	volatile LONG gAddViewCalls = 0;
	int gAddViewLogs = 0;
	bool gAddViewInstalled = false;
	// [UiSpike] BalloonViewSuppress=1 -> refuse class 0xAA8314 registrations
	// (the identification-by-subtraction test; see AddViewObjDetour).
	int gViewSuppress = 0;
	// [UiSpike] BalloonViewKill = a vtable VA (hex). At the frame-400
	// enumeration, every live view object of that class is removed through
	// the renderer's own RemoveViewObject. Identification by subtraction.
	int gViewKill = 0;

	bool __fastcall AddViewObjDetour(void* self, void* edx, void* obj,
		int32_t a2, uint32_t a3)
	{
		InterlockedIncrement(&gAddViewCalls);
		if (gAddViewLogs < 40 && obj)
		{
			++gAddViewLogs;
			const uintptr_t base =
				reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
			uint32_t vtVa = 0;
			uint32_t f0 = 0, f4 = 0, f8 = 0, fc = 0;
			__try
			{
				const uint32_t* w = static_cast<const uint32_t*>(obj);
				vtVa = static_cast<uint32_t>(
					reinterpret_cast<uintptr_t>(*static_cast<void**>(obj))
					- base + kImageBase);
				f0 = w[1]; f4 = w[2]; f8 = w[3]; fc = w[4];
			}
			__except (EXCEPTION_EXECUTE_HANDLER)
			{
				vtVa = 0xBADBADBA;
			}
			Logger::Get().WriteLine(LogLevel::Info,
				"CodePatches: VIEWOBJ #%ld obj=%p vt=0x%08X a2=%d a3=0x%08X "
				"| +04=%08X +08=%08X +0C=%08X +10=%08X.",
				gAddViewCalls, obj, vtVa, a2, a3, f0, f4, f8, fc);
		}
		// ---- THE IDENTIFICATION TEST -----------------------------------
		// Three objects of class 0xAA8314 register 1.3 s after the HUD batch,
		// 0x80 apart in one array, and the city shows exactly three floating
		// markers (two U-Drive-It offer balloons + the mayor-hat balloon).
		// That is a population MATCH, which no other candidate ever produced
		// - but a match is not a proof.
		//
		// So prove it by SUBTRACTION: refuse to register that class and see
		// what disappears. This is the cheapest possible decisive test - no
		// geometry maths, nothing to misalign, nothing that can hang, and it
		// cannot produce an ambiguous "no change" because the expected result
		// is an ABSENCE the user cannot miss.
		//   balloons gone  -> class 0xAA8314 IS the balloon drawable; the
		//                     size then lives in its draw 0x620500/0x620160
		//   balloons stay  -> class excluded, and whatever DID vanish names
		//                     itself for free
		// Armed by [UiSpike] BalloonViewSuppress=1. Log-only otherwise.
		if (gViewSuppress && obj)
		{
			__try
			{
				const uintptr_t base =
					reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
				const uint32_t vtVa = static_cast<uint32_t>(
					reinterpret_cast<uintptr_t>(*static_cast<void**>(obj))
					- base + kImageBase);
				if (vtVa == 0x00AA8314)
				{
					Logger::Get().WriteLine(LogLevel::Info,
						"CodePatches: VIEWSUPPRESS refused obj=%p "
						"vt=0x00AA8314 (identification test).", obj);
					return false;
				}
			}
			__except (EXCEPTION_EXECUTE_HANDLER) { /* fall through */ }
		}
		return gAddViewOrig(self, edx, obj, a2, a3);
	}

	// ---- #188 VIEWLIST: enumerate the renderer's LIVE view objects -------
	// The AddViewObject hook can only see registrations that happen AFTER it
	// arms, and it cannot arm before the renderer exists (PostCityInit). It
	// caught 11 - implausibly few for a city view - so it was showing a TAIL,
	// not a census. Watching a doorway never enumerates the room.
	//
	// AddViewObject (0x007C5D90) dispatches by LAYER into four lists on the
	// renderer, byte-verified:
	//     layer 3 -> renderer+0x188      layer 5 -> renderer+0x18C
	//     layer 0 -> renderer+0x190      layer 2 -> renderer+0x194
	//     anything else -> returns false
	// and the inserter 0x007C5C80 walks them as a CIRCULAR list with a
	// sentinel: head = *(field); node = *head; while (node != head)
	// { ...; node = *node; } with the sort key at node+0x0C (compared to the
	// a3 argument at 0x007C5CA0) and the object pointer at node+0x08.
	//
	// Driven off the renderer's Draw so it runs every frame regardless of
	// when anything registered. Header slot 18 (Draw) + 3 inherited COM slots
	// = vt+0x54 - the same +3 rule that put Pick at +0x104 and PickTerrain at
	// +0xF0, both of which this project already relies on.
	//
	// POSITIVE CONTROL built in: the 8 HUD classes the registration hook
	// already saw (0xAB4480 / 0xAB39D0 / 0xAB42F8 / 0xAB4624) MUST appear in
	// the enumeration. If they do not, the walk is wrong and every count
	// below is void - say so rather than reporting a number.
	typedef bool(__fastcall* RenderDrawFn)(void* self, void* edx);
	RenderDrawFn gRenderDrawOrig = nullptr;
	volatile LONG gFrameCount = 0;
	bool gViewListDumped = false;
	bool gDrawHooked = false;

	void DumpViewObjectLists(void* renderer)
	{
		const uintptr_t base =
			reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
		const uint32_t offs[4] = { 0x188, 0x18C, 0x190, 0x194 };
		const int layers[4] = { 3, 5, 0, 2 };
		int grand = 0;
		for (int k = 0; k < 4; ++k)
		{
			int n = 0;
			__try
			{
				uint8_t* field = static_cast<uint8_t*>(renderer) + offs[k];
				void* head = *reinterpret_cast<void**>(field);
				if (!head) { continue; }
				void* node = *reinterpret_cast<void**>(head);
				// Bound the walk: a corrupt or misread list must not spin.
				while (node && node != head && n < 400)
				{
					void* obj = *reinterpret_cast<void**>(
						static_cast<uint8_t*>(node) + 8);
					uint32_t key = *reinterpret_cast<uint32_t*>(
						static_cast<uint8_t*>(node) + 0x0C);
					uint32_t vtVa = 0;
					if (reinterpret_cast<uintptr_t>(obj) > 0x10000)
					{
						vtVa = static_cast<uint32_t>(
							reinterpret_cast<uintptr_t>(
								*static_cast<void**>(obj)) - base + kImageBase);
					}
					Logger::Get().WriteLine(LogLevel::Info,
						"CodePatches: VIEWLIST layer%d[%d] obj=%p "
						"vt=0x%08X key=0x%08X.", layers[k], n, obj, vtVa, key);
					++n;
					void* next = *reinterpret_cast<void**>(node);
					// IDENTIFY BY SUBTRACTION, aimed from the ini so a wrong
					// guess costs a relaunch and not a rebuild. Removing a
					// view object is the renderer's own supported operation
					// (RemoveViewObject, vt+0x84) - no geometry, nothing to
					// misalign, and the expected result is an ABSENCE the
					// user cannot misread as "no change".
					if (gViewKill != 0 && vtVa == static_cast<uint32_t>(gViewKill))
					{
						void** rvt = *reinterpret_cast<void***>(renderer);
						typedef bool(__fastcall* RemoveFn)(void*, void*, void*);
						RemoveFn rem = reinterpret_cast<RemoveFn>(rvt[0x84 / 4]);
						const bool ok = rem(renderer, nullptr, obj);
						Logger::Get().WriteLine(LogLevel::Info,
							"CodePatches: VIEWKILL removed obj=%p vt=0x%08X "
							"-> %d.", obj, vtVa, ok ? 1 : 0);
					}
					node = next;
				}
			}
			__except (EXCEPTION_EXECUTE_HANDLER)
			{
				Logger::Get().WriteLine(LogLevel::Info,
					"CodePatches: VIEWLIST layer%d FAULTED after %d entries "
					"- walk is wrong, ignore this layer.", layers[k], n);
			}
			grand += n;
			Logger::Get().WriteLine(LogLevel::Info,
				"CodePatches: VIEWLIST layer%d (renderer+0x%X) total %d.",
				layers[k], offs[k], n);
		}
		Logger::Get().WriteLine(LogLevel::Info,
			"CodePatches: VIEWLIST GRAND TOTAL %d live view objects. CONTROL: "
			"the 8 HUD classes (0xAB4480/0xAB39D0/0xAB42F8/0xAB4624) must "
			"appear above, or this walk is void.", grand);
	}

	bool __fastcall RenderDrawDetour(void* self, void* edx)
	{
		const LONG f = InterlockedIncrement(&gFrameCount);
		// Wait until the city is settled and the balloons exist, then dump
		// ONCE. Frame 400 at ~30 fps is ~13 s after the first drawn frame.
		if (f == 400 && !gViewListDumped)
		{
			gViewListDumped = true;
			DumpViewObjectLists(self);
		}
		return gRenderDrawOrig(self, edx);
	}

	void InstallViewObjProbe()
	{
		if (gAddViewInstalled) { return; }
		{
			wchar_t ini[MAX_PATH] = {};
			GetModuleFileNameW(reinterpret_cast<HMODULE>(&__ImageBase), ini,
				MAX_PATH);
			wchar_t* s = wcsrchr(ini, L'\\');
			if (s) { wcscpy_s(s + 1, 32, L"SC4UIScale.ini"); }
			gViewSuppress = static_cast<int>(GetPrivateProfileIntW(
				L"UiSpike", L"BalloonViewSuppress", 0, ini));
			wchar_t kb[32] = {};
			GetPrivateProfileStringW(L"UiSpike", L"BalloonViewKill", L"0",
				kb, 32, ini);
			gViewKill = static_cast<int>(wcstoul(kb, nullptr, 16));
		}
		const uintptr_t base =
			reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
		void* svc = *reinterpret_cast<void**>(base - kImageBase + 0xB43DD0);
		if (!svc) { return; }
		void** vt = *reinterpret_cast<void***>(svc);
		void* target = vt[0x80 / 4];
		const uintptr_t tva =
			reinterpret_cast<uintptr_t>(target) - base + kImageBase;
		// Sanity-bound the slot: a bad index would hand MinHook garbage.
		if (tva < 0x401000 || tva > 0xA80000)
		{
			Logger::Get().WriteLine(LogLevel::Info,
				"CodePatches: VIEWOBJ slot +0x80 = 0x%08X is outside .text - "
				"NOT installed (slot derivation wrong).",
				static_cast<unsigned>(tva));
			return;
		}
		const MH_STATUS init = MH_Initialize();
		if (init != MH_OK && init != MH_ERROR_ALREADY_INITIALIZED) { return; }
		if (MH_CreateHook(target, reinterpret_cast<void*>(&AddViewObjDetour),
				reinterpret_cast<void**>(&gAddViewOrig)) != MH_OK
			|| MH_EnableHook(target) != MH_OK)
		{
			Logger::Get().WriteLine(LogLevel::Error,
				"CodePatches: VIEWOBJ failed to hook AddViewObject at "
				"0x%08X.", static_cast<unsigned>(tva));
			return;
		}
		// The list ENUMERATOR, driven off Draw (vt+0x54) - this is the one
		// that cannot miss objects registered before we armed.
		if (!gDrawHooked)
		{
			void* dr = vt[0x54 / 4];
			const uintptr_t dva =
				reinterpret_cast<uintptr_t>(dr) - base + kImageBase;
			if (dva >= 0x401000 && dva <= 0xA80000
				&& MH_CreateHook(dr, reinterpret_cast<void*>(&RenderDrawDetour),
					reinterpret_cast<void**>(&gRenderDrawOrig)) == MH_OK
				&& MH_EnableHook(dr) == MH_OK)
			{
				gDrawHooked = true;
				Logger::Get().WriteLine(LogLevel::Info,
					"CodePatches: VIEWLIST armed on renderer Draw (vt+0x54 -> "
					"0x%08X); one full enumeration at frame 400.",
					static_cast<unsigned>(dva));
			}
			else
			{
				Logger::Get().WriteLine(LogLevel::Info,
					"CodePatches: VIEWLIST could NOT hook Draw (vt+0x54 = "
					"0x%08X) - enumeration absent.",
					static_cast<unsigned>(dva));
			}
		}
		gAddViewInstalled = true;
		Logger::Get().WriteLine(LogLevel::Info,
			"CodePatches: VIEWOBJ armed on cISC43DRender::AddViewObject "
			"(vt+0x80 -> 0x%08X). Two balloons on screen MUST produce "
			"registrations.", static_cast<unsigned>(tva));
	}

	void InstallPickProbe()
	{
		InstallViewObjProbe();
		if (gPickInstalled) { return; }
		const uintptr_t base =
			reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
		void* svc = *reinterpret_cast<void**>(base - kImageBase + 0xB43DD0);
		if (!svc)
		{
			Logger::Get().WriteLine(LogLevel::Info,
				"CodePatches: PICKPROBE render service null at PostCityInit "
				"- not installed (retries next city).");
			return;
		}
		void** vt = *reinterpret_cast<void***>(svc);
		void* target = vt[0x104 / 4];
		const uintptr_t tva =
			reinterpret_cast<uintptr_t>(target) - base + kImageBase;
		if (tva < 0x401000 || tva > 0xA80000)
		{
			Logger::Get().WriteLine(LogLevel::Info,
				"CodePatches: PICKPROBE Pick impl resolved outside the image "
				"(0x%08X) - not installed.", static_cast<uint32_t>(tva));
			return;
		}
		const MH_STATUS init = MH_Initialize();
		if (init != MH_OK && init != MH_ERROR_ALREADY_INITIALIZED)
		{
			Logger::Get().WriteLine(LogLevel::Error,
				"CodePatches: PICKPROBE MH_Initialize failed (%d).", init);
			return;
		}
		if (MH_CreateHook(target, reinterpret_cast<void*>(&PickDetour),
				reinterpret_cast<void**>(&gPickOrig)) != MH_OK
			|| MH_EnableHook(target) != MH_OK)
		{
			Logger::Get().WriteLine(LogLevel::Error,
				"CodePatches: PICKPROBE failed to hook Pick at 0x%08X.",
				static_cast<uint32_t>(tva));
			return;
		}
		gPickInstalled = true;
		Logger::Get().WriteLine(LogLevel::Info,
			"CodePatches: PICKPROBE armed on cISC43DRender::Pick impl "
			"0x%08X (runtime-resolved slot +0x104). Hover/click the balloon "
			"- PICKHIT lines name its class vtable.",
			static_cast<uint32_t>(tva));
	}

}
