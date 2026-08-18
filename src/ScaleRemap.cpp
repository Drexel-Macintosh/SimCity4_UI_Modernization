#include "ScaleRemap.h"

#include "Logger.h"
#include "MinHook.h"

#include <intrin.h>

ScaleRemap* ScaleRemap::instance = nullptr;
void* ScaleRemap::gameModuleBase = nullptr;
size_t ScaleRemap::gameModuleSize = 0;

ScaleRemap::ScaleRemap(const Settings& settings)
	: settings(settings)
	, hwnd(nullptr)
	, internalW(0)
	, internalH(0)
	, metricsActive(false)
	, active(false)
	, hooksInstalled(false)
	, minhookReady(false)
	, hookedTargets{}
	, hookedTargetCount(0)
	, scaleX(1.0f)
	, scaleY(1.0f)
	, offsetX(0)
	, offsetY(0)
	, realGetCursorPos(nullptr)
	, realSetCursorPos(nullptr)
	, realClipCursor(nullptr)
	, realGetSystemMetrics(nullptr)
	, realGetDeviceCaps(nullptr)
	, realGetClientRect(nullptr)
	, realGetWindowRect(nullptr)
	, realSetWindowPos(nullptr)
	, realMoveWindow(nullptr)
{
	instance = this;

	// The game module's address range, for return-address caller filtering.
	HMODULE exe = GetModuleHandleW(nullptr);
	gameModuleBase = exe;
	if (exe)
	{
		const IMAGE_DOS_HEADER* dos = reinterpret_cast<const IMAGE_DOS_HEADER*>(exe);
		const IMAGE_NT_HEADERS* nt = reinterpret_cast<const IMAGE_NT_HEADERS*>(
			reinterpret_cast<const uint8_t*>(exe) + dos->e_lfanew);
		gameModuleSize = nt->OptionalHeader.SizeOfImage;
	}
}

ScaleRemap::~ScaleRemap()
{
	Uninstall();
	instance = nullptr;
}

bool ScaleRemap::CallerIsGameModule(void* returnAddress)
{
	return gameModuleBase != nullptr
		&& returnAddress >= gameModuleBase
		&& returnAddress < static_cast<uint8_t*>(gameModuleBase) + gameModuleSize;
}

bool ScaleRemap::ComputeTransform()
{
	RECT client = {};
	if (!hwnd || !GetClientRect(hwnd, &client))
	{
		return false;
	}

	const LONG clientW = client.right - client.left;
	const LONG clientH = client.bottom - client.top;

	if (internalW <= 0 || internalH <= 0 || clientW <= 0 || clientH <= 0)
	{
		return false;
	}

	if (clientW == internalW && clientH == internalH)
	{
		// Identity: presentation matches the internal frame (no wrapper
		// scaling, or a small panel like the table). Remap not needed.
		scaleX = scaleY = 1.0f;
		offsetX = offsetY = 0;
		return false;
	}

	// The wrapper maintains aspect ratio: uniform scale, centered letterbox.
	const float sx = static_cast<float>(clientW) / static_cast<float>(internalW);
	const float sy = static_cast<float>(clientH) / static_cast<float>(internalH);
	const float s = (sx < sy) ? sx : sy;

	scaleX = s;
	scaleY = s;
	offsetX = (clientW - static_cast<LONG>(s * internalW)) / 2;
	offsetY = (clientH - static_cast<LONG>(s * internalH)) / 2;

	Logger::Get().WriteLine(
		LogLevel::Info,
		"ScaleRemap: client %ldx%ld, internal %dx%d -> scale %.4f, letterbox (%ld, %ld)",
		clientW, clientH, internalW, internalH, s, offsetX, offsetY);

	return true;
}

void ScaleRemap::PhysClientToGame(LONG& x, LONG& y) const
{
	if (!active) { return; }
	x = static_cast<LONG>((x - offsetX) / scaleX);
	y = static_cast<LONG>((y - offsetY) / scaleY);
	if (x < 0) { x = 0; } else if (x >= internalW) { x = internalW - 1; }
	if (y < 0) { y = 0; } else if (y >= internalH) { y = internalH - 1; }
}

void ScaleRemap::GameClientToPhys(LONG& x, LONG& y) const
{
	if (!active) { return; }
	x = static_cast<LONG>(x * scaleX) + offsetX;
	y = static_cast<LONG>(y * scaleY) + offsetY;
}

void ScaleRemap::PhysScreenToGameScreen(LONG& x, LONG& y) const
{
	if (!active) { return; }
	// The game converts screen->client itself with the REAL window origin,
	// so pre-warp the screen point such that after the game subtracts the
	// origin it lands on game-space client coords.
	POINT origin = { 0, 0 };
	ClientToScreen(hwnd, &origin); // our DLL: real, untransformed
	LONG cx = x - origin.x;
	LONG cy = y - origin.y;
	PhysClientToGame(cx, cy);
	x = origin.x + cx;
	y = origin.y + cy;
}

LPARAM ScaleRemap::TransformClientLParam(LPARAM lParam) const
{
	LONG x = static_cast<SHORT>(LOWORD(lParam));
	LONG y = static_cast<SHORT>(HIWORD(lParam));
	PhysClientToGame(x, y);
	return MAKELPARAM(static_cast<WORD>(x), static_cast<WORD>(y));
}

LPARAM ScaleRemap::TransformScreenLParam(LPARAM lParam) const
{
	LONG x = static_cast<SHORT>(LOWORD(lParam));
	LONG y = static_cast<SHORT>(HIWORD(lParam));
	PhysScreenToGameScreen(x, y);
	return MAKELPARAM(static_cast<WORD>(x), static_cast<WORD>(y));
}

BOOL WINAPI ScaleRemap::HookGetCursorPos(LPPOINT lpPoint)
{
	ScaleRemap* self = instance;
	if (!self || !self->realGetCursorPos)
	{
		return FALSE;
	}

	const BOOL result = self->realGetCursorPos(lpPoint);

	if (result && self->active && lpPoint && CallerIsGameModule(_ReturnAddress()))
	{
		self->PhysScreenToGameScreen(lpPoint->x, lpPoint->y);
		if (self->settings.logCoordTraffic)
		{
			Logger::Get().WriteLine(
				LogLevel::Trace, "GetCursorPos(game) -> (%ld, %ld)", lpPoint->x, lpPoint->y);
		}
	}

	return result;
}

BOOL WINAPI ScaleRemap::HookSetCursorPos(int x, int y)
{
	ScaleRemap* self = instance;
	if (!self || !self->realSetCursorPos)
	{
		return FALSE;
	}

	if (self->active && CallerIsGameModule(_ReturnAddress()))
	{
		LONG px = x;
		LONG py = y;
		// Inverse of PhysScreenToGameScreen.
		POINT origin = { 0, 0 };
		ClientToScreen(self->hwnd, &origin);
		LONG cx = px - origin.x;
		LONG cy = py - origin.y;
		self->GameClientToPhys(cx, cy);
		px = origin.x + cx;
		py = origin.y + cy;
		if (self->settings.logCoordTraffic)
		{
			Logger::Get().WriteLine(
				LogLevel::Trace, "SetCursorPos(game) (%d, %d) -> (%ld, %ld)", x, y, px, py);
		}
		return self->realSetCursorPos(px, py);
	}

	return self->realSetCursorPos(x, y);
}

BOOL WINAPI ScaleRemap::HookClipCursor(const RECT* lpRect)
{
	ScaleRemap* self = instance;
	if (!self || !self->realClipCursor)
	{
		return FALSE;
	}

	if (self->active && lpRect && CallerIsGameModule(_ReturnAddress()))
	{
		RECT scaled = *lpRect;
		POINT origin = { 0, 0 };
		ClientToScreen(self->hwnd, &origin);
		LONG l = scaled.left - origin.x, t = scaled.top - origin.y;
		LONG r = scaled.right - origin.x, b = scaled.bottom - origin.y;
		self->GameClientToPhys(l, t);
		self->GameClientToPhys(r, b);
		scaled.left = origin.x + l; scaled.top = origin.y + t;
		scaled.right = origin.x + r; scaled.bottom = origin.y + b;
		return self->realClipCursor(&scaled);
	}

	return self->realClipCursor(lpRect);
}

int WINAPI ScaleRemap::HookGetSystemMetrics(int nIndex)
{
	ScaleRemap* self = instance;
	if (!self || !self->realGetSystemMetrics)
	{
		return 0;
	}

	if (self->metricsActive && CallerIsGameModule(_ReturnAddress()))
	{
		// The game's UI compositor sizes its surfaces from screen metrics;
		// they must agree with the internal render resolution from the very
		// FIRST query during startup, or blits land with wrong geometry.
		switch (nIndex)
		{
		case SM_CXSCREEN: case SM_CXFULLSCREEN: case SM_CXVIRTUALSCREEN:
			return self->internalW;
		case SM_CYSCREEN: case SM_CYFULLSCREEN: case SM_CYVIRTUALSCREEN:
			return self->internalH;
		default:
			break;
		}
	}

	return self->realGetSystemMetrics(nIndex);
}

int WINAPI ScaleRemap::HookGetDeviceCaps(HDC hdc, int index)
{
	ScaleRemap* self = instance;
	if (!self || !self->realGetDeviceCaps)
	{
		return 0;
	}

	if (self->metricsActive && CallerIsGameModule(_ReturnAddress()))
	{
		switch (index)
		{
		case HORZRES: case DESKTOPHORZRES:
			return self->internalW;
		case VERTRES: case DESKTOPVERTRES:
			return self->internalH;
		default:
			break;
		}
	}

	return self->realGetDeviceCaps(hdc, index);
}

BOOL WINAPI ScaleRemap::HookGetClientRect(HWND hWnd, LPRECT lpRect)
{
	ScaleRemap* self = instance;
	if (!self || !self->realGetClientRect)
	{
		return FALSE;
	}

	const BOOL result = self->realGetClientRect(hWnd, lpRect);

	// Before the window is attached (startup), lie for any game-module rect
	// query - the game only ever asks about its own windows during init.
	// After attach, lie only for the tracked game window.
	if (result && lpRect && self->active && hWnd == self->hwnd
		&& CallerIsGameModule(_ReturnAddress()))
	{
		lpRect->right = lpRect->left + self->internalW;
		lpRect->bottom = lpRect->top + self->internalH;
	}

	return result;
}

BOOL WINAPI ScaleRemap::HookGetWindowRect(HWND hWnd, LPRECT lpRect)
{
	ScaleRemap* self = instance;
	if (!self || !self->realGetWindowRect)
	{
		return FALSE;
	}

	const BOOL result = self->realGetWindowRect(hWnd, lpRect);

	if (result && lpRect && self->active && hWnd == self->hwnd
		&& CallerIsGameModule(_ReturnAddress()))
	{
		lpRect->right = lpRect->left + self->internalW;
		lpRect->bottom = lpRect->top + self->internalH;
	}

	return result;
}

BOOL WINAPI ScaleRemap::HookSetWindowPos(
	HWND hWnd, HWND hWndInsertAfter, int X, int Y, int cx, int cy, UINT uFlags)
{
	ScaleRemap* self = instance;
	if (!self || !self->realSetWindowPos)
	{
		return FALSE;
	}

	// The game believes its window is internal-sized (we lie about rects and
	// metrics), so it periodically tries to enforce that size. Letting those
	// through fights whoever manages the real fullscreen-size window (us) -
	// an infinite resize war that hangs startup. Swallow the size component
	// of game-module window positioning; keep everything else.
	if (self->active && (uFlags & SWP_NOSIZE) == 0
		&& CallerIsGameModule(_ReturnAddress()))
	{
		if (self->settings.logCoordTraffic)
		{
			Logger::Get().WriteLine(
				LogLevel::Trace, "SetWindowPos(game) size %dx%d suppressed", cx, cy);
		}
		return self->realSetWindowPos(hWnd, hWndInsertAfter, X, Y, cx, cy, uFlags | SWP_NOSIZE);
	}

	return self->realSetWindowPos(hWnd, hWndInsertAfter, X, Y, cx, cy, uFlags);
}

BOOL WINAPI ScaleRemap::HookMoveWindow(
	HWND hWnd, int X, int Y, int nWidth, int nHeight, BOOL bRepaint)
{
	ScaleRemap* self = instance;
	if (!self || !self->realMoveWindow)
	{
		return FALSE;
	}

	if (self->active && CallerIsGameModule(_ReturnAddress()))
	{
		// Same rationale as HookSetWindowPos: preserve the real size.
		RECT r = {};
		if (self->realGetWindowRect && self->realGetWindowRect(hWnd, &r))
		{
			return self->realMoveWindow(hWnd, X, Y, r.right - r.left, r.bottom - r.top, bRepaint);
		}
	}

	return self->realMoveWindow(hWnd, X, Y, nWidth, nHeight, bRepaint);
}

bool ScaleRemap::InstallHooks()
{
	Logger& logger = Logger::Get();

	if (hooksInstalled)
	{
		return true;
	}

	if (!minhookReady)
	{
		// v2.69.2: tolerate ALREADY_INITIALIZED. MinHook is one process-wide
		// singleton and FOUR other modules in this DLL also initialize it
		// (UiSpike's SUBBORN/FLYOPEN/SUBBORN2/SHOWHOOK sites + WebRedirect).
		// This was the ONE site that treated a second init as failure, so if
		// any of them ran first - and WebRedirect installs unconditionally at
		// every tier - this returned false and ScaleRemap silently never
		// hooked. Same tolerance every other site already has.
		const MH_STATUS init = MH_Initialize();
		if (init != MH_OK && init != MH_ERROR_ALREADY_INITIALIZED)
		{
			logger.WriteLine(LogLevel::Error,
				"ScaleRemap: MinHook init failed (%d).", init);
			return false;
		}
		minhookReady = true;
	}

	HMODULE user32 = GetModuleHandleW(L"user32.dll");
	if (!user32)
	{
		return false;
	}

	struct HookSpec
	{
		const char* name;
		bool enabled;
		void* detour;
		void** original;
	};

	HMODULE gdi32 = GetModuleHandleW(L"gdi32.dll");

	struct HookSpecEx
	{
		HMODULE module;
		const char* name;
		bool enabled;
		void* detour;
		void** original;
	};

	HookSpecEx specs[] = {
		{ user32, "GetCursorPos", settings.hookGetCursorPos, reinterpret_cast<void*>(&HookGetCursorPos), reinterpret_cast<void**>(&realGetCursorPos) },
		{ user32, "SetCursorPos", settings.hookSetCursorPos, reinterpret_cast<void*>(&HookSetCursorPos), reinterpret_cast<void**>(&realSetCursorPos) },
		{ user32, "ClipCursor",   settings.hookClipCursor,   reinterpret_cast<void*>(&HookClipCursor),   reinterpret_cast<void**>(&realClipCursor) },
		{ user32, "GetSystemMetrics", settings.hookWindowMetrics, reinterpret_cast<void*>(&HookGetSystemMetrics), reinterpret_cast<void**>(&realGetSystemMetrics) },
		{ gdi32,  "GetDeviceCaps",    settings.hookWindowMetrics, reinterpret_cast<void*>(&HookGetDeviceCaps),    reinterpret_cast<void**>(&realGetDeviceCaps) },
		{ user32, "GetClientRect",    settings.hookWindowMetrics, reinterpret_cast<void*>(&HookGetClientRect),    reinterpret_cast<void**>(&realGetClientRect) },
		{ user32, "GetWindowRect",    settings.hookWindowMetrics, reinterpret_cast<void*>(&HookGetWindowRect),    reinterpret_cast<void**>(&realGetWindowRect) },
		{ user32, "SetWindowPos",     settings.hookWindowMetrics, reinterpret_cast<void*>(&HookSetWindowPos),     reinterpret_cast<void**>(&realSetWindowPos) },
		{ user32, "MoveWindow",       settings.hookWindowMetrics, reinterpret_cast<void*>(&HookMoveWindow),       reinterpret_cast<void**>(&realMoveWindow) },
	};

	bool any = false;
	for (const HookSpecEx& spec : specs)
	{
		if (!spec.enabled || !spec.module)
		{
			continue;
		}
		void* target = reinterpret_cast<void*>(GetProcAddress(spec.module, spec.name));
		if (!target)
		{
			logger.WriteLine(LogLevel::Error, "ScaleRemap: %s not found.", spec.name);
			continue;
		}
		if (MH_CreateHook(target, spec.detour, spec.original) != MH_OK
			|| MH_EnableHook(target) != MH_OK)
		{
			logger.WriteLine(LogLevel::Error, "ScaleRemap: hook %s failed.", spec.name);
			continue;
		}
		// v2.69.2: remember the target so RemoveHooks can undo exactly this
		// hook and nothing else. Capacity == sizeof(specs), so the guard can
		// only trip if someone grows specs[] without growing the array.
		if (hookedTargetCount < static_cast<int>(sizeof(hookedTargets) / sizeof(hookedTargets[0])))
		{
			hookedTargets[hookedTargetCount++] = target;
		}
		else
		{
			logger.WriteLine(LogLevel::Error,
				"ScaleRemap: hookedTargets[] full - %s hooked but NOT tracked; "
				"grow the array or RemoveHooks will leave it installed.",
				spec.name);
		}
		any = true;
		logger.WriteLine(LogLevel::Debug, "ScaleRemap: hooked %s.", spec.name);
	}

	hooksInstalled = any;
	return any;
}

void ScaleRemap::RemoveHooks()
{
	// v2.69.2: undo ONLY the hooks this module installed. The previous body
	// was MH_DisableHook(MH_ALL_HOOKS) + MH_Uninitialize() - but MinHook is a
	// process-wide singleton this module does not own: UiSpike holds four
	// GAME-CODE hooks (SUBBORN/FLYOPEN/SUBBORN2/SHOWHOOK) and WebRedirect
	// holds the ShellExecuteA/W pair. This runs at SHUTDOWN 2/3 while the
	// game's own teardown is still ahead (and the #104 spin thread may be
	// live), so ALL_HOOKS ripped out other modules' detours mid-flight and
	// MH_Uninitialize freed the SHARED trampoline pool under them. The shipped
	// default only survived because useScaleRemap=0 keeps minhookReady false -
	// the one documented setting that arms this path made shutdown unsafe.
	// The shutdown probe's own legend records "SHUTDOWN 2/3 ... (MinHook)
	// hung" as a real observed outcome.
	// MinHook stays initialized for the process lifetime; the OS reclaims it.
	for (int i = 0; i < hookedTargetCount; i++)
	{
		if (hookedTargets[i])
		{
			MH_DisableHook(hookedTargets[i]);
			MH_RemoveHook(hookedTargets[i]);
			hookedTargets[i] = nullptr;
		}
	}
	hookedTargetCount = 0;
	hooksInstalled = false;
	realGetCursorPos = nullptr;
	realSetCursorPos = nullptr;
	realClipCursor = nullptr;
}

bool ScaleRemap::EarlyInstall(int gameInternalW, int gameInternalH)
{
	internalW = gameInternalW;
	internalH = gameInternalH;

	if (!settings.scalingEnabled || internalW <= 0 || internalH <= 0)
	{
		return false;
	}

	if (!InstallHooks())
	{
		Logger::Get().WriteLine(
			LogLevel::Error, "ScaleRemap: early hook install failed - remap disabled.");
		return false;
	}

	// Metric lies go live NOW, before the game initializes graphics, so its
	// whole world is internal-resolution-shaped from the first query. The
	// coordinate transforms wait for the window (AttachWindow).
	metricsActive = settings.hookWindowMetrics;

	Logger::Get().WriteLine(
		LogLevel::Info,
		"ScaleRemap: early install, internal %dx%d, metric lies %s.",
		internalW, internalH, metricsActive ? "ACTIVE" : "off");
	return true;
}

bool ScaleRemap::AttachWindow(HWND gameWindow)
{
	hwnd = gameWindow;

	if (!settings.scalingEnabled || !hooksInstalled)
	{
		active = false;
		return false;
	}

	// WE manage the real window (the game is lied into believing it is
	// internal-sized and its own resize attempts are suppressed): strip the
	// frame and cover the monitor. Calls below come from THIS module, so
	// they pass through the hooks untransformed. Skipped when the window
	// already covers the monitor (e.g. emulated-fullscreen mode).
	MONITORINFO mi = { sizeof(MONITORINFO) };
	RECT preClient = {};
	GetClientRect(hwnd, &preClient);
	if (GetMonitorInfoW(MonitorFromWindow(hwnd, MONITOR_DEFAULTTOPRIMARY), &mi)
		&& (preClient.right - preClient.left < mi.rcMonitor.right - mi.rcMonitor.left - 8
			|| preClient.bottom - preClient.top < mi.rcMonitor.bottom - mi.rcMonitor.top - 8))
	{
		const LONG style = GetWindowLongW(hwnd, GWL_STYLE);
		SetWindowLongW(hwnd, GWL_STYLE,
			(style & ~(WS_CAPTION | WS_THICKFRAME | WS_MINIMIZEBOX | WS_MAXIMIZEBOX)) | WS_POPUP);
		if (realSetWindowPos)
		{
			realSetWindowPos(
				hwnd, HWND_TOP,
				mi.rcMonitor.left, mi.rcMonitor.top,
				mi.rcMonitor.right - mi.rcMonitor.left,
				mi.rcMonitor.bottom - mi.rcMonitor.top,
				SWP_FRAMECHANGED | SWP_SHOWWINDOW);
		}
		Logger::Get().WriteLine(
			LogLevel::Info,
			"ScaleRemap: window set borderless %ldx%ld.",
			mi.rcMonitor.right - mi.rcMonitor.left,
			mi.rcMonitor.bottom - mi.rcMonitor.top);
	}

	active = ComputeTransform();

	Logger::Get().WriteLine(
		LogLevel::Info, "ScaleRemap: transforms %s.", active ? "ACTIVE" : "identity (inactive)");

	if (!active && metricsActive)
	{
		// Identity presentation (e.g. no wrapper scaling): the metric lies
		// still return the internal size, which now EQUALS what the game
		// would see anyway only if internal == real screen. If they differ,
		// keep lying - the game sized itself around the internal values at
		// startup and consistency matters more than truth.
		Logger::Get().WriteLine(
			LogLevel::Debug, "ScaleRemap: metric lies remain active for consistency.");
	}

	return active;
}

void ScaleRemap::OnWindowSizeChanged()
{
	if (settings.scalingEnabled && hwnd)
	{
		active = ComputeTransform() && hooksInstalled;
	}
}

void ScaleRemap::Uninstall()
{
	RemoveHooks();
	metricsActive = false;
	active = false;
	hwnd = nullptr;
}


