#pragma once
#include <cstdint>

// Returns the SC4 build number from the host exe's version resource
// (1.1.641.0 -> 641), or 0 if it cannot be determined.
uint16_t GetGameVersion();
