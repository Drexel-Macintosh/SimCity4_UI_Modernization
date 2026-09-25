////////////////////////////////////////////////////////////////////////////
//
// UiSpikeFlyouts - the god- and mayor-mode tool flyouts:
//  - ScaleGodFlyouts, and the draw hooks it installs: the DRAW HOOK slot
//    thunks, the disaster flyout's blit hooks, the flash guard and the mouse
//    and hit-test thunks;
//  - the nested sub-flyouts: their geometry, the born-scale detours and the
//    hook installers; the first-level flyout open hook; the visibility trace;
//  - the MDOCK log latch, and the BATCHED ID LOOKUPS.
//
// Split out of UiSpike.cpp verbatim (audit B11, 2026-09-25). The hooks, the
// sub-flyouts and ScaleGodFlyouts share dozens of globals among themselves,
// so they moved as one file. What it shares with UiSpike.cpp is in
// UiSpikeInternal.h: a definition UiSpike.cpp also uses sits in a
// `namespace UiSpikeInternal` block where it always stood. The BATCHED ID
// LOOKUPS stay in one piece because tools/dev/idwalk builds them as a unit.
//
////////////////////////////////////////////////////////////////////////////

#include "UiSpike.h"
#include "UiSpikeInternal.h"
#include "UiSpikeIds.h"         // the window-id tables

#include "Logger.h"
#include "IniCache.h"           // the live-tune re-read
#include "RoundHalfUp.h"
#include "ExeBase.h"
#include "cIGZWin.h"
#include "cIGZBuffer.h"
#include "cIGZGraphicSystem.h"
#include "cISC4App.h"
#include "GZServPtrs.h"         // cISC4AppPtr
#include "MinHook.h"            // the sub-flyout and flyout-open detours

#include <cmath>
#include <cstdint>
#include <cstdio>               // sprintf_s
#include <cstdlib>              // atoi (the live-tune re-read)
#include <cstring>              // memset
#include <algorithm>            // std::min
#include <intrin.h>             // _ReturnAddress (the sub-flyout twin guard)
#include <set>
#include <Windows.h>            // SEH guards, VirtualProtect

using UiSpikeInternal::SafeAbsRect;
using UiSpikeInternal::SafeBufProbe;
using UiSpikeInternal::gGaugeEpoch;
using UiSpikeInternal::ChildSnapshot;
using UiSpikeInternal::LiveTuneIniPath;
using UiSpikeInternal::gChartProbe;
using UiSpikeInternal::gChartScale;
using UiSpikeInternal::ScaleRound;
using UiSpikeInternal::kFgMax;
using UiSpikeInternal::gTierF;
using UiSpikeInternal::gScaleAbbPanel;
using UiSpikeInternal::gReadyCount;
using UiSpikeInternal::gFgWaitRoot;
using UiSpikeInternal::gFgWaitN;
using UiSpikeInternal::healDoneStrip;
using UiSpikeInternal::healPhase;
using UiSpikeInternal::kFgThunks;
using UiSpikeInternal::gSpikeSelf;
using UiSpikeInternal::gSubLastStrip;
using UiSpikeInternal::gDisLastStrip;
using UiSpikeInternal::gDisDockValid;
using UiSpikeInternal::gDisChromeHealed;
using UiSpikeInternal::gDisDockLogged;
using UiSpikeInternal::gBornQN;
using UiSpikeInternal::EnsureBufferClassBltHook;
using UiSpikeInternal::gVisSeenN;
using UiSpikeInternal::gMDockLoggedN;
using UiSpikeInternal::gMayorRebirthLogs;

// ---- DRAW HOOK: per-instance GZPaint interception -------------------------
// The disaster flyout's circle and bar are PAINTED art, not windows: the
// DPROBE run recorded ZERO geometry changes across open/settle/hover even
// though the bar visibly jumps. And the container answers ONLY to base
// cIGZWin (no cIGZWinGen/BMP), so there is no supported image API. That
// leaves intercepting the paint.
//
// cIGZWin::GZPaint is virtual #85. cIGZUnknown contributes exactly 3 slots
// (QueryInterface/AddRef/Release) and NEITHER class declares a virtual
// destructor (verified in the headers), so GZPaint is vtable INDEX 87.
//
// THE LINE ABOVE IS WRONG FOR BUILD
// 1.1.641 AND HAS COST TWO WASTED LAUNCHES. Slot 87 is byte-IDENTICAL
// across all 23 live UI class vtables and disassembles to
//     mov eax,[ecx+0x4C]; ret        <- a two-instruction GETTER
// (slot 86 is its matching setter, mov [ecx+0x4C],arg; ret 4). It is not
// a paint entry, which is why hooking it 'installs cleanly and never
// fires' - for ANY class, not just the one under investigation. Do not
// re-derive this; the null looks identical to a broken instrument.
//
// THE REAL PER-CLASS DRAW IS SLOT 88. For the menu strip class
// 0x00AB6D88 that is 0x0079AA70, and it is the SOLE unique override in
// the whole 84..150 band (21 distinct implementations across 23
// classes). It is already thunked by SlotThunk2<88>, and its per-item
// blit is already intercepted by BltStripThunk on the draw context's
// slot 29 - a DIFFERENT CHANNEL from the class-wide BltClassThunk on
// 0x00AC1400[29]. Scoping a fix to the wrong one of those two is the
// single most repeated mistake in this file's history.
// cIGZWin declares 144 virtuals (147 slots); the concrete class adds its
// own, so the copy is oversized to 256.
//
// SAFETY: we swap the vtable pointer on the INSTANCE only, pointing it at a
// private copy. The shared class vtable (0x00AB6AA8) is never written, so no
// other window of that class is affected and the game's .rdata is untouched.
// This first iteration is OBSERVE-ONLY - it logs and calls the original.
namespace
{
	// GZPaint (idx 87) installed cleanly but NEVER fired, even after forcing
	// InvalidateSelfAndParents - so this window is not painted through its own
	// GZPaint virtual. Rather than guess one slot at a time, hook the whole
	// draw-related RANGE and see which the game actually calls.
	//
	// SAFETY: only slots whose real signature takes ZERO arguments may be
	// hooked this way. __thiscall is callee-cleanup, so a thunk declared with
	// the wrong arg count would clean the wrong number of stack bytes and
	// corrupt the stack.
	//
	// THE SLOT TABLE BELOW WAS OFF BY ONE UNTIL 2026-08-01, and it also
	// omitted slot 89 entirely, which is what shifted everything after it. It
	// cost a wasted probe build on task #89 (calling "93" as
	// GetBufferToDrawTo returned [+0x6c], the DRAW CONTEXT). Corrected from
	// the exe (1.1.641, base cGZWin vt 0x00A8D000; cSC4WinMiniMap vt
	// 0x00AB83B8 differs only at +0xDC and +0x160):
	//   87 (+0x15C) GZPaint                  0x0099BE4C
	//   88 (+0x160) Plot                     base 0x009A0A17 / minimap 0x007A79B0
	//   89 (+0x164) Draw                     0x0099BA07   <-- was MISSING
	//   90 (+0x168) CalcAbsoluteArea         0x0099DCE4
	//   91 (+0x16C) InvalidateSelf           0x0099BECC (= [ecx+0x70] = 1)
	//   92 (+0x170) InvalidateSelfAndParents 0x0099BED1
	//   93 (+0x174) GetDrawContext           0x0099BEF9 (= [ecx+0x6c])
	//   94 (+0x178) GetBufferToDrawTo        0x0099BEFD (= [ecx+0x68])
	//  100 (+0x190) PrivateBuffer(bool)      0x0099EA70  <-- NOT zero-arg
	//  101 (+0x194) GetPrivateBuffer         0x009D419D (= [ecx+0x64])
	//  123/124     PlotComposite/PlotPresent 0x0099E62D / 0x0099C498
	// Slot 89 Draw calls [eax+0x1EC] and only reaches [eax+0x1F0] if that
	// returned true - so a [win+0x64] private buffer CANNOT reach the screen
	// without a paint on the same object in the same call.
	// Our C++ InvalidateSelf() calls are unaffected: they land on 0x0099BECC.
	// Returning uintptr_t preserves EAX exactly for every one of them (the
	// void-returning slots simply have their garbage EAX ignored by the caller).
	typedef uintptr_t(__thiscall* SlotFn)(void*);
}

namespace UiSpikeInternal
{
	// ---- TIER MATH (v2.24.0 tier-generality pass, audit 2026-07-29) -------
	// Every 2x-hardwired constant in the hooks below became its derived form;
	// at f=2 each form reduces EXACTLY to the old constant; each hook
	// documents its own identity case.
	//
	// gTierF mirrors settings.spikeScaleFactor for these namespace-scope
	// hooks (settings is a UiSpike member and invisible here). Default 2.0f =
	// the legacy compiled assumption.
	// this comment used to claim
	// "hooks are only ever installed BY those sweeps", which has been false
	// since v2.32.0 - ArmDeferred installs four at PostCityInit, BEFORE any
	// sweep has written gTierF. Anything running from those hooks before the
	// first pass therefore sees the COMPILED DEFAULT, not the live tier -
	// which is why EarlyDockTick deliberately uses settings.spikeScaleFactor
	// and not gTierF. Consult the tier from settings in pre-sweep code.
	// IDENTITY DEFAULT, NOT 2.0f. This was `= 2.0f` and that is a LIE
	// whenever the tier is not 2x. gTierF is the hook-visible mirror of the tier
	// factor, read at 97 sites, but it was ASSIGNED at only two - inside
	// ScaleGodFlyouts and ScaleMenuFlyouts. So:
	//   * at 1x those never scale, gTierF stayed 2.0 for the whole process, and
	//     the DLL was NOT inert at the 1x baseline. MEASURED 2026-08-19:
	//       Settings ... ScaleFactor=1.00 / AutoScale: ... window 1024x768
	//       UiSpike: SUBBORN2 installed ... sub-flyouts are born x2.00, dock=1
	//     Sub-flyouts born at 2x inside a 1x layout is the broken docking the
	//     user photographed at 1x.
	//   * at EVERY tier, any hook that fires BEFORE those two functions reads
	//     2.0 regardless of the real factor. At 1.5x and 3x that is silently
	//     wrong rather than visibly wrong, which is worse.
	//
	// A DEFAULT THAT IS NOT THE IDENTITY TURNS "NOT YET KNOWN" INTO A
	// CONFIDENT WRONG ANSWER. 1.0f means "no scaling" - the only safe thing to
	// believe before the tier is decided. The real value is now pushed in
	// UNCONDITIONALLY by SetTierMirror() at the moment the tier is resolved,
	// so this initialiser should never be the value anything actually uses.
	float gTierF = 1.0f;
}

namespace
{
	// RoundHalfUp (floor(v + 0.5)) lives in RoundHalfUp.h, shared with
	// ScaleTier's icon code (audit B9).

	// A BLIT EXTENT MUST FLOOR, NEVER ROUND UP.
	//
	// THE DEFECT (reported 2026-08-06, and the wording is the diagnosis):
	// "the weird lines to the RIGHT and BOTTOM of the sun and moon". Right edge
	// and bottom edge ONLY - an L-shaped artefact, not a texture-wide one.
	//
	// Our two hand-written sprite blits (the disaster ring and the sub-flyout
	// ring, colour-keyed copies into the container buffer) sized their
	// destination as RoundHalfUp(srcExtent * f) and sampled with
	// floor(o / f). With an ODD source at f=1.5 that rounds UP:
	//     sw = 27  ->  27 * 1.5 = 40.5  ->  41 destination columns
	// but there are only 40 columns of real content. Column 40 re-samples the
	// last source column and lands one pixel outside where the ring belongs -
	// a stray line down the RIGHT edge. The height does the same on the BOTTOM.
	// Rounding UP manufactures a pixel that has no source.
	//
	// WHY 2x AND 3x ARE PERFECT, AND WHY THIS IS 1.5x-ONLY: at an integer
	// factor srcExtent*f is already whole, so floor and round agree exactly and
	// no phantom column can exist. Same shape as #142 (font point sizes) and
	// the strip step-extra (5*1.5 = 7.5): a rule that only misbehaves where the
	// product is fractional. Integer tiers are BIT-IDENTICAL under this change.
	//
	// MEASURED DEAD, DO NOT RETRY: the first attempt at this symptom rewrote
	// the SAMPLER to map by the real size ratio (o*src/dst, the Upscale2x
	// method). It compiled, shipped, and the player reported it made "a lot of
	// fields worse" - it changes the duplication pattern across the WHOLE
	// sprite when the defect is only at the two trailing edges. Reverted the
	// same session. The extent was the bug, not the mapping.
	inline int FloorScale(int v, float f)
	{
		return static_cast<int>(std::floor(v * static_cast<double>(f)));
	}

	// Sentinel for live-tune ini overrides: "value not set in the ini" =
	// derive from gTierF. Any real override is far inside +-1000000.
	const int32_t kIniAuto = -1000000;

	SlotFn gOrigSlot[128] = {};
	int gSlotHits[128] = {};
	void* gVtCopy[256] = {};
	int gForceInvalidate = 0;

	// Second vtable copy for the disaster STRIP window (vtable 0x00AB6D88).
	// The container (vtable 0x00AB6AA8) uses gVtCopy above; the strip is a
	// different class so it needs its own copy to avoid clobbering.
	SlotFn gOrigSlot2[128] = {};
	int gSlotHits2[128] = {};
	void* gVtCopy2[256] = {};

	// Click-path hooks on the strip (cIGZWin vtable indices): 120/121 =
	// IsPointInWindow{Window,Parent}Coordinates (the window-level hit-test),
	// 133 = GZOnMouseDownL (the list's click handler). Different signatures
	// than SlotFn, so they get dedicated typed originals.
	typedef bool(__fastcall* MouseFn)(void*, void*, int32_t, int32_t, uint32_t);
	typedef bool(__fastcall* PtInFn)(void*, void*, int32_t, int32_t);
	// Slots 136 & 138 are the VERIFIED list-specific 3-arg mouse handlers (ret
	// 0xc). 136 commits+fires the selection; 138 computes item-from-Y. Hooking
	// these is safe (correct 3-arg signature); slot 133 was a 1-arg stub (crash).
	MouseFn gOrigMouse136 = nullptr;
	MouseFn gOrigMouse138 = nullptr;
	// Slot 121 IsPointInWindowParentCoordinates (verified 2-arg): the container
	// calls this to decide if the cursor is over the strip. Log what it's asked
	// and what it answers to see whether IT rejects the left half.
	PtInFn  gOrigPt121 = nullptr;
	// Slot 149 [vtbl+0x254] (verified 2-arg, ret 8): the strip's REFINED per-item
	// hit-test. Its IsPointInMe (slot 62) calls this (when MouseTrans) to narrow
	// the coarse 0x14 rect down to the actual 1x icon -> only the right half is
	// clickable. Force it to accept, so the whole (0x14-covered) picture clicks;
	// item is still picked by Y in handler 138. gSelForce toggles it (live).
	// Default ON with gClickHook - see that flag's comment. Without this the
	// slot-149 hook installs but Slot149Thunk just calls through, so the
	// narrowed 1x hit region survives even with the container claim widened.
	PtInFn  gOrigSlot149 = nullptr;
	int     gSelForce = 1;
	// Slot 62 IsPointInMe (0x0099C97C, base, 2-arg): the routing's actual
	// "is the cursor in the strip" test. Log its (x,y)+answer for left vs right
	// hovers to resolve why only the right half routes here.
	PtInFn  gOrigSlot62 = nullptr;
	// Slot 59 [vt+0xec] WindowToScreenCoordinates(int32&x, int32&y): the coord
	// transform IsPointInMe runs on the cursor before the rect test. Log in->out
	// to MEASURE the ~45px offset that shifts the hit-test right of the draw.
	typedef bool(__fastcall* XformFn)(void*, void*, int32_t*, int32_t*);
	XformFn gOrigSlot59 = nullptr;
	// ⭐ DEFAULT FLIPPED TO ON (this build). Originally 0 pending verification -
	// "SDK vtable slot numbers past ~97 may not match the game and CRASHED" -
	// but the DVT dump DID verify them (see the install site's own later
	// comment: "Click-path hooks on the VERIFIED 3-arg list handlers (136
	// commit+fire, 138 pick-from-Y). Safe signatures."), on this exact class,
	// years before this default was ever revisited. No shipping ini - not the
	// packaging template, not the live dev ini on this machine - has ever set
	// ClickHook=1, so the fix these thunks implement has been DORMANT since
	// the day it was verified: on the disaster flyout's own "LOCKED" install
	// site as much as the sub-flyout fallback below. That is the mechanism
	// behind "an old issue has come back" - it was never actually shipped
	// live in the first place, only proven safe once in a hand-edited ini.
	// Still overridable via [Disaster] ClickHook= in the ini if a future
	// game patch ever moves these vtable slots again.
	int     gClickHook = 1;           // installs the 62/59/136/138/121/149 click hooks
	// THE CLICK GATE (v2.11.24, found by full offline disasm): the CONTAINER
	// overrides IsPointInMe (0x0079A180) to tail-call its slot 121 (0x0079AE30),
	// which claims the point ONLY when x >= (width - [this+0xe0]) - i.e. the
	// RIGHTMOST [0xe0] px = the strip column, stored as width-from-right-edge.
	// [0xe0] still holds the 1x strip width (~44/49) while the draw is 2x, so
	// routing dies at the container for the left half of the pictures - which
	// is also why the strip's DS62/DS149 hooks stayed silent there. Fix: scale
	// [0xe0] by gClaimScale (2 = double). Idempotent via a sane-range guard;
	// if the game recomputes the field back to 1x, the sweep re-applies it.
	int     gClaimScale = 2;          // 0/1 = off; >1 = scale [container+0xe0] by the
	                                  // TIER factor (v2.24.0: the ini value is an
	                                  // ENABLE flag now, not the multiplier - atoi
	                                  // of "1.5" is 1, so an integer multiplier
	                                  // could never be fractional; audit A6).
	                                  // Default ON with gClickHook/gSelForce - the
	                                  // three levers are load-bearing together;
	                                  // see gClickHook's comment.
	int32_t gClaimOrig = 0;           // the 1x claim width we scaled (latched by the
	                                  // sweeps); the draw group restores exactly this
	                                  // value instead of dividing by an int factor
	// FLASH GUARD (v2.11.26): the player must NEVER see the stock 1x (or half-
	// transformed "garbled") first paint of a god flyout. Class-vtable Plot
	// patch (FlashGuardThunk<K>) suppresses painting of any god-flyout window
	// until the sweep marks its ROOT (the direct child of 0x9A47B417) fully
	// docked+transformed in gReadyWins - sticky per city, cleared in Disarm
	// (v2.23.3; NOT rebuilt per sweep, see ScaleGodFlyouts). Fail-open: a
	// root left pending ~120 suppressed paints (an unmanaged flyout) paints
	// stock anyway rather than staying invisible.
	// DEFAULT OFF (v2.11.28). v2.11.26/27 REGRESSED the city HUD: the guard
	// suppresses by walking <=4 parents for id 0x9A47B417, but that parent is
	// an ancestor of far more than the flyouts, and the 4-slot fail-open table
	// thrashes when several windows contend - so unrelated HUD windows (the
	// bottom-left date/City Name panel) got permanently unpainted (black box,
	// missing art). Suppressing paint is too blunt: the correct fix for the
	// open-flash is to make the flyout SCALED BEFORE IT IS SHOWN (or keep it
	// hidden for the frame we transform it), not to blank arbitrary windows.
	// Kept in-tree, disabled, as the record of what not to repeat.
	int     gFlashGuard = 0;          // ini [Disaster] FlashGuard (default OFF)

	// DPROBE band, live-tunable via ini [Probe] (v2.12.0). The band was
	// hardcoded to the GOD flyout column (the bottom query panels animate
	// constantly and drowned the signal), but Mayor-mode menus open outside
	// that column, so the probe has to be aimable without a rebuild. Defaults
	// reproduce the god-mode band exactly.
	// v2.69.3: default OFF. The compiled default used to be 1, which meant a
	// SHIPPED install (whose clean ini has no [Probe] section at all) ran the
	// DPROBE band walk and the MPROBE main-window diff every 16 ms forever -
	// pure instrument cost for a user who can never consume the output. The
	// dev machine is unaffected: its ini says [Probe] Enabled and that is
	// read at startup (and re-read under LiveTune=1). Flagged by the v2.69.x
	// adversarial review's perf sweep as a shipped-install blocker.
	int     gProbeOn = 0;             // 1 = probes on (dev ini opts in)
	int     gIconProbe = 0;           // task #149 ICONPROBE, dev ini, default OFF
	int     gSmallWin = 0;            // #188 SMALLWIN bubble hunt, default OFF

	// WIDEWATCH counters live here, ahead of EVERY channel that touches them
	// (slot 20 at ~:428 and BltClassThunk at ~:1683 both come before the
	// WIDEWATCH block itself).
	unsigned gW_strip = 0;    // BltStripThunk, dest overlaps a plaza cell
	unsigned gW_stripSub = 0; // ... and we substituted the enlarged surface
	unsigned gW_class = 0;    // BltClassThunk (shared buffer class)
	unsigned gW_s20 = 0;      // slot 20 private-buffer present
	unsigned gW_present = 0;  // PlotPresent 0x0099C498 for ANY window
	unsigned gW_dump = 0;
	int gKickLeft = 0;   // frames of forced redraw after a substitution

	inline bool InPlazaCell(const int32_t* d)
	{
		if (!d) { return false; }
		return (d[0] < 88 && d[2] > 0)
			&& ((d[1] < 480 && d[3] > 392) || (d[1] < 578 && d[3] > 490));
	}

	int     gIconFit = 0;             // task #149 ICONFIT centre-stretch, default OFF
	int     gIconHook = 0;            // task #149 ICONHOOK, dev ini, default OFF
	int     gIconHookLog = 24;        // bounded log budget
	void*   gIconVtCopy[160] = {};    // per-INSTANCE vtable copy for the menu column
	void*   gIconPaintOrig = nullptr; // original slot-87 (GZPaint) target
	
	// ICONHOOK (task #149). The menu column is painted by a THIRD-PARTY
	// DLL class (vt 0x6E247500 in one capture - a DLL base, so it is NOT a
	// stable address and must never be hard-coded). The icons do not pass
	// through BltClassThunk at all: an ICONFIT run that would have matched
	// bmp 176x44 / src 88 / dst 88 logged NOTHING for them, while firing on
	// unrelated full-bitmap blits. So the shared buffer class is the wrong
	// hook point, and this is the right one - scoped to ONE window instance
	// so it cannot spray across the UI the way the shared-class edit did.
	//
	// Installed by swapping the INSTANCE's vtable pointer to a private copy
	// (never the shared class vtable - same rule as gVtCopy / gBmpVtCopy).
	// GZPaint is vtable INDEX 87 (see the note at the top of this file).
	// PASS-THROUGH FOR NOW: it calls the original and logs. That makes it a
	// measurement of whether we are even on the paint path before anything
	// touches pixels - the previous attempt skipped that step and shipped a
	// visible regression.
	int __fastcall IconColPaintThunk(void* self, void* edx, void* a1, void* a2)
	{
		if (gIconHookLog > 0)
		{
			gIconHookLog--;
			Logger::Get().WriteLine(LogLevel::Info,
				"UiSpike: ICONHOOK paint fired on column self=%p (orig=%p)",
				self, gIconPaintOrig);
		}
		typedef int (__fastcall *PaintFn)(void*, void*, void*, void*);
		if (!gIconPaintOrig) { return 0; }
		return reinterpret_cast<PaintFn>(gIconPaintOrig)(self, edx, a1, a2);
	}
	int     gIconFitLog = 12;         // bounded log budget for ICONFIT
	int     gIconCover = 1;           // task #149: pre-fill the cell (default ON with ICONCENTRE)
	// ICONTALLY (task #149): UNBOUNDED counters. Both log probes are budget
	// capped, so 'willCut=1 every time' only ever described the frames that
	// were still being logged - which cannot distinguish 'always cuts' from
	// 'cuts while logging is on', and that distinction IS the flicker.
	// Counters cannot saturate the way a line budget can (law 41).
	unsigned gTalStrip = 0;   // every 4-state strip blit seen
	unsigned gTalCut   = 0;   // ... that we re-cut
	unsigned gTalCover = 0;   // pre-fill blits issued
	unsigned gTalDump  = 0;
	// ICONWATCH (task #149): the plaza cell is drawn by SOMETHING we do not
	// intercept. Proven: one draw context (ctx=02F64D14, all 89 blits),
	// cut+skip==strip every dump, cut is exactly the 2 plaza items - so every
	// blit reaching BltStripThunk IS corrected, yet two uncorrected icons
	// remain on screen and vanish on hover (their source goes off-texture at
	// state 3). Watch BOTH blit channels for anything landing in that cell,
	// tagged by channel, so the other path names itself.
	unsigned gWatchLog = 40;
	// ---- PRESENTWATCH (task #149) -------------------------------------
	// WHY: five instruments all reported 'every plaza blit corrected' while
	// the screen showed uncorrected art. Static analysis of the exe found
	// the reason: the menu strip owns a PRIVATE BUFFER (its slot 192,
	// 0x0079BDC0, calls PrivateBuffer(true)), so the item draw writes into
	// that buffer - not the screen. The buffer then reaches the screen by
	// routes that DO NOT USE BUFFER SLOT 29, the only slot we hook:
	//   0x0099BA3E  -> slot 20 (+0x50), its own 16bpp pixel loop
	//   0x0099C498  -> PlotPresent, primary call [eax+0x98] (renderer)
	// Our probes were blind BY CONSTRUCTION. This watches slot 20 on BOTH
	// known buffer classes so the present path stops being invisible.
	//
	// LOG ONLY - it calls the original and changes nothing. Its job is to
	// decide which lever step 2 uses, not to fix anything.
	//
	// POSITIVE CONTROL: gS20Any counts EVERY slot-20 call for ANY window.
	// If gS20Any is 0 the thunk never ran and a silent 'no plaza present'
	// is an instrument failure, not a finding.
	void** const kBufClassVt2 = reinterpret_cast<void**>(0x00ADB418);
	// plain globals: MSVC inline asm resolves these by bare name
	void* gS20Orig0 = nullptr;
	void* gS20Orig1 = nullptr;
	unsigned gS20Any = 0;
	unsigned gS20Cell = 0;
	unsigned gS20Log = 24;

	// THE FIRST VERSION OF THIS CRASHED THE GAME (PRIV_INSTRUCTION at a
	// garbage EIP, EDX still holding 0x00AC1400 - a return into nowhere).
	// It declared slot 20 as __fastcall with TWO stack args, inferred from
	// two visible pushes. __thiscall is CALLEE-CLEANUP: guess the arity
	// wrong and the thunk cleans the wrong number of bytes and unwinds the
	// stack into garbage. THIS FILE ALREADY SAYS SO at the SlotThunk note:
	// only ZERO-arg slots may be hooked by a typed thunk.
	//
	// A NAKED TAIL JMP makes no arity assumption whatsoever: it never
	// returns to us, so it never cleans anything. ecx/edx/the argument
	// stack pass through byte-identical. Same pattern as X8DispatchStub in
	// CodePatches.cpp. We read the dest rect from [esp+8] (arg2, the rect
	// pointer per the call site) WITHOUT disturbing the frame.
	void S20Note(void* rect)
	{
		gS20Any++;
		if (!rect) { return; }
		const int32_t* d = reinterpret_cast<const int32_t*>(rect);
		const bool inCell = (d[0] < 88 && d[2] > 0)
			&& ((d[1] < 480 && d[3] > 392) || (d[1] < 578 && d[3] > 490));
		if (!inCell) { return; }
		gS20Cell++;
		gW_s20++;
		if (gS20Log == 0) { return; }
		gS20Log--;
		Logger::Get().WriteLine(LogLevel::Info,
			"UiSpike: PRESENTWATCH slot20 dst(%d,%d,%d,%d) %dx%d - a PRIVATE "
			"BUFFER present over the plaza cell, the channel every slot-29 "
			"hook was blind to",
			d[0], d[1], d[2], d[3], d[2]-d[0], d[3]-d[1]);
	}
	__declspec(naked) void Slot20Thunk0()
	{
		__asm pushad
		__asm mov eax, [esp+0x28]
		__asm push eax
		__asm call S20Note
		__asm add esp, 4
		__asm popad
		__asm mov eax, gS20Orig0
		__asm jmp eax
	}
	__declspec(naked) void Slot20Thunk1()
	{
		__asm pushad
		__asm mov eax, [esp+0x28]
		__asm push eax
		__asm call S20Note
		__asm add esp, 4
		__asm popad
		__asm mov eax, gS20Orig1
		__asm jmp eax
	}
	// gIconCentreOff (task #149): isolate whether MOVING the dest is what
	// flickers. Everything else is proven: one context, every plaza blit
	// corrected, plaza cells drawn exactly as often as their neighbours
	// (cut:skip = 50:150 = 2 items : 6 items). The only variable we
	// introduce besides the source cut is the dest OFFSET. 1 = cut the
	// source but leave the dest at the cell origin (icon lands top-left).
	// If the flicker stops, the offset is the trigger; if it persists, the
	// source cut alone is enough to cause it and the cause is elsewhere.
	int gIconCentreOff = 0;
	void IconWatch(const char* chan, void* ctx, const int32_t* s, const int32_t* d)
	{
		if (gWatchLog == 0 || !s || !d) { return; }
		// the two plaza rows measured live: dst x 0..88, y 392..480 and 490..578
		const bool inCell = (d[0] < 88 && d[2] > 0)
			&& ((d[1] < 480 && d[3] > 392) || (d[1] < 578 && d[3] > 490));
		if (!inCell) { return; }
		gWatchLog--;
		Logger::Get().WriteLine(LogLevel::Info,
			"UiSpike: ICONWATCH [%s] ctx=%p src(%d,%d,%d,%d) %dx%d "
			"dst(%d,%d,%d,%d) %dx%d",
			chan, ctx, s[0], s[1], s[2], s[3], s[2]-s[0], s[3]-s[1],
			d[0], d[1], d[2], d[3], d[2]-d[0], d[3]-d[1]);
	}
	int     gProbeL = -150;           // band in ABSOLUTE screen px
	int     gProbeR = 500;
	int     gProbeT = 380;
	int     gProbeB = 1250;
	int     gProbeMax = 30;           // max DPROBE lines per sweep
	int     gAdvisorHeal = 0;         // FALLBACK ONLY (default OFF as of
	                                  // v2.20.0): one-shot advisor face
	                                  // re-frame via synthesized face+back
	                                  // clicks. Replaced by the data
	                                  // pre-scale (kDataScaledSubtreeIds),
	                                  // which needs no injected input and has
	                                  // no visible flash. Kept as an escape
	                                  // hatch if that ever regresses.

	// MAYOR-mode flyout docking (kMayorFlyoutDock), ini [Flyout] MayorDock.
	// 0 = MEASURE: never move a mayor flyout, just report its native placement
	// and the derived offset via the MCAL log line. 1 = apply the dock for
	// entries whose offsets have been measured (derived=true).
	// Replaced LandDX/LandDY/LandDock, which were screenshot-tuned nudges
	// layered on the WRONG anchor (the god toolbar) - see kMayorFlyoutDock.
	// #95 PHASE 4 (2026-08-02): DEFAULT FLIPPED 0 -> 1. Every row in
	// kMayorFlyoutDock is derived=true and has been confirmed on screen, and
	// NO redistributable ini carries a [Flyout] section - so the old
	// default meant a FRESH INSTALL scaled mayor flyouts but never docked
	// them (they sat at the game's native placement while their spawn
	// buttons had moved). The live machine has run MayorDock=1 for weeks;
	// 0 is now the MEASURING escape hatch, which is the right way round.
	int     gMayorDock = 1;

	// DISASTER-SPECIFIC draw tuning (the ring 2x atlas upscale and the bar
	// shift/widen inside BltClassThunk) applies ONLY to the disaster flyout.
	// Those offsets - RingDX/RingDY/BarDX/BarW - were measured for THAT window.
	// BltClassThunk identifies its target by a SIZE heuristic (destIsContainer:
	// h>300, 150<w<700), and the zone-density sub-flyout's buffer (258x482)
	// passes it too, so without this gate the disaster offsets get applied to a
	// window they were never measured for - which is exactly the bar and icons
	// sitting too far right, not touching the connector.
	// 1 while the disaster container is the hooked instance, 0 while the shared
	// sub-flyout container is. They are never live at the same time (disaster is
	// god mode, sub-flyouts are mayor mode). The generic fixes - buffer
	// force-recreate and the strip item-field doubling - stay ON for both.
	int     gDisasterDrawTuning = 1;

	// SBLT trace: log every blit into the sub-flyout container's buffer so the
	// tile offsets can be COMPUTED offline. ini [Flyout] SubBltLog.
	int     gSubBltLog = 0;

	// EVTP/EBLT (v2.17.4): recon for the EMERGENCY flyout's 496-wide picture
	// panel 0x2992FD21 (1x dispatch pictures; none of the existing hooks see
	// it). ini [Flyout] EmergLog. Diagnostic only.
	int     gEmergLog = 0;

	// RCAL: log ring-sized blits + their dest buffer, to establish whether the
	// mayor flyout circles are PAINTED art or WINDOW art. ini [Flyout] RingCal.
	int     gRingCalLog = 0;
	// Sub-flyout ring nudge, BUFFER px, live-tunable via ini [Flyout]
	// SubRingDX/SubRingDY. kIniAuto = derive from the tier; a value in the ini
	// overrides (0 draws the sprite at the game's own origin).
	//
	// #134: these were plain ints defaulting to 0 and carrying HAND-ENTERED
	// ini values, which is why one file could not be right at more than one
	// tier. They are now DERIVED by the same feature-alignment chain that
	// tools\flyout-sim\derive_subring.py documents: seat the ring's magenta
	// HOLE centre (25,26 in the 1x sprite) on the button's ELLIPSE centre
	// (21,15 in the 1x cell). Substituting the native and dock laws, the
	// container's own offset CANCELS out of both axes, leaving:
	//
	//   SubRingDX(f) = rhu(21f) - rhu(25f) - rhu(-16.5f)
	//   SubRingDY(f) = rhu(15f) - rhu(37f)/2 + rhu(26.5f) - rhu(26f)
	//
	//        f=1.5      f=2 (SHIPPING, confirmed on screen)      f=3
	//   DX:    19        25  <- reproduces the ini exactly   37
	//   DY:    -4        -6  <- reproduces the ini exactly   -8
	//
	// The f=2 column is the gate: it must equal the values 2x shipped with, or
	// this derivation is wrong and a confirmed on screen tier has been disturbed.
	// Test-SubRingLock asserts exactly that.
	int     gSubRingDX = kIniAuto;
	int     gSubRingDY = kIniAuto;
	// #135: DERIVES TO ZERO, ON PURPOSE, AT EVERY TIER.
	// The ring sprite's right edge is the strip's left edge (both are 80f in
	// the buffer) - they are ONE shape, and the connector wedge lives in the
	// ring's right half. Any non-zero X nudge pushes that wedge into the panel
	// and leaves its two border lines ending in mid-air: the junction seam.
	// The alignment the old nudge was doing is now carried by SubDockDXEff(),
	// which moves the WHOLE assembly and so keeps the weld intact.
	// Do not "restore" a non-zero default to re-seat a ring. If the ring is
	// off its button, the DOCK is wrong - fix that. An ini override still
	// works for diagnosis, but it reopens the seam by construction.
	inline int SubRingDXEff()
	{
		return gSubRingDX != kIniAuto ? gSubRingDX : 0;
	}
	inline int SubRingDYEff()
	{
		return gSubRingDY != kIniAuto ? gSubRingDY
			: RoundHalfUp(15.0 * gTierF) - RoundHalfUp(37.0 * gTierF) / 2
				+ RoundHalfUp(26.5 * gTierF) - RoundHalfUp(26.0 * gTierF);
	}

	// ---- #95: THE OTHER HALF OF THE PLACEMENT (v2.46.0) ----------------
	// MEASURED, not inferred (tools\flyout-sim\emu_plot.py, 2026-08-02):
	// the ring+stem sprite's y inside the container is the object's [0x100]
	// and NOTHING else. Four runs with 0x100 = 138 / 200 / 0 / 417 moved the
	// ring blit to exactly that y, while the three BAR rects stayed
	// byte-identical; changing [0xF4] 6->12 moved nothing. So the stem Y is a
	// FREE variable that cannot disturb the strip - which is precisely what
	// the player described: "the flyout never moves, just where it attaches in
	// the list should".
	//
	// v2.45.0 moved the container to the game's clamped position and left the
	// ring latched, so the ring slid off its button by the distance moved and
	// was reverted the same session. These carry the compensating term: the
	// container goes where the game's own math says, and the ring sprite is
	// offset by exactly the move, so it lands where it lands TODAY - a
	// position confirmed exact by SUBGEO (ring centre == button centre) and
	// by the player's eyes. gSubRingDX/DY stay the USER's ini nudges; these are
	// ours, and they are ZERO whenever SubMath is off, so SubMath=0 remains
	// bit-identical to v2.45.2.
	int     gSubRingAutoX = 0;
	int     gSubRingAutoY = 0;

	// BIRTH OWNS THE DOCK (2026-09-25). When SubPlaceDetour docks a container it
	// records the three decisions it made for this open - WHICH button spawned
	// it (the game's own Place() anchor cy), WHERE it put the container, and the
	// ring pin (gSubRingAutoY) - and the sweep REUSES them for that container
	// instead of re-deriving them. Re-deriving was the defect: the sweep's older
	// placement formula (SubPlaceTop minus the SubContainerShiftFromGeo shift)
	// disagrees with birth's SubPlaceTopMb, so its +-3 px candidate match either
	// found no button (6+ item strips: dead back-arrow zone) or claimed the
	// NEIGHBOUR and rewrote the ring pin for it (the 5-item memo.submenus power
	// strip at 3x: ring + back arrow jump one row down to Water whenever the
	// container repaints). Gate: _tests\Test-SubBirthOwnsDock.py.
	// Both frames are the container's PARENT frame (what Place() and GetT use).
	// Cleared on every Place() of the container, so one open's record can never
	// reach another (container addresses are recycled - see REBIRTH).
	cIGZWin* gSubBornWin = nullptr;
	int32_t  gSubBornCy = 0;        // Place() anchor = the spawn button's centre y
	int32_t  gSubBornTopRel = 0;    // container top after the birth dock
	int32_t  gSubBornAutoY = 0;     // the ring pin birth chose
	int32_t  gSubBornH = 0;         // container height the record belongs to
	int      gSubOwnLog = 0;        // SUBOWN verdict line, once per open

	// Live record of the sub-flyout ring blit (v2.16.0). The game blits the 1x
	// ring sprite at a DIFFERENT buffer y per menu (94 zones/roads, 119 rails
	// - measured via RCAL 2026-07-29) and its native container placement
	// follows that y, so the dock must know the CURRENT menu's value. The ring
	// draw records it here, tagged with the buffer size so a stale value from
	// the previous menu is never applied to the wrong window (blits fire every
	// frame vs the 4x/sec sweep, so "stale" self-corrects within a frame).
	int     gSubGeoLog = 0;   // #95: SUBGEO assembly dump, 8 lines max
	// FIX (2026-08-23 review): SUBGEO2 used to share gSubGeoLog with the
	// original SUBGEO above - two consumers incrementing one counter meant
	// adding SUBGEO2 silently halved SUBGEO's documented 8-line budget
	// (both hit the shared cap after ~4 lines each). Separate counter,
	// same per-open reset site (SubPlaceDetour's birth hook).
	int     gSubGeo2Log = 0;  // SUBGEO2 dump, independent of gSubGeoLog, 40 lines max
	// STRIP SHIFT (v4.0.27): vertical shift of the sub-flyout strip window
	// (and its icons) inside the container, in DESIGN ROWS (1 row = 49px:
	// item 44 + spacing 5). Negative = up. This is the disaster-arc pattern:
	// the dock/ring never moves; the strip and icons move to meet it.
	// Build Park: stock arm meets row 7 ("Tourist Trap"); unpinned layout
	// put row 5 ("Marina") -> shift = -2 rows. ini [SubFlyout]
	// StripShiftRows: RETIRED (v4.0.30) - moving the strip independently
	// breaks bar+strip alignment. ContainerShiftRows/Fine (v4.0.31): RETIRED
	// (v4.0.33), replaced by SubContainerShiftFromGeo(). Their never-read
	// globals and ini reads were removed in the 2026-09-25 audit (B1).
	// #134: SUBGEO sits AFTER the atNative/atTarget gate, so a container the
	// sweep does not recognise logs nothing at all - which is exactly the case
	// that needs explaining. SUBCAND logs every candidate button BEFORE that
	// gate, so the button's absolute X is recorded whether or not the sweep
	// claims it. That absolute X is the one unmeasured term in the ring law:
	// kSubNativeDX (the game's own native container offset) was measured at
	// f=2 and ASSUMED factor-independent, and 3x says otherwise.
	// ⚠ Since 2026-09-25 a BORN container logs only its anchor button here
	// (the birth-owns-the-dock filter runs first, because every candidate of
	// a born container shares birth's target and would otherwise "match"); an
	// anchor that matches nothing is reported by the SUBOWN negative line.
	int     gSubCandLog = 0;  // #134: pre-gate candidate dump, 24 lines max
	int     gSubShiftLog = 0; // SUBSHIFT diagnostic, independent counter
	int     gSubRingBltX = -1;
	int     gSubRingBltY = -1;
	int     gSubRingBufW = -1;
	int     gSubRingBufH = -1;

	// ---- BACK-ARROW CLICK FORWARD (v2.17.0) ---------------------------
	// The submenus mod (memo.submenus.dll) bakes a red back arrow into the
	// ring-box of its menu-frame art (its five 292x53 frame atlases
	// 0xAC581B70..74; arrow measured (52,14)..(62,38) at 1x, widest frame),
	// and its "back" action is A CLICK ON THE PHYSICAL MENU BUTTON (source:
	// Hook_HandleButtonActivatedReopen in submenus-dll). At 1x the two
	// coincide - the arrow art overlaps the button. Our 2x ring draw pushes
	// the visible arrow just past the button's right edge, where clicks fell
	// into dead space (proven live: a whole session of arrow-clicking fired
	// DHIT136 only twice). Fix: claim the drawn arrow's rect through the
	// routing chain (container slot 121 -> strip slot 62/149) and, at the
	// strip's commit handler (136), synthesize a REAL OS click at the
	// selected button's centre (SetCursorPos + posted down/up - the same
	// same input style a real click produces), so the mod's own back/close logic
	// runs. The button centre is structurally OUTSIDE the arrow zone
	// (centre = btn+47, zone starts at btn+80 for ringBltX=0), so the
	// forwarded click cannot re-enter this path.
	// Arrow art bounds inside the 80x53 ring-box, 1x sprite px, plus click
	// margin: x 48..66, y 10..44.
	const int kSubArrowX0 = 48, kSubArrowX1 = 66;
	const int kSubArrowY0 = 10, kSubArrowY1 = 44;
	int     gArrowClick = 1;                     // ini [Flyout] ArrowClick
	int     gSubArrowAbs[4] = { 0, 0, -1, -1 };  // abs l,t,r,b; r<l = invalid
	int     gSubBtnCX = -1;                      // selected button centre, abs
	int     gSubBtnCY = -1;

	// Sub-flyout CONTAINER dock delta, SCREEN px, ini [Flyout] SubDockDX/DY.
	// The game places the container per the PLACEMENT LAW below (its 1x ring
	// sprite centred on the button). Once the ring is drawn at 2x the whole
	// assembly must shift so the ring's HOLE lands back on the button; for the
	// zones menu (ring blitted at (0,94)):
	//   ring centre = container + (0,94) + (80,53) = btn + (100,61)
	//   button centre = btn + (47,37)   =>  delta (-53,-24)
	// The delta is the SAME for every menu regardless of where its ring sits
	// in the buffer - native and target both shift with ringBltY, so their
	// difference cannot depend on it.
	// Applying that delta to the RING alone centres it but tears it off the
	// strip/bar, which are already welded to it inside the buffer (ring 0..160,
	// strip 160..248, bar 152..258). Applying it to the CONTAINER moves the
	// whole assembly together, so the ring seats on the button AND stays joined.
	// v2.24.0 (audit B6): the shipped -53/-24 were the f=2 evaluation of the
	// geometry above - half-sprite (40,26.5) and half-cell (23.5,18.5) design
	// units scaled by f, plus the factor-independent native offsets:
	//   dockDX(f) = RoundHalfUp((23.5 - 40) * f) - SubNativeDX()
	//             = RoundHalfUp(-16.5 * f) - 20      -> f=2: -33 - 20 = -53
	//   (#134: the second term is SubNativeDX(), which is 20 only at f=2)
	//   dockDY(f) = kSubPlaceBias - RoundHalfUp(26.5 * f)
	//             = 29 - RoundHalfUp(26.5 * f)       -> f=2: 29 - 53  = -24
	// (the ring is drawn at f x 80x53, so its half box is (40f, 26.5f); the
	// button cell is f x 47x37, half (23.5f, 18.5f); the native law already
	// contains SubNativeDX()/kSubPlaceBias).
	// #134: this block used to end "both factor-independent". kSubPlaceBias
	// is (re-verified at f=3); SubNativeDX is NOT, and believing that comment
	// is what kept 3x broken. Do not restore the claim.
	// kIniAuto = derive from the tier factor; a value in the ini overrides.
	int     gSubDockDX = kIniAuto;
	int     gSubDockDY = kIniAuto;
	// THE PLACEMENT LAW (measured 2026-07-29, residual ZERO on both menus
	// checked - zones ring y=94: 274 = 397-94-29; rails ring y=119:
	// 549 = 697-119-29):
	//     nativeX = buttonAbsX + SubNativeDX()   (= btnW/2 - 27)
	//     nativeY = buttonCentreY - ringBltY - kSubPlaceBias
	// The old constant kSubNativeDY=-86 was this law evaluated at ringBltY=94;
	// it silently failed every menu whose ring sits elsewhere (rails & depots,
	// and three more transport menus). The dock DELTA (SubDockDX/DY) is the
	// same for every menu: native and target both shift with ringBltY, so
	// their difference cannot depend on it.
	// #134 (2026-08-05): this was `const int kSubNativeDX = 20`, described as
	// "factor-independent". IT IS NOT, and 20 is merely its f=2 evaluation.
	// MEASURED live by SUBCAND at 3840x2160 (tier 3.00): the game places the
	// sub-flyout container at BTN(237) + 43 = 280, not 237 + 20 = 257. The
	// button cell is 47x37 at 1x, so at f=3 it is 141x111, and
	//     141/2 - 27 = 43      (f=3, measured)
	//      94/2 - 27 = 20      (f=2, the shipped constant, reproduced EXACTLY)
	// i.e. the game seats the container 27px left of the button CENTRE, and
	// that 27 is UNSCALED - the same shape as kSubPlaceBias below, which is
	// likewise unscaled and was already verified on two menus.
	//
	// NOTE the halving is on the SCALED width, not the design width:
	// RoundHalfUp(47f)/2 gives 70 at f=3 (141/2), whereas RoundHalfUp(47f/2)
	// would give 71 and miss the measurement by 1. That is the project's
	// standing (a>>1)-(b>>1) rounding law, not a coincidence.
	//
	// WHAT THE STALE 20 COST: natX was under-computed by 23 at f=3, so the
	// born path (which docks from the game's REAL native) landed 23px right of
	// the sweep's target (which docks from the assumed one). The sweep then
	// recognised the container at NEITHER position, silently declined it, and
	// every 3x sub-flyout ran with the sweep dead - including the back-arrow
	// click zone, which is assigned ONLY inside that sweep. The ring being
	// "off to the right" was the visible half of that; the dead arrow zone was
	// the invisible half. At f=2 assumed == actual, which is why 2x never saw
	// any of it.
	// btnW is the button's DRAWN width. The sweep has the real window and
	// passes it; the dock delta runs where no button is in hand and passes the
	// design cell scaled by the tier. For every stock button those are the
	// same number (47f), and SUBCAND prints the live width so a third-party
	// button that is not 47f announces itself instead of failing silently.
	inline int SubNativeDXFor(int btnW) { return btnW / 2 - 27; }
	inline int SubNativeDX()
	{
		return SubNativeDXFor(RoundHalfUp(47.0 * gTierF));
	}
	const int kSubPlaceBias = 29;   // sprite box half-height 26.5 + the game's
	                                // own 2.5px fudge, exact on both menus
	                                // (#134: verified again at f=3 - natT 207
	                                // matched the born native Y to the pixel,
	                                // so the Y law needed no change at all)

	inline int32_t SubPlaceTop(int32_t contentH, int32_t cy, int32_t viewH,
		float f)
	{
		const int32_t fE8  = RoundHalfUp(25 * f);   // [0xE8] end cap
		const int32_t fF4  = RoundHalfUp(53 * f);   // [0xF4] ring h / content floor
		const int32_t f100 = RoundHalfUp(29 * f);   // [0x100] y anchor
		const int32_t margT = RoundHalfUp(10 * f);
		const int32_t margB = viewH - margT;
		int32_t top = (fF4 >> 1) - (contentH >> 1) + cy - f100;
		// the game's four clamps, in ITS order
		if (top < margT) { top = margT; }
		if (viewH > 0 && top > margB - contentH) { top = margB - contentH; }
		if (top > cy - f100 - fE8) { top = cy - f100 - fE8; }
		const int32_t floorT = cy + fF4 - contentH + fE8 - f100;
		if (top < floorT) { top = floorT; }
		return top;
	}
	// SubPlaceTopMb: the SAME four clamps as SubPlaceTop, but marg_b comes
	// from the game's own MEASURED Place() parameter `mB` directly, never
	// re-derived from a desktop/monitor viewH (2026-08-23, root-cause pass).
	//
	// `sub_79AD00`'s REAL bottom margin is `mB`, a LIVE value the caller
	// (`sub_7EAEB0`) computes as `this[0x18C]->GetY() - 10`
	// (SUBFLYOUT-BUILDER.md ss3.1). WHAT `this[0x18C]` actually IS has not
	// been independently re-verified this pass - "the 3D view's own
	// Y-extent" is that doc's own reading, not re-confirmed here; an
	// adversarial review (2026-08-23) noted it could equally be a
	// position rather than a height, possibly tied to this mod's OWN HUD
	// scaling rather than something tier-independent. What IS directly
	// measured and certain: `mB` is NOT the desktop resolution.
	// SubPlaceTop's `margB = viewH - marginT` (viewH = gLastViewH, the
	// desktop height) was always the wrong quantity for this family:
	// measured 2026-08-23, mB=1166 on a 1600-tall desktop - a 434px gap.
	// Re-verified against the real `sub_79AD00` under Unicorn
	// (tools/uimap/emu/emu_subplacetopmb_model.py, committed and
	// re-runnable - not a throwaway script): feeding it fully-scaled
	// content/item metrics with the RAW measured mT=10/mB=1166 reproduces
	// this function's output bit-exact for every measured Civic Tools
	// button AT ITS OWN REAL COUNT (cnt 3/5/6/3/8/8/8, cy 397..997), not
	// just the one bar the mB-clamp fix
	// originally targeted.
	//
	// mT is passed the same way, for the same reason: measured constant
	// (10) regardless of tier - the sub-flyout builder's own screen-margin
	// literals are never patched by this mod (post-birth resize, not
	// born-2x - see tools/uimap/SUBFLYOUT-BUILDER.md ss5), so re-deriving
	// margT from `f` was accidentally consistent with the measured value
	// only because the top clamp never binds for any button measured so
	// far, not because RoundHalfUp(10*f) is actually correct.
	inline int32_t SubPlaceTopMb(int32_t contentH, int32_t cy, int32_t mT,
		int32_t mB, float f)
	{
		const int32_t fE8  = RoundHalfUp(25 * f);
		const int32_t fF4  = RoundHalfUp(53 * f);
		const int32_t f100 = RoundHalfUp(29 * f);
		int32_t top = (fF4 >> 1) - (contentH >> 1) + cy - f100;
		if (top < mT) { top = mT; }
		if (top > mB - contentH) { top = mB - contentH; }
		if (top > cy - f100 - fE8) { top = cy - f100 - fE8; }
		const int32_t floorT = cy + fF4 - contentH + fE8 - f100;
		if (top < floorT) { top = floorT; }
		return top;
	}
	// [Flyout] SubMath. DEFAULT 0 - REVERTED THE SAME SESSION IT SHIPPED
	// (v2.45.1). The math above is genuinely correct about the CONTAINER: it
	// reproduces the game's own Place 32/32 at n=1..8 x f=1/1.5/2/3, and with
	// it the 8-item picker stopped overlapping the bottom HUD. But the player's
	// eyes-on found what the emulator structurally could not: moving the
	// container SLIDES THE RING OFF ITS BUTTON by exactly the distance moved.
	//
	// WHY - and our own source said so 30 lines into the ring blit: "ORIGIN
	// STAYS PUT, only the SIZE doubles. v2.15.0 scaled the origin too and that
	// pushed the circle 94px down, UNDOCKING it." The ring's origin is the
	// GAME's stored blit origin inside the container; it does not follow a
	// container we relocate. Container placement and ring attachment are ONE
	// coupled system, and the emulator only models the container half - so a
	// 32/32 pass there proves the arithmetic, NOT the outcome.
	//
	// The user states the real law: "The flyout never moves - just where it
	// attaches in the list should." So the lever for the bottom-HUD overlap is
	// the ATTACHMENT POINT inside the list, not the container's position.
	//
	// ---- v2.46.0: BOTH HALVES, SO THIS IS BACK ON BY DEFAULT ------------
	// The missing half was found and MEASURED (emu_plot, see gSubRingAutoY):
	// the stem's y is a free variable that cannot move the strip. So the
	// container now goes to the game's clamped position AND the ring sprite is
	// offset by exactly that move, which pins it to the legacy dock the player
	// already confirmed. Net effect, and it is what the player described: the
	// strip stops hanging into the bottom HUD, the ring does not move at all.
	// 0 = the pre-v2.46 constant delta (instant revert, no rebuild).
	int gSubMath = 1;
	// Last view height seen by the sweep, so the born-at-Place path can apply
	// the same bottom-margin clamp. 0 = not yet known -> that clamp is skipped.
	int32_t gLastViewH = 0;

	inline int32_t SubDockDXEff()
	{
		return gSubDockDX != kIniAuto
			// #135 (2026-08-05): was RoundHalfUp(-16.5 * gTierF) - SubNativeDX().
			// That docked the assembly to a position which then required a
			// NON-ZERO SubRingDX to seat the ring on its button - and sliding
			// the ring is what tore it off the bar. The ring/strip/bar are
			// WELDED in the buffer (ring 0..80f, strip starts at 80f), so any
			// SubRingDX drives the connector wedge that many px INTO the panel
			// and its top/bottom border lines terminate mid-panel: the "broken
			// bar at the junction" the player reported, present at 2x since the
			// nudge shipped and simply tolerated.
			//
			// The RING LAW already said which lever is correct: "applying that
			// delta to the RING alone centres it but tears it off the
			// strip/bar ... applying it to the CONTAINER moves the whole
			// assembly together, so the ring seats on the button AND stays
			// joined." So the dock now carries the whole alignment and
			// SubRingDX derives to 0.
			//
			// Solve hole centre == ellipse centre with DX = 0:
			//     C + rhu(25f) = btn + rhu(21f),  C = btn + SubNativeDX + dock
			// =>  dock(f) = rhu(21f) - rhu(25f) - SubNativeDX()
			//     f=1.5: -14    f=2: -28    f=3: -55
			// The assembly therefore sits ~25px (2x) / 37px (3x) right of where
			// it used to. That is a VISIBLE move to a previously accepted
			// position - deliberate, and the only way to hold both properties.
			? gSubDockDX
			: RoundHalfUp(21.0 * gTierF) - RoundHalfUp(25.0 * gTierF)
				- SubNativeDX();
	}
	inline int32_t SubDockDYEff()
	{
		return gSubDockDY != kIniAuto
			? gSubDockDY : kSubPlaceBias - RoundHalfUp(26.5 * gTierF);
	}
	// v4.0.33: container shift for sub-flyout arm alignment.
	// The arm meets the strip at a row determined by the ring's buffer
	// position. At 1x the arm meets at kTargetFromBottom rows from the
	// visible bottom (measured ≈ 2.70 for all tall Build menus). At scale
	// f the ring blit (ringBltY) doesn't scale linearly, so the arm meets
	// a different row. The shift moves the container to compensate.
	//
	// Exact formula (sweep path, ringBltY known):
	//   naturalRow = (ringBltY + autoY0 + ringHs/2 - stripTop) / rowPitch
	//   targetRow  = visibleRows - kTargetFromBottom
	//   shift      = (targetRow - naturalRow) * rowPitch
	// where autoY0 = legT - tgtT (SubMath offset before container shift).
	//
	// Empirical fallback (birth path, ringBltY unknown):
	//   shift = max(0, (f - 1.5)) * 160  [measured from 1.5x→2x data]
	//
	// Works for ALL counts — no cnt gate. StripTop = capHs for cnt ≥ 2
	// (stripH > ringHs), so the shift is per container type, not per count.
	// kSubArmTargetBottom: armRow_fromBottom at 1x target. Measured as
	// 1.50 (bottom of Tourist Trap in the 8-row Build menu).
	const double kSubArmTargetBottom = 1.50;
	// THE STRIP/CONTAINER GEOMETRY SUM, one copy (audit B9: it was written
	// out here, in the SUBBORN log and in the SUBSHIFT log). Every input is
	// already at the tier: ring and cap height, item height and spacing.
	struct SubStripGeo
	{
		int32_t rowPitch;       // item height + spacing
		int32_t visibleRows;    // min(cnt, 8)
		int32_t stripH;         // cnt rows, less the trailing spacing
		int32_t contentH;       // max(strip, ring) + both caps
		int32_t stripTop;       // the strip centred in the content
	};
	inline SubStripGeo SubStripGeometry(int32_t ringHs, int32_t capHs,
		int32_t sItemH, int32_t sSpacing, int32_t cnt)
	{
		SubStripGeo g;
		g.rowPitch = sItemH + sSpacing;
		g.visibleRows = cnt < 8 ? cnt : 8;
		g.stripH = g.rowPitch * cnt - sSpacing;
		g.contentH = (g.stripH > ringHs ? g.stripH : ringHs) + 2 * capHs;
		g.stripTop = (g.contentH - g.stripH) / 2;
		return g;
	}

	// Exact shift from measured ring position. Called at sweep time when
	// gSubRingBltY and autoY0 are available.
	//   ringBltY: ring's blit Y in the container buffer (gSubRingBltY)
	//   autoY0:   gSubRingAutoY before the container shift (legT - tgtT)
	//   cnt:      strip item count (for computing stripTop / visibleRows)
	// The terms are returned too, so the SUBSHIFT log prints the formula's
	// own numbers instead of a second copy of it.
	struct SubShiftTerms
	{
		int32_t ringHs;
		int32_t stripTop;
		double naturalRow;
		double targetRow;
		int32_t shift;          // pixels, positive = container moves UP
	};
	inline SubShiftTerms SubContainerShiftFromGeo(
		int32_t ringBltY, int32_t autoY0, int32_t cnt)
	{
		const double f = static_cast<double>(gTierF);
		SubShiftTerms t;
		// UNSCALED SetLayout constants (tall: ringH=53, capH=25) and the
		// strip item dims (itemH=44, spacing=5 at 1x), at the tier
		t.ringHs = RoundHalfUp(53.0 * f);
		const SubStripGeo g = SubStripGeometry(t.ringHs, RoundHalfUp(25.0 * f),
			RoundHalfUp(44.0 * f), RoundHalfUp(5.0 * f), cnt);
		t.stripTop = g.stripTop;
		// Natural armRow in the buffer (includes SubMath auto offset)
		t.naturalRow =
			static_cast<double>(ringBltY + autoY0 + t.ringHs / 2 - g.stripTop)
			/ static_cast<double>(g.rowPitch);
		t.targetRow = static_cast<double>(g.visibleRows) - kSubArmTargetBottom;
		const double needed = t.targetRow - t.naturalRow;
		t.shift = (gTierF <= 1.0f || cnt < 1 || needed <= 0.0) ? 0
			: static_cast<int32_t>(RoundHalfUp(needed * g.rowPitch));
		return t;
	}
}

namespace UiSpikeInternal
{
	// 0xABB26B0E treated as a god PANEL (scaled + bottom-anchor docked to
	// (6,490))? DEFAULT 0 = NO, i.e. pre-v2.12.1 behaviour: left at stock,
	// untouched. ini [Flyout] ScaleGodPanelABB.
	// WHY OFF: v2.12.1 docked it there to fix founded-city god mode, but it did
	// NOT fix it - the real fix was v2.12.2 (0x0A78827A, the toolbar carrying
	// Obliterate/Reconcile/Disaster/Day-Night). Meanwhile the move dragged its
	// 434x976 background child 0x0BB26B19 from (5,1337) up to (8,782), directly
	// over the minimap dock 0x0987B48F at (10,1176) 470x446 - and per
	// CITY-DOCK-OVERLAP.md's z-order reading (dump order = add order, later =
	// on top) 0xABB26B0E paints ABOVE the dock. That is the minimap going dark.
	int     gScaleAbbPanel = 0;
}

namespace
{
	bool    gFgParentOk = false;      // GetParentWin slot verified at runtime
	// kFgMax: UiSpikeInternal.h (audit B11), shared with UiSpike.cpp.
	void**  gFgVt[kFgMax] = {};       // patched class vtables
	SlotFn  gFgOrig[kFgMax] = {};     // their original Plot fns
	int     gFgCount = 0;
	void*   gReadyWins[16] = {};
}

namespace UiSpikeInternal
{
	int     gReadyCount = 0;
	void*   gFgWaitRoot[4] = {};      // fail-open counters per pending root
	int     gFgWaitN[4] = {};
	void*    healDoneStrip = nullptr;         // ADVHEAL: strip already healed
	int      healPhase = 0;                   // ADVHEAL: 0 = armed, 1 = face clicked
}

namespace
{
	// CAA (CalcAbsoluteArea) experiment: log count for the rect-pointer probe.
	int gCaaLogCount = 0;
	int gCaaLogCount2 = 0;

	// Per-frame container-position tracker (replaces the dead buffer scan):
	// logs the container's absolute rect whenever it changes, to catch whether
	// the open->settle "jump" is a real window move or pure art animation.
	int gPosFrames = 0;
	int gPosLogged = 0;
	int gLastPosL = 0x7FFFFFFF, gLastPosT = 0, gLastPosW = 0, gLastPosH = 0;

	// ---- BLT HOOK on the disaster flyout's screen composite ----------------
	// Container Plot() ends by doing [0x68]->Blt(src=[0xdc] 141x339 buffer, ...)
	// to composite the flyout onto the 2400x1600 screen. The on-screen SIZE is
	// this Blt's DEST rect - the ONLY lever (all member-field writes proved
	// inert). We swap [0x68]'s vtable to a per-instance copy whose Blt (idx29,
	// offset 0x74) is our thunk, ONLY around the container's Plot call, then
	// restore it - so no other window's blits are affected. First build is
	// LOG-ONLY to capture the real arg layout (Blt's args weren't parseable
	// statically); once known we double the dest rect.
	typedef int(__thiscall* BltFn)(void* self, void* a1, void* a2, void* a3, void* a4);
	BltFn gOrigBlt = nullptr;
	void* gBltVtCopy[64] = {};

	// SRC/DST DECOUPLE hook on the container's BUFFER [0xdc] (v2.7.94). Offline
	// emulator (tools/flyout-sim) proved: the internal element draws are
	// [0xdc]->Blt(drawCtx, srcRect, dstRect) and are 1:1 (src size == dst size).
	// Doubling the fields doubles BOTH -> the src rect reads past the 1x texture
	// edge = the tiling MESS. Fix: HALVE the srcRect (a2) back to 1x so the real
	// texture STRETCHES to the doubled dst. (Whether the buffer Blt stretches is
	// the one thing the emulator stubs - this build is that in-game test.)
	BltFn gCtxOrigBlt = nullptr;
	void* gCtxVtCopy[64] = {};
	int gEltLog = 0;         // v2.8.6: log the first N element blits (src+dst) into
	                         // the buffer so we can see WHY the ring renders 1x while
	                         // the bar renders 2x in the SAME 2x buffer.
	// (gCtxHalve, a src-halving switch hardwired OFF since v2.8.3, was removed
	// with its branch in the 2026-09-25 audit, B1: buffer size is the 2x lever.)

	int __fastcall BltThunkCtx(void* self, void* /*edx*/,
		void* a1, void* a2, void* a3, void* a4)
	{
		if (gEltLog < 16 && a2 && a3)
		{
			gEltLog++;
			int32_t* s = reinterpret_cast<int32_t*>(a2);
			int32_t* d = reinterpret_cast<int32_t*>(a3);
			IconWatch("CLASS", self, s, d);
			if (InPlazaCell(d)) { gW_class++; }
			Logger::Get().WriteLine(LogLevel::Debug,
				"UiSpike: DELT src=(%d,%d,%d,%d) %dx%d  dst=(%d,%d,%d,%d) %dx%d",
				s[0], s[1], s[2], s[3], s[2] - s[0], s[3] - s[1],
				d[0], d[1], d[2], d[3], d[2] - d[0], d[3] - d[1]);
		}
		return gCtxOrigBlt ? gCtxOrigBlt(self, a1, a2, a3, a4) : 0;
	}

	// BUFFER RECREATE (v2.8.0/v2.8.1). Offline RE proved: on-screen flyout size
	// == the source buffer's PHYSICAL size, and the buffer is (re)created inside
	// Plot via buffer->Init(w,h,f0,f1) — class vtable 0x00AC1400 slot 3
	// (0x008269B0) - with w,h from the WINDOW size. A stale 141-wide buffer left
	// from an early small window is forced to recreate at the current window
	// (the SlotThunk<88> Plot hook corrupts its cached width); no Init hook is
	// needed for that. (The Init hook, its x2 scale knob and the ring-hiding and
	// src-halving switches were all hardwired off or inert and were removed in
	// the 2026-09-25 audit, B1.)
	void** const kBufClassVt = reinterpret_cast<void**>(0x00AC1400);
	bool   gBufVtWritable = false;

	// CLASS-level buffer Blt hook (v2.8.7). Because the buffer is force-recreated,
	// the instance vtable swap (BltThunkCtx) is dead; to see/adjust the element
	// draws we must hook the class vtable's Blt slot (0x00AC1400[29]=0x74).
	// v2.9.4: it also draws the sub-flyout ring at 2x (CODE-ONLY: read the ring
	// from the atlas (a1), nearest-upscale, write into the container at the
	// ring pos, color-keying magenta, and skip the game's 1x ring blit).
	typedef int(__thiscall* CBltFn)(void* self, void* a1, void* a2, void* a3, void* a4);
	CBltFn gClassBltOrig = nullptr;
	int    gStripDump = 0;               // DIAGNOSTIC (ini StripDump): declared here
	                                     // (before BltClassThunk) so the ring/bar draw
	                                     // logger can see it. See fuller note at the
	                                     // strip globals. No visual effect. Live-tunable.
	int    gClassBltLog = 0;             // log first N class-Blt draws
	int    gDrawCtxLog = 0;              // v2.9.2: probe the ring draw's SOURCE
	                                     // (drawContext a1) = the art atlas, to find
	                                     // where the 2x ring/picture art must go.
	// The dock (DisDockXEff/DisDockYEff) is the only position lever: the ring
	// seat globals were deleted in v4.0.41 (REGRESSION.md [CC-03]).
	// v4.0.16: initial scroll (first-visible ITEM index) written to the
	// disaster strip once per open. Measured 2026-08-22: the strip draws 6
	// rows of pitch 98 at dst-Y 0/98/196/294/392/490 and the ring centre
	// lands at strip-local y~303 - the gap between visible rows 3 and 4.
	// At scroll 0 that gap is volcano|fire, which is what stock shows; the
	// field was observed at 3 (= bottom of the 9-item list, 6 visible), so
	// the wrong disasters sat beside the ring. ini [Disaster] InitScroll.
	int    gDisInitScroll = 0;
	// 2026-08-23 REBUILD: both dock offsets become kIniAuto sentinels
	// resolved through DisDockXEff()/DisDockYEff() (declared beside the
	// rebuild code, before BltClassThunk). Explicit ini still wins; the
	// auto value depends on the DrawRebuild lever:
	//   rebuild ON  -> DERIVED, not tuned: the game's own unclamped Place
	//     output relative to the toolbar, from documented stock data only
	//     (_vanilla-reference/FINDINGS.md button table + the builder
	//     constants in SUBFLYOUT-BUILDER.md ss4.2):
	//       DockX = (btnRelX 10 + btnW/2 37) - [0xFC]40             = 7
	//       DockY = (btnRelY 190 + btnH/2 29) - [0x100]34
	//               + ([0xF4]62>>1) - (contentH1x 339>>1)           = 47
	//     ((a>>1)-(b>>1) halving discipline per the ring law.) With the
	//     rebuild's stock-proportional in-buffer ring (0, rhu(138f)),
	//     this lands the ring centre within 2px of the user-accepted
	//     2026-07-28 seat at f=2 - cross-checked in the plan - while
	//     being fully derived, so 1.5x/3x follow with no per-tier tuning
	//     (closes #123).
	//   (The legacy values -2 / 40 and their hand-tuned history:
	//   REGRESSION.md [CC-04].)
	int    gRingDockX = kIniAuto;         // disaster container dock X (ini DockX)
	int    gRingDockY = kIniAuto;         // disaster container dock Y (ini DockY)
	// v2.24.0 (audit B2/B3): the bar widen is the TIER FACTOR (float - an int
	// could never be 1.5) and the bar shift is "keep the widened bar flush
	// right" in closed form. The game always blits the 53px 1x bar art at
	// x = bufferW - 53; widened to RoundHalfUp(53*W) px it must start at
	// bufferW - RoundHalfUp(53*W), i.e. shift = 53 - RoundHalfUp(53*W).
	// f=2: widen 2.0, shift 53-106 = -53 - exactly the shipped ini values
	// (BarW=2 / BarDX=-53; the old compiled -45 default was dead in practice,
	// the deployed ini always overrode it). Ini values still override.
	int    gBarDX = kIniAuto;            // shift the BAR draws (caps+spine at the
	                                     // right edge) left so the widened bar stays
	                                     // flush. Live-tunable via ini [Disaster] BarDX.
	float  gBarWiden = -1.0f;            // x-upscale factor for the BAR draws so the
	                                     // scaled pictures nest inside the pill.
	                                     // <=0 = auto (tier factor). Live (BarW).
	inline float BarWidenEff()
	{
		return gBarWiden > 0.0f ? gBarWiden : gTierF;
	}
	inline int32_t BarDXEff()
	{
		return gBarDX != kIniAuto
			? gBarDX : 53 - RoundHalfUp(53.0 * BarWidenEff());
	}

	// (The LAYER FIX bar-tile cache and the ring seat-scaling helpers were
	// deleted in v4.0.41 with the legacy disaster path: REGRESSION.md [CC-05].)

	// Draw one BAR tile: read the atlas (a1), x-upscale by gBarWiden, write into
	// the container (self) at (d[0]+gBarDX, d[1]), color-keying magenta.
	// (v4.0.41) SUB-FLYOUT ONLY since the disaster rebuild: the disaster
	// family's bar draws are reconstructed by DrawDisasterElementScaled
	// below and never reach this function. History: REGRESSION.md [CC-06].
	void DrawBarScaled(void* self, void* a1, const int32_t* s, const int32_t* d)
	{
		int32_t* af = reinterpret_cast<int32_t*>(a1);
		int32_t* cf = reinterpret_cast<int32_t*>(self);
		uint8_t* asrc = reinterpret_cast<uint8_t*>(
			static_cast<uintptr_t>(static_cast<uint32_t>(af[15])));
		uint8_t* cdst = reinterpret_cast<uint8_t*>(
			static_cast<uintptr_t>(static_cast<uint32_t>(cf[15])));
		const int astride = af[16], cstride = cf[16];
		const int cW = cf[7] - cf[5], cH = cf[8] - cf[6];
		const int sw = s[2] - s[0], sh = s[3] - s[1];
		// gBarDX = -53 is NOT a disaster-only tweak - it is GENERIC, and the SBLT
		// blit trace proves why. The bar art is 53px wide and the game draws it
		// FLUSH AGAINST THE RIGHT EDGE of the container buffer:
		//     sub-flyout: buf 258 wide, bar dst x = 205..258   (205 + 53 = 258)
		// Widening it 2x without shifting puts it at 205..311 - 53px past the
		// end of the buffer - so the visible bar collapses to a sliver on the
		// right and the icon strip (x 160..248) no longer overlaps it. Shifting
		// left by exactly one bar width keeps the doubled bar flush:
		//     152 + 106 = 258 = buffer width, and 160..248 lands centred on it.
		// I gated this to disaster in v2.13.6 on the assumption it was
		// hand-tuned for that flyout; the trace shows it is just "keep the
		// widened bar flush right", which every container of this class needs.
		const int dx0 = d[0] + BarDXEff();
		// CAPS ARE NEVER Y-DOUBLED (v2.18.4, reverting v2.17.2/.3). The
		// doubled cap's lower half got overdrawn by the square fill tiles the
		// game paints AFTER the top cap, leaving square shoulders poking past
		// the arc at both pill ends (user report, mayor menus). The disaster
		// flyout - whose caps were always x-wide-only 106x25 - is the
		// confirmed on screen CORRECT look; the original "seam" this doubling
		// chased was actually the alpha-halo + ring-position issues, fixed
		// separately. x-widening only, exactly like disaster.
		const int dy0 = d[1];
		if (!asrc || !cdst || astride <= 0 || cstride <= 0) return;
		// v2.24.0 (audit B2): fractional NN like Upscale2x.cs - dest width is
		// RoundHalfUp(sw*W) and each dest column samples src floor(ox/W). At
		// W=2 this is bit-identical to the old sw*2 / ox/2 integer path.
		const double barW = static_cast<double>(BarWidenEff());
		const int barDstW = RoundHalfUp(sw * barW);
		for (int oy = 0; oy < sh; oy++)
		{
			const int cy = dy0 + oy;
			if (cy < 0 || cy >= cH) continue;
			const uint8_t* srow = asrc + (s[1] + oy) * astride;
			uint8_t* drow = cdst + cy * cstride;
			for (int ox = 0; ox < barDstW; ox++)
			{
				const int cx = dx0 + ox;
				if (cx < 0 || cx >= cW) continue;
				const uint8_t* sp = srow + (s[0] + static_cast<int>(ox / barW)) * 4;
				if (sp[0] == 0xFF && sp[1] == 0x00 && sp[2] == 0xFF)
					continue;
				// ALPHA (v4.0.21): blend EVERY nonzero-alpha pixel - the
				// v2.17.3 "skip 0<a<128" halo guard is obsolete now that
				// low weights BLEND instead of stamping opaque: a faint
				// edge column contributes almost nothing of itself but is
				// exactly what carries the pill's fade over the dock arm.
				// Skipping it left a navy sliver where the fade should be
				// (user screenshot 2026-08-22). Stock blends every nonzero
				// source pixel; so do we now.
				uint8_t* dp = drow + cx * 4;
				const uint8_t sa = sp[3];
				if (sa == 0)
					continue;
				if (sa == 255)
				{
					dp[0] = sp[0]; dp[1] = sp[1]; dp[2] = sp[2];
					dp[3] = sp[3];
				}
				else
				{
					// v4.0.21: single alpha blend, user-confirmed correct.
					dp[0] = static_cast<uint8_t>(
						(sp[0] * sa + dp[0] * (255 - sa) + 127) / 255);
					dp[1] = static_cast<uint8_t>(
						(sp[1] * sa + dp[1] * (255 - sa) + 127) / 255);
					dp[2] = static_cast<uint8_t>(
						(sp[2] * sa + dp[2] * (255 - sa) + 127) / 255);
					dp[3] = 255;
				}
			}
		}
	}

	// v2.36.10 ([Probe] EdgeBlt, task #59): countdown of edge-strip blits still
	// to log. Declared here because BltClassThunk reads it and the probe block
	// that parses the ini sits far below.
	int gEdgeBltLog = 0;

	// #162 THIN-BLIT PROBE. [Probe] ThinBlt=<lines>. Default OFF.
	//
	// THE QUESTION IT ANSWERS, and nothing else in this file can: is the
	// reported hairline DRAWN, or is it a GAP? Five hypotheses were shipped
	// against these two lines by reasoning about mechanisms - art snapping,
	// tiled sizing, 9-slice sizing, a runtime-bitmap underfill, button cells -
	// and every offline census came back clean:
	//     abutting windows separating at 1.5x   0  (0 at 1x/2x/3x, controls OK)
	//     cropped blits under-filling           0 of 783
	//     advisor portrait cell vs window       exact at 1.5x AND 2x
	// When every coverage model says "covered" and the player still sees ink,
	// the model is wrong - so stop modelling and watch the blits.
	//
	// A hairline that is DRAWN must arrive here as a dst rect <= 3px on one
	// axis. If a session that shows the line logs NOTHING, the line is NOT
	// drawn through this buffer class: it is an uncovered gap (look at what
	// fails to cover it) or it is outside the UI buffer entirely (the #59
	// boundary). Either answer is worth more than a sixth guess.
	//
	// A NULL HERE IS ONLY EVIDENCE WITH ITS POSITIVE CONTROL. The counter
	// below reports how many blits were SEEN as well as how many were thin, so
	// "0 thin of 0 seen" (hook never ran) can never be misread as "0 thin of
	// 40,000 seen" (hook ran, nothing thin).
	int gThinBlt = 0;          // remaining lines to log; 0 = off
	int gThinSeen = 0;         // total blits this hook observed
	int gThinHit = 0;          // of those, thin ones

	// ===========================================================================
	// DISASTER FLYOUT REBUILD (2026-08-23, approved plan: "study the 1x
	// disaster flyout and rebuild this flyout scale code from scratch").
	//
	// WHY: six same-day live-tested patches to the ring/bar junction all
	// corrected one element against the game's own re-flowed mixed-1x/2x
	// layout (bar right-anchored to the LIVE 2x window, ring left-anchored
	// and UNCHANGED - confirmed by directly querying the real emulated
	// Plot() at both window sizes, tools/flyout-sim/emu_plot.py, goldens in
	// _tests/golden/disaster-{stock-1x,live-2x}-drawlist.txt). Each patch
	// fixed a symptom; the junction between independently-corrected
	// elements can never be right by construction.
	//
	// THE INVARIANT THIS REPLACES ALL OF THAT WITH: at factor f, the live
	// buffer equals the stock 1x buffer magnified by f. Every element draw
	// is mapped to its STOCK dst, scaled by f, nearest-upscaled, and
	// RGBA-copied - in stock order (bar first, ring last, painted ON TOP).
	// Verified offline before this was written: _tests/Test-DisasterDrawRebuild.py
	// (identity at f=1 against the real emulated draw list; gap-free,
	// overlap-free coverage and an exact geometric weld at every shipping
	// tier; 3 negative controls proving the gate actually rejects a wrong
	// formula).
	//
	// STOCK GEOMETRY (buffer 141x339, measured from the real Plot/tiler,
	// not inferred - see the golden files):
	//   top cap    src(94,0,147,25)   dst(88,0,141,25)
	//   spine      src(94,25,147,37)  repeating 53x12 tile, dst y 25..314
	//   bottom cap src(147,37,200,62) dst(88,314,141,339)  <- a DIFFERENT
	//              source rect than the top cap, not a reused sprite
	//   ring       src(0,0,94,62)     dst(0,138,94,200)    <- LEFT-anchored,
	//              confirmed BYTE-IDENTICAL between the stock and live-2x
	//              golden captures: this element never re-flows with
	//              window size, so it needs no seat correction at all once
	//              the bar is fixed to sit where a stock-proportional
	//              weld puts it.
	// The weld: ring right edge (94) overlaps bar left edge (141-53=88) by
	// exactly 6px, ring painted LAST. That overlap and that order are the
	// entire "fused" look.
	//
	// kIniAuto sentinel matches this file's existing convention (SubDockDX
	// etc.) - "not set by ini" rather than a magic literal. The one-release
	// DrawRebuild kill switch and the whole legacy path it guarded were
	// deleted in v4.0.41 after user acceptance at 2x/1.5x/3x.
	// (v4.0.41) gDisRebuild / [Disaster] DrawRebuild deleted: the legacy
	// path it reverted to is gone, so the rebuild is THE pipeline.
	bool gDisSpineDrawn = false;   // per-paint latch: has this paint's
	                               // spine region already been drawn?
	                               // Reset when the TOP CAP arrives (it is
	                               // always first in stock draw order), set
	                               // when the first spine tile arrives.
	int  gDisRebuildLog = 40;      // DISREBUILD diagnostic log budget
	int  gDisBufDump = 0;          // ini [Disaster] BufDump=N - remaining
	                               // full-buffer dumps to write (diagnostic;
	                               // default off in a shipped install)

	// Dock offsets, resolved: explicit ini wins; auto depends on the
	// rebuild lever. See gRingDockX/gRingDockY's comment for the closed-
	// form derivation of 7/47 (documented stock data, zero tuning).
	inline int32_t DisDockXEff()
	{
		return gRingDockX != kIniAuto ? gRingDockX : 7;
	}
	inline int32_t DisDockYEff()
	{
		return gRingDockY != kIniAuto ? gRingDockY : 47;
	}

	inline int32_t DisBarLeft(float f)
	{
		// rhu(94f) - rhu(6f): NOT (W - rhu(53f)) - the two are only
		// numerically equal at the tiers this project ships (verified in
		// the offline gate); this form is the one that is geometrically
		// exact by definition (ring-right minus the stock weld), which is
		// the property every downstream assertion depends on.
		return RoundHalfUp(94.0 * f) - RoundHalfUp(6.0 * f);
	}
	inline int32_t DisCapHeight(float f)
	{
		return RoundHalfUp(25.0 * f);
	}

	// Pure RGBA copy (the stock element op the 2026-08-23 measurements proved
	// correct for this never-cleared buffer - see that function's own
	// comment for why a blend here is wrong): nearest-neighbour upscale
	// from (sx0,sy0)-relative source pixels into an explicit dst rect,
	// magenta-keyed, source alpha preserved untouched.
	void DisBlitScaled(uint8_t* cdst, int cstride, int cW, int cH,
		const uint8_t* asrc, int astride,
		int sx0, int sy0, int srcW, int srcH,
		int dx0, int dy0, int dstW, int dstH, float f)
	{
		for (int oy = 0; oy < dstH; oy++)
		{
			const int cy = dy0 + oy;
			if (cy < 0 || cy >= cH) { continue; }
			const int srow = sy0 + std::min(srcH - 1,
				static_cast<int>(oy / f));
			const uint8_t* srcRow = asrc + srow * astride;
			uint8_t* dstRow = cdst + cy * cstride;
			for (int ox = 0; ox < dstW; ox++)
			{
				const int cx = dx0 + ox;
				if (cx < 0 || cx >= cW) { continue; }
				const int scol = sx0 + std::min(srcW - 1,
					static_cast<int>(ox / f));
				const uint8_t* sp = srcRow + scol * 4;
				if (sp[0] == 0xFF && sp[1] == 0x00 && sp[2] == 0xFF)
				{
					continue;   // magenta colour-key = transparent
				}
				uint8_t* dp = dstRow + cx * 4;
				dp[0] = sp[0]; dp[1] = sp[1]; dp[2] = sp[2]; dp[3] = sp[3];
			}
		}
	}

	// Full-buffer dump for offline pixel verification (the DISBUFDUMP
	// instrument, promoted from a hardcoded 2-shot to ini [Disaster]
	// BufDump=N). Same file format/naming the offline renderer
	// (tools/research/render_disbuf.py) and the pixel half of
	// _tests/Test-DisasterDrawRebuild.py consume. Path derived from our
	// own module (the SpinProbe ResolveCsvPath pattern) - never hardcoded.
	void DisMaybeDumpBuffer(const uint8_t* cdst, int cstride, int cW, int cH)
	{
		if (gDisBufDump <= 0 || !cdst || cstride <= 0
			|| cW <= 0 || cH <= 0 || cW > 4096 || cH > 4096)
		{
			return;
		}
		gDisBufDump--;
		static int sWritten = 0;
		HMODULE selfMod = nullptr;
		wchar_t dp2[MAX_PATH] = {};
		if (!GetModuleHandleExW(
				GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS |
				GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
				reinterpret_cast<LPCWSTR>(&gDisBufDump), &selfMod)
			|| !GetModuleFileNameW(selfMod, dp2, MAX_PATH))
		{
			return;
		}
		wchar_t* sl = nullptr;
		for (wchar_t* p = dp2; *p; p++)
		{
			if (*p == L'\\' || *p == L'/') { sl = p; }
		}
		if (!sl) { return; }
		*(sl + 1) = L'\0';
		wchar_t name[48];
		swprintf_s(name, L"SC4UIScale-disbuf%d.bin", sWritten++);
		wcscat_s(dp2, MAX_PATH, name);
		FILE* fp = nullptr;
		if (_wfopen_s(&fp, dp2, L"wb") != 0 || !fp) { return; }
		const int32_t hdr[3] = { cW, cH, cstride };
		fwrite("DBUF", 1, 4, fp);
		fwrite(hdr, sizeof(int32_t), 3, fp);
		for (int y = 0; y < cH; y++)
		{
			fwrite(cdst + y * cstride, 4, cW, fp);
		}
		fclose(fp);
		Logger::Get().WriteLine(LogLevel::Info,
			"UiSpike: DISBUFDUMP wrote %dx%d buffer -> %ls", cW, cH, dp2);
	}

	// Dispatches ONE classified element draw (ring / top cap / bottom cap /
	// spine-tile-arrival) to its stock-geometry reconstruction. `s`/`d` are
	// THIS call's own raw src/dst - never reused across elements, so top
	// cap and bottom cap (different source sprites, per the stock geometry
	// above) are never confused with each other.
	void DrawDisasterElementScaled(void* self, void* a1,
		const int32_t* s, const int32_t* d, int kind)
	{
		int32_t* af = reinterpret_cast<int32_t*>(a1);
		int32_t* cf = reinterpret_cast<int32_t*>(self);
		uint8_t* asrc = reinterpret_cast<uint8_t*>(
			static_cast<uintptr_t>(static_cast<uint32_t>(af[15])));
		uint8_t* cdst = reinterpret_cast<uint8_t*>(
			static_cast<uintptr_t>(static_cast<uint32_t>(cf[15])));
		const int astride = af[16], cstride = cf[16];
		const int cW = cf[7] - cf[5], cH = cf[8] - cf[6];
		if (!asrc || !cdst || astride <= 0 || cstride <= 0) { return; }
		const float f = gTierF;
		const int barLeft = DisBarLeft(f);
		const int capH = DisCapHeight(f);

		if (kind == 0)   // RING - left-anchored, unaffected by W, drawn LAST
		{
			const int dstW = FloorScale(s[2] - s[0], f);   // FLOOR: matches
			const int dstH = FloorScale(s[3] - s[1], f);   // the existing
			                                                // ring-blit convention (never overrun the source edge)
			const int dx0 = RoundHalfUp(d[0] * f);
			const int dy0 = RoundHalfUp(d[1] * f);
			DisBlitScaled(cdst, cstride, cW, cH, asrc, astride,
				s[0], s[1], s[2] - s[0], s[3] - s[1],
				dx0, dy0, dstW, dstH, f);
			// Ring is the LAST element in stock draw order, so the buffer
			// is complete here - the one right moment to dump it.
			DisMaybeDumpBuffer(cdst, cstride, cW, cH);
		}
		else if (kind == 1)   // TOP CAP - resets the per-paint spine latch
		{
			gDisSpineDrawn = false;
			DisBlitScaled(cdst, cstride, cW, cH, asrc, astride,
				s[0], s[1], s[2] - s[0], s[3] - s[1],
				barLeft, 0, cW - barLeft, capH, f);
		}
		else if (kind == 2)   // BOTTOM CAP - own source sprite, own dst
		{
			DisBlitScaled(cdst, cstride, cW, cH, asrc, astride,
				s[0], s[1], s[2] - s[0], s[3] - s[1],
				barLeft, cH - capH, cW - barLeft, capH, f);
		}
		else   // kind == 3: FIRST spine tile this paint - draw the WHOLE
		{      // scaled spine region in one pass, phase-locked to the cap
		       // edge (per-tile stock-y mapping is ill-posed: 53 live
		       // tiles vs 25 stock tiles, the game re-flows tile COUNT to
		       // the live height - see the module-level design comment).
			if (gDisSpineDrawn) { return; }
			gDisSpineDrawn = true;
			const int srcW = s[2] - s[0], srcH = s[3] - s[1];   // 53x12
			const int spineY0 = capH, spineY1 = cH - capH;
			for (int cy = spineY0; cy < spineY1; cy++)
			{
				if (cy < 0 || cy >= cH) { continue; }
				const int srow = s[1] + (static_cast<int>(
					std::floor((cy - spineY0) / f)) % srcH + srcH) % srcH;
				const uint8_t* srcRow = asrc + srow * astride;
				uint8_t* dstRow = cdst + cy * cstride;
				for (int cx = barLeft; cx < cW; cx++)
				{
					if (cx < 0 || cx >= cW) { continue; }
					const int scol = s[0] + std::min(srcW - 1,
						static_cast<int>(std::floor((cx - barLeft) / f)));
					const uint8_t* sp = srcRow + scol * 4;
					if (sp[0] == 0xFF && sp[1] == 0x00 && sp[2] == 0xFF)
					{
						continue;
					}
					uint8_t* dp = dstRow + cx * 4;
					dp[0] = sp[0]; dp[1] = sp[1]; dp[2] = sp[2]; dp[3] = sp[3];
				}
			}
		}
		if (gDisRebuildLog > 0)
		{
			gDisRebuildLog--;
			Logger::Get().WriteLine(LogLevel::Info,
				"UiSpike: DISREBUILD kind=%d f=%.2f src(%d,%d,%d,%d) "
				"raw_dst(%d,%d,%d,%d) barLeft=%d capH=%d buf=%dx%d",
				kind, f, s[0], s[1], s[2], s[3], d[0], d[1], d[2], d[3],
				barLeft, capH, cW, cH);
		}
	}


	int __fastcall BltClassThunk(void* self, void* /*edx*/,
		void* a1, void* a2, void* a3, void* a4)
	{
		if (a2 && a3)
		{
			int32_t* s = reinterpret_cast<int32_t*>(a2);
			int32_t* d = reinterpret_cast<int32_t*>(a3);

			// ---- ICONFIT (task #149): DOES THE ART FILL ITS FRAME? ----------
			// The rule, and the whole point: never interpret the plugin's art.
			// A menu item button takes stateW = imageWidth/4 (the ENGINE's own
			// rule) and then reads a slice AS WIDE AS
			// THE CELL. With 1x art in a doubled cell it pulls 88px out of a
			// 176x44 strip, spanning TWO 44px states - which is why an
			// uncovered custom icon shows as N copies side by side. N is the
			// scale ratio, not a tiling bug.
			//
			// CURE: read ONE state and leave the destination alone, so the blit
			// stretches that state across the whole cell. Tier-independent by
			// construction - the ratio falls out of dstW/stateW and 1.5/2/3 are
			// never mentioned. Needs NO catalogue, no per-mod package and no
			// extraction, so content published years from now is covered.
			//
			// SELF-VALIDATING, because a1's field layout is a HYPOTHESIS (it is
			// the source buffer, assumed to share self's rect layout at [5..8]).
			// If that is wrong the derived bmpW is garbage and every condition
			// below fails, so the blit passes through untouched. Fail-safe by
			// design: this runs in a per-frame draw path.
			//
			// SCOPE IS THE OVER-READ SIGNATURE ITSELF, not a size heuristic:
			//   bmpW divides by 4      -> it is a 4-state strip
			//   srcW is a whole multiple of stateW AND larger  -> over-read
			//   srcH == bmpH           -> a full-height state strip
			//   dstW == srcW           -> currently a 1:1 copy, nothing stretching
			// Art that already fits has srcW == stateW, so the condition is
			// false and correct icons are never touched - it cannot fight the
			// static packages or double-scale anything.
			// DEAD, DO NOT RE-ENABLE. This was the WRONG CHANNEL: these icons
			// blit through BltStripThunk (the strip's draw-context slot 29),
			// never through the class-wide buffer Blt. Left disabled because
			// its gate also matched ordinary FULL-BITMAP draws (srcW == bmpW
			// is trivially a whole multiple of bmpW/4) and shipped a white
			// line through UI art. The live rule is ICONCENTRE, below.
			if (false && a1)
			{
				const int32_t* sb = reinterpret_cast<const int32_t*>(a1);
				const int bmpW = sb[7] - sb[5];
				const int bmpH = sb[8] - sb[6];
				const int srcW = s[2] - s[0], srcH = s[3] - s[1];
				const int dstW = d[2] - d[0], dstH = d[3] - d[1];
				if (bmpW > 0 && bmpH > 0 && bmpW <= 4096 && bmpH <= 4096
					&& (bmpW % 4) == 0 && srcW > 0 && srcH > 0 && dstW > 0 && dstH > 0)
				{
					const int stateW = bmpW / 4;
					if (stateW > 0 && srcW > stateW && (srcW % stateW) == 0
						&& srcH == bmpH && dstW == srcW)
					{
						s[2] = s[0] + stateW;
						if (gIconFitLog > 0)
						{
							gIconFitLog--;
							Logger::Get().WriteLine(LogLevel::Info,
								"UiSpike: ICONFIT bmp %dx%d stateW=%d src %dx%d -> %dx%d "
								"dst %dx%d (x%.2f)",
								bmpW, bmpH, stateW, srcW, srcH, stateW, srcH,
								dstW, dstH, stateW ? (double)dstW / stateW : 0.0);
						}
					}
				}
			}
			// v2.11.2: the class Blt patch is now PERMANENT (fires for every
			// buffer-class blit, incl. the scroll-arrow repaint path), so gate the
			// ring/bar transforms to the disaster CONTAINER buffer by its size -
			// other UI that shares this buffer class falls through untouched.
			int32_t* cf0 = reinterpret_cast<int32_t*>(self);
			const int selfW = cf0[7] - cf0[5];
			const int selfH = cf0[8] - cf0[6];
			// ---- EDGE-BLIT DETECTOR (v2.36.10, task #59) ------------------
			// The pause border is a THIN GOLD STRIP hugging all four screen
			// edges. Three window-tree passes could not name it, so test the
			// other hypothesis directly: if it is blitted through this buffer
			// class at all, it must appear here as a thin dst rect flush
			// against an edge of a screen-sized dest. Tight filter (<=12px on
			// one axis AND touching an edge AND a big dest) so it cannot
			// flood; capped at 40 lines. [Probe] EdgeBlt=1.
			// If a full session with pauses logs NOTHING, the border is not
			// drawn through the UI buffer class at all - it is in the 3D /
			// present path, which is a different class of work entirely and
			// the honest place to stop guessing.
			// ---- #162 THIN-BLIT PROBE (see the declaration for the question) --
			if (gThinBlt > 0)
			{
				gThinSeen++;
				// THE HEARTBEAT IS THE POSITIVE CONTROL, AND THE FIRST VERSION
				// OF THIS PROBE DID NOT HAVE ONE. It printed only on a hit, so a
				// session with no thin blits produced an EMPTY LOG - byte-identical
				// to the hook never running. That is the exact failure this file
				// warns about everywhere else (law 54, NULL IS NOT EVIDENCE), and
				// it cost a launch: the run came back silent and the silence could
				// not be read. Now the count prints on its own schedule, so
				// "40,000 seen / 0 thin" (a real null) can never be confused with
				// "0 seen" (a dead probe).
				// gThinSeen==1 is the FIRST BLIT: it proves the hook is installed
				// AND executing AND the ini key arrived. Without it, silence has
				// three possible causes (no thin blits / hook not running / key
				// not read) and the run answers nothing - which is exactly what
				// happened twice.
				if (gThinSeen == 1 || (gThinSeen % 2000) == 0)
				{
					Logger::Get().WriteLine(LogLevel::Info,
						"UiSpike: THINBLT heartbeat - %d blit(s) seen, %d thin so "
						"far. A heartbeat with 0 thin IS the answer: the hairline "
						"is not drawn through this buffer class.",
						gThinSeen, gThinHit);
				}
				const int tdw = d[2] - d[0], tdh = d[3] - d[1];
				if (tdw > 0 && tdh > 0 && (tdw <= 3 || tdh <= 3))
				{
					gThinHit++;
					gThinBlt--;
					// 2026-08-17: also print the SOURCE IMAGE's own dimensions.
					// The 084246 capture caught the hairline drawer red-handed -
					// 19x an 18x2 band from src(18,36,36,38) tiled across the
					// bottom of a 340x155 code-created buffer - and then the
					// hunt STALLED because `img=%p` names a runtime pointer, not
					// a sheet: no 340x155 window exists in any .UI and no
					// 54-wide sheet exists in the stock extract, so the sheet
					// could not be found offline. Its WxH keys find_tgi across
					// all NINE archives (the discover-don't-list law).
					// RAW RECT READS, NEVER VIRTUALS (adversarial review
					// 2026-08-17): a1's identity is an explicit HYPOTHESIS
					// (:1997 - source buffer vs draw context is UNRESOLVED),
					// and __except cannot protect against a valid object of
					// the WRONG CLASS - Width()/Height() would dispatch two
					// arbitrary engine methods as getters, with side effects
					// and no exception, mid-draw. ICONFIT's idiom instead:
					// read the rect words at [5..8]; if the hypothesis is
					// wrong the numbers are garbage and print as such - no
					// control transfer, fail-safe by construction.
					int imW = -1, imH = -1;
					__try
					{
						if (a1)
						{
							int32_t* r1 = reinterpret_cast<int32_t*>(a1);
							imW = r1[7] - r1[5];
							imH = r1[8] - r1[6];
						}
					}
					__except (EXCEPTION_EXECUTE_HANDLER) { imW = imH = -2; }
					Logger::Get().WriteLine(LogLevel::Info,
						"UiSpike: THINBLT dst(%d,%d,%d,%d) %dx%d  src(%d,%d,%d,%d) "
						"%dx%d  destBuf=%dx%d  img=%p %dx%d  [seen %d, thin %d]",
						d[0], d[1], d[2], d[3], tdw, tdh,
						s[0], s[1], s[2], s[3], s[2] - s[0], s[3] - s[1],
						selfW, selfH, a1, imW, imH, gThinSeen, gThinHit);
					if (gThinBlt == 0)
					{
						Logger::Get().WriteLine(LogLevel::Info,
							"UiSpike: THINBLT budget spent after %d blit(s) seen, "
							"%d thin. If the hairline is still on screen and no row "
							"above sits under it, the line is NOT drawn through this "
							"buffer class - it is an uncovered gap or outside the UI "
							"buffer (the #59 boundary).", gThinSeen, gThinHit);
					}
				}
			}
			if (gEdgeBltLog > 0 && selfW >= 1000 && selfH >= 700)
			{
				const int dw = d[2] - d[0], dh = d[3] - d[1];
				const bool thin = (dw > 0 && dh > 0) && (dw <= 12 || dh <= 12);
				const bool touches = (d[0] <= 2 || d[1] <= 2
					|| d[2] >= selfW - 2 || d[3] >= selfH - 2);
				if (thin && touches)
				{
					gEdgeBltLog--;
					Logger::Get().WriteLine(LogLevel::Debug,
						"UiSpike: EBLT dst(%d,%d,%d,%d) %dx%d  src(%d,%d,%d,%d) "
						"%dx%d  dest=%dx%d  img=%p",
						d[0], d[1], d[2], d[3], dw, dh,
						s[0], s[1], s[2], s[3], s[2] - s[0], s[3] - s[1],
						selfW, selfH, a1);
				}
			}
			// destIsContainer = the DISASTER-era size heuristic (unchanged, its
			// path is LOCKED). destIsSubContainer = the mayor sub-flyout
			// container, identified by its EXACT 258px width (every observed
			// menu: 258 x 206..874 - the 2-item "Freight Train" menu is 206,
			// which a height-only gate kept missing; first 300, then 260, each
			// time skipping the ring -> 1x, undocked circle). Height floor 100
			// only rejects degenerate buffers.
			// v2.18.3: SIZE HEURISTICS CANNOT SEPARATE TOOLTIPS from the
			// disaster container - tip backing buffers are text-sized (185..
			// 490+ wide, 120..400+ tall, all seen) and every widening of this
			// gate ate another tooltip's translucent fill (torn body, clipped
			// corners). Positive identification instead: the disaster
			// container is 282x678 and exists ONLY in god mode, so the gate is
			// narrow (w 200..400) AND tall (h > 500), and the bar block below
			// additionally splits by mode (god -> destIsContainer, mayor ->
			// destIsSubContainer w==258). Tooltips satisfy neither.
			// v2.24.0 (audit A3/A4): both gates are now DERIVED from the tier
			// factor. The old literals were the f=2 evaluations:
			//   container band  (100..200 x >250 design) -> 200..400 x >500
			//   sub width       129 design               -> 258 EXACT
			// At f=2 the forms reduce to those numbers exactly (integer factors
			// get zero tolerance, so 2x keeps its bit-exact == 258 gate; only
			// fractional factors allow +-1 for the game's own rounding of the
			// f x 129 buffer). Without this, the sub machinery never fired at
			// 1.5x (194) or 3x (387), and the disaster path died at 3x (423).
			const bool destIsContainer =
				(selfH > RoundHalfUp(250 * gTierF)
				 && selfW > RoundHalfUp(100 * gTierF)
				 && selfW < RoundHalfUp(200 * gTierF));
			const int wantSubW = RoundHalfUp(129 * gTierF);
			const int subTol =
				(gTierF == std::floor(gTierF)) ? 0 : 1;
			const bool destIsSubContainer =
				(!gDisasterDrawTuning && selfH >= 100
				 && selfW >= wantSubW - subTol && selfW <= wantSubW + subTol);

			// ---- DISASTER FLYOUT REBUILD DISPATCH (2026-08-23) ----------
			// See the design comment above DisBarLeft. Classifies each of
			// the disaster container's element draws by ITS OWN signature
			// (measured from the real emulated Plot, goldens in
			// _tests/golden/) and redraws it at stock-geometry-times-f.
			// Every handled draw returns 0 - nothing downstream ever sees
			// a disaster element draw.
			// The sub-flyout family (destIsSubContainer) is untouched by
			// construction - this gate requires gDisasterDrawTuning.
			if (gDisasterDrawTuning && destIsContainer
				&& a1 && gTierF > 1.01f)
			{
				const int sw = s[2] - s[0], sh = s[3] - s[1];
				const int dw = d[2] - d[0], dh = d[3] - d[1];
				const bool rightAnchored =
					(d[0] >= selfW - 53 - 4 && d[0] < selfW);
				if (d[0] == 0 && sw > 80 && sw < 120 && sh > 40 && sh < 90)
				{
					// RING (94x62, left-anchored, drawn last = on top)
					DrawDisasterElementScaled(self, a1, s, d, 0);
					return 0;
				}
				if (rightAnchored && sh == 25 && d[1] == 0)
				{
					// TOP CAP (also draws nothing else; resets spine latch)
					DrawDisasterElementScaled(self, a1, s, d, 1);
					return 0;
				}
				if (rightAnchored && sh == 25 && d[3] == selfH)
				{
					// BOTTOM CAP (its own source sprite)
					DrawDisasterElementScaled(self, a1, s, d, 2);
					return 0;
				}
				if (rightAnchored && sh <= 12 && dh <= 12)
				{
					// SPINE TILE - first arrival draws the whole scaled
					// spine region; the rest of this paint's tiles drop.
					DrawDisasterElementScaled(self, a1, s, d, 3);
					return 0;
				}
				// Anything else (unknown draw into the container) falls
				// through untouched and lands at 1x rather than being
				// mis-corrected. DISREBUILD logging plus DISBUFDUMP make
				// such a draw visible if one exists.
				(void)dw;
			}
			// DIAGNOSTIC (ini StripDump): throttled log of ring/bar draws + the
			// dest buffer size, so the COLLAPSE repaint (which now routes here too)
			// shows exactly which buffer/size it paints into.
			// ---- SBLT: full blit trace for the SUB-FLYOUT container -----------
			// MEASURE, DO NOT GUESS. Three screenshot-driven builds failed to
			// seat this bar, which is the exact failure mode the project notes
			// warn about ("burned many hours and never converged"). So capture
			// EVERY blit into this buffer - unmodified src and dest rects, in
			// call order - and compute the offsets offline from the trace
			// instead of inferring them from pixels.
			// Scoped by gDisasterDrawTuning==0, i.e. only while the shared
			// sub-flyout container is the hooked instance, so the disaster
			// flyout's (working) draw path is never logged or disturbed.
			if (gSubBltLog && destIsSubContainer)
			{
				static int sblt = 0;
				if (sblt < 120)
				{
					sblt++;
					Logger::Get().WriteLine(LogLevel::Debug,
						"UiSpike: SBLT #%03d self=%p buf=%dx%d  src(%d,%d,%d,%d) %dx%d"
						"  dst(%d,%d,%d,%d) %dx%d  a1=%p",
						sblt, self, selfW, selfH,
						s[0], s[1], s[2], s[3], s[2] - s[0], s[3] - s[1],
						d[0], d[1], d[2], d[3], d[2] - d[0], d[3] - d[1], a1);
				}
			}
			// ---- EBLT: blits into the EMERGENCY panel's buffer (496 wide).
			// Lines appearing = the panel IS this hooked buffer class and the
			// read-modify-write toolkit applies; silence = different class
			// (then the EVTP vtable log picks the hook family).
			// v2.18.1: widened for the TOOLTIP capture - the tip draws TWO
			// boxes (title buffer 430x120 seen; the torn BODY box is narrower)
			// so the gate takes any mid-sized buffer and the cap covers both
			// boxes' full tile sets. self logged to separate the buffers.
			if (gEmergLog && selfW >= 60 && selfW <= 600 && selfH >= 60
				&& selfW != 258)
			{
				static int eblt = 0;
				if (eblt < 400)
				{
					eblt++;
					Logger::Get().WriteLine(LogLevel::Debug,
						"UiSpike: EBLT #%03d self=%p buf=%dx%d  src(%d,%d,%d,%d) %dx%d"
						"  dst(%d,%d,%d,%d) %dx%d  a1=%p",
						eblt, self, selfW, selfH,
						s[0], s[1], s[2], s[3], s[2] - s[0], s[3] - s[1],
						d[0], d[1], d[2], d[3], d[2] - d[0], d[3] - d[1], a1);
				}
			}
			// ---- RCAL: where are the MAYOR flyout rings drawn? ----------------
			// The circles on zones/transport/utilities/civic render at 1x and
			// detached. That is either (a) immediate-mode painted art, like the
			// disaster ring - fixable only by intercepting the blit - or (b)
			// window-bound art, fixable in the SelectiveArt package. Those need
			// opposite fixes, so identify the LAYER before touching either.
			// This logs every blit whose SOURCE is ring-sized, with the DEST
			// buffer's dimensions, regardless of destIsContainer. If mayor rings
			// appear here, they are painted (a). If nothing appears while a
			// mayor flyout is open, they are window art (b).
			if (gRingCalLog)
			{
				const int rsw = s[2] - s[0], rsh = s[3] - s[1];
				if (rsw > 70 && rsw < 140 && rsh > 35 && rsh < 100)
				{
					static int rcal = 0;
					if (rcal < 40)
					{
						rcal++;
						Logger::Get().WriteLine(LogLevel::Debug,
							"UiSpike: RCAL #%02d buf=%dx%d  src(%d,%d) %dx%d  "
							"dst(%d,%d) %dx%d  cont=%d",
							rcal, selfW, selfH, s[0], s[1], rsw, rsh,
							d[0], d[1], d[2] - d[0], d[3] - d[1],
							destIsContainer ? 1 : 0);
					}
				}
			}
			if (gStripDump && (d[0] == 0 || (d[0] >= 200 && d[0] < 400)))
			{
				static int bn = 0;
				if (++bn >= 12)
				{
					bn = 0;
					Logger::Get().WriteLine(LogLevel::Debug,
						"UiSpike: DCBUF self=%p dst(%d,%d,%d,%d) src %dx%d selfWxH=%dx%d cont=%d",
						self, d[0], d[1], d[2], d[3], s[2] - s[0], s[3] - s[1],
						selfW, selfH, destIsContainer ? 1 : 0);
				}
			}
			// v2.71.7 (hover-break diagnosis): DCBUF's 200..400 x band and
			// DCBL's 20-line cap are 2x-era and both went blind at 1.5x (bar
			// at x=158, cap consumed by the open). The down-arrow hover
			// repaint left ZERO lines. Trace EVERY blit into the disaster
			// container, capped, in call order - the hover repaint's exact
			// src/dst is what the fix needs. Diagnostic only.
			if (gStripDump && destIsContainer)
			{
				static int dbar = 0;
				if (dbar < 300)
				{
					dbar++;
					Logger::Get().WriteLine(LogLevel::Debug,
						"UiSpike: DBAR #%03d self=%p buf=%dx%d src(%d,%d,%d,%d) "
						"%dx%d dst(%d,%d,%d,%d) %dx%d a1=%p",
						dbar, self, selfW, selfH,
						s[0], s[1], s[2], s[3], s[2] - s[0], s[3] - s[1],
						d[0], d[1], d[2], d[3], d[2] - d[0], d[3] - d[1], a1);
				}
			}
			// Log the first bar cap (x=229) + every non-bar draw (ring, x<200),
			// each with its target buffer `self`, so we can tell if the ring draws
			// into the SAME force-recreated buffer as the bar or a different one.
			if (gClassBltLog < 20 && (d[0] < 200 || gClassBltLog < 2))
			{
				gClassBltLog++;
				Logger::Get().WriteLine(LogLevel::Debug,
					"UiSpike: DCBL self=%p src %dx%d (%d,%d,%d,%d)  dst %dx%d (%d,%d,%d,%d)",
					self, s[2] - s[0], s[3] - s[1], s[0], s[1], s[2], s[3],
					d[2] - d[0], d[3] - d[1], d[0], d[1], d[2], d[3]);
			}
			// PROBE the ring draw's SOURCE (a1 = drawContext / art atlas). Log its
			// vtable + (if it is the buffer class) its internal area rect
			// [0x14..0x20], so we know what/where the atlas is for the 2x art.
			if (gDrawCtxLog < 3 && a1 && d[0] == 0)
			{
				const int rw = d[2] - d[0];
				if (rw > 40 && rw < 160)
				{
					gDrawCtxLog++;
					// deref-ok: a1 is the swapped Blt slot's own draw-context argument (the game's live object)
					void** a1vt = *reinterpret_cast<void***>(a1);
					int32_t* af = reinterpret_cast<int32_t*>(a1);
					Logger::Get().WriteLine(LogLevel::Debug,
						"UiSpike: DCTX a1=%p a1vt=%p isBufCls=%d area[0x14..0x20]=(%d,%d,%d,%d)",
						a1, (void*)a1vt, (a1vt == kBufClassVt) ? 1 : 0,
						af[5], af[6], af[7], af[8]);
				}
			}
			// (The v2.9.3 atlas pixel dump, removed in v2.66.0, and the header of the
			// deleted legacy disaster ring block lived here: REGRESSION.md [CC-07].
			// The dump carried an absolute machine path into the shipped binary; if a
			// dump is ever needed again, derive its path at runtime beside the log.)
			// DJUNC (v4.0.17): the dock-tail overlap survives PicsOnTop, so
			// the tail pixels come from a draw none of the scoped probes
			// watch. Log EVERY blit - any surface, any class state - whose
			// dst crosses the arm/pill/pictures junction band (container-x
			// ~140..260, y ~250..470). A hit names the owner; total silence
			// means the arm is vector-FILLED by the arc helper (no atlas,
			// no Blt) and needs a different lever entirely.
			if (gStripDump)
			{
				static int djn = 0;
				const int jw = d[2] - d[0], jh = d[3] - d[1];
				if (djn < 60 && jw > 0 && jh > 0
					&& d[0] < 260 && d[2] > 140
					&& d[1] < 470 && d[3] > 250)
				{
					djn++;
					Logger::Get().WriteLine(LogLevel::Info,
						"UiSpike: DJUNC #%02d self=%p src(%d,%d,%d,%d) "
						"dst(%d,%d,%d,%d) %dx%d a1=%p",
						djn, self, s[0], s[1], s[2], s[3],
						d[0], d[1], d[2], d[3], jw, jh, a1);
				}
			}
			// (The legacy disaster ring block was deleted in v4.0.41; the dispatch
			// above owns every disaster element draw. History: REGRESSION.md [CC-08].)
			// ---- SUB-FLYOUT RING 2x (v2.15.0, derived from the RCAL trace) ----
			// The shared sub-flyout container paints its circle as an 80x53
			// sprite at dst(0,94) into a 258x482 buffer - measured, not guessed:
			//     RCAL buf=258x482  src(0,0) 80x53  dst(0,94) 80x53  cont=1
			// It fell through the disaster ring check by ONE PIXEL (that test is
			// `sw > 80`, and this sprite is exactly 80 wide), so it was blitted
			// unscaled into a 2x buffer = the 1x, detached circle.
			// The buffer is 2x of 129x241, so BOTH the size and the origin scale:
			// 80x53 -> 160x106, and (0,94) -> (0,188). No hand-tuned offset is
			// needed or wanted here - unlike disaster's RingDX/RingDY, this is
			// just "the whole thing is twice as big in a twice-as-big buffer".
			if (a1 && destIsSubContainer)
			{
				const int sw = s[2] - s[0], sh = s[3] - s[1];
				if (sw >= 70 && sw <= 140 && sh >= 35 && sh <= 100)
				{
					int32_t* af = reinterpret_cast<int32_t*>(a1);
					int32_t* cf = reinterpret_cast<int32_t*>(self);
					uint8_t* asrc = reinterpret_cast<uint8_t*>(
						static_cast<uintptr_t>(static_cast<uint32_t>(af[15])));
					uint8_t* cdst = reinterpret_cast<uint8_t*>(
						static_cast<uintptr_t>(static_cast<uint32_t>(cf[15])));
					const int astride = af[16], cstride = cf[16];
					const int cW = cf[7] - cf[5], cH = cf[8] - cf[6];
					const int sx0 = s[0], sy0 = s[1];
					// ORIGIN STAYS PUT, only the SIZE doubles.
					// v2.15.0 scaled the origin too ((0,94) -> (0,188)) and that
					// pushed the circle 94px down, undocking it. The evidence
					// against scaling the origin is direct: at (0,94) with 1x
					// size the player reported the sub-flyout "docked correctly but
					// it's 1x" - so that origin was already right; only the sprite
					// was small. SubRingDX/DY are live-tunable from the ini for
					// the final centring, so this never needs another rebuild.
					// Record dst + buffer size for the dock's placement law -
					// ringBltY varies per menu (94 zones, 119 rails...).
					gSubRingBltX = d[0];
					gSubRingBltY = d[1];
					gSubRingBufW = cW;
					gSubRingBufH = cH;
					// #95: gSubRingBltX/Y above are the RAW pre-offset values,
					// so the dock law and ringFresh are unaffected by the Auto
					// term - it moves the SPRITE only, never the recorded
					// origin, the strip, the bar or the items.
					const int dx0 = d[0] + SubRingDXEff() + gSubRingAutoX;
					const int dy0 = d[1] + SubRingDYEff() + gSubRingAutoY;
					// v2.24.0 (audit B1): fractional NN, same as the disaster
					// ring above; f=2 is bit-identical to the old *2 / >>1.
					const int subDstW = FloorScale(sw, gTierF);    // FLOOR, see decl
					const int subDstH = FloorScale(sh, gTierF);    // FLOOR, see decl
					if (asrc && cdst && astride > 0 && cstride > 0)
					{
						for (int oy = 0; oy < subDstH; oy++)
						{
							const int cy = dy0 + oy;
							if (cy < 0 || cy >= cH) continue;
							const uint8_t* srow = asrc
								+ (sy0 + static_cast<int>(oy / gTierF)) * astride;
							uint8_t* drow = cdst + cy * cstride;
							for (int ox = 0; ox < subDstW; ox++)
							{
								const int cx = dx0 + ox;
								if (cx < 0 || cx >= cW) continue;
								const uint8_t* sp = srow
									+ (sx0 + static_cast<int>(ox / gTierF)) * 4;
								if (sp[0] == 0xFF && sp[1] == 0x00 && sp[2] == 0xFF)
									continue;   // magenta colour key
								// mod frames are RGBA: skip semi-transparent
								// edge pixels (dark halo), keep a==0 stock art
								if (sp[3] > 0 && sp[3] < 128)
									continue;
								uint8_t* dp = drow + cx * 4;
								dp[0] = sp[0]; dp[1] = sp[1]; dp[2] = sp[2]; dp[3] = sp[3];
							}
						}
					}
					return 0;   // skip the game's 1x ring blit
				}
			}
			// BAR: shift left by gBarDX AND x-upscale by gBarWiden (manual: read the
			// atlas src, write gBarWiden-x-wide into the container) so the 2x pictures
			// nest inside the pill. Skips the original blit. Live-tunable (BarDX/BarW).
			// NOT gated on gDisasterDrawTuning: the bar x-upscale (gBarWiden) is
			// the generic "1x bar art in a 2x window" fix and is needed by every
			// hooked container. Only the disaster-measured SHIFT is gated, inside
			// DrawBarTile. Gating the whole block (v2.13.6) left the sub-flyout's
			// bar at 1x width so the icons no longer sat in it.
			// v2.24.0 (audit A7): the bar-tile x gate is BUFFER-RELATIVE now.
			// The game always blits the 53px-wide 1x bar art flush against the
			// buffer's right edge (SBLT: sub dst x = 205 = 258-53; disaster cap
			// x = 229 = 282-53), so "is this a bar tile" = "does it start at
			// selfW-53" (4px slop). The old absolute 200..400 band was only
			// true at f=2 and rejected every bar tile at 1.5x (141/159).
			if (a1 && d[0] >= selfW - 53 - 4 && d[0] < selfW
				// (v4.0.41) SUB-FLYOUT ONLY: every disaster bar draw is owned
				// by the rebuild dispatch above (which returns 0 before this
				// point); the disaster legacy arm is deleted.
				&& !gDisasterDrawTuning && destIsSubContainer
				&& (BarWidenEff() > 1.0f || BarDXEff() != 0))
			{
				if (BarWidenEff() > 1.0f)
				{
					// v4.0.21 single blend - the user-confirmed sub-flyout path.
					DrawBarScaled(self, a1, s, d);
					return 0;   // skip the original 1x-wide bar blit
				}
				d[0] += BarDXEff();   // widen==1: shift only
				d[2] += BarDXEff();
			}
		}
		return gClassBltOrig ? gClassBltOrig(self, a1, a2, a3, a4) : 0;
	}

	// STRIP (disaster pictures) Blt probe/actor. Patched onto the class Blt
	// vtable ONLY around the strip's Plot (SlotThunk2<88>). Logs each picture's
	// src/dst + the source texture size, so we can see the zoom (2x texture read
	// at 1x -> 1/4). Later doubles the src to un-zoom.
	CBltFn gStripBltOrig = nullptr;
	void*  gStripVtCopy[64] = {};        // instance-vtable copy for the strip's [0x68]
	int    gStripProbe = 24;             // log first N strip item blits
	// #149 CELLPROBE budgets - separate so a flood of correct draws can never
	// starve the one line that names the defect.
	// THE FIRST VERSION OF THIS PROBE COULD NOT SEE ITS OWN SUBJECT.
	// It logged only `texW > 200`, but the icons under investigation were 176
	// wide at the moment it ran - so the filter excluded exactly them, the six
	// lines it did print were all UNAFFECTED icons, and "zero MISMATCH" was a
	// statement about a set the defect could not be in.
	//
	// A FILTER IS A SCOPE, AND A SCOPE THAT EXCLUDES THE SUBJECT TURNS EVERY
	// RESULT INTO A FALSE ALL-CLEAR (law 42: a gate is only as honest as its
	// scope). The threshold is now below every real icon width, and the budget
	// is large enough to survive city load and still be spending when a flyout
	// opens - the first version's budget of 6 was gone before the menu existed.
	// DISARMED FOR RELEASE. The "ok" budget logs ordinary correct draws - pure
	// noise in a shipped log - so it is 0. The MISMATCH budget stays small but
	// non-zero: it fires ONLY when a strip's read stride disagrees with
	// texW/4, which is a real defect on a player's install and exactly what we
	// would need them to send us. Raise gCellProbeOk when investigating.
	int    gCellProbeOk = 0;
	int    gCellProbeBad = 8;
	const int kCellProbeMinW = 100;   // below the smallest 1x strip (176)
	// (gStrip2xSrc deleted v2.24.0, audit C8: the "x2 the src rect" experiment
	// was dead at 0 and hardwired *2 - removed so a re-enable can't resurrect
	// a 2x-only path.)
	int    gStripFieldScale = 2;         // >1 = scale the strip item-size/spacing fields
	                                     // [0xf4]/[0xf8]/[0xfc] so it reads the full
	                                     // 88x88 icon, lays out at 2x, AND the
	                                     // hit-test matches (clicks work). Live-tunable.
	// The STOCK (1x) strip item metrics, latched once. SlotThunk2<88> writes
	// base*f absolutely on every Plot, so the base must never be an already
	// scaled value. Primed by whichever sees the stock numbers first: the
	// born-scale detour (from SetItemMetrics' own argument, the earliest
	// possible moment) or SlotThunk2 itself.
	int    gStripBase4 = 0;              // [0xf4] item size
	int    gStripBase8 = 0;              // [0xf8] spacing
	int    gStripBaseC = 0;              // [0xfc] step extra
	bool   gStripBaseCap = false;

	// THE STEP-EXTRA MUST FLOOR. ROUNDING IT UP COSTS A WHOLE ROW.
	//
	// The strip's own Plot (0x0079AA70) decides how many rows are visible with
	//     visibleRows = (stripWinH + [0xFC]) / ([0xF8] + [0xFC])     // integer
	// and stock metrics are (44, 44, 5) against a window height that is ALWAYS
	// exactly 49n - 5. So stock computes (49n - 5 + 5) / 49 = n - exact,
	// remainder ZERO, for every n. THERE IS NO SPARE PIXEL IN THIS CONTROL, so
	// any upward drift in the denominator costs a whole row.
	//
	// Scaling the metrics: 44*1.5 = 66 exactly, but 5*1.5 = 7.5 - the ONLY
	// half-pixel in the system - and RoundHalfUp sends it to 8. The denominator
	// becomes 74 where the geometry only supports 73, the floor division drops
	// one row, and the last item of every flyout of 3+ items is unreachable
	// until the player scrolls. USER-REPORTED 2026-08-06.
	//
	// INTEGER TIERS ARE UNAFFECTED: 5*2 = 10 and 5*3 = 15 are already whole,
	// so floor and round agree exactly. Verified for n=2..12 at f=1.5/2/3 by
	// tools\uimap\emu\gate_strip_visible_rows.py, which also carries the
	// negative control (the old rule MUST fail at 1.5x).
	//
	// Same family as #142 (font point sizes) and #143 (cell divides): a rule
	// that is exact at every integer factor and silently wrong at 1.5.
	inline int ScaleStepExtra(int base, float f)
	{
		return static_cast<int>(std::floor(base * f));
	}
	int    gStripHitW = 0;              // if >0, force the strip item's [0xEC]/[0xF0]
	                                     // fields (currently -1 = "use natural ~44 size"
	                                     // -> only the right half is clickable) to this
	                                     // value, to make the FULL 2x cell selectable.
	                                     // Test with 88. Live-tunable (ini StripHitW).
	// THE SELECTABLE LAYER: the container's cursor routing hit-tests the strip via
	// the rect at strip-window offset 0x14 (mm[5..8] = L,T,R,B) -> 0x664c60. That
	// rect stayed at 1x width while we scaled the draw, so only the right half is
	// clickable. Widen it: SelDL extends the LEFT edge left, SelDR the RIGHT edge
	// right (px, in the rect's own coord space). Live-tunable. 0 = untouched.
	int    gSelDL = 0;
	int    gSelDR = 0;
	// gStripDump declared earlier (before BltClassThunk). DIAGNOSTIC (ini
	// StripDump): every ~30 slot-88 hits, log the strip list's scroll/count/
	// viewport fields (DSCROLL) + re-arm the DSTRIP item-Y probe; and in
	// BltClassThunk log the ring/bar dest buffer (DCBUF). No visual effect.


	// ---- ICONENLARGE (task #149 stage 2) ----------------------------------
	// THE FIX. Not a rect patch - those all failed, on screen, five times.
	//
	// The engine's rects are ALREADY CORRECT FOR A CORRECTLY-SIZED TEXTURE.
	// That is exactly why the 318 covered icons render perfectly: src
	// (88,0,176,88) out of a 352x88 texture IS state 1. The same rects out of a
	// plugin's un-upscaled 176x44 are the defect - two copies at rest, and on
	// hover state 3 asks for column 264 in a 176-wide texture and draws
	// nothing. The rects were never wrong. THE TEXTURE IS.
	//
	// So: hand the blit a bigger source and DO NOT TOUCH EITHER RECT. The
	// destination stays where the engine put it and the source rect stays as
	// the engine computed it, so the compositor sees precisely the draw it
	// issued. Every previous attempt modified a rect and every one flickered -
	// including the tiled variant that rewrote every pixel of the cell every
	// frame, which is what proves rect modification ITSELF is the trigger.
	//
	// Built entirely on the vendored SDK - no field offsets, no fake structs,
	// no raw memory arithmetic:
	//     cIGZGraphicSystem::CreateBuffer  -> cIGZBuffer
	//     cIGZBuffer::Init(w,h,colorType,depth)
	//     GetPixel / SetPixel              -> nearest-neighbour, exact copies
	//     Get/SetTransparency              -> the magenta key survives
	// The resample is the SAME exact-pixel operation Upscale2x.cs performs
	// offline, so a synthesised icon is identical in character to every icon we
	// already ship.
	//
	// SCOPE. Fires ONLY on the over-read signature - a 4-state strip whose
	// own cell (texW/4) is SMALLER than the cell the engine is drawing. Covered
	// art has texW/4 == cell by definition, so the 318 correct icons cannot be
	// touched by construction. This is not "the upscaler is on"; it is a repair
	// applied to precisely the case we have proven we break.
	struct EnlargeEntry { void* src; cIGZBuffer* big; int factor; };
	const int kEnlargeMax = 64;
	EnlargeEntry gEnlarge[kEnlargeMax] = {};
	int  gEnlargeN = 0;
	int  gEnlargeEpoch = -1;
	unsigned gEnlargeMade = 0;
	unsigned gEnlargeHit = 0;
	unsigned gEnlargeFail = 0;

	// #92 LAW: a pointer-keyed static that survives a city transition is a
	// CRASH, not a leak - city 2's allocator hands out city 1's addresses.
	void EnlargeReset()
	{
		for (int i = 0; i < gEnlargeN; i++)
		{
			if (gEnlarge[i].big) { gEnlarge[i].big->Release(); }
			gEnlarge[i].src = nullptr;
			gEnlarge[i].big = nullptr;
		}
		gEnlargeN = 0;
	}

	cIGZGraphicSystem* GetGraphicSystem()
	{
		// THE FIRST VERSION PASSED THE IID AS THE SERVICE ID AND GOT NULL
		// (log: 'gs=00000000'). GetSystemService takes (srvid, riid, ...) and
		// for the graphic system those are DIFFERENT numbers - the SDK's own
		// typedef spells it out:
		//   cRZSysServPtr<cIGZGraphicSystem, 7546940ul, 3289776732ul>
		//                                    ^IID       ^SRVID
		// Use the typedef rather than hand-copying either constant.
		static cIGZGraphicSystem* gs = nullptr;
		if (!gs)
		{
			cIGZGraphicSystemPtr p;
			if (p) { gs = p; }
		}
		return gs;
	}

	// Returns an enlarged copy of src, or nullptr (in which case the caller
	// leaves everything alone and the old broken-but-stable behaviour stands -
	// never a crash, never a half-applied fix).
	cIGZBuffer* GetEnlarged(void* srcUnknown, int factor)
	{
		if (!srcUnknown || factor < 2 || factor > 4) { return nullptr; }
		if (gEnlargeEpoch != gGaugeEpoch) { EnlargeReset(); gEnlargeEpoch = gGaugeEpoch; }
		for (int i = 0; i < gEnlargeN; i++)
		{
			if (gEnlarge[i].src == srcUnknown && gEnlarge[i].factor == factor)
			{
				gEnlargeHit++;
				return gEnlarge[i].big;
			}
		}
		if (gEnlargeN >= kEnlargeMax) { return nullptr; }

		cIGZUnknown* unk = static_cast<cIGZUnknown*>(srcUnknown);
		cIGZBuffer* src = nullptr;
		if (!unk->QueryInterface(GZIID_cIGZBuffer,
				reinterpret_cast<void**>(&src)) || !src)
		{
			gEnlargeFail++;
			return nullptr;
		}
		const int32_t sw = src->Width();
		const int32_t sh = src->Height();
		cIGZBuffer* big = nullptr;
		cIGZGraphicSystem* gs = GetGraphicSystem();
		if (sw > 0 && sh > 0 && sw <= 1024 && sh <= 1024 && gs
			&& gs->CreateBuffer(&big) && big)
		{
			cGZBufferColorType ct = src->GetColorType();
			if (big->Init(static_cast<uint32_t>(sw * factor),
					static_cast<uint32_t>(sh * factor),
					ct.bufferType, src->GetBitsPerPixel()))
			{
				// Nearest neighbour: every output pixel is an EXACT copy of a
				// source pixel, so no new colours are invented and the
				// transparency key stays exact. Same rule as the offline
				// pipeline.
				for (int32_t y = 0; y < sh * factor; y++)
				{
					const int32_t sy = y / factor;
					for (int32_t x = 0; x < sw * factor; x++)
					{
						big->SetPixel(x, y, src->GetPixel(x / factor, sy));
					}
				}
				uint32_t key = 0;
				if (src->GetTransparentColor(key)) { big->SetTransparency(key); }
				gEnlarge[gEnlargeN].src = srcUnknown;
				gEnlarge[gEnlargeN].big = big;
				gEnlarge[gEnlargeN].factor = factor;
				gEnlargeN++;
				gEnlargeMade++;
				gKickLeft = 8;   // enough redraws to reach every buffer in rotation
				Logger::Get().WriteLine(LogLevel::Info,
					"UiSpike: ICONENLARGE built %dx%d -> %dx%d (x%d) for src=%p "
					"- cached %d/%d, made=%u hits=%u",
					sw, sh, sw * factor, sh * factor, factor, srcUnknown,
					gEnlargeN, kEnlargeMax, gEnlargeMade, gEnlargeHit);
				src->Release();
				return big;
			}
			big->Release();
			big = nullptr;
		}
		gEnlargeFail++;
		if (gEnlargeFail <= 4)
		{
			Logger::Get().WriteLine(LogLevel::Info,
				"UiSpike: ICONENLARGE could not build for src=%p (%dx%d, gs=%p) "
				"- leaving the blit untouched.", srcUnknown, sw, sh, (void*)gs);
		}
		src->Release();
		return nullptr;
	}


	// ---- WIDEWATCH (task #149) - FIND THE SECOND DRAW ---------------------
	// STAGE 2 WORKS: the enlarged surface is built (176x44 -> 352x88, cache
	// stable at 2 entries, 0 failures) and the CORRECT icon renders. But an
	// UNCORRECTED copy is drawn too, alternating with ours.
	//
	// WHY THE PREVIOUS WATCH MISSED IT, and the rule this encodes: every
	// earlier probe was capped by a LINE BUDGET, so "no lines" could mean
	// "never happened" OR "budget spent". Both readings were available and I
	// took the wrong one twice today. COUNTERS CANNOT SATURATE THE WAY A LINE
	// BUDGET CAN (law 41): a failing event always leaves a number, even after
	// logging stops.
	//
	// So: unbounded counters on EVERY channel that could put pixels in the
	// plaza cells, dumped together at a fixed cadence so the RATIOS are
	// visible. If our corrected draw is 1/frame and something else is also
	// 1/frame, the alternation is explained and the culprit is named.
	//
	// PlotPresent 0x0099C498 is the one channel never yet instrumented. Static
	// analysis flagged its PRIMARY path as `call [eax+0x98]` on a RENDERER
	// surface - not a blit at all, so no blit hook of ours could ever see it.
	// That is the leading suspect for the second draw.

	void WideDump(const char* why)
	{
		gW_dump++;
		Logger::Get().WriteLine(LogLevel::Info,
			"UiSpike: WIDEWATCH #%u (%s) strip=%u sub=%u class=%u slot20=%u "
			"present=%u  | strip==sub means EVERY cell blit we see is "
			"corrected, so any leftover comes from a channel not counted here",
			gW_dump, why, gW_strip, gW_stripSub, gW_class, gW_s20, gW_present);
	}

	// THE FIRST VERSION DECLARED THIS __stdcall AND CRASHED THE GAME:
	// ACCESS_VIOLATION at 0x0099C4A1 - PlotPresent's first real instruction -
	// with ECX = 1. PlotPresent is a VIRTUAL: __thiscall, `this` in ECX, no
	// stack args. An __stdcall detour looks for `this` on the stack and leaves
	// ECX as whatever the caller happened to have, so the original ran against
	// garbage and dereferenced it.
	//
	// THAT IS THE SECOND CRASH TODAY FROM GUESSING A CALLING CONVENTION (the
	// first was a typed thunk on slot 20, PRIV_INSTRUCTION). THE RULE: for any
	// __thiscall target, write __fastcall(void* self, void* edx) - ecx maps to
	// self, edx is ignored, and NOTHING is cleaned that should not be. Never
	// infer arity or convention from a disassembly excerpt.
	typedef int(__fastcall* PlotPresentFn)(void*, void*);
	PlotPresentFn gOrigPlotPresent = nullptr;

	int __fastcall PlotPresentDetour(void* self, void* edx)
	{
		gW_present++;
		// Cadence keyed to OUR draw, not to wall time, so the ratio is exact.
		if ((gW_present % 60) == 0) { WideDump("present tick"); }
		return gOrigPlotPresent ? gOrigPlotPresent(self, edx) : 0;
	}

	void InstallWideWatch()
	{
		static bool done = false;
		if (done) { return; }
		done = true;
		const MH_STATUS init = MH_Initialize();
		if (init != MH_OK && init != MH_ERROR_ALREADY_INITIALIZED)
		{
			Logger::Get().WriteLine(LogLevel::Info,
				"UiSpike: WIDEWATCH MH_Initialize failed (%d).", init);
			return;
		}
		void* target = reinterpret_cast<void*>(0x0099C498);   // PlotPresent
		if (MH_CreateHook(target, reinterpret_cast<void*>(&PlotPresentDetour),
				reinterpret_cast<void**>(&gOrigPlotPresent)) != MH_OK
			|| MH_EnableHook(target) != MH_OK)
		{
			Logger::Get().WriteLine(LogLevel::Info,
				"UiSpike: WIDEWATCH could NOT hook PlotPresent at %p - a zero "
				"present count below is an INSTRUMENT FAILURE, not a finding.",
				target);
			gOrigPlotPresent = nullptr;
			return;
		}
		Logger::Get().WriteLine(LogLevel::Info,
			"UiSpike: WIDEWATCH installed on PlotPresent %p. Counters are "
			"UNBOUNDED - they cannot saturate like a log budget.", target);
	}

	int __fastcall BltStripThunk(void* self, void* /*edx*/,
		void* a1, void* a2, void* a3, void* a4)
	{
		if (a2 && a3)
		{
			int32_t* s = reinterpret_cast<int32_t*>(a2);   // srcRect
			int32_t* d = reinterpret_cast<int32_t*>(a3);   // dstRect
			IconWatch("STRIP", self, s, d);
			if (InPlazaCell(d)) { gW_strip++; }

			// ---- #162 THIN-BLIT PROBE, ON THE CHANNEL THAT ACTUALLY DRAWS --
			// THE SAME DETECTOR WAS FIRST PUT ON BltClassThunk, AND THE
			// COMMENT AT THE TOP OF THIS FILE NAMES THAT AS THE MISTAKE:
			// "a DIFFERENT CHANNEL from the class-wide BltClassThunk on
			// 0x00AC1400[29]. Scoping a fix to the wrong one of those two is
			// the single most repeated mistake in this file's history."
			//
			// MEASURED, 2026-08-16, a 3m14s city session with the mode cluster
			// on screen the whole time: BltClassThunk logged its ARMED line and
			// its FIRST-BLIT heartbeat and then never reached 2000 blits. The
			// shared buffer class barely draws the city HUD at all, so "0 thin
			// blits" there was a CHANNEL null, not an answer - exactly the law
			// about an instrument scoped to the wrong channel.
			//
			// This is the strip/item draw context's own slot 29, i.e. the blit
			// that puts BUTTON AND ITEM ART on screen. If a short bright run is
			// blitted anywhere, it comes through here.
			if (gThinBlt > 0)
			{
				gThinSeen++;
				if (gThinSeen == 1 || (gThinSeen % 2000) == 0)
				{
					Logger::Get().WriteLine(LogLevel::Info,
						"UiSpike: STRIPTHIN heartbeat - %d strip blit(s) seen, "
						"%d thin so far. A LARGE seen count with 0 thin is a "
						"real null; a SMALL one means this channel is idle too "
						"and the null is worthless.", gThinSeen, gThinHit);
				}
				const int tdw = d[2] - d[0], tdh = d[3] - d[1];
				if (tdw > 0 && tdh > 0 && (tdw <= 3 || tdh <= 3))
				{
					gThinHit++;
					if (gThinBlt > 0) { gThinBlt--; }
					Logger::Get().WriteLine(LogLevel::Info,
						"UiSpike: STRIPTHIN dst(%d,%d,%d,%d) %dx%d  "
						"src(%d,%d,%d,%d) %dx%d  img=%p  [seen %d, thin %d]",
						d[0], d[1], d[2], d[3], tdw, tdh,
						s[0], s[1], s[2], s[3], s[2] - s[0], s[3] - s[1],
						a1, gThinSeen, gThinHit);
				}
			}

			// ---- CELLPROBE (#149) - IS THE READ STRIDE THE TEXTURE'S CELL?
			// The user sees the enlarged icon SHIFTED RIGHT, and shifted
			// FURTHER on hover. Growing-with-state displacement is the #143
			// signature exactly: the draw picks its column as
			// `state * stride`, so if `stride != texW/4` the window walks off
			// the cell boundary a little more with every state.
			//
			// TWO INDEPENDENT BUDGETS, on purpose. A single budget is spent by
			// whatever draws first - at city load that is hundreds of correct
			// icons - and the ONE line that matters never prints. Then "no
			// mismatch logged" reads as "no mismatch exists", which is the
			// null-is-not-evidence trap this project keeps paying for. So the
			// mismatch case gets a budget no correct draw can touch, and the
			// matching case gets its own so a silent probe is still
			// distinguishable from a clean one.
			if (a1)
			{
				// deref-ok: a1 is the swapped Blt slot's own argument, null-checked, compared to kBufClassVt
				void** vt = *reinterpret_cast<void***>(a1);
				if (vt == kBufClassVt)
				{
					const int32_t* af = reinterpret_cast<const int32_t*>(a1);
					const int texW = af[7] - af[5];
					const int texH = af[8] - af[6];
					const int stride = s[2] - s[0];
					if (texW > kCellProbeMinW && stride > 0)
					{
						const bool match = (texW / 4) == stride;
						int& budget = match ? gCellProbeOk : gCellProbeBad;
						if (budget > 0)
						{
							budget--;
							Logger::Get().WriteLine(LogLevel::Info,
								"UiSpike: CELLPROBE %s tex=%dx%d texW/4=%d "
								"stride=%d state=%d src(%d,%d,%d,%d) "
								"dst(%d,%d,%d,%d) a1=%p",
								match ? "match" : "MISMATCH", texW, texH,
								texW / 4, stride,
								(stride > 0) ? (s[0] / stride) : -1,
								s[0], s[1], s[2], s[3],
								d[0], d[1], d[2], d[3], a1);
						}
					}
				}
			}
			if (gStripProbe > 0)
			{
				gStripProbe--;
				int aw = 0, ah = 0;
				// deref-ok: a1 null-checked; the slot's own draw-context argument
				void** a1vt = a1 ? *reinterpret_cast<void***>(a1) : nullptr;
				if (a1vt == kBufClassVt)
				{
					int32_t* af = reinterpret_cast<int32_t*>(a1);
					aw = af[7] - af[5]; ah = af[8] - af[6];
				}
				Logger::Get().WriteLine(LogLevel::Debug,
					"UiSpike: DSTRIP src %dx%d (%d,%d,%d,%d) dst %dx%d (%d,%d,%d,%d) "
					"a1=%p srcTex=%dx%d isBuf=%d",
					s[2] - s[0], s[3] - s[1], s[0], s[1], s[2], s[3],
					d[2] - d[0], d[3] - d[1], d[0], d[1], d[2], d[3],
					a1, aw, ah, (a1vt == kBufClassVt) ? 1 : 0);
			}
		}

		// ---- ICONCENTRE (task #149): ONE TRUE STATE, CENTRED ------------
		// MEASURED (424 blits, DSTRIP, menu open at f=2):
		//   src (88,0,176,88) dst 88x88 srcTex=352x88  -> 318 CORRECT
		//   src (88,0,176,88) dst 88x88 srcTex=176x44  -> 106 BROKEN
		// The draw (0x0079AA70, slot 88) cuts SRC at the SCALED stride. For
		// 352x88 art the true cell is 352/4 = 88, so that IS state 1. For
		// 1x 176x44 art the true cell is 44, so an 88-wide cut spans states
		// 2-3 and reads twice the texture height - the two-copies artefact.
		// The copy count is the scale ratio.
		//
		// NO RUNTIME UPSCALER: a runtime upscaler
		// would be unbounded and would end the property that every scaled
		// pixel comes from a diffable build step. AND THIS BLT CANNOT
		// STRETCH ANYWAY - the removed gBltScale test: a 2538x6102 dest changed
		// nothing, so Blt is a 1:1 copy clipped to dest and on-screen size
		// is the SOURCE size. Re-cutting SRC alone would therefore leave a
		// small icon jammed in the top-left - the ORIGINAL symptom.
		//
		// So the achievable cure is exact and modest: draw ONE TRUE STATE,
		// CENTRED in the cell. Native size, deliberate rather than broken.
		//
		// SELF-LIMITING: when texW/4 already equals the read stride the two
		// rects are left untouched, so the 318 correct blits never move and
		// this can neither fight the static packages nor double-scale.
		// Rect arithmetic only - no allocation, no pixels, no upscale.
		if (gIconFit && a1 && a2 && a3)
		{
			int32_t* s = reinterpret_cast<int32_t*>(a2);
			int32_t* d = reinterpret_cast<int32_t*>(a3);
			// deref-ok: a1 is the slot's own argument, compared to kBufClassVt before any field is read
			void** a1vt = *reinterpret_cast<void***>(a1);
			if (a1vt == kBufClassVt)   // only then are af[5..8] a real rect
			{
				const int32_t* af = reinterpret_cast<const int32_t*>(a1);
				const int texW = af[7] - af[5];
				const int texH = af[8] - af[6];
				const int srcW = s[2] - s[0], srcH = s[3] - s[1];
				const int dstW = d[2] - d[0], dstH = d[3] - d[1];
				if (texW > 0 && texH > 0 && (texW % 4) == 0
					&& srcW > 0 && srcH > 0 && dstW > 0 && dstH > 0)
				{
					const int cellW = texW / 4;
					// ICONSTATE (task #149): log EVERY blit of a 4-state strip, whether
					// or not the re-cut fires, with the state index the engine asked for.
					// Hover changes the state; if the icon vanishes on hover we need to
					// see WHICH state was requested and what source rect we handed back.
					// Logging only the acted-on case cannot answer that - the skipped
					// case is exactly the one that goes wrong.
					if (gIconFitLog > 0 && cellW > 0)
					{
						gIconFitLog--;
						Logger::Get().WriteLine(LogLevel::Info,
							"UiSpike: ICONSTATE tex %dx%d cell=%d src(%d,%d,%d,%d) %dx%d "
							"state=%d dst(%d,%d,%d,%d) willCut=%d",
							texW, texH, cellW, s[0], s[1], s[2], s[3], srcW, srcH,
							(srcW > 0 ? s[0] / srcW : -1),
							d[0], d[1], d[2], d[3],
							(srcW != texW && cellW < srcW && (srcW % cellW) == 0) ? 1 : 0);
					}
					// Only act when the read stride OVER-READS the real cell.
					// Never widen a read; never touch already-correct art.
					// srcW != texW IS LOAD-BEARING. A full-bitmap 1:1 draw has
					// srcW == texW, which is trivially a whole multiple of
					// texW/4, so without this the rule fires on ordinary UI art
					// and clips it to a quarter - the white line, shipped once
					// and re-caught by gate_iconcentre.py --selftest. An
					// over-read is a PARTIAL read, never the whole bitmap.
					gTalStrip++;
					if (gTalStrip == 1 || (gTalStrip % 40) == 0)   // 1 = positive control
					{
						gTalDump++;
						Logger::Get().WriteLine(LogLevel::Info,
							"UiSpike: ICONTALLY dump#%u strip=%u cut=%u skip=%u cover=%u "
							"(cut+skip MUST equal strip; cover MUST equal cut)",
							gTalDump, gTalStrip, gTalCut, gTalStrip - gTalCut, gTalCover);
					}
					if (srcW != texW && cellW < srcW && (srcW % cellW) == 0)
					{
						const int state = s[0] / srcW;   // which state was wanted
						const int nl = state * cellW;
						if (state >= 0 && state < 4 && nl + cellW <= texW)
						{
							// ICONCOVER (task #149). MEASURED: the re-cut blit SUCCEEDS
						// (ICONBLT ret is identical for it and for the perfect 2x
						// icons) and its rects are exactly right - yet the cell
						// flickers and blanks on hover. Cause: we paint 44x44 of an
						// 88x88 cell and NOTHING paints the remainder, so the other
						// three quarters keep the previous frame.
						//
						// A 1:1 clipped Blt CANNOT fill 88 from 44 (gBltScale: a
						// 2538x6102 dest changed nothing), and upscaling is
						// forbidden. So coverage needs a SECOND blit: run the
						// ORIGINAL rects first to fill the whole cell exactly as it
						// filled before, then let the corrected centred state draw
						// over it. The backdrop is the old doubled read - not
						// beautiful, but it is STABLE, and stability is what the
						// flicker and the hover-blank actually are.
						gTalCut++;
						// THE FIRST PRE-FILL USED THE ORIGINAL RECTS AND THAT WAS WRONG.
						// Those are the very rects that over-read: at state 3 the source is
						// (264,0,352,88), entirely outside a 176-wide texture, so the fill
						// drew NOTHING and the backdrop vanished on hover - user-observed,
						// 2026-08-14. Filling a cell from a read that lands outside the
						// source can never be stable.
						//
						// Instead tile the CORRECTED state across the cell, then let the
						// centred copy draw over it. Every read is in-texture by
						// construction, so coverage no longer depends on the state index.
						if (gIconCover && gStripBltOrig)
						{
							int32_t ts[4], td[4];
							for (int ty = 0; ty < dstH; ty += texH)
							{
								for (int tx = 0; tx < dstW; tx += cellW)
								{
									ts[0] = nl;  ts[1] = 0;
									ts[2] = nl + cellW;  ts[3] = texH;
									td[0] = d[0] + tx;  td[1] = d[1] + ty;
									td[2] = td[0] + cellW;  td[3] = td[1] + texH;
									if (td[2] > d[2]) { td[2] = d[2]; }
									if (td[3] > d[3]) { td[3] = d[3]; }
									// IconCover 2 = TILE-ONLY. Full coverage every frame from valid
							// in-texture states, so there is no uncovered region to hold the
							// previous frame - the buffer is never cleared (this class has NO
							// fill primitive: a vtable scan for rep/stos found none, with the
							// known Blt as positive control). Coverage is therefore the only
							// way to stop stale pixels without upscaling.
							gStripBltOrig(self, a1, ts, td, a4);
									gTalCover++;
								}
							}
						}
						// STAGE 2: swap the SOURCE, leave both rects exactly as the engine
						// set them. cellW < srcW is the over-read signature, so the factor
						// the engine expects is srcW/cellW.
						cIGZBuffer* bigger = GetEnlarged(a1, srcW / cellW);
						if (bigger)
						{
							gW_stripSub++;
							a1 = static_cast<void*>(bigger);
							return gStripBltOrig ? gStripBltOrig(self, a1, a2, a3, a4) : 0;
						}
						// no enlarged copy available -> change NOTHING. The icon stays
						// wrong but stable; a half-applied fix is worse than none.
						s[0] = nl;          s[1] = 0;
							s[2] = nl + cellW;  s[3] = texH;
							// centre the smaller copy inside the original cell
							const int ox = (gIconCentreOff || gIconCover == 2)
								? 0 : (dstW - cellW) / 2;
							const int oy = (gIconCentreOff || gIconCover == 2)
								? 0 : (dstH - texH) / 2;
							d[0] += (ox > 0) ? ox : 0;
							d[1] += (oy > 0) ? oy : 0;
							d[2] = d[0] + cellW;
							d[3] = d[1] + texH;
							if (gIconFitLog > 0)
							{
								gIconFitLog--;
								Logger::Get().WriteLine(LogLevel::Info,
									"UiSpike: ICONCENTRE tex %dx%d cell=%d state=%d "
									"src %d->%d dst cell %dx%d -> (%d,%d,%d,%d)",
									texW, texH, cellW, state, srcW, cellW,
									dstW, dstH, d[0], d[1], d[2], d[3]);
							}
						}
					}
				}
			}
		}
		// ICONBLT (task #149): the LAST place the pixels can go missing.
		// The source rects are proven in-texture and the art is proven
		// non-empty, yet the icon vanishes on hover - so capture what the
		// real Blt actually DID: its return value, and the rects as they
		// stand at the moment of the call. A failed or clipped-away blit is
		// invisible to every probe upstream of this line.
		if (gIconFit && gIconFitLog > 0 && a2 && a3)
		{
			int32_t* fs = reinterpret_cast<int32_t*>(a2);
			int32_t* fd = reinterpret_cast<int32_t*>(a3);
			const int r = gStripBltOrig
				? gStripBltOrig(self, a1, a2, a3, a4) : 0;
			gIconFitLog--;
			Logger::Get().WriteLine(LogLevel::Info,
				"UiSpike: ICONBLT ctx=%p ret=%d src(%d,%d,%d,%d) %dx%d "
				"dst(%d,%d,%d,%d) %dx%d",
				self, r, fs[0], fs[1], fs[2], fs[3], fs[2]-fs[0], fs[3]-fs[1],
				fd[0], fd[1], fd[2], fd[3], fd[2]-fd[0], fd[3]-fd[1]);
			return r;
		}
		return gStripBltOrig ? gStripBltOrig(self, a1, a2, a3, a4) : 0;
	}
	// (gFieldMask and gWinScale deleted v2.24.0, audit C6/C7. Both were dead
	// at 0 with hardwired *2 bodies. History for the record: doubling the
	// container fields on top of the force-recreated buffer clipped the art
	// ("choppy bar", v2.8.3) - buffer size alone is the whole scale lever;
	// and doubling the window rect [0xa8..0xb4] was a proven DEAD END
	// (v2.7.96/97: composite clips to the PARENT's notion of child size).
	// Deleted so a re-enable cannot resurrect 2x-only code at another tier.)
	int gBltLog = 0;
	// (gBltScale removed, audit B1: a3 (dest rect) proved NOT the size lever -
	// a 2538x6102 dest gave zero change => Blt is a 1:1 copy clipped to dest;
	// on-screen size = SOURCE buffer size.)

	bool SafeRead4(void* p, int* out4)
	{
		__try
		{
			const int32_t* r = reinterpret_cast<const int32_t*>(p);
			out4[0] = r[0]; out4[1] = r[1]; out4[2] = r[2]; out4[3] = r[3];
			return true;
		}
		__except (EXCEPTION_EXECUTE_HANDLER) { return false; }
	}

	int __fastcall BltThunk(void* self, void* /*edx*/,
		void* a1, void* a2, void* a3, void* a4)
	{
		// Log-only: the first few composite Blts' rects.
		if (gBltLog < 8)
		{
			gBltLog++;
			int r1[4] = { 0,0,0,0 }, r2[4] = { 0,0,0,0 }, r3[4] = { 0,0,0,0 };
			const bool ok1 = SafeRead4(a2, r1);
			const bool ok2 = SafeRead4(a3, r2);
			const bool ok3 = SafeRead4(a4, r3);
			Logger::Get().WriteLine(LogLevel::Debug,
				"UiSpike: DBLT this=%p a1=%p srcA2=(%d,%d,%d,%d ok%d) "
				"dstA3=(%d,%d,%d,%d ok%d) a4=%p(%d,%d,%d,%d ok%d)",
				self, a1,
				r1[0], r1[1], r1[2], r1[3], ok1 ? 1 : 0,
				r2[0], r2[1], r2[2], r2[3], ok2 ? 1 : 0,
				a4, r3[0], r3[1], r3[2], r3[3], ok3 ? 1 : 0);
		}
		return gOrigBlt ? gOrigBlt(self, a1, a2, a3, a4) : 0;
	}

	// ---- FLASH GUARD ------------------------------------------------------
	bool IsReadyWin(void* w)
	{
		for (int i = 0; i < gReadyCount; i++)
			if (gReadyWins[i] == w) return true;
		return false;
	}

	void AddReadyWin(void* w)
	{
		if (!w || IsReadyWin(w)) return;
		if (gReadyCount < 16) gReadyWins[gReadyCount++] = w;
	}

	// Class-level Plot gate. Walks <=4 parent hops to find the god-flyout ROOT
	// this window belongs to; non-flyout windows of the same class pass
	// through untouched. Only active once GetParentWin is runtime-verified
	// (gFgParentOk) so a wrong header slot can never crash a paint.
	bool ResolveShotPath(wchar_t* out, size_t outLen)
	{
		HMODULE self = nullptr;
		if (!GetModuleHandleExW(
				GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS |
				GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
				reinterpret_cast<LPCWSTR>(&ResolveShotPath), &self) || !self)
		{
			return false;
		}
		wchar_t path[MAX_PATH] = {};
		if (GetModuleFileNameW(self, path, MAX_PATH) == 0) { return false; }
		wchar_t* last = nullptr;
		for (wchar_t* q = path; *q; q++)
		{
			if (*q == L'\\' || *q == L'/') { last = q; }
		}
		if (!last) { return false; }
		*(last + 1) = L'\0';
		wcscpy_s(out, outLen, path);
		wcscat_s(out, outLen, L"SC4UIScale-advisor.bmp");
		return true;
	}

	// ---- #168 ADVISORSHOT: the PIXELS, after the paint, from the window's
	// own draw buffer. Ten fixes have been reasoned from geometry; not one
	// looked at what is actually on the surface. [Probe] AdvisorShot=1.
	//
	// The buffer is [win+0x68] - GetBufferToDrawTo, slot 94 / +0x178, resolved
	// as [ecx+0x68] (see the vtable note at the top of this file). We take it
	// AFTER the original Plot returns, so the paint is complete, and write the
	// window's own rect out as an uncompressed BMP beside the log.
	//
	// The lock/read pattern is ScanRegion's, unchanged: Lock(0x8000) first
	// because hardware surfaces read back blank without the dirty-update flag,
	// raw 32bpp bits when available, GetPixel otherwise, all inside SEH.
	int gAdvisorShot = 0;
	bool DumpWinPixels(void* self, int off, const wchar_t* path,
		int* ow, int* oh, int* oc, int* diagLock, int* diagBpp, int* diagStride)
	{
		*ow = 0; *oh = 0; *oc = 0;
		*diagLock = -2; *diagBpp = 0; *diagStride = 0;
		__try
		{
			void* raw = *reinterpret_cast<void**>(
				reinterpret_cast<char*>(self) + off);
			if (!raw) { return false; }
			cIGZBuffer* buf = nullptr;
			if (!reinterpret_cast<cIGZBuffer*>(raw)->QueryInterface(
					GZIID_cIGZBuffer, reinterpret_cast<void**>(&buf)) || !buf)
			{
				return false;
			}
			cIGZWin* w = static_cast<cIGZWin*>(self);
			const int x0 = w->GetL(), y0 = w->GetT();
			const int ww = w->GetW(), hh = w->GetH();
			const int bw = buf->Width(), bh = buf->Height();
			if (ww <= 0 || hh <= 0 || bw <= 0 || bh <= 0)
			{
				buf->Release(); return false;
			}
			int lockFlag = -1;
			if (buf->Lock(0x8000)) { lockFlag = 0x8000; }
			else if (buf->Lock(0)) { lockFlag = 0; }
			const int bpp = static_cast<int>(buf->GetBitsPerPixel());
			const unsigned int bits = buf->GetColorSurfaceBits();
			const int stride = static_cast<int>(buf->GetColorSurfaceStride());
			const bool useRaw = (bits != 0 && stride > 0 && bpp == 32);
			*diagLock = lockFlag; *diagBpp = bpp; *diagStride = stride;
			const uint8_t* base = reinterpret_cast<const uint8_t*>(
				static_cast<uintptr_t>(bits));
			FILE* f = nullptr;
			if (_wfopen_s(&f, path, L"wb") != 0 || f == nullptr)
			{
				if (lockFlag >= 0) { buf->Unlock(lockFlag); }
				buf->Release(); return false;
			}
			const int rowB = ((ww * 3) + 3) & ~3;
			const uint32_t pix = static_cast<uint32_t>(rowB) * hh;
			uint8_t hdr[54] = {};
			hdr[0] = 'B'; hdr[1] = 'M';
			*reinterpret_cast<uint32_t*>(hdr + 2) = 54 + pix;
			*reinterpret_cast<uint32_t*>(hdr + 10) = 54;
			*reinterpret_cast<uint32_t*>(hdr + 14) = 40;
			*reinterpret_cast<int32_t*>(hdr + 18) = ww;
			*reinterpret_cast<int32_t*>(hdr + 22) = hh;
			*reinterpret_cast<uint16_t*>(hdr + 26) = 1;
			*reinterpret_cast<uint16_t*>(hdr + 28) = 24;
			*reinterpret_cast<uint32_t*>(hdr + 34) = pix;
			fwrite(hdr, 1, 54, f);
			static uint8_t seen[4096];
			memset(seen, 0, sizeof(seen));
			int colours = 0;
			uint8_t* row = static_cast<uint8_t*>(malloc(rowB));
			if (!row)
			{
				fclose(f); if (lockFlag >= 0) { buf->Unlock(lockFlag); }
				buf->Release(); return false;
			}
			for (int yy = hh - 1; yy >= 0; yy--)
			{
				memset(row, 0, rowB);
				const int sy = y0 + yy;
				for (int xx = 0; xx < ww; xx++)
				{
					const int sx = x0 + xx;
					uint8_t r = 0, g = 0, b = 0;
					if (sx >= 0 && sy >= 0 && sx < bw && sy < bh)
					{
						if (useRaw)
						{
							const uint32_t v = *reinterpret_cast<const uint32_t*>(
								base + static_cast<size_t>(sy) * stride + sx * 4);
							r = static_cast<uint8_t>((v >> 16) & 0xFF);
							g = static_cast<uint8_t>((v >> 8) & 0xFF);
							b = static_cast<uint8_t>(v & 0xFF);
						}
						else
						{
							const uint32_t v = buf->GetPixel(
								static_cast<uint32_t>(sx), static_cast<uint32_t>(sy));
							buf->ConvertNativeValueToRGB(v, r, g, b);
						}
					}
					row[xx * 3 + 0] = b; row[xx * 3 + 1] = g; row[xx * 3 + 2] = r;
					const int k = ((r >> 3) << 10) | ((g >> 3) << 5) | (b >> 3);
					if (!(seen[k >> 3] & (1 << (k & 7))))
					{
						seen[k >> 3] |= static_cast<uint8_t>(1 << (k & 7));
						colours++;
					}
				}
				fwrite(row, 1, rowB, f);
			}
			free(row); fclose(f);
			if (lockFlag >= 0) { buf->Unlock(lockFlag); }
			buf->Release();
			*ow = ww; *oh = hh; *oc = colours;
			return true;
		}
		__except (EXCEPTION_EXECUTE_HANDLER) { return false; }
	}

	// ---- #162 DRAWPROBE: slot 88 (Plot) - THE CHANNEL THAT IS ACTUALLY
	// INSTALLED. [Probe] DrawProbe=<lines>. Default OFF.
	//
	// THE TWO PREVIOUS PROBES WERE ON CHANNELS THAT NEVER RAN.
	//   BltClassThunk  - buffer-class slot 29. Armed and executing, but a
	//                    3m14s city session produced under 2000 blits: the
	//                    shared buffer class barely draws the HUD at all.
	//   BltStripThunk  - the strip draw-context's slot 29, and installed ONLY
	//                    inside SlotThunk<88> when gStripProbe > 0, a key that
	//                    was never set. Zero lines, by construction.
	// Both cost the player a launch. This one is different for a reason that can
	// be checked BEFORE asking for a launch: FlashGuardThunk is written onto
	// vt[88] of every painting class at city load by the same code that emits
	// "DFG patched class vt=%p Plot=%p", and that line is in EVERY capture we
	// hold. The hook is proven installed and proven executing before the probe
	// is armed - which is the check PROBES-NEEDED.md section 1 demands and the
	// one I skipped twice.
	//
	// It logs the window id and its LIVE rect at paint time for the windows
	// under investigation. If the hat/people/advisor ids never appear, then
	// slot 88 is not what paints them either, and that is a REAL answer with a
	// working positive control - the heartbeat proves the thunk ran.
	int gDrawProbe = 0;
	int gDrawSeen = 0;
	const uint32_t kDrawWatch[] = {
		0xC988BC79,  // mayor's-hat button   (dashboard, design 97,37 60x46)
		0x4988BC6A,  // people button        (dashboard, design 138,93 54x42)
		0x2988BC85,  // sun/starburst button - the CONTROL: same family, and
		             // the workflow measured it as parity-immune
		0xCA15C7CF, 0x2A15C7F1, 0x8A15C802, 0x6A15C7BE,   // advisor FRAMES
		0x6A15C7AA, 0xAA15C7E2, 0xAA15C795,
		0x0A15C7D8, 0xEA15C7FA, 0x8A15C80C, 0x4A15C7C6,   // advisor FACES
		0x6A15C7B5, 0x6A15C7EA, 0x0A15C7A1,

		// ===== #176, 2026-08-16. USER-REPORTED at 1.5x, correct at 2x:
		// "Mayor rating is broken and the overall ratings are broken look at
		// their formatting" / "it's only half filled".
		//
		// TWO DIFFERENT WIDGETS, and the docs are explicit that they are NOT
		// the same subsystem (build_selective_safe.py:401-404). Do not treat a
		// reading from one as evidence about the other.
		//
		// (a) THE HUD MAYOR RATING BAR - reachable TODAY, which is why it is
		//     worth arming now. id 0x8A517556, clsid GZWinBMP, and GZWinBMP's
		//     vtable 0x00ADF6A0 is ALREADY one of the 8 classes PatchFlashGuard
		//     hooks (measured in capture 2026-08-16-142828), so this id needs no
		//     new hook and costs no behaviour change.
		//     Its .UI is area=(120,57,222,68) = 102x11 with
		//     imagerect=(0,0,102,11) cropping a 102x26 sheet {46a006b0,14015549}
		//     - i.e. only the TOP 11 of 26 rows are the resting band, and the
		//     controller (0x7E86C0-0x7E8A80) selects other bands by offsetting Y.
		//     THE SUSPECT NUMBER: that band height scales 11 -> 22 (2x) and
		//     11 -> 33 (3x), both exact, but 11 -> 16.5 at 1.5x, and we ship 17.
		//     A fractional band height is the same family as every other 1.5x
		//     defect, on the HEIGHT axis (see #177).
		0x8A517556,  // HUD Mayor Rating bar (GZWinBMP, vt already patched)

		// (b) THE CITY OPINION POLLS BARS - listed so they report the moment
		//     their class is reachable, but THEY WILL NOT REPORT YET AND THAT
		//     IS NOT A NULL RESULT (law 91). cSC4WinTrendBar has its OWN vtable
		//     0x00ABA430, and it is NOT among the 8 vtables PatchFlashGuardClass
		//     patched in the last capture - class-scoped draw hooks are
		//     vtable-scoped. Arming these without patching that vtable would
		//     produce a guaranteed silence that reads like an answer.
		//     kFgMax is 12 and 8 are used, so there are 4 free slots when we
		//     decide to spend one - deliberately NOT done in this build, because
		//     FlashGuardThunk can SUPPRESS a paint and these six are the very
		//     windows under complaint.
		0x6A5E6EDC, 0x6A5E6EDD, 0x6A5E6EDE,   // Environment / Traffic / Health
		0x6A5E6EDF, 0x6A5E6EE0, 0x6A5E6EE1,   // Education / Safety / Land Value
	};

	template <int K>
	uintptr_t __fastcall FlashGuardThunk(void* self, void* /*edx*/)
	{
		if (gFlashGuard && gFgParentOk)
		{
			cIGZWin* cur = reinterpret_cast<cIGZWin*>(self);
			cIGZWin* root = nullptr;
			for (int hop = 0; hop < 4 && cur; hop++)
			{
				cIGZWin* p = cur->GetParentWin();
				if (!p) break;
				if (p->GetID() == 0x9A47B417) { root = cur; break; }
				cur = p;
			}
			if (root && !IsReadyWin(root))
			{
				int slot = -1;
				for (int i = 0; i < 4; i++)
					if (gFgWaitRoot[i] == root) { slot = i; break; }
				if (slot < 0)
				{
					for (int i = 0; i < 4; i++)
						if (!gFgWaitRoot[i]) { slot = i; break; }
					if (slot < 0) slot = 0;
					gFgWaitRoot[slot] = root;
					gFgWaitN[slot] = 0;
				}
				if (++gFgWaitN[slot] <= 120)
					return 1;              // suppress the stock paint
				// pending too long (unmanaged flyout) -> fail-open: paint stock
			}
			else if (root)
			{
				for (int i = 0; i < 4; i++)
					if (gFgWaitRoot[i] == root)
					{
						gFgWaitRoot[i] = nullptr;
						gFgWaitN[i] = 0;
					}
			}
		}
		if (gDrawProbe > 0)
		{
			gDrawSeen++;
			if (gDrawSeen == 1)
			{
				Logger::Get().WriteLine(LogLevel::Info,
					"UiSpike: DRAWPROBE live - slot 88 paint #1 observed. This "
					"line is the positive control: the hook is installed AND "
					"executing. If no DRAWPROBE win= rows follow, slot 88 does "
					"not paint the watched windows - that is an ANSWER, not a "
					"dead probe.");
			}
			__try
			{
				cIGZWin* w = static_cast<cIGZWin*>(self);
				const uint32_t id = w->GetID();
				for (size_t i = 0; i < sizeof(kDrawWatch) / sizeof(kDrawWatch[0]); i++)
				{
					if (kDrawWatch[i] != id) { continue; }
					if (gDrawProbe <= 0) { break; }
					gDrawProbe--;
					Logger::Get().WriteLine(LogLevel::Info,
						"UiSpike: DRAWPROBE win=0x%08X rect=(%d,%d %dx%d) "
						"class=%p [paint %d]",
						id, w->GetL(), w->GetT(), w->GetW(), w->GetH(),
						*reinterpret_cast<void**>(self), gDrawSeen);
					break;
				}
			}
			__except (EXCEPTION_EXECUTE_HANDLER) {}
		}
		const uintptr_t fgRet = gFgOrig[K] ? gFgOrig[K](self) : 0;
		if (gAdvisorShot > 0)
		{
			__try
			{
				if (static_cast<cIGZWin*>(self)->GetID() == 0xCA15C7CF)
				{
					gAdvisorShot--;
					wchar_t path[MAX_PATH];
					if (ResolveShotPath(path, MAX_PATH))
					{
						// FIRST ATTEMPT READ BACK BLANK (colours=1). The
						// slot table in this file is explicit that 94
						// GetBufferToDrawTo is [ecx+0x68] and 93 GetDrawContext
						// is [ecx+0x6c], and it records that confusing the two
						// already cost a probe build once (#89). So try BOTH,
						// keep whichever yields real pixels, and PRINT the lock
						// diagnostics either way - without lockFlag/bpp/stride
						// a blank dump cannot be told apart from a wrong offset.
						const int offs[2] = { 0x68, 0x6c };
						for (int oi = 0; oi < 2; oi++)
						{
							int aw = 0, ah = 0, ac = 0;
							int dl = 0, db = 0, ds = 0;
							const bool ok = DumpWinPixels(self, offs[oi], path,
								&aw, &ah, &ac, &dl, &db, &ds);
							Logger::Get().WriteLine(LogLevel::Info,
								"UiSpike: ADVISORSHOT off=+0x%02X %s %dx%d "
								"colours=%d lock=%d bpp=%d stride=%d -> %S%s",
								offs[oi], ok ? "wrote" : "FAILED", aw, ah, ac,
								dl, db, ds, path,
								(ok && ac < 24)
									? "  ** REFUSAL: blank read, NOT 'no line' **"
									: "");
							if (ok && ac >= 24) { break; }   // real pixels: keep
						}
					}
				}
			}
			__except (EXCEPTION_EXECUTE_HANDLER) {}
		}
		return fgRet;
	}
}

namespace UiSpikeInternal
{
	typedef uintptr_t(__fastcall* FgThunkFn)(void*, void*);
	FgThunkFn const kFgThunks[kFgMax] = {
		&FlashGuardThunk<0>, &FlashGuardThunk<1>, &FlashGuardThunk<2>,
		&FlashGuardThunk<3>, &FlashGuardThunk<4>, &FlashGuardThunk<5>,
		&FlashGuardThunk<6>, &FlashGuardThunk<7>, &FlashGuardThunk<8>,
		&FlashGuardThunk<9>, &FlashGuardThunk<10>, &FlashGuardThunk<11>,
	};
	// FLASHSET (v2.30.0, task #50). THE instrument for the systemic 1x flash.
	// A panel that we scale while it is ALREADY VISIBLE has, by definition,
	// been painted at least once at 1x - that painted frame IS the flash the
	// user sees. A panel scaled while hidden cannot flash. So logging the
	// former, once per id, turns "almost every field flashes" into the exact
	// finite list of windows to fix, measured instead of guessed.
	//
	// This does NOT fix anything by itself and must never gate a paint (the
	// FlashGuard lesson). It is pure observation.
	// v2.31.0 CORRECTION to v2.30.0's own instrument. `IsVisible()` returns
	// the window's OWN flag bit - and both cGZWin constructors set
	// [this+0xC8] = 0x8903 (Visible|Enabled|Sortable|AcceptFocus), so EVERY
	// window is born "visible" by that test. v2.30.0 therefore reported
	// "already visible" for windows that had never been on screen, which
	// over-reports and cannot distinguish a real flash from a load-time
	// scale behind the loading screen.
	//
	// The engine's real on-screen test is an ANCESTOR WALK (0x0099EA70): a
	// window is on screen only if its own bit AND every ancestor's bit are
	// set. cIGZWin::GetParentWin() lets us do exactly that walk ourselves -
	// no hook, no exe call. A panel scaled while genuinely on screen has
	// been painted at least once at 1x; that is the flash.
	bool IsOnScreen(cIGZWin* w, int guard)
	{
		while (w && guard-- > 0)
		{
			if (!w->IsVisible()) { return false; }
			cIGZWin* parent = w->GetParentWin();
			if (parent == w) { break; }   // defensive: self-parent
			w = parent;
		}
		return true;
	}

	void NoteFlashCandidate(cIGZWin* win, uint32_t id, int n, const char* tag,
		unsigned int msSinceArm)
	{
		static uint32_t seen[96] = {};
		static int seenCount = 0;
		for (int i = 0; i < seenCount; i++) { if (seen[i] == id) return; }
		if (seenCount >= 96) return;
		seen[seenCount++] = id;
		const bool onScreen = IsOnScreen(win);
		Logger::Get().WriteLine(
			LogLevel::Debug,
			"UiSpike: FLASHSET %s 0x%08X scaled %d window(s) %s, +%ums after "
			"city arm (candidate #%d).",
			tag, id, n,
			onScreen ? "ON SCREEN - THIS ONE FLASHED"
			         : "own-bit visible but NOT on screen (no flash)",
			msSinceArm, seenCount);
	}
}

namespace
{
	// Patch one class vtable's Plot (slot 88) with the guard. Idempotent;
	// refuses our own instance copies; capped at kFgMax classes.
	void PatchFlashGuardClass(void** vt)
	{
		if (!vt || vt == gVtCopy || vt == gVtCopy2) return;
		for (int i = 0; i < gFgCount; i++)
			if (gFgVt[i] == vt) return;
		if (gFgCount >= kFgMax) return;
		DWORD oldProt;
		if (!VirtualProtect(&vt[88], sizeof(void*),
			PAGE_EXECUTE_READWRITE, &oldProt))
			return;
		gFgVt[gFgCount] = vt;
		gFgOrig[gFgCount] = reinterpret_cast<SlotFn>(vt[88]);
		vt[88] = reinterpret_cast<void*>(kFgThunks[gFgCount]);
		Logger::Get().WriteLine(LogLevel::Info,
			"UiSpike: DFG patched class vt=%p Plot=%p (idx %d)",
			(void*)vt, reinterpret_cast<void*>(gFgOrig[gFgCount]), gFgCount);
		gFgCount++;
	}
	// -----------------------------------------------------------------------

	template <int IDX>
	uintptr_t __fastcall SlotThunk(void* self, void* /*edx*/)
	{
		const int cap = 4;
		if (gSlotHits[IDX] < cap)
		{
			gSlotHits[IDX]++;
			Logger::Get().WriteLine(
				LogLevel::Debug,
				"UiSpike: DHOOK slot %d ENTER ptr%p (hit %d)",
				IDX, self, gSlotHits[IDX]);
		}

		// v2.11.25 DUAL-USE FIELD: [this+0xe0] is BOTH the container's hit-claim
		// width (slot121 0x0079AE30 claims the rightmost [0xe0] px - wants 2x,
		// set by the dock loop's ClaimScale) AND a Plot layout inset (1x base 53;
		// doubled it makes the game paint a SECOND orange bar beside our replay -
		// confirmed on screen on the v2.11.24 test). Hit-tests never run inside the
		// draw group, so: present the 1x value to every draw-group call and
		// restore the 2x claim immediately after. gVtCopy is installed only on
		// the disaster container instance, so `self` is always that container.
		int32_t* claimW = reinterpret_cast<int32_t*>(
			reinterpret_cast<char*>(self) + 0xE0);
		int32_t claimSaved = 0;
		// v2.24.0 (audit A6): the old "v / gClaimScale if divisible" halving
		// could never represent a 1.5x claim (int divisor/modulus). The sweep
		// now LATCHES the 1x value it scaled (gClaimOrig); the draw group
		// simply presents that latched 1x value and re-arms the scaled one
		// after. At f=2 this restores exactly the same numbers as the old
		// divide (scaled = 2*orig, restore = orig).
		if (gClaimScale > 1 && gClaimOrig > 0)
		{
			const int32_t v = *claimW;
			const int32_t scaled = RoundHalfUp(gClaimOrig * gTierF);
			if (v == scaled && scaled != gClaimOrig)
			{
				claimSaved = v;
				*claimW = gClaimOrig;
			}
		}

		// FIELD FORCE (slot 88 = container Plot). v2.7.76/77 doubled the 6 layout
		// fields ONCE at hook-install with ZERO visible effect. Two explanations:
		// the game recomputes them every frame (so a one-shot write is instantly
		// overwritten before Plot reads them), OR they aren't the drawing source.
		// This does BOTH the diagnostic and the fix: log the field values as Plot
		// SEES them (before we touch them) for the first frames -> if they read
		// 53/25/... the game reset them; then force them to 2x every frame right
		// before the original Plot runs, so Plot draws at 2x if these are the
		// real lever. Base (1x) was 53,25,12,94,62,6 -> 2x = 106,50,24,188,124,12.
		if (IDX == 88)
		{
			// OBSERVE-ONLY (v2.7.81). Forcing the window rect [0xa8..0xb4] made
			// the art SHRINK, because the full disassembly (0x79b0e0) shows TWO
			// rects: the draw path sizes the internal buffer [0xdc] from the
			// window rect [0xa8..0xb4], but the on-screen blit (0x79b43c) does
			// [0x68]->Blt(src=[0xdc], ...) using a SEPARATE rect at [0x24..0x30]
			// (filled via [0xdc]->GetBufferArea, vtable idx12). Before forcing
			// anything again, dump BOTH rects + the key pointers/flags at their
			// natural values, and track how they change open->settle. Then the
			// fix is exact, not guessed.
			//   [0x24..0x30] m[0x9..0xC]   window rect [0xa8..0xb4] m[0x2a..0x2d]
			//   dst buf [0x68] m[0x1A]   drawCtx [0xd8] m[0x36]   buf [0xdc] m[0x37]
			//   [0x100] m[0x40]   dirty byte[0x114]   flags [0x118/0x11c/0x120]
			int32_t* m = reinterpret_cast<int32_t*>(self);
			uint8_t* mb = reinterpret_cast<uint8_t*>(self);
			// (r24 force removed: v2.7.83 proved doubling r24 has no visible
			// effect - it is not the on-screen dest. The Blt hook below is the
			// real lever.)
			static int dcount = 0;
			static int32_t pa = -1, pb = -1, pc = -1, pd = -1;
			static int32_t qa = -1, qb = -1, qc = -1, qd = -1;
			const bool changed =
				(m[0x9] != pa || m[0xA] != pb || m[0xB] != pc || m[0xC] != pd ||
				 m[0x2a] != qa || m[0x2b] != qb || m[0x2c] != qc || m[0x2d] != qd);
			if (dcount < 30 && (dcount < 3 || changed))
			{
				dcount++;
				pa = m[0x9]; pb = m[0xA]; pc = m[0xB]; pd = m[0xC];
				qa = m[0x2a]; qb = m[0x2b]; qc = m[0x2c]; qd = m[0x2d];
				Logger::Get().WriteLine(LogLevel::Debug,
					"UiSpike: DOBS n=%d r24=(%d,%d,%d,%d) win=(%d,%d,%d,%d) "
					"dst68=0x%X ctx=0x%X buf=0x%X v100=%d dirty=0x%02X f118=%d f11c=%d f120=%d",
					dcount, m[0x9], m[0xA], m[0xB], m[0xC],
					m[0x2a], m[0x2b], m[0x2c], m[0x2d],
					(unsigned)m[0x1A], (unsigned)m[0x36], (unsigned)m[0x37],
					m[0x40], mb[0x114], m[0x46], m[0x47], m[0x48]);
				// Measure the dest buffer [0x68] and the cached src buffer [0xdc]
				// dimensions - this reveals whether the on-screen size is clamped
				// by a fixed per-window slot (dst68 = 282x678) or the full screen.
				int q1 = -1, w1 = -1, h1 = -1, b1 = -1;
				int q2 = -1, w2 = -1, h2 = -1, b2 = -1;
				void* dst = reinterpret_cast<void*>(static_cast<uintptr_t>(
					static_cast<uint32_t>(m[0x1A])));
				void* src = reinterpret_cast<void*>(static_cast<uintptr_t>(
					static_cast<uint32_t>(m[0x37])));
				if (dst) SafeBufProbe(dst, &q1, &w1, &h1, &b1);
				if (src) SafeBufProbe(src, &q2, &w2, &h2, &b2);
				Logger::Get().WriteLine(LogLevel::Debug,
					"UiSpike: DOBS   dst68 qi=%d %dx%d bpp=%d | srcBuf qi=%d %dx%d bpp=%d",
					q1, w1, h1, b1, q2, w2, h2, b2);
			}
		}

		// BLT HOOK: swap dest buffer [0x68]'s vtable to our copy so the
		// container's screen composite routes through BltThunk, ONLY around this
		// Plot call; restored immediately after. Container only (IDX==88).
		void* bltDst = nullptr;
		void** bltSavedVt = nullptr;
		void* ctxBuf = nullptr;
		void** ctxSavedVt = nullptr;
		if (IDX == 88)
		{
			int32_t* mm = reinterpret_cast<int32_t*>(self);
			// (PER-FIELD ISOLATION [gFieldMask, v2.7.90] and WINDOW-RECT DOUBLE
			// [gWinScale, v2.7.96] deleted v2.24.0, audit C6/C7: both dead at 0
			// with hardwired *2 bodies. Buffer size is the whole scale lever -
			// field doubling clipped the art, window-rect doubling was a proven
			// dead end. Deleted so a re-enable can't resurrect 2x-only code.)
			// FORCE BUFFER RECREATION (v2.8.1). The [0xdc] buffer is created once
			// and reused, so Init never fires on static frames (DINIT was empty).
			// Corrupt the buffer's cached width field [buf+0x1c] so Plot's validity
			// check (GetWidth vs window) fails -> Plot releases + recreates it at
			// the real window size, so the 0x1c corruption is transient.
			{
				void* buf = reinterpret_cast<void*>(static_cast<uintptr_t>(
					static_cast<uint32_t>(mm[0x37])));
				const int winW = mm[0x2c] - mm[0x2a];   // current window width (282)
				// Only force a recreate while the buffer is STALE (cached width !=
				// the window — e.g. the 141 buffer left from an early small window).
				// Corrupt [0x1c] so Plot's validity fails -> it recreates at the 282
				// window -> buffer becomes 282 (2x the stale 141). Once it matches,
				// stop -> validity passes -> stable (no per-frame recreate loop).
				if (buf && reinterpret_cast<int32_t*>(buf)[7] != winW)
				{
					reinterpret_cast<int32_t*>(buf)[7] = 0x7FFF;   // [0x1c] bogus
					reinterpret_cast<uint8_t*>(self)[0x114] |= 1;  // dirty
				}
			}
			bltDst = reinterpret_cast<void*>(static_cast<uintptr_t>(
				static_cast<uint32_t>(mm[0x1A])));
			if (bltDst)
			{
				// deref-ok: bltDst is the hooked slot's own destination buffer (measured mm[0x1A]), null-checked
				void** vt = *reinterpret_cast<void***>(bltDst);
				if (vt != gBltVtCopy)
				{
					for (int i = 0; i < 64; i++) gBltVtCopy[i] = vt[i];
					gOrigBlt = reinterpret_cast<BltFn>(vt[29]);
					gBltVtCopy[29] = reinterpret_cast<void*>(&BltThunk);
				}
				bltSavedVt = vt;
				*reinterpret_cast<void***>(bltDst) = gBltVtCopy;
			}
			// Swap the container BUFFER [0xdc]'s vtable so its internal element
			// draws route through BltThunkCtx (halves srcRect). Restored after.
			ctxBuf = reinterpret_cast<void*>(static_cast<uintptr_t>(
				static_cast<uint32_t>(mm[0x37])));
			if (ctxBuf)
			{
				// deref-ok: ctxBuf is the hooked slot's own context buffer (measured mm[0x37]), null-checked
				void** vt = *reinterpret_cast<void***>(ctxBuf);
				if (vt != gCtxVtCopy)
				{
					for (int i = 0; i < 64; i++) gCtxVtCopy[i] = vt[i];
					gCtxOrigBlt = reinterpret_cast<BltFn>(vt[29]);
					gCtxVtCopy[29] = reinterpret_cast<void*>(&BltThunkCtx);
					// DIAGNOSTIC (v2.7.99): log the buffer class vtable + key
					// method addrs so we can disassemble Init(0xc) / GetBufferArea
					// (0x30) offline and pin the 141-vs-282 (0.5) mechanism. The
					// on-screen flyout size == this buffer's PHYSICAL size.
					Logger::Get().WriteLine(LogLevel::Debug,
						"UiSpike: DBVT bufVt=%p init0xc=%p getW0x24=%p getH0x28=%p "
						"getArea0x30=%p blt0x74=%p",
						(void*)vt, vt[3], vt[9], vt[10], vt[12], vt[29]);
				}
				ctxSavedVt = vt;
				*reinterpret_cast<void***>(ctxBuf) = gCtxVtCopy;
			}
		}

		// Patch the buffer CLASS vtable for the disaster container (IDX==88):
		// the class Blt (slot 29) and, with IconFit, the present watch (slot 20).
		// (Until the 2026-09-25 audit this also held the Init-slot patch and a
		// condition built from knobs that were all hardwired off, plus
		// gRing2xBlit = 1, which made it always true.)
		if (IDX == 88)
		{
			if (!gBufVtWritable)
			{
				DWORD oldProt;
				if (VirtualProtect(&kBufClassVt[0], 64 * sizeof(void*),
					PAGE_EXECUTE_READWRITE, &oldProt))
					gBufVtWritable = true;
			}
			if (gBufVtWritable)
			{
				// v2.11.2: PERMANENT patch. Leave the class Blt hooked (do NOT
				// restore after this Plot) so the ring/bar scaler also fires
				// during the scroll-arrow repaint, which runs OUTSIDE this Plot
				// and was collapsing the flyout to 1x. Transforms are gated to
				// the container buffer (destIsContainer) inside BltClassThunk,
				// so other UI sharing this buffer class is untouched.
				if (!gClassBltOrig)
					gClassBltOrig = reinterpret_cast<CBltFn>(kBufClassVt[29]);
				if (kBufClassVt[29] != reinterpret_cast<void*>(&BltClassThunk))
					kBufClassVt[29] = reinterpret_cast<void*>(&BltClassThunk);
				// PRESENTWATCH install (task #149). Same permanent-class-patch
				// discipline as the Blt above, but slot 20 (+0x50) - the present
				// path that copies a window's PRIVATE BUFFER out, which never
				// routes through slot 29 and so was invisible to every probe we
				// built. Patched on BOTH known buffer classes: 0x00AC1400 and
				// 0x00ADB418 (its slot 29 is 0x00991BA0 and can take a renderer
				// path under dgVoodoo). LOG ONLY - it calls through.
				if (gIconFit)
				{
					InstallWideWatch();
					if (!gS20Orig0)
					{
						gS20Orig0 = kBufClassVt[20];
						kBufClassVt[20] = reinterpret_cast<void*>(&Slot20Thunk0);
					}
					if (!gS20Orig1)
					{
						DWORD oldP = 0;
						if (VirtualProtect(&kBufClassVt2[20], sizeof(void*),
							PAGE_EXECUTE_READWRITE, &oldP))
						{
							gS20Orig1 = kBufClassVt2[20];
							kBufClassVt2[20] = reinterpret_cast<void*>(&Slot20Thunk1);
							VirtualProtect(&kBufClassVt2[20], sizeof(void*), oldP, &oldP);
						}
					}
					static unsigned s20Dump = 0;
					if (++s20Dump % 40 == 0)
					{
						Logger::Get().WriteLine(LogLevel::Info,
							"UiSpike: PRESENTWATCH tally anySlot20=%u plazaCell=%u "
							"(anySlot20==0 means the thunk never ran - instrument "
							"failure, NOT a finding)", gS20Any, gS20Cell);
					}
				}
			}
		}

		const uintptr_t ret = gOrigSlot[IDX](self);

		if (IDX == 88 && bltDst && bltSavedVt)
		{
			*reinterpret_cast<void***>(bltDst) = bltSavedVt;
		}
		if (IDX == 88 && ctxBuf && ctxSavedVt)
		{
			*reinterpret_cast<void***>(ctxBuf) = ctxSavedVt;
		}
		if (claimSaved)
		{
			*claimW = claimSaved;   // re-arm the 2x hit-claim after the draw call
		}

		// CAA OBSERVE (slot 89 = CalcAbsoluteArea): v2.7.74 proved the
		// return value (0x06752001) is NOT a rect pointer — same value for
		// both container and strip, reads as garbage when dereferenced.
		// Log-only now; the rect-modification experiment is dead.
		if (IDX == 89 && gCaaLogCount < 5)
		{
			gCaaLogCount++;
			Logger::Get().WriteLine(LogLevel::Debug,
				"UiSpike: CAA ptr%p ret=0x%08X (not a rect ptr)", self, (unsigned)ret);
		}

		// DPOS tracker on Plot (slot 88).
		if (IDX == 88 && gPosFrames < 4000)
		{
			gPosFrames++;
			int aL = 0, aT = 0, cw = 0, ch = 0;
			if (SafeAbsRect(self, &aL, &aT, &cw, &ch))
			{
				if (aL != gLastPosL || aT != gLastPosT
					|| cw != gLastPosW || ch != gLastPosH)
				{
					gLastPosL = aL; gLastPosT = aT; gLastPosW = cw; gLastPosH = ch;
					if (gPosLogged < 60)
					{
						gPosLogged++;
						Logger::Get().WriteLine(LogLevel::Debug,
							"UiSpike: DPOS frame=%d cont.abs(%d,%d) %dx%d",
							gPosFrames, aL, aT, cw, ch);
					}
				}
			}
		}

		return ret;
	}

	// Second thunk set for the disaster STRIP window (vtable 0x00AB6D88).
	// Identical logic but uses gOrigSlot2/gSlotHits2 so the container's
	// vtable copy (gVtCopy) is not clobbered.
	template <int IDX>
	uintptr_t __fastcall SlotThunk2(void* self, void* /*edx*/)
	{
		const int cap = 4;
		if (gSlotHits2[IDX] < cap)
		{
			gSlotHits2[IDX]++;
			Logger::Get().WriteLine(
				LogLevel::Debug,
				"UiSpike: DHOOK2 slot %d ENTER ptr%p (hit %d)",
				IDX, self, gSlotHits2[IDX]);
		}

		// x2 the strip's item-size / spacing fields ([0xf4]/[0xf8]/[0xfc]) BEFORE
		// its Plot so it reads the full 88x88 icon (not 1/4), lays pictures out at
		// 2x, and the HIT-TEST uses the same 2x rects (clicks land). Capture the
		// natural values once; apply every Plot.
		if (IDX == 88 && gStripFieldScale > 1)
		{
			int32_t* mm = reinterpret_cast<int32_t*>(self);
			// v2.36.0: the latch lives at file scope (gStripBase*) so the
			// born-scale path can PRIME it from the builder's own stock
			// argument. It is a latch of the 1x base, and this block writes
			// base*f absolutely (never multiplying in place) - so if the base
			// ever latched an already-scaled 88 this would write 176. That is
			// exactly why priming it matters (law 30).
			if (!gStripBaseCap && mm[0x3d] > 0 && mm[0x3d] < 200)
			{
				gStripBase4 = mm[0x3d];   // [0xf4] item size
				gStripBase8 = mm[0x3e];   // [0xf8] spacing
				gStripBaseC = mm[0x3f];   // [0xfc] step extra
				gStripBaseCap = true;
			}
			if (gStripBaseCap)
			{
				// v2.24.0 (audit A5): scale by the TIER FACTOR, not the int
				// flag (an int could never be 1.5; gStripFieldScale is the
				// enable switch now). f=2: RoundHalfUp(sf*2) == sf*2 exactly.
				mm[0x3d] = RoundHalfUp(gStripBase4 * gTierF);
				mm[0x3e] = RoundHalfUp(gStripBase8 * gTierF);
				mm[0x3f] = ScaleStepExtra(gStripBaseC, gTierF);   // FLOOR, see decl
			}
			// EXPERIMENT: force the item hit/selection size fields ([0xEC]=mm[0x3b],
			// [0xF0]=mm[0x3c], both -1 = "natural ~44") to make the full 2x cell
			// clickable. Live-tunable (StripHitW); 0 = leave untouched.
			if (gStripHitW > 0)
			{
				mm[0x3b] = gStripHitW;
				mm[0x3c] = gStripHitW;
			}
		}

		// DIAGNOSTIC: dump the list's candidate scroll/count/viewport fields every
		// ~30 hits + re-arm the DSTRIP item-Y probe, so a click on the up/down arrow
		// shows which field is the scroll offset and whether the item Y's shift.
		if (IDX == 88 && gStripDump)
		{
			int32_t* mm = reinterpret_cast<int32_t*>(self);
			static int dcnt = 0;
			if (++dcnt >= 30)
			{
				dcnt = 0;
				Logger::Get().WriteLine(LogLevel::Debug,
					"UiSpike: DSCROLL self=%p [0x90]=%d [0x94]=%d [0x98]=%d [0x9C]=%d "
					"[0xA0]=%d [0xA4]=%d [0xB0]=%d [0xE0]=%d [0xE4]=%d [0xE8]=%d "
					"[0xEC]=%d [0xF0]=%d [0xF4]=%d [0xF8]=%d [0xFC]=%d [0x100]=%d "
					"[0x104]=%d [0x118]=%d",
					self, mm[0x24], mm[0x25], mm[0x26], mm[0x27],
					mm[0x28], mm[0x29], mm[0x2C], mm[0x38], mm[0x39], mm[0x3A],
					mm[0x3B], mm[0x3C], mm[0x3D], mm[0x3E], mm[0x3F], mm[0x40],
					mm[0x41], mm[0x46]);
				// Strip WINDOW rect (the HIT region) vs its [0x68] dest buffer area
				// (where the pictures actually composite) -> reveals the hit-vs-visual
				// x offset behind "only the right half is clickable".
				cIGZWin* sw = reinterpret_cast<cIGZWin*>(self);
				// deref-ok: self is the hooked window; +0x68 is its measured dest-buffer field (probe-only, gStripProbe > 0)
				void* s68d = *reinterpret_cast<void**>(
					reinterpret_cast<char*>(self) + 0x68);
				int b5 = 0, b6 = 0, b7 = 0, b8 = 0;
				if (s68d)
				{
					int32_t* bb = reinterpret_cast<int32_t*>(s68d);
					b5 = bb[5]; b6 = bb[6]; b7 = bb[7]; b8 = bb[8];
				}
				Logger::Get().WriteLine(LogLevel::Debug,
					"UiSpike: DSWIN winL=%d winT=%d winW=%d winH=%d buf68Area=(%d,%d,%d,%d)",
					sw->GetL(), sw->GetT(), sw->GetW(), sw->GetH(), b5, b6, b7, b8);
				// RAW field dump 0x40..0x134 so a stray ~44/176 (the un-doubled
				// hit-test cell width, right-aligned in the 88 cell) can be spotted.
				for (int off = 0x40; off <= 0x130; off += 0x20)
				{
					int k = off / 4;
					Logger::Get().WriteLine(LogLevel::Debug,
						"UiSpike: DRAW6 @0x%02X: %d %d %d %d %d %d %d %d",
						off, mm[k], mm[k + 1], mm[k + 2], mm[k + 3],
						mm[k + 4], mm[k + 5], mm[k + 6], mm[k + 7]);
				}
				gStripProbe = 8;   // re-log 8 item dst-Y's to see the scroll shift
			}
		}

		// Hook the strip's DEST buffer [0x68] instance around its Plot so each
		// per-picture blit routes through BltStripThunk (probe + optional 2x-src
		// un-zoom). Instance swap (not class) because [0x68] is the screen dest,
		// a different class than the container buffer. Restored right after.
		void*  s68 = nullptr;
		void** s68SavedVt = nullptr;
		if (IDX == 88 && gStripProbe > 0)
		{
			// deref-ok: self is the hooked window; +0x68 measured (probe-only, gStripProbe > 0)
			s68 = *reinterpret_cast<void**>(reinterpret_cast<char*>(self) + 0x68);
			if (s68)
			{
				// deref-ok: s68 null-checked; the window's own dest buffer
				void** vt = *reinterpret_cast<void***>(s68);
				if (vt != reinterpret_cast<void**>(gStripVtCopy))
				{
					for (int i = 0; i < 64; i++) gStripVtCopy[i] = vt[i];
					gStripBltOrig = reinterpret_cast<CBltFn>(vt[29]);
					gStripVtCopy[29] = reinterpret_cast<void*>(&BltStripThunk);
				}
				s68SavedVt = vt;
				*reinterpret_cast<void***>(s68) =
					reinterpret_cast<void**>(gStripVtCopy);
			}
		}

		const uintptr_t ret = gOrigSlot2[IDX](self);

		// AFTER CalcAbsoluteArea (slot 89) recomputes the SELECTABLE RECT at offset
		// 0x14 (mm[5..8] = L,T,R,B) - the rect the container's cursor routing
		// hit-tests via 0x664c60 - re-apply the widen so it survives to routing
		// time (a Plot-time write got wiped by CAA). CAA writes the natural rect
		// fresh each call, so we just apply the delta. SelDL extends the LEFT edge
		// left, SelDR the RIGHT edge right; both accept negatives.
		if (IDX == 89 && (gSelDL != 0 || gSelDR != 0))
		{
			int32_t* mm = reinterpret_cast<int32_t*>(self);
			const int natL = mm[5], natR = mm[7];
			mm[5] = natL - gSelDL;
			mm[7] = natR + gSelDR;
			if (gStripDump)
			{
				static int sc = 0;
				if (++sc >= 15)
				{
					sc = 0;
					Logger::Get().WriteLine(LogLevel::Debug,
						"UiSpike: DSEL(CAA) natL=%d natR=%d -> L=%d R=%d T=%d B=%d",
						natL, natR, mm[5], mm[7], mm[6], mm[8]);
				}
			}
		}

		if (s68 && s68SavedVt)
		{
			*reinterpret_cast<void***>(s68) = s68SavedVt;
		}

		// CAA2 OBSERVE (same finding as CAA: not a rect pointer).
		if (IDX == 89 && gCaaLogCount2 < 5)
		{
			gCaaLogCount2++;
			Logger::Get().WriteLine(LogLevel::Debug,
				"UiSpike: CAA2 ptr%p ret=0x%08X (not a rect ptr)", self, (unsigned)ret);
		}


		// ICONKICK2 (task #149): REFRESH EVERY BUFFER IN THE PRESENT ROTATION.
		// MEASURED: strip=84 draws vs present=104880 - a ~1248:1 ratio - so what
		// reaches the screen is a buffer that PERSISTS between draws. Our
		// substituted (correct) art lands in whichever buffer is current while
		// another in the rotation still holds the pre-fix image; alternating
		// presentation of the two IS the flicker. ONE correct draw can never be
		// enough. This also explains every earlier failure: correct rects,
		// centred rects, and a fully tiled cell all flickered because each only
		// ever reached one buffer per draw.
		//
		// Writes the dirty byte DIRECTLY - [win+0x70] is the sole field slot 91
		// InvalidateSelf sets (`mov byte [ecx+0x70],1` at 0x0099BECC). A one-byte
		// store to a documented field has no calling convention to get wrong,
		// and both of today's crashes came from getting one wrong.
		if (IDX == 88 && gKickLeft > 0 && self)
		{
			gKickLeft--;
			*(reinterpret_cast<uint8_t*>(self) + 0x70) = 1;
		}
		return ret;
	}

	// Point-in-arrow test, ABSOLUTE screen px. Mayor sub-flyout only: the
	// disaster flyout uses the stock atlas (no back arrow) and its click
	// machinery is LOCKED.
	inline bool InSubArrowAbs(int32_t x, int32_t y)
	{
		return gArrowClick && !gDisasterDrawTuning &&
			gSubArrowAbs[2] >= gSubArrowAbs[0] &&
			x >= gSubArrowAbs[0] && x <= gSubArrowAbs[2] &&
			y >= gSubArrowAbs[1] && y <= gSubArrowAbs[3];
	}

	// --- Click-path hooks on the strip: the two VERIFIED list handlers ---
	// Log the click coordinates (x,z,mods) each handler receives, so a working
	// (right-half) vs dead (left-half) click reveals the coordinate space and
	// where the SELECTABLE region actually sits vs the drawn pictures.
	bool __fastcall Mouse136Thunk(void* self, void* edx, int32_t x, int32_t z,
		uint32_t mods)
	{
		if (gStripDump)
			Logger::Get().WriteLine(LogLevel::Debug,
				"UiSpike: DHIT136 x=%d z=%d mods=%08X", x, z, mods);
		// (x,z) are strip-local (via the slot-59 transform, DXF-verified);
		// GetL/GetT are absolute (DGEO-verified) - same conversion DGEO logs.
		{
			cIGZWin* sw = reinterpret_cast<cIGZWin*>(self);
			if (InSubArrowAbs(sw->GetL() + x, sw->GetT() + z))
			{
				// Forward as a REAL click on the physical button. Cursor warp
				// first so poll-based reads agree with the message coords
				// (a proven pattern elsewhere in this file). Debounced: one forward
				// per press even if down+up both land here.
				static DWORD lastFwd = 0;
				const DWORD now = GetTickCount();
				if (now - lastFwd > 250 && gSubBtnCX >= 0)
				{
					lastFwd = now;
					HWND hwnd = GetActiveWindow();
					if (hwnd)
					{
						POINT pt = { gSubBtnCX, gSubBtnCY };
						ClientToScreen(hwnd, &pt);
						SetCursorPos(pt.x, pt.y);
						const LPARAM lp = MAKELPARAM(gSubBtnCX, gSubBtnCY);
						PostMessageW(hwnd, WM_LBUTTONDOWN, MK_LBUTTON, lp);
						PostMessageW(hwnd, WM_LBUTTONUP, 0, lp);
						Logger::Get().WriteLine(LogLevel::Debug,
							"UiSpike: ARROWCLICK fwd -> btn centre (%d,%d)",
							gSubBtnCX, gSubBtnCY);
					}
				}
				return true;   // handled; never run the strip's item-select
			}
		}
		return gOrigMouse136 ? gOrigMouse136(self, edx, x, z, mods) : false;
	}
	bool __fastcall Mouse138Thunk(void* self, void* edx, int32_t x, int32_t z,
		uint32_t mods)
	{
		// Arrow-zone points must not run the pick-item-from-Y logic - the
		// arrow's Y would light up an arbitrary item.
		{
			cIGZWin* sw = reinterpret_cast<cIGZWin*>(self);
			if (InSubArrowAbs(sw->GetL() + x, sw->GetT() + z)) { return false; }
		}
		if (gStripDump)
		{
			Logger::Get().WriteLine(LogLevel::Debug,
				"UiSpike: DHIT138 x=%d z=%d mods=%08X", x, z, mods);
			// A few times, correlate the window-local coords with the strip's
			// real rect + its parent (container) rect + siblings, to see where the
			// selectable region sits vs the drawn pictures and what covers the left.
			static int g = 0;
			if (g < 3)
			{
				g++;
				cIGZWin* sw = reinterpret_cast<cIGZWin*>(self);
				cIGZWin* par = sw->GetParentWin();
				Logger::Get().WriteLine(LogLevel::Debug,
					"UiSpike: DGEO strip abs(L=%d T=%d W=%d H=%d) -> mouseAbs(%d,%d)",
					sw->GetL(), sw->GetT(), sw->GetW(), sw->GetH(),
					sw->GetL() + x, sw->GetT() + z);
				if (par)
				{
					Logger::Get().WriteLine(LogLevel::Debug,
						"UiSpike: DGEO parent id=%08X abs(L=%d T=%d W=%d H=%d) kids=%d",
						par->GetID(), par->GetL(), par->GetT(), par->GetW(),
						par->GetH(), par->GetChildCount());
					// CONTAINER hit rects vs its size: [0x14] is what routing tests.
					int32_t* pm = reinterpret_cast<int32_t*>(par);
					Logger::Get().WriteLine(LogLevel::Debug,
						"UiSpike: DCONT [0x14]=(%d,%d,%d,%d) [0x2C]W=%d [0x30]H=%d "
						"[0xA8]=(%d,%d,%d,%d)",
						pm[5], pm[6], pm[7], pm[8], pm[11], pm[12],
						pm[0x2a], pm[0x2b], pm[0x2c], pm[0x2d]);
				}
			}
		}
		return gOrigMouse138 ? gOrigMouse138(self, edx, x, z, mods) : false;
	}
	// IsPointInWindowParentCoordinates on the strip: log the parent-coord point
	// the container tests and the answer. If left-half points return 0 (or are
	// never asked), we learn exactly where the left half is being dropped.
	bool __fastcall Pt121Thunk(void* self, void* edx, int32_t x, int32_t y)
	{
		const bool r = gOrigPt121 ? gOrigPt121(self, edx, x, y) : false;
		if (gStripDump)
		{
			static int n = 0;
			if (++n >= 3)
			{
				n = 0;
				Logger::Get().WriteLine(LogLevel::Debug,
					"UiSpike: DPT121 x=%d y=%d -> %d", x, y, r ? 1 : 0);
			}
		}
		return r;
	}
	// CONTAINER slot 121 (its claim function 0x0079AE30, identity known from
	// the offline disasm: claims the rightmost [this+0xe0] px). Extend the
	// claim to the drawn back-arrow's rect WITHOUT touching [0xe0] - that
	// field is DUAL-USE (claim width AND a Plot layout inset, draw-side
	// halved), so widening it would corrupt the bar layout. Coordinate
	// space: parent-of-container = the full-screen 3D view at (0,0) = abs.
	PtInFn  gOrigContPt121 = nullptr;
	bool __fastcall ContPt121Thunk(void* self, void* edx, int32_t x, int32_t y)
	{
		const bool r = gOrigContPt121 ? gOrigContPt121(self, edx, x, y) : false;
		if (!r && InSubArrowAbs(x, y)) { return true; }
		return r;
	}
	// Refined per-item hit-test (slot 149) - a MouseTrans TRANSPARENCY test:
	// return true = "pass the mouse through here" (the caller INVERTS it), so the
	// opaque icon returns false = clickable. The 1x mask makes the left half read
	// transparent. Force false = "opaque everywhere the 0x14 rect covers" so the
	// whole picture is clickable (item still picked by Y in 138). gSelForce (live).
	bool __fastcall Slot149Thunk(void* self, void* edx, int32_t x, int32_t y)
	{
		if (gSelForce)
		{
			if (gStripDump)
			{
				static int n = 0;
				if (n < 4) { n++; Logger::Get().WriteLine(LogLevel::Debug,
					"UiSpike: DS149 x=%d y=%d -> FORCED opaque(0)", x, y); }
			}
			return false;   // not transparent -> caller treats as inside/clickable
		}
		return gOrigSlot149 ? gOrigSlot149(self, edx, x, y) : false;
	}
	// WindowToScreenCoordinates (slot 59): measure the transform applied to the
	// cursor. a1=&x, a2=&y (pointers, modified in place). Log before/after.
	bool __fastcall Slot59Thunk(void* self, void* edx, int32_t* a1, int32_t* a2)
	{
		int inx = a1 ? *a1 : 0, iny = a2 ? *a2 : 0;
		const bool r = gOrigSlot59 ? gOrigSlot59(self, edx, a1, a2) : false;
		if (gStripDump)
		{
			static int n = 0;
			if (++n >= 3)
			{
				n = 0;
				Logger::Get().WriteLine(LogLevel::Debug,
					"UiSpike: DXF in(%d,%d) -> out(%d,%d)  dx=%d dy=%d",
					inx, iny, a1 ? *a1 : 0, a2 ? *a2 : 0,
					(a1 ? *a1 : 0) - inx, (a2 ? *a2 : 0) - iny);
			}
		}
		return r;
	}
	// IsPointInMe (slot 62): log the point the routing tests + the answer, so a
	// left vs right hover shows whether slot 62 itself rejects the left half.
	bool __fastcall Slot62Thunk(void* self, void* edx, int32_t x, int32_t y)
	{
		// Arrow zone: answer yes so the routed (container-claimed) click
		// continues into the strip handlers, where 136 forwards it. Verified
		// coordinate space: this slot receives ABSOLUTE coords (DS62 log).
		if (InSubArrowAbs(x, y)) { return true; }
		const bool r = gOrigSlot62 ? gOrigSlot62(self, edx, x, y) : false;
		if (gStripDump)
		{
			static int n = 0;
			if (++n >= 3)
			{
				n = 0;
				Logger::Get().WriteLine(LogLevel::Debug,
					"UiSpike: DS62 IsPointInMe x=%d y=%d -> %d", x, y, r ? 1 : 0);
			}
			// One-time dump of the strip's low fields (0x00..0x60): the routing's
			// un-doubled rect (~44px, right-aligned, e.g. 236,?,278,?) lives here,
			// separate from [0x14](190..278) and [0xA8]. Find the ~44 / 236 value.
			static bool dumped = false;
			if (!dumped)
			{
				dumped = true;
				int32_t* mm = reinterpret_cast<int32_t*>(self);
				for (int off = 0x00; off <= 0x60; off += 0x20)
				{
					int k = off / 4;
					Logger::Get().WriteLine(LogLevel::Debug,
						"UiSpike: DFLD @0x%02X: %d %d %d %d %d %d %d %d", off,
						mm[k], mm[k+1], mm[k+2], mm[k+3],
						mm[k+4], mm[k+5], mm[k+6], mm[k+7]);
				}
			}
		}
		return r;
	}
}

// ============ SUB-FLYOUT GEOMETRY (measured for v2.34.0, task #50) ==========
// Three facts about the nested plop sub-flyouts, measured across 6 opens /
// 3 menus, that the born-scale path below builds on:
//
//  1. The ITEMS ARE NOT WINDOWS. The whole assembly is container 0x8A6E61E0 ->
//     strip 0x8A2CAD8B -> a degenerate tip layer. Menu items are BLITS into
//     the container's paint buffer. No window sweep can ever reach them.
//  2. THE FLASH IS THE BUFFER. The window rect is corrected within ~1ms, but
//     the paint buffer was already allocated from the 1x rect, so Plot #1 fills
//     a 2x window from a 1x buffer (20-36ms at the measured 54.5fps).
//  3. THE GEOMETRY IS CODE-DERIVED (vf10 0x0079AC60 stores the fields):
//         W = [+0xf0] - [+0xf8] + [+0xe4]        = 80 - 4 + 53 = 129
//         H = max(stripH, [+0xf4]) + 2*[+0xe8]   = max(stripH,53) + 50
//         stripH = count*(cell 44 + gap 5) - 5   = 49n - 5, n clamped [1,8]
//     This reproduces 8/8 observed container heights and 4/4 strip heights.
//
// The v2.34.0 cure built them at round(stock*f) from the CONSTANTS (a vf10
// trampoline promoting the seven fields, plus three imm8 provider sites in
// sub_7EAEB0). It broke the UI twice, stayed behind [UiSpike] SubFlyoutBorn2x
// (default 0) after the born-scale path replaced it, and was removed in the
// 2026-09-25 audit (B1). History: REGRESSION.md, VERSION-HISTORY.txt v2.34.0.

// ============ SUB-FLYOUT BORN-SCALED (v2.36.0, task #50) ================
// THE USER'S REPORT: "It's not a flash it shows the prescaled version for a
// split second", in "SUB PANELS AND THEIR SUB PANELS AND THEIR SUB PANELS
// NEVER THE MAIN 3 OF GOD / MAYOR / MY SIM".
//
// WHY IT HAPPENS. The container is built FRESH on every open (sub_7EAEB0,
// new(0x150)) and is BORN VISIBLE at 1x - both cGZWin ctors set
// [this+0xC8]=0x8903. Nothing scales it until the next sweep tick, so the game
// paints 1-2 genuine stock-size frames first (20-36ms at the measured 54.5fps;
// 6 of 6 opens in the corpus were first seen at 1x with vis=1). The 1x paint
// BUFFER that DOBS reports on Plot #1 is the fossil of those frames.
//
// THE CURE IS THE AVATAR-FACES CURE. Advisor faces, the news reader, the
// budget popups and the region flyouts were all fixed by making the window
// BORN CORRECT (pre-scale while HIDDEN, kAlwaysScaleCityIds). That could never
// be applied here because there is nothing to pre-scale before the click. For
// a runtime-built window the equivalent instant is its CONSTRUCTION - so we
// scale it there, in the two ticks between "the game finished the layout" and
// "the first pixel".
//
// WHAT THIS IS NOT (all measured, all reverted - "THE FLASH:
// DECODED, NOT FIXED"): not the SetFlag show hook (on-demand windows are born
// visible, so no transition ever fires); not DATA pre-scale (broke mayor
// mode); not paint suppression (permanently banned); not a sweep cadence
// change (the sweep already runs every ~16ms). And - the important one - NOT
// the v2.34/v2.35 born-2x, which promoted the BUILDER'S CONSTANTS in vf10
// (0x0079AC60 SetLayout) and drove the coupled [+0xEC] = artH - 2*[+0xE8] to
// -47. This hooks vf14 (0x0079AD00 Place), a DIFFERENT function that only sets
// an area, and scales the FINISHED rect. No constant, no field, no exe byte.
//
// WHY IT IS SAFE, in one line: the arithmetic is IDENTICAL to the sweep's.
// tools\uimap\emu\emu_subflyout.py runs the game's own sub_79AD00 offline for
// n=1..8 at f=1/1.5/2/3 and asserts born == sweep == the six measured live
// rects (71 checks, PASS). Only the TIMING changes, and the sweep stays behind
// us as the idempotent safety net.
//
//   builder order (SUBFLYOUT-BUILDER.md 3.1), and where we sit in it:
//     0x7EAEEF  strip->SetItemMetrics(44,44,5)     <- we RECORD the strip here
//     0x7EAF4E  strip->GetDesiredSize(&sz,n)          (1x - must stay 1x, see
//     0x7EB16E  container->SetLayout(img,53,25,...)    the 432-vs-482 note)
//     0x7EB193  container->Place(sz.w,sz.h,cx,cy,..) <- WE SCALE ON ITS RETURN
//     0x7EB1D2  container->GetStripRect(&r)            (reads what we wrote)
//     0x7EB1D9  stripWin->SetArea(&r)                  -> strip born scaled
//     0x7EB20D  containerWin->AddChild(stripWin)
namespace
{
	typedef void(__fastcall* SubPlaceFn)(void*, void*, int, int, int, int, int, int);
	typedef void(__fastcall* SubMetricsFn)(void*, void*, int, int, int);
	SubPlaceFn   gOrigSubPlace = nullptr;
	SubMetricsFn gOrigSubMetrics = nullptr;
}

namespace UiSpikeInternal
{
	// The one UiSpike, for the free-function detours whose treatments are
	// members. Set by InstallShowHook and InstallFlyoutOpenHook, which
	// ArmDeferred calls back to back (audit B9: the show hook kept its own
	// copy, gSpikeForHook, holding the same pointer).
	UiSpike* gSpikeSelf = nullptr;
}

namespace
{
	bool gSubBornScaleInstalled = false;
	int  gSubBornScaleOn = 1;      // [Flyout] SubBornScale - live-tunable
	// v2.39.0 task #5: the SAME Place detour, second builder. Its own lever so
	// a mis-size can be switched off live without touching the confirmed on screen
	// sub-flyout path (size and placement must be separately
	// switchable, or a bad call forces a rebuild).
	int  gDisBornScaleOn = 1;      // [Flyout] DisBornScale - live-tunable
	int  gDisBornDockOn  = 1;      // [Disaster] BornDock - live-tunable
	int  gDisBornMetricsOn = 1;    // [Disaster] BornMetrics - live-tunable (v2.39.5)
	int  gDisBornLog = 0;          // DISBORN lines emitted (cap 10)
	int  gSubBornDockOn = 1;       // [Flyout] SubBornDock  - live-tunable
	int  gSubBornLog2 = 0;
}

namespace UiSpikeInternal
{
	// The strip CONTROL object (obj+0) the builder just gave item metrics to.
	// SetItemMetrics runs ~250 instructions before Place in the SAME builder
	// call on the single UI thread, so "the last one" is unambiguous.
	void* gSubLastStrip = nullptr;
	// v2.39.1: the disaster twin gets its OWN strip pointer and base metrics.
	// gSubLastStrip / gStripBase* are single globals written by whichever
	// builder ran last; sharing them across two builders is "two writers, one
	// pointer, no ownership marker" and the fields we write are per-instance.
	void* gDisLastStrip = nullptr;
}

namespace
{
	int   gDisStripBase4 = 0, gDisStripBase8 = 0, gDisStripBaseC = 0;
	bool  gDisStripBaseCap = false;
	// v2.39.3: the dock target the sweep computes, cached so birth can apply it.
	// Pure function of the already-scaled toolbar + two ini offsets, so it is
	// identical on every tick and safe to reuse. Cleared in Disarm (a new city
	// has a new toolbar).
	int32_t gDisDockL = 0, gDisDockT = 0;
}

namespace UiSpikeInternal
{
	bool    gDisDockValid = false;
}

namespace
{
	// GODDOCK born-dock log budget. (The v4.0.10-12 "derived" disaster dock
	// - container target = disaster button + measured stock glue * f - was
	// retired in v4.0.13 because it moved the RING off its button, and its
	// capture/target code was removed in the 2026-09-25 audit, B1.)
	int     gDisDerivedLogs = 0;
}

namespace UiSpikeInternal
{
	// v2.39.4: container whose chrome-live repaint has already been
	// forced. Pointer-keyed and one-shot: the block that sets it runs on
	// every sweep tick while the flyout is open. Cleared in Disarm, and
	// a per-open container is a NEW pointer so each open heals once.
	cIGZWin* gDisChromeHealed = nullptr;
	// v2.39.5: container whose settled dock line has been logged (the line
	// printed 867x in one 23s open before this). Reset when the flyout
	// closes (contFound false) - pointer identity alone is unsafe, the heap
	// recycles container addresses within seconds (measured, DPROBE).
	cIGZWin* gDisDockLogged = nullptr;
}

namespace
{
	// The born records the sweep has not adopted yet. ScaleSubtree is made
	// idempotent by scaleMap (keyed on window pointer): a window WE scaled at
	// birth is a pointer the sweep has never seen, so without this it would be
	// classified Fresh and scaled A SECOND time (129 -> 258 -> 516). The
	// sweep drains this queue into scaleMap before it walks, which makes the
	// very next Classify() return AlreadyScaled.
	struct BornRec { void* win; uint32_t id; int32_t ow, oh, sw, sh; };
	BornRec gBornQ[8];
}

namespace UiSpikeInternal
{
	int gBornQN = 0;
}

namespace
{
	void NoteBorn(void* win, uint32_t id, int32_t ow, int32_t oh,
		int32_t sw, int32_t sh)
	{
		if (!win) { return; }
		for (int i = 0; i < gBornQN; i++)
		{
			if (gBornQ[i].win == win)   // same open, re-entered: overwrite
			{
				gBornQ[i] = { win, id, ow, oh, sw, sh };
				return;
			}
		}
		if (gBornQN >= 8) { gBornQN = 7; }   // drop the oldest; never overrun
		gBornQ[gBornQN++] = { win, id, ow, oh, sw, sh };
	}
}

namespace UiSpikeInternal
{
	// The buffer class's Blt is what draws the 2x ring and widens the 1x bar
	// art (BltClassThunk, gated internally by the destIsSubContainer size
	// heuristic). It is installed inside the container's Plot detour and left
	// PERMANENTLY hooked - but that detour is installed by the sweep, i.e. one
	// tick too late for a born-scaled container's FIRST paint. Installing it
	// here changes only WHEN, never what it does.
	void EnsureBufferClassBltHook()
	{
		if (!gBufVtWritable)
		{
			DWORD oldProt;
			if (!VirtualProtect(&kBufClassVt[0], 64 * sizeof(void*),
				PAGE_EXECUTE_READWRITE, &oldProt))
			{
				return;
			}
			gBufVtWritable = true;
			// v4.10.0 (S6): the page stays RWX for the session - every
			// later slot write relies on gBufVtWritable. Recorded so a stray
			// write into that page by anything in this 50-plugin process is
			// attributable to a page WE opened.
			Logger::Get().WriteLine(LogLevel::Info,
				"UiSpike: buffer class vtable page at %p made PAGE_EXECUTE_READWRITE "
				"for the session (was 0x%08lX; not restored - later slot writes rely "
				"on it).", static_cast<void*>(&kBufClassVt[0]),
				static_cast<unsigned long>(oldProt));
		}
		if (!gClassBltOrig)
		{
			gClassBltOrig = reinterpret_cast<CBltFn>(kBufClassVt[29]);
		}
		if (kBufClassVt[29] != reinterpret_cast<void*>(&BltClassThunk))
		{
			kBufClassVt[29] = reinterpret_cast<void*>(&BltClassThunk);
		}
	}
}

namespace
{
	// sub_79A0E0  strip->SetItemMetrics(itemW, itemH, spacing), ret 0xC.
	// PASS-THROUGH ONLY. Scaling the arguments here is the v2.35 trap: the
	// builder feeds the result to GetDesiredSize -> Place, which computes
	// contentH = max(stripH,[0xF4]) + 2*[0xE8] from the STILL-1x container
	// fields. At f=2, n=4 that yields 432 where the live value is 482. The
	// item metrics must be promoted AFTER Place has done its 1x arithmetic.
	void __fastcall SubMetricsDetour(void* self, void* edx, int w, int h, int sp)
	{
		const uintptr_t ret = reinterpret_cast<uintptr_t>(_ReturnAddress());
		gOrigSubMetrics(self, edx, w, h, sp);
		// SAME-CALL-SITE GUARD, and it is not optional. This method is called
		// by every strip in the game - the first-level twin (0x007E72AF), the
		// U-Drive-It / Earned Cars strip that once crashed us, others we have
		// never enumerated. Accepting any of them would (a) leave
		// gSubLastStrip pointing at a foreign object we then write fields
		// into, and (b) let a foreign itemW become the latched 1x base for
		// EVERY sub-flyout. 0x007EAEFA is the instruction after the
		// sub-flyout builder's own `call [eax+0x30]`.
		const uintptr_t modBase = ExeBase();
		// v2.39.1: the DISASTER twin's own call site (0x007E72AF = after
		// sub_7E7270's `call [edx+0x30]`) is now accepted, into SEPARATE state.
		// It was previously rejected, which was correct while nothing scaled
		// that flyout at birth - but v2.39.0 made the container born-2x, and a
		// born container whose items are still 1x is the "geometry born, state
		// not" half-fix the v2.36.2 law warns about (measured: 88x578 strip
		// window full of 44px cells - the tiny thumbnail column).
		if (ret == modBase - 0x400000 + 0x007E72AF)
		{
			gDisLastStrip = self;
			if (!gDisStripBaseCap && w > 0 && w < 200)
			{
				gDisStripBase4 = w;
				gDisStripBase8 = h;
				gDisStripBaseC = sp;
				gDisStripBaseCap = true;
			}
			// PRIME THE SHARED LATCH FROM A STOCK ARGUMENT (law 30, v2.39.2).
			// SlotThunk2<88> latches gStripBase* from whatever it first sees in
			// the strip's fields; if it ever sees an already-scaled value it
			// writes base*f on top of that forever, for EVERY strip in the game
			// (the v2.39.1 duplicated-icons-everywhere regression). Priming it
			// here from the builder's own STOCK argument closes that door before
			// any strip is painted - the same reason the sub-flyout twin primes
			// it at :3320. Both builders pass 44/44/5, so whichever arrives
			// first sets the identical base and the other is a no-op.
			if (!gStripBaseCap && w > 0 && w < 200)
			{
				gStripBase4 = w;
				gStripBase8 = h;
				gStripBaseC = sp;
				gStripBaseCap = true;
			}
			return;
		}
		if (ret != modBase - 0x400000 + 0x007EAEFA) { return; }
		gSubLastStrip = self;
		// Prime the base SlotThunk2<88> re-applies every Plot. It latches the
		// FIRST value it sees, so if it ever latched our born-scaled 88 it
		// would then write RoundHalfUp(88*f) = 176 (law 30: a constant is
		// never alone). Priming it from the builder's own stock argument
		// closes that door before the strip is ever painted.
		if (!gStripBaseCap && w > 0 && w < 200)
		{
			gStripBase4 = w;
			gStripBase8 = h;
			gStripBaseC = sp;
			gStripBaseCap = true;
		}
	}

	// sub_79AD00  container->Place(w, h, cx, cy, margT, margB), ret 0x18.
	void __fastcall SubPlaceDetour(void* self, void* edx, int w, int h,
		int cx, int cy, int mT, int mB)
	{
		const uintptr_t ret = reinterpret_cast<uintptr_t>(_ReturnAddress());
		// Let the game lay the whole assembly out at stock size first - its
		// arithmetic is the source of truth and we never disturb it.
		gOrigSubPlace(self, edx, w, h, cx, cy, mT, mB);
		// BIRTH OWNS THE DOCK: every Place() from the sub-flyout builder
		// (return address 0x7EB196, the twin guard below) starts a new open, so
		// forget the previous open's record HERE - before the early return that
		// follows. Cleared any later, a live SubBornScale=0 or a stock tier would
		// skip the clear, and a recycled container address of the same height
		// would inherit the last open's anchor and never dock (review 2026-09-25).
		// It is set again only if this open's birth dock runs.
		if (ret == ExeBase() - 0x400000 + 0x007EB196)
		{
			gSubBornWin = nullptr;
		}
		if (!self || !gSubBornScaleOn || gTierF <= 1.01f) { return; }

		// TWIN GUARD (law 32). Place is a SHARED class method: sub_7EAEB0
		// builds the nested sub-flyout and sub_7E7270 builds the FIRST-LEVEL
		// Create Disaster flyout from the same class - SAME TWO VTABLES, so the
		// return address is the only discriminator.
		//
		// v2.39.0 (task #5): the disaster twin is now handled HERE too. The
		// v2.36.0 comment said it was "already scaled by other proven paths" -
		// true of its clicks, dock, layering and art (v2.11.30, confirmed on screen)
		// but NOT of its SIZE AT BIRTH, which is the jump the player still sees.
		//
		// Byte-verified 2026-07-31 (both twins, at the same 0x25 delta):
		//   SetLayout 0x7EB16E / 0x7E74AE   both `ff 50 10`
		//   Place     0x7EB193 / 0x7E74D3   both `ff 52 14`
		//   accept    0x7EB196 / 0x7E74D6
		// sub_7E7270 has exactly ONE caller (0x7F4D2C, gated on
		// `cmp esi,0x69B9324A`) and ZERO raw-address occurrences image-wide, so
		// the return address is a sound discriminator on its own.
		const uintptr_t modBase = ExeBase();
		const uintptr_t retSub = modBase - 0x400000 + 0x007EB196;
		const uintptr_t retDis = modBase - 0x400000 + 0x007E74D6;
		const bool isDisaster = (ret == retDis);
		if (ret != retSub && !isDisaster) { return; }
		if (isDisaster && !gDisBornScaleOn) { return; }

		// POSITIVE IDENTIFICATION (law 3). The cIGZWin base sits at obj+4 -
		// proven by Place itself (`lea ecx,[esi+4]` before `call [edx+0xdc]`
		// SetArea), not assumed. SetID(0x8A6E61E0) ran at 0x7EB11A, i.e.
		// BEFORE this call, so the id is already readable.
		//
		// THE DISASTER CONTAINER HAS NO ID AT ALL - sub_7E7270 contains no
		// SetID call (scanned 0x7E7270..0x7E75B0). "same
		// class, DIFFERENT id" is wrong and would send you to build the wrong
		// guard. For that twin the return address IS the identification.
		cIGZWin* win = reinterpret_cast<cIGZWin*>(
			reinterpret_cast<char*>(self) + 4);
		if (!isDisaster && win->GetID() != 0x8A6E61E0) { return; }

		// SUBPLACE (2026-08-23 diagnostic, no behavior change): the RAW
		// Place() parameters, never logged before. mT/mB are the game's
		// OWN bottom-margin clamp inputs - candidate source for the
		// shared sub-flyout bottom line the user's bottom-anchor law
		// requires (see research/laws/project-sc4-flyout-bottom-anchor.md,
		// which is law L1 promoted). Logged before any
		// of our own math touches cy, so this is the pristine value.
		{
			// 2026-08-23: raised 40 -> 2000 mid-verification. A
			// comprehensive click-through (every flyout, every
			// sub-category, God Mode + Mayor Mode + My Sims) hit the old
			// cap with roughly a minute of clicking still left, leaving
			// everything after it unverifiable from the log even though
			// the underlying math still ran. Still a bounded cap, just
			// one sized for actually finishing a full sweep in one boot.
			static int spLog = 2000;
			if (spLog > 0)
			{
				spLog--;
				Logger::Get().WriteLine(LogLevel::Info,
					"UiSpike: SUBPLACE self=%p kind=%s f=%.2f w=%d h=%d "
					"cx=%d cy=%d mT=%d mB=%d viewH=%d",
					self, isDisaster ? "DIS" : "SUB", gTierF, w, h, cx,
					cy, mT, mB, gLastViewH);
			}
		}

		char* obj = reinterpret_cast<char*>(self);
		int32_t* sr = reinterpret_cast<int32_t*>(obj + 0x108);  // strip L,T,R,B
		const int32_t l = win->GetL(), t = win->GetT();
		const int32_t cw = win->GetW(), ch = win->GetH();
		const int32_t osl = sr[0], ost = sr[1];
		const int32_t osw = sr[2] - sr[0], osh = sr[3] - sr[1];
		if (cw <= 0 || ch <= 0) { return; }

		// --- 1. the container: edge-derived rounding, exactly ScaleSubtree's
		// (UiSpike.cpp:8197). A root keeps its anchor - size only.
		const int32_t newW = ScaleRound(l + cw, gTierF) - ScaleRound(l, gTierF);
		const int32_t newH = ScaleRound(t + ch, gTierF) - ScaleRound(t, gTierF);
		win->SetW(newW);
		win->SetH(newH);

		// --- 2. the strip rect, still sitting in [0x108..0x114] where
		// GetStripRect will read it four instructions from now. Scaling all
		// four parent-relative edges is identical to what ScaleSubtree does to
		// a child (SetW/SetH + a relative GZWinMoveTo).
		for (int i = 0; i < 4; i++) { sr[i] = ScaleRound(sr[i], gTierF); }

		// --- 3. the strip's item metrics. AFTER Place, never before.
		// --- THE DISASTER TWIN STOPS HERE (v2.39.0, task #5) ---------------
		// The first-level flyout was the FIRST one we ever scaled (v2.11.x) and
		// it is still on that era's mechanism: ScaleGodFlyouts sizes it only
		// once IsVisible() is true (UiSpike.cpp ~:7671), so the game paints it
		// at 141x339 first. Every other flyout has since been upgraded - the
		// id-bearing ones to pre-scale-while-hidden (IsGodPanelId, v2.11.28/29)
		// and the nested sub-flyout to born-at-Place (v2.36.0). This brings the
		// first one up to the same standard.
		//
		// ROW 1 IS NOT AVAILABLE HERE, and that was measured rather than
		// assumed: the container is CREATED FRESH per open, not persisted
		// hidden. Archived DPROBE shows four distinct pointers in ~60s of one
		// session (29B6C618, 29B6C418, 29B6B818, then 29B6C618 AGAIN - the heap
		// address recycled within 11s). You cannot pre-scale a window that does
		// not exist yet, so row 4 is the only lever. That recycling also makes
		// Classify's id==0 address-reuse hazard real and OBSERVED, which is why
		// NoteBorn's record for this window carries id 0 deliberately.
		//
		// DELIBERATELY NOT DONE for this twin (each would be a second lever in
		// one change, and this one is measured first):
		//   * item metrics - gStripBase* is primed by SubMetricsDetour, whose
		//     call-site guard rejects the disaster strip's 0x7E72AC. Its args
		//     are the same 44/44/5, so the sweep's existing pass still handles
		//     them exactly as it does today.
		//   * the dock - ScaleGodFlyouts docks ABSOLUTELY off the live toolbar;
		//     the sub-flyout's RELATIVE delta form would displace it.
		//   * InstallSubFlyoutHooksNow - it sets gDisasterDrawTuning = 0
		//     (:3593), which would kill this flyout's measured ring/bar offsets.
		if (isDisaster)
		{
			// v2.39.1 - THE HALF-FIX THAT SHIPPED IN v2.39.0, AND WHY.
			// v2.39.0 scaled the container and the strip RECT and marked the
			// container born. That made Classify return AlreadyScaled, so the
			// sweep SKIPPED THE WHOLE SUBTREE - including the strip item
			// metrics it had been scaling all along. Result: an 88x578 strip
			// window full of 44px cells (the tiny thumbnail column, user
			// screenshots). Geometry born correct, STATE not born: exactly the
			// v2.36.2 law, which the v2.39.0 comment quoted and then did not
			// apply. When born-scaling takes a window off the sweep, it
			// inherits EVERYTHING the sweep was doing for it.
			// DO NOT WRITE THE ITEM METRICS HERE. v2.39.1 did, and it broke
			// ICONS GAME-WIDE (regression of the task #55/#56 fix).
			//
			// SlotThunk2<88> (:1924) latches its 1x base from the strip's OWN
			// fields on the FIRST Plot and thereafter writes base*f absolutely:
			//     if (!gStripBaseCap && mm[0x3d] > 0 && mm[0x3d] < 200) { latch }
			//     if (gStripBaseCap) { mm[0x3d] = RoundHalfUp(gStripBase4*f); }
			// mm is int32_t*, so mm[0x3d]/[0x3e]/[0x3f] are BYTE offsets
			// 0xF4/0xF8/0xFC. Writing 0xF8 = 88 here, before that latch had
			// run, made it latch 88 as the BASE and start writing 176 - and
			// gStripBase* is SHARED BY EVERY STRIP IN THE GAME, so every picker
			// cell went double-width and showed both art states side by side.
			// Exactly law 30, warned about verbatim in the comment above that
			// block. The metrics belong to the Plot-time thunk; birth's job is
			// only to make sure it latches a CLEAN 1x base (done below).
			void* dstrip = gDisLastStrip;
			// DOCK AT BIRTH (v2.39.3). Target = the accepted scheme:
			// toolbar-live + DockX/DockY (gDisDock cache, tick-computed).
			// (The v4.0.10-12 "derived" container targets moved the RING off
			// its button - retired v4.0.13, removed 2026-09-25.)
			// Absolute move - GZWinMoveTo takes a DELTA, hence target -
			// current.
			{
				int32_t tgtL = 0, tgtT = 0;
				if (gDisDockValid)
				{
					tgtL = gDisDockL; tgtT = gDisDockT;
					if (gDisBornDockOn)
					{
						const int32_t dl = tgtL - l;
						const int32_t dt = tgtT - t;
						if (dl != 0 || dt != 0)
						{
							win->GZWinMoveTo(dl, dt);
						}
						if (gDisDerivedLogs < 6)
						{
							gDisDerivedLogs++;
							Logger::Get().WriteLine(LogLevel::Info,
								"UiSpike: GODDOCK #%d born (%d,%d) -> "
								"(%d,%d) [accepted tbLive+ini] before "
								"first paint.",
								gDisDerivedLogs, l, t, tgtL, tgtT);
						}
					}
				}
			}
			NoteBorn(win, 0, cw, ch, newW, newH);
			// The strip WINDOW must be registered too, or the sweep finds it
			// Fresh at its already-2x rect and doubles it again.
			void* dstripWin = nullptr;
			if (dstrip)
			{
				typedef void*(__fastcall* GetWinFn)(void*, void*);
				// deref-ok: dstrip is the strip control the hook received; dsvt && dsvt[3] checked
				void** dsvt = *reinterpret_cast<void***>(dstrip);
				if (dsvt && dsvt[3])
				{
					// deref-ok: the strip control's own GetWindow slot - exactly the call the builder makes at 0x7EB1D9
					dstripWin = reinterpret_cast<GetWinFn>(dsvt[3])(dstrip, nullptr);
				}
				if (dstripWin)
				{
					NoteBorn(dstripWin, 0, osw, osh,
						sr[2] - sr[0], sr[3] - sr[1]);
				}
				// INITIAL SCROLL (v4.0.14 - the actual fire-beside-the-ring
				// fix). The thumbnails are drawn by the strip's own Plot
				// from member fields, NOT from the window rect - a window
				// move cannot move them (v4.0.13's rigid-follow wrote into
				// rect fields that read (0,0) pre-layout and changed nothing
				// on screen; removed). Measured with StripDump=1: six rows of
				// pitch 98 at dst-Y 0..490, ring centre at strip-local ~303 =
				// the gap between visible rows 3 and 4, which at scroll 0 is
				// exactly volcano|fire. The first-visible field was observed
				// at 3 = scrolled to the BOTTOM of the 9-item list, so the
				// wrong disasters flanked the ring. Write it once per open,
				// after Place, guarded so a recycled/garbage object is never
				// touched. User scrolling afterwards remains free.
				//
				// OFFSET FRAME (v2.39.8 law, see below): dstrip is the OUTER
				// object - every WINDOW-relative offset from the DSCROLL
				// dump shifts +1 int here (win[0xE4]->sm[0x3A],
				// win[0xE8]->sm[0x3B], win[0xFC]->sm[0x40]).
				if (dstrip && gDisBornDockOn)
				{
					int32_t* sm = reinterpret_cast<int32_t*>(dstrip);
					const int32_t count = sm[0x3A];    // win [0xE4]
					const int32_t sp = sm[0x40];       // win [0xFC] spacing
					// Sanity: only write when the fields match the shape we
					// measured (9 disasters). ROOT CAUSE (2026-08-23,
					// user-reported "tail connects to the stripe
					// incorrectly", confirmed via SCROLLINIT-MISS logging
					// every single open): this block runs BEFORE "BORN ITEM
					// METRICS" below, which is what actually scales the
					// spacing field - so `sp` here is STILL the raw 1x
					// value (5) captured by SubMetricsDetour, never the
					// scaled one. Comparing against ScaleRound(5, gTierF)
					// compared against a state that had not happened yet,
					// so this guard failed on every open, the scroll was
					// never reset, and whatever the game's own default
					// scroll position is (measured 2026-08-22 as 3 - the
					// bottom of the 9-item list) stayed live, putting the
					// wrong pair of disasters beside the ring. Compare
					// against the CAPTURED stock base instead of a value
					// that only exists after this point in the function.
					if (count == 9 && sp == gDisStripBaseC)
					{
						const int32_t oldScroll = sm[0x3B];  // win [0xE8]
						sm[0x3B] = gDisInitScroll;
						Logger::Get().WriteLine(LogLevel::Info,
							"UiSpike: SCROLLINIT strip scroll %d -> %d "
							"(first-visible item; 0 = volcano|fire beside "
							"the ring).",
							oldScroll, gDisInitScroll);
					}
					else
					{
						// 2026-08-23: this guard was measured firing zero
						// times in a live session (user report: "the tail
						// connects to the stripe incorrectly", every open) -
						// meaning the scroll never gets reset and whatever
						// the game's own default is (measured once,
						// 2026-08-22, as 3 - the bottom of the list) stays
						// live, putting the wrong pair of disasters beside
						// the ring. Log exactly which half of the guard
						// failed and what the fields actually held, instead
						// of guessing again.
						static int sScrollMissLog = 40;
						if (sScrollMissLog > 0)
						{
							sScrollMissLog--;
							Logger::Get().WriteLine(LogLevel::Info,
								"UiSpike: SCROLLINIT-MISS count=%d "
								"(want 9) sp=%d (want stock base %d) "
								"scroll=%d f=%.2f - guard did not fire, ring "
								"may sit beside the wrong pair.",
								count, sp, gDisStripBaseC, sm[0x3B],
								gTierF);
						}
					}
				}
			}
			// BORN ITEM METRICS (v2.39.5, task #80 - THE MISSING ARROW).
			// The scroll arrows are not painted on demand: the container's
			// Plot (0x79B0E0 +0x10D/+0x143) only READS byte flags
			// [0x118]/[0x119] to pick the end-cap atlas cell (plain pill vs
			// arrow, cells step [0xE0] from x94), and the constructor
			// (0x7F0AF4) births both flags 0. The open flow SETS them from a
			// scroll-needed decision whose arithmetic is the strip Plot's
			// own opening lines (0x79AA70):
			//     visibleRows = (stripWinH + [0xFC]) / ([0xF8] + [0xFC])
			// At our birth state that is (578+5)/(44+5) = 11 >= 9 items ->
			// "everything fits" -> flags stay 0 -> NO ARROW, and no repaint
			// can ever bring it back (DISHEAL fired and changed nothing -
			// measured, session 17:21 2026-07-31). A user scroll re-runs the
			// decision with the by-then-hooked 2x metrics ((578+10)/98 = 6
			// < 9) and the arrow "appears". Stock 1x: (289+5)/49 = 6 < 9 ->
			// arrow, which is why this never happened before v2.39.0 scaled
			// the strip rect at birth: the units were never mixed.
			//
			// So: make the units consistent AT BIRTH - scaled rect AND
			// scaled metrics. This is NOT the v2.39.1 regression returning:
			//  * both latches (gDisStripBase*, shared gStripBase*) were
			//    primed from the builder's STOCK 44/44/5 at the metrics call
			//    BEFORE Place ran (:3308-3333; the DISBORN line prints the
			//    primed base as proof) - SlotThunk2 can no longer latch a
			//    scaled value, which was the entire v2.39.1 failure mode;
			//  * the write goes to the DISASTER strip's own fields only
			//    (offsets 0xF4/0xF8/0xFC - the ones the strip Plot provably
			//    reads and SlotThunk2 provably re-writes each hooked Plot,
			//    so this is idempotent with the Plot-time path);
			//  * the READ-GUARD below refuses unless the fields still hold
			//    the exact stock bases - if anything already scaled them (or
			//    the layout ever changes) it becomes a logged no-op, never a
			//    second scaling.
			// Kill switch: [Disaster] BornMetrics=0 (EXACT key match, law 19).
			// OFFSET FRAME (v2.39.8 - the read-guard caught v2.39.7's error
			// and printed "metrics left to Plot" instead of corrupting a
			// field). dstrip is the OUTER strip object from SetItemMetrics
			// (vptr at +0, cIGZWin base at +4), so its metrics are
			// OBJECT-relative 0xF8/0xFC/0x100 - exactly what the proven
			// sub-flyout branch below writes on gSubLastStrip. The
			// 0xF4/F8/FC trio v2.39.7 used is the WINDOW-relative frame (the
			// strip Plot's `this` is the embedded window, 4 bytes in); both
			// name the same three fields, off by the +4 embed.
			bool metricsBorn = false;
			if (dstrip && gDisBornMetricsOn && gDisStripBaseCap
				&& gDisStripBase4 >= 30 && gDisStripBase4 <= 60
				&& gDisStripBase8 >= 30 && gDisStripBase8 <= 60
				&& gDisStripBaseC >= 1 && gDisStripBaseC <= 20)
			{
				int32_t* mw = reinterpret_cast<int32_t*>(
					reinterpret_cast<char*>(dstrip) + 0xF8);
				int32_t* mh = reinterpret_cast<int32_t*>(
					reinterpret_cast<char*>(dstrip) + 0xFC);
				int32_t* ms = reinterpret_cast<int32_t*>(
					reinterpret_cast<char*>(dstrip) + 0x100);
				if (*mw == gDisStripBase4 && *mh == gDisStripBase8
					&& *ms == gDisStripBaseC)
				{
					*mw = RoundHalfUp(gDisStripBase4 * gTierF);
					*mh = RoundHalfUp(gDisStripBase8 * gTierF);
					*ms = ScaleStepExtra(gDisStripBaseC, gTierF);  // FLOOR, see decl
					metricsBorn = true;
				}
			}
			// The ring/bar/arrow drawing corrector (BltClassThunk on the
			// buffer class vtable) is permanent once installed but used to
			// be installed only from inside SlotThunk<88> - which needs the
			// sweep's vtable swap first, so the FIRST frames of a session's
			// first open painted uncorrected chrome. Install it at birth
			// too: idempotent, and the disaster branch returning before the
			// sub-twin's call at step 6 was exactly the law-16 gap the
			// mechanism audit flagged.
			EnsureBufferClassBltHook();
			if (gDisBornLog < 10)
			{
				gDisBornLog++;
				// v2.39.8: (l,t) is the PRE-dock birth position and printing
				// only it made a WORKING born-dock read like a failure
				// (born (63,688), already docked by the time the sweep saw
				// it). Print the live post-dock position too.
				Logger::Get().WriteLine(
					LogLevel::Debug,
					"UiSpike: DISBORN container %dx%d -> %dx%d born (%d,%d) "
					"docked (%d,%d), strip (%d,%d %dx%d) -> (%d,%d %dx%d), "
					"latch base %d/%d/%d (Plot writes %d/%d/%d), "
					"metrics %s%s.",
					cw, ch, newW, newH, l, t,
					win->GetL(), win->GetT(),
					osl, ost, osw, osh,
					sr[0], sr[1], sr[2] - sr[0], sr[3] - sr[1],
					gDisStripBase4, gDisStripBase8, gDisStripBaseC,
					RoundHalfUp(gDisStripBase4 * gTierF),
					RoundHalfUp(gDisStripBase8 * gTierF),
					// THIS LINE USED TO REPORT RoundHalfUp AND IT WAS A LIE.
					// The step-extra is the ONE half-pixel in the system
					// (5*1.5 = 7.5) and the WRITE at :6432 deliberately FLOORS
					// it to 7 - rounding to 8 makes the denominator 74 where
					// the geometry supports 73, drops a row, and hides the last
					// item (USER-REPORTED 2026-08-06, cured by ScaleStepExtra).
					// The log recomputed it with the OLD rule, so it printed
					// "Plot writes 66/66/8" while the field correctly held 7.
					// 2026-08-16: that single wrong digit sent a whole
					// investigation at the step-extra while chasing a broken
					// end-cap arrow. Law 80 - fix the number that is WRONG, not
					// the one reporting it; here the REPORTER was the wrong one.
					// Report through the same function the write uses, always.
					ScaleStepExtra(gDisStripBaseC, gTierF),
					metricsBorn ? "BORN" : "left to Plot",
					dstripWin ? "" : " (STRIP WINDOW UNRESOLVED)");
			}
			return;
		}

		void* strip = gSubLastStrip;
		if (strip && gStripBaseCap)
		{
			char* so = reinterpret_cast<char*>(strip);
			*reinterpret_cast<int32_t*>(so + 0xF8) =
				RoundHalfUp(gStripBase4 * gTierF);
			*reinterpret_cast<int32_t*>(so + 0xFC) =
				RoundHalfUp(gStripBase8 * gTierF);
			*reinterpret_cast<int32_t*>(so + 0x100) =
				ScaleStepExtra(gStripBaseC, gTierF);   // FLOOR, see decl
			// SUBSCROLL (v4.0.22): measure the strip's scroll/count fields at
			// birth - same object frame as the metrics above (+4 from the
			// embedded window). The Build Park report ("arm meets row 7 -
			// Tourist Trap - in stock, row 5 - Marina - at 2x") is the same
			// disease the disaster flyout had (v4.0.14): ringY sits mid-pill
			// by law, so WHICH LOT lands there is decided by first-visible.
			// Log-only until the stock value is known; then a guarded write
			// mirrors InitScroll. Budget-capped, one line per open.
			{
				static int scLog = 20;
				const int32_t cnt =
					*reinterpret_cast<int32_t*>(so + 0xE8);
				if (scLog > 0)
				{
					scLog--;
					Logger::Get().WriteLine(LogLevel::Info,
						"UiSpike: SUBSCROLL strip=%p count=%d firstVisible=%d "
						"itemW=%d spacing=%d",
						strip, cnt,
						*reinterpret_cast<int32_t*>(so + 0xEC),
						*reinterpret_cast<int32_t*>(so + 0xF8),
						*reinterpret_cast<int32_t*>(so + 0x100));
				}
				// v4.0.27: the InitScroll write is RETIRED. Pre-scrolling was
				// the wrong lever twice over - see the law
				// research\laws\project-sc4-flyout-never-prescroll.md.
			}
		}

		// --- 4. the dock. The sweep can only dock one tick LATER than it
		// scales, because its placement law needs a ring blit at the new
		// buffer size (ringFresh) - which cannot exist until the window has
		// painted once. That is the SECOND settle the player sees. Here the
		// position is the game's native one BY CONSTRUCTION, so the delta
		// applies with no button search and no ring data. The sweep then
		// recognises its own target (atTarget) and does nothing.
		// SUBBORN (v4.0.31): log full builder geometry at birth for every
		// sub-flyout. Captures1x baseline across all scale factors to
		// derive the container shift mathematically. Fires once per open.
		// Reset SUBGEO/SUBGEO2/SUBSHIFT counters here - birth is the one
		// genuine per-open EDGE event. FIX (2026-08-23 review): SUBSHIFT
		// used to reset on `ringFresh` in the sweep, which is a LEVEL
		// condition (true continuously once the ring has painted, not just
		// on the first tick), so its reset ran on every sweep tick and
		// defeated its own 40-line-per-open budget - it became an
		// unconditional per-tick emitter for as long as the flyout stayed
		// open. Resetting once here, at the only real "new menu" moment,
		// is what the sweep's own comment already claimed it was doing.
		gSubGeoLog = 0;
		gSubGeo2Log = 0;
		gSubShiftLog = 0;
		{
			static int sbLog = 30;
			if (sbLog > 0 && strip)
			{
				sbLog--;
				char* so = reinterpret_cast<char*>(strip);
				char* co = reinterpret_cast<char*>(win);
				const int32_t cnt =
					*reinterpret_cast<int32_t*>(so + 0xE8);
				const int32_t firstVis =
					*reinterpret_cast<int32_t*>(so + 0xEC);
				const int32_t sItemW =
					*reinterpret_cast<int32_t*>(so + 0xF8);
				const int32_t sItemH =
					*reinterpret_cast<int32_t*>(so + 0xFC);
				const int32_t sSpacing =
					*reinterpret_cast<int32_t*>(so + 0x100);
				// Container SetLayout fields — these are UNSCALED 1x
				// values; the DLL scales the window size but the game's
				// own layout data stays at 1x.
				const int32_t barW1x =
					*reinterpret_cast<int32_t*>(co + 0xE0);
				const int32_t capH1x =
					*reinterpret_cast<int32_t*>(co + 0xE4);
				const int32_t midH1x =
					*reinterpret_cast<int32_t*>(co + 0xE8);
				const int32_t ringW1x =
					*reinterpret_cast<int32_t*>(co + 0xEC);
				const int32_t ringH1x =
					*reinterpret_cast<int32_t*>(co + 0xF0);
				const int32_t overlap1x =
					*reinterpret_cast<int32_t*>(co + 0xF4);
				const int32_t xAnc1x =
					*reinterpret_cast<int32_t*>(co + 0xF8);
				const int32_t yAnc1x =
					*reinterpret_cast<int32_t*>(co + 0xFC);
				// All scaled values for consistent computation
				const int32_t ringHs =
					RoundHalfUp(ringH1x * gTierF);
				const int32_t capHs =
					RoundHalfUp(capH1x * gTierF);
				const SubStripGeo g =
					SubStripGeometry(ringHs, capHs, sItemH, sSpacing, cnt);
				// armRow requires ringBltY from SUBGEO2; here we
				// estimate assuming ring centred in container.
				// Real armRow = (ringBltY + ringHs/2 - stripTop)
				//               / rowPitch  [from SUBGEO2 data]
				const float armRowEst =
					static_cast<float>(g.contentH / 2 - g.stripTop)
					/ static_cast<float>(g.rowPitch);
				Logger::Get().WriteLine(LogLevel::Info,
					"UiSpike: SUBBORN strip=%p f=%.2f cnt=%d "
					"firstV=%d  sW=%d sH=%d sSp=%d  "
					"barW=%d capH=%d midH=%d ringW=%d ringH=%d "
					"ov=%d xA=%d yA=%d  "
					"ringHs=%d capHs=%d  "
					"contentH=%d stripH=%d stripTop=%d "
					"rowPitch=%d armRow(est)=%.2f  "
					"CONT(%d,%d %dx%d)",
					strip, gTierF, cnt, firstVis,
					sItemW, sItemH, sSpacing,
					barW1x, capH1x, midH1x, ringW1x, ringH1x,
					overlap1x, xAnc1x, yAnc1x,
					ringHs, capHs,
					g.contentH, g.stripH, g.stripTop,
					g.rowPitch, armRowEst,
					win->GetL(), win->GetT(),
					newW, newH);
			}
		}
		int32_t dx = 0, dy = 0;
		if (gSubBornDockOn)
		{
			dx = SubDockDXEff();
			dy = SubDockDYEff();
			// #95: the LEGACY delta is the ring's reference. Reset the ring
			// offsets here - this is the first thing that happens to a NEW
			// menu, so a previous menu's correction can never survive into
			// this one's first paint (the sweep is only 4x/sec, the blits are
			// every frame; birth is the only point that beats them both).
			const int32_t legDY = dy;
			gSubRingAutoX = 0;   // X is never modelled, so this stays 0
			gSubRingAutoY = 0;
			// #95 PHASE 3, ROOT CAUSE (2026-08-23, third pass - see
			// SubPlaceTopMb's comment for the full derivation, and
			// research/laws/project-sc4-flyout-bottom-anchor.md for the
			// write-up). The v4.0.36 SubSharedBottom generalization
			// (mB-clamp gate + hypothetical-8-row cyRef substitution +
			// flat SubContainerShiftPx bornshift) was itself built on a
			// wrong quantity: SubPlaceTop's own bottom margin was
			// `gLastViewH - marginT` (the DESKTOP height), not the
			// game's own measured `mB` (a 434px gap on a 1600-tall
			// desktop at 2x - the bottom HUD/toolbar, not scaling
			// error). That one wrong margin is what made the flat
			// bornshift "necessary": it was compensating for a clamp
			// that fired at the wrong threshold, and the compensation
			// only ever cancelled cleanly for the ONE content height
			// (874, the 8-row cap) it was tuned against - CONFIRMED
			// 2026-08-23 by directly querying the real sub_79AD00 under
			// Unicorn (tools/uimap/emu) with the measured mT=10/mB=1166
			// and fully-scaled item metrics: it reproduces this
			// function's own SUBANCHOR predictions bit-exact, and
			// SEPARATELY reproduces three ALREADY-measured native (f=1)
			// positions on record for Hospitals/Education/Rewards.
			//
			// With margB = mB directly, EVERY bar's OWN real content
			// height (short or tall) naturally clamps to the SAME
			// shared bottom whenever that bar's cy is large enough to
			// reach it - the user's "identical bottom" law falls out of
			// the corrected formula with no hypothetical-8-row hack, no
			// per-bar clamp gate, and no empirical shift constant.
			// SubSharedBottom/SubBarClampsAt8Rows/SubContainerShiftPx
			// are retired from this path.
			//
			// mT/mB are ALREADY the live Place() parameters for THIS
			// open, at whatever tier and resolution are active - no
			// per-tier constant to keep in sync, and no assumption that
			// needs revisiting if a 4x tier is ever added.
			//
			// No disaster branch here: the disaster twin docks and returns in the
			// GODDOCK block far above (REGRESSION.md [CC-13]).
			//
			// FIXED 2026-09-25 FOR BORN CONTAINERS ("birth owns the dock",
			// see gSubBornWin). The sweep-time mirror (search
			// `SubPlaceTop(sub->GetH()`) still carries the OLD viewH-margin
			// formula plus `SubContainerShiftFromGeo`, and it disagreed with
			// THIS formula: no button matched for 6+ item strips (dead
			// back-arrow zone - `SUBGEO BTN` count 0), and for the 5-item
			// memo.submenus power strip at 3x it matched the NEIGHBOUR and
			// rewrote the ring pin one row down. A container docked here now
			// records its anchor, top and pin, and the sweep reuses them
			// instead of re-deriving them. The old formula remains ONLY for
			// containers this block did not dock (SubBornDock=0 / SubMath=0).
			// Gate: _tests\Test-SubBirthOwnsDock.py.
			if (!isDisaster && gSubMath && ch > 0)
			{
				const int32_t nativeT = win->GetT();
				const int32_t top = SubPlaceTopMb(newH, cy, mT, mB, gTierF);
				// ABSOLUTE -> RELATIVE: GZWinMoveTo moves BY, not TO.
				dy = top - nativeT;
				// Hold the ring at the legacy dock, so the FIRST paint
				// is already right and there is no attach-then-jump.
				gSubRingAutoY = legDY - dy;
				// BIRTH OWNS THE DOCK: this open's decisions, for the sweep
				// to reuse (see gSubBornWin). `top` is where the move below
				// puts the container: nativeT + dy.
				gSubBornWin = win;
				gSubBornCy = cy;
				gSubBornTopRel = top;
				gSubBornAutoY = gSubRingAutoY;
				gSubBornH = newH;
				gSubOwnLog = 0;
				// 2026-08-23: raised 40 -> 2000, same reason as SUBPLACE's
				// budget above.
				static int sAnchorLog = 2000;
				if (sAnchorLog > 0)
				{
					sAnchorLog--;
					Logger::Get().WriteLine(LogLevel::Info,
						"UiSpike: SUBANCHOR strip=%p f=%.2f cy=%d mT=%d "
						"mB=%d newH=%d nativeT=%d top=%d dy=%d",
						strip, gTierF, cy, mT, mB,
						newH, nativeT, top, dy);
				}
			}
			if (dx != 0 || dy != 0)
			{
				win->GZWinMoveTo(dx, dy);   // RELATIVE - moves BY, not TO
			}
		}

		// --- 5. hand both windows to the sweep as ALREADY SCALED.
		NoteBorn(win, 0x8A6E61E0, cw, ch, newW, newH);
		void* stripWin = nullptr;
		if (strip)
		{
			// The strip control's window via its own vt+0x0C, exactly the call
			// the builder makes at 0x7EB1D9 - never a guessed obj+4.
			typedef void*(__fastcall* GetWinFn)(void*, void*);
			// deref-ok: strip is the hooked control; svt && svt[3] checked
			void** svt = *reinterpret_cast<void***>(strip);
			if (svt && svt[3])
			{
				// deref-ok: the strip control's own GetWindow slot (builder call 0x7EB1D9)
				stripWin = reinterpret_cast<GetWinFn>(svt[3])(strip, nullptr);
			}
			if (stripWin)
			{
				NoteBorn(stripWin, 0x8A2CAD8B, osw, osh,
					sr[2] - sr[0], sr[3] - sr[1]);
			}
		}

		// --- 6. the ring/bar scaler must be live for the FIRST paint too.
		EnsureBufferClassBltHook();

		// --- 7. and so must the PER-WINDOW state it reads (v2.36.2). Measured:
		// with only the class hook installed here, the first sub-flyout of a
		// city still painted a 1x bar for 159ms (9 frames) - "DCBUF dst(205,..)
		// src 53x3 selfWxH=258x874": 53px of bar art flush to the right edge of
		// a 258 buffer, with the ring aligned to it. [0xe0] was still 53 and
		// only became 106 when the sweep's SUBCLAIM ran. Opens #2+ never showed
		// it because they INHERIT the latched state from the previous open -
		// they are not faster (30-48ms), they are pre-warmed.
		if (gSpikeSelf && stripWin)
		{
			gSpikeSelf->InstallSubFlyoutHooksNow(
				win, reinterpret_cast<cIGZWin*>(stripWin));
		}

		if (gSubBornLog2 < 10)
		{
			gSubBornLog2++;
			// cnt re-read here (the SUBBORN block's own local died at the
			// close of its brace above) so this final-numbers line can be
			// correlated to a strip's item count without cross-referencing
			// the earlier SUBBORN line by pointer alone.
			const int32_t cnt2 = strip
				? *reinterpret_cast<int32_t*>(
					reinterpret_cast<char*>(strip) + 0xE8)
				: -1;
			Logger::Get().WriteLine(LogLevel::Debug,
				"UiSpike: SUBBORN2 0x8A6E61E0 born x%.2f cnt=%d: container "
				"%dx%d -> %dx%d at (%d,%d)%+d%+d, strip rel(%d,%d) %dx%d -> "
				"(%d,%d) %dx%d, items x%.2f%s.",
				gTierF, cnt2, cw, ch, newW, newH, l, t, dx, dy,
				osl, ost, osw, osh, sr[0], sr[1],
				sr[2] - sr[0], sr[3] - sr[1], gTierF,
				stripWin ? "" : " (STRIP WINDOW NOT RESOLVED)");
		}
	}
}

// ============ FIRST-LEVEL FLYOUT: SCALE ON OPEN (v2.36.1, task #50) =====
// MEASURED, from the v2.36.0 session log - which is why this exists at all.
// v2.36.0 born-scaled the NESTED container and fired ZERO times, because the
// menus the player calls "sub flyouts" are the FIRST-LEVEL tool flyouts. The
// log named them and their cost in the same line:
//     mayor flyout 0x699306ED at(22,344) size 230x710, +10 win (docked).
//     mayor flyout 0x69923479 at(22,344) size 230x720,  +6 win (docked).
//     god   flyout 0x49923239 at(22,344) size 250x498,  +8 win (moved).
// "+N win" is N windows scaled AT THE MOMENT IT OPENED - so the flyout was on
// screen at 1x, at its native position, until that sweep ran. One frame at
// 18.34ms. That is the jump.
//
// UiSpike.cpp's own comment already said why there was no cure: these are
// "DESTROYED AND RECREATED on every open rather than hidden, so there is no
// pre-scale while hidden to do". Correct - and the answer is the same one as
// for the nested container: act at the OPEN, not on the next tick.
//
// THE HOOK POINT IS A SINGLE FUNNEL... CORRECTED v2.39.6: it is TWO. The
// line above originally said "seven call sites, single funnel" - an exhaustive
// E8-rel32 scan of the exe (2026-07-31) found ELEVEN sites calling sub_7E5C10
// (0x7EC770, 0x7EDB16, 0x7EDC12, 0x7EDC73, 0x7EF6D9, 0x7F484E, 0x7F48B2,
// 0x7F4C80, 0x7F4FE6, 0x7F5049, 0x7F5221 - Emergency, U-Drive-It and
// Terrain-FX/Day-Night ARE among them, three flyouts the first generation
// audit wrongly filed as unfunnelled) PLUS a byte-identical TWIN opener
// sub_7E5D80 (same prologue, latch [edi+0x204] instead of [edi+0x200], ONE
// extra stack arg -> ret 0x14) with exactly two call sites:
//     0x7F50A7  Signs & Labels 0xAB954023  (script 0xCB95403E) - the ONE
//               flyout that was still generation 1 until the twin was hooked
//     0x7E718A  flyout 0x09DE8798 (script 0x09DE3002) - DEAD CONTENT: that
//               script exists in NO archive on the machine (game + every
//               plugin, any-type scan, positive control: every live flyout
//               script IS found). If the branch ever fired, OnFlyoutOpened's
//               `if (win ...)` guard no-ops on the unresolvable id.
// sub_7E5C10's arg2 IS the flyout id (compared against [this+0x200] - its own
// "clicked the same button again = close" test). __thiscall, ret 0x10.
//
// WHAT WE RUN THERE: the EXISTING pass, unchanged. Not a copy of it, not a new
// geometry path - ScaleGodFlyouts is built to run 60x/sec and is idempotent
// via scaleMap, so calling it one tick earlier changes only WHEN. That keeps
// the blast radius at "the same code, sooner" (law 29).
namespace
{
	typedef int(__fastcall* FlyoutOpenFn)(void*, void*, uint32_t, uint32_t,
		void*, uint32_t);
	FlyoutOpenFn gOrigFlyoutOpen = nullptr;
	bool gFlyoutOpenInstalled = false;
	int  gFlyoutOpenOn = 1;          // [Flyout] BornOnOpen - live-tunable
	int  gFlyoutOpenLog = 0;
	// v2.39.6: the TWIN opener sub_7E5D80 (Signs & Labels + one dead branch).
	// One extra stack arg vs the funnel -> its own typedef; __fastcall with
	// five stack args compiles to the matching ret 0x14 callee-clean.
	typedef int(__fastcall* FlyoutOpen2Fn)(void*, void*, uint32_t, uint32_t,
		void*, uint32_t, uint32_t);
	FlyoutOpen2Fn gOrigFlyoutOpen2 = nullptr;

	int __fastcall FlyoutOpenDetour(void* self, void* edx, uint32_t scriptId,
		uint32_t flyoutId, void* a3, uint32_t a4)
	{
		// Let the game build and show the flyout first - we scale what it
		// produced, exactly as the sweep would have a tick later.
		const int r = gOrigFlyoutOpen(self, edx, scriptId, flyoutId, a3, a4);
		if (gFlyoutOpenOn && gSpikeSelf && gTierF > 1.01f)
		{
			gSpikeSelf->OnFlyoutOpened(flyoutId);
		}
		return r;
	}

	int __fastcall FlyoutOpenDetour2(void* self, void* edx, uint32_t scriptId,
		uint32_t flyoutId, void* a3, uint32_t a4, uint32_t a5)
	{
		const int r = gOrigFlyoutOpen2(self, edx, scriptId, flyoutId, a3, a4, a5);
		if (gFlyoutOpenOn && gSpikeSelf && gTierF > 1.01f)
		{
			gSpikeSelf->OnFlyoutOpened(flyoutId);
		}
		return r;
	}
}

void UiSpike::OnFlyoutOpened(uint32_t flyoutId)
{
	if (!lastView || inPass) { return; }     // no view yet, or already sweeping
	{
		PassGuard passGuard(*this);          // no nested tree walks (see Run);
		                                     // RAII so an unwind cannot latch it
		ScaleGodFlyouts(lastView, gTierF);
	}
	// v2.36.3 (task #77): sub_7E5C10 is also the CLOSER - clicking the same
	// button again closes the flyout (it compares arg2 against [this+0x200]).
	// On a close the window is already gone, and the old line logged
	// "(-1,-1) -1x-1", which reads like a failure. The pass itself is a
	// harmless no-op there, so say nothing.
	cIGZWin* win = lastView->GetChildWindowFromIDRecursive(flyoutId);
	if (win && gFlyoutOpenLog < 12)
	{
		gFlyoutOpenLog++;
		Logger::Get().WriteLine(LogLevel::Info,
			"UiSpike: FLYOPEN 0x%08X scaled at OPEN (before first paint) - "
			"now (%d,%d) %dx%d.", flyoutId,
			win->GetL(), win->GetT(), win->GetW(), win->GetH());
	}
}

void UiSpike::InstallFlyoutOpenHook()
{
	if (gFlyoutOpenInstalled) { return; }
	gSpikeSelf = this;
	gFlyoutOpenOn = settings.spikeFlyoutBornOnOpen;
	if (gFlyoutOpenOn <= 0) { return; }
	if (gTierF <= 1.01f) { return; }         // stock tier stays inert

	const uintptr_t base = ExeBase();
	void* target = reinterpret_cast<void*>(base - 0x400000 + 0x007E5C10);

	const MH_STATUS init = MH_Initialize();
	if (init != MH_OK && init != MH_ERROR_ALREADY_INITIALIZED)
	{
		Logger::Get().WriteLine(LogLevel::Error,
			"UiSpike: FLYOPEN MH_Initialize failed (%d).", init);
		return;
	}
	if (MH_CreateHook(target, reinterpret_cast<void*>(&FlyoutOpenDetour),
			reinterpret_cast<void**>(&gOrigFlyoutOpen)) != MH_OK
		|| MH_EnableHook(target) != MH_OK)
	{
		Logger::Get().WriteLine(LogLevel::Error,
			"UiSpike: FLYOPEN failed to hook the flyout opener at %p.", target);
		return;
	}
	gFlyoutOpenInstalled = true;
	Logger::Get().WriteLine(LogLevel::Info,
		"UiSpike: FLYOPEN installed on the tool-flyout opener %p - every "
		"first-level flyout is scaled + docked at its OPEN instead of on the "
		"next sweep tick (the +N-win-at-open frame).", target);

	// v2.39.6 (task #81): the TWIN opener - Signs & Labels was the ONE flyout
	// still on generation 1, solely because it opens through this function
	// instead of the funnel above. Same treatment, same pass, same switch.
	// Its failure is deliberately NON-FATAL: the primary funnel hook stays.
	void* target2 = reinterpret_cast<void*>(base - 0x400000 + 0x007E5D80);
	if (MH_CreateHook(target2, reinterpret_cast<void*>(&FlyoutOpenDetour2),
			reinterpret_cast<void**>(&gOrigFlyoutOpen2)) != MH_OK
		|| MH_EnableHook(target2) != MH_OK)
	{
		Logger::Get().WriteLine(LogLevel::Error,
			"UiSpike: FLYOPEN2 failed to hook the twin opener at %p - "
			"Signs & Labels stays on the sweep (one open-frame at 1x).",
			target2);
		return;
	}
	Logger::Get().WriteLine(LogLevel::Info,
		"UiSpike: FLYOPEN2 installed on the twin opener %p - Signs & Labels "
		"(the last generation-1 flyout) is now scaled + docked at its OPEN.",
		target2);
}

// v2.36.2: the SUBHOOK/SUBCLAIM install, run AT BIRTH instead of on the sweep.
// Byte-for-byte the same operations the sweep performs (ScaleGodFlyouts, the
// KNOWN-MENU GATE block) - same crash guard, same vtable checks, same guarded
// claim promotion - just earlier, so the very first sub-flyout of a city does
// not paint 9 frames of 1x bar while it waits.
//
// THE TWO HALVES ARE ONE OPERATION. [0xE0] is DUAL-USE: the hit-claim width
// AND a Plot layout inset. SlotThunk<88> presents the latched 1x value to the
// draw group and re-arms the 2x claim after. Promote [0xE0] WITHOUT installing
// that thunk first and the game paints a SECOND orange bar (v2.11.24, user
// confirmed). Order here is: container thunks -> claim -> strip thunks.
//
// THE CRASH GUARD IS NOT OPTIONAL (law 3, v2.22.1). These hooks were
// validated only on the known parent menus; when U-Drive-It -> Earned Cars
// (an 88-WIDE strip, a foreign layout) received them the game died. Positive
// identification only.
namespace
{
	// The parent menus whose sub-flyouts the claim/strip hooks were validated
	// on, in the order the dock code tries them (audit B9: this table was
	// written three times). Positive identification only (law 3, v2.22.1):
	// U-Drive-It -> Earned Cars, an 88-WIDE strip, crashed the game when it
	// got the hooks. v2.25.3 (task #48) opted in the two tool-flyout COLUMNS,
	// the same 258-wide architecture as the five originals (live log
	// 2026-07-30: "SUBSKIP container 0x8A6E61E0 258x874"), which is why the
	// gate stays an id list, never a width test alone.
	const uint32_t kSubFlyoutParents[] = {
		0x49923239, 0x69923479, 0xC99237A0, 0xE992F711, 0x699306ED,
		0x8BB27C12, 0xAB954023
	};

	bool KnownSubFlyoutParentOpen(cIGZWin* root)
	{
		for (uint32_t pid : kSubFlyoutParents)
		{
			cIGZWin* par = root->GetChildWindowFromIDRecursive(pid);
			if (par && par->IsVisible()) { return true; }
		}
		return false;
	}
}

void UiSpike::InstallSubFlyoutHooksNow(cIGZWin* sub, cIGZWin* strip)
{
	if (!sub || !strip || !lastView || gClaimScale <= 1) { return; }
	if (!KnownSubFlyoutParentOpen(lastView)) { return; }

	void** subVt = *reinterpret_cast<void***>(sub);
	if (subVt != reinterpret_cast<void**>(0x00AB6AA8)) { return; }
	void** kvt = *reinterpret_cast<void***>(strip);
	if (kvt != reinterpret_cast<void**>(0x00AB6D88)) { return; }

	// ---- container: buffer force-recreate + the [0xE0] presentation -------
	for (int vi = 0; vi < 256; vi++) { gVtCopy[vi] = subVt[vi]; }
	for (int si = 87; si <= 97; si++)
	{
		gOrigSlot[si] = reinterpret_cast<SlotFn>(subVt[si]);
		gVtCopy[si] = reinterpret_cast<void*>(
			si == 87 ? (void*)&SlotThunk<87> :
			si == 88 ? (void*)&SlotThunk<88> :
			si == 89 ? (void*)&SlotThunk<89> :
			si == 90 ? (void*)&SlotThunk<90> :
			si == 91 ? (void*)&SlotThunk<91> :
			si == 92 ? (void*)&SlotThunk<92> :
			si == 93 ? (void*)&SlotThunk<93> :
			si == 94 ? (void*)&SlotThunk<94> :
			si == 95 ? (void*)&SlotThunk<95> :
			si == 96 ? (void*)&SlotThunk<96> :
			           (void*)&SlotThunk<97>);
	}
	if (gClickHook && gArrowClick)
	{
		gOrigContPt121 = reinterpret_cast<PtInFn>(subVt[121]);
		gVtCopy[121] = reinterpret_cast<void*>(&ContPt121Thunk);
	}
	*reinterpret_cast<void***>(sub) = gVtCopy;
	gForceInvalidate = 20;
	gDisasterDrawTuning = 0;   // this is not the disaster flyout

	// ---- claim width, only while still in its 1x range (idempotent) -------
	int32_t* claimW = reinterpret_cast<int32_t*>(
		reinterpret_cast<char*>(sub) + 0xE0);
	if (*claimW >= 30 && *claimW <= 60)
	{
		const int32_t oldW = *claimW;
		gClaimOrig = oldW;
		*claimW = RoundHalfUp(oldW * gTierF);
	}

	// ---- strip: item fields + the click path ------------------------------
	for (int vi = 0; vi < 256; vi++) { gVtCopy2[vi] = kvt[vi]; }
	for (int si = 87; si <= 97; si++)
	{
		gOrigSlot2[si] = reinterpret_cast<SlotFn>(kvt[si]);
		gVtCopy2[si] = reinterpret_cast<void*>(
			si == 87 ? (void*)&SlotThunk2<87> :
			si == 88 ? (void*)&SlotThunk2<88> :
			si == 89 ? (void*)&SlotThunk2<89> :
			si == 90 ? (void*)&SlotThunk2<90> :
			si == 91 ? (void*)&SlotThunk2<91> :
			si == 92 ? (void*)&SlotThunk2<92> :
			si == 93 ? (void*)&SlotThunk2<93> :
			si == 94 ? (void*)&SlotThunk2<94> :
			si == 95 ? (void*)&SlotThunk2<95> :
			si == 96 ? (void*)&SlotThunk2<96> :
			           (void*)&SlotThunk2<97>);
	}
	if (gClickHook)
	{
		gOrigMouse136 = reinterpret_cast<MouseFn>(kvt[136]);
		gOrigMouse138 = reinterpret_cast<MouseFn>(kvt[138]);
		gOrigPt121    = reinterpret_cast<PtInFn>(kvt[121]);
		gOrigSlot149  = reinterpret_cast<PtInFn>(kvt[149]);
		gOrigSlot62   = reinterpret_cast<PtInFn>(kvt[62]);
		gOrigSlot59   = reinterpret_cast<XformFn>(kvt[59]);
		gVtCopy2[62]  = reinterpret_cast<void*>(&Slot62Thunk);
		gVtCopy2[59]  = reinterpret_cast<void*>(&Slot59Thunk);
		gVtCopy2[136] = reinterpret_cast<void*>(&Mouse136Thunk);
		gVtCopy2[138] = reinterpret_cast<void*>(&Mouse138Thunk);
		gVtCopy2[121] = reinterpret_cast<void*>(&Pt121Thunk);
		gVtCopy2[149] = reinterpret_cast<void*>(&Slot149Thunk);
	}
	*reinterpret_cast<void***>(strip) = gVtCopy2;

	static int bornHookLog = 0;
	if (bornHookLog < 8)
	{
		bornHookLog++;
		// NOTE the strip is hooked BEFORE its own SetID/SetArea run (both come
		// after GetStripRect in the builder), so printing its id or rect here
		// would log zeros. Print what is real at this instant.
		Logger::Get().WriteLine(LogLevel::Debug,
			"UiSpike: SUBBORNHOOK container 0x%08X %dx%d hooked AT BIRTH with "
			"its strip (ptr %p, pre-SetID), claim [0xe0] -> %d. This closes the "
			"159ms first-open 1x-bar window.",
			sub->GetID(), sub->GetW(), sub->GetH(),
			reinterpret_cast<void*>(strip), *claimW);
	}
}

// ============ VISIBILITY TRACE (v2.36.8, task #59) ======================
// THE INSTRUMENT THE BORDER ACTUALLY NEEDS, after two of mine failed for the
// same reason: the v2.36.4 EdgeDump probe walked one root, then two levels
// (that probe was removed in the 2026-09-25 audit once #59/#60 closed). The two
// anonymous full-screen candidates (vt 0x00AB8CD0 / 0x00AB8F50) came from the
// FULL tree dump, so they live deeper than that, and pausing added no
// full-screen window at either shallow depth.
//
// So: walk the WHOLE tree from the main window (the 3D view is a descendant,
// so one root covers everything) at full depth, and print ONLY the windows
// whose VISIBILITY CHANGED since the previous pass. Pausing then prints
// exactly what appeared - no size filter, no depth limit, no guess about
// which root owns it. Law 20: hidden children are included, because the
// border may exist all along and merely become visible.
//
// [Probe] VisTrace=1. Capped at 300 lines so it cannot flood a play session.
namespace
{
	struct VisSeen { void* win; uint8_t vis; };
	VisSeen gVisSeen[2048] = {};
}

namespace UiSpikeInternal
{
	int gVisSeenN = 0;
}

namespace
{
	int gVisTrace = 0;      // [Probe] VisTrace - live-tunable
	int gVisLogged = 0;
	bool gVisPrimed = false;

	int8_t VisLookup(void* w)
	{
		for (int i = 0; i < gVisSeenN; i++)
		{
			if (gVisSeen[i].win == w) { return static_cast<int8_t>(gVisSeen[i].vis); }
		}
		return -1;
	}
	void VisStore(void* w, uint8_t v)
	{
		for (int i = 0; i < gVisSeenN; i++)
		{
			if (gVisSeen[i].win == w) { gVisSeen[i].vis = v; return; }
		}
		if (gVisSeenN < 2048) { gVisSeen[gVisSeenN++] = { w, v }; }
	}

	void VisWalk(cIGZWin* win, int depth)
	{
		if (!win || depth > 24 || gVisLogged >= 300) { return; }
		const uint8_t vis = win->IsVisible() ? 1u : 0u;
		const int8_t prev = VisLookup(win);
		// v2.36.9 — THE GAP IN v2.36.8, found by reasoning about its own null
		// result. It logged only FLIPS of windows it had already seen, so a
		// window CREATED when you pause was silently baselined and never
		// reported. The pause badge visibly appears, so "zero flips" could
		// never have proved "not a window" - it only ruled out one of the two
		// ways a window can arrive. NEW windows now print too.
		const bool isNew = (prev < 0);
		if (gVisPrimed && (isNew || static_cast<uint8_t>(prev) != vis))
		{
			gVisLogged++;
			Logger::Get().WriteLine(LogLevel::Debug,
				"UiSpike: VIS %s d=%d id=0x%08X vt=%p (%d,%d %dx%d) kids=%d",
				isNew ? (vis ? "NEW+VIS" : "NEW-hid")
				      : (vis ? "SHOWN  " : "hidden "),
				depth, win->GetID(), *reinterpret_cast<void**>(win),
				win->GetL(), win->GetT(), win->GetW(), win->GetH(),
				win->GetChildCount());
		}
		VisStore(win, vis);
		if (win->GetChildCount() > 0)
		{
			ChildSnapshot snap = {};
			win->EnumChildren(GZIID_cIGZWin, ChildSnapshot::Callback, &snap);
			for (int i = 0; i < snap.count; i++)
			{
				VisWalk(snap.wins[i], depth + 1);
			}
		}
	}
}

void UiSpike::VisTraceTick()
{
	if (gVisTrace <= 0) { return; }
	cISC4AppPtr pSC4App;
	cIGZWin* pMainWindow = pSC4App ? pSC4App->GetMainWindow() : nullptr;
	if (!pMainWindow) { return; }
	const bool first = !gVisPrimed;
	VisWalk(pMainWindow, 0);
	if (first)
	{
		gVisPrimed = true;
		Logger::Get().WriteLine(LogLevel::Info,
			"UiSpike: VIS primed - %d windows baselined from the MAIN window "
			"at full depth. From here only visibility CHANGES print (cap 300). "
			"PAUSE now: whatever the border is, it must appear as SHOWN.",
			gVisSeenN);
	}
}

void UiSpike::DrainBornScaleRecords()
{
	for (int i = 0; i < gBornQN; i++)
	{
		const BornRec& b = gBornQ[i];
		ScaleRecord rec = {};
		rec.id = b.id;
		rec.origW = b.ow;
		rec.origH = b.oh;
		rec.scaledW = b.sw;
		rec.scaledH = b.sh;
		rec.resetRescales = 0;
		rec.leaveAlone = false;
		scaleMap[b.win] = rec;
	}
	gBornQN = 0;
}

void UiSpike::InstallSubFlyoutBornScale()
{
	if (gSubBornScaleInstalled) { return; }
	gSubBornScaleOn = settings.spikeSubFlyoutBornScale;
	gSubBornDockOn = settings.spikeSubFlyoutBornDock;
	if (gSubBornScaleOn <= 0) { return; }
	if (gTierF <= 1.01f) { return; }        // stock tier stays inert

	const uintptr_t base = ExeBase();
	void* place = reinterpret_cast<void*>(base - 0x400000 + 0x0079AD00);
	void* metrics = reinterpret_cast<void*>(base - 0x400000 + 0x0079A0E0);

	const MH_STATUS init = MH_Initialize();
	if (init != MH_OK && init != MH_ERROR_ALREADY_INITIALIZED)
	{
		Logger::Get().WriteLine(LogLevel::Error,
			"UiSpike: SUBBORN2 MH_Initialize failed (%d).", init);
		return;
	}
	if (MH_CreateHook(metrics, reinterpret_cast<void*>(&SubMetricsDetour),
			reinterpret_cast<void**>(&gOrigSubMetrics)) != MH_OK
		|| MH_EnableHook(metrics) != MH_OK)
	{
		Logger::Get().WriteLine(LogLevel::Error,
			"UiSpike: SUBBORN2 failed to hook SetItemMetrics at %p.", metrics);
		return;
	}
	if (MH_CreateHook(place, reinterpret_cast<void*>(&SubPlaceDetour),
			reinterpret_cast<void**>(&gOrigSubPlace)) != MH_OK
		|| MH_EnableHook(place) != MH_OK)
	{
		MH_DisableHook(metrics);
		Logger::Get().WriteLine(LogLevel::Error,
			"UiSpike: SUBBORN2 failed to hook Place at %p.", place);
		return;
	}
	gSubBornScaleInstalled = true;
	Logger::Get().WriteLine(LogLevel::Info,
		"UiSpike: SUBBORN2 installed (Place %p + SetItemMetrics %p) - nested "
		"sub-flyouts are born x%.2f, dock=%d. Geometry is identical to the "
		"sweep's (emu_subflyout.py, 71 checks); only the timing changes.",
		place, metrics, gTierF, gSubBornDockOn);
}

namespace
{
	// v2.43.3: MDOCK is a per-id FACT ("this script's marker differs from the
	// one our constant was measured on"), not a per-tick event - but it sat in
	// the dock path, which runs every 16ms while a flyout is open: 5211 lines
	// and a 1MB log in one session. Log it ONCE per id per city. Reset in
	// Disarm so a second city re-reports (the script could differ there).
	uint32_t gMDockLogged[8] = {};
}

namespace UiSpikeInternal
{
	int gMDockLoggedN = 0;
}

namespace
{
	// #95: MDRIFT alarm switch ([Flyout] MarkerAlarm, default 1). Cheap -
	// one line per id per city via MDockShouldLog (ids XORed so a god-path
	// entry cannot silence its mayor-path twin).
	int gMDockAlarm = 1;
	// #198: derive the god dock from the live marker (see the dock site). Default
	// ON. It is an identity on a stock install - the kill switch exists so a
	// user who hits a bad interaction can get the old behaviour back in one
	// ini line rather than waiting for a build.
	int gGodMarkerFix = 1;
	bool MDockShouldLog(uint32_t id)
	{
		for (int i = 0; i < gMDockLoggedN; i++)
		{
			if (gMDockLogged[i] == id) { return false; }
		}
		if (gMDockLoggedN < 8) { gMDockLogged[gMDockLoggedN++] = id; return true; }
		return false;
	}
}

namespace UiSpikeInternal
{
	// Collect EVERY window with the given id under root (bounded walk).
	// v2.25.20, the budget-dialog lesson: GetChildWindowFromIDRecursive
	// returns the FIRST match, and these ids exist TWICE - a permanent
	// HIDDEN template plus the OPEN instance - so the single-find plus
	// IsVisible() check skipped the real dialog on every pass (the minimap
	// non-unique-id trap, again). Callers iterate all matches.
	struct IdCollectCtx
	{
		uint32_t id;
		cIGZWin** out;
		int max;
		int* n;
		int depth;
		static bool Callback(cIGZWin* /*parent*/, uint32_t /*childID*/,
			void* child, void* pContext)
		{
			IdCollectCtx* ctx = static_cast<IdCollectCtx*>(pContext);
			cIGZWin* win = static_cast<cIGZWin*>(child);
			if (!win) { return true; }
			if (win->GetID() == ctx->id && *ctx->n < ctx->max)
			{
				ctx->out[(*ctx->n)++] = win;
			}
			if (ctx->depth < 8 && *ctx->n < ctx->max)
			{
				IdCollectCtx sub = { ctx->id, ctx->out, ctx->max, ctx->n,
					ctx->depth + 1 };
				win->EnumChildren(GZIID_cIGZWin, IdCollectCtx::Callback, &sub);
			}
			return true;
		}
	};

	// ---- BATCHED ID LOOKUPS (audit A1, 2026-09-25) --------------------------
	// An idle city tick cost ~46 whole-tree walks, most of them
	// GetChildWindowFromIDRecursive calls that MISS - and a miss walks the
	// whole subtree. These answer a list
	// of ids in ONE walk with the engine's own order (decompiled 0x0099DEC4:
	// post-order, EnumChildren order, children before self, the root last,
	// first match wins), keeping the first match per id. That gives each id
	// the answer its own call would have given, as long as nothing changes the
	// tree between the walk and the use of an answer - callers that do change
	// it re-walk the ids still to come (IdBatch::Touched).
	//
	// POSITIVE CONTROL. The first kIdWalkChecks walks are re-asked of the
	// engine (or, for the collect walk, of IdCollectCtx), id by id. A
	// disagreement is logged and the engine's answer is used; the IDWALK
	// summary line reports the result either way.
	const unsigned kIdWalkChecks = 2048;
	unsigned gIdWalkChecked = 0;
	unsigned gIdWalkIds = 0;
	unsigned gIdWalkHits = 0;
	unsigned gIdWalkBad = 0;

	void NoteIdWalkChecked()
	{
		if (++gIdWalkChecked != kIdWalkChecks) { return; }
		Logger::Get().WriteLine(LogLevel::Info,
			"UiSpike: IDWALK %u batched walk(s) checked against the per-id "
			"lookups they replace (%u id answer(s), %u hit(s)): %u disagreed%s. "
			"Checking stops here.",
			gIdWalkChecked, gIdWalkIds, gIdWalkHits, gIdWalkBad,
			gIdWalkBad ? " - READ THE IDWALK DISAGREES LINES ABOVE" : "");
	}

	void NoteIdWalkDisagrees(uint32_t id, cIGZWin* root, const char* what,
		const void* batched, const void* engine)
	{
		if (++gIdWalkBad > 8) { return; }
		Logger::Get().WriteLine(LogLevel::Info,
			"UiSpike: IDWALK DISAGREES for 0x%08X under 0x%08X (%s): batched "
			"%p, per-id %p - using the per-id answer.",
			id, root ? root->GetID() : 0u, what, batched, engine);
	}

	struct IdFindCtx
	{
		const uint32_t* ids;
		cIGZWin** out;
		int n;
		int left;

		static void Match(cIGZWin* win, IdFindCtx* ctx)
		{
			const uint32_t id = win->GetID();
			for (int k = 0; k < ctx->n; k++)
			{
				if (!ctx->out[k] && ctx->ids[k] == id)
				{
					ctx->out[k] = win;
					ctx->left--;
				}
			}
		}

		static bool Callback(cIGZWin* /*parent*/, uint32_t /*childID*/,
			void* child, void* pContext)
		{
			IdFindCtx* ctx = static_cast<IdFindCtx*>(pContext);
			cIGZWin* win = static_cast<cIGZWin*>(child);
			if (!win || ctx->left <= 0) { return true; }
			win->EnumChildren(GZIID_cIGZWin, IdFindCtx::Callback, ctx);
			Match(win, ctx);
			return true;
		}
	};

	// out[k] = root->GetChildWindowFromIDRecursive(ids[k]), for every k.
	void FindIdsRecursive(cIGZWin* root, const uint32_t* ids, int n,
		cIGZWin** out)
	{
		for (int k = 0; k < n; k++) { out[k] = nullptr; }
		if (!root || n <= 0) { return; }
		IdFindCtx ctx = { ids, out, n, n };
		root->EnumChildren(GZIID_cIGZWin, IdFindCtx::Callback, &ctx);
		if (ctx.left > 0) { IdFindCtx::Match(root, &ctx); }

		if (gIdWalkChecked >= kIdWalkChecks) { return; }
		for (int k = 0; k < n; k++)
		{
			cIGZWin* engine = root->GetChildWindowFromIDRecursive(ids[k]);
			gIdWalkIds++;
			if (engine) { gIdWalkHits++; }
			if (engine != out[k])
			{
				NoteIdWalkDisagrees(ids[k], root, "find", out[k], engine);
				out[k] = engine;
			}
		}
		NoteIdWalkChecked();
	}

	// w->GetChildWindowFromIDRecursive(w's own id) walks all of w's subtree,
	// finds no descendant with that id, and returns w itself (self last).
	// Checked against that lookup during the IDWALK window like the walks.
	cIGZWin* SelfLookup(cIGZWin* w, uint32_t id)
	{
		if (w && gIdWalkChecked < kIdWalkChecks)
		{
			cIGZWin* engine = w->GetChildWindowFromIDRecursive(id);
			gIdWalkIds++;
			if (engine) { gIdWalkHits++; }
			if (engine != w)
			{
				NoteIdWalkDisagrees(id, w, "self", w, engine);
				return engine;
			}
		}
		return w;
	}

	// A fixed list of lookups that a loop consumes IN ORDER, answered by one
	// walk. The loop calls Touched() once it has done anything that may change
	// the tree (scaled, moved or rebuilt what it found); the ids still to come
	// are then re-walked before the next answer is handed out. Asked for an id
	// out of sequence, it falls back to the engine's own lookup - so a future
	// edit of the loop's gates cannot make it hand out a wrong answer.
	struct IdBatch
	{
		static const int kMax = 16;
		cIGZWin* root = nullptr;
		uint32_t ids[kMax] = {};
		cIGZWin* wins[kMax] = {};
		int n = 0;
		int next = 0;
		bool walked = false;
		bool stale = false;

		void Add(uint32_t id) { if (n < kMax) { ids[n++] = id; } }

		cIGZWin* Next(uint32_t id)
		{
			if (next >= n || ids[next] != id)
			{
				return root ? root->GetChildWindowFromIDRecursive(id) : nullptr;
			}
			if (!walked || stale)
			{
				FindIdsRecursive(root, ids + next, n - next, wins + next);
				walked = true;
				stale = false;
			}
			return wins[next++];
		}

		void Touched() { stale = true; }
	};

	// IdCollectCtx for several ids in ONE walk: the same pre-order, depth-8
	// walk, keeping up to 4 matches per id in walk order. It descends while
	// ANY id is below its cap - a superset of each single walk's nodes - and
	// an id at its cap takes no more, so every id's list comes out identical
	// to its own walk's.
	struct IdCollectManyCtx
	{
		const uint32_t* ids;
		int n;
		cIGZWin* (*out)[4];
		int* counts;
		int* open;   // ids still below the cap
		int depth;

		static bool Callback(cIGZWin* /*parent*/, uint32_t /*childID*/,
			void* child, void* pContext)
		{
			IdCollectManyCtx* ctx = static_cast<IdCollectManyCtx*>(pContext);
			cIGZWin* win = static_cast<cIGZWin*>(child);
			if (!win) { return true; }
			const uint32_t id = win->GetID();
			for (int k = 0; k < ctx->n; k++)
			{
				if (ctx->ids[k] == id && ctx->counts[k] < 4)
				{
					ctx->out[k][ctx->counts[k]++] = win;
					if (ctx->counts[k] == 4) { (*ctx->open)--; }
				}
			}
			if (ctx->depth < 8 && *ctx->open > 0)
			{
				IdCollectManyCtx sub = *ctx;
				sub.depth = ctx->depth + 1;
				win->EnumChildren(GZIID_cIGZWin, IdCollectManyCtx::Callback, &sub);
			}
			return true;
		}
	};

	void CollectIdsUnder(cIGZWin* root, const uint32_t* ids, int n,
		cIGZWin* (*out)[4], int* counts)
	{
		for (int k = 0; k < n; k++)
		{
			counts[k] = 0;
			for (int i = 0; i < 4; i++) { out[k][i] = nullptr; }
		}
		if (!root || n <= 0) { return; }
		int open = n;
		IdCollectManyCtx ctx = { ids, n, out, counts, &open, 0 };
		root->EnumChildren(GZIID_cIGZWin, IdCollectManyCtx::Callback, &ctx);

		if (gIdWalkChecked >= kIdWalkChecks) { return; }
		for (int k = 0; k < n; k++)
		{
			cIGZWin* single[4] = {};
			int nSingle = 0;
			IdCollectCtx one = { ids[k], single, 4, &nSingle, 0 };
			root->EnumChildren(GZIID_cIGZWin, IdCollectCtx::Callback, &one);
			gIdWalkIds++;
			if (nSingle > 0) { gIdWalkHits++; }
			bool same = (nSingle == counts[k]);
			for (int i = 0; same && i < nSingle; i++)
			{
				same = (single[i] == out[k][i]);
			}
			if (!same)
			{
				NoteIdWalkDisagrees(ids[k], root, "collect",
					counts[k] ? out[k][0] : nullptr, nSingle ? single[0] : nullptr);
				counts[k] = nSingle;
				for (int i = 0; i < 4; i++) { out[k][i] = single[i]; }
			}
		}
		NoteIdWalkChecked();
	}
	// ---- end BATCHED ID LOOKUPS (tools/dev/idwalk tests this block) --------
}

// ScaleGodFlyouts's two names from the block above.
using UiSpikeInternal::IdBatch;
using UiSpikeInternal::SelfLookup;

namespace UiSpikeInternal
{
	// #194: REBIRTH lines logged this city (cap 8, in ScaleGodFlyouts). It
	// stood with the SHOWHOOK counters in UiSpike.cpp; Disarm resets it.
	int       gMayorRebirthLogs = 0;   // #194
}

// Absolute top-left of a window (walk GetParentWin, summing GetL/GetT).
// GetAreaAbsolute() is avoided (the overload pair crashes, per project
// notes); GetParentWin + GetL/GetT are all safe calls. Capped for safety.
static void AbsoluteTopLeft(cIGZWin* win, int32_t& outL, int32_t& outT)
{
	outL = 0;
	outT = 0;
	int guard = 0;
	for (cIGZWin* w = win; w != nullptr && guard < 32; w = w->GetParentWin(), ++guard)
	{
		outL += w->GetL();
		outT += w->GetT();
	}
}

// God-mode tool flyouts (terraform/terrain-fx/disaster/day-night). VERIFIED
// 2026-07-23: a size-only scale does NOT work - the game positions each
// flyout ONCE at the STOCK spawn-button spot and never re-tracks the scaled
// button, so the flyout lands at the old small-toolbar location. FIX (the
// plan's fallback): DOCK each flyout by scaling it ABOUT THE TOOLBAR'S LIVE
// bottom-left corner. The toolbar (0xC991EDA8) is scaled first by the panel
// loop; we read its live corner and map each flyout's stock offset from the
// STOCK corner (left 5, bottom frameH-238; constant across resolutions) to
// live, scaled by f. This transforms the whole god-tool cluster as a unit,
// preserving each flyout's proportional offset. Two of four flyouts are
// NESTED so they and the toolbar are found by id RECURSIVELY; absolute
// positions via AbsoluteTopLeft. Idempotent: skip if already at scaled size.
void UiSpike::ScaleGodFlyouts(cIGZWin* pView, float f)
{
	if (!pView)
	{
		return;
	}
	// v2.24.0 tier math: mirror the tier factor for the namespace-scope draw
	// hooks BEFORE anything below can install one (settings is invisible to
	// them; see gTierF).
	gTierF = f;
	// v2.36.1: remember the view so the flyout-OPEN hook can run this very
	// pass at the moment a flyout is built, instead of up to a tick later.
	lastView = pView;
	VisTraceTick();         // v2.36.8: inert unless [Probe] VisTrace=1
	// #137: run the panel docks on the TICK, not only from ScaleAllPanels /
	// ScalePanelsUnder / the show hook. MEASURED: those three fire on scale and
	// open events only, so a panel that becomes visible between them paints
	// undocked until the player touches something - the log showed the Graphs
	// band painting for 1.9s before the dock reached it, then snapping. The
	// function is idempotent (it compares against the target and writes nothing
	// when already seated), which is exactly why the author noted it costs "a
	// compare per entry" at tick rate. Belt and braces with the anchor-lifetime
	// fix above: that makes the dock POSSIBLE at birth, this makes it PROMPT.
	ApplyPanelDocks(pView, f);
	// FLASH GUARD bootstrap: patch the KNOWN disaster classes up front so even
	// the first-ever open never shows a stock frame; other flyout classes are
	// patched on discovery in the dock loops below. The ready set is STICKY
	// PER CITY (see the NOTE below): it is NOT rebuilt per sweep, and it is
	// cleared only in Disarm at city shutdown (v2.23.3).
	static bool fgBoot = false;
	if (!fgBoot)
	{
		fgBoot = true;
		PatchFlashGuardClass(reinterpret_cast<void**>(0x00AB6AA8)); // container
		PatchFlashGuardClass(reinterpret_cast<void**>(0x00AB6D88)); // strip
	}
	// NOTE (v2.11.27): the ready set is STICKY - do NOT clear it per sweep.
	// v2.11.26 cleared it here and re-added after scaling, so every frame
	// BETWEEN sweeps saw an unready window and got suppressed; the fail-open
	// then let the stock/garbled frame through anyway. A window scaled once
	// stays ready (the game keeps our geometry while the flyout lives).
	// LIVE-TUNE (v2.10): re-read disaster ring offsets from the ini every ~20
	// sweeps so positions dial in WITHOUT a rebuild. Edit [Disaster] RingDX /
	// RingDY / DockX in Documents\SimCity 4\Plugins\SC4UIScale.ini; the open
	// flyout updates within a second.
	//
	// v2.69.0 SHIPPING COST: this block is 48 GetPrivateProfileStringA calls.
	// Polled every 20 sweeps at ~60 Hz that is ~144 ini reads per second, for
	// a lever only WE use while dialing a fix in. It now runs ONCE at startup
	// (so a user's ini overrides still take effect exactly as before) and keeps
	// polling only when [UiSpike] LiveTune=1. Default off: read once, then
	// never again. Turning it on restores the old behaviour verbatim.
	// (Audit B8, 2026-09-25: the reads go through IniCache, so the whole
	// block is answered from one parse of the file, re-read only when the
	// file changes - a LiveTune edit is still seen on the next poll.)
	{
		static int s_poll = 0;
		static bool s_readOnce = false;
		static int s_liveTune = -1;   // -1 = not yet resolved
		const bool firstPass = !s_readOnce;
		if (firstPass || (s_liveTune > 0 && ++s_poll >= 20))
		{
			s_poll = 0;
			s_readOnce = true;
			const char* kIni = LiveTuneIniPath();
			char b[32];
			if (s_liveTune < 0)
			{
				IniCache::ReadStringA("UiSpike", "LiveTune", "", b, sizeof(b), kIni);
				s_liveTune = b[0] ? atoi(b) : 0;
			}
			// One table instead of 53 copies of read + atoi (audit B9). A key
			// overrides its global only when it is present in the ini.
			struct LiveKey { const char* section; const char* key; int* target; };
			static const LiveKey kLiveKeys[] = {
				// BufDump=N writes N container-buffer dumps beside the DLL for
				// offline pixel verification (render_disbuf.py).
				{ "Disaster", "BufDump", &gDisBufDump },
				{ "Disaster", "DockX", &gRingDockX },
				{ "Disaster", "DockY", &gRingDockY },
				// v4.0.14: initial scroll (first-visible item) for the strip.
				{ "Disaster", "InitScroll", &gDisInitScroll },
				// BarDX/BarW stay: the SUB-FLYOUT family still consumes them
				// (DrawBarScaled). Deleted [Disaster] keys: REGRESSION.md [CC-17].
				{ "Disaster", "BarDX", &gBarDX },
				// v2.39.0 task #5: born-at-Place size for the first-level flyout.
				// Live so a bad size can be switched off mid-session without a
				// rebuild, and WITHOUT touching the sub-flyout's own lever.
				{ "Disaster", "BornScale", &gDisBornScaleOn },
				{ "Disaster", "BornDock", &gDisBornDockOn },
				{ "Disaster", "BornMetrics", &gDisBornMetricsOn },
				{ "Disaster", "StripDump", &gStripDump },
				{ "Disaster", "StripHitW", &gStripHitW },
				{ "Disaster", "ClickHook", &gClickHook },
				{ "Disaster", "SelDL", &gSelDL },
				{ "Disaster", "SelDR", &gSelDR },
				{ "Disaster", "SelForce", &gSelForce },
				{ "Disaster", "ClaimScale", &gClaimScale },
				{ "Disaster", "FlashGuard", &gFlashGuard },
				// [Probe]: aim the DPROBE geometry probe at whatever menu is under
				// investigation (Mayor mode opens outside the god column).
				{ "Probe", "Enabled", &gProbeOn },
				{ "Probe", "BandL", &gProbeL },
				{ "Probe", "BandR", &gProbeR },
				{ "Probe", "BandT", &gProbeT },
				{ "Probe", "BandB", &gProbeB },
				{ "Probe", "Max", &gProbeMax },
				{ "Probe", "VisTrace", &gVisTrace },
				{ "Probe", "EdgeBlt", &gEdgeBltLog },   // = how many lines to log
				{ "Probe", "AdvisorShot", &gAdvisorShot },
				{ "Probe", "DrawProbe", &gDrawProbe },
				// #162: how many thin-dst blits to log (armed below the table).
				{ "Probe", "ThinBlt", &gThinBlt },
				// [Probe] IconProbe (task #149): class census of everything
				// visible, so a menu's item classes appear as NEW lines the
				// moment that menu opens. Read-only. Default OFF.
				{ "Probe", "IconProbe", &gIconProbe },
				// [Probe] SmallWin (#188): NAME the small floating windows over
				// the 3D view - built to identify the U-Drive-It START bubbles
				// the player clicks (the #186 pin hit the DURING-mission marker;
				// the start bubbles are a different, unidentified window).
				// IconProbe cannot do this: it dedupes by CLASS and a bubble
				// sharing GZWinBMP's vtable spends its 4 example slots on dock
				// windows at load. Value = total lines to print. Default OFF.
				{ "Probe", "SmallWin", &gSmallWin },
				{ "Probe", "IconFit", &gIconFit },
				{ "Probe", "IconCover", &gIconCover },
				{ "Probe", "IconCentreOff", &gIconCentreOff },
				{ "Probe", "IconHook", &gIconHook },
				{ "Probe", "IconFitLog", &gIconFitLog },
				// [Flyout]: mayor-mode flyout docking (kMayorFlyoutDock).
				{ "Flyout", "MayorDock", &gMayorDock },
				// #95: MarkerAlarm - the god-path marker-drift diagnostic (MDRIFT).
				// Diagnostic ONLY; it never moves a window. Default 1.
				{ "Flyout", "MarkerAlarm", &gMDockAlarm },
				// #198: GodMarkerFix - derive the god dock when a mod moved the
				// script's 0x0000AAAA marker. Identity on stock; default 1.
				{ "Flyout", "GodMarkerFix", &gGodMarkerFix },
				// #57: ChartScale - scale the Graphs chart's frozen interior
				// fields (legend band height, tick lengths). 1 = on (default),
				// 0 = probe only, no writes. Instant revert, no rebuild.
				{ "Flyout", "ChartScale", &gChartScale },
				// #57 PHASE 1: ChartProbe - the repaint proof. Default 0.
				// 1 = flood the plot area green and trigger the game's own
				// SetDirty, ONCE per chart object. Diagnostic only; defaces the
				// chart until set back to 0. See gChartProbe for the committed
				// discriminator.
				{ "Flyout", "ChartProbe", &gChartProbe },
				// #95: SubMath - the sub-flyout placement model (validated 32/32 vs
				// the game's own sub_79AD00). 1 = model (default), 0 = the legacy
				// fixed delta, which is wrong by up to 197px at 8 items.
				{ "Flyout", "SubMath", &gSubMath },
				{ "Flyout", "SubBltLog", &gSubBltLog },
				{ "Flyout", "RingCal", &gRingCalLog },
				{ "Flyout", "SubRingDX", &gSubRingDX },   // #134: absent = derive per tier
				{ "Flyout", "SubRingDY", &gSubRingDY },   // #134: absent = derive per tier
				{ "Flyout", "ArrowClick", &gArrowClick },
				{ "Flyout", "EmergLog", &gEmergLog },
				{ "Flyout", "SubDockDX", &gSubDockDX },
				{ "Flyout", "SubDockDY", &gSubDockDY },
				// v2.36.0 born-scale: flip either half live, no rebuild. Size and
				// dock are separable on purpose - if a menu ever lands in the
				// wrong PLACE, SubBornDock=0 isolates that from the size half.
				{ "Flyout", "SubBornScale", &gSubBornScaleOn },
				{ "Flyout", "SubBornDock", &gSubBornDockOn },
				{ "Flyout", "BornOnOpen", &gFlyoutOpenOn },
				{ "Flyout", "ScaleGodPanelABB", &gScaleAbbPanel },
				{ "Flyout", "AdvisorHeal", &gAdvisorHeal },
			};
			for (const LiveKey& k : kLiveKeys)
			{
				IniCache::ReadStringA(k.section, k.key, "", b, sizeof(b), kIni);
				if (b[0]) { *k.target = atoi(b); }
			}
			// [Disaster] BarW is the one float (v2.24.0: 1.5 is legal).
			IniCache::ReadStringA("Disaster", "BarW", "", b, sizeof(b), kIni);
			if (b[0]) gBarWiden = static_cast<float>(atof(b));
			// #162: [Probe] ThinBlt = how many thin-dst blits to log.
			//
			// ARM THE HOOK HERE, OR THE PROBE IS A GUARANTEED NULL.
			// BltClassThunk lives on the buffer class vtable and is installed
			// ONLY by EnsureBufferClassBltHook(), which is called from the
			// disaster/emergency flyout birth path and from the container's own
			// Plot detour. A session that never opens a god flyout therefore
			// never patches slot 29 - the thunk does not run, and the probe
			// writes NOTHING no matter how many blits the UI performs. Two
			// capture runs were spent on exactly that: the log came back empty,
			// and the emptiness was read as "no thin blits through this class"
			// when it actually meant "this code was never reached".
			// Installed-not-executed is bad enough (#47); this was never even
			// installed.
			if (gThinBlt > 0)
			{
				static bool s_thinArmed = false;
				if (!s_thinArmed)
				{
					s_thinArmed = true;
					EnsureBufferClassBltHook();
					Logger::Get().WriteLine(LogLevel::Info,
						"UiSpike: THINBLT armed - buffer-class slot 29 hooked "
						"(orig=%p). A run with this line but no THINBLT "
						"heartbeat means this class is not the one drawing - "
						"NOT that there were no blits.",
						gClassBltOrig);
				}
			}
			// POSITIVE CONTROL (task #149). Announce UNCONDITIONALLY on the
			// first pass so an empty ICONPROBE capture can be told apart from
			// "this build never loaded" and "the key was never read". A null
			// is not evidence until the probe is proven able to fire - the
			// first capture returned 0 lines and was uninterpretable because
			// this line did not exist.
			{
				static bool s_iconAnnounced = false;
				if (!s_iconAnnounced)
				{
					s_iconAnnounced = true;
					Logger::Get().WriteLine(LogLevel::Info,
						"UiSpike: ICONPROBE build present; gIconProbe=%d (ini %s).",
						gIconProbe, kIni);
				}
			}
		}
	}
	passScreenW = pView->GetW();
	passScreenH = pView->GetH();

	// ---- ADVISOR PORTRAIT REFRESH v2 (task #43, v2.19.5) -----------------
	// The advisor faces are LIVE 3D head renders. v2.19.4's same-tick
	// Hide+Show of the strip did NOT re-frame them (ADVHEAL fired, faces
	// stayed quarter-zoomed): the advisor system re-inits on its OWN view
	// switches, not window visibility. The head binder (exe 0x41DE20)
	// creates each head object ONCE per slot ("cmp [edi],0; jne" = reuse
	// path on later entries); the creation-time framing is stale 1x, and
	// only entering a briefing and returning re-frames. So reproduce the
	// USER'S PROVEN workaround with real synthesized clicks (the ArrowClick
	// input style): on the strip's first scaled visible sighting, click
	// face button 1 (City Planner); on a later sweep with the briefing
	// visible, click its "Return to Advisors Panel" button. One-shot per
	// strip window (re-arms on city reload); [Flyout] AdvisorHeal=0 off.
	// Cost: the briefing flashes for ~1 sweep tick, once per city load.
	if (gAdvisorHeal)
	{
		// healDoneStrip / healPhase live at namespace scope (v2.23.3):
		// Disarm resets them so city 2's strip is healed even if it reuses
		// city 1's freed address.
		cIGZWin* strip = pView->GetChildWindowFromIDRecursive(0x6A15C767);
		if (strip && static_cast<void*>(strip) != healDoneStrip
			&& strip->GetW() > 1000)
		{
			if (healPhase == 0)
			{
				if (strip->IsVisible())
				{
					cIGZWin* face = strip->GetChildWindowFromID(0xCA15C7CF);
					HWND hwnd = GetActiveWindow();
					if (face && hwnd)
					{
						int32_t fl = 0, ft = 0;
						AbsoluteTopLeft(face, fl, ft);
						const int32_t cx = fl + face->GetW() / 2;
						const int32_t cy = ft + face->GetH() / 2;
						POINT pt = { cx, cy };
						ClientToScreen(hwnd, &pt);
						SetCursorPos(pt.x, pt.y);
						const LPARAM lp = MAKELPARAM(cx, cy);
						PostMessageW(hwnd, WM_LBUTTONDOWN, MK_LBUTTON, lp);
						PostMessageW(hwnd, WM_LBUTTONUP, 0, lp);
						healPhase = 1;
						Logger::Get().WriteLine(LogLevel::Info,
							"UiSpike: ADVHEAL2 face click at (%d,%d).", cx, cy);
					}
				}
			}
			else
			{
				cIGZWin* brief = pView->GetChildWindowFromIDRecursive(0xAA15EF06);
				if (brief && brief->IsVisible())
				{
					cIGZWin* back = brief->GetChildWindowFromID(0x8A15EFE6);
					HWND hwnd = GetActiveWindow();
					if (back && hwnd)
					{
						int32_t bl = 0, bt = 0;
						AbsoluteTopLeft(back, bl, bt);
						const int32_t cx = bl + back->GetW() / 2;
						const int32_t cy = bt + back->GetH() / 2;
						POINT pt = { cx, cy };
						ClientToScreen(hwnd, &pt);
						SetCursorPos(pt.x, pt.y);
						const LPARAM lp = MAKELPARAM(cx, cy);
						PostMessageW(hwnd, WM_LBUTTONDOWN, MK_LBUTTON, lp);
						PostMessageW(hwnd, WM_LBUTTONUP, 0, lp);
						healDoneStrip = static_cast<void*>(strip);
						healPhase = 0;
						Logger::Get().WriteLine(LogLevel::Info,
							"UiSpike: ADVHEAL2 back click at (%d,%d) - heal complete.", cx, cy);
					}
				}
				else if (strip->IsVisible())
				{
					// Briefing never appeared (click swallowed) - re-arm.
					healPhase = 0;
				}
			}
		}
	}

	// ---- MPROBE (task #41, v2.17.5): change-triggered probe of the MAIN
	// WINDOW's DIRECT children. The tooltip window does NOT live under the 3D
	// view (a whole-frame DPROBE band caught nothing at a visible tooltip's
	// position), so it parents to the root. Diffs pos/size/vis per pointer;
	// the transient tooltip pops as NEW / vis-change, with its class vtable
	// logged so the fix's hook point is decided from data. [Probe] Enabled.
	if (gProbeOn)
	{
		struct MGeom { int32_t l, t, w, h; int vis; };
		static std::map<void*, MGeom> mPrev;
		// #92 law: pointer-keyed static, cleared on the city epoch. See the
		// matching note on prevGeom below.
		static int mPrevEpoch = -1;
		if (mPrevEpoch != gGaugeEpoch) { mPrev.clear(); mPrevEpoch = gGaugeEpoch; }
		cIGZWin* root = pView;
		for (int up = 0; up < 12; up++)
		{
			cIGZWin* p = root->GetParentWin();
			if (!p) { break; }
			root = p;
		}
		ChildSnapshot mk = {};
		root->EnumChildren(GZIID_cIGZWin, ChildSnapshot::Callback, &mk);
		int mlogged = 0;
		for (int mi = 0; mi < mk.count; mi++)
		{
			cIGZWin* mw = mk.wins[mi];
			if (!mw) { continue; }
			MGeom now = { mw->GetL(), mw->GetT(), mw->GetW(), mw->GetH(),
				mw->IsVisible() ? 1 : 0 };
			void* key = static_cast<void*>(mw);
			std::map<void*, MGeom>::iterator it = mPrev.find(key);
			const bool isNew = (it == mPrev.end());
			const bool chg = isNew || it->second.l != now.l
				|| it->second.t != now.t || it->second.w != now.w
				|| it->second.h != now.h || it->second.vis != now.vis;
			if (chg && mlogged < 12)
			{
				mlogged++;
				Logger::Get().WriteLine(LogLevel::Debug,
					"UiSpike: MPROBE id=0x%08X abs(%d,%d) %dx%d vis=%d vt=%p%s",
					mw->GetID(), now.l, now.t, now.w, now.h, now.vis,
					*reinterpret_cast<void**>(mw), isNew ? " NEW" : "");
			}
			mPrev[key] = now;
			// The TIP LAYER (found by this probe 2026-07-29: full-screen
			// overlay, class 0x00AB6770, toggles visible per tooltip). The tip
			// BOX is one of ITS descendants - walk the subtree while visible
			// and log every window with geometry + class (TPROBE).
			if (mw->GetID() == 0x2AAB8CC1 && now.vis == 1)
			{
				struct TFrame { cIGZWin* win; int depth; int32_t ax, ay; };
				TFrame tstack[64];
				int tsp = 0;
				TFrame tf0 = { mw, 0, 0, 0 };
				tstack[tsp++] = tf0;
				int tlogged = 0;
				while (tsp > 0 && tlogged < 16)
				{
					TFrame tf = tstack[--tsp];
					if (!tf.win || tf.depth > 6) { continue; }
					if (tf.depth > 0)
					{
						tlogged++;
						Logger::Get().WriteLine(LogLevel::Debug,
							"UiSpike: TPROBE d%d id=0x%08X abs(%d,%d) %dx%d vis=%d vt=%p",
							tf.depth, tf.win->GetID(),
							tf.ax + tf.win->GetL(), tf.ay + tf.win->GetT(),
							tf.win->GetW(), tf.win->GetH(),
							tf.win->IsVisible() ? 1 : 0,
							*reinterpret_cast<void**>(tf.win));
					}
					ChildSnapshot tk = {};
					tf.win->EnumChildren(GZIID_cIGZWin,
						ChildSnapshot::Callback, &tk);
					for (int ti = 0; ti < tk.count && tsp < 60; ti++)
					{
						TFrame nf = { tk.wins[ti], tf.depth + 1,
							tf.ax + tf.win->GetL(), tf.ay + tf.win->GetT() };
						tstack[tsp++] = nf;
					}
				}
			}
		}
	}

	// ---- ICONPROBE (task #149, 2026-08-14): WHICH CLASS DRAWS A MENU ITEM
	// ICON. A custom lot's icon (Lighted Palm Plaza, 176x44 = four 44x44
	// states) draws 44x44 in the TOP-LEFT of its 132px cell at 3x - the
	// classic "the draw follows the SOURCE, the window rect is never read"
	// shape that BmpCtxBltThunk already cures for GZWinBMP (vt 0x00ADF6A0).
	// But a FOUR-STATE strip implies a BUTTON, and buttons blit through a
	// different path, so the hook point is UNDECIDED and must not be
	// guessed: the six failed Day/Night fixes were every one of them edits
	// to code that provably never ran for those buttons.
	//
	// WHY A CLASS CENSUS AND NOT A GEOMETRY PROBE: the window is correctly
	// sized - only the blit inside it is small - so no rect test can find
	// it. This logs each DISTINCT vtable once per city epoch with up to 4
	// example windows, so opening a menu makes that menu's classes appear
	// as new lines. It draws nothing and moves nothing.
	//
	// Arm with [Probe] IconProbe=1 in the dev ini. Default OFF.
	// #188 SMALLWIN: every ~2s, print every VISIBLE small (<=80px both axes)
	// child of the 3D VIEW - id, class vtable, absolute rect. The U-Drive-It
	// START bubbles parent to the VIEW, not to this function's pView param
	// (the caller passes the panel ROOT - the first cut enumerated big panels
	// and returned a structural null, the instrument-on-the-wrong-CHANNEL
	// class). Host = the tracked lastView member. Dedup by window pointer per
	// city epoch so each distinct small window prints exactly once; the ini
	// value caps distinct windows. One ARMED line per epoch is the positive
	// control (THINBLT's own two-burned-launches lesson).
	if (gSmallWin > 0)
	{
		static std::set<void*> swSeen;
		static int swEpoch = -1;
		static unsigned swTick = 0;
		cIGZWin* swHost = lastView;
		if (swHost)
		{
			if (swEpoch != gGaugeEpoch)
			{
				swSeen.clear();
				swEpoch = gGaugeEpoch;
				Logger::Get().WriteLine(LogLevel::Info,
					"UiSpike: SMALLWIN armed - censusing <=80px children of "
					"view %p every ~2s, %d distinct max (#188). No SMALLWIN "
					"lines after this + bubbles on screen = they are NOT "
					"view children (renderer sprites or a deeper subtree).",
					(void*)swHost, gSmallWin);
			}
			if ((++swTick % 125u) == 0
				&& static_cast<int>(swSeen.size()) < 200)
			{
				// FINAL FORM (v4, the clean-verdict pass). History: d1 null
				// (armed); d2 found only PANEL FURNITURE and its 24-cap
				// truncated. This pass excludes the known panel/dock subtrees
				// outright, walks to depth 3 of what remains, and caps at 200
				// - so a null here with the armed line present is the #133
				// impossibility verdict: the start bubbles are RENDERER
				// sprites, unreachable from the window tree.
				static const uint32_t kSwSkip[] = {
					0x6A61E29F,   // dock
					0x6A15C767,   // advisors console strip
					0xCA2AEDC0,   // news ticker
					0xAA231508,   // news reader
					0xAA15EF06,   // briefing compact
					0x2A1D96B1,   // briefing expanded
					0xAA3AC002, 0xAA3AC000,   // budget compact bars
					0xE9889775,   // status HUD
					0xC98F49F1,   // city panel variant
				};
				struct SwFrame { cIGZWin* win; int depth; uint32_t parent; };
				SwFrame stack[192];
				int sp = 0;
				SwFrame f0 = { swHost, 0, 0 };
				stack[sp++] = f0;
				while (sp > 0 && static_cast<int>(swSeen.size()) < 200)
				{
					SwFrame fr = stack[--sp];
					if (!fr.win || fr.depth > 3) { continue; }
					bool skip = false;
					const uint32_t fid = fr.win->GetID();
					for (size_t k = 0;
						k < sizeof(kSwSkip) / sizeof(kSwSkip[0]); k++)
					{
						if (fid == kSwSkip[k]) { skip = true; break; }
					}
					if (skip) { continue; }
					if (fr.depth > 0 && fr.win->IsVisible()
						&& !swSeen.count(fr.win))
					{
						const int32_t ww = fr.win->GetW();
						const int32_t wh = fr.win->GetH();
						if (ww > 0 && wh > 0 && ww <= 80 && wh <= 80)
						{
							int32_t al = 0, at = 0;
							AbsoluteTopLeft(fr.win, al, at);
							swSeen.insert(fr.win);
							Logger::Get().WriteLine(LogLevel::Info,
								"UiSpike: SMALLWIN d%d id=0x%08X (under "
								"0x%08X) vt=%p abs(%d,%d) %dx%d (#188)",
								fr.depth, fid, fr.parent,
								*reinterpret_cast<void**>(fr.win),
								al, at, ww, wh);
						}
					}
					if (fr.depth < 3 && sp < 160)
					{
						ChildSnapshot ck = {};
						fr.win->EnumChildren(GZIID_cIGZWin,
							ChildSnapshot::Callback, &ck);
						for (int i = 0; i < ck.count && sp < 190; i++)
						{
							if (!ck.wins[i]) { continue; }
							SwFrame nf = { ck.wins[i], fr.depth + 1, fid };
							stack[sp++] = nf;
						}
					}
				}
			}
		}
	}

	if (gIconProbe)
	{
		struct VtSeen { int examples; };
		static std::map<void*, VtSeen> vtSeen;
		// #92 law: pointer/class-keyed static, cleared on the city epoch.
		static int vtEpoch = -1;
		if (vtEpoch != gGaugeEpoch) { vtSeen.clear(); vtEpoch = gGaugeEpoch; }

		cIGZWin* iroot = pView;
		for (int up = 0; up < 12; up++)
		{
			cIGZWin* p = iroot->GetParentWin();
			if (!p) { break; }
			iroot = p;
		}

		struct IFrame { cIGZWin* win; int depth; uint32_t parentId; };
		IFrame istack[256];
		int isp = 0;
		IFrame if0 = { iroot, 0, 0 };
		istack[isp++] = if0;
		int inewClasses = 0;
		int iexamples = 0;
		while (isp > 0 && inewClasses < 12 && iexamples < 48)
		{
			IFrame fr = istack[--isp];
			if (!fr.win || fr.depth > 10) { continue; }

			// COLUMN DUMP (task #149). The menu column is drawn by a PLUGIN
			// DLL class, and the vtable dedupe above HIDES ITS CHILDREN - the
			// item buttons, which are what actually blits the icon. Dump that
			// one subtree verbatim, no dedupe, once per city epoch.
			if (gIconHook && fr.win->GetID() == 0x8A2CAD8B)
			{
				void** vt = *reinterpret_cast<void***>(fr.win);
				if (vt && vt != gIconVtCopy)
				{
					// Copy the class vtable, patch ONE slot in the copy, then point
					// this instance at it. The shared class table is never written.
					for (int vi = 0; vi < 160; vi++) { gIconVtCopy[vi] = vt[vi]; }
					// ICONVT (task #149): NAME THE PAINT SLOT INSTEAD OF GUESSING IT.
					// Slot 87 (GZPaint) installed cleanly and fired ZERO times, so this
					// class draws through something else. The discriminator is free:
					// the GAME's own methods live at 0x00Axxxxx, so any slot pointing
					// into the DLL's range is a slot this class OVERRIDES - and the
					// draw entry must be one of those. Dumping them turns an unbounded
					// guess into a short ranked list, in ONE launch.
					// The DLL base MOVES between runs (0x6E247500 then 0x6E2474F8), so
					// the test is 'not the game's range', never a hard-coded base.
					{
						char ov[512];
						int op = 0;
						int nOver = 0;
						for (int vi = 0; vi < 160; vi++)
						{
							const uintptr_t a = reinterpret_cast<uintptr_t>(vt[vi]);
							if (a == 0) { continue; }
							// game code sits below 0x01000000; anything above is the DLL
							if (a < 0x01000000) { continue; }
							nOver++;
							if (op < 460)
							{
								op += sprintf_s(ov + op, sizeof(ov) - op, "%d ", vi);
							}
						}
						ov[op] = '\0';
						Logger::Get().WriteLine(LogLevel::Info,
							"UiSpike: ICONVT column class overrides %d of 160 slots: %s",
							nOver, ov);
						for (int vi = 80; vi < 100; vi++)
						{
							Logger::Get().WriteLine(LogLevel::Info,
								"UiSpike: ICONVT   slot %d = %p%s",
								vi, vt[vi],
								(reinterpret_cast<uintptr_t>(vt[vi]) >= 0x01000000)
									? " <- DLL override" : "");
						}
					}
					gIconPaintOrig = vt[87];
					gIconVtCopy[87] = reinterpret_cast<void*>(&IconColPaintThunk);
					*reinterpret_cast<void***>(fr.win) = gIconVtCopy;
					// ICONKICK: #47 LESSON - INSTALLING THE HOOK IS ONLY HALF OF IT,
					// THE ENGINE MUST CALL IT. Slot 87 IS a DLL override here, so the
					// slot is right, yet it fired zero times: the menu had already
					// painted before our sweep installed the thunk, and nothing asked
					// it to repaint. Kick it once, at install, exactly as the gauge and
					// BMP leaf-kicks do.
					fr.win->InvalidateSelfAndParents();
					Logger::Get().WriteLine(LogLevel::Info,
						"UiSpike: ICONHOOK installed on column 0x%08X %dx%d "
						"(class vt=%p, slot87 orig=%p). If no ICONHOOK paint line "
						"follows, this class does not paint through slot 87.",
						fr.win->GetID(), fr.win->GetW(), fr.win->GetH(),
						(void*)vt, gIconPaintOrig);
				}
			}

			if (fr.win->GetID() == 0x8A2CAD8B)
			{
				static int s_colEpoch = -1;
				if (s_colEpoch != gGaugeEpoch)
				{
					s_colEpoch = gGaugeEpoch;
					ChildSnapshot ck = {};
					fr.win->EnumChildren(GZIID_cIGZWin, ChildSnapshot::Callback, &ck);
					Logger::Get().WriteLine(LogLevel::Info,
						"UiSpike: ICONCOL column 0x%08X %dx%d has %d direct children",
						fr.win->GetID(), fr.win->GetW(), fr.win->GetH(), ck.count);
					for (int ci = 0; ci < ck.count && ci < 20; ci++)
					{
						cIGZWin* cw = ck.wins[ci];
						if (!cw) { continue; }
						ChildSnapshot gk = {};
						cw->EnumChildren(GZIID_cIGZWin, ChildSnapshot::Callback, &gk);
						int32_t cl = 0, ct = 0;
						AbsoluteTopLeft(cw, cl, ct);
						Logger::Get().WriteLine(LogLevel::Info,
							"UiSpike: ICONCOL   child#%d id=0x%08X abs(%d,%d) %dx%d "
							"vis=%d vt=%p grandchildren=%d",
							ci, cw->GetID(), cl, ct, cw->GetW(), cw->GetH(),
							cw->IsVisible() ? 1 : 0, *reinterpret_cast<void**>(cw),
							gk.count);
					}
				}
			}

			ChildSnapshot ik = {};
			fr.win->EnumChildren(GZIID_cIGZWin, ChildSnapshot::Callback, &ik);

			const int32_t iw = fr.win->GetW();
			const int32_t ih = fr.win->GetH();
			// No leaf test: a menu item may carry a text child, and the
			// vtable dedupe below is what bounds the volume, not the shape.
			if (fr.win->IsVisible() && iw >= 16 && ih >= 16)
			{
				void* vt = *reinterpret_cast<void**>(fr.win);
				std::map<void*, VtSeen>::iterator vit = vtSeen.find(vt);
				if (vit == vtSeen.end())
				{
					VtSeen fresh = { 0 };
					vtSeen[vt] = fresh;
					vit = vtSeen.find(vt);
					inewClasses++;
					Logger::Get().WriteLine(LogLevel::Info,
						"UiSpike: ICONPROBE NEW CLASS vt=%p (id=0x%08X %dx%d d%d "
						"children=%d)",
						vt, fr.win->GetID(), iw, ih, fr.depth, ik.count);
				}
				if (vit->second.examples < 4)
				{
					vit->second.examples++;
					iexamples++;
					int32_t al = 0, at = 0;
					AbsoluteTopLeft(fr.win, al, at);
					Logger::Get().WriteLine(LogLevel::Info,
						"UiSpike: ICONPROBE   vt=%p id=0x%08X abs(%d,%d) %dx%d d%d "
						"parent=0x%08X children=%d",
						vt, fr.win->GetID(), al, at, iw, ih, fr.depth,
						fr.parentId, ik.count);
				}
			}

			const uint32_t myId = fr.win->GetID();
			for (int ii = 0; ii < ik.count && isp < 250; ii++)
			{
				IFrame nf = { ik.wins[ii], fr.depth + 1, myId };
				istack[isp++] = nf;
			}
		}
	}

	// ---- DPROBE: change-triggered geometry probe (Phase 1 instrument) -----
	// WHY: the only instrument was the 1-second whole-tree LiveDump, which can
	// only ever capture SETTLED states. The disaster flyout's open->settle and
	// hover transitions are instantaneous, so its three independent elements
	// (orange CIRCLE, orange BAR, disaster PICTURES - proven independent
	// because hovering moves ONLY the bar) never appeared as identifiable
	// windows, and every fix was guesswork against the one window that was
	// visible. This walks the god-flyout parent 0x9A47B417's ENTIRE subtree
	// every sweep and logs ONLY what changed since the previous sweep, making
	// those transitions observable.
	// Keyed by (id, parentId, sibling-index) so anonymous id==0 windows stay
	// individually trackable - the exact flaw that made earlier diffs discard
	// the very windows we were hunting.
	//
	// v2.69.3: the v2.69.0 `if (gProbeOn)` gate around this WALK is REVERTED
	// (found by the adversarial review, verified in source, and REACHED on this
	// very machine - the dev ini says [Probe] Enabled=0). The gate's stated
	// justification - "verified zero mutations inside the block; it is pure
	// instrument" - was FALSE, and the instrument that produced it had no
	// positive control: its regex matched Set*/GZWinMoveTo-style CALLS, and the
	// block's real mutations are neither - they are raw vtable swaps
	// (`*reinterpret_cast<void***>(w) = gVtCopy` / gVtCopy2, the DISASTER DRAW
	// HOOK installs), `gDisasterDrawTuning = 1`, and InvalidateSelfAndParents().
	// This walk IS the per-tick re-find the runtime-image lever depends on:
	// disaster-flyout windows are TRANSIENT, so their draw hooks must be
	// re-installed each sweep as instances appear. Gating it killed the
	// disaster ring/bar 2x draw fix whenever the probe was off.
	// The per-tick COST concern stays real but must be re-attacked by
	// SEPARATING hook-install from diff-logging - with an eyes-on disaster
	// adjudicator, not a text scan. The LOG lines inside remain gated on
	// gProbeOn per line, exactly as pre-v2.69.0.
	{
		// Key by the window POINTER: it is genuinely unique per window. Keying
		// by (id,parentId,index) collapsed together every anonymous window
		// whose parent was also anonymous (id 0 / par 0), so unrelated windows
		// appeared as one entry "changing" hundreds of times - useless.
		struct PGeom { int32_t l, t, w, h; int vis; };
		static std::map<void*, PGeom> prevGeom;
		// #92 law, applied to the probes: a pointer-keyed static outlives the
		// windows it keys on. At city teardown every pointer in here dangles,
		// and a second city that lands on a reused address reads as "not new"
		// -> the probe silently reports nothing. gGaugeEpoch is the same lever
		// Disarm() already uses for the gauge latches, and it cannot get stuck.
		static int prevGeomEpoch = -1;
		if (prevGeomEpoch != gGaugeEpoch) { prevGeom.clear(); prevGeomEpoch = gGaugeEpoch; }
		// pView IS 0x9A47B417 (kGZWin_SC4View3DWin, the god-flyout parent).
		// This used to be pView->GetChildWindowFromIDRecursive(0x9A47B417): a
		// whole-view walk to get pView back (audit A1; see SelfLookup).
		cIGZWin* probeRoot = SelfLookup(pView, 0x9A47B417);
		if (probeRoot)
		{
			struct Frame { cIGZWin* win; uint32_t parentId; int index; int32_t ax, ay; int depth; };
			Frame stack[512];
			int sp = 0;
			Frame first = { probeRoot, 0u, 0, 0, 0, 0 };
			stack[sp++] = first;
			int logged = 0;
			while (sp > 0)
			{
				Frame fr = stack[--sp];
				cIGZWin* w = fr.win;
				if (!w || fr.depth > 10)
				{
					continue;
				}
				const int32_t ax = fr.ax + w->GetL();
				const int32_t ay = fr.ay + w->GetT();
				const uint32_t id = w->GetID();
				PGeom now = { ax, ay, w->GetW(), w->GetH(), w->IsVisible() ? 1 : 0 };
				void* key = static_cast<void*>(w);
				// The geometry diff feeds ONLY the gProbeOn log below; the hook
				// installs further down never read it. So with the probe off
				// the map is neither searched nor written (audit A1, 2026-09-25:
				// ~1,700 map operations per tick, in a map that also grew with
				// every transient window). The walk itself stays - it re-installs
				// the disaster draw hooks (the v2.69.3 note above).
				bool isNew = true, changed = true;
				if (gProbeOn)
				{
					std::map<void*, PGeom>::iterator it = prevGeom.find(key);
					isNew = (it == prevGeom.end());
					changed = isNew
						|| it->second.l != now.l || it->second.t != now.t
						|| it->second.w != now.w || it->second.h != now.h
						|| it->second.vis != now.vis;
				}
				// Band the probe on the area under investigation - the bottom
				// query panels animate constantly and drown the signal if the
				// whole frame is logged. Live-tunable via ini [Probe] so the
				// probe can be re-aimed at a Mayor-mode menu without a rebuild.
				const bool inBand = (now.vis == 1) && now.w > 8 && now.h > 8
					&& ax > gProbeL && ax < gProbeR && ay > gProbeT && ay < gProbeB;
				if (gProbeOn && changed && inBand && logged < gProbeMax)
				{
					logged++;
					Logger::Get().WriteLine(
						LogLevel::Debug,
						"UiSpike: DPROBE ptr%p d%d id=0x%08X par=0x%08X #%d abs(%d,%d) %dx%d vis=%d%s",
						key, fr.depth, id, fr.parentId, fr.index,
						now.l, now.t, now.w, now.h, now.vis, isNew ? " NEW" : "");
				}
				// ---- CLASS PROBE (draw-hook step 1) ----------------------
				// One-shot, for the disaster flyout container + its strip:
				// report the concrete class (vtable pointer) and which GZWin
				// interfaces it answers to. The vtable identifies the class we
				// would have to intercept GZPaint() on (cIGZWin.h:181); an
				// interface like cIGZWinGen would instead offer a cheap,
				// supported way in. This decides the hook point instead of
				// guessing at it.
				// #199 (2026-08-29): WAS an absolute-screen-Y band
				//     ax > -150 && ax < 500 && ay > 380 && ay < 1250
				// - unscaled 1x/2x-era screen literals. The disaster container is
				// bottom-anchored, so its Y rides BOTH the factor and the screen
				// height: T ~= screenH - rhu(542*f). At the 2400x1600 where v4.0.40
				// was approved it landed inside the band; at 3840x2160 x1.5 it
				// measures ay=1339 and the band REJECTED THE ONE WINDOW IT EXISTS
				// TO FIND - so slots 87..97 were never installed on it, while the
				// DCLAIM promotion in the other loop fired unopposed. [0xE0] is
				// DUAL-USE (hit-claim width AND the Plot bar width / end-cap atlas
				// cell step), so the game then painted the bar 80px at x=131 and
				// read cap cells at 94+flag*80=174 - 27px into the WRONG atlas
				// column. SC4-UI-ENGINE.md states the invariant verbatim: "promote
				// the field before installing the thunk and the game paints a
				// SECOND bar (v2.11.24)". THAT is why scrolling broke the buttons:
				// the cap cell index is the scroll-arrow enable flag.
				//
				// THRESHOLDS COME FROM CONTROLS: a gate that rejects the known-good
				// target is the wrong gate, so it is REPLACED, not re-tuned. The
				// substitute is the SAME positive identification the DCLAIM loop
				// uses and has always been safe with - a DIRECT child of the god
				// flyout parent 0x9A47B417. That is what keeps this away from the
				// MAYOR sub-flyout container, which is the same class 0x00AB6AA8
				// and (measured 194x655) passes the size and class gates too:
				// handing it gVtCopy would set gDisasterDrawTuning=1 on a mayor
				// window - the "right class, wrong window" trap this file already
				// records from the Earned Cars crash. Deleting the band outright
				// would have done exactly that.
				if (id == 0 && now.vis == 1 && now.h > 400 && now.w > 80
					&& fr.parentId == 0x9A47B417)
				{
					static std::map<void*, int> probedOnce;
					// #92 law: same epoch clear - otherwise the next city's
					// window at a recycled address is treated as already probed.
					static int probedOnceEpoch = -1;
					if (probedOnceEpoch != gGaugeEpoch)
					{
						probedOnce.clear(); probedOnceEpoch = gGaugeEpoch;
					}
					if (probedOnce.find(key) == probedOnce.end())
					{
						probedOnce[key] = 1;
						void** vt = *reinterpret_cast<void***>(w);
						Logger::Get().WriteLine(
							LogLevel::Debug,
							"UiSpike: DCLASS ptr%p %dx%d vtable=%p", key, now.w, now.h,
							static_cast<void*>(vt));
						struct IfaceProbe { const char* name; uint32_t iid; };
						const IfaceProbe kIfaces[] = {
							{ "cIGZWin",       0x22BA0121u },
							{ "cIGZWinGen",    0x5386D516u },
							{ "cIGZWinBtn",    0x00008810u },
							{ "cIGZWinText",   0x212CDC1Fu },
							{ "cIGZWinScroll", 0x61325A2Du },
							{ "cIGZWinProc",   0x22E85D8Eu },
							{ "cIGZWinCombo",  0x412CE496u },
							{ "cIGZWinSlider", 0x21325207u },
							{ "cIGZWinOptGrp", 0xA1336CC0u },
						};
						for (const IfaceProbe& ip : kIfaces)
						{
							void* out = nullptr;
							if (w->QueryInterface(ip.iid, &out) && out != nullptr)
							{
								Logger::Get().WriteLine(
									LogLevel::Debug,
									"UiSpike: DCLASS   ptr%p supports %s", key, ip.name);
								static_cast<cIGZUnknown*>(out)->Release();
							}
						}
					}

					// Install the observe-only GZPaint hook on the DISASTER
					// CONTAINER ONLY (282x678 - it paints the circle + bar;
					// the 88-wide strip is the pictures).
					// TIGHT size gate: an earlier `w > 150` test also matched
					// two unrelated generic windows (470x444, 516x504, class
					// vtable 0x00ADF6A0). Because gVtCopy is ONE shared array,
					// hooking more than one window left the earlier ones
					// pointing at a copy of a DIFFERENT class's vtable - a real
					// crash risk. One window only.
					// v2.22.3 (audit fix): the size box is NOT identification.
					// The same "right class, wrong window" trap that crashed
					// Earned Cars applies here, and this gate sits inside a
					// walk of the WHOLE view subtree - which now holds nine My
					// Sims roots, 43 dashboard variants and the static-dat
					// panels. Require the POSITIVE class match too.
					// v2.24.0 (audit A4): the size box is DERIVED from the tier
					// factor (design band 100..200 x 250..450; f=2 evaluates to
					// the old 200..400 x 500..900 exactly). At 3x the container
					// is 423x1017, which the old literals rejected - the whole
					// disaster draw/click fix was dead there. The POSITIVE class
					// check below remains the real identification (v2.22.3).
					if (now.w >= RoundHalfUp(100 * gTierF)
						&& now.w <= RoundHalfUp(200 * gTierF)
						&& now.h >= RoundHalfUp(250 * gTierF)
						&& now.h <= RoundHalfUp(450 * gTierF)
						&& *reinterpret_cast<void***>(w)
							== reinterpret_cast<void**>(0x00AB6AA8))
					{
						void** curVt = *reinterpret_cast<void***>(w);
						if (curVt != gVtCopy)
						{
							for (int vi = 0; vi < 256; vi++)
							{
								gVtCopy[vi] = curVt[vi];
							}
							for (int si = 87; si <= 97; si++)
							{
								gOrigSlot[si] = reinterpret_cast<SlotFn>(curVt[si]);
								gSlotHits[si] = 0;
							}
							gVtCopy[87] = reinterpret_cast<void*>(&SlotThunk<87>);
							gVtCopy[88] = reinterpret_cast<void*>(&SlotThunk<88>);
							gVtCopy[89] = reinterpret_cast<void*>(&SlotThunk<89>);
							gVtCopy[90] = reinterpret_cast<void*>(&SlotThunk<90>);
							gVtCopy[91] = reinterpret_cast<void*>(&SlotThunk<91>);
							gVtCopy[92] = reinterpret_cast<void*>(&SlotThunk<92>);
							gVtCopy[93] = reinterpret_cast<void*>(&SlotThunk<93>);
							gVtCopy[94] = reinterpret_cast<void*>(&SlotThunk<94>);
							gVtCopy[95] = reinterpret_cast<void*>(&SlotThunk<95>);
							gVtCopy[96] = reinterpret_cast<void*>(&SlotThunk<96>);
							gVtCopy[97] = reinterpret_cast<void*>(&SlotThunk<97>);
							*reinterpret_cast<void***>(w) = gVtCopy;
							gForceInvalidate = 20;
							// The DISASTER container is the hooked instance now,
							// so its measured ring/bar offsets apply again.
							gDisasterDrawTuning = 1;
							// Reset the position tracker so it records this open's
							// trajectory from the very first Plot frame (catching
							// the pre-jump position if the window really moves).
							gPosFrames = 0;
							gPosLogged = 0;
							gLastPosL = 0x7FFFFFFF; gLastPosT = 0;
							gLastPosW = 0; gLastPosH = 0;
							// DUMP member fields used by Plot() for drawing.
							// Plot reads [this+0xe0..0xec] as layout params.
							{
								int32_t* m = reinterpret_cast<int32_t*>(w);
								Logger::Get().WriteLine(LogLevel::Debug,
									"UiSpike: DMEM ptr%p m[0x26]=%d m[0x27]=%d "
									"m[0x36]=%d m[0x37]=%d m[0x38]=%d m[0x39]=%d "
									"m[0x3A]=%d m[0x3B]=%d m[0x3C]=%d m[0x3D]=%d "
									"m[0x46]=%d m[0x47]=%d m[0x48]=%d",
									key,
									m[0x26], m[0x27],  // 0x98, 0x9C
									m[0x36], m[0x37], m[0x38], m[0x39],  // 0xD8-0xE4
									m[0x3A], m[0x3B], m[0x3C], m[0x3D],  // 0xE8-0xF4
									m[0x46], m[0x47], m[0x48]);          // 0x118-0x120
								// (Doubling MOVED to the per-frame Plot hook, slot 88.
								// One-shot doubling here had zero visible effect —
								// the game likely recomputes these each frame. The
								// DMEM read above still captures the 1x base values.)
								(void)m;
							}
							Logger::Get().WriteLine(
								LogLevel::Debug,
								"UiSpike: DHOOK installed on ptr%p (%dx%d) origVt=%p slots87-97 orig87=%p orig88=%p",
								key, now.w, now.h, static_cast<void*>(curVt),
								reinterpret_cast<void*>(gOrigSlot[87]),
								reinterpret_cast<void*>(gOrigSlot[88]));
						}
						// SC4 windows paint into a buffer (winflag_pbuff) and
						// then just blit it, so GZPaint only runs when the
						// window is invalidated. With our dock disabled nothing
						// ever invalidates it - which is why the hook installed
						// but never fired. Force a few invalidates so we can
						// tell whether GZPaint is on this window's paint path
						// at all.
						if (gForceInvalidate > 0)
						{
							gForceInvalidate--;
							w->InvalidateSelfAndParents();
						}
					}

					// STRIP hook (88x578 - the disaster thumbnail pictures).
					// Different vtable (0x00AB6D88) so it gets its own copy.
					// v2.22.3 (audit fix): positive class match required - see
					// the note on the container hook above.
					// #199: these were UNSCALED 2x literals (the comment above says
					// "88x578" - a 2x measurement). The strip measures 66x433 at 1.5x
					// (passes by luck) and 132x866 at 3x (FAILS). With the container
					// band fixed above, this hook becomes reachable at 3x for the
					// first time and would have failed silently on its own box - the
					// fix half-applied. Derived from the same 1x base the container
					// gate uses (44x289 at 1x, DISBORN), with the same generous
					// bracket, so f=2 still admits 88x578 exactly as before.
					if (now.w >= RoundHalfUp(30 * gTierF) && now.w <= RoundHalfUp(60 * gTierF)
						&& now.h >= RoundHalfUp(200 * gTierF) && now.h <= RoundHalfUp(350 * gTierF)
						&& *reinterpret_cast<void***>(w)
							== reinterpret_cast<void**>(0x00AB6D88))
					{
						void** curVt2 = *reinterpret_cast<void***>(w);
						if (curVt2 != gVtCopy2)
						{
							for (int vi = 0; vi < 256; vi++)
							{
								gVtCopy2[vi] = curVt2[vi];
							}
							for (int si = 87; si <= 97; si++)
							{
								gOrigSlot2[si] = reinterpret_cast<SlotFn>(curVt2[si]);
								gSlotHits2[si] = 0;
							}
							gVtCopy2[87] = reinterpret_cast<void*>(&SlotThunk2<87>);
							gVtCopy2[88] = reinterpret_cast<void*>(&SlotThunk2<88>);
							gVtCopy2[89] = reinterpret_cast<void*>(&SlotThunk2<89>);
							gVtCopy2[90] = reinterpret_cast<void*>(&SlotThunk2<90>);
							gVtCopy2[91] = reinterpret_cast<void*>(&SlotThunk2<91>);
							gVtCopy2[92] = reinterpret_cast<void*>(&SlotThunk2<92>);
							gVtCopy2[93] = reinterpret_cast<void*>(&SlotThunk2<93>);
							gVtCopy2[94] = reinterpret_cast<void*>(&SlotThunk2<94>);
							gVtCopy2[95] = reinterpret_cast<void*>(&SlotThunk2<95>);
							gVtCopy2[96] = reinterpret_cast<void*>(&SlotThunk2<96>);
							gVtCopy2[97] = reinterpret_cast<void*>(&SlotThunk2<97>);
							// DVT: dump the strip's real vtable addresses (anchor on
							// slot 88 = Plot, verified) so the true GZOnMouseDownL slot
							// can be confirmed offline before we hook it.
							if (gStripDump)
							{
								for (int b = 84; b <= 140; b += 8)
									Logger::Get().WriteLine(LogLevel::Debug,
										"UiSpike: DVT s%d: %p %p %p %p %p %p %p %p", b,
										curVt2[b], curVt2[b + 1], curVt2[b + 2],
										curVt2[b + 3], curVt2[b + 4], curVt2[b + 5],
										curVt2[b + 6], curVt2[b + 7]);
							}
							// Click-path hooks on the VERIFIED 3-arg list handlers
							// (136 commit+fire, 138 pick-from-Y). Safe signatures.
							if (gClickHook)
							{
								gOrigMouse136 =
									reinterpret_cast<MouseFn>(curVt2[136]);
								gOrigMouse138 =
									reinterpret_cast<MouseFn>(curVt2[138]);
								gOrigPt121 =
									reinterpret_cast<PtInFn>(curVt2[121]);
								gOrigSlot149 =
									reinterpret_cast<PtInFn>(curVt2[149]);
								gOrigSlot62 =
									reinterpret_cast<PtInFn>(curVt2[62]);
								gVtCopy2[62] =
									reinterpret_cast<void*>(&Slot62Thunk);
								gOrigSlot59 =
									reinterpret_cast<XformFn>(curVt2[59]);
								gVtCopy2[59] =
									reinterpret_cast<void*>(&Slot59Thunk);
								gVtCopy2[136] =
									reinterpret_cast<void*>(&Mouse136Thunk);
								gVtCopy2[138] =
									reinterpret_cast<void*>(&Mouse138Thunk);
								gVtCopy2[121] =
									reinterpret_cast<void*>(&Pt121Thunk);
								gVtCopy2[149] =
									reinterpret_cast<void*>(&Slot149Thunk);
							}
							*reinterpret_cast<void***>(w) = gVtCopy2;
							Logger::Get().WriteLine(
								LogLevel::Debug,
								"UiSpike: DHOOK2 installed on ptr%p (%dx%d) origVt=%p orig88=%p",
								key, now.w, now.h, static_cast<void*>(curVt2),
								reinterpret_cast<void*>(gOrigSlot2[88]));
							// Enumerate the strip's children + rects. If the pictures
							// are child button windows at 1x positions, THEY are the
							// (un-scaled) click targets and must be resized to 2x.
							if (gStripDump)
							{
								ChildSnapshot cs = {};
								w->EnumChildren(GZIID_cIGZWin,
									ChildSnapshot::Callback, &cs);
								Logger::Get().WriteLine(LogLevel::Debug,
									"UiSpike: DKIDS strip has %d children", cs.count);
								for (int ki = 0; ki < cs.count && ki < 16; ki++)
								{
									cIGZWin* c = cs.wins[ki];
									if (!c) continue;
									Logger::Get().WriteLine(LogLevel::Debug,
										"UiSpike: DKID %d id=%08X L=%d T=%d W=%d H=%d vis=%d",
										ki, c->GetID(), c->GetL(), c->GetT(),
										c->GetW(), c->GetH(), c->IsVisible() ? 1 : 0);
								}
							}
						}
					}
				}

				if (gProbeOn) { prevGeom[key] = now; }
				// Only `count` needs clearing: the callback appends and the loop
				// below reads wins[0..count). This runs for every view window
				// every tick, so the 1 KB zero-fill was ~860 KB a tick.
				ChildSnapshot snap;
				snap.count = 0;
				w->EnumChildren(GZIID_cIGZWin, ChildSnapshot::Callback, &snap);
				for (int i = 0; i < snap.count && sp < 500; i++)
				{
					Frame ch = { snap.wins[i], id, i, ax, ay, fr.depth + 1 };
					stack[sp++] = ch;
				}
			}
		}
	}

	// TWO MODES, one god flyout at a time (user discipline 2026-07-24).
	// Baseline for every flyout is SIZE-ONLY in place (ScaleSubtree depth 0:
	// grow the root + spread children 2x WITHOUT moving the root) - the game
	// natively positions them roughly right and moving roots was what caused
	// the cross-flyout breakage. But size-only alone leaves a flyout ~one
	// button too low (the root top-left stays at its 1x spot while internals
	// grow down), so a flyout that has been dialed in gets a SMALL vertical
	// dock nudge from the scaled toolbar strip 0xC991EDA8 (whose ScaleRecord
	// preserves the stock top-left). We add flyouts to kGodFlyoutDock ONE AT
	// A TIME as each is verified. Everything else stays size-only until then.
	// Terrain-FX and Day/Night SHARE the 0xCA35CBED flyout window (proven
	// 2026-07-24 by dumping its live children). Its dock offset drives whatever
	// is showing 1:1:
	//   offY 40  -> ring btn2   (correct for terrain-fx)
	//   offY 160 -> ring btn5   (correct for day/night)
	// so the offset MUST be chosen by which tool is currently rendering through
	// it. The container swaps its child set per tool:
	//   TERRAIN-FX open -> 4-button set 0x0AA44502..05 (its sub-tools)
	//   DAY/NIGHT  open -> 3-button set 0xCA35CB74/76/78 (sun/moon/wavy)
	// Day/Night has no dock entry of its own - it rides entirely on 0xCA35CBED.
	// (0xABB26B0E was described here as "a frozen hidden template at Y1045".
	// That held only BEFORE a city is founded; in a founded city it is the live
	// god panel, and treating it as an unmovable template is what pushed the god
	// UI off the bottom of the screen. It is a god PANEL now - see kGodPanelIds.
	// Day/Night rendering is unaffected either way.) Detect DAY/NIGHT via
	// its sub-tool 0xCA35CB74 (vis=1 only when day/night is the open tool; the
	// v2.7.28 diag proved terrain-fx does NOT show it). NOT the 0xCA35CBED root,
	// which stays vis=1 for both.
	const int32_t kTerrfxOffY   = 40;   // terrain-fx showing -> its ring btn2
	const int32_t kDayNightOffY = 160;  // day/night showing  -> its ring btn5

	// Every offset here is the DESIGN CONSTANT from the clean 1:1 vanilla
	// capture (_vanilla-reference/FINDINGS.md "EXACT STOCK DIMENSIONS"),
	// computed as (flyoutStock - toolbarStock) with toolbar 0xC991EDA8 at
	// stock (5,435) - never hand-tuned:
	//   0x49923239 (11,355) -> ( 6,-80)   terraform
	//   0xCA35CBED (11,475) -> ( 6, 40)   terrain-fx
	//   0x0A78827A ( 5,495) -> ( 0, 60)   disaster
	// gateVisible: only dock while the root reports vis=1. Needed for
	// TERRAIN-FX (a closed one docked on top of day/night is what breaks it),
	// but DISASTER's root is vis=0 ALWAYS - the "flyout roots report vis=0
	// while their children draw" pattern - so gating it there silently skipped
	// the dock entirely (0 dock lines, window left at stock 74x291).
	struct GodFlyoutDock { uint32_t id; int32_t offX; int32_t offY; bool gateVisible; };
	static const GodFlyoutDock kGodFlyoutDock[] = {
		{ 0x49923239, 6, -80,         true  }, // 1 TERRAFORM  (green) - LOCKED v2.7.25
		{ 0xCA35CBED, 6, kTerrfxOffY, true  }, // 2 TERRAIN-FX (tan) - offY chosen below
		// NOTE: 0x0A78827A is NOT the disaster flyout, despite the label in
		// _vanilla-reference/FINDINGS.md. Live tree (2026-07-24): it sits at
		// (10,542) with vis=0 - a HIDDEN god sub-tool strip (its .UI script
		// I-aa53e3ea lists Obliterate/Reconcile/Disasters/Day-Night buttons).
		// Docking/scaling it changes nothing on screen. The VISIBLE disaster
		// flyout is an anonymous (id==0) child of 0x9A47B417 holding the
		// orange bar + the 88x578 thumbnail strip. Do not re-add this id.
	};

	// kMayorFlyoutDock now lives at namespace scope (see the alignment-marker
	// rule up there) because ScalePanelsUnder needs it too.

	// 0xABB26B0E is a god PANEL (kGodPanelIds, gated by gScaleAbbPanel), never
	// a size-only window: the kSizeOnlyIds list and its size-only pass were
	// removed in v2.12.1 (REGRESSION.md [CC-18]).

	cIGZWin* dnTool = pView->GetChildWindowFromIDRecursive(0xCA35CB74);
	const bool dayNightActive = (dnTool != nullptr && dnTool->IsVisible());

	// MAYOR vs GOD mode.
	//
	// REJECTED (v2.12.4-2.12.6): the mayor toolbar button's ENABLED flag. It
	// looked right in a founded city (en=1 mayor / en=0 god) but is NOT stable -
	// it read en=0 in all 99 dump samples of one session while still evaluating
	// TRUE during sweeps, so the mayor nudge fired in PRE-FOUNDING GOD MODE and
	// shifted terraform twice. A flag that flickers between the sweep and the
	// dump cannot gate anything.
	//
	// USE INSTEAD: the composite mayor HUD 0xE9889775 (Mayor Rating / RCI /
	// funds). It is shown in mayor mode and hidden in god mode, which is what
	// "mayor mode" actually means. Verified across all THREE states - the two
	// that the enabled flag conflated (pre-founding god, founded god) plus
	// mayor: vis=1 only in mayor mode.
	cIGZWin* mayorHud = pView->GetChildWindowFromIDRecursive(0xE9889775);
	const bool mayorModeActive = (mayorHud != nullptr && mayorHud->IsVisible());

	// Dock + scale the dialed-in flyouts. Needs the scaled toolbar strip as
	// the anchor; if it isn't scaled yet this cycle, dock next tick.
	cIGZWin* tb = pView->GetChildWindowFromIDRecursive(0xC991EDA8);
	if (!tb)
	{
		return;
	}
	std::map<void*, ScaleRecord>::iterator tbIt = scaleMap.find(tb);
	if (tbIt == scaleMap.end() || tbIt->second.id != tb->GetID()
		|| tb->GetW() != tbIt->second.scaledW)
	{
		return;
	}
	const int32_t tbLiveL = tb->GetL();
	const int32_t tbLiveT = tb->GetT();

	// v2.39.5 (task #80): WARM THE DISASTER DOCK CACHE FROM THE TOOLBAR, NOT
	// FROM THE OPEN FLYOUT. gDisDockL/T used to be written only inside the
	// flyout-open block below (the container loop) - a latch that can only
	// warm while the flyout is OPEN is cold on the first open by construction,
	// so SubPlaceDetour's dock-at-birth never fired on open 1 and the window
	// was born at (63,688) instead of (6,502) (measured, session 17:21
	// 2026-07-31). The target is a pure function of the already-scaled toolbar
	// (the scaleMap gate above guarantees it) and two live-tunable ini
	// offsets, so computing it every tick here is free and keeps DockX/DockY
	// live-tuning intact. The per-city reset at Disarm stays; the cache
	// re-warms on the first sweep tick after the toolbar is scaled - long
	// before a human can click the disaster button.
	gDisDockL = tbLiveL + ScaleRound(DisDockXEff(), f);
	gDisDockT = tbLiveT + ScaleRound(DisDockYEff(), f);
	gDisDockValid = true;

	// CALIBRATION (disaster dock): log the absolute CENTRE of god buttons 2 and
	// 4 so a single Disaster screenshot pins the dock. The container is static
	// at abs(126,518) (DPOS), moving it moves the ring 1:1, so once we know
	// button4_centre and (from the screenshot) the ring centre, the correction
	// is exact: container_target = current + (button4_centre - ring_centre).
	// Buttons: btn2 0x8A32DDDB (terrain-fx spawn, docks correctly) and
	// btn4 0x69B9324A (disaster spawn). Log a few frames then go quiet.
	{
		static int calibLogged = 0;
		if (calibLogged < 3)
		{
			cIGZWin* b2 = pView->GetChildWindowFromIDRecursive(0x8A32DDDB);
			cIGZWin* b4 = pView->GetChildWindowFromIDRecursive(0x69B9324A);
			int32_t tbAL = 0, tbAT = 0;
			AbsoluteTopLeft(tb, tbAL, tbAT);
			if (b2 != nullptr && b4 != nullptr)
			{
				calibLogged++;
				int32_t b2L = 0, b2T = 0, b4L = 0, b4T = 0;
				AbsoluteTopLeft(b2, b2L, b2T);
				AbsoluteTopLeft(b4, b4L, b4T);
				Logger::Get().WriteLine(LogLevel::Debug,
					"UiSpike: DCAL toolbar.abs(%d,%d) %dx%d  btn2.ctr(%d,%d) %dx%d  "
					"btn4.ctr(%d,%d) %dx%d",
					tbAL, tbAT, tb->GetW(), tb->GetH(),
					b2L + b2->GetW() / 2, b2T + b2->GetH() / 2, b2->GetW(), b2->GetH(),
					b4L + b4->GetW() / 2, b4T + b4->GetH() / 2, b4->GetW(), b4->GetH());
			}
		}
	}

	// ---- SHARED SUB-FLYOUT CONTAINER (v2.13.3) ---------------------------
	// Size it, do NOT reposition it (SubDock=0), and log the relationship to
	// whichever flyout is currently open so the real placement rule can be
	// derived from data rather than guessed. See kSubFlyoutIds for why a
	// hardcoded per-tool anchor would be wrong.
	// v2.36.0: adopt anything the born-scale detour already scaled BEFORE we
	// walk, so Classify() sees AlreadyScaled instead of Fresh. Without this a
	// born-scaled container is a pointer the sweep has never met and would be
	// scaled a SECOND time (129 -> 258 -> 516).
	DrainBornScaleRecords();

	for (uint32_t subId : kSubFlyoutIds)
	{
		cIGZWin* sub = pView->GetChildWindowFromIDRecursive(subId);
		if (!sub || sub->GetW() <= 0 || sub->GetH() <= 0 || !sub->IsVisible())
		{
			// menu closed: invalidate the back-arrow click zone so stray
			// clicks at the old rect are never forwarded
			gSubArrowAbs[2] = -1;
			gSubBtnCX = -1;
			continue;
		}

		int n = 0;
		ScaleSubtree(sub, f, 0, &n, false);
		if (n > 0)
		{
			sub->InvalidateSelfAndParents();
		}

		// ---- KNOWN-MENU GATE (v2.22.1) — THE CRASH FIX --------------------
		// 0x8A6E61E0 is SHARED by every second-level menu, and so is its strip
		// child 0x8A2CAD8B (archived logs show the SAME strip id at heights
		// 284/382/578/774 = different item counts per menu). The disaster-
		// derived draw hooks below (buffer force-recreate via SlotThunk,
		// strip item-field doubling, [0xe0] claim doubling) were validated
		// ONLY on the five menus in kParents. When the player opened
		// U-Drive-It -> Earned Cars the same hooks installed on THAT strip
		// (log: "SUBHOOK strip 0x8A2CAD8B 88x774 ... item fields x2") and the
		// game died - a foreign layout getting a force-recreated buffer plus
		// doubled item pitch.
		// FIX = positive identification (law 3): install the hooks only while
		// one of the KNOWN parent menus is actually open. An unknown menu's
		// sub-flyout keeps the plain subtree scale above and is left alone -
		// it may look stock-ish, but it cannot crash. Add a menu to kParents
		// (and verify its strip) to opt it in.
		bool knownMenuOpen = false;
		{
			// kSubFlyoutParents: the v2.25.3 column opt-in and why the gate is
			// an id list are recorded at the table.
			knownMenuOpen = KnownSubFlyoutParentOpen(pView);
			if (!knownMenuOpen)
			{
				static int skipLog = 0;
				if (skipLog < 10)
				{
					skipLog++;
					Logger::Get().WriteLine(LogLevel::Info,
						"UiSpike: SUBSKIP container 0x%08X %dx%d - no known parent "
						"menu open; disaster draw hooks NOT installed (crash guard)",
						subId, sub->GetW(), sub->GetH());
				}
			}
		}

		// ---- DOCK THE WHOLE ASSEMBLY (v2.15.3) ---------------------------
		// Identify the SELECTED parent button by matching the game's own
		// placement rule, then move the container to the derived target. Done
		// by ABSOLUTE target (not a relative nudge) so it is idempotent - the
		// sweep runs 4x/sec and a relative move would walk the window away.
		// Matching accepts EITHER the native position or the already-docked one,
		// so a second pass recognises its own work and does nothing.
		if (pView) { gLastViewH = pView->GetH(); }   // #95: for the born path
		const int32_t subDockDX = SubDockDXEff();   // v2.24.0: derived (audit B6)
		const int32_t subDockDY = SubDockDYEff();
		if (subDockDX != 0 || subDockDY != 0)
		{
			int32_t sl = 0, st = 0;
			AbsoluteTopLeft(sub, sl, st);
			// The law needs THIS menu's ringBltY. If the recorded blit is not
			// for this buffer size, the menu just switched and its ring has not
			// painted yet - skip; blits fire every frame vs this 4x/sec sweep,
			// so the next sweep has fresh data.
			const bool ringFresh =
				(gSubRingBufW == sub->GetW() && gSubRingBufH == sub->GetH());
			// FIX (2026-08-23 review): the SUBSHIFT counter reset used to
			// live here, gated on ringFresh - a LEVEL condition true on
			// every tick once the ring has painted, not an edge, so it
			// reset the counter right back to 0 immediately before its own
			// gate check ran and defeated the 40-line cap entirely. The
			// reset now lives at the actual per-open edge event, in
			// SubPlaceDetour's birth hook, alongside SUBGEO/SUBGEO2.
			// #134: the POSITIVE CONTROL for SUBCAND. Without this, an empty
			// SUBCAND log has two readings - "the sweep ran and no button
			// matched" and "the sweep never ran" - and they need opposite
			// fixes. This line fires whenever the dock block is entered, so
			// silence below it is a measurement rather than an absence.
			if (gSubCandLog < 24)
			{
				Logger::Get().WriteLine(LogLevel::Debug,
					"UiSpike: SUBSWEEP entered  cont(%d,%d %dx%d)  "
					"ringBuf=%dx%d ringFresh=%d  dock(%d,%d) f=%.2f",
					sl, st, sub->GetW(), sub->GetH(),
					gSubRingBufW, gSubRingBufH, ringFresh ? 1 : 0,
					subDockDX, subDockDY, gTierF);
			}
			// SUBGEO2 (v4.0.23): the ring's TRUE drawn absolute position vs
			// the strip rows, printed per open UNCONDITIONALLY - the original
			// SUBGEO sits inside the candidate-match success path, which for
			// the memo.submenus columns (Build Park et al.) never matches and
			// therefore never spoke. This is the instrument that decides
			// whether the attach row is wrong because of a bad ring pin
			// (AutoY from an inverted-clamped cy) or something else.
			//
			// (The v4.0.24 RingRowDesign pin, retired in v4.0.25: REGRESSION.md
			// [CC-19].)
			if (ringFresh && gSubGeo2Log < 40)
			{
				gSubGeo2Log++;
				int32_t stl = 0, stt = 0;
				cIGZWin* stw = sub->GetChildWindowFromID(0x8A2CAD8B);
				if (stw) { AbsoluteTopLeft(stw, stl, stt); }
				const int ringAbsX = sl + gSubRingBltX + gSubRingAutoX
					+ SubRingDXEff();
				const int ringAbsY = st + gSubRingBltY + gSubRingAutoY
					+ SubRingDYEff();
				// Debug, not Info (audit A5): up to 40 lines per submenu open
				// was 14% of a play log at the shipped LogLevel=1 budget.
				Logger::Get().WriteLine(LogLevel::Debug,
					"UiSpike: SUBGEO2 CONT(%d,%d %dx%d)  RINGr(%d,%d)  "
					"RINGa(%d,%d)  AUTO(%d,%d)  nudge(%d,%d)  "
					"STRIP(%d,%d %dx%d)",
					sl, st, sub->GetW(), sub->GetH(),
					gSubRingBltX, gSubRingBltY, ringAbsX, ringAbsY,
					gSubRingAutoX, gSubRingAutoY,
					SubRingDXEff(), SubRingDYEff(),
					stl, stt, stw ? stw->GetW() : 0,
					stw ? stw->GetH() : 0);
			}
			// Never shift the strip child independently of its container: the bar art
			// is painted into the container buffer at the builder's positions, so that
			// breaks bar+strip alignment (STRIP SHIFT, v4.0.27, retired; REGRESSION.md
			// [CC-20]).
			// BIRTH OWNS THE DOCK (2026-09-25): a container that SubPlaceDetour
			// docked THIS open is claimed by birth's own anchor (the game's
			// Place() cy = the spawn button's centre) and target, and keeps
			// birth's ring pin. The formula match below is the LEGACY path, for
			// containers birth did not dock (SubBornDock=0 / SubMath=0): its
			// SubPlaceTop + SUBSHIFT target disagrees with birth's SubPlaceTopMb,
			// so on a born container it matched no button at 6+ items and the
			// NEIGHBOUR at 5 (ring + back arrow one row low). See gSubBornWin.
			const bool bornOwned = gSubMath && gSubBornWin == sub
				&& gSubBornH == sub->GetH();
			const int32_t parentAbsT = st - sub->GetT();   // parent frame -> abs
			const int32_t bornCyAbs = gSubBornCy + parentAbsT;
			const int32_t bornTopAbs = gSubBornTopRel + parentAbsT;
			bool done = false;
			bool subShiftLoggedThisSweep = false;
			for (uint32_t pid : kSubFlyoutParents)
			{
				if (done || !ringFresh) { break; }
				cIGZWin* par = pView->GetChildWindowFromIDRecursive(pid);
				if (!par || !par->IsVisible()) { continue; }
				ChildSnapshot kids = {};
				par->EnumChildren(GZIID_cIGZWin, ChildSnapshot::Callback, &kids);
				for (int ci = 0; ci < kids.count; ci++)
				{
					cIGZWin* kid = kids.wins[ci];
					if (!kid || !kid->IsVisible()) { continue; }
					if (kid->GetW() < 40 || kid->GetW() > 200) { continue; }
					int32_t bl = 0, bt = 0;
					AbsoluteTopLeft(kid, bl, bt);
					const int32_t natL = bl + SubNativeDXFor(kid->GetW());
					const int32_t natT =
						bt + kid->GetH() / 2 - gSubRingBltY - kSubPlaceBias;
					// #95: the model, or the legacy constant when SubMath=0.
					const int32_t bcy = bt + kid->GetH() / 2;
					// BIRTH OWNS THE DOCK: only the button birth was anchored to
					// may claim a born container - never a neighbour whose
					// formula target happens to land within the +-3 px window.
					if (bornOwned && abs(bcy - bornCyAbs) > 2) { continue; }
					// The LEGACY target is where the container must sit for the
					// ring to land on its button, and it is exactly right about
					// the ring at every factor - substituting the two Eff()
					// forms collapses it to
					//     ringAbs = (bcx, bcy) - (RoundHalfUp(16.5f) - bltX,
					//                             RoundHalfUp(26.5f))
					// i.e. the ring sprite CENTRED on the button, which is what
					// SUBGEO measured live (BTN ctr 227,679 == ring ctr).
					// So: container to the MODEL, ring pinned to the LEGACY.
					const int32_t legL = natL + subDockDX;
					const int32_t legT = natT + subDockDY;
					// SubMath governs Y ONLY, and X deliberately stays on the
					// measured law. The model's X is not wrong, it is a
					// DIFFERENT convention: the 80f-wide ring sprite has the
					// stem built into its right half, so the game's own
					// left = cx - 27f draws the ring 13f RIGHT of the button
					// centre, while our measured dock centres it (they differ
					// by exactly RoundHalfUp(40f) - RoundHalfUp(27f) = 26 at
					// f=2). Nothing is broken horizontally - the reported
					// defect is the column hanging into the bottom HUD - so
					// moving X would be an unforced 26px change to a placement
					// the player has already signed off. It would ALSO desync
					// birth from the sweep: the sweep only re-docks a container
					// it finds at the native or the target position, and a
					// 26px disagreement fails both tests, which silently ends
					// the dock AND freezes the back-arrow click zone.
					const int32_t tgtL = legL;
					// A born container's target is where birth put it - the one
					// SubPlaceTopMb decision for this open, never re-derived.
					int32_t tgtT = bornOwned ? bornTopAbs
						: gSubMath
						? SubPlaceTop(sub->GetH(), bcy, pView->GetH(), gTierF)
						: legT;
					// v4.0.33: container shift from ring geometry (all counts).
					// Uses gSubRingBltY (measured) and autoY0 = legT - tgtT
					// to compute the exact shift needed for the arm to meet
					// the strip at the target row.
					// LEGACY PATH ONLY: birth's SubPlaceTopMb already chose the
					// born container's top, and shifting it again is exactly the
					// 148 px row this used to add on the 5-item power strip.
					if (!bornOwned && gTierF > 1.0f)
					{
						cIGZWin* stw = sub->GetChildWindowFromID(0x8A2CAD8B);
						if (stw && gSubRingBltY >= 0)
						{
							const int32_t cnt =
								*reinterpret_cast<const int32_t*>(
									reinterpret_cast<const char*>(stw) + 0xE4);
							// FIX (2026-08-23 review): cnt was read with no
							// upper bound - SubContainerShiftFromGeo only
							// guards cnt<1. A strip caught mid-repopulate
							// (item list rebuilding on the same tick the
							// sweep runs) or an unexpected layout at this
							// offset could hand an out-of-range cnt straight
							// into stripH/contentH and produce an oversized
							// shiftPx, applied unconditionally to tgtT below
							// with no further check. No shipped category
							// approaches 64 items; this is a shape sanity
							// bound, not a tuned gameplay limit.
							if (cnt >= 1 && cnt <= 64)
							{
								const int32_t autoY0 = legT - tgtT;
								const SubShiftTerms terms = SubContainerShiftFromGeo(
									gSubRingBltY, autoY0, cnt);
								const int32_t shiftPx = terms.shift;
								if (shiftPx > 0)
								{
									tgtT -= shiftPx;
								}
								if (gSubShiftLog < 40 && !subShiftLoggedThisSweep)
								{
									subShiftLoggedThisSweep = true;
									gSubShiftLog++;
									// The formula's own terms (SubContainerShiftFromGeo)
									Logger::Get().WriteLine(LogLevel::Debug,
										"UiSpike: SUBSHIFT cnt=%d "
										"ringBltY=%d autoY0=%d gAutoY=%d shift=%d "
										"natRow=%.2f tgtRow=%.2f ringHs=%d sT=%d f=%.2f",
										cnt, gSubRingBltY, autoY0, gSubRingAutoY,
										shiftPx, terms.naturalRow, terms.targetRow,
										terms.ringHs, terms.stripTop, gTierF);
								}
							}
						}
					}
					const bool atNative = (abs(sl - natL) <= 3 && abs(st - natT) <= 3);
					const bool atTarget = (abs(sl - tgtL) <= 3 && abs(st - tgtT) <= 3);
					// #134: BEFORE the gate, so a container the sweep declines
					// still reports the one number the ring law cannot derive -
					// the button's absolute X. ERR is stated in the log rather
					// than left to be re-derived: it is the signed distance
					// from the ring HOLE centre to the button ELLIPSE centre,
					// the two features derive_subring.py aligns. ERR is exactly
					// the amount to SUBTRACT from SubRingDX, so a reader never
					// has to dial. NATDX is the live kSubNativeDX for this tier;
					// it is 20 at f=2 by construction, and any other value there
					// means this instrument is lying.
					if (gSubCandLog < 24)
					{
						gSubCandLog++;
						const int32_t ringAbsX =
							sl + gSubRingBltX + gSubRingAutoX + SubRingDXEff();
						const int32_t holeCX = ringAbsX + RoundHalfUp(25 * gTierF);
						const int32_t elliCX = bl + RoundHalfUp(21 * gTierF);
						Logger::Get().WriteLine(LogLevel::Debug,
							"UiSpike: SUBCAND #%02d btn=0x%08X BTN(%d,%d %dx%d)  "
							"CONT(%d,%d)  nat(%d,%d) tgt(%d,%d)  atNat=%d atTgt=%d  "
							"NATDX=%d  holeCX=%d elliCX=%d  ERR=%+d  "
							"(DX=%d) f=%.2f",
							gSubCandLog, kid->GetID(), bl, bt,
							kid->GetW(), kid->GetH(), sl, st,
							natL, natT, tgtL, tgtT, atNative ? 1 : 0,
							atTarget ? 1 : 0, sl - subDockDX - bl,
							holeCX, elliCX, holeCX - elliCX,
							SubRingDXEff(), gTierF);
					}
					if (!atNative && !atTarget) { continue; }
					done = true;
					// #95: pin the ring to the legacy (measured-correct) spot
					// by offsetting the sprite by exactly the container move.
					// Refreshed EVERY sweep while the menu is open, so it can
					// never drift; identically zero when SubMath is off.
					gSubRingAutoX = 0;                                // X unmodelled
					// BIRTH OWNS THE DOCK: birth's pin, verbatim - one writer
					// per open. (legT - tgtT is the same number only when the
					// game's native top equals the unclamped law.)
					gSubRingAutoY = bornOwned ? gSubBornAutoY
						: (gSubMath ? (legT - tgtT) : 0);
					// Back-arrow click zone (abs) + selected-button centre for
					// the forward. Computed from the POST-dock container pos
					// (tgt), the recorded ring blit, and the measured arrow
					// bounds; refreshed every sweep while the menu is open.
					// v2.24.0 (audit B8): the arrow art bounds are 1x sprite px,
					// drawn at the tier factor - so scale them by f, keeping the
					// +-4 click margin UNSCALED (f=2: RoundHalfUp(48*2)-4 = 92 =
					// the old 2*48-4 exactly; same for all four edges).
					// #95: the arrow is INSIDE the ring sprite, so its click
					// zone must carry the Auto offset too - otherwise moving
					// the container would leave the hit box behind on a
					// hit-test-sensitive control. With the pin above, the two
					// terms cancel and the zone lands exactly where v2.45.2
					// put it (the arithmetic proof is in Test-SubRingLock).
					gSubArrowAbs[0] = tgtL + gSubRingBltX + SubRingDXEff()
						+ gSubRingAutoX + RoundHalfUp(kSubArrowX0 * gTierF) - 4;
					gSubArrowAbs[1] = tgtT + gSubRingBltY + SubRingDYEff()
						+ gSubRingAutoY + RoundHalfUp(kSubArrowY0 * gTierF) - 4;
					gSubArrowAbs[2] = tgtL + gSubRingBltX + SubRingDXEff()
						+ gSubRingAutoX + RoundHalfUp(kSubArrowX1 * gTierF) + 4;
					gSubArrowAbs[3] = tgtT + gSubRingBltY + SubRingDYEff()
						+ gSubRingAutoY + RoundHalfUp(kSubArrowY1 * gTierF) + 4;
					gSubBtnCX = bl + kid->GetW() / 2;
					gSubBtnCY = bt + kid->GetH() / 2;
					// SUBOWN (law 44 - the probe states the verdict): which
					// button owns this open, and the ring pin + arrow zone the
					// sweep will now hold. Once per open (reset at birth).
					if (bornOwned && gSubOwnLog < 1)
					{
						gSubOwnLog++;
						Logger::Get().WriteLine(LogLevel::Info,
							"UiSpike: SUBOWN birth btn=0x%08X ctr(%d,%d) top=%d "
							"autoY=%d ringA=%d arrow(%d,%d)-(%d,%d) - sweep reuses "
							"birth's anchor, target and ring pin",
							kid->GetID(), gSubBtnCX, gSubBtnCY, tgtT,
							gSubRingAutoY,
							tgtT + gSubRingBltY + gSubRingAutoY + SubRingDYEff(),
							gSubArrowAbs[0], gSubArrowAbs[1],
							gSubArrowAbs[2], gSubArrowAbs[3]);
					}
					// #95 SUBGEO - the WHOLE assembly in one line, once per
					// open. Two wrong models in a row came from reasoning about
					// these four rects separately; this prints them together in
					// ONE coordinate space (absolute) so the relationship is
					// read, not inferred:
					//   BTN    the spawn button (where the ring must sit)
					//   CONT   the container we position
					//   RINGr  the ring blit ORIGIN *inside* the container
					//          (the game's own value - we never scale it)
					//   RINGa  that origin in ABSOLUTE screen coords
					//   STRIP  the item column, absolute
					// If RINGa != BTN centre-ish, the ring is off its button.
					// If STRIP runs past the HUD, the column overflows.
					// The two are separate facts and this line shows both.
					if (gSubGeoLog < 8)
					{
						gSubGeoLog++;
						int32_t stl = 0, stt = 0;
						cIGZWin* stw = sub->GetChildWindowFromID(0x8A2CAD8B);
						if (stw) { AbsoluteTopLeft(stw, stl, stt); }
						// v2.46.0: RINGa is now the TRUE DRAWN position - it
						// carries the Auto offset AND the ini nudge
						// (SubRingDX/DY, live 25/-6), which the old line
						// silently omitted. That omission is worth 25px and
						// would have sent the next reader hunting a phantom.
						// AUTO/TGT print beside it so a wrong placement names
						// its own term instead of being re-derived.
						// ACCEPTANCE: RINGa must be IDENTICAL to v2.45.2's
						// (the pin), i.e. it must not move when SubMath flips.
						Logger::Get().WriteLine(LogLevel::Debug,
							"UiSpike: SUBGEO BTN(%d,%d %dx%d ctr %d,%d)  "
							"CONT(%d,%d %dx%d)  RINGr(%d,%d)  RINGa(%d,%d)  "
							"AUTO(%d,%d)  TGT(%d,%d)  STRIP(%d,%d %dx%d)  "
							"math=%d f=%.2f",
							bl, bt, kid->GetW(), kid->GetH(),
							gSubBtnCX, gSubBtnCY,
							sl, st, sub->GetW(), sub->GetH(),
							gSubRingBltX, gSubRingBltY,
							sl + gSubRingBltX + gSubRingAutoX + SubRingDXEff(),
							st + gSubRingBltY + gSubRingAutoY + SubRingDYEff(),
							gSubRingAutoX, gSubRingAutoY, tgtL, tgtT,
							stl, stt, stw ? stw->GetW() : 0,
							stw ? stw->GetH() : 0, gSubMath, gTierF);
					}
					if (atNative)
					{
						// GZWinMoveTo is RELATIVE (moves BY, not TO) - the header
						// docs are wrong and every early "vanishing panel" bug
						// came from misusing it. Delta = target - current ABS.
						sub->GZWinMoveTo(tgtL - sl, tgtT - st);
						sub->InvalidateSelfAndParents();
						Logger::Get().WriteLine(LogLevel::Debug,
							"UiSpike: SUBDOCK 0x%08X btn=0x%08X abs(%d,%d) ringY=%d "
							"native(%d,%d) -> target(%d,%d)",
							subId, kid->GetID(), bl, bt, gSubRingBltY,
							natL, natT, tgtL, tgtT);
					}
					break;
				}
			}
			// SUBOWN's negative verdict: a born container whose anchor matched no
			// candidate keeps birth's ring pin (nothing overwrites it) but gets no
			// back-arrow zone - say so, once per open, instead of staying silent.
			if (bornOwned && ringFresh && !done && gSubOwnLog < 1)
			{
				gSubOwnLog++;
				Logger::Get().WriteLine(LogLevel::Info,
					"UiSpike: SUBOWN birth anchor cy=%d (abs %d) matched no button "
					"in the open menu - ring pin kept (autoY=%d), no arrow zone",
					gSubBornCy, bornCyAbs, gSubRingAutoY);
			}
		}

		// ---- REUSE THE DISASTER DRAW FIXES (v2.13.5) ----------------------
		// PROVEN by the SVT class probe: this container is class 0x00AB6AA8 and
		// its strip child is 0x00AB6D88 - the SAME concrete classes as the
		// disaster flyout. So the two fixes already written for those classes
		// apply verbatim, and nothing new has to be reverse-engineered:
		//   SlotThunk<88> (force-recreate)   -> corrupts the buffer's cached
		//       width so Plot recreates it at the CURRENT (2x) window size.
		//       That is the "bar is still 1x" fix: for code-painted controls
		//       the lever is the BUFFER, not the window.
		//   SlotThunk2<88> + gStripFieldScale -> doubles the strip's item
		//       size/spacing fields [0xf4]/[0xf8]/[0xfc]. That is the
		//       "pictures are not seated on the bar" fix.
		//
		// SAFETY vs the "one window only" warning on gVtCopy: that warning is
		// about hooking windows of DIFFERENT classes, which left earlier
		// instances pointing at a copy of the wrong class's vtable. Here the
		// class is IDENTICAL, so gVtCopy/gVtCopy2 are already exact copies of
		// these very vtables. The two windows are also never live at the same
		// time (disaster is god mode, this is mayor mode). The vtable is
		// verified before every patch and the instance is skipped if it is not
		// the expected class.
		{
			void** subVt = *reinterpret_cast<void***>(sub);
			if (knownMenuOpen && subVt == reinterpret_cast<void**>(0x00AB6AA8))
			{
				for (int vi = 0; vi < 256; vi++) { gVtCopy[vi] = subVt[vi]; }
				for (int si = 87; si <= 97; si++)
				{
					gOrigSlot[si] = reinterpret_cast<SlotFn>(subVt[si]);
					gVtCopy[si] = reinterpret_cast<void*>(
						si == 87 ? (void*)&SlotThunk<87> :
						si == 88 ? (void*)&SlotThunk<88> :
						si == 89 ? (void*)&SlotThunk<89> :
						si == 90 ? (void*)&SlotThunk<90> :
						si == 91 ? (void*)&SlotThunk<91> :
						si == 92 ? (void*)&SlotThunk<92> :
						si == 93 ? (void*)&SlotThunk<93> :
						si == 94 ? (void*)&SlotThunk<94> :
						si == 95 ? (void*)&SlotThunk<95> :
						si == 96 ? (void*)&SlotThunk<96> :
						           (void*)&SlotThunk<97>);
				}
				// Back-arrow claim (v2.17.0): container slot 121 is the claim
				// function 0x0079AE30 (verified by disasm; same class as the
				// disaster container). Sub-flyout install only - the disaster
				// install path stays untouched (LOCKED), and the thunk is
				// additionally gated on !gDisasterDrawTuning.
				if (gClickHook && gArrowClick)
				{
					gOrigContPt121 = reinterpret_cast<PtInFn>(subVt[121]);
					gVtCopy[121] = reinterpret_cast<void*>(&ContPt121Thunk);
				}
				*reinterpret_cast<void***>(sub) = gVtCopy;
				gForceInvalidate = 20;
				// This window is NOT the disaster flyout: keep the generic
				// fixes (buffer force-recreate, strip item fields) but switch
				// off the disaster-measured ring/bar offsets, which would
				// otherwise fire on it via the destIsContainer size heuristic.
				gDisasterDrawTuning = 0;
				// v2.36.3: the line now sits where the install actually
				// happens, so it is an EVENT. Since v2.36.2 birth-hooks the
				// container, this should be RARE - a burst of these means the
				// born-hook path stopped firing, which is itself the signal.
				Logger::Get().WriteLine(LogLevel::Info,
					"UiSpike: SUBHOOK container 0x%08X %dx%d -> draw hooks "
					"installed HERE by the sweep (birth hook did not run)",
					subId, sub->GetW(), sub->GetH());
			}
			// CLAIM WIDTH (the other half of the click fix). The container's
			// custom IsPointInMe claims only the rightmost [this+0xe0] px, and
			// that field keeps its 1x value while the draw is 2x - so only the
			// right half of the pictures is clickable. Same guarded, idempotent
			// write as the disaster dock: only touch it when it is still in the
			// 1x range, so re-running the sweep cannot double it twice.
			// NOTE [0xe0] is DUAL-USE (claim width AND a Plot layout inset) -
			// SlotThunk halves it back on entry to the draw group, which is what
			// stops a SECOND bar being painted.
			if (knownMenuOpen && gClaimScale > 1)
			{
				int32_t* claimW = reinterpret_cast<int32_t*>(
					reinterpret_cast<char*>(sub) + 0xE0);
				if (*claimW >= 30 && *claimW <= 60)
				{
					// v2.24.0 (audit A6): scale by the tier factor and LATCH the
					// 1x original for the draw group's restore. f=2: identical
					// write to the old oldW * gClaimScale(=2).
					const int32_t oldW = *claimW;
					gClaimOrig = oldW;
					*claimW = RoundHalfUp(oldW * gTierF);
					Logger::Get().WriteLine(LogLevel::Debug,
						"UiSpike: SUBCLAIM container 0x%08X [0xe0] %d -> %d",
						subId, oldW, *claimW);
				}
				// v2.36.3 (task #77): the "hooks installed" line used to print
				// HERE, i.e. on EVERY sweep while a menu was open (194x in one
				// session) - the install is gated separately, above, on the
				// vtable check. Read as an event it reported a 159ms install
				// gap that did not exist; the real signal was SUBCLAIM. The
				// accurate line now lives in the install branch itself. See
				// METHOD.md "YOUR OWN INSTRUMENTS CAN LIE".
			}
			ChildSnapshot sk = {};
			sub->EnumChildren(GZIID_cIGZWin, ChildSnapshot::Callback, &sk);
			for (int ci = 0; ci < sk.count; ci++)
			{
				// Crash guard (v2.22.1): no strip hooks, no field doubling and
				// no heal-invalidate for a sub-flyout whose owning menu is not
				// one we validated. See the KNOWN-MENU GATE note above.
				if (!knownMenuOpen) { break; }
				cIGZWin* kid = sk.wins[ci];
				if (!kid) { continue; }
				void** kvt = *reinterpret_cast<void***>(kid);
				// FIRST-OPEN SELF-HEAL (v2.18.6, correcting v2.18.5): on the
				// first-ever open of a menu the strip may never re-Plot after
				// install (airports sat at 1x layout for minutes). The Plot
				// hook does capture-naturals-then-double; the ONLY thing
				// missing was the Plot itself. So the sweep INVALIDATES when
				// it sees 1x fields on a visible strip - and NEVER writes the
				// fields (v2.18.5 wrote them BEFORE the hook's one-shot
				// capture ran, poisoning the captured "naturals" with doubled
				// values = 4x pitch, giant items, menus broken everywhere).
				if ((kvt == reinterpret_cast<void**>(0x00AB6D88)
						|| kvt == gVtCopy2) && gStripFieldScale > 1)
				{
					const int32_t f4 = reinterpret_cast<int32_t*>(kid)[0x3d];
					if (f4 >= 40 && f4 <= 50)
					{
						sub->InvalidateSelfAndParents();
						static int healLog = 0;
						if (healLog < 20)
						{
							healLog++;
							Logger::Get().WriteLine(LogLevel::Debug,
								"UiSpike: SUBHEAL strip 0x%08X fields still 1x "
								"(f4=%d) - invalidating for a fresh Plot",
								kid->GetID(), f4);
						}
					}
				}
				if (kvt != reinterpret_cast<void**>(0x00AB6D88)) { continue; }
				for (int vi = 0; vi < 256; vi++) { gVtCopy2[vi] = kvt[vi]; }
				for (int si = 87; si <= 97; si++)
				{
					gOrigSlot2[si] = reinterpret_cast<SlotFn>(kvt[si]);
					gVtCopy2[si] = reinterpret_cast<void*>(
						si == 87 ? (void*)&SlotThunk2<87> :
						si == 88 ? (void*)&SlotThunk2<88> :
						si == 89 ? (void*)&SlotThunk2<89> :
						si == 90 ? (void*)&SlotThunk2<90> :
						si == 91 ? (void*)&SlotThunk2<91> :
						si == 92 ? (void*)&SlotThunk2<92> :
						si == 93 ? (void*)&SlotThunk2<93> :
						si == 94 ? (void*)&SlotThunk2<94> :
						si == 95 ? (void*)&SlotThunk2<95> :
						si == 96 ? (void*)&SlotThunk2<96> :
						           (void*)&SlotThunk2<97>);
				}
				// ---- THE CLICK FIX, same two levers as disaster ---------------
				// Only the RIGHT half of the pictures is clickable here, exactly
				// as on the disaster flyout, and for the same reason: this
				// container class OVERRIDES IsPointInMe (0x0079A180 -> slot 121
				// = 0x0079AE30) to claim only the RIGHTMOST [this+0xe0] px. That
				// field still holds its 1x value while the draw is 2x, so the
				// left half never reaches the strip at all - and because the
				// router is first-claim-wins, every downstream hook stays SILENT,
				// which is what made this look like a z-order bug for hours.
				// Two levers, and they INTERSECT - both are required:
				//   ClaimScale=2 doubles [container+0xe0]  (widens the claim)
				//   SelForce=1   forces the strip's refined mask (slot 149) open
				if (gClickHook)
				{
					gOrigMouse136 = reinterpret_cast<MouseFn>(kvt[136]);
					gOrigMouse138 = reinterpret_cast<MouseFn>(kvt[138]);
					gOrigPt121    = reinterpret_cast<PtInFn>(kvt[121]);
					gOrigSlot149  = reinterpret_cast<PtInFn>(kvt[149]);
					gOrigSlot62   = reinterpret_cast<PtInFn>(kvt[62]);
					gOrigSlot59   = reinterpret_cast<XformFn>(kvt[59]);
					gVtCopy2[62]  = reinterpret_cast<void*>(&Slot62Thunk);
					gVtCopy2[59]  = reinterpret_cast<void*>(&Slot59Thunk);
					gVtCopy2[136] = reinterpret_cast<void*>(&Mouse136Thunk);
					gVtCopy2[138] = reinterpret_cast<void*>(&Mouse138Thunk);
					gVtCopy2[121] = reinterpret_cast<void*>(&Pt121Thunk);
					gVtCopy2[149] = reinterpret_cast<void*>(&Slot149Thunk);
				}
				*reinterpret_cast<void***>(kid) = gVtCopy2;
				Logger::Get().WriteLine(LogLevel::Info,
					"UiSpike: SUBHOOK strip 0x%08X %dx%d -> disaster strip hooks "
					"installed (item fields x%d, clickHook=%d)",
					kid->GetID(), kid->GetW(), kid->GetH(),
					gStripFieldScale, gClickHook);
			}
		}

		// CLASS PROBE. The sub-flyout's strip child is 88px wide - the SAME
		// width as the disaster flyout's thumbnail strip - and the symptoms
		// match disaster exactly (bar painted at 1x, pictures not seated on the
		// bar). If these are the same concrete classes as the disaster
		// container (0x00AB6AA8) and strip (0x00AB6D88), then the fixes already
		// exist and are already patched into those class vtables
		// (the SlotThunk<88> force-recreate for the stale 1x buffer, gStripFieldScale for the
		// item size/spacing fields) - they are merely gated to the disaster
		// window. That would turn this into a gating change instead of a fresh
		// disassembly job, so establish it before building anything.
		{
			static int vtLogged = 0;
			if (vtLogged < 2)
			{
				vtLogged++;
				void** subVt = *reinterpret_cast<void***>(sub);
				ChildSnapshot sk = {};
				sub->EnumChildren(GZIID_cIGZWin, ChildSnapshot::Callback, &sk);
				Logger::Get().WriteLine(LogLevel::Debug,
					"UiSpike: SVT sub=0x%08X vtable=%p  (disaster container "
					"0x00AB6AA8 / strip 0x00AB6D88)", subId, (void*)subVt);
				for (int ci = 0; ci < sk.count; ci++)
				{
					cIGZWin* kid = sk.wins[ci];
					if (!kid) { continue; }
					void** kvt = *reinterpret_cast<void***>(kid);
					Logger::Get().WriteLine(LogLevel::Debug,
						"UiSpike: SVT   child=0x%08X %dx%d vtable=%p%s",
						kid->GetID(), kid->GetW(), kid->GetH(), (void*)kvt,
						(kvt == reinterpret_cast<void**>(0x00AB6D88))
							? "  == DISASTER STRIP CLASS" : "");
				}
			}
		}

		// SCAL: which flyout is open, where its buttons are, and where the game
		// put the sub-menu relative to each. One capture with a sub-menu open
		// gives the offset AND tells us whether it anchors to the clicked
		// button, to the parent flyout, or is centred on something.
		static int scal = 0;
		if (scal < 10)
		{
			int32_t sl = 0, st = 0;
			AbsoluteTopLeft(sub, sl, st);
			// Find the open parent flyout among the ones we know.
			const uint32_t kParents[] = {
				0x49923239, 0x69923479, 0xC99237A0, 0xE992F711, 0x699306ED
			};
			for (uint32_t pid : kParents)
			{
				cIGZWin* par = pView->GetChildWindowFromIDRecursive(pid);
				if (!par || !par->IsVisible()) { continue; }
				int32_t pl = 0, pt = 0;
				AbsoluteTopLeft(par, pl, pt);
				scal++;
				Logger::Get().WriteLine(LogLevel::Debug,
					"UiSpike: SCAL sub=0x%08X abs(%d,%d) %dx%d  parent=0x%08X "
					"abs(%d,%d) %dx%d  subRelParent(%d,%d)",
					subId, sl, st, sub->GetW(), sub->GetH(),
					pid, pl, pt, par->GetW(), par->GetH(),
					sl - pl, st - pt);
				// ...and against every button in that flyout, so the anchor is
				// identifiable no matter which one was clicked.
				ChildSnapshot kids = {};
				par->EnumChildren(GZIID_cIGZWin, ChildSnapshot::Callback, &kids);
				for (int ci = 0; ci < kids.count; ci++)
				{
					cIGZWin* kid = kids.wins[ci];
					if (!kid || !kid->IsVisible()) { continue; }
					if (kid->GetW() < 40 || kid->GetW() > 200) { continue; }
					int32_t bl = 0, bt = 0;
					AbsoluteTopLeft(kid, bl, bt);
					Logger::Get().WriteLine(LogLevel::Debug,
						"UiSpike: SCAL   btn=0x%08X abs(%d,%d) %dx%d  "
						"ctr(%d,%d)  subRelBtn(%d,%d)",
						kid->GetID(), bl, bt, kid->GetW(), kid->GetH(),
						bl + kid->GetW() / 2, bt + kid->GetH() / 2,
						sl - bl, st - bt);
				}
				break;
			}
		}
	}

	// ---- MAYOR-ONLY FLYOUTS (v2.13.2) ------------------------------------
	// Zones/Transport/Utilities/Civic never enter the god loop below, and the
	// generic sweep now skips them (IsMayorOnlyFlyoutId) precisely so they can
	// be docked here to their own spawn button by the alignment-marker rule.
	// Unlike the god flyouts these are DESTROYED AND RECREATED on every open
	// rather than hidden, so there is no "pre-scale while hidden" to do: each
	// fresh instance is scaled and docked on the first sweep that sees it.
	// v2.25.4: the gate moved PER-ENTRY. anyMode entries (the Sim-mode
	// sidebar's flyout columns) must be processed while the mayor HUD is
	// HIDDEN - v2.25.3 gated them here on mayorModeActive while the generic
	// sweep skipped them unconditionally, leaving a raw 1x window (the
	// user's "completely broken" screenshot; log proof: zero "mayor flyout
	// 0x8BB27C12" lines in the whole session). Their state gate is the
	// flyout+button search itself: neither exists outside their mode.
	//
	// Both loops' flyout lookups in ONE walk (audit A1): in mayor mode with
	// nothing open that was nine whole-view misses a tick. Same gates, same
	// order as the loops; a flyout that is found gets scaled and docked, so
	// the loop calls Touched() and the ids after it are walked again.
	IdBatch flyouts;
	flyouts.root = pView;
	for (const MayorFlyoutDock& m : kMayorFlyoutDock)
	{
		if (m.mayorOnly && (mayorModeActive || m.anyMode)) { flyouts.Add(m.flyoutId); }
	}
	for (const GodFlyoutDock& d : kGodFlyoutDock) { flyouts.Add(d.id); }
	{
		for (const MayorFlyoutDock& m : kMayorFlyoutDock)
		{
			if (!m.mayorOnly) { continue; }
			if (!mayorModeActive && !m.anyMode) { continue; }
			cIGZWin* win = flyouts.Next(m.flyoutId);
			if (!win || win->GetW() <= 0 || win->GetH() <= 0) { continue; }
			flyouts.Touched();

			// ============ #194 REBIRTH PURGE ============================
			// USER: in mayor mode the Emergency flyout, opened FIRST after a
			// load, drew its ring detached from the strip; clicking elsewhere
			// and reopening fixed it.
			//
			// THE LATCH IS NOT COLD - IT IS WARM WITH FOREIGN DATA, and that
			// distinction is the whole fix. #80 cured the DISASTER flyout by
			// warming a cache earlier, and applying that here would do nothing
			// (every absent-record path already returns the right answer) and
			// could poison more addresses.
			//
			// MEASURED, log _tests/captures/SC4UIScale-2026-08-18-205344.log:
			//   :16034  MDOCK 0x0992FD17 live marker (3,234) units=screen
			//           -> used (3,234) -> (25,776) overrides table (22,542)
			//   :16035  mayor flyout 0x0992FD17 at(25,776) size 308x840, +7 win
			// +7 where the script has EIGHT windows: the marker was skipped.
			//
			// WHY. These flyouts are destroyed and recreated on every open, so
			// a new marker lands on a RECYCLED heap address still carrying a
			// dead window's record. The only anti-reuse test in Classify is
			// win->GetID() != rec.id, and the alignment marker's id is
			// 0x0000AAAA - CENSUSED over tools/uiscripts/extracted: 74
			// instances across 41 scripts with 25 distinct rect sizes. An
			// id-keyed guard is structurally inert for the most-shared id in
			// the corpus. Classify returns AlreadyScaled, ScaleSubtree skips
			// the marker, MarkerIsDesignUnits then matches neither size and
			// falls through to "screen units", so the dock subtracts the RAW
			// design offset and lands on the game's own native placement -
			// where nothing looks moved, so the container is never seated and
			// the welded ring sits (f-1)*234 px low.
			//
			// It self-corrects on a later open because it is sticky per
			// ADDRESS, not per open: opening another flyout recycles the
			// pointer, the marker classifies Fresh, and the dock is right
			// thereafter. That is exactly what the player saw.
			//
			// THE CURE IS THE PROJECT'S OWN, copied from ScalePanelRoot
			// (~:14887) whose comment describes this failure in these words:
			// "new objects land on RECYCLED heap addresses ... classify
			// Unrecognized, and stay stuck at 1x design geometry forever".
			// Erase the root's own record too - that is what clears a
			// tug-of-war tombstone left by a previous instance at this
			// address, which otherwise pins the whole flyout at raw 1x.
			//
			// THE GATE IS THE ENTIRE SAFETY ARGUMENT. Purge ONLY when the
			// root is not already at its recorded scaled size. After
			// ScaleSubtree the record carries scaledW == GetW(), so the gate
			// is false on every subsequent tick and the purge fires exactly
			// once per open. Without it this would re-purge and re-scale at
			// sweep cadence - the double-scale that shipped #98's 4x legend.
			// God-path flyouts are hidden/re-shown rather than rebuilt, keep
			// their scaled size, and so never take this branch.
			if (Classify(win) != ScaleState::AlreadyScaled)
			{
				scaleMap.erase(win);
				PurgeSubtreeRecords(win, 0);
				if (gMayorRebirthLogs < 8)
				{
					gMayorRebirthLogs++;
					Logger::Get().WriteLine(LogLevel::Info,
						"UiSpike: REBIRTH 0x%08X purged stale records before "
						"scale (%dx%d) - a recreated flyout landed on recycled "
						"addresses; without this its 0x0000AAAA marker keeps a "
						"dead window's record and the dock uses design units.",
						m.flyoutId, win->GetW(), win->GetH());
				}
			}

			int n = 0;
			ScaleSubtree(win, f, 0, &n, false);

			cIGZWin* btn = pView->GetChildWindowFromIDRecursive(m.buttonId);
			bool moved = false;
			int32_t targetL = 0, targetT = 0;
			if (btn != nullptr && m.derived && gMayorDock != 0)
			{
				int32_t bl = 0, bt = 0;
				AbsoluteTopLeft(btn, bl, bt);
				targetL = bl + ScaleRound(m.offX, f);
				targetT = bt + ScaleRound(m.offY, f);
				// v2.43.1 (task #94): PREFER THE LIVE MARKER over the cached
				// constant. The table's R is -marker(1x) read off the STOCK
				// script, so a mod that REPLACES the script moves the marker
				// and the constant misdocks by exactly the difference -
				// measured on warrior's god-terraforming-in-mayor-mode:
				// LANDSCAPE marker moved (3,27)->(3,59) and SIGNS & LABELS
				// (3,183)->(4,5), which is the "ring against the wrong
				// circle" the player reported. The rule this file already
				// documents above the table IS the general form:
				//     target = spawnButtonAbs - markerOffset(live)
				// v2.47.0 CORRECTION: this comment used to end "and the
				// marker is scaled with the subtree we just scaled, so its
				// live L/T are already in screen units". THAT IS NOT TRUE OF
				// EVERY FLYOUT - see MarkerIsDesignUnits(), where the log
				// shows two mod flyouts permanently disagreeing. The unit
				// system is now MEASURED against the spawn button, which is
				// the ruler the alignment-marker rule already implies. The
				// table stays as the FALLBACK for any script with no marker.
				cIGZWin* mk = win->GetChildWindowFromID(0x0000AAAA);
				if (mk != nullptr)
				{
					const bool mkDesign = MarkerIsDesignUnits(mk, f);
					const int32_t mkX = mkDesign
						? ScaleRound(mk->GetL(), f) : mk->GetL();
					const int32_t mkY = mkDesign
						? ScaleRound(mk->GetT(), f) : mk->GetT();
					const int32_t liveL = bl - mkX;
					const int32_t liveT = bt - mkY;
					if ((liveL != targetL || liveT != targetT)
						&& MDockShouldLog(m.flyoutId))
					{
						// Loud on purpose: for a STOCK script these must
						// agree (the constant was derived from that very
						// marker). A disagreement means the live script is
						// NOT the one the constant was measured from.
						Logger::Get().WriteLine(LogLevel::Info,
							"UiSpike: MDOCK 0x%08X live marker (%d,%d) units=%s "
							"-> used (%d,%d) -> (%d,%d) overrides table "
							"(%d,%d) - the live script differs from the one R "
							"was measured on (a mod replaced it). "
							"[mkW=%d btnW=%d]",
							m.flyoutId, mk->GetL(), mk->GetT(),
							mkDesign ? "DESIGN(scaled by us)" : "screen",
							mkX, mkY, liveL, liveT, targetL, targetT,
							mk->GetW(), btn->GetW());
					}
					targetL = liveL;
					targetT = liveT;
				}
				const int32_t curL = win->GetL();
				const int32_t curT = win->GetT();
				moved = (curL != targetL || curT != targetT);
				if (moved)
				{
					win->GZWinMoveTo(targetL - curL, targetT - curT);
				}
			}
			if (moved || n > 0)
			{
				win->InvalidateSelfAndParents();
				Logger::Get().WriteLine(LogLevel::Info,
					"UiSpike: mayor flyout 0x%08X at(%d,%d) size %dx%d, +%d win%s.",
					m.flyoutId, win->GetL(), win->GetT(),
					win->GetW(), win->GetH(), n,
					moved ? " (docked)" : "");
			}
			// ---- EVTP (v2.17.4, ini [Flyout] EmergLog): one-shot class probe
			// of the EMERGENCY flyout's children. Its 496x636 panel
			// 0x2992FD21 paints dispatch pictures at 1x, and NO existing
			// instrument fires for it (not the disaster strip/container
			// classes). This logs each child's vtable so the right hook
			// family can be chosen from data.
			if (gEmergLog && m.flyoutId == 0x0992FD17)
			{
				static bool evtpDone = false;
				if (!evtpDone)
				{
					evtpDone = true;
					ChildSnapshot ek = {};
					win->EnumChildren(GZIID_cIGZWin, ChildSnapshot::Callback, &ek);
					for (int ei = 0; ei < ek.count; ei++)
					{
						cIGZWin* kw = ek.wins[ei];
						if (!kw) { continue; }
						Logger::Get().WriteLine(LogLevel::Debug,
							"UiSpike: EVTP child 0x%08X %dx%d vt=%p",
							kw->GetID(), kw->GetW(), kw->GetH(),
							*reinterpret_cast<void**>(kw));
					}
				}
			}
			// MCAL for the not-yet-derived ones: report native placement so the
			// offset can be measured instead of guessed.
			if (btn != nullptr && (!m.derived || gMayorDock == 0))
			{
				static int mcal2 = 0;
				if (mcal2 < 8)
				{
					mcal2++;
					int32_t bl = 0, bt = 0;
					AbsoluteTopLeft(btn, bl, bt);
					Logger::Get().WriteLine(LogLevel::Debug,
						"UiSpike: MCAL flyout=0x%08X native(%d,%d) %dx%d  "
						"button=0x%08X abs(%d,%d) %dx%d  R(%d,%d)  target(%d,%d)"
						" [MEASURING - not moved]",
						m.flyoutId, win->GetL(), win->GetT(),
						win->GetW(), win->GetH(),
						m.buttonId, bl, bt, btn->GetW(), btn->GetH(),
						win->GetL() - bl, win->GetT() - bt,
						bl + ScaleRound(win->GetL() - bl, f),
						bt + ScaleRound(win->GetT() - bt, f));
				}
			}
		}
	}

	for (const GodFlyoutDock& d : kGodFlyoutDock)
	{
		cIGZWin* win = flyouts.Next(d.id);
		if (!win || win->GetW() <= 0 || win->GetH() <= 0)
		{
			continue;
		}
		flyouts.Touched();
		PatchFlashGuardClass(*reinterpret_cast<void***>(win));

		// PRE-SCALE WHILE HIDDEN (v2.11.29) - the REGION-SCREEN fix, applied to
		// god flyouts. This is why they flashed: SIZE was gated behind
		// IsVisible(), so the game showed a 1x (or half-transformed) frame and
		// only the NEXT sweep grew it - the visible jump. The region panels
		// solved exactly this by scaling while hidden (see the sweep's
		// IsRegionPanelId exception: "pre-scaled while hidden so they appear
		// already at 2x (no visible jump when a flyout opens)"). So scale the
		// subtree UNCONDITIONALLY here, and gate only the DOCK MOVE on
		// visibility - a closed flyout must not be repositioned (docking a
		// closed terrain-fx on top of day/night is what broke them), but it can
		// absolutely be pre-sized. ScaleSubtree is idempotent via scaleMap, so
		// a hidden flyout is sized once and then costs nothing.
		int n = 0;
		ScaleSubtree(win, f, 0, &n, false);

		// MAYOR-MODE PATH (v2.13.0). If this flyout has a mayor entry AND the
		// mayor HUD is up, dock it against its own SPAWN BUTTON instead of the
		// god toolbar - see kMayorFlyoutDock. While the offset is not yet
		// derived (entry.derived == false) or MayorDock=0, do not move it at
		// all: report the GAME's native placement via MCAL so the offset can be
		// measured rather than guessed.
		const MayorFlyoutDock* md =
			mayorModeActive ? FindMayorDock(d.id) : nullptr;
		const bool mayorMeasuring = (md != nullptr && (!md->derived || gMayorDock == 0));
		const bool dockNow =
			!mayorMeasuring && !(d.gateVisible && !win->IsVisible());
		bool moved = false;
		if (dockNow)
		{
			// 0xCA35CBED: the shared terrain-fx/day-night window - pick its
			// offset from whichever tool is rendering through it (see above).
			// All other flyouts use their fixed table offset.
			int32_t offY = d.offY;
			if (d.id == 0xCA35CBED)
			{
				offY = dayNightActive ? kDayNightOffY : kTerrfxOffY;
			}
			int32_t targetL = tbLiveL + ScaleRound(d.offX, f);
			int32_t targetT = tbLiveT + ScaleRound(offY, f);
			// #198 DERIVE THE GOD DOCK FROM THE LIVE MARKER (2026-08-25).
			// User-reported: the god day/night ring sat low at BOTH 1.5x AND 2x.
			// A defect alive at an INTEGER factor cannot be offset-parity or any
			// snap/rounding artefact - those are no-ops at 2x by construction - so
			// what remains is a stock-derived CONSTANT scaled by f and applied to
			// geometry that is no longer stock: error 32*f, i.e. 48 px at 1.5x, 64
			// at 2x, 96 at 3x, invisible only at 1x where nothing of ours runs.
			//
			// *** THE CONSTANTS ABOVE **ARE** THE ALIGNMENT-MARKER RULE, precomputed
			// on stock. Reproduced 3/3 from raw bytes (god toolbar {0,96A006B0,
			// 69E3D347}, buttons at local l=10, t=10/70/130/190/250, BYTE-IDENTICAL
			// in stock and carbon):
			//     terraform  (10, 10) - marker (4,90) = ( 6, -80) == table row 1
			//     terrain-fx (10, 70) - marker (4,30) = ( 6,  40) == kTerrfxOffY
			//     day/night  (10,250) - marker (4,90) = ( 6, 160) == kDayNightOffY
			// So deriving the offset live is not a "false equivalence" with the
			// mayor path (the old comment below) - it is the SAME rule, recomputed
			// from the script that is actually loaded instead of the one loaded in
			// 2003. That comment's arithmetic objection was a slip: the markers
			// differ by 60 and the constants by 120, but the BUTTONS differ by 180,
			// and 180 - 60 = 120 exactly. REGRESSION.md already recorded this rule
			// reproducing all three locked god docks to the pixel.
			//
			// MEASURED under the Scoty Carbon Skin - TWO broken constants, not one:
			//   script            stock mk.t  live mk.t  table  derived  error@1.5x
			//   e9923283 terrafm      90          0       -80     +10    135 HIGH
			//   aaa44448 terrfx       30         30        40      40      0 (ctrl)
			//   aa356502 day/night    90        122       160     128     48 LOW
			// Correcting only day/night would have left the LARGER defect standing
			// on the same code path, from the same root cause.
			//
			// IDENTITY ON STOCK BY CONSTRUCTION: with an unmodded script the live
			// marker IS the stock marker, so the derived offset equals the table
			// value exactly and the LOCKED v2.7.25 docks cannot move. The table
			// remains the fallback whenever the marker is missing.
			if (gGodMarkerFix)
			{
				// Design-unit button positions inside the god toolbar. Same source
				// as the derivation above; carbon does not touch that script.
				int32_t btnL = -1, btnT = -1;
				if (d.id == 0x49923239)      { btnL = 10; btnT = 10; }
				else if (d.id == 0xCA35CBED) { btnL = 10; btnT = dayNightActive ? 250 : 70; }
				cIGZWin* mk = (btnT >= 0) ? win->GetChildWindowFromID(0x0000AAAA)
				                          : nullptr;
				if (mk != nullptr)
				{
					// The marker may hold DESIGN units (our subtree scale does not
					// reach an invisible child on some flyouts) or SCREEN units.
					// MarkerIsDesignUnits is the same normaliser the mayor path
					// uses; getting it wrong is a factor-sized error, not a nudge.
					const bool design = MarkerIsDesignUnits(mk, f);
					const float inv = (f > 0.01f) ? (1.0f / f) : 1.0f;
					const int32_t mkL = design ? mk->GetL() : ScaleRound(mk->GetL(), inv);
					const int32_t mkT = design ? mk->GetT() : ScaleRound(mk->GetT(), inv);
					const int32_t derivedX = btnL - mkL;
					const int32_t derivedY = btnT - mkT;
					const int32_t dx = derivedX - d.offX;
					const int32_t dy = derivedY - offY;
					if (dx != 0 || dy != 0)
					{
						targetL = tbLiveL + ScaleRound(derivedX, f);
						targetT = tbLiveT + ScaleRound(derivedY, f);
						if (MDockShouldLog(d.id ^ 0x40000000u))
						{
							Logger::Get().WriteLine(LogLevel::Info,
								"UiSpike: MFIX 0x%08X %ls marker %ls(%d,%d) -> derived "
								"offset (%d,%d) vs table (%d,%d); dock moved (%+d,%+d) "
								"design px (x%.2f). A mod moved this script's alignment "
								"marker, so the toolbar constant no longer describes it.",
								d.id,
								(d.id == 0x49923239) ? L"terraform"
									: (dayNightActive ? L"day/night" : L"terrain-fx"),
								design ? L"design" : L"screen", mkL, mkT,
								derivedX, derivedY, d.offX, offY, dx, dy, f);
						}
					}
				}
			}
			// #95 PHASE 1 - MARKER-DRIFT ALARM (diagnostic only, no behaviour).
			// The plan proposed converting THIS path to the live-marker rule
			// too. That premise did NOT survive the source: these offsets are
			// (flyoutStock - toolbarStock) from the vanilla capture and they
			// select by WHICH TOOL renders (offY 40 = terrain-fx ring btn2,
			// 160 = day/night ring btn5). They are TOOLBAR-anchored, not
			// -marker(1x), and the two scripts' markers differ by 60 while the
			// constants differ by 120 - so substituting the marker rule here
			// would move a LOCKED, user-verified god dock on a false equivalence.
			// What IS worth having is the alarm: if a mod ever replaces one of
			// these scripts, the marker moves and this path has no way to know.
			// So RECORD the drift and change nothing.
			if (gMDockAlarm)
			{
				cIGZWin* gmk = win->GetChildWindowFromID(0x0000AAAA);
				if (gmk != nullptr && MDockShouldLog(d.id ^ 0x80000000u))
				{
					Logger::Get().WriteLine(LogLevel::Info,
						"UiSpike: MDRIFT 0x%08X god-path marker live(%d,%d) "
						"design(%d,%d) f=%.2f - toolbar-anchored dock UNCHANGED "
						"by design; a live/design mismatch means a mod replaced "
						"this script and the constant no longer describes it.",
						d.id, gmk->GetL(), gmk->GetT(),
						ScaleRound(gmk->GetL(), 1.0f / (f > 0.01f ? f : 1.0f)),
						ScaleRound(gmk->GetT(), 1.0f / (f > 0.01f ? f : 1.0f)),
						f);
				}
			}
			// MAYOR: re-anchor onto the spawn button. Same shape as the god
			// formula, different anchor: button + ScaleRound(stockGlueOffset,f).
			bool mayorAnchorOk = true;
			if (md != nullptr && md->derived)
			{
				cIGZWin* btn = pView->GetChildWindowFromIDRecursive(md->buttonId);
				// #95 PHASE 4: a MISSING spawn button must mean NO MOVE. Before
				// this, targetL/T kept the GOD-TOOLBAR values computed above and
				// the flyout was moved there anyway - docking a mayor-mode
				// flyout against a toolbar that is not the one it spawned from.
				// The mayorOnly loop already behaves this way (moved stays
				// false); this makes the two paths agree.
				if (btn == nullptr) { mayorAnchorOk = false; }
				if (btn != nullptr)
				{
					int32_t bl = 0, bt = 0;
					AbsoluteTopLeft(btn, bl, bt);
					targetL = bl + ScaleRound(md->offX, f);
					targetT = bt + ScaleRound(md->offY, f);
					// v2.43.2 (task #94): SAME LIVE-MARKER RULE AS THE
					// mayorOnly LOOP. 0x49923239 (Landscape) never reaches
					// that loop - it is mayorOnly=false because it SHARES its
					// id with the god terraform flyout, so it is docked here,
					// on the god path's mayor branch. v2.43.1 fixed only the
					// other loop, which is exactly why Signs & Labels came
					// good and Landscape did not (log: MDOCK lines for
					// 0xAB954023 only, none for 0x49923239).
					cIGZWin* mk = win->GetChildWindowFromID(0x0000AAAA);
					if (mk != nullptr)
					{
						// v2.47.0: measure the marker's units, do not assume
						// them - THIS is the site that misdocked Landscape by
						// 59px onto the wrong circle. See MarkerIsDesignUnits.
						const bool mkDesign = MarkerIsDesignUnits(mk, f);
						const int32_t mkX = mkDesign
							? ScaleRound(mk->GetL(), f) : mk->GetL();
						const int32_t mkY = mkDesign
							? ScaleRound(mk->GetT(), f) : mk->GetT();
						const int32_t liveL = bl - mkX;
						const int32_t liveT = bt - mkY;
						if ((liveL != targetL || liveT != targetT)
							&& MDockShouldLog(d.id))
						{
							Logger::Get().WriteLine(LogLevel::Info,
								"UiSpike: MDOCK(god-path) 0x%08X live marker "
								"(%d,%d) units=%s -> used (%d,%d) -> (%d,%d) "
								"overrides table (%d,%d) - the live script "
								"differs from the one R was measured on (a mod "
								"replaced it). [mkW=%d btnW=%d]",
								d.id, mk->GetL(), mk->GetT(),
								mkDesign ? "DESIGN(scaled by us)" : "screen",
								mkX, mkY, liveL, liveT, targetL, targetT,
								mk->GetW(), btn->GetW());
						}
						targetL = liveL;
						targetT = liveT;
					}
				}
			}
			// MAYOR-MODE NUDGE (v2.12.4). Every offset in kGodFlyoutDock is
			// measured against the GOD toolbar 0xC991EDA8, because they were
			// derived pre-founding where these flyouts spawn from it. In a
			// FOUNDED city the terraform tool is not in god mode at all - it is
			// mayor mode's "Landscape Tools", spawned from the MAYOR toolbar
			// 0x69E40A1F, which sits at a different origin with a different
			// button pitch (100 vs 120). Docking against the hidden god toolbar
			// there puts the ring roughly one button ABOVE the button it should
			// circle. These are SCREEN px, live-tunable via ini [Flyout], and
			// apply ONLY in mayor mode so the pre-founding god docks - which are
			// verified and locked - are untouched.
			const int32_t curL = win->GetL();
			const int32_t curT = win->GetT();
			moved = mayorAnchorOk && (curL != targetL || curT != targetT);
			if (moved)
			{
				win->GZWinMoveTo(targetL - curL, targetT - curT);
			}
		}
		// MCAL - the measurement line. Logged OUTSIDE the dock branch so it also
		// fires while measuring (dock skipped), which is the whole point: it
		// reports where the GAME put the flyout relative to its spawn button.
		//   R      = native - buttonAbs   <- the stock glue offset, 1x units
		//   target = buttonAbs + f*R      <- what to put in kMayorFlyoutDock
		// Copy R straight into the table's offX/offY and set derived=true. No
		// screenshots, no eyeballing - the two numbers that produced today's
		// wrong Landscape values both came from reading a ring off a screenshot.
		if (md != nullptr)
		{
			static int mcalLogged = 0;
			cIGZWin* btn = pView->GetChildWindowFromIDRecursive(md->buttonId);
			if (btn != nullptr && mcalLogged < 12)
			{
				mcalLogged++;
				int32_t bl = 0, bt = 0;
				AbsoluteTopLeft(btn, bl, bt);
				const int32_t rx = win->GetL() - bl;
				const int32_t ry = win->GetT() - bt;
				Logger::Get().WriteLine(LogLevel::Debug,
					"UiSpike: MCAL flyout=0x%08X native(%d,%d) %dx%d  "
					"button=0x%08X abs(%d,%d) %dx%d  R(%d,%d)  target(%d,%d)%s",
					d.id, win->GetL(), win->GetT(), win->GetW(), win->GetH(),
					md->buttonId, bl, bt, btn->GetW(), btn->GetH(),
					rx, ry,
					bl + ScaleRound(rx, f), bt + ScaleRound(ry, f),
					mayorMeasuring ? " [MEASURING - not moved]" : " [DOCKED]");
			}
		}
		if (moved || n > 0)
		{
			// REPAINT. Resizing/moving only changes geometry - the game keeps
			// rendering the STALE paint until something invalidates the window.
			// That is why the flyout appeared at 1x on open and only snapped to
			// 2x once the mouse hovered it (the hover invalidated it for us).
			// Force it ourselves so the very first frame draws scaled.
			win->InvalidateSelfAndParents();
			Logger::Get().WriteLine(
				LogLevel::Info,
				"UiSpike: god flyout 0x%08X at(%d,%d) size %dx%d, +%d win%s%s.",
				d.id, win->GetL(), win->GetT(), win->GetW(), win->GetH(), n,
				moved ? " (moved)" : "",
				dockNow ? "" : " [PRE-SCALED while hidden]");
		}
		AddReadyWin(win);
		// DIAGNOSTIC (kept for ongoing god-flyout work): log each flip of the
		// active-tool signal. dayNightActive=1 -> offY 160 (day/night btn5);
		// =0 -> offY 40 (terrain-fx btn2). Fires on change only - no spam.
		if (d.id == 0xCA35CBED)
		{
			static int lastDn = -1;
			const int nowDn = dayNightActive ? 1 : 0;
			if (nowDn != lastDn)
			{
				lastDn = nowDn;
				Logger::Get().WriteLine(
					LogLevel::Debug,
					"UiSpike: DIAG dayNightActive %d -> 0xCA35CBED offY %d, liveT=%d.",
					nowDn, nowDn ? kDayNightOffY : kTerrfxOffY, win->GetT());
			}
		}
	}

	// DISASTER (Create Disasters, btn4). The REAL flyout is an ANONYMOUS
	// (id==0) direct child of the god-flyout parent 0x9A47B417, holding the
	// orange bar/ring + the thumbnail scroll strip. (0x0A78827A - which
	// FINDINGS.md mislabels "Disaster flyout" - is a HIDDEN vis=0 strip, so
	// docking or scaling THAT changes nothing on screen.)
	// Per the vanilla rule the game already places a god flyout against its
	// spawn button, so we do NOT move it - we only SCALE it. Two separate
	// things had been silently defeating that, both handled here:
	//   1. STALE RECORD - this window's pointer often carries a leftover
	//      scaleMap entry from an earlier id==0 window. Classify() then says
	//      Unrecognized and ScaleSubtree no-ops (the "+0 win" in the DIAG).
	//      Evict its records first so the scale actually runs.
	//   2. STALE PAINT - resizing only changes geometry; the game keeps
	//      drawing the OLD bitmap until something invalidates it, which is
	//      exactly why it only snapped to 2x after the mouse hovered it.
	//      InvalidateSelfAndParents() makes the very first frame draw scaled.
	// DISASTER (btn4) - DOCK ONLY, derived by analogy with the working
	// TERRAIN-FX flyout (measured side-by-side 2026-07-24):
	//   TERRAIN-FX root 0xCA35CBED  abs(22,502)  offset (6, 40) -> ring on btn2
	//   DISASTER   root 0x00000000  abs(126,518) <- 104px too far RIGHT
	// Both roots are DIRECT children of the god-flyout parent 0x9A47B417, so
	// they dock the same way; disaster's is just anonymous (no id), which is
	// why it must be found structurally. Terrain's ring sits ~60px below its
	// root top, so for the ring to land on btn4 (Y802) the root wants Y742:
	//   offX 6  -> tbLiveL(10) + 12  = 22   (same column as terrain-fx)
	//   offY 160 -> tbLiveT(422) + 320 = 742 (btn4 row)
	// NO ScaleSubtree here: at depth>0 it doubles child POSITIONS, which flings
	// this flyout's thumbnail strip and bar off to the right. Position first;
	// scaling needs a size-only-in-place mechanism (separate phase).
	// *** DISABLED during Phase 1/2 (DPROBE identification). ***
	// Any dock we apply here shows up in the probe as OUR movement and masks
	// the game's own open/settle/hover behaviour - which is precisely the
	// signal we need to separate the circle, bar and pictures. Re-enable only
	// once the three elements are identified (Phase 3), and then dock each
	// element individually rather than dragging this container.
	// DISASTER dock (btn4). Re-enabled 2026-07-25 with a DERIVED offset, once
	// DPROBE proved the container is a STATIC window at abs(126,518) and moving
	// it moves the whole orange flyout 1:1 (the rendered frame is GPU-only and
	// can't be pixel-measured - see GOD-MODE-FLYOUTS.md).
	//   Derivation (matches the working terrain-fx method, NOT eyeballed):
	//   toolbar abs(10,422), 120px 2x button pitch -> btn4 centre (104,860).
	//   terrain-fx docks (22,502), arm on btn2 centre 620 -> arm is 118px below
	//   the flyout top. So for the arm to land on btn4 (860): top = 742, same
	//   left column X=22 -> toolbar offset (6,160). Vector from raw (126,518):
	//   down 224, left 104 = the player's "down + slightly left" arrow, and the
	//   terraform-on-btn1 relationship the player set as the acceptance test.
	// NO ScaleSubtree (it doubles child positions and flings the strip); dock
	// first, scale later.
	// pView itself - the same self-lookup as the DPROBE root above (audit A1).
	cIGZWin* godParent = SelfLookup(pView, 0x9A47B417);
	if (godParent)
	{
		ChildSnapshot snap = {};
		godParent->EnumChildren(GZIID_cIGZWin, ChildSnapshot::Callback, &snap);
		// FLASH GUARD: one-time runtime proof that the header's GetParentWin
		// slot is right - a known (parent,child) pair from this enumeration
		// must round-trip. Until this passes, the guard stays inert (paints
		// pass through), so a wrong slot can never crash or blank anything.
		if (!gFgParentOk && snap.count > 0 && snap.wins[0])
		{
			cIGZWin* p = snap.wins[0]->GetParentWin();
			if (p == godParent || (p && p->GetID() == 0x9A47B417))
			{
				gFgParentOk = true;
				Logger::Get().WriteLine(LogLevel::Info,
					"UiSpike: DFG GetParentWin verified (child %p -> parent %p) "
					"- flash guard ACTIVE", (void*)snap.wins[0], (void*)p);
			}
			else
			{
				static bool warned = false;
				if (!warned)
				{
					warned = true;
					Logger::Get().WriteLine(LogLevel::Info,
						"UiSpike: DFG GetParentWin MISMATCH (got %p, want %p) - "
						"flash guard stays OFF", (void*)p, (void*)godParent);
				}
			}
		}
		// FLASH GUARD: arm EVERY god-flyout child class now, while they are
		// still closed. Classes discovered only at open-time are hooked one
		// frame too late - that frame is the flash.
		for (int j = 0; j < snap.count; j++)
		{
			if (snap.wins[j])
				PatchFlashGuardClass(*reinterpret_cast<void***>(snap.wins[j]));
		}
		// Per-open dump of ALL god-parent children (id+rect+vis) in enum order
		// (= routing/z-order), captured WHILE the flyout is open, to find the
		// sibling covering screen ~190..239 on top of our container. The old
		// one-shot fired at city load, before the flyout existed, and saw
		// nothing. gpdumped re-arms when the container disappears (flyout
		// closed) so every open produces one fresh dump.
		static bool gpdumped = false;
		bool contFound = false;
		for (int i = 0; i < snap.count; i++)
		{
			cIGZWin* c = snap.wins[i];
			// id==0 + DIRECT child of 0x9A47B417 + tall + visible uniquely
			// identifies it (terrain-fx's own anonymous arm child is nested
			// under 0xCA35CBED, so it is never enumerated here).
			if (!c || c->GetID() != 0 || !c->IsVisible()
				|| c->GetH() < 400 || c->GetW() < 150 || c->GetW() > 900)
			{
				continue;
			}
			contFound = true;
			if (gStripDump && !gpdumped)
			{
				gpdumped = true;
				Logger::Get().WriteLine(LogLevel::Debug,
					"UiSpike: DGP-OPEN godParent has %d children, container=idx %d "
					"rect(%d,%d %dx%d)", snap.count, i,
					c->GetL(), c->GetT(), c->GetW(), c->GetH());
				for (int j = 0; j < snap.count; j++)
				{
					cIGZWin* k = snap.wins[j];
					if (!k) continue;
					const int32_t kl = k->GetL(), kt = k->GetT();
					const int32_t kw = k->GetW(), kh = k->GetH();
					// Flag any sibling whose rect overlaps the DEAD BAND: the
					// container-local strip x 190..239 (the left, unclickable
					// half of the pictures) at the picture rows.
					const int32_t dbL = c->GetL() + 190, dbR = c->GetL() + 239;
					const bool overBand = k != c && k->IsVisible()
						&& kl < dbR && (kl + kw) > dbL
						&& kt < (c->GetT() + c->GetH()) && (kt + kh) > c->GetT();
					Logger::Get().WriteLine(LogLevel::Debug,
						"UiSpike: DGPKID %d id=%08X L=%d T=%d W=%d H=%d vis=%d%s%s",
						j, k->GetID(), kl, kt, kw, kh,
						k->IsVisible() ? 1 : 0,
						(j == i) ? " <==CONTAINER" : "",
						overBand ? " **OVER-DEAD-BAND**" : "");
				}
				// LEVEL 2: the container's OWN children, in enum order = the
				// [this+0x44] list order the router (0x0099DFA9) walks. The
				// router gives the point to the FIRST visible child without
				// flag 0x200000 that claims it - so whichever child here spans
				// the dead band x 190..239 AHEAD of the strip (vt 0x00AB6D88)
				// is the click thief. Log each child's vtable + the two flags
				// the router reads (1=visible, 0x200000=input-transparent) +
				// 0x80000 (MouseTrans, selects the refined-mask branch).
				typedef bool(__fastcall* FlagFn)(void*, void*, uint32_t);
				ChildSnapshot cc = {};
				c->EnumChildren(GZIID_cIGZWin, ChildSnapshot::Callback, &cc);
				Logger::Get().WriteLine(LogLevel::Debug,
					"UiSpike: DCKIDS container has %d children (router order, "
					"first claim wins)", cc.count);
				for (int j = 0; j < cc.count; j++)
				{
					cIGZWin* k = cc.wins[j];
					if (!k) continue;
					void** vt = *reinterpret_cast<void***>(k);
					FlagFn gf = reinterpret_cast<FlagFn>(vt[67]);
					const bool fVis  = gf(k, nullptr, 1);
					const bool fThru = gf(k, nullptr, 0x200000);
					const bool fMT   = gf(k, nullptr, 0x80000);
					const int32_t kl = k->GetL(), kw = k->GetW();
					// dead band: strip-local left half, abs x 190..239
					const bool overBand = kl < 239 && (kl + kw) > 190;
					Logger::Get().WriteLine(LogLevel::Debug,
						"UiSpike: DCKID %d id=%08X L=%d T=%d W=%d H=%d vt=%p "
						"vis=%d thru=%d mt=%d%s%s",
						j, k->GetID(), kl, k->GetT(), kw, k->GetH(), vt,
						fVis ? 1 : 0, fThru ? 1 : 0, fMT ? 1 : 0,
						(vt == gVtCopy2
							|| vt == reinterpret_cast<void**>(0x00AB6D88))
							? " <==STRIP" : "",
						overBand ? " **OVER-DEAD-BAND**" : "");
				}
			}
			// Dock the container: toolbar-live + DockX/DockY, the accepted
			// scheme. (The v4.0.10-12 target derived from the game's stock
			// glue moved the RING off its button; retired v4.0.13.)
			const int32_t targetL = tbLiveL + ScaleRound(DisDockXEff(), f);   // v2.10: live-tunable (ini [Disaster] DockX)
			const int32_t targetT = tbLiveT + ScaleRound(DisDockYEff(), f);   // v2.11.30: live-tunable (ini [Disaster] DockY)
			// v2.39.5: the gDisDock cache write that lived here moved UP to
			// right after tbLiveL/T are read (before the flyout even exists).
			// Writing it only here was the first-open hole: the cache could
			// only warm while the flyout was OPEN, so dock-at-birth never
			// fired on open 1 of a session (measured 2026-07-31). This block
			// is now the FALLBACK for a cold cache (ini mid-session edits,
			// BornDock=0), and its move below is a no-op when birth docked.
			const int32_t cl = c->GetL();
			const int32_t ct = c->GetT();
			if (cl != targetL || ct != targetT)
			{
				c->GZWinMoveTo(targetL - cl, targetT - ct);
				c->InvalidateSelfAndParents();
			}

			// v2.11.24 CLAIM FIX: the container's custom hit-claim (slot 121,
			// 0x0079AE30) accepts only x >= width - [this+0xe0] - the rightmost
			// [0xe0] px = the strip column as width-from-right-edge. It held the
			// 1x width while the draw went 2x, killing routing for the pictures'
			// left half (and starving the strip's slot 62/149 hooks). Scale it.
			// Sane-range guard (30..60 = plausible 1x values) makes the write
			// idempotent AND self-healing if the game recomputes the field.
			if (gClaimScale > 1)
			{
				int32_t* claimW = reinterpret_cast<int32_t*>(
					reinterpret_cast<char*>(c) + 0xE0);
				if (*claimW >= 30 && *claimW <= 60)
				{
					// v2.24.0 (audit A6): tier-factor scale + 1x latch, exactly
					// like the SUBCLAIM write above. f=2 identical to oldW*2.
					const int32_t oldW = *claimW;
					gClaimOrig = oldW;
					*claimW = RoundHalfUp(oldW * gTierF);
					Logger::Get().WriteLine(LogLevel::Debug,
						"UiSpike: DCLAIM container [0xe0] %d -> %d "
						"(claim band now rightmost %d px of %d).",
						oldW, *claimW, *claimW, c->GetW());
				}
			}

			// NOTE (v2.7.75): window SetW/SetH scaling REVERTED. It caused
			// regressions (ring disappeared, bar stretched, strip flew right)
			// because the painted art uses hardcoded 1x pixel offsets that
			// don't follow the window rect. The CAA hook also failed:
			// CalcAbsoluteArea returns 0x06752001 (a packed value, not a
			// rect pointer). Binary-patching Plot() is the next approach.

			// COMMENT CORRECTED v2.39.5 (the old text here was the premise
			// v2.39.4 was mis-reasoned from). It said "until both vtable
			// swaps are in, every paint stays suppressed" - FALSE since
			// v2.11.28: the suppression is behind gFlashGuard, which
			// defaults 0 and is BANNED from being re-enabled (:219-227).
			// Nothing is ever suppressed; the first frames of a session's
			// first open genuinely paint uncorrected chrome, which is why
			// the birth path now installs the class Blt hook itself.
			// This gate only means "the sweep's hooks are live on this
			// container" - AddReadyWin is bookkeeping for the dormant guard.
			if (*reinterpret_cast<void***>(c) == gVtCopy && gOrigSlot2[88])
			{
				AddReadyWin(c);
				// v2.39.4's DIAGNOSIS WAS WRONG (measured 2026-07-31,
				// session 17:21): this repaint fired correctly, once, and the
				// arrow stayed missing - even after a hover repaint with all
				// hooks live. The arrow was never "unpainted": the container's
				// Plot READS byte flags [0x118]/[0x119] to choose plain-cap vs
				// arrow-cap atlas cells, and the open flow had computed
				// "nothing to scroll" from MIXED units (2x strip window, 1x
				// item pitch), so the flags were 0 and no repaint could help.
				// Real cure: born item metrics in SubPlaceDetour (v2.39.5).
				// TRIAGE rule: a stale frame that survives a REPAINT is a
				// stale DECISION - check what the draw computes from.
				//
				// This one-shot stays: it is still the correct belt-and-braces
				// for the first frames painted before the sweep's vtable
				// swaps, and it is a FORCED REPAINT, never paint suppression.
				//
				// ONE-SHOT PER CONTAINER. This block runs on EVERY sweep tick
				// while the flyout is open - 809 times in the measured session -
				// so an unlatched invalidate would repaint the flyout ~60x a
				// second for as long as it is on screen.
				if (c != gDisChromeHealed)
				{
					gDisChromeHealed = c;
					// v2.39.7: SET THE REDRAW DIRTY BIT FIRST. The container's
					// draw (0x79B0E8) tests byte [0x114] bit 0 and takes the
					// pure re-BLIT path when clear - an invalidate alone shows
					// the STALE CACHED BUFFER again, healing nothing. The
					// game's own hover/press handlers always do BOTH
					// (0x79AF02 `or [ecx+0x114],1` then the invalidate), and
					// we already follow that protocol at the two SUBHEAL
					// sites. Same one-shot latch; only the re-blit became a
					// re-draw.
					reinterpret_cast<uint8_t*>(c)[0x114] |= 1;
					c->InvalidateSelfAndParents();
					Logger::Get().WriteLine(
						LogLevel::Info,
						"UiSpike: DISHEAL chrome live - one forced REDRAW "
						"(dirty bit + invalidate) so first-frame chrome heals "
						"without user input.");
				}
			}

			// v2.39.5: log on the OPEN and on any actual move only. This line
			// used to print unconditionally every sweep tick - 867 lines in
			// one 23s open (measured) - which buried the signal it carries.
			// (cl,ct) were read BEFORE the fallback move above, so a printed
			// mismatch vs dock() shows exactly what the fallback corrected;
			// birth-docked opens print one line with cl==targetL, ct==targetT.
			if (c != gDisDockLogged || cl != targetL || ct != targetT)
			{
				gDisDockLogged = c;
				Logger::Get().WriteLine(
					LogLevel::Info,
					"UiSpike: disaster flyout (anon) %dx%d (%d,%d) -> dock(%d,%d).",
					c->GetW(), c->GetH(), cl, ct, targetL, targetT);
			}
			break;
		}
		if (!contFound)
		{
			gpdumped = false;   // flyout closed -> next open dumps again
			gDisDockLogged = nullptr;   // next open logs its dock line again
		}
	}
}
