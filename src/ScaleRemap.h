#pragma once

#define WIN32_LEAN_AND_MEAN
#include <Windows.h>

#include "Settings.h"

// Owns THE coordinate transform between physical space (what Windows and the
// input layer sees: real panel pixels) and game space (the small
// internal resolution SC4 renders at; dgVoodoo stretches the frame to the
// panel). Exactly one transform exists in the whole system:
//
//     game = (physical - letterboxOffset) / scale
//
// Hooked cursor APIs apply it ONLY to calls made by the game module itself
// (return-address filtered); our DLL and the wrapper always see real physical
// coordinates. Identity (scale 1, no hooks) whenever the presented client
// size equals the game's internal size - e.g. a native 1024x768 panel.
class ScaleRemap
{
public:
	explicit ScaleRemap(const Settings& settings);
	~ScaleRemap();

	// Phase 1 - call from the DLL-director CONSTRUCTOR (plugin scan, before
	// the game initializes graphics): installs all hooks and starts lying
	// about screen metrics immediately, so the game sizes every surface from
	// the internal resolution from its very first query. Cursor-coordinate
	// transforms stay pass-through until AttachWindow computes the scale.
	bool EarlyInstall(int internalW, int internalH);

	// Phase 2 - call once the game window exists (PostAppInit): computes the
	// scale/letterbox from the client rect and activates the coordinate
	// transforms. Returns true if the remap is ACTIVE (non-identity).
	bool AttachWindow(HWND gameWindow);

	void Uninstall();
	void OnWindowSizeChanged();

	bool IsActive() const { return active; }
	float Scale() const { return scaleX; } // uniform in practice; X reported

	// Physical client coords -> game client coords (identity when inactive).
	void PhysClientToGame(LONG& x, LONG& y) const;
	// Physical screen coords -> the screen coords the game expects.
	void PhysScreenToGameScreen(LONG& x, LONG& y) const;
	// Game client coords -> physical client coords.
	void GameClientToPhys(LONG& x, LONG& y) const;

	// Convenience for mouse-message lParams (client-coordinate messages).
	LPARAM TransformClientLParam(LPARAM lParam) const;
	// For WM_MOUSEWHEEL-style screen-coordinate lParams.
	LPARAM TransformScreenLParam(LPARAM lParam) const;

private:
	bool ComputeTransform();
	bool InstallHooks();
	void RemoveHooks();
	static bool CallerIsGameModule(void* returnAddress);

	static BOOL WINAPI HookGetCursorPos(LPPOINT lpPoint);
	static BOOL WINAPI HookSetCursorPos(int x, int y);
	static BOOL WINAPI HookClipCursor(const RECT* lpRect);
	static int WINAPI HookGetSystemMetrics(int nIndex);
	static int WINAPI HookGetDeviceCaps(HDC hdc, int index);
	static BOOL WINAPI HookGetClientRect(HWND hWnd, LPRECT lpRect);
	static BOOL WINAPI HookGetWindowRect(HWND hWnd, LPRECT lpRect);
	static BOOL WINAPI HookSetWindowPos(HWND hWnd, HWND hWndInsertAfter, int X, int Y, int cx, int cy, UINT uFlags);
	static BOOL WINAPI HookMoveWindow(HWND hWnd, int X, int Y, int nWidth, int nHeight, BOOL bRepaint);

	const Settings& settings;
	HWND hwnd;
	int internalW;
	int internalH;
	bool metricsActive; // metric lies live (from EarlyInstall until Uninstall)
	bool active;        // coordinate transforms live (post-AttachWindow, non-identity)
	bool hooksInstalled;
	bool minhookReady;

	// v2.69.2: the exact targets THIS module hooked, so RemoveHooks can undo
	// only its own work. MinHook is one process-wide singleton shared with
	// UiSpike's four game-code hooks and WebRedirect's ShellExecute pair;
	// MH_ALL_HOOKS / MH_Uninitialize from here would tear those down too.
	void* hookedTargets[9];
	int hookedTargetCount;

	float scaleX;
	float scaleY;
	LONG offsetX; // letterbox offset inside the client area, physical px
	LONG offsetY;

	// Original functions (trampolines) filled in by MinHook.
	using GetCursorPosFn = BOOL(WINAPI*)(LPPOINT);
	using SetCursorPosFn = BOOL(WINAPI*)(int, int);
	using ClipCursorFn = BOOL(WINAPI*)(const RECT*);
	using GetSystemMetricsFn = int(WINAPI*)(int);
	using GetDeviceCapsFn = int(WINAPI*)(HDC, int);
	using GetRectFn = BOOL(WINAPI*)(HWND, LPRECT);
	using SetWindowPosFn = BOOL(WINAPI*)(HWND, HWND, int, int, int, int, UINT);
	using MoveWindowFn = BOOL(WINAPI*)(HWND, int, int, int, int, BOOL);
	GetCursorPosFn realGetCursorPos;
	SetCursorPosFn realSetCursorPos;
	ClipCursorFn realClipCursor;
	GetSystemMetricsFn realGetSystemMetrics;
	GetDeviceCapsFn realGetDeviceCaps;
	GetRectFn realGetClientRect;
	GetRectFn realGetWindowRect;
	SetWindowPosFn realSetWindowPos;
	MoveWindowFn realMoveWindow;

	static ScaleRemap* instance; // hook thunks need static access
	static void* gameModuleBase;
	static size_t gameModuleSize;
};
