// cIUIScaleInfo - ask SC4UIScale what it is doing to the UI.
//
// Public interface of the SC4UIScale DLL (https://github.com/Drexel-Macintosh/
// SimCity4_UI_Modernization), for other GZCOM plugin DLLs. Copy this header into
// your project; it needs only the gzcom-dll headers. No rights reserved.
//
// Getting it (any time from your director's PostAppInit on - every plugin DLL is
// loaded by then):
//
//     cIUIScaleInfo* pInfo = nullptr;
//     if (RZGetFrameWork()->GetCOMObject()->GetClassObject(
//             GZCLSID_cIUIScaleInfo, GZIID_cIUIScaleInfo,
//             reinterpret_cast<void**>(&pInfo)))
//     {
//         const float f = pInfo->GetUIScaleFactor();
//         pInfo->Release();
//     }
//     // false: SC4UIScale is not installed (or older than 4.11.0) - use 1.0.
//
// Look it up when you need it and release it straight away. Never hold the
// pointer past your director's PreAppShutdown: at exit the game unloads every
// plugin DLL in path order, and a pointer held past SC4UIScale's unload points
// at code that is gone.
//
// THE CONTRACT IS FROZEN. The methods below, their order and their meaning never
// change. Anything new goes in a new interface with a new IID, so a DLL built
// against this header keeps working with every later SC4UIScale.
#pragma once
#include "cIGZUnknown.h"

static const uint32_t GZCLSID_cIUIScaleInfo = 0xB54643B5;
static const uint32_t GZIID_cIUIScaleInfo = 0xA9885499;

class cIUIScaleInfo : public cIGZUnknown
{
public:
	// The SC4UIScale version as (major << 16) | (minor << 8) | patch:
	// 0x040B00 is 4.11.0.
	virtual uint32_t GetModVersion() = 0;

	// The factor SC4UIScale enlarges the game's UI by in this session: 1.0 when it
	// is not scaling (the stock tier, an unsupported game build, or scaling turned
	// off), otherwise the tier: 1.5, 2.0 or 3.0 today (treat it as any float).
	// Fixed for the whole session - a new tier takes effect only after a restart.
	//
	// A length of L stock pixels is drawn as floor(L * factor + 0.5) pixels; use
	// the same rounding and your windows line up with the game's.
	virtual float GetUIScaleFactor() = 0;

	// true when the factor was picked automatically from the render resolution,
	// false when the player set it by hand.
	virtual bool IsAutoScale() = 0;

	// The region view's map scale right now: screen pixels per stock pixel of the
	// region map, the player's region zoom included. One region cell, 128 pixels
	// wide in the stock game, is 128 * this wide on screen. 1.0 when SC4UIScale
	// does not scale the region view. First set during SC4UIScale's own
	// PostAppInit (which may run after yours) and changed by the mouse-wheel
	// zoom, so read it each time you lay something out on the region view.
	virtual float GetRegionMapScale() = 0;
};
