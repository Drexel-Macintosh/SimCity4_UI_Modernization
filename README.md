# SimCity 4 UI Modernization

**Runtime UI scaling for SimCity 4 Deluxe 1.1.641.** The game renders the
world at the display's native resolution while every interface element —
windows, buttons, fonts, icons, cursors, menus — is drawn at 1.5×, 2× or 3×.
SimCity 4 has no UI scaling of its own; its interface is hard-coded around
1024×768 assumptions, which makes it near-unusable on modern high-DPI
displays. This project fixes that without modifying a single game file.

It is **not** whole-frame upscaling. The world stays sharp; only the
interface grows.

## Tiers

| Tier | Minimum render resolution | Character |
|---|---|---|
| 1.5× | 1440×1080 | fractional — the tier that exercises every rounding path |
| 2× | 1920×1440 | the reference tier: exact doubling throughout |
| 3× | 2880×2160 | for 4K-class displays |

**Auto scale** picks the largest tier the display resolution can carry at boot
and arms the matching package set. An in-game selector inside the game's own
Graphic Options dialog lets the player change scale, resolution and window
mode; changes apply on restart, and boot-state validation repairs a
hand-edited or incoherent configuration to a runnable state, so no combination
of choices can trap the player in an unusable UI. Tier 1 (stock) is a
first-class state: every scaling subsystem off, indistinguishable from a
no-mod install.

## Requirements

- **SimCity 4 Deluxe, executable build 1.1.641.** The in-memory byte patches
  are keyed to this exact build and refuse anything else — deliberately.
- **Windows, 32-bit game process.** The DLL is Win32/x86.
- **[dgVoodoo2](http://dege.freeweb.hu/dgVoodoo2/)** or another wrapper that
  lifts the DirectX 7 2048×2048 texture cap — required for 3× and for any
  render surface wider than 2048 px, recommended everywhere. Window modes
  (Borderless / Fullscreen / Windowed) are coordinated with the wrapper.
- **SC4GraphicsOptions.dll** (community plugin) for the in-game Resolution /
  Window Mode controls. The scale selector works without it.

## Install

1. Download a bundle from [Releases](../../releases), unzip it, and copy
   its `Plugins\` tree into `Documents\SimCity 4\Plugins` - it is two
   folders and one file:

   ```
   Documents\SimCity 4\Plugins\
     010-SC4UIScale\      packages, fonts, log
     zzz-SC4UIScale\      overrides that must beat other mods
     SC4UIScale.dll       the only loose file the bundle installs
   ```

   On its first launch the mod writes one more loose file beside the DLL,
   `SC4UIScale.ini` - your settings. It lives at the **Plugins root**, not in
   the mod's folder, because a package manager replaces the whole versioned
   package folder on every update and your settings would go with it. It is
   created only when absent and is never overwritten.

   The DLL has to sit at the root: SimCity 4's dat scan is recursive but its
   **DLL loader is top-level only**. Everything else lives in the folders, so
   uninstalling is deleting those three things.
   Upgrading from before v4.4.0 moves your old root files - settings included
   - into `010-SC4UIScale\` on the first launch.
2. Launch the game. AutoScale picks the tier the current resolution can
   carry. To change it, open **Options → Graphic Options**; that panel also
   sets resolution and window mode, and changes apply on restart.

**Optional companion plugin.** The in-game resolution and window-mode control
writes `SC4GraphicsOptions.ini`, which is read by the community plugin
[SC4 Graphics Options](https://community.simtropolis.com/files/file/36091-sc4-graphics-options/).
Install it for those settings to take effect. UI scaling itself works without
it; only the resolution/window-mode control needs it.

Prebuilt release bundles are published under
[Releases](../../releases); the repository itself ships the *generators*,
not the artwork (see below). Building from source:
[docs/BUILDING.md](docs/BUILDING.md) — Visual Studio, `Release|Win32`
(never x64; the game is a 32-bit process).

## How it works

Two halves that must always agree. **Data**: enlarged copies of the game's UI
art and `.UI` layout scripts, shipped as DBPF packages (`z_SC4UIScale_*.dat`)
that load after the originals and win by plugin-order precedence. **Runtime**:
`SC4UIScale.dll`, a gzcom-dll plugin that scales the live window tree as
dialogs are created, byte-patches the layout constants compiled into the
executable's memory image (each site verified against its expected bytes
before anything is written), and rebuilds the render surfaces that must be
recreated rather than resized. Everything is in-memory, per session; nothing
on disk is touched except the mod's own files. Full detail:
[docs/HOW-IT-WORKS.md](docs/HOW-IT-WORKS.md).

## Documentation

| Path | What it is |
|---|---|
| [docs/](docs/) | Product documentation: [how it works](docs/HOW-IT-WORKS.md), [what it scales](docs/WHAT-IT-SCALES.md), [compatibility](docs/COMPATIBILITY.md), [building](docs/BUILDING.md) |
| [CHANGELOG.md](CHANGELOG.md) | Release history |

Known limitations are listed in
[research/KNOWN-LIMITATIONS.md](research/KNOWN-LIMITATIONS.md).

## Engine documentation

Scaling this interface meant reverse-engineering it first. Maxis shipped no UI
SDK, so one had to be written — from measurement, against
`SimCity 4.exe` 1.1.641.0. That reference is published here alongside the mod,
because it outlives it: the next person to modify this game's interface should
not have to rediscover any of it.

**Start at [docs/DECOMPILATION-STATUS.md](docs/DECOMPILATION-STATUS.md)** —
what is documented, what is partial, what is still unknown, and every hook and
byte patch the DLL installs.

| Path | What it is |
|---|---|
| [tools/research/](tools/research/) | The engine reference: how the UI is built, sized, painted and hit-tested, plus per-screen anatomy for the region view, mayor mode, the budget dialogs and more |
| [research/laws/](research/laws/) | 50 engineering rules, each paid for by a defect that reached the screen — the most transferable material here |
| [research/UNKNOWNS-AND-NEXT-TARGETS.md](research/UNKNOWNS-AND-NEXT-TARGETS.md) | The unknowns register: what is genuinely open, what was closed as impossible, and the refutation record behind both |
| [tools/uimap/](tools/uimap/) | The offline model: a layout emulator and gate suite that answer geometry questions without launching the game |
| [_tests/](_tests/) | The regression net: contract gates and deploy scripts, also offline |

## Repository map

| Path | What it is |
|---|---|
| `src/` | The DLL: director, window-tree scaler (`UiSpike.cpp`), executable patches (`CodePatches.cpp`), tier/package logic (`ScaleTier.cpp`) |
| `tools/` | Package builders — every shipped `.dat` is generated, never hand-edited — plus the research corpus and the offline model |
| `docs/`, `research/` | Product documentation and the distilled research tier (laws, unknowns register) |
| `_tests/` | Gates, deploy scripts and the regression ledger |
| `vendor/` | The third-party libraries the DLL links — gzcom-dll, MinHook and sc4-dll-utilities, each a **git submodule** pinned to a specific upstream commit (fetch with `git submodule update --init`) |

No Maxis-derived art is committed to this repository; the packages are built
locally from an owned installation. The research corpus does carry game
content in text form as its evidence base — decoded scripts, data records and
disassembly listings — set out in
[THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md) §4a.

## License

This project's own code is dedicated to the public domain —
[CC0 1.0](LICENSE), no rights reserved, no attribution required. It
statically links two third-party libraries with their own terms
(gzcom-dll, LGPL-2.1-or-later; MinHook, BSD-2-Clause); see
[THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md) before redistributing a
build. SimCity 4 and its assets belong to Electronic Arts; this is an
unofficial, unaffiliated mod. The DLL links no EA code and the repository
carries no EA binaries or artwork; the engine documentation's text-form
evidence (decoded scripts, disassembly listings) is disclosed in
[THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md) §4a.
