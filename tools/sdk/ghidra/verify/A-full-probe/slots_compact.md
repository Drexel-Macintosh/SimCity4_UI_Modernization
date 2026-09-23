| hdr | declaration | compiled | Mac | exe | note |
|---:|---|---:|---:|---:|---|
| 0 | bool QueryInterface(u32, void**) | 0 | 0 |  |  |
| 1 | u32 AddRef() | 1 | 1 |  |  |
| 2 | u32 Release() | 2 | 2 |  |  |
| 3 | bool DoMessage(cGZMessage&) | 3 | 3 |  |  |
| 4 | bool Init() | 4 | 4 |  |  |
| 5 | bool Shutdown() | 5 | 5 |  |  |
| 6 | cIGZWinMgr* GetWindowManager() | 6 | 6 |  |  |
| 7 | bool SetWindowManager(cIGZWinMgr*) | 7 | 7 |  |  |
| 8 | cIGZKeyboard* GetKeyboard() | 8 | 8 |  |  |
| 9 | bool SetKeyboard(cIGZKeyboard*) | 9 | 9 |  |  |
| 10 | cIGZWin* GetMainWindow() | 10 | 10 |  |  |
| 11 | cIGZWin* GetParentWin() | 11 | 11 |  |  |
| 12 | bool SetParentWin(cIGZWin*) | 12 | 12 |  |  |
| 13 | i32 GetChildCount() | 13 | 13 |  |  |
| 14 | bool ChildAdd(cIGZWin*) | 14 | 14 |  |  |
| 15 | bool ChildRemove(cIGZWin*) | 15 | 15 |  |  |
| 16 | bool ChildDelete(cIGZWin*) | 16 | 16 |  |  |
| 17 | bool ChildDeleteAbsolute(cIGZWin*) | 17 | 17 |  |  |
| 18 | bool ChildDeleteAll() | 18 | 18 |  |  |
| 19 | bool ChildExists(cIGZWin*) | 20 | 19~ | 20d | C!=Mac(ord) |
| 20 | bool ChildExists(u32) | 19 | 20~ | 19d | C!=Mac(ord) |
| 21 | bool IsWinInParentChain(cIGZWin*) | 21 | 21 |  |  |
| 22 | bool IsWinInChildChain(cIGZWin*) | 22 | 22 |  |  |
| 23 | bool PullToFront() | 23 | 23 |  |  |
| 24 | bool SendToBack() | 24 | 24 |  |  |
| 25 | bool ChildToFront(cIGZWin*) | 26 | 25~ | 26d | C!=Mac(ord) |
| 26 | bool ChildToFront(u32) | 25 | 26~ | 25d | C!=Mac(ord) |
| 27 | bool ChildToBack(cIGZWin*) | 27 | 27 |  |  |
| 28 | bool ChildStepFront(cIGZWin*) | 28 | 28 |  |  |
| 29 | bool ChildStepBack(cIGZWin*) | 29 | 29 |  |  |
| 30 | bool MoveRelativeTo(cIGZWin*, bool) | 30 | 30 |  |  |
| 31 | bool ChildMoveRelative(cIGZWin*, cIGZWin*, bool) | 31 | 31 |  |  |
| 32 | bool EnumChildren(u32, EnumChildrenCallback, void*) | 32 | 32 |  |  |
| 33 | bool SortChildren(SortChildrenCallback, void*, bool) | 33 | 33 |  |  |
| 34 | cIGZWin* GetChildWindowFromID(u32) | 34 | 34 |  |  |
| 35 | cIGZWin* GetChildWindowFromIDRecursive(u32) | 35 | 35 | 35 |  |
| 36 | bool GetChildAs(u32, u32, void**) | 36 | 36 | 36 |  |
| 37 | bool GetChildAsRecursive(u32, u32, void**) | 37 | 37 | 37 |  |
| 38 | cIGZWin* GetWindowFromPoint(i32, i32) | 38 | 38 |  |  |
| 39 | cIGZWin* GetChildWindowFromPoint(i32, i32) | 39 | 39 |  |  |
| 40 | cIGZWin* GetChildWindowFromCursorPoint(i32, i32) | 40 | 40 |  |  |
| 41 | i32 GetW() const | 41 | 41 | 41 |  |
| 42 | i32 GetH() const | 42 | 42 | 42 |  |
| 43 | i32 GetL() const | 43 | 43 |  |  |
| 44 | i32 GetT() const | 44 | 44 |  |  |
| 45 | i32 GetR() const | 45 | 45 |  |  |
| 46 | i32 GetB() const | 46 | 46 |  |  |
| 47 | bool GetArea(cRZRect&) const | 48 | 47~ | 47d | C!=Mac(ord) C!=EXE |
| 48 | i32* GetArea() const | 47 | 48~ | 48 | C!=Mac(ord) C!=EXE |
| 49 | bool GetAreaAbsolute(cRZRect&) const | 50 | 49~ | 49d | C!=Mac(ord) C!=EXE |
| 50 | i32* GetAreaAbsolute() const | 49 | 50~ | 50d | C!=Mac(ord) C!=EXE |
| 51 | bool SetW(i32) | 51 | 51 | 51 |  |
| 52 | bool SetH(i32) | 52 | 52 | 52 |  |
| 53 | bool SetSize(i32, i32) | 54 | 53~ | 53 | C!=Mac(ord) C!=EXE |
| 54 | bool SetArea(const cRZRect&) | 56 | 54~ | 54 | C!=Mac(ord) C!=EXE |
| 55 | bool SetArea(i32, i32, i32, i32) | 55 | 55~ | 55 |  |
| 56 | bool GZWinMoveTo(i32, i32) | 57 | 56 | 56 | C!=Mac C!=EXE |
| 57 | bool FitRectToWindow(cRZRect&, i32) | 58 | 58 | 58 |  |
| 58 | bool ScreenToWindowCoordinates(i32&, i32&) const | 59 | 59 |  |  |
| 59 | bool WindowToScreenCoordinates(i32&, i32&) const | 60 | 60 |  |  |
| 60 | bool WindowToWindowCoordinates(cIGZWin*, i32&, i32&) const | 61 | 61 |  |  |
| 61 | bool IsPointInWindowScreenCoordinates(i32, i32) const | 62 | 62 |  |  |
| 62 | u32 GetID() const | 63 | 63 | 63 |  |
| 63 | bool SetID(u32) | 64 | 64 | 64 |  |
| 64 | u32 GetInstanceID() const | 65 | 65 |  |  |
| 65 | bool SetInstanceID(u32) | 66 | 66 |  |  |
| 66 | bool GetFlag(tWinFlag) const | 67 | 67 | 67 |  |
| 67 | tWinFlag SetFlag(tWinFlag, bool) | 68 | 68 | 68 |  |
| 68 | bool ShowWindow() | 69 | 69 | 69 |  |
| 69 | bool HideWindow() | 70 | 70 | 70 |  |
| 70 | bool IsVisible() const | 71 | 71 |  |  |
| 71 | bool IsEnabled() const | 72 | 72 |  |  |
| 72 | cIGZString* GetCaption() const | 73 | 73 |  |  |
| 73 | bool SetCaption(cIGZString const&) | 74 | 74 |  |  |
| 74 | cIGZWinKeyAccelerator* GetKeyboardAccelerator() | 75 | 75 |  |  |
| 75 | bool SetKeyboardAccelerator(cIGZWinKeyAccelerator*) | 76 | 76 |  |  |
| 76 | bool AccelerateKeyboardMsg() | 77 | 77 |  |  |
| 77 | u32 GetKeyEquivalent() | 78 | 78 |  |  |
| 78 | bool SetKeyEquivalent(u32) | 79 | 79 |  |  |
| 79 | bool CheckKeyEquivalent(u32) | 80 | 80 |  |  |
| 80 | u32 MakeKeyEquivalent(u32, u32) | 81 | 81 |  |  |
| 81 | bool IsChildKeyEquivalent(u32, u32) | 82 | 82 |  |  |
| 82 | bool ProcessCursorMessage(cGZMessage&) | 83 | 83 |  |  |
| 83 | bool UpdateCursor() | 84 | 84 |  |  |
| 84 | bool SetCursor(cIGZCursor*, bool) | 85 | 85 |  |  |
| 85 | bool SetNotificationTarget(cIGZWin*) | 86 | 86 | 86 |  |
| 86 | cIGZWin* GetNotificationTarget() | 87 | 87 | 87 |  |
| 87 | bool GZPaint() | 88 | 88 | 88 |  |
| 88 | bool Plot() | 89 | 89 |  |  |
| 89 | intptr_t CalcAbsoluteArea() | 90 | 90 |  |  |
| 90 | void InvalidateSelf() | 91 | 91 |  |  |
| 91 | void InvalidateSelfAndParents() | 92 | 92 |  |  |
| 92 | intptr_t GetDrawContext() | 93 | 93 |  |  |
| 93 | intptr_t GetBufferToDrawTo() | 94 | 94 |  |  |
| 94 | void SetBufferToDrawTo() | 95 | 95 |  |  |
| 95 | void SetBufferToDrawToRecursive() | 96 | 96 |  |  |
| 96 | void SetAreaToDrawTo() | 97 | 97 |  |  |
| 97 | void SetAreaToDrawToRecursive() | 98 | 98 |  |  |
| 98 | intptr_t GetAreaToDrawTo() | 99 | 99 |  |  |
| 99 | bool PrivateBuffer(bool) | 100 | 100 |  |  |
| 100 | intptr_t GetPrivateBuffer() | 101 | 101 |  |  |
| 101 | bool GetFillColor(cRZColor&) | 104 | 102~ | 102d | C!=Mac(ord) C!=EXE |
| 102 | u32 GetFillColor() | 103 | 104~ | 103d | C!=Mac(ord) |
| 103 | void GetFillColor(u8&, u8&, u8&) | 102 | 106~ | 104d | C!=Mac(ord) C!=EXE |
| 104 | bool SetFillColor(cRZColor const&) | 107 | 103~ | 105d | C!=Mac(ord) C!=EXE |
| 105 | void SetFillColor(u32) | 106 | 105~ | 106d | C!=Mac(ord) |
| 106 | void SetFillColor(u8, u8, u8) | 105 | 107~ | 107d | C!=Mac(ord) C!=EXE |
| 107 | bool MakeFillColor(u8, u8, u8) | 108 | 108 |  |  |
| 108 | void SetFadeEffectPeriod(i32, i32) | 109 | 109 |  |  |
| 109 | void GetFadeEffectPeriod(i32&, i32&) | 110 | 110 |  |  |
| 110 | void SetShadeColor(cRZColor const&) | 111 | 111 |  |  |
| 111 | void GetShadeColor(cRZColor&) | 112 | 112 |  |  |
| 112 | bool GetParam(u32, cIGZVariant**) | 113 | 113 |  |  |
| 113 | bool SetParam(u32, cIGZVariant*) | 114 | 114 |  |  |
| 114 | bool EnumParams(EnumParamsCallback, void*) | 115 | 115 |  |  |
| 115 | bool AddMessageFilter(cIGZWinMessageFilter*) | 116 | 116 |  |  |
| 116 | bool RemoveMessageFilter(cIGZWinMessageFilter*) | 117 | 117 |  |  |
| 117 | bool SetSize(cRZPoint const&) | 53 | 118~ | 118 | C!=Mac(ord) C!=EXE |
| 118 | void CenterWindowInRect(cRZRect const&) | 119 | 119~ | 119 |  |
| 119 | void CenterWindowInRect(cRZRect*) | 118 | 120~ | 120 | C!=Mac(ord) C!=EXE |
| 120 | bool IsPointInWindowWindowCoordinates(i32, i32) | 120 | 121 |  | C!=Mac |
| 121 | bool IsPointInWindowParentCoordinates(i32, i32) | 121 | 122 |  | C!=Mac |
| 122 | bool PlotComposite() | 122 | 123 |  | C!=Mac |
| 123 | bool PlotPresent() | 123 | 124 | 124 | C!=Mac C!=EXE |
| 124 | void SetFillColorRGB(u32) | 124 | 125 |  | C!=Mac |
| 125 | u32 GetFillColorRGB() | 125 | 126 |  | C!=Mac |
| 126 | u32 ConvertPackedRGBToNative(u32) | 126 | 127 |  | C!=Mac |
| 127 | u32 ConvertNativeToPackedRGB(u32) | 127 | 128 |  | C!=Mac |
| 128 | bool GZOnCharacter(int8_t) | 128 | 129 |  | C!=Mac |
| 129 | bool GZOnKeyDown(u32, u32) | 129 | 130 |  | C!=Mac |
| 130 | bool GZOnKeyUp(u32, u32) | 130 | 131 |  | C!=Mac |
| 131 | bool GZOnSetFocus(u32, u32) | 131 | 132 |  | C!=Mac |
| 132 | bool GZOnKillFocus(cIGZWin*) | 132 | 133 |  | C!=Mac |
| 133 | bool GZOnMouseDownL(i32, i32, u32) | 133 | 134 |  | C!=Mac |
| 134 | bool GZOnMouseDownR(i32, i32, u32) | 134 | 135 |  | C!=Mac |
| 135 | bool GZOnMouseUpL(i32, i32, u32) | 135 | 136 |  | C!=Mac |
| 136 | bool GZOnMouseUpR(i32, i32, u32) | 136 | 137 |  | C!=Mac |
| 137 | bool GZOnMouseMove(i32, i32, u32) | 137 | 138 |  | C!=Mac |
| 138 | bool GZOnMouseWheel(i32, i32, u32) | 138 | 139 |  | C!=Mac |
| 139 | bool GZOnCaptureChanged(cIGZWin*, u32, u32, u32) | 139 | 140 |  | C!=Mac |
| 140 | bool GZOnMouseEnter(u32, u32) | 140 | 141 |  | C!=Mac |
| 141 | bool GZOnMouseExit(u32) | 141 | 142 |  | C!=Mac |
| 142 | bool GZOnCommand(u32) | 142 | 143 |  | C!=Mac |
| 143 | bool SendMsg(cIGZWin*, cGZMessage const&) | 144 | 144~ | 145d | C!=EXE |
| 144 | bool SendMsg(cIGZWin*, u32, u32, u32, u32) | 143 | 145~ | 144d | C!=Mac(ord) C!=EXE |
| 145 | bool PostMsg(cIGZWin*, cGZMessage const&) | 146 | 146~ | 147d | C!=EXE |
| 146 | bool PostMsg(cIGZWin*, u32, u32, u32, u32) | 145 | 147~ | 146d | C!=Mac(ord) C!=EXE |
