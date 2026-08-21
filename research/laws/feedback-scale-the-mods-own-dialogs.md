# Run the Coverage Census in Both Directions

A verification gate that only asks "is what was built still correct?" is
structurally blind to "is there something that was never built?". Both
questions have to be asked, or whole windows sit at 1x indefinitely with every
gate green.

## The blind spot

A large gameplay mod's Village Hall / Town Hall info screen
`{96a006b0,9b868f68}` rendered at 1x under 1.5x fonts — labels cut mid-word,
values printed over them — while every offline gate reported clean.

The reason is scope, not correctness. `build_dialog_static.py` carries a sound
winner assert, but the question it asks is *"is one of the targeted dialogs
owned by a plugin?"* It never asks the mirror question, *"is a plugin's own
dialog scaled at all?"* A mod-**added** window appears in no targets list, has
no stock twin to diff against, and is never built, so every verifier that works
from the target list cannot see it. A gate is only as honest as its scope.

**Method:** for any coverage question, run the census in both directions.
Direction one is "is what was built still correct?". Direction two is
"enumerate what exists, subtract what is handled, name the remainder." The
second direction needs its own instrument that enumerates from the live plugin
tree, not from the build's own inputs. `tools\uiscripts\winning_corpus.py` is
that instrument here: it lists third-party script holders that nothing handles.
A report of unhandled holders is only useful if it is read — the target state
is zero third-party winners, and any nonzero count is a coverage gap, not a
note.

## The crop is a third number and it does not scale itself

Under `blttype=normal` the engine slices `imagerect` out of the bitmap and
blits that slice at the window origin. Scaling the window (285 to 428) and the
bitmap (285 to 429) while leaving `imagerect=(0,0,285,30)` alone paints 285px
of art into a 428px window — every row stripe comes up short.

A blit has three numbers: source size, crop rect, destination size. The builder
scales a rect only when `art_plan` reports that the art was scaled, and
`art_plan` knows the stock art store only, so **mod-supplied art is always
classified "left at 1x" there** and its crops are silently left untouched. The
fix is to reuse the `RUNTIME_BOUND_2X` classification — "the reference is
unchanged but its pixels are scaled" — scoped to the owning package, so
mod-owned rects scale with mod-owned art. A build line reading `rects2x=0` on a
file containing 24 `imagerect` entries is a failure signal, not a status line.

## Mod-supplied art is clipped, never stretched

When a mod supplies its own `GZWinBMP` art, `blttype=normal` means the bitmap
is drawn at its own size and clipped by the window — never stretched. Art and
window therefore do not scale to the same number and cannot: at fractional
factors the rounded window and rounded bitmap differ by the parity of the left
edge (285 becomes 427 or 428 depending on it). This is not an upscaler defect
and must not be "fixed" there.

The question that decides what appears on screen is whether the pixels the
window cuts are a repeat of the last pixels it keeps. Ask it at 1x as well,
because mods deliberately crop several of their own strips.

## Dangling references need an instrument that reads Plugins

Mod data can carry dangling TGI references — `{46a006b0,b5cfffff}`, present in
none of the nine shipped archives nor anywhere in the Plugins tree, appears
after a graph-label typo at `0xFF5D2E9F`. Before calling any reference
dangling, obtain the null from an instrument that reads the Plugins tree as
well as the stock archives, and report a positive control from the same run. A
stock-only null is not evidence of absence; one shipped as a visible defect
here in the form of a 2x2-tiled splash.
