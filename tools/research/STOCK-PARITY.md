# Stock-parity comparison: 800x600 Maxis-stock vs our 2x native (region screen)

Date: 2026-07-22. User's acceptance bar: **our UI at native res should look as
if it were stock.**

## Sources

- STOCK: true 800x600 boot with the ENTIRE scaling stack disabled (remap
  Enabled=0, ScaleAll=0, art dat + 2x FontStyle.ini stashed) — region tree
  dump in `Plugins\SC4UIScale.log.bak-stock800` (01:32:44). First attempt was
  invalid: with only ScaleAll=0 the remap layer went ACTIVE (internal 800x600
  != native panel) and hooked the metric APIs — that is the wrapper path, not
  stock. A clean stock run requires `[Scaling] Enabled=0` too.
- NATIVE DESIGN: 2400x1600 pre-scale region dumps (multiple sessions).
- OURS: the scaled geometry lines from the same logs (v2.5.7+ anchor rules).
- This pass is geometric; pixel-level capture comparison was out of scope
  (exclusive fullscreen on the stock machine).

## Panel-placement comparison (geometric)

| Panel | stock 800x600 | native design | ours (2x) | verdict |
|---|---|---|---|---|
| Legend 0x0BB0F5E7 | (643,392) 152x203, gaps R5 B5 | (2243,1392), gaps R5 B5 | (2086,1184) 304x406, gaps R10 B10 | OK: the game itself uses FIXED pixel gaps at every res; ours = 2x design gap |
| Mini button 0x6BB92BCA | (756,558), gaps R10 B10 | same gaps | (2312,1516), gaps R20 B20 | OK |
| Region panel 0x09EBE9EE | (5,496), L5, bottom OVERHANG -2 | (5,1496), same | (10,1392) 830x212, L10, overhang -4 | OK (overhang preserved since v2.5.7) |
| Options cluster 0x6A91DC15 | (670,0), R15 T0 | (2270,0), R15 | (2140,0), R30 | OK |
| Top cluster 0x6A91DC16 | (170,0) 454x91, center 397 (3px left of screen center) | center 1197 (same 3px bias) | (743,0) 908x182, center 1197 | OK - even the stock off-center bias survives |
| Top flyout 0x09EBEE45 | (18,4) 778x204 (nearly full-width at 800 - CANNOT center) | (818,4), center 1207 (+7 bias) | (429,8) 1556x408, center 1207 | OK - design center preserved |
| Arc strip 0x6A91DC14 | full-width-ish | (623,0) 1154x51, center 1200 exact | (46,0) 2308x102, center 1200 | OK |
| Compass 0xEA8CAD19 | (28,32) | same | (56,64) | OK |

**Panel-INTERNAL geometry: stock 800x600 children coordinates are IDENTICAL
to native-design children coordinates** (legend rows, region-panel fields,
cluster buttons, flyout innards all verified line-by-line). Uniform 2x
therefore preserves internal stock composition exactly.

## Conclusion (geometry)

No outstanding geometric deviations on the region screen. The game's own
layout convention is: fixed pixel corner gaps + centered top elements at any
resolution; our 2x doubles panel, children, and gaps coherently — the result
is exactly "the 800x600 layout built at 2x".

## Follow-on work (settled since this pass)

1. Font rendering: 437 name-form font= tokens converted to GUID form across
   all 23 edited scripts — legend rows (DataInsetLegend x20), flyout
   checkboxes (GenBodyMedium x8), city funds/pop/date/rating, budget, news.
   The GUID rule and its mechanism: `FONTS-AND-DIALOGS.md` Q1.
2. Load Region dialog: static 2x script shipped
   (z_SC4UIScale_DialogStatic.dat); root GZWinGen + buttons have no
   imagerect (engine-fitted). Recipe: `FONTS-AND-DIALOGS.md` Q2.
3. The other five region dialogs (Play/Audio/Graphics/Create/Delete): same
   static treatment.
4. The region screen's full architecture, anchoring law and lifecycle:
   `REGION-SWITCH.md` §0 and `REGION-SCREEN.md`.
