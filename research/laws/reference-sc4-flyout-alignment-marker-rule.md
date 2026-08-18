---
name: reference-sc4-flyout-alignment-marker-rule
description: "THE rule SC4 uses to place every tool flyout: each flyout script has a hidden 0x0000AAAA child sized like its SPAWN BUTTON, and flyoutPos = spawnButtonAbs - markerOffset. Reproduces all 3 hand-tuned god docks to the pixel. Use it instead of eyeballing offsets."
metadata:
  node_type: memory
  type: reference
  originSessionId: f1160943-a698-434b-a6bf-d3c3e2971cea
  modified: 2026-08-02T23:06:53.535Z
---

Found 2026-07-28 while docking mayor-mode flyouts. It ends the offset-guessing
that cost ~15 build cycles on god mode.

**THE RULE.** Every tool-flyout .UI script contains a hidden child
`id=0x0000AAAA` whose size equals its SPAWN BUTTON's size. The game positions
the flyout as:

    flyoutPos = spawnButtonAbs - markerOffset

so after the subtree has been scaled to 2x, the correct dock target is:

    target = spawnButtonAbs - markerOffset(LIVE, i.e. already scaled)

**Why trust it (three independent confirmations):**
- It reproduces ALL THREE locked, hand-tuned god docks to the pixel:
  terraform (22,262), terrain-fx (22,502), day/night (22,742). 7-for-7 across
  flyouts and modes.
- It predicted the game's native mayor placement exactly: Landscape marker
  (3,27) at 1x, button abs (28,398) -> (25,371) = what the MCAL log measured.
- Two separate derivations agreed on the same target (22,344): `button + 2R`
  where R = native - buttonAbs, and `button - marker2x`.

**It also explains the special case the constant table could not.** The shared
window 0xCA35CBED needed two different offsets (terrain-fx 40 / day-night 160)
because the container swaps SCRIPT, which moves the marker. The rule handles
that with no special case.

**COROLLARY (2026-07-29 evening, cost one bad deploy): MARKERS ARE
POSITIONING DATA — NEVER SCALE THEM ANYWHERE.** Not at runtime (the
original rule) and NOT IN SHIPPED .UI DATA either: v2.20.0 pre-scaled the
advisor strip's whole subtree including its 0x0000AAAA marker, and the
game (which reads the marker at NATIVE units) placed the whole Advisors
box shifted by exactly -(markerOffset) = -(229,63). double_subtree_areas
in build_selective_safe.py now skips id=0x0000AAAA tags; any future
data-side subtree scaling must do the same.

**Trap it exposes:** one window id can have TWO scripts. `0x49923239` is
god/terraform (125x291 -> 250x582, marker (4,90)) AND mayor/Landscape Tools
(125x249 -> 250x498, marker (3,27)). A single fixed offset can never be right
for both - gate by mode (mayor HUD 0xE9889775 visible) or read the live marker.

**Mayor-mode map (measured):** buttons of toolbar 0x69E40A1F, identified by
POSITION not enum order (the dump enumerates children in REVERSE of .UI add
order): 1 Landscape 0x8991EE08, 2 Zones 0x0991EE13, 3 Transportation
0xA994824D, 4 Utilities 0xE991EE2F, 5 Civic 0x0991EE39, 6 Bulldoze 0xE999C820,
7 Emergency 0x6991EE42. Flyouts: Landscape 0x49923239, Zones 0x69923479,
Transport 0xC99237A0, Utilities 0xE992F711, Civic 0x699306ED, Emergency
0x0992FD17.

**How to apply:** measure with the MCAL log line (ini `[Flyout] MayorDock=0`
scales but never moves a mayor flyout and prints native pos, spawn-button abs,
derived R and the resulting target). Paste R into `kMayorFlyoutDock` in
`src\UiSpike.cpp` and set derived=true. Never tune by screenshot - that is what
produced two wrong Landscape values in one session.

**Gotcha:** only Landscape reaches the flyout dock loop. Zones/Transport/
Utilities/Civic fall through to `ScalePanelRoot`'s CENTER-ANCHOR branch
(fires when gapT and gapB both exceed frameH/4), which repositions them with no
reference to their spawn button - so they are not "off by a constant", they are
placed by an unrelated rule. Docking them requires intercepting that path.

**THE SHARED SUB-FLYOUT CONTAINER `0x8A6E61E0`** (second-level menus: zone
density, road types) does NOT follow the marker rule - it has no marker. Its own
rules, all measured:
- PLACEMENT LAW (v2.16.0, residual ZERO on both menus checked): the game puts
  it at `nativeY = buttonCentreY - ringBltY - 29`, `nativeX = buttonAbsX + 20`,
  where ringBltY is where THAT menu blits its 1x ring sprite into the buffer
  (94 zones/roads, 119 rails - it VARIES per menu). The earlier constant
  `btn + (20,-86)` was this law at ringBltY=94 and silently failed 4 transport
  menus (rails & depots etc.); the DLL now records ringBltY at blit time and
  computes native from the law. The dock delta (-53,-24) is menu-invariant
  (native and target both shift with ringBltY). Also: the container can be as
  short as 258x286 - the destIsContainer height gate must stay >260, not >300,
  or short menus get no 2x ring at all.
- Its class IS the disaster container `0x00AB6AA8` (strip child `0x00AB6D88`),
  so every disaster fix applies verbatim: buffer force-recreate for the 1x bar,
  strip item-field doubling for unseated icons, and ClaimScale+SelForce for the
  right-half-only clicks.
- Dock it to `btn + (-33,-110)` so the 2x ring lands on the button while the
  ring/strip/bar stay welded (they are adjacent inside the buffer by
  construction - moving the ring alone tears them apart).
- `gBarDX=-53` is GENERIC (one bar-art width; the bar is drawn flush right and
  widening it 2x overruns the buffer), NOT a disaster-only tweak.
- Its ring nudge SubRingDX=25/SubRingDY=-6 is DERIVED (2026-07-29), not
  dialled: the 80x53 sprite is a KEYRING whose magenta hole (centre (25,26))
  must frame the button's OFF-CENTRE ellipse (centre (21,15) in its 47x37
  cell) - button art being off-centre in its cell, not sprite padding, is why
  box-centre math was 4-5px off. Re-derive after any SubDock change:
  `python tools\flyout-sim\derive_subring.py` (asserts art + expected values;
  the atlas is plain DBPF art `I-14215ed0..ed5`, no in-game dump needed).

- DEEP SUBMENUS are a third-party plugin (memo.submenus.dll 2.1.0, source
  cloned to tools\research\submenus-dll-src). Its "back" = CLICKING THE
  PHYSICAL BUTTON (the red arrow is just frame art that overlaps the button
  at 1x); v2.17.0 forwards clicks on the drawn arrow's rect to the button as
  a real OS click (ArrowClick=1). Its 55 own Item Icons needed 2x overrides -
  un-overridden 176x44 icons render DUPLICATED in 2x cells (game slices the
  strip by the doubled 88px cell).
- **SC4 LOAD-ORDER LAW (proven live, cost one failed deploy): Documents-root
  FILES load BEFORE subfolders — a root z_*.dat can NEVER override a dat in
  a subfolder.** Overriding another Documents mod needs a FOLDER sorting
  after the target ("zzz-SC4UIScale\" beats "150-mods\"); root packages only
  beat INSTALL-dir resources. ALL plugin-bound icons (124 = 55 submenus-mod
  + 69 CAM/Maxis-landmark) ship in
  zzz-SC4UIScale\z_SC4UIScale_ItemIconsSub-2x.dat (tier-gated, v2.17.1).
  When scanning plugin exemplars for Item Icons, parse BOTH formats - CAM's
  are ~half TEXT exemplars; binary-only parsing missed 30 icons.
- The sub-flyout container is identified by EXACT WIDTH (selfW==258,
  selfH>=100). Height-only gates missed the 258x206 Freight nested menu
  TWICE (300 then 260) = 1x disconnected circle on that menu only.

⚠ **THE MARKER'S UNIT SYSTEM MUST BE MEASURED, NOT ASSUMED** (v2.47.0). The
live marker's `GetL()/GetT()` are NOT reliably in screen units: the invisible
`0x0000AAAA` child is not always reached by its flyout's subtree scale, and
that state is PERMANENT, not a startup race. Measured with WarriorUI in:
`0xAB954023` script marker (4,5) read live (8,10) = SCALED, while
`0x49923239` script (3,59) read live (3,59) = DESIGN, still design a second
and many sweep ticks later. Subtracting design units from a screen coordinate
put the Landscape ring 59px low, on the WRONG CIRCLE — while `MCAL` printed
the right target all along (it scales its offset; the dock did not). Decide
with `UiSpike::MarkerIsDesignUnits()` — a PURE READ of `scaleMap`, never
`Classify()` (which mutates the tug-of-war counter and can tombstone a window
just for being asked). ⛔ Do NOT use the marker's size against its spawn
button as the discriminator: "the marker is sized like the spawn button" is
TRUE ENOUGH TO MISLEAD and false in detail (S&L's marker is 64 wide against a
47-design button, scoring 34 vs 30), so it guesses wrong and does it
silently. We RECORD what we scale — ask the record, not the geometry.

Full write-up incl. the instruments (MCAL/SCAL/SVT/SBLT/RCAL):
`tools\research\MAYOR-MODE.md` top section "SESSION STATE 2026-07-29".

Related: [[project-sc4-god-flyouts]], [[reference-sc4-flyout-hittest-playbook]],
[[feedback-sc4-founded-city-invalidates-notes]], [[project-sc4-ui-scaling-northstar]],
[[feedback-sc4-measure-dont-infer]]
