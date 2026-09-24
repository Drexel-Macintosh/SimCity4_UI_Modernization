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
// The whole window tree under the main window, breadth first.
struct Node { cIGZWin* w; cIGZWin* parent; };
static Node gAll[4096];
static int gAllN = 0;

static bool CollectAll(cIGZWin* parent, uint32_t, void* child, void*)
{
	if (child && gAllN < 4096) { gAll[gAllN].w = (cIGZWin*)child; gAll[gAllN].parent = parent; gAllN++; }
	return true;
}

static void WalkTree(cIGZWin* root)
{
	gAllN = 0;
	root->EnumChildren(GZIID_cIGZWin, CollectAll, nullptr);
	for (int head = 0; head < gAllN && gAllN < 4096; head++)
		gAll[head].w->EnumChildren(GZIID_cIGZWin, CollectAll, nullptr);
}

static bool SameAsBase(cIGZWin* w, int from, int to)
{
	void** vt = *(void***)w;
	void** bvt = (void**)Rebase(0x00ADC8D8);
	for (int s = from; s <= to; s++)
		if (vt[s] != bvt[s]) return false;
	return true;
}

// A window the geometry and colour tests can use: visible, with a parent, and
// not overriding the methods under test, so the base class's code runs.
static bool PlainGeometry(cIGZWin* w)
{
	return SameAsBase(w, 41, 60) && SameAsBase(w, 75, 80) && SameAsBase(w, 102, 107)
		&& SameAsBase(w, 111, 112) && SameAsBase(w, 118, 128);
}

// A window away from its parent's origin, inside a parent away from the
// screen's origin, tells relative from absolute and "move by" from "move to".
static bool Offset(int i)
{
	cIGZWin* w = gAll[i].w;
	cRZRect pa;
	int32_t q[4];
	gAll[i].parent->GetAreaAbsolute(pa);
	Rect4(pa, q);
	return w->GetL() > 0 && w->GetT() > 0 && (q[0] > 0 || q[1] > 0);
}

static int FindGeometryWindow(bool strict)
{
	for (int pass = 0; pass < 2; pass++)
		for (int i = 0; i < gAllN; i++)
		{
			cIGZWin* w = gAll[i].w;
			if (!gAll[i].parent || !w->IsVisible() || w->GetW() < 12 || w->GetH() < 12) continue;
			if (strict && !PlainGeometry(w)) continue;
			if (pass == 0 && !Offset(i)) continue;
			return i;
		}
	return -1;
}

// For one handler slot: a visible window whose entry there is the base
// class's, so the call runs the shared stub (or base SetFocus, a no-op on a
// visible window).
static cIGZWin* FindHandlerWindow(int slot)
{
	for (int i = 0; i < gAllN; i++)
		if (gAll[i].w->IsVisible() && SameAsBase(gAll[i].w, slot, slot)) return gAll[i].w;
	return nullptr;
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

	// Set colours DIFFERENT from the current ones, read them back through
	// every getter, then restore. A setter that did nothing, or stored a
	// pointer, reads back wrong.
	cRZColor t;
	t.raw = (c.raw & 0xFF000000) | (((c.raw & 0xFFFFFF) == 0x336699) ? 0x996633 : 0x336699);
	const uint32_t want = t.raw & 0xFFFFFF;
	BALANCED(b, w->SetFillColor(t));
	w->GetFillColor(c2);
	uint8_t r2 = 0, g2 = 0, b2_ = 0;
	w->GetFillColor(r2, g2, b2_);
	Check(b && c2.raw == t.raw && ((uint32_t)r2 << 16 | (uint32_t)g2 << 8 | b2_) == want,
		"SetFillColor(cRZColor) BY VALUE (slot 105) stores the colour itself: set 0x%08X, read 0x%08X = (%u,%u,%u)",
		t.raw, c2.raw, r2, g2, b2_);
	BALANCED(b, w->SetFillColor((uint8_t)0x12, (uint8_t)0x34, (uint8_t)0x56));
	w->GetFillColor(c2);
	Check(b && (c2.raw & 0xFFFFFF) == 0x123456, "SetFillColor(r, g, b) (slot 107) sets (0x12,0x34,0x56): read 0x%08X", c2.raw);
	BALANCED(b, w->SetFillColor(native));
	w->GetFillColor(c2);
	Log("INFO  SetFillColor(uint32_t native) (slot 106) with the original colour's native value: stack %s, colour now 0x%08X",
		b ? "balanced" : "OFF", c2.raw);
	gInfo++;
	w->SetFillColor(c);
	w->GetFillColor(c2);
	Check(c2.raw == c.raw, "fill colour restored: 0x%08X", c2.raw);

	cRZColor s, s2, ts;
	w->GetShadeColor(s);
	ts.raw = s.raw ^ 0x00A5A5A5;
	BALANCED(b, w->SetShadeColor(ts));
	w->GetShadeColor(s2);
	Check(b && s2.raw == ts.raw, "SetShadeColor(cRZColor) BY VALUE (slot 111) stores the colour itself: set 0x%08X, read 0x%08X",
		ts.raw, s2.raw);
	w->SetShadeColor(s);
	w->GetShadeColor(s2);
	Check(s2.raw == s.raw, "shade colour restored: 0x%08X", s2.raw);

	uint32_t rgb = 0, nat = 0, back = 0, now = 0;
	BALANCED(b, rgb = w->GetFillColorRGB());
	BALANCED(b2, w->SetFillColorRGB(0x00336699));
	now = w->GetFillColorRGB();
	Check(b && b2 && now == 0x00336699, "SetFillColorRGB (125) / GetFillColorRGB (126): set 0x00336699, read 0x%08X", now);
	w->SetFillColorRGB(rgb);
	w->SetFillColor(c);
	w->GetFillColor(c2);
	Check(w->GetFillColorRGB() == rgb && c2.raw == c.raw, "fill colour restored again: 0x%08X", c2.raw);
	BALANCED(b, nat = w->ConvertPackedRGBToNative(0x00F84010));
	BALANCED(b2, back = w->ConvertNativeToPackedRGB(nat));
	Check(b && b2 && (back & 0xFFFFFF) == 0xF84010, "ConvertPackedRGBToNative (127) / ConvertNativeToPackedRGB (128): 0xF84010 -> 0x%08X -> 0x%08X", nat, back);
}

static void TestHandlers(void* v)
{
	cIGZWin* w = ((WinCtx*)v)->w;
	bool b, r;
	cIGZWin* hw;
	// Each handler runs on a window whose entry for that slot is the base
	// class's, so it reaches the shared stub for its argument size.
#define H(slot, label, call) do { hw = FindHandlerWindow(slot); \
	if (!hw) { Log("INFO  %-44s no window with the base handler; skipped", label); gInfo++; break; } \
	r = true; BALANCED(b, r = hw->call); \
	Check(b && !r, "%-44s stack %s, returned %d (window 0x%08X)", label, b ? "balanced" : "OFF", (int)r, hw->GetID()); } while (0)
	H(129, "GZOnCharacter(c) (slot 129)", GZOnCharacter(0));
	H(130, "GZOnKeyDown(key, mods) (130)", GZOnKeyDown(0, 0));
	H(131, "GZOnKeyUp(key, mods) (131)", GZOnKeyUp(0, 0));
	H(132, "GZOnSetFocus(cIGZWin*) (132)", GZOnSetFocus(nullptr));
	H(133, "GZOnKillFocus(cIGZWin*) (133)", GZOnKillFocus(nullptr));
	H(134, "GZOnMouseDownL(x, y, mods) (134)", GZOnMouseDownL(0, 0, 0));
	H(135, "GZOnMouseDownR(x, y, mods) (135)", GZOnMouseDownR(0, 0, 0));
	H(136, "GZOnMouseUpL(x, y, mods) (136)", GZOnMouseUpL(0, 0, 0));
	H(137, "GZOnMouseUpR(x, y, mods) (137)", GZOnMouseUpR(0, 0, 0));
	H(138, "GZOnMouseMove(x, y, mods) (138)", GZOnMouseMove(0, 0, 0));
	H(139, "GZOnMouseWheel(x, y, mods, delta) (139)", GZOnMouseWheel(0, 0, 0, 0));
	H(140, "GZOnCaptureChanged(old, new) (140)", GZOnCaptureChanged(nullptr, nullptr));
	H(141, "GZOnMouseEnter(cIGZWin*) (141)", GZOnMouseEnter(nullptr));
	H(142, "GZOnMouseExit(data) (142)", GZOnMouseExit(0));
	H(143, "GZOnCommand(command, data) (143)", GZOnCommand(0, 0));
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

// Returns false when the tree has no usable window yet (keep waiting).
static bool RunWindowTests()
{
	cISC4AppPtr sc4;
	cIGZWin* main = sc4 ? sc4->GetMainWindow() : nullptr;
	if (!main) return false;
	WalkTree(main);
	int gi = FindGeometryWindow(true);
	const bool strict = gi >= 0;
	if (gi < 0) gi = FindGeometryWindow(false);
	if (gi < 0) return false;
	Log("\n%d windows under the main window; geometry window: %s (vtable %p)", gAllN,
		strict ? "does not override any method under test" : "a derived class (no plain window visible)",
		*(void**)gAll[gi].w);
	WinCtx g = { gAll[gi].w, gAll[gi].parent };
	Run("cIGZWin geometry, moves and keys", TestGeometry, &g);
	Run("cIGZWin colours", TestColours, &g);
	Run("cIGZWin input handlers and messages", TestHandlers, &g);
	return true;
}

static LRESULT CALLBACK Subclass(HWND hwnd, UINT msg, WPARAM wp, LPARAM lp, UINT_PTR id, DWORD_PTR)
{
	if (msg == WM_TIMER && wp == kTimerId && !gDone)
	{
		cISC4AppPtr sc4;
		cIGZWin* main = sc4 ? sc4->GetMainWindow() : nullptr;
		// Wait 8 s after the UI appears, then retry every 5 s until a usable
		// window exists, for up to 10 minutes.
		if (main && main->GetChildCount() > 0 && ++gTicksWithUI >= 8 && (gTicksWithUI - 8) % 5 == 0)
		{
			const bool ran = RunWindowTests();
			if (ran || gTicksWithUI > 600)
			{
				gDone = true;
				KillTimer(hwnd, kTimerId);
				if (!ran) { Log("INFO  no usable window appeared in 10 minutes; window tests skipped"); gInfo++; }
				Log("\nDONE: %d passed, %d failed, %d info", gPass, gFail, gInfo);
				RemoveWindowSubclass(hwnd, Subclass, id);
			}
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
