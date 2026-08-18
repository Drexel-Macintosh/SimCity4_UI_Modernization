# Selective-Safe 2x UI Art Override — z_SC4UIScale_SelectiveArt.dat

Built 2026-07-21 by `build_selective_safe.py` (this folder), implementing the
selective mechanism prescribed by `tools\research\UI-ART-BINDING.md` section 6
(blanket 2x is unsafe; see that doc's four reasons). One package serves 2x art to
the city-HUD windows the runtime scaling layer doubles ~~, and to nothing else~~.

**⚠ CORRECTED 2026-08-16 — "and to nothing else" stopped being true on 2026-07-23 and is badly false now.** Beside the reference-driven partition the builder stages a **code-bound** list that no `.UI` scan can see: `CODE_BOUND_TGIS` (`build_selective_safe.py:320-590`), staged at `:1779-1823`, reported at `:1825`. It is **299 TGIs, not 39** — `:320` opens a 39-entry literal and then appends five more blocks (`] + [` x5): 16 advice-row glyphs `0x14416250-0x1441625F` (`:522`), 68 news/advisor arts `0x140155B4-0x140155F7` (`:538`), 5 master-budget bands (`:552-554`), 59 HTML page backgrounds read from `html-image-refs.txt` (`:562-568`), and **the whole 112-entry 42x42 thumbnail group `0x4C06F888`** (`:585-589`).

Not all 299 ship — `:1779` drops three classes first (already covered by the scaled-`.UI` logic `:1782`, UNSCALED-only CONFLICT `:1785`, no 2x asset `:1789`). Measured against `refmap.csv`'s 431 referenced TGIs: **271 of the 299 have no `.UI` reference at all, and 249 of those ship a 2x PNG in this package** (verify in `stage\` and `package-list.txt`). Shipped, and plainly not city HUD: `0x14315E61` the screen-edge PAUSED alert border (`:376`), `0x14416327` the **region**-screen city-bubble AuraBar (`:405`), `0x14416244` the Audio Options playlist strip (`:412`), `0x53244588` the code-created restore-toolbars icon forced in place at its original TGI (`:418`, `:598-599`).

Nor is "bound by the exe" the whole story: the 59 `html-image-refs.txt` entries are reached by `sc4://image/<group>/<instance>` URLs inside LTEXT resources in SimCityLocale.DAT (`:556-561`), and group `0x4C06F888` is staged **wholesale** with no per-consumer proof, on the stated reasoning that "Staging the WHOLE group beats mining the property" (`:580-582`).

**"Selective" means selected by a hand-maintained consumer list — NOT "reachable only from a scaled `.UI` subtree". A TGI in this package can be drawn anywhere in the game.** That is the same trap the #148 note at the bottom of this file records: *"A `.UI` edit is scoped to that `.UI`. An ART edit is scoped to the whole game."*

---

## BUILDER CONTRACT as of 2026-07-29 (read before editing the generator)

The builder now emits **two** packages and has three deliberate exceptions to
its original "art and `imagerect` only" rule. ~~Current 2x output: **345 entries**~~
**CORRECTED 2026-08-16: current output is 655 entries at EVERY tier** (asserted by
`_tests\Test-DatIntegrity.ps1:145` / `:215` / `:217`;
`tools\selective-safe\package-list.txt:4` reads `index : 655 entries`).
All three tiers must be rebuilt together with `--factor 2`, `--factor 1.5`,
`--factor 3`.

**1. It still never edits `area=` … ~~except twice, both because the game reads
that geometry BEFORE any runtime sweep can run:~~
except in THREE PLACES, each for its own reason *(corrected 2026-08-16 — #170
partly survived because this line said "twice" and named one root, so nobody
looked in this builder for the advisor buttons' geometry)*:**

- `double_subtree_areas()` (`build_selective_safe.py:646`) — scales `area=` on
  every DESCENDANT of a named root (`kDataScaledSubtreeIds` in `UiSpike.cpp`
  makes that root **root-only** so the children are not scaled twice).
  ~~Used for the **advisor strip** `0x6A15C767`:~~
  *(corrected 2026-08-16)* Used for **TEN roots across five call sites**, not
  one: advisor strip `0x6A15C767` (`:1963`); Monthly Budget `0xAA3AC002`,
  `0xCA4C332D`, `0xAA3AC001`, `0xAA3AC000` (`:2011`); Graphs `0x8A8B5B71`,
  `0x8A8B5B72`, `0x0A4A8176` (`:2035`); U-Drive-It dashboard `0x4BCB938A`
  (`:2057`); console variant `0xEC1A5CBF` (`:2082`).
  ⛔ **EVERY ONE OF THOSE ROOTS IS IN `kDataScaledSubtreeIds`, so
  `ScalePanelRoot` RETURNS before the child loop (`src\UiSpike.cpp:14557`).
  The runtime sweep NEVER walks these children and nothing downstream repairs a
  number written here.** If a control under one of these roots is the wrong
  size, THIS BUILDER is the suspect — not `ScaleSubtree`, not the strip-button
  class in `UiSpike.cpp`.
  Since #170 (2026-08-16) an ART LEAF under these roots is sized as a LENGTH,
  not by its edges — no children + `image={g,i}` + no `imagerect` →
  `nl + scale_fn(r-l)` (`:739-751`); #148's leaf rule, previously only in
  `ScaleSubtree` and `build_dialog_static.py`. Provable no-op at integer
  factors, and the build FATALs if it ever is not (`:757-759`).
  The advisor strip's own numbers are unchanged: its seven faces are live 3D
  head renders whose framing is fixed when the game BINDS each head during city
  load, so runtime doubling was always too late (quarter-zoomed faces).
  19 edits per script — re-counted 2026-08-16, 20 descendant tags minus the one
  skipped `0x0000AAAA` marker, in both `I-cbc905cd` and `I-4a160034`.
  **VERIFIED EXACT:** every child's live 2x geometry equals 2 × its design
  area, checked 16/16 against a live dump.
- `seat_faces_on_apertures()` (`:864`, called `:1976`) — #152, added
  2026-08-14, missing from this contract until 2026-08-16. **Not a scale: a
  TRANSLATE.** It seats the 7 advisor faces on their frame's MEASURED art
  aperture, because `double_subtree_areas` rounds a face and its frame
  independently and their odd 1x offset of `(2,1)` does not survive f=1.5.
  Width and height are never touched, the delta is capped at 1px (guard G5,
  `:919-921`), and a move at an integer factor STOPS THE BUILD (`:1986-1990`) —
  so it writes at 1.5x only: 7 windows per script, 14 across the two advisor
  scripts, and nothing else in the 330-script corpus.
- The **ticker marquee** `0xAA12F33C` design width, because the game re-imposes
  its init-cached geometry every roll tick and undoes any runtime `SetW`.
  Width only — `l`, `t` and `b` pass through unchanged (`:1940`) — inline
  `re.subn` at `:1942`, scoped to `_I-2a2aed99.ui` (`:1937`), asserted to match
  exactly once (`:1945`). ⚠ It is **not** `double_one_window_area()`: that
  function (`:931`) and `parity_nudge_btn_areas()` (`:1241`) both still contain
  `area=` writes but have **ZERO call sites** — #89's single-window doubling was
  reverted in v2.41.3 (`:2109-2121`) and the #148 parity nudge was reverted the
  day it shipped (`:2122-2126`). Grepping for `area=` in this file finds five
  writers; only three of them run.

  **IT SKIPS ALIGNMENT MARKERS (`id=0x0000AAAA`) — never remove that.** The
  game positions a panel at `anchor − markerOffset` in NATIVE units, so
  doubling a marker displaced the whole Advisors box by exactly `−(229,63)`.
  That was a shipped regression; the skip is the fix.

**2. Third-party overrides** (`thirdparty-ui\` + `thirdparty-art\` → the
separate `zzz-SC4UIScale\z_SC4UIScale_ThirdPartyUI-<tier>.dat`). A plugin can
replace a stock `.UI` script and/or its art wholesale, and by the LOAD-ORDER
LAW (root loads before subfolders) our root package can never win. Inputs are
**the MOD's own** files — never the stock ones (different dimensions, and using
stock silently reverts the mod's features). Art is upscaled with the project
`Upscale2x.exe` at the build factor. **Re-extract these inputs after any
update to the mod or we ship a stale layout.**

**3. `fresh_dir()` instead of `shutil.rmtree`** for staging dirs — these live
under OneDrive, which holds a handle on the folder, so rmtree deletes the files
and then dies with `WinError 5` on the rmdir.

Full mechanism + per-fix trap signatures: `_tests\REGRESSION.md`.
Scenario axes this package is sensitive to: `_tests\SCENARIOS.md`.

## What the runtime scales (set S)

The runtime layer doubles these window IDs + their subtrees:

    0xE9889775  0x6A64E3C0  0xCA2AEDC0  0x0987B48F  0x69E40A1F  0xEA8CAD14
    0x6A15C767  0xAA3AC000  0xABC619D2  0x0A4A8176  0x8A8B5B71  0xC98F49F1
    0x699306ED  0xCA35CBED  0x0A78827A

~~All 15 IDs were located as `id=0x...` window definitions in the extracted .UI
scripts (no guessing was needed). They resolve to **23 .UI files** — 18 in the
default-layout group G-96A006B0 plus all 5 of their 800x600 twins in G-08000600
(the engine picks the group by screen resolution, so both must ship edited):~~

⚠ **CORRECTED 2026-08-16 — THE ID LIST ABOVE AND THE TABLE BELOW ARE THE
2026-07-21 SNAPSHOT, NOT THE CURRENT PARTITION.** `SCALED_WINDOW_IDS` now holds
**51 ids** (`build_selective_safe.py:102-281`, 51 distinct, no duplicates) and
the package ships **89 edited `.UI` scripts — 79 in G-96A006B0 + 10 in
G-08000600** (`package-list.txt`, 89 rows of TypeID `0x00000000`; `stage\`,
`stage-15x\` and `stage-3x\` each hold the same 89). The group rule is unchanged
and still governs: the engine picks the group by screen resolution, so both must
ship edited.

The 36 ids added since this snapshot: the god-mode toolbar cluster `0xC991EDA8`/
`0x49923239` (:118) · nine region-screen panels (:121-122) · the news reader
`0xAA231508` (:139) · **four** mayor-mode flyouts `0x69923479`/`0xC99237A0`/
`0xE992F711`/`0x0992FD17` (:152-155 — the other two members of that family,
`0x49923239` Landscape and `0x699306ED` Civic, were already listed) · the three
budget siblings `0xAA3AC001`/`0xAA3AC002`/`0xCA4C332D` (:172-174) · the two
advisor briefing panels `0xAA15EF06`/`0x2A1D96B1` (:185-186) · Data Views
`0xAA32BCE6` (:205) · both U-Drive-It consoles `0x4BCB938A`/`0xEC1A5CBF`
(:215, :228) · eight My Sims roots (:239-255) · the Graphs middle root
`0x8A8B5B72` (:267) · the Sim-mode sidebar `0xABB26B0E` (:268) · the two
tool-flyout columns `0x8BB27C12`/`0xAB954023` (:279-280). 15 + 36 = 51.

**DISCOVER the list, do not read it here** — `SCALED_WINDOW_IDS` at
`build_selective_safe.py:102` is the only authority. Most of the later additions
carry their own dated rationale comment; the original 15 at :103-106 do not.

Keep the table below as history: its 15→23 arithmetic is still correct **for
those 15 ids** (re-verified 2026-08-16 against `tools\uiscripts\extracted`, 330
scripts: 18 in G-96A006B0 + 5 in G-08000600). What is no longer true is the
"23 shipped scripts" total quoted beneath it.

| Instance | Groups | Root window | What it is | Retargets | Rect x2 |
|----------|--------|-------------|------------|----------:|--------:|
| 2bc90671 | 96A006B0 + 08000600 | 0xE9889775 (+0x69E40A1F) | main city toolbar/status bar, variant A | 8 / 9 | 11 / 9 |
| 898897de | 96A006B0 + 08000600 | 0xE9889775 (+0x69E40A1F) | main city toolbar (City Funds, Mayor Rating, RCI), variant B | 8 / 9 | 10 / 9 |
| 0a5fa5d6 | 96A006B0 | 0x6A64E3C0 | City Opinion Polls panel, variant A | 0 | 9 |
| 4bc906b5 | 96A006B0 | 0x6A64E3C0 | City Opinion Polls panel, variant B | 0 | 7 |
| 2a2aed99 | 96A006B0 + 08000600 | 0xCA2AEDC0 | news ticker | 1 / 1 | 1 / 1 |
| c973b411 | 96A006B0 + 08000600 | 0x0987B48F (+0xEA8CAD14) | top-left city status panel (name, date, funds, mode + speed buttons) | 5 / 5 | 8 / 8 |
| 4a160034 | 96A006B0 | 0x6A15C767 | Advisors panel, variant A | 2 | 3 |
| cbc905cd | 96A006B0 | 0x6A15C767 | Advisors panel, variant B | 2 | 3 |
| aa3acdfe | 96A006B0 | 0xAA3AC000 subtree ONLY | budget quick panel (file holds 4 top-level windows; see below) | 11 | 5 |
| cbc3c2b9 | 96A006B0 | 0xAA3AC000 subtree ONLY | budget quick panel, variant (same caveat) | 10 | 5 |
| 6bc61f19 | 96A006B0 | 0xABC619D2 | Building Style Control | 7 | 7 |
| 6bc9065a | 96A006B0 | 0x8A8B5B71 (+0x0A4A8176) | graphs/data-view panel, variant A | 23 | 5 |
| ea2871aa | 96A006B0 | 0x8A8B5B71 (+0x0A4A8176) | graphs/data-view panel, variant B | 43 | 5 |
| 49889894 | 96A006B0 | 0xC98F49F1 | options menu (Audio/Graphics/Play, Exit to Region) | 1 | 0 |
| c9930681 | 96A006B0 + 08000600 | 0x699306ED | Mayor-mode build toolbar | 0 / 0 | 1 / 1 |
| aa356502 | 96A006B0 | 0xCA35CBED | day/night control toolbar | 0 | 1 |
| aaa44448 | 96A006B0 | 0xCA35CBED | God-mode terrain tools toolbar | 0 | 1 |
| aa53e3ea | 96A006B0 | 0x0A78827A | God-mode tools panel (disasters, obliterate, day/night) | 4 | 1 |

("x / y" = default-group file / 08000600 twin. Totals: 149 ref retargets, 111
imagerect doublings across the 23 shipped scripts.)

**Partial-file caveat**: `aa3acdfe` and `cbc3c2b9` each contain FOUR top-level
windows (0xAA3AC000, 0xAA3AC001, 0xAA3AC002, 0xCA4C332D). Only 0xAA3AC000 is in
the runtime's scaled list, so edits are confined to its subtree (verified by
line-range check); the sibling windows keep 1x refs. If the runtime ever scales
0xAA3AC001 / 0xAA3AC002 / 0xCA4C332D too, add them to `SCALED_WINDOW_IDS` in the
build script and rebuild.

## Ref map (refmap.csv)

All 281 layout scripts parsed (271 G-96A006B0 + 10 G-08000600; the font-config
and the 48 binary G-8A5971C5 payloads carry no image refs). Every `image={gid,iid}`
occurrence (2,962 total — matches the research census) was classified by whether
it sits inside a scaled subtree:

| Classification | Refs | Meaning | Action |
|---------------|-----:|---------|--------|
| EXCLUSIVE | ~~93~~ **305** | referenced ONLY from scaled subtrees | 2x PNG shipped at the ORIGINAL TGI (in-place override) |
| SHARED | ~~30~~ **12** | referenced from scaled subtrees AND elsewhere | 2x clone at a NEW instance ID; scaled-subtree refs retargeted |
| UNSCALED-only | ~~308~~ **114** | never referenced from a scaled subtree | untouched |
| **Total** | **431** | matches UI-ART-BINDING.md's census exactly | |

**⚠ AMENDED 2026-08-16 — the split moved; the total did not.** Re-counted off
the builder's own `refmap.csv` (431 data rows, column `classification`:
EXCLUSIVE 305, SHARED 12, UNSCALED 114 — the CSV writes the bare label
`UNSCALED`, this table's "-only" suffix is prose). The cause is
`SCALED_WINDOW_IDS` growing from the 15 ids listed in "What the runtime scales"
above to **51** (`build_selective_safe.py:102`); `mark_scaled()` at
`build_selective_safe.py:1080-1091` marks each of those windows' WHOLE SUBTREE,
so refs migrate UNSCALED -> EXCLUSIVE, and SHARED shrinks because the "and
elsewhere" half of a shared ref is now itself inside the scaled set. The
93/30/308 figures belong to the 2026-07-21 build named at the top of this file.
`refmap.csv` is rewritten on every run (`build_selective_safe.py:2161`; see
"Rebuild" below), so it — not this table — is what a rebuild is checked against.
Re-verified unchanged: the Action column (all 305 EXCLUSIVE `2x-in-place`, all
12 SHARED `clone+retarget`, all 114 UNSCALED `untouched`), the 431 total, and
the 2,962 occurrence count in the paragraph above.

- Every EXCLUSIVE and SHARED ref had a 2x asset in `upscale\preview\SimCity_1`
  (0 left at 1x), and every staged PNG was verified exactly 2x its 1x original
  (IHDR width/height check, 123/123 pass).
- The research doc's scariest shared art — the universal 180x180 dialog chrome
  (14416240, 144161EE) and the standard dialog button strip (144161EB) — turned
  out to be UNSCALED-only: no scaled window references them, so they are untouched
  and the doc's open question O1 (button-strip vertical stretch) is **bypassed
  entirely**: no shared strip is ever 2x'd in place anywhere.
- `refmap.csv` columns: TGI, classification, occurrence count, referencing file
  lists (scaled/unscaled), 2x availability, action, clone TGI.

## The IID clone scheme (SHARED set)

    clone GroupID    = original GroupID   (a ref's GID is honored — research doc §2)
    clone InstanceID = original InstanceID XOR 0x53430001
                       ("SC" = 0x5343, +0x0001 marker in the low bits)

XOR is self-inverse (audit: XOR a clone IID with 0x53430001 to recover the
original) and preserves uniqueness. Collision checks performed at build time, all
clean: clone TGIs vs the full 2,280-entry PNG store, vs all 431 referenced TGIs,
vs the 93 in-place override TGIs, and vs each other. All 30 shared refs are in
group 0x46A006B0. Example: `{46a006b0,14416241}` -> `{46a006b0,47026240}`.

Unscaled screens keep the ORIGINAL TGIs (stock 1x art, byte-untouched), so the
region view, loading screens, dialogs and menus render exactly as shipped.

## imagerect doubling

`imagerect=(l,t,r,b)` is in **bitmap pixel coordinates** (LTRB, proven in the
research doc) — both the 9-slice inset spec (`edgeimage=yes`) and the source-crop
form. Whenever a control's art went 2x (in-place exclusive OR retargeted clone),
its `imagerect` values were doubled in the shipped script: 111 controls.
No other bitmap-space pixel attribute exists in these scripts (`gutters`,
`textoffsets`, `tipoffsets`, `area` are window-layout space — the runtime layer's
domain). **Division of labor: the runtime doubles layout (`area` etc.) and must
NOT double `imagerect` for these windows — the shipped .UI already carries
doubled rects.**

## Package contents (~~146 entries, 2,185,737 bytes~~ **655 entries, 11,712,063 bytes**)

> Re-measured 2026-08-16: `package-list.txt:1` (`(11712063 bytes)`) and `:4`
> (`index : 655 entries`); asserted by `_tests\Test-DatIntegrity.ps1:145`
> (`z_SC4UIScale_SelectiveArt-2x.dat`, `entries = 655`). The 146/93/30/23 figures
> were a 2026-07-21 snapshot. **Read these counts off `package-list.txt`, never
> from here.**

| Content | Type | Entries |
|---------|------|--------:|
| 2x PNGs at original TGIs (EXCLUSIVE set) | 0x856DDBAC | ~~93~~ **305** |
| 2x PNG clones at XOR'd instance IDs (SHARED set) | 0x856DDBAC | ~~30~~ **12** |
| 2x PNGs for CODE-BOUND art (no .UI referrer) | 0x856DDBAC | **249** |
| Edited .UI scripts at ORIGINAL TGIs | 0x00000000 | ~~23~~ **89** |

> **The code-bound row is new, not a re-split of the first two** (2026-08-16).
> 305 = `refmap.csv` rows with `action=2x-in-place`; 12 = rows with
> `action=clone+retarget`; the remaining 566 − 305 − 12 = 249 staged PNGs match
> neither (139 in group `0x46A006B0`, 110 in group `0x4C06F888`). They come from
> `CODE_BOUND_TGIS` (`build_selective_safe.py:320`), which concatenates a literal
> TGI list, every line of `html-image-refs.txt`, and **the entire 0x4C06F888
> thumbnail group** read out of `..\dbpf\extracted-png-tgi.csv`
> (`build_selective_safe.py:585-589`); staged at `build_selective_safe.py:1817/1821`.
> The clone scheme itself is unchanged: `CLONE_XOR = 0x53430001`
> (`build_selective_safe.py:99`).

Same-TGI .UI overrides from Plugins are proven community practice (Raise the UI
Mod ships exactly this way — research doc §5). `DbpfPack.exe --list` verified:
~~146 entries~~ **655 entries**, DBPF 1.0 / index 7.0, no DIR record
(uncompressed, like the game's own art). Full listing: `package-list.txt`.
(2026-08-16: `package-list.txt:2` still reads `version : DBPF 1.0   index 7.0`
and `:6` `DIR     : compression directory absent (all uncompressed)` — only the
entry count moved.)

## Verification performed

(2026-08-16: the CHECKS below are still the right checks; only the numbers
moved — all re-measured from `package-list.txt` + a file count of `stage\`.)

1. `--list` entry count == staged file count (~~146 == 146~~ **655 == 655**).
2. All ~~123~~ **566** staged PNGs exactly 2x their 1x originals (IHDR check).
3. Independent re-parse of all ~~23~~ **89** shipped scripts vs originals: 1,028 controls
   compared — every scaled-subtree shared ref retargeted to the correct clone,
   every doubled-art control's imagerect exactly doubled, zero clone refs in
   unscaled subtrees, zero unexpected byte changes. 0 violations.
   ⚠ the 1,028-control figure is **UNVERIFIED** — it is not recorded in any
   artifact readable at correction time; leave it until a build log is captured.
4. Edits in the two multi-window files confined to the 0xAA3AC000 subtree
   (diff line ranges vs top-level window positions).

## Deployment

Copy the package to the game's plugins folder (do NOT touch the install dir):

    copy "z_SC4UIScale_SelectiveArt.dat" "%USERPROFILE%\Documents\SimCity 4\Plugins\"

- Load order: plugins load after SimCity_1.dat, later-alphabetical wins per TGI;
  the `z_` prefix sorts late. Deploy INSTEAD of the blanket per-group packages in
  `tools\selective\` (those 2x whole groups and are unsafe for unscaled screens).
- Requires the runtime scaling layer to be active for the windows above —
  without it the city HUD draws 2x art into 1x windows. Conversely the package is
  exactly what the runtime needs: it should double layout only, not imagerect.
- Revert: delete the .dat from Plugins. Nothing else is modified anywhere.

## Rebuild

    python build_selective_safe.py

Idempotent; re-stages into `stage\`, rewrites `refmap.csv`, `package-list.txt`
and the .dat. Inputs: `uiscripts\extracted` (331 files), `upscale\preview\SimCity_1`
(2,206 2x PNGs), `dbpf\extracted-png-tgi.csv`, `dbpf\DbpfPack.exe`.

## Known risks / open items

- The scaled-window ID list is the runtime layer's; if more windows are added to
  the runtime's scaling set later (e.g. query panels, the budget siblings above),
  the partition MUST be recomputed — a newly scaled window that references
  original TGIs would draw 1x art, and any of its refs currently classed
  EXCLUSIVE-elsewhere could silently flip to SHARED.
- Art bound outside .UI scripts (exemplar ItemIcons, loading screens; 1,849 PNGs)
  is untouched by design and will render 1x inside scaled windows if any such
  window draws exemplar-bound icons (e.g. menu ItemIcons hosted in scaled
  toolbars). That binding path needs its own research pass.
- The 08000600 twins exist for only 5 of the 18 windows; at 800x600 the other 13
  windows use the default-group scripts (already covered).

---

## 2026-08-06 — TWO BUILDER STAGES ADDED AND REVERTED THE SAME DAY (#148)

Both are still in `build_selective_safe.py` as **documented dead code with the
call sites removed**. Read them before proposing anything similar.

### `parity_nudge_btn_areas` — moved a button onto an even edge

Correct diagnosis: `ScaleSubtree` is edge-derived, so at f=1.5 an odd `l` costs
the window one pixel against a 71px art cell. Moving the button to an even `l`
fixes it. 177 buttons across 29 scripts.

**Reverted:** the nudge is up to 2px at 1.5x. Invisible on the Landscape flyout
(5 buttons, 50px apart); a visible misalignment in `aa1f1f57` (21 faces, and the
most-nudged script at 24+28). Also hit the advisors, the budget rows, the dock.

> **A fix that MOVES things is judged by its densest neighbourhood.**

### `fit_state_strips_to_windows` — regenerated sheets at `states * window`

Correct diagnosis: `ScaleDim`'s `CellUnit` is a guess (LCM of every count that
divides the width — a 136px FOUR-state sheet snaps on 8; it snaps heights too,
which a horizontal strip never needs). 61 sheets rebuilt from the pristine 1x
source. Offline mismatch count went to 0 at every tier.

**Reverted:** it broke the disaster flyout thumbnails on hover.

> ⛔ **THE FLYOUT STRIP ITEMS ARE CREATED AT RUNTIME AND APPEAR IN NO `.UI`.**
> They bind art **by TGI**. The conflict check could only enumerate `.UI`
> consumers, so it reported 0 conflicts and was wrong.
>
> **A `.UI` edit is scoped to that `.UI`. An ART edit is scoped to the whole
> game.** To reinstate, first answer: *how does the builder enumerate the
> RUNTIME consumers of a TGI?* Until that instrument exists, any art-dimension
> change is unbounded.

(Also measured and refuted: "a stale `imagerect` elsewhere still describes the
old sheet size" — of 115 art-sized strips in scope, **zero** carry an
`imagerect`.)

### Where the fix actually lives

~~`src\UiSpike.cpp`, in `ScaleSubtree`: a **leaf** window (`GetChildCount() == 0`)
takes its scaled size **size-derived**, `ScaleRound(w, f)`. Nothing moves.~~

**CORRECTED 2026-08-16 (#170): that is true of `ScaleSubtree`, but it is not the
whole answer — and `ScaleSubtree` is the one copy that CANNOT REACH THIS
BUILDER'S OWN SUBTREES. The leaf rule lives in THREE places:**

1. `src\UiSpike.cpp:17327` (rationale from `:17296`) — `ScaleSubtree`, for
   windows the runtime sweep actually walks. Predicate there is just
   `GetChildCount() == 0`.
2. `tools\dialog-static\build_dialog_static.py:748` — `leaf_art_sized`, since
   #155, because statically-served dialogs are excluded from the sweep.
3. `tools\selective-safe\build_selective_safe.py:704-762` — inside
   `double_subtree_areas` (`:646`), since #170. **This is the one this document
   is about.**

A pre-scaled subtree root is listed in `kDataScaledSubtreeIds`
(`src\UiSpike.cpp:5373-5374`; the advisor strip `0x6A15C767` is the first
entry), and `ScalePanelRoot` **returns on that test before it reaches the child
loop** (`src\UiSpike.cpp:14570-14573`; the loop is at `:14579`). That test is
called from exactly one site in the codebase, so nothing downstream repairs a
coordinate this builder writes. That is why the seven advisor buttons — named as
nudge victims two paragraphs above — shipped an 82px window against an 83px art
cell at 1.5x from v2.94.1 (2026-08-06) until #170 landed on 2026-08-16, with the
`ScaleSubtree` rule live that whole time.

SCOPE of the builder rule (the #155 predicate, deliberately not "every leaf"):
no children, an `image={g,i}`, and no `imagerect`
(`build_selective_safe.py:738-741`). Position never moves; only the extent, by
at most one pixel. Provable no-op at an integer factor and asserted as one — the
build aborts if it changes any area at 2x/3x
(`build_selective_safe.py:758-761`).

⚠ Stale cross-reference to expect while reading the builder:
`build_selective_safe.py:719` cites this guard as "UiSpike.cpp:14557". It is at
`:14570` today.

Containers keep edge-derived rounding so #143's white seams cannot return.
