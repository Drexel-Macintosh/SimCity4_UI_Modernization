# CHECKPOINT — sub-flyout ART vs CODE (2026-07-30)

Full write-up: `tools\uimap\SUBFLYOUT-ART-VERDICT.md`. Offline only; exe never
launched, nothing modified.

## VERDICT

**CODE-DERIVED.** The sub-flyout container's rect is computed entirely from
imm8 constants; the loaded bitmap is never consulted for geometry.

```
W_stock = [+0xf0] - [+0xf8] + [+0xe4] = 80 - 4 + 53 = 129        (constant, always)
H_stock = max(stripH, [+0xf4]=53) + 2*[+0xe8]=50
stripH  = count*(cell 44 + gap 5) - 5 = 49*count - 5,  count clamped [1,8]
```

Live 258x482 = the DLL sweep's 2x of stock **129x241** — a number already
written in `src\UiSpike.cpp:2544` ("129x241 -> 258x482"), which I re-derived
independently from the immediates before reading it.

## Every observed size reproduced (8/8 + 4/4)

| items | stripH | contH | x2 container | matches |
|---|---|---|---|---|
| 1 | 44 → floor **53** | 103 | **258x206** | Freight ✔ |
| 2 | 93 | 143 | 258x286 | ✔ |
| 3 | 142 | 192 | 258x384 | ✔ (strip 284 ✔) |
| 4 | 191 | 241 | 258x482 | ✔ (strip 382 ✔) |
| 5 | 240 | 290 | 258x580 | ✔ |
| 6 | 289 | 339 | 258x678 | strip 578 ✔ |
| 7 | 338 | 388 | 258x776 | ✔ |
| 8 | 387 | 437 | 258x874 | ✔ (strip 774 ✔) |

Freight's 206 is the tell: 1 item gives 44, below the 53 floor, so it clamps —
the only height that breaks every naive arithmetic model, and the formula nails
it exactly.

## Three independent falsifications of ART-DERIVED

1. All **7** builder call sites pass art instances `0x14215ED0/ED0/ED1/ED2/
   ED3/ED4/EDD` — **every one measures 292x53**. Constant art, window height
   varying 103→437. (Refutes `tools\uimap\SUBFLYOUT-CONSTANTS.md` §0's
   "different art instances per menu" — measured false.)
2. No art in the 2,280-image inventory is 44x191, and only 3 have any of the
   heights {103,143,192,241,290,339,388,437} — none of them 129 wide. The 24
   images that ARE 129 wide are all square 129x129, all `.UI`-bound, and none
   appears as an imm32 in the exe (checked, so the collision is recorded).
3. Item icons are **already 2x** (`tools\itemicons\stage`, 320 files at 352x88
   vs stock 176x44) and the cell stayed 44 until `gStripFieldScale=2` — a
   runtime *constant* patch — was added. Same for `ClaimScale=2` (the 53 at
   win+0xe0).

## Corrections to prior notes

* The builder is **`sub_7EAEB0`** (0x007EAEB0–0x007EB2E9), NOT `sub_7EAC70`
  (that function ends `ret` @ 0x007EAEAD). The `124` at 0x007EAD4B belongs to
  the other function and is not in this path.
* The `0x258` at 0x007EAF3D is **600 decimal** (view-height threshold), not the
  container's 258 width. Unrelated numbers.
* `0x8A6E61E0` art is **not** shipped at 2x (absent from `refmap.csv`,
  `package-list.txt`, `stage\`, `CODE_BOUND_TGIS`). It still should be — for
  sprite crispness (bar/ring 1x), not for size.
