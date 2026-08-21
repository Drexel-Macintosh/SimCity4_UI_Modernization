# Changelog

## 4.0.0

First public release.

SC4UIScale renders SimCity 4's interface at **1.5x, 2x or 3x** while the
world continues to render at your display's native resolution. The game has
no UI scaling of its own; its interface is built around 1024x768
assumptions, which leaves it unusable on modern high-resolution displays.

- **Automatic tier selection.** At launch the mod measures the resolution
  the game actually renders at and arms the largest tier that fits
  (1.5x from 1440x1080, 2x from 1920x1440, 3x from 2880x2160).
- **In-game settings panel.** Scale, resolution and window mode are
  selectable inside the game's own Graphic Options dialog. Choices apply on
  restart; a scale the chosen resolution cannot carry is refused rather than
  silently ignored.
- **Coherent by construction.** A hand-edited or inconsistent configuration
  is repaired to a runnable state at launch, so no combination of settings
  leaves the interface too large to navigate back from.
- **Stock is a first-class state.** Selecting 1x disarms every scaling
  subsystem and unloads every art package: identical to a clean install.
- **Scales the whole interface**, including third-party mod dialogs, menu
  icons, fonts, cursors and flyout menus. See `docs/WHAT-IT-SCALES.md`.
- **Nothing on disk is modified.** All scaling is in-memory per session;
  the mod owns only its own files.

Requires SimCity 4 Deluxe build 1.1.641. See `README.md` to install and
`research/KNOWN-LIMITATIONS.md` for what the mod does not do.
