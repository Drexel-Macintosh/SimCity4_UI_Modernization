# runtime-test: the fixed headers, checked inside the running game

`SC4HeaderTest.dll` is a throwaway plugin built against the fix branch
(`C:\dev\gzcom-dll-fork`, `fix-vtable-order`) with `build.cmd`. Output goes
to `_build\`, which is ignored.

**Install:** copy `_build\SC4HeaderTest.dll` to the Plugins root, with the
game closed. **Run:** start the game, wait about 15 s on the region screen,
quit normally. **Read:** `Plugins\SC4HeaderTest.log`. **Then delete both.**

## What it checks

Every call is checked two ways:
- **the result**, against an independent reading;
- **the stack pointer**, before and after. A method on the wrong slot or
  with the wrong argument list leaves it off.

| target | what it calls |
|---|---|
| app | `cIGZApp::FrameWork` / `ModuleName` / `AsIGZSystemService`, plus the old header's slot-5 "FrameWork" for contrast |
| game director | `GetDirectorID` through `cIGZCOMDirector` on the game's resource-manager director (vtable `0x00AD8BA0`, must return `0xC3CAEC3B`) |
| window | one plain window under the main window: `GetArea` ×2, `GetAreaAbsolute` ×2, `GZWinOffset`, `GZWinMoveTo`, `SetSize` ×2, `SetArea` ×2, `CenterWindowInRect` ×2, `IsPointInWindow…` ×2, `CheckKeyEquivalent`, `AccelerateKeyboardMsg`, all six fill-colour methods, `SetShadeColor`, the four RGB converters, all 15 input handlers (on a window whose handlers are the base class's stubs), and `SendMsg` / `PostMsg` ×2 with message type 0, which does nothing |

Every window change is put back. Every test runs under SEH, so a failure is
logged, not a crash.
