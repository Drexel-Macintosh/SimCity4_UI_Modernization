# Package manifest

The complete set of DBPF packages that make up an SC4UIScale install: what
each package contains, how the tier system arms them, and the dependency
gates that keep third-party overrides honest.

For the product overview see [../README.md](../README.md); for the runtime
half of the stack see [HOW-IT-WORKS.md](HOW-IT-WORKS.md).

> **Installing?** Grab the ready-built bundle from
> [Releases](../../releases) — the repository itself ships the *generators*,
> not the artwork. See [Building the packages](#building-the-packages).

**Authority.** Entry counts below are asserted by `_tests\Test-DatIntegrity.ps1`
(its `$EXPECTED` table), which checks every *deployed* package and is updated
deliberately whenever a count changes. That script is the source of truth;
this file describes it. Byte sizes are indicative only — nothing asserts
them, so measure the file before quoting one. (`DbpfPack` output is
non-deterministic: to prove a package unchanged, compare per-entry payloads,
never the file hash — a DBPF header carries a build timestamp.)

**Which tier is armed, and why a package is off, are NOT in this file and NOT
in a directory listing** — since v4.5.0 they live only in
`z_SC4UIScale_STATE.txt`. `_tests\Verify-Arming.ps1` is the after-a-boot check
for the arming layout itself.

---

## The tier system

`ScaleTier::Decide` picks the factor from the **render** resolution and arms
the matching package set.

- **Render resolution is not the requested resolution.** DirectX +
  Fullscreen/Borderless renders at the monitor's native mode (the wrapper
  ignores the request); DirectX + Windowed and Software use the requested
  size.
- **Tier 1 = true stock**: every scaling subsystem off, every package holding
  its inert `.off` content, FontStyle moved aside — the DLL is
  indistinguishable from a no-DLL install (isolation-tested).
- **All tiers carry identical entry counts and TGIs**; only pixel dimensions
  and layout coordinates differ.

---

## The arming layout (v4.5.0) — a content swap at a stable filename

Through v4.4.0 arming was a **rename**: the winning tier kept
`z_SC4UIScale_<Pkg>-<tag>.dat` and the losing tiers were pushed aside as
`….dat.x1-disabled`. That is the single reason a package manager cannot
uninstall this mod — sc4pac removes files **by manifest name**, and 53 of 68
installed files sat under a renamed name. From v4.5.0 nothing of ours is ever
renamed. Three file classes, and only the first is ever loaded:

| Class | Name | What it is |
|---|---|---|
| **LIVE** | `z_SC4UIScale_<Pkg>.dat` | The only thing SC4 loads. Exactly one per package. Its **content** changes; the **name never does** — not at any tier, not under any gate verdict, ever. |
| **PAYLOAD** | `z_SC4UIScale_<Pkg>.<tag>.uipay` | Inert. Never renamed, never loaded, never written by the DLL. `<tag>` is `15x` / `2x` / `3x` (tiers), `1x` / `on` (inverse-gated), or `off`. |
| **STATE** | `z_SC4UIScale_STATE.txt` | One per folder of ours, rewritten every boot. The only place the armed tier and the gate verdict now exist — see below. |

`ScaleTier::ArmOne` copies the chosen payload over the live name (staged to
`.dat.tmp`, then `MoveFileEx`, so it is atomic and **fails inert** rather than
mixed). `ScaleTier::CommitArming` runs the whole set in one pass at DLL load,
during the plugin scan — the same moment the rename used to run.
`ScaleTier::MigrateRenamesToPayloads` upgrades a pre-4.5.0 install in place, so
an existing player needs no download.

**Why `.uipay` is safe — measured, not assumed.** Probe #202 copied a real DBPF
to `.uipay`, booted, and it did **not** appear in the registered-segment census
while **13 of our live `.dat` files did, in the same census**. That second half
is the positive control: the census demonstrably could have seen it. The plugin
scan is extension-gated. (`.dat.x1-disabled` being skipped only ever proved
that *one* string is skipped; this proves it for the string the layout now
rests on.)

**The `.off` package.** A package that is gated off — wrong tier, or a
dependency gate refused it — is not an absent file. It is the same live `.dat`
holding the `.off` payload: a **one-entry DBPF that contests nothing**, whose
single TGI is verified absent from the installed-archive census before it is
built (`tools\payload\build_payloads.py`). It declares no contested TGI, so the
runner-up is promoted by the engine's own scan-order logic at index-build time —
which is what the rename bought by keeping the file off disk, and what closing
a segment afterwards could never produce.

### `z_SC4UIScale_STATE.txt` — the diagnosis a constant filename destroys

⛔ **A directory listing no longer carries the armed tier or the gate verdict.**
Every live filename is a constant and `off` looks exactly like `2x`. Written by
`ScaleTier::WriteArmState` into **each** of our folders on **every** boot; the
game never reads it and nothing gates on it. Two `#` header lines, then TSV:

```
# SC4UIScale arming state. Rewritten every boot; the game never reads it.
# base	tag	reason	paySize	payTime	liveSize	liveTime
z_SC4UIScale_SelectiveArt	3x	armed	73400320	133...	73400320	133...
z_SC4UIScale_NamIcons	off	dep ABSENT (NetworkAddonMod_Controller.dat)	4096	133...	4096	133...
```

| Column | Meaning |
|---|---|
| `base` | The package's **leaf** name — `SyncDat` strips the folder before recording it |
| `tag` | The armed payload tag, or `off` |
| `reason` | The gate verdict in the DLL's own words (`armed`, `dep ABSENT (x.dat)`, `dep CHANGED`, `PARTIAL`, …) |
| `paySize` / `payTime` | Stamp of the payload that was copied |
| `liveSize` / `liveTime` | Stamp of the live file **after** the copy |

The live stamp is what makes the steady state free (four file stats, zero I/O
when it matches) **and** self-healing: an installer or an sc4pac package update
that restores a shipped file changes its mtime, the stamp misses, and the next
boot re-arms. It is also a usable positive control from outside the DLL — a row
whose `liveSize`/`liveTime` disagree with the file it names is **stale**, and
any tier read from it is a statement about a different boot.

**Every script that needs the armed tier or a gate verdict reads this file**
(`_tests\Verify-Arming.ps1`, `Test-ThirdPartyGates.ps1`,
`Toggle-SaveWarningUI.ps1`, `Toggle-BuildingStylesUI.ps1`,
`Set-StockCompare.ps1`). A check that infers "live" from a `.dat` existing is
measuring nothing — it is true for every package at every tier.

### Payload sets per package shape

`tools\payload\build_payloads.py` derives the shape from the source names **and
from the DLL's own `SyncDat` call sites**, never from a hand-written list:

| Shape | Payloads emitted | Packages |
|---|---|---|
| **Full tier set** | `15x`, `2x`, `3x`, `off` | `SelectiveArt`, `DialogStatic`, `ItemIcons`, `ItemIconsSub`, `ThirdPartyUI`, `WarriorUI`, `SaveWarningUI`, `CamUI`, `NamIcons`, `CsiIcons`, `UncoveredIcons`, the `ZCarbon*` family |
| **Inverse-gated** | `1x`/`on`, `off` | `SelectorUI` (armed by the **absence** of a tier), `WebText` (gated on the Web Button mod) |
| **Plain** | *none* — never armed | `MenuFix`, `CamGraphLabels` |

⚠ The inverse row is derived from `ScaleTier.cpp`, not from the filename,
because the filesystem cannot tell "never armed" from "armed by on/off": both
look like a bare untagged `.dat`. Getting it wrong is silent and total —
`WebText` was classified tier-independent, nothing built it a payload, and
`ArmOne` logged *"NO PAYLOAD AT ALL … leaving it exactly as found"* while its
inverse gate never fired (found 2026-08-29, alongside the same failure in
`SelectorUI` — two instances of one class, which is why it is derived now).

### Pre-4.5.0 filename tag convention (still in the sources and the builders)

The tier tag goes in the base name, immediately before the extension. The
**generators still emit these names**, and `Convert-ToPayloadLayout.ps1` turns
them into payloads — so the convention is not dead, it just no longer reaches
an installed tree:

| Factor | Tag | Generator output | Becomes |
|---|---|---|---|
| 1.5× | `-15x` | `z_SC4UIScale_SelectiveArt-15x.dat`, `FontStyle-15x.ini` | `z_SC4UIScale_SelectiveArt.15x.uipay` |
| 2× | `-2x` | `z_SC4UIScale_SelectiveArt-2x.dat` | `z_SC4UIScale_SelectiveArt.2x.uipay` |
| 3× | `-3x` | `z_SC4UIScale_SelectiveArt-3x.dat`, `FontStyle-3x.ini` | `z_SC4UIScale_SelectiveArt.3x.uipay` |

It governs all tier-paired bases: `SelectiveArt`, `DialogStatic`, `ItemIcons`,
`ItemIconsSub`, `ThirdPartyUI`, `WarriorUI`, `SaveWarningUI`, `CamUI`,
`NamIcons`, `CsiIcons`, `UncoveredIcons`.

⚠ **`FontStyle.ini` is still managed by copy, not by payload.** It is not a
DBPF and the game probes it by path, so `ScaleTier::SyncFont` still copies
`FontStyle-<tag>.ini` over the probed `FontStyle.ini` and still moves it aside
at the stock tier. Fonts are the one part of the static layer the `.uipay`
story does not cover.

### Fonts

`FontStyle.ini` — all **88** stock styles at the tier's point sizes, plus two
stock-size `*Html` clone styles that exist only as HTML size-index sources,
so the file on disk holds **90** lines. Whole-file replacement, not a merge —
every style must be present. The game probes `<install>\Plugins\`, then the
install root, then falls back to the DBPF copy (proven by disassembly).
`FontStyle-<tag>.ini` ships per tier; `ScaleTier::SyncFont` copies the active
tier over the probed `FontStyle.ini` at boot. Note this reaches
`GZWinText`/button captions only — rich text goes through the HTML engine
instead (see [HOW-IT-WORKS.md](HOW-IT-WORKS.md)).

`z_SC4UIScale_FontStyle.ini` — an empty, inert marker file, present only so a
package manager (sc4pac) has something of ours to install and later delete.
The game never reads this exact name (only `<install>\Plugins\FontStyle.ini`,
which the DLL manages at runtime and is never shipped in the bundle — see
`_packaging\Build-Dist.ps1`'s `#182` comment). Branding it with the standard
`z_SC4UIScale_` prefix means a manual, by-hand removal of this mod catches it
the same way it catches every other package; a leftover live-named
`FontStyle.ini` with no DLL to manage it was the exact shape of the #182
crash.

---

## Package contents

> **Reading the names below.** They are written `z_SC4UIScale_<Pkg>-<tier>.dat`
> because that is what the **builders** produce and what the entry counts are
> asserted against. **On an installed v4.5.0 tree that file does not exist**:
> it is `z_SC4UIScale_<Pkg>.<tier>.uipay` beside a single live
> `z_SC4UIScale_<Pkg>.dat`. See [the arming layout](#the-arming-layout-v450--a-content-swap-at-a-stable-filename).

### Tier-paired packages (`010-SC4UIScale\` - v4.2.0 subfolder move; pre-4.2.0 these sat at the `Plugins\` root)

| Package | Entries | What it is |
|---|---|---|
| `z_SC4UIScale_SelectiveArt-<tier>.dat` | **696** | Enlarged art + edited `.UI` scripts for every runtime-scaled window. Exclusive art is replaced **in place**; art shared with things that must stay 1× is **cloned** at `IID XOR 0x53430001` and only the scaled consumer is retargeted; `imagerect` extents are doubled wherever the art doubled |
| `z_SC4UIScale_DialogStatic-<tier>.dat` | **265** | Fully statically-scaled dialogs (`area=` included) — the query/confirm/options family, which lives at main-window level and is never touched by the city sweep |
| `z_SC4UIScale_ItemIcons-<tier>.dat` | **356** | Toolbar/picker item icons, stock pool |

### Tier-paired packages (`zzz-SC4UIScale\` subfolder)

| Package | Entries | What it is |
|---|---|---|
| `z_SC4UIScale_ItemIconsSub-<tier>.dat` | **130** | Icons owned by other mods (submenus DLL + CAM/Maxis landmarks), drawn from each mod's own artwork. Not dependency-gated: entries are keyed to resource ids only those plugins introduce, so without the plugin they sit inert |
| `z_SC4UIScale_ThirdPartyUI-<tier>.dat` | 2 | A scaled copy of a **mod's own** `.UI` script + its own art, where the mod replaces a stock panel wholesale (CoriBoom 36-Slot Building Styles). Gated |
| `z_SC4UIScale_WarriorUI-<tier>.dat` | 4 | Same pattern for warrior's god-terraforming-in-mayor-mode scripts (mayor Landscape flyout + Signs & Labels column) plus the mod's own two art assets. Gated |
| `z_SC4UIScale_SaveWarningUI-<tier>.dat` | 2 | Same pattern for the two in-city quit/exit confirms, which the cyclone-boom save-warning mod replaces. Gated |
| `z_SC4UIScale_CamUI-<tier>.dat` | **22** | The six dialog-static targets CAM replaces, plus CAM's own three dialogs (city info / civic / school query) and their bitmaps: 9 scripts + 13 art. Gated |
| `z_SC4UIScale_NamIcons-<tier>.dat` | **392** | NAM's own ItemIcon strips, upscaled from NAM's own bitmaps, never a stock lookalike. Gated on `NetworkAddonMod_Controller.dat`, presence only, no size check |
| `z_SC4UIScale_CsiIcons-<tier>.dat` | 16 | U-Drive-It offer-balloon icons (City Situation Indicators) |
| `z_SC4UIScale_UncoveredIcons-<tier>.dat` | *varies* | Icons a custom lot ships that no other package in this set covers. The count is however many the install has — the integrity test deliberately asserts no number for it, and the package is simply absent when nothing is uncovered |

### Untagged packages (no tier triple — but not all of them are "always on")

| Package | Entries | What it is |
|---|---|---|
| `z_SC4UIScale_MenuFix.dat` | 6 | Exemplar patches fixing CAM 4.0.1's broken submenu parents. Reported by the integrity test, not entry-asserted |
| `z_SC4UIScale_WebText.dat` | 3 | LTEXT overrides that name Simtropolis, matching the DLL's redirect of the dead `simcity.ea.com` link. Active at every *tier*, but **inverse-gated** on the Web Button mod — ships `.on.uipay` + `.off.uipay` |
| `zzz-SC4UIScale\z_SC4UIScale_CamGraphLabels.dat` | 1 | The one LTEXT (`0xFF5D2E9F`) CAM's Power/Water charts ask for and no installed archive provides. Inert without CAM by construction — nothing except CAM binds the instance. Never armed, no payloads |
| `zzz-SC4UIScale\z_SC4UIScale_SelectorUI-1x.dat` *(built)* → `…SelectorUI.dat` + `.1x`/`.off` payloads *(installed)* | 1 | The scale selector's own dialog at the stock tier — the Graphic Options script and nothing else. One entry by design: the stock tier must never ship scaled art. The ONE package armed by the **absence** of a tier, which is why it is the only thing keeping 1x from being a one-way door — and why a payload sweep written against `{15x,2x,3x}` would have silently dropped it |

A string has no geometry, so none of these carry a tier triple. They divide
two ways, and the difference is invisible on disk — both are a bare untagged
`.dat`:

- `MenuFix` and `CamGraphLabels` are **never armed**. No payload is built for
  them; their `.dat` is already a stable name sc4pac can remove.
- `WebText` and `SelectorUI` are **inverse-gated** — armed with `on`/`off`
  rather than a tier — so they *do* get payloads and *do* appear in
  `z_SC4UIScale_STATE.txt`. Which group a package is in is derived from
  `ScaleTier.cpp`'s `SyncDat` call sites, never from its filename; see the
  warning under [payload sets per package shape](#payload-sets-per-package-shape).

---

## Dependency gates

Five packages contain copies of *another mod's* data and are gated by
`ScaleTier` (`kThirdPartyDeps`) on that mod still being installed:

| Package | Gate |
|---|---|
| `SaveWarningUI` | exact name + size of the mod's dat (the scaled copy hard-codes the mod's exact rects, so a mod update must disable it) |
| `CamUI` | both `CAM_Extended_Essentials.dat` and `CAM_Intro.dat`, exact size (the six replaced scripts come from two of CAM's dats; a half-present set would be half stale) |
| `ThirdPartyUI` | presence of the mod's package by name prefix (the scaled copy supplies art for a panel the runtime sweep scales, so only the mod-gone case is unambiguously wrong) |
| `WarriorUI` | exact name + size of both mod dats |
| `NamIcons` | presence of `NetworkAddonMod_Controller.dat`, no size check (pure art at the mod's own TGIs; a NAM update leaves the icons stale-looking, never mis-geometried, so a size check would disable 392 good icons on every patch) |

Without these gates, uninstalling a mod would not uninstall the scaled copy of
its data: that copy sits in `zzz-` and outranks everything, so the mod's UI
would stay on screen. "NOT FOUND (live or gated)" from the integrity test
while the mod is absent is correct behaviour, not a regression.

⛔ **Since v4.5.0 a closed gate is not an absent file.** The gated package is
its normal live `z_SC4UIScale_<Pkg>.dat`, holding the `.off` payload's bytes:
byte-different and TGI-empty, but **name-identical** to an armed one. So
`Test-Path` cannot answer "did the gate fire?" for any package, and the verdict
is read from the `reason` column of `z_SC4UIScale_STATE.txt` — where the DLL
writes it in its own words (`dep ABSENT (CAM_Intro.dat)`, `dep CHANGED`, …).
`_tests\Test-ThirdPartyGates.ps1` does exactly that, and **refuses** rather
than reporting a verdict when the state file is missing or its stamps do not
match the files they name.

**Any new package built from another mod's data needs its dependency row in
the same change.** Reproduce the load order with
`python tools\dbpf\who_owns_tgi.py <instance...>`.

### Load-order law

Files in the `Plugins` **root load before subfolders**; subfolders load
alphabetically, later wins. Overriding another mod requires a folder that
sorts after it (`zzz-SC4UIScale\` beats `150-mods\`); deliberately LOSING
to a mod requires sorting before it - which is why the main packages live
in `010-SC4UIScale\` (v4.2.0): `010-` < `050-load-first\` < `150-mods\`,
so CAM, the 36-style mod and their kin keep beating our stock-derived
copies exactly as they did when we sat at the root. A plugin
may replace a stock **script**, its **art**, or both — check for both, and
build the override from **the mod's** files, never the stock ones.
Recognition rule: if a panel's live window count or root size does not match
the stock script you are reading, a plugin has replaced it.

---

## Deployment map

⛔ **The `-<tier>` names below are what the BUILDERS emit and what the deploy
copies. They are not what an installed tree contains.** Both
`_tests\Deploy-OnGameClose.ps1` and `_packaging\Build-Dist.ps1` still write the
tier-tagged layout they always did, and both then call
`_tests\Convert-ToPayloadLayout.ps1`, which turns whatever it finds into
payloads plus one seeded live file per package. (One conversion, two callers,
nothing to drift: Build-Dist derives most of its file list by regex-parsing
Deploy's `Copy-Item` lines, but ~30 are invisible to that regex and are
compensated by hardcoded blocks — converting the copy lines instead would have
shipped payloads *and* tier-tagged live dats side by side, i.e. two live
providers for every TGI, with an identical file count and nothing going red.)

| File (as built / deployed) | Source in this project | Destination |
|---|---|---|
| `SC4UIScale.dll` | `build\Release\` | `Documents\SimCity 4\Plugins\` - the ROOT: the game only loads DLLs from the top level (measured, v4.2.0 maiden boot). The log and gcap live in `010-SC4UIScale\`; the ini sits at the ROOT beside the DLL (v4.5.0) |
| `SC4UIScale.ini` | **not shipped** (v4.5.0) - the DLL seeds it from `kStarterIni` on first launch; `_packaging\SC4UIScale.ini` is the commented reference copy | `Plugins\` - the ROOT, where every update and uninstall leaves it alone (a copy in the package folder dies on every sc4pac update; measured) |
| `z_SC4UIScale_SelectiveArt-<tier>.dat` | `tools\selective-safe\` / `tools\packages\<tag>\` | `Plugins\010-SC4UIScale\` |
| `z_SC4UIScale_DialogStatic-<tier>.dat` | `tools\dialog-static\` / `tools\packages\<tag>\` | `Plugins\010-SC4UIScale\` |
| `z_SC4UIScale_ItemIcons-<tier>.dat` | `tools\itemicons\` | `Plugins\010-SC4UIScale\` |
| `ItemIconsSub`, `MenuFix`, `ThirdPartyUI`, `WarriorUI`, `SaveWarningUI`, `CamUI`, `NamIcons`, `CamGraphLabels`, `CsiIcons`, `UncoveredIcons`, `SelectorUI` | their builders under `tools\` | `Plugins\zzz-SC4UIScale\` — **the subfolder is required** (load-order law) |
| `FontStyle-<tier>.ini` | `tools\fonts\` / `tools\packages\<tag>\` | `Plugins\010-SC4UIScale\`; `ScaleTier::SyncFont` copies the active tier to the probed `FontStyle.ini` |

**What the same tree looks like after conversion**, per folder:

```
Plugins\
  SC4UIScale.dll                                  <- the only root file
  010-SC4UIScale\
    SC4UIScale.ini  SC4UIScale.log  SC4UIScale.gcap
    FontStyle-15x.ini  FontStyle-2x.ini  FontStyle-3x.ini    <- copied, not payloads
    z_SC4UIScale_SelectiveArt.dat                 <- LIVE, name never changes
    z_SC4UIScale_SelectiveArt.15x.uipay
    z_SC4UIScale_SelectiveArt.2x.uipay
    z_SC4UIScale_SelectiveArt.3x.uipay
    z_SC4UIScale_SelectiveArt.off.uipay
    …DialogStatic, ItemIcons, WebText the same way…
    z_SC4UIScale_STATE.txt                        <- armed tag + gate reason
  zzz-SC4UIScale\
    z_SC4UIScale_ThirdPartyUI.dat  + its .uipay set
    …ItemIconsSub, WarriorUI, SaveWarningUI, CamUI, NamIcons, CsiIcons,
      UncoveredIcons, SelectorUI, CamGraphLabels, ZCarbon*…
    z_SC4UIScale_STATE.txt
```

Deploying still means dropping **all** tiers in and letting the DLL choose:
`ScaleTier` arms the right one at startup by copying that tier's payload over
the live name, and copies the right font into place. **Nothing is renamed, at
any point, by anyone** — that is the whole property sc4pac needs, and the
reason `z_SC4UIScale_STATE.txt` exists to carry the diagnosis a listing used
to give away for free.

**Deploy while the game is CLOSED.** It holds the DLL and dats open, and it
runs **elevated** — a normal shell cannot kill it, and it must never be
killed anyway. The established pattern is `_tests\Deploy-OnGameClose.ps1`:
poll for `SimCity 4.exe` to exit, then copy.

**The release bundle is built, not assembled by hand:** run
`_packaging\Build-Dist.ps1` and it produces `dist\SC4UIScale-v<version>\`
with a `Plugins\` tree you copy straight in, plus `README.txt`,
`Install.ps1`, `LICENSE.txt`, `THIRD-PARTY-NOTICES.md` and `SHA256SUMS.txt`.
It derives its file list **by parsing `_tests\Deploy-OnGameClose.ps1`**
rather than keeping a second copy of "what a working install contains": one
manifest, one failure mode.

---

## Building the packages

Every package is generated; nothing is hand-edited. The builders live under
`tools\`, and the end-to-end procedure — corpus bootstrap, per-tier rebuilds
and the gates that check them — is in [BUILDING.md](BUILDING.md). Two rules
that are not optional:

- **A mod's own dialogs are not in the game's data**, so nothing here can
  build them from a stock source. The dialog builder reads
  `tools\dialog-static\thirdparty-src\` (not shipped — it holds verbatim
  extracts of other people's mods) and fails loudly naming any missing TGI.
- **Art the game cuts into cells must keep dividing evenly.** The game picks
  a cell with an integer divide compiled into it: `imageWidth ÷ 4` for a
  four-state strip, `÷ 3` per axis for a nine-slice border. At fractional
  tiers the upscaler snaps dimensions to preserve that divisibility; at 2×
  and 3× it is free. See [BUILDING.md](BUILDING.md).

---

## Licence and dependencies

**This project's own code is PUBLIC DOMAIN — CC0 1.0, no rights reserved, no
attribution required.** Copy it, change it, sell it, ship it closed-source.
None of that needs permission or credit. `SPDX-License-Identifier: CC0-1.0`

**It statically links exactly two third-party libraries, and you must honour
their terms if you redistribute a build:**

| Component | Licence | Obligation on you |
|---|---|---|
| [**gzcom-dll**](https://github.com/nsgomez/gzcom-dll) — Nelson Gomez | **LGPL-2.1-or-later** | Ship its source and let recipients relink. Publishing this project's full source satisfies it. Changes to gzcom-dll itself stay LGPL. |
| **MinHook** — Tsuda Kageyu | **BSD-2-Clause** | Reproduce its copyright notice and disclaimer in your distribution. |

That is the complete list. This project does **not** use
`0xC0000054/sc4-resource-loading-hooks`, any other `sc4-*` plugin,
`memo33/*`, or `nsgomez/scgl` — the only third-party `<ClCompile>` entries in
the vcxproj are the two above.

SimCity 4 and its assets belong to **Electronic Arts**; this is an unofficial,
unaffiliated mod containing no EA code. The scaled art and font files it
generates are derived from the player's own installation, are not covered by
the CC0 dedication, and are excluded from the published source.

→ **Full detail, pinned commits and exact obligations:
[`THIRD-PARTY-NOTICES.md`](../THIRD-PARTY-NOTICES.md)** · dedication text:
[`LICENSE`](../LICENSE)
