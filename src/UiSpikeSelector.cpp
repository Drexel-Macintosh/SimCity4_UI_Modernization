////////////////////////////////////////////////////////////////////////////
//
// UiSpikeSelector - the in-game scale selector (the Graphic Options
// dialog's scale, mode and resolution rows): the v3.14 state machine.
//
// Split out of UiSpike.cpp verbatim (audit B11, 2026-09-25). It shares only
// gReadoutW/gReadoutH and SafeAbsRect with the rest of UiSpike
// (UiSpikeInternal.h), and _tests\Test-SelectorContract.py reads this file.
//
////////////////////////////////////////////////////////////////////////////

#include "UiSpike.h"
#include "UiSpikeInternal.h"

#include "Logger.h"
#include "ScaleTier.h"   // the selector greys out tiers this resolution cannot carry
#include "IniCache.h"    // audit B8: every read of our ini, one parse
#include "RoundHalfUp.h"

#include "cIGZWin.h"
#include "cIGZString.h"
#include "cIGZWinText.h"
#include "cIGZWinBtn.h"     // radio state
#include "cIGZWinCombo.h"   // the tier picker
#include "cIGZWinGen.h"     // SetWinProc/GetWinProc on the dialog
#include "cIGZWinProc.h"    // the chained click handler
#include "cIGZWinMessageFilter.h"  // per-BUTTON message filter
#include "cGZMessage.h"
#include "cRZBaseString.h"
#include "cISC4App.h"
#include "GZServPtrs.h"      // cISC4AppPtr

#include <cmath>
#include <cstdlib>
#include <cstring>
#include <cstdio>
#include <string>
#include <Windows.h>

using UiSpikeInternal::gReadoutW;
using UiSpikeInternal::gReadoutH;
using UiSpikeInternal::SafeAbsRect;

// ============ IN-GAME SCALE SELECTOR (v3.14 STATE MACHINE) ==============
// One source of truth, one pure derivation, event-driven application.
//
// The v3.13 selector grew by accretion into a ~1,400-line per-250ms
// function carrying six generations of mechanism, several measured dead
// but still executing. v3.14 replaces it with:
//
//   SelState   ALL facts, read at defined moments: session facts cached
//              once per session (display enumeration, live mode, package
//              census), visit facts read ONCE per dialog open (the two
//              inis, the dll, the render size), and the player's staged
//              requests, reset per visit.
//   SelDerive  ONE pure function state -> the entire UI. No side effects,
//              no syscalls, no logging. Every rule lives here and only
//              here. SPEC: _tests\Test-SelectorDerive.py was written
//              FIRST and this function mirrors it row for row.
//   SelApply   DIFF-APPLY: a combo is rebuilt only when its derived rows
//              differ from what was last pushed, and only on a tick where
//              a selection changed - which implies every drop list is
//              closed, so a rebuild can never mutate an open drop.
//   SelOnClose COMMIT AT CLOSE: Accept is the only exit (Cancel and
//              Default ship disabled), so a close re-reads the controls
//              and writes only keys whose values changed.
//
// THE PINNED DESIGN: the player's scale pick is a REQUEST that is never
// overwritten; the EFFECTIVE row derives fresh every pass as "request if
// usable else Auto". Bounce and un-bounce need no state machine at all.
//
// SHAPE GATE: _tests\Test-SelectorContract.py asserts the structure above
// on this source (writes only at close, no syscalls in the tick path,
// RemoveAllStrings only in the diff-apply).
//
// STRIPPED in v3.14, each measured dead in the v3.13.x logs (ledger):
// the SELHIT coordinate trace, the SELMSG message trace, the SELCAL
// calibration, the chained SelectorWinProc (its only outputs fed dead
// paths), and the gfx-ini-stamp Accept detector (3 Accepts, 3 "no write
// ever seen"). KEPT, quieted: the SELBTN button filters - they name the
// closing button in SELCLOSE.
namespace
{
	// Row order MUST match the listelement order the builder writes.
	const float kSelFactors[] = { 0.0f, 1.0f, 1.5f, 2.0f, 3.0f }; // [0] = Auto
	const char* const kSelLabels[] = { "Auto", "1x", "1.5x", "2x", "3x" };
	const int   kSelCount =
		static_cast<int>(sizeof(kSelFactors) / sizeof(kSelFactors[0]));
	// THE "needs WxH" NUMBERS ARE READ FROM ScaleTier's table, never a
	// second copy of the arithmetic - the caption is a promise to the
	// player, and the boot path enforces the table (law: two copies of a
	// rule are two rules).
	void SelMinimumFor(int k, int* w, int* h)
	{
		*w = 0; *h = 0;
		ScaleTier::TierMinimum(kSelFactors[k], w, h);
	}

	// The four stock resolution radios and our custom-resolution radio
	// (0x5CA1E002) are GONE as of v3.14.3: the stock four ship hidden in
	// data, and ours was generation-1 furniture the state machine made dead
	// (our close-time commit owns SC4GraphicsOptions.ini; the game never
	// rewrites it on Accept - measured). The builder comment carries the
	// full rationale.
	const uint32_t kSelDlgId    = 0x2A57CB82;   // Graphic Options root (GZWinGen)
	const uint32_t kSelReadoutId = 0x5CA1E000;
	const uint32_t kSelLabelId   = 0x5CA1E003;
	const uint32_t kSelComboId   = 0x5CA1E004;
	const uint32_t kSelResComboId  = 0x5CA1E006;
	const uint32_t kSelModeLabelId = 0x5CA1E007;
	const uint32_t kSelModeComboId = 0x5CA1E008;
	const uint32_t kSelResLabelId  = 0x5CA1E00B;
	// The game's OWN "takes effect next restart" popup, born hidden inside
	// this dialog. We never show it (the information lives in the combo
	// captions instead - a popup at the moment of CHANGE appears before the
	// player has agreed to anything); the watch below only ever sees a rise
	// the GAME caused, and the 10s net guarantees it cannot trap the player.
	const uint32_t kSelNoticeId  = 0x2A57CB83;

	// THREE MODES, ALPHABETICAL, AND NAMED - not positional.
	//   0 Borderless  a window covering the screen. NO display-mode change,
	//                 so nothing needs restoring on exit and alt-tab is
	//                 instant. The game's own ini says WindowWidth/Height
	//                 are IGNORED here - which is why the resolution
	//                 control offers a single row in this mode. Recommended.
	//   1 Fullscreen  exclusive; CHANGES THE DISPLAY MODE to the chosen
	//                 resolution, which is why the desktop visibly resizes.
	//   2 Windowed    a plain window at the chosen size.
	// The names are the contract, and the raw 0/1/2 appear nowhere.
	const int kModeBorderless = 0;
	const int kModeFullscreen = 1;
	const int kModeWindowed   = 2;
	const char* const kSelModeLabels[] = { "Borderless", "Fullscreen", "Windowed" };
	const int kSelModeCount = 3;

	struct SelRes { int w, h; };
	const int kSelResMax = 24;

	// ONE familiar-size table for every branch that offers resolutions.
	// (Law 94: hand-lists rot fastest when duplicated.)
	const SelRes kSelFamiliar[] = {
		{ 3840, 2160 }, { 2560, 1600 }, { 2560, 1440 }, { 2400, 1600 },
		{ 1920, 1200 }, { 1920, 1080 }, { 1600, 1200 }, { 1280, 1024 },
		{ 1024, 768 }, { 800, 600 }
	};
	const int kSelFamiliarN =
		static_cast<int>(sizeof(kSelFamiliar) / sizeof(kSelFamiliar[0]));

	// ---- SESSION FACTS: the display, enumerated ONCE -------------------
	// EnumDisplaySettingsW costs 3,264ms on this machine (dgVoodoo sits
	// between us and the driver) - measured by the v3.13.2 instrument, all
	// of it on the first click. The warm thread kicks it at DLL load, the
	// tri-state handshake keeps the UI thread safe at any moment, and since
	// the 2026-09-25 audit (A4) a disk cache skips the enumeration entirely
	// while the display is unchanged.
	SelRes gSelModeCache[64];
	int  gSelModeCacheN = 0;
	volatile LONG gSelEnumState = 0;   // 0 = idle, 1 = enumerating, 2 = done
	int  gSelCapW = 0, gSelCapH = 0;   // largest mode the panel reports
	int  gSelDeskW = 0, gSelDeskH = 0; // the registry desktop mode

	// ---- A4 (audit 2026-09-25): THE MODE LIST IS CACHED ON DISK ------------
	// MEASURED in game: "SELRES display enumerated ONCE in 5901ms - 31
	// distinct mode(s)" - ~655 EnumDisplaySettingsW calls at 4-14 ms each
	// under the game (37-101 ms for all of them in a clean 32-bit process).
	// The warm thread hid most of that, but a Graphic Options open inside the
	// first ~6 s still waited on it, and it competed with boot for all 6 s.
	//
	// The list only changes when the display does, so it is cached in
	// SC4UIScale-DisplayModes.txt (our folder), keyed by a hash of the primary
	// adapter's and monitor's device ids plus the desktop mode (w, h, bpp,
	// Hz). The desktop mode itself is always read live - one call, the same
	// ENUM_REGISTRY_SETTINGS read the key needs. A miss enumerates in full
	// (never stopping early: the largest mode needs the whole list), and the
	// warm thread drops to low priority first. Deleting the file just forces
	// one re-enumeration.
	const wchar_t kSelModeCacheFile[] = L"SC4UIScale-DisplayModes.txt";

	void SelHashW(uint64_t& h, const wchar_t* s)
	{
		for (; *s; s++)
		{
			h ^= static_cast<uint64_t>(*s);
			h *= 1099511628211ull;   // FNV-1a 64
		}
		h ^= 0xFF;
		h *= 1099511628211ull;       // field separator
	}

	// Hash, not the ids: the cache file never holds hardware identifiers.
	uint64_t SelDisplayKey(const DEVMODEW& desk)
	{
		uint64_t h = 1469598103934665603ull;
		DISPLAY_DEVICEW ad = {};
		ad.cb = sizeof(ad);
		for (DWORD i = 0; EnumDisplayDevicesW(nullptr, i, &ad, 0); i++)
		{
			if (ad.StateFlags & DISPLAY_DEVICE_PRIMARY_DEVICE) { break; }
			ad = {};
			ad.cb = sizeof(ad);
		}
		SelHashW(h, ad.DeviceID);
		SelHashW(h, ad.DeviceString);
		DISPLAY_DEVICEW mon = {};
		mon.cb = sizeof(mon);
		if (ad.DeviceName[0] && EnumDisplayDevicesW(ad.DeviceName, 0, &mon, 0))
		{
			SelHashW(h, mon.DeviceID);
		}
		wchar_t modeStr[64];
		swprintf_s(modeStr, L"%lux%lux%lu@%lu",
			desk.dmPelsWidth, desk.dmPelsHeight, desk.dmBitsPerPel,
			desk.dmDisplayFrequency);
		SelHashW(h, modeStr);
		return h;
	}

	// True when the file holds a complete list for this key.
	bool SelLoadModeCache(uint64_t key)
	{
		wchar_t path[MAX_PATH];
		ScaleTier::GetOurFilePathW(kSelModeCacheFile, path, MAX_PATH);
		FILE* f = nullptr;
		if (!path[0] || _wfopen_s(&f, path, L"r") != 0 || !f) { return false; }
		char line[128];
		unsigned long long fileKey = 0;
		bool keyOk = false, ended = false;
		int capW = 0, capH = 0, n = 0;
		SelRes modes[64] = {};
		while (fgets(line, sizeof(line), f))
		{
			int w = 0, h = 0;
			if (sscanf_s(line, "key=%llx", &fileKey) == 1) { keyOk = (fileKey == key); }
			else if (sscanf_s(line, "cap=%dx%d", &w, &h) == 2) { capW = w; capH = h; }
			else if (sscanf_s(line, "mode=%dx%d", &w, &h) == 2)
			{
				if (w > 0 && h > 0 && n < 64) { modes[n].w = w; modes[n].h = h; n++; }
			}
			else if (strncmp(line, "end", 3) == 0) { ended = true; }
		}
		fclose(f);
		// "end" proves the file is whole: a write cut short misses, it never
		// hands out half a list.
		if (!keyOk || !ended || n <= 0 || capW <= 0 || capH <= 0) { return false; }
		for (int k = 0; k < n; k++) { gSelModeCache[k] = modes[k]; }
		gSelModeCacheN = n;
		gSelCapW = capW;
		gSelCapH = capH;
		return true;
	}

	void SelSaveModeCache(uint64_t key)
	{
		wchar_t path[MAX_PATH];
		ScaleTier::GetOurFilePathW(kSelModeCacheFile, path, MAX_PATH);
		FILE* f = nullptr;
		if (!path[0] || _wfopen_s(&f, path, L"w") != 0 || !f) { return; }
		fprintf(f, "# SC4UIScale display-mode cache (audit A4). Rebuilt when the "
			"display changes; safe to delete.\nkey=%016llx\ncap=%dx%d\n",
			static_cast<unsigned long long>(key), gSelCapW, gSelCapH);
		for (int k = 0; k < gSelModeCacheN; k++)
		{
			fprintf(f, "mode=%dx%d\n", gSelModeCache[k].w, gSelModeCache[k].h);
		}
		fputs("end\n", f);
		fclose(f);
	}

	// lowerOnMiss: the warm thread's call - a miss drops that thread to low
	// priority before the long enumeration. Never set from the UI thread.
	void SelEnumOnce(bool lowerOnMiss = false)
	{
		if (gSelEnumState == 2) { return; }
		const LONG prev = InterlockedCompareExchange(&gSelEnumState, 1, 0);
		if (prev == 2) { return; }
		if (prev == 1)
		{
			// The warm thread is mid-enumeration. WAIT for its answer rather
			// than race it into the same arrays - this can only happen if the
			// dialog is opened within seconds of DLL load, which the game's
			// own load screens make practically impossible; the wait is a
			// correctness net, not an expected path.
			while (gSelEnumState != 2) { Sleep(5); }
			return;
		}
		const unsigned long long t0 = PerfProbe::NowUs();
		// The desktop mode, live, in one call - the key needs it and the
		// selector's desktop row is always the current one.
		DEVMODEW rd = {};
		rd.dmSize = sizeof(rd);
		const bool haveDesk = EnumDisplaySettingsW(nullptr, ENUM_REGISTRY_SETTINGS, &rd)
			&& rd.dmPelsWidth > 0;
		if (haveDesk)
		{
			gSelDeskW = static_cast<int>(rd.dmPelsWidth);
			gSelDeskH = static_cast<int>(rd.dmPelsHeight);
		}
		const uint64_t key = SelDisplayKey(rd);
		const bool cached = haveDesk && SelLoadModeCache(key);
		if (!cached)
		{
			if (lowerOnMiss)
			{
				SetThreadPriority(GetCurrentThread(), THREAD_PRIORITY_LOWEST);
			}
			DEVMODEW dm = {};
			dm.dmSize = sizeof(dm);
			for (DWORD i = 0; EnumDisplaySettingsW(nullptr, i, &dm); i++)
			{
				const int mw = static_cast<int>(dm.dmPelsWidth);
				const int mh = static_cast<int>(dm.dmPelsHeight);
				if (mw <= 0 || mh <= 0) { continue; }
				if (mw * mh > gSelCapW * gSelCapH) { gSelCapW = mw; gSelCapH = mh; }
				bool dup = false;
				for (int k = 0; k < gSelModeCacheN; k++)
				{
					if (gSelModeCache[k].w == mw && gSelModeCache[k].h == mh)
					{
						dup = true;
						break;
					}
				}
				if (!dup && gSelModeCacheN < 64)
				{
					gSelModeCache[gSelModeCacheN].w = mw;
					gSelModeCache[gSelModeCacheN].h = mh;
					gSelModeCacheN++;
				}
			}
			// Only a real list with a real key is worth keeping.
			if (haveDesk && gSelModeCacheN > 0 && gSelCapW > 0) { SelSaveModeCache(key); }
		}
		if (gSelCapW <= 0)
		{
			gSelCapW = GetSystemMetrics(SM_CXSCREEN);
			gSelCapH = GetSystemMetrics(SM_CYSCREEN);
		}
		if (gSelDeskW <= 0) { gSelDeskW = gSelCapW; gSelDeskH = gSelCapH; }
		// PUBLISH LAST: every reader gates on ==2, so the arrays above are
		// complete before anyone is allowed to see them.
		InterlockedExchange(&gSelEnumState, 2);
		Logger::Get().WriteLine(LogLevel::Info,
			"UiSpike: SELRES display modes %s in %llums - %d distinct "
			"mode(s), panel max %dx%d, desktop %dx%d.%s",
			cached ? "read from SC4UIScale-DisplayModes.txt" : "enumerated",
			(PerfProbe::NowUs() - t0) / 1000ull,
			gSelModeCacheN, gSelCapW, gSelCapH, gSelDeskW, gSelDeskH,
			cached ? "" : " Cached for the next launch (a full enumeration"
				" measured 5,901 ms in game).");
	}

	DWORD WINAPI SelEnumWarmThread(LPVOID)
	{
		SelEnumOnce(true);
		return 0;
	}

	void SelDisplayMax(int* w, int* h)
	{
		SelEnumOnce();
		*w = gSelCapW;
		*h = gSelCapH;
	}

	// The user's desktop mode - unaffected by whatever mode a fullscreen
	// game has temporarily put the display into (ENUM_REGISTRY_SETTINGS,
	// never the current metrics: in exclusive fullscreen those are the mode
	// THE GAME SET, which made the list a one-way ratchet).
	void SelDesktopMode(int* w, int* h)
	{
		SelEnumOnce();
		*w = gSelDeskW;
		*h = gSelDeskH;
	}

	// ---- PATHS -----------------------------------------------------------
	// SC4GraphicsOptions.ini belongs to a THIRD-PARTY DLL that lives at the
	// PLUGINS ROOT. v4.2.0: with our DLL in Plugins\010-SC4UIScale\, "beside
	// the DLL" would miss it (reads fall to defaults, and the selector would
	// WRITE an orphan ini into our folder that nothing reads) - so this
	// resolves against the real root, shared with ScaleTier. Every consumer
	// (SelReadGfxMode/Res, SelGraphicsDllPresent, SelWriteGraphicsIni) goes
	// through this one path source.
	void SelGfxIniPath(wchar_t* out, size_t outLen)
	{
		wchar_t path[MAX_PATH] = {};
		ScaleTier::GetPluginsRootW(path, MAX_PATH);
		swprintf_s(out, outLen, L"%sSC4GraphicsOptions.ini", path);
	}

	// The ini beside THIS dll - the same file Settings::Load read at startup.
	// Resolved here rather than reusing the director's helper because that
	// one is file-static to the director.
	void SelIniPath(wchar_t* out, size_t outLen)
	{
		ScaleTier::GetOurFilePathW(L"SC4UIScale.ini", out, outLen);
	}

	// dgVoodoo.conf sits BESIDE THE EXE (Apps\), not beside the DLL.
	void SelDgVoodooPath(wchar_t* out, size_t outLen)
	{
		wchar_t exe[MAX_PATH] = {};
		GetModuleFileNameW(nullptr, exe, MAX_PATH);
		wchar_t* slash = wcsrchr(exe, L'\\');
		if (slash) { *(slash + 1) = L'\0'; }
		swprintf_s(out, outLen, L"%sdgVoodoo.conf", exe);
	}

	// ---- VISIT FACTS, READ ONCE PER OPEN ----------------------------------
	// SC4GraphicsOptions.ini belongs to a THIRD-PARTY DLL (SC4Graphics-
	// Options.dll, a community plugin); dgVoodoo is a third component again.
	// On an install WITHOUT that DLL, WindowMode and WindowWidth/Height are
	// read by nobody - so the dll's presence is a visit fact and both
	// controls hide when it is absent. The scale selector is unaffected: it
	// writes our own ini, which we own.
	//
	// Parsed by ScaleTier::ReadGraphicsOptions, the reader the boot tier
	// decision uses (audit B8: this file used to carry its own copy of the
	// mode rules and parsed the ini twice per open). Vendored IniReader, as
	// the owning DLL; a missing file or a rejected line gives the defaults.
	ScaleTier::GraphicsOptions SelReadGfx()
	{
		PerfProbe::Scope perf_("sel.iniRead");
		return ScaleTier::ReadGraphicsOptions();
	}

	int SelModeOf(const ScaleTier::GraphicsOptions& g)
	{
		return (g.mode == ScaleTier::WindowMode::Windowed) ? kModeWindowed
			: (g.mode == ScaleTier::WindowMode::Borderless) ? kModeBorderless
			: kModeFullscreen;
	}

	// Our own ini's scale keys. Defaults mirror Settings::Load's.
	void SelReadOurScale(bool* autoScale, float* factor)
	{
		PerfProbe::Scope perf_("sel.iniRead");
		wchar_t p[MAX_PATH] = {};
		SelIniPath(p, MAX_PATH);
		*autoScale = IniCache::ReadIntW(L"UiSpike", L"AutoScale", 1, p) != 0;
		wchar_t f[32] = {};
		IniCache::ReadStringW(L"UiSpike", L"ScaleFactor", L"2", f, 32, p);
		*factor = static_cast<float>(_wtof(f));
	}

	bool SelGraphicsDllPresent()
	{
		PerfProbe::Scope perf_("sel.dllStat");
		wchar_t dir[MAX_PATH] = {};
		SelGfxIniPath(dir, MAX_PATH);
		wchar_t* slash = wcsrchr(dir, L'\\');
		if (slash == nullptr) { return false; }
		*(slash + 1) = 0;
		wchar_t dll[MAX_PATH] = {};
		swprintf_s(dll, L"%sSC4GraphicsOptions.dll", dir);
		return GetFileAttributesW(dll) != INVALID_FILE_ATTRIBUTES;
	}

	// ---- THE WRITERS (close path only - the contract gate asserts it) ----
	// NOT WritePrivateProfileString. dgVoodoo.conf is ini-SHAPED but its
	// keys are column-aligned ("FullScreenMode   = true") and the file
	// carries comments the wrapper's own tooling expects. A profile write
	// would reformat the line and could reorder the section. This rewrites
	// exactly the value token on the FullScreenMode line and touches
	// nothing else - and never adds a BOM, a standing law for every ini the
	// game or a wrapper reads.
	bool SelWriteDgVoodooFullScreen(bool fullscreen)
	{
		PerfProbe::Scope perf_("sel.dgWrite");
		wchar_t path[MAX_PATH] = {};
		SelDgVoodooPath(path, MAX_PATH);
		HANDLE h = CreateFileW(path, GENERIC_READ, FILE_SHARE_READ, nullptr,
			OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, nullptr);
		if (h == INVALID_HANDLE_VALUE) { return false; }
		DWORD size = GetFileSize(h, nullptr);
		if (size == INVALID_FILE_SIZE || size > (1u << 20))
		{
			CloseHandle(h);
			return false;
		}
		char* buf = new char[size + 1];
		DWORD got = 0;
		const BOOL ok = ReadFile(h, buf, size, &got, nullptr);
		CloseHandle(h);
		if (!ok) { delete[] buf; return false; }
		buf[got] = 0;

		// Find the FullScreenMode line - the one that ASSIGNS it, not the
		// commented ";InheritColorProfileInFullScreenMode:" nor
		// "InheritColorProfileInFullScreenMode", both of which contain the
		// same substring. Anchor on a line START.
		const char* want = "FullScreenMode";
		bool wrote = false;
		for (DWORD i = 0; i < got && !wrote; i++)
		{
			const bool atLineStart = (i == 0 || buf[i - 1] == '\n');
			if (!atLineStart) { continue; }
			if (strncmp(buf + i, want, 14) != 0) { continue; }
			// the '=' for this key
			DWORD j = i + 14;
			while (j < got && (buf[j] == ' ' || buf[j] == '\t')) { j++; }
			if (j >= got || buf[j] != '=') { continue; }
			j++;
			while (j < got && (buf[j] == ' ' || buf[j] == '\t')) { j++; }
			DWORD vEnd = j;
			while (vEnd < got && buf[vEnd] != '\r' && buf[vEnd] != '\n') { vEnd++; }
			const char* val = fullscreen ? "true" : "false";
			const size_t vLen = strlen(val);
			const size_t oldLen = vEnd - j;
			char* out = new char[got + vLen + 1];
			memcpy(out, buf, j);
			memcpy(out + j, val, vLen);
			memcpy(out + j + vLen, buf + vEnd, got - vEnd);
			const DWORD outLen = static_cast<DWORD>(got - oldLen + vLen);
			HANDLE hw = CreateFileW(path, GENERIC_WRITE, 0, nullptr,
				CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, nullptr);
			if (hw != INVALID_HANDLE_VALUE)
			{
				DWORD put = 0;
				wrote = WriteFile(hw, out, outLen, &put, nullptr) != 0;
				CloseHandle(hw);
			}
			delete[] out;
		}
		delete[] buf;
		Logger::Get().WriteLine(LogLevel::Info,
			"UiSpike: SELMODE dgVoodoo FullScreenMode -> %ls in %ls (%ls). "
			"This is the setting that actually decides windowing; the game's "
			"own WindowMode does nothing without it.",
			fullscreen ? L"true" : L"false", path,
			wrote ? L"written" : L"FAILED - the value stays as it was");
		return wrote;
	}

	void SelWriteGraphicsIni(int modeIdx, int w, int h)
	{
		PerfProbe::Scope perf_("sel.iniWrite");
		wchar_t p[MAX_PATH] = {};
		SelGfxIniPath(p, MAX_PATH);
		const wchar_t* modeStr = (modeIdx == kModeFullscreen) ? L"FullScreen"
			: (modeIdx == kModeBorderless) ? L"Borderless" : L"Windowed";
		wchar_t num[24] = {};
		if (w > 0 && h > 0)
		{
			swprintf_s(num, L"%d", w);
			IniCache::WriteStringW(L"GraphicsOptions", L"WindowWidth", num, p);
			swprintf_s(num, L"%d", h);
			IniCache::WriteStringW(L"GraphicsOptions", L"WindowHeight", num, p);
		}
		IniCache::WriteStringW(L"GraphicsOptions", L"WindowMode",
			modeStr, p);
		Logger::Get().WriteLine(LogLevel::Info,
			"UiSpike: SELMODE SC4GraphicsOptions.ini -> WindowMode=%ls "
			"WindowWidth=%d WindowHeight=%d.%ls",
			modeStr, w, h,
			(modeIdx == kModeBorderless)
				? L" (borderless ignores the size by the game's own rule - it "
				  L"is written so switching back to fullscreen or windowed "
				  L"still has one.)"
				: L"");
	}

	// ---- THE STATE --------------------------------------------------------
	struct SelState
	{
		// session facts (cached once per session, never re-read mid-session)
		int capW, capH;            // panel max mode
		int deskW, deskH;          // registry desktop mode
		const SelRes* modes;       // the panel's reported modes (cached)
		int modeN;
		bool pkg[8];               // tier package on disk (Auto/1x: always)
		int liveMode;              // the mode the game BOOTED with
		// visit facts (read ONCE per dialog open)
		int liveW, liveH;          // measured render size
		int iniMode, iniW, iniH;   // SC4GraphicsOptions.ini
		bool ourAuto; float ourFactor;   // our ini (AutoScale/ScaleFactor)
		bool dll;                  // SC4GraphicsOptions.dll present
		// the player's staged requests (this visit only; -1 = untouched)
		int sMode, sRes, sScale;   // sScale is a REQUEST, never overwritten
	};

	struct SelUi
	{
		int effMode, effW, effH;   // the one future the commit will write
		int effScale;
		bool bounced;              // the request does not fit; Auto derived
		int modeSel;
		int resCount, resSel;
		SelRes res[kSelResMax];    // THE list - one index space, no dual
		char modeRows[kSelModeCount][80];
		char resRows[kSelResMax][80];
		char scaleRows[kSelCount][80];
	};

	// ---- THE PURE FUNCTION ------------------------------------------------
	// The FULL res list for a mode, largest first. ONE index space - the UI
	// shows exactly this, and the commit indexes exactly this (the v3.13
	// two-index-space defect is structurally gone).
	//   BORDERLESS  the desktop, and only that - the game documents
	//               WindowWidth/Height as ignored here; a control with no
	//               effect must not look like a choice.
	//   FULLSCREEN  familiar sizes INTERSECTED with what the panel reports
	//               (an unsupported mode in exclusive fullscreen is a black
	//               screen, not a cosmetic problem; and the raw enumeration
	//               grows a scrollbar that draws magenta). The desktop mode
	//               is always legal even if no familiar table carries it -
	//               a 3:2 panel's native size is in nobody's list.
	//   WINDOWED    familiar sizes that fit the desktop, EXCLUDING the
	//               desktop-equal size: a desktop-sized window overflows the
	//               screen once its title bar exists, and "fill the screen
	//               with a window" is Borderless's job. No mode check - a
	//               window needs no display mode. (v3.13.2 measured the old
	//               C++ had NO windowed branch at all; the spec pins this.)
	int SelBuildResRows(const SelState& st, int mode, SelRes* out)
	{
		int n = 0;
		if (mode == kModeBorderless)
		{
			if (st.deskW > 0 && st.deskH > 0)
			{
				out[0].w = st.deskW;
				out[0].h = st.deskH;
				n = 1;
			}
			return n;
		}
		if (mode == kModeFullscreen)
		{
			for (int f = 0; f < kSelFamiliarN && n < 7; f++)
			{
				const int w = kSelFamiliar[f].w;
				const int h = kSelFamiliar[f].h;
				if (st.capW > 0 && (w > st.capW || h > st.capH)) { continue; }
				bool supported = false;
				for (int k = 0; k < st.modeN; k++)
				{
					if (st.modes[k].w == w && st.modes[k].h == h)
					{
						supported = true;
						break;
					}
				}
				if (!supported) { continue; }
				out[n].w = w;
				out[n].h = h;
				n++;
			}
			if (st.deskW > 0 && st.deskH > 0 && n < kSelResMax)
			{
				bool have = false;
				for (int k = 0; k < n; k++)
				{
					if (out[k].w == st.deskW && out[k].h == st.deskH)
					{
						have = true;
						break;
					}
				}
				if (!have) { out[n].w = st.deskW; out[n].h = st.deskH; n++; }
			}
		}
		else   // WINDOWED - and this branch MUST exist (v3.13.2 measured 0 rows).
		{
			for (int f = 0; f < kSelFamiliarN && n < 7; f++)
			{
				const int w = kSelFamiliar[f].w;
				const int h = kSelFamiliar[f].h;
				if (st.deskW > 0 && (w > st.deskW || h > st.deskH)) { continue; }
				if (w == st.deskW && h == st.deskH) { continue; }
				out[n].w = w;
				out[n].h = h;
				n++;
			}
		}
		// Largest first, so the list reads the way the stock one does.
		for (int a = 0; a < n; a++)
		{
			for (int b = a + 1; b < n; b++)
			{
				if (out[b].w * out[b].h > out[a].w * out[a].h)
				{
					const SelRes t = out[a];
					out[a] = out[b];
					out[b] = t;
				}
			}
		}
		return n;
	}

	// SelDerive: state -> the entire UI. PURE - no side effects, no
	// syscalls, no logging (the contract gate asserts the shape). Mirrors
	// _tests\Test-SelectorDerive.py, which was written first.
	void SelDerive(const SelState& st, SelUi* ui)
	{
		ui->effMode = 0; ui->effW = 0; ui->effH = 0;
		ui->effScale = 0; ui->bounced = false; ui->modeSel = 0;
		ui->resCount = 0; ui->resSel = 0;
		for (int i = 0; i < kSelModeCount; i++) { ui->modeRows[i][0] = 0; }
		for (int i = 0; i < kSelResMax; i++) { ui->resRows[i][0] = 0; }
		for (int i = 0; i < kSelCount; i++) { ui->scaleRows[i][0] = 0; }

		// -- the pending future already in the files -----------------------
		// In F/W the game renders the requested size, so ini != live means a
		// restart-pending change (an earlier Accept, or a hand edit - same
		// thing). In B the ini size is documented-ignored, so only the MODE
		// can be pending.
		const bool pending = (st.iniMode != st.liveMode)
			|| (st.iniMode != kModeBorderless
				&& (st.iniW != st.liveW || st.iniH != st.liveH));
		const int baseMode = pending ? st.iniMode : st.liveMode;
		ui->effMode = (st.sMode >= 0) ? st.sMode : baseMode;
		ui->modeSel = ui->effMode;

		ui->resCount = SelBuildResRows(st, ui->effMode, ui->res);

		// -- effective resolution ------------------------------------------
		if (ui->effMode == kModeBorderless)
		{
			// The DESKTOP, whatever the resolution control says.
			ui->effW = st.deskW;
			ui->effH = st.deskH;
			ui->resSel = 0;
		}
		else
		{
			if (st.sRes >= 0 && st.sRes < ui->resCount)
			{
				ui->resSel = st.sRes;
			}
			else
			{
				const bool useIni = pending && st.iniMode == ui->effMode;
				const int baseW = useIni ? st.iniW : st.liveW;
				const int baseH = useIni ? st.iniH : st.liveH;
				int found = -1;
				for (int i = 0; i < ui->resCount; i++)
				{
					if (ui->res[i].w == baseW && ui->res[i].h == baseH)
					{
						found = i;
						break;
					}
				}
				// The base is not offered by this mode (switching to Windowed
				// at the desktop size is exactly that). The LARGEST the mode
				// offers is the closest thing to what the player had - rows
				// are largest-first, so row 0. Refusing to move here IS the
				// defect: the mode made the current value invalid.
				ui->resSel = (found >= 0) ? found : (ui->resCount - 1);
			}
			if (ui->resSel >= 0 && ui->resSel < ui->resCount)
			{
				ui->effW = ui->res[ui->resSel].w;
				ui->effH = ui->res[ui->resSel].h;
			}
		}
		// No owning dll: mode/res are hidden and the scale's fit question is
		// asked against what is RUNNING (spec mirror: eff_res = live).
		if (!st.dll)
		{
			ui->effW = st.liveW;
			ui->effH = st.liveH;
		}

		// -- scale: the REQUEST is never overwritten; effective is derived --
		int iniRow = 0;
		if (!st.ourAuto)
		{
			for (int k = 1; k < kSelCount; k++)
			{
				// Tier factors are exact halves/wholes; 0.01 sits far inside
				// the smallest gap between any two of them.
				if (st.ourFactor > kSelFactors[k] - 0.01f
					&& st.ourFactor < kSelFactors[k] + 0.01f)
				{
					iniRow = k;
					break;
				}
			}
		}
		const int request = (st.sScale >= 0) ? st.sScale : iniRow;
		bool usable[kSelCount];
		for (int k = 0; k < kSelCount; k++)
		{
			// PACKAGE FIRST, THEN FIT - offering a tier whose art is not
			// installed makes the escape hatch WRITE THE TRAP (the boot
			// validator bounces it back to Auto). Same predicate the boot
			// path uses, so the selector and the validator never disagree.
			// An unmeasured render size is not evidence of a small screen.
			usable[k] = (k <= 1) ? true
				: st.pkg[k] && (ui->effW <= 0 || ui->effH <= 0
					|| ScaleTier::Fits(kSelFactors[k], ui->effW, ui->effH));
		}
		const bool requestValid =
			(request >= 0 && request < kSelCount && usable[request]);
		ui->effScale = requestValid ? request : 0;   // bounce is DERIVED
		ui->bounced = (request != ui->effScale);

		// -- captions: "(current)" = running now, "- on restart" = chosen --
		for (int m = 0; m < kSelModeCount; m++)
		{
			const char* tag = (m == st.liveMode) ? " (current)"
				: (m == ui->effMode && (st.sMode >= 0 || pending))
					? " - on restart"
				: (m == kModeBorderless) ? " (recommended)" : "";
			_snprintf_s(ui->modeRows[m], _TRUNCATE, "%s%s",
				kSelModeLabels[m], tag);
		}
		for (int i = 0; i < ui->resCount; i++)
		{
			const SelRes& r = ui->res[i];
			const bool isCurrent = (ui->effMode != kModeBorderless)
				&& r.w == st.liveW && r.h == st.liveH
				&& st.liveMode == ui->effMode;
			const bool isChosen = (i == ui->resSel)
				&& (st.sRes >= 0 || pending);
			_snprintf_s(ui->resRows[i], _TRUNCATE, "%dx%d%s", r.w, r.h,
				isCurrent ? " (current)" : (isChosen ? " - on restart" : ""));
		}
		for (int k = 0; k < kSelCount; k++)
		{
			if (!usable[k])
			{
				// Say WHAT IT NEEDS, not just "no". A control that refuses
				// without explaining itself is a bug report.
				int mw = 0, mh = 0;
				SelMinimumFor(k, &mw, &mh);
				_snprintf_s(ui->scaleRows[k], _TRUNCATE, "%s - needs %dx%d",
					kSelLabels[k], mw, mh);
			}
			else if (k == ui->effScale)
			{
				// THE EFFECTIVE RESOLUTION, NOT THE RUNNING ONE: the two
				// controls must describe the SAME future.
				_snprintf_s(ui->scaleRows[k], _TRUNCATE, "%s @ %dx%d",
					kSelLabels[k], ui->effW, ui->effH);
			}
			else
			{
				_snprintf_s(ui->scaleRows[k], _TRUNCATE, "%s", kSelLabels[k]);
			}
		}
	}

	// ---- DIFF-APPLY --------------------------------------------------------
	// What we last pushed into each combo. A rebuild happens ONLY when the
	// derived rows differ from this cache, and RemoveAllStrings exists in
	// exactly one function (the contract gate asserts both).
	char gSelPushedScale[kSelCount][80];
	int  gSelPushedScaleN = 0;
	char gSelPushedRes[kSelResMax][80];
	int  gSelPushedResN = 0;
	char gSelPushedMode[kSelModeCount][80];
	int  gSelPushedModeN = 0;
	// The selections we last applied - the poll's baseline. A GetSelection
	// that differs from this is the player's event.
	int  gSelAppliedScale = -1, gSelAppliedRes = -1, gSelAppliedMode = -1;

	bool SelRowsDiffer(const char (*pushed)[80], int pushedN,
		const char (*rows)[80], int n)
	{
		if (pushedN != n) { return true; }
		for (int i = 0; i < n; i++)
		{
			if (strcmp(pushed[i], rows[i]) != 0) { return true; }
		}
		return false;
	}

	void SelPushCombo(cIGZWinCombo* c, const char (*rows)[80], int n,
		char (*cache)[80], int* cacheN, int sel, int* appliedSel)
	{
		if (SelRowsDiffer(cache, *cacheN, rows, n))
		{
			PerfProbe::Scope perf_("sel.rebuild");
			// Safe to rebuild: this runs on OPEN (nothing is down yet) or on
			// the tick a selection CHANGED - which implies this combo's drop
			// list just closed, and only one drop can be open at a time.
			c->RemoveAllStrings();
			for (int i = 0; i < n; i++)
			{
				cRZBaseString rs(rows[i]);
				c->InsertString(rs, i);
			}
			for (int i = 0; i < n; i++)
			{
				strcpy_s(cache[i], 80, rows[i]);
			}
			*cacheN = n;
			if (sel >= 0 && sel < n) { c->SetSelection(sel, false); }
			*appliedSel = sel;
		}
		else
		{
			const int cur = c->GetSelection();
			if (sel >= 0 && sel < n && cur != sel)
			{
				c->SetSelection(sel, false);
				*appliedSel = sel;
			}
			else
			{
				*appliedSel = cur;
			}
		}
	}

	// ---- VISIT STATE -------------------------------------------------------
	SelState gSelState;
	bool gSelDlgUp = false;
	cIGZWin* gSelDlgLast = nullptr;
	unsigned int gSelLastMs = 0;
	int  gSelLogs = 0;
	bool gSelNoGfxDllLogged = false;
	bool gSelBounced = false;      // last apply ended with the request bounced
	// Session facts captured lazily on first open.
	int  gSelLiveMode = -1;        // the mode the game BOOTED with: the ini
	                               // changes the moment a choice commits, so
	                               // only a first-open read answers "what am
	                               // I running", never "what will apply".
	bool gSelPkg[8] = { true, true, false, false, false, false, false, false };
	bool gSelPkgCached = false;
	// Notice watch + net.
	bool gSelNoticeWasUp = false;
	unsigned int gSelNoticeShownMs = 0;
	// The pre-dialog resolution rescue (RESMISMATCH), once per session.
	bool gSelResRescued = false;

	// ---- THE BUTTONS, ASKED DIRECTLY ---------------------------------------
	// cIGZWin::AddMessageFilter attaches to ANY window - including each
	// button - and DoMessage is handed the window the message went to, so a
	// click identifies its own button by POINTER IDENTITY. One filter serves
	// all four buttons; it never consumes anything (returns false), and
	// gSelLastBtn is what SELCLOSE reads to name the closing button.
	struct SelBtnSlot { uint32_t id; const char* name; cIGZWin* win; };
	SelBtnSlot gSelBtns[] = {
		{ 0xEA57DA59u, "ACCEPT",           nullptr },
		{ 0x6A57DA48u, "CANCEL",           nullptr },
		{ 0xEA5E99D9u, "DEFAULT SETTINGS", nullptr },
		{ 0xEA57DA6Fu, "NOTICE-ACCEPT",    nullptr },
	};
	const int kSelBtnCount =
		static_cast<int>(sizeof(gSelBtns) / sizeof(gSelBtns[0]));

	int  gSelLastBtn = -1;
	int  gSelBtnLogs = 0;
	bool gSelFiltersOn = false;

	class SelBtnFilter : public cIGZWinMessageFilter
	{
	public:
		SelBtnFilter() : refCount(0) {}

		bool QueryInterface(uint32_t riid, void** ppvObj) override
		{
			if (riid == GZIID_cIGZWinMessageFilter)
			{
				*ppvObj = static_cast<cIGZWinMessageFilter*>(this);
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
			// Never self-deletes: a DLL-lifetime singleton, and a
			// use-after-free here would land inside the game's message pump.
			if (refCount > 0) { --refCount; }
			return refCount;
		}

		bool DoMessage(cIGZWin* pWin, cGZMessage& msg) override
		{
			PerfProbe::Scope perf_("sel.btnFilter");
			for (int i = 0; i < kSelBtnCount; i++)
			{
				if (gSelBtns[i].win != nullptr && gSelBtns[i].win == pWin)
				{
					// EVERY message updates the tracker - SELCLOSE needs the
					// last button touched whatever the type. The LOG is
					// quieted (v3.14): enter and click only, never the move
					// storm, tiny budget.
					gSelLastBtn = i;
					if ((msg.dwMessageType == 0x13
							|| msg.dwMessageType == 0x10)
						&& gSelBtnLogs < 20)
					{
						gSelBtnLogs++;
						Logger::Get().WriteLine(LogLevel::Info,
							"UiSpike: SELBTN  %-16s got type=0x%08X "
							"d1=0x%08X d2=0x%08X d3=0x%08X",
							gSelBtns[i].name, msg.dwMessageType,
							msg.dwData1, msg.dwData2, msg.dwData3);
					}
					break;
				}
			}
			// OBSERVE ONLY. Returning true here could swallow the click and
			// break the game's own Accept.
			return false;
		}

	private:
		uint32_t refCount;
	};

	SelBtnFilter gSelBtnFilter;

	void SelAttachButtonFilters(cIGZWin* gfxDlg)
	{
		int found = 0;
		for (int i = 0; i < kSelBtnCount; i++)
		{
			cIGZWin* w = gfxDlg->GetChildWindowFromIDRecursive(gSelBtns[i].id);
			gSelBtns[i].win = w;
			if (w != nullptr)
			{
				w->AddMessageFilter(&gSelBtnFilter);
				found++;
			}
		}
		gSelFiltersOn = found > 0;
		gSelLastBtn = -1;
		Logger::Get().WriteLine(LogLevel::Info,
			"UiSpike: SELBTN attached a message filter to %d of %d buttons "
			"(Accept 0x%08X, Cancel 0x%08X, Default 0x%08X, notice-Accept "
			"0x%08X). Enter and click are named in the log; the closing "
			"button is named by SELCLOSE.",
			found, kSelBtnCount, gSelBtns[0].id, gSelBtns[1].id,
			gSelBtns[2].id, gSelBtns[3].id);
	}

	void SelDetachButtonFilters()
	{
		if (!gSelFiltersOn) { return; }
		for (int i = 0; i < kSelBtnCount; i++)
		{
			if (gSelBtns[i].win != nullptr)
			{
				gSelBtns[i].win->RemoveMessageFilter(&gSelBtnFilter);
				gSelBtns[i].win = nullptr;
			}
		}
		gSelFiltersOn = false;
	}

	// ---- THE FREEZE INSTRUMENT (kept in the build) -------------------------
	// v3.13.2's instrument named the freeze in one launch; it stays armed.
	// In-memory buckets only (the leading suspect WAS synchronous file I/O -
	// an instrument must not be made of the thing it measures). FRAME GAP:
	// entry-to-entry stride while the dialog is up. PASS: one service pass
	// over 25ms names its contributors. Table dumped on close + shutdown.
	int gSelPerfGapLogs = 0;
	int gSelPerfPassLogs = 0;
	unsigned long long gSelPerfPrevCallUs = 0;
	PerfProbe::Row gSelPerfPrevRows[32];
	int gSelPerfPrevRowN = 0;

	int SelPerfDelta(const PerfProbe::Row* prev, int prevN, char* out, int cap)
	{
		PerfProbe::Row now[32];
		const int n = PerfProbe::Snapshot(now, 32);
		int off = 0;
		out[0] = 0;
		for (int i = 0; i < n && off < cap - 40; i++)
		{
			unsigned long long pTot = 0;
			unsigned int pCnt = 0;
			for (int j = 0; j < prevN; j++)
			{
				if (prev[j].name == now[i].name)
				{
					pTot = prev[j].totalUs;
					pCnt = prev[j].count;
					break;
				}
			}
			const unsigned long long dUs = now[i].totalUs - pTot;
			if (dUs >= 1000ull)
			{
				off += _snprintf_s(out + off, static_cast<size_t>(cap - off),
					_TRUNCATE, " %s=%llums/%u", now[i].name, dUs / 1000ull,
					now[i].count - pCnt);
			}
		}
		return off;
	}

	void SelPerfDump(const char* why)
	{
		PerfProbe::Row rows[32];
		const int n = PerfProbe::Snapshot(rows, 32);
		// Insertion sort by total, descending - 32 rows, no allocator.
		for (int i = 1; i < n; i++)
		{
			const PerfProbe::Row r = rows[i];
			int j = i - 1;
			while (j >= 0 && rows[j].totalUs < r.totalUs)
			{
				rows[j + 1] = rows[j];
				j--;
			}
			rows[j + 1] = r;
		}
		Logger::Get().WriteLine(LogLevel::Info,
			"UiSpike: SELPERF table (%s), per bucket since launch. A stall "
			"appearing in NO bucket happened outside the bracketed code.",
			why);
		for (int i = 0; i < n && i < 14; i++)
		{
			Logger::Get().WriteLine(LogLevel::Info,
				"UiSpike: SELPERF   %-16s n=%-6u total=%llu.%03llums "
				"max=%llu.%03llums",
				rows[i].name, rows[i].count,
				rows[i].totalUs / 1000ull, rows[i].totalUs % 1000ull,
				rows[i].maxUs / 1000ull, rows[i].maxUs % 1000ull);
		}
	}

	// RAII: times a whole service pass across its many early returns, and
	// names the in-pass contributors when a single pass stalls.
	struct SelPassWatch
	{
		unsigned long long t0;
		PerfProbe::Row rows[32];
		int n;
		SelPassWatch()
		{
			t0 = PerfProbe::NowUs();
			n = PerfProbe::Snapshot(rows, 32);
		}
		~SelPassWatch()
		{
			const unsigned long long dUs = PerfProbe::NowUs() - t0;
			PerfProbe::Add("sel.pass", dUs);
			if (dUs > 25000ull && gSelPerfPassLogs < 40)
			{
				gSelPerfPassLogs++;
				char detail[512];
				const int len = SelPerfDelta(rows, n, detail, sizeof(detail));
				Logger::Get().WriteLine(LogLevel::Info,
					"UiSpike: SELPERF pass took %llums. In-pass:%s",
					dUs / 1000ull,
					len ? detail
						: " (no bracket >=1ms - the time is in unbracketed "
						"code inside this pass)");
			}
		}
	};

	// ---- COMMIT (close handler only) ----------------------------------------
	void SelCommitScale(int row)
	{
		if (row < 0 || row >= kSelCount) { return; }
		PerfProbe::Scope perf_("sel.commit");
		wchar_t ini[MAX_PATH] = {};
		SelIniPath(ini, MAX_PATH);
		if (ini[0] == 0) { return; }

		// ScaleAll IS WRITTEN TOO, AND THAT CLOSES THE WORST TRAP FOUND.
		// The art and font layer is armed from the FACTOR, while every
		// geometry consumer is gated on ScaleAll - so with ScaleAll=0 every
		// choice made here was committed and then silently voided at the
		// next boot, forever. Picking a scale IS a request for scaling, so
		// the switch that enables it is part of the request. Stock (row 1)
		// is the one case that must not touch it: 1x is meant to be inert,
		// and a reference capture taken with ScaleAll=0 must stay that way.
		// Written only if off - the commit writes only changed keys.
		if (row != 1)
		{
			wchar_t cur[16] = {};
			IniCache::ReadStringW(L"UiSpike", L"ScaleAll", L"1", cur, 16, ini);
			if (_wtoi(cur) == 0)
			{
				IniCache::WriteStringW(L"UiSpike", L"ScaleAll", L"1", ini);
				Logger::Get().WriteLine(LogLevel::Info,
					"UiSpike: SELECTOR ScaleAll was %ls - written back as 1. "
					"Without it the tier's art and fonts arm while every "
					"geometry patch stays off, and nothing in this dialog "
					"could have repaired that.", cur);
			}
		}
		if (row == 0)
		{
			IniCache::WriteStringW(L"UiSpike", L"AutoScale", L"1", ini);
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
			IniCache::WriteStringW(L"UiSpike", L"AutoScale", L"0", ini);
			IniCache::WriteStringW(L"UiSpike", L"ScaleFactor", val, ini);
			Logger::Get().WriteLine(LogLevel::Info,
				"UiSpike: SELECTOR committed AutoScale=0 ScaleFactor=%ls to "
				"%ls. Applies at the next launch.", val, ini);
		}
	}

	// ---- THE THREE EVENTS ---------------------------------------------------
	void SelApply(cIGZWin* gfxDlg, const SelUi& ui)
	{
		PerfProbe::Scope perf_("sel.apply");
		cIGZWin* sc = gfxDlg->GetChildWindowFromIDRecursive(kSelComboId);
		if (sc != nullptr)
		{
			cIGZWinCombo* c = nullptr;
			if (sc->QueryInterface(GZIID_cIGZWinCombo,
					reinterpret_cast<void**>(&c)) && c)
			{
				SelPushCombo(c, ui.scaleRows, kSelCount, gSelPushedScale,
					&gSelPushedScaleN, ui.effScale, &gSelAppliedScale);
				c->Release();
			}
		}
		if (!gSelState.dll)
		{
			// READ-ONLY READOUTS. No owning dll means nothing reads the ini,
			// so these controls cannot change anything - show exactly the
			// current value and offer nothing else (a one-row dropdown).
			const int lm = (gSelState.liveMode >= 0 && gSelState.liveMode < kSelModeCount)
				? gSelState.liveMode : kModeFullscreen;
			char modeRow[1][80];
			_snprintf_s(modeRow[0], _TRUNCATE, "%s (current)", kSelModeLabels[lm]);
			cIGZWin* mc = gfxDlg->GetChildWindowFromIDRecursive(kSelModeComboId);
			if (mc != nullptr)
			{
				cIGZWinCombo* c = nullptr;
				if (mc->QueryInterface(GZIID_cIGZWinCombo,
						reinterpret_cast<void**>(&c)) && c)
				{
					SelPushCombo(c, modeRow, 1, gSelPushedMode,
						&gSelPushedModeN, 0, &gSelAppliedMode);
					c->Release();
				}
			}
			char resRow[1][80];
			_snprintf_s(resRow[0], _TRUNCATE, "%dx%d (current)",
				gSelState.liveW, gSelState.liveH);
			cIGZWin* rr = gfxDlg->GetChildWindowFromIDRecursive(kSelResComboId);
			if (rr != nullptr)
			{
				cIGZWinCombo* c = nullptr;
				if (rr->QueryInterface(GZIID_cIGZWinCombo,
						reinterpret_cast<void**>(&c)) && c)
				{
					SelPushCombo(c, resRow, 1, gSelPushedRes,
						&gSelPushedResN, 0, &gSelAppliedRes);
					c->Release();
				}
			}
			return;
		}
		cIGZWin* mc = gfxDlg->GetChildWindowFromIDRecursive(kSelModeComboId);
		if (mc != nullptr)
		{
			cIGZWinCombo* c = nullptr;
			if (mc->QueryInterface(GZIID_cIGZWinCombo,
					reinterpret_cast<void**>(&c)) && c)
			{
				SelPushCombo(c, ui.modeRows, kSelModeCount, gSelPushedMode,
					&gSelPushedModeN, ui.modeSel, &gSelAppliedMode);
				c->Release();
			}
		}
		cIGZWin* rc = gfxDlg->GetChildWindowFromIDRecursive(kSelResComboId);
		if (rc != nullptr)
		{
			cIGZWinCombo* c = nullptr;
			if (rc->QueryInterface(GZIID_cIGZWinCombo,
					reinterpret_cast<void**>(&c)) && c)
			{
				SelPushCombo(c, ui.resRows, ui.resCount, gSelPushedRes,
					&gSelPushedResN, ui.resSel, &gSelAppliedRes);
				c->Release();
			}
		}
	}

	void SelOnOpen(cIGZWin* gfxDlg)
	{
		PerfProbe::Scope perf_("sel.open");
		gSelDlgUp = true;
		gSelDlgLast = gfxDlg;
		SelAttachButtonFilters(gfxDlg);

		// THE COMBO'S LIVE GEOMETRY vs ITS PARENT'S CLIP, once per open -
		// the player reported the box "cut off"; the margin is a number, not
		// an impression.
		{
			cIGZWin* cg = gfxDlg->GetChildWindowFromIDRecursive(kSelComboId);
			if (cg != nullptr)
			{
				int cl = 0, ct = 0, cw = 0, ch = 0;
				cIGZWin* par = cg->GetParentWin();
				int pl = 0, pt = 0, pw = 0, ph = 0;
				if (SafeAbsRect(cg, &cl, &ct, &cw, &ch)
					&& par != nullptr && SafeAbsRect(par, &pl, &pt, &pw, &ph))
				{
					Logger::Get().WriteLine(LogLevel::Info,
						"UiSpike: SELGEOM combo [%d,%d %dx%d] parent [%d,%d "
						"%dx%d] - bottom margin %d px (combo bottom %d, "
						"parent bottom %d). A negative or tiny margin is the "
						"box being clipped.",
						cl, ct, cw, ch, pl, pt, pw, ph,
						(pt + ph) - (ct + ch), ct + ch, pt + ph);
				}
			}
		}

		// ---- session facts (cached once, never re-read mid-session) ----
		SelEnumOnce();   // correctness net: waits out a still-warming thread
		SelDisplayMax(&gSelState.capW, &gSelState.capH);
		SelDesktopMode(&gSelState.deskW, &gSelState.deskH);
		gSelState.modes = gSelModeCache;
		gSelState.modeN = gSelModeCacheN;
		if (!gSelPkgCached)
		{
			for (int k = 2; k < kSelCount; k++)
			{
				gSelPkg[k] = ScaleTier::PackageAvailable(kSelFactors[k]);
			}
			gSelPkgCached = true;
		}
		for (int k = 0; k < kSelCount && k < 8; k++)
		{
			gSelState.pkg[k] = gSelPkg[k];
		}
		const ScaleTier::GraphicsOptions gfx = SelReadGfx();
		if (gSelLiveMode < 0) { gSelLiveMode = SelModeOf(gfx); }
		gSelState.liveMode = gSelLiveMode;

		// ---- visit facts: each read ONCE, here -------------------------
		gSelState.iniMode = SelModeOf(gfx);
		gSelState.iniW = gfx.width;
		gSelState.iniH = gfx.height;
		SelReadOurScale(&gSelState.ourAuto, &gSelState.ourFactor);
		gSelState.dll = SelGraphicsDllPresent();
		gSelState.liveW = gReadoutW;
		gSelState.liveH = gReadoutH;
		gSelState.sMode = -1;
		gSelState.sRes = -1;
		gSelState.sScale = -1;

		if (!gSelState.dll && !gSelNoGfxDllLogged)
		{
			gSelNoGfxDllLogged = true;
			Logger::Get().WriteLine(LogLevel::Info,
				"UiSpike: SELMODE SC4GraphicsOptions.dll is NOT installed - "
				"Window Mode and Resolution are shown as READ-ONLY readouts "
				"(one row, the current value). That DLL owns "
				"SC4GraphicsOptions.ini, so without it WindowMode and "
				"WindowWidth/Height are read by nothing and cannot be "
				"changed. The scale selector is unaffected: it writes our "
				"own ini.");
		}

		SelUi ui;
		SelDerive(gSelState, &ui);
		SelApply(gfxDlg, ui);
		gSelBounced = ui.bounced;

		Logger::Get().WriteLine(LogLevel::Info,
			"UiSpike: SELRES offering %d row(s) for %s - one index space, "
			"the list the commit reads.",
			ui.resCount, kSelModeLabels[ui.effMode]);
		if (gSelLogs < 2)
		{
			gSelLogs++;
			Logger::Get().WriteLine(LogLevel::Info,
				"UiSpike: SELECTOR serviced Graphic Options (v3.14 state "
				"machine: state -> derive -> diff-apply, commit at close). "
				"Absent combo means the DATA half is missing for this tier: "
				"rebuild and deploy DialogStatic.");
		}
	}

	void SelOnTick(cIGZWin* gfxDlg)
	{
		// THE TICK DOES ONE THING: poll the three combos. A selection change
		// is the only event; no-event ticks cost three GetSelection calls
		// and nothing else - no syscalls, no file I/O, no logging, no list
		// mutation (the contract gate asserts the shape).
		PerfProbe::Scope perf_("sel.poll");
		int scaleSel = -1, modeSel = -1, resSel = -1;
		cIGZWin* sc = gfxDlg->GetChildWindowFromIDRecursive(kSelComboId);
		if (sc != nullptr)
		{
			cIGZWinCombo* c = nullptr;
			if (sc->QueryInterface(GZIID_cIGZWinCombo,
					reinterpret_cast<void**>(&c)) && c)
			{
				scaleSel = c->GetSelection();
				c->Release();
			}
		}
		if (gSelState.dll)
		{
			cIGZWin* mc = gfxDlg->GetChildWindowFromIDRecursive(kSelModeComboId);
			if (mc != nullptr)
			{
				cIGZWinCombo* c = nullptr;
				if (mc->QueryInterface(GZIID_cIGZWinCombo,
						reinterpret_cast<void**>(&c)) && c)
				{
					modeSel = c->GetSelection();
					c->Release();
				}
			}
			cIGZWin* rc = gfxDlg->GetChildWindowFromIDRecursive(kSelResComboId);
			if (rc != nullptr)
			{
				cIGZWinCombo* c = nullptr;
				if (rc->QueryInterface(GZIID_cIGZWinCombo,
						reinterpret_cast<void**>(&c)) && c)
				{
					resSel = c->GetSelection();
					c->Release();
				}
			}
		}

		const bool modeChanged = gSelState.dll && modeSel >= 0
			&& modeSel < kSelModeCount && modeSel != gSelAppliedMode;
		// A mode change rebuilds the res list, so a same-tick res reading
		// would index the OLD rows - it is ignored and re-polled next tick.
		const bool resChanged = gSelState.dll && !modeChanged && resSel >= 0
			&& resSel < gSelPushedResN && resSel != gSelAppliedRes;
		const bool scaleChanged =
			scaleSel >= 0 && scaleSel < kSelCount
			&& scaleSel != gSelAppliedScale;
		if (!modeChanged && !resChanged && !scaleChanged) { return; }

		if (modeChanged)
		{
			gSelState.sMode = modeSel;
			gSelState.sRes = -1;   // the old index belonged to the old list
			Logger::Get().WriteLine(LogLevel::Info,
				"UiSpike: SELMODE staged %s - applies at the next launch, "
				"and writes BOTH files.", kSelModeLabels[modeSel]);
		}
		if (resChanged)
		{
			gSelState.sRes = resSel;
		}
		if (scaleChanged)
		{
			// The pick is a REQUEST, never overwritten - the effective row
			// is derived as "request if usable else Auto".
			gSelState.sScale = scaleSel;
		}

		SelUi ui;
		SelDerive(gSelState, &ui);
		SelApply(gfxDlg, ui);

		if (resChanged && ui.resSel >= 0 && ui.resSel < ui.resCount)
		{
			Logger::Get().WriteLine(LogLevel::Info,
				"UiSpike: SELRES staged %dx%d - applies at the next launch; "
				"the scale list was re-checked against it.",
				ui.res[ui.resSel].w, ui.res[ui.resSel].h);
		}
		// Bounce and un-bounce, logged on the transition only.
		if (ui.bounced && !gSelBounced && gSelState.sScale >= 0
			&& gSelState.sScale < kSelCount)
		{
			int mw = 0, mh = 0;
			SelMinimumFor(gSelState.sScale, &mw, &mh);
			Logger::Get().WriteLine(LogLevel::Info,
				"UiSpike: SELECTOR %s no longer fits the staged %dx%d (needs "
				"%dx%d) - the effective scale is DERIVED back to Auto. The "
				"request stands: stage a resolution it fits and it returns.",
				kSelLabels[gSelState.sScale], ui.effW, ui.effH, mw, mh);
		}
		else if (!ui.bounced && gSelBounced && gSelState.sScale >= 0
			&& gSelState.sScale < kSelCount)
		{
			Logger::Get().WriteLine(LogLevel::Info,
				"UiSpike: SELECTOR the staged %s fits the staged %dx%d again "
				"- the request stands, no state machine needed.",
				kSelLabels[gSelState.sScale], ui.effW, ui.effH);
		}
		gSelBounced = ui.bounced;
	}

	void SelOnClose(cIGZWin* gfxDlg)
	{
		PerfProbe::Scope perf_("sel.close");
		// LIVENESS-GUARDED (v3.14.1, after a crash). The close re-read used
		// to run against gSelDlgLast unconditionally, on the strength of "the
		// windows still exist at this point - hidden, not destroyed". That
		// held for every main-menu close ever measured, but with a city
		// loaded an unchanged Accept DESTROYED the dialog instead of hiding
		// it (MWKID saw it leave the tree), the stored pointer dangled, and
		// the re-read crashed the game ~150ms after the click - no SELCLOSE
		// line, no exception report. So: the caller passes the pointer IT
		// found this pass. Non-null means the dialog is still in the tree
		// (hidden) and every read below is safe. Null means destroyed - the
		// re-read is skipped (the staged values the tick already collected
		// stand), and the button filters are zeroed WITHOUT calling
		// RemoveMessageFilter on windows that no longer exist.
		const bool alive = (gfxDlg != nullptr);
		if (!alive)
		{
			Logger::Get().WriteLine(LogLevel::Info,
				"UiSpike: SELCLOSE the dialog was DESTROYED, not hidden - "
				"skipping the close re-read (the staged values the 250ms "
				"tick collected stand) and detaching the button filters by "
				"zeroing; RemoveMessageFilter on destroyed windows would be "
				"a wild call.");
		}
		if (alive)
		{
			int scaleSel = -1, modeSel = -1, resSel = -1;
			cIGZWin* sc =
				gfxDlg->GetChildWindowFromIDRecursive(kSelComboId);
			if (sc != nullptr)
			{
				cIGZWinCombo* c = nullptr;
				if (sc->QueryInterface(GZIID_cIGZWinCombo,
						reinterpret_cast<void**>(&c)) && c)
				{
					scaleSel = c->GetSelection();
					c->Release();
				}
			}
			if (gSelState.dll)
			{
				cIGZWin* mc =
					gfxDlg->GetChildWindowFromIDRecursive(kSelModeComboId);
				if (mc != nullptr)
				{
					cIGZWinCombo* c = nullptr;
					if (mc->QueryInterface(GZIID_cIGZWinCombo,
							reinterpret_cast<void**>(&c)) && c)
					{
						modeSel = c->GetSelection();
						c->Release();
					}
				}
				cIGZWin* rc =
					gfxDlg->GetChildWindowFromIDRecursive(kSelResComboId);
				if (rc != nullptr)
				{
					cIGZWinCombo* c = nullptr;
					if (rc->QueryInterface(GZIID_cIGZWinCombo,
							reinterpret_cast<void**>(&c)) && c)
					{
						resSel = c->GetSelection();
						c->Release();
					}
				}
			}
			if (gSelState.dll && modeSel >= 0 && modeSel < kSelModeCount
				&& modeSel != gSelAppliedMode)
			{
				gSelState.sMode = modeSel;
				gSelState.sRes = -1;
			}
			if (gSelState.dll && resSel >= 0 && resSel < gSelPushedResN
				&& resSel != gSelAppliedRes)
			{
				gSelState.sRes = resSel;
			}
			if (scaleSel >= 0 && scaleSel < kSelCount
				&& scaleSel != gSelAppliedScale)
			{
				gSelState.sScale = scaleSel;
			}
		}

		// One final derive from the re-read state. The pair it produces is
		// coherent BY CONSTRUCTION - the effective scale was checked against
		// the effective resolution inside SelDerive, so the old close-time
		// re-check has no condition left to guard.
		SelUi ui;
		SelDerive(gSelState, &ui);

		const char* btn = (gSelLastBtn >= 0)
			? gSelBtns[gSelLastBtn].name : "(none seen)";
		Logger::Get().WriteLine(LogLevel::Info,
			"UiSpike: SELCLOSE the last button to receive a message was %s. "
			"staged scale=%d mode=%d res=%d",
			btn, gSelState.sScale, gSelState.sMode, gSelState.sRes);

		// ACCEPT IS THE ONLY WAY OUT: Cancel and Default Settings ship
		// DISABLED (build_dialog_static DISABLED_BTNS), so a dialog close IS
		// the commit. SCALE: written only if it changed against our ini.
		int iniRow = 0;
		if (!gSelState.ourAuto)
		{
			for (int k = 1; k < kSelCount; k++)
			{
				if (gSelState.ourFactor > kSelFactors[k] - 0.01f
					&& gSelState.ourFactor < kSelFactors[k] + 0.01f)
				{
					iniRow = k;
					break;
				}
			}
		}
		if (ui.effScale != iniRow)
		{
			Logger::Get().WriteLine(LogLevel::Info,
				"UiSpike: SELCLOSE committing the staged scale (closed via "
				"%s; Cancel and Default are disabled, so this can only be "
				"Accept).", btn);
			SelCommitScale(ui.effScale);
		}
		// MODE + RESOLUTION: the PAIR, to BOTH files, only if either changed
		// against the gfx ini. WindowMode without FullScreenMode is the
		// exact half-applied state that makes the game ignore the setting -
		// writing the pair is the whole point of this control. An unchanged
		// visit writes nothing.
		if (gSelState.dll
			&& (ui.effMode != gSelState.iniMode
				|| (ui.effMode != kModeBorderless
					&& (ui.effW != gSelState.iniW
						|| ui.effH != gSelState.iniH))))
		{
			Logger::Get().WriteLine(LogLevel::Info,
				"UiSpike: SELCLOSE committing %s at %dx%d (closed via %s).",
				kSelModeLabels[ui.effMode], ui.effW, ui.effH, btn);
			SelWriteGraphicsIni(ui.effMode, ui.effW, ui.effH);
			// EXCLUSIVE only for Fullscreen. Asking the wrapper for
			// exclusive under borderless or windowed is exactly what makes
			// a "windowed" setting come up fullscreen anyway.
			SelWriteDgVoodooFullScreen(ui.effMode == kModeFullscreen);
		}

		if (alive)
		{
			SelDetachButtonFilters();
		}
		else
		{
			// The buttons died with the dialog: there is nothing to detach,
			// and RemoveMessageFilter on a freed window is a wild call.
			// Zero our slots so no later DoMessage can match a dangling
			// pointer; the next open re-attaches fresh.
			for (int i = 0; i < kSelBtnCount; i++) { gSelBtns[i].win = nullptr; }
			gSelFiltersOn = false;
			gSelLastBtn = -1;
		}
		gSelDlgUp = false;
		gSelDlgLast = nullptr;
		gSelState.sMode = -1;
		gSelState.sRes = -1;
		gSelState.sScale = -1;
		gSelAppliedScale = -1;
		gSelAppliedRes = -1;
		gSelAppliedMode = -1;
		gSelPushedScaleN = 0;
		gSelPushedResN = 0;
		gSelPushedModeN = 0;
		gSelBounced = false;
		// The full timing table, now that a whole visit's work is in the
		// buckets.
		SelPerfDump("dialog closed");
	}

	// ---- PER-PASS COMPANIONS (dialog up) ------------------------------------
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

	// The readout line (#192) and the fixed captions. SelSetCaption diffs
	// internally, so this is write-rare even though it runs per pass.
	void SelApplyStatics(cIGZWin* gfxDlg, const Settings& settings)
	{
		PerfProbe::Scope perf_("sel.caption");
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
		// The Scale caption, matching the "Window Mode" / "Resolution"
		// captions the data ships beside the other two combos. The "- on
		// restart" half of the old text lives in the combo rows now.
		SelSetCaption(gfxDlg, kSelLabelId, "Scale");
		// BOTH column captions are ours: the stock "Resolution" header is
		// hidden, because the column leads with Window Mode and a fixed
		// caption above the wrong control is worse than none. Set even
		// without the dll - the read-only readouts still need their names.
		const uint32_t capIds[2] = { kSelModeLabelId, kSelResLabelId };
		const char* const capTxt[2] = { "Window Mode", "Resolution" };
		for (int ci = 0; ci < 2; ci++)
		{
			cIGZWin* lw = gfxDlg->GetChildWindowFromIDRecursive(capIds[ci]);
			if (lw == nullptr) { continue; }
			cIGZWinText* t = nullptr;
			if (lw->QueryInterface(GZIID_cIGZWinText,
					reinterpret_cast<void**>(&t)) && t)
			{
				cIGZString* cur = lw->GetCaption();
				const bool same = (cur != nullptr && cur->ToChar() != nullptr
					&& strcmp(cur->ToChar(), capTxt[ci]) == 0);
				if (!same)
				{
					cRZBaseString want(capTxt[ci]);
					t->SetCaption(want);
				}
				t->Release();
			}
		}
	}

	// The game's OWN restart notice: we never show it (its information lives
	// in the captions), so a rise is the game's own doing - reported, and
	// retired by a 10s net if the game's handler leaves it up. A timeout
	// cannot be wrong about what a message means; the net guarantees the box
	// can never become a trap.
	void SelNoticeTick(cIGZWin* gfxDlg, unsigned int now)
	{
		PerfProbe::Scope perf_("sel.notice");
		cIGZWin* nw = gfxDlg->GetChildWindowFromIDRecursive(kSelNoticeId);
		const bool up = (nw != nullptr && nw->IsVisible());
		if (up != gSelNoticeWasUp)
		{
			gSelNoticeWasUp = up;
			gSelNoticeShownMs = up ? now : 0;   // arm the net on a rise
			Logger::Get().WriteLine(LogLevel::Info,
				"UiSpike: SELNOTICE %s - a rise we did not cause is the "
				"game's own notice; the 10s net retires it if the game's "
				"Accept does not.", up ? "VISIBLE" : "hidden");
		}
		if (gSelNoticeShownMs != 0 && nw != nullptr
			&& static_cast<int>(now - gSelNoticeShownMs) > 10000)
		{
			if (nw->IsVisible()) { nw->HideWindow(); }
			gSelNoticeShownMs = 0;
			Logger::Get().WriteLine(LogLevel::Info,
				"UiSpike: SELECTOR retired the restart notice after 10s - "
				"the game's own Accept had not hidden it, so the net did.");
		}
	}

}

void UiSpike::DumpSelectorPerf(const char* why)
{
	SelPerfDump(why);
}

void UiSpike::WarmSelectorCaches()
{
	HANDLE h = CreateThread(nullptr, 0, SelEnumWarmThread, nullptr, 0, nullptr);
	if (h != nullptr)
	{
		CloseHandle(h);   // fire and forget; the tri-state is the handshake
	}
	else
	{
		// No thread, no warm - the first open pays the old price, which is
		// slow but correct. Say so, so a stall with this line present has an
		// explanation on file.
		Logger::Get().WriteLine(LogLevel::Info,
			"UiSpike: SELRES warm thread FAILED to start (err %lu) - the "
			"first Graphic Options open will enumerate synchronously.",
			GetLastError());
	}
}

void UiSpike::ServiceScaleSelector()
{
	// FRAME-GAP watchdog: entry-to-entry stride of the caller's loop, checked
	// BEFORE the throttle because the gap is the thing being measured. Only
	// logged while the dialog is up - that is when the player feels the stall.
	{
		const unsigned long long callUs = PerfProbe::NowUs();
		if (gSelPerfPrevCallUs != 0 && gSelDlgUp
			&& (callUs - gSelPerfPrevCallUs) > 500000ull
			&& gSelPerfGapLogs < 40)
		{
			gSelPerfGapLogs++;
			char detail[512];
			const int len = SelPerfDelta(gSelPerfPrevRows, gSelPerfPrevRowN,
				detail, sizeof(detail));
			Logger::Get().WriteLine(LogLevel::Info,
				"UiSpike: SELPERF frame gap %llums with Graphic Options up. "
				"In-gap:%s", (callUs - gSelPerfPrevCallUs) / 1000ull,
				len ? detail
					: " (none of ours >=1ms - the stall is OUTSIDE this "
					"DLL's bracketed code)");
		}
		gSelPerfPrevCallUs = callUs;
		gSelPerfPrevRowN = PerfProbe::Snapshot(gSelPerfPrevRows, 32);
	}

	// Throttle. The dialog is almost never open, so a 250ms beat is
	// imperceptible and turns a per-frame recursive id search into a
	// rounding error against the ~16ms tick.
	const unsigned int now = GetTickCount();
	if (gSelLastMs != 0 && (now - gSelLastMs) < 250u) { return; }
	gSelLastMs = now;

	// Everything from here to any return is one bracketed pass.
	SelPassWatch selPassWatch_;

	cISC4AppPtr pSC4App;
	if (!pSC4App) { return; }
	cIGZWin* pMainWindow = pSC4App->GetMainWindow();
	if (!pMainWindow) { return; }

	// THIS RUNS BEFORE THE DIALOG GATE, AND THAT IS THE POINT.
	// A safety net that needs the player to go looking for the problem is
	// not a safety net. It needs nothing from the dialog: pMainWindow is
	// the window whose real size it measures.
	// ---- 0. THE RESOLUTION THE GAME ACTUALLY LAID OUT AT -----------------
	// THE TIER IS DECIDED FROM AN INFERENCE; THIS IS THE MEASUREMENT.
	// At PreAppInit there is no window yet, so the director must PREDICT the
	// render size from two SC4GraphicsOptions.ini keys plus a rule about
	// what the wrapper does with them. That rule is right for this machine
	// and still an inference about someone else's software.
	// pMainWindow->GetW()/GetH() is the size the UI was ACTUALLY laid out
	// at. If it disagrees with what the tier was decided from, the tier was
	// chosen from a number that never happened. A disagreement flips to
	// Auto for the NEXT launch rather than trying to rescale a live game:
	// the tier packages and the font are chosen once, at startup.
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
						IniCache::WriteStringW(L"UiSpike", L"AutoScale",
							L"1", iniP);
						Logger::Get().WriteLine(LogLevel::Info,
							"UiSpike: RESMISMATCH wrote AutoScale=1 - a manual "
							"factor that cannot fit the size actually being "
							"rendered is exactly the trap the boot rescue "
							"exists for, and the next launch now picks the "
							"tier from the real resolution. The selector's "
							"next open reads the ini and follows it.");
					}
				}
			}
		}
	}

	cIGZWin* gfxDlg = nullptr;
	{
		// Bracketed: this walks the ENTIRE window tree from the main window,
		// every pass, dialog open or not - the widest recursive search in
		// this function.
		PerfProbe::Scope perf_("sel.findDlg");
		gfxDlg = pMainWindow->GetChildWindowFromIDRecursive(kSelDlgId);
	}
	if (gfxDlg != nullptr) { gSelDlgLast = gfxDlg; }
	if (gfxDlg == nullptr || !gfxDlg->IsVisible())
	{
		// Closed. With Cancel and Default disabled, a close IS the commit.
		// gfxDlg is non-null iff the dialog is still IN THE TREE (hidden);
		// null means the game destroyed it, and SelOnClose must not touch it.
		if (gSelDlgUp) { SelOnClose(gfxDlg); }
		return;
	}

	const bool justOpened = !gSelDlgUp;
	if (justOpened) { SelOnOpen(gfxDlg); }
	else { SelOnTick(gfxDlg); }

	SelApplyStatics(gfxDlg, settings);
	SelNoticeTick(gfxDlg, now);
}
