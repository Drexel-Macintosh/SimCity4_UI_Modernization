# Known limitations

Every entry below is measured and bounded: what the player sees, what causes
it, and where the boundary sits — except the one item under "Not yet probed",
which is flagged as such precisely because it does not meet that bar. The
engine reference behind these entries is in `research/laws/`; the offline
regression suite that holds them in place is in `_tests/`.

## On screen at scaled tiers

- **Vertical art residual on some state strips at 1.5x.** 32 of 193 state
  strips carry an art cell 1-2 px taller than their window at 1.5x, the result
  of a height snap that protects a divide the engine never performs. The
  residual is structurally zero at 2x and 3x.
- **The last item of a flyout sits below the fold at 1.5x.** At 1.5x the
  bottom item of a flyout is outside the visible area when the flyout opens,
  and scrolling to the end leaves empty space below it. The cause is
  container-height and scroll-extent arithmetic rather than art.
- ~~**The Restore-Toolbars button clips at scaled tiers.**~~ **CURED in
  v4.5.3.** The game builds this small button with no size of its own — its
  size comes entirely from its four-frame strip, which this mod enlarges — and
  then places it with two hardcoded 1x constants, `GZWinMoveTo(12, viewH−28)`.
  Overflow was `cellH − 28`, and the view height cancels, so it was
  resolution-independent: +1 / +10 / +29 px below the screen edge at
  1.5x / 2x / 3x. A second, larger fault sat on top of it: once the button
  became visible this mod's own panel sweep re-doubled it to 84×76 (2x art in
  a 4x box, 20 px off-screen) — user-confirmed on screen as a visible jump.
  Cured at the source: one 6-byte block patch makes the game's own builder
  emit `(round(12f), viewH − round(28f))`, and the sweep stands down on the
  window once that patch is live. Gated on the enlarged art actually being in
  play, because with the packages stashed the stock 28 is correct.
- **Item icons differ by 2 px between packages at 1.5x.** The item-icon group
  is 68 px tall from one package and 66 px tall from two others at 1.5x: three
  implementations of the icon-dimension rule that agree exactly at 2x and 3x
  and diverge only at the fractional tier. The affected packages rarely place
  adjacent buttons on one toolbar row, which is where a 2 px difference would
  show.
- **Third-party and Carbon-skin art still takes the ragged 1.5x copy.** At
  1.5x the stock corpus is resampled by the v4.8.0 straight-edge hybrid, but
  the third-party lanes — CamUI, the NAM icons, the Web Button and the
  ZCarbon\* skin art — still run the builder with their own flag sets and take
  nearest, so a stroke in that art renders 1 px or 2 px by the parity of its
  origin while the stock chrome beside it renders one width. The hybrid was
  judged on the stock corpus only: none of those lanes was on the screen the
  user judged, and the Carbon skin is not installed on the test machine. A
  resampler change nobody has looked at does not ship; the lanes are wired
  when they can be seen. Runtime-synthesised third-party icons
  (`ScaleTier.cpp` `ResampleCells`) are outside the corpus altogether.
- **1.5x curves are blended, not copied — the residual of the hybrid.** At
  3/2 a run of w source pixels wants 1.5w output pixels, an integer only for
  even w: a copy rule cannot be even, so nearest renders some strokes 1 px and
  some 2 px (#200's default, rejected on screen as ragged), and an average
  cannot be crisp on a straight edge (the pre-#200 default, rejected on screen
  as soft). The hybrid decides per block — a straight edge takes an exact copy
  at one width, every other block (a staircase step, an arc, a picture) takes
  the 2:1 area average — so what remains on screen is the blended curve, the
  same anti-aliasing a vector UI renders at 150%. MEASURED on the shipped
  1.5x corpus, v4.7.2 → v4.8.0: stroke-width consistency 0.2997 → 0.2237
  (cv1 0.319 → 0.232); invented colours 1,270,876 → 6,391,698 px and
  soft_frac 0.419 → 0.564 — those two rises are the price, paid at curves
  only. Lot and building thumbnails (the 485 TGIs the ItemIcons and
  ItemIconsSub packages carry, all group `6a386d26`) keep the ragged-but-hard
  nearest copy by the user's choice — a rendered picture wants hard pixels,
  and the two icon packages are byte-identical to v4.7.2. 2x and 3x are
  untouched: 0 of 2206 sheets changed. Ledger #203 in `_tests/REGRESSION.md`.
- **Two post-launch 1.5x rule changes were gate-verified, not
  launch-verified.** The user's two launches judged the round-1 tree (round 2
  with the thumbnail sheets returned to shipped bytes). Two changes to the
  reference landed after launch 2 and were held by the gates — hybrid parity
  2206 of 2206 sheets byte-equal, key integrity PASS at 1.5/2/3 with no
  exemptions added, the edge-quality report — not by a third launch: the
  straight-tie test no longer wraps at a cell edge (it had handed a first-row
  block the last row as its neighbour), and the nearest-key-mask rule
  replaced nine hand-reverted keyed sheets. Their scope is bounded to the
  first and last block row or column of a cell and to those nine sheets;
  pixel-level compare of the shipped dats against the round-2 dats the user
  saw: SelectiveArt 159 of 696 PNGs differ by 2-20 px each, DialogStatic 10 of
  266 differ by 4-20 px, no entry added or removed. If a 1.5x cell border or a
  keyed sheet looks wrong, this is the first place to look.

## Performance and lifecycle

- **The first city open of a session is slow with large plugin sets (~54 s).**
  Measured against the same session's second city open (9.2 s): 934 MB in
  1.9 M reads, one core saturated, and a 15-second stretch that does zero
  disk. This is the game's one-time lazy load of the plugin corpus, CPU-bound
  rather than disk-bound; no ini key, hook or call triggers it earlier, and
  prefetching cannot help a load that is not waiting on disk. The one lever
  with a real mechanism — repacking the plugin archives into fewer, larger
  files — would modify another mod's files, so the mod leaves them alone.
- **The process can linger after quitting.** After the game window closes, the
  process sometimes survives with one core pinned. The cause is the game's own
  teardown order: the window manager's valid-window set is destroyed before
  the window tree, so every removal becomes a no-op and one retry loop spins.
  The mod ships a guarded mitigation that releases the loop once the spin is
  measured, plus opt-in per-launch telemetry. The spin is intermittent — two
  runs with byte-identical configuration produced opposite outcomes. Removing
  the cause would mean patching game code, which this mod does not do.

## Coverage boundaries

- **UI size and text size are one knob.** A tier gates the art packages and
  the font table together, so a combination such as UI at 2x with text at 3x
  is not expressible at any layer.
- **The intro video presents at its stock size.** The four geometry sites that
  size it are patched and verified applied; the presentation rect is decided
  downstream of those numbers, so the video keeps its stock size at every
  tier.
- **Coverage denominators.** ~~Of 298 script-declared UI roots, 288 are covered
  (96.6%); of 17 code-created named windows, 11 (64.7%); combined 299 of 315,
  94.9%.~~ ⛔ **ALL THREE SUPERSEDED 2026-09-01.** D1 (96.6%) is *retired*, not
  re-measured. `tools/uimap/coverage-matrix.md` §4 had carried a 2026-08-16
  instruction to re-derive "10 root slots / 9 distinct ids" before quoting
  either D1 figure, and that instruction was executed on 2026-09-01 for the
  first time. All nine gaps had closed — but only six genuinely. The other three
  (`0x6BFAC122`, `0x8BFAC13E`, `0xCBFACAE1`) were being counted as covered
  *without being covered*: they sit in `kOwnsBackgroundSheet` in
  `src/UiSpike.cpp`, a DERIVED array they qualify for on art data alone while
  the windows are never created. A numerator that admits windows which never
  render cannot be published, so 96.6% — and the combined 94.9% built on top of
  it — are withdrawn rather than restated. D2 was re-measured the same day and
  is **13 of 17 code-created named windows = 76.5%**, not 11/17 = 64.7%
  (`_tests/REGRESSION.md`, "2026-09-01 — D2 re-measured"; the D1 re-derivation
  under "2026-09-01 — D1 re-derived"). The live figures are stated only by
  `tools/uimap/coverage_rederive.py`, the one tool permitted to state a
  coverage figure: a run on 2026-09-01 prints **93 of 117 distinct stock `.UI`
  root ids reached = 79.5%** over all roots, and, after removing the 27 roots
  the retail game cannot instantiate — Maxis's Lot Editor, a Lua debugger, an
  exemplar editor, three singletons, Simulator Control and three dead design
  variants, each printed every run with its own mechanism and ceilinged at
  `MAX_EXCLUSIONS = 27` — **90/90 = 100% of RETAIL-REACHABLE stock `.UI`
  roots.** That scope phrase is part of the number, not decoration: "100% of
  the UI" would be false while the unbounded code-created channel remains
  untouched by any of this. Windows that are visible but unnameable are deliberately left out of
  the percentage: three creation channels — a singleton factory, computed
  window ids, and art bound by no script — are structurally invisible to any
  offline census. These are the survey's own denominators; the canonical
  headline is 86 of 117 distinct root ids = 73.5% ⛔ SUPERSEDED 2026-09-01: this is no longer the canonical headline. The metric counted only ONE of the mod's delivery mechanisms - a literal in `UiSpike.cpp` - and missed the staged dialog path entirely, undercounting by seven player-facing dialogs that ship PRE-SCALED. Counting both mechanisms gives **93/117 = 79.5%**, and removing the roots the retail game cannot instantiate (Maxis's Lot Editor, Lua debugger and exemplar tooling, each excluded with a named mechanism and a positive control) gave **93/93 = 100% of RETAIL-REACHABLE stock .UI roots** ⛔ SUPERSEDED 2026-09-01 (later the same day): the exclusion list grew 24 → 27 when the standing instruction in `tools/uimap/coverage-matrix.md` §4 — "re-derive '10 root slots / 9 distinct ids' before quoting either" — was executed for the first time. Three unshipped Move In My Sim marker variants (`0x6BFAC122`, `0x8BFAC13E`, `0xCBFACAE1`) were being counted as COVERED without being covered: all three sit in `kOwnsBackgroundSheet` in `src/UiSpike.cpp`, a DERIVED array they qualify for on art data alone, while the windows are never created. Excluding them costs the NUMERATOR three as well as the denominator, so the current figure is **90/90 = 100% of RETAIL-REACHABLE stock .UI roots** (117 total − 27 unreachable = 90, printed by `tools/uimap/coverage_rederive.py`, the only tool permitted to state a coverage figure). The ratio is unchanged, which is the point: an exclusion that costs the numerator cannot have been motivated by wanting a better number. That scope phrase is part of the number: "100% of the UI" would be false while the unbounded code-created channel exists.
  (`tools/uimap/coverage-matrix.md`).
- **Font line height comes from rendered captures.** The fonts are a format no
  offline tool can read, so line height is measured at 1x and 2x from captures
  of the rendered screen. The chart-legend gate checks its vertical placement
  at those two tiers and records the fractional tiers as skipped.

## Not yet probed

- **Six in-world visuals have no ownership census — this is a discovery gap,
  not a proven boundary.** Zot discs (no-power/water/job/car), the in-world
  Data Views tint, the underground/subway/pipe views, in-world
  traffic-density colouring, the network drag preview, and the aircraft
  landing ring have never had a census row: no hook, no imm32 sweep, no
  `AddViewObject` differential has run against any of them. Whether the
  window layer can reach them is genuinely open, not settled — a prior
  version of this document asserted "drawn by the renderer, no sizing
  lever" for all six, which overstated what had actually been measured.
  `research/UNKNOWNS-AND-NEXT-TARGETS.md` §B.1 tracks each with a scored
  next probe and none has been closed: zots (row 3, imm32 sweep then one
  hook), the network drag preview (row 19, `find_imm` on
  `0xA90920`/`0xA9093D`), the in-world Data Views tint (row 22, `AddViewObject`
  differential), the underground/subway/pipe views and traffic-density
  colouring (row 23, same differential), and the aircraft landing ring
  (row 20's note — parked, not closed). Do not cite this item as a
  renderer-only boundary until one of those probes runs.

## Compatibility boundaries

- **Tier minimums bind on height at 3x.** 1.5x requires 1440x1080, 2x requires
  1920x1440, 3x requires 2880x2160. Height is the binding dimension, and the
  Graphics Options dialog — the tallest design panel — is the first element to
  clip when a display falls short.
- **CAM's intro splash art is scaled in the 2x and 3x dialog packages only.**
  The splash art lives in CAM's own archive and appears in no stock extract.
  The 1.5x dialog package leaves it at stock size, so a player running CAM at
  1.5x sees an unscaled splash.
- **Geometry parity, not pixel parity, is the stock-parity bar.** Parity on
  the region screen is verified line-by-line against a true 800x600 reference,
  which fixes positions and extents rather than rendered pixels.
