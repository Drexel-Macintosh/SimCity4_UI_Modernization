# SC4UIScale

**Runtime UI scaling for SimCity 4 Deluxe 1.1.641.** The game renders the
world at your display's native resolution while every interface element —
windows, buttons, fonts, icons, cursors, menus — is drawn at 1.5×, 2× or 3×.
SimCity 4 has no UI scaling of its own; its interface is hard-coded around
1024×768 assumptions, which makes it near-unusable on modern high-DPI
displays. This project fixes that without modifying a single game file.

## How it works

Two halves that must always agree:

- **Data** — enlarged copies of the game's UI art and `.UI` layout scripts,
  shipped as DBPF packages (`z_SC4UIScale_*.dat`) that load after the
  originals and win by plugin-order precedence.
- **Runtime** — `SC4UIScale.dll`, a gzcom-dll plugin: scales the live
  window tree as dialogs are created, byte-patches ~30 layout constants
  inside the executable's memory image, and rebuilds render surfaces that
  must be recreated rather than resized.

Everything is in-memory, per session. Nothing on disk is touched except the
mod's own files.

## Features

- **Auto scale** — picks the largest tier your resolution can carry at boot
  (1.5× ≥ 1440×1080 · 2× ≥ 1920×1440 · 3× ≥ 2880×2160).
- **In-game selector** — a Scale / Resolution / Window Mode panel inside the
  game's own Graphic Options dialog. Changes apply on restart, guarded so no
  combination of choices can produce an unusable state.
- **Boot-state validation** — a hand-edited or incoherent ini is repaired to
  a runnable state at launch, never trapping the player in an oversized UI.
- **Window modes** — Borderless (recommended), exclusive Fullscreen, and
  Windowed, coordinated across the three components that each own a piece of
  the answer (the game, SC4GraphicsOptions.dll, dgVoodoo).

## Requirements

- SimCity 4 Deluxe, executable build **1.1.641** (the byte patches are
  keyed to it and refuse anything else)
- Windows, 32-bit game process (the DLL is Win32/x86)
- [dgVoodoo2](http://dege.freeweb.hu/dgVoodoo2/) or another wrapper that
  lifts the DirectX 7 2048×2048 texture cap — required for 3×, recommended
  everywhere
- SC4GraphicsOptions.dll (community plugin) if you want the in-game
  Resolution / Window Mode controls; the scale selector works without it

## Install

1. Copy `SC4UIScale.dll`, `SC4UIScale.ini` and the `z_SC4UIScale_*` packages
   into `Documents\SimCity 4\Plugins`.
2. Launch the game. AutoScale picks the right tier for your resolution;
   change it any time in **Options → Graphic Options**.

Building from source: [docs/BUILDING.md](docs/BUILDING.md) — Visual Studio,
`Release|Win32` (never x64; the game is a 32-bit process).

## Repository map

| Path | What it is |
|---|---|
| `src/` | The DLL: director, window-tree scaler (`UiSpike.cpp`), executable patches (`CodePatches.cpp`), tier/package logic (`ScaleTier.cpp`) |
| `tools/` | Package builders — every shipped `.dat` is generated, never hand-edited |
| `docs/` | How it works, what it scales, package manifest, compatibility |
| `research/` | The reverse-engineering knowledge base: the scaling laws, decompiled subsystem references, open unknowns |
| `_tests/` | The regression net: gates, goldens, deploy scripts |
| `VERSION-HISTORY.txt` | The full engineering ledger, newest first |

No Maxis-derived art is committed to this repository; the packages are built
locally from an owned installation.

## Status

Working and in daily use at 1.5× (2400×1600), 2×, and 3× (3840×2160).
See [START-HERE.md](START-HERE.md) for orientation and
[CONTINUITY.md](CONTINUITY.md) for the current work in flight.
