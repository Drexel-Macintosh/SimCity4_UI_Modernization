| hdr | declaration | compiled | pm-thunk | Mac | exe | flags |
|---:|---|---:|---:|---:|---:|---|
| 0 | `bool QueryInterface(uint32_t, void**)` | 0 | 0 | 0 |  |  |
| 1 | `uint32_t AddRef()` | 1 | 1 | 1 |  |  |
| 2 | `uint32_t Release()` | 2 | 2 | 2 |  |  |
| 3 | `bool DoMessage(cGZMessage&)` | 3 | 3 | 3 |  |  |
| 4 | `bool Init()` | 4 | 4 | 4 |  |  |
| 5 | `bool Shutdown()` | 5 | 5 | 5 |  |  |
| 6 | `cIGZWinMgr* GetWindowManager()` | 6 | 6 | 6 |  |  |
| 7 | `bool SetWindowManager(cIGZWinMgr*)` | 7 | 7 | 7 |  |  |
| 8 | `cIGZKeyboard* GetKeyboard()` | 8 | 8 | 8 |  |  |
| 9 | `bool SetKeyboard(cIGZKeyboard*)` | 9 | 9 | 9 |  |  |
| 10 | `cIGZWin* GetMainWindow()` | 10 | 10 | 10 |  |  |
| 11 | `cIGZWin* GetParentWin()` | 11 | 11 | 11 |  |  |
| 12 | `bool SetParentWin(cIGZWin*)` | 12 | 12 | 12 |  |  |
| 13 | `int32_t GetChildCount()` | 13 | 13 | 13 |  |  |
| 14 | `bool ChildAdd(cIGZWin*)` | 14 | 14 | 14 |  |  |
| 15 | `bool ChildRemove(cIGZWin*)` | 15 | 15 | 15 |  |  |
| 16 | `bool ChildDelete(cIGZWin*)` | 16 | 16 | 16 |  |  |
| 17 | `bool ChildDeleteAbsolute(cIGZWin*)` | 17 | 17 | 17 |  |  |
| 18 | `bool ChildDeleteAll()` | 18 | 18 | 18 |  |  |
| 19 | `bool ChildExists(cIGZWin*)` | 20 | 20 | 19~ | 20d | C!=MAC(ovl-ordinal) C!=HDR |
| 20 | `bool ChildExists(uint32_t)` | 19 | 19 | 20~ | 19d | C!=MAC(ovl-ordinal) C!=HDR |
| 21 | `bool IsWinInParentChain(cIGZWin*)` | 21 | 21 | 21 |  |  |
| 22 | `bool IsWinInChildChain(cIGZWin*)` | 22 | 22 | 22 |  |  |
| 23 | `bool PullToFront()` | 23 | 23 | 23 |  |  |
| 24 | `bool SendToBack()` | 24 | 24 | 24 |  |  |
| 25 | `bool ChildToFront(cIGZWin*)` | 26 | 26 | 25~ | 26d | C!=MAC(ovl-ordinal) C!=HDR |
| 26 | `bool ChildToFront(uint32_t)` | 25 | 25 | 26~ | 25d | C!=MAC(ovl-ordinal) C!=HDR |
| 27 | `bool ChildToBack(cIGZWin*)` | 27 | 27 | 27 |  |  |
| 28 | `bool ChildStepFront(cIGZWin*)` | 28 | 28 | 28 |  |  |
| 29 | `bool ChildStepBack(cIGZWin*)` | 29 | 29 | 29 |  |  |
| 30 | `bool MoveRelativeTo(cIGZWin*, bool)` | 30 | 30 | 30 |  |  |
| 31 | `bool ChildMoveRelative(cIGZWin*, cIGZWin*, bool)` | 31 | 31 | 31 |  |  |
| 32 | `bool EnumChildren(uint32_t, cIGZWin::EnumChildrenCallback, void*)` | 32 | 32 | 32 |  |  |
| 33 | `bool SortChildren(cIGZWin::SortChildrenCallback, void*, bool)` | 33 | 33 | 33 |  |  |
| 34 | `cIGZWin* GetChildWindowFromID(uint32_t)` | 34 | 34 | 34 |  |  |
| 35 | `cIGZWin* GetChildWindowFromIDRecursive(uint32_t)` | 35 | 35 | 35 | 35 |  |
| 36 | `bool GetChildAs(uint32_t, uint32_t, void**)` | 36 | 36 | 36 | 36 |  |
| 37 | `bool GetChildAsRecursive(uint32_t, uint32_t, void**)` | 37 | 37 | 37 | 37 |  |
| 38 | `cIGZWin* GetWindowFromPoint(int32_t, int32_t)` | 38 | 38 | 38 |  |  |
| 39 | `cIGZWin* GetChildWindowFromPoint(int32_t, int32_t)` | 39 | 39 | 39 |  |  |
| 40 | `cIGZWin* GetChildWindowFromCursorPoint(int32_t, int32_t)` | 40 | 40 | 40 |  |  |
| 41 | `int32_t GetW() const` | 41 | 41 | 41 | 41 |  |
| 42 | `int32_t GetH() const` | 42 | 42 | 42 | 42 |  |
| 43 | `int32_t GetL() const` | 43 | 43 | 43 |  |  |
| 44 | `int32_t GetT() const` | 44 | 44 | 44 |  |  |
| 45 | `int32_t GetR() const` | 45 | 45 | 45 |  |  |
| 46 | `int32_t GetB() const` | 46 | 46 | 46 |  |  |
| 47 | `bool GetArea(cRZRect&) const` | 48 | 48 | 47~ | 47d | C!=MAC(ovl-ordinal) C!=EXE C!=HDR |
| 48 | `int32_t* GetArea() const` | 47 | 47 | 48~ | 48 | C!=MAC(ovl-ordinal) C!=EXE C!=HDR |
| 49 | `bool GetAreaAbsolute(cRZRect&) const` | 50 | 50 | 49~ | 49d | C!=MAC(ovl-ordinal) C!=EXE C!=HDR |
| 50 | `int32_t* GetAreaAbsolute() const` | 49 | 49 | 50~ | 50d | C!=MAC(ovl-ordinal) C!=EXE C!=HDR |
| 51 | `bool SetW(int32_t)` | 51 | 51 | 51 | 51 |  |
| 52 | `bool SetH(int32_t)` | 52 | 52 | 52 | 52 |  |
| 53 | `bool SetSize(int32_t, int32_t)` | 54 | 54 | 53~ | 53 | C!=MAC(ovl-ordinal) C!=EXE C!=HDR |
| 54 | `bool SetArea(const cRZRect&)` | 56 | 56 | 54~ | 54 | C!=MAC(ovl-ordinal) C!=EXE C!=HDR |
| 55 | `bool SetArea(int32_t, int32_t, int32_t, int32_t)` | 55 | 55 | 55~ | 55 |  |
| 56 | `bool GZWinMoveTo(int32_t, int32_t)` | 57 | 57 | 56 | 56 | C!=MAC C!=EXE C!=HDR |
| 57 | `bool FitRectToWindow(cRZRect&, int32_t)` | 58 | 58 | 58 | 58 | C!=HDR |
| 58 | `bool ScreenToWindowCoordinates(int32_t&, int32_t&) const` | 59 | 59 | 59 |  | C!=HDR |
| 59 | `bool WindowToScreenCoordinates(int32_t&, int32_t&) const` | 60 | 60 | 60 |  | C!=HDR |
| 60 | `bool WindowToWindowCoordinates(cIGZWin*, int32_t&, int32_t&) const` | 61 | 61 | 61 |  | C!=HDR |
| 61 | `bool IsPointInWindowScreenCoordinates(int32_t, int32_t) const` | 62 | 62 | 62 |  | C!=HDR |
| 62 | `uint32_t GetID() const` | 63 | 63 | 63 | 63 | C!=HDR |
| 63 | `bool SetID(uint32_t)` | 64 | 64 | 64 | 64 | C!=HDR |
| 64 | `uint32_t GetInstanceID() const` | 65 | 65 | 65 |  | C!=HDR |
| 65 | `bool SetInstanceID(uint32_t)` | 66 | 66 | 66 |  | C!=HDR |
| 66 | `bool GetFlag(cIGZWin::tWinFlag) const` | 67 | 67 | 67 | 67 | C!=HDR |
| 67 | `tWinFlag SetFlag(cIGZWin::tWinFlag, bool)` | 68 | 68 | 68 | 68 | C!=HDR |
| 68 | `bool ShowWindow()` | 69 | 69 | 69 | 69 | C!=HDR |
| 69 | `bool HideWindow()` | 70 | 70 | 70 | 70 | C!=HDR |
| 70 | `bool IsVisible() const` | 71 | 71 | 71 |  | C!=HDR |
| 71 | `bool IsEnabled() const` | 72 | 72 | 72 |  | C!=HDR |
| 72 | `cIGZString* GetCaption() const` | 73 | 73 | 73 |  | C!=HDR |
| 73 | `bool SetCaption(cIGZString const&)` | 74 | 74 | 74 |  | C!=HDR |
| 74 | `cIGZWinKeyAccelerator* GetKeyboardAccelerator()` | 75 | 75 | 75 |  | C!=HDR |
| 75 | `bool SetKeyboardAccelerator(cIGZWinKeyAccelerator*)` | 76 | 76 | 76 |  | C!=HDR |
| 76 | `bool AccelerateKeyboardMsg()` | 77 | 77 | 77 |  | C!=HDR |
| 77 | `uint32_t GetKeyEquivalent()` | 78 | 78 | 78 |  | C!=HDR |
| 78 | `bool SetKeyEquivalent(uint32_t)` | 79 | 79 | 79 |  | C!=HDR |
| 79 | `bool CheckKeyEquivalent(uint32_t)` | 80 | 80 | 80 |  | C!=HDR |
| 80 | `uint32_t MakeKeyEquivalent(uint32_t, uint32_t)` | 81 | 81 | 81 |  | C!=HDR |
| 81 | `bool IsChildKeyEquivalent(uint32_t, uint32_t)` | 82 | 82 | 82 |  | C!=HDR |
| 82 | `bool ProcessCursorMessage(cGZMessage&)` | 83 | 83 | 83 |  | C!=HDR |
| 83 | `bool UpdateCursor()` | 84 | 84 | 84 |  | C!=HDR |
| 84 | `bool SetCursor(cIGZCursor*, bool)` | 85 | 85 | 85 |  | C!=HDR |
| 85 | `bool SetNotificationTarget(cIGZWin*)` | 86 | 86 | 86 | 86 | C!=HDR |
| 86 | `cIGZWin* GetNotificationTarget()` | 87 | 87 | 87 | 87 | C!=HDR |
| 87 | `bool GZPaint()` | 88 | 88 | 88 | 88 | C!=HDR |
| 88 | `bool Plot()` | 89 | 89 | 89 |  | C!=HDR |
| 89 | `intptr_t CalcAbsoluteArea()` | 90 | 90 | 90 |  | C!=HDR |
| 90 | `void InvalidateSelf()` | 91 | 91 | 91 |  | C!=HDR |
| 91 | `void InvalidateSelfAndParents()` | 92 | 92 | 92 |  | C!=HDR |
| 92 | `intptr_t GetDrawContext()` | 93 | 93 | 93 |  | C!=HDR |
| 93 | `intptr_t GetBufferToDrawTo()` | 94 | 94 | 94 |  | C!=HDR |
| 94 | `void SetBufferToDrawTo()` | 95 | 95 | 95 |  | C!=HDR |
| 95 | `void SetBufferToDrawToRecursive()` | 96 | 96 | 96 |  | C!=HDR |
| 96 | `void SetAreaToDrawTo()` | 97 | 97 | 97 |  | C!=HDR |
| 97 | `void SetAreaToDrawToRecursive()` | 98 | 98 | 98 |  | C!=HDR |
| 98 | `intptr_t GetAreaToDrawTo()` | 99 | 99 | 99 |  | C!=HDR |
| 99 | `bool PrivateBuffer(bool)` | 100 | 100 | 100 |  | C!=HDR |
| 100 | `intptr_t GetPrivateBuffer()` | 101 | 101 | 101 |  | C!=HDR |
| 101 | `bool GetFillColor(cRZColor&)` | 104 | 104 | 102~ | 102d | C!=MAC(ovl-ordinal) C!=EXE C!=HDR |
| 102 | `uint32_t GetFillColor()` | 103 | 103 | 104~ | 103d | C!=MAC(ovl-ordinal) C!=HDR |
| 103 | `void GetFillColor(uint8_t&, uint8_t&, uint8_t&)` | 102 | 102 | 106~ | 104d | C!=MAC(ovl-ordinal) C!=EXE C!=HDR |
| 104 | `bool SetFillColor(cRZColor const&)` | 107 | 107 | 103~ | 105d | C!=MAC(ovl-ordinal) C!=EXE C!=HDR |
| 105 | `void SetFillColor(uint32_t)` | 106 | 106 | 105~ | 106d | C!=MAC(ovl-ordinal) C!=HDR |
| 106 | `void SetFillColor(uint8_t, uint8_t, uint8_t)` | 105 | 105 | 107~ | 107d | C!=MAC(ovl-ordinal) C!=EXE C!=HDR |
| 107 | `bool MakeFillColor(uint8_t, uint8_t, uint8_t)` | 108 | 108 | 108 |  | C!=HDR |
| 108 | `void SetFadeEffectPeriod(int32_t, int32_t)` | 109 | 109 | 109 |  | C!=HDR |
| 109 | `void GetFadeEffectPeriod(int32_t&, int32_t&)` | 110 | 110 | 110 |  | C!=HDR |
| 110 | `void SetShadeColor(cRZColor const&)` | 111 | 111 | 111 |  | C!=HDR |
| 111 | `void GetShadeColor(cRZColor&)` | 112 | 112 | 112 |  | C!=HDR |
| 112 | `bool GetParam(uint32_t, cIGZVariant**)` | 113 | 113 | 113 |  | C!=HDR |
| 113 | `bool SetParam(uint32_t, cIGZVariant*)` | 114 | 114 | 114 |  | C!=HDR |
| 114 | `bool EnumParams(cIGZWin::EnumParamsCallback, void*)` | 115 | 115 | 115 |  | C!=HDR |
| 115 | `bool AddMessageFilter(cIGZWinMessageFilter*)` | 116 | 116 | 116 |  | C!=HDR |
| 116 | `bool RemoveMessageFilter(cIGZWinMessageFilter*)` | 117 | 117 | 117 |  | C!=HDR |
| 117 | `bool SetSize(cRZPoint const&)` | 53 | 53 | 118~ | 118 | C!=MAC(ovl-ordinal) C!=EXE C!=HDR |
| 118 | `void CenterWindowInRect(cRZRect const&)` | 119 | 119 | 119~ | 119 | C!=HDR |
| 119 | `void CenterWindowInRect(cRZRect*)` | 118 | 118 | 120~ | 120 | C!=MAC(ovl-ordinal) C!=EXE C!=HDR |
| 120 | `bool IsPointInWindowWindowCoordinates(int32_t, int32_t)` | 120 | 120 | 121 |  | C!=MAC |
| 121 | `bool IsPointInWindowParentCoordinates(int32_t, int32_t)` | 121 | 121 | 122 |  | C!=MAC |
| 122 | `bool PlotComposite()` | 122 | 122 | 123 |  | C!=MAC |
| 123 | `bool PlotPresent()` | 123 | 123 | 124 | 124 | C!=MAC C!=EXE |
| 124 | `void SetFillColorRGB(uint32_t)` | 124 | 124 | 125 |  | C!=MAC |
| 125 | `uint32_t GetFillColorRGB()` | 125 | 125 | 126 |  | C!=MAC |
| 126 | `uint32_t ConvertPackedRGBToNative(uint32_t)` | 126 | 126 | 127 |  | C!=MAC |
| 127 | `uint32_t ConvertNativeToPackedRGB(uint32_t)` | 127 | 127 | 128 |  | C!=MAC |
| 128 | `bool GZOnCharacter(int8_t)` | 128 | 128 | 129 |  | C!=MAC |
| 129 | `bool GZOnKeyDown(uint32_t, uint32_t)` | 129 | 129 | 130 |  | C!=MAC |
| 130 | `bool GZOnKeyUp(uint32_t, uint32_t)` | 130 | 130 | 131 |  | C!=MAC |
| 131 | `bool GZOnSetFocus(uint32_t, uint32_t)` | 131 | 131 | 132 |  | C!=MAC |
| 132 | `bool GZOnKillFocus(cIGZWin*)` | 132 | 132 | 133 |  | C!=MAC |
| 133 | `bool GZOnMouseDownL(int32_t, int32_t, uint32_t)` | 133 | 133 | 134 |  | C!=MAC |
| 134 | `bool GZOnMouseDownR(int32_t, int32_t, uint32_t)` | 134 | 134 | 135 |  | C!=MAC |
| 135 | `bool GZOnMouseUpL(int32_t, int32_t, uint32_t)` | 135 | 135 | 136 |  | C!=MAC |
| 136 | `bool GZOnMouseUpR(int32_t, int32_t, uint32_t)` | 136 | 136 | 137 |  | C!=MAC |
| 137 | `bool GZOnMouseMove(int32_t, int32_t, uint32_t)` | 137 | 137 | 138 |  | C!=MAC |
| 138 | `bool GZOnMouseWheel(int32_t, int32_t, uint32_t)` | 138 | 138 | 139 |  | C!=MAC |
| 139 | `bool GZOnCaptureChanged(cIGZWin*, uint32_t, uint32_t, uint32_t)` | 139 | 139 | 140 |  | C!=MAC |
| 140 | `bool GZOnMouseEnter(uint32_t, uint32_t)` | 140 | 140 | 141 |  | C!=MAC |
| 141 | `bool GZOnMouseExit(uint32_t)` | 141 | 141 | 142 |  | C!=MAC |
| 142 | `bool GZOnCommand(uint32_t)` | 142 | 142 | 143 |  | C!=MAC |
| 143 | `bool SendMsg(cIGZWin*, cGZMessage const&)` | 144 | 144 | 144~ | 145d | C!=EXE C!=HDR |
| 144 | `bool SendMsg(cIGZWin*, uint32_t, uint32_t, uint32_t, uint32_t)` | 143 | 143 | 145~ | 144d | C!=MAC(ovl-ordinal) C!=EXE C!=HDR |
| 145 | `bool PostMsg(cIGZWin*, cGZMessage const&)` | 146 | 146 | 146~ | 147d | C!=EXE C!=HDR |
| 146 | `bool PostMsg(cIGZWin*, uint32_t, uint32_t, uint32_t, uint32_t)` | 145 | 145 | 147~ | 146d | C!=MAC(ovl-ordinal) C!=EXE C!=HDR |
