#pragma once
#include <cstdint>

// Oldest game build this DLL will install into. Everything below it (638,
// 640, ...) predates the address layout every patch here targets, so those
// are refused outright. 0 means "could not be determined" and is refused too.
constexpr uint16_t kMinSupportedGameVersion = 641;

// Newest game build verified by hand. Builds ABOVE the minimum still run -
// the verify-before-write law makes each patch decline individually if its
// site moved - but the log names them as untested. Bump when a new build is
// certified.
constexpr uint16_t kTestedGameVersion = 641;

// Returns the SC4 build number from the host exe's version resource
// (1.1.641.0 -> 641), or 0 if it cannot be determined.
uint16_t GetGameVersion();
