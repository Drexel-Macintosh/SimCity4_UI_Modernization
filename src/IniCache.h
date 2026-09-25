#pragma once
// PARSE THE INI ONCE (audit B8, 2026-09-25).
//
// About 90 reads of SC4UIScale.ini went through GetPrivateProfileString/Int,
// and every one of them re-opened and re-parsed the whole file. These are
// drop-in replacements with the same arguments and the same results: the
// file is parsed once per version (a changed write time or size re-reads it,
// so an edit made while the game runs is still seen, as before), and every
// lookup is answered from that parse under the profile API's own rules
// (IniParse.h). tools/dev/inicache/run_inicache_parity.py checks them
// against the real API.
//
// Every profile WRITE goes through WriteStringW, which drops the cached
// parse of that file, so a read after our own write can never be stale.
//
// Not replaced: GetPrivateProfileSectionW. The BOM check in ScaleTier tests
// what Windows itself makes of the file, and the dev-key roll-up enumerates
// [Probe] once at boot; both stay on the real API.
//
// Settings::Load keeps the vendored IniReader (v4.0.7, the ecosystem parser),
// and SC4GraphicsOptions.ini is parsed with IniReader too, because the DLL
// that owns that file uses it.
#include <cstdint>

namespace IniCache
{
	// GetPrivateProfileIntW
	uint32_t ReadIntW(const wchar_t* section, const wchar_t* key, int def,
		const wchar_t* path);
	// GetPrivateProfileStringW (section and key must not be null)
	unsigned long ReadStringW(const wchar_t* section, const wchar_t* key,
		const wchar_t* def, wchar_t* out, unsigned long size, const wchar_t* path);
	// GetPrivateProfileStringA: arguments and result in the ANSI code page
	unsigned long ReadStringA(const char* section, const char* key,
		const char* def, char* out, unsigned long size, const char* path);
	// WritePrivateProfileStringW, then the cached parse of `path` is dropped.
	int WriteStringW(const wchar_t* section, const wchar_t* key,
		const wchar_t* value, const wchar_t* path);
	// Drop the cached parse of `path` (a file written some other way).
	void Invalidate(const wchar_t* path);
}
