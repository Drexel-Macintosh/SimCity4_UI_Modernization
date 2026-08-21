# MECHANISM GENERATIONS — which families are on which one

**Why this exists.** The scaling mechanisms in this project have gone through
several generations, and a UI family scaled by an early generation does not
move to a later one on its own. An open-flash, a one-frame jump, or a control
that arrives at the wrong size is usually a family still running an older
mechanism rather than a new defect.

**When a family misbehaves, check its GENERATION before designing anything.**

## The generations

| # | mechanism | in code | requires |
|---|---|---|---|
| 1 | scale-when-visible | the sweep sizes it after `IsVisible()` | — (produces an open-flash) |
| 2 | pre-scale while hidden | `IsRegionPanelId` / `IsGodPanelId` / `IsAlwaysScaleCityId` exceptions in `ScalePanelsUnder`'s visibility gate (cite the SYMBOL, not a line number — line cites drift onto unrelated code, in one case onto the GZWinBMP vtable copy) | the window must **persist hidden**. Membership only bypasses the sweep's `!IsVisible()` skip; it does NOT change WHEN the sweep runs, so a window already on screen at the first pass gains nothing |
| 3 | data pre-scale | `kDataScaledSubtreeIds` + doubled `area=` | fully scripted, not runtime-composed |
| 4 | builder constant patch | `CodePatches` | constants each feed exactly one coordinate |
| 5 | born-at-Place detour | `SubPlaceDetour` (v2.36.0) | code-created, coupled constants |
| 6 | born chrome state | v2.36.2 | born geometry ALSO needs born hook state |
| 7 | data-born + dependency gate | `ScaleTier::kThirdPartyDeps` (v2.38.x) | static doubling that wins the load order |
| 8 | **coupled art + budget patch** | 2x art in `CODE_BOUND_TGIS` **plus** the byte that re-derives the container's width budget from that art (`CodePatches::ApplyAdviceRowScale`, v2.40.0) | the element shares a fixed total with a sibling, so art alone EVICTS the sibling. Both halves ship and revert together; the art alone is a regression |
| 9 | **settle-gated detour scale** (EARLYDOCK, v2.41.19) | `EarlyDockTick` from the `cGZWin::SetFlag` detour: fire the moment the subtree reports its **full design child count** (direct "fully built" signal), scale via the sweep's own `ScalePanelRoot` (scaleMap ⇒ the sweep later skips it), and run any one-shot-surface recreate **in the same action** (`TryRecreateMinimapSurface`) | the panel is ON SCREEN during city load, so gens 1-8 are all too late. Measured +109-328ms vs the sweep's +968ms. **Law — its two dead siblings:** the message queue never fires during the load tail, and geometry mutation inside `PostCityInit` crashes (~25 windows; two byte writes are fine) |

**Generation 9's install/fire timing:** installed by `InstallShowHook` at
`ArmDeferred` (PostCityInit), fires from the game's own `SetFlag` stack after
init returns. The rule it embodies: **check when a mechanism INSTALLS and
FIRES before reaching for it** — gens 1-8 all fire at or after the first sweep
pass, which is after the city HUD's first paint.

**Generation 8 is the only mechanism where the DATA half is unsafe on its
own.** Generations 3 and 7 also ship art/scripts, but there a missing code
half merely leaves something unscaled. Here it removes a working control. Any
future entry of this shape records the coupling in the builder comment, in
`_tests\Test-DatIntegrity.ps1`, and beside the `Settings.h` switch, because
flipping the ini switch is the instinctive response to a bad report and it
makes this class of bug WORSE, not better.

## Flyout families and their open path

An exhaustive E8-rel32 scan of the exe finds **ELEVEN** call sites into the
open funnel `sub_7E5C10`: 0x7EC770, 0x7EDB16, 0x7EDC12, 0x7EDC73, 0x7EF6D9,
0x7F484E, 0x7F48B2, 0x7F4C80, 0x7F4FE6, 0x7F5049, 0x7F5221. The exe is the
authority on that count — a source comment enumerating call sites answers
which sites are enumerated, not which sites exist.

`sub_7E5D80` is a byte-identical TWIN of the funnel (latch `[edi+0x204]` vs
`[edi+0x200]`, ret 0x14 vs 0x10). Its call sites are 0x7F50A7, which pushes
id `0xAB954023`, and 0x7E718A, reached from dispatcher `sub_7E7130` when
`[esi+8]==1`, which pushes id `0x09DE8798` (script `0x09DE3002`).

| family | roots | generation | evidence | the measurement |
|---|---|---|---|---|
| **Emergency** | `0x0992FD17` | **at-open (v2.36.1)** — IS on the funnel | site 0x7F4C80 pushes id 0x0992FD17; dock marker (3,234) verified EXACT in `I-899302fc.ui` | `FLYOPEN 0x0992FD17` on open (cap 12, open early) |
| **U-Drive-It column** | `0x8BB27C12` | **at-open** — IS on the funnel | site 0x7EF6D9 pushes id 0x8BB27C12; marker (4,150) verified EXACT in `I-6bb27447.ui` | `FLYOPEN 0x8BB27C12` |
| **Terrain-FX / Day-Night** | `0xCA35CBED` | **at-open, dock included** — TWO funnel sites (0x7EDC73 terrain-fx, 0x7F5049 day/night) | `OnFlyoutOpened` runs the whole god table including the dock | if `dayNightActive` flips AFTER the open-scale the dock moves one frame later; the tick after a day/night toggle logs a `(moved)` line when it does |
| **Signs & Labels** | `0xAB954023` | **at-open (v2.39.6)** — the last family to leave generation 1 | it opens through the twin `sub_7E5D80` (site 0x7F50A7), which the FLYOPEN2 twin hook scales exactly as the funnel hook scales the eleven | `FLYOPEN2 0xAB954023` on open; with it, **every flyout in the game is born-modern** |
| **Text Entry / Set Lot Size / Business Deals / Save box** | `0xC9264BE2`, `0x8926EEBE`, `0x4C30E4FA`, `0xAA8DEF97` | **data-born (v2.39.9/.11)** | the already-scaled guard is GENERAL **and** gated on `Classify == Fresh`, so it means "arrived scaled", not "is currently wide" | staged sizes are known at every tier (ownership table below); a live 1x arrival is reachable only through a package-load failure |
| **Create Disaster** | anonymous under `0x9A47B417` | **born-at-Place (v2.39.8)** | on NO funnel at all — zero sites in either opener, and its builder has one gated caller — so born-at-Place is the only available lever; size, dock, metrics, arrow and chrome all land at birth | the born-metrics write clears the read-guard once the offset frame is correct (v2.39.8) |

## The city-dialog ownership table

Measured with `tools\dbpf\who_owns_tgi.py` against the staged corpora. **All
three ids are data-born at EVERY scaled tier**, so the dialog block's runtime
scaling of them is unreachable in any shipping configuration — it is
belt-and-braces for a package-load failure, which is exactly why it stays
*guarded* rather than deleted.

| id | script | stock 1x | 1.5x | 2x | 3x | winner of the load order |
|---|---|---|---|---|---|---|
| `0xAA8DEF97` | `I-ca8cbf0f` | 300x166 | 450x249 | 600x332 | 900x498 | **`zzz-SC4UIScale\z_SC4UIScale_CamUI-2x.dat` at 1000x350** — CAM replaces the script with a LARGER one; 4 files carry this TGI |
| `0xC9264BE2` | `I-e9263d4c` | 319x113 | 479x169 | 638x226 | 957x339 | root `z_SC4UIScale_DialogStatic-2x.dat` |
| `0x8926EEBE` | `I-e9263de5` | 249x92 | 374x138 | 498x184 | 747x276 | root `z_SC4UIScale_DialogStatic-2x.dat` |

**Note:** the CamUI winner's 1000x350 doubles to `MWKID 0xAA8DEF97 (200,241
2000x700)` at 2x, and that arrival is what the general `Classify == Fresh`
guard exists to catch — a guard scoped to a hand-listed pair of dialogs does
not see it. The Save box's own `designW` in `kCityDialogIds` is 560, entered
against the STOCK 300x166 script's auto-fit behaviour rather than CAM's larger
replacement; the guard threshold of 700 separates the two.

At stock tier the DLL renames the static dats aside and is fully inert, so
there is no configuration in which these dialogs both arrive 1x *and* get
runtime-scaled — except a package-load failure.

**Measured details:**
- In `kGodToolFlyoutIds`, `0xCA35CBED` is the terrain-effect flyout and
  `0x49923239` is terraform.
- `gMayorDock` defaults to **1** (`src\UiSpike.cpp:528`); 0 is the measuring
  escape hatch. Neither the packaged ini nor the dist ini carries a
  `[Flyout]` section, and that is fine: the read is
  `GetPrivateProfileStringA("Flyout", "MayorDock", "", ...)` guarded by
  `if (b[0])` (`src\UiSpike.cpp:12115-12116`), so an absent section leaves
  the compiled default standing and a fresh install docks.
- `OnFlyoutOpened` has two SILENT bail-outs (`!lastView || inPass`, and
  ScaleGodFlyouts' toolbar-not-scaled early-return) that drop any funnel
  flyout to gen-1 behaviour for one frame with no log line.
- The dock markers come from script group `G-96a006b0`, but a second group
  (`G-08000600`) carries DIFFERENT marker values for Zones/Civic and nothing
  asserts which group the game loaded — a silent trap if a resolution change
  ever flips it.

## Container and root facts

- Disaster's root is `vis=1` in every logged sighting, and the code requires
  `IsVisible()` to find it. `0x0A78827A` is a different window.
- The disaster container is scaled (born-at-place) and has **no id at all**.
- `0x0A78827A` stays in `SCALED_WINDOW_IDS` — it **is** the god toolbar in a
  founded city.
- `0xABB26B0E` is scaled while hidden regardless of any switch
  (`IsAlwaysScaleCityId` returns true for it unconditionally), and the
  U-Drive-It dock math silently depends on that.

## Worked example: a list entry that a preceding `continue` makes unreachable

The failure shape: an id sits in `kAlwaysScaleCityIds`, but an earlier
`continue` in the same loop removes it from the walk before the visibility
exception is ever reached. `IsGodToolFlyoutId` and `IsMayorOnlyFlyoutId` both
`continue` ahead of that exception, so any id they match gains nothing from
membership. For a mayor flyout the membership is doubly inert — mayor flyouts
are destroyed and recreated per open, so there is no "hidden" window to
pre-scale.

`0xCA35CBED` and `0x699306ED` are the worked example. Neither is in
`kAlwaysScaleCityIds`; each is scaled by its own mechanism instead —
`0xCA35CBED` by `kGodToolFlyoutIds` (`src\UiSpike.cpp:4903`, scaled by
`ScaleGodFlyouts`) and `kGodFlyoutDock` (`:12932`); `0x699306ED` by
`kMayorFlyoutDock` (`:5130`). The reasoning is recorded in the source at
`src\UiSpike.cpp:5309-5316`. Both ids remain in `SCALED_WINDOW_IDS`, so
`Test-BornCorrectCoverage` reports them as *"covered by its OWN mechanism
only"* (`_tests\Test-BornCorrectCoverage.ps1:139`).
