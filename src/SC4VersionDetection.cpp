#include "SC4VersionDetection.h"

#define WIN32_LEAN_AND_MEAN
#include <Windows.h>
#include <vector>

#pragma comment(lib, "version.lib")

uint16_t GetGameVersion()
{
	wchar_t exePath[MAX_PATH] = {};
	if (GetModuleFileNameW(nullptr, exePath, MAX_PATH) == 0)
	{
		return 0;
	}

	const DWORD infoSize = GetFileVersionInfoSizeW(exePath, nullptr);
	if (infoSize == 0)
	{
		return 0;
	}

	std::vector<uint8_t> data(infoSize);
	if (!GetFileVersionInfoW(exePath, 0, infoSize, data.data()))
	{
		return 0;
	}

	VS_FIXEDFILEINFO* fixedInfo = nullptr;
	UINT fixedInfoSize = 0;
	if (!VerQueryValueW(data.data(), L"\\", reinterpret_cast<void**>(&fixedInfo), &fixedInfoSize)
		|| fixedInfo == nullptr
		|| fixedInfoSize < sizeof(VS_FIXEDFILEINFO))
	{
		return 0;
	}

	// 1.1.641.0 -> FileVersionLS high word is 641.
	return static_cast<uint16_t>(HIWORD(fixedInfo->dwFileVersionLS));
}
