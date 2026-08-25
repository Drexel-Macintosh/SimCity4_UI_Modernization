#pragma once
#include <stdint.h>

// Public surface of the DX7 draw-call census (tools\research\udriveit\
// gdcap.cpp, compiled into the DLL for register row #4). Log-only; the
// wrapper (CodePatches::ArmGpuCapProbe / WriteGpuCapCloseout) owns all
// logging - this module never touches the Logger.
namespace GdCap
{
	// Byte-gates the three hook sites and arms the hooks. Recording does NOT
	// start yet - it waits for Begin(). Returns nullptr on success, else a
	// static reason string for the refusal log.
	const char* Install(uint32_t frames, uint32_t maxRecords,
		const wchar_t* outPath);

	// City latch (PostCityInit): recording starts after `skip` more Clear
	// boundaries, then runs for the Install()-requested count and self-
	// disarms. Idempotent; returns true only on the call that latches.
	bool Begin(uint32_t skip);

	// City exit (PreCityShutdown): keeps the capture honest if the player
	// leaves the city early. 0 = nothing to do, 1 = un-latched while still
	// skipping (next city re-latches), 2 = finalized a partial recording.
	int CityExit();

	bool Installed();

	// Idempotent; writes the GCAP file (header + records). Call OUTSIDE any
	// hook - PreAppShutdown. Returns true if the file is on disk.
	bool WriteCloseout();

	// Positive control: total driver calls seen since the hooks armed.
	// 0 means the probe never saw the driver and any null capture is VOID.
	uint32_t CallsSeen();
	uint32_t RecordsUsed();
	uint32_t FramesCaptured();

	// Clear boundaries seen since the latch. Adjudicates a short capture:
	// SC4 issues Clear only when it redraws, so a low count means the view
	// was static, not that the probe failed.
	uint32_t ClearsSinceBegin();

	// Unconditional marker censuses + which marker owned the session
	// (0 = neither ever fired, 1 = Clear, 2 = Flush). Together these
	// separate "the game did not redraw" from "the marker hook is dead".
	uint32_t ClearsTotal();
	uint32_t FlushesTotal();
	int      MarkerUsed();
}
