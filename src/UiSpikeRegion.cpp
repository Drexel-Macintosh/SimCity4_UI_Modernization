////////////////////////////////////////////////////////////////////////////
//
// UiSpikeRegion - the region screen: tile-grow zoom (RegionZoomStep,
// ApplyPendingRegionZoom) and the region watcher that activates the pass
// (RegionWatchTick).
//
// Split out of UiSpike.cpp verbatim (audit B11, 2026-09-25). It shares
// ChildSnapshot, gGaugeEpoch and kGZWin_RegionScreen with the rest of
// UiSpike (UiSpikeInternal.h).
//
////////////////////////////////////////////////////////////////////////////

#include "UiSpike.h"
#include "UiSpikeInternal.h"

#include "Logger.h"
#include "ScaleTier.h"
#include "CodePatches.h"
#include "cIGZWin.h"
#include "cISC4App.h"
#include "GZServPtrs.h"      // cISC4AppPtr

#include <cmath>
#include <cstdint>
#include <Windows.h>

using UiSpikeInternal::ChildSnapshot;
using UiSpikeInternal::gGaugeEpoch;
using UiSpikeInternal::kGZWin_RegionScreen;

namespace
{
	// (#131 REGIONCAM/REGIONWATCH, the read-only probes of the region camera
	// and its device frustum, lived here. They proved the camera lever DEAD -
	// our scale reached the device and the screen ignored it - and were
	// removed in the 2026-09-25 audit, B1. The measurements and the offsets
	// are in _tests/REGRESSION.md, "THE LEVER THAT DOES NOT WORK".)

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

	// (#131 v2.79.0 REGIONTILE, the per-tick composite resize, is gone: the
	// growth happens inside the game's own rebuild via the sub_7AE3D0 hook,
	// CodePatches::ApplyRegionTileScale / GrowTileBitmap. Its leftover buffer
	// constants were removed in the 2026-09-25 audit; the engine facts - the
	// 0x00AC1400 vtable correction, Init's four args and its ready latch -
	// are in tools/research/REGION-SCREEN.md and REGRESSION.md.)

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
// ROTATION IS NOT OFFERED and must not be faked. The tiles are thumbnails
// baked at a fixed angle when each city was last SAVED; rotating the region
// would require re-rendering every city, which only the city view can do at
// save time. A button that cannot work is worse than no button.
void UiSpike::RegionZoomStep(int dir)
{
	if (dir == 0 || settings.spikeRegionZoomLevels <= 0) { return; }

	// THE WHEEL ONLY RECORDS INTENT. Applying a zoom rebuilds 18 pixel
	// buffers (9 tiles x source + composite) with Shutdown/Init/resample,
	// synchronously. Doing that per notch FROZE THE GAME when the player
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
		// while the player keeps scrolling into the wall.
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
	// Inside a city this search always MISSES (the region screen is torn down
	// and only returns after Disarm), and a miss walks the whole main tree -
	// every tick. So one confirmed miss while `continuous` latches for the
	// rest of that city: gGaugeEpoch changes at Disarm, which re-opens the
	// search. A region window that merely exists hidden is found, never
	// latched, so the present=false path below is unchanged (audit A1).
	static int s_regionMissEpoch = -1;
	cIGZWin* pRegion = nullptr;
	if (!(continuous && s_regionMissEpoch == gGaugeEpoch))
	{
		pRegion = pMainWindow->GetChildWindowFromIDRecursive(kGZWin_RegionScreen);
		if (!pRegion && continuous) { s_regionMissEpoch = gGaugeEpoch; }
	}
	const bool present = (pRegion != nullptr) && pRegion->IsVisible();

	// RGKID (v2.26.7, measurement): change-only dump of the region screen's
	// direct children + one level below - the CITY-SELECT BUBBLE (with the
	// Mayor Rating bar the the defect report says drawing twice) lives there and has
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
		// this used to claim "scaleMap keeps its
		// records, so persistent region UI is NOT re-scaled on return."
		// MEASURED FALSE - nothing in the region host subtree persists. All
		// nine panels re-scale from DESIGN geometry at boot-equal descendant
		// counts (10/2/9/3/5/18/10/3/3) on every city->region return, and the
		// return is safe because of PURGE-ON-FRESH-ROOT, not because records
		// survive. Your own comment is an instrument, and this one lied.
		regionChildCountSeen = -1;
		regionStableTicks = 0;
		regionActive = false;
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
		// comes back exactly as the player left it. Zeroing the level here would
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

		// v2.79.1: dump the tile items + their sprite bounds, once per region
		// arrival (read-only).
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
	// #131: there is deliberately NO per-tick tile pass here. v2.80.0 had
	// one; it resized buffers the game OWNS and the game restored them every
	// frame (counter 9/18/27/36, unbounded) while the click mask went stale
	// and city tiles became unclickable. The growth now happens inside the
	// game's own rebuild via the sub_7AE3D0 hook
	// (CodePatches::ApplyRegionTileScale), so the composite and the click mask
	// inherit the new size for free. Law 57: a fix that must re-apply every
	// tick is a fight, not a fix.

	// Same idempotent whitelist pass as the city view, every tick while the
	// region screen stays up.
	ScalePanelsUnder(pRegion, "region");

	// Transient dialogs are NOT docked at runtime. They carry game-generated
	// scrolling lists (the Audio playlist), slider and radio-grid controls,
	// and LIVE content the game re-lays-out every frame - tree-scaling them
	// malformed the layout and fought the game's per-frame reset (jumpy).
	// Static .UI script scaling is the shipping path. (The experimental
	// DockDialogs=1 path was removed in the 2026-09-25 audit, B1.)
}
