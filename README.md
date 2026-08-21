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

1. Copy `SC4UIScale.dll`, `SC4UIScale.ini` and the `z_SC4UIScale_*` packages
   into `Documents\SimCity 4\Plugins`.
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
| [research/laws/](research/laws/) | The scaling laws: engineering rules, each derived from a real defect; start at the [index](research/laws/INDEX.md) |
| [tools/research/](tools/research/) | The SDK-style reference to SC4's UI engine, written from measurement (Maxis shipped no SDK) |
| [tools/uimap/](tools/uimap/) | The offline simulator: layout emulation, gates and compositors that run without launching the game |
| [_tests/](_tests/) | The regression net: contract gates and deploy scripts that run without the game |
| [CHANGELOG.md](CHANGELOG.md) | Release history |

Known limitations are listed in
[research/KNOWN-LIMITATIONS.md](research/KNOWN-LIMITATIONS.md).

## Repository map

| Path | What it is |
|---|---|
| `src/` | The DLL: director, window-tree scaler (`UiSpike.cpp`), executable patches (`CodePatches.cpp`), tier/package logic (`ScaleTier.cpp`) |
| `tools/` | Package builders — every shipped `.dat` is generated, never hand-edited |
| `vendor/` | The third-party libraries the DLL links — gzcom-dll and MinHook, each a **git submodule** pinned to a specific upstream commit (fetch with `git submodule update --init`) |

No Maxis-derived art is committed to this repository; the packages are built
locally from an owned installation.

## License

This project's own code is dedicated to the public domain —
[CC0 1.0](LICENSE), no rights reserved, no attribution required. It
statically links two third-party libraries with their own terms
(gzcom-dll, LGPL-2.1-or-later; MinHook, BSD-2-Clause); see
[THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md) before redistributing a
build. SimCity 4 and its assets belong to Electronic Arts; this is an
unofficial, unaffiliated mod containing no EA code.
