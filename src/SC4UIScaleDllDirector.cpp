////////////////////////////////////////////////////////////////////////////
//
// SC4UIScale - runtime UI scaling for SimCity 4 Deluxe 1.1.641
//
// The northstar: the game runs at the display's NATIVE resolution with full
// world detail, and the UI ELEMENTS are drawn larger. Three cooperating
// layers: this DLL's runtime cIGZWin-tree scaler (UiSpike), the 2x art
// override dat (z_SC4UIScale_SelectiveArt.dat), and the 2x FontStyle.ini.
//
// This DLL is self-contained: any number of gzcom directors can sit side by
// side in the Plugins folder, and this one owns only its own files. It reads
// SC4UIScale.ini, writes SC4UIScale.log, and installs its
// own lightweight subclass purely for a 16ms timer (and the dormant
// ScaleRemap message transforms, identity at native resolution).
//
////////////////////////////////////////////////////////////////////////////

#define WIN32_LEAN_AND_MEAN
#include <Windows.h>
#include <commctrl.h>

#include "cIGZCOM.h"
#include "cIGZFrameWork.h"
#include "cIGZFrameWorkW32.h"
#include "cIGZMessage2Standard.h"
#include "cIGZMessageServer2.h"
#include "cRZMessage2COMDirector.h"
#include "GZCLSIDDefs.h"
#include "GZServPtrs.h"

#include "CodePatches.h"
#include "Logger.h"
#include "ScaleTier.h"
#include "WebRedirect.h"
#include "SC4VersionDetection.h"
#include "ScaleRemap.h"
#include "Settings.h"
#include "SpinProbe.h"
#include "UiSpike.h"

#pragma comment(lib, "comctl32.lib")

#define UISCALE_NAME_STR "SC4UIScale"
// This string is the only version the log header knows. A log that names a
// build that is not running poisons every diagnosis that trusts it, so bump
// it in the same commit as the change it describes, never after.
#define UISCALE_VERSION_STR "4.0.4"

extern "C" IMAGE_DOS_HEADER __ImageBase;

namespace
{
	const uint32_t kSC4UIScaleDirectorID = 0x4AC38B1E; // touch director + 1

	const uint32_t kSC4MessagePostCityInit = 0x26D31EC1;
	const uint32_t kSC4MessagePreCityShutdown = 0x26D31EC2;

	const UINT_PTR kSubclassId = 0x55495331; // 'UIS1'
	const UINT_PTR kTimerId = 0x55495332;
	const UINT kTimerPeriodMs = 16;

	// â›” DO NOT ADD A WM_APP "EARLY PASS" CHANNEL. Built, measured and
	// reverted 2026-08-01 (task #89). The theory was that WM_TIMER, being
	// SYNTHESISED only when the queue is empty, was losing to a busy queue -
	// so a POSTED message would jump the line. It does not: the posted
	// message arrived +2016ms after arm versus the timer's +2031ms, a 15ms
	// gap = one timer period. The game does not pump messages AT ALL during
	// the city load tail, so there is no line to jump. Every message-queue
	// lever dies on that one fact. See _tests\REGRESSION.md task #89.

	void GetDllSiblingPath(const wchar_t* fileName, wchar_t* out, size_t outLen)
	{
		wchar_t path[MAX_PATH] = {};
		GetModuleFileNameW(reinterpret_cast<HMODULE>(&__ImageBase), path, MAX_PATH);

		wchar_t* lastSlash = wcsrchr(path, L'\\');
		if (lastSlash)
		{
			*(lastSlash + 1) = L'\0';
		}

		swprintf_s(out, outLen, L"%s%s", path, fileName);
	}
}

class SC4UIScaleDllDirector final : public cRZMessage2COMDirector
{
public:
	SC4UIScaleDllDirector()
		: remap(settings)
		, uiSpike(settings)
		, gameWindow(nullptr)
		, subclassed(false)
		, tierActive(false)
	{
		wchar_t iniPath[MAX_PATH] = {};
		wchar_t logPath[MAX_PATH] = {};
		GetDllSiblingPath(L"SC4UIScale.ini", iniPath, MAX_PATH);
		GetDllSiblingPath(L"SC4UIScale.log", logPath, MAX_PATH);

		settings.Load(iniPath);

		Logger& logger = Logger::Get();
		logger.Init(logPath, static_cast<LogLevel>(settings.logLevel));
		logger.WriteHeader(UISCALE_NAME_STR " v" UISCALE_VERSION_STR);
		// REQUIREMENT: enumerate the display's modes NOW, on a
		// background thread, not on the first Graphic Options click - v3.13.2
		// measured that enumeration at 3.3s (dgVoodoo between us and the
		// driver), all of it spent while the player watched a frozen dialog.
		uiSpike.WarmSelectorCaches();
		// #188 ARTFETCH armed AS EARLY AS THE DLL EXISTS. This constructor
		// runs during the plugin scan, long before PostAppInit - and that
		// matters: a PostAppInit-armed build saw ZERO fetches of the signpost
		// FRAME sheets even though our 2x override of those exact sheets
		// visibly moved a balloon, which means the fetch had already happened.
		// Log-only; gated on the same dev knob as the rest of the #188 probes.
		if (settings.spikeMissionBubbleFx >= 3)
		{
			CodePatches::InstallArtFetchProbe();
		}
		// #111: this line USED to print "factor=%.2f" from the ini, ~90 lines
		// before AutoScale overwrites spikeScaleFactor with the computed tier.
		// A reader saw "factor=2.00" next to "AutoScale: tier 1.50" in the same
		// log and concluded package selection was keying on the ini value -
		// a wrong diagnosis that stood for a day. It is not: ScaleTier.cpp reads
		// the ini NOWHERE, SyncStaticLayers matches only on its parameter, and
		// EVERY consumer of spikeScaleFactor runs after the tier assignment.
		// The defect was this instrument, so it now says what it actually is.
		// (Standing law: your own log line is an instrument, and this one lied.)
		logger.WriteLine(
			LogLevel::Info,
			"Settings (as READ FROM INI, before the tier decision): ScaleAll=%d "
			"ScaleRegion=%d MenuFlyouts=%d ScaleFactor=%.2f scaling=%d logLevel=%d",
			settings.spikeScaleAll ? 1 : 0,
			settings.spikeScaleRegion ? 1 : 0,
			settings.spikeMenuFlyouts ? 1 : 0,
			settings.spikeScaleFactor,
			settings.scalingEnabled ? 1 : 0,
			settings.logLevel);
		if (settings.spikeAutoScale)
		{
			logger.WriteLine(
				LogLevel::Info,
				"  ^ ScaleFactor above is the INI REQUEST and is about to be "
				"REPLACED by the computed tier (AutoScale=1). The EFFECTIVE "
				"factor is the one on the 'AutoScale: ... -> tier' line below, "
				"and that is what art, fonts and geometry all use.");
		}

		// DPI awareness FIRST (before reading the monitor size below), so the
		// metrics come back in physical pixels - and before the game creates
		// its window (this constructor runs during plugin scan).
		{
			using SetCtxFn = BOOL(WINAPI*)(DPI_AWARENESS_CONTEXT);
			HMODULE user32 = GetModuleHandleW(L"user32.dll");
			SetCtxFn setCtx = user32
				? reinterpret_cast<SetCtxFn>(GetProcAddress(user32, "SetProcessDpiAwarenessContext"))
				: nullptr;
			bool dpiOk = false;
			if (setCtx)
			{
				dpiOk = setCtx(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2) != FALSE;
			}
			if (!dpiOk)
			{
				dpiOk = SetProcessDPIAware() != FALSE;
			}
			logger.WriteLine(
				LogLevel::Info, "DPI awareness: %s.", dpiOk ? "per-monitor v2 set" : "FAILED (already set?)");
		}

		// AUTOSCALE tier decision: pick the factor from the ACTUAL RENDER
		// resolution (not the requested one), enable/stash the static data
		// layers to match - BEFORE the game loads dats or probes FontStyle.ini.
		{
			wchar_t gfxIni[MAX_PATH] = {};
			GetDllSiblingPath(L"SC4GraphicsOptions.ini", gfxIni, MAX_PATH);
			const int reqW = GetPrivateProfileIntW(L"GraphicsOptions", L"WindowWidth", 0, gfxIni);
			const int reqH = GetPrivateProfileIntW(L"GraphicsOptions", L"WindowHeight", 0, gfxIni);

			// KEY: what the game actually RENDERS the UI at differs from the
			// requested WindowWidth/Height. With DirectX + dgVoodoo in
			// EXCLUSIVE FULLSCREEN, the wrapper renders at the MONITOR's
			// native mode and reports that to the game (proven: request
			// 1600x1200 -> tree is 2400x1600). Borderless(FullScreen)
			// likewise covers the whole screen (WindowWidth/Height ignored
			// per the SC4GraphicsOptions docs). But WINDOWED DirectX renders
			// into a window of the requested size, and Software renders at
			// the requested size in every mode. So:
			//   DirectX + FullScreen/Borderless -> render = monitor native
			//   DirectX + Windowed              -> render = requested size
			//   Software (any mode)             -> render = requested size
			wchar_t driver[32] = {};
			GetPrivateProfileStringW(L"GraphicsOptions", L"Driver", L"DirectX", driver, 32, gfxIni);
			const bool software = _wcsicmp(driver, L"Software") == 0;

			wchar_t mode[40] = {};
			GetPrivateProfileStringW(L"GraphicsOptions", L"WindowMode", L"FullScreen", mode, 40, gfxIni);
			const bool windowed = _wcsicmp(mode, L"Windowed") == 0;
			// BORDERLESS covers the whole screen and the game's own ini says
			// outright that WindowWidth/Height are "ignored for the borderless
			// full screen mode" - so that mode, and only that mode, renders at
			// the desktop's size no matter what was requested.
			const bool borderless =
				_wcsicmp(mode, L"Borderless") == 0
				|| _wcsicmp(mode, L"BorderlessFullScreen") == 0;

			int gfxW = reqW;
			int gfxH = reqH;
			// EXCLUSIVE FULLSCREEN HONOURS THE
			// REQUEST. This branch used to cover every non-windowed mode on
			// the strength of one measurement (request 1600x1200 -> tree came
			// back 2400x1600), and that measurement was taken under a
			// different wrapper configuration. dgVoodoo.conf here reads
			// `Resolution = unforced`, which passes the game's requested mode
			// straight through - and the player OBSERVED the desktop mode change
			// when they picked a resolution, which is the same fact from the
			// other side.
			//
			// So only BORDERLESS ignores the request now. Exclusive fullscreen
			// performs a real mode change and renders at what was asked for,
			// exactly like windowed. If a wrapper is ever configured to force
			// a resolution instead, UiSpike's RESMISMATCH check measures the
			// window the game actually laid out and corrects the tier - the
			// assumption is no longer the only line of defence.
			if (!software && borderless)
			{
				const int monW = GetSystemMetrics(SM_CXSCREEN);
				const int monH = GetSystemMetrics(SM_CYSCREEN);
				if (monW > 0 && monH > 0)
				{
					gfxW = monW;
					gfxH = monH;
				}
				logger.WriteLine(
					LogLevel::Info,
					"AutoScale: DirectX %ls - render res = desktop %dx%d "
					"(requested %dx%d is ignored in borderless by the game's "
					"own rule).", mode, gfxW, gfxH, reqW, reqH);
			}
			else if (!software)
			{
				// Windowed AND exclusive fullscreen both render at the
				// requested size - fullscreen by changing the display mode to
				// match, which is why the desktop resolution visibly changes.
				logger.WriteLine(
					LogLevel::Info,
					"AutoScale: DirectX %ls - render res = requested %dx%d.",
					mode, gfxW, gfxH);
			}
			else
			{
				logger.WriteLine(
					LogLevel::Info, "AutoScale: Software %ls - render res = requested %dx%d.", mode, gfxW, gfxH);
			}

			// #192: publish what the tier was decided FROM, for the readout in
			// the Graphic Options dialog. gfxW/gfxH here is the RENDER res
			// after the wrapper has had its say - not the requested size the
			// game's own resolution list shows.
			UiSpike::SetRenderResForReadout(gfxW, gfxH);
			// The same condition the branch above already decided on: when
			// the wrapper renders at the monitor's mode, the game's own
			// WindowWidth/Height are ignored, so Graphic Options' four
			// resolution rows are inert controls. Told once, here, because
			// this is the only place that works it out.
			UiSpike::SetRequestedResIgnored(!software && borderless);

			// CAPTURED BEFORE ANYTHING FORCES IT. spikeScaleAll is set to
			// false in two places below (the auto-path's !tierActive block and
			// the stock-factor block), so by the time the static-layer gate is
			// reached it no longer answers "did the USER ask for this mod to be
			// active" - it answers "is scaling happening right now", which is a
			// different question and the wrong one for that gate.
			const bool iniWantsScaling = settings.spikeScaleAll;

			// THE BOOT-STATE VALIDATOR. The requirement: if a player manually
			// adjusts the ini we need to run a check for resolution and scale
			// combination correct, and if it flags false flip it back to
			// auto, automatically").
			//
			// HERE, and outside both branches, because what it asks depends
			// only on the ini and the screen - never on HOW the factor was
			// chosen. A gate that depends only on the factor living inside a
			// branch that asks how the factor was picked is the shape that
			// has shipped from this one function four times (#149, #182, and
			// the two of 2026-08-19 recorded below).
			//
			// It replaces the narrower Fits() rescue that used to sit in the
			// manual branch: that was one of these conditions, and two
			// rescues in two branches would be two rules.
			wchar_t bootIni[MAX_PATH] = {};
			GetDllSiblingPath(L"SC4UIScale.ini", bootIni, MAX_PATH);
			ScaleTier::BootState bs = {
				settings.spikeAutoScale, settings.spikeScaleFactor,
				settings.spikeScaleAll, gfxW, gfxH
			};
			const bool bootRepaired = !ScaleTier::ValidateBootState(bs, bootIni);
			settings.spikeAutoScale = bs.autoScale;
			settings.spikeScaleFactor = bs.factor;

			if (settings.spikeAutoScale)
			{
				const float tier = ScaleTier::Decide(gfxW, gfxH);
				tierActive = tier > 1.01f;
				settings.spikeScaleFactor = tier;
				if (!tierActive)
				{
					// Tier 1 = TRUE stock: every scaling subsystem off.
					// (Isolation-tested: the DLL must be inert here, not
					// merely "disabled".)
					settings.spikeScaleAll = false;
					settings.spikeScaleRegion = false;
					settings.spikeMenuFlyouts = false;
					settings.spikeDumpTree = false;
				}
				logger.WriteLine(
					LogLevel::Info,
					"AutoScale: %dx%d -> tier %.2f (%s).",
					gfxW, gfxH, tier,
					tierActive ? "scaling active" : "stock - all layers dormant");
			}
			else
			{
				// The fit rescue that used to live here is now condition C7
				// of ScaleTier::ValidateBootState, which runs above and
				// outside both branches. Two rescues in two branches would be
				// two rules, and this one could only ever see manual mode.
				tierActive = settings.spikeScaleAll
					&& settings.spikeScaleFactor > 1.01f;
				logger.WriteLine(
					LogLevel::Info,
					"AutoScale %s: ScaleFactor %.2f, static layers %s.",
					settings.spikeAutoScale ? "RESCUED to auto" : "off (manual)",
					settings.spikeScaleFactor,
					tierActive ? "synced at this factor (#182)"
					           : "untouched (ScaleAll=0 or stock factor)");
			}

			// FACTOR 1 MEANS INERT, NO MATTER HOW THE FACTOR WAS CHOSEN.
			// The "Tier 1 = TRUE stock" block above lives inside the AutoScale
			// branch, so it never ran for a MANUAL tier 1 - and Set-Tier.ps1
			// -Tier 1 sets AutoScale=0 + ScaleFactor=1, which is exactly how a
			// 1x reference is taken. Result, measured 2026-08-19 at 1024x768:
			//     UiSpike: ScaleAll done, 529 windows scaled.
			//     UiSpike: SUBHOOK strip 0x8A2CAD8B -> ... (item fields x2)
			// The whole sweep ran at f=1.00 and the sub-flyout strip was given
			// x2 item fields inside a 1x layout. That is the broken docking the
			// user photographed at the 1x baseline, twice.
			//
			// THIRD INSTANCE OF THIS EXACT SHAPE IN THIS ONE FUNCTION. The
			// comments below already record #149 and #182 - both "AutoScale=0,
			// a supported user setting, silently changed behaviour". Those two
			// were fixed by moving a gate OUT of the AutoScale branch, and this
			// one is the same move for the same reason. A decision that depends
			// only on the FACTOR must never live inside a branch that asks how
			// the factor was chosen.
			if (settings.spikeScaleFactor <= 1.01f)
			{
				tierActive = false;
				settings.spikeScaleAll = false;
				settings.spikeScaleRegion = false;
				settings.spikeMenuFlyouts = false;
				settings.spikeDumpTree = false;
				logger.WriteLine(
					LogLevel::Info,
					"Factor %.2f is stock: every scaling subsystem forced OFF "
					"(ScaleAll/ScaleRegion/MenuFlyouts/DumpTree), regardless of "
					"AutoScale=%d. A 1x baseline must be INERT, not merely "
					"'scaling by 1' - the sweep still installs draw hooks and "
					"hands strips x2 item fields.",
					settings.spikeScaleFactor, settings.spikeAutoScale ? 1 : 0);
			}

			// The hook-visible tier mirror, pushed UNCONDITIONALLY and for
			// BOTH branches (auto and manual), at the first moment the
			// effective factor is known. It used to be set only inside
			// ScaleGodFlyouts/ScaleMenuFlyouts, which are scaling paths - so
			// at tier 1 it kept its initialiser and every one of its 97
			// readers behaved as if the tier were 2x. That is why the 1x
			// baseline was not inert: sub-flyouts were born x2.00 inside a 1x
			// layout (log, 2026-08-19).
			UiSpike::SetTierMirror(settings.spikeScaleFactor);

			// #182: the sync runs for MANUAL tiers too. This gate used to be
			// AutoScale-only, and that is the SECOND instance of the exact
			// failure documented for #149 below ("AutoScale=0 - a supported
			// user setting - silently turned the cure off"): a package
			// deployed fresh under manual mode never had its tier activated,
			// so the 2x UncoveredIcons strip served at 1.5x - Notre-Dame's
			// icon shifted right with a wrong hover (2026-08-17, user-
			// reported; ZERO ScaleTier lines in the whole session log was
			// the proof - law 54). Manual + ScaleAll=0 keeps the untouched
			// behaviour: Set-StockCompare owns that state with its own
			// suffixes, and a dormant rig must not have its files renamed.
			// `|| iniWantsScaling` ADDED 2026-08-19 - CHOOSING 1x MUST UNLOAD
			// THE ART. Without it, a manual stock factor skipped this sync
			// entirely and the PREVIOUS tier's dats stayed armed: geometry ran
			// at 1x while the art was still 2x, so the whole UI was wrong on
			// screen. User-reported the first time the in-game selector was
			// used to pick 1x ("1X didn't work the game loaded with every
			// broken"), and the log named it two lines apart - "Factor 1.00 is
			// stock: every scaling subsystem forced OFF" followed by "static
			// layers untouched".
			//
			// SyncStaticLayers(1.0) is exactly the right call here: its own
			// contract for factor <= 1.01 is disable-all, so this stashes every
			// package and leaves the stock-tier selector as the only thing of
			// ours in the game - which is precisely what picking 1x means.
			//
			// The ScaleAll=0 rig KEEPS its untouched behaviour, because that is
			// what iniWantsScaling reads: Set-StockCompare owns that state with
			// its own suffixes and a dormant rig must not have its files
			// renamed. The distinction the old gate could not draw is "the player
			// asked for stock" versus "the rig is dormant"; the ini's own
			// ScaleAll is what separates them.
			// `|| bootRepaired` is MANDATORY, not cosmetic. A repair means we
			// are running something other than what the ini asked for, so the
			// art MUST be resynced to what we actually run. Without it the
			// force-stock repair (autoScale=false, factor=1.0, scaleAll=false)
			// makes all three other terms false, and the previous tier's dats
			// stay armed - the exact trap the repair exists to close.
			if (settings.spikeAutoScale || tierActive || iniWantsScaling
				|| bootRepaired)
			{
				// #111: name the EFFECTIVE factor at the moment the static
				// layers are chosen, so "which art/font package is live" is
				// answerable from the log without inferring it from two lines
				// printed at different times. Geometry uses this same value.
				logger.WriteLine(
					LogLevel::Info,
					"Static layers: selecting the x%.2f package (art dats + "
					"FontStyle) - same factor the runtime geometry uses.",
					settings.spikeScaleFactor);
				ScaleTier::SyncStaticLayers(settings.spikeScaleFactor);
			}

			// UNCONDITIONAL, AND OUTSIDE EVERY BRANCH ABOVE. The stock-tier
			// scale selector's package is armed by the ABSENCE of a tier, so
			// the one state it must reach is the state in which none of the
			// branches above run at all.
			//
			// MEASURED 2026-08-19, one build after it shipped: it was folded
			// into SyncStaticLayers, which is not called at the stock tier
			// ("static layers untouched (ScaleAll=0 or stock factor)" two
			// lines up in the same log). Result on a 1x machine - the dat sat
			// as .x1-disabled, this DLL logged that the selector "IS
			// serviced", and Graphic Options had no selector in it. The code
			// half ran, the data half was stashed, and the log looked healthy.
			//
			// THIRD TIME THIS SHAPE HAS SHIPPED FROM THIS FUNCTION. #149 and
			// #182 are recorded a few lines below in exactly these terms:
			// work bolted onto a convenient neighbour inherits that
			// neighbour's gate silently. The condition this depends on is
			// "is the tier stock" - so that, and nothing else, is what it is
			// gated on.
			ScaleTier::SyncSelectorPackage(!tierActive);

			// #149: OUTSIDE the AutoScale branch, deliberately. The scan
			// depends only on the FACTOR, never on how the factor was chosen.
			// It used to ride inside SyncStaticLayers and therefore inherited
			// that function's AutoScale gate, so AutoScale=0 - a supported
			// user setting - silently turned the uncovered-icon cure off.
			if (tierActive)
			{
				ScaleTier::ScanUncoveredIcons(settings.spikeScaleFactor);
			}

			// #138 INTRO VIDEO - PATCHED HERE, NOT IN PostAppInit.
			// The game builds cSC4WinIntroVideoScreen during its own
			// app-init; PostAppInit (where every other CodePatches call
			// lives) runs LONG after that - measured +16.4s on 2026-08-05.
			// A patch applied there is installed but never executed, which
			// is law 47 and has cost this project whole sessions. The tier
			// is already final at this point, so the correct factor is in
			// hand: patch now.
			if (settings.spikeScaleAll)
			{
				CodePatches::ApplyIntroVideoScale(settings.spikeScaleFactor);
			}
		}

		// ScaleRemap installs ONLY if explicitly opted in (default off). Its
		// internal!=present metric lies are the rejected whole-frame approach;
		// with UI-element scaling + dgVoodoo present-scaling they double-
		// transform and garble. (DPI awareness was already set above.)
		if (settings.scalingEnabled && tierActive)
		{
			if (settings.useScaleRemap)
			{
				int internalW = settings.internalWidth;
				int internalH = settings.internalHeight;
				if (internalW <= 0 || internalH <= 0)
				{
					wchar_t gfxIni[MAX_PATH] = {};
					GetDllSiblingPath(L"SC4GraphicsOptions.ini", gfxIni, MAX_PATH);
					internalW = GetPrivateProfileIntW(L"GraphicsOptions", L"WindowWidth", 0, gfxIni);
					internalH = GetPrivateProfileIntW(L"GraphicsOptions", L"WindowHeight", 0, gfxIni);
				}
				remap.EarlyInstall(internalW, internalH);
			}
			else
			{
				logger.WriteLine(LogLevel::Info, "ScaleRemap disabled (UI-element scaling only).");
			}
		}
	}

	uint32_t GetDirectorID() const override
	{
		return kSC4UIScaleDirectorID;
	}

	bool QueryInterface(uint32_t riid, void** ppvObj) override
	{
		if (riid == GZCLSID::kcIGZMessageTarget2)
		{
			*ppvObj = static_cast<cIGZMessageTarget2*>(this);
			AddRef();
			return true;
		}
		return cRZCOMDllDirector::QueryInterface(riid, ppvObj);
	}

	uint32_t AddRef() override { return cRZCOMDllDirector::AddRef(); }
	uint32_t Release() override { return cRZCOMDllDirector::Release(); }

	bool OnStart(cIGZCOM* pCOM)
	{
		const uint16_t gameVersion = GetGameVersion();
		if (gameVersion < kMinSupportedGameVersion)
		{
			Logger::Get().WriteLine(
				LogLevel::Error,
				"Game version %u detected (minimum supported is %u). Every "
				"patch this DLL installs targets the %u build, so no hooks "
				"are registered and nothing is patched - the DLL stays inert.",
				static_cast<unsigned>(gameVersion),
				static_cast<unsigned>(kMinSupportedGameVersion),
				static_cast<unsigned>(kMinSupportedGameVersion));
			return true;
		}
		if (gameVersion > kTestedGameVersion)
		{
			Logger::Get().WriteLine(
				LogLevel::Info,
				"Game version %u detected - newer than the tested build %u. "
				"Proceeding: every byte patch verifies its site before "
				"writing and declines individually if the build moved it.",
				static_cast<unsigned>(gameVersion),
				static_cast<unsigned>(kTestedGameVersion));
		}

		cIGZFrameWork* const pFramework = RZGetFrameWork();
		if (pFramework->GetState() < cIGZFrameWork::kStatePreAppInit)
		{
			pFramework->AddHook(this);
		}
		else
		{
			PreAppInit();
		}
		return true;
	}

	bool PostAppInit()
	{
		Logger& logger = Logger::Get();

		// #149. FIRST thing in PostAppInit, deliberately: the dats are indexed
		// by now but no menu strip has been built, so registering enlarged art
		// for the icons no package of ours covers means every consumer that
		// ever asks gets the correct size - born correct, no blit hook, and
		// nothing to flicker against. Runs only when the scaler is active.
		if (settings.spikeScaleAll)
		{
			ScaleTier::EnlargeUncoveredIcons(settings.spikeScaleFactor);
		}

		// #121: the minimap terrain bake's x8 extension. Rides the scaler
		// switch like every other geometry patch - it exists because OUR
		// resized Data Views map reaches zoom -3, which the game's own bake
		// dispatch excludes. Verifies 15 + 33 + 20 bytes and declines on any
		// mismatch; never writes at factor 1.
		if (settings.spikeScaleAll)
		{
			CodePatches::ApplyMiniMapX8Bake(settings.spikeScaleFactor);
		}

		// Hardcoded-geometry patches ride the scaler switch: they only make
		// sense alongside the 2x art they compensate for.
		if (settings.spikeScaleAll && settings.spikeRatingArrowPatch)
		{
			CodePatches::ApplyRatingArrowScale(settings.spikeScaleFactor);
		}
		// #130: the reveal WIDTH above and the reveal ORIGIN here are one
		// control. ApplyRatingArrowScale only scales the step (7 -> 7f, which
		// is exactly the authored W/3); the origin comes from a snapshot the
		// panel builder takes before anything of ours can scale the window.
		if (settings.spikeScaleAll)
		{
			CodePatches::InstallRatingArrowAnchor(settings.spikeScaleFactor,
				settings.spikeRatingArrowAnchor);
		}
		// #188: the U-Drive-It start bubbles are renderer-drawn Swarm
		// effects; a data override of their EFFDIR was proven inert from
		// both plugin trees, so the spawned instance is scaled instead.
		// The click test is a ray-pick against the drawn geometry (no
		// radius constant), so the bigger visual IS the bigger click
		// target.
		if (settings.spikeScaleAll)
		{
			CodePatches::InstallMissionBubbleScale(settings.spikeScaleFactor,
				settings.spikeMissionBubbleFx,
				settings.spikeMissionBubbleScale);
		}
		if (settings.spikeScaleAll && settings.spikeTooltipWrapPatch)
		{
			CodePatches::ApplyTooltipWrapScale(settings.spikeScaleFactor);
		}
		// #159 placement cost readout. Its own key, not TooltipWrapPatch's:
		// the two are different constants in different subsystems, and the
		// tooltip wrap was already applied while this box still clipped -
		// which is how we knew they were separate.
		if (settings.spikeScaleAll && settings.spikeCostBoxPatch)
		{
			CodePatches::ApplyCostBoxScale(settings.spikeScaleFactor);
		}
		// #131: the region map. Rides ScaleRegion, not ScaleAll - ScaleRegion
		// is the switch that says "the region screen is ours". This is the one
		// patch here that compensates for no artwork at all: the region
		// terrain is renderer-drawn at a fixed px-per-cell and simply ignores
		// resolution. RegionMapScale < 0 means "follow the tier".
		if (settings.spikeScaleRegion && settings.spikeRegionMapScale != 0.0f)
		{
			const float regionFactor = (settings.spikeRegionMapScale > 0.0f)
				? settings.spikeRegionMapScale
				: settings.spikeScaleFactor;
			// The isometric basis is the lever. ApplyRegionCameraScale is
			// disarmed (measured dead) and kept only as a tombstone.
			CodePatches::ApplyRegionIsoScale(regionFactor);
			// COUPLED PAIR (law 43): the basis moves tile POSITIONS, this makes
			// the tiles that big by growing sub_7AE3D0's output inside the
			// game's own rebuild. Ship both or neither - the basis alone
			// spreads the tiles apart with gaps (confirmed on screen, worse than the
			// defect it fixes).
			CodePatches::SetRegionTileSharp(settings.spikeRegionTileSharp);
			const int tileHooked = CodePatches::ApplyRegionTileScale(regionFactor);
			// #132: the snapshot hook. Must be installed BEFORE the first
			// region screen opens, because what it captures is each item's
			// pristine art on the way into sub_7AE510 - the one moment the
			// un-shifted savegame thumbnail exists.
			//
			// GATED ON THE TILE HOOK, and that is load-bearing (adversarial
			// review, 2026-08-05, CONFIRMED). ApplyRegionTileScale installs
			// nothing at factor <= 1.001, and RegionMapScale=1.0 reaches here
			// because the gate above only tests != 0. Zoom would then move the
			// BASIS while every rebuilt tile came out stock-sized - the tiles
			// spread apart with gaps, which is precisely the half-of-a-coupled-
			// pair failure this file's own comment says must never ship.
			// Same outcome if MinHook succeeded on 0x7AE510 and failed on
			// 0x7AE3D0. Both halves or neither (law 43).
			if (settings.spikeRegionZoom && tileHooked)
			{
				CodePatches::ApplyRegionZoomHook();
			}
			else if (settings.spikeRegionZoom)
			{
				logger.WriteLine(
					LogLevel::Info,
					"UIScale: REGIONZOOM NOT armed - the tile-growth hook did not"
					" install at factor %.2f, so a zoom could only move the"
					" lattice and leave the tiles stock-sized.", regionFactor);
			}
		}
		if (settings.spikeScaleAll && settings.spikeHtmlSizePatch)
		{
			CodePatches::ApplyHtmlSizeScale(settings.spikeScaleFactor);
		}
		if (settings.spikeScaleAll && settings.spikeAdviceRowPatch)
		{
			// Must ride the same gate as the SelectiveArt package: this
			// patch is the precondition of the twelve 2x row glyphs, and
			// the art without it is exactly the task-#88 defect.
			CodePatches::ApplyAdviceRowScale(settings.spikeScaleFactor);
		}
		if (settings.spikeScaleAll && settings.spikeBudgetButtonPatch)
		{
			CodePatches::ApplyBudgetButtonScale(settings.spikeScaleFactor);
		}
		if (settings.spikeScaleAll && settings.spikeOrdinanceInsetPatch)
		{
			CodePatches::ApplyOrdinanceInsetScale(settings.spikeScaleFactor);
			// COUPLED HALF (law 43), v2.74.0. Same ini switch, adjacent line:
			// the name-label x is the one inset that cannot fit a push imm8, so
			// above x2.50 it is re-encoded as two equal-length 43-byte blocks
			// instead of clamped to 127. The call MUST follow the line above,
			// not precede it: ApplyOrdinanceInsetScale leaves the two windows
			// stock at f >= 2.5, and the block applier verifies stock bytes.
			// Below x2.50 this is a no-op and 2x keeps its confirmed clamp.
			CodePatches::ApplyOrdinanceNameColumnScale(settings.spikeScaleFactor);
		}
		if (settings.spikeScaleAll && settings.spikeBudgetDeptPatch)
		{
			CodePatches::ApplyBudgetFamilyScale(settings.spikeScaleFactor);
			if (settings.spikeSubFlyoutBorn2x > 0)
			{
				CodePatches::ApplySubFlyoutProviderScale(settings.spikeScaleFactor);
			}
		}
		// v2.37.0 task #78: the Data Views legend is laid out by the game on
		// EVERY view selection, so it must be born correct - a sweep pin can
		// only ever fix it one presented frame late.
		if (settings.spikeScaleAll && settings.spikeDataViewLegendPatch > 0)
		{
			CodePatches::ApplyDataViewLegendScale(settings.spikeScaleFactor);
		}
		// v2.55.0 task #57: the GRAPHS legend budget is NOT armed here. It is
		// one half of a coupled pair with EARLYCHART's plot right margin, and
		// its disarm flag ([Flyout] ChartScale) is read by UiSpike's own ini
		// pass rather than by Settings - so both halves arm together inside
		// UiSpike, where that flag is in scope. Splitting them across two call
		// sites is exactly how they could drift apart (law 43), and the
		// oracle's H-EARLYCHART candidate shows what a split pair looks like
		// on screen: the plot border painted inside the checkbox column.

		// Dead-link fix (independent of scaling): the website button's
		// http://simcity.ea.com/ has been gone for years - send it to the
		// community hub instead. Active at EVERY tier.
		//
		// v2.69.0: now declinable. This is the only non-scaling behaviour in
		// the DLL and it installs a process-wide ShellExecuteA/W hook, so a
		// user who wants strictly-scaling-and-nothing-else must be able to say
		// no - [UiSpike] WebRedirect=0. Default stays on: the EA URL is dead.
		if (settings.webRedirect)
		{
			WebRedirect::Install();
		}
		else
		{
			logger.WriteLine(LogLevel::Info,
				"SC4UIScale: WebRedirect declined by ini - the region website "
				"button keeps its original (dead) EA URL.");
		}

		// Stock tier: nothing else runs - no window attach, no subclass,
		// no timer, no message hooks. The game must be indistinguishable
		// from a no-DLL install (isolation-proven requirement).
		if (!tierActive)
		{
			// ONE EXCEPTION, and it is the reason the tier is escapable: the
			// scale selector in Graphic Options. Without a tick source here,
			// 1x is a one-way door - every package is stashed, so the only
			// way back up is editing the ini by hand, which is exactly what
			// the selector exists to replace.
			//
			// What installs: the window subclass and the WM_TIMER, and the
			// timer body runs ServiceScaleSelector ONLY (TickCheck returns
			// immediately - nothing ever arms at this tier). No message
			// subscriptions, no code patches, no sweeps, no hooks.
			//
			// SelectorAtStock=0 restores the absolute isolation this block
			// used to have, and Set-Tier.ps1 -Tier 1 writes that 0 - so a
			// STOCK REFERENCE CAPTURE is still a true no-DLL control, while a
			// player who chose 1x in-game keeps a way back. The two paths to
			// 1x want different things and now say so.
			if (settings.spikeSelectorAtStock)
			{
				cIGZFrameWorkW32* pFwStock = nullptr;
				if (RZGetFrameWork()->QueryInterface(
					GZIID_cIGZFrameWorkW32, reinterpret_cast<void**>(&pFwStock)))
				{
					gameWindow = pFwStock->GetMainHWND();
					pFwStock->Release();
					if (gameWindow && SetWindowSubclass(gameWindow, SubclassProc,
						kSubclassId, reinterpret_cast<DWORD_PTR>(this)))
					{
						subclassed = true;
						SetTimer(gameWindow, kTimerId, kTimerPeriodMs, nullptr);
						logger.WriteLine(LogLevel::Info,
							"Stock tier: UI-scaling subsystems not installed; "
							"the Graphic Options scale selector IS serviced "
							"(SelectorAtStock=1) so 1x is not a one-way door.");
						return true;
					}
				}
				logger.WriteLine(LogLevel::Info,
					"Stock tier: selector wanted but no tick source could be "
					"installed - 1x has no in-game way back. Use "
					"_tests\\Set-Tier.ps1.");
				return true;
			}
			logger.WriteLine(LogLevel::Info,
				"Stock tier: UI-scaling subsystems not installed, selector "
				"declined by ini (SelectorAtStock=0) - fully inert.");
			return true;
		}

		cIGZMessageServer2Ptr pMsgServ;
		if (pMsgServ)
		{
			if (!pMsgServ->AddNotification(this, kSC4MessagePostCityInit)
				|| !pMsgServ->AddNotification(this, kSC4MessagePreCityShutdown))
			{
				logger.WriteLine(LogLevel::Error, "Failed to subscribe to city messages.");
				return true;
			}
		}
		else
		{
			logger.WriteLine(LogLevel::Error, "Message server unavailable.");
			return true;
		}

		cIGZFrameWorkW32* pFrameworkW32 = nullptr;
		if (RZGetFrameWork()->QueryInterface(
			GZIID_cIGZFrameWorkW32, reinterpret_cast<void**>(&pFrameworkW32)))
		{
			gameWindow = pFrameworkW32->GetMainHWND();
			pFrameworkW32->Release();

			if (gameWindow)
			{
				if (settings.useScaleRemap)
				{
					remap.AttachWindow(gameWindow);
				}

				if (SetWindowSubclass(gameWindow, SubclassProc, kSubclassId,
					reinterpret_cast<DWORD_PTR>(this)))
				{
					subclassed = true;
					SetTimer(gameWindow, kTimerId, kTimerPeriodMs, nullptr);
					logger.WriteLine(LogLevel::Info, "Tick subclass installed (16ms).");
				}
				else
				{
					logger.WriteLine(LogLevel::Error, "SetWindowSubclass failed - no tick source.");
				}
			}
			else
			{
				logger.WriteLine(LogLevel::Error, "GetMainHWND returned null.");
			}
		}
		else
		{
			logger.WriteLine(LogLevel::Error, "cIGZFrameWorkW32 unavailable.");
		}

		return true;
	}

	bool PreAppShutdown()
	{
		// #104 SHUTDOWN TRACE. The game "hangs on shutdown" often enough that
		// it blocked the deploy step TWICE in one session (the window
		// closes, the PROCESS does not exit, and the player has to End Task).
		// Waiting for a clean exit is the ONLY safe deploy path because the game
		// runs elevated and holds the DLL open, so this tax is paid on every
		// build.
		//
		// This is a PROBE, not a fix, and it is deliberately shaped to
		// adjudicate rather than to sight (law 44). Each stage prints BEFORE
		// it runs, so the LAST LINE IN THE LOG NAMES THE STAGE THAT HUNG:
		//   no SHUTDOWN line at all -> we never got here; the hang is in the
		//     game or in something ahead of PreAppShutdown, and NOTHING in
		//     this function is implicated. That is the single most valuable
		//     outcome, because it exonerates the whole cleanup path in one
		//     observation.
		//   "SHUTDOWN 1/3" is last  -> KillTimer/RemoveWindowSubclass hung
		//   "SHUTDOWN 2/3" is last  -> remap.Uninstall() (MinHook) hung
		//   "SHUTDOWN 3/3" is last  -> ResetTracking hung
		//   "SHUTDOWN done"         -> our cleanup completed; anything after
		//     that is the game's own teardown, and the stock control decides
		//     whether stock does the same.
		// NOTE what is deliberately NOT undone here and stays a live
		// hypothesis: the CodePatches BYTE PATCHES in the game's .text are
		// never reverted, and UiSpike's per-instance VTABLE COPIES are never
		// restored. Neither is touched by this probe.
		// The freeze instrument's last chance to report: a session where
		// Graphic Options never closed cleanly still gets its table.
		uiSpike.DumpSelectorPerf("shutdown");
		Logger::Get().WriteLine(
			LogLevel::Info, "SHUTDOWN 1/3 timer+subclass (subclassed=%d hwnd=%p)",
			subclassed ? 1 : 0, static_cast<void*>(gameWindow));
		if (subclassed && gameWindow)
		{
			KillTimer(gameWindow, kTimerId);
			RemoveWindowSubclass(gameWindow, SubclassProc, kSubclassId);
			subclassed = false;
		}
		Logger::Get().WriteLine(LogLevel::Info, "SHUTDOWN 2/3 remap.Uninstall");
		remap.Uninstall();
		Logger::Get().WriteLine(LogLevel::Info, "SHUTDOWN 3/3 ResetTracking");
		uiSpike.ResetTracking(); // full forget is safe only at APP shutdown
		// FONT REVERT (v4.0.4): the last chance to prevent a leftover scaled
		// FontStyle.ini from outliving an sc4pac uninstall - see
		// ScaleTier::RevertFontOnShutdown's own comment for why this has to
		// happen HERE, not on any later launch. Logged before/after like
		// every other stage, so a hang here names itself the same way.
		Logger::Get().WriteLine(LogLevel::Info, "SHUTDOWN 3.5/3 font revert");
		ScaleTier::RevertFontOnShutdown();
		Logger::Get().WriteLine(
			LogLevel::Info,
			"SHUTDOWN done - our cleanup returned. Anything after this is the "
			"game's own teardown (byte patches and vtable copies NOT reverted).");

		// SPINPROBE (task #105). "Anything after this" is precisely where the
		// #104 spin lives - the four measured constraints put it AFTER this
		// point, on a thread that is not the pump. So this is the one moment
		// worth sampling, and it is the last line of our code that runs.
		//
		// The bisect named a CONFIG (OrdinanceInsetPatch + BudgetDeptPatch,
		// Budget opened) but a config is not a mechanism, and two mechanism
		// stories invented from the disassembly have already been wrong. One
		// hot EIP settles it. Default OFF; see SpinProbe.h for why it is safe
		// to suspend threads here and what it refuses to do.
		// #107 OUTCOME RECORDER. #104 is INTERMITTENT - two runs on
		// 2026-08-03 with byte-identical config and identical actions gave
		// opposite outcomes. That makes the 13-run bisect's CLEAN verdicts
		// coin flips rather than evidence, so the pair it named is not
		// established. Deciding it needs RATES, and rates are only cheap if
		// ordinary play supplies them - hence one row per launch, appended to
		// a file that (unlike SC4UIScale.log) is never recreated.
		SpinProbe::LaunchInfo li = {};
		li.version = UISCALE_VERSION_STR;
		li.factor = settings.spikeScaleFactor;
		li.scaleAll = settings.spikeScaleAll;
		li.ordinanceInset = settings.spikeOrdinanceInsetPatch;
		li.budgetDept = settings.spikeBudgetDeptPatch;
		li.budgetButton = settings.spikeBudgetButtonPatch;
		li.probeSeconds = settings.spikeSpinProbe;
		li.spinFix = settings.spikeSpinFix;
		SpinProbe::RecordShutdown(li);

		// v2.67.0 (#114): THE FIX AND THE PROBE ARE NOW SEPARATE.
		// Until now Arm() was called ONLY when SpinProbe > 0, and the #104
		// shutdown-hang cure lives INSIDE the sampler loop. So the obvious
		// release hygiene move - set SpinProbe=0 in the shipped ini - would
		// have silently removed the hang fix and handed every user the 85-150%
		// CPU spin on exit. Nothing said so; the coupling was invisible.
		//
		// So: arm when EITHER is wanted, and pick the window from which one.
		//   SpinProbe > 0  -> diagnostic run, user-chosen duration, CSV on
		//   SpinFix only   -> kFixOnlySeconds, no CSV, no per-second reporting
		// The fix-only window is short on purpose: if the repair works the
		// process exits within ~1s (measured, v2.62.0), and if it does not
		// there is nothing to gain by sampling a dying process for two
		// minutes. A shorter window also bounds the one behaviour that reads
		// badly from outside - suspending threads during shutdown.
		const int kFixOnlySeconds = 30;
		const int probeSecs = settings.spikeSpinProbe > 0
			? settings.spikeSpinProbe
			: (settings.spikeSpinFix != 0 ? kFixOnlySeconds : 0);
		if (probeSecs > 0)
		{
			SpinProbe::Arm(probeSecs);
		}
		return true;
	}

	bool DoMessage(cIGZMessage2* pMessage)
	{
		cIGZMessage2Standard* pStandard = static_cast<cIGZMessage2Standard*>(pMessage);

		switch (pStandard->GetType())
		{
		case kSC4MessagePostCityInit:
			// Deferred: the walk hangs the game if run inside this message.
			// Fire on the NEXT timer tick (~16ms) - the earliest safe moment
			// once the message loop pumps again. The old 2s delay outlasted
			// the loading screen, causing a visible 1x -> 2x flash.
			uiSpike.ArmDeferred(GetTickCount());
			// #188 elimination instrument: the render singleton exists only
			// after city init, so the Pick probe installs here (tiny: a few
			// reads + one MinHook; idempotent).
			if (settings.spikeScaleAll && settings.spikeMissionBubbleFx >= 3)
			{
				CodePatches::InstallPickProbe();
			}
			break;
		case kSC4MessagePreCityShutdown:
			// Disarm stops the sweeps but the scale records SURVIVE the city
			// transition: persistent windows must stay marked as scaled or
			// the next ScaleAll would compound 2x -> 4x.
			uiSpike.Disarm();
			break;
		}

		return true;
	}

private:
	static LRESULT CALLBACK SubclassProc(
		HWND hwnd, UINT msg, WPARAM wParam, LPARAM lParam,
		UINT_PTR subclassId, DWORD_PTR refData)
	{
		SC4UIScaleDllDirector* self = reinterpret_cast<SC4UIScaleDllDirector*>(refData);

		if (msg == WM_TIMER && wParam == kTimerId)
		{
			// The in-game scale selector is serviced FIRST and
			// UNCONDITIONALLY. TickCheck does nothing unless a city armed the
			// sweep, and at the stock tier nothing ever arms it - which is
			// precisely where the player needs this control, because 1x is
			// the state you cannot leave without it. Self-throttled to 250ms.
			self->uiSpike.ServiceScaleSelector();
			self->uiSpike.TickCheck(GetTickCount());
			return 0;
		}

		// #132 REGION ZOOM. The region screen has NO camera and NO view
		// transform - a full decompile of all 197 functions in the module
		// (tools\research\REGION-SCREEN.md) finds zero references to zoom,
		// rotate, angle or yaw. It composites baked thumbnails at a fixed
		// isometric basis. So "zoom" here is OUR mechanism from #131 driven by
		// input: the basis sets pixels-per-cell and the sub_7AE3D0 hook sizes
		// the tiles. Consumed only while the region screen is up, so the city
		// view's own wheel zoom is untouched.
		//
		// RegionZoomOperable() is part of the condition, not just a guard
		// deeper in: IsRegionUp() only says the region tick has run, which is
		// independent of whether the zoom hooks installed. Without this we
		// would SWALLOW the wheel (return 0, DefSubclassProc skipped) in
		// configurations where zoom can never apply, giving the player dead
		// input plus one "0 pristine snapshots" line per gesture.
		if (msg == WM_MOUSEWHEEL && self->settings.spikeRegionZoom &&
			self->uiSpike.IsRegionUp() && CodePatches::RegionZoomOperable())
		{
			const int delta = GET_WHEEL_DELTA_WPARAM(wParam);
			if (delta != 0)
			{
				self->uiSpike.RegionZoomStep(delta > 0 ? +1 : -1);
				return 0; // consumed - do not let the game also act on it
			}
		}

		// Dormant wrapper-path input remap (identity/no-op at native res).
		if (self->remap.IsActive())
		{
			switch (msg)
			{
			case WM_MOUSEMOVE:
			case WM_LBUTTONDOWN: case WM_LBUTTONUP: case WM_LBUTTONDBLCLK:
			case WM_RBUTTONDOWN: case WM_RBUTTONUP: case WM_RBUTTONDBLCLK:
			case WM_MBUTTONDOWN: case WM_MBUTTONUP: case WM_MBUTTONDBLCLK:
			case WM_XBUTTONDOWN: case WM_XBUTTONUP: case WM_XBUTTONDBLCLK:
				return DefSubclassProc(hwnd, msg, wParam,
					self->remap.TransformClientLParam(lParam));

			case WM_MOUSEWHEEL:
			case WM_MOUSEHWHEEL:
				return DefSubclassProc(hwnd, msg, wParam,
					self->remap.TransformScreenLParam(lParam));

			default:
				break;
			}
		}
		if (msg == WM_SIZE)
		{
			self->remap.OnWindowSizeChanged();
		}

		return DefSubclassProc(hwnd, msg, wParam, lParam);
	}

	Settings settings;
	ScaleRemap remap;
	UiSpike uiSpike;
	HWND gameWindow;
	bool subclassed;
	bool tierActive; // resolution tier chose scaling; false = stock, inert
};

cRZCOMDllDirector* RZGetCOMDllDirector()
{
	static SC4UIScaleDllDirector sDirector;
	return &sDirector;
}


