# Changelog

All notable changes to **SC4UIScale** — runtime UI scaling for SimCity 4
Deluxe (build 1.1.641) — newest first. The game renders the world at your
display's native resolution while every interface element is drawn at
**1.5x, 2x or 3x**; AutoScale picks the largest tier your resolution can
carry, and the in-game selector lets you override it.

Several internal builds usually served one user-visible goal, so closely
related builds are grouped into one entry below. Nothing on disk is ever
modified except the mod's own files; all scaling is in-memory per session.

## 4.0.0 - public release preparation

The first public release. Everything before this entry was the development
series that produced it.

- **In-game scale selector, final form.** The selector introduced in v3.2.0
  and hardened through v3.13 ships as the v3.14 state machine (below): one
  pure derive, changes committed only when the dialog is accepted, and a
  standing performance instrument that proves every open is instant.
- **Documentation restructured for a public audience.** The engineering
  ledger and session notes were distilled into three durable forms: a
  lessons-learned library (`research/laws/`), an SDK-grade reference for the
  game's UI engine (`research/`, `tools/research/`), and offline simulators
  and gates that reproduce the engine's arithmetic without launching the
  game (`tools/uimap/`, `_tests/`).
- **Work-in-progress documentation removed.** The repository no longer
  carries open defect lists, probe plans, or session state. What remains is
  shipped product, reference documentation, the regression net, and
  `research/KNOWN-LIMITATIONS.md` — the honest, bounded list of what the
  mod does not do.
- Release bundle verified end to end: every file in the distribution is
  byte-identical to the build it was cut from (`SHA256SUMS.txt` included).

## 3.14.0 - 3.14.4 — the selector becomes a state machine (2026-08-20)

- **Selector rewritten as a state machine.** Six generations of mechanism
  were replaced by one design: a single state snapshot read at defined
  moments, one pure function that derives the whole dialog from it, and a
  diff-apply that rebuilds a dropdown only when its derived rows actually
  change. Closing the dialog commits only the settings that changed; an
  untouched visit writes nothing.
- **Your scale pick is a request, never overwritten.** The effective row is
  derived fresh each time as "your request if it fits the screen, else
  Auto". Pick a resolution the request no longer fits and the row falls to
  Auto by itself; pick the old resolution back and your request returns —
  no hidden state either way.
- **Crash fix: Accepting Graphic Options with a city loaded.** With a city
  running the game *destroys* the Graphic Options dialog on Accept (the main
  menu only hides it). The selector's close handler could re-read a dialog
  that no longer existed. It now checks whether the dialog is still alive at
  close and takes the safe path when it is not; both outcomes are now
  structurally safe.
- **Layout polish.** The redundant radio button beside the scale dropdown
  was removed; the Resolution and Scale rows now sit on the same aligned
  band; the scale dropdown carries a "Scale" caption matching "Window Mode"
  and "Resolution". All geometry is derived from the dialog's own clip
  arithmetic, so nothing can be cut off at any tier.
- **Dropdowns are one uniform colour.** The engine's combo drop-list paints
  its standard list colour regardless of script attributes; the selector now
  joins that standard, so the closed field, the open list and its surround
  are one colour — the exact look of the game's own stock combos.
- The performance instrument that measured the v3.13 freeze stays in the
  build (per-pass cost table, frame-gap and pass watchdogs), so any future
  slowdown is named, not guessed.

## 3.13.2 - 3.13.3 — the Graphic Options freeze fix (2026-08-20)

- **Fixed: the first open of Graphic Options could freeze the game for
  several seconds.** An in-memory timing instrument proved the cause in one
  launch: the first enumeration of display modes through dgVoodoo's
  virtualized display costs over three seconds, and it ran on the UI thread
  at the one moment you are guaranteed to be watching — the first click.
- **Cure:** the resolution list is now enumerated once, on a background
  thread, while the game is still loading. A tri-state handshake
  (idle / enumerating / done) means the dialog's only race path is a
  correctness net, and the first open is instant. The log line that proved
  the defect now carries its own duration, so the cure is measurable in the
  same line.
- **Fixed: the Windowed mode list was empty.** The list builder had a branch
  for Borderless and one for Fullscreen and none at all for Windowed; the
  dropdown was empty at birth. Windowed now offers the familiar sizes below
  your desktop size (a window at desktop size is Borderless's job).
- The selector's behaviour specification was written first as an offline
  test (`_tests/Test-SelectorDerive.py`) and the code mirrors it rule for
  rule.

## 3.3.0 - 3.13.1 — selector hardening (2026-08-19 → 2026-08-20)

Twenty-odd builds that turned the new selector into something you can trust.
Highlights, all user-visible:

- **Borderless mode added**, and the fullscreen list now contains only sizes
  your display actually reports (removes the pink scrollbar of impossible
  modes).
- **Resolution and Window Mode dropdowns write both configuration files
  together** — the game's `SC4GraphicsOptions.ini` and dgVoodoo's config —
  so the two can never disagree about what "fullscreen" means.
- **The dropdown shows what you chose**, and the readout names the
  resolution that will actually apply. The restart popup is gone; the dialog
  uses the game's own "settings apply on next launch" notice.
- **Accept is the only exit.** Cancel and Default Settings are disabled for
  the selector's rows, so a stray click can never discard or reset a choice
  you have not reviewed.
- **Per-tier minimum resolutions are explicit**, and a boot-time coherence
  check validates the whole configuration file (twenty-six audited failure
  modes) and repairs it to a runnable state instead of letting a hand-edited
  file trap you.
- **Window Mode and Resolution rows hide themselves** when the companion
  plugin that owns them (`SC4GraphicsOptions.dll`) is not installed.
- The resolution list no longer ratchets one-way in fullscreen, and the
  hundreds of file reads per click that the first design cost were cached
  away — the measurement that finished the job is the v3.13.3 freeze fix.

## 3.2.0 - 3.2.3 — in-game scale selector introduced (2026-08-19)

- **New: change the scale from inside the game.** Graphic Options gains a
  UI Scale picker offering **Auto / 1x / 1.5x / 2x / 3x**. The choice
  applies on restart — switching tier moves nine art packages and the font
  table the game reads once at startup, so nothing short of a relaunch can
  do it. The dialog already carries the game's own notice that its settings
  take effect next launch, which is why the control belongs there.
- **Tiers your screen cannot carry are refused, not silently ignored.** At a
  resolution with no room for 3x, the row names the size 3x needs and snaps
  back if selected. The fit rule shown to you is the same one the next boot
  uses.
- **A refused choice bounces to Auto** — the one row that always fits — and
  the configuration file is updated to match, so the control never lies
  about what will happen.
- **A manual tier that no longer fits is rescued at boot.** If you picked 3x
  on a large display and later run on a smaller one, the UI would scale past
  the screen — and the control that fixes it would be the first thing
  off-screen. The factor is now checked against the resolution at boot and
  falls back to Auto, writing the fallback back so file, selector and screen
  all agree.
- **1x is no longer a one-way door.** At the stock tier the mod deliberately
  installs nothing — which would also have stashed the one control that lets
  you leave 1x. A dedicated single-entry package now keeps the selector
  visible at stock geometry, and a minimal tick services it and nothing else.
  Taking a true-stock reference capture still gets absolute isolation.
- **Fixed: choosing 1x left the previous tier's art armed**, breaking the
  whole UI (1x geometry over 2x art). The static-layer sync now runs for a
  deliberate 1x choice and stashes every package, which is exactly what
  picking 1x means.

## 3.1.0 - 3.1.2 — Move In My Sim marker, resident portraits, dispatch counts (2026-08-19)

- **Fixed: the Move In My Sim marker** — the framed sim face and arrow over
  a candidate house — rendered pixel-identical at every tier while the rest
  of the UI scaled. It now scales at 1.5x / 2x / 3x, and its tip lands on
  the house instead of half a marker down-and-right.
- **Fixed: some resident sim faces drew magnified to their top-left corner**
  in the "<name> lives here" marker. The default faces were never staged
  with the named ones; every face the indicator can bind now ships at the
  same size in every tier.
- **Fixed: the count under a dispatch hat vanished at 2x** (the text plate
  height stayed at 1x while the glyphs doubled), and a 1.5x-only rounding
  fault behind the deployment counts was corrected with the project's single
  rounding convention.
- **The 1x baseline is now genuinely inert.** A default of 2.0 in an
  internal factor mirror meant tier-1 code paths behaved as if scaled; every
  subsystem now forces off at factor 1 regardless of how the factor was
  chosen.
- Tier tooling reduced to one call: tier and screen settings are applied
  together (packages, font table, graphics ini, dgVoodoo config), with new
  gates against tier drift between packages.

## 3.0.0 - 3.0.38 — third-party menu icons automatic; the U-Drive-It balloon (2026-08-15 → 2026-08-18)

- **New: custom third-party lot and menu icons are enlarged automatically.**
  Any lot menu icon you install after this mod's art packages were built
  used to draw doubled at rest and blank on hover — broken by us, since we
  enlarge the menu's state cells. At boot the DLL now indexes every DBPF
  under `Plugins` (index reads only, ~50-190 ms), compares item-icon
  resources against the ones our packages supply, and enlarges whatever is
  left over before any menu asks for it. No download, no extra package, no
  action. Confirmed automatic on real Simtropolis downloads at both 1.5x and
  2x. An offline escape hatch rebuilds an override package for the rare mod
  whose own strip is malformed.
- **Fixed: the U-Drive-It offer balloon** (and the shared dispatch pin it
  rides on) now scale with the tier. The balloon is a city-situation
  indicator drawn by two screen-space quads whose sizes live inside
  machine instructions rather than data; both were decoded and patched.
  User-confirmed at 3x (3840x2160) and on the shared dispatch path at 1.5x.
  The hunt cost ~17 launches; the lesson — a data-section constant sweep is
  blind to inline immediates — is in `research/laws/`.
- **Fixed: the HUD mayor-rating bar** could draw its fill short of the
  groove (the classic "half bar"). The bar's composer latches a crop from
  the window's size at bind time and never refreshes it; the resize pass now
  carries the latch across, guarded by the latch's own signature. The old
  tier-dependent appearance was never real — sixty-one captured sessions
  showed the same timing race at every tier.
- **Fixed: manual tier mode now syncs the static layers** (with AutoScale
  off, a package could stay armed for the wrong tier while the boot scan
  counted its icons as covered).
- Text-seat batch residue from the valign fixes and a one-sheet bubble pin
  were cleaned up in the same series.

## 2.99.0 — cell-aligned sampling for state strips (2026-08-14)

- **Fixed: three bright slivers at the right end of the region bubble's
  population rows at 1.5x.** Once a sheet's width is snapped to keep its
  state cells whole, a global sampler and the snap disagree and cell
  boundaries drift — three columns of the next state bled into the previous
  cell. State strips are now sampled per state cell, scoped by a list
  derived from the `.UI` scripts that actually bind each sheet (193 proven
  strips), never by heuristic. At 2x and 3x the change is byte-identical —
  measured, not argued. User-confirmed: "lines are gone, region screen is
  clean."

## 2.98.0 — static dialogs get the runtime cure too (2026-08-13)

- **Fixed: tearing beside the play button and the population readout on the
  region city bubble.** The earlier cure for art cells taller than their
  windows had landed in the runtime path only; the statically doubled
  dialogs never got it. Both paths now agree.

## 2.97.0 - 2.97.1 — CAM's own dialogs scaled (2026-08-13)

- **Fixed: CAM's own windows were never scaled at all.** The city info
  screen ("MZ v1") showed labels cut mid-word with percentages printed over
  them; the civic and school query panels had the same defect. A mod-added
  window is in no target list and has no stock twin, so every gate stayed
  green while it rendered at 1x for the project's whole life. All three
  dialogs — plus nine of CAM's own bitmaps — now ship scaled at every tier,
  and a new gate asserts nothing visible is clipped that 1x kept.
- The DLL's reported version string now matches the shipped binary (it had
  been lagging several releases behind, verified in the deployed bytes).

## 2.96.0 — the 1.5x offset family closed (2026-08-13)

- **Fixed: advisor portraits sat one pixel high and My Sim portraits one
  pixel left at 1.5x.** Edge-derived rounding preserves a child's offset
  only when the offset times the factor is whole — at 1.5x every odd offset
  is a lottery on its frame's position, and at integer factors none can
  fail. The cure seats each child from its frame plus the scaled offset
  instead of nudging edges; it translates only, caps at one pixel, and is a
  measured no-op at 2x and 3x (0 of 22 and 0 of 14 windows moved).
  User-confirmed. With this, every reported 1.5x defect to date was closed
  and confirmed on screen.

## 2.95.0 — the 1.5x art family closed (2026-08-09)

- **Fixed, user-confirmed: disaster-flyout thumbnails (hover slide and
  wrap), Monthly Budget rows, menu icons generally, the reverse-L edge
  defect, and CAM's missing "Exported" graph caption.** Three measured
  causes, all data-side: six of nine packages had never been rebuilt after
  the previous day's rule fix; a height snap was applied to strips the
  engine only ever divides horizontally; and the sampler re-registered every
  fractional sheet's pixels by one. The 2x and 3x sets were regenerated and
  proven untouched (0 of 2206 files changed at 2x).

## 2.94.0 - 2.94.2 — the oversized-art family (2026-08-06)

- **Fixed: icons and portraits drawn larger than their buttons at 1.5x**
  (thumbnails, My Sim grid, advisors, budget rows). The dimension snap
  introduced for 1.5x had taken a least-common-multiple of every plausible
  cell count and overshot; it now snaps only to the two divides the engine
  actually performs (nine-slice thirds and four-state strips).
- **Fixed: the "reverse L"** — an uncovered right column and bottom row on
  some 1.5x controls. Leaf windows now take their size from the scaled
  dimensions rather than from two independently rounded edges; containers
  keep edge-derived rounding so abutting pieces stay abutting. The branch
  cannot fire at integer factors by construction.
- **CAM's Power/Water graphs gain their missing fourth legend caption.**
  CAM's chart data declares four series but binds a label resource that
  exists in no installed archive (a one-nibble typo upstream). We supply the
  missing resource in a small inert-until-CAM package; CAM's files are
  untouched and the gap was reported upstream.

## 2.93.0 - 2.93.2 — NAM icons, the startup splash, city-open cost (2026-08-05 → 2026-08-06)

- **New: NAM compatibility package** — 392 Network Addon Mod menu icons,
  upscaled from NAM's own artwork, gated on NAM's controller file being
  installed. NAM icons used to draw doubled inside doubled cells and blank
  on hover. Coverage is defined as "our file loads last for this resource",
  which is the question that actually decides what the game displays.
- **Fixed: the startup splash tiling 2x2** ("the SimCity logo appearing four
  times"). The tiled background was being fetched from the wrong archive —
  the lookup tool carried a hand-written list of seven game archives when
  the install ships nine. The tool now discovers the archives; the splash
  background comes from the game's own.
- **The first city open with a large plugin set was measured, not guessed**:
  ~54 s for city #1 versus ~9 s for city #2 in the same session — a one-time
  lazy load of the plugin corpus, CPU-saturated, with no lever the mod can
  reach. It is documented in `research/KNOWN-LIMITATIONS.md` rather than
  claimed as anything else.
- **1.5x cell divides:** the game's own integer cell divisions stop being
  exact at fractional factors; scaled sheet dimensions are now snapped so
  the divides stay whole (the rule that produced the family corrected in
  v2.94/v2.95 — kept because the snap itself is right and load-bearing).
- A stray build-machine path was found embedded in the DLL as UTF-16 and
  removed; the release scrub for GitHub publication ran: 630 files shipped,
  zero identity tokens, leak scan clean.

## 2.86.0 - 2.92.0 — flyouts, rings, and the Graphs radio band (2026-08-05)

- **Sub-flyout placement is now factor-derived**, not pinned to 2x offsets.
- **The disaster ring/bar junction seats with the dock** — one welded shape,
  seated as one.
- **The advice-row dismiss X survives at every tier** — the row's column
  budget is widened with the tier instead of eating the X's reserve.
- **The Graphs radio band is born correct** — its bottom dock, anchor
  lifetime and show-path gating were rebuilt so the band arrives at its
  final geometry instead of jumping into it.

## 2.85.0 — region zoom range ±5; release hygiene; CC0 (2026-08-05)

- **Region zoom range widened from ±2 to ±5** (user-confirmed). Zoom-out was
  capped by one comparison that guarded a path which had always handled it;
  zoom-in was bounded by our own memory bookkeeping, not the machine (the
  game is large-address-aware; the budget was raised and the per-item
  accounting corrected). Levels past the memory budget are refused whole and
  logged, so the end of the range feels like a range, not a fault. Usable
  range: tier 1.5x −5..+5, tier 2x −5..+4, tier 3x −5..+2.
- **Release bundle became plug-and-play**: `dist\SC4UIScale-v<version>\` is
  a `Plugins\` tree you copy straight in, with a README, an installer script
  (`Install.ps1`, with `-WhatIf` and `-Uninstall`), the license, third-party
  notices and SHA256 sums. Its file list is parsed from the deploy script,
  so the bundle and a working install cannot drift apart.
- **Ship blocker fixed:** the shipped ini omitted the two keys that enable
  scaling at all — a fresh install loaded and quietly scaled nothing. The
  gate now checks both directions: every key resolves to a read, and every
  load-bearing setting that defaults off is present.
- **Relicensed CC0 1.0 (public domain)** at the author's request. The two
  statically compiled third-party libraries (gzcom-dll, LGPL-2.1-or-later;
  MinHook, BSD-2-Clause) keep their own terms, and the notices say so
  plainly.
- **WebText shipped** — the mod's web-button label package is now a normal
  manifest entry instead of a hand-placed file.

## 2.84.0 — region tile sharpness when zoomed (2026-08-05)

- **Fixed: the region map went soft when zoomed** (user-confirmed with a
  before/after pair). The cause was not source resolution: the game's own
  alignment filter runs at scale 1.0 purely to land tiles on the pixel grid,
  and zoom puts fractional positions into it, roughly doubling the blur of
  the magnification itself. The filter now gets an exact-identity phase and
  the alignment is re-applied as whole destination pixels. All four buffers
  of every item get identical treatment, so colour and silhouette can never
  drift apart.

## 2.81.0 - 2.83.1 — the region map at 2x/3x, rebuilt on the game's own builder (2026-08-05)

- **Fixed: the region map was too small at 2x/3x** (user-confirmed). The
  isometric basis floats that size a region cell were patched (one region
  cell is exactly 128 screen pixels at every resolution — that *is* the
  defect), and each freshly built tile bitmap is enlarged inside the game's
  own rebuild, so the composite and the click mask are generated at the new
  size together.
- **Region zoom rebuilt as a trigger of the game's own item builder** after
  in-place resizing proved structurally impossible (two crashes; an item
  owns four bitmaps, a composite and three derived run lists that only the
  rebuild keeps consistent). Zoom is absolute-from-pristine: no compounding,
  and zoom-out is exact rather than lossy.
- The adversarial review of that rebuild landed four contract hardenings
  (coupled-hook arming, all-or-nothing validation before any write, a real
  memory budget, ref-counted stashes).

## 2.76.0 - 2.77.0 — panel docking as a table (2026-08-04)

- **All UI elements dock via one table** (user direction). Panel-to-panel
  docking joined the mayor-flyout dock mechanism, and docking became
  *born-correct*: a docked panel is placed by the instant the game makes it
  visible, before its first paint — no more first-open jump, the defect the
  project had fixed "dozens of times before" in smaller forms.
- The mayor-rating change arrows were fixed at 2x as well as 3x; the detour
  is self-gating on the defect (it writes only when live and cached seats
  differ), so a correct 2x seat can never regress.

## 2.74.0 — the 3x sweep (2026-08-04)

- **All four user-reported 3x defects fixed in one release**: the dock
  minimap's decorative fake plate neutralized so the real map sits on clean
  metal, the Ordinances name label cleared of the eye icon (an encoding
  ceiling had clamped it), the Graphs legend's vertical start, and the
  detached rating-decline arrow. Each patch was verified against the live
  bytes before it was applied, and every one is a provable no-op below 3x.

## 2.72.0 - 2.73.0 — fractional-tier crash fixed; minimap family (2026-08-04)

- **Fixed: the Data Views crash at fractional tiers** — five of the game's
  own exception reports traced to one instruction. The minimap surface is
  created at a size snapped to a power of two, and window and surface agree
  only when the factor itself is a power of two. The crash is cured for the
  whole family (all three minimaps, not just the one that crashed), and the
  stale ring around snapped maps is a repaint, not a border.
- **Fixed: the dock minimap "garbage"** — it was our own artwork, staged
  wrong; the dock now shows clean terrain at every tier.

## 2.71.2 - 2.71.8 — minimap bake, package gating, disaster ring (2026-08-04)

- **The minimap terrain bake extended to x8** using the game's own bake, so
  large-tier minimaps are sharp instead of stretched.
- **Two package-gating defects in shipping code fixed** (a package could be
  counted on by a scan while its tier gate said otherwise).
- **The disaster ring seat scales with the tier** (3x) and re-docks at 1.5x.
- Dead Data Views fallbacks deleted; the log's Info level finally gates its
  volume (tree-dump rows moved to Debug, event lines kept).

## 2.69.0 - 2.69.5 — release hardening; Data Views zoom cliff (2026-08-04)

- **No visible change, by design**: the per-tick cost of the scaler was cut
  (steady state now costs ~0 re-enumerations), silent truncation at internal
  caps now announces itself, the dead-EA-link web redirect became opt-out-able,
  and three settings that did nothing were named and removed from the
  shipped ini.
- **Fixed: the Data Views zoom cliff** — zooming in the Data Views at
  fractional tiers hit a surface-recreation edge and dropped the panel.
- Three regressions the adversarial review found in this series were fixed
  the same day.

## 2.62.0 - 2.64.0 — shutdown hang mitigated; budget popup close-X (2026-08-03)

- **The shutdown hang mitigated.** After the window closes, the process
  could spin at one core forever. The root cause is the game's own
  window-manager teardown order (a freed valid-window set leaves every
  removal a no-op and one retry loop spinning); when the spin is measured,
  the mod now points the stuck list's sentinel at itself so the loop's own
  empty test passes — two guarded writes, no game code called. Opt-in
  telemetry accumulates the rate. The cause remains the game's; details in
  `research/KNOWN-LIMITATIONS.md`.
- **Fixed: the dead close-X on empty budget department popups.** The popup
  was pinned with its twin's height and parked above its host rect, where
  the click router could never reach it. Each twin now uses its own stock
  height and host, popup, content and art move together.
- Hardening of the in-city confirm dialogs against a latent fourth base
  size (nothing visible on any observed path).

## 2.55.0 - 2.56.0 — Graphs legend (2026-08-02 → 2026-08-03)

- **Fixed: the Graphs legend** (user-confirmed). The chart does not lay out
  its legend; the panel builder does, once, from a six-constant right-margin
  budget that never scaled. The column is now born at the tier factor.

## 2.49.0 - 2.53.0 — the Graphs chart against a stock reference (2026-08-02 → 2026-08-03)

- The Graphs chart family was rebuilt against a true-stock reference capture
  rather than against the scaled screen: chart grid, axis labels and plot
  area now match "stock, scaled" instead of approximating it.

## 2.42.0 - 2.48.1 — My Sims portraits, U-Drive-It consoles, building styles (2026-08-01 → 2026-08-02)

- **Fixed: My Sims portraits at 1x in a scaled panel** (user-confirmed) —
  runtime-supplied portraits now scale with their panel via the image
  hook, with a per-open census as the standing acceptance instrument.
- **U-Drive-It consoles:** the fifth console variant insured, the gauge
  silent-skip on second cities hardened, and the marker's unit system
  measured (world-anchored, not pixel-fixed) so its dock derives from the
  live marker.
- **Building Style Control gets its born-correct cure** — the dialog a
  third-party mod replaces, scaled from the mod's own script.

## 2.36.0 - 2.41.x — the flash fixed; minimaps; born-scaled flyouts (2026-07-30 → 2026-08-01)

- **The 1x flash at mode transitions fixed at the source.** Swept panels are
  born 1x and the sweep is reactive, so every mode switch painted 1-2 frames
  of unscaled UI. The cure is always "born scaled", never "hide the paint":
  sub-flyouts are scaled at their own construction, first-level tool flyouts
  at the open call, and persistent panels pre-scaled while hidden. Paint
  suppression was tried and permanently rejected — it blanked HUD windows.
- **The first sub-flyout of a city no longer shows a 1x bar and detached
  ring** (user-confirmed): the chrome state is installed at birth, not on
  the next tick.
- **City-open minimap corruption fixed** — 2x art in 1x windows on the first
  open; the minimap's one-shot display surface is now recreated rather than
  resized, with a bounded retry.
- **The news/advice row layout** and its dismiss X survived the glyph
  upgrade; the quit/exit confirm flash (another plugin owned the script)
  closed.

## 2.24.0 - 2.35.x — the three-tier system; the budget architecture (2026-07-29 → 2026-07-30)

- **1.5x and 3x join 2x.** Every 2x-hardwired constant in the flyout
  draw/click machinery became its derived form under one invariant: at f=2
  each general form reduces exactly to the constant it replaced. Item icons
  and sub-icons gained 1.5x and 3x packages; the whole pipeline now rounds
  one way (`floor(v*f + 0.5)`).
- **The Monthly Budget** — a multi-root composed panel — and its five
  detail dialogs (Ordinances, Neighbor Deals, Transportation, Taxes,
  Business Deals) were decoded and scaled at the source: children born
  scaled in data, buttons and department columns patched at their exe
  constants, all tier-general.
- **Ordinance description popups** grow to fit their text; the news reader,
  advisor strips and briefing panels, My Sims faces, U-Drive-It gauges and
  picker thumbs all gained their 2x treatments in this wave.

## 2.7.0 and the v2.4-v2.6 series — AutoScale and the region screen (2026-07-22)

- **AutoScale: the scale factor becomes a fit function.** On every boot the
  DLL reads the effective resolution and picks the largest installed tier
  whose widest UI piece (880 design px) and tallest dialog (558 design px)
  fit, capped at 800x600 density — any resolution, including ones never
  directly tested, gets a provably fitting factor (a 2000-resolution sweep
  found zero violations). The DLL manages the static layers to match,
  renaming tier packages aside at stock and re-activating them at scaled
  tiers — idempotent, self-healing, logged.
- **Stock tiers are truly inert**: no subclass, no timer, no hooks —
  indistinguishable from a no-DLL install (isolation-proven), except the
  dead-EA-link fix.
- **Plugins-only footprint** (user requirement): everything lives in
  `Documents\SimCity 4\Plugins`; no Program Files writes; portable across
  any Steam path.
- **The region screen completed** (user-accepted): all nine region panels
  scale; fonts solved (the tier font table loads from `Plugins\` and sizes
  all 88 styles game-wide); eleven region dialogs ship statically doubled;
  geometry at stock verified with zero deviations against true 800x600.
- **DLL split:** `SC4TouchControls.dll` froze at v1.0.5 as a touch-only
  product; the new `SC4UIScale.dll` owns all UI scaling, and both load side
  by side.

## 2.0.0 - 2.3.x — the runtime scaler finds its north star (2026-07-21)

- The first approach — whole-frame upscaling of a small internal render —
  worked but scaled the world too, and was abandoned as the wrong turn.
  The north star replaced it: **the game runs at native resolution and only
  the UI elements are drawn larger.**
- The cIGZWin-tree scaler, the selective 2x art package, and the 2x font
  table (all 88 styles, loaded from `Plugins\`) were proven together.

## 1.0.0 - 1.0.4 — touch controls (2026-07-19, now a separate product)

- Touch support for SimCity 4 shipped as **SC4TouchControls** (two-finger
  pan, pinch, twist, one-finger look — all four gestures user-confirmed).
  It was frozen at v1.0.4/v1.0.5 when the UI-scaling work split into this
  project; it is maintained separately and is not part of SC4UIScale.

---

### Compatibility notes (apply to every release above)

- **SimCity 4 Deluxe, executable 1.1.641** — the byte patches verify the
  version and refuse anything else.
- **dgVoodoo2** (or another wrapper lifting the DirectX 7 2048x2048 texture
  cap) is required for 3x and recommended everywhere; above 2048 px wide
  the unpatched game crashes regardless of this mod.
- **Compatibility layers exist for**: Network Addon Mod (392 menu icons),
  Colossus Addon Mod (UI scripts, art, and a missing graph caption),
  Allow More Building Styles, Save Warning, God Terraforming in Mayor Mode,
  and the Submenus DLL's icons. The five gated packages deactivate
  themselves when the owning mod is absent; where a mod is patched, its own
  artwork is enlarged, never a Maxis substitute. See
  `docs/COMPATIBILITY.md`.
- **Another UI-scaling mod conflicts** — only one thing can own the layout.
- **"Everything looks zoomed" from the very first frame** is Windows DPI
  virtualisation, not this mod: check for a compatibility shim on the
  executable before blaming a plugin.
- Tier minimums: 1.5x needs 1440x1080, 2x needs 1920x1440, 3x needs
  2880x2160; AutoScale never picks a tier your screen cannot carry, and the
  selector refuses one it cannot.
