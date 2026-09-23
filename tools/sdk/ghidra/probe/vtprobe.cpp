// vtprobe.cpp - which vtable slot does OUR compiler give each cIGZWin method
// when it compiles the vendored gzcom-dll header? Built with /FAs by
// _tests\Test-GZWinHeaderSlots.py, which reads the slot out of the .asm and
// compares it to the slot the method REALLY occupies in SimCity 4.exe 1.1.641.
// Each probe's name is the method (and overload) it means to call; the gate
// owns the truth. Compile only - never linked, never run.
#include "cIGZWin.h"
#include "cRZRect.h"
#define P(name, call) extern "C" void __cdecl probe_##name(cIGZWin* w) { w->call; }
static cRZRect& R() { return *(cRZRect*)0; }
static cRZPoint& Pt() { return *(cRZPoint*)0; }
static cRZColor& C() { return *(cRZColor*)0; }
static uint8_t& B() { return *(uint8_t*)0; }
static cIGZString& S() { return *(cIGZString*)0; }
static cGZMessage& M() { return *(cGZMessage*)0; }

// --- every cIGZWin method src\ calls (the allowlist rows) ---
P(QueryInterface, QueryInterface(0, (void**)0))
P(Release, Release())
P(Init, Init())
P(GetMainWindow, GetMainWindow())
P(GetParentWin, GetParentWin())
P(GetChildCount, GetChildCount())
P(EnumChildren, EnumChildren(0, (cIGZWin::EnumChildrenCallback)0, 0))
P(GetChildWindowFromID, GetChildWindowFromID(0))
P(GetChildWindowFromIDRecursive, GetChildWindowFromIDRecursive(0))
P(GetW, GetW())
P(GetH, GetH())
P(GetL, GetL())
P(GetT, GetT())
P(GetR, GetR())
P(GetB, GetB())
P(SetW, SetW(1))
P(SetH, SetH(1))
P(GetID, GetID())
P(GetFlag, GetFlag((cIGZWin::tWinFlag)1))
P(SetFlag, SetFlag((cIGZWin::tWinFlag)1, true))
P(ShowWindow, ShowWindow())
P(HideWindow, HideWindow())
P(IsVisible, IsVisible())
P(IsEnabled, IsEnabled())
P(GetCaption, GetCaption())
P(SetCaption, SetCaption(S()))
P(GZPaint, GZPaint())
P(InvalidateSelf, InvalidateSelf())
P(InvalidateSelfAndParents, InvalidateSelfAndParents())
P(AddMessageFilter, AddMessageFilter((cIGZWinMessageFilter*)0))
P(RemoveMessageFilter, RemoveMessageFilter((cIGZWinMessageFilter*)0))
P(GZWinMoveTo, GZWinMoveTo(1, 2))

// --- declarations that compile to the WRONG exe slot (controls + deny list) ---
P(GetArea_rect, GetArea(R()))
P(GetArea_ptr, GetArea())
P(GetAreaAbsolute_rect, GetAreaAbsolute(R()))
P(GetAreaAbsolute_ptr, GetAreaAbsolute())
P(SetSize_wh, SetSize(1, 2))
P(SetArea_rect, SetArea(R()))
P(SetArea_ltrb, SetArea(1, 2, 3, 4))
P(FitRectToWindow, FitRectToWindow(R(), 0))
P(GetFillColor_color, GetFillColor(C()))
P(GetFillColor_void, GetFillColor())
P(GetFillColor_rgb, GetFillColor(B(), B(), B()))
P(SetFillColor_color, SetFillColor(C()))
P(SetFillColor_u32, SetFillColor((uint32_t)0))
P(SetFillColor_rgb, SetFillColor((uint8_t)0, (uint8_t)0, (uint8_t)0))
P(SetSize_pt, SetSize(Pt()))
P(CenterWindowInRect_ref, CenterWindowInRect(R()))
P(CenterWindowInRect_ptr, CenterWindowInRect(&R()))
P(IsPointInWindowWindowCoordinates, IsPointInWindowWindowCoordinates(1, 2))
P(PlotPresent, PlotPresent())
P(GZOnMouseWheel, GZOnMouseWheel(0, 0, 0))
P(GZOnCommand, GZOnCommand(1))
P(SendMsg_msg, SendMsg((cIGZWin*)0, M()))
P(SendMsg_5, SendMsg((cIGZWin*)0, 0, 0, 0, 0))
P(PostMsg_msg, PostMsg((cIGZWin*)0, M()))
P(PostMsg_5, PostMsg((cIGZWin*)0, 0, 0, 0, 0))
