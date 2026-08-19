#include "ScaleTier.h"
#include "Logger.h"

// #149 stage 2. Everything the resource-level fix needs is vendored SDK - no
// field offsets, no fake structs, no raw memory arithmetic on engine objects.
#include "cGZPersistResourceKey.h"
#include "cIGZPersistResource.h"
#include "cIGZPersistResourceManager.h"
#include "cIGZPersistResourceFactory.h"
#include "cIGZBuffer.h"
#include "cIGZGraphicSystem.h"
#include "GZServPtrs.h"

#define WIN32_LEAN_AND_MEAN
#include <Windows.h>

#include <cwchar>
#include <cstdlib>
#include <cstdint>

extern "C" IMAGE_DOS_HEADER __ImageBase;

namespace
{
	// Fit constants (design px of the largest UI pieces at 1x).
	const int kWidestDesignPx = 880;  // city composite status panel
	const int kTallestDesignPx = 558; // Graphics Options dialog

	// Known package factors, tried LARGEST first. 2.0 uses the untagged
	// file names (the original package); other factors use tagged names
	// (e.g. z_SC4UIScale_SelectiveArt-15x.dat) once Step-3 generation
	// produces them - shipping a new package automatically extends
	// coverage because installation is discovered from disk.
	struct Package
	{
		float factor;
		const wchar_t* tag; // filename suffix before the extension
	};
	// Uniform tagging: EVERY factor (including 2x) carries a tag, so fonts
	// have a per-factor source name distinct from the live probed
	// FontStyle.ini, and dats are gated purely by the .dat vs
	// .dat.x1-disabled extension. Tried LARGEST factor first.
	const Package kPackages[] = {
		{ 4.0f, L"-4x" },
		{ 3.0f, L"-3x" },
		{ 2.0f, L"-2x" },
		{ 1.5f, L"-15x" },
	};
	const int kPackageCount = static_cast<int>(sizeof(kPackages) / sizeof(kPackages[0]));

	const wchar_t kDisabledSuffix[] = L".x1-disabled";

	void DllDir(wchar_t* out, size_t outLen)
	{
		GetModuleFileNameW(reinterpret_cast<HMODULE>(&__ImageBase), out, static_cast<DWORD>(outLen));
		wchar_t* s = wcsrchr(out, L'\\');
		if (s)
		{
			*(s + 1) = L'\0';
		}
	}

	bool FileExists(const wchar_t* p)
	{
		const DWORD a = GetFileAttributesW(p);
		return a != INVALID_FILE_ATTRIBUTES && !(a & FILE_ATTRIBUTE_DIRECTORY);
	}

	// True when two files are byte-identical. Reads in 8 KB chunks; the font
	// sources are ~23 KB, so this is one boot-time comparison of a few pages.
	bool FilesIdentical(const wchar_t* a, const wchar_t* b)
	{
		HANDLE ha = CreateFileW(a, GENERIC_READ, FILE_SHARE_READ, nullptr,
			OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, nullptr);
		if (ha == INVALID_HANDLE_VALUE) { return false; }
		HANDLE hb = CreateFileW(b, GENERIC_READ, FILE_SHARE_READ, nullptr,
			OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, nullptr);
		if (hb == INVALID_HANDLE_VALUE) { CloseHandle(ha); return false; }

		LARGE_INTEGER sa = {}, sb = {};
		bool same = GetFileSizeEx(ha, &sa) && GetFileSizeEx(hb, &sb)
			&& sa.QuadPart == sb.QuadPart;
		if (same)
		{
			unsigned char ba[8192], bb[8192];
			for (;;)
			{
				DWORD ra = 0, rb = 0;
				const BOOL oa = ReadFile(ha, ba, sizeof(ba), &ra, nullptr);
				const BOOL ob = ReadFile(hb, bb, sizeof(bb), &rb, nullptr);
				if (!oa || !ob || ra != rb) { same = false; break; }
				if (ra == 0) { break; }                 // both hit EOF together
				if (memcmp(ba, bb, ra) != 0) { same = false; break; }
			}
		}
		CloseHandle(hb);
		CloseHandle(ha);
		return same;
	}

	// #118: is `live` one of OUR shipped tier fonts rather than the user's own?
	// Returns the matching tag ("-2x" etc.) or nullptr if it matches none.
	//
	// This is what makes the upgrade-install case decidable. We ship these
	// files, so byte-identity is proof of authorship - no heuristics, no
	// version stamp needed, and it stays correct if the font contents change,
	// because the comparison is always against the sources we shipped WITH
	// this build. A user font that happened to be identical to one of ours
	// would be "lost" only in the sense that restoring ours gives them the
	// same bytes back.
	const wchar_t* MatchesAnyTierFontSource(const wchar_t* live,
		const wchar_t* srcDir)
	{
		if (srcDir == nullptr || srcDir[0] == L'\0') { return nullptr; }
		for (int i = 0; i < kPackageCount; i++)
		{
			wchar_t src[MAX_PATH];
			swprintf_s(src, L"%sFontStyle%s.ini", srcDir, kPackages[i].tag);
			if (FileExists(src) && FilesIdentical(live, src))
			{
				return kPackages[i].tag;
			}
		}
		return nullptr;
	}

	// The package's art dat (live or gated) beside the DLL marks it
	// installed. The 2x package also accepts its legacy UNTAGGED names
	// (pre-multi-package installs) so Decide() works before migration runs.
	bool PackageInstalled(const Package& pkg)
	{
		wchar_t dir[MAX_PATH];
		DllDir(dir, MAX_PATH);
		wchar_t p[MAX_PATH];
		swprintf_s(p, L"%sz_SC4UIScale_SelectiveArt%s.dat", dir, pkg.tag);
		if (FileExists(p))
		{
			return true;
		}
		swprintf_s(p, L"%sz_SC4UIScale_SelectiveArt%s.dat%s", dir, pkg.tag, kDisabledSuffix);
		if (FileExists(p))
		{
			return true;
		}
		if (pkg.factor >= 1.99f && pkg.factor <= 2.01f)
		{
			swprintf_s(p, L"%sz_SC4UIScale_SelectiveArt.dat", dir);
			if (FileExists(p))
			{
				return true;
			}
			swprintf_s(p, L"%sz_SC4UIScale_SelectiveArt.dat%s", dir, kDisabledSuffix);
			return FileExists(p);
		}
		return false;
	}

	// ---- THIRD-PARTY DEPENDENCY GATE (v2.38.0, task #79c) -----------------
	// Some of our packages are built from ANOTHER MOD'S data (its .UI script
	// or its art) because that mod replaces a stock resource and, by the
	// load-order law, our root package can never override it. Those packages
	// are only correct while that mod is installed: left active after the user
	// removes it, OUR frozen copy keeps the mod's UI alive - the trap
	// MAYOR-MODE.md:126 recorded ("it must move OUR override too or our copy
	// keeps the mod alive") and that we had only applied inside a manual test
	// script. Verified 2026-07-31: with CoriBoom's mod deleted, our
	// zzz- copy (532x640) still beats the stock script (531x406).
	//
	// So each such package declares the mod it depends on, and is enabled ONLY
	// when that mod is present. Nothing here reads, writes, renames or deletes
	// the other mod's files - we only look, and only ever rename OUR OWN dats.
	struct ThirdPartyDep
	{
		const wchar_t* package;   // ours, relative to Documents\Plugins
		const wchar_t* modFile;   // the owning mod's dat, searched by NAME
		bool prefixMatch;         // true = match a NAME PREFIX (version-proof)
		DWORD modSize;            // 0 = presence only, no staleness check
		// A package may be built from MORE THAN ONE of a mod's dats. Both must
		// then be present and unchanged, or our copies are a mix of live and
		// stale. nullptr = no second file.
		const wchar_t* modFile2;
		DWORD modSize2;
	};
	const ThirdPartyDep kThirdPartyDeps[] = {
		// Exact name + SIZE. Our copy hard-codes this mod's exact rects, so a
		// mod update MUST disable us: falling back to runtime scaling is
		// correct-with-a-flash, while stale geometry would be visibly wrong.
		{ L"zzz-SC4UIScale\\z_SC4UIScale_SaveWarningUI",
		  L"SaveWarning_Disable_Exit_Quit.dat", false, 2408, nullptr, 0 },
		// CAM replaces NINE stock .UI scripts; SIX are our dialog-static
		// targets, so until v2.38.3 we shipped doubled copies of scripts the
		// game never loads (generic popup 300x166 vs CAM's 500x175; the
		// startup splash; four building-query panels, one of them 21 -> 45
		// nodes). Found by tools\uiscripts\winning_corpus.py.
		// TWO dats because the six come from two of CAM's files - both must be
		// present and unchanged or our set is half stale.
		{ L"zzz-SC4UIScale\\z_SC4UIScale_CamUI",
		  L"CAM_Extended_Essentials.dat", false, 2817430,
		  L"CAM_Intro.dat", 1001294 },
		// PREFIX, presence only. This package supplies 2x ART for a panel the
		// runtime sweep scales, so a stale copy still renders; disabling it on
		// a version bump would reintroduce the task #44 corruption. Gate only
		// on the mod being GONE - the case that is unambiguously wrong.
		{ L"zzz-SC4UIScale\\z_SC4UIScale_ThirdPartyUI",
		  L"CoriBoom's 36 Slot Building Styles UI", true, 0, nullptr, 0 },
		// warrior's "God Terraforming in Mayor Mode" (task #94, 2026-08-02).
		// It replaces TWO stock flyout scripts from 150-mods\ - the mayor
		// LANDSCAPE flyout {0,96A006B0,09923283} and the SIGNS & LABELS
		// column {0,96A006B0,CB95403E} - with compact layouts, AND ships its
		// own 1x copies of two art TGIs we already ship 2x ({46A006B0,
		// 14215E27} and {..,EB7C4D3B}). By the load-order law its 1x data
		// beat our root 2x, which is why the terraform ring came undocked
		// and the green strips drew unscaled. Our package carries 2x copies
		// of THE MOD'S scripts + THE MOD'S art from zzz-SC4UIScale\.
		// EXACT NAME + SIZE on both dats: our copy hard-codes this mod's
		// exact rects, so a mod update MUST disable us (same reasoning as
		// SaveWarningUI) - runtime scaling with a flash beats stale geometry.
		{ L"zzz-SC4UIScale\\z_SC4UIScale_WarriorUI",
		  L"UI_Compact.dat", false, 8702,
		  L"Mayor_Sign_Menu.dat", 5766 },
		// NAM ITEM ICONS (#139, 2026-08-05). The Network Addon Mod ships 381
		// ItemIcon strips of its own at {856DDBAC,6A386D26,*} - the transport
		// flyouts are almost entirely NAM's. With no 2x copy each strip is a
		// LEFT1X multi-state strip inside a doubled cell, so the button shows
		// TWO states side by side and hovering indexes past the art and draws
		// nothing (TRIAGE.md:23; same family as #49/#55). Ours are upscaled
		// from NAM'S OWN bitmaps, never a stock lookalike.
		//
		// PRESENCE ONLY, EXACT NAME, NO SIZE CHECK. Unlike SaveWarningUI and
		// WarriorUI, this package hard-codes no rects from the mod - it is
		// pure art at the mod's own TGIs. A NAM update that changes an icon
		// makes ours merely stale-looking, never mis-geometried, so gating on
		// size would disable 381 good icons every time NAM ships a patch.
		// `NetworkAddonMod_Controller.dat` is NAM's stable marker: the name is
		// constant across every controller variant and version, and it sits
		// three directories below Plugins - inside FindPluginFile's depth-4
		// budget (Plugins -> 770-network-addon-mod -> 9-patches ->
		// nam.controller.<variant>.sc4pac\<file>).
		{ L"zzz-SC4UIScale\\z_SC4UIScale_NamIcons",
		  L"NetworkAddonMod_Controller.dat", false, 0, nullptr, 0 },
	};
	const int kThirdPartyDepCount =
		static_cast<int>(sizeof(kThirdPartyDeps) / sizeof(kThirdPartyDeps[0]));

	// Look a gate up BY PACKAGE NAME, never by index. The index form was live
	// for about ten minutes in v2.38.3 and was already wrong: inserting the
	// CamUI row in the middle shifted ThirdPartyUI from [1] to [2] while its
	// call site still read depOk[1], which would have gated CoriBoom's package
	// on CAM's presence. A package with no declared dependency is ungated.
	bool DepOkByName(const wchar_t* package, const bool* depOk)
	{
		for (int d = 0; d < kThirdPartyDepCount; d++)
		{
			if (wcscmp(kThirdPartyDeps[d].package, package) == 0)
			{
				return depOk[d];
			}
		}
		return true;
	}

	// Depth-limited recursive search for a plugin file by name. sc4pac folder
	// names carry the mod VERSION ("cyclone-boom.save-warning.1.0.sc4pac"), so
	// a hard-coded relative path would break the moment a mod we do not
	// control is updated. Our own subfolder is skipped so a package can never
	// satisfy its own dependency.
	bool FindPluginFile(
		const wchar_t* dir,
		const wchar_t* name,
		bool prefixMatch,
		int depth,
		wchar_t* outPath,
		size_t outLen,
		DWORD* outSize)
	{
		if (depth <= 0)
		{
			return false;
		}
		wchar_t pattern[MAX_PATH];
		swprintf_s(pattern, L"%s*", dir);
		WIN32_FIND_DATAW fd = {};
		HANDLE h = FindFirstFileW(pattern, &fd);
		if (h == INVALID_HANDLE_VALUE)
		{
			return false;
		}
		bool found = false;
		do
		{
			if (fd.cFileName[0] == L'.')
			{
				continue;   // "." and ".."
			}
			if (fd.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY)
			{
				if (_wcsicmp(fd.cFileName, L"zzz-SC4UIScale") == 0
					|| _wcsicmp(fd.cFileName, L"_dllstash") == 0)
				{
					continue;
				}
				wchar_t sub[MAX_PATH];
				swprintf_s(sub, L"%s%s\\", dir, fd.cFileName);
				found = FindPluginFile(sub, name, prefixMatch, depth - 1,
					outPath, outLen, outSize);
			}
			else
			{
				const size_t n = wcslen(name);
				found = prefixMatch
					? (_wcsnicmp(fd.cFileName, name, n) == 0)
					: (_wcsicmp(fd.cFileName, name) == 0);
				if (found)
				{
					swprintf_s(outPath, outLen, L"%s%s", dir, fd.cFileName);
					*outSize = fd.nFileSizeLow;
				}
			}
		} while (!found && FindNextFileW(h, &fd));
		FindClose(h);
		return found;
	}

	// Gate one tagged dat by its EXTENSION (SC4 loads any *.dat in Plugins,
	// so an inactive factor's dat must NOT end in .dat).
	//   active:   base<tag>.dat.x1-disabled -> base<tag>.dat
	//   inactive: base<tag>.dat -> base<tag>.dat.x1-disabled
	void SyncDat(const wchar_t* dir, const wchar_t* base, const wchar_t* tag, bool active)
	{
		wchar_t live[MAX_PATH];
		wchar_t stash[MAX_PATH];
		swprintf_s(live, L"%s%s%s.dat", dir, base, tag);
		swprintf_s(stash, L"%s%s%s.dat%s", dir, base, tag, kDisabledSuffix);

		const wchar_t* from = active ? stash : live;
		const wchar_t* to = active ? live : stash;
		if (!FileExists(from))
		{
			return; // already in the desired state (or package absent)
		}
		if (MoveFileExW(from, to, MOVEFILE_REPLACE_EXISTING))
		{
			Logger::Get().WriteLine(
				LogLevel::Info, "ScaleTier: %ls%ls.dat -> %s.", base, tag,
				active ? "ACTIVE" : "disabled");
		}
		else
		{
			Logger::Get().WriteLine(
				LogLevel::Info, "ScaleTier: could not gate %ls%ls.dat (err %u).",
				base, tag, GetLastError());
		}
	}

	// One-time migration of a legacy (pre-multi-package) install: the
	// original 2x package shipped UNTAGGED file names. Rename its dats to
	// their -2x names (live or gated form) and derive the FontStyle-2x.ini
	// package source from the legacy font file. Idempotent no-op afterward.
	void MigrateLegacyUntagged2x(const wchar_t* dir)
	{
		const wchar_t* bases[] = {
			L"z_SC4UIScale_SelectiveArt",
			L"z_SC4UIScale_DialogStatic",
		};
		for (int i = 0; i < 2; i++)
		{
			wchar_t legacy[MAX_PATH];
			wchar_t tagged[MAX_PATH];
			// live form
			swprintf_s(legacy, L"%s%s.dat", dir, bases[i]);
			swprintf_s(tagged, L"%s%s-2x.dat", dir, bases[i]);
			if (FileExists(legacy) && !FileExists(tagged))
			{
				MoveFileExW(legacy, tagged, 0);
				Logger::Get().WriteLine(
					LogLevel::Info, "ScaleTier: migrated %ls.dat -> -2x tag.", bases[i]);
			}
			// gated form
			swprintf_s(legacy, L"%s%s.dat%s", dir, bases[i], kDisabledSuffix);
			swprintf_s(tagged, L"%s%s-2x.dat%s", dir, bases[i], kDisabledSuffix);
			if (FileExists(legacy) && !FileExists(tagged))
			{
				MoveFileExW(legacy, tagged, 0);
				Logger::Get().WriteLine(
					LogLevel::Info, "ScaleTier: migrated %ls.dat (gated) -> -2x tag.", bases[i]);
			}
		}

		// Font: the live FontStyle.ini (or its stashed form) IS the 2x
		// table on a legacy install - copy it to the -2x package source if
		// that source doesn't exist yet. The live file itself is left for
		// SyncFont to manage.
		wchar_t src2x[MAX_PATH];
		swprintf_s(src2x, L"%sFontStyle-2x.ini", dir);
		if (!FileExists(src2x))
		{
			wchar_t legacyFont[MAX_PATH];
			swprintf_s(legacyFont, L"%sFontStyle.ini", dir);
			if (!FileExists(legacyFont))
			{
				swprintf_s(legacyFont, L"%sFontStyle.ini%s", dir, kDisabledSuffix);
			}
			if (FileExists(legacyFont) && CopyFileW(legacyFont, src2x, TRUE))
			{
				Logger::Get().WriteLine(
					LogLevel::Info, "ScaleTier: derived FontStyle-2x.ini package source.");
			}
		}
	}

	// The game's install Plugins folder (<install>\Plugins\), derived from
	// the running exe path (<install>\Apps\SimCity 4.exe). Empty string on
	// any parse failure. This is the folder the game ACTUALLY probes for
	// the loose FontStyle.ini (disassembly probe order: <install>\Plugins
	// -> <install>\ -> DBPF). Documents\Plugins is NOT probed for it - the
	// 2026-07-22 "Documents-only works" test was a timing confound; retiring
	// the install-root copy made all text render 1x while frames stayed 2x.
	void InstallPluginsDir(wchar_t* out, size_t outLen)
	{
		out[0] = L'\0';
		wchar_t exe[MAX_PATH];
		if (!GetModuleFileNameW(nullptr, exe, MAX_PATH))
		{
			return;
		}
		wchar_t* file = wcsrchr(exe, L'\\'); // ...\Apps\SimCity 4.exe
		if (!file)
		{
			return;
		}
		*file = L'\0';
		wchar_t* apps = wcsrchr(exe, L'\\'); // ...\Apps
		if (!apps)
		{
			return;
		}
		*apps = L'\0';
		swprintf_s(out, outLen, L"%s\\Plugins\\", exe);
	}

	// The active factor's font must BE the probed name FontStyle.ini in
	// liveDir. Each factor ships a source FontStyle<tag>.ini in srcDir
	// (Documents\Plugins, beside the DLL); the active one is copied over
	// liveDir\FontStyle.ini. Stock tier moves the live font aside
	// (reversible) so the game uses its built-in 1x table.
	void SyncFont(
		const wchar_t* srcDir,
		const wchar_t* liveDir,
		const wchar_t* activeTag /* nullptr = stock */)
	{
		if (liveDir[0] == L'\0')
		{
			Logger::Get().WriteLine(
				LogLevel::Info, "ScaleTier: font live dir unresolved - skipped.");
			return;
		}

		wchar_t live[MAX_PATH];
		swprintf_s(live, L"%sFontStyle.ini", liveDir);

		// ============ USER FONT PRESERVATION (v2.68.0, #115) ============
		// FontStyle.ini is NOT ours. Other SC4 font mods ship one, and the
		// player may have hand-edited theirs. Before this, we DESTROYED it:
		//   * the CopyFileW below passes bFailIfExists = FALSE, so the FIRST
		//     scaled launch overwrote the user's file with NO backup at all;
		//   * the stock-tier MoveFileExW used MOVEFILE_REPLACE_EXISTING, so a
		//     SECOND stock launch overwrote the .x1-disabled copy the first one
		//     made - destroying the last remaining trace.
		// A user who installs at 1440p, then plays on a 1080p laptop (stock
		// tier), lost their font mod permanently and silently.
		//
		// The cure is one file kept once. `.user-original` is written ONLY if
		// it does not already exist (bFailIfExists = TRUE), so it always holds
		// the file as it was BEFORE we ever touched it, no matter how many
		// times tiers change. It is never overwritten and never deleted.
		// #118 (v2.71.3) - THE UPGRADE-INSTALL TRAP. The test above was
		// "a live file exists and we have no snapshot yet", which is TRUE on
		// the first launch after upgrading from any earlier build of THIS mod:
		// by then `live` is already OUR OWN scaled font, written by the old
		// version before this preservation existed. We would snapshot our 2x
		// font as ".user-original" and then, at stock tier, faithfully
		// "restore" a 2x font over the user's file - the very data loss this
		// block was added to prevent, with the evidence destroyed.
		//
		// The distinguishing test is exact and cheap: we SHIP the tier font
		// sources, so a live file that is byte-identical to any of them is
		// ours by construction. Only a file that matches NONE of them can be
		// the user's. (Byte compare, not size: the three tier fonts are all
		// 23,016 bytes, so size alone cannot even tell them apart.)
		wchar_t userOrig[MAX_PATH];
		swprintf_s(userOrig, L"%sFontStyle.ini.user-original", liveDir);
		if (FileExists(live) && !FileExists(userOrig))
		{
			const wchar_t* ourTag = MatchesAnyTierFontSource(live, srcDir);
			if (ourTag != nullptr)
			{
				// Ours, not theirs. Taking no snapshot is the SAFE outcome:
				// with no .user-original the stock tier moves our file aside
				// instead of restoring a wrong one, which leaves the user
				// exactly where they were.
				Logger::Get().WriteLine(
					LogLevel::Info,
					"ScaleTier: %ls is OUR %ls font (byte-identical), not the "
					"user's - no .user-original taken. This is an upgrade "
					"install; snapshotting here would have made our own scaled "
					"font masquerade as the user's original (#118).",
					live, ourTag);
			}
			else if (CopyFileW(live, userOrig, TRUE))
			{
				Logger::Get().WriteLine(
					LogLevel::Info,
					"ScaleTier: preserved the pre-existing %ls as .user-original "
					"(never overwritten; restored at stock tier).", live);
			}
		}

		if (activeTag == nullptr)
		{
			// STOCK TIER = the game as the user had it. Restore their original
			// if we kept one; only then move ours aside. Note the missing
			// MOVEFILE_REPLACE_EXISTING - a stale aside from a previous run is
			// left alone rather than clobbered.
			if (FileExists(userOrig))
			{
				if (CopyFileW(userOrig, live, FALSE))
				{
					Logger::Get().WriteLine(
						LogLevel::Info,
						"ScaleTier: stock tier - restored the user's original %ls.", live);
					return;
				}
			}
			if (FileExists(live))
			{
				wchar_t aside[MAX_PATH];
				swprintf_s(aside, L"%sFontStyle.ini%s", liveDir, kDisabledSuffix);
				if (!MoveFileExW(live, aside, 0))
				{
					Logger::Get().WriteLine(
						LogLevel::Info,
						"ScaleTier: %ls kept - an earlier %ls already exists (err %u).",
						live, aside, GetLastError());
					return;
				}
				Logger::Get().WriteLine(
					LogLevel::Info, "ScaleTier: %ls removed (stock tier).", live);
			}
			return;
		}

		wchar_t src[MAX_PATH];
		swprintf_s(src, L"%sFontStyle%s.ini", srcDir, activeTag);
		if (!FileExists(src))
		{
			Logger::Get().WriteLine(
				LogLevel::Info, "ScaleTier: font source FontStyle%ls.ini missing - text stays 1x.", activeTag);
			return;
		}
		if (CopyFileW(src, live, FALSE))
		{
			Logger::Get().WriteLine(
				LogLevel::Info, "ScaleTier: FontStyle%ls.ini -> %ls.", activeTag, live);
		}
		else
		{
			// A failed install-root write (locked file / ACL) is loud: the
			// tier's frames will scale but its text will not.
			Logger::Get().WriteLine(
				LogLevel::Info, "ScaleTier: could not copy FontStyle%ls.ini -> %ls (err %u).",
				activeTag, live, GetLastError());
		}
	}
}


// ===========================================================================
// ICONSYNTH (task #149) - find the menu icons WE BREAK, at boot, cheaply.
//
// WHY THIS EXISTS. Stock control 2026-08-14, user-confirmed on screen:
//
//     our layer OFF : one icon, visible on hover      CORRECT
//     our layer ON  : two icons, vanishes on hover    BROKEN
//
// WE cause it. SlotThunk2<88> scales the strip's cell width [esi+0xF4] so the
// icons we DID pre-upscale render correctly. The draw then picks its source
// column as `state * cellWidth`. For a plugin's un-upscaled 176x44 strip (true
// cell 44) hover asks for state 3 at column 3*88 = 264 in a 176-wide texture -
// outside it, so nothing draws. At stock the cell is 44 and it works.
//
// So this mod BREAKS every custom icon a player installs after us. Not "fails
// to enlarge" - breaks. Our packages supply 485 icon TGIs; anything a user
// downloads later is outside that set.
//
// ⛔ NO BLIT-LAYER FIX EXISTS - measured, do not re-attempt. The engine needs
// CELL SIZE AND ART SIZE TO AGREE; the cell is per-STRIP while coverage is
// per-TGI, and a real strip mixes both. Every rect patch was rejected on
// screen: re-cut source -> flickers; + centre -> flickers; + tile the whole
// cell so every pixel is rewritten every frame -> STILL flickers. Baseline is
// stable, ANY modification flickers. See _tests\REGRESSION.md #149.
//
// THEREFORE the art must match the cell. Build-time packages cannot do it -
// they cannot know about a lot published next year - so it happens at BOOT,
// against THIS user's install.
//
// THIS FILE IS STAGE 1: the fingerprint and the coverage scan. It reads DBPF
// INDEXES ONLY - no decompression, no pixels, no codec - so it is cheap enough
// to run every boot. Stage 2 (handing the game an enlarged copy) consumes the
// list this produces.
// ===========================================================================
namespace IconSynth
{
	// The menu ItemIcon resource: type PNG, group ItemIcon. Both measured, and
	// both are what the exe's three icon sites push (0x78EE11, 0x7ECB4C,
	// 0x7F0388 - see REGRESSION.md #49).
	const uint32_t kIconType  = 0x856DDBAC;
	const uint32_t kIconGroup = 0x6A386D26;

	// #49's STANDING RULE, and it is load-bearing here: .SC4Lot / .SC4Desc /
	// .SC4Model are ALL DBPF archives and any of them can supply art at an icon
	// TGI. Globbing "*.dat" is what made an earlier sweep report "no art
	// anywhere" for five landmarks whose strips sat inside .SC4Lot files, and
	// it is why our own scanner reported 0 uncovered icons for a custom lot it
	// could not physically see.
	bool IsDbpfName(const wchar_t* name)
	{
		const wchar_t* dot = wcsrchr(name, L'.');
		if (!dot) { return false; }
		return _wcsicmp(dot, L".dat") == 0
			|| _wcsicmp(dot, L".sc4lot") == 0
			|| _wcsicmp(dot, L".sc4desc") == 0
			|| _wcsicmp(dot, L".sc4model") == 0;
	}

	bool IsOurPackage(const wchar_t* name)
	{
		return _wcsnicmp(name, L"z_SC4UIScale_", 13) == 0;
	}

	// ---- FINGERPRINT ------------------------------------------------------
	// A boot check has to be nearly free or it becomes a tax on every launch
	// (first city open already costs ~54s, #141). This opens NO files: it is a
	// directory walk accumulating count, total size and newest write time.
	//
	// It changes when a plugin is added, removed, resized or re-dated, so the
	// generated set can never go silently stale - which is exactly how three
	// packages rotted before (law: a package is not done until it is in the
	// manifest AND something proves it fresh).
	struct Fingerprint
	{
		uint32_t files;
		uint64_t bytes;
		uint64_t newest;
	};

	// ⛔ MAX_PATH IS NOT ENOUGH HERE - #139, TRAP 1, PAID FOR IN TEN MISSED
	// ICONS THE USER FOUND BY EYE. NAM nests its dats 283-298 characters deep
	// (`...\Legacy Road Viaduct Puzzle Piece Menu Button Access#\...`), so a
	// MAX_PATH (260) buffer truncates and the file "does not exist" - the walk
	// then reports a clean sheet for a folder full of uncovered icons. The
	// documented cure is the \\?\ prefix plus buffers that can hold it, and
	// this walk is the exact shape that bug had.
	const int kLongPath = 1024;

	// How many entries lived past the classic limit. This is the POSITIVE
	// CONTROL for the long-path handling itself: the CONTROL icon cannot
	// detect a truncated walk because it is chosen BY that same walk (#139:
	// "when a tool and its gate share a helper, they share its blind spots").
	// A number here proves the deep tree was actually reachable.
	int gLongPathsSeen = 0;

	void Walk(const wchar_t* dir, Fingerprint& fp,
		void (*onFile)(const wchar_t*, const wchar_t*, void*), void* ctx)
	{
		wchar_t glob[kLongPath];
		if (swprintf_s(glob, L"%s\\*", dir) < 0) { return; }
		WIN32_FIND_DATAW fd = {};
		HANDLE h = FindFirstFileW(glob, &fd);
		if (h == INVALID_HANDLE_VALUE) { return; }
		do
		{
			if (fd.cFileName[0] == L'.'
				&& (fd.cFileName[1] == L'\0'
					|| (fd.cFileName[1] == L'.' && fd.cFileName[2] == L'\0')))
			{
				continue;
			}
			wchar_t full[kLongPath];
			if (swprintf_s(full, L"%s\\%s", dir, fd.cFileName) < 0)
			{
				// Deeper than even the long-path buffer. Say so - a silent
				// skip here reads as "no icons in that folder".
				Logger::Get().WriteLine(LogLevel::Info,
					"IconSynth: ⚠ path too long even for %d wchars under %ls - "
					"SKIPPED, so UNCOVERED is a lower bound.", kLongPath, dir);
				continue;
			}
			if (wcslen(full) > MAX_PATH) { gLongPathsSeen++; }
			if (fd.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY)
			{
				// SC4's plugin scan is RECURSIVE, so ours must be too.
				Walk(full, fp, onFile, ctx);
				continue;
			}
			fp.files++;
			fp.bytes += (static_cast<uint64_t>(fd.nFileSizeHigh) << 32)
				| fd.nFileSizeLow;
			const uint64_t t =
				(static_cast<uint64_t>(fd.ftLastWriteTime.dwHighDateTime) << 32)
				| fd.ftLastWriteTime.dwLowDateTime;
			if (t > fp.newest) { fp.newest = t; }
			if (onFile) { onFile(full, fd.cFileName, ctx); }
		} while (FindNextFileW(h, &fd));
		FindClose(h);
	}

	// ---- DBPF INDEX READ (index only - never the payload) -----------------
	// SC4 ships index major 7, minor 0 (20-byte entries) or 1 (24). Reading
	// only the index means no QFS, no PNG, no allocation beyond the index
	// itself - which is what keeps this affordable at boot.
	bool ReadIconTgis(const wchar_t* path,
		void (*onTgi)(uint32_t, void*), void* ctx)
	{
		HANDLE f = CreateFileW(path, GENERIC_READ, FILE_SHARE_READ, nullptr,
			OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, nullptr);
		if (f == INVALID_HANDLE_VALUE) { return false; }
		bool ok = false;
		uint8_t hdr[0x68] = {};
		DWORD got = 0;
		if (ReadFile(f, hdr, sizeof(hdr), &got, nullptr) && got == sizeof(hdr)
			&& hdr[0] == 'D' && hdr[1] == 'B' && hdr[2] == 'P' && hdr[3] == 'F')
		{
			// ⛔ THESE OFFSETS WERE WRONG IN THE FIRST BUILD AND THE SCAN WENT
			// SILENT RATHER THAN LOUD: it read count from 0x38 and offset from
			// 0x40, both of which are 0 in a real SC4 DBPF, so the `count > 0`
			// guard rejected EVERY file and the boot line reported ours=0
			// theirs=0 UNCOVERED=0 - a clean bill of health from a blind probe.
			// Verified against Plugins\z_SC4UIScale_ItemIconsSub-2x.dat:
			//   0x24 = 130 entries, 0x28 = 0x16D04D, 0x3C = 0 -> 130 icons found,
			// matching that package's known entry count.
			const uint32_t count  = *reinterpret_cast<uint32_t*>(hdr + 0x24);
			const uint32_t offset = *reinterpret_cast<uint32_t*>(hdr + 0x28);
			const uint32_t idxMin = *reinterpret_cast<uint32_t*>(hdr + 0x3C);
			const uint32_t stride = (idxMin == 1) ? 24 : 20;
			// Sanity, so a malformed or non-SC4 DBPF cannot make us allocate
			// wildly or walk off the end.
			if (count > 0 && count < 200000 && offset > 0)
			{
				const uint32_t bytes = count * stride;
				uint8_t* idx = static_cast<uint8_t*>(malloc(bytes));
				if (idx)
				{
					if (SetFilePointer(f, offset, nullptr, FILE_BEGIN)
							!= INVALID_SET_FILE_POINTER
						&& ReadFile(f, idx, bytes, &got, nullptr)
						&& got == bytes)
					{
						for (uint32_t i = 0; i < count; i++)
						{
							const uint8_t* e = idx + i * stride;
							const uint32_t t = *reinterpret_cast<const uint32_t*>(e);
							const uint32_t g = *reinterpret_cast<const uint32_t*>(e + 4);
							const uint32_t inst = *reinterpret_cast<const uint32_t*>(e + 8);
							if (t == kIconType && g == kIconGroup && onTgi)
							{
								onTgi(inst, ctx);
							}
						}
						ok = true;
					}
					free(idx);
				}
			}
		}
		CloseHandle(f);
		return ok;
	}

	// ---- THE SCAN ---------------------------------------------------------
	// Two passes over the SAME file list: ours supplies the covered set, every
	// other DBPF supplies the candidate set, and the difference is the icons we
	// break. Bounded, allocation-light, index-reads only.
	//
	// ⚠ ORDER IS NOT GUARANTEED by the directory walk, so coverage cannot be
	// decided on the fly - collect ours FIRST, then diff. Deciding per-file as
	// they arrive would mark an icon uncovered simply because our package had
	// not been walked yet.
	const int kMaxTgi = 4096;

	struct ScanState
	{
		uint32_t ours[kMaxTgi];
		int      nOurs;
		uint32_t theirs[kMaxTgi];
		int      nTheirs;
		bool     collectingOurs;
		int      dropped;      // hit the cap - report it, never hide it
	};

	ScanState* gScan = nullptr;

	// ---- THE HAND-OFF TO STAGE 2 ------------------------------------------
	// The scan runs at SyncStaticLayers, which is BEFORE the game opens a
	// single dat - so nothing can be fetched from the resource manager yet.
	// Stage 2 therefore runs later (PostAppInit) and needs the answer carried
	// across. This is that carrier, plus ONE covered instance kept as the
	// POSITIVE CONTROL: if the covered icon does not read back at the scaled
	// size, the fetch is broken and an "uncovered art is 1x" finding would be
	// an instrument reading, not a fact.
	const int kMaxFix = 512;
	uint32_t gFixList[kMaxFix] = {};
	int      gFixN = 0;
	bool     gFixTruncated = false;
	uint32_t gControlInst = 0;   // one of OURS, known-enlarged on disk

	void AddTgi(uint32_t inst, void* /*ctx*/)
	{
		if (!gScan) { return; }
		uint32_t* arr = gScan->collectingOurs ? gScan->ours : gScan->theirs;
		int&      n   = gScan->collectingOurs ? gScan->nOurs : gScan->nTheirs;
		for (int i = 0; i < n; i++) { if (arr[i] == inst) { return; } }
		if (n >= kMaxTgi) { gScan->dropped++; return; }
		arr[n++] = inst;
	}

	void OnFile(const wchar_t* full, const wchar_t* name, void* /*ctx*/)
	{
		if (!gScan || !IsDbpfName(name)) { return; }
		if (IsOurPackage(name) != gScan->collectingOurs) { return; }
		ReadIconTgis(full, AddTgi, nullptr);
	}

	// Returns the number of UNCOVERED icons; logs the whole picture.
	int ScanAndReport(const wchar_t* pluginsDir, float factor)
	{
		const DWORD t0 = GetTickCount();
		Fingerprint fp = {};

		gScan = static_cast<ScanState*>(calloc(1, sizeof(ScanState)));
		if (!gScan)
		{
			Logger::Get().WriteLine(LogLevel::Info,
				"IconSynth: out of memory for the scan - skipped.");
			return -1;
		}

		gFixN = 0;
		gFixTruncated = false;
		gControlInst = 0;
		gLongPathsSeen = 0;

		// \\?\ turns off the 260-character limit for every path derived from
		// this root (#139 trap 1). It requires a fully-qualified path with
		// backslashes, which DllDir already produces.
		wchar_t root[kLongPath];
		if (wcsncmp(pluginsDir, L"\\\\?\\", 4) == 0)
		{
			swprintf_s(root, L"%s", pluginsDir);
		}
		else
		{
			swprintf_s(root, L"\\\\?\\%s", pluginsDir);
		}

		gScan->collectingOurs = true;
		Walk(root, fp, OnFile, nullptr);
		const int nOurs = gScan->nOurs;
		if (nOurs > 0) { gControlInst = gScan->ours[0]; }

		Fingerprint fp2 = {};
		gScan->collectingOurs = false;
		Walk(root, fp2, OnFile, nullptr);

		// The difference IS the defect set: icons some plugin supplies at 1x
		// that no package of ours enlarges. At any tier > 1 the engine scales
		// the strip's cell but not this art, so the draw over-reads - two
		// copies at rest, and nothing at all on hover once the state index
		// walks past the end of the texture.
		int uncovered = 0;
		int logged = 0;
		for (int i = 0; i < gScan->nTheirs; i++)
		{
			const uint32_t inst = gScan->theirs[i];
			bool covered = false;
			for (int j = 0; j < nOurs; j++)
			{
				if (gScan->ours[j] == inst) { covered = true; break; }
			}
			if (covered) { continue; }
			uncovered++;
			if (gFixN < kMaxFix) { gFixList[gFixN++] = inst; }
			else { gFixTruncated = true; }
			if (logged < 24)
			{
				logged++;
				Logger::Get().WriteLine(LogLevel::Info,
					"IconSynth:   UNCOVERED icon {%08X,%08X,%08X} - this one "
					"renders doubled and vanishes on hover at f=%.2f",
					kIconType, kIconGroup, inst, factor);
			}
		}

		Logger::Get().WriteLine(LogLevel::Info,
			"IconSynth: scanned %u files / %llu bytes in %u ms "
			"(%d past MAX_PATH - #139 cost 10 missed icons to a truncating "
			"walk, so a 0 here on a NAM install means the \\\\?\\ prefix is "
			"not working). ours=%d theirs=%d UNCOVERED=%d%s  "
			"fingerprint=%u/%llu/%llu",
			fp2.files, fp2.bytes, GetTickCount() - t0, gLongPathsSeen,
			nOurs, gScan->nTheirs, uncovered,
			(logged < uncovered) ? " (list truncated at 24)" : "",
			fp2.files, fp2.bytes, fp2.newest);

		if (gScan->dropped)
		{
			// A cap that silently truncates reads as "fully covered" - the
			// exact shape of a report that is wrong in the safe-looking
			// direction. Say it loudly instead.
			Logger::Get().WriteLine(LogLevel::Info,
				"IconSynth: ⚠ TGI CAP HIT - %d entries dropped, so UNCOVERED is "
				"a LOWER BOUND. Raise kMaxTgi (%d).", gScan->dropped, kMaxTgi);
		}

		free(gScan);
		gScan = nullptr;
		return uncovered;
	}

	// =======================================================================
	// STAGE 2 - BORN CORRECT AT THE RESOURCE, NOT PATCHED AT THE BLIT.
	//
	// Five blit-layer attempts failed on screen and the sixth (substituting an
	// enlarged source surface inside BltStripThunk) rendered the RIGHT icon
	// while a stale uncorrected copy kept flashing beside it. That outcome is
	// the standing law, not a surprise:
	//
	//     feedback-sc4-reactive-sweep-flashes:
	//     "THE CURE IS ALWAYS BORN-2x, NEVER HIDE THE PAINT."
	//
	// A blit hook is by definition reactive - it corrects a draw that the
	// compositor has already scheduled, and it can never reach a copy that is
	// already sitting in some buffer. So stop correcting draws and fix the
	// thing every draw reads from: the RESOURCE.
	//
	// The engine asks the resource manager for {PNG, ItemIcon, instance} and
	// gets back an object that is simultaneously a cIGZBuffer (the blit's own
	// source - proven, GetEnlarged QueryInterfaces the live blit argument to
	// exactly this IID) and a cIGZPersistResource (what the manager keys on).
	// Register an enlarged object under that key BEFORE the menus are built
	// and every consumer - every strip, every state, every frame, including
	// paths we have never instrumented - gets correct art with no hook at all.
	//
	// ⛔ THIS IS NOT "THE UPSCALER IS ON". It touches ONLY the instances the
	// scan proved are UNCOVERED - art some plugin shipped at 1x that no
	// package of ours enlarges. Covered icons are never fetched, never
	// re-registered, never resampled. The resample itself is the same exact
	// nearest-neighbour pixel copy Upscale2x.cs performs offline, so a
	// synthesised icon is identical in character to every icon we ship.
	//
	// ⚠ ONE-WAY DOOR AVOIDED DELIBERATELY: nothing here modifies the game's
	// object. A new buffer is built, and only a complete, verified one is
	// registered. Any failure at any step leaves the original registration
	// untouched, so the worst case is the old broken-but-stable rendering.
	int  gMade = 0, gMiss = 0, gSkip = 0, gFail = 0;

	int RoundHalfUp(float v)
	{
		return static_cast<int>(v + 0.5f);
	}

	// ---- ScaleDim: THE OFFLINE UPSCALER'S DIMENSION RULE, PORTED VERBATIM ---
	// #158. Our runtime enlargement produced 264x66 at f=1.5 while our OWN
	// offline art for the same tier is 264x68 - same cell width, 2px shorter.
	// Two paths that both claim to scale an icon must not disagree, and the
	// offline one is the reference: 320 covered icons ship at 68 and render
	// correctly, so 66 was the odd one out.
	//
	// Upscale2x.cs::ScaleDim / CellUnit, matched exactly:
	//   integer factor            -> round(v*f), untouched (2x and 3x are no-ops)
	//   otherwise                 -> snap to the nearest multiple of CellUnit(v)
	//   CellUnit(v)               -> lcm of {3,4} that divide v (so 12, 4, 3 or 1)
	//   ties go UP                -> art a shade too big can never UNDER-cover
	//   correction > 12.5% of v   -> leave alone; the divisor was a coincidence
	//                                of the number, not a real cell count
	//
	// Worked example, the case that exposed this: h = 44, f = 1.5 -> 66.
	// CellUnit(44) = 4 (44%4==0, 44%12!=0); 66%4 = 2, so down=64 up=68, a TIE
	// that resolves UP to 68 - the same 68 the offline build reaches from its
	// 88-tall stage art via 0.75. Different starting point, identical answer.
	const int kCellCounts[] = { 3, 4 };

	int Gcd(int a, int b) { while (b != 0) { int t = a % b; a = b; b = t; } return a; }

	int CellUnit(int v)
	{
		int k = 1;
		for (int i = 0; i < 2; i++)
		{
			const int n = kCellCounts[i];
			if (v % n == 0) { k = k / Gcd(k, n) * n; }   // lcm
		}
		return k;
	}

	int ScaleDim(int v, float factor)
	{
		const int s = RoundHalfUp(v * factor);
		if (factor == static_cast<float>(static_cast<int>(factor))) { return s; }
		const int k = CellUnit(v);
		if (k <= 1 || (s % k) == 0) { return s; }
		const int down = s - (s % k);
		const int up = down + k;
		int snapped = ((s - down) < (up - s)) ? down : up;   // ties -> up
		if (snapped < k) { snapped = k; }
		// PROPORTIONALITY GUARD (Upscale2x's own): a 16px icon divides by 16
		// but is not a 16-cell strip; snapping it would move it 33%.
		if (abs(snapped - s) * 8 > s) { return s; }
		return snapped;
	}

	// Kept alive on purpose: the manager's cache is refcounted and its garbage
	// collector drops resources nobody holds. If ours were released the game
	// could reload the 1x original from disk mid-session and the defect would
	// silently return - the exact "package rotted and every gate stayed green"
	// shape. Holding the reference is what makes the fix durable.
	const int kHoldMax = 512;
	cIGZUnknown* gHold[kHoldMax] = {};
	int gHoldN = 0;

	// The per-cell nearest-neighbour resample, factored out so the two paths
	// below cannot drift apart. `read` is the source of truth for pixels -
	// either the live source buffer or a snapshot taken before the destination
	// was re-initialised over it.
	//
	// PER-CELL, not whole-bitmap. A 4-state strip is four independent images
	// that happen to share a texture; scaling the sheet as one image lets
	// rounding drift bleed a column of state N+1 into state N at non-integer
	// factors. Mapping each cell on its own makes every output cell an exact
	// resample of exactly one input cell - #156's rule.
	void ResampleCells(const uint32_t* read, int sw, int sh,
		cIGZBuffer* dst, int newW, int newH, int cell, int newCell)
	{
		for (int y = 0; y < newH; y++)
		{
			const int sy = (y * sh) / newH;
			for (int x = 0; x < newW; x++)
			{
				const int state = x / newCell;
				const int xin   = x - state * newCell;
				int sx = state * cell + (xin * cell) / newCell;
				if (sx >= sw) { sx = sw - 1; }
				dst->SetPixel(static_cast<uint32_t>(x), static_cast<uint32_t>(y),
					read[static_cast<size_t>(sy) * sw + sx]);
			}
		}
	}

	// ---- THE IN-PLACE PATH ------------------------------------------------
	// Registering a replacement needs an object the manager can key on, and a
	// plain graphics buffer is not one. But the object the manager ALREADY
	// hands out for this TGI is a cIGZBuffer, and cIGZBuffer::Init is a public
	// SDK method - so resize THAT object and every future fetch, every strip,
	// every state gets the enlarged art with no registration, no factory and
	// no hook. Same born-correct outcome, one less moving part.
	//
	// ⚠ ORDER IS LOAD-BEARING: Init reallocates, so the pixels must be read
	// out BEFORE it is called. And if Init fails the object is left smaller
	// than the game expects, which is worse than the defect - so a failure
	// restores the original size and contents from the snapshot, and says so
	// loudly if even that fails.
	bool EnlargeInPlace(cIGZBuffer* src, int sw, int sh,
		int newW, int newH, int cell, int newCell)
	{
		uint32_t* px = static_cast<uint32_t*>(
			malloc(static_cast<size_t>(sw) * sh * sizeof(uint32_t)));
		if (!px)
		{
			Logger::Get().WriteLine(LogLevel::Info,
				"IconSynth:   step snapshot alloc FAILED (%dx%d).", sw, sh);
			return false;
		}
		for (int y = 0; y < sh; y++)
		{
			for (int x = 0; x < sw; x++)
			{
				px[static_cast<size_t>(y) * sw + x] =
					src->GetPixel(static_cast<uint32_t>(x),
						static_cast<uint32_t>(y));
			}
		}
		uint32_t tkey = 0;
		const bool hasT = src->GetTransparentColor(tkey);
		const cGZBufferColorType ct = src->GetColorType();
		const uint32_t bpp = src->GetBitsPerPixel();

		bool ok = src->Init(static_cast<uint32_t>(newW),
			static_cast<uint32_t>(newH), ct.bufferType, bpp);
		if (!ok)
		{
			// Some buffer implementations refuse a second Init while still
			// holding an allocation. Try the documented teardown once.
			src->Uninitialize();
			ok = src->Init(static_cast<uint32_t>(newW),
				static_cast<uint32_t>(newH), ct.bufferType, bpp);
			Logger::Get().WriteLine(LogLevel::Info,
				"IconSynth:   in-place Init refused while initialised; after "
				"Uninitialize it %s.", ok ? "SUCCEEDED" : "still FAILED");
		}
		// Do not trust the return value alone - measure the object.
		if (ok && (src->Width() != newW || src->Height() != newH))
		{
			Logger::Get().WriteLine(LogLevel::Info,
				"IconSynth:   in-place Init returned true but the buffer reads "
				"back %dx%d, not %dx%d. Treating as FAILURE.",
				src->Width(), src->Height(), newW, newH);
			ok = false;
		}

		if (!ok)
		{
			const bool restored =
				src->Init(static_cast<uint32_t>(sw), static_cast<uint32_t>(sh),
					ct.bufferType, bpp)
				&& src->Width() == sw && src->Height() == sh;
			if (restored)
			{
				for (int y = 0; y < sh; y++)
				{
					for (int x = 0; x < sw; x++)
					{
						src->SetPixel(static_cast<uint32_t>(x),
							static_cast<uint32_t>(y),
							px[static_cast<size_t>(y) * sw + x]);
					}
				}
				if (hasT) { src->SetTransparency(tkey); }
			}
			else
			{
				Logger::Get().WriteLine(LogLevel::Info,
					"IconSynth:   ⚠ THE ORIGINAL COULD NOT BE RESTORED after a "
					"failed in-place resize (%dx%d). This icon is now in an "
					"unknown state - do not ship this path until the cause is "
					"understood.", sw, sh);
			}
			free(px);
			return false;
		}

		ResampleCells(px, sw, sh, src, newW, newH, cell, newCell);
		if (hasT) { src->SetTransparency(tkey); }

		// ---- VERIFY THE WRITE, DO NOT ASSUME IT --------------------------
		// CELLPROBE settled that the rects are flush (stride == texW/4 == 132,
		// src(0,0,132,132) -> dst 132x132, zero mismatches with budget to
		// spare). The rects being right and the picture being wrong leaves
		// exactly one suspect: what SetPixel actually put in the buffer.
		//
		// A right-shifted, wrapping image is the classic signature of a ROW
		// PITCH that disagrees with the width - and this buffer was resized by
		// Uninitialize+Init, which is precisely the path where a stale pitch
		// would survive. So read back what we wrote and compare it against the
		// snapshot we wrote it from. Sampling, not a full compare: 3 rows x 8
		// columns is enough to catch a pitch skew, which grows with y.
		int bad = 0;
		uint32_t firstBadGot = 0, firstBadWant = 0;
		int firstBadX = -1, firstBadY = -1;
		for (int yi = 0; yi < 3; yi++)
		{
			const int y = (newH * (2 * yi + 1)) / 6;
			const int sy = (y * sh) / newH;
			for (int xi = 0; xi < 8; xi++)
			{
				const int x = (newW * (2 * xi + 1)) / 16;
				const int state = x / newCell;
				const int xin = x - state * newCell;
				int sx = state * cell + (xin * cell) / newCell;
				if (sx >= sw) { sx = sw - 1; }
				const uint32_t want = px[static_cast<size_t>(sy) * sw + sx];
				const uint32_t got = src->GetPixel(
					static_cast<uint32_t>(x), static_cast<uint32_t>(y));
				if (got != want)
				{
					if (!bad) { firstBadX = x; firstBadY = y;
						firstBadGot = got; firstBadWant = want; }
					bad++;
				}
			}
		}
		const cGZBufferColorType after = src->GetColorType();
		Logger::Get().WriteLine(LogLevel::Info,
			"IconSynth:   VERIFY %dx%d -> %dx%d: %d/24 sampled pixels WRONG. "
			"type %d->%d bpp %u->%u.%s",
			sw, sh, newW, newH, bad, static_cast<int>(ct.bufferType),
			static_cast<int>(after.bufferType), bpp, src->GetBitsPerPixel(),
			bad ? "" : " Readback matches the source exactly, so the pixels we"
				" wrote are the pixels that are there.");
		if (bad)
		{
			Logger::Get().WriteLine(LogLevel::Info,
				"IconSynth:   VERIFY first wrong pixel at (%d,%d): got %08X "
				"want %08X - the buffer is NOT storing what SetPixel was "
				"handed, so the resample is innocent and the write path is "
				"the defect.",
				firstBadX, firstBadY, firstBadGot, firstBadWant);
		}
		free(px);
		return true;
	}

	// Build the enlarged twin of `src`. Returns the new object with ONE
	// reference owned by the caller, or nullptr (caller then changes nothing).
	cIGZPersistResource* BuildEnlarged(cIGZGraphicSystem* gs, cIGZBuffer* src,
		int newW, int newH, int cell, int newCell)
	{
		// ⚠ ONE LINE PER STEP, ON PURPOSE. The first build of this function
		// logged a single "could not build" for three different failures, so
		// the launch that ran it proved the diagnosis and then refused to say
		// WHICH call said no - a probe that answers half a question costs a
		// whole launch. Each gate below names itself.
		cIGZBuffer* big = nullptr;
		if (!gs->CreateBuffer(&big) || !big)
		{
			Logger::Get().WriteLine(LogLevel::Info,
				"IconSynth:   step CreateBuffer FAILED.");
			return nullptr;
		}

		// The manager keys on cIGZPersistResource. If the graphic system's
		// buffer class does not implement it there is no way to register the
		// result, and saying so plainly beats registering something wrong.
		cIGZPersistResource* res = nullptr;
		if (!big->QueryInterface(GZIID_cIGZPersistResource,
				reinterpret_cast<void**>(&res)) || !res)
		{
			Logger::Get().WriteLine(LogLevel::Info,
				"IconSynth:   step QueryInterface(cIGZPersistResource) FAILED - "
				"a plain graphics buffer is not a persistable resource, so it "
				"can never be REGISTERED under a TGI. The in-place path below "
				"is the answer, not a bigger hammer here.");
			big->Release();
			return nullptr;
		}

		const cGZBufferColorType ct = src->GetColorType();
		if (!big->Init(static_cast<uint32_t>(newW), static_cast<uint32_t>(newH),
				ct.bufferType, src->GetBitsPerPixel()))
		{
			Logger::Get().WriteLine(LogLevel::Info,
				"IconSynth:   step Init(%d,%d,type %d,%u bpp) FAILED.",
				newW, newH, static_cast<int>(ct.bufferType),
				src->GetBitsPerPixel());
			res->Release();
			big->Release();
			return nullptr;
		}

		// Snapshot then resample through the SHARED routine, so this path and
		// the in-place path can never drift apart on the sampling rule.
		const int sw = src->Width();
		const int sh = src->Height();
		uint32_t* px = static_cast<uint32_t*>(
			malloc(static_cast<size_t>(sw) * sh * sizeof(uint32_t)));
		if (!px)
		{
			res->Release();
			big->Release();
			return nullptr;
		}
		for (int y = 0; y < sh; y++)
		{
			for (int x = 0; x < sw; x++)
			{
				px[static_cast<size_t>(y) * sw + x] =
					src->GetPixel(static_cast<uint32_t>(x),
						static_cast<uint32_t>(y));
			}
		}
		ResampleCells(px, sw, sh, big, newW, newH, cell, newCell);
		free(px);

		uint32_t tkey = 0;
		if (src->GetTransparentColor(tkey)) { big->SetTransparency(tkey); }

		big->Release();   // res holds the object alive from here
		return res;
	}

	// =======================================================================
	// THE FACTORY WRAP - the only point EVERY instance passes through.
	//
	// MEASURED 2026-08-15, and it is why the in-place cache fix was invisible:
	//
	//   RE-FETCH {18020094} fixedPtr=2408E114
	//       GetResource        = 2408E114  528x132   <- our object, it stuck
	//       GetPrivateResource = 2408E594  176x44    <- a DIFFERENT object
	//
	// GetPrivateResource exists precisely to hand a consumer its OWN copy, so
	// no amount of mutating the shared one can ever be seen by the menu. The
	// resource cache was the wrong channel; the FACTORY is the right one,
	// because both fetches build their object through it.
	//
	// ⛔ NOT by implementing cIGZPersistResourceFactory. It declares two
	// CreateInstance overloads, and MSVC lays overloaded virtuals out in
	// REVERSE declaration order - the trap already documented at the top of
	// UiSpike.cpp, which cost this project a wrong-slot call once. Instead the
	// game's OWN vtable is copied and ONE slot repointed, the same discipline
	// as gVtCopy2/SlotThunk2: never write a shared class vtable.
	//
	// Slot choice is safe against that same trap: the overload pair occupies
	// slots 3 and 4 in EITHER order, so Read is slot 5 and Write is slot 6
	// regardless of which way MSVC ordered them.
	const int kFacSlots = 16;
	void* gFacVtCopy[kFacSlots] = {};
	void* gFacOrigVt = nullptr;
	void* gFacInstance = nullptr;
	float gFacFactor = 1.0f;
	unsigned gFacReads = 0, gFacHits = 0;

	typedef bool(__fastcall* FacReadFn)(void*, void*, cIGZPersistResource*, void*);
	FacReadFn gFacOrigRead = nullptr;

	bool InFixList(uint32_t inst)
	{
		for (int i = 0; i < gFixN; i++) { if (gFixList[i] == inst) { return true; } }
		return false;
	}

	bool __fastcall FacReadThunk(void* self, void* edx,
		cIGZPersistResource* res, void* rec)
	{
		const bool ok = gFacOrigRead ? gFacOrigRead(self, edx, res, rec) : false;
		gFacReads++;
		// NULL IS NOT EVIDENCE. Without this, "no born-correct lines" reads
		// identically for "the wrap never ran" and "the wrap ran and our two
		// icons never came through Read" - two very different next steps.
		if (gFacReads == 1 || (gFacReads % 500) == 0)
		{
			Logger::Get().WriteLine(LogLevel::Info,
				"IconSynth: factory Read #%u (hits so far %u) - the wrap IS "
				"live, so a missing icon is a scope question, not a plumbing "
				"one.", gFacReads, gFacHits);
		}
		if (!ok || !res) { return ok; }

		// The object is now loaded from the record at its authored size. This
		// is the earliest moment its pixels exist, and the consumer has not
		// seen it yet - born correct, not corrected.
		cGZPersistResourceKey k;
		res->GetKey(k);
		if (k.type != kIconType || k.group != kIconGroup
			|| !InFixList(k.instance))
		{
			return ok;
		}

		cIGZBuffer* buf = nullptr;
		if (!res->QueryInterface(GZIID_cIGZBuffer,
				reinterpret_cast<void**>(&buf)) || !buf)
		{
			return ok;
		}
		const int sw = buf->Width();
		const int sh = buf->Height();
		if (sw >= 4 && sh >= 1 && sw <= 4096 && sh <= 4096 && (sw % 4) == 0)
		{
			const int cell    = sw / 4;
			const int newCell = RoundHalfUp(cell * gFacFactor);
			const int newW    = newCell * 4;
			const int newH    = ScaleDim(sh, gFacFactor);
			if (newW > sw
				&& EnlargeInPlace(buf, sw, sh, newW, newH, cell, newCell))
			{
				gFacHits++;
				if (gFacHits <= 8)
				{
					Logger::Get().WriteLine(LogLevel::Info,
						"IconSynth: FACTORY born-correct {%08X} %dx%d -> %dx%d "
						"(read #%u) - this instance is enlarged BEFORE the "
						"consumer that asked for it ever sees it.",
						k.instance, sw, sh, newW, newH, gFacReads);
				}
			}
		}
		buf->Release();
		return ok;
	}

	void InstallFactoryWrap(cIGZPersistResourceFactory* fac, float factor)
	{
		if (!fac || gFacInstance) { return; }
		void** vt = *reinterpret_cast<void***>(fac);
		if (!vt) { return; }
		for (int i = 0; i < kFacSlots; i++) { gFacVtCopy[i] = vt[i]; }
		gFacOrigRead = reinterpret_cast<FacReadFn>(vt[5]);   // Read
		gFacVtCopy[5] = reinterpret_cast<void*>(&FacReadThunk);
		gFacOrigVt = vt;
		gFacFactor = factor;
		*reinterpret_cast<void***>(fac) = gFacVtCopy;
		gFacInstance = fac;
		Logger::Get().WriteLine(LogLevel::Info,
			"IconSynth: factory wrap INSTALLED on %p (vt %p -> %p, Read slot 5 "
			"= %p). A reads=0 line later means the wrap never ran - that is an "
			"INSTRUMENT FAILURE, not proof the icons are fine.",
			static_cast<void*>(fac), static_cast<void*>(vt),
			static_cast<void*>(gFacVtCopy),
			reinterpret_cast<void*>(gFacOrigRead));
	}

	void EnlargeAndRegister(float factor)
	{
		if (factor <= 1.01f) { return; }
		if (gFixN <= 0)
		{
			Logger::Get().WriteLine(LogLevel::Info,
				"IconSynth: stage 2 - nothing uncovered, no work to do.");
			return;
		}

		cIGZPersistResourceManagerPtr rm;
		cIGZGraphicSystemPtr gs;
		if (!rm || !gs)
		{
			// NULL IS NOT EVIDENCE: without both services this reports zero
			// fixes for a reason that has nothing to do with the icons.
			Logger::Get().WriteLine(LogLevel::Info,
				"IconSynth: stage 2 ABORTED - resMan=%p gfxSys=%p. A zero count "
				"here is an INSTRUMENT FAILURE, not a clean bill of health.",
				static_cast<void*>(rm), static_cast<void*>(gs));
			return;
		}

		const DWORD t0 = GetTickCount();
		gMade = gMiss = gSkip = gFail = 0;

		// POSITIVE CONTROL FIRST. One icon we KNOW our packages enlarged: it
		// must come back at the scaled size. If it comes back 1x the fetch is
		// reading past our dats and every "uncovered" measurement below is
		// meaningless.
		if (gControlInst)
		{
			const cGZPersistResourceKey ck(kIconType, kIconGroup, gControlInst);
			cIGZBuffer* cb = nullptr;
			if (rm->GetResource(ck, GZIID_cIGZBuffer,
					reinterpret_cast<void**>(&cb), 0, nullptr) && cb)
			{
				Logger::Get().WriteLine(LogLevel::Info,
					"IconSynth: CONTROL {%08X} is one of OURS and reads back "
					"%dx%d (cell %d). At f=%.2f a covered icon must already be "
					"enlarged - if this says 44 tall the fetch is wrong, not "
					"the icons.",
					gControlInst, cb->Width(), cb->Height(), cb->Width() / 4,
					factor);
				cb->Release();
			}
			else
			{
				Logger::Get().WriteLine(LogLevel::Info,
					"IconSynth: CONTROL {%08X} DID NOT FETCH - the resource "
					"manager cannot see icon art at this point in boot, so "
					"stage 2 is running too early. Nothing below is evidence.",
					gControlInst);
			}
		}

		for (int i = 0; i < gFixN; i++)
		{
			const uint32_t inst = gFixList[i];
			const cGZPersistResourceKey key(kIconType, kIconGroup, inst);

			cIGZBuffer* src = nullptr;
			if (!rm->GetResource(key, GZIID_cIGZBuffer,
					reinterpret_cast<void**>(&src), 0, nullptr) || !src)
			{
				gMiss++;
				continue;
			}

			const int sw = src->Width();
			const int sh = src->Height();
			// A menu icon strip is FOUR states side by side. Anything that is
			// not a clean 4-way split is not the shape this fix understands,
			// and guessing at it is how the white line shipped.
			if (sw < 4 || sh < 1 || sw > 4096 || sh > 4096 || (sw % 4) != 0)
			{
				gSkip++;
				src->Release();
				continue;
			}

			const int cell    = sw / 4;
			const int newCell = RoundHalfUp(cell * factor);
			const int newW    = newCell * 4;
			// #158: HEIGHT USES THE OFFLINE RULE, not a bare round, so the
			// runtime and the shipped art agree at every tier.
			const int newH    = ScaleDim(sh, factor);

			// newCell MUST equal the cell the engine will draw. SlotThunk2<88>
			// writes RoundHalfUp(base * gTierF) into [0xF4], so the identical
			// expression is used here - matching the engine's arithmetic
			// exactly rather than approximating it (SC4 measure, don't infer).
			if (newW <= sw || gHoldN >= kHoldMax)
			{
				gSkip++;
				src->Release();
				continue;
			}

			// PATH A - REPLACE THE REGISTRATION. Non-destructive: it builds a
			// separate object and only swaps it in when every step succeeded,
			// so trying it first costs nothing and its failure is diagnostic.
			bool done = false;
			cIGZPersistResource* res =
				BuildEnlarged(gs, src, newW, newH, cell, newCell);
			if (res)
			{
				res->SetKey(key);
				// Replace, don't shadow: an old registration for the same key
				// must go first or the manager may keep handing out the 1x
				// original.
				rm->UnregisterResource(key);
				if (rm->RegisterResource(key, *res))
				{
					gHold[gHoldN++] = res;   // reference deliberately retained
					done = true;
					if (gMade < 8)
					{
						Logger::Get().WriteLine(LogLevel::Info,
							"IconSynth: BORN CORRECT (registered) {%08X} "
							"%dx%d -> %dx%d (cell %d -> %d at f=%.2f)",
							inst, sw, sh, newW, newH, cell, newCell, factor);
					}
				}
				else
				{
					Logger::Get().WriteLine(LogLevel::Info,
						"IconSynth:   step RegisterResource FAILED for {%08X}.",
						inst);
					res->Release();
				}
			}

			// PATH B - RESIZE THE OBJECT THE MANAGER ALREADY HANDS OUT. No
			// registration, no factory, no hook: the one object every consumer
			// fetches simply becomes the right size.
			if (!done)
			{
				done = EnlargeInPlace(src, sw, sh, newW, newH, cell, newCell);
				if (done)
				{
					// The manager's cache is refcounted and collects what
					// nobody holds. Releasing here would let the 1x original
					// reload mid-session with every gate still green - the
					// exact shape of the three packages that rotted. So the
					// reference stays.
					if (gHoldN < kHoldMax) { gHold[gHoldN++] = src; }
					if (gMade < 8)
					{
						Logger::Get().WriteLine(LogLevel::Info,
							"IconSynth: BORN CORRECT (in place) {%08X} "
							"%dx%d -> %dx%d (cell %d -> %d at f=%.2f)",
							inst, sw, sh, newW, newH, cell, newCell, factor);
					}
					gMade++;
					continue;   // reference held on purpose - no Release
				}
			}

			if (done) { gMade++; }
			else
			{
				gFail++;
				if (gFail <= 4)
				{
					Logger::Get().WriteLine(LogLevel::Info,
						"IconSynth: BOTH PATHS FAILED for {%08X} (%dx%d -> "
						"%dx%d) - the original is untouched, so this icon "
						"keeps its old behaviour.",
						inst, sw, sh, newW, newH);
				}
			}
			src->Release();
		}

		// ---- THE DISCRIMINATING RE-FETCH ----------------------------------
		// On screen the doubling stopped but the art still draws at 1x in the
		// top-left, while our object measures 528x132. Both cannot be the same
		// object, so ask the manager for it AGAIN, two different ways, and
		// print the POINTERS - that single comparison separates "the fix did
		// not take" from "the consumer is handed a different instance".
		//
		//   same ptr, enlarged  -> shared cache holds our fix; the strip must
		//                          be getting its copy from somewhere else
		//   new ptr,  1x        -> every fetch mints a fresh object from the
		//                          DBPF, so mutating one instance can never be
		//                          seen by anyone. The cure is then the
		//                          FACTORY (cIGZPersistResourceFactory), which
		//                          is the only point every instance passes
		//                          through.
		for (int i = 0; i < gFixN && i < 4; i++)
		{
			const cGZPersistResourceKey key(kIconType, kIconGroup, gFixList[i]);
			cIGZBuffer* shared = nullptr;
			cIGZBuffer* priv = nullptr;
			const bool gotShared = rm->GetResource(key, GZIID_cIGZBuffer,
				reinterpret_cast<void**>(&shared), 0, nullptr) && shared;
			const bool gotPriv = rm->GetPrivateResource(key, GZIID_cIGZBuffer,
				reinterpret_cast<void**>(&priv), 0, nullptr) && priv;
			Logger::Get().WriteLine(LogLevel::Info,
				"IconSynth: RE-FETCH {%08X} fixedPtr=%p | GetResource=%p %dx%d "
				"| GetPrivateResource=%p %dx%d | hasRegistered=%d",
				gFixList[i],
				(i < gHoldN) ? static_cast<void*>(gHold[i]) : nullptr,
				static_cast<void*>(shared),
				gotShared ? shared->Width() : -1,
				gotShared ? shared->Height() : -1,
				static_cast<void*>(priv),
				gotPriv ? priv->Width() : -1,
				gotPriv ? priv->Height() : -1,
				rm->HasRegisteredResource(key) ? 1 : 0);
			if (shared) { shared->Release(); }
			if (priv) { priv->Release(); }
		}

		// If instances are minted per consumer, the FACTORY is the only point
		// every one of them passes through - so find out now whether there is
		// one to wrap, in the same launch rather than the next.
		cIGZPersistResourceFactory* fac = nullptr;
		const bool haveFac = rm->FindObjectFactory(kIconType, &fac);
		Logger::Get().WriteLine(LogLevel::Info,
			"IconSynth: factory for type %08X: found=%d ptr=%p (factoryCount=%u)"
			" - this is the wrap point if every consumer gets its own instance.",
			kIconType, haveFac ? 1 : 0, static_cast<void*>(fac),
			rm->GetFactoryCount());
		if (haveFac && fac) { InstallFactoryWrap(fac, factor); }

		// "registered" was the wrong word once this grew a second path, and a
		// log line that names the wrong mechanism sends the next reader to the
		// wrong code (#77). Say FIXED, and say how.
		Logger::Get().WriteLine(LogLevel::Info,
			"IconSynth: stage 2 done in %u ms - fixed=%d notFound=%d "
			"skipped=%d failed=%d of %d uncovered%s. Every fixed icon is held "
			"by reference so the cache cannot drop it back to 1x.",
			GetTickCount() - t0, gMade, gMiss, gSkip, gFail, gFixN,
			gFixTruncated ? " (LIST TRUNCATED at 512 - more remain)" : "");
	}
}

namespace ScaleTier
{
	float Decide(int width, int height)
	{
		if (width <= 0 || height <= 0)
		{
			return 1.0f;
		}

		// Density cap: never scale past "everything feels like 800x600".
		const float capW = width / 800.0f;
		const float capH = height / 600.0f;
		const float cap = capW < capH ? capW : capH;

		for (int i = 0; i < kPackageCount; i++)
		{
			const Package& pkg = kPackages[i];
			if (!PackageInstalled(pkg))
			{
				continue;
			}
			if (kWidestDesignPx * pkg.factor <= width
				&& kTallestDesignPx * pkg.factor <= height
				&& pkg.factor <= cap)
			{
				return pkg.factor;
			}
		}
		return 1.0f; // stock
	}

	void EnlargeUncoveredIcons(float factor)
	{
		IconSynth::EnlargeAndRegister(factor);
	}

	// ICONSYNTH stage 1 (task #149) - SEPARATE FROM SyncStaticLayers ON PURPOSE.
	//
	// ⛔ IT USED TO LIVE INSIDE SyncStaticLayers AND THAT WAS A REAL BUG.
	// SyncStaticLayers RAN ONLY on the AutoScale path back then (⚠ NO LONGER
	// TRUE since v3.0.2/#182 - manual tiers with ScaleAll=1 sync too; the
	// second instance of this exact lesson). The icon SCAN has nothing to do
	// with package placement, so riding along in there meant that with
	// AutoScale=0 - A SUPPORTED USER SETTING, not just the test rig - the scan
	// never ran, UNCOVERED stayed 0, stage 2 reported "nothing to do", and every
	// third-party icon silently went back to being broken.
	//
	// Caught 2026-08-15 by flipping to the 1.5x tier with Set-Tier.ps1: the icon
	// broke and the log said `AutoScale off: ... layers untouched` two lines
	// above `stage 2 - nothing uncovered`. The tier was innocent; the COUPLING
	// was the defect.
	//
	// THE LAW: a subsystem must be gated on the condition IT actually depends
	// on. This one depends only on "is the factor > 1", never on how that factor
	// was decided. Attaching it to a convenient neighbour makes it inherit that
	// neighbour's gate, silently.
	void ScanUncoveredIcons(float factor)
	{
		if (factor <= 1.0f) { return; }
		wchar_t plugDir[MAX_PATH];
		DllDir(plugDir, MAX_PATH);
		size_t pl = wcslen(plugDir);
		while (pl > 0 && plugDir[pl - 1] == 92) { plugDir[--pl] = 0; }
		IconSynth::ScanAndReport(plugDir, factor);
	}

	void SyncStaticLayers(float factor)
	{
		// PACKAGES live beside the DLL in Documents\SimCity 4\Plugins (dats
		// + per-factor font sources; the user's plugins-only requirement).
		// ONE exception, forced by the engine: the game probes the loose
		// FontStyle.ini in <install>\Plugins ONLY (never Documents - the
		// 2026-07-22 "Documents works" test was a timing confound), so the
		// active font is mirrored there each boot. That write stays inside
		// a Plugins folder and is DLL-managed - no manual install steps.
		wchar_t docPlugins[MAX_PATH];
		DllDir(docPlugins, MAX_PATH);
		wchar_t instPlugins[MAX_PATH];
		InstallPluginsDir(instPlugins, MAX_PATH);

		// #182 GUARD (adversarial review 2026-08-17): now that MANUAL factors
		// also reach this function, an unvalidated ScaleFactor (2.5, or 3.0 on
		// an install carrying only the 2x package) would stash EVERY package
		// and activate NOTHING - the whole art+font layer silently vanishing
		// while geometry still scales. A factor above stock that matches NO
		// kPackages entry refuses loudly and leaves the files exactly as they
		// are. Deliberate stock (factor <= 1.01) keeps its disable-all
		// semantics - "all layers dormant" is that path's contract.
		if (factor > 1.01f)
		{
			bool anyMatch = false;
			for (int i = 0; i < kPackageCount; i++)
			{
				if (factor >= kPackages[i].factor - 0.01f
					&& factor <= kPackages[i].factor + 0.01f)
				{
					anyMatch = true;
					break;
				}
			}
			if (!anyMatch)
			{
				Logger::Get().WriteLine(
					LogLevel::Info,
					"ScaleTier: NO package matches factor %.2f - static layers "
					"LEFT AS-IS (refusing to stash every package). Supported "
					"factors are 1.5 / 2 / 3; fix ScaleFactor in the ini.",
					factor);
				return;
			}
		}

		// Select exactly the chosen factor's package: gate every known
		// package's dats (active only for the match), and install the
		// matching font source as the live FontStyle.ini (or remove it at
		// stock). Untagged legacy 2x names are migrated to -2x tags first
		// so old installs keep working.
		MigrateLegacyUntagged2x(docPlugins);

		// Resolve the third-party dependencies ONCE per boot (one directory
		// walk each, not one per tier). A package whose owning mod is gone -
		// or was updated out from under the copy we built - must be gated OFF
		// no matter which tier is active.
		bool depOk[kThirdPartyDepCount] = {};
		for (int d = 0; d < kThirdPartyDepCount; d++)
		{
			const ThirdPartyDep& dep = kThirdPartyDeps[d];
			wchar_t hit[MAX_PATH] = {};
			DWORD sz = 0;
			bool present = FindPluginFile(
				docPlugins, dep.modFile, dep.prefixMatch, 4, hit, MAX_PATH, &sz);
			bool sizeOk = (dep.modSize == 0) || (sz == dep.modSize);
			if (present && sizeOk && dep.modFile2 != nullptr)
			{
				wchar_t hit2[MAX_PATH] = {};
				DWORD sz2 = 0;
				const bool p2 = FindPluginFile(docPlugins, dep.modFile2,
					dep.prefixMatch, 4, hit2, MAX_PATH, &sz2);
				const bool s2 = (dep.modSize2 == 0) || (sz2 == dep.modSize2);
				if (!p2 || !s2)
				{
					// Report the SECOND file as the reason, not the first -
					// a message naming the file that was fine would send the
					// next reader looking in the wrong place.
					present = p2;
					sizeOk = s2;
					sz = sz2;
					swprintf_s(hit, L"%s", dep.modFile2);
				}
			}
			depOk[d] = present && sizeOk;
			if (!present)
			{
				Logger::Get().WriteLine(
					LogLevel::Info,
					"ScaleTier: %ls dep ABSENT (%ls) -> disabled; the stock "
					"package takes over.", dep.package, dep.modFile);
			}
			else if (!sizeOk)
			{
				// Loud on purpose: our copy is now stale, the dialog falls
				// back to runtime scaling, and someone has to re-sync
				// thirdparty-src\ and rebuild.
				Logger::Get().WriteLine(
					LogLevel::Info,
					"ScaleTier: %ls dep CHANGED (%ls is %u bytes, built from "
					"%u) -> disabled; re-extract and rebuild.",
					dep.package, dep.modFile, sz, dep.modSize);
			}
			else
			{
				Logger::Get().WriteLine(
					LogLevel::Info, "ScaleTier: %ls dep ok (%ls).",
					dep.package, hit);
			}
		}

		const wchar_t* activeTag = nullptr;
		for (int i = 0; i < kPackageCount; i++)
		{
			const Package& pkg = kPackages[i];
			const bool match =
				factor >= pkg.factor - 0.01f && factor <= pkg.factor + 0.01f;
			if (match)
			{
				activeTag = pkg.tag;
			}
			SyncDat(docPlugins, L"z_SC4UIScale_SelectiveArt", pkg.tag, match);
			SyncDat(docPlugins, L"z_SC4UIScale_DialogStatic", pkg.tag, match);
			SyncDat(docPlugins, L"z_SC4UIScale_ItemIcons", pkg.tag, match);
			// SUBFOLDER package (v2.17.1): overrides for icons that live in
			// OTHER Documents-plugin subfolders (the submenus mod's 55). LOAD
			// ORDER LAW (proven 2026-07-29): root Plugins FILES load BEFORE
			// subfolders, so a root dat can NEVER override a subfolder dat -
			// such overrides must sit in a folder sorting after the target
			// ("zzz-SC4UIScale" beats "150-mods").
			SyncDat(docPlugins, L"zzz-SC4UIScale\\z_SC4UIScale_ItemIconsSub",
				pkg.tag, match);
			// #196 (2026-08-18): CsiIcons was MISSING from this list entirely -
			// zero occurrences of "CsiIcons" anywhere in this file - while
			// Deploy-OnGameClose.ps1 hard-copies the 15x build to the plain
			// .dat name and the other two as .x1-disabled. Its own comment
			// there says "the ACTIVE tier keeps its plain .dat name, the other
			// two ship .x1-disabled and ScaleTier renames" - a dependency on
			// a call that did not exist. So the package NEVER followed the
			// tier: it stayed on whatever the deploy hard-coded, which is 1.5x.
			//
			// MEASURED, and this is how it surfaced: with AutoScale on and the
			// tier resolved to 2x, Set-StockCompare's enumeration listed
			// z_SC4UIScale_CsiIcons-15x.dat as LIVE while every sibling was
			// -2x and CsiIcons-2x.dat sat .x1-disabled beside it. All three
			// builds exist and carry the same 16 instances, so this was never
			// a build gap - the file was simply never renamed.
			//
			// ⭐ THIRD TIME THIS SHAPE HAS SHIPPED. #119 was WarriorUI missing
			// its SyncDat call; the deploy block above records three more
			// packages that rotted by being hand-placed and never wired. The
			// standing law is "a package is not done until it is in the
			// MANIFEST", and the manifest is TWO lists, not one: the deploy
			// that places the files AND this list that follows the tier.
			// Wiring only the first is what happened here, on the same day the
			// package was added.
			//
			// No dependency gate: CsiIcons is built from the player's own Maxis
			// archives, so unlike CamUI/WarriorUI/ThirdPartyUI there is no mod
			// whose presence it must be conditioned on. Tier-gated only, which
			// is exactly the ItemIconsSub shape directly above.
			SyncDat(docPlugins, L"zzz-SC4UIScale\\z_SC4UIScale_CsiIcons",
				pkg.tag, match);
			// SUBFOLDER package (#149): ItemIcons that a THIRD-PARTY LOT
			// supplies and no package of ours covered - the Lighted Palm Plaza
			// case. Built by tools\itemicons\build_uncovered_icons.py, which
			// discovers the set exactly the way the boot scan does rather than
			// from a list, so a lot published next year is covered without
			// editing anything.
			//
			// SUBFOLDER for the same load-order reason as its neighbour above:
			// the custom lot sits in 900-custom-lots\, and a ROOT dat can never
			// override a subfolder dat. "zzz-SC4UIScale" sorts after it.
			//
			// UNGATED, deliberately, unlike SaveWarningUI/CamUI: this package
			// contains ONLY overrides keyed to a third-party TGI. Remove the
			// mod and the TGI is referenced by nothing, so the entry is inert
			// rather than wrong - there is no state where a stale copy shows
			// the player something broken. A dependency gate here would fail
			// the whole package on a harmless upstream re-release (#139's
			// reason for presence-only gating, one step further).
			SyncDat(docPlugins, L"zzz-SC4UIScale\\z_SC4UIScale_UncoveredIcons",
				pkg.tag, match);
			// SUBFOLDER package (v2.38.0, task #79c): 2x copies of the two
			// in-city quit/exit confirm scripts, built from the save-warning
			// MOD's versions because that mod replaces them from 150-mods\ and
			// beats our root DialogStatic package. Gated on that mod: with it
			// gone, this turns off and our root stock-derived copy - which
			// then wins over SimCity_1.dat - scales the stock dialog instead.
			SyncDat(docPlugins, L"zzz-SC4UIScale\\z_SC4UIScale_SaveWarningUI",
				pkg.tag, match && DepOkByName(
					L"zzz-SC4UIScale\\z_SC4UIScale_SaveWarningUI", depOk));
			// SUBFOLDER package (v2.38.3): 2x copies of the SIX dialog-static
			// targets CAM replaces, built from CAM's own scripts. Gated on CAM
			// being installed and unchanged - with CAM gone this turns off and
			// our root stock-derived copies take over, which is the correct
			// unmodded behaviour.
			SyncDat(docPlugins, L"zzz-SC4UIScale\\z_SC4UIScale_CamUI",
				pkg.tag, match && DepOkByName(
					L"zzz-SC4UIScale\\z_SC4UIScale_CamUI", depOk));
			// SUBFOLDER package (v2.20.2, task #44): 2x-transformed copies of
			// .UI scripts that OTHER plugins override wholesale. CoriBoom's
			// 36 Slot Building Styles UI replaces the stock Building Style
			// Control script from 150-mods\, so by the same load-order law our
			// root package never won and that panel rendered corrupted.
			// v2.38.0: gated on CoriBoom's mod for the same reason - with the
			// mod removed our copy of ITS script would otherwise keep its
			// 36-slot UI on screen (measured: our 532x640 beats the stock
			// 531x406). Presence only, no size check: see kThirdPartyDeps.
			SyncDat(docPlugins, L"zzz-SC4UIScale\\z_SC4UIScale_ThirdPartyUI",
				pkg.tag, match && DepOkByName(
					L"zzz-SC4UIScale\\z_SC4UIScale_ThirdPartyUI", depOk));
			// SUBFOLDER package (v2.47.0, task #94): 2x copies of warrior's
			// "God Terraforming in Mayor Mode" scripts + art.
			//
			// #119 (v2.71.3): THIS CALL WAS MISSING. The kThirdPartyDeps row
			// (see :148) existed and its depOk was computed every boot - and
			// then DISCARDED, because nothing ever asked for it. The dat was
			// therefore NEVER TIER-GATED: it stayed active at the stock tier
			// (where every other package is stashed) and, worse, stayed active
			// with warrior's mod REMOVED - exactly the state its own comment
			// says must disable us, since our copy hard-codes that mod's rects.
			// MEASURED: z_SC4UIScale_WarriorUI-2x.dat was live in Plugins with
			// no .x1-disabled twin while the other subfolder packages had one.
			// Gated now on the same EXACT NAME + SIZE pair as SaveWarningUI.
			SyncDat(docPlugins, L"zzz-SC4UIScale\\z_SC4UIScale_WarriorUI",
				pkg.tag, match && DepOkByName(
					L"zzz-SC4UIScale\\z_SC4UIScale_WarriorUI", depOk));
			// SUBFOLDER package (#139, 2026-08-05): 2x/1.5x/3x copies of NAM's
			// OWN 381 ItemIcon strips. It MUST live in zzz-SC4UIScale\ and not
			// the root ItemIcons dat: root Plugins FILES load before
			// SUBFOLDERS (the load-order law above), and NAM is a subfolder
			// (770-network-addon-mod\), so a root override could never win.
			// "zzz-" sorts after "770-", so this one does.
			SyncDat(docPlugins, L"zzz-SC4UIScale\\z_SC4UIScale_NamIcons",
				pkg.tag, match && DepOkByName(
					L"zzz-SC4UIScale\\z_SC4UIScale_NamIcons", depOk));
		}
		// Install root FIRST (the copy the game reads); Documents mirror
		// second (kept for inspectability + package consistency).
		SyncFont(docPlugins, instPlugins, activeTag);
		SyncFont(docPlugins, docPlugins, activeTag);
	}
}

