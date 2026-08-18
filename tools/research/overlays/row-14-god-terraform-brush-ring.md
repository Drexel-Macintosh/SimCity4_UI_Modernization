# Row 14 — god-mode terraform brush ring (in-world cursor circle)

**Session 2026-08-17, static attribution pass. Grade: PARTIAL (no live capture
was possible — read-only session, game never launched). Every claim below is
byte-read from the shipped exe / a durable extract in this session; nothing is
carried from volatile notes.**

Binary facts: `SimCity 4.exe` 1.1.641.0 Steam x86, ImageBase 0x400000.
Sections (read this session from the PE header): `.text` raw 0x7000 va
0x407000 size 0x679000; `.rdata` raw 0x680000 va 0xA80000 size 0x87000.
EFFDIR extract: `tools\research\effdir\T-ea5118b0_G-ea5118b1_I-00000001.png`
(1,094,484 bytes, the QFS-decompressed EFFDIR TGI
{0xEA5118B0, 0xEA5118B1, 0x00000001} from `SimCity_1.dat`). All EFFDIR
offsets below are into that decompressed blob.

**Scope guard — NOT this row:** the WarriorUI terraform ring (third-party
flyout BUTTON ring, window world, `[R:3883]`) and the disaster-flyout ring
sprite (screen-space sprite, §2.6) are different, already-documented visuals.
This row is the STOCK circle drawn ON TERRAIN under the cursor while a
god-mode terraform brush (raise/lower/level/smooth) is selected.

---

## VERDICT

**Owning system: the Swarm effects manager (§2.1), via a dedicated
"cursor effects" / brushEffect family defined in the EFFDIR (§2.2).**
The brush cursor visuals are named effects — `mountain_tool_active`,
`valley_tool_active`, `level_tool_active`, `smooth_tool_active` (+
`_inactive` twins, + `mayorlandscape_tool_*` for the mayor-mode landscape
brush) — each a parent effect whose children are `_normal` / `_invert`
terrain-decal variants. Renderer-world, not a window; no census generation
has ever shown a window at the cursor in city view.

## EVIDENCE

1. **The effect family exists, and ONLY in the EFFDIR.** Name→index map
   entries (map layout `[u32 len][name][u32 index]`, walked 869 entries from
   blob 0x104E28 to the `end`/0xFFFFFFFF sentinel at 0x10A964 this session):
   - `mountain_tool_inactive`=24 (map entry at blob 0x104E28),
     `mountain_tool_active`=25, `valley_tool_inactive`=26,
     `valley_tool_active`=27, `level_tool_inactive`=28,
     `level_tool_active`=29, `level_icon_active`=31,
     `smooth_tool_inactive`=32, `smooth_tool_active`=33,
     `flora_tool_inactive`=36, `flora_tool_active`=37,
     `fauna_tool_inactive`=40, `fauna_tool_active`=41,
     `mayorlandscape_tool_inactive`=42, `mayorlandscape_tool_active`=43,
     `road_tool_inactive`=44 — a CONTIGUOUS cursor-effect index block 24–44.
     Also `torch_active`=325, `torch_inactive`=326 (see 5).
     Related names in the same blob: `level_arrow_select_{north,south,east,
     west}_{active,inactive}`, `road_cursor_particle_inactive`,
     `*_coverage_circle_*` (census row 11's family — same subsystem).
2. **Child-reference records (decoded this session, builder layout
   `[u32 nameLen][name][u8 type][u32 flags][9f rot][3f trans][f SCALE]
   [u8 zmin][u8 zmax][u16 copies][u16 mult][4f ramps][2 u16][u32 idx]`):**
   - `mountain_tool_active_normal` blob 0x0A15BB: type=1, flags=0,
     rot=identity, trans=(0,0,0), **SCALE=1.0**, ramps (0,1,1,1).
   - `mountain_tool_active_invert` 0x0A1635, `mountain_tool_active2_normal`
     0x0A16AF, `mountain_tool_inactive_normal` 0x0A14A3 (+4 more sites),
     `valley_tool_active_normal` 0x0A1AB8/0x0A1FAD/0x0A38A6,
     `fauna_tool_active_normal` 0x0A54CD, `flora_tool_seeds` 0x0A528D
     (type=0 = particle class), `mayorlandscape_tool_active_normal`
     0x0A57EF — ALL identity transform, ALL SCALE=1.0.
   - The whole family clusters in blob 0x0A14A3–0x0A57EF — the cursor-
     effects section of the visual-effect definitions.
3. **The exe's effect-description keyword table names the machinery.**
   `.rdata` keyword run (all read this session):
   - `brushEffect` VA **0xA9F680** — an effect CLASS in the Swarm language,
     listed with visualEffect/decalEffect/soundEffect/etc. (0xA9F608–0xA9F6FC).
   - brushEffect properties: `brush` **0xAA0888**, `width` **0xAA0878**,
     `apply` **0xAA0880**, `ring` **0xAA078C**; error string
     `No such brush: '%s'` **0xAA0864**; `brushID` **0xA9F778**.
   - `apply`-op tokens = the terraform verbs themselves: `mountain`
     **0xA9F3D4**, `valley` 0xA9F3C4, `level` 0xA9F3BC, `smoothen` 0xA9F3B0,
     `erosion` 0xA9F3A8, `volcano` 0xA9F3CC, `pothole` 0xA9F2B0, `ground`
     0xA9F3F8 — plus decal draw modes (`decalNoOverlap` 0xA9F398,
     `modulate`/`additive*`/`depthDecal*` 0xA9F400–0xA9F460).
   - Keyword consumers in `.text` (sole refs, found by imm32 scan):
     `ring` → **0x5A1F12**; `brush` → **0x5A2E2D** (byte-verified this
     session: `0x5A2E2C: 68 88 08 AA 00 push 0xAA0888` — property fetch);
     `width` → **0x5A2FA2**; `No such brush` → **0x5A3065**, preceded at
     **0x5A305B** by a 20-byte-stride table lookup
     (`lea ecx,[eax+eax*4]; mov eax,[edx+ecx*4+4]`) = the named-brush
     resolver. All inside the effect-class reader region just below
     `ReadChild` 0x5AB690 (§2.2).
4. **The renderer names the subsystem.** Flag string `kUseCursorEffects` VA
   **0xABB850**, registered at **0x7DFDD1** (byte-verified:
   `68 50 B8 AB 00 push 0xABB850`), in the same registry block as
   `kRenderDecals`/`kRenderTerrain`/`kRenderAutomata` (0xABB708–0xABB9D0).
   Maxis's own name for this visual family is "cursor effects".
5. **Sibling proof that the family spawns by name:** `torch_active` /
   `torch_inactive` (volcano-cheat cursor, indices 325/326) ARE exe string
   literals at VA ~0xA9EBB8 (file 0x69EBB8), beside `volcano_control`
   0xA9E9E0 — this family is CreateEffectByName-driven where the exe holds
   the name.

**Nulls, each WITH its positive control:**
- `mountain_tool*` etc. appear NOWHERE in game data outside the EFFDIR:
  full decompress-scan of every entry of every discovered .dat (11 DBPF
  files under the install dir, 111k+ entries, QFS-decompressed via
  `tools\uimap\emu\qfs_ab.py`, both size classes, ASCII + UTF-16LE).
  POSITIVE CONTROL: the same scanner found the names inside the EFFDIR
  entry of `SimCity_1.dat`.
- The names are NOT exe literals, and no `%s`-style composition is possible:
  `_tool` occurs in the exe exactly once (inside `mysim_dispatch_tool`),
  `_tool_active` zero times. POSITIVE CONTROL: the same scan finds
  `torch_active` and the UDI `mission_selection` literals.
- ZERO direct `E8` call sites of `CreateEffectByName` 0x5939B0 in `.text`
  (full scan) — all callers go through the service vtable, so a static
  caller census cannot name the spawner. POSITIVE CONTROL: the BUBBLEALL
  instrument logs live callers by return address (8 distinct ret addrs in
  the 2026-08-17 captures).
- No capture shows a tool-cursor spawn — but NO captured run ever had a
  terraform brush selected (the 08-17 runs were mayor-hat regression tests).
  POSITIVE CONTROL: BUBBLEALL in those same logs records helipad/rotor/
  copter spawns, so the hook sees the channel. This null is scope-limited,
  not evidentiary.

**Consequence of the nulls:** how the game selects `mountain_tool_active` at
runtime is UNKNOWN — either the name pointer comes out of the loaded EFFDIR
name map itself, or spawn is by INDEX through a non-name API (the contiguous
24–44 block invites hardcoded indices). If by-index, it would BYPASS the
0x5939B0 name hook — the live probe below adjudicates exactly this.

## SIZING

- Per-child EFFDIR SCALE float = **1.0** (world units) for every record in
  the family (offsets in EVIDENCE 2; the float sits at nameEnd+53, the
  byte the v3.0.4-era data lever would patch — structurally inert as a
  plugin override per the §2.2 load law).
- Zoom ramps (0.0, 1.0, 1.0, 1.0), zmin=zmax=0 — no per-zoom size steps.
- The ring DIAMETER is the brush footprint: brushEffect `brush`/`width`
  data resolved through the 20-byte-stride brush table at **0x5A305B**
  (record layout unread — deliberately UNKNOWN, a work item).
- NO screen-pixel constant exists anywhere on this path (contrast the
  signpost 44.0f push at 0x5F20AF or the marker-strip table 0xAA523C —
  nothing of that shape references this family).

## TIER CALL

**Stay (world-anchored) — expected n-a at 1.5x/2x/3x, same class as the
windmill shadows and zoom-gated grid decals (§2.2).** The visual is a
terrain decal sized in world units with identity transforms and SCALE=1.0;
the camera scales it with zoom, so a UI tier change should not and must not
touch it. Do NOT build a lever for this row. Caveat for eyes-on: only the
ring's LINE WIDTH could conceivably read thin on high-DPI rigs — if a
future eyes-on says so, the lever would be the child SCALE via a §2.1-style
instance-transform hook (never the EFFDIR data route, which is load-law
inert).

## LIVE PROBE (the single cheapest, spec)

Zero new code: run the existing BUBBLEALL census (already in the shipped
DLL, `CodePatches` detour on 0x5939B0; lines appear in
`_tests\captures\SC4UIScale-2026-08-17-*.log`), enter god mode, select the
raise-terrain brush, hover terrain ~5s, click once, switch to lower-terrain.
- EXPECTED (attribution + name-route proven): `BUBBLEALL
  mountain_tool_active ret=0x... ok=1` (and `..._inactive` /
  `valley_tool_active` on tool switch) while the ring is on screen — the
  ret addr names the spawning code site for free, closing the plumbing
  UNKNOWN.
- POSITIVE CONTROL: the BUBBLEALL install line + ambient spawns (helipad/
  rotor lines) in the same capture.
- If the ring is ON SCREEN and BUBBLEALL stays silent while the control
  lines print: the spawn is by-index / a different manager API — the
  attribution to the effects manager still holds (the visuals only exist
  as EFFDIR effects), but the hook for any future lever must move to the
  by-index creator (start the hunt at the effect-manager service vtable,
  §2.1).

## DEAD ENDS (do not re-walk)

- No S3D/prop route: nothing brush/cursor-named in `s3d-name-sweep.txt`
  beyond tourist "balloon" props (checked in the #188 session, `[R:11600]`).
- `ApplyTerrainBrush` VA 0xAB41B4 (ref 0x750413) is `cSTETerrain`'s
  script/tunable method table (beside SetSeaLevel/GetCellAltitude) — the
  terrain EDIT op, not the cursor visual. `MiscTerrainTunables` /
  `RaiseLowerAmount` (0xAB4124/0xAB4138) tune terraform STRENGTH, not size.
- The `16.0f` imms at 0x4B8B3D/0x4B8B42 are the UDI one-cell hover quad
  (census row 6) — a different visual; never patch (`[R:11350]`).
- WarriorUI ring + disaster-flyout ring sprite: window-world, §2.6 — not
  this row.
