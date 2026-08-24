# Changelog

## 4.1.0 (2026-08-24)

- **Fixed: the deployment-count digit on emergency/dispatch pins** (fire-station
  pins and the player-dropped pin) overlapped the helmet art at scaled tiers.
  Root cause measured live at 1x and 2x: the digit's box height and seat offset
  are stock inline constants (14px/9px) that never rode the tier while the pin
  balloon and pole did. `ApplyPinDigitScale` scales both, coupled to the
  existing signpost balloon patch so a half-patched pin is impossible.
  User-confirmed at 2x.
- **Fixed: stacked indicator balloons overlapped each other** at scaled tiers —
  the collision probe offset (43px, screen-space) now rides the tier
  (`ApplyStackShift`). Solo pins byte-provably unaffected.
- New research instrumentation (all log-only, ini-gated, default off):
  `[Probe] DispatchQuad` (submitted-quad census with per-caller caps),
  `[Probe] ViewListRepeat` (repeating renderer view-object enumeration),
  `[UiSpike] CsiCountPlate` (dispatch-view count-plate A/B lever).
  Probe keys now arm their own probes at every tier and always log their
  resolved values.

## 4.0.41

- **Deleted the disaster flyout's legacy scaling path** (~28KB of code),
  scheduled since the v4.0.40 rebuild and executed after user acceptance
  at 2x, 1.5x, and 3x: the hand-tuned ring seat (RingDX/RingDY) and its
  seat-scaling extrapolation, the RingUnderStrip viewport clip, the
  neck-penetration clip, the LayerFix bar-tile cache/replay machinery,
  the DrawRebuild kill switch itself, and a years-dead unreachable
  disaster branch in the sub-flyout birth hook. The ini keys RingDX,
  RingDY, RingUnderStrip, LayerFix, and DrawRebuild no longer exist
  (BarDX/BarW remain — the mayor sub-flyout family still uses them). The
  v4.0.40 uniform stock-transform is now the only disaster paint
  pipeline.

## 4.0.40

- **Create Disasters flyout rebuilt from scratch on one invariant: at
  scale factor f, the flyout's rendering equals the stock 1x rendering
  magnified by f.** The old pipeline (the first flyout this project ever
  scaled) corrected each painted element separately — a hand-tuned ring
  seat, a bar shift+widen, a layer-order replay, two clip fixes — so the
  junction between elements could never be right by construction; six
  same-day patches to the ring/bar "tail" junction all failed for that
  reason. The rebuild classifies each element draw (ring, bar caps,
  spine) and redraws it at its disassembly-derived stock geometry times
  f, in stock order. The ring/bar weld, the strip overlap, and 1.5x/3x
  correctness all follow from the math, with zero per-tier tuning. The
  ring's dock position is now fully derived from documented stock data
  (retiring the hand-tuned RingDX/RingDY seat entirely — the dock is the
  only position lever). Proven against the real emulated game code
  offline before shipping (`_tests/Test-DisasterDrawRebuild.py`), then
  user-confirmed on screen. `[Disaster] DrawRebuild=0` restores the old
  path for one release as a safety lever.

## 4.0.39

- **Fixed: the Create Disasters flyout opened with the ring beside the
  wrong pair of disasters.** The scroll-reset guard compared the strip's
  spacing field against its already-scaled value, but ran before the
  scaling had happened — so it failed on every open and the reset never
  ran. It now compares against the captured stock value.

## 4.0.38

- **Root-caused and fixed the short-strip sub-flyout misalignment**
  (Police/Fire/Education/Hospitals and any other category with fewer
  than 8 items at 2x/1.5x/3x). The two prior attempts this cycle
  (v4.0.35's flat empirical shift, v4.0.36's per-bar mB-clamp
  generalization) both left these menus broken because neither addressed
  the real bug: `SubPlaceTop()`'s bottom screen margin was derived from
  the desktop resolution, not the game's own live view-height parameter
  (`mB`) — a 434px gap on a 1600-tall desktop that is the game's bottom
  HUD, not scaling error. The corrected formula (`SubPlaceTopMb()`, using
  the measured `mT`/`mB` directly) makes every short menu center on its
  own toolbar button and makes every tall (8-row-capped) menu on a bar
  converge on the identical shared bottom automatically — no per-bar
  special case, no empirical shift constant. Verified against the real
  disassembled game function under emulation before shipping. One known
  side effect, not yet visually reconfirmed: the already-approved Build
  Park/Green Spaces/Sports Grounds/Plazas family's shared bottom moves
  by 16px (1150 → 1166), the derived-not-tuned value.
- **Confirmed (adversarial review), not caused by the above: the
  sub-flyout back-arrow scroll control and click-forwarding have been
  silently non-functional** on any menu with more items than fit
  visually (Landmarks, Rewards, Parks, any category over 8 items),
  independent of this release. A second, still-unfixed placement
  formula inside the periodic sweep never agreed with the birth hook's
  position closely enough to activate the code that arms the back-arrow
  hit zone. Not something this release introduces or fixes - flagged
  now because verifying the placement fix is what surfaced it. Tracked
  in `research/laws/project-sc4-flyout-bottom-anchor.md`.

## 4.0.37

- **Fixed a real, severe crash: an empty `FontStyle.ini` could crash the game
  loading the city-select screen (#182).** Every release from v4.0.1 through
  v4.0.9 shipped an empty `FontStyle.ini` placeholder (added so sc4pac could
  track and uninstall the font file the DLL generates at runtime). The
  existing font-preservation logic could not byte-match that empty file to
  any of our shipped tier fonts, so it wrongly snapshotted it as the
  player's own pre-existing font (`.user-original`); any later trip to the
  stock tier restored that empty snapshot over the live `FontStyle.ini`, and
  the game crashed (`ACCESS_VIOLATION` in `sub_7B4150`) the next time any
  city loaded. `ScaleTier::SyncFont` now recognizes an empty file as ours by
  construction, never snapshots or restores one, and self-heals any install
  that already has a corrupted empty snapshot on its next stock-tier boot —
  no manual file surgery required.
- **Root-caused the same bug at the packaging level.** The sc4pac
  placeholder shipped under the game's own live filename, so a player who
  removed this mod by hand (rather than through sc4pac) could leave an
  empty, unbranded `FontStyle.ini` behind with no DLL left to repair it —
  a landmine that crashes a completely vanilla game. The placeholder is
  renamed to `z_SC4UIScale_FontStyle.ini`: sc4pac still gets a real file it
  installed and can delete, a manual "remove everything named
  z_SC4UIScale\_" cleanup now catches it like every other package, and the
  game never reads that filename at all.

## 4.0.35

- **Sub-flyout container shift (v4.0.31-v4.0.35): computed instead of
  hand-tuned.** The second-level flyouts (the strip that spawns off a
  first-level flyout button) now shift their container at birth by an
  empirical scale-factor formula (`f²×73−60` px at birth, all counts),
  replacing the retired ini-tunable `ContainerShiftRows`/`Fine`. A
  per-count geometry formula (`SubContainerShiftFromGeo`) exists at sweep
  time for when the sweep dock path is live. Calibrated against Build
  Park at 2x (`kSubArmTargetBottom = 1.50` rows from strip bottom).
- **Known open defect:** Sports Grounds (5-item strip) and the mayor
  column's Plazas still attach the ring arm too high with the strip's
  bottom clipped at 2x. Instrumentation (SUBBORN / SUBBORN2 / SUBGEO2 /
  SUBSHIFT / SUBCAND / BORNSHIFT log lines) is in place for the next
  pass; see `HANDOFF-2026-08-23.md` for the full diagnosis - the key
  finding is that placement is decided entirely by the birth hook (the
  sweep dock gate never fires), and the birth hook's ring auto offset is
  a different quantity than the sweep formula was fed.

## 4.0.21

- **Fixed: the Create Disasters flyout opened scrolled to the bottom of its
  list**, putting the wrong disasters beside the docking ring. Measured with
  the strip diagnostics: nine disasters, six visible, first-visible field
  sitting at 3 (= fully scrolled down). The open path now writes the
  scroll/first-visible field to 0 once per birth, guarded to fire only when
  the strip's fields match the measured shape, so a recycled object can
  never be written blind. Live-tunable via `[Disaster] InitScroll`.
- **Fixed: the dock connector (the ring's tail) drew on top of the orange
  strip.** The mechanism that replays cached bar tiles over the ring after
  the ring redraw (`Circle → Strip`) shipped default-OFF years ago and no
  ini ever set it - so out of the box the ring, painted last including its
  tail, stamped straight over the pill. `LayerFix` now defaults ON. This is
  the same z-order every other god-tool flyout shows: connector back,
  orange strip middle, pictures front.
- **The widened orange strip's edges now alpha-blend onto what is behind
  them** instead of stamping opaque (and skipping faint columns outright),
  which cut a hard seam plus a navy sliver exactly where the connector
  slides under the pill. Every nonzero-alpha source pixel weight-blends;
  fully opaque art renders bit-identical to before. This mirrors why the
  Mayor-mode tool flyouts always met their connectors smoothly: their art
  goes through the engine's own alpha-compositing blit.
- **Retired the v4.0.10–4.0.13 experimental "derived" container docks**
  (glue-delta scaling and button-center anchoring). The container was never
  the misaligned piece - the ring paints inside it and docks via the
  accepted toolbar-live scheme, which is restored as the only dock target.
  The real fixes turned out to be scroll state and paint order, not
  position.

## 4.0.9

- **Fixed: third-party menu icons installed in the game's own Plugins folder
  stayed at 1x.** SimCity 4 loads plugins from TWO places -
  `Documents\SimCity 4\Plugins` and `<install>\Plugins` beside the game exe
  (on a GOG install: `C:\Program Files (x86)\GOG Galaxy\Games\SimCity 4
  Deluxe Edition\Plugins`). The uncovered-icon scanner only walked the
  Documents folder, so any third-party dat parked in the install root was
  loaded by the game yet invisible to the scan: its menu icons were never
  enlarged and drew at 1x inside scaled flyouts. Which assets broke depended
  purely on where each mod happened to be installed - the same dat scales
  fine from one folder and breaks from the other. The scan now walks both
  roots, and the Web Button Improvement Mod detection checks both as well.
- **Fixed: the flyout bar-tile cache saturated on heavy installs.** A fixed
  64-slot cache dropped replay tiles mid-paint (`BARCACHE saturated ...
  LayerFix replay is INCOMPLETE` in the log), leaving part of a flyout paint
  un-replayed. The cache now grows on demand up to a generous ceiling and
  logs once when it first exceeds the old fixed cap.

## 4.0.8

- **Both INI files the mod reads are now parsed with the ecosystem's
  `sc4-dll-utilities` `IniReader`.** v4.0.7 converted our own
  `SC4UIScale.ini`; this release moves the reads of the shared
  `SC4GraphicsOptions.ini` (boot tier decision, ScaleRemap fallback and the
  Graphic Options readouts) onto the same parser. The stated v4.0.7 reason
  for keeping `GetPrivateProfile*` there was wrong: SC4GraphicsOptions.dll
  parses that file with its own library, not `GetPrivateProfile*`, so there
  was nothing to stay bug-compatible with. Missing or malformed files fall
  back to defaults exactly as before. The remaining `GetPrivateProfile*`
  calls read only our own ini's live-tune keys.
- **sc4-dll-utilities is now a git submodule** (`vendor\sc4-dll-utilities`,
  pinned to upstream commit cb52a04, verified byte-identical to the vendored
  subset it replaces) instead of four copied files - same treatment as
  gzcom-dll and MinHook. Fetch submodules after cloning, as documented.

## 4.0.7

- **`SC4UIScale.ini` is now parsed with the ecosystem's `sc4-dll-utilities`
  `IniReader`** (vendored, LGPL-2.1) instead of the `GetPrivateProfile*` APIs,
  matching the wider SC4 DLL ecosystem. Parsing is verified identical; the
  shared `SC4GraphicsOptions.ini` still uses `GetPrivateProfile*` because it is
  the canonical parser that file's other consumers use. (Project now C++20.)
- **The website-button redirect now steps aside when the Web Button Improvement
  Mod is installed.** That mod already owns the region website button, so our
  `ShellExecute` redirect is skipped to avoid double-handling the URL; without
  the mod, our standard redirect runs as before.

## 4.0.6

Removes the hard dependency on the optional `SC4GraphicsOptions.dll` plugin.

- **The mod now scales even if `SC4GraphicsOptions.dll` / `.ini` are not
  installed.** The boot tier decision previously read the render resolution
  from `SC4GraphicsOptions.ini` (owned by that third-party plugin) and fell
  back to doing nothing when it was absent. It now falls back to the monitor
  size as the render-resolution basis, so AutoScale still picks a sensible
  tier; the existing `RESMISMATCH` check verifies against the real window and
  corrects on later launches.
- **Without the plugin, the Graphic Options Resolution / Window-Mode controls
  show as read-only readouts** (the current value, single-entry dropdowns,
  with their labels) instead of empty boxes. They cannot change anything in
  that state — nothing reads the ini — so they offer no other choices; the
  Scale control is unaffected and still works.

## 4.0.5

Bug-fix release.

- **Fixed: on a game build the mod doesn't support, it could leave the
  interface half-scaled.** The version check used to log a warning and then
  run its setup anyway - arming a scaled art tier with no geometry scaling
  behind it. It now refuses the whole setup on an unsupported build: the art
  is stashed back to stock and the mod stays fully inert, so the game runs
  exactly as if the mod weren't installed. A build newer than the tested one
  still runs, but is logged as untested.

## 4.0.4

Bug-fix release.

- **Fixed: uninstalling via a package manager (e.g. sc4pac) could leave a
  scaled font active on an otherwise fully-reverted, stock interface.**
  Package managers intentionally don't remove `.ini` files on uninstall (to
  protect user-configured settings), so the font table this mod writes
  needs to already be reverted by the time an uninstall happens. It now
  reverts automatically on every clean shutdown, at no cost during normal
  play.
- **Improved: one more package (the largest art package) now uses a
  filename that never changes**, so a package manager can reliably track
  and remove it regardless of which scale tier is active. The remaining
  two root-level packages will follow in a future release.

## 4.0.2

Bug-fix release.

- **Fixed: sub-menu picture strips (e.g. the Building Styles picker) could
  have only the right half of each thumbnail clickable.** The menu
  container's hit-test region was not being widened to match the enlarged
  artwork in every case, leaving the left portion of each picture
  unresponsive to clicks.

## 4.0.1

Bug-fix release.

- **Fixed: heavily-modded installs could leave thousands of menu icons
  unscaled.** The icon-coverage scan capped how many third-party icons it
  could track, and the fix queue capped how many it could correct, at fixed
  limits sized for a typical install. A very large plugin folder could
  exceed both, leaving mod-supplied icons rendered at 1x - visible as
  doubled art that vanishes on hover. Both limits are now unbounded: every
  icon found is tracked and every one queued is corrected, regardless of
  install size.
- **Fixed: uninstalling via a package manager (e.g. sc4pac) could leave a
  stray `FontStyle.ini` behind.** That file is generated by the DLL at
  first launch, so a package manager had no record of it to remove. The
  release bundle now ships an empty placeholder at that path, so package
  managers can track and clean it up like any other installed file.

## 4.0.0

First public release.

SC4UIScale renders SimCity 4's interface at **1.5x, 2x or 3x** while the
world continues to render at your display's native resolution. The game has
no UI scaling of its own; its interface is built around 1024x768
assumptions, which leaves it unusable on modern high-resolution displays.

- **Automatic tier selection.** At launch the mod measures the resolution
  the game actually renders at and arms the largest tier that fits
  (1.5x from 1440x1080, 2x from 1920x1440, 3x from 2880x2160).
- **In-game settings panel.** Scale, resolution and window mode are
  selectable inside the game's own Graphic Options dialog. Choices apply on
  restart; a scale the chosen resolution cannot carry is refused rather than
  silently ignored.
- **Coherent by construction.** A hand-edited or inconsistent configuration
  is repaired to a runnable state at launch, so no combination of settings
  leaves the interface too large to navigate back from.
- **Stock is a first-class state.** Selecting 1x disarms every scaling
  subsystem and unloads every art package: identical to a clean install.
- **Scales the whole interface**, including third-party mod dialogs, menu
  icons, fonts, cursors and flyout menus. See `docs/WHAT-IT-SCALES.md`.
- **Nothing on disk is modified.** All scaling is in-memory per session;
  the mod owns only its own files.

Requires SimCity 4 Deluxe build 1.1.641. See `README.md` to install and
`research/KNOWN-LIMITATIONS.md` for what the mod does not do.
