# MECHANISM GENERATIONS — which families are still on an old one

**Why this exists.** Our scaling mechanisms have gone through several
generations, and older UI families were never upgraded when a better one
arrived. The Create Disaster flyout proved the point: it was the FIRST flyout we
ever scaled (v2.11.x), still sized only once `IsVisible()` was true, and still
jumped on open — while every other flyout had been upgraded twice since.

**When a family misbehaves, check its GENERATION before designing anything.**

## The generations

| # | mechanism | in code | requires |
|---|---|---|---|
| 1 | scale-when-visible | the sweep sizes it after `IsVisible()` | — (produces an open-flash) |
| 2 | pre-scale while hidden | `IsRegionPanelId` / `IsGodPanelId` / `IsAlwaysScaleCityId` exceptions in `ScalePanelsUnder`'s visibility gate (cite the SYMBOL, not a line - the old `:~5482` cite pointed at the GZWinBMP vtable copy by the time the 2026-08-01 audit checked it) | the window must **persist hidden**. ⚠ #89 measured the limit: membership only bypasses the sweep's `!IsVisible()` skip - it does NOT change WHEN the sweep runs, so a window already on screen at the first pass gains nothing |
| 3 | data pre-scale | `kDataScaledSubtreeIds` + doubled `area=` | fully scripted, not runtime-composed |
| 4 | builder constant patch | `CodePatches` | constants each feed exactly one coordinate |
| 5 | born-at-Place detour | `SubPlaceDetour` (v2.36.0) | code-created, coupled constants |
| 6 | born chrome state | v2.36.2 | born geometry ALSO needs born hook state |
| 7 | data-born + dependency gate | `ScaleTier::kThirdPartyDeps` (v2.38.x) | static doubling that wins the load order |
| 8 | **coupled art + budget patch** | 2x art in `CODE_BOUND_TGIS` **plus** the byte that re-derives the container's width budget from that art (`CodePatches::ApplyAdviceRowScale`, v2.40.0) | the element shares a fixed total with a sibling, so art alone EVICTS the sibling. Both halves ship and revert together; the art alone is a regression |

| 9 | **settle-gated detour scale** (EARLYDOCK, #89, v2.41.19) | `EarlyDockTick` from the `cGZWin::SetFlag` detour: fire the moment the subtree reports its **full design child count** (direct "fully built" signal), scale via the sweep's own `ScalePanelRoot` (scaleMap ⇒ the sweep later skips it), and run any one-shot-surface recreate **in the same action** (`TryRecreateMinimapSurface`) | the panel is ON SCREEN during city load, so gens 1-8 are all too late. Measured +109-328ms vs the sweep's +968ms. ⛔ Its two dead siblings: the message queue never fires during the load tail, and geometry mutation inside `PostCityInit` crashes (~25 windows; two byte writes are fine) |

**Generation 9's install/fire timing:** installed by `InstallShowHook` at
`ArmDeferred` (PostCityInit), fires from the game's own `SetFlag` stack after
init returns. It exists because the audit's finding held: **check when a
mechanism INSTALLS and FIRES before reaching for it** - gens 1-8 all fire at or
after the first sweep pass, which is after the city HUD's first paint.

**Generation 8 is the first mechanism where the DATA half is unsafe on its
own.** Generations 3 and 7 also ship art/scripts, but there a missing code
half merely leaves something unscaled. Here it removes a working control. Any
future entry of this shape must record the coupling in the builder comment,
`Test-DatIntegrity.ps1`, the `Settings.h` switch, `REGRESSION.md` and
`HANDOFF.md` — five places, because flipping the ini switch is the instinctive
response to a bad report and it makes this class of bug WORSE, not better.

## Audited 2026-07-31, RE-VERIFIED against the exe the same evening

⚠ **The first draft of this table was wrong in three of four rows** — it was
compiled from `UiSpike.cpp`'s own comment listing "seven enumerated call
sites", but an exhaustive E8-rel32 scan of the exe found **ELEVEN** call sites
into the open funnel `sub_7E5C10` (0x7EC770, 0x7EDB16, 0x7EDC12, 0x7EDC73,
0x7EF6D9, 0x7F484E, 0x7F48B2, 0x7F4C80, 0x7F4FE6, 0x7F5049, 0x7F5221). The
lesson is the SCOPE NULL again: the comment answered "which sites did we
enumerate", not "which sites exist".

| family | roots | gen (verified) | truth | the measurement |
|---|---|---|---|---|
| **Emergency** | `0x0992FD17` | **at-open (v2.36.1)** — IS on the funnel | site 0x7F4C80 pushes id 0x0992FD17; dock marker (3,234) verified EXACT in `I-899302fc.ui` | `FLYOPEN 0x0992FD17` on open (cap 12, open early) |
| **U-Drive-It column** | `0x8BB27C12` | **at-open** — IS on the funnel | site 0x7EF6D9 pushes id 0x8BB27C12; marker (4,150) verified EXACT in `I-6bb27447.ui` | `FLYOPEN 0x8BB27C12` |
| **Terrain-FX / Day-Night** | `0xCA35CBED` | **at-open, dock included** — TWO funnel sites (0x7EDC73 terrain-fx, 0x7F5049 day/night); `OnFlyoutOpened` runs the whole god table incl. the dock | the first-draft "dock gen 1" claim was wrong | possible 1-frame jump remains only if `dayNightActive` flips AFTER the open-scale — watch for a `(moved)` line on the tick after a day/night toggle |
| **Signs & Labels** | `0xAB954023` | ✅ **RESOLVED v2.39.6 (task #81, user-confirmed)** — was the only genuine gen-1 flyout | it opens through `sub_7E5D80` (site 0x7F50A7), a byte-identical TWIN of the funnel (latch `[edi+0x204]` vs `[edi+0x200]`, ret 0x14 vs 0x10); the FLYOPEN2 twin hook (v2.39.6) closed it exactly as this row's "cheap fix" predicted | `FLYOPEN2 0xAB954023` on open; with it, **every flyout in the game is born-modern** |
| **UNKNOWN flyout** | `0x09DE8798` (script `0x09DE3002`) | **untracked** — in NO list anywhere in UiSpike.cpp | the twin's SECOND call site (0x7E718A, reached from dispatcher `sub_7E7130` on `[esi+8]==1`); the script exists in NO extracted corpus (structural null — identify before hooking the twin) | log `GetChildWindowFromIDRecursive(0x09DE8798)` per mode; find what UI it even is |
| **Text Entry / Set Lot Size / Business Deals / Save box** | `0xC9264BE2`, `0x8926EEBE`, `0x4C30E4FA`, `0xAA8DEF97` | **RESOLVED v2.39.9/.11** ✅ | ⚠ **THIS ROW'S LATENT FIRED THE SAME EVENING IT WAS WRITTEN.** The "Saving Disabled" box opened at **4x** — `MWKID 0xAA8DEF97 (200,241 2000x700)`, exactly 4x its 500x175 design — because the already-scaled guard was scoped to the two quit confirms. The guard is now GENERAL **and** gated on `Classify == Fresh` (so it means "arrived scaled", not "is currently wide"). Both user-confirmed. | Superseded by the measured ownership table below — the "Set Lot Size unmeasured" caveat is partly answered: its staged sizes are known at every tier, a live 1x ARRIVAL is still unrecorded (and now unreachable outside a package-load failure) |
| **Create Disaster** | anonymous under `0x9A47B417` | ✅ **6/6 — COMPLETE v2.39.8 (task #80, user-confirmed "arrow works now in both modes")** | on NO funnel at all (zero sites in either opener — its builder has one gated caller), so born-at-Place was the only possible lever; size+dock+metrics+arrow+chrome all at birth; the v2.39.8 offset-frame fix was the last piece (the read-guard had refused the born-metrics write since v2.39.5) | v2.39.8 acceptance in REGRESSION.md |

## The city-dialog ownership table (MEASURED 2026-07-31, `who_owns_tgi.py` + staged corpora)

Taken while resolving the "Saving Disabled" 4x. **All three ids are data-born
at EVERY scaled tier**, so the dialog block's runtime scaling of them is
unreachable in any shipping configuration — it is belt-and-braces for a
package-load failure, which is exactly why it must stay *guarded* rather than
be deleted.

| id | script | stock 1x | 1.5x | 2x | 3x | winner of the load order TODAY |
|---|---|---|---|---|---|---|
| `0xAA8DEF97` | `I-ca8cbf0f` | 300x166 | 450x249 | 600x332 | 900x498 | **`zzz-SC4UIScale\z_SC4UIScale_CamUI-2x.dat` at 1000x350** — CAM replaces the script with a LARGER one; 4 files carry this TGI |
| `0xC9264BE2` | `I-e9263d4c` | 319x113 | 479x169 | 638x226 | 957x339 | root `z_SC4UIScale_DialogStatic-2x.dat` |
| `0x8926EEBE` | `I-e9263de5` | 249x92 | 374x138 | 498x184 | 747x276 | root `z_SC4UIScale_DialogStatic-2x.dat` |

⚠ **The CamUI winner's 1000x350 is EXACTLY the live arrival that produced the
4x** (`MWKID 0xAA8DEF97 (200,241 2000x700)` = 1000x350 doubled) — independent
confirmation of the diagnosis from a completely different instrument. Note the
Save box's own `designW` in `kCityDialogIds` is 560, i.e. it was entered
against the STOCK 300x166 script's auto-fit behaviour, not against CAM's larger
replacement; the guard threshold (700) still separates them, but the number is
a stock-era constant worth re-deriving if CAM's script ever changes.

At stock tier the DLL renames the static dats aside and is fully inert, so
there is no configuration in which these dialogs both arrive 1x *and* get
runtime-scaled — except a package-load failure.

**Also found in the re-verification, all measured:**
- `kGodToolFlyoutIds`' two comments are **swapped** (`0xCA35CBED` labelled
  terraform, `0x49923239` labelled terrain-effect — every other site in the
  file has them the right way round). Fixed in-source 2026-07-31.
- The "PREDICTED from the script, not measured" warnings on the Emergency and
  U-Drive-It dock offsets can be retired — both markers verified exact.
- ~~`gMayorDock` defaults **0** in code and NO redistributable ini carries a
  `[Flyout]` section — a fresh install scales mayor flyouts but never docks
  them. The live machine works because its ini has `MayorDock=1`. Fix the
  bundles before any redistribution.~~
  ✅ **CORRECTED 2026-08-16 — CLOSED by #95 Phase 4 (2026-08-02). `gMayorDock`
  now defaults to 1 (`src\UiSpike.cpp:528`), flipped for exactly the reason
  this bullet gave (`src\UiSpike.cpp:521-527`); 0 is now the MEASURING escape
  hatch. The bundle half is still literally true — neither
  `_packaging\SC4UIScale.ini` nor `dist\SC4UIScale-v3.0.0\Plugins\SC4UIScale.ini`
  carries a `[Flyout]` section — but it is no longer a defect: the ini read is
  `GetPrivateProfileStringA("Flyout", "MayorDock", "", ...)` guarded by
  `if (b[0])` (`src\UiSpike.cpp:12115-12116`), so an absent section leaves the
  compiled default standing and a fresh install docks. NO bundle action is
  required before redistribution.**
- `OnFlyoutOpened` has two SILENT bail-outs (`!lastView || inPass`, and
  ScaleGodFlyouts' toolbar-not-scaled early-return) that drop any funnel
  flyout to gen-1 behaviour for one frame with no log line.
- The dock markers come from script group `G-96a006b0`, but a second group
  (`G-08000600`) carries DIFFERENT marker values for Zones/Civic and nothing
  asserts which group the game loaded — a silent trap if a resolution change
  ever flips it.

## Stale doc claims found in the same audit

- **`GOD-MODE-FLYOUTS.md:96`** — *"Disaster's root is vis=0 always."* Every
  logged sighting is `vis=1`, and the code requires `IsVisible()` to find it.
  The sentence is about `0x0A78827A`, a different window.
- **`GOD-MODE-FLYOUTS.md:56`** — *"Disaster: Scaled = NO"* and `:107`
  *"UNSOLVED"*. Two generations stale.
- **`REGRESSION.md:2132`** — *"same class, different id"*. The disaster
  container has **no id at all**.
- **`GOD-MODE-FLYOUTS.md:121`** — *"`0x0A78827A` … remove it from
  SCALED_WINDOW_IDS"*. Already adjudicated against; it **is** the god toolbar in
  a founded city.
- **`0xABB26B0E` "ini-gated (default OFF)"** — `IsAlwaysScaleCityId` returns
  true for it unconditionally, so it is scaled while hidden regardless of the
  switch, and the U-Drive-It dock math silently depends on that.

## Dead entries that advertise coverage they do not deliver

~~`kAlwaysScaleCityIds` contains `0xCA35CBED` and `0x699306ED`, but both are
`continue`d earlier in the same loop by `IsGodToolFlyoutId` /
`IsMayorOnlyFlyoutId`, so they can never reach the visibility exception. For
`0x699306ED` it is doubly meaningless — mayor flyouts are destroyed and
recreated per open, so there is no "hidden" to pre-scale.~~

**CORRECTED 2026-08-16 — ACTED ON, so this is history, not a live inventory.**
The finding was right and #95 Phase 4 REMOVED both ids from
`kAlwaysScaleCityIds`, citing this reasoning verbatim in the source
(`src\UiSpike.cpp:5309-5316`: *"they were dead entries advertising coverage
they could not deliver … Both are `continue`d earlier in the same loop"*).
Verified 2026-08-16: the array now runs `src\UiSpike.cpp:5234-5352` and
contains neither id — the only occurrence of either between those lines is
that removal comment. Each id lives in its own mechanism instead:
`0xCA35CBED` in `kGodToolFlyoutIds` (`:4903`, scaled by `ScaleGodFlyouts`) and
`kGodFlyoutDock` (`:12932`); `0x699306ED` in `kMayorFlyoutDock` (`:5130`).
Both are still in `SCALED_WINDOW_IDS`, so `Test-BornCorrectCoverage` still
sees them — it reports them as *"covered by its OWN mechanism only"*
(`_tests\Test-BornCorrectCoverage.ps1:139`), naming `kGodToolFlyoutIds` and
`kMayorFlyoutDock`, since `kGodFlyoutDock` is not one of the three arrays that
test parses (`:122-126`). Removal shipped with #95 (closed v2.46.0,
`_tests\REGRESSION.md:4069`); the exact build that carried Phase 4 is not
recorded in-source. The second sentence's per-open destroy/recreate rationale
was not re-verified in this pass — it is struck only because the paragraph as
a whole no longer describes the code. **Keep this section as the WORKED
EXAMPLE of the failure shape ("a list entry that a preceding `continue` makes
unreachable"), and read the heading above as historical: do not go looking for
these two entries in the list.**
