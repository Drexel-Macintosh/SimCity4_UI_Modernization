#include "Settings.h"

// sc4-dll-utilities (0xC0000054) - the ecosystem INI parser, vendored under
// vendor\sc4-dll-utilities (LGPL-2.1, see that folder's LICENSE.txt). Replaces
// the GetPrivateProfile* family so parsing matches the wider SC4 DLL ecosystem.
#include "IniReader.h"

#include <filesystem>
#include <optional>

void Settings::Load(const wchar_t* iniPath)
{
	// Parse once. Section/key names are case-insensitive, ';' lines are
	// comments. If the file is missing or unparseable we keep the member
	// defaults (same contract as GetPrivateProfile's defaults).
	std::optional<IniReader> reader;
	try
	{
		reader.emplace(std::filesystem::path(iniPath));
	}
	catch (const std::exception&)
	{
		reader.reset();
	}

	const std::optional<IniSection> scaling =
		reader ? reader->get_section_optional("Scaling") : std::nullopt;
	const std::optional<IniSection> spike =
		reader ? reader->get_section_optional("UiSpike") : std::nullopt;
	const std::optional<IniSection> logging =
		reader ? reader->get_section_optional("Logging") : std::nullopt;

	auto gi = [](const std::optional<IniSection>& s, const char* key, int def)
	{
		return s ? s->get_converted_value<int>(key, def) : def;
	};
	auto gu = [](const std::optional<IniSection>& s, const char* key, unsigned int def)
	{
		return s ? s->get_converted_value<uint32_t>(key, def) : def;
	};
	auto gf = [](const std::optional<IniSection>& s, const char* key, float def)
	{
		return s ? s->get_converted_value<float>(key, def) : def;
	};

	scalingEnabled = gi(scaling, "Enabled", scalingEnabled ? 1 : 0) != 0;
	scalingAutoConfig = gi(scaling, "AutoConfig", scalingAutoConfig ? 1 : 0) != 0;
	internalWidth = gi(scaling, "InternalWidth", internalWidth);
	internalHeight = gi(scaling, "InternalHeight", internalHeight);
	presentWidth = gi(scaling, "PresentWidth", presentWidth);
	presentHeight = gi(scaling, "PresentHeight", presentHeight);
	hookGetCursorPos = gi(scaling, "HookGetCursorPos", hookGetCursorPos ? 1 : 0) != 0;
	hookSetCursorPos = gi(scaling, "HookSetCursorPos", hookSetCursorPos ? 1 : 0) != 0;
	hookClipCursor = gi(scaling, "HookClipCursor", hookClipCursor ? 1 : 0) != 0;
	hookWindowMetrics = gi(scaling, "HookWindowMetrics", hookWindowMetrics ? 1 : 0) != 0;
	logCoordTraffic = gi(scaling, "LogCoordTraffic", logCoordTraffic ? 1 : 0) != 0;

	spikeDumpTree = gi(spike, "DumpTree", spikeDumpTree ? 1 : 0) != 0;
	spikeLiveDumpMs = gu(spike, "LiveDumpMs", spikeLiveDumpMs);
	// base 16 accepted (0x-prefixed), matching the old wcstoul(...,0) behaviour.
	spikeScaleWindowId = gu(spike, "ScaleWindowID", spikeScaleWindowId);
	spikeScaleFactor = gf(spike, "ScaleFactor", spikeScaleFactor);
	spikeScaleAll = gi(spike, "ScaleAll", spikeScaleAll ? 1 : 0) != 0;
	spikeScaleRegion = gi(spike, "ScaleRegion", spikeScaleRegion ? 1 : 0) != 0;
	spikeRegionMapScale = gf(spike, "RegionMapScale", spikeRegionMapScale);
	spikeRegionZoom = gi(spike, "RegionZoom", spikeRegionZoom ? 1 : 0) != 0;
	spikeRegionZoomLevels = gi(spike, "RegionZoomLevels", spikeRegionZoomLevels);
	spikeRegionZoomStepRatio = gf(spike, "RegionZoomStepRatio", spikeRegionZoomStepRatio);
	spikeRegionZoomMaxEdge = gi(spike, "RegionZoomMaxEdge", spikeRegionZoomMaxEdge);
	spikeRegionTileSharp = gi(spike, "RegionTileSharp", spikeRegionTileSharp ? 1 : 0) != 0;
	if (spikeRegionZoomLevels < 0) { spikeRegionZoomLevels = 0; }
	if (spikeRegionZoomLevels > 6) { spikeRegionZoomLevels = 6; }
	if (spikeRegionZoomStepRatio < 1.05f) { spikeRegionZoomStepRatio = 1.05f; }
	if (spikeRegionZoomStepRatio > 2.0f) { spikeRegionZoomStepRatio = 2.0f; }
	if (spikeRegionZoomMaxEdge < 256) { spikeRegionZoomMaxEdge = 256; }
	if (spikeRegionZoomMaxEdge > 4096) { spikeRegionZoomMaxEdge = 4096; }
	spikeMenuFlyouts = gi(spike, "MenuFlyouts", spikeMenuFlyouts ? 1 : 0) != 0;
	spikeCenterSmallLeaves = gi(spike, "CenterSmallLeaves", spikeCenterSmallLeaves ? 1 : 0) != 0;
	spikeCenterLeafMaxPx = gi(spike, "CenterLeafMaxPx", spikeCenterLeafMaxPx);
	spikeAutoScale = gi(spike, "AutoScale", spikeAutoScale ? 1 : 0) != 0;
	useScaleRemap = gi(scaling, "UseScaleRemap", useScaleRemap ? 1 : 0) != 0;
	spikeSelectorAtStock = gi(spike, "SelectorAtStock", spikeSelectorAtStock ? 1 : 0) != 0;
	spikeRatingArrowPatch = gi(spike, "RatingArrowPatch", spikeRatingArrowPatch ? 1 : 0) != 0;
	spikeRatingArrowAnchor = gi(spike, "RatingArrowAnchor", spikeRatingArrowAnchor);
	spikeMissionBubbleFx = gi(spike, "MissionBubbleFx", spikeMissionBubbleFx);
	spikeMissionBubbleScale = gf(spike, "MissionBubbleScale", spikeMissionBubbleScale);
	spikeTooltipWrapPatch = gi(spike, "TooltipWrapPatch", spikeTooltipWrapPatch ? 1 : 0) != 0;
	spikeCostBoxPatch = gi(spike, "CostBoxPatch", spikeCostBoxPatch ? 1 : 0) != 0;
	spikeParentFrameRounding = gi(spike, "ParentFrameRounding", spikeParentFrameRounding ? 1 : 0) != 0;
	spikeHtmlSizePatch = gi(spike, "HtmlSizePatch", spikeHtmlSizePatch ? 1 : 0) != 0;
	spikeAdviceRowPatch = gi(spike, "AdviceRowPatch", spikeAdviceRowPatch ? 1 : 0) != 0;
	spikeBudgetButtonPatch = gi(spike, "BudgetButtonPatch", spikeBudgetButtonPatch ? 1 : 0) != 0;
	spikeOrdinanceInsetPatch = gi(spike, "OrdinanceInsetPatch", spikeOrdinanceInsetPatch ? 1 : 0) != 0;
	spikeBudgetDeptPatch = gi(spike, "BudgetDeptPatch", spikeBudgetDeptPatch ? 1 : 0) != 0;
	webRedirect = gi(spike, "WebRedirect", webRedirect ? 1 : 0) != 0;
	spikeSpinProbe = gi(spike, "SpinProbe", spikeSpinProbe);
	spikeSpinFix = gi(spike, "SpinFix", spikeSpinFix);
	spikePopupWrap = gi(spike, "PopupWrap", spikePopupWrap ? 1 : 0) != 0;
	spikeShowHook = gi(spike, "ShowHook", spikeShowHook);
	spikeEarlyBake = gi(spike, "EarlyBake", spikeEarlyBake);
	spikeEarlyDock = gi(spike, "EarlyDock", spikeEarlyDock);
	spikeSubFlyoutBorn2x = gi(spike, "SubFlyoutBorn2x", spikeSubFlyoutBorn2x);
	spikeSubFlyoutBornScale = gi(spike, "SubFlyoutBornScale", spikeSubFlyoutBornScale);
	spikeSubFlyoutBornDock = gi(spike, "SubFlyoutBornDock", spikeSubFlyoutBornDock);
	spikeFlyoutBornOnOpen = gi(spike, "FlyoutBornOnOpen", spikeFlyoutBornOnOpen);
	spikeRestoreToolbarsPatch = gi(spike, "RestoreToolbarsPatch", spikeRestoreToolbarsPatch);
	spikeDataViewLegendPatch = gi(spike, "DataViewLegendPatch", spikeDataViewLegendPatch);
	spikeDockDialogs = gi(spike, "DockDialogs", spikeDockDialogs ? 1 : 0) != 0;

	logLevel = gi(logging, "LogLevel", logLevel);
	if (logLevel < 0) { logLevel = 0; }
	if (logLevel > 3) { logLevel = 3; }
}
