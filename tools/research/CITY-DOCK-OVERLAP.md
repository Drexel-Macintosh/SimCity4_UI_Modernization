# City HUD Bottom-Left "U-Dock" Composition at 2x — Stock Layout, Clamp Diagnosis, Cure

Companion to `..\uiscripts\UISCRIPTS.md` (script format), `DYNAMIC-CONTROLS.md`
(code-drawn controls), `..\selective-safe\SELECTIVE-SAFE.md` (art package).

Evidence base:
- Runtime truth: a full pre-scale tree dump of the city HUD at 2400x1600 (840 windows,
  positions/sizes/visibility), followed by `ScaleAll x2.00 (view 2400x1600)` and the
  incremental passes.
- Design truth: `..\uiscripts\extracted\T-00000000_G-96a006b0_I-c973b411.ui` (view cluster +
  mode overlay) and `...I-2bc90671.ui` (the live composite HUD; `I-898897de` is the stale
  development copy). `area=` is corner-format `(x1,y1,x2,y2)`, absolute for roots,
  parent-relative for children.
- Scaler code: `..\..\src\UiSpike.cpp` — `ScalePanelRoot()` anchor math and the on-screen
  clamp.
- Art: `..\dbpf\extracted\SimCity_1\` — dock sheet `13d14ca0` (235x222), composite sheet
  `4bbe9c7d` (878x182), Mayor Mode button strip `14015555` (4 cells of 60x46, a mayor bust
  on an oval button — this is "the Mayor symbol").

Summary: the reported dock breakage at 2x is **one bug**. The stock design overlaps the
dock and the composite panel on purpose (the arts interlock), and the dock's bottom 11 px
hang off-screen on purpose. At 2x the scaler's anchor math reproduces both facts perfectly
— and an unconditional on-screen clamp then overrides the answer for the one panel that
legitimately overhangs, lifting the dock 22 px relative to everything else. Making the
clamp per-edge conditional on the design gap snaps the whole dock area back to design
proportions. No .UI edits, no art changes, no per-child tweaks.

---

## 1. Stock 1x composition of the dock area

### 1.1 The players

Three sibling top-level windows under the city view `0x9A47B417` (cSC4View3DWin) make up
the bottom-left composition, plus the ticker family to the right:

| Window | Script | Stock rect at 2400x1600 (runtime) | Notes |
|---|---|---|---|
| `0xE9889775` composite status panel | `I-2bc90671` root 1 | (139,1413) 880x180 → (139,1413)-(1019,1593) | bottom gap 7 px |
| `0x0987B48F` minimap cluster ("U-dock") | `I-c973b411` root 1 | (5,1388) 235x223 → (5,1388)-(240,1611) | **bottom 11 px off-screen by design** |
| `0xEA8CAD14` mode-transition overlay | `I-c973b411` root 2 | (0,-16) 225x139 | **top 16 px off-screen by design**; 4 hidden 66x43 cross-fade BMPs (`0xEA8CAD15..18`, art 14416102-05) |
| `0xCA2AEDC0` news ticker strip | `I-2a2aed99` | (232,1552) 757x43 | rides in the composite's bottom band |
| `0x6A64E3C0` opinion polls panel | `I-4bc906b5` | (501,1412) 538x135 | rides on the composite |

The .UI roots carry 1024x768-era coordinates (cluster `(30,-5,265,218)`, composite
`(140,613,1020,793)`); at 2400x1600 the game's HUD code re-anchors them to the values
above. The 11 px bottom overhang is resolution-independent stock behavior (y = 1600 - 212;
the .UI top overhang -5 becomes a bottom overhang once the code bottom-docks the cluster).

### 1.2 Z-order

The runtime tree dump enumerates children in exact reverse of .UI sibling order (verified:
the composite's 14 children appear in the dump precisely backwards from `I-2bc90671`,
background last). .UI order = add order = paint order, first child painted first (behind) —
the cluster's full-size background BMP is its first .UI child and its buttons paint over
it, which is only possible with first-behind. Applying the same reading to the top-level
dump order (top-first) gives the add order, bottom to top:

```
... < 0xE9889775 (composite)  <  0x0987B48F (dock)  <  0xEA8CAD14 (mode overlay) < ...
```

So the **dock paints on top of the composite** — the composite's left end tucks UNDER the
dock. The two background sheets are shaped for it: `4bbe9c7d` (composite) has a diagonal
notch cut into its top-left; `13d14ca0` (dock) has the curved right hump that fills it.

### 1.3 The designed interlock — proven by the alignment ghost

`I-2bc90671` contains an invisible child, literally labeled with the dock's Mayor button id:

```
<LEGACY clsid=GZWinCustom id=0x0000aaaa area=(-37,12,23,56) caption="0xc988bc79" winflag_visible=no ...>
```

Composite origin (139,1413) + (-37,12) = **(102,1425)** — exactly where the dock places
the Mayor Mode button: cluster (5,1388) + child (97,37) = **(102,1425)**. The designers
encoded the intended relative placement of the two panels as a ghost rect: the composite
must sit at **cluster origin + (134,25)**, so the mayor bust nests into the composite's
notch. The 800x600 variant `G-08000600\I-2bc90671` carries the same ghost at (-37,47) —
per-resolution anchoring, same mechanism. A second ghost `0xAA6767AA` "<alignment target>"
at (413,140) marks the ticker slot.

### 1.4 Dock (0x0987B48F) subtree — design rects

Parent-relative corners from `I-c973b411`; absolute = +(5,1388). The runtime dump agrees on
every size and position. Paint order = table order (first = bottom).

| # | Window | Role | rel rect | abs at 1x |
|---|---|---|---|---|
| 1 | (anon BMP) | dock sheet 13d14ca0, imagerect (0,0,235,222) | (0,1)-(235,223) | (5,1389)-(240,1611) — bottom 11 px art rows clipped by the screen, by design |
| 1a | (anon BMP)+text `0x00000002` | city-name plate | (42,182)-(189,204) | (47,1571)-(194,1593) |
| 2 | (anon BMP)+text `0x00000001` | date strip | (98,140)-(170,155) | (103,1528)-(175,1543) |
| 3 | `0x00000044` | Hide Toolbars | (10,179)-(34,201) | (15,1567)-(39,1589) |
| 4 | `0xE9920494` | Zoom Out | (41,169)-(62,181) | (46,1557)-(67,1569) |
| 5 | `0x4992046A` | Zoom In | (41,145)-(63,166) | (46,1533)-(68,1554) |
| 6 | `0x99887766` | Query (?-button) | (95,85)-(131,106) | (100,1473)-(136,1494) |
| 7 | `0x8B96B73E` | Route Query (?-button) | (95,106)-(131,127) | (100,1494)-(136,1515) |
| 8 | `0x2A4FBB08` | Rotate CW | (21,153)-(40,174) | (26,1541)-(45,1562) |
| 9 | `0x8A4FBAEA` | Rotate CCW | (64,153)-(83,174) | (69,1541)-(88,1562) |
| 10 | `0x8998BBDF` | Cheetah speed | (159,163)-(188,179) | (164,1551)-(193,1567) |
| 11 | `0x4A4FBB60` | Rhino speed | (134,163)-(158,179) | (139,1551)-(163,1567) |
| 12 | `0x6A4FBB31` | Turtle speed | (114,163)-(133,179) | (119,1551)-(138,1567) |
| 13 | `0xC998BB81` | Pause | (95,163)-(113,179) | (100,1551)-(118,1567) |
| 14 | `0x2988BC85` | God Mode button (art 14415860) | (26,-6)-(90,44) | (31,1382)-(95,1432) — hangs 6 px above the dock root |
| 15 | `0xC988BC79` | **Mayor Mode button** (bust art 14015555) | (97,37)-(157,83) | (102,1425)-(162,1471) |
| 16 | `0x4988BC6A` | My Sim Mode button (art 13f15230) | (138,93)-(192,135) | (143,1481)-(197,1523) |
| 17 | `0x8988BC94` | Options button (art 13e14fb3) | (195,174)-(229,200) | (200,1562)-(234,1588) |
| 18 | `0x0BC3B559` | minimap (cSC4WinMiniMap, clsid 0xca318388) | (18,72)-(82,136) | (23,1460)-(87,1524) |
| 19 | `0xAA75CA06` | 67x16 click target over the date area (art {1abe787d,14416242}) | (98,138)-(165,154) | (103,1526)-(170,1542) |
| 20 | `0xAA771FD7` | time-of-day rollover BMP + "10:00" text (vis=0) | (92,119)-(140,140) | hidden |

### 1.5 Composite (0xE9889775, live I-2bc90671) subtree — design rects

Absolute = +(139,1413); background children are relative to the bg BMP at (141,1413).

| Window | Role | rel rect | abs at 1x |
|---|---|---|---|
| (anon BMP) | sheet 4bbe9c7d 878x182 | (2,0)-(880,182) | (141,1413)-(1019,1595) (bg child extends 2 px past the 180-tall root; clipped) |
| (anon)+`0x0A51201D` | Mayor Rating label plate | bg (84,28)-(249,52) | (225,1441)-(390,1465) |
| (anon)+(anon) | RCI label plate | bg (255,28)-(295,52) | (396,1441)-(436,1465) |
| `0x8A517556` | rating groove (art 14015549) | bg (120,57)-(222,68) | (261,1470)-(363,1481) |
| `0x00008A50` | rating groove alt (vis=0) | bg (122,56)-(227,69) | hidden |
| `0xCA5A415E` / `0x6A5A4156` | rating change arrows | bg (98,58)-(119,67) / (225,58)-(246,67) | (239,1471)-(260,1480) / (366,1471)-(387,1480) |
| (anon)+`0x09E418FE` | funds plate | bg (100,85)-(242,104) | (241,1498)-(383,1517) |
| (anon)+`0xC9E41918` | population plate | bg (110,112)-(238,130) | (251,1525)-(379,1543) |
| `0xAA9211B3` | RCI demand meter button | (256,16)-(298,134) | (395,1429)-(437,1547) |
| `0x09D27EB0`/`0x29D27EC0`/`0x49D27ED0` | RCI columns 8x71 | (263/273/283,56) | x 402..430, y 1469-1540 |
| `0x2BC8B116` | tab-stack backdrop BMP (art 0bc6638a 55x117) | (301,18)-(356,135) | (440,1431)-(495,1548) |
| `0xABC54125` `0x49EDF9B7` `0x00000041` | tab column 1 (RH tab / Advisors / Budget), 34x35 | (299,27/62/97) | (438,1440..1545) |
| `0x99887755` `0x15200002` `0x15200003` | tab column 2 (Data Views / Graphs / Opinion Polls) | (326,27/62/97) | (465,1440..1545) |
| `0x0000AAAA` | **alignment ghost = Mayor button footprint** (vis=0) | (-37,12)-(23,56) | (102,1425)-(162,1469) |
| `0xAA6767AA` | "<alignment target>" ghost (vis=0) | (413,140)-(445,170) | (552,1553)-(584,1583) |

### 1.6 Who overlaps whom at 1x (designed)

Panel roots overlap in x 139..240 (101 px), y 1413..1593 (the full composite height).
Within that region, painted top-to-bottom:

- **Dock over composite (by design):** Mayor button (102,1425)-(162,1471) — its right
  21 px sit on the composite; exactly the ghost footprint. My Sim button (143,1481)-(197,1523)
  fully over the composite bg notch. Rhino+Cheetah (139..193,1551-1567), Options
  (200,1562)-(234,1588), city-name plate right half, date/people-strip right edges — all
  over the composite bg's left slope, which is opaque dock-sheet territory there.
- **Composite content tucked under the dock's right hump (by design):** the rating label
  plate's left ~15 px (x 225..240) and the left arrow's first pixel (x 239) start under
  the dock silhouette; the plate has lead-in padding and the text is center-aligned, so
  nothing readable is hidden.
- Nothing else from the composite lives at x < 240; the interlock is pure art shaping plus
  those two tucked-lead-in edges.

---

## 2. Why an unconditional on-screen clamp breaks the composition at 2x

### 2.1 Measured facts

```
UiSpike: ScaleAll x2.00 (view 2400x1600)
UiSpike: panel 0xEA8CAD14 (0,-16 225x139)   -> (0,0 450x278)       [city pass]
UiSpike: panel 0x0987B48F (5,1388 235x223)  -> (10,1154 470x446)   [city pass]
UiSpike: panel 0xE9889775 (139,1413 880x180) -> (278,1226 1760x360) [incremental]
UiSpike: panel 0xCA2AEDC0 (232,1552 757x43) -> (464,1504 1514x86)  [incremental]
UiSpike: panel 0x6A64E3C0 (501,1412 538x135) -> (1002,1224 1076x270)
UiSpike: panel 0x69E40A1F (4,982 157x488)   -> (8,364 314x976)
```

Every bottom-family panel obeys the scaler's bottom-anchored rule
`y' = 1600 - 2*(1600 - y)` exactly: composite 1226, ticker 1504, polls 1224, tool column
364. Cross-check of mutual consistency: the ticker relative to the composite is (93,139) at
1x and (186,278) at 2x — perfect doubling. **The whole composite family is
design-proportional at 2x.** The misfit is the dock: the same rule yields
`1600 - 2*(1600-1388) = 1176` (bottom overhang 22 = 2 x 11), while an unconditional clamp
produces **1154 = 1600 - 446**, i.e. fully on-screen. The mode overlay is the same story on
the top edge: the rule gives (0,-32), the clamp gives (0,0).

### 2.2 Root cause — one clamp line

`src\UiSpike.cpp`, `ScalePanelRoot()`. The scaled-gap anchor math computes
`gapB = frameH - (t+h) = -11`, takes the bottom-anchor branch, and produces
`newY = 1600 - ScaleRound(-11, 2.0) - 446 = 1176` — the design answer. An unconditional
clamp then discards it:

```cpp
// On-screen clamp: whatever the anchor math says, a panel that fits
// the frame must end up inside it (fail toward visible).
if (newY + newH > frameH) newY = frameH - newH;   // 1176 -> 1154   <-- wrong for designed overhang
if (newY < 0) newY = 0;                            // -32  -> 0     <-- same, 0xEA8CAD14
```

An unconditional clamp cannot distinguish "anchor math overflowed" from "the design itself
overhangs". For the dock it discards a correct answer and lifts the panel **22 px**
relative to the composite family; for the mode overlay it pushes the panel **32 px** down.

### 2.3 The 22 px shift, quantified

Clamped 2x dock children = 2 x rel + (10,1154). Design-intent = 2 x rel + (10,1176)
(everything 22 px lower). Composite children are correct either way: see section 3.2.

Alignment-ghost check at 2x: ghost target = composite (278,1226) + 2 x (-37,12) =
**(204,1250)**. Clamped Mayor button = (10,1154) + 2 x (97,37) = **(204,1228)**. X exact,
**y off by exactly 22** — the entire dock-vs-composite composition error in one number.

Collisions and exposures that do not exist at 1x (all derived from that one delta;
silhouette-dependent extents marked ~):

1. **Mayor symbol overlap** — Mayor button clamped (204,1228)-(324,1320) vs designed
   (204,1250)-(324,1342). The composite's top edge band (bg art rows 0..~12, screen
   y 1226..~1250) is the panel's rounded top-left frame line; designed, the bust sits
   fully below it, nested in the notch. Shifted, the bust's upper half paints across the
   frame line (overlap x 282..324, y 1228..~1250) and the notch pixels meant to be hidden
   under the bust show as a ~22 px crescent beneath it. The God button (62,1142 vs design
   1164) and My Sim button (286,1340 vs 1362) ride equally high over the composite art —
   the whole interlock seam (x 282..480) is discontinuous by 22 px.
2. **Elements that read as missing** — two mechanisms, both real:
   - The dock paints on top and its opaque body is 22 px high: along x 440..480 the dock's
     right hump covers the composite's top-left frame line and the upper-left corner
     of the Mayor Rating label plate (450,1282)-(780,1330) ~22 px beyond design (~y 1282..1304
     of the plate's left ~30 px). The composite's frame vanishes under the dock body
     for that stretch.
   - The composite's notch region that should be covered is exposed lower down: raw
     sheet-edge pixels of 4bbe9c7d appear below the dock silhouette — reads as broken or
     missing art at the seam.
3. **Extra art, mirror of the overhang:** the dock sheet's bottom 22 px (2 x art rows
   201..222 — the rounded bottom-corner band that stock always clips off-screen) become
   fully visible at y 1556..1600, doubling the dock's apparent bottom margin and shifting
   every dock control (city name, Hide Toolbars, speed row) visibly up from the screen
   edge compared to stock proportions.
4. **Mode overlay 0xEA8CAD14** at (0,0) instead of (0,-32): its cross-fade child BMPs
   (2x: (34,76)-(166,162)) draw 32 px lower than stock proportion during mode transitions.
   Minor, but the identical bug.
5. **No new child-vs-child control collisions.** Exhaustive rect sweep: no dock button
   lands on any composite interactive child even shifted (Options ends x 468 vs funds
   plate starting x 482; speed row ends x 386 vs rating groove starting x 522; the arrow
   at x 474..516 is already tucked at 1x). The damage is composition- and art-level plus
   the label-corner coverage, not dead buttons.

---

## 3. The cure

### 3.1 Per-edge clamp, conditional on the design gap

The clamp is per-edge conditional: it clamps toward an edge only when the panel's DESIGN
rect did not already overhang that edge. When the design gap is negative the anchor math
has already produced exactly the scaled overhang, and it stands:

```cpp
// On-screen clamp, PER-EDGE conditional on the DESIGN gap: a negative
// design gap is an INTENTIONAL overhang (the dock hangs 11 px off the
// bottom, the mode overlay starts at y=-16) and the anchor math already
// scaled it correctly; clamping it shifts the panel off its design
// alignment. Only a non-negative gap can mean genuine overflow.
if (gapR >= 0 && newX + newW > frameW) newX = frameW - newW;
if (gapL >= 0 && newX < 0)             newX = 0;
if (gapB >= 0 && newY + newH > frameH) newY = frameH - newH;
if (gapT >= 0 && newY < 0)             newY = 0;
```

Why this is safe and sufficient:
- A negative gap can only reach the clamp via the matching edge-anchor branch (the
  center branch requires both gaps > frame/4, i.e. positive), so "gap < 0" is precisely
  "the anchor result carries scaled design overhang" — the guard never weakens the clamp
  for genuine overflow (mid-screen or oversized panels still clamp).
- It is a general rule, not a window-id special case: it covers 0x0987B48F and 0xEA8CAD14
  and any other overhanging stock panel for free, at every scale factor and resolution.
- Zero data-side changes: no .UI edits, no art, no SCALED_WINDOW_IDS churn, no re-pack of
  `z_SC4UIScale_SelectiveArt.dat`.
- No interactive dock child ever enters the clipped band. The lowest control is the
  city-name plate, whose bottom sits at `frameH + R(11,f) - R(223,f) + R(204,f)`, i.e.
  `8*f` px above the frame bottom at every factor (11 - 223 + 204 = -8) — 16 px of margin
  at 2x, more above it. Only the non-interactive rounded-corner art rows go off-screen —
  exactly the stock proportion.

Alternatives that do not work:
- **Anchoring dock + composite as a unit:** it produces the identical rects for this pair
  (unit-anchoring about the composite's bottom rule also yields dock y 1176) but requires
  a pairing registry, does nothing for 0xEA8CAD14, and couples panels that the game
  positions independently per resolution (the 800x600 ghost offset differs).
- **Per-child adjustments:** the dock's internal layout is already perfect (all 20
  children move as one with the root), and no child edit can rejoin the one-bitmap art
  seam. There is nothing to adjust per-child.

### 3.2 Resulting rects at 2400x1600

Dock `0x0987B48F`: **(10,1176) 470x446 → (10,1176)-(480,1622)**, bottom 22 px off-screen
(= stock 11 px x 2). Composite family unchanged. Log line:
`panel 0x0987B48F (5,1388 235x223) -> (10,1176 470x446)`.

| Element | 2x rect |
|---|---|
| dock sheet BMP | (10,1178)-(480,1622) (rows past 1600 clipped, as stock) |
| God Mode | (62,1164)-(190,1264) |
| **Mayor Mode** | **(204,1250)-(324,1342)** — top-left equals the ghost target (204,1250); nests in the notch |
| My Sim | (286,1362)-(394,1446) |
| minimap | (46,1320)-(174,1448) |
| Query / Route Query | (200,1346)-(272,1388) / (200,1388)-(272,1430) |
| Zoom In / Zoom Out | (92,1466)-(136,1508) / (92,1514)-(134,1538) |
| Rotate CW / CCW | (52,1482)-(90,1524) / (138,1482)-(176,1524) |
| Pause / Turtle / Rhino / Cheetah | y 1502..1534; x 200-236 / 238-276 / 278-326 / 328-386 |
| date strip / people strip | (206,1456)-(350,1486) / (206,1452)-(340,1484) |
| Hide Toolbars | (30,1534)-(78,1578) |
| city-name plate | (94,1540)-(388,1584) |
| Options | (400,1524)-(468,1576) |
| Mode overlay `0xEA8CAD14` | (0,-32) 450x278; cross-fade BMPs (34,44)-(166,130) |
| Composite root | (278,1226)-(2038,1586); bg (282,1226)-(2038,1590) |
| rating label / groove / arrows | (450,1282)-(780,1330) / (522,1340)-(726,1362) / (474,1342)-(516,1360) + (728,1342)-(770,1360) |
| funds / population plates | (482,1396)-(766,1434) / (502,1450)-(758,1486) |
| RCI meter + columns | (790,1258)-(874,1494); columns x 804/824/844, y 1338-1480 |
| tab stack + 6 tabs | (880,1262)-(990,1496); tabs 68x70 at x 876/930, y 1280/1350/1420 |
| ticker | (464,1504)-(1978,1590) |

Every interactive dock child stays fully on-screen (max bottom 1584 < 1600), and the
dock-vs-composite offset is 2 x (134,25) = (268,50), so the interlock seam, the bust
nesting, the label tuck-under, and the stock bottom margin are all design-proportional.

### 3.3 Verification

1. The log shows `-> (10,1176 470x446)` for 0x0987B48F and `-> (0,-32 450x278)` for
   0xEA8CAD14; no other panel's placement line changes.
2. Ghost identity: composite pos + 2 x (-37,12) == Mayor button screen pos in the tree dump.
3. On screen: the mayor bust sits below the composite's top frame line; no raw sheet-edge
   crescent under the mode buttons; the "Mayor Rating" plate corner is uncovered; the dock
   bottom corner band is off-screen.
4. Panels that clamp legitimately (oversized or mid-screen cases) still clamp — the guard
   relaxes only edges with negative design gaps.
