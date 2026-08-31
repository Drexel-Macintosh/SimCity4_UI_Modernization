# Row 16 — traffic/commute route overlay (query route trace) + row 4 twofer (what sizes the 8x8 route dots)

**Session 2026-08-17. Grade: PARTIAL (static disassembly, byte-read from the
shipped Steam 1.1.641 exe this session; ZERO live executions of this module
exist in any capture — see the nulls section, every one carries its positive
control). All VAs are static ImageBase 0x400000 VAs.**

## VERDICT

The in-world route visuals (dots + query signpost billboard) are owned by the
**signpost-occupant module itself — clsid `0xAB72FBB3`, one 0x590-byte GZCOM
class** whose ctor is `0x5F5510`. There is no separate "route-dot subsystem":
the doc's "`0x5F7400`" is a **mid-function VA inside this class's view-init
method `0x5F73A0`** (0x5F7400 lands between two instructions of it), and the
"8x8 dots" are the **ten 8x8 FSH tiles this init loads** into the instance.
The route trace on the **Data Views map** is a second, WINDOW-side consumer:
`cSC4WinMapView` (clsid `0x28C5A41F`, §2.6 family) has its own route segment
drawer — do not conflate the two.

Row 4 twofer: the `0xAA523C` supersession is CONFIRMED byte-for-byte, and the
REAL size source for everything this class draws (dots included, per the
static model) is: **per-item pixel size (item vtable +0x14, an int) →
px→world helper `0x7F6690` on the live view `[0xB43DD8]` → × the SAME
`0xAA523C[zoom]` float** — one multiply per quad inside builder `0x5F5FB0`.
So if the dots are strip items (unverified live), **v3.0.7's MARKERZOOM table
patch already co-scales them**; nothing new to build until a route-query
capture says otherwise.

## THE CLASS (byte-anchored)

- **Registration**: registration site `0x46083F` pushes factory `0x5F5CE0`,
  clsid getter `0x5F5940` = `mov eax,0xAB72FBB3; ret` → registered via
  `0x90E133`. Factory `0x5F5CE0` news the object through the class-object
  registry at `[0xB0A970]` and tail-calls ctor `0x5F5D0E → 0x5F5510`.
- **Direct creation** (the query path): `0x4D82C0` `push 0x590; call
  0x5E55E0` (operator new) → `push 1; call 0x5F5510` at `0x4D82D9`.
- **Ctor `0x5F5510`** (arg = 1 enables extra interface): vtables written:
  `[obj+0]=0xAA5268`, `[obj+4]=0xAA5418` (base ctor `0x5EE050` first),
  `[obj+8]=0xAA5408` (slot3 = message handler `0x5F7510` — cIGZMessageTarget
  shape), `[obj+0xC]=0xAA5380` (slot3 = init `0x5F73A0`, also `0x5F5E20`
  shutdown), `[obj+0x10]=0xAA5364`, `[obj+0x14]=0xAA5300` (the big view
  interface, 0x5FD2xx–0x5FFAxx methods), `[obj+0x28]=0xAA52E8`,
  `[obj+0x6C]=0xAA52E4`, and iff arg!=0 `[obj+0x70]=0xAA5498`,
  `[obj+0x58C]=0xAA1F38` (at `0x5F551E`/`0x5F5525`).
- **QI ids**: own iid **`0x4B44FBE2`** (QI `0x5F4930`, `cmp eax,0x4B44FBE2`
  at `0x5F4934`); base QI `0x5EC960` exposes **`0xE9793A65`** (the marker
  interface id, byte-confirmed in #188) and `0x452294AA`. Matches the #188
  hover-handler note "0xAB72FBB3 -> QI 0x4B44FBE2" (REGRESSION.md:11652).

## INIT `0x5F73A0` — the fn the doc calls "route-dot subsystem 0x5F7400"

this = obj+0xC. Sequence:
- one-time flags at `[this+0x2E]` bit1; identity transform block filled
  (`0x5F73BD–0x5F7413`);
- `lea ecx,[esi-8]` (=obj+4) `push 0xAB72FBB3; call [vt+0x20]` at
  `0x5F7418–0x5F741D` — registers the occupant type with its manager;
- `call 0x5EC940` (2 args) then configures sub-object at obj+0x580 via
  `0x7D2B50` with literal args incl. 3,4,5 / -1.0f (`0x5F7432–0x5F7455`) —
  semantics unresolved;
- **texture loop `0x5F7470–0x5F74B1`**: for ebx = `0xAA5214` .. `< 0xAA523C`
  (**the cmp instruction is `0x5F74AB` `81 FB 3C 52 AA 00`; the doc's
  "0x5F74AD" is the address-dword offset inside it — both refer to the same
  compare; supersession CONFIRMED: an END-BOUND, not a size read**): builds
  TGI {T=`0x7AB50E44` (imm at `0x5F747A`), G=`0x1ABE787D` (imm at
  `0x5F7482`), I=[ebx]} and fetches via resource mgr `[0xB43CD4]` vt+0x18
  into `obj+0x54C..0x570` (ten pointer slots; `lea edi,[esi+0x540]` at
  `0x5F7465`);
- subscribes message ids **`0xA6B79602`** (at `0x5F74CB`) and
  **`0x06CDB65B`** (at `0x5F74E8`) on the message server `[0xB43CCC]`
  vt+0x14;
- calls `0x5F5EF0` (content-item vector rebuild) then builder `0x5F5FB0`.

**The tile table `0xAA5214` (byte-read this session):** ten u32 instances
`8B4A6560 61 62 63 64 65 64 65 66 67` — **10 loads over an 8-distinct-id
range; entries 6,7 repeat 8B4A6564/65**. This resolves §2.5's CARRIED
"ten tiles vs 8-instance range" disagreement: BOTH were right. `0xAA5214` has
exactly ONE .text consumer: the imm at `0x5F7461`.

**The tiles are real and 8x8**: `find_tgi.py 8b4a6560 8b4a6561 8b4a6567` →
all in `SimCity_2.dat`, T=0x7AB50E44 G=0x1ABE787D (offsets 119150191/
119150330/119151159, sizes 139/176/128). Parsed SHPI headers: `G264` dir,
1 entry each, **w=8 h=8** (codes 0x60/0x61). "8x8 route dots" = these.

## MESSAGE HANDLER `0x5F7510` (vtable 0xAA5408 slot 3, this = obj+8)

- msg type `0xA6B79602` → `lea ecx,[esi-8]` (=obj) → **rebuild strip
  `0x5F5FB0`** then `0x5ECFB0` (route/content data changed);
- msg type `0x86AD10EE` → reads msg vt+0x38, divides by 1000
  (`mul 0x10624DD3; shr edx,6` at `0x5F7556–0x5F755D`), calls **blink timer
  `0x5F4960`**: accumulates ms at `[obj+0xB0]`, every **0x1F4 = 500 ms**
  toggles byte `[obj+0xAD]` (`sete` flip at `0x5F4983`) — the route
  dots/highlight BLINK phase;
- msg type `0x06CDB65B` → `0x5F7576` path (not walked).

## THE BUILDER `0x5F5FB0` (prologue `55 8B EC 83 E4 F8`, confirmed) — SIZING

- Zoom factor: `0x5F605B` `mov edi,[0xB43DD8]; mov ecx,[edi+0xC]` (zoom 0–4)
  → **`fld [ecx*4+0xAA523C]`, instruction at `0x5F6064` (address-dword at
  `0x5F6067`)** → stored to the persistent stack slot ([esp+0x5C] at base
  depth). The doc's sole-consumer proof holds: this is the ONLY data read.
- Head furniture (as §2.5): default content px `0x18`=24 written at
  `0x5F6053`; `push 8.0f` at `0x5F609D`; `push 64.0f` at `0x5F60BF`;
  `push 8.0f` at `0x5F60D3` — each converted px→world (`call 0x7F6690` at
  `0x5F607D/0x5F6094/0x5F60B6/0x5F60CA/0x5F60DE`) then
  `fmul [esp+0x5C]` (zoom table) immediately after each call.
- **Item loop `0x5F699E–0x5F6AD1`** (the census-relevant one): iterates the
  content vector at `obj+0x574/0x578`; per item: vt+0x18(&tex) at
  `0x5F69B4`, **vt+0x14(&sizePx int)** at `0x5F69CB`, `fild` +
  unsigned-fixup, **`call 0x7F6690` at `0x5F69E8` → `fmul [esp+0x5C]` at
  `0x5F69ED`** (same zoom-table slot), running-offset layout
  (`fadd/fst [esp+0x20]`), FOUR 20-byte vertices per item appended to the
  vertex array at `[obj+0x4BC]` (`0x5F6A17–0x5F6AB5`). Two more px→world
  calls at `0x5F6AE5/0x5F6AFD` in the loop epilogue.
- Items are 8-byte objects; the vector is (re)filled by `0x5F5EF0`: clears
  via `0x527180`, then hands a visitor {vtable `0xA80810`, id
  **`0x2C1FD612`**} to service `[0xB43CE4]` vt+0x10 (`0x5F5F51–0x5F5F74`) —
  providers contribute the items. **Which provider contributes DOT items,
  and what its vt+0x14 returns (8?), is the one unverified link** in the
  sizing model.
- The ten tiles `obj+0x54C..0x570` have NO other read in `0x5EC000–0x600000`
  (positive control: the same scan finds the init writes, the shutdown
  releases `0x5F5E70/0x5F5E99/0x5F5EA5`, and the dtor run
  `0x5F5843–0x5F588B`). They are plausibly handed out AS item textures by
  the provider — untraced.

## THE CREATOR — the query-tool view-input-control

- VIC class: ctor **`0x4D7F00`** (base ctor `0x5FB320` — the shared
  occupant-view VIC base; primary vtable **`0xA92968`**; `[this+0x28] =
  0xA8298C`). Built (0x80 bytes) by the city tool factory at
  **`0x7F1CE8`/`0x7F1CFB`** (sole ctor caller).
- Its handler **`0x4D81D0`** (vtable slot at `0xA929A8`): state check
  `[this+0x2C]==3` → deactivate; else takes the renderer
  **`[0xB43DD0]` vt+0x104 pick at `0x4D8264`** (the §2.4 slot-65 pick —
  a SECOND call site besides the documented `0x4B8A38`) with a
  stack-built filter (vtables `0xA9293C`/`0xA92924` written at
  `0x4D8230/0x4D8236`), then **creates the signpost occupant at
  `0x4D82C0–0x4D82D9`** (`new 0x590` → `push 1` → ctor `0x5F5510`).
  Pick-miss fallback continues at `0x4D8272` via `[0xB21920]`.
- **Caution (#188):** the 0x4D7xxx VIC cluster was proven DORMANT for
  balloon clicks in idle mayor view (SPHOVER=0). This VIC is a TOOL control;
  the claim here is only that it runs when its tool is active (route/query),
  which no capture has ever exercised.

## THE WINDOW-SIDE TWIN — Data Views map route trace (for the census, not a target)

`cSC4WinMapView` clsid **`0x28C5A41F`** (factory `0x466080` `push 0x9E8`,
ctor `0x7A0D50`, registered at `0x46631F` — all already in REGRESSION.md:5311
from #109): segment drawer **`0x7A2380`** (15 internal call sites,
`0x7A24BB–0x7A436B`), input = vectors of 12-byte cell elements (÷12 idiom
`imul 0x2AAAAAAB` at `0x7A23A8`), passes its OWN texture array
`lea edx,[ebx+0x54C]` at `0x7A260D` (and `0x7A29DB`) into `0x79ED90`
(sole caller `0x7A2628`). Same +0x54C offset as the occupant is a
COINCIDENCE of two different classes — do not cross-patch. Window world,
§2.6 family, out of scope for row 16's in-world defect class.

## NULLS (each with its positive control)

- **Zero live executions of the whole module**: all twelve 2026-08-17
  captures have "SPPROBE strip hook armed on 0x005F5FB0" (positive control
  printed per run) and **SPSTRIP fire count = 0**; SPQUAD/SPTEX/SPATTACH
  also 0. Scope limit: **no route query was performed in any captured
  session** (zero "route" mentions in every log) — the null says nothing
  about route-query behaviour. This also RE-EXPLAINS #188's "dormant
  0x5F7xxx module" verdict: the module is the route/signpost view; idle
  mayor view never runs it.
- **px→world caller census** (whole .text, corrected scanner —the first
  scan had an off-by-one and returned a FALSE empty; positive control: it
  now finds the documented `0x5F20B6` 44px-quad call): 18 callers total —
  `0x46CD0A/23/5A/75` (unknown fourth system, unexamined),
  `0x5F0FA3/0x5F1EF3/0x5F1F03/0x5F1F2F/0x5F20B6/0x5F20C6` (signpost-view
  quad/texture twin), `0x5F607D/94/B6/CA/DE/0x5F69E8/0x5F6AE5/0x5F6AFD`
  (this builder). No route-dot sizing outside the builder.
- **`0xAA5214` sole consumer** `0x5F7461` (positive control: the same imm
  scan finds 20 users of group `0x1ABE787D`).
- Raw disp32 byte-scans yield FALSE positives (e.g. "`+0x544` at
  0x5FA67C" was HKEY registry-string parser bytes; "`+0x54C` at 0x77F687"
  a jump displacement) — every hit used above was verified by disassembly
  context.

## TIER CALL

**Scale (screen-space)** — same hybrid class as §2.5: dot POSITIONS are
world-anchored (route cells), but every quad's SIZE is px constants ×
`0xAA523C[zoom]` × px→world, i.e. tier-shrunk on high-DPI rigs exactly like
the marker strips. Predicted: **v3.0.7 `ApplyMarkerZoomScale` already
co-scales the route visuals** (single table read serves every quad the
builder makes). If dots turn out NOT to be strip items, the lever is still
the same class (the tile draw path would need its own multiply). The 8x8
tile ART will want a crisp-art companion at 2x/3x, like the strip icons.

## LIVE PROBE (cheapest single step — a CAPTURE, not a build)

Launch the SHIPPED build with `MissionBubbleFx=3` (arms SPSTRIP on
`0x5F5FB0`), query a residential building → press Route (and/or run the
query tool over a road). Expected positives: first-ever SPSTRIP lines
(this/zoom/table-value) at the moment the trace appears; dots blink at
1 Hz (2×500 ms, `0x5F4960`). Adjudicates in one run: (a) the attribution
(builder fires on route query), (b) row 4's sizing (dot px ≈ 8 ×
table[zoom] × tier — at zoom 2 with the 1.5x patch: 8×1.125 = 9 px vs
stock 6 px), (c) whether MARKERZOOM already scales it. If a build is
allowed, add a log-only naked hook on init `0x5F73A0` (prologue
`83 EC 0C 56 8B F1`, byte-verified) logging `this` — one line per occupant
created per route query via `0x4D82C0`.

## Dead ends and unknowns

- `0x7D2B50` config args (1,1,1,0,1,1,0,3,4,5,-1,-1.0f,1,-1) on obj+0x580 —
  semantics unknown.
- The `0x2C1FD612` item-provider (who answers the visitor) — untraced; it is
  the missing link for DOT item granularity.
- Msg ids `0xA6B79602`/`0x06CDB65B`/`0x86AD10EE` — sources unnamed (lookup.py
  null; positive control: it resolves known ids).
- `0x46CDxx` px→world caller cluster — a fourth pixel-fixed billboard system
  nobody has looked at (candidate for census rows 8/15).


---

## MEASURED 2026-08-31 — the drawer is a dedicated `cISC4ViewObject3D`

Status: **UNKNOWN → DOCUMENTED.** Three independent offline lenses converged on
one chain from bytes; the prediction was written into `SC4UIScale.ini` *before*
the run; every element of it hit.

### The chain

```
pick handler   0x004D4D70   tool vtable 0x00A90A88 slot +0x40
  gated at     0x004D4F19   cmp [esi+0x8C],1        <- route mode only
→ 0x004CAC50   pick action; RemoveViewObject's any prior trace first
→ 0x004CA460   builder: new(0x2C), ctor 0x007DDD50, vtable 0x00ABB648,
                 stored at [tool+0x9C]
  0x004CA54D   AddViewObject(obj, layer=5, key=0x3E8)
THE DRAWER =   0x007DD9B0   vtable 0x00ABB648 slot +0x0C
```

The path result lives **inside the drawable**: a list of 0x44-byte strand nodes
at `[drawable+0x14]` / `[drawable+0x18]`, filled per network tile by
`0x004C5E20` through BeginStrand `0x007DDC50` and AddPoint `0x007DDB30`. Draw
walks that list and calls `0x007DD410` once per strand.

### Prediction versus measurement

Armed with **zero new code** — the `AddViewObject` detour (#188 VIEWOBJ,
`CodePatches.cpp:9392`) was already shipped; only `[Probe] ViewListRepeat=240`
was set.

| # | predicted | measured | |
|---|---|---|---|
| 1 | `vt=0x00ABB648` | `vt=0x00ABB648` | HIT |
| 2 | layer 5 | `a2=5` | HIT |
| 3 | `key=0x3E8` | `a3=0x000003E8` | HIT |
| 4 | absent at load, appears at the PICK | regs #1..#11 are load-time HUD classes, **none** is 0x00ABB648; #12 and #13 are the two clicks | HIT |
| 5 | second pick replaces the first | same slot `layer5[6]`, obj `41A9A454` → `467EA854` | HIT |

Positive control: `ViewListRepeat resolved to 240 (raw 240; read from [Probe])`
and `VIEWLIST GRAND TOTAL 14` on all three dumps — the enumerator ran, so an
absence would have meant something.

### Bonus fields, read live off the registration dump

* `[obj+0x04] = 0x00ABB630` — confirms **on screen** what ctor `0x007DDD50`'s
  bytes claimed.
* `[obj+0x10] = 0x40000000` = **float 2.0** — the scale lever's live value,
  matching the six inline per-zoom immediates `{2,2,2,2,1.4,1.2}` @`0x004CA4A2`.

**OPEN, recorded as an observation and not a claim:** `[obj+0x0C]` differed
between the two picks — `0x00000001` on the road, `0x44AA2C01` on the building.
The latter reads as float 1361.375, but the former does not read as a sane
float, so the field is **not identified**.

### What this refutes

Three attributions have now died on this row, and the write-up keeps all three
because each was held with confidence at the time:

1. **Named effect / EFFECTFILTER** — refuted from bytes against a 1,148-name
   EFFDIR dump with 13/13 recall including the DAT-only `cloudfx_expensive_slave`.
2. **The signpost-occupant module** — refuted; `cSC4SignpostOccupant` belongs to
   the Sign Tool, pinned through the game's own `kCommandID_SignTool` table.
3. **A per-network-tile occupant HIGHLIGHT flag** — the last standing
   hypothesis, explicitly speculative, now dead: the dots are a registered
   drawable, not a flag on occupants.
