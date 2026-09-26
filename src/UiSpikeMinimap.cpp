////////////////////////////////////////////////////////////////////////////
//
// UiSpikeMinimap - the cSC4WinMiniMap windows: the HUD dock minimap's
// surface recreate (TryRecreateMinimapSurface), the bake-size snap all three
// instances share (SnapMiniMapToBake), the early bake at PostCityInit
// (EarlyMinimapBake) and the #126 draw hook; plus the surface carry-over and
// the synchronous bake, which the Data Views and U-Drive-It map blocks in
// UiSpike::ScalePanelsUnder call too.
//
// Split out of UiSpike.cpp verbatim (audit B11, 2026-09-25). What it shares
// with UiSpike.cpp is in UiSpikeInternal.h.
//
// Saved as UTF-8 WITH a byte-order mark, like UiSpike.cpp: a log string in
// TryRecreateMinimapSurface carries a non-ASCII character, and MSVC reads a
// file without the mark in the ANSI code page, which would change the
// string's bytes.
//
////////////////////////////////////////////////////////////////////////////

#include "UiSpike.h"
#include "UiSpikeInternal.h"
#include "UiSpikeIds.h"       // kGZWin_WinSC4App, kGZWin_SC4View3DWin

#include "Logger.h"
#include "CodePatches.h"     // MiniMapX8Active: the bake ceiling
#include "cIGZWin.h"
#include "cIGZBuffer.h"
#include "cISC4App.h"
#include "GZServPtrs.h"      // cISC4AppPtr

#include <cstdint>
#include <Windows.h>         // SEH guards

using UiSpikeInternal::ParentIdOf;
using UiSpikeInternal::SafeBufProbe;
using UiSpikeInternal::kSurfMaxAttempts;
using UiSpikeInternal::lastMinimapSurfResize;
using UiSpikeInternal::gMinimapRetry;
using UiSpikeInternal::gMmStretches;
using UiSpikeInternal::gMmEntries;
using UiSpikeInternal::gMmHooked;
using UiSpikeInternal::DriveMiniMapBake;
using UiSpikeInternal::CaptureSurface;
using UiSpikeInternal::RestoreSurfaceBilinear;
using UiSpikeInternal::LogMinimapBuffer;
using UiSpikeInternal::HookMiniMapDraw;

// ---- SHARED WITH UiSpike.cpp (UiSpikeInternal.h) ---------------------------
namespace UiSpikeInternal
{
	// Per-city, so UiSpike::Disarm resets both: the SECOND-CITY LIFECYCLE
	// LATCHES note in UiSpike.cpp, and BOUNDED RETRY in UiSpikeInternal.h.
	cIGZWin* lastMinimapSurfResize = nullptr; // HUD dock minimap surface latch
	SurfRetry gMinimapRetry = {};
}

namespace
{
	// ===== SURFACE CARRY-OVER (v2.41.14, task #89) ==========================
	// THE DEFECT THESE EXIST TO FIX, measured 2026-08-01 and confirmed on screen:
	// our surface-recreate destroyed the display surface, built a new one and
	// PRE-CLEARED IT TO BLACK - so a perfectly good map vanished until the
	// engine's message-driven bake landed, and that empty box is what the player
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
}

namespace UiSpikeInternal
{
	// v2.71.1 (#121, the last 1%): run the game's OWN terrain bake right now
	// instead of waiting for its message.
	//
	// WHY: the recompute at 0x7A7840 does not paint anything - it reallocates
	// the raster, recomputes zoom, memsets the dirty-tile mask to all-0xFF and
	// sets fd=1. The paint happens later, when the game's message handler
	// (0x7A8640) sees fd and calls the bake at 0x7A7FF0. For stock that is
	// invisible: its map is already correct before the panel is shown. Ours is
	// rescaled and its surface recreated AFTER creation, so the bake lands a
	// tick or more after the panel is on screen and the player sees it fill in.
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

	// Copy a surface's pixels out. Returns false (and leaves w/h 0) on any
	// failure, which makes the caller fall back to the plain black fill - i.e.
	// exactly the pre-v2.41.12 behaviour, never worse.
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

	// MMBUF (v2.41.4, task #89). THE PRIVATE PAINT BUFFER, not the display
	// surface. The dock minimap ships winflag_pbuff=yes, and our own measured
	// law from the U-Drive-It gauges (#46/#47) says a pbuff at [win+0x6c] is
	// ALLOCATED AT FIRST PAINT from the window's then-current size. If the
	// game paints the minimap once at 64x64 and our sweep then resizes the
	// window to 128x128, every later draw composites through a 64x64 buffer -
	// which is the "corrupted map" the player sees, and it would persist until
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
			// [+0x114] IS NOT A COM OBJECT. It is a PLAIN 3-DWORD STRUCT -
			// {pixel pointer, w, h} - exactly as our own fallback uses it:
			// 0x007A7570(raw + 0x114, w, h) treats ecx as that struct, and the
			// bake reads it as a raw base (0x7A8550: mov esi,[ebx+0x114]).
			//
			// v2.41.6 passed raw+0x114 to SafeBufProbe, which does a VIRTUAL
			// call (QueryInterface). That loads the FIRST PIXEL of the map
			// raster as a vtable pointer and calls through it - a wild
			// indirect call, caught by SEH only by luck, and the exact hazard
			// the SAFETY notes atop UiSpike.cpp warn about. It also made every
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
		// black yet the player sees colour, the pixels have to come from
		// somewhere - this says whether the raster holds real map data,
		// uninitialised heap, or nothing. Reads only; no calls.
		// SAMPLE THE MIDDLE, ON A DIAGONAL - v2.41.11 fix to my own probe.
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
		// THE FIVE-POINT DIAGONAL ABOVE CANNOT LOCATE A BLOCK. It samples
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
// surface was still showing pre-bake content. That content is what the player
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
// THIS IS THE ONE THING WE RUN INSIDE PostCityInit, and that is the region
// carrying the measured hang. It is kept as small as it can possibly be: two
// non-recursive hops, one first-match recursive lookup, two BYTE WRITES and
// one InvalidateSelf. No tree walk, no geometry, no surface allocation - none
// of what ScaleAll does, which is what earned the ban. [Spike] EarlyBake=0
// makes it completely inert without a rebuild.
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

	// (MODE 2 - scaling the dock itself here at PostCityInit - repeated the
	// v2.41.15 crash shape one ini key away and was removed in the
	// 2026-09-25 audit, B1. The dock is scaled early by EarlyDock instead.)
}

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

	// THE LEGAL SET IS terrainDim << k FOR ANY INTEGER k - MULTIPLES **AND
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
	// THIS IS 1.5x's PROBLEM AND IT IS STRUCTURAL. The dock recess is 64px
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
	// SAFETY PROPERTY, and the reason this is shippable without re-verifying
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
	// ...but the sweep re-checks the dock map on EVERY tick (TryRecreate-
	// MinimapSurface runs each pass), so an IDENTICAL repeat - same window,
	// terrain, slot and result - is counted instead of printed, and the count
	// rides on the next line that does print. Every snap that changes anything
	// still logs its branch. Before this, ~35 Info lines a second in every city
	// at the shipped LogLevel=1 (measured 2026-09-25: 382 lines in 380 ticks).
	struct SnapSeen { cIGZWin* map; int32_t dim, w, h, snap; unsigned repeats; };
	static SnapSeen s_seen[2] = {};
	SnapSeen& seen = s_seen[strcmp(who, "UDMAP") == 0 ? 1 : 0];
	if (seen.map == pMap && seen.dim == terrainDim && seen.w == curW
		&& seen.h == curH && seen.snap == snap)
	{
		++seen.repeats;
	}
	else
	{
		char rep[64] = "";
		if (seen.repeats)
		{
			snprintf(rep, sizeof(rep), " [previous result repeated %u time(s)]", seen.repeats);
		}
		Logger::Get().WriteLine(LogLevel::Info,
			"UiSpike: %s snap terrainDim=%ld slot=%ldx%ld ceiling=%ld -> %ld (%s)%s",
			who, (long)terrainDim, (long)curW, (long)curH, (long)ceiling, (long)snap,
			terrainDim <= want ? "multiple" : "DIVISOR", rep);
		seen.map = pMap; seen.dim = terrainDim; seen.w = curW; seen.h = curH;
		seen.snap = snap; seen.repeats = 0;
	}

	// LEAVING THE WINDOW OVERSIZED IS NOT AN OPTION. Tried 2026-08-06: skip
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
	// GZWinMoveTo IS A RELATIVE MOVE. MEASURED 2026-08-06, THE HARD WAY.
	//
	// The name and the header (`GZWinMoveTo(int32_t x, int32_t y)`,
	// cIGZWin.h:137) both read like an absolute placement, so this was
	// "corrected" from the original delta form to seat+delta. MEASURED RESULT,
	// from this function's own new log line plus the player's screenshot:
	//     seat (27,108) 96x96 -> asked for (43,124)
	// (27,108) is exactly the recess origin (18*1.5=27), so (43,124) would have
	// been dead centre had the call been absolute. The map instead rendered
	// BELOW the recess, over the date field - i.e. it moved BY (43,124) from
	// (27,108). The original delta form was right all along.
	//
	// THE LESSON, and it is the expensive one: a header signature is not a
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

		// MARK THE WHOLE DIRTY MASK. THE GAME'S OWN "MARK ALL" ONLY MARKS A
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
		// MARKING MORE THAN EXISTS IS SAFE: the bake iterates tilesX/tilesY
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
	// That is the "corrupted image still behind it" the player reported: not
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
	// (The v2.72.3 ancestor paint-buffer probe was deleted in v2.73.0 as an
	// invalid instrument: REGRESSION.md [CC-14].)
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
// city tile, i.e. 128. The uncovered 64px band is the "garbage" the player sees -
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
// compositor scales 128 -> 192. Soft, which the player has accepted.
//
// WHY THIS IS SAFE HERE AND NOT ON THE DATA VIEWS MAP. The #109 faulting chain
// (0x007A2F60) resolves its target with `push 0xCA318385 / push 0x4203` - window
// id 0x4203, the Data Views map, EXCLUSIVELY. The dock minimap is 0x0BC3B559 and
// never enters that chain; it sat at window 192 / blit 128 for this entire
// session without ever crashing.
namespace UiSpikeInternal
{
	// #126 minimap draw hook counters. ScaleAllPanels (UiSpike.cpp) logs
	// these three, so they are shared (UiSpikeInternal.h).
	int      gMmStretches = 0;   // EXECUTED counter (law 47)
	int      gMmEntries = 0;     // thunk CALLED counter (see MmDrawThunk)
	int      gMmHooked = 0;      // INSTALLED counter
}

namespace
{
	bool     gMmFirstFireLogged = false;
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
}

namespace UiSpikeInternal
{
	// Per-instance vtable COPY - the class vtable itself is never written
	// (same discipline as the GZWinBMP hook in UiSpike.cpp).
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
void UiSpike::TryRecreateMinimapSurface(cIGZWin* pDock)
{
	if (!pDock) { return; }
	cIGZWin* pMM = pDock
		? pDock->GetChildWindowFromIDRecursive(0x0BC3B559) : nullptr;
	// WHAT THIS CHECK CAN AND CANNOT PROVE (corrected v2.41.7 by the
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
	// v2.73.3 (#126): the dock minimap is SNAPPED to the bake size. The
	// v2.73.0 stretch was refuted on screen (see the tombstone in MmDrawThunk
	// and REGRESSION.md [CC-15]), and a correct 128 map in a 192 recess beats a
	// torn 192 one. The remaining 32px ring of BAKED FAKE MAP in the dock
	// artwork is an ART defect and gets an ART fix - see #126.
	if (pMM && pMM->GetW() > 64) { SnapMiniMapToBake(pMM, "MINIMAP"); }
	if (pMM) { HookMiniMapDraw(pMM, "MINIMAP"); }
	// THE `> 64` WAS A MAGIC LITERAL THAT EXCLUDED EXACTLY ONE TIER.
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
	// HONEST STATUS: this is the best-supported hypothesis, not a proof. The
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
