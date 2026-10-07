#define WIN32_LEAN_AND_MEAN
#include <Windows.h>

#include "UIScaleInfo.h"

#include "../api/cIUIScaleInfo.h"
#include "cIGZCOM.h"
#include "cIGZFrameWork.h"
#include "cRZCOMDllDirector.h"

#include "CodePatches.h"
#include "Logger.h"

#include <cstdio>

namespace
{
	volatile uint32_t gModVersion = 0;
	volatile float gUiFactor = 1.0f;
	volatile bool gAutoScale = false;

	volatile LONG gLookups = 0;      // every Factory call, ours included
	volatile LONG gRefusedLogged = 0;
	const LONG kRefusedLogMax = 8;
	volatile bool gQuietRefusal = false;   // the self-check's own negative probe

	// STATIC LIFETIME. The count is kept so AddRef/Release answer like any
	// other GZCOM object, but nothing is ever deleted: a caller that releases
	// one time too many must not be able to free an object other DLLs hold.
	// What this does NOT cover is process exit: the game FreeLibrary's every
	// plugin in path order without asking, so a pointer another DLL still holds
	// when ours is unloaded points into unmapped code. api\README.md tells
	// callers to release by their PreAppShutdown (adversarial review 2026-10-07).
	class UIScaleInfoImpl final : public cIUIScaleInfo
	{
	public:
		bool QueryInterface(uint32_t riid, void** ppvObj) override
		{
			if (!ppvObj) { return false; }
			if (riid == GZIID_cIUIScaleInfo)
			{
				*ppvObj = static_cast<cIUIScaleInfo*>(this);
			}
			else if (riid == GZIID_cIGZUnknown)
			{
				*ppvObj = static_cast<cIGZUnknown*>(this);
			}
			else
			{
				*ppvObj = nullptr;
				return false;
			}
			AddRef();
			return true;
		}

		uint32_t AddRef() override
		{
			return static_cast<uint32_t>(InterlockedIncrement(&refs));
		}

		uint32_t Release() override
		{
			const LONG n = InterlockedDecrement(&refs);
			return n > 0 ? static_cast<uint32_t>(n) : 0;
		}

		uint32_t GetModVersion() override { return gModVersion; }

		float GetUIScaleFactor() override { return gUiFactor; }

		bool IsAutoScale() override { return gAutoScale; }

		float GetRegionMapScale() override
		{
			// The factor CodePatches last WROTE into the region basis - the
			// number the tiles are laid out with, zoom and rollbacks included -
			// not a value recomputed from settings that could disagree with it.
			const float f = CodePatches::RegionIsoLiveFactor();
			return f > 0.0f ? f : 1.0f;
		}

	private:
		volatile LONG refs = 1;   // the static object's own reference
	};

	UIScaleInfoImpl gInfo;
}

namespace UIScaleInfo
{
	bool Factory(uint32_t iid, void** ppvObj)
	{
		InterlockedIncrement(&gLookups);
		if (gInfo.QueryInterface(iid, ppvObj))
		{
			return true;
		}
		// A refusal is the one answer a caller cannot diagnose from its side
		// (a typo'd IID looks exactly like "mod not installed"), so it is
		// logged, with the IID, up to a budget.
		if (!gQuietRefusal
			&& InterlockedIncrement(&gRefusedLogged) <= kRefusedLogMax)
		{
			Logger::Get().WriteLine(LogLevel::Info,
				"API: cIUIScaleInfo lookup REFUSED - IID 0x%08X is not one this "
				"class answers (it answers 0x%08X cIUIScaleInfo and 0x%08X "
				"cIGZUnknown).", iid, GZIID_cIUIScaleInfo, GZIID_cIGZUnknown);
		}
		return false;
	}

	void Publish(uint32_t modVersion, float uiFactor, bool autoScale)
	{
		gModVersion = modVersion;
		gUiFactor = uiFactor > 0.0f ? uiFactor : 1.0f;
		gAutoScale = autoScale;
	}

	void SelfCheck(float appliedUi, bool appliedAuto, float regionMeasured)
	{
		Logger& logger = Logger::Get();
		cIGZFrameWork* fw = RZGetFrameWork();
		cIGZCOM* com = fw ? fw->GetCOMObject() : nullptr;
		if (!com)
		{
			logger.WriteLine(LogLevel::Error,
				"API: cIUIScaleInfo self-check could not reach the game's COM "
				"object - no verdict.");
			return;
		}

		const LONG before = gLookups;
		cIUIScaleInfo* p = nullptr;
		const bool ok = com->GetClassObject(GZCLSID_cIUIScaleInfo,
			GZIID_cIUIScaleInfo, reinterpret_cast<void**>(&p)) && p != nullptr;
		// The lookup has to have come through OUR factory: an answer from
		// anywhere else (another DLL registering the same CLSID) would make
		// every number below someone else's.
		const bool viaUs = gLookups != before;
		if (!ok || !viaUs)
		{
			logger.WriteLine(LogLevel::Error,
				"API: cIUIScaleInfo (CLSID 0x%08X) is NOT reachable through the "
				"game's COM (%s) - other DLLs cannot ask for the scale.",
				GZCLSID_cIUIScaleInfo,
				!ok ? "GetClassObject returned false"
				    : "answered by a different factory");
			if (p) { p->Release(); }
			return;
		}

		// NEGATIVE CONTROL: an IID this class does not implement must be
		// refused, or a caller asking for a future interface would be handed
		// this vtable and call past its end.
		void* wrong = nullptr;
		gQuietRefusal = true;
		const bool wrongRefused = !com->GetClassObject(GZCLSID_cIUIScaleInfo,
			GZIID_cIUIScaleInfo ^ 0x1u, &wrong);
		gQuietRefusal = false;
		if (wrong) { static_cast<cIGZUnknown*>(wrong)->Release(); }

		const uint32_t v = p->GetModVersion();
		const float ui = p->GetUIScaleFactor();
		const bool autoScale = p->IsAutoScale();
		const float region = p->GetRegionMapScale();
		logger.WriteLine(LogLevel::Info,
			"API: cIUIScaleInfo answered through the game's COM (CLSID 0x%08X, "
			"IID 0x%08X): version %u.%u.%u, UI factor %.2f (%s), region map "
			"%.2f. Unknown IID refused: %s.",
			GZCLSID_cIUIScaleInfo, GZIID_cIUIScaleInfo,
			(v >> 16) & 0xFFu, (v >> 8) & 0xFFu, v & 0xFFu,
			ui, autoScale ? "auto" : "manual",
			region, wrongRefused ? "yes" : "NO - DEFECT");
		p->Release();

		// THE VALUES, not just the reachability (adversarial review
		// 2026-10-07, finding 3): every ruler below is independent of Publish,
		// so a deleted or mis-fed Publish reads as a MISMATCH here instead of a
		// healthy "UI factor 1.00" line.
		const auto closeTo = [](float a, float b) {
			const float d = a - b;
			return d < 0.001f && d > -0.001f;
		};
		const bool uiOk = closeTo(ui, appliedUi);
		const bool autoOk = autoScale == appliedAuto;
		const bool regionOk = regionMeasured < 0.0f || closeTo(region, regionMeasured);
		char regionText[64] = {};
		if (regionMeasured < 0.0f)
		{
			sprintf_s(regionText, "not measurable on this build");
		}
		else
		{
			sprintf_s(regionText, "%s (basis measured x%.3f)",
				regionOk ? "yes" : "NO", regionMeasured);
		}
		logger.WriteLine((uiOk && autoOk && regionOk) ? LogLevel::Info : LogLevel::Error,
			"API: %s this session - UI factor %s (geometry gate applies %.2f), "
			"auto %s, region %s.",
			(uiOk && autoOk && regionOk) ? "the answers MATCH"
			                             : "the answers DO NOT MATCH",
			uiOk ? "yes" : "NO", appliedUi, autoOk ? "yes" : "NO", regionText);
	}
}
