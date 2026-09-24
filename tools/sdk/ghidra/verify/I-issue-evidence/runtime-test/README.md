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

## Results (2026-09-23, Steam 1.1.641, region screen)

| run | result | what changed after it |
|---|---|---|
| 1 | 6/6 (app, directors); window tests found no window | the window search walked only 2 levels |
| 2 | 49/49 | window at (0,0) in a parent at (0,0), and colour writes reused the current values: relative-vs-absolute and store-vs-no-op were not told apart. Moves were still told apart, by their put-back steps. |
| 3 | **51/51, 0 failed** (`run3-log.md`) | no plain window on the region screen sits offset in an offset parent, so the geometry window is still (0,0). Colours now write different values and read them back, which is discriminating. |

What the runs do not separate:
- **relative vs absolute (47/48 vs 49/50).** The fix does not change this pairing; the bodies read +0xA8 vs +0x14.
- **the five 12-byte mouse handlers (134-138)**, from each other. They are separated by DoMessage's jump table.
- **the side-effecting cIGZApp methods (4, 6-9, 11-14)**, which were not called. The game's own boot and shutdown call sites pin them.

**Clean-up:** the test DLL and its log were removed from Plugins after run 3.
