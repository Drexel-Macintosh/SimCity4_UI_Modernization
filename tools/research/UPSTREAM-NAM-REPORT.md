# Upstream note — Network Addon Mod (NAM)

Informational. There is no defect in NAM. SC4UIScale ships a compatibility
layer for it, and the NAM team needs to do nothing. This note exists because
every third-party override SC4UIScale performs is recorded with a
developer-facing callout.

Measured against the sc4pac package tree `Plugins\770-network-addon-mod\`.

## What NAM ships that the layer touches

Menu-button **ItemIcons** — DBPF entries of type `0x856DDBAC` in group
`0x6A386D26`. Nothing else. NAM's networks, textures, exemplars, RUL files,
LTEXT and DLLs are untouched.

A census of both plugin trees finds **392 distinct ItemIcon instances whose
winning supplier is a file inside `770-network-addon-mod\`**. They come from
across the whole NAM tree rather than one icon pack — the biggest single
contributors are:

| supplier file | icons won |
|---|---:|
| `RealHighway_Core.dat` | 20 |
| `RealRailway_Icons.dat` | 10 |
| `NetworkAddonMod_Legacy_RoadViaductPuzzlePieceButtons.dat` | 8 |
| `IDS2_VShaped_Steel_Girder_SAM.dat` | 7 |
| `Network_Addon_Mod_Sam_Bridges_Bulk.dat` | 7 |
| `NetworkAddonMod_URail_Puzzle_Plugin.dat` | 5 |
| …plus a long tail across bridge, viaduct and SAM packages | |

**Everything here is correctly authored.** Each icon is a well-formed
four-state strip. The strip widths are simply wider than a stock-derived
pipeline expects: stock icons are `176x44`, while NAM also uses `356x58`.
That is a legitimate authoring choice, not an error.

## Why it interacts with SC4UIScale

`SC4UIScale.dll` renders SimCity 4's UI at 1.5x / 2x / 3x on high-resolution
displays, partly by shipping enlarged copies of stock `.UI` scripts and art.

An ItemIcon is a **four-state strip** and the button picks its cell by
`imageWidth / 4`. When the layer doubles the button cell but the icon is still
supplied at 1x, the cell arithmetic lands mid-glyph: the player sees **two
half-size copies of the icon side by side, and hovering blanks the button**
because the hover cell falls past the end of the bitmap.

**That symptom belongs to SC4UIScale, not to NAM.** With the layer disabled,
NAM's icons render exactly as intended.

## The compatibility layer

SC4UIScale generates 1.5x / 2x / 3x copies of **NAM's own icons** — never
stock substitutes, which would silently replace NAM's artwork with Maxis art
— and ships them as:

    Plugins\zzz-SC4UIScale\z_SC4UIScale_NamIcons-{15x,2x,3x}.dat

`zzz-` sorts after `770-network-addon-mod`, so the enlarged copy wins. Only
one tier is active at a time; the other two sit on disk renamed
`.x1-disabled`.

The whole package is **gated on NAM being installed** — presence of
`NetworkAddonMod_Controller.dat`, checked by exact name. Remove NAM and the
package deactivates itself; it can never inject icons for a mod that is not
there.

Transformation, per icon: LANCZOS upscale to `factor x` the source, with the
**width snapped to a multiple of 4** so the four state cells stay whole
(`356 * 1.5 = 534` is not divisible by 4 — that one rounds to 536). No
recolouring, no re-authoring, no change to any TGI.

## What would retire the layer

Nothing is broken, so there is nothing to fix. The only thing that would
retire this layer is upstream art at more than one scale — a large ask for a
cosmetic edge case affecting people running the game at 2400px+ with a
third-party UI scaler. It is not a request.

One small thing keeps the copies correct across NAM releases: if a future NAM
changes an icon's **dimensions** (not just its pixels), the enlarged copy
becomes a stale picture until it is rebuilt. Sizes are deliberately **not**
checked at load time — a size check would fail the entire package on a
harmless upstream change — so a line in the NAM changelog when icon strip
dimensions change is enough to trigger a regeneration.

## Guard rails

* `tools\uimap\emu\gate_namicons.py` — 392 icons x 3 tiers, 5 negative
  controls. Verifies every TGI is present at exactly tier size, every width
  is divisible by 4, and **no orphans**: no override is ever shipped for a TGI
  NAM does not actually have.
* Section **3b** of that gate re-derives the load-order **winner per TGI**
  across both plugin trees and fails if any third-party file wins an icon the
  package claims to cover. Root-package files load before subfolder files, so
  a stock icon shipped from the SC4UIScale root loses to a NAM copy shipped
  from a subfolder — the Rail button (`0x2A3ED76A`) is exactly that case, and
  the enlarged copy of it ships from `zzz-` for the same reason NAM's own
  icons do. A coverage count alone cannot see this; the winner derivation can.
* NAM's dats are read with the `\\?\` long-path prefix. NAM legitimately nests
  paths to 283–298 characters, past Windows' 260-char `MAX_PATH`; without the
  prefix a plain `open()` throws on files that plainly exist and icons are
  silently missed.

## Provenance and redistribution

The generated packages contain **derivative copies of NAM's artwork**,
enlarged. They are not published in the public repository: the repo ships the
generator, never the art. Rebuilding runs
`tools\itemicons\rebuild_namicons.py` against a local NAM install and produces
the packages there.
