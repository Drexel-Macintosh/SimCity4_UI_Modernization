#include "WebRedirect.h"
#include "Logger.h"

#define WIN32_LEAN_AND_MEAN
#include <Windows.h>
#include <shellapi.h>

#include "MinHook.h"

#include <cstring>
#include <cwchar>

// The region screen's website button shells out to http://simcity.ea.com/,
// dead since EA retired the site. Redirect any simcity.ea.com URL to the
// living community hub instead. Hooked at ShellExecute so it works no
// matter where the game stores the URL string.
namespace
{
	const char kDeadHostA[] = "simcity.ea.com";
	const wchar_t kDeadHostW[] = L"simcity.ea.com";
	const char kTargetA[] = "https://community.simtropolis.com/";
	const wchar_t kTargetW[] = L"https://community.simtropolis.com/";

	typedef HINSTANCE(WINAPI* ShellExecuteAFn)(
		HWND, LPCSTR, LPCSTR, LPCSTR, LPCSTR, INT);
	typedef HINSTANCE(WINAPI* ShellExecuteWFn)(
		HWND, LPCWSTR, LPCWSTR, LPCWSTR, LPCWSTR, INT);

	ShellExecuteAFn realShellExecuteA = nullptr;
	ShellExecuteWFn realShellExecuteW = nullptr;

	bool ContainsDeadHostA(LPCSTR s)
	{
		if (!s)
		{
			return false;
		}
		// Case-insensitive substring search.
		const size_t n = strlen(s);
		const size_t m = sizeof(kDeadHostA) - 1;
		for (size_t i = 0; i + m <= n; i++)
		{
			if (_strnicmp(s + i, kDeadHostA, m) == 0)
			{
				return true;
			}
		}
		return false;
	}

	bool ContainsDeadHostW(LPCWSTR s)
	{
		if (!s)
		{
			return false;
		}
		const size_t n = wcslen(s);
		const size_t m = (sizeof(kDeadHostW) / sizeof(wchar_t)) - 1;
		for (size_t i = 0; i + m <= n; i++)
		{
			if (_wcsnicmp(s + i, kDeadHostW, m) == 0)
			{
				return true;
			}
		}
		return false;
	}

	HINSTANCE WINAPI HookShellExecuteA(
		HWND hwnd, LPCSTR op, LPCSTR file, LPCSTR params, LPCSTR dir, INT show)
	{
		if (ContainsDeadHostA(file))
		{
			Logger::Get().WriteLine(
				LogLevel::Info,
				"WebRedirect: '%s' -> '%s'.", file, kTargetA);
			file = kTargetA;
		}
		return realShellExecuteA(hwnd, op, file, params, dir, show);
	}

	HINSTANCE WINAPI HookShellExecuteW(
		HWND hwnd, LPCWSTR op, LPCWSTR file, LPCWSTR params, LPCWSTR dir, INT show)
	{
		if (ContainsDeadHostW(file))
		{
			Logger::Get().WriteLine(
				LogLevel::Info, "WebRedirect: dead EA URL -> Simtropolis (W).");
			file = kTargetW;
		}
		return realShellExecuteW(hwnd, op, file, params, dir, show);
	}
}

namespace WebRedirect
{
	void Install()
	{
		// MinHook may already be initialized by ScaleRemap; tolerate that.
		const MH_STATUS init = MH_Initialize();
		if (init != MH_OK && init != MH_ERROR_ALREADY_INITIALIZED)
		{
			Logger::Get().WriteLine(
				LogLevel::Info, "WebRedirect: MinHook init failed (%d).", init);
			return;
		}

		HMODULE shell32 = LoadLibraryW(L"shell32.dll");
		if (!shell32)
		{
			return;
		}

		int hooked = 0;
		if (MH_CreateHook(
			reinterpret_cast<LPVOID>(GetProcAddress(shell32, "ShellExecuteA")),
			reinterpret_cast<LPVOID>(&HookShellExecuteA),
			reinterpret_cast<LPVOID*>(&realShellExecuteA)) == MH_OK)
		{
			hooked++;
		}
		if (MH_CreateHook(
			reinterpret_cast<LPVOID>(GetProcAddress(shell32, "ShellExecuteW")),
			reinterpret_cast<LPVOID>(&HookShellExecuteW),
			reinterpret_cast<LPVOID*>(&realShellExecuteW)) == MH_OK)
		{
			hooked++;
		}
		MH_ApplyQueued();
		if (MH_EnableHook(MH_ALL_HOOKS) == MH_OK && hooked > 0)
		{
			Logger::Get().WriteLine(
				LogLevel::Info,
				"WebRedirect: %d ShellExecute hook(s) active (simcity.ea.com -> simtropolis).",
				hooked);
		}
	}
}
