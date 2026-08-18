# CHECKPOINT — sub-flyout LIVE EVIDENCE (offline log mining)

**Agent:** live-evidence (one of three parallel sub-flyout agents; siblings own
the exe/builder + constants and the art verdict — I touched neither).
**Date:** 2026-07-30. **Status:** COMPLETE.
**Deliverable:** `tools\uimap\SUBFLYOUT-LIVE-EVIDENCE.md` — read that for the
measured tables. This file is the short recall card.

## What was done

Parsed **11 log files** end to end with `tools\uimap\diff\parse_log.py` re-used
as a library (not re-implemented), plus targeted greps for the `SUB*` / `SCAL` /
`SVT` / `DOBS` / `DSTRIP` / `DPOS` instruments its grammar does not model.
Nothing was launched, modified or deleted. SimCity 4 was never touched.

## The five findings that change the fix

1. **The assembly is THREE windows and no more.** Container `0x8A6E61E0` →
   strip `0x8A2CAD8B` → tip layer `0x2AAB8CC1` (always `0x0`, `vis=0`).
   **The menu items are NOT windows** — they are `DSTRIP` blits into the
   container's paint buffer. No window sweep can ever reach them.

2. **Every open is born 1x, 6/6 opens, 3 different menus.** Container
   `129 x {192,241,339}` → `258 x {384,482,678}`; strip `44 x {142,191,289}` →
   `88 x {284,382,578}`. Size law fits all with zero residual:
   strip H = `49n − 5` (1x) / `98n − 10` (2x); container H = strip H + 50/+100;
   container W = 129/258 fixed.

3. **The flash is the BUFFER, not the sweep.** The window rect is corrected
   within ~1 ms of being observed (the 1x `DPROBE` and the already-2x `SUBHOOK`
   share a timestamp on all six opens). But `DOBS` shows the *paint buffer* still
   at 1x on the first Plot afterwards — a 2x window filled from a 1x buffer for
   **20–36 ms = 1–2 frames** at the measured 54.5 fps. **Raising sweep frequency
   cannot fix this.**

4. **`FLASHSET` was structurally incapable of reporting any of it.** It sits at
   `UiSpike.cpp` L4321, and `IsSubFlyoutId` does `continue` at **L4269** — 52
   lines earlier. Same for `IsMayorOnlyFlyoutId` (L4262) and `IsGodToolFlyoutId`
   (L4252). The blind spot is the exact complement of the skip list: every window
   moved from the generic sweep to a specialist path left the instrument's reach
   at that moment. Confirmed by the only log with `FLASHSET` lines
   (`SC4UIScale.log` v2.33.1, 8 candidates — region panels + Data Views, zero
   flyouts).

5. **Sub-flyouts emit NO scale-event line at all.** `ScaleGodFlyouts` calls
   `ScaleSubtree` directly with no `panel … -> …` log. So `grep "panel 0x"` and
   `grep "scaled"` — the two standard audit greps — are blind to the whole
   assembly. The only `panel 0x8A6E61E0` lines in the corpus are two v2.5.5 lines
   from *before* the skip existed, and they show the old bug (L doubled from the
   screen origin, T clamped).

## Bonus (hand to the ART agent, do not act on it here)

`DSTRIP` prints the real source-texture size. **`srcTex=176x44` (1x) appears 119
times in `bak-prerings`, exclusively on the UTILITIES menu**, while Zones and
Transportation always show `352x88` (2x). The blit reads an 88x88 rect from a
176x44 texture — out of bounds both axes. Menu-specific 1x atlas, directly
observable. `presblt` has zero 176x44.

## Corpus map (where the evidence is, and is not)

| File | Sub-flyout lines |
|---|---|
| `Plugins\SC4UIScale.log.bak-prerings` (v2.14.0) | **202** — 5 opens: Zones, Transport, Utilities ×3 |
| `Plugins\SC4UIScale.log.bak-presblt` (v2.13.7) | **438** — 1 open: Zones |
| `Plugins\SC4TouchControls.log.bak-dialogtest` (v2.5.5) | **4** — the only `panel` scale events |
| all 8 others (incl. `bak-premayordock` 469 978 lines, `.log.prev` 279 269) | **0** |

## Traps for whoever picks this up

- **The corpus is v2.13.7/v2.14.0; shipping is v2.33.1.** SIZE facts are
  architectural and hold. **POSITION facts predate `SUBDOCK`** (v2.15.3) and
  describe deliberate pre-dock behaviour — do not read "position didn't double"
  as a defect.
- **No `SUBDOCK` / `SUBCLAIM` / `SUBSKIP` / `SUBHEAL` line exists in any log.**
  Those instruments postdate the evidence. The v2.16.0 placement law and the
  `[0xE0] 53 → 106` claim are **documented in REGRESSION.md but NOT
  log-verified**.
- **`DPROBE` is the only instrument that ever caught the 1x state, and it is
  disarmed AND mis-aimed.** `SC4UIScale.ini [Probe] Enabled=0`, and the band is
  `BandT=1000..BandB=1460` while the container lives at **abs y 274…698** — even
  re-armed, today's band logs nothing. To reproduce: `Enabled=1`, `BandL≈100`,
  `BandR≈700`, `BandT≈200`, `BandB≈1200`, `Max≥120`.
- **`DPROBE`'s `NEW` flag is pointer-keyed and heap addresses get recycled**
  between menus (proven: `2A91D418` is the container in opens 1/2/4 and the
  *strip* in open 3). Absence of `NEW` ≠ the window persisted.
- **Every `SUB*` instrument is rate-capped** (`SCAL` first-match, `SUBSKIP` 10,
  `SUBHEAL` 20, `SVT` 2, `DOBS` ~7, `DPROBE` `Max`/sweep). That is why the 1x
  buffer is proven on 6/6 opens but its recovery timestamp only on 2/6.
- **Coverage is 3 of 7 `kHookParents`.** Civic `0x699306ED`, Landscape
  `0x49923239`, U-Drive-It `0x8BB27C12` and Signs `0xAB954023` are entirely
  unobserved in every surviving log.
- **`258x206` (listed in REGRESSION.md L373 as a seen size) does not fit the
  measured size law** (implies n≈1.2). Re-measure before trusting it.
- **No f=1.0 sub-flyout capture exists** anywhere. The "1x" column throughout is
  our own DLL observing the window *before* it scaled it — right for a flash
  analysis, but it is not a vanilla reference.

## Acceptance criterion the fix must meet

`DOBS`'s `srcBuf` must equal the window rect on **Plot #1**, not Plot #2.
Everything else (window rect, strip rect, `[0xF4]/[0xF8]/[0xFC]` = 88/88/10,
blit dst 88x88 pitch 98) is already correct by the second frame today.
