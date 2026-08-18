# SUB-FLYOUT LIVE EVIDENCE — the measured ground truth

**Scope.** Everything below is extracted from log files this project already
captured. Nothing here is disassembly, art extraction, or simulation — those
belong to the sibling agents (`SUBFLYOUT-BUILDER.md`, `SUBFLYOUT-ART-VERDICT.md`,
`SUBFLYOUT-CONSTANTS.md`). This file is the LIVE oracle only.

Every row cites **log file + line number + timestamp**. Rows that are derived
rather than read off a line are labelled **HYPOTHESIS**.

Method: `tools\uimap\diff\parse_log.py` (its regexes are transcribed from the
printf sites in `src\UiSpike.cpp`), re-used as a library, plus targeted greps for
the `SUB*` / `SCAL` / `SVT` / `DOBS` / `DSTRIP` / `DPOS` instruments whose grammar
`parse_log.py` does not yet model.

---

## 0. THE CORPUS — and the fact that almost none of it contains the defect

Eleven candidate log files were parsed end to end. **Three** contain any sighting
of `0x8A6E61E0` / `0x8A2CAD8B`. This matters: it is the reason the sub-flyout
never showed up in prior flash work.

| Log file | Version | Lines | Sub-flyout lines | Notes |
|---|---|---|---|---|
| `Plugins\SC4TouchControls.log.bak-dialogtest` | v2.5.5-dialogs | 1 193 | **4** | earliest; DLL logged into the TouchControls log then |
| `Plugins\SC4UIScale.log.bak-presblt` | v2.13.7-barwiden | 203 388 | **438** | 1 open (Zones) |
| `Plugins\SC4UIScale.log.bak-prerings` | v2.14.0-transutil | 240 209 | **202** | 5 opens (Zones / Transport / Utilities ×3) |
| `Plugins\SC4UIScale.log` | v2.33.1-revert | 435 | 0 | current; short boot run |
| `Plugins\SC4UIScale.log.bak-premayordock` | v2.12.7-modetest | 469 978 | 0 | biggest log in the corpus, zero sightings |
| `Plugins\SC4UIScale.log.prev` | — | 279 269 | 0 | |
| `Plugins\SC4UIScale.log.bak-godfix` | — | 39 239 | 0 | god mode only |
| `Plugins\SC4UIScale.log.bak-godmode-final` | — | 55 831 | 0 | god mode only |
| `Plugins\SC4UIScale.log.bak-stock800` | — | 77 | 0 | stock reference, f=1.0 |
| `_tests\last-selective-2x.log` | — | 523 | 0 | |
| `tools\research\_checkpoints\pds-cache\SC4UIScale-snapshot.log` | v2.27.3 | 548 | 0 | |

Both `SC4UIScale` evidence logs ran at **render res 2400x1600, tier 2.00**
(`AutoScale:` line 3 of each file). So every "2x" number below is a real tier-2
measurement, not an inference.

> **Corpus age caveat — read before trusting any POSITION number.** The two rich
> logs are **v2.13.7 and v2.14.0**; shipping is **v2.33.1**. `SUBDOCK` (v2.15.3),
> `SUBCLAIM` (v2.17.0), `SUBSKIP` (v2.22.1), `SUBHEAL` (v2.18.6) and the derived
> tier math (v2.24.0) **did not exist yet**, and `SubDockDX/DY` were 0. The
> **SIZE** facts are architectural and still hold. The **POSITION** facts describe
> pre-dock behaviour and have since been deliberately changed.

---

## 1. THE SUB-FLYOUT WINDOW CENSUS

The whole assembly is **three windows deep and that is all**. Measured from the
1-second full-tree dump, which prints real parent/child nesting by indentation
(`SC4UIScale.log.bak-presblt` L4592–4594, `[23:45:33.342]`):

```
UI     id=0x9A47B417 pos(0,0) size(2400x1600) children=43   <- the 3D VIEW
UI       id=0x8A6E61E0 pos(178,274) size(258x482) children=1   <- CONTAINER
UI         id=0x8A2CAD8B pos(160,50) size(88x382) children=1   <- ITEM STRIP
UI           id=0x2AAB8CC1 pos(0,0) size(0x0) children=0 vis=0  <- tip layer, 0x0
```

### 1a. Distinct window ids ever seen

| id | role | depth below view | parent | ever non-degenerate? | source |
|---|---|---|---|---|---|
| `0x8A6E61E0` | shared sub-flyout **container** | 1 | `0x9A47B417` (3D view) | yes | presblt L4392; prerings L4427 |
| `0x8A2CAD8B` | **item strip** | 2 | `0x8A6E61E0` | yes | presblt L4393; prerings L4428 |
| `0x2AAB8CC1` | tooltip **tip layer** | 3 | `0x8A2CAD8B` | **no — always `0x0`, `vis=0`** | presblt L4594; prerings L4582 |

**There is no fourth id. There are no per-item windows.** This is the single most
important structural fact in this file and it is measured, not inferred: the
strip reports `children=1` and that one child is a 0x0 invisible tip layer.

The visible menu items are **blits into the container's paint buffer**, logged by
the `DSTRIP` instrument (`prerings` L4462–4465, `[23:58:48.318]`):

```
DSTRIP src 88x88 (176,0,264,88) dst 88x88 (0,  0,88, 88) srcTex=352x88
DSTRIP src 88x88 ( 88,0,176,88) dst 88x88 (0, 98,88,186) srcTex=352x88
DSTRIP src 88x88 ( 88,0,176,88) dst 88x88 (0,196,88,284) srcTex=352x88
DSTRIP src 88x88 ( 88,0,176,88) dst 88x88 (0,294,88,382) srcTex=352x88
```

**Consequence for the fix:** no window-tree sweep can ever reach a sub-flyout
item, because items are not windows. Only the container's buffer and the strip's
layout fields `[0xF4]/[0xF8]/[0xFC]` control them.

### 1b. Every open observed, with its menu and 2x rect

`ScaleGodFlyouts`'s `SCAL` line names the open parent flyout, but it is
**rate-capped** and only fired on the first open of each session. Opens 2–5 were
attributed instead by reading the enclosing 1-second tree dump and finding which
`kHookParents` id was `vis=1` — a direct measurement, not a guess.

| # | Log | Line / timestamp | Parent menu | Container rect @2x (abs) | Strip @2x | Items | Attribution source |
|---|---|---|---|---|---|---|---|
| A | presblt | L4433 `[23:45:32.432]` | `0x69923479` **ZONES** | (178,274) **258x482** | 88x382 | 4 | `SCAL` L4398 (explicit) |
| 1 | prerings | L4468 `[23:58:48.334]` | `0x69923479` **ZONES** | (178,274) **258x482** | 88x382 | 4 | `SCAL` L4433 (explicit) |
| 2 | prerings | L39404 `[23:59:25.419]` | `0xC99237A0` **TRANSPORTATION** | (178,374) **258x482** | 88x382 | 4 | tree dump L39451 `[23:59:25.803]`, `0xC99237A0 … vis=1` |
| 3 | prerings | L67738 `[23:59:55.671]` | `0xE992F711` **UTILITIES** | (178,498) **258x384** | 88x284 | 3 | tree dump L67791 `[23:59:56.174]`, `0xE992F711 … vis=1` |
| 4 | prerings | L69662 `[23:59:57.763]` | `0xE992F711` **UTILITIES** | (178,525) **258x678** | 88x578 | 6 | tree dump L69712 `[23:59:58.202]` |
| 5 | prerings | L70642 `[23:59:58.988]` | `0xE992F711` **UTILITIES** | (178,698) **258x384** | 88x284 | 3 | tree dump L70661 `[23:59:59.204]` |
| E1 | dialogtest | L1186 `[22:12:58.230]` | *(not derivable — no tree dump)* | (412,551) **258x384** | — | 3 | `panel` scale event |
| E2 | dialogtest | L1188 `[22:13:08.251]` | *(not derivable)* | (178,355) **258x678** | — | 6 | `panel` scale event |

**Nesting depth.** Every single sighting in the entire corpus is at **depth 1
below the 3D view**, with the same parent `0x9A47B417`, on all six opens across
three different top-level menus. There is **no evidence anywhere in these logs of
a sub-sub-flyout being a separate window**. Selecting a deeper level re-populates
*the same* `0x8A6E61E0` instance (or a freshly allocated one at the same tree
position) — see §1c.

> **HYPOTHESIS (derivable, worth stating):** the reported "nested sub-flyout →
> deeper" behaviour is *not* a deeper window tree. It is the same shared
> container being **destroyed and rebuilt at 1x** for each level. That is why the
> flash reproduces "at EVERY depth" — every depth is a fresh 1x birth of the same
> window. Directly supported by the pointer churn in §1c.

### 1c. Pointer churn — the window is rebuilt, not reused

The `DPROBE` instrument keys on the raw window pointer. Across the five prerings
opens the container/strip pointers **swap and get recycled**:

| Open | container ptr | strip ptr | `NEW` flag present? |
|---|---|---|---|
| 1 `[23:58:48.308]` | `2A91D418` | `2A91D018` | both **NEW** (L4427–4428) |
| 2 `[23:59:25.399]` | `2A91D418` | `2A91D018` | neither (L39382–39383) |
| 3 `[23:59:55.635]` | `2A91D218` | `2A91D418` | neither (L67719–67720) |
| 4 `[23:59:57.743]` | `2A91D418` | `2A91E218` | strip **NEW** (L69636–69637) |
| 5 `[23:59:58.953]` | `2A91E218` | `2A91D018` | neither (L70624–70625) |

`2A91D418` is the container in opens 1/2/4 and the **strip** in open 3. These are
heap addresses being freed and reallocated between menus. This is the measured
form of "code-created, re-populated per menu".

**Instrument consequence:** `DPROBE`'s `NEW` flag is pointer-keyed, so a recycled
address is silently *not* flagged new. Do not treat absence of `NEW` as evidence
that a window persisted.

### 1d. Content-derived size law (fits all 8 opens, zero residual)

| quantity | 1x | 2x |
|---|---|---|
| item cell | 44 x 44 | 88 x 88 |
| item pitch | 49 | 98 |
| strip H (n items) | `49n − 5` | `98n − 10` |
| strip W | 44 | 88 |
| container H | strip H + 50 | strip H + 100 |
| container W | **129** | **258** |
| strip rel pos in container | (80, 25) | (160, 50) |

Check: n=3 → 142 / 284; n=4 → 191 / 382; n=6 → 289 / 578. All three appear in the
logs exactly. Container: 192/241/339 → 384/482/678. All six appear exactly.

**The `258` in the task brief is `129 × 2`, and `129` is a fixed 1x design
constant** — width is the only quantity that never varies with content.

### 1e. Sizes documented elsewhere but ABSENT from every surviving log

`_tests\REGRESSION.md` L370–374 and `src\UiSpike.cpp` L2539 record these from
sessions whose logs have since been rotated away. **Not verifiable from live
evidence today** — flagged so nobody treats them as measured here:

`258x874` (strip 88x774), `258x776`, `258x580`, `258x286`, `258x206` (Freight).
Applying §1d in reverse: 874 → strip 774 → n=8; 580 → strip 480 → n=5;
206 → strip 106 → hmm, n≈1.2 — **that one does not fit the law and should be
re-measured before it is trusted**. (HYPOTHESIS: `258x206` was recorded at a
different tier or is a transcription of a 1x value.)

---

## 2. THE 1x vs 2x PAIRS — the exact before/after the fix must produce

**Every open in the corpus, without exception, was first seen at its 1x size with
`vis=1`.** Six for six. This is the core finding.

### 2a. Container `0x8A6E61E0`

| Open | 1x sighting | 1x rect | 2x sighting | 2x rect | W×2? | H×2? | L×2? | T×2? |
|---|---|---|---|---|---|---|---|---|
| A (presblt, Zones) | L4392 `[23:45:32.408]` | abs(178,274) **129x241** | L4433 `[23:45:32.432]` | abs(178,274) **258x482** | ✅ | ✅ | ❌ held | ❌ held |
| 1 (prerings, Zones) | L4427 `[23:58:48.308]` | abs(178,274) 129x241 | L4468 `[23:58:48.334]` | abs(178,274) 258x482 | ✅ | ✅ | ❌ held | ❌ held |
| 2 (Transport) | L39382 `[23:59:25.399]` | abs(178,374) 129x241 | L39404 `[23:59:25.419]` | abs(178,374) 258x482 | ✅ | ✅ | ❌ held | ❌ held |
| 3 (Utilities) | L67719 `[23:59:55.635]` | abs(178,498) 129x192 | L67738 `[23:59:55.671]` | abs(178,498) 258x384 | ✅ | ✅ | ❌ held | ❌ held |
| 4 (Utilities) | L69636 `[23:59:57.743]` | abs(178,525) 129x339 | L69662 `[23:59:57.763]` | abs(178,525) 258x678 | ✅ | ✅ | ❌ held | ❌ held |
| 5 (Utilities) | L70624 `[23:59:58.953]` | abs(178,698) 129x192 | L70642 `[23:59:58.988]` | abs(178,698) 258x384 | ✅ | ✅ | ❌ held | ❌ held |

**Position is held on purpose, not missed.** `src\UiSpike.cpp` L2554: *"scale the
size, KEEP the game's position (SubDock=0, default)"*. At v2.13.7/v2.14.0
`SubDockDX/DY` were 0, so the dock branch (L5783) never ran. Do not read `❌ held`
as a defect at this version.

The **contrast case** proves what happens if you *do* let the generic sweep move
it — the only `panel` scale events in the corpus, from before `IsSubFlyoutId`
existed (`SC4TouchControls.log.bak-dialogtest`):

```
L1186 [22:12:58.230] panel 0x8A6E61E0 (206,647 129x192) -> (412,551 258x384)
L1188 [22:13:08.251] panel 0x8A6E61E0 ( 89,525 129x339) -> (178,355 258x678)
```

W and H double correctly; **L doubles from the screen origin** (206→412, 89→178)
and **T does neither** (647→551, 525→355 — `ScalePanelRoot`'s clamp/centre
branch). That is exactly the bug `IsSubFlyoutId` was introduced to stop.

### 2b. Item strip `0x8A2CAD8B`

| Open | 1x rect (abs) | 2x rect (abs) | W×2? | H×2? | rel pos ×2? |
|---|---|---|---|---|---|
| A | (258,299) **44x191** | (338,324) **88x382** | ✅ | ✅ | ✅ (80,25)→(160,50) |
| 1 | (258,299) 44x191 | (338,324) 88x382 | ✅ | ✅ | ✅ |
| 2 | (258,399) 44x191 | (338,424) 88x382 | ✅ | ✅ | ✅ |
| 3 | (258,523) 44x142 | (338,548) 88x284 | ✅ | ✅ | ✅ |
| 4 | (258,550) 44x289 | (338,575) 88x578 | ✅ | ✅ | ✅ |
| 5 | (258,723) 44x142 | (338,748) 88x284 | ✅ | ✅ | ✅ |

Unlike the container, the strip's **relative** position doubles (it is a child, so
`ScaleSubtree` scales it), which is why its absolute x moves 258→338 while the
container's stays put.

### 2c. The paint BUFFER — the quantity that doubles ONE FRAME LATE

This is the flash itself. `DOBS` prints the window rect and the source buffer's
own dimensions in the same line.

| Open | first Plot after open | window rect | **buffer** | next Plot | buffer |
|---|---|---|---|---|---|
| A | presblt L4404–4405 `[23:45:32.412]` | win=(178,274,436,756) = **258x482** | **129x241 (1x)** | L4444 `[23:45:32.434]` | **258x482 (2x)** |
| 1 | prerings L4440 `[23:58:48.315]` | 258x482 | **129x241 (1x)** | L4479 `[23:58:48.340]` | **258x482 (2x)** |
| 2 | prerings L39387 `[23:59:25.402]` | 258x482 | **129x241 (1x)** | *(DOBS cap reached)* | — |
| 3 | prerings L67724 `[23:59:55.636]` | 258x384 | **129x192 (1x)** | *(capped)* | — |
| 4 | prerings L69641 `[23:59:57.744]` | 258x678 | **129x339 (1x)** | *(capped)* | — |
| 5 | prerings L70629 `[23:59:58.953]` | 258x384 | **129x192 (1x)** | *(capped)* | — |

**A 2x window painted from a 1x buffer.** That is what the user sees. The window
geometry is already right; the pixels are not.

Corroborating: on open A the buffer's blit vtable slot changes between the two
Plots — `blt0x74=00826AD0` (stock, L4406) → `blt0x74=6E6C2D60` (our
`gForceRecreate` hook, L4428). The recreate lands on the **second** Plot.

### 2d. Quantities that DOUBLE, and quantities that DO NOT

**Doubles (measured in-log):**

| quantity | 1x → 2x | evidence |
|---|---|---|
| container W | 129 → 258 | §2a, 6/6 opens |
| container H | 192/241/339 → 384/482/678 | §2a |
| strip W | 44 → 88 | §2b |
| strip H | 142/191/289 → 284/382/578 | §2b |
| strip rel pos | (80,25) → (160,50) | §2b |
| paint buffer | = container, **one frame late** | §2c |
| strip item field `[0xF4]` | 44 → **88** | `DSCROLL` prerings L67767-region `[23:59:55.966]` |
| strip item field `[0xF8]` | 44 → **88** | same line |
| strip item pitch `[0xFC]` | 5 → **10** | same line |
| item blit dst cell | 44x44 → **88x88**, pitch 49 → 98 | `DSTRIP`, §1a |

(The 1x values of `[0xF4]/[0xF8]` are not printed in these logs; they are read
off the source's own heal guard `f4 >= 40 && f4 <= 50` at `UiSpike.cpp` L5971 and
the ×2 arithmetic. **HYPOTHESIS-adjacent**: the 88 is measured, the 44 is
inferred from the guard band.)

**Never doubles anywhere in the corpus:**

| quantity | value | is that correct? |
|---|---|---|
| container abs L,T | held at game's value | **YES — deliberate.** `SubDock=0` at this version; `IsSubFlyoutId` skips the sweep on purpose (`UiSpike.cpp` L4269). |
| tip layer `0x2AAB8CC1` | always `0x0`, `vis=0` | **YES — nothing to scale.** |
| **item source atlas `srcTex`** | **176x44 on some menus** | **NO — this is a real mismatch, see §2e.** |
| container claim field `[0xE0]` | no `SUBCLAIM` line exists in any log | **UNKNOWN.** `SUBCLAIM` is a v2.17.0 instrument; the corpus predates it. `REGRESSION.md` L271/304 documents the intended `53 → 106`, but **it is not verifiable from live evidence.** |

### 2e. The one quantity that genuinely fails to double: the item ATLAS

`DSTRIP` prints the source texture's real dimensions. Across the corpus:

| `srcTex` | count (prerings) | count (presblt) | when |
|---|---|---|---|
| `352x88` (2x, 4 cells of 88) | 1 145 | 3 192 | Zones, Transportation |
| **`176x44` (1x, 4 cells of 44)** | **119** | **0** | **Utilities only**, from `[23:59:55.966]` (prerings L67767) onward |

The blit asks for an **88x88** source rect at `(88,0,176,88)` from a texture that
is only **176x44** — the read is out of bounds in both axes. The strip fields were
doubled (§2d) but the art behind that menu was not.

This is *live confirmation* of the class of defect `REGRESSION.md` L288–293 calls
"an un-overridden 176x44 icon". **Interpretation is the art agent's call** — I am
only reporting that the 1x/2x atlas pair is directly observable, is
**menu-specific**, and that Utilities is the menu that exhibits it in this corpus.

---

## 3. TIMING — how long the flash lasts

### 3a. Frame rate (needed to convert ms into frames)

The `DPOS` instrument carries the game's own frame counter:

| timestamp | frame | source |
|---|---|---|
| `[23:58:48.316]` | 1 | prerings |
| `[23:59:25.403]` | 2 032 | prerings |
| `[23:59:55.637]` | 3 672 | prerings |
| `[23:59:57.746]` | 3 787 | prerings |
| `[23:59:58.953]` | 3 853 | prerings |

3 852 frames over 70.637 s = **54.5 fps → 18.34 ms per frame.**

### 3b. Per-open latency

`DPROBE` is **change-triggered** (`UiSpike.cpp` L5276–5286: logs a window only
when its pos/size/vis differs from the previous sweep). So a 1x `DPROBE` line
means "this geometry is new *this sweep*", and the next line means "we changed
it". The gap is one sweep period.

| Open | 1x seen | scaled (2x seen) | Δ | frames @18.34ms | buffer still 1x until | visible-flash Δ |
|---|---|---|---|---|---|---|
| A | `23:45:32.408` | `23:45:32.432` | **24 ms** | 1.3 | `23:45:32.434` | **22 ms ≈ 1.2 frames** |
| 1 | `23:58:48.308` | `23:58:48.334` | **26 ms** | 1.4 | `23:58:48.340` | **25 ms ≈ 1.4 frames** |
| 2 | `23:59:25.399` | `23:59:25.419` | **20 ms** | 1.1 | *(DOBS capped)* | ≥20 ms |
| 3 | `23:59:55.635` | `23:59:55.671` | **36 ms** | 2.0 | *(capped)* | ≥36 ms |
| 4 | `23:59:57.743` | `23:59:57.763` | **20 ms** | 1.1 | *(capped)* | ≥20 ms |
| 5 | `23:59:58.953` | `23:59:58.988` | **35 ms** | 1.9 | *(capped)* | ≥35 ms |

**Range 20–36 ms, i.e. ONE TO TWO RENDERED FRAMES.** Median ≈25 ms.

That is precisely a "flash": long enough to be seen, too short to look like a
layout error. It matches the user's description exactly.

### 3c. What bounds the *creation* time

The full-tree dump runs once per second and is the only instrument that could
prove when the window was born. For open 3 the previous dump ended
`[23:59:55.154]` (prerings L67718, `847 windows`) **without** `0x8A6E61E0`; the
first 1x `DPROBE` is `[23:59:55.635]`. So creation is bounded to a 481 ms window
by the dump, and to **≤ one sweep period (~20–36 ms)** by `DPROBE`'s
change-trigger.

> **HYPOTHESIS:** the true 1x lifetime is one sweep period, not more. The sweep
> catches the window on the very next tick after creation because `DPROBE` and
> the scale run in the *same* pass — note that the 1x `DPROBE` line and the
> `SUBHOOK` line reporting the already-2x size share a timestamp to the
> millisecond on all six opens (e.g. presblt L4392 and L4394, both
> `[23:45:32.408]`). The window rect is fixed within ~1 ms of being observed.
> **The latency is not in the sweep. It is in the BUFFER**, which only catches up
> on the following Plot (§2c). Fixing sweep frequency cannot fix this.

---

## 4. WHICH CODE PATH TOUCHES THEM

| Window | `ScalePanelsUnder` (generic sweep) | `ScaleMenuFlyouts` | `ScaleGodFlyouts` sub-flyout block | Net |
|---|---|---|---|---|
| `0x8A6E61E0` container | **EXPLICITLY SKIPPED** — `UiSpike.cpp` L4269 `if (IsSubFlyoutId(...)) continue;` | **no** — it is a child of the 3D view `0x9A47B417`, not of `kGZWin_MenuContainer` | **YES** — L5708–5721, `ScaleSubtree(sub, f, 0, &n, false)` | **covered, but only via ScaleGodFlyouts** |
| `0x8A2CAD8B` strip | no (never reached; parent skipped) | no | yes, as a descendant of `ScaleSubtree` | covered |
| `0x2AAB8CC1` tip layer | no | no | reached but `0x0` → no-op | n/a |
| **item cells** (blits) | **impossible — not windows** | impossible | not by geometry; only via the `SlotThunk2` field doubling | **only the draw hooks** |

### 4a. The gate that causes the flash

`UiSpike.cpp` L5711:

```cpp
if (!sub || sub->GetW() <= 0 || sub->GetH() <= 0 || !sub->IsVisible())
{ ... continue; }
```

**The sub-flyout is scaled ONLY while it is already visible.** There is no
pre-scale-while-hidden path for it, and there cannot be a naive one, because the
window does not exist until the menu opens (§1c: it is allocated per menu).

This is the *same* visibility-gate mechanism documented at `UiSpike.cpp`
L2619–2632 for the mode-transition flash — but the proven cure there
(pre-scale while hidden, `kAlwaysScaleCityIds`) **is not applicable here**, because
that cure requires the window to exist before it is shown. That is why this one
survived task #50.

### 4b. Windows that appear in dumps but never in any "scaled" line

You asked specifically for these. The answer:

- **`0x8A6E61E0` and `0x8A2CAD8B` produce NO scale-event line in any modern log.**
  `ScaleGodFlyouts` calls `ScaleSubtree` directly and emits **no** `panel … -> …`
  line, no `dialog … scaled` line, no `menu flyout … scaled` line. The parser
  found **0 scale events** for these ids across all 11 files.
  The only `panel` lines that ever named the container are the two v2.5.5
  `dialogtest` lines from *before* the skip existed (§2a).
- Practical effect: the two most-used diagnostic greps on this project
  (`grep "panel 0x"` and `grep "scaled"`) are **blind to the entire sub-flyout
  assembly.** Anyone auditing "what did we scale this session" from the log gets
  a list that silently excludes it.
- `SUBHOOK` is the only line that reports the container's size at all, and it
  fires **only** when `gClaimScale > 1` **and** a `kHookParents` menu is open
  (L5926). A sub-flyout under any *other* menu (U-Drive-It, Earned Cars, …) is
  scaled by `ScaleSubtree` and then logs **nothing at all** except a capped
  `SUBSKIP`.

---

## 5. THE INSTRUMENT GAP — exactly what you were blind to

`FLASHSET` lives inside the top-level panel loop of `ScalePanelsUnder`
(`UiSpike.cpp` L4321–4334):

```cpp
const bool wasOnScreen = IsOnScreen(p.win);
const int n = ScalePanelRoot(p.win, screenW, screenH, f);
if (n > 0) { … if (wasOnScreen) NoteFlashCandidate(...); }
```

**`IsSubFlyoutId` returns `continue` at L4269 — 52 lines BEFORE that code.**

So:

| Window | Could `FLASHSET` ever have reported it? | Why not |
|---|---|---|
| `0x8A6E61E0` container | **NO** | skipped at L4269, never reaches L4321 |
| `0x8A2CAD8B` strip | **NO** | never a top-level panel; only ever a `ScaleSubtree` descendant, and `FLASHSET` only wraps roots |
| `0x2AAB8CC1` tip layer | **NO** | same |
| item cells | **NO** | not windows |
| **every mayor-only flyout** (`IsMayorOnlyFlyoutId`, L4262) | **NO** | skipped 59 lines earlier — Zones/Transport/Utilities/Civic |
| **every god tool flyout** (`IsGodToolFlyoutId`, L4252) | **NO** | skipped 69 lines earlier |
| everything in `kNeverScaleIds` (L4244) | NO | by design |

**The blind spot is not a bug in `FLASHSET` — it is the exact complement of the
skip list.** `FLASHSET` measures the *generic sweep's* flash. Every window that
was pulled out of the generic sweep into a specialist path
(`ScaleGodFlyouts` / mayor dock / sub-flyout) became invisible to it *at the
moment it was pulled out*.

Confirmation from the only log that has `FLASHSET` at all
(`SC4UIScale.log`, v2.33.1, 8 lines, L86–231): candidates #1–#8 are
`0x09EBE9EE`, `0x6A91DC15`, `0x6A91DC16`, `0xEA8CAD19`, `0x6A91DC14`,
`0xAA32BCE6`, `0xEA8CAD14`, `0x0987B48F` — region panels and the Data Views
container. **Not one flyout, not one sub-flyout.** The instrument reported a
clean-looking finite list precisely because it could not see the family that
still flashes.

### 5a. Second gap: the only instrument that DID catch it is disarmed

`DPROBE` is the sole instrument that ever recorded the 1x state, and
`Plugins\SC4UIScale.ini` `[Probe]` currently reads:

```
Enabled=0
BandL=400  BandR=2100  BandT=1000  BandB=1460
Max=120
```

Three separate ways it can miss the sub-flyout even when re-armed:

1. **`Enabled=0`** — off by default; the ini comment says *"DISARMED again
   2026-07-29"*.
2. **Band** — `UiSpike.cpp` L5284 requires `ax > BandL && ax < BandR && ay > BandT
   && ay < BandB`. The container sits at **abs y = 274…698**; the current band
   starts at **y=1000**. **Even with `Enabled=1`, today's band would not have
   logged a single one of the six opens.**
3. **`inBand` requires `now.vis == 1`** (same line) — a hidden window is never
   probed, so `DPROBE` can never prove a pre-scale worked.

To reproduce this evidence you need `Enabled=1`, `BandT≈200`, `BandB≈1200`,
`BandL≈100`, `BandR≈700`, `Max` ≥ 120.

### 5b. Third gap: every SUB* instrument is rate-capped

| Instrument | Cap | Source |
|---|---|---|
| `SCAL` | fires only on the first match per session | why opens 2–5 have no parent line |
| `SUBSKIP` | `skipLog < 10` | `UiSpike.cpp` L5763 |
| `SUBHEAL` | `healLog < 20` | L5975 |
| `SVT` | `vtLogged < 2` | L6051 |
| `DOBS` | counter `n=1…7` observed then silence | why only opens A and 1 have a *second* buffer measurement |
| `DPROBE` | `logged < gProbeMax` per sweep | L5286 |

The caps are why §2c can only prove the buffer catch-up on 2 of 6 opens. The 1x
buffer is proven on **all six**; the recovery timestamp on two.

---

## 6. WHAT THIS CORPUS CANNOT TELL YOU

State plainly, so no one over-reads this file:

1. **No 1.5x or 3x sighting exists.** Every number here is tier 2.00 at
   2400x1600. The §1d law is stated in ×2 form because that is all that was
   measured; its 1.5x rounding behaviour is untested (and `parse_log.py`'s own
   docstring warns that 1.5x is where the two size laws diverge).
2. **No `SUBDOCK`, `SUBCLAIM`, `SUBSKIP` or `SUBHEAL` line exists anywhere in the
   corpus.** Those instruments postdate both evidence logs. The v2.16.0 placement
   law (`nativeY = buttonCentreY − ringBltY − 29`) is **documented but not
   log-verified here**; the `ringBltY=94` value for Zones *is* corroborated
   (`SCAL … ringY` does not exist, but the container's `DCBL` ring blit lands at
   `dst (0,94,80,147)`, presblt L4421 `[23:45:32.412]` — consistent with 94).
3. **No sighting under Civic `0x699306ED`, Landscape `0x49923239`, U-Drive-It
   `0x8BB27C12`, or Signs `0xAB954023`.** Four of the seven `kHookParents` are
   entirely unobserved. If the fix is validated only against Zones/Transport/
   Utilities it is validated against 3 of 7.
4. **No stock (f=1.0) capture of a sub-flyout exists.** `bak-stock800` is 77
   lines and contains none. So the "1x" column throughout is *our DLL observing
   the window before it scaled it*, which is the right comparison for a flash but
   is **not** a vanilla reference.
5. **`0x8A6E61E0` never appears in `bak-premayordock` (469 978 lines) or
   `.log.prev` (279 269 lines).** Absence there is absence of the *user opening a
   plop sub-menu*, not absence of the defect.

---

## 7. TARGETS THE FIX MUST HIT (summary card)

For a Zones 4-item sub-menu at tier 2.00, first frame after the menu opens:

| thing | must be | not |
|---|---|---|
| container `0x8A6E61E0` | 258 x 482 | 129 x 241 |
| container paint buffer | 258 x 482 **on the FIRST Plot** | 129x241 for 1–2 frames |
| strip `0x8A2CAD8B` | 88 x 382 at rel (160,50) | 44 x 191 at rel (80,25) |
| strip fields `[0xF4]/[0xF8]/[0xFC]` | 88 / 88 / 10 | 44 / 44 / 5 |
| item blit dst | 88x88, pitch 98 | 44x44, pitch 49 |
| item source atlas | 352 x 88 | **176 x 44** (Utilities today) |
| container abs pos | whatever the dock law says — **do not double from origin** | (356,548) |

Generalise via §1d for other item counts. The acceptance criterion that actually
matters: **`DOBS`'s `srcBuf` must equal the window rect on Plot #1, not Plot #2.**

---

*Evidence agent. Sources: `Plugins\SC4UIScale.log*` (all), `Plugins\SC4TouchControls.log.bak-dialogtest`,
`_tests\last-selective-2x.log`, `tools\research\_checkpoints\pds-cache\SC4UIScale-snapshot.log`,
`src\UiSpike.cpp` (read-only), `tools\uimap\diff\parse_log.py` (re-used),
`_tests\REGRESSION.md`, `tools\research\MAYOR-MODE.md`. Nothing was launched, modified, or deleted.*
