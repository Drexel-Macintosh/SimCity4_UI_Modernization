# Changelog

## 4.6.0 (2026-08-30) - the engine documentation becomes a section

**Nothing about the mod changes.** No new DLL, no repackaged art, no setting
to adjust - this release is documentation and the gates that check it. If you
only play the game, 4.5.9 and 4.6.0 are the same mod.

Scaling this interface meant reverse-engineering it first, and that work was
already in the repository - it was just undiscoverable and, in places,
contradicted itself. It is now a section you can read:

- **A front door.** `docs/DECOMPILATION-STATUS.md` says what is documented,
  what is only partly understood, what is still unknown, and lists every hook
  and byte patch the DLL installs. The repository README points at it, and
  each research folder now has an index that GitHub renders in place.
- **The corpus agrees with itself.** Every contradiction the project's own
  register had flagged as a publication blocker is closed: a census row that
  held three different states for one visual, an attribution corrected in two
  places but left stale in three others, a defect recorded as simultaneously
  open and closed, and a patch count that was wrong by roughly ten times
  because "families", "tables" and "sites" had been used interchangeably.
- **Honest labelling.** The repository claimed to contain no EA content of any
  kind. It does contain some, in text form, as the evidence behind the
  documentation - decoded scripts and data records, a few disassembly
  listings. `THIRD-PARTY-NOTICES.md` §4a now says exactly what and why, and
  the takedown offer covers it.
- **Two gates that had gone quietly red are green again**, one of them for the
  first time in months. Details in `VERSION-HISTORY.txt`.

## 4.5.9 (2026-08-30) - two mods that only matter if you use the Carbon Skin

Both changes in this release are invisible unless you have Scoty's Carbon Skin
installed. If you do not, nothing about your game changes from 4.5.7.

- **Carbon Skin + Raise the UI now work together.** Using both, the interface
  was drawn with the wrong layout, because neither this mod's Carbon support
  nor its Raise support describes the combination. Scoty already publishes a
  combined file for exactly this pairing, and this mod now enlarges *that* -
  so the combination gets the layout its author intended. Enabled
  automatically when both are installed; nothing to configure.
- **This mod no longer puts the yellow pause border back.** With the Carbon
  Skin installed, this mod's enlarged copy of Scoty's gold pause border was
  overriding any pause-remover you had chosen - including Scoty's own, which
  ships inside the skin. The border is still enlarged for people who want it;
  it now steps aside when you have installed something to remove it. Both
  known removers are recognised.

## 4.5.7 (2026-08-30) - the cheat box, two new mods, and a log that was lying

- **The Ctrl+X cheat box no longer clips what you type.** The box sizes itself
  from four numbers written into the game's own code, while its text follows
  this mod's enlarged font - so at 2x a 26pt line was being drawn into a 20px
  box. The box now scales with the font.
- **Support for two newly-released mods that this mod was breaking:**
  - *Raise the UI Mod* (warrior). It ships interface layouts but no artwork, so
    the game drew them using this mod's enlarged artwork with the original
    small coordinates - producing magenta and black blocks on the region screen
    and a jumbled bottom-left corner in mayor mode. Both are fixed, and the
    mod's raise is preserved exactly.
  - *Region View Census UI* (null-45). Its window never scaled while its text
    did, so five of its forty labels overflowed their boxes at 2x and its frame
    broke apart at 3x. Now scaled properly.
  - *SMP Yellow Pause Thingy Remover* needs nothing from this mod and works as
    intended - checked rather than assumed.
- **Fixed: the Web Button Improvement Mod support shipped an unscaled layout.**
  Installing that mod on its own would have broken the region screen the same
  way, because our own package was overriding a correctly-scaled file with an
  original-size one. It had been doing this since the package was added.
- **Fixed: a log line reported nonsense.** The cheat-box patch logged
  "x0.00 ... 13pt -> 1077542912pt" while doing the right thing. Harmless in
  itself, but a diagnostic that misreports is worse than none, so it is
  corrected.

## 4.5.3 (2026-08-30) - the button that brings the toolbars back is on screen again

- **The Restore-Toolbars button was born partly below the bottom of the
  screen, and then visibly jumped larger.** Hide the toolbars and the small
  button that brings them back appears in the bottom-left corner - at 2x its
  lower edge was cut off by the screen edge, and a moment later it grew to
  double size and was cut off worse. Both are fixed; it now sits clear of the
  edge and does not move after it appears.
- **Why it happened.** The game builds that button without giving it a size -
  its size comes entirely from its four-frame button artwork, which this mod
  enlarges. But the game then places it using two fixed numbers that were
  written for the original artwork, so the button grew while its position did
  not. The amount it hung off the edge did not depend on your resolution: 1 px
  at 1.5x, 10 px at 2x, 29 px at 3x.
- **The jump was this mod's own doing.** Once the button became visible, the
  routine that enlarges interface panels enlarged it a second time - putting
  2x artwork inside a 4x frame. The mod now leaves that button alone, because
  the button is already correct when it is created.
- **New setting `RestoreToolbarsPatch`** under `[UiSpike]` (on by default)
  turns both halves off together if you ever want the old behaviour. The fix
  only applies while this mod's enlarged artwork is actually in use - with the
  packages switched off the game's original placement is already right, and
  changing it would move a correctly-placed button.

## 4.5.2 (2026-08-30) - the 1x scale picker could never arm; settings edits on fresh installs did nothing

- **The in-game scale picker's 1x package could never activate.** The package
  that keeps the Graphic Options scale picker working at 1x - so 1x is not a
  one-way door you can only leave by editing a file - was requested at every
  boot but the request was recorded one step after the pass that applies
  requests had already run. On a machine running at 1x, the picker never came
  back. (At 1.5x/2x/3x nothing was visibly wrong, which is why the v4.5.1
  release test could not catch it.)
- **Editing the auto-created settings file mostly did nothing.** The
  `SC4UIScale.ini` the mod writes on first launch put five of its eight
  settings (`AutoScale`, `ScaleFactor`, `SelectorAtStock`, `WebRedirect`,
  `SpinFix`) under a `[Scaling]` heading; the mod reads all five from
  `[UiSpike]`. The written values matched the built-in defaults, so nothing
  looked wrong - until you changed one and nothing happened. Fixed, and the
  ini-key test now validates the file the mod actually writes, not just the
  reference copy in the repo.
- **A failed first-run settings write is no longer silent.** If the ini cannot
  be created (read-only Plugins folder, for instance), the log now says so and
  why, instead of the mod being inert with an empty log.
- **The zip installer got its first test suite, and it found three bugs:**
  uninstall deleted `z_SC4UIScale_*` files from *anywhere* under Plugins
  (including a sc4pac-managed copy of this mod, which it now leaves alone with
  a notice); upgrading from v4.4.x moved your settings file into
  `010-SC4UIScale\` where the mod no longer reads it (it now migrates it back
  to the Plugins root, keeping your edits); and `SHA256SUMS.txt` described a
  file layout the bundle no longer shipped (it is now written last, and the
  release zip is now built - and hashed - by the packaging script itself).
- **Channel/packaging corrections** ahead of resubmitting the sc4pac PR: the
  published minimum resolution now matches the code's real 1440x1080 floor
  (was stated as 1320x900), the upstream package file is a clean generated
  document instead of the internal engineering record, third-party artwork
  attribution now installs with the overrides package, and the arming state
  files no longer duplicate every entry across both folders.

## 4.5.1 (2026-08-30) - v4.5.0 did not work when installed by sc4pac

- **If you installed v4.5.0 through sc4pac, half the mod was stuck at 2x.**
  The dialogs, item icons and the main art package rendered at 2x no matter
  which tier you picked, while the third-party overrides followed your choice -
  so the UI came out at two different scales at once. A hand-installed v4.5.0
  was not affected.
- **The cause.** v4.5.0 stopped hard-coding its folder names and started
  finding its two folders by looking at what is inside them - so that a package
  manager could name those folders whatever it likes. That search only looked
  two levels below `Plugins`. sc4pac puts one of our two packages three levels
  down, because it strips a shared folder prefix from one package and not the
  other. The search found the override folder and missed the other one, then
  fell back to a folder name that does not exist on an sc4pac install.
- **Fixed**, and the fix is covered by a test that proves it catches the bug:
  `Test-FolderDiscovery.ps1` builds the layout sc4pac actually produces, plus
  four others including an empty tree, and rebuilds itself with the old
  behaviour to confirm the old behaviour fails.
- **Also fixed, all from the same wrong assumption:**
  - The live-tuning settings block read the ini from the wrong folder, so every
    key in it silently fell back to its default.
  - Two of the six filename patterns used to identify our folders matched files
    we no longer ship.
  - With the Carbon Skin installed, the log claimed "NO carbon packages are
    present" on an sc4pac install that had all 44 of them.
  - `Set-Tier` looked for `SC4UIScale.ini` in the mod folder and refused to run
    with "the tier cannot be set without it". The ini has been at the `Plugins`
    root since v4.5.0.
  - The developer deploy script moved the ini back into the mod folder on every
    deploy, and deleted the root copy when both existed.
- The mod now says so in the log when more than one folder looks like ours -
  the shape you get if you leave a hand install in place and then add the
  sc4pac one on top.

## 4.4.0 (2026-08-29) - the Plugins root is now just the DLL

- **This mod used to leave five loose files at your `Plugins` root** - the
  DLL, the ini, the log, plus a `.gcap` census and a `#104` csv when those
  probes were on. Every other DLL mod in a typical tree leaves two or three,
  so we were the untidiest thing in the folder.
- **From v4.4.0 the root gets `SC4UIScale.dll` and nothing else.** The
  settings, log and everything else moved into `010-SC4UIScale\`, so the
  folder now carries everything a user - or a package manager - would want to
  remove. The DLL has to stay: SimCity 4's dat scan is recursive but its DLL
  loader is top-level only, measured.
- That is the shape every sc4pac-installed DLL mod already uses: the `.dll` at
  the root, its data in the package's own folder. We now match it.
- **Upgrading keeps your settings.** On the first launch the DLL moves any
  pre-4.4.0 root files into `010-SC4UIScale\` before it reads anything, and
  says so in the log. The regenerated log and dev leftovers are dropped rather
  than carried.
- Uninstall is now genuinely two folders plus one file - and the manual
  `FontStyle.ini` step the old README asked for is gone from the instructions,
  because the DLL has reverted that file on every clean shutdown since v4.0.4.
  The README said otherwise; the README was wrong.
- `Test-DatIntegrity` gained a red gate: any file of ours at the Plugins root
  other than `SC4UIScale.dll` now fails the suite, matched by prefix rather
  than a written-down list.

## 4.3.1 (2026-08-29) - the Carbon Skin packages now SHIP

- **v4.3.0 shipped the reskin support but not the packages.** That was an
  inconsistency, not a policy: this mod has always shipped `CamUI`,
  `NamIcons`, `WarriorUI`, `ThirdPartyUI`, `SaveWarningUI` and `WebButtonUI`,
  every one of them built from another mod's own artwork and gated on that mod
  being installed. The eight `ZCarbon*` packages are the same kind of thing and
  are now bundled the same way (24 files, all three tiers).
- **So if you have Scoty Carbon Skin 1.5, it now just works.** Install this
  mod, keep the skin where it is, and the skin's own art and dialog layouts are
  rendered at your scale factor. No local build, no extra step.
- The packages are inert for everyone else: each is gated on the skin's own
  files by exact name and byte size, so with no skin installed they never arm,
  and if the skin is updated or removed they disarm themselves.
- Attribution is in `THIRD-PARTY-NOTICES.md`: the artwork is **Scoty's**,
  enlarged - never Maxis art substituted for his. If Scoty would rather these
  not be distributed, that is his call and they come out on request.

## 4.3.0 (2026-08-29) - Full UI-reskin support, sharper 1.5x, and three god-mode fixes

- **SCOTY CARBON SKIN 1.5 IS SUPPORTED END TO END.** A full reskin replaces
  the UI's art and dialog layouts wholesale - 494 of the same resources this
  mod scales - and is designed to load last, so its 1x versions win and the
  result is 1x art and 1x-positioned dialogs inside a scaled UI. Eight new
  dependency-gated packages (`z_SC4UIScale_ZCarbon*`, 1.5x/2x/3x each) rebuild
  the skin's OWN art and geometry at your scale factor. They arm only while
  the skin's files are present and unchanged, and disarm cleanly to the
  stock-look layer when it is removed - proven, not assumed: with the skin
  filtered out, all 494 contested resources revert to our own packages with
  zero orphans, and the full 1,496-resource baseline matches.
  **Most players have no reskin installed; that is the default state and costs
  nothing.** The release bundle deliberately contains no skin-derived files -
  players with the skin build them locally from the shipped generators.
- **1.5x IS NOW AS SHARP AS 2x AND 3x.** At integer factors the upscaler
  copies pixels exactly (measured: zero invented pixels across 562 million).
  At 1.5x an averaging pass had become the default for 78% of all artwork, to
  buy a tick-evenness property only ~4% of sheets structurally have - the rest
  paid softness for nothing. The averaging is now opt-in, scoped to a derived
  list of sheets that actually contain tick ladders. Measured on the shipped
  files: invented pixels 8.97% -> 1.30%, hard edges at full strength 59% ->
  86%, softened edges 34% -> 8.9%; 2x/3x unchanged.
  Five builders that bypassed the resampler entirely (U-Drive-It balloons,
  uncovered icons, NAM icons, web button, carbon icons) were smoothing at
  EVERY tier and now use nearest.
- **GOD MODE: three fixes.** The day/night and terraform flyouts docked 48px
  and 135px off with a reskin installed - the dock constants were the
  alignment-marker rule precomputed on stock art, and the skin moves that
  marker. The dock now derives from the live marker, which is an identity on
  an unmodded install. And the disaster flyout's buttons broke when scrolled:
  a hook that neutralises a dual-use field was never installed because its
  install site sat behind a hard-coded screen-position band, so the game read
  scroll-arrow art from the wrong column of the sprite sheet. That band is
  replaced by a positive identification; a second latent instance that would
  have failed at 3x is fixed with it.
- Also: the mod now warns in its log when a reskin is installed without the
  matching packages, when two copies of a gated mod file exist, and when a
  skin folder name could sort ahead of our overrides.

## 4.2.0 (2026-08-24) — BREAKING LAYOUT CHANGE: two folders + the root DLL pair

- **The install shrinks from ~23 loose root files to two folders plus the
  root DLL pair**: `Plugins\010-SC4UIScale\` (all packages and fonts), the
  unchanged `Plugins\zzz-SC4UIScale\` overrides folder, and
  `SC4UIScale.dll` + `SC4UIScale.ini` (+ the generated log) at the top
  level — **measured on the move's maiden boot: SimCity 4's dat scan is
  recursive but its DLL loader is top-level only**, so the DLL and its
  beside-the-DLL files cannot move. Uninstall = delete two folders + any
  file named `SC4UIScale.*`. The `010-` prefix is load-bearing: it keeps
  the main packages loading BEFORE `050-load-first\` and `150-mods\`, so
  CAM, the 36-style mod, save-warning and their kin keep beating our
  stock-derived copies exactly as they did at the root (that losing is the
  compatibility mechanism).
- Both the dev deploy and the release `Install.ps1` auto-migrate old
  root-layout installs: the font snapshot and state files move into the new
  folder, stale root packages are removed, and the user's ini is preserved
  on upgrade (new). `Test-DatIntegrity` goes red on any root leftover
  outside the DLL-anchored set.
- New `PluginsRoot()` resolution in the DLL: every subsystem that hunts
  OTHER mods' files (the six third-party dependency gates, the
  uncovered-icon scan, web-button detection, and the `SC4GraphicsOptions.ini`
  read/write pair) now roots at the real Plugins root instead of "beside the
  DLL" — required for the move, and logged like every resolver.
- Fixed in passing: `z_SC4UIScale_CsiIcons-*.dat` (the U-Drive-It offer
  balloon icons) was **absent from every dist bundle since 2026-08-18** —
  the bundle builder's manifest parser could not see its expression-built
  deploy line. Rescued explicitly, with a bundle-size floor so the next
  silent drop goes red. Also hardened eight sibling-path buffers against a
  path-length overflow.
- sc4pac note: package paths changed; the channel entry (maintained
  externally) needs a matching update.

## 4.1.1 (2026-08-24, local instrumented build — not a public release)

- No gameplay or scaling changes. Research instrumentation that closed three
  of the register's four open items in one evening (all log-only, ini-gated,
  default off, fully inert without their keys):
  - `[Probe] GpuCap` — the DX7 draw-call census (`gdcap.cpp` wired into the
    DLL): GCAP v2 records with two-level caller attribution (immediate
    DrawArrays caller + the SubmitPrimitive 0x7D2990 caller, which names the
    drawing SYSTEM), city-view latch with early-exit safety, dual frame
    markers (Clear/Flush) self-selecting in-city, file written at shutdown
    only. Closed register #4; ground-truth-validated against the v4.1.0 pin
    draw sites.
  - `[Probe] FontGuid` — logs every `SetFontStyleByGUID` assignment
    (obj/guid/prev/caller). Closed register #24: the purple-GZWinText state
    does not reproduce on current builds; fallback GUID stored 0 times.
  - `[Probe] ForceRuntimeScaleId` — dev repro lever excluding one window id
    from kNeverScaleIds (used with a dat quarantine to recreate the
    runtime-only state; documented double-scale hazard in its log line).
  - `[Probe] ViewListRepeat` hygiene: always logs its resolved value; the
    null-render-singleton early-out now says so instead of silent-nulling.
    Its colour dump closed register #22/#23 (the data-view tint is NOT a
    view object).

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
  pass; the full diagnosis was written up in the 2026-08-23 session handoff
  (deleted 2026-08-29 and superseded by
  `research/laws/project-sc4-flyout-bottom-anchor.md`, which carries it under
  "What is still open") - the key
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
