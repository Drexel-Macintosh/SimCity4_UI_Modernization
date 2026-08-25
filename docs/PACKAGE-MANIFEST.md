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

---

## The tier system

`ScaleTier::Decide` picks the factor from the **render** resolution and
enables the matching package set: the active tier's dats live under their
`-<tag>` names, the others are renamed `.x1-disabled` at boot.

- **Render resolution is not the requested resolution.** DirectX +
  Fullscreen/Borderless renders at the monitor's native mode (the wrapper
  ignores the request); DirectX + Windowed and Software use the requested
  size.
- **Tier 1 = true stock**: every scaling subsystem off, all dats gated,
  FontStyle moved aside — the DLL is indistinguishable from a no-DLL install
  (isolation-tested).
- **All tiers carry identical entry counts and TGIs**; only pixel dimensions
  and layout coordinates differ.

### Filename tag convention (the DLL relies on this)

The factor tag goes in the base name, immediately before the extension:

| Factor | Tag | Example |
|---|---|---|
| 1.5× | `15x` | `z_SC4UIScale_SelectiveArt-15x.dat`, `FontStyle-15x.ini` |
| 2× | *(untagged)* | `z_SC4UIScale_SelectiveArt.dat` — the default generator output |
| 3× | `3x` | `z_SC4UIScale_SelectiveArt-3x.dat`, `FontStyle-3x.ini` |

`ScaleTier::SyncDat` builds every name as `base + tag + ".dat"`, so the
convention governs all tier-paired bases: `SelectiveArt`, `DialogStatic`,
`ItemIcons`, `ItemIconsSub`, `ThirdPartyUI`, `WarriorUI`, `SaveWarningUI`,
`CamUI`, `NamIcons`, `CsiIcons`, `UncoveredIcons`.

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

### Untagged packages (tier-independent, always on)

| Package | Entries | What it is |
|---|---|---|
| `z_SC4UIScale_MenuFix.dat` | 6 | Exemplar patches fixing CAM 4.0.1's broken submenu parents. Reported by the integrity test, not entry-asserted |
| `z_SC4UIScale_WebText.dat` | 3 | LTEXT overrides that name Simtropolis, matching the DLL's redirect of the dead `simcity.ea.com` link (active at every tier) |
| `zzz-SC4UIScale\z_SC4UIScale_CamGraphLabels.dat` | 1 | The one LTEXT (`0xFF5D2E9F`) CAM's Power/Water charts ask for and no installed archive provides. Inert without CAM by construction — nothing except CAM binds the instance |
| `zzz-SC4UIScale\z_SC4UIScale_SelectorUI-1x.dat` | 1 | The scale selector's own dialog at the stock tier — the Graphic Options script and nothing else. One entry by design: the stock tier must never ship scaled art |

A string has no geometry, so `CamGraphLabels` and `WebText` carry no tier
triple and no `.x1-disabled` variant.

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

| File | Source in this project | Destination |
|---|---|---|
| `SC4UIScale.dll` | `build\Release\` | `Documents\SimCity 4\Plugins-SC4UIScale\` |
| `SC4UIScale.ini` | `_packaging\SC4UIScale.ini` | beside the DLL |
| `z_SC4UIScale_SelectiveArt-<tier>.dat` | `tools\selective-safe\` / `tools\packages\<tag>\` | `Plugins-SC4UIScale\` |
| `z_SC4UIScale_DialogStatic-<tier>.dat` | `tools\dialog-static\` / `tools\packages\<tag>\` | `Plugins-SC4UIScale\` |
| `z_SC4UIScale_ItemIcons-<tier>.dat` | `tools\itemicons\` | `Plugins-SC4UIScale\` |
| `ItemIconsSub`, `MenuFix`, `ThirdPartyUI`, `WarriorUI`, `SaveWarningUI`, `CamUI`, `NamIcons`, `CamGraphLabels`, `CsiIcons`, `UncoveredIcons`, `SelectorUI` | their builders under `tools\` | `Plugins\zzz-SC4UIScale\` — **the subfolder is required** (load-order law) |
| `FontStyle-<tier>.ini` | `tools\fonts\` / `tools\packages\<tag>\` | beside the DLL; `ScaleTier` copies the active tier to the probed `FontStyle.ini` |

`ScaleTier` manages the tier gating itself at startup — it renames the
non-active tiers to `.x1-disabled` and copies the right font into place, so
deploying means dropping all tiers in and letting the DLL choose.

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
