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
#include "IniCache.h"     // audit B8: every read of our ini, one parse
#include "RoundHalfUp.h"  // audit B9: the one rounding rule (law 89)
#include "ExeBase.h"     // audit B7: the exe base, read once
#include "UiSpikeInternal.h"  // audit B11: what the split files share
#include "UiSpikeIds.h"       // audit B11: the window-id tables
#include "SpinProbe.h"    // #107: per-launch outcome recorder (was Budget opened?)

#include "cIGZWin.h"
#include "cIGZString.h"
#include "cIGZWinText.h"
#include "cIGZWinBtn.h"     // in-game scale selector: radio state
#include "cIGZWinCombo.h"   //   ... the tier picker
#include "cIGZWinGen.h"     //   ... SetWinProc/GetWinProc on the dialog
#include "cIGZWinProc.h"    //   ... the chained click handler
#include "cIGZWinMessageFilter.h"  // ... per-BUTTON message filter
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
#include <algorithm>   // std::min (disaster rebuild NN sampling clamps)
#include <cstdio>      // _snprintf_s (the DVLEG legend read-back line)
#include <string>      // the wrapped caption we build
#include <set>         // #188 SMALLWIN per-epoch dedupe
#include <Windows.h>   // SEH guard for probing hook return values
#include <psapi.h>     // v4.10.0: PROCESS_MEMORY_COUNTERS_EX for the heartbeat (K32 export, no new lib)

// The live-tune re-read below used a HARDCODED absolute path to this dev
// box's Plugins folder. On any other machine that read silently returns
// nothing, so every [Disaster] value falls back to its COMPILED default -
// which were then the pre-fix values (RingDY -27, DockY 130, LayerFix 1,
// RingDX 0, DockX 6): item 2 lined up with the tornado button instead of
// item 4, and the circle painted over the strip junction. The ini now
// resolves beside this DLL (both installed into Plugins), AND the compiled
// defaults themselves are the USER-ACCEPTED stock-parity set (REGRESSION.md
// v2.11.25, accepted 2026-07-28) - so a fresh install with NO [Disaster]
// section ships correct too. Ini values still override for live tuning.
extern "C" IMAGE_DOS_HEADER __ImageBase;

// ---- SHARED WITH THE SPLIT FILES (UiSpikeInternal.h, audit B11) -------------
namespace UiSpikeInternal
{
	int32_t gReadoutW = 0, gReadoutH = 0;   // #192, set by the director
	int gGaugeEpoch = 0;   // bumped by Disarm; see the epoch note below

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

	// The immediate parent's id, for the log line that the MINIMAP comment
	// has claimed since v2.22.3 was already printed - it was not.
	uint32_t ParentIdOf(cIGZWin* w)
	{
		cIGZWin* p = w ? w->GetParentWin() : nullptr;
		return (p && p != w) ? p->GetID() : 0u;
	}
}
using UiSpikeInternal::gReadoutW;
using UiSpikeInternal::gReadoutH;
using UiSpikeInternal::SafeAbsRect;
using UiSpikeInternal::gGaugeEpoch;
using UiSpikeInternal::ChildSnapshot;
using UiSpikeInternal::kMaxChildrenPerLevel;
using UiSpikeInternal::kGZWin_RegionScreen;
using UiSpikeInternal::SafeBufProbe;
using UiSpikeInternal::ParentIdOf;
using UiSpikeInternal::SurfRetry;
using UiSpikeInternal::kSurfMaxAttempts;
using UiSpikeInternal::lastMinimapSurfResize;
using UiSpikeInternal::gMinimapRetry;
using UiSpikeInternal::gMmBufLogged;
using UiSpikeInternal::gMmStretches;
using UiSpikeInternal::gMmEntries;
using UiSpikeInternal::gMmHooked;
using UiSpikeInternal::DriveMiniMapBake;
using UiSpikeInternal::CaptureSurface;
using UiSpikeInternal::RestoreSurfaceBilinear;
using UiSpikeInternal::LogMinimapBuffer;
using UiSpikeInternal::HookMiniMapDraw;
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
using UiSpikeInternal::IsOnScreen;
using UiSpikeInternal::NoteFlashCandidate;
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
using UiSpikeInternal::FindIdsRecursive;
using UiSpikeInternal::CollectIdsUnder;

namespace UiSpikeInternal
{
	// Resolved once; the DLL cannot move while loaded.
	const char* LiveTuneIniPath()
	{
		static char s_path[MAX_PATH] = {};
		if (!s_path[0])
		{
			ScaleTier::GetOurFilePathA("SC4UIScale.ini", s_path, MAX_PATH);
		}
		return s_path;
	}
}

// The flyout draw hooks - the DRAW HOOK slot thunks, the tier mirror
// gTierF, the disaster flyout's blit hooks, the flash guard and the mouse
// thunks - are in UiSpikeFlyouts.cpp (audit B11).
namespace
{
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
	// gGaugeEpoch: UiSpikeInternal (top of this file, audit B11).

	// #93: one-shot latch for the UDVAR sighting line. Cleared in Disarm so a
	// SECOND city re-reports (second-city law - a latch that survives a city
	// change is how #92 hid, and this one exists precisely to catch a rare
	// event we have never observed).
	bool    gUdVarSeen = false;

	// #57: CHARTGEO one-shot counter (4 lines max, read-only probe).
	int     gChartGeoLog = 0;
}

namespace UiSpikeInternal
{
	// ---- #57 PHASE 1: THE REPAINT PROOF. ini [Flyout] ChartProbe, default 0
	// THIS DELIBERATELY DEFACES THE CHART: it floods the plot area opaque
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
	// Proving it with an absurd rect at +0xE0 is worthless: that is the
	//    write that already failed, so it cannot separate "no repaint" from
	//    "field ignored". A colour CAN.
	int     gChartProbe = 0;
}

namespace
{
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
	// Rebased 0xAB4D08 = cSC4LineGraph's main vtable, the type-1 chart and the
	// ONLY chart type that has a legend column (the bar builder, type 2, makes
	// no legend items; its stock right margin is W-2 at 0x76D837).
	uintptr_t gChartLineMainVt = 0;
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
			// v4.10.1: ONLY THE LINE CHART HAS A LEGEND TO CLEAR. This thunk
			// also sits on the type-2 (bar) cIGZGraph vtable, and taking the
			// legend budget there pulled every bar chart's right edge in by
			// the width of a legend it does not have - 244 px at 2x.
			// USER-CONFIRMED ON SCREEN 2026-09-23: Graphs -> RCI Demand showed
			// the bars ending under the line chart's plot edge with the right
			// quarter of the panel empty. Bars take the proportional margin.
			uintptr_t chartVt = 0;
			CodePatches::SafeReadPtr(chart, &chartVt);
			const bool hasLegend = (chartVt == gChartLineMainVt);
			const int32_t budgetRM = hasLegend
				? CodePatches::GraphLegendPlotRightMargin(f) : 0;
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
					"(%d,%d,%d,%d) in %dx%d sane=%d vt=%08X %s budgetRM=%d "
					"- born correct, no stock frame", l, t, rr, b,
					r[0], r[1], r[2], r[3], winW, winH, sane ? 1 : 0,
					static_cast<uint32_t>(chartVt),
					hasLegend ? "line" : "no-legend", budgetRM);
				// LEGENDOBJ: the legend entries live in a linked list at
				// chart+0x228 (sub_9B5ADE walks it, calling each node's
				// [+8]->vt[1] to draw). The "invisible barrier" pushing
				// the legend text right lives in these objects - dump
				// their first dwords so the next fix is measured, not
				// guessed.
				uintptr_t headRaw = 0;   // v4.10.0: guarded read of a measured offset
				CodePatches::SafeReadPtr(chart + 0x228, &headRaw);
				uint32_t* head = reinterpret_cast<uint32_t*>(headRaw);
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
		const uintptr_t delta = ExeBase() - 0x400000;
		gChartStoreReal = 0x9B1F1D + delta;
		gChartLineMainVt = 0xAB4D08 + delta;
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
}

namespace UiSpikeInternal
{
	// #57: scale the chart's frozen interior fields. ini [Flyout] ChartScale.
	// Three earlier levers failed on screen: re-arm the sentinel (v2.50.0),
	// scale the tick font (v2.51.0), write the rect (v2.52.0). Their
	// measurements: REGRESSION.md [CC-01].
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
}

namespace
{
	// The chart object we have already scaled - the re-arm must happen ONCE
	// per object, or the sweep re-lays the chart 4x/sec forever (the
	// "incremental panel ... 1 windows scaled" churn trap, v2.25.1).
	// Cleared in Disarm: a second city gets a new chart at a possibly REUSED
	// address, which is exactly how #92 hid.
	cIGZWin* gChartScaled = nullptr;

	// The sub-flyout ring and geometry, gScaleAbbPanel and the flash guard's
	// data: UiSpikeFlyouts.cpp (audit B11).

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
	// (The HUD dock minimap's latch, lastMinimapSurfResize, lives with its
	// block in UiSpikeMinimap.cpp; audit B11.)
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
	// The v2.69.5 dock-seed and the v2.69.6/v2.70.0 per-sweep heal were
	// deleted in v2.71.4, once the x8 bake patch (#121) let the game bake a
	// real base at zoom -3 (REGRESSION.md [CC-02]). What remains is the clamp
	// below; since v2.72.0 it is the sizing policy at every tier (the Data
	// Views block in ScalePanelsUnder).
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
	// The #126 minimap draw hook counters (gMmStretches, gMmEntries,
	// gMmHooked) live with the hook in UiSpikeMinimap.cpp (audit B11).
	// ScaleAllPanels logs them.

	// SurfRetry and kSurfMaxAttempts, with the BOUNDED RETRY note (v2.41.0,
	// task #89): UiSpikeInternal.h. The minimap's budget, gMinimapRetry, is
	// in UiSpikeMinimap.cpp (audit B11).
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
	// healDoneStrip and healPhase (ADVHEAL), and the CAA and position
	// probes: UiSpikeFlyouts.cpp (audit B11).

	// SafeAbsRect: UiSpikeInternal (top of this file), shared with the
	// selector (audit B11).

	// SafeBufProbe: UiSpikeInternal (top of this file), shared with the
	// minimap file (audit B11).

	// The SURFACE CARRY-OVER (CaptureSurface, RestoreSurfaceBilinear) and
	// DriveMiniMapBake: UiSpikeMinimap.cpp (audit B11). The DVMAP and UDMAP
	// blocks in ScalePanelsUnder call them.

	// The BLT hooks, the flash guard and the slot, mouse and hit-test
	// thunks: UiSpikeFlyouts.cpp (audit B11).
}

namespace
{
	const int kMaxDepth = 8;
	const int kMaxWindows = 1500;
	// kMaxChildrenPerLevel: UiSpikeInternal.h (audit B11).
	// The window-id tables and their Is...Id predicates: UiSpikeIds.h (audit
	// B11). IsGodPanelId, IsNeverScaleId, ScaleRound, CityHudOriginX and
	// StillChildOf stay here: each reads state or helpers of this file.

	inline bool IsGodPanelId(uint32_t id)
	{
		// 0xABB26B0E is ini-gated (default OFF) - see gScaleAbbPanel. Scaling and
		// docking it to (6,490) covers the minimap dock, and it did not fix the
		// founded-city god mode it was added for (0x0A78827A did).
		if (id == 0xABB26B0E && gScaleAbbPanel == 0)
		{
			return false;
		}
		return IdIn(kGodPanelIds, id);
	}

	// [Probe] ForceRuntimeScaleId - Build 1 (2026-08-24) dev repro lever for
	// register row #24. A nonzero id is EXCLUDED from kNeverScaleIds at every
	// consult site, putting that dialog back on the runtime-only scaling path
	// (the purple-GZWinText state). Side effect while set: the DLGLISTS
	// overlap census also stops listing that id - expected, dev-only.
	// Dev-ini-only, never shipped. PRIMED from SetTierMirror (the tier tail,
	// outside every hook) so the one-time ini read + log can never fire
	// inside a detour (review finding 5); the guard below is belt-and-braces
	// for any consult that could theoretically precede the mirror.
	inline uint32_t ForceRuntimeScaleId()
	{
		static bool s_read = false;
		static uint32_t s_id = 0;
		if (!s_read)
		{
			s_read = true;
			char buf[32] = {};
			IniCache::ReadStringA("Probe", "ForceRuntimeScaleId", "0",
				buf, sizeof(buf), LiveTuneIniPath());
			s_id = static_cast<uint32_t>(strtoul(buf, nullptr, 16));
			Logger::Get().WriteLine(LogLevel::Info,
				"UiSpike: ForceRuntimeScaleId resolved to 0x%08X (read from "
				"[Probe]; nonzero EXCLUDES that id from kNeverScaleIds at "
				"ALL consult sites - dev repro lever for #24. With the "
				"DialogStatic dat still ACTIVE this DOUBLE-SCALES the dialog "
				"to ~4x; quarantine the dat first.)", s_id);
		}
		return s_id;
	}

	inline bool IsNeverScaleId(uint32_t id)
	{
		if (id != 0 && id == ForceRuntimeScaleId()) { return false; }
		return IdIn(kNeverScaleIds, id);
	}

	// ScaleRound: UiSpikeInternal.h, shared with the flyout file (audit B11).

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
	// A live marker can be in SCREEN units (scaled with its subtree) or still
	// in DESIGN units (the subtree scale never reached it). Both were measured
	// with WarriorUI installed, and it is not a race that waiting fixes. The
	// marker's size cannot tell them apart reliably either. History
	// (v2.43.1-v2.47.0): REGRESSION.md [CC-12].
	//
	// The authoritative answer is not geometric at all: WE record every
	// window we scale. See UiSpike::MarkerIsDesignUnits (a PURE READ of
	// scaleMap - deliberately not Classify(), which mutates the tug-of-war
	// counter and could tombstone a window just for asking).

	// ChildSnapshot: UiSpikeInternal.h (audit B11, shared with the region file).

	// CRASH KILLER, one copy (audit B9): is `child` still in `parent`'s LIVE
	// child list? Mutating an earlier sibling can make the game destroy a
	// later one (reactive menu layouts during rapid switching), so a sweep
	// re-checks before touching the next snapshot entry. The check proves
	// the liveness of THIS pointer only, never of the rest of the snapshot
	// (v2.69.3 - see ScaleSubtree). Only [0, count) is read, so only count
	// needs clearing.
	bool StillChildOf(cIGZWin* parent, cIGZWin* child)
	{
		ChildSnapshot verify;
		verify.count = 0;
		parent->EnumChildren(GZIID_cIGZWin, ChildSnapshot::Callback, &verify);
		for (int j = 0; j < verify.count; j++)
		{
			if (verify.wins[j] == child) { return true; }
		}
		return false;
	}
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

// The sub-flyout born-scale detours, the first-level flyout open hook, the
// sub-flyout hook installers and the visibility trace: UiSpikeFlyouts.cpp
// (audit B11).

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
	// gap this closes, and it is the one the player's question needs:
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
	// resize after they are shown. So the thing the player watches resize is
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
		// the window the player watches resize; the four below are the panel
		// furniture that was already on screen when they clicked.
		{ 0x0423278F, 0, 0, 0, 0, false },
		{ 0xAA3AC000, 0, 0, 0, 0, false },
		{ 0xAA3AC001, 0, 0, 0, 0, false },
		{ 0xAA3AC002, 0, 0, 0, 0, false },
		{ 0xCA4C332D, 0, 0, 0, 0, false },
	};
	int       gBudgetTickLog = 0;
	// gMayorRebirthLogs (#194): UiSpikeFlyouts.cpp (audit B11).
	int       gArtSizedRefusals = 0;     // #197
	// gReadoutW/gReadoutH (#192, set by the director): UiSpikeInternal.
	bool      gBudgetTickAnnounced = false;
	int       gBudgetShowOpens = 0;
	bool      gShowHookInstalled = false;

	// GODSHOW / GODFIX (v4.0.9 follow-up, 2026-08-22): the god-mode DISASTER
	// flyout jumps for a split second on its first open. Instrument reading
	// from the repro session: ZERO 'FLYOPEN ... scaled at OPEN' lines while
	// the hook was armed - the disaster flyout opens through neither hooked
	// funnel, so its first frame was corrected by the sweep instead of being
	// born correct. tools\uimap\subflyout-builder.json names the family
	// positively: builder sub_7EAEB0 Sets the container id 0x8A6E61E0 and the
	// strip id 0x8A2CAD8B (REGRESSION.md's SUBHOOK lines 258x482 / 88x382 at
	// f=2 -> design 129x241 / 44x191). This block keys on THOSE ids only -
	// not the refuted whole-HUD scale-at-show scope (#50/#76) - and acts on
	// the hidden->visible transition, which the SHOWHOOK analysis proved is
	// pre-paint: SetFlag invalidates without painting, so geometry set here
	// is what the first frame draws. ScaleSubtree is idempotent via scaleMap,
	// so if the flyout ever arrives already scaled this is a measured no-op,
	// and the line still prints its verdict either way.
	struct GodFlyoutRoot { uint32_t id; int32_t w, h; const char* name; };
	const GodFlyoutRoot kGodFlyoutRoots[] = {
		{ 0x8A6E61E0, 129, 241, "disaster container" },
		{ 0x8A2CAD8B,  44, 191, "disaster strip"     },
	};
	int       gGodShowLog = 0;

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
		if (gEarlyDockPending && !gInEarlyDock && gSpikeSelf)
		{
			if (((++gEarlyDockCalls) & (kEarlyDockEvery - 1)) == 0)
			{
				gInEarlyDock = true;      // our own SetW/SetH re-enter SetFlag
				gSpikeSelf->EarlyDockTick();
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
			&& gSpikeSelf && gTierF > 1.01f)
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
					gSpikeSelf->ApplyPanelDocks(
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

		// GODSHOW/GODFIX - see kGodFlyoutRoots above. Same transition test as
		// BUDGETSHOW: [this+0xC8] & 1 is still 0 here, i.e. genuinely hidden
		// -> visible, and scaling now lands BEFORE the first paint.
		if (flag == 1u && value && self && !gInShowHook && !gInEarlyDock
			&& gSpikeSelf && gTierF > 1.01f && gGodShowLog < 16)
		{
			const uint32_t bitsG =
				*reinterpret_cast<const uint32_t*>(
					reinterpret_cast<const char*>(self) + 0xC8);
			if ((bitsG & 1u) == 0u)
			{
				cIGZWin* wg = static_cast<cIGZWin*>(self);
				const uint32_t gid = wg->GetID();
				for (const GodFlyoutRoot& gr : kGodFlyoutRoots)
				{
					if (gr.id != gid) { continue; }
					gGodShowLog++;
					const int32_t ew = RoundHalfUp(gr.w * gTierF);
					const int32_t eh = RoundHalfUp(gr.h * gTierF);
					const int32_t lw = wg->GetW(), lh = wg->GetH();
					gInShowHook = true;
					Logger::Get().WriteLine(LogLevel::Info,
						"UiSpike: GODSHOW #%d 0x%08X (%s) becoming visible "
						"%dx%d, expect %dx%d, design %dx%d, %d children -> %s.",
						gGodShowLog, gid, gr.name, lw, lh, ew, eh,
						gr.w, gr.h, wg->GetChildCount(),
						(lw == ew && lh == eh) ? "BORN CORRECT"
							: (lw == gr.w && lh == gr.h)
								? "STILL 1x - scaling NOW pre-paint"
								: "NEITHER design nor expected - read the numbers");
					gSpikeSelf->ScaleOnShow(wg);
					const int32_t nw = wg->GetW(), nh = wg->GetH();
					if (nw != lw || nh != lh)
					{
						Logger::Get().WriteLine(LogLevel::Info,
							"UiSpike: GODFIX 0x%08X (%s) %dx%d -> %dx%d at "
							"SHOW, before first paint - the funnel never saw "
							"this flyout, so this is its born-correct lever.",
							gid, gr.name, lw, lh, nw, nh);
					}
					else if (lw != ew || lh != eh)
					{
						// ScaleOnShow scaled nothing AND the size is not the
						// expected one - say so loudly instead of leaving a
						// silent no-op that reads as a fix.
						Logger::Get().WriteLine(LogLevel::Info,
							"UiSpike: GODFIX 0x%08X (%s) UNCHANGED at %dx%d "
							"- scaleMap considered it done; if the jump ever "
							"reproduces, this line is the counter-evidence.",
							gid, gr.name, lw, lh);
					}
					gInShowHook = false;
					break;
				}
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
				if (gShowHookMode >= 2 && gSpikeSelf)
				{
					gSpikeSelf->ScaleOnShow(w);
				}
				gInShowHook = false;
			}
		}
		return gOrigSetFlag(self, edx, flag, value);
	}
}

void UiSpike::InstallShowHook()
{
	gSpikeSelf = this;
	gShowHookMode = settings.spikeShowHook;
	gEarlyDockMode = settings.spikeEarlyDock;
	// v2.41.17: the trampoline now serves TWO consumers, so it must install if
	// EITHER wants it. ShowHook itself ships at 0 (refuted for the city HUD),
	// and EARLYDOCK would silently never run if this still keyed off it alone.
	if (gShowHookInstalled || (gShowHookMode <= 0 && gEarlyDockMode <= 0)) { return; }
	if (gTierF <= 1.01f) { return; }   // stock tier stays inert

	const uintptr_t base = ExeBase();
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
	// a tick later - the player saw exactly that ("it jumps when you open the city
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
	cityLoads++;   // heartbeat: city arms this session (counted before any early-out)
	if (!settings.spikeDumpTree && settings.spikeScaleWindowId == 0 && !settings.spikeScaleAll)
	{
		return;
	}
	armed = true;
	fireAtMs = fireAtTickMs;
	// v2.32.0: install the show hook here, not in the ctor - by PostCityInit
	// the tier is decided and gTierF is live, so a stock tier stays inert.
	InstallShowHook();
	InstallSubFlyoutBornScale();
	InstallFlyoutOpenHook();
	// 2026-08-23 (user-reported: disaster flyout "isn't born correctly,
	// jumps and the circle tail connects to the stripe incorrectly" - but
	// ONLY on the session's first open). EnsureBufferClassBltHook() patches
	// a FIXED vtable address (kBufClassVt = 0x00AC1400, valid the moment
	// the exe is mapped - no live container needed), but it was only ever
	// called from inside a container's OWN birth handler - one paint-frame
	// too late for that container's very first Plot(). The game's own
	// UNHOOKED Blt draws that first frame (wrong ring size/position
	// relative to the strip - exactly "the tail connects incorrectly"),
	// and DISHEAL's forced redraw corrects it a moment later - exactly the
	// visible "jump", and exactly why it only happens once per session
	// (every subsequent open already has the hook active from its very
	// first frame). Calling it here, at the same point every other
	// sub-flyout hook gets installed and well before any player has had a
	// chance to open a single flyout, closes the race instead of racing to
	// catch up after it: idempotent, touches no container-specific state,
	// so this is purely additive to the existing birth-time call.
	EnsureBufferClassBltHook();
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
	// THE HALF THAT WAS MISSING WHEN v2.41.15 CRASHED. Scaling the dock
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
	// exactly the player's headline repro: the My Sims STRIP windows hook ONCE
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
	// The MDOCK log latch and MDockShouldLog: UiSpikeFlyouts.cpp (audit B11).
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
	// opener - so it fires whenever the player opens a tool flyout, and that hook
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
	// (v4.0.41) the bar-tile cache and its Disarm resets died with the
	// legacy disaster path.
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

// v4.10.0 - RESOURCE HEARTBEAT. One Info line every 5 minutes (and one
// at the first tick, the baseline) so any tester's log carries a slope:
// private bytes, handles, GDI/USER objects, address space left, our two maps,
// the fixed-table fill levels and the city/epoch counters. ~2 KB per hour.
// Nothing here calls into the game. Memory counters come from kernel32's
// K32GetProcessMemoryInfo (resolved once), so no new import library.
void UiSpike::HeartbeatTick(unsigned int nowTickMs)
{
	const unsigned int kPeriodMs = 5u * 60u * 1000u;
	if (lastHeartbeatMs != 0
		&& static_cast<int>(nowTickMs - lastHeartbeatMs) < static_cast<int>(kPeriodMs))
	{
		return;
	}
	if (firstHeartbeatMs == 0) { firstHeartbeatMs = nowTickMs ? nowTickMs : 1u; }
	lastHeartbeatMs = nowTickMs ? nowTickMs : 1u;
	heartbeatSeq++;

	typedef BOOL (WINAPI* PmiFn)(HANDLE, PROCESS_MEMORY_COUNTERS*, DWORD);
	static PmiFn pmi = nullptr;
	static bool pmiTried = false;
	if (!pmiTried)
	{
		pmiTried = true;
		HMODULE k32 = GetModuleHandleW(L"kernel32.dll");
		if (k32)
		{
			pmi = reinterpret_cast<PmiFn>(GetProcAddress(k32, "K32GetProcessMemoryInfo"));
		}
	}
	PROCESS_MEMORY_COUNTERS_EX pm = {};
	pm.cb = sizeof(pm);
	if (pmi)
	{
		pmi(GetCurrentProcess(), reinterpret_cast<PROCESS_MEMORY_COUNTERS*>(&pm), sizeof(pm));
	}
	MEMORYSTATUSEX ms = {};
	ms.dwLength = sizeof(ms);
	GlobalMemoryStatusEx(&ms);
	DWORD handles = 0;
	GetProcessHandleCount(GetCurrentProcess(), &handles);
	const DWORD gdi = GetGuiResources(GetCurrentProcess(), GR_GDIOBJECTS);
	const DWORD usr = GetGuiResources(GetCurrentProcess(), GR_USEROBJECTS);
	const unsigned int mb = 1024u * 1024u;
	int fixN = 0, heldN = 0;
	unsigned facReads = 0, facHits = 0;
	ScaleTier::IconSynthCounts(&fixN, &heldN, &facReads, &facHits);
	Logger::Get().WriteLine(LogLevel::Info,
		"HEARTBEAT #%u t=+%umin privMB=%u peakPrivMB=%u wsMB=%u availVirtMB=%u "
		"handles=%lu gdi=%lu user=%lu | scaleMap=%u menuBaseline=%u cities=%d "
		"epoch=%d armed=%d continuous=%d ready=%d bornQ=%d visSeen=%d mdock=%d "
		"ticks=%u | icons: uncovered=%d held=%d facReads=%u facHits=%u | logKB=%llu",
		heartbeatSeq,
		static_cast<unsigned int>((nowTickMs - firstHeartbeatMs) / 60000u),
		static_cast<unsigned int>(pm.PrivateUsage / mb),
		static_cast<unsigned int>(pm.PeakPagefileUsage / mb),
		static_cast<unsigned int>(pm.WorkingSetSize / mb),
		static_cast<unsigned int>(ms.ullAvailVirtual / mb),
		static_cast<unsigned long>(handles),
		static_cast<unsigned long>(gdi),
		static_cast<unsigned long>(usr),
		static_cast<unsigned int>(scaleMap.size()),
		static_cast<unsigned int>(menuBaseline.size()),
		cityLoads, gGaugeEpoch, armed ? 1 : 0, continuous ? 1 : 0,
		gReadyCount, gBornQN, gVisSeenN, gMDockLoggedN, tickSerial,
		fixN, heldN, facReads, facHits,
		Logger::Get().BytesWritten() / 1024ull);
}

void UiSpike::TickCheck(unsigned int nowTickMs)
{
	if (inPass)
	{
		// The timer fired on a nested message pump entered by one of our
		// cIGZWin calls: never run two walks on the same stack.
		return;
	}
	PassGuard passGuard(*this);   // v4.10.0: RAII, see UiSpike.h

	if (armed && static_cast<int>(nowTickMs - fireAtMs) >= 0)
	{
		armed = false; // initial fire exactly once per arming
		Run();
	}
	else if (continuous)
	{
		// Catch dynamically created UI (flyout submenus, dialogs, advisors).
		// Runs every tick (~16ms) so new panels (e.g. the Options toolbar)
		// scale before the player perceives a 1x flash. Crash-killer liveness
		// re-checks in ScalePanelsUnder/ScaleMenuFlyouts guard menu churn.
		++tickSerial;
		// Timed (audit A1): the SELPERF table at shutdown reports the per-tick
		// cost, which decides whether batching the tick's id lookups is worth it.
		PerfProbe::Scope perf_("tick.incr");
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

	HeartbeatTick(nowTickMs);
	// inPass is cleared by passGuard's destructor.
}


void UiSpike::LiveViewDump()
{
	cISC4AppPtr pSC4App;
	cIGZWin* pMainWindow = pSC4App ? pSC4App->GetMainWindow() : nullptr;
	cIGZWin* pAppWin = pMainWindow
		? pMainWindow->GetChildWindowFromID(kGZWin_WinSC4App) : nullptr;
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
	// v4.10.0 (S3): an ANONYMOUS window (id 0) born at a recycled
	// address matches a dead record's id (0 == 0), fails both size tests and
	// lands here - silently, until now. That is the "one flyout stuck at 1x
	// after hours" shape the code already describes (the region-switch
	// population bug). Say so once per id per city, the MDOCK budget shape.
	{
		static uint32_t seen[16];
		static int seenN = 0;
		static int seenEpoch = -1;
		if (seenEpoch != gGaugeEpoch) { seenN = 0; seenEpoch = gGaugeEpoch; }
		bool dup = false;
		for (int i = 0; i < seenN; i++) { if (seen[i] == rec.id) { dup = true; break; } }
		if (!dup && seenN < 16)
		{
			seen[seenN++] = rec.id;
			Logger::Get().WriteLine(LogLevel::Info,
				"UiSpike: UNRECOG id=0x%08X ptr=%p now %dx%d, record orig %dx%d "
				"scaled %dx%d%s - left alone. Once per id per city.",
				rec.id, static_cast<void*>(win), w, h, rec.origW, rec.origH,
				rec.scaledW, rec.scaledH,
				rec.id == 0
					? " [ANONYMOUS: if this is a NEW window at a reused address it stays 1x until restart]"
					: "");
		}
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
	for (uint32_t id : kRciColumnIds)
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
						RoundHalfUp(cw * gGaugeScale);
					const int32_t wantH =
						RoundHalfUp(ch * gGaugeScale);
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
						dst[2] = RoundHalfUp(cw * m);
						dst[3] = RoundHalfUp(ch * m);
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
						int32_t dw = RoundHalfUp(w * m);
						int32_t dh = RoundHalfUp(h * m);
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
						// SLACK OF 2px, AND THAT BOUND IS THE WHOLE SAFETY.
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
					// INFO level, not Debug, and its OWN budget - the existing
					// BMPX rows are Debug and were invisible at the player's live
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

	// The BATCHED ID LOOKUPS (FindIdsRecursive, CollectIdsUnder, IdBatch):
	// UiSpikeFlyouts.cpp, in one piece (audit B11).

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
		// Every root in ONE walk (audit A1): 16 lookups a tick, 5 of them
		// misses. Nothing in this loop changes the tree - it swaps vtables and
		// invalidates - so the answers hold for the whole loop.
		cIGZWin* roots[32] = {};
		const int nBatch = (nIds < 32) ? nIds : 32;
		FindIdsRecursive(pSearchRoot, ids, nBatch, roots);
		for (int k = 0; k < nIds; k++)
		{
			cIGZWin* root = (k < nBatch) ? roots[k]
				: pSearchRoot->GetChildWindowFromIDRecursive(ids[k]);
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
					// the repro the the defect report says.
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

// #127 (v2.76.0): drive kPanelDock. Runs from BOTH the full city sweep and the
// incremental pass, because a panel the player OPENS (Graphs, Budget) is never
// present during the load-time sweep - v2.75.1 put the pin in ScaleAll only and
// it therefore never fired even once (the log had no GRAPHPIN line at all).
// Idempotent by construction: once the child sits at its target the delta is 0
// and nothing is written, so running it at 16ms costs a compare per entry.
void UiSpike::ApplyPanelDocks(cIGZWin* pRoot, float f, bool fromShow)
{
	// #137: the guard here was `f < 2.5f` with the note "2x is confirmed on screen;
	// never touch it". That protected a 2x layout the player has since reported
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

	// #162 (2026-08-24): THE DOCK-COMPOSITE INTERLOCK WELD, Y ONLY.
	// The designers encoded the two panels' relative placement as a ghost
	// child (I-2bc90671: id 0x0000AAAA, caption "0xc988bc79", at (-37,12)):
	// composite = dock origin + (134,25). 134 is EVEN - X survives every
	// factor (201 exact at 1.5x; #101 also co-anchors X, so X is never
	// touched here). 25 is ODD - the offset-parity law's broken axis: the
	// design offset is 37.5px at f=1.5 and NO integer placement can align
	// the two background sheets. Rounding UP (38 - the measured state that
	// showed the defect) leaves the composite half a pixel LOW, which
	// UNCOVERS the panel notch's edge from under the dock hump: the user's
	// "sharp blue line + disconnect" beside the mayor medallion, 1.5x only.
	// Rounding DOWN tucks the notch the half pixel FURTHER UNDER the
	// covering hump, where the error is invisible - coverage is one-sided.
	// floor(25*f) is exact at 2x/3x, so the weld is an identity compare at
	// integer tiers by construction. Idempotent like the dock table above.
	// LAW: AN INTERLOCK CHILD ROUNDS TOWARD THE TUCK.
	__try
	{
		cIGZWin* pDockW = pRoot->GetChildWindowFromIDRecursive(0x0987B48F);
		cIGZWin* pComp = pRoot->GetChildWindowFromIDRecursive(0xE9889775);
		if (pDockW && pComp
			&& pDockW->GetW() > 0 && pDockW->GetH() > 0
			&& pComp->GetW() > 0 && pComp->GetH() > 0)
		{
			const int32_t ty = pDockW->GetT()
				+ static_cast<int32_t>(25.0f * f);   // trunc == floor: f > 0
			const int32_t cy = pComp->GetT();
			if (cy != ty)
			{
				pComp->GZWinMoveTo(0, ty - cy);
				static int s_weldLogs = 0;
				if (s_weldLogs < 4)
				{
					s_weldLogs++;
					Logger::Get().WriteLine(LogLevel::Info,
						"UiSpike: INTERLOCK WELD composite 0xE9889775 y %d -> "
						"%d (dock top %d + floor(25*%.2f)=%d, tuck-biased; the "
						"ghost contract from I-2bc90671).",
						cy, ty, pDockW->GetT(), f,
						static_cast<int32_t>(25.0f * f));
				}
			}
		}
	}
	__except (EXCEPTION_EXECUTE_HANDLER)
	{
		Logger::Get().WriteLine(LogLevel::Error,
			"UiSpike: INTERLOCK WELD FAULTED - composite left as placed.");
	}
}

// One idempotent whitelist pass over the visible panels parented to pRoot.
// Safe to run any number of times: Classify() makes re-scaling a no-op.
// Returns the number of windows newly scaled this pass.
int UiSpike::ScalePanelsUnder(cIGZWin* pRoot, const char* rootTag)
{
	const int32_t screenW = pRoot->GetW();
	const int32_t screenH = pRoot->GetH();
	const float f = settings.spikeScaleFactor;

	// DRAIN BEFORE THE WALK (v2.39.0, task #5). Born-scale records were
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
				// re-laying itself is not what the player is watching.
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
			// v2.69.3: the reset that used to sit here was UNSOUND - a verify
			// proves liveness of THIS pointer only, never of the remainder,
			// so the signal must stay latched once anything has mutated.
			if (!StillChildOf(pRoot, p.win))
			{
				continue;
			}
		}

		// REGION: whitelist ONLY. Transient dialogs there (Load Region, the
		// city-info bubble) are game-positioned; scaling them causes the
		// reset/re-anchor fight the player saw as "jumping around". They stay
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
		// RESTORE-TOOLBARS (v4.5.3). Window 0x43 is SIZED BY ITS OWN ART, and
		// that art is already ours and already enlarged - so this sweep's
		// generic double takes a correct 42x38 button to 84x76 (2x art in a
		// 4x box, bottom edge 20 px off-screen). The capture logs record it
		// as "THIS ONE FLASHED ON SCREEN" and the user confirmed the jump.
		// Once CodePatches has fixed the ORIGIN at the source, the button is
		// born correct and the only thing left for us to do is not touch it.
		//
		// Gated on the patch actually being live, not on the tier: if the
		// write was refused (modded exe, unknown build) the button is still
		// mis-placed, and standing down would leave it clipped with nothing
		// compensating. A refused patch therefore falls back to exactly
		// today's behaviour rather than a new untested state.
		// Inline rather than a kNeverScaleIds entry: this is a runtime
		// condition, and that table is a compile-time set consulted from
		// several passes that must keep scaling this id when unpatched.
		if (p.win->GetID() == 0x00000043
			&& CodePatches::RestoreToolbarsOriginPatched())
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
		// (0xAA32BCE6, the DATA VIEWS panel, was skipped here until v2.21.0. It is
		// scaled like any panel since v2.21.2, with the DVMAP surface recreate
		// further down this function: REGRESSION.md [CC-27].)
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
		// LAW: WHEN THE ROOT HAS NO ID, THE FIX CANNOT BE AN ID LIST. Widen
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
	// only exists once the player OPENS the panel, long after the load-time sweep
	// - putting this in ScaleAll alone (v2.75.1) meant it never fired once.
	// City passes ("city"/"incremental") get it from ScaleGodFlyouts two
	// statements below, whose first act (after two inert probes) is
	// ApplyPanelDocks on this same root - so running it here too was a second
	// full dock pass every tick (audit A1, 2026-09-25). The region pass has no
	// ScaleGodFlyouts and keeps this call.
	if (rootTag[0] == 'r') { ApplyPanelDocks(pRoot, f); }

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
		// The scoped search is what keeps the dashboard's twin out. The descent
		// check in TryRecreateMinimapSurface only catches the engine's tree links
		// disagreeing (see its note there); the v2.41.0 comment that first called
		// it a gate: REGRESSION.md [CC-28].
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
		// The clamp's history before v2.72.0 (off in v2.70.0, back on in v2.70.1,
		// the fallback in v2.71.0): REGRESSION.md [CC-16].
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
					// 0x7A8640, so it lands a tick or more later - the player sees
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
				// DUPLICATED ON PURPOSE, FOR NOW: this block cannot simply
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
					// 0x7A8640, so it lands a tick or more later - the player sees
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
					// retired in v2.71.4 (REGRESSION.md [CC-02]). The kick now
					// just re-fires the recompute and the synchronous bake - at
					// every zoom.
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
		// no single obvious answer. Rather than making the player cycle
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

			// CARRY-OVER (v2.41.14). UDMAP was the ONE block with NO
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
		// Only when UDMAP's lookup of that root hit (audit A1): on a miss
		// nothing above has run, so its own lookup of 0x4BCB938A would miss
		// too - and a miss returns before any of its state is touched.
		if (pUdRoot) { HookDashboardGauges(pRoot, f); }

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
				// THEY DREW 1x ANYWAY BECAUSE A GZWinBMP DRAWS dst = src
				// (law 83 / the BMPX rationale at :11655) and these roots were
				// not in this list, so the blit hook never ran on them. A
				// window at 92x194 showing a 46x97 source is exactly the player's
				// "identical instead of scaling", and it is why FIVE patches
				// aimed at sizes and constants could not move it - the size was
				// already right and the BLIT was not following.
				//
				// THE "IT IS NOT A WINDOW" VERDICT WAS A FALSE NULL OF MY
				// OWN MAKING. The 37-dump test compared the last 8 dumps
				// against the FIRST FIVE - and these windows first appear in
				// dump #5, so the things being hunted were absorbed into the
				// test's own baseline. They are never destroyed either: they
				// persist in the view's child list and merely toggle vis, and a
				// "no NEW ids" test is structurally blind to a resident
				// show/hide widget. The positive control (the picker grid
				// appearing for one tick) proved the dump sees TRANSIENTS; it
				// never proved it could see THIS.
				// LAW: A DIFF NEEDS A BASELINE TAKEN BEFORE THE THING
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
						// The painters use cIGZWin+0x24 (LOCAL rect), NOT
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
						//     keep the confirmed on screen leftward text widening.
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
								// LOG BEFORE THE GATE. The accept path below is
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
									// DUMP THE RAW FIELDS - DO NOT GUESS AGAIN.
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
						// breaks up - the "Expense / s" the player reported.
						//
						// These are PLAIN FIELDS on the chart object with no
						// setter in the module, read fresh on every layout,
						// so scaling them needs NO byte patch and touches no
						// shared engine code - which matters because the
						// paint path is shared by every chart in the game.
						// The plot rect is computed ONCE: sub_9B3647 only
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
							// SCALE THE MARGINS, NEVER IMPOSE A RECT. The
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
							// NO SENTINEL RE-ARM. v2.50.0 re-armed
							// [0xE0] to force a re-lay and the recompute came
							// back as the FLAT 16px DEFAULTS (16,16,960,496),
							// discarding the very margins we want to scale.
							// The rect is computed once and nothing re-arms
							// it, so writing it directly STICKS - that is the
							// whole reason this lever works.
							// ONCE PER OBJECT (gChartScaled): the sweep
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
		// measured (2026-07-29 20:29 capture ("DATA VIEWS
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

// AbsoluteTopLeft and ScaleGodFlyouts: UiSpikeFlyouts.cpp (audit B11).

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


// Push the RESOLVED tier factor into the hook-visible mirror, from the one
// place that knows it, at the moment it is known - and UNCONDITIONALLY,
// including tier 1. gTierF is namespace-scope and invisible to `settings`,
// which is exactly why it drifted: the two functions that used to set it are
// scaling paths, so they do not run when there is no scaling to do, and the
// mirror kept its initialiser instead.
//
// DO NOT GATE THIS ON factor > 1.01. That gate is what created the bug:
// "no scaling" still has a correct factor (1.0), and 97 read sites need it.
void UiSpike::SetTierMirror(float f)
{
	gTierF = f;
	// Build 1 (review 2026-08-24, finding 5): prime the ForceRuntimeScaleId
	// lazy read HERE - the tier tail, director constructor, outside every
	// hook - so the one-time ini read + resolved-value log can never fire
	// inside the SetFlag/paint detours that consult IsNeverScaleId. After
	// this call the helper is a pure static read forever.
	(void)ForceRuntimeScaleId();
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
		// #166: A PANEL ROOT IS SIZED AS A LENGTH, NOT BY ITS EDGES.
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
		// THIS IS NOT A REVERSAL OF #161, AND THE DISTINCTION IS THE WHOLE
		// FIX. #161 made CHILDREN round in the parent's ABSOLUTE DESIGN frame,
		// because a child's edge must land exactly on its parent's and on its
		// siblings'. That is still right and is untouched here (ScaleSubtree,
		// ~:16913). A ROOT has no sibling to abut - it is anchored in the frame
		// and its only contract is with ITS OWN ART. Edge-derived is correct
		// for a child; length-derived is correct for a root. Same file, two
		// roles, two rules (law 86).
		//
		// PROVABLE NO-OP AT AN INTEGER FACTOR, by arithmetic rather than
		// hope: when v*f is exact for all v, R(l+w)-R(l) = (l+w)f - lf = wf =
		// R(w*f). So 2x and 3x are bit-identical and the 530 above is 0 there.
		// emu_panel_anchor.py models the OLD law and reproduces 39/39 panels
		// from the captures. After this change it must be updated in step; a
		// mismatch against a pre-#166 capture is the change working, NOT a
		// regression - but it must be re-baselined deliberately, not ignored.
		// SCOPED TO ROOTS THAT OWN A BACKGROUND SHEET. The first cut of this
		// applied length-sizing to EVERY panel root - 627 of them at 1.5x - to
		// correct the 5 that actually have art whose size must match. The other
		// 622 carry no background image at all, so moving them a pixel is an
		// unrequested change with no benefit. That is law 94, the right rule at
		// the wrong scope, walked into eight hours after writing it down.
		//
		// The set is DERIVED, not hand-written: it is every ROOT-depth node in
		// the .UI corpus that carries an `image=` AND `blttype=tiled`, i.e. a
		// window whose own background sheet is bound to it. Regenerate with the
		// census; it currently yields 17, and
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
		//   0 of 39 panels move at 2400x1600 f=2.0 (the CONFIRMED ON SCREEN tier)
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
		// Measured across the player's captures at every tier - img 48/64/96 in
		// a window ScalePanelRoot had set to 72/128/288, i.e. art*f = 32*f*f.
		// Refuse the write and source == window, so the blit's clamp gives
		// m = 1 and the marker draws at exactly 32*f.
		//
		// THE MOVE GOES WITH IT. newX/newY are computed FROM newW/newH,
		// so "size only" is not separable - and the measured teleport
		// (934,700)->(902,668) is 32px off the world point the game had just
		// set for it. A move derived from a size we refuse to write is
		// incoherent.
		//
		// THE RECORD IS STILL MANDATORY. Without one this root stays
		// Fresh, and PURGE-ON-FRESH-ROOT wipes every descendant record on every
		// pass - the count child would classify Fresh and be re-scaled by f
		// each sweep. Runaway growth, and the least obvious trap here.
		//
		// count++ MUST NOT FIRE: nothing was mutated, and the log line
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
		// LAW: A ROOT WHOSE POSITION IS AN OUTPUT MUST NOT BE RE-ANCHORED.
		// Ask whether the game rewrites left/top every frame. If it does, its
		// position is already in final screen space and scaling it is a second
		// application - the positional twin of the born-at-art-size trap.
		const bool worldAnchored = (win->GetID() == 0x27DF05BE
			|| win->GetID() == 0x27DF05BF);

		// Proven call order preserved: move the root to its anchor first,
		// then resize. The move is RELATIVE, so the delta comes from the
		// CURRENT position even when the anchor came from the recorded one.
		// A SEAT-ON-RESIZE WAS HERE AND IS REMOVED. It compensated the
		// growth against the marker's bottom-centre tip, which is the right
		// ANCHOR - but it cannot work, because the tool re-places this window
		// EVERY FRAME: 0x0043A26A / 0x00437ED5 call GZWinMoveTo with
		// (mouseX - [ctrl+0x48], mouseY - [ctrl+0x44]). Anything we write is
		// overwritten on the next tick.
		//
		// THE REAL CAUSE IS A LATCH (the #176 shape again). Those two
		// offsets are captured AT INIT, at 0x0043A82D and 0x0043A841, as
		//     [ctrl+0x44] = win->GetH()      -> 97
		//     [ctrl+0x48] = win->GetW() / 2  -> 23
		// while the window is still 46x97, and NOTHING refreshes them. Our
		// sweep then grows the window to 92x194 and the game keeps anchoring it
		// with 1x offsets, so the tip lands half a marker down-and-right of the
		// cursor - exactly "shifted down and to the right".
		//
		// LAW: BEFORE COMPENSATING A POSITION, CHECK WHO WRITES IT LAST.
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
				if (!StillChildOf(win, snap.wins[i]))
				{
					continue;
				}
			}
			// #161: a panel root's own extent was rounded at ITS design origin
			// (newH = R(t+h) - R(t)), so its children must round there too or
			// a child whose edge equals the parent's height lands a pixel past
			// it. MEASURED on the god toolbar: strip (5,1011) 74x351 -> 526
			// tall, while its bottom cap at local t=351 rounded to 527 - the
			// one transparent pixel the player reported as a break in the rail.
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
	// Guard: a dialog that arrives already scaled by data is left alone (the
	// data-born exact-match guard below; history REGRESSION.md [CC-23]).
	{
		// Also scaled at runtime: the "Text Entry" prompt (Save City confirm,
		// I-e9263d4c) and Set Lot Size (I-e9263de5), which the game builds
		// through the same bypass as the two quit confirms (v2.25.6).
		//
		// bw/bh: up to FOUR measured 1x base sizes per id (0 = unused), read by
		// the data-born EXACT-MATCH guard below. The quit/exit confirms are ONE
		// FAMILY whose script<->id mapping varies with package and mod state, so
		// every member carries EVERY candidate base and the mapping stops
		// mattering (v2.39.14). Safe by arithmetic: at f=1.5/2/3 the products
		// {495x236, 405x242, 405x243}, {660x314, 540x322, 540x324} and
		// {990x471, 810x483, 810x486} never collide with a 1x base (330x157 /
		// 270x161 / 270x162), nor do the fourth base's (330x109, v2.64.0:
		// 495x164, 660x218, 990x327). The exact match fails LOUDLY when a base
		// is missing (a 4x resize on screen), so the table must be complete.
		// designW is read by no code: the width guard it was declared for was
		// replaced by the exact match.
		// History (v2.25.6-v2.64.0): REGRESSION.md [CC-23].
		struct CityDialog { uint32_t id; int32_t designW;
			int32_t bw[4]; int32_t bh[4]; };
		const CityDialog kCityDialogIds[] = {
			// Bases MEASURED from the corpora 2026-07-31 (stock extraction +
			// thirdparty-src + every staged tier - staged sizes are all
			// exactly RoundHalfUp(base*f), verified at 1.5x/2x/3x). Listed
			// here: stock 330x157, stock 270x161, save-warning mod 270x162.
			//
			// The fourth base, 330x109, is the two-button region-screen quit
			// (I-4a551b4c), which we stage at every tier. Without it (before v2.64.0,
			// #102) a data-born 660x218 arrival fell through to SetW/SetH and came
			// out 1320x436: REGRESSION.md [CC-29].
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
			// Tried in this list and removed: 0x4A9DB60C and 0xEBB16D71 (v2.25.17),
			// the budget masters (v2.25.23: data-doubled, roots in kNeverScaleIds)
			// and 0x0423278F (banned below). History: REGRESSION.md [CC-21].
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
			// (The v2.25.9 note on the Save City status box - "in NO .UI script"
			// and the designW-560 width guard - was falsified by v2.39.13, below:
			// REGRESSION.md [CC-30].)
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
		// DO NOT "fix" this by consulting IsNeverScaleId here. That would
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
		// v2.25.20: collect EVERY instance of each id - the single-find
		// returned the hidden TEMPLATE for the budget masters and the
		// visibility check then skipped the real open dialog.
		// All six ids in ONE walk (audit A1; it was six walks of the main
		// window a tick). A visible instance gets scaled and moved, so once
		// one has been handled the ids after it are collected again.
		const int kDlgN = static_cast<int>(
			sizeof(kCityDialogIds) / sizeof(kCityDialogIds[0]));
		uint32_t dlgIds[kDlgN] = {};
		for (int k = 0; k < kDlgN; k++) { dlgIds[k] = kCityDialogIds[k].id; }
		cIGZWin* dlgFound[kDlgN][4] = {};
		int dlgCount[kDlgN] = {};
		CollectIdsUnder(pMainWindow, dlgIds, kDlgN, dlgFound, dlgCount);
		bool dlgTouched = false;
		for (int di = 0; di < kDlgN; di++)
		{
			const CityDialog& dlg = kCityDialogIds[di];
			const uint32_t dlgId = dlg.id;
			if (dlgTouched)
			{
				CollectIdsUnder(pMainWindow, dlgIds + di, kDlgN - di,
					dlgFound + di, dlgCount + di);
				dlgTouched = false;
			}
			cIGZWin** found = dlgFound[di];
			const int nFound = dlgCount[di];
			for (int inst = 0; inst < nFound; inst++)
			{
			cIGZWin* pDlg = found[inst];
			if (!pDlg || !pDlg->IsVisible())
			{
				continue;
			}
			dlgTouched = true;
			const int32_t w = pDlg->GetW();
			// The two MODAL confirms. The rest of this list keeps
			// preserve-the-old-centre.
			//
			// v2.38.1 CORRECTION TO v2.37.5. These were forced to the true
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
			// ---- THE DATA-BORN GUARD (v2.38.0 #79c; exact match since v2.39.13) ----
			// A dialog in this table can arrive already scaled BY DATA (the root
			// DialogStatic package, or our SaveWarningUI / CamUI rebuild of a mod's
			// script). Such a window must not be scaled again, and it is not moved
			// either (see "NOTHING MOVES HERE" below).
			//
			// The test is on the ARRIVED SIZE, never on which package supplied the
			// script, and it applies to every id in this table (LAW 23: scoping a
			// guard to the case you tested leaves the untested cases unguarded). Both
			// conditions are required:
			//   - Classify() == Fresh: no scale record of ours exists, so the window
			//     is not one WE scaled on an earlier sweep. A window with a record
			//     must go on to the child re-pass below (v2.25.18). Classify also
			//     erases stale and address-reused records.
			//   - EXACT PRODUCT MATCH: the arrived (w,h) is RoundHalfUp(base * f)
			//     +-1px for one of the id's measured 1x bases. No width threshold can
			//     work: the Save box's 1x and scaled candidate sets overlap.
			// Residual accepted: a foreign mod shipping one of these ids at exactly
			// one of our product sizes would be wrongly skipped; that is undecidable
			// by size alone. History (v2.38.0-v2.39.13): REGRESSION.md [CC-22].
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
				// CORRECTION (v2.38.0, measured): "RE-OPENED on the same window
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
				// composed it, unattached to its slider. That is the player's
				// "white lines in budget are broken" at 3x, and the block's own
				// comment above records the same sentence from the 2x era.
				// Derived, not constant - and it reduces to 16 at f=2 exactly,
				// so the confirmed 2x layout cannot move (the law: "a
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
			// CONFIRMED ON SCREEN as shipped, so the confirmed integer tiers must
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
					RoundHalfUp(120.0 * settings.spikeScaleFactor);
				const int32_t comboDy =
					RoundHalfUp(settings.spikeScaleFactor)
					- static_cast<int32_t>(std::floor(settings.spikeScaleFactor));
				// COMPOUNDING GUARDRAIL (review 2026-08-17, finding 3): the
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
				const int32_t capX = RoundHalfUp(400.0 * mf);
				const int32_t capW = RoundHalfUp(120.0 * mf);
				const int32_t monX = RoundHalfUp(520.0 * mf);
				const int32_t monW = RoundHalfUp(85.0 * mf);
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
			// THE #110 DEFECT, measured and then confirmed on screen on both sides:
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
			// the box (stock control, confirmed on screen) - so #103's "stock has no
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
				RoundHalfUp(stockPopH * pf);
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
	// identify itself the next time the player opens one.
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
		for (uint32_t id : kRciColumnIds)
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
			if (!StillChildOf(pMenu, child))
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
	// not present in this binary's map - probe once with the log-before-call guard.
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
// DELIBERATELY TIER-GENERAL - this is a runtime ordering fix, not art
// maths; the same stale latch fires at 2x/3x whenever a session gets no
// post-sweep rating tick, so gating it to fractional factors would re-ship
// the historical 2x half-bar. There is no arithmetic of ours in the path:
// the values written are exactly what the game's next SetImage would write.
// ADVERSARIAL REVIEW 2026-08-16 NARROWED THE SCOPE, and the reasons are
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
		// toolbar at 1.5x, which is what the player saw as "a break in the white
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
		// NO-OP AT AN INTEGER FACTOR BY CONSTRUCTION: ScaleRound is exact
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
		// #167: A STATE-STRIP BUTTON IS SIZED AS A LENGTH, NOT BY ITS EDGES.
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
		// THIS DOES NOT REVERSE #161. #161 governs a child's POSITION - newL
		// and newT above still round in the parent's absolute design frame, so
		// edges still land on their parent's and their siblings'. Only the
		// EXTENT changes, and only for a window whose art cell must fit inside
		// it. Position edge-derived, size length-derived.
		//
		// PROVABLE NO-OP AT AN INTEGER FACTOR: when v*f is exact for all v,
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
		// exactly what the player saw on Landscape's "Level Terrain" (the only
		// one of five buttons at an odd l) and on the god-mode Day/Night sun
		// and moon (all three at l=79).
		//
		// WHY THE SIZE AND NOT THE POSITION. The first repair moved such
		// buttons onto an even edge, in the .UI, at build time. It fixed the
		// reported cases and SHIPPED A WORSE BUG: a nudge is up to 2px at 1.5x,
		// and in the densest grid in the game ("Select A My Sim", 21 faces) the
		// whole grid visibly slid left inside its own frame. Reverted the same
		// day. Changing the WIDTH moves nothing and is bounded by one pixel.
		//
		// WHY LEAVES ONLY. Edge-derived rounding exists so that abutting
		// pieces stay abutting - #143's white seams are what happens when they
		// do not. A window WITH CHILDREN is a panel: it tiles with its
		// neighbours and its edges are load-bearing. A LEAF is a discrete icon;
		// nothing is butted against it, so a one-pixel size change is invisible
		// while a one-pixel art mismatch is not. Containers keep edge-derived
		// rounding untouched, so the seams cannot come back.
		//
		// NO-OP AT AN INTEGER FACTOR BY CONSTRUCTION: ScaleRound(l*2) is
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
				// LIVE child list before touching it (StillChildOf).
				if (!StillChildOf(win, snap.wins[i]))
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
