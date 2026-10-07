#pragma once
#include <cstdint>

// The cIUIScaleInfo service (api/cIUIScaleInfo.h): what this DLL is doing to the
// UI, for other plugin DLLs. One static object, registered with the game's COM
// by class ID; the director publishes the values the moment it has decided them.
namespace UIScaleInfo
{
	// The FactoryFunctionPtr2 the director hands to AddCls. Hands out the one
	// static object; counts lookups and logs refusals (budgeted).
	bool Factory(uint32_t iid, void** ppvObj);

	// The session's decision, from the tier tail of the constructor. Until this
	// runs (and on an unsupported game build, where it is never reached) the
	// object answers 1.0 / not auto - the truth for a DLL that scales nothing.
	void Publish(uint32_t modVersion, float uiFactor, bool autoScale);

	// POSITIVE CONTROL, run once at PostAppInit: look the class up through the
	// GAME's COM - the exact path another DLL takes - and check what comes back
	// against rulers that do NOT go through Publish: the UI factor the geometry
	// patches are gated on, the session's AutoScale, and the region basis float
	// measured in the exe (pass a negative regionMeasured when it cannot be
	// read). A mismatch is logged as an error, never as a healthy line.
	void SelfCheck(float appliedUi, bool appliedAuto, float regionMeasured);
}
