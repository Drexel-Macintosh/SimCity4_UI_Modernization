#include "WebRedirect.h"
#include "Logger.h"
#include "ScaleTier.h"

#define WIN32_LEAN_AND_MEAN
#include <Windows.h>
#include <shellapi.h>

#include "Logger.h"
#include "MinHook.h"

#include <cstring>
#include <cwchar>
#include <cwctype>
#include <filesystem>
#include <string>

extern "C" IMAGE_DOS_HEADER __ImageBase;

// The region screen's website button shells out to http://simcity.ea.com/,
// dead since EA retired the site. Two behaviours, decided by whether the
// cyclone-boom "Web Button Improvement Mod" (Option A, "Click Prevented") is
// installed:
//   * ABSENT  - the button stays live and we redirect any simcity.ea.com URL
//               to the living community hub (this DLL's standard dead-link
//               fix).
//   * PRESENT - the mod owns the button; a click must do NOTHING - no browser
//               AND no minimize. The real mechanism is the mod's own inert
//               WebButtonUI .ui (website-button id cleared to 0), which we
//               re-ship per tier in the mod-gated z_SC4UIScale_WebButtonUI
//               package so it also wins at scaled factors (the SelectiveArt
//               dat carries a live-id copy). Because the id is cleared, the
//               game's web-launch routine never runs, so there is nothing to
//               block or restore. The ShellExecute hook below is only a
//               backstop for that case, plus the redirect when absent.
namespace
{
	const char kDeadHostA[] = "simcity.ea.com";
	const wchar_t kDeadHostW[] = L"simcity.ea.com";
	const char kTargetA[] = "https://community.simtropolis.com/";
	const wchar_t kTargetW[] = L"https://community.simtropolis.com/";

	bool g_blockDeadEa = false;

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

	// "Is this a web URL of any kind?" The game keyed the region website
	// button on its control id (0x4A779A1A); our scaled tiers carry a live
	// button, so when the Web Button Improvement Mod is absent the click MUST
	// still fire (and be redirected). When the mod IS present its intent is
	// 'click does nothing' - block ANY web URL, not just simcity.ea.com, so a
	// scaled-tier button can never leak a browser launch on some other host.
	bool LooksLikeWebUrlA(LPCSTR s)
	{
		if (!s) { return false; }
		return _strnicmp(s, "http://", 7) == 0
			|| _strnicmp(s, "https://", 8) == 0
			|| _strnicmp(s, "www.", 4) == 0;
	}

	bool LooksLikeWebUrlW(LPCWSTR s)
	{
		if (!s) { return false; }
		return _wcsnicmp(s, L"http://", 7) == 0
			|| _wcsnicmp(s, L"https://", 8) == 0
			|| _wcsnicmp(s, L"www.", 4) == 0;
	}

	HINSTANCE WINAPI HookShellExecuteA(
		HWND hwnd, LPCSTR op, LPCSTR file, LPCSTR params, LPCSTR dir, INT show)
	{
		const bool dead = ContainsDeadHostA(file);
		const bool anyWeb = g_blockDeadEa && LooksLikeWebUrlA(file);
		if (dead || anyWeb)
		{
			if (g_blockDeadEa)
			{
				Logger::Get().WriteLine(
					LogLevel::Info,
					"WebRedirect: '%s' BLOCKED (Web Button Improvement Mod "
					"owns the button; click does nothing).", file);
				return reinterpret_cast<HINSTANCE>(static_cast<INT_PTR>(42));
			}
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
		const bool dead = ContainsDeadHostW(file);
		const bool anyWeb = g_blockDeadEa && LooksLikeWebUrlW(file);
		if (dead || anyWeb)
		{
			if (g_blockDeadEa)
			{
				Logger::Get().WriteLine(
					LogLevel::Info,
					"WebRedirect: web URL BLOCKED (Web Button Improvement Mod "
					"owns the button; click does nothing).");
				return reinterpret_cast<HINSTANCE>(static_cast<INT_PTR>(42));
			}
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
		// Decide the behaviour from the mod's presence, once. ONE detector:
		// ScaleTier's two-root version (Documents Plugins + install Plugins).
		// This file used to carry its own one-root twin, and the two
		// DISAGREED whenever the mod sat in the install root - WebText stood
		// down while the redirect stayed armed, the exact split ScaleTier's
		// comment says must not happen.
		wchar_t docPlugins[MAX_PATH] = {};
		ScaleTier::GetPluginsRootW(docPlugins, MAX_PATH);
		g_blockDeadEa = ScaleTier::WebButtonModPresent(docPlugins);

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
				"WebRedirect: %d ShellExecute hook(s) active (%s).",
				hooked,
				g_blockDeadEa
					? "BLOCK dead EA URL - Web Button Improvement Mod present"
					: "simcity.ea.com -> simtropolis");
		}
	}
}
