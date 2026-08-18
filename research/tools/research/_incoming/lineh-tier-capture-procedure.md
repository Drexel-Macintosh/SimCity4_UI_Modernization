# TARGET: the USER, for one sitting at the game. Clears oracle unknown **U1** (`lineH(pt)` at the 1.5x and 3x tiers), and — free, from the same 1.5x launch — **U6** and **U8**. Instrument: `tools\uimap\emu\measure_lineh_tier.py`. Consumer: `tools\uimap\emu\prove_chart_legend.py`.

## WHY (one paragraph, then the steps)

`prove_chart_legend.py` knows `lineH` at **two** point sizes only — 15 px @ 13 pt and
28 px @ 24-26 pt. Two points do not determine the pt→px rule, so **every vertical
check at f=1.5 and f=3 is SKIPPED**: the row stack, the column-overflow test and the
checkbox-pitch test. 1.5x and 3x are both SHIPPED packages, so a whole class of
checks is silent at two of our three tiers, and this one unknown is the largest
single cause of the oracle's 2914 skips. Two captures per tier fix it permanently.

**Your in-game time: about 2 minutes per tier.** Everything else is file flips the
orchestrator does with the game closed.

---

## 1. THE CHART TO OPEN — and the POSITIVE CONTROL

**PRIMARY chart: `Population by Age`.** Nine legend rows, labels `1-10`, `11-20`,
… `81-90`.

This is the label set that gives an **unambiguous ONE-LINE row at every tier**, and
that property is what makes the capture readable at all. The row advance is
`pitch = (lines + separators) × lineH + PAD`, so a pitch only equals `lineH + PAD`
if the row is one line — and at 2x the plain legend's rows are *two* lines each with
pitch 60, so a careless reading writes `60 − 4 = 56` into the oracle as a
"measurement". The by-Age labels are five glyphs each, the narrowest set in the
whole graph LTEXT block, against a certified text box of 72 / 124 / 168 / 263 px at
1x / 1.5x / 2x / 3x. Nothing in that set can wrap at any tier.

**How we will know the capture actually shows that, rather than a chart whose rows
all wrapped:** the script counts the text ink bands **per row** and prints them. Nine
rows each showing exactly one ink line prints `CLEAN: every row renders exactly ONE
line`. Any row showing 2 is excluded, and below three usable row pairs the script
refuses outright rather than reporting a number.

That counter is **proven able to see a wrap** (it is not a structural null): run on
the existing 1x Garbage capture it prints `[1, 1, 1, 1, 1, 1, 1, 2, 2]` — it finds
exactly the two labels the repo already records as `STOCK_WRAPS` ("Waste to Energy",
"Garbage Pollution"), which it was never told about.

**SECONDARY chart: `Garbage`.** Also nine rows, ~15 extra seconds. Worth it: its
stock geometry is already the oracle's ground truth (`M_STOCK` tops/swtops) and its
group separators are known, so it independently exercises PAD and the separator model
at the new tier — and it is the chart the oracle's checkbox-pitch check is written
against. Two of its rows wrap even at stock, which is exactly why it is the
secondary and not the primary.

**Clicks, per launch:**

1. Load your usual test city (the legend rows come from the label list, not the
   data, but a city with history removes all doubt).
2. Click the **Graphs** button in the left-hand mayor-mode button column (chart
   icon). A window titled **Graphs** opens: chart on top, a grid of graph names
   below.
3. Click **`Population by Age`** (middle column of the grid). The chart title
   changes; the legend shows nine rows `1-10` … `81-90`. **Say "captured?" and
   wait** — the capture is taken without touching your window.
   *If that chart does not show nine `NN-NN` rows,* try `Education by Age` (same age
   bands); if neither does, carry on with Garbage alone — the script's CONDITIONAL
   path still measures it, just with fewer usable row pairs. (Which of the two
   by-Age charts owns that label block is not decompiled; the label block itself is
   confirmed vanilla.)
4. Click **`Garbage`** (middle column). Legend shows the nine Garbage rows.
   **Wait for the second capture.**
5. Quit the game normally (do not kill it — it runs elevated and holds our DLL and
   dats open).

Do not move or resize the Graphs window between the two clicks.

---

## 2. FORCING THE TIER

### 2a. TIER 1.5 — AutoScale does all of it. One ini, three keys.

`<HOME>\OneDrive\Documents\SimCity 4\Plugins\SC4GraphicsOptions.ini`

```
WindowMode=Windowed
WindowWidth=1920
WindowHeight=1080
```

`Driver=DirectX` unchanged. **Never save that file with a BOM** — the options DLL
abandons a BOM'd ini and the game boots at stock 1024x768.

Nothing else changes. `SC4UIScale.ini` keeps `AutoScale=1` and `ScaleAll=1`, and the
DLL does the rest: DirectX **Windowed** renders at the *requested* size (not the
panel), `ScaleTier::Decide(1920,1080)` returns **1.50** — 2x is refused because
`558×2 = 1116 > 1080` and the density cap is `min(2.4, 1.8) = 1.8` — and
`SyncStaticLayers(1.5)` enables the three `-15x` dats and installs `FontStyle-15x.ini`
as the live `FontStyle.ini` in **both** Plugins folders. `_tests\Test-BootMatrix.ps1`
already asserts exactly this row (`1920x1080 → tier 1.50, tag -15x`), so this is a
previously exercised configuration, not a new one.

The 1.5x window (1920x1080) fits on the panel, so everything is clickable normally.

**Verify in `SC4UIScale.log` before capturing:**

```
AutoScale: 1920x1080 -> tier 1.50 (scaling active).
CodePatches: graph legend budget x1.50 (8 of 8 sites) - strip 178, ...
```

The second line is load-bearing: if the budget patch declines, the legend is laid out
at the stock 72-px box, the by-Age labels are no longer guaranteed one line, and the
script will refuse.

**Free with this launch:** the log's `CHARTGEO` line prints `WIN[0xA8]` at 1.5x —
that is precisely the measurement **U8** asks for (`winW(1.5)` = 731 or 732), and its
origin feeds the script's `--chart-origin`, which decides **U6**. Keep the log.

### 2b. TIER 3 — AutoScale cannot reach it on this panel. State it plainly.

`Decide()` requires `880×3 = 2640 ≤ width` and a density cap `height/600 ≥ 3`, i.e.
**≥ 2640 × 1800**. The panel is 2400x1600. No on-screen window can select tier 3
honestly, so the choice is between an oversized window and a manual factor.

**PATH A (recommended — no in-game cost, orchestrator staging).** Set the factor by
hand and stage the layers by hand, because with `AutoScale=0` the DLL logs
"layers untouched" and syncs nothing.

Game closed, orchestrator does:

- `SC4UIScale.ini`: `AutoScale=0`, `ScaleFactor=3.0` (leave `ScaleAll=1`).
- In `Documents\SimCity 4\Plugins`: gate the three `-2x` dats off
  (`.dat` → `.dat.x1-disabled`) and the three `-3x` dats on (`.dat.x1-disabled` →
  `.dat`) — `SelectiveArt`, `DialogStatic`, `ItemIcons`.
- Copy `FontStyle-3x.ini` over `FontStyle.ini` in `Documents\SimCity 4\Plugins`
  **and** in `<install>\Plugins` (the game probes the install copy only).
- `SC4GraphicsOptions.ini` stays native `2400x1600 FullScreen`.

**The hazard this path creates, named:** nothing re-syncs the layers, so a missed font
copy renders the legend at 26 pt inside a 3x box and the number gets filed under the
wrong pt — a silent, wrong `LINEH_BY_PT[39]`. Mitigation: the live `FontStyle.ini` is
copied next to the capture and passed to the script as `--fontstyle`, which turns the
point size from an assumption into evidence.

**Expected and NOT a bug at 3x on this panel:** the top status bar is 2640 design px
wide and will overhang the right edge, and the tallest dialogs no longer fit
(`558×3 = 1674 > 1600` — do not open Graphics Options). Neither touches the chart:
the Graphs window is ~514 × ~320 at 1x (its chart alone is a measured 488 × 256), so
at 3x it is roughly 1540 × 960 — inside 2400x1600 with room to spare. If it does
open partly off-screen, drag it by its title bar; the capture is of the whole game
window either way. (The ~320 height is estimated off the stock capture, not measured
to the pixel; the 488 × 256 chart is measured.)
Known bounded impurity: the `zzz-SC4UIScale\` third-party overrides are 2x copies and
stay 2x at f=3; none of them is the Graphs chart, and this capture is used for the
chart legend only.

**Verify in the log before capturing:**

```
AutoScale off: manual ScaleFactor 3.00, layers untouched.
CodePatches: graph legend budget x3.00 (8 of 8 sites) - strip 371, ...
```

**PATH B (fallback, UNPROVEN on this machine).** `Driver=Software`,
`WindowMode=Windowed`, `WindowWidth=2640`, `WindowHeight=1800`. Software renders at
the requested size in every mode, so `Decide()` returns 3.0 legitimately and
`SyncStaticLayers` stages everything itself — the honest version. The cost: the
window is larger than the display, so the bottom ~200 px and right ~240 px are off
screen (the dock is bottom-anchored, so the Graphs button may sit under the edge and
the window has to be dragged up first), and no capture has ever been taken from an
oversized window here — `PrintWindow(PW_RENDERFULLCONTENT)` on a window bigger than
the desktop is untested in this repo. Use it only if Path A's manual staging is
judged too impure to trust.

### 2c. Can both tiers share ONE session?

**One sitting: yes. One launch: no, and it is not close.** The tier is decided once
at DLL load (`PostAppInit`, before the game loads any dat), `FontStyle.ini` is read
by the engine at startup, the static dats are gated on disk before that, and the
eight legend-budget exe patches are written once per process for one factor. Nothing
re-reads any of it at runtime. So it is two launches:

> boot 1.5x → 2 clicks → 2 captures → quit → orchestrator flips config → boot 3x →
> 2 clicks → 2 captures → quit → orchestrator restores.

Total in-game time ≈ 5 minutes including two loads.

---

## 3. WHAT THE ORCHESTRATOR CAPTURES

`tools\capture\CaptureWindow.exe <out.png>` — `PrintWindow(PW_RENDERFULLCONTENT)` of
the game's largest visible top-level window, `SetProcessDPIAware()` first. It does
not steal the foreground and it synthesises no input.

```
_tests\captures\graphs-15x-byage.png      _tests\captures\graphs-3x-byage.png
_tests\captures\graphs-15x-garbage.png    _tests\captures\graphs-3x-garbage.png
_tests\captures\graphs-15x-fontstyle.ini  _tests\captures\graphs-3x-fontstyle.ini   (copies of the LIVE FontStyle.ini)
_tests\captures\graphs-15x-SC4UIScale.log _tests\captures\graphs-3x-SC4UIScale.log
```

Then, per tier:

```
python tools\uimap\emu\measure_lineh_tier.py --selftest
python tools\uimap\emu\measure_lineh_tier.py _tests\captures\graphs-15x-byage.png ^
       --tier 1.5 --fontstyle _tests\captures\graphs-15x-fontstyle.ini ^
       --chart-origin <X,Y from the log's CHARTGEO>
```

Run `--selftest` first every time: it is the instrument's own gate — one positive
control (the known `lineH = 15` must come back out of the 1x Garbage capture) and
three negative controls, including the 56 trap on the 2x live checkbox tops. A gate
that cannot go red is not a gate.

The script prints `lineH` with its uncertainty and the exact one-line oracle edit
(`LINEH_BY_PT[20] = …`, `LINEH_BY_PT[39] = …`), or it REFUSES and names the single
measurement that clears the refusal. It never prints a number it cannot defend.

---

## 4. RESTORE (orchestrator, game closed)

**Use our own code, not a snapshot.** Restore is only two edits, because
`ScaleTier::SyncStaticLayers` is idempotent and self-healing — with `AutoScale=1` it
re-gates *every* installed package to the decided tier and reinstalls the matching
font in both Plugins folders on the next boot, by itself:

1. `SC4UIScale.ini`: `AutoScale=1` (the stale `ScaleFactor=3.0` line is then ignored
   — the director overwrites `spikeScaleFactor` with the tier it decides).
2. `SC4GraphicsOptions.ini`: `WindowMode=FullScreen`, `WindowWidth=2400`,
   `WindowHeight=1600` — **no BOM**.

Boot once and confirm both lines:

```
AutoScale: 2400x1600 -> tier 2.00 (scaling active).
CodePatches: graph legend budget x2.00 (8 of 8 sites) - strip 240, ...
```

⚠ **Do NOT use `_working-backup\GOLDEN-*\Restore-Golden.ps1` for this.** It restores a
2026-07-22/23 snapshot of `Documents-Plugins` wholesale — including `SC4UIScale.dll`
— which would roll the shipped build back past v2.55.0 and undo today's #57 fix. It
also kills the running game. It is the right tool for "the live config is broken and
I want the known-good July state back", and the wrong tool for undoing a two-key
experiment.

Belt and braces, before §2b touches anything: record the pre-state (which
`z_SC4UIScale_*` files are `.dat` vs `.dat.x1-disabled`, the SHA-256 of both
`FontStyle.ini` copies, and the `AutoScale`/`ScaleFactor`/`WindowMode`/`WindowWidth`/
`WindowHeight` values) to `_tests\captures\prestate-lineh-tier.txt`, so the restore
is checkable rather than remembered.

---

## 5. WHAT THIS DOES AND DOES NOT SETTLE

- **Settles:** `lineH(20)` and `lineH(39)`, i.e. `LINEH_BY_PT` at the two shipped
  tiers where it is currently unknown. Those two integers un-skip the row stack, the
  column-overflow test and the checkbox-pitch test at f=1.5 and f=3.
- **Settles, same 1.5x launch, from the log rather than the pixels:** U8 (`winW` at
  1.5x — 731 vs 732, task #75's container-vs-child divergence reaching the chart
  frame) and, with `--chart-origin`, U6 (the swatch vertical rule: `sc(3,f)` vs
  `round(3*lineH/15)`, which agree at 1x/2x and diverge at 1.5x/3x).
- **Does NOT settle:** U5 (whether TOP and PAD *should* scale in a fix) — the
  captures measure what the shipped build does, not what a future candidate should
  do; and U7 (the corpus NMAX bound). Both stay unknowns, marked.
- **PAD = 4 is an INPUT here, not a measurement** (0x0076E34B, deliberately
  unpatched). The script's PAD-free leg — every pitch must differ from the minimum by
  a whole multiple of `lineH` — is the one that does not lean on it, and it is what
  catches the all-rows-wrapped case that would otherwise ship a doubled `lineH`.
