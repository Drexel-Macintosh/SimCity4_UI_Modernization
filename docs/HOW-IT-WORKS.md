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
already painted at the wrong size, and the user sees a flash or a jump.

So panels are made correct **before their first paint**, from inside the game's
own `cGZWin::SetFlag` path — the call the game itself makes as a window becomes
visible — gated on the subtree being fully built. The periodic sweep remains as
a belt, and skips anything already handled.

The corollary, learned expensively: **if a fix has to re-apply every tick, it
is a fight, not a fix.** Growing a buffer the game owns from outside means the
game's next rebuild undoes it. Grow it *inside* the rebuild and everything
downstream inherits the new size — including hit-test masks.

## Tiers

Three scale factors — 1.5×, 2×, 3× — chosen automatically from the screen
resolution, with a slack check so a resolution that cannot fit the scaled UI
falls to the tier below. Each tier has its own art packages; only one is active
at a time, the others sit on disk renamed `.x1-disabled`.

Nothing here is 2×-only arithmetic. Every constant is a function of the factor,
and 1.5× exists specifically to keep that honest — a value that only works at
even multiples fails visibly there.

## Third-party gating

Packages that patch another mod's UI are keyed to that mod's presence, checked
by filename at load. If the mod isn't installed the package is deactivated, so
this layer can never inject a frozen copy of someone else's interface into a
game that doesn't have it.

## Safety

- The plugin verifies the game is **1.1.641** before patching anything and
  disables itself otherwise.
- Every code patch checks the bytes it expects to find before writing.
- Everything it does is in-memory and per-session. **No game file is modified.**
- It writes `SC4UIScale.log` beside itself — the first thing to attach to a bug
  report.
