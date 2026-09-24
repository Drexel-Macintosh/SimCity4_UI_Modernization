// SC4HeaderTest: checks the fixed gzcom-dll headers (branch fix-vtable-order)
// inside the running game.
//
// Built against C:\dev\gzcom-dll-fork. Once the game is up it calls the fixed
// methods on live objects and writes SC4HeaderTest.log next to the DLL:
//   - the app object;
//   - one of the game's own COM directors;
//   - a real window, including its input handlers.
//
// Each call is checked two ways:
//   1. the result, against an independent reading;
//   2. the stack, which must come back balanced. A method on the wrong slot,
//      or with the wrong arguments, leaves the stack off.
// Every window change is put back. Every test runs under SEH, so a failure is
// logged instead of crashing the game. It runs once, then does nothing.

#include <windows.h>
#include <commctrl.h>
#include <cstdarg>
#include <cstdint>
#include <cstdio>
#include <cstring>

#include "cRZCOMDllDirector.h"
#include "cIGZApp.h"
#include "cIGZCOMDirector.h"
#include "cIGZFrameWork.h"
#include "cIGZFrameWorkW32.h"
#include "cIGZWin.h"
#include "cISC4App.h"
#include "GZServPtrs.h"
#include "cRZRect.h"
#include "cRZPoint.h"
#include "cGZMessage.h"

// gzcom-dll only declares cRZColor; the game's is 4 bytes, passed by value.
class cRZColor { public: uint32_t raw; };

static const uint32_t kDirectorID = 0x5C4E0A17;
static const uintptr_t kExeBase = 0x00400000;

// ------------------------------------------------------------------- logging
static FILE* gLog = nullptr;
static int gPass = 0, gFail = 0, gInfo = 0;

static void Log(const char* fmt, ...)
{
	if (!gLog) return;
	va_list a;
	va_start(a, fmt);
	vfprintf(gLog, fmt, a);
	va_end(a);
	fputc('\n', gLog);
	fflush(gLog);
}

static void Check(bool ok, const char* fmt, ...)
{
	if (!gLog) return;
	fputs(ok ? "PASS  " : "FAIL  ", gLog);
	va_list a;
	va_start(a, fmt);
	vfprintf(gLog, fmt, a);
	va_end(a);
	fputc('\n', gLog);
	fflush(gLog);
	(ok ? gPass : gFail)++;
}

typedef void (*TestFn)(void*);
static void Run(const char* name, TestFn fn, void* ctx)
{
	Log("\n== %s", name);
	__try { fn(ctx); }
	__except (EXCEPTION_EXECUTE_HANDLER)
	{
		Log("FAIL  %s: exception 0x%08X (caught)", name, GetExceptionCode());
		gFail++;
	}
}

// The stack pointer before and after one call. The frame is EBP-based
// (optimisation off below), so an unbalanced callee is survivable here.
#define BALANCED(ok, stmt) do { uintptr_t e0_ = 0, e1_ = 0; \
	__asm { mov e0_, esp } stmt; __asm { mov e1_, esp } ok = (e0_ == e1_); } while (0)

#pragma optimize("", off)

static uintptr_t Rebase(uintptr_t va) { return (uintptr_t)GetModuleHandleA(nullptr) - kExeBase + va; }

static void Rect4(const cRZRect& r, int32_t out[4]) { memcpy(out, &r, 16); }

// ------------------------------------------------------------------ cIGZApp
static void TestApp(void*)
{
	cIGZFrameWork* fw = RZGetFrameWork();
	cIGZApp* app = fw ? fw->Application() : nullptr;
	Log("framework %p, app %p", fw, app);
	if (!app) { Check(false, "no app object"); return; }

	bool b;
	cIGZFrameWork* got = nullptr;
	BALANCED(b, got = app->FrameWork());
	Check(b && got == fw, "cIGZApp::FrameWork() (slot 10) returns the framework %p (got %p, stack %s)",
		fw, got, b ? "balanced" : "OFF");

	const char* name = nullptr;
	BALANCED(b, name = app->ModuleName());
	Check(b && name && strcmp(name, "SimCity 4") == 0, "cIGZApp::ModuleName() (slot 5) returns \"%s\" (stack %s)",
		name ? name : "(null)", b ? "balanced" : "OFF");

	cIGZSystemService* svc = nullptr;
	BALANCED(b, svc = app->AsIGZSystemService());
	Check(b && svc != nullptr, "cIGZApp::AsIGZSystemService() (slot 3) returns %p", svc);

	// What the OLD header's FrameWork() reached: slot 5.
	typedef void* (__fastcall* Fn0)(void*, void*);
	void** vt = *(void***)app;
	void* old = ((Fn0)vt[5])(app, nullptr);
	Log("INFO  the OLD header's FrameWork() called slot 5 and got %p = \"%s\", not the framework %p",
		old, old ? (const char*)old : "", fw);
	gInfo++;
}

// ------------------------------------------------------------ COM directors
static void TestDirectors(void*)
{
	bool b;
	uint32_t id = 0;
	cIGZCOMDirector* mine = static_cast<cIGZCOMDirector*>(RZGetCOMDllDirector());
	BALANCED(b, id = mine->GetDirectorID());
	Check(b && id == kDirectorID, "this plugin's director: GetDirectorID() through cIGZCOMDirector (slot 13) = 0x%08X", id);

	// The resource manager's director: vtable 0x00AD8BA0; its GetDirectorID returns 0xC3CAEC3B.
	const uintptr_t vt = Rebase(0x00AD8BA0);
	BYTE* base = (BYTE*)GetModuleHandleA(nullptr);
	IMAGE_NT_HEADERS* nt = (IMAGE_NT_HEADERS*)(base + ((IMAGE_DOS_HEADER*)base)->e_lfanew);
	IMAGE_SECTION_HEADER* sec = IMAGE_FIRST_SECTION(nt);
	int found = 0;
	for (int s = 0; s < nt->FileHeader.NumberOfSections; s++)
	{
		if (!(sec[s].Characteristics & IMAGE_SCN_MEM_WRITE)) continue;
		uintptr_t* p = (uintptr_t*)(base + sec[s].VirtualAddress);
		size_t n = sec[s].Misc.VirtualSize / 4;
		for (size_t i = 0; i < n; i++)
		{
			if (p[i] != vt) continue;
			cIGZCOMDirector* d = (cIGZCOMDirector*)&p[i];
			cIGZFrameWork* dfw = nullptr;
			BALANCED(b, id = d->GetDirectorID());
			Check(b && id == 0xC3CAEC3B,
				"game director at %p (vtable 0x00AD8BA0): GetDirectorID() through cIGZCOMDirector (slot 13) = 0x%08X, expected 0xC3CAEC3B",
				d, id);
			BALANCED(b, dfw = d->FrameWork());
			Check(b && dfw == RZGetFrameWork(), "the same director's FrameWork() (slot 11) is the live framework: %p", dfw);
			found++;
		}
	}
	if (!found)
	{
		Log("INFO  the resource manager's director object was not found in the exe's data sections");
		gInfo++;
	}
}

// ------------------------------------------------------------------ windows
struct Kids { cIGZWin* w[256]; int n; };
static bool CollectKids(cIGZWin*, uint32_t, void* child, void* ctx)
{
	Kids* k = (Kids*)ctx;
	if (child && k->n < 256) k->w[k->n++] = (cIGZWin*)child;
	return true;
}

static int Kids_(cIGZWin* w, Kids& k)
{
	k.n = 0;
	w->EnumChildren(GZIID_cIGZWin, CollectKids, &k);
	return k.n;
}

// Handlers identical to the base cGZWin's (0x00ADC8D8) at 129-143, so calling
// them runs the shared stubs (or base SetFocus, a no-op on a visible window).
static bool PlainHandlers(cIGZWin* w)
{
	void** vt = *(void***)w;
	void** bvt = (void**)Rebase(0x00ADC8D8);
	for (int s = 129; s <= 143; s++)
		if (vt[s] != bvt[s]) return false;
	return true;
}

struct Pick { cIGZWin* geom; cIGZWin* plain; };

static void FindWindows(cIGZWin* main, Pick& pick)
{
	pick.geom = pick.plain = nullptr;
	static Kids l1, l2;
	Kids_(main, l1);
	for (int i = 0; i < l1.n; i++)
	{
		if (!l1.w[i]->IsVisible()) continue;
		Kids_(l1.w[i], l2);
		for (int j = 0; j < l2.n; j++)
		{
			cIGZWin* c = l2.w[j];
			if (!c->IsVisible() || c->GetW() < 12 || c->GetH() < 12) continue;
			if (!pick.geom && PlainHandlers(c)) pick.geom = c;
			if (!pick.plain && PlainHandlers(c)) pick.plain = c;
		}
		if (pick.geom) break;
	}
}

struct WinCtx { cIGZWin* w; cIGZWin* parent; };

static void TestGeometry(void* v)
{
	cIGZWin* w = ((WinCtx*)v)->w;
	cIGZWin* p = ((WinCtx*)v)->parent;
	const int32_t L = w->GetL(), T = w->GetT(), R = w->GetR(), B = w->GetB(), W = w->GetW(), H = w->GetH();
	Log("window ID 0x%08X at (%d,%d)-(%d,%d), %dx%d; parent ID 0x%08X", w->GetID(), L, T, R, B, W, H, p->GetID());
	bool b;
	int32_t q[4];

	cRZRect r;
	memset(&r, 0xCD, sizeof r);
	BALANCED(b, w->GetArea(r));
	Rect4(r, q);
	Check(b && q[0] == L && q[1] == T && q[2] == R && q[3] == B,
		"GetArea(cRZRect&) (slot 47) fills (%d,%d,%d,%d)", q[0], q[1], q[2], q[3]);
	int32_t* pr = nullptr;
	BALANCED(b, pr = w->GetArea());
	Check(b && pr && pr[0] == L && pr[1] == T && pr[2] == R && pr[3] == B, "GetArea() (slot 48) points at the same rect");

	cRZRect ra, pa;
	int32_t qa[4], qp[4];
	BALANCED(b, w->GetAreaAbsolute(ra));
	Rect4(ra, qa);
	int32_t* pra = nullptr;
	bool b2;
	BALANCED(b2, pra = w->GetAreaAbsolute());
	p->GetAreaAbsolute(pa);
	Rect4(pa, qp);
	Check(b && b2 && pra && memcmp(qa, pra, 16) == 0 && qa[0] == qp[0] + L && qa[1] == qp[1] + T,
		"GetAreaAbsolute(cRZRect&) (49) and GetAreaAbsolute() (50) agree, and equal the parent's absolute origin + (%d,%d): (%d,%d)",
		L, T, qa[0], qa[1]);

	BALANCED(b, w->GZWinOffset(3, 2));
	Check(b && w->GetL() == L + 3 && w->GetT() == T + 2, "GZWinOffset(3, 2) (slot 57) moves BY: now (%d,%d)", w->GetL(), w->GetT());
	w->GZWinOffset(-3, -2);
	Check(w->GetL() == L && w->GetT() == T, "GZWinOffset(-3, -2) puts it back");

	BALANCED(b, w->GZWinMoveTo(L + 5, T + 4));
	Check(b && w->GetL() == L + 5 && w->GetT() == T + 4, "GZWinMoveTo(L+5, T+4) (slot 56) moves TO: now (%d,%d)", w->GetL(), w->GetT());
	w->GZWinMoveTo(L, T);
	Check(w->GetL() == L && w->GetT() == T, "GZWinMoveTo(L, T) puts it back");

	BALANCED(b, w->SetSize(W + 2, H + 1));
	Check(b && w->GetW() == W + 2 && w->GetH() == H + 1 && w->GetL() == L, "SetSize(w, h) (slot 53) resizes: now %dx%d", w->GetW(), w->GetH());
	cRZPoint pt;
	pt.nX = W + 1;
	pt.nY = H + 2;
	BALANCED(b, w->SetSize(pt));
	Check(b && w->GetW() == W + 1 && w->GetH() == H + 2, "SetSize(cRZPoint) -> SetSizeFromPoint (slot 118) resizes: now %dx%d", w->GetW(), w->GetH());
	w->SetSize(W, H);
	Check(w->GetW() == W && w->GetH() == H, "SetSize(W, H) puts it back");

	int32_t nr[4] = { L + 1, T + 1, R + 1, B + 1 };
	cRZRect rr;
	memcpy(&rr, nr, 16);
	BALANCED(b, w->SetArea(rr));
	Check(b && w->GetL() == L + 1 && w->GetR() == R + 1, "SetArea(const cRZRect&) (slot 54) sets the rect: now (%d,%d)", w->GetL(), w->GetT());
	BALANCED(b, w->SetArea(L, T, R, B));
	Check(b && w->GetL() == L && w->GetT() == T && w->GetR() == R && w->GetB() == B, "SetArea(l, t, r, b) (slot 55) puts it back");

	BALANCED(b, w->CenterWindowInRect((cRZRect*)nullptr));
	Check(b && w->GetL() == L && w->GetT() == T, "CenterWindowInRect(cRZRect*) (slot 120) accepts null (the reference overload at 119 would not)");
	BALANCED(b, w->CenterWindowInRect(r));
	Log("INFO  CenterWindowInRect(own rect) (slot 119): stack %s, window now at (%d,%d)", b ? "balanced" : "OFF", w->GetL(), w->GetT());
	gInfo++;
	w->GZWinMoveTo(L, T);
	Check(w->GetL() == L && w->GetT() == T, "window back at (%d,%d)", L, T);

	bool in = false, out = true, pin = false;
	BALANCED(b, in = w->IsPointInWindowWindowCoordinates(W / 2, H / 2));
	BALANCED(b2, out = w->IsPointInWindowWindowCoordinates(-5, -5));
	bool b3;
	BALANCED(b3, pin = w->IsPointInWindowParentCoordinates(L + W / 2, T + H / 2));
	Check(b && b2 && b3 && in && !out && pin, "IsPointInWindowWindowCoordinates (121) and ...ParentCoordinates (122): centre in, (-5,-5) out");

	uint32_t k = w->GetKeyEquivalent();
	bool yes = false, no = true;
	BALANCED(b, yes = w->CheckKeyEquivalent(k & 0xFFFF, k >> 16));
	BALANCED(b2, no = w->CheckKeyEquivalent((k & 0xFFFF) ^ 1, k >> 16));
	Check(b && b2 && yes && !no, "CheckKeyEquivalent(key, modifiers) (slot 80): its own key 0x%08X matches, another does not", k);

	if (w->GetKeyboardAccelerator() == nullptr)
	{
		cGZMessage m(0);
		bool acc = true;
		BALANCED(b, acc = w->AccelerateKeyboardMsg(m));
		Check(b && !acc, "AccelerateKeyboardMsg(msg) (slot 77) with no accelerator returns false");
	}
	else { Log("INFO  window has a keyboard accelerator; AccelerateKeyboardMsg not called"); gInfo++; }

	// Old header: its GetArea(cRZRect&) compiled to slot 48.
	typedef bool (__fastcall* OldGetAreaRect)(void*, void*, cRZRect*);
	void** vt = *(void***)w;
	cRZRect junk;
	memset(&junk, 0xCD, sizeof junk);
	BALANCED(b, ((OldGetAreaRect)vt[48])(w, nullptr, &junk));
	Rect4(junk, q);
	Log("INFO  the OLD header's GetArea(cRZRect&) called slot 48: rect %s, stack %s",
		(q[0] == L && q[1] == T) ? "filled" : "NOT filled", b ? "balanced" : "OFF by 4 bytes");
	gInfo++;
}

static void TestColours(void* v)
{
	cIGZWin* w = ((WinCtx*)v)->w;
	bool b, b2, b3;
	cRZColor c, c2;
	BALANCED(b, w->GetFillColor(c));
	uint32_t native = 0;
	BALANCED(b2, native = w->GetFillColor());
	uint8_t rr = 0, gg = 0, bb = 0;
	BALANCED(b3, w->GetFillColor(rr, gg, bb));
	Check(b && b2 && b3 && (c.raw & 0xFFFFFF) == ((uint32_t)rr << 16 | (uint32_t)gg << 8 | bb),
		"GetFillColor(cRZColor&) (102), () (103) and (r&,g&,b&) (104) agree: 0x%08X = (%u,%u,%u)", c.raw, rr, gg, bb);

	BALANCED(b, w->SetFillColor(c));
	w->GetFillColor(c2);
	Check(b && c2.raw == c.raw, "SetFillColor(cRZColor) BY VALUE (slot 105) stores the colour itself: 0x%08X", c2.raw);
	BALANCED(b, w->SetFillColor(rr, gg, bb));
	w->GetFillColor(c2);
	Check(b && (c2.raw & 0xFFFFFF) == (c.raw & 0xFFFFFF), "SetFillColor(r, g, b) (slot 107) keeps the colour: 0x%08X", c2.raw);
	BALANCED(b, w->SetFillColor(native));
	w->GetFillColor(c2);
	Log("INFO  SetFillColor(uint32_t native) (slot 106): stack %s, colour now 0x%08X", b ? "balanced" : "OFF", c2.raw);
	gInfo++;
	w->SetFillColor(c);
	w->GetFillColor(c2);
	Check(c2.raw == c.raw, "fill colour restored: 0x%08X", c2.raw);

	cRZColor s, s2;
	w->GetShadeColor(s);
	BALANCED(b, w->SetShadeColor(s));
	w->GetShadeColor(s2);
	Check(b && s2.raw == s.raw, "SetShadeColor(cRZColor) BY VALUE (slot 111) stores the colour itself: 0x%08X", s2.raw);

	uint32_t rgb = 0, nat = 0, back = 0;
	BALANCED(b, rgb = w->GetFillColorRGB());
	BALANCED(b2, w->SetFillColorRGB(rgb));
	Check(b && b2 && w->GetFillColorRGB() == rgb, "GetFillColorRGB (126) / SetFillColorRGB (125) round-trip 0x%08X", rgb);
	BALANCED(b, nat = w->ConvertPackedRGBToNative(0x00F84010));
	BALANCED(b2, back = w->ConvertNativeToPackedRGB(nat));
	Check(b && b2 && (back & 0xFFFFFF) == 0xF84010, "ConvertPackedRGBToNative (127) / ConvertNativeToPackedRGB (128): 0xF84010 -> 0x%08X -> 0x%08X", nat, back);
}

static void TestHandlers(void* v)
{
	cIGZWin* w = ((WinCtx*)v)->w;
	Log("handler window ID 0x%08X: its handlers 129-143 are the base class's", w->GetID());
	bool b, r;
#define H(label, call) do { r = true; BALANCED(b, r = w->call); \
	Check(b && !r, "%-44s stack %s, returned %d", label, b ? "balanced" : "OFF", (int)r); } while (0)
	H("GZOnCharacter(c) (slot 129)", GZOnCharacter(0));
	H("GZOnKeyDown(key, mods) (130)", GZOnKeyDown(0, 0));
	H("GZOnKeyUp(key, mods) (131)", GZOnKeyUp(0, 0));
	if (w->IsVisible()) H("GZOnSetFocus(cIGZWin*) (132)", GZOnSetFocus(nullptr));
	H("GZOnKillFocus(cIGZWin*) (133)", GZOnKillFocus(nullptr));
	H("GZOnMouseDownL(x, y, mods) (134)", GZOnMouseDownL(0, 0, 0));
	H("GZOnMouseDownR(x, y, mods) (135)", GZOnMouseDownR(0, 0, 0));
	H("GZOnMouseUpL(x, y, mods) (136)", GZOnMouseUpL(0, 0, 0));
	H("GZOnMouseUpR(x, y, mods) (137)", GZOnMouseUpR(0, 0, 0));
	H("GZOnMouseMove(x, y, mods) (138)", GZOnMouseMove(0, 0, 0));
	H("GZOnMouseWheel(x, y, mods, delta) (139)", GZOnMouseWheel(0, 0, 0, 0));
	H("GZOnCaptureChanged(old, new) (140)", GZOnCaptureChanged(nullptr, nullptr));
	H("GZOnMouseEnter(cIGZWin*) (141)", GZOnMouseEnter(nullptr));
	H("GZOnMouseExit(data) (142)", GZOnMouseExit(0));
	H("GZOnCommand(command, data) (143)", GZOnCommand(0, 0));
#undef H

	// Message type 0 is not one DoMessage handles, so these do nothing.
	cGZMessage m0(0);
	BALANCED(b, w->SendMsg(w, 0, 0, 0, 0));
	Check(b, "SendMsg(win, type, d1, d2, d3) (slot 144): stack balanced");
	BALANCED(b, w->SendMsg(w, m0));
	Check(b, "SendMsg(win, const cGZMessage&) (slot 145): stack balanced");
	BALANCED(b, w->PostMsg(w, 0, 0, 0, 0));
	Check(b, "PostMsg(win, type, d1, d2, d3) (slot 146): stack balanced");
	BALANCED(b, w->PostMsg(w, m0));
	Check(b, "PostMsg(win, const cGZMessage&) (slot 147): stack balanced");
}

#pragma optimize("", on)

// ------------------------------------------------------------ the scheduler
static UINT_PTR kTimerId = 0x5C4E;
static int gTicksWithUI = 0;
static bool gDone = false;

static void RunWindowTests()
{
	cISC4AppPtr sc4;
	cIGZWin* main = sc4 ? sc4->GetMainWindow() : nullptr;
	Pick pick;
	FindWindows(main, pick);
	if (!pick.geom)
	{
		Log("INFO  no plain visible window found under the main window; window tests skipped");
		gInfo++;
		return;
	}
	WinCtx g = { pick.geom, pick.geom->GetParentWin() };
	Run("cIGZWin geometry, moves and keys", TestGeometry, &g);
	Run("cIGZWin colours", TestColours, &g);
	WinCtx h = { pick.plain, pick.plain->GetParentWin() };
	Run("cIGZWin input handlers and messages", TestHandlers, &h);
}

static LRESULT CALLBACK Subclass(HWND hwnd, UINT msg, WPARAM wp, LPARAM lp, UINT_PTR id, DWORD_PTR)
{
	if (msg == WM_TIMER && wp == kTimerId && !gDone)
	{
		cISC4AppPtr sc4;
		cIGZWin* main = sc4 ? sc4->GetMainWindow() : nullptr;
		if (main && main->GetChildCount() > 0 && ++gTicksWithUI >= 8)
		{
			gDone = true;
			KillTimer(hwnd, kTimerId);
			RunWindowTests();
			Log("\nDONE: %d passed, %d failed, %d info", gPass, gFail, gInfo);
			RemoveWindowSubclass(hwnd, Subclass, id);
		}
		return 0;
	}
	return DefSubclassProc(hwnd, msg, wp, lp);
}

class SC4HeaderTestDirector : public cRZCOMDllDirector
{
public:
	uint32_t GetDirectorID() const { return kDirectorID; }

	bool OnStart(cIGZCOM* pCOM)
	{
		char path[MAX_PATH];
		HMODULE self = nullptr;
		GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
			(LPCSTR)&kDirectorID, &self);
		GetModuleFileNameA(self, path, MAX_PATH);
		char* slash = strrchr(path, '\\');
		if (slash) strcpy_s(slash + 1, MAX_PATH - (slash + 1 - path), "SC4HeaderTest.log");
		fopen_s(&gLog, path, "w");
		Log("SC4HeaderTest: fixed gzcom-dll headers (fix-vtable-order) checked inside the game");
		Log("OnStart reached: the game loaded this plugin's director (GetDirectorID now at slot 13)");
		RZGetFrameWork()->AddHook(this);
		return true;
	}

	bool PostAppInit()
	{
		Run("cIGZApp", TestApp, nullptr);
		Run("cIGZCOMDirector", TestDirectors, nullptr);
		cIGZFrameWorkW32* w32 = nullptr;
		if (RZGetFrameWork()->QueryInterface(GZIID_cIGZFrameWorkW32, (void**)&w32) && w32)
		{
			HWND hwnd = w32->GetMainHWND();
			if (hwnd && SetWindowSubclass(hwnd, Subclass, 1, 0))
			{
				SetTimer(hwnd, kTimerId, 1000, nullptr);
				Log("\nwindow tests will run 8 s after the UI appears");
			}
			w32->Release();
		}
		return true;
	}

	bool PreAppShutdown()
	{
		Log("\nPreAppShutdown reached: the game is closing normally with this plugin loaded");
		if (gLog) { fclose(gLog); gLog = nullptr; }
		return true;
	}
};

cRZCOMDllDirector* RZGetCOMDllDirector()
{
	static SC4HeaderTestDirector sDirector;
	return &sDirector;
}
