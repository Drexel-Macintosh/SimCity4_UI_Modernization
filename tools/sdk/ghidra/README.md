# tools\sdk\ghidra — the Mac debug-symbol type archive

`out\SimCity4.gdt.json` is a JSON export of `SimCity4.gdt` from
[0xC0000054/sc4-ghidra-symbols](https://github.com/0xC0000054/sc4-ghidra-symbols)
(Apache-2.0, Nicholas Hayes; upstream commit `5997577`; licence text in
`out\LICENSE-sc4-ghidra-symbols.txt`). The JSON is a straight format
conversion, with nothing added or removed. Its types were extracted from the 32-bit Mac
ports of SimCity 4 Deluxe, which shipped **with debug symbols**. It holds
**no Windows addresses**. What it does hold: 839 structs (class layouts and
vtables with method names in slot order), 212 function signatures and 40 enums.

`python tools\sdk\lookup.py <ClassOrMethodName>` prints it (section 6).

## How far to trust it on Windows — measured 2026-09-23

| Check | Result |
|---|---|
| Interfaces in both this archive and gzcom-dll (`calibrate_slots.py`) | 186; 112 slot-for-slot identical; 81% of all slots carry the same name. Most of the rest are spelling (`Conection`/`Connection`) or Ghidra's overload suffixes, not order. A few real order disagreements exist (e.g. `cISC4NetworkTool` 16/17, `cIGZWinGen` from 16), and we don't yet know which side is right |
| `cIGZWin` against the exe's own code (cSC4WinAlertBorder vtable `0x00AB5B48`) | **Mac order is exact** at every slot decoded: 35, 36, 41, 42, 48, 51–58, 63–70, 86–88, 118–121, 124 |
| Independent positive controls | slot 88 = `GZPaint` is our REGRESSION.md finding ("SLOT 87 IS NOT GZPaint"); slot 124 = `PlotPresent` = `0x0099C498`, our `PlotPresentDetour` VA; slot 68 = `SetFlag` = `0x0099DB6B`, our `SetFlagDetour` VA |
| `cIGZWinFlatRect` | IID = **`0xC2AFA76F`** (exe `0x47B993`, `0x4861D7`: `GetChildAs(id, 0xC2AFA76F, &p)`), then slot 3 `AsIGZWin` and slot 2 `Release`, as the archive orders them |

**Field offsets and this-adjusts are Mac layout.** The thunks say `Thn232`
(0xE8). Windows adjustors differ (cGZWin's are `0xD8`). Byte-verify any
offset before using it.

## What it found that we did not have

**The gzcom-dll `cIGZWin.h` compiles to the wrong slot in two bands:** 4
methods in slots 53–57, and all 28 declarations that compile to slot 118 or
later except `CenterWindowInRect(ref)`. Four of those 28 were measured by the
probe; the rest follow from the one-slot shift.
Gated by `_tests\Test-GZWinHeaderSlots.py`. The header omits `GZWinOffset`
(slot 57) and declares `SetSize(cRZPoint)` late. MSVC pulls overloads up to
the first same-named slot, so compiling the header gives:

- `GZWinMoveTo` → slot 57 = the exe's **`GZWinOffset`**. That is why every
  one of our 21 calls passes a delta, and why the scaling laws say
  "GZWinMoveTo moves BY, not TO".
- `SetSize(w,h)` → slot 54 = exe `SetArea(const cRZRect&)`: calling it
  would dereference `w` as a pointer.
- `SetArea(rect)` → slot 56 = exe `GZWinMoveTo`.
- From slot 118 on, calls land one slot low: `PlotPresent`, the `GZOn*`
  handlers, `SendMsg`, `PostMsg`, `CenterWindowInRect(ptr)`.
  `SetSize(cRZPoint)` → slot 53 = exe `SetSize(w,h)`.

Our source calls none of the broken names (the gate proves this every run).

**87 interfaces gzcom-dll does not declare.** The UI-relevant ones:
`cIGZWinFlatRect`, `cIGZWinGrid`, `cIGZWinBMP`, `cIGZWinToolTip`,
`cIGZWinHTML`, `cIGZWinListBox`, `cIGZWinTextTicker`, `cIGZWinTreeView`,
`cIGZWinKnob`, `cIGZFontRenderer`, `cIGZDrawContext*`, `cIGZGraph`,
`cIGZLineGraph`, `cIGZScatterGraph`, `cISC4WinMiniMap`,
`cISC4WinAdviceList`, `cISC4WinAlertBorder`, `cISC4WinRCI`,
`cISC4GlyphTextureManager`, `cISC4CachedStringTexture`. There are also
class layouts for `cSC4BudgetUIWinProc`, `cSC4SubBudgetWindow`,
`cSC4GraphsViewWinProc`, `cSC4WinMapView`, `cSC4View3DWin`,
`cSC4PanelUIWinProc` and 170+ more.

## Regenerate

```
tools\sdk\ghidra\run-export.cmd
```

This needs Ghidra 12.x (`GHIDRA_HOME`, default `C:\dev\tools\ghidra_12.1.4_PUBLIC`)
and a clone of the symbols repo (`SC4_SYMBOLS`, default `C:\dev\sc4-ghidra-symbols`).
The script is `ExportGdt.java`.
