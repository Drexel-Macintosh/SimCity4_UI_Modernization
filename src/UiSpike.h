#pragma once

#include "Settings.h"

#include <map>

// Research spike toward the UI-scaling northstar (game at native resolution,
// UI elements drawn larger). Dumps the live cIGZWin tree and optionally
// resizes one window to observe art/layout/hit-test behavior. Ini-driven.
class UiSpike
{
public:
	static void SetRenderResForReadout(int32_t w, int32_t h);   // #192
	// True when the wrapper renders at the monitor's mode and the game's own
	// WindowWidth/Height are ignored - i.e. the four stock resolution rows in
	// Graphic Options do nothing at all. Set by the director, which is the
	// one place that works this out.
	static void SetRequestedResIgnored(bool ignored);
	static void SetTierMirror(float f);   // resolved tier -> hook-visible mirror
	// IN-GAME SCALE SELECTOR (2026-08-19, user request). Fills the readout,
	// pushes the radio/combo state, and services the click filter on the
	// Graphic Options dialog.
	//
	// DRIVEN DIRECTLY FROM THE TIMER, not from IncrementalPass, and that is
	// the whole point: IncrementalPass needs a city view and `continuous`,
	// neither of which exists at the stock tier or on the main menu - and the
	// stock tier is exactly where the player needs a way back UP. Cheap by
	// construction: throttled internally, one id lookup per service.
	void ServiceScaleSelector();
	// Freeze instrument: writes the PerfProbe bucket table to the log. The
	// selector calls it on dialog close; the director at shutdown, so a
	// session where the dialog never closes cleanly still reports.
	void DumpSelectorPerf(const char* why);
	// Kicks the display-mode enumeration onto a background thread at DLL
	// load, so the first Graphic Options open finds the cache already warm
	// (v3.13.2 measured the enumeration at 3.3s, all on the first click).
	void WarmSelectorCaches();
	// v2.32.0 SHOWHOOK (task #50): scale a subtree at the instant the game
	// makes it visible, BEFORE its first paint. PUBLIC because the SetFlag
	// detour is a free function in the GAME's call stack.
	void ScaleOnShow(class cIGZWin* win);
	void InstallShowHook();
	// v2.34.0 task #50: trampoline the sub-flyout layout setter so the nested
	// menus are BORN at f (their paint buffer is then allocated correct on
	// Plot #1 - the flash is the buffer, not the sweep).
	void InstallSubFlyoutBorn();
	// v2.36.0 task #50: scale the nested sub-flyout at CONSTRUCTION (a detour
	// on its Place), so its first paint is already correct instead of one
	// sweep tick late. DrainBornScaleRecords hands those windows to scaleMap
	// as AlreadyScaled so the sweep cannot scale them a second time.
	void InstallSubFlyoutBornScale();
	void DrainBornScaleRecords();
	// v2.36.2: the SUBHOOK/SUBCLAIM install performed AT BIRTH. Same ops, same
	// crash guard, same order as the sweep's - the container thunks MUST go in
	// before the [0xE0] promotion (dual-use field; see the note at the body).
	void InstallSubFlyoutHooksNow(class cIGZWin* sub, class cIGZWin* strip);
	// v2.36.4 tasks #59/#60: name the screen-edge border window, and settle
	// whether the U-Drive-It map marker is a cIGZWin at all. [Probe] EdgeDump.
	void EdgeProbeTick(class cIGZWin* pView);
	// v2.36.8 task #59: full-depth visibility-change trace from the MAIN
	// window. Prints only windows whose vis flipped, so pausing names the
	// border whatever its depth or owner. [Probe] VisTrace.
	void VisTraceTick();
	// v2.36.1 task #50: the FIRST-LEVEL tool flyouts (Zones / Transportation /
	// Utilities / Civic / Landscape ...) are created fresh on every open and
	// were scaled+docked by the next sweep tick - one 1x frame, which is the
	// jump still visible after that fix. All seven open sites funnel
	// through one function; the hook runs the EXISTING pass at that instant.
	void InstallFlyoutOpenHook();
	void OnFlyoutOpened(uint32_t flyoutId);

	explicit UiSpike(const Settings& settings);

	// Deferred execution: running the tree walk inside the PostCityInit
	// message hangs the game (proven), so the director ARMS the spike at
	// city init and the input handler's timer FIRES it once, several
	// seconds later, when the game is idle and stable.
	void ArmDeferred(unsigned int fireAtTickMs);
	void Disarm();
	// Full forget: APP shutdown only, never between cities (clearing between
	// cities is exactly the double-scale hazard - see scaleMap below).
	void ResetTracking();
	// #132: true while the region screen is up and stable.
	bool IsRegionUp() const { return regionActive; }
	// #132: one wheel notch of region zoom (+1 in, -1 out).
	void RegionZoomStep(int dir);
	// #132 live region zoom factor; 0 = not yet initialised from the tier.
	float regionZoom = 0.0f;          // live factor
	int regionZoomTarget = 0;         // level, -Levels..+Levels
	int regionZoomLastApplied = 0;    // the level actually on screen
	bool regionZoomPending = false;   // a notch arrived; apply once it settles
	bool regionZoomAtLimitLogged = false;
	unsigned int regionZoomLastStepMs = 0;
	// A rebuild is 8-10 full-image passes PER ITEM. Applying one per notch is
	// what froze the game on a fast scroll, so a burst collapses into a single
	// rebuild once the wheel has been quiet this long.
	static const unsigned int kRegionZoomSettleMs = 120;
	// Rebuilds every item at the new absolute factor via the game's own
	// sub_7AE510. Needs the region screen, which the caller already holds.
	void ApplyPendingRegionZoom(cIGZWin* pRegion, unsigned int nowTickMs);
	void TickCheck(unsigned int nowTickMs);

	// v2.41.10 (task #89): ask the dock minimap to re-bake AT PostCityInit -
	// two byte writes + InvalidateSelf, no walk. Gated by [Spike] EarlyBake.
	// See the long note at the definition before touching it: this is the one
	// thing we run inside the region that carries the hang lesson.
	void EarlyMinimapBake();

	// v2.41.17 (task #89): called from the cGZWin::SetFlag detour - the game's
	// own stack, and it keeps firing AFTER city init returns. Scales the dock
	// once its subtree stops changing, so it is never painted at 1x. Gated by
	// [Spike] EarlyDock (1 = log only, the shipping default).
	void EarlyDockTick();

	// v2.41.19: the dock minimap's destroy+recreate (the v2.21.1 crash site),
	// extracted verbatim from the sweep so EarlyDockTick can run the SAME code.
	// All gates live inside; safe to call from both, idempotent by the latch.
	void TryRecreateMinimapSurface(class cIGZWin* pDock);
	// #127: table-driven panel-to-panel docking (kPanelDock). Called from
	// BOTH the full city sweep and the incremental pass - a user-opened
	// panel is absent at load time. Idempotent; no-op below f=1.4
	// (#137: was 2.5, which meant 2x never got docked at all).
	// fromShow: called from the SetFlag show detour, where the window's
	// visible bit is not set yet - gate on geometry, not the flag (#137c).
	void ApplyPanelDocks(class cIGZWin* pRoot, float f, bool fromShow = false);
	// v2.72.1 (#109, the FAMILY): enforce window == surface on any
	// cSC4WinMiniMap instance by snapping its window to the largest exact
	// power-of-two multiple of terrainDim within the bake ceiling. All three
	// instances (Data Views map, HUD dock minimap, U-Drive-It twin) carry the
	// mismatch at non-power-of-two tiers; fixing one and not its siblings is
	// how the family rots. Returns the snapped edge, or 0 if not needed.
	int SnapMiniMapToBake(class cIGZWin* pMap, const char* who);

	// ⛔ THE FIRST PASS CANNOT BE MADE EARLIER THROUGH THE MESSAGE QUEUE.
	// Measured and reverted 2026-08-01 (task #89): a posted WM_APP message
	// arrived +2016ms after arm versus the timer's +2031ms - 15ms, one timer
	// period. The game does not pump messages at all during the city load
	// tail. WM_TIMER cadence, ShowHook and WM_APP all die on that same fact.
	// The cure for load-time damage is DATA (kDataScaledSubtreeIds), exactly
	// as the advisor faces taught in task #43.

private:
	// Per-window scale bookkeeping, keyed by cIGZWin pointer. The record
	// makes scaling IDEMPOTENT: a window is scaled at most once per
	// lifetime, re-running ScaleAll after a city reload is harmless, and a
	// recreated window at a REUSED address is detected by ID/size mismatch.
	struct ScaleRecord
	{
		uint32_t id;      // GetID() at scale time (address-reuse detector)
		int32_t origW;    // pre-scale size (recreated-at-design-size detector)
		int32_t origH;
		int32_t scaledW;  // post-scale size (already-scaled detector)
		int32_t scaledH;
		uint8_t resetRescales; // tug-of-war counter (game resets, we re-scale)
		bool leaveAlone;  // tombstone: game-managed geometry or guard-refused;
		                  // never mutate this window again
		int32_t origL = 0; // pre-scale position: re-scales after a game reset
		int32_t origT = 0; // anchor from HERE, never from the current (already
		                   // moved) position - otherwise every reset compounds
		                   // the move (the Load Region dialog walked across the
		                   // screen: 342 -> 684 -> 1368)
		bool hasOrigPos = false;
	};
	enum class ScaleState
	{
		Fresh,            // never seen (or stale record evicted): scale it
		AlreadyScaled,    // current size matches the record: skip mutation
		ResetToOriginal,  // back at recorded pre-scale size: re-scale
		Unrecognized      // known window, unexpected size (game resized it):
		                  // leave alone - fail toward under-scaling
	};
	ScaleState Classify(class cIGZWin* win);
	// v2.66.0 (#113): store a fresh scale record WITHOUT wiping the
	// tug-of-war counter. Classify() increments `resetRescales` through a
	// reference into the map and tombstones at >3 - but every re-scale site
	// then assigned a brand-new record with the counter reset to 0, so the
	// counter could never exceed 1 and the tombstone was UNREACHABLE.
	// Measured in a live 12-minute session: 8,586 "[re-scaled after reset]"
	// events, 0 tombstones. Use this instead of `scaleMap[win] = rec;` on
	// every RE-SCALE path. Tombstone writes may assign directly - they set
	// leaveAlone, so the counter is moot.
	void StoreScaleRecord(void* win, ScaleRecord rec);

	// #94 v2.47.0: is this window's rect still in DESIGN units (never scaled
	// by us), or already in SCREEN units? A PURE READ of scaleMap - never
	// Classify(), which mutates the tug-of-war counter and can tombstone a
	// window just for being asked. Used by the flyout docks, where reading an
	// invisible alignment marker's raw L/T as if it were screen units put the
	// Landscape ring 59px low, on the wrong button.
	bool MarkerIsDesignUnits(class cIGZWin* win, float f);

	void Run();
	void PurgeSubtreeRecords(class cIGZWin* win, int depth);
	void DumpTree(class cIGZWin* win, int depth, int* totalCount);
	void LiveViewDump(); // diagnostic: dump visible transient panels live
	                     // (captures an open query/tool panel). Gated by
	                     // settings.spikeLiveDumpMs.
	void LiveDumpChildren(class cIGZWin* parent, uint32_t skipId, const char* tag);
	void ScaleTarget(class cIGZWin* pMainWindow);
	// pAbsL/pAbsT: the PARENT's absolute DESIGN origin (#161). Edge-derived
	// rounding makes a scaled size depend on position, so a child's local
	// coordinates must be rounded in the same frame the parent's extent was,
	// or the child's edge misses the parent's by a pixel at fractional tiers.
	// Defaults of 0 reproduce the old math exactly: ScaleRound(0+t) -
	// ScaleRound(0) == ScaleRound(t), so untouched callers are a no-op.
	void ScaleSubtree(class cIGZWin* win, float factor, int depth, int* count,
		bool centerLeaves = false, int32_t pAbsL = 0, int32_t pAbsT = 0);
	void ScaleAllPanels(class cIGZWin* pMainWindow);

	void IncrementalPass();
	int ScalePanelsUnder(class cIGZWin* pRoot, const char* rootTag);
	void ScaleGodFlyouts(class cIGZWin* pView, float f);
	int ScalePanelRoot(class cIGZWin* win, int32_t frameW, int32_t frameH, float f);
	void RegionWatchTick(unsigned int nowTickMs);
	void DialogDockTick(class cIGZWin* pMainWindow, class cIGZWin* pRegion,
		int32_t screenW, int32_t screenH);
	void ScaleMenuFlyouts(class cIGZWin* pMenu, int32_t screenW, int32_t screenH, float f);

	const Settings& settings;
	bool armed = false;
	bool moveProbeLogged = false;
	bool visibilityProbeOk = false;
	bool visibilityProbeLogged = false;
	bool continuous = false;      // incremental sweeps active (post initial scale)
	bool inPass = false;          // re-entrancy latch: no nested tree walks
	unsigned int fireAtMs = 0;
	unsigned int tickSerial = 0;  // incremental sweeps run every 4th tick (1s)
	bool bootDumpDone = false;    // one-shot main-window dump at the region
	                              // screen (no city armed) for recon
	unsigned int lastLiveDumpMs = 0; // throttle for the live city-view dump
	                                 // diagnostic (settings.spikeLiveDumpMs)


	// Pass-scoped frame for the size-sanity guard (set by pass entry points
	// before ScaleSubtree recursion; 0 disables the guard).
	int32_t passScreenW = 0;
	int32_t passScreenH = 0;

	// The 3D view, latched by ScaleGodFlyouts. The flyout-open hook needs a
	// view to run that pass with and has no way to look one up cheaply from
	// inside the game's own call stack. Null until the first sweep, which is
	// the correct failure mode: no view yet = nothing to scale yet.
	class cIGZWin* lastView = nullptr;

	// One-shot delayed RCI-column readout: the city-init readout runs before
	// the composite HUD is even visible, so it re-runs ~30 incremental
	// passes in (see DYNAMIC-CONTROLS.md, cSC4WinRCI draws from its rect).
	int rciRecheckCountdown = 0;

	// NEVER cleared between cities: UI windows can PERSIST across city
	// loads, and clearing while they persist re-scales them (2x -> 4x) when
	// ScaleAll re-runs. Stale keys (destroyed windows) are tolerated: keys
	// are only compared, never dereferenced (Classify only runs on windows
	// just observed via a live EnumChildren), and address reuse is
	// disambiguated by Classify()'s ID/size checks. ResetTracking() (app
	// shutdown) is the only clear.
	std::map<void*, ScaleRecord> scaleMap;

	// Region-screen watcher state (timer-driven; there is no city message
	// to arm from when only the region is up). Activation waits for the
	// host's child count to hold steady across consecutive ticks.
	int32_t regionChildCountSeen = -1;
	int regionStableTicks = 0;
	bool regionActive = false;

	// Per-dialog "docked this appearance" latches (indexed like the dock
	// table in UiSpike.cpp); cleared when the dialog closes so a reopened
	// dialog is re-scaled and re-docked.
	bool dialogDocked[8] = {};

	// Menu-container baseline (ptr -> id): direct children of 0xAA32BCE6
	// present at capture time = the persistent fold-out machinery, never
	// mutated. Visible children appearing AFTER the baseline are transient
	// flyouts. Re-captured each city session (cleared in Disarm).
	std::map<void*, uint32_t> menuBaseline;
	bool menuBaselineCaptured = false;

	friend struct UiSpikeEnumCtx;
};
