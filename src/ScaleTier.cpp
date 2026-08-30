#include "ScaleTier.h"
#include "Logger.h"

// #149 stage 2. Everything the resource-level fix needs is vendored SDK - no
// field offsets, no fake structs, no raw memory arithmetic on engine objects.
#include "cGZPersistResourceKey.h"
#include "cIGZPersistResource.h"
#include "cIGZPersistResourceManager.h"
#include "cIGZPersistResourceFactory.h"
// #201 SEGMENT CENSUS probe: the registered-DBPF walk that would let a tier
// be excluded at LOAD time instead of renamed on disk.
#include "cIGZPersistDBSegment.h"
#include "cIGZPersistDBSegmentMultiPackedFiles.h"
#include "cRZBaseString.h"
#include "cIGZBuffer.h"
#include "cIGZGraphicSystem.h"
#include "GZServPtrs.h"

#define WIN32_LEAN_AND_MEAN
#include <Windows.h>

#include <cwchar>
#include <cstdlib>
#include <cstdint>
#include <filesystem>
#include <string>

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

	// v4.5.0: the tier decision and the dependency verdicts happen at DLL
	// load; load-time exclusion needs both again at PostAppInit. Stashed
	// rather than recomputed, so the two mechanisms cannot disagree about
	// which packages are legitimate - two copies of a rule are two rules.
	wchar_t gArmedTag[8] = {};
	bool    gArmedTagValid = false;

	bool    gArmedDepOk[32] = {};
	bool    gArmedDepOkValid = false;


	void DllDir(wchar_t* out, size_t outLen)
	{
		GetModuleFileNameW(reinterpret_cast<HMODULE>(&__ImageBase), out, static_cast<DWORD>(outLen));
		wchar_t* s = wcsrchr(out, L'\\');
		if (s)
		{
			*(s + 1) = L'\0';
		}
	}

	// v4.2.0 (subfolder move): the Documents PLUGINS ROOT, distinct from
	// DllDir(). With the DLL living in Plugins\010-SC4UIScale\, "beside the
	// DLL" is no longer the Plugins root - and seven subsystems (dependency
	// gates, the uncovered-icon scan, web-button detection, the
	// SC4GraphicsOptions.ini read/write pair) need the ROOT to find OTHER
	// mods' files. Walk up from DllDir until the leaf directory is named
	// "Plugins" (at most 2 levels - the DLL is designed to sit exactly one
	// level down); if no ancestor is named Plugins (a dev tree, or a user
	// who renamed the folder chain), fall back to DllDir and SAY SO - a
	// silent wrong root here reads as "no third-party mods installed".
	// The resolver PROPER, silent. Split out 2026-08-29 (v4.4.0 root
	// cleanup): the ini and log paths are now resolved BEFORE Logger::Init,
	// so the warning branch below cannot run there - it would go to a file
	// that does not exist yet AND would latch s_warned, swallowing the one
	// warning a real fallback is entitled to. Returns whether an ancestor
	// named "Plugins" was actually found; on failure `out` still holds
	// DllDir(), which is the documented fallback.
	bool PluginsRootQuiet(wchar_t* out, size_t outLen)
	{
		DllDir(out, outLen);
		wchar_t probe[MAX_PATH];
		wcscpy_s(probe, MAX_PATH, out);
		for (int up = 0; up < 3; up++)
		{
			// probe ends with a backslash; the leaf name sits between the
			// last two separators.
			size_t len = wcslen(probe);
			if (len < 2) { break; }
			probe[len - 1] = L'\0';                    // drop trailing sep
			wchar_t* leaf = wcsrchr(probe, L'\\');
			if (!leaf) { break; }
			if (_wcsicmp(leaf + 1, L"Plugins") == 0)
			{
				probe[len - 1] = L'\\';                // restore trailing sep
				wcscpy_s(out, outLen, probe);
				return true;
			}
			*(leaf + 1) = L'\0';                       // ascend one level
		}
		return false;
	}

	void PluginsRoot(wchar_t* out, size_t outLen)
	{
		if (PluginsRootQuiet(out, outLen)) { return; }
		// Fallback: DllDir itself. Logged once - every resolver states its
		// resolved value, and this one failing silently would blind every
		// third-party gate.
		static bool s_warned = false;
		if (!s_warned)
		{
			s_warned = true;
			Logger::Get().WriteLine(LogLevel::Info,
				"ScaleTier: PluginsRoot - no ancestor named 'Plugins' within "
				"2 levels of the DLL; falling back to the DLL's own folder. "
				"Third-party dependency detection may be blind.");
		}
	}

	// v4.4.0 ROOT CLEANUP: names a file inside 010-SC4UIScale\, resolved
	// WITHOUT logging so the very first callers (the ini, and the log
	// itself) can use it before Logger::Init. Every loose file this mod
	// used to drop beside the DLL now goes through here; the DLL alone
	// stays at the Plugins root, because the game's DLL loader is
	// top-level only - measured, see OurPackagesDir below.
	// Defined below with the discovery block; declared here because
	// OurFilePath is the earliest caller (the ini and log resolve through
	// it before Logger::Init).
	void ResolveOurDirs();
	const wchar_t* EarlyDirPtr();

	// v4.5.0: THE INI GOES BACK TO THE PLUGINS ROOT, and only the ini.
	//
	// v4.4.0 moved it into our folder for tidiness. MEASURED against sc4pac
	// 0.10.0 by installing a throwaway channel: that is wrong under a package
	// manager, in two different ways.
	//   * In the package folder it is DESTROYED BY EVERY UPDATE. An update
	//     deletes <group>.<name>.<oldver>.sc4pac wholesale and creates a new
	//     versioned folder - measured, v1.0.0 -> v2.0.0 - so the player's tier
	//     choice would not survive a single package bump.
	//   * Shipping it with `isIni: true` is worse, not better: it lands at the
	//     root RENAMED to <stem>_sc4pacnew.ini, is never activated, and is
	//     deleted on uninstall even after the user has edited it.
	// The root copy is the only one that survives both. Measured control: an
	// activated root ini came through a v1->v2 update byte-identical while the
	// versioned folder was wiped.
	//
	// So we ship NO ini at all; the DLL creates this one on first run. It is
	// the second file at the root after the DLL - which is still fewer than
	// the two or three every other DLL mod leaves there.
	void OurIniPath(wchar_t* out, size_t outLen)
	{
		if (!out || outLen == 0) { return; }
		out[0] = 0;
		wchar_t root[MAX_PATH] = {};
		PluginsRootQuiet(root, MAX_PATH);
		const wchar_t* name = L"SC4UIScale.ini";
		if (wcslen(root) + wcslen(name) + 1 > outLen) { return; }
		wcscpy_s(out, outLen, root);
		wcscat_s(out, outLen, name);
	}

	void OurFilePath(const wchar_t* name, wchar_t* out, size_t outLen)
	{
		if (!out || outLen == 0) { return; }
		out[0] = L'\0';
		// v4.5.0: the folder is DISCOVERED, not named.
		const wchar_t* sub = L"";
		const wchar_t* root = EarlyDirPtr();
		// LENGTH-CHECKED, not wcscat_s-and-hope: the secure-CRT concat
		// ABORTS THE PROCESS on truncation, and this path is now one
		// folder deeper than the beside-the-DLL one it replaces. On an
		// over-long path we hand back an EMPTY string - every consumer
		// here degrades to its default on a path it cannot open, which
		// is a setting lost, not a game killed.
		if (wcslen(root) + wcslen(sub) + wcslen(name) + 1 > outLen) { return; }
		wcscpy_s(out, outLen, root);
		wcscat_s(out, outLen, sub);
		wcscat_s(out, outLen, name);
	}

	// v4.2.0: where OUR packages and fonts live. MEASURED on the move's
	// maiden boot: SimCity 4's DAT scan is recursive but its DLL LOADER IS
	// TOP-LEVEL ONLY - a DLL in a subfolder produces no log, no director,
	// nothing. So the DLL (and its beside-the-DLL ini/log) stays at the
	// Plugins ROOT, while every package and font source lives in
	// Plugins\010-SC4UIScale\ - which this resolver names.
	// ============ v4.5.0 FOLDER DISCOVERY - NOT FOLDER NAMES ==============
	// Through v4.4.0 this mod hard-coded "010-SC4UIScale" and
	// "zzz-SC4UIScale" in 82 places. sc4pac names package folders ITSELF,
	// with the version baked in (`<group>.<name>.<version>.sc4pac` inside a
	// numbered subfolder), so every one of those literals resolves to
	// nothing under a package-manager install - which is why sc4pac could
	// not install this mod at all, not merely uninstall it badly.
	//
	// FOUND BY CONTENT, NEVER BY NAME. A folder is ours if it holds files we
	// ship. Which of the two it is, is decided by WHICH packages it holds:
	//   EARLY    - holds SelectiveArt. Must LOSE to CAM/NAM: it carries
	//              stock-derived copies that a real mod is entitled to beat.
	//   OVERRIDE - holds CamUI / ItemIconsSub / UncoveredIcons. Must WIN:
	//              these are built FROM those mods' own art.
	// One folder holding both is legal and both handles point at it (a
	// single-package install); a folder holding neither marker is not ours.
	//
	// Scans two levels: our own top-level layout, and `<subfolder>/<pkg>` as
	// sc4pac lays it out. Falls back to the v4.2.0 names and SAYS SO - a
	// silently wrong folder here disarms every package we own.
	// ==== BEGIN FOLDER-DISCOVERY ==========================================
	// Everything between these sentinels is lifted VERBATIM by
	// _tests/Test-FolderDiscovery.ps1, compiled standalone and run against
	// simulated Plugins trees. Extraction is by sentinel, never by line
	// number, so the test cannot silently drift away from the code it claims
	// to cover. The only external dependency permitted in here is
	// PluginsRootQuiet, which the harness stubs.
	struct OurDirs
	{
		bool     resolved;
		bool     earlyFound;
		bool     overrideFound;
		wchar_t  early[MAX_PATH];
		wchar_t  override_[MAX_PATH];
		wchar_t  earlyLeaf[64];
		wchar_t  overrideLeaf[64];
	};
	OurDirs gOurDirs = {};

	// Which marker does this directory carry? bit0 = early, bit1 = override.
	//
	// EVERY PATTERN HERE MUST MATCH A FILE WE ACTUALLY SHIP. Two of the
	// original six did not, and nothing noticed because the survivors happened
	// to be enough:
	//   * `ItemIcons-*` (hyphen) is a v2.x tier-tagged name. v4.5.0 ships
	//     `z_SC4UIScale_ItemIcons.dat` / `.2x.uipay`, so the hyphen form never
	//     matched again. The dot is load-bearing: a bare `ItemIcons*` would
	//     also match `ItemIconsSub`, which lives in the OVERRIDE folder, and
	//     would set the early bit on it.
	//   * `UncoveredIcons*` is synthesized at runtime and is not a shipped
	//     file at all, so it can never classify a freshly installed tree.
	// Replaced with names verified present in dist/SC4UIScale-v4.5.0/Plugins/.
	int ClassifyDir(const wchar_t* dir)
	{
		struct Marker { const wchar_t* pat; int bit; };
		const Marker markers[] = {
			{ L"z_SC4UIScale_SelectiveArt*",    1 },
			{ L"z_SC4UIScale_DialogStatic*",    1 },
			{ L"z_SC4UIScale_ItemIcons.*",      1 },
			{ L"z_SC4UIScale_ItemIcons-*",      1 },   // pre-4.5.0 trees
			{ L"z_SC4UIScale_CamUI*",           2 },
			{ L"z_SC4UIScale_ItemIconsSub*",    2 },
			{ L"z_SC4UIScale_ThirdPartyUI*",    2 },
			{ L"z_SC4UIScale_SelectorUI*",      2 },
		};
		int bits = 0;
		for (const Marker& m : markers)
		{
			wchar_t pat[MAX_PATH];
			swprintf_s(pat, L"%s%s", dir, m.pat);
			WIN32_FIND_DATAW fd = {};
			HANDLE h = FindFirstFileW(pat, &fd);
			if (h != INVALID_HANDLE_VALUE) { bits |= m.bit; FindClose(h); }
		}
		return bits;
	}

	// How many directories carried each marker set. First match still WINS -
	// this only exists so a second candidate is REPORTED instead of silently
	// losing. A stale hand-installed 010-SC4UIScale\ sorts before 050-load-first
	// and would quietly out-rank the sc4pac-managed package on a migration.
	int gEarlyCandidates = 0;
	int gOvrCandidates = 0;

	// DEPTH 3, and the number is a measurement, not a margin.
	//
	// sc4pac installs a package into `Plugins\<subfolder>\<grp>.<name>.<ver>.sc4pac\`
	// and strips the longest common directory prefix from the package's files.
	// Our two packages therefore land at DIFFERENT depths, which is exactly the
	// trap:
	//   override pkg - every file shares `/Plugins/zzz-SC4UIScale/`, so that
	//                  prefix is stripped and the markers sit at DEPTH 2:
	//                  Plugins\900-overrides\<pkg>.sc4pac\
	//   early pkg    - it also ships the DLL at `/Plugins/`, so the common
	//                  prefix is only `/Plugins/` and `010-SC4UIScale/` is
	//                  PRESERVED, putting the markers at DEPTH 3:
	//                  Plugins\050-load-first\<pkg>.sc4pac\010-SC4UIScale\
	// At the old cap of 2 the override half resolved and the early half fell
	// back to a `Plugins\010-SC4UIScale\` that does not exist - which
	// MigrateRootLooseFiles then creates, empty. ArmOne finds no payload, logs
	// "NO PAYLOAD AT ALL" and leaves the installed .dat alone; those files are
	// byte-identical to the 2x payloads, so SelectiveArt / ItemIcons /
	// DialogStatic / WebText stay pinned at 2x at EVERY tier while the override
	// half arms correctly. A mixed-factor screen, from one comparison.
	//
	// Cost: directory metadata only, and SC4's own plugin scan already walks
	// this whole tree recursively reading DBPF headers. Measured on the live
	// tree: 86 directories exist within 4 levels.
	void ScanForOurDirs(const wchar_t* dir, int depth, int& earlyBits, int& ovrBits)
	{
		if (depth > 3) { return; }
		wchar_t pat[MAX_PATH];
		swprintf_s(pat, L"%s*", dir);
		WIN32_FIND_DATAW fd = {};
		HANDLE h = FindFirstFileW(pat, &fd);
		if (h == INVALID_HANDLE_VALUE) { return; }
		do
		{
			if (fd.cFileName[0] == L'.') { continue; }
			if (!(fd.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY)) { continue; }
			wchar_t sub[MAX_PATH];
			swprintf_s(sub, L"%s%s\\", dir, fd.cFileName);
			const int bits = ClassifyDir(sub);
			if (bits & 1)
			{
				++gEarlyCandidates;
				if (!earlyBits)
				{
					earlyBits = 1;
					wcscpy_s(gOurDirs.early, MAX_PATH, sub);
					wcscpy_s(gOurDirs.earlyLeaf, 64, fd.cFileName);
				}
			}
			if (bits & 2)
			{
				++gOvrCandidates;
				if (!ovrBits)
				{
					ovrBits = 1;
					wcscpy_s(gOurDirs.override_, MAX_PATH, sub);
					wcscpy_s(gOurDirs.overrideLeaf, 64, fd.cFileName);
				}
			}
			// Never descend into a folder that is already one of ours.
			if (!bits) { ScanForOurDirs(sub, depth + 1, earlyBits, ovrBits); }
			// The walk deliberately does NOT stop once both are found. Stopping
			// early is what made a second candidate invisible, and "which of
			// the two did we pick" is the only question worth asking on a
			// half-migrated install.
		} while (FindNextFileW(h, &fd));
		FindClose(h);
	}

	void ResolveOurDirs()
	{
		if (gOurDirs.resolved) { return; }
		gOurDirs.resolved = true;
		wchar_t root[MAX_PATH] = {};
		PluginsRootQuiet(root, MAX_PATH);
		int e = 0, o = 0;
		gEarlyCandidates = 0;
		gOvrCandidates = 0;
		ScanForOurDirs(root, 1, e, o);
		if (!e)
		{
			swprintf_s(gOurDirs.early, L"%s010-SC4UIScale\\", root);
			wcscpy_s(gOurDirs.earlyLeaf, 64, L"010-SC4UIScale");
		}
		if (!o)
		{
			swprintf_s(gOurDirs.override_, L"%szzz-SC4UIScale\\", root);
			wcscpy_s(gOurDirs.overrideLeaf, 64, L"zzz-SC4UIScale");
		}
		gOurDirs.earlyFound = (e != 0);
		gOurDirs.overrideFound = (o != 0);
		// NO LOGGING HERE. The ini and log paths resolve through this and are
		// needed before Logger::Init exists - the same trap PluginsRootQuiet
		// was split to avoid. The director calls LogOurDirs() once the logger
		// is up.
	}
	// ==== END FOLDER-DISCOVERY ============================================

	// ============ THE STARTER INI ==========================================
	// v4.5.0 stopped shipping an ini - correctly, because a package manager
	// deletes the versioned package folder on every update and an ini kept
	// inside it loses the player's tier on each version bump. What it did NOT
	// do was create one instead, and the channel metadata claimed it did.
	//
	// MEASURED on a real sc4pac install (2026-08-30): no ini was created, so
	// Settings::Load fell through to the compiled defaults - and `ScaleAll`
	// and `ScaleRegion` both default to FALSE. BootState then correctly
	// refuses to draw scaled art inside 1x windows and forces stock. The
	// player installs the mod, launches, and the game is completely unchanged,
	// with nothing to edit and nothing on screen to explain it.
	//
	// The project's own shipped ini has warned about exactly this for months:
	// "DO NOT DELETE ScaleAll OR ScaleRegion. Both are OFF in the DLL's
	// built-in defaults ... remove either one and that half of the mod simply
	// does nothing, with no error and no complaint in the log." Removing the
	// file removed both keys.
	//
	// So the DLL writes the file the metadata already promised. Only when it
	// is ABSENT - an existing ini is never touched, and this never overwrites
	// a player's settings.
	const char* const kStarterIni =
		"; ===========================================================================\r\n"
		";  SC4UIScale.ini  -  SimCity 4 Deluxe UI scaling\r\n"
		"; ===========================================================================\r\n"
		";\r\n"
		";  Written by the mod on its first run because no ini was found. Every\r\n"
		";  value below is already the recommended one - you do not need to edit\r\n"
		";  anything to use the mod.\r\n"
		";\r\n"
		";  DO NOT DELETE ScaleAll OR ScaleRegion. Both are OFF in the DLL's\r\n"
		";  built-in defaults, so they are the only keys here that do NOT fall back\r\n"
		";  to something useful: remove either and that half of the mod does\r\n"
		";  nothing, with no error anywhere. Every other key may be deleted and\r\n"
		";  falls back to exactly the value shown.\r\n"
		";\r\n"
		";  Save as plain UTF-8 or ANSI, WITHOUT a byte-order mark. Some editors\r\n"
		";  add one silently; the game then reads the file as unreadable and falls\r\n"
		";  back to defaults.\r\n"
		"; ===========================================================================\r\n"
		"\r\n"
		"[UiSpike]\r\n"
		"\r\n"
		"; Scale the city-view UI. This is the main switch.\r\n"
		"ScaleAll=1\r\n"
		"\r\n"
		"; Extend the same scaling to the region screen.\r\n"
		"ScaleRegion=1\r\n"
		"\r\n"
		"[Scaling]\r\n"
		"\r\n"
		"; Pick the factor automatically from the resolution the game renders at.\r\n"
		"; 1 = automatic (recommended). Minimum resolutions: 1440x1080 for 1.5x,\r\n"
		"; 1920x1440 for 2x, 2880x2160 for 3x. Below 1440x1080 the mod stays inert\r\n"
		"; and the game is stock.\r\n"
		"AutoScale=1\r\n"
		"\r\n"
		"; The factor used when AutoScale=0. Supported: 1.5, 2.0, 3.0.\r\n"
		"ScaleFactor=2.00\r\n"
		"\r\n"
		"; Keep the in-game UI Scale picker (Graphic Options) working at 1x, so 1x\r\n"
		"; is not a one-way door that needs a hand edit to leave.\r\n"
		"SelectorAtStock=1\r\n"
		"\r\n"
		"; The region screen's website button points at a dead EA address; send it\r\n"
		"; to the Simtropolis community hub instead.\r\n"
		"WebRedirect=1\r\n"
		"\r\n"
		"; Workaround for a stock-game hang when quitting after opening the Budget\r\n"
		"; window. Does nothing unless the hang is detected.\r\n"
		"SpinFix=1\r\n"
		"\r\n"
		"[Logging]\r\n"
		"\r\n"
		"; 0 = errors only, 1 = normal, 2 = verbose, 3 = debug.\r\n"
		"LogLevel=1\r\n";

	bool SeedIniIfAbsentImpl()
	{
		wchar_t ini[MAX_PATH] = {};
		OurIniPath(ini, MAX_PATH);
		if (ini[0] == 0) { return false; }
		if (GetFileAttributesW(ini) != INVALID_FILE_ATTRIBUTES) { return false; }

		// CREATE_NEW, not CREATE_ALWAYS: if anything raced us to the file
		// between the check above and here, theirs wins. Never clobber.
		HANDLE h = CreateFileW(ini, GENERIC_WRITE, 0, nullptr, CREATE_NEW,
			FILE_ATTRIBUTE_NORMAL, nullptr);
		if (h == INVALID_HANDLE_VALUE) { return false; }
		const DWORD len = static_cast<DWORD>(strlen(kStarterIni));
		DWORD wrote = 0;
		// No BOM. Standing order, and the file's own header repeats it: a BOM
		// makes the parser treat the whole file as unreadable.
		const BOOL ok = WriteFile(h, kStarterIni, len, &wrote, nullptr);
		CloseHandle(h);
		if (!ok || wrote != len) { DeleteFileW(ini); return false; }
		return true;
	}


	void LogOurDirsImpl()
	{
		ResolveOurDirs();
		char a[MAX_PATH] = {}, b[MAX_PATH] = {};
		WideCharToMultiByte(CP_UTF8, 0, gOurDirs.early, -1, a, sizeof(a), nullptr, nullptr);
		WideCharToMultiByte(CP_UTF8, 0, gOurDirs.override_, -1, b, sizeof(b), nullptr, nullptr);
		// Every resolver states its resolved value, and says which half it had
		// to guess - a fallback that logged nothing would look exactly like a
		// successful discovery.
		Logger::Get().WriteLine(LogLevel::Info,
			"ScaleTier: our folders resolved BY CONTENT - early=%s (%s), "
			"override=%s (%s).", a,
			gOurDirs.earlyFound ? "discovered" : "FALLBACK to the v4.2.0 name",
			b,
			gOurDirs.overrideFound ? "discovered" : "FALLBACK to the v4.2.0 name");

		// A SECOND CANDIDATE IS THE HALF-MIGRATED INSTALL, and it is silent
		// otherwise: first match wins, and the line above prints only the
		// winner. The realistic shape is a hand install left in place while
		// sc4pac adds its own copy - `010-SC4UIScale` sorts before
		// `050-load-first`, so the ABANDONED folder wins and the managed one
		// is never armed. Two providers of every TGI, one of them stale.
		if (gEarlyCandidates > 1 || gOvrCandidates > 1)
		{
			Logger::Get().WriteLine(LogLevel::Info,
				"ScaleTier: WARNING - %d directories carry our EARLY marker "
				"and %d carry our OVERRIDE marker. Exactly one of each is "
				"correct. The paths above are simply the first found, so a "
				"leftover hand-installed folder can outrank the one your "
				"package manager owns. Delete the copy you are not using.",
				gEarlyCandidates, gOvrCandidates);
		}
	}

	const wchar_t* EarlyDirPtr()
	{
		ResolveOurDirs();
		return gOurDirs.early;
	}

	const wchar_t* OverrideDirPtr()
	{
		ResolveOurDirs();
		return gOurDirs.override_;
	}

	// The TOP-LEVEL folder our override package sits under, relative to the
	// Plugins root - `zzz-SC4UIScale` hand-installed, `900-overrides` under a
	// package manager. Load order is decided by the top-level component, so
	// this, not the leaf, is what a sort-position comparison must use.
	void OverrideTopLevel(wchar_t* out, size_t outLen)
	{
		ResolveOurDirs();
		if (!out || outLen == 0) { return; }
		out[0] = 0;
		wchar_t root[MAX_PATH] = {};
		PluginsRootQuiet(root, MAX_PATH);
		const size_t rootLen = wcslen(root);
		const wchar_t* rel = gOurDirs.override_;
		if (rootLen && _wcsnicmp(rel, root, rootLen) == 0) { rel += rootLen; }
		wcscpy_s(out, outLen, rel);
		if (wchar_t* slash = wcschr(out, L'\\')) { *slash = L'\0'; }
	}

	void OurPackagesDir(wchar_t* out, size_t outLen)
	{
		wcscpy_s(out, outLen, EarlyDirPtr());
	}

	void OurOverrideDir(wchar_t* out, size_t outLen)
	{
		ResolveOurDirs();
		wcscpy_s(out, outLen, gOurDirs.override_);
	}

	// Maps a table entry written with its v4.2.0 folder prefix onto whatever
	// folder that package ACTUALLY lives in now. The table strings stay as
	// stable identifiers - 49 of them - and only this one function knows
	// where the bytes are, so a new layout is one edit rather than 49.
	void ResolveOurRelative(const wchar_t* rel, wchar_t* out, size_t outLen)
	{
		ResolveOurDirs();
		const wchar_t* slash = wcschr(rel, L'\\');
		if (!slash)
		{
			swprintf_s(out, outLen, L"%s%s", gOurDirs.early, rel);
			return;
		}
		const size_t n = static_cast<size_t>(slash - rel);
		const bool isOverride = (n == 14 && _wcsnicmp(rel, L"zzz-SC4UIScale", 14) == 0);
		swprintf_s(out, outLen, L"%s%s",
			isOverride ? gOurDirs.override_ : gOurDirs.early, slash + 1);
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

	// #182 (2026-08-23): a REAL FontStyle.ini is never empty - the format is a
	// list of style lines, so 0 bytes can only be the placeholder we ship in
	// the release zip so sc4pac has a file to track (v4.0.1). An empty file
	// is OURS by construction, exactly like a byte-identical tier source, and
	// must never be treated as the player's real original: measured live,
	// 2026-08-23 - an empty file got snapshotted as .user-original (the gap
	// below did not know "empty" counts as ours), the stock-tier restore then
	// faithfully copied that empty snapshot back over the live file, and the
	// game crashed loading the city-select screen (ACCESS_VIOLATION in
	// sub_7B4150, the tile-paint callback, on a font fetch that found nothing
	// because the live file defined zero styles) - a stock/1x baseline is
	// supposed to be the safest state this mod can produce, not the one that
	// crashes. A file with no bytes cannot be "the user's font" under any
	// interpretation, so this check needs no byte comparison at all.
	bool IsEmptyFile(const wchar_t* path)
	{
		WIN32_FILE_ATTRIBUTE_DATA fad = {};
		if (!GetFileAttributesExW(path, GetFileExInfoStandard, &fad))
		{
			return false;
		}
		return fad.nFileSizeHigh == 0 && fad.nFileSizeLow == 0;
	}

	// #118: is `live` one of OUR shipped tier fonts rather than the player's own?
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
	// One place that writes the repaired tier back, so "the file, the game and
	// the selector agree" is a single statement rather than four copies.
	// Both keys are written: the ini must not keep `inf` / `4` / `2,5` text,
	// because the in-game selector and the next human reader both go through
	// that value.
	void WriteRepairedIni(const wchar_t* iniPath, float tier)
	{
		if (iniPath == nullptr || iniPath[0] == 0) { return; }
		wchar_t val[32] = {};
		swprintf_s(val, L"%.2f", tier);
		WritePrivateProfileStringW(L"UiSpike", L"AutoScale", L"1", iniPath);
		WritePrivateProfileStringW(L"UiSpike", L"ScaleFactor", val, iniPath);
	}

	// Is this tier's art actually on disk? Decide() asks this to refuse a
	// factor the install cannot carry.
	//
	// ⚠ v4.5.0: THIS HAD TO CHANGE WITH THE ARMING SCHEME, and getting it
	// wrong is silent. It used to probe `SelectiveArt<tag>.dat` and its
	// `.x1-disabled` twin - BOTH of which MigrateRenamesToPayloads renames
	// out of existence. Left alone, every tier row would have failed except
	// 2x, whose fallback checks the BARE name - and the bare name is the live
	// stable file, which now always exists. The result would have been every
	// machine silently pinned to 2x, with no error anywhere.
	//
	// So: payloads are the evidence now. The legacy names are still accepted,
	// because this runs on the boot BEFORE migration too, and on that boot
	// they are all that exists.
	bool PackageInstalled(const Package& pkg)
	{
		wchar_t dir[MAX_PATH];
		OurPackagesDir(dir, MAX_PATH);
		wchar_t p[MAX_PATH];

		// The payload for this tier: the post-migration answer.
		const wchar_t* t = (pkg.tag && pkg.tag[0] == L'-') ? pkg.tag + 1 : pkg.tag;
		swprintf_s(p, L"%sz_SC4UIScale_SelectiveArt.%s.uipay", dir, t);
		if (FileExists(p)) { return true; }

		// Pre-migration names.
		swprintf_s(p, L"%sz_SC4UIScale_SelectiveArt%s.dat", dir, pkg.tag);
		if (FileExists(p)) { return true; }
		swprintf_s(p, L"%sz_SC4UIScale_SelectiveArt%s.dat%s", dir, pkg.tag, kDisabledSuffix);
		if (FileExists(p)) { return true; }

		// The historical 2x special case: before tier tags existed, 2x WAS
		// the bare name. It is only evidence when no payload set exists at
		// all - after migration the bare name is the live target of every
		// tier, so treating it as proof of 2x would pin the whole install.
		if (pkg.factor >= 1.99f && pkg.factor <= 2.01f)
		{
			wchar_t any[MAX_PATH];
			swprintf_s(any, L"%sz_SC4UIScale_SelectiveArt.*.uipay", dir);
			WIN32_FIND_DATAW fd = {};
			HANDLE h = FindFirstFileW(any, &fd);
			if (h != INVALID_HANDLE_VALUE) { FindClose(h); return false; }

			swprintf_s(p, L"%sz_SC4UIScale_SelectiveArt.dat", dir);
			if (FileExists(p)) { return true; }
			swprintf_s(p, L"%sz_SC4UIScale_SelectiveArt.dat%s", dir, kDisabledSuffix);
			return FileExists(p);
		}
		return false;
	}

	// ---- THIRD-PARTY DEPENDENCY GATE (v2.38.0, task #79c) -----------------
	// Some of our packages are built from ANOTHER MOD'S data (its .UI script
	// or its art) because that mod replaces a stock resource and, by the
	// load-order law, our root package can never override it. Those packages
	// are only correct while that mod is installed: left active after the player
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
		// WEB BUTTON IMPROVEMENT MOD (cyclone-boom). It ships its own
		// web-button bitmap {856DDBAC,46A006B0,14416302} (320x60); our runtime
		// region scaling enlarges the button's window, so a 1x bitmap stretches
		// soft. Ours are 1.5x/2x/3x upscaled from THE MOD'S bitmap (generator
		// tools\itemicons\rebuild_webbutton.py). The mod's region .UI
		// (0xAA920991) is left to runtime scaling - doubling it would
		// double-scale. PRESENCE ONLY, PREFIX MATCH: the dat name varies by
		// option (A/B/C) and version, and the package is pure art at the mod's
		// own TGI, so a mod update makes ours stale-looking, never
		// mis-geometried - same reasoning as NamIcons.
		{ L"zzz-SC4UIScale\\z_SC4UIScale_WebButtonUI",
		  L"z_Full Screen - Web Button Improvement Mod", true, 0, nullptr, 0 },
		// ---- Scoty Carbon Skin 1.5 (v4.3.0) ----------------------------------
		// Eight carbon-sourced override packages, every one built FROM the
		// skin's own dats, so every row pins EXACT filename + EXACT byte size
		// (the SaveWarningUI reasoning: our copies hard-code Carbon's layout,
		// so a skin update MUST disable us - stale carbon geometry/art would
		// be visibly wrong, while falling back is merely un-carbon'd).
		// Every row ALSO pins scoty_Carbon_Files.dat: it is the skin's core
		// dat, so "present and unchanged" means the WHOLE skin is the version
		// we built from, not just the one file a package was cut from.
		// The Z-late base names (ZCarbon*) are LOAD-BEARING: they must sort
		// after every existing zzz package so they win shared TGIs when armed
		// (see _tests\REGRESSION.md 2026-08-25 "zzz-INTERNAL SORT TRAP").
		//
		// Scaled copies of Carbon's .UI scripts - hard-code its rects.
		{ L"zzz-SC4UIScale\\z_SC4UIScale_ZCarbonUI",
		  L"scoty_carbon_PNG.dat", false, 3460148,
		  L"scoty_Carbon_Files.dat", 268639 },
		// Upscaled copies of Carbon's panel/background art at its own TGIs.
		{ L"zzz-SC4UIScale\\z_SC4UIScale_ZCarbonArt",
		  L"scoty_carbon_PNG.dat", false, 3460148,
		  L"scoty_Carbon_Files.dat", 268639 },
		// Upscaled copies of Carbon's icon strips at its own TGIs.
		{ L"zzz-SC4UIScale\\z_SC4UIScale_ZCarbonIcons",
		  L"scoty_carbon_PNG.dat", false, 3460148,
		  L"scoty_Carbon_Files.dat", 268639 },
		// Carbon's variant of the save-warning confirm dialogs (option A dat).
		{ L"zzz-SC4UIScale\\z_SC4UIScale_ZCarbonSaveWarning",
		  L"w_scoty_Carbon_CB_SaveWarning_optA.dat", false, 3853,
		  L"scoty_Carbon_Files.dat", 268639 },
		// Carbon's CAM-extended panels - its rects, not CAM's own.
		{ L"zzz-SC4UIScale\\z_SC4UIScale_ZCarbonCamUI",
		  L"y_scoty_CAM_Extended_Essentials.dat", false, 28646,
		  L"scoty_Carbon_Files.dat", 268639 },
		// Carbon's building-styles panel skin.
		{ L"zzz-SC4UIScale\\z_SC4UIScale_ZCarbonStyles",
		  L"z_scoty_Carbon_BuildingStyles.dat", false, 10270,
		  L"scoty_Carbon_Files.dat", 268639 },
		// Carbon's NAM-facing skin pieces.
		{ L"zzz-SC4UIScale\\z_SC4UIScale_ZCarbonNam",
		  L"y_scoty_Carbon_NAM.dat", false, 166501,
		  L"scoty_Carbon_Files.dat", 268639 },
		// Carbon's restyle of warrior's God-Terraforming mod: the GodMod dat
		// redeclares EXACTLY WarriorUI's four TGIs (scripts 09923283/CB95403E
		// + art EB7C4D3B/14215E27), so this package must out-sort WarriorUI
		// (Z-late) and be built from the GodMod dat's own payloads. Armed on
		// that dat alone: it constitutes the compact layouts by itself, so it
		// is correct even if warrior's original is removed.
		{ L"zzz-SC4UIScale\\z_SC4UIScale_ZCarbonGodMod",
		  L"z_scoty_Carbon_GodMod.dat", false, 21005,
		  L"scoty_Carbon_Files.dat", 268639 },
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
	// outMatches (optional, 2026-08-25): when non-null the walk does NOT stop
	// at the first hit - it counts EVERY copy of the name in the tree. A
	// second copy is a real defect class: the gate size-checks the copy it
	// found first (enumeration order), while the GAME loads both and renders
	// the later-sorting one, so a stale duplicate can satisfy a fingerprint
	// for art the player never sees. The out params still describe the FIRST
	// match (unchanged decisions); the count only makes the shadow loud.
	bool FindPluginFile(
		const wchar_t* dir,
		const wchar_t* name,
		bool prefixMatch,
		int depth,
		wchar_t* outPath,
		size_t outLen,
		DWORD* outSize,
		int* outMatches = nullptr)
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
				// A dependency must never be satisfied by our OWN packages.
				// v4.5.0: matched against the DISCOVERED folder names, so this
				// still holds when a package manager picked those names.
				ResolveOurDirs();
				if (_wcsicmp(fd.cFileName, gOurDirs.overrideLeaf) == 0
					|| _wcsicmp(fd.cFileName, gOurDirs.earlyLeaf) == 0
					|| _wcsicmp(fd.cFileName, L"_dllstash") == 0)
				{
					continue;
				}
				wchar_t sub[MAX_PATH];
				swprintf_s(sub, L"%s%s\\", dir, fd.cFileName);
				wchar_t scratchPath[MAX_PATH] = {};
				DWORD scratchSize = 0;
				int subMatches = 0;
				const bool hit = FindPluginFile(sub, name, prefixMatch,
					depth - 1,
					found ? scratchPath : outPath,
					found ? MAX_PATH : outLen,
					found ? &scratchSize : outSize,
					outMatches ? &subMatches : nullptr);
				if (outMatches)
				{
					*outMatches += subMatches;
				}
				if (hit)
				{
					found = true;
				}
			}
			else
			{
				const size_t n = wcslen(name);
				const bool hit = prefixMatch
					? (_wcsnicmp(fd.cFileName, name, n) == 0)
					: (_wcsicmp(fd.cFileName, name) == 0);
				if (hit)
				{
					if (outMatches)
					{
						(*outMatches)++;
					}
					if (!found)
					{
						swprintf_s(outPath, outLen, L"%s%s", dir, fd.cFileName);
						*outSize = fd.nFileSizeLow;
					}
					found = true;
				}
			}
		} while ((outMatches != nullptr || !found) && FindNextFileW(h, &fd));
		FindClose(h);
		return found;
	}

	// Defined with the ArmOne block below; declared here because the
	// record-then-commit pair sits above it in the file.
	bool ArmOne(const wchar_t* dir, const wchar_t* base, const wchar_t* tag,
		const char* reason);
	void LoadArmState(const wchar_t* dir);
	void WriteArmState(const wchar_t* dir);
	int  MigrateRenamesToPayloads(const wchar_t* dir);

	// ============ v4.5.0: SyncDat NO LONGER RENAMES - IT RECORDS ==========
	// Every call site and every gate expression is unchanged. What changed is
	// what a call MEANS: it used to perform a rename, it now records "this
	// package wants this tag", and CommitArming() below does the one thing
	// that actually touches disk.
	//
	// WHY RECORD-THEN-COMMIT RATHER THAN ARM IN PLACE. The tier loop calls
	// this FOUR times per package - once per tier - and exactly one of those
	// calls has active=true. A gated-off package gets active=false on all
	// four. Arming in place cannot tell those two cases apart: "not this
	// tier" and "not at all" both look like a single false. Under the rename
	// scheme that was fine, because false meant "push this file aside" and
	// three pushes plus one pull landed correctly. Under a STABLE filename
	// there is nothing to push aside - the name is constant - so the
	// distinction has to survive to the end of the loop. Recording preserves
	// it: a base that never receives an active call is the gated-off case and
	// commits `.off`.
	//
	// This is also why there is exactly ONE mechanism now. The previous
	// attempt (load-time exclusion) ran a SECOND rule set beside this one and
	// the two drifted within a day - `-1x` was absent from kPackages, so
	// SelectorUI was classified "tier-independent, always stays" and sat live
	// at 3x in the winning folder. Two mechanisms for one decision is the
	// defect; see research/laws/feedback-arming-must-be-additive-and-pre-scan.md
	struct WantRow
	{
		wchar_t dir[MAX_PATH];
		wchar_t base[96];
		wchar_t tag[16];
		bool    wanted;
	};
	WantRow gWant[64] = {};
	int     gWantCount = 0;

	// "-15x" -> "15x", "-1x" -> "1x", "" -> "on". The payload suffix never
	// carries the hyphen, because it is not a tier TAG there - it is a file
	// extension component.
	void PayloadTagOf(const wchar_t* tag, wchar_t* out, size_t outLen)
	{
		if (!tag || !*tag) { wcscpy_s(out, outLen, L"on"); return; }
		wcscpy_s(out, outLen, tag[0] == L'-' ? tag + 1 : tag);
	}

	void SyncDat(const wchar_t* dir, const wchar_t* base, const wchar_t* tag, bool active)
	{
		// `base` may still carry its v4.2.0 folder prefix; WHERE a package
		// lives is discovered, so resolve the prefix rather than
		// concatenating `dir` onto it.
		wchar_t stem[MAX_PATH];
		if (wcschr(base, L'\\'))
		{
			ResolveOurRelative(base, stem, MAX_PATH);
		}
		else
		{
			swprintf_s(stem, L"%s%s", dir, base);
		}
		// split the resolved stem back into folder + leaf
		wchar_t folder[MAX_PATH];
		wcscpy_s(folder, MAX_PATH, stem);
		wchar_t* slash = wcsrchr(folder, L'\\');
		const wchar_t* leaf = stem;
		if (slash)
		{
			leaf = stem + (slash - folder) + 1;
			*(slash + 1) = 0;
		}

		WantRow* row = nullptr;
		for (int i = 0; i < gWantCount; i++)
		{
			if (_wcsicmp(gWant[i].base, leaf) == 0
				&& _wcsicmp(gWant[i].dir, folder) == 0)
			{
				row = &gWant[i];
				break;
			}
		}
		if (!row)
		{
			if (gWantCount >= 64)
			{
				Logger::Get().WriteLine(LogLevel::Info,
					"SyncDat: package table full at %d - %ls NOT ARMED. This "
					"is a build defect, not a user state.", gWantCount, leaf);
				return;
			}
			row = &gWant[gWantCount++];
			wcscpy_s(row->dir, MAX_PATH, folder);
			wcscpy_s(row->base, 96, leaf);
			wcscpy_s(row->tag, 16, L"off");
			row->wanted = false;
		}
		if (active)
		{
			PayloadTagOf(tag, row->tag, 16);
			row->wanted = true;
		}
	}

	// The single pass that touches disk. Runs once, after every SyncDat call
	// for this boot has been made.
	void CommitArming()
	{
		if (gWantCount == 0) { return; }

		// Distinct folders, so migration and the state file run once each.
		wchar_t dirs[4][MAX_PATH] = {};
		int nDirs = 0;
		for (int i = 0; i < gWantCount; i++)
		{
			bool seen = false;
			for (int d = 0; d < nDirs; d++)
			{
				if (_wcsicmp(dirs[d], gWant[i].dir) == 0) { seen = true; break; }
			}
			if (!seen && nDirs < 4) { wcscpy_s(dirs[nDirs++], MAX_PATH, gWant[i].dir); }
		}

		int migrated = 0;
		for (int d = 0; d < nDirs; d++)
		{
			migrated += MigrateRenamesToPayloads(dirs[d]);
			LoadArmState(dirs[d]);
		}

		int armed = 0, off = 0, failed = 0;
		for (int i = 0; i < gWantCount; i++)
		{
			WantRow& w = gWant[i];
			const bool ok = ArmOne(w.dir, w.base,
				w.wanted ? w.tag : L"off",
				w.wanted ? "armed" : "gated off or no tier match");
			if (!ok) { failed++; }
			else if (w.wanted) { armed++; }
			else { off++; }
		}

		for (int d = 0; d < nDirs; d++) { WriteArmState(dirs[d]); }

		Logger::Get().WriteLine(LogLevel::Info,
			"CommitArming: %d package(s) across %d folder(s) - %d armed, %d "
			"inert, %d FAILED%s. A failure count above zero means a package "
			"is holding bytes we did not choose; read the ArmOne lines above.",
			gWantCount, nDirs, armed, off, failed,
			migrated ? " (after a one-time migration from the rename layout)"
			         : "");
	}

	// ============ STABLE-FILENAME PACKAGES (v4.0.3, PILOT: SelectiveArt) ===
	// sc4pac maintainer, confirmed by the user: the package manager tracks
	// files it installed BY EXACT NAME and can only remove those exact
	// names. SyncDat's rename dance (whichever tier is active loses its
	// suffix; the other two keep `.x1-disabled`) means the file sc4pac
	// remembers installing may not be the file that exists on disk the
	// moment the player uninstalls - and AutoScale performs this rename on
	// the FIRST LAUNCH, picking whatever tier the player's own screen
	// needs, so this is not a rare manual-tier-switch edge case. It is the
	// same shape of bug FontStyle.ini already had, at 11x the surface area
	// (every tier-managed package).
	//
	// THE FIX, same principle as the FontStyle.ini placeholder: give
	// sc4pac ONE filename that NEVER changes - `<base>.dat`, no tier tag -
	// and move content into it instead of renaming files around it. The
	// three tier SOURCES become PERMANENTLY suffixed (`<base><tag>.dat
	// .x1-disabled`, always, never promoted to a bare .dat name); only
	// their BYTES get copied onto the one stable name SC4 actually loads.
	//
	// SCOPE, DELIBERATE: this is the PILOT, SelectiveArt only. STOCK (1x)
	// still disables the stable file by the same rename-to-.x1-disabled
	// trick as before - a genuinely inert placeholder DBPF would close
	// that gap too, but nothing in this codebase builds one yet, and
	// inventing that format tonight is out of scope for a pilot. Stock is
	// also the tier this bug bites LEAST: AutoScale almost never lands
	// there (it needs a screen too small for even 1.5x), so the common
	// case - someone uninstalling while the mod is actively scaling their
	// UI - is fully covered.
	//
	// MIGRATION IS BUILT IN, NOT A SEPARATE STEP. Every v4.0.0-4.0.2
	// install has the OLD layout: one of the three tier files sits bare
	// (whichever tier was last active), matching the pattern this function
	// would otherwise mistake for "no stable file has ever been written."
	// So the very first thing this does is look for that bare legacy file,
	// and if found, re-suffix it (source-only invariant restored) before
	// anything else runs. Idempotent: once migrated, this check costs one
	// FileExists per tag per call.
	// ============ v4.5.0 ArmOne - CONTENT SWAP AT A STABLE FILENAME =======
	// Replaces SyncDat's rename dance, which is the single reason a package
	// manager cannot uninstall this mod: sc4pac removes files BY MANIFEST
	// NAME, and 53 of 68 installed files sat under a renamed name.
	//
	// THE SHAPE. Per package, two file classes:
	//   LIVE     z_SC4UIScale_<Pkg>.dat           the only thing SC4 loads.
	//                                             Its CONTENT changes; the
	//                                             name never does, at any
	//                                             tier, under any gate
	//                                             verdict, ever.
	//   PAYLOAD  z_SC4UIScale_<Pkg>.<tag>.uipay   inert. Never renamed, never
	//                                             live, never written by us.
	//
	// WHY .uipay IS SAFE, measured rather than assumed: probe #202 copied a
	// real DBPF to `.uipay`, booted, and it did NOT appear in the registered
	// segment census while 13 of our live .dat files did. The scan is
	// EXTENSION-gated. `.dat.x1-disabled` being skipped only ever proved that
	// ONE string is skipped; this proves it for the string we now rely on.
	//
	// WHY IT SATISFIES THE LAW. "Arming must be additive and pre-scan" - a
	// file that must not be armed must never ENTER the plugin scan, because
	// entering IS the damage: the win is latched into the merged index before
	// any code of ours runs. A gated-off package here is a live file holding
	// `.off` content, which declares no contested TGI, so the runner-up is
	// promoted by the engine's own scan-order logic at index-build time. That
	// is what the rename bought by keeping the file off disk, and what
	// closing a segment afterwards could never produce.
	//
	// Runs in the director constructor, DURING the plugin scan - the same
	// moment the rename ran, which is why both work and why a PostAppInit
	// pass could not.

	// The stamp that makes the steady state free. Deliberately NOT
	// FilesIdentical(): that short-circuits only on a SIZE mismatch and then
	// reads both files to EOF in 8 KB chunks. In steady state the sizes match
	// by construction, so it would read everything, every boot - ~88 MB at
	// 3x, over OneDrive cloud placeholders.
	//
	// The LIVE file's stats are in the stamp as well as the payload's, and
	// that is what makes this self-healing: an installer - or an sc4pac
	// package UPDATE, which wipes the versioned folder wholesale - that
	// restores a shipped file changes its mtime, the stamp misses, and the
	// next boot re-copies. A payload-only fingerprint would call that steady.
	struct ArmStamp
	{
		uint64_t paySize, payTime, liveSize, liveTime;
	};

	bool StatFile(const wchar_t* p, uint64_t* size, uint64_t* mtime)
	{
		WIN32_FILE_ATTRIBUTE_DATA a = {};
		if (!GetFileAttributesExW(p, GetFileExInfoStandard, &a)) { return false; }
		*size = (static_cast<uint64_t>(a.nFileSizeHigh) << 32) | a.nFileSizeLow;
		*mtime = (static_cast<uint64_t>(a.ftLastWriteTime.dwHighDateTime) << 32)
			| a.ftLastWriteTime.dwLowDateTime;
		return true;
	}

	// One row per package, persisted per folder. Doubles as the diagnostic a
	// constant filename would otherwise destroy: with every name fixed, a
	// directory listing no longer tells you the armed tier or a gate verdict.
	struct ArmRow
	{
		wchar_t  base[96];
		wchar_t  tag[16];
		// 160, not 64: this column is what REPLACES the diagnosis a constant
		// filename destroys, and the real verdicts ("dep ABSENT (x.dat)",
		// "dep CHANGED", "PARTIAL") do not fit in 64.
		char     reason[160];
		ArmStamp stamp;
	};
	ArmRow gArmRows[64] = {};
	int    gArmRowCount = 0;

	const wchar_t kStateFile[] = L"z_SC4UIScale_STATE.txt";

	void LoadArmState(const wchar_t* dir)
	{
		wchar_t p[MAX_PATH];
		swprintf_s(p, L"%s%s", dir, kStateFile);
		FILE* f = nullptr;
		if (_wfopen_s(&f, p, L"r") != 0 || !f) { return; }
		char line[512];
		while (fgets(line, sizeof(line), f))
		{
			char b[96] = {}, t[16] = {}, r[160] = {};
			ArmStamp s = {};
			const int got = sscanf_s(line,
				"%95[^\t]\t%15[^\t]\t%159[^\t]\t%llu\t%llu\t%llu\t%llu",
				b, static_cast<unsigned>(sizeof(b)),
				t, static_cast<unsigned>(sizeof(t)),
				r, static_cast<unsigned>(sizeof(r)),
				&s.paySize, &s.payTime, &s.liveSize, &s.liveTime);
			if (got == 7 && gArmRowCount < 64)
			{
				ArmRow& row = gArmRows[gArmRowCount++];
				MultiByteToWideChar(CP_UTF8, 0, b, -1, row.base, 96);
				MultiByteToWideChar(CP_UTF8, 0, t, -1, row.tag, 16);
				strcpy_s(row.reason, r);
				row.stamp = s;
			}
		}
		fclose(f);
	}

	ArmRow* FindArmRow(const wchar_t* base)
	{
		for (int i = 0; i < gArmRowCount; i++)
		{
			if (_wcsicmp(gArmRows[i].base, base) == 0) { return &gArmRows[i]; }
		}
		return nullptr;
	}

	// THE PRIMITIVE. tag is "15x" / "2x" / "3x" / "1x" / "on" / "off".
	// True when the live file ends the call holding that payload's bytes.
	bool ArmOne(const wchar_t* dir, const wchar_t* base, const wchar_t* tag,
		const char* reason)
	{
		wchar_t live[MAX_PATH], src[MAX_PATH];
		swprintf_s(live, L"%s%s.dat", dir, base);
		swprintf_s(src, L"%s%s.%s.uipay", dir, base, tag);

		const wchar_t* usedTag = tag;
		if (!FileExists(src))
		{
			// A missing payload is a SHIP DEFECT, not a state to absorb
			// quietly. Fall back to `.off` - inert is the only safe wrong
			// answer - and name the file out loud.
			Logger::Get().WriteLine(LogLevel::Info,
				"ArmOne: MISSING PAYLOAD %ls.%ls.uipay - falling back to "
				".off. This is a packaging defect; the package will be inert.",
				base, tag);
			swprintf_s(src, L"%s%s.off.uipay", dir, base);
			usedTag = L"off";
			if (!FileExists(src))
			{
				Logger::Get().WriteLine(LogLevel::Info,
					"ArmOne: NO PAYLOAD AT ALL for %ls (not even .off). "
					"Leaving %ls.dat exactly as found - never destroy a live "
					"file we cannot replace.", base, base);
				return false;
			}
		}

		ArmStamp now = {};
		if (!StatFile(src, &now.paySize, &now.payTime)) { return false; }
		const bool haveLive = StatFile(live, &now.liveSize, &now.liveTime);

		ArmRow* row = FindArmRow(base);
		if (haveLive && row && _wcsicmp(row->tag, usedTag) == 0
			&& row->stamp.paySize == now.paySize
			&& row->stamp.payTime == now.payTime
			&& row->stamp.liveSize == now.liveSize
			&& row->stamp.liveTime == now.liveTime)
		{
			return true;   // steady state: four stats, zero I/O
		}

		// ATOMIC, AND FAIL-INERT. A bare CopyFileW is neither: it fails
		// MIXED, leaving the previous tier's bytes under this tier's
		// geometry - precisely the screen this redesign exists to eliminate.
		// The rename it replaces failed inert; so must this.
		wchar_t tmp[MAX_PATH];
		swprintf_s(tmp, L"%s%s.dat.tmp", dir, base);
		if (!CopyFileW(src, tmp, FALSE))
		{
			Logger::Get().WriteLine(LogLevel::Info,
				"ArmOne: could not stage %ls.%ls.uipay (err %u) - %ls.dat "
				"left untouched.", base, usedTag, GetLastError(), base);
			return false;
		}
		if (!MoveFileExW(tmp, live, MOVEFILE_REPLACE_EXISTING))
		{
			const DWORD e = GetLastError();
			DeleteFileW(tmp);
			Logger::Get().WriteLine(LogLevel::Info,
				"ArmOne: could not commit %ls.dat (err %u) - staged copy "
				"discarded, previous content intact.", base, e);
			return false;
		}
		StatFile(live, &now.liveSize, &now.liveTime);

		if (!row)
		{
			if (gArmRowCount >= 64) { return true; }
			row = &gArmRows[gArmRowCount++];
			wcscpy_s(row->base, 96, base);
		}
		wcscpy_s(row->tag, 16, usedTag);
		strcpy_s(row->reason, reason ? reason : "");
		row->stamp = now;

		Logger::Get().WriteLine(LogLevel::Info,
			"ArmOne: %ls.dat <- .%ls.uipay (%s)", base, usedTag,
			reason ? reason : "");
		return true;
	}

	void WriteArmState(const wchar_t* dir)
	{
		// Restores the signal a constant filename destroys. NOT a marker
		// file - nothing gates on it. It exists so a directory listing, and
		// the test harness, can still answer "which tier is armed, and why is
		// this one off".
		wchar_t p[MAX_PATH];
		swprintf_s(p, L"%s%s", dir, kStateFile);
		FILE* f = nullptr;
		if (_wfopen_s(&f, p, L"w") != 0 || !f) { return; }
		fputs("# SC4UIScale arming state. Rewritten every boot; the game never"
			" reads it.\n# base\ttag\treason\tpaySize\tpayTime\tliveSize"
			"\tliveTime\n", f);
		for (int i = 0; i < gArmRowCount; i++)
		{
			const ArmRow& r = gArmRows[i];
			char b[128] = {}, t[32] = {};
			WideCharToMultiByte(CP_UTF8, 0, r.base, -1, b, sizeof(b),
				nullptr, nullptr);
			WideCharToMultiByte(CP_UTF8, 0, r.tag, -1, t, sizeof(t),
				nullptr, nullptr);
			fprintf(f, "%s\t%s\t%s\t%llu\t%llu\t%llu\t%llu\n", b, t, r.reason,
				r.stamp.paySize, r.stamp.payTime,
				r.stamp.liveSize, r.stamp.liveTime);
		}
		fclose(f);
	}

	// ONE-TIME UPGRADE FROM THE RENAME LAYOUT. A v4.4.0 install has
	// <base>-<tag>.dat and <base>-<tag>.dat.x1-disabled and no payloads. Turn
	// those into payloads in place, so an upgrading user needs no download.
	//
	// The tag set is DERIVED from kPackages plus -1x, never a hand-written
	// literal: a sweep written against {15x,2x,3x} would miss
	// z_SC4UIScale_SelectorUI-1x, the one package armed by the ABSENCE of a
	// tier and the only thing keeping 1x from being a one-way door.
	int MigrateRenamesToPayloads(const wchar_t* dir)
	{
		wchar_t pat[MAX_PATH];
		swprintf_s(pat, L"%sz_SC4UIScale_*", dir);
		WIN32_FIND_DATAW fd = {};
		HANDLE h = FindFirstFileW(pat, &fd);
		if (h == INVALID_HANDLE_VALUE) { return 0; }

		int moved = 0;
		do
		{
			if (fd.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) { continue; }
			wchar_t name[MAX_PATH];
			wcscpy_s(name, MAX_PATH, fd.cFileName);

			const size_t dl = wcslen(kDisabledSuffix);
			size_t nl = wcslen(name);
			if (nl > dl && _wcsicmp(name + nl - dl, kDisabledSuffix) == 0)
			{
				name[nl - dl] = 0;
				nl -= dl;
			}
			if (nl < 5 || _wcsicmp(name + nl - 4, L".dat") != 0) { continue; }
			name[nl - 4] = 0;

			const wchar_t* hit = nullptr;
			for (int i = 0; i < kPackageCount && !hit; i++)
			{
				const size_t tl = wcslen(kPackages[i].tag);
				const size_t bl = wcslen(name);
				if (bl > tl && _wcsicmp(name + bl - tl, kPackages[i].tag) == 0)
				{
					hit = kPackages[i].tag;
				}
			}
			if (!hit)
			{
				const size_t bl = wcslen(name);
				if (bl > 3 && _wcsicmp(name + bl - 3, L"-1x") == 0)
				{
					hit = L"-1x";
				}
			}
			if (!hit) { continue; }   // untagged: already a stable name

			wchar_t base[MAX_PATH];
			wcscpy_s(base, MAX_PATH, name);
			base[wcslen(base) - wcslen(hit)] = 0;

			wchar_t dst[MAX_PATH], from[MAX_PATH];
			swprintf_s(dst, L"%s%s.%s.uipay", dir, base, hit + 1);
			swprintf_s(from, L"%s%s", dir, fd.cFileName);
			// Was this the ARMED copy? An .x1-disabled suffix means no.
			// It matters: moving the armed file into a payload leaves the
			// package with NOTHING live until ArmOne runs, and if ArmOne
			// then fails on I/O the player boots with that package simply
			// missing. So the armed one is seeded straight across to the
			// stable name here, closing the window entirely rather than
			// relying on the next call succeeding.
			const bool wasArmed =
				_wcsicmp(fd.cFileName + wcslen(fd.cFileName) - wcslen(kDisabledSuffix),
					kDisabledSuffix) != 0;
			if (FileExists(dst)) { DeleteFileW(from); moved++; }
			else if (MoveFileExW(from, dst, 0)) { moved++; }
			else { continue; }
			if (wasArmed)
			{
				wchar_t stable[MAX_PATH];
				swprintf_s(stable, L"%s%s.dat", dir, base);
				if (!FileExists(stable)) { CopyFileW(dst, stable, TRUE); }
			}
		} while (FindNextFileW(h, &fd));
		FindClose(h);

		if (moved)
		{
			Logger::Get().WriteLine(LogLevel::Info,
				"ArmOne: migrated %d pre-4.5.0 tier file(s) in this folder "
				"into .uipay payloads - no download needed.", moved);
		}
		return moved;
	}

	// One-time migration of a legacy (pre-multi-package) install: the
	// original 2x package shipped UNTAGGED file names. Rename its dats to
	// their -2x names (live or gated form) and derive the FontStyle-2x.ini
	// package source from the legacy font file. Idempotent no-op afterward.
	void MigrateLegacyUntagged2x(const wchar_t* dir)
	{
		// SelectiveArt REMOVED (v4.0.3): an untagged z_SC4UIScale_SelectiveArt
		// .dat[.x1-disabled] is no longer a legacy artifact to migrate AWAY
		// from - it is SyncDatStable's normal, current, content-swapped
		// state (see its comment above). This function running on it would
		// rename the stable file to -2x.dat every single boot, fighting
		// SyncDatStable's own migration forever (each undoes the other's
		// idempotence check). SyncDatStable owns SelectiveArt's migration
		// now, including the ACTUALLY relevant case (a bare v4.0.0-4.0.2
		// active-tier file), which this ancient pre-multi-package check
		// never covered anyway.
		const wchar_t* bases[] = {
			L"z_SC4UIScale_DialogStatic",
		};
		for (int i = 0; i < 1; i++)
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
		//     scaled launch overwrote the player's file with NO backup at all;
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
		// "restore" a 2x font over the player's file - the very data loss this
		// block was added to prevent, with the evidence destroyed.
		//
		// The distinguishing test is exact and cheap: we SHIP the tier font
		// sources, so a live file that is byte-identical to any of them is
		// ours by construction. Only a file that matches NONE of them can be
		// the player's. (Byte compare, not size: the three tier fonts are all
		// 23,016 bytes, so size alone cannot even tell them apart.)
		wchar_t userOrig[MAX_PATH];
		swprintf_s(userOrig, L"%sFontStyle.ini.user-original", liveDir);
		if (FileExists(live) && !FileExists(userOrig))
		{
			const wchar_t* ourTag = MatchesAnyTierFontSource(live, srcDir);
			if (ourTag != nullptr || IsEmptyFile(live))
			{
				// Ours, not theirs (#182: empty is ours by construction - see
				// IsEmptyFile). Taking no snapshot is the SAFE outcome: with
				// no .user-original the stock tier moves our file aside
				// instead of restoring a wrong one, which leaves the player
				// exactly where they were.
				Logger::Get().WriteLine(
					LogLevel::Info,
					"ScaleTier: %ls is OUR %ls (not the user's) - no "
					".user-original taken. This is an upgrade install; "
					"snapshotting here would have made our own font "
					"masquerade as the user's original (#118/#182).",
					live, ourTag != nullptr
						? L"shipped tier font (byte-identical)"
						: L"empty sc4pac-tracking placeholder");
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
			// #182 SELF-HEAL: a .user-original from before this fix may
			// already BE the corrupted empty snapshot (see IsEmptyFile's
			// comment - this is exactly the file that crashed the game
			// loading the city-select screen). Discard it here rather than
			// trust it: a real user font is never 0 bytes, so this can only
			// ever throw away a bad snapshot, never a genuine one. Every
			// affected install repairs itself on its next stock-tier boot
			// with this fix, with no manual file surgery required.
			if (FileExists(userOrig) && IsEmptyFile(userOrig))
			{
				DeleteFileW(userOrig);
				Logger::Get().WriteLine(
					LogLevel::Info,
					"ScaleTier: discarded an empty .user-original for %ls - "
					"it could only be our own corrupted #182 snapshot, never "
					"the player's real font, and restoring it crashes the "
					"game loading the city-select screen. Falling through to "
					"remove the live file instead, so the game's own built-in "
					"font table applies.", live);
			}
			// STOCK TIER = the game as the player had it. Restore their original
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
				// A STALE STASH MADE THE STOCK TIER KEEP ITS SCALED FONT.
				// MoveFileExW with no flags REFUSES when the destination
				// exists (err 183), and the destination survives every
				// previous visit to stock - so the SECOND time a player
				// selected 1x the rename failed, the 2x FontStyle.ini stayed
				// live, and the whole UI came up stock-sized with scaled text.
				// User-reported 2026-08-19 ("when I select 1x the font scaling
				// is not changing"), and the log had been saying it in plain
				// words the entire time: "kept - an earlier ... already exists
				// (err 183)". A failure that logs itself is still a failure.
				//
				// The stale file is OUR OWN previously-stashed font - the
				// user's original, if there ever was one, lives under
				// .user-original and is restored above, before this line is
				// reached. So it is safe to drop and re-stash the current one,
				// which also keeps exactly ONE stashed copy instead of
				// silently preferring the oldest.
				// PROVEN OURS, NOT ASSUMED OURS. The stale stash is deleted
				// only when it is byte-identical to one of the tier font
				// sources we ship - the same distinguishing test #118 uses
				// twenty lines above. If it is anything else it is left
				// exactly where it is and the rename fails as before: a
				// scaled font staying live is a cosmetic defect, and deleting
				// a font we cannot prove is ours is not.
				if (FileExists(aside))
				{
					const wchar_t* asideTag =
						MatchesAnyTierFontSource(aside, srcDir);
					if (asideTag != nullptr || IsEmptyFile(aside))
					{
						// #182: an empty aside is ours by construction (same
						// reasoning as IsEmptyFile's own comment) - without
						// this, a stale empty stash would fail the SAME test
						// asideTag uses, get left in place, and the
						// MoveFileExW below would then fail (err 183) and
						// strand the live (possibly also empty) file exactly
						// where the game reads it.
						DeleteFileW(aside);
						Logger::Get().WriteLine(LogLevel::Info,
							"ScaleTier: dropped a stale %ls stash so the live "
							"font can be put aside - it was %ls, and leaving "
							"it there is what kept a scaled (or empty, #182) "
							"font live at the stock tier.",
							kDisabledSuffix, asideTag != nullptr
								? L"byte-identical to our own tier source"
								: L"an empty sc4pac-tracking placeholder");
					}
					else
					{
						Logger::Get().WriteLine(LogLevel::Info,
							"ScaleTier: an existing %ls stash is NOT one of "
							"our fonts - leaving it untouched. The live font "
							"stays and the stock tier keeps scaled text; that "
							"is the safe direction.", aside);
					}
				}
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
// WHY THIS EXISTS. Stock control 2026-08-14, confirmed on screen on screen:
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
// NO BLIT-LAYER FIX EXISTS - measured, do not re-attempt. The engine needs
// CELL SIZE AND ART SIZE TO AGREE; the cell is per-STRIP while coverage is
// per-TGI, and a real strip mixes both. Every rect patch was rejected on
// screen: re-cut source -> flickers; + centre -> flickers; + tile the whole
// cell so every pixel is rewritten every frame -> STILL flickers. Baseline is
// stable, ANY modification flickers.
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
	// 0x7F0388).
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

	// MAX_PATH IS NOT ENOUGH HERE - #139, TRAP 1, PAID FOR IN TEN MISSED
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
					"IconSynth: path too long even for %d wchars under %ls - "
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
			// THESE OFFSETS WERE WRONG IN THE FIRST BUILD AND THE SCAN WENT
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
	// ORDER IS NOT GUARANTEED by the directory walk, so coverage cannot be
	// decided on the fly - collect ours FIRST, then diff. Deciding per-file as
	// they arrive would mark an icon uncovered simply because our package had
	// not been walked yet.
	// ---- GROWABLE ARRAYS - WIDEN, NEVER SILENTLY TRUNCATE -----------------
	// This scan and its fix list used to be fixed at 4096 and 512 entries.
	// MEASURED against a real install (45,945 plugin files under a
	// sc4pac-managed "150-mods" tree): 6,619 third-party icon TGIs were
	// dropped from the scan outright, and of the ones that WERE counted,
	// only the first 512 could ever be corrected - no matter how many were
	// found, thousands stayed uncorrected. There is no natural ceiling on
	// "how many icons a player's plugin folder contains", so these grow
	// instead of capping. Standing law: a patch that cannot express its
	// value must REFUSE or WIDEN, never silently truncate.
	struct U32List
	{
		uint32_t* data;
		int n;
		int cap;
	};

	void U32Push(U32List& list, uint32_t v)
	{
		if (list.n >= list.cap)
		{
			const int newCap = (list.cap > 0) ? list.cap * 2 : 1024;
			uint32_t* grown = static_cast<uint32_t*>(realloc(
				list.data, static_cast<size_t>(newCap) * sizeof(uint32_t)));
			if (!grown) { return; }   // OOM: this one entry is dropped, not the feature
			list.data = grown;
			list.cap = newCap;
		}
		list.data[list.n++] = v;
	}

	void U32Free(U32List& list)
	{
		free(list.data);
		list.data = nullptr;
		list.n = 0;
		list.cap = 0;
	}

	struct PtrList
	{
		cIGZUnknown** data;
		int n;
		int cap;
	};

	void PtrPush(PtrList& list, cIGZUnknown* v)
	{
		if (list.n >= list.cap)
		{
			const int newCap = (list.cap > 0) ? list.cap * 2 : 1024;
			cIGZUnknown** grown = static_cast<cIGZUnknown**>(realloc(
				list.data, static_cast<size_t>(newCap) * sizeof(cIGZUnknown*)));
			if (!grown) { return; }
			list.data = grown;
			list.cap = newCap;
		}
		list.data[list.n++] = v;
	}

	struct ScanState
	{
		U32List ours;
		U32List theirs;
		bool    collectingOurs;
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
	U32List  gFixList = {};
	uint32_t gControlInst = 0;   // one of OURS, known-enlarged on disk

	void AddTgi(uint32_t inst, void* /*ctx*/)
	{
		if (!gScan) { return; }
		U32List& list = gScan->collectingOurs ? gScan->ours : gScan->theirs;
		for (int i = 0; i < list.n; i++) { if (list.data[i] == inst) { return; } }
		U32Push(list, inst);
	}

	void OnFile(const wchar_t* full, const wchar_t* name, void* /*ctx*/)
	{
		if (!gScan || !IsDbpfName(name)) { return; }
		if (IsOurPackage(name) != gScan->collectingOurs) { return; }
		ReadIconTgis(full, AddTgi, nullptr);
	}

	// Returns the number of UNCOVERED icons; logs the whole picture.
	//
	// TWO ROOTS (2026-08-22, "some assets don't scale" user report): SC4 loads
	// plugins from BOTH <install>\Plugins AND Documents\SimCity 4\Plugins -
	// caspe's log shows FontStyle being written to a GOG install-dir Plugins
	// AND an OneDrive Documents Plugins on the same launch. This scan used to
	// walk ONLY the DLL's own folder, so any third-party dat parked in the
	// install root was rendered by the game yet invisible here: never in
	// gFixList, never enlarged by stage 2 or the factory wrap, drawn at 1x
	// inside scaled flyouts. Both roots are now walked in both phases; AddTgi
	// already dedupes by instance across everything.
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

		gFixList.n = 0;   // keep the buffer; only the logical length resets
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

		// The second root: <install>\Plugins\ beside the running game. Empty
		// when the exe path cannot be parsed, and SKIPPED when it resolves to
		// the same folder as the DLL's own (a DLL deployed into the install
		// tree must not be walked twice - harmless but wasteful).
		wchar_t root2[kLongPath] = L"";
		{
			wchar_t instPlugins[MAX_PATH];
			InstallPluginsDir(instPlugins, MAX_PATH);
			if (instPlugins[0])
			{
				size_t n = wcslen(instPlugins);
				while (n > 0 && instPlugins[n - 1] == L'\\')
				{
					instPlugins[--n] = 0;
				}
				const wchar_t* docCmp = pluginsDir;
				if (wcsncmp(docCmp, L"\\\\?\\", 4) == 0) { docCmp += 4; }
				if (_wcsicmp(instPlugins, docCmp) != 0)
				{
					swprintf_s(root2, L"\\\\?\\%s", instPlugins);
				}
			}
		}
		Logger::Get().WriteLine(LogLevel::Info,
			"IconSynth: scan root 1 (DLL side): %ls%s",
			root,
			root2[0] ? "" : "   [scan root 2 (<install>\\Plugins): not "
			"scanned - unresolved or identical to root 1]");
		if (root2[0])
		{
			Logger::Get().WriteLine(LogLevel::Info,
				"IconSynth: scan root 2 (install side): %ls", root2);
		}

		gScan->collectingOurs = true;
		Walk(root, fp, OnFile, nullptr);
		if (root2[0]) { Walk(root2, fp, OnFile, nullptr); }
		const int nOurs = gScan->ours.n;
		if (nOurs > 0) { gControlInst = gScan->ours.data[0]; }

		Fingerprint fp2 = {};
		gScan->collectingOurs = false;
		Walk(root, fp2, OnFile, nullptr);
		if (root2[0]) { Walk(root2, fp2, OnFile, nullptr); }

		// The difference IS the defect set: icons some plugin supplies at 1x
		// that no package of ours enlarges. At any tier > 1 the engine scales
		// the strip's cell but not this art, so the draw over-reads - two
		// copies at rest, and nothing at all on hover once the state index
		// walks past the end of the texture.
		int uncovered = 0;
		int logged = 0;
		for (int i = 0; i < gScan->theirs.n; i++)
		{
			const uint32_t inst = gScan->theirs.data[i];
			bool covered = false;
			for (int j = 0; j < nOurs; j++)
			{
				if (gScan->ours.data[j] == inst) { covered = true; break; }
			}
			if (covered) { continue; }
			uncovered++;
			U32Push(gFixList, inst);
			if (logged < 24)
			{
				logged++;
				Logger::Get().WriteLine(LogLevel::Info,
					"IconSynth:   UNCOVERED icon {%08X,%08X,%08X} - this one "
					"renders doubled and vanishes on hover at f=%.2f",
					kIconType, kIconGroup, inst, factor);
			}
		}

		// UNCOVERED is now the EXACT count, not a lower bound: nothing above
		// this line can drop a TGI, so every one of them is either counted
		// here or already in gFixList for stage 2 to attempt.
		Logger::Get().WriteLine(LogLevel::Info,
			"IconSynth: scanned %u files / %llu bytes in %u ms "
			"(%d past MAX_PATH - #139 cost 10 missed icons to a truncating "
			"walk, so a 0 here on a NAM install means the \\\\?\\ prefix is "
			"not working). ours=%d theirs=%d UNCOVERED=%d%s  "
			"fingerprint=%u/%llu/%llu",
			fp2.files, fp2.bytes, GetTickCount() - t0, gLongPathsSeen,
			nOurs, gScan->theirs.n, uncovered,
			(logged < uncovered) ? " (list truncated at 24 for readability - "
				"every one is still counted and queued)" : "",
			fp2.files, fp2.bytes, fp2.newest);

		U32Free(gScan->ours);
		U32Free(gScan->theirs);
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
	// THIS IS NOT "THE UPSCALER IS ON". It touches ONLY the instances the
	// scan proved are UNCOVERED - art some plugin shipped at 1x that no
	// package of ours enlarges. Covered icons are never fetched, never
	// re-registered, never resampled. The resample itself is the same exact
	// nearest-neighbour pixel copy Upscale2x.cs performs offline, so a
	// synthesised icon is identical in character to every icon we ship.
	//
	// ONE-WAY DOOR AVOIDED DELIBERATELY: nothing here modifies the game's
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
	PtrList gHold = {};

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
	// ORDER IS LOAD-BEARING: Init reallocates, so the pixels must be read
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
					"IconSynth:   THE ORIGINAL COULD NOT BE RESTORED after a "
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
		// ONE LINE PER STEP, ON PURPOSE. The first build of this function
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
	// NOT by implementing cIGZPersistResourceFactory. It declares two
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
		for (int i = 0; i < gFixList.n; i++)
		{
			if (gFixList.data[i] == inst) { return true; }
		}
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
		if (gFixList.n <= 0)
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

		for (int i = 0; i < gFixList.n; i++)
		{
			const uint32_t inst = gFixList.data[i];
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
			if (newW <= sw)
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
					PtrPush(gHold, res);   // reference deliberately retained
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
					PtrPush(gHold, src);
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
		for (int i = 0; i < gFixList.n && i < 4; i++)
		{
			const cGZPersistResourceKey key(kIconType, kIconGroup, gFixList.data[i]);
			cIGZBuffer* shared = nullptr;
			cIGZBuffer* priv = nullptr;
			const bool gotShared = rm->GetResource(key, GZIID_cIGZBuffer,
				reinterpret_cast<void**>(&shared), 0, nullptr) && shared;
			const bool gotPriv = rm->GetPrivateResource(key, GZIID_cIGZBuffer,
				reinterpret_cast<void**>(&priv), 0, nullptr) && priv;
			Logger::Get().WriteLine(LogLevel::Info,
				"IconSynth: RE-FETCH {%08X} fixedPtr=%p | GetResource=%p %dx%d "
				"| GetPrivateResource=%p %dx%d | hasRegistered=%d",
				gFixList.data[i],
				(i < gHold.n) ? static_cast<void*>(gHold.data[i]) : nullptr,
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
			"skipped=%d failed=%d of %d uncovered. Every fixed icon is held "
			"by reference so the cache cannot drop it back to 1x.",
			GetTickCount() - t0, gMade, gMiss, gSkip, gFail, gFixList.n);
	}
}

namespace ScaleTier
{
	void GetPluginsRootW(wchar_t* out, size_t outLen)
	{
		PluginsRoot(out, outLen);
	}

	void GetOurFilePathW(const wchar_t* name, wchar_t* out, size_t outLen)
	{
		// The ini is the one file that does NOT live in our folder - route it
		// even if a caller asks for it by name, so there is exactly one answer
		// to "where is the ini" no matter which door you come in by.
		if (_wcsicmp(name, L"SC4UIScale.ini") == 0)
		{
			OurIniPath(out, outLen);
			return;
		}
		OurFilePath(name, out, outLen);
	}

	void GetOurFilePathA(const char* name, char* out, size_t outLen)
	{
		wchar_t wname[MAX_PATH] = {};
		MultiByteToWideChar(CP_ACP, 0, name, -1, wname, MAX_PATH);
		wchar_t wpath[MAX_PATH] = {};
		// THE SAME ROUTING AS THE W DOOR. This called OurFilePath directly and
		// so answered the package folder for the ini while every W caller
		// answered the root - two answers in one process. UiSpike's LiveTune
		// block comes through here, so its whole [Probe]/[Disaster]/[SubFlyout]
		// key set was reading a file that does not exist and silently taking
		// defaults. Proven by the shipped DLL's own log: line 2 names the root,
		// line 459 names 010-SC4UIScale\, same boot.
		if (_wcsicmp(wname, L"SC4UIScale.ini") == 0)
		{
			OurIniPath(wpath, MAX_PATH);
			WideCharToMultiByte(CP_ACP, 0, wpath, -1, out,
				static_cast<int>(outLen), nullptr, nullptr);
			return;
		}
		OurFilePath(wname, wpath, MAX_PATH);
		WideCharToMultiByte(CP_ACP, 0, wpath, -1, out,
			static_cast<int>(outLen), nullptr, nullptr);
	}

	// ============ v4.4.0 ROOT CLEANUP: LOOSE-FILE MIGRATION ===============
	// Through v4.3.1 this mod dropped FIVE loose files beside the DLL at the
	// Plugins ROOT (ini, log, gcap, the #104 csv, plus whatever the user's
	// own backups added). Every other DLL mod on a typical install leaves
	// two or three there, so ours was the untidiest thing in the folder -
	// and an sc4pac uninstall cannot reach loose root files it did not
	// install by name. From v4.4.0 the DLL is the ONLY thing we put at the
	// root (the loader is top-level only, so it has no choice); everything
	// else lives in 010-SC4UIScale/ and disappears with the folder.
	//
	// RUNS BEFORE Settings::Load AND BEFORE Logger::Init - it has to, or the
	// first read would miss a migrated ini and silently fall back to
	// defaults, which is the exact silent-partial-state class of bug this
	// project keeps paying for. It therefore cannot log; the director prints
	// the outcome as soon as the logger exists.
	//
	// The log is DELETED rather than moved: it is recreated with mode "w" on
	// every boot, so moving it would preserve one stale session and then
	// immediately overwrite it. The #104 csv is MOVED because SpinProbe
	// appends to it and it is never recreated - losing it loses the rate
	// history the probe exists to build.
	static int s_migrated = 0;
	static char s_migratedNames[128] = {};

	int MigrateRootLooseFiles()
	{
		wchar_t root[MAX_PATH] = {};
		PluginsRootQuiet(root, MAX_PATH);
		wchar_t dir[MAX_PATH] = {};
		swprintf_s(dir, L"%s010-SC4UIScale", root);
		CreateDirectoryW(dir, nullptr);   // harmless if it already exists

		struct Item { const wchar_t* name; const char* tag; bool keep; };
		// v4.5.0 REVERSES v4.4.0 FOR THE INI ALONE. A 4.4.0 install has it in
		// our folder; it has to come back to the root, because a package
		// manager deletes that folder wholesale on every update and would take
		// the tier choice with it. Carried, not recreated - the whole reason to
		// move it is that it holds settings somebody chose.
		{
			wchar_t folderIni[MAX_PATH] = {}, rootIni[MAX_PATH] = {};
			OurFilePath(L"SC4UIScale.ini", folderIni, MAX_PATH);
			OurIniPath(rootIni, MAX_PATH);
			if (folderIni[0] && rootIni[0] && FileExists(folderIni))
			{
				// A root ini that already exists is the live one and wins; the
				// folder copy is then a leftover, not a second opinion.
				if (FileExists(rootIni)) { DeleteFileW(folderIni); }
				else if (MoveFileExW(folderIni, rootIni, MOVEFILE_COPY_ALLOWED))
				{
					s_migrated++;
					if (strlen(s_migratedNames) + 12 < sizeof(s_migratedNames))
					{
						strcat_s(s_migratedNames, "ini->root ");
					}
				}
			}
		}

		const Item items[] = {
			{ L"SC4UIScale-104.csv", "csv",  true  },
			{ L"SC4UIScale.gcap",    "gcap", true  },
			{ L"SC4UIScale.log",     "log",  false },
		};
		for (const Item& it : items)
		{
			wchar_t src[MAX_PATH] = {};
			swprintf_s(src, L"%s%s", root, it.name);
			if (!FileExists(src)) { continue; }
			wchar_t dst[MAX_PATH] = {};
			OurFilePath(it.name, dst, MAX_PATH);
			bool done = false;
			if (!it.keep)
			{
				done = DeleteFileW(src) != 0;
			}
			else if (FileExists(dst))
			{
				// Already migrated on a previous boot and the root copy came
				// back (a re-run of an old installer). The in-folder copy is
				// the live one by construction - nothing has read either yet.
				done = DeleteFileW(src) != 0;
			}
			else
			{
				done = MoveFileExW(src, dst, MOVEFILE_COPY_ALLOWED) != 0;
			}
			if (!done) { continue; }
			s_migrated++;
			if (strlen(s_migratedNames) + strlen(it.tag) + 2 < sizeof(s_migratedNames))
			{
				strcat_s(s_migratedNames, it.tag);
				strcat_s(s_migratedNames, " ");
			}
		}
		return s_migrated;
	}

	const char* MigratedRootFileNames()
	{
		return s_migratedNames;
	}

	void LogOurDirs()
	{
		LogOurDirsImpl();
	}

	bool SeedIniIfAbsent()
	{
		return SeedIniIfAbsentImpl();
	}



	// ============ #201 SEGMENT CENSUS - A PROBE, NOT A FIX ================
	// THE QUESTION IT EXISTS TO ANSWER: can a loaded .dat be dropped from the
	// resource manager at runtime? If yes, this mod can stop RENAMING its own
	// files to arm a tier - every tier stays on disk under the name a package
	// manifest would carry, and sc4pac (which uninstalls BY NAME) stops
	// orphaning 78% of what it installed.
	//
	// The SDK says it is possible: GetSegmentCount / GetSegmentByIndex /
	// GetPath / UnregisterDBSegment are all declared. An API existing is a
	// HYPOTHESIS. This walk turns it into a measurement - and it ONLY
	// measures: it never unregisters anything.
	//
	// POSITIVE CONTROL IS THE POINT. A census that finds none of our dats is
	// evidence of nothing until it proves it could have seen them, so this
	// logs the TOTAL segment count and the OTHER paths it found even when our
	// own count is zero. A bare "0 of ours" line would be exactly the false
	// zero this project has already shipped twice.
	//
	// Default OFF ([Probe] SegmentCensus = 0). Log-only, one pass, at
	// PostAppInit - where #149 already established the dats are indexed.
	void SegmentCensus()
	{
		Logger& logger = Logger::Get();
		cIGZPersistResourceManagerPtr rm;
		if (!rm)
		{
			logger.WriteLine(LogLevel::Info,
				"SEGCENSUS ABORTED - no resource manager. A zero count here "
				"would be an INSTRUMENT FAILURE, not a clean bill of health.");
			return;
		}

		const uint32_t total = rm->GetSegmentCount();
		logger.WriteLine(LogLevel::Info,
			"SEGCENSUS: %u registered DB segment(s). Walking them for a path "
			"each - this is the list a load-time tier exclusion would filter.",
			total);
		if (total == 0)
		{
			logger.WriteLine(LogLevel::Info,
				"SEGCENSUS: ZERO segments. Either this runs before the plugin "
				"scan or GetSegmentCount is not the accessor - EITHER WAY the "
				"question is unanswered, not answered 'no'.");
			return;
		}

		uint32_t ours = 0, named = 0, unnamed = 0;
		for (uint32_t i = 0; i < total; i++)
		{
			cIGZPersistDBSegment* seg = rm->GetSegmentByIndex(i);
			if (!seg) { unnamed++; continue; }
			cRZBaseString path;
			seg->GetPath(path);
			const char* p = path.ToChar();
			if (!p || !*p) { unnamed++; continue; }
			named++;
			const bool mine = (strstr(p, "SC4UIScale") != nullptr);
			if (mine) { ours++; }
			// Every path, ours or not: the non-ours ones ARE the positive
			// control. Trimmed to the last two path components so the line
			// stays readable without hiding which folder it came from.
			const char* tail = p;
			int seps = 0;
			for (const char* q = p + strlen(p); q > p; q--)
			{
				if (*(q - 1) == '\\' || *(q - 1) == '/')
				{
					if (++seps == 2) { tail = q; break; }
				}
			}
			logger.WriteLine(LogLevel::Info,
				"SEGCENSUS  [%3u] %s%s", i, tail, mine ? "   <- OURS" : "");

			// ROUND 2 (2026-08-29). Round 1 measured 12 segments, 12 paths,
			// ZERO ours - and named the reason: both Plugins trees register
			// as ONE segment each, so the individual .dat files are not
			// segments at this level. Unregistering one would drop EVERY mod
			// in that folder, which is not a tier switch.
			//
			// But cIGZPersistDBSegmentMultiPackedFiles declares its OWN
			// GetSegmentCount/GetSegmentByIndex - child packed files. If the
			// Plugins segment is one of those, the individual dats ARE
			// reachable one level down, and the question reopens there.
			// Ask by QueryInterface; a refusal is itself the answer.
			cIGZPersistDBSegmentMultiPackedFiles* multi = nullptr;
			if (!seg->QueryInterface(GZIID_cIGZPersistDBSegmentMultiPackedFiles,
					reinterpret_cast<void**>(&multi)) || !multi)
			{
				continue;
			}
			const uint32_t kids = multi->GetSegmentCount();
			uint32_t kidsOurs = 0, kidsNamed = 0;
			for (uint32_t k = 0; k < kids; k++)
			{
				cIGZPersistDBSegment* kid = multi->GetSegmentByIndex(k);
				if (!kid) { continue; }
				cRZBaseString kp;
				kid->GetPath(kp);
				const char* kpc = kp.ToChar();
				if (!kpc || !*kpc) { continue; }
				kidsNamed++;
				if (strstr(kpc, "SC4UIScale") != nullptr)
				{
					kidsOurs++;
					const char* kt = kpc;
					int ks = 0;
					for (const char* q = kpc + strlen(kpc); q > kpc; q--)
					{
						if (*(q - 1) == '\\' || *(q - 1) == '/')
						{
							if (++ks == 2) { kt = q; break; }
						}
					}
					logger.WriteLine(LogLevel::Info,
						"SEGCENSUS    child[%3u] %s   <- OURS", k, kt);
				}
			}
			logger.WriteLine(LogLevel::Info,
				"SEGCENSUS  [%3u] is a MULTI-PACKED segment: %u child(ren), "
				"%u with a path, %u ours. If ours > 0 the individual dats ARE "
				"addressable one level down. If children exist but none are "
				"ours, the walk works and our dats live elsewhere - a real "
				"answer either way.", i, kids, kidsNamed, kidsOurs);
			multi->Release();
		}
		logger.WriteLine(LogLevel::Info,
			"SEGCENSUS TOTAL: %u segment(s), %u with a readable path, %u "
			"without, %u ours. If 'ours' is 0 while 'with a readable path' is "
			"large, the walk works and our dats are simply not segments - a "
			"real answer. If BOTH are 0 the instrument failed and nothing was "
			"measured.", total, named, unnamed, ours);
	}


	// THE fit predicate. Extracted from Decide 2026-08-19 so the in-game
	// selector can ask the same question the boot path asks, rather than
	// carrying its own copy of 880/558/800/600 - a second copy would be a
	// second rule, and this one is shown to the player as a promise about
	// what will happen at the next launch.
	// EXPLICIT MINIMUM RESOLUTIONS PER TIER (user instruction 2026-08-19:
	// "you need to have minimum resolutions for all the scaling coded in").
	//
	// THE OLD RULE PASSED A CONFIGURATION THAT DEMONSTRABLY DOES NOT WORK.
	// It was three inequalities - 880*f <= w, 558*f <= h, and f <= the density
	// cap min(w/800, h/600) - and at 1920x1200 the cap is EXACTLY 2.00, so 2x
	// passed by sitting precisely on the boundary. On screen it does not fit:
	// the player measured the options menu pushed over the other menus. A tier
	// admitted at the exact cap has zero headroom, and zero headroom is not a
	// margin, it is a coincidence.
	//
	// So the thresholds now come from the CONTROLS, which is the standing law
	// for this project - measure the known-good set, and if the gauge fails
	// them the gauge is wrong:
	//     2x   @ 2400x1600  GOOD (weeks of daily use)
	//     2x   @ 1920x1200  BAD  (measured 2026-08-19, this defect)
	//     1.5x @ 1920x1200  GOOD (same session)
	//     3x   @ 3840x2160  GOOD (confirmed on screen)
	// One stated choice - 20% density headroom over the 800x600 feel - lands a
	// table consistent with every one of those four points, which is the most
	// any threshold here can currently claim:
	//     minW = max(880*f, 800*f * 1.2) = 960*f
	//     minH = max(558*f, 600*f * 1.2) = 720*f
	//
	// The numbers are written out rather than computed so they can be READ,
	// argued with, and corrected against the next measurement - a threshold
	// nobody can see is a threshold nobody will check.
	struct TierMinRow { float factor; int minW; int minH; };
	const TierMinRow kTierMinimums[] = {
		{ 1.5f, 1440, 1080 },   // 1920x1200 clears this - confirmed good there
		{ 2.0f, 1920, 1440 },   // 1920x1200 FAILS on height - the measured defect
		{ 3.0f, 2880, 2160 },   // 3840x2160 clears this - confirmed good there
		{ 4.0f, 3840, 2880 },   // no package ships for 4x; kept so the table is
		                        // total over kPackages rather than silently
		                        // falling through for one row.
	};
	const int kTierMinimumCount =
		static_cast<int>(sizeof(kTierMinimums) / sizeof(kTierMinimums[0]));

	bool TierMinimumFor(float factor, int* outW, int* outH)
	{
		for (int i = 0; i < kTierMinimumCount; i++)
		{
			if (factor >= kTierMinimums[i].factor - 0.01f
				&& factor <= kTierMinimums[i].factor + 0.01f)
			{
				if (outW) { *outW = kTierMinimums[i].minW; }
				if (outH) { *outH = kTierMinimums[i].minH; }
				return true;
			}
		}
		return false;
	}

	bool Fits(float factor, int width, int height)
	{
		if (width <= 0 || height <= 0 || factor <= 1.01f)
		{
			// Stock always fits and is always available: it needs no package
			// and no room.
			return factor <= 1.01f;
		}
		int minW = 0, minH = 0;
		if (TierMinimumFor(factor, &minW, &minH))
		{
			return width >= minW && height >= minH;
		}
		// A factor with no table row is not a tier we ship. Refuse rather
		// than fall back to the old arithmetic: ValidateBootState's C5/C6
		// reject it by name, and a second opinion here would only disagree.
		return false;
	}

	bool TierMinimum(float factor, int* outW, int* outH)
	{
		return TierMinimumFor(factor, outW, outH);
	}

	bool KnownFactor(float factor)
	{
		for (int i = 0; i < kPackageCount; i++)
		{
			if (factor >= kPackages[i].factor - 0.01f
				&& factor <= kPackages[i].factor + 0.01f)
			{
				return true;
			}
		}
		return false;
	}

	bool PackageAvailable(float factor)
	{
		for (int i = 0; i < kPackageCount; i++)
		{
			if (factor >= kPackages[i].factor - 0.01f
				&& factor <= kPackages[i].factor + 0.01f)
			{
				return PackageInstalled(kPackages[i]);
			}
		}
		return false;
	}

	// ============ THE BOOT-STATE VALIDATOR ================================
	// REQUIREMENT: "if a user manually adjusts the ini file we need to run a
	// check for 'resolution and scale combination correct', and if it flags
	// false we should flip it back to auto. Automatically."
	//
	// Every condition below is a MEASURED failure mode, not a defensive
	// guess - each one was reproduced against this code and then survived an
	// adversarial pass whose job was to refute it. The order matters and is
	// commented at each step.
	bool ValidateBootState(BootState& st, const wchar_t* iniPath)
	{
		// The installed census, printed nowhere before today. Half the
		// failure modes are invisible without it, because "which tiers does
		// this install actually have art for" was never in the log.
		const bool have15 = PackageAvailable(1.5f);
		const bool have2 = PackageAvailable(2.0f);
		const bool have3 = PackageAvailable(3.0f);
		const bool have4 = PackageAvailable(4.0f);
		const bool measured = (st.renderW > 0 && st.renderH > 0);

		Logger::Get().WriteLine(LogLevel::Info,
			"BootState: AutoScale=%d ScaleFactor(ini)=%.2f ScaleAll=%d "
			"render=%dx%d%ls installed{1.5=%d 2=%d 3=%d 4=%d}",
			st.autoScale ? 1 : 0, st.factor, st.scaleAll ? 1 : 0,
			st.renderW, st.renderH, measured ? L"" : L" (UNMEASURED)",
			have15 ? 1 : 0, have2 ? 1 : 0, have3 ? 1 : 0, have4 ? 1 : 0);

		// ---- C0: did we actually READ the file? --------------------------
		// A UTF-8 BOM on the FIRST line destroys the first section header, so
		// every key silently returns its built-in default - AutoScale=1,
		// ScaleAll=0, ScaleFactor=2.0 - which is precisely the art-armed,
		// geometry-off state below. MEASURED against a real ini in four
		// encodings: with a BOM and [UiSpike] on line 1, every key reads
		// empty while the SECOND section still reads fine.
		//
		// AN EMPTY SECTION READ IS A READ FAILURE, NOT A REQUEST FOR
		// DEFAULTS. It is also the positive control for this whole function:
		// if we could not read the file, nothing below is evidence of
		// anything.
		//
		// (The shipped ini is immune - its line 1 is a ';' comment, which
		// absorbs the BOM. This catches a hand-edited or re-saved one.)
		if (iniPath != nullptr && iniPath[0] != 0 && FileExists(iniPath))
		{
			wchar_t sect[64] = {};
			const DWORD n = GetPrivateProfileSectionW(L"UiSpike", sect, 64,
				iniPath);
			if (n == 0)
			{
				st.autoScale = false;
				st.factor = 1.0f;
				Logger::Get().WriteLine(LogLevel::Info,
					"BootState REPAIR: the ini exists but its [UiSpike] "
					"section reads EMPTY - a UTF-8 BOM on the first line "
					"destroys the first section header and every key then "
					"falls back to its built-in default. Forcing stock. "
					"NOTHING written to that file: the write would append a "
					"SECOND [UiSpike] and make it worse. Re-save it as ANSI "
					"or UTF-16LE.");
				return false;
			}
		}

		// ---- C1: ScaleAll off while the factor asks for a tier -----------
		// THE WORST OF THE MEASURED FAILURES, because it traps the player.
		// The art/font layer is armed FROM THE FACTOR, while every geometry
		// consumer is gated on ScaleAll - so ScaleAll=0 with a tier means
		// tier art and tier fonts drawn inside 1x windows. And the in-game
		// selector cannot repair it: it writes AutoScale and ScaleFactor,
		// never ScaleAll, so every row it offers leaves the art armed.
		//
		// A DELETED KEY REACHES THIS TOO. GetPrivateProfileIntW returns 0 for
		// any WORD ("true", "yes", "on"), and the built-in default is false,
		// so a missing key is indistinguishable from a disabled one.
		//
		// Remedy is to LOWER THE ART TO THE GEOMETRY, never to switch a
		// subsystem on behind the player's back: ScaleAll is their own off
		// switch, and their stored tier preference is not ours to overwrite.
		// Nothing is written; the log names the key to restore.
		const float effective = st.autoScale
			? Decide(st.renderW, st.renderH) : st.factor;
		if (!st.scaleAll && effective > 1.01f)
		{
			Logger::Get().WriteLine(LogLevel::Info,
				"BootState REPAIR: ScaleAll=0 (or the key is missing - its "
				"built-in default is 0) but the factor asks for %.2f. Art and "
				"fonts are armed from the factor while every geometry patch "
				"is gated on ScaleAll, so this would draw %.2fx art inside 1x "
				"windows. Forcing stock: factor 1.00, every package stashed. "
				"NOTHING written to the ini - restore ScaleAll=1 to get "
				"scaling back.", effective, effective);
			st.autoScale = false;
			st.factor = 1.0f;
			return false;
		}

		// Everything below judges a MANUAL factor. Auto cannot fail them:
		// Decide only ever returns a tier that is installed and fits.
		if (st.autoScale)
		{
			Logger::Get().WriteLine(LogLevel::Info,
				"BootState: COHERENT (AutoScale - the tier is derived, so it "
				"is installed and fits by construction).");
			return true;
		}

		// ---- C2: finite ---------------------------------------------------
		// wcstod accepts inf, nan, infinity, 0x1p3. NaN fails EVERY
		// comparison, so it slips past `factor > 1.01f` in both the package
		// guard and the stock block, and reaches the tier mirror and the
		// code-patch battery that write factor-derived immediates into .text.
		if (!(st.factor == st.factor) || st.factor > 1.0e6f
			|| st.factor < -1.0e6f)
		{
			const float was = st.factor;
			st.autoScale = true;
			st.factor = Decide(st.renderW, st.renderH);
			WriteRepairedIni(iniPath, st.factor);
			Logger::Get().WriteLine(LogLevel::Info,
				"BootState REPAIR: ScaleFactor %.2f is not a finite number. "
				"Falling back to Auto, which picks %.2f. Written back so the "
				"file, the running game and the in-game selector agree.",
				was, st.factor);
			return false;
		}

		// ---- C3: below stock -> clamp, do NOT flip ------------------------
		// A negative or zero factor already lands on coherent stock; this
		// only stops "-2.00" leaking into the tier mirror's 97 readers and
		// into the Graphic Options readout. Flipping here would turn scaling
		// ON in a state that is already correct.
		if (st.factor < 1.0f)
		{
			Logger::Get().WriteLine(LogLevel::Info,
				"BootState: ScaleFactor %.2f is below stock - clamped to 1.00 "
				"for the tier mirror and the readout. AutoScale left at %d "
				"(this is already a stock state, not a repair).",
				st.factor, st.autoScale ? 1 : 0);
			st.factor = 1.0f;
			return false;
		}

		// ---- C4: manual stock is COHERENT, and must short-circuit ---------
		// Set-Tier.ps1 -Tier 1 writes exactly this for every 1x reference
		// capture. Stock needs no package and no room, so returning here is
		// what makes it impossible for a baseline to be flipped back on.
		if (st.factor <= 1.01f)
		{
			Logger::Get().WriteLine(LogLevel::Info,
				"BootState: COHERENT (manual stock - needs no package and no "
				"room; a 1x reference capture can never be flipped).");
			return true;
		}

		// ---- C5: a tier the package table knows -------------------------
		// SyncStaticLayers REFUSES a non-table factor and returns, leaving
		// last boot's art armed while the sweep runs at the new one.
		if (!KnownFactor(st.factor))
		{
			const float was = st.factor;
			st.autoScale = true;
			st.factor = Decide(st.renderW, st.renderH);
			WriteRepairedIni(iniPath, st.factor);
			Logger::Get().WriteLine(LogLevel::Info,
				"BootState REPAIR: ScaleFactor %.2f is not a supported tier "
				"(1.5 / 2 / 3). The art layer would have stayed at whatever "
				"was armed last boot while geometry scaled by %.2f. Falling "
				"back to Auto, which picks %.2f - written back.",
				was, was, st.factor);
			return false;
		}

		// ---- C6: and that tier's art is ON DISK --------------------------
		// The manual path never asked. kPackages carries a 4.0 row that no
		// package has ever been built for, so ScaleFactor=4 passed every
		// existing check, stashed all three real tiers and armed nothing -
		// including the stock-tier selector, leaving no way back.
		if (!PackageAvailable(st.factor))
		{
			const float was = st.factor;
			st.autoScale = true;
			st.factor = Decide(st.renderW, st.renderH);
			WriteRepairedIni(iniPath, st.factor);
			Logger::Get().WriteLine(LogLevel::Info,
				"BootState REPAIR: ScaleFactor %.2f is a supported tier but "
				"NO package for it is installed. Selecting it stashes every "
				"tier that IS installed and arms none, which takes the "
				"in-game selector down with it. Falling back to Auto, which "
				"picks %.2f - written back.", was, st.factor);
			return false;
		}

		// ---- C7: and the screen can carry it -----------------------------
		// The trap the case raised: a tier chosen on a large display puts
		// Graphic Options (558 design px tall) off-screen on a smaller one,
		// and that dialog is the only in-game way back.
		if (!measured)
		{
			Logger::Get().WriteLine(LogLevel::Info,
				"BootState: render resolution UNMEASURED (0x0) - the FIT "
				"check is skipped; a missing number is not evidence of a "
				"small screen. The finite / supported-tier / package-installed "
				"checks all still ran.");
			return true;
		}
		if (!Fits(st.factor, st.renderW, st.renderH))
		{
			const float was = st.factor;
			st.autoScale = true;
			st.factor = Decide(st.renderW, st.renderH);
			WriteRepairedIni(iniPath, st.factor);
			Logger::Get().WriteLine(LogLevel::Info,
				"BootState REPAIR: ScaleFactor %.2f does not fit %dx%d - the "
				"UI would be scaled past the screen and Graphic Options, the "
				"only way to change it, would go off-screen with it. Falling "
				"back to Auto, which picks %.2f - written back.",
				was, st.renderW, st.renderH, st.factor);
			return false;
		}

		Logger::Get().WriteLine(LogLevel::Info,
			"BootState: COHERENT (manual %.2f - supported, installed, and it "
			"fits %dx%d).", st.factor, st.renderW, st.renderH);
		return true;
	}

	float Decide(int width, int height)
	{
		if (width <= 0 || height <= 0)
		{
			return 1.0f;
		}

		for (int i = 0; i < kPackageCount; i++)
		{
			const Package& pkg = kPackages[i];
			if (!PackageInstalled(pkg))
			{
				continue;
			}
			if (Fits(pkg.factor, width, height))
			{
				return pkg.factor;
			}
		}
		return 1.0f; // stock
	}

	// THE ONE PACKAGE ARMED BY THE ABSENCE OF A TIER.
	// z_SC4UIScale_SelectorUI-1x carries a single script: Graphic Options at
	// STOCK geometry with the scale-selector nodes injected. Its gate is the
	// INVERSE of every other package - live only when NO tier is active -
	// because 1x without the selector is a one-way door: every other package
	// is stashed, so the only way back up would be editing the ini by hand.
	//
	// IT LIVED INSIDE SyncStaticLayers FOR ONE BUILD AND THAT WAS THE BUG.
	// SyncStaticLayers is not called at the stock tier - the director's own log
	// says "static layers untouched (ScaleAll=0 or stock factor)" - so the
	// package could never be armed in THE EXACT STATE IT EXISTS FOR. Measured
	// 2026-08-19: a 1x machine had z_SC4UIScale_SelectorUI-1x.dat.x1-disabled
	// on disk, the DLL logged that the selector "IS serviced", and the dialog
	// had no selector in it. The code half ran and the data half was stashed.
	//
	// THIRD RECORDING OF THIS SHAPE IN THIS FILE'S NEIGHBOURHOOD (#149 and
	// #182 are the others, both in SC4UIScaleDllDirector.cpp beside the call
	// site). BOLTING WORK ONTO A CONVENIENT NEIGHBOUR MAKES IT INHERIT THAT
	// NEIGHBOUR'S GATE SILENTLY. The condition this depends on is "is the tier
	// stock", so that is the only thing it may be gated on - and the caller
	// invokes it UNCONDITIONALLY.
	void SyncSelectorPackage(bool stockTier)
	{
		// v4.2.0: zzz-SC4UIScale stays a TOP-LEVEL Plugins folder (its whole
		// purpose is sorting after 150-mods etc.), so with the DLL living in
		// 010-SC4UIScale\ the sync dir is the PLUGINS ROOT, not DllDir.
		wchar_t pluginsRoot[MAX_PATH];
		PluginsRoot(pluginsRoot, MAX_PATH);
		SyncDat(pluginsRoot, L"zzz-SC4UIScale\\z_SC4UIScale_SelectorUI",
			L"-1x", stockTier);
		Logger::Get().WriteLine(LogLevel::Info,
			"ScaleTier: SelectorUI-1x %ls (tier is %ls). This is the ONLY "
			"package armed by the ABSENCE of a tier, and it is what keeps 1x "
			"from being a one-way door.",
			stockTier ? L"ARMED" : L"stashed",
			stockTier ? L"stock" : L"scaled");
	}

	void EnlargeUncoveredIcons(float factor)
	{
		IconSynth::EnlargeAndRegister(factor);
	}

	// ICONSYNTH stage 1 (task #149) - SEPARATE FROM SyncStaticLayers ON PURPOSE.
	//
	// IT USED TO LIVE INSIDE SyncStaticLayers AND THAT WAS A REAL BUG.
	// SyncStaticLayers RAN ONLY on the AutoScale path back then (NO LONGER
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
		// v4.2.0: this scan's whole purpose is enumerating THIRD-PARTY icon
		// art, so its root is the real Plugins root - scoped to DllDir it
		// would see only our own folder, report UNCOVERED=0, and every
		// third-party icon would silently regress to the #149 shape.
		wchar_t plugDir[MAX_PATH];
		PluginsRoot(plugDir, MAX_PATH);
		size_t pl = wcslen(plugDir);
		while (pl > 0 && plugDir[pl - 1] == 92) { plugDir[--pl] = 0; }
		IconSynth::ScanAndReport(plugDir, factor);
	}

	// cyclone-boom "Web Button Improvement Mod": when installed it owns the
	// region website button (its own text + link), so our WebText override and
	// ShellExecute redirect must both step aside. Detected by file name,
	// searched recursively (the dat name varies by option A/B/C and version).
	bool WebButtonModPresent(const wchar_t* pluginsDir)
	{
		const wchar_t* needle = L"web button improvement mod";
		// BOTH PLUGIN ROOTS (2026-08-22): the game loads <install>\Plugins as
		// well, and the same blind spot that hid install-root icons from the
		// uncovered-icon scan would here keep our WebText override armed
		// against a mod installed in the other root - its text would fight
		// ours on the region screen.
		wchar_t instPlugins[MAX_PATH];
		InstallPluginsDir(instPlugins, MAX_PATH);
		for (int pass = 0; pass < 2; pass++)
		{
			const wchar_t* dir = (pass == 0) ? pluginsDir : instPlugins;
			if (!dir[0]) { continue; }
			if (pass == 1 && _wcsicmp(instPlugins, pluginsDir) == 0)
			{
				continue;   // one tree, already searched
			}
			try
			{
				for (const auto& entry : std::filesystem::recursive_directory_iterator(dir))
				{
					if (!entry.is_regular_file()) { continue; }
					std::wstring name = entry.path().filename().wstring();
					for (wchar_t& c : name) { c = static_cast<wchar_t>(towlower(c)); }
					if (name.find(needle) != std::wstring::npos) { return true; }
				}
			}
			catch (...) { /* unreadable tree -> treat as absent */ }
		}
		return false;
	}

	void SyncStaticLayers(float factor)
	{
		// PACKAGES live beside the DLL in Documents\SimCity 4\Plugins (dats
		// + per-factor font sources; the player's plugins-only requirement).
		// ONE exception, forced by the engine: the game probes the loose
		// FontStyle.ini in <install>\Plugins ONLY (never Documents - the
		// 2026-07-22 "Documents works" test was a timing confound), so the
		// active font is mirrored there each boot. That write stays inside
		// a Plugins folder and is DLL-managed - no manual install steps.
		wchar_t docPlugins[MAX_PATH];
		// v4.2.0: packages+fonts live in 010-SC4UIScale\, the DLL at root.
		OurPackagesDir(docPlugins, MAX_PATH);
		wchar_t instPlugins[MAX_PATH];
		InstallPluginsDir(instPlugins, MAX_PATH);
		// v4.2.0: our own packages live beside the DLL (docPlugins =
		// Plugins\010-SC4UIScale\); everything that faces OTHER mods -
		// dependency walks, web-button detection, the zzz-SC4UIScale
		// overrides (a TOP-LEVEL folder by design) - roots at the real
		// Plugins root.
		wchar_t pluginsRoot[MAX_PATH];
		PluginsRoot(pluginsRoot, MAX_PATH);

		// WEB BUTTON IMPROVEMENT MOD - INVERSE GATE. When the mod is installed
		// it owns the region website button (its own LTEXT + link), so our
		// WebText override must step aside or its text wins over the mod's
		// (root load order: our z_SC4UIScale_WebText sorts after the mod's
		// dat). Disabled while the mod is present, re-enabled when it is gone.
		// Runs before the factor guard below so it applies at every tier,
		// including stock. (The ShellExecute redirect is gated separately in
		// the director.)
		const bool webBtnPresent = WebButtonModPresent(pluginsRoot);
		SyncDat(docPlugins, L"z_SC4UIScale_WebText", L"", !webBtnPresent);

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
		// MEMOIZED lookups (2026-08-25, review finding 4): the eight ZCarbon
		// rows share two filenames (scoty_Carbon_Files.dat x8,
		// scoty_carbon_PNG.dat x3), and a FindPluginFile walk has no early
		// exit on failure - it enumerates the whole tree to depth 4. Without
		// this cache a no-skin machine pays 8 extra full-tree walks at DLL
		// load, and this project's own law says a ~3s cost on a watched
		// moment is a freeze. One walk per DISTINCT (name, prefix) pair.
		struct DepLookup { const wchar_t* name; bool prefix; bool present;
		                   DWORD size; wchar_t hit[MAX_PATH]; };
		DepLookup cache[2 * 32] = {};
		int cacheN = 0;
		auto findCached = [&](const wchar_t* name, bool prefix,
		                      wchar_t* outHit, DWORD* outSz) -> bool {
			for (int c = 0; c < cacheN; c++)
			{
				if (cache[c].prefix == prefix
					&& _wcsicmp(cache[c].name, name) == 0)
				{
					wcscpy_s(outHit, MAX_PATH, cache[c].hit);
					*outSz = cache[c].size;
					return cache[c].present;
				}
			}
			wchar_t h[MAX_PATH] = {};
			DWORD s = 0;
			int matches = 0;
			const bool p = FindPluginFile(
				pluginsRoot, name, prefix, 4, h, MAX_PATH, &s, &matches);
			if (matches > 1)
			{
				// The gate fingerprints the copy found FIRST; the game loads
				// every copy and renders the later-sorting one. Never silent.
				Logger::Get().WriteLine(
					LogLevel::Info,
					"ScaleTier: DUPLICATE dep source - %d copies of %ls in the "
					"Plugins tree; the gate checked %ls but the game may render "
					"a different copy. Remove the stale one.",
					matches, name, h);
			}
			if (cacheN < static_cast<int>(sizeof(cache) / sizeof(cache[0])))
			{
				cache[cacheN].name = name;
				cache[cacheN].prefix = prefix;
				cache[cacheN].present = p;
				cache[cacheN].size = s;
				wcscpy_s(cache[cacheN].hit, MAX_PATH, h);
				cacheN++;
			}
			wcscpy_s(outHit, MAX_PATH, h);
			*outSz = s;
			return p;
		};
		for (int d = 0; d < kThirdPartyDepCount; d++)
		{
			const ThirdPartyDep& dep = kThirdPartyDeps[d];
			wchar_t hit[MAX_PATH] = {};
			DWORD sz = 0;
			bool present = findCached(dep.modFile, dep.prefixMatch, hit, &sz);
			bool sizeOk = (dep.modSize == 0) || (sz == dep.modSize);
			// WHICH file failed, and what WE expected of THAT file. Both must
			// travel together: the old code swapped in file 2's byte count but
			// went on printing file 1's NAME and file 1's EXPECTED size, so a
			// second-file mismatch logged a nonsense comparison against the
			// wrong filename (every ZCarbon row pins a second file, so this
			// fired precisely in the re-install-a-different-build case).
			const wchar_t* failName = dep.modFile;
			DWORD failExpect = dep.modSize;
			if (present && sizeOk && dep.modFile2 != nullptr)
			{
				wchar_t hit2[MAX_PATH] = {};
				DWORD sz2 = 0;
				const bool p2 = findCached(dep.modFile2,
					dep.prefixMatch, hit2, &sz2);
				const bool s2 = (dep.modSize2 == 0) || (sz2 == dep.modSize2);
				if (!p2 || !s2)
				{
					// Report the SECOND file as the reason, not the first -
					// a message naming the file that was fine would send the
					// next reader looking in the wrong place.
					present = p2;
					sizeOk = s2;
					sz = sz2;
					failName = dep.modFile2;
					failExpect = dep.modSize2;
					swprintf_s(hit, L"%s", dep.modFile2);
				}
			}
			depOk[d] = present && sizeOk;
			// "The stock package takes over" is TRUE only when the mod is
			// GONE. A RESKIN that is still installed keeps winning the load
			// order after we disarm, so our stock-derived layer does NOT take
			// over - it loses to the mod's own 1x data. Measured 2026-08-25:
			// with the ZCarbon set off and the skin present, carbon beats our
			// 010 layer on 473 TGIs. Say which case this is.
			const bool skinStillLoads =
				(wcsstr(dep.package, L"ZCarbon") != nullptr);
			if (!present)
			{
				Logger::Get().WriteLine(
					LogLevel::Info,
					"ScaleTier: %ls dep ABSENT (%ls) -> disabled; the stock "
					"package takes over.", dep.package, failName);
				// PARTIAL uninstall: the OTHER pinned file of this row may
				// still be installed, in which case that mod keeps winning
				// and the stock package takes over NOTHING. Measured: losing
				// only scoty_Carbon_Files.dat costs 336 TGIs across all eight
				// carbon packages while eleven skin dats keep loading.
				if (skinStillLoads && dep.modFile2 != nullptr)
				{
					wchar_t other[MAX_PATH] = {};
					DWORD otherSz = 0;
					const wchar_t* otherName =
						(failName == dep.modFile) ? dep.modFile2 : dep.modFile;
					if (findCached(otherName, dep.prefixMatch, other, &otherSz))
					{
						Logger::Get().WriteLine(
							LogLevel::Info,
							"ScaleTier:   ^ PARTIAL: %ls is still installed, so "
							"the skin keeps winning those TGIs and draws its own "
							"1x art inside scaled cells. Restore %ls, or remove "
							"the skin entirely - a half-removed skin is the one "
							"state nothing of ours can cover.",
							otherName, failName);
					}
				}
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
					dep.package, failName, sz, failExpect);
				if (skinStillLoads)
				{
					Logger::Get().WriteLine(
						LogLevel::Info,
						"ScaleTier:   ^ THE SKIN IS STILL INSTALLED, so nothing "
						"of ours takes over - it keeps winning those TGIs and "
						"will draw its own 1x art inside scaled cells. Rebuild "
						"the carbon packages (tools\\research\\carbon, see "
						"CARBON-COMPAT.md) to restore scaled carbon styling.");
				}
			}
			else
			{
				Logger::Get().WriteLine(
					LogLevel::Info, "ScaleTier: %ls dep ok (%ls).",
					dep.package, hit);
			}
		}

		// PUBLIC-INSTALL NET (2026-08-25). The released bundle deliberately
		// ships NO carbon-derived dats (they are another author's pixels), so
		// a player who installs the skin and our release gets the skin
		// winning ~473 TGIs at 1x inside a scaled UI - and every gate stays
		// green, because the packages simply do not exist to be checked.
		// Nothing else in the product would ever tell them. This does.
		bool carbonSkinPresent = false;
		wchar_t carbonSkinPath[MAX_PATH] = {};
		for (int c = 0; c < cacheN; c++)
		{
			if (cache[c].present
				&& _wcsicmp(cache[c].name, L"scoty_Carbon_Files.dat") == 0)
			{
				carbonSkinPresent = true;
				wcscpy_s(carbonSkinPath, MAX_PATH, cache[c].hit);
				break;
			}
		}
		if (carbonSkinPresent)
		{
			// THE COMPARATOR-AMBIGUOUS FOLDER, checked at runtime (2026-08-25).
			// Our overrides only win because zzz-SC4UIScale sorts last. '_'
			// (0x5F) sits BETWEEN the upper-case letters and the lower-case
			// ones, so a folder like the skin author's own `z____scoty_mods`
			// sorts BEFORE us when the comparator upcases and AFTER us when it
			// lowercases - and in the second case every package we just armed
			// is inert. The installer renames it; a player who unzips the mod
			// by hand gets the ambiguous name back, and nothing else would
			// ever tell them.
			const size_t rootLen = wcslen(pluginsRoot);
			if (_wcsnicmp(carbonSkinPath, pluginsRoot, rootLen) == 0)
			{
				wchar_t folder[MAX_PATH] = {};
				wcscpy_s(folder, MAX_PATH, carbonSkinPath + rootLen);
				if (wchar_t* slash = wcschr(folder, L'\\'))
				{
					*slash = L'\0';
				}
				auto foldCmp = [](const wchar_t* a, const wchar_t* b,
				                  bool upper) -> int {
					for (;; ++a, ++b)
					{
						wchar_t ca = *a, cb = *b;
						if (upper)
						{
							if (ca >= L'a' && ca <= L'z') { ca = ca - 32; }
							if (cb >= L'a' && cb <= L'z') { cb = cb - 32; }
						}
						else
						{
							if (ca >= L'A' && ca <= L'Z') { ca = ca + 32; }
							if (cb >= L'A' && cb <= L'Z') { cb = cb + 32; }
						}
						if (ca != cb) { return (ca < cb) ? -1 : 1; }
						if (ca == 0) { return 0; }
					}
				};
				// Compare against the folder we ACTUALLY occupy. Against the
				// literal v4.2.0 name this verdict was computed for a folder
				// that need not exist, and got the answer wrong in both
				// directions on any package-manager install.
				wchar_t ourTop[MAX_PATH] = {};
				OverrideTopLevel(ourTop, MAX_PATH);
				const int cUp = foldCmp(folder, ourTop, true);
				const int cLo = foldCmp(folder, ourTop, false);
				if (cUp >= 0 || cLo >= 0)
				{
					Logger::Get().WriteLine(
						LogLevel::Info,
						"ScaleTier: WARNING - the skin folder '%ls' can sort "
						"AT/AFTER our override folder '%ls' (upcased cmp %d, "
						"lowercased cmp %d). Under that ordering the skin loads "
						"after our overrides and every carbon package is armed "
						"but never rendered. Rename the folder so it sorts "
						"earlier under both foldings (the supported name is "
						"zz-scoty-mods).",
						folder, ourTop, cUp, cLo);
				}
			}
		}
		if (carbonSkinPresent)
		{
			// Our override folder is NOT named zzz-SC4UIScale under a package
			// manager - it is <group>.<name>.<version>.sc4pac. Hard-coding the
			// v4.2.0 name here made a correct install report "installed but NO
			// carbon packages are present" with 44 carbon payloads sitting in
			// the folder this pattern never looked at.
			wchar_t pat[MAX_PATH];
			swprintf_s(pat, L"%sz_SC4UIScale_ZCarbon*", OverrideDirPtr());
			WIN32_FIND_DATAW cfd = {};
			HANDLE ch = FindFirstFileW(pat, &cfd);
			if (ch == INVALID_HANDLE_VALUE)
			{
				Logger::Get().WriteLine(
					LogLevel::Info,
					"ScaleTier: Scoty Carbon Skin is installed but NO carbon "
					"packages are present. The skin wins the load order on "
					"~473 UI resources, so at any scale factor its 1x art and "
					"1x dialog layouts draw inside scaled cells. Build them "
					"from your own copy of the skin - see CARBON-COMPAT.md in "
					"tools\\research\\carbon of the source repo.");
			}
			else
			{
				FindClose(ch);
			}
		}

		// sizeof(gArmedDepOk) would over-READ depOk, which has exactly
		// kThirdPartyDepCount entries. Copy the real count and let the
		// compiler prove the buffer is big enough.
		static_assert(kThirdPartyDepCount <= 32,
			"gArmedDepOk is too small for the dependency table");
		memcpy(gArmedDepOk, depOk, sizeof(bool) * kThirdPartyDepCount);
		gArmedDepOkValid = true;

		const wchar_t* activeTag = nullptr;
		for (int i = 0; i < kPackageCount; i++)
		{
			const Package& pkg = kPackages[i];
			const bool match =
				factor >= pkg.factor - 0.01f && factor <= pkg.factor + 0.01f;
			if (match)
			{
				activeTag = pkg.tag;
				wcscpy_s(gArmedTag, 8, pkg.tag);   // v4.5.0, for exclusion
				gArmedTagValid = true;
			}
			// SelectiveArt is an ORDINARY package again (v4.5.0). It was
			// lifted out of this loop in v4.0.3 to pilot the stable-filename
			// content swap that every package now uses, so the special case
			// it existed for no longer exists - and leaving it would be a
			// second arming mechanism, which is the defect that broke the 3x
			// UI this morning.
			SyncDat(docPlugins, L"z_SC4UIScale_SelectiveArt", pkg.tag, match);
			SyncDat(docPlugins, L"z_SC4UIScale_DialogStatic", pkg.tag, match);
			SyncDat(docPlugins, L"z_SC4UIScale_ItemIcons", pkg.tag, match);
			// SUBFOLDER package (v2.17.1): overrides for icons that live in
			// OTHER Documents-plugin subfolders (the submenus mod's 55). LOAD
			// ORDER LAW (proven 2026-07-29): root Plugins FILES load BEFORE
			// subfolders, so a root dat can NEVER override a subfolder dat -
			// such overrides must sit in a folder sorting after the target
			// ("zzz-SC4UIScale" beats "150-mods").
			SyncDat(pluginsRoot, L"zzz-SC4UIScale\\z_SC4UIScale_ItemIconsSub",
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
			// THIRD TIME THIS SHAPE HAS SHIPPED. #119 was WarriorUI missing
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
			SyncDat(pluginsRoot, L"zzz-SC4UIScale\\z_SC4UIScale_CsiIcons",
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
			SyncDat(pluginsRoot, L"zzz-SC4UIScale\\z_SC4UIScale_UncoveredIcons",
				pkg.tag, match);
			// SUBFOLDER package (v2.38.0, task #79c): 2x copies of the two
			// in-city quit/exit confirm scripts, built from the save-warning
			// MOD's versions because that mod replaces them from 150-mods\ and
			// beats our root DialogStatic package. Gated on that mod: with it
			// gone, this turns off and our root stock-derived copy - which
			// then wins over SimCity_1.dat - scales the stock dialog instead.
			SyncDat(pluginsRoot, L"zzz-SC4UIScale\\z_SC4UIScale_SaveWarningUI",
				pkg.tag, match && DepOkByName(
					L"zzz-SC4UIScale\\z_SC4UIScale_SaveWarningUI", depOk));
			// SUBFOLDER package (v2.38.3): 2x copies of the SIX dialog-static
			// targets CAM replaces, built from CAM's own scripts. Gated on CAM
			// being installed and unchanged - with CAM gone this turns off and
			// our root stock-derived copies take over, which is the correct
			// unmodded behaviour.
			SyncDat(pluginsRoot, L"zzz-SC4UIScale\\z_SC4UIScale_CamUI",
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
			SyncDat(pluginsRoot, L"zzz-SC4UIScale\\z_SC4UIScale_ThirdPartyUI",
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
			SyncDat(pluginsRoot, L"zzz-SC4UIScale\\z_SC4UIScale_WarriorUI",
				pkg.tag, match && DepOkByName(
					L"zzz-SC4UIScale\\z_SC4UIScale_WarriorUI", depOk));
			// SUBFOLDER package (#139, 2026-08-05): 2x/1.5x/3x copies of NAM's
			// OWN 381 ItemIcon strips. It MUST live in zzz-SC4UIScale\ and not
			// the root ItemIcons dat: root Plugins FILES load before
			// SUBFOLDERS (the load-order law above), and NAM is a subfolder
			// (770-network-addon-mod\), so a root override could never win.
			// "zzz-" sorts after "770-", so this one does.
			SyncDat(pluginsRoot, L"zzz-SC4UIScale\\z_SC4UIScale_NamIcons",
				pkg.tag, match && DepOkByName(
					L"zzz-SC4UIScale\\z_SC4UIScale_NamIcons", depOk));
			// WebButtonUI (2026-08-21): cyclone-boom Web Button Improvement
			// Mod's web-button bitmap, per tier, gated on the mod - without this
			// SyncDat the tiers stay in whatever state they were deployed and
			// 2x art crops/stretches at every other factor.
			SyncDat(pluginsRoot, L"zzz-SC4UIScale\\z_SC4UIScale_WebButtonUI",
				pkg.tag, match && DepOkByName(
					L"zzz-SC4UIScale\\z_SC4UIScale_WebButtonUI", depOk));
			// ---- Scoty Carbon Skin packages (v4.3.0) -----------------------
			// One call per kThirdPartyDeps Carbon row - a dep row without its
			// SyncDat call is silently inert (#119, WarriorUI, recorded just
			// above). All eight arm only with the skin present and unchanged;
			// with it gone or updated they turn off and our stock-derived
			// packages take over.
			SyncDat(pluginsRoot, L"zzz-SC4UIScale\\z_SC4UIScale_ZCarbonUI",
				pkg.tag, match && DepOkByName(
					L"zzz-SC4UIScale\\z_SC4UIScale_ZCarbonUI", depOk));
			SyncDat(pluginsRoot, L"zzz-SC4UIScale\\z_SC4UIScale_ZCarbonArt",
				pkg.tag, match && DepOkByName(
					L"zzz-SC4UIScale\\z_SC4UIScale_ZCarbonArt", depOk));
			SyncDat(pluginsRoot, L"zzz-SC4UIScale\\z_SC4UIScale_ZCarbonIcons",
				pkg.tag, match && DepOkByName(
					L"zzz-SC4UIScale\\z_SC4UIScale_ZCarbonIcons", depOk));
			SyncDat(pluginsRoot,
				L"zzz-SC4UIScale\\z_SC4UIScale_ZCarbonSaveWarning",
				pkg.tag, match && DepOkByName(
					L"zzz-SC4UIScale\\z_SC4UIScale_ZCarbonSaveWarning", depOk));
			SyncDat(pluginsRoot, L"zzz-SC4UIScale\\z_SC4UIScale_ZCarbonCamUI",
				pkg.tag, match && DepOkByName(
					L"zzz-SC4UIScale\\z_SC4UIScale_ZCarbonCamUI", depOk));
			SyncDat(pluginsRoot, L"zzz-SC4UIScale\\z_SC4UIScale_ZCarbonStyles",
				pkg.tag, match && DepOkByName(
					L"zzz-SC4UIScale\\z_SC4UIScale_ZCarbonStyles", depOk));
			SyncDat(pluginsRoot, L"zzz-SC4UIScale\\z_SC4UIScale_ZCarbonNam",
				pkg.tag, match && DepOkByName(
					L"zzz-SC4UIScale\\z_SC4UIScale_ZCarbonNam", depOk));
			SyncDat(pluginsRoot, L"zzz-SC4UIScale\\z_SC4UIScale_ZCarbonGodMod",
				pkg.tag, match && DepOkByName(
					L"zzz-SC4UIScale\\z_SC4UIScale_ZCarbonGodMod", depOk));
		}
		// Install root FIRST (the copy the game reads); Documents mirror
		// second (kept for inspectability + package consistency).
		SyncFont(docPlugins, instPlugins, activeTag);
		SyncFont(docPlugins, docPlugins, activeTag);

		// Everything above only RECORDED what it wants. This is the one
		// pass that touches disk, and it runs after the last SyncDat of
		// the boot so a package that never received an active call can be
		// told apart from one whose tier simply came up later in the loop.
		CommitArming();
	}

	// ============ FONTSTYLE.INI SHUTDOWN REVERT (v4.0.4) ===================
	// USER-CONFIRMED REAL DAMAGE, not a hypothetical: an sc4pac uninstall
	// removes the DLL but leaves FontStyle.ini behind - confirmed directly by
	// the sc4pac developer ("the DLL goes and the .ini stay ... sc4pac
	// wouldn't uninstall INI files, as those contain settings that have been
	// manually configured by the user"). With the DLL gone, stock SC4 reads
	// whatever FontStyle.ini says - which, at the moment of uninstall, is
	// still whichever tier's font table SyncFont copied onto it. The player
	// is left with scaled text over a stock, unscaled UI: exactly the
	// "font/geometry disagree" half-state BootState exists to prevent for
	// OUR OWN runtime, except here there is no runtime left to prevent it.
	//
	// THE PROPOSED FIX WAS "CHECK ON THE NEXT LAUNCH" AND IT CANNOT WORK: if
	// the DLL is gone, nothing of ours runs to perform any check. The only
	// code that can still act is code that runs WHILE THE DLL IS STILL
	// INSTALLED - i.e., at shutdown, on THIS session, before the player ever
	// gets to an uninstall. sc4pac can only uninstall with the game closed
	// (it holds these files open while running, same as every other write
	// this DLL ever does), so a clean shutdown always precedes any uninstall
	// that follows it.
	//
	// REUSES SyncFont'S OWN STOCK-TIER PATH, ZERO NEW LOGIC: activeTag=null
	// already means "restore the player's real .user-original if we have
	// one, else move the live file aside to .x1-disabled" - the exact same
	// call every 1x selection already makes, proven by every 1x session this
	// project has ever run. Moving it aside (not deleting it, not writing an
	// empty stub) means FontStyle.ini simply DOES NOT EXIST after a clean
	// shutdown - so even sc4pac's own "leave .ini files alone" policy has
	// nothing under that exact name to leave behind. The .x1-disabled
	// leftover, if sc4pac's subfolder-wholesale-delete does not reach it
	// (root, not a subfolder - the modmaker's other uninstall category), is
	// inert clutter with a non-standard extension nothing ever reads - never
	// a broken-looking UI again.
	//
	// COST AT SHUTDOWN: two FileExists checks and at most one CopyFileW or
	// MoveFileExW of a 23KB file - the same order of cost SyncFont already
	// pays at every boot without incident. Deliberately NOT given its own
	// numbered SHUTDOWN n/4 probe line in the director's shutdown trace:
	// this call sits in the DIRECTOR's shutdown sequence, which already logs
	// immediately before and after it, so a hang here is diagnosable the
	// same way every other shutdown stage already is.
	void RevertFontOnShutdown()
	{
		wchar_t docPlugins[MAX_PATH];
		// v4.2.0: packages+fonts live in 010-SC4UIScale\, the DLL at root.
		OurPackagesDir(docPlugins, MAX_PATH);
		wchar_t instPlugins[MAX_PATH];
		InstallPluginsDir(instPlugins, MAX_PATH);
		SyncFont(docPlugins, instPlugins, nullptr);
		SyncFont(docPlugins, docPlugins, nullptr);
	}
}

