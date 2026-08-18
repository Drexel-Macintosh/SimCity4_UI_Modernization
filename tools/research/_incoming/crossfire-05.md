## VERDICT — reconciled

I re-measured every load-bearing claim myself (PE headers, capstone disassembly, PNG pixel decode, DBPF index scans of 150 archives). Four angles, one mechanism, **three of the four angles wrong on at least one detail**. Adjudications below.

---

## 1. SETTLED (all four angles agree AND I independently verified)

**S1. The brief's premise is a blind-instrument null.** The bar is not painted into a GZWinBMP buffer. It is a real child window: `id=0x4A553000`, `clsid=0xAA5D16A9` (= cSC4WinAuraBar), 1x area `(11,92,113,103)` = **102x11**, at depth 3 under the bubble root.
*My evidence:* `tools\uiscripts\extracted\T-00000000_G-96a006b0_I-ca539340.ui` line 10 — read in full. **Positive control:** the same nesting level holds `0x4a552000` "Unincorporated"/city-name, `0x4a552001` mayor-name, `0x4a552002/3/4/5/6` funds+population and the anonymous `caption="Mayor Rating:"` label — all of which visibly render, none of which appear in the dump. The dumper stops one level above them. `clsid=0xaa5d16a9` appears in **1 of 330** extracted .UI scripts.

**S2. cSC4WinAuraBar::Draw = VA 0x00797CC0.** I read the vtable slots directly (file offset = VA − 0x400000 for .text/.rdata/.data; verified from the PE section table — `.text VA=00407000 raw=00007000`):
```
[0x00AB64B8 + 0x160] = 0x00797CC0   cSC4WinAuraBar
[0x00ADF6A0 + 0x160] = 0x009BC325   GZWinBMP
[0x00ADDAF0 + 0x160] = 0x009B167D   GZWinBtn
```

**S3. The draw law** — disassembled at 0x00797CC0, byte-for-byte:
```
00797D16  8b7808  mov edi,[eax+8]     ; img.R          eax = image rect (call [img+0x30])
00797D19  8b4b08  mov ecx,[ebx+8]     ; win.R          ebx = &this->rect (this+0x24)
00797D1E  2bf9    sub edi,ecx
00797D22  2bfa    sub edi,edx         ; -img.L
00797D24  03f9    add edi,ecx         ; +win.L
00797D26  d1ff    sar edi,1           ; edi = (imgW - winW) >> 1   -> src.L
00797D2C..32      mov edx,[eax+0xc]; sub edx,[eax+4]; dec edx      ; imgH-1
00797D37..47      fild / fmul [esi+0xE8] / fadd [0xA92D28]=0.5 / call 0x9EEF04 (ftol)
00797D5B  mov [src.T],eax ;  00797D5F inc eax ;  mov [src.B],eax   ; src.B = src.T+1
00797D57  03cf    add ecx,edi         ; src.R = winW + src.L
00797D60  53      push ebx            ; DESTINATION = the full window rect
00797D79  e8420e1400  call 0x8d8bc0   ; (ctx, image, &src, &dst, 0,0,0)
```
**`src` width is taken from the WINDOW; only `src` position and the row divisor come from the ART. `src` height is always 1.**

**S4. The art is code-bound and unreferenced by any script.** Bind site (disassembled):
```
007B514C  push 0x4a5d1208        ; AuraBar custom iid
007B5157  push 0x4a553000        ; window id
007B515E  call [edx+0x94]        ; get-child-as
007B5178  call [edx+0x10]        ; SetFraction(double)
007B517E  push 0x14416327 ; 007B5183 push 0x46a006b0 ; 007B5190 call 0x602b70
007B51A7  call [edx+0x0c]        ; SetImage
```
Immediate counts in `.text`: `0x14416327` **1** (0x7B517F), `0x4A553000` **1**, `0x4A5D1208` **1**; contrast `0x14015549` **2** (0x7E851D, 0x7ED224 — both HUD controllers). `grep -ril 14416327 tools/uiscripts/extracted/` = **0 of 330**. refmap.csv rows for `14416327` = **0**; **positive control**: `0x856DDBAC,0x46A006B0,0x14416326,UNSCALED,...` row exists, because *that* one is .UI-referenced.

**S5. Fraction law** (disassembled 0x7B4FA0-0x7B4FE2 + 0x797C20): `call [eax+0x38]` → `movsx ecx,al` (rating is a **signed byte**), then `fmul [0xAB98B8]` where **[0xAB98B8] = 0.005**, `fadd [0xA92D28]` = **0.5**. SetFraction clamps to [0.0, 1.0] (`[0xA80990]=0.0`, `[0xA80AB0]=1.0`). So `frac = rating/200 + 0.5`, and `row = ftol(frac*(imgH-1) + 0.5)`.

**S6. The art is 102x26 and is overridden by NOTHING.** Indexed **139** DBPF archives under `Documents\SimCity 4\Plugins`, the game `Plugins` and `Apps` — `14416327` hits = **0**. **Positive control on the same indexer:** the game-root scan (11 archives) finds it twice in `SimCity_1.dat` (groups `46A006B0` and `1ABE787D`), and finds the HUD's `14015549` in both the stock dat and our `z_SC4UIScale_SelectiveArt-2x.dat`. The indexer is not blind; the null is real.

**S7. The RatingArrowPatch A/B was a structural null.** The imul-7 sites are in the HUD controller 0x7E86C0-0x7E8A80, which touches `0x14015549` / windows `0x6A5A4156` / `0xCA5A415E`. Disjoint from 0x797CC0 ← 0x7B5147. Nothing to explain.

---

## 2. CONFLICTS — named and adjudicated

### CONFLICT A — pixel structure of 14416327. **Angle 4 right, Angle 1 wrong.**
Angle 1: "26-row state stack, y cells filled from the left, 25 cells". Angle 4: "12 red left / centre / 12 green right; row 0 = 12 red, rows 12-13 empty, row 25 = 12 green".

I decoded the PNG (zlib + unfilter, RGB8, 102x26) and segmented on the `FF00FF` key:
```
row  0 : 24 cells, 12 RED (FF0000) | key gap | 12 grey (BBBBBB)
row 12 : 24 cells, all grey            <- neutral
row 13 : 24 cells, all grey
row 25 : 24 cells, 12 grey | key gap | 12 GREEN (00FF00)
```
**24 cells, all 3px wide, 1px magenta key between them, wider key gap at centre.** It is a **bidirectional** meter: red fills leftward for negative rating, green fills rightward for positive. Angle 1 misread the run-length pattern as a monotone fill and got the cell count wrong. Angle 4's reading is confirmed (its "6-px grey centre marker" is right for the HUD sheet — `14015549` has **25** cells, widths {3,4}, with a coloured `(172,179,175)` centre cell — and slightly wrong for the region sheet, whose centre is pure key).
*Why it matters:* the user's "green-fill-plus-groove pattern" is this 12+12 segment ladder, and "two runs side by side" means the ladder including **two centre gaps**. That is a real discriminator against a stretch/clamp model.

### CONFLICT B — is the whole bubble 1x-in-2x (Angle 3's 10-row suspect table)? **Angle 3 is refuted. Measured.**
Angle 3 concluded "all 10 bubble arts ship 1x; root cause = `0x0A551C50` missing from `SCALED_WINDOW_IDS`". It looked only at `tools/selective-safe/refmap.csv` + `package-list.txt` — **the wrong package**. The bubble is handled by `tools/dialog-static/build_dialog_static.py` → `z_SC4UIScale_DialogStatic-2x.dat`. Indexing that dat:
```
14416322 bubble-bg    PRESENT 2x     14416326 btn-play   PRESENT 2x
14416323 btn-close    PRESENT 2x     CBFB3730/31/32 stars PRESENT 2x
14416324 btn-delete   PRESENT 2x     14015586 tooltip     PRESENT 2x
14416325 btn-import   PRESENT 2x     14416327 RATING BAR  ABSENT
```
**9 of 10 already ship at 2x. Exactly one is missing.** Angle 3's rows 2-9 are non-defects; acting on that table would have burned a session on eight windows that are already correct.
Its root-cause claim is also wrong in kind: the bubble is **born** 2x by a static .UI clone, not by the runtime sweep — so the sweep's id list is irrelevant here.

### CONFLICT C — is winW=204 actually measured? **Yes, now. Angle 4's "one inferred link" is closed.**
I extracted `T=00000000 G=96A006B0 I=CA539340` from `z_SC4UIScale_DialogStatic-2x.dat` (offset 1341628, 14335 bytes, uncompressed text) and read the AuraBar line:
```
2x   : clsid=0xaa5d16a9 id=0x4a553000 area=(22,184,226,206)   = 204 x 22
1.5x : area=(17,138,170,155)                                   = 153 x 17
3x   : area=(33,276,339,309)                                   = 306 x 33
```
Every other row of the 2x clone matches the live dump to the pixel (root `(292,142,808,642)` = 516x500; inner BMP `(24,20,494,304)` = 470x284; the three band BMPs; all four buttons; the star BMPs). **The window is born 204 wide, statically. No runtime-scaler timing is involved.** Independently, the symptom itself measures it: copies = winW/imgW = 2 ⟹ winW = 204.

### CONFLICT D — does the blitter tile/wrap? **Partly measured, and it does not matter. Angle 4's caution was the honest position.**
I disassembled 0x8D8BC0. Confirmed: args are `(ctx, image, &src, &dst, 0,0,0)`; `srcW = src.R-src.L`, `srcH = src.B-src.T`; there is a `srcW==1 && srcH==1` solid-fill fast path (skipped here, srcW=204); and the software fallback at 0x8D8D3D **normalises the offset args modulo srcW/srcH** (`99 f7ff idiv edi` / `99 f7fb idiv ebx`, then the negative fixup `lea eax,[esi+ecx]; cdq; idiv edi; imul eax,edi; sub esi,eax`). That is textbook **tiled**-pattern origin normalisation, not clamping.
What is **not** traced to a byte is what the sampler does when the *src rect exceeds the image bounds* — the accelerated path goes through `QI{0xAB300B2B}` → `call [vt+0x9C]`, which I did not follow. **This is the one genuinely inferential link in the chain, and it is over-determined:** a clamping sampler would produce edge-smear (51px of flat colour, one ladder, 51px of flat colour), not two ladders; the user saw two ladders. And, decisively, **the fix is model-independent** — wrap, tile-period-=-imgW, or clamp all collapse to the same correct output once `imgW == winW`.

---

## 3. THE MECHANISM (single best-supported) + ARITHMETIC

> The region bubble's Mayor Rating bar is a **cSC4WinAuraBar** that builds its blit **source rect from its own window width** and takes only the *row index* from the art. Our static 2x clone borns that window at **204** wide; its art `{856DDBAC, 46A006B0, 14416327}` is **code-bound**, invisible to both reference-driven builders, and therefore still **102** wide. A 204-px source span over a 102-px image is exactly **two periods** of the segment ladder.

```
imgW = 102 (measured, PNG IHDR)         imgH = 26 (26 states, rows 0..25)
src.L = (imgW - winW) >> 1     src.R = src.L + winW     src.B = src.T + 1
row   = ftol(frac*(imgH-1) + 0.5),  frac = clamp(rating/200 + 0.5, 0, 1)

f=1.0  winW=102 -> src.x = [   0, 102)  = 102/102 = 1.00 period   ONE ladder   (stock, correct)
f=1.5  winW=153 -> src.x = [ -25, 128)  = 153/102 = 1.50 periods  1.5 ladders  (predicted, unseen)
f=2.0  winW=204 -> src.x = [ -51, 153)  = 204/102 = 2.00 periods  TWO ladders  <-- REPORTED
f=3.0  winW=306 -> src.x = [-102, 204)  = 306/102 = 3.00 periods  THREE ladders
```
Copy count == winW / imgW == the tier factor. This is the **same law already recorded** for task #49 (Grutzehaus menu icons) and #55 (picker icons) — "the count of visible copies tells you the scale ratio" — extended from `imagerect`-driven GZWinBMPs to a self-sizing painter. At f=2 the ladder's left edge lands at dst x=51 and again at x=153, so the seam falls at a half-period offset: **the two visible centre gaps should sit near dst x≈99 and x≈201**, not symmetrically. That is a falsifiable detail to check on the fix screenshot.

---

## 4. WHICH LEVER REACHES IT

**WINNER — art data.** Add `{0x856DDBAC, 0x46A006B0, 0x14416327}` to the DialogStatic package at each tier. The assets **already exist and already have the exactly-right widths**:
```
tools\upscale\preview\SimCity_1\T-0x856ddbac_G-0x46a006b0_I-0x14416327.png      204x52
tools\upscale\preview-15x\...                                                    153x39
tools\upscale\preview-3x\...                                                     306x78
```
and the measured clone window widths are **153 / 204 / 306**. Exact match at all three tiers ⟹ `src.L = 0`, `src.R = winW`, exactly one period. Blast radius: one 265-byte PNG per tier, bound at **one** code site, referenced by **zero** scripts — nothing else can consume it. Group `0x46A006B0` alone is sufficient: it is a literal push at 0x7B5183, **and** the HUD's `14015549` is overridden under `46A006B0` only and the HUD bar is user-confirmed correct — an empirical positive control for this exact art class. (The `1ABE787D` twin is a zero-cost hedge if wanted.)

**Height caveat, and the A1↔A2/3/4 conflict resolved:** width is load-bearing; **height is not drawn** (src is always 1 row, tiled down winH) — it only sets the state divisor `imgH-1`.
- `204x26` (width-only double) ⟹ divisor 25 ⟹ **byte-identical state selection to stock**.
- `204x52` (the existing uniform upscale) ⟹ divisor 51 ⟹ **23 of the 201 integer ratings** (−100..+100) land one cell off from stock; max deviation **1 state = 6px at 2x** (12.24% of the continuous domain — Angle 1's figure reproduced exactly).
**Recommendation:** ship the existing 204/153/306-wide assets as-is for the first A/B (zero new art, all tiers covered, cures the defect outright). Refine to height-26/26/26 only if stock-parity pixel-diffing (task #31/#70) flags it — it is a 6px cell on 11% of ratings, invisible without an A/B.

**LOSER 1 — the BMPX draw hook on vtable 0x00ADF6A0 slot 88.** Structurally cannot reach it. `src/UiSpike.cpp:4868` sets `kBmpClassVt = 0x00ADF6A0`; the gate at `:5020` is `if (vt != kBmpClassVt) return false;` and again at `:5098`. The AuraBar's vptr is `0x00AB64B8` — rejected before anything else runs. Separately, `HookRuntimeBmpsUnder` is only ever called with `kBmpxCityRoots` (`:5874`) and `kBmpxDialogRoots` (`:8702`), neither of which contains a region id. Two independent reasons; either alone is fatal.

**LOSER 2 — a code patch at 0x00797CC0.** No clean in-place byte edit exists: forcing `sar edi,1` → `xor edi,edi` at 0x797D26 fixes `src.L` but leaves `src.R = winW + 0` (still a 204-px span), and by 0x797D4C the image-rect pointer in `eax` has been clobbered by the ftol call at 0x797D47 — so clamping `src.R` to `imgW` needs a re-fetch, i.e. a **full detour** plus a new class-identification path, plus a `.rdata` vtable write at `0x00AB6618`, for one widget. Upside-down trade against a 265-byte PNG (SC4 blast-radius law).

**LOSER 3 (worth naming as a fallback, not a fix) — shrink the window instead.** Setting the AuraBar clone back to 102x11 also makes `imgW == winW`. It cures the doubling with no new art and is the cheapest *diagnostic* A/B, but it leaves the bar half-size inside a 2x bubble. Use only if the art fix somehow fails.

---

## 5. STILL GENUINELY UNKNOWN — as questions, with the exact measurement

**Q1. When the source rect exceeds the image, does the sampler wrap (period = imgW), tile at period = src rect, or clamp?**
*Measurement:* trace the object returned by `QI{0xAB300B2B}` on the draw context (0x8D8BC0 +0xEE) and disassemble its `[vt+0x9C]`. **Cheaper and sufficient:** the fix itself discriminates — if a 204-wide asset yields ONE correct ladder, every candidate model agrees and the question is moot. *Do not spend a session on this before the fix A/B.*

**Q2. Is the doubling the ONLY visible defect in the region bubble?**
Nobody in four angles has looked at the bubble on screen; Angle 3's 8 extra "suspects" are refuted at the data level but that is arithmetic, not eyes.
*Measurement:* one look at the bubble with a **founded** city selected (London: Kensington or Fulham). It must be an existing city — an empty tile raises the narrow stub `0x0A551C53` (script I-ca539343 / I-0a8cd184), which contains **no** AuraBar at all, which is exactly why all five existing stock region captures are useless here. Per the standing rule: `PrintWindow(PW_RENDERFULLCONTENT)`, never a full-screen grab of the user's desktop.

**Q3. Is the 1.5x tier also defective today (predicted 1.5 ladders), and does its window width 153 stay 153 after the 1.5x rounding law?**
*Measurement:* already half-answered — I read `area=(17,138,170,155)` = **153** from the shipped `z_SC4UIScale_DialogStatic-15x.dat`, and the preview asset is **153** wide. Match confirmed. The remaining half is eyes-on at the 1.5x tier, which is currently `.x1-disabled`.

**Q4. How many other code-bound art TGIs are missing from every package?**
`14416327` is one confirmed instance; `DYNAMIC-CONTROLS.md` Q4 already suspects the TrendBar (`14015580`/`14015584`) and mayor faces (`14315e60`/`14315e62`) — same class, unverified.
*Measurement:* scan `.text` for every 4-byte immediate that matches a known PNG instance id in `tools/dbpf/extracted-png-tgi.csv`, subtract the set referenced by any `.UI`, and diff against the three package lists. That is a complete, offline census of the blind spot.

---

## 6. FINDINGS THAT BELONG IN THE DOCS REGARDLESS OF THIS FIX

### → `tools\research\DYNAMIC-CONTROLS.md` — new section

> **cSC4WinAuraBar (clsid `0xAA5D16A9`) — the self-sizing meter**
>
> The Mayor Rating meter in the region city-select bubble is not a GZWinBMP. It is a `cSC4WinAuraBar`, the only use of that class in the entire 330-script UI corpus (`T-00000000_G-96a006b0_I-ca539340.ui`, `id=0x4a553000`, 1x area `(11,92,113,103)` = 102x11). Its class name is in the exe's clsid→name registry at `.data` VA `0x00B08FA0` → `.rdata 0x00A89594` = `"cSC4WinAuraBar"` (neighbours: `0xAA5C2F86` cSC4WinTrendBar, `0xCA1492AC` cSC4WinAdviceList).
>
> Object layout (size 0xF8, factory `0x00797F20`, ctor `0x00797E60`): `[+0]` primary vptr `0x00AB64B8`; `[+0x24]` window rect; `[+0x68]` draw context; `[+0xE0]` custom-interface vptr `0x00AB6488`; `[+0xE8]` fraction (double); `[+0xF0]` image. Custom IID `0x4A5D1208`; on that interface slot 3 (`+0x0C`) = `SetImage` (`0x00797E10`), slot 4 (`+0x10`) = `SetFraction(double)` (`0x00797C20`, clamped to [0.0,1.0] against `[0xA80990]`/`[0xA80AB0]`).
>
> **Draw (vtable `0x00AB64B8` slot +0x160 = VA `0x00797CC0`) — the trap.** It composes the blit source rect as
> `src.L = (imgW - winW) >> 1`, `src.R = src.L + winW`, `src.T = ftol(frac*(imgH-1) + 0.5)`, `src.B = src.T + 1`
> and passes the **full window rect** as the destination to the tiled blit helper `0x008D8BC0`. **The source WIDTH comes from the window, not from the art; only the row index comes from the art.** Consequently:
> * The art's **width must equal the window's width at every tier**, or the painter samples outside the bitmap and the pattern repeats `winW / imgW` times. At f=2 with the stock 102-wide art in a 204-wide window you get exactly two ladders side by side, offset half a period.
> * The art's **height is never drawn** — `src` is always one row tall and is tiled down the window. Height serves only as the state divisor `imgH-1`. A uniform 2x upscale therefore doubles the state count (26→52) and shifts the selected state by at most one cell on 23 of the 201 integer ratings; a width-only double preserves stock state selection exactly.
>
> **Art binding is by CODE, not by script.** The region-bubble populate routine `sub_7B4B80` does `GetChildAsRecursive(0x4A553000, 0x4A5D1208)` at `0x007B515E`, `SetFraction` at `0x007B5178`, then `push 0x14416327 / push 0x46a006b0 / call 0x602B70` (`0x007B517E`) and `SetImage` at `0x007B51A7`. Each of `0x14416327`, `0x4A553000`, `0x4A5D1208` occurs **exactly once** in `.text`. Group `0x46A006B0` is a literal push, so only that group needs an override.
>
> **The value law:** `call [eax+0x38]` returns the mayor rating as a **signed byte**; `frac = rating * 0.005 + 0.5` (`[0xAB98B8] = 0.005`, `[0xA92D28] = 0.5`), i.e. −100..+100 → 0.0..1.0.
>
> **Art anatomy** (`{856DDBAC, 46A006B0, 14416327}`, 102x26 RGB, twin under group `1ABE787D`): a 26-row vertical state stack. Each row is a bidirectional ladder of **24 cells, 3px wide, separated by 1px `FF00FF` key**, with a wider key gap at centre — 12 cells left of centre, 12 right. Row 0 = 12 red (`FF0000`) on the left; rows 12-13 = all neutral grey (`BBBBBB`); row 25 = 12 green (`00FF00`) on the right. The city-HUD groove `{46A006B0, 14015549}` uses the same 102x26 stack with 25 cells (widths 3 and 4, coloured centre marker) and a red/green **gradient**, but is consumed by a plain GZWinBMP with `imagerect=(0,0,102,11)` through the HUD controller `0x007E86C0-0x007E8A80`. **The two bars share no code and no art** — `0x14015549` appears in `.text` only at `0x7E851D` and `0x7ED224`. A change to either cannot regress the other.

### → `tools\research\SC4-UI-ENGINE.md` — three laws

> **Law: reference-driven art builders are structurally blind to code-bound TGIs.** Both `tools/selective-safe/build_selective_safe.py` (via `refmap.csv`) and `tools/dialog-static/build_dialog_static.py` (its stated rule: "Every `image={gid,iid}`: if a 2x PNG exists…") discover art by scanning `.UI` script attributes. Art that the exe pushes as an immediate and hands to `SetImage` is never named by a script, so it appears in **zero** refmap rows and **zero** package lists, and it silently ships at 1x inside a scaled window. Confirmed instance: `{856DDBAC, 46A006B0, 14416327}` — 0 of 330 scripts reference it, 0 refmap rows, 0 package rows, while its .UI-referenced siblings `14416321…14416326` all have rows and all ship 2x. Suspected further instances: cSC4WinTrendBar `14015580`/`14015584`, mayor faces `14315e60`/`14315e62`. **When a widget looks 1x inside a correct 2x frame and the art is not in refmap, do not conclude "no art" — scan `.text` for the instance id.**
>
> **Law: the duplicated-pattern signature now has two sources, and both give the same number.** Extending the task #49/#55 rule ("N copies = 1x art in an Nx cell"): the count of visible copies equals `windowWidth / artWidth` both for GZWinBMPs with an `imagerect` and for **self-sizing painters that derive their source rect from the window** (`cSC4WinAuraBar::Draw`). In the second family there is no `imagerect` to inspect — the only cure is to make the art's width equal the window's width at every tier. Measured tier widths for the region rating bar: 153 / 204 / 306 at f = 1.5 / 2 / 3, all read out of the shipped `z_SC4UIScale_DialogStatic-*.dat` clones.
>
> **Law: class-scoped draw hooks are vtable-scoped.** The BMPX runtime-image hook gates on `vt == 0x00ADF6A0` (`src/UiSpike.cpp:4868`, `:5020`, `:5098`). Any widget whose class has its own vtable — cSC4WinAuraBar `0x00AB64B8`, cSC4WinTrendBar `0x00ABA430`, cSC4WinRCI `0x00AB8628` — is rejected before the hook sees it, no matter which root list you add. Before proposing "extend the BMPX hook to X", read X's vptr out of the tree dump.

### → `METHOD.md` / the NULL-IS-NOT-EVIDENCE record

> **The RGKID tree dumper has a hard 4-level cap** (`src/UiSpike.cpp:8910/8925/8945/8956`, loops i/j/q/z; the innermost print does not recurse). Across the 759,126-byte live log the label-depth histogram is `{0 dots:53, 1:91, 2:30, 3:1}` and there are **zero** 4-dot labels. A window at depth 5 is not absent from the tree — it is beyond the instrument. The region bubble prints at depth 2, so nothing below its grandchildren is ever visible: the city-name, mayor-name, funds, three population fields and the Mayor Rating bar all exist in the script and all render on screen, and none of them appear in any dump. **Before writing "no child is X ⟹ X is not a window", state which known-visible sibling at the same depth the dump DID print.** In this defect it printed none, and four independent investigations each had to rediscover that the premise was a blind instrument.