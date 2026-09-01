# Row 10 — building/lot selection glow on query & demolish hover

> **CURRENT GRADE: ATTRIBUTED** — RENDERER_DRAW, per-occupant tint, 2026-08-30.
>
> ⛔ **The dated header below is the ORIGINAL session's grade and is
> superseded.** It is kept rather than rewritten because this project
> annotates history instead of editing it — but the front door
> (`docs/DECOMPILATION-STATUS.md`) grade-scans the top of this file, so
> the line above is the one that counts. See the MEASURED section at the
> end of this file for what changed and how it was proven.

**Session 2026-08-17. Grade: PARTIAL (static disassembly only — no screen or
live-capture proof yet). Every VA below read from the shipped exe this
session** (`SimCity 4.exe` 1.1.641 Steam, ImageBase 0x400000, LAA-flipped /
code-identical).

## VERDICT

The hover glow is the **occupant highlight flag** — candidate 3 of the row's
list ("an occupant flag the renderer tints"). It is NOT an effect spawn and
NOT a pick-path visual:

- `cISC4Occupant` carries `GetHighlight()` / `SetHighlight(uint32 mode, bool
  sendMsgNow)` at vt+0x40 / vt+0x44
  (`vendor\gzcom-dll\gzcom-dll\include\cISC4Occupant.h:57-58`).
- The **query tool** control (clsid `0xC7AF928E`, ctor `0x4C4590`, vtable
  `0xA90A88`, object size 0xA0) hover-swaps a single occupant:
  - `0x4CBF83` `mov [this+0x2C], newOccupant` (hover target cached)
  - `0x4CBF90` `call [vt+0x40]` GetHighlight → `0x4CBF98`
    `mov [this+0x40], eax` (old value saved)
  - `0x4CBF9D-0x4CBF9F` `push 0; push 7; call [vt+0x44]` —
    **SetHighlight(7, false)**
  - leave/clear path `0x4CBF65-0x4CBF6D`: `push 0; push [this+0x40];
    call [vt+0x44]` — restores the saved value, then Release `0x4CBF7E`.
- The **demolish tool** control (clsid `0x46DDB5F1`, ctor `0x4B9070`, vtable
  `0xA901A0`, object size 0xD8) does the same swap with **mode 5**:
  - `0x4B99E9` GetHighlight → `0x4B99EE` `mov [this+0x78], eax` (old saved)
  - `0x4B99F6-0x4B9A00` `push 0; push 5; call [vt+0x44]` —
    **SetHighlight(5, false)** (twin encoding at `0x4B9A07`, same args).
- The **mayor-mode default control** (ctor `0x4DAE80`, vtable `0xA92CA8`,
  size 0x98, built at `0x7E6DBD`) highlights EVERY occupant of the hovered
  lot in a loop — `0x4DB34A-0x4DB350` `push 0; push 5; call [vt+0x44]` —
  and clears with mode 0 at `0x4DAD7E`. Its Init (`0x4DA6C0`, vtable slot
  `0xA92CB4`) additionally spawns ONE `local_tile_outline` effect
  (name str `0xA92C80`, pushed `0x4DA77A`) via effects-manager
  `[0xB43D1C]` vt+0x1C, cached at `[this+0x94]` — the hovered-tile outline
  that rides along with the default pointer.
- Tool identity is byte-proven from the command dispatcher at `0x7F26A9`:
  `sub edi, 0x6A935CF3` (= **QueryTool** id, name table pair at .data
  `0xB0DF40`) `je 0x7F2783` → new(0xA0) + ctor `0x4C4590`; the `-0x42` case
  (= **DemolishTool** `0x6A935D36`, pair at `0xB0DFDC`) checks the live
  control's clsid `0x46DDB5F1` at `0x7F26CC` and news 0xD8 + ctor `0x4B9070`
  at `0x7F26EA`.

The flag's state machine lives in the occupant itself: `0x80D580`
(vtable slot .rdata `0xABEAE8`, module 0x80Dxxx = the concrete occupant
class) — reads current state, self-resolves the placeable/render object
(`vt+0x50` at `0x80D58E`), applies to it, and posts
**kSC4MessageOccupantHighlightChange = GUID `0xE6E85114`** (string .rdata
`0xA8AE74`, name→guid pair .data `0xB0871C`; message object alloc 0x2C +
GUID push at `0x80D600` — the ONLY code ref to that GUID in the exe).
Reading `0x80D580` as `cSC4Occupant::SetHighlight` is PLAUSIBLE, not
slot-proven: my vtable walk-back start (`0xABEA98`) may have fused with a
preceding table, so its slot index is unadjudicated. The renderer-side
mode→tint mapping (what color mode 5 vs 7 paints) was NOT located this
session — UNKNOWN.

## Ruled out (each with its positive control)

1. **Effect-family spawn for the hover glow** (candidate 2): the EFFDIR name
   census (scratch scan of the rescued extract
   `tools\research\effdir\T-ea5118b0_G-ea5118b1_I-00000001.png`, 2,431
   length-prefixed names — positive control: it finds all 18
   `mission_selection_*` and both `selection_blue/red`) has NO
   hover/highlight-named record consumed by the query/demolish path. The
   `selection_{blue,red}` effects that DO exist in the exe are pushed only at
   `0x4C2326` / `0x4C2531` inside `0x4C2090` (sole caller `0x4C2D45`, fn
   `0x4C2660`) — a per-CELL vector spawner (instances at obj+0xEC / +0xF8)
   belonging to a different control family (embedded vtable `0xA90728`,
   written at `0x4BF9EC`/`0x4C0465`) — cell previews, not the hover glow.
   `selection_green` does not exist as an exe string at all; the exe's
   `selection_yellow` string (`0xA83A3C`) is a CONFIG-KEY in the 9
   property-registration blocks at `0xA7076C`, `0xA70E7C`, `0xA713FC`,
   `0xA7197C`, `0xA7572C`, `0xA75CAC`, `0xA7622C`, `0xA76F3C`, `0xA779DC`
   (neighbors: `decal_color`, `window_offsetX`, `zoomLevel`, `cameraX` —
   a parameter block, registrar `0x407FA0`, this `0xB20CF0`), not an effect
   spawn.
2. **Live effect route (BUBBLEALL)**: `_tests\captures\SC4UIScale-2026-08-17-*.log`
   BUBBLEALL lines (unfiltered CreateEffectByName census; positive control:
   16 distinct names captured incl. `atmospheric_effects`, `helipad`,
   `copter_spotlight`) contain zero selection/highlight/outline names. ⚠
   SCOPE LIMIT: nothing proves the query/demolish tools were hovered during
   those captures, so this null is consistent-with, not proof-of, the
   flag mechanism.
3. **Window world**: not re-tested here; the row inherits the doc's §1
   two-worlds law — no window census has ever shown a window tracking a
   hovered building, and the tint follows the 3D model through camera
   rotation (player-observable). Formally owed with the live probe.

## Related but NOT this row

- `0x4B8880` pick-Accept + `0x4B8A00`/`0x4B8A38` ray-pick (§2.4) — ⚠ the
  §2.4 CARRIED note calls vtable `0xA901A0` "the offer view-input-control";
  this session byte-proved `0xA901A0` is installed by ctor `0x4B9070`, the
  object the dispatcher builds for **DemolishTool**. Either the carried label
  or the carried VA is wrong — re-derive before using either. (Not
  adjudicated here; out of row scope.)
- The mayor-view pick chain `0x4D7820` (row brief's starting point): sole
  direct caller `0x4D7ACF` in virtual fn `0x4D7AC0` (vtable slot `0xA928F0`)
  — a THIRD class in the same module, likely the shared pick base of the
  0x4DAxxx control family. The hover state it computes feeds the
  default-control loop that calls SetHighlight(5).

## SIZING

No number of ours exists on this path. The glow is a per-occupant MODE
(0 / 5 / 7 observed), applied to the occupant's own render model — the
"size" of the visual is the building/lot model itself, i.e. **world-anchored
by construction**. The companion `local_tile_outline` effect is an EFFDIR
child record (world units, shipped scale 1.0, zoom ramps) — also
world-anchored. There is no screen-px constant, no per-zoom px table, no
EFFDIR scale ≠ 1 anywhere on the row-10 path.

## TIER CALL

**Stay (n-a).** At 1.5x/2x/3x the tint covers exactly the model's pixels at
any resolution and the tile outline is camera-scaled; both are correct at
every tier without us. Patching anything here would be wrong (§2.4's
never-patch hover-quad law generalizes).

## LIVE PROBE (to promote PARTIAL → DOCUMENTED)

One naked, log-only detour at **`0x80D580`** (stock prologue
`51 55 56 8B 74 24 10 57 8B E9` — verify bytes before writing; 7+ patchable
bytes). Per the thiscall-hook rule: naked stub, save all regs, log raw
`(ecx, [esp+4], [esp+8])` = (occupant, dwHighlight, bSendMessageNow),
tail-jmp to a relocated prologue. Expected positive control: with the QUERY
tool, sweeping the cursor across one building yields a `dwHighlight=7` line
on enter and a restore line (old value, usually 0) on leave; DEMOLISH hover
yields 5/restore; the default mayor pointer yields one 5-line per lot
occupant. If hover produces NO lines while the glow visibly appears, the
concrete occupant class in play overrides SetHighlight elsewhere — widen by
logging the vtable ptr of `ecx` on the query control's cached occupant at
`[queryCtl+0x2C]`.

## Dead ends / loose threads for the next session

- Mode→tint color map (renderer side): untouched. Entry points: the
  placeable object resolved at `0x80D58E` (self vt+0x50) and the apply call
  `0x80D5A0` / `0x80D5CE` (vt+0x44 / vt+0x60 on the resolved object).
- Highlight-mode enum: 0=off, 5=demolish+default-hover, 7=query-hover; other
  values unknown (network tool header mentions occupant highlights too —
  `cSC4NetworkTool.h:145`).
- The `0xA90728`-interface cell-preview class (selection_blue/red spawner
  `0x4C2090`) — identity unproven (zone/network drag preview candidates);
  its callers: `0x4C3052`, `0x4C3104`, `0x4C321C`, `0x4C3663`, `0x4C36DE`.
