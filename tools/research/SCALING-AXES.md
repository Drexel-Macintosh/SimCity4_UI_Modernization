# SCALING AXES — the catalog of everything we scale, and the two-knob design

**Status:** durable reference + settled design brief. Task #97.
**Created:** 2026-08-03. **Repo root:** `<repo root>\`
**Decision of record (user, 2026-08-03):** ship **TWO** knobs — **UI scale** (1.5 / 2 / 3) and **U-Drive-It bubble scale**. **UI and TEXT are locked 1:1.** There is no text knob and there will not be one. UI scaling above 3x is explicitly deferred (§7).

---

## Citation audit — **EVERY `file:line` IN THIS DOCUMENT IS STALE. THE SYMBOL NAME IS THE ANCHOR; THE NUMBER IS NOT.**

**Measured, not suspected.** Of the 63 table rows in this file that pair a
backticked **symbol** with a `src\...:NNN` **citation**, the symbol is present
within ±20 lines of the cited line in **5** cases and **absent in 58**.
`src\UiSpike.cpp` was ~8.9k lines when this document was written (2026-08-03),
17,113 lines when that rot was first measured, and **21,831 lines on
2026-08-30**; `ScaleTier.cpp` has gone 1,895 → **4,619** and `CodePatches.cpp`
4,065 → **8,469** over the same stretch. The four spot checks below were once
repaired *to new line numbers* — **and every one of those repairs has rotted
since.** That is why the right-hand column is now a grep and never a number:

| This file says | How to resolve it |
|---|---|
| `Settings::spikeScaleFactor` — `src\Settings.h:55` | `src\Settings.h` (grep `float spikeScaleFactor`) |
| `gTierF` — `src\UiSpike.cpp:145` | `src\UiSpike.cpp` (grep `float gTierF =`; the §0 trap is the comment block immediately above it) |
| `RoundHalfUp` — `src\UiSpike.cpp:151-154` | `src\UiSpike.cpp` (grep `inline int32_t RoundHalfUp`) |
| `ScaleRound` — `src\UiSpike.cpp:3823-3826` | `src\UiSpike.cpp` (grep `inline int32_t ScaleRound`) |
| `ScaleTier::Decide` — `src\ScaleTier.cpp:31-36` (`kPackages`) | `src\ScaleTier.cpp` (grep `kPackages[] =`, then `float Decide(`); called from `src\SC4UIScaleDllDirector.cpp` (grep `ScaleTier::Decide`) |

**Law: a `file:line` that points at the wrong thing is worse than no citation** —
it reads as measured, and this project's own law is that an inference written
down as a measurement kills your next seven candidates. **Treat every line
number below as UNVERIFIED and resolve the symbol by name**
(`grep -n "<symbol>" src\*.cpp`). The **claims** in this file were
measured and mostly still hold; only their addresses rotted.

The load-bearing entry points, and the **grep that finds each** — this table
replaced a column of line numbers because that column rotted inside a week:

| Symbol | Anchor |
|---|---|
| `UiSpike::ScaleOnShow` | `src\UiSpike.cpp` (grep `void UiSpike::ScaleOnShow`) |
| `UiSpike::EarlyDockTick` | `src\UiSpike.cpp` (grep `void UiSpike::EarlyDockTick`) |
| `UiSpike::EarlyMinimapBake` | `src\UiSpike.cpp` (grep `void UiSpike::EarlyMinimapBake`) |
| `UiSpike::MarkerIsDesignUnits` | `src\UiSpike.cpp` (grep `bool UiSpike::MarkerIsDesignUnits`) |
| `UiSpike::ScalePanelsUnder` | `src\UiSpike.cpp` (grep `int UiSpike::ScalePanelsUnder`) |
| `UiSpike::ScaleGodFlyouts` | `src\UiSpike.cpp` (grep `void UiSpike::ScaleGodFlyouts`) |
| `UiSpike::ScalePanelRoot` | `src\UiSpike.cpp` (grep `int UiSpike::ScalePanelRoot`) |
| `UiSpike::DialogDockTick` | `src\UiSpike.cpp` (grep `void UiSpike::DialogDockTick`) |
| `UiSpike::RegionWatchTick` | `src\UiSpike.cpp` (grep `void UiSpike::RegionWatchTick`) |
| `UiSpike::ScaleMenuFlyouts` | `src\UiSpike.cpp` (grep `void UiSpike::ScaleMenuFlyouts`) |
| `UiSpike::ScaleSubtree` | `src\UiSpike.cpp` (grep `void UiSpike::ScaleSubtree`) |
| `ScaleTier::Decide` | `src\ScaleTier.cpp` (grep `float Decide(`) |
| `kNeverScaleIds` / `kFontSizedIds` / `kAdviceListScaleSelfIds` | `src\UiSpike.cpp` (grep each name followed by `[] = {`) |
| `kRegionPanelIds` / `kCityDialogIds` / `kDVPins` | `src\UiSpike.cpp` (grep `kRegionPanelIds[] = {`, `kCityDialogIds[] = {`, `kDVPins[] = {`) |
| `kThirdPartyDeps` / `kPackages` | `src\ScaleTier.cpp` (grep `kThirdPartyDeps[] = {`, `kPackages[] = {`) |

---

**Conventions used throughout this document**
- `[M]` = **measured** this session, from source, from a shipped artifact, or from a live log line already in the repo.
- `[INF]` = **inference**. Our law: *an inference written down as a measurement kills your next seven candidates.* Every unmarked structural statement is a direct read of the cited **symbol** — resolve it by grep, not by line number.
- Axis tags: **A = UI-GEOMETRY** (window rects, art, chrome, layout constants) · **B = TEXT** (font point sizes, wrap widths, HTML size tables) · **C = UDI-BUBBLE** (the in-world mission marker) · **MIXED** (an element whose box is derived from its text, or whose text is wrapped to its box).

---

## 0. THE ONE ARCHITECTURAL FACT THAT FRAMES EVERYTHING

There is **exactly one scale number in the entire DLL**: `Settings::spikeScaleFactor` (`src\Settings.h`, grep `float spikeScaleFactor`), overwritten at boot by the tier decision (`src\SC4UIScaleDllDirector.cpp`, grep `settings.spikeScaleFactor = tier`) and mirrored into the namespace-scope `gTierF` (`src\UiSpike.cpp`, grep `float gTierF =`; the mirror is written by `UiSpike::SetTierMirror`). Every runtime lever in §1 reads one of those two. **87 occurrences of the pair in `UiSpike.cpp` alone.** `[M]`

The axes are fused a second time **upstream of the DLL**: `ScaleTier::SyncStaticLayers` (`src\ScaleTier.cpp`, grep `void SyncStaticLayers`, called from `src\SC4UIScaleDllDirector.cpp`, grep `ScaleTier::SyncStaticLayers`) picks **one tag** (`-15x` / `-2x` / `-3x`) that gates the art dat **and** `FontStyle<tag>.ini` in the same call, and tier eligibility is gated on the **art** dat existing (`src\ScaleTier.cpp`, grep `bool PackageInstalled` and the "Is this tier's art actually on disk?" comment above it).

**Consequence, stated plainly:** "UI 2x + Text 3x" is not expressible at any layer today — not in the settings, not in the runtime, not in the package system. §2 explains why that is the *correct* state and not a limitation to be lifted.

**Warning — the `gTierF` trap, and why any new mirror must repeat an audit.** The comment block directly above the `gTierF` definition records it in place (`src\UiSpike.cpp`, grep `gTierF mirrors settings.spikeScaleFactor`): `ArmDeferred` installs four hooks at `PostCityInit`, **before any sweep has written `gTierF`**, so anything running from those hooks pre-sweep sees the **compiled default `2.0f`**. That is why `EarlyDockTick` deliberately reads `settings.spikeScaleFactor` (`src\UiSpike.cpp`, grep `void UiSpike::EarlyDockTick`, then the `const float f = settings.spikeScaleFactor;` at its head) and not `gTierF`. **A second scale number needs its own mirror and its own repeat of this audit, or it silently defaults to 2.0.**

---

# 1. THE CATALOG

## 1.0 How to read the tables

Each row: the lever, **the grep that finds it**, what it multiplies, which axis it belongs to, when it reads the factor, whether it is idempotent and which epoch clears it, and any **coupled pair** (Law 43: *a coupled pair ships together or not at all — and whatever moves a sprite must move its hit box*). The "where" column names a file and a symbol; it never names a line, because line numbers in this tree rot inside a week.

---

## 1.1 AXIS A — UI-GEOMETRY (runtime)

### 1.1a Global plumbing

| Lever | Where (grep) | Multiplies | f timing | Idempotent / epoch | Notes |
|---|---|---|---|---|---|
| `Settings::spikeScaleFactor` | `src\Settings.h` (grep `float spikeScaleFactor`); parsed `src\Settings.cpp` (grep `"ScaleFactor"`); overwritten `src\SC4UIScaleDllDirector.cpp` (grep `settings.spikeScaleFactor = tier`) | the single factor | once at boot | n/a | today carries **all three** axes |
| `gTierF` mirror | `src\UiSpike.cpp` (grep `float gTierF =`); written by `UiSpike::SetTierMirror` and inside `ScaleMenuFlyouts` (grep `gTierF = f;`) | every namespace-scope hook | written per pass, read per **draw** | n/a | see the trap at §0 |
| `ScaleRound` | `src\UiSpike.cpp` (grep `inline int32_t ScaleRound`) | window geometry | per call | pure | `ScaleRound` is `RoundHalfUp(v * f)` — one line, delegating (#162). |
| `RoundHalfUp` (floor(v+0.5)) | `src\UiSpike.cpp` (grep `inline int32_t RoundHalfUp`) | tier-math constants, all blit dst rects, **and now window geometry too** | per call | pure | the **art pipeline** convention — matches `Upscale2x::ScaleDim` and the `.UI` builders' `scale_len`. **There is now one rounding stream, not two.** |

> **The two-rounding-streams entry is settled.** `llround` rounds a negative
> half value *away from zero* (−16.5 → −17), so any window with a **negative
> absolute design origin** had both edges pushed outward and came out ONE
> PIXEL LONGER than the same span scaled as a length. That was #162 — "a
> phantom line under the mayor's hat" and "random lines under the advisor
> portraits", both reported as **1.5x-only**, which is structural: at f=2 and
> f=3 `v*f` is already whole and the two rules are byte-identical.
>
> **The integer-tier control, measured over all 2920 nodes of the shipped `.UI`
> corpus:** f=2 → **0** size and **0** position changes; f=3 → **0** and **0**;
> f=1.5 → 8 sizes and 44 positions, in 6 files, **all** descendants of the 12
> nodes with a negative absolute origin. Priced by
> `tools\uimap\emu\gate_art_vs_window.py` (grep `llround_scale as R` for the
> rule swap that reproduces the refuted pre-#162 behaviour): with `llround`, 1 node short at 1.5x
> and 0 at 2x; with half-up, **0 and 0**, and the f=2 control stays 0 either way.
>
> Task #75's "unresolved 824-pair 1.5x divergence" was CLOSED AS REFUTED —
> the divergence had no artifact. This row is the current state.
| `ScaleTier::Decide` + `SyncStaticLayers` | `src\ScaleTier.cpp` (grep `kPackages[] =`, `float Decide(`, `void SyncStaticLayers`); called `src\SC4UIScaleDllDirector.cpp` (grep `ScaleTier::Decide`, `ScaleTier::SyncStaticLayers`) | selects ONE tag for art dat **and** FontStyle | once at boot | idempotent by file state | **MIXED A+B** — see §2.4 |

### 1.1b The generic sweep

| Lever | Where (grep) | Multiplies | f timing | Idempotent / epoch | Coupled pair |
|---|---|---|---|---|---|
| `ScaleSubtree` rect scale | `src\UiSpike.cpp` (grep `void UiSpike::ScaleSubtree`) | **POSITION IS EDGE-DERIVED IN THE *PARENT'S* FRAME; SIZE IS LENGTH-DERIVED FOR LEAVES AND STATE-STRIP BUTTONS.** Position: `newL/T = ScaleRound(pAbs+l,f) - ScaleRound(pAbs,f)`, rounded in the parent's absolute *design* frame, **not** `round(v*f)` (#161 — grep `pAbsL` inside `ScaleSubtree`; the frame is handed down on the recursive call and seeded by `ScalePanelRoot`, grep `#161: hand this DESIGN origin to the child loop`). Note: `[UiSpike] ParentFrameRounding=0` collapses `pAbs` to 0 (grep `if (!settings.spikeParentFrameRounding)`) and restores the old `round(v*f)` exactly — it defaults **on** (`src\Settings.h`, grep `spikeParentFrameRounding`; parsed `src\Settings.cpp`, grep `"ParentFrameRounding"`). Size: `newW/H = ScaleRound(aL+w,f) - ScaleRound(aL,f)` for containers, but `ScaleRound(w,f)` when the window's vtable is `0x00ADDAF0` (#167 state-strip button class — grep `0x00ADDAF0`) **or** when it has no children (#148 leaf rule — grep `#148 THE REVERSE L`; this branch runs *after* the ternary and overrides it, so leaf wins). All three are no-ops at an integer factor by construction (each guarded in place; grep the `#161`/`#167`/`#148` markers). **Law: this row does NOT govern the advisor button row.** `0x6A15C767` is in `kDataScaledSubtreeIds` (grep `kDataScaledSubtreeIds[] = {`) and `ScalePanelRoot` returns before its child loop for those ids (grep `IsDataScaledSubtreeId(win->GetID())`), so the sweep never walks those buttons — their size comes from `tools\selective-safe\build_selective_safe.py`, which is where #170 was fixed. | `f` param | yes, via `Classify` → `scaleMap` | window rect ↔ its cached paint buffer |
| centre-small-leaves branch | `src\UiSpike.cpp` (grep `centerLeaves` inside `ScaleSubtree`) | slot centre; leaf keeps 1x size | per pass | yes (records `scaled==orig`) | leaf moves but does not grow; hit box moves with it |
| `ScalePanelRoot` — anchor + resize | `src\UiSpike.cpp` (grep `int UiSpike::ScalePanelRoot`); anchors and clamps are the `gapT`/`gapB`/`cMinY` block inside it (grep `if (gapT > cMinY && gapB > cMinY)`) | root rect, gaps `round(gapL,f)` | `f` param | yes; `PurgeSubtreeRecords` on Fresh (grep `PurgeSubtreeRecords`) | root move ↔ root resize — **call order is load-bearing** (the comment says so in place) |
| double-scale guard + tombstone | `src\UiSpike.cpp` (grep `double-scale` and `tombstone`) | — | — | tombstone record | compares against `frameW/H`; fails **safe** (skip + one log line) |
| `ScalePanelsUnder` city/region loop | `src\UiSpike.cpp` (grep `int UiSpike::ScalePanelsUnder`; the factor is the `const float f = settings.spikeScaleFactor;` at its head) | drives all of the above | `settings.spikeScaleFactor` | yes | — |
| `ScaleMenuFlyouts` (size only, no root move) | `src\UiSpike.cpp` (grep `void UiSpike::ScaleMenuFlyouts`; `gTierF = f;` is its first statement) | subtree rects, `centerLeaves=true` | per pass | yes; `menuBaseline` cleared in `UiSpike::Disarm` | flyout size ↔ spawn button |
| `ScaleGodFlyouts` dock tables | `src\UiSpike.cpp` (grep `void UiSpike::ScaleGodFlyouts`); god table grep `kGodFlyoutDock[] = {`; mayor table grep `kMayorFlyoutDock[] = {` | `target = buttonAbs + f*R` | `f` + `gTierF` | yes; `lastView` nulled in `UiSpike::Disarm` | **Law:** flyout position ↔ spawn button ↔ hidden alignment marker `0x0000AAAA` |
| `MarkerIsDesignUnits` (#94) | `src\UiSpike.cpp` (grep `bool UiSpike::MarkerIsDesignUnits`) | — (pure read of `scaleMap`) | — | pure read | marker units ↔ scaleMap record |
| `DialogDockTick` (region dialogs) | `src\UiSpike.cpp` (grep `void UiSpike::DialogDockTick`; the factor is its opening `const float f = settings.spikeScaleFactor;`); table grep `kRegionDialogDocks[] = {` | dialog rect + dock under spawn button | per tick | yes; `dialogDocked[8]` reset on close (grep `dialogDocked`) | dialog ↔ spawn button |
| `RegionWatchTick` | `src\UiSpike.cpp` (grep `void UiSpike::RegionWatchTick`) | drives the region pass | per tick | stability-gated | — |
| in-city dialog pass (`kCityDialogIds`) | `src\UiSpike.cpp` (grep `kCityDialogIds[] = {` and its consuming loop) | dialog rect + descendants | `settings.spikeScaleFactor` | yes; guard `arrived == round(base*f) ±1` | **Warning: factor-parameterised guard** — new factors need a fresh product-collision check (v2.39.13/.14 scars) |
| BMPRECT `imagerect` doubling | `src\UiSpike.cpp` (grep `BMPRECT`) | GZWinBMP `imagerect` `[+0xe8..0xf4]` ×f | per Fresh dialog | one-shot per Fresh instance | 9-slice src rect ↔ 2x art in the dat |
| `EarlyDockTick` (EARLYDOCK, #89) | `src\UiSpike.cpp` (grep `void UiSpike::EarlyDockTick`) | dock root via `ScalePanelRoot` | `settings.spikeScaleFactor` (**not** `gTierF`, deliberately) | one-shot per city; latches reset in `ArmDeferred` and `Disarm` | **Law: scale ↔ minimap surface recreate are ONE action** — the `TryRecreateMinimapSurface(pDock)` call sits inside `EarlyDockTick` itself; splitting them was the v2.41.15 crash |
| `EarlyMinimapBake` | `src\UiSpike.cpp` (grep `void UiSpike::EarlyMinimapBake`) | two dirty bytes only | `settings.spikeScaleFactor` | one-shot per city | — |
| `ScaleOnShow` / ShowHook | `src\UiSpike.cpp` (grep `void UiSpike::ScaleOnShow`, installed by `UiSpike::InstallShowHook`) | subtree via `ScaleSubtree(gTierF)` | `gTierF` per event | yes | dormant at the shipped `ShowHook=1` |
| `Classify` / `scaleMap` | `src\UiSpike.cpp` (grep `UiSpike::ScaleState UiSpike::Classify`); map `src\UiSpike.h` (grep `std::map<void*, ScaleRecord> scaleMap`); record `src\UiSpike.h` (grep `struct ScaleRecord`) | — | — | **THE idempotence engine**; cleared only in `UiSpike::ResetTracking` (app shutdown) | `ScaleRecord` stores **one** `scaledW/H` and has **no axis field** |

### 1.1c Sub-flyout / disaster draw-hook family (painted, not windowed)

| Lever | Where (grep) | Multiplies | f timing | Idempotent / epoch | Coupled pair |
|---|---|---|---|---|---|
| SUBBORN — `vf10` field promotion, 7 fields | table `src\UiSpike.cpp` (grep `kSubFields[] = {`), detour `SubVf10Detour`, install `UiSpike::InstallSubFlyoutBorn` | `round(stock*gTierF)` on `[0xE4,0xE8,0xF0,0xF4,0xF8,0xFC,0x100]` | `gTierF` per construction | yes (promotes only a still-stock value) | **Law:** `[0xE4]` is **dual-use**: bar width **and** the `IsPointInMe` claim width. Fused with `gStripFieldScale = 1` (grep `gStripFieldScale`) — "neither half shippable alone" |
| SUBBORNSCALE — Place detour | `src\UiSpike.cpp` (grep `SubPlaceDetour`, installed by `UiSpike::InstallSubFlyoutBornScale`; the math is the `ScaleRound(l + cw, gTierF)` block inside it) | `ScaleRound(l+cw,gTierF) - ScaleRound(l,gTierF)`, all 4 `sr[]` | `gTierF` per Place | records drained to `scaleMap` as AlreadyScaled (grep `void UiSpike::DrainBornScaleRecords`; called **before** the walk in `ScalePanelsUnder`) | container ↔ its born-correct paint buffer |
| Sub-flyout ring model | `src\UiSpike.cpp` (grep `inline int32_t SubPlaceTop`, `SubPlaceTopMb`, `int gSubMath`) | `round(-16.5*f) - 20`, `29 - round(26.5*f)`, ring blit Y | `gTierF` per open | latched per menu, self-correcting within a frame | **Law — RING LAW** (grep `RING LAW`): container position ↔ ring sprite Y ↔ back-arrow hit rect (grep `back-arrow`) |
| Strip item metrics `[0xf4/f8/fc]` | `src\UiSpike.cpp` (grep `SubMetricsDetour`; the disaster twin is the `gDisStripBase4` block, grep `gDisStripBase4`) | `round(gStripBase* × gTierF)` | `gTierF` every Plot | base latched once (grep `gStripBaseCap`); `gSubLastStrip`/`gDisLastStrip` nulled in `UiSpike::Disarm` | **Law:** item draw rect ↔ item hit rect (grep `gStripHitW`) |
| Container hit-claim `[+0xe0]` (`gClaimScale`) | `src\UiSpike.cpp` (grep `gClaimScale`; latch grep `gClaimOrig`) | `round(gClaimOrig × gTierF)` | `gTierF` per draw | sane-range guard; presented as 1x inside the draw group, re-armed after | **Law — the canonical Law-43 pair** — this IS the hit box for the 2x-drawn sprite |
| Ring atlas fractional-NN upscale | `src\UiSpike.cpp` (grep `DrawDisasterElementScaled`; the upscale is its `FloorScale(s[2] - s[0], f)` pair) | `round(sw*gTierF)`, source `ox/gTierF` | per draw | stateless | ring ↔ strip ↔ bar, welded in one buffer |
| Sub-flyout atlas upscale | `src\UiSpike.cpp` (grep `subDstW`, inside `BltClassThunk`) | same form | per draw | stateless | — |
| Bar widen / shift | `src\UiSpike.cpp` (grep `inline float BarWidenEff`, `inline int32_t BarDXEff`; draw grep `void DrawBarScaled`) | `round(53*W)`, `53 - round(53*W)` | `gTierF` per draw | stateless; `gBarCache` owner-keyed, cleared in `UiSpike::Disarm` | bar width ↔ bar x (flush-right invariant) |
| Family gates (`destIsContainer` heuristics) | `src\UiSpike.cpp` (grep `destIsContainer` — the size tests read `RoundHalfUp(250 * gTierF)` and friends) | `round(250*gTierF)`, `round(100/200*gTierF)`, `round(250..450*gTierF)` | per draw | stateless | **Warning: size *discriminators* derived from the factor** — with more than one live factor they stop discriminating |
| `ScaleGodFlyouts` claim re-scale sites | `src\UiSpike.cpp` (grep `gClaimOrig * gTierF` and the claim writes inside `UiSpike::ScaleGodFlyouts`) | `round(oldW × gTierF)` | per pass | idempotent by value compare | sprite ↔ hit box |
| FlashGuard (dead, kept) | `src\UiSpike.cpp` (grep `int     gFlashGuard`) | — | — | `gFgWaitRoot[4]` cleared in `UiSpike::Disarm` (grep `gFgWaitRoot`) | — |
| Live-tune ini re-read (every 20 sweeps) | `src\UiSpike.cpp` (grep `LiveTuneIniPath` and the `"LiveTune"` poll that uses it) | `gRingDX/DY`, `gBarDX/W`, `gStripHitW`, `gSubMath`, … | per event, ~20 sweeps | value writes only | reads `[Disaster]`/`[Flyout]`/`[Probe]` **by section, explicit keys** — a new section is therefore safe (§4.6) |

### 1.1d Runtime-image draw hooks

| Lever | Where (grep) | Multiplies | f timing | Idempotent / epoch | Coupled pair |
|---|---|---|---|---|---|
| `GaugeCtxBltThunk` — U-Drive-It dials | `src\UiSpike.cpp` (grep `GaugeCtxBltThunk`; the snap rule is its `sourceIsOneX` / `kFitSlack` test — #186 replaced the older relative `m < 0.75f * gGaugeScale` form, which now survives only in the comment recording that swap) | `dst = cw*m` with the fit clamp, plus **snap to 1.0 unless the source is judged still-1x** | `gGaugeScale` per sweep | per-instance vtable copies, cap 16; **`gGaugeEpoch`** (grep `gGaugeEpoch`, bumped in `UiSpike::Disarm`) is the #92 fix for pointer-keyed latches | dial art ↔ console window |
| MINIMAP / DVMAP / UDMAP surface recreate | `src\UiSpike.cpp` (grep `void UiSpike::TryRecreateMinimapSurface`; the DVMAP and UDMAP twins are the blocks tagged `DVMAP`/`UDMAP` in their own log lines) | `blitSize` (`[+0xE4]`, self-updated by the class `SetArea`) | derived from the live window | latched per instance; latches + retry budgets nulled in `UiSpike::Disarm` | **Law: window rect ↔ one-shot display surface** — the v2.21.0 heap overrun |
| `BmpCtxBltThunk` — GZWinBMP plain-path dest scale | `src\UiSpike.cpp` (grep `BmpCtxBltThunk`) | `dst = dst0 + round(w*m)`, `m = gBmpScale` **reduced until it fits the live window** | `gBmpScale` set once per pass (grep `gBmpScale = `) | per-draw one-shot (grep `gBmpBltDone`); budgets + `gBmpxRootTrack` cleared in `UiSpike::Disarm` | **Law: image dst ↔ live window size** — this is the UDI lever, §3 |
| `HookRuntimeBmpsUnder` + `kBmpxCityRoots` | `src\UiSpike.cpp` (grep `void HookRuntimeBmpsUnder`; roots grep `kBmpxCityRoots[] = {`, and the call that passes them) | sets `gBmpScale = f` for **all 12 roots at once** | per sweep | class-vtable copy is process-lifetime; per-open census (grep `FlushBmpOpenCensus`) | **MIXED A+C** — 11 UI roots + 1 UDI root on one global |
| dialog-root twin (`kBmpxDialogRoots`) | `src\UiSpike.cpp` (grep `kBmpxDialogRoots`) | same, 2 roots | per sweep | same | — |
| EARLYCHART `ChartStoreThunk` | `src\UiSpike.cpp` (grep `ChartStoreThunk` — the definition and the one vtable-slot install that points at it) | plot rect margins ×`gTierF`, `bandH 32→32f`, ticks `4→4f` | `gTierF` per paint | verify-before-write on the vtable slot; `gChartBornLog` reset in `UiSpike::Disarm` | **MIXED** — see R2/R3 in §2.2 |

### 1.1e Byte patches (all PostAppInit one-shots into `.text`)

Every row resolves the same way: grep the `Apply…` name in `src\SC4UIScaleDllDirector.cpp` for the call, and in `src\CodePatches.cpp` for the definition. The site tables are named, so grep those by name too.

| Lever | Site table(s) to grep in `src\CodePatches.cpp` | Axis |
|---|---|---|
| `ApplyRatingArrowScale` | `kRatingImulSites` (3 imul sites) | **A** (art-coupled: 7px/rating point ↔ 2x arrow art) |
| `ApplyTooltipWrapScale` | `kTipWrapSites = {0x79880A, 0x7988A9}`, `kStockTipWrap` | **MIXED** — R8 |
| `ApplyHtmlSizeScale` | `kHtmlFontSizeTable`, `kHtmlHeadingSizeTable`, `kPopupStyleRetargets` | **B** — the only true runtime TEXT lever |
| `ApplyAdviceRowScale` | grep `int ApplyAdviceRowScale`; the patched window is `0x0079388F` / `0x0079388B` | **MIXED** — R9 |
| `ApplyBudgetButtonScale` | `kBudgetBtnSizeSites`, `kBudgetBtnXSites`, `kBudgetBtnYSites` (35 sites) | **A** |
| `ApplyOrdinanceInsetScale` | `kOrdinanceInsetSites`, `kOrdinanceNameXImm8Sites` | **A** (inset chosen to clear 2x icons) — but see R19 |
| `ApplyBudgetFamilyScale` | `kDeptImm8Sites`, `kDeptImm32Sites`, `kMasterNotchSites`, `kBudgetLeaDisp8Sites`, `kBudgetSubImm8Sites`, `kBizBoxSizeSites` | **A** — but see R20/R21 |
| `ApplySubFlyoutProviderScale` | `kSubFlyoutProviderSites` | **A** — **Law:** fused with SUBBORN; `sub_7EAEB0` only, the twin `sub_7E7270` must stay stock (`src\CodePatches.h`, grep `sub_7E7270`) |
| `ApplyDataViewLegendScale` | `kDataViewLegendLeaSites`, `kDataViewLegendImm32Sites` | **A** for the **origins only**; the pitch is text-derived and must never be patched (`src\CodePatches.h`, grep `ApplyDataViewLegendScale` and read the contract comment above it) → quasi-MIXED, R16 |

**Warning: all nine are one-shot at `PostAppInit`.** `ScaleSizeTable` verifies against *stock* bytes before writing (`src\CodePatches.cpp`, grep `void ScaleSizeTable`), so a second application at a new factor finds non-stock bytes and **skips**. This is the structural reason knob 1 requires a restart (§4.6).

---

## 1.2 AXIS A — UI-GEOMETRY (offline / assets)

| # | Artifact | Generator | Factors built | What it bakes | Gated by |
|---|---|---|---|---|---|
| 1 | (art PNG upscaler) | `tools\upscale\Upscale2x.cs` — grep `private static int ScaleDim`. **`ScaleDim` is NOT plain `floor(v*f+0.5)`.** It rounds half-up (its first statement), then **at a non-integer factor only** snaps the result to a multiple of `CellUnit(v)` — the LCM of whichever of `kCellCounts = {3,4}` (grep `kCellCounts`) divides the **source** dim (grep `private static int CellUnit`) — ties **UP** (grep `Ties go UP`), abandoned if the correction exceeds 12.5% of the **scaled** dim (grep `Math.Abs(snapped - s) * 8 > s`). **It returns before `CellUnit` is ever consulted when the factor is whole (grep `if (factor == Math.Floor(factor)) return s;`), which is why every snap defect (#157, #158, #171) is 1.5x-only and 2x/3x stay byte-identical.** Snap scoping is per file: `--no-snap` → `CellUnit` = 1 (grep `if (sNoSnapThis) { return 1; }`), `--nine-slice` → `CellUnit` consults `{3}` alone (grep `kNineSliceCounts`, `sNineSliceOnly`). The **height** is taken out of `ScaleDim` entirely at every write site (grep `sNoHeightSnap ?` — `oh = sNoHeightSnap ? floor(h*f+0.5) : ScaleDim(h,f)`, four of them) by `--height-exact-group` / `--height-exact-strips` (grep those flag names in the argument parser) — **Law: there is no `--no-height-snap` flag; the one source comment naming one is stale (grep `--no-height-snap`; a single hit, in a comment), `sNoHeightSnap` is only the field (grep `private static bool sNoHeightSnap`)**. `--cell-strips` does **not** touch the snap: it sets `sStripStates` for `BuildSampleMap`'s per-state horizontal **sampling**. NN throughout (`--hq` is never safe to ship). Factor guard `(1.0, 16.0]` — grep `factor > 16.0`. | any `--factor` | PNG pixel dims | nothing — feeds 2–7 |
| 2 | `z_SC4UIScale_SelectiveArt-{2x,15x,3x}.dat` | `tools\selective-safe\build_selective_safe.py` | **equal at every tier** — #136 closed the 3x fork: the `or FACTOR <= 2.0` tail on the `0x1441625x` glyph range is gone (grep `if True` in `build_selective_safe.py`, immediately under the `0x14416250` range); `src\CodePatches.cpp` (grep `THE TIER CEILING IS GONE` — "3x SelectiveArt therefore goes 651 -> 655 entries"); the per-tier entry counts are asserted in `_tests\Test-DatIntegrity.ps1` (grep `SelectiveArt` — the rows carry their own `# #136: was 651` history, and the count has moved again since) | 2x art in place or cloned at `iid^CLONE_XOR` (`build_selective_safe.py`, grep `CLONE_XOR =`); `imagerect`; `area` for **all ten `kDataScaledSubtreeIds` roots, the 7 seated advisor faces, and the ticker marquee** — `src\UiSpike.cpp` (grep `kDataScaledSubtreeIds[] = {`) lists the ids and `build_selective_safe.py` runs `double_subtree_areas` on every one (grep `double_subtree_areas(new_text` for the advisor, four budget, three Graphs, dashboard and console-variant calls); the faces are `ADVISOR_FACE_SEATS` seated by `seat_faces_on_apertures`; the marquee is the `id=0xaa12f33c` `widen_marquee` closure | `src\ScaleTier.cpp` — the SelectiveArt gate is `SyncDat(docPlugins, L"z_SC4UIScale_SelectiveArt", pkg.tag, match)` (grep `z_SC4UIScale_SelectiveArt"`; a second `SelectiveArt` mention sits in the payload-probe comment above `PackageInstalled` and is not the gate) |
| 5 | `z_SC4UIScale_ItemIcons-{tier}.dat` | `tools\itemicons\stage_icons.py` | 356 each | 266+ toolbar picker icons | `src\ScaleTier.cpp` (grep `z_SC4UIScale_ItemIcons"`) |
| 6 | `zzz-SC4UIScale\z_SC4UIScale_ItemIconsSub-{tier}.dat` | `tools\itemicons\build_itemicons_sub.py` | 130 each | 129 mod-owned icons + Missing Thumb `0x144161EC` | `src\ScaleTier.cpp` (grep `z_SC4UIScale_ItemIconsSub`) |
| 7 | `zzz-SC4UIScale\z_SC4UIScale_ThirdPartyUI-{tier}.dat` | — | 2 each | CoriBoom's `.UI` + its 516x654 art | `src\ScaleTier.cpp` (grep `z_SC4UIScale_ThirdPartyUI`), dep-gated |
| 10 | `zzz-SC4UIScale\z_SC4UIScale_WarriorUI-{tier}.dat` | — | 4 each | warrior's 2 flyout scripts + 2 art TGIs | **FIXED by #119 (v2.71.3).** `src\ScaleTier.cpp` (grep `z_SC4UIScale_WarriorUI`) — tier-gated on `pkg.tag`/`match` AND mod-gated via `DepOkByName`, the same shape as the other dep-gated `SyncDat` calls (grep `DepOkByName` for the full set: SaveWarningUI, CamUI, ThirdPartyUI, NamIcons and the rest). Rationale is the comment directly above the call (grep `#119 (v2.71.3): THIS CALL WAS MISSING`); the `kThirdPartyDeps` row it consumes is the `z_SC4UIScale_WarriorUI` entry in that table. |

**Correctly axis-free (neither A nor B nor C):**

| # | Artifact | Why it is axis-free |
|---|---|---|
| 11 | `zzz-SC4UIScale\z_SC4UIScale_MenuFix.dat` | exemplar patches re-pointing CAM's 10 broken submenu parents. No pixels, no points. Untagged and correct. |
| 12 | `z_SC4UIScale_WebText.dat` | 3 LTEXTs swapping `simcity.ea.com` → Simtropolis, matching `WebRedirect.cpp`. String content only. Untagged and correct. |

---

## 1.3 AXIS B — TEXT

Only **three** artifacts are purely on the text axis. That is the whole of it.

| Lever | Where (grep) | Multiplies | Notes |
|---|---|---|---|
| `FontStyle-{2x,15x,3x}.ini` | `tools\fonts\make_fontstyle.py` | the `size` token of the **88 stock** styles (the shipped files hold **90** — the two `HTML_CLONE_BLOCK` styles are added but never scaled; see the correction box below); CRLF / GUIDs / params byte-preserved | mirrored to `<install>\Plugins\FontStyle.ini` at boot by `ScaleTier::SyncFont` (`src\ScaleTier.cpp`, grep `void SyncFont` and its call sites). Note: the game reads `FontStyle.ini` from the **install** `Plugins\`, not Documents |
| HTML `.rdata` size tables | `src\CodePatches.cpp` (grep `kHtmlFontSizeTable` `0xACD4A0 = {8,10,12,14,18,24,36}` and `kHtmlHeadingSizeTable` `0xAB4AD0 = {8,10,12,16,19,24,48}`); applied inside `ApplyHtmlSizeScale` via `ScaleSizeTable` (grep `void ScaleSizeTable`) | `lround(stock[i] * factor)` | each rich window **copies** the table at creation (setter `0x8FEEB8` → `this+0x1A8`), so one `.rdata` write at PostAppInit reaches every instance the process will build. Gated by `[UiSpike] HtmlSizePatch` (default 1). This is what makes news, story pages, tutorials, advisor toasts, My Sims rows and Credits scale **at all** — `FontStyle.ini` can never reach them |
| `HTML_CLONE_BLOCK` popup styles | `tools\fonts\make_fontstyle.py` (grep `HTML_CLONE_BLOCK`); retargeted by `kPopupStyleRetargets` (`src\CodePatches.cpp`, grep that name) | two never-scaled clone styles + 4 `push <guid>` retargets | see R11 — this exists **only** to stop the popup path compounding FontStyle × table to 4x |

**Font size facts** `[M]` (13 distinct 1x sizes: `10×1, 11×3, 12×2, 13×28, 14×22, 15×4, 16×15, 17×2, 18×4, 19×2, 21×2, 24×2, 32×1`):

> **Correction — the ranges are measured off the shipped files, and the style
> count depends on which file you count.**
>
> * "Range 15–48 at 1.5x, 20–64 at 2x, 30–96 at 3x" would just be
>   `round(1x-range × f)`. **Measured off the shipped files:**
>   `packages\15x\FontStyle-15x.ini` = **14..48**, `FontStyle.candidate.ini`
>   (2x) = **14..64**, `packages\3x\FontStyle-3x.ini` = **14..96**. The
>   **14** floor is the never-scaled `MessageBodyHtml` clone — which this
>   very table declares two rows down.
>   `tools\packages\PACKAGES.md` §`packages\15x\` / §`packages\3x\` and the
>   `FontStyle.candidate.ini` paragraph under them carry the correct figures.
> * `FontStyle.default.ini` (stock) = **88** styles. Every generated file —
>   candidate, 15x, 3x — = **90**, because `HTML_CLONE_BLOCK` adds two. The
>   generator's own stdout says *"88 styles, size range 15..48"* because
>   **clones never enter its change list**, so 88/15 is what it *printed*
>   and 90/14 is what is *on disk*. Both numbers are right about different
>   things; say which. (Re-measured on the files themselves:
>   `FontStyle.default.ini` 88 / range 10..32; `FontStyle.candidate.ini` 90
>   / 14..64; `packages\15x\FontStyle-15x.ini` 90 / 14..48;
>   `packages\3x\FontStyle-3x.ini` 90 / 14..96.)

| Style | 1x | 1.5x | 2x | 3x | note |
|---|---|---|---|---|---|
| `ChartTickText` | 10 | 15 | 20 | 30 | was `KEEP_STOCK` until v2.53.2 |
| `Legend` | 13 | **18** | **24** | **36** | `SIZE_SQUEEZE` 0.92 — **not** 20/26/39 |
| `Default` / `Body` / `ToolTip` / `MenuItem` / `ButtonLabel` … (28 styles) | 13 | 20 | 26 | 39 | |
| `LoadScreenTitle` | 32 | 48 | 64 | 96 | |
| `MessageHeaderHtml` / `MessageBodyHtml` | 16 / 14 | 16 / 14 | 16 / 14 | 16 / 14 | never scaled, any tier |

- **`KEEP_STOCK`** (`tools\fonts\make_fontstyle.py`, grep `KEEP_STOCK = set()`) is **empty today**. Its one historical member was `ChartTickText`, pinned because the Graphs tick gutter was a frozen 45px rect; unpinned at v2.53.2 once the geometry lever landed. The retired warning about it is still in the comment block directly above the empty set (grep `DO NOT UNPIN THIS AGAIN`).
- **`SIZE_SQUEEZE = {"Legend": 0.92}`** (grep `SIZE_SQUEEZE`; applied as `eff = factor * SIZE_SQUEEZE.get(name, 1.0)` — grep `SIZE_SQUEEZE.get`). Measured, not aesthetic. It is **one half of a coupled pair** — see R5.
- Shipped `packages\15x\FontStyle-15x.ini` and `packages\3x\FontStyle-3x.ini` are **byte-identical to a fresh regeneration** `[M]`; `--selfcheck` byte-reproduces `FontStyle.candidate.ini` at factor 2. `tools\fonts\FontStyle-{15x,3x}.gen.ini` were the known-stale 62-style side-outputs, already excluded from deploy — **RETIRED: both files were deleted from the tree on 2026-08-23** (`git log --diff-filter=D --name-only -- tools/fonts/FontStyle-15x.gen.ini`), so the hazard they posed is gone rather than merely gated. The gate that excluded them still ships and still names the three real sources: `_tests\Deploy-OnGameClose.ps1`, grep `FONT TIER SOURCES`.

---

## 1.4 AXIS C — UDI-BUBBLE

**Exactly one element.** The in-world U-Drive-It mission marker, window id `0x48E945B4`, art TGI `{856DDBAC, 46A006B0, 094AC89A}`.

| Lever | Where (grep) | Role |
|---|---|---|
| membership in `kBmpxCityRoots` | `src\UiSpike.cpp` (grep `kBmpxCityRoots[] = {`, then `0x48E945B4` inside it; the rationale is the `U-DRIVE-IT MISSION MARKER` comment immediately above the entry) | the **only** thing that scales its drawn image |
| `BmpCtxBltThunk` | `src\UiSpike.cpp` (grep `BmpCtxBltThunk`) | stretches dst by `m = min(gBmpScale, winW/artW, winH/artH)` |
| `gBmpScale` | `src\UiSpike.cpp` (grep `float  gBmpScale` for the declaration, `gBmpScale = ` for the per-pass write) | **Warning: one global serving all 12 roots** |
| `gBmpCurId` | `src\UiSpike.cpp` (grep `gBmpCurId`) `[M]` | already available inside the draw thunk — the natural home for a per-id lookup |
| window scale | the blanket city sweep — `src\UiSpike.cpp` (grep `int UiSpike::ScalePanelsUnder`, which calls `ScalePanelRoot` per root) | the marker is a direct child of the 3D view `0x9A47B417` |
| art staging | `tools\selective-safe\build_selective_safe.py` (grep `0x094AC89A`) | stock 32x32 → 48 / 64 / 96 at 1.5x / 2x / 3x |
| the probe that proved it is a real window | `src\UiSpike.cpp` (grep `EDGE bubble`) | `EDGE bubble 0x48E945B4 PRESENT / rect (1637,610 128x128) vis=1 vt=00ADF6A0` — `0x00ADF6A0` is the GZWinBMP class |

Full mechanism, feasibility and ceiling: **§3**.

### What is NOT on the C axis, despite the name

These are ordinary UI-A chrome and **must not** take a bubble factor. Putting them on a 2×UI axis reproduces the #46 defect exactly ("424x650 → 848x1300, 4x frame around 2x content" — `src\UiSpike.cpp`, grep `424x650`).

| Element | id | Where (grep in `src\UiSpike.cpp`) | Rule |
|---|---|---|---|
| Car Control / status panel (11 vehicle scripts) | `0x10000006` | `0x10000006`, inside `kNeverScaleIds[] = {` | `kNeverScaleIds` — served by the static dat; runtime must not touch it (that WAS #46) |
| Vehicle + pedestrian pickers | `0xCBF32603` | `0xCBF32603` — one hit inside `kNeverScaleIds`, one inside `kBmpxDialogRoots` | static dat for layout, BMPX for runtime thumbs |
| Driving dashboard console (43 scripts) | `0x4BCB938A` | `0x4BCB938A` (it appears in `kAlwaysScaleCityIds`, `kDataScaledSubtreeIds` and the sweep); gauges `GaugeCtxBltThunk`; minimap `TryRecreateMinimapSurface` and the `UDMAP` block | swept + art + gauge draw hook + surface recreate |
| Console VARIANT (#93) | `0xEC1A5CBF` | `0xEC1A5CBF`, plus the `UDVAR` probe line | `kAlwaysScaleCityIds` (resident, `vis=0`) |
| UDI toolbar flyout + sub-flyout (#48/#95) | — | generic mayor-flyout dock + ring model | no UDI-specific id; ordinary flyout machinery |

---

## 1.5 MIXED — the group that matters most

**These are the elements whose box is derived from their text, or whose text is wrapped to their box.** They are catalogued here as reference; §2.2 presents the *risk register* that justifies the 1:1 lock.

> **Note: §1.5 and §2.2 are NOT "the same set".** §1.5 holds **15** rows
> (M1–M15); §2.2 holds **26** (R1–R26). They overlap heavily but they are
> different inventories at different granularities. **26 is the register's
> own count** (§2.2's own heading says so) and is the number to cite for the
> 1:1 lock.

| # | Element | Where (grep) | The coupling |
|---|---|---|---|
| M1 | `kFontSizedIds` — 23 controls, position-only | `src\UiSpike.cpp` (grep `kFontSizedIds` — the `[] = {` hit is the list, the `for (uint32_t known : kFontSizedIds)` hit is the consumer) | size deliberately **not** scaled because the font/art already sized it; position scaled by UI |
| M2 | Ordinance/deal description popup | `src\UiSpike.cpp` (grep `stockPopH` for the height pin, `natW = body->GetW() - 10` for the wrap) | box height `125*f` sized to hold N lines of scaled font; wrap width then derived from the box |
| M3 | Advice/news row column budget | `src\CodePatches.cpp` (grep `int ApplyAdviceRowScale`), patched over `83 EE 3D` @ `0x0079388F`; called from `src\SC4UIScaleDllDirector.cpp` (grep `ApplyAdviceRowScale`) | `S(f) = round(18f) + 18 + 9 + round(16f)`; the headline TEXT column is the residue |
| M4 | Tooltip wrap width | `src\CodePatches.cpp` (grep `kTipWrapSites`, `kStockTipWrap`, `void ApplyTooltipWrapScale`) | a TEXT wrap width scaled by the UI factor to protect a code-painted frame's corner arcs |
| M5 | HTML size tables + popup GUID retarget | `src\CodePatches.cpp` (grep `kHtmlFontSizeTable`, `kPopupStyleRetargets`, `void ApplyHtmlSizeScale`) + `tools\fonts\make_fontstyle.py` (grep `HTML_CLONE_BLOCK`) | the runtime TEXT patch and the DATA font package are one mechanism split across two artifacts |
| M6 | Chart interior + LEGENDFIX / LEGENDSWATCH (#57) | `src\UiSpike.cpp` (grep `LEGENDFIX`, `LEGENDSWATCH`, `CHARTGEO`; the born twin is `ChartStoreThunk`) | The chart renders **`ChartLabel` (`0xE9C86B5E`)**, not `Legend`, so `SIZE_SQUEEZE` never touches it (byte-verified at `0x0076DD91`). The legend ROW geometry is not band-derived: it is a six-constant right-margin budget owned by the PANEL builder `sub_76D3D0`, patched at birth by `CodePatches::ApplyGraphLegendBudgetScale` (grep `kGraphLegendImmSites`). The `32f` band write inside `ChartStoreThunk` (chart field `+0x108`/`+0x10C`) still ships and is still MIXED — but it is UNKNOWN whether the band rect and the legend column are the same object (reference gap G33 — the scope note that defines it lives in `SC4-UI-ENGINE.md` §5.4, grep `G33`; **`SDK-GAPS.md` has no §13, so that half of the old citation was already dead**): two independent instruments measured two different things. The measurement that would settle it: dump `chart+0x108` and the legend child rects in one `CHARTGEO` line at the same instant, or disassemble what reads `chart+0x108` inside the draw path `sub_9B5ADE` |
| M7 | `kAdviceListScaleSelfIds` — recursion disabled | `src\UiSpike.cpp` (grep `kAdviceListScaleSelfIds` — list and consumer) | items game-sized to the container (A) while their content is HTML text (B), with no lever left |
| M8 | Ticker marquee — hands off | `src\UiSpike.cpp` (grep `kAdviceListNeverTouchIds`, `0xAA12F33C`); the one `area=` edit is `tools\selective-safe\build_selective_safe.py` (grep `widen_marquee`) | width ships in the `.UI` at the UI factor; height is font-derived; neither reachable at runtime, by design |
| M9 | Budget master column width pin + forced caption re-apply | `src\UiSpike.cpp` (grep `0x0ABCE400` — the master-only slider id that gates the block) | widths are UI; the re-apply exists because the text paint buffer was born at the old width |
| M10 | Neighbor Deals combo width pin | `src\UiSpike.cpp` (grep `comboW`) | a UI width chosen to fit TEXT ("7000M"); no byte patch possible (disp8 ceiling) |
| M11 | News reader `0xAA231508` list membership | `src\UiSpike.cpp` (grep `0xAA231508`, inside `kAlwaysScaleCityIds`) | the membership of an A-axis id list is **justified by a TEXT fact** |
| M12 | Establish City `0x6A414973` | `src\UiSpike.cpp` (grep `0x6A414973`, inside `kNeverScaleIds`) | runtime geometry scaling breaks the **text colour** path; whole subtree handed to the static dat |
| M13 | DialogStatic geometry corpus | `tools\dialog-static\build_dialog_static.py` (grep `def scale_len` for the rule, `def verify_doubled` for the assertion, `drowheight` for row metrics, `dbl_gridcol` for `wingridcol`, `dbl_tuple` for `gutters/textoffsets/tipoffsets`) | 261 entries of hand-sized boxes, every one sized to hold a specific point size |
| M14 | Credits HTML LTEXT size map | `tools\dialog-static\build_dialog_static.py` (grep `credits_maps`, and `bump_width` for the table widths) | index remaps calibrated against the **runtime HTML table** but selected by the **UI package tag** |
| M15 | Data Views legend pitch | `src\UiSpike.cpp` (grep `kDVPins`, and `ACTIVELY WRONG` for the standing-down rationale); `src\CodePatches.h` (grep `ApplyDataViewLegendScale` and read the contract above it) | the game advances rows by `18 * ceil(measuredH / 18)` — a text-measured height with an unscaled quantum. We patch only the origins |

---

## 1.6 EVERY ID LIST, and whether a split axis would change its membership

| List | Where (grep) | Size | Purpose | Membership changes if axes diverge? |
|---|---|---|---|---|
| `kRegionPanelIds` | `src\UiSpike.cpp` (grep `kRegionPanelIds[] = {`) | 9 | region panels scaled even while hidden | No |
| `kNeverScaleIds` | `src\UiSpike.cpp` (grep `kNeverScaleIds[] = {`; consumers grep `IsNeverScaleId(`) | **20** — the three v2.65.0 Mode C roots are included: grep `0x0A41C7B2`, `0x0A41C7B3` and `0x27DF05BF` **inside that literal** (each carries its own trailing comment; all three ids also appear elsewhere in the file). `0xCBF32603` (§1.4) is in the same literal — grep it there | roots the **sweep** must not touch (static-dat served) | **YES** — every entry's justification is "the static dat serves it at the tier tag". No single tag ⇒ no premise. Consulted at only 2 sites (`ScaleOnShow`, city direct-children loop) — **not** `ScaleSubtree` |
| `kGodToolFlyoutIds` | `src\UiSpike.cpp` (grep `kGodToolFlyoutIds[] = {`) | 2 | skip in generic sweep | No |
| `kGodPanelIds` | `src\UiSpike.cpp` (grep `kGodPanelIds[] = {`) | 4 | scale by id even while `vis=0` | No |
| `kMayorFlyoutDock` | `src\UiSpike.cpp` (grep `kMayorFlyoutDock[] = {`) | 8 rows | `target = buttonAbs + f·R` | **YES** `[INF]` — `R = -marker(1x)` scaled by `f`; content sized on another axis no longer lands. No measurement exists at split axes |
| `kSubFlyoutIds` | `src\UiSpike.cpp` (grep `kSubFlyoutIds[] = {`) | 1 | shared 2nd-level container | No |
| `kAlwaysScaleCityIds` | `src\UiSpike.cpp` (grep `kAlwaysScaleCityIds[] = {`) | 33 | pre-scale while hidden (born-2x, no open flash) | **YES** — the stated rule (grep `IF WE SHIP 2x ART FOR A PANEL`) is *"IF WE SHIP 2x ART FOR A PANEL, IT MUST BE PRE-SCALED WHILE HIDDEN"*; `0xAA231508` is justified by a TEXT fact (M11) |
| `kDataScaledSubtreeIds` | `src\UiSpike.cpp` (grep `kDataScaledSubtreeIds[] = {`) | 10 | scale ROOT at runtime, children already scaled in the `.UI`, **never recurse** | **YES, sharpest** — children born at the *package tag* factor, root scaled at the *runtime* factor, recursion **disabled** so nothing can correct a mismatch. Note: also grants TWO powers (do-not-scale AND do-not-walk) |
| *(banned)* `kDataScaledWindowIds` | `src\UiSpike.cpp` (grep `THERE IS NO kDataScaledWindowIds` — the ban is the comment block under the `kDataScaledSubtreeIds` literal; the name has no definition anywhere) | **0** | documented ban (v2.41.1/.2/.3 — union-rect containers are ALL-OR-NONE) | must stay 0 |
| `kFontSizedIds` | `src\UiSpike.cpp` (grep `kFontSizedIds[] = {`) | 23 | position-only; size owned by font/art | **YES — this list IS the `UI == TEXT` assumption** (M1) |
| `kAdviceListScaleSelfIds` | `src\UiSpike.cpp` (grep `kAdviceListScaleSelfIds[] = {`) | 5 | scale self, never recurse | YES (M7). Structurally weak: keyed on ID, so any new `clsid 0xCA1492AC` window is unprotected (grep `0xCA1492AC` — the note sits just under the literal) |
| `kAdviceListNeverTouchIds` | `src\UiSpike.cpp` (grep `kAdviceListNeverTouchIds[] = {`) | 1 | ticker marquee | YES (M8) |
| `kRegionDialogDocks` | `src\UiSpike.cpp` (grep `kRegionDialogDocks[] = {`) | 6 | dialog ← spawn button | No |
| `kSubFields` | `src\UiSpike.cpp` (grep `kSubFields[] = {`) | 7 | born-2x container fields | No (but `[0xE4]` is dual-use) |
| `kGodFlyoutDock` | `src\UiSpike.cpp` (grep `kGodFlyoutDock[] = {`) | 2 rows | god flyout offsets | No |
| `kCityDialogIds` | `src\UiSpike.cpp` (grep `kCityDialogIds[] = {`) | 6 | main-window transients the sweep cannot reach | **YES** — guard is `arrived == round(base·f) ±1` with 3 candidate bases per id; new factors triple the product set (v2.39.13/.14 scars) |
| `kDVPins` | `src\UiSpike.cpp` (grep `kDVPins[] = {`) | 21 | Data Views legend fallback pin — **stood down** when `DataViewLegendPatchedSites() >= 8` (grep `DataViewLegendPatchedSites() >= 8`) | pitch hard-coded 18 while the game's is text-derived; already documented ACTIVELY WRONG (grep `ACTIVELY WRONG` — one hit, in the block under the table) |
| `kBmpxCityRoots` | `src\UiSpike.cpp` (grep `kBmpxCityRoots[] = {`) | 12 (8 My Sims + 3 Graphs + **1 UDI marker**) | GZWinBMP roots to hook | **YES — the single list that MUST split** for the C axis (§3.5) |
| `kBmpxDialogRoots` | `src\UiSpike.cpp` (grep `kBmpxDialogRoots[] = {`) | 2 | same, dialog scope | No |
| byte-patch site tables | `src\CodePatches.cpp` — grep each table by name; §1.1e lists all of them (`kRatingImulSites`, `kTipWrapSites`, `kPopupStyleRetargets`, `kBudgetBtn*Sites`, `kOrdinance*Sites`, `kDept*Sites`, `kMasterNotchSites`, `kBudget*Sites`, `kBizBoxSizeSites`, `kSubFlyoutProviderSites`, `kDataViewLegend*Sites`) | — | site addresses | `kTipWrapSites` (M4), `kPopupStyleRetargets` (M5) and the advice-row site (grep `kAdviceRowMidSite`) are text-adjacent; **all one-shot at PostAppInit** |
| `kThirdPartyDeps` | `src\ScaleTier.cpp` (grep `kThirdPartyDeps[] = {`) | **5** | package ↔ mod gates | packages named by tag; a second tag dimension multiplies this table. All five rows are consumed: the WarriorUI row (grep `z_SC4UIScale_WarriorUI` — first hit is the table row, the later hits are its `SyncDat` call) got its `DepOkByName` gate in #119 / v2.71.3, with the fix recorded in the comment directly above that call (grep `#119 (v2.71.3): THIS CALL WAS MISSING`). The row count moved 4 → 5 when `#139` added `NamIcons` (grep `z_SC4UIScale_NamIcons`). |
| `scaleMap` | `src\UiSpike.h` (grep `std::map<void*, ScaleRecord> scaleMap`); written/read throughout `src\UiSpike.cpp` (grep `scaleMap`) | unbounded | idempotence engine | `ScaleRecord` (`src\UiSpike.h`, grep `struct ScaleRecord`) has **no axis field**; `MarkerIsDesignUnits` (`src\UiSpike.cpp`, grep `bool UiSpike::MarkerIsDesignUnits`) reads it to answer "design or screen units" and would need an axis-qualified answer |
| `menuBaseline` | `src\UiSpike.h` (grep `std::map<void*, uint32_t> menuBaseline`) | dynamic | flyout-vs-machinery discriminator | No |

---

# 2. THE 1:1 TEXT LOCK

## 2.1 The decision

> **UI scale and TEXT scale ship LOCKED 1:1. UI 2.0 ⇒ fonts 2.0, always. There is no `TextScale` key, and a hand-added one is rejected and logged (§4.4).**
> **Decided by the user, 2026-08-03.** This section is the durable justification. **Do not re-open it without new measurement.**

The original brief proposed three axes with `A == B` as a *default coupling*. The catalog work below found that `A == B` is not a default — it is a **load-bearing invariant in 26 named places**. What follows is the evidence.

## 2.2 THE MIXED RISK REGISTER — 26 entries, what would break

Each entry: the coupling arithmetic and **the grep that finds it**. `u` = UI factor, `t` = text factor.

**Box ← Text** (a box constant that exists only to hold text of a given size)

- **R1 — Graphs legend text box.** `src\UiSpike.cpp` (grep `winW2 - 4` — two hits, both inside the `LEGENDFIX` block): the legend row's text rect is right-anchored at a raw `obj[9] == winW2 - 4` at **every** factor while the style goes 13 → 26pt. The measurement is recorded in the chart comment block (grep `currently wraps in 110`): 26pt "Expenses" needs ~113 px and "currently wraps in 110". **This is the bug that triggered this whole task.**
  > Settled facts (#57 closed v2.55.0):
  > 1. **The style is `ChartLabel` (`0xE9C86B5E`), not `Legend`** (byte-verified, `0x0076DD91`), so it goes 13 → **26** pt, not 13 → 24. `Legend` is the Data Views legend.
  > 2. The shipped cure is `CodePatches::ApplyGraphLegendBudgetScale` — 8 sites in the panel builder `sub_76D3D0` — which scales the **budget**, so the box is born wide. The v2.54.x rect patch that rewrote an output rect inside an unchanged 110 px budget was refuted and reverted.
  > 3. Every `file:line` citation in this document has since rotted outright, not by 13–21 lines (`tools\uimap\coverage-matrix.md` §0.9 *"Every line number in the pre-amendment reports is stale"* calls out the identical drift for its own file). The three spot checks recorded here — `kFontSizedIds`, `kAdviceListScaleSelfIds`, `kBmpxCityRoots` — were each repaired to a new number and each rotted again; all three now resolve only by name (§1.6). **Grep the symbol, do not trust the number.**
- **R2 — Graphs legend band height.** `src\UiSpike.cpp` (grep `w[0x120/4] == 32` — the born write is inside `ChartStoreThunk`, the reactive twin inside the `LEGENDFIX` block): `if (w[0x120/4] == 32) w[0x120/4] = RoundHalfUp(32 * f)`. The 32px band was sized to hold **one** 13pt line. Pure box←text, frozen constant.
  > The MEASURED cause of the observed wrap is the **72 px text box inside
  > the unchanged 110 px right-margin budget** (`sub_76D3D0`), not the band
  > height (`SC4-UI-ENGINE.md` §5.4.8). The band height may well also be
  > tight — UNKNOWN, and it is the same unknown as M6 (reference gap G33):
  > nothing has shown the band rect and the legend column to be the same
  > object. And the style is `ChartLabel`, not `Legend`.
- **R6 — Ordinance/deal popup height.** `src\UiSpike.cpp` (grep `stockPopH` — the declaration is the ordinance/plain ternary, the write is the `lround(stockPopH * pf)` two lines below): `wantH = lround(125.0 * pf)`. Rationale in the comment block above it (grep `cannot hold ONE line of Arta 28`): at 2x the box is 840x125 where `round(stock*f)` is 780x250, so the body lands 25px tall, *"which cannot hold ONE line of Arta 28"*.
- **R17 — Budget master column widths + forced text re-measure.** `src\UiSpike.cpp` (grep `capX`, and `45055` for the measurement comment above it): `capX/capW/monX/monW = lround({400,120,520,85} * mf)`, chosen so "45055/54727" stops clipping to "45055/54"; then `t->SetCaption(*cap)` (grep `if (cap) { t->SetCaption(*cap); }`) because the paint buffer was born at the old width. Box sized for text, then text forced to re-measure to the box — **both halves needed, neither sufficient**.
- **R18 — Neighbor Deals combo width.** `src\UiSpike.cpp` (grep `comboW`; the encoding argument is the comment above it, grep `sub_7798C0`): `comboW = lround(120.0 * spikeScaleFactor)`, gated on the exact stock width 120. Exists solely because "7000M" truncated. No byte patch possible — `lea edi,[edx+0x78]` inside `sub_7798C0` is a disp8 that cannot encode `120*f` for `f >= 1.07`. **A text-fit width with exactly one available lever.**
- **R21 — Budget slider track.** `src\UiSpike.cpp` (grep `int32_t off = 79, trackW = 110;`): raw `off = 79, trackW = 110`, position-only, unscaled. Structurally identical to the Graphs legend's 110 and the same failure shape.
- **R22 — Sub-flyout container height from item metrics.** `src\UiSpike.cpp` (grep `stripH = count*(cell 44 + gap 5) - 5` — the derivation block that opens the SUBBORN section) gives `H = max(count*(cell 44 + gap 5) - 5, 53) + 2*25`; the three provider constants are `src\CodePatches.cpp` (grep `kSubFlyoutProviderSites`) and the seven container fields are `kSubFields` (`src\UiSpike.cpp`, grep `kSubFields[] = {`). Not text (menu items are blits — grep `Menu items are BLITS` in the same block) but the same defect class, and `[0xE4] = 53` is simultaneously the bar width **and** the `IsPointInMe` claim width.
- **R25 — the DialogStatic corpus.** `tools\dialog-static\build_dialog_static.py` (grep `def scaled_area` for the rule and `if nd.area is not None:` for the walk that applies it to every `area=`), asserted by `verify_doubled` (grep `def verify_doubled` — it requires *exactly* `scale_len(v)`), plus the row/grid/tuple metrics (grep `drowheight`, `dbl_gridcol`, `dbl_tuple`). **Every one of these 261 boxes was hand-sized to hold a specific point size.** See §2.3 for the corpus numbers.

**Text ← Box** (a text metric derived from a box)

- **R7 — the popup wrap width, R6 running backwards.** `src\UiSpike.cpp` (grep `SetWinTextFlag(0x0002, true)` for the flag, `natW = body->GetW() - 10` for the wrap): word-wrap flag `0x0002` is turned ON and the engine re-wraps at `GetW() - 10` (335 at 1x, 680 at 2x, 1025 at 3x). **Box←text at `stockPopH` and text←box at `natW` in one block — the two greps land ~110 lines apart in the same function. Circular by construction.**
- **R8 — Tooltip wrap width (#41).** `src\CodePatches.cpp` (grep `kStockTipWrap` — the `= 250` declaration, then the `lround(kStockTipWrap * factor)` inside `ApplyTooltipWrapScale`; sites `kTipWrapSites`): `250` → `250 * factor` (push imm32). A hardcoded 250px wrap for tip TEXT inside a code-painted frame (Plot override `0x798710` — grep that address for the comment that names it); with 2x fonts the text wrapped narrow-and-tall and painted over the rounded-corner arcs. **A text metric scaled to preserve an art frame.**
- **R10 — Advice pane usable width is art-derived at runtime.** `src\CodePatches.cpp` (grep `sub_9BCBC5` — the comment block that records the derivation): the text class computes usable width as `GetW() - 2*gutter - scrollbarW` (`sub_9BCBC5` @ `0x009BCBC5`, gutter default 5 @ `0x009BFFCC`) and fetches `scrollbarW` **live** from the scrollbar window's own `GetW()`. Collapsed rows passed and expanded rows failed on a flat reserve — **the text wrap width is a function of an art width that appears and disappears.**

**Mixed residues** (a text column defined as whatever art columns leave behind)

- **R9 — Advice/news row column budget (#88).** `src\CodePatches.cpp` (grep `kAdviceRowMidSite` for the `0x79388F` site constant and `int ApplyAdviceRowScale` for the patch), patched over `83 EE 3D` @ `0x0079388F`: `S(f) = round(18*f) + 18 + 9 + round(16*f)`, and the headline column is the **residue** `pane->GetW() - S`. Four-way coupling in one constant: arrow glyph art, dismiss-X art, a flat 9px gutter, and the live scrollbar art width — with the TEXT column defined as what is left. Its precondition contract is declared in `src\CodePatches.h` (grep `PRECONDITION CONTRACT`, in the block above `ApplyAdviceRowScale`), and `src\Settings.h` warns the ini flag is **not** a safe kill switch (grep `spikeAdviceRowPatch`, then `NOT A SAFE KILL SWITCH` in its trailing comment).
  > Settled state (#136, v2.88.0): the old `kAdviceXScaleMaxFactor` fork is
  > gone. The constant still exists (`src\CodePatches.cpp`, grep
  > `kAdviceXScaleMaxFactor`) but it is **dead**: a whole-repo grep over
  > `.cpp/.h/.py/.ps1` returns the declaration and nothing else.
  > `ApplyAdviceRowScale` hardcodes `const bool xScaled = true;` (grep
  > `xScaled = true`) with `glyphX = glyph` (grep `glyphX = glyph`, the next
  > line), and the mirrored `FACTOR <= 2.0` filter was deleted from
  > `tools\selective-safe\build_selective_safe.py` in the same commit — that
  > file's only surviving mention is the comment recording the deletion
  > (grep `tail is GONE`). The imm8 was an ENCODING, not a law of nature:
  > when `S > 127` the patch rewrites the 19-byte window at `0x0079388B`
  > (grep `kAdviceRowWinSite`), folding `mov`+`sub esi, imm8` into
  > `lea esi, [eax - imm32]` and paying for the bytes with a store proven
  > dead by liveness (grep `proven dead` inside `ApplyAdviceRowScale`).
  > **SelectiveArt is therefore 655 entries at EVERY tier** — read straight
  > from the shipped DBPF index counts of the 2x, 1.5x and 3x packages
  > (655/655/655) and asserted in `_tests\Test-DatIntegrity.ps1` (grep
  > `z_SC4UIScale_SelectiveArt"` for the three `entries =` rows). **A 3x
  > package that is not equal to the 2x one is a regression, not the
  > design.** *(The 655 was the count when this was written; the 3x row's
  > trailing `# #136: was 651` comment has grown a further entry since, so
  > take the number from the gate, not from this paragraph — what is load-
  > bearing is that the three tiers agree.)*
  > **Warning:** the coupling is still hard, only its condition changed: if
  > the wide re-encode is ever removed or logs `advice row wide re-encode
  > REFUSED` (grep that string in `src\CodePatches.cpp`), the builder filter
  > **and** the 3x count must both go back to the pre-#136 651 in the SAME
  > build — art without the patch is the task-#88 defect. The
  > `kAdviceXScaleMaxFactor` trailing comment ("above this the X stays
  > stock") and `build_selective_safe.py`'s `SIXTEEN AT <=2x, TWELVE AT 3x`
  > block (grep that phrase) are stale source comments describing the
  > repealed rule.
- **R16 — Data Views legend pitch, quantised from measured text height.** `src\CodePatches.cpp` (grep `18 * ceil(h/18)`, the comment that records the derivation) + `src\CodePatches.h` (grep `ApplyDataViewLegendScale` and read the contract above it): the game advances each row by `18 * ceil(measuredH / 18)`, so a label that wraps to two lines gets a 72px slot; **the quantum 18 never scales**. We patch only the four ORIGINS (`src\CodePatches.cpp`, grep `kDataViewLegendLeaSites` and `kDataViewLegendImm32Sites`) and must never patch the pitch. The legacy `kDVPins` table (`src\UiSpike.cpp`, grep `kDVPins[] = {`) hard-codes pitch 18 and is documented ACTIVELY WRONG (grep `ACTIVELY WRONG` — one hit, in the block under the table) — measured 2026-07-31 09:32:19.577, it flattened the game's deliberate 72px gap after index 4 and dragged eight windows up by 36px.
- **R19 — Ordinance row insets, with a live under-scale clamp.** `src\CodePatches.cpp` (grep `kOrdinanceInsetSites`, then `kOrdinanceNameXImm8Sites` for the clamped pair): header/checkbox x 18→36 and row text/strip x 34→68, to clear 2x checkbox art and the eye glyph. But `{0x77CC23, 0x44}` and `{0x77D0E0, 0x44}` (grep either address) are the ordinance **name text x**, where stock-coherent 2x is 136 and `push imm8` caps at 127 — **a TEXT column position deliberately under-scaled to fit an encoding limit**, clearing the measured eye by only **~10px**. ⚠ *Corrected 2026-08-30: this row said the eye ends at "~104" and the clamp clears it "by 23px". Alpha-scanned (a>16) off the shipped row-strip sheets, per cell: stock `{46a006b0,140155b7}` 1320x18 inks cols 5..24 in a 330-wide cell, the 2x sheet 10..49 in a 660-wide cell, the 3x sheet 15..74 in a 990-wide cell; strip x is 34 / 68 / 102, so **the eye ends at 58 stock, 117 at 2x, 176 at 3x**. The recorded 104 was the 1x ink EXTENT laid at a 2x ORIGIN. The real margin is 127 − 117 = 10px — which is exactly the stock gap (name 68 vs eye end 58), so the clamp reproduces stock spacing and buys no headroom at all. Same source of error made the 3x figure understated: the label lands ~49px inside the eye, not 29.* **Warning:** that clamp is a live 3x hazard, and the margin is less than half what this row used to claim.
- **R20 — Slider-department builder column map.** `src\CodePatches.cpp` (grep `kDeptImm8Sites[] = {`: title x 20, "Monthly Expense" header x 18, category strip+eye rows x 18 on two paths, name column x 48, building-count x 258, sliders x 260 w 110, Subtotal x 250). Every named defect in that source block is an art-glyph-vs-text-column collision at a **single coupled factor**: the eye landing on "(eye)ealth", "Large Medical Cente7", the slider track running through "Parks and Recreation".

**Compounding / index couplings**

- **R11 — HTML size tables ↔ FontStyle popup clones.** `src\CodePatches.cpp` (grep `kHtmlFontSizeTable` and `kHtmlHeadingSizeTable` for the two `.rdata` addresses, `kPopupStyleRetargets` for the retargets, and `idx = (4*size+8)/18` for the comment that derives the coupling) + `tools\fonts\make_fontstyle.py` (grep `HTML_CLONE_BLOCK`; the same formula is restated in its header comment, grep `idx=(4*size+8)/18`). The popup builders derive an HTML size **index** from the `MessageHeader`/`MessageBody` **point size** (`idx = (4*size+8)/18`), so scaling the FontStyle size silently re-indexes the table and **compounds to 4x**. The cure is four `push <guid>` retargets onto stock-size clone styles. **Warning:** the generator FATALs if the clones are missing (`tools\fonts\make_fontstyle.py`, grep `FATAL: %s missing from generated output`) — after they were hand-added post-generation for five weeks (a Law-45 scar).
- **R12 — Credits HTML LTEXT size map keyed by the UI tag.** `tools\dialog-static\build_dialog_static.py` (grep `credits_maps`):
  ```python
  credits_maps = { "":    {"2":"1","3":"2","7":"5"},   # 2x   -> 16/20/36 pt
                   "15x": {"2":"1","3":"2","7":"6"},   # 1.5x -> 12/15/36
                   "3x":  {"2":"1","3":"2","7":"3"} }  # 3x   -> 24/30/36
  ```
  Index remaps calibrated against the table `ApplyHtmlSizeScale` produces at the runtime factor, but **selected by the package tag**. At `u=2, t=3` the file ships the 2x map while the table is `stock×3 = {24,30,36,42,54,72,108}` → indexes 1/2/5 resolve to **24/30/72 pt instead of the approved 16/20/36** — the title doubles. The source comment immediately above `credits_maps` records that the *previous* maps compounded exactly this way once. Plus the column widths (grep `def bump_width`): the credits table `width="N"` is scaled by `scale_len` (u) while the text in those columns is sized by the HTML table (t) — the mid-word wrap ("Compose/rs" — grep `Compose`) the comment describes, reintroduced. **This is the cleanest concrete instance of "the asset silently assumes font factor == UI factor".**

**Couplings with NO independent lever at all** (call these out for #54)

- **R4 — the Graphs tick gutter, the inverse coupling.** `src\UiSpike.cpp` (grep `THREE LEVERS, THREE REFUTATIONS` — the ledger, and the comment block it closes is the whole citation): the plot's left gutter (45) is described by the game as text-derived, but **measured INVARIANT to the font** — 10pt and 20pt both produced `PLOT(45,20,866,492)` byte-identical (grep that string — two hits, one per font size), because the plot rect is computed once per chart object and nothing re-arms its sentinel. Text scaled; the box refused to follow. **Three levers, three refutations, all recorded in place.** A few lines above the ledger the comment states the honest lever *would have been* to scale the text and let the game re-derive (grep `the honest lever is to scale the TEXT`) — and the paragraph after it records that it does not work (grep `AND THAT SECOND THEORY DIED TOO`).
- **R13 — the ticker marquee: width and height on different mechanisms.** `src\UiSpike.cpp` (grep `kAdviceListNeverTouchIds[] = {` for the list, `0xAA12F33C` for the marquee entry, `IsAdviceListNeverTouchId(` for the consumer) + `tools\selective-safe\build_selective_safe.py` (grep `id=0xaa12f33c` — **two hits**: `main()` and its `carbon_transform_script` twin, which the file's own comment marks *"IDENTICAL to main()"*; every builder anchor below likewise appears once per path). SelectiveArt writes `area=` from THREE live mechanisms, not one: (1) `double_subtree_areas` (grep `def double_subtree_areas`) scales every DESCENDANT of TEN roots — advisor `0x6a15c767`, budget `aa3ac002`/`ca4c332d`/`aa3ac001`/`aa3ac000`, Graphs `8a8b5b71`/`8a8b5b72`/`0a4a8176`, U-Drive-It dashboard `4bcb938a`, console variant `ec1a5cbf` (grep `double_subtree_areas(new_text` for the call set, and each root id for its own block); (2) `seat_faces_on_apertures` (grep `def seat_faces_on_apertures`, called on `ADVISOR_FACE_SEATS`) translates the 7 faces in both advisor scripts — asserted a no-op at integer factors and exactly 7 at 1.5x (grep `THE NO-OP AT AN INTEGER FACTOR IS ASSERTED` and `seat pass moved`); (3) the marquee, an INLINE `widen_marquee` closure (grep `def widen_marquee`) — NOT `double_one_window_area` (grep `def double_one_window_area`), which is DORMANT with zero call sites since the #89 dock form was reverted (grep `DO NOT DATA-DOUBLE ANYTHING IN THE HUD DOCK`), as is `parity_nudge_btn_areas` (grep that name; reverted per `THE PARITY NUDGE WAS CALLED HERE AND IS REVERTED`). The marquee is the only `area=` edit that touches WIDTH ALONE — `(l, t, l + scale_len(r - l), b)` inside `widen_marquee`, leaving top and bottom untouched; `double_subtree_areas` and `double_one_window_area` scale all four coordinates. **Warning: the builder's own comments are wrong about this** (grep `never area=` and `deliberate exception to`) — believing them is what let #170 sit undetected, because `0x6A15C767` is in `kDataScaledSubtreeIds` so `ScalePanelRoot` RETURNS before the child loop (`src\UiSpike.cpp`, grep `IsDataScaledSubtreeId(win->GetID())`): the runtime sweep never walks the advisor buttons, and their shipped geometry comes from `double_subtree_areas` ALONE. The width ships baked in the `.UI` because the game re-imposes cached geometry every roll tick; the height is font-derived (*"3 × lineHeight of the 2x AdvisorHeadline"* — `src\UiSpike.cpp`, grep `lineHeight of the 2x AdvisorHeadline`, the comment directly above `kAdviceListNeverTouchIds`); the items are game-sized to the marquee. **Neither half is reachable at runtime, by design.**
- **R24 — Establish City `0x6A414973`: box and text cannot be separated at all.** `src\UiSpike.cpp` (grep `0x6A414973` — one hit, its entry inside `kNeverScaleIds[] = {`; the rationale is the comment block a few lines above it, grep `wrong colour (purple)`): runtime geometry scaling renders its `GZWinText` nodes in a **wrong colour (purple)** while TextEdit and button captions stay black, because *"runtime geometry scaling does not carry the text/art path the way a doubled .UI does"*. The whole subtree is handed to the static dat. **The only entry in this register with no runtime lever whatsoever.**

**List memberships justified by a text fact** (the "skip-lists rot" shape, aimed at the feature)

- **R14 — `kFontSizedIds`, 23 controls whose size is owned by their content.** `src\UiSpike.cpp` (grep `kFontSizedIds[] = {` for the list, `IsFontSizedId(win->GetID())` for the one consumer, inside `ScaleSubtree`) — position scaled, `SetW`/`SetH` deliberately never called. One is genuinely font-derived (`0xCBC61559` "Change style every"); 21 are `GZWinSpinner`s that size themselves from the `{46a006b0, 82b99d9d}` arrow strip. Recorded failures when slot and content disagreed: a 263x32 2x caption doubled to 526x64 and sat ~16px below its fixed-size siblings; a spinner at 60x72 clipped its DOWN arrow inside a 98x44 parent FlatRect. **At UI 2x / Text 1x these 23 stay 1x-sized but get moved to 2x coordinates → holes. At UI 1x / Text 2x they overflow their parents. This list is *definitionally* `UI == TEXT`.**
- **R15 — `kAdviceListScaleSelfIds`, recursion deliberately disabled.** `src\UiSpike.cpp` (grep `kAdviceListScaleSelfIds[] = {` for the list, `IsAdviceListScaleSelfId(win->GetID())` for the consumer, also inside `ScaleSubtree`). Items are game-sized to the container (`SetArea(0,0,GetW,GetH)` at item-create `0x7931F1`) while their TEXT is HTML sized by R11. **If the HTML ever outgrows the container there is no lever left, because recursion is off.**
- **R23 — News reader `0xAA231508`.** `src\UiSpike.cpp` (grep `0xAA231508` — the first hit is the justification comment, the second is its entry inside `kAlwaysScaleCityIds[] = {`; grep `content pane is sized from the 2x FONTS` to land on the sentence itself): *"its content pane is sized from the 2x FONTS and always renders large, so a frame left at 1x gets a hugely oversized pane inside it."* The geometry cure (pre-scale while hidden) is correct **only for as long as that text fact holds**.

**The law behind four apparent no-ops**

- **R3 — Graphs legend swatch re-hang.** `src\UiSpike.cpp` (grep `rowTextL1 - RoundHalfUp(gap0 * f)`; the `LEGENDSWATCH` log line a few lines below is the same block): `obj[2] = rowTextL1 - RoundHalfUp(gap0 * f); obj[4] = obj[2] + RoundHalfUp(sw * f)`. The colour swatch has **no gutter of its own** — its position is derived from the TEXT box left edge and its own 1x-era gap. Measured, the swatch is not an independent half of anything: the whole column is a **six-constant right-margin budget** owned by the PANEL builder `sub_76D3D0`, and the pair that must ship together is *budget strip ↔ plot right margin*, not *swatch ↔ text box*. The `UiSpike` rect hooks were rewriting outputs inside an unchanged 110 px budget (law 49); the shipped cure patches the budget itself so the column is born at `f`. See `_tests\REGRESSION.md` → *CHART LEGEND MATH (#57)* and *LAWS AUDITED AGAINST #57*.
- **R5 — `SIZE_SQUEEZE` ↔ the legend rect widening.** `tools\fonts\make_fontstyle.py` (grep `SIZE_SQUEEZE = {"Legend": 0.92}` for the constant, `SIZE_SQUEEZE.get` for the application) paired with the `winW2 - 4` legend rect in `src\UiSpike.cpp` (R1). The TEXT is shrunk 8% to fit a box; the BOX is separately widened by 4px in C++. **One coupled pair split across a Python generator and a runtime hook, with nothing asserting they still agree.** At `t ≠ u` the squeeze multiplies `t` while its partner multiplies `u`: the pair silently unpairs. Law 43 violation by construction. Settled scope: the squeeze is on style **`Legend` (`0xE9C86B5F`)**, which is the **DATA VIEWS** legend (`0x007A0747`). The GRAPHS chart pushes **`ChartLabel` (`0xE9C86B5E`)** at `0x0076DD91` — byte-verified — so `SIZE_SQUEEZE` **has never applied to the chart at all**, and every calculation that assumed the chart renders at the squeezed 24 pt was reading the wrong style (it renders at ChartLabel's raw 26 pt at 2x). The 8 % the squeeze was invented to buy is the same ~6 % that law 48 explains properly: ink grows **x2.13** per doubling (n=17, mean 2.130, sd 0.026), not x2.00. (2.121 is one string's ratio, `Income` 33->70, not the population mean.)
- **R26 — the gauge dial dest-rect snap, and the governing law.** `src\UiSpike.cpp` (grep `GaugeCtxBltThunk` for the thunk, `sourceIsOneX` for the snap rule): `dst = cw * m` with the same fit clamp, plus a snap to 1.0 when the source is judged still-1x. *(Citation note: the rule this entry was written against was the **relative** test `m < 0.75f * gGaugeScale`. #186 replaced it with the absolute `sourceIsOneX` / `kFitSlack` form; grepping the old expression now lands only in the comment that records its retirement. The coupling this entry is about is unchanged.)* Listed because it is the third instance of the law behind R17 / R7 / R22: **the window rect and its CACHED PAINT BUFFER are a coupled pair, and the buffer is born at first-paint size.** Every box-vs-content fix in this register that looked inert (v2.50.0 / .51.0 / .52.0 on the chart) failed on **this law, not on its arithmetic**. *Prove the REPAINT before you tune the VALUE.* Bounded by #57: law 46 held for the gauges and still holds here, but it was **not** why the chart patches failed. The chart is destroyed and rebuilt on every graph switch (`0x0076D3DA-0x0076D409`), so its repaint was never in doubt; the blocker sat **upstream of the repaint** — the value being repainted came out of a right-margin budget nobody had read. Once the repaint is proven, ask **who COMPUTES** the value, not only who paints it (law 49).

## 2.3 The corpus measurement — the lock is cheap, and splitting is not

`[M]` Corpus: **2537 controls** carrying both an `area=` and a resolvable `font=`, across **215 of the 331** winning `.UI` scripts; **128 distinct (box-height, style) pairs**. Ratio = box height ÷ 1x point size.

**Stock distribution:**
```
min 1.00   p5 1.29   p25 1.38   median 1.38   p75 1.82   max 16.00
1351 controls (53%) sit below ratio 1.50
```
Restricted to the 49 hand-listed `dialog-static` TARGETS (310 controls): `min 1.17, p5 1.38, median 1.62`.

**Cost of the 1:1 lock — what we actually ship:**

| factor | min box:pt ratio | median | pairs whose ratio DROPS vs 1x | worst drop |
|---|---|---|---|---|
| 1x (stock) | 1.000 | 1.385 | — | — |
| **1.5x** | **1.000** | 1.350 | **75 / 128** | **−2.94%** |
| 2x | 1.000 | 1.385 | **0 / 128** | 0 |
| 3x | 1.000 | 1.385 | **0 / 128** | 0 |

Worst case is `PUckDate` 11pt (→17 at 1.5x, ×1.5455) inside an even-height box (×1.5000). **The corpus minimum never falls below the tightest shape the game ever shipped (1.000).** The 1:1 lock is exactly safe at f=2 and f=3 and costs ≤2.94% at f=1.5 — another face of task #75's unresolved 1.5x rounding divergence.

**Cost of splitting, at the modest `u=2, t=3`:** every ratio multiplies by `u/t = 0.667`. The corpus **median 1.38 becomes 0.92 — below the tightest shape the game ever shipped — and 53% of all text controls land under 1.00.** That is not an edge case; it is the modal control. Named victims:

| Asset | Baked constant | Source | At u=2 / t=3 |
|---|---|---|---|
| Building Style Control button | `h=16`, `MessageHeader` 16pt (ratio **1.00**) | `…I-6bc61f19.ui` | 32px box, 48pt text → **0.67** |
| Budget ledger lines (×11) | `h=15`, `BdgtLedgerLineLite` 14pt (1.07) | `…I-cbc3c2b9.ui` | 30px box, 42pt text → **0.71** |
| Select A Bridge header | `h=21`, `GenHeader` 18pt (1.17) | `…I-ebd0d36c.ui` | 42px box, 54pt text → **0.78** |
| Establish City body rows (×3) | `h=16`, `GenBodyMedium` 13pt (1.23) | `…I-2a41436b.ui` | 32px box, 39pt text → **0.82** |
| Audio Options playlist | `drowheight=20`, `ListBoxItem` 13pt (1.54) | `…I-ca53f06e.ui`, scaled by `build_dialog_static.py` (grep `drowheight`) | 40px row, 39pt text → **1.03** |
| Audio Options song column | `wingridcol="1,1,200"` | `build_dialog_static.py` (grep `dbl_gridcol`, which rewrites every `wingridcol=`) | 400px column chosen for 26pt text, holding 39pt |

## 2.4 The upstream blocker, for completeness

Even if the runtime were split, the **package system cannot express it.** `ScaleTier::kPackages` (`src\ScaleTier.cpp`, grep `kPackages[] =`) enables exactly **one whole package per factor**, and `SyncStaticLayers` (grep `void SyncStaticLayers`) selects the art dat and `FontStyle<tag>.ini` with the **same tag** — inside that function, grep `SyncDat(docPlugins, L"z_SC4UIScale_SelectiveArt"` for the art half and `SyncFont(docPlugins` for the font half, both fed the one `activeTag`. Tier eligibility is gated on the **art** dat existing (grep `bool PackageInstalled`). An independent text axis needs a second tag dimension, a font-source gate independent of `PackageInstalled`, and a doubled `kThirdPartyDeps` table (grep `kThirdPartyDeps[] = {`).

## 2.5 Verdict of record

Splitting UI from TEXT would **manufacture the task #41 (tooltips), #42 (news box) and #57 (Graphs legend) defect family deliberately, everywhere, on purpose**. Two entries (R14/M1, R6+R7/M2) have **no independent formulation at all**; three more (R8, R9, R11) are byte patches applied once at `PostAppInit` and cannot be re-derived per axis without redesigning `CodePatches`; five (R13, R15, R23, R24, and the `kNeverScaleIds` premise) are **id-list memberships whose justification is a text fact** — the "skip-lists rot" failure mode aimed squarely at the feature.

**Locked 1:1. Settled.**

*If a future reader still wants a text knob, the only defensible shape is a **bounded** one — `t ∈ {u·0.92 … u·1.0}` — and the existing, currently-empty `KEEP_STOCK` set (`tools\fonts\make_fontstyle.py`, grep `KEEP_STOCK = set()`) is its natural mechanism: it is the working precedent for "styles whose box is A-scaled but whose text must not follow". A free axis is refused.*

---

# 3. THE UDI AXIS

## 3.1 What the bubble is — measured, not inferred

`[M]` It **is** a real `cIGZWin`. The probe (`src\UiSpike.cpp`, grep `void UiSpike::EdgeProbeTick` — the `EDGE bubble 0x48E945B4` log pair at its tail) reports:
```
UiSpike: EDGE bubble 0x48E945B4 PRESENT | rect (1637,610 128x128) vis=1 vt=00ADF6A0
```
`0x00ADF6A0` is the **GZWinBMP** class that the BMPX hook already serves. It parents **straight to the 3D view** `0x9A47B417`, which is why every static (`.UI`-based) approach missed it — it has zero `.UI` references and is code-bound (`tools\selective-safe\build_selective_safe.py`, grep `pushed beside the window id at VA` — the U-Drive-It block inside `CODE_BOUND_TGIS`).

`[M]` The #46 log line `(1284,755 32x32) -> (1268,739 64x64)` is **centre growth**, a signature only `ScalePanelRoot`'s centre branch (`src\UiSpike.cpp`, grep `cMinX` inside `UiSpike::ScalePanelRoot`) produces — confirming it is a direct view child, not renderer-drawn and not deeper in the tree.

**It has no text.** It is a single-image leaf, hooked as a root with **no BMP children** (`src\UiSpike.cpp`, grep `U-DRIVE-IT MISSION MARKER` — its lone `0x48E945B4` entry at the tail of `kBmpxCityRoots`). No font style is involved at any bubble factor. **The TEXT axis is orthogonal to the bubble axis, for free.**

## 3.2 The mechanism — three multipliers stack

1. **Art:** stock `T-856ddbac_G-46a006b0_I-094ac89a.png` is **32×32** (`tools\dbpf\extracted\SimCity_1\`); SelectiveArt stages it at the tier factor → **48 / 64 / 96** for 1.5x / 2x / 3x. `[M]` (verified by reading the PNG IHDRs in `tools\selective-safe\stage`, `stage-15x`, `stage-3x`)
2. **Window:** the exe path at `0x4B82F0` loads the art, `GetRect`s it, centres it on the world anchor and `SetArea`s the window to it — **the window is born art-sized** — then the blanket city sweep scales it by `f` (the `ScalePanelRoot` call site in `UiSpike::ScalePanelsUnder` — `src\UiSpike.cpp`, grep `ScalePanelRoot(p.win`).
3. **Draw:** GZWinBMP's plain path sets `dst = src` (it never reads the window rect); `BmpCtxBltThunk` (`src\UiSpike.cpp`, grep `int __fastcall BmpCtxBltThunk`; the fit reduce is the `float m = gBmpScale;` block a few lines into it) multiplies dst by `gBmpScale` and then **reduces it until it fits the live window**:
   ```
   m = gBmpScale;  if (w*m > winW) m = winW/w;  if (h*m > winH) m = winH/h;
   ```

**Therefore the shipped law is `drawn = 32·f²`.** `[M]` Corroborated by the live log line (2026-07-31, ×8):
```
BMPX draw id=0x48E945B4 img 64x64 win 128x128 -> dst 128x128 (x2.00)
```

## 3.3 THE FINDING THAT MUST NOT BE SOFT-PEDALLED

| tier f | art | window | **drawn (shipped law `32f²`)** | vs stock | **user's rule `32·2f`** |
|---|---|---|---|---|---|
| 1 | 32 | 32 | 32 | 1× | — |
| 1.5 | 48 | 72 | **72** | 2.25× | **96** — we are **25% under** |
| 2 | 64 | 128 | **128** | 4× | **128** — exact match |
| 3 | 96 | 288 | **288** | 9× | **192** — we are **50% over** |

**The user's "assumed approach" (`bubble = 2 × UI`) is already shipped at the shipped tier — by arithmetic accident.** The two laws coincide at **exactly one point, f = 2**, which is the only tier anyone runs. Nobody could have seen the divergence because nobody runs 1.5x or 3x. *This is the "2x hides rounding bugs" scar in a new costume.*

**Implementing the user's rule is a deliberate BEHAVIOUR CHANGE at 1.5x (72→96) and 3x (288→192), not a new feature.** It must ship as such in the three `VERSION-HISTORY.txt` files, and `_tests` needs an assertion pinning `drawn = 32·B` so the two laws can never diverge silently again (§5.3).

## 3.4 Feasibility verdict

> ### **FEASIBLE — an independent bubble factor is sound, with named constraints.**

Reasons:
- The bubble is a real `cIGZWin` on a mechanism we already own end to end.
- **The required per-element multiplier for the default `B = 2·UI` is the constant 2 at every tier** — the same ratio that ships and is user-confirmed today at 2x (#60). Zero-regression default.
- **No new art, no new font style, no new package** is needed for the default: stretch delivers it.
- **Clipping imposes no limit:** the parent is the full-screen 3D view, so an enlarged bubble structurally cannot overflow its parent; only the screen edge bounds it.
- **The hit box follows for free.** Its hit box *is* its window rect, and the fit clamp guarantees `drawn ≤ window` — so the sprite can never outgrow its hit box, **provided the window is scaled before the blit**. The current call order already does this: the panel loop in `UiSpike::ScalePanelsUnder` (`src\UiSpike.cpp`, grep `ScalePanelRoot(p.win`), then `HookRuntimeBmpsUnder` (grep `kBmpxCityRoots`), draw later still. (Law 43 satisfied by construction, not by luck — but state it, because reordering those calls would break it.)

**The three constraints:**

1. **`gBmpScale` must become per-id.** It is one global (`src\UiSpike.cpp`, grep `float  gBmpScale`) set once per pass for all 12 roots (assigned at the head of `HookRuntimeBmpsUnder`; the root list is `kBmpxCityRoots`: eight My Sims roots, three Graphs roots, one UDI marker). Without this, **every My Sims portrait takes the bubble factor too.** The lookup has a free home: `gBmpCurId` is already computed inside `BmpDrawThunk` (`src\UiSpike.cpp`, grep `gBmpCurId = w->GetID()`) `[M]`.
2. **The bubble's window scale must bypass `ScalePanelRoot`'s generic anchor and grow unconditionally about its centre.** `ScalePanelRoot` only grows about the centre when the panel sits more than `frameW/4` (600px at 2400) from **both** side edges and `frameH/4` (400px) from top and bottom (`src\UiSpike.cpp`, grep `cMinX` inside `UiSpike::ScalePanelRoot`). The #46 measurement is centre growth, but the **#60 sighting at (1637,610) had only 635px of right-hand gap — 35px of margin.** `[M]` Any marker inside that quarter-screen edge band instead takes `newX = ScaleRound(gapL, f)` (grep that expression), which multiplies its **position** and detaches a world-anchored sprite from its mission site; the on-screen clamp a few lines below it (grep `clampX && gapR >= 0`) then shoves it further. **This is a live hazard at today's factor, independent of the knob, and it gets no worse with B — but a bubble-specific window scale must not inherit it.**
3. **The ini key needs its own section.** The live-tune re-read (`src\UiSpike.cpp`, grep `LiveTuneIniPath` — the `[UiSpike] LiveTune` poll block inside `UiSpike::ScaleGodFlyouts`) parses `[Disaster]`/`[Flyout]`/`[Probe]` by section with explicit keys — a `[UDriveIt]` section cannot be swallowed. A new namespace-scope mirror must repeat the `src\UiSpike.cpp` tier-mirror audit (grep `gTierF mirrors settings.spikeScaleFactor`) (§0).

**One rounding note.** Today `m = gBmpScale` and `winW/artW` are **exactly equal**, so the draw sits on the fit-clamp knife edge. At `f = 1.5` the edge-derived `ScaleRound(l+48, 1.5) - ScaleRound(l, 1.5)` can land **71 rather than 72** depending on `l`, silently clamping `m` to 1.479. `[INF]` — the arithmetic is certain, the specific `l` values in play are not measured. **Mitigation:** set the window from `round(32·B)` first, then compute the blit multiplier **from the live window** (`m = winW / artW`) rather than from a factor, and log when they differ by more than 0.01 (§4.4).

## 3.5 The ceiling

> **`B ≤ 2 × UI`, i.e. drawn 96 / 128 / 192 px at UI 1.5 / 2 / 3. ART sets that ceiling — not clipping, not a bounds check.**

Layered, in the order the limits actually bite:

1. **ART is the only real limit.** The tier packages stage the bubble at `32f` `[M]`. The only other bubble art that exists anywhere in the repo is `32·2f` (§3.6). Above `B = 2f` every pixel is nearest-neighbour block replication at ratio `B/f`. At `B = 2f` that ratio is exactly 2 — precisely what ships at UI 2x today and is user-confirmed. **Above it, nothing has been seen by anyone.**
2. **CLIPPING sets no limit** (parent is the full-screen 3D view).
3. **The imagerect-fits-image guarantee is NOT in play.** `BmpDrawThunk` skips EDGE/9-slice mode entirely (`src\UiSpike.cpp`, grep `if (!edgeMode && gBmpScale > 1.01f)`) and the plain path is gated on `w == sw && h == sh` (grep that expression in `BmpCtxBltThunk`). The bubble draws through the **plain** path — the live log line proves it.
4. **The hard mechanical stop** is `ScalePanelRoot`'s double-scale guard (`src\UiSpike.cpp`, grep `double-scale guard` inside `UiSpike::ScalePanelRoot`): `newW > frameW || newH > frameH` skips and tombstones. With `drawn = 32·B` against a 2400x1600 frame that is `32B ≤ 1600`, i.e. **B ≤ 50**. It fails **safe** (window left exactly as the game made it, one log line, no crash) and is nowhere near the useful range. **It is an assets/sanity ceiling we are choosing, not a crash ceiling — say so in the ini comment so nobody "fixes" it later.**

## 3.6 Exactly which art builds do not exist yet, and their cost

`[M]` **The 4x and 6x bubble art already exists in the repo, and is byte-reproducible in one command:**

```
sha256 1eb12941…e549c  tools\selective-safe\bubble4x\T-0x856ddbac_G-0x46a006b0_I-0x094ac89a.png   128x128,  990 B
sha256 1eb12941…e549c  Upscale2x.exe dbpf\extracted\SimCity_1 <out> --factor 4  (same TGI)        ← IDENTICAL
sha256 4cc62e02…2330a  tools\selective-safe\bubble4x-3x\…094ac89a.png                             192x192, 1712 B
sha256 4cc62e02…2330a  Upscale2x.exe … --factor 6                                                 ← IDENTICAL
```

So the premise "the 4x and 6x art needs building" is **half wrong, in the useful direction**. What does **not** exist is a shippable **dat** carrying them.

**Warning — `[M]` the 1.5x-tier bubble source in the repo is WRONG — it is a double-resample.** `bubble4x-15x\…094ac89a.png` is 96x96, and so is a direct `--factor 3` from the 1x master, but **they are different files: 510 of 9216 pixels (5.5%) differ.** `bubble4x-15x` was built as `--factor 2` over the *1.5x NN output*, inheriting the 1.5x 2:1 stipple and then doubling it. The correct source is a **direct `--factor 3`**, which already sits at `tools\upscale\preview-3x\SimCity_1\…094ac89a.png` (sha `12d360ad…45a1`).

| Deliverable | Exists? | Cost |
|---|---|---|
| bubble art @ absolute **3x** (UI 1.5 × 2) | yes — `tools\upscale\preview-3x\…094ac89a.png` — **use this, NOT `bubble4x-15x\`** | 0 |
| bubble art @ absolute **4x** (UI 2 × 2) | yes — `tools\selective-safe\bubble4x\` (verified ≡ `--factor 4`) | 0 |
| bubble art @ absolute **6x** (UI 3 × 2) | yes — `tools\selective-safe\bubble4x-3x\` (verified ≡ `--factor 6`) | 0 |
| a **shippable dat** carrying any of them | **none, at any tier** | **~1.2 KB and <1 s each** |
| a `SyncDat` base name for it | no — `src\ScaleTier.cpp` issues exactly 7 (grep `SyncDat(` inside `SyncStaticLayers` and count; §5.5 records this count moving since) | one line |
| an ini key / Settings field / mirror | no — zero hits for bubble/udi/udriveit in `Settings.h`, `Settings.cpp`, `ScaleTier.cpp`, `SC4UIScaleDllDirector.cpp` `[M]` | §4 |

**A bubble-only package is one TGI: ~1.2 KB, <1 s to build, no upscale-tree run at all.** Five advertised absolute factors ⇒ **~6 KB for the entire bubble axis, all tiers.** Compare a full tier `[M]`: factor 4 = 18.8 s upscale / 66 MB tree / ~20 MB dat `[INF]`; factor 6 = 35.0 s / 113 MB / ~27 MB `[INF]` — plus DialogStatic, ItemIcons, ItemIconsSub, three third-party dats and a FontStyle. **Four orders of magnitude apart.**

**Three facts make the bubble the ONE asset in this project that may legally be over-scaled relative to its tier:**
1. **It has zero `.UI` references** (code-bound — `tools\selective-safe\build_selective_safe.py`, grep `U-DRIVE-IT mission bubble` inside `CODE_BOUND_TGIS`), so there is no `imagerect` to keep in step with the pixels — the rect≤art invariant is **vacuous** for it. Every other TGI over-scaled past its tier would break that invariant immediately.
2. Its parent is the full-screen 3D view, so nothing clips it.
3. Precedent exists for a 1–3 entry root package: `WebText` (3), `SaveWarningUI` (2).

**Load order:** `z_SC4UIScale_UdiBubble-*.dat` sorts after `z_SC4UIScale_SelectiveArt-*.dat` (`U` > `S`) and root files load in order, later wins (`docs\PACKAGE-MANIFEST.md` §"Load-order law" — the rule moved out of `README.md`, which no longer carries a package table or a load-order section). It therefore beats the tier's own `32f` staging. No `zzz-` subfolder needed — no mod overrides this TGI.

**Law: sharp art is a coupled TRIPLE, not a pair.** Shipping `UdiBubble-4x` **also** requires taking `0x48E945B4` off the stretch multiplier (or moving it to `kNeverScaleIds`), or you get `32·2f·f`. Ship all three or none.

## 3.7 A refuted lead is still written down as fact

`src\UiSpike.cpp` (grep `THE U-DRIVE-IT MAP MARKER` — the comment block that
opens "the 4x-art attempt at {46a006b0, 094ac89a} shipped in v2.25.17 and did
nothing") and `_tests\REGRESSION.md` §"TWO DEAD LEADS, both closed — do not
re-walk" assert that `{46A006B0, 094AC89A}` **"is not the marker"**. But stock art is
32x32, our tier-2 stage is 64x64, and the live draw reports `img 64x64` —
**the marker is drawing our staged copy of exactly that TGI.** The 2026-07-30
withdrawal rested on a **null** (the user reported "blue map circles
unchanged"; the note itself admits the "!" bubble may have gone 4x
unobserved). *NULL IS NOT EVIDENCE.*

**Settled:** the TGI IS the marker's art. It shipped via `CODE_BOUND_TGIS`
(v2.21.4) together with the 15-glyph mission table at VA `0x44DEC7`; the
one-line adjudicator was `BUBBLE_OVERRIDE_ENABLED` in
`tools\selective-safe\build_selective_safe.py` (grep the name) (rebuild, read
whether `BMPX draw id=0x48E945B4` says `img 128x128`).

The general lesson stands: `tools\selective-safe\bubble4x*\` was armed dead
plumbing behind one Python boolean with a live copy path in the
`elif (BUBBLE_OVERRIDE_ENABLED …)` branch immediately below it (grep
`ART OVERRIDE %08x/%08x staged`) —
the exact shape Law 45 warns about ("if the generator's output is not the
shippable file, it will eventually ship"), one flag from shipping.

---

# 4. THE SETTINGS SURFACE — TWO KNOBS

## 4.1 Shape

```
KNOB 1: UI scale      1.5 / 2 / 3        (text follows 1:1, always)
KNOB 2: Bubble scale  auto (= 2 x UI) or an absolute factor
```

Two edits to the existing ini: a comment block and one new key meaning in `[UiSpike]`, plus one new section `[UDriveIt]`. **No key is renamed or removed.**

**Law: file format is non-negotiable: ASCII, CRLF, no BOM.** All three shipped `SC4UIScale.ini` copies are CRLF/no-BOM, first bytes `3b 20 53` (`; S`) `[M]`. *(Housekeeping: the one non-ASCII warning glyph in a comment in the preview ini should be ASCII-ised when this lands — a non-ASCII byte in a non-BOM ini is read as ANSI and is pure risk for zero benefit. **Citation retired:** `dist\SC4UIScale-preview\SC4UIScale.ini` no longer exists and `dist\` is untracked, so git cannot date its removal; the only tracked ini today is `_packaging\SC4UIScale.ini`, which is CRLF / no-BOM and byte-checked clean of non-ASCII.)*

## 4.2 `AutoScale` becomes tri-state

`0` and `1` keep their **exact current meanings**, so no existing file changes behaviour. `2` is new and is what a settings GUI writes.

| value | meaning | `ScaleFactor` | `SyncStaticLayers` runs? |
|---|---|---|---|
| `1` | **auto (default)** — resolution decides | ignored, overwritten | yes |
| `2` | **user choice** — `ScaleFactor` is the *request*, validated + clamped | authoritative (subject to clamp) | **yes** |
| `0` | manual, **diagnostic** — legacy meaning, unchanged | verbatim, unvalidated | **no** (packages left as-is) |

**Warning: `AutoScale=0` is a footgun and a GUI must never write it** — the runtime factor moves and the packages do not, producing 2x art under a 3x runtime, the exact shape the whole tier system exists to prevent. Keep it documented as diagnostic-only.

## 4.3 The ini — default case (what ships)

```ini
[UiSpike]
; ---- KNOB 1: UI SCALE -------------------------------------------------
; AutoScale = 1  pick the UI scale from the game resolution (fit function)
;                and gate the matching data package. ScaleFactor ignored.
;             2  USE ScaleFactor BELOW as the requested UI scale, and gate
;                the matching data package to it. This is what a settings
;                GUI writes. Validated: an unbuilt or too-large request is
;                CLAMPED DOWN and the clamp is logged, never silent.
;             0  manual/diagnostic: ScaleFactor is used verbatim and the
;                data packages are NOT touched. Mismatched art is on you.
AutoScale=1
; ScaleFactor: the UI scale. Supported values 1.5, 2.0, 3.0 (one built
; asset package each). Only read when AutoScale=0 or 2.
ScaleFactor=2.0
;
; ---- TEXT SCALE: THERE IS NO KEY, AND THERE WILL NOT BE ---------------
; Text is LOCKED 1:1 to the UI scale. UI 2.0 => fonts 2.0, always.
; This is not a simplification, it is a correctness requirement: 26 places
; in this mod size a BOX from a FONT or wrap a FONT to a BOX (ordinance
; popup height, tooltip wrap, advice row column budget, Graphs legend band,
; the whole DialogStatic corpus). Half of all stock text controls sit at a
; box:point ratio under 1.5, so a text factor 1.5x above the UI factor puts
; the modal control below the tightest box the game ever shipped.
; See tools\research\SCALING-AXES.md section 2.
; A "TextScale" / "FontScale" / "TextFactor" key here is IGNORED and logged
; as REJECTED.

[UDriveIt]
; ---- KNOB 2: U-DRIVE-IT MISSION BUBBLE --------------------------------
; The in-world mission MARKER only (window 0x48E945B4, the round pin over
; a mission site). The driving dashboard, the Car Control panel and the
; vehicle/pedestrian pickers are ordinary UI chrome and follow the UI
; scale - this key does NOT touch them.
;
; BubbleScale = auto     2 x the UI scale (DEFAULT). At UI 2.0 that is
;                        4.00 -> drawn 128 px, which is exactly what
;                        v2.36.6 already ships. Changing the UI scale keeps
;                        the 2x relationship.
;             = <number> an ABSOLUTE factor over the 32 px stock art:
;                        drawn size = round(32 * BubbleScale) px.
;                        Supported band: 1.0 .. 2 x UI scale.
;                        Above 2 x UI is allowed up to 4 x UI but is
;                        UNVERIFIED and logged as such; above that it is
;                        rejected and clamped. This is an ART/sanity cap,
;                        NOT a crash cap - do not "fix" it upward without
;                        building art. (The mechanical stop is B <= 50 and
;                        it fails safe.)
BubbleScale=auto
```

**Second example — user overrode the bubble and picked UI 1.5x:**
```ini
[UiSpike]
AutoScale=2
ScaleFactor=1.5

[UDriveIt]
; auto would be 3.00 (drawn 96 px); user wants a smaller pin.
BubbleScale=2.0
```

**Warning:** `BubbleScale` must be read as a **string first** (`GetPrivateProfileStringA("UDriveIt","BubbleScale","auto",…)`) — a float read cannot represent `auto`. Compare case-insensitively against `auto`; otherwise `strtod` with an end-pointer check, the same shape as the validated conversions in `Settings::Load` (`src\Settings.cpp`, grep `get_converted_value`) — note the `GetPrivateProfile*`-family parse this line originally pointed at has since been replaced by an `IniReader`, so the *pattern* survives there but the API does not.

## 4.4 Settings fields, validation, and log lines

Fields to add beside `spikeScaleFactor` (`src\Settings.h`, grep `spikeScaleFactor`):

```cpp
// [UiSpike] AutoScale is now tri-state: 0 manual-no-sync, 1 auto, 2 user choice.
int  spikeAutoScaleMode = 1;      // replaces bool spikeAutoScale (keep the bool
                                  // accessor: spikeAutoScale == (mode != 0))
// [UDriveIt] - knob 2. UI/TEXT stay on spikeScaleFactor; this is the ONLY
// second scale number in the DLL. Read the tier-mirror audit in UiSpike.cpp
// (grep "gTierF mirrors settings.spikeScaleFactor") BEFORE adding a
// namespace-scope mirror: four hooks install at ArmDeferred BEFORE any sweep
// and would read the compiled default.
bool  udiBubbleAuto  = true;      // BubbleScale=auto
float udiBubbleScale = 0.0f;      // 0 = derive (2 * spikeScaleFactor)
float udiBubbleEff   = 0.0f;      // RESOLVED value after clamp - the ONLY
                                  // field any hook may read
```

All logging at `LogLevel::Info` via `Logger::Get().WriteLine`, prefix `UDIScale:` (matching the existing `AutoScale:` / `ScaleTier:`). **Every rejection logs the requested value, the reason, and the value actually used. No path may log only the final value.**

**Knob 1 — two independent gates, both from existing code:** `PackageInstalled` (`src\ScaleTier.cpp`, grep `bool PackageInstalled`) and the fit test (same file, grep `bool Fits(` and its `TierMinimumFor` / `kTierMinimums` table).
```
AutoScale: user choice UI 3.00 (AutoScale=2) ACCEPTED - package -3x installed, fits 2400x1600. Auto-detect would have chosen 2.00.
AutoScale: user choice UI 3.00 (AutoScale=2) REJECTED - needs 2640x1674, screen is 2400x1600. CLAMPED DOWN to 2.00.
AutoScale: user choice UI 3.00 (AutoScale=2) REJECTED - z_SC4UIScale_SelectiveArt-3x.dat not installed. CLAMPED DOWN to 2.00 (largest installed that fits).
AutoScale: user choice UI 2.50 (AutoScale=2) REJECTED - not a supported value (1.50 / 2.00 / 3.00). CLAMPED DOWN to 2.00.
```

**Warning — concrete consequence, state it up front:** at the project's own native **2400x1600, 3x is NOT eligible** — `kWidestDesignPx 880 * 3 = 2640 > 2400`, and the density cap is `min(2400/800, 1600/600) = 2.667 < 3`. `[M]` **Only 1.5 and 2 are reachable at the user's resolution today.** A UI must grey 3x out on this machine, with the reason inline.

**Text-lock enforcement** (fires when someone hand-edits the ini; detect with `GetPrivateProfileStringW(L"UiSpike", L"TextScale", L"", …)` and the same for `FontScale`, `TextFactor`):
```
UiSpike: REJECTED key [UiSpike] TextScale=3.0 - text is locked 1:1 to the UI scale and is not settable. Using UI 2.00 for both. Key ignored, not removed. See tools\research\SCALING-AXES.md section 2.
```

**Knob 2 — resolution order: parse → derive-if-auto → range clamp → art route → apply.**
```
UDIScale: bubble auto = 2.00 x UI 2.00 -> 4.00; art 64 px, stretch x2.00, drawn 128 px.
UDIScale: bubble 2.00 from ini (auto would be 4.00 at UI 2.00); art 64 px, stretch x1.00, drawn 64 px.
UDIScale: REJECTED BubbleScale='big' - not a number and not 'auto'. Using auto = 4.00.
UDIScale: REJECTED BubbleScale=0.50 - below 1.00 (stock art size). CLAMPED UP to 1.00.
UDIScale: BubbleScale=6.00 is above the art-backed ceiling 4.00 (2 x UI 2.00) - UNVERIFIED, nearest-neighbour stretch x3.00 from 64 px art. Applying 6.00 anyway; report anything odd.
UDIScale: REJECTED BubbleScale=12.00 - above the hard cap 8.00 (4 x UI 2.00). CLAMPED DOWN to 8.00.
```
Hard cap: `min(4.0f * ui, 8.0f)`.

**The art-fallback line.** **Warning:** the requested **factor never falls back — only the SHARPNESS does.** Drawn size stays `round(32 · B)` on every path, because stretch is always available. Anything else would be a silent size change.
```
UDIScale: bubble 3.00 requested; no sharp art package (looked for z_SC4UIScale_UdiBubble-3x.dat beside the DLL). Nearest BUILT art = 2.00 (tier package z_SC4UIScale_SelectiveArt-2x.dat, 64 px). Using nearest + stretch x1.50 -> drawn 96 px. SIZE IS CORRECT, SHARPNESS IS NOT (nearest-neighbour). Requested factor UNCHANGED at 3.00.
```
Today **no** bubble art package exists at any factor, so this line fires on every boot until an eighth `SyncDat` base is added. That is correct and honest — it is the line that stops "it looks fine" being mistaken for "sharp art shipped".

**The two lines that stop a silent success** (law: *a probe for a fix must ADJUDICATE the fix, not just sight the target*):
```
UDIScale: bubble window 0x48E945B4 not seen this session - factor 4.00 was armed but NEVER APPLIED. (No U-Drive-It mission active, or the marker moved class.)
UDIScale: WARNING - blit multiplier from live window is 1.98, requested 2.00 (window 127x127, wanted 128). Fit clamp bit; the window scale and the blit scale disagree.
```
The second guards the knife edge of §3.4. **Implementation requirement:** set the window to `round(32·B)` **first**, then compute the blit multiplier **from the live window** (`m = winW / artW`), and log when they differ by more than 0.01.

## 4.5 Precedence vs AutoScale — one sentence

> **An explicit user choice always beats auto-detection, but never beats the assets or the screen; every downgrade is announced.**

```
AutoScale=1  ->  UI = Decide(resW, resH).                     ScaleFactor ignored.
AutoScale=2  ->  UI = clamp(ScaleFactor, supported n installed n fits).
AutoScale=0  ->  UI = ScaleFactor verbatim, packages untouched (diagnostic).
Knob 2       ->  independent of all of the above; only its DEFAULT is a
                 function of the resolved UI value, and it is resolved AFTER
                 the UI clamp, never before.
```

**Warning — that last clause matters:** if the user asks for UI 3x on a 2400x1600 screen and is clamped to 2x, `BubbleScale=auto` must resolve to **4.00, not 6.00**. The auto coupling follows the **effective** UI scale, not the requested one.

Emit immediately after the existing `AutoScale: %dx%d -> tier %.2f` line (`src\SC4UIScaleDllDirector.cpp`, grep `-> tier %.2f`):
```
AutoScale: EXPLICIT wins - UI 2.00 from ini (AutoScale=2); auto-detect for 2400x1600 would also be 2.00.
AutoScale: EXPLICIT wins - UI 1.50 from ini (AutoScale=2); auto-detect for 2400x1600 would have chosen 2.00. User setting honoured.
AutoScale: AUTO wins - UI 2.00 from 2400x1600 (AutoScale=1); ini ScaleFactor=3.0 is present but ignored in auto mode.
```
That third line is important: today `ScaleFactor=2.0` sits in every shipped ini and is **silently overwritten** (`src\SC4UIScaleDllDirector.cpp`, grep `settings.spikeScaleFactor = tier;`). Users will edit it, see nothing happen, and file a bug. **Say it out loud.**

## 4.6 Restart requirements

### Knob 1 (UI + text): **RESTART REQUIRED. No partial application, no "apply now".**

Structural, not laziness:
- The nine byte patches are **PostAppInit one-shots into `.text`** (`src\SC4UIScaleDllDirector.cpp`, grep `bool PostAppInit` — the run of `CodePatches::Apply*` calls inside it). `ScaleSizeTable` verifies against **stock** bytes before writing (`src\CodePatches.cpp`, grep `void ScaleSizeTable`), so a second application at a new factor finds non-stock bytes and **skips** — the HTML tables would keep the old factor while windows moved.
- `FontStyle-<tag>.ini` is mirrored into `<install>\Plugins\FontStyle.ini` at boot (`src\ScaleTier.cpp`, grep `void SyncFont`) and the engine builds its font table **once**.
- Package gating is **file renames** (`.dat` ↔ `.dat.x1-disabled`); DBPF load order is read at startup only.
- Born-correct hooks bake at construction: SUBBORN (`src\UiSpike.cpp`, grep `UiSpike::InstallSubFlyoutBorn`), SUBBORNSCALE Place detour (grep `UiSpike::InstallSubFlyoutBornScale`), EARLYCHART (grep `EARLYCHART - the chart is BORN correct`). Windows already built keep the old numbers.
- `scaleMap` records stock→scaled only (`src\UiSpike.h`, grep `struct ScaleRecord` and `std::map<void*, ScaleRecord> scaleMap`); there is **no** scaled→rescaled path, and `Classify` would treat an already-scaled window as done.
- Cached paint buffers are born at first-paint size (R26) — the box would move and the pixels would not.

Log line on a detected mid-session change (from the same 20-sweep poll):
```
UiSpike: ScaleFactor in the ini changed 2.00 -> 3.00 while running. NOT APPLIED - the UI scale is fixed at process start (font table, byte patches and data packages are all boot-time). Restart SimCity 4.
```

### Knob 2 (bubble): **LIVE, within ~1 second.**

It rides the existing live-tune re-read (`src\UiSpike.cpp`, grep `LiveTuneIniPath` — the `[UiSpike] LiveTune` poll block inside `UiSpike::ScaleGodFlyouts`), which reads explicit keys **per section** — a new `[UDriveIt]` section cannot be swallowed by `[Disaster]`/`[Flyout]`/`[Probe]`. The marker is a single-image leaf with no children (`src\UiSpike.cpp`, grep `COUNT THE ROOT ITSELF` in `HookRuntimeBmpsUnder`), no text, parented to the full-screen 3D view so it cannot overflow a parent, and its hit box *is* its window rect.

Requirements for live to be **honest**:
- store the bubble's **stock 32x32** in its `scaleMap` record so the new size is computed **absolutely** (`round(32·B)`), never incrementally;
- re-set window **then** blit, in that order (the existing call order already does this: the `ScalePanelRoot(p.win…)` panel loop in `UiSpike::ScalePanelsUnder`, then `HookRuntimeBmpsUnder`/`kBmpxCityRoots`, draw later);
- bypass `ScalePanelRoot`'s generic edge anchor for this id and grow **unconditionally about the centre** (§3.4 constraint 2).

```
UDIScale: live re-read - bubble 4.00 -> 3.00; window 0x48E945B4 re-set 128x128 -> 96x96, stretch x1.50.
UDIScale: live change to 3.00 applied by STRETCH ONLY; sharp art for 3.00 (if ever built) needs a restart to gate its dat.
```

## 4.7 Migration guarantee — existing 2x users see NO change

The golden config (`_working-backup\GOLDEN-2x-DirectX-2026-07-23\Documents-Plugins\SC4UIScale.ini`) is `AutoScale=1`, `ScaleFactor=2.0`, no `[UDriveIt]` section.

1. **`AutoScale` default stays `1`** and its `0`/`1` semantics are byte-identical. The new value is `2`, which no existing file contains. `Settings.cpp` switches from `!= 0` to `GetPrivateProfileIntW(…, 1)` — same result for `0` and `1`.
2. **Missing `[UDriveIt]` → `BubbleScale=auto` → `B = 2 × UI = 4.00` at UI 2x → drawn 128 px.** That is *exactly* the measured shipped behaviour (`BMPX draw … win 128x128 -> dst 128x128 (x2.00)`). **Same pixels.** The default is safe **because** the old `f²` law and the new `2f` law intersect at f = 2 — this is not a coincidence we are relying on, it is the one point we are deliberately pinning the new law to.
3. **The DLL never writes `SC4UIScale.ini`.** No key is injected into a user's file on upgrade. Only a GUI writes, and only on user action — with `WritePrivateProfileStringW` (in-place, key- and comment-preserving), **never a rewrite**, because the file carries `[Disaster]`/`[Flyout]`/`[Probe]` live-tune keys no GUI knows about.
4. **No key renamed, none removed.** `ScaleFactor` stays the wire name for the UI axis. An alias (`UIScale=`) would create two sources of truth for one field — **refused**.
5. **Warning: 1.5x and 3x users DO change** (bubble 72→96 px and 288→192 px). There are none today (both tiers are ineligible at the only tested resolution), but this ships as a **stated behaviour change** with the §5.3 assertion, not as a silent fix.

## 4.8 If a GUI is ever built — the two rules

- Write **ASCII, CRLF, no BOM**, and **preserve unknown keys and comments** (`WritePrivateProfileStringW`, in place).
- **Never write `AutoScale=0`.**

Ineligible UI-scale options must be **greyed with the reason inline, never hidden**: `3x — needs a 2640 x 1674 display (yours is 2400 x 1600)` / `3x — asset package not installed (z_SC4UIScale_SelectiveArt-3x.dat)`. A helper line under the UI-scale control, always visible: *"Text scales with the UI, 1:1. Fonts, tooltips and dialog text all follow this setting — they are not separately adjustable, because every dialog box in the game is sized to hold text at this exact factor."* Footer: *"UI scale changes take effect after you restart SimCity 4. Bubble scale applies immediately, even while the game is running."*

---

# 5. THE PIPELINE AND THE GATES

> **§5.2–§5.4 are PROPOSED gates — specified here, never written** (re-checked
> 2026-08-30). `Test-ScaleComboMatrix`, `Test-BubbleArtLaw` and
> `Test-TextBoxFit` are designs on this page and nothing else: no script by
> those names, or by any successor name, has ever existed in `_tests\`. They
> are deliberately named **without a `.ps1` extension** throughout §5–§8 so no
> sentence reads as a link to a file a reader could open. §5.5's extensions to
> the gates that **do** exist — `_tests\Test-DatIntegrity.ps1`,
> `_tests\Test-ScaleTierDecide.ps1`, `_tests\Test-PackageGating.py`,
> `_tests\Deploy-OnGameClose.ps1` — are unaffected, and those are live files.

## 5.1 What must be built

**Font side: nothing.** `[M]` Text locked 1:1 means the text factor ≡ the tier factor. The three `FontStyle-<tag>.ini` files already exist, are byte-reproducible (`make_fontstyle.py --selfcheck`), and are already hash-asserted `deployed == built` (`_tests\Test-DatIntegrity.ps1`, grep `$FONT_SOURCES` and the `FontStyle-` rows in `$BUILT_PAIRS`). The bubble carries **no text at all**, so no font style is needed at any bubble factor.

**Bubble side: a package, not pixels** (§3.6). New generator `tools\bubble\build_bubble.py --absolute <B>` → `z_SC4UIScale_UdiBubble-<tag>.dat`, ~1.2 KB, <1 s. Plus one `SyncDat` line in `src\ScaleTier.cpp` and one `_tests\Test-DatIntegrity.ps1` row-pair.

**Warning — tag-map.** `_factor_tag()` exists in **three copies** — grep `def _factor_tag` in `tools\selective-safe\build_selective_safe.py`, `tools\dialog-static\build_dialog_static.py` and `tools\itemicons\stage_icons.py`: integer → `"%dx"`, else `"%gx"` with `.`→`_`. 4→`4x`, 6→`6x`, 2.25→`2_25x` all work — **but 1.5 is special-cased to `15x`, not `1_5x`**, so an absolute bubble factor of 1.5 would tag `-15x` and read like the UI 1.5 tier tag. Cosmetic collision only (different base name), but **the bubble builder must carry its own explicit tag map and refuse anything not in it**, rather than inherit the general rule.

## 5.2 `Test-ScaleComboMatrix` — PROPOSED, never written — no advertised setting without a package

The Law-45 gate. Reads the advertised sets **from source, not from a copy**: UI factors from `ScaleTier::kPackages` (`src\ScaleTier.cpp`, grep `kPackages[] = {`), bubble multipliers from a new `kBubbleMultipliers` table in `src\Settings.h`. **Hard-fails if either parses empty** (the anti-drift guard from `Test-ThirdPartyGates.ps1`).

For every cell of `UI × bubbleMult`: compute `absB = ui * mult`; assert the UI tier's four core dats + `FontStyle-<tag>.ini` exist (live or `.x1-disabled`); assert `z_SC4UIScale_UdiBubble-<absBtag>.dat` exists **unless** the cell is declared in a documented `$STRETCH_ONLY` table; assert `absB <= 2 * ui`; assert the UI factor is *reachable* at the declared target resolution via the `Decide()` mirror already in `Test-ScaleTierDecide.ps1`.

```
FAIL: advertised combo UI=3 x bubble=2 (absolute 6x) has no z_SC4UIScale_UdiBubble-6x.dat and is not listed in $STRETCH_ONLY - a user can select a setting with no package behind it. Build it (tools\bubble\build_bubble.py --absolute 6) or add the cell to $STRETCH_ONLY with a reason.
FAIL: advertised UI factor 3 is NOT reachable at 2400x1600 (Decide cap = 2.667, and 880*3 = 2640 > 2400). Either grey it out in the settings UI or document the override.
FAIL: advertised combo UI=2 x bubble=3 asks absolute 6x, above the 2xUI art ceiling - every pixel would be block-replicated from 4x art and nobody has ever seen it.
FAIL: kBubbleMultipliers parsed as empty - the advertised set could not be read, so this gate proved NOTHING. Fix the parse before trusting a pass.
```

## 5.3 `Test-BubbleArtLaw` — PROPOSED, never written — pin `drawn = 32·B` and the art provenance

The axis already exists and its law is wrong (§3.3). This gate makes the two laws unable to diverge silently again.

- **Provenance:** for every shipped `UdiBubble-<absB>` package, extract its single entry and assert its SHA-256 equals a fresh `Upscale2x.exe --factor <absB>` over `tools\dbpf\extracted\SimCity_1` for that TGI. **This is what caught the `bubble4x-15x` double-resample.**
- **Dimension:** PNG IHDR = `32·absB` square. **Cardinality:** exactly 1 entry, TGI `{856DDBAC, 46A006B0, 094AC89A}`.
- **Exclusivity:** `0x094AC89A` appears in **no other live package at a different factor** — the over-scale exception must stay a set of size one.
- **The rect invariant:** `0x094AC89A` has **zero `.UI` references** across the winning corpus. *This is WHY the exception is legal.*
- **Law arithmetic:** mirror `BmpCtxBltThunk`'s `m = min(gBmpScale, winW/artW)` and assert the modelled drawn size equals `32·absB` for every advertised cell, in **both** the STRETCH and SHARP routes.

```
FAIL: z_SC4UIScale_UdiBubble-4x.dat entry is 128x128 but its bytes do not match a fresh Upscale2x --factor 4 - it was built from an intermediate (bubble4x-15x\ is exactly this bug: 510/9216 px differ from a direct --factor 3). Rebuild from the 1x master.
FAIL: modelled drawn size at UI=1.5, bubble=2 is 72 px; the law says 32*B = 96. Shipped behaviour is 32*f^2, which equals 32*2f ONLY at f=2. Implementing the user's rule is a deliberate BEHAVIOUR CHANGE at 1.5x and 3x - if that is intended, update this expectation in the SAME commit as the code.
FAIL: TGI 46A006B0/094AC89A appears in BOTH z_SC4UIScale_SelectiveArt-2x.dat (64x64) and z_SC4UIScale_UdiBubble-4x.dat (128x128) with both live, and the UdiBubble package does NOT sort after SelectiveArt. The tier art wins and the bubble knob does nothing.
FAIL: 0x094AC89A now has 2 .UI references in the winning corpus. The over-scale exception was legal ONLY because it had none - an imagerect scaled at the TIER factor over art at the BUBBLE factor breaks rect<=art. Stop shipping sharp bubble art.
```

## 5.4 `Test-TextBoxFit` — PROPOSED, never written — the direct descendant of the legend bug

**Three cases (1.5 / 2 / 3), not combinatorial, precisely because text is locked 1:1.** This gate is what makes the lock a *checked* invariant rather than a belief. It reproduces the §2.3 corpus in-gate:
- parse `[Font Styles]` from `tools\fonts\FontStyle.default.ini` (name→1x pt, GUID→name);
- walk all 331 scripts in `tools\uiscripts\extracted\`, harvesting every tag carrying both `area=(l,t,r,b)` and a resolvable `font=` (by name or GUID);
- apply `make_fontstyle.py`'s **own** rules — `SIZE_SQUEEZE`, `KEEP_STOCK` — **parsed out of the generator, not retyped**;
- per factor assert (i) `min(scale_len(h) / fontsize_N) >= 1.000` and (ii) per-pair `ratio_N / ratio_1x >= 1 - 0.030`.

Pinned expectations `[M]`: **n = 2537 controls / 215 scripts / 128 distinct pairs; ratio regressions 0 / 0 / 75 at 2x / 3x / 1.5x; worst −2.94%; min ratio 1.000 at all four factors.**

```
FAIL: f=1.5 control h=16 font=PUckDate(11pt->17pt) ratio 1.455 -> 1.412 (-2.94%) in I-xxxxxxxx.ui - the box grew x1.500 and the text grew x1.545. Tolerance is -3.0%. Either add the style to KEEP_STOCK / SIZE_SQUEEZE in tools\fonts\make_fontstyle.py, or widen the box in the static builder. THIS IS THE GRAPHS-LEGEND FAILURE MODE (task #57): 2x text in a 1x-derived box.
FAIL: f=2.0 has 3 ratio regressions. At an INTEGER factor with text locked 1:1 there must be EXACTLY ZERO - a nonzero count means the 1:1 lock has been broken somewhere (a new SIZE_SQUEEZE entry, a KEEP_STOCK entry, or a box no longer scaled by scale_len).
FAIL: corpus parsed 0 controls - the .UI harvest or the font table parse broke; this run proved nothing (NULL IS NOT EVIDENCE).
FAIL: corpus parsed 812 controls, expected ~2537 - parse truncated.
```
**Positive control** (stated in the gate's own header, per *NULL IS NOT EVIDENCE*): a `--selftest` switch injects `SIZE_SQUEEZE = {"GenBodyMedium": 1.10}` and asserts the run goes **red**. A gate that has never been seen to fail has not been shown to work.

## 5.5 Extensions to existing gates (no rewrites)

- **`_tests\Test-DatIntegrity.ps1`**: one `$EXPECTED` row per bubble package (`entries = 1`) with the reason-comment convention, and one `$BUILT_PAIRS` hash row. **Warning — task #58's lesson applies verbatim: for a 1-entry dat the count and byte size are *guaranteed* to survive a stale-content bug — only the hash pair catches it.**
- **`_tests\Test-ScaleTierDecide.ps1`**: add a `$namedKnob` block once the knob exists — an *explicitly chosen* factor must still satisfy the fit invariant or be refused **with a logged reason**, never silently downgraded.
- **`_tests\Deploy-OnGameClose.ps1`**: add the bubble copy lines **in the same change as the package** (Law 40; the ThirdPartyUI/WarriorUI rot is what that law is made of).
- **The WarriorUI gate — settled (#119, v2.71.3).** Do **not** re-add the
  `SyncDat` call; doing so would double-add it.
  - **The `SyncDat` call exists** — `src\ScaleTier.cpp`, grep `z_SC4UIScale_WarriorUI`: `pkg.tag, match && DepOkByName(L"zzz-SC4UIScale\\z_SC4UIScale_WarriorUI", depOk)` — and it is **both** tier-gated (the `match` predicate a few lines above, grep `const bool match =`) and mod-gated, exactly like its three siblings.
  - **The `kThirdPartyDeps` row is consumed.** Grep `UI_Compact.dat` in `src\ScaleTier.cpp` for the row (EXACT NAME + SIZE on `UI_Compact.dat` 8702 / `Mayor_Sign_Menu.dat` 5766). `depOk` is filled (grep `depOk[d] = present && sizeOk;`) and read by the `DepOkByName` argument **inside the same function** (`SyncStaticLayers`, grep `void SyncStaticLayers`), which is live from `src\SC4UIScaleDllDirector.cpp` (grep `ScaleTier::SyncStaticLayers(settings.spikeScaleFactor)`). The two name strings match byte-for-byte, so this does not fall through `DepOkByName`'s `return true` default (grep `bool DepOkByName`) — the failure mode where a *present* call is still ungated.
  - There are now **ten** `SyncDat` call sites (count them: grep `SyncDat(` in `src\ScaleTier.cpp`); earlier "exactly seven" counts were stale (see the banner at the top of this document: the symbol is the anchor, the number is not, and this count is itself the kind of number that keeps moving).
  - **The deploy-script staging is correct as-is — do not re-derive the alarm from it.** `_tests\Deploy-OnGameClose.ps1` (grep `z_SC4UIScale_WarriorUI-2x.dat`) lays `WarriorUI-2x.dat` down live with `-15x`/`-3x` as `.x1-disabled`; `SyncStaticLayers` flips the pair per tier at boot. The deploy never changed; what was missing was the boot-time gate.
  - **Regression-proofed, so this cannot silently come back:** `_tests\Test-PackageGating.py` asserts that *every* `kThirdPartyDeps` row has a `SyncDat` call (its assertion 1, written for this defect) and that every gate names **its own** package. It currently reports `[zzz-SC4UIScale\z_SC4UIScale_WarriorUI] gated` across 5 rows / 10 call sites, and its #119 negative control — deleting the WarriorUI call — reproduces the original bug. Full post-mortem in the code at `src\ScaleTier.cpp` (grep `#119 (v2.71.3): THIS CALL WAS MISSING`) and in the v2.71.3 changelog entry — **citation partly retired:** the root `VERSION-HISTORY.txt` has since been trimmed to recent releases and no longer carries v2.71.3; that entry now survives only in `_archive\SNAPSHOT-2026-08-14-pre-release-doc-pass\VERSION-HISTORY.txt` (grep `v2.71.3`).
- **The package table is stale in three places** `[M]`: `ItemIcons` 266→356 and it is tiered, not `-2x`-only; `ItemIconsSub` 125→130; `SelectiveArt` 345→**655 / 655 / 655** at 1.5x / 2x / 3x (#136 (v2.88.0) ended the per-tier split: the builder's `FACTOR <= 2.0` filter on the four dismiss-X glyphs is gone — `tools\selective-safe\build_selective_safe.py`, grep `` `or FACTOR <= 2.0` tail is GONE ``, the condition is now `if True` — so 3x ships the same entries as 1.5x/2x. Asserted in `_tests\Test-DatIntegrity.ps1` (grep the `SelectiveArt` rows in `$EXPECTED`), and read back from the shipped `tools\packages\3x\z_SC4UIScale_SelectiveArt-3x.dat` DBPF index-count. **Citation retired:** `README.md` no longer carries the package table at all; it moved to `docs\PACKAGE-MANIFEST.md` §"Package contents", where the counts to check against live today.)

## 5.6 Frozen artifacts

**Nothing in this plan touches `dist\SC4TouchControls-v1.0.4\` or `-v1.0.5\`.** Both knobs live entirely in `SC4UIScale.dll` and its packages; the touch DLL is a separate binary and a separate project.

Three ways it could still go wrong:
1. `_tests\Test-DatIntegrity.ps1` asserts frozen SHA-256 hashes — grep `$EXPECTED = @(` for the per-package entry counts and `$BUILT_PAIRS = @(` for the `built == deployed` hash compare (the compare itself is the `Get-FileHash` pair inside `foreach ($pair in $BUILT_PAIRS)`). Adding `$EXPECTED`/`$BUILT_PAIRS` rows must not perturb those blocks. **If either hash line goes red while doing #97 work, that is not a #97 regression — stop and investigate.** **Citation partly retired:** the second half of this claim — that the deployed `SC4TouchControls.dll` *is* the frozen v1.0.5 binary — is **no longer asserted in this gate**; `SC4TouchControls` has zero hits in the file today. The touch DLL is now held out by **name** instead, in `_tests\Set-StockPlugins.ps1` (grep `TOUCH QUARANTINE - USER ORDER` and the `$Quarantined` list under it). The repo's tracked history is a single squashed commit, so `git log --diff-filter=D` cannot date the move.
2. Do **not** add the bubble package to any `dist\SC4TouchControls-v1.0.*` README, manifest, or USB bundle. It belongs to the UI-scale product.
3. `Deploy-OnGameClose.ps1` already deploys into the shared `Plugins` folder where both products live; adding bubble copy lines there is fine and does not touch `dist\`.

---

# 6. RECOMMENDED SEQUENCING

## Increment 1 — CATALOG + DEFAULT. Zero new assets, zero new knobs.
*Ship the arithmetic, not the settings surface.*

1. **Adjudicate the refuted-lead-written-as-fact** (§3.7). One line settles it. Until then every downstream decision rests on a null.
2. **Settle the unmeasured glyph-layer question** with one `GetChildCount()` on `0x48E945B4` (§8, Q2).
3. **Make `gBmpScale` per-id** inside `BmpDrawThunk` (`gBmpCurId` is already computed there — `src\UiSpike.cpp`, grep `gBmpCurId = w->GetID()`). Without this, every My Sims portrait takes the bubble factor.
4. **Give `0x48E945B4` a window scale that bypasses `ScalePanelRoot`'s generic anchor** and grows unconditionally about its centre (§3.4 constraint 2). **This is a live hazard at today's factor, independent of the knob.**
5. **Pin `drawn = 32·B` with `B = 2·UI` hardcoded.** **Warning:** deliberate behaviour change at 1.5x (72→96) and 3x (288→192) — put it in the changelog.
6. **Delete or promote `BUBBLE_OVERRIDE_ENABLED`** (`tools\selective-safe\build_selective_safe.py`, grep `BUBBLE_OVERRIDE_ENABLED` — the assignment, then the `elif` copy path just below it). Armed dead plumbing with a live copy path behind one boolean is the exact Law-45 shape. If promoted, `bubble4x-15x\` **must** be replaced by the direct `--factor 3` file (§3.6).
7. **Fix the WarriorUI gate** (§5.5).

**Gate proving increment 1 done:** the proposed `Test-BubbleArtLaw` (§5.3 — never written) green in its STRETCH-route form (law arithmetic + exclusivity + zero-`.UI`-refs) at all three tiers; `Test-DatIntegrity.ps1` still green; **plus one eyes-on** — the predicted 1x-flash (§8 Q5) will be visible during the session this needs anyway.

## Increment 2 — the UI knob. Still no bubble knob.
`spikeAutoScaleMode` + the tri-state `AutoScale`; decide and document the `Decide()`-override question (§4.5 — at 2400x1600 only 1.5 and 2 are reachable); **restart-required**, exactly like the tier, because the nine `CodePatches` are PostAppInit one-shots.
**Gate:** the proposed `Test-ScaleComboMatrix` (§5.2) over `UI × {2}` (bubble fixed) + the proposed `Test-TextBoxFit` (§5.4) green at all three factors, **including its `--selftest` positive control**. Neither gate exists yet — writing them is part of this increment.

## Increment 3 — the bubble knob, STRETCH-ONLY.
`Settings` fields per §4.4, in its **own `[UDriveIt]` section**, its own mirror, and **a repeat of the `src\UiSpike.cpp` tier-mirror audit** (grep `gTierF mirrors settings.spikeScaleFactor`). Advertised multipliers `{1, 1.5, 2}`; every cell in `$STRETCH_ONLY`.
**Gate:** the proposed `Test-ScaleComboMatrix` (§5.2 — never written) full matrix green with every cell justified as STRETCH-ONLY.

## Increment 4 (optional, quality) — sharp art.
`tools\bubble\build_bubble.py --absolute <B>` → `z_SC4UIScale_UdiBubble-<tag>.dat`, ~1.2 KB, <1 s each.
**Law — a coupled TRIPLE:** ship the dat, take the id off the stretch multiplier, and move the `$STRETCH_ONLY` cell — **all three or none**, or you get `32·2f·f`.
**Gate:** the proposed `Test-BubbleArtLaw` (§5.3 — never written) in SHARP-route form + new `Test-DatIntegrity` rows.

---

# 7. BACKLOG — UI scaling above 3x (deferred by the user)

**Explicitly deferred, 2026-08-03. Recorded to size it, not to design it. Build nothing here now.**

What already exists:
- **`ScaleTier::kPackages` already has a 4x slot** (`src\ScaleTier.cpp`, grep `{ 4.0f, L"-4x" }` — the first row of `kPackages[] = {`), inert because `PackageInstalled` gates eligibility on the art dat existing (same file, grep `bool PackageInstalled`).
- **`Upscale2x` accepts up to 16.0** (`tools\upscale\Upscale2x.cs`, grep `factor > 16.0` — the argument-range check and the `--factor must be in (1.0, 16.0]` refusal beside it). `[M]` A full factor-4 upscale run costs **18.8 s / 66 MB tree / ~20 MB dat `[INF]`**; factor 6 costs **35.0 s / 113 MB / ~27 MB `[INF]`**.
- `_factor_tag()` handles 4 → `4x` correctly in all three copies.
- `make_fontstyle.py` needs one command for `FontStyle-4x.ini` (23,016 B, sub-second).

**What would block it — in the order it bites:**

1. **Blocker: `Decide()`'s fit cap refuses even 3x on the user's own display.** `[M]` At 2400x1600, `cap = min(2400/800, 1600/600) = 2.667`, and 3x also fails `880·3 = 2640 > 2400`. **4x needs ≥ 3520x2232.** A UI-above-3x product needs a display that does not exist on this desk.
2. **Blocker: the imm8 encoding ceilings in `CodePatches.cpp` are the real wall.** The advice-row X fork is gone (#136 — see R9), but the encoding wall stands: at 4x the ordinance name-column x wants 136 and clamps to 127 (`src\CodePatches.cpp`, grep `kOrdinanceNameXImm8Sites` for the two sites and `ideal 136 -> ships 127` for the worked example; the clamp itself is grep `push imm8 ceiling`); the budget slider widths (110→440), row text widths (120→480) and master funding sliders (90→360) all blow `push imm8` (same file — grep `slider width (110`, `item slider width (110`, `row capacity text width (120`, `master funding slider 1 width (90`; each comment carries its own "clamps to 127"). ~~**At 3x several already clamp (R19).**~~ **[CORRECTED 2026-08-30 — this understated the tier by two steps.]** Seven of those sites clamp at **f = 1.5 AND f = 2.0**, i.e. in tiers that ship today, not only at 3x: `0x788D1B` / `0x78916A` (stock 110 → 165 at 1.5x), `0x787021` / `0x787072` (90 → 135), `0x7870DD` (120 → 180) and `0x787165` / `0x78724A` (85 → 128 — the one that only just crosses). An eighth, `0x78B9A1` (60), joins them at 3x from `kBudgetSubImm8Sites`. **This was invisible to every clamp census built from the log**, because `ApplyBudgetFamilyScale` clamps SILENTLY (`src\CodePatches.cpp`, grep `push imm8 ceiling (slider width at f=2)` and `sub imm8 ceiling`) while the ordinance clamp beside it logs a line per site (grep `ordinance inset %ld clamped to 127`). The values are NOT corrected: that means re-encoding nine sites inside a user-confirmed 2x dialog, which is the #98 law. *(Anchor note, not a change of claim: since v2.74.0 the ordinance name-column x is a **fork** — the imm8 sites above are the `f < 2.50` path, and at or above 2.50 an equal-length block re-encode takes over — grep `OrdinanceNameXUsesBlock` and `kOrdinanceNameXBlocks`. A reader greping `136` will land in both.)* A 4x UI tier ships **visibly wrong budget and ordinance columns** unless those sites are re-encoded to imm32 first. That is the largest single work item.
3. **Closed — there is ONE rounding stream.** `ScaleRound` (`src\UiSpike.cpp`, grep `inline int32_t ScaleRound`) is a one-liner that delegates to `RoundHalfUp` (same file, grep `inline int32_t RoundHalfUp`) as of #162, and **#75 was CLOSED AS REFUTED** — the 824-pair 1.5x divergence had no artifact. A new factor no longer multiplies anything here. See the corrected row in §1.1a.
4. **Warning: `kCityDialogIds`' factor-parameterised base guard** (`src\UiSpike.cpp`, grep `PER-ID 1x BASE SIZES for the data-born EXACT-MATCH guard` for the rationale block, then `struct CityDialog` for the table it guards) needs a fresh product-collision check per factor (v2.39.13/.14 scars).
5. **Warning: the DialogStatic corpus at 4x** — no measurement exists. §2.3 shows 0 regressions at 2x and 3x, `[INF]` 4x should behave like the other even factor, but that is an inference and the proposed `Test-TextBoxFit` gate (§5.4 — never written) would settle it in one run.
6. **Not a blocker, note it:** `Upscale2x` reports `Bad magic: 74` — 74 files named `.png` that are not PNG data, correctly skipped at every factor; the existing counter is the gate.

**Note on the bubble axis and a future tier:** a per-id bubble factor is a **multiplier over whatever the tier art is**, so nothing in §3–§6 forecloses a future 4x UI tier. The tier would simply need its own package set first.

---

# 8. REFERENCE QUESTIONS

Each with **the single measurement that resolves it.**

| # | Question | Status | The one measurement |
|---|---|---|---|
| **Q1** | Is `{46A006B0, 094AC89A}` the marker's art? Our own source (`src\UiSpike.cpp`, grep `THE U-DRIVE-IT MAP MARKER`) and `_tests\REGRESSION.md` say **NO**, on a null; stock art is 32x32, our 2x stage is 64x64, and the live draw reports `img 64x64`. | **CONTRADICTION IN OUR OWN DOCS** — the "no" rests on a null (*NULL IS NOT EVIDENCE*) | Flip `BUBBLE_OVERRIDE_ENABLED` in `tools\selective-safe\build_selective_safe.py` (grep the name), rebuild, read whether `BMPX draw id=0x48E945B4` says `img 128x128`. **Do this before building anything.** Then correct or delete the refuted note either way. |
| **Q2** | Does the bubble carry a second **glyph** layer? If it does, that art is shared game-wide (`46A006A7` slider, `82B99D9D` spinner — recorded in the session diary that was retired 2026-08-06 into the local-only archive tree, so this citation is **evidence a published reader cannot check**; the two instance ids are the anchor, and they are greppable in the staged corpus) and is pinned to the UI factor, so **a 4x bubble would carry a 2x glyph**. The 15 glyph entries in `build_selective_safe.py` (grep `per-mission icon table at VA 0x44DEC7` — the run of `(0x46A006B0, …)` tuples under `mission icon table @0x44DEC7` inside `CODE_BOUND_TGIS`) were staged on a premise later refuted (the `0x44DEC1` table is a resource-registration table, not glyphs), so the layer may not exist at all. | **UNMEASURED** | One `GetChildCount()` on `0x48E945B4`, or a second `BMPX draw` line for it, in the same pass as Q1. **Settle before choosing the sharp-art route.** |
| **Q3** | Which reading of "udriveit bubble" did the user mean — **R1** the in-world marker `0x48E945B4`, or **R2** the mission *proposal* popup / whole UDI HUD? The user has called those "bubbles" before (`_tests\REGRESSION.md` ~v2.25.19, *"I clicked multiple and one is still open"*). | **This document assumes R1 throughout, and R1 is what #46/#60 called "the bubble" and what the user confirmed as "markers are 2x now".** | ASK. The stakes are asymmetric: **R1 costs almost nothing; R2 means a whole extra DialogStatic build at factor 2f PLUS a FontStyle at 2f** (font sizes 40–128 at UI 2x) and **manufactures the #41/#42/#57 defect family deliberately** — the exact thing §2 refuses. Do not silently assume. |
| **Q4** | Are there any **pre-rendered text art** assets (art whose pixels are typeset glyphs) that would need the text axis rather than the art axis? | **STRUCTURAL NULL, declared honestly.** `tools\dbpf\extracted-png-tgi.csv` has no name column — 2281 rows of TGI + offset only — so a name-based scan **could not have found them**, pass or fail. The only text-shaped art positively identified from our own docs is the advice-row "X" glyph in the `0x1441625x` sheet (`build_selective_safe.py`, grep `range(0x14416250, 0x1441625F + 1)` — the CODE_BOUND range, and `sc4://HTML/46a006b0/1441625X` for the consumer note), which is a pictogram, not typeset copy. | A pixel pass over the 188-PNG scaled set, not an index query. **Low priority given the 1:1 lock** — with text ≡ UI, pre-rendered text art is on the same factor as everything else and cannot desync. It only becomes urgent if the lock is ever revisited. |
| **Q5** | The **predicted 1x-flash**: because the marker's window is scaled by the periodic sweep but **born art-sized**, a freshly appearing marker should draw at `32f` for up to one sweep interval before jumping to `32f²`. | `[INF]` **predicted, unobserved** — derived from the born-art-sized fact (§3.2 step 2) and the sweep cadence, not seen | One look during the eyes-on that increment 1 needs anyway. If real, it is the ordinary reactive-sweep flash family and the cure is the known one: make it born-correct. |
| **Q6** | Does the fit clamp bite at f = 1.5? Today `m = gBmpScale` and `winW/artW` are **exactly** equal, so the draw sits on a knife edge; `ScaleRound(l+48, 1.5) - ScaleRound(l, 1.5)` can land 71 rather than 72 depending on `l`, silently clamping `m` to 1.479. | `[INF]` the arithmetic is certain; the `l` values actually in play are **not measured** | Log the modelled `winW` and `m` for the marker at f = 1.5 over a few mission spawns. **Mitigated for free** by the §4.4 requirement to compute `m` from the live window and warn on a >0.01 disagreement — do that regardless of the answer. |
| **Q7** | Do the `kMayorFlyoutDock` offsets (`R = -marker(1x)` × f) still land if a flyout's content is sized on a different axis than its marker? | `[INF]` **moot under the 1:1 lock** — recorded only so a future reader who reopens §2 knows this was never measured at split axes | Would need a split-axis build to measure. **Do not build one to find out.** |
| **Q8** | At 4x, does the DialogStatic box:point corpus stay clean (0 regressions, min ratio ≥ 1.000) as it does at 2x and 3x? | `[INF]` expected — 4x is an even factor like 2x, and the 1.5x regressions came from odd-point styles rounding up faster than even boxes | One run of the proposed `Test-TextBoxFit` gate (§5.4 — never written) with factor 4 added. **Backlog only** (§7). |

---

## APPENDIX — corrections this catalog made to earlier notes

`[M]` Verified against source when this catalog was written (2026-08-03); earlier drafts and adjacent notes carried these wrong.

**Read this appendix as a list of SYMBOLS, not of addresses.** Five of the seven corrections below were originally stated as line numbers — the first of them literally one number set against another — and **every one of those numbers has since rotted**, on both sides. What the corrections were actually about (which symbol; that a declaration site is not its consumption site) survives, and is now written as the grep that finds it:

- `gBmpCurId` is **set** inside the draw thunk, not merely declared — `src\UiSpike.cpp`, grep `gBmpCurId = w->GetID()` for the assignment the original correction was pointing at, and `uint32_t gBmpCurId` for the declaration it is not. Both numbers in that correction are dead.
- `kAdviceListNeverTouchIds` is **declared** in one place and **consumed** in another — `src\UiSpike.cpp`, grep `const uint32_t kAdviceListNeverTouchIds[] = {` for the declaration and `for (uint32_t known : kAdviceListNeverTouchIds)` for the consumer. That two-site split *is* the correction; the addresses never were.
- `kFontSizedIds` carries **23 entries** — `src\UiSpike.cpp`, grep `const uint32_t kFontSizedIds[] = {`, consumed by `IsFontSizedId` (grep `inline bool IsFontSizedId`). `[M]` The count is the durable half of this row and it still holds: re-counted from the array literal on 2026-08-30, still 23.
- `ApplyHtmlSizeScale`'s two table writes are in its own body — `src\CodePatches.cpp`, grep `void ApplyHtmlSizeScale` and read the two `ScaleSizeTable(` calls inside it. The stock tables those writes verify against are `kStockHtmlFontSizes` and `kStockHtmlHeadingSizes` (grep each by name); the VAs they patch are `kHtmlFontSizeTable` / `kHtmlHeadingSizeTable`.
- `tools\selective-safe\bubble4x-15x\…094ac89a.png` is a **double-resample and must not ship** — use `tools\upscale\preview-3x\SimCity_1\…094ac89a.png` (§3.6).
- `WarriorUI` gating is settled — the `SyncDat` call exists (`src\ScaleTier.cpp`, grep `z_SC4UIScale_WarriorUI` and take the `SyncDat(` call site among the hits; the post-mortem sits directly above it, grep `#119 (v2.71.3): THIS CALL WAS MISSING`) (#119, v2.71.3; §5.5).
- README package counts are stale in three places (§5.5).
