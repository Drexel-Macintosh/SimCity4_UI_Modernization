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

	// The fit predicate ALONE, without the "is it installed" and
	// "largest first" parts of Decide. Published so the in-game scale
	// selector can grey out a factor this resolution cannot carry, using the
	// SAME arithmetic that would refuse it at boot rather than a second copy
	// of the thresholds. Two copies of a rule are two rules, and this one is
	// about to be shown to the player as a promise.
	bool Fits(float factor, int width, int height);

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
	// ⛔ CALL THIS UNCONDITIONALLY. It must NOT be folded into
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
	// manual-tier mode SKIPPED AT THE TIME (⚠ since v3.0.2/#182 manual tiers
	// with ScaleAll=1 sync too), so AutoScale=0 silently disabled the whole
	// uncovered-icon cure.
	void ScanUncoveredIcons(float factor);

	void EnlargeUncoveredIcons(float factor);
}
