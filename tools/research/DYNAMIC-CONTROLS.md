# SC4 Dynamic (Code-Drawn) UI Controls — Class Map, Geometry Sources, 2x Recommendations

Research date: 2026-07-21. Binary: `SimCity 4.exe` 1.1.641.0 Steam (x86, 4GB-patched),
ImageBase 0x400000, `.text` raw==RVA 0x7000..0x680000, `.rdata` 0x680000, `.data` 0x707000.
All analysis offline (capstone 5.x via Python 3.12); game files untouched.
Addresses below are VAs (file offset = VA − 0x400000 for all sections referenced).

## Headline findings

1. **The exe contains a full `{clsid → class-name}` registry** in `.data` at VA 0xB08F78+
   (648 entries, pairs of `[clsid][ptr to name string]`). This named every custom clsid in
   the .UI scripts.
2. **The RCI graph draws from its WINDOW rect** (fully proportional) — it will follow our
   doubling automatically.
3. **TrendBar (poll bars / opinion bars) draws at its ART's pixel size**, centered in its
   window — content scale is controlled by the bitmap, and its two bitmaps are **code-bound
   TGIs missing from our 2x override package**.
4. **The ticker (AdviceList) lays out its children from its own window size and the
   AdvisorHeadline font style** — dou­ble the container + 2x FontStyle and its per-frame
   "geometry reset" produces *correct 2x geometry by itself*. The tombstone can likely be
   replaced by "scale container only, never its children".
5. **The Mayor Rating change-arrows are the only true hardcoded-constant drawer**:
   `SetW(delta * 7)` px per rating point, 3 patchable `imul ..., 7` sites.

---

## Q1 — Class map (city HUD scripts I-2bc90671 composite, I-4bc906b5 / I-0a5fa5d6 polls, I-2a2aed99 ticker)

| Control (visual) | .UI clsid | Engine class (from registry) | Window id(s) in .UI | Key code (VA) |
|---|---|---|---|---|
| RCI demand graph (3 columns, 8x71 each) | `0xc7a0e17e` | **cSC4WinRCI** | 0x09d27eb0 / 0x29d27ec0 / 0x49d27ed0 | factory 0x466170, ctor 0x7A9770, **Draw 0x7A9500** |
| Opinion-poll bars (6 per polls panel) | `0xaa5c2f86` | **cSC4WinTrendBar** | 0x6a5e6edc..0x6a5e6ee1 | factory 0x4661A0, ctor 0x7BF5E0, **Draw 0x7BF0A0** |
| News ticker marquee + News window list | `0xca1492ac` | **cSC4WinAdviceList** | marquee 0xaa12f33c, list 0x6a231531 | QI 0x793080, Init 0x793190, item-create 0x7931F1, Draw = no-op (0x949ade `mov al,1`) |
| Ticker roll text item (created at runtime by AdviceList) | `0xaa12e5f5` (also appears in 5 dialog scripts) | unnamed in registry; instantiated via CreateInstance(clsid 0xaa12e5f5, iid 0x4a11fd4a) | n/a (code-created) | creation sites 0x443fc9, 0x76a182, 0x78ce11, 0x7931F0, GetClassID 0x8fa317 |
| Funds / population / date / rating texts | `GZWinText` (standard) | cGZWinText | funds 0x09e418fe, pop 0xc9e41918, rating label 0x0a51201d | HUD binds cIGZWinText (iid 0x212cdc1f) at 0x7EE64D/0x7EE668 — caption updates only |
| Mayor Rating bar + change arrows | `GZWinBMP` × 4 (standard) driven by controller code | cGZWinBMP + HUD controller | groove 0x8a517556 (art 14015549), hidden 0x00008a50 (1401554a), arrows 0x6a5a4156 / 0xca5a415e (art 1401554b halves) | **controller 0x7E86C0–0x7E8A80** ⚠ *2026-08-17:* the groove's content is a **runtime-COMPOSED buffer** pushed by sub_7E8510 via SetImage, and its live imagerect is a **bind-time LATCH** — see the Addendum 2026-08-17 below (#176) |
| Panel containers | `0x89e1567c` | **cSC4WinGenTransparent** | 0xe9889775, 0x6a64e3c0, 0xca2aedc0 … | factory 0x4661D0, ctor 0x79C560 |
| Ticker clip strip | `GZWinFlatRect` (standard) | cGZWinFlatRect | 0xca2aeec0 | resized by ticker init 0x7726E2+ |

Other custom clsids named while mapping (for future passes): `0xca318388` cSC4WinMiniMap,
`0xaa5d16a9` cSC4WinAuraBar, `0xca5d3294` cSC4WinAlertBorder, `0x9a47b417` cSC4View3DWin,
`0x28c5a41f` cSC4WinMapView, `0xea659793` cSC4WinRegionScreen, `0x2ba6bb97` cSC4WinRegionView,
`0x2a3832aa` cSC4WinIntroVideoScreen, `0xaa38326e` cSC4WinSplashScreen,
`0xc918c6ff`/`0x4918c704`/`0x29aad0f6`/`0x29ab0142` LotConfig/NetworkLot chooser+editors.
Frequent but unnamed (framework classes registered at 0x4662B0, not in the named registry):
`0xcbcbf1e0` (134 uses), `0xaa7cecfd` (56 uses) — neither is one of our dynamic controls.

Class registration: window classes are registered in one function at **0x4662B0** with the
pattern `push <factory>; push <clsid>; mov ecx,esi; call 0x90E133`.

## Q2 — Geometry source per control (binary evidence)

### cSC4WinRCI — WINDOW-derived (follows doubling automatically)
`Draw` @ 0x7A9500 reads the live window rect `{L,T,R,B}` at `this+0xA8..0xB4`
(same fields the cIGZWin `GetW/GetH/GetL/GetT/GetArea` getters at 0x99C81B/0x99C82A/0x99BC53/
0x994EE4/0x99BCE1 return), picks horizontal vs vertical by `width > height`, computes
`half = extent/2` **from the window**, log-scales the demand value
(`fyl2x` ratio of `[this+0x128]` value vs `[this+0x120/0x124]` range) and multiplies by that
half-extent, then fills a rect via the draw context (`[this+0x6C]`, SetColor `[vt+0x54]`,
FillRect `[vt+0x8C]`). **No pixel constants anywhere in the function.**
The controller xref at 0x7ED362 only binds demand IDs and colors per column
(0x09d27eb0→{0x1010,0x1020,0x1030 residential}, 0x29d27ec0→commercial, 0x49d27ed0→industrial);
it never sets sizes.

*Reconciling "graph drew at ~stock size in doubled frames":* the code cannot draw at stock
size in a doubled window — if it looked stock, the three column windows themselves
(0x09d27eb0/0x29d27ec0/0x49d27ed0, only 8x71 each) were not actually resized in that run
(scaler timing/sweep miss), or the observation was of the 1x background art / mayor widget.
**Test:** dump the three windows' W/H after scaling; if 16x142, the bars are correct by code.

### cSC4WinTrendBar — ART-size-derived (content scales with the bitmap, not the window)
`Draw` @ 0x7BF0A0: requires two image objects `[this+0xEC]` (groove) and `[this+0xF0]` (fill);
draws them **centered in the window at native image size**
(`x = L + (winW − imgW)/2`, `y = T + (winH − imgH)/2`), splits the fill image into
**six cells — `bandW = fillW/6`
(0x7BF0E4 `imul 0xAAAAAAAB` / 0x7BF0F5 `shr 2`, the /6 reciprocal; #176(b))**, and places the fill marker at
`fraction[this+0xE0] × (imgdim − 1)` — i.e. every content dimension comes from the **image**.
Band/threshold constants at 0xABA3EC/F0/F4 and 0xABA414/418/41C are value-domain
(±1e-5, ±0.01, ±0.02), not pixels.

The images are **code-bound**: the polls controller at 0x7ED4AC loads
`{type 0x856DDBAC, group 0x46A006B0, instance 0x14015580}` and `{…, 0x14015584}` and passes
them to each TrendBar through its custom interface (`GetChildAsRecursive(id, iid 0xca5c2f84)`
then `[vt+0x10]` = SetImages) — the .UI scripts never reference these TGIs, so the
reference-driven selective-art build **missed them** (confirmed absent from
`tools/selective-safe/package-list.txt`; the .UI-visible tick overlay 14015585 IS in).

*Reconciling "poll FILLS appeared correctly proportioned in doubled frames":* the fill is
always proportioned **relative to its own groove image** (fraction × image width), so the
bar reads "correct" even when the whole groove+fill unit renders at 1x centered in the 2x
frame; the doubled 14015585 tick-overlay BMPs on top reinforce the impression.

### cSC4WinAdviceList (news ticker marquee + News window list) — WINDOW + FONT derived
- The class's draw-self override is a **no-op** (`mov al,1; ret` @ 0x949ADE) — children paint.
- Item creation @ 0x7931F1: creates the internal roll window (CreateInstance clsid
  `0xaa12e5f5`, iid 0x4a11fd4a) and sets its area to
  **`SetArea4(0, 0, GetW(), GetH())` of the AdviceList window itself** (vcalls `[+0xA4]`,
  `[+0xA8]`, `[+0xDC]` visible at 0x793210–0x79322E). The per-frame "child geometry reset"
  therefore *reproduces whatever size the container is* — it only fights us if we scale the
  children directly.
- Ticker init @ 0x77258B–0x772735: caches the marquee rect, fetches font style GUID
  **0xaa0f4ab4 = `AdvisorHeadline` in FontStyle.ini** from the font manager (0x913C72,
  `[vt+0x14]`, line-height `[vt+0x8C]`), computes scroll geometry as `3 × lineHeight`, and
  resizes the clip strip 0xca2aeec0 to `SetSize(W, min(2 × lineHeight, H))`.
  **Strip height and scroll step both scale with the font style — no pixel constants.**
  (Community's "ticker ignores font size" precedent was DAT-based FontStyle; our loose-file
  root FontStyle.ini is the probe-order winner per the FontStyle research, and the style is
  fetched live by GUID.)

### Funds / population / rating text — FONT-derived (already handled)
HUD controller binds cIGZWinText interfaces (iid 0x212cdc1f) for 0x09e418fe / 0xc9e41918 at
0x7EE64D+ and only updates captions. Sizes come from `font=` styles in the .UI —
`MayorFunds` 0x4a835024, `MayorPop` 0x4a835023, `MayorRCI` 0x4a835021, `MayorMRating`
0x4a835022, `MayorNeedsBars`/`Header` 0x4a835026/25 — **all present in FontStyle.ini**
(2x whole-file replacement already deployed). Doubled window + doubled style = correct.

### Mayor Rating slider — CODE CONSTANTS (the one true offender)
Controller at **0x7E86C0–0x7E8A80** (rating-change handler):
- groove BMP 0x8a517556: image (re)bound via cIGZWinBMP (iid 0xc12cea13) `[vt+0x10]`;
  groove art 14015549 is .UI-bound and already 2x in the package (staged imagerect 204x22).
   **Correction (#176, byte-verified): the staged
   imagerect is DEAD DATA at runtime.** What is (re)bound is not the sheet but a
  buffer **composed by sub_7E8510** (one filmstrip row of 14015549,
  `row = artH*(rating+100)/200`, replicated to every row), pushed through
  SetImage on EVERY rating tick — and SetImage's tail (0x9BC447) **overwrites
  the live imagerect** with `(0,0,min(areaW,imgW),min(areaH,imgH))` from the
  window's area AT THAT MOMENT. SetArea never touches it, so a bind that lands
  before a resize keeps drawing the old size until the next tick — the #176
  latch race, cured by RELATCH in v3.0.1. Full mechanism:
  `SC4-UI-ENGINE.md` §2.6; `_tests\REGRESSION.md` "#176 — ROOT CAUSE FOUND".
- `delta = newRating − oldRating` clamped to ±3, then:
  - **`SetW(delta * 7)`** on arrow window 0x6a5a4156 (imul @ **0x7E87B1**) or
    0xca5a415e (imul @ **0x7E89D7**), i.e. hardcoded **7 px per rating point** —
    a clip-reveal over the 42x9 arrow strip 1401554b (2x in package → 84x18);
  - left-arrow reposition `GZWinMoveTo(base + (3−delta)*7, y)` (imul @ **0x7E8A02**),
    base coords from cached fields `[obj+0x378/0x37C]` (snapshotted at panel init);
  - hidden side gets `SetW(1)` + HideWindow.
- Mayor face art swapped by state: code-bound instances **0x14315e60 / 0x14315e62**
  (0x7E8AF4/0x7E8B0A) — also **not in the override package**.

At 2x (doubled windows + 2x arrow art) the reveal shows **half** the intended arrow cells:
this is the "poll-bar drift"-adjacent mayor-widget artifact. Purely constant-driven.

## Q3 — Data-driven levers for CONTENT scale

| Control | Lever that changes content scale | In .UI script? |
|---|---|---|
| cSC4WinRCI | none needed — content = f(window area); window `area=` is the lever | yes (area already doubled) |
| cSC4WinTrendBar | **art size** of code-bound TGIs 0x14015580 (groove) + 0x14015584 (fill), group 0x46A006B0, type 0x856DDBAC | **no** — code-bound, must be added to the override .dat |
| cSC4WinAdviceList / ticker | **FontStyle.ini `AdvisorHeadline` (0xaa0f4ab4)** for text+strip+scroll; window size for width/child layout | font: no (code GUID); window: yes |
| GZWinText fields | FontStyle.ini styles (Mayor\*) | yes (`font=` names) |
| Mayor arrows | none — 7 px/step immediates | no |

No gauge-style min/max/scale attributes exist on these classes in the LEGACY .UI dialect —
TrendBar's value fraction and thresholds are set through its custom COM interface and static
floats. The only script-side levers are `area=`, `image=`/`imagerect=`, and `font=`.

## Q4 — Recommendations

| Control | Verdict | Action |
|---|---|---|
| RCI demand graph | **(a) already fine at 2x** (window-derived) | Verify the 3 column windows really get doubled (dump W/H post-scale); no code work expected |
| Opinion-poll bars (TrendBar) | **(b) fixable via data** | Add 2x overrides for code-bound art `{0x856DDBAC, 0x46A006B0, 0x14015580}` and `{…, 0x14015584}` to z_SC4UIScale_SelectiveArt.dat (2x-in-place, same TGI — they're loaded from DBPF by TGI, so an override dat wins). Rerun build with these added to the exclusive set |
| News ticker marquee | **(b) fixable via data + scaler policy** | Un-tombstone: double ONLY the marquee window 0xaa12f33c (+ panel/flatrect/BMP as normal windows), **never touch AdviceList children**; 2x `AdvisorHeadline` in FontStyle.ini does the rest (strip height + scroll step are font-derived). Keep the double-scale guard for its children permanently |
| Funds/population/date/rating texts | **(a) already fine at 2x** given deployed 2x FontStyle.ini | Nothing; if a field still looks 1x on the table, that's a FontStyle probe issue, not geometry |
| Mayor Rating change-arrows | **(c) needs code hook** (small) | In-place byte patch at DLL init: the three `imul …, 7` sites — bytes `6B F6 07` @ 0x7E87B1, `6B C9 07` @ 0x7E89D7, `6B C9 07` @ 0x7E8A02 — change the last byte 0x07→0x0E when ScaleAll=2x. Also add 2x overrides for face art 0x14315e60/0x14315e62 (check for siblings 0x14315e61/63 at runtime). Verify the cached arrow base pos `[obj+0x378/0x37C]` is captured post-scaling (it's snapshotted at panel init; our scaler runs after — confirm on table). Fallback: **(d) accept at 1x** — the arrows are 21x9 garnish |
| News/advice window art (bonus finding) | future pass | More code-bound art constants live at 0x77A495–0x77A837 and 0x780952–0x78910C (instances 0x140155b4..0x140155f7, c8, cb, cc, d0–d7) — the news window + advisor panels bind art by TGI in code; include when that panel is tackled |

## Addendum 2026-07-29 — News content SOLVED: it is an HTML engine (v2.19.0)

The Q4 ticker recommendation ("2x AdvisorHeadline does the rest") was HALF
right: the font style drives the marquee GEOMETRY (measured 676x90 = 3 x
doubled lineHeight live) but the item TEXT comes from the game's HTML
renderer — exe .rdata templates with literal `SIZE=2`/`SIZE=3` (reader
headlines 0xA83850/0xA83820, story pages 0xAB57A8/0xAB5810, bold headers
0xA83880/0xAB51C0, popup builder format string 0xA97F08 with sc4:// LINK
support), plus 189 locale LTEXTs with embedded `<font size="N">`. SIZE=1..7
resolves via the FONT table 0xACD4A0 {8,10,12,14,18,24,36} (engine setup
`push 7; push 0xacd4a0; call 0x8FEEB8` at 0x905C82 — the setter COPIES into
each rich window at this+0x1A8) and H1..H7 via 0xAB4AD0 (passed per-window
at 0x76A1FD). Popup builders derive their index from the MessageHeader/Body
style sizes: `idx = (4*size+8)/18` at 0x762F30 / 0x52CC70. Fixed in
SC4UIScale v2.19.0 by scaling both tables + retargeting the popup style
GUIDs at stock-size clones — full mechanism and trap signatures in
`_tests\REGRESSION.md` ("NEWS BOX + NEWS TEXT = THE HTML ENGINE").
Bonus-finding art (0x140155b4..f7) + LTEXT sc4:// art now in SelectiveArt
(328). The rich-item class 0xaa12e5f5 lives at code ~0x8FA317 (GetClassID);
creation sites 0x443FC9/0x76A182/0x78CE11/0x7931F0.

## Addendum 2026-07-23 — Audio Options playlist grid checkboxes (FIXED)

The Audio Options playlist (`.UI {0x96A006B0, 0xCA53F06E}`, GZWinGrid id
`0x8a550c56`) draws a per-row checkbox from **code-bound art
`{0x856DDBAC, 0x46A006B0, 0x14416244}`** (128x16 = 8 states of 16x16; the
instance ONE below the .UI-bound radiocheck strip 0x14416245). Loaded by the
audio controller at **VA 0x4F4B78 / 0x4F4E37** (explicit group 0x46A006B0
immediates; the {1ABE787D,14416244} twin is NOT loaded by this path) via the
standard image loader `call 0x602B00` — override dat wins by TGI. Zero .UI
refs (corpus-verified). Added to `CODE_BOUND_TGIS` in build_selective_safe.py;
**in-game verified at 2x: both checked and unchecked states draw correctly**,
i.e. the grid's strip slicing is proportional (imageWidth/8), no pixel
constants — same rule as GZWinBtn.

Two builder bugs fixed with it in build_dialog_static.py: the grid attrs are
spelled `drowheight`/`dcolwidth` (d-prefixed), so the original
`\browheight` regex silently missed them (rows shipped 20px inside the
doubled dialog); and `wingridcol="1,1,200 "` carries a PIXEL column width in
every 3rd slot (scale the width, never the two index slots).

## Addendum 2026-07-29 — the U-Drive-It GAUGE class 0xCBCBF1E0 (task #47)

The "frequent but unnamed" clsid from Q1 (134 .UI uses) is the U-Drive-It
gauge dial. Fully mapped offline (`exe_scan.py` + `disasm_fn.py` + a new
Unicorn harness `tools/flyout-sim/emu_gauge.py`); working log in
`_checkpoints/task47-gauges.md`.

**Identity:** registration `push 0x466220; push 0xcbcbf1e0` @ 0x004663DA
(the clsid's ONLY .text hit is 0x004663E0). Factory **0x00466220**
(`new(0x108)`, returns base+4), ctor **0x007628E0**. MAIN vtable 0xAB4900
(18 slots), **cIGZWin vtable 0xAB46A0** (152 slots), custom iid
**0x0BCBF1DF** (QI @ 0x00762490). Overridden cIGZWin slots vs a stock
window: 0, 4 (Init: resolves style 0x68963C4C via font/style mgr 0x913C72),
5 (Shutdown), 62, **88 = draw-self = 0x00762830**, 121, 134, 136, 138,
142, 148.

**Fields** (cIGZWin-pointer relative): +0xd8 strip image (cIGZBuffer;
SetImage = main-vt slot 4 @ 0x762680), +0xe8 frame count (slot 6 @
0x762A20), +0xec/+0xf0/+0xf4 min/max/value floats, +0xf8 frame index
(recomputed by 0x762770: `(value-min)/(max-min)*count`, then invalidate via
vt idx 92 +0x170), +0xfc style GUID, +0x6c draw context (cIGZWin base
field, same as cSC4WinRCI).

**Draw @ 0x00762830 (30 instructions):**
```
cellW = img->Width()/count;   H = img->Height();
frame = vt[72]() ? [this+0xf8] : 0;              // +0x120 visibility gate
src = {frame*cellW, 0, frame*cellW+cellW, H};
dst = {0, 0, cellW, H};                          // <- ART-derived, window IGNORED
[this+0x6c]->vt[38](img, &src, &dst);            // ctx +0x98, callee cleans 12
```
**Geometry source = ART (like cSC4WinTrendBar), NOT window, NOT a cached
buffer.** There is no equivalent of the minimap's [+0xE4]/[+0xF0] or the
disaster container's [0xdc]/[buf+0x1c] — the force-recreate-buffer lever
does not apply to this class; there is nothing to recreate. Emulator proof:
1x art (928x62/16) in a doubled 116x124 window -> dst (0,0,58,62) = the
exact top-left-quadrant symptom; 2x art -> dst (0,0,116,124).

**Why the art pass missed it:** the .UI children carry NO `image=`. The
dashboard binder **0x005646AE–0x0056477C** reads VEHICLE EXEMPLAR
properties `0x2BE8E834` (gauge window ids) / `0x2BE8E6CB` (strip image
instances, group 0x46A006B0) / `0xABE8E6CC` (frame counts), loads via
0x602B70, and injects through iid 0x0BCBF1DF. Per-vehicle min/max/value
setters at 0x00566100+. Dashboard .UI bound as id 0x4BCB938A / iid
0x22BA0121 @ 0x00564644.

**Fix shipped (v2.23.2-gauges):** per-instance vtable-copy hook on slot 88,
scoped under dashboard root 0x4BCB938A, class-verified (`vt == 0xAB46A0 &&
vt[88] == 0x762830`); inside the draw the context's vtable is swapped to a
copy whose slot 38 scales the DEST rect only (source untouched — widening
src reads past the texture = the documented tiling mess), restored
immediately after. Self-limiting to the live window so an unscaled window
or already-2x art degrades to a no-op. Optional crisper follow-up: mine
0x2BE8E6CB across the 43 vehicle exemplars and add those TGIs to
CODE_BOUND_TGIS (the runtime multiplier then self-limits to 1.0).

## Addendum 2026-08-17 — #176: the SetImage crop LATCH; TrendBar is immune; the fill strip is /6

Two claims above were half-true and each half-truth cost real time; both are
corrected inline and expanded here. Byte evidence 2026-08-16; ledger:
`_tests\REGRESSION.md` "#176 — ROOT CAUSE FOUND" / "#176(b)"; engine model:
`SC4-UI-ENGINE.md` §2.6.

1. **Mayor Rating groove (GZWinBMP 0x8a517556).** The Q2 row's "art 14015549
   is .UI-bound and already 2x (staged imagerect 204x22)" described the
   package, not the runtime. sub_7E8510 **composes** the fill buffer per
   rating tick (row = artH*(rating+100)/200 of 14015549, replicated to all
   rows) and pushes it via cIGZWinBMP::SetImage (0x9BC57E) on every firing,
   even delta=0. SetImage's tail 0x9BC447 rewrites the live imagerect
   [win+0xE8] to `(0,0,min(areaW,imgW),min(areaH,imgH))` **from the window's
   area at bind time**; GZWinBMP::SetArea (0x99C837) never touches it; the
   draw (0x9BC325) is dst-follows-src off that member. First bind beats the
   city sweep in 61/61 captured sessions → the crop latches at the 1x size and
   heals only on the next sim rating tick. ⭐ THE LATCH LAW: a latch computed
   from live geometry is a hidden consumer of that geometry — ask WHEN content
   was BOUND, not what the geometry is now. Cured in v3.0.1 (RELATCH,
   `src\UiSpike.cpp` — armed per panel root, latch-signature keyed).
   Consequence for this file's Q3/Q4 tables: the groove's script-side
   `imagerect` is NOT a live lever on that window, and the three `imul ,7`
   sites remain ARROWS ONLY — **no pixel constant exists in the fill chain**
   (measured tick pitch at row 5 is 4px, not 7).

2. **cSC4WinTrendBar (polls bars) is IMMUNE to the latch** — Draw 0x7BF0A0
   (vt 0xABA430 slot 88) re-reads every geometric input per frame: groove/fill
   dims via cIGZBuffer Width/Height virtuals each draw, vertical extent from
   the draw rect recomputed at vt+0x184 (0x99CF6A) inside the SetArea chain;
   SetImages (0x7BEEB0, main vt 0xABA68C slot 4) stores POINTERS only. Full
   member census: zero stale-able geometry; bind-before and bind-after the
   sweep draw identically (f=2 control pixel-exact). Correct fractional polls
   bars therefore need only the shipped fractional art + the sweep — no code.
   And the fill sheet {46a006b0,14015584} is a **six-cell strip** (the /3 in
   Q2 was wrong): states=6 is carried in `find_cell_strips.py`'s CODE_BOUND
   table because zero `.UI` refs exist for the `.UI`-derivation to see.

## Method notes / reproducibility

- Class-name registry: `.data` VA 0xB08F74 region, stride 8, `[clsid][char* name]`;
  name strings pooled at VA ~0xA89000. Dump script pattern: walk pairs while the pointer
  resolves into `.rdata`.
- Community cIGZWin header (vendor/gzcom-dll) slot numbering is confirmed by game code for
  `GetW +0xA4, GetH +0xA8, GetArea* +0xC0, SetW +0xCC, SetSize +0xD4, SetArea4 +0xDC,
  GZWinMoveTo +0xE0, GetChildAsRecursive +0x94, ShowWindow +0x110/Hide +0x114 (observed),
  SetID +0xFC` — but drifts in the high region: the **draw-self virtual is empirically slot 88
  (vtable+0x160)**, found by diffing the four class vtables (identical base impls everywhere
  except overridden slots). Window rect lives at `this+0xA8..0xB4` (L,T,R,B) on the cIGZWin
  subobject; TrendBar's draw sees it at `this+0x24..0x30` (different subobject offset).
- Vtables: cSC4WinRCI 0xAB8628 (cIGZWin at this+4; main 0xAB8884), cSC4WinTrendBar 0xABA430
  (main 0xABA68C), cSC4WinGenTransparent 0xAB7358, cSC4WinAdviceList 0xAB58B0.
- Custom interface IIDs seen: cISC4WinTrendBar 0xca5c2f84, cISC4WinAdviceList 0xca1492a2,
  cIGZWinBMP 0xc12cea13, cIGZWinText 0x212cdc1f, ticker-item iid 0x4a11fd4a.
- The ticker init also proves the HUD loads its .UI by TGI `{0x96a006b0, 0x2a2aed99}` at
  0x7EE69E (matches the extracted script name).
