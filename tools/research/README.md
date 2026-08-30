# The SC4 UI engine, reverse-engineered

SimCity 4 shipped with no UI SDK. This directory is one, written from
measurement while scaling that UI to 2x and 3x — the engine model, the
per-family anatomy, and the record of what was refuted along the way.

Everything here describes **SimCity 4 Deluxe 1.1.641.0 (Steam, x86,
4GB-patched)**, ImageBase `0x400000`, file offset = VA − 0x400000. All
disassembly was done offline with capstone; the game binary is opened
read-only and never modified on disk.

## Start here

| If you want to | Read |
|---|---|
| Understand how the UI is built, sized, painted and hit-tested | [SC4-UI-ENGINE.md](SC4-UI-ENGINE.md) — the engine model, and the one file to read first |
| Diagnose a specific UI defect | [TRIAGE.md](TRIAGE.md) — 49 symptom rows, each pointing at a mechanism |
| Know what the vendor SDK leaves out | [SDK-GAPS.md](SDK-GAPS.md) — vtable layout, the paint pipeline, the class registries |
| Know how any of this was established | [METHOD.md](METHOD.md) — the evidence rules, and what is not allowed to substitute for them |
| See what is documented and what is still unknown | [../../docs/DECOMPILATION-STATUS.md](../../docs/DECOMPILATION-STATUS.md) — per-screen status, hook and patch inventory |

## The engine reference

- **[SC4-UI-ENGINE.md](SC4-UI-ENGINE.md)** — the core. §2 the widget
  catalogue, §3 the `.UI` script format, §4 art binding and the sizing rules,
  §8 the virtual-address tables. Read once and you can predict how an unseen
  panel will behave.
- **[SDK-GAPS.md](SDK-GAPS.md)** — what `gzcom-dll` does not document: the
  window-class population and how to identify one, `GZWinBMP` in full, the
  paint pipeline, the class registries.
- **[SCALING-AXES.md](SCALING-AXES.md)** — every axis the mod scales, and the
  two-knob model behind them.
- **[MECHANISM-GENERATIONS.md](MECHANISM-GENERATIONS.md)** — which cure
  family is on which generation, so an old approach is not re-applied to a
  problem that outgrew it.
- **[FINAL-3-PERCENT.md](FINAL-3-PERCENT.md)** — the honest denominator: what
  fraction of the UI is mapped, the three creation channels no offline tool
  can enumerate, and what is structurally unknowable.

## Per-family anatomy

Each of these decodes one screen or one widget family down to addresses and
struct offsets.

| Document | Subject |
|---|---|
| [REGION-SCREEN.md](REGION-SCREEN.md) | The region view — 203 functions, field maps for six objects, a 17-row lever table, and the dead ends |
| [MAYOR-MODE.md](MAYOR-MODE.md) | The city-mode HUD and its panels |
| [BUDGET-DETAIL-ANATOMY.md](BUDGET-DETAIL-ANATOMY.md) | The budget detail dialogs |
| [GOD-MODE-FLYOUTS.md](GOD-MODE-FLYOUTS.md) | God-mode tool flyouts and the nested sub-flyout geometry |
| [CITY-SITUATION-INDICATORS.md](CITY-SITUATION-INDICATORS.md) | The U-Drive-It offer balloon and the dispatch-indicator system that draws it |
| [CITY-DOCK-OVERLAP.md](CITY-DOCK-OVERLAP.md) | The bottom-left dock composition and its clearances |
| [DYNAMIC-CONTROLS.md](DYNAMIC-CONTROLS.md) | Code-drawn controls: class map and geometry sources |
| [FONTS-AND-DIALOGS.md](FONTS-AND-DIALOGS.md) | Font resolution and transient-dialog sizing |
| [UI-ART-BINDING.md](UI-ART-BINDING.md) | How art binds to windows, and why blanket art replacement is unsafe |
| [ITEMICONS.md](ITEMICONS.md) | Exemplar-bound item icons and Sim portraits |
| [REGION-SWITCH.md](REGION-SWITCH.md) | The region/city transition and what it re-lays |
| [SC4-WORLD-OVERLAYS.md](SC4-WORLD-OVERLAYS.md) | The 23-row census of UI-like visuals drawn **outside** the window tree, and the triage that tells the two worlds apart |
| [STOCK-PARITY.md](STOCK-PARITY.md) | Stock 800×600 against 2x native, side by side |

## Compatibility reports

Findings about other people's mods, written up for their authors as much as
for us: [CAM](UPSTREAM-CAM-REPORT.md),
[NAM](UPSTREAM-NAM-REPORT.md),
[Building Styles](UPSTREAM-BUILDINGSTYLES-REPORT.md),
[Carbon Skin](UPSTREAM-CARBON-REPORT.md),
[God Terraforming](UPSTREAM-WARRIOR-REPORT.md),
[save warning](UPSTREAM-SAVEWARNING-REPORT.md).
[COMMUNITY-UI-WIKI-NOTES.md](COMMUNITY-UI-WIKI-NOTES.md) records which
community claims about the `.UI` format survived checking.

## How to read a claim

Every non-obvious statement carries its own evidence inline — a virtual
address, a log line, a script path, or the document that proved it. Three
kinds of hex number appear and are easy to confuse, so the documents always
say which one they mean:

- a **window id** is the `id=0x…` in a `.UI` script, what `GetID()` returns;
- a **clsid** is the class selector in `clsid=`, resolvable to a name through
  the exe's own registry;
- a **class vtable address** is an `.rdata` address, which is how anonymous
  windows get identified at all.

Two conventions worth knowing before you cite anything from here. **The symbol
is the anchor, the number is not** — file:line citations rot fast (one
document measured 92% stale in weeks), so cite a symbol or a VA. And **a null
is not evidence**: a probe that finds nothing proves nothing until you show it
could have seen the thing, which is why the probe write-ups state what each
instrument cannot see.

## The evidence base

- **`udriveit/`** — the largest cluster: probe scripts and their output from
  the investigation that identified the offer balloon, plus the general
  exe-mining toolbox that grew out of it. Includes whole-function disassembly
  listings.
- **`regionmap/`** — the region screen sliced function by function, eight
  files, generated against the function-start database in `../uimap/`.
- **`overlays/`** — per-row deep dives behind the in-world census. Each states
  its own grade; several are explicitly PARTIAL (mechanism named from static
  disassembly, never yet seen running).
- **`_checkpoints/`** — session records, kept as history. Dated, not
  maintained; the canonical files above supersede them wherever they differ.
- **`carbon/`, `zots-decode/`, `effdir/`, `scripts/`, `probe162/`,
  `unknowns-instruments/`, `recovered-headers/`, `morebuildingstyles/`,
  `sharp15/`** — the instruments behind individual findings.
- **`submenus-dll-src/`** — vendored source of another author's mod, kept for
  reference under its own licence. Not ours.

Some of this material reproduces game content as text — decoded scripts, data
records, disassembly listings. What that is and how it is licensed is set out
in [THIRD-PARTY-NOTICES.md](../../THIRD-PARTY-NOTICES.md) §4a.

The offline simulator that these documents are checked against — the layout
emulator, the gates, and the model databases — lives in
[../uimap/](../uimap/).
