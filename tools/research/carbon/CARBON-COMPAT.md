# Scoty Carbon Skin 1.5 × SC4UIScale — offline compatibility analysis

Measured 2026-08-25 (overnight, offline — no game launch). Source drop:
`Downloads\Scoty_Carbon_Skin_1-5 (2)\z____scoty_mods\z__Scoty_Carbon_Skin\`
(27 dats + PDF note), mirrored to `tools\research\carbon\source\`
(NOT committed — third-party redistribution; the public repo never ships it).

## What the skin is

A full UI reskin (anthracite/gray): 5 core dats + per-mod add-on
redeclarations. The author's contract (PDF):

- drop `z____scoty_mods\` into Plugins; **the skin must load AFTER every
  UI-modifying plugin** (its redeclarations beat the mods they restyle);
- delete `y_`/`z_` add-on dats whose target mod isn't installed;
- choose ONE of RCI-Qry A–E and ONE of CensusRepo Expanded/Regular;
- requires the game's **Interface Transparency** option ON — Carbon covers
  group `46A006B0` (×371) but barely its opaque twin `1ABE787D` (×20; the
  twins law is UNKNOWNS-AND-NEXT-TARGETS.md row "UI art store");
- does not support 800×600, tutorial mode, developer mode.

## Installed-target audit (this machine, both Plugins trees swept; Steam tree empty)

KEEP (target present): core ×5 (`scoty_Carbon_Files/FSH/PNG/Txt/Txt_NoLatin`),
`w_..SaveWarning_optA` (150-mods SaveWarning_Disable_Exit_Quit.dat),
`w_..SubMenu-Essential` (memo.submenus-dll), `y_scoty_CAM_Extended_Essentials`
(050-load-first CAM core), `y_scoty_Carbon_NAM` (770-network-addon-mod),
`z_scoty_Carbon_BuildingStyles` (150-mods CoriBoom 36-slot UI).

DELETE (target absent): DAMN, CensusRepoQE ×2, ExtendedTerrainUI,
RCI-DLL-Qry-Upgrd ×5, RegionCensusDLL, Yellow-pause-remover, GodMod,
ExtendDataView, RaiseUI, CAM_Casino_Essentials. (RaiseUI absent is good —
a 40px geometry mover that would have fought the scaler.)

## The collision census (the decisive numbers)

`carbon_census.py` → `_tests\captures\2026-08-25-carbon\carbon-vs-ours-intersection.txt`

- Carbon kept dats: **673 unique TGIs** (403 PNG, 206 .UI, 41 LTEXT, 22 FSH, 1 DIR).
- Ours (live 010- + zzz-): 1,496. **Intersection: 494 TGIs = 73% of Carbon.**
- At the natural placement `010-SC4UIScale < z____scoty_mods < zzz-SC4UIScale`:
  - **CARBON beats our 010 packages on 473**: 337 PNG + 135 .UI + 1 LTEXT
    (SelectiveArt 249+26, DialogStatic-15x 87+109, ItemIcons 1, WebText 1)
    → 1× carbon art and 1×-positioned carbon dialogs inside a scaled UI.
  - **Our zzz beats carbon on 21**: CamUI 9+1, CsiIcons 8, SaveWarningUI 2,
    ThirdPartyUI 2, ItemIconsSub 1 → scaled-Maxis patches inside the skin.
- No folder placement fixes both directions. Placing carbon BEFORE 010 also
  kills its CAM/NAM/submenu redeclarations (they'd lose to 050-/150-/770-).
- Carbon-only remainder (179 TGIs): loads under runtime scaling — the
  .UI-geometry hooks scale whatever geometry loads; art drawn via the
  GZWinBMP path follows the runtime-image lever. Live verification pending.
- Carbon's 22 FSH: region/3D-texture domain (`{7AB50E44,1ABE787D}` consumer
  path), disjoint from our static packages — loads free.
- The 1 LTEXT collision is the web-button caption (ours: WebText, armed only
  when the web-button mod is ABSENT; carbon's: "Visit Scoty's productions…").
  Carbon winning it is acceptable — caption only, our WebRedirect still hooks
  the click.
- Intra-carbon layering is real: add-on dats redeclare core TGIs
  (alphabetical last-wins INSIDE its folder) — any per-TGI source extraction
  must resolve the carbon-internal winner first (`carbon_stage.py` does).

## Feasibility measurements (all green)

1. **Dimensions**: 250 shared PNGs — carbon is authored at stock 1×
   (ours/carbon ≈ 1.5 on both axes across the board; `dim_compare.py`).
   A handful are deliberately resized by the skin ("repositioning") — the
   carbon-sourced build scales carbon's own dimensions, so they ride along.
2. **QFS**: `scoty_Carbon_Files.dat` payloads are RefPack-compressed (DIR
   entry present; DbpfPack's banner is blind to it — its --extract is RAW).
   `DbpfExtract.exe` decompresses (147/147, 0 failures); `qfs_ab.qfs` also
   round-trips (149,337 bytes == header usize).
3. **.UI format**: carbon scripts are the same `<LEGACY …>` text our
   dialog-static scaler parses/edits/verifies.
4. **Production scaler**: `Upscale2x.exe --factor 1.5` on carbon art —
   carbon dock plate (235,222)→(353,333), exactly our stock-build's output
   frame. (Bare invocation; the real build passes the nine-slice/no-snap/
   height-exact lists.)
5. **Repack**: DbpfPack (the daily packer) — no new capability needed.

Prepared inputs: `tools\research\carbon\builder-inputs\thirdparty-src\`
(206 decompressed .ui, bare-hex names) + `thirdparty-art\` (404 PNG),
extracted in game-load order so later dats overwrote (winner-resolved).
`extracted-plain\` holds the same content in analysis naming + MANIFEST.

## The architecture (the CamUI pattern, scaled up — settled by the 4-lane
## pipeline survey, 2026-08-25, wf_9d883e33-862)

Treat Carbon exactly like CAM: the skin installs at its natural place and
WINS everywhere it is designed to; we ship **carbon-sourced, carbon-gated
scaled packages in zzz-SC4UIScale** that re-win the colliding TGIs with
carbon-STYLED scaled content:

- **Names are load-bearing: every carbon package base starts `ZCarbon`**
  (`z_SC4UIScale_ZCarbonUI`, `z_SC4UIScale_ZCarbonIcons`, …) so it sorts
  AFTER every existing zzz package (CsiIcons/ItemIconsSub/SaveWarningUI/
  ThirdPartyUI/…) and wins their shared TGIs when armed; gate-off hands
  those TGIs straight back. Base names stay purely alphanumeric after
  `z_SC4UIScale_` (Test-DatIntegrity drift regex `z_SC4UIScale_[A-Za-z0-9]+`).
- **ZCarbonUI** (the big one): carbon-sourced scaled copies of the 473
  carbon-wins TGIs (135 scripts + 337 art + the root-package clone TGIs
  referenced by scripts whose art carbon overrides — survey risk 5).
  Built by the existing dialog-static + selective-safe third-party
  machinery; enrollment (TP_TARGETS/TP_ART_PACKAGE, ~472 rows) is
  GENERATED from `carbon-vs-ours-intersection.txt`, never hand-typed.
- **ZCarbonIcons** (BUILT tonight as the end-to-end demonstration,
  `build_carbon_icons.py` → `proto-packages\z_SC4UIScale_ZCarbonIcons-{15x,2x}.dat`,
  18 PNGs): the 8 CSI balloons duplicated into BOTH twin groups (carbon
  ships zero `1ABE787D` twins — the #188 scoping trap), + ItemIcons strip
  `00001111` + Missing Thumb `144161EC` via the ItemIconsSub Upscale2x
  recipe. Frames verified IDENTICAL to the live stock-derived CsiIcons-15x
  (16/16) — a drop-in geometric twin.
- **WebText: deliberately NO carbon build.** Carbon's caption already says
  Simtropolis (consistent with WebRedirect); it covers 12 locale groups to
  our 1. Losing that TGI to carbon is the correct end state.
- **Gates** (kThirdPartyDeps): geometry-bearing packages pin EXACT name +
  size on `scoty_carbon_PNG.dat` (3,460,148) + `scoty_Carbon_Files.dat`
  (268,639); pure-art packages presence-only. Never a WebButtonModPresent-
  style substring scan (no self-skip). FindPluginFile already skips our
  folders — no new skip entries. Packages sourced from carbon's ADD-ON
  redeclarations gate on the add-on dat itself, which encodes both facts in
  one file (e.g. a phase-2 carbon SaveWarning variant gates on
  `w_scoty_Carbon_CB_SaveWarning_optA.dat` + `scoty_Carbon_Files.dat` —
  fits the 2-file struct without extension).
- Survey risk 3 (package-ownership): carbon redeclares save-warning/CAM
  scripts (e.g. `6A553AA4`, `0A55161D`, `12121201`) — enrollment follows
  the MEASURED winner (regenerate `winning-corpus.json` with carbon
  installed; the winner assert then names every carbon-held target), never
  blanket-assigned while the existing gates still own them.
- Phase 1 leaves the remaining zzz-side collisions OURS (CamUI 9+1,
  SaveWarningUI 2, ThirdPartyUI 2 — functionally correct, Maxis-styled
  patches). Phase 2 ships ZCarbon variants for them.
- Deploy/Test/Dist wiring per package: one kThirdPartyDeps row + one
  SyncDat+DepOkByName call (BOTH, in the same change — #119), 3 LITERAL
  Copy-Item lines in Deploy-OnGameClose + $DEPENDENCY_GATED entry,
  EXPECTED + BUILT_PAIRS rows in Test-DatIntegrity. Build-Dist needs
  nothing when the copy lines are literal (its parser is blind to
  expression-built copies — the CsiIcons incident).

## Build-readiness (measured tonight)

Every corpus prerequisite is PRESENT on this machine: uiscripts corpus
(331), 1x extract (2,281), preview 2x/15x/3x (2,206 each),
winning-corpus.json. Carbon inputs prepared: `builder-inputs\thirdparty-src`
(206 decompressed .ui) + `thirdparty-art` (404 PNG), extracted by
DbpfExtract in game-load order (winner-resolved). The ONLY step that
requires the skin in the live tree first is the winning-corpus.json
regeneration (Bootstrap harvests from live Plugins) — an install-moment
step, not a blocker tonight.

A pruned install folder is staged at `install-staged\z____scoty_mods\`
(the 10 KEEP dats + the author's PDF; the 17 not-installed-target dats
removed per the author's own rule). ⚠ DO NOT drop it into Plugins until
ZCarbonUI is built, gated, and deployed — with the skin installed and no
carbon packages, carbon beats our 010 layer on 473 TGIs and the UI looks
broken at any fractional tier.

## Order of work for the implementation session

1. Install `install-staged\z____scoty_mods\` into Plugins (game closed).
2. Regenerate winning-corpus.json + Bootstrap TP harvest (carbon now the
   measured winner on its TGIs).
3. Generate enrollments from the intersection file; run selective-safe +
   dialog-static at 15x/2x/3x → ZCarbonUI dats; promote build_carbon_icons
   outputs (or fold them into the generated package set).
4. DLL: kThirdPartyDeps rows + SyncDat calls; version bump; build.
5. Deploy wiring (literal lines + $DEPENDENCY_GATED) + Test-DatIntegrity
   rows; run the gate suite offline.
6. Per-TGI winner census (three-layout: stock / +carbon / +carbon+ZCarbon)
   — every colliding TGI must end owned by a ZCarbon dat; zero winner
   changes outside the carbon set.
7. Boot + eyes-on at 1.5x/2x (user): dep gates green, skin coherent,
   scaled. Then ledger/memory/release per house law.

## 2026-08-25 implementation addenda

- **User confirmed Interface Transparency is ON** (the skin's requirement).
- **Two more mods installed by the user and handled**: warrior's
  god-terraforming-in-mayor-mode (150-mods, files match WarriorUI's gate
  pins exactly — the existing package arms with zero changes) and
  null-45's region-view-census-ui (DLL at Plugins root + dat in 150-mods).
  Carbon's two matching add-on dats were un-pruned into the installed skin
  (now 12 dats).
- **Eighth package `z_SC4UIScale_ZCarbonGodMod`**: carbon's GodMod dat
  redeclares EXACTLY WarriorUI's four TGIs (scripts `09923283`/`CB95403E`,
  art `EB7C4D3B`/`14215E27`); Z-late beats WarriorUI when armed; gate =
  `z_scoty_Carbon_GodMod.dat` (21,005) + core. Built by the selective-safe
  lane (WarriorUI's twin flow). Carbon's RegionCensus dat is one `.UI` in
  the census DLL's private group `0x9CB6053F` — zero overlap, un-prune IS
  the handling (live check: does the region screen scale its window?).
- **Census v2**: includes DISARMED dats (`.dat.x1-disabled`) — the first
  census missed the GodMod↔WarriorUI overlap because WarriorUI was
  gate-dark. Intersection stays 494 TGIs.
- **DbpfPack timestamp law**: dats are never raw-byte-identical across
  runs (header 24–31 = pack-time stamps); equality proofs zero those bytes
  (REGRESSION.md 2026-08-25).
- **Design order (user)**: users add/remove plugins AT WILL — presence
  gates handle every combination; carbon-absent is the DEFAULT state; the
  public bundle never carries carbon-derived dats (Build-Dist assert),
  carbon users build locally from the shipped generators. All packages
  ship 1.5×/2×/3×.

## 2026-08-25 adversarial review outcomes (all fixed same session)

1. **THE COMPARATOR-AMBIGUOUS BOUNDARY** (critical): `z____scoty_mods` vs
   `zzz-SC4UIScale` was the first folder pair in this tree where upcasing
   and lowercasing comparators disagree — under upcase-ordinal (NTFS
   enumeration; implied by the skin author's own z+underscore convention)
   the skin loads AFTER our overrides and every ZCarbon dat is inert.
   Cure: the skin now installs as **`zz-scoty-mods`** (unambiguous under
   every comparator; installer migrates the author-named folder), and
   `carbon_final_census.py` computes winners under BOTH foldings, going
   RED on any comparator-dependent winner. Full law: REGRESSION.md.
2. Winner assert now checks the SUPPLIER (a non-carbon mod out-sorting
   carbon on an enrolled iid FATALs again, as pre-carbon).
3. Deploy's ZCarbon copies presence-gated (unguarded miss under EAP=Stop
   aborted the tail of the deploy incl. the armed-tier restore).
4. Dep resolution memoized per (name,prefix): 16 walks → 7 (6 skinless).
5. Census counts all DBPF extensions (.dat/.SC4Lot/.SC4Desc/.SC4Model —
   the IsDbpfName law), not `*.dat` only.
6. Mission-bubble carbon path guards against a partial pinned family.
7. Comment counts (seven→eight) + installer header fixed.

## Known residuals (phase-2 candidates, cosmetic only)

- CAM startup splash `ea7f0eae`: carbon's reskin classified untouched
  (UNSCALED-only refs) — the splash keeps our CAM-styled scaled art.
- refmap `clone+retarget` TGIs whose sources carbon owns: root-script
  windows draw stock-styled clone pixels (carbon-script windows are
  correct — dialog-static ships its carbon clone b1f56dba).
- WebText caption: carbon's wins by design.

## Open items for the live session (cannot be resolved offline)

1. The ~179 carbon-only TGIs under runtime scaling — eyes-on pass.
2. Boot verification of gates + winners after the ZCarbon deploy.
3. Region-census DLL window under region-screen runtime scaling — eyes-on.
