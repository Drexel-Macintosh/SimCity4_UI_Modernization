# tools\sdk\ghidra — the Mac debug-symbol type archive

`out\SimCity4.gdt.json` is a JSON export of `SimCity4.gdt` from
[0xC0000054/sc4-ghidra-symbols](https://github.com/0xC0000054/sc4-ghidra-symbols)
(Apache-2.0, Nicholas Hayes; upstream commit `5997577`; licence text in
`out\LICENSE-sc4-ghidra-symbols.txt`).

- The JSON is a straight format conversion, with nothing added or removed.
- Its types come from the 32-bit Mac ports of SimCity 4 Deluxe, which shipped
  **with debug symbols**.
- It holds **no Windows addresses**. It does hold 839 structs (class layouts,
  and vtables with method names in slot order), 212 function signatures and
  40 enums.

`python tools\sdk\lookup.py <ClassOrMethodName>` prints it (section 6).

## The Mac and Windows builds differ — here is exactly how

The two compilers lay out **same-named overloads** differently.

- The Mac compiler keeps declaration order.
- **MSVC pulls every overload of a name up to the first one's slot, in
  reverse declaration order.**

**To predict a Windows vtable, compile the Mac declaration order with MSVC.**
Never read the Mac slot numbers directly where an interface has overloads.
Measured 2026-09-23:

| check | result |
|---|---|
| `cIGZWinFlatRect`, Mac order compiled with MSVC | matches the exe at **all 20 slots**. The Mac slot numbers alone are wrong at 4–14. |
| `cIGZWin` against the exe's own code (base vtable `0x00ADC8D8`, 15 classes) | Mac order exact at every slot decoded **except 103 and 106**. Those are the fill-colour overloads: the exe groups 3 getters then 3 setters, while the Mac interleaves Get/Set. |
| `cIGZWin` 118–147, decoded without the Mac names | all 30 match. The exe's DoMessage jump table `0x99CEF9` routes message types to 129–143. |
| independent positive controls | slot 88 `GZPaint` (our REGRESSION.md finding); 68 `SetFlag` = `0x0099DB6B` (`SetFlagDetour`); 124 `PlotPresent` = `0x0099C498` (`PlotPresentDetour`) |
| interfaces in both this archive and gzcom-dll (`calibrate_slots.py`) | 186; 112 slot-identical; 81% of slots carry the same name. The rest is mostly spelling and overload order. |

Two more cautions:
- **Field offsets.** Windows `cGZWin` is 0xD8 bytes; Mac is 0xE8. For classes
  derived from it, Mac offset = Windows offset + 0x10 (checked on 12
  `cSC4WinCalloutBox` fields). The Mac thunks say `Thn232` (0xE8); the Windows
  ones do `sub ecx,0xD8`.
- **The archive can be incomplete.**
  - `cIGZWinGen` has 32 slots on Windows and 31 on Mac.
  - The Mac `vftable_cIGZGraph` (35 slots) is not the Windows cIGZGraph (55).
  - Bound every Windows vtable by its neighbours; do not trust the Mac count.

## What it found: the SDK header compiles to the wrong slots

The pinned gzcom-dll `cIGZWin.h` (08c529bc, identical to upstream HEAD
`779b669b`) compiles under MSVC to the wrong exe slot for **40 of its 147
declarations**:

| band | what compiles wrong |
|---|---|
| 47–50 | Each `GetArea` / `GetAreaAbsolute` pair is swapped. `GetArea()` reaches the exe's `GetArea(cRZRect&)`, which writes 16 bytes through whatever is on the stack. |
| 53–57 | `GZWinOffset` (57) is missing, and the late `SetSize(cRZPoint)` is pulled up to 53. **`GZWinMoveTo` compiles to the exe's `GZWinOffset`**. That is why every one of our 21 move calls passes a delta, and why the scaling laws say "moves BY, not TO". `SetSize(w,h)` reaches `SetArea(const cRZRect&)`. |
| 102–107 | The `GetFillColor` / `SetFillColor` r,g,b and `cRZColor` overloads are swapped. |
| 118–147 | Every declaration except `CenterWindowInRect(ref)` lands one slot low (`CenterWindowInRect(ptr)` two low): `PlotPresent`, all `GZOn*`, `SendMsg`, `PostMsg`. |

**The 47–50 and 102–107 bands are an upstream regression.**
- Commit `387a9751` ("Fix the ordering of a few overloads in cIGZWin",
  2026-06-27) wrote those groups in the exe's slot order. MSVC reverses
  overload groups, so they now compile backwards.
- Its parent `26fcb160` compiles all eight correctly. MEASURED by compiling
  both versions.

**Right slot, wrong ABI:**
- the exe takes colours **by value** (`SetFillColor(cRZColor)`,
  `SetShadeColor`), where the header passes references;
- `AccelerateKeyboardMsg` pops one argument, and the header passes none;
- `CheckKeyEquivalent` pops two, and the header passes one.

**Gate.** `_tests\Test-GZWinHeaderSlots.py` compiles a probe and scans `src\`.
It fails the build if we call:
- any `cIGZWin` method whose compiled slot is wrong,
- one with a known ABI defect, or
- one no exe-verified row covers.

Today `src\` calls 29 `cIGZWin` methods; all 29 are verified.
`GZWinMoveTo` is the one deliberate exception, used as `GZWinOffset`.

**Upstream status** (read-only search, 2026-09-23):
- nsgomez/gzcom-dll: no issue or PR mentions it, and the file is unchanged at
  HEAD.
- The 11 forks: none has `GZWinOffset`.
- The same author's SimCity 3000 header (`sc3k-gzcom-dll`) does declare
  `GZWinOffset`.
- One downstream project (SC4-ModernCamera) hit the relative-move symptom and
  put it down to the game.
- **Nothing has been posted upstream.** That waits for the user.

## What it found: interfaces the SDK does not declare

The archive holds 87 interfaces gzcom-dll does not declare. Four widget
families are now mapped onto the exe, each verified independently:
FlatRect (IID `0xC2AFA76F`), Grid (`0xDAA6B9BE`), the tooltip
`cSC4WinCalloutBox` (`0xC9B432CF`), and the chart family (`0x?2CF2351`).
Details, levers and corrections: **`tools\research\WIDGET-INTERFACES.md`**.

Still unmapped UI interfaces: `cIGZWinBMP`, `cIGZWinHTML`, `cIGZWinListBox`,
`cIGZWinTextTicker`, `cIGZWinTreeView`, `cIGZWinKnob`, `cIGZFontRenderer`,
`cIGZDrawContext*`, `cISC4WinMiniMap`, `cISC4WinAdviceList`,
`cISC4WinAlertBorder`, `cISC4WinRCI`, `cISC4GlyphTextureManager` and
`cISC4CachedStringTexture`.

## Files

| path | what |
|---|---|
| `ExportGdt.java`, `run-export.cmd` | regenerate `out\SimCity4.gdt.json` (needs Ghidra 12.x at `GHIDRA_HOME`, default `C:\dev\tools\ghidra_12.1.4_PUBLIC`, and a clone at `SC4_SYMBOLS`, default `C:\dev\sc4-ghidra-symbols`) |
| `calibrate_slots.py` | archive vs gzcom-dll slot agreement |
| `probe\` | the header probe the gate compiles |
| `verify\<unit>\` | the 2026-09-23 evidence scripts: `A-full-probe` (all 147 declarations, two compiler readings), `B-second-class-exe-decode` (slots decoded on 15 classes), `W-*` (widgets), and each `*-verify` (the independent skeptic). Only scripts and slot tables are committed. Disassembly dumps and downloaded third-party files regenerate locally and are ignored (`verify\.gitignore`); `THIRD-PARTY-NOTICES.md` §4a limits whole-function listings. |
