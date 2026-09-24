# In-game run 3 (2026-09-23 20:41), SC4HeaderTest built from commit f975656

The log exactly as the plugin wrote it. Runs 1 and 2 are summarised in README.md.

```
SC4HeaderTest: fixed gzcom-dll headers (fix-vtable-order) checked inside the game
OnStart reached: the game loaded this plugin's director (GetDirectorID now at slot 13)

== cIGZApp
framework 03100014, app 03120040
PASS  cIGZApp::FrameWork() (slot 10) returns the framework 03100014 (got 03100014, stack balanced)
PASS  cIGZApp::ModuleName() (slot 5) returns "SimCity 4" (stack balanced)
PASS  cIGZApp::AsIGZSystemService() (slot 3) returns 03120024
INFO  the OLD header's FrameWork() called slot 5 and got 059E1574 = "SimCity 4", not the framework 03100014

== cIGZCOMDirector
PASS  this plugin's director: GetDirectorID() through cIGZCOMDirector (slot 13) = 0x5C4E0A17
PASS  game director at 00B63690 (vtable 0x00AD8BA0): GetDirectorID() through cIGZCOMDirector (slot 13) = 0xC3CAEC3B, expected 0xC3CAEC3B
PASS  the same director's FrameWork() (slot 11) is the live framework: 03100014

window tests will run 8 s after the UI appears

70 windows under the main window; geometry window: does not override any method under test (vtable 00A92F28)

== cIGZWin geometry, moves and keys
window ID 0x6104489A at (0,0)-(2400,1600), 2400x1600; parent ID 0x00000000
PASS  GetArea(cRZRect&) (slot 47) fills (0,0,2400,1600)
PASS  GetArea() (slot 48) points at the same rect
PASS  GetAreaAbsolute(cRZRect&) (49) and GetAreaAbsolute() (50) agree, and equal the parent's absolute origin + (0,0): (0,0)
PASS  GZWinOffset(3, 2) (slot 57) moves BY: now (3,2)
PASS  GZWinOffset(-3, -2) puts it back
PASS  GZWinMoveTo(L+5, T+4) (slot 56) moves TO: now (5,4)
PASS  GZWinMoveTo(L, T) puts it back
PASS  SetSize(w, h) (slot 53) resizes: now 2402x1601
PASS  SetSize(cRZPoint) -> SetSizeFromPoint (slot 118) resizes: now 2401x1602
PASS  SetSize(W, H) puts it back
PASS  SetArea(const cRZRect&) (slot 54) sets the rect: now (1,1)
PASS  SetArea(l, t, r, b) (slot 55) puts it back
PASS  CenterWindowInRect(cRZRect*) (slot 120) accepts null (the reference overload at 119 would not)
INFO  CenterWindowInRect(own rect) (slot 119): stack balanced, window now at (0,0)
PASS  window back at (0,0)
PASS  IsPointInWindowWindowCoordinates (121) and ...ParentCoordinates (122): centre in, (-5,-5) out
PASS  CheckKeyEquivalent(key, modifiers) (slot 80): its own key 0x00000000 matches, another does not
PASS  AccelerateKeyboardMsg(msg) (slot 77) with no accelerator returns false
INFO  the OLD header's GetArea(cRZRect&) called slot 48: rect NOT filled, stack OFF by 4 bytes

== cIGZWin colours
PASS  GetFillColor(cRZColor&) (102), () (103) and (r&,g&,b&) (104) agree: 0x00000000 = (0,0,0)
PASS  SetFillColor(cRZColor) BY VALUE (slot 105) stores the colour itself: set 0x00336699, read 0x00336699 = (51,102,153)
PASS  SetFillColor(r, g, b) (slot 107) sets (0x12,0x34,0x56): read 0x00123456
INFO  SetFillColor(uint32_t native) (slot 106) with the original colour's native value: stack balanced, colour now 0x00000000
PASS  fill colour restored: 0x00000000
PASS  SetShadeColor(cRZColor) BY VALUE (slot 111) stores the colour itself: set 0xFF5A5A5A, read 0xFF5A5A5A
PASS  shade colour restored: 0xFFFFFFFF
PASS  SetFillColorRGB (125) / GetFillColorRGB (126): set 0x00336699, read 0x00336699
PASS  fill colour restored again: 0x00000000
PASS  ConvertPackedRGBToNative (127) / ConvertNativeToPackedRGB (128): 0xF84010 -> 0xFFF84010 -> 0xFFF84010

== cIGZWin input handlers and messages
PASS  GZOnCharacter(c) (slot 129)                  stack balanced, returned 0 (window 0x6104489A)
PASS  GZOnKeyDown(key, mods) (130)                 stack balanced, returned 0 (window 0x6A0AF41D)
PASS  GZOnKeyUp(key, mods) (131)                   stack balanced, returned 0 (window 0x6A0AF41D)
PASS  GZOnSetFocus(cIGZWin*) (132)                 stack balanced, returned 0 (window 0x6104489A)
PASS  GZOnKillFocus(cIGZWin*) (133)                stack balanced, returned 0 (window 0x6104489A)
PASS  GZOnMouseDownL(x, y, mods) (134)             stack balanced, returned 0 (window 0x6104489A)
PASS  GZOnMouseDownR(x, y, mods) (135)             stack balanced, returned 0 (window 0x6104489A)
PASS  GZOnMouseUpL(x, y, mods) (136)               stack balanced, returned 0 (window 0x6104489A)
PASS  GZOnMouseUpR(x, y, mods) (137)               stack balanced, returned 0 (window 0x6104489A)
PASS  GZOnMouseMove(x, y, mods) (138)              stack balanced, returned 0 (window 0x6104489A)
PASS  GZOnMouseWheel(x, y, mods, delta) (139)      stack balanced, returned 0 (window 0x6104489A)
PASS  GZOnCaptureChanged(old, new) (140)           stack balanced, returned 0 (window 0x6104489A)
PASS  GZOnMouseEnter(cIGZWin*) (141)               stack balanced, returned 0 (window 0x6104489A)
PASS  GZOnMouseExit(data) (142)                    stack balanced, returned 0 (window 0x6104489A)
PASS  GZOnCommand(command, data) (143)             stack balanced, returned 0 (window 0x6A0AF41D)
PASS  SendMsg(win, type, d1, d2, d3) (slot 144): stack balanced
PASS  SendMsg(win, const cGZMessage&) (slot 145): stack balanced
PASS  PostMsg(win, type, d1, d2, d3) (slot 146): stack balanced
PASS  PostMsg(win, const cGZMessage&) (slot 147): stack balanced

DONE: 51 passed, 0 failed, 4 info

PreAppShutdown reached: the game is closing normally with this plugin loaded
```
