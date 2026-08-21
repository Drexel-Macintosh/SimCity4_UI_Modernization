# City Situation Indicator Geometry

The blue offer balloon that appears above a U-Drive-It vehicle is a **City
Situation Indicator** (CSI), category 4 of the game's dispatch-indicator
system. It is the only in-world overlay in SimCity 4 that the player clicks,
so its geometry is both a visual and an input concern. A fuller write-up of
the indicator system lives in
`tools\research\CITY-SITUATION-INDICATORS.md`.

## Addresses

| Role | Address |
| --- | --- |
| Drawer, `cSC4DispatchVehicleView::Draw` | `0x0046D990` |
| Geometry builder | `0x0046C8B0` |
| `AddIndicator` | `0x0046F240` |
| Call site into the builder | `0x0046F616` |

The drawer was identified by suppression: patching it to draw nothing removes
the balloons from the screen and nothing else.

## Two quads, not one

The indicator is built from **two independent quads**, each with its own size
lever. Any fix that changes only one of them produces a half-scaled indicator
that still looks broken, which is the single most expensive trap in this area.

**Pin / backing quad, 64x64.** Eight `±32.0f` immediates, encoded as
`C7 84 24 …` with the immediate at instruction+7:

```
0x0046EABD  0x0046EACA  0x0046EAF6  0x0046EB01
0x0046EB2D  0x0046EB38  0x0046EB64  0x0046EB6F
```

**Icon quad, 35x35 — and this quad's size is also its click box.**
`mov eax,0x420C0000` at `0x0046CC47`, immediate at **`0x0046CC48`**, inside
the CSI-only branch guarded by `cmp [esi+4],4`. The value is stored to both
the record's width and its height (`+0xD0` / `+0xD4`); the drawer then halves
them to `±17.5`. Because the same field drives hit-testing, changing the icon
size moves the clickable region with it — growing the icon without accounting
for that changes where the player must click.

**Do not patch `0x0046CCB9`.** It is the identical instruction carrying
`32.0f` on the **non-CSI** branch. It is a tempting match for any byte or
pattern search and belongs to a different indicator category.

## Why constant sweeps never found these

Both levers are **inline immediates inside `.text`**, not entries in `.rdata`.
A data-section constant sweep is structurally blind to them and returns an
honest null however carefully it is run; the search has to disassemble the
branch, not scan the constant pool.

A related false lead: `0x00A8819C = 42.0f` is a live, frequently-read
constant near this code, but it feeds the quad's **translation**, not its
extent. A constant can be genuinely live and still be the wrong constant.

## Art

Eight PNG strips, type `0x856DDBAC`, each 152x38 — four 38x38 states laid out
horizontally:

| Instance | Vehicle |
| --- | --- |
| `0x4BB1305D` | car |
| `0x4BB1305E` | helicopter |
| `0x4BB1305F` | police |
| `0x4BB13060` | ferry |
| `0x0C0305C3` | sail |
| `0x0C0305C4` | plane |
| `0x0C0305C5` | tank |
| `0x0C0305C6` | train |

**Each strip exists twice, pixel-identical, in two groups:
`0x46A006B0` (the group actually drawn) and `0x1ABE787D`.** A tracer scoped to
only one group reports the art as untouched and wrongly exonerates it; scope
any art-side instrument to both groups before believing a null.

The set of eight is provably complete: all four automata LUA resources were
QFS-decompressed and every `csi_image` reference extracted, giving 8 of 8
covered.

## Implementation

The runtime patch ships as `ApplyCsiIndicatorScale` in `src\CodePatches.cpp`.
It is **both-or-neither** — it applies the pin and icon levers together or
applies neither — and tier-general, deriving both sizes from the active scale
factor rather than from per-tier tables. Scaled art ships as
`tools\packages\{15x,2x,3x}\z_SC4UIScale_CsiIcons-*.dat`.

## Scope note

The eight pin immediates are **not category-guarded**. Other dispatch-indicator
categories reach the same backing quad, so scaling the pin affects them too.
Only the icon lever at `0x0046CC48` sits behind the `cmp [esi+4],4` CSI test.
