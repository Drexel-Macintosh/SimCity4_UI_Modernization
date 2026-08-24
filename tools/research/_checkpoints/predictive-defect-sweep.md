# Predictive Defect Sweep — SC4 UI Scaling @ 2x

**Purpose:** find UI still wrong at 2x BEFORE the user sees it. **Analysis only — no shipping code changed.**
**Started:** 2026-07-30 · Baseline: **SC4UIScale v2.27.3-forcerelayout**
**Method:** METHOD.md levels 1-4 only (docs → SDK headers → existing logs → offline disassembly). No game launched.

---

## RANKING AT A GLANCE

| # | what | mode | confidence | user-visibility | owning layer |
|---|---|---|---|---|---|
| **D1** | Neighbor Deals title Y never doubles — patch site address wrong (`0x77F5B9` → `0x77F5B2`) | A | **PROVEN** | high (title overlaps body) | byte patch |
| **D2** | Data Views small leaves latched at 1x by CENTER-IN-SLOT (`0x4A32CA92` + 8 siblings) | C | **PROVEN** (1 instance) / MEDIUM (siblings) | high (half-size arrows on a HUD panel) | runtime |
| **D3** | `push imm8` ceiling silently clamps 9 budget widths at 2x, 13 at 3x | A | HIGH (clamps) / HYPOTHESIS (2x visibility) | low at 2x, **structural at 1.5x/3x** | runtime pin |
| **D4** | 9 reachable roots ship 1x art although the 2x asset already exists | C | MEDIUM | medium (occupant chips, neighborhood buttons) | art dat |
| H1 | 6 static-doubled roots uninsured against the 4x trap | D | HYPOTHESIS | none today | runtime list |
| H3 | 2 bucket-D roots with no art gap and no coverage | D | HYPOTHESIS | unknown | needs a rect |

**If only one thing is done: D1.** It is a one-line address correction, it is
byte-proven, and the shipping build is already printing the failure at every
launch.

---

## ⚠ CONCURRENCY NOTE (read before acting on anything here)

This sweep ran **while another session was live in the same tree**. Observed:
the game was running (`SC4UIScale.log` written 17:39-17:41), and
`src\UiSpike.cpp`, `src\SC4UIScaleDllDirector.cpp` and `build\Release\SC4UIScale.dll`
were modified at ~17:56 by something other than this sweep (this sweep wrote
**only** `predictive-defect-sweep.md` and `pds-cache\*`).

All findings were **re-verified against the post-17:56 files** and still hold:
`kGZWin_MenuContainer = 0xAA32BCE6` (UiSpike.cpp:2162), the
`centerLeaves=true` call (UiSpike.cpp:7794), the `centerThisLeaf` branch
(UiSpike.cpp:7882-7888) and `{ 0x77F5B9, 0x08 }` (CodePatches.cpp:181) are all
still present. Line numbers may drift; the ids, VAs and byte patterns will not.

---

## IN FLIGHT / NEXT  (cold-resume block)

**Sources EXHAUSTED**
- METHOD.md, HANDOFF.md, UISCRIPTS.md, coverage-matrix.md
- `_tests\last-selective-2x.log` (builder log — the 22 "missing 2x" + 2 CONFLICT lines resolved, see RULED OUT)
- live runtime log snapshot `pds-cache\SC4UIScale-snapshot.log` (548 lines, region view, LiveDumpMs=0 → no full-tree dump available this session)
- `tools\dbpf\extracted-png-tgi.csv` (2280 PNG TGIs = the game's complete art inventory)
- `build_selective_safe.py` CODE_BOUND_TGIS + SCALED_WINDOW_IDS; `build_dialog_static.py` TARGETS + discover_query_family()
- `UiSpike.cpp` kNeverScaleIds / kGodToolFlyoutIds / kGodPanelIds + the city/region sweep enumeration (line ~4020)
- `CodePatches.cpp` kDeptImm8Sites (partially — full site verification IN PROGRESS)
- fresh offline recompute: `pds-cache\art_coverage.py` → `art-coverage-report.txt` + `art-coverage.json`

- `UiSpike.cpp` sweep internals: `ScalePanelRoot`, `ScaleSubtree`, `ScaleMenuFlyouts`, `kAlwaysScaleCityIds`, `kFontSizedIds`, `kDataScaledSubtreeIds`, `kCityDialogIds`
- **ALL CodePatches site tables verified against the exe** — see WHAT WAS PROVEN CLEAN. `kRootOnlyScaleIds` no longer exists (removed with the ticker fix); nothing to review there.

**Sources NOT YET examined** (none of the findings above depend on them; they are where further yield most likely is)
- SC4-UI-ENGINE.md (1168 ln) — esp. §9 "where our own docs contradict each other", and the widget catalogue's per-class scaling rules. **Highest-value remaining read.**
- MAYOR-MODE.md, GOD-MODE-FLYOUTS.md, UI-ART-BINDING.md, ITEMICONS.md, DYNAMIC-CONTROLS.md, BUDGET-DETAIL-ANATOMY.md
- `_tests\REGRESSION.md` read only in parts (lines 95-215, 450-465, 785-800, 1600-1700); `_tests\SCENARIOS.md` not read
- ItemIcons / WebText / ThirdPartyUI builders (only SelectiveArt + DialogStatic were audited)

**NEXT ACTIONS, in order**
1. ~~Resolve H2~~ — DONE, resolved clean (centerLeaves=false on that path).
2. Read SC4-UI-ENGINE.md §9 + the widget catalogue and re-test D4's nine roots against each class's stated scaling rule.
3. When a game session next happens, set `[UiSpike] LiveDumpMs>0`, tour Data Views + Neighbor Deals + the Master eye dialogs, then re-run
   `python _tests\Audit-UnscaledWindows.py` — that measures D1, D2 and D4 in one pass. **The repo currently has no full-tree dump** (the live log this session had `LiveDumpMs=0`), which is the single biggest gap in this sweep.

**Cached artefacts (do not recompute)** — all in `tools\research\_checkpoints\pds-cache\`:
`SC4UIScale-snapshot.log` (live runtime log snapshot) · `art_coverage.py` + `art-coverage-report.txt` + `art-coverage.json` · `verify_patch_sites.py` + `patch-site-verification.txt` · `center_leaf_blast.py` + `center-leaf-blast.txt`

---

## RULED OUT (checked, NOT defects — do not re-chase)

| Candidate | Why it is not a defect |
|---|---|
| Builder log `missing 2x asset, skipped: 22` (140155BA-BF, CD-CF, D8-DF, E7-E8, EE-EF, EC1392AC) | All 22 are **absent from the game entirely** — verified against `tools\dbpf\extracted-png-tgi.csv` (2280 entries, the full PNG inventory): zero hits at 1x, and the same gaps appear in BOTH mirror groups `46a006b0` and `1abe787d`. They are artefacts of the blanket `range(0x140155B4, 0x140155F7+1)` in CODE_BOUND_TGIS covering unused instance numbers. Nothing renders them. |
| `0x299BA0FC` (script I-e9a56248), 12/12 art refs 1x | **Dev Exemplar/Cohort editor** — captions "View Entire Exemplar", "Save All Changed Resources", "Configure Columns", GZWinGrid. Coverage-matrix bucket E, unreachable in shipping gameplay. |
| `0xCBA7FFBD` (I-cba9ef16) | **Lua script debugger** — captions "Breakpoints", "Call Stack", "Script View", "Kill", "Pause". Bucket E. |
| `0xCB40CFDC` (I-cb40cfdc) | Documented DEV twin of the Label Tool (coverage-matrix bucket E caveat). |
| Static-doubled **region-screen** roots absent from kNeverScaleIds (0x0A551C50, 0x4A5BA0E7, 0x6A5BA20C, 0xEA5BA0D1, 0x0A5BA192, 0x0A8CD3EE, 0x0A592004, 0x8A5AB1D0, 0x2A57CB82, 0x2A57DB82) | The **region pass is a WHITELIST**, not a sweep — `UiSpike.cpp` ~line 4048: `if (isRegionPass && !IsRegionPanelId(...)) continue;`. They cannot double-scale no matter what kNeverScaleIds says. |

---

## EXCLUSIONS (owned elsewhere / already accepted — deliberately not reported)
- Ordinance description popup text wrap.
- Region city-select bubble doubled Mayor Rating bar (proven not ours: `RatingArrowPatch=0` still doubles).
- Business Deals empty box at 1x — accepted residual, id **banned** from kCityDialogIds.
- Sliders / spinner arrows / combo width at 1x by design (shared glyphs 46A006A7 / 82B99D9D — need a consumer census first).
- Graphs chart interior — ON HOLD by user (task #57).
- Everything in HANDOFF "USER-CONFIRMED WORKING".

---

# RANKED DEFECT TABLE

Ranked by (confidence × user-visibility). PROVEN items first.

---

## D1 — Neighbor Deals dialog: title Y never doubles (patch site address is wrong)

| field | value |
|---|---|
| **panel / element** | Budget → **Neighbor Deals** detail dialog, department **title** row |
| **id / VA** | window `0x0ABCDE00`; builder `0x77E600-0x781C8E`; **bad site VA `0x0077F5B9`**, **correct site VA `0x0077F5B2`** |
| **failure mode** | **A — EXE-CONST GEOMETRY** |
| **confidence** | **HIGH — PROVEN (byte-verified, and the live log already reports the failure)** |

**EVIDENCE**

1. The shipping build says so out loud. Live runtime log, this session
   (`pds-cache\SC4UIScale-snapshot.log`, v2.27.3):
   ```
   [17:39:40.932] CodePatches: dept imm8 site 0x0077F5B9 bytes unexpected - skipped.
   ```
2. `src\CodePatches.cpp:181` declares `{ 0x77F5B9, 0x08 }, // deals title y (8)`.
   Expected bytes are `6A 08` (`push 8`). The exe at that VA holds:
   ```
   0x77F5B9: BC 0A 52 8B CE E8 ...      <- middle of a push imm32, not a push imm8
   ```
3. The real stanza is **7 bytes earlier**, at `0x77F5B2`:
   ```
   0x77F5B0:  00 51 | 6A 08 | 6A 14 | 68 00 DE BC 0A | 52 | 8B CE | E8 9D A0 FF FF
                 ^     push y  push x   push id 0x0ABCDE00  push  mov ecx,esi  call
                       (8)     (20)
   ```
   `0x77F5B4 = 6A 14` is the deals title **x**, which IS patched and verifies fine.
4. The pattern is confirmed by the three sibling builders in the same table — every
   one puts **y exactly 2 bytes before x**, and the MASTER builder's stanza is
   **byte-identical** to the deals one:
   ```
   bizbox     0x77C260: 6A 05 6A 0A 68 00 E0 BC 0A 51 8B CE E8 ...
   ordinance  0x78BA29: 6A 05 6A 0A 68 00 E0 BC 0A 50 8B CF E8 ...
   master     0x786CA2: 6A 08 6A 14 68 00 DE BC 0A 52 8B CE ...     <- identical
   deals FIX  0x77F5B2: 6A 08 6A 14 68 00 DE BC 0A 52 8B CE ...     <- identical
   ```
   `0x77F5B9` is a transposition of `0x77F5B2`.

**SYMPTOM PREDICTED.** Title x doubles 20→40 but title y stays at **8** while the
title glyphs are ~2x tall (FontStyle doubles all text). Neighbor Deals is the ONE
budget department whose title sits at stock height inside a doubled frame — the
same class of overlap that `v2.25.30` fixed for the Business Deals box and
`v2.27.0` fixed for the ordinance popup. Every sibling department (Master,
bizbox, ordinance popup) already doubles both coordinates, so Neighbor Deals is
visibly inconsistent with its own family.

**PROPOSED FIX — MATH + OWNING LAYER**

- Layer: **byte patch** — `CodePatches.cpp`, `kDeptImm8Sites`.
- Change the site address only; the value math is already correct and general:
  `y = round(stock × f) = round(8 × f)` → f=1 → 8 (identity holds, site is skipped
  by the existing `if (v == s.stock) continue;`), f=1.5 → 12, f=2 → **16**, f=3 → 24.
  All within the `push imm8` ceiling of 127, so no clamp at any shipping tier.
- Entry becomes `{ 0x77F5B2, 0x08 }, // deals title y (8)`.
- Expected startup line changes from `43 imm8` to **`44 imm8`**, and the
  `dept imm8 site 0x0077F5B9 bytes unexpected - skipped.` line **disappears**.
  `_tests\REGRESSION.md` expected-line table needs both updated in the same pass.

**BLAST RADIUS**

- Nothing else consumes `0x77F5B2`. It is one `push imm8` feeding the title-create
  call at `0x77F5BE`, pinned on both sides by `6A 14` (x) and
  `68 00 DE BC 0A` (window id) — a 12-byte signature that occurs at exactly two
  places in the exe (deals + master), and the master copy is a different VA already
  in the table. Verify-before-write makes a wrong hit impossible.
- **Secondary harm being fixed:** a permanently-skipped site erodes the project's
  own tripwire. METHOD.md §4 step 5 makes the site COUNT the detector for "the exe
  or another mod changed under us". A site that can never verify prints a
  skip line every single launch, which trains the reader to treat skip lines as
  noise — the next real drop would be read as normal. Removing it restores the
  signal.
- Risk of the fix: none identified. It cannot regress a working panel because the
  current site writes nothing at all.

---

## D2 — Data Views panel: small leaves permanently frozen at 1x by CENTER-IN-SLOT

| field | value |
|---|---|
| **panel / element** | **Data Views** fold-out (compact bar + expanded pages): the expand/collapse **arrow buttons** and the 24-25px **icon buttons**, plus the 9 legend swatches |
| **id** | container `0xAA32BCE6`; proven instance `0x4A32CA92`; same-class siblings `0xA32CACD4`, `0x0A32CAC3`, `0xEA2871E9` (×2), `0xEA2871D9` + their `24x24` GZWinBMP children; legend `0x8A909E10..18` |
| **failure mode** | **C — LEFT-1x-INSIDE-A-DOUBLED-FRAME** (mechanism: a runtime rule, not a missing asset) |
| **confidence** | **HIGH for `0x4A32CA92` (arithmetically PROVEN from a measured rect). MEDIUM for the 8 siblings** (same rule, same code path, same size class; never separately measured). |

**EVIDENCE — the mechanism, end to end**

1. `UiSpike.cpp:2162` — `const uint32_t kGZWin_MenuContainer = 0xAA32BCE6;` and
   `UiSpike.cpp:4146` calls `ScaleMenuFlyouts(pMenu, ...)` on it. The file's own
   v2.21.0 comment says this id is **NOT** "plop-menu machinery" as the
   spike-era label claimed — **it is the Data Views panel**. The function name
   and its centerLeaves argument still carry the old belief.
2. `UiSpike.cpp:7794` — that path is the **only** caller passing
   `centerLeaves = true`:
   ```cpp
   // centerLeaves: flyout item icons are exemplar-bound 1x art - they
   // center in their doubled slots instead of stretching.
   ScaleSubtree(child, f, 0, &n, true);
   ```
3. `UiSpike.cpp:7882-7899` — the branch keeps the **stock size**:
   ```cpp
   const bool centerThisLeaf = (centerLeaves || settings.spikeCenterSmallLeaves)
       && depth > 0 && win->GetChildCount() == 0
       && w <= settings.spikeCenterLeafMaxPx && h <= settings.spikeCenterLeafMaxPx;
   ...
   win->GZWinMoveTo(newL - l, newT - t);
   ScaleRecord rec = { win->GetID(), w, h, w, h, 0, false };   // scaledW == origW
   ```
   `CenterLeafMaxPx = 48` (Settings.h:70 default **and** the live
   `SC4UIScale.ini`). Because the record says scaledW==origW, the next
   `Classify()` returns **AlreadyScaled**, so the generic city sweep — which
   *does* reach `0xAA32BCE6` since v2.21.2 — can never correct it. **The 1x size
   is latched, not transient.**
4. **The arithmetic proof.** The project's own grand-tour baseline
   (the audit-tour raw dump — retired 2026-08-23, its content transcribed in REGRESSION.md ~line 201) recorded
   `0x4A32CA92` as one of only five on-screen 1x misses:
   ```
   ON-SCREEN    id=0x4A32CA92 d11  pos(979,26) 22x20 kids=0
   ```
   Stock in the LIVE script `I-2bc9060f` is `area=(484,8,506,28)` = 22x20 at (484,8).
   Running the center-in-slot formula at f=2 reproduces the observed rect **exactly**:
   | quantity | formula | value | observed |
   |---|---|---|---|
   | newL | `round(484*2) + (round(506*2)-round(484*2))/2 - 22/2` | **979** | 979 ✔ |
   | newT | `round(8*2) + (round(28*2)-round(8*2))/2 - 20/2` | **26** | 26 ✔ |
   | size | kept at stock | **22x20** | 22x20 ✔ |
   Plain 2x would have been `(968,16) 44x40`. No other code path in the DLL
   produces (979,26); this identifies the branch beyond doubt.
5. **The rule's premise is false for these windows.** It exists for "1x art that
   cannot grow (exemplar-bound icons)". But `refmap.csv` says every one of these
   leaves carries art we **do** ship at 2x:
   | window | stock | art | refmap action |
   |---|---|---|---|
   | `0x4A32CA92` | 22x20 | `46a006b0/144161e0` | SHARED → **clone+retarget** |
   | `0xA32CACD4`, `0x0A32CAC3` | 22x20 | `46a006b0/144161e2` | SHARED → **clone+retarget** |
   | `0xEA2871E9` ×2, `0xEA2871D9` | 24x24 / 25x25 | `46a006b0/14015543` | EXCLUSIVE → **2x-in-place** |
   | 3× unnamed GZWinBMP | 24x24 | `46a006b0/140155ec` | EXCLUSIVE → **2x-in-place** |
   `2x-in-place` is the decisive case: the game loads the doubled bitmap at the
   original TGI, so a **2x image is being drawn into a stock-size window**.
   Full enumeration: `pds-cache\center-leaf-blast.txt` (19 freezable leaves, 9 with 2x art).
6. Corroborating: the rule's original justification is itself stale. The
   `kNeverScaleIds` header records that the zoning/utilities flyout item icons
   *"now ship 2x via z_SC4UIScale_ItemIcons-2x.dat (266 icons) so the doubled
   slots get doubled art"* — i.e. the class of art the centering was invented
   for no longer exists.

**SYMPTOM PREDICTED.** On the Data Views bar the expand/collapse arrows and the
small round icon buttons render at half size, floating in the middle of their
doubled slots, with a doubled bitmap clipped into a stock-size window. This is
precisely how the auditor labelled it: *"REAL MISSES: the user can see these at
half size."*

**PROPOSED FIX — MATH + OWNING LAYER**

- Layer: **runtime** (`UiSpike.cpp`). Two options, both expressible as math:
  1. *Preferred, narrow:* make the centering **art-aware** — center only when the
     window's art is NOT one we ship at f. For every other leaf use the normal
     `w' = round((l+w)·f) − round(l·f)`, which reduces to `w` at f=1.
  2. *Simplest:* pass `centerLeaves = false` at `UiSpike.cpp:7794`. The container
     is Data Views, not a plop menu, and its leaves' art all ships at f.
- Either way the identity holds at f=1 (`round(x·1) = x`), so 1.5x/3x inherit correctly.
- The **latched record** must also be invalidated once, or already-frozen windows
  stay frozen: the fix only takes effect for windows classified `Fresh`.

**BLAST RADIUS**

- Changing the flag affects **all 19 leaves** under `0xAA32BCE6`, not just the 9 with art.
- ⚠ **The 9 legend swatches `0x8A909E10..0x8A909E18` (13x10 GZWinFlatRect, no art)
  are the regression risk.** REGRESSION.md records that Data Views legends are
  *code-managed and re-laid per view-select, requiring a pin-back pass* (v2.21.3).
  Doubling them to 26x20 could fight that pin. Gate the change behind an ini
  lever and verify the legend first — this is the same shape as the v2.25.25
  Business-Deals entry that tore Ordinances.
- `0x0000AAAA` (17x14) is the alignment marker — it must keep its size; the
  marker rule (`reference-sc4-flyout-alignment-marker-rule`) depends on it.
  Any fix must exclude it explicitly.
- No other panel is touched: `ScaleMenuFlyouts` is called only on `0xAA32BCE6`,
  and `settings.spikeCenterSmallLeaves` is **0** in the shipped ini, so no other
  subtree reaches this branch.

---

## D3 — `push imm8` ceiling: 9 budget widths silently clamped at 2x, 13 at 3x

| field | value |
|---|---|
| **panel / element** | **Master Budget** eye-icon sub-dialogs (funding sliders, capacity/monthly/subtotal value columns) + the department slider widths + (f=3 only) the department name column |
| **VA** | `kDeptImm8Sites`: `0x787021`, `0x787072` (90) · `0x7870DD` (120) · `0x787165`, `0x78724A` (85) · `0x788D1B`, `0x78916A` (110) · `0x788527`, `0x78874D`, `0x788B3C`, `0x788FD3` (48, f=3 only). `kOrdinanceInsetSites`: `0x77CC23`, `0x77D0E0` (68) |
| **failure mode** | **A — EXE-CONST GEOMETRY** (encoding limit, not a wrong address) |
| **confidence** | **HIGH that the clamps occur** (arithmetic + the code says so). **HYPOTHESIS on 2x visibility** — the Master dialog is in HANDOFF's user-confirmed list, so at f=2 treat this as *accepted residual + an instrumentation gap*. The **tier** consequence is the real finding. |

**EVIDENCE**

`CodePatches.cpp` `ApplyBudgetFamilyScale`, dept-imm8 loop:
```cpp
long v = std::lround(s.stock * factor);
if (v == s.stock) continue;
if (v < 1) continue;
if (v > 127) v = 127;   // push imm8 ceiling (slider width at f=2)
```
`push imm8` (`6A xx`) cannot encode >127, so `round(stock × f)` is truncated.
Computed over the shipping tables (`pds-cache` transcript):

| tier | sites clamped | worst case |
|---|---|---|
| **1.5x** | 7 | stock 120 → want 180 → **127** (29% short) |
| **2x** | **9** | stock 120 → want 240 → **127** (47% short); slider 110 → 220 → 127 (42%) |
| **3x** | **13** | stock 120 → want 360 → **127** (65% short); name column 48 → 144 → 127 |

**Two distinct problems, and the second is the one that matters:**

1. **Silent clamping (method violation).** METHOD.md §4 step 6 is explicit:
   *"Log every imm8 clamp."* `ApplyOrdinanceInsetScale` obeys — its two clamps
   appear in the live log:
   ```
   [17:39:40.931] CodePatches: ordinance inset 136 clamped to 127 at 0x0077CC23.
   [17:39:40.931] CodePatches: ordinance inset 136 clamped to 127 at 0x0077D0E0.
   ```
   The dept-imm8 loop clamps **7 more sites with no log line at all**. The
   startup summary reports only a site *count* (`43 imm8 + …`), which is
   identical whether a site landed on its exact value or was truncated by 47%.
   So the project's own tripwire cannot see two-thirds of its clamps.
2. **The columns and their positions disagree.** For the Master dialog the
   **x positions are imm32 and scale fully** (`0x787024`→400, `0x787075`→610,
   `0x7871FB`→690, `0x7870E0`→800, `0x787168`→1040) while the **widths are imm8
   and stop at 127**. Position doubles, extent does not — the classic
   half-scaled-column shape, and it gets monotonically worse with f. At 3x the
   name column itself clamps (48→127 instead of 144), which re-opens exactly
   the icon-on-text overlap the ordinance-inset patch was written to prevent.
   This is why HANDOFF's *"treat 1.5x/3x as UNVERIFIED"* is understated: these
   sites are **structurally unable** to reach their tier values, not merely
   untested.

**PROPOSED FIX — MATH + OWNING LAYER**

- The value is unchanged: `width = round(stock × f)`. What must change is the
  **carrier**, because the encoding caps at 127.
- Layer: **runtime pin**, not a byte patch — and the project already has the
  precedent and named it. `CodePatches.cpp:225-228` on the Neighbor Deals combo:
  *"Width 120 is a lea disp8 inside sub_7798C0 (max 127 - cannot hold 240):
  **widened by the runtime combo pin in UiSpike instead**."* Apply that same
  shape to these seven widths.
- The pin must follow METHOD.md §4.1: run **on the sweep** (law 18), pair by
  **id arithmetic** never by the state being corrected (law 19), and be
  **idempotent, size-only, record-free** (law 14).
- Cheap interim (no new mechanism, restores the tripwire): make the dept-imm8
  loop log its clamps like the ordinance loop already does. That alone converts
  a silent 47% error into a visible one.

**BLAST RADIUS**

- The seven widths are read only by their own create calls inside the budget
  builders; verify-before-write already proves each site is unique (all 194
  other sites verify clean — see D1's verifier run).
- A width pin touches windows inside `0x0423278F`/the master dialogs. **`0x0423278F`
  is PERMANENTLY BANNED from `kCityDialogIds`** (law 14, third strike) — the pin
  must therefore be record-free and must not re-use that list.
- Adding log lines changes expected startup output → `_tests\REGRESSION.md`
  expected-line table and `Test-DatIntegrity`/boot assertions must be updated in
  the same pass.

---

## D4 — Nine reachable roots ship 1x art although 2x art already exists for it

| field | value |
|---|---|
| **panel / element** | Sim **occupant chips** (3 scripts) · **Establish / Obliterate neighborhood** buttons · **grid popup** at the advisor-toast origin |
| **ids** | `0x6BFAC122`, `0x8BFAC13E` (I-0bfac164) · `0xCBFACAE1` (I-abfac197) · `0x27DF05BF`, `0x27DF05BE` (I-6a9455c9) · `0x0A41C7B2` (I-0a41be3e), `0x0A41C7B3` (I-0a41be3f) · `0xEACA96DD` (I-6aca9687) |
| **failure mode** | **C — LEFT-1x-INSIDE-A-DOUBLED-FRAME** |
| **confidence** | **MEDIUM** — the art gap is PROVEN from data; the geometry side depends on the sweep actually reaching each root, which no dump in the repo covers. |

**EVIDENCE**

Fresh offline recompute (`pds-cache\art_coverage.py`, which imports the shipping
builder so the parser and the `SCALED_WINDOW_IDS` gate are byte-identical to
what ships): after excluding dev-editor roots, these nine roots are **not** in
`SCALED_WINDOW_IDS`, **not** statically doubled by `build_dialog_static.py`
(query-family auto-discovery modelled), and **not** on any never-scale list —
so nothing ships their art at 2x, while the generic city sweep will double their
geometry.

Every one of their art refs is classified `UNSCALED / untouched` in
`refmap.csv` **but carries `twox_available = yes`** — the 2x asset is already
generated in `tools\upscale\preview\SimCity_1`, merely not staged:

| root | stock | art refs (all UNSCALED→untouched, 2x available) |
|---|---|---|
| `0x6BFAC122` | 46x108 | `1abe787d/6bf47dbd`, `1abe787d/ea32f100`, `46a006b0/13f15214`, `46a006b0/2bf4822d` |
| `0x8BFAC13E` | 46x108 | `1abe787d/6bf47dbd`, `1abe787d/ea32f100`, `46a006b0/13f15214`, `46a006b0/2bf4822c` |
| `0xCBFACAE1` | 46x108 | + `1abe787d/6bf47dbe`, `46a006b0/6bf47dbf` (5 refs) |
| `0x27DF05BF` / `BE` | 46x97 | `1abe787d/ea32f100`, `46a006b0/13f15213`, `46a006b0/13f15214` |
| `0x0A41C7B2` | 62x49 | `46a006b0/14416230` |
| `0x0A41C7B3` | 62x49 | `46a006b0/14416232` |
| `0xEACA96DD` | 94x185 | `46a006b0/144161c0` |

This independently reproduces coverage-matrix bucket D items 6, 7 and 8 — and
confirms they are still open at v2.27.3, whereas bucket D items 3, 4 and 9
(`0x8A8DFCF5`, `0x0A551C53`, `0x000A0000`) have since been closed via
`kNeverScaleIds` + dialog-static. The occupant chips are the same work HANDOFF
lists as *"#47 remainder — occupant chips (measure their class first)"*.

**PROPOSED FIX — MATH + OWNING LAYER**

- Layer: **art dat** — add the roots to `build_selective_safe.SCALED_WINDOW_IDS`.
  That marks their subtrees scaled, so each ref is staged at
  `size' = round(size × f)` and any `imagerect` is rewritten by the same factor.
  No new mechanism; this is the exact cure applied to the budget backgrounds,
  advisor briefings, Data Views, the U-Drive-It dashboard and the four mayor
  flyouts.
- **Do this only together with the runtime side** — the project's own law:
  *"art and runtime must move together, always."* If a root turns out to be
  main-window-parented (outside the sweep), it needs dialog-static instead, and
  shipping 2x art alone would give 2x art in a 1x window.

**BLAST RADIUS**

- ⚠ `1abe787d/ea32f100` and `46a006b0/13f15214` are shared by **all five** chip
  roots; `13f15213`/`13f15214` also appear in the god-mode confirm family.
  The builder's SHARED classifier will clone+retarget rather than replace
  in-place — verify it does not land in `CODE_BOUND_FORCE`.
- ⚠ `0x27DF05BE` is **also** the root of the statically-doubled *Obliterate City
  confirm* (`build_dialog_static.py` target `2a41436c`). One id, two different
  scripts. Marking it scaled in the art builder while dialog-static also doubles
  its other script is exactly the collision class that produced the Establish
  City 4x bug. Measure the parentage of both before touching this id.
- HANDOFF requires measuring the chips' **class** first (portraits are
  runtime-generated and are covered by the BMPX hook, not by art staging).

---

# HYPOTHESES (not proven — do not promote without measurement)

## H1 — 6 static-doubled roots are uninsured against the Establish-City 4x trap

`UiSpike.cpp` states the rule plainly: *"Anything the static dat serves that
lives in the swept tree MUST be listed here [kNeverScaleIds]."* Of 36 roots that
`build_dialog_static.py` doubles, **20 are absent from `kNeverScaleIds`**
(`pds-cache\art-coverage-report.txt`). Ten of those are region-screen roots and
are provably safe (the region pass is a whitelist — see RULED OUT). Of the
remainder, these have **documented** main-window parentage and are safe today:
`0x10000005` (query family), `0x4A9DB60C`/`0xEBB16D71`/`0xEBBC081E` (advisor
toasts), `0x27DF05BE`/`0x6A4D0A59` (god-mode confirms), `0xAA921F4F`.

Left **uninsured with no parentage evidence in the repo**: `0x2A96ED21`
(I-4a89b3f2), `0x6AAEEC4A` (I-eaaeec1b), `0x0A8CD3EE` (Photo Album),
`0x0A592004` (Credits), `0x0A5BA192` (City Import), `0x8A5AB1D0` (Delete City).
These are safe only for as long as an assumption about parentage holds — the
precise shape of the Establish City failure, which the file's own comment says
*"we shipped without noticing"*. **Hardening, not a visible defect.** Cost of
insuring: one id per line, inert if the assumption was right.

## ~~H2~~ — RESOLVED CLEAN, see WHAT WAS PROVEN CLEAN below.

## H3 — two bucket-D roots have no art gap and no coverage: mechanism unknown

`0x6BB92BCB` (Trip-Types legend inset, 181x296, I-abb0120f) and `0xEC1A5CBF`
(U-Drive-It console VARIANT, I-8c1a5c9f) appear in **no** shipping list, yet the
art recompute clears them (their refs are shared with scaled scripts, so the art
ships 2x). Coverage-matrix predicted "quarter-art + 2x-text" for the first and
noted the two audits disagree about it. With 2x art confirmed, the remaining
risk is geometry only. Needs a live rect — no dump in the repo covers either.

---

# WHAT WAS PROVEN CLEAN (negative results worth keeping)

- **All 195 CodePatches sites verify against the exe except one.** The offline
  verifier (`pds-cache\verify_patch_sites.py`, real PE section mapping so the
  `.rdata` HTML tables are checked correctly too) reports **194 OK / 1
  mismatched** — the mismatch is D1. Failure mode A is otherwise exhausted for
  every table currently in the file.
- **No missed twins** in the fixed-signature budget tables: `6A 1E 68 B4 00 00 00`
  → 20 exe hits / 20 listed; `81 E9 C3 00 00 00` → 5/5; `6A 64 68 2C 01 00 00`
  → 5/5. (`68 0D 01 00 00` has 3 exe hits vs 1 listed, but the two extras are at
  `0x0094DFFD`/`0x00956A9D`, far outside the budget builders — a generic
  `push 269`, not a twin. The patcher only writes the listed VA.)
- **The `0x00000202` exclusion in `kFontSizedIds` is harmless.** It was excluded
  because the id collides with a 271-wide GZWinCombo in `I-e9a56248` — which is
  the dev Exemplar/Cohort editor. The spinner it protects is a direct child of
  root `0xAA3AC002`, which is in `kDataScaledSubtreeIds`, so **the sweep never
  descends there** and `kFontSizedIds` is never consulted for it. Its arrow art
  `82B99D9D` is `EXCLUSIVE → 2x-in-place`, so the spinner is correctly sized from
  2x art. No defect. *(Side note: HANDOFF still says spinner arrows `82B99D9D`
  are "1x BY DESIGN" — refmap says otherwise; that is a doc inconsistency for
  SC4-UI-ENGINE.md §9, not a rendering bug.)*
- **The center-in-slot rule reaches ONLY Data Views (was H2).** The concern was
  that the rule's premise — *"flyout item icons are exemplar-bound 1x art"* — is
  stale now that those icons ship 2x (`z_SC4UIScale_ItemIcons-2x.dat`, ItemIcons
  356). It does not matter: the tool-flyout columns `0x8BB27C12`/`0xAB954023` and
  all five mayor flyouts are scaled at `UiSpike.cpp:5956` with
  `ScaleSubtree(win, f, 0, &n, false)` — **centerLeaves = false** — and
  `settings.spikeCenterSmallLeaves` is `0` in the shipped ini. The only caller
  passing `true` is `ScaleMenuFlyouts` (`UiSpike.cpp:7794`), which is only ever
  invoked on `kGZWin_MenuContainer = 0xAA32BCE6`. **D2 is therefore bounded to
  the Data Views subtree** — 19 leaves, not a game-wide class.
- **Four of the five grand-tour on-screen misses are closed.** `0x6A2AEDCA`,
  `0xCA2AEDCD`, `0xCA2AEEC0`, `0xCA2AEDCC` (news ticker children) were fixed when
  the root-only rule for `0xCA2AEDC0` was removed; `0xAA231508` (news reader) is
  now deterministic via `kAlwaysScaleCityIds`. **`0x4A32CA92` is the only one
  never addressed** — it is D2.

