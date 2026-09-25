#pragma once
#include <cstdint>

#include "cIGZWin.h"
#include "Logger.h"

// What UiSpike.cpp shares with the files split out of it (audit B11,
// 2026-09-25). Each seam was measured by compiling the halves apart, and
// this header holds exactly what the compiler asked for:
//   UiSpikeSelector.cpp  gReadoutW, gReadoutH, SafeAbsRect
//   UiSpikeRegion.cpp    ChildSnapshot, gGaugeEpoch, kGZWin_RegionScreen
// Variables are defined in UiSpike.cpp; constants and ChildSnapshot are
// inline here. Anything added widens a seam, so add only what a split needs.
namespace UiSpikeInternal
{
	// #192: the render size the director measured, for the resolution
	// readout and the selector's resolution rows.
	extern int32_t gReadoutW;
	extern int32_t gReadoutH;

	// SEH-guarded walk of a window's ABSOLUTE top-left (sum of GetL/GetT up
	// the parent chain) plus its own w/h. False on a fault.
	bool SafeAbsRect(void* winPtr, int* outL, int* outT, int* outW, int* outH);

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
}
