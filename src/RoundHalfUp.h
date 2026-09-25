#pragma once
#include <cmath>
#include <cstdint>

// Round-half-up (floor(v + 0.5)) - the SAME rounding rule as the whole art
// pipeline (Upscale2x.exe dimensions, the .UI builders' scale_len), so
// runtime geometry and shipped art can never disagree by a rounding rule
// (law 89). NOTE: differs from llround/ScaleRound only at NEGATIVE half
// values (-49.5 -> -49 here, -50 there); the art pipeline convention wins
// for all tier-math forms.
//
// ONE DEFINITION (audit B9, 2026-09-25). UiSpike.cpp had this one;
// ScaleTier.cpp's icon code had its own RoundHalfUp(float), a truncating
// (int)(v + 0.5f), and several UiSpike sites rounded with lround or
// (int)(x * m + 0.5f). On the non-negative sizes all of them round, those
// agree with this one bit for bit - checked for every float in [0, 2^20):
// the single exception is 0.49999997, which the float add rounds up to 1
// and which no size of at least 1 pixel can produce.
inline int32_t RoundHalfUp(double v)
{
	return static_cast<int32_t>(std::floor(v + 0.5));
}
