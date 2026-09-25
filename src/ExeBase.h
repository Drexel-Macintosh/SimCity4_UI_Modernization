#pragma once
#include <Windows.h>
#include <cstdint>

// The exe's load address, read once (audit B7, 2026-09-25).
//
// 71 sites in CodePatches, UiSpike and ScaleTier each called
// GetModuleHandleW(nullptr) to rebase a fixed VA against the exe's image base
// (0x400000; its relocations are stripped). The value cannot change while the
// process runs, so one read is exact. The static is constant-initialized, so
// there is no thread-safe-static guard; the lazy store is a benign race, as
// every thread stores the same value.
inline uintptr_t ExeBase()
{
	static uintptr_t s_base = 0;
	if (!s_base)
	{
		s_base = reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
	}
	return s_base;
}
