#pragma once

// Dynamic resolution-tier decision + static-layer package management.
//
// The runtime scaler adapts per boot, but the ART dat, the static DIALOG
// dat, and FontStyle.ini are files the game loads blindly - at stock
// resolutions they would wreck the UI (2x fonts in 1x frames, dialogs
// larger than the screen). The DLL therefore decides the tier BEFORE the
// game loads data and arms exactly one factor's package set, so ANY
// resolution - including ones never directly tested - gets a provably
// fitting factor from the same geometry math.
//
// HOW "ARM" WORKS, v4.5.0 - A CONTENT SWAP AT A STABLE FILENAME.
// Through v4.4.0 arming was a RENAME: the winning tier's dat kept its
// `<base><tag>.dat` name and the losers were pushed aside as
// `<base><tag>.dat.x1-disabled`. That is the single reason a package manager
// cannot uninstall this mod - sc4pac removes files BY MANIFEST NAME, and 53
// of 68 installed files sat under a renamed name. From v4.5.0:
//
//   LIVE     z_SC4UIScale_<Pkg>.dat          the only thing SC4 loads. Its
//                                            CONTENT changes; the NAME never
//                                            does - not at any tier, not
//                                            under any gate verdict, ever.
//   PAYLOAD  z_SC4UIScale_<Pkg>.<tag>.uipay  inert. Never renamed, never
//                                            loaded. tag = 15x/2x/3x/1x/on/off.
//                                            Inert by EXTENSION, measured:
//                                            probe #202 put a real DBPF at
//                                            `.uipay` and it was absent from
//                                            the registered-segment census
//                                            while 13 of our live .dat files
//                                            were present in the same census.
//   STATE    z_SC4UIScale_STATE.txt          written into each of our folders
//                                            every boot by WriteArmState. TSV
//                                            after two `#` lines: base, tag,
//                                            reason, paySize, payTime,
//                                            liveSize, liveTime.
//
// ⛔ A DIRECTORY LISTING NO LONGER CARRIES THE ARMED TIER OR THE GATE VERDICT.
// Every live filename is a constant, and a gated-off package is that same
// file holding the `.off` payload's bytes. STATE.txt is the ONLY place either
// answer now exists - every script and every human diagnosis reads it, and a
// check that infers "live" from a `.dat` existing is measuring nothing.
// See ScaleTier.cpp: ArmOne / CommitArming / WriteArmState, and
// MigrateRenamesToPayloads for the in-place upgrade from the rename layout.
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

	// Write a starter SC4UIScale.ini at the Plugins root when none exists.
	// Returns true if it wrote one. MUST run before Settings::Load: the two
	// keys that switch this mod on default to OFF in the code, so a fresh
	// install with no ini is silently inert.
	bool SeedIniIfAbsent();
	// Why the last SeedIniIfAbsent returned false, when that false means
	// FAILURE (nullptr when the ini simply already existed). Read AFTER
	// Logger::Init: seeding runs before any log sink exists, and a silent
	// seed failure is an inert mod with an empty log - the exact fresh-
	// install symptom the seeder was built to eliminate.
	const char* SeedIniFailure(unsigned long* lastError);
	const char* MigratedRootFileNames();

	// v4.5.0: prints which folders this mod actually resolved to, and
	// whether either half fell back to the hard-coded v4.2.0 name. Call once
	// AFTER Logger::Init - discovery itself is silent because the ini and
	// log paths resolve through it before the logger exists.
	void LogOurDirs();

	// #201 PROBE (log-only, [Probe] SegmentCensus, default 0). Walks the
	// registered DBPF segments and prints a path each. It never unregisters
	// anything.
	//
	// It was built to ask whether a LOADED dat can be dropped at runtime -
	// which would have let this mod stop renaming its own files to arm a tier.
	// That is not the route that worked. #202 reused this same census the
	// other way round, as the instrument for a PRE-scan question: a real DBPF
	// copied to `.uipay` never appeared here, while 13 of our live `.dat`
	// files did in the same run - the positive control proving the census
	// could have seen it. That measurement is what the v4.5.0 payload layout
	// rests on, so this probe stays: it is how the `.uipay` claim gets
	// re-checked against a future patch.
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

	// Record which package each tier wants (SyncDat), for CommitArming to
	// apply in one pass. v4.5.0: this no longer renames anything - it swaps
	// the CONTENT of each package's stable `.dat` name in from the matching
	// `.<tag>.uipay` payload, and a package with no tier match commits `.off`.
	// PLUGINS-ONLY: all managed files - both dats and FontStyle.ini - live in
	// this mod's own Plugins subfolders; nothing in the game install directory
	// (portable, no Program Files writes). Idempotent, and free in the steady
	// state (four file stats, no I/O, when the stamp still matches); a failed
	// swap fails INERT and self-heals on the next boot.
	void SyncStaticLayers(float factor);

	// Arm or silence z_SC4UIScale_SelectorUI - the stock-tier scale selector,
	// the ONE package gated on the ABSENCE of a tier. Its payload tags are
	// `on` / `off` rather than tier tags, for that reason.
	//
	// CALL THIS UNCONDITIONALLY. It must NOT be folded into
	// SyncStaticLayers: that function is not called at the stock tier, which
	// is the only state this package is for, so folding it in makes it
	// unreachable exactly when it is needed (measured 2026-08-19 - under the
	// pre-4.5.0 rename layout the dat sat .x1-disabled on a 1x machine while
	// the DLL reported the selector live; the v4.5.0 shape of that same fault
	// is a live `.dat` holding `.off` bytes, which a listing cannot show).
	void SyncSelectorPackage(bool stockTier);

	// THE ONE PASS THAT TOUCHES DISK. The DIRECTOR calls this after the LAST
	// SyncDat/SyncSelectorPackage record of each boot path. It must never be
	// welded into a recorder: v4.5.1 had it on SyncStaticLayers' tail, so
	// the selector want recorded after that call was silently discarded on
	// every boot (4th occurrence of the neighbour-gate shape). Idempotent
	// and cheap when re-run (steady state is four file stats per package).
	void CommitArming();

	// cyclone-boom "Web Button Improvement Mod" detection, BOTH plugin roots
	// (the Documents tree passed in, plus <install>\Plugins). THE only
	// detector: WebRedirect.cpp used to carry a one-root twin, and the two
	// disagreed whenever the mod sat in the install root - WebText stood
	// down while the ShellExecute redirect stayed armed.
	bool WebButtonModPresent(const wchar_t* pluginsDir);

	// TRUE when a SCALED art package was actually selected for this boot -
	// i.e. SyncStaticLayers matched the running factor to a kPackages row and
	// armed that tier's dats. This is the gate for any patch whose
	// correctness depends on OUR ENLARGED ART BEING THE ART IN PLAY, and it
	// is deliberately NOT `spikeScaleAll` or `spikeScaleFactor`: with the
	// packages stashed (stock compare, a failed arm, ScaleAll=0) the game
	// reads STOCK art at stock size, and a patch that assumes enlarged art
	// would then be wrong in the opposite direction - manufacturing a defect
	// out of a cure. Reads the same stashed decision the exclusion pass uses,
	// so the two can never disagree about which art is live.
	bool ScaledArtArmed();

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
