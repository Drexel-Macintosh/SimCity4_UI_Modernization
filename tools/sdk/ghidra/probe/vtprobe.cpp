// vtprobe.cpp - which vtable slot does OUR compiler give each cIGZWin method
// when it compiles the vendored gzcom-dll header? Built with /FAs by
// _tests\Test-GZWinHeaderSlots.py, which reads the slot out of the .asm and
// compares it to the slot the method REALLY occupies in SimCity 4.exe 1.1.641.
// Each probe's name is the method it means to call; the gate owns the truth.
#include "cIGZWin.h"
#define P(name, call) extern "C" void __cdecl probe_##name(cIGZWin* w) { w->call; }
static cRZRect& R() { return *(cRZRect*)0; }
static cRZPoint& Pt() { return *(cRZPoint*)0; }
P(SetW, SetW(1))
P(SetH, SetH(1))
P(SetSize_wh, SetSize(1, 2))
P(SetArea_rect, SetArea(R()))
P(SetArea_ltrb, SetArea(1, 2, 3, 4))
P(GZWinMoveTo, GZWinMoveTo(1, 2))
P(FitRectToWindow, FitRectToWindow(R(), 0))
P(GetID, GetID())
P(SetFlag, SetFlag((cIGZWin::tWinFlag)1, true))
P(ShowWindow, ShowWindow())
P(GZPaint, GZPaint())
P(SetSize_pt, SetSize(Pt()))
P(CenterWindowInRect_ref, CenterWindowInRect(R()))
P(CenterWindowInRect_ptr, CenterWindowInRect(&R()))
P(IsPointInWindowWindowCoordinates, IsPointInWindowWindowCoordinates(1, 2))
P(PlotPresent, PlotPresent())
P(GZOnCommand, GZOnCommand(1))
