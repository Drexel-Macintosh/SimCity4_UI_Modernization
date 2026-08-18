# SC4 Exemplar-Bound Item Icons & My Sims Portraits — 2x Scaling Research

Research date: 2026-07-21. Companion to `UI-ART-BINDING.md` (.UI-script art) and
`DYNAMIC-CONTROLS.md` (code-drawn HUD controls). This file covers the LAST art-binding
class the scaler cannot yet double: **exemplar-bound `ItemIcon` art** (toolbar picker /
flyout item buttons) and the **My Sims portrait strip**.

Binary: `SimCity 4.exe` 1.1.641.0 Steam (x86, in `...\SimCity 4 Deluxe\Apps\`),
ImageBase 0x400000, file offset = VA − 0x400000 in `.text` (VA 0x407000..0x680000).
All analysis offline (capstone 5.x + a from-scratch DBPF exemplar parser, both in the
appendix). Game files read-only.

## STATUS: substantially complete. Q1/Q2 solid, Q4 solid, Q3 partial (portrait-art
TGI source not fully traced — see the marked gap). Enough for an implementation recipe.

---

## TL;DR / recommended recipe

- **ItemIcon TGI = `{ type 0x856DDBAC, group 0x6A386D26, instance = <Item Icon value> }`.**
  The exemplar property **`0x8A2602B8` ("Item Icon")** holds only the *instance* ID;
  the type (0x856DDBAC PNG) and group (0x6A386D26) are **hardcoded in the exe** and
  concatenated at load time (proven at 3 code sites, below).
- Every ItemIcon PNG is a **176x44 four-state button strip** (four 44x44 cells:
  normal/hover/pressed/disabled). It is bound to a **GZWinBtn** (the menu-item button
  template, clsid **0x4988BC6A**). Button state selection = imageWidth ÷ 4 —
  **proportional, no pixel constants** — so a 2x strip (352x88, four 88x88 cells) still
  picks the correct cell. This is the same "state strips are safe" rule proven for
  .UI buttons in `UI-ART-BINDING.md` §3.
- **266 distinct ItemIcon PNGs exist** (all in group 0x6A386D26). **All 266 already have
  2x upscales** in `tools\upscale\preview\SimCity_1\` (verified: 0 missing). No new art
  needs generating — they just need packing into an override .dat at their **same TGIs**.
- **RECIPE for the toolbar picker/flyout icons:** add the 266 icon TGIs (2x, same TGI) to
  the override .dat (same 2x-in-place mechanism as the TrendBar art in `DYNAMIC-CONTROLS.md`
  §Q4 — override DBPF wins by TGI). Then the doubled item-button slots show 2x icons.
  This removes the reason the zoning flyout (0x69923479) and utilities flyout
  (0xE992F711) were excluded in `UiSpike.cpp` — re-test them with the icons packed.
- **My Sims strip (0x698894D3):** portrait slots are **code-created** at a **fixed slot
  pitch** (135px, 36x41 art) and the strip fills `containerWidth / slotPitch` slots — so a
  doubled container tiles MORE 1x slots (the observed artifact). Getting the stock count at
  double size needs the **slot pitch doubled in code** (a hook, not data) PLUS 2x portrait
  art PLUS the doubled container. Pure data cannot fix this one. Lower priority than the
  toolbar icons. (Portrait-art TGI source: see partial finding Q3.)

---

## Q1 — How menu/picker ItemIcons bind

### Exemplar storage
- Exemplars are **TypeID `0x6534284A`**, cohorts **TypeID `0x05342861`**, both in
  **SimCity_1.dat only** (8,957 exemplars + 388 cohorts there; SimCity_2–5 and EP1 have
  **zero** exemplars/cohorts — gameplay data is entirely in _1).
- All 8,957 are **binary** format (signature `EQZB1###`; cohorts `CQZB1###`). No text
  (`EQZT`) exemplars in the base game. Format decoded from scratch (appendix); 8,957/8,957
  parse cleanly.

### The three Item* properties (found by census of all 8,957 exemplars)
| Property ID | Standard SC4 name | Type | Count | Meaning (from values) |
|---|---|---|---|---|
| **`0x8A2602B8`** | **Item Icon** | Uint32 | 278 exemplars, **266 distinct values** | icon PNG **instance** ID |
| **`0x8A2602B9`** | **Item Order** | Uint32 | 253 exemplars | sort index within the menu (0,1,2,3…) |
| **`0x8A2602BB`** | **Item Button ID** | Uint32 | 83 exemplars, 38 distinct | the menu/button/group the item lands in |

Co-occurrence: B8-only 77, B8+B9 118, B8+B9+BB 83, B9-only 52. (Property *names* are the
well-known SC4-modding names; here they are **confirmed by value semantics**, not by an
embedded string — binary exemplars carry no names.)

Related properties seen at the same code sites (not censused in full):
`0x8A2602A9` (item display-name / LTEXT key, group `0xCA416AB5`) and `0xABE1AF70`
(an **alternate icon** property used only when a condition holds — see site 2 below).

### The icon TGI is assembled in code (the key finding)
The `Item Icon` value is ONLY the instance. Type and group are exe constants. Three
code sites read `0x8A2602B8` and immediately stamp `0x856DDBAC` + `0x6A386D26`:

- **Site 1 — 0x78EDC9:** `push 0x8A2602B8; push esi; call 0x5FD480` (GetProperty), then
  at **0x78EE09** `mov [esp+0x30], 0x856DDBAC` and **0x78EE11** `mov [esp+0x34], 0x6A386D26`,
  then `call 0x602B00` (image load). Also reads `0x8A2602BB` at 0x78EDD9. Creates the item
  object via `call 0x79B6B0` (0x78EE4B).
- **Site 2 — 0x7ECB1E:** `push 0x8A2602B8` (but at 0x7ECB12, if a `[edx+0x4C]` test on
  `0x144161EC` is true, it uses `push 0xABE1AF70` instead — an alternate icon). Group/type
  stamped at **0x7ECB44** `0x856DDBAC` / **0x7ECB4C** `0x6A386D26`, `call [edx+0x94]`.
  Reads `0x8A2602B9` (order) at 0x7ECBDD.
- **Site 3 — 0x7F0359 / 0x7F038F / 0x7F0597:** same pattern (B8, group 0x6A386D26, B9).

**Conclusion:** `ItemIcon TGI = {0x856DDBAC, 0x6A386D26, <B8 value>}`.

### Evidence B8 = a real PNG instance in group 0x6A386D26
Cross-checked all 266 distinct B8 values against the extracted PNG store:
- **266 / 266 resolve** to a PNG in **group `0x6A386D26`** (0 misses).
- **All 266 are exactly 176x44 px** — i.e. a 4-cell horizontal state strip, 44x44 per cell.
  (Matches the PNG census in `dbpf\NOTES.md`: group 0x6A386D26 holds 356 PNGs, the icon pool.)

### Bitmap-size vs button-rect fit
The icon is drawn by a **GZWinBtn** (the menu-item button template, clsid **0x4988BC6A**;
GZWinBtn class iid `0x00008810`, descriptor at VA 0xAD5CAC). GZWinBtn draws a **4-state
strip**: it divides image width by 4 to select the cell (`UI-ART-BINDING.md` §3 proves this
is proportional with no pixel constants). For **standard-style** buttons the state cell is
fit/stretched to the button rect at least horizontally (that doc's open question O1 — the
vertical-stretch case — is still the one untested variable). Practical upshot: whether the
44x44 cell is blitted 1:1-centered or fit-to-rect, a **doubled button slot needs a doubled
(88x88-cell) strip** to look right, and the 4-state math never clamps or crops.

The current in-game artifact ("1x icons centered in 2x slots") is consistent with the icon
being drawn at its native cell size while the surrounding slot is doubled — plus the
scaler's own `centerLeaves` centering (`UiSpike.cpp` ScaleSubtree, ~line 1049).

## Q2 — Does a 2x PNG at the same TGI draw at 2x, or clamp/crop?

**It draws at 2x; nothing clamps.** Reasons:
1. Images are loaded **by TGI from the DBPF chain** (`call 0x602B00` / `[edx+0x94]` at the
   sites above). A Plugins override .dat supplying `{0x856DDBAC, 0x6A386D26, I}` at 2x wins
   over SimCity_1.dat — identical to the mechanism already used for the .UI selective art
   and the code-bound TrendBar art (`DYNAMIC-CONTROLS.md` §Q4).
2. GZWinBtn state selection is `imageWidth / 4` — a 352-px-wide strip yields 88-px cells,
   correct state every time. No hardcoded 44 or 176 anywhere in the draw path (the item
   sites contain no icon-dimension immediates; the only nearby constants are the TGI type
   `0x856DDBAC` and group `0x6A386D26`).
3. There is **no `imagerect` crop** on these buttons (the icon comes from the exemplar, not
   a .UI `image=`/`imagerect=` pair), so the `imagerect`-doubling caveat from
   `UI-ART-BINDING.md` §3 does **not** apply here — this is strictly a strip, safest case.

**The one thing to confirm on the table:** that the item-button *slot* is actually being
doubled by the scaler when the picker is open. If the slot is 1x, a 2x icon overflows; if
2x, it fits. The exclusion list in `UiSpike.cpp` (`kNeverScaleIds`) currently keeps the
flyout columns at 1x precisely to avoid the mismatch — the fix is: pack the 2x icons, then
REMOVE 0x69923479 / 0xE992F711 from `kNeverScaleIds` and re-test.

## Q3 — My Sims strip slot width (PARTIAL — art source not fully traced)

- Strip window **`0x698894D3`** (container `blttype=tiled`, area 881x139), inner scrolling
  root **`0xCA1F1D9C`**. Defined in .UI script **`{0x96A006B0, 0xAA1F1F57}`** (+ its
  `0x08000600` 800x600 twin). Left end-cap BMP `0x00000002` = `image={46a006b0,13f15240}`
  (60x182). The player-portrait tab buttons use `image={46a006b0,13f1524c}` and the
  nameplate BMP `image={46a006b0,13f1524d}` (128x37).
- **Portrait slots are code-created, not .UI-listed.** The .UI carries **template** BMP
  slots `0x22220000..0x22220004` (5 of them), each **area 36x41 px** on a **135-px
  horizontal pitch** (225,360,495,630,765 → step 135), each with `imagerect=(0,0,36,41)`
  and **no `image=`** (the portrait bitmap is bound at runtime). A separate chooser-portrait
  template `0x22220055` (36x41) exists in the "swap sim" sub-panel.
- The strip-builder code references the container and templates:
  `0x698894D3` at VAs 0x76E8FB / 0x76EA11 / 0x76FD02; `0xCA1F1D9C` at 0x76E7C7 / 0x76E91E /
  0x76EA3B / 0x76EAA4 / 0x76F480 / … ; portrait template `0x22220000` at 0x76EB67 / 0x76F889
  / 0x76FAD8 / 0x76FBBF; chooser template `0x22220055` at 0x7717EA / 0x7718CA. This is where
  the "how many portraits fit = containerWidth / slotPitch" loop lives.
- **Why doubling the container alone re-tiles MORE 1x portraits:** the slot pitch (≈135px)
  is a code/layout constant, not derived from art size, so a wider container just fits more
  135-px slots. To land on the **stock count at double size** you need, together:
  (a) 2x portrait art, (b) the **slot-pitch constant doubled in code** (a byte/immediate
  patch, analogous to the Mayor-arrow `imul …,7` patch in `DYNAMIC-CONTROLS.md` §Q4), and
  (c) the doubled container. Data-only cannot do it.
- **GAP (needs a follow-up pass):** I did not finish tracing the exact TGI the portrait
  bitmap is loaded from (the slots have no `image=`; the portrait art is code-bound like the
  TrendBar art). Next session: disassemble the loop around 0x76EB67–0x76FBBF for the
  `SetImage`/image-load call and its type/group immediates (expect the same `0x856DDBAC` +
  a group constant pattern as Q1). Also confirm the pitch immediate to patch (search the
  loop for `135`/`0x87` and the slot `area` math).

**Recommendation:** treat My Sims as **lower priority / code-hook** work, or leave the
strip at 1x (it stays in `kNeverScaleIds`). The toolbar icons (Q1/Q2) are the high-value,
data-only win.

## Q4 — Work estimate for the LEFT TOOLBAR tree

Two separate icon systems feed the left toolbar and its flyouts:

1. **Fixed flyout-column button art (.UI-bound)** — the persistent left-column buttons in
   scripts like `{0x96A006B0, 0xE9949936}` (zoning col 0x69923479),
   `{0x96A006B0, 0x4992F764}` (utilities col 0xE992F711), etc. Their `image=` refs are the
   **group 0x46A006B0 4-state strips** (e.g. `14215e60`, `14215e28`, `14215e2a`) — these are
   already part of the **431 .UI-referenced PNGs handled by the selective-safe pipeline**
   (`tools\selective-safe\`). No new work here beyond that pipeline.
2. **Dynamic picker/flyout ITEM icons (exemplar-bound)** — the buildings/parks/rewards/
   utilities items that populate the sub-menus from exemplars. These are the
   **`{0x856DDBAC, 0x6A386D26, I}`** icons: **266 distinct TGIs**.

**Distinct icon TGIs to ship: 266** (upper bound = the entire ItemIcon pool; these populate
the whole left-toolbar menu tree — parks, rewards, water, power, education, health, safety,
transport pickers). A tighter "only the currently-open flyout" subset was not separated out
(would require walking each menu's `Item Button ID` grouping) — but since all 266 already
have 2x art, shipping the full set costs nothing extra and is the safe choice.

**Do 2x upscales already exist?** **YES — all 266 do.** Verified against
`tools\upscale\preview\SimCity_1\` (naming `T-0x856ddbac_G-0x6a386d26_I-0x<inst>.png`):
0 of 266 missing. The preview folder holds all 2,206 PNG-magic entries, so the icon pool is
fully covered. **No new upscaling required** — only DBPF packing at the same TGIs.

Effort: pack 266 existing 2x PNGs into the override .dat (reuse `DbpfPack.exe`), add them to
the selective/exclusive art set, and drop 0x69923479 / 0xE992F711 (and any other
exemplar-icon flyouts) from `kNeverScaleIds` in `UiSpike.cpp`. Table re-test the pickers.

---

## Concrete reference values (for a fresh session)

- Exemplar type `0x6534284A`; cohort type `0x05342861`; both **SimCity_1.dat only**.
- Item props: **`0x8A2602B8` Item Icon**, **`0x8A2602B9` Item Order**, **`0x8A2602BB` Item
  Button ID**; alt icon `0xABE1AF70`; item name `0x8A2602A9` (LTEXT group `0xCA416AB5`).
- Icon TGI = **`{0x856DDBAC, 0x6A386D26, <B8>}`**; 266 distinct; every one **176x44** (4×44).
- Icon read/assemble code: **0x78EDC9 / 0x78EE09 / 0x78EE11** (site 1),
  **0x7ECB1E / 0x7ECB44 / 0x7ECB4C** (site 2), **0x7F0359 / 0x7F038F / 0x7F0597** (site 3).
- Menu-item button template clsid **0x4988BC6A** (state siblings 0x2988BC85, 0xC988BC79,
  0x8988BC94); menu handler code 0x7EC41C–0x7EC586; toolbar handler code 0x7F5944–0x7F5C6F;
  also 0x7E9150, 0x7E97A0, 0x7F21B0.
- Item object ctor **0x79B6B0**, vtable **0xAB6FE4** (draw-self and getters not re-diffed
  here; it inherits the GZWinBtn draw path).
- GZWinBtn iid `0x00008810` (descriptor 0xAD5CAC); GZWinBMP iid `0xC12CEA13` (descriptor
  0xAD5CE0). Standard-class clsid/iid/descriptor table at **VA 0xB16FA0** (12-byte stride).
  Named cSC4Win* clsid→name registry at **VA 0xB08F78** (8-byte stride).
- My Sims: strip window **0x698894D3**, inner root **0xCA1F1D9C**, script
  `{0x96A006B0, 0xAA1F1F57}` (+0x08000600 twin); portrait templates **0x22220000..04**
  (36x41, 135px pitch) and chooser **0x22220055**; builder code 0x76E7C7–0x76FD25,
  0x7717EA–0x77157C.
- Current scaler exclusions (`src\UiSpike.cpp` ~line 70, `kNeverScaleIds`): 0x69923479
  (zoning flyout), 0xE992F711 (utilities flyout), 0x698894D3 (My Sims). Menu-flyout scaler
  `ScaleMenuFlyouts` at line 973; container id `0xAA32BCE6`.

## Appendix — reproduction

### DBPF exemplar extraction
`tools\dbpf\DbpfExtract.exe "<...>\SimCity_1.dat" <out> 0x6534284A`  → 8,957 exemplars
(`.png`-named but binary EQZB). Cohorts: filter `0x05342861` → 388.

### Binary exemplar (EQZB1###) format — decoded here, matches game
```
0x00  char[8]  signature "EQZB1###" (cohort "CQZB1###")
0x08  u32×3    parent cohort TGI
0x14  u32      property count
0x18  properties, each:
        u32 propId
        u16 valueType   (0x100 u8, 0x200 u16, 0x300 u32, 0x700 s32,
                         0x800 s64, 0x900 float, 0xB00 bool, 0xC00 string)
        u16 keyType      0x80 = array, 0x00 = single
        if array: 1 pad byte, u32 repCount, then repCount values
        if single: 1 pad byte, then ONE value   <-- the pad byte on singles
                                                     was the parser gotcha
```
Python parser + census: `scratchpad\ex_scan.py` / `item_analysis.py` (writes
`scratchpad\item_table.csv` = every exemplar's G/I, name, B8/B9/BB, parent cohort).

### Exe scanning / disassembly
- Immediate search: `scratchpad\exe_scan.py`, `exe_scan2.py` (find where a TGI/prop/window
  id appears as a `.text` immediate).
- Disassembly: `scratchpad\disasm.py <startVA> <endVA>` (capstone, file off = VA−0x400000).
- Class registries: `scratchpad\classreg.py`, `namehunt.py`, `vtdump.py`.
- .UI dumping (CR-line-ending safe): `scratchpad\ui_dump.py <file> [needle]`.

### Key verified numbers
- 266/266 B8 values resolve to group-0x6A386D26 PNGs; all 176x44; 266/266 have a 2x file in
  `tools\upscale\preview\SimCity_1\`. Preview holds all 2,206 PNG-magic entries.
