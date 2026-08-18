# Task #47 checkpoint — U-Drive-It gauge dials at 1x (class 0xCBCBF1E0)

Working notes, appended as the work proceeds. Binary: `SimCity 4.exe` 1.1.641.0
Steam, ImageBase 0x400000, file offset == VA - 0x400000.

## STEP 1 — OFFLINE MEASUREMENT: DONE (2026-07-29)

### Class 0xCBCBF1E0 identity (all measured, no inference)

| Thing | Value | How measured |
|---|---|---|
| clsid literal xref | **0x004663E0** (only hit in .text) | `exe_scan.py CBCBF1E0` |
| registration site | `push 0x466220; push 0xcbcbf1e0; call 0x90E133` @ 0x004663DA | disasm 0x4662B0 |
| factory | **0x00466220** — `new(0x108)` + ctor, returns **base+4** | disasm |
| ctor | **0x007628E0** | disasm |
| dtor/shutdown helper | 0x007629A0 | disasm |
| MAIN vtable (at base+0) | **0x00AB4900** (18 slots) | ctor writes |
| cIGZWin vtable (at base+4) | **0x00AB46A0** (152 slots; 0xAB4900 begins 0x260 later) | ctor writes |
| custom iid | **0x0BCBF1DF** | QI @ 0x00762490 |
| object size | 0x108 bytes from base | factory `push 0x108` |

Overridden cIGZWin slots (diff of 0xAB46A0 vs the disaster container's
0xAB6AA8): 0, 4, 5, 62, **88**, 121, 134, 136, 138, 142, 148.
**Slot 88 (+0x160) = draw-self = 0x00762830** — the only draw override.

### Field map — offsets relative to the **classBase**

(the window-tree pointer is classBase+4, so a cIGZWin* sees these MINUS 4)

| base off | cIGZWin* off | meaning | evidence |
|---|---|---|---|
| 0xdc | **0xd8** | strip IMAGE (cIGZBuffer) | setter main-vt slot4 0x762680, getter slot5 0x762700, read by draw |
| 0xe0 | 0xdc | resolved STYLE object | Init 0x762570 gets it from style mgr 0x913C72 `vt[0x14]` |
| 0xe4 | 0xe0 | (zeroed, unused in draw) | ctor |
| 0xe8 | 0xe4 | (zeroed, unused in draw) | ctor |
| 0xec | **0xe8** | FRAME COUNT (divisor) | setter main-vt slot6 0x762A20, getter slot7 0x7624D0, draw's `div` |
| 0xf0 | 0xec | float MIN | getter 0x7624E0, used by 0x762770 |
| 0xf4 | 0xf0 | float MAX (ctor = 1.0f) | getter 0x7624F0 |
| 0xf8 | 0xf4 | float VALUE | getter 0x762500 |
| 0xfc | **0xf8** | int FRAME INDEX (computed) | recompute 0x762770 stores it; draw reads it |
| 0x100 | 0xfc | style GUID (ctor = 0x68963C4C) | getter 0x7624C0, setter 0x762710 |
| 0x104 | 0x100 | (zeroed) | ctor |
| — | 0x6c | DRAW CONTEXT (cIGZWin base field) | draw `mov ecx,[esi+0x6c]`; same field cSC4WinRCI uses |

`0x00762770` = value→frame recompute: `frame = (value-min)/(max-min) * count`,
stores classBase+0xfc, then invalidates via cIGZWin vt **index 92 (+0x170)**.

### THE DRAW (0x00762830) — decompiled, 30 instructions

```
img   = [this+0xd8];              if (!img) return true;
count = [this+0xe8];              if (count == 0u) return true;
H     = img->vt[10]();            // cIGZBuffer::Height  (+0x28)
W     = img->vt[9]();             // cIGZBuffer::Width   (+0x24)
cellW = W / count;
frame = this->vt[72]() ? [this+0xf8] : 0;      // vt +0x120 = visibility gate
ctx   = [this+0x6c];
src   = { frame*cellW, 0, frame*cellW + cellW, H };
dst   = { 0, 0, cellW, H };
ctx->vt[38](img, &src, &dst);     // +0x98, __thiscall, callee cleans 12 bytes
return true;
```

### VERDICT — the prescribed force-recreate-buffer lever DOES NOT APPLY

There is **no cached buffer and no cached width** on this class. Nothing like
the minimap's `[this+0xE4]` blitSize / `[this+0xF0]` surface, and nothing like
the disaster container's `[0xdc]` buffer whose `[buf+0x1c]` we corrupt. The
draw blits **straight from the strip image to the draw context every frame**.

The control is **ART-SIZE-DERIVED** — the exact same rule already documented for
`cSC4WinTrendBar` in DYNAMIC-CONTROLS.md. The **destination rect is the ART's
cell size at the window's local origin** and the window rect is never read by
the draw at all. That is a complete explanation of the reported symptom
(1x dial face pinned in the top-left of a correctly-doubled window).

### Emulator proof (new instrument: `tools/flyout-sim/emu_gauge.py`)

Runs the real 0x00762830 under Unicorn with a synthetic object.

```
A) 1x art (928x62, 16 frames), DOUBLED window 116x124, frame 7
   CTX.vt[38]  arg2_rect (406, 0, 464, 62)   <- SOURCE (slides with frame)
               arg3_rect (0, 0, 58, 62)      <- DEST: 1x, top-left  ** BUG **
B) 2x art (1856x124, 16 frames), same window
   CTX.vt[38]  arg2_rect (812, 0, 928, 124)
               arg3_rect (0, 0, 116, 124)    <- fills the doubled window
```
Both runs completed to the sentinel with a 3-arg (12-byte) callee cleanup on
slot 38 — that **confirms the calling convention** as well as the rects.

### Where the gauge ART comes from (why the 2x art pass could never reach it)

The .UI (`I-0bec56c1`, car console) declares the five 0xcbcbf1e0 children with
**NO `image=` attribute at all** — same TGI-less shape as the My Sims portraits.
The dashboard binder at **0x005646AE–0x0056477C** loops the gauges:

```
props = vehicle exemplar (cISCPropertyHolder), GetProperty = vt[0x24]
  0x2BE8E834 -> array of gauge WINDOW IDs
  0x2BE8E6CB -> array of gauge STRIP IMAGE INSTANCES
  0xABE8E6CC -> array of gauge FRAME COUNTS
for each i:
  root->GetChildAsRecursive(winId[i], iid 0x0BCBF1DF, &gauge)
  load image {group 0x46A006B0, instance imgInst[i]} via call 0x00602B70
  gauge->vt[0x10](image)     // main-vt slot 4 = SetImage  0x762680
  gauge->vt[0x18](frames[i]) // main-vt slot 6 = SetFrameCount 0x762A20
```
Dashboard .UI is fetched as id 0x4BCB938A / iid 0x22BA0121 @ 0x00564644.
Per-vehicle gauge setters seen at 0x00566100+ (`0xebcb9403`, `0x2bcb940b`,
`0x2bcbce68`, …) call main-vt slots 8/10/12 = SetMin/SetMax/SetValue.

**So the dial strips are code-bound TGIs {0x856DDBAC, 0x46A006B0, <instance
from vehicle exemplar property 0x2BE8E6CB>}** — invisible to the
reference-driven art build, which is why refmap lists only the .UI-bound
GZWinBMP dial faces/buttons (2BEB4BBB, CBCB9A73/74, 2BEC54A3, 2BEC99B1,
4BE99DC8, CC39214D, AC101989) as 2x. The needle strips were never in the
package. The REGRESSION.md line "the gauge ART is already staged 2x" is
therefore true only of the surrounding art.

### Two justified levers (measured)

1. **DATA (crisper, bigger job):** mine exemplar property 0x2BE8E6CB across the
   43 vehicle exemplars, add those {0x856DDBAC, 0x46A006B0, inst} to
   CODE_BOUND_TGIS in build_selective_safe.py, rebuild dats, bump
   Test-DatIntegrity expectations.
2. **CODE (this pass):** intercept the ONE `ctx->vt[38]` call the draw makes and
   scale the **DEST** rect by the scale factor (never the source — widening the
   source reads past the texture edge = the documented tiling mess). This is the
   mirror image of the already in-game-confirmed `BltThunkCtx` src/dst decouple
   (v2.7.94). Emulator case B is exactly what the scaled dst reproduces.

## STEP 2 — IMPLEMENTATION: DONE

`src/UiSpike.cpp`, new anonymous-namespace block `GAUGE DIALS` immediately
before `UiSpike::ScalePanelsUnder`, plus a hook block after the UDMAP block.

- scoped: `pRoot->GetChildWindowFromIDRecursive(0x4BCB938A)` then a bounded
  recursive walk of THAT subtree only (never global).
- positive class check per window: `*(void**)win == 0x00AB46A0` **and**
  `vt[88] == 0x00762830`. Anything else is skipped untouched.
- per-instance vtable copy (152 slots = the exact class-table length), slot 88
  replaced. The shared class vtable is NEVER written.
- inside the draw thunk the draw context's vtable pointer is swapped to a copy
  with slot 38 replaced, restored immediately after the original draw returns.
- the dst rewrite is self-limiting: multiplier starts at f and is reduced until
  `cell*m` fits the live window, so an unscaled window is left at stock size.
- pointer-latched per instance + reset when the dashboard root pointer changes
  (never writes to a possibly-freed object).
- every raw memory/vtable operation in `__try/__except`.
- log: `GAUGE 2X win %dx%d parent=... id=... — hooking draw slot 88` per
  instance, plus first-12 `GAUGE draw ... cell WxH win WxH -> dst WxH`.

## STEP 3 — portraits + Graphs chart: NOT ATTEMPTED (different mechanism)

Portraits are `GZWinBMP` (`cGZWinBMP`), not 0xCBCBF1E0 — a different class,
different vtable, different fields. Nothing measured here transfers. Documented
in REGRESSION.md; needs its own offline pass on cGZWinBMP's draw + `imagerect`.
Graphs chart class not yet identified.

## STEP 4/5

See REGRESSION.md "ONE BUG CLASS" addendum + DYNAMIC-CONTROLS.md addendum.

## STEP 4 — VERSION / BUILD / DEPLOY / SUITES: DONE

- **Version discrepancy found.** The brief said "currently deployed:
  v2.22.4-flash". Measured reality: `src/SC4UIScaleDllDirector.cpp` was at
  `2.23.1-textsweep` AND both `build/Release/SC4UIScale.dll` and the deployed
  `Documents\SimCity 4\Plugins\SC4UIScale.dll` contained `2.23.1-textsweep`
  (byte-scanned). Setting the requested `2.23.0-gauges` would have moved the
  banner BACKWARDS and made two different builds ambiguous in the log, which is
  the one thing the banner exists to prevent. Bumped FORWARD instead:
  **`2.23.2-gauges`**.
- A parallel session is live in this tree (`_checkpoints/task49-grutzehaus.md`,
  submenus-mod icon work). Only two files were touched here:
  `src/UiSpike.cpp` and `src/SC4UIScaleDllDirector.cpp` (version line only),
  plus new `tools/flyout-sim/emu_gauge.py` and the two research/regression docs.
- Build: MSBuild Release/Win32 — **succeeded, no warnings**.
  `build\Release\SC4UIScale.dll` 296,448 bytes, banner string verified
  `2.23.2-gauges`, 5 `GAUGE` log strings present.
- `SimCity 4.exe` absent from tasklist -> **DEPLOYED** to
  `<HOME>\OneDrive\Documents\SimCity 4\Plugins\SC4UIScale.dll`.
- `_tests\Test-DatIntegrity.ps1`:
  `ALL PASS (11 dats + 3 font sources + 2 DLLs + frozen-bundle hash)`
- `_tests\Test-ScaleTierDecide.ps1`:
  `ALL PASS (14 named cases + 5000x2 random fit sweep)`

## WHAT TO LOOK FOR ON THE NEXT IN-GAME RUN

Drive a car, then the Cigar Boat, with LogLevel=3:
```
UiSpike: GAUGE 2X win 116x124 parent=0x4BCB938A id=0x2BF98D69 - hooking draw slot 88 (dst rect -> x2.00)
UiSpike: GAUGE 5 instance(s) hooked under dashboard root 0x4BCB938A (dash 926x264)
UiSpike: GAUGE draw id=0x2BF98D69 cell 58x62 win 116x124 -> dst 116x124 (x2.00)
```
- 5 hook lines for the car (0x2BF98D69, 0x2BCB940B, 0xEBCB9403, 0xEBF98D37,
  0x2C0C1C8C), 5 for the boat.
- If a `cell` is already the doubled size, that gauge's strip WAS in the art
  package and the multiplier will self-limit to 1.0 (no double-scale).
- If a `win` reads the DESIGN size, the sweep is not doubling that child and the
  multiplier clamps to 1.0 -> stock look preserved, no clipping.
- Zero `GAUGE hook FAULTED` lines expected.

## WHAT REMAINS

- **Portraits (My Sims):** different class (`GZWinBMP`), not touched. Measured
  datum: the staged 2x `.UI` (`stage\T-0x00000000_G-0x08000600_I-0xaa1f1f57.ui`)
  is byte-identical to the extracted 1x for 0x22220000 / 0x22220055 — window
  area (255,57,291,98) and `imagerect=(0,0,36,41)` BOTH left at 1x. The runtime
  face bitmap is 36x41. Needs its own offline pass on cGZWinBMP's draw to learn
  whether its dest comes from `imagerect` or the window rect before any lever is
  chosen. Do NOT assume it is the gauge mechanism — nothing here transfers.
- **Graphs chart:** class not yet identified. Same rule.
- **Optional crisper gauge fix (data):** mine vehicle-exemplar property
  0x2BE8E6CB for the strip instances and add {0x856DDBAC, 0x46A006B0, inst} to
  `CODE_BOUND_TGIS`; the runtime dst rewrite then self-limits to 1.0 on its own,
  so the two fixes cannot fight.

## STEP 5 — DOCS: DONE (post-reconnect verification pass)

After the connection drop the coordinator asked for a resume; verified live
state first instead of redoing: wiring present (UiSpike.cpp line ~3931
HookDashboardGauges after the UDMAP block), version 2.23.2-gauges in source AND
in both the built and deployed DLLs (byte-scanned, 296,448 bytes each), suites
already green. Nothing was re-run or rebuilt.

- DYNAMIC-CONTROLS.md: new addendum "the U-Drive-It GAUGE class 0xCBCBF1E0"
  (identity, fields, draw decomp, binder, fix) — the Step 1 findings now live
  in the canonical research doc, not just this checkpoint.
- _tests\REGRESSION.md "ONE BUG CLASS": new subsection "Gauge dials FIX
  SHIPPED (v2.23.2-gauges) — awaiting eyes-on" with the corrected mechanism
  (ART-sized dest rect, NOT a cached buffer), the shipped lever, four trap
  signatures, and the explicit portraits/chart stop rationale. Inserted before
  the parallel session's "DUPLICATED MENU ICON" section without touching it.

TASK #47 COMPLETE pending in-game eyes-on (expected log lines listed above).
