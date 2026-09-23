// Compile the VENDORED cIGZWin.h with MSVC and see which vtable offset each
// overload / handler lands on (read from the /FAs listing). This measures what
// OUR DLL would call, independent of the Mac layout and of the exe.
#include <cstdint>
#include "cIGZWin.h"

extern "C" {
bool t_SetArea_rect(cIGZWin* w, const cRZRect& r) { return w->SetArea(r); }
bool t_SetArea_ltrb(cIGZWin* w) { return w->SetArea(1, 2, 3, 4); }
bool t_GetArea_ref(cIGZWin* w, cRZRect& r) { return w->GetArea(r); }
int32_t* t_GetArea_ptr(cIGZWin* w) { return w->GetArea(); }
bool t_SetSize_wh(cIGZWin* w) { return w->SetSize(5, 6); }
bool t_SetSize_pt(cIGZWin* w, const cRZPoint& p) { return w->SetSize(p); }
void t_Center_ref(cIGZWin* w, const cRZRect& r) { w->CenterWindowInRect(r); }
void t_Center_ptr(cIGZWin* w, cRZRect* r) { w->CenterWindowInRect(r); }
bool t_IsPtWin(cIGZWin* w) { return w->IsPointInWindowWindowCoordinates(7, 8); }
bool t_PlotPresent(cIGZWin* w) { return w->PlotPresent(); }
bool t_OnChar(cIGZWin* w) { return w->GZOnCharacter(9); }
bool t_OnMouseMove(cIGZWin* w) { return w->GZOnMouseMove(1, 2, 3); }
bool t_OnMouseWheel(cIGZWin* w) { return w->GZOnMouseWheel(1, 2, 3); }
bool t_OnCapture(cIGZWin* w) { return w->GZOnCaptureChanged(w, 1, 2, 3); }
bool t_OnEnter(cIGZWin* w) { return w->GZOnMouseEnter(1, 2); }
bool t_OnExit(cIGZWin* w) { return w->GZOnMouseExit(1); }
bool t_OnCommand(cIGZWin* w) { return w->GZOnCommand(1); }
bool t_SendMsg_ref(cIGZWin* w, const cGZMessage& m) { return w->SendMsg(w, m); }
bool t_SendMsg_5(cIGZWin* w) { return w->SendMsg(w, 1, 2, 3, 4); }
bool t_PostMsg_ref(cIGZWin* w, const cGZMessage& m) { return w->PostMsg(w, m); }
bool t_PostMsg_5(cIGZWin* w) { return w->PostMsg(w, 1, 2, 3, 4); }
uint32_t t_GetID(cIGZWin* w) { return w->GetID(); }
uint32_t t_SetFlag(cIGZWin* w) { return (uint32_t)w->SetFlag(cIGZWin::WinFlag_Visible, true); }
}
