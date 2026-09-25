#pragma once
#include <cstdint>

#include "cIGZWin.h"
#include "Logger.h"
#include "RoundHalfUp.h"

class cIGZBuffer;
class UiSpike;

// What UiSpike.cpp shares with the files split out of it (audit B11,
// 2026-09-25). Each seam was measured by compiling the halves apart, and
// this header holds exactly what the compiler asked for:
//   UiSpikeSelector.cpp  gReadoutW, gReadoutH, SafeAbsRect
//   UiSpikeRegion.cpp    ChildSnapshot, gGaugeEpoch, kGZWin_RegionScreen
//   UiSpikeMinimap.cpp   ParentIdOf, SafeBufProbe; and UiSpike.cpp needs 13
//                        names from it: SurfRetry, kSurfMaxAttempts and the
//                        minimap block below
//   UiSpikeFlyouts.cpp   LiveTuneIniPath, gChartProbe, gChartScale,
//                        ScaleRound, kFgMax, SafeAbsRect, SafeBufProbe,
//                        gGaugeEpoch, ChildSnapshot; and UiSpike.cpp needs
//                        the 23 names of the flyout block below
// Functions and variables are defined in UiSpike.cpp, except the minimap and
// flyout blocks, which their own files define. Constants, ScaleRound and the
// ChildSnapshot and SurfRetry types are inline here. Anything added widens a
// seam, so add only what a split needs.
namespace UiSpikeInternal
{
	// #192: the render size the director measured, for the resolution
	// readout and the selector's resolution rows.
	extern int32_t gReadoutW;
	extern int32_t gReadoutH;

	// SEH-guarded walk of a window's ABSOLUTE top-left (sum of GetL/GetT up
	// the parent chain) plus its own w/h. False on a fault.
	bool SafeAbsRect(void* winPtr, int* outL, int* outT, int* outW, int* outH);

	// SEH-guarded identity check of a candidate cIGZBuffer (defined in
	// UiSpike.cpp; the MMBUF log calls it too).
	bool SafeBufProbe(void* bufPtr, int* outQi, int* outW, int* outH, int* outBpp);

	// The immediate parent's id, 0 if none (defined in UiSpike.cpp).
	uint32_t ParentIdOf(cIGZWin* w);

	// Bumped by Disarm: per-city latches compare their own epoch to it.
	extern int gGaugeEpoch;

	// Boot-dump proven (region screen recon): the region UI host is
	// 0xEA659793 (13 children: legend, region panel, button clusters,
	// compass, hidden flyouts). 0x2AAB8CC1 exists there but is empty+hidden.
	const uint32_t kGZWin_RegionScreen = 0xEA659793;

	// v2.25.0 (task #53, code-created audit 2026-07-29): 96 was 79% consumed
	// by ONE popup (the ordinance list family) while four installed ordinance
	// mods keep adding rows to it - and an overflow is SILENT, making the
	// verify pass read the dropped children as dead. 256 gives ~3.3x the
	// worst measured consumer; ChildSnapshot::Callback now logs (once) if it
	// is ever hit anyway.
	const int kMaxChildrenPerLevel = 256;

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

	// ---- UiSpikeMinimap.cpp: what UiSpike.cpp calls and resets ----------
	// Per-city state: Disarm resets the latch, the budget and the MMBUF
	// sample count (the #92 second-city law); ScaleAllPanels logs the three
	// #126 draw-hook counters.
	extern cIGZWin* lastMinimapSurfResize;   // HUD dock minimap surface latch
	extern SurfRetry gMinimapRetry;
	extern int gMmBufLogged;
	extern int gMmStretches;   // EXECUTED counter (law 47)
	extern int gMmEntries;     // thunk CALLED counter (see MmDrawThunk)
	extern int gMmHooked;      // INSTALLED counter

	// The synchronous bake and the surface carry-over (the DVMAP and UDMAP
	// blocks in ScalePanelsUnder use them as the MINIMAP block does), the
	// MMBUF log and the #126 draw hook.
	void DriveMiniMapBake(void* mm, const char* who);
	bool CaptureSurface(void* surf, int* outW, int* outH);
	void RestoreSurfaceBilinear(cIGZBuffer* pBuf, int srcW, int srcH, int n);
	void LogMinimapBuffer(const char* when, cIGZWin* pMM);
	bool HookMiniMapDraw(cIGZWin* win, const char* who);

	// ---- UiSpike.cpp -> UiSpikeFlyouts.cpp ----------------------------------
	// The ini beside this DLL, for the live-tune re-read.
	const char* LiveTuneIniPath();
	// #57's two chart switches, which ScaleGodFlyouts's live-tune table sets.
	extern int gChartProbe;
	extern int gChartScale;

	// Rounding-correct scaling. Truncation happens to be exact at f=2.0
	// (bit-identical results) but drifts at non-integer factors (1.5x).
	//
	// HALF-UP, NOT HALF-AWAY-FROM-ZERO. THIS IS #162, AND THE FIX WAS
	// ALREADY WRITTEN AT THE TOP OF UiSpike.cpp - IT JUST NEVER REACHED HERE.
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
	// RoundHalfUp (RoundHalfUp.h) is the art pipeline's
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

	// v2.25.0 (task #53): 6 was FULL (one slot wasted on the tooltip class),
	// so any further class the ready-gate met was silently unguarded. 12.
	const int kFgMax = 12;

	// ---- UiSpikeFlyouts.cpp: what UiSpike.cpp reads, calls and resets -------
	extern float gTierF;           // the hook-visible tier mirror (SetTierMirror)
	extern int gScaleAbbPanel;     // [Flyout] ScaleGodPanelABB
	extern int gReadyCount;        // the flash guard's ready list
	extern void* gFgWaitRoot[4];
	extern int gFgWaitN[4];
	extern void* healDoneStrip;    // ADVHEAL
	extern int healPhase;
	typedef uintptr_t(__fastcall* FgThunkFn)(void*, void*);
	extern FgThunkFn const kFgThunks[kFgMax];
	bool IsOnScreen(cIGZWin* w, int guard = 24);
	void NoteFlashCandidate(cIGZWin* win, uint32_t id, int n, const char* tag,
		unsigned int msSinceArm);
	extern UiSpike* gSpikeSelf;
	extern void* gSubLastStrip;
	extern void* gDisLastStrip;
	extern bool gDisDockValid;
	extern cIGZWin* gDisChromeHealed;
	extern cIGZWin* gDisDockLogged;
	extern int gBornQN;
	void EnsureBufferClassBltHook();
	extern int gVisSeenN;
	extern int gMDockLoggedN;
	extern int gMayorRebirthLogs;
	void FindIdsRecursive(cIGZWin* root, const uint32_t* ids, int n,
		cIGZWin** out);
	void CollectIdsUnder(cIGZWin* root, const uint32_t* ids, int n,
		cIGZWin* (*out)[4], int* counts);
}
