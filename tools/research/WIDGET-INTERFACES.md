# Widget interfaces — FlatRect, Grid, ToolTip, Graph

**What this file is.** The Windows-side map of four UI widget families our docs
graded THIN or left unnamed. It is the first use of the Mac debug-symbol
archive (`tools\sdk\ghidra\`) on real widgets. Written 2026-09-23.

**How it was established.**
- Four finder units each decoded one family from `SimCity 4.exe` 1.1.641.0
  (Steam, 7,876,608 bytes), offline, with capstone.
- **Four independent verifiers** then re-derived every load-bearing claim with
  their own scripts, trying to refute it.
- Everything below survived that check, or carries the verifier's correction.
- **All of it is a static reading.** The game was not launched. Under
  `docs\DECOMPILATION-STATUS.md`'s strict bar, these are **PARTIAL**
  (mechanism named, never seen running) until a screen confirms them.
- Evidence scripts: `tools\sdk\ghidra\verify\W-*` (finder) and `W-*-verify`
  (verifier). They regenerate every dump from your own exe; the dumps
  themselves are not committed.

---

## 0. Reading the Mac symbols on Windows — the rule

The Mac and Windows builds differ, and the main cause is that the compilers
lay out **same-named overloads** differently.

- The Mac compiler keeps declaration order.
- **MSVC pulls every overload of a name up to the first one's slot, in
  reverse declaration order.**

**No single rule predicts a Windows vtable; treat both as predictions and
byte-verify.** MEASURED:
- **Compiling the Mac declaration order with MSVC** reproduces all 20 Windows
  slots of cIGZWinFlatRect (`verify\W-FlatRect\msvc_order.cpp`). The same
  grouping explains cIGZWin 102–107 (3 getters, then 3 setters, where the Mac
  interleaves Get/Set), cIGZLineGraph 22/23 and cIGZScatterGraph 15/16, 18/20.
- **The same rule mispredicts cIGZWin 53–118.** The exe keeps `SetSize(w,h)`
  (53) and `SetSize(cRZPoint)` (118) ungrouped. MSVC always groups same-named
  overloads, so the two could not have shared a name in the Windows source,
  and a second kind of Mac/PC difference exists: the sources' names. On
  cIGZWin the raw Mac slot numbers are right everywhere except 103/106.

> ⚠ Same-day correction (2026-09-23). This section first gave "compile the Mac order with MSVC; do not read the Mac slot numbers" as THE rule, with the `SetSize` pair as a footnote. An independent review measured the rule failing across cIGZWin 53–118, so the pair is the counterexample, not an exception to note in passing.

Two more cautions, both MEASURED:
- **Field offsets differ by cGZWin's size.** Windows `cGZWin` is 0xD8 bytes;
  Mac is 0xE8. For a class derived from cGZWin, Mac offset = Windows offset +
  0x10 (checked on 12 cSC4WinCalloutBox fields). Mac adjustor thunks say
  `Thn232` (0xE8); the Windows ones do `sub ecx,0xD8`.
- **The Mac archive can be missing or mislabelled.**
  - cIGZWinGen has 32 slots on Windows and 31 on Mac.
  - The Mac `vftable_cIGZGraph` (35 slots) is **not** the Windows cIGZGraph
    (55 slots).
  - Always bound a Windows vtable by its neighbours (a pure-call table, a
    referenced next table). Do not trust the Mac count.

---

## 1. GZWinFlatRect — a coloured rectangle with optional edges

| | |
|---|---|
| IID / CLSID | **`0xC2AFA76F`** / `0xC2AFA76E` (registry table entry 0 at `0xB16FA8`) |
| class | `cGZWinFlatRect`, 0xF0 bytes. Factory `0x0099899E`, ctor `0x009CD842`. |
| class vtable | `0x00AE20A0` (151 slots). Overrides 0–3, 88 GZPaint `0x009CD1FF`, 103, 104, 106, 107, 130, 131, and 148 dtor `0x009CD6FC`. |
| interface vtable | `0x00AE2050`, exactly 20 slots, at `[this+0xD8]`. Abstract table `0x00AE2300`. |
| this-adjust | +0xD8. QI returns `ecx+0xD8`; AsIGZWin is `lea eax,[ecx-0xD8]`. |

**Windows slot order.** This is the Mac order after MSVC grouping. Slots 0–3
and 15–19 match the Mac; slots 4–14 do not.

| slot | Windows method | slot | Windows method |
|---|---|---|---|
| 4 | `SetFillColor(ulong native)` | 12 | `SetOutlineFlags(long)` → byte `+0xDD` |
| 5 | `SetFillColor(r,g,b)` | 13 | `GetOutlineFlags()` |
| 6 | `GetFillColor()` → native | 14 | `GetOutlineFlag(mask)` |
| 7 | `GetFillColor(r&,g&,b&)` | 15 | `SetOutlineColors(4 × ulong)` |
| 8 | `SetOutlineColor(ulong)` (all edges) | 16 | `GetOutlineColors(4 × ulong&)` |
| 9 | `SetOutlineColor(r,g,b)` (all edges) | 17 | `AutoSize(const cRZRect&)` |
| 10 | `SetOutlineColor(edge, r,g,b)` | 18 | `SetSizeMode(long)` → byte `+0xDC` |
| 11 | `GetOutlineColor(edge, r&,g&,b&)` | 19 | `GetSizeMode()` |

**Fields.**
- `+0xD4` fill colour, packed 0x00RRGGBB. This is cGZWin's field; GZPaint reads
  it through cIGZWin 126.
- `+0xDC` size mode.
- `+0xDD` outline flags:

  | bit | meaning |
  |---|---|
  | 0x01 | left edge |
  | 0x02 | top edge |
  | 0x04 | right edge |
  | 0x08 | bottom edge |
  | 0x10 | raised bevel |
  | 0x20 | sunken bevel |
  | 0x40 | no fill |

- `+0xE0..+0xEC` edge colours, in the order left, top, right, bottom.

**What it means for scaling.**
- **The fill is proportional.** It is a FillRect over the draw rect, so a
  doubled window gets a doubled fill with no hook.
- **Outlines use the draw context's current line thickness, 1.0 by default.**
  GZPaint has no width field of its own. The DC does have a setter:
  `SetLineThickness(float)` at vtable `0xAC16C8` slot 25 (`vt+0x64`), which
  other widgets set and restore around their own lines. A GZPaint wrapper could
  therefore draw 2x borders.
  - ⚠ The finder's "hard 1 px, cannot be thickened" was **refuted** by the
    verifier.
- **Size comes only from `area=`.** The `.UI` applier `0x0094E33B` carries
  colours and flags, no pixels, and no `.UI` keyword sets the size mode.
- **cGZWinGen re-imposes geometry through `AutoSize`.**
  - It calls AutoSize on every FlatRect child, inset by its gutter **bytes**
    `+0x114`/`+0x115`, which are unscaled. This happens only when the owner's
    size changes (fast path `0x99A0E8`).
  - A child with size mode 3, 4 or 5 is re-stretched from the owner. Plain
    `.UI` FlatRects keep mode 0, so AutoSize never moves them.
- **The `0x42B7C351` bar is a FlatRect subclass.** It uses mode 5, and its
  AutoSize override enforces a minimum **height** of max(8, textH+8, btnH+2).
  - The 128 + 2·gutterX minimum **width** belongs to the owning cGZWinGen
    (`gen+0xE8`, enforced by its SetArea override `0x99A0AF`), not to the bar.
  - Our docs call the `0x42B7C35x` family "the generic scrollbar family". The
    decode suggests a caption bar with three buttons. INFERRED; open.
- **Data Views legend swatches** `0x8A909E10+k` are re-seated in code with 1x
  immediates at `0x007A07D9`: x = 0x173, y += 0x3D; labels at x = 0x116.

---

## 2. GZWinGrid — the table control

| | |
|---|---|
| IID / CLSID | **`0xDAA6B9BE`** / `0xDAA6B9BF`. Registry entry 18 `0xB17080`, name `GZWinGrid`; GZCLSIDDefs.h agrees. |
| class | `cGZWinGrid`, 0x2E8 bytes. Factory `0x00998B10`, ctor `0x009ABC95(0x19BFF)` (= `.UI` `fdefault`). |
| layout | cIGZWinGrid at **+0**, the cGZWin sub-object at **+4** (0xD8 bytes), the grid's own fields from +0xDC |
| interface vtable | `0x00ADD578` at +0: 140 interface slots, plus 2 virtuals the class adds (140, 141). Pure table `0x00ADD348` = 140 × `_purecall`. |
| cIGZWin vtable | `0x00ADD7B0` at +4, 151 slots. GZPaint `0x009AF168`, SetArea `0x9A619F`, SetFlag `0x9A6224`. |

- 116 of the 140 slots were verified by behaviour, 25 are consistent by
  argument count, and 2 are unchecked.
- The order of the `GetSelection` pair (41/42) is unresolved: the Mac has no
  signatures for it, and MSVC grouping is active.

**Pixel state** (object-relative):

| field | meaning | ctor | reached by |
|---|---|---|---|
| `+0xF0..+0xFC` | gutters L,T,R,B | 5 | `.UI gutters=`. The loader calls `SetGutters(0,0,0,0)` when the key is absent. |
| `+0x100..+0x10C` | cell gutters (inset every cell window; row auto-height adds T+B) | 1 | no `.UI` key. **Three code callers** (verifier): `0x79C8F2` `(4,4,4,8)` in the Init of vtable `0xAB78A0`, our documented `0xEACA96DD` grid popup (R5); `0x79CD7C` and `0x99572C` pass lineHeight/8. |
| `+0x110` | column-header height | 20 | `colhdrsz`. Absent → `SetHeaderSizes(0,0)`. |
| `+0x114` | row-header width | 80 | `rowhdrsz` |
| `+0x140` | default column width | 100 | `dcolwidth` |
| `+0x144` | default row height | 20 | `drowheight` |
| `+0x154/+0x158` | grid-line width | 1 | no setter and no key |
| format record `+0x24` / `+0x26` | explicit / cached per-column or per-row size (int16) | −1 | `wingridcol` third value, `SetColumnWidth` |

Derived fields (`+0x118..+0x124`, `+0x130/+0x134`) are recomputed from the
window rect. **Never scale them.**

- `tools\dialog-static\build_dialog_static.py` already scales `dcolwidth`,
  `drowheight`, `colhdrsz`, `rowhdrsz`, `gutters` and the third `wingridcol`
  value.
- Rows grow on their own with bigger fonts or art: auto-height is the maximum
  of the default and the content height.
- The `+0x26` cache is cleared by the cell setters, sorts, deletes and
  `ResizeColumnToFitCellWindows`. It is **not** cleared by
  `SetDefault*`/`SetDefaultFont`.

**Code-only pixel state no `.UI` scaler reaches:**
- **Custom Tunes pins column 0 at 255 px.** `SetColumnWidth(0,1,255)` is called
  at `0x004F4B4C` (imm32 at `0x004F4B44`) on grid `0x8A550C56`.
  - Column 0 holds the song titles; column 1, from `wingridcol="1,1,200"`,
    holds the checkboxes.
  - Read statically: titles stay 255 px wide at every scale, and the checkbox
    column starts at an unscaled x = 255.
  - This contradicts the comment in `build_dialog_static.py`
    (grep `200px song-name`). That comment now carries a dated correction.
  - **PATCHED in v4.10.1 (unreleased), at the user's request, without an
    on-screen check.** The user has no custom tunes, so the list is empty.
    - **It is a detour, not a byte patch.** The first version rewrote the
      imm32 to lround(255·f). An independent review found the flaw: that is
      only right while *our* scaled copy of the dialog is loaded. If another
      mod's 1x copy wins (an updated Carbon skin disarming our ZCarbonUI, for
      example), a 510 column in a 289 grid hides every checkbox.
    - `CodePatches::InstallCustomTunesColumnScale` hooks
      `cGZWinGrid::SetColumnWidth` (`0x009AC43B`, grid slot 65).
    - It acts only on the call returning to `0x004F4B52` with the stock
      arguments (0, 1, 255).
    - It sets the width to lround(255 × gridW / 289), where gridW is the
      loaded grid's own `[win+0xB0] − [win+0xA8]`, the formula of the game's
      `GetW`.
    - Results: our copies → 382 / 510 / 765; any 1x copy → 255, exactly stock.
    - Ini key `[UiSpike] CustomTunesColumnPatch` (default 1).
    - `_tests\Test-PatchSiteBytes.py` pins the 15-byte call site and the
      10-byte prologue. The two VAs are classified as control flow in
      `gate_patch_families_combined.py` and `crosscheck.py`.
  - **Still a static reading.** Confirm it once custom tunes exist. Opening
    Audio Options logs the chosen width either way.
- The cheat windows, lot editor, dev property viewers, Lua debugger and
  `GZWinFileBrowser` bake widths and gutters in code. None of them is a
  player dialog.

---

## 3. Tooltips — `cSC4WinCalloutBox`, not the GZ tooltip

There are two tooltip systems in the exe, and **only one runs**.

- **Dormant: GZ `cIGZWinToolTip`.**
  - IID `0x22C010CF`, 6 slots (QI, AddRef, Release, AsIGZWin, SetFont,
    CopyTipInfo). Interface vtable `0x00AE4380`, class vtable `0x00AE4398`,
    ctor `0x9D9C6C`, window id `0x82F0121D`.
  - Its manager is clsid `0x22C010CE` (vtable `0xAE434C`).
  - Its 256×64 buffer, 256 px ellipsis and 2 px gaps change nothing on
    screen.
  - Correction: the gap sites are `0x9DA3FA`/`0x9DA4B1`, not
    `…3F9`/`…4B0`.
  - The GZ tip window also overrides cIGZWin 62, 121 and 122 to return false,
    so it is hit-test transparent.
- **Live: `cSC4WinToolTipMgr` → `cSC4WinCalloutBox`.** This is our "tip layer"
  `0x2AAB8CC1`.

  | | |
  |---|---|
  | IID | **`0xC9B432CF`** (single literal, QI `0x797F50`) |
  | class | `cSC4WinCalloutBox` (Mac name; all 21 slots match), 0x1B4 bytes, ctor `0x799DD0` |
  | vtables | interface `0x00AB69D0` (21 slots) at +0; cGZWin `0x00AB6770` (151 slots) at **+4** |
  | Init / GZPaint | `0x7980D0` (sets id `0x2AAB8CC1` on **every** instance) / **`0x798710`** (slot 88; our docs called it "Plot") |
  | creators | exactly 9: `0x42960A`, `0x437F98`, `0x439128`, `0x43A32D`, `0x4C5876`, `0x7E728C`, `0x7E7D1C` (the tooltip manager), `0x7EAF7F`, `0x7EED54` |

  - The window is **full-screen** and paints the tip into a cached buffer at
    an internal rect. Window-rect scaling therefore cannot reach it; only code
    bytes and art can.

**What already scales.**
- The text: FontStyle `ToolTip 0xA85F1A83` and `ToolTipTitle 0xE9C86C9D`.
- The 250 px wrap, patched by `kTipWrapSites`. The constraint value in GZPaint
  is a **height** budget, (bottom − top) − 2·padX, so padX does not interact
  with the wrap.
- The frame geometry: cell = frame/5, and the tail geometry is multiples of
  the cell.

**What does not scale.** We ship **no 2x frame art**: `0x14416190` 90×90,
`0x14416192` 30×30, query frame `0x14416208`, meter `0x1441621F`. The corners
and tails stay 1x around 2x text.

**The 1x literals.** 60 of the 62 listed sites were re-read at their VAs by the
verifier.

| lever | values and sites |
|---|---|
| pads | expanded (8,8) `0x7EFCCD`/`0x7EFCCB`; simple (5,3) `0x7EFD42`/`0x7EFD40`; defaults 8/3 `0x79834C`/`0x79835F`; query callouts (12,10) at `0x438002`, `0x43A397`, `0x439200` |
| cursor-avoidance rect | expanded ±28 `0x7EFCD6`/`0x7EFCE3`; simple {−4,−4,20,20} `0x7EFD4B`/`0x7EFD58`; ctor ±28 `0x799E94`/`0x799EA5`; traffic-route query ±40 `0x4C58BF`/`0x4C58CC`; query {−w,−1000,w,28} |
| internal gaps | +4 at `0x798781`, `0x79885A`, `0x79890B`, `0x798994`, `0x798CB2`, `0x798CE1`; +3 at `0x79887E`; +2 at `0x798A02` |
| screen inset | 16, at `0x7981EA`..`0x7981F9` |

**Other decoded behaviour.**
- Every tip waits for a 750 ms timer, **except** text containing "ESRB", which
  shows immediately (`0x7EFD7C`).
- The manager's messages go through message-server **slot 5 AddNotification**.
  The finder said slot 4, which the verifier refuted.

---

## 4. The Graphs chart — the `cGZGraph` family

Every chart is a GZ-framework control that derives from a `cGZGraph` base:
ctor `0x9B7526`, main vtable `0xADE188` (178 slots), cIGZGraph vtable `0xADE450`
at +0xD8. The IIDs share one stem, `0x?2CF2351`.

| interface | IID | slots | implemented by | notes |
|---|---|---|---|---|
| cIGZGraph | `0x02CF2351` | 55 | every chart (adjust +0xD8) | slot 12 SetGraphAreaRect `0x9B1F1D` (our EARLYCHART seam); 14 CompleteRedraw `0x9B2431` |
| cIGZLineGraph | `0x12CF2351` | 35 | `cGZLineGraph` (ctor `0x9BA988`) and SC4 `cSC4LineGraph` (ctor `0x76B5F0`) = **type 1**, the Graphs line chart | adjust +0x22C |
| (bar, unnamed) | `0x22CF2351` | 40 | **type 2** (ctor `0x9B9DED`) | not in the Mac archive |
| cIGZScatterGraph | `0x32CF2351` | 33 | `cGZScatterGraph` (ctor `0x9BA033`) | not used by the Graphs panel |
| (pie, unnamed) | `0x42CF2351` | 31 | **type 3** (ctor `0x9BA216`) | not in the Mac archive |

- Type-1 vtables: main `0xAB4D08`, cIGZGraph `0xAB4C28`, line `0xAB4B98`.
- Windows names for cIGZGraph slots beyond the ones above are INFERRED from
  their bodies; the Mac archive has no true cIGZGraph table.

**Chart types in this install** (MEASURED, exemplar property `0xAA4C0D1B`):
- **Type 2 (bar):** Demands `0x0E`, Education Demographic `0x12` and
  Population Demographic `0x13`.
- **Type 1:** every other graph.
- **Type 3:** none. CAM's `CAM_Extended_Graph.dat` keeps the same types.

**Fonts.** The chart **title** uses `Legend 0xE9C86B5F`, so the 0.92 squeeze
does reach it. Axis labels and axis titles use `ChartTickText 0xE9C86B6E`
(pushed at `0x76D658`). Legend rows use `ChartLabel`.

**Levers already in use (EARLYCHART).**
- Plot rect `+0xE0..+0xEC`.
- Title band height `+0x120` (= 32; its automatic rect is `+0x108`).
- Major tick lengths `+0x180/+0x184` (= 4).
- `+0x108` is read by `0x9B5E45`, by the layout driver `0x9B37A4` and by
  `0x9B7B00` (the verifier found this third reader).

**Levers not used yet — only those that actually run:**

| lever | site | note |
|---|---|---|
| series line width 1 | `0x76C3B8` (imm32 `0x76C3BC`) | Widths above 1 go through `cIGZBuffer` vt+0x70, which is **not yet decoded**. |
| plot frame width (push 1) | `0x9B3A58` | This frame is what reads as the axes on screen. |
| tick widths (push 1) | value ticks `0x9B3B65`, `0x9B3BA2`, `0x9B3CB9`, `0x9B3CF7`; category ticks `0x9B473D`, `0x9B4784`, `0x9B4893`, `0x9B48D3` | |
| bar frame (push 1) | `0x9B5581` | |
| legend swatch frame (push 1) | `0x76E250` | |
| 2 px label gaps | `0x9B7FE0`, `0x9B7E4C`, `0x9B7E50`, `0x9B8063` | |
| category-label pads | `0x9B8507`, `0x9B8508`, `0x9B86CF` | |
| title margin 4 | `0x9B3884` | |

**Dead code — do not patch** (verifier, static):
- The axes at `0x9B250B`/`0x9B253A`: DrawAxes is gated on `+0x14C`, which
  only ever holds 0.
- The window border `0x9B396A`: the builder clears it at `0x76D701`.
- The text-item frame `0x9B408E`: the builder clears it at `0x76E314`.

### 4.1 ⚠ POSSIBLE DEFECT IN OUR DLL — bar charts get the line chart's right margin

`InstallChartBornScale` puts `ChartStoreThunk` on the type-2 cIGZGraph vtable
as well as type 1 (`0xADE568+0x30`, grep `type2 iface`). When the legend budget
is armed, the thunk sets `plot.right = winW − GraphLegendPlotRightMargin(f)`
for **every** chart it sees: **244 px at 2x, 181 at 1.5x, and 377 at 3x**
(strip + round(2f)).

The stock bar-chart margin is `W−2` (`0x76D837`), and the type-2 branch
creates **no legend**. The prediction is therefore an empty strip of about
240 px at 2x (about 180 at 1.5x) on the right of Demands, Education
Demographic and Population Demographic.

- The verifier confirmed the code path statically.
- **It is a hypothesis until someone sees it on screen.**
- If confirmed, the cure is to apply `budgetRM` only to the type-1 main vtable
  `0xAB4D08`, leaving type 2 on its proportional margin.

> ✅ **CONFIRMED ON SCREEN, then FIXED (2026-09-23).**
> - The user's 2x screenshot of Graphs → **RCI Demand** shows the bars ending under the line chart's plot edge, with the right quarter of the panel empty and the category labels crowded together. The line chart **Garbage** looked correct: its legend fills that space.
> - The same screenshots show the chart title renders (§6).
> - Fixed in v4.10.1 (unreleased). `ChartStoreThunk` reads the chart's main vtable with `SafeReadPtr` and takes the legend budget only for `0xAB4D08`; bar charts get the proportional margin (about 4 px at 2x).
> - The `EARLYCHART` log line now prints the vtable and `line` or `no-legend`, so the next log shows which path each chart took.
> - Grep `ONLY THE LINE CHART HAS A LEGEND` in `src\UiSpike.cpp`.
> - **Post-fix, confirmed 16:18.**
>   - The user sees the RCI Demand bars running to the edge.
>   - The log shows `vt=00ADE648 no-legend budgetRM=0`, moving the right edge from 974 to 972 in a 976-wide window; the line chart stays at `vt=00AB4D08 line budgetRM=244`.

---

## 5. Corrections this work made to other docs (2026-09-23)

| doc | anchor | correction |
|---|---|---|
| `SDK-GAPS.md` §1 | grep `CORRECTED 2026-09-23` | slot 57 = GZWinOffset; no six-for-five collapse; 139 wheel, 140 capture, 142 exit, 143 command; §1.3 names; §1.4 `ret 0x10` |
| `SC4-UI-ENGINE.md` | grep `the band model above is superseded` | the same slot facts, and the MSVC grouping |
| `SC4-UI-ENGINE.md` | grep `not a grid.` | `vt+0x1AC` at `0x79D91C` is `SetFillColor(25,3,220)` |
| `SC4-UI-ENGINE.md` | grep `is pushed` near `ChartTickText` | push site `0x76D658` |
| `SC4-UI-ENGINE.md` | grep `true of the chart's LEGEND ROWS` | the Legend squeeze reaches the chart title |
| `SC4-UI-ENGINE.md` | grep ``is `GZPaint` (class vtable`` | `0x798710` is GZPaint of cSC4WinCalloutBox |
| `build_dialog_static.py` | grep `CORRECTED 2026-09-23` | in the Audio playlist, `wingridcol` sizes column 1 (the checkboxes); titles are column 0, set in code |

**Flagged, not changed:**
- `src\` comments that call `0x798710` "Plot".
- `kMsgTypeToolTipTick`: the id table at `0xB08040` holds `0x0CA56DD7`, but the
  code posts `0xCA56DD76`. The code value is what behaves.

## 6. Open

- Does `cIGZBuffer` vt+0x70 honour line widths above 1? This must be decoded
  before any width lever is raised.
- ~~The bar-chart gutter (§4.1) and the Custom Tunes column pin (§2): each
  needs one look at 2x.~~
  - The gutter was confirmed on screen and fixed.
  - Custom Tunes is patched, but still needs one look once custom tunes exist.
  - After the v4.10.1 deploy, RCI Demand must show bars running to about 4 px
    from the plot's right edge.
- ~~Is the chart title visible on stock screens?~~ Yes. The 2x screenshots of
  Garbage and Demand both show it (2026-09-23).
- The tooltip frame art: ship 2x frames and scale the literals in §3? Decide
  together, in-game.
- The `0x42B7C35x` family: caption bar or scrollbar? Is `0x0047BAA6` a
  close/minimise action?
- The unidentified IID `0xE98B2F57`: accepted by the base cGZWin QI next to
  cIGZWin's own `0x22BA0121`.
