#include "Settings.h"

#define WIN32_LEAN_AND_MEAN
#include <Windows.h>
#include <cstdlib>

namespace
{
	float GetPrivateProfileFloat(
		const wchar_t* section,
		const wchar_t* key,
		float defaultValue,
		const wchar_t* iniPath)
	{
		wchar_t buffer[64] = {};
		GetPrivateProfileStringW(section, key, L"", buffer, 64, iniPath);

		if (buffer[0] == L'\0')
		{
			return defaultValue;
		}

		wchar_t* end = nullptr;
		const double value = wcstod(buffer, &end);
		return (end == buffer) ? defaultValue : static_cast<float>(value);
	}
}

void Settings::Load(const wchar_t* iniPath)
{
	const wchar_t* const kLogging = L"Logging";



	const wchar_t* const kScaling = L"Scaling";
	scalingEnabled = GetPrivateProfileIntW(kScaling, L"Enabled", scalingEnabled ? 1 : 0, iniPath) != 0;
	scalingAutoConfig = GetPrivateProfileIntW(kScaling, L"AutoConfig", scalingAutoConfig ? 1 : 0, iniPath) != 0;
	internalWidth = GetPrivateProfileIntW(kScaling, L"InternalWidth", internalWidth, iniPath);
	internalHeight = GetPrivateProfileIntW(kScaling, L"InternalHeight", internalHeight, iniPath);
	presentWidth = GetPrivateProfileIntW(kScaling, L"PresentWidth", presentWidth, iniPath);
	presentHeight = GetPrivateProfileIntW(kScaling, L"PresentHeight", presentHeight, iniPath);
	hookGetCursorPos = GetPrivateProfileIntW(kScaling, L"HookGetCursorPos", hookGetCursorPos ? 1 : 0, iniPath) != 0;
	hookSetCursorPos = GetPrivateProfileIntW(kScaling, L"HookSetCursorPos", hookSetCursorPos ? 1 : 0, iniPath) != 0;
	hookClipCursor = GetPrivateProfileIntW(kScaling, L"HookClipCursor", hookClipCursor ? 1 : 0, iniPath) != 0;
	hookWindowMetrics = GetPrivateProfileIntW(kScaling, L"HookWindowMetrics", hookWindowMetrics ? 1 : 0, iniPath) != 0;
	logCoordTraffic = GetPrivateProfileIntW(kScaling, L"LogCoordTraffic", logCoordTraffic ? 1 : 0, iniPath) != 0;

	const wchar_t* const kSpike = L"UiSpike";
	spikeDumpTree = GetPrivateProfileIntW(kSpike, L"DumpTree", spikeDumpTree ? 1 : 0, iniPath) != 0;
	spikeLiveDumpMs = GetPrivateProfileIntW(kSpike, L"LiveDumpMs", spikeLiveDumpMs, iniPath);
	{
		wchar_t buffer[32] = {};
		GetPrivateProfileStringW(kSpike, L"ScaleWindowID", L"0", buffer, 32, iniPath);
		spikeScaleWindowId = wcstoul(buffer, nullptr, 0); // base 0: accepts 0x-prefixed hex
	}
	spikeScaleFactor = GetPrivateProfileFloat(kSpike, L"ScaleFactor", spikeScaleFactor, iniPath);
	spikeScaleAll = GetPrivateProfileIntW(kSpike, L"ScaleAll", spikeScaleAll ? 1 : 0, iniPath) != 0;
	spikeScaleRegion = GetPrivateProfileIntW(kSpike, L"ScaleRegion", spikeScaleRegion ? 1 : 0, iniPath) != 0;
	spikeRegionMapScale = GetPrivateProfileFloat(kSpike, L"RegionMapScale", spikeRegionMapScale, iniPath);
	spikeRegionZoom = GetPrivateProfileIntW(kSpike, L"RegionZoom", spikeRegionZoom ? 1 : 0, iniPath) != 0;
	spikeRegionZoomLevels = GetPrivateProfileIntW(kSpike, L"RegionZoomLevels", spikeRegionZoomLevels, iniPath);
	spikeRegionZoomStepRatio = GetPrivateProfileFloat(kSpike, L"RegionZoomStepRatio", spikeRegionZoomStepRatio, iniPath);
	spikeRegionZoomMaxEdge = GetPrivateProfileIntW(kSpike, L"RegionZoomMaxEdge", spikeRegionZoomMaxEdge, iniPath);
	spikeRegionTileSharp = GetPrivateProfileIntW(kSpike, L"RegionTileSharp", spikeRegionTileSharp ? 1 : 0, iniPath) != 0;
	if (spikeRegionZoomLevels < 0) { spikeRegionZoomLevels = 0; }
	if (spikeRegionZoomLevels > 6) { spikeRegionZoomLevels = 6; }
	if (spikeRegionZoomStepRatio < 1.05f) { spikeRegionZoomStepRatio = 1.05f; }
	if (spikeRegionZoomStepRatio > 2.0f) { spikeRegionZoomStepRatio = 2.0f; }
	if (spikeRegionZoomMaxEdge < 256) { spikeRegionZoomMaxEdge = 256; }
	if (spikeRegionZoomMaxEdge > 4096) { spikeRegionZoomMaxEdge = 4096; }
	spikeMenuFlyouts = GetPrivateProfileIntW(kSpike, L"MenuFlyouts", spikeMenuFlyouts ? 1 : 0, iniPath) != 0;
	spikeCenterSmallLeaves = GetPrivateProfileIntW(kSpike, L"CenterSmallLeaves", spikeCenterSmallLeaves ? 1 : 0, iniPath) != 0;
	spikeCenterLeafMaxPx = GetPrivateProfileIntW(kSpike, L"CenterLeafMaxPx", spikeCenterLeafMaxPx, iniPath);
	spikeAutoScale = GetPrivateProfileIntW(kSpike, L"AutoScale", spikeAutoScale ? 1 : 0, iniPath) != 0;
	useScaleRemap = GetPrivateProfileIntW(kScaling, L"UseScaleRemap", useScaleRemap ? 1 : 0, iniPath) != 0;
	spikeSelectorAtStock = GetPrivateProfileIntW(kSpike, L"SelectorAtStock", spikeSelectorAtStock ? 1 : 0, iniPath) != 0;
	spikeRatingArrowPatch = GetPrivateProfileIntW(kSpike, L"RatingArrowPatch", spikeRatingArrowPatch ? 1 : 0, iniPath) != 0;
	spikeRatingArrowAnchor = GetPrivateProfileIntW(kSpike, L"RatingArrowAnchor", spikeRatingArrowAnchor, iniPath);
	spikeMissionBubbleFx = GetPrivateProfileIntW(kSpike, L"MissionBubbleFx", spikeMissionBubbleFx, iniPath);
	spikeMissionBubbleScale = GetPrivateProfileFloat(kSpike, L"MissionBubbleScale", spikeMissionBubbleScale, iniPath);
	spikeTooltipWrapPatch = GetPrivateProfileIntW(kSpike, L"TooltipWrapPatch", spikeTooltipWrapPatch ? 1 : 0, iniPath) != 0;
	spikeCostBoxPatch = GetPrivateProfileIntW(kSpike, L"CostBoxPatch", spikeCostBoxPatch ? 1 : 0, iniPath) != 0;
	spikeParentFrameRounding = GetPrivateProfileIntW(kSpike, L"ParentFrameRounding", spikeParentFrameRounding ? 1 : 0, iniPath) != 0;
	spikeHtmlSizePatch = GetPrivateProfileIntW(kSpike, L"HtmlSizePatch", spikeHtmlSizePatch ? 1 : 0, iniPath) != 0;
	spikeAdviceRowPatch = GetPrivateProfileIntW(kSpike, L"AdviceRowPatch", spikeAdviceRowPatch ? 1 : 0, iniPath) != 0;
	spikeBudgetButtonPatch = GetPrivateProfileIntW(kSpike, L"BudgetButtonPatch", spikeBudgetButtonPatch ? 1 : 0, iniPath) != 0;
	spikeOrdinanceInsetPatch = GetPrivateProfileIntW(kSpike, L"OrdinanceInsetPatch", spikeOrdinanceInsetPatch ? 1 : 0, iniPath) != 0;
	spikeBudgetDeptPatch = GetPrivateProfileIntW(kSpike, L"BudgetDeptPatch", spikeBudgetDeptPatch ? 1 : 0, iniPath) != 0;
	webRedirect = GetPrivateProfileIntW(kSpike, L"WebRedirect", webRedirect ? 1 : 0, iniPath) != 0;
	spikeSpinProbe = GetPrivateProfileIntW(kSpike, L"SpinProbe", spikeSpinProbe, iniPath);
	spikeSpinFix = GetPrivateProfileIntW(kSpike, L"SpinFix", spikeSpinFix, iniPath);
	spikePopupWrap = GetPrivateProfileIntW(kSpike, L"PopupWrap", spikePopupWrap ? 1 : 0, iniPath) != 0;
	spikeShowHook = GetPrivateProfileIntW(kSpike, L"ShowHook", spikeShowHook, iniPath);
	spikeEarlyBake = GetPrivateProfileIntW(kSpike, L"EarlyBake", spikeEarlyBake, iniPath);
	spikeEarlyDock = GetPrivateProfileIntW(kSpike, L"EarlyDock", spikeEarlyDock, iniPath);
	spikeSubFlyoutBorn2x = GetPrivateProfileIntW(kSpike, L"SubFlyoutBorn2x", spikeSubFlyoutBorn2x, iniPath);
	spikeSubFlyoutBornScale = GetPrivateProfileIntW(kSpike, L"SubFlyoutBornScale", spikeSubFlyoutBornScale, iniPath);
	spikeSubFlyoutBornDock = GetPrivateProfileIntW(kSpike, L"SubFlyoutBornDock", spikeSubFlyoutBornDock, iniPath);
	spikeFlyoutBornOnOpen = GetPrivateProfileIntW(kSpike, L"FlyoutBornOnOpen", spikeFlyoutBornOnOpen, iniPath);
	spikeDataViewLegendPatch = GetPrivateProfileIntW(kSpike, L"DataViewLegendPatch", spikeDataViewLegendPatch, iniPath);
	spikeDockDialogs = GetPrivateProfileIntW(kSpike, L"DockDialogs", spikeDockDialogs ? 1 : 0, iniPath) != 0;

	logLevel = GetPrivateProfileIntW(kLogging, L"LogLevel", logLevel, iniPath);
	if (logLevel < 0) { logLevel = 0; }
	if (logLevel > 3) { logLevel = 3; }
}
