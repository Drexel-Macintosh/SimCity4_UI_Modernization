# What it scales

A map of the interface, and what happens to each part. "Data" means an
enlarged package supplies it; "runtime" means the DLL resizes it live; several
need both.

## City view

| Element | How |
|---|---|
| Main toolbar and mode buttons | data + runtime |
| Every toolbar flyout (Zones, Transport, Utilities, Parks, Landscape, Signs…) | data + runtime |
| Sub-flyouts, their rings and back arrows | runtime — the ring and its stem are one sprite, so the container and the blit move together |
| God-mode toolset and its five flyouts | data + runtime |
| Emergency and Disaster panels | data + runtime |
| Dashboard minimap | runtime — the window *and* its render surface are recreated at the new size |
| Pause / disaster / situation alert borders | data (nine-slice art at tier size) |
| Mayor rating meter and decline arrow | data |
| Move In My Sim marker — the framed sim face, plate and green/red arrow that float over a candidate house | data + runtime — the art comes from a data-scaled `I-6a9455c9`, and both roots (`0x27DF05BE`/`0x27DF05BF`) are hooked for the BMPX blit so the bitmaps follow the window |
| Building query panels, including the ones the Colossus Addon Mod **adds** — its city info screen (Village Hall / Town Hall) and its civic and school panels | data — built from the mod's own scripts and bitmaps, in a package that switches itself off if the mod is removed |
| Tooltips | runtime — the text box is sized from the font, not from the scale factor |

## Dialogs

| Dialog | Notes |
|---|---|
| Budget, and all eight department detail panels | column insets are byte-patched; they're hard-coded in the executable |
| Ordinances, and the description popup | name-column width is re-encoded to fit at 3× |
| Graphs | the legend's width budget lives in the *panel builder*, not the chart, and is re-derived at scale |
| Data Views | legend born at the right size; the map is filled via the game's own terrain bake |
| Advisors | portraits, detail pages and speech boxes |
| Building Style Control | works with the stock dialog and with *Allow More Building Styles* |
| Audio Options | playlist rows and checkboxes |
| Quit / exit confirmation | including the in-city save warning |
| Establish City | radios, title band, spacing |
| Query panels | civic and residential building queries |

## News and advisors

The newsreader, the ticker, story and tutorial pages, per-row dismiss buttons
and the advisor mugshots. SimCity 4 renders this text through a built-in HTML
engine whose font-size tables live in the executable's read-only data — those
tables are patched directly, because no font configuration file can reach them.

## Region view

The region map is drawn as one contiguous slab with terrain continuous across
city boundaries, and city tiles stay clickable. Zoom works across ±5 levels.
The city bubble, its rating bar and the region flyouts all scale.

**Region rotation is not possible** — the tiles are baked at save time and no
rotation path exists in the region module.

## Menu icons

Every menu button's icon is a four-state strip, and the button picks its cell
by `imageWidth ÷ 4`. Supply a 1× strip inside a doubled button and you get two
half-size copies side by side, blanking on hover. All stock icons are covered,
plus 392 from the Network Addon Mod and the Colossus Addon Mod's own sets.

## Text

Font tables are generated per tier. Point sizes do **not** scale linearly with
ink — measured at about ×2.13 per doubling, not ×2.00 — so text boxes are sized
from measured font extents rather than multiplied by the tier factor.

## Not scaled

- **The intro video.** It plays at its authored size; the presentation rect is
  decided downstream of the four geometry constants that control its layout.
- **The 3D world.** Deliberately — it already renders at your native
  resolution, and stretching it is the thing this mod exists to avoid.
