# How it works

SimCity 4's interface is a tree of `cIGZWin` windows. Most are laid out from
`.UI` scripts stored as DBPF resources; some are built in code with hard-coded
constants; a few own render surfaces of their own. Scaling the UI means
handling all three, which is why this is a DLL and not just an art pack.

## The two halves

**Data.** Enlarged copies of the game's UI artwork and `.UI` layout scripts,
shipped as ordinary DBPF packages that load after the originals and win. This
covers everything the scripts describe: bitmaps, image rects, and the layout
of scripted dialogs.

**Runtime.** `SC4UIScale.dll` — a gzcom-dll plugin — handles what data cannot:

- **Live geometry.** Walks the window tree and resizes windows the scripts
  don't own, and re-docks panels whose position is computed rather than
  declared.
- **Code constants.** About thirty layout values are compiled into the
  executable — column insets, row widths, grid origins. Those are patched in
  memory at load, each verified against its expected opcode and stock operand
  before a single byte is written; a mismatch aborts that patch and logs it.
- **Render surfaces.** The minimap and Data Views map own DirectDraw surfaces
  created once at a fixed size. Resizing the window is not enough — the surface
  is destroyed and recreated at the new size, in the same action, because
  splitting them crashes the game.

## Born correct, not corrected

The hardest class of bug here isn't wrong geometry, it's *right geometry
applied too late*. A panel that is resized one tick after it appears has
already painted at the wrong size, and the player sees a flash or a jump.

So panels are made correct **before their first paint**, from inside the game's
own `cGZWin::SetFlag` path — the call the game itself makes as a window becomes
visible — gated on the subtree being fully built. The periodic sweep remains as
a belt, and skips anything already handled.

The corollary: **if a fix has to re-apply every tick, it is a fight, not a
fix.** Growing a buffer the game owns from outside means the
game's next rebuild undoes it. Grow it *inside* the rebuild and everything
downstream inherits the new size — including hit-test masks.

## Tiers

Three scale factors — 1.5×, 2×, 3× — chosen automatically from the screen
resolution, with a slack check so a resolution that cannot fit the scaled UI
falls to the tier below. Each tier has its own art packages, and exactly one is
active at a time.

**How a tier is armed (v4.5.0).** Every package has one live file whose name
*never changes* — `z_SC4UIScale_<Pkg>.dat` — and a set of inert payloads beside
it, `z_SC4UIScale_<Pkg>.<tag>.uipay`. Arming copies the chosen payload's bytes
over the live file, atomically, during the plugin scan. The payloads are never
loaded: the scan is gated on the file extension, measured by putting a real
package at `.uipay` and confirming it was absent from the game's own
registered-segment census while thirteen live `.dat` files appeared in the same
census.

This replaced a rename (`.dat` ↔ `.dat.x1-disabled`), which worked but meant a
package manager could not uninstall the mod: it removes files by the name it
installed, and most of ours were living under a different one.

The cost of a constant filename is that a directory listing no longer tells you
anything — which tier is armed, and why a package is switched off, look
identical on disk. So the DLL writes `z_SC4UIScale_STATE.txt` into each of its
folders on every boot, naming the armed tag and the reason per package. That
file, and the log, are where the answer lives now.

Nothing here is 2×-only arithmetic. Every constant is a function of the factor,
and 1.5× exists specifically to keep that honest — a value that only works at
even multiples fails visibly there.

## Third-party gating

Packages that patch another mod's UI are keyed to that mod's presence, checked
by filename at load. If the mod isn't installed the package is switched off, so
this layer can never inject a frozen copy of someone else's interface into a
game that doesn't have it. "Off" means its live file holds a one-entry package
that claims nothing, so the game's own load order promotes whatever would have
won anyway.

## Safety

- The plugin verifies the game is **1.1.641** before patching anything and
  disables itself otherwise.
- Every code patch checks the bytes it expects to find before writing.
- Everything it does is in-memory and per-session. **No game file is modified.**
  The mod does rewrite *its own* package files to arm a tier — never anything
  the game shipped, and never anything another mod installed.
- It writes `SC4UIScale.log` into `Plugins\010-SC4UIScale\` (v4.4.0; it used
  to sit beside the DLL) — the first thing to attach to a bug
  report.
