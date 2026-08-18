# BLIT BEHAVIOUR — what 2x art actually does to each drawing class

## ⛔ A BLIT HAS **THREE** NUMBERS, NOT TWO

> **SOURCE** (the bitmap) · **CROP** (`imagerect=`) · **DESTINATION** (the
> window). **Scaling any two of them is not a partial fix, it is a new defect.**

This is the durable form of the rule and it belongs above everything else on
this page, because the rest of this file is about the SOURCE↔DESTINATION
relationship alone — which is only two thirds of the model. `imagerect=` is a
**source rect in bitmap pixels, corner form** (`SC4-UI-ENGINE.md` §3.3), it is
present on 839 controls, and it does **not** scale itself.

It was already written down when #154 broke it anyway: v2.97.0 scaled a mod
dialog's windows and its bitmaps and left all 24 `imagerect` crops at 1×, so
each row stripe painted 285px of a 428px window. **The rule was not disobeyed —
the code path never asked the question**, because `build_dialog_static.py`
decides "did the art scale?" from the *stock* upscale store, and art the MOD
supplies is therefore always classified `left1x` there. So the second half of
the law is:

> When you check one of the three, check whether your test for "did this scale?"
> can actually SEE every supplier of that thing.

**And the sizing of the source itself is a fourth question with its own answer**
— the sheet's **ROLE** decides its rule (strip → `width/N`, 9-slice → `/3`,
tiled → *no snap at all*). See `SC4-UI-ENGINE.md` §4.6c; do not re-derive it here.

---

**LAW 35.** A control's draw slot is one of three things, and guessing wrong
makes the artefact *worse*: that is how the region rating bar ended up drawn
twice (v2.37.1). Before shipping art for any code-painted control, find its row
here — or measure it (§ How to classify) and add one.

| behaviour | what it means | 2x art does | 1x art in a 2x window does |
|---|---|---|---|
| **dst-follows-src** | the destination rect is computed from the ART | draws 2x — correct | draws 1x in the top-left corner |
| **stretch** | source and destination are independent | scales to fit | stretches, usually fine |
| **src-follows-dst** | the SOURCE rect is computed from the WINDOW | **TILES** — the artefact | under-fills |

---

## The table

| class / path | clsid | draw (slot 88) | behaviour | evidence |
|---|---|---|---|---|
| `GZWinBMP` plain | — | `0x009BC325` | **dst-follows-src** | disasm: `dst = {areaL, areaT, areaL+srcW, areaT+srcH}` — the window rect is never read. `task55-47-runtimeimg.md:35-46`; mirrored in `UiSpike.cpp:4859-4879` |
| U-Drive-It gauge | `0xCBCBF1E0` | `0x00762830` | **dst-follows-src** | **emulated 2026-07-31**, both legs: window 58x62→116x124 leaves dst `(0,0,3,62)` *unchanged*; art 58x62→116x124 makes dst `(0,0,7,124)`. `emu_gauge.py` |
| `cSC4WinAuraBar` | `0x...` | `0x00797CC0` | **src-follows-dst** | v2.37.1, the region rating bar: under-sized art tiled inside a correctly-sized window. Cure was to ship art at the WINDOW's size |
| 9-slice EDGE (`blttype=edge`, `edgeimage=yes`) | — | see ⚠ below | **stretch** | `cell = img->W()/3`; a 2x sheet thickens the frame, it cannot clip to a quadrant. Used by the alert borders and `{46a006b0,46a006a4}` |

⚠ **THE `/3` RULE IS CONFIRMED; THE VA ATTRIBUTED TO IT IS NOT.** This row used
to name `NineSlice 0x008D9550`, but `REGRESSION.md` records that `0x008D9550`
has **exactly one caller image-wide** — `0x00794198`, inside
`cSC4WinAlertBorder`'s slot-88 draw `0x00794100`. A script attribute on a
`GZWinGen`/`GZWinBMP` therefore cannot be reaching it by that path, and one of
the two records is wrong. The **cell rule itself** is measured independently and
stands: at 1.5x a 9-slice sheet sized off `/3` renders clean and one sized off
`LCM{3,4}` leaves the corner arc short (#157, 418 px → 4 px control, 0 at 2x).
Do not re-assert the VA without disassembling it; do rely on `img->W()/3`.

> ✅ **VA RE-ASSERTED 2026-08-18 — the disassembly this block asked for already
> existed.** Both records were right and neither described the other's window.
> **There are two 9-slice blitters and three drawers, and the drawer always
> performs the `/3` itself:**
>
> | drawer (its own slot-88 draw) | divides | then calls |
> |---|---|---|
> | `cSC4WinAlertBorder` `0x00794100` | `img->W()/3`, `img->H()/3` | `0x008D9550` (one caller image-wide) |
> | **`GZWinBMP` `0x009BC325`, EDGE branch** — entered on flag bit 8 of the holder at `[this+0xD8]` via its `vt[10]`. **This is the `blttype=edge` / `edgeimage=yes` row's real drawer** | the **source rect** by 3 (`idiv` at `0x9BC414`, `0x9BC422`) | `0x008D8800` |
> | `GZWinBtn` `0x009B05E0` (nine-slice branch) | `srcW/3`, `srcH/3` (`0x009B05E9`, `0x009B0602`) | `0x008D8800` |
>
> Neither blitter contains a divide — each receives a cell its caller already
> cut. Sources: `src\UiSpike.cpp` BMPX comment block (2026-07-30 disasm; the
> shipped `edgeMode` skip depends on it, #47 user-confirmed) · `MAYOR-MODE.md`'s
> 2026-07-29 callee list for `0x9BC325`, which contains `008d8800` and **not**
> `008d9550` · `_incoming\sdkgaps-06.md` §4A.6 · `probe_btn_nineslice.py:25-42`.
> `img->W()/3` remains correct for this row because a sheet with no `imagerect`
> has `src` = its natural rect. Full write-up and the one residual open question
> in `_tests\REGRESSION.md` §"RESOLVED 2026-08-18 — three addresses, three
> different JOBS".
| `blttype=tiled` | — | (script attribute, not a class) | **src-follows-dst — TILES** | **observed live 2026-07-31**: the CAM startup splash root `8aa9aa14` is `blttype=tiled` with a 768x600 background; doubling the root to 1536x1200 tiled it **exactly 2x2**. Cured by shipping the art at 1536x1200 |
| `GZWinBtn` | — | `0x009B167D` | *not classified* | distinct address confirmed (TRIAGE §4) but the blit path has NOT been run |

⚠ **`blttype=` is a per-node SCRIPT attribute and it overrides class intuition.**
The splash root is a plain `GZWinGen`; nothing about the class predicts tiling.
**Read the node's `blttype=` before reasoning from its clsid** — `tiled` and
`edge` behave completely differently from the default path, and `tiled` is the
one that produces the duplicated-image artefact.

⚠ **Only the first two rows and the 9-slice are measured end-to-end.** The
`cSC4WinAuraBar` row is inferred from a shipped fix that worked, which is strong
but is not the same as running its draw. `GZWinBtn` is unclassified — do not
assume it from its neighbours.

**Population:** 26 distinct window-class vtables have been observed live across
our session logs. This table covers a handful of them. Absence from this table
is *not* evidence of any behaviour.

⛔ **AND THE CLASS IS ONLY HALF THE QUESTION — THERE ARE THREE CHANNELS OUT OF A
BUFFER, NOT ONE** (added 2026-08-15, #149). Classifying a control's draw slot
tells you what the draw *computes*; it does not tell you whether your hook can
*see* it. A window that owns a **private buffer** (slot 192 `0x0079BDC0` calls
`PrivateBuffer(true)` on the menu strip) has its item draws land in that buffer,
which then reaches the screen by **slot 20 (`+0x50`)**, the present path
`0x0099BA3E`, or by **`PlotPresent` `0x0099C498`** — neither of which routes
through **slot 29 `Blt`**, the only slot most probes hook. There are also **two**
buffer classes, `0x00AC1400` and `0x00ADB418`. Five instruments all reported
"every blit corrected" against a screen that disagreed, and this was why. See
`SC4-UI-ENGINE.md` §2.3.

---

## Why this decides the My Sims ¼-size portraits (#3)

The portrait cells are `GZWinBMP` with **no `image=`** — pixels supplied at
runtime — inside windows the sweep doubles. `GZWinBMP` is **dst-follows-src**,
so the destination is sized from whatever bitmap the runtime hands over. A 2x
window plus a 1x runtime bitmap draws 1x in the corner. **That is the reported
symptom, and it follows from the table rather than from a theory.**

It also explains why shipping 2x art cannot fix it: there is no art TGI to
ship. The lever has to change either the bitmap the runtime supplies or the
rect the draw computes.

⚠ Do not confuse this with the *other* mechanism in the same family: the
pbuff clip (`[win+0x6c]` is the window's own pixel buffer, allocated at FIRST
PAINT from the then-current size — `task55-47-runtimeimg.md:449-453`). Both
produce a small top-left image. They are distinguished by the `BMPX draw` line:
`win 72x82 -> dst 72x82` means the draw was right and the buffer clipped it;
`win 36x41` means the window was still 1x when it drew.

---

## How to classify a class (offline, ~2 minutes)

`tools\flyout-sim\emu_gauge.py` runs a real slot-88 draw under Unicorn with a
synthetic object and captures the `(src, dst)` pair the control feeds its draw
context. Two runs classify it:

```
python emu_gauge.py --draw=<VA> --win=<2x w,h>              # A: 1x art, 2x window
python emu_gauge.py --draw=<VA> --img=<2x w,h> --win=<2x w,h>   # B: 2x art, 2x window
```

- `dst` identical in A and B, sized from the art  → **dst-follows-src**
- `dst` tracks the WINDOW in A                    → **src-follows-dst** or stretch;
  compare `src` to separate them (src changing with the window = src-follows-dst)

⚠ **The field map in `emu_gauge.py` is class `0xCBCBF1E0`'s.** A class that
keeps its image pointer or frame count at other offsets needs its own map first,
or the run is meaningless. **A run that captures no draw-context call is a NULL,
not a verdict** — state the positive control before believing it.
