////////////////////////////////////////////////////////////////////////////
//
// UiSpike - research spike for the UI-scaling northstar:
// SC4 at native high resolution with the UI ELEMENTS drawn larger.
//
// Hard-won rules encoded here (probed on the real 1.1.641 binary):
//  - PROVEN SAFE cIGZWin calls: GetID, GetChildCount, GetW/GetH/GetL/GetT,
//    EnumChildren (callback convention correct), GetChildWindowFromID(Rec).
//  - PROVEN WRONG: the paired GetArea/GetAreaAbsolute overload slots (MSVC
//    lays overloaded virtuals out in REVERSE declaration order; the
//    community header does not account for it). Never call them; the
//    single-name getters provide the full rect. For resizing, use SetW/SetH
//    (single-name slots) - avoid the SetArea overload pair.
//  - Running the tree walk inside the PostCityInit message HANGS the game.
//    The walk must run deferred, several seconds after city init, from the
//    subclass timer on an idle UI thread.
//  - Scaling is IDEMPOTENT per window: scaleMap records original + scaled
//    geometry, so re-running ScaleAll (second city load) is harmless whether
//    the game persists or recreates its UI windows. Never clear the records
//    between cities.
//
////////////////////////////////////////////////////////////////////////////

#include "UiSpike.h"

#include "Logger.h"
#include "cIGZBuffer.h"
#include "cIGZGraphicSystem.h"
#include "GZServPtrs.h"
#include "cIGZFrameWork.h"
#include "cRZCOMDllDirector.h"
#include "ScaleTier.h"   // the selector greys out tiers this resolution cannot carry
#include "CodePatches.h"  // v2.37.0 #78: is the Data Views legend born correct?
#include "SpinProbe.h"    // #107: per-launch outcome recorder (was Budget opened?)

#include "cIGZWin.h"
#include "cIGZString.h"
#include "cIGZWinText.h"
#include "cIGZWinBtn.h"     // in-game scale selector: radio state
#include "cIGZWinCombo.h"   //   ... the tier picker
#include "cIGZWinGen.h"     //   ... SetWinProc/GetWinProc on the dialog
#include "cIGZWinProc.h"    //   ... the chained click handler
#include "cGZMessage.h"
#include "cRZBaseString.h"
#include "cIGZBuffer.h"
#include "cIGZFont.h"      // v2.28.0: measure + break the popup description
#include "cIGZFontSys.h"   //          ourselves (the engine never re-wraps)
#include "cISC4App.h"
#include "GZServPtrs.h"
#include "MinHook.h"   // v2.32.0 SHOWHOOK: trampoline on cGZWin::SetFlag

#include <cmath>
#include <cstdlib>     // atoi (live-tune ini re-read)
#include <intrin.h>   // _ReturnAddress (sub-flyout twin guard)
#include <cstring>     // strchr/strlen (popup wrap idempotence)
#include <cstdio>      // _snprintf_s (the DVLEG legend read-back line)
#include <string>      // the wrapped caption we build
#include <set>         // #188 SMALLWIN per-epoch dedupe
#include <Windows.h>   // SEH guard for probing hook return values

// The live-tune re-read below used a HARDCODED absolute path to this dev
// box's Plugins folder. On any other machine that read silently returns
// nothing, so every [Disaster] value falls back to its COMPILED default -
// which are the pre-fix values (RingDY -27, DockY 130, LayerFix 1,
// ClaimScale 0, SelForce 0): the shipped flyout would have no click fix, the
// wrong dock and the junction gap. The ini lives beside this DLL (both are
// installed into the Plugins folder), so resolve it from our own module path
// exactly like the director does for the ini/log it loads at startup.
extern "C" IMAGE_DOS_HEADER __ImageBase;

namespace
{
	// Resolved once; the DLL cannot move while loaded.
	const char* LiveTuneIniPath()
	{
		static char s_path[MAX_PATH] = {};
		if (!s_path[0])
		{
			char dir[MAX_PATH] = {};
			GetModuleFileNameA(reinterpret_cast<HMODULE>(&__ImageBase), dir, MAX_PATH);
			char* lastSlash = strrchr(dir, '\\');
			if (lastSlash) { *(lastSlash + 1) = '\0'; }
			sprintf_s(s_path, "%sSC4UIScale.ini", dir);
		}
		return s_path;
	}
}

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
// ⛔ CORRECTED 2026-08-14 (#149) - THE LINE ABOVE IS WRONG FOR BUILD
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
	// ⚠ THE SLOT TABLE BELOW WAS OFF BY ONE UNTIL 2026-08-01, and it also
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

	// ---- TIER MATH (v2.24.0 tier-generality pass, audit 2026-07-29) -------
	// Every 2x-hardwired constant in the hooks below became its derived form;
	// at f=2 each form reduces EXACTLY to the old constant (identity table in
	// tools\research\_checkpoints\tier-math-fixes.md + _tests\REGRESSION.md).
	//
	// gTierF mirrors settings.spikeScaleFactor for these namespace-scope
	// hooks (settings is a UiSpike member and invisible here). Default 2.0f =
	// the legacy compiled assumption.
	// ⚠ CORRECTED 2026-08-01 (SDK-law audit): this comment used to claim
	// "hooks are only ever installed BY those sweeps", which has been false
	// since v2.32.0 - ArmDeferred installs four at PostCityInit, BEFORE any
	// sweep has written gTierF. Anything running from those hooks before the
	// first pass therefore sees the COMPILED DEFAULT, not the live tier -
	// which is why EarlyDockTick deliberately uses settings.spikeScaleFactor
	// and not gTierF. Consult the tier from settings in pre-sweep code.
	// ⛔ IDENTITY DEFAULT, NOT 2.0f. This was `= 2.0f` and that is a LIE
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
	// ⭐ A DEFAULT THAT IS NOT THE IDENTITY TURNS "NOT YET KNOWN" INTO A
	// CONFIDENT WRONG ANSWER. 1.0f means "no scaling" - the only safe thing to
	// believe before the tier is decided. The real value is now pushed in
	// UNCONDITIONALLY by SetTierMirror() at the moment the tier is resolved,
	// so this initialiser should never be the value anything actually uses.
	float gTierF = 1.0f;

	// Round-half-up (floor(v + 0.5)) - the SAME rounding rule as the whole
	// art pipeline (Upscale2x.exe dimensions, the .UI builders' scale_len),
	// so runtime geometry and shipped art can never disagree by a rounding
	// rule. NOTE: differs from llround/ScaleRound only at NEGATIVE half
	// values (-49.5 -> -49 here, -50 there); the art pipeline convention
	// wins for all tier-math forms.
	inline int32_t RoundHalfUp(double v)
	{
		return static_cast<int32_t>(std::floor(v + 0.5));
	}

	// ⛔ A BLIT EXTENT MUST FLOOR, NEVER ROUND UP.
	//
	// THE DEFECT (user-reported 2026-08-06, and the wording is the diagnosis):
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
	// ⚠ WHY 2x AND 3x ARE PERFECT, AND WHY THIS IS 1.5x-ONLY: at an integer
	// factor srcExtent*f is already whole, so floor and round agree exactly and
	// no phantom column can exist. Same shape as #142 (font point sizes) and
	// the strip step-extra (5*1.5 = 7.5): a rule that only misbehaves where the
	// product is fractional. Integer tiers are BIT-IDENTICAL under this change.
	//
	// ⚠ MEASURED DEAD, DO NOT RETRY: the first attempt at this symptom rewrote
	// the SAMPLER to map by the real size ratio (o*src/dst, the Upscale2x
	// method). It compiled, shipped, and the user reported it made "a lot of
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
	int gPaintHits = 0;
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
	PtInFn  gOrigSlot149 = nullptr;
	int     gSelForce = 0;
	// Slot 62 IsPointInMe (0x0099C97C, base, 2-arg): the routing's actual
	// "is the cursor in the strip" test. Log its (x,y)+answer for left vs right
	// hovers to resolve why only the right half routes here.
	PtInFn  gOrigSlot62 = nullptr;
	// Slot 59 [vt+0xec] WindowToScreenCoordinates(int32&x, int32&y): the coord
	// transform IsPointInMe runs on the cursor before the rect test. Log in->out
	// to MEASURE the ~45px offset that shifts the hit-test right of the draw.
	typedef bool(__fastcall* XformFn)(void*, void*, int32_t*, int32_t*);
	XformFn gOrigSlot59 = nullptr;
	int     gStripForceX = 0;         // if >0, force the click X passed to the list's
	                                  // GZOnMouseDownL to this value, so a click
	                                  // anywhere in the 2x cell registers as a hit
	                                  // (the FIX, once the diagnostic confirms the list
	                                  // handler is what rejects the left half).
	int     gClickHook = 0;           // 0 = do NOT install the 120/121/133 click hooks
	                                  // (SDK vtable slot numbers past ~97 may not match
	                                  // the game and CRASHED). Only enable once the DVT
	                                  // dump verifies the real GZOnMouseDownL slot.
	int     gMouseSlot = 133;         // vtable slot to hook as GZOnMouseDownL (SDK says
	                                  // 133; override via ini once verified).
	// THE CLICK GATE (v2.11.24, found by full offline disasm): the CONTAINER
	// overrides IsPointInMe (0x0079A180) to tail-call its slot 121 (0x0079AE30),
	// which claims the point ONLY when x >= (width - [this+0xe0]) - i.e. the
	// RIGHTMOST [0xe0] px = the strip column, stored as width-from-right-edge.
	// [0xe0] still holds the 1x strip width (~44/49) while the draw is 2x, so
	// routing dies at the container for the left half of the pictures - which
	// is also why the strip's DS62/DS149 hooks stayed silent there. Fix: scale
	// [0xe0] by gClaimScale (2 = double). Idempotent via a sane-range guard;
	// if the game recomputes the field back to 1x, the sweep re-applies it.
	int     gClaimScale = 0;          // 0/1 = off; >1 = scale [container+0xe0] by the
	                                  // TIER factor (v2.24.0: the ini value is an
	                                  // ENABLE flag now, not the multiplier - atoi
	                                  // of "1.5" is 1, so an integer multiplier
	                                  // could never be fractional; audit A6)
	int32_t gClaimOrig = 0;           // the 1x claim width we scaled (latched by the
	                                  // sweeps); the draw group restores exactly this
	                                  // value instead of dividing by an int factor
	// FLASH GUARD (v2.11.26): the user must NEVER see the stock 1x (or half-
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
	unsigned gTalSkip  = 0;   // ... that we left alone
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

	// ⛔ THE FIRST VERSION OF THIS CRASHED THE GAME (PRIV_INSTRUCTION at a
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
	void* gS20Rect = nullptr;
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
	                                  // clicks. Superseded by the data
	                                  // pre-scale (kDataScaledSubtreeIds),
	                                  // which needs no injected input and has
	                                  // no visible flash. Kept as an escape
	                                  // hatch if that ever regresses.

	// MAYOR-mode flyout docking (kMayorFlyoutDock), ini [Flyout] MayorDock.
	// 0 = MEASURE: never move a mayor flyout, just report its native placement
	// and the derived offset via the MCAL log line. 1 = apply the dock for
	// entries whose offsets have been measured (derived=true).
	// Superseded LandDX/LandDY/LandDock, which were screenshot-tuned nudges
	// layered on the WRONG anchor (the god toolbar) - see kMayorFlyoutDock.
	// #95 PHASE 4 (2026-08-02): DEFAULT FLIPPED 0 -> 1. Every row in
	// kMayorFlyoutDock is derived=true and has been user-confirmed, and
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

	// ---- #92: THE LIFECYCLE EPOCH (v2.47.1) ---------------------------
	// Disarm() clears the tracking state between cities, but three latches
	// live as FUNCTION-LOCAL STATICS inside HookDashboardGauges - declared
	// far below Disarm, so it cannot reach them - and they are keyed on the
	// dashboard's POINTER: lastDashRoot, scanRoot, scanCount. If a second
	// city's dashboard is allocated at the SAME address as the first's
	// (ordinary heap reuse, and these are large short-lived objects), the
	// `pDash != lastDashRoot` test reads FALSE for a genuinely new object,
	// so the re-hook and the GAUGESCAN survey are both SILENTLY SKIPPED and
	// the second city's gauges are never hooked. Nothing logs, because the
	// code believes it already did the work - the same address-reuse shape
	// that scaleMap defends against with an ID check.
	//
	// A monotonic epoch is the fix: Disarm bumps it, the hook notices its
	// own epoch is stale and drops the latches. Monotonic rather than a
	// dirty flag so a double Disarm, or a Disarm racing a sweep, cannot
	// leave it stuck - there is no state to get wrong, only a number to
	// compare.
	int     gGaugeEpoch = 0;

	// #93: one-shot latch for the UDVAR sighting line. Cleared in Disarm so a
	// SECOND city re-reports (second-city law - a latch that survives a city
	// change is how #92 hid, and this one exists precisely to catch a rare
	// event we have never observed).
	bool    gUdVarSeen = false;

	// #57: CHARTGEO one-shot counter (4 lines max, read-only probe).
	int     gChartGeoLog = 0;

	// ---- #57 PHASE 1: THE REPAINT PROOF. ini [Flyout] ChartProbe, default 0
	// ⚠ THIS DELIBERATELY DEFACES THE CHART: it floods the plot area opaque
	// green. It is a DIAGNOSTIC, not a fix, and it is two field writes plus
	// one virtual call - ChartProbe=0 and a restart undoes it completely.
	//
	// WHY THIS AND NOT ANOTHER LAYOUT TWEAK (law 46). Three builds moved
	// layout values and NOTHING moved on screen, every write provably
	// landing. The offline disassembly then found what all three missed:
	//   * the painters DO read chart+0xE0 directly - sub_9B3994 passes that
	//     exact address to device->FillRect and to the frame call, and
	//     sub_9B2365 / sub_9B43C6 read it too. So "they read a stale copy"
	//     is REFUTED, which leaves only: THE PAINTERS NEVER RAN.
	//   * the chart's paint core sub_9B2431 has NO dirty flag - the gate is
	//     one level up in the generic driver sub_99E62D (vt+0x1EC):
	//         cmp byte [ebx+0x70], 0 / je   -> skip self-draw entirely
	//     cIGZWin+0x70 is the dirty byte, cleared after a paint only when
	//     +0x64 (an optional offscreen surface) is non-zero.
	//   * InvalidateSelfAndParents was never the right call. The game's own
	//     idiom is vt+0x170 (sub_99BED1) = SetDirty AND propagate up the
	//     ancestor chain; every chart mutator ends with it, including the
	//     panel builder at 0x76D5C7. The chart does not override it, so it
	//     cannot clobber anything we wrote.
	//
	// THE DISCRIMINATOR, COMMITTED BEFORE THE BUILD (per #47):
	//   GREEN BOX  -> repaints work AND chart+0xE0 is live. The only thing
	//                 left is WHICH VALUES we compute -> phase 2.
	//   NO GREEN   -> the window never reaches the draw. Do NOT try another
	//                 field. Next is the +0x64 offscreen surface and the
	//                 pbuff question (the v2.25.14 gauge precedent, where
	//                 the cure was born-2x DATA, not repaints).
	// ⛔ Proving it with an absurd rect at +0xE0 is worthless: that is the
	//    write that already failed, so it cannot separate "no repaint" from
	//    "field ignored". A colour CAN.
	int     gChartProbe = 0;
	// #57 v2.55.0: the byte patch is process-wide and idempotent, but the
	// applier walks 8 sites and logs, so latch it. NOT cleared by Disarm -
	// unlike the pointer-keyed latches this is keyed to the PROCESS, and a
	// second city must not re-run a patch whose stock bytes are gone.
	bool    gGraphBudgetArmed = false;
	cIGZWin* gChartProbed = nullptr;   // once per object; cleared in Disarm
	int     gChartScaleLog = 0;        // CHARTSCALE lines, 8 max per city

	// ---- #57 v2.54.0: EARLYCHART - the chart is BORN correct, no jump ----
	// USER REQUIREMENT: "we simply cannot have a jump". The sweep fixup runs
	// at 16ms but the chart PAINTS STOCK IN ITS CREATION FRAME, so a 1-2
	// frame BIG->resized snap was visible on every graph switch. Cadence can
	// never fix that; only born-correct can (the #89 EARLYDOCK law: scale
	// and first paint must be ONE action).
	// THE SEAM, measured: the layout driver sub_9B3647 computes the plot
	// rect DURING the first paint (sub_9B2431 calls it before any painter)
	// and stores it through ONE vtable slot - iface vt+0x30 = sub_9B1F1D,
	// 18 bytes, one call site. Detour THAT SLOT and the margins are scaled
	// in the very same paint that first draws the chart: no stock frame ever
	// reaches the screen.
	// VERIFIED OFFLINE (2026-08-03): slot +0x30 holds 0x9B1F1D in the type1
	// (0xAB4C28) and type2 (0xADE568) iface vtables; type3 (0xADEDE0)
	// OVERRIDES it with 0x9B2F92 and is deliberately NOT patched - verify-
	// before-write, and our live Graphs chart is type1 (every CHARTGEO line
	// says vt=00AB4D08). The sweep-block fixup stays as the fallback; its
	// bandH==32 marker makes it inert on charts this thunk already handled.
	uintptr_t gChartStoreReal = 0;    // rebased 0x9B1F1D
	int       gChartBornLog = 0;      // EARLYCHART lines, 8 max per city
	int       gChartLegendLog = 0;    // LEGENDOBJ/GKID recon, 3 rounds max
	int       gChartReconLog = 0;     // LEGENDCBOX/LEGENDSWATCH, 14 max
	// LEGENDNODE (2026-08-06): dumps EVERY node in the chart's legend list with
	// the reason LEGENDFIX accepted or DECLINED it. The existing LEGENDFIX line
	// only prints on the ACCEPT path, so a row that is silently skipped - which
	// is precisely the reported defect, a legend row whose caption never lands -
	// produced no output at all. Law: log BEFORE the gate, never only after it.
	int       gChartNodeLog = 0;      // 48 max = 2 opens x 24 guard
	bool      gChartBornInstalled = false;

	void __fastcall ChartStoreThunk(void* iface, void* /*edx*/, int32_t* r)
	{
		// this = chart+0xD8; the rect is the freshly computed 1x-margin
		// plot rect, about to be stored into chart+0xE0..0xEF.
		uint8_t* chart = reinterpret_cast<uint8_t*>(iface) - 0xD8;
		int32_t* w = reinterpret_cast<int32_t*>(chart);
		const float f = gTierF;
		if (f > 1.01f && r != nullptr)
		{
			// window size from the LOCAL rect at +0x24 (the one the paint
			// path reads - measured, sub_9B38A5).
			const int32_t winW = w[0x2C/4] - w[0x24/4];
			const int32_t winH = w[0x30/4] - w[0x28/4];
			const int32_t l = r[0], t = r[1], rr = r[2], b = r[3];
			const int32_t nl = RoundHalfUp(l * f);
			const int32_t nt = RoundHalfUp(t * f);
			// RIGHT MARGIN - the coupled half of the #57 budget patch.
			// The legend column is laid out by the PANEL builder off winW and
			// never reads this rect, so scaling this margin proportionally
			// (winW-110 -> winW-220) bought the legend nothing and opened a
			// dead gutter between the plot edge and the checkbox column.
			// When the budget patch is fully armed it publishes the margin
			// that clears the new strip by sc(2,f), exactly as stock clears
			// its own by 2. Taking one without the other is the oracle's
			// H-EARLYCHART candidate and it paints the plot border INSIDE the
			// checkbox column - so a zero here means "not armed", and we keep
			// the proportional margin we ship today.
			const int32_t budgetRM =
				CodePatches::GraphLegendPlotRightMargin(f);
			const int32_t nr = (budgetRM > 0)
				? (winW - budgetRM)
				: (winW - RoundHalfUp((winW - rr) * f));
			const int32_t nb = winH - RoundHalfUp((winH - b) * f);
			const bool sane = (nr - nl >= 200) && (nb - nt >= 100)
				&& nl >= 0 && nt >= 0 && nr <= winW && nb <= winH;
			if (sane)
			{
				r[0] = nl; r[1] = nt; r[2] = nr; r[3] = nb;
				// bandH BEFORE the legend latch: sub_9B3647 latches the
				// legend rect right AFTER this store, computing from
				// bandH - so setting it here makes the legend BORN at the
				// scaled height too. Ticks likewise read fresh at paint.
				if (w[0x120/4] == 32)
				{
					w[0x120/4] = RoundHalfUp(32 * f);
				}
				w[0x180/4] = RoundHalfUp(4 * f);
				w[0x184/4] = RoundHalfUp(4 * f);
			}
			if (gChartBornLog < 8)
			{
				gChartBornLog++;
				Logger::Get().WriteLine(LogLevel::Info,
					"UiSpike: EARLYCHART store (%d,%d,%d,%d) -> "
					"(%d,%d,%d,%d) in %dx%d sane=%d budgetRM=%d - born "
					"correct, no stock frame", l, t, rr, b,
					r[0], r[1], r[2], r[3], winW, winH, sane ? 1 : 0,
					budgetRM);
				// LEGENDOBJ: the legend entries live in a linked list at
				// chart+0x228 (sub_9B5ADE walks it, calling each node's
				// [+8]->vt[1] to draw). The "invisible barrier" pushing
				// the legend text right lives in these objects - dump
				// their first dwords so the next fix is measured, not
				// guessed.
				uint32_t* head = reinterpret_cast<uint32_t*>(
					*reinterpret_cast<uintptr_t*>(chart + 0x228));
				int n = 0;
				uint32_t* node = head ? reinterpret_cast<uint32_t*>(
					static_cast<uintptr_t>(head[0])) : nullptr;
				while (node && node != head && n < 4)
				{
					uint32_t* obj = reinterpret_cast<uint32_t*>(
						static_cast<uintptr_t>(node[2]));   // node+8
					if (obj)
					{
						Logger::Get().WriteLine(LogLevel::Debug,
							"UiSpike: LEGENDOBJ[%d] %08X: %08X %08X %08X "
							"%08X %08X %08X %08X %08X", n,
							node[2], obj[0], obj[1], obj[2], obj[3],
							obj[4], obj[5], obj[6], obj[7]);
					}
					node = reinterpret_cast<uint32_t*>(
						static_cast<uintptr_t>(node[0]));
					n++;
				}
			}
		}
		// forward to the real store (thiscall, one stack arg, ret 4 -
		// our __fastcall thunk callee-cleans the same 4 bytes).
		typedef void(__thiscall* StoreFn)(void*, int32_t*);
		reinterpret_cast<StoreFn>(gChartStoreReal)(iface, r);
	}

	// Patch iface vt+0x30 in the VERIFIED chart vtables. .rdata write via
	// VirtualProtect - the PatchFlashGuardClass / ApplyHtmlSizeScale
	// precedent. Installed once; never uninstalled (static thunk, same
	// lifetime rule as every vtable copy in this file).
	void InstallChartBornScale()
	{
		if (gChartBornInstalled) { return; }
		gChartBornInstalled = true;
		const uintptr_t delta = reinterpret_cast<uintptr_t>(
			GetModuleHandleW(nullptr)) - 0x400000;
		gChartStoreReal = 0x9B1F1D + delta;
		static const uintptr_t kSlots[] = {
			0xAB4C28 + 0x30,   // type1 iface (the live Graphs chart)
			0xADE568 + 0x30,   // type2 iface
			// type3 (0xADEDE0) deliberately absent: it overrides the slot
			// with 0x9B2F92 - never write a slot you have not verified.
		};
		for (uintptr_t slotVA : kSlots)
		{
			uintptr_t* slot = reinterpret_cast<uintptr_t*>(slotVA + delta);
			if (*slot != gChartStoreReal)
			{
				Logger::Get().WriteLine(LogLevel::Info,
					"UiSpike: EARLYCHART slot %08X holds %08X, expected "
					"%08X - SKIPPED (verify-before-write)",
					static_cast<uint32_t>(slotVA),
					static_cast<uint32_t>(*slot),
					static_cast<uint32_t>(gChartStoreReal));
				continue;
			}
			DWORD old = 0;
			if (VirtualProtect(slot, sizeof(uintptr_t),
				PAGE_READWRITE, &old))
			{
				*slot = reinterpret_cast<uintptr_t>(&ChartStoreThunk);
				VirtualProtect(slot, sizeof(uintptr_t), old, &old);
				FlushInstructionCache(GetCurrentProcess(), nullptr, 0);
				Logger::Get().WriteLine(LogLevel::Info,
					"UiSpike: EARLYCHART installed on slot %08X - charts "
					"are BORN with scaled margins (no first-paint jump)",
					static_cast<uint32_t>(slotVA));
			}
		}
	}
	// #57: scale the chart's frozen interior fields. ini [Flyout] ChartScale.
	// v2.52.0: BACK ON (default 1) with the mechanism corrected - the write
	// now scales the game's own MARGINS in place and does NOT re-arm the
	// sentinel. History of the two failed attempts is kept below because each
	// one killed a theory that looked right on paper.
	// ⛔ v2.50.0's version (re-arm the sentinel) IS THE ONE THAT FAILED
	// THE SAME SESSION. It did exactly what it said (log: "CHARTSCALE band
	// 32->64 tick 4->8 ... sentinel re-armed") and the screen did not change,
	// because re-arming ONLY the plot sentinel [0xE0] is a half measure: the
	// legend rect at [0x108] has its OWN sentinel, was never re-armed, and
	// kept its 32-tall rect - so bandH=64 had nothing to act on. Worse, the
	// re-lay recomputed the plot as (16,16,960,496), the FLAT 16px DEFAULTS,
	// throwing away the text-derived left gutter (45) the game had worked out.
	// Net: numbers moved, pixels did not, and the margins got worse.
	// MEASURED TARGET, for whoever finishes this (stock capture
	// _tests\captures\graphs-stock-ref.png, chart-local, 488x256 window):
	//     stock plot (78,21,408,234)  ->  x2 = (156,42,816,468) in 976x512
	// i.e. left gutter 156 (room for 20pt ticks), top 42 (room for the
	// title), right 816 leaving a 160px legend gap (26pt "Expenses" needs
	// ~113 and currently wraps in 110). ⚠ Do NOT hard-code that rect for
	// every chart: the bar charts (Population by Age) carry NO legend and
	// their plot legitimately runs wider. The margins are text-derived, so
	// the honest lever is to scale the TEXT and let the game re-derive them.
	//
	// ⛔ AND THAT SECOND THEORY DIED TOO (v2.51.0 -> v2.51.1, same hour).
	// Unpinning ChartTickText 10 -> 20 did NOT move the gutter by one pixel:
	//     10pt -> CHARTGEO PLOT(45,20,866,492)   gutter 45
	//     20pt -> CHARTGEO PLOT(45,20,866,492)   gutter 45   (byte-identical)
	// and the user's screen showed "8000"/"4000" sheared in half. The gutter
	// is INVARIANT to the font, because the plot rect is computed ONCE per
	// chart object and nothing ever re-arms its sentinel - so no font change
	// can reach it. Fonts re-pinned; the lever is GEOMETRY.
	// v2.52.0 therefore wrote the rect DIRECTLY (margins x f, once per
	// object, no re-arm).
	//
	// ⛔ AND THAT DIED TOO - THIRD THEORY, SAME SESSION. The write STICKS:
	//     CHARTSCALE plot (45,20,866,492) -> (90,40,756,472)  sane=1
	//     CHARTGEO   PLOT[0xE0](90,40,756,472)   <- three ticks later, held
	// and the screen did not change by one pixel. So chart+0xE0..0xEF is a
	// rect the chart KEEPS but not the one it DRAWS FROM.
	//
	// THREE LEVERS, THREE REFUTATIONS, ALL MEASURED:
	//   1. re-arm the sentinel  -> recomputes to flat 16px defaults, no
	//                              visual change (v2.50.0)
	//   2. scale the tick font  -> gutter byte-identical, digits sheared
	//                              (v2.51.0)
	//   3. write the rect       -> field holds, pixels do not move (v2.52.0)
	//
	// LEADING SURVIVOR, NOT YET TESTED: the chart is code-painted into its
	// own CACHED BUFFER (SC4-UI-ENGINE.md classifies it beside the gauge
	// dials), so it re-renders only when its data changes -
	// InvalidateSelfAndParents is not enough. That is the #47 lesson exactly
	// ("an installed hook is not an executed hook"), and the established
	// lever is the buffer force-recreate (SlotThunk<88> + gForceRecreate)
	// already used for the sub-flyout and the dials. If the buffer is the
	// blocker, EVERY field-level fix above would look inert exactly as it
	// did - which is why they must not be re-tried before that is settled.
	// DEFAULT 0: none of the three writes earns its place until then.
	// v2.53.1: DEFAULT 1 - the missing half was found by the green-box proof
	// (2026-08-03). All three earlier "failures" shared one cause: the value
	// writes landed but nothing ever DIRTIED the window, because the chart's
	// repaint gate is cIGZWin+0x70 and only vt+0x170 (the game's own
	// SetDirty-and-propagate) reaches it; InvalidateSelfAndParents does not.
	// With the green probe: field write + vt[0x170] = pixels moved, in
	// exactly the rect at chart+0xE0. The scale below now ends with that
	// call, gates on the FIELD (bandH==32) instead of a pointer latch (the
	// chart is REPLACED on every graph switch - user-proven - and a reused
	// address would silently skip; the #92 trap), and runs on every sweep so
	// every newly created chart gets processed.
	int     gChartScale = 1;
	// The chart object we have already scaled - the re-arm must happen ONCE
	// per object, or the sweep re-lays the chart 4x/sec forever (the
	// "incremental panel ... 1 windows scaled" churn trap, v2.25.1).
	// Cleared in Disarm: a second city gets a new chart at a possibly REUSED
	// address, which is exactly how #92 hid.
	cIGZWin* gChartScaled = nullptr;

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
	//        f=1.5      f=2 (SHIPPING, user-confirmed)      f=3
	//   DX:    19        25  <- reproduces the ini exactly   37
	//   DY:    -4        -6  <- reproduces the ini exactly   -8
	//
	// The f=2 column is the gate: it must equal the values 2x shipped with, or
	// this derivation is wrong and a user-confirmed tier has been disturbed.
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
	// ⚠ Do not "restore" a non-zero default to re-seat a ring. If the ring is
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
	// the user described: "the flyout never moves, just where it attaches in
	// the list should".
	//
	// v2.45.0 moved the container to the game's clamped position and left the
	// ring latched, so the ring slid off its button by the distance moved and
	// was reverted the same session. These carry the compensating term: the
	// container goes where the game's own math says, and the ring sprite is
	// offset by exactly the move, so it lands where it lands TODAY - a
	// position confirmed exact by SUBGEO (ring centre == button centre) and
	// by the user's eyes. gSubRingDX/DY stay the USER's ini nudges; these are
	// ours, and they are ZERO whenever SubMath is off, so SubMath=0 remains
	// bit-identical to v2.45.2.
	int     gSubRingAutoX = 0;
	int     gSubRingAutoY = 0;

	// Live record of the sub-flyout ring blit (v2.16.0). The game blits the 1x
	// ring sprite at a DIFFERENT buffer y per menu (94 zones/roads, 119 rails
	// - measured via RCAL 2026-07-29) and its native container placement
	// follows that y, so the dock must know the CURRENT menu's value. The ring
	// draw records it here, tagged with the buffer size so a stale value from
	// the previous menu is never applied to the wrong window (blits fire every
	// frame vs the 4x/sec sweep, so "stale" self-corrects within a frame).
	int     gSubGeoLog = 0;   // #95: SUBGEO assembly dump, 8 lines max
	// #134: SUBGEO sits AFTER the atNative/atTarget gate, so a container the
	// sweep does not recognise logs nothing at all - which is exactly the case
	// that needs explaining. SUBCAND logs every candidate button BEFORE that
	// gate, so the button's absolute X is recorded whether or not the sweep
	// claims it. That absolute X is the one unmeasured term in the ring law:
	// kSubNativeDX (the game's own native container offset) was measured at
	// f=2 and ASSUMED factor-independent, and 3x says otherwise.
	int     gSubCandLog = 0;  // #134: pre-gate candidate dump, 24 lines max
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
	// ⚠ #134: this block used to end "both factor-independent". kSubPlaceBias
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

	// Effective sub-flyout dock delta (audit B6): ini override wins, else the
	// derived form above. f=2 reduces to the shipped (-53,-24) exactly.
	// ---- #95 PHASE 2: THE GAME'S OWN PLACEMENT, EVALUATED AT SCALE -------
	// The deltas below are CONSTANTS, and the true correction is not: the
	// container is centred on its button, so the term grows with the item
	// count. MEASURED with the game's own sub_79AD00 under Unicorn (the
	// existing emu_subflyout harness), stock vs every-metric-scaled:
	//     n:      1     2     3     4     5     6     7     8
	//     delta -54   -74   -98  -123  -147  -172  -196  -221   (f=2)
	//     fixed -24   -24   -24   -24   -24   -24   -24   -24
	// i.e. the error runs from 30px at n=1 to 197px at n=8 - which is the
	// 8-item aircraft picker hanging into the bottom HUD. Horizontally the
	// fixed -53 should be -27, so it also sits 26px too far left.
	//
	// ⚠ MY FIRST CLOSED FORM WAS WRONG BY EXACTLY -2 AT EVERY n. The game
	// does (F4>>1) - (contentH>>1), and (53*f)>>1 != (53>>1)*f - the
	// truncation differs per factor. So this reproduces the game's INTEGER
	// expression, it does not re-derive it. Validated 32/32 exact against the
	// real machine code at n=1..8 x f=1/1.5/2/3, INCLUDING the clamps (at f=3
	// the top margin fires for n>=7). f=1 reproduces stock exactly, which is
	// the regression guard.
	//
	// contentH is taken from the container's LIVE height - never a recomputed
	// item count. The container IS contentH, so this cannot disagree with what
	// is on screen.
	inline int32_t SubPlaceLeft(int32_t cx, float f)
	{
		return cx - RoundHalfUp(27 * f);            // [0xFC] x anchor
	}
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
	// [Flyout] SubMath. ⛔ DEFAULT 0 - REVERTED THE SAME SESSION IT SHIPPED
	// (v2.45.1). The math above is genuinely correct about the CONTAINER: it
	// reproduces the game's own Place 32/32 at n=1..8 x f=1/1.5/2/3, and with
	// it the 8-item picker stopped overlapping the bottom HUD. But the user's
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
	// offset by exactly that move, which pins it to the legacy dock the user
	// already confirmed. Net effect, and it is what the user described: the
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
			// bar at the junction" the user reported, present at 2x since the
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

	bool    gFgParentOk = false;      // GetParentWin slot verified at runtime
	// v2.25.0 (task #53): 6 was FULL (one slot wasted on the tooltip class),
	// so any further class the ready-gate met was silently unguarded. 12.
	const int kFgMax = 12;
	void**  gFgVt[kFgMax] = {};       // patched class vtables
	SlotFn  gFgOrig[kFgMax] = {};     // their original Plot fns
	int     gFgCount = 0;
	void*   gReadyWins[16] = {};
	int     gReadyCount = 0;
	void*   gFgWaitRoot[4] = {};      // fail-open counters per pending root
	int     gFgWaitN[4] = {};

	// SECOND-CITY LIFECYCLE LATCHES (audit 2026-07-29, v2.23.3). These were
	// function-local statics inside the MINIMAP/DVMAP/UDMAP surface-recreate
	// blocks and the ADVHEAL state machine. A function-local static survives
	// the whole process, but the pointers it latches die with the city: if
	// the second city's allocator hands the SAME freed address to its new
	// window object, the "pMap != lastXxx" one-shot test wrongly skips - the
	// display surface is never recreated and the window-sized renderer later
	// overruns it (exactly the v2.21.0 Data Views crash shape). Hoisted to
	// namespace scope ONLY so UiSpike::Disarm can NULL them at city
	// shutdown; their in-function usage is unchanged.
	cIGZWin* lastMinimapSurfResize = nullptr; // HUD dock minimap surface latch
	cIGZWin* lastDataMapSurfResize = nullptr; // Data Views map surface latch
	// v2.69.4 (DVMAP black-map regression, stock-control adjudicated
	// 2026-08-04): the recreate fires at CITY LOAD while the Data Views panel
	// is HIDDEN, so the "old picture" we carry over is the game's still-
	// UNBAKED black surface, and the load-time recompute cannot produce a
	// real repaint (#47 law: a called recompute is not an executed paint).
	// The dock minimap survives the identical code only because its surface
	// is baked while VISIBLE before we recreate. Cure: latch the instance
	// here and RE-FIRE the game's recompute (0x7A7840) + invalidate the
	// first sweep the map is actually on screen - the leaf-kick shape.
	// Pointer-keyed latch => cleared in Disarm beside its two siblings
	// (the #92 second-city law).
	cIGZWin* gDvMapVisibleKick = nullptr;     // set on recreate, fired on first visible
	// v2.71.4 RETIREMENT (tombstone): the v2.69.5 ZOOM-CLIFF dock-seed and the
	// v2.69.6/v2.70.0 per-sweep heal are DELETED here, not gated. They existed
	// because the game's terrain bake silently produces nothing at zoom=-3
	// (stock can never need it: 256 surface / 64-cell smallest tile = -2; our
	// 512 surface pushes SMALL tiles past the bake ceiling), and they were the
	// workaround of record until the x8 bake patch (#121, v2.71.1) made the
	// game itself bake a real base there. v2.71.2 measured the seed actively
	// HURTING once the bake was live: on open it overwrote a correct hidden
	// bake with a blurry 128->512 dock upscale. With a real bake there is
	// nothing to seed and nothing to heal, and a fallback that can only fight
	// the primary path is a bug, not a safety net. Forensic record:
	// REGRESSION.md #121 and VERSION-HISTORY v2.69.5-v2.70.1. The clamp below
	// is the surviving fallback - it engages only when the x8 patch declines
	// on an unexpected exe build.
	// v2.69.10: the clamp and DVPIN are a COUPLED PAIR (law 43) and v2.69.8/9
	// split them - DVPIN's table pins the map picture to 256*f = 512 EVERY
	// sweep, so the clamp and the pin fought at ~30 Hz (the CLAMPED log line
	// fired every 20-40ms) and every DVPIN re-double also re-desynced
	// blitSize (its SetW bypasses the class SetArea override). This flag is
	// the single source of truth: the clamp block sets it, DVPIN reads it and
	// targets the SAME clamped size + centered position, so after the first
	// clamp nobody resizes the map again. Cleared in Disarm (#92 law).
	int32_t  gDvMapClampBlit = 0;             // 0 = no clamp on this city
	// #127: log-throttle for the graphs-band pin (once per distinct move).
	int32_t  gGraphBandLastX = INT32_MIN, gGraphBandLastY = INT32_MIN;
	// #126 minimap draw hook counters. Declared HERE, early, because the
	// ScaleAll pass logs them and it lives above the hook block. Same
	// anonymous namespace, so the hook below writes these very objects.
	int      gMmStretches = 0;   // EXECUTED counter (law 47)
	int      gMmEntries = 0;     // thunk CALLED counter (see MmDrawThunk)
	bool     gMmFirstFireLogged = false;
	int      gMmHooked = 0;      // INSTALLED counter

	// BOUNDED RETRY (v2.41.0, task #89). Until now all three surface blocks
	// latched the window pointer AFTER the attempt regardless of outcome, so a
	// FAULTED or FAILED recreate was never retried: the window kept a stale 1x
	// display surface under a 2x rect for the rest of the city. That is the
	// v2.21.0 crash shape made permanent, and it is the very corruption this
	// task exists to remove.
	//
	// Now the latch is set only on SUCCESS. A failure is counted instead, and
	// after kSurfMaxAttempts the pointer is latched anyway so a genuinely
	// unrecreatable surface cannot re-attempt at the sweep's ~4x/sec forever.
	// Keyed on the pointer: a NEW object gets a fresh budget, which is what
	// makes this safe across the second-city address-reuse trap.
	const int kSurfMaxAttempts = 2;
	struct SurfRetry
	{
		void* ptr;
		int   fails;
		bool ShouldAttempt(void* p)
		{
			if (p != ptr) { ptr = p; fails = 0; }  // new object, fresh budget
			return fails < kSurfMaxAttempts;
		}
		void NoteFail() { ++fails; }
		bool Exhausted() const { return fails >= kSurfMaxAttempts; }
		void Reset() { ptr = nullptr; fails = 0; }
	};
	SurfRetry gMinimapRetry = {};
	SurfRetry gDataMapRetry = {};
	SurfRetry gUdMapRetry = {};
	// v2.37.4 DIALOG ANCHOR TABLE (task #2, the quit-confirm creep). Keyed on
	// the dialog ID - NOT the window pointer, and NOT the scaleMap record.
	// The game re-opens these confirms by resetting the SIZE back to stock, so
	// Classify drops the scale record every time; an anchor stored there is
	// already gone by the next open, which is exactly why the v2.37.3 attempt
	// changed nothing. Without a surviving anchor the centre-preserving move
	// re-centres from the ALREADY-MOVED position and the dialog walks -135,-81
	// per open (measured: 930,398 -> 795,317 -> 660,236 -> ... -> 120,0).
	// Value-writes only; cleared in Disarm like every other per-city latch.
	struct DlgAnchor { uint32_t id; int32_t l, t; };
	DlgAnchor gDlgAnchors[8] = {};
	int gDlgAnchorCount = 0;
	// v2.38.0 (task #79c): ids already reported by DLGBORN. The data-born path
	// runs on EVERY sweep while the dialog is open (~60x/second), so the line
	// has to be one-shot per id or it would bury the log - and a log this
	// verification depends on must stay readable.
	uint32_t gDlgBornLogged[8] = {};
	int gDlgBornCount = 0;
	cIGZWin* lastUdMapSurfResize = nullptr;   // U-Drive-It map surface latch
	void*    healDoneStrip = nullptr;         // ADVHEAL: strip already healed
	int      healPhase = 0;                   // ADVHEAL: 0 = armed, 1 = face clicked

	// CAA (CalcAbsoluteArea) experiment: log count for the rect-pointer probe.
	int gCaaLogCount = 0;
	int gCaaLogCount2 = 0;

	// Per-frame container-position tracker (replaces the dead buffer scan):
	// logs the container's absolute rect whenever it changes, to catch whether
	// the open->settle "jump" is a real window move or pure art animation.
	int gPosFrames = 0;
	int gPosLogged = 0;
	int gLastPosL = 0x7FFFFFFF, gLastPosT = 0, gLastPosW = 0, gLastPosH = 0;

	// SEH-guarded walk of a window's ABSOLUTE top-left (sum of GetL/GetT up the
	// parent chain) + its own w/h. GetL/GetT/GetParentWin are the safe accessors
	// (the GetArea* overload pair is known to crash in MSVC - avoid it).
	bool SafeAbsRect(void* winPtr, int* outL, int* outT, int* outW, int* outH)
	{
		__try
		{
			cIGZWin* self = reinterpret_cast<cIGZWin*>(winPtr);
			int aL = 0, aT = 0;
			cIGZWin* n = self;
			for (int guard = 0; n != nullptr && guard < 32; guard++)
			{
				aL += n->GetL();
				aT += n->GetT();
				n = n->GetParentWin();
			}
			*outL = aL;
			*outT = aT;
			*outW = self->GetW();
			*outH = self->GetH();
			return true;
		}
		__except (EXCEPTION_EXECUTE_HANDLER)
		{
			return false;
		}
	}

	// Objectively locate the orange ring/bar inside a REGION of a buffer.
	// Pure C + SEH only (no C++ unwinding objects) so a bad GetPixel can't
	// crash the game. Subsamples on a 2px grid. Centroid/bbox are returned in
	// the buffer's own coordinate space (= absolute screen coords here).
	// A pixel is "orange" if it is bright, red-dominant, mid green, low blue.
	// Diagnostic fields describing what a region actually contains, so we can
	// see the ring's TRUE color instead of guessing the threshold again.
	struct RegionStats
	{
		int lockOk;
		int lockFlag;    // which lock flag succeeded (0, 0x8000, or -1 none)
		unsigned int bitsAddr;   // GetColorSurfaceBits
		int stride;      // GetColorSurfaceStride
		int bpp;
		int usedRaw;     // 1 if scanned via raw bits, 0 if via GetPixel
		int sampled;     // total pixels sampled
		int nonBlack;    // pixels not near-black
		int orange;      // pixels matching the orange predicate
		int ocx, ocy;    // orange centroid (buffer/screen coords)
		int omnx, omny, omxx, omxy;   // orange bbox
		int mrb;         // best (R-B) seen
		int mr, mg, mb;  // that pixel's RGB
		int mx, my;      // that pixel's location
	};

	bool ScanRegion(cIGZBuffer* buf, int x0, int y0, int x1, int y1,
		RegionStats* s)
	{
		__try
		{
			const int bw = buf->Width();
			const int bh = buf->Height();
			if (bw <= 0 || bh <= 0 || bw > 8192 || bh > 8192)
			{
				s->orange = -2;             // bad buffer dims
				return true;
			}
			if (x0 < 0) x0 = 0;
			if (y0 < 0) y0 = 0;
			if (x1 > bw) x1 = bw;
			if (y1 > bh) y1 = bh;
			// Hardware surfaces read back blank via GetPixel unless synced.
			// IsDirtyUpdate (0x8000) is the documented flag that forces it.
			int lockFlag = -1;
			if (buf->Lock(0x8000)) { lockFlag = 0x8000; }
			else if (buf->Lock(0)) { lockFlag = 0; }
			s->lockOk = (lockFlag >= 0) ? 1 : 0;
			s->lockFlag = lockFlag;
			s->bpp = static_cast<int>(buf->GetBitsPerPixel());
			const unsigned int bitsAddr = buf->GetColorSurfaceBits();
			const int stride = static_cast<int>(buf->GetColorSurfaceStride());
			s->bitsAddr = bitsAddr;
			s->stride = stride;
			const bool useRaw = (bitsAddr != 0 && stride > 0 && s->bpp == 32);
			s->usedRaw = useRaw ? 1 : 0;
			const uint8_t* bits = reinterpret_cast<const uint8_t*>(
				static_cast<uintptr_t>(bitsAddr));

			long long sx = 0, sy = 0;
			int count = 0, sampled = 0, nonBlack = 0;
			int minX = x1, minY = y1, maxX = -1, maxY = -1;
			int mrb = -999, mr = 0, mg = 0, mb = 0, mx = -1, my = -1;
			for (int y = y0; y < y1; y += 2)
			{
				for (int x = x0; x < x1; x += 2)
				{
					uint8_t r = 0, g = 0, b = 0;
					if (useRaw)
					{
						const uint32_t px = *reinterpret_cast<const uint32_t*>(
							bits + static_cast<size_t>(y) * stride + x * 4);
						r = static_cast<uint8_t>((px >> 16) & 0xFF);
						g = static_cast<uint8_t>((px >> 8) & 0xFF);
						b = static_cast<uint8_t>(px & 0xFF);
					}
					else
					{
						const uint32_t px = buf->GetPixel(
							static_cast<uint32_t>(x), static_cast<uint32_t>(y));
						buf->ConvertNativeValueToRGB(px, r, g, b);
					}
					sampled++;
					if (r > 24 || g > 24 || b > 24) nonBlack++;
					const int rb = static_cast<int>(r) - static_cast<int>(b);
					if (rb > mrb) { mrb = rb; mr = r; mg = g; mb = b; mx = x; my = y; }
					if (r >= 170 && g >= 45 && g <= 180 && b <= 110
						&& (r - b) >= 90 && (r - g) >= 35)
					{
						sx += x;
						sy += y;
						count++;
						if (x < minX) minX = x;
						if (y < minY) minY = y;
						if (x > maxX) maxX = x;
						if (y > maxY) maxY = y;
					}
				}
			}
			if (lockFlag >= 0)
			{
				buf->Unlock(static_cast<uint32_t>(lockFlag));
			}
			s->sampled = sampled;
			s->nonBlack = nonBlack;
			s->orange = count;
			s->mrb = mrb; s->mr = mr; s->mg = mg; s->mb = mb; s->mx = mx; s->my = my;
			if (count > 0)
			{
				s->ocx = static_cast<int>(sx / count);
				s->ocy = static_cast<int>(sy / count);
				s->omnx = minX; s->omny = minY; s->omxx = maxX; s->omxy = maxY;
			}
			return true;
		}
		__except (EXCEPTION_EXECUTE_HANDLER)
		{
			return false;
		}
	}

	// SEH-guarded identity check for a candidate buffer pointer: does it answer
	// to cIGZBuffer, and what are its dims/depth? Pure C only (no C++ unwind).
	bool SafeBufProbe(void* bufPtr, int* outQi, int* outW, int* outH, int* outBpp)
	{
		__try
		{
			cIGZBuffer* buf = reinterpret_cast<cIGZBuffer*>(bufPtr);
			void* q = nullptr;
			int qi = 0;
			if (buf->QueryInterface(GZIID_cIGZBuffer, &q) && q != nullptr)
			{
				qi = 1;
				static_cast<cIGZUnknown*>(q)->Release();
			}
			*outQi = qi;
			*outW = buf->Width();
			*outH = buf->Height();
			*outBpp = static_cast<int>(buf->GetBitsPerPixel());
			return true;
		}
		__except (EXCEPTION_EXECUTE_HANDLER)
		{
			return false;
		}
	}

	// ===== SURFACE CARRY-OVER (v2.41.14, task #89) ==========================
	// THE DEFECT THESE EXIST TO FIX, measured 2026-08-01 and user-confirmed:
	// our surface-recreate destroyed the display surface, built a new one and
	// PRE-CLEARED IT TO BLACK - so a perfectly good map vanished until the
	// engine's message-driven bake landed, and that empty box is what the user
	// read as "corruption". Raster sampling proved it: distinct=4 (real
	// terrain colours) before our pass, all zeros after.
	//
	// The cure is to carry the picture ACROSS the recreate. Capture first,
	// recreate exactly as before (the destroy/create ORDER is untouched - that
	// is the v2.21.1 crash site), then repaint. Black stays underneath as the
	// floor so a partial restore still cannot show uninitialised VRAM.
	//
	// Shared by all three surface blocks (MINIMAP / DVMAP / UDMAP). One static
	// buffer is safe because each block captures and repaints before the next
	// block runs - they are sequential in ScalePanelsUnder, never interleaved.
	const int kCarryMax = 512;                       // covers 64->128 (dock,
	                                                 // any tier) and 256->512
	                                                 // (Data Views at 2x)
	uint32_t gCarryPix[kCarryMax * kCarryMax];

	// Copy a surface's pixels out. Returns false (and leaves w/h 0) on any
	// failure, which makes the caller fall back to the plain black fill - i.e.
	// exactly the pre-v2.41.12 behaviour, never worse.
	// v2.71.1 (#121, the last 1%): run the game's OWN terrain bake right now
	// instead of waiting for its message.
	//
	// WHY: the recompute at 0x7A7840 does not paint anything - it reallocates
	// the raster, recomputes zoom, memsets the dirty-tile mask to all-0xFF and
	// sets fd=1. The paint happens later, when the game's message handler
	// (0x7A8640) sees fd and calls the bake at 0x7A7FF0. For stock that is
	// invisible: its map is already correct before the panel is shown. Ours is
	// rescaled and its surface recreated AFTER creation, so the bake lands a
	// tick or more after the panel is on screen and the user sees it fill in.
	// MEASURED 2026-08-04: our own log shows blits=0 at one recompute and 336
	// by the next, and the STOCK CONTROL paints the correct map immediately -
	// so the gap is ours, not the game's.
	//
	// SAFETY: this is the game's own function, on the game's own object, on the
	// UI thread the handler itself runs on (single-threaded; every hook here
	// already relies on that). It is idempotent because the bake clears the
	// dirty mask and fd as it finishes, so the later message finds nothing left
	// to do - no double paint, no fight. SEH-guarded: on any fault we simply
	// fall back to the old behaviour (the message-driven bake still runs).
	void DriveMiniMapBake(void* mm, const char* who)
	{
		if (!mm) { return; }
		__try
		{
			typedef void (__thiscall* BakeFn)(void*);
			reinterpret_cast<BakeFn>(0x007A7FF0)(mm);
		}
		__except (EXCEPTION_EXECUTE_HANDLER)
		{
			Logger::Get().WriteLine(LogLevel::Error,
				"UiSpike: DVMAP synchronous bake FAULTED (%s) - falling back "
				"to the game's message-driven bake (the map will fill in a "
				"moment later, as it did before v2.71.1).", who);
		}
	}

	bool CaptureSurface(void* surf, int* outW, int* outH)
	{
		*outW = 0; *outH = 0;
		if (!surf) { return false; }
		__try
		{
			cIGZBuffer* pBuf = nullptr;
			if (!reinterpret_cast<cIGZBuffer*>(surf)->QueryInterface(
					GZIID_cIGZBuffer, reinterpret_cast<void**>(&pBuf)) || !pBuf)
			{
				return false;
			}
			const int w = pBuf->Width(), h = pBuf->Height();
			if (w <= 0 || h <= 0 || w > kCarryMax || h > kCarryMax)
			{
				pBuf->Release();
				return false;
			}
			for (int y = 0; y < h; y++)
			{
				for (int x = 0; x < w; x++)
				{
					gCarryPix[y * w + x] = pBuf->GetPixel(x, y);
				}
			}
			pBuf->Release();
			*outW = w; *outH = h;
			return true;
		}
		__except (EXCEPTION_EXECUTE_HANDLER)
		{
			*outW = 0; *outH = 0;
			return false;
		}
	}

	// Repaint the captured picture into pBuf at n x n, BILINEAR. Fixed-point
	// 8.8. All four channels are blended independently: the raster carries
	// meaningful alpha (measured 00 on the map body, FF on the border), so it
	// is interpolated too rather than forced opaque.
	void RestoreSurfaceBilinear(cIGZBuffer* pBuf, int srcW, int srcH, int n)
	{
		for (int y = 0; y < n; y++)
		{
			const int syq = (y * srcH * 256) / n;
			int sy0 = syq >> 8;
			const int fy = syq & 0xFF;
			if (sy0 > srcH - 1) { sy0 = srcH - 1; }
			const int sy1 = (sy0 + 1 < srcH) ? sy0 + 1 : sy0;
			for (int x = 0; x < n; x++)
			{
				const int sxq = (x * srcW * 256) / n;
				int sx0 = sxq >> 8;
				const int fx = sxq & 0xFF;
				if (sx0 > srcW - 1) { sx0 = srcW - 1; }
				const int sx1 = (sx0 + 1 < srcW) ? sx0 + 1 : sx0;

				const uint32_t p00 = gCarryPix[sy0 * srcW + sx0];
				const uint32_t p10 = gCarryPix[sy0 * srcW + sx1];
				const uint32_t p01 = gCarryPix[sy1 * srcW + sx0];
				const uint32_t p11 = gCarryPix[sy1 * srcW + sx1];

				uint32_t out = 0;
				for (int sh = 0; sh < 32; sh += 8)
				{
					const int c00 = (p00 >> sh) & 0xFF;
					const int c10 = (p10 >> sh) & 0xFF;
					const int c01 = (p01 >> sh) & 0xFF;
					const int c11 = (p11 >> sh) & 0xFF;
					const int top = c00 + (((c10 - c00) * fx) >> 8);
					const int bot = c01 + (((c11 - c01) * fx) >> 8);
					const int v = top + (((bot - top) * fy) >> 8);
					out |= static_cast<uint32_t>(v & 0xFF) << sh;
				}
				pBuf->SetPixel(x, y, out);
			}
		}
	}

	void LogBufCandidate(const char* label, void* bufPtr)
	{
		if (bufPtr == nullptr)
		{
			Logger::Get().WriteLine(LogLevel::Debug,
				"UiSpike: DBUF %-10s = null", label);
			return;
		}
		int qi = -1, w = -1, h = -1, bpp = -1;
		if (SafeBufProbe(bufPtr, &qi, &w, &h, &bpp))
		{
			Logger::Get().WriteLine(LogLevel::Debug,
				"UiSpike: DBUF %-10s ptr%p qiBuf=%d %dx%d bpp=%d",
				label, bufPtr, qi, w, h, bpp);
		}
		else
		{
			Logger::Get().WriteLine(LogLevel::Debug,
				"UiSpike: DBUF %-10s ptr%p FAULT", label, bufPtr);
		}
	}

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
	int gCtxHalve = 0;       // v2.8.3: OFF. Only needed when fields were doubled
	                         // (to halve the doubled src back to 1x). With natural
	                         // fields (gFieldMask=0) the srcs are already 1x; halving
	                         // them would show half the texture. Buffer size is the
	                         // 2x lever now, so leave the element draws untouched.

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
		if (gCtxHalve && a2)
		{
			int32_t* r = reinterpret_cast<int32_t*>(a2);   // srcRect (l,t,r,b)
			const int w = r[2] - r[0], h = r[3] - r[1];
			// ONLY halve the doubled CONTAINER-element srcs (bar caps ~106w,
			// ring ~188w). The thumbnail blits go through this same buffer but
			// were NOT dst-doubled, so halving their (small) src showed 1/4 of
			// the picture. Guard on size so thumbnails render full.
			if ((w > 80 || h > 80) && w < 8000 && h < 8000)
			{
				r[0] /= 2; r[1] /= 2; r[2] /= 2; r[3] /= 2;
			}
		}
		return gCtxOrigBlt ? gCtxOrigBlt(self, a1, a2, a3, a4) : 0;
	}

	// BUFFER RESIZE hook (v2.8.0). Offline RE proved: on-screen flyout size ==
	// the source buffer's PHYSICAL size (141), and the buffer is (re)created inside
	// Plot via buffer->Init(w,h,f0,f1) — class vtable 0x00AC1400 slot 3 (0x008269B0),
	// where w,h come from the WINDOW size (282x678) but a runtime 0.5 makes the
	// physical buffer 141x339. Hooking Init (NOT the window) to enlarge the buffer
	// leaves the window at 282, so it should not fly the strip or trip the parent-
	// clip like the window-resize did (v2.7.96). We patch the SHARED class vtable
	// slot, but ONLY around the disaster container's Plot call (restored right
	// after), so no other buffer in the game is affected. gInitLog also finally
	// records the REAL Init args (resolves the static 282-vs-141 contradiction).
	typedef int(__thiscall* InitFn)(void* self, int w, int h, int f0, int f1);
	InitFn gCtxOrigInit = nullptr;
	int    gInitScale = 1;               // Init passthrough: recreate buffer at the
	                                     // CURRENT window (282) = 2x the stale 141;
	                                     // no doubling needed (composite clips to
	                                     // r24=282). >1 overshoots + loops forever.
	int    gHideRing = 0;                // v2.8.4 test CONFIRMED the visible orange
	                                     // circle is the BUTTON's selection ring (it
	                                     // stayed when the container ring was hidden),
	                                     // NOT a flyout element. Also 0xec/0xf0 are
	                                     // shared with the bar, so hiding broke it.
	                                     // Leave OFF. Scaling the circle = god-toolbar
	                                     // button work, separate from the flyout.
	int    gForceRecreate = 1;           // corrupt the buffer's cached width so
	                                     // Plot's validity check fails -> it
	                                     // releases + recreates the buffer -> Init
	                                     // fires -> InitThunk doubles it. (Init is
	                                     // otherwise never called on static frames.)
	void** const kBufClassVt = reinterpret_cast<void**>(0x00AC1400);
	void*  gBufSavedInit = nullptr;
	bool   gBufVtWritable = false;
	int    gInitLog = 0;

	int __fastcall InitThunk(void* self, void* /*edx*/, int w, int h, int f0, int f1)
	{
		if (gInitLog < 6)
		{
			gInitLog++;
			Logger::Get().WriteLine(LogLevel::Debug,
				"UiSpike: DINIT in w=%d h=%d f0=%d f1=%d -> req %dx%d",
				w, h, f0, f1, w * gInitScale, h * gInitScale);
		}
		return gCtxOrigInit
			? gCtxOrigInit(self, w * gInitScale, h * gInitScale, f0, f1) : 0;
	}

	// CLASS-level buffer Blt hook (v2.8.7). Because the buffer is force-recreated,
	// the instance vtable swap (BltThunkCtx) is dead; to see/adjust the element
	// draws we must hook the class vtable's Blt slot (0x00AC1400[29]=0x74),
	// patched only around the disaster Plot. Logs each draw; can also halve large
	// srcs (to stretch a field-doubled ring).
	typedef int(__thiscall* CBltFn)(void* self, void* a1, void* a2, void* a3, void* a4);
	CBltFn gClassBltOrig = nullptr;
	void*  gClassBltSaved = nullptr;
	int    gStripDump = 0;               // DIAGNOSTIC (ini StripDump): declared here
	                                     // (before BltClassThunk) so the ring/bar draw
	                                     // logger can see it. See fuller note at the
	                                     // strip globals. No visual effect. Live-tunable.
	int    gClassBltLog = 0;             // log first N class-Blt draws
	int    gClassHalveRing = 0;          // halve srcs >80 (stretch a doubled ring)
	int    gRingScale = 1;               // v2.9.0 dst-enlarge: DEAD (blit clips, no
	                                     // stretch - confirmed in 0x826ad0+0x826210).
	                                     // Ring needs 2x ART, not geometry.
	int    gDrawCtxLog = 0;              // v2.9.2: probe the ring draw's SOURCE
	                                     // (drawContext a1) = the art atlas, to find
	                                     // where the 2x ring/picture art must go.
	int    gDumpAtlas = 0;               // v2.9.3: dump the 306x62 atlas pixels (done)
	int    gAtlasDumped = 0;
	int    gRing2xBlit = 1;              // v2.9.4: CODE-ONLY 2x ring. Read the 94x62
	                                     // ring from the atlas (a1), nearest-upscale
	                                     // 2x -> 188x124, write into the container
	                                     // (self) at the ring pos, color-keying
	                                     // magenta. Skips the game's 1x ring blit.
	                                     // Both buffers are the same readable class.
	int    gRingDX = 0;                  // v2.9.7: back to 0 (no buffer-edge clip);
	int    gRingDY = -27;                // v2.10: live-tunable via ini [Disaster] RingDY
	int    gRingDockX = 6;               // disaster container dock X offset (ini DockX)
int    gRingDockY = 130;             // disaster container dock Y offset (ini DockY).
                                     // STOCK PARITY TARGET (from the 1024x768
                                     // vanilla capture 2026-07-28): the flyout's
                                     // TOP ARROW sits at the TERRAFORM button
                                     // (btn1) height and the 4th disaster centres
                                     // on the DISASTER button (btn4) - 6 items
                                     // visible. At 2x the button pitch is 120 and
                                     // btn4 centre is y=860, so btn1 centre = 500;
                                     // the old 130 put the container top at
                                     // tbLiveT+260 = 682 (~btn3), i.e. ~180px too
                                     // low, which is why item 2 - not item 4 - lined
                                     // up with the tornado button. 40 -> top 502.
                                     // NOTE: this is in 1x units (x f at use), while
                                     // RingDY is SCREEN px - move the unit up by N
                                     // screen px and RingDY must go UP by the same N
                                     // to keep the ring on btn4.
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

	// v2.71.8 (3x tier): the v2.71.6 RingDXEff/RingDYEff helpers lived here.
	// They scaled the RingDX/RingDY correction by (f-1), anchoring it at f=1 =
	// the game's own 1x anchor. That anchor is the UNDOCKED stock seat, so the
	// (f-1) law drifted at 3x (8px right, 7px low - "flyout circle not 1:1
	// docked"). The ring seat now uses SEAT-SCALING, computed inline at the
	// disaster ring blit below (it needs the sprite size sw/sh): keep the
	// ring's centre at its f=2 docked seat scaled by f/2. gRingDX/gRingDY are
	// still the f=2 tuning values; only the tier extrapolation changed.

	// LAYER FIX (v2.11): the game paints BAR tiles first, then the RING, so the
	// 2x ring's right arc/neck lands ON TOP of the bar's left edge -> the circle
	// covers the strip (wrong order). We want Circle -> Strip -> Pictures. Fix:
	// cache each bar tile as it draws, and after the ring upscale REPLAY the tiles
	// on top, so the strip's orange covers the circle's right arc (smooth lead-in).
	// Same-orange double-draw elsewhere is harmless. Live-toggle via ini LayerFix.
	int    gLayerFix = 1;
	struct BarTile { void* a1; int32_t s[4]; int32_t d[4]; };
	BarTile gBarCache[64] = {};
	int     gBarCacheN = 0;
	// v2.39.10 (task #84): WHICH CONTAINER OWNS THE CACHED TILES.
	// The fill site is family-agnostic - `gDisasterDrawTuning ? destIsContainer
	// : destIsSubContainer` - so BOTH the disaster container and the mayor
	// sub-flyout container fill this cache, but the only DRAIN is inside the
	// DISASTER ring block. So after a sub-flyout painted, its tiles sat here
	// indefinitely (cap 64), holding raw `a1` atlas pointers across opens and
	// across a city switch, and the next disaster ring draw would have
	// replayed FOREIGN tiles onto the disaster container.
	// The cache is a WITHIN-ONE-PAINT structure; owner-keying makes that
	// explicit: a different `self` means a new paint, so discard first.
	void*   gBarCacheOwner = nullptr;
	bool    gBarCacheSatLogged = false;

	// Draw one BAR tile: read the atlas (a1), x-upscale by gBarWiden, write into
	// the container (self) at (d[0]+gBarDX, d[1]), color-keying magenta. Shared by
	// the live draw and the post-ring replay so both paint identically.
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
		// user-confirmed CORRECT look; the original "seam" this doubling
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
				// ALPHA (v2.17.3): the submenus mod's frame art is RGBA (real
				// alpha, no magenta key); copying its semi-transparent edge
				// pixels opaque paints a dark halo. Skip a<128 - but ONLY when
				// alpha is meaningfully set: stock magenta-keyed art carries
				// a=0 on every pixel and must keep drawing as before.
				if (sp[3] > 0 && sp[3] < 128)
					continue;
				uint8_t* dp = drow + cx * 4;
				dp[0] = sp[0]; dp[1] = sp[1]; dp[2] = sp[2]; dp[3] = sp[3];
			}
		}
	}

	// v2.36.10 ([Probe] EdgeBlt, task #59): countdown of edge-strip blits still
	// to log. Declared here because BltClassThunk reads it and the probe block
	// that parses the ini sits far below.
	int gEdgeBltLog = 0;

	// #162 THIN-BLIT PROBE. [Probe] ThinBlt=<lines>. Default OFF.
	//
	// ⛔ THE QUESTION IT ANSWERS, and nothing else in this file can: is the
	// reported hairline DRAWN, or is it a GAP? Five hypotheses were shipped
	// against these two lines by reasoning about mechanisms - art snapping,
	// tiled sizing, 9-slice sizing, a runtime-bitmap underfill, button cells -
	// and every offline census came back clean:
	//     abutting windows separating at 1.5x   0  (0 at 1x/2x/3x, controls OK)
	//     cropped blits under-filling           0 of 783
	//     advisor portrait cell vs window       exact at 1.5x AND 2x
	// When every coverage model says "covered" and the user still sees ink,
	// the model is wrong - so stop modelling and watch the blits.
	//
	// A hairline that is DRAWN must arrive here as a dst rect <= 3px on one
	// axis. If a session that shows the line logs NOTHING, the line is NOT
	// drawn through this buffer class: it is an uncovered gap (look at what
	// fails to cover it) or it is outside the UI buffer entirely (the #59
	// boundary). Either answer is worth more than a sixth guess.
	//
	// ⚠ A NULL HERE IS ONLY EVIDENCE WITH ITS POSITIVE CONTROL. The counter
	// below reports how many blits were SEEN as well as how many were thin, so
	// "0 thin of 0 seen" (hook never ran) can never be misread as "0 thin of
	// 40,000 seen" (hook ran, nothing thin).
	int gThinBlt = 0;          // remaining lines to log; 0 = off
	int gThinSeen = 0;         // total blits this hook observed
	int gThinHit = 0;          // of those, thin ones


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
			// rule, #49 REGRESSION.md:1387) and then reads a slice AS WIDE AS
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
			// ⛔ DEAD, DO NOT RE-ENABLE. This was the WRONG CHANNEL: these icons
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
				// ⛔ THE HEARTBEAT IS THE POSITIVE CONTROL, AND THE FIRST VERSION
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
					// ⛔ RAW RECT READS, NEVER VIRTUALS (adversarial review
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
			if (gClassHalveRing)
			{
				const int w = s[2] - s[0], h = s[3] - s[1];
				if ((w > 80 || h > 80) && w < 8000 && h < 8000)
				{ s[0] /= 2; s[1] /= 2; s[2] /= 2; s[3] /= 2; }
			}
			if (gRingScale > 1 && d[0] == 0)
			{
				const int rw = d[2] - d[0], rh = d[3] - d[1];
				if (rw > 40 && rw < 160)
				{
					d[2] = d[0] + rw * gRingScale;
					d[3] = d[1] + rh * gRingScale;
				}
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
					void** a1vt = *reinterpret_cast<void***>(a1);
					int32_t* af = reinterpret_cast<int32_t*>(a1);
					Logger::Get().WriteLine(LogLevel::Debug,
						"UiSpike: DCTX a1=%p a1vt=%p isBufCls=%d area[0x14..0x20]=(%d,%d,%d,%d)",
						a1, (void*)a1vt, (a1vt == kBufClassVt) ? 1 : 0,
						af[5], af[6], af[7], af[8]);
				}
			}
			// ATLAS PIXEL DUMP — REMOVED v2.66.0 (release hygiene, #112).
			// The v2.9.3 one-shot that dumped the 306x62 atlas to
			// atlas_dump.bin lived here. It was DEAD CODE: `gDumpAtlas` is a
			// hardcoded 0 (:1345, its own comment already said "(done)"),
			// nothing writes it, and there is no ini key for it — so the
			// block could not execute. It is removed rather than repaired
			// because it carried an ABSOLUTE MACHINE PATH into the shipped
			// binary:
			//     C:\Users\<user>\OneDrive\Documents\SimCity 4\Plugins\...
			// A byte scan of build\Release\SC4UIScale.dll found that string
			// in the artifact we were about to publish. It would also have
			// silently failed for every user but us.
			// gDumpAtlas / gAtlasDumped are DELIBERATELY KEPT declared: two
			// live conditions (:2583, :2603) still read them, and with
			// gDumpAtlas == 0 those short-circuit exactly as before, so this
			// removal is behaviour-neutral by construction.
			// If the dump is ever needed again, derive the path at runtime
			// beside the log — never hardcode one.
			// CODE-ONLY 2x RING: read the 94x62 ring from the atlas (a1),
			// nearest-upscale 2x, write into the container (self) at the ring's
			// dst origin, color-keying magenta. Skip the game's 1x ring blit.
			// gDisasterDrawTuning: the ring upscale and its RingDX/RingDY were
			// measured for the DISASTER flyout. The sub-flyout container is the
			// same class and passes destIsContainer, so it must be excluded.
			if (gRing2xBlit && gDisasterDrawTuning && a1 && d[0] == 0 && destIsContainer)
			{
				const int sw = s[2] - s[0], sh = s[3] - s[1];
				if (sw > 80 && sw < 120 && sh > 40 && sh < 90)   // the ring (94x62)
				{
					int32_t* af = reinterpret_cast<int32_t*>(a1);     // atlas
					int32_t* cf = reinterpret_cast<int32_t*>(self);   // container
					uint8_t* asrc = reinterpret_cast<uint8_t*>(
						static_cast<uintptr_t>(static_cast<uint32_t>(af[15])));
					uint8_t* cdst = reinterpret_cast<uint8_t*>(
						static_cast<uintptr_t>(static_cast<uint32_t>(cf[15])));
					const int astride = af[16], cstride = cf[16];
					const int cW = cf[7] - cf[5], cH = cf[8] - cf[6];
					const int sx0 = s[0], sy0 = s[1];
					// v2.71.8 (3x tier): SEAT-SCALING, replacing v2.71.6's
					// (f-1)*ini law. That law anchored the correction at f=1 =
					// the game's own 1x anchor d[] - but d[] is the UNDOCKED
					// stock seat, not a docked one: the ring sits on button 4
					// only once the dock runs, and the dock is a scaled
					// placement. The docked seat therefore scales linearly with
					// the tier, so keep the ring's CENTRE at its f=2 seat scaled
					// by f/2. Centre at f=2 = d[]+RingDX/DY + (sw,sh) (half the
					// 2x sprite == the 1x size); scale that by f/2 and subtract
					// the scaled half-size to get the top-left. Bit-identical at
					// f=2 (even-int RoundHalfUp, exact /2). At f=3 this moves the
					// seat (32,444)->(24,437): the (f-1) law was 8px right and
					// 7px low - the "flyout circle not 1:1 docked" report.
					const int cx2 = d[0] + gRingDX + sw;   // ring centre-x @ f=2
					const int cy2 = d[1] + gRingDY + sh;   // ring centre-y @ f=2
					const int dx0 = (gTierF <= 1.01f) ? d[0]
						: RoundHalfUp(cx2 * gTierF / 2.0)
							- RoundHalfUp(sw * gTierF) / 2;
					const int dy0 = (gTierF <= 1.01f) ? d[1]
						: RoundHalfUp(cy2 * gTierF / 2.0)
							- RoundHalfUp(sh * gTierF) / 2;
					// v2.24.0 (audit B1): fractional NN (Upscale2x.cs method) in
					// place of the hardwired *2 / >>1. At f=2: RoundHalfUp(sh*2)
					// = sh*2 and floor(oy/2.0) = oy>>1, bit-identical.
					const int ringDstW = FloorScale(sw, gTierF);   // FLOOR, see decl
					const int ringDstH = FloorScale(sh, gTierF);   // FLOOR, see decl
					if (asrc && cdst && astride > 0 && cstride > 0)
					{
						for (int oy = 0; oy < ringDstH; oy++)
						{
							const int cy = dy0 + oy;
							if (cy < 0 || cy >= cH) continue;
							const uint8_t* srow = asrc
								+ (sy0 + static_cast<int>(oy / gTierF)) * astride;
							uint8_t* drow = cdst + cy * cstride;
							for (int ox = 0; ox < ringDstW; ox++)
							{
								const int cx = dx0 + ox;
								if (cx < 0 || cx >= cW) continue;
								const uint8_t* sp = srow
									+ (sx0 + static_cast<int>(ox / gTierF)) * 4;
								if (sp[0] == 0xFF && sp[1] == 0x00 && sp[2] == 0xFF)
									continue;   // magenta color-key = transparent
								uint8_t* dp = drow + cx * 4;
								dp[0] = sp[0]; dp[1] = sp[1]; dp[2] = sp[2]; dp[3] = sp[3];
							}
						}
					}
					// LAYER FIX: the ring was just painted on top of the bar (game
					// order is bar->ring). Replay the cached bar tiles ON TOP so the
					// strip's orange covers the circle's right arc = Circle -> Strip.
					if (gLayerFix)
					{
						// v2.39.10: replay ONLY tiles this container cached.
						// The fill site serves both flyout families, so without
						// this an accumulated sub-flyout paint would be replayed
						// onto the disaster container. Clear either way - a
						// non-matching owner means the tiles are stale and must
						// not survive into the next paint (they hold raw atlas
						// pointers).
						if (gBarCacheOwner == self)
						{
							for (int i = 0; i < gBarCacheN; i++)
								DrawBarScaled(self, gBarCache[i].a1,
									gBarCache[i].s, gBarCache[i].d);
						}
						gBarCacheN = 0;
						gBarCacheOwner = nullptr;
						gBarCacheSatLogged = false;
					}
					return 0;   // skip the game's 1x ring blit
				}
			}
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
			if (gRing2xBlit && a1 && destIsSubContainer)
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
					// size the user reported the sub-flyout "docked correctly but
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
				&& (gDisasterDrawTuning ? destIsContainer : destIsSubContainer)
				&& (BarWidenEff() > 1.0f || BarDXEff() != 0))
			{
				if (BarWidenEff() > 1.0f)
				{
					// Cache this tile so the ring block can replay it on top
					// (LAYER FIX), then draw it now so the bar renders even on
					// frames where the ring never draws.
					if (gLayerFix)
					{
						// v2.39.10: OWNER-KEY THE CACHE. A different container
						// means a different paint, so anything still here is
						// stale - discard it rather than letting the disaster
						// ring block replay a sub-flyout's tiles (or vice
						// versa) and rather than holding its atlas pointers.
						if (self != gBarCacheOwner)
						{
							gBarCacheN = 0;
							gBarCacheOwner = self;
							gBarCacheSatLogged = false;
						}
						if (gBarCacheN < 64)
						{
							BarTile& t = gBarCache[gBarCacheN++];
							t.a1 = a1;
							t.s[0] = s[0]; t.s[1] = s[1]; t.s[2] = s[2]; t.s[3] = s[3];
							t.d[0] = d[0]; t.d[1] = d[1]; t.d[2] = d[2]; t.d[3] = d[3];
						}
						else if (!gBarCacheSatLogged)
						{
							// NO SILENT CAPS: at 64 tiles the LayerFix replay is
							// silently incomplete, which would read as "the fix
							// stopped working" with nothing in the log to say so.
							gBarCacheSatLogged = true;
							Logger::Get().WriteLine(LogLevel::Info,
								"UiSpike: BARCACHE saturated at 64 tiles on ptr%p "
								"- LayerFix replay is INCOMPLETE for this paint.",
								self);
						}
					}
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
	// ⛔ THE FIRST VERSION OF THIS PROBE COULD NOT SEE ITS OWN SUBJECT.
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

	// ⛔ THE STEP-EXTRA MUST FLOOR. ROUNDING IT UP COSTS A WHOLE ROW.
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
	// until the user scrolls. USER-REPORTED 2026-08-06.
	//
	// ⚠ INTEGER TIERS ARE UNAFFECTED: 5*2 = 10 and 5*3 = 15 are already whole,
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
	// v2.36.4 diagnostic ([Probe] EdgeDump): name the screen-edge border
	// window (#59) and settle whether the U-Drive-It map marker is a window
	// at all (#60). Logs only when the observed SET changes, capped at 40.
	int    gEdgeDump = 0;
	int    gStripHitDX = 0;              // (confirmed no-op: [0xA8]/[0xB0] is a
	                                     // recomputed cache) - left for reference.
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
	// ⛔ SCOPE. Fires ONLY on the over-read signature - a 4-state strip whose
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
		// ⛔ THE FIRST VERSION PASSED THE IID AS THE SERVICE ID AND GOT NULL
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
	// ⛔ WHY THE PREVIOUS WATCH MISSED IT, and the rule this encodes: every
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

	// ⛔ THE FIRST VERSION DECLARED THIS __stdcall AND CRASHED THE GAME:
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
			// ⛔ THE SAME DETECTOR WAS FIRST PUT ON BltClassThunk, AND THE
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
		// The copy count is the scale ratio (#49, REGRESSION.md:1387).
		//
		// ⛔ WE DO NOT UPSCALE (user order 2026-08-14): a runtime upscaler
		// would be unbounded and would end the property that every scaled
		// pixel comes from a diffable build step. AND THIS BLT CANNOT
		// STRETCH ANYWAY - see gBltScale below: a 2538x6102 dest changed
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
					// ⛔ srcW != texW IS LOAD-BEARING. A full-bitmap 1:1 draw has
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
						// ⛔ THE FIRST PRE-FILL USED THE ORIGINAL RECTS AND THAT WAS WRONG.
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
	int gBltScale = 0;   // DISABLED: a3 (dest rect) proved NOT the size lever -
	                     // a 2538x6102 dest gave zero change => Blt is a 1:1 copy
	                     // clipped to dest; on-screen size = SOURCE buffer size.

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
		// SCALE FIRST, then log the MODIFIED a3 so we prove the write reaches the
		// real Blt. TEST at 3x so any real effect is unmistakable (2x could grow
		// mostly off the bottom of the screen and look "unchanged"). If a3 logs
		// as 3x here but the screen is still 1x, the dest is being CLIPPED to the
		// window bounds and the window size (parent clip) is the true clamp.
		int before2 = -1, before3 = -1;
		if (gBltScale && a3)
		{
			int32_t* r = reinterpret_cast<int32_t*>(a3);
			if (r[2] > 0 && r[3] > 0 && r[2] < 4000 && r[3] < 4000)
			{
				before2 = r[2]; before3 = r[3];
				r[2] *= 3;
				r[3] *= 3;
			}
		}
		if (gBltLog < 8)
		{
			gBltLog++;
			int r1[4] = { 0,0,0,0 }, r2[4] = { 0,0,0,0 }, r3[4] = { 0,0,0,0 };
			const bool ok1 = SafeRead4(a2, r1);
			const bool ok2 = SafeRead4(a3, r2);
			const bool ok3 = SafeRead4(a4, r3);
			Logger::Get().WriteLine(LogLevel::Debug,
				"UiSpike: DBLT this=%p a1=%p srcA2=(%d,%d,%d,%d ok%d) "
				"dstA3_before=(%d,%d) dstA3_now=(%d,%d,%d,%d ok%d) a4=%p(%d,%d,%d,%d ok%d)",
				self, a1,
				r1[0], r1[1], r1[2], r1[3], ok1 ? 1 : 0,
				before2, before3,
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
	// ⛔ THE TWO PREVIOUS PROBES WERE ON CHANNELS THAT NEVER RAN.
	//   BltClassThunk  - buffer-class slot 29. Armed and executing, but a
	//                    3m14s city session produced under 2000 blits: the
	//                    shared buffer class barely draws the HUD at all.
	//   BltStripThunk  - the strip draw-context's slot 29, and installed ONLY
	//                    inside SlotThunk<88> when gStripProbe > 0, a key that
	//                    was never set. Zero lines, by construction.
	// Both cost the user a launch. This one is different for a reason that can
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
		// ⚠ TWO DIFFERENT WIDGETS, and the docs are explicit that they are NOT
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
		//     their class is reachable, but ⛔ THEY WILL NOT REPORT YET AND THAT
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
						// ⛔ FIRST ATTEMPT READ BACK BLANK (colours=1). The
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

	typedef uintptr_t(__fastcall* FgThunkFn)(void*, void*);
	FgThunkFn const kFgThunks[kFgMax] = {
		&FlashGuardThunk<0>, &FlashGuardThunk<1>, &FlashGuardThunk<2>,
		&FlashGuardThunk<3>, &FlashGuardThunk<4>, &FlashGuardThunk<5>,
		&FlashGuardThunk<6>, &FlashGuardThunk<7>, &FlashGuardThunk<8>,
		&FlashGuardThunk<9>, &FlashGuardThunk<10>, &FlashGuardThunk<11>,
	};

	// Patch one class vtable's Plot (slot 88) with the guard. Idempotent;
	// refuses our own instance copies; capped at kFgMax classes.
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
	bool IsOnScreen(cIGZWin* w, int guard = 24)
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

	// THE THREE-TWIN GATE (task #89). Window id 0x0BC3B559 is NOT unique -
	// the HUD dock and the U-Drive-It dashboard both host a cSC4WinMiniMap
	// under it. Today the two are told apart by SEARCH SCOPE alone, with
	// nothing asserting that the scope actually held; when the search was
	// global (pre-v2.22.3) it silently reached the dashboard's instance while
	// driving and left the dock's surface un-recreated. Both logged
	// "128x128", so the log could not tell them apart either.
	//
	// This walks the parent chain and proves the instance really belongs to
	// the root we scoped to, so a future widening of either search is caught
	// by an assertion instead of by a user report months later.
	bool IsDescendantOf(cIGZWin* w, cIGZWin* ancestor, int guard = 24)
	{
		if (!w || !ancestor) { return false; }
		while (w && guard-- > 0)
		{
			if (w == ancestor) { return true; }
			cIGZWin* parent = w->GetParentWin();
			if (parent == w) { break; }   // defensive: self-parent
			w = parent;
		}
		return false;
	}

	// The immediate parent's id, for the log line that the MINIMAP comment
	// has claimed since v2.22.3 was already printed - it was not.
	uint32_t ParentIdOf(cIGZWin* w)
	{
		cIGZWin* p = w ? w->GetParentWin() : nullptr;
		return (p && p != w) ? p->GetID() : 0u;
	}

	// MMBUF (v2.41.4, task #89). THE PRIVATE PAINT BUFFER, not the display
	// surface. The dock minimap ships winflag_pbuff=yes, and our own measured
	// law from the U-Drive-It gauges (#46/#47) says a pbuff at [win+0x6c] is
	// ALLOCATED AT FIRST PAINT from the window's then-current size. If the
	// game paints the minimap once at 64x64 and our sweep then resizes the
	// window to 128x128, every later draw composites through a 64x64 buffer -
	// which is the "corrupted map" the user sees, and it would persist until
	// something forces a reallocation (dismissing the load-warning modal).
	//
	// This logs the buffer's REAL dimensions at three points around our
	// resize. Read-only, SEH-guarded, one line each, capped per city.
	// It settles the question the last three attempts all guessed at:
	// geometry, timing and art were never the defect if this reads 64x64
	// while the window reads 128x128.
	// v2.41.6. TWO PREVIOUS PROBES WERE WRONG AND BOTH SAID SO IN THE LOG -
	// which is the point of a log-only build. [win+0x6c] is the DRAW CONTEXT,
	// not a pixel buffer (our own note, ~:4988). And cIGZWin vtable slots
	// "92/93" are NOT GetDrawContext/GetBufferToDrawTo: slot 93 returned
	// [+0x6c] verbatim and slot 92 returned NULL, so the slot list in this
	// file's header comment is off by one. (That comment also calls 87..97
	// "exactly the zero-arg draw group" while listing SetBufferToDrawTo and
	// SetAreaToDrawTo, which take arguments - it is not trustworthy, and
	// calling a wrong-arity __thiscall slot corrupts the stack.)
	//
	// So: NO vtable guessing. Only the offsets our own research MEASURED for
	// cSC4WinMiniMap (SC4-UI-ENGINE.md ~:310 + the MINIMAP block below):
	//   [+0xE4]  blitSize (int32)         - self-updates via the SetArea override
	//   [+0xF0]  display surface POINTER  - one-shot Init; we destroy+recreate
	//   [+0x114] render buffer, EMBEDDED  - our fallback calls
	//                                       0x7A7570(this+0x114, w, h)
	//   [+0x104] zoom (int32)
	//   [+0xFD] [+0xFE] dirty flags
	int gMmBufLogged = 0;
	void LogMinimapBuffer(const char* when, cIGZWin* pMM)
	{
		if (!pMM || gMmBufLogged >= 12) { return; }
		gMmBufLogged++;
		uint8_t* raw = reinterpret_cast<uint8_t*>(pMM);

		int32_t blit = -1, zoom = -1, fd = -1, fe = -1, fc = -1;
		void* surf = nullptr;
		void* rptr = nullptr;
		int32_t rw = -1, rh = -1;
		__try
		{
			blit = *reinterpret_cast<int32_t*>(raw + 0xE4);
			surf = *reinterpret_cast<void**>(raw + 0xF0);
			fc = raw[0xFC];   // one-shot init latch (set at 0x7A8B50); it also
			                  // gates the message SUBSCRIPTION at 0x7A714D
			fd = raw[0xFD];
			fe = raw[0xFE];
			zoom = *reinterpret_cast<int32_t*>(raw + 0x104);
			// ⛔ [+0x114] IS NOT A COM OBJECT. It is a PLAIN 3-DWORD STRUCT -
			// {pixel pointer, w, h} - exactly as our own fallback uses it:
			// 0x007A7570(raw + 0x114, w, h) treats ecx as that struct, and the
			// bake reads it as a raw base (0x7A8550: mov esi,[ebx+0x114]).
			//
			// v2.41.6 passed raw+0x114 to SafeBufProbe, which does a VIRTUAL
			// call (QueryInterface). That loads the FIRST PIXEL of the map
			// raster as a vtable pointer and calls through it - a wild
			// indirect call, caught by SEH only by luck, and the exact hazard
			// this file's SAFETY note at ~:100 warns about. It also made every
			// `rbuf` field in the v2.41.6/.7 logs meaningless. Plain reads now.
			rptr = *reinterpret_cast<void**>(raw + 0x114);
			rw = *reinterpret_cast<int32_t*>(raw + 0x118);
			rh = *reinterpret_cast<int32_t*>(raw + 0x11C);
		}
		__except (EXCEPTION_EXECUTE_HANDLER)
		{
			blit = -2;
		}

		// The DISPLAY SURFACE at [+0xF0] IS a real COM buffer - QI works on it
		// (measured: qi=1 in every run), so probing it this way is correct.
		int sq = -1, sw = -1, sh = -1, sb = -1;
		if (surf) { SafeBufProbe(surf, &sq, &sw, &sh, &sb); }

		// Sample the raster's actual PIXELS. If our Fill left the surface all
		// black yet the user sees colour, the pixels have to come from
		// somewhere - this says whether the raster holds real map data,
		// uninitialised heap, or nothing. Reads only; no calls.
		// ⚠ SAMPLE THE MIDDLE, ON A DIAGONAL - v2.41.11 fix to my own probe.
		// v2.41.8 sampled p[0], p[n/4], p[n/2], p[n-1]. For a 64-wide raster
		// n/4=1024 and n/2=2048 are EXACT MULTIPLES OF THE WIDTH, so both land
		// on COLUMN 0: three of four samples were the border. That produced
		// four identical greys and I read it as "the raster is blank", which
		// is not what it showed. Sample a diagonal through the CENTRE instead,
		// and report how many DISTINCT values we saw - one number that says
		// "real image" vs "uniform fill" without me eyeballing hex.
		uint32_t px[5] = { 0, 0, 0, 0, 0 };
		int distinct = -1;
		if (rptr && rw > 0 && rh > 0 && rw < 4096 && rh < 4096)
		{
			__try
			{
				const uint32_t* p = reinterpret_cast<const uint32_t*>(rptr);
				const int cx = rw / 2, cy = rh / 2;
				px[0] = p[cy * rw + cx];                    // dead centre
				px[1] = p[(rh / 4) * rw + (rw / 4)];        // upper-left quad
				px[2] = p[(rh * 3 / 4) * rw + (rw * 3 / 4)];// lower-right quad
				px[3] = p[cy * rw + (rw / 4)];              // mid-left of centre
				px[4] = p[(rh / 4) * rw + (rw * 3 / 4)];    // upper-right quad
				distinct = 0;
				for (int i = 0; i < 5; i++)
				{
					bool seen = false;
					for (int j = 0; j < i; j++) { if (px[j] == px[i]) { seen = true; break; } }
					if (!seen) { distinct++; }
				}
			}
			__except (EXCEPTION_EXECUTE_HANDLER)
			{
				distinct = -2;
			}
		}

		// ===== MMGRID: ACTUALLY LOOK AT THE BUFFER (2026-08-06) =====
		// ⛔ THE FIVE-POINT DIAGONAL ABOVE CANNOT LOCATE A BLOCK. It samples
		// (32,32),(16,16),(48,48),(16,32),(48,16) - five pixels out of 4096 -
		// and an hour was spent theorising about a corrupt corner from those
		// five values, twice reaching a conclusion the buffer itself refutes.
		// A probe that cannot see the reported artefact is not evidence about
		// it either way (law: a null is not evidence; state the control).
		//
		// This walks a 16x16 grid over BOTH the raster and the display surface
		// and prints a picture, plus the bounding box of reddish pixels. It
		// answers the two questions no amount of reasoning has settled:
		//   1. WHERE is the red block, in buffer coordinates?
		//   2. Is it in the RASTER (so the bake put it there) or only in the
		//      SURFACE (so the raster->surface transfer did)?
		// Legend: R reddish  G greenish  B blueish  # bright/plate  . dark
		auto dumpGrid = [](const char* tag, const void* base, int w, int h)
		{
			if (!base || w <= 0 || h <= 0 || w > 4096 || h > 4096) { return; }
			char rows[16][17] = {};
			int rl = w, rt = h, rr = -1, rb = -1, nred = 0;
			__try
			{
				const uint32_t* p = static_cast<const uint32_t*>(base);
				for (int gy = 0; gy < 16; gy++)
				{
					const int y = (gy * h) / 16;
					for (int gx = 0; gx < 16; gx++)
					{
						const int x = (gx * w) / 16;
						const uint32_t v = p[y * w + x];
						const int r = (v >> 16) & 0xFF;
						const int g = (v >> 8) & 0xFF;
						const int b = v & 0xFF;
						char c;
						if (r > 60 && r > g * 2 && r > b * 2) { c = 'R'; }
						else if (g > 60 && g > r + 20 && g > b + 20) { c = 'G'; }
						else if (b > 60 && b > r + 20 && b > g + 20) { c = 'B'; }
						else if (r > 150 && g > 150 && b > 150) { c = '#'; }
						else { c = '.'; }
						rows[gy][gx] = c;
						if (c == 'R')
						{
							nred++;
							if (x < rl) { rl = x; }
							if (x > rr) { rr = x; }
							if (y < rt) { rt = y; }
							if (y > rb) { rb = y; }
						}
					}
					rows[gy][16] = 0;
				}
			}
			__except (EXCEPTION_EXECUTE_HANDLER) { return; }
			Logger& lg = Logger::Get();
			lg.WriteLine(LogLevel::Info,
				"UiSpike: MMGRID %s %dx%d - reddish cells %d/256%s",
				tag, w, h, nred,
				nred ? "" : "  (NONE - this buffer is not the red one)");
			for (int gy = 0; gy < 16; gy++)
			{
				lg.WriteLine(LogLevel::Info, "UiSpike: MMGRID %s |%s|",
					tag, rows[gy]);
			}
			if (nred)
			{
				lg.WriteLine(LogLevel::Info,
					"UiSpike: MMGRID %s reddish bbox = (%d,%d)..(%d,%d) of %dx%d",
					tag, rl, rt, rr, rb, w, h);
			}

			// ===== NAME THE COLOURS (2026-08-06) =====
			// The grid proved the red region is DETERMINISTIC - byte-identical
			// across two separate game sessions - so it is NOT uninitialised
			// heap. Something WRITES it, the same way every time. Classifying
			// pixels as "reddish" cannot say what they are; a histogram can.
			// Top half vs bottom half, because the split is exactly halfway.
			for (int half = 0; half < 2; half++)
			{
				uint32_t val[8] = {};
				int cnt[8] = {};
				int used = 0, total = 0;
				const int y0 = half ? h / 2 : 0;
				const int y1 = half ? h : h / 2;
				__try
				{
					const uint32_t* p = static_cast<const uint32_t*>(base);
					for (int y = y0; y < y1; y += 2)
					{
						for (int x = 0; x < w; x += 2)
						{
							const uint32_t v = p[y * w + x];
							total++;
							int i = 0;
							for (; i < used; i++) { if (val[i] == v) { cnt[i]++; break; } }
							if (i == used && used < 8) { val[used] = v; cnt[used] = 1; used++; }
						}
					}
				}
				__except (EXCEPTION_EXECUTE_HANDLER) { continue; }
				// simple selection sort, 8 entries
				for (int a = 0; a < used; a++)
				{
					for (int b = a + 1; b < used; b++)
					{
						if (cnt[b] > cnt[a])
						{
							int tc = cnt[a]; cnt[a] = cnt[b]; cnt[b] = tc;
							uint32_t tv = val[a]; val[a] = val[b]; val[b] = tv;
						}
					}
				}
				char buf[220] = {};
				int off = 0;
				for (int i = 0; i < used && i < 6 && off < 180; i++)
				{
					off += _snprintf_s(buf + off, sizeof(buf) - off, _TRUNCATE,
						"%08X x%d  ", val[i], cnt[i]);
				}
				lg.WriteLine(LogLevel::Info,
					"UiSpike: MMHIST %s %s-half y[%d,%d) sampled=%d distinct>=%d | %s",
					tag, half ? "BOTTOM" : "TOP", y0, y1, total, used, buf);

				// ===== RAW BYTES (2026-08-06) =====
				// The histogram showed the bad region is `00 00 VV FF` per
				// pixel - green and blue always zero, only the red byte varying
				// - while a good pixel is `00 VV 00 00`. Same shape, ONE BYTE
				// higher. That is an alignment/stride signature, not garbage
				// and not a palette. Print the actual bytes of 8 consecutive
				// pixels from one row of each half so the offset can be read
				// off directly instead of inferred from a classifier.
				__try
				{
					const uint8_t* bp = static_cast<const uint8_t*>(base);
					const int y = y0 + (y1 - y0) / 2;
					const uint8_t* row = bp + (size_t)y * w * 4;
					char hex[160] = {};
					int ho = 0;
					for (int i = 0; i < 8 && ho < 140; i++)
					{
						ho += _snprintf_s(hex + ho, sizeof(hex) - ho, _TRUNCATE,
							"%02X%02X%02X%02X ", row[i * 4 + 0], row[i * 4 + 1],
							row[i * 4 + 2], row[i * 4 + 3]);
					}
					lg.WriteLine(LogLevel::Info,
						"UiSpike: MMBYTES %s %s y=%d x0..7 (mem order b0 b1 b2 b3) | %s",
						tag, half ? "BOTTOM" : "TOP", y, hex);
				}
				__except (EXCEPTION_EXECUTE_HANDLER) {}
			}
		};
		dumpGrid("raster ", rptr, rw, rh);
		{
			// The surface is a COM buffer; its pixels live behind the same
			// [+0x3c] ptr / [+0x40] stride pair the flyout atlas uses.
			void* sp = nullptr; int stride = 0;
			if (surf && sq == 1 && sw > 0 && sh > 0)
			{
				__try
				{
					uint8_t* sb2 = reinterpret_cast<uint8_t*>(surf);
					sp = *reinterpret_cast<void**>(sb2 + 0x3c);
					stride = *reinterpret_cast<int32_t*>(sb2 + 0x40);
				}
				__except (EXCEPTION_EXECUTE_HANDLER) { sp = nullptr; }
			}
			if (sp && stride == sw * 4) { dumpGrid("surface", sp, sw, sh); }
			else if (sp)
			{
				Logger::Get().WriteLine(LogLevel::Info,
					"UiSpike: MMGRID surface SKIPPED - stride %d != w*4 (%d); "
					"grid walker assumes packed rows.", stride, sw * 4);
			}
		}

		const int32_t winW = pMM->GetW();
		Logger::Get().WriteLine(LogLevel::Debug,
			"UiSpike: MMBUF %-16s win=%dx%d blit=%d zoom=%d fc=%d fd=%d fe=%d | "
			"surf[+0xF0]=%p %dx%d bpp=%d qi=%d | raster[+0x114]=%p %dx%d "
			"centre-diag px=%08X,%08X,%08X,%08X,%08X distinct=%d%s",
			when, winW, pMM->GetH(), blit, zoom, fc, fd, fe,
			surf, sw, sh, sb, sq, rptr, rw, rh,
			px[0], px[1], px[2], px[3], px[4], distinct,
			((sq == 1 && sw > 0 && sw != winW) || (rw > 0 && rw != winW))
				? "   <<< A BUFFER DOES NOT MATCH THE WINDOW" : "");
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
		// user-confirmed on the v2.11.24 test). Hit-tests never run inside the
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
			// check (GetWidth vs window) fails -> Plot releases + recreates it ->
			// Init runs -> InitThunk doubles the physical size. Plot re-Inits with
			// the real window size, so the 0x1c corruption is transient.
			if (gHideRing)
			{
				mm[0x3b] = 0;   // [0xec] ring width  -> 0 (ring not drawn)
				mm[0x3c] = 0;   // [0xf0] ring height -> 0
				reinterpret_cast<uint8_t*>(self)[0x114] |= 1;
			}
			if (gForceRecreate)
			{
				void* buf = reinterpret_cast<void*>(static_cast<uintptr_t>(
					static_cast<uint32_t>(mm[0x37])));
				const int winW = mm[0x2c] - mm[0x2a];   // current window width (282)
				// Only force a recreate while the buffer is STALE (cached width !=
				// the window — e.g. the 141 buffer left from an early small window).
				// Corrupt [0x1c] so Plot's validity fails -> it recreates at the 282
				// window -> buffer becomes 282 (2x the stale 141). Once it matches,
				// stop -> validity passes -> stable (no per-frame recreate loop).
				if (buf && reinterpret_cast<int32_t*>(buf)[7] != winW * gInitScale)
				{
					reinterpret_cast<int32_t*>(buf)[7] = 0x7FFF;   // [0x1c] bogus
					reinterpret_cast<uint8_t*>(self)[0x114] |= 1;  // dirty
				}
			}
			bltDst = reinterpret_cast<void*>(static_cast<uintptr_t>(
				static_cast<uint32_t>(mm[0x1A])));
			if (bltDst)
			{
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

		// Patch the buffer CLASS vtable's Init slot for the DURATION of this Plot
		// only (restored immediately after), so buffer (re)creation inside Plot
		// allocates at gInitScale x. Scoped to the disaster container (IDX==88).
		if (IDX == 88 &&
			(gInitScale != 1 || gClassBltLog < 20 || gClassHalveRing ||
			 gRingScale > 1 || gDrawCtxLog < 3 || (gDumpAtlas && !gAtlasDumped) ||
			 gRing2xBlit))
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
				if (gInitScale != 1)
				{
					if (!gCtxOrigInit)
						gCtxOrigInit = reinterpret_cast<InitFn>(kBufClassVt[3]);
					gBufSavedInit = kBufClassVt[3];
					kBufClassVt[3] = reinterpret_cast<void*>(&InitThunk);
				}
				if (gClassBltLog < 20 || gClassHalveRing || gRingScale > 1 ||
					gDrawCtxLog < 3 || (gDumpAtlas && !gAtlasDumped) || gRing2xBlit)
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
		}

		const uintptr_t ret = gOrigSlot[IDX](self);

		if (IDX == 88 && gBufSavedInit)
		{
			kBufClassVt[3] = gBufSavedInit;   // restore Init immediately
			gBufSavedInit = nullptr;
		}
		if (IDX == 88 && gClassBltSaved)
		{
			kBufClassVt[29] = gClassBltSaved; // restore class Blt immediately
			gClassBltSaved = nullptr;
		}
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
			s68 = *reinterpret_cast<void**>(reinterpret_cast<char*>(self) + 0x68);
			if (s68)
			{
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

namespace
{
	const int kMaxDepth = 8;
	const int kMaxWindows = 1500;
	// v2.25.0 (task #53, code-created audit 2026-07-29): 96 was 79% consumed
	// by ONE popup (the ordinance list family) while four installed ordinance
	// mods keep adding rows to it - and an overflow is SILENT, making the
	// verify pass read the dropped children as dead. 256 gives ~3.3x the
	// worst measured consumer; ChildSnapshot::Callback now logs (once) if it
	// is ever hit anyway.
	const int kMaxChildrenPerLevel = 256;

	const uint32_t kGZWin_WinSC4App = 0x6104489A;
	const uint32_t kGZWin_SC4View3DWin = 0x9A47B417;
	const uint32_t kGZWin_MenuContainer = 0xAA32BCE6;
	// Boot-dump proven (region screen recon): the region UI host is
	// 0xEA659793 (13 children: legend, region panel, button clusters,
	// compass, hidden flyouts). 0x2AAB8CC1 exists there but is empty+hidden.
	const uint32_t kGZWin_RegionScreen = 0xEA659793;

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
		for (uint32_t known : kRegionPanelIds)
		{
			if (id == known) { return true; }
		}
		return false;
	}

	// NEVER scaled (user click-through 2026-07-21): windows whose content is
	// game-tiled or exemplar-art-bound at 1x, where doubling the frame makes
	// things WORSE until that art can be doubled. They stay stock size, and
	// stock-positioned by the game (flyouts hug their spawn button).
	//
	// ⚠ READ THE NAME AS "NEVER SCALED **BY THE SWEEP**" (clarified v2.39.12,
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
		// zoning/utilities flyout columns REMOVED 2026-07-22: their item
		// icons now ship 2x via z_SC4UIScale_ItemIcons-2x.dat (266 icons,
		// property 0x8A2602B8 art), so the doubled slots get doubled art.
		// 0x698894D3 My Sims strip - REMOVED from this list in v2.22.0
		// (2026-07-29 night, user report "MySims menus corrupted and
		// crashing", blocking U-Drive-It). The deferral had become the BUG:
		// the sweep scaled the sibling content panel 0xCA1F1D9C (log:
		// (149,1413 861x134) -> (298,1226 1722x268)) while this root stayed
		// 1x, so the composed pair (glued by the 0x0000AAAA marker inside
		// 0x698894D3) tore apart - scattered title band + detached slot
		// blocks. Three of the family's arts were ALREADY 2x-in-place
		// (ABB172FA/FB + 8BB230D4, shared with swept Sim-mode panels), so
		// pure-1x was no longer reachable either. Full family treatment:
		// SCALED_WINDOW_IDS (art) + kAlwaysScaleCityIds (pre-scale while
		// hidden). Watch on verify: the PORTRAITS are runtime-generated
		// images - if they tile/repeat inside doubled slots, that is the
		// original deferral concern and needs a slot-pitch code hook.
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
		// huge-empty-panel look the user reported.
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
		0x27DF05BE, // #191 Move In My Sim marker, green twin - born
		            // correct from the data-scaled I-6a9455c9
		0x27DF05BF, // 46x97 tiled plaque (I-6a9455c9), backing image
		            // {46a006b0,13f15214} + a 36x41 icon inset at (5,5).
		            // ⚠ ONLY the ...BF twin. 0x27DF05BE is NOT here on
		            // purpose: that id is ALSO the root of the Obliterate
		            // City confirm (I-2a41436c), which we already ship
		            // DATA-SCALED via build_dialog_static.py:280. One id,
		            // two different windows - listing BE would reach the
		            // wrong one (law: match the family THEN check the host).
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
		// v2.39.5: these two comments were SWAPPED for weeks (every other site
		// in the file has them the right way round - kGodFlyoutDock :7008-7009,
		// GOD-MODE-FLYOUTS.md). Caught by the exe re-verification 2026-07-31.
		0xCA35CBED, // terrain-effect flyout   (direct view child)
		0x49923239, // terraform tool flyout   (direct view child)
		// 0x0A78827A REMOVED v2.12.2: it is the FOUNDED-CITY GOD TOOLBAR (see
		// kGodPanelIds), not a flyout. Listing it here made the city sweep skip
		// it, so it rendered at dead stock 74x291 while everything around it
		// was 2x.
		// 0xABB26B0E REMOVED v2.12.1: it is a bottom-anchored god PANEL (see
		// kGodPanelIds), not a flyout. Listing it here made the city sweep skip
		// it, so it only ever got the size-only treatment that pushed it off
		// the bottom of the screen in a founded city. Day/Night rendering rides
		// on 0xCA35CBED and is unaffected by this move.
	};
	inline bool IsGodToolFlyoutId(uint32_t id)
	{
		for (uint32_t known : kGodToolFlyoutIds)
		{
			if (id == known) { return true; }
		}
		return false;
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
	inline bool IsGodPanelId(uint32_t id)
	{
		// 0xABB26B0E is ini-gated (default OFF) - see gScaleAbbPanel. Scaling and
		// docking it to (6,490) covers the minimap dock, and it did not fix the
		// founded-city god mode it was added for (0x0A78827A did).
		if (id == 0xABB26B0E && gScaleAbbPanel == 0)
		{
			return false;
		}
		for (uint32_t known : kGodPanelIds)
		{
			if (id == known) { return true; }
		}
		return false;
	}

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
	// USER DIRECTION 2026-08-04: "ALL OF THE UI ELEMENTS SHOULD BE DOCKED VIA
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
	// THE OFFSET IS MEASURED AT THE USER-CONFIRMED TIER AND SCALED. offX/offY
	// are in the anchor's own SCALED pixels at f=2 (the tier the user has
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
		// and the expansion arrow at 2x AND 3x (user-reported).
		//
		// THE DESIGN SAYS BOTTOM-DOCK, and the .UI proves it. Comparing the two
		// scripts that share this band id - Graphs I-6bc9065a vs Data Views
		// I-ea2871aa, the panel the user pointed at as correct:
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
		// ⚠ ANCHOR LIFETIME IS PART OF THE DOCK. v2.89.0 briefly anchored this
		// to 0x8A8B5B72 - correct arithmetic, wrong window. ApplyPanelDocks
		// bails on !pAnchor->IsVisible(), and the log shows 0x8A8B5B72 opening
		// NINETEEN SECONDS after the band:
		//     13:45:04.291  open #1 of 0x8A8B5B71  <- chart, opens WITH the band
		//     13:45:04.291  open #1 of 0x0A4A8176  <- the band
		//     13:45:23.845  open #1 of 0x8A8B5B72  <- the bad anchor
		// so the band painted undocked until the user clicked something. An
		// anchor must be alive whenever its child is, or the dock is born late
		// by construction - the #50/#76 born-correct law applied to the ANCHOR.
		//
		// 0x8A8B5B71 carries the SAME bottom relationship in the design
		// (band.bottom - chart.bottom = -10) and opens simultaneously, so it
		// gives an identical target: at f=3, 2004 - 321 - rhu(10*3) = 1653,
		// the value the 0x8A8B5B72 route produced and the user confirmed.
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
		//   USER-CONFIRMED 2026-07-28. Shares its id with the GOD terraform
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
		// ⚠ v2.39.5: this is the ONE flyout still on GENERATION 1 - it opens
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
		for (uint32_t known : kSubFlyoutIds)
		{
			if (id == known) { return true; }
		}
		return false;
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
		// ⛔ DO NOT MOVE THIS TO kNeverScaleIds. That was tried on
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
		// #95 PHASE 4: 0x699306ED (civic) and 0xCA35CBED (terrain-fx /
		// day-night) REMOVED - they were dead entries advertising coverage
		// they could not deliver. Both are `continue`d earlier in the same
		// loop (IsMayorOnlyFlyoutId / IsGodToolFlyoutId), so they could
		// never reach this list's visibility exception. Each is really
		// covered by its OWN mechanism (kMayorFlyoutDock / kGodFlyoutDock),
		// and Test-BornCorrectCoverage now reports them that way instead of
		// being told a comforting falsehood by this list.
		0x4BCB938A, // U-Drive-It dashboard console (43 vehicle scripts)
		0xABB26B0E, // Sim-mode left sidebar
		// #90 (v2.42.0): ships 2x art (SCALED_WINDOW_IDS) but had NO
		// born-correct route - the only one of the 50, caught by the audit
		// and now guarded by _tests\Test-BornCorrectCoverage.ps1. The gen-2
		// precondition is MEASURED, not assumed: both golden dumps show it
		// resident as a direct view child from city load, pos(489,894)
		// 532x640 vis=0 (live script = CoriBoom's 36-slot 532x640, not stock
		// 531x406; the #44 ThirdPartyUI gate still governs which art ships).
		// Opened by button 0xABC54125 on composite 0xE9889775. ⚠ The panel
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
		for (uint32_t known : kAlwaysScaleCityIds)
		{
			if (id == known) { return true; }
		}
		return false;
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
		// ⚠ THE MECHANISM, STATED NO STRONGER THAN THE EVIDENCE. The task
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
		// ⚠ INSURANCE, NOT A SIGHTING. No dump in the repo contains this id
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
		// ⚠ #102 COMMENT-ONLY CORRECTION (2026-08-03). The three labels
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
		// ⛔ THE HUD DOCK 0x0987B48F IS **NOT** A MEMBER, AND MUST NEVER BE.
		// v2.41.1 added it and BROKE THE DOCK AND EVERY FLYOUT (user-reported,
		// same session, reverted in v2.41.2). Membership makes ScalePanelRoot
		// RETURN EARLY at the dock root - and the god/mayor flyout DOCKING
		// logic lives inside that child recursion, so the flyouts lost the
		// machinery that positions them against their spawn buttons.
		// The dock's minimap is instead born 2x as a SINGLE WINDOW; see
		// kDataScaledWindowIds below.
	};
	// ⛔ THERE IS NO kDataScaledWindowIds, AND THE DOCK MUST NOT GET ONE.
	// v2.41.2 added a single-window form (minimap 0x0BC3B559 born 2x in data,
	// sweep skips just that window, recursion continues) specifically to avoid
	// v2.41.1's flyout breakage. It fixed the flyouts and BROKE THE MINIMAP A
	// DIFFERENT WAY: the dock's rect is the UNION OF ITS CHILDREN WITH NO
	// CLAMP (CITY-DOCK-OVERLAP.md), so a child pre-doubled to (36,144)-(164,272)
	// hangs past the 235x223 design frame, the union grows, and the
	// bottom-anchored dock drags the map outside the window (user-reported).
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
		for (uint32_t known : kFontSizedIds)
		{
			if (id == known) { return true; }
		}
		return false;
	}
	inline bool IsDataScaledSubtreeId(uint32_t id)
	{
		for (uint32_t known : kDataScaledSubtreeIds)
		{
			if (id == known) { return true; }
		}
		return false;
	}
	inline bool IsNeverScaleId(uint32_t id)
	{
		for (uint32_t known : kNeverScaleIds)
		{
			if (id == known) { return true; }
		}
		return false;
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
		// MY SIMS story lists (v2.22.2). REGRESSION.md carried an explicit
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
		for (uint32_t known : kAdviceListScaleSelfIds)
		{
			if (id == known) { return true; }
		}
		return false;
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
		for (uint32_t known : kAdviceListNeverTouchIds)
		{
			if (id == known) { return true; }
		}
		return false;
	}

	// Region DIALOG DOCKING (user feedback 2026-07-21): these transients are
	// .UI-placed at fixed 800x600-era design coords, so at native res they
	// open small and detached from the buttons that spawn them. Each one is
	// scaled 2x once per appearance and MOVED under its spawn button
	// (position computed from the live, already-doubled flyout geometry).
	// Dialog root ids recovered from the .UI scripts by caption.
	struct DialogDock
	{
		uint32_t dialogId;
		uint32_t flyoutId;  // region-host child hosting the spawn button
		uint32_t buttonId;
	};
	const DialogDock kRegionDialogDocks[] = {
		{ 0x4A5BA0E7, 0x09EBEE45, 0x2A5B0001 }, // Load Region   <- open-folder
		{ 0xEA5BA0D1, 0x09EBEE45, 0x2A5B0000 }, // Create Region <- new-region
		{ 0x6A5BA20C, 0x09EBEE45, 0x2A5B0002 }, // Delete Region <- trash
		{ 0x2A57DB82, 0x09EBEE60, 0x0A5510A9 }, // Play Options  <- gears
		{ 0xEA53F5DB, 0x09EBEE60, 0xA98F4F88 }, // Audio Options <- speaker
		{ 0x2A57CB82, 0x09EBEE60, 0x098F4F6C }, // Graphic Opts  <- monitor
	};
	const int kDialogDockCount =
		static_cast<int>(sizeof(kRegionDialogDocks) / sizeof(kRegionDialogDocks[0]));

	inline int32_t Abs32(int32_t v) { return v < 0 ? -v : v; }

	// Rounding-correct scaling. Truncation happens to be exact at f=2.0
	// (bit-identical results) but drifts at non-integer factors (1.5x).
	//
	// ⛔ HALF-UP, NOT HALF-AWAY-FROM-ZERO. THIS IS #162, AND THE FIX WAS
	// ALREADY WRITTEN AT THE TOP OF THIS FILE - IT JUST NEVER REACHED HERE.
	//
	// This was std::llround. llround rounds half AWAY FROM ZERO, so a span
	// that straddles the origin has BOTH its edges pushed outward and comes
	// out ONE PIXEL LONGER than the same span scaled as a length:
	//
	//     dashboard button 0x2988bc85, absolute design T = -11, h = 50
	//     llround:  R(39*1.5=58.5)=59  R(-11*1.5=-16.5)=-17  ->  h = 76
	//     the art:  ScaleDim(50, 1.5)                        ->  h = 75
	//                                                     ONE UNCOVERED ROW
	//
	// which is the "phantom line under the mayor's hat", and the same
	// asymmetry moves a negative-origin parent's whole subtree by a pixel
	// against its own background art (the advisor-portrait line). Both were
	// reported as 1.5x-only, and that is structural, not luck: at f=2 and
	// f=3 the product v*f is an exact integer, the two rules are identical,
	// and NOTHING changes. Measured over all 2920 nodes of the shipped .UI
	// corpus: f=2 -> 0 size and 0 position changes; f=3 -> 0 and 0;
	// f=1.5 -> 8 sizes and 44 positions, in 6 files, all of them descendants
	// of the 12 nodes that have a negative absolute origin.
	//
	// RoundHalfUp (declared at the top of this file) is the art pipeline's
	// own convention - Upscale2x.exe's dimensions and the .UI builders'
	// scale_len both use floor(v + 0.5). Its comment has said since it was
	// written that it "differs from llround/ScaleRound only at NEGATIVE half
	// values" and that "the art pipeline convention wins for all tier-math
	// forms". ScaleRound was the one place still disagreeing with it, so
	// runtime geometry and shipped art could differ by a rounding rule -
	// exactly the thing that comment promised could not happen.
	//
	// Proven offline by tools/uimap/emu/gate_art_vs_window.py, which prices
	// every image-bound node against the PNG its tier actually ships:
	// with llround, 1 node is short at 1.5x and 0 at 2x; with half-up,
	// 0 and 0, and the f=2 control stays at 0 either way.
	inline int32_t ScaleRound(int32_t v, float f)
	{
		return RoundHalfUp(static_cast<double>(v) * static_cast<double>(f));
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
		for (uint32_t known : kCityHudFamilyIds)
		{
			if (id == known) { return true; }
		}
		return false;
	}

	// The leader's scaled x, clamped ONCE for the whole family. Members are
	// never clamped individually: individual clamping is exactly what shears
	// them apart today (11 of the 15 bottom panels were pulled back by
	// DIFFERENT amounts at 1400x1050, up to 90px of relative shear between
	// two siblings). Union-rect containers are ALL-OR-NONE.
	inline int32_t CityHudOriginX(int32_t frameW, float f)
	{
		int32_t origin = ScaleRound(kCityHudLeaderL, f);
		const int32_t span =
			ScaleRound(kCityHudLeaderR, f) - ScaleRound(kCityHudLeaderL, f);
		if (origin + span > frameW) { origin = frameW - span; }
		if (origin < 0) { origin = 0; }
		return origin;
	}

	// ---- #94 v2.47.0: THE MARKER'S UNIT SYSTEM IS MEASURED, NOT ASSUMED ---
	// v2.43.1/.2 docked from the live marker on the written premise that "the
	// marker is scaled with the subtree we just scaled, so its live L/T are
	// already in screen units". THE LOG REFUTED THAT, and it cost the
	// Landscape dock: with WarriorUI installed the two mod flyouts disagree
	// permanently, not transiently -
	//     0xAB954023 S&L        script (4, 5)  read live (8,10) = SCALED
	//     0x49923239 LANDSCAPE  script (3,59)  read live (3,59) = DESIGN
	// and Landscape still read (3,59) a full second and many sweep ticks
	// later, so this is not an ordering race that waiting would fix - that
	// subtree scale simply never reaches this child. Docking design units as
	// if they were screen units left the ring 59px low, on the WRONG BUTTON.
	//
	// ⛔ THE FIRST FIX FOR THIS WAS A SIZE HEURISTIC, AND THE OFFLINE GATE
	// KILLED IT BEFORE IT SHIPPED. The idea was to use the spawn button as a
	// ruler, since the alignment-marker rule says the marker is "sized like
	// the spawn button". MEASURED: that premise does not hold. S&L's marker
	// is 64 wide against a 47-design (94-live) button, so the two hypotheses
	// score 34 vs 30 - it would have guessed WRONG, and the guess would have
	// been invisible until some future mod tripped it.
	//
	// The authoritative answer is not geometric at all: WE record every
	// window we scale. See UiSpike::MarkerIsDesignUnits (a PURE READ of
	// scaleMap - deliberately not Classify(), which mutates the tug-of-war
	// counter and could tombstone a window just for asking).

	// Snapshot-then-mutate child collection: never mutate windows while the
	// parent's child list is being enumerated (whether EnumChildren
	// snapshots or live-iterates is unknowable - assume it live-iterates).
	struct ChildSnapshot
	{
		cIGZWin* wins[kMaxChildrenPerLevel];
		int count;

		static bool Callback(cIGZWin* parent, uint32_t childID, void* child, void* pContext)
		{
			ChildSnapshot* snap = static_cast<ChildSnapshot*>(pContext);
			if (snap->count < kMaxChildrenPerLevel)
			{
				snap->wins[snap->count++] = static_cast<cIGZWin*>(child);
			}
			else
			{
				// Task #53: an overflow silently DROPS children - the sweep
				// then never scales them and the verify pass reads them as
				// dead. Surface it once so the cap gets raised deliberately
				// instead of the symptom being chased as a scaling bug.
				static bool overflowLogged = false;
				if (!overflowLogged)
				{
					overflowLogged = true;
					Logger::Get().WriteLine(LogLevel::Error,
						"UiSpike: ChildSnapshot OVERFLOW - parent 0x%08X has "
						">%d children; the rest are invisible to every pass. "
						"Raise kMaxChildrenPerLevel.",
						parent ? parent->GetID() : 0u, kMaxChildrenPerLevel);
				}
			}
			return true;
		}
	};
}

struct UiSpikeEnumCtx
{
	UiSpike* spike;
	int depth;
	int* totalCount;

	static bool Callback(cIGZWin* parent, uint32_t childID, void* child, void* pContext)
	{
		UiSpikeEnumCtx* ctx = static_cast<UiSpikeEnumCtx*>(pContext);
		ctx->spike->DumpTree(static_cast<cIGZWin*>(child), ctx->depth, ctx->totalCount);
		return true;
	}
};

// ============ SUB-FLYOUT BORN-2x (v2.34.0, task #50) ============
// THE DEFECT, measured across 6 opens / 3 menus: nested plop sub-flyouts
// render 1x for 1-2 frames on EVERY open, at every depth. Three facts settle
// the mechanism, none of them guessed:
//
//  1. The ITEMS ARE NOT WINDOWS. The whole assembly is container 0x8A6E61E0 ->
//     strip 0x8A2CAD8B -> a degenerate tip layer. Menu items are BLITS into
//     the container's paint buffer. No window sweep can ever reach them - which
//     is why pre-scale-while-hidden, the SetFlag show hook and data pre-scale
//     all failed here: every one of them operates on windows.
//  2. THE FLASH IS THE BUFFER. The window rect is corrected within ~1ms, but
//     the paint buffer was already allocated from the 1x rect, so Plot #1 fills
//     a 2x window from a 1x buffer (20-36ms at the measured 54.5fps). Same law
//     as the U-Drive-It gauges. NO sweep cadence can fix this.
//  3. THE GEOMETRY IS CODE-DERIVED, not art-derived (the bitmap is loaded but
//     never read for the rect):
//         W = [+0xf0] - [+0xf8] + [+0xe4]        = 80 - 4 + 53 = 129
//         H = max(stripH, [+0xf4]) + 2*[+0xe8]   = max(stripH,53) + 50
//         stripH = count*(cell 44 + gap 5) - 5   = 49n - 5, n clamped [1,8]
//     This reproduces 8/8 observed container heights and 4/4 strip heights with
//     zero fudge - including Freight's 206, the one size that fits no
//     progression: 1 item -> 44 < the 53 floor -> 53+50=103, x2 = 206.
//
// CURE: build them at round(stock*f) so the buffer is allocated correct on
// Plot #1. The three provider constants are byte-patched (they fit imm8); the
// seven container fields are written HERE, in a trampoline on their setter
// vf10 (0x0079AC60), because [+0xf0] = 80 -> 160 cannot encode as imm8 and
// compensating with the other terms would corrupt their meaning (the 53 is
// also the IsPointInMe claim width).
//
// AND we must stop doing it twice: our own gStripFieldScale=2 and the sweep's
// subtree scale exist precisely to double these windows AFTER birth. Born-2x
// plus those still active = 4x. The lever fuses both halves for that reason -
// neither is shippable alone.
namespace
{
	typedef void(__fastcall* SubVf10Fn)(void*, void*, void*, int, int, int, int, int, int, int);
	SubVf10Fn gOrigSubVf10 = nullptr;
	bool      gSubBornInstalled = false;
	int       gSubBornLogged = 0;

	// The seven fields vf10 stores, with their stock values (art-verdict
	// table, roles taken from the stores inside vf10 - not from push order).
	struct SubField { int off; int stock; const char* what; };
	const SubField kSubFields[] = {
		{ 0xE4, 53, "bar width (also the hit-claim)" },
		{ 0xE8, 25, "end cap (x2 = the +50)" },
		{ 0xF0, 80, "ring-sprite width term" },   // <- cannot encode as imm8
		{ 0xF4, 53, "minimum content extent (Freight floor)" },
		{ 0xF8,  4, "overlap subtracted from W" },
		{ 0xFC, 27, "anchor offset (cross axis)" },
		{ 0x100,29, "anchor offset (long axis)" },
	};

	void __fastcall SubVf10Detour(void* self, void* edx, void* bmp,
		int a2, int a3, int a4, int a5, int a6, int a7, int a8)
	{
		// Let the game store its stock values first, then overwrite - the
		// original also stores the bitmap and computes [+0xec] from it, and
		// we must not disturb either.
		// ⚠ TWIN GUARD - the single most important line here. vf10 is a SHARED
		// class method: sub_7EAEB0 builds the NESTED sub-flyout (ours) and
		// sub_7E7270 builds the FIRST-LEVEL flyout from the same two classes
		// with its own copies of every constant. The first-level one is
		// already scaled after birth (gStripFieldScale / gBarDX / ClaimScale /
		// the god pre-scale), so promoting its fields here would double-scale
		// the flyouts that currently WORK. Discriminate by return address:
		// 0x007EB171 is the instruction after the sub-flyout builder's
		// `call [eax+0x10]`; the only other caller returns to 0x007E74B1.
		const uintptr_t ret = reinterpret_cast<uintptr_t>(_ReturnAddress());
		const uintptr_t modBase = reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
		const uintptr_t kSubBuilderRet = modBase - 0x400000 + 0x007EB171;
		gOrigSubVf10(self, edx, bmp, a2, a3, a4, a5, a6, a7, a8);
		if (!self || gTierF <= 1.01f) { return; }
		if (ret != kSubBuilderRet)
		{
			if (gSubBornLogged < 6)
			{
				gSubBornLogged++;
				Logger::Get().WriteLine(LogLevel::Debug,
					"UiSpike: SUBLAY ret=0x%08X - NOT the sub-flyout builder "
					"(expected 0x%08X); left at stock (twin guard).",
					static_cast<uint32_t>(ret - (modBase - 0x400000)),
					static_cast<uint32_t>(0x007EB171));
			}
			return;
		}
		char* obj = reinterpret_cast<char*>(self);
		for (const SubField& fld : kSubFields)
		{
			int32_t* p = reinterpret_cast<int32_t*>(obj + fld.off);
			// Idempotent: only promote a value still at its stock reading, so
			// a second call (or a re-populate) cannot compound.
			if (*p == fld.stock)
			{
				*p = static_cast<int32_t>(std::lround(fld.stock * gTierF));
			}
		}
		if (gSubBornLogged < 6)
		{
			gSubBornLogged++;
			Logger::Get().WriteLine(LogLevel::Debug,
				"UiSpike: SUBBORN fields x%.2f -> bar %d cap %d ring %d min %d "
				"overlap %d (W should be born %d).",
				gTierF,
				*reinterpret_cast<int32_t*>(obj + 0xE4),
				*reinterpret_cast<int32_t*>(obj + 0xE8),
				*reinterpret_cast<int32_t*>(obj + 0xF0),
				*reinterpret_cast<int32_t*>(obj + 0xF4),
				*reinterpret_cast<int32_t*>(obj + 0xF8),
				*reinterpret_cast<int32_t*>(obj + 0xF0)
					- *reinterpret_cast<int32_t*>(obj + 0xF8)
					+ *reinterpret_cast<int32_t*>(obj + 0xE4));
		}
	}
}

void UiSpike::InstallSubFlyoutBorn()
{
	if (gSubBornInstalled || settings.spikeSubFlyoutBorn2x <= 0) { return; }
	if (gTierF <= 1.01f) { return; }   // stock tier stays inert

	const uintptr_t base = reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
	void* target = reinterpret_cast<void*>(base - 0x400000 + 0x0079AC60);

	const MH_STATUS init = MH_Initialize();
	if (init != MH_OK && init != MH_ERROR_ALREADY_INITIALIZED)
	{
		Logger::Get().WriteLine(LogLevel::Error,
			"UiSpike: SUBBORN MH_Initialize failed (%d).", init);
		return;
	}
	if (MH_CreateHook(target, reinterpret_cast<void*>(&SubVf10Detour),
			reinterpret_cast<void**>(&gOrigSubVf10)) != MH_OK
		|| MH_EnableHook(target) != MH_OK)
	{
		Logger::Get().WriteLine(LogLevel::Error,
			"UiSpike: SUBBORN failed to hook sub-flyout vf10 at %p.", target);
		return;
	}
	gSubBornInstalled = true;
	// STAGE 2, fused: stop our own post-birth doubling of the same windows.
	gStripFieldScale = 1;
	Logger::Get().WriteLine(LogLevel::Info,
		"UiSpike: SUBBORN installed on vf10 %p - sub-flyouts born x%.2f; "
		"gStripFieldScale forced to 1 (was 2) so they are not doubled twice.",
		target, gTierF);
}

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
// WHAT THIS IS NOT (all measured, all reverted - REGRESSION.md "THE FLASH:
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
	// Set in ArmDeferred. The detours are free functions; the treatments they
	// need (the sweep pass, the draw-hook install) are members.
	UiSpike* gSpikeSelf = nullptr;
	bool gSubBornScaleInstalled = false;
	int  gSubBornScaleOn = 1;      // [Flyout] SubBornScale - live-tunable
	// v2.39.0 task #5: the SAME Place detour, second builder. Its own lever so
	// a mis-size can be switched off live without touching the user-confirmed
	// sub-flyout path (REGRESSION.md: size and placement must be separately
	// switchable, or a bad call forces a rebuild).
	int  gDisBornScaleOn = 1;      // [Flyout] DisBornScale - live-tunable
	int  gDisBornDockOn  = 1;      // [Disaster] BornDock - live-tunable
	int  gDisBornMetricsOn = 1;    // [Disaster] BornMetrics - live-tunable (v2.39.5)
	int  gDisBornLog = 0;          // DISBORN lines emitted (cap 10)
	int  gSubBornDockOn = 1;       // [Flyout] SubBornDock  - live-tunable
	int  gSubBornLog2 = 0;

	// The strip CONTROL object (obj+0) the builder just gave item metrics to.
	// SetItemMetrics runs ~250 instructions before Place in the SAME builder
	// call on the single UI thread, so "the last one" is unambiguous.
	void* gSubLastStrip = nullptr;
	// v2.39.1: the disaster twin gets its OWN strip pointer and base metrics.
	// gSubLastStrip / gStripBase* are single globals written by whichever
	// builder ran last; sharing them across two builders is "two writers, one
	// pointer, no ownership marker" and the fields we write are per-instance.
	void* gDisLastStrip = nullptr;
	int   gDisStripBase4 = 0, gDisStripBase8 = 0, gDisStripBaseC = 0;
	bool  gDisStripBaseCap = false;
	// v2.39.3: the dock target the sweep computes, cached so birth can apply it.
	// Pure function of the already-scaled toolbar + two ini offsets, so it is
	// identical on every tick and safe to reuse. Cleared in Disarm (a new city
	// has a new toolbar).
	int32_t gDisDockL = 0, gDisDockT = 0;
	bool    gDisDockValid = false;
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

	// The born records the sweep has not adopted yet. ScaleSubtree is made
	// idempotent by scaleMap (keyed on window pointer): a window WE scaled at
	// birth is a pointer the sweep has never seen, so without this it would be
	// classified Fresh and scaled A SECOND time (129 -> 258 -> 516). The
	// sweep drains this queue into scaleMap before it walks, which makes the
	// very next Classify() return AlreadyScaled.
	struct BornRec { void* win; uint32_t id; int32_t ow, oh, sw, sh; };
	BornRec gBornQ[8];
	int gBornQN = 0;

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
		const uintptr_t modBase =
			reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
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
		if (!self || !gSubBornScaleOn || gTierF <= 1.01f) { return; }

		// TWIN GUARD (law 32). Place is a SHARED class method: sub_7EAEB0
		// builds the nested sub-flyout and sub_7E7270 builds the FIRST-LEVEL
		// Create Disaster flyout from the same class - SAME TWO VTABLES, so the
		// return address is the only discriminator.
		//
		// v2.39.0 (task #5): the disaster twin is now handled HERE too. The
		// v2.36.0 comment said it was "already scaled by other proven paths" -
		// true of its clicks, dock, layering and art (v2.11.30, user-confirmed)
		// but NOT of its SIZE AT BIRTH, which is the jump the user still sees.
		//
		// Byte-verified 2026-07-31 (both twins, at the same 0x25 delta):
		//   SetLayout 0x7EB16E / 0x7E74AE   both `ff 50 10`
		//   Place     0x7EB193 / 0x7E74D3   both `ff 52 14`
		//   accept    0x7EB196 / 0x7E74D6
		// sub_7E7270 has exactly ONE caller (0x7F4D2C, gated on
		// `cmp esi,0x69B9324A`) and ZERO raw-address occurrences image-wide, so
		// the return address is a sound discriminator on its own.
		const uintptr_t modBase =
			reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
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
		// ⚠ THE DISASTER CONTAINER HAS NO ID AT ALL - sub_7E7270 contains no
		// SetID call (scanned 0x7E7270..0x7E75B0). REGRESSION.md:2132's "same
		// class, DIFFERENT id" is wrong and would send you to build the wrong
		// guard. For that twin the return address IS the identification.
		cIGZWin* win = reinterpret_cast<cIGZWin*>(
			reinterpret_cast<char*>(self) + 4);
		if (!isDisaster && win->GetID() != 0x8A6E61E0) { return; }

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
			// ⚠ v2.39.1 - THE HALF-FIX THAT SHIPPED IN v2.39.0, AND WHY.
			// v2.39.0 scaled the container and the strip RECT and marked the
			// container born. That made Classify return AlreadyScaled, so the
			// sweep SKIPPED THE WHOLE SUBTREE - including the strip item
			// metrics it had been scaling all along. Result: an 88x578 strip
			// window full of 44px cells (the tiny thumbnail column, user
			// screenshots). Geometry born correct, STATE not born: exactly the
			// v2.36.2 law, which the v2.39.0 comment quoted and then did not
			// apply. When born-scaling takes a window off the sweep, it
			// inherits EVERYTHING the sweep was doing for it.
			// ⛔ DO NOT WRITE THE ITEM METRICS HERE. v2.39.1 did, and it broke
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
			// DOCK AT BIRTH (v2.39.3). The sweep's dock is the last piece of
			// the open-jump: measured born (63,688) -> dock (6,502). The target
			// is cached by the sweep (it is a pure function of the scaled
			// toolbar and the ini offsets, identical every tick), so applying
			// it here needs no tree walk and no toolbar read inside the game's
			// own call. The sweep then finds the window already at its target
			// and its `cl != targetL` test makes the later move a no-op.
			// Absolute, NOT the sub-flyout's relative delta form - the two
			// flyouts have different dock laws and mixing them displaces this
			// one (GZWinMoveTo takes a DELTA, hence target - current).
			if (gDisDockValid && gDisBornDockOn)
			{
				const int32_t dl = gDisDockL - l;
				const int32_t dt = gDisDockT - t;
				if (dl != 0 || dt != 0) { win->GZWinMoveTo(dl, dt); }
			}
			NoteBorn(win, 0, cw, ch, newW, newH);
			// The strip WINDOW must be registered too, or the sweep finds it
			// Fresh at its already-2x rect and doubles it again.
			void* dstripWin = nullptr;
			if (dstrip)
			{
				typedef void*(__fastcall* GetWinFn)(void*, void*);
				void** dsvt = *reinterpret_cast<void***>(dstrip);
				if (dsvt && dsvt[3])
				{
					dstripWin = reinterpret_cast<GetWinFn>(dsvt[3])(dstrip, nullptr);
				}
				if (dstripWin)
				{
					NoteBorn(dstripWin, 0, osw, osh,
						sr[2] - sr[0], sr[3] - sr[1]);
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
			// ⚠ OFFSET FRAME (v2.39.8 - the read-guard caught v2.39.7's error
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
					// ⛔ THIS LINE USED TO REPORT RoundHalfUp AND IT WAS A LIE.
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
		}

		// --- 4. the dock. The sweep can only dock one tick LATER than it
		// scales, because its placement law needs a ring blit at the new
		// buffer size (ringFresh) - which cannot exist until the window has
		// painted once. That is the SECOND settle the user sees. Here the
		// position is the game's native one BY CONSTRUCTION, so the delta
		// applies with no button search and no ring data. The sweep then
		// recognises its own target (atTarget) and does nothing.
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
			// #95 PHASE 2: use the same validated model here, so BIRTH and the
			// SWEEP agree. They must: the sweep only re-docks a container it
			// finds at the native OR the target position, so if birth used the
			// old constant and the sweep the model, the container would sit at
			// neither and never be docked at all.
			// The button centre is not in scope at birth, so RECOVER it by
			// inverting the game's own 1x expression:
			//     nativeTop = (53>>1) - (ch>>1) + cy - 29
			//  => cy        = nativeTop + (ch>>1) + 3
			// and SELF-CHECK it: recomputing the 1x top from that cy must
			// reproduce nativeTop. If it does not, a 1x clamp fired and the
			// inversion is not valid - fall back to the constant delta and let
			// the sweep (which has the real button) correct it.
			if (gSubMath && ch > 0)
			{
				const int32_t nativeL = win->GetL();
				const int32_t nativeT = win->GetT();
				const int32_t cy = nativeT + (ch >> 1) + 3;
				const int32_t check = (53 >> 1) - (ch >> 1) + cy - 29;
				if (check == nativeT)
				{
					// Y only - X keeps the constant, exactly as the sweep does
					// (see the tgtL comment there). The recovered cy and the
					// sweep's BUTTON CENTRE are provably the SAME number:
					// substituting the game's own ringY = (ch>>1) - 26 into the
					// measured natT law gives natT = bcy - (ch>>1) - 3, which
					// is the game's own nativeT = cy - (ch>>1) - 3. So birth
					// and the sweep feed the model an identical anchor and
					// cannot disagree - which they MUST not, per above.
					dy = SubPlaceTop(newH, cy, gLastViewH, gTierF) - nativeT;
					// ...and hold the ring at the legacy dock, so the FIRST
					// paint is already right and there is no attach-then-jump.
					gSubRingAutoY = legDY - dy;
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
			void** svt = *reinterpret_cast<void***>(strip);
			if (svt && svt[3])
			{
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
			Logger::Get().WriteLine(LogLevel::Debug,
				"UiSpike: SUBBORN2 0x8A6E61E0 born x%.2f: container %dx%d -> "
				"%dx%d at (%d,%d)%+d%+d, strip rel(%d,%d) %dx%d -> (%d,%d) "
				"%dx%d, items x%.2f%s.",
				gTierF, cw, ch, newW, newH, l, t, dx, dy,
				osl, ost, osw, osh, sr[0], sr[1],
				sr[2] - sr[0], sr[3] - sr[1], gTierF,
				stripWin ? "" : " (STRIP WINDOW NOT RESOLVED)");
		}
	}
}

// ============ FIRST-LEVEL FLYOUT: SCALE ON OPEN (v2.36.1, task #50) =====
// MEASURED, from the v2.36.0 session log - which is why this exists at all.
// v2.36.0 born-scaled the NESTED container and fired ZERO times, because the
// menus the user calls "sub flyouts" are the FIRST-LEVEL tool flyouts. The
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
// THE HOOK POINT IS A SINGLE FUNNEL... ⚠ CORRECTED v2.39.6: it is TWO. The
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
	inPass = true;                           // no nested tree walks (see Run)
	ScaleGodFlyouts(lastView, gTierF);
	inPass = false;
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

	const uintptr_t base = reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
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
// Byte-for-byte the same operations the sweep performs (UiSpike.cpp, the
// KNOWN-MENU GATE block) - same crash guard, same vtable checks, same guarded
// claim promotion - just earlier, so the very first sub-flyout of a city does
// not paint 9 frames of 1x bar while it waits.
//
// ⚠ THE TWO HALVES ARE ONE OPERATION. [0xE0] is DUAL-USE: the hit-claim width
// AND a Plot layout inset. SlotThunk<88> presents the latched 1x value to the
// draw group and re-arms the 2x claim after. Promote [0xE0] WITHOUT installing
// that thunk first and the game paints a SECOND orange bar (v2.11.24, user
// confirmed). Order here is: container thunks -> claim -> strip thunks.
//
// ⚠ THE CRASH GUARD IS NOT OPTIONAL (law 3, v2.22.1). These hooks were
// validated only on the known parent menus; when U-Drive-It -> Earned Cars
// (an 88-WIDE strip, a foreign layout) received them the game died. Positive
// identification only.
void UiSpike::InstallSubFlyoutHooksNow(cIGZWin* sub, cIGZWin* strip)
{
	if (!sub || !strip || !lastView || gClaimScale <= 1) { return; }

	bool knownMenuOpen = false;
	const uint32_t kHookParents[] = {
		0x49923239, 0x69923479, 0xC99237A0, 0xE992F711, 0x699306ED,
		0x8BB27C12, 0xAB954023
	};
	for (uint32_t pid : kHookParents)
	{
		cIGZWin* par = lastView->GetChildWindowFromIDRecursive(pid);
		if (par && par->IsVisible()) { knownMenuOpen = true; break; }
	}
	if (!knownMenuOpen) { return; }

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

// ============ EDGE PROBE (v2.36.4, tasks #59 + #60) =====================
// TWO COLD DEFECTS, ONE SESSION. Both first moves are measurements, per
// METHOD.md: identify the window before choosing a cure (ENGINE §4.7), and
// never guess a lever for a window that has never been named.
//
// (A) #59 THE SCREEN-EDGE BORDER. Narrowed offline to eight full-screen
//     windows, two of which are ANONYMOUS (id 0, vt 0x00AB8CD0 / 0x00AB8F50)
//     — the shape of a frame overlay. This logs the full-screen SET whenever
//     it changes, so pausing (or switching mode) names the one that appears.
//
// (B) #60 THE U-DRIVE-IT MAP MARKER. The 4x-art attempt at {46a006b0,
//     094ac89a} shipped in v2.25.17 and did nothing — that TGI is not the
//     marker. Offline this session also killed the second lead: the
//     "15-entry glyph table" at 0x44DEC1 is a RESOURCE REGISTRATION table
//     whose every consumer (0x9970A0, 0x9C85B3, ...) sits in the UI-window
//     code region — spinner/slider art, not a world billboard. So the open
//     question is binary and this answers it: **is the marker a cIGZWin at
//     all?** If bubble 0x48E945B4 is absent or vis=0 while markers are on
//     screen, it is a 3D/world billboard and no window or art lever can
//     reach it — which redirects the whole task.
//
// Live-tunable: [Probe] EdgeDump=1. Costs nothing when off.
// ============ VISIBILITY TRACE (v2.36.8, task #59) ======================
// THE INSTRUMENT THE BORDER ACTUALLY NEEDS, after two of mine failed for the
// same reason: EdgeProbeTick walked one root, then two levels. The two
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
	int gVisSeenN = 0;
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

void UiSpike::EdgeProbeTick(cIGZWin* pView)
{
	if (gEdgeDump <= 0 || !pView) { return; }
	const int32_t sw = pView->GetW(), sh = pView->GetH();
	if (sw <= 0 || sh <= 0) { return; }

	static uint32_t lastSig = 0;
	static int edgeLogged = 0;
	uint32_t sig = 0;
	struct Hit { uint32_t id; void* vt; int32_t l, t, w, h; int vis; char root; };
	Hit hits[24] = {};
	int n = 0;
	int smallWins = 0;   // 16..96px square candidates anywhere under the view

	// ⚠ v2.36.5 CORRECTION TO THIS PROBE'S FIRST VERSION. It walked the VIEW
	// only and found 2 windows; the eight-window list that motivated it came
	// from the view dump AND the MAIN-WINDOW dump, and the two anonymous
	// prime suspects (vt 0x00AB8CD0 / 0x00AB8F50) are not under the view. The
	// instrument was structurally blind to exactly what it was built to find
	// - the FLASHSET mistake, repeated. Walk BOTH roots.
	cISC4AppPtr pSC4App;
	cIGZWin* pMainWindow = pSC4App ? pSC4App->GetMainWindow() : nullptr;
	cIGZWin* roots[2] = { pView, pMainWindow };
	for (int r = 0; r < 2; r++)
	{
		if (!roots[r]) { continue; }
		ChildSnapshot lvl1 = {};
		roots[r]->EnumChildren(GZIID_cIGZWin, ChildSnapshot::Callback, &lvl1);
		for (int i = 0; i < lvl1.count && n < 24; i++)
		{
			cIGZWin* a = lvl1.wins[i];
			if (!a) { continue; }
			cIGZWin* level[1 + 64] = {};
			int levelN = 0;
			level[levelN++] = a;
			ChildSnapshot lvl2 = {};
			a->EnumChildren(GZIID_cIGZWin, ChildSnapshot::Callback, &lvl2);
			for (int j = 0; j < lvl2.count && levelN < 65; j++)
			{
				if (lvl2.wins[j]) { level[levelN++] = lvl2.wins[j]; }
			}
			for (int k = 0; k < levelN && n < 24; k++)
			{
				cIGZWin* w = level[k];
				const int32_t ww = w->GetW(), wh = w->GetH();
				// marker-sized census (B): a world billboard has NO window,
				// so "markers on screen but zero small windows" is the proof.
				if (r == 0 && ww >= 16 && ww <= 96 && wh >= 16 && wh <= 96
					&& w->IsVisible())
				{
					smallWins++;
				}
				if (ww < sw * 9 / 10 || wh < sh * 9 / 10) { continue; }
				const int vis = w->IsVisible() ? 1 : 0;
				hits[n].id = w->GetID();
				hits[n].vt = *reinterpret_cast<void**>(w);
				hits[n].l = w->GetL(); hits[n].t = w->GetT();
				hits[n].w = ww; hits[n].h = wh;
				hits[n].vis = vis;
				hits[n].root = (r == 0) ? 'V' : 'M';
				sig = sig * 31u + hits[n].id + static_cast<uint32_t>(vis) * 7u
					+ static_cast<uint32_t>(r) * 3u;
				n++;
			}
		}
	}
	sig = sig * 31u + static_cast<uint32_t>(smallWins);

	// (B) is the U-Drive-It bubble a window at all right now?
	cIGZWin* bub = pView->GetChildWindowFromIDRecursive(0x48E945B4);
	const uint32_t bubSig = bub
		? (0xB0000000u + static_cast<uint32_t>(bub->GetW()) * 3u
			+ (bub->IsVisible() ? 1u : 0u))
		: 0xB0FFFFFFu;
	sig = sig * 31u + bubSig;

	if (sig == lastSig || edgeLogged >= 40) { return; }
	lastSig = sig;
	edgeLogged++;
	for (int i = 0; i < n; i++)
	{
		Logger::Get().WriteLine(LogLevel::Debug,
			"UiSpike: EDGE [%c] full-screen win #%d id=0x%08X vt=%p "
			"(%d,%d %dx%d) vis=%d  [screen %dx%d]",
			hits[i].root, i, hits[i].id, hits[i].vt, hits[i].l, hits[i].t,
			hits[i].w, hits[i].h, hits[i].vis, sw, sh);
	}
	Logger::Get().WriteLine(LogLevel::Debug,
		"UiSpike: EDGE bubble 0x48E945B4 %s | marker-sized visible windows "
		"under the view: %d | roots walked: view=%s main=%s (change #%d of 40)",
		bub ? "PRESENT" : "ABSENT", smallWins,
		pView ? "yes" : "no", pMainWindow ? "yes" : "NO - could not reach it",
		edgeLogged);
	if (bub)
	{
		Logger::Get().WriteLine(LogLevel::Debug,
			"UiSpike: EDGE   bubble rect (%d,%d %dx%d) vis=%d vt=%p",
			bub->GetL(), bub->GetT(), bub->GetW(), bub->GetH(),
			bub->IsVisible() ? 1 : 0, *reinterpret_cast<void**>(bub));
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
	if (settings.spikeSubFlyoutBorn2x > 0)
	{
		// The two mechanisms both make the window born 2x - together they
		// would double it twice. The constants path is the one that broke the
		// UI twice; refuse rather than stack them.
		Logger::Get().WriteLine(LogLevel::Info,
			"UiSpike: SUBBORN2 NOT installed - SubFlyoutBorn2x (the DEAD "
			"constants path) is enabled. Turn that off to use born-scale.");
		return;
	}

	const uintptr_t base = reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
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

// ===================== SHOWHOOK (v2.32.0, task #50) =====================
// THE SYSTEMIC 1x FLASH. Measured, not assumed (FLASHSET, v2.31.0): twelve
// panels were scaled while genuinely ON SCREEN - the city HUD at +297ms after
// the city arm, and two more at +82s/+97s during play. On-screen at scale time
// means the game already painted them at 1x; that painted frame IS the flash.
//
// Why the sweep cannot win this race: the arm fires at PostCityInit and the
// NEXT timer tick does not arrive for ~290ms, because the game's message loop
// is busy finishing the load. No cadence change reaches that.
//
// Why THIS hook is the cure (offline emulation, tools\uimap\emu\SHOW-PATH.md):
//   * the visibility SETTER is vt+0x110 SetFlag(flag,value), base impl
//     0x0099DB6B - and project lore's "vt+0x10C" is GetFlag, a READER.
//   * every window is BORN visible ([this+0xC8] = 0x8903 in both ctors), so a
//     freshly built tree yields no transition - but its ANCESTOR (the view
//     root the loading screen hides) does flip, and that one call is what puts
//     the whole HUD on screen.
//   * SetFlag does NOT paint in its own call stack (it only invalidates), so
//     scaling here is provably pre-paint. Nothing is suppressed - the
//     FlashGuard lesson stands.
//   * we scale BEFORE calling the original: for PrivateBuffer windows the
//     visible path sizes back-buffers from the CURRENT rect, so scaling after
//     would leave a 1x buffer behind a 2x rect.
//   * 0x0099DB6B is ONE shared implementation across every window class
//     sampled; the two overrides both call it. So this is a single trampoline,
//     not a vtable campaign.
//
// [Spike] ShowHook: 0 = off, 1 = LOG ONLY (default - proves the transitions
// land where predicted), 2 = log + scale. The ini is re-read live, so 1 -> 2
// needs no rebuild, and 2 -> 0 is an instant escape hatch if it misbehaves.
namespace
{
	typedef bool(__fastcall* SetFlagFn)(void*, void*, uint32_t, bool);
	SetFlagFn gOrigSetFlag = nullptr;
	UiSpike*  gSpikeForHook = nullptr;
	int       gShowHookMode = 0;
	bool      gInShowHook = false;
	int       gShowHookLogged = 0;
	// BUDGETSHOW census (2026-08-18). NOT a treatment - it changes no
	// geometry and runs at any ShowHook setting. It exists because the
	// budget path is SILENT BY DESIGN: the four composed roots are scaled
	// once by the city sweep (kDataScaledSubtreeIds) and never revisited,
	// and the sweep does not descend into them, so after city open the log
	// says nothing at all about them. A 2026-08-18 session with LogLevel=3
	// produced ZERO 'incremental panel' lines for any budget root across a
	// whole session of play - which is consistent BOTH with 'born correct'
	// and with 'nobody is looking', and cannot tell them apart. That is the
	// gap this closes, and it is the one the user's question needs:
	// does the FIRST open after a city load differ from later opens?
	int       gBudgetShowLog = 0;
	// BUDGETWATCH state (2026-08-18). BUDGETSHOW proved the roots are BORN
	// CORRECT - 0xAA3AC000 1250x206 and 0xAA3AC001 837x758, both exactly
	// RoundHalfUp(design * 1.5), at the hidden->visible transition, and the
	// VWKID line 60ms later shows the same rect at the same origin. So the
	// user's resize is NOT us arriving late, and it is not the sweep: the
	// whole session logged ZERO 'incremental panel' lines. Something moves
	// or resizes these windows AFTER they are shown, and nothing in the mod
	// currently looks. This watches for exactly that and takes no action.
	struct BudgetWatch { uint32_t id; int32_t w, h, l, t; bool seen; };
	BudgetWatch gBudgetWatch[4] = {
		{ 0xAA3AC000, 0, 0, 0, 0, false },
		{ 0xAA3AC001, 0, 0, 0, 0, false },
		{ 0xAA3AC002, 0, 0, 0, 0, false },
		{ 0xCA4C332D, 0, 0, 0, 0, false },
	};
	int       gBudgetWatchLog = 0;
	// BUDGETKIDS (2026-08-18). Pre-registered as the next step BEFORE the
	// 19:04 capture, and the capture is what selects it: BUDGETSHOW proved
	// both roots are born at RoundHalfUp(design*f), and BUDGETWATCH then
	// logged FOUR changes - all at city open, all vis=0, all our own sweep -
	// and NOTHING at either department open, with 36 of its 40 lines still
	// unspent. That is a TRUE null with a working positive control: the
	// instrument fires, on these ids, and the roots simply do not move or
	// resize after they are shown. So the thing the user watches resize is
	// not the root. One level down is the only place left.
	uint32_t  gBudgetKidsDigest[4] = { 0, 0, 0, 0 };
	int       gBudgetKidsCount[4] = { -1, -1, -1, -1 };
	int       gBudgetKidsLog = 0;
	// BUDGETTICK (2026-08-18). BUDGETWATCH samples from the sweep, ~16 ms,
	// so it can only see a change that OUTLIVES a tick. The reported symptom
	// is 'a split second' - a few frames - which is exactly the duration that
	// can open wrong and be corrected between two samples, leaving a null
	// that means 'too slow to see it', not 'it did not happen'. Treating that
	// null as proof would be the same error as a probe scoped to the wrong
	// channel, so it is named in the ledger and closed here instead.
	//
	// This samples from inside the cGZWin::SetFlag detour, which fires for
	// EVERY flag change on EVERY window - orders of magnitude more often than
	// the sweep, and during the exact layout/invalidate traffic a resize
	// generates. It uses ONLY the pointer the game just handed us and caches
	// NO window pointers, so it cannot outlive an object (the #117 lesson).
	// No new hook, no vtable work - the file header warns off the SetArea
	// overload pair, and this needs neither.
	struct BudgetTick { uint32_t id; int32_t w, h, l, t; bool seen; };
	BudgetTick gBudgetTick[5] = {
		// THE ONE THAT ACTUALLY OPENS. Shared exe-built department transient,
		// rebuilt per department, no .UI script, main-window child. This is
		// the window the user watches resize; the four below are the panel
		// furniture that was already on screen when they clicked.
		{ 0x0423278F, 0, 0, 0, 0, false },
		{ 0xAA3AC000, 0, 0, 0, 0, false },
		{ 0xAA3AC001, 0, 0, 0, 0, false },
		{ 0xAA3AC002, 0, 0, 0, 0, false },
		{ 0xCA4C332D, 0, 0, 0, 0, false },
	};
	int       gBudgetTickLog = 0;
	int       gMayorRebirthLogs = 0;   // #194
	int       gArtSizedRefusals = 0;     // #197
	int32_t   gReadoutW = 0, gReadoutH = 0;   // #192, set by the director
	bool      gReqResIgnored = false;   // wrapper overrides the resolution
	int       gReadoutLogs = 0;
	bool      gBudgetTickAnnounced = false;
	int       gBudgetShowOpens = 0;
	bool      gShowHookInstalled = false;

	// EARLYDOCK (v2.41.17, task #89). State for scaling the dock from inside
	// this detour once its subtree has settled. All per-city; all cleared in
	// Disarm (second-city law) AND re-armed in ArmDeferred.
	int   gEarlyDockMode = 0;
	bool  gEarlyDockPending = false;  // armed this city, not yet acted
	bool  gInEarlyDock = false;       // re-entrancy: our own SetW/SetH will
	                                  // themselves trip SetFlag
	unsigned int gEarlyDockCalls = 0; // throttle: the lookup is far too costly
	                                  // to run on EVERY SetFlag in the game
	int   gEarlyDockLastCount = -1;   // child count seen at the last check
	int   gEarlyDockStable = 0;       // consecutive checks with no change
	// v2.41.18: was 128, and EARLYDOCK NEVER FIRED. The window between arm and
	// the sweep is only ~759ms (measured), and SetFlag barely fires during the
	// load tail - the game is busy with non-UI work, which is the same fact
	// that killed the message-queue lever. 128 was tuned for a hook that fires
	// constantly during PLAY, not during LOAD. 8 gives ~16x more checks in the
	// same window; `pending` is cleared after one shot (or once the dock is
	// already 2x), so the cost is bounded to that window.
	const unsigned int kEarlyDockEvery = 8;     // check cadence, in SetFlag calls
	const int kEarlyDockStableNeeded = 2;       // matches RegionWatchTick's test
	int   gEarlyDockChecks = 0;      // how many times the tick actually ran
	int   gEarlyDockLogged = 0;      // cap on the diagnostic lines

	bool __fastcall SetFlagDetour(void* self, void* edx, uint32_t flag, bool value)
	{
		// EARLYDOCK. Deliberately FIRST and deliberately cheap: an increment
		// and a mask on the overwhelming majority of calls. We only pay for a
		// tree lookup once every kEarlyDockEvery calls, and only until the
		// dock has been dealt with once this city.
		if (gEarlyDockPending && !gInEarlyDock && gSpikeForHook)
		{
			if (((++gEarlyDockCalls) & (kEarlyDockEvery - 1)) == 0)
			{
				gInEarlyDock = true;      // our own SetW/SetH re-enter SetFlag
				gSpikeForHook->EarlyDockTick();
				gInEarlyDock = false;
			}
		}

		// #137d: PANEL DOCK AT SHOW - ITS OWN GATE, NOT ShowHook's.
		// This trampoline now serves THREE consumers, and the third was keyed
		// off the wrong flag. #127 put "dock at show" inside ScaleOnShow, which
		// only runs when gShowHookMode >= 2; the shipped ini has ShowHook=0 and
		// the log says so plainly - "SHOWHOOK installed ... (mode 0: log only)".
		// So the born-correct dock has NEVER EXECUTED, and every version since
		// #127 relied on the tick to correct the panel after its first paint.
		// That is the one-frame jump, and it is law 47 (installed != executed)
		// in the same function that already records this exact mistake for
		// EARLYDOCK at v2.41.17. ShowHook stays 0 - scale-at-show is refuted
		// for the city HUD and this must not depend on reviving it.
		if (flag == 1u && value && self && !gInShowHook && !gInEarlyDock
			&& gSpikeForHook && gTierF > 1.01f)
		{
			// Same transition test as below: [this+0xC8] & 1 is what
			// IsVisible() reads, and it is still 0 here - which is exactly why
			// ApplyPanelDocks must be told to gate on geometry (fromShow).
			const uint32_t bits0 =
				*reinterpret_cast<const uint32_t*>(
					reinterpret_cast<const char*>(self) + 0xC8);
			if ((bits0 & 1u) == 0u)
			{
				cIGZWin* w0 = static_cast<cIGZWin*>(self);
				if (IsPanelDockMember(w0->GetID()))
				{
					gInShowHook = true;
					cIGZWin* scope = w0;
					for (int up = 0; up < 6 && scope; up++)
					{
						cIGZWin* parent = scope->GetParentWin();
						if (!parent || parent == scope) { break; }
						scope = parent;
					}
					gSpikeForHook->ApplyPanelDocks(
						scope ? scope : w0, gTierF, true);
					gInShowHook = false;
				}
			}
		}

		// BUDGETTICK. EVERY flag change on one of the four roots, not just the
		// visibility transition - so a resize that lands and is corrected
		// within a single sweep tick still gets recorded. Costs one compare on
		// every other window in the game.
		if (self && gTierF > 1.01f && gBudgetTickLog < 120)
		{
			// ARMED-AND-COVERING line. A probe that prints nothing is
			// ambiguous between "nothing happened" and "not watching the
			// right thing" - which is exactly how today went. This makes the
			// covered set appear in the log whether or not anything fires.
			if (!gBudgetTickAnnounced)
			{
				gBudgetTickAnnounced = true;
				Logger::Get().WriteLine(LogLevel::Info,
					"UiSpike: BUDGETTICK armed, watching 0x0423278F (department "
					"transient - the window a department click BUILDS), plus "
					"0xAA3AC000/01/02 and 0xCA4C332D. Silence on 0x0423278F now "
					"means no flag-adjacent geometry change, not an unwatched "
					"window.");
			}
			cIGZWin* wt = static_cast<cIGZWin*>(self);
			const uint32_t tid = wt->GetID();
			for (BudgetTick& bt : gBudgetTick)
			{
				if (bt.id != tid) { continue; }
				const int32_t cw = wt->GetW(), ch = wt->GetH();
				const int32_t cl = wt->GetL(), ct = wt->GetT();
				if (bt.seen && (cw != bt.w || ch != bt.h
						|| cl != bt.l || ct != bt.t))
				{
					gBudgetTickLog++;
					Logger::Get().WriteLine(LogLevel::Info,
						"UiSpike: BUDGETTICK 0x%08X (%d,%d %dx%d) -> "
						"(%d,%d %dx%d)  [%s]  vis=%d flag=%u val=%d - seen "
						"INSIDE SetFlag, i.e. between sweep samples.",
						tid, bt.l, bt.t, bt.w, bt.h, cl, ct, cw, ch,
						(cw == bt.w && ch == bt.h) ? "MOVED only"
							: (cl == bt.l && ct == bt.t) ? "RESIZED only"
								: "moved AND resized",
						wt->IsVisible() ? 1 : 0, flag, value ? 1 : 0);
				}
				bt.w = cw; bt.h = ch; bt.l = cl; bt.t = ct; bt.seen = true;
				break;
			}
		}

		// BUDGETSHOW. Four ids, tested only on a real hidden->visible
		// transition, capped - the cost on every other window is one compare.
		// The line is SELF-ADJUDICATING: it prints the live size next to
		// RoundHalfUp(design * f), which is the same convention the sweep and
		// every builder use (law 89). Born correct reads live == expect on
		// open #1; a jump reads the design size on open #1 and the expected
		// size on opens #2+ - the uninitialised-latch signature, and exactly
		// what the flyout family turned out to be at v2.36.2.
		if (flag == 1u && value && self && !gInShowHook && !gInEarlyDock
			&& gTierF > 1.01f && gBudgetShowLog < 24)
		{
			const uint32_t bitsB =
				*reinterpret_cast<const uint32_t*>(
					reinterpret_cast<const char*>(self) + 0xC8);
			if ((bitsB & 1u) == 0u)
			{
				// Design sizes are the MEASURED ones already carried by
				// kDataScaledSubtreeIds / kCityDialogIds, not fresh guesses:
				// 0xAA3AC000 833x137, 0xAA3AC001 558x505, 0xAA3AC002 500x464
				// (the LIVE copy is I-cbc3c2b9 - #102 settled that against 14
				// captures), 0xCA4C332D 500x353.
				struct BudgetRoot { uint32_t id; int32_t w, h; const char* name; };
				static const BudgetRoot kBudgetRoots[] = {
					{ 0xAA3AC000, 833, 137, "balance bar"          },
					{ 0xAA3AC001, 558, 505, "department frame"     },
					{ 0xAA3AC002, 500, 464, "taxes editor popup"   },
					{ 0xCA4C332D, 500, 353, "take-out-a-loan popup" },
				};
				cIGZWin* wb = static_cast<cIGZWin*>(self);
				const uint32_t bid = wb->GetID();
				for (const BudgetRoot& br : kBudgetRoots)
				{
					if (br.id != bid) { continue; }
					gBudgetShowLog++;
					gBudgetShowOpens++;
					const int32_t ew = RoundHalfUp(br.w * gTierF);
					const int32_t eh = RoundHalfUp(br.h * gTierF);
					const int32_t lw = wb->GetW(), lh = wb->GetH();
					Logger::Get().WriteLine(LogLevel::Info,
						"UiSpike: BUDGETSHOW #%d 0x%08X (%s) becoming visible "
						"%dx%d, expect %dx%d, design %dx%d, %d children -> %s.",
						gBudgetShowOpens, bid, br.name, lw, lh, ew, eh,
						br.w, br.h, wb->GetChildCount(),
						(lw == ew && lh == eh) ? "BORN CORRECT"
							: (lw == br.w && lh == br.h)
								? "STILL 1x - WILL JUMP when the sweep catches it"
								: "NEITHER design nor expected - read the numbers");
					break;
				}
			}
		}

		// Cheapest possible rejection first: this fires for EVERY flag change
		// on EVERY window in the game.
		if (gShowHookMode > 0 && flag == 1u && value && self && !gInShowHook)
		{
			// Transition test, not a redundant set: the live bit is
			// [this+0xC8] & 1, which is exactly what IsVisible() reads.
			const uint32_t bits =
				*reinterpret_cast<const uint32_t*>(
					reinterpret_cast<const char*>(self) + 0xC8);
			if ((bits & 1u) == 0u)
			{
				cIGZWin* w = static_cast<cIGZWin*>(self);
				gInShowHook = true;   // no re-entry from anything below
				if (gShowHookLogged < 60)
				{
					gShowHookLogged++;
					Logger::Get().WriteLine(
						LogLevel::Debug,
						"UiSpike: SHOWHOOK 0x%08X becoming visible (%dx%d, %d "
						"children) - %s.",
						w->GetID(), w->GetW(), w->GetH(), w->GetChildCount(),
						gShowHookMode >= 2 ? "scaling now" : "log only");
				}
				if (gShowHookMode >= 2 && gSpikeForHook)
				{
					gSpikeForHook->ScaleOnShow(w);
				}
				gInShowHook = false;
			}
		}
		return gOrigSetFlag(self, edx, flag, value);
	}
}

void UiSpike::InstallShowHook()
{
	gSpikeForHook = this;
	gShowHookMode = settings.spikeShowHook;
	gEarlyDockMode = settings.spikeEarlyDock;
	// v2.41.17: the trampoline now serves TWO consumers, so it must install if
	// EITHER wants it. ShowHook itself ships at 0 (refuted for the city HUD),
	// and EARLYDOCK would silently never run if this still keyed off it alone.
	if (gShowHookInstalled || (gShowHookMode <= 0 && gEarlyDockMode <= 0)) { return; }
	if (gTierF <= 1.01f) { return; }   // stock tier stays inert

	const uintptr_t base = reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
	void* target = reinterpret_cast<void*>(base - 0x400000 + 0x0099DB6B);

	const MH_STATUS init = MH_Initialize();
	if (init != MH_OK && init != MH_ERROR_ALREADY_INITIALIZED)
	{
		Logger::Get().WriteLine(LogLevel::Error,
			"UiSpike: SHOWHOOK MH_Initialize failed (%d) - not installed.", init);
		return;
	}
	if (MH_CreateHook(target, reinterpret_cast<void*>(&SetFlagDetour),
			reinterpret_cast<void**>(&gOrigSetFlag)) != MH_OK
		|| MH_EnableHook(target) != MH_OK)
	{
		Logger::Get().WriteLine(LogLevel::Error,
			"UiSpike: SHOWHOOK failed to hook cGZWin::SetFlag at %p.", target);
		return;
	}
	gShowHookInstalled = true;
	Logger::Get().WriteLine(LogLevel::Info,
		"UiSpike: SHOWHOOK installed on cGZWin::SetFlag %p (mode %d: %s).",
		target, gShowHookMode,
		gShowHookMode >= 2 ? "log + SCALE at show" : "log only");
}

void UiSpike::ScaleOnShow(cIGZWin* win)
{
	if (!win || gTierF <= 1.01f) { return; }
	// Same policy as the sweep - this changes WHEN we scale, never WHAT.
	const uint32_t id = win->GetID();
	if (IsNeverScaleId(id)) { return; }
	const int32_t w = win->GetW(), h = win->GetH();
	if (w <= 0 || h <= 0) { return; }

	int n = 0;
	ScaleSubtree(win, gTierF, 0, &n, false);
	if (n > 0)
	{
		Logger::Get().WriteLine(LogLevel::Debug,
			"UiSpike: SHOWHOOK pre-scaled 0x%08X (%dx%d) - %d window(s) BEFORE "
			"first paint.", id, w, h, n);
	}

	// #127 (v2.77.0): DOCK AT SHOW, so a docked panel is BORN seated instead of
	// jumping on its first open. v2.76.0 only ran kPanelDock from the sweeps, so
	// the Graphs band painted once at the anchor's own (wrong) seat and snapped
	// a tick later - the user saw exactly that ("it jumps when you open the city
	// for the first time"), and it is the same first-paint family as #50/#76:
	// a window must be BORN correct, not corrected afterwards.
	// The dock needs BOTH windows, and `win` here may be either one (or an
	// ancestor of them), so walk up to a root that can see the whole pair.
	if (IsPanelDockMember(id))
	{
		cIGZWin* scope = win;
		for (int up = 0; up < 6 && scope; up++)
		{
			cIGZWin* parent = scope->GetParentWin();
			if (!parent || parent == scope) { break; }
			scope = parent;
		}
		// #137c: fromShow=true - the visible bit is not set yet on this
		// window, so gate on geometry instead of the flag or the dock
		// can never be born-correct (see ApplyPanelDocks).
		ApplyPanelDocks(scope ? scope : win, gTierF, true);
	}
}

UiSpike::UiSpike(const Settings& settings)
	: settings(settings)
{
}

void UiSpike::ArmDeferred(unsigned int fireAtTickMs)
{
	if (!settings.spikeDumpTree && settings.spikeScaleWindowId == 0 && !settings.spikeScaleAll)
	{
		return;
	}
	armed = true;
	fireAtMs = fireAtTickMs;
	// v2.32.0: install the show hook here, not in the ctor - by PostCityInit
	// the tier is decided and gTierF is live, so a stock tier stays inert.
	InstallShowHook();
	InstallSubFlyoutBorn();
	InstallSubFlyoutBornScale();
	InstallFlyoutOpenHook();
	rciRecheckCountdown = 30; // re-log the RCI columns ~30s into the city
	Logger::Get().WriteLine(LogLevel::Info, "UiSpike: armed (deferred fire).");

	// EARLYDOCK arm (v2.41.17). Re-armed EVERY city; the detour does the work
	// once the dock's subtree settles.
	gEarlyDockMode = settings.spikeEarlyDock;
	gEarlyDockPending = (gEarlyDockMode > 0);
	gEarlyDockCalls = 0;
	gEarlyDockLastCount = -1;
	gEarlyDockStable = 0;
	gEarlyDockChecks = 0;
	gEarlyDockLogged = 0;
	gInEarlyDock = false;

	if (settings.spikeEarlyBake > 0) { EarlyMinimapBake(); }
}

namespace
{
	// Own function: __try is illegal where objects need unwinding, and the
	// caller holds a cISC4AppPtr.
	bool SafeSetBakeFlags(void* pMM)
	{
		__try
		{
			uint8_t* raw = reinterpret_cast<uint8_t*>(pMM);
			raw[0xFD] = 1;   // re-bake gate  (consumed at 0x7A8718 -> 0x7A7FF0)
			raw[0xFE] = 1;   // whole-body gate (checked at 0x7A867D)
			return true;
		}
		__except (EXCEPTION_EXECUTE_HANDLER)
		{
			return false;
		}
	}
}

// EARLY MINIMAP BAKE (v2.41.10, task #89).
//
// THE MEASUREMENT THIS IS BUILT ON. At our first sweep (+1.9s) the minimap's
// raster was uniform grey and BOTH dirty bytes were ZERO - i.e. the game had
// not baked the city map and had no re-bake pending - while the display
// surface was still showing pre-bake content. That content is what the user
// calls "the corrupted map". Stock never shows it because a stock load is
// short enough that the bake lands before the HUD is revealed; our ~11.7MB of
// extra dats stretch the load past that point.
//
// The bake is reached only from 0x7A8640, which is a handler on the GAME'S OWN
// message server ([0xB43CCC], ids 0x99EF1142/0x99EF1143) - NOT the Windows
// queue, so it is not subject to the load-tail starvation that killed the
// WM_APP experiment. It tests [+0xFE] then [+0xFD]. Setting those two bytes
// here means the next internal message bakes the city map, during load.
//
// ⚠ THIS IS THE ONE THING WE RUN INSIDE PostCityInit, and that is the region
// carrying the measured hang. It is kept as small as it can possibly be: two
// non-recursive hops, one first-match recursive lookup, two BYTE WRITES and
// one InvalidateSelf. No tree walk, no geometry, no surface allocation - none
// of what ScaleAll does, which is what earned the ban. [Spike] EarlyBake=0
// makes it completely inert without a rebuild.
// EARLYDOCK (v2.41.17, task #89). Runs from inside the cGZWin::SetFlag
// detour - i.e. ON THE GAME'S OWN STACK, and crucially it keeps being called
// AFTER city init has returned, which is the difference from v2.41.15.
//
// THE THREE LEVERS AND WHY THIS IS THE ONE LEFT:
//   message queue   - dead: the game does not pump during the load tail
//                     (posted WM_APP beat WM_TIMER by 15ms).
//   inside PostCityInit - CRASHED (v2.41.15) when it mutated ~25 windows of
//                     geometry, though two byte writes there are fine. The
//                     likely shape: the game's init continues after us and
//                     re-lays against geometry it did not expect.
//   HERE            - the game's stack, but AFTER init, and we WAIT for the
//                     subtree to stop changing instead of racing it.
//
// The gate is the stability test RegionWatchTick already uses: act only once
// the dock's child count is unchanged across kEarlyDockStableNeeded checks, so
// we never touch a half-built subtree.
//
// Ships at mode 1 (LOG ONLY) on purpose - law 38. Mode 1 reports exactly what
// mode 2 would do, so one city open says whether the timing is right before
// any window moves.
void UiSpike::EarlyDockTick()
{
	if (!gEarlyDockPending || gEarlyDockMode <= 0) { return; }
	if (inPass) { return; }   // never race the sweep

	cISC4AppPtr pSC4App;
	cIGZWin* pMain = pSC4App ? pSC4App->GetMainWindow() : nullptr;
	if (!pMain) { return; }
	cIGZWin* pApp = pMain->GetChildWindowFromID(kGZWin_WinSC4App);
	cIGZWin* pView = pApp
		? pApp->GetChildWindowFromID(kGZWin_SC4View3DWin) : nullptr;
	if (!pView) { return; }
	cIGZWin* pDock = pView->GetChildWindowFromIDRecursive(0x0987B48F);

	// DIAGNOSTIC (v2.41.18). EARLYDOCK produced NO output at all on its first
	// run, and silence has two completely different causes: the tick never ran
	// (SetFlag too rare during load), or it ran and never qualified. Those need
	// opposite fixes, so the instrument must tell them apart - a null is not
	// evidence until it can be distinguished from blindness.
	++gEarlyDockChecks;
	if (gEarlyDockLogged < 6)
	{
		++gEarlyDockLogged;
		Logger::Get().WriteLine(LogLevel::Debug,
			"UiSpike: EARLYDOCK check #%d at +%ums (%u SetFlag calls) - dock %s"
			"%s, children=%d, stableRun=%d",
			gEarlyDockChecks, GetTickCount() - fireAtMs, gEarlyDockCalls,
			pDock ? "FOUND " : "NOT FOUND",
			pDock ? "" : " (view built, dock not yet)",
			pDock ? pDock->GetChildCount() : -1, gEarlyDockStable);
	}
	if (!pDock) { return; }

	// Already 2x? Then the sweep beat us to it this city; stand down quietly.
	const int32_t w = pDock->GetW();
	if (w > 300)
	{
		gEarlyDockPending = false;
		return;
	}

	// v2.41.19 GATE. The design child count IS the "fully built" signal: the
	// dock's .UI declares exactly 20 children (CITY-DOCK-OVERLAP.md 1.4, rows
	// 1-20; measured live: children=20 at the FIRST check, +328ms). The old
	// two-consecutive-checks stability test was a PROXY for this, and it cost
	// 625ms - SetFlag fires so rarely during load that the second check did
	// not arrive until the reveal ("would scale +953ms" vs FLASHSET +968ms).
	// Fire on the direct signal; keep stability as the fallback for a modded
	// dock whose child count differs.
	const int32_t kids = pDock->GetChildCount();
	const int kDockDesignChildren = 20;
	if (kids < kDockDesignChildren)
	{
		if (kids != gEarlyDockLastCount)
		{
			gEarlyDockLastCount = kids;
			gEarlyDockStable = 0;
			return;                 // still being built - do NOT touch it
		}
		if (++gEarlyDockStable < kEarlyDockStableNeeded) { return; }
	}

	gEarlyDockPending = false;      // one shot per city, whatever happens next
	Logger& lg = Logger::Get();
	const unsigned int sinceArm = GetTickCount() - fireAtMs;

	if (gEarlyDockMode < 2)
	{
		lg.WriteLine(LogLevel::Info,
			"UiSpike: EARLYDOCK would scale dock 0x0987B48F now - %dx%d, %d "
			"children, stable for %d checks, +%ums after arm, after %u SetFlag "
			"calls. LOG ONLY (EarlyDock=1). Compare that against the FLASHSET "
			"time below: earlier means this lever wins.",
			w, pDock->GetH(), kids, gEarlyDockStable, sinceArm, gEarlyDockCalls);
		return;
	}

	const float f = settings.spikeScaleFactor;
	inPass = true;   // no timer walk on a nested pump while we mutate
	const int n = ScalePanelRoot(pDock, pView->GetW(), pView->GetH(), f);
	// ⚠ THE HALF THAT WAS MISSING WHEN v2.41.15 CRASHED. Scaling the dock
	// self-updates the minimap's blitSize to 128 while its one-shot display
	// surface stays 64; the next bake is then a 128 render into a 64 surface -
	// the v2.21.0 heap overrun. Scale and recreate are ONE action. This is
	// the sweep's own extracted function, gates and carry-over included.
	TryRecreateMinimapSurface(pDock);
	inPass = false;
	lg.WriteLine(LogLevel::Info,
		"UiSpike: EARLYDOCK scaled dock 0x0987B48F x%.2f - %d window(s), "
		"%d -> %d wide, +%ums after arm, surface recreated in the SAME action. "
		"The sweep will find it AlreadyScaled and skip it.",
		f, n, w, pDock->GetW(), sinceArm);
}

void UiSpike::EarlyMinimapBake()
{
	Logger& lg = Logger::Get();

	cISC4AppPtr pSC4App;
	cIGZWin* pMain = pSC4App ? pSC4App->GetMainWindow() : nullptr;
	if (!pMain)
	{
		lg.WriteLine(LogLevel::Info, "UiSpike: EARLYBAKE no main window.");
		return;
	}
	cIGZWin* pApp = pMain->GetChildWindowFromID(kGZWin_WinSC4App);
	cIGZWin* pView = pApp
		? pApp->GetChildWindowFromID(kGZWin_SC4View3DWin) : nullptr;
	if (!pView)
	{
		lg.WriteLine(LogLevel::Info,
			"UiSpike: EARLYBAKE city view not built yet - nothing to ask.");
		return;
	}
	cIGZWin* pDock = pView->GetChildWindowFromIDRecursive(0x0987B48F);
	cIGZWin* pMM = pDock
		? pDock->GetChildWindowFromIDRecursive(0x0BC3B559) : nullptr;
	if (!pMM)
	{
		lg.WriteLine(LogLevel::Info,
			"UiSpike: EARLYBAKE dock=%p minimap NOT FOUND at PostCityInit "
			"(too early - the bake cannot be requested here).",
			static_cast<void*>(pDock));
		return;
	}

	const bool ok = SafeSetBakeFlags(pMM);
	if (ok) { pMM->InvalidateSelf(); }
	lg.WriteLine(LogLevel::Info,
		"UiSpike: EARLYBAKE minimap %p %dx%d - dirty bytes %s at PostCityInit; "
		"the city map should bake on the next internal message, before reveal.",
		static_cast<void*>(pMM), pMM->GetW(), pMM->GetH(),
		ok ? "SET + invalidated" : "FAULTED (unchanged)");

	// ===== MODE 2: SCALE THE DOCK HERE, SO IT IS NEVER SEEN AT 1x =========
	// User's question, 2026-08-01: "is there any way to load our map directly
	// without first showing the unscaled map?" With mode 1 the dock is still
	// 1x until the first sweep (+766..+2250ms measured), so the user watches a
	// small dock, then a jump.
	//
	// WHAT MAKES THIS DEFENSIBLE NOW, when "scale it earlier" was refuted:
	// that refutation was about the MESSAGE QUEUE - a posted WM_APP beat
	// WM_TIMER by 15ms because the game does not pump during the load tail.
	// This is not the queue. PostCityInit runs on the game's own call stack,
	// and mode 1 has now demonstrated across several runs that a scoped lookup
	// plus writes here is reachable and does not hang. The banned thing is the
	// full tree WALK (ScaleAll, 456 windows); this is ONE subtree, ~25 windows.
	//
	// Safety properties, all pre-existing rather than invented here:
	//  - ScalePanelRoot is the SAME function the sweep calls, so the geometry
	//    is identical by construction - not a second implementation to drift.
	//  - It records into scaleMap, so the later sweep classifies the dock
	//    AlreadyScaled and skips it. No double-scale, no 4x.
	//  - The factor comes from settings.spikeScaleFactor (what the sweep uses),
	//    NOT gTierF - gTierF is still its compiled default this early, which
	//    would silently be wrong at 1.5x/3x.
	//  - EarlyBake=1 keeps the old flags-only behaviour; =0 is fully inert.
	//
	// The minimap SURFACE still catches up at the first sweep, which is where
	// the capture/carry-over lives - so expect the map soft until then, not
	// blank. Moving that here too is the next step if this proves sound.
	if (settings.spikeEarlyBake >= 2)
	{
		const float f = settings.spikeScaleFactor;
		const int32_t fw = pView->GetW(), fh = pView->GetH();
		const int32_t beforeW = pDock->GetW();
		const int n = ScalePanelRoot(pDock, fw, fh, f);
		lg.WriteLine(LogLevel::Info,
			"UiSpike: EARLYDOCK scaled dock 0x0987B48F x%.2f at PostCityInit - "
			"%d window(s), %d -> %d wide. The dock should never be seen at 1x; "
			"the sweep will find it AlreadyScaled and skip it.",
			f, n, beforeW, pDock->GetW());
	}
}

namespace
{
	// v2.42.1: BMPX draw-log budget and root-pointer tracking. Declared here
	// (before Disarm) so the per-city reset in Disarm() can see them; the
	// BMPX machinery further down in the file shares the same anonymous
	// namespace and uses them directly.
	int    gBmpDrawLog = 0;
	bool   gBmpDrawLogSatLogged = false;
	// #153 SEATPROBE budget. Declared HERE, beside its sibling, for the same
	// reason: Disarm() resets it and Disarm is defined above the BMPX block.
	int    gBmpSeatProbe = 0;
	// #191 (2026-08-19). THAT COUNTER IS ONE GLOBAL BUDGET AND IT IS MEASURED
	// TO STARVE. Two captures, two different tiers, identical result:
	//   2026-08-18 22:04:57.250..505  24/24 rows, ALL id=0x48E945B4, x2.00
	//   2026-08-19 08:02:27.408..798  24/24 rows, ALL id=0x48E945B4, x3.00
	// 0x48E945B4 is the U-Drive-It mission marker; it redraws on a timer and
	// empties the budget inside 400 ms, so every runtime-supplied portrait
	// drawn afterwards produces NO ROW AT ALL. (The Debug BMPX budget went the
	// same way in the same run: 40/40 rows, same id, zero others.) A probe that
	// cannot emit is a REFUSAL, not a null - law 54 / NULL IS NOT EVIDENCE -
	// and it is exactly why the hover-portrait report has no runtime evidence.
	// Per-id quota: every distinct window id gets its own small share. The old
	// global count survives as a second, larger ceiling.
	struct BmpSeatQuota { uint32_t id; int used; };
	BmpSeatQuota gBmpSeatQuota[24] = {};
	int    gBmpSeatQuotaN = 0;
	bool BmpSeatBudget(uint32_t id)
	{
		if (gBmpSeatProbe >= 96) { return false; }
		for (int i = 0; i < gBmpSeatQuotaN; i++)
		{
			if (gBmpSeatQuota[i].id != id) { continue; }
			if (gBmpSeatQuota[i].used >= 4) { return false; }
			gBmpSeatQuota[i].used++;
			gBmpSeatProbe++;
			return true;
		}
		if (gBmpSeatQuotaN >= 24) { return false; }
		gBmpSeatQuota[gBmpSeatQuotaN].id = id;
		gBmpSeatQuota[gBmpSeatQuotaN].used = 1;
		gBmpSeatQuotaN++;
		gBmpSeatProbe++;
		return true;
	}
	// v2.42.3: an OPEN is (pointer changed) OR (hidden -> visible). The
	// v2.42.2 budget re-armed only on a NEW-HOOK pass, which is blind to
	// exactly the user's headline repro: the My Sims STRIP windows hook ONCE
	// at city load, so every later reopen hooks nothing, prints nothing, and
	// (in v2.42.2) got no invalidate either. `vis` carries that second half.
	struct BmpxRootTrack { uint32_t id; cIGZWin* ptr; bool vis; int seq; };
	BmpxRootTrack gBmpxRootTrack[32] = {};
	int gBmpxRootTrackN = 0;
	// Per-open draw census, flushed as ONE summary line at the NEXT open of
	// the same root (and at Disarm). Counts, not per-draw lines, so it can
	// never saturate: the whole point is that a FAILING open must produce a
	// line. drawn=0 vs drawn=N is the mechanism discriminator.
	uint32_t gBmpOpenId = 0;      // root whose open the census belongs to
	int gBmpOpenSeq = 0;          // 1-based: "the 3rd open was small"
	int gBmpOpenScaled = 0;       // draws we scaled (img < win)
	int gBmpOpenClamped = 0;      // draws already at window size (m -> 1)
	// Defined with the BMPX machinery further down (same anonymous
	// namespace, re-opened). Declared here so Disarm can flush the last
	// open of a city. It only writes a log line and zeroes counters - no
	// call into any game object, so it is legal in Disarm.
	void FlushBmpOpenCensus();
	// v2.43.3: MDOCK is a per-id FACT ("this script's marker differs from the
	// one our constant was measured on"), not a per-tick event - but it sat in
	// the dock path, which runs every 16ms while a flyout is open: 5211 lines
	// and a 1MB log in one session. Log it ONCE per id per city. Reset in
	// Disarm so a second city re-reports (the script could differ there).
	uint32_t gMDockLogged[8] = {};
	int gMDockLoggedN = 0;
	// #95: MDRIFT alarm switch ([Flyout] MarkerAlarm, default 1). Cheap -
	// one line per id per city via MDockShouldLog (ids XORed so a god-path
	// entry cannot silence its mayor-path twin).
	int gMDockAlarm = 1;
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

void UiSpike::Disarm()
{
	armed = false;
	continuous = false;
	// #92: invalidate the dashboard-gauge latches. They are function-local
	// statics far below this point AND keyed on the dashboard POINTER, so a
	// second city whose dashboard lands on a reused address would look
	// already-hooked and be skipped without a word. Bumping the epoch is the
	// only reach we have into them, and it cannot get stuck.
	gGaugeEpoch++;
	gUdVarSeen = false;   // #93: re-report the console variant next city
	gChartGeoLog = 0;     // #57: re-probe the chart in the next city
	gChartProbed = nullptr; // #57 phase 1: same second-city law as below
	gChartScaleLog = 0;     // #57: fresh CHARTSCALE lines next city
	gChartBornLog = 0;      // #57: fresh EARLYCHART/LEGENDOBJ lines next city
	gChartLegendLog = 0;    // #57: fresh legend recon next city
	gChartReconLog = 0;     // #57: fresh LEGENDCBOX/SWATCH next city
	gChartScaled = nullptr; // #57: second-city law - the new chart may reuse
	                        // this address; without the clear it would look
	                        // already-scaled and be silently skipped (#92).
	// Re-capture the menu baseline next city session: cheap, and safe in
	// both persistence worlds (persistent container -> same pointers
	// re-baselined; recreated container -> stale pointers dropped instead
	// of the new machinery being mistaken for flyouts).
	menuBaseline.clear();
	menuBaselineCaptured = false;

	// SECOND-CITY LIFECYCLE HARDENING (audit 2026-07-29, v2.23.3). DO NOT
	// remove these clears. Each latch below records a raw window pointer
	// (or per-pointer state) from THIS city; at PreCityShutdown the game
	// frees those windows, and the next city's allocator may hand the SAME
	// address to a brand-new object. A latch that survives the transition
	// then silently matches the new window and skips its one-shot work:
	//  - a skipped MINIMAP/DVMAP/UDMAP surface recreate leaves the stale 1x
	//    display surface under a window-sized renderer = the v2.21.0
	//    crash-on-expand shape, only in city 2;
	//  - a stale ready set / fail-open wait table misgates the flash guard;
	//  - a stale ADVHEAL latch skips city 2's advisor heal.
	// The trap signature is always "works in city 1, not in city 2".
	// VALUE-WRITES ONLY in Disarm: the window tree may be mid-teardown, so
	// never call into game objects from here.
	// v2.41.7 (SDK-law audit, 2026-08-01). lastView is a RAW cIGZWin* to the
	// city's 3D view (set at the end of ScalePanelsUnder). It belongs to this
	// same family and was missed because it arrived in v2.36.1, AFTER the
	// v2.23.3 audit that built this block.
	//
	// Why it is not merely untidy: its consumers are NOT the sweep. They are
	// OnFlyoutOpened (:4010), which runs from the MinHook detour on the flyout
	// opener - so it fires whenever the user opens a tool flyout, and that hook
	// is never uninstalled. Between city 2's PostCityInit and city 2's first
	// sweep (~1-2s, measured) lastView still points at CITY ONE's freed view,
	// and OnFlyoutOpened would call GetChildWindowFromIDRecursive through it.
	lastView = nullptr;
	lastMinimapSurfResize = nullptr;
	lastDataMapSurfResize = nullptr;
	gDvMapVisibleKick = nullptr;   // v2.69.4: pointer latch, #92 law
	gDvMapClampBlit = 0;           // v2.69.10: per-city clamp, #92 law
	lastUdMapSurfResize = nullptr;
	// v2.41.0 (task #89): the minimap/DVMAP/UDMAP retry budgets are per-city
	// for the same reason as every latch above - a budget that survives the
	// transition would report "exhausted" for a brand-new city-2 object at a
	// reused address and skip its recreate entirely.
	gMinimapRetry.Reset();
	gDataMapRetry.Reset();
	gUdMapRetry.Reset();
	gMmBufLogged = 0;   // MMBUF samples again next city (second-city law)
	// EARLYDOCK is per-city too: a pending flag surviving the transition would
	// fire against city 1's freed dock, and a stale child count would satisfy
	// the stability test instantly on city 2 - the exact half-built subtree the
	// gate exists to avoid.
	gEarlyDockPending = false;
	gEarlyDockCalls = 0;
	gEarlyDockLastCount = -1;
	gEarlyDockStable = 0;
	gEarlyDockChecks = 0;
	gEarlyDockLogged = 0;
	gInEarlyDock = false;
	gDlgAnchorCount = 0;      // v2.37.4: dialog anchors re-learn per city
	gDlgBornCount = 0;        // v2.38.0: DLGBORN reports once per city too
	gBudgetShowLog = 0;       // BUDGETSHOW re-arms per city - the whole
	gBudgetWatchLog = 0;      // and so does BUDGETWATCH; its baselines are
	for (BudgetWatch& bw : gBudgetWatch) { bw.seen = false; }  // per city
	gBudgetKidsLog = 0;
	gBudgetTickLog = 0;
	gMayorRebirthLogs = 0;    // #194: re-report per city
	gArtSizedRefusals = 0;    // #197
	gBudgetTickAnnounced = false;
	for (BudgetTick& bt : gBudgetTick) { bt.seen = false; }
	for (int& c : gBudgetKidsCount) { c = -1; }   // no baseline carries
	for (uint32_t& d : gBudgetKidsDigest) { d = 0; }  // across a city
	gBudgetShowOpens = 0;     // question is about the FIRST open of a city
	gMDockLoggedN = 0;        // v2.43.3: MDOCK re-reports per city
	FlushBmpOpenCensus();     // v2.42.3: report the city's last open
	gBmpDrawLog = 0;          // v2.42.1: BMPX draw budget re-arms per city
	gBmpSeatProbe = 0;        // #153 SEATPROBE budget, same discipline
	gBmpSeatQuotaN = 0;       // #191: and the per-id quota that now feeds it
	for (BmpSeatQuota& q : gBmpSeatQuota) { q.id = 0; q.used = 0; }
	gBmpDrawLogSatLogged = false;
	gBmpxRootTrackN = 0;      // v2.42.1: root pointers die with the city
	// v2.39.1: both strip pointers are RAW pointers to game objects that die
	// with the city. They happen to be safe today only because each builder
	// calls SetItemMetrics immediately before Place, so the pointer is always
	// re-set before it is read - safety by call ORDER, not by lifecycle. Null
	// them explicitly (the second-city law); the base metrics are stock
	// constants and deliberately survive.
	gSubLastStrip = nullptr;
	gDisLastStrip = nullptr;
	gDisDockValid = false;    // v2.39.3: new city, new toolbar
	gDisChromeHealed = nullptr;  // v2.39.4: heal again next city
	gDisDockLogged = nullptr;    // v2.39.5: next open logs its dock line
	// v2.39.10 (task #84): the bar-tile cache holds RAW ATLAS POINTERS and a
	// container pointer. Both die with the city; the second-city lifecycle law
	// (a function-local static holding a dead pointer) applies verbatim.
	gBarCacheN = 0;
	gBarCacheOwner = nullptr;
	gBarCacheSatLogged = false;
	gReadyCount = 0;          // gReadyWins latch table: per-city rebuild
	healPhase = 0;            // ADVHEAL state machine re-arms
	healDoneStrip = nullptr;  // ADVHEAL re-heals next city's strip
	for (int i = 0; i < 4; i++)
	{
		gFgWaitRoot[i] = nullptr;
		gFgWaitN[i] = 0;
	}
}

void UiSpike::ResetTracking()
{
	// APP shutdown only. Clearing between cities is exactly the double-scale
	// hazard: persistent windows would lose their "already scaled" records
	// and the next ScaleAll would compound 2x -> 4x.
	scaleMap.clear();
	menuBaseline.clear();
	menuBaselineCaptured = false;
}

void UiSpike::TickCheck(unsigned int nowTickMs)
{
	if (inPass)
	{
		// The timer fired on a nested message pump entered by one of our
		// cIGZWin calls: never run two walks on the same stack.
		return;
	}
	inPass = true;

	if (armed && static_cast<int>(nowTickMs - fireAtMs) >= 0)
	{
		armed = false; // initial fire exactly once per arming
		Run();
	}
	else if (continuous)
	{
		// Catch dynamically created UI (flyout submenus, dialogs, advisors).
		// Runs every tick (~16ms) so new panels (e.g. the Options toolbar)
		// scale before the user perceives a 1x flash. Crash-killer liveness
		// re-checks in ScalePanelsUnder/ScaleMenuFlyouts guard menu churn.
		++tickSerial;
		IncrementalPass();
	}

	// Boot recon: one-shot full main-window dump while NO city has ever
	// armed (i.e., sitting at the launch/region screen) so the region
	// screen's true window tree is observable without loading a city.
	// Runs ~20s after the first tick to let the screen settle.
	if (settings.spikeDumpTree && !bootDumpDone && !armed && !continuous)
	{
		if ((++tickSerial) > 1250) // ~20s of 16ms ticks
		{
			bootDumpDone = true;
			cISC4AppPtr pSC4App;
			cIGZWin* pMainWindow = pSC4App ? pSC4App->GetMainWindow() : nullptr;
			if (pMainWindow)
			{
				visibilityProbeOk = true;
				Logger::Get().WriteLine(LogLevel::Debug, "UiSpike: ---- BOOT tree dump begin ----");
				int total = 0;
				DumpTree(pMainWindow, 0, &total);
				Logger::Get().WriteLine(LogLevel::Debug, "UiSpike: ---- BOOT dump end, %d windows ----", total);
			}
		}
	}

	// The region screen exists when NO city is loaded, so its scaling
	// cannot hang off PostCityInit arming: poll for it from the (always-
	// running) subclass timer instead. Suppressed while a city arm is
	// pending so we never walk the region tree mid-teardown.
	if (settings.spikeScaleAll && settings.spikeScaleRegion && !armed)
	{
		RegionWatchTick(nowTickMs);
	}

	// DIAGNOSTIC: live city-view dump. While in a city (continuous), every
	// spikeLiveDumpMs ms, log each VISIBLE direct child of the 3D view and
	// its subtree - so an open query/tool panel is captured with its live,
	// post-scale geometry (the region DumpTree only fires at city init,
	// before any panel is open). Off unless LiveDumpMs>0.
	if (settings.spikeLiveDumpMs > 0 && continuous
		&& static_cast<int>(nowTickMs - lastLiveDumpMs) >= static_cast<int>(settings.spikeLiveDumpMs))
	{
		lastLiveDumpMs = nowTickMs;
		LiveViewDump();
	}

	inPass = false;
}

namespace
{
	struct LiveSnap
	{
		cIGZWin** out; int* n; int max;
		static bool Callback(cIGZWin* parent, uint32_t childID, void* child, void* pContext)
		{
			LiveSnap* s = static_cast<LiveSnap*>(pContext);
			if (*s->n < s->max) { s->out[(*s->n)++] = static_cast<cIGZWin*>(child); }
			return true;
		}
	};
}

// Dump the visible direct children (+ subtrees) of `parent`, skipping any
// child whose id == skipId (used to skip the giant 3D-view subtree). Tagged
// by `tag` so the two roots are distinguishable in the log.
void UiSpike::LiveDumpChildren(cIGZWin* parent, uint32_t skipId, const char* tag)
{
	if (!parent)
	{
		return;
	}
	Logger& logger = Logger::Get();
	cIGZWin* kids[256] = {};
	int nKids = 0;
	LiveSnap snap{ kids, &nKids, 256 };
	parent->EnumChildren(GZIID_cIGZWin, LiveSnap::Callback, &snap);

	logger.WriteLine(LogLevel::Debug,
		"UiSpike: ==== LIVE dump [%s] parent 0x%08X: %d children ====",
		tag, parent->GetID(), nKids);
	for (int i = 0; i < nKids; i++)
	{
		cIGZWin* k = kids[i];
		if (!k || !k->IsVisible() || k->GetID() == skipId)
		{
			continue;
		}
		logger.WriteLine(LogLevel::Debug,
			"UiSpike: -- [%s] visible child 0x%08X (%d,%d %dx%d) --",
			tag, k->GetID(), k->GetL(), k->GetT(), k->GetW(), k->GetH());
		int total = 0;
		DumpTree(k, 1, &total);
	}
	logger.WriteLine(LogLevel::Debug, "UiSpike: ==== LIVE dump [%s] end ====", tag);
}

void UiSpike::LiveViewDump()
{
	cISC4AppPtr pSC4App;
	cIGZWin* pMainWindow = pSC4App ? pSC4App->GetMainWindow() : nullptr;
	cIGZWin* pAppWin = pMainWindow
		? pMainWindow->GetChildWindowFromID(kGZWin_WinSC4App) : nullptr;
	cIGZWin* pView = pAppWin
		? pAppWin->GetChildWindowFromID(kGZWin_SC4View3DWin) : nullptr;
	if (!pAppWin)
	{
		return;
	}
	visibilityProbeOk = true; // DumpTree logs IsVisible(); safe in a city

	// FULL-TREE dump (2026-07-23): the god-mode disaster/day-night flyouts do
	// NOT appear under the view or main-window direct children (they're
	// parented deeper - likely the menu-flyout machinery). A complete
	// recursion from the main window guarantees they're captured wherever
	// they live, so the god-flyout geometry is fully known before building.
	if (pMainWindow)
	{
		Logger& lg = Logger::Get();
		lg.WriteLine(LogLevel::Debug, "UiSpike: ==== LIVE full-tree dump begin ====");
		int total = 0;
		DumpTree(pMainWindow, 0, &total);
		lg.WriteLine(LogLevel::Debug, "UiSpike: ==== LIVE full-tree dump end, %d windows ====", total);
	}
}

void UiSpike::Run()
{
	Logger& logger = Logger::Get();

	cISC4AppPtr pSC4App;
	if (!pSC4App)
	{
		logger.WriteLine(LogLevel::Error, "UiSpike: cISC4App unavailable.");
		return;
	}

	cIGZWin* pMainWindow = pSC4App->GetMainWindow();
	if (!pMainWindow)
	{
		logger.WriteLine(LogLevel::Error, "UiSpike: no main window.");
		return;
	}

	if (settings.spikeDumpTree)
	{
		// One-shot visibility probe on the main window before the walk trusts
		// IsVisible()/GetFlag() across the whole tree.
		logger.WriteLine(LogLevel::Debug, "UiSpike: probing IsVisible() on main window...");
		const bool mainVis = pMainWindow->IsVisible();
		logger.WriteLine(LogLevel::Debug, "UiSpike: IsVisible() survived; main vis=%d.", mainVis ? 1 : 0);
		visibilityProbeOk = true;

		logger.WriteLine(LogLevel::Debug, "UiSpike: ---- tree dump begin (with visibility) ----");
		int total = 0;
		DumpTree(pMainWindow, 0, &total);
		logger.WriteLine(LogLevel::Debug, "UiSpike: ---- dump end, %d windows ----", total);
	}

	if (settings.spikeScaleWindowId != 0)
	{
		ScaleTarget(pMainWindow);
	}

	if (settings.spikeScaleAll)
	{
		ScaleAllPanels(pMainWindow);
	}
}

namespace
{
	struct PanelInfo
	{
		cIGZWin* win;
		int32_t l, t, w, h;
	};

	struct CollectCtx
	{
		PanelInfo* panels;
		int count;
		int max;

		static bool Callback(cIGZWin* parent, uint32_t childID, void* child, void* pContext)
		{
			CollectCtx* ctx = static_cast<CollectCtx*>(pContext);
			if (ctx->count < ctx->max)
			{
				cIGZWin* win = static_cast<cIGZWin*>(child);
				PanelInfo& p = ctx->panels[ctx->count++];
				p.win = win;
				p.l = win->GetL();
				p.t = win->GetT();
				p.w = win->GetW();
				p.h = win->GetH();
			}
			return true;
		}
	};
}

bool UiSpike::MarkerIsDesignUnits(cIGZWin* win, float f)
{
	if (win == nullptr || f <= 1.0f) { return false; }
	std::map<void*, ScaleRecord>::const_iterator it = scaleMap.find(win);
	if (it == scaleMap.end())
	{
		// We never scaled it, so it still holds what the script declared.
		// This is the Landscape case: its invisible 0x0000AAAA marker is
		// never reached by that flyout's subtree scale, and it still read
		// (3,59) a full second and many sweep ticks after the open - so it
		// is a permanent state, not a race that waiting would fix.
		return true;
	}
	const ScaleRecord& rec = it->second;
	if (rec.id != win->GetID()) { return true; }   // address reuse: not ours
	if (win->GetW() == rec.scaledW && win->GetH() == rec.scaledH)
	{
		return false;                              // screen units (the S&L case)
	}
	if (win->GetW() == rec.origW && win->GetH() == rec.origH)
	{
		return true;                               // game reset it to design
	}
	// Neither size matches: something else owns this rect. Keep the
	// pre-v2.47.0 behaviour rather than inventing a correction.
	return false;
}

void UiSpike::StoreScaleRecord(void* win, ScaleRecord rec)
{
	// Carry the tug-of-war counter forward. See the header note: without
	// this, `++rec.resetRescales > 3` in Classify() is dead code because the
	// re-scale that follows resets the field to 0, and the game/us fight
	// forever at ~12 geometry mutations a second.
	std::map<void*, ScaleRecord>::iterator it = scaleMap.find(win);
	if (it != scaleMap.end())
	{
		rec.resetRescales = it->second.resetRescales;
	}
	scaleMap[win] = rec;
}

UiSpike::ScaleState UiSpike::Classify(cIGZWin* win)
{
	std::map<void*, ScaleRecord>::iterator it = scaleMap.find(win);
	if (it == scaleMap.end())
	{
		return ScaleState::Fresh;
	}

	ScaleRecord& rec = it->second;

	if (win->GetID() != rec.id)
	{
		// Address reuse: a DIFFERENT window now lives where a scaled one
		// died. Evict the stale record; this window was never scaled.
		scaleMap.erase(it);
		return ScaleState::Fresh;
	}

	if (rec.leaveAlone)
	{
		// Tombstoned: the game actively manages this window's geometry
		// (dynamic controls like the ticker marquee reset it every frame) or
		// the guard refused it. Never fight the game.
		return ScaleState::Unrecognized;
	}

	const int32_t w = win->GetW();
	const int32_t h = win->GetH();

	if (w == rec.scaledW && h == rec.scaledH)
	{
		return ScaleState::AlreadyScaled;
	}
	if (w == rec.origW && h == rec.origH)
	{
		// Same ID, back at the recorded pre-scale size. If this keeps
		// happening the GAME is resetting it each frame (dynamic control):
		// after a few rounds of the tug-of-war, tombstone it and let the
		// game win permanently.
		if (++rec.resetRescales > 3)
		{
			rec.leaveAlone = true;
			Logger::Get().WriteLine(
				LogLevel::Debug,
				"UiSpike: window 0x%08X tombstoned (game-managed geometry).",
				rec.id);
			return ScaleState::Unrecognized;
		}
		return ScaleState::ResetToOriginal;
	}
	return ScaleState::Unrecognized;
}

void UiSpike::ScaleAllPanels(cIGZWin* pMainWindow)
{
	Logger& logger = Logger::Get();

	// The city view window hosts every HUD panel as a direct child.
	cIGZWin* pAppWin = pMainWindow->GetChildWindowFromID(kGZWin_WinSC4App);
	cIGZWin* pView = pAppWin ? pAppWin->GetChildWindowFromID(kGZWin_SC4View3DWin) : nullptr;
	if (!pView)
	{
		logger.WriteLine(LogLevel::Error, "UiSpike: city view window not found.");
		return;
	}

	logger.WriteLine(
		LogLevel::Info,
		"UiSpike: ScaleAll x%.2f (view %dx%d)",
		settings.spikeScaleFactor, pView->GetW(), pView->GetH());

	const int scaled = ScalePanelsUnder(pView, "city");

	ApplyPanelDocks(pView, settings.spikeScaleFactor);

	// #126, law 47 (installed != executed): report both counters every pass, so
	// a hook that installs and never fires cannot be mistaken for a working one.
	logger.WriteLine(LogLevel::Info,
		"UiSpike: ScaleAll done, %d windows scaled. | minimap draw hook: "
		"installed=%d entered=%d stretched=%d (this line fires ONCE per city, "
		"right after install - see the FIRST FIRE line for the real answer)",
		scaled, gMmHooked, gMmEntries, gMmStretches);

	// RCI-column diagnostic (DYNAMIC-CONTROLS.md): cSC4WinRCI draws from its
	// window rect, so a doubled column doubles the graph for free - but the
	// research suspects these three escaped the sweep. Log their post-pass
	// geometry once per city so the next session's log settles it.
	const uint32_t rciColumns[] = { 0x09D27EB0, 0x29D27EC0, 0x49D27ED0 };
	for (uint32_t id : rciColumns)
	{
		cIGZWin* pCol = pView->GetChildWindowFromIDRecursive(id);
		if (pCol)
		{
			logger.WriteLine(
				LogLevel::Debug,
				"UiSpike: RCI column 0x%08X post-pass (%d,%d %dx%d) vis=%d",
				id, pCol->GetL(), pCol->GetT(), pCol->GetW(), pCol->GetH(),
				pCol->IsVisible() ? 1 : 0);
		}
		else
		{
			logger.WriteLine(LogLevel::Debug, "UiSpike: RCI column 0x%08X not found.", id);
		}
	}
	continuous = true; // incremental sweeps take over from here
}

// ===================== U-DRIVE-IT GAUGE DIALS (task #47) =====================
// MEASURED OFFLINE 2026-07-29 (tools/flyout-sim/emu_gauge.py — a new Unicorn
// harness that runs the REAL draw with a synthetic object; full write-up in
// tools/research/DYNAMIC-CONTROLS.md "Addendum — the U-Drive-It gauge class").
//
// The task brief prescribed the force-recreate-buffer lever. THE MEASUREMENT
// SAYS IT CANNOT APPLY: class 0xCBCBF1E0 has no cached buffer and no cached
// width. Its object is 0x108 bytes (factory 0x00466220, ctor 0x007628E0,
// window pointer = classBase+4) and its whole field set is
//   +0xd8 strip image   +0xe8 frame count   +0xf8 frame index
//   +0xec/0xf0/0xf4 min/max/value floats    +0x6c draw context (cIGZWin base)
// all offsets relative to the cIGZWin pointer. There is nothing resembling the
// minimap's [+0xE4] blitSize / [+0xF0] one-shot surface, nor the disaster
// container's [0xdc] buffer whose [buf+0x1c] we corrupt.
//
// The draw-self override is cIGZWin vtable slot 88 (+0x160) = 0x00762830, and
// it is 30 instructions long:
//     img=[this+0xd8]; count=[this+0xe8];        (bail if either is empty)
//     H=img->Height(); W=img->Width(); cellW=W/count;
//     frame = this->vt[72]() ? [this+0xf8] : 0;
//     src = {frame*cellW, 0, frame*cellW+cellW, H};
//     dst = {0, 0, cellW, H};
//     [this+0x6c]->vt[38](img, &src, &dst);      // +0x98, callee cleans 12
// The WINDOW RECT IS NEVER READ. This class is ART-SIZE-DERIVED — the exact
// rule already documented for cSC4WinTrendBar — so its content stays 1x in the
// top-left of a doubled window no matter what we do to the window. Emulator:
//   1x art (928x62 /16) in a 116x124 window -> dst (0,0, 58, 62)   <- the bug
//   2x art (1856x124/16) in the same window -> dst (0,0,116,124)   <- the goal
//
// The art cannot be fixed by the art pass either: the .UI declares these
// children with NO image= at all, and the dashboard binder (0x005646AE) loads
// each strip from the VEHICLE EXEMPLAR (property 0x2BE8E6CB, group 0x46A006B0)
// and pushes it in through the custom interface (SetImage = main-vtable slot 4,
// 0x00762680). Code-bound TGIs are invisible to the reference-driven build.
//
// So the lever is the ONE draw-context call: scale its DESTINATION rect, which
// reproduces the emulator's 2x-art result exactly and lets the engine stretch
// the pristine 1x strip. Scaling the SOURCE instead would read past the texture
// edge — the documented tiling mess (GOD-MODE-FLYOUTS.md v2.7.94). This is the
// mirror image of the already in-game-confirmed BltThunkCtx src/dst decouple.
namespace
{
	// The class's cIGZWin vtable, and its length: the class's MAIN vtable sits
	// at 0x00AB4900, i.e. exactly 0x260 bytes (152 slots) later, and the highest
	// slot the class overrides is 148. 152 is therefore the measured table
	// length — copy that many and nothing else.
	void** const kGaugeClassVt = reinterpret_cast<void**>(0x00AB46A0);
	constexpr uintptr_t kGaugeDrawVA = 0x00762830;   // slot 88 (draw-self)
	constexpr int kGaugeVtSlots = 152;
	constexpr int kGaugeDrawSlot = 88;
	constexpr int kGaugeCtxBltSlot = 38;             // ctx vtable +0x98
	constexpr int kGaugeMaxInst = 16;                // car has 5, boat 5

	typedef uintptr_t(__thiscall* GaugeDrawFn)(void* self);
	typedef int(__thiscall* GaugeCtxBltFn)(void* self, void* img,
		int32_t* src, int32_t* dst);

	GaugeDrawFn   gGaugeOrigDraw = nullptr;
	GaugeCtxBltFn gGaugeOrigCtxBlt = nullptr;
	void*  gGaugeCtxVtCopy[64] = {};
	void** gGaugeCtxVtSrc = nullptr;      // the ctx vtable gGaugeCtxVtCopy mirrors
	bool   gGaugeInDraw = false;          // true only inside a gauge draw
	float  gGaugeScale = 1.0f;            // the sweep's scale factor
	int32_t gGaugeWinW = 0, gGaugeWinH = 0;   // live window size of the gauge
	uint32_t gGaugeCurId = 0;
	int    gGaugeDrawLog = 0;

	cIGZWin* gGaugeHooked[kGaugeMaxInst] = {};
	void*    gGaugeVtCopy[kGaugeMaxInst][kGaugeVtSlots] = {};
	int      gGaugeHookedN = 0;
	bool     gGaugeCapLogged = false;

	// Rewrite the destination rect of the gauge's single blit. Self-limiting:
	// the multiplier starts at the sweep's factor and is reduced until the
	// scaled cell still fits the LIVE window, so a window the sweep did not
	// double is left at exactly its stock size (no clipping, no regression).
	int __fastcall GaugeCtxBltThunk(void* self, void* /*edx*/,
		void* img, int32_t* src, int32_t* dst)
	{
		// GBLT diagnostic (v2.25.12, "duplicate dials" on the Free Drive
		// console): log EVERY blit made during a hooked gauge draw, raw
		// src+dst, so the artifact's exact draw shows itself. Capped.
		if (gGaugeInDraw && src && dst)
		{
			static int gbltLog = 0;
			if (gbltLog < 24)
			{
				gbltLog++;
				Logger::Get().WriteLine(LogLevel::Debug,
					"UiSpike: GBLT id=0x%08X src(%d,%d,%d,%d) dst(%d,%d,%d,%d) win %dx%d",
					gGaugeCurId, src[0], src[1], src[2], src[3],
					dst[0], dst[1], dst[2], dst[3], gGaugeWinW, gGaugeWinH);
			}
		}
		if (gGaugeInDraw && dst && gGaugeScale > 1.01f)
		{
			__try
			{
				const int32_t cw = dst[2] - dst[0];
				const int32_t ch = dst[3] - dst[1];
				if (dst[0] == 0 && dst[1] == 0 && cw > 0 && ch > 0
					&& gGaugeWinW > 0 && gGaugeWinH > 0)
				{
					// #186: ask whether the SOURCE is still 1x art, and ask it
					// ABSOLUTELY - the old test was `m < 0.75f * gGaugeScale`,
					// which is relative to the tier and therefore measured
					// itself at a fractional one (law 95). At 2x that threshold
					// is 1.50 and any already-scaled strip (cell ~= window,
					// m ~= 1.0) cleared it by a mile. At 1.5x it collapses to
					// 1.125 - INSIDE the band of legitimate rounding
					// disagreement between cell-first art (#171: cell 77) and
					// an edge-derived window (87) - so 0xEBCB9403 came out at
					// min(87/77, 93/75) = 1.1299 and missed the snap by 0.005.
					// A 1.13x stretch of a 4235px-wide tiled source is exactly
					// the residual that split the dials in v2.25.12.
					//
					// The honest question is "is this source 1x?", which the
					// tier cannot answer. 1x art in a scaled window satisfies
					// R(cell*f) <= win BY CONSTRUCTION - that is what 1x art
					// means here. Already-scaled art overshoots by about the
					// whole factor. kFitSlack absorbs the 1-2px cell-first vs
					// edge-derived disagreement that only exists at q > 1.
					//
					// INTEGER-TIER NO-OP, checked against CAPTURES and not
					// against the numbers this comment would have liked:
					//   3x, cell 204x180 in win 213x213 (72 GBLT lines in
					//       _tests/captures, the only 3x gauge geometry we
					//       have ever measured): OLD m = min(3, 213/204,
					//       213/180) = 1.0441 < 0.75*3 = 2.25 -> snap to 1.0.
					//       NEW want = 612x540 >> 215 -> pure copy. IDENTICAL.
					//   1.5x, cell 102x96 in win 106x107 and 107x107: OLD
					//       m = 1.0392 / 1.0490, both < 1.125 -> snap. NEW
					//       want = 153x144 -> pure copy. IDENTICAL.
					// Across every captured gauge geometry the ONLY divergence
					// is 0xEBCB9403 (cell 77x75, win 87x93 at 1.5x), which is
					// the defect this exists to fix.
					//
					// The 1x-art branch is reasoned, NOT measured, and says so:
					// task47-gauges.md's "cell 58x62 win 116x124 -> x2.00" is
					// under its "WHAT TO LOOK FOR ON THE NEXT IN-GAME RUN"
					// heading - a PREDICTED log line, and it appears in zero
					// captures. Worked through anyway: want = 116x124 <= win,
					// so sourceIsOneX holds, neither clamp trips, and the
					// result is dst 116x124 at the full 2.00 - the #47 cure
					// unchanged. Believe the arithmetic, not the provenance.
					//
					// KNOWN, BOUNDED BEHAVIOUR CHANGE (adversarial review,
					// 2026-08-18): the guard's SHAPE went from relative to
					// absolute, so 1x art whose cell OVERFLOWS its own stock
					// window by 5-25% would flip from stretch-to-fit to pure
					// copy. Nothing in the repo has that shape - captures,
					// cell-strips.txt and the shipped packages all show the
					// window ~4-5% LARGER than the cell - and such art would
					// already clip at stock. Recorded rather than hidden.
					//
					// It also keeps the original self-limiting property: a
					// window the sweep never scaled has win ~= cell, so want
					// overshoots and the draw stays at stock size.
					constexpr int32_t kFitSlack = 2;
					const int32_t wantW =
						static_cast<int32_t>(cw * gGaugeScale + 0.5f);
					const int32_t wantH =
						static_cast<int32_t>(ch * gGaugeScale + 0.5f);
					const bool sourceIsOneX = (wantW <= gGaugeWinW + kFitSlack)
						&& (wantH <= gGaugeWinH + kFitSlack);
					float m = 1.0f;
					if (sourceIsOneX)
					{
						m = gGaugeScale;
						if (cw * m > static_cast<float>(gGaugeWinW))
							m = static_cast<float>(gGaugeWinW) / cw;
						if (ch * m > static_cast<float>(gGaugeWinH))
							m = static_cast<float>(gGaugeWinH) / ch;
					}
					else if (gGaugeDrawLog < 12)
					{
						// Law 54: no log line = did not run. The suppressed
						// path used to be silent, so "the stretch is off" and
						// "the hook never fired" read identically in a capture.
						gGaugeDrawLog++;
						Logger::Get().WriteLine(LogLevel::Debug,
							"UiSpike: GAUGE copy id=0x%08X cell %dx%d win %dx%d "
							"- source already tier-scaled (want %dx%d), pure "
							"copy, no stretch",
							gGaugeCurId, cw, ch, gGaugeWinW, gGaugeWinH,
							wantW, wantH);
					}
					if (m > 1.001f)
					{
						dst[2] = static_cast<int32_t>(cw * m + 0.5f);
						dst[3] = static_cast<int32_t>(ch * m + 0.5f);
						if (gGaugeDrawLog < 12)
						{
							gGaugeDrawLog++;
							Logger::Get().WriteLine(LogLevel::Debug,
								"UiSpike: GAUGE draw id=0x%08X cell %dx%d win %dx%d "
								"-> dst %dx%d (x%.2f)",
								gGaugeCurId, cw, ch, gGaugeWinW, gGaugeWinH,
								dst[2], dst[3], m);
						}
					}
				}
			}
			__except (EXCEPTION_EXECUTE_HANDLER) {}
		}
		return gGaugeOrigCtxBlt ? gGaugeOrigCtxBlt(self, img, src, dst) : 1;
	}

	// Per-instance draw-self hook. Swaps the DRAW CONTEXT's vtable pointer to a
	// copy whose slot 38 is ours, for the duration of this one draw only, then
	// restores it. The context is shared with other windows, so the swap must
	// never outlive the call — same discipline as the disaster BltThunkCtx.
	uintptr_t __fastcall GaugeDrawThunk(void* self, void* /*edx*/)
	{
		void*  ctx = nullptr;
		void** ctxSavedVt = nullptr;
		__try
		{
			int32_t* m = reinterpret_cast<int32_t*>(self);
			gGaugeWinW = m[0x2c] - m[0x2a];    // window rect [+0xa8..0xb4] L,T,R,B
			gGaugeWinH = m[0x2d] - m[0x2b];
			gGaugeCurId = static_cast<cIGZWin*>(self)->GetID();
			ctx = *reinterpret_cast<void**>(
				reinterpret_cast<char*>(self) + 0x6c);
			if (ctx && gGaugeScale > 1.01f)
			{
				void** vt = *reinterpret_cast<void***>(ctx);
				if (vt && vt != reinterpret_cast<void**>(&gGaugeCtxVtCopy[0]))
				{
					if (vt != gGaugeCtxVtSrc)
					{
						for (int i = 0; i < 64; i++) gGaugeCtxVtCopy[i] = vt[i];
						gGaugeOrigCtxBlt =
							reinterpret_cast<GaugeCtxBltFn>(vt[kGaugeCtxBltSlot]);
						gGaugeCtxVtCopy[kGaugeCtxBltSlot] =
							reinterpret_cast<void*>(&GaugeCtxBltThunk);
						gGaugeCtxVtSrc = vt;
					}
					ctxSavedVt = vt;
					*reinterpret_cast<void***>(ctx) =
						reinterpret_cast<void**>(&gGaugeCtxVtCopy[0]);
					gGaugeInDraw = true;
				}
			}
		}
		__except (EXCEPTION_EXECUTE_HANDLER)
		{
			ctxSavedVt = nullptr;
			gGaugeInDraw = false;
		}

		const uintptr_t ret = gGaugeOrigDraw
			? gGaugeOrigDraw(self)
			: reinterpret_cast<GaugeDrawFn>(kGaugeDrawVA)(self);

		gGaugeInDraw = false;
		if (ctx && ctxSavedVt)
		{
			__try { *reinterpret_cast<void***>(ctx) = ctxSavedVt; }
			__except (EXCEPTION_EXECUTE_HANDLER) {}
		}
		return ret;
	}

	// Install on ONE window, but only after POSITIVELY identifying the class by
	// its vtable AND its slot-88 target. The v2.22.1 Earned Cars crash was a
	// shared class hooked without context, so nothing here is inferred from an
	// id, a size or a name.
	bool HookGaugeInstance(cIGZWin* win, cIGZWin* parent)
	{
		if (!win) return false;
		bool ok = false;
		__try
		{
			void** vt = *reinterpret_cast<void***>(win);
			// Already ours? (idempotent re-sweep, or an address the allocator
			// handed back to a new object - the slot check catches both.)
			for (int i = 0; i < gGaugeHookedN; i++)
			{
				if (gGaugeHooked[i] == win
					&& vt == reinterpret_cast<void**>(&gGaugeVtCopy[i][0]))
				{
					return false;
				}
			}
			if (vt != kGaugeClassVt) return false;             // wrong class
			// v2.25.11: accept a FlashGuard thunk in slot 88 (DFG patches
			// class vtables in place; kFgMax=12 can reach this class too -
			// the exact silent-miss that kept BMPX dark since v2.25.0).
			{
				void* slot88 = vt[kGaugeDrawSlot];
				bool ok88 = (slot88 == reinterpret_cast<void*>(kGaugeDrawVA));
				for (int i = 0; i < kFgMax && !ok88; i++)
				{
					if (slot88 == reinterpret_cast<void*>(kFgThunks[i]))
					{
						ok88 = true;
					}
				}
				if (!ok88) return false;                       // wrong layout
			}
			int slot = -1;
			for (int i = 0; i < gGaugeHookedN; i++)
			{
				if (gGaugeHooked[i] == win || gGaugeHooked[i] == nullptr)
				{
					slot = i;
					break;
				}
			}
			if (slot < 0)
			{
				if (gGaugeHookedN >= kGaugeMaxInst)
				{
					if (!gGaugeCapLogged)
					{
						gGaugeCapLogged = true;
						Logger::Get().WriteLine(LogLevel::Info,
							"UiSpike: GAUGE instance cap %d reached - remaining "
							"gauges stay at stock size.", kGaugeMaxInst);
					}
					return false;
				}
				slot = gGaugeHookedN++;
			}
			for (int i = 0; i < kGaugeVtSlots; i++) gGaugeVtCopy[slot][i] = vt[i];
			if (!gGaugeOrigDraw)
				gGaugeOrigDraw = reinterpret_cast<GaugeDrawFn>(vt[kGaugeDrawSlot]);
			gGaugeVtCopy[slot][kGaugeDrawSlot] =
				reinterpret_cast<void*>(&GaugeDrawThunk);
			*reinterpret_cast<void***>(win) =
				reinterpret_cast<void**>(&gGaugeVtCopy[slot][0]);
			gGaugeHooked[slot] = win;
			ok = true;
		}
		__except (EXCEPTION_EXECUTE_HANDLER)
		{
			Logger::Get().WriteLine(LogLevel::Error,
				"UiSpike: GAUGE hook FAULTED (instance skipped)");
			return false;
		}
		if (ok)
		{
			Logger::Get().WriteLine(LogLevel::Debug,
				"UiSpike: GAUGE 2X win %dx%d parent=0x%08X id=0x%08X - hooking "
				"draw slot 88 (dst rect -> x%.2f)",
				win->GetW(), win->GetH(),
				parent ? parent->GetID() : 0u, win->GetID(), gGaugeScale);
		}
		return ok;
	}

	struct GaugeWalkCtx
	{
		int depth;
		int* installed;

		static bool Callback(cIGZWin* parent, uint32_t /*childID*/,
			void* child, void* pContext)
		{
			GaugeWalkCtx* ctx = static_cast<GaugeWalkCtx*>(pContext);
			cIGZWin* win = static_cast<cIGZWin*>(child);
			if (!win) return true;
			if (HookGaugeInstance(win, parent)) (*ctx->installed)++;
			if (ctx->depth < 6)
			{
				GaugeWalkCtx sub = { ctx->depth + 1, ctx->installed };
				win->EnumChildren(GZIID_cIGZWin, GaugeWalkCtx::Callback, &sub);
			}
			return true;
		}
	};

	// Hook every 0xCBCBF1E0 instance under the DASHBOARD root only. Scoped, not
	// global-recursive: id collisions across roots are what broke v2.22.3, and
	// this class has 134 uses across the .UI corpus.
	void HookDashboardGauges(cIGZWin* pRoot, float f)
	{
		static cIGZWin* lastDashRoot = nullptr;
		static int gaugeHealPasses = 0;
		// #92: declared up here with the other latches (they used to sit 30
		// lines down) so ONE epoch check can drop all three together.
		static cIGZWin* scanRoot = nullptr;
		static int scanCount = 0;
		cIGZWin* pDash = pRoot
			? pRoot->GetChildWindowFromIDRecursive(0x4BCB938A) : nullptr;
		if (!pDash || f <= 1.01f) return;
		gGaugeScale = f;
		// #92: a new city invalidates every pointer-keyed latch here. Without
		// this, a second dashboard at a REUSED address looks like the same
		// object and its gauges are never hooked - silently, since the code
		// believes the work is done. See gGaugeEpoch.
		static int seenGaugeEpoch = -1;
		if (seenGaugeEpoch != gGaugeEpoch)
		{
			seenGaugeEpoch = gGaugeEpoch;
			lastDashRoot = nullptr;
			scanRoot = nullptr;
			scanCount = 0;
		}
		if (pDash != lastDashRoot)
		{
			// GAUGE GHOST HEAL (v2.25.13, GBLT-measured): the game draws the
			// FIRST 68x60 needle frame the instant the console is created -
			// our hook lands on the next sweep, up to 250 ms later - and that
			// pre-hook frame is baked into the console composite. Needle
			// frames are mostly transparent, so the corrected 136x120 draws
			// never cover it: a permanent small ghost dial at the top-left
			// ("duplicates ... settles in the middle at top speed"). Force
			// the console to re-composite for a few sweeps after hooking.
			gaugeHealPasses = 3;
			// New dashboard object: drop the old latches WITHOUT touching the
			// old windows (they are freed - writing their vtable back would be
			// a use-after-free). Our vtable copies are static, so nothing the
			// dead objects could still reference goes away.
			for (int i = 0; i < kGaugeMaxInst; i++) gGaugeHooked[i] = nullptr;
			gGaugeHookedN = 0;
			gGaugeDrawLog = 0;
			lastDashRoot = pDash;
		}
		// GAUGESCAN diagnostic (v2.25.12): survey EVERY gauge-class window
		// under the dash each of the first passes - reveals any sibling
		// instance (a game-created duplicate, an unscaled twin) that the
		// hook bookkeeping would not log. Capped to 3 surveys per dash.
		if (pDash != scanRoot) { scanRoot = pDash; scanCount = 0; }
		if (scanCount < 3)
		{
			scanCount++;
			ChildSnapshot gk = {};
			pDash->EnumChildren(GZIID_cIGZWin, ChildSnapshot::Callback, &gk);
			for (int i = 0; i < gk.count; i++)
			{
				cIGZWin* w = gk.wins[i];
				if (!w) { continue; }
				void** vt = *reinterpret_cast<void***>(w);
				const bool isGauge = (vt == kGaugeClassVt);
				const bool ours = (vt >= reinterpret_cast<void**>(&gGaugeVtCopy[0][0])
					&& vt <= reinterpret_cast<void**>(&gGaugeVtCopy[kGaugeMaxInst - 1][0]));
				if (isGauge || ours)
				{
					Logger::Get().WriteLine(LogLevel::Debug,
						"UiSpike: GAUGESCAN id=0x%08X vt=%p (%d,%d %dx%d) vis=%d %s",
						w->GetID(), (void*)vt, w->GetL(), w->GetT(),
						w->GetW(), w->GetH(), w->IsVisible() ? 1 : 0,
						ours ? "HOOKED" : "unhooked");
				}
			}
		}

		int installed = 0;
		GaugeWalkCtx ctx = { 0, &installed };
		if (HookGaugeInstance(pDash, pRoot)) installed++;
		pDash->EnumChildren(GZIID_cIGZWin, GaugeWalkCtx::Callback, &ctx);
		if (installed > 0)
		{
			Logger::Get().WriteLine(LogLevel::Info,
				"UiSpike: GAUGE %d instance(s) hooked under dashboard root "
				"0x4BCB938A (dash %dx%d)",
				installed, pDash->GetW(), pDash->GetH());
		}
		if (gaugeHealPasses > 0 && gGaugeHookedN > 0)
		{
			gaugeHealPasses--;
			for (int i = 0; i < gGaugeHookedN; i++)
			{
				if (gGaugeHooked[i]) { gGaugeHooked[i]->InvalidateSelfAndParents(); }
			}
			pDash->InvalidateSelfAndParents();
			Logger::Get().WriteLine(LogLevel::Debug,
				"UiSpike: GAUGE ghost-heal invalidate (%d left).",
				gaugeHealPasses);
		}
	}
}

// ============ RUNTIME-SUPPLIED GZWinBMP IMAGES (task #47, v2.25.0) ==========
// MEASURED OFFLINE 2026-07-30 (disassembly of Plot 0x9BC325; same session that
// root-caused task #55). GZWinBMP's draw-self override (cIGZWin vtable
// 0x00ADF6A0 slot 88 = 0x9BC325) has three paths:
//   background:  ctx vt[21]/vt[35] fill (untouched here)
//   PLAIN image: src = imagerect (flag 0x10) or the image's natural rect;
//                dst = {areaL, areaT, areaL+srcW, areaT+srcH}  - THE DRAW
//                FOLLOWS THE SOURCE, the window rect is never read - then ONE
//                ctx->vt[38](img, &src, &dst) blit (+0x98, same slot the
//                gauge class uses; flag 0x20 shifts dst by src.l/t first)
//   EDGE (flag bit 8 on the holder object at [this+0xd8], tested via its
//                vt[10]): src /= 3 then helper 0x8D8800 9-slices with MANY
//                vt[38] calls - scaling those would shear the frame. SKIP.
// So a RUNTIME-SUPPLIED 1x bitmap (My Sims portraits 36x41, Select-A-Sim
// picker faces - Path 4, in no dat, unreachable by any art pass) draws 1x in
// the top-left of its doubled window. The lever is the gauge fix's mirror:
// scale the ONE plain-path DEST rect about its own origin, self-limited to
// the live window so an already-2x image (or an unscaled window) is a no-op.
// The pickers' 42x42 thumbs are ALSO covered as insurance: their group
// 0x4C06F888 now ships 2x (task #55), which makes dst already fill the cell
// and the multiplier clamp to 1.0 - the two fixes cannot fight.
//
// Unlike the gauge hook there is NO per-instance vtable table: every GZWinBMP
// shares the ONE class vtable, so ONE static patched copy serves every hooked
// window. No instance cap, nothing leaks when transient pickers reopen, and
// dead windows dying while pointing at the static copy is harmless (it
// outlives them). The class vtable itself is NEVER written.
namespace
{
	void** const kBmpClassVt = reinterpret_cast<void**>(0x00ADF6A0);
	constexpr uintptr_t kBmpDrawVA = 0x009BC325;   // slot 88 (Plot override)
	constexpr int kBmpVtSlots = 151;   // measured: 151 code ptrs, then a 0
	constexpr int kBmpDrawSlot = 88;
	constexpr int kBmpCtxBltSlot = 38;             // ctx vtable +0x98
	constexpr int kBmpEdgeFlagBit = 8;             // 9-slice mode - never scale

	typedef uintptr_t(__thiscall* BmpDrawFn)(void* self);
	typedef int(__thiscall* BmpCtxBltFn)(void* self, void* img,
		int32_t* src, int32_t* dst);
	typedef bool(__thiscall* BmpFlagTestFn)(void* self, uint32_t flagBit);

	BmpDrawFn   gBmpOrigDraw = nullptr;
	BmpCtxBltFn gBmpOrigCtxBlt = nullptr;
	// #176 RELATCH arming flag - set per panel root by the sweep loop, read
	// at ScaleSubtree's resize site. Declared here (not with the helper)
	// because the arming site precedes the helper in this file.
	bool gRelatchArmed = false;
	void*  gBmpVtCopy[kBmpVtSlots] = {};   // the ONE shared patched vtable
	bool   gBmpVtReady = false;
	void*  gBmpCtxVtCopy[64] = {};
	void** gBmpCtxVtSrc = nullptr;         // ctx vtable the copy mirrors
	bool   gBmpInDraw = false;             // true only inside a hooked draw
	bool   gBmpBltDone = false;            // plain path = exactly ONE blit
	float  gBmpScale = 1.0f;
	int32_t gBmpWinW = 0, gBmpWinH = 0;
	uint32_t gBmpCurId = 0;
	// #153 PROBE: the hook scales dst ABOUT ITS OWN ORIGIN and never moves it,
	// so if a portrait lands a pixel off, the origin it was handed is already
	// wrong - and that origin comes from the WINDOW. The existing BMPX line
	// prints SIZES ONLY, which cannot distinguish "the window is misplaced"
	// from "the hook draws it wrong". These two capture the missing half.
	int32_t gBmpWinL = 0, gBmpWinT = 0;
	// #191: GetL()/GetT() are PARENT-RELATIVE, so the #153 row alone cannot say
	// whether a portrait sits wrong inside its frame or whether the frame is
	// itself displaced. Capture the parent id and the accumulated screen origin
	// too, so a single row can be checked against design x f offline.
	uint32_t gBmpParentId = 0;
	int32_t gBmpAbsL = 0, gBmpAbsT = 0;
	int32_t gBmpDepth = 0;                 // parents walked (0 = a root)

	// Scale the plain-path dest rect about its own origin. Self-limiting: the
	// multiplier starts at the sweep factor and is reduced until the scaled
	// image still fits the LIVE window, so an unscaled window or already-2x
	// pixels leave the draw at exactly stock size.
	int __fastcall BmpCtxBltThunk(void* self, void* /*edx*/,
		void* img, int32_t* src, int32_t* dst)
	{
		if (gBmpInDraw && !gBmpBltDone && src && dst && gBmpScale > 1.01f)
		{
			gBmpBltDone = true;   // one-shot: the plain path blits once
			__try
			{
				const int32_t w = dst[2] - dst[0];
				const int32_t h = dst[3] - dst[1];
				const int32_t sw = src[2] - src[0];
				const int32_t sh = src[3] - src[1];
				// Only the follows-source signature (dst size == src size).
				if (w > 0 && h > 0 && w == sw && h == sh
					&& gBmpWinW > 0 && gBmpWinH > 0)
				{
					float m = gBmpScale;
					if (w * m > static_cast<float>(gBmpWinW))
						m = static_cast<float>(gBmpWinW) / w;
					if (h * m > static_cast<float>(gBmpWinH))
						m = static_cast<float>(gBmpWinH) / h;
					if (m > 1.001f)
					{
						int32_t dw = static_cast<int32_t>(w * m + 0.5f);
						int32_t dh = static_cast<int32_t>(h * m + 0.5f);
						// #162 - CLOSE THE UNDERFILL, NOT JUST THE OVERFLOW.
						//
						// The two clamps above only fire when the scaled bitmap
						// is TOO BIG for the window. Nothing corrected the other
						// direction, and at a fractional factor the rounding
						// lands short about half the time:
						//     advisor portrait 41px tall, f=1.5 -> 61.5 -> 61
						//     inside a 62px window  =  ONE UNCOVERED ROW
						// which draws as a hairline under the portrait. Reported
						// under the advisor portraits AND under the mayor's face,
						// with "the lines don't exist at 2x" - at an integer
						// factor w*m is exact, so the shortfall is structurally
						// impossible there. That is the signature, not a
						// coincidence, and it is why three art-side fixes missed
						// it: these bitmaps are SUPPLIED AT RUNTIME and have no
						// .UI art entry to resize.
						//
						// ⛔ SLACK OF 2px, AND THAT BOUND IS THE WHOLE SAFETY.
						// A genuinely 1x bitmap in a scaled window is SHORT BY
						// HALF, and stretching that to fit is the #55 disaster
						// (1x art blown up inside a doubled frame). This may only
						// ever close a ROUNDING gap, never a SCALING one, so a
						// shortfall beyond 2px is left exactly as it is - visibly
						// small, which is the honest outcome and the deliberate
						// #47 trade.
						const int32_t kFillSlack = 2;
						if (dw < gBmpWinW && gBmpWinW - dw <= kFillSlack)
						{
							dw = gBmpWinW;
						}
						if (dh < gBmpWinH && gBmpWinH - dh <= kFillSlack)
						{
							dh = gBmpWinH;
						}
						dst[2] = dst[0] + dw;
						dst[3] = dst[1] + dh;
						gBmpOpenScaled++;   // v2.42.3 census: never saturates
					}
					else
					{
						gBmpOpenClamped++;
					}
					// v2.69.3: burn the 40-line budget ONLY when the rows can
					// actually be written. The rows moved to Debug in v2.69.0
					// but the counter kept incrementing at every level, so a
					// LogLevel=1 log carried the Info "saturated" sentence
					// with ZERO rows above it - an instrument announcing data
					// it never produced (measured: 20+ such sentences in one
					// capture session).
					// #153 SEATPROBE. The question this answers, and NOTHING
					// else in this file can: does the 1px belong to the WINDOW
					// or to this hook's own draw?
					//
					// This hook scales dst about dst[0],dst[1] and NEVER moves
					// it (see above: only dst[2]/dst[3] are written). So the
					// origin is handed in, not chosen here. Printing it beside
					// the window's own L/T is the whole experiment:
					//   dst origin tracks win L/T   -> the WINDOW is misplaced,
					//                                  and the offset-parity law
					//                                  (#152) is the cure
					//   dst origin differs by 1     -> the hook's caller applies
					//                                  its own inset, and the
					//                                  .UI must NOT be edited
					//
					// ⚠ INFO level, not Debug, and its OWN budget - the existing
					// BMPX rows are Debug and were invisible at the user's live
					// logLevel. An instrument nobody can read is not evidence
					// (law 54: no log line = did not run).
					if (BmpSeatBudget(gBmpCurId))
					{
						Logger::Get().WriteLine(LogLevel::Info,
							"UiSpike: SEATPROBE id=0x%08X parent=0x%08X d=%d "
							"win L,T=(%d,%d) %dx%d abs=(%d,%d) "
							"| dst origin=(%d,%d) src %dx%d -> dst %dx%d "
							"(x%.2f) f=%.2f",
							gBmpCurId, gBmpParentId, gBmpDepth,
							gBmpWinL, gBmpWinT, gBmpWinW, gBmpWinH,
							gBmpAbsL, gBmpAbsT,
							dst[0], dst[1], sw, sh,
							dst[2] - dst[0], dst[3] - dst[1], m, gBmpScale);
					}
					if (Logger::Get().IsEnabled(LogLevel::Debug))
					{
						if (gBmpDrawLog < 40)
						{
							gBmpDrawLog++;
							if (m > 1.001f)
								Logger::Get().WriteLine(LogLevel::Debug,
									"UiSpike: BMPX draw id=0x%08X img %dx%d win %dx%d "
									"-> dst %dx%d (x%.2f)",
									gBmpCurId, w, h, gBmpWinW, gBmpWinH,
									dst[2] - dst[0], dst[3] - dst[1], m);
							else
								Logger::Get().WriteLine(LogLevel::Debug,
									"UiSpike: BMPX draw-skip id=0x%08X img %dx%d "
									"win %dx%d (m clamped to 1)",
									gBmpCurId, w, h, gBmpWinW, gBmpWinH);
						}
						else if (!gBmpDrawLogSatLogged)
						{
							gBmpDrawLogSatLogged = true;
							Logger::Get().WriteLine(LogLevel::Info,
								"UiSpike: BMPX drawlog saturated at 40 lines "
								"- further BMPX draws are silent this budget.");
						}
					}
				}
			}
			__except (EXCEPTION_EXECUTE_HANDLER) {}
		}
		return gBmpOrigCtxBlt ? gBmpOrigCtxBlt(self, img, src, dst) : 1;
	}

	// Draw-self hook: arm the ctx slot-38 swap for THIS draw only (restored
	// immediately after - the context is shared, same discipline as the gauge
	// and disaster thunks), and only for the PLAIN path (edge mode skipped).
	uintptr_t __fastcall BmpDrawThunk(void* self, void* /*edx*/)
	{
		void*  ctx = nullptr;
		void** ctxSavedVt = nullptr;
		__try
		{
			cIGZWin* w = static_cast<cIGZWin*>(self);
			gBmpWinW = w->GetW();
			gBmpWinH = w->GetH();
			gBmpWinL = w->GetL();     // #153 probe: position, not just size
			gBmpWinT = w->GetT();
			gBmpCurId = w->GetID();
			// #191: parent id + accumulated screen origin. Read-only, already
			// inside this function's __try, and bounded at 24 hops exactly like
			// IsOnScreen's guard so a self-parented or cyclic node cannot spin.
			gBmpParentId = ParentIdOf(w);
			gBmpAbsL = gBmpWinL;
			gBmpAbsT = gBmpWinT;
			gBmpDepth = 0;
			{
				cIGZWin* pw = w->GetParentWin();
				while (pw && pw != w && gBmpDepth < 24)
				{
					gBmpAbsL += pw->GetL();
					gBmpAbsT += pw->GetT();
					gBmpDepth++;
					cIGZWin* nx = pw->GetParentWin();
					if (nx == pw) { break; }
					pw = nx;
				}
			}
			// EDGE/9-slice test, exactly as the draw itself does it: the
			// holder object embedded at [this+0xd8] answers vt[10](bit).
			bool edgeMode = false;
			char* holder = reinterpret_cast<char*>(self) + 0xd8;
			void** hvt = *reinterpret_cast<void***>(holder);
			if (hvt && hvt[10])
			{
				edgeMode = reinterpret_cast<BmpFlagTestFn>(hvt[10])(
					holder, kBmpEdgeFlagBit);
			}
			if (!edgeMode && gBmpScale > 1.01f)
			{
				ctx = *reinterpret_cast<void**>(
					reinterpret_cast<char*>(self) + 0x6c);
				if (ctx)
				{
					void** vt = *reinterpret_cast<void***>(ctx);
					if (vt && vt != reinterpret_cast<void**>(&gBmpCtxVtCopy[0]))
					{
						if (vt != gBmpCtxVtSrc)
						{
							for (int i = 0; i < 64; i++) gBmpCtxVtCopy[i] = vt[i];
							gBmpOrigCtxBlt =
								reinterpret_cast<BmpCtxBltFn>(vt[kBmpCtxBltSlot]);
							gBmpCtxVtCopy[kBmpCtxBltSlot] =
								reinterpret_cast<void*>(&BmpCtxBltThunk);
							gBmpCtxVtSrc = vt;
						}
						ctxSavedVt = vt;
						*reinterpret_cast<void***>(ctx) =
							reinterpret_cast<void**>(&gBmpCtxVtCopy[0]);
						gBmpInDraw = true;
						gBmpBltDone = false;
					}
				}
			}
		}
		__except (EXCEPTION_EXECUTE_HANDLER)
		{
			ctxSavedVt = nullptr;
			gBmpInDraw = false;
		}

		const uintptr_t ret = gBmpOrigDraw
			? gBmpOrigDraw(self)
			: reinterpret_cast<BmpDrawFn>(kBmpDrawVA)(self);

		gBmpInDraw = false;
		if (ctx && ctxSavedVt)
		{
			__try { *reinterpret_cast<void***>(ctx) = ctxSavedVt; }
			__except (EXCEPTION_EXECUTE_HANDLER) {}
		}
		return ret;
	}

	// Hook one window IF it is positively a GZWinBMP (class vtable AND slot-88
	// target verified - law 3, the Earned Cars lesson). Idempotent: a window
	// already on the shared copy is recognized and skipped.
	bool HookBmpInstance(cIGZWin* win)
	{
		if (!win) return false;
		bool ok = false;
		__try
		{
			void** vt = *reinterpret_cast<void***>(win);
			if (vt == reinterpret_cast<void**>(&gBmpVtCopy[0]))
				return false;                              // already ours
			if (vt != kBmpClassVt) return false;           // wrong class
			// v2.25.11: slot 88 may legitimately hold a FlashGuard thunk -
			// DFG patches CLASS vtables in place (log: "DFG patched class
			// vt=00ADF6A0 Plot=009BC325 idx 4"), and that single line is why
			// BMPX never engaged ANYWHERE (zero BMPX log lines since
			// v2.25.0; the kFgMax 6->12 raise let DFG reach this class).
			// Accept the FG thunk: the chain stays intact (our per-copy
			// draw -> FG thunk -> 0x9BC325).
			{
				void* slot88 = vt[kBmpDrawSlot];
				bool ok88 = (slot88 == reinterpret_cast<void*>(kBmpDrawVA));
				for (int i = 0; i < kFgMax && !ok88; i++)
				{
					if (slot88 == reinterpret_cast<void*>(kFgThunks[i]))
					{
						ok88 = true;
					}
				}
				if (!ok88) return false;                   // wrong layout
			}
			if (!gBmpVtReady)
			{
				for (int i = 0; i < kBmpVtSlots; i++) gBmpVtCopy[i] = vt[i];
				gBmpOrigDraw = reinterpret_cast<BmpDrawFn>(vt[kBmpDrawSlot]);
				gBmpVtCopy[kBmpDrawSlot] =
					reinterpret_cast<void*>(&BmpDrawThunk);
				gBmpVtReady = true;
			}
			*reinterpret_cast<void***>(win) =
				reinterpret_cast<void**>(&gBmpVtCopy[0]);
			ok = true;
		}
		__except (EXCEPTION_EXECUTE_HANDLER)
		{
			return false;
		}
		return ok;
	}

	// v2.42.4 (#47): the freshly hooked leaves, so the caller can kick ONE
	// repaint through each of them. MEASURED NEED: on the picker's 2nd open
	// the root pointer changed, 25 instances hooked, and the census still
	// read scaled=0 clamped=0 across 13 seconds on screen - the engine put
	// pixels there WITHOUT ever calling the per-window Draw we hook. An earlier
	// v2.42.2 invalidated only the ROOT, which evidently does not reach the
	// leaves' own draw path.
	const int kBmpKickMax = 64;
	cIGZWin* gBmpKick[kBmpKickMax] = {};
	int gBmpKickN = 0;
	bool gBmpKickSatLogged = false;

	struct BmpWalkCtx
	{
		int depth;
		int* installed;

		static bool Callback(cIGZWin* /*parent*/, uint32_t /*childID*/,
			void* child, void* pContext)
		{
			BmpWalkCtx* ctx = static_cast<BmpWalkCtx*>(pContext);
			cIGZWin* win = static_cast<cIGZWin*>(child);
			if (!win) return true;
			if (HookBmpInstance(win))
			{
				(*ctx->installed)++;
				if (gBmpKickN < kBmpKickMax) { gBmpKick[gBmpKickN++] = win; }
				else if (!gBmpKickSatLogged)
				{
					// NO SILENT CAPS: past 64 the repaint kick is incomplete
					// for this pass, which would read as "the fix stopped
					// working" with nothing in the log to say so.
					gBmpKickSatLogged = true;
					Logger::Get().WriteLine(LogLevel::Info,
						"UiSpike: BMPX kick list saturated at %d - repaint "
						"kick is INCOMPLETE for this pass.", kBmpKickMax);
				}
			}
			if (ctx->depth < 8)
			{
				BmpWalkCtx sub = { ctx->depth + 1, ctx->installed };
				win->EnumChildren(GZIID_cIGZWin, BmpWalkCtx::Callback, &sub);
			}
			return true;
		}
	};

	// BMPRECT (v2.25.10): double the LIVE imagerect of GZWinBMP children.
	// For the code-built dialogs (kCityDialogIds) the game BYPASSES our
	// staged .UI, so it renders the ORIGINAL script's 1x imagerect against
	// art our dat serves at 2x - a 1x source rect over a 2x bitmap 9-slices
	// the frame into stripes (the Save box "tearing", measured: body BMP
	// {1abe787d,144161ee} rect=(22,35,180,180) edge=yes in I-ca8cbf0f).
	// Field map from the 0x9BC325 draw disasm: flag holder at [this+0xd8]
	// (vt[10](bit)), imagerect at [this+0xe8..0xf4] when flag 0x10 is set.
	// Callers run this ONLY on a FRESH dialog instance (one-shot), so value
	// re-doubling cannot occur.
	struct BmpRectCtx { float f; int* fixed_; int depth; };
	struct BmpRectWalk
	{
		static void Fix(cIGZWin* w, BmpRectCtx* ctx)
		{
			__try
			{
				void** vt = *reinterpret_cast<void***>(w);
				if (vt != kBmpClassVt) { return; }
				char* holder = reinterpret_cast<char*>(w) + 0xd8;
				void** hvt = *reinterpret_cast<void***>(holder);
				if (!hvt || !hvt[10]) { return; }
				if (!reinterpret_cast<BmpFlagTestFn>(hvt[10])(holder, 0x10))
				{
					return;   // no imagerect - the frame self-adapts
				}
				int32_t* r = reinterpret_cast<int32_t*>(
					reinterpret_cast<char*>(w) + 0xe8);
				// #176 belt (review finding 1): a crop that already EQUALS the
				// window's current area is window-following - it is correct as
				// it stands (either the game's own SetImage wrote it, or the
				// RELATCH guard did), and multiplying it would double-scale.
				// The 1x crops this pass exists for cannot match: ScaleSubtree
				// has already enlarged the window by the time this walk runs.
				if (r[0] == 0 && r[1] == 0
					&& r[2] == w->GetW() && r[3] == w->GetH())
				{
					return;
				}
				if (r[2] > r[0] && r[3] > r[1]
					&& r[0] >= 0 && r[1] >= 0 && r[2] <= 2000 && r[3] <= 2000)
				{
					for (int k = 0; k < 4; k++)
					{
						r[k] = ScaleRound(r[k], ctx->f);
					}
					(*ctx->fixed_)++;
				}
			}
			__except (EXCEPTION_EXECUTE_HANDLER) {}
		}
		static bool Callback(cIGZWin* /*parent*/, uint32_t /*childID*/,
			void* child, void* pContext)
		{
			BmpRectCtx* ctx = static_cast<BmpRectCtx*>(pContext);
			cIGZWin* win = static_cast<cIGZWin*>(child);
			if (!win) { return true; }
			Fix(win, ctx);
			if (ctx->depth < 3)
			{
				BmpRectCtx sub = { ctx->f, ctx->fixed_, ctx->depth + 1 };
				win->EnumChildren(GZIID_cIGZWin, BmpRectWalk::Callback, &sub);
			}
			return true;
		}
	};

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

	// v2.42.3 (#47): ONE summary line per panel open, emitted when the NEXT
	// open of any tracked root starts (and at Disarm). Counts only, so it can
	// never saturate - the whole point is that a FAILING open must leave a
	// line. THE DISCRIMINATOR, decided in advance:
	//   scaled=0 clamped=0  -> the paint never reached our hooked Draw at all
	//                          (engine composited the cell from its private
	//                          buffer) => pbuff/composite mechanism; more
	//                          repaints will NOT cure it, born-2x data will
	//                          (law 8, the v2.25.14 gauge precedent).
	//   scaled=N (N>0)      -> our draw WAS applied for that open; if it still
	//                          looked small, the composite ignored a correct
	//                          draw => a different mechanism, re-measure.
	void FlushBmpOpenCensus()
	{
		if (!gBmpOpenId) { return; }
		Logger::Get().WriteLine(LogLevel::Debug,
			"UiSpike: BMPX open #%d of 0x%08X census: scaled=%d clamped=%d",
			gBmpOpenSeq, gBmpOpenId, gBmpOpenScaled, gBmpOpenClamped);
		gBmpOpenId = 0;
		gBmpOpenScaled = 0;
		gBmpOpenClamped = 0;
	}

	// Hook every GZWinBMP under each listed root found below pSearchRoot.
	// Scoped by id on purpose (id collisions across roots broke v2.22.3);
	// the self-limiting draw math is what makes a broad within-root walk safe.
	void HookRuntimeBmpsUnder(cIGZWin* pSearchRoot, const uint32_t* ids,
		int nIds, float f, const char* tag)
	{
		if (!pSearchRoot || f <= 1.01f) return;
		gBmpScale = f;
		for (int k = 0; k < nIds; k++)
		{
			cIGZWin* root = pSearchRoot->GetChildWindowFromIDRecursive(ids[k]);
			if (!root) continue;
			// v2.42.1: log when the resolved root pointer CHANGES between
			// passes - on a reopen this answers whether the id resolved to a
			// NEW window (open instance) or the SAME one (hidden template).
			{
				BmpxRootTrack* slot = nullptr;
				for (int t = 0; t < gBmpxRootTrackN; t++)
					if (gBmpxRootTrack[t].id == ids[k]) { slot = &gBmpxRootTrack[t]; break; }
				if (!slot && gBmpxRootTrackN < 32)
					slot = &gBmpxRootTrack[gBmpxRootTrackN++];
				if (slot)
				{
					if (slot->ptr && slot->ptr != root)
						Logger::Get().WriteLine(LogLevel::Debug,
							"UiSpike: BMPX root 0x%08X resolved %p -> %p (%s)",
							ids[k], slot->ptr, root, tag);
					// v2.42.3: OPEN = pointer changed OR hidden -> visible.
					// The second half is the one that matters: the My Sims
					// STRIP is resident and hooks ONCE at city load, so a
					// reopen changes NEITHER the pointer NOR the hook count -
					// which is why v2.42.2 was blind (and inert) on exactly
					// the repro the user reports.
					const bool visNow = root->IsVisible();
					const bool opened = (slot->ptr && slot->ptr != root)
						|| (visNow && !slot->vis);
					if (opened)
					{
						FlushBmpOpenCensus();      // report the PREVIOUS open
						gBmpOpenId = ids[k];
						gBmpOpenSeq = ++slot->seq;
						gBmpOpenScaled = 0;
						gBmpOpenClamped = 0;
						gBmpDrawLog = 0;           // fresh budget per OPEN
						gBmpDrawLogSatLogged = false;
						Logger::Get().WriteLine(LogLevel::Debug,
							"UiSpike: BMPX open #%d of 0x%08X ptr%p (%s)",
							gBmpOpenSeq, ids[k], root, tag);
					}
					slot->id = ids[k];
					slot->ptr = root;
					slot->vis = visNow;
				}
			}
			int installed = 0;
			gBmpKickN = 0;                 // v2.42.4: per-root kick list
			gBmpKickSatLogged = false;
			BmpWalkCtx ctx = { 0, &installed };
			// v2.36.7: COUNT THE ROOT ITSELF. It was hooked here all along but
			// never counted, so an id that IS the GZWinBMP (no BMP children) -
			// e.g. the U-Drive-It marker 0x48E945B4 - hooked silently and
			// produced no BMPX line at all. The fix worked; the log denied it.
			// Third instrument of this shape in one session (see METHOD.md
			// "YOUR OWN INSTRUMENTS CAN LIE"): report what you DID, not what a
			// sub-walk happened to do.
			if (HookBmpInstance(root)) { installed++; }
			root->EnumChildren(GZIID_cIGZWin, BmpWalkCtx::Callback, &ctx);
			if (installed > 0)
			{
				gBmpDrawLog = 0;
				gBmpDrawLogSatLogged = false;
				Logger::Get().WriteLine(LogLevel::Info,
					"UiSpike: BMPX %d instance(s) hooked under 0x%08X (%s, x%.2f)",
					installed, ids[k], tag, f);
				// v2.42.4: kick EACH freshly hooked leaf, then the root.
				// One invalidate per instance, once per open - bounded, and
				// NOT the banned ghost-heal (which was N blind sweeps over
				// everything, every pass). Acceptance: the next open's census
				// must read scaled>0. If it still reads scaled=0, the engine
				// is not reaching Draw even when told the window is dirty -
				// STOP and disassemble the blit path; do not add sweeps.
				for (int i = 0; i < gBmpKickN; i++)
				{
					if (gBmpKick[i]) { gBmpKick[i]->InvalidateSelfAndParents(); }
				}
				// v2.42.2: force a repaint through the freshly hooked path.
				// Measured: on repeated "add a Sim" the game skips the grid
				// cells' Draw (pbuff already populated at 1x from a prior
				// unhooked paint or cache blit). One invalidate per new-hook
				// pass makes the engine re-walk the subtree through our blit
				// scaler. NOT a blind sweep - fires only when installed > 0.
				root->InvalidateSelfAndParents();
			}
		}
	}
}

// One idempotent whitelist pass over the visible panels parented to pRoot.
// Safe to run any number of times: Classify() makes re-scaling a no-op.
// Returns the number of windows newly scaled this pass.
// ===== THE DOCK MINIMAP SURFACE RECREATE (extracted v2.41.19) ==========
// Verbatim extraction of the sweep's MINIMAP block - the v2.21.1 crash
// site. NOTHING inside was changed; only the indentation moved. TWO callers:
//  1. ScalePanelsUnder (the sweep), exactly as before.
//  2. EarlyDockTick mode 2, immediately after the early dock scale.
//
// WHY THE SECOND CALLER IS MANDATORY, not optional: v2.41.15 crashed
// precisely because an early dock scale ran WITHOUT this. Scaling the dock
// self-updates the minimap's blitSize [+0xE4] to 128 (the class SetArea
// override) while the one-shot display surface stays 64 - and the next
// bake is then a 128-sized render into a 64 surface, the documented
// v2.21.0 heap overrun ("silent native death"), which matches that crash
// landing AFTER everything appeared to complete. SCALE AND RECREATE ARE
// ONE ACTION - the two-halves law: they ship together or not at all.
// All gates (pointer latch, GetW()>64, retry budget, tree-link check) are
// INSIDE, so both callers are idempotent against each other by the latch.
// v2.72.1 (#109, the FAMILY): the #109 invariant belongs to the CLASS, not to
// one instance. All three cSC4WinMiniMap windows - the Data Views map, the HUD
// dock minimap and the U-Drive-It dashboard twin - are sized `design * f` while
// their surface is created at `blitSize`, which can only ever be
// `terrainDim << k`. Those agree only when f is a power of two, so at 1.5x and
// 3x EVERY instance carries the mismatch, not just the one that happened to
// crash. MEASURED at 3x, before and after the v2.72.0 DVMAP fix, unchanged:
//   dock minimap   win 192x192  blitSize=128     <- still mismatched
//   Data Views map win 512x512  blitSize=512     <- fixed by v2.72.0
// and at 2x the dock reads 128/128, matched, exactly like the DV map.
//
// Fixing one instance and leaving its siblings is how a family rots (law: a
// coupled pair ships together or not at all). This is the shared cure.
//
// Returns the snapped edge, or 0 if nothing was needed / possible.
int UiSpike::SnapMiniMapToBake(cIGZWin* pMap, const char* who)
{
	if (!pMap) { return 0; }
	int32_t terrainDim = 0;
	__try
	{
		void* terrain = *reinterpret_cast<void**>(0x00B43CEC);
		if (terrain)
		{
			void** tvt = *reinterpret_cast<void***>(terrain);
			typedef int (__thiscall* GetDimFn)(void*);
			terrainDim = reinterpret_cast<GetDimFn>(tvt[0x174 / 4])(terrain);
		}
	}
	__except (EXCEPTION_EXECUTE_HANDLER) { terrainDim = 0; }
	if (terrainDim <= 0) { return 0; }

	// The bake ceiling: the game's own dispatch reaches zoom -2 (x4); the #121
	// patch extends it to zoom -3 (x8). Never exceed it - a size the bake
	// cannot reach is the black map all over again.
	const int32_t ceiling = terrainDim * (CodePatches::MiniMapX8Active() ? 8 : 4);
	const int32_t curW = pMap->GetW();
	const int32_t curH = pMap->GetH();
	const int32_t want = curW < ceiling ? curW : ceiling;

	// ⛔ THE LEGAL SET IS terrainDim << k FOR ANY INTEGER k - MULTIPLES **AND
	// DIVISORS**. This search used to be a single ascending loop:
	//
	//     for (int32_t s = terrainDim; s <= want; s <<= 1) { snap = s; }
	//
	// which starts AT terrainDim and can only ever go up. When terrainDim is
	// LARGER than the slot the layout reserved, the loop body never executes,
	// `snap` stays 0, and the function returns having corrected NOTHING -
	// window at `design*f`, surface still native, i.e. exactly the #109
	// window-vs-surface mismatch this helper exists to prevent, arrived at
	// silently instead of by crashing.
	//
	// ⚠ THIS IS 1.5x's PROBLEM AND IT IS STRUCTURAL. The dock recess is 64px
	// of design, so the slot is 64*f:
	//     f=2.0 -> 128 : terrainDim 64 and 128 both fit; 256 divides to 128.
	//     f=3.0 -> 192 : 64 -> 128 fits.
	//     f=1.5 ->  96 : 64 fits (snaps DOWN to 64, no growth possible since
	//                    the next multiple 128 > 96 - that is just what
	//                    1 < 1.5 < 2 means against a power-of-two law), but
	//                    terrainDim 128 / 256 (medium / large city) NEVER
	//                    ENTERED THE LOOP AT ALL.
	// So on any city bigger than small, 1.5x left the dock minimap wholly
	// uncorrected. Reported 2026-08-06 as a corrupt dashboard map.
	//
	// ⚠ SAFETY PROPERTY, and the reason this is shippable without re-verifying
	// the confirmed tiers: THE NEW BRANCH ONLY RUNS WHERE THE OLD CODE DID
	// NOTHING. If terrainDim <= want the ascending loop is byte-for-byte the
	// old one; the descending branch is reachable only when the old loop would
	// have returned 0. It cannot regress a case that previously worked.
	int32_t snap = 0;
	if (terrainDim <= want)
	{
		for (int32_t s = terrainDim; s <= want; s <<= 1) { snap = s; }
	}
	else
	{
		// Halve until it fits. kMinSnap keeps a degenerate slot from asking
		// for a 2px map - below that, decline and leave the window alone
		// rather than seat something nobody can read.
		const int32_t kMinSnap = 32;
		for (int32_t s = terrainDim; s >= kMinSnap; s >>= 1)
		{
			if (s <= want) { snap = s; break; }
		}
		if (snap <= 0)
		{
			// LogLevel has no Warning tier (Error/Info/Debug/Trace) - this is a
			// real "the map will not match its surface" condition, so Error.
			Logger::Get().WriteLine(LogLevel::Error,
				"UiSpike: %s NO LEGAL BLIT - terrainDim=%ld, slot=%ldx%ld, "
				"want=%ld; smallest legal divisor is still above the slot. "
				"Window left alone (surface may not match).",
				who, (long)terrainDim, (long)curW, (long)curH, (long)want);
			return 0;
		}
	}
	// Law 54: say which branch ran and what it chose, every time. A snap that
	// silently picks the same value it always did is indistinguishable in a log
	// from one that never ran.
	Logger::Get().WriteLine(LogLevel::Info,
		"UiSpike: %s snap terrainDim=%ld slot=%ldx%ld ceiling=%ld -> %ld (%s)",
		who, (long)terrainDim, (long)curW, (long)curH, (long)ceiling, (long)snap,
		terrainDim <= want ? "multiple" : "DIVISOR");

	// ⚠ LEAVING THE WINDOW OVERSIZED IS NOT AN OPTION. Tried 2026-08-06: skip
	// the resize when only a divisor fits, on the theory that slot 88's stretch
	// blit would fill the recess from the smaller map. It does not - the log's
	// own buffer probe says so in as many words:
	//     MMBUF win=96x96 blit=64 ... <<< A BUFFER DOES NOT MATCH THE WINDOW
	// and the 64px surface simply blits at the window's TOP-LEFT, leaving the
	// map jammed into the corner of the recess (user screenshot, same day).
	// The stretch is disarmed anyway - kMmStretchEnabled is false, refuted as a
	// stride tear. So the window must be resized to the map and CENTRED.
	if (snap <= 0 || curW == snap) { return 0; }

	uint8_t* raw = reinterpret_cast<uint8_t*>(pMap);
	const int32_t blitBefore = *reinterpret_cast<int32_t*>(raw + 0xe4);
	// ⛔ GZWinMoveTo IS A RELATIVE MOVE. MEASURED 2026-08-06, THE HARD WAY.
	//
	// The name and the header (`GZWinMoveTo(int32_t x, int32_t y)`,
	// cIGZWin.h:137) both read like an absolute placement, so this was
	// "corrected" from the original delta form to seat+delta. MEASURED RESULT,
	// from this function's own new log line plus the user's screenshot:
	//     seat (27,108) 96x96 -> asked for (43,124)
	// (27,108) is exactly the recess origin (18*1.5=27), so (43,124) would have
	// been dead centre had the call been absolute. The map instead rendered
	// BELOW the recess, over the date field - i.e. it moved BY (43,124) from
	// (27,108). The original delta form was right all along.
	//
	// ⚠ THE LESSON, and it is the expensive one: a header signature is not a
	// semantic. Two readings were possible, the shipped code already encoded
	// the correct one, and it was changed on the strength of the NAME. The
	// after-move read-back below exists so this is never ambiguous again -
	// GetL()/GetT() after the call is the only thing that settles it.
	const int32_t seatL = pMap->GetL();
	const int32_t seatT = pMap->GetT();
	const int32_t dx = (curW - snap) / 2;
	const int32_t dy = (curH - snap) / 2;
	pMap->SetW(snap);
	pMap->SetH(snap);
	pMap->GZWinMoveTo(dx, dy);        // RELATIVE - do not "fix" this to seat+d
	Logger::Get().WriteLine(LogLevel::Info,
		"UiSpike: %s centred: seat (%ld,%ld) %ldx%ld, moved by (%ld,%ld) -> "
		"now at (%ld,%ld) %ldx%ld. EXPECTED (%ld,%ld); if 'now' equals the "
		"move delta instead, GZWinMoveTo changed semantics - re-measure.",
		who, (long)seatL, (long)seatT, (long)curW, (long)curH, (long)dx, (long)dy,
		(long)pMap->GetL(), (long)pMap->GetT(), (long)snap, (long)snap,
		(long)(seatL + dx), (long)(seatT + dy));
	// blitSize [+0xE4] self-updates ONLY through the class's SetArea override;
	// SetW/SetH bypass it. Leaving it stale is the v2.69.9 stride tear (two
	// copies side by side + interlaced garbage). Write it directly.
	*reinterpret_cast<int32_t*>(raw + 0xe4) = snap;
	__try
	{
		typedef void (__thiscall* RecomputeFn)(void*);
		reinterpret_cast<RecomputeFn>(0x007A7840)(pMap);

		// ⛔ MARK THE WHOLE DIRTY MASK. THE GAME'S OWN "MARK ALL" ONLY MARKS A
		// 64-CELL CITY, AND WE HAND IT A BRAND-NEW RASTER.
		//
		// MEASURED 2026-08-06 by dumping the buffer (MMGRID), after an hour of
		// arguing about it from a five-pixel sample:
		//     raster 64x64, reddish bbox = (0,28)..(60,60)
		//     rows 0-3 of 8 tile rows  = real city
		//     rows 4-7                 = never written
		// 64px raster / 8px tiles = 8 tile rows; the boundary is exactly at
		// tile row 4.
		//
		// The mask at [+0x120] is 16 dwords - one per tile ROW, one bit per
		// tile column (the game's own incremental marker at 0x7A71F0 clamps
		// its index to 15 and writes [ebp+ecx*4+0x120], so the field is
		// +0x120..+0x15F). But EVERY "mark all" the game does passes 0x10:
		//     0x7A78D7  push 0x10   ; inside the recompute we just called
		//     0x7A66C3  push 0x10
		//     0x7A8602  push 0x10   ; the bake's own tail clear
		// 0x10 bytes = 4 dwords = 4 tile rows = a 64-CELL city. On 128 cells
		// it marks half the mask, on 256 a quarter.
		//
		// Stock survives this because it allocates the raster ONCE at city
		// init, while terrain generation is setting every bit through
		// 0x7A71F0, and nothing ever clears rows >= 4. WE force a second
		// free+malloc mid-session (0x7A7570 inside the recompute above), so
		// our fresh raster has rows >= 4 unmarked AND uninitialised - and the
		// bake skips unmarked tiles (0x7A8165 test -> je 0x7A85B4). What shows
		// through is old heap, which is the red block.
		//
		// ⚠ MARKING MORE THAN EXISTS IS SAFE: the bake iterates tilesX/tilesY
		// derived from the TERRAIN dims (0x7A8010-0x7A8032), so surplus mask
		// bits are never consulted. This is a no-op at any size the game
		// already covered, which is why it cannot regress 2x or 3x.
		memset(raw + 0x120, 0xFF, 0x40);   // 16 dwords = all 16 tile rows

		DriveMiniMapBake(pMap, who);
		Logger::Get().WriteLine(LogLevel::Info,
			"UiSpike: %s dirty mask widened to all 16 tile rows before the "
			"bake (the game's own mark-all writes 4 rows = a 64-cell city; "
			"this raster is %ld px for a %ld-cell terrain).",
			who, (long)snap, (long)terrainDim);
	}
	__except (EXCEPTION_EXECUTE_HANDLER)
	{
		Logger::Get().WriteLine(LogLevel::Error,
			"UiSpike: %s snap recompute FAULTED (report this line).", who);
	}
	// AlreadyScaled at the snapped size: the sweep must never re-double this
	// window behind the policy - that is the tug-of-war shape.
	ScaleRecord rec = { pMap->GetID(), snap, snap, snap, snap, 0, false };
	StoreScaleRecord(pMap, rec);
	pMap->InvalidateSelf();
	// v2.72.2: REPAINT WHAT WE VACATED. Shrinking the window from `curW` to
	// `snap` hands a ring of (curW-snap) px back to the parent, and NOTHING
	// repaints it - InvalidateSelf only dirties the map's NEW, smaller rect,
	// so the parent's last paint of the old, larger area stays on screen.
	// That is the "corrupted image still behind it" the user reported: not
	// corruption at all, just a stale region nobody owns any more.
	//
	// Our C++ InvalidateSelf() lands on slot 91 (0x0099BECC) and only sets
	// THIS window's dirty byte. The game's own idiom for "and repaint my
	// ancestors" is vt+0x170 (sub_99BED1) = SetDirty AND propagate - the
	// same call the #57 green-box proof showed was the ONLY thing that
	// actually moves pixels (cIGZWin+0x70 is the repaint gate). Apply it to
	// the PARENT, because the vacated ring is the parent's pixels now.
	if (cIGZWin* pParent = pMap->GetParentWin())
	{
		if (pParent != pMap)
		{
			__try
			{
				void** pvt = *reinterpret_cast<void***>(pParent);
				if (pvt && pvt[0x170 / 4])
				{
					typedef void (__thiscall* DirtyFn)(void*);
					reinterpret_cast<DirtyFn>(pvt[0x170 / 4])(pParent);
				}
			}
			__except (EXCEPTION_EXECUTE_HANDLER)
			{
				Logger::Get().WriteLine(LogLevel::Error,
					"UiSpike: %s parent re-dirty FAULTED (stale ring may "
					"remain around the map; report this line).", who);
			}
		}
	}
	// v2.72.3's ancestor private-paint-buffer probe lived here. DELETED in
	// v2.73.0: it was an INVALID INSTRUMENT. All four ancestors reported the
	// SAME pointer (030D8C14) with cachedW=0, which is impossible for four
	// distinct windows - `[win+0x6c]` is not the per-window buffer field on a
	// cIGZWin (that offset was lifted from the gauge draw path, where `self`
	// is a different object). Its plausibility guard is the only reason it
	// never wrote into unknown memory. Deleted rather than left in place: a
	// broken instrument that prints confident lines is worse than none, and
	// the pbuff hypothesis is MOOT anyway - the recess geometry (dock art
	// recess = 64*f = 192 against a 128 image) explains the symptom without
	// it. See #126.
	Logger::Get().WriteLine(LogLevel::Info,
		"UiSpike: %s window SNAPPED %dx%d -> %d (terrain %d, largest exact "
		"power-of-two multiple within the x%d bake ceiling; window==surface "
		"now, which is the #109 invariant; blitSize %d -> %d, zoom now %d).",
		who, curW, curH, snap, terrainDim,
		CodePatches::MiniMapX8Active() ? 8 : 4, blitBefore,
		*reinterpret_cast<int32_t*>(raw + 0xe4),
		*reinterpret_cast<int32_t*>(raw + 0x104));
	return snap;
}

// ===== #126 (v2.73.0): FILL THE DOCK MINIMAP'S RECESS AT NON-POWER-OF-TWO TIERS
//
// THE DEFECT, MEASURED. We scale the dock artwork by f, so its minimap RECESS is
// 64*f = 192 at 3x. The map IMAGE can only ever be a power-of-two multiple of the
// city tile, i.e. 128. The uncovered 64px band is the "garbage" the user sees -
// the recess is a hole in the dock bitmap, so it shows whatever is behind it.
//   tier 2.00: recess 128, image 128 -> exact, clean (why 2x never showed this)
//   tier 3.00: recess 192, image 128 -> 64px uncovered
// It is NOT our snap: the band was identical before v2.72.1 (win 192/blit 128)
// and after (win 128/blit 128). And it is NOT the map data - MMBUF measured the
// raster at 128x128 with five distinct terrain colours.
//
// THE LEVER. The draw override's live branch (0x007A7A81) builds its dest rect as
// {[esi+0x24], [esi+0x28], +blitSize, +blitSize} and hands the surface's FULL
// buffer area as the SOURCE - it is ALREADY A STRETCH BLIT, it just always asks
// for blitSize squared. So we do not need to blit anything ourselves: present a
// larger blitSize for the duration of the original call and the game's own
// compositor scales 128 -> 192. Soft, which the user has accepted.
//
// WHY THIS IS SAFE HERE AND NOT ON THE DATA VIEWS MAP. The #109 faulting chain
// (0x007A2F60) resolves its target with `push 0xCA318385 / push 0x4203` - window
// id 0x4203, the Data Views map, EXCLUSIVELY. The dock minimap is 0x0BC3B559 and
// never enters that chain; it sat at window 192 / blit 128 for this entire
// session without ever crashing.
namespace
{
	void** const kMmClassVt = reinterpret_cast<void**>(0x00AB83B8);
	constexpr uintptr_t kMmDrawVA = 0x007A79B0;   // cSC4WinMiniMap draw override
	constexpr int kMmDrawSlot = 0x160 / 4;        // 88 - same slot as GZWinBMP's
	constexpr int kMmVtSlots = 151;               // same cIGZWin layout

	typedef uintptr_t(__thiscall* MmDrawFn)(void* self);

	MmDrawFn gMmOrigDraw = nullptr;
	void*    gMmVtCopy[kMmVtSlots] = {};   // ONE shared patched vtable
	bool     gMmVtReady = false;

	uintptr_t __fastcall MmDrawThunk(void* self, void* /*edx*/)
	{
		int32_t* pBlit = nullptr;
		int32_t  savedBlit = 0;
		// v2.73.2: COUNT ENTRIES SEPARATELY FROM STRETCHES. v2.73.1 logged only
		// the stretch count, once, from the ScaleAll pass - which runs ONCE per
		// city and fires immediately after the hook is installed, i.e. before
		// any draw could possibly have happened. "stretched=0" from that sample
		// could not have shown a later fire, so it proved nothing (law: a null
		// is not evidence until the probe is shown able to see the thing).
		// Entries vs stretches separates the three possibilities cleanly:
		//   entries==0            -> the thunk is never CALLED (vtable replaced,
		//                            or this window does not draw via slot 88)
		//   entries>0 stretch==0  -> called, but the condition declined
		//   both >0               -> working
		gMmEntries++;
		__try
		{
			uint8_t* raw = reinterpret_cast<uint8_t*>(self);
			// GATE: the override early-outs into the RECOMPUTE when the raster
			// is absent (0x7A79BB / 0x7A79C6 -> call 0x7A7840). That path
			// REALLOCS the raster FROM blitSize, so a faked value there would
			// resize the real buffer instead of merely the blit. Only fake it
			// once a raster already exists.
			if (*reinterpret_cast<int32_t*>(raw + 0x114) != 0)
			{
				cIGZWin* w = static_cast<cIGZWin*>(self);
				const int32_t winW = w->GetW();
				const int32_t winH = w->GetH();
				int32_t* blit = reinterpret_cast<int32_t*>(raw + 0xe4);
				const int32_t cur = *blit;
				// Square windows only (the blit is blitSize x blitSize), and
				// only ever ENLARGE. At 2x the window already equals blitSize,
				// so this is a no-op and 2x stays bit-identical.
				// v2.73.3: REFUTED ON SCREEN. Faking blitSize does NOT make the
				// game scale the image - it makes the blit walk 192-wide rows
				// out of a 128-wide buffer, i.e. the v2.69.9 STRIDE TEAR
				// ("two copies side by side + interlaced garbage"). The
				// FIRST FIRE line proved the thunk ran and did exactly what it
				// was told; the premise that the override's live branch is
				// "already a stretch blit" was simply wrong. The source extent
				// is not independent of blitSize.
				// Disarmed via kMmStretchEnabled rather than deleted, because
				// the ENTRY counter is still a useful instrument and the
				// tombstone must stay attached to the evidence.
				const bool kMmStretchEnabled = false;
				if (kMmStretchEnabled
					&& winW == winH && cur > 0 && winW > cur && winW <= 4096)
				{
					savedBlit = cur;
					*blit = winW;
					pBlit = blit;
					gMmStretches++;
					if (!gMmFirstFireLogged)
					{
						gMmFirstFireLogged = true;
						Logger::Get().WriteLine(LogLevel::Info,
							"UiSpike: MINIMAP stretch FIRST FIRE - win %dx%d, "
							"blitSize %d -> %d for this draw. The game's own "
							"stretch blit is now filling the recess.",
							winW, winH, cur, winW);
					}
				}
			}
		}
		__except (EXCEPTION_EXECUTE_HANDLER) { pBlit = nullptr; }

		uintptr_t r = 0;
		__try { r = gMmOrigDraw ? gMmOrigDraw(self) : 0; }
		__except (EXCEPTION_EXECUTE_HANDLER) { r = 0; }

		// RESTORE ON EVERY PATH, including the fault path above. The message
		// handler's transfer (0x007A86DC) also reads +0xE4 as its COPY EXTENT,
		// paired with the destination buffer's own pitch and base - a leaked
		// 192 there would over-copy. This is the one thing most likely to bite,
		// so it is unconditional.
		if (pBlit)
		{
			__try { *pBlit = savedBlit; }
			__except (EXCEPTION_EXECUTE_HANDLER) {}
		}
		return r;
	}

	// Per-instance vtable COPY - the class vtable itself is never written
	// (same discipline as the GZWinBMP hook above).
	bool HookMiniMapDraw(cIGZWin* win, const char* who)
	{
		if (!win) { return false; }
		bool ok = false;
		__try
		{
			void** vt = *reinterpret_cast<void***>(win);
			if (!vt) { return false; }
			if (vt == &gMmVtCopy[0]) { return true; }   // already ours
			// Verify-before-write: the slot must hold the stock override, and
			// the class vtable must be the one we measured.
			if (vt != kMmClassVt) { return false; }
			if (vt[kMmDrawSlot] != reinterpret_cast<void*>(kMmDrawVA))
			{
				return false;
			}
			if (!gMmVtReady)
			{
				for (int i = 0; i < kMmVtSlots; i++) { gMmVtCopy[i] = vt[i]; }
				gMmOrigDraw = reinterpret_cast<MmDrawFn>(vt[kMmDrawSlot]);
				gMmVtCopy[kMmDrawSlot] = reinterpret_cast<void*>(&MmDrawThunk);
				gMmVtReady = true;
			}
			*reinterpret_cast<void***>(win) =
				reinterpret_cast<void**>(&gMmVtCopy[0]);
			gMmHooked++;
			ok = true;
		}
		__except (EXCEPTION_EXECUTE_HANDLER) { return false; }
		Logger::Get().WriteLine(LogLevel::Info,
			"UiSpike: %s draw hook installed (slot %d, vt copy) - the game's own "
			"stretch blit will now fill the window from a smaller image.", who,
			kMmDrawSlot);
		return ok;
	}
}

// #127 (v2.76.0): drive kPanelDock. Runs from BOTH the full city sweep and the
// incremental pass, because a panel the user OPENS (Graphs, Budget) is never
// present during the load-time sweep - v2.75.1 put the pin in ScaleAll only and
// it therefore never fired even once (the log had no GRAPHPIN line at all).
// Idempotent by construction: once the child sits at its target the delta is 0
// and nothing is written, so running it at 16ms costs a compare per entry.
void UiSpike::ApplyPanelDocks(cIGZWin* pRoot, float f, bool fromShow)
{
	// #137: the guard here was `f < 2.5f` with the note "2x is user-confirmed;
	// never touch it". That protected a 2x layout the user has since reported
	// as WRONG in the same way as 3x - the band overlapping the title and the
	// expansion arrow - and because the dock never fired at 2x there was
	// nothing correcting it there at all. The dock now runs at every scaled
	// tier. It stays off at f<1.4 because the mod is inert below its first
	// tier and the design geometry is already correct at 1x by definition.
	if (!pRoot || f < 1.4f) { return; }
	for (int i = 0; i < kPanelDockCount; i++)
	{
		const PanelDock& d = kPanelDock[i];
		__try
		{
			cIGZWin* pAnchor = pRoot->GetChildWindowFromIDRecursive(d.anchorId);
			cIGZWin* pChild  = pRoot->GetChildWindowFromIDRecursive(d.childId);
			if (!pAnchor || !pChild) { continue; }
			// #137c: THE VISIBILITY TEST IS WHY THE PANEL JUMPED FOR ONE FRAME.
			// The show path is a detour on cGZWin::SetFlag that fires on the
			// 0->1 transition of the visible bit, and it deliberately runs
			// BEFORE the bit is set ("if ((bits & 1u) == 0u)"). So when #127's
			// dock-at-show called in here, IsVisible() was still FALSE for the
			// very window being shown and this line bailed - every time. The
			// dock could therefore never seat the panel at birth; the tick had
			// to correct it after the first paint, which is the flash.
			// Called from the show path we skip the flag and gate on GEOMETRY
			// instead, which is the "scale while HIDDEN, gate the move on real
			// state not on the visible flag" rule from the flyout work.
			if (!fromShow && (!pAnchor->IsVisible() || !pChild->IsVisible()))
			{
				continue;
			}
			// Geometry gate, applied on BOTH paths: a window with no size has
			// not been laid out yet and its rect would be a guess. This is the
			// check that keeps the hidden path honest now that the flag is not
			// doing it - without it, docking early would be docking blind.
			if (pAnchor->GetW() <= 0 || pAnchor->GetH() <= 0
				|| pChild->GetW() <= 0 || pChild->GetH() <= 0)
			{
				continue;
			}
			// #137: BOTTOM-REFERENCED. offX/offY are 1x DESIGN units read off
			// the .UI (dLeft, and band.bottom -> parent.bottom), so they scale
			// by f directly rather than by f/2. The vertical target is measured
			// UP from the anchor's bottom edge, which is what makes the band
			// dock like Data Views instead of drifting into the title.
			// Child height is read live: the band's own height is already
			// correct (503x107 -> 1509x321 at f=3, verified in the log), so
			// using it here keeps the bottom flush whatever the row count.
			const int32_t anchorBottom = pAnchor->GetT() + pAnchor->GetH();
			const int32_t tx = pAnchor->GetL() + RoundHalfUp(d.offX * f);
			const int32_t ty = anchorBottom - pChild->GetH()
				- RoundHalfUp(d.offY * f);
			const int32_t cx = pChild->GetL();
			const int32_t cy = pChild->GetT();
			if (cx == tx && cy == ty) { continue; }   // already seated
			pChild->GZWinMoveTo(tx - cx, ty - cy);    // relative, like all moves
			if (tx != gGraphBandLastX || ty != gGraphBandLastY)
			{
				gGraphBandLastX = tx;
				gGraphBandLastY = ty;
				Logger::Get().WriteLine(LogLevel::Info,
					"UiSpike: PANELDOCK %s 0x%08X (%d,%d) -> (%d,%d) under "
					"0x%08X at (%d,%d) [f=%.2f].",
					d.what, d.childId, cx, cy, tx, ty, d.anchorId,
					pAnchor->GetL(), pAnchor->GetT(), f);
			}
		}
		__except (EXCEPTION_EXECUTE_HANDLER)
		{
			Logger::Get().WriteLine(LogLevel::Error,
				"UiSpike: PANELDOCK %s FAULTED - left as the sweep placed it.",
				d.what);
		}
	}
}

void UiSpike::TryRecreateMinimapSurface(cIGZWin* pDock)
{
	if (!pDock) { return; }
	cIGZWin* pMM = pDock
		? pDock->GetChildWindowFromIDRecursive(0x0BC3B559) : nullptr;
	// ⚠ WHAT THIS CHECK CAN AND CANNOT PROVE (corrected v2.41.7 by the
	// SDK-law audit, against my own v2.41.0 wording). pMM was produced by
	// pDock's OWN recursive search, so testing "is pMM under pDock" is
	// very nearly a tautology: it CANNOT catch the U-Drive-It twin,
	// because the search is already scoped and could never have returned
	// it. What it can still catch is the engine's tree links DISAGREEING -
	// the child list [win+0x44] and the parent pointer [win+0x48] are
	// separate fields - which is worth an assertion but is NOT the
	// "wrong twin" diagnosis the old message asserted.
	// The scoping is what protects the twins, here and in the UDMAP block
	// (which is symmetrically scoped under 0x4BCB938A). Do not read a
	// silent log here as "the twin check ran and passed".
	if (pMM && !IsDescendantOf(pMM, pDock))
	{
		Logger::Get().WriteLine(LogLevel::Info,
			"UiSpike: MINIMAP TREE-LINK MISMATCH - 0x0BC3B559 at %p was "
			"returned by the dock's own recursive search but its parent "
			"chain (immediate parent 0x%08X) does not reach the dock. "
			"Engine child/parent links disagree; surface untouched.",
			static_cast<void*>(pMM), ParentIdOf(pMM));
		pMM = nullptr;
	}
	// v2.73.0 (#126): the dock minimap is NO LONGER SNAPPED. v2.72.1 shrank its
	// window to the image size, which was correct-but-pointless: it never was on
	// the #109 crash path (that chain resolves id 0x4203 exclusively), and
	// shrinking the window did nothing about the real defect - the dock ART's
	// recess is 64*f = 192 while the image can only be 128, leaving a 64px band
	// of bare recess. Let the window keep its full scaled size and hook the draw
	// instead, so the game's own stretch blit fills it from the 128 image.
	// v2.73.3: the SNAP is back. The stretch was refuted on screen (see the
	// tombstone in MmDrawThunk), and a correct 128 map in a 192 recess beats a
	// torn 192 one. The remaining 32px ring of BAKED FAKE MAP in the dock
	// artwork is an ART defect and gets an ART fix - see #126.
	if (pMM && pMM->GetW() > 64) { SnapMiniMapToBake(pMM, "MINIMAP"); }
	if (pMM) { HookMiniMapDraw(pMM, "MINIMAP"); }
	// ⛔ THE `> 64` WAS A MAGIC LITERAL THAT EXCLUDED EXACTLY ONE TIER.
	//
	// This block is the v2.41.9 (#89) repair: capture the old picture, destroy
	// and recreate the display surface, CLEAR THE RASTER, restore. Its gate
	// asked "is this window bigger than native?", spelled as a bare 64.
	//
	// Which tiers reach it, after SnapMiniMapToBake above:
	//     2.0x  slot 128, snap is a no-op (curW == snap, returns early)
	//           -> we never realloc the raster, so there is nothing to repair
	//     3.0x  slot 192 -> snapped to 128 -> 128 > 64 -> REPAIR RUNS
	//     1.5x  slot  96 -> snapped to  64 ->  64 > 64 is FALSE -> SKIPPED
	// So 1.5x is the ONLY tier that reallocates the raster WITHOUT the repair,
	// and it is excluded by one pixel of a hard-coded literal. That is the
	// whole reason "it works at 2x and 3x": 2x never needed it and 3x got it by
	// accident of a threshold.
	//
	// MEASURED 2026-08-06 that the block does not run at 1.5x: `MINIMAP 2X` is
	// LogLevel::Info and appears ZERO times in a log where Debug-level MMBUF
	// lines from the same function do appear (positive control, law 54).
	//
	// >= admits the snapped-to-64 case. Stock is unaffected because the whole
	// scaling path is gated on factor > 1.01 long before here.
	//
	// ⚠ HONEST STATUS: this is the best-supported hypothesis, not a proof. The
	// raster's bad region is DETERMINISTIC (byte-identical across two separate
	// sessions), so it is not uninitialised heap - which is what this repair
	// guards against. If the red survives, the byte dump added below names it
	// instead, and this gate change should be judged on its own merits (the
	// tier asymmetry above is real regardless).
	if (pMM && pMM != lastMinimapSurfResize && pMM->GetW() >= 64
		&& gMinimapRetry.ShouldAttempt(pMM))
	{
		uint8_t* raw = reinterpret_cast<uint8_t*>(pMM);
		const int32_t blitSize = *reinterpret_cast<int32_t*>(raw + 0xe4);
		Logger& lg = Logger::Get();

		// Only a surface that reaches Step 4 counts as recreated. Declared
		// outside the __try so the __except path leaves it false.
		bool surfOk = false;

		// ===== CARRY THE OLD PICTURE ACROSS THE RECREATE (v2.41.12) =====
		// MEASURED 2026-08-01: before this block runs, the minimap raster
		// holds a REAL image - centre-diagonal sampling gives distinct=4
		// with terrain colours (3D66B4 blue, 73B000 green). Afterwards it
		// is all zeros, because we destroy the surface, make a new one and
		// PRE-CLEAR IT TO BLACK. So our own repair takes a working map away
		// and shows nothing until the game's message-driven bake lands.
		//
		// The pre-clear was added to hide uninitialised VRAM, and it does -
		// but black is not the only non-garbage option. Copy the old
		// picture out first and paint it back scaled, so the map is
		// CONTINUOUSLY VISIBLE and merely softens until the bake sharpens
		// it. Falls back to the black fill if anything here fails, so the
		// worst case is exactly the old behaviour.
		//
		// Deliberately NOT reordering the destroy/create sequence: that is
		// the v2.21.1 crash site, and lifetime changes there are how it
		// crashed. This only READS before and WRITES after.
		int oldW = 0, oldH = 0;
		CaptureSurface(*reinterpret_cast<void**>(raw + 0xf0), &oldW, &oldH);
		lg.WriteLine(LogLevel::Info,
			"UiSpike: MINIMAP captured old surface %dx%d for carry-over%s",
			oldW, oldH, (oldW > 0) ? "" : " - FAILED, will clear to black");

		lg.WriteLine(LogLevel::Info,
			"UiSpike: MINIMAP 2X win %dx%d blitSize=%d ptr=%p parent=0x%08X "
			"(found under dock 0x0987B48F by scoped search) — recreating surface",
			pMM->GetW(), pMM->GetH(), blitSize, static_cast<void*>(pMM),
			ParentIdOf(pMM));

		// MMBUF sample 2 of 3: the window has now been resized by the pass
		// above. If the pbuff is STILL 64x64 here, it was allocated at the
		// old size and every composite from now on clips through it.
		LogMinimapBuffer("2-after-resize", pMM);

		__try
		{
			// Step 1: Destroy old display surface [esi+0xf0]
			void* oldSurf = *reinterpret_cast<void**>(raw + 0xf0);
			if (oldSurf)
			{
				*reinterpret_cast<void**>(raw + 0xf0) = nullptr;
				void** oldVt = *reinterpret_cast<void***>(oldSurf);
				typedef void (__thiscall* DeleteFn)(void*);
				reinterpret_cast<DeleteFn>(oldVt[2])(oldSurf); // vtable+0x8
				lg.WriteLine(LogLevel::Debug, "UiSpike: MINIMAP old surface destroyed");
			}

			// Step 2: Get the surface factory via the global object.
			// call 0x8793EC → globalObj; QI({0xC416025C,0x73283C}) → factory
			void* factory = nullptr;
			typedef void* (__cdecl* GetGlobalFn)();
			void* globalObj = reinterpret_cast<GetGlobalFn>(0x008793EC)();
			if (globalObj)
			{
				void** gvt = *reinterpret_cast<void***>(globalObj);
				typedef bool (__thiscall* QIFn)(void*, uint32_t, uint32_t, void**);
				reinterpret_cast<QIFn>(gvt[5])(
					globalObj, 0xC416025C, 0x73283C, &factory);
			}

			// Step 3: Create new surface via factory->vtable+0xc
			if (factory)
			{
				void** fvt = *reinterpret_cast<void***>(factory);
				typedef bool (__thiscall* CreateFn)(void*, void**);
				reinterpret_cast<CreateFn>(fvt[3])(
					factory, reinterpret_cast<void**>(raw + 0xf0));
			}

			// Step 4: Init new surface at blitSize × blitSize
			void* newSurf = *reinterpret_cast<void**>(raw + 0xf0);
			if (newSurf && blitSize > 0)
			{
				void** nvt = *reinterpret_cast<void***>(newSurf);
				typedef bool (__thiscall* InitFn)(void*, int, int, int, int);
				reinterpret_cast<InitFn>(nvt[3])(
					newSurf, blitSize, blitSize, 9, 32);
				surfOk = true;
				lg.WriteLine(LogLevel::Info,
					"UiSpike: MINIMAP new surface created+inited at %dx%d",
					blitSize, blitSize);
			}
			else
			{
				lg.WriteLine(LogLevel::Error,
					"UiSpike: MINIMAP surface creation FAILED (factory=%p surf=%p)",
					factory, newSurf);
			}
		}
		__except (EXCEPTION_EXECUTE_HANDLER)
		{
			lg.WriteLine(LogLevel::Error,
				"UiSpike: MINIMAP surface recreation FAULTED");
		}

		// Pre-clear the new surface so the one frame between Init and the
		// engine's deferred terrain re-bake shows a solid colour instead of
		// uninitialized VRAM (the "garbled map" flash on city open). The
		// game's own builder does the equivalent Lock/fill/Unlock at
		// 0x7A8C81. We go through the cIGZBuffer interface via QI so the
		// Fill slot is correct regardless of the concrete surface's vtable
		// layout: its PRIMARY vtable inserts extra virtuals (Width sits at
		// slot 34, not the interface's slot 9), so a Fill dispatched through
		// the raw primary pointer would hit the wrong slot. QI yields the
		// clean interface vtable. SEH-guarded: an unsupported QI or a fault
		// just leaves the flash in place - it never crashes.
		{
			void* surfPrimary = *reinterpret_cast<void**>(raw + 0xf0);
			if (surfPrimary)
			{
				__try
				{
					cIGZBuffer* pPrimary = reinterpret_cast<cIGZBuffer*>(surfPrimary);
					cIGZBuffer* pBuf = nullptr;
					if (pPrimary->QueryInterface(GZIID_cIGZBuffer, reinterpret_cast<void**>(&pBuf))
						&& pBuf)
					{
						const uint32_t black = pBuf->ConvertRGBValueToNative(0, 0, 0);
						cRZRect outRect = {};
						pBuf->Fill(black, 0, 0, blitSize, blitSize, &outRect);

						// CARRY-OVER (v2.41.12): repaint the old picture,
						// nearest-neighbour scaled to the new size, so the
						// map never goes blank. Black stays underneath as
						// the floor, so a partial restore still cannot show
						// uninitialised VRAM.
						if (oldW > 0 && oldH > 0 && blitSize > 0)
						{
							RestoreSurfaceBilinear(pBuf, oldW, oldH, blitSize);
							lg.WriteLine(LogLevel::Info,
								"UiSpike: MINIMAP old picture carried over "
								"%dx%d -> %dx%d bilinear (map stays visible; "
								"the engine's bake sharpens it).",
								oldW, oldH, blitSize, blitSize);
						}
						else
						{
							lg.WriteLine(LogLevel::Debug,
								"UiSpike: MINIMAP surface pre-cleared to black "
								"(no old picture to carry over)");
						}
						pBuf->Release();
					}
					else
					{
						lg.WriteLine(LogLevel::Info,
							"UiSpike: MINIMAP surface QI for cIGZBuffer failed (flash remains)");
					}
				}
				__except (EXCEPTION_EXECUTE_HANDLER)
				{
					lg.WriteLine(LogLevel::Error,
						"UiSpike: MINIMAP surface pre-clear FAULTED (flash remains)");
				}
			}
		}

		// Run the game's OWN per-size recompute (cSC4WinMiniMap sub at
		// 0x7A7840 - the exact call init makes at 0x7A8B57). It does, in
		// order: resize the render buffer [this+0x114] to blitSize via
		// 0x7A7570; recompute the zoom level [this+0x104] from the terrain
		// dimension vs blitSize; notify [this+0x120]; and - critically -
		// set the dirty flags [this+0xFD]=[this+0xFE]=1 that tell Plot the
		// terrain image must be re-baked into the display surface. Without
		// those flags Plot just re-blits its cached (64x64 / empty) image
		// and the 2x surface never shows the city. Reads [this+0xE4] for
		// the size (already set to blitSize by the SetArea override above).
		// Proven safe: init invokes it with the same preconditions.
		if (blitSize > 0)
		{
			__try
			{
				typedef void (__thiscall* RecomputeFn)(void*);
				reinterpret_cast<RecomputeFn>(0x007A7840)(pMM);
				lg.WriteLine(LogLevel::Info,
					"UiSpike: MINIMAP recompute 0x7A7840 ok zoom=%d fd=%d fe=%d",
					*reinterpret_cast<int32_t*>(raw + 0x104),
					(int)raw[0xfd], (int)raw[0xfe]);
			}
			__except (EXCEPTION_EXECUTE_HANDLER)
			{
				// Fallback: replicate the parts of 0x7A7840 that do not
				// touch the [this+0x120] notifier, and set the dirty flags
				// by hand so Plot still re-bakes.
				lg.WriteLine(LogLevel::Error,
					"UiSpike: MINIMAP 0x7A7840 FAULTED - manual fallback");
				__try
				{
					typedef bool (__thiscall* CreateBufFn)(void*, int, int);
					reinterpret_cast<CreateBufFn>(0x007A7570)(
						raw + 0x114, blitSize, blitSize);
				}
				__except (EXCEPTION_EXECUTE_HANDLER) {}
				int32_t mapW = 0;
				__try
				{
					void* terrain = *reinterpret_cast<void**>(0x00B43CEC);
					if (terrain)
					{
						void** tvt = *reinterpret_cast<void***>(terrain);
						typedef int (__thiscall* GetDimFn)(void*);
						mapW = reinterpret_cast<GetDimFn>(tvt[0x174 / 4])(terrain);
					}
				}
				__except (EXCEPTION_EXECUTE_HANDLER) {}
				if (mapW > 0)
				{
					int32_t zoom = 0, dim = mapW;
					while (dim > blitSize) { dim >>= 1; zoom++; }
					while (dim < blitSize) { dim <<= 1; zoom--; }
					*reinterpret_cast<int32_t*>(raw + 0x104) = zoom;
				}
				raw[0xfd] = 1;
				raw[0xfe] = 1;
			}
		}

		// ===== CLEAR THE RASTER, NOT JUST THE SURFACE (v2.41.9, #89) =====
		// THE HOLE THIS CLOSES. Our sequence above is:
		//   1. recreate the display surface [+0xF0]
		//   2. pre-clear THAT SURFACE to black          <- destination
		//   3. recompute 0x7A7840, which internally calls 0x7A7570 and
		//      FREE+MALLOCS the raster [+0x114] at the new size <- SOURCE,
		//      and it is now UNINITIALISED HEAP
		//   4. InvalidateSelf
		// Later, on a MESSAGE tick (not a paint), 0x7A8640 runs the
		// raster->surface transfer (0x7A66F0/0x7A67F0) and copies that
		// uninitialised heap straight over the black we just wrote.
		// We were cleaning the destination and never the source.
		//
		// Why this is ours and not stock's: stock allocates this raster
		// ONCE at city init, with the pointer NULL, and the tile bake
		// fills it before anything transfers. Only WE force a second
		// free+malloc at a DIFFERENT size mid-session - on a heap carrying
		// our extra ~11.7MB of dats, so the fresh block is full of former
		// pixel data. That reads as mottled colour, which is exactly the
		// "corruption" reported, and it corrects itself once the [+0xFD]
		// re-bake gate finally repopulates the raster.
		//
		// Layout is MEASURED, not guessed: 0x7A7570 treats ecx as a
		// 3-dword struct {pixel ptr, w, h} (early-out 0x7A757C, free
		// 0x5E5620, malloc(w*h*4) 0x5E55E0, store 0x7A75BB) and the bake
		// reads it as a raw base (0x7A8550: mov esi,[ebx+0x114]).
		//
		// Writes only zeroes, into a buffer the engine is about to
		// overwrite anyway. No game call, no render entry point, no
		// geometry. Bounds-checked and SEH-guarded; a fault just leaves
		// the old behaviour.
		{
			void* rptr = nullptr;
			int32_t rw = 0, rh = 0;
			__try
			{
				rptr = *reinterpret_cast<void**>(raw + 0x114);
				rw = *reinterpret_cast<int32_t*>(raw + 0x118);
				rh = *reinterpret_cast<int32_t*>(raw + 0x11C);
				if (rptr && rw > 0 && rh > 0 && rw <= 4096 && rh <= 4096)
				{
					memset(rptr, 0, static_cast<size_t>(rw) *
						static_cast<size_t>(rh) * 4u);
					lg.WriteLine(LogLevel::Debug,
						"UiSpike: MINIMAP raster [+0x114] %p %dx%d zeroed "
						"(source of the transfer, not just the surface).",
						rptr, rw, rh);
				}
				else
				{
					lg.WriteLine(LogLevel::Info,
						"UiSpike: MINIMAP raster NOT zeroed - ptr=%p %dx%d "
						"outside sane bounds.", rptr, rw, rh);
				}
			}
			__except (EXCEPTION_EXECUTE_HANDLER)
			{
				lg.WriteLine(LogLevel::Error,
					"UiSpike: MINIMAP raster zero FAULTED (garbage may remain).");
			}
		}

		// BOUNDED RETRY (v2.41.0, task #89). Latch ONLY on success. Before
		// this, the latch was set here unconditionally, so a FAULTED or
		// FAILED recreate was never retried and the window kept its stale
		// 1x surface under a 2x rect for the rest of the city - the
		// v2.21.0 crash shape, made permanent by the very guard meant to
		// prevent it. After kSurfMaxAttempts we latch anyway so a
		// genuinely unrecreatable surface cannot re-attempt at ~4x/sec.
		if (surfOk)
		{
			lastMinimapSurfResize = pMM;
		}
		else
		{
			gMinimapRetry.NoteFail();
			if (gMinimapRetry.Exhausted())
			{
				lastMinimapSurfResize = pMM;   // give up, stop retrying
				lg.WriteLine(LogLevel::Error,
					"UiSpike: MINIMAP surface recreate failed %d time(s) - "
					"giving up on this instance (stale surface remains).",
					kSurfMaxAttempts);
			}
			else
			{
				lg.WriteLine(LogLevel::Info,
					"UiSpike: MINIMAP surface recreate failed - will RETRY "
					"on a later sweep (attempt %d of %d).",
					gMinimapRetry.fails, kSurfMaxAttempts);
			}
		}

		// MMBUF sample 3 of 3: after the display-surface recreate. The
		// surface and the pbuff are DIFFERENT objects - this line proves
		// whether fixing one leaves the other stale.
		LogMinimapBuffer("3-after-recreate", pMM);

		// Schedule an engine draw so Plot re-bakes the terrain into the
		// new 2x surface on its own tick. Do NOT call Plot ourselves - it
		// is a render entry point and re-entering it from the subclass
		// timer is unsafe (the PostCityInit hang lesson applies to draws
		// too). InvalidateSelf is the safe "mark dirty" primitive.
		pMM->InvalidateSelf();
	}
}

int UiSpike::ScalePanelsUnder(cIGZWin* pRoot, const char* rootTag)
{
	const int32_t screenW = pRoot->GetW();
	const int32_t screenH = pRoot->GetH();
	const float f = settings.spikeScaleFactor;

	// ⚠ DRAIN BEFORE THE WALK (v2.39.0, task #5). Born-scale records were
	// drained inside ScaleGodFlyouts (:6898), which runs AFTER this walk - fine
	// for the nested sub-flyout, because the walk skips it by id
	// (IsSubFlyoutId). The Create Disaster container is ANONYMOUS, so nothing
	// skips it: born at 282x678 it would reach Classify with no record yet,
	// come back Fresh, and be scaled AGAIN to 564x1356.
	// DrainBornScaleRecords is a plain queue drain (gBornQN -> 0), so calling it
	// here as well as there is safe and idempotent; the later call becomes a
	// no-op whenever this one has already emptied the queue.
	DrainBornScaleRecords();

	// MMBUF sample 1 of 3 (task #89): the dock minimap's private paint buffer
	// BEFORE this pass touches anything. If buffer and window agree here, the
	// corruption is not yet present and it dates to our resize below.
	if (rootTag[0] == 'c')
	{
		cIGZWin* pDockPre = pRoot->GetChildWindowFromIDRecursive(0x0987B48F);
		cIGZWin* pMMPre = pDockPre
			? pDockPre->GetChildWindowFromIDRecursive(0x0BC3B559) : nullptr;
		LogMinimapBuffer("1-before-pass", pMMPre);
	}

	// Snapshot the panel list first: resizing during enumeration would
	// mutate the collection being walked.
	// v2.22.3 (audit fix): the cap was SILENT. Direct children of the view
	// have grown a lot (nine My Sims roots, the U-Drive-It status panel + its
	// dashboard, Data Views un-skipped), and because enumeration is
	// reverse-add-order the panels DROPPED would be the earliest-added ones -
	// i.e. a whole panel silently never scaling. Raised to 128 and logged once
	// if it ever fills, so this can never again be an invisible failure.
	PanelInfo panels[128] = {};
	CollectCtx ctx = { panels, 0, 128 };
	pRoot->EnumChildren(GZIID_cIGZWin, CollectCtx::Callback, &ctx);
	if (ctx.count >= 128)
	{
		static bool capLogged = false;
		if (!capLogged)
		{
			capLogged = true;
			Logger::Get().WriteLine(LogLevel::Info,
				"UiSpike: PANELCAP hit %d direct view children - panels beyond "
				"the cap are NOT scaled (raise PanelInfo[]).", ctx.count);
		}
	}

	int scaledWindows = 0;
	// v2.69.0 (#117): see the note at the head of ScaleSubtree's child loop.
	// The verify below is a CRASH KILLER and stays; it is now skipped only when
	// the previous iteration provably mutated nothing.
	bool mutatedSinceVerify = false;
	for (int i = 0; i < ctx.count; i++)
	{
		PanelInfo& p = panels[i];

		// BUDGETWATCH. FIRST in the loop, deliberately - before the region
		// filter, before never-scale, before every skip - because the whole
		// point is to see changes on windows this loop deliberately does NOT
		// touch. Read-only: it compares and logs, and continues into the
		// normal path unchanged.
		if (p.win && gBudgetWatchLog < 40)
		{
			const uint32_t wid = p.win->GetID();
			for (BudgetWatch& bw : gBudgetWatch)
			{
				if (bw.id != wid) { continue; }
				const int32_t cw = p.win->GetW(), ch = p.win->GetH();
				const int32_t cl = p.win->GetL(), ct = p.win->GetT();
				if (bw.seen && (cw != bw.w || ch != bw.h
						|| cl != bw.l || ct != bw.t))
				{
					gBudgetWatchLog++;
					// ATTRIBUTION IS TESTED, NOT ASSERTED. The first
					// version of this line claimed "NOT by us"; the 19:04
					// capture showed all four roots going design ->
					// RoundHalfUp(design*f) at city open with vis=0, which is
					// our OWN sweep one tick late - the watcher baselines a
					// panel before this loop scales it, so the change lands on
					// the next tick. Only the arithmetic can tell the two
					// apart, so the arithmetic decides the wording.
					const bool wasDesign =
						(bw.w == RoundHalfUp(cw / gTierF)
							|| cw == RoundHalfUp(bw.w * gTierF));
					Logger::Get().WriteLine(LogLevel::Info,
						"UiSpike: BUDGETWATCH 0x%08X CHANGED (%d,%d %dx%d) -> "
						"(%d,%d %dx%d)  [%s]  vis=%d  %s",
						wid, bw.l, bw.t, bw.w, bw.h, cl, ct, cw, ch,
						(cw == bw.w && ch == bw.h) ? "MOVED only"
							: (cl == bw.l && ct == bw.t) ? "RESIZED only"
								: "moved AND resized",
						p.win->IsVisible() ? 1 : 0,
						wasDesign
							? "- size ratio is the tier factor: this is OUR "
							  "sweep, surfaced one tick late."
							: "- NOT a tier-factor change, so not our scaling.");
				}
				bw.w = cw; bw.h = ch; bw.l = cl; bw.t = ct; bw.seen = true;

				// BUDGETKIDS: the same question one level down, and only
				// while the root is actually on screen - a hidden template
				// re-laying itself is not what the user is watching.
				if (p.win->IsVisible() && gBudgetKidsLog < 30)
				{
					const int slot =
						static_cast<int>(&bw - &gBudgetWatch[0]);
					ChildSnapshot kids = {};
					p.win->EnumChildren(GZIID_cIGZWin,
						ChildSnapshot::Callback, &kids);
					// FNV-1a over every child's (id, L, T, W, H). A digest,
					// not a comparison of stored rects: 36 children x 4 roots
					// of retained state would be the expensive way to answer
					// a yes/no question, and the follow-up dump below prints
					// the actual numbers once something has changed.
					uint32_t dg = 2166136261u;
					for (int k = 0; k < kids.count; k++)
					{
						cIGZWin* kw = kids.wins[k];
						if (!kw) { continue; }
						const uint32_t f5[5] = {
							kw->GetID(),
							static_cast<uint32_t>(kw->GetL()),
							static_cast<uint32_t>(kw->GetT()),
							static_cast<uint32_t>(kw->GetW()),
							static_cast<uint32_t>(kw->GetH()) };
						for (uint32_t v : f5)
						{
							dg = (dg ^ (v & 0xFFu)) * 16777619u;
							dg = (dg ^ ((v >> 8) & 0xFFu)) * 16777619u;
							dg = (dg ^ ((v >> 16) & 0xFFu)) * 16777619u;
							dg = (dg ^ ((v >> 24) & 0xFFu)) * 16777619u;
						}
					}
					if (gBudgetKidsCount[slot] >= 0
						&& (dg != gBudgetKidsDigest[slot]
							|| kids.count != gBudgetKidsCount[slot]))
					{
						gBudgetKidsLog++;
						Logger::Get().WriteLine(LogLevel::Info,
							"UiSpike: BUDGETKIDS 0x%08X children CHANGED "
							"(%d -> %d children) while the root held "
							"(%d,%d %dx%d) - dumping first 10:",
							wid, gBudgetKidsCount[slot], kids.count,
							cl, ct, cw, ch);
						const int dumpN = kids.count < 10 ? kids.count : 10;
						for (int k = 0; k < dumpN; k++)
						{
							cIGZWin* kw = kids.wins[k];
							if (!kw) { continue; }
							Logger::Get().WriteLine(LogLevel::Info,
								"UiSpike: BUDGETKIDS   [%d] 0x%08X "
								"(%d,%d %dx%d) vis=%d",
								k, kw->GetID(), kw->GetL(), kw->GetT(),
								kw->GetW(), kw->GetH(),
								kw->IsVisible() ? 1 : 0);
						}
					}
					gBudgetKidsDigest[slot] = dg;
					gBudgetKidsCount[slot] = kids.count;
				}
				break;
			}
		}

		if (i > 0 && mutatedSinceVerify)
		{
			// CRASH KILLER: earlier panel mutations can trigger game-side
			// destruction of later panels (rapid menu switching). Verify the
			// pointer is still in the live child list before touching it.
			ChildSnapshot verify = {};
			pRoot->EnumChildren(GZIID_cIGZWin, ChildSnapshot::Callback, &verify);
			// v2.69.3: the reset that used to sit here was UNSOUND - a verify
			// proves liveness of THIS pointer only, never of the remainder,
			// so the signal must stay latched once anything has mutated.
			bool alive = false;
			for (int j = 0; j < verify.count; j++)
			{
				if (verify.wins[j] == p.win) { alive = true; break; }
			}
			if (!alive)
			{
				continue;
			}
		}

		// REGION: whitelist ONLY. Transient dialogs there (Load Region, the
		// city-info bubble) are game-positioned; scaling them causes the
		// reset/re-anchor fight the user saw as "jumping around". They stay
		// stock until the static .UI design pass handles them.
		const bool isRegionPass = (rootTag[0] == 'r');
		if (isRegionPass && !IsRegionPanelId(p.win->GetID()))
		{
			continue;
		}
		if (IsNeverScaleId(p.win->GetID()))
		{
			continue;
		}
		// God-mode tool flyouts are handled by ScaleGodFlyouts with a
		// SIZE-ONLY (no root move) scale - the generic root-move anchor here
		// teleports them. Skip so terraform/terrain-fx (direct view children)
		// aren't double-handled.
		if (IsGodToolFlyoutId(p.win->GetID()))
		{
			continue;
		}
		// MAYOR-ONLY FLYOUTS (zones/transport/utilities/civic). Left to the
		// generic path they hit ScalePanelRoot's CENTER-ANCHOR branch (both
		// gapT and gapB exceed frameH/4), which repositions them with no
		// reference to the button that spawned them - the zone flyout landed at
		// y=241 (421 + 180 - 360) instead of 344. ScaleGodFlyouts docks them to
		// their spawn button via the alignment-marker rule instead.
		if (IsMayorOnlyFlyoutId(p.win->GetID()))
		{
			continue;
		}
		// SHARED SUB-FLYOUT container: the generic path doubles its position
		// from the screen origin, which bears no relation to the button that
		// spawned it. ScaleGodFlyouts sizes it and leaves the game's placement.
		if (IsSubFlyoutId(p.win->GetID()))
		{
			continue;
		}
		// Only the REAL HUD: the tree is mostly hidden variant stacks and
		// menu layers - scaling those collapses the UI (proven). Known
		// region panels are the exception: pre-scaled while hidden so they
		// appear already at 2x (no visible jump when a flyout opens). The
		// god-toolbar TWINS get the same treatment: 0x69E40A1F reports vis=0
		// in god mode while it still draws, and skipping it split the twins
		// (the duplicate-sun bug).
		if (!p.win->IsVisible()
			&& !IsRegionPanelId(p.win->GetID())
			&& !IsGodPanelId(p.win->GetID())
			&& !IsAlwaysScaleCityId(p.win->GetID()))
		{
			continue;
		}
		// 0xAA32BCE6 - the DATA VIEWS panel (task #45), NOT "plop-menu
		// machinery" as the original spike-era label claimed: the full tree
		// dump (userclickthrough log line 606+) shows its 8 children are the
		// Data Views fold-out - compact bar 0x8A2871B1/B2, expanded pages
		// 0x8A2871C3/D4/D5, list flyout 0x8A2871C4, hidden Map View
		// 0x00004200. Live script I-2bc9060f (rect-matched;
		// I-ea287193/I-0b72f276 are stale copies).
		//
		// v2.21.0 removed the historical skip here and shipped 2x art: the
		// COMPACT panel rendered correctly (user-confirmed) but EXPAND
		// crashed. v2.21.1 reverted; the offline disassembly then proved the
		// crash was NOT the expand geometry (the state-flip helpers
		// 0x79DF10/0x79DFB0 are pure show/hide via sub_9AFCFE - no moves, no
		// resizes) but the map child 0x00004203: a second cSC4WinMiniMap
		// instance whose one-shot display surface stayed 256 while the
		// data-view renderer sub_7A2F60 built window-sized (512) buffers.
		// v2.21.2 re-lands the scaling WITH the DVMAP surface recreate
		// (see the block after ScaleGodFlyouts) - the same lever that has
		// protected the dock minimap since it was scaled.
		// Skip full-screen overlay layers (they already cover the view).
		if (p.w >= screenW * 9 / 10 && p.h >= screenH * 9 / 10)
		{
			continue;
		}
		// Skip degenerate/empty windows.
		if (p.w <= 0 || p.h <= 0)
		{
			continue;
		}

		// FLASHSET: capture on-screen state BEFORE the scale - afterwards is
		// too late to tell whether this window was on screen when we resized
		// it. The ancestor walk is what makes this a flash test rather than a
		// born-visible test (see NoteFlashCandidate).
		const bool wasOnScreen = IsOnScreen(p.win);
		// #107: record whether Budget was ever opened this launch. It is a
		// MEASURED precondition of #104 (bisect runs 2-4 were false negatives
		// purely because Budget never got opened), so it is recorded per
		// launch rather than remembered.
		SpinProbe::NoteWindowId(p.win->GetID());
		// #176 RELATCH, ARMED FOR EVERY CITY PANEL ROOT (widened 2026-08-19).
		// It used to be limited to kAlwaysScaleCityIds on the grounds that the
		// guard is "provably safe only under roots whose staged scripts
		// pre-scale every authored crop". That scoping is unnecessary, because
		// RelatchBmpSourceRect refuses on its own terms - it acts ONLY when the
		// crop is EXACTLY (0,0,oldW,oldH), i.e. when it demonstrably tracked the
		// pre-resize window and is therefore a stale SetImage latch. Its own
		// comment says so: "not latch-following: leave every real crop alone".
		// It also requires the GZWinBMP class, the has-imagerect flag, sane
		// image dims, and no-ops when the crop already matches.
		//
		// WHY IT HAD TO WIDEN: the "<name> lives here" balloon that appears
		// after Move In a Sim is an ANONYMOUS root (id 0x00000000, 272x200 ->
		// 544x400 at 2x), so it cannot be named in any id list. Its portrait
		// kept a 36x41 crop over the 72x82 face our package now wins with, and
		// drew the top-left quarter magnified - user: "a purple circle shows
		// which should have his face but it's only showing the top left 1/4".
		//
		// ⭐ LAW: WHEN THE ROOT HAS NO ID, THE FIX CANNOT BE AN ID LIST. Widen
		// a guard that is self-limiting rather than inventing a size or
		// position heuristic to name the unnameable.
		gRelatchArmed = true;
		const int n = ScalePanelRoot(p.win, screenW, screenH, f);
		gRelatchArmed = false;
		// n counts WINDOWS MUTATED (every SetW/SetH/GZWinMoveTo in
		// ScalePanelRoot and ScaleSubtree is paired with a count++), so n>0 is
		// the exact "we touched something" signal the verify gate needs.
		if (n > 0) { mutatedSinceVerify = true; }
		if (n > 0)
		{
			Logger::Get().WriteLine(
				LogLevel::Debug,
				"UiSpike: %s panel 0x%08X - %d windows scaled.",
				rootTag, p.win->GetID(), n);
			if (wasOnScreen)
			{
				NoteFlashCandidate(p.win, p.win->GetID(), n, rootTag,
					GetTickCount() - fireAtMs);
			}
		}
		scaledWindows += n;
	}

	if (settings.spikeMenuFlyouts)
	{
		cIGZWin* pMenu = pRoot->GetChildWindowFromID(kGZWin_MenuContainer);
		if (pMenu)
		{
			ScaleMenuFlyouts(pMenu, screenW, screenH, f);
		}
	}

	// #127: table-driven panel docking, EVERY incremental tick. The Graphs pair
	// only exists once the user OPENS the panel, long after the load-time sweep
	// - putting this in ScaleAll alone (v2.75.1) meant it never fired once.
	ApplyPanelDocks(pRoot, f);

	// God-mode tool flyouts: dock them for the CITY view on BOTH the initial
	// "city" pass AND every "incremental" pass (that's the continuous sweep
	// that catches a flyout opened after init). Only "region" is excluded.
	if (rootTag[0] != 'r')
	{
		ScaleGodFlyouts(pRoot, f);

		// After the minimap window is scaled, recreate its internal display
		// surface at the new blitSize. The surface's vtable+0xc is an Init
		// method (one-shot), NOT a resize — calling it on an existing surface
		// corrupts it. We must destroy and recreate, replicating the game's
		// own pattern from 0x7A8C18-0x7A8C61.
		// Track the minimap pointer (not a bool) so this re-fires when the
		// game rebuilds the UI on a new city load (new minimap object).
		// lastMinimapSurfResize lives at namespace scope (v2.23.3): Disarm
		// NULLs it so a second city reusing the freed address still re-fires.
		// SCOPED to the HUD dock (v2.22.3 - audit fix). This search used to be
		// global-recursive, and window id 0x0BC3B559 is NOT unique: the
		// U-Drive-It dashboard (root 0x4BCB938A, all 43 vehicle scripts) hosts
		// a SECOND cSC4WinMiniMap under the SAME id. EnumChildren enumerates in
		// REVERSE add order (CITY-DOCK-OVERLAP.md 1.2) and the dashboard is
		// added later, so while driving the global search reached the
		// DASHBOARD's instance: this block recreated that surface and latched
		// it, then the UDMAP block below destroyed the brand-new surface and
		// recreated it again in the same sweep - while the dock instance never
		// got its recreate at all. Both log lines also read "128x128" (both are
		// 64x64 design), so the log could not tell them apart.
		//
		// v2.41.0 CORRECTION (task #89): the comment used to end "the parent id
		// is now printed". It was not - the line printed only win/blitSize/ptr,
		// so the single fact that would have identified the wrong twin was
		// still missing. It is printed now, AND it is a GATE: the instance must
		// prove it descends from the dock before we touch its surface. Scoping
		// is no longer held by the search alone. (Standing law: your own
		// comment is an instrument, and this one was lying about its scope.)
		cIGZWin* pDock = pRoot->GetChildWindowFromIDRecursive(0x0987B48F);
		// v2.41.19: the whole recreate lives in TryRecreateMinimapSurface now
		// (shared with EarlyDockTick mode 2 - see the note on the function).
		TryRecreateMinimapSurface(pDock);

		// DATA VIEWS map (task #45 re-land, v2.21.2): the expanded page's
		// 256x256 map child 0x00004203 is a SECOND cSC4WinMiniMap instance -
		// proven offline: the class's GetClassID at 0x7A6580 returns clsid
		// 0xCA318388 and the Data Views renderer sub_7A2F60 fetches 0x4203
		// via the same iid 0xCA318385 the dock minimap exposes. The v2.21.0
		// crash-on-expand was THIS instance: the renderer builds a
		// window-sized pixel buffer (it reads the LIVE rect at 0x7A301E and
		// creates the buffer at W x H, 0x7A3094), while the instance's
		// one-shot display surface was still 256 from city init - the same
		// stale-surface overrun the dock-minimap block above exists to
		// prevent. blitSize [this+0xE4] self-updates via the class SetArea
		// override when the sweep resizes the window; only the surface is
		// one-shot. Mirror of the MINIMAP block above, per-step rationale
		// documented there. lastDataMapSurfResize lives at namespace scope
		// (v2.23.3): Disarm NULLs it so a second city reusing the freed
		// address still re-fires the recreate.
		cIGZWin* pDVRoot = pRoot->GetChildWindowFromID(kGZWin_MenuContainer);
		cIGZWin* pDVMap = pDVRoot
			? pDVRoot->GetChildWindowFromIDRecursive(0x00004203) : nullptr;
		// v2.70.0: THE CLAMP IS OFF (user decision - "we need this map to
		// scale"). It shipped in v2.69.8-10 and works, but the trade it makes
		// (a 256 map centered in the 512 slot on small tiles) is the thing
		// the user rejected. The FULL-SIZE path below is v2.69.5's - which
		// the user confirmed looked right. (Its later add-on, the per-sweep
		// heal, was retired with the dock-seed in v2.71.4 - the x8 bake patch
		// made both obsolete; see the tombstone at the latch declarations.)
		// The clamp code is kept below, gated, as the emergency fallback; the
		// DVPIN coupling is inert while gDvMapClampBlit stays 0.
		//
		// (v2.69.8's original rationale, kept for the record): the game's
		// terrain bake fills this map only while
		// surface <= terrain*4 (zoom >= -2) and produces NOTHING past it, AND
		// it re-clears the surface to 0xFF000000 every sim-day tick - so any
		// content we inject is wiped ~1x/second and a heal loop at the OLD
		// 30-sweep cadence would flicker. (At per-sweep cadence the gap is
		// one 16 ms frame, which is why the heal is viable after all.) On
		// tiles too small for the full 2x map it
		// CLAMPed the window to terrain*4 and centered it in its slot. The
		// surface then never leaves the game's design range, the bake works,
		// and the map draws CORRECT at reduced size - small city, smaller
		// map. Bigger tiles are untouched (their zoom stays >= -2 at 512).
		// The scaleMap record is written as AlreadyScaled at the clamped size
		// so the sweep never re-doubles it (no tug-of-war, no tombstone
		// flicker). The renderer builds WINDOW-sized buffers (#45), so a
		// clamped window keeps buffer==surface==256 - full stock behavior.
		// v2.70.1: CLAMP BACK ON as the stable interim. v2.70.0's per-sweep
		// heal produced WRONG CELL COLORS + a per-day flash, and the user's
		// screenshot proves WHY the whole heal family is unfixable: the game
		// ALPHA-BLENDS data cells onto whatever base is under them AT PAINT
		// TIME. Refresh order is clear -> bake (nothing at zoom=-3) -> blend
		// cells onto BLACK, so the cells are born dark and no later base
		// repair can un-blend them. The base must exist BEFORE the cell
		// paint - i.e. the game's own bake must work at -3. That is the
		// CodePatches x8 bake extension being derived offline (#121); until
		// it ships, the clamp (correct, stable, smaller map on small tiles
		// only) is the honest state. Flip to false ONLY with the bake patch.
		// v2.71.0: the clamp is now the FALLBACK, not the policy. When the
		// x8 bake patch is live the game can bake a real terrain base at
		// zoom -3, so the map runs FULL SIZE and nothing needs clamping. If
		// the patch declined (wrong exe build, another mod got the site
		// first), we fall back to the clamp - correct, stable, smaller.
		// v2.72.0 (#109 CLOSED - THE FRACTIONAL-TIER CRASH): this block is no
		// longer a fallback for a declined bake. It is the SIZING POLICY, and
		// it runs at every tier.
		//
		// MEASURED, not inferred. Five SimCity Exception Reports (the game
		// writes them to Documents\SimCity 4\Exception Reports\) all fault at
		// the SAME instruction - 0x00910010, ACCESS_VIOLATION, the `rep stosd`
		// inside the game's row fill - at 1.5x (12:36:27) and at 3x (15:29:10)
		// alike, and never at 2x. The invariant they break is NOT the one this
		// project wrote down for two weeks ("blitSize is not a power-of-two
		// multiple of terrainDim"): blitSize measured EXACT at both crashing
		// tiers (1.5x 256 = 64<<2, 3x 512 = 64<<3). The real break is one level
		// out - the WINDOW and the SURFACE disagree:
		//
		//     tier    window   blitSize/surface   result
		//     1.50    384      256                CRASH
		//     2.00    512      512                fine
		//     3.00    768      512                CRASH
		//
		// The window is ScaleRound(256, f); the surface is created AT blitSize,
		// which snaps to a power-of-two multiple of terrainDim. Those agree
		// only when f is itself a power of two. Everything downstream that
		// takes its EXTENT from the window rect and its STRIDE from the surface
		// then walks off the end - in the game's own code, which is why no
		// __except of ours ever fired and the log simply stops.
		//
		// Cure: make the window EQUAL the surface at every tier, exactly as it
		// already is at 2x. Bit-identical at f=2 (512 is already the answer
		// there), so the working tier cannot regress.
		//
		// THE TRADE, stated plainly: at 3x on a 64-cell tile the map is 512 in
		// a slot the layout reserved for 768 - centred, correct, and still 2x
		// the stock size. A non-power-of-two map size is not available at all;
		// the alternative to a smaller map here is the crash, not a bigger map.
		if (pDVMap && pDVMap->GetW() > 256)
		{
			int32_t terrainDim = 0;
			__try
			{
				void* terrain = *reinterpret_cast<void**>(0x00B43CEC);
				if (terrain)
				{
					void** tvt = *reinterpret_cast<void***>(terrain);
					typedef int (__thiscall* GetDimFn)(void*);
					terrainDim = reinterpret_cast<GetDimFn>(tvt[0x174 / 4])(terrain);
				}
			}
			__except (EXCEPTION_EXECUTE_HANDLER) { terrainDim = 0; }
			// The bake ceiling: the game's own dispatch covers zoom -2 (x4);
			// our #121 patch extends it to zoom -3 (x8). Never exceed it - a
			// size the bake cannot reach is the black map (#121) all over.
			const int32_t bakeCeiling = terrainDim > 0
				? terrainDim * (CodePatches::MiniMapX8Active() ? 8 : 4) : 0;
			// The largest EXACT power-of-two multiple of terrainDim that fits
			// both the scaled window and the bake ceiling. This is the only
			// family of sizes the bake's addressing can describe.
			int32_t maxBlit = 0;
			if (terrainDim > 0)
			{
				const int32_t want = pDVMap->GetW() < bakeCeiling
					? pDVMap->GetW() : bakeCeiling;
				for (int32_t s = terrainDim; s <= want; s <<= 1) { maxBlit = s; }
			}
			if (maxBlit > 0 && pDVMap->GetW() != maxBlit)
			{
				const int32_t curW = pDVMap->GetW();
				const int32_t curH = pDVMap->GetH();
				uint8_t* dvRaw = reinterpret_cast<uint8_t*>(pDVMap);
				const int32_t blitBefore =
					*reinterpret_cast<int32_t*>(dvRaw + 0xe4);
				pDVMap->SetW(maxBlit);
				pDVMap->SetH(maxBlit);
				// Center in the slot the 2x layout reserved.
				pDVMap->GZWinMoveTo((curW - maxBlit) / 2, (curH - maxBlit) / 2);
				// v2.69.9 (the "split map" tear): blitSize [this+0xE4]
				// self-updates only through the class's SetArea OVERRIDE -
				// SetW/SetH does not route through it, so after the clamp the
				// window and surface were 256 while blitSize stayed 512, and
				// the renderer drew 512-stride into a 256 buffer: two copies
				// side by side + interlaced garbage, exactly the screenshot.
				// Write it directly, then re-run the game's per-size
				// recompute so zoom lands back at -2 (inside the bake range)
				// and the dirty flags match the clamped size.
				*reinterpret_cast<int32_t*>(dvRaw + 0xe4) = maxBlit;
				// v2.69.10: publish the clamp so DVPIN targets the SAME size
				// (its table entry used to re-double the map every sweep -
				// the ~30 Hz CLAMPED-line fight in the v2.69.9 log).
				gDvMapClampBlit = maxBlit;
				__try
				{
					typedef void (__thiscall* RecomputeFn)(void*);
					reinterpret_cast<RecomputeFn>(0x007A7840)(pDVMap);
					// v2.71.1 BORN CORRECT (#121 last 1%): the recompute only
					// MARKS every tile dirty (memset 0xFF at 0x7A78E2) and sets
					// fd=1; the actual bake is MESSAGE-DRIVEN via the handler
					// 0x7A8640, so it lands a tick or more later - the user sees
					// the panel open, then the map fill in. STOCK never shows
					// that gap (user-verified 2026-08-04: stock paints the
					// correct map immediately) because its map is built right
					// before it is shown, while ours is rescaled + recreated
					// after creation. Cure = the project's standing one: do the
					// work while HIDDEN. Drive the game's own bake synchronously
					// right here, on the same object and thread the handler
					// would use (0x7A8721), so the raster is full before the
					// first paint. Idempotent: the bake clears the dirty mask
					// itself, so the later message finds nothing to do.
					DriveMiniMapBake(pDVMap, "dvmap-recreate");
				}
				__except (EXCEPTION_EXECUTE_HANDLER)
				{
					Logger::Get().WriteLine(LogLevel::Error,
						"UiSpike: DVMAP clamp recompute FAULTED (report).");
				}
				// AlreadyScaled at the clamped size: the sweep must never
				// re-double this window (that is the tug-of-war shape).
				ScaleRecord rec = { pDVMap->GetID(), maxBlit, maxBlit,
					maxBlit, maxBlit, 0, false };
				StoreScaleRecord(pDVMap, rec);
				pDVMap->InvalidateSelf();
				// v2.72.2: repaint the ring we vacated - see the identical
				// block in SnapMiniMapToBake for the full reasoning. Shrinking
				// the window hands (curW-maxBlit) px back to the parent and
				// InvalidateSelf only dirties our NEW rect, so the parent's
				// last paint of the larger area stays on screen. vt+0x170 is
				// the game's SetDirty-AND-propagate; plain InvalidateSelf
				// does not reach cIGZWin+0x70 on an ancestor.
				// ⚠ DUPLICATED ON PURPOSE, FOR NOW: this block cannot simply
				// call SnapMiniMapToBake because it also publishes
				// gDvMapClampBlit, which DVPIN reads (law 43, coupled pair).
				// Consolidating the two needs that publish threaded through
				// the helper - owed, and tracked.
				if (cIGZWin* pDvParent = pDVMap->GetParentWin())
				{
					if (pDvParent != pDVMap)
					{
						__try
						{
							void** pvt = *reinterpret_cast<void***>(pDvParent);
							if (pvt && pvt[0x170 / 4])
							{
								typedef void (__thiscall* DirtyFn)(void*);
								reinterpret_cast<DirtyFn>(pvt[0x170 / 4])(pDvParent);
							}
						}
						__except (EXCEPTION_EXECUTE_HANDLER)
						{
							Logger::Get().WriteLine(LogLevel::Error,
								"UiSpike: DVMAP parent re-dirty FAULTED "
								"(stale ring may remain; report this line).");
						}
					}
				}
				Logger::Get().WriteLine(LogLevel::Info,
					"UiSpike: DVMAP window SNAPPED %dx%d -> %d (terrain %d, "
					"largest exact power-of-two multiple within the x%d bake "
					"ceiling; window==surface now, which is the #109 invariant; "
					"blitSize %d -> %d, zoom now %d).",
					curW, curH, maxBlit, terrainDim,
					CodePatches::MiniMapX8Active() ? 8 : 4, blitBefore,
					*reinterpret_cast<int32_t*>(dvRaw + 0xe4),
					*reinterpret_cast<int32_t*>(dvRaw + 0x104));
			}
		}
		if (pDVMap && pDVMap != lastDataMapSurfResize && pDVMap->GetW() > 256
			&& gDataMapRetry.ShouldAttempt(pDVMap))
		{
			uint8_t* raw = reinterpret_cast<uint8_t*>(pDVMap);
			const int32_t blitSize = *reinterpret_cast<int32_t*>(raw + 0xe4);
			Logger& lg = Logger::Get();
			bool surfOk = false;   // v2.41.0: latch only on success (see MINIMAP)
			lg.WriteLine(LogLevel::Info,
				"UiSpike: DVMAP 2X win %dx%d blitSize=%d ptr=%p parent=0x%08X "
				"— recreating surface",
				pDVMap->GetW(), pDVMap->GetH(), blitSize,
				static_cast<void*>(pDVMap), ParentIdOf(pDVMap));

			// CARRY-OVER (v2.41.14): same defect as the dock minimap - the
			// recreate below blanks a working map. Capture BEFORE the destroy.
			// Note the ceiling: this instance is 256 design, so 512 at 2x fits
			// kCarryMax exactly, but 768 at 3x does NOT and CaptureSurface
			// refuses - the block then falls back to the plain black fill,
			// i.e. exactly the old behaviour. Documented rather than silent.
			int dvOldW = 0, dvOldH = 0;
			CaptureSurface(*reinterpret_cast<void**>(raw + 0xf0), &dvOldW, &dvOldH);
			lg.WriteLine(LogLevel::Info,
				"UiSpike: DVMAP captured old surface %dx%d for carry-over%s",
				dvOldW, dvOldH, (dvOldW > 0) ? "" : " - none, will clear to black");
			__try
			{
				void* oldSurf = *reinterpret_cast<void**>(raw + 0xf0);
				if (oldSurf)
				{
					*reinterpret_cast<void**>(raw + 0xf0) = nullptr;
					void** oldVt = *reinterpret_cast<void***>(oldSurf);
					typedef void (__thiscall* DeleteFn)(void*);
					reinterpret_cast<DeleteFn>(oldVt[2])(oldSurf);
				}
				void* factory = nullptr;
				typedef void* (__cdecl* GetGlobalFn)();
				void* globalObj = reinterpret_cast<GetGlobalFn>(0x008793EC)();
				if (globalObj)
				{
					void** gvt = *reinterpret_cast<void***>(globalObj);
					typedef bool (__thiscall* QIFn)(void*, uint32_t, uint32_t, void**);
					reinterpret_cast<QIFn>(gvt[5])(
						globalObj, 0xC416025C, 0x73283C, &factory);
				}
				if (factory)
				{
					void** fvt = *reinterpret_cast<void***>(factory);
					typedef bool (__thiscall* CreateFn)(void*, void**);
					reinterpret_cast<CreateFn>(fvt[3])(
						factory, reinterpret_cast<void**>(raw + 0xf0));
				}
				void* newSurf = *reinterpret_cast<void**>(raw + 0xf0);
				if (newSurf && blitSize > 0)
				{
					void** nvt = *reinterpret_cast<void***>(newSurf);
					typedef bool (__thiscall* InitFn)(void*, int, int, int, int);
					reinterpret_cast<InitFn>(nvt[3])(
						newSurf, blitSize, blitSize, 9, 32);
					surfOk = true;
					lg.WriteLine(LogLevel::Info,
						"UiSpike: DVMAP new surface created+inited at %dx%d",
						blitSize, blitSize);
				}
				else
				{
					lg.WriteLine(LogLevel::Error,
						"UiSpike: DVMAP surface creation FAILED (factory=%p surf=%p)",
						factory, newSurf);
				}
			}
			__except (EXCEPTION_EXECUTE_HANDLER)
			{
				lg.WriteLine(LogLevel::Error,
					"UiSpike: DVMAP surface recreation FAULTED");
			}
			// Pre-clear (QI for the clean interface vtable, see MINIMAP note).
			{
				void* surfPrimary = *reinterpret_cast<void**>(raw + 0xf0);
				if (surfPrimary)
				{
					__try
					{
						cIGZBuffer* pPrimary = reinterpret_cast<cIGZBuffer*>(surfPrimary);
						cIGZBuffer* pBuf = nullptr;
						if (pPrimary->QueryInterface(GZIID_cIGZBuffer, reinterpret_cast<void**>(&pBuf))
							&& pBuf)
						{
							const uint32_t black = pBuf->ConvertRGBValueToNative(0, 0, 0);
							cRZRect outRect = {};
							pBuf->Fill(black, 0, 0, blitSize, blitSize, &outRect);
							// CARRY-OVER (v2.41.14), same as MINIMAP: black is
							// the floor, then repaint the old picture so the
							// Data Views map does not go blank on expand.
							if (dvOldW > 0 && dvOldH > 0 && blitSize > 0)
							{
								RestoreSurfaceBilinear(pBuf, dvOldW, dvOldH, blitSize);
								lg.WriteLine(LogLevel::Info,
									"UiSpike: DVMAP old picture carried over "
									"%dx%d -> %dx%d bilinear.",
									dvOldW, dvOldH, blitSize, blitSize);
							}
							pBuf->Release();
						}
					}
					__except (EXCEPTION_EXECUTE_HANDLER) {}
				}
			}
			// Per-size recompute + dirty flags (game's own 0x7A7840; manual
			// fallback mirrors the MINIMAP block).
			if (blitSize > 0)
			{
				__try
				{
					typedef void (__thiscall* RecomputeFn)(void*);
					reinterpret_cast<RecomputeFn>(0x007A7840)(pDVMap);
					// v2.71.1 BORN CORRECT (#121 last 1%): the recompute only
					// MARKS every tile dirty (memset 0xFF at 0x7A78E2) and sets
					// fd=1; the actual bake is MESSAGE-DRIVEN via the handler
					// 0x7A8640, so it lands a tick or more later - the user sees
					// the panel open, then the map fill in. STOCK never shows
					// that gap (user-verified 2026-08-04: stock paints the
					// correct map immediately) because its map is built right
					// before it is shown, while ours is rescaled + recreated
					// after creation. Cure = the project's standing one: do the
					// work while HIDDEN. Drive the game's own bake synchronously
					// right here, on the same object and thread the handler
					// would use (0x7A8721), so the raster is full before the
					// first paint. Idempotent: the bake clears the dirty mask
					// itself, so the later message finds nothing to do.
					DriveMiniMapBake(pDVMap, "dvmap-recreate");
					lg.WriteLine(LogLevel::Info,
						"UiSpike: DVMAP recompute 0x7A7840 ok zoom=%d fd=%d fe=%d "
						"| x8bake=%s blits=%d clips=%d",
						*reinterpret_cast<int32_t*>(raw + 0x104),
						(int)raw[0xfd], (int)raw[0xfe],
						// law 47: installed != executed. zoom=-3 with blits
						// climbing = a real terrain base is being baked at
						// full size. zoom=-3 with blits STUCK AT 0 means the
						// write took but the path never runs. clips>0 = the
						// blitSize is not an exact power-of-two multiple of
						// the terrain dim (the #109 family) - safe, but the
						// sizing policy leaked and wants fixing.
						CodePatches::MiniMapX8Active() ? "live" : "off",
						CodePatches::MiniMapX8Blits(),
						CodePatches::MiniMapX8Clips());
				}
				__except (EXCEPTION_EXECUTE_HANDLER)
				{
					lg.WriteLine(LogLevel::Error,
						"UiSpike: DVMAP 0x7A7840 FAULTED - manual fallback");
					__try
					{
						typedef bool (__thiscall* CreateBufFn)(void*, int, int);
						reinterpret_cast<CreateBufFn>(0x007A7570)(
							raw + 0x114, blitSize, blitSize);
					}
					__except (EXCEPTION_EXECUTE_HANDLER) {}
					int32_t mapW = 0;
					__try
					{
						void* terrain = *reinterpret_cast<void**>(0x00B43CEC);
						if (terrain)
						{
							void** tvt = *reinterpret_cast<void***>(terrain);
							typedef int (__thiscall* GetDimFn)(void*);
							mapW = reinterpret_cast<GetDimFn>(tvt[0x174 / 4])(terrain);
						}
					}
					__except (EXCEPTION_EXECUTE_HANDLER) {}
					if (mapW > 0)
					{
						int32_t zoom = 0, dim = mapW;
						while (dim > blitSize) { dim >>= 1; zoom++; }
						while (dim < blitSize) { dim <<= 1; zoom--; }
						*reinterpret_cast<int32_t*>(raw + 0x104) = zoom;
					}
					raw[0xfd] = 1;
					raw[0xfe] = 1;
				}
			}
			// Bounded retry, same policy as MINIMAP (v2.41.0, task #89).
			if (surfOk)
			{
				lastDataMapSurfResize = pDVMap;
				// v2.69.4: arm the first-visible re-kick (see the latch note
				// at its declaration). The load-time recompute above ran while
				// the panel is hidden; this re-fires it when the map can
				// actually paint.
				gDvMapVisibleKick = pDVMap;
			}
			else
			{
				gDataMapRetry.NoteFail();
				if (gDataMapRetry.Exhausted())
				{
					lastDataMapSurfResize = pDVMap;
					lg.WriteLine(LogLevel::Error,
						"UiSpike: DVMAP surface recreate failed %d time(s) - "
						"giving up on this instance.", kSurfMaxAttempts);
				}
				else
				{
					lg.WriteLine(LogLevel::Info,
						"UiSpike: DVMAP surface recreate failed - will RETRY "
						"(attempt %d of %d).", gDataMapRetry.fails, kSurfMaxAttempts);
				}
			}
			pDVMap->InvalidateSelf();
		}

		// v2.69.4: the first-visible DVMAP kick (armed by the recreate above).
		// One pointer compare per sweep in the steady state; the recompute
		// re-fires exactly once, the first sweep the map is on screen - which
		// is when the game's renderer can actually rebuild the terrain base
		// this map composites data onto. The window pointer is validated by
		// re-finding it (never dereference the latch blindly: the panel can
		// be torn down between sweeps).
		if (gDvMapVisibleKick)
		{
			cIGZWin* pKickRoot = pRoot->GetChildWindowFromID(kGZWin_MenuContainer);
			cIGZWin* pKick = pKickRoot
				? pKickRoot->GetChildWindowFromIDRecursive(0x00004203) : nullptr;
			if (pKick != gDvMapVisibleKick)
			{
				// The instance the latch was armed for is gone (panel rebuilt
				// or city changed under us). Drop the latch; a new recreate
				// will re-arm it for the new instance.
				gDvMapVisibleKick = nullptr;
			}
			else if (IsOnScreen(pKick))
			{
				gDvMapVisibleKick = nullptr;
				__try
				{
					typedef void (__thiscall* RecomputeFn)(void*);
					reinterpret_cast<RecomputeFn>(0x007A7840)(pKick);
					DriveMiniMapBake(pKick, "dvmap-kick");   // v2.71.1, see above
					pKick->InvalidateSelf();
					const int32_t kzoom = *reinterpret_cast<int32_t*>(
						reinterpret_cast<uint8_t*>(pKick) + 0x104);
					Logger::Get().WriteLine(LogLevel::Info,
						"UiSpike: DVMAP first-visible kick - recompute re-fired "
						"while the map can paint (zoom=%d fd=%d fe=%d).",
						kzoom,
						(int)reinterpret_cast<uint8_t*>(pKick)[0xfd],
						(int)reinterpret_cast<uint8_t*>(pKick)[0xfe]);
					// v2.69.5 armed the dock-seed here when zoom <= -3; it was
					// retired in v2.71.4 (see the tombstone at the latch
					// declarations). The kick now just re-fires the recompute
					// and the synchronous bake - at every zoom.
				}
				__except (EXCEPTION_EXECUTE_HANDLER)
				{
					Logger::Get().WriteLine(LogLevel::Error,
						"UiSpike: DVMAP first-visible kick FAULTED (map may "
						"stay black; report this line).");
				}
			}
		}

		// U-DRIVE-IT DASHBOARD MINIMAP (task #46 part 2, v2.21.5): the
		// driving console script (root 0x4BCB938A, I-0bec56c1 family)
		// embeds a THIRD cSC4WinMiniMap instance - clsid 0xca318388 with
		// THE SAME window id as the dock minimap (0x0BC3B559, 64x64
		// design). Once the sweep doubles the console, this instance needs
		// the same one-shot-surface recreate as the dock (MINIMAP block
		// above) and the Data Views map (DVMAP): without it the map draws
		// its 1x surface in a black 2x hole - and the DVMAP crash taught us
		// what a stale surface can do when a renderer goes window-sized.
		// Scoped search under the DASHBOARD root so the global dock search
		// (which returns its own first match) cannot shadow it.
		// lastUdMapSurfResize lives at namespace scope (v2.23.3): Disarm
		// NULLs it so a second city reusing the freed address still re-fires.
		cIGZWin* pUdRoot = pRoot->GetChildWindowFromIDRecursive(0x4BCB938A);
		// #93 UDVAR: the console VARIANT 0xEC1A5CBF has never been seen live
		// - no dump in the repo holds it - so "which vehicle spawns it" has
		// been an open question for weeks. Rather than making the user cycle
		// every vehicle type against a DPROBE band, let it report ITSELF the
		// first time it ever exists: id, rect, parent, and whether it is a
		// SIBLING of the dashboard or a CHILD of it (the one fact that
		// decides which half of its insurance is doing the work). One line
		// per session, and the search only runs while a U-Drive-It console
		// is actually up, so it costs nothing in the common case.
		if (pUdRoot != nullptr && !gUdVarSeen)
		{
			cIGZWin* pUdVar = pRoot->GetChildWindowFromIDRecursive(0xEC1A5CBF);
			if (pUdVar != nullptr)
			{
				gUdVarSeen = true;
				const bool underDash =
					(pUdRoot->GetChildWindowFromIDRecursive(0xEC1A5CBF) != nullptr);
				// rel, not abs: AbsoluteTopLeft is defined further down this
				// file, and the parent id below identifies the frame anyway.
				const int32_t vl = pUdVar->GetL(), vt = pUdVar->GetT();
				Logger::Get().WriteLine(LogLevel::Info,
					"UiSpike: UDVAR 0xEC1A5CBF SIGHTED - rel(%d,%d) %dx%d "
					"vis=%d parent=0x%08X %s dashboard 0x4BCB938A. Design is "
					"463x132: %dx%d means %s. RECORD THE VEHICLE/MODE ON "
					"SCREEN NOW - this closes #93.",
					vl, vt, pUdVar->GetW(), pUdVar->GetH(),
					pUdVar->IsVisible() ? 1 : 0, ParentIdOf(pUdVar),
					underDash ? "INSIDE the" : "SIBLING of the",
					pUdVar->GetW(), pUdVar->GetH(),
					(pUdVar->GetW() >= 900) ? "born/scaled 2x (insured)"
											: "still 1x - insurance did NOT take");
			}
		}
		cIGZWin* pUdMap = pUdRoot
			? pUdRoot->GetChildWindowFromIDRecursive(0x0BC3B559) : nullptr;
		// v2.73.0 (#126): the U-Drive-It twin gets the DRAW HOOK, not the snap -
		// same reasoning as the dock (it is not on the #109 chain either, which
		// resolves id 0x4203 exclusively).
		if (pUdMap && pUdMap->GetW() > 64) { SnapMiniMapToBake(pUdMap, "UDMAP"); }
		if (pUdMap) { HookMiniMapDraw(pUdMap, "UDMAP"); }
		if (pUdMap && pUdMap != lastUdMapSurfResize && pUdMap->GetW() > 64
			&& gUdMapRetry.ShouldAttempt(pUdMap))
		{
			uint8_t* raw = reinterpret_cast<uint8_t*>(pUdMap);
			const int32_t blitSize = *reinterpret_cast<int32_t*>(raw + 0xe4);
			Logger& lg = Logger::Get();
			bool surfOk = false;   // v2.41.0: latch only on success (see MINIMAP)
			lg.WriteLine(LogLevel::Info,
				"UiSpike: UDMAP 2X win %dx%d blitSize=%d ptr=%p parent=0x%08X "
				"— recreating surface",
				pUdMap->GetW(), pUdMap->GetH(), blitSize,
				static_cast<void*>(pUdMap), ParentIdOf(pUdMap));

			// CARRY-OVER (v2.41.14). ⚠ UDMAP was the ONE block with NO
			// pre-clear at all, so it never even had the black floor - a fresh
			// surface here could show uninitialised VRAM outright. It now gets
			// both: the black floor AND the carried-over picture.
			int udOldW = 0, udOldH = 0;
			CaptureSurface(*reinterpret_cast<void**>(raw + 0xf0), &udOldW, &udOldH);
			lg.WriteLine(LogLevel::Info,
				"UiSpike: UDMAP captured old surface %dx%d for carry-over%s",
				udOldW, udOldH, (udOldW > 0) ? "" : " - none, will clear to black");
			__try
			{
				void* oldSurf = *reinterpret_cast<void**>(raw + 0xf0);
				if (oldSurf)
				{
					*reinterpret_cast<void**>(raw + 0xf0) = nullptr;
					void** oldVt = *reinterpret_cast<void***>(oldSurf);
					typedef void (__thiscall* DeleteFn)(void*);
					reinterpret_cast<DeleteFn>(oldVt[2])(oldSurf);
				}
				void* factory = nullptr;
				typedef void* (__cdecl* GetGlobalFn)();
				void* globalObj = reinterpret_cast<GetGlobalFn>(0x008793EC)();
				if (globalObj)
				{
					void** gvt = *reinterpret_cast<void***>(globalObj);
					typedef bool (__thiscall* QIFn)(void*, uint32_t, uint32_t, void**);
					reinterpret_cast<QIFn>(gvt[5])(
						globalObj, 0xC416025C, 0x73283C, &factory);
				}
				if (factory)
				{
					void** fvt = *reinterpret_cast<void***>(factory);
					typedef bool (__thiscall* CreateFn)(void*, void**);
					reinterpret_cast<CreateFn>(fvt[3])(
						factory, reinterpret_cast<void**>(raw + 0xf0));
				}
				void* newSurf = *reinterpret_cast<void**>(raw + 0xf0);
				if (newSurf && blitSize > 0)
				{
					void** nvt = *reinterpret_cast<void***>(newSurf);
					typedef bool (__thiscall* InitFn)(void*, int, int, int, int);
					reinterpret_cast<InitFn>(nvt[3])(
						newSurf, blitSize, blitSize, 9, 32);
					surfOk = true;
					lg.WriteLine(LogLevel::Info,
						"UiSpike: UDMAP new surface created+inited at %dx%d",
						blitSize, blitSize);
				}
				else
				{
					// v2.41.0: UDMAP was the only one of the three with no
					// failure branch at all - a null factory or surface was
					// completely silent, so the one case the retry needs to
					// see could not be seen.
					lg.WriteLine(LogLevel::Error,
						"UiSpike: UDMAP surface creation FAILED (factory=%p surf=%p)",
						factory, newSurf);
				}
			}
			__except (EXCEPTION_EXECUTE_HANDLER)
			{
				lg.WriteLine(LogLevel::Error,
					"UiSpike: UDMAP surface recreation FAULTED");
			}
			// Pre-clear + carry-over (v2.41.14). This block is NEW here: UDMAP
			// previously had NEITHER, so its fresh surface could show
			// uninitialised VRAM outright. Black first as the floor, then the
			// old picture on top. Mirrors MINIMAP/DVMAP exactly.
			{
				void* surfPrimary = *reinterpret_cast<void**>(raw + 0xf0);
				if (surfPrimary)
				{
					__try
					{
						cIGZBuffer* pPrimary = reinterpret_cast<cIGZBuffer*>(surfPrimary);
						cIGZBuffer* pBuf = nullptr;
						if (pPrimary->QueryInterface(GZIID_cIGZBuffer, reinterpret_cast<void**>(&pBuf))
							&& pBuf)
						{
							const uint32_t black = pBuf->ConvertRGBValueToNative(0, 0, 0);
							cRZRect outRect = {};
							pBuf->Fill(black, 0, 0, blitSize, blitSize, &outRect);
							if (udOldW > 0 && udOldH > 0 && blitSize > 0)
							{
								RestoreSurfaceBilinear(pBuf, udOldW, udOldH, blitSize);
								lg.WriteLine(LogLevel::Info,
									"UiSpike: UDMAP old picture carried over "
									"%dx%d -> %dx%d bilinear.",
									udOldW, udOldH, blitSize, blitSize);
							}
							else
							{
								lg.WriteLine(LogLevel::Debug,
									"UiSpike: UDMAP surface pre-cleared to black "
									"(first pre-clear this block has ever had).");
							}
							pBuf->Release();
						}
					}
					__except (EXCEPTION_EXECUTE_HANDLER)
					{
						lg.WriteLine(LogLevel::Error,
							"UiSpike: UDMAP pre-clear/carry-over FAULTED.");
					}
				}
			}
			// Recompute + dirty flags (game's own 0x7A7840, as MINIMAP/DVMAP).
			if (blitSize > 0)
			{
				__try
				{
					typedef void (__thiscall* RecomputeFn)(void*);
					reinterpret_cast<RecomputeFn>(0x007A7840)(pUdMap);
					lg.WriteLine(LogLevel::Info,
						"UiSpike: UDMAP recompute 0x7A7840 ok zoom=%d fd=%d fe=%d",
						*reinterpret_cast<int32_t*>(raw + 0x104),
						(int)raw[0xfd], (int)raw[0xfe]);
				}
				__except (EXCEPTION_EXECUTE_HANDLER)
				{
					raw[0xfd] = 1;
					raw[0xfe] = 1;
				}
			}
			// Bounded retry, same policy as MINIMAP (v2.41.0, task #89).
			if (surfOk)
			{
				lastUdMapSurfResize = pUdMap;
			}
			else
			{
				gUdMapRetry.NoteFail();
				if (gUdMapRetry.Exhausted())
				{
					lastUdMapSurfResize = pUdMap;
					lg.WriteLine(LogLevel::Error,
						"UiSpike: UDMAP surface recreate failed %d time(s) - "
						"giving up on this instance.", kSurfMaxAttempts);
				}
				else
				{
					lg.WriteLine(LogLevel::Info,
						"UiSpike: UDMAP surface recreate failed - will RETRY "
						"(attempt %d of %d).", gUdMapRetry.fails, kSurfMaxAttempts);
				}
			}
			pUdMap->InvalidateSelf();
		}

		// U-DRIVE-IT GAUGE DIALS (task #47, v2.23.0). Same dashboard root as
		// UDMAP above, but a completely different mechanism: the dial control
		// (class 0xCBCBF1E0) holds no buffer to recreate - it blits its strip
		// straight to the draw context with a DEST rect sized from the ART. See
		// the long note on the GAUGE namespace above ScalePanelsUnder for the
		// measurement. Hook is scoped under 0x4BCB938A, class-verified per
		// instance, per-instance vtable copy, pointer-latched.
		HookDashboardGauges(pRoot, f);

		// RUNTIME-SUPPLIED GZWinBMP IMAGES (task #47, v2.25.0): the My Sims
		// family's portraits are Path-4 runtime bitmaps (36x41, in no dat) -
		// GZWinBMP draws dst = src size, so they sat 1x in doubled slots. Hook
		// the class draw for every GZWinBMP under the family roots (see the
		// BMPX namespace note above ScalePanelsUnder). Self-limiting: BMPs
		// whose art is already 2x clamp to m=1.0 and draw untouched.
		{
			static const uint32_t kBmpxCityRoots[] = {
				0x698894D3, 0xCA1F1D9C, 0xAA1F1EC5,   // My Sims catalog roots
				0xEA1F1E4D, 0x6A61E29F, 0xABBAA2D3,   // Sim detail strips
				0xEA1F1E4E, 0xEA1F1E5E,               // find-sim / evict
				// GRAPHS panel roots (intake bug 6, measured offline
				// 2026-07-30): the "stale duplicate script" theory is DEAD -
				// the two scripts are DIFFERENT panels, both staged, and every
				// art ref in both is 2x-in-place (refmap-verified). The three
				// roots' children are all standard GZWinBMP/Btn/Text; the
				// chart itself is controller-painted at runtime. Hooking the
				// BMPs here is self-limiting insurance: correct 2x draws
				// clamp to m=1.0, only content actually smaller than its
				// window is stretched. The chart line proper still needs the
				// live DPROBE pass if this leaves it 1x.
				0x8A8B5B71, 0x8A8B5B72, 0x0A4A8176,
				// #191 MOVE IN MY SIM MARKER - the framed sim face + arrow that
				// floats over a candidate house. A WINDOW PAIR, both parented
				// directly to the 3D-view root 0x9A47B417, each with two
				// GZWinBMP children (the 46x97 plate, and the 36x41 portrait
				// 0xEA9457BA at (5,5)):
				//     0x27DF05BE  green arrow - sits on the target house
				//     0x27DF05BF  red arrow   - follows the mouse
				// Art: {46a006b0,13f15213} green / {46a006b0,13f15214} red.
				//
				// THE SWEEP ALREADY RESIZES THEM. Measured, tier 2.00:
				//     panel 0x27DF05BE (531,375 46x97) -> (1062,750 92x194)
				//     "3 windows scaled", portrait child -> (10,10) 72x82
				// and it HOLDS at 92x194 for the rest of the session. The
				// geometry was never the problem.
				//
				// ⭐ THEY DREW 1x ANYWAY BECAUSE A GZWinBMP DRAWS dst = src
				// (law 83 / the BMPX rationale at :11655) and these roots were
				// not in this list, so the blit hook never ran on them. A
				// window at 92x194 showing a 46x97 source is exactly the user's
				// "identical instead of scaling", and it is why FIVE patches
				// aimed at sizes and constants could not move it - the size was
				// already right and the BLIT was not following.
				//
				// ⛔ THE "IT IS NOT A WINDOW" VERDICT WAS A FALSE NULL OF MY
				// OWN MAKING. The 37-dump test compared the last 8 dumps
				// against the FIRST FIVE - and these windows first appear in
				// dump #5, so the things being hunted were absorbed into the
				// test's own baseline. They are never destroyed either: they
				// persist in the view's child list and merely toggle vis, and a
				// "no NEW ids" test is structurally blind to a resident
				// show/hide widget. The positive control (the picker grid
				// appearing for one tick) proved the dump sees TRANSIENTS; it
				// never proved it could see THIS.
				// ⭐ LAW: A DIFF NEEDS A BASELINE TAKEN BEFORE THE THING
				// EXISTS. State when the target first appears relative to the
				// window the baseline covers, or the diff hides it.
				0x27DF05BE, 0x27DF05BF,
				// U-DRIVE-IT MISSION MARKER (task #60, v2.36.6). MEASURED live
				// 2026-07-30 22:23 with markers on screen, after TWO dead leads
				// (the 4x-art attempt at {46a006b0,094ac89a}, and the
				// "15-entry glyph table" that turned out to be a registration
				// table for spinner/slider art):
				//   EDGE bubble 0x48E945B4 PRESENT
				//   EDGE   bubble rect (1637,610 128x128) vis=1 vt=00ADF6A0
				// vt 0x00ADF6A0 IS the GZWinBMP class this very hook serves, so
				// the marker was always reachable - it simply sat under no
				// listed root (it parents straight to the 3D view) and was
				// never hooked. It is also TRANSIENT: present in one sample and
				// gone 0.5s later, which is why every earlier static approach
				// missed it. The sweep re-finds it by id whenever it exists.
				// WHY THIS GIVES EXACTLY WHAT WAS ASKED ("2x their current
				// size"): the draw follows the SOURCE, so a 32px art draws 32px
				// in a 128px window; BmpCtxBltThunk scales the dest by the tier
				// factor (2.0) and then REDUCES it until it still fits the live
				// window - 64x64 inside 128x128 fits, so it lands at exactly
				// 2x, and the fit rule makes overshoot structurally impossible.
				0x48E945B4,
			};
			HookRuntimeBmpsUnder(pRoot, kBmpxCityRoots,
				static_cast<int>(std::size(kBmpxCityRoots)), f, "city");

			// ---- #57 CHARTGEO: READ the chart's own layout fields --------
			// PURE READ, no writes, no hooks. Offline disassembly located the
			// layout driver sub_9B3647 -> sub_9B799D (main vt +0x2B0), which
			// stores the plot rect via sub_9B1F1D into chart+0xE0..0xEF, and
			// said the legend is a full-width TOP BAND (chart+0x108..0x114,
			// height chart+0x120 = hard 32) with an unconditional right
			// margin of W-16. OUR SCREENSHOTS SHOW A RIGHT-HAND LEGEND
			// COLUMN. One of those is wrong, and designing a fix on the
			// wrong one wastes a build - so read the real numbers.
			// The chart IS the cIGZWin (its ctor writes the main vtable at
			// offset 0 and cIGZWin slot +0xDC is its SetArea override), so a
			// child of the Graphs root whose vptr is one of the three known
			// chart vtables IS the chart object.
			// v2.53.1: the gate is the SCALE FLAG, not the log cap. The user
			// PROVED (green-probe run) that switching graphs REPLACES the
			// chart object, so the scale must run for every NEW chart, every
			// sweep - nesting it under the 4-line log cap would silently stop
			// scaling after the fourth sighting. The log lines keep their own
			// cap inside.
			if (gChartGeoLog < 4 || gChartScale || gChartProbe)
			{
				// v2.54.0: install the born-correct store thunk the first
				// time we are here with the tier known. Idempotent latch.
				// v2.55.0: ARM THE COUPLED PAIR. EARLYCHART owns the plot's
				// right margin; the byte patch owns the legend strip that
				// margin has to clear. Arming one without the other is the
				// oracle's H-EARLYCHART candidate - it paints the plot border
				// INSIDE the checkbox column - so both go in here, behind the
				// one ChartScale flag. The applier verifies all eight sites
				// before writing any, so a declined patch simply leaves
				// EARLYCHART on its old proportional margin with the sweep
				// fallback still live.
				if (gChartScale && f > 1.01f)
				{
					InstallChartBornScale();
					if (!gGraphBudgetArmed)
					{
						gGraphBudgetArmed = true;
						CodePatches::ApplyGraphLegendBudgetScale(f);
					}
				}
				cIGZWin* gRoot =
					pRoot->GetChildWindowFromIDRecursive(0x8A8B5B71);
				if (gRoot != nullptr)
				{
					ChildSnapshot ck = {};
					gRoot->EnumChildren(GZIID_cIGZWin,
						ChildSnapshot::Callback, &ck);
					// v2.54.1 GKID: the MULTI-SERIES legend (Garbage etc)
					// is checkbox WINDOWS in the root's right margin, and
					// they wrap their captions - dump every child that
					// starts right of the chart window (design x >= 500,
					// i.e. 2x >= 1000) so the barrier is a measured rect.
					if (gChartLegendLog < 3)
					{
						for (int gi = 0; gi < ck.count; gi++)
						{
							cIGZWin* g = ck.wins[gi];
							if (!g || g->GetL() < RoundHalfUp(500 * f))
							{
								continue;
							}
							Logger::Get().WriteLine(LogLevel::Debug,
								"UiSpike: GKID id=0x%08X (%d,%d %dx%d) "
								"vis=%d vt=%08X",
								g->GetID(), g->GetL(), g->GetT(),
								g->GetW(), g->GetH(),
								g->IsVisible() ? 1 : 0,
								*reinterpret_cast<uint32_t*>(g));
						}
					}
					for (int ci = 0; ci < ck.count; ci++)
					{
						cIGZWin* c = ck.wins[ci];
						if (!c) { continue; }
						const uint32_t vt = *reinterpret_cast<uint32_t*>(c);
						if (vt != 0x00AB4D08 && vt != 0x00ADE648
							&& vt != 0x00ADEEC0) { continue; }
						const int32_t* fld =
							reinterpret_cast<const int32_t*>(c);
						// log lines keep their own 4-cap; the SCALE below
						// runs regardless (see the gate comment above).
						const bool logThis = (gChartGeoLog < 4);
						if (logThis) gChartGeoLog++;
						if (logThis) Logger::Get().WriteLine(LogLevel::Debug,
							"UiSpike: CHARTGEO vt=%08X id=0x%08X  "
							"WIN[0xA8](%d,%d,%d,%d) %dx%d  "
							"PLOT[0xE0](%d,%d,%d,%d)  "
							"LEGEND[0x108](%d,%d,%d,%d) bandH[0x120]=%d  "
							"tickLen[0x180]=%d,%d  f=%.2f",
							vt, c->GetID(),
							fld[0xA8/4], fld[0xAC/4], fld[0xB0/4], fld[0xB4/4],
							fld[0xB0/4] - fld[0xA8/4],
							fld[0xB4/4] - fld[0xAC/4],
							fld[0xE0/4], fld[0xE4/4], fld[0xE8/4], fld[0xEC/4],
							fld[0x108/4], fld[0x10C/4], fld[0x110/4],
							fld[0x114/4], fld[0x120/4],
							fld[0x180/4], fld[0x184/4], f);

						// ---- #57 PHASE 1a: the fields that decide it -----
						// ⚠ The painters use cIGZWin+0x24 (LOCAL rect), NOT
						// +0xA8 - the line above is kept for continuity with
						// yesterday's captures, but +0x24 is the one the
						// paint path actually reads (sub_9B38A5:
						// lea esi,[ebx+0x24] then movsd x4).
						if (logThis) Logger::Get().WriteLine(LogLevel::Debug,
							"UiSpike: CHARTDIAG local[0x24](%d,%d,%d,%d)  "
							"offscreen[0x64]=%08X  dirty[0x70]=%d  "
							"outerFill[0x128]=%08X en[0x12C]=%d  "
							"plotFill[0x134]=%d col[0x138]=%08X  "
							"bgImg[0x144]=%08X plotImg[0x148]=%08X",
							fld[0x24/4], fld[0x28/4], fld[0x2C/4], fld[0x30/4],
							static_cast<uint32_t>(fld[0x64/4]),
							reinterpret_cast<const uint8_t*>(c)[0x70],
							static_cast<uint32_t>(fld[0x128/4]),
							reinterpret_cast<const uint8_t*>(c)[0x12C],
							reinterpret_cast<const uint8_t*>(c)[0x134],
							static_cast<uint32_t>(fld[0x138/4]),
							static_cast<uint32_t>(fld[0x144/4]),
							static_cast<uint32_t>(fld[0x148/4]));

						// ---- #57 PHASE 1b/1c: POKE GREEN, THEN TRIGGER ---
						if (gChartProbe && c != gChartProbed)
						{
							uint8_t*  b8 = reinterpret_cast<uint8_t*>(c);
							uint32_t* b32 = reinterpret_cast<uint32_t*>(c);
							// The poke only shows if no plot BACKGROUND IMAGE
							// is set - ctor default is 0. Verify, never assume.
							const bool pokeOk = (b32[0x148/4] == 0);
							if (pokeOk)
							{
								b8[0x134] = 1;              // plot fill ON
								b32[0x138/4] = 0xFF00FF00;  // opaque green
							}
							// vt+0x170 = sub_99BED1: SetDirty + propagate to
							// ancestors. __thiscall, zero args, no return.
							// This is what the game itself calls after every
							// chart mutation - NOT InvalidateSelfAndParents,
							// which never reached the dirty gate at +0x70.
							typedef void(__thiscall* DirtyFn)(void*);
							void** cvt = *reinterpret_cast<void***>(c);
							if (cvt && cvt[0x170 / 4])
							{
								reinterpret_cast<DirtyFn>(cvt[0x170 / 4])(c);
							}
							gChartProbed = c;
							Logger::Get().WriteLine(LogLevel::Debug,
								"UiSpike: CHARTPROBE poke=%d (plotImg=%08X) "
								"-> plot fill green + vt[0x170] SetDirty. "
								"EXPECT: the plot area floods GREEN in exactly "
								"PLOT[0xE0]. If it does NOT, the window never "
								"reaches the draw - stop trying fields and go "
								"to the +0x64/pbuff path (law 46).",
								pokeOk ? 1 : 0,
								static_cast<uint32_t>(b32[0x148/4]));
						}

						// ---- #57 v2.54.1: LEGEND RECON, steady state -----
						// The first-layout LEGENDOBJ dump came back EMPTY -
						// the legend entries are bound AFTER first paint. And
						// the Garbage screenshot showed the multi-series
						// legend has CHECKBOXES = real WINDOWS in the root's
						// right margin, not chart paint. Two legends, two
						// mechanisms; dump both here at steady state.
						// LEGENDFIX v2.54.4 - now MEASURED against two stock 1024x768
						// captures (graphs-stock-ref.png = Income/Expenses,
						// graphs-stock-garbage.png = the multi-series kind). Stock
						// columns, absolute px:
						//   Income/Expenses:            swatch 895..904  text 910..951
						//   Garbage: cbox 893..908      swatch 911..920  text 925..993
						// Entry objects on the list at chart+0x228 (text first, then
						// its swatch):
						//   vt 00ADE540 = TEXT BLOCK. String vector obj[3..5], RECT
						//     obj[7..10]. Live at 2x: (884,20,972,76) = width 88,
						//     right edge winW-4. That IS 2x of stock's 44 - the game
						//     scales this one. But 26pt Arta is WIDER than 2x 13pt
						//     (metrics do not scale linearly), so the proportional
						//     box marginally fails and "Expenses" wraps where stock
						//     fits with 2px to spare.
						//   vt 00ADE0DC = SWATCH. RECT obj[2..5]. Live at 2x:
						//     (870,23,880,29) = 10 wide, 6 tall, 14px left of the
						//     text. Stock 1x is 10 wide, 6 tall, 15px left of the
						//     text -> the swatch is the ONE element the game never
						//     scales. It should be 20x12 at offset 28.
						// This is why v2.54.3 killed the colour: the checkbox WINDOW
						// is a real child that our own sweep already scales correctly
						// (stock local L = textL-32 -> 2x gives textL-64), so moving
						// it slid a correct element on top of the broken one. The
						// checkbox move is REVERTED here - and with it the window
						// motion that brought the switch-charts jump back.
						// Fix, by legend kind:
						//   plain (no checkboxes): the whole right margin is free, so
						//     keep the user-confirmed leftward text widening.
						//   checkbox: the column is already laid out; widen RIGHT
						//     only (the spare 4px) and move no window.
						//   both: scale the swatch - size x f and offset-from-text
						//     x f - so the dash is 2x and sits in the 2x gap.
						if (gChartScale && f > 1.01f)
						{
							uint8_t* cb = reinterpret_cast<uint8_t*>(c);
							uint32_t* head = reinterpret_cast<uint32_t*>(
								*reinterpret_cast<uintptr_t*>(cb + 0x228));
							uint32_t* node = head
								? reinterpret_cast<uint32_t*>(
									static_cast<uintptr_t>(head[0]))
								: nullptr;
							const int32_t winW2 = reinterpret_cast<int32_t*>(
								c)[0x2C/4] - reinterpret_cast<int32_t*>(c)[0x24/4];
							const int32_t plotR = reinterpret_cast<int32_t*>(c)[0xE8/4];
							// Per-series checkboxes are real children of the chart,
							// parked in the right margin (right of the plot).
							bool hasBoxes = false;
							{
								ChildSnapshot lk = {};
								c->EnumChildren(GZIID_cIGZWin,
									ChildSnapshot::Callback, &lk);
								for (int li = 0; li < lk.count; li++)
								{
									cIGZWin* k = lk.wins[li];
									if (!k || k->GetL() <= plotR) { continue; }
									hasBoxes = true;
									// RECON, capped: the real column, so any residual
									// is measured next round instead of guessed.
									if (gChartReconLog < 14)
									{
										gChartReconLog++;
										Logger::Get().WriteLine(LogLevel::Debug,
											"UiSpike: LEGENDCBOX id=0x%08X "
											"rect=(%d,%d,%d,%d) plotR=%d winW=%d",
											k->GetID(), k->GetL(), k->GetT(),
											k->GetR(), k->GetB(), plotR, winW2);
									}
								}
							}
							// text-box left edge of the row we are inside, before and
							// after our own widening, so the swatch can be re-hung off
							// it proportionally. -1 = no text row seen yet.
							int32_t rowTextL0 = -1;
							int32_t rowTextL1 = -1;
							bool fixed = false;
							int guard = 0;
							while (node && node != head && guard++ < 24)
							{
								int32_t* obj = reinterpret_cast<int32_t*>(
									static_cast<uintptr_t>(node[2]));
								// ⛔ LOG BEFORE THE GATE. The accept path below is
								// an EXACT equality (obj[9] == winW2-4) plus a
								// non-empty-width test. Any row that misses either
								// keeps its stock geometry and is never
								// repositioned - and until now that produced NO log
								// line whatsoever, so a silently-declined row was
								// indistinguishable from a row that was never
								// visited. That is the shape of the reported
								// defect: a legend row present with checkbox and
								// swatch but no caption in view.
								if (gChartNodeLog < 48)
								{
									gChartNodeLog++;
									const char* why = "ACCEPT";
									if (!obj) { why = "skip: node has no object"; }
									else if (static_cast<uint32_t>(obj[0]) != 0x00ADE540u)
									{ why = "skip: not a text block (vtable)"; }
									else if (obj[9] != winW2 - 4)
									{ why = "skip: right edge != winW-4"; }
									else if (obj[7] <= 0)
									{ why = "skip: left <= 0"; }
									else if (obj[7] >= obj[9])
									{ why = "skip: EMPTY WIDTH (left >= right)"; }
									Logger::Get().WriteLine(LogLevel::Info,
										"UiSpike: LEGENDNODE #%d vt=0x%08X "
										"L=%d T=%d R=%d B=%d textL=%d textR=%d "
										"winW=%d plotR=%d -> %s",
										guard, obj ? static_cast<uint32_t>(obj[0]) : 0u,
										obj ? obj[2] : 0, obj ? obj[3] : 0,
										obj ? obj[4] : 0, obj ? obj[5] : 0,
										obj ? obj[7] : 0, obj ? obj[9] : 0,
										winW2, plotR, why);
									// ⛔ DUMP THE RAW FIELDS - DO NOT GUESS AGAIN.
									// The L/T/R/B above came back as garbage
									// (11012112 / 2017652148), so obj[2..5] are
									// NOT a rect for this class, and the object's
									// VERTICAL extent - the whole subject of the
									// reported defect, a caption landing below the
									// visible band - has never been located.
									// Guessing offsets a second time is exactly how
									// the minimap cost an hour and five dead
									// theories; print the fields and READ them.
									// obj[7]/obj[9] are known-good (textL/textR)
									// and serve as the landmark for the rest.
									if (obj)
									{
										char fbuf[320] = {};
										int fo = 0;
										for (int fi = 0; fi < 20 && fo < 285; fi++)
										{
											fo += _snprintf_s(fbuf + fo,
												sizeof(fbuf) - fo, _TRUNCATE,
												"[%d]=%d ", fi, obj[fi]);
										}
										Logger::Get().WriteLine(LogLevel::Info,
											"UiSpike: LEGENDRAW #%d %s", guard, fbuf);
									}
								}
								if (obj && static_cast<uint32_t>(obj[0]) == 0x00ADE540u
									&& obj[9] == winW2 - 4
									&& obj[7] > 0 && obj[7] < obj[9])
								{
									const int32_t w0 = obj[9] - obj[7];
									rowTextL0 = obj[7];
									obj[9] = winW2;      // marker + the spare 4px
									if (!hasBoxes)
									{
										obj[7] = obj[9] - RoundHalfUp(w0 * f);
									}
									rowTextL1 = obj[7];
									fixed = true;
									if (gChartLegendLog < 6)
									{
										gChartLegendLog++;
										Logger::Get().WriteLine(LogLevel::Info,
											"UiSpike: LEGENDFIX %s text w %d->%d "
											"left %d->%d (right -> winW %d)",
											hasBoxes ? "cbox" : "plain", w0,
											obj[9] - obj[7], rowTextL0, rowTextL1,
											winW2);
									}
								}
								else if (obj && static_cast<uint32_t>(obj[0])
									== 0x00ADE0DCu && rowTextL0 > 0)
								{
									// The swatch of the row we just fixed. Scale it and
									// re-hang it at f x its own 1x-era gap from the
									// text. Centred vertically on its old centre so the
									// dash stays on the text baseline. rowTextL0 is
									// cleared right after, so a swatch is never moved
									// twice and an unfixed row is never touched.
									const int32_t sw = obj[4] - obj[2];
									const int32_t sh = obj[5] - obj[3];
									const int32_t gap0 = rowTextL0 - obj[2];
									const int32_t cy = (obj[3] + obj[5]) / 2;
									const int32_t h1 = RoundHalfUp(sh * f);
									if (gap0 > 0 && sw > 0 && sh > 0)
									{
										obj[2] = rowTextL1 - RoundHalfUp(gap0 * f);
										obj[4] = obj[2] + RoundHalfUp(sw * f);
										obj[3] = cy - h1 / 2;
										obj[5] = obj[3] + h1;
										if (gChartReconLog < 14)
										{
											gChartReconLog++;
											Logger::Get().WriteLine(LogLevel::Debug,
												"UiSpike: LEGENDSWATCH %dx%d gap %d "
												"-> (%d,%d,%d,%d) gap %d", sw, sh,
												gap0, obj[2], obj[3], obj[4],
												obj[5], rowTextL1 - obj[2]);
										}
									}
									rowTextL0 = -1;
									rowTextL1 = -1;
								}
								node = reinterpret_cast<uint32_t*>(
									static_cast<uintptr_t>(node[0]));
							}
							if (fixed)
							{
								typedef void(__thiscall* DirtyFn)(void*);
								void** cvt = *reinterpret_cast<void***>(c);
								if (cvt && cvt[0x170 / 4])
								{
									reinterpret_cast<DirtyFn>(cvt[0x170 / 4])(c);
								}
							}
						}

						// ---- #57 CHART INTERIOR SCALE (v2.50.0) ----------
						// MEASURED by the CHARTGEO line above, 2026-08-02:
						//   LEGEND band (4,4,972,36)  bandH[0x120] = 32
						//   tickLen[0x180] = 4,4
						// both IDENTICAL at f=1 and f=2 while Legend went
						// 13 -> 26pt. Two stacked 26pt entries need ~55px of
						// a 32px band, so the second overflows and its text
						// breaks up - the "Expense / s" the user reported.
						//
						// These are PLAIN FIELDS on the chart object with no
						// setter in the module, read fresh on every layout,
						// so scaling them needs NO byte patch and touches no
						// shared engine code - which matters because the
						// paint path is shared by every chart in the game.
						// ⚠ The plot rect is computed ONCE: sub_9B3647 only
						// recomputes while [0xE0] holds the sentinel
						// 0x7FFFFFFF, and NOTHING in the module ever re-arms
						// it (not even SetArea). So we re-arm it ourselves,
						// exactly once per chart object, to make the new
						// band height take effect.
						// VERIFY-BEFORE-WRITE, like CodePatches: only touch
						// fields that still hold the stock values, so a
						// second pass - or a game that ever changes them -
						// is never clobbered.
						// v2.53.1: gate on the FIELD, not a pointer latch.
						// The chart is REPLACED on every graph switch (user-
						// proven: the green vanished on reselect), and a new
						// chart can reuse the freed address - the exact #92
						// trap, where a pointer latch silently skips it.
						// bandH[0x120] is a value WE always set when we
						// process a chart, so "bandH == 32" IS the
						// not-yet-processed marker: verify-before-write,
						// idempotent at sweep cadence, address-proof.
						if (gChartScale && f > 1.01f
							&& reinterpret_cast<int32_t*>(c)[0x120/4] == 32)
						{
							int32_t* w = reinterpret_cast<int32_t*>(c);
							const int32_t winW = w[0xB0/4] - w[0xA8/4];
							const int32_t winH = w[0xB4/4] - w[0xAC/4];
							const int32_t l = w[0xE0/4], t = w[0xE4/4];
							const int32_t r = w[0xE8/4], b = w[0xEC/4];
							// ⚠ SCALE THE MARGINS, NEVER IMPOSE A RECT. The
							// stock line chart is plot (78,21,408,234) in a
							// 488x256 window, but the BAR charts (Population
							// by Age) carry NO legend and their plot
							// legitimately runs wider - a hard-coded rect
							// would crush them. Scaling whatever the game
							// itself computed is self-correcting for every
							// chart type: if it reserved 45px to hold 10pt
							// digits, 90px is the SAME layout at 20pt.
							const int32_t nl = RoundHalfUp(l * f);
							const int32_t nt = RoundHalfUp(t * f);
							const int32_t nr = winW - RoundHalfUp((winW - r) * f);
							const int32_t nb = winH - RoundHalfUp((winH - b) * f);
							// Refuse anything that would collapse the plot -
							// a scaled margin must never eat its own graph.
							const bool sane = (l != 0x7FFFFFFF)
								&& (nr - nl >= 200) && (nb - nt >= 100)
								&& nl >= 0 && nt >= 0
								&& nr <= winW && nb <= winH;
							if (sane)
							{
								w[0xE0/4] = nl; w[0xE4/4] = nt;
								w[0xE8/4] = nr; w[0xEC/4] = nb;
								// v2.53.1: THE COUPLED SET, whole or not at
								// all (law 43). The layout latches FOUR rects
								// behind separate sentinels; v2.52.0 moved
								// only the plot, leaving legend + axis
								// furniture parked at the old positions.
								// LEGEND band (4,4,972,36): scale its height
								// band and bandH together; the ticks scale
								// with their lengths.
								w[0x108/4] = RoundHalfUp(w[0x108/4] * f);
								w[0x10C/4] = RoundHalfUp(w[0x10C/4] * f);
								// v2.53.2: right edge widened to the WINDOW
								// edge (was winW-4). The legend text is
								// right-anchored and wrap-limited by THIS
								// edge; at 26pt "Expenses" missed the box by
								// a few px ("Expense / s"). +4 here plus the
								// 0.92 Legend squeeze in make_fontstyle.py
								// clears the shortfall with margin. The
								// window clips at winW anyway, so this can
								// never paint outside the chart.
								w[0x110/4] = winW;
								// height grows with the band:
								w[0x114/4] = w[0x10C/4]
									+ RoundHalfUp(32 * f);
								w[0x120/4] = RoundHalfUp(32 * f);
								// axis-title rects (+0x1CC/+0x1DC): latched
								// like the others; scale only if REAL (the
								// sentinel means "never set" - leave it).
								for (int ax = 0; ax < 2; ax++)
								{
									int32_t* arect = &w[(0x1CC + ax*0x10)/4];
									if (arect[0] != 0x7FFFFFFF)
									{
										for (int k = 0; k < 4; k++)
										{
											arect[k] = RoundHalfUp(
												arect[k] * f);
										}
									}
								}
								w[0x180/4] = RoundHalfUp(4 * f);
								w[0x184/4] = RoundHalfUp(4 * f);
								// v2.53.1 THE MISSING HALF, proven by the
								// green box: fields only take effect through
								// the game's OWN SetDirty - vt+0x170
								// (sub_99BED1, __thiscall, no args), which
								// sets cIGZWin+0x70 and propagates to the
								// ancestors. InvalidateSelfAndParents never
								// reached that byte, which is why v2.52.0's
								// write held for three ticks and drew
								// nothing.
								typedef void(__thiscall* DirtyFn)(void*);
								void** cvt = *reinterpret_cast<void***>(c);
								if (cvt && cvt[0x170 / 4])
								{
									reinterpret_cast<DirtyFn>(
										cvt[0x170 / 4])(c);
								}
							}
							// ⛔ NO SENTINEL RE-ARM. v2.50.0 re-armed
							// [0xE0] to force a re-lay and the recompute came
							// back as the FLAT 16px DEFAULTS (16,16,960,496),
							// discarding the very margins we want to scale.
							// The rect is computed once and nothing re-arms
							// it, so writing it directly STICKS - that is the
							// whole reason this lever works.
							// ⚠ ONCE PER OBJECT (gChartScaled): the sweep
							// runs 4x/sec and this write is RELATIVE, so
							// repeating it would compound 45 -> 90 -> 180.
							// (gChartScaled retired v2.53.1 - the field
							// marker above replaces it; kept as a last-seen
							// pointer for the log only.)
							gChartScaled = c;
							if (gChartScaleLog < 8) gChartScaleLog++;
							if (gChartScaleLog <= 8)
							Logger::Get().WriteLine(LogLevel::Info,
								"UiSpike: CHARTSCALE plot (%d,%d,%d,%d) -> "
								"(%d,%d,%d,%d) in %dx%d  margins L%d T%d R%d "
								"B%d -> L%d T%d R%d B%d  tick=%d  sane=%d",
								l, t, r, b, nl, nt, nr, nb, winW, winH,
								l, t, winW - r, winH - b,
								nl, nt, winW - nr, winH - nb,
								RoundHalfUp(4 * f), sane ? 1 : 0);
						}
						break;
					}
				}
			}
		}

		// DATA VIEWS expanded-page PIN-BACK (task #45, v2.21.3). DPROBE
		// measured (2026-07-29 20:29 capture; REGRESSION.md "DATA VIEWS
		// PANEL"): the game's view-select code re-lays the legend on EVERY
		// selection, mixing 1x .UI-era origin constants with pitches derived
		// from the SCALED font - rows re-set to container-rel x=278 /
		// y=24+36k, chips to (371, 61+36k) - which parks the label rows
		// underneath the 512-wide map picture (map spans page-x 218..730;
		// rows landed at 494). Same class as the RCI-column re-imposition:
		// it happens AFTER our sweep and the idempotency map will not
		// re-touch the children. Fix = pin every laid-out child back to
		// scaled DESIGN geometry each sweep while the page is visible; the
		// game only re-imposes at select time, so the sweep snaps it right
		// back. Design rects are from the live tree dump (userclickthrough
		// log line 628+): rows 0x8A909E00..08 rel (278,24+18k) 117x56 under
		// the anon container (targets are PARENT-relative, so the container
		// choice cancels out); chips 0x8A909E10..18 rel (370,61+18k) 13x10,
		// labels 0x8100/0x8101 rel (367,270/288), map 0x00004203 rel
		// (109,60) 256x256 - all directly under the page.
		if (pDVRoot)
		{
			cIGZWin* pPage = pDVRoot->GetChildWindowFromID(0x8A2871C3);
			if (pPage && pPage->IsVisible() && f > 1.01f)
			{
				struct DVPin { uint32_t id; int32_t l, t, w, h; };
				static const DVPin kDVPins[] = {
					// legend label rows (container-relative)
					{ 0x8A909E00, 278,  24, 0, 0 },
					{ 0x8A909E01, 278,  42, 0, 0 },
					{ 0x8A909E02, 278,  60, 0, 0 },
					{ 0x8A909E03, 278,  78, 0, 0 },
					{ 0x8A909E04, 278,  96, 0, 0 },
					{ 0x8A909E05, 278, 114, 0, 0 },
					{ 0x8A909E06, 278, 132, 0, 0 },
					{ 0x8A909E07, 278, 150, 0, 0 },
					{ 0x8A909E08, 278, 168, 0, 0 },
					// legend colour chips (page-relative)
					{ 0x8A909E10, 370,  61, 0, 0 },
					{ 0x8A909E11, 370,  79, 0, 0 },
					{ 0x8A909E12, 370,  97, 0, 0 },
					{ 0x8A909E13, 370, 115, 0, 0 },
					{ 0x8A909E14, 370, 133, 0, 0 },
					{ 0x8A909E15, 370, 151, 0, 0 },
					{ 0x8A909E16, 370, 169, 0, 0 },
					{ 0x8A909E17, 370, 187, 0, 0 },
					{ 0x8A909E18, 370, 205, 0, 0 },
					// range labels + the data map picture (page-relative)
					{ 0x00008100, 367, 270, 0, 0 },
					{ 0x00008101, 367, 288, 0, 0 },
					{ 0x00004203, 109,  60, 256, 256 },
				};
				// ===== v2.37.0 task #78: THE LEGEND IS THE GAME'S NOW =====
				// The 18 legend windows are re-laid by sub_007A04F0 on EVERY
				// view selection, and as of v2.37.0 that routine's four origin
				// constants are scaled in place (CodePatches::
				// ApplyDataViewLegendScale), so the legend is BORN correct and
				// this table must not touch it.
				//
				// That is not just a tidy-up - the table is ACTIVELY WRONG for
				// the legend. Its pitch is a fixed 18 (36 at 2x), but the game
				// advances by 18*ceil(h/18) from each row's MEASURED height, so
				// a label that wraps to two lines gets a 72px slot. Measured
				// 2026-07-31 09:32:19.577: the game laid nine rows at
				// 24,60,96,132,168,240,276,312,348 - a deliberate gap after
				// index 4 - and this pin FLATTENED it, dragging eight windows
				// up by 36px. Patching only the origin leaves the game's own
				// per-row deltas untouched, so the tall row keeps its slot.
				//
				// FALLBACK (only where a site could not be patched - at 3x the
				// chip Y is 61*3=183 and overflows its lea disp8): correct just
				// the axes the game really left at 1x, and correct Y by
				// SHIFTING every row by the origin delta rather than writing a
				// uniform table. Idempotent by construction: the game restarts
				// its accumulator at zero on every re-lay, so index 0 sits at
				// EXACTLY the stock origin until we move it, and once moved the
				// test stops matching. Verified in the log - 0x8A909E00 is at
				// y=24 and 0x8A909E10 at y=61 on all 18 switches.
				const int32_t kDVRowX = 278, kDVRowY = 24;   // the GAME's
				const int32_t kDVChipX = 371, kDVChipY = 61; // own constants
				const bool dvBorn = (CodePatches::DataViewLegendPatchedSites() >= 8);
				int32_t rowDY = 0, chipDY = 0;   // 0  = leave Y alone
				int32_t rowX = -1, chipX = -1;   // -1 = leave X alone
				if (!dvBorn)
				{
					cIGZWin* aRow = pPage->GetChildWindowFromIDRecursive(0x8A909E00);
					cIGZWin* aChip = pPage->GetChildWindowFromIDRecursive(0x8A909E10);
					if (aRow)
					{
						if (aRow->GetT() == kDVRowY) { rowDY = ScaleRound(kDVRowY, f) - kDVRowY; }
						if (aRow->GetL() == kDVRowX) { rowX = ScaleRound(kDVRowX, f); }
					}
					if (aChip)
					{
						if (aChip->GetT() == kDVChipY) { chipDY = ScaleRound(kDVChipY, f) - kDVChipY; }
						if (aChip->GetL() == kDVChipX) { chipX = ScaleRound(kDVChipX, f); }
					}
				}

				for (const DVPin& pin : kDVPins)
				{
					const bool isRow = (pin.id >= 0x8A909E00 && pin.id <= 0x8A909E08);
					const bool isChip = (pin.id >= 0x8A909E10 && pin.id <= 0x8A909E18);
					cIGZWin* c = pPage->GetChildWindowFromIDRecursive(pin.id);
					if (!c) { continue; }
					int32_t tl = ScaleRound(pin.l, f);
					int32_t tt = ScaleRound(pin.t, f);
					const int32_t cl = c->GetL();
					const int32_t ct = c->GetT();
					if (isRow || isChip)
					{
						if (dvBorn) { continue; } // born correct - hands off
						const int32_t dy = isRow ? rowDY : chipDY;
						const int32_t tx = isRow ? rowX : chipX;
						if (dy == 0 && tx < 0) { continue; } // nothing left 1x
						tt = ct + dy;
						tl = (tx >= 0) ? tx : cl;
					}
					// v2.69.10: the MAP picture and the bake-ceiling clamp are
					// a coupled pair - when the clamp is live this pin targets
					// the CLAMPED size, centered in the slot the 2x layout
					// reserved. Same numbers the clamp block writes, so once
					// settled neither side ever resizes the window again (the
					// v2.69.9 log showed this entry re-doubling the map every
					// sweep against the clamp, ~30 Hz - and each re-double
					// also re-desynced blitSize, which is the tear itself).
					int32_t tw = pin.w > 0 ? ScaleRound(pin.w, f) : 0;
					int32_t th = pin.h > 0 ? ScaleRound(pin.h, f) : 0;
					if (pin.id == 0x00004203 && gDvMapClampBlit > 0
						&& tw > gDvMapClampBlit)
					{
						const int32_t inset = (tw - gDvMapClampBlit) / 2;
						tl += inset;
						tt += inset;
						tw = gDvMapClampBlit;
						th = gDvMapClampBlit;
					}
					bool touched = false;
					if (cl != tl || ct != tt)
					{
						c->GZWinMoveTo(tl - cl, tt - ct);
						touched = true;
					}
					if (pin.w > 0)
					{
						if (c->GetW() != tw || c->GetH() != th)
						{
							c->SetW(tw);
							c->SetH(th);
							touched = true;
						}
					}
					if (touched)
					{
						c->InvalidateSelfAndParents();
						Logger::Get().WriteLine(LogLevel::Debug,
							"UiSpike: DVPIN 0x%08X (%d,%d)->(%d,%d).",
							pin.id, cl, ct, tl, tt);
					}
				}

				// DVLEG - the POSITIVE CONTROL for the silence above.
				// "zero DVPIN lines" is also what a pass that never ran
				// prints, so it can never be the proof on its own (METHOD.md
				// "YOUR OWN INSTRUMENTS CAN LIE"). This reads back what the
				// GAME actually laid down: a resolved-id count proves the
				// pass was live, and the y-list proves a wrapped label kept
				// its taller slot instead of being flattened. Change-only
				// (the pass runs every ~16ms tick), so it prints once per
				// real re-lay. The latch is a geometry HASH, never a pointer,
				// so it is safe across a city teardown.
				{
					uint32_t h = 2166136261u;
					int rows = 0, chips = 0, n = 0;
					char ys[224];
					ys[0] = '\0';
					for (uint32_t id = 0x8A909E00; id <= 0x8A909E08; id++)
					{
						cIGZWin* c = pPage->GetChildWindowFromIDRecursive(id);
						if (!c) { continue; }
						rows++;
						const int32_t t = c->GetT();
						h = (h ^ static_cast<uint32_t>(t)) * 16777619u;
						if (n >= 0 && n < 200)
						{
							const int w = _snprintf_s(ys + n, sizeof(ys) - n, _TRUNCATE,
								n ? ",%d" : "%d", t);
							if (w > 0) { n += w; }
						}
					}
					for (uint32_t id = 0x8A909E10; id <= 0x8A909E18; id++)
					{
						cIGZWin* c = pPage->GetChildWindowFromIDRecursive(id);
						if (!c) { continue; }
						chips++;
						h = (h ^ (static_cast<uint32_t>(c->GetT()) * 3u)) * 16777619u;
					}
					static uint32_t lastDvLegHash = 0;
					if (h != lastDvLegHash)
					{
						lastDvLegHash = h;
						Logger::Get().WriteLine(LogLevel::Debug,
							"UiSpike: DVLEG born=%d rows=%d chips=%d rowY=[%s]",
							dvBorn ? 1 : 0, rows, chips, ys);
					}
				}
			}
		}
	}

	return scaledWindows;
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
	EdgeProbeTick(pView);   // v2.36.4: inert unless [Probe] EdgeDump=1
	VisTraceTick();         // v2.36.8: inert unless [Probe] VisTrace=1
	// #137: run the panel docks on the TICK, not only from ScaleAllPanels /
	// ScalePanelsUnder / the show hook. MEASURED: those three fire on scale and
	// open events only, so a panel that becomes visible between them paints
	// undocked until the user touches something - the log showed the Graphs
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
				GetPrivateProfileStringA("UiSpike", "LiveTune", "", b, sizeof(b), kIni);
				s_liveTune = b[0] ? atoi(b) : 0;
			}
			GetPrivateProfileStringA("Disaster", "RingDX", "", b, sizeof(b), kIni);
			if (b[0]) gRingDX = atoi(b);
			GetPrivateProfileStringA("Disaster", "RingDY", "", b, sizeof(b), kIni);
			if (b[0]) gRingDY = atoi(b);
			GetPrivateProfileStringA("Disaster", "DockX", "", b, sizeof(b), kIni);
			if (b[0]) gRingDockX = atoi(b);
			GetPrivateProfileStringA("Disaster", "DockY", "", b, sizeof(b), kIni);
			if (b[0]) gRingDockY = atoi(b);
			GetPrivateProfileStringA("Disaster", "BarDX", "", b, sizeof(b), kIni);
			if (b[0]) gBarDX = atoi(b);
			GetPrivateProfileStringA("Disaster", "BarW", "", b, sizeof(b), kIni);
			if (b[0]) gBarWiden = static_cast<float>(atof(b));   // v2.24.0: float (1.5 legal)
			GetPrivateProfileStringA("Disaster", "LayerFix", "", b, sizeof(b), kIni);
			if (b[0]) gLayerFix = atoi(b);
			// v2.39.0 task #5: born-at-Place size for the first-level flyout.
			// Live so a bad size can be switched off mid-session without a
			// rebuild, and WITHOUT touching the sub-flyout's own lever.
			GetPrivateProfileStringA("Disaster", "BornScale", "", b, sizeof(b), kIni);
			if (b[0]) gDisBornScaleOn = atoi(b);
			GetPrivateProfileStringA("Disaster", "BornDock", "", b, sizeof(b), kIni);
			if (b[0]) gDisBornDockOn = atoi(b);
			GetPrivateProfileStringA("Disaster", "BornMetrics", "", b, sizeof(b), kIni);
			if (b[0]) gDisBornMetricsOn = atoi(b);
			GetPrivateProfileStringA("Disaster", "StripDump", "", b, sizeof(b), kIni);
			if (b[0]) gStripDump = atoi(b);
			GetPrivateProfileStringA("Disaster", "StripHitDX", "", b, sizeof(b), kIni);
			if (b[0]) gStripHitDX = atoi(b);
			GetPrivateProfileStringA("Disaster", "StripHitW", "", b, sizeof(b), kIni);
			if (b[0]) gStripHitW = atoi(b);
			GetPrivateProfileStringA("Disaster", "StripForceX", "", b, sizeof(b), kIni);
			if (b[0]) gStripForceX = atoi(b);
			GetPrivateProfileStringA("Disaster", "ClickHook", "", b, sizeof(b), kIni);
			if (b[0]) gClickHook = atoi(b);
			GetPrivateProfileStringA("Disaster", "MouseSlot", "", b, sizeof(b), kIni);
			if (b[0]) gMouseSlot = atoi(b);
			GetPrivateProfileStringA("Disaster", "SelDL", "", b, sizeof(b), kIni);
			if (b[0]) gSelDL = atoi(b);
			GetPrivateProfileStringA("Disaster", "SelDR", "", b, sizeof(b), kIni);
			if (b[0]) gSelDR = atoi(b);
			GetPrivateProfileStringA("Disaster", "SelForce", "", b, sizeof(b), kIni);
			if (b[0]) gSelForce = atoi(b);
			GetPrivateProfileStringA("Disaster", "ClaimScale", "", b, sizeof(b), kIni);
			if (b[0]) gClaimScale = atoi(b);
			GetPrivateProfileStringA("Disaster", "FlashGuard", "", b, sizeof(b), kIni);
			if (b[0]) gFlashGuard = atoi(b);
			// [Probe]: aim the DPROBE geometry probe at whatever menu is under
			// investigation (Mayor mode opens outside the god column).
			GetPrivateProfileStringA("Probe", "Enabled", "", b, sizeof(b), kIni);
			if (b[0]) gProbeOn = atoi(b);
			GetPrivateProfileStringA("Probe", "BandL", "", b, sizeof(b), kIni);
			if (b[0]) gProbeL = atoi(b);
			GetPrivateProfileStringA("Probe", "BandR", "", b, sizeof(b), kIni);
			if (b[0]) gProbeR = atoi(b);
			GetPrivateProfileStringA("Probe", "BandT", "", b, sizeof(b), kIni);
			if (b[0]) gProbeT = atoi(b);
			GetPrivateProfileStringA("Probe", "BandB", "", b, sizeof(b), kIni);
			if (b[0]) gProbeB = atoi(b);
			GetPrivateProfileStringA("Probe", "Max", "", b, sizeof(b), kIni);
			if (b[0]) gProbeMax = atoi(b);
			GetPrivateProfileStringA("Probe", "EdgeDump", "", b, sizeof(b), kIni);
			if (b[0]) gEdgeDump = atoi(b);
			GetPrivateProfileStringA("Probe", "VisTrace", "", b, sizeof(b), kIni);
			if (b[0]) gVisTrace = atoi(b);
			GetPrivateProfileStringA("Probe", "EdgeBlt", "", b, sizeof(b), kIni);
			if (b[0]) gEdgeBltLog = atoi(b);   // = how many lines to log
			// #162: [Probe] ThinBlt = how many thin-dst blits to log.
			//
			// ⛔ ARM THE HOOK HERE, OR THE PROBE IS A GUARANTEED NULL.
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
			GetPrivateProfileStringA("Probe", "AdvisorShot", "", b, sizeof(b), kIni);
			if (b[0]) gAdvisorShot = atoi(b);
			GetPrivateProfileStringA("Probe", "DrawProbe", "", b, sizeof(b), kIni);
			if (b[0]) gDrawProbe = atoi(b);
			GetPrivateProfileStringA("Probe", "ThinBlt", "", b, sizeof(b), kIni);
			if (b[0]) gThinBlt = atoi(b);
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
				// [Probe] IconProbe (task #149): class census of everything
				// visible, so a menu's item classes appear as NEW lines the
				// moment that menu opens. Read-only. Default OFF.
				GetPrivateProfileStringA("Probe", "IconProbe", "", b, sizeof(b), kIni);
				if (b[0]) gIconProbe = atoi(b);
				// [Probe] SmallWin (#188): NAME the small floating windows over
				// the 3D view - built to identify the U-Drive-It START bubbles
				// the user clicks (the #186 pin hit the DURING-mission marker;
				// the start bubbles are a different, unidentified window).
				// IconProbe cannot do this: it dedupes by CLASS and a bubble
				// sharing GZWinBMP's vtable spends its 4 example slots on dock
				// windows at load. Value = total lines to print. Default OFF.
				GetPrivateProfileStringA("Probe", "SmallWin", "", b, sizeof(b), kIni);
				if (b[0]) gSmallWin = atoi(b);
				GetPrivateProfileStringA("Probe", "IconFit", "", b, sizeof(b), kIni);
				if (b[0]) gIconFit = atoi(b);
				GetPrivateProfileStringA("Probe", "IconCover", "", b, sizeof(b), kIni);
				if (b[0]) gIconCover = atoi(b);
				GetPrivateProfileStringA("Probe", "IconCentreOff", "", b, sizeof(b), kIni);
				if (b[0]) gIconCentreOff = atoi(b);
				GetPrivateProfileStringA("Probe", "IconHook", "", b, sizeof(b), kIni);
				if (b[0]) gIconHook = atoi(b);
				GetPrivateProfileStringA("Probe", "IconFitLog", "", b, sizeof(b), kIni);
				if (b[0]) gIconFitLog = atoi(b);
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
			// [Flyout]: mayor-mode flyout docking (kMayorFlyoutDock).
			GetPrivateProfileStringA("Flyout", "MayorDock", "", b, sizeof(b), kIni);
			if (b[0]) gMayorDock = atoi(b);
			// #95: MarkerAlarm - the god-path marker-drift diagnostic (MDRIFT).
			// Diagnostic ONLY; it never moves a window. Default 1.
			GetPrivateProfileStringA("Flyout", "MarkerAlarm", "", b, sizeof(b), kIni);
			if (b[0]) gMDockAlarm = atoi(b);
			// #95: SubMath - the sub-flyout placement model (validated 32/32 vs
			// the game's own sub_79AD00). 1 = model (default), 0 = the legacy
			// fixed delta, which is wrong by up to 197px at 8 items.
			// #57: ChartScale - scale the Graphs chart's frozen interior
			// fields (legend band height, tick lengths). 1 = on (default),
			// 0 = probe only, no writes. Instant revert, no rebuild.
			GetPrivateProfileStringA("Flyout", "ChartScale", "", b, sizeof(b), kIni);
			if (b[0]) gChartScale = atoi(b);
			// #57 PHASE 1: ChartProbe - the repaint proof. Default 0.
			// 1 = flood the plot area green and trigger the game's own
			// SetDirty, ONCE per chart object. Diagnostic only; defaces the
			// chart until set back to 0. See gChartProbe for the committed
			// discriminator.
			GetPrivateProfileStringA("Flyout", "ChartProbe", "", b, sizeof(b), kIni);
			if (b[0]) gChartProbe = atoi(b);
			GetPrivateProfileStringA("Flyout", "SubMath", "", b, sizeof(b), kIni);
			if (b[0]) gSubMath = atoi(b);
			GetPrivateProfileStringA("Flyout", "SubBltLog", "", b, sizeof(b), kIni);
			if (b[0]) gSubBltLog = atoi(b);
			GetPrivateProfileStringA("Flyout", "RingCal", "", b, sizeof(b), kIni);
			if (b[0]) gRingCalLog = atoi(b);
			GetPrivateProfileStringA("Flyout", "SubRingDX", "", b, sizeof(b), kIni);
			if (b[0]) gSubRingDX = atoi(b);   // #134: absent = derive per tier
			GetPrivateProfileStringA("Flyout", "SubRingDY", "", b, sizeof(b), kIni);
			if (b[0]) gSubRingDY = atoi(b);   // #134: absent = derive per tier
			GetPrivateProfileStringA("Flyout", "ArrowClick", "", b, sizeof(b), kIni);
			if (b[0]) gArrowClick = atoi(b);
			GetPrivateProfileStringA("Flyout", "EmergLog", "", b, sizeof(b), kIni);
			if (b[0]) gEmergLog = atoi(b);
			GetPrivateProfileStringA("Flyout", "SubDockDX", "", b, sizeof(b), kIni);
			if (b[0]) gSubDockDX = atoi(b);
			GetPrivateProfileStringA("Flyout", "SubDockDY", "", b, sizeof(b), kIni);
			if (b[0]) gSubDockDY = atoi(b);
			// v2.36.0 born-scale: flip either half live, no rebuild. Size and
			// dock are separable on purpose - if a menu ever lands in the
			// wrong PLACE, SubBornDock=0 isolates that from the size half.
			GetPrivateProfileStringA("Flyout", "SubBornScale", "", b, sizeof(b), kIni);
			if (b[0]) gSubBornScaleOn = atoi(b);
			GetPrivateProfileStringA("Flyout", "SubBornDock", "", b, sizeof(b), kIni);
			if (b[0]) gSubBornDockOn = atoi(b);
			GetPrivateProfileStringA("Flyout", "BornOnOpen", "", b, sizeof(b), kIni);
			if (b[0]) gFlyoutOpenOn = atoi(b);
			GetPrivateProfileStringA("Flyout", "ScaleGodPanelABB", "", b, sizeof(b), kIni);
			if (b[0]) gScaleAbbPanel = atoi(b);
			GetPrivateProfileStringA("Flyout", "AdvisorHeal", "", b, sizeof(b), kIni);
			if (b[0]) gAdvisorHeal = atoi(b);
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
	// ⛔ v2.69.3: the v2.69.0 `if (gProbeOn)` gate around this WALK is REVERTED
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
		cIGZWin* probeRoot = pView->GetChildWindowFromIDRecursive(0x9A47B417);
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
				std::map<void*, PGeom>::iterator it = prevGeom.find(key);
				const bool isNew = (it == prevGeom.end());
				const bool changed = isNew
					|| it->second.l != now.l || it->second.t != now.t
					|| it->second.w != now.w || it->second.h != now.h
					|| it->second.vis != now.vis;
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
				if (id == 0 && now.vis == 1 && now.h > 400 && now.w > 80
					&& ax > -150 && ax < 500 && ay > 380 && ay < 1250)
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
							gPaintHits = 0;
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
					if (now.w >= 60 && now.w <= 120 && now.h >= 400 && now.h <= 700
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

				prevGeom[key] = now;
				ChildSnapshot snap = {};
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

	// kSizeOnlyIds REMOVED (v2.12.1, founded-city god mode). It held exactly one
	// id, 0xABB26B0E, on the belief that it was "a frozen hidden template at
	// Y1045" that day/night merely rode on - true in the PRE-FOUNDING god mode
	// where all the flyout work was done, and FALSE in a founded city, where
	// 0xABB26B0E is the god panel that god mode actually shows (live dump: two
	// real 148x116 god buttons under it, everything else vis=0).
	// Size-only scaling never moves the root, and this panel's stock rect
	// (3,1045) 157x488 is BOTTOM-anchored, so doubling it in place grew it from
	// y=1045 to y=2021 on a 1600px screen - 421px off the bottom. That was the
	// user's "God Mode never loads, the UI stays crushed".
	// It is now a god PANEL: same treatment as its twin 0x69E40A1F, which has
	// the IDENTICAL stock size (157x488) and is already transformed correctly.
	// The panel transform y' = f*y - (f-1)*frameH yields 2*1045-1600 = 490, i.e.
	// (6,490) - exactly the dock position recorded for this id on 2026-07-24.

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
	cIGZWin* mayorBtn1 = pView->GetChildWindowFromIDRecursive(0x8991EE08);
	cIGZWin* mayorHud = pView->GetChildWindowFromIDRecursive(0xE9889775);
	const bool mayorModeActive = (mayorHud != nullptr && mayorHud->IsVisible());

	// (the size-only pass that lived here is gone - see kSizeOnlyIds note above)

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
	gDisDockL = tbLiveL + ScaleRound(gRingDockX, f);
	gDisDockT = tbLiveT + ScaleRound(gRingDockY, f);
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
		// ONLY on the five menus in kParents. When the user opened
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
			// v2.25.3 (task #48): the two tool-flyout COLUMNS opted in. Their
			// sub-flyout is the SAME 258-wide architecture the five originals
			// use (live log 2026-07-30: "SUBSKIP container 0x8A6E61E0 258x874"
			// - the strip-width family the disaster hooks were built for).
			// The Earned Cars crash strip was 88 WIDE - a different layout -
			// which is why the gate stays an id list, never a width test alone.
			const uint32_t kHookParents[] = {
				0x49923239, 0x69923479, 0xC99237A0, 0xE992F711, 0x699306ED,
				0x8BB27C12, 0xAB954023
			};
			for (uint32_t pid : kHookParents)
			{
				cIGZWin* par = pView->GetChildWindowFromIDRecursive(pid);
				if (par && par->IsVisible()) { knownMenuOpen = true; break; }
			}
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
			const uint32_t kParents[] = {
				0x49923239, 0x69923479, 0xC99237A0, 0xE992F711, 0x699306ED,
				0x8BB27C12, 0xAB954023   // v2.25.3: the two tool-flyout columns
			};
			// The law needs THIS menu's ringBltY. If the recorded blit is not
			// for this buffer size, the menu just switched and its ring has not
			// painted yet - skip; blits fire every frame vs this 4x/sec sweep,
			// so the next sweep has fresh data.
			const bool ringFresh =
				(gSubRingBufW == sub->GetW() && gSubRingBufH == sub->GetH());
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
			bool done = false;
			for (uint32_t pid : kParents)
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
					const int32_t bcx = bl + kid->GetW() / 2;
					const int32_t bcy = bt + kid->GetH() / 2;
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
					// ⚠ SubMath governs Y ONLY, and X deliberately stays on the
					// measured law. The model's X is not wrong, it is a
					// DIFFERENT convention: the 80f-wide ring sprite has the
					// stem built into its right half, so the game's own
					// left = cx - 27f draws the ring 13f RIGHT of the button
					// centre, while our measured dock centres it (they differ
					// by exactly RoundHalfUp(40f) - RoundHalfUp(27f) = 26 at
					// f=2). Nothing is broken horizontally - the reported
					// defect is the column hanging into the bottom HUD - so
					// moving X would be an unforced 26px change to a placement
					// the user has already signed off. It would ALSO desync
					// birth from the sweep: the sweep only re-docks a container
					// it finds at the native or the target position, and a
					// 26px disagreement fails both tests, which silently ends
					// the dock AND freezes the back-arrow click zone.
					const int32_t tgtL = legL;
					const int32_t tgtT = gSubMath
						? SubPlaceTop(sub->GetH(), bcy, pView->GetH(), gTierF)
						: legT;
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
					gSubRingAutoY = gSubMath ? (legT - tgtT) : 0;
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
		}

		// ---- REUSE THE DISASTER DRAW FIXES (v2.13.5) ----------------------
		// PROVEN by the SVT class probe: this container is class 0x00AB6AA8 and
		// its strip child is 0x00AB6D88 - the SAME concrete classes as the
		// disaster flyout. So the two fixes already written for those classes
		// apply verbatim, and nothing new has to be reverse-engineered:
		//   SlotThunk<88>  + gForceRecreate  -> corrupts the buffer's cached
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
		// (gForceRecreate for the stale 1x buffer, gStripFieldScale for the
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
	{
		for (const MayorFlyoutDock& m : kMayorFlyoutDock)
		{
			if (!m.mayorOnly) { continue; }
			if (!mayorModeActive && !m.anyMode) { continue; }
			cIGZWin* win = pView->GetChildWindowFromIDRecursive(m.flyoutId);
			if (!win || win->GetW() <= 0 || win->GetH() <= 0) { continue; }

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
			// thereafter. That is exactly what the user saw.
			//
			// THE CURE IS THE PROJECT'S OWN, copied from ScalePanelRoot
			// (~:14887) whose comment describes this failure in these words:
			// "new objects land on RECYCLED heap addresses ... classify
			// Unrecognized, and stay stuck at 1x design geometry forever".
			// Erase the root's own record too - that is what clears a
			// tug-of-war tombstone left by a previous instance at this
			// address, which otherwise pins the whole flyout at raw 1x.
			//
			// ⚠ THE GATE IS THE ENTIRE SAFETY ARGUMENT. Purge ONLY when the
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
				// circle" the user reported. The rule this file already
				// documents above the table IS the general form:
				//     target = spawnButtonAbs - markerOffset(live)
				// ⚠ v2.47.0 CORRECTION: this comment used to end "and the
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
		cIGZWin* win = pView->GetChildWindowFromIDRecursive(d.id);
		if (!win || win->GetW() <= 0 || win->GetH() <= 0)
		{
			continue;
		}
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
			// #95 PHASE 1 - MARKER-DRIFT ALARM (diagnostic only, no behaviour).
			// ⛔ The plan proposed converting THIS path to the live-marker rule
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
	//   down 224, left 104 = the user's "down + slightly left" arrow, and the
	//   terraform-on-btn1 relationship the user set as the acceptance test.
	// NO ScaleSubtree (it doubles child positions and flings the strip); dock
	// first, scale later.
	cIGZWin* godParent = pView->GetChildWindowFromIDRecursive(0x9A47B417);
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
			// Dock the container (same offset as before).
			const int32_t targetL = tbLiveL + ScaleRound(gRingDockX, f);   // v2.10: live-tunable (ini [Disaster] DockX), default 6
			const int32_t targetT = tbLiveT + ScaleRound(gRingDockY, f);   // v2.11.30: live-tunable (ini [Disaster] DockY), default 130
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

			// ⚠ COMMENT CORRECTED v2.39.5 (the old text here was the premise
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
				// ⚠ v2.39.4's DIAGNOSIS WAS WRONG (measured 2026-07-31,
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
				// ⚠ ONE-SHOT PER CONTAINER. This block runs on EVERY sweep tick
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

// Erase every scaleMap record keyed under win's CURRENT subtree pointers
// (win itself excluded - its record is about to be overwritten). Read-only
// walk; only the bookkeeping map is touched.
// #192: the director hands us the RENDER resolution the tier was decided
// from, so the Graphic Options readout can state what is actually being
// rendered rather than what was requested.
void UiSpike::SetRenderResForReadout(int32_t w, int32_t h)
{
	gReadoutW = w;
	gReadoutH = h;
}

void UiSpike::SetRequestedResIgnored(bool ignored)
{
	gReqResIgnored = ignored;
}

// Push the RESOLVED tier factor into the hook-visible mirror, from the one
// place that knows it, at the moment it is known - and UNCONDITIONALLY,
// including tier 1. gTierF is namespace-scope and invisible to `settings`,
// which is exactly why it drifted: the two functions that used to set it are
// scaling paths, so they do not run when there is no scaling to do, and the
// mirror kept its initialiser instead.
//
// ⛔ DO NOT GATE THIS ON factor > 1.01. That gate is what created the bug:
// "no scaling" still has a correct factor (1.0), and 97 read sites need it.
void UiSpike::SetTierMirror(float f)
{
	gTierF = f;
}

void UiSpike::PurgeSubtreeRecords(cIGZWin* win, int depth)
{
	// v2.69.0: a silent stop here leaves stale scaleMap records below the cap,
	// which read as "already scaled" on the next sweep. One line per city.
	if (win && depth > kMaxDepth)
	{
		static int purgeWarnEpoch = -1;
		if (purgeWarnEpoch != gGaugeEpoch)
		{
			purgeWarnEpoch = gGaugeEpoch;
			Logger::Get().WriteLine(LogLevel::Info,
				"UiSpike: PurgeSubtreeRecords DEPTH CAP %d reached under "
				"id=0x%08X - records below it are NOT purged",
				kMaxDepth, win->GetID());
		}
	}
	if (!win || depth > kMaxDepth)
	{
		return;
	}
	ChildSnapshot snap = {};
	win->EnumChildren(GZIID_cIGZWin, ChildSnapshot::Callback, &snap);
	for (int i = 0; i < snap.count; i++)
	{
		scaleMap.erase(snap.wins[i]);
		PurgeSubtreeRecords(snap.wins[i], depth + 1);
	}
}

// Scale one panel root (anchored to the nearer frame edge) and sweep its
// subtree. Idempotent: an already-scaled root is left untouched but its
// descendants are still swept for NEW windows. Returns windows newly scaled.
int UiSpike::ScalePanelRoot(cIGZWin* win, int32_t frameW, int32_t frameH, float f)
{
	// Frame for the size-sanity guard used throughout this panel's subtree.
	passScreenW = frameW;
	passScreenH = frameH;

	int count = 0;

	const ScaleState state = Classify(win);

	if (state == ScaleState::Fresh)
	{
		// PURGE-ON-FRESH-ROOT (REGION-SWITCH.md): a Fresh panel root proves
		// the game rebuilt this subtree - every descendant is a NEW window
		// object. But new objects land on RECYCLED heap addresses that can
		// still carry scaleMap records of the destroyed windows; id=0
		// children then collide (0==0, size matches neither orig nor
		// scaled), classify Unrecognized, and stay stuck at 1x design
		// geometry forever (the region-switch population bug). Erasing every
		// record under the fresh root makes a switch bookkeeping-identical
		// to a fresh boot. No-op on true first boot; records of windows
		// alive elsewhere are untouchable by construction.
		PurgeSubtreeRecords(win, 0);
	}

	// #161: this root's DESIGN origin, for its children to round in. 0 means
	// "not scaled on this pass", which is the identity and so the old maths.
	int32_t rootDesignL = 0, rootDesignT = 0;

	if (state == ScaleState::Fresh || state == ScaleState::ResetToOriginal)
	{
		// Geometry is read AT MUTATION TIME: GZWinMoveTo is RELATIVE (moves
		// BY, not TO - proven by the cycle-20 diagnostics), so the delta
		// must derive from the position the window has right now, never
		// from a snapshot captured earlier in the pass.
		const int32_t curL = win->GetL();
		const int32_t curT = win->GetT();
		const int32_t w = win->GetW();
		const int32_t h = win->GetH();

		// Anchor math runs on the DESIGN geometry. On a re-scale after a
		// game reset the window still sits at the position WE moved it to -
		// using that would compound the move every round (drift).
		int32_t l = curL;
		int32_t t = curT;
		if (state == ScaleState::ResetToOriginal)
		{
			const ScaleRecord& prev = scaleMap[win];
			if (prev.hasOrigPos)
			{
				l = prev.origL;
				t = prev.origT;
			}
		}

		// Edge-derived, rounded (see ScaleSubtree for why).
		// ⛔ #166: A PANEL ROOT IS SIZED AS A LENGTH, NOT BY ITS EDGES.
		//
		// This was `ScaleRound(l + w, f) - ScaleRound(l, f)`, and that makes a
		// window's scaled SIZE depend on its POSITION:
		//
		//     edges  == length   iff  l*f is an integer
		//     at f = p/q lowest terms, iff  q | l
		//
		// At f=1.5, q=2, so the size FLIPS WITH THE PARITY OF THE LIVE ORIGIN.
		// The offline art is sized as a pure LENGTH - ScaleDim(w, f) - and
		// cannot know where the game will dock the panel, so the two halves of
		// the pipeline disagree by a pixel on every odd origin.
		//
		// MEASURED over every capture we hold (design->scaled pairs from this
		// very log line):
		//     f=1.5    530 panels disagree,  1434 agree
		//     f=2.0      0
		//     f=3.0      0
		// e.g. the city dashboard 0x0987B48F, design l=30 w=235, docked at
		// live l=5:   edges = R(240)-R(8) = 352,  length = R(352.5) = 353,
		// against a 353-wide tiled background. At its DESIGN origin the same
		// panel computes 353 and is exact - which is why every offline gate
		// reported it clean and eight hypotheses died on it.
		//
		// ⚠ THIS IS NOT A REVERSAL OF #161, AND THE DISTINCTION IS THE WHOLE
		// FIX. #161 made CHILDREN round in the parent's ABSOLUTE DESIGN frame,
		// because a child's edge must land exactly on its parent's and on its
		// siblings'. That is still right and is untouched here (ScaleSubtree,
		// ~:16913). A ROOT has no sibling to abut - it is anchored in the frame
		// and its only contract is with ITS OWN ART. Edge-derived is correct
		// for a child; length-derived is correct for a root. Same file, two
		// roles, two rules (law 86).
		//
		// ⚠ PROVABLE NO-OP AT AN INTEGER FACTOR, by arithmetic rather than
		// hope: when v*f is exact for all v, R(l+w)-R(l) = (l+w)f - lf = wf =
		// R(w*f). So 2x and 3x are bit-identical and the 530 above is 0 there.
		// ⚠ emu_panel_anchor.py models the OLD law and reproduces 39/39 panels
		// from the captures. After this change it must be updated in step; a
		// mismatch against a pre-#166 capture is the change working, NOT a
		// regression - but it must be re-baselined deliberately, not ignored.
		// ⚠ SCOPED TO ROOTS THAT OWN A BACKGROUND SHEET. The first cut of this
		// applied length-sizing to EVERY panel root - 627 of them at 1.5x - to
		// correct the 5 that actually have art whose size must match. The other
		// 622 carry no background image at all, so moving them a pixel is an
		// unrequested change with no benefit. That is law 94, the right rule at
		// the wrong scope, walked into eight hours after writing it down.
		//
		// The set is DERIVED, not hand-written: it is every ROOT-depth node in
		// the .UI corpus that carries an `image=` AND `blttype=tiled`, i.e. a
		// window whose own background sheet is bound to it. Regenerate with the
		// census in _tests/REGRESSION.md #166; it currently yields 17, and
		// contains all 4 ids the 218-capture live-rect harvest confirmed
		// (0x0987B48F, 0x0A78827A, 0xABB26B0E, 0xC991EDA8).
		static const uint32_t kOwnsBackgroundSheet[] = {
			0x0987B48F, 0x09EBEE45, 0x0A78827A, 0x27DF05BE, 0x27DF05BF,
			0x69E40A1F, 0x6A243D9E, 0x6BB92BCA, 0x6BFAC122, 0x8BFAC13E,
			0xAAA9C9D9, 0xABB26B0E, 0xC98F49F1, 0xC991EDA8, 0xCBFACAE1,
			0xEA8CAD14, 0xEA8CAD19,
		};
		bool ownsSheet = false;
		{
			const uint32_t wid = win->GetID();
			for (size_t i = 0;
				i < sizeof(kOwnsBackgroundSheet) / sizeof(kOwnsBackgroundSheet[0]);
				i++)
			{
				if (kOwnsBackgroundSheet[i] == wid) { ownsSheet = true; break; }
			}
		}
		// Length for a root that must match its own art; edges for everything
		// else, which keeps every panel that is fine today bit-identical.
		const int32_t newW = ownsSheet ? ScaleRound(w, f)
			: (ScaleRound(l + w, f) - ScaleRound(l, f));
		const int32_t newH = ownsSheet ? ScaleRound(h, f)
			: (ScaleRound(t + h, f) - ScaleRound(t, f));

		// #161: hand this DESIGN origin to the child loop below. The extent
		// above was rounded here, so the children must round here too - see
		// the note at the recursion. Captured after the ResetToOriginal
		// correction, so a re-scale uses the design origin and not the
		// position we moved the window to.
		rootDesignL = l;
		rootDesignT = t;

		// Belt-and-braces double-scale guard: a target size beyond the
		// frame means the bookkeeping failed (or the panel genuinely cannot
		// fit). Either way: fail safe, touch nothing. This line should
		// NEVER appear in a healthy log.
		if (newW > frameW || newH > frameH)
		{
			Logger::Get().WriteLine(
				LogLevel::Info,
				"UiSpike: panel 0x%08X target %dx%d exceeds frame %dx%d - SKIPPED (double-scale guard) and tombstoned.",
				win->GetID(), newW, newH, frameW, frameH);
			// Tombstone: without a record the next pass would retry forever
			// (guard spam). The window is left exactly as the game made it.
			ScaleRecord dead = { win->GetID(), w, h, w, h, 0, true };
			scaleMap[win] = dead;
			return 0;
		}

		// Scaled-gap anchoring: uniform scaling about the nearer frame
		// edge. Unlike gap-preservation, this keeps OVERLAPPING SIBLINGS
		// aligned (the polls panel rides on the composite HUD; both must
		// transform identically for their relative layout to survive).
		const int32_t gapL = l;
		const int32_t gapR = frameW - (l + w);
		const int32_t gapT = t;
		const int32_t gapB = frameH - (t + h);

		// Per-axis anchor choice: a panel HUGGING an edge keeps its scaled
		// gap to that edge; a panel NOT near either edge (min gap > 1/4 of
		// the frame) scales about its own center. Edge math on a mid-screen
		// panel teleports it (the day/night slider at y=832 was "bottom-
		// anchored" to y=64); center math also covers the screen-centered
		// top strips whose edge math pushed them off-screen entirely.
		const int32_t cMinX = frameW / 4;
		const int32_t cMinY = frameH / 4;

		// Generic per-axis anchor. NOTE (2026-07-23): the god-tool flyouts
		// (terraform/terrain-fx/disaster) animate their position code-side,
		// so a snapshot-based dock mis-fires (clamped to Y0). Day/Night lands
		// correctly under this generic anchor; the others need a spawn-button
		// dock that reads the LIVE button position at open time (Phase 2
		// follow-up), not a design-offset. Generic keeps them in-range for
		// now (kGodToolFlyoutIds retained for that follow-up).
		// #101: the city bottom-HUD family co-anchors off ONE leader so that
		// overlapping siblings transform identically. Adjudicated offline
		// before this was built, with tools\uimap\emu\emu_panel_anchor.py:
		//   0 of 39 panels move at 2400x1600 f=2.0 (the USER-CONFIRMED tier)
		//   20 of 39 move at 1400x1050 f=1.5, all of them toward the design
		//   layout, and the leader itself does not move at either.
		// Family X is deliberately NOT clamped per-member below (clampX
		// stays false): CityHudOriginX already decided the family's fit, and
		// a per-member clamp is precisely what shears the family apart.
		int32_t newX;
		bool clampX = true;
		if (IsCityHudFamilyId(win->GetID()))
		{
			newX = CityHudOriginX(frameW, f)
			     + ScaleRound(l, f) - ScaleRound(kCityHudLeaderL, f);
			clampX = false;
		}
		else if (gapL > cMinX && gapR > cMinX)
			newX = l + w / 2 - newW / 2;
		else if (gapL <= gapR)
			newX = ScaleRound(gapL, f);
		else
			newX = frameW - ScaleRound(gapR, f) - newW;

		int32_t newY;
		if (gapT > cMinY && gapB > cMinY)
			newY = t + h / 2 - newH / 2;
		else if (gapT <= gapB)
			newY = ScaleRound(gapT, f);
		else
			newY = frameH - ScaleRound(gapB, f) - newH;

		// #127: the Graphs checkbox-band pin is NOT here. The band 0x0A4A8176 is
		// anchored BEFORE the chart 0x8A8B5B71 in the pass AND only once (Fresh),
		// so it can never see the chart's scaled frame from inside this function.
		// It is pinned instead in PinGraphsCheckBand(), a post-sweep step that
		// reads both windows' LIVE positions - pass-order- and state-proof.

		// On-screen clamp, PER-EDGE conditional on the DESIGN gap: a negative
		// design gap is an INTENTIONAL overhang (the minimap dock hangs 11px
		// off-screen at 1x; the city mode overlay starts at y=-16) and the
		// anchor math already scaled it correctly - clamping it shifts the
		// panel off its design alignment (the Mayor-symbol overlap bug,
		// CITY-DOCK-OVERLAP.md). Only a non-negative gap can mean genuine
		// overflow worth clamping.
		if (clampX && gapR >= 0 && newX + newW > frameW) newX = frameW - newW;
		if (clampX && gapL >= 0 && newX < 0) newX = 0;
		if (gapB >= 0 && newY + newH > frameH) newY = frameH - newH;
		if (gapT >= 0 && newY < 0) newY = 0;

		// #197 ART-SIZED ROOT: this window is BORN at its art's pixel size, so
		// writing a scaled geometry here is the SECOND application of f.
		// Measured across the user's captures at every tier - img 48/64/96 in
		// a window ScalePanelRoot had set to 72/128/288, i.e. art*f = 32*f*f.
		// Refuse the write and source == window, so the blit's clamp gives
		// m = 1 and the marker draws at exactly 32*f.
		//
		// ⛔ THE MOVE GOES WITH IT. newX/newY are computed FROM newW/newH,
		// so "size only" is not separable - and the measured teleport
		// (934,700)->(902,668) is 32px off the world point the game had just
		// set for it. A move derived from a size we refuse to write is
		// incoherent.
		//
		// ⛔ THE RECORD IS STILL MANDATORY. Without one this root stays
		// Fresh, and PURGE-ON-FRESH-ROOT wipes every descendant record on every
		// pass - the count child would classify Fresh and be re-scaled by f
		// each sweep. Runaway growth, and the least obvious trap here.
		//
		// ⛔ count++ MUST NOT FIRE: nothing was mutated, and the log line
		// would otherwise claim a write that did not happen. The invariant gate
		// requires mutation -> increment, never the reverse.
		const bool artSizedRoot = (win->GetID() == 0x48E945B4 && f > 1.01f);
		if (artSizedRoot)
		{
			ScaleRecord rec = { win->GetID(), w, h, w, h, 0, false };
			rec.origL = l;
			rec.origT = t;
			rec.hasOrigPos = true;
			StoreScaleRecord(win, rec);
			if (gArtSizedRefusals < 4)
			{
				gArtSizedRefusals++;
				const int32_t want = RoundHalfUp(32 * f);
				Logger::Get().WriteLine(LogLevel::Info,
					"UiSpike: ARTSIZED-ROOT 0x%08X %dx%d at f=%.2f - refusing "
					"the root geometry write (art is staged at f, so it is "
					"already %d). %s Children still walked below.",
					win->GetID(), w, h, f, want,
					(w == want && h == want)
						? "Matches - on-screen is exactly the factor."
						: "DOES NOT MATCH the expected size: the art stage and "
						  "this refusal have drifted - re-check "
						  "MISSION_BUBBLE_FIXED96_MULT.");
			}
		}
		else
		{
		// #191 WORLD-ANCHORED ROOTS: SIZE ONLY, NEVER MOVE.
		// The Move In My Sim marker pair (0x27DF05BE green / 0x27DF05BF red)
		// is positioned BY THE GAME every frame to track a world point - the
		// candidate house, or the mouse. Its left/top are an OUTPUT of that
		// tracking, not a design-space anchor, so the generic root-move
		// multiplies a screen position that was already correct. MEASURED at
		// tier 2.00, the moment the blit started following:
		//     panel 0x27DF05BE (535,381 46x97) -> (1070,762 92x194)
		// The SIZE is right and the POSITION is exactly doubled - which walks
		// the marker off the house. User: "the alignment is off but it grew".
		//
		// Same treatment the god-mode tool flyouts already get (see the
		// IsGodToolFlyoutId skip in the panel loop, whose comment records that
		// "the generic root-move anchor here teleports them") - but those are
		// skipped entirely, and this one still NEEDS the resize, so it takes a
		// size-only path rather than an exclusion.
		//
		// ⭐ LAW: A ROOT WHOSE POSITION IS AN OUTPUT MUST NOT BE RE-ANCHORED.
		// Ask whether the game rewrites left/top every frame. If it does, its
		// position is already in final screen space and scaling it is a second
		// application - the positional twin of the born-at-art-size trap.
		const bool worldAnchored = (win->GetID() == 0x27DF05BE
			|| win->GetID() == 0x27DF05BF);

		// Proven call order preserved: move the root to its anchor first,
		// then resize. The move is RELATIVE, so the delta comes from the
		// CURRENT position even when the anchor came from the recorded one.
		// ⛔ A SEAT-ON-RESIZE WAS HERE AND IS REMOVED. It compensated the
		// growth against the marker's bottom-centre tip, which is the right
		// ANCHOR - but it cannot work, because the tool re-places this window
		// EVERY FRAME: 0x0043A26A / 0x00437ED5 call GZWinMoveTo with
		// (mouseX - [ctrl+0x48], mouseY - [ctrl+0x44]). Anything we write is
		// overwritten on the next tick.
		//
		// ⭐ THE REAL CAUSE IS A LATCH (the #176 shape again). Those two
		// offsets are captured AT INIT, at 0x0043A82D and 0x0043A841, as
		//     [ctrl+0x44] = win->GetH()      -> 97
		//     [ctrl+0x48] = win->GetW() / 2  -> 23
		// while the window is still 46x97, and NOTHING refreshes them. Our
		// sweep then grows the window to 92x194 and the game keeps anchoring it
		// with 1x offsets, so the tip lands half a marker down-and-right of the
		// cursor - exactly "shifted down and to the right".
		//
		// ⭐ LAW: BEFORE COMPENSATING A POSITION, CHECK WHO WRITES IT LAST.
		// A per-frame writer beats any one-shot correction, and the fix has to
		// go where the STALE INPUT is produced, not where the symptom appears.
		count++;
		if (!worldAnchored) { win->GZWinMoveTo(newX - curL, newY - curT); }
		win->SetW(newW);
		win->SetH(newH);

		ScaleRecord rec = { win->GetID(), w, h, newW, newH, 0, false };
		// #191: only claim an original position if we actually moved the root.
		// A world-anchored root is re-placed by the game every frame, so a
		// recorded origL/origT would be a stale screen position that the
		// reset/re-anchor path could later restore on top of the game's own.
		rec.origL = worldAnchored ? 0 : l;
		rec.origT = worldAnchored ? 0 : t;
		rec.hasOrigPos = !worldAnchored;
		StoreScaleRecord(win, rec);
		}

		Logger::Get().WriteLine(
			LogLevel::Debug,
			"UiSpike: panel 0x%08X (%d,%d %dx%d) -> (%d,%d %dx%d)%s",
			win->GetID(), l, t, w, h, newX, newY, newW, newH,
			state == ScaleState::ResetToOriginal ? " [re-scaled after reset]" : "");
	}
	// Data-pre-scaled subtree: children already carry scaled geometry from
	// the .UI, so recursing would scale them twice (see the set above).
	if (IsDataScaledSubtreeId(win->GetID()))
	{
		return count;
	}

	// AlreadyScaled / Unrecognized: root untouched; still sweep descendants
	// for newly created windows. (AdviceList windows deeper in the subtree
	// gate their own children inside ScaleSubtree.)

	if (win->GetChildCount() > 0)
	{
		ChildSnapshot snap = {};
		win->EnumChildren(GZIID_cIGZWin, ChildSnapshot::Callback, &snap);
		int verifiedAtCount = count;   // #117: see ScaleSubtree's child loop
		for (int i = 0; i < snap.count; i++)
		{
			if (i > 0 && count != verifiedAtCount)
			{
				// CRASH KILLER: re-verify liveness (see ScaleSubtree).
				ChildSnapshot verify = {};
				win->EnumChildren(GZIID_cIGZWin, ChildSnapshot::Callback, &verify);
				// v2.69.3: mid-loop signal reset REMOVED (unsound - see ScaleSubtree).
				bool alive = false;
				for (int j = 0; j < verify.count; j++)
				{
					if (verify.wins[j] == snap.wins[i]) { alive = true; break; }
				}
				if (!alive)
				{
					continue;
				}
			}
			// #161: a panel root's own extent was rounded at ITS design origin
			// (newH = R(t+h) - R(t)), so its children must round there too or
			// a child whose edge equals the parent's height lands a pixel past
			// it. MEASURED on the god toolbar: strip (5,1011) 74x351 -> 526
			// tall, while its bottom cap at local t=351 rounded to 527 - the
			// one transparent pixel the user reported as a break in the rail.
			ScaleSubtree(snap.wins[i], f, 1, &count, false,
				rootDesignL, rootDesignT);
		}
	}

	return count;
}

void UiSpike::IncrementalPass()
{
	cISC4AppPtr pSC4App;
	if (!pSC4App)
	{
		return;
	}
	cIGZWin* pMainWindow = pSC4App->GetMainWindow();
	if (!pMainWindow)
	{
		return;
	}
	cIGZWin* pAppWin = pMainWindow->GetChildWindowFromID(kGZWin_WinSC4App);
	cIGZWin* pView = pAppWin ? pAppWin->GetChildWindowFromID(kGZWin_SC4View3DWin) : nullptr;
	if (!pView)
	{
		return;
	}

	// Same idempotent pass as the initial ScaleAll: new panels get the full
	// treatment, known panels get a descendant sweep, scaled windows are
	// skipped by Classify().
	ScalePanelsUnder(pView, "incremental");

	// In-city quit / exit-to-region confirmation dialogs. These are modal
	// popups parented under the MAIN WINDOW (not the 3D view), so the city
	// pass above never sees them. The static .UI script override does not
	// take effect for these in-city variants (the game appears to build
	// them through a code path that bypasses the DBPF override), so they
	// must be scaled at runtime. Root IDs:
	//   0xAA921F4F - "Save and Quit" / "Save and Exit to Region" (3-btn),
	//                AND the region-screen "Quit SimCity 4"/"Cancel"
	//                (2-btn, script I-4a551b4c, 330x109). #102 comment fix:
	//                "(3-btn)" alone described only two of this id's three
	//                stock scripts. See the kCityDialogIds table below.
	//   0x6AAEEC4A - "Exit to Region" / "Exit and Play City" (3-btn)
	// Guard: only scale if the root width is still at 1x design size
	// (< 400 px); if the static override ever starts working the root
	// arrives at ~540-660 px and this skip keeps us from double-scaling.
	{
		// v2.25.6: + the "Text Entry" prompt (Save City confirm, I-e9263d4c)
		// and Set Lot Size (I-e9263de5). The Batch-C static override shipped
		// in v2.25.5 and the box STILL rendered collapsed (user screenshot)
		// - the same bypass the two quit confirms have: the game builds
		// these through a code path the DBPF override never reaches. The
		// w >= 400 guard below keeps this harmless if the static override
		// ever does take effect.
		// Per-id DESIGN width (tier-math law: the old flat `w >= 400` guard
		// was a 2x-era constant - at 1.5x a scaled 249-wide Set Lot Size is
		// 374 px and would slip past 400 and re-scale). "Still at 1x" is now
		// w < designW*1.25: exact design width passes, any scaled instance
		// (factor >= 1.5) is skipped. f=2 identity: quit confirms 330 -> 412
		// threshold; unscaled 330 < 412 scales, doubled 660 >= 412 skips -
		// same behavior as the old 400 for every pre-existing id.
		//
		// v2.39.13 - PER-ID 1x BASE SIZES for the data-born EXACT-MATCH guard
		// (bases2W/H = 0 means one base). The #85 mapping falsified the single
		// threshold for the Save box: its 1x candidate set {300 stock, 500 CAM}
		// OVERLAPS its scaled set {450 stock-1.5x, 600 stock-2x}, so NO width
		// threshold can separate "arrived 1x" from "arrived data-born" - the
		// designW-560/threshold-700 pair was derived from CAM's script and left
		// the CAM-ABSENT config re-scaling our own 600x332 to 1200x664 (a 4x of
		// stock design; the mirror image of the bug v2.39.9 fixed). The guard
		// now skips iff the arrived (w,h) EQUALS round(base*f) (+-1) for one of
		// the id's known 1x bases - precise at every tier, no overlap possible.
		// Both live arrivals ever recorded for the Save box (500x175 on
		// 2026-07-30 pre-CamUI, 1000x350 on 2026-07-31) are EXACT script sizes;
		// the "auto-fits the filename" claim traced back to the falsified
		// v2.25.9 note and has never been observed.
		// v2.39.14: THREE candidate bases per id (0 = unused). v2.39.13 had
		// two and MIS-ASSIGNED which confirm script owns which id - MEASURED
		// FAILURE, mod-removed state, task #83:
		//   "in-city dialog 0xAA921F4F scaled (930,426 540x322) -> 1080x644"
		// i.e. 0xAA921F4F actually arrives at 2x of 270x161 (the size I had
		// filed under the OTHER id), so no product matched and the guard
		// re-scaled a data-born dialog to 4x on screen.
		// THE LESSON (law 23 again, in its own fix): I scoped each id to the
		// mapping I believed, and the belief was wrong. The two confirms are
		// ONE FAMILY whose script<->id mapping varies with package and mod
		// state, so every member now carries EVERY candidate base and the
		// mapping stops mattering. Safe by arithmetic: at f=1.5/2/3 the
		// products {495x236, 405x242, 405x243}, {660x314, 540x322, 540x324},
		// {990x471, 810x483, 810x486} never collide with any 1x base
		// (330x157 / 270x161 / 270x162), so a genuinely-1x arrival still
		// scales.
		// ⚠ HONEST NOTE: v2.39.11's width threshold would have SKIPPED this
		// case correctly (540 >= 412). The exact-match guard is stricter and
		// therefore fails LOUDLY when its data is wrong instead of silently
		// getting it right - which is why the data must be complete, not why
		// the guard is wrong (the threshold had its own hole: the CAM-absent
		// 600x332 arrival, which is what motivated the product match).
		// v2.64.0 (#102): widened 3 -> 4. The confirm family has a FOURTH
		// stock base (330x109, the region-screen two-button quit) that we
		// already SHIP staged at every tier; with only three slots its
		// data-born arrival matched no product and fell through to a 4x
		// resize. See the block comment on 0xAA921F4F below.
		struct CityDialog { uint32_t id; int32_t designW;
			int32_t bw[4]; int32_t bh[4]; };
		const CityDialog kCityDialogIds[] = {
			// Bases MEASURED from the corpora 2026-07-31 (stock extraction +
			// thirdparty-src + every staged tier - staged sizes are all
			// exactly RoundHalfUp(base*f), verified at 1.5x/2x/3x). Listed
			// here: stock 330x157, stock 270x161, save-warning mod 270x162.
			//
			// ⛔ #102 COMMENT-ONLY CORRECTION (2026-08-03) - THIS BLOCK USED
			// TO SAY "the confirm FAMILY's three ... Both ids carry all
			// three", i.e. it CLAIMED THE SET WAS COMPLETE. IT IS NOT.
			// THIS EDIT CHANGES NO CODE AND NO DATA - the table still holds
			// the same three bases and the guard still reads bw[0..2].
			// The stock extraction declares 0xAA921F4F as a ROOT in THREE
			// scripts, not two (id_collisions.py grades it CRITICAL):
			//   I-0a55161d area=(332,232,662,389) = 330x157  <- in the table
			//              "Save and Quit"/"Quit without Save"/"Cancel"
			//   I-6a553aa4 area=(332,232,602,393) = 270x161  <- in the table
			//              "Save and Exit to Region"/"Exit Without Saving"/
			//              "Cancel"
			//   I-4a551b4c area=(332,170,662,279) = 330x109  <- *** MISSING ***
			//              "Quit SimCity 4"/"Cancel" - the region-screen quit,
			//              a TWO-button member, which is also why the header
			//              comment's "(3-btn)" never described the family.
			// Our own build_dialog_static.py:19/:289 has named I-4a551b4c and
			// its shared root id since it was written, and STAGES it at every
			// tier: stage 660x218, stage-15x 495x164, stage-3x 990x327. So a
			// data-born 660x218 arrival is a thing WE ship.
			// ✅ FIXED v2.64.0 (2026-08-03). The consequence WAS: the
			// exact-product guard loops over bw[]/bh[], so a data-born
			// 660x218 matched no product, dataBorn stayed false, and the
			// block fell through to SetW/SetH -> 1320x436. That is the
			// v2.39.14 4x shape, inside the guard whose own note says "the
			// data must be complete". Cure applied exactly as drafted here:
			// bw[]/bh[] widened 3 -> 4, 330x109 added, loop bound now
			// kCityDialogBases. Arithmetically safe - 330x109's products
			// (495x164 / 660x218 / 990x327) collide with no 1x base, so no
			// existing member can start matching the new slot.
			// ⚠ THIS IS HARDENING, NOT A VISIBLE FIX. Per the reachability
			// note below the variant is LATENT, so there is nothing to
			// eyes-on: correct behaviour before and after is identical on
			// every path we have ever observed. What changes is what happens
			// IF that path is ever raised - 660x218 instead of 1320x436.
			// REACHABILITY, STATED HONESTLY: LATENT, not live. Disarm() on
			// kSC4MessagePreCityShutdown sets continuous=false and
			// IncrementalPass() (which owns this block) only runs while
			// continuous, so the region-screen variant is not reached with no
			// city loaded. POSITIVE CONTROL for that null: this same block DOES
			// log 0xAA921F4F whenever the in-city variant opens ("in-city
			// dialog 0xAA921F4F scaled (1065,479 270x162) -> 540x324" and
			// "DLGBORN 0xAA921F4F born 540x324"), so the instrument can see
			// this id - and across every capture in _tests/captures it has only
			// ever seen the 270x162 member, never 330x109 or 660x218.
			// UNRESOLVED: whether any in-city path can raise the 2-button
			// variant. Until that is measured, do not call this dead.
			// v2.64.0 (#102): 4th base 330x109 added to 0xAA921F4F ONLY.
			// MEASURED, not assumed: the staged script
			// tools\dialog-static\stage\T-0x00000000_G-0x96a006b0_I-
			// 0x4a551b4c.ui declares `id=0xaa921f4f area=(664,340,1324,558)`
			// = 660x218 = RoundHalfUp(330x109 * 2), and `6aaeec4a` appears
			// ZERO times in that file. The save-warning twin does not carry
			// this member, so giving it the slot would be inventing a base
			// we have never seen.
			{ 0xAA921F4F, 330, { 330, 270, 270, 330 }, { 157, 161, 162, 109 } },
			{ 0x6AAEEC4A, 330, { 330, 270, 270,   0 }, { 157, 161, 162,   0 } },
			{ 0xC9264BE2, 319, { 319,   0,   0 }, { 113,   0,   0 } },
			{ 0x8926EEBE, 249, { 249,   0,   0 }, {  92,   0,   0 } },
			// v2.25.17: the v2.25.16 entries 0x4A9DB60C/0xEBB16D71/0x0423278F
			// are REVERTED - they were identified by MWKID TIMING correlation,
			// not content, and were actually the ADVISOR TOAST family (already
			// static-doubled: 900x492 = the doubled 450x246 toast!), so the
			// runtime entry double-doubled every toast (user screenshot:
			// giant corrupted toast) while the real budget sub-dialogs stayed
			// 1x. Identity for this list must be CONTENT-matched, never
			// inferred from which dialog the user "should" have had open.
			// v2.25.20 - THE BUDGET MASTERS, with the REAL flaw fixed: their
			// ids exist TWICE (a permanent hidden template + the open
			// instance), so every earlier runtime pass found the TEMPLATE,
			// failed IsVisible(), and skipped the real dialog. The loop now
			// iterates EVERY instance of each id (IdCollectCtx). Static
			// double was separately PROVEN bypassed (deployed 1000x404 data
			// vs live 500x464 template), so runtime is the only lever -
			// exactly the Save-box treatment, per instance. designW 500 =
			// the script width (the game content-fits HEIGHT only).
			// v2.25.23: the budget masters LEFT this list for good - they are
			// data-doubled now (DialogStatic wins the load race after the
			// SelectiveArt emit fix) with their roots in kNeverScaleIds;
			// runtime scaling of a data-doubled dialog would be 4x.
			// 0x0423278F (Ordinances) also REMOVED: both runtime attempts
			// tore it (v2.25.21 off-screen, v2.25.22 row interleave) - the
			// revert law. It gets its own measured pass; it may be an
			// embedded master-B composition rather than a plain dialog.
			// 0x4C30E4FA = the Business Deals empty-state box - VWKID caught
			// it view-parented at 272x200, parking off-screen at (-272,-200)
			// when closed (still "visible", which is harmless here).
			// Bases = its measured 1x design (VWKID 272x200); not currently
			// staged by any package, so the exact-match guard only fires if a
			// future package ships it 2x - which is precisely when it should.
			{ 0x4C30E4FA, 272, { 272, 0, 0 }, { 200, 0, 0 } },  // Business Deals empty-state
			// v2.25.26: 0x0423278F is BANNED from this list PERMANENTLY -
			// third strike. v2.25.25 re-added it with designW 300 reasoning
			// the 375px guard could only ever match the small Business Deals
			// empty box - but the guard tests a SNAPSHOT while the id is a
			// LIFECYCLE: the shared transient passes through a small state,
			// takes a Fresh scale record there, and the record-owning
			// per-sweep child re-pass then doubles everything the game lays
			// into it when it becomes Ordinances (torn rows, 720x120 buttons
			// = the exe-patched 360x60 doubled again; user screenshot 11:5x).
			// The department dialogs are fully handled at the SOURCE
			// (ApplyBudgetButtonScale + art-born-2x rows); the empty box
			// needs a record-free one-shot mechanism if it is ever fixed -
			// never this list. LAW: a width guard cannot gate a window that
			// REPOPULATES - the record outlives the state that matched.
			// v2.25.9: the Save City status box, identity MEASURED by MWKID
			// (2026-07-30 01:57:58): root 0xAA8DEF97 vt=00ADC678, 500x175,
			// with ANONYMOUS children (OK 150x30, body BMP 468x98, title BMP
			// 473x25) - fully code-laid at 1x metrics, in NO .UI script,
			// which is why the three script-based fixes could never reach it.
			// designW 560: the box may auto-fit the filename, so the guard
			// threshold (700) tolerates 1x widths up to ~700 while any scaled
			// instance (>=1000) is skipped.
			// v2.39.13 (#85 mapping): TWO bases - stock script 300x166 AND
			// CAM's replacement 500x175 (CAM owns the TGI when installed; our
			// CamUI package rebuilds CAM's at 1000x350, our root DialogStatic
			// rebuilds stock at 600x332). The old designW-560/threshold-700
			// pair was derived from CAM's script only and left the CAM-ABSENT
			// config re-scaling our own 600x332 arrival to 1200x664. The 1x
			// and scaled candidate sets OVERLAP for this id (500 CAM-1x >
			// 450 stock-1.5x), so no width threshold can ever work - the
			// exact-match guard is the only correct form. Both live arrivals
			// on record (500x175, 1000x350) are exact script sizes; the
			// "auto-fits the filename" claim traced to the falsified v2.25.9
			// note and has never been observed.
			{ 0xAA8DEF97, 560, { 300, 500, 0 }, { 166, 175, 0 } },
		};
		// ============ TASK #85: THE TWO LISTS DO NOT CONTRADICT ============
		// Three ids sit in BOTH kCityDialogIds and kNeverScaleIds, and on
		// 2026-07-31 that overlap was read (by me) as a contradiction and
		// filed as a defect. It is not one - but it IS a landmine, so this
		// block turns it into a signpost that maintains itself.
		//
		// THE TWO LISTS GOVERN DIFFERENT MECHANISMS:
		//   kNeverScaleIds -> consulted at EXACTLY TWO sites, and (corrected
		//     v2.39.13 - the first version of this note misnamed them, law
		//     20/22 in its own defense of law 20/22): UiSpike::ScaleOnShow
		//     (the SHOWHOOK path, DORMANT at the shipped ShowHook=1 log-only
		//     default) and the city SWEEP's panel loop (which enumerates
		//     DIRECT view children only). NOT ScaleSubtree - membership does
		//     not protect a window from recursive descent. Its own stated
		//     invariant (~:2443) is "it is served by
		//     z_SC4UIScale_DialogStatic ... so THE SWEEP must leave it alone"
		//     - the Establish City 4x precedent (868x468 -> 1736x936).
		//   kCityDialogIds -> this block, which exists precisely BECAUSE these
		//     are main-window transients the sweep cannot reach (0xAA8DEF97
		//     is MEASURED as a direct child of pMainWindow - a sibling of
		//     WinSC4App - so the sweep's never-scale test can never even
		//     fire for it; that entry is inert insurance).
		// So "the sweep must not touch it" and "this block may size it if it
		// ever arrives unscaled" are compatible statements about one window.
		//
		// MEASURED 2026-07-31 (who_owns_tgi.py + the staged corpora), which is
		// what makes the overlap SAFE rather than merely explicable: all three
		// are data-born at EVERY scaled tier, so this block's scaling of them
		// is unreachable in any shipping configuration -
		//   0xAA8DEF97 I-ca8cbf0f 300x166 -> 450/600/900 (winner today:
		//     zzz-SC4UIScale\z_SC4UIScale_CamUI-2x.dat at 1000x350 - CAM ships
		//     a LARGER replacement script; 4 files carry the TGI)
		//   0xC9264BE2 I-e9263d4c 319x113 -> 479/638/957 (root DialogStatic)
		//   0x8926EEBE I-e9263de5 249x92  -> 374/498/747 (root DialogStatic)
		// and at stock tier the DLL renames the dats aside and is inert. The
		// entries are BELT-AND-BRACES for a package-load failure, which is why
		// they must stay GUARDED (v2.39.9/.11) rather than be deleted: delete
		// them and a failed data load renders these dialogs at 1x with no
		// mechanism left to catch it.
		//
		// ⛔ DO NOT "fix" this by consulting IsNeverScaleId here. That would
		// make the skip ABSOLUTE and throw away the belt-and-braces, to remove
		// a double-scale that the Fresh+width guard already removes by
		// MEASURED STATE (law 23: a state test must test the state).
		//
		// The assertion below is the part that maintains itself: it names the
		// overlap once per session, so the next person to see both lists finds
		// a log line explaining it - and if someone adds a NEW id to both
		// lists without thinking, the line changes and says so.
		{
			static bool overlapLogged = false;
			if (!overlapLogged)
			{
				overlapLogged = true;
				char buf[256];
				int n = 0, used = 0;
				for (const CityDialog& d : kCityDialogIds)
				{
					if (!IsNeverScaleId(d.id)) { continue; }
					n++;
					if (used < static_cast<int>(sizeof(buf)) - 16)
					{
						used += _snprintf_s(buf + used, sizeof(buf) - used,
							_TRUNCATE, "%s0x%08X", used ? " " : "", d.id);
					}
				}
				if (n > 0)
				{
					Logger::Get().WriteLine(LogLevel::Info,
						"UiSpike: DLGLISTS %d id(s) in BOTH kCityDialogIds and "
						"kNeverScaleIds (%s) - INTENDED: never-scale governs the "
						"SWEEP, this block is the transient-dialog mechanism. "
						"All are data-born at every scaled tier, so this block "
						"is their belt-and-braces for a package-load failure "
						"and is held off by the Fresh+width guard.", n, buf);
				}
			}
		}
		// #192 RESOLUTION / SCALE READOUT + the in-game scale selector
		// MOVED OUT 2026-08-19 to UiSpike::ServiceScaleSelector, driven
		// straight from the timer. It cannot live here: this function
		// needs a city view and `continuous`, so the dialog was
		// unserviced on the main menu and at the stock tier - and the
		// stock tier is exactly where the player needs the control to
		// climb back up. ONE owner writes those captions.

		const float f = settings.spikeScaleFactor;
		const int32_t scrW = pMainWindow->GetW();
		const int32_t scrH = pMainWindow->GetH();
		for (const CityDialog& dlg : kCityDialogIds)
		{
			const uint32_t dlgId = dlg.id;
			// v2.25.20: collect EVERY instance of the id - the single-find
			// returned the hidden TEMPLATE for the budget masters and the
			// visibility check then skipped the real open dialog.
			cIGZWin* found[4] = {};
			int nFound = 0;
			{
				IdCollectCtx cctx = { dlgId, found, 4, &nFound, 0 };
				pMainWindow->EnumChildren(GZIID_cIGZWin,
					IdCollectCtx::Callback, &cctx);
			}
			for (int inst = 0; inst < nFound; inst++)
			{
			cIGZWin* pDlg = found[inst];
			if (!pDlg || !pDlg->IsVisible())
			{
				continue;
			}
			const int32_t w = pDlg->GetW();
			// The two MODAL confirms. The rest of this list keeps
			// preserve-the-old-centre.
			//
			// ⚠ v2.38.1 CORRECTION TO v2.37.5. These were forced to the true
			// screen centre. THAT WAS AN OVERRIDE OF THE GAME'S OWN RULE, and
			// it is what produced the first-open jump: SC4 places the dialog,
			// we moved it 213px a tick later, and opens #2+ only looked right
			// because they inherited the moved position (an uninitialised
			// LATCH - opens #2+ are pre-warmed, not faster; the v2.36.2 law).
			//
			// SC4's placement rule, read out of its own code rather than
			// inferred (sub_0x78E2F0, and the same pair at 0x0078E0BD):
			//     0x0078E3DF  sub edi,eax ; imul 0x55555556 ... -> (H-h)/3
			//     0x0078E409  cdq ; sar eax,1                   -> (W-w)/2
			// i.e. horizontally centred, vertically ONE THIRD down - a
			// deliberate slightly-high placement. Confirmed against three
			// measured births before touching anything: h=162 -> y=479,
			// h=175 -> y=475, h=324 -> y=425, all exactly (1600-h)/3.
			//
			// So we now MATCH that rule instead of fighting it. Stock parity,
			// still drift-proof by construction (a pure function of screen and
			// dialog size, no term from the current position), and the jump
			// cannot exist because nothing moves at birth.
			const bool modalConfirm =
				(dlgId == 0xAA921F4F || dlgId == 0x6AAEEC4A);
			// ---- v2.38.0 (task #79c): THE DATA-BORN GUARD --------------
			// `designW` has been declared in this table since v2.25.6 and three
			// comment blocks describe a `w < designW*5/4` guard - but NOTHING
			// EVER READ IT. Consequence, latent to this day: 0x6AAEEC4A IS
			// data-doubled by the root DialogStatic package (660x314), so this
			// block would have scaled it AGAIN to 1320x628 the first time
			// anyone opened that variant.
			//
			// Now that the two modal confirms are born correct from data - via
			// zzz-SC4UIScale\z_SC4UIScale_SaveWarningUI when the save-warning
			// mod owns their scripts, or the root DialogStatic copy when it
			// does not - this block must not touch their SIZE at all. It still
			// centres them, which is idempotent and drift-proof.
			//
			// KEYING ON THE ARRIVED SIZE IS THE POINT: this guard does not
			// know or care WHICH package supplied the script. Mod installed,
			// mod removed, mod updated - a 1x birth still gets scaled exactly
			// as before, a 2x birth is left alone. That is what makes all
			// three states correct without a single state test.
			//
			// ⚠ v2.39.9 - THE SCOPING ABOVE WAS THE BUG, AND IT SHIPPED.
			// v2.38.0 scoped this guard to the two confirm ids "on purpose
			// (law 29 - blast radius)", documenting the Save box 0xAA8DEF97
			// as untested - and the "Saving Disabled" box arrived data-born
			// at 1000x350 and this block scaled it AGAIN. MEASURED:
			// `MWKID 0xAA8DEF97 (200,241 2000x700)` = 4x of the winning
			// script's 500x175 design, frame art tiling (user screenshot).
			// `newW > scrW` could never catch it: 2000 < 2400.
			// (v2.39.13 correction of the v2.39.9 causal note that stood
			// here: the doubled arrival was CAM's replacement script
			// rebuilt by OUR CamUI package - 2 x 1000x350 - NOT the
			// 6a553aa4 confirm-family reuse; that story came from the
			// v2.25.9 note, which the #85 mapping FALSIFIED node-for-node.)
			//
			// LAW 23 (the reason this sat latent for a day): SCOPING A GUARD
			// TO THE CASE YOU TESTED LEAVES THE UNTESTED CASES UNGUARDED.
			// When the guard's own test is on MEASURED STATE rather than
			// identity, narrowing it by id adds risk instead of removing it.
			//
			// ⚠ v2.39.13 - AND A THRESHOLD IS THE WRONG SHAPE OF STATE TEST.
			// The #85 mapping proved no width threshold can work for the Save
			// box: its 1x candidate set {300 stock, 500 CAM} OVERLAPS its
			// scaled set {450 stock-1.5x, 600 stock-2x}. The v2.39.9
			// designW-560/threshold-700 pair (derived from CAM's script) left
			// the CAM-ABSENT config re-scaling our own 600x332 root arrival
			// to 1200x664 - the mirror image of the bug it fixed. The guard
			// is now an EXACT PRODUCT MATCH: skip iff the arrived (w,h)
			// equals RoundHalfUp(base * f) +-1px for one of the id's
			// measured 1x bases (kCityDialogIds carries them; every staged
			// tier was verified to equal that product). A 1x arrival matches
			// no product and is scaled; a data-born arrival matches its
			// package's product exactly, from EITHER package, at EVERY tier.
			// Residual accepted: a foreign mod shipping this id at exactly
			// one of our product sizes would be wrongly skipped - that case
			// is undecidable by size alone and was equally wrong before.
			//
			// ⚠ v2.39.11 - AND THE WIDTH TEST ALONE IS NOT "ARRIVED SCALED".
			// v2.39.9 fixed the 4x (user-confirmed) but a 3-lens adversarial
			// review caught what the eyes-on could not see: `w >= designW*5/4`
			// is ALSO true of a window WE scaled on an earlier sweep. From the
			// next tick on, every id in this table would take this branch and
			// `continue` BEFORE the AlreadyScaled/Unrecognized child re-pass
			// below - dead-coding the very law written above it ("Any dialog
			// with a scale RECORD is OURS: run the idempotent child pass BEFORE
			// the width guard, every sweep while visible", v2.25.18, the
			// Health & Education row-overlap fix). It would also poison
			// DLGBORN, which is once-per-id: a false "data-scaled" line for a
			// window we scaled ourselves would block the real birth from ever
			// logging.
			// Classify IS the arrived-vs-ours test - it returns Fresh only when
			// no scale record of ours exists (and it erases stale/address-reused
			// records first). So: Fresh AND already-wide == genuinely born
			// scaled by DATA. Everything else falls through to the machinery
			// that has been correct since v2.25.18.
			const ScaleState dlgState = Classify(pDlg);
			// v2.39.13: EXACT PRODUCT MATCH against the id's measured 1x
			// bases (see the table comments). RoundHalfUp mirrors both the
			// builders' staging math and this DLL's own ScaleRound; +-1
			// covers edge-derived rounding. f==1 tiers never reach here
			// (the DLL is inert at stock), so the match cannot misfire on a
			// genuine 1x arrival at 1x.
			const int32_t dlgH = pDlg->GetH();
			bool dataBorn = false;
			if (dlgState == ScaleState::Fresh)
			{
				// v2.64.0 (#102): bound derived from the array, not written
				// as a literal. The 3 that used to sit here is exactly how
				// the 4th base went unread after the table was extended -
				// widening bw[]/bh[] can no longer leave this loop behind.
				const int kBaseSlots =
					static_cast<int>(sizeof(dlg.bw) / sizeof(dlg.bw[0]));
				for (int b = 0; b < kBaseSlots && !dataBorn; b++)
				{
					if (dlg.bw[b] <= 0) { continue; }
					const int32_t pw = RoundHalfUp(dlg.bw[b] * f);
					const int32_t ph = RoundHalfUp(dlg.bh[b] * f);
					if (w >= pw - 1 && w <= pw + 1
						&& dlgH >= ph - 1 && dlgH <= ph + 1)
					{
						dataBorn = true;
					}
				}
			}
			if (dataBorn)
			{
				const int32_t l = pDlg->GetL();
				const int32_t t = pDlg->GetT();
				const int32_t h = dlgH;
				// NOTHING MOVES HERE. The dialog is data-born at its true size,
				// so the game's own placement pass already put it exactly where
				// SC4 puts a dialog of that size - measured (930,425) for
				// 540x324, which is (2400-540)/2, (1600-324)/3 to the pixel.
				// Any move we make from here is a MOVE AFTER BIRTH, i.e. the
				// jump. The cure for a first-open jump is never a faster
				// correction; it is not correcting at all.
				bool logged = false;
				for (int b = 0; b < gDlgBornCount; b++)
				{
					if (gDlgBornLogged[b] == dlgId) { logged = true; break; }
				}
				if (!logged && gDlgBornCount < static_cast<int>(
					sizeof(gDlgBornLogged) / sizeof(gDlgBornLogged[0])))
				{
					gDlgBornLogged[gDlgBornCount++] = dlgId;
					// Prints the game's own placement beside what its rule
					// predicts: equal means we are at stock parity and nothing
					// needs to move. A MISMATCH is the thing to investigate -
					// never a reason to add a corrective move back in.
					Logger::Get().WriteLine(
						LogLevel::Debug,
						"UiSpike: DLGBORN 0x%08X born %dx%d at (%d,%d); SC4 rule "
						"predicts (%d,%d); left untouched (data-scaled).",
						dlgId, w, h, l, t,
						(scrW - w) / 2, (scrH - h) / 3);
				}
				continue;
			}
			// v2.39.11: Classify is now hoisted ABOVE the width guard (it is
			// what makes that guard mean "arrived scaled" rather than "is
			// currently wide"); reuse the same value here - calling it twice
			// would be wasted work on a function that also MUTATES scaleMap
			// (it erases stale records).
			const ScaleState state = dlgState;
			// v2.25.18 (Health & Education rows overlapping): the CITY SWEEP
			// scales the budget masters as hidden view-parented templates,
			// then the game CONTENT-FITS the root height at open -> Classify
			// says Unrecognized -> the old order skipped the late-children
			// pass entirely, leaving the game-created ROWS at 1x pitch
			// inside the 2x dialog. Any dialog with a scale RECORD (Already-
			// Scaled OR Unrecognized) is OURS: run the idempotent child pass
			// BEFORE the width guard, every sweep while visible.
			if (state == ScaleState::AlreadyScaled
				|| state == ScaleState::Unrecognized)
			{
				// v2.25.7 (the Save box, measured): the save flow RE-USES the
				// quit-confirm window (6a553aa4 family: logged 270x162 at the
				// save moment, and NO modal-runner call site carries a
				// "City Saved" script - all seven were enumerated from the
				// exe) and CREATES its content children AFTER our one-shot
				// pass, so they were born 1x inside the already-scaled frame.
				// Idempotent re-pass while the dialog is visible: children
				// created since the root scale get caught within one sweep;
				// everything already scaled is a no-op via scaleMap.
				int late = 0;
				ChildSnapshot lateKids = {};
				pDlg->EnumChildren(GZIID_cIGZWin, ChildSnapshot::Callback,
					&lateKids);
				for (int j = 0; j < lateKids.count; j++)
				{
					ScaleSubtree(lateKids.wins[j], f, 1, &late);
				}
				if (late > 0)
				{
					pDlg->InvalidateSelfAndParents();
					Logger::Get().WriteLine(LogLevel::Info,
						"UiSpike: in-city dialog 0x%08X LATE children: %d scaled.",
						dlgId, late);
				}
				continue;
			}
			if (state != ScaleState::Fresh && state != ScaleState::ResetToOriginal)
			{
				continue;
			}
			if (state == ScaleState::Fresh)
			{
				PurgeSubtreeRecords(pDlg, 0);
			}
			const int32_t l = pDlg->GetL();
			const int32_t t = pDlg->GetT();
			const int32_t h = pDlg->GetH();
			const int32_t newW = ScaleRound(l + w, f) - ScaleRound(l, f);
			const int32_t newH = ScaleRound(t + h, f) - ScaleRound(t, f);
			if (newW > scrW || newH > scrH)
			{
				// v2.25.16: SKIP without a dead record. Ordinances resizes
				// with content (MWKID saw 1000x970 AND 1000x554) - a dead
				// record written at the tall state froze it at 1x forever
				// even after it shrank to a size whose double fits.
				continue;
			}
			passScreenW = scrW;
			passScreenH = scrH;
			pDlg->SetW(newW);
			pDlg->SetH(newH);
			// v2.25.22 (Ordinances "can't close"): scale about the CENTER and
			// clamp on-screen. Every earlier dialog in this list was small
			// enough that keeping l,t was harmless; a 1000-wide centered
			// dialog doubled in place ran to x=2700 with Accept/Cancel/X
			// unreachable. Preserve the old center, clamp into the screen.
			// v2.37.3: the anchor must OUTLIVE the move block - the scale record
			// written after it has to store the ORIGINAL position, not the moved one.
			int32_t baseL = l;
			int32_t baseT = t;
			{
				// v2.37.3 THE CREEP FIX (task #2, measured). The quit / exit-to-region
				// confirm is re-opened carrying its PREVIOUS POSITION while its SIZE is
				// back at stock (270x162), so we re-scale it - and
				// ⚠ CORRECTION (v2.38.0, measured): "RE-OPENED on the same window
				// object" - the original wording here - is WRONG. MWKID at
				// 13:49:31.898 lists pMainWindow's children while the dialog is
				// closed and 0xAA921F4F is NOT among them, so it is not simply
				// hidden between uses. Position survives the close; the object's
				// identity does not follow from that. It matters because §4.7
				// row 1 (pre-scale while hidden) is therefore NOT available for
				// this family - a conclusion drawn from the wrong premise would
				// have sent the next fix down a dead path.
				// this centre-preserving math then ran from the position we had ALREADY
				// moved it to, shifting it a further (newW-w)/2, (newH-h)/2 on EVERY
				// open. Measured across three opens: (1065,479) -> (930,398) ->
				// (795,317) = exactly -135,-81 each time, walking the dialog off the
				// top-left of the screen.
				// Anchor on the FIRST-SEEN position. The scale record already carried
				// it (origL/origT) - it was never read back, and was then overwritten
				// with the moved position, so the anchor drifted with the dialog.
				// v2.37.4: the scaleMap record CANNOT hold this anchor. The game
				// re-opens the confirm by resetting its SIZE to stock, so
				// Classify drops the record on every open and the lookup that
				// shipped in v2.37.3 always missed - baseL fell back to the
				// already-moved position and the creep continued unchanged.
				// The anchor lives in a per-city table keyed on the dialog ID.
				{
					bool known = false;
					for (int a = 0; a < gDlgAnchorCount; a++)
					{
						if (gDlgAnchors[a].id == dlgId)
						{
							baseL = gDlgAnchors[a].l;
							baseT = gDlgAnchors[a].t;
							known = true;
							break;
						}
					}
					if (!known && gDlgAnchorCount
						< static_cast<int>(sizeof(gDlgAnchors) / sizeof(gDlgAnchors[0])))
					{
						gDlgAnchors[gDlgAnchorCount].id = dlgId;
						gDlgAnchors[gDlgAnchorCount].l = l;
						gDlgAnchors[gDlgAnchorCount].t = t;
						gDlgAnchorCount++;
					}
				}
				// v2.37.5 (user report), CORRECTED v2.38.1: the QUIT /
				// EXIT-TO-REGION confirms were landing high AND left - measured
				// 540x324 at (795,317) on 2400x1600 - because scaling about
				// their own centre maps the 800x600 design position nowhere in
				// particular, and the creep then walked them further.
				// v2.37.5 forced the true screen centre, which fixed the
				// symptom and introduced a first-open JUMP once the dialog
				// became data-born: SC4 had already placed it correctly and we
				// moved it 213px afterwards.
				//
				// Now we APPLY SC4'S OWN RULE for the scaled size - x=(W-w)/2,
				// y=(H-h)/3, read out of the game at 0x0078E3DF / 0x0078E409 -
				// so this path agrees with where the data-born path leaves the
				// dialog. Only reachable now when the dialog arrives at 1x
				// (a mod update trips the package gate), and it lands on the
				// same pixel the data-born path would.
				//
				// It is DRIFT-PROOF BY CONSTRUCTION: the target is a pure
				// function of the screen and the dialog size, with no term
				// taken from the dialog's current position, so it cannot
				// compound however many times it runs. That is a strictly better
				// property than the v2.37.4 anchor table, which only avoids
				// drift by remembering where the dialog started.
				// Scoped to the two modal confirms ONLY - the rest of
				// kCityDialogIds (budget masters, Save box, text entry) keep the
				// preserve-the-old-centre behaviour they were tuned with.
				// (v2.38.0: `modalConfirm` is now declared above, so the
				// data-born guard can share it.)
				int32_t nl;
				int32_t nt;
				if (modalConfirm)
				{
					nl = (scrW - newW) / 2;   // SC4's own rule, 0x0078E409
					nt = (scrH - newH) / 3;   // SC4's own rule, 0x0078E3DF
				}
				else
				{
					nl = baseL + w / 2 - newW / 2;
					nt = baseT + h / 2 - newH / 2;
				}
				if (nl + newW > scrW) { nl = scrW - newW; }
				if (nt + newH > scrH) { nt = scrH - newH; }
				if (nl < 0) { nl = 0; }
				if (nt < 0) { nt = 0; }
				if (nl != l || nt != t)
				{
					pDlg->GZWinMoveTo(nl - l, nt - t);
					// The instrument I claimed in v2.37.3 and did not actually
					// add. Info level so a zero count is a real measurement.
					Logger::Get().WriteLine(LogLevel::Info,
						"UiSpike: DLGPOS 0x%08X anchor(%d,%d) (%d,%d)->(%d,%d).",
						dlgId, baseL, baseT, l, t, nl, nt);
				}
			}

			ScaleRecord rec = { pDlg->GetID(), w, h, newW, newH, 0, false };
			// v2.37.3: carry the ORIGINAL anchor forward, never the moved one -
			// writing the post-move position here is what let the anchor drift.
			rec.origL = baseL;
			rec.origT = baseT;
			rec.hasOrigPos = true;
			StoreScaleRecord(pDlg, rec);

			int cnt = 0;
			ChildSnapshot snap = {};
			pDlg->EnumChildren(GZIID_cIGZWin, ChildSnapshot::Callback, &snap);
			for (int j = 0; j < snap.count; j++)
			{
				ScaleSubtree(snap.wins[j], f, 1, &cnt);
			}
			// BMPRECT (v2.25.10): the game bypasses our staged .UI for these,
			// so GZWinBMP children carry 1x imagerects against 2x-staged art
			// (9-slice stripes). One-shot per Fresh instance - see the walk
			// struct above.
			int rectFixed = 0;
			{
				BmpRectCtx rctx = { f, &rectFixed, 0 };
				pDlg->EnumChildren(GZIID_cIGZWin, BmpRectWalk::Callback, &rctx);
			}
			Logger::Get().WriteLine(
				LogLevel::Info,
				"UiSpike: in-city dialog 0x%08X scaled (%d,%d %dx%d) -> %dx%d, %d descendants, %d imagerects x%.2f",
				dlgId, l, t, w, h, newW, newH, cnt, rectFixed, f);
			} // per-instance
		}
	}

	// MWKID (v2.25.8, permanent instrument): CHANGE-ONLY dump of the main
	// window's direct children + one level below. Three Save-box fixes in a
	// row missed because the box's IDENTITY was inferred; this logs every
	// transient dialog's id, CLASS VTABLE and rect the moment it appears or
	// changes visibility, so the next unknown box identifies itself from the
	// user's own session log. Cost: one enum per sweep + a hash; log lines
	// only when the top-level set actually changes (dialog open/close).
	{
		static uint32_t mwkidSig = 0;
		ChildSnapshot mk = {};
		pMainWindow->EnumChildren(GZIID_cIGZWin, ChildSnapshot::Callback, &mk);
		uint32_t sig = static_cast<uint32_t>(mk.count);
		for (int i = 0; i < mk.count; i++)
		{
			cIGZWin* w = mk.wins[i];
			if (!w) { continue; }
			sig = sig * 31u + w->GetID() + (w->IsVisible() ? 1u : 0u)
				+ static_cast<uint32_t>(w->GetW()) * 7u
				// v2.26.9: fold in the CHILD COUNT. A window that opens one
				// level down (the ordinance description popup) never altered
				// the top-level hash, so the dump never fired and POPKID
				// stayed empty even with the popup on screen.
				+ static_cast<uint32_t>(w->GetChildCount()) * 1009u;
		}
		if (sig != mwkidSig)
		{
			mwkidSig = sig;
			for (int i = 0; i < mk.count; i++)
			{
				cIGZWin* w = mk.wins[i];
				if (!w) { continue; }
				Logger::Get().WriteLine(LogLevel::Debug,
					"UiSpike: MWKID %2d id=0x%08X vt=%p (%d,%d %dx%d) vis=%d",
					i, w->GetID(), *reinterpret_cast<void**>(w),
					w->GetL(), w->GetT(), w->GetW(), w->GetH(),
					w->IsVisible() ? 1 : 0);
				if (!w->IsVisible()) { continue; }
				ChildSnapshot sub = {};
				w->EnumChildren(GZIID_cIGZWin, ChildSnapshot::Callback, &sub);
				// v2.25.31: cap raised 24 -> 48. The budget dept dialogs'
				// HEADER texts (0xABCDE01/02) and section boxes sat just past
				// 24 and the header-float defect could not be measured.
				for (int j = 0; j < sub.count && j < 48; j++)
				{
					cIGZWin* c = sub.wins[j];
					if (!c) { continue; }
					Logger::Get().WriteLine(LogLevel::Debug,
						"UiSpike: MWKID %2d.%-2d id=0x%08X vt=%p (%d,%d %dx%d) vis=%d",
						i, j, c->GetID(), *reinterpret_cast<void**>(c),
						c->GetL(), c->GetT(), c->GetW(), c->GetH(),
						c->IsVisible() ? 1 : 0);
					// v2.26.7: the shared TEXT POPUP 0x0423278D (Business Deals
					// empty box AND the ordinance description) draws its title over
					// its body (user: "crushed box"). Its title/body live one level
					// deeper than MWKID prints, so dump them for that id only.
					if (c->GetID() == 0x0423278D)
					{
						ChildSnapshot pk = {};
						c->EnumChildren(GZIID_cIGZWin, ChildSnapshot::Callback, &pk);
						for (int q = 0; q < pk.count && q < 12; q++)
						{
							cIGZWin* d = pk.wins[q];
							if (!d) { continue; }
							Logger::Get().WriteLine(LogLevel::Debug,
								"UiSpike: POPKID %d id=0x%08X vt=%p (%d,%d %dx%d) vis=%d",
								q, d->GetID(), *reinterpret_cast<void**>(d),
								d->GetL(), d->GetT(), d->GetW(), d->GetH(),
								d->IsVisible() ? 1 : 0);
							// v2.26.8: one level deeper - the TITLE and BODY text
							// windows live under the popup's full-size content
							// child, which is why they never appeared.
							ChildSnapshot pg = {};
							d->EnumChildren(GZIID_cIGZWin, ChildSnapshot::Callback, &pg);
							for (int r = 0; r < pg.count && r < 12; r++)
							{
								cIGZWin* e = pg.wins[r];
								if (!e) { continue; }
								Logger::Get().WriteLine(LogLevel::Debug,
									"UiSpike: POPKID %d.%-2d id=0x%08X vt=%p (%d,%d %dx%d) vis=%d",
									q, r, e->GetID(), *reinterpret_cast<void**>(e),
									e->GetL(), e->GetT(), e->GetW(), e->GetH(),
									e->IsVisible() ? 1 : 0);
							}
						}
					}
				}
			}
		}
	}

	// NOTCHPIN (v2.25.30): the slider-department category rows carry a
	// STOCK 16-wide funding-notch bitmap (ids 0x0ABCE2xx) whose x=339 is
	// COMPOSED at runtime - no literal 339 exists anywhere in the exe
	// (whole-image scan), so no byte patch can move it. With v2.25.29's
	// name column at 96, long 2x category names run under it. Cure = the
	// law-6 PIN-BACK pattern (DVPIN / RCI columns): while the budget
	// transient is visible, re-seat each notch proportionally on its LIVE
	// slider sibling (stock: 79 into a 110-wide track). Position-only, no
	// scale record, and idempotent - once moved its x is no longer 339.
	// Deals rows (same id family beside combos) have no slider sibling
	// and are left untouched. Worst case on any miss: the notch stays at
	// 339, exactly today's cosmetic state.
	// v2.26.4: iterate EVERY 0x0423278F instance. The master budget
	// sub-dialog shares the department dialog's id and both are open at
	// once (MWKID 14:41:56 showed 0 = master 1300x338, 1 = department
	// 1000x554), so GetChildWindowFromID returned only one of them - the
	// pins and the BHDR dump were running on whichever came first.
	if (settings.spikeBudgetDeptPatch)
	{
		ChildSnapshot mwAll = {};
		pMainWindow->EnumChildren(GZIID_cIGZWin, ChildSnapshot::Callback, &mwAll);
		for (int bi = 0; bi < mwAll.count; bi++)
		{
		cIGZWin* pBudgetDlg = mwAll.wins[bi];
		if (pBudgetDlg && pBudgetDlg->GetID() == 0x0423278F && pBudgetDlg->IsVisible())
		{
			ChildSnapshot dc = {};
			pBudgetDlg->EnumChildren(GZIID_cIGZWin, ChildSnapshot::Callback, &dc);
			for (int i = 0; i < dc.count; i++)
			{
				cIGZWin* c = dc.wins[i];
				if (!c) { continue; }
				const uint32_t cid = c->GetID();
				if ((cid & 0xFFFFFF00u) != 0x0ABCE200u) { continue; }
				// #128 (v2.73.1): this gate USED to read `!= 16`. 16 is 8*2 -
				// a 2x-baked literal. The notch is ART-DERIVED (art 0x140155C8
				// is 8x18 at 1x), so its live width is 8*f: 12 at 1.5x, 16 at
				// 2x, 24 at 3x. The equality therefore matched ONLY at 2x, and
				// at every other tier this pin silently re-seated NOTHING -
				// leaving each department's funding rule wherever the game
				// composed it, unattached to its slider. That is the user's
				// "white lines in budget are broken" at 3x, and the block's own
				// comment above records the same sentence from the 2x era.
				// Derived, not constant - and it reduces to 16 at f=2 exactly,
				// so the confirmed 2x layout cannot move (HANDOFF.md law: "a
				// tier is not 2x with rounding"; replace the constant with its
				// derivation AND prove the derivation reduces to it at f=2).
				const int32_t kNotchW =
					RoundHalfUp(8.0 * settings.spikeScaleFactor);
				if (c->GetW() != kNotchW) { continue; }
				// v2.26.2: pair by SLIDER FAMILY, not by a single hardcoded
				// x. Department rows use sliders 0x0ABCDF0k (stock track 110,
				// notch 79); the MASTER budget rows use two slider columns
				// 0x0ABCE40k / 0x0ABCE50k (stock track 90, notch offset 63,
				// both measured live 2026-07-30). The notch belongs to the
				// nearest slider at or left of it in the same row.
				// v2.26.5: DETERMINISTIC id pairing, no position test. v2.26.2
				// added a "nearest slider at or left of the notch" test that
				// rejected the correct slider whenever the notch was still at its
				// stock x (dept: notch 339 vs slider 520) - the pin silently
				// stopped firing (user: white lines wrong on every department
				// flyout). Mapping MEASURED 2026-07-30:
				//   department  notch 0x0ABCE20k  <-> slider 0x0ABCDF0k (63/90 n/a,
				//                                    stock offset 79 of track 110)
				//   master      notch index n     <-> row n/2, column n%2 ->
				//               slider 0x0ABCE400|row / 0x0ABCE500|row (63 of 90)
				const uint32_t k = cid & 0xFFu;
				int32_t off = 79, trackW = 110;
				cIGZWin* sl = pBudgetDlg->GetChildWindowFromID(0x0ABCDF00u | k);
				if (!sl || sl->GetT() != c->GetT())
				{
					const uint32_t row = k >> 1, col = k & 1u;
					sl = pBudgetDlg->GetChildWindowFromID(
						(col ? 0x0ABCE500u : 0x0ABCE400u) | row);
					off = 63; trackW = 90;
				}
				if (!sl || sl->GetT() != c->GetT()) { continue; }
				const int32_t nx =
					sl->GetL() + (off * sl->GetW() + trackW / 2) / trackW;
				if (nx == c->GetL()) { continue; }   // already seated
				c->GZWinMoveTo(nx - c->GetL(), 0);
			}

			// COMBO WIDTH PIN (v2.26.0): Neighbor Deals' GZWinCombo width is
			// `lea edi,[edx+0x78]` inside sub_7798C0 - a disp8 (max 127)
			// that cannot encode 120*f at f>=1.07, so no byte patch exists
			// (the "7000M" truncation). The combo class re-lays its own
			// drop arrow from its area, so widening the window is the whole
			// fix. Idempotent: gate on the exact stock width; no record.
			//
			// #185 RESIDUE (v3.0.2): +1px Y RE-SEAT AT FRACTIONAL TIERS ONLY.
			// The combo's y inside its row is cursor+1 - a one-byte `inc eax`
			// at 0x77F813 (x12 row twins) that CANNOT hold a scaled value -
			// and the class then insets its drop-arrow oval 1px further (both
			// measured at 1x: pill border row 72, fill row 73, arrow top row
			// 74 = 1 fill row of clearance). The pill art's border thickness
			// is R(1*f) px (measured in the shipped sheets: 1/2/2/3 at
			// 1x/1.5x/2x/3x), so the arrow lands at rowTop+2 at EVERY tier
			// while the interior starts at rowTop+R(f): at 1.5x the clearance
			// is 2-R(1.5) = 0 and the dark oval fuses into the pill's top
			// border (user: "the dark blue oval is getting cut off as it goes
			// across the top", Screenshot 2026-08-17 103229, rows measured:
			// gap 0 above / 2 below vs 1/1 at 1x). 2x shares the 0-gap and is
			// USER-CONFIRMED as shipped, so the confirmed integer tiers must
			// not move: dy = R(f) - floor(f) restores the 1x clearance at
			// fractional tiers and is PROVABLY 0 at every integer f (R(k)=k).
			//   f=1.5: dy=+1 -> combo [rowTop+2..], arrow oval clearance 1/1.
			//   f=1, 2, 3: dy=0 - byte-for-byte the confirmed behavior.
			// Same idempotence as the width pin: the move rides the one-shot
			// width gate (GetW()==120), so a dialog rebuild resets BOTH and
			// the pin re-applies BOTH. GZWinMoveTo is RELATIVE (law: measured
			// 2026-08-06).
			{
				const int32_t comboW =
					static_cast<int32_t>(std::lround(120.0 * settings.spikeScaleFactor));
				const int32_t comboDy =
					RoundHalfUp(settings.spikeScaleFactor)
					- static_cast<int32_t>(std::floor(settings.spikeScaleFactor));
				// ⚠ COMPOUNDING GUARDRAIL (review 2026-08-17, finding 3): the
				// dy is RELATIVE and its idempotence is borrowed from the
				// width gate - safe only while nothing restores W to 120
				// without also restoring T. The master column pin 15 lines
				// below exists precisely because this dialog's re-lay CAN
				// rewrite values per refresh. So every application is COUNTED
				// and logged per epoch: a count that keeps climbing while one
				// dialog sits open is the compounding signature, visible in
				// the first session instead of as a combo marching out of its
				// pill at +1px per tick. (SetW alone was value-idempotent and
				// would have hidden this class forever.)
				if (comboW != 120)
				{
					static int comboDyEpoch = -1;
					static int comboDyCount = 0;
					if (comboDyEpoch != gGaugeEpoch)
					{
						comboDyEpoch = gGaugeEpoch;
						comboDyCount = 0;
					}
					for (int i = 0; i < dc.count; i++)
					{
						cIGZWin* c = dc.wins[i];
						if (!c) { continue; }
						if ((c->GetID() & 0xFFFFFF00u) != 0x0ABCE100u) { continue; }
						if (c->GetW() != 120) { continue; }
						c->SetW(comboW);
						if (comboDy != 0)
						{
							c->GZWinMoveTo(0, comboDy);
							comboDyCount++;
							if (comboDyCount <= 6 || (comboDyCount % 50) == 0)
							{
								Logger::Get().WriteLine(LogLevel::Info,
									"UiSpike: COMBODY #%d id=0x%08X +%dpx "
									"(a climbing count with ONE dialog open = "
									"compounding; expected: combos-per-dialog "
									"x opens)",
									comboDyCount, c->GetID(), comboDy);
							}
						}
					}
				}
			}

			// BHDR (v2.25.32, measurement): the content pane 0x0423278E
			// hosts the dept TITLE (0xABCDE00), the floating "Monthly
			// Expense/Estimate" HEADERS (0xABCDE01/02) and the name/count
			// windows - one level below what MWKID prints. Change-only dump
			// of its children so the header-float fix comes from measured
			// rects, not screenshot estimates.
			cIGZWin* pPane = pBudgetDlg->GetChildWindowFromID(0x0423278E);
			if (pPane)
			{
			// MASTER COLUMN WIDTH PIN (v2.26.6). MEASURED (BHDR 15:33:38,
			// master 1300x338): the capacity texts sit at (800, w127) and the
			// monthly/subtotal texts at (1040, w127) - x correct, width stuck
			// at the push-imm8 ceiling instead of 120f/85f, which is why
			// "45055/54727" clipped to "45055/54" (stock shows it in full,
			// _tests\captures\stock-budget\stock-1024-master-151212.png).
			// 240 and 170 cannot be encoded in those instructions, so the
			// windows are widened here: L is already right, the helper places
			// the window AT x (right-alignment happens inside it), and stock
			// adjacency 400+120=520 reproduces exactly as 800+240=1040.
			// Gated on a master-only slider id; idempotent. MUST run every
			// sweep: v2.26.5 put it inside the change-only dump branch and
			// the dialog's own per-refresh re-lay simply overwrote it.
			if (pBudgetDlg->GetChildWindowFromID(0x0ABCE400u))
			{
				const float mf = settings.spikeScaleFactor;
				const int32_t capX = static_cast<int32_t>(std::lround(400.0 * mf));
				const int32_t capW = static_cast<int32_t>(std::lround(120.0 * mf));
				const int32_t monX = static_cast<int32_t>(std::lround(520.0 * mf));
				const int32_t monW = static_cast<int32_t>(std::lround(85.0 * mf));
				ChildSnapshot wp = {};
				pPane->EnumChildren(GZIID_cIGZWin, ChildSnapshot::Callback, &wp);
				for (int i = 0; i < wp.count; i++)
				{
					cIGZWin* t = wp.wins[i];
					if (!t) { continue; }
					if ((t->GetID() & 0xFFFFFF00u) != 0x0ABCDE00u) { continue; }
					int32_t want = 0;
					if (t->GetL() == capX) { want = capW; }
					else if (t->GetL() == monX) { want = monW; }
					if (want == 0 || t->GetW() == want) { continue; }
					t->SetW(want);
					// v2.26.7: widening alone was not enough - the text kept
					// rendering clipped at its ORIGINAL width (the paint buffer
					// is born at first-paint size, the same law as the U-Drive-It
					// consoles). Re-applying the caption forces the text object to
					// re-measure and re-render into the new rect.
					cIGZString* cap = t->GetCaption();
					if (cap) { t->SetCaption(*cap); }
				}

				// v2.26.4: one signature PER INSTANCE - the master and the
				// department dialog share id 0x0423278F and are open at once,
				// so a single hash swallowed the second one.
				static uint32_t bhdrSigs[4] = { 0, 0, 0, 0 };
				uint32_t& bhdrSig = bhdrSigs[bi & 3];
				ChildSnapshot pc = {};
				pPane->EnumChildren(GZIID_cIGZWin, ChildSnapshot::Callback, &pc);
				uint32_t sig = static_cast<uint32_t>(pc.count)
					+ static_cast<uint32_t>(pBudgetDlg->GetW()) * 131u;
				for (int i = 0; i < pc.count; i++)
				{
					cIGZWin* c = pc.wins[i];
					if (!c) { continue; }
					sig = sig * 31u + c->GetID() + static_cast<uint32_t>(c->GetT()) * 7u;
				}
				if (sig != bhdrSig)
				{
					bhdrSig = sig;
					Logger::Get().WriteLine(LogLevel::Debug,
						"UiSpike: BHDR instance %d dlg (%d,%d %dx%d) pane children=%d",
						bi, pBudgetDlg->GetL(), pBudgetDlg->GetT(),
						pBudgetDlg->GetW(), pBudgetDlg->GetH(), pc.count);
					for (int i = 0; i < pc.count && i < 48; i++)
					{
						cIGZWin* c = pc.wins[i];
						if (!c) { continue; }
						Logger::Get().WriteLine(LogLevel::Debug,
							"UiSpike: BHDR %2d id=0x%08X vt=%p (%d,%d %dx%d) vis=%d",
							i, c->GetID(), *reinterpret_cast<void**>(c),
							c->GetL(), c->GetT(), c->GetW(), c->GetH(),
							c->IsVisible() ? 1 : 0);
						// v2.25.33: one level deeper for the anonymous band /
						// slab BMPs - the scroll arrows live below them and
						// appeared in NO dump so far.
						if (c->GetID() != 0) { continue; }
						ChildSnapshot gc = {};
						c->EnumChildren(GZIID_cIGZWin, ChildSnapshot::Callback, &gc);
						for (int j = 0; j < gc.count && j < 16; j++)
						{
							cIGZWin* g = gc.wins[j];
							if (!g) { continue; }
							Logger::Get().WriteLine(LogLevel::Debug,
								"UiSpike: BHDR %2d.%-2d id=0x%08X vt=%p (%d,%d %dx%d) vis=%d",
								i, j, g->GetID(), *reinterpret_cast<void**>(g),
								g->GetL(), g->GetT(), g->GetW(), g->GetH(),
								g->IsVisible() ? 1 : 0);
						}
					}

					// v2.26.0: the v2.25.33/.34 BMPX band hooks are GONE for
					// good. The full decode (BUDGET-DETAIL-ANATOMY.md) proved
					// the band/slab stack is art-height driven and our 2x
					// D-series art already renders it at exactly stock x2
					// through the same plain-blit path as the slabs - the
					// hook was doubling an ALREADY-2x source (the stripes,
					// and the prime suspect for the gray band). Nothing to
					// hook here; the bands need no help.

				}
				}
			}
		}
		}   // per-instance loop (v2.26.4)

		// SHARED TEXT POPUP 0x0423278D - THE BOX WAS NEVER SCALED (v2.28.2).
		// Settled by offline emulation of the builder (tools\uimap\emu), which
		// reproduces every measured rect exactly:
		//
		//   * the body is created with align 0x63 = FILL (push 0x63 @0x78BA69)
		//     and the fill branch (0x779793-0x7797D2) calls SetArea(x, y,
		//     parentW-2x, parentH-y) - it OVERWRITES all four edges and
		//     discards the text extent. So body W = parentW-3x, H = parentH-2y
		//     for ANY string in ANY font. The measured 795x75 was the body at
		//     (15,25); 750x25 is the same body after v2.27.0 moved it to
		//     (30,50). The "3 lines vs 1 line" reading was an artifact of two
		//     dumps straddling that patch, not a wrap.
		//   * `push 0x3e8` (1000) at 0x77971A is NOT a wrap width: it is
		//     applied AFTER the only layout call (FitWindowToText @0x7796D8)
		//     and is then overwritten by the fill branch. Refuted on ORDERING.
		//
		// The real defect is geometric and ours: the popup's own constants
		// were never scaled - height 125 (push 0x7d @0x78B99F, twice), right
		// margin 60 (sub ebx,0x3c @0x78B9A1), x 30 (push 0x1e @0x78B9D7) and
		// the y clamp -125 (add eax,-0x7d @0x78B9C3). At 2x the box is
		// 840x125 where round(stock*f) is 780x250, so the body lands 25px
		// tall - which cannot hold ONE line of Arta 28. THAT is the clip.
		// The margin and x are byte-patched (CodePatches); 250 and -250
		// exceed the imm8 ceiling, so the height and the clamp are pinned
		// here. Pin rules (laws 14/18/19): runs on the SWEEP, size+position
		// only, no scale record, idempotent (the target is a fixed
		// round(stock*f), so re-applying it is a no-op), and its test does
		// not depend on the state it corrects.
		if (settings.spikePopupWrap)
		for (int bi = 0; bi < mwAll.count; bi++)
		{
			cIGZWin* host = mwAll.wins[bi];
			if (!host || !host->IsVisible()) { continue; }
			cIGZWin* pop = host->GetChildWindowFromID(0x0423278D);
			if (!pop || !pop->IsVisible()) { continue; }
			cIGZWin* content = pop->GetChildWindowFromID(0x0423278F);
			if (!content) { continue; }

			// ================= TWIN GATE (v2.63.0, task #110) =================
			// Window 0x0423278D is built by TWO functions with DIFFERENT stock
			// heights, and until now this pin applied the ordinance twin's 125
			// to both:
			//
			//   sub_78B120  ordinance DESCRIPTION popup - stock H 125
			//               (push 0x7d @0x78B99F), backdrop 0x384 / outer 0x484.
			//               Host = the Ordinances dialog, ~754 tall at 2x, so
			//               the clamp below never fires. THIS is what the pin
			//               was written for (v2.28.2) and it is correct.
			//   sub_77BEC0  the generic "no entries in the budget ledger" box -
			//               stock H 100 (push 0x64 @0x77C19E + 4 more), backdrop
			//               0x385 / outer 0x485, close-X 0xCC / outer 0x1CC.
			//               Called from 0x77C7E6 Ordinances, 0x77F51A Neighbor
			//               Deals, 0x786BA2 Transportation and 0x78826D EVERY
			//               department page.
			//
			// THE #110 DEFECT, measured and then user-confirmed on both sides:
			// for the ledger twin the HOST IS THE BOX - a top-level 600x127
			// window - because CodePatches clamps its five SetSize sites to the
			// `push imm8` ceiling (round(100*f)=200 cannot encode, so it ships
			// 127 at every tier >= 1.28x). Pinning the popup to 250 inside a
			// 127-tall host made the clamp below fire with hostH - wantH =
			// 127 - 250 = -123, so the popup - and with it the close-X at
			// popup-local y=22 - sat at host-local y=-101, ABOVE the host rect.
			// The sprite still drew (the engine does not clip it) but the
			// router's hit walk only descends into children whose rect contains
			// the point, so the click never reached the X.
			// LOGGED 19 TIMES as `POPBOX 600x127 -> 600x250 at y=-123`.
			//
			// PROVEN, not argued: at 1x with the whole layer parked the X closes
			// the box (stock control, user-confirmed) - so #103's "stock has no
			// close handler" verdict is REFUTED. Its gate decoded the command
			// dispatch correctly but nothing ever established that a click on
			// the X ARRIVES there as command 0xCC; it does not. Then at 2x with
			// PopupWrap=0 the X closed again - which isolates this pin as the
			// cause, and simultaneously reintroduced the ordinance twin's text
			// clip, which is why the cure is per-twin and not a kill switch.
			//
			// THE COUPLED SET (law: all or none). The frame is drawn by the
			// backdrop pair, so lifting the popup alone leaves a dead band and
			// lifting nothing leaves the body at parentH-2y = 27px - less than
			// one line of Arta 28. Host + popup + content + 0x485 + 0x385 move
			// together to round(100*f); the popup then fits its host, the clamp
			// is a no-op, the X lands inside the host rect, and the body fill
			// below has 100px to wrap in.
			const bool ordinanceTwin =
				(pop->GetChildWindowFromIDRecursive(0x00000484) != nullptr);
			const bool ledgerTwin =
				(pop->GetChildWindowFromIDRecursive(0x00000485) != nullptr);

			const float pf = settings.spikeScaleFactor;
			// Each twin reduces to ITS OWN stock height at f=1.
			const double stockPopH = ordinanceTwin ? 125.0 : 100.0;
			const int32_t wantH =
				static_cast<int32_t>(std::lround(stockPopH * pf));
			const int32_t haveH = pop->GetH();

			// POPSEEN: the reachability line this pin never had. Unconditional,
			// one per popup instance, so its ABSENCE is finally evidence.
			{
				static cIGZWin* gPopSeen = nullptr;
				if (pop != gPopSeen)
				{
					gPopSeen = pop;
					Logger::Get().WriteLine(LogLevel::Info,
						"UiSpike: POPSEEN 0x0423278D host 0x%08X (%dx%d) pop "
						"(%d,%d %dx%d) twin=%s stockH=%d wantH=%d",
						host->GetID(), host->GetW(), host->GetH(),
						pop->GetL(), pop->GetT(), pop->GetW(), pop->GetH(),
						ordinanceTwin ? "ordinance(0x484)"
							: (ledgerTwin ? "empty-ledger(0x485)" : "UNKNOWN"),
						static_cast<int>(stockPopH), wantH);
				}
			}
			// Fail closed: an unknown third builder is left entirely alone.
			if (!ordinanceTwin && !ledgerTwin) { continue; }
			if (haveH == wantH) { continue; }   // already pinned - idempotent

			if (ledgerTwin)
			{
				// Grow the FRAME with the window, or the dead band and the
				// negative-y clamp both come straight back. The host is only
				// grown, never shrunk - from the other three callers it is a
				// full dialog that is already big enough.
				if (host->GetH() < wantH) { host->SetH(wantH); }
				cIGZWin* outerBack = pop->GetChildWindowFromID(0x00000485);
				cIGZWin* innerBack = outerBack
					? outerBack->GetChildWindowFromID(0x00000385) : nullptr;
				if (outerBack) { outerBack->SetH(wantH); }
				if (innerBack) { innerBack->SetH(wantH); }
			}

			pop->SetH(wantH);
			content->SetH(wantH);

			// The builder clamps the popup's y to parentH-125; with the box
			// twice as tall that clamp is 125*f short, so a popup opened low
			// in the dialog would hang past the bottom. Same math, applied to
			// the live rect. For the ledger twin the host was just grown to
			// match, so this is a no-op there BY CONSTRUCTION - which is
			// exactly what keeps the close-X inside the host rect.
			int32_t movedTo = pop->GetT();
			const int32_t hostH = host->GetH();
			if (hostH > 0 && movedTo + wantH > hostH)
			{
				const int32_t clamped = hostH - wantH;
				pop->GZWinMoveTo(0, clamped - movedTo);   // RELATIVE (law)
				movedTo = clamped;
			}

			// v2.28.3: growing the FRAME is not enough. The fill branch sized
			// the body ONCE, at creation, as parentH-2y - so it stayed 25px
			// tall inside the now-250px box (measured: POPBOX said 780x250
			// while POPKID still read body 690x25). Re-apply the builder's own
			// formula at the corrected parent height; that is the same math
			// the exe would have produced had the box been right to begin
			// with, and it reduces to stock at f=1.
			cIGZWin* body = content->GetChildWindowFromID(0x0ABCE001);
			int32_t natW = -1, natH = -1;
			if (body)
			{
				const int32_t by = body->GetT();
				const int32_t fillH = wantH - by * 2;

				// v2.28.4 - THE ACTUAL CAUSE, traced in the text class itself
				// (0x009BF486, offline emulation):
				//
				//   w = [this+0x160]            (the wrap width)
				//   w == 0 || flags & 0x0200 -> ONE line, no breaks
				//   flags & 0x0002           -> WORD WRAP at w
				//   else                     -> break at '\n' ONLY, then clip
				//
				// `flags` is [this+0x128], the field SetWinTextFlag writes,
				// and its CONSTRUCTOR DEFAULT IS 0 (0x009C026C) - so the
				// description was in the third regime all along: it broke only
				// where the string itself carries a newline and clipped the
				// rest. It never word-wrapped. That is why re-applying the
				// caption, FitWindowToText and clear-and-restore all did
				// nothing (v2.27.1/.2/.3), and it explains both live
				// screenshots: an early break with space to spare = a hard
				// newline; a mid-word cut at the box edge = a newline segment
				// wider than the box.
				//
				// The wrap width is NOT a constant anywhere - it is
				// GetW() - 2*gutter (gutter default 5, so GetW()-10),
				// recomputed by the class's own SetArea override
				// (0x009BFCA5 -> sub_9BCBC5 -> sub_9BF98B re-breaks lines).
				// So: turn word-wrap ON, then resize. The resize below IS the
				// trigger, and the engine then wraps at GetW()-10 at EVERY
				// tier by itself - 335 at 1x, 680 at 2x, 1025 at 3x - with no
				// string handling and no constant of ours.
				int32_t hadWrap = -1;
				cIGZWinText* txt = nullptr;
				if (body->QueryInterface(GZIID_cIGZWinText,
						reinterpret_cast<void**>(&txt)) && txt)
				{
					// Read BEFORE writing: the emulator's field map is proven
					// for the class at 0x009BC000-0x009C1000, but that THIS
					// window is that class was HYPOTHESIS. false here confirms
					// the whole diagnosis; true means a different class and
					// the newline-only reading is wrong.
					hadWrap = txt->GetWinTextFlag(0x0002) ? 1 : 0;
					txt->SetWinTextFlag(0x0002, true);
					txt->Release();
				}

				body->SetW(pop->GetW() - body->GetL() * 3);
				if (fillH > 0) { body->SetH(fillH); }
				natW = body->GetW() - 10;   // the wrap width now in force
				natH = hadWrap;
			}
			Logger::Get().WriteLine(LogLevel::Info,
				"UiSpike: POPBOX %dx%d -> %dx%d at y=%d (x%.2f of stock "
				"390x125); body (%d,%d %dx%d), wrap width %d, wrap flag was %d.",
				pop->GetW(), haveH, pop->GetW(), wantH, movedTo, pf,
				body ? body->GetL() : -1, body ? body->GetT() : -1,
				body ? body->GetW() : -1, body ? body->GetH() : -1,
				natW, natH);
		}
	}

	// VWKID (v2.25.20, permanent instrument): MWKID's twin for the 3D VIEW
	// layer. The budget sub-dialogs are VIEW-parented, so MWKID never saw
	// them and three fixes shipped against inferred identities. This logs
	// every DIRECT view child that BECOMES VISIBLE (change-only on the
	// visible-id set): id, class vtable, rect - plus one level of children
	// for a newly visible window. The Taxes/department OPEN instance will
	// identify itself the next time the user opens one.
	{
		static uint32_t vwkidSig = 0;
		ChildSnapshot vk = {};
		pView->EnumChildren(GZIID_cIGZWin, ChildSnapshot::Callback, &vk);
		uint32_t sig = 0;
		for (int i = 0; i < vk.count; i++)
		{
			cIGZWin* w = vk.wins[i];
			if (!w || !w->IsVisible()) { continue; }
			sig = sig * 31u + w->GetID() + static_cast<uint32_t>(w->GetW()) * 7u;
		}
		if (sig != vwkidSig)
		{
			vwkidSig = sig;
			for (int i = 0; i < vk.count; i++)
			{
				cIGZWin* w = vk.wins[i];
				if (!w || !w->IsVisible()) { continue; }
				Logger::Get().WriteLine(LogLevel::Debug,
					"UiSpike: VWKID %2d id=0x%08X vt=%p (%d,%d %dx%d)",
					i, w->GetID(), *reinterpret_cast<void**>(w),
					w->GetL(), w->GetT(), w->GetW(), w->GetH());
			}
		}
	}

	// RUNTIME-SUPPLIED GZWinBMP IMAGES in TRANSIENT dialogs (task #47,
	// v2.25.0): the Select A My Sim picker (root 0x6A243D9E, 22 placeholder
	// cells receiving runtime-generated Sim faces) and the two U-Drive-It
	// pickers (shared root 0xCBF32603, cells receiving group-4C06F888 thumbs
	// - 2x since task #55, so those clamp to m=1.0 = pure insurance). These
	// dialogs are static-doubled by DialogStatic and exist only while open;
	// their parentage is main-window level, and searching from pMainWindow
	// covers the 3D view too if any turns out view-parented. The shared-copy
	// hook design means reopening the dialog re-hooks fresh windows with no
	// slot leak. See the BMPX namespace note above ScalePanelsUnder.
	{
		static const uint32_t kBmpxDialogRoots[] = { 0x6A243D9E, 0xCBF32603 };
		HookRuntimeBmpsUnder(pMainWindow, kBmpxDialogRoots,
			static_cast<int>(std::size(kBmpxDialogRoots)),
			settings.spikeScaleFactor, "dialog");
	}

	// Delayed RCI readout: the city-init one runs before the composite HUD
	// exists; this one runs after the HUD has been up for ~30s.
	if (rciRecheckCountdown > 0 && --rciRecheckCountdown == 0)
	{
		const uint32_t rciColumns[] = { 0x09D27EB0, 0x29D27EC0, 0x49D27ED0 };
		for (uint32_t id : rciColumns)
		{
			cIGZWin* pCol = pView->GetChildWindowFromIDRecursive(id);
			if (pCol)
			{
				Logger::Get().WriteLine(
					LogLevel::Debug,
					"UiSpike: RCI column 0x%08X recheck (%d,%d %dx%d) vis=%d",
					id, pCol->GetL(), pCol->GetT(), pCol->GetW(), pCol->GetH(),
					pCol->IsVisible() ? 1 : 0);
			}
		}
	}
}

namespace
{
	// Absolute-position lookup: DFS from `root` (whose absolute origin is
	// baseX/baseY), accumulating child offsets. Read-only, safe calls only.
	bool FindAbsolute(cIGZWin* root, uint32_t id, int32_t baseX, int32_t baseY,
		int depth, cIGZWin** out, int32_t* absX, int32_t* absY)
	{
		if (depth > 4)
		{
			return false;
		}
		ChildSnapshot snap = {};
		root->EnumChildren(GZIID_cIGZWin, ChildSnapshot::Callback, &snap);
		for (int i = 0; i < snap.count; i++)
		{
			cIGZWin* c = snap.wins[i];
			const int32_t cx = baseX + c->GetL();
			const int32_t cy = baseY + c->GetT();
			if (c->GetID() == id)
			{
				*out = c;
				*absX = cx;
				*absY = cy;
				return true;
			}
			if (FindAbsolute(c, id, cx, cy, depth + 1, out, absX, absY))
			{
				return true;
			}
		}
		return false;
	}
}

void UiSpike::DialogDockTick(cIGZWin* pMainWindow, cIGZWin* pRegion,
	int32_t screenW, int32_t screenH)
{
	const float f = settings.spikeScaleFactor;

	for (int i = 0; i < kDialogDockCount; i++)
	{
		const DialogDock& d = kRegionDialogDocks[i];
		cIGZWin* pDlg = pMainWindow->GetChildWindowFromIDRecursive(d.dialogId);
		if (!pDlg || !pDlg->IsVisible())
		{
			dialogDocked[i] = false; // closed: re-scale + re-dock on reopen
			continue;
		}

		// Scale 2x, idempotent (same record machinery as panels). The game
		// recreates/resets dialogs at design size each open; the origin-
		// anchored records prevent compounding.
		const ScaleState state = Classify(pDlg);
		if (state == ScaleState::Fresh)
		{
			// Same recycled-address hazard as panel roots (REGION-SWITCH.md:
			// dialog descendant counts rot 8/7/6 across reopens without this).
			PurgeSubtreeRecords(pDlg, 0);
		}
		bool newlyScaled = false;
		if (state == ScaleState::Fresh || state == ScaleState::ResetToOriginal)
		{
			const int32_t l = pDlg->GetL();
			const int32_t t = pDlg->GetT();
			const int32_t w = pDlg->GetW();
			const int32_t h = pDlg->GetH();
			const int32_t newW = ScaleRound(l + w, f) - ScaleRound(l, f);
			const int32_t newH = ScaleRound(t + h, f) - ScaleRound(t, f);
			if (newW > screenW || newH > screenH)
			{
				ScaleRecord dead = { pDlg->GetID(), w, h, w, h, 0, true };
				scaleMap[pDlg] = dead;
				continue;
			}
			passScreenW = screenW;
			passScreenH = screenH;
			pDlg->SetW(newW);
			pDlg->SetH(newH);

			ScaleRecord rec = { pDlg->GetID(), w, h, newW, newH, 0, false };
			rec.origL = l;
			rec.origT = t;
			rec.hasOrigPos = true;
			StoreScaleRecord(pDlg, rec);

			int cnt = 0;
			ChildSnapshot snap = {};
			pDlg->EnumChildren(GZIID_cIGZWin, ChildSnapshot::Callback, &snap);
			int verifiedAtCnt = cnt;   // #117: see ScaleSubtree's child loop
			for (int j = 0; j < snap.count; j++)
			{
				if (j > 0 && cnt != verifiedAtCnt)
				{
					ChildSnapshot verify = {};
					pDlg->EnumChildren(GZIID_cIGZWin, ChildSnapshot::Callback, &verify);
					// v2.69.3: mid-loop signal reset REMOVED (unsound - see ScaleSubtree).
					bool alive = false;
					for (int k = 0; k < verify.count; k++)
					{
						if (verify.wins[k] == snap.wins[j]) { alive = true; break; }
					}
					if (!alive)
					{
						continue;
					}
				}
				ScaleSubtree(snap.wins[j], f, 1, &cnt);
			}
			newlyScaled = true;
			Logger::Get().WriteLine(
				LogLevel::Debug,
				"UiSpike: dialog 0x%08X scaled (%d,%d %dx%d) -> %dx%d, %d descendants.",
				d.dialogId, l, t, w, h, newW, newH, cnt);
		}

		if (newlyScaled || !dialogDocked[i])
		{
			// Dock under the spawn button: centered on it, just below, on
			// screen. Button absolute position comes from the LIVE flyout
			// geometry (already doubled; valid even while the flyout is
			// hidden - region flyouts are pre-scaled).
			cIGZWin* pFly = pRegion->GetChildWindowFromID(d.flyoutId);
			cIGZWin* pBtn = nullptr;
			int32_t bx = 0;
			int32_t by = 0;
			if (pFly && FindAbsolute(pFly, d.buttonId,
				pFly->GetL(), pFly->GetT(), 0, &pBtn, &bx, &by))
			{
				int32_t tx = bx + pBtn->GetW() / 2 - pDlg->GetW() / 2;
				int32_t ty = by + pBtn->GetH() + 8;
				if (tx + pDlg->GetW() > screenW) tx = screenW - pDlg->GetW();
				if (tx < 0) tx = 0;
				if (ty + pDlg->GetH() > screenH) ty = screenH - pDlg->GetH();
				if (ty < 0) ty = 0;
				pDlg->GZWinMoveTo(tx - pDlg->GetL(), ty - pDlg->GetT());
				pDlg->InvalidateSelfAndParents();
				dialogDocked[i] = true;
				Logger::Get().WriteLine(
					LogLevel::Debug,
					"UiSpike: dialog 0x%08X docked at (%d,%d) under button 0x%08X.",
					d.dialogId, tx, ty, d.buttonId);
			}
		}
	}
}

namespace
{
	// #131 PROBE (v2.78.1). The REGIONCAM byte patch TOOK - its log line
	// prints `0.2500 -> 0.7500` - and the region did not move on screen, so
	// the open question is no longer "is the value right" but "is this the
	// camera that draws the slab, and does our value survive to draw time".
	// Reasoning further from the disassembly would be guessing; this reads
	// the live object instead.
	//
	// WE DO NOT TRUST A HARD-CODED FIELD OFFSET. The disassembly says the
	// camera lands at `esi+0x164` where esi is cSC4WinRegionScreen's `this`,
	// but our cIGZWin* may be a SUB-OBJECT pointer, so +0x164 from OUR
	// pointer need not be the same field. Instead we scan a bounded window
	// of the object for a pointer whose [+0x12C]/[+0x130] read as the LIVE
	// SCREEN SIZE - that pair is the camera's viewport (sub_7CB9B0 stores
	// GetW()/GetH() there) and it doubles as the POSITIVE CONTROL: if
	// nothing in range carries the screen size, this object does not own the
	// camera and the whole lever is misattributed. A zero here is then a
	// real measurement, not a structural null (law: state the positive
	// control before believing a null).
	const int kCamViewportW = 0x12C;
	const int kCamViewportH = 0x130;
	const int kCamScale     = 0x0F0;
	const int kCamWuPerPx   = 0x134;
	const int kCamZoomIdx   = 0x108;
	// v2.78.2, one hop further. MEASURED at 21:45:36: the camera holds
	// scale=0.7500 and wu/px=3.4842 - exactly our value and exactly the
	// derived reprojection - while the screen still draws the stock ~98 px
	// per region cell. So the camera OBJECT is right and the RENDER does not
	// follow it. The next link is the device: sub_7CBE40 computes
	// halfW = 0.5*viewportW*wuPerPx and pushes it through sub_7FF2E0 into
	// device[+0x18C..+0x198], but ONLY if [cam+0x0C] is non-null - and
	// SetScale stores [cam+0xF0] at 0x007CD72C BEFORE that null check at
	// 0x007CD735. A camera with no device attached would therefore report
	// exactly what we see: our value stored, nothing on screen.
	const int kCamDevice    = 0x00C;
	const int kDevDirtyCnt  = 0x17C;
	const int kDevNear      = 0x184;
	const int kDevFar       = 0x188;
	const int kDevLeft      = 0x18C;
	const int kDevRight     = 0x190;
	const int kDevTop       = 0x194;
	const int kDevBottom    = 0x198;

	struct CamRead
	{
		int32_t vw;
		int32_t vh;
		int32_t zoomIdx;
		float scale;
		float wuPerPx;
		bool ok;
	};

	// Per-candidate SEH: one bad pointer must not abort the whole scan.
	CamRead TryReadCam(const void* p)
	{
		CamRead r;
		r.vw = 0; r.vh = 0; r.zoomIdx = 0; r.scale = 0.0f; r.wuPerPx = 0.0f; r.ok = false;
		__try
		{
			const uint8_t* b = static_cast<const uint8_t*>(p);
			r.vw      = *reinterpret_cast<const int32_t*>(b + kCamViewportW);
			r.vh      = *reinterpret_cast<const int32_t*>(b + kCamViewportH);
			r.zoomIdx = *reinterpret_cast<const int32_t*>(b + kCamZoomIdx);
			r.scale   = *reinterpret_cast<const float*>(b + kCamScale);
			r.wuPerPx = *reinterpret_cast<const float*>(b + kCamWuPerPx);
			r.ok = true;
		}
		__except (EXCEPTION_EXECUTE_HANDLER)
		{
			r.ok = false;
		}
		return r;
	}

	struct DevRead
	{
		float left, right, top, bottom, nearZ, farZ;
		int32_t dirtyCnt;
		bool ok;
	};

	DevRead TryReadDev(const void* p)
	{
		DevRead d;
		d.left = d.right = d.top = d.bottom = d.nearZ = d.farZ = 0.0f;
		d.dirtyCnt = 0; d.ok = false;
		__try
		{
			const uint8_t* b = static_cast<const uint8_t*>(p);
			d.left     = *reinterpret_cast<const float*>(b + kDevLeft);
			d.right    = *reinterpret_cast<const float*>(b + kDevRight);
			d.top      = *reinterpret_cast<const float*>(b + kDevTop);
			d.bottom   = *reinterpret_cast<const float*>(b + kDevBottom);
			d.nearZ    = *reinterpret_cast<const float*>(b + kDevNear);
			d.farZ     = *reinterpret_cast<const float*>(b + kDevFar);
			d.dirtyCnt = *reinterpret_cast<const int32_t*>(b + kDevDirtyCnt);
			d.ok = true;
		}
		__except (EXCEPTION_EXECUTE_HANDLER)
		{
			d.ok = false;
		}
		return d;
	}

	// (#132's TryClearBuiltLatch lived here until v2.83.0. It belonged to the
	// in-place resize that crashed twice: clearing byte[item+0x34] regenerates
	// the +0x38 run list but NOT the click mask at +0x44, so it could never
	// make a resize safe. The rebuild path clears the latch itself, via
	// sub_7B5430 and sub_7B29E0.)

	bool TryReadSlot(const void* obj, int off, void** out)
	{
		__try
		{
			*out = *reinterpret_cast<void* const*>(static_cast<const uint8_t*>(obj) + off);
			return true;
		}
		__except (EXCEPTION_EXECUTE_HANDLER)
		{
			return false;
		}
	}

	// v2.78.3 CHANGE-WATCH. MEASURED 21:48:26 - camera scale 0.7500, device
	// frustum halfW 6689.6: OUR values, all the way to the device, pushed
	// (dirtyCnt=16). The screen nonetheless kept drawing the stock ~98 px per
	// region cell, whose frustum would be halfW 20068.8 (and 8192/40137 = 20%
	// of screen width, which is exactly what the screenshot shows).
	//
	// The one-shot probe fires when the region screen COMES UP, 3.6s after
	// boot. The user's screenshot is later. So the gap left in my own
	// instrument is: does something reconfigure the scene when the region is
	// SHOWN rather than CONSTRUCTED? A periodic re-read that logs ONLY ON
	// CHANGE answers that without spamming, and an explicit "steady" line
	// after N unchanged samples keeps a null affirmative rather than silent
	// (law 54: absence of a line must never be the evidence).
	void* gWatchCam = nullptr;
	float gWatchScale = -1.0f;
	float gWatchHalfW = -1.0f;
	int gWatchChanges = 0;
	int gWatchSamples = 0;
	bool gWatchSteadySaid = false;
	unsigned int gWatchLastMs = 0;
	const int kWatchMaxChanges = 24;
	const int kWatchSteadyAfter = 20;
	const unsigned int kWatchPeriodMs = 250;

	void WatchRegionCamera(unsigned int nowTickMs)
	{
		if (!gWatchCam) { return; }
		if (gWatchLastMs != 0 && (nowTickMs - gWatchLastMs) < kWatchPeriodMs) { return; }
		gWatchLastMs = nowTickMs;

		const CamRead c = TryReadCam(gWatchCam);
		if (!c.ok) { return; }

		float halfW = -1.0f;
		void* dev = nullptr;
		if (TryReadSlot(gWatchCam, kCamDevice, &dev) && dev)
		{
			const DevRead d = TryReadDev(dev);
			if (d.ok) { halfW = (d.right - d.left) * 0.5f; }
		}

		gWatchSamples++;
		const bool changed =
			(c.scale != gWatchScale) ||
			(halfW < 0.0f) != (gWatchHalfW < 0.0f) ||
			(halfW >= 0.0f && gWatchHalfW >= 0.0f && fabs(halfW - gWatchHalfW) > 1.0);

		if (changed && gWatchChanges < kWatchMaxChanges)
		{
			gWatchChanges++;
			Logger::Get().WriteLine(
				LogLevel::Info,
				"UiSpike: REGIONWATCH change #%d at sample %d - scale %.4f -> %.4f,"
				" device halfW %.1f -> %.1f (ours 6689.6, stock 20068.8).",
				gWatchChanges, gWatchSamples, gWatchScale, c.scale, gWatchHalfW, halfW);
			gWatchScale = c.scale;
			gWatchHalfW = halfW;
			gWatchSteadySaid = false;
		}
		else if (!changed && !gWatchSteadySaid && gWatchSamples >= kWatchSteadyAfter)
		{
			gWatchSteadySaid = true;
			Logger::Get().WriteLine(
				LogLevel::Info,
				"UiSpike: REGIONWATCH STEADY - %d samples over ~%dms, scale held %.4f"
				" and device halfW held %.1f. Nothing resets them while the region is"
				" on screen, so the visible slab is NOT drawn through this frustum.",
				gWatchSamples, gWatchSamples * kWatchPeriodMs, c.scale, halfW);
		}
	}

	// ============================================================
	// #131 v2.78.5 — THE TILE PROBE. Read it, do not decode it.
	// ============================================================
	// The static trace answered POSITION (the .data isometric basis) but
	// stalled on EXTENT: sub_7B3110 takes the tile's drawn size from
	// [item+0x1C] vt+0x30, and [item+0x1C] is built upstream of a copy-ctor.
	// Chasing that in a disassembler is slow because this exe has no symbols.
	// The game already holds every number we need in memory, so read it:
	// ONE launch replaces the whole static hunt (METHOD order: live
	// instruments come BEFORE the disassembler; I had it backwards).
	//
	// Item list, measured: [regionScreen+0xE0] is the item manager;
	// sub_7B3A80 walks [mgr+0x100]..[mgr+0x104] as a pointer array
	// (count = (end-start)/4). Each item has float screen pos at +0x10/+0x14
	// and the sprite at +0x1C.
	//
	// THE QUESTION THIS ANSWERS: what is the tile sprite's bounds rect, and
	// does its size match the 128 px cell? If bounds are ~128 wide the sprite
	// is cell-sized art and the fix is to scale bounds + stretch the blit. If
	// they are something else, that number tells us what the blit really uses.
	const int kMgrOff = 0xE0;
	const int kArrStart = 0x100;
	const int kArrEnd = 0x104;
	const int kItemPosX = 0x10;
	const int kItemPosY = 0x14;
	const int kItemSprite = 0x1C;
	const int kSpriteBoundsSlot = 0x30; // vt+0x30 -> const int32_t rect[4]
	const int kMaxItemsLogged = 10;

	typedef const int32_t*(__thiscall* GetBoundsFn)(const void*);

	bool TryReadDwords(const void* p, int off, int n, uint32_t* out)
	{
		__try
		{
			const uint8_t* b = static_cast<const uint8_t*>(p) + off;
			for (int i = 0; i < n; i++)
			{
				memcpy(&out[i], b + i * 4, 4);
			}
			return true;
		}
		__except (EXCEPTION_EXECUTE_HANDLER)
		{
			return false;
		}
	}

	// Calling a game vtable getter is what sub_7B3110 does every frame, so it
	// is a path the engine already exercises - but it is still a call into
	// foreign code, so it is wrapped and the result is plausibility-checked.
	bool TryGetSpriteBounds(const void* sprite, int32_t* out4)
	{
		__try
		{
			const void* const* vt = *reinterpret_cast<const void* const* const*>(sprite);
			GetBoundsFn fn =
				reinterpret_cast<GetBoundsFn>(const_cast<void*>(vt[kSpriteBoundsSlot / 4]));
			const int32_t* r = fn(sprite);
			if (!r) { return false; }
			for (int i = 0; i < 4; i++) { out4[i] = r[i]; }
			return true;
		}
		__except (EXCEPTION_EXECUTE_HANDLER)
		{
			return false;
		}
	}

	void ProbeRegionTiles(const void* regionObj)
	{
		void* mgr = nullptr;
		if (!TryReadSlot(regionObj, kMgrOff, &mgr) || !mgr)
		{
			Logger::Get().WriteLine(
				LogLevel::Info, "UiSpike: REGIONTILE no item manager at +0x%02X.", kMgrOff);
			return;
		}

		uint32_t se[2] = { 0, 0 };
		if (!TryReadDwords(mgr, kArrStart, 1, &se[0]) ||
			!TryReadDwords(mgr, kArrEnd, 1, &se[1]) || !se[0] || se[1] < se[0])
		{
			Logger::Get().WriteLine(
				LogLevel::Info, "UiSpike: [dbg] REGIONTILE item array unreadable (%08X..%08X).",
				se[0], se[1]);
			return;
		}
		const int count = static_cast<int>((se[1] - se[0]) / 4);
		Logger::Get().WriteLine(
			LogLevel::Info,
			"UiSpike: [dbg] REGIONTILE item array %08X..%08X = %d item(s). Basis says one"
			" region cell is 128 px wide at stock.",
			se[0], se[1], count);

		const int n = (count < kMaxItemsLogged) ? count : kMaxItemsLogged;
		for (int i = 0; i < n; i++)
		{
			uint32_t itemPtr = 0;
			if (!TryReadDwords(reinterpret_cast<const void*>(se[0]), i * 4, 1, &itemPtr) ||
				!itemPtr)
			{
				continue;
			}
			const void* item = reinterpret_cast<const void*>(itemPtr);

			uint32_t pos[2] = { 0, 0 };
			uint32_t spritePtr = 0;
			if (!TryReadDwords(item, kItemPosX, 2, pos)) { continue; }
			if (!TryReadDwords(item, kItemSprite, 1, &spritePtr)) { continue; }
			float px = 0.0f, py = 0.0f;
			memcpy(&px, &pos[0], 4);
			memcpy(&py, &pos[1], 4);

			if (!spritePtr)
			{
				Logger::Get().WriteLine(
					LogLevel::Info,
					"UiSpike: [dbg] REGIONTILE[%d] item=%08X pos=(%.2f,%.2f) sprite=NULL.",
					i, itemPtr, px, py);
				continue;
			}

			const void* sprite = reinterpret_cast<const void*>(spritePtr);
			uint32_t svt = 0;
			TryReadDwords(sprite, 0, 1, &svt);

			int32_t b[4] = { 0, 0, 0, 0 };
			const bool gotBounds = TryGetSpriteBounds(sprite, b);

			Logger::Get().WriteLine(
				LogLevel::Info,
				"UiSpike: [dbg] REGIONTILE[%d] item=%08X pos=(%.2f,%.2f) sprite=%08X vt=%08X"
				" bounds=%s(%d,%d,%d,%d) SIZE=%dx%d",
				i, itemPtr, px, py, spritePtr, svt, gotBounds ? "" : "FAILED",
				b[0], b[1], b[2], b[3], b[2] - b[0], b[3] - b[1]);

			// Dump the sprite head once: whichever fields carry the source
			// bitmap dimensions will be visible next to the bounds above, and
			// that is the field the blit reads.
			if (i == 0)
			{
				uint32_t d[16] = {};
				if (TryReadDwords(sprite, 0, 16, d))
				{
					Logger::Get().WriteLine(
						LogLevel::Info,
						"UiSpike: [dbg] REGIONTILE sprite head +00..+3C: %08X %08X %08X %08X"
						" %08X %08X %08X %08X %08X %08X %08X %08X %08X %08X %08X %08X",
						d[0], d[1], d[2], d[3], d[4], d[5], d[6], d[7],
						d[8], d[9], d[10], d[11], d[12], d[13], d[14], d[15]);
				}
			}
		}
	}

	// ============================================================
	// #131 v2.79.0 — REGIONTILE: make the composite buffer f-times bigger.
	// ============================================================
	// The tile's drawn SIZE is the composite buffer's pixel size, full stop:
	// sub_7AE510 Inits [item+0x2C] from the SOURCE thumbnail's rect
	// (0x007AE6D9..0x007AE706, byte-verified), sub_7B3300 copies into it with
	// `rep movsd` 1:1, sub_7B2A30 blits it to screen 1:1, and sub_7B3110
	// takes the tile's screen rect from its bounds. No stage resamples.
	//
	// So: resize the composite and refill it ourselves. Everything downstream
	// follows, because everything downstream reads the buffer.
	//
	// WHY NOT A DETOUR ON sub_7B3300: it takes its source in EAX with an
	// unverified stack cleanup, so hooking it needs naked asm built on a
	// guess. This runs in our own region tick in plain C++ and SELF-GATES ON
	// THE DEFECT (law 56) - it acts only when the composite is not already
	// the size we want, so a re-run by the game is simply re-fixed on the
	// next tick and our own work is never redone.
	//
	// ⛔ CORRECTED v2.83.1. This block used to state that [item+0x1C] and
	// [item+0x2C] "are both cIGZBuffer, vtable 0x00ADB418, verified on BOTH
	// before any write". THAT IS FALSE AND WAS NEVER TRUE. The region tile
	// buffers carry vtable **0x00AC1400** - measured on all nine items in
	// every capture ("sprite=... vt=00AC1400" in the REGIONTILE dump below,
	// and again in the v2.83.0 run). 0x00ADB418 is a DIFFERENT buffer class,
	// constructed at exactly one site (0x00990B7C) into a device member.
	// The claim survived because nothing in this file ever compared against
	// it; CodePatches::GrowTileBitmap has always used 0x00AC1400 and is what
	// actually ships. Left as a named correction rather than deleted, because
	// this comment was cited as evidence during the #132 design and a
	// contradicted invariant that is merely erased tends to come back.
	//   vt+0x04 AddRef      vt+0x08 Release     vt+0x0C Init(w,h,fmt,bpp)
	//   vt+0x10 Deinit      vt+0x24 GetWidth    vt+0x28 GetHeight
	//   vt+0x88 GetBits     vt+0x8C GetStride
	// Those getters are shared game-wide - we CALL them, never patch them.
	const uintptr_t kIGZBufferVt = 0x00AC1400;
	const int kItemComposite = 0x2C;
	const int kItemStride = 0x80;      // 0x007B1528 add [esi+4],0x80
	const int kBufInit = 0x0C / 4;
	const int kBufGetW = 0x24 / 4;
	const int kBufGetH = 0x28 / 4;
	const int kBufGetBits = 0x88 / 4;
	const int kBufGetStride = 0x8C / 4;
	const int32_t kMaxDim = 8192;

	// v2.80.0 — CORRECTED SIGNATURES, decompiled from the exe (not inferred).
	//   vt[3]  +0x0C  0x008269B0  bool Init(w,h,colorType,bpp)   ret 0x10  (FOUR args)
	//   vt[4]  +0x10  0x00825CE0  bool Shutdown()                (0 args)
	//   vt[8]  +0x20  0x008268B0  bool IsLocked()  -> word[+0x38]
	//   vt[9]  +0x24  Width   vt[10] +0x28  Height
	//   vt[34] +0x88  GetBits vt[35] +0x8C  GetStride
	//
	// ⛔ v2.79.x called Init with THREE args plus a pointer to a {9,0x20} pair.
	// The real function is __thiscall with FOUR dword args and cleans 0x10 -
	// so every call popped 4 bytes more than we pushed. Nine per tick, and it
	// never crashed only because Init bailed at its first instruction.
	//
	// THE LATCH: Init's first test is `mov al,[esi+8]; cmp al,0; jne ->ret 0`.
	// byte[buf+0x08] is a READY flag (slot +0x9C is literally `return
	// byte[this+8]`). Our live dump read +0x08 = 1, so Init refused every
	// time and wrote nothing - that IS the initFailed=9. Shutdown() at slot
	// +0x10 frees the bits AND clears the latch; FreeBits alone does NOT
	// clear it and leaves Init still refusing.
	typedef int32_t(__thiscall* BufGetIntFn)(void*);
	typedef void*(__thiscall* BufGetPtrFn)(void*);
	typedef char(__thiscall* BufInitFn)(void*, uint32_t, uint32_t, uint32_t, uint32_t);
	typedef char(__thiscall* BufVoidFn)(void*);
	const int kBufShutdown = 0x10 / 4;
	const int kBufIsLocked = 0x20 / 4;
	const int kBufFmtType = 0x0C;   // colorType (9 = ARGB8888)
	const int kBufFmtBpp = 0x10;    // 0x20
	const int kBufReadyLatch = 0x08;
	const int kBufHwCache = 0x48;
	const int kItemBuiltLatch = 0x34; // byte: "composite already filled"

	int gTileScaled = 0;
	int gTileSkipped = 0;
	bool gTileLoggedFirst = false;

	void ProbeRegionCamera(int32_t screenW, int32_t screenH, const void* regionObj)
	{
		// Is our patched immediate still live in memory? If another mod (or a
		// second copy of us) rewrote it, the byte we logged is not the byte
		// the game read. Cheap, and it separates "we never wrote" from "we
		// wrote and it was undone".
		float liveImm = 0.0f;
		{
			const uintptr_t base = reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
			const uint8_t* site = reinterpret_cast<const uint8_t*>(0x7AD0BC + (base - 0x400000));
			__try { liveImm = *reinterpret_cast<const float*>(site); }
			__except (EXCEPTION_EXECUTE_HANDLER) { liveImm = -1.0f; }
		}

		int hits = 0;
		for (int off = 0; off <= 0x400; off += 4)
		{
			void* p = nullptr;
			if (!TryReadSlot(regionObj, off, &p) || !p) { continue; }
			const uintptr_t pv = reinterpret_cast<uintptr_t>(p);
			if (pv < 0x10000 || (pv & 3) != 0) { continue; }

			const CamRead c = TryReadCam(p);
			if (!c.ok) { continue; }
			if (c.vw != screenW || c.vh != screenH) { continue; }

			hits++;
			Logger::Get().WriteLine(
				LogLevel::Info,
				"UiSpike: [dbg] REGIONCAM probe HIT at +0x%03X obj=%p scale=%.4f wu/px=%.4f"
				" viewport=%dx%d zoomIdx=%d (cell would be %.0f px).",
				off, p, c.scale, c.wuPerPx, c.vw, c.vh, c.zoomIdx,
				(c.wuPerPx > 0.0001f) ? (1024.0f / c.wuPerPx) : 0.0f);

			// Reject the known false positive before following any pointer out
			// of it: a real camera has a sane zoom index and a positive scale.
			// (+0x06C matched the viewport test at 21:45:36 with scale=0 and a
			// garbage zoomIdx - that offset is the draw CONTEXT, not a camera.)
			if (c.zoomIdx < 0 || c.zoomIdx > 4 || c.scale <= 0.0f || c.scale > 1000.0f)
			{
				Logger::Get().WriteLine(
					LogLevel::Info,
					"UiSpike:   ^ rejected as a camera (zoomIdx/scale implausible)"
					" - not following its device pointer.");
				continue;
			}

			// THE LINK UNDER TEST. If the device frustum still carries the
			// STOCK half-extents, the camera was reconfigured and never
			// re-pushed, and the fix is to force the push. If it carries OUR
			// half-extents, the device is right too and the region slab is not
			// drawn through this frustum at all - which sends us back to the
			// draw path with the camera lever eliminated.
			void* dev = nullptr;
			if (!TryReadSlot(p, kCamDevice, &dev) || !dev)
			{
				Logger::Get().WriteLine(
					LogLevel::Info,
					"UiSpike:   ^ NO DEVICE at [cam+0x0C]. SetScale stores the scale"
					" BEFORE its device null-check (0x007CD72C vs 0x007CD735), so the"
					" reprojection never reached a device. That is the defect.");
				continue;
			}

			// Arm the change-watch on the plausible camera.
			gWatchCam = p;
			gWatchScale = c.scale;
			gWatchHalfW = -1.0f;
			gWatchChanges = 0;
			gWatchSamples = 0;
			gWatchSteadySaid = false;
			gWatchLastMs = 0;

			DevRead d = TryReadDev(dev);
			if (!d.ok)
			{
				Logger::Get().WriteLine(
					LogLevel::Info, "UiSpike:   ^ device %p unreadable.", dev);
				continue;
			}
			// What the two hypotheses predict, so the numbers adjudicate
			// themselves in the log instead of needing a second pass.
			const float halfWNow  = 0.5f * static_cast<float>(c.vw) * c.wuPerPx;
			const float halfWStock = 0.5f * static_cast<float>(c.vw) * 10.4525f;
			Logger::Get().WriteLine(
				LogLevel::Info,
				"UiSpike:   ^ DEVICE %p frustum L=%.1f R=%.1f T=%.1f B=%.1f"
				" near=%.1f far=%.1f dirtyCnt=%d | halfW: live=%.1f ours=%.1f stock=%.1f",
				dev, d.left, d.right, d.top, d.bottom, d.nearZ, d.farZ, d.dirtyCnt,
				(d.right - d.left) * 0.5f, halfWNow, halfWStock);
			gWatchHalfW = (d.right - d.left) * 0.5f;
		}

		Logger::Get().WriteLine(
			LogLevel::Info,
			"UiSpike: REGIONCAM probe done - %d candidate(s) with viewport %dx%d;"
			" live patched immediate at 0x007AD0BC reads %.4f (expect 0.7500).",
			hits, screenW, screenH, liveImm);
		if (hits == 0)
		{
			Logger::Get().WriteLine(
				LogLevel::Info,
				"UiSpike: REGIONCAM probe found NO camera under the region screen."
				" The scan CAN see the screen size (that is its positive control),"
				" so this is a measured null: the region camera is not reachable"
				" from this object and 0x007AD0BB is the wrong lever.");
		}
	}
}

// #132 REGION ZOOM.
//
// The region screen has NO camera and NO view transform. A full decompile of
// all 197 functions in the module (tools\research\REGION-SCREEN.md) contains
// ZERO references to zoom, rotate, angle or yaw - verified against a positive
// control on the same grep (camera:11, frustum:2, basis:2). The screen
// composites bitmaps baked at a fixed isometric basis, in 2D.
//
// So "zoom" is #131's own two levers driven by input:
//   * the isometric basis (pixels per region cell) -> tile POSITIONS;
//   * the sub_7AE3D0 hook factor                   -> tile SIZE on the next
//     rebuild, and the click mask with it.
// Existing tile bitmaps are rescaled by the RATIO so the change is visible
// immediately; anything the game rebuilds afterwards lands at the new factor
// because the hook's factor moved too. Both halves, always - law 43.
//
// ⛔ ROTATION IS NOT OFFERED and must not be faked. The tiles are thumbnails
// baked at a fixed angle when each city was last SAVED; rotating the region
// would require re-rendering every city, which only the city view can do at
// save time. A button that cannot work is worse than no button.
void UiSpike::RegionZoomStep(int dir)
{
	if (dir == 0 || settings.spikeRegionZoomLevels <= 0) { return; }

	// ⚠ THE WHEEL ONLY RECORDS INTENT. Applying a zoom rebuilds 18 pixel
	// buffers (9 tiles x source + composite) with Shutdown/Init/resample,
	// synchronously. Doing that per notch FROZE THE GAME when the user
	// scrolled fast (2026-08-05) - every queued notch paid the full cost.
	// Now a burst of notches collapses into ONE resize on the next 16ms tick.
	const int lo = -settings.spikeRegionZoomLevels;
	const int hi = settings.spikeRegionZoomLevels;
	int want = regionZoomTarget + dir;
	if (want < lo) { want = lo; }
	if (want > hi) { want = hi; }
	if (want == regionZoomTarget)
	{
		// Already at a stop. Say so ONCE per stop so the log does not fill up
		// while the user keeps scrolling into the wall.
		if (!regionZoomAtLimitLogged)
		{
			regionZoomAtLimitLogged = true;
			Logger::Get().WriteLine(
				LogLevel::Info,
				"UiSpike: REGIONZOOM at the %s limit (level %d of +/-%d) - ignoring.",
				(dir > 0) ? "IN" : "OUT", regionZoomTarget,
				settings.spikeRegionZoomLevels);
		}
		return;
	}
	regionZoomAtLimitLogged = false;
	regionZoomTarget = want;
	regionZoomPending = true; // applied by ApplyPendingRegionZoom on the tick
	regionZoomLastStepMs = GetTickCount();
}

// Applies at most ONE zoom change, and only once the level has SETTLED. A
// rebuild is a real cost - per item it is 8-10 full-image passes, two of them
// carrying ~3 virtual calls per pixel and two more one unreserved vector insert
// per opaque pixel - so it must happen once per gesture, not once per notch.
// Applying per notch is what froze the game on a fast scroll (2026-08-05).
void UiSpike::ApplyPendingRegionZoom(cIGZWin* pRegion, unsigned int nowTickMs)
{
	if (!regionZoomPending || !pRegion) { return; }
	// Let the wheel finish. Each further notch pushes the deadline out, so a
	// spin of any length costs exactly one rebuild.
	if ((nowTickMs - regionZoomLastStepMs) < kRegionZoomSettleMs) { return; }
	regionZoomPending = false;

	const float base = (settings.spikeRegionMapScale > 0.0f)
		? settings.spikeRegionMapScale
		: settings.spikeScaleFactor;
	if (regionZoom <= 0.0f) { regionZoom = base; }

	// Level -> factor, always recomputed from the BASE so repeated steps can
	// never drift or compound.
	float want = base;
	for (int i = 0; i < regionZoomTarget; i++) { want *= settings.spikeRegionZoomStepRatio; }
	for (int i = 0; i > regionZoomTarget; i--) { want /= settings.spikeRegionZoomStepRatio; }

	const float before = regionZoom;
	if (want == before) { return; }

	// Stock is NO LONGER a floor (v2.85.0). The tile hook shrinks as well as
	// grows, so below 1.0 the basis and the tiles stay coupled and the map just
	// gets smaller - which is what you want on a big region. The old refusal
	// existed only because RegionBuildThunk early-outed at <= 1.001, leaving
	// tiles baked-size under a shrinking lattice.
	// The snapshot is the whole mechanism. Without it a rebuild would compound
	// (sub_7AE510 reads the CURRENT bitmaps) and would crash on the null mask
	// sub_7B13C0 leaves behind. If the hook never fired, say so and do nothing
	// - a null must be affirmative (law 54).
	const int snapped = CodePatches::RegionPristineCount();
	if (snapped <= 0)
	{
		Logger::Get().WriteLine(
			LogLevel::Info,
			"UiSpike: REGIONZOOM level %+d NOT applied - 0 pristine snapshots."
			" The sub_7AE510 hook did not fire for this region, so a rebuild"
			" would compound the tiles instead of rescaling them.",
			regionZoomTarget);
		return;
	}

	int skipped = 0;
	const unsigned int t0 = GetTickCount();
	const int rebuilt = CodePatches::RegionZoomRebuild(
		pRegion, want, settings.spikeRegionZoomMaxEdge, &skipped);
	const unsigned int elapsed = GetTickCount() - t0;

	if (rebuilt <= 0)
	{
		// Wording matters here. RegionZoomRebuild validates everything BEFORE
		// touching the basis and rolls it back if it committed and then
		// rebuilt nothing, so the map really is unchanged - but this line used
		// to claim that unconditionally, back when the basis was written first
		// and never restored. Say what was checked, not what we hope happened;
		// the CodePatches log line above this one names the actual reason.
		Logger::Get().WriteLine(
			LogLevel::Info,
			"UiSpike: REGIONZOOM level %+d NOT APPLIED (%.3f -> %.3f): 0 of %d"
			" snapshot(s) rebuilt, %d skipped. Basis unchanged - see the"
			" REGIONZOOM reason line above. Holding at level %+d.",
			regionZoomTarget, before, want, snapped, skipped,
			regionZoomLastApplied);
		// The factor never took, so the level must not stick either or the
		// next step would compute its ratio against a scale that is not live.
		regionZoomTarget = regionZoomLastApplied;
		return;
	}

	regionZoom = want;
	regionZoomLastApplied = regionZoomTarget;

	Logger::Get().WriteLine(
		LogLevel::Info,
		"UiSpike: REGIONZOOM level %+d (of +/-%d): %.3f -> %.3f - items=%d"
		" rebuilt, %d skipped, %u ms. One cell = %.0f px. Tile hook grew %d,"
		" declined %d.",
		regionZoomTarget, settings.spikeRegionZoomLevels, before, want,
		rebuilt, skipped, elapsed, 128.0f * want,
		CodePatches::RegionTileGrown(), CodePatches::RegionTileDeclined());
}

void UiSpike::RegionWatchTick(unsigned int nowTickMs)
{
	cISC4AppPtr pSC4App;
	if (!pSC4App)
	{
		return;
	}
	cIGZWin* pMainWindow = pSC4App->GetMainWindow();
	if (!pMainWindow)
	{
		return;
	}

	// Recursive lookup: tolerant of the region screen being a direct child
	// of the main window or one level down.
	cIGZWin* pRegion = pMainWindow->GetChildWindowFromIDRecursive(kGZWin_RegionScreen);
	const bool present = (pRegion != nullptr) && pRegion->IsVisible();

	// RGKID (v2.26.7, measurement): change-only dump of the region screen's
	// direct children + one level below - the CITY-SELECT BUBBLE (with the
	// Mayor Rating bar the user reports drawing twice) lives there and has
	// never been measured. Same shape as MWKID; costs one enum per sweep.
	if (present && settings.spikeScaleRegion)
	{
		static uint32_t rgkidSig = 0;
		ChildSnapshot rk = {};
		pRegion->EnumChildren(GZIID_cIGZWin, ChildSnapshot::Callback, &rk);
		uint32_t sig = static_cast<uint32_t>(rk.count);
		for (int i = 0; i < rk.count; i++)
		{
			cIGZWin* w = rk.wins[i];
			if (!w) { continue; }
			sig = sig * 31u + w->GetID() + (w->IsVisible() ? 1u : 0u)
				+ static_cast<uint32_t>(w->GetW()) * 7u
				+ static_cast<uint32_t>(w->GetChildCount()) * 1009u;  // v2.26.9
		}
		if (sig != rgkidSig)
		{
			rgkidSig = sig;
			for (int i = 0; i < rk.count; i++)
			{
				cIGZWin* w = rk.wins[i];
				if (!w || !w->IsVisible()) { continue; }
				Logger::Get().WriteLine(LogLevel::Debug,
					"UiSpike: RGKID %2d id=0x%08X vt=%p (%d,%d %dx%d)",
					i, w->GetID(), *reinterpret_cast<void**>(w),
					w->GetL(), w->GetT(), w->GetW(), w->GetH());
				ChildSnapshot sub = {};
				w->EnumChildren(GZIID_cIGZWin, ChildSnapshot::Callback, &sub);
				for (int j = 0; j < sub.count && j < 24; j++)
				{
					cIGZWin* c = sub.wins[j];
					if (!c) { continue; }
					Logger::Get().WriteLine(LogLevel::Debug,
						"UiSpike: RGKID %2d.%-2d id=0x%08X vt=%p (%d,%d %dx%d) vis=%d",
						i, j, c->GetID(), *reinterpret_cast<void**>(c),
						c->GetL(), c->GetT(), c->GetW(), c->GetH(),
						c->IsVisible() ? 1 : 0);
					// v2.26.8: the CITY-SELECT BUBBLE (Mayor Rating bar drawn
					// twice) is not a direct region child - it hangs under one
					// of the full-screen view layers, so recurse one level for
					// any child that is itself a container.
					if (!c->IsVisible()) { continue; }
					ChildSnapshot g2 = {};
					c->EnumChildren(GZIID_cIGZWin, ChildSnapshot::Callback, &g2);
					for (int q = 0; q < g2.count && q < 16; q++)
					{
						cIGZWin* e = g2.wins[q];
						if (!e) { continue; }
						// v2.27.0: print INVISIBLE ones too - the Mayor Rating bar
						// was among the skipped indices last pass - and recurse
						// one more level, since the bar is a grandchild of the
						// city-select bubble 0x0A551C50 (516x500), not a child.
						Logger::Get().WriteLine(LogLevel::Debug,
							"UiSpike: RGKID %2d.%d.%-2d id=0x%08X vt=%p (%d,%d %dx%d) vis=%d",
							i, j, q, e->GetID(), *reinterpret_cast<void**>(e),
							e->GetL(), e->GetT(), e->GetW(), e->GetH(),
							e->IsVisible() ? 1 : 0);
						ChildSnapshot g3 = {};
						e->EnumChildren(GZIID_cIGZWin, ChildSnapshot::Callback, &g3);
						for (int z = 0; z < g3.count && z < 16; z++)
						{
							cIGZWin* f = g3.wins[z];
							if (!f) { continue; }
							Logger::Get().WriteLine(LogLevel::Debug,
								"UiSpike: RGKID %2d.%d.%d.%-2d id=0x%08X vt=%p (%d,%d %dx%d) vis=%d",
								i, j, q, z, f->GetID(), *reinterpret_cast<void**>(f),
								f->GetL(), f->GetT(), f->GetW(), f->GetH(),
								f->IsVisible() ? 1 : 0);
						}
					}
				}
			}
		}
	}

	(void)nowTickMs;
	if (!present)
	{
		// Region screen gone (city entered) - reset so the next return to
		// the region re-stabilizes before scaling.
		//
		// CORRECTED 2026-08-04: this used to claim "scaleMap keeps its
		// records, so persistent region UI is NOT re-scaled on return."
		// MEASURED FALSE - nothing in the region host subtree persists. All
		// nine panels re-scale from DESIGN geometry at boot-equal descendant
		// counts (10/2/9/3/5/18/10/3/3) on every city->region return, and the
		// return is safe because of PURGE-ON-FRESH-ROOT, not because records
		// survive. Your own comment is an instrument, and this one lied.
		regionChildCountSeen = -1;
		regionStableTicks = 0;
		regionActive = false;
		// Drop the camera watch: the object is rebuilt with the screen, so a
		// stale pointer here would be read across a teardown.
		gWatchCam = nullptr;
		// #132: release our refs on the pristine bitmaps - but ONLY when the
		// window is really gone, not merely hidden. Dropping them on every
		// hide would leave zoom dead on the second visit if the screen is
		// hidden rather than torn down, and this branch cannot tell the
		// difference except by the pointer.
		//
		// Keeping a stash across a region CHANGE is safe, which is why the
		// weaker signal is good enough: every live item got its art from
		// sub_7AE510, so every live item has a CURRENT capture. A stale entry
		// can only ever be one no live item matches.
		if (!pRegion && CodePatches::RegionPristineCount() > 0)
		{
			CodePatches::ClearRegionPristine();
		}
		// Deliberately NOT resetting the zoom level. The basis lives in .data
		// and is still patched, so the next region build computes its
		// positions from it and the hook sizes its tiles to match - the map
		// comes back exactly as the user left it. Zeroing the level here would
		// desynchronise the bookkeeping from the pixels.
		regionZoomPending = false;
		return;
	}

	if (!regionActive)
	{
		// Stability check instead of a wall-clock settle: activate on the
		// second consecutive tick with an unchanged child count (~500ms).
		// The old 3s settle left the 1x layout on screen long enough to
		// visibly JUMP to 2x; this usually finishes behind the load screen.
		// Never walk a tree that may still be initializing (the
		// PostCityInit hang lesson) - a mid-build tree churns its child
		// count and keeps failing this check.
		const int32_t kids = pRegion->GetChildCount();
		if (kids != regionChildCountSeen)
		{
			regionChildCountSeen = kids;
			regionStableTicks = 0;
			return;
		}
		if (++regionStableTicks < 1)
		{
			return;
		}
		regionActive = true;
		Logger::Get().WriteLine(
			LogLevel::Info,
			"UiSpike: region screen up (%dx%d) - scaling.",
			pRegion->GetW(), pRegion->GetH());

		// #131: one-shot, read-only. Fires once per region arrival so a
		// city->region return re-measures; nothing here writes.
		ProbeRegionCamera(pRegion->GetW(), pRegion->GetH(), pRegion);
		// v2.79.1: and dump the tile items + their sprite bounds. Written in
		// v2.78.5 and never wired up - which is why we are guessing about the
		// item list instead of reading it.
		ProbeRegionTiles(pRegion);

		// Recon: dump the region tree once on activation (autonomous test
		// loop reads geometry from the log without a human at the screen).
		if (settings.spikeDumpTree)
		{
			visibilityProbeOk = true;
			Logger::Get().WriteLine(LogLevel::Debug, "UiSpike: ---- region tree dump begin ----");
			int total = 0;
			DumpTree(pRegion, 0, &total);
			Logger::Get().WriteLine(LogLevel::Debug, "UiSpike: ---- region dump end, %d windows ----", total);
		}
	}

	// #131 v2.78.3: sample the region camera + its device every 250ms while
	// the region is up, change-only. Read-only; writes nothing.
	WatchRegionCamera(nowTickMs);

	// #132: at most ONE zoom change per settled gesture, however many wheel
	// notches arrived. This is the rate limit that stops a fast scroll hanging
	// the game on stacked synchronous rebuilds.
	ApplyPendingRegionZoom(pRegion, nowTickMs);

	// #131 v2.79.0: THE COUPLED HALF of the isometric-basis patch. The basis
	// (CodePatches::ApplyRegionIsoScale) moves the tile POSITIONS; this makes
	// the tiles themselves that big. Ship both or neither - basis alone
	// spreads them apart with gaps, which is worse than the original defect.
	// Self-gates on the composite's size, so it is idempotent and re-fixes
	// any tile the game rebuilds.
	// ⛔ #131: there is deliberately NO per-tick tile pass here. v2.80.0 had
	// one; it resized buffers the game OWNS and the game restored them every
	// frame (counter 9/18/27/36, unbounded) while the click mask went stale
	// and city tiles became unclickable. The growth now happens inside the
	// game's own rebuild via the sub_7AE3D0 hook
	// (CodePatches::ApplyRegionTileScale), so the composite and the click mask
	// inherit the new size for free. Law 57: a fix that must re-apply every
	// tick is a fight, not a fix. Full autopsy in _tests\REGRESSION.md #131.

	// Same idempotent whitelist pass as the city view, every tick while the
	// region screen stays up.
	ScalePanelsUnder(pRegion, "region");

	// Transient dialogs: RUNTIME docking is off by default. These dialogs
	// carry game-generated scrolling lists (the Audio playlist), slider and
	// radio-grid controls, and LIVE content the game re-lays-out every frame -
	// tree-scaling them malforms the internal layout and fights the game's
	// per-frame reset (jumpy). The correct path is STATIC .UI script scaling
	// (double area=/imagerect in the dialog scripts, ship in the art dat, let
	// the game create + place them). Docking code kept for that positioning
	// work; enable with [UiSpike] DockDialogs=1 only for experiments.
	if (settings.spikeDockDialogs)
	{
		DialogDockTick(pMainWindow, pRegion, pRegion->GetW(), pRegion->GetH());
	}
}

void UiSpike::ScaleMenuFlyouts(cIGZWin* pMenu, int32_t screenW, int32_t screenH, float f)
{
	gTierF = f;   // v2.24.0 tier math: keep the hook-visible mirror current
	// STRATEGY: the container 0xAA32BCE6 and everything present at baseline
	// capture is the persistent fold-out MACHINERY - never mutated. Only
	// children appearing AFTER the baseline (transient flyout popups) are
	// touched, and only with a SIZE-ONLY subtree scale (no root move): the
	// base button strip stays 1x, so a flyout must stay glued to the
	// unscaled button that spawned it and grow right/down from there.
	ChildSnapshot snap = {};
	pMenu->EnumChildren(GZIID_cIGZWin, ChildSnapshot::Callback, &snap);

	if (!menuBaselineCaptured)
	{
		// Captured on the first pass after city init (menus closed, so
		// everything VISIBLE now is machinery; hidden children are likely
		// pre-created flyouts - do NOT baseline them so they get scaled
		// before their first show (no 1x flash on open).
		for (int i = 0; i < snap.count; i++)
		{
			if (snap.wins[i]->IsVisible())
			{
				menuBaseline[snap.wins[i]] = snap.wins[i]->GetID();
			}
		}
		menuBaselineCaptured = true;
		Logger::Get().WriteLine(
			LogLevel::Info,
			"UiSpike: menu baseline captured - %d children protected.", snap.count);
		return;
	}

	// #117: see the note at ScaleSubtree's child loop. Menus are the loop the
	// crash was FIRST seen on, so the gate is the conservative form here too -
	// any scaled window in the previous iteration re-verifies.
	bool mutatedSinceVerify = false;
	for (int i = 0; i < snap.count; i++)
	{
		cIGZWin* child = snap.wins[i];

		if (i > 0 && mutatedSinceVerify)
		{
			// CRASH KILLER: re-verify liveness before touching (menus churn
			// hard during rapid clicking - the exact crash scenario).
			ChildSnapshot verify = {};
			pMenu->EnumChildren(GZIID_cIGZWin, ChildSnapshot::Callback, &verify);
			// v2.69.3: mid-loop signal reset REMOVED (unsound - see ScaleSubtree).
			bool alive = false;
			for (int j = 0; j < verify.count; j++)
			{
				if (verify.wins[j] == child) { alive = true; break; }
			}
			if (!alive)
			{
				continue;
			}
		}

		std::map<void*, uint32_t>::iterator it = menuBaseline.find(child);
		if (it != menuBaseline.end())
		{
			if (child->GetID() == it->second)
			{
				continue; // persistent machinery - hands off
			}
			menuBaseline.erase(it); // address reuse: not machinery anymore
		}

		// Scale hidden flyouts too: pre-created flyouts that haven't been
		// shown yet get scaled NOW so they appear at 2x on first open.
		const int32_t w = child->GetW();
		const int32_t h = child->GetH();
		if (w <= 0 || h <= 0)
		{
			continue;
		}
		if (w >= screenW * 9 / 10 && h >= screenH * 9 / 10)
		{
			continue; // full-screen layer, not a flyout
		}

		// Size-only subtree scale (depth 0 = resize without moving the
		// root), same idempotent Classify() lifecycle as everything else.
		// centerLeaves: flyout item icons are exemplar-bound 1x art - they
		// center in their doubled slots instead of stretching.
		passScreenW = screenW;
		passScreenH = screenH;
		int n = 0;
		ScaleSubtree(child, f, 0, &n, true);
		if (n > 0) { mutatedSinceVerify = true; }
		if (n > 0)
		{
			Logger::Get().WriteLine(
				LogLevel::Debug,
				"UiSpike: menu flyout 0x%08X - %d windows scaled (size-only root).",
				child->GetID(), n);
		}
	}
}

void UiSpike::DumpTree(cIGZWin* win, int depth, int* totalCount)
{
	if (!win || depth > kMaxDepth || *totalCount >= kMaxWindows)
	{
		return;
	}

	(*totalCount)++;

	// Safe single-name getters only (see header notes).
	const uint32_t id = win->GetID();
	const int32_t l = win->GetL();
	const int32_t t = win->GetT();
	const int32_t w = win->GetW();
	const int32_t h = win->GetH();
	const int32_t children = win->GetChildCount();

	// Visibility annotation. IsVisible() and GetFlag() are single-name
	// virtuals (trustworthy slots per the overload-pair rule), but still
	// unverified on this binary - probe once with the log-before-call guard.
	int visible = -1;
	int enabled = -1;
	if (visibilityProbeOk)
	{
		if (!visibilityProbeLogged)
		{
			visibilityProbeLogged = true;
			Logger::Get().WriteLine(LogLevel::Debug, "UiSpike: first IsVisible()/GetFlag() call...");
		}
		visible = win->IsVisible() ? 1 : 0;
		enabled = win->GetFlag(cIGZWin::WinFlag_Enabled) ? 1 : 0;
	}

	Logger::Get().WriteLine(
		LogLevel::Debug,
		"UI %*sid=0x%08X pos(%d,%d) size(%dx%d) children=%d vis=%d en=%d",
		depth * 2, "", id, l, t, w, h, children, visible, enabled);

	if (children > 0)
	{
		UiSpikeEnumCtx ctx = { this, depth + 1, totalCount };
		win->EnumChildren(GZIID_cIGZWin, UiSpikeEnumCtx::Callback, &ctx);
	}
}

// #176 RELATCH — carry a SetImage-latched source rect across OUR resize.
//
// MECHANISM (byte-verified 2026-08-16, wf-176 + controller disassembly):
// cIGZWinBMP::SetImage (0x9BC57E) ends in 0x9BC447, which rewrites the live
// imagerect member [win+0xE8..0xF4] to (0,0,min(areaW,imgW),min(areaH,imgH))
// FROM THE WINDOW'S AREA AT THAT MOMENT. GZWinBMP::SetArea (0x99C837) never
// touches that member, and the draw (0x9BC325) is dst-follows-src - so a
// window whose bitmap was code-bound BEFORE our sweep keeps drawing its
// pre-sweep size until the game happens to call SetImage again. The city-HUD
// Mayor Rating groove 0x8A517556 is the measured victim: the rating handler
// (sub_7E8510) binds a runtime-composed buffer ~0.8s BEFORE the city sweep,
// and only re-binds on a sim rating tick (~once per sim month). Every
// tick-less session shows 102x11 content in a 153x17 window at 1.5x - the
// green fill "stops 6 rows short of the bottom". 2x/3x had the identical
// latch (102x11 in 204x22 = the historical "half bar") healed only by luck
// of tick timing. Captures: 08-16-174827 (stale, 1 firing), 08-13-155410 /
// 08-16-172018 (healed, post-sweep firing).
//
// THE GUARD IS THE LATCH'S OWN SIGNATURE, NOT AN ID LIST (law 94): fire only
// when the crop reads exactly (0,0,oldW,oldH) - i.e. it was FOLLOWING the
// window per SetImage's formula - and continue that behaviour across the
// resize with the same min() clamp the game applies. A deliberate sub-crop
// (big-sheet children: l,t != 0) or a staged pre-scaled crop (already
// (0,0,newW-ish,newH-ish), != old area) can never match. Idempotent with the
// healthy order too: if the sweep ever runs before the first bind, the crop
// is the staged one, the guard skips, and the game's own SetImage latches
// correctly against the enlarged window.
//
// ⚠ DELIBERATELY TIER-GENERAL - this is a runtime ordering fix, not art
// maths; the same stale latch fires at 2x/3x whenever a session gets no
// post-sweep rating tick, so gating it to fractional factors would re-ship
// the historical 2x half-bar. There is no arithmetic of ours in the path:
// the values written are exactly what the game's next SetImage would write.
// ⚠ ADVERSARIAL REVIEW 2026-08-16 NARROWED THE SCOPE, and the reasons are
// load-bearing:
//   * `crop == (0,0,oldW,oldH)` alone is NOT unique to the latch - 577 of 877
//     authored .UI imagerects are full-area-at-origin, and 34 of those are the
//     TOP-LEFT CELL of a larger sheet; expanding such a crop drags neighbour
//     art into the window. The discriminator is the ROOT: under the
//     kAlwaysScaleCityIds roots every staged script pre-scales its crops, so
//     an authored crop there can never equal the OLD (1x) area - only a
//     SetImage latch can. The relatch is therefore ARMED per panel root
//     (gRelatchArmed), never blanket.
//   * That scoping also keeps it out of the kCityDialogIds pass, where
//     BMPRECT (:9042) multiplies crops AFTER ScaleSubtree - the two rewrites
//     composing would double-scale a crop. BMPRECT additionally gained its
//     own belt (skip a crop that already equals the window's area).
//   * Edge/9-slice windows (flag bit 8) carry slice geometry in the rect -
//     excluded, same test BMPX uses (:8895).
//   * KNOWN INERT population: BMPX-hooked instances carry a swapped vtable
//     and fail the class test; they are already served by BMPX's dst-stretch.
//   * KNOWN RESIDUAL: if the GAME later shrinks a relatched window without a
//     rebind and Classify tombstones it, the crop outlives the geometry and
//     overdraws until the next SetImage. Reachable only for reset-fighting
//     windows, none of which live under the armed roots today.
namespace
{
	int RelatchBmpSourceRect(cIGZWin* w, int32_t oldW, int32_t oldH,
		int32_t newW, int32_t newH, int32_t* outW, int32_t* outH)
	{
		__try
		{
			if (*reinterpret_cast<void**>(w) != kBmpClassVt) { return 0; }
			// Flag holder at [this+0xd8]: bit 0x10 = "has imagerect", bit 8 =
			// edge/9-slice (slice geometry lives in the rect - hands off).
			// Same access pattern as BMPRECT above; hvt[10] is the flag test.
			char* holder = reinterpret_cast<char*>(w) + 0xd8;
			void** hvt = *reinterpret_cast<void***>(holder);
			if (!hvt || !hvt[10]) { return 0; }
			if (!reinterpret_cast<BmpFlagTestFn>(hvt[10])(holder, 0x10))
			{
				return 0;
			}
			if (reinterpret_cast<BmpFlagTestFn>(hvt[10])(holder,
				kBmpEdgeFlagBit))
			{
				return 0;
			}
			cIGZBuffer* img = *reinterpret_cast<cIGZBuffer**>(
				reinterpret_cast<char*>(w) + 0xdc);
			if (!img) { return 0; }
			int32_t* r = reinterpret_cast<int32_t*>(
				reinterpret_cast<char*>(w) + 0xe8);
			if (r[0] != 0 || r[1] != 0 || r[2] != oldW || r[3] != oldH)
			{
				return 0;   // not latch-following: leave every real crop alone
			}
			// Same sanity floor as ScanRegion (:1384): a torn-down or not-yet
			// Init'ed buffer reads 0x0 and would collapse the crop to nothing,
			// which is strictly worse than the stale-but-visible status quo.
			const int32_t iw = img->Width();
			const int32_t ih = img->Height();
			if (iw <= 0 || ih <= 0 || iw > 8192 || ih > 8192) { return 0; }
			// Mirror 0x9BC447's clamp exactly: crop = min(new area, image).
			const int32_t cw = (newW < iw) ? newW : iw;
			const int32_t ch = (newH < ih) ? newH : ih;
			if (cw == r[2] && ch == r[3]) { return 0; }   // no-op: no log slot
			r[2] = cw;
			r[3] = ch;
			if (outW) { *outW = cw; }
			if (outH) { *outH = ch; }
			return 1;
		}
		__except (EXCEPTION_EXECUTE_HANDLER) {}
		return 0;
	}
}

void UiSpike::ScaleSubtree(cIGZWin* win, float f, int depth, int* count,
	bool centerLeaves, int32_t pAbsL, int32_t pAbsT)
{
	// v2.69.0: both caps used to truncate in SILENCE. That is the #53 failure
	// class exactly - windows past the cap stay 1x, and the log shows a clean
	// run, so the next session reads "scaled fine" from an instrument that
	// never saw them. Say so, once per city, for each cap independently.
	if (win && depth > kMaxDepth)
	{
		static int depthWarnEpoch = -1;
		if (depthWarnEpoch != gGaugeEpoch)
		{
			depthWarnEpoch = gGaugeEpoch;
			Logger::Get().WriteLine(LogLevel::Info,
				"UiSpike: ScaleSubtree DEPTH CAP %d reached under id=0x%08X - "
				"deeper windows are NOT scaled", kMaxDepth, win->GetID());
		}
	}
	if (win && depth <= kMaxDepth && *count >= kMaxWindows)
	{
		static int countWarnEpoch = -1;
		if (countWarnEpoch != gGaugeEpoch)
		{
			countWarnEpoch = gGaugeEpoch;
			Logger::Get().WriteLine(LogLevel::Info,
				"UiSpike: ScaleSubtree WINDOW CAP %d reached - the remainder of "
				"this subtree is NOT scaled", kMaxWindows);
		}
	}
	if (!win || depth > kMaxDepth || *count >= kMaxWindows)
	{
		return;
	}

	const ScaleState state = Classify(win);

	// #161: this window's absolute DESIGN origin, for its children to round in.
	// Set only on the pass that positions it; 0 means "unknown", which is the
	// identity R(0+t) - R(0) == R(t) and therefore the pre-#161 behaviour.
	int32_t kidAbsL = 0, kidAbsT = 0;

	// [UiSpike] ParentFrameRounding=0 restores the pre-#161 maths exactly, by
	// collapsing the inherited frame to the identity. This change touches EVERY
	// scaled child at a fractional tier, so it ships with its own off switch -
	// and it is the A/B that says whether a newly-noticed 1px seam is this
	// change or was always there.
	if (!settings.spikeParentFrameRounding) { pAbsL = 0; pAbsT = 0; }

	// Ticker marquee (AdviceList): NEVER touch, NEVER recurse - the game
	// re-imposes its cached geometry every roll tick (the scaled width
	// ships in the edited .UI script; see kAdviceListNeverTouchIds).
	if (IsAdviceListNeverTouchId(win->GetID()))
	{
		return;
	}

	if (state == ScaleState::Fresh || state == ScaleState::ResetToOriginal)
	{
		// Geometry read at mutation time (GZWinMoveTo is RELATIVE - the
		// delta must come from the CURRENT position, see ScalePanelRoot).
		const int32_t l = win->GetL();
		const int32_t t = win->GetT();
		const int32_t w = win->GetW();
		const int32_t h = win->GetH();

		// CENTER-IN-SLOT mode for small leaves: 1x art that cannot grow
		// (exemplar-bound icons) looks intentional centered in its doubled
		// slot, and broken anchored top-left in it. The window KEEPS its 1x
		// size (record scaledW==origW -> AlreadyScaled next pass, so the
		// centering is applied exactly once) and moves to the center of
		// where its scaled slot would be.
		const bool centerThisLeaf =
			(centerLeaves || settings.spikeCenterSmallLeaves)
			&& depth > 0
			&& win->GetChildCount() == 0
			&& w <= settings.spikeCenterLeafMaxPx
			&& h <= settings.spikeCenterLeafMaxPx;
		if (centerThisLeaf)
		{
			// #161: the slot is the parent's frame, so round it there too -
			// otherwise a centred leaf centres on a slot the parent never has.
			const int32_t cAL = pAbsL + l, cAT = pAbsT + t;
			const int32_t cBaseL = ScaleRound(pAbsL, f), cBaseT = ScaleRound(pAbsT, f);
			const int32_t slotCenterX = (ScaleRound(cAL, f) - cBaseL)
				+ (ScaleRound(cAL + w, f) - ScaleRound(cAL, f)) / 2;
			const int32_t slotCenterY = (ScaleRound(cAT, f) - cBaseT)
				+ (ScaleRound(cAT + h, f) - ScaleRound(cAT, f)) / 2;
			const int32_t newL = slotCenterX - w / 2;
			const int32_t newT = slotCenterY - h / 2;
			win->GZWinMoveTo(newL - l, newT - t);
			ScaleRecord rec = { win->GetID(), w, h, w, h, 0, false };
			StoreScaleRecord(win, rec);
			(*count)++;
			return; // leaf: nothing to recurse
		}

		// Edge-derived rounding: newW = round(r*f) - round(l*f), so
		// siblings that abut before scaling still abut after it (rounding
		// the width directly drifts abutting edges apart at non-integer
		// factors). Bit-identical to the old truncation math at f=2.0.
		//
		// #161 — AND THE EDGES MUST BE ROUNDED IN THE PARENT'S FRAME, NOT THE
		// CHILD'S. Edge-derived rounding makes a scaled size depend on POSITION
		// (the #148 note below says so). The parent's extent was rounded at its
		// own absolute origin; a child rounded at a local origin of 0 therefore
		// lands somewhere the parent's extent never reaches. MEASURED on the god
		// toolbar at 1.5x, which is what the user saw as "a break in the white
		// line on the left that is not in 2x or stock":
		//
		//   strip  pos(5,1011) 74x351 -> height = R(1011+351) - R(1011) = 526
		//   cap    pos(0, 351) at a LOCAL origin -> top = R(351) - R(0)   = 527
		//                                          ^ one transparent pixel
		//
		// Rounding the cap at the parent's origin gives R(1011+351) - R(1011) =
		// 526 - exactly the parent's bottom. Siblings still abut, because they
		// all share pAbs.
		//
		// ⚠ NO-OP AT AN INTEGER FACTOR BY CONSTRUCTION: ScaleRound is exact
		// there, so R(a+b) - R(a) == R(b) for every a. 2x and 3x cannot move.
		// Callers that pass no origin get pAbs = 0, which is the identity
		// R(0+t) - R(0) == R(t) - i.e. exactly the previous behaviour.
		const int32_t aL = pAbsL + l;
		const int32_t aT = pAbsT + t;
		kidAbsL = aL;                 // #161: hand this frame to the children
		kidAbsT = aT;
		const int32_t baseL = ScaleRound(pAbsL, f);
		const int32_t baseT = ScaleRound(pAbsT, f);
		const int32_t newL = ScaleRound(aL, f) - baseL;
		const int32_t newT = ScaleRound(aT, f) - baseT;
		// ⛔ #167: A STATE-STRIP BUTTON IS SIZED AS A LENGTH, NOT BY ITS EDGES.
		//
		// MEASURED by DRAWPROBE (slot 88, the paint entry point) in a live
		// 1.5x city session, and this is the first time these numbers have ever
		// been observed rather than modelled:
		//
		//   advisor frame 0xCA15C7CF  live rect (464,53  82x141)
		//   its art cell  {46A006B0,14015571}      332/4 =  83x141
		//
		// design 55 * 1.5 = 82.5. The ART rounds UP as a length -> 83. The
		// WINDOW rounds DOWN from its edges -> 82. A GZWinBtn draws its cell at
		// NATIVE SIZE and never reads the window's width, so 83 px of art go
		// into an 82 px window - seven times across the advisor row. At 2x and
		// 3x, 55*f is exact and window == cell == 110 / 165, which is why the
		// integer tiers have never shown it.
		//
		// SCOPED BY CLASS, WHICH IS THE ROLE (law 86), NOT BY AN ID LIST.
		// DRAWPROBE reported the vtable for every watched window: the advisor
		// FRAMES and both dashboard buttons all paint through 0x00ADDAF0, while
		// the advisor FACES paint through 0x00ADC678 and are NOT state strips.
		// Keying on the class is therefore derived from measurement and cannot
		// rot the way a hand-list does (law 94).
		//
		// ⚠ THIS DOES NOT REVERSE #161. #161 governs a child's POSITION - newL
		// and newT above still round in the parent's absolute design frame, so
		// edges still land on their parent's and their siblings'. Only the
		// EXTENT changes, and only for a window whose art cell must fit inside
		// it. Position edge-derived, size length-derived.
		//
		// ⚠ PROVABLE NO-OP AT AN INTEGER FACTOR: when v*f is exact for all v,
		// R(a+w)-R(a) = wf = R(w*f) identically, so 2x and 3x cannot move.
		bool stripBtnClass = false;
		__try
		{
			stripBtnClass =
				(*reinterpret_cast<void**>(win) == reinterpret_cast<void*>(0x00ADDAF0));
		}
		__except (EXCEPTION_EXECUTE_HANDLER) { stripBtnClass = false; }
		int32_t newW = stripBtnClass ? ScaleRound(w, f)
			: (ScaleRound(aL + w, f) - ScaleRound(aL, f));
		int32_t newH = stripBtnClass ? ScaleRound(h, f)
			: (ScaleRound(aT + h, f) - ScaleRound(aT, f));

		// #148 THE REVERSE L: A LEAF TAKES ITS SIZE, NOT ITS EDGES.
		//
		// Edge-derived rounding makes the scaled SIZE depend on the POSITION.
		// At f=1.5 that costs a control one pixel whenever l is odd:
		//     l=68 : 68*1.5 = 102 exact    ; 115*1.5 = 172.5 -> 173 ; w = 71
		//     l=69 : 69*1.5 = 103.5 -> 104 ; 116*1.5 = 174   exact  ; w = 70
		// The four-state art sheet is 284 wide, so its cell is 284/4 = 71 for
		// BOTH. The odd-edge control gets a 71px cell in a 70px window and the
		// uncovered right column plus bottom row draw as a REVERSE L. That is
		// exactly what the user saw on Landscape's "Level Terrain" (the only
		// one of five buttons at an odd l) and on the god-mode Day/Night sun
		// and moon (all three at l=79).
		//
		// ⛔ WHY THE SIZE AND NOT THE POSITION. The first repair moved such
		// buttons onto an even edge, in the .UI, at build time. It fixed the
		// reported cases and SHIPPED A WORSE BUG: a nudge is up to 2px at 1.5x,
		// and in the densest grid in the game ("Select A My Sim", 21 faces) the
		// whole grid visibly slid left inside its own frame. Reverted the same
		// day. Changing the WIDTH moves nothing and is bounded by one pixel.
		//
		// ⛔ WHY LEAVES ONLY. Edge-derived rounding exists so that abutting
		// pieces stay abutting - #143's white seams are what happens when they
		// do not. A window WITH CHILDREN is a panel: it tiles with its
		// neighbours and its edges are load-bearing. A LEAF is a discrete icon;
		// nothing is butted against it, so a one-pixel size change is invisible
		// while a one-pixel art mismatch is not. Containers keep edge-derived
		// rounding untouched, so the seams cannot come back.
		//
		// ⚠ NO-OP AT AN INTEGER FACTOR BY CONSTRUCTION: ScaleRound(l*2) is
		// exact for every l, so edge-derived and size-derived already agree.
		// 2x and 3x are unaffected - the branch cannot fire there.
		if (win->GetChildCount() == 0)
		{
			const int32_t sizeW = ScaleRound(w, f);
			const int32_t sizeH = ScaleRound(h, f);
			if (sizeW != newW || sizeH != newH)
			{
				static int leafFixEpoch = -1;
				static int leafFixCount = 0;
				if (leafFixEpoch != gGaugeEpoch)
				{
					leafFixEpoch = gGaugeEpoch;
					leafFixCount = 0;
				}
				if (leafFixCount < 8)
				{
					leafFixCount++;
					Logger::Get().WriteLine(LogLevel::Info,
						"UiSpike: LEAFSIZE id=0x%08X l=%d t=%d %dx%d -> edge %dx%d "
						"SIZE %dx%d (#148 reverse-L; position unchanged)",
						win->GetID(), l, t, w, h, newW, newH, sizeW, sizeH);
				}
				newW = sizeW;
				newH = sizeH;
			}
		}

		// FONT-SIZED control: its size already followed the 2x font, so move
		// it into place and leave the size alone (see kFontSizedIds). Recorded
		// with scaled==current so the next sweep classifies it AlreadyScaled;
		// if its owner later re-sizes it from the font, that reads as
		// Unrecognized and we still never fight it.
		if (IsFontSizedId(win->GetID()))
		{
			if (depth > 0)
			{
				win->GZWinMoveTo(newL - l, newT - t);
			}
			ScaleRecord rec = { win->GetID(), w, h, w, h, 0, false };
			StoreScaleRecord(win, rec);
			(*count)++;
			Logger::Get().WriteLine(
				LogLevel::Debug,
				"UiSpike: font-sized 0x%08X pos (%d,%d)->(%d,%d), size %dx%d kept.",
				win->GetID(), l, t, newL, newT, w, h);
			return;
		}

		if (passScreenW > 0 && (newW > passScreenW || newH > passScreenH))
		{
			// Belt-and-braces double-scale guard (see ScalePanelRoot).
			// Tombstone so the next pass does not retry forever (guard spam).
			Logger::Get().WriteLine(
				LogLevel::Debug,
				"UiSpike: window 0x%08X target %dx%d exceeds frame - skipped and tombstoned.",
				win->GetID(), newW, newH);
			ScaleRecord dead = { win->GetID(), w, h, w, h, 0, true };
			scaleMap[win] = dead;
		}
		else
		{
			(*count)++;

			// Resize self. Root keeps its anchor; descendants also scale
			// their position within the (already-scaled) parent so the
			// layout grows coherently instead of bunching in the top-left.
			//
			win->SetW(newW);
			win->SetH(newH);
			if (depth > 0)
			{
				win->GZWinMoveTo(newL - l, newT - t);
			}

			// #176: SetArea never refreshes a GZWinBMP's SetImage-latched
			// source rect, so a code-bound bitmap keeps drawing at the
			// pre-resize size until the next SetImage (see RelatchBmpSourceRect
			// above). ARMED per root, never blanket - see the scope note
			// there. Log per fire (law 54), capped like LEAFSIZE, WITH a
			// saturation notice - the fire count is this change's
			// blast-radius measurement and must not truncate silently.
			int32_t rlW = 0, rlH = 0;
			if (gRelatchArmed
				&& RelatchBmpSourceRect(win, w, h, newW, newH, &rlW, &rlH))
			{
				static int relatchEpoch = -1;
				static int relatchCount = 0;
				if (relatchEpoch != gGaugeEpoch)
				{
					relatchEpoch = gGaugeEpoch;
					relatchCount = 0;
				}
				relatchCount++;
				if (relatchCount <= 8)
				{
					Logger::Get().WriteLine(LogLevel::Info,
						"UiSpike: RELATCH id=0x%08X imagerect (0,0,%d,%d) -> "
						"(0,0,%d,%d) across %dx%d->%dx%d resize (#176)",
						win->GetID(), w, h, rlW, rlH, w, h, newW, newH);
					if (relatchCount == 8)
					{
						Logger::Get().WriteLine(LogLevel::Info,
							"UiSpike: RELATCH log saturated - further fires "
							"this city are counted but not printed.");
					}
				}
			}

			ScaleRecord rec = { win->GetID(), w, h, newW, newH, 0, false };
			StoreScaleRecord(win, rec);
		}
	}
	// AlreadyScaled: skip the mutation, still recurse (sweeps revisit
	// scaled panels looking for NEW descendants).
	// Unrecognized: the game resized it after we scaled it - leave it alone
	// (fails toward under-scaling, never compounds).

	// AdviceList containers: self scaled above (normal treatment - the box
	// is .UI-derived), but children are game-managed items born at the
	// scaled container size. Recursing double-scales them (v2.18.6 news
	// reader item at 1648x708). See kAdviceListScaleSelfIds.
	if (IsAdviceListScaleSelfId(win->GetID()))
	{
		return;
	}

	if (win->GetChildCount() > 0)
	{
		// Snapshot-then-mutate: collect the child pointers BEFORE touching
		// any of them, so nothing mutates a child list mid-enumeration.
		// Within this stack frame nothing else runs (single UI thread, our
		// code never pumps), so the pointers are valid when collected.
		ChildSnapshot snap = {};
		win->EnumChildren(GZIID_cIGZWin, ChildSnapshot::Callback, &snap);
		// ---- #117 (v2.69.0): why this verify is now CONDITIONAL --------------
		// The verify below is a CRASH KILLER and it stays. What changed is WHEN
		// it runs. It used to run on every iteration i>0, at every level of an
		// 8-deep recursion, on a 16 ms tick - a full re-enumeration per child.
		//
		// â›” DO NOT "optimise" this by hoisting the enumeration out of the loop.
		// That is the obvious fix and it is WRONG: the list is re-read precisely
		// because OUR OWN WRITES can make the game destroy a later sibling, so a
		// snapshot taken before the loop is stale by construction.
		//
		// The sound gate is: skip the verifies only while NOTHING has mutated
		// yet. Nothing else runs inside this stack frame (single UI thread,
		// our code never pumps - see the snapshot note above), so until our
		// first write the child list provably equals the snapshot. Once
		// anything has mutated, EVERY later index verifies.
		//
		// v2.69.3 CORRECTION (found by adversarial review, verified in
		// source): v2.69.0 also RE-BASELINED the signal inside the loop
		// whenever a verify ran ("verifiedAtCount = *count" after the
		// enumeration). That was unsound: a verify proves liveness of ONE
		// pointer - snap.wins[i] - and says nothing about the remainder, so
		// crediting later indices with it reintroduced the use-after-free.
		// Kill sequence: i=0 mutates and the game tears down c1 AND c2;
		// i=1 verifies (c1 dead, continue) and consumed the signal; i=2 saw
		// the count unchanged since that verify, SKIPPED its check, and
		// dereferenced freed c2. The old code was safe precisely because
		// every i>0 re-verified. The baseline is therefore taken ONCE,
		// before the loop, and never advanced: the skip window is only the
		// provably-safe prefix before the first mutation. The O(n^2) win is
		// unchanged - the steady state ("everything already scaled") never
		// moves the count and still costs zero enumerations.
		//
		// The mutation signal is *count itself, and it is EXACT rather than a
		// new flag that could miss a site: every SetW/SetH/GZWinMoveTo in this
		// function (:13104, :13129, :13159-13163) and in ScalePanelRoot (:11240-
		// 11242) is paired with a count++ - and it has to be, because the
		// per-panel "%d windows scaled" log lines that every fix in this project
		// was verified against are that same counter. A mutation that failed to
		// count would already have been a visible instrument bug.
		//
		// Steady state is "everything already scaled -> count never moves", so
		// the enumerations collapse to roughly the number of windows actually
		// mutated per tick, which is ~0 once a city has settled.
		int verifiedAtCount = *count;
		for (int i = 0; i < snap.count; i++)
		{
			if (i > 0 && *count != verifiedAtCount)
			{
				// CRASH KILLER: mutating an earlier sibling can make the game
				// destroy a later one (reactive menu layouts during rapid
				// menu switching). Re-verify this pointer is still in the
				// LIVE child list before touching it.
				ChildSnapshot verify = {};
				win->EnumChildren(GZIID_cIGZWin, ChildSnapshot::Callback, &verify);
				// v2.69.3: mid-loop signal reset REMOVED (unsound - see ScaleSubtree).
				bool alive = false;
				for (int j = 0; j < verify.count; j++)
				{
					if (verify.wins[j] == snap.wins[i]) { alive = true; break; }
				}
				if (!alive)
				{
					continue;
				}
			}
			// #161: children round in THIS window's absolute DESIGN frame.
			// kidAbs* is set only on the pass that actually positions this
			// window (Fresh/ResetToOriginal), because only there do we hold its
			// pre-scale l/t - by recursion time GetL()/GetT() already return
			// SCALED coordinates and would silently poison the frame. When it
			// is unknown we pass 0, which is the identity and therefore exactly
			// the old behaviour; an already-scaled child does not move anyway.
			ScaleSubtree(snap.wins[i], f, depth + 1, count, centerLeaves,
				kidAbsL, kidAbsT);
		}
	}
}

void UiSpike::ScaleTarget(cIGZWin* pMainWindow)
{
	Logger& logger = Logger::Get();

	cIGZWin* target = pMainWindow->GetChildWindowFromIDRecursive(settings.spikeScaleWindowId);
	if (!target)
	{
		logger.WriteLine(
			LogLevel::Error, "UiSpike: window 0x%08X not found.", settings.spikeScaleWindowId);
		return;
	}

	const int32_t w = target->GetW();
	const int32_t h = target->GetH();
	const float f = settings.spikeScaleFactor;

	logger.WriteLine(
		LogLevel::Info,
		"UiSpike: scaling SUBTREE of 0x%08X x%.2f (was %dx%d)...",
		settings.spikeScaleWindowId, f, w, h);

	// Guard frame for the size-sanity check.
	passScreenW = pMainWindow->GetW();
	passScreenH = pMainWindow->GetH();

	int count = 0;
	ScaleSubtree(target, f, 0, &count);

	logger.WriteLine(
		LogLevel::Info,
		"UiSpike: subtree scaled, %d windows; root now %dx%d",
		count, target->GetW(), target->GetH());
}

// ============ IN-GAME SCALE SELECTOR (2026-08-19) ======================
// USER REQUEST: a radio beside our resolution/scale readout in Graphic
// Options, shown selected, plus a picker for Auto / 1x / 1.5x / 2x / 3x.
//
// SHAPE: the widgets ship in DATA with our ids and EMPTY captions
// (build_dialog_static.py inject_res_readout); this code fills the text,
// pushes the current state, and reads the player's choice back. Empty in
// data is deliberate and unchanged from #192 - if this code never runs the
// player sees blank space, never a stale or invented number.
//
//   0x5CA1E000  readout text  "<W>x<H> @ <f>x <auto|manual>"
//   0x5CA1E002  radio         lit when NO stock resolution radio is lit
//   0x5CA1E003  label         "UI Scale (applies on restart)"
//   0x5CA1E004  combo         Auto / 1x / 1.5x / 2x / 3x
//
// THE TIER APPLIES ON RESTART, and that is not a shortcut. Switching tier
// renames nine dat packages AND the FontStyle.ini the game probes once at
// startup, so nothing short of a relaunch can move it. This dialog already
// carries the game's OWN notice - "Resolution, UI translucency, color
// quality and rendering mode changes will not take effect until the next
// time you start..." - which is exactly why the control belongs here.
namespace
{
	// Row order MUST match the listelement order the builder writes.
	const float kSelFactors[] = { 0.0f, 1.0f, 1.5f, 2.0f, 3.0f }; // [0] = Auto
	const char* const kSelLabels[] = { "Auto", "1x", "1.5x", "2x", "3x" };
	const int   kSelCount =
		static_cast<int>(sizeof(kSelFactors) / sizeof(kSelFactors[0]));
	// ⛔ THE "needs WxH" NUMBERS ARE NO LONGER COMPUTED HERE. They used to be
	// 880*f and 558*f - this file's own copy of the fit arithmetic - and when
	// that arithmetic was replaced by an explicit per-tier minimum table the
	// caption would have gone on quoting the old numbers at the player. A
	// second copy of a rule is a second rule, and this one is displayed as a
	// promise. ScaleTier::TierMinimum reads the table the boot path enforces.
	void SelMinimumFor(int k, int* w, int* h)
	{
		*w = 0; *h = 0;
		ScaleTier::TierMinimum(kSelFactors[k], w, h);
	}
	bool  gSelUsable[8] = { true, true, true, true, true, true, true, true };
	int   gSelCommitted = -1;       // row currently written to the ini

	// The four stock resolution radios. Our radio means "none of these" -
	// i.e. the resolution came from SC4GraphicsOptions.ini rather than this
	// list, which is the state every scaled tier runs in.
	const uint32_t kStockResRadios[] = {
		0x6A57DA5A, 0x6A57DA5B, 0x6A57DA5C, 0x6A57DA5D
	};
	const uint32_t kSelAcceptId = 0xEA57DA59;   // Accept (the 3-button row)
	const uint32_t kSelCancelId = 0x6A57DA48;   // Cancel
	const uint32_t kSelDlgId    = 0x2A57CB82;   // Graphic Options root (GZWinGen)
	const uint32_t kSelReadoutId = 0x5CA1E000;
	const uint32_t kSelRadioId   = 0x5CA1E002;
	const uint32_t kSelLabelId   = 0x5CA1E003;
	const uint32_t kSelComboId   = 0x5CA1E004;
	// The game's OWN "takes effect next restart" popup, born hidden inside
	// this dialog, and its Accept button.
	const uint32_t kSelNoticeId  = 0x2A57CB83;
	// The four stock resolution LABELS, re-identified in data because they
	// all ship sharing 0xca57da80 (build_dialog_static RES_LABEL_IDS).
	const uint32_t kStockResLabels[] = {
		0x5CA1E010, 0x5CA1E011, 0x5CA1E012, 0x5CA1E013
	};
	bool gSelResRowsHidden = false;
	unsigned int gSelNoticeShownMs = 0;
	unsigned int gSelClickMs = 0;      // last click seen by the winproc
	// ACCEPT TRACE (2026-08-19). We cannot tell from a message WHICH
	// control was clicked - no id is carried - so the rects of the two
	// buttons that close this dialog are captured when it opens and every
	// click is tested against them. One Accept click settles whether a
	// coordinate hit-test is a sound basis for real Accept semantics.
	int  gSelAcceptRect[4] = { 0, 0, 0, 0 };   // L,T,W,H absolute
	int  gSelCancelRect[4] = { 0, 0, 0, 0 };
	bool gSelRectsOk = false;
	bool gSelNoticeWasUp = false;    // last observed notice visibility
	// RADIO TRACE. The user wants OUR radio to be selectable - clicking it
	// should make the custom resolution the one that applies on restart. Before
	// building that, one measurement is needed: does clicking a GZWinBtn we
	// injected actually CHECK it? It is style=radiocheck but it belongs to no
	// group the game knows about, so whether the engine toggles it on click,
	// or whether only the dialog's own handler does that for ITS radios, is an
	// open question - and guessing it is how a handler keyed on a field the
	// message does not carry got written earlier today.
	int  gSelRadioState = -1;        // bitmask: b0..b3 stock radios, b4 ours
	int  gSelRadioLogs = 0;
	bool gSelOursWas = false;        // our radio last service
	int  gSelStockWas = 0;           // stock radio mask last service
	bool gSelResRescued = false;      // resolution mismatch handled once
	unsigned long long gSelGfxStamp = 0;  // SC4GraphicsOptions.ini mtime
	bool gSelNoticePending = false;   // a change is waiting for Accept
	bool gSelAcceptSeen = false;      // this appearance
	int  gSelTraceLogs = 0;

	int   gSelPushed = -2;          // last row we pushed or observed
	bool  gSelDlgUp = false;        // dialog visible at the last service
	int   gSelLogs = 0;
	int   gSelMsgLogs = 0;          // bounded instrument budget
	unsigned int gSelLastMs = 0;
	void* gSelProcOn = nullptr;     // dialog our proc is currently chained on

	int SelRowFromSettings(const Settings& s)
	{
		if (s.spikeAutoScale) { return 0; }
		for (int k = 1; k < kSelCount; k++)
		{
			// Tier factors are exact halves/wholes; 0.01 sits far inside the
			// smallest gap between any two of them.
			if (s.spikeScaleFactor > kSelFactors[k] - 0.01f &&
				s.spikeScaleFactor < kSelFactors[k] + 0.01f)
			{
				return k;
			}
		}
		return -1;   // a factor no row can express: say nothing, claim nothing
	}

	// Can THIS resolution carry the tier on row k? Auto and 1x always can.
	// Delegated to ScaleTier::Fits so the answer shown to the player is the
	// answer the next launch will actually give.
	bool SelRowUsable(int k)
	{
		if (k <= 1) { return true; }             // Auto, 1x
		if (gReadoutW <= 0 || gReadoutH <= 0)
		{
			// We were never handed a render size, so the FIT question cannot
			// be answered - a missing measurement is not evidence of a small
			// screen. The PACKAGE question needs no screen and still runs.
			return ScaleTier::PackageAvailable(kSelFactors[k]);
		}
		// ⭐ PACKAGE FIRST, THEN FIT. Offering a tier whose art is not
		// installed makes the escape hatch WRITE THE TRAP: the player picks
		// it, and the next boot's validator bounces it straight back to Auto.
		// A control that offers a choice it knows will be refused is worse
		// than one that does not offer it. Same predicate the boot path uses,
		// so the selector and the validator can never disagree.
		return ScaleTier::PackageAvailable(kSelFactors[k])
			&& ScaleTier::Fits(kSelFactors[k], gReadoutW, gReadoutH);
	}

	void SelSetCaption(cIGZWin* parent, uint32_t id, const char* text)
	{
		cIGZWin* w = parent->GetChildWindowFromIDRecursive(id);
		if (!w) { return; }
		cIGZWinText* t = nullptr;
		if (w->QueryInterface(GZIID_cIGZWinText,
				reinterpret_cast<void**>(&t)) && t)
		{
			cIGZString* cur = w->GetCaption();
			const bool same = (cur != nullptr && cur->ToChar() != nullptr
				&& strcmp(cur->ToChar(), text) == 0);
			if (!same)
			{
				cRZBaseString want(text);
				t->SetCaption(want);
			}
			t->Release();
		}
	}

	// COMMIT. One writer for the tier keys, and it writes the SAME two keys
	// Set-Tier.ps1 writes, to the SAME ini Settings::Load reads. Win32 profile
	// writes never emit a BOM, which is the one thing that must stay true of
	// this file: a BOM makes the game's own ini parser miss every key.
	// The ini beside THIS dll - the same file Settings::Load read at startup.
	// Resolved here rather than reusing the director's helper because that one
	// is file-static to the director; duplicating four lines beats exporting a
	// path helper across the module boundary for one call.
	void SelIniPath(wchar_t* out, size_t outLen)
	{
		wchar_t path[MAX_PATH] = {};
		GetModuleFileNameW(reinterpret_cast<HMODULE>(&__ImageBase), path, MAX_PATH);
		wchar_t* lastSlash = wcsrchr(path, L'\\');
		if (lastSlash) { *(lastSlash + 1) = L'\0'; }
		swprintf_s(out, outLen, L"%sSC4UIScale.ini", path);
	}

	// SC4GraphicsOptions.ini sits beside the DLL, same as our own ini.
	void SelGfxIniPath(wchar_t* out, size_t outLen)
	{
		wchar_t path[MAX_PATH] = {};
		GetModuleFileNameW(reinterpret_cast<HMODULE>(&__ImageBase), path, MAX_PATH);
		wchar_t* lastSlash = wcsrchr(path, L'\\');
		if (lastSlash) { *(lastSlash + 1) = L'\0'; }
		swprintf_s(out, outLen, L"%sSC4GraphicsOptions.ini", path);
	}

	// Last-write time of that file, 0 if it cannot be read.
	unsigned long long SelGfxIniStamp()
	{
		wchar_t p[MAX_PATH] = {};
		SelGfxIniPath(p, MAX_PATH);
		WIN32_FILE_ATTRIBUTE_DATA fad = {};
		if (!GetFileAttributesExW(p, GetFileExInfoStandard, &fad)) { return 0ull; }
		ULARGE_INTEGER u;
		u.LowPart = fad.ftLastWriteTime.dwLowDateTime;
		u.HighPart = fad.ftLastWriteTime.dwHighDateTime;
		return u.QuadPart;
	}

	// ⭐ WHAT WE COMMITTED, FOR DISPLAY ONLY - and it is why the control
	// looked broken. SelCommit writes the INI; it deliberately does not touch
	// the live `settings`, because spikeScaleFactor is read all over the
	// running game and changing it mid-session would move geometry that the
	// art cannot follow until the next launch.
	//
	// But the combo seeded itself from `settings` on every open, so the moment
	// the dialog was reopened it snapped back to whatever was RUNNING - Auto -
	// and every deliberate choice looked like it had been thrown away. The
	// user reported exactly that: "no matter the resolution I select it just
	// jumps back to auto". The commits were all in the log; only the display
	// was lying.
	//
	// So the display reads the PENDING choice when there is one, and the live
	// settings otherwise. Nothing about the running game changes.
	int gSelPendingRow = -1;

	void SelCommit(int row)
	{
		if (row < 0 || row >= kSelCount) { return; }
		gSelPendingRow = row;
		wchar_t ini[MAX_PATH] = {};
		SelIniPath(ini, MAX_PATH);
		if (ini[0] == 0) { return; }
		if (row == 0)
		{
			WritePrivateProfileStringW(L"UiSpike", L"AutoScale", L"1", ini);
			Logger::Get().WriteLine(LogLevel::Info,
				"UiSpike: SELECTOR committed AutoScale=1 (Auto) to %ls. "
				"Applies at the next launch.", ini);
		}
		else
		{
			// %g so 1.5 stays "1.5" and 2 stays "2" - the same literals the
			// ini already carries and Set-Tier.ps1 writes.
			wchar_t val[32] = {};
			swprintf_s(val, L"%g", kSelFactors[row]);
			WritePrivateProfileStringW(L"UiSpike", L"AutoScale", L"0", ini);
			WritePrivateProfileStringW(L"UiSpike", L"ScaleFactor", val, ini);
			Logger::Get().WriteLine(LogLevel::Info,
				"UiSpike: SELECTOR committed AutoScale=0 ScaleFactor=%ls to "
				"%ls. Applies at the next launch.", val, ini);
		}
	}

	// ⭐ THE GAME ALREADY OWNS THIS BOX (user direction, 2026-08-19).
	// 0x2A57CB83 is a GZWinGen born hidden inside Graphic Options carrying the
	// stock text "Resolution, UI translucency, color quality, color cursor and
	// rendering mode changes will not take effect until the next time you
	// start the game." - which is EXACTLY true of a tier change, for exactly
	// the same reason (the setting is read once, at startup). Showing the
	// game's own notice beats inventing a second one that says the same thing
	// in our words: same wording, same art, same place the player already
	// learned to expect it.
	//
	// Its Accept button (0xEA57DA6F) is the game's, and so is whatever hides
	// the box again. We only ever SHOW it - see the dismissal safety net in
	// the winproc, which exists because we cannot see that button's clicks.
	void ShowRestartNotice(cIGZWin* gfxDlg)
	{
		cIGZWin* notice = gfxDlg->GetChildWindowFromIDRecursive(kSelNoticeId);
		if (!notice)
		{
			Logger::Get().WriteLine(LogLevel::Info,
				"UiSpike: SELECTOR restart notice %08X not found - the scale "
				"still changed, the player just was not told.", kSelNoticeId);
			return;
		}
		if (!notice->IsVisible())
		{
			notice->ShowWindow();
			gSelNoticeShownMs = GetTickCount();
			Logger::Get().WriteLine(LogLevel::Info,
				"UiSpike: SELECTOR showed the game's own restart notice.");
		}
	}

	// Our WinProc CHAINS - it never replaces the dialog's own handler. The
	// game's Accept/Cancel/radio logic lives behind GetWinProc(); dropping it
	// would break the dialog outright, so every message is forwarded and our
	// return value is whatever the game's proc said.
	class SelectorWinProc : public cIGZWinProc
	{
	public:
		SelectorWinProc() : refCount(0), next(nullptr) {}

		void SetNext(cIGZWinProc* p) { next = p; }

		bool QueryInterface(uint32_t riid, void** ppvObj) override
		{
			if (riid == GZIID_cIGZWinProc)
			{
				*ppvObj = static_cast<cIGZWinProc*>(this);
				AddRef();
				return true;
			}
			if (riid == GZIID_cIGZUnknown)
			{
				*ppvObj = static_cast<cIGZUnknown*>(this);
				AddRef();
				return true;
			}
			return false;
		}
		uint32_t AddRef() override { return ++refCount; }
		uint32_t Release() override
		{
			// Deliberately NEVER self-deletes. This object is a singleton
			// owned by the DLL for the process lifetime; the dialog can be
			// created and destroyed many times, and a use-after-free here
			// would be a crash inside the game's own message pump.
			if (refCount > 0) { --refCount; }
			return refCount;
		}

		bool DoWinProcMessage(cIGZWin* pWin, cGZMessage& pMsg) override
		{
			Observe(pMsg.dwMessageType, pMsg.dwData1, pMsg.dwData2,
				pMsg.dwData3);
			return next ? next->DoWinProcMessage(pWin, pMsg) : false;
		}

		bool DoWinMsg(cIGZWin* pWin, uint32_t id, uint32_t d1, uint32_t d2,
			uint32_t d3) override
		{
			Observe(id, d1, d2, d3);
			return next ? next->DoWinMsg(pWin, id, d1, d2, d3) : false;
		}

	private:
		// INSTRUMENT AND ARM TOGETHER. We do not know which message id a
		// button click arrives as, so the commit is keyed on the CONTROL ID
		// appearing in either data slot rather than on a guessed message
		// type - those ids are unique to this dialog, so it cannot fire on
		// anything else, and it does not depend on which of the two message
		// shapes the engine uses. The bounded log beside it is what proves
		// which shape actually arrived.
		void Observe(uint32_t id, uint32_t d1, uint32_t d2, uint32_t d3)
		{
			const bool accept = (d1 == kSelAcceptId || d2 == kSelAcceptId);
			const bool cancel = (d1 == kSelCancelId || d2 == kSelCancelId);
			// ⛔ THE HOVER TYPES ARE EXCLUDED ON PURPOSE. The first capture
			// spent 96 of its 120 lines on three message types that repeat on
			// every mouse move (0xA2BF8ACD/CE/CF, each carrying one unchanging
			// window pointer), which is how a bounded instrument can fill up
			// with noise and MISS the one event it was armed for. Same shape
			// as a grep that filters out the adjacent line holding the answer.
			const bool hoverNoise = (id == 0xA2BF8ACDu || id == 0xA2BF8ACEu
				|| id == 0xA2BF8ACFu);
			if (!hoverNoise && gSelMsgLogs < 80)
			{
				gSelMsgLogs++;
				Logger::Get().WriteLine(LogLevel::Info,
					"UiSpike: SELMSG type=0x%08X d1=0x%08X d2=0x%08X "
					"d3=0x%08X%s", id, d1, d2, d3,
					accept ? "  <- ACCEPT id" :
					cancel ? "  <- CANCEL id" :
					(d1 == kSelComboId || d2 == kSelComboId) ? "  <- our COMBO" :
					(d1 == kSelRadioId || d2 == kSelRadioId) ? "  <- our RADIO" : "");
			}
			// THE ACCEPT TRACE. Type 0x0D carries x in d1 and y in d2 - the
			// one directly usable fact the first capture established. Test it
			// against the two closing buttons and SAY SO, so a single click
			// tells us whether their coordinates and ours share a space.
			if (id == 0x0000000Du && gSelRectsOk && gSelTraceLogs < 40)
			{
				gSelTraceLogs++;
				const int x = static_cast<int>(d1), y = static_cast<int>(d2);
				const bool inAcc =
					x >= gSelAcceptRect[0] && x < gSelAcceptRect[0] + gSelAcceptRect[2] &&
					y >= gSelAcceptRect[1] && y < gSelAcceptRect[1] + gSelAcceptRect[3];
				const bool inCan =
					x >= gSelCancelRect[0] && x < gSelCancelRect[0] + gSelCancelRect[2] &&
					y >= gSelCancelRect[1] && y < gSelCancelRect[1] + gSelCancelRect[3];
				Logger::Get().WriteLine(LogLevel::Info,
					"UiSpike: SELHIT click (%d,%d) accept=[%d,%d %dx%d]->%s "
					"cancel=[%d,%d %dx%d]->%s", x, y,
					gSelAcceptRect[0], gSelAcceptRect[1], gSelAcceptRect[2],
					gSelAcceptRect[3], inAcc ? "HIT" : "miss",
					gSelCancelRect[0], gSelCancelRect[1], gSelCancelRect[2],
					gSelCancelRect[3], inCan ? "HIT" : "miss");
			}
			// ⛔ NO COMMIT HERE ANY MORE. This used to fire when a message
			// carried the Accept button's id, and the instrument below proved
			// no such message exists - 120 captured messages, every one a
			// mouse coordinate pair or a repeated window pointer, not one
			// control id in any slot. The commit moved to the selection
			// change itself, which is observable. Kept as an INSTRUMENT: if a
			// message ever does carry one of these ids, the log says so and
			// real Accept/Cancel semantics become available.
			(void)accept;
			(void)cancel;
			// The ONE fact this instrument established that is directly
			// usable: type 0x0000000D is a mouse click, carrying x in d1 and
			// y in d2. We cannot tell WHICH control was hit - no id is
			// present in any slot - but "a click happened" is enough for the
			// restart notice's safety net below.
			if (id == 0x0000000Du) { gSelClickMs = GetTickCount(); }
		}

		uint32_t refCount;
		cIGZWinProc* next;
	};

	SelectorWinProc gSelProc;
}

void UiSpike::ServiceScaleSelector()
{
	// Throttle. The dialog is almost never open, so a 250ms beat is
	// imperceptible and turns a per-frame recursive id search into a rounding
	// error against the ~16ms tick.
	const unsigned int now = GetTickCount();
	if (gSelLastMs != 0 && (now - gSelLastMs) < 250u) { return; }
	gSelLastMs = now;

	cISC4AppPtr pSC4App;
	if (!pSC4App) { return; }
	cIGZWin* pMainWindow = pSC4App->GetMainWindow();
	if (!pMainWindow) { return; }

	cIGZWin* gfxDlg = pMainWindow->GetChildWindowFromIDRecursive(kSelDlgId);
	if (gfxDlg == nullptr || !gfxDlg->IsVisible())
	{
		// Closed. Forget the staged choice: a dialog dismissed without Accept
		// must commit nothing, and the next open re-reads the live settings.
		if (gSelDlgUp)
		{
			// Closed. Drop the per-appearance state so the next open re-reads
			// the live settings and re-derives which tiers this resolution
			// can carry - the player may have changed the resolution in the
			// same visit.
			gSelDlgUp = false;
			gSelPushed = -2;
			gSelCommitted = -1;
			if (gSelNoticePending)
			{
				// The change is committed and WILL apply; only the notice was
				// missed. Say that plainly - a detector that silently never
				// fires is indistinguishable from one that works.
				Logger::Get().WriteLine(LogLevel::Info,
					"UiSpike: SELACCEPT the dialog closed with a scale change "
					"pending and NO write to SC4GraphicsOptions.ini was ever "
					"seen. The change is committed and applies next launch; "
					"the notice did not show because Accept could not be "
					"detected this way either.");
			}
			gSelNoticePending = false;
			gSelAcceptSeen = false;
		}
		return;
	}
	const bool justOpened = !gSelDlgUp;
	gSelDlgUp = true;

	// ---- 0. THE RESOLUTION THE GAME ACTUALLY LAID OUT AT -----------------
	// ⭐ THE TIER IS DECIDED FROM AN INFERENCE; THIS IS THE MEASUREMENT.
	// At PreAppInit there is no window yet, so the director must PREDICT the
	// render size from two SC4GraphicsOptions.ini keys plus a rule about what
	// the wrapper does with them ("DirectX + FullScreen -> monitor native,
	// requested size ignored"). That rule is right for this machine's current
	// setup and it is still an inference about someone else's software.
	//
	// pMainWindow->GetW()/GetH() is the size the UI was ACTUALLY laid out at.
	// If it disagrees with what the tier was decided from, the tier was chosen
	// from a number that never happened - which is what the user hit after
	// changing resolution here: the resolution moved and the text stayed
	// scaled, because the prediction still said the old size.
	//
	// Per the standing instruction for this case, a disagreement flips to Auto
	// for the NEXT launch rather than trying to rescale a live game: the tier
	// packages and the font are chosen once, at startup, and cannot move now.
	{
		const int32_t realW = pMainWindow->GetW();
		const int32_t realH = pMainWindow->GetH();
		if (realW > 0 && realH > 0 && gReadoutW > 0 && gReadoutH > 0
			&& !gSelResRescued)
		{
			// 64px of slack: window chrome and rounding are not a resolution
			// change, and a gauge that fires on noise is worse than none.
			const int dw = realW > gReadoutW ? realW - gReadoutW : gReadoutW - realW;
			const int dh = realH > gReadoutH ? realH - gReadoutH : gReadoutH - realH;
			if (dw > 64 || dh > 64)
			{
				gSelResRescued = true;
				const bool badNow =
					!ScaleTier::Fits(settings.spikeScaleFactor, realW, realH);
				Logger::Get().WriteLine(LogLevel::Info,
					"UiSpike: RESMISMATCH the tier was decided from %dx%d but "
					"the UI is laid out at %dx%d. Factor %.2f %s that size.",
					gReadoutW, gReadoutH, realW, realH,
					settings.spikeScaleFactor,
					badNow ? "DOES NOT FIT" : "still fits");
				// Report the truth from here on, whatever we do about it.
				gReadoutW = realW;
				gReadoutH = realH;
				if (badNow && !settings.spikeAutoScale)
				{
					wchar_t iniP[MAX_PATH] = {};
					SelIniPath(iniP, MAX_PATH);
					if (iniP[0] != 0)
					{
						WritePrivateProfileStringW(L"UiSpike", L"AutoScale",
							L"1", iniP);
						Logger::Get().WriteLine(LogLevel::Info,
							"UiSpike: RESMISMATCH wrote AutoScale=1 - a manual "
							"factor that cannot fit the size actually being "
							"rendered is exactly the trap the boot rescue "
							"exists for, and the next launch now picks the "
							"tier from the real resolution.");
					}
				}
			}
		}
	}

	// ---- 0a. ACCEPT TRACE: capture the closing buttons' absolute rects ----
	// Captured on OPEN, because that is when they exist and are laid out, and
	// re-captured every open in case the tier (and therefore the geometry)
	// changed. SafeAbsRect walks the parent chain under SEH - the same helper
	// the sweep uses - so a bad pointer cannot take the game down.
	if (justOpened)
	{
		// ⭐ ACCEPT IS DETECTED BY ITS SIDE EFFECT, NOT BY A MESSAGE.
		// The notice belongs on Accept, and the message layer provably cannot
		// deliver that: 36 traced messages, none touching the Accept rect,
		// and none arriving at all at the moment it was pressed. So watch
		// what Accept DOES instead - the game applies its graphics settings,
		// which rewrites SC4GraphicsOptions.ini. A change to that file's
		// timestamp while this dialog is open is Accept happening.
		//
		// Snapshotted per APPEARANCE: Set-Tier.ps1 writes the same file
		// between sessions, and a stale baseline would read as an Accept the
		// instant the dialog opened.
		gSelGfxStamp = SelGfxIniStamp();
		gSelAcceptSeen = false;
		gSelRectsOk = false;
		cIGZWin* acc = gfxDlg->GetChildWindowFromIDRecursive(kSelAcceptId);
		cIGZWin* can = gfxDlg->GetChildWindowFromIDRecursive(kSelCancelId);
		if (acc && can
			&& SafeAbsRect(acc, &gSelAcceptRect[0], &gSelAcceptRect[1],
				&gSelAcceptRect[2], &gSelAcceptRect[3])
			&& SafeAbsRect(can, &gSelCancelRect[0], &gSelCancelRect[1],
				&gSelCancelRect[2], &gSelCancelRect[3]))
		{
			gSelRectsOk = true;
			Logger::Get().WriteLine(LogLevel::Info,
				"UiSpike: SELHIT rects captured - Accept=[%d,%d %dx%d] "
				"Cancel=[%d,%d %dx%d]. Click coordinates are compared against "
				"these; if a click ON Accept reports miss, the two are in "
				"different coordinate spaces and a hit-test is the wrong "
				"mechanism.",
				gSelAcceptRect[0], gSelAcceptRect[1], gSelAcceptRect[2],
				gSelAcceptRect[3], gSelCancelRect[0], gSelCancelRect[1],
				gSelCancelRect[2], gSelCancelRect[3]);
		}
		else
		{
			Logger::Get().WriteLine(LogLevel::Info,
				"UiSpike: SELHIT could not resolve the Accept/Cancel rects "
				"(accept=%p cancel=%p) - the trace cannot run this visit.",
				static_cast<void*>(acc), static_cast<void*>(can));
		}
	}

	// ---- 0c. DOES THE GAME RAISE ITS OWN RESTART NOTICE? -----------------
	// The user reports the stock box appears only AFTER Accept. If the game
	// raises it by itself when a restart-relevant setting changed, that
	// transition is a FREE, exact Accept signal - better than any hit-test.
	// Report every transition either way, so one Accept click says which.
	{
		cIGZWin* nw = gfxDlg->GetChildWindowFromIDRecursive(kSelNoticeId);
		const bool up = (nw != nullptr && nw->IsVisible());
		if (up != gSelNoticeWasUp)
		{
			gSelNoticeWasUp = up;
			Logger::Get().WriteLine(LogLevel::Info,
				"UiSpike: SELNOTICE %s (weShowedItAt=%u) - a rise we did not "
				"cause is the game's own Accept handler, and that transition "
				"is the Accept signal we lack.",
				up ? "VISIBLE" : "hidden", gSelNoticeShownMs);
		}
	}

	// ---- 0. chain our WinProc onto the dialog ---------------------------
	// Re-checked whenever the dialog POINTER changes, not once ever: the
	// dialog can be destroyed and rebuilt, and a rebuilt one carries none of
	// our state.
	if (gSelProcOn != gfxDlg)
	{
		cIGZWinGen* gen = nullptr;
		if (gfxDlg->QueryInterface(GZIID_cIGZWinGen,
				reinterpret_cast<void**>(&gen)) && gen)
		{
			cIGZWinProc* prev = gen->GetWinProc();
			if (prev != static_cast<cIGZWinProc*>(&gSelProc))
			{
				gSelProc.SetNext(prev);
				gen->SetWinProc(&gSelProc);
				gSelProcOn = gfxDlg;
				Logger::Get().WriteLine(LogLevel::Info,
					"UiSpike: SELECTOR winproc chained on Graphic Options "
					"(previous proc %s).", prev ? "kept" : "was none");
			}
			gen->Release();
		}
		else
		{
			Logger::Get().WriteLine(LogLevel::Info,
				"UiSpike: SELECTOR could not get cIGZWinGen on the dialog - "
				"clicks will not be seen.");
			gSelProcOn = gfxDlg;   // do not retry on every service
		}
	}

	// ---- 0aa. DID ACCEPT JUST HAPPEN? -----------------------------------
	// One file stat per 250ms, and only while a dialog nobody leaves open is
	// up. If the game does NOT rewrite that file on Accept this simply never
	// fires - and the close-time line below says so out loud, so a dead
	// detector cannot pass for a working one.
	if (!gSelAcceptSeen)
	{
		const unsigned long long nowStamp = SelGfxIniStamp();
		if (nowStamp != 0 && gSelGfxStamp != 0 && nowStamp != gSelGfxStamp)
		{
			gSelAcceptSeen = true;
			gSelGfxStamp = nowStamp;
			Logger::Get().WriteLine(LogLevel::Info,
				"UiSpike: SELACCEPT SC4GraphicsOptions.ini was rewritten while "
				"Graphic Options is open - that is the game applying its "
				"settings, i.e. Accept. noticePending=%d",
				gSelNoticePending ? 1 : 0);
			if (gSelNoticePending)
			{
				gSelNoticePending = false;
				ShowRestartNotice(gfxDlg);
			}
		}
	}

	// ---- 0b. THE RESTART NOTICE MUST NOT BE ABLE TO TRAP THE PLAYER -----
	// We show the game's own notice; its Accept button is the game's, and we
	// cannot see its clicks. If the game's handler does not hide the box then
	// nothing else would, so there is a net - but it is a TIMER, not a click.
	//
	// ⛔ IT USED TO DISMISS ON "A CLICK", AND THAT SILENTLY KILLED THE
	// FEATURE. The net fired on message type 0x0D, which the FIRST capture -
	// two occurrences, arriving with a button press - made look like a click.
	// The SECOND capture showed the truth: 36 of them in one continuous sweep
	// as the pointer moved. It is a mouse MOVE. So the notice was dismissed
	// within ~250ms of appearing, every time, by nothing more than the user
	// moving the mouse. Measured 2026-08-19:
	//     15:21:03.433 showed the game's own restart notice
	//     15:21:03.896 dismissed the restart notice on a click (safety net)
	// and the user reported, correctly, that no notice ever appeared.
	//
	// ⭐ MY OWN INSTRUMENT HAD ALREADY CORRECTED THE LABEL AND I KEPT THE
	// CONCLUSION DRAWN FROM THE FIRST READING. A second measurement that
	// contradicts the first is a RETRACTION, not extra confidence.
	//
	// A timeout cannot be wrong about what a message means. Ten seconds is
	// long enough to read one sentence and reach the button, and it still
	// guarantees the box can never become a trap.
	if (gSelNoticeShownMs != 0)
	{
		cIGZWin* notice = gfxDlg->GetChildWindowFromIDRecursive(kSelNoticeId);
		if (notice == nullptr || !notice->IsVisible())
		{
			gSelNoticeShownMs = 0;   // dismissed - by the game, or by us
		}
		else if (static_cast<int>(now - gSelNoticeShownMs) > 10000)
		{
			notice->HideWindow();
			gSelNoticeShownMs = 0;
			Logger::Get().WriteLine(LogLevel::Info,
				"UiSpike: SELECTOR retired the restart notice after 10s - the "
				"game's own Accept had not hidden it, so the net did. If this "
				"line appears every time, that button is not wired to a notice "
				"WE raised and the net is the only way it ever closes.");
		}
	}

	// ---- 1. the readout line (#192 behaviour, unchanged) ----------------
	char l1[96];
	if (gReadoutW > 0 && gReadoutH > 0)
	{
		_snprintf_s(l1, sizeof(l1), _TRUNCATE, "%dx%d @ %.2fx %s",
			gReadoutW, gReadoutH, settings.spikeScaleFactor,
			settings.spikeAutoScale ? "auto" : "manual");
	}
	else
	{
		// Honest rather than blank-but-wrong: only claim a render size we
		// were actually handed.
		_snprintf_s(l1, sizeof(l1), _TRUNCATE, "res ? @ %.2fx %s",
			settings.spikeScaleFactor,
			settings.spikeAutoScale ? "auto" : "manual");
	}
	SelSetCaption(gfxDlg, kSelReadoutId, l1);
	SelSetCaption(gfxDlg, kSelLabelId, "UI Scale (applies on restart)");

	// ---- 1b. HIDE THE STOCK RESOLUTION ROWS WHEN THEY DO NOTHING --------
	// User-raised: with dgVoodoo overriding the resolution, those four rows
	// are inert - the wrapper renders at the monitor's mode and the game's
	// WindowWidth/Height are ignored. Worse, every value they offer (800x600
	// through 1600x1200) is below the 1440x1080 the smallest tier needs, so on
	// an install where they DO work, picking one silently drops the mod to
	// stock. A control that either does nothing or breaks the mod should not
	// be presented as a choice.
	//
	// CONDITIONAL, never unconditional: gReqResIgnored is the director's own
	// answer to "is the wrapper overriding", so a player running without it
	// keeps the stock list exactly as the game shipped it. Done once per
	// appearance - the rows do not come back while the dialog is open.
	if (justOpened)
	{
		gSelResRowsHidden = false;
		if (gReqResIgnored)
		{
			int hidden = 0;
			for (int k = 0; k < 4; k++)
			{
				cIGZWin* r = gfxDlg->GetChildWindowFromIDRecursive(kStockResRadios[k]);
				if (r && r->IsVisible()) { r->HideWindow(); hidden++; }
				cIGZWin* t = gfxDlg->GetChildWindowFromIDRecursive(kStockResLabels[k]);
				if (t && t->IsVisible()) { t->HideWindow(); hidden++; }
			}
			gSelResRowsHidden = hidden > 0;
			Logger::Get().WriteLine(LogLevel::Info,
				"UiSpike: SELRES hid %d node(s) of the stock resolution list - "
				"the wrapper renders at the monitor's mode, so those rows "
				"cannot change anything. %s",
				hidden,
				hidden == 8 ? "All four rows." :
				"FEWER THAN THE EXPECTED 8: the labels are re-identified in "
				"DATA, so a stale DialogStatic package would leave some "
				"sharing 0xca57da80 and unreachable - rebuild it.");
		}
	}

	// ---- 2. the radio: is the live resolution one of the stock four? ----
	// DERIVED every service, never tracked: ask the four stock radios what
	// they are rather than remembering what we last saw.
	{
		int mask = 0;
		bool anyStock = false;
		for (int k = 0; k < 4; k++)
		{
			cIGZWin* w =
				gfxDlg->GetChildWindowFromIDRecursive(kStockResRadios[k]);
			if (!w) { continue; }
			cIGZWinBtn* b = nullptr;
			if (w->QueryInterface(GZIID_cIGZWinBtn,
					reinterpret_cast<void**>(&b)) && b)
			{
				if (b->IsChecked()) { anyStock = true; mask |= (1 << k); }
				b->Release();
			}
		}
		cIGZWin* w = gfxDlg->GetChildWindowFromIDRecursive(kSelRadioId);
		bool oursChecked = false;
		if (w)
		{
			cIGZWinBtn* b = nullptr;
			if (w->QueryInterface(GZIID_cIGZWinBtn,
					reinterpret_cast<void**>(&b)) && b)
			{
				oursChecked = b->IsChecked();
				if (oursChecked) { mask |= (1 << 4); }
				// ⚠ ONLY SEEDED ON OPEN. Forcing it every service would make
				// the control unclickable: the player checks it, 250ms later
				// we overwrite it from the stock radios, and the click looks
				// ignored. On open we state the truth; after that the player
				// owns it - and the trace below records what their click did.
				if (justOpened)
				{
					const bool want = !anyStock;
					if (oursChecked != want)
					{
						b->SetChecked(want);
						oursChecked = want;
						mask = (mask & 0x0F) | (want ? (1 << 4) : 0);
					}
				}
				b->Release();
			}
		}
		// ---- MUTUAL EXCLUSION, ENFORCED BY US -------------------------
		// MEASURED 2026-08-19: the engine DOES toggle our injected
		// radiocheck button when it is clicked (mask went 0x02 -> 0x12 on the
		// user's click), so the choice is readable directly - no click
		// detection needed, which matters because Accept clicks provably
		// never reach us. But the engine does NOT group ours with the stock
		// four: the same trace caught 1024x768 AND ours lit simultaneously
		// (mask 0x12). Radio buttons that can both be on are not radio
		// buttons, so the grouping is ours to enforce.
		//
		// The rule is by TRANSITION, not by state: whichever one just turned
		// ON wins, and the other side is cleared. Deciding from state alone
		// cannot tell which the user actually clicked.
		const bool oursNow = oursChecked;
		const int  stockNow = mask & 0x0F;
		if (oursNow && !gSelOursWas && stockNow != 0)
		{
			// The player just chose OUR resolution: clear the stock four.
			//
			// ⭐ THIS IS ALSO HOW THE CHOICE SURVIVES ACCEPT. The game writes
			// SC4GraphicsOptions.ini from ITS OWN radio state, and we cannot
			// see the Accept click to intervene. With no stock resolution
			// selected there is nothing for it to write, so the custom
			// WindowWidth/Height already in the file simply stays - which is
			// exactly what "keep my resolution" means.
			for (int k = 0; k < 4; k++)
			{
				cIGZWin* w2 =
					gfxDlg->GetChildWindowFromIDRecursive(kStockResRadios[k]);
				if (!w2) { continue; }
				cIGZWinBtn* b2 = nullptr;
				if (w2->QueryInterface(GZIID_cIGZWinBtn,
						reinterpret_cast<void**>(&b2)) && b2)
				{
					if (b2->IsChecked()) { b2->SetChecked(false); }
					b2->Release();
				}
			}
			mask &= ~0x0F;
			Logger::Get().WriteLine(LogLevel::Info,
				"UiSpike: SELRADIO custom resolution re-selected - cleared the "
				"stock resolution radios so the game has nothing to write over "
				"%dx%d on Accept.", gReadoutW, gReadoutH);
		}
		else if (stockNow != 0 && gSelStockWas == 0 && oursNow)
		{
			// A stock resolution just won: ours must go dark, or two radios
			// claim the same choice.
			cIGZWin* w2 = gfxDlg->GetChildWindowFromIDRecursive(kSelRadioId);
			if (w2)
			{
				cIGZWinBtn* b2 = nullptr;
				if (w2->QueryInterface(GZIID_cIGZWinBtn,
						reinterpret_cast<void**>(&b2)) && b2)
				{
					b2->SetChecked(false);
					b2->Release();
				}
			}
			mask &= ~(1 << 4);
			Logger::Get().WriteLine(LogLevel::Info,
				"UiSpike: SELRADIO a stock resolution was chosen - our custom "
				"radio cleared.");
		}
		gSelOursWas = (mask & (1 << 4)) != 0;
		gSelStockWas = mask & 0x0F;

		// SELRADIO: one line per CHANGE, never per service.
		if (mask != gSelRadioState && gSelRadioLogs < 30)
		{
			gSelRadioLogs++;
			gSelRadioState = mask;
			Logger::Get().WriteLine(LogLevel::Info,
				"UiSpike: SELRADIO stock[800x600=%d 1024=%d 1280=%d 1600=%d] "
				"ours=%d (mask 0x%02X). If `ours` flips to 1 after a click we "
				"did not make, the engine toggles injected radiocheck buttons "
				"and the custom-resolution choice is readable directly.",
				(mask >> 0) & 1, (mask >> 1) & 1, (mask >> 2) & 1,
				(mask >> 3) & 1, (mask >> 4) & 1, mask);
		}
	}

	// ---- 3. the combo IS the readout ------------------------------------
	// On open: REBUILD the list, then select the live row. After that the
	// combo owns the value - re-pushing every service would fight the
	// player's own selection.
	//
	// THE LIST IS BUILT AT RUNTIME because both facts it shows are runtime
	// facts. Whether a tier is usable depends on the resolution, which no .UI
	// can know; and the ACTIVE row carries the live resolution so the closed
	// control reads "1.5x @ 2400x1600" - the readout line this row used to
	// hold before the combo took its place. A row the screen cannot carry
	// says what it would need, and selecting it is REFUSED, so the control
	// can never promise a tier that would silently fall back to stock at the
	// next launch. The rule is ScaleTier::Fits, the same predicate the boot
	// path uses; a second copy of 880/558 here would be a second rule.
	cIGZWin* comboWin = gfxDlg->GetChildWindowFromIDRecursive(kSelComboId);
	if (comboWin)
	{
		cIGZWinCombo* c = nullptr;
		if (comboWin->QueryInterface(GZIID_cIGZWinCombo,
				reinterpret_cast<void**>(&c)) && c)
		{
			if (justOpened)
			{
				// The PENDING choice wins if there is one - see gSelPendingRow.
				const int live = (gSelPendingRow >= 0)
					? gSelPendingRow : SelRowFromSettings(settings);
				for (int k = 0; k < kSelCount; k++)
				{
					gSelUsable[k] = SelRowUsable(k);
				}
				c->RemoveAllStrings();
				for (int k = 0; k < kSelCount; k++)
				{
					char row[80];
					if (!gSelUsable[k])
					{
						// Say WHAT IT NEEDS, not just "no". A control that
						// refuses without explaining itself is a bug report.
						int mw = 0, mh = 0;
						SelMinimumFor(k, &mw, &mh);
						_snprintf_s(row, sizeof(row), _TRUNCATE,
							"%s - needs %dx%d", kSelLabels[k], mw, mh);
					}
					else if (k == live && k == gSelPendingRow)
					{
						// Chosen this session: say that it is queued, so the
						// player can tell a pending choice from the live one.
						_snprintf_s(row, sizeof(row), _TRUNCATE,
							"%s - on restart", kSelLabels[k]);
					}
					else if (k == live && gReadoutW > 0 && gReadoutH > 0)
					{
						// The ACTIVE row carries the resolution, so the closed
						// combo shows the whole readout line.
						_snprintf_s(row, sizeof(row), _TRUNCATE, "%s @ %dx%d",
							kSelLabels[k], gReadoutW, gReadoutH);
					}
					else
					{
						_snprintf_s(row, sizeof(row), _TRUNCATE, "%s",
							kSelLabels[k]);
					}
					cRZBaseString rs(row);
					c->InsertString(rs, k);
				}
				if (live >= 0) { c->SetSelection(live, false); }
				gSelPushed = live;
				gSelCommitted = live;
			}
			else
			{
				const int row = c->GetSelection();
				if (row >= 0 && row < kSelCount && row != gSelPushed)
				{
					if (!gSelUsable[row])
					{
						// REFUSED -> BOUNCE TO AUTO (user direction,
						// 2026-08-19). Auto is the only row that always fits
						// by construction, and it answers what the player was
						// reaching for: "give me the biggest scale this
						// screen can take". Snapping back to the PREVIOUS row
						// would have been the timid choice and leaves someone
						// who just moved to a smaller screen stuck on a tier
						// that no longer fits.
						//
						// It COMMITS Auto too, deliberately. A bounce that
						// only moved the highlight would leave the ini
						// holding the old value while the closed control read
						// "Auto" - the control would be lying, which is the
						// one thing it must never do.
						int bounceMinW = 0, bounceMinH = 0;
						SelMinimumFor(row, &bounceMinW, &bounceMinH);
						Logger::Get().WriteLine(LogLevel::Info,
							"UiSpike: SELECTOR refused row %d (%s) - %dx%d "
							"cannot carry it (needs %dx%d). Bounced to Auto.",
							row, kSelLabels[row], gReadoutW, gReadoutH,
							bounceMinW, bounceMinH);
						c->SetSelection(0, false);
						gSelPushed = 0;
						gSelCommitted = 0;
						SelCommit(0);
						ShowRestartNotice(gfxDlg);
					}
					else
					{
						// COMMIT ON CHANGE, not on Accept.
						//
						// ⭐ MEASURED, NOT CHOSEN (2026-08-19). The first
						// build staged the choice and committed when a
						// message carrying the Accept button's id arrived.
						// The SELMSG instrument proved no such message
						// exists: across 120 captured messages every one was
						// either a mouse coordinate pair (type 0x0D /
						// 0xA2BF8AD4) or one repeated WINDOW POINTER
						// (0xA2BF8ACD/CE/CF) - not a single control id in any
						// data slot. That commit path could never have fired,
						// and only the instrument could have said so.
						//
						// Committing on change is safe HERE specifically
						// because the tier applies at the next launch: the
						// write changes nothing about the running game, and
						// picking another row overwrites it.
						gSelPushed = row;
						gSelCommitted = row;
						// ⛔ SHOWN ON THE CHANGE, AND THAT IS NOT THE
						// PREFERRED TIMING - it is the only one left.
						// The user asked for it on Accept, twice, and
						// Accept has now been eliminated by two
						// independent measurements:
						//   1. MESSAGES - 36 traced with the dialog
						//      open, none touching the Accept rect, and
						//      none arriving at all at the moment it was
						//      pressed. The winproc does not see it.
						//   2. SIDE EFFECT - the game does NOT rewrite
						//      SC4GraphicsOptions.ini on Accept. Three
						//      Accepts in one session, three
						//      "NO write ... was ever seen" lines.
						// The detector below stays armed anyway: it costs
						// one file stat, and if a future build of the
						// game (or another setting changed in the same
						// visit) does move that file, the log will say
						// so and the timing can move with it.
						SelCommit(row);
						ShowRestartNotice(gfxDlg);
					}
				}
			}
			c->Release();
		}
	}

	if (gSelLogs < 2)
	{
		gSelLogs++;
		Logger::Get().WriteLine(LogLevel::Info,
			"UiSpike: SELECTOR serviced Graphic Options - readout \"%s\", "
			"combo %s. Absent means the DATA half is missing for this tier: "
			"rebuild and deploy DialogStatic.", l1,
			comboWin ? "present" : "ABSENT");
	}
}
