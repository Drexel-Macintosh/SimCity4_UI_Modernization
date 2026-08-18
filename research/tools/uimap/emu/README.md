# tools\uimap\emu — the LAYOUT EMULATOR (Stage 3)

Predicts a dialog's window rects **without launching SimCity 4**, by running
the game's own layout machine code under Unicorn with the window / font /
service APIs stubbed. Stage 3 of the offline UI model in `METHOD.md` §6;
sibling of `tools\flyout-sim\emu_hittest.py` (which does the same for the
CLICK path) and of `tools\uimap\` Stages 1–2 (builder census / constant map).

| File | What |
|---|---|
| `scale_rules.py` | **THE ONE SCALING MODEL — ~~every gate here imports it.~~ 13 of the 21 `gate_*.py` files import it (corrected 2026-08-16).** The eight that do not are `gate_103_closepath`, `gate_103_twin_ids`, `gate_advice_rowx`, `gate_graphlegend_leftanchor`, `gate_iconcentre`, `gate_ordinance_namex`, `gate_patch_families_combined` and `gate_tp_bmp_fit` — and three of them still round half-up privately: `gate_tp_bmp_fit.py:336` inline (`int(s1 * wf / float(w1x) + 0.5)`), plus `gate_graphlegend_leftanchor.py:102` and `gate_ordinance_namex.py:86` (both `def r`). `--drift` sees none of the three: it inspects only top-level `def` bodies (`scale_rules.py:720`), and of those keeps only names in `_LOCAL_NAMES` — which lists `"R"`, not `"r"` — or bodies containing `floor(` with `0.5` (`:717-719`, `:738-740`). So `0 DRIFT, 2 DUPLICATE` prices two named copies in one file, not the folder. `RoundHalfUp` / `ScaleRound` / edge-derived / the #148 leaf rule / `CellUnit` / `ScaleDim` / the three sheet ROLES / the offset-parity law / the tiled seam algebra, each mirrored from `src\UiSpike.cpp` or `Upscale2x.cs` and named with its source. `--selftest` re-derives all of it (146040 checks) including a **source tripwire** that fails if the C++ or C# it claims to mirror has moved. `--drift` hunts private copies in the sibling files and prices each one against the canon |
| `gate_tiled_seam.py` | **the WRAP-SEAM gate (#160)** — the one question every other gate here answered by skipping it. Where a `blttype=tiled` boundary lands, whether the repeat count changes, whether the sheet outgrew its window. `--pre160` is a **mandatory positive control**: it re-sizes the sheets the pre-fix way and must go red on the strip the user reported |
| `gate_offset_parity.py` | **the OFFSET-PARITY law, evaluated (#152)** — `q \| d` proved by exhaustion, the three measured panels reproduced with the axis they failed on, a corpus census whose integer tiers read exactly zero, and a 92-entry candidate list filtered by CONTAINMENT (not parentage — the measured faces are siblings) |
| `emu_layout.py` | the emulator: stubs, recorder, call-site decoder, acceptance suite |
| `emu_text_extent.py` | **the MEASURED text-extent + wrap model** (#57 legend). Per-glyph Arta metrics read out of the game's own rendered pixels (the shipped fonts are `.mxf`, unreadable by FreeType), the `x2.13-not-x2.00` size law, and the wrap simulator that adjudicates any proposed legend box width. `--selfcheck`, `--extract`, `--wrap`. |
| `prove_chart_legend.py` | **the ACCEPTANCE ORACLE** (#57 legend). **TEN** machine-checked invariants (order/non-overlap, visibility, fit, containment, `f=1` reduction, monotonicity+northstar, rounding, coupled pair, **row pitch**, **frame**) over 11 candidate layouts × 2 font hypotheses × 4 tiers × 2 legend kinds = **10708 checks**, plus I3 over 13 real chart label sets. FOUR statuses — PASS / FAIL / SKIP / **UNDECIDED** — and only PASS is evidence. Calibrated: the candidate reproducing the live 2x defect (11/11 exact) is *required* to go red, as are the two counterexamples that passed the previous revision with zero failures. `--verbose`, `--details`, `--mutate` (22/22, including a perturb-the-certified-candidate family). Gate: `_tests\Test-ChartLegendMath.ps1`. |
| `emu_chart_legend.py` | **the LAYOUT MODEL** behind the oracle (#57). Closed-form, integer-exact re-implementation of `sub_76D3D0`'s legend loop (`0x0076DE95..0x0076E373`), horizontal *and* vertical. Reproduces stock 1x, live 2x, **and the bug** — that third one is what makes it falsifiable |
| `emu_chart_font.py` | the DATA/FONT knob on top of it: what `ChartLabel` (`0xE9C86B5E`) point size the measured stock layout implies |
| `gate_graphlegend_leftanchor.py` | **the BYTE GATE** — 127 checks over the shipped patch. Stock bytes still match the exe; the three re-encoded blocks are length-exact and disassemble back cleanly with both branch targets preserved; constants reduce to stock at `f=1`; every tier carries the **oracle's** certified strip. `--emit` prints the exact hex `src\CodePatches.cpp` must write. **This is the artifact law 50 exists to protect** — diff `--emit` against the C++ after any change to the block encodings |
| `emu_legend_row_oracle.py` | the ROW oracle: one legend row at any `f`, from one formula that must reproduce **both** the measured stock 1x and the measured broken 2x |
| `measure_legend_columns.py` | the authoritative MEASURED column table (1x and 2x) the models are fitted against |
| `numbers_audit_bornlegend.py` | **independent** register-level replay of the patched machine semantics — imports nothing from the model except the two measured font inputs. The second instrument, deliberately built not to share a failure mode |
| `check_candidate_bornlegend.py` | runs the shipped model with exactly the candidate's constants; prints both chart kinds at `f=1` (must reduce to stock) and `f=2` |
| `attack_15x.py` | **RED TEAM** against the oracle at `f=1.5` — read-only adversary that tries to make the gate lie at the one tier with no live capture |
| `break_labelset.py` | **RED TEAM** through the label-set lens: feeds the oracle real shipped label sets it was never fitted on, trying to make it wrong, silent, or crash |
| `emu_trip_legend.py` | the adjudicating probe for the **Trip Types** legend (#98) — the next customer of this machinery |
| `emu_chart_range.py` | the chart's own series max-scan, run offline |
| `measure_lineh_tier.py` | **an instrument, not a model**: given one capture PNG per tier it clears **U1** (`lineHeight` at 1.5x and 3x), the single largest unknown left in the suite. Procedure: `tools\research\_incoming\lineh-tier-capture-procedure.md` |
| `gate_iconfit_rule.py` | **the ICONFIT PREDICATE gate** (#149). Adjudicates a proposed **blit-rewriting** rule — 59 fixtures (19 MEASURED out of the shipped captures, 31 derived from the 837-icon census, 9 assumed), 16 negative controls, per-condition adversaries. Calibrated: the predicate that shipped the white-line regression is *required* to go red, and the gate proves it was also **inert on its own target class**. `--selftest`, `--emit` (the C++-ready block), `-v` |
| `emu_subflyout.py`, `emu_subplace_model.py` | the sub-flyout ancestors of this folder (#50, #95) — `emu_subplace_model.py` is the permanent regression for `SubPlaceTop`/`SubPlaceLeft` |
| `POPUP-VERDICT.md` | **the answer** to the ordinance-popup wrap question, with evidence and the recommended fix as math |
| `RESUME.md` | one command to continue an interrupted run |
| `state.json` | per-case results, flushed after **every** work unit |
| `cache\` | cached call-site decodes (`callsites-<builder>-<len>-<target>.json`) |

*(Table completed 2026-08-03: it previously listed only `emu_layout.py`,
`emu_text_extent.py` and `prove_chart_legend.py`, so nine files on disk —
including the byte gate — had no entry in their own directory's index.)*

Requires Python 3.12 + `capstone` + `unicorn` (already installed for
`tools\flyout-sim`). **Offline only. The exe is opened read-only; the game is
never launched and no game file is ever written.**

---

## Quick start

```
cd tools\uimap\emu
python emu_layout.py --selftest --fresh -v     # the acceptance suite, verbose
python emu_layout.py --selftest --resume       # skip cases already recorded
```

Expected today: **5 pass, 0 fail** (see `POPUP-VERDICT.md` §2).

---

## Running it against any other builder VA

This is the general tool — the popup is just its first customer.

```
python emu_layout.py --builder=0x78B980 --len=0x140 --parent=840x125
```

* `--builder=VA`  start of the code range to scan
* `--len=N`       how many bytes to scan (default `0x200`)
* `--parent=WxH`  the size of the parent window the labels are added to.
                  **Required for align `0x63` (fill)**, which reads the
                  parent's `GetW`/`GetH`. Everything else ignores it.
* `--f=1.5`       scale factor applied to the decoded `x`/`y` — this is how
                  you model a `CodePatches` `round(stock × f)` table before
                  writing it
* `--measure=W,H` force the text extent instead of using the font model
                  (only matters for align `0` / `6`)
* `--resume` / `--fresh`  resume from / discard `state.json`
* `-v`            print every recorded API call as it happens

It prints, per call site, the decoded ten arguments and the predicted rect:

```
builder 0x0078B980 (+0x140)  -> 2 call(s) to sub_779660
  0x0078BA35  id=0x0ABCE000  x=10  y=5   align=0x00 (left@x)
       -> (10,5) 616x12
  0x0078BA81  id=0x0ABCE001  x=15  y=25  align=0x63 (fill(parent))
       -> (15,25) 795x75
```

### One-off label

```
python emu_layout.py --label parent=840x125 x=30 y=50 align=0x63 text=120 \
                     id=0x0ABCE001 style=0xEA85D308
```

`text=` accepts a real string, or an integer meaning "a string this many
characters wide" (call sites give a resource id, not text).

### Tier sweep

```
python -c "import emu_layout as E;\
 [print(f, E.LayoutEmu(E.FontModel(scale=f)).run_label(\
   (0,0,int(round(450*f))-int(round(60*f)),int(round(125*f))),0x0ABCE001,\
   int(round(15*f)),int(round(25*f)),120,0x63,0)['label']) for f in (1,1.5,2,3)]"
```

---

## STATE OF THE MODEL — 2026-08-03

**The goal is a UI emulator good enough that a fix can be adjudicated before it
is built.** We are closer than we have ever been and it is worth being exact
about how much closer, because the gap is where the next four failed patches
live. Four buckets, and nothing may be promoted between them without a
measurement.

### ✅ WHAT IT CAN ADJUDICATE OFFLINE, TODAY

| question | instrument | strength of the answer |
|---|---|---|
| Will a proposed **Graphs legend** geometry collide, overflow, or bury the swatch, at `f = 1 / 1.5 / 2 / 3`, for both chart kinds? | `prove_chart_legend.py` | **Decisive.** 10708 checks, ten invariants, calibrated so the known-bad layout must go red, mutation-audited 22/22 |
| Does a hand-encoded patch **assemble to what we think**, keep its length, land on instruction boundaries, and preserve its branch targets? | `gate_graphlegend_leftanchor.py` | **Decisive, byte-level.** Capstone round-trip; the class of bug it catches (an `imm32` one byte off) is a crash no layout gate can see |
| How wide will a given **string** render at a given point size? | `emu_text_extent.py` | **Strong, with a stated ±3.8 px residual** — measured out of rendered pixels, not queried from a font |
| Where does a **label factory** (`sub_779660`) put a control? | `emu_layout.py` | **Real machine code under Unicorn** for the align branches; anything downstream of `measure()` is a hypothesis, and `--selftest` says which is which |
| **What does a static dialog actually LOOK like** at 1× vs a tier? | `render_dialog.py` | **The first pixel instrument here** (#155). Composites the shipped `.UI` + shipped art the way the engine does — parent-relative areas resolved to absolute, `imagerect` slices at native size, window clip, state 0 for button strips, magenta as transparent — then diffs against the 1× render upscaled NEAREST. **A clean result is NOT proof the screen is clean** (no text, no runtime draws, no edge/tiled blits); a dirty result names an uncovered pixel and where. It earned its keep by producing a *negative*: the region bubble's reported "white lines" are absent from its static composition at every tier, which ruled out the whole art-and-geometry hypothesis in one run |
| Which art sheets are **provably state strips**? | `upscale\find_cell_strips.py` | **Derived from the `.UI` that BINDS each sheet**, not guessed: 193 of 2206. Feeds `Upscale2x --cell-strips`, which samples those per state so one state's ink cannot bleed into the next cell (#156). Scoping the same transform by `CellUnit`'s guess instead moved 1186 sheets and displaced an advisor aperture |
| Will a **mod's own bitmap** still fill its row after scaling — bitmap, `imagerect` crop **and** window all considered? | `gate_tp_bmp_fit.py` | **Decisive now, and it was not before.** It read two of the blit's three numbers and passed the build that shipped half-width stripes; its negative control is the script extracted back out of the DEPLOYED dat (48 findings). Read its header before trusting it — it has been wrong twice |
| Does `CodePatches.cpp` patch anything the model has never seen? | `..\crosscheck.py` | **Strong but narrower than it looks** — see the DEFERRED bucket below |
| Will a **sub-flyout** land where the DLL thinks? | `emu_subplace_model.py` | **Decisive** — validated against the game's own `sub_79AD00` |

### 📏 MEASURED (a number taken from the game, not derived)

* Stock and 2x legend column geometry, both chart kinds (`measure_legend_columns.py`).
* Per-glyph Arta advances at **13 pt and 26 pt only**, from rendered pixels.
* Ink growth **×2.13** per doubling (n=17, mean 2.130, sd 0.026, pooled 2.133).
* `lineHeight` **at 1x and 2x only**.
* Every byte of `sub_76D3D0` quoted anywhere in this suite, read from the shipped exe.

### 🔶 ASSUMED / MODELLED (correct-looking, unproven — treat as hypotheses)

* **Glyph advance at any size other than 13 or 26 pt** is interpolated or
  extrapolated between two anchors. `emu_chart_font.py` prints `~` for these.
  Everything at 1.5x and 3x rests on this.
* **`E3-CORPUS`'s `NMAX = 20`** is *declared*, not proven. (`E2` uses the
  provable `NMAX = 33` and carries no such unknown — prefer it.)
* **The extra text line on two of the nine Garbage rows.** The pitch formula at
  `0x0076E34B` has no group-separator term, so the extra 15 px (1x) / 28 px (2x)
  *must* be a line — but the cause of the break is unproven.
* **The four `H_SCALE` / `H_NONE` checkbox hypotheses.** The oracle proves the
  fix correct under *both*, which is the right way to ship an unknown — but it
  is still an unknown, not a result.

### ❌ WHAT IT STILL CANNOT DO — the honest gap

1. **IT NEVER LOOKS AT A PIXEL.** Every verdict in this folder is arithmetic
   over rects and glyph widths. Nothing here can see a colour, a missing
   sprite, a dangling art reference, a z-order mistake, or a 2x image drawn
   into a 1x box (#98 is exactly that, and this suite would call it fine).
   **"The model passes" and "the screen is right" are different claims.**
2. **VERTICAL IS UNVERIFIED AT THE TIERS WE SHIP ALONGSIDE 2x.** `lineHeight`
   has never been measured at 1.5x or 3x, so **2914 of 10708 checks (27%) are
   SKIPPED**, almost all of them U1/U6. `measure_lineh_tier.py` clears it with
   one capture per tier and is the cheapest open item in the project.
3. **THE GENERATED MODEL DOES NOT KNOW ABOUT THE FIX WE SHIPPED.** Stages 1–2
   (`builders.json` / `constants.json`) have never censused `sub_76D3D0`, so
   `crosscheck.py` carries the eight #57 sites as **DEFERRED** — printed,
   guarded, self-expiring, and **not passes**. The suite in this folder knows
   the builder intimately; the *generated* model does not know it at all.
   Those are two different models and only one of them is regenerable.
4. **NO SCHEMA FOR A REWRITTEN INSTRUCTION BLOCK.** `constants.json` models
   single immediates only. Three of the eight shipped sites are equal-length
   block re-encodings and **cannot** be represented today, regardless of
   census work. This is a known structural limit, written down rather than
   discovered again.
5. **ONE BUILDER, DEEPLY; THE UI, BARELY.** This folder models the Graphs
   legend to the pixel and the ordinance popup to a verdict. It does not model
   the toolbars, the budget family, the advisors, the news reader, or any
   code-painted surface. Coverage of *the UI* is not what these 10708 checks
   measure.
6. **IT CANNOT SEE WINDOWS THAT ARE NOT IN THE `.UI` CORPUS.** The
   code-created census (`..\wincensus.py`, 17 named) is a separate inventory,
   and three creation channels put an unbounded number of windows outside
   *both* (`..\coverage-matrix.md` §0.1).

### The rule that keeps this honest

**A SKIP IS NEVER A PASS, AND NEITHER IS A DEFERRAL.** Every gate here counts
and prints its not-a-pass buckets separately, by named reason. If a future
change makes one of them silent, that is a regression in the gate even if the
gate goes green — which is precisely how `crosscheck.py` went from RED to
GREEN on 2026-08-03 without a single site becoming covered.

---

## What is REAL and what is MODELLED

Do not blur this line when quoting a result.

**Real machine code, executed under Unicorn** (1:1 file-offset == RVA mapping,
`ImageBase 0x400000`, exactly as `tools\flyout-sim`):

| VA | Function |
|---|---|
| `0x00779660` | `sub_779660` — the label factory, all three align branches |
| `0x0099C837` | `cGZWin::SetArea(l,t,r,b)` → stores L,T,R,B at `[this+0xA8..0xB4]` |
| `0x0099C8C5` | `cGZWin::GZWinMoveTo(x,y)` |
| `0x0099C81B` / `0x0099C82A` | `GetW` / `GetH` |
| `0x0099BCE1` | `int32_t* GetArea()` |
| `0x0099BC68` / `0x0099BCB6` | `SetW` / `SetSize` |

**Modelled in python** (needs the live font/resource system):

* `factory->[vt+0x34](id, pText)` — create text window
* `factory->[vt+0x14](styleId)` — font for a style GUID
* `gfx->[vt+0x88](R,G,B)` — pack colour
* **`cIGZWinText::FitWindowToText(b1,b2)`** — the *only* font-dependent step;
  modelled as `area := (L, T, L+measure_w, T+measure_h)`
* `SetFont` / `SetTextColor` / `SetAlignment` / `Release` / `SetID` /
  `SetFlag` / `ChildAdd` / `InvalidateSelf` — recorded no-ops

The two lazily-built singletons `sub_913C72` (win-text factory) and
`sub_913C1A` (graphics system) are intercepted at their entry addresses and
return fake service objects. The exe image is patched **only inside the
emulator's memory**.

### The font-metric callback

`FontModel(scale, char_w, line_h, forced)` — `measure(text, style) -> (w,h)`.
It is a **callback on purpose**: text extents are the one thing the model
cannot derive from the binary. The defaults are a coarse `char_w × len`
estimate and are **not calibrated**; the only calibrated number in the file is
the title's extent (`303x37`), back-solved from the live `697x37` dump via the
align-0 identity `windowW = 1000 − textW`.

**Rule: a prediction that depends on `measure()` is a HYPOTHESIS.** A
prediction that does not (anything built with align `0x63` = fill) is
arithmetic on the binary's own constants and can be quoted directly.
`--selftest` tells you which is which per case.

---

## Resumability

Every completed work unit — one acceptance case, one builder call site — is
written to `state.json` **immediately**, not at the end. Re-running from
scratch is always safe; `--resume` skips anything already marked `done`.
Call-site disassembly is cached in `cache\` so a restart never re-scans.

`state.json` layout:

```json
{ "version": 1,
  "cases": { "accept::BODY 2x ...": { "done": true, "pass": true,
                                      "got": [750,25], "expect": [750,25] },
             "builder::0078B980::0x0078BA35": { "done": true, "result": {...} } } }
```

Delete `state.json` (or pass `--fresh`) to start over.

---

## Extending it to a new builder

1. Find the builder VA (Stage 1 census, or the live dump's window id → the
   `sub_779660` call site).
2. Run `--builder=VA --len=... --parent=WxH` and read the decoded constants.
3. If a call site's args come back `dyn`, they were not immediates — the
   backward push-walk cannot follow a register. Read that site by hand
   (`tools\flyout-sim\disasm_fn.py VA --nostop`) and use `--label`.
4. If the run prints `!! unmodelled <vtable> slot +0xNNN`, the builder touched
   an API the stub table does not implement. Add it to `WIN_STUBS` /
   `TXT_STUBS` / `FAC_STUBS` / `GFX_STUBS` **with its argument count** — the
   count matters, a wrong one desynchronises the stack and the run faults.
   Get it from the callee's `ret N`, or from `cIGZWin.h` / `cIGZWinText.h`
   in `vendor\gzcom-dll\`.

### Known vtable-offset gotchas (paid for once already)

* The game's `cIGZWin` vtable is **`header + 4` from about `+0xE4` onward** —
  there is one extra virtual the SDK header does not list. So real
  `+0x100 = SetID`, `+0x110 = SetFlag(flag,value)`, `+0x10C = GetFlag`,
  `+0xF8 = IsPointInMe`. Below `+0xE0` the header is exact
  (`+0xA4 GetW`, `+0xDC SetArea`, `+0xE0 GZWinMoveTo`, `+0x38 ChildAdd`).
* `cIGZFont`'s header **is** exact — confirmed by `+0x8C = GetLineHeight`.
* `cRZRect` is declared `{x,y,w,h}` but a window's area field holds
  **`{L,T,R,B}`** (`GetW` = `[+0xB0] − [+0xA8]`). Never assume from the name.
* There is **more than one `cIGZWinText` implementation**; the vtable at
  `0x00AE1678` is not the one `sub_779660` creates (its `+0x14` takes one
  argument, the factory's takes two).

---

## 2026-08-06 — THE SUITE CAN NOW LOOK AT A PIXEL

This README used to say, correctly, that the emulator **"NEVER LOOKS AT A
PIXEL"**. That gap cost ten failed theories on #148: every one was checked
against a number instead of against an image.

### `render_flyout.py` — the first OFFLINE COMPOSITOR

Composites a window subtree from the **shipped** art the way GZWinBMP/GZWinBtn
do, and writes a PNG you can actually look at:

- `imagerect` crop when present; otherwise the whole sheet as a `sheetW/states`
  state strip
- magenta `0xFF00FF` punched to alpha (it is SC4's colour KEY, not a colour)
- 1:1 blit at the child's top-left, **not** stretched to fit
- optional green window boxes, so a window/art size disagreement is VISIBLE
- any tier, and either candidate geometry rule (`--rule edges|size`), because
  the staged `.UI` keeps 1x areas at fractional tiers and the runtime rule is
  often the thing in question

```
python render_flyout.py --script T-00000000_G-96a006b0_I-09923283.ui \
                        --tier 15x --out landscape-15x.png
```

It killed two theories in three minutes each, with no build and no launch.

### New gates

| gate | asserts | notes |
|---|---|---|
| `gate_btn_undercover.py` | an art-sized state-strip button's **scaled window == art cell**, both axes. ~~read from the **STAGED** scripts and art. **TWO HALVES:** the `selective-safe` half MODELS the DLL's leaf rule and reports the 1.5× residual; the `dialog-static` half (#155) models nothing — it reads the shipped `area=` verbatim and **FAILS at every tier**~~ **Corrected 2026-08-16 (#170/#171).** The ART is staged, but the 1x design `area=` — and the window the runtime half models from it — is read from the PRISTINE corpus `tools\uiscripts\extracted` and paired to the staged node by DOCUMENT ORDER (`gate_btn_undercover.py:74`, `:142-158`, `:200-207`, `:222-223`; a staged script with no pristine twin falls back to its own area, `:200-201`). **THREE POPULATIONS, not two** (`:46-58`): (1) RUNTIME-SCALED — the staged `.UI` still carries its 1x area, so the gate models the DLL's leaf size-derived rule and REPORTS the 1.5× residual (34 at 1.5×, 0 at 2×/3×); (2) PRE-SCALED DATA — the area ships already multiplied and `ScalePanelRoot` RETURNS before the child loop for a `kDataScaledSubtreeIds` id (`src\UiSpike.cpp:14557`, function at `:14303`; `0x6A15C767`, the advisor strip of `I-cbc905cd`/`I-4a160034`, is the FIRST entry at `src\UiSpike.cpp:5374`), so **no runtime rule reaches these nodes at all** — the shipped `area=` is judged VERBATIM against the staged art cell (`:246-256`) and split by cause: `BUILDER-WRONG` is a hard FAIL at every tier (`:458-463`), an art cell over-snapped by `ScaleDim` is REPORTED (132 at 1.5×, 0 at 2×/3× = #171); (3) `dialog-static` (#155), which does **not fail** on window-vs-cell: it asserts the shipped window equals the SIZE-DERIVED rule re-derived from the 1x design (`:394-397`) and fails at every tier on that alone, while a window≠cell disagreement is only a REPORTED residual (`:399-408`) — 352 of those at 1.5× (`{(0,1):1, (1,0):1, (0,2):347, (0,6):3}`) currently sit under a PASS line (law 92). | the #148 guard, and #155 is the lesson. It had never scanned `dialog-static\` at all, **and** it excused the 1.5× residual with *"the parity class is repaired by the leaf size-derived rule"* — a repair that lives in the RUNTIME sweep, which statically-served dialogs are deliberately excluded from. A gate excusing a defect with a fix that does not run in the path it is not scanning. Negative controls: a pre-fix selective-safe build names Level Terrain + the three Day/Night buttons; the bubble script pulled back out of a deployed v2.97.1 dat names `0x4A560000` |
| `gate_btn_cell_vs_window.py` | **nothing** — REPORT ONLY | records a FALSIFIED law: a GZWinBtn's cell need not match its window in general (420 mismatches at 2x AND 3x on perfect tiers, incl. a 24x6 sheet in a 996-wide window) |
| `gate_imagerect_vs_art.py` | no fractional tier over-extends a partial crop beyond the integer-tier baseline | the thumbnail-split guard. The under-read count it prints is a BASELINE, not a failure — closing it broke the thumbnails twice |
| `gate_tp_bmp_fit.py` | for every third-party `GZWinBMP blttype=normal`, all THREE numbers of the blit: **(A)** `imagerect` may not over-read the bitmap, **(B)** the drawn slice must still **cover its window** as fully as at 1×, **(C)** the pixels the window cuts must be a **repeat of the last pixels it keeps** — B and C both asked at the tier **and at 1×**, failing only where OUR scaling loses what 1× had | the #154 guard, and it has been wrong twice — read this before trusting it. **(i)** First draft asserted "no ink may be clipped": **27 failures on a correct build**, because `blttype=normal` art is clipped not stretched and at f=1.5 one bitmap must serve windows of 427 **and** 428 (odd vs even left edge). **(ii)** Second draft read the window and the bitmap but not the CROP between them — two of three numbers — and **passed the build that shipped half-width stripes**. **(iii)** The first repair of that compared the rect to the BITMAP, which flags the m³ glyph (bitmap snapped 20→32, rect and window both 20→30, two transparent pixels undrawn, nothing wrong). Only coverage-of-the-WINDOW is the question that decides pixels. Negative control is the **real** artefact: extract the script back out of the deployed v2.97.0 dat → `FAIL: 48 findings`. `--selftest` additionally puts the window edge on the rightmost column that differs from its neighbour; 22 of 31 bitmaps are too uniform to be able to fail and are NAMED as untestable, not counted green |

**THE LAW: build the instrument that can SEE the defect class, not another one
that can only COUNT.** Paid for twice — `MMGRID` for the minimap (#146), the
compositor for the flyouts (#148).

---

## 2026-08-14 — GATING A **PREDICATE**, NOT A LAYOUT (`gate_iconfit_rule.py`)

Everything above adjudicates a *geometry*. #149 needed something else: a
**runtime predicate** that decides, per blit, whether to rewrite a source rect.
Its first attempt shipped a white line through UI art because its conditions
were satisfied by an ordinary full-bitmap 1:1 blit (`srcW == bmpW` is trivially
a whole multiple of `bmpW/4`).

| asserts | notes |
|---|---|
| a candidate predicate FIRES on every over-read the game really performs and on NONE of the blits it really performs otherwise | The must-fire fixtures are **measured**, not imagined: the `DSTRIP` probe (`UiSpike.cpp:2412`) recorded 25 distinct blit shapes across the shipped captures, including `src 88x88 (88,0,176,88) dst 88x88 srcTex=176x44` — 1x art in a 2x cell. That one line refutes two of the shipped predicate's conditions |

Three things this gate established that no amount of reasoning had:

1. **The blit on this path is 1:1 and the source offset is in CELL units**
   (`src.left = state × dstW`), so 1x art in an `f`-scaled cell over-reads on
   **both** axes by `f`. `srcH == bmpH` — a shipped condition — is therefore
   the signature of a **full-bitmap** blit and is false for every real
   over-read. The shipped predicate could only ever fire on the wrong thing.
2. **`srcW % stateW == 0` is true only at integer ratios**, so the whole 1.5x
   tier was structurally unreachable, at every icon size.
3. **The rewrite must move all four coordinates**, not just `right`: the state
   index is `src.left / srcW`, and `src.bottom` is the cell height.

**The condition the fix needed and nobody had: UNIFORMITY.** An over-read is
the *same* over-read on both axes (`srcW/stateW == srcH/bmpH`, cross-multiplied
with an operand-derived tolerance because at f=1.5 the two axes round
independently). It excludes a half-bitmap crop drawn 1:1 — which `srcW != bmpW`
does not.

**Negative controls, since a gate that cannot fail proves nothing:** reverting
`srcW != bmpW` must resurrect both real regressions (it does); every condition
gets an **adversary** — a shape only that condition rejects — and must fire the
moment its condition is dropped; the one condition with no adversary is proven
*implied* by sweep, not excused; 72/72 single-pixel perturbations of the
certified fixtures turn the verdict off.

---

## 2026-08-16 — ONE ROUNDING RULE, THE THIRD SHEET ROLE, AND THE TILED SEAM

Three gaps closed, and one **model error inside this folder** found and named on
the way. Every number below is from a real run; every gate carries its
integer-tier control.

### 1. `scale_rules.py` — the rounding rule is no longer copied

`--drift` counted **SEVENTEEN private re-implementations** of the same
three-line rule inside this one folder, under eleven different names:

```
def R      gate_abut_1_5x, gate_art_vs_window
def rhu    gate_btn_undercover, gate_btn_cell_vs_window,
           gate_graphs_banddock, gate_iconfit_rule
def round_half_up  gate_imagerect_vs_art, gate_strip_visible_rows,
                   render_flyout, emu_subflyout
def lround gate_introvid, gate_namicons
def sc     prove_chart_legend, measure_lineh_tier
def sc_up  attack_15x        def scale_len   gate_minimap_snap
def scale_round emu_panel_anchor
(+ private cell_unit / scale_dim in gate_btn_cell_vs_window)
```

They all agreed **today**. They had not agreed the day before: #162 changed
`ScaleRound` in the DLL from llround to `RoundHalfUp`, and each copy had to be
hunted down by hand. **A copy that gets missed does not fail — it keeps
returning the old answer, and the gate built on it certifies the wrong
geometry.**

Fifteen were replaced with an import. The last two are the deliberate tie-break
wrappers in `gate_btn_cell_vs_window.py`, which now delegate to the canon and
keep only the knob. Result:

```
0 DRIFT (disagrees with the DLL today), 2 DUPLICATE
```

**Behaviour-neutral, and proved rather than asserted.** Every touched gate was
run before and after and its output diffed:

```
gate_abut_1_5x  gate_art_vs_window  gate_btn_cell_vs_window
gate_imagerect_vs_art  gate_btn_undercover  gate_iconfit_rule
gate_introvid  gate_namicons  attack_15x  prove_chart_legend
                                    -> all BYTE-IDENTICAL to baseline
```
(`gate_namicons` was already red on task #152 and is still red, identically.
`Test-ChartLegendMath.ps1` still reports `ALL PASS (32 assertions)` and the
mutation audit still reports 22/22, run from a different working directory to
prove the import resolves off the script's own path.)

`--selftest` re-derives the whole model — **146040 checks, 0 failed** — against
exact rational arithmetic rather than against itself, and ends with the control
that matters:

```
  S1 rounding is exact vs Fraction oracle           40004 checks
  S2 llround differs only at negative halves         2500 disagreements
  S3 INTEGER-TIER CONTROL: every rule a no-op       96908 checks
  S4 offset-parity law + 3 measured #152 fixtures     519 checks
  S5 worked examples quoted in REGRESSION.md           11 checks
  S6 role lists: 193 strip  30 nine  10 tiled 121 no-snap
  S7 tiled seam algebra + positive control           5970 checks
  S8 source tripwires on UiSpike.cpp + Upscale2x.cs     9 checks
```

S8 is the point of the file: a **text tripwire** on the nine expressions in
`src\UiSpike.cpp` and `Upscale2x.cs` this module claims to mirror. It cannot
tell you the new code is wrong, only that the code being mirrored has moved —
which is exactly the signal that was missing when #162 changed `ScaleRound`
under eight private copies.

The refuted pre-#162 rule is exported as `llround_scale`, on purpose: a gate
that reports clean under **both** rules is not measuring anything, and the
negative control is now an import rather than a hand edit.

### 2. `gate_tiled_seam.py` — the seam every gate skipped

`gate_art_vs_window.py:195` reads, in full:

```python
if blt == "tiled":
    continue                      # repeats: always covers
```

`gate_btn_undercover`, `gate_imagerect_vs_art` and `gate_tp_bmp_fit` skip it on
the same grounds. **The grounds are true and they are not the question.** Tiling
always covers, so "does the art cover the window" is answered *yes* before it is
asked — and 169 tiled nodes across 78 window shapes were certified by a question
that could not fail. What tiling can still get wrong is WHERE THE SEAM IS.

```
21 tiled image-bound nodes checked per tier (of 169 tiled nodes in the corpus)
   0 LEAF (window = R(w,f), #148)   21 CONTAINER (edge-derived)

   factor  nodes      raw      NEW   T1 drift (report only)
   f=1.0      21       16        0   0 inherent / 0 avoidable  <- stock, subtracted
   f=2.0      21       16        0   0 inherent / 0 avoidable  <- INTEGER CONTROL
   f=3.0      21       16        0   0 inherent / 0 avoidable  <- INTEGER CONTROL
   f=1.5      21       23        7   3 inherent / 0 avoidable  <- the fractional tier
```

Findings are keyed by **(node, metric, AXIS)**, not by node: sixteen of these
sheets already exceed their window at 1x, so the per-node subtraction the
sibling gates use would swallow the whole node and hide a fresh failure on the
other axis. Measured: it hid four.

**Mandatory positive control** — a gate green both before and after a known fix
has reproduced nothing:

```
$ python gate_tiled_seam.py --pre160
   f=1.5      21       34       18   9 inherent / 4 avoidable
          T4=9  T5=9
POSITIVE CONTROL OK: the pre-#160 art sizing puts 18 failure(s) back on the
1.5x list, including T4 on the god toolbar strip {46a006b0,14415876} that the
user reported as "a break in the white line", and the f=2 / f=3 controls
stayed at zero throughout.
```

**A metric it built, ran, and threw away.** The first revision carried a
"last-tile phase" check. It fired 10 times at 1.5x and **zero at 2x and 3x** —
which looks exactly like a defect metric passing its control. It was measuring
the window's own edge-derived rounding a second time and calling it a seam.
**Passing the integer-tier control is necessary and not sufficient.**

T1 (seam drift) is deliberately **report-only**. At f=3/2 a sheet of odd 1x
extent has a period that is not an integer, so the boundary must accumulate half
a pixel per tile no matter what size ships. Counting that as a failure would
condemn the best possible build, and a model that condemns the best possible
build is broken rather than informative (law 88).

### 3. ⛔ THE MODEL ERROR THE CONTROL COULD NOT CATCH

The gate's first revision scaled every window edge-derived and reported **7 new
1.5x overhangs**, led by the god toolbar strip at 527 art vs 526 window. The
integer control was clean throughout. It was still wrong: `UiSpike.cpp` gives a
**leaf** its SIZE, not its edges —

```cpp
if (win->GetChildCount() == 0) { newW = ScaleRound(w, f); ... }   // #148
```

— and both rules are identical at f=2 and f=3, **so no integer-tier control can
ever see the difference.** The finding survived only because the strip turned
out to be a container (its `.UI` gives it a `<CHILDREN>` block of tool buttons),
which the corrected model now says explicitly. `scale_rules.window_extent()`
carries the split and the warning.

⚠ **A number in #160's write-up does not survive that split.** `REGRESSION.md`
records the strip's 1.5x window as 527 = `R(351,1.5)`, the size-derived answer.
The strip has children, so the sweep gives it the edge-derived extent from its
absolute origin 185: `R(536,1.5) - R(185,1.5) = 804 - 278 = 526`. The shipped
1.5x sheet is 527 tall. That one-pixel overhang is what T5 reports, on 7 nodes,
at 1.5x only. **It is a static prediction, not a sighting.**

### 4. `gate_offset_parity.py` — the law that names the axis, evaluated

```
  A  closed form == definition, by exhaustion     772 (d,f) pairs x 4097 frames
     advisor faces (7 x 2 scripts)      off=2,1    f=1.5  -> ('y',)  ok  (user: "high")
     My Sim portraits (21-face grid)    off=3,2    f=1.5  -> ('x',)  ok  (user: "left")
     advisor detail page                off=2,2    f=1.5  -> (none)  ok  (user: "correct at every tier")
  C  corpus census over 330 .UI files, 5635 parent->child edges
     f=1.0     1            0  <- stock identity, must be 0
     f=2.0     1            0  <- INTEGER CONTROL: q=1, must be 0
     f=3.0     1            0  <- INTEGER CONTROL: q=1, must be 0
     f=1.5     2         3825  <- the fractional tier (a POPULATION, not a defect list)
  D  seated insets: 10559 contained pairs with an art-bound host; 7605 carry a
     dying offset at f=1.5; 106 of those are inside the visibility band (<=3px).
     POSITIVE CONTROL: 7 of 7 shipped ADVISOR_FACE_SEATS recovered by the filter
     INTEGER CONTROL: 0 at f=1, 0 at f=2, 0 at f=3 (all must be 0)
     predicted failing axis across 92 candidates: 48 x-only, 7 y-only, 37 both
```

**Two filters were wrong before this one worked, and both failures are recorded
in the gate's own header.** Parent→child edges whose offset dies is **3825 of
5635 — 67.9% of the corpus**, a population rather than a triage list. Narrowing
to "both parent and child bind art" recovered **zero of seven** measured faces,
because #152's faces are `GZWinGen` **SIBLINGS** of their frames and bind **no
art at all** (the portrait is supplied at runtime). Measured in
`T-00000000_G-96a006b0_I-4a160034.ui`: face `0x0A15C7D8` at abs (479,649) 48x52,
frame `0xCA15C7CF` at abs (477,648) 55x94, both at depth 1, offset (2,1).

The relation that works is CONTAINMENT with an art-bound host — derived from the
one measured case, and now **asserted**: a filter that cannot see the defect it
was built from is not a filter. The `<=3px` visibility band is labelled as a
heuristic and taken from the controls (the shipped seats are (2,1), My Sim is
(3,2)), not chosen by taste. The REPAIRED list is read out of
`build_selective_safe.py::ADVISOR_FACE_SEATS` rather than retyped, so the gate
cannot claim a repair the build no longer performs.

### What this changes about the honest gap in §"WHAT IT STILL CANNOT DO"

* Gap 1 (never looks at a pixel) is unchanged — all four new metrics are still
  arithmetic over rects.
* The tiled family is no longer invisible, but **only 21 of 169 tiled nodes are
  priceable**: the other 148 bind no `image=` of their own (mostly clsid
  `0x89e1567c`, which sources its sheet somewhere the `.UI` parser cannot
  follow). `gate_tiled_seam.py` prints that count on every run, pass or fail.
* Nothing here models the pattern INSIDE a tile — nearest-neighbour re-phasing
  (#162) is a different instrument's job.
* Offline "leaf" is read from the static `.UI` child list; the DLL asks
  `GetChildCount()` on the LIVE tree, which can differ wherever code adds
  children at runtime.
* `gate_offset_parity.py`'s 92 candidates are **hypotheses**, not defects.
  STATIC DEFECT = HYPOTHESIS.
