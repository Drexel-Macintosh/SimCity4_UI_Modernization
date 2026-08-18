# Changelog

Notable builds. Versions not listed were incremental fixes along the way.

## 3.0.0 — first public release

**This is the first public release of SC4UIScale.** Every version numbered
below 3.0.0 was an internal development build and was never published. Those
entries are kept because they record what each change was and why it was made.

3.0.0 is a publication milestone rather than a feature release — the work in it
is the work listed below. What that adds up to, for anyone reading this first:

- **The interface is drawn at 1.5×, 2× or 3×**, chosen automatically from your
  screen resolution. The city itself still renders natively; nothing is
  upscaled as a whole frame.
- **Covered:** toolbars, flyouts and sub-flyouts, dialogs, the news reader,
  the dashboard minimap, the region map, the Data Views map, the graphs and
  their legends, menu icons, tooltips and fonts.
- **Nothing on disk is modified.** No save game and no game file is written;
  the enlarged artwork ships as ordinary plugin packages and the rest happens
  in memory, per session.
- **Compatibility packages** for the Network Addon Mod, the Colossus Addon Mod,
  *Allow More Building Styles*, *Save Warning* and *God Terraforming in Mayor
  Mode* — each built from that mod's own artwork, each deactivating itself if
  the mod is not installed. Menu icons from memo33's Submenus DLL are covered
  too, in a package that is not gated.
- **Known issues.** Two defects remain open at 1.5×: the last item in a flyout
  needs a scroll before it appears, and the dashboard city map can render
  incorrectly. Neither is possible at 2× or 3×, which are also the more heavily
  verified tiers. The intro video does not scale.

## v2.99.0 — state-strip artwork at 1.5×

- **The bright slivers on the region view's population rows are gone.** At 1.5×
  only, each of the three population rows on a city's region bubble ended with
  a thin bright sliver hard against its right edge.

  Buttons of this kind draw from one wide sheet cut into equal cells — one cell
  per state: normal, hover, pressed, disabled. Enlarging a sheet snaps its width
  so that division stays exact, but the resampler was still mapping the *whole*
  sheet at once. Once the snap moved the width off an exact multiple, the two
  disagreed and the cell boundaries drifted: a few columns of the next state
  were drawn inside the previous one. Three rows, three slivers. Those sheets
  are now resampled one state at a time, so a cell boundary in the enlarged
  sheet lands exactly where it does in the original.

  Which sheets are state strips is no longer inferred from their dimensions. The
  list is derived from the layout scripts that actually bind each sheet — 341
  scripts read, 197 art-bound button sheets, 193 proven state strips. An earlier
  attempt that guessed from the numbers alone matched 1186 sheets, six times as
  many, and moved a pixel in an advisor panel that was not a state strip at all;
  it was measured, rejected and backed out.

- **2× and 3× artwork is byte-for-byte unchanged** — none of the 2,206 images
  differs at either tier. 77 changed at 1.5×.

## v2.98.0 — static dialogs at 1.5×

- **Tearing around the region view's play button is gone.** At 1.5×, the play
  button on a city's region bubble and two controls beside it showed a leftover
  column of the next state's artwork down one edge.

  This is the same defect v2.94.1 fixed for buttons drawn by the live layout
  pass, and the reason it came back is worth stating: that fix was made in one
  of the two places that size a control and not the other. Some dialogs are
  served whole from a prebuilt package and are deliberately excluded from the
  live pass — running both would scale them twice — so nothing repairs them
  afterwards. The same button therefore came out 83 pixels wide when the live
  pass sized it and 82 when the package builder did, against an 83-pixel artwork
  cell. The package builder now applies the identical rule: a control that draws
  artwork and has no crop of its own takes its enlarged size from its own size
  rather than from its neighbours' edges.

  47 controls across 19 dialogs move at 1.5×, by at most one pixel each.
  Position never changes, only size. Text controls are deliberately left alone —
  resizing them would move a line break in dialogs that are already confirmed
  good.

- **Invisible at 2× and 3×, and now proven so.** For whole-number factors both
  ways of working the size out give the same answer, and the build stops if a
  single pixel ever moves at those tiers.

- **The check that existed for exactly this had never looked at these dialogs.**
  It scanned the live-pass artwork only, and where it did see a 1.5× discrepancy
  it excused it on the grounds that the live pass repairs it — which is true
  where it was looking and false where it was not. It now has a second half that
  reads the shipped dialogs verbatim and fails at every tier.

- **Still open, and recorded rather than excused:** 347 of the 460 artwork-sized
  buttons have an artwork cell two pixels taller than their window. That is a
  different cause — a height being snapped on sheets whose states run
  horizontally — and fixing it globally would move a third of all artwork, so it
  is a deliberate decision left for its own release.

## v2.97.1 — the dialogs a mod ADDS

- **Colossus Addon Mod's own windows are scaled for the first time.** The
  Village Hall / Town Hall info screen — the one captioned "MZ v1", with the
  city summary, utilities, civic and environmental columns — rendered at its
  original size while every label around it was drawn with the scaled font.
  The result was labels cut off mid-word with their values printed on top of
  them. CAM's school and civic query panels had the same problem. All three
  are now built at your tier, along with the nine strips and badges the info
  screen draws.

  These panels had rendered that way for the whole life of the project. They
  are not replacements for anything in the base game — the mod adds them — so
  there was no stock version to compare them against, and nothing flagged them
  as unhandled. Every UI script in the game is now either the base game's or
  ours.

  As with every other mod override we ship, this is built from CAM's own data,
  changes only pixel geometry and font references, ships in its own file, and
  disables itself if CAM is removed or updated. No file belonging to another
  mod is ever modified.

- **Row stripes in CAM's query panels now run the full width of their row.**
  These panels draw a coloured strip behind each row by cropping a piece out of
  a bitmap. Scaling moved the row and the bitmap but not the crop, so the strip
  stopped part-way across and left bare panel behind it. Two of the panels have
  been drawing short strips since the CAM support first shipped.

- **The version in the log header is correct again.** It had read 2.93.1 for
  several releases, so the log named a build that was not running.

## v2.94.1 — 1.5×, continued

More of the 1.5× tier, and one caption that was never ours to begin with.

- **The "reverse L" on toolbar buttons is gone.** At 1.5× some buttons drew a
  thin line down their right edge and along their bottom. The cause is that a
  control's scaled *width* was derived from its scaled *edges*, so it depended
  on where the control sat: a button starting at an even x got 71 pixels, one
  starting at an odd x got 70, and both were drawing from a 71-pixel art cell.
  The leftover column and row were the line. Leaf controls — discrete icons —
  now take their scaled size from their size instead of their edges. Nothing
  moves and nothing changes by more than a pixel. Panels are untouched, because
  deriving *their* size from their edges is what keeps adjacent pieces flush.

  This is invisible at 2× and 3×: doubling and tripling a whole number is exact,
  so the two ways of working it out already agreed.

- **The blank fourth row in the Power and Water graphs now says "Exported".**
  This one is a data gap in CAM, not in SimCity and not in this mod. CAM's
  Power and Water charts declare four series and ask for a caption resource for
  the fourth that isn't in any installed file — so the row rendered with a
  working checkbox, a coloured swatch, and no text. We ship the missing
  20-byte string rather than modify CAM's file; it is inert if CAM isn't
  installed, and it can be deleted once CAM fixes the id. Reported upstream.

## v2.93.2 — 1.5×

The first proper look at the 1.5× tier. It had passed every automated check
since the tier was added, because the checks compare our output against our own
rules and the rules were what was wrong.

- **White seams across flyout art and toolbar buttons are gone.** SimCity cuts
  its art sheets into cells with an integer divide — three for a nine-slice
  border, four for a button's normal/hover/pressed/disabled strip. At 2× and 3×
  a scaled sheet always still divides evenly. At 1.5× it often doesn't, so the
  cells drift apart and each one draws a sliver of the next, which reads as a
  bright line. Scaled dimensions are now snapped to keep those divides exact.
- **Text no longer clips at 1.5×.** Point sizes round down rather than to
  nearest; rounding up overshot the boxes.

2× and 3× artwork is byte-for-byte unchanged.

Still open at 1.5×: the last item in a flyout needs a scroll to appear, and the
dashboard city map can render wrong. 2× and 3× are unaffected and remain the
more heavily verified tiers.

## v2.93.1

- Menu icons from the **Network Addon Mod** (392 of them) are covered — they
  previously rendered as two half-size copies that blanked on hover.
- Startup splash no longer tiles 2×2.
- Removed the compiler's absolute build path from the shipped binary.

## v2.92.0 — Graphs

Graphs' option grid docks correctly at 2× and 3×. The band is bottom-anchored
per the design rather than offset from the chart's top, which is why it had
been wrong by the same amount at every tier.

## v2.88.0 — News rows at 3×

The news row's width budget lived in a sign-extended 8-bit immediate, which
capped what could be expressed at 3×; the instruction window was widened to a
32-bit form, so 3× now ships the same content as 1.5× and 2×.

## v2.85.0 — Region zoom

Region zoom across ±5 levels, rebuilt from a pristine snapshot each time rather
than resizing in place.

## v2.81.1 — Region map

The region draws as one contiguous slab with terrain continuous across city
boundaries, and city tiles are clickable. One region cell is 128 screen pixels
at every resolution — four floats in the executable's data section were the
whole defect.

## v2.76.0 — Data Views map

Full-size Data Views map, via an ×8 extension of the game's own terrain bake.

## v2.55.0 — Graphs legend

The chart never laid out its own legend; the *panel builder* did, once, from
six hard-coded literals plus the window width. Re-derived at scale and patched
at birth.

## v2.46.0 — Sub-flyouts

Sub-flyout rings and their back-arrow click zones sit correctly. The ring and
its stem are a single sprite blitted at an origin stored per-open, so the
container and the sprite have to move together or neither does.

## v2.41.19 — Minimap

The dashboard minimap scales and its render surface is recreated in the same
action, from inside the game's own show path — early enough to be correct
before the first paint.

## v2.36.x — Born correct

Flyouts and panels made correct *before* their first paint rather than
corrected a tick later, ending the open-flash and open-jump.

## v2.32.0 — Tiers

1.5× / 2× / 3×, selected automatically from the screen resolution, with per-tier
art packages and font tables.

## v2.0 — First working build

Runtime UI scaling for SimCity 4 Deluxe 1.1.641. Internal, like everything else
below 3.0.0.
