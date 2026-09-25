#pragma once
#include <cstdint>

// What UiSpike.cpp and UiSpikeSelector.cpp share (audit B11, 2026-09-25).
// The in-game scale selector was split out of UiSpike.cpp; these three are
// all it used from the rest of that file (measured by compiling the two
// halves apart). Defined in UiSpike.cpp. Anything added here widens the
// seam between the two files, so add only what the compiler asks for.
namespace UiSpikeInternal
{
	// #192: the render size the director measured, for the resolution
	// readout and the selector's resolution rows.
	extern int32_t gReadoutW;
	extern int32_t gReadoutH;

	// SEH-guarded walk of a window's ABSOLUTE top-left (sum of GetL/GetT up
	// the parent chain) plus its own w/h. False on a fault.
	bool SafeAbsRect(void* winPtr, int* outL, int* outT, int* outW, int* outH);
}
