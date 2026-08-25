# Upstream note — Scoty Carbon Skin 1.5 and SC4UIScale

This note records what SC4UIScale overrides of the Carbon Skin's data, why,
and the findings from the offline analysis (2026-08-25) that may interest the
author. One genuine defect is reported (§CSI balloons); everything else is
observation.

## What the skin does (as measured)

Scoty Carbon Skin 1.5 replaces the SC4 interface (anthracite/gray): 5 core
dats + per-mod add-on redeclarations. The core carries 673 unique TGIs (403
PNG art, 206 `.UI` scripts, 41 LTEXT, 22 FSH, 1 compression DIR). Its art is
authored at stock 1× dimensions (a handful of sheets deliberately resized as
part of its repositioning). Its `.UI` payloads are QFS/RefPack-compressed
with a proper DIR record. The add-on dats redeclare core TGIs (intra-folder
alphabetical last-wins), which is a clean modular design.

## What SC4UIScale does, and why it is required

SC4UIScale ships pre-scaled copies of stock UI scripts and art so the UI is
born at the selected scale (1.5×/2×/3×) on high-resolution displays. 494 of
Carbon's 673 TGIs are TGIs SC4UIScale also covers. Without adaptation,
whichever side wins the load order is wrong: Carbon winning shows 1× carbon
dialogs inside a scaled UI; SC4UIScale winning shows scaled *Maxis-style*
art punching through the skin.

Resolution (v4.3.0): SC4UIScale builds carbon-styled scaled twins of every
colliding TGI FROM the skin's own payloads (`z_SC4UIScale_ZCarbon*` packages,
armed only while the skin's dats are present at their exact sizes; any skin
update disarms them until rebuilt). The skin's files are never modified, and
the packages are built locally on the player's machine from the player's own
copy of the skin — no redistribution.

## Defect report: the CSI balloon reskins can never display

`scoty_carbon_PNG.dat` reskins the eight U-Drive-It CSI balloon icons at
`{0x856DDBAC, 0x46A006B0, 0x4BB1305D..60, 0x0C0305C3..C6}` — but the
engine's dispatch-vehicle drawer resolves these icons through their
**`0x1ABE787D` twin group**, and the skin ships zero `1ABE787D` copies of
them (verified over the full extract). Stock ships every icon
pixel-identical in BOTH groups. Consequence: the carbon balloon art is dead
data even in an unmodded, unscaled game — the balloons stay Maxis. Fix:
duplicate the eight PNGs into group `0x1ABE787D`. (SC4UIScale hit the exact
same trap once; the two-group law is measured, not theoretical.)

## Observations (not defects)

- The transparency requirement is structural: the skin covers group
  `0x46A006B0` (×371) but few of its `0x1ABE787D` twins (×20), so
  non-transparent mode falls back to Maxis art — consistent with the PDF's
  own note.
- The web-button LTEXT (`{2026960B, 6A231EAA, 0A5128F3}`) already points
  players at Simtropolis; SC4UIScale deliberately does NOT override it when
  the skin is installed.
- SC4UIScale's per-TGI census tooling (`tools/research/carbon/`) can
  regenerate every number in this note from a local copy of the skin.
