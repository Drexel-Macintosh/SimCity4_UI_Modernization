# Founding a City Changes the Window Set

God mode before a city is founded and god mode inside a founded city are two
different window sets wearing the same mode name. Several windows that are
genuinely hidden, inert, or template-only in an unfounded region become live,
drawing windows once a city exists. Any note describing a window as "hidden",
"never visible", "inert", "a frozen template", or "do not touch" is therefore a
dated observation about one of those two states, not a property of the window.

## Two windows that flip

- `0xABB26B0E` — recorded as a frozen hidden template at Y1045 and placed on a
  scale-in-place list (never move the root). In a founded city it is the live
  god panel. Size-only scaling grew its bottom-anchored stock rect
  (3,1045) 157x488 downward to y=2021 on a 1600px screen — 421px off the bottom
  of the display.
- `0x0A78827A` — recorded as a hidden god sub-tool strip whose docking and
  scaling changed nothing on screen, so it lived in `kGodToolFlyoutIds`, which
  makes the city sweep skip it entirely. In a founded city it is the god toolbar
  (Obliterate City / Reconcile Edges / Disaster / Day-Night, script
  I-aa53e3ea), and it rendered at dead stock 74x291.

## The fix shape

Both cases were repaired the same way: remove the id from the skip lists and add
it to `kGodPanelIds`, which scales by id even when the root reports `vis=0`.
These roots report `vis=0` while their children draw, so visibility-gated
scaling never reaches them.

The standard panel transform

```
y' = f*y - (f-1)*frameH
```

reproduced the previously measured docks exactly, with no tuning:
(5,1071) → (10,542) and (3,1045) → (6,490).

## Working rule

Re-measure in a founded city before trusting any "hidden / inert / template /
do-not-touch" claim about a god-mode window, and prefer a stock control run over
reasoning from screenshots. Baseline vanilla captures taken in an unfounded
region (1280x1024) contain no founded-city data at all, so they cannot answer a
founded-city question. Running `_tests\Set-StockCompare.ps1 -Mode Stock` and
relaunching once settles several questions simultaneously: it showed that god
mode is collapsed by default in stock as well (so the collapsed state is not a
defect), that the expand tab works in stock, and that the four tool buttons it
reveals name the responsible window directly. Screenshot-first guessing produced
two wrong theories before the control run produced the answer.
