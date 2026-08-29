#pragma once

// Dynamic resolution-tier decision + static-layer package management.
//
// The runtime scaler adapts per boot, but the ART dat, the static DIALOG
// dat, and FontStyle.ini are files the game loads blindly - at stock
// resolutions they would wreck the UI (2x fonts in 1x frames, dialogs
// larger than the screen). The DLL therefore decides the tier BEFORE the
// game loads data and enables exactly one factor's package (stashing all
// others), so ANY resolution - including ones never directly tested -
// gets a provably fitting factor from the same geometry math.
namespace ScaleTier
{
	// The largest INSTALLED package factor N satisfying the fit function:
	//   880*N <= width    (widest UI piece: city composite, design px)
	//   558*N <= height   (tallest UI piece: Graphics dialog, design px)
	//   N <= min(width/800, height/600)   (density cap: 800x600-feel max)
	// Falls back to 1.0 (stock, scaling dormant) when nothing fits.
	float Decide(int width, int height);

	// v4.2.0 (subfolder move): the Documents PLUGINS ROOT - walks up from
	// the DLL's folder (which now lives in Plugins\010-SC4UIScale\) to the
	// nearest ancestor named "Plugins", at most 2 levels; falls back to the
	// DLL's own folder with a one-shot log line. Every consumer that hunts
	// OTHER mods' files (dependency gates, SC4GraphicsOptions.ini, icon
	// scans) MUST use this, never the DLL sibling path.
	void GetPluginsRootW(wchar_t* out, size_t outLen);

	// v4.4.0 ROOT CLEANUP: names a file inside Plugins/010-SC4UIScale/.
	// The DLL is the only thing this mod leaves at the Plugins root (the
	// game's DLL loader is top-level only, measured); the ini, log, gcap
	// and #104 csv all resolve through here so an sc4pac uninstall that
	// removes the folder removes them with it. Resolves WITHOUT logging -
	// the ini and log paths are needed before Logger::Init exists.
	void GetOurFilePathW(const wchar_t* name, wchar_t* out, size_t outLen);
	void GetOurFilePathA(const char* name, char* out, size_t outLen);

	// One-time move of the pre-v4.4.0 loose root files into that folder.
	// MUST be called before Settings::Load and before Logger::Init - a read
	// that beats the migration silently falls back to defaults. Returns how
	// many files moved; MigratedRootFileNames() names them for the log line
	// the director prints once the logger is up.
	int MigrateRootLooseFiles();
	const char* MigratedRootFileNames();

	// v4.5.0: prints which folders this mod actually resolved to, and
	// whether either half fell back to the hard-coded v4.2.0 name. Call once
	// AFTER Logger::Init - discovery itself is silent because the ini and
	// log paths resolve through it before the logger exists.
	void LogOurDirs();

	// #201 PROBE (log-only, [Probe] SegmentCensus, default 0). Walks the
	// registered DBPF segments and prints a path each. Exists to answer ONE
	// question: whether a loaded dat can be dropped at runtime, which would
	// let this mod stop renaming its own files to arm a tier. It never
	// unregisters anything.
	void SegmentCensus();


	// The fit predicate ALONE, without the "is it installed" and
	// "largest first" parts of Decide. Published so the in-game scale
	// selector can grey out a factor this resolution cannot carry, using the
	// SAME arithmetic that would refuse it at boot rather than a second copy
	// of the thresholds. Two copies of a rule are two rules, and this one is
	// about to be shown to the player as a promise.
	bool Fits(float factor, int width, int height);

	// Is this factor one of the tiers the package table knows about?
	bool KnownFactor(float factor);

	// The explicit minimum resolution this tier needs, for the in-game
	// selector's "needs WxH" caption. PUBLISHED so the number shown to the
	// player is READ FROM the table the boot path enforces, never a second
	// copy of the arithmetic - the player is being made a promise here.
	bool TierMinimum(float factor, int* outW, int* outH);

	// KnownFactor AND that tier's art actually on disk. PUBLISHED because the
	// MANUAL path never asked the disk: PackageInstalled had exactly one
	// caller (Decide), which is why every "factor with no art" failure mode
	// exists. kPackages even carries a 4.0 row no package was ever built for.
	bool PackageAvailable(float factor);

	// THE BOOT-STATE VALIDATOR (2026-08-19: "run a check for
	// resolution and scale combination correct, and if it flags false flip it
	// back to auto, automatically").
	//
	// One function, one call site, run BEFORE the tier is applied. Answers
	// "is [AutoScale, ScaleFactor, ScaleAll, packages, resolution] coherent?",
	// repairs it if not, writes the repair back where writing is safe, and
	// tells the caller a repair happened so the static-layer sync cannot then
	// be skipped.
	//
	// Deliberately takes PRIMITIVES, not Settings: ScaleTier does not know
	// about the settings struct today and this must not be the change that
	// couples them.
	struct BootState
	{
		bool  autoScale;         // in/out
		float factor;            // in/out
		bool  scaleAll;          // in ONLY - never written, never mutated
		int   renderW, renderH;  // in - 0/0 means UNMEASURED, not small
	};

	// true  = coherent as read; nothing changed, nothing written.
	// false = REPAIRED; autoScale/factor now hold what will actually run.
	bool ValidateBootState(BootState& st, const wchar_t* iniPath);

	// Enable the package matching `factor` and stash every other installed
	// package (suffix ".x1-disabled"). PLUGINS-ONLY: all managed files -
	// both dats and FontStyle.ini - live beside the DLL in the Documents
	// SimCity 4 Plugins folder; nothing in the game install directory
	// (portable, no Program Files writes). Idempotent; a failed rename
	// self-heals on the next boot.
	void SyncStaticLayers(float factor);

	// Arm or stash z_SC4UIScale_SelectorUI-1x - the stock-tier scale selector,
	// the ONE package gated on the ABSENCE of a tier.
	//
	// CALL THIS UNCONDITIONALLY. It must NOT be folded into
	// SyncStaticLayers: that function is not called at the stock tier, which
	// is the only state this package is for, so folding it in makes it
	// unreachable exactly when it is needed (measured 2026-08-19 - the dat sat
	// .x1-disabled on a 1x machine while the DLL reported the selector live).
	void SyncSelectorPackage(bool stockTier);

	// #149 stage 2. SyncStaticLayers runs before the game opens a single dat,
	// so it can only NAME the icons no package of ours enlarges. This runs at
	// PostAppInit - dats indexed, no menu built yet - and registers a
	// correctly-sized twin for each of them with the resource manager, so the
	// art is BORN CORRECT for every consumer instead of being patched at the
	// blit (which is reactive and provably loses to anything already buffered:
	// feedback-sc4-reactive-sweep-flashes).
	//
	// Touches ONLY instances the scan proved uncovered; a covered icon is
	// never fetched, never re-registered, never resampled. Any failure leaves
	// the game's own registration untouched.
	// #149 stage 1. Names the third-party ItemIcons no package of ours covers.
	// MUST be called on EVERY path that ends with a factor > 1, not only the
	// AutoScale one - it was originally folded into SyncStaticLayers, which
	// manual-tier mode SKIPPED AT THE TIME (since v3.0.2/#182 manual tiers
	// with ScaleAll=1 sync too), so AutoScale=0 silently disabled the whole
	// uncovered-icon cure.
	void ScanUncoveredIcons(float factor);

	void EnlargeUncoveredIcons(float factor);

	// USER-CONFIRMED, real damage: an sc4pac uninstall removes the DLL but
	// leaves FontStyle.ini behind (sc4pac does not uninstall .ini files, to
	// protect user-configured settings) - so stock SC4 then reads whichever
	// tier's font table was live at the moment of uninstall, over an
	// otherwise fully stock UI. Call this from the director's shutdown path,
	// while the DLL is still installed - it is the only code that ever CAN
	// act, since nothing of ours runs after uninstall to check anything.
	// Reuses SyncFont's own stock-tier revert; see its call site's comment.
	void RevertFontOnShutdown();
}
