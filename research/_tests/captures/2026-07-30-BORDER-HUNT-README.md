# PAUSE-BORDER HUNT — saved evidence (task #59, UNRESOLVED / SKIPPED)

Captured 2026-07-30 late. **Do not re-run the probes below — their answers are
here.** Full write-up: `_tests\REGRESSION.md` "THE PAUSE BORDER: DECODED TO A
DEAD END"; live state in task #59.

## The defect
At tier 2 (2400x1600) the paused-state indicator draws in **raw screen pixels**:
a ~2-3 px gold frame around the whole screen plus a ~24 px pause badge at the
top-left corner. Neither scales with the tier. User screenshots 2026-07-30.

## Files here
| file | what it is |
|---|---|
| `2026-07-30-border-hunt-vistrace.log` | the v2.36.10-borderhunt session: `VIS primed - 840 windows`, the pause/unpause cycles, the 70 buffer-class blit lines, and the (unarmed, then armed) EdgeBlt run |
| `2026-07-30-border-hunt-SC4UIScale.ini` | the exact probe configuration used (`[Probe] VisTrace=1`, `EdgeBlt=40`, `EdgeDump=0`) |

## What the evidence proves
1. **Not a window.** 840 windows baselined from the MAIN window at FULL depth;
   BOTH arrival mechanisms tested (visibility flips AND newly-created windows).
   Across repeated pauses the only change is `0x2AAB8CC1`, the sub-flyout
   tooltip tip layer. The sweep was provably alive (11 `BMPX` lines).
2. **No badge-sized window at the screen corner** in any dump.
3. **⚠ The `EBLT` zero is NOT evidence.** With the class-Blt hook armed, every
   destination was panel-sized (258x482, 383x156, 360x156, 340x148, 323x156,
   317x148, 280x148) and **none screen-sized** — the UI buffer class never
   composites to the screen, so that detector could not have seen a full-screen
   border even in principle.

## Offline decode results (no files needed to reproduce)
- **No border/badge art exists** in the extracted set: every PNG 8..80 px
  scanned at two gold thresholds (25 %, then 7 %). Hits are progress swatches
  (18x14 solid gold), the 36x41 `fa8cdfc4..ce` portrait-cell family, a solid
  32x32 gold circle, a gold triangle. No edge tile, no pause glyph.
- **9-slice helper `0x8D8800` has exactly 6 callers** — `0x99971A`, `0x9B061E`,
  `0x9BC439`, `0x9BEC32`, `0x9C2C1F`, `0x9CA297` — all ordinary UI widget
  classes, none a full-screen painter.
- **Both anonymous full-screen classes excluded by their own code.**
  `vt 0x00AB8CD0` (Plot `0x7AB130`): animating list — ctor floats 300.0/5.0/3.0,
  counts 10/32, Plot iterates a collection with fld/fadd scroll math.
  `vt 0x00AB8F50` (Plot `0x7AB590`): 3-line wrapper delegating to
  `[this+0xd8] vt+0x54`.
- Dead ends not worth repeating: the `+0xF09` flag on singleton `0x00B43CD8`
  is set from exemplar properties `0x4A7F19F3/F4` (a preference, not a border);
  `0x73283C` is CODE, not a string; a colour-table scan returned 508 false
  positives from opcode bytes — noise, not data.

## CONCLUSION
The border and badge are painted in the game's **3D / present path**, outside
every mechanism this project owns — the same category as #72 (region bubble
double bar, "not ours, needs the exe paint routine").

## The only remaining foothold, if this is ever resumed
Everything visible must pass through the **DirectDraw primary surface**. A
hook on that surface's `Blt`/`BltFast`, logging thin rects flush to a
screen-sized destination, would catch the border on its first frame — which is
exactly what all six UI-side probes were structurally unable to do.
**Weigh first:** it is a new subsystem for this project (every existing hook
targets the game's own UI classes), it goes through dgVoodoo — the wrapper the
working 2x setup depends on — and the prize is a 2 px line. Gate it off by
default, log-only, no transforms, with a revert path.

## Probe levers (all returned to 0; re-arm only if resuming)
`[Probe] VisTrace` — full-depth visibility + creation trace, cap 300 lines.
`[Probe] EdgeDump` — full-screen window set, both roots, on change.
`[Probe] EdgeBlt`  — thin edge blits through the UI buffer class (see the
warning above: it cannot see the screen surface).
