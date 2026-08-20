# Known limitations

Everything below is **measured, documented, and bounded** — each entry names
what the user sees, what causes it, and where it stands. Nothing here is a
mystery; the expensive work of finding and refuting wrong explanations is
already done and lives in the lessons library (`research/laws/`) and the
regression net (`_tests/`). Everything else the release gates check is
green, with the named internal exceptions at the end of this document.

## On screen at scaled tiers

- **Faint hairlines on two mode buttons at 1.5x.** The mayor's-hat and My Sim
  buttons could show a 1px line at 1.5x only. Eight hypotheses were refuted
  by measurement (the 1.5x art is a bit-exact copy of the 1x source; windows
  match their cells; no art underfills), the symptom stopped reproducing
  after the 1.5x art rules of v2.95-v2.99 landed, and the closure is recorded
  honestly: *symptom gone, mechanism never established*. If it ever returns,
  the decoded signal (an 18x2 band tiled across the bottom edge of a
  340x155 buffer) and its candidate sheet are on file.
- **Vertical art residual on some state strips at 1.5x.** 32 of 193 state
  strips carry an art cell 1-2 px taller than their window at 1.5x (a height
  snap protecting a divide the engine never performs); structurally zero at
  2x/3x. A derived subset shipped; the general rule was tried, broke one
  sheet, and was reverted. Whether any of it is visible has never been
  confirmed on screen — at 2x the same buttons look identical, which is the
  standing control.
- **The last item of a flyout is hidden until you scroll, at 1.5x.** The
  bottom item of every flyout is not visible on open, and scrolling to the
  end leaves empty space. It is container-height / scroll-extent arithmetic,
  not art; it was never diagnosed and has no window id or builder on file.
- **The Restore-Toolbars button clips at scaled tiers.** The small button is
  built by the game with no size of its own — size comes entirely from its
  four-frame strip — so with scaled art it is 10 px clipped at birth at 2x.
  Fully decoded (builder, art, id and position are all known); the
  prescribed two-part cure is written down and not yet shipped.
- **The disaster ring at 1.5x is verified by arithmetic, not by composite
  eyes-on.** Ring, strip and bar are one welded shape; every gate is green
  at all tiers, but no gate composites the three sprites, and the on-screen
  composite was never photographed at 1.5x.
- **Icon packages disagree by 2 px on one group at 1.5x (latent, never
  observed on screen).** The item-icon group ships 68 px tall from one
  package and 66 px tall from two others at 1.5x — three implementations of
  the icon-dimension rule disagree, while the integer-tier control reads
  exactly zero at 2x and 3x (which is what makes it a defect and not a
  residual). Nobody has seen it because the affected packages rarely put
  adjacent buttons on one toolbar row. Status: measured and bounded;
  neither 66 nor 68 is a fix until a 1.5x eyes-on control adjudicates.

## Performance and lifecycle

- **First city open of a session is slow with large plugin sets (~54 s).**
  Measured against the same session's second city (9.2 s): 934 MB in 1.9 M
  reads, a saturated single core, and a 15-second stretch that did zero
  disk. It is the game's one-time lazy load of the plugin corpus, CPU-bound
  rather than disk-bound; there is no ini key, hook or call the mod can use
  to trigger it earlier, and prefetching cannot help a load that is not
  waiting on disk. The one lever with a real mechanism — repacking the
  plugin archives into fewer, larger files — would mean modifying another
  mod's files and is not taken.
- **The process can linger after quitting (shutdown spin).** After the game
  window closes, the process sometimes survives with one core pinned. The
  cause is the game's own teardown order: the window manager's valid-window
  set is destroyed before the window tree, so every removal becomes a no-op
  and one retry loop spins. The mod ships a guarded mitigation that releases
  the loop when the spin is measured, plus opt-in per-launch telemetry; the
  spin is intermittent (two runs with byte-identical configuration produced
  opposite outcomes), so the rate, not the mechanism, is what remains
  measured. Fixing the cause would mean patching game code, which this mod
  does not do.

## Coverage boundaries

- **UI and text size are one knob.** A tier gates both the art packages and
  the font table together; "UI at 2x with text at 3x" is not expressible at
  any layer. This was closed by decision, not by impossibility — it could be
  reopened, but it needs a new layer, not a new constant.
- **The intro video does not scale.** The four geometry sites are patched
  and verified applied, and the video still presents at its stock size —
  something downstream of those numbers also decides the presentation rect.
  The patch is necessary but not sufficient, and this is stated plainly
  rather than claimed as working.
- **Some in-world overlays are not scaled.** Zot discs (no-power /
  no-water / no-jobs), the in-world Data Views tint, underground / subway /
  pipe views, in-world traffic-density colouring and the network drag
  preview are drawn by the renderer, not by the window layer the mod scales;
  they have no sizing lever on file. The aircraft landing ring is in the
  same family.
- **Coverage is stated with honest denominators.** Of 298 script-declared
  UI roots, 288 are covered (96.6%); of 17 code-created named windows, 11
  (64.7%); combined 299/315 = 94.9%. Windows that are visible but unnameable
  are deliberately not expressed as a percentage — three creation channels
  (a singleton factory, computed window ids, and art bound by no script) are
  structurally invisible to every offline census.
- **Font line height is measured at 1x and 2x only.** The chart-legend
  acceptance oracle therefore skips its vertical checks at 1.5x and 3x
  (2,914 of 10,708). The fonts are a format no offline tool can read, so the
  number can only come from a rendered capture; the skip is recorded as a
  skip, never as a pass.

## Compatibility and verification boundaries

- **The test history is one machine with a large plugin set.** Every
  eyes-on confirmation to date ran on one installation carrying CAM, NAM and
  a large Plugins folder. The game's plugin scan is recursive, so even the
  "stock" baselines were contaminated once (since corrected). A near-vanilla
  verification pass is a stated condition of the public release, not yet
  taken.
- **The stock-parity bar has never been tested at the pixel level.**
  Geometry parity on the region screen is verified line-by-line against a
  true 800x600 reference; the full pixel A/B ("our UI should look as if it
  were stock") was attempted once, failed because the workstation was
  locked, and was never re-run.
- **2400x1800 windowed has never been launched with the mod.** Tier
  minimums are 1.5x = 1440x1080, 2x = 1920x1440, 3x = 2880x2160; the one
  untested corner is 3x's bottom edge, where height binds and the Graphics
  Options dialog — the tallest design panel — is the first thing to clip.
- **CAM's intro splash artwork ships in the 2x and 3x dialog packages but
  not the 1.5x one.** The splash art lives in CAM's own archive and is
  absent from every stock extract; including it in the ungated dialog
  package redistributes CAM-derived art to users without CAM, and keeping it
  out leaves CAM users without it. This is a licensing decision, not an
  engineering one, and it is recorded as open.
- **The Data Views map's larger fill configuration is designed but not
  built.** The fractional-tier crash (window and power-of-two surface
  disagreeing) is cured; the fill-at-768 layout was designed to the byte and
  remains unbuilt, with one named hazard on file (the message handler reads
  the same field as its copy extent).
- **One latent ordering risk, no user-visible symptom.** The Data Views
  scrollbar sits in two scaling lists; today the panel loop happens to run
  first and record the geometry, and nothing enforces that order — it is
  incidental, not guaranteed. Nothing has ever been observed to break.

## Named internal exceptions (recorded, bounded)

- The NAM icon gate re-derives load-order winners against the **live**
  Plugins folder, so it reads red whenever the live install rests at the
  stock tier (the icon packages renamed aside, and CAM wins the load order
  for icons the mod would normally override). It is environmental, not a
  package defect.
- The patch-family collision gate carries five unregistered cost-box tables
  (shipped without entering the gate's width map), so it is blind to that
  one family and exits red. The rest of the gate block is green.
- The two archive-census tools (`who_owns_tgi.py`, `winning_corpus.py`)
  still carry a hand-written list of seven game archives; the install ships
  nine (the list misses `Intro.dat` and `Sound.dat` — the omission that
  produced the startup-splash defect). The quoted "zero third-party winners
  of stock `.UI` scripts" census never opened the two missing archives, so
  it is a null without a positive control: it may still be zero, and it is
  not yet evidence that it is. The sibling lookup tool already discovers the
  archives instead of listing them; these two have not been brought over.
