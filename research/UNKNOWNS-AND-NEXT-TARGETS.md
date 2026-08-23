# SC4 UI reverse-engineering — documented vs. unknown

**Survey basis:** four independent documentation lenses (window/UI engine, in-world/renderer, render/art pipeline, open defects) over the SC4UIScale repo, plus targeted live verification of the contradictions below. Nothing was modified. No web access. The game executable was not opened during this survey — **every VA in this report is inherited from the repo's own notes, not re-verified against the exe today.**

**Grading bar used:** DOCUMENTED = the docs name a concrete mechanism that *predicts behaviour* — a VA, a struct offset, a vtable slot, a resource type/group, or a rule with a stated control. UNKNOWN = visible or known to exist, but nothing says what draws it, what sizes it, or how to change it. CLOSED-AS-IMPOSSIBLE = investigated with a stated positive control and proven unreachable. OPEN-DEFECT = mechanism known, work unfinished.

---

## A. Documented well enough to publish as reference

Deduplicated across lenses. This is the publishable core, and it is genuinely SDK-grade: `tools/research/SC4-UI-ENGINE.md` (~3,000 lines) is the artifact, with `SC4-WORLD-OVERLAYS.md`, `CITY-SITUATION-INDICATORS.md`, `UI-ART-BINDING.md`, `ITEMICONS.md`, `REGION-SCREEN.md` and `tools/dbpf/NOTES*.md` as the supporting set.

### A.1 The window tree and the GZWin engine

| Subsystem | The mechanism that makes it documented |
|---|---|
| Tree topology | One `cIGZWin` tree from `cISC4App::GetMainWindow()`. Four interior hosts decide everything: `0x6104489A` WinSC4App, `0x9A47B417` cSC4View3DWin (every in-city HUD/toolbar/flyout), `0xEA659793` region host (13 children), `0xAA32BCE6` Data Views fold-out. `0x2AAB8CC1` is the tooltip layer (vt `0x00AB6770`), not the region host. |
| Geometry primitives | Window rect = four int32 at `this+0xA8..0xB4` (L,T,R,B). `GetW 0x99C81B`, `GetH 0x99C82A`, `GetL 0x99BC53`. `GZWinMoveTo` is **relative**, never absolute. MSVC reverses overloaded-virtual vtable order, so `GetArea`/`SetArea` pairs land swapped and are unusable by naive index — use single-name getters. |
| Vtable slot map | `GetChildAsRecursive +0x94`, `GetW +0xA4`, `GetH +0xA8`, `SetW +0xCC`, `SetSize +0xD4`, `SetArea4 +0xDC`, `GZWinMoveTo +0xE0`, `SetID +0xFC`, `Show +0x110`/`Hide +0x114`. Draw band re-derived 2026-08-01: 87 GZPaint `0x0099BE4C`, 88 Plot (per-class; base `0x009A0A17`), 89 Draw `0x0099BA07`, 90 CalcAbsoluteArea `0x0099DCE4`, 91 InvalidateSelf `0x0099BECC`, 92 InvalidateSelfAndParents `0x0099BED1`, 93/94 draw-context getters, 100 `PrivateBuffer(bool) 0x0099EA70`, 123/124 PlotComposite/PlotPresent. **The vendor `cIGZWin.h` is missing one virtual (relative move, real slot 57, `0x0099BD27`), so every header-derived name above slot 56 is one too low.** |
| Child order = paint order | `EnumChildren` returns exact reverse of `.UI` sibling order; `.UI` order is add order is paint order (first child painted first/behind). Proven on the 14-child composite HUD against `I-2bc90671`. Consequences: never identify a button by enumeration index; `GetChildWindowFromIDRecursive` returns the **last-added** match (`0x0BC3B559` is shared by two minimaps and must be searched scoped). |
| Hit-test / routing | Router `GetChildWindowFromCursorPoint 0x0099DFA9` walks `[this+0x44]` head-forward, skips children lacking flag 1 or carrying `0x200000`, first child whose slot 40 (`[vt+0xA0]`) claims the point wins. Base `IsPointInMe 0x0099C97C` = coarse `[this+0x14]` rect; flag `0x80000` (MouseTrans) routes to the refined mask at slot 149 → `0x0099BBBE` → `[this+0x64]` HitTest, **result inverted (0 = opaque = clickable)**. First-claim-wins: a closed upstream gate starves every downstream hook. |
| Class registry | `{clsid → class-name}` registry in `.data` at `0xB08F78`: 648 entries, 8-byte stride, name pool ~`0xA89000`. clsid/iid/descriptor table at `0xB16FA0`, 12-byte stride. Registration pattern `push <factory>; push <clsid>; mov ecx,esi; call 0x90E133` at `0x4662B0`. To settle base-vs-override without launching: search the image for a function's LE address; each `.rdata` hit is a vtable slot and `VA − slot*4` is the vtable base. |
| The flyout pair | Two anonymous classes (`id==0`, identified only by vtable) `0x00AB6AA8`/`0x00AB6D88` implement the disaster flyout and every second-level menu. Container Plot `0x0079B0E0` (dirty gate `byte[0x114]&1`, buffer `[0xDC]`, arc helper `0x8D8BC0`, six layout insets `[0xE0..0xF4]`); strip Plot `0x0079AA70` (item size `[0xF4]`, spacing `[0xF8]`, count `[0xFC]`, visible range `[0xE4]..[0xE8]`). Container overrides `IsPointInMe` at `0x0079A180` → slot 121 `0x0079AE30`: claims only the rightmost `[this+0xE0]` px — and `[0xE0]` is **dual-use** (hit width wants 2x, Plot inset wants 1x). |
| Nested plop sub-flyout | Three windows (container `0x8A6E61E0` → strip `0x8A2CAD8B` → degenerate tip); **menu items are blits into the container's paint buffer, not child windows**, so no tree sweep can ever reach one. Builder `sub_7EAEB0` runs fresh per open. Closed form reproducing 8/8 observed heights: `stripH = 49n−5` (n = clamp(count,1,8)); `contentH = max(stripH, [+0xF4]=53) + 2·[+0xE8]=50`; `contW = 129` invariant. Constants are **coupled** (`[+0xEC] = artHeight − 2·[+0xE8]`), so the cure is a detour on `Place 0x0079AD00`, scaling finished rects. |
| Buffers | Two classes: `0x00AC1400` (main UI buffer — Init `0x8269B0`, GetW `0x808620`, GetBufferArea `0x8268C0`, **Blt slot 29 = `0x826AD0`**, rect `[0x14..0x20]`, pixels/stride `[0x3C]/[0x40]`, 32bpp BGRA) and `0x00ADB418` (region map items, Blt `0x00991BA0`). Three exit channels: slot 29 Blt, slot 20 private-buffer present (from `0x0099BA3E`), `PlotPresent 0x0099C498`. **A window owning a private buffer is invisible to a slot-29 hook. Blt clips, never stretches** (a 2538×6102 dest changed nothing on screen). |
| Colour key | Per-byte test, not a word compare: skip when `sp[0]==0xFF && sp[1]==0x00 && sp[2]==0xFF`, plus a separate guard for `0 < sp[3] < 0x80`. Stock magenta art has `a==0` everywhere and must keep drawing. **Exact-match only — any interpolating resampler moves a key pixel off `0xFF00FF` and the key colour draws pink.** |
| Named widgets | `cSC4WinRCI 0xC7A0E17E` (Draw `0x7A9500`, window-derived, no pixel constants). `cSC4WinTrendBar 0xAA5C2F86` (Draw `0x7BF0A0`, art-derived, fill band = fillW/6, immune to the latch — re-reads all geometry live). `cSC4WinMiniMap 0xCA318388` (self-updating `[+0xE4]` blitSize but a **one-shot** display surface `[+0xF0]` — every scaled instance needs destroy-and-recreate). `cSC4WinAdviceList 0xCA1492AC` (Refresh `0x00793810` is the **only** row emitter image-wide; middle cell = `GetW()−61`, with `61 = 18+18+25` encoded `83 EE 3D` at `0x0079388F`; correct general form `S(f) = round(18f)+18+9+round(16f)`). `GZWinBtn` iid `0x00008810`, descriptor `0xAD5CAC`, vt `0x00ADDAF0`. |
| GZWinText line-break | Regime chosen at `0x009BF486`: `w==0 \|\| flags&0x0200` → one line; `flags&0x0002` → word wrap at w; else break on `\n` only and clip. Constructor default flags = 0 (`0x009C026C`), so code-created text gets regime 3. Wrap width = `GetW() − 2·gutter − scrollbarW` (`sub_9BCBC5`, gutter default 5 at `0x009BFFCC`), scrollbar width read **live** from `[this+0x1d4]`. Class overrides SetArea at `0x009BFCA5` and re-breaks — the resize is the trigger. |
| Fonts | One parse site only: `[Font Styles]`/`[Font Aliases]` referenced once each (`0x44DE23`/`0x44DD7F`) inside init `0x44DB60`; no second table load, no locale override. Per-line callback `0x44D7F0` → `0x44D4D0` registers with the font system (singleton `0x913C72`, `vt+0x18 RegisterStyle`) and adds name→GUID to a private dict (clsid `0xBA2E7954`). Slots: `+0x14 GetStyleByGUID`, `+0x18 RegisterStyle`, `+0x34` name dict, `+0x8C` line height, `+0x98 GetStyleFromName`. Named fetch sites: WindowTitle `0xE2B14587@0x7EACA5`, GenButton `0x4A809919@0x77BA93`, ChartLabel `0xE9C86B5E@0x0076DD91`, Legend `0xE9C86B5F@0x007A0747`. Probe order Plugins → install root → DBPF; deployment is whole-file replacement. |
| Tooltips | Code-painted entirely by the tip layer's Plot `0x798710`; no child windows exist under `0x2AAB8CC1`. **Hardcoded 250px wrap** (`push 0xfa` at `0x79880A` and `0x7988A9`). Tips are content-sized (430×120, 490×316 observed). |

### A.2 The `.UI` script format

| Fact | Anchor |
|---|---|
| Storage | TypeID `0x00000000`, **SimCity_1.dat only**, 330 entries: 271 in `0x96A006B0` (default layouts), 10 in `0x08000600` (800×600 override set — the GID is the literal resolution digits), 48 in `0x8A5971C5` (animation banks/configs, not layouts), 1 font-style table. Legacy pseudo-XML, one `<LEGACY>` per line, nested by `<CHILDREN>`, unquoted attributes — needs a lenient parser. |
| `area=` | **Corner form** (l,t,r,b), absolute for roots, parent-relative for children, always absolute pixels. No percentages, anchors or layout managers. Proven by button rows `(68,28,115,65)`/`(68,78,115,115)` = 47×37 on a 50px pitch. |
| `imagerect=` | A **source crop** in bitmap pixels, also corner form. Proven by HUD sheet `14015545` (878×182) whose child at `area=(122,111,254,130)` carries `imagerect=(122,111,878,182)` — impossible as (x,y,w,h). 839 crops in the corpus, four use patterns (big-sheet re-crop, multi-state, pixel-registered collage, 9-slice edge). |
| The three-number law | A blit has a SOURCE (bitmap), a CROP (imagerect) and a DESTINATION (window). **Scaling any two of the three is not a partial fix, it is a new defect.** |
| `blttype=` | `tiled \| normal \| edge`, plus `edgeimage=yes\|no`. Stock tally: edge 277, tiled 254, normal 9; edgeimage yes 56 / no 788. **The 11 third-party scripts invert this** (edge 17, tiled 1, normal 31) — a count over the stock corpus describes Maxis's habits, not the engine's behaviour. |
| `font=` | GZWinText's deserializer `0x94E516` honours a token/GUID (`SetFontStyleByGUID` iface `+0x4C = 0x9C16FD`, stores `this+0xE0`, fallback GUID `0x68963C4C`) and **silently discards a raw string** into property `0xFAA4AE85`, which has zero consumers image-wide. Other deserializers (`0x94CF0A`, `0x94F9E4`, `0x950657`, `0x950C94`, `0x959491`) do call GetStyleFromName; GZWinText's does not. Rule: convert every `font=NAME` to `font=0x........`, which the round-trip serializer `0x95BC5F` already emits. |
| `align=` | valign token byte-verified in the align deserializer `0xAD584C-0xAD58A4` (`leftbottom` = token 2). **The CENTER mode is self-scaling**: seat = `(GetH()−textH)>>1`, recomputed on every SetArea at `0x9C20D3` — so `align=leftcenter` re-seats at any tier while `align=lefttop` visibly floats once the box grows. |
| `gutters=` | Content padding, **not** the 9-slice inset. Proven arithmetically: 271 of 277 edge roots carry `(64,64)` while the frame art `144161e4` is 78×78, and 64+64 > 78. |
| Alignment marker | Every tool-flyout script carries a hidden `GZWinCustom id=0x0000AAAA` sized to its spawn button; the game places the panel at `panelPos = anchorAbs − markerOffset` in **native units**. Reproduces all three god docks to the pixel (22,262 / 22,502 / 22,742). **Never scale a marker** — doubling the advisor strip's (229,63) marker shifted the strip by exactly −(229,63). |
| Scrollbars | ids `0x42B7C351/53/54/55` are stamped by **generic framework code**, not any panel: `sub_99A96E` allocates 0x11C bytes (ctor `sub_99A67E`, vt `0x00ADC398`) into `[owner+0xF0]` and `SetID(0x42B7C351)` at `0x0099A9F6`; the three children are stamped inside `sub_99A70F` with the id passed as an **argument**, which is why a literal-SetID census finds only the parent. Any id-keyed rule on `0x42B7C35x` hits every scrollbar in the game. |

### A.3 Art: containers, binding, and the sizing rules

| Fact | Anchor |
|---|---|
| DBPF | v1.0 / index 7.0, 20-byte index entries (T,G,I,Offset,Size, LE), compressed-entry directory at `E86B1EEF/E86B1EEF/286B1F03` (16B records), QFS detected by `0x10FB` at +4 after a 4-byte LE compressed size and a 3-byte BE uncompressed size. SC4 ships type `0x856DDBAC` payloads **uncompressed with no DIR record**; roundtrip proven byte-identical 4/4. |
| UI art store | **All** UI image art is type `0x856DDBAC` in SimCity_1.dat only — 2,280 entries, 0 in SimCity_2..5/EP1/Locale (measured over ~108k entries). Group split: `46a006b0` 810, `1abe787d` 743, `6a386d26` 356, `4c06f888` 112, `ab7e5421` 93, others. **`0x46A006B0` and `0x1ABE787D` are near-mirror twins** (743 MD5-identical at the same IID, 0 differing, 67 unpaired) — override one without the other and you ship mixed-scale UI. |
| The 74 oddballs | Classified by magic bytes: 2,206 true PNG, 41 JPEG (all `0xCA133ECB`, tutorial screenshots 125×195), 26 EA SHPI/FSH (all `0x46A006B0`), 7 BMP (all `0x6A1EED2C`, 16×16). Every FSH is single-entry, bitmap code `0x7D` only (32bpp A8R8G8B8 stored BGRA, top-down); bytes 24..31 are the EA filler `"Buy ERTS"`; native 2x rebuild = original bytes + new pixels with exactly four patched fields, 74/74 re-parsed exact. |
| Four binding paths | **1** `.UI`-referenced TGI (2,962 occurrences, 431 distinct pairs, the ref's GID is honoured → selective retargeting works). **2** code-bound TGI immediates via `0x602B00` / `[edx+0x94]`, nine confirmed instances tabulated. **2b** exemplar-bound ItemIcons. **3** `sc4://HTML/<g>/<i>` URLs inside LTEXTs (`0x2026960B` in SimCityLocale.DAT). **4** runtime-generated with no TGI (My Sims portraits, advisor faces = live 3D head renders bound at `0x41DE20`, gauge dials, the Graphs chart, tooltips). **~1,850 of 2,280 PNGs are bound by paths 2/2b/3/4 — which is exactly why blanket 2x is unsafe.** |
| ItemIcons | TGI = `{0x856DDBAC, 0x6A386D26, <Item Icon>}`; exemplar property `0x8A2602B8` holds **only** the instance — type and group are exe constants stamped at `0x78EE09`/`0x78EE11` (read `0x78EDC9`; further sites `0x7ECB1E/44/4C`, `0x7F0359/8F/97`; alt-icon property `0xABE1AF70`). All 266 distinct values resolve, all exactly 176×44 = a 4-cell 44×44 strip on template clsid `0x4988BC6A` with no imagerect. Binary exemplar layout fully decoded (8-byte signature, parent cohort TGI, u32 count, then `{u32 id; u16 valueType; u16 keyType(0x80=array)}`, **1 pad byte before singles as well as arrays**), 8957/8957 parse. **CAM ships roughly half its exemplars as text — a binary-only parse silently missed 30 icons.** |
| Three blit behaviours | **dst-follows-src**: GZWinBMP's plain path (vt `0x00ADF6A0`, slot 88 = `0x9BC325`) computes dst = `{areaL, areaT, areaL+srcW, areaT+srcH}` — the window rect is never read, so 2x art gives a 2x draw with no hook. **stretch**: the edge/9-slice path (holder flag bit 8) divides src by 3 and issues many blits. **src-follows-dst**: `cSC4WinAuraBar 0x00797CC0` computes `src.L=(imgW−winW)>>1` — under-sized art tiles rather than shrinking. |
| The SetImage LATCH (#176) | GZWinBMP member map: `+0xA8..0xB4` area, `+0xD8` flag holder (bit `0x10` has-imagerect, bit 8 edge), `+0xDC` live `cIGZBuffer*`, `+0xE8..0xF4` live imagerect. `SetImage 0x9BC57E` (tail `0x9BC447`) rewrites `[win+0xE8]` to `(0,0,min(areaW,imgW),min(areaH,imgH))` **from the window's area at bind time**, and `SetArea 0x99C837` never touches it. **The latch law: any value derived from a window's size at bind time is a hidden consumer of that geometry — ask WHEN content was bound, not what the geometry is now.** |
| The sheet's ROLE decides its rule | The engine cell-divides with an integer divide baked into machine code and never reads a cell count from data. **N-state strip**: cell = `imageWidth/N`, cut horizontally only. **9-slice frame**: cell = `(W/3, H/3)`, snap to a multiple of **3 and 3 alone** — LCM{3,4}=12 is a third answer wrong for both (180×180 at f=1.5: 418 uncovered px at 276 vs 4 at 270). **Tiled / 1:1**: src-follows-dst, no divide, snap nothing. The three role lists are **derived** from the corpus that binds each sheet (`find_cell_strips.py` 193/2206, `find_nine_slice.py`, `find_no_snap.py` 193 entries), never hand-listed. Measured breakage: 31% of /3 sheets and 43% of /4 sheets break at 1.5x, **0% at 2x and 3x**. |
| Load order | Files in the Plugins **root load before files in subfolders**, so a root `z_*.dat` can never override a dat inside a subfolder. A plugin may replace a stock `.UI`, its art, or both. **Recognition rule: if a panel's live window count or root size disagrees with the stock script you are reading, a plugin has replaced that script** (live 532×640 / 73 windows vs stock 531×406 was the tell). |
| Resampling | `--smooth-unkeyed` (Catmull-Rom) ships; **`--smooth-keyed` is forbidden** — interpolation moves a key pixel off `0xFF00FF` and the key colour draws. A second exclusion is structural: art that is **measured** cannot be smoothed (`seat_faces_on_apertures` scans the advisor frame for the aperture; a one-pixel gradient makes the scan stop early and the build FATAL). `no-smooth.txt` is derived with a `--check` mode that fails on a stale list. |
| Minimap terrain bake | Field map `+0xE4` blitSize, `+0xF0` one-shot surface, `+0x104` zoom, `+0x114` raster (a plain 3-dword struct), `+0x120` 16-byte dirty mask. **zoom = −log2(blitSize/terrainDim) computed by a shift loop at `0x7A7892-0x7A78D5` with no exactness test** ⇒ blitSize must be an exact power-of-two multiple of terrainDim or addresses walk off the raster. Recompute `0x7A7840` **marks only**; handler `0x7A8640` is the only caller of bake `0x7A7FF0`; the 5-entry dispatch at `0x7A8628` is indexed `zoom+2` and its bound test `cmp ecx,4; ja` at `0x7A8563` is **unsigned**, so zoom=−3 wraps, every tile is skipped, and step 5 still clears the mask and reports success. |
| Region screen | `cSC4WinRegionView` paints nothing through the cIGZWin draw slot — every region pixel goes through the painter at `+0xD8` (`sub_7B6060`, `sub_7B4150`); tile cache at `+0x10C`; bitmap factory `+0x154`. Default tile images = 12 slots = **6 pairs {RGB, alpha mask}**, stride 8. Items own six refcounted buffers (`+0x1C` source, `+0x20` mask, `+0x2C` composite…) and are **bottom-anchored**. One region cell = 128×64 px. `cIGZGDriver` real vtable = header slot **+ 0x0C**, verified at five sites in `sub_7A9D60`. |

### A.4 In-world / renderer-side

| Subsystem | Mechanism |
|---|---|
| The two-worlds law | Every visual is drawn by exactly one of two systems, each with its own instruments, sizing vocabulary (world-anchored / pixel-fixed / zoom-ramped), hit-test path and levers. **One observation decides: does a full-depth window dump show a window at the visual's position while it is on screen.** |
| px→world primitive | `0x007F6690 = fld [esp+4]; fmul [ecx+0x150]; ret 4` — a pixel value times the live view scale. **Eighteen callers, fully enumerated.** This is the discriminator between pixel-fixed and world-anchored: a drawer that never calls it is in world units. |
| CSI (the U-Drive-It offer balloon) | Category 4 of a 7-way dispatch-indicator system. Drawer `cSC4DispatchVehicleView::Draw 0x0046D990`, **identified by suppression on screen**; keyed on the automaton (QI iid `0xA9B40F05` at `0x0046DDBD`), category test `cmp ecx,4` at `0x0046DD6C`. Two screen-space quads: pin 64×64 from eight ±32.0f **inline imm32** at `0x0046EABD/EACA/EAF6/EB01/EB2D/EB38/EB64/EB6F` (`C7 84 24 <disp32> <imm32>`, verts `[esp+0x150]` stride 0x14); icon + **click box** 35.0f at `0x0046CC47` inside the CSI-only branch `cmp [esi+4],4 @0x0046CC41`, stored to record `+0xD0/+0xD4`, halved to ±17.5 at `0x0046EC2C/EC38`. Emitted via `0x007D2990(6=GL_QUADS,2,4,&verts)` → DX7 GDriver `DrawArrays` at `[[this+0x30]]+0x0C`. Art declared by the automata LUA field `csi_image` (type `0xCA63E2A3` group `0x4A5E8F3F`, parser `0x00521C70`, field `+0x68`), each a 152×38 four-state PNG. **The negative table is as valuable as the positive one**: `0x00A8819C`=42.0f is the quad *translation*, `0x00A881A0`=50.0f orbit radius, `0x00A88260`=43.0f leader, `0x00A88268`=21.0f, `0x00A88170` per-zoom table (not the CSI path), `0x00A881AC` style bytes. `0x0046CCB9` is the identical instruction shape holding 32.0f on the non-CSI branch — never touch it. |
| Swarm effects | Effects requested **by name** (table `0xB09AE0`). `CreateEffectByName = 0x5939B0` (`__thiscall` + 2 stack args, result in AL, success writes `*ppOut` only at `0x593AB9`). The 0x14C-byte instance's 4th transform block: rot 3×3 `+0xE0`, translation `+0x104`, **scale `+0x110`**, flag byte `+0xDD`. Activation `0x5919D0` multiplies instance scale into every child spawn (`fmul [esi+0x48] @0x591FEA`). **`SetParameter` has no scale id (0..0x13 only)** — the instance transform is the only runtime scale lever. Service ptr `[0xB43D1C]`, iface vt `0xA9F264`, slot `+0x1C` = the only `.rdata` reference. |
| EFFDIR format | TGI `{0xEA5118B0, 0xEA5118B1, 0x00000001}`, 1,094,484 bytes decompressed, 1,149-entry name→index map. Child record: `[u32 nameLen][name][u8 type][u32 flags][9 f32 rot][3 f32 trans][f32 SCALE][u8 zoomMin][u8 zoomMax][u16 copies][u16 mult][4 f32 zoom ramps][2 u16 weights][u32 effectIndex]` — proven twice (semantically over 406 records, and by parser disassembly `ReadChild 0x5AB690` / `ReadTransform 0x5DA930`, scale read `0x5DAA2B` → `child+0x48`). |
| Marker strips | Builder `0x5F5FB0` code-generates billboard strips: 24px content icons + 8.0f margins + 64.0f disc, each through px→world then `fmul` the per-zoom float table `.rdata 0xAA523C = {0.5,0.75,1.0,1.5,2.0}`. **Sole-consumer proven**: the only other `.text` reference (`0x5F74AB`) is a texture-loop end bound, not a size read. |
| Signposts | `cSC4SignpostOccupant` clsid `0xAB72FBB3`, 0x590 bytes, ctor `0x5F5510`, factory `0x5F5CE0`, own iid `0x4B44FBE2`. Init = `vt(obj+0xC)` slot 3 = **`0x5F73A0`** (the older docs' "`0x5F7400`" is a phantom VA that decodes mid-instruction). Loads ten 8×8 FSH tiles `8B4A6560..67` as `{0x7AB50E44,0x1ABE787D,inst}` into `obj+0x54C..0x570`. Quad builder `0x5F20A0` uses a hardcoded **44.0f screen pixels** (`push` at `0x5F20AF`) + 150.0f pole raise; texture compose `0x5F12D0` in 52px cells. |
| Renderer pick | `cISC43DRender vt+0x104` (slot 65) called at `0x4B8A38` — a ray-pick against drawn geometry, **no radius constant on the path**; wrapper `0x4B8A00` reached only from the control's two mouse handlers; whitelist fn `0x4B8880` (5 automata families) plus the signpost at `0x4B8947`. **Compare chain resolved** (`disasm_at.py 0x4B8880`, offline): type (`vt+0x1C`) tested against `0x74758926`, `0x278128A0` (also the offer-proxy's `GetType()`, `REGRESSION.md:11934`), `0x2890D4DE`, `0xA823821E` (the automata **prop-family** id, `CodePatches.cpp:5481`), `0xC772BF98` — the first/second/third/fifth accept unconditionally, `0xA823821E` instead branches to a nested QI(`0xE9793A65`)+type-recheck against `0xAB72FBB3` (`cSC4SignpostOccupant`) at `0x4B8947`, which is the "plus the signpost" clause (§2.4 of `SC4-WORLD-OVERLAYS.md` has the full chain). The 16.0f imms at `0x4B8B3D/0x4B8B42` are the one-cell **world-unit** hover quad — never patch them. |
| AddViewObject | `cISC43DRender::AddViewObject = vt+0x80 → 0x007C5D90`. Hooking it censuses **every object the renderer will draw** — the only enumerating instrument that exists for the renderer side. A live capture logged 8 HUD-chrome registrations (`0xAB4480/0xAB39D0/0xAB42F8/0xAB4624`) then three of class `0xAA8314` (ctor `0x00620770`, draw `0x00620500`), which was then eliminated by subtraction. |
| Occupant highlight | No separate visual — the renderer tints the occupant's own model via `SetHighlight(mode, sendNow)` at `vt+0x44`. Query tool (clsid `0xC7AF928E`) uses mode 7 at `0x4CBF9D`; demolish (`0x46DDB5F1`) mode 5 at `0x4B99F6`; mayor-default control mode 5 at `0x4DB34A`. Change posts `kSC4MessageOccupantHighlightChange 0xA2D1C5B9` (`0x80D600`, the only ref). |
| Marker per-object size | vt0 `0xAA4900`; slot 13 `SetSize` `0x5ED400` (each arg `fmul 10.0f` → ftol → `mov [this+0x5E/0x5F],al`), slot 14 `GetSize` `0x5ECA10`. **A marker carries its size in tenths of a world unit, byte-capped at 25.5 — and that field is also a spatial-index key**: inflating it to probe a visual made each marker span many more cells and hung the game. Writes are permanently disabled. |
| TagKind markers | 25 `Tag1x1x3_*` exemplars bind a deliberately **NULL S3D** and carry a TagKind byte (exemplar property `0xABB90E58`, which occurs **exactly once** image-wide: `push 0xABB90E58` at `0x004FBFFC`). Spine: ctor `0x004FBB40` → visitor `0x004FC710` → builder `0x004FBFE0` (jump table `0x004FC410` on tag−1) → factory `0x00505370` (`vt+0x3C`) → creator `0x00510690`. LOD floats `0x00A94810`=500.0f / `0x00A94814`=−1000.0f at `0x00508E10`. Live-confirmed. |
| The boundary case | Window `0x48E945B4` is a **code-created GZWinBMP parented straight to the 3D view under no listed root, and transient** (one sample, gone 0.5s later) — which is why static censuses missed it for weeks. Standing counter-example to "in-world ⇒ not a window": sample the census while the visual is on screen or the null is not a null. |

### A.5 Project-side machinery (the mod's own model, publishable as method)

- **The parentage rule and its correction.** Descent from the 3D view is *necessary but not sufficient*: `ScalePanelsUnder` takes a flat `EnumChildren`, so `ScalePanelRoot` only ever sees a **direct** child, and eight gates plus a 128-panel cap can skip it. Below a swept root, any id in `kDataScaledSubtreeIds` makes `ScalePanelRoot` return before the child loop. Windows parented at main-window level are outside the sweep entirely. **A window served by both layers renders at 4x.**
- **The sweep is structural, not id-keyed.** `ScaleSubtree` recurses on the child list — a window needs no id, no script and no list entry, only a covered ancestor. Proven by three formerly "unidentified" classes.
- **Born-1x and its two builder exceptions**; the measured cause of the 1x mode-transition flash is the **visibility gate**, not sweep latency. **Paint suppression is permanently banned** (measured: did not fix the flash, blanked HUD windows).
- **Four born-correct cures, chosen by HOW the window is born** (persists-hidden → pre-scale hidden; scripted subtree → data pre-scale; code-created per open → patch the builder's constants; coupled constants → detour the builder's own placement call). The diagnostic that picks the row is counting live children vs `area=` entries under the root.
- **The game re-imposes init-cached geometry** in three measured places (ticker marquee `0xAA12F33C` per roll tick, RCI columns, Data Views legend per view selection). Diagnostic: a value right in one log line and wrong in the next with no code of yours between is a re-imposition — move the fix to data or add a pin-back pass.
- **Hooking rules.** Everything is `__thiscall` virtuals and `__thiscall` is callee-cleanup, so a wrong argument count corrupts the stack with **no partial failure mode**. Known-zero arity → `uintptr_t __thiscall Fn(void*)`; known args → `__fastcall(self, edx, …)`; **arity unknown → `__declspec(naked)` tail jmp and nothing else.** Swap the vtable on the **instance** (private 256-entry copy), never the class. Class identity is necessary, never sufficient — the same-class surgery installed on a different layout killed the game. Never call Plot from a hook; `InvalidateSelfAndParents` (slot 92) is the only safe repaint primitive.
- **The tier system.** Exactly one scale number (`Settings::spikeScaleFactor`), written once from `ScaleTier::Decide`, mirrored to `gTierF`. Decide takes the first tier satisfying `880f ≤ width`, `558f ≤ height` and `f ≤ min(w/800, h/600)` — the **density cap is not redundant**; dropping it admits resolutions with no slack. The tag gates both the art dats and `FontStyle<tag>.ini`, so "UI 2x + text 3x" is not expressible at any layer. `ScaleRound = RoundHalfUp(v·f)`, children rounding inside the parent's design frame; blit extents floor.
- **Coverage, stated honestly with three denominators**: D1 = 298 script-declared roots, 288 covered (96.6%); D2 = 17 code-created named windows, 11 covered (64.7%); combined 299/315 = 94.9%. **D3 (windows visible but unnameable) is deliberately not a percentage.**

---

## B. Genuine unknowns, ranked

Score = value to a modder (1–5) × tractability (1–5). Deduplicated: 35 raw unknowns across four lenses collapse to 28 distinct items.

### B.1 The ranking

| # | Unknown | V | T | Score | Cost |
|---|---|---|---|---|---|
| ~~1~~ | ~~Does `GZWinBtn` stretch a state cell vertically?~~ (OPEN QUESTION O1) **CLOSED 2026-08-23** — disassembled `0x9B167D`→`0x9B1541`→`sub_9B09B7`→`0x9B0B34`: `F8`/`FA` (state-cell w/h, `[this+0xf8]/[this+0xfa]`) are copied from the image interface's own per-state rect (`call [iface+0xbc]`, `rect.right−left` / `rect.bottom−top`), never from `GetW()`/`GetH()` of the window. Vertical axis matches the horizontal `imageWidth/N` rule: both are SOURCE-sized, not window-stretched. Full chain: `SC4-UI-ENGINE.md` §2.7. | | | | |
| ~~2~~ | ~~`winflag_*` name→bit map~~ **CLOSED 2026-08-23** — pinned via disassembled `GetFlag`/`SetFlag` sites (real slots `vt+0x10C`/`vt+0x110`, not the vendor header's `+0x108`/`+0x10C`): `visible`=`0x1`, `enabled`=`0x2`, `alphablend`=`0x4`, `moveable`=`0x100`, `sortable`=`0x800`, `pbuff`=`0x10000`, `pbufftrans`=`0x20000`, `pbufferase`=`0x40000`, `mousetrans`=`0x80000`, `ignoremouse`=`0x200000`, `acceptfocus`=`0x8000` — 11/13 with a measured test site (ctor `0x8903` decomposition plus `PlotComposite`/`IsPointInMe`/router disassembly already in-tree). `sizeable`=`0x200`, `pbuffvid`=`0x100000` remain header-only (`cIGZWin.h`), not independently disassembled. Full table + evidence: `SC4-UI-ENGINE.md` §3.1a; also noted in `SDK-GAPS.md` §5. | | | | |
| 3 | **Zots** (no-power/water/job/car discs) — no census row at all | 4 | 4 | **16** | imm32 sweep, then one hook |
| 4 | **The DX7 GDriver / 2D blit helper family** — no general model of the renderer | 5 | 3 | **15** | Log-only naked hook + 1 launch |
| 5 | **The `0xC2C2EB0F` singleton window factory's output** (27 live-band sites) | 5 | 3 | **15** | Live hook + 1 session |
| ~~6~~ | ~~The five automata family ids in the pick whitelist `0x4B8880`~~ **CLOSED 2026-08-23** — disassembled offline (`disasm_at.py 0x4B8880`, byte-verified): `0x74758926`, `0x278128A0` (also seen as a live occupant `GetType()` in `REGRESSION.md:11934`), `0x2890D4DE`, `0xA823821E` (the automata prop-family id, `CodePatches.cpp:5481`), `0xC772BF98`. `0xA823821E` alone branches into the nested QI(`0xE9793A65`)+type-recheck against `0xAB72FBB3` (`cSC4SignpostOccupant`) at `0x4B8947` — the doc's "plus the signpost" clause. Full chain: `SC4-WORLD-OVERLAYS.md` §2.4. | | | | |
| ~~7~~ | ~~Have the two `ScaleDim`/`CellUnit` copies drifted?~~ **CLOSED 2026-08-23** — YES, measured over the real 392-file `nam-1x` corpus at f=1.5 (`_tests\Test-ScaleDimParity.py`): width agrees on all 392, but 122 of 392 (every 176×44 sheet — the #150 shape) disagree on height, offline 66 vs runtime 68, because `ScaleTier.cpp`'s `ScaleDim` has no equivalent of `--height-exact-group`/`sNoHeightSnap`. Integer-tier no-op control holds (0/8000 at f=2,3). Full derivation: `SC4-UI-ENGINE.md` §4.6c.1. | | | | |
| 8 | The other six **dispatch-indicator categories** (settles a printed contradiction) | 3 | 4 | **12** | Read jump table + 1 suppression launch |
| ~~9~~ | ~~The ~1,850 PNGs with no `.UI` ref — consumer census~~ **PARTIALLY CLOSED 2026-08-23** — subtraction done against the real manifest (`tools/dbpf/extracted-png-tgi.csv`) union the actually-shipped `CODE_BOUND_TGIS` (341 pairs, evaluated in-process, not the §4.2 illustrative table) + ItemIcons (266) + HTML refs (59) + `.UI` refs (431): known-bound = 983 real PNGs (+26 dangling/wrong-group refs, independently matching `predictive-defect-sweep.md`'s "skipped: 22" log). **Residual = 1,297**, not ~1,850 — of the 1,853 PNGs with no `.UI` ref, only 556 are actually covered by a known non-`.UI` path. Bucketed by group and by instance-ID sub-family in `SDK-GAPS.md` §9: one candidate family is already-decoded-but-unstaged (`1421xx` = `MAYOR-MODE.md`'s mood band), two are genuinely new and unnamed (`1441xx` 288, `ec212Dxx/Exx` 106). | 3 | 3 | **9** | imm32 scan on `1441xx` + `ec212Dxx/Exx` |
| 10 | Computed (non-literal) window ids — 89 of 162 SetID sites | 3 | 4 | **12** | SetID hook, one session |
| 11 | **Resolution-as-GID for arbitrary resolutions** — a different architecture | 4 | 3 | **12** | Find the selector, one test dat |
| 12 | Reconstruct `cISC4ViewObject3D` (no header exists) | 4 | 3 | **12** | Intersect vtables from the existing hook |
| 13 | `gutters=` / `textoffsets=` / `tipoffsets=` consumers | 3 | 4 | **12** | `.rdata` string xref |
| 14 | ~~Depth-1+ nodes the code treats as roots~~ **PARTIALLY CLOSED 2026-08-23** — corpus side measured (see §F.4); code-side call-site count still open | 3 | 4 | **12** | Disassembler sweep of the winId-loader thunk's callers |
| ~~15~~ | ~~Sibling per-zoom float tables in `.rdata` (+ `.text` imm32)~~ **CLOSED 2026-08-23** — offline `.rdata` byte sweep (isolated-exactly-5-window scan + `find_imm.py` consumer check) found three more families, none sharing a consumer with `0xAA523C`: **`0xA88170`={20,30,40,50,60}f, sole consumer `0x46CD03`** (screen-px zoom table feeding the CSI-adjacent dispatch-marker builder `0x46C8B0`, already logged in `CITY-SITUATION-INDICATORS.md:149`/`REGRESSION.md:13247`); **`0xAB4330`={1,2,4,8,16}f, sole consumer `0x751CB5`** (`fmul [ecx*4+0xAB4330]` in `sub_751C80`, indexed by the GLOBAL zoom var `[0xB4C70C]`, not a per-object field — new address, module unidentified); and **four byte-identical int32 copies of `{8,16,32,73,146}`** at `0xAA2B3C`/`0xAB8BCC`/`0xABACE0`/`0xABD668` — `0xABACE0` is the known region-camera Z-table (`CodePatches.cpp:193`, consumer `0x7CBE50`), `0xABD668` is a NEW 8-reference consumer (`0x8087AA`-`0x8088E4`, one `fild [edx*4+0xABD668]`/`fdivr` pair per slot, a different module), and `0xAA2B3C`/`0xAB8BCC` return ZERO `.text` imm32 hits — inconclusive (dead/unfolded duplicate data, or reached only by non-literal addressing a byte scan can't see). Full sweep + evidence: `SC4-WORLD-OVERLAYS.md` §2.5. | | | | |
| 16 | #162's actual mechanism (see §D — 8 refuted hypotheses) | 4 | 2 | **8** | External capture + instrumented art |
| ~~17~~ | ~~Three named code-created windows with no known role~~ **CLOSED 2026-08-23 for 2 of 3, partial for the 3rd** — static disasm of all three builders (`disasm_at.py`, byte-verified against `SimCity 4.exe` 1.1.641.0): `0x9AEDEF7C` and `0xA802B4EB` are fully identified (image-file browser and its `RecordedAnimations` folder-picker sibling); `sub_7BC350`'s own role is nailed (Photo Album content/backdrop populate) but its window's id/vtable link (`0x85202C0E`/`0xAB9980`) could not be re-confirmed statically — see below and `SC4-UI-ENGINE.md` §4.8. | | | | |
| 18 | The TagKind sprite's literal size constant | 2 | 4 | **8** | Continue `0x00510690` past `0x5106E7` |
| 19 | Network drag preview + footprint ok/notok spawner | 2 | 4 | **8** | `find_imm` on `0xA90920`/`0xA9093D` |
| ~~20~~ | ~~MySim head bubble~~ **CLOSED 2026-08-19 (#191, user-confirmed)** - it is a GZWin pair 0x27DF05BE/BF, not renderer-side. Cure: kBmpxCityRoots + born-correct .UI. Aircraft landing ring still open. | | | | |
| ~~21~~ | ~~`cIGZWin` slots 95/96/97 (community names explicitly disowned)~~ **CLOSED 2026-08-23** — diffed `[vt+0x17C]`/`[vt+0x180]`/`[vt+0x184]` across all 111 window-class vtables in `tools/uimap/_work/wincensus.json` (a superset of the ~23 named classes): **zero overrides**, every class resolves to the same base bodies `0x0099C6F8`/`0x0099D57E`/`0x0099CF6A` — these three virtuals are non-polymorphic. Disassembly confirms the semantics: 95 `SetBufferToDrawTo` resolves the buffer via `GetPrivateBuffer()`/`GetParentWin()` walk (stopping at an ancestor with a private buffer or `WinFlag_DelayedPlot`), falling back to `cIGZGraphicSystem` for the root, then calls its own slot 98; 96 is 95-on-self-then-96-on-every-child (`[this+0x44]`); 97 writes `[this+0x24..0x30]` areaToDrawTo with the same ancestor-stopping rule as 95; 98 is the 96 recursion pattern applied to 97. Full derivation: `SDK-GAPS.md` §1. | | | | |
| 22 | In-world Data View tint of the 3D city | 3 | 3 | **9** | AddViewObject differential |
| 23 | Underground / subway / pipe views + in-world traffic density | 3 | 3 | **9** | Same differential |
| 24 | Why GZWinText renders purple under runtime-only scaling | 2 | 3 | **6** | Dump `[this+0xE0]` on a purple vs black sibling |
| 25 | Renderer-side highlight mode→tint mapping | 2 | 3 | **6** | Follow `vt+0x50` from `0x80D58E` |
| 26 | The signpost kinds table + **is `0x5F20A0` live at all** | 2 | 3 | **6** | One SPTEX capture |
| 27 | The unknown flyout `0x09DE8798` (script in no extracted corpus) | 2 | 3 | **6** | Log by mode + search all NINE archives |
| ~~28~~ | ~~The S3D format~~ **PARTIALLY CLOSED 2026-08-23** — hand-decoded the ConnectArrow arrow plate `{T=0x5AD0E817,G=0xBADB57F1,I=0x29F10000}` (`SimCity_1.dat` off=140503203). The register's "244 bytes" is the ON-DISK QFS/RefPack-COMPRESSED size; the format lives in the 336-byte decompressed buffer (DIR entry + embedded QFS header agree). Chunk chain `3DMD→HEAD→VERT→INDX→PRIM→MATS→ANIM→PROP→REGP` (8-byte tag+length headers, each body_end landing exactly on the next tag — except `ANIM`, whose length field is anomalous/unresolved); `VERT`=4-vertex textured quad (5 floats/vertex), `INDX`=6 indices `[0,1,2,3,0,2]` (2 triangles), `MATS` embeds the model's own name string `"29F10000_ConnectArrow_Ui8x1x3_Z1S"`. Full byte table + reproducer: `tools\research\overlays\row-15-neighbor-connection-arrows.md` §6, `python tools\dbpf\decode_s3d_plate.py`. NOT decoded: several numeric fields (HEAD's 2nd u16, VERT's pre-float 4 bytes, most of MATS, ANIM's post-tag u32) — one instance's fields, not a general reader/writer. | | | | |
| 29 | The `.UI` deserializer's **completion path** | 5 | 1 | **5** | Open-ended; highest ceiling |
| — | Lower tier: loading screens + cursor art (6), non-PNG oddballs at 2x (6), `font=NAME` tokenizer (3, operationally moot), the 44 animation-bank blobs (3) | | | | |

### B.2 The one I would attack next

**~~#1 — read `GZWinBtn`'s Plot...~~ CLOSED 2026-08-23.** Disassembly of
`0x9B167D`→`0x9B1541`→`sub_9B09B7` (`SC4-UI-ENGINE.md` §2.7) settles it:
the state-cell's destination width AND height are both copied from the
image interface's own per-state rect (`call [iface+0xbc]`, byte-verified),
never from the window's `GetW()`/`GetH()`. Height is **SOURCE-sized**, same
as the published horizontal rule — there is no vertical stretch to chase.

Consequence for #177 (the `CellUnit`-snapped strip height, currently
protected by a hand-maintained 44-entry exception list): the engine's own
`GZWinBtn` draw path performs **no vertical divide at all** for state art —
height is copied whole, not divided by a state count. A snap rule treating
strip height as needing `/N` symmetry with width is solving a problem this
class's draw path does not have. The corpus-side follow-up specified below
is still the correct next step before trusting or retiring the hand list:

- **The follow-up is derivable, not exploratory.** For every sheet in `cell-strips.txt`, collect all `.UI` nodes binding it and test whether any two have different y origins over the same x span. Empty derived set ⇒ `--height-exact-strips` is corpus-wide safe. Integer control is built in: 0 changes at 2x and 3x or the derivation is wrong.
- `14415860` (`I-c973b411`, coupled to the #162 hairlines by a single revert) can now be re-examined knowing the height rule itself is closed and SOURCE-sized — any remaining discrepancy there is #162's mechanism, not a live height-stretch question.

**Next up:** #4, the DrawArrays caller census. It is the single highest-*leverage* item in the survey — the render-art lens's one-sentence summary of the whole boundary is that everything past the UI buffer is "documented one visual at a time, by finding that visual's inline immediates, with no general model," and the CSI cost seventeen launches for exactly that reason. A log-only naked tail-jmp on the GDriver's DrawArrays slot, counting calls per caller-return-address, would name **every in-world drawer in the exe in one capture** and convert rows 8 and 10–16 of the census from "mechanism named, never seen running" to attributed. Do it after #1, and resolve the one-argument `SetTexture` call at `0x7AA075` first — a wrong arity there is a crash, not a null.

### B.3 First probes, for the top of the list

| # | Concrete first probe |
|---|---|
| ~~1~~ | ~~Disassemble `0x9B167D`...~~ **DONE 2026-08-23** — height comes from the image interface's per-state rect (cell), not the window; see §B.1 item 1 and `SC4-UI-ENGINE.md` §2.7. Run the stacked-consumer derivation over `cell-strips.txt` (still open, corpus-side). |
| 2 | Find the flag-name table in the `.UI` attribute dispatch near `0x94B995`/`0x94E516` and read the name→bit pairs directly. Corroborate two behaviourally with `GetFlag` (`[vt+0x10C]`) on a live window whose script sets them; `moveable`/`sizeable` are independently testable against the movable-window rig in `TRIAGE.md §8`. |
| 3 | Sweep the exe for the four Zot instance ids as imm32 — `0x0FD10000`, `0x107A0000`, `0x1C430000`, `0x1C440000` — with `tools/research/udriveit/exe_instance_sweep.py`. The ConnectArrow precedent (one `push` at `0x6D4A66` named the creator) says a single site is enough. **If zero hits, they are data-driven**: hook the marker factory's `OccupantSize` read at `0x4A25D3` and log the exemplar TGI. State the positive control either way. |
| 4 | Enumerate `.text` xrefs to the GDriver vtable slots (the `+0x0C` rule makes header-slot → real-offset mechanical), anchored on the two known sites: `0x007D2990`'s `[[this+0x30]]+0x0C` and the `sub_7A9D60` cloud draws. Then a log-only naked tail-jmp on the DrawArrays slot counting calls by caller return address for one session. |
| 5 | Detour the singleton's create vcall (`[edx+0x34]` in the `sub_779660` pattern) and log clsid + returned pointer + the id subsequently stamped, for one city-load-to-quit session; cross-reference against the 27 owner functions in `funcs.json`. |
| ~~6~~ | ~~Disassemble the compare chain at `0x4B8880`...~~ **DONE 2026-08-23** — see §B.1 item 6 and `SC4-WORLD-OVERLAYS.md` §2.4 for the five resolved ids. |
| ~~7~~ | ~~Run both `ScaleDim` implementations...~~ **DONE 2026-08-23** — `_tests\Test-ScaleDimParity.py` runs both over the real 392-file `nam-1x` corpus at f=1.5: width agrees (392/392), height disagrees (122/392, all 176×44 sheets, offline 66 vs runtime 68 — the missing `sNoHeightSnap`). Integer-tier no-op control holds. Gate is RED by design (documents a real drift, not a gate bug); see §B.1 item 7 and `SC4-UI-ENGINE.md` §4.6c.1. |
| 8 | Read the 7-entry jump table at `0x0046F71C` and each case's record initialiser, then re-run the CSIDRAW suppression hook (`CsiKill=1`) with a police/fire dispatch active. **If dispatch markers vanish too, census row 5 is re-attributed in one launch.** |
| ~~9~~ | ~~Subtract the known sets...~~ **DONE 2026-08-23** — subtraction complete against the manifest, using the actually-shipped `CODE_BOUND_TGIS` list (evaluated in-process) rather than the §4.2 table. Residual = 1,297 real PNGs, bucketed by group and by 2-byte instance prefix in `SDK-GAPS.md` §9. Remaining: the `.text` imm32 scan for the two largest unnamed buckets, `1441xx` (288, twin groups) and `ec212Dxx`/`ec212Exx` (106). |
| 10 | Hook `SetID` (slot `+0xFC`) for one session, log id + caller return address, bucket by owner function against `funcs.json`. The consecutive-run signature (12 ids at `0x12C`, 12 at `0x2F4`, 4 at `0x551`) makes families obvious immediately. |
| 11 | Trace where the current resolution is formatted into a GID (the `.UI` deserialisation sites are catalogued in `§8.2`) and whether it is a lookup or a computed GID. If computed, **one test dat carrying a single trivially-different script under the current resolution's GID answers it in one launch** — and would mean per-resolution UIs are shippable with no runtime rewriting at all. |
| 12 | Collect the vtables of every class seen through the existing AddViewObject hook (`0xAB4480`, `0xAB39D0`, `0xAB42F8`, `0xAB4624`, `0xAA8314`), intersect their slot layouts, write the recovered interface into a header. **The instrument already exists and already fires.** |

---

## C. Closed as impossible — with the proof, and with the scar

| Closure | Proof and positive control |
|---|---|
| **Full-screen and renderer-drawn UI, within the cIGZWin model** | With the class-Blt hook armed, **every** destination out of the UI buffer class is panel-sized (258×482, 383×156, 360×156, 340×148, 323×156, 317×148, 280×148) and not one is screen-sized. The buffer class never composites to the screen. The city LOADING/SAVING screen has no `.UI` in the 339-file corpus and never appears in the tree — 100% code-painted. **This is a boundary, not a gap** — and note it does not close §B#4: the GDriver world *beyond* the boundary is unknown, not impossible. |
| **Reading the composited frame back in-process** | Nine builds. The container has no private buffer and paints into the shared 2400×1600 screen buffer, which is GPU-only: `Lock()` succeeds, every pixel reads `(0,0,0)`, `GetColorSurfaceBits()`/`Stride()` return 0. Objective pixel measurement must come from an external screen capture. |
| **EFFDIR override from a plugin** | The manager fetches the TGI **once** at GZCOM Init `0x594A30` (one-shot flag `mgr+0x1AC`) and resolver `0x97377F` is first-provider-in-list-wins. Proven inert from **both** plugin trees by two control launches carrying an unmissable 3x scale. |
| **Buffer Blt cannot stretch** | No scaling ops in `0x826AD0` or delegate `0x826210`; a 2538×6102 dest rect changed nothing on screen. 2x is reached by a bigger buffer, a code upscale, or field doubling — never by enlarging the dest. |
| **Region rotation (#133)** | 0 refs to rotate/angle/yaw across 197 decompiled region functions, against a positive control. Tiles are baked at save time. |
| **The message queue as a born-correct hook** | A posted `WM_APP` beat `WM_TIMER` by one timer period — the game does not pump messages at all during the city-load tail. |
| **`font=NAME` on GZWinText** | The raw-string path stores property `0xFAA4AE85` with **zero consumers image-wide**. Inert by construction; the GUID form bypasses it. |
| **Sub-flyout items via the window tree** | The visible menu items are blits into the container's paint buffer, not child windows. No tree sweep reaches one at any depth. |
| Also refused/refuted with reasons on file | In-place render-surface resize; growing a game-owned buffer from our own tick; a global blt-stretch hook (refused pre-build on blast radius + hit-box divergence); the v2.70.0 per-sweep Data Views heal ("the alpha-blend order makes this family unfixable in principle"). |
| **Not impossible — closed by decision** | #97, two-knob UI/text scaling: closed by **user decision**, not by impossibility. It could be reopened. (The tier tag gates both art dats and `FontStyle<tag>.ini`, so it would need a new layer, not a new constant.) |

**The scar, and it belongs in the publication.** The boundary table in `SC4-UI-ENGINE.md §0` has been **wrong twice**: the pause/alert border and the region Mayor Rating bar were both admitted as "outside the boundary" on nulls whose instruments could not have seen them, and both turned out to be ordinary windows with art already in the package. The table is a claim needing periodic re-audit, not settled fact. **Before admitting any new element, state the positive control for every null in its evidence column: what the instrument would have shown, and whether it has ever shown it.**

---

## D. Open defects with a known mechanism

### D.1 On-screen

| ID | Mechanism | What is actually missing |
|---|---|---|
| **#162** | **NOT KNOWN — the one exception in this table.** Two phantom hairlines at 1.5x only (mayor's hat, advisor portraits, `I-c973b411`), user-confirmed. Eight hypotheses refuted by measurement: the 1.5x art is a bit-exact floor-NN copy (0/24840 and 0/20412 mismatches, differ positive-controlled); the window matches the state cell in both axes; abutting windows do not separate; no art underfills; #161's rounding fix did not remove them; and the even-row parity theory was **kill-tested** by the user holding the button — the line stayed. One live signal: an 18×2 band `src(18,36,36,38)` tiled 19× across the bottom edge of a 340×155 buffer — the middle third of a **54-wide** sheet, i.e. 1x nine-slice geometry in a scaled frame. | Which sheet and which window. `img=%p` is a runtime pointer; **no 340×155 window exists in any `.UI`** (so the owner is code-created) and **no 54-wide sheet exists in the stock extract** (so it is third-party, in another archive, or runtime-composed). A kill test on the candidate came back negative. Every offline explanation is exhausted; this needs the live composited surface, which no in-process instrument can reach. |
| **#188 / CSI** | Both size levers found and byte-decoded; both ride the tier factor. Fifteen prior eliminations recorded. | **No eyes-on for the two-quad patch.** The law minted in the same entry says 1.5x cannot discriminate two overlapping quads — so force tier 3, start a U-Drive-It mission, look at pin and disc separately, then dial back and re-check the click box (which follows `+0xD0/+0xD4`). |
| **#166** | The size-parity law: art scales as a **length** (`ScaleDim(w,f)`), a window scales by its **edges** (`R(l+w,f) − R(l,f)`). They agree only when `l·f` is an integer, so at f=1.5 a window's scaled size flips with the parity of its **live** origin. 18 of 38 tiled/1:1 observations disagree at 1.5x, 0 of 12 at both integer tiers, over 218 captures with a 16,450/16,450 parse control. Cure deployed, gated on a derived 17-id table. | That the 1px is what paints a **short bright run** was never measured — a tiled source wider than its dest is clipped, which over-covers rather than gapping. Every offline gate is structurally blind (the `.UI` only carries design origins). Eyes-on the 17 length-sized roots at 1.5x with a 2x control in the same sitting. |
| **#177** | A strip's **height** is snapped by `CellUnit` although the engine performs no vertical divide. After #171 closed the width axis, **every** remaining art-cell mismatch at 1.5x is a height mismatch. 32 of 193 strips; zero at 2x/3x. A derived subset shipped; the general rule broke `{46a006b0,14415860}` and was reverted. | The principled rule — **this is §B#1**. Current reading `{(0,2):347}`: 351 of 352 mismatches are the cell being *taller* than the window. |
| **#165** | `{46a006b0,14416315}` is 136×17 at 1x, 204×26 at 1.5x, and `204/8 = 25.5` so the engine reads a 25px cell and the strip loses 4px. `CellUnit` consults hard-coded `{3,4}`, so the per-sheet state count never reaches `ScaleDim`; `BuildSampleMap` then declines **silently, with no warning and no counter**. | Reconciliation. The arithmetic under #171's cell-first rule gives `8 × R(17×1.5) = 208`, cell 26 exact — but nobody re-read the shipped width. **Five-minute offline answer nobody has taken.** Do **not** implement HARDENING-PROPOSALS C5 (`lcm(CellUnit, states)`) — it is precisely what #157's law forbids and its worked example is arithmetically impossible. |
| **#43** | Restore-Toolbars button, fully decoded: built by `sub_7EDEB0` from `I-c973b411`, `CreateInstance(0x22ECFC47)` at `0x007EDFF6`, art `{0x856DDBAC,0x46A006B0,0x53244588}` at `0x007EE02F`, `SetID(0x43)` at `0x007EE13E`, `GZWinMoveTo(0xC, viewH−0x1C)` at `0x007EE146`, born hidden. **The builder never sets a size** — size comes entirely from the 84×19 four-frame strip. With 2x art it is 10px clipped at birth and 20px after our own sweep re-scales it. | **Neither half of the prescribed cure is in `src` today — verified this session: no `0x00000043` entry in `kNeverScaleIds` (`src/UiSpike.cpp:4847`) and no `0x007EE15A` patch in `CodePatches.cpp`.** Ship both halves together: tier-generalise `0x1C` to `round(28f)` **and** add `0x43` to `kNeverScaleIds` with a parent check (small-id collision hazard: `0x000000FF` is stamped at three unrelated sites). |
| **#172** | The "?" is two stacked buttons — Query `0x99887766` above Route Query `0x8b96b73e`, abutting at y=106, **and that abutment is the divider line the user reads as a defect**. Route Query's art exceeds its window *in stock* (design 36×21, art 37×23), so a +1/+2 stock gap becomes +3/+6 at 3x. Clamp shipped 2026-08-16. | Eyes-on. It is also the one place the pipeline must deliberately disagree with stock art dimensions, which no other builder stage does. |
| **#123** | The disaster ring/strip/bar are one welded shape. v2.71.8's seat-scaling moved the 1.5x seat from (8,77) to (13,81); **v2.71.6's own 1.5x fix was never re-tested either — two unverified corrections stacked.** | Whether the ring's hole frames the disaster button at 1.5x and whether the ring→bar junction seams. The arithmetic gates are green at all tiers but **none of them composites the three sprites**. |
| **#125** | Data Views map: the window is `ScaleRound(256,f)`, the surface is created at `blitSize` which `SetArea 0x007A8E30` snaps to the largest power of two ≤ min(W,H). They agree only when f is a power of two — 1.5x and 3x crash at the identical instruction `0x00910010` in five of the game's own exception reports. Crash cured; **Config F (fill at 768) is designed to the byte and never built.** | Nothing is built. Named hazard: the message handler also reads `+0xE4` at `0x007A86DC` as its copy extent, so a faked 768 live at that moment over-copies. Build Half 1 alone first and prove `clips=0`. |
| **#155** | 347 of 460 static-dialog buttons have an art cell 2px taller than its window at 1.5x — `CellUnit` snapping the height of a horizontal four-state strip. Structurally zero at 2x/3x. | Whether it is **visible**, and whether #177's derived subset already superseded it. The ledger never reconciles the two entries. |
| — | 1.5x flyout bottom item invisible on open, empty space when scrolled to the end. Explicitly **not art** — container height / scroll-extent arithmetic. | Everything else. Never diagnosed: no window id, no builder, no scroll-extent site. #171's cell-first law predicts a total-first height computation. |
| **#182** | `SyncStaticLayers` is the only caller of the per-package gating and runs on the AutoScale path only ⇒ with `AutoScale=0` no tier sync runs at boot, so a package stays 2x-active-by-pattern at a 1.5x tier and the #149 boot scan counts the icon covered. Half-fixed in v3.0.2. | Whether ScaleTier lines actually appear under `AutoScale=0`, and whether `IsOurPackage` was made tier-aware or only the sync path fixed. The ledger's own note says to read the manual-mode exclusion reason first — **that reason is not written down anywhere.** |
| **#104** | The window-manager teardown spin. Cause relocated: the WinMgr valid set is **wholesale empty (1543 buckets, 0 entries)** before the window tree tears down. Layout-squeeze refuted by three disassembly passes; the ordinance+dept culprit pair refuted as sufficient by run15. Instruments shipped (SpinProbe, per-launch rate recorder). | **No loop has ever been named** — no EIP, no base rate. Two runs on 2026-08-03 with byte-identical config and identical actions produced opposite outcomes, which invalidates every single-trial cell of the 9-run bisect. The one positive measurement (46 of 47 threads parked) was lost to log truncation. |
| — | Data Views scrollbar: `0xAA32BCE6` is in **both** `kAlwaysScaleCityIds` (→ `ScalePanelRoot`, `centerLeaves=false`, buttons 24×25→48×50) and `kGZWin_MenuContainer` (→ `ScaleMenuFlyouts`, `centerLeaves=true`, under which a 24×25 childless leaf trips `centerThisLeaf` and is recorded `scaledW == origW` **permanently**). | **Nothing enforces the ordering** — today the panel loop happens to run first, but that is incidental. Separately, the live geometry quoted for this family has **no log behind it** (grep of all five retained logs for `42B7C35` returns zero hits) and should be treated as unsourced. |

### D.2 Instrument and gate debt

- **`crosscheck.py` is RED and its model is two weeks stale — verified this session.** `tools/uimap/constants.json` is dated **Aug 4 07:46**; `src/CodePatches.cpp` is **Aug 18 07:51**. Latest reading: 293 entries = 278 adjudicated (262 passed, **16 MISSED**) + 15 skipped, exit 1, 41 EXTRAS. **Until it is regenerated, no reasoning about the region-screen, intro-video or cost-box patch families from the offline model is valid.** (Note: two lenses quoted this gate as GREEN and RED respectively — they were reading runs from different dates. The mtimes adjudicate: the RED reading is the current one.)
- **`gate_patch_families_combined.py` exits 1 on five unregistered tables** — the whole `#159` cost-box family (`kCostBoxHeightSite`, `kCostBoxWidthSite`, `kCostOriginBack`, `kCostOriginSite`, `kCostOriginStock`) shipped without entering the gate's WIDTHS map. **The only instrument that can see two byte patches colliding is silently blind to a whole family** — the exact gap #106 was built to close.
- **`gate_namicons.py` exits 1** (392 orphans + 1 losing icon `0xD6482A2C`). Task #152 says fixed-because-NAM-is-not-installed; `PROBES-NEEDED` and `TRIAGE-PLAYBOOK` still list it red. Nobody has recorded which is true.
- **`_tests\Test-ScaleDimParity.py` (new, register #7) exits 1** — the runtime ICONSYNTH `ScaleDim` (`ScaleTier.cpp:1309`) has no `sNoHeightSnap` equivalent, so any third-party ItemIcon of `{0x856DDBAC,0x6A386D26}` not already covered by our shipped package gets enlarged to height 68 at 1.5x where the offline pipeline ships 66 (measured on 122 of the 392 real `nam-1x` sources, all 176×44). Fix is a one-line port (`if (group == 0x6A386D26) return RoundHalfUp(v*factor);` before the `CellUnit` snap in `ScaleDim`, or an explicit height-exact parameter) — not yet done; this is engineering debt, not a research unknown.
- **`[Probe] EdgeBlt` is lazy and not self-armed — a guaranteed null with no warning.** It shares `BltClassThunk` with ThinBlt but got no arming block; `EnsureBufferClassBltHook()` has three call sites and no `s_edgeArmed` symbol exists. One-line mirror of `UiSpike.cpp:12068-12082` with its own control line.
- **U1 — `lineHeight` has never been measured at 1.5x or 3x**, so `prove_chart_legend.py` **skips 2,914 of 10,708 checks** (almost all vertical) at the two tiers shipped alongside 2x. A skip is never a pass. Two points do not determine the pt→px rule. The instrument and procedure already exist; it needs one rendered capture per tier.
- **`gate_tiled_seam` +1px clip on `1441587b` (437 vs 436) accepted as benign** with no explanation beyond the clip direction. The house law says a residual that exists at one tier only *is* the defect — check 2x and 3x.
- **#124** — the power-of-two snap exists inline in the DVMAP path **and** as `SnapMiniMapToBake`: one rule in two places, the exact shape that produced #150.
- **#141** — first city open costs 54.3s wall / 53.1s CPU / 934 MB in 1.9M reads vs 9.2s for city #2; CPU/wall = 0.92 = a saturated single core, and a 15s stretch did zero disk. The user/kernel split is recorded automatically by `Trace-CityOpen.ps1` and **nobody has run it**.

### D.3 Release blockers

- **#178 — DialogStatic 261 vs 262.** The single differing entry is `{856ddbac,46a006b0,ea7f0eae}`, **CAM's own intro splash**, absent from all four PNG corpora including the pristine 1x extract. 261 keeps it inside the dependency-gated CamUI package; 262 redistributes CAM-derived artwork to users without CAM. 2x and 3x currently ship 262. **This is a licensing decision, not an engineering one**, and it gates on the unstarted third-party audit.
- **Tasks #144–#148 all pending**: cut v3.0.0 as the first public release, GitHub publish readiness, third-party/Maxis derived-content audit, Simtropolis bundle, **verify on a near-vanilla install**. Do #148 first — the entire test history is against **one machine** with CAM, NAM and a large plugin set, and the Plugins scan is recursive so even the "stock" baselines were contaminated once.
- **`dist/` is ~24 DLL versions behind — verified this session.** `dist/SC4UIScale-v3.0.0` is dated **Aug 14 13:44**; `VERSION-HISTORY.txt` (Aug 17 19:30) tops out at v3.0.24 and `CodePatches.cpp` is Aug 18. The #166 17-id table was byte-scanned present in `build/Release/SC4UIScale.dll` and in the deployed `Plugins/SC4UIScale.dll` and **absent from the dist bundle**. Anyone validating the published reference against `dist/` is validating the first cut.
- **Stock-parity pixel pass (#31/#70) has never run.** Geometry parity on the region screen is verified clean line-by-line, but the first capture attempt failed because the workstation was locked (exclusive fullscreen), and it was never re-run. **The whole acceptance bar — "our UI should look as if it were stock" — has never been tested at the pixel level.** ~2 minutes of unlocked machine time.
- **The broad 1.5x eyes-on sweep is owed.** Every 1.5x defect in the #142–#186 range was found by a human eye on **one panel at a time**. `SCENARIOS.md` exists; there is no record of it having been walked at 1.5x.
- **2400×1800 windowed has never been launched with our layer.** Tier minimums are 1.5x = 1320×900, 2x = 1760×1200, 3x = 2640×1800; expect any 3x breakage at the bottom first (height binds, and `kTallestDesignPx` is the Graphics Options dialog, not the dock).
- **#175 has no ledger entry at all.** Keyed smoothing shipped a pink block on the Options dialog and was reverted; the cure survived as `gate_key_integrity.py` and a commented-out line at `Rebuild-Corpus.ps1:172`, but grep finds no `REGRESSION.md` section. **A refuted attribution one restart from being lost — the exact failure the #171–#178 ledger block was written to prevent.**

---

## E. Publication blockers — document contradictions, verified live

These would actively mislead a reader. Line numbers below were checked this session.

| # | Contradiction | Verified |
|---|---|---|
| **1** | **`SC4-WORLD-OVERLAYS.md` holds three states for the same row in one file.** Line **450** (§3 census row 1) still reads *"UDI offer balloon — **UNKNOWN, every named system now ELIMINATED live** … Live suspect now: the marker's own per-object size … armed in v3.0.25."* Line **490** says the balloon *"was moved UNKNOWN→DOCUMENTED with v3.0.7."* Line **558** is a **RESOLVED addendum** naming the CSI and `cSC4DispatchVehicleView::Draw 0x0046D990`. §2.5 still reads "STATUS: DOCUMENTED / eyes-on pending" — **that eyes-on ran and failed.** | Yes — all four in the current file |
| **2** | **`VERSION-HISTORY.txt` v3.0.7 asserts the refuted attribution in confident prose**: *"THE REAL BALLOON BUILDER … the offer balloon is a MARKER attachment (occupant marker type `0xCB79919B`) whose billboard strip is CODE-GENERATED by builder `0x5F5FB0` — not a window, effect, S3D model, or signpost quad."* The file ends at v3.0.24 with **no CSI entry**, although `ApplyCsiIndicatorScale` is live in `CodePatches.cpp` (Aug 18) and called under `factor>1.01 && mode>=2`. | Yes |
| **3** | **Census row 5 vs `CITY-SITUATION-INDICATORS.md` §1.** Row 5 attributes police/fire dispatch markers to marker-strip builder `0x5F5FB0`; the CSI doc says the other categories of `cSC4DispatchVehicleView` draw the dispatch/emergency markers. **Both cannot be right** — §B#8 settles it in one launch. | Yes |
| **4** | **The NineSlice `/3` owner has three addresses in print.** `0x00794100` (SC4-UI-ENGINE §4.6c, TRIAGE.md, `Upscale2x.cs` ×4, `VERIFY.md`), `0x008D9550` (REGRESSION.md, BLIT-BEHAVIOUR.md), `0x8D8800` (the `UiSpike.cpp:8718` comment and `probe_btn_nineslice.py`). **Most of it is already resolved in `REGRESSION.md:3556-3587`**: `0x00794100` is `cSC4WinAlertBorder`'s own slot-88 draw, which **calls** `0x008D9550` at `0x00794198`; `0x8D8800` is the different function an earlier audit wrongly "cleared". **What is genuinely open**: `0x008D9550` has *exactly one caller image-wide*, and it is not GZWinBMP — so **nothing yet says what performs the `/3` for a `GZWinBMP` with `edgeimage=yes`.** The rule is empirically solid (2x/3x clean, 4 uncovered px at 270 vs 418 at 276); the attribution is not. One disassembly of `0x9BC325`'s edge branch (already located at `UiSpike.cpp:8715-8719`) closes it. ⛔ **SUPERSEDED 2026-08-18 — the row above is kept because its diagnosis was right; only its "genuinely open" clause is now closed.** That disassembly was never missing: it exists three times over (`src\UiSpike.cpp` BMPX comment block, "MEASURED OFFLINE 2026-07-30" — grep `RUNTIME-SUPPLIED GZWinBMP`, *not* line 8715; `MAYOR-MODE.md`'s 2026-07-29 callee list for `0x9BC325`, which contains `008d8800` and not `008d9550`; and `_incoming\sdkgaps-06.md` §4A.6 at instruction level). **Answer: nothing external performs the `/3` — `GZWinBMP`'s own slot-88 draw `0x009BC325` divides the source rect inside its EDGE branch and then calls the blitter `0x008D8800`.** The three addresses were three different jobs, not three answers to one question: ⭐ **every one of the three drawers cuts its own cell, and neither blitter contains a divide at all.** Full write-up + the one residual open question (which operands the EDGE branch divides — `sdkgaps-06.md` says `r`/`b` only, which is an unverified `_incoming\` draft that its own OPEN section reports failing an offline recomposition) in `_tests\REGRESSION.md` §"RESOLVED 2026-08-18 — three addresses, three different JOBS". The stale VA `0x00794100` was corrected in `SC4-UI-ENGINE.md` §4.6c and `TRIAGE.md`; it is **still uncorrected** in `tools\packages\PACKAGES.md:405`, `VERIFY.md` and the `Upscale2x.cs` comments. | Yes |
| **5** | **#165 contradicts itself inside `START-HERE.md`.** Line **432**: *"OPEN AND LIVE in `z_SC4UIScale_SelectiveArt-15x.dat` right now."* Line **575**: *"CLOSED 2026-08-16 by the #171 cell-first rule … USER-CONFIRMED."* `REGRESSION.md:10002` still heads the section *"#165 OPEN, LIVE IN THE SHIPPED 1.5x PACKAGE."* Line 435 flags the table as "partly stale" without resolving it. | Yes |
| **6** | **#162 has three verdicts in one ledger file** — `:9684` "CLOSED (pending eyes-on)", `:9835` "MECHANISM FOUND (not yet fixed)", `:10033` "KILL TEST RESULT: NEGATIVE — REFUTED". **The last one wins**; `START-HERE.md:417` adjudicates correctly and then `:558` re-asserts the refuted theory 141 lines later. Do not quote `:9684` or `:9835`. | Reported by two lenses |
| **7** | **Line-number citations rot fast.** `SCALING-AXES.md`'s file:line citations measured **92% stale** (symbol within ±20 lines in 5 of 63 rows); `SC4-UI-ENGINE.md §2.1`'s own anchors moved +305..+309 lines in a single week. **VAs and struct offsets do not have this problem and are the safe currency for a public reference.** The project's own resolution — "the symbol is the anchor, the number is not" — should be applied mechanically before publishing. |Reported, consistent with §2.1 drift |
| **8** | **`src/UiSpike.cpp.before-iconprobe-2026-08-14` (732 KB, Aug 14) sits in `src/`.** It duplicated every symbol in both of my greps this session. In a published tree it doubles every hit a modder gets on `kNeverScaleIds`, `ScalePanelRoot`, the BMPX block and the NineSlice comment — with the *old* values. | Yes |
| **9** | **Three window-UI mechanisms are documented only outside the SDK doc** and should be folded in: the `align=`/valign token system and the self-scaling CENTER seat (`REGRESSION.md:11063-11110` only — its absence from §3 is the biggest hole in the format chapter); the GZWinCombo internals (factory `sub_7798C0`, `combodowncolor` at `0x779B0D`, the row builder's one-byte `inc eax` at `0x77F813`, the inclusive combo rect proven by the patched disp8 at `0x779927`); and the generic scrollbar id family. |Reported by two lenses |
| **10** | **Two key documents sit in `tools/research/_incoming/` and `tools/uimap/`, outside the curated set**: `FINAL-3-PERCENT.md` (the honest coverage denominator, the three structurally-unbounded creation channels, the §7 "structurally unknowable" table) and `coverage-matrix.md`. **They are the best-argued unknowns inventory in the repo** and are dated early August — several rows are stale in the direction of being *more closed* than they read. Two items were re-verified as genuinely still open this session (the `0x43` clip, the three role-unknown windows). | Yes |

---

## F. Coverage honesty — what this survey could not see

1. **This was a documentation survey, not a re-verification.** No lens launched the game, ran a gate, or disassembled anything new. **Every VA, offset and slot number in §A is inherited from the repo's notes.** The exe was never opened. What I verified independently this session is narrow and stated inline: file mtimes, the `0x43`/`kNeverScaleIds` absence, the NineSlice address spread, the `#165` and overlays-census contradictions, the stray `src` backup.
2. **The in-world unknown list is a lower bound, by the census's own admission.** `SC4-WORLD-OVERLAYS.md` says "discover, don't trust the list" — and walking it against the game's feature surface turns up **at least five visuals with no row at all**: zots, the in-world Data View tint, underground/pipe/subway views, in-world traffic-density colouring, and network drag preview. These are discovery gaps, not attribution gaps, and there is no reason to think five is the total. (A sixth, the aircraft landing ring, is also open — row 20 above parks it as "still open", not closed.) **Corrected 2026-08-23** — `research/KNOWN-LIMITATIONS.md` previously listed all six as a settled "renderer-drawn, no sizing lever" boundary, contradicting this row; its "Not yet probed" section now states the discovery-gap framing and cites the §B.1 rows above instead.
3. **Three creation channels are structurally invisible to every offline tool in the repo**, so no census built on them can be complete: the `0xC2C2EB0F` singleton factory (220 call edges across 129 functions; 27 in the live-UI band), the 89 of 162 `SetID` sites that pass a non-literal id, and the ~1,850 PNGs bound by no `.UI` ref. The project names the first as where the next genuinely-unknown defect will come from.
4. **The coverage denominator counts depth-0 roots by construction.** `0x00004200` is a known depth-1 node the code addresses as a top-level handle. **Measured 2026-08-23** (`tools\uimap\depth_ladder.py`, re-running the same tag grammar as `coverage_rederive.py` over all depths, positive-control-verified against `0x00004200` and all 7 previously-documented code winId pairs): **1,296 distinct ids exist at depth ≥1 somewhere in the 339-file corpus** (3,980 id-bearing occurrences: depth 1 = 2,010, depth 2 = 1,324, depth 3 = 641, depth 4 = 5) — the full candidate pool for the "covered ancestor" assumption failure mode. What remains unmeasured is narrower and harder: **how many of those 1,296 candidates the compiled code actually passes as a loader winId.** The repo's entire measured universe of such call sites is still the 7 pairs in `coverage-matrix.md` §0.6 (1 of 7 is depth-1+); closing the code-side count needs a disassembler enumerating every caller of the winId-loader thunk family and reading its pushed argument, not obtainable from the `.UI` corpus alone.
5. **The lenses disagreed about the grading bar, and the publication must pick one.** The in-world lens flagged that several rows it graded DOCUMENTED (census rows 8, 10–16) would be **PARTIAL** under the repo's own stricter law — mechanism named, never seen running. I applied the task's stated bar (a concrete anchor that predicts behaviour), which is looser. **State which bar the published reference uses, rather than silently choosing.**
6. **Two lenses quoted the same gate as GREEN and as RED.** Both quotes were accurate for their date; the mtimes adjudicate (RED is current). This is a general hazard: the repo's status lines are timestamped inconsistently, and several "CLOSED" markers in `START-HERE.md` are not supported by the ledger section they cite (§H#5, §H#6, plus `#122` — marked CLOSED USER-CONFIRMED while the ledger itself says nobody wrote a fix and flags the causal mechanism as an inference).
7. **Some closures rest on saturated or single-trial instruments.** `#122`'s DBAR instrument saturated at its 300 cap; `#104`'s 9-run bisect is invalidated by two identical-configuration runs producing opposite outcomes; `#109`'s crash closure has two 1.5x captures and **no 3x capture**.
8. **One backlog item is excluded from §D under a standing instruction from the author.** It is a known, documented item with a decoded mechanism; it is not an unknown, and its exclusion does not affect the unknowns inventory.
9. **`_working-backup/` and `_incoming/` shadow copies exist** and were visible in my greps. Anything a reader greps in the published tree may return a stale duplicate of a corrected fact unless those trees are excluded from the export.

---

## G. Method content worth publishing as such

The most transferable material in this repo is not the address list — it is the refutation record and the laws that came out of it. These generalise past SC4 and would be the reference's most-cited section.

1. **Suppression identifies; scaling does not.** Eleven subsystems were closed by elimination, and every "make it bigger" test returned an ambiguous "no change" — while one "make it stop" test named the drawer in a single launch.
2. **A `.rdata` constant sweep is blind to inline immediates.** Both CSI size levers are imm32 *inside instructions* (`C7 84 24 <disp32> <imm32>`, `mov eax,imm32`). Any "the constant is inert" verdict that did not scan `.text` immediates is a filtered null. **This one sentence would save the next modder a week** — it is why the CSI cost seventeen launches.
3. **Null is not evidence.** A probe finding nothing is not a fact until you prove it *could* have seen the thing. Publish the instrument-scope table (`SC4-WORLD-OVERLAYS.md §4`), where every probe states what it **cannot** see.
4. **Three-provenance grading**: byte-verified / carried / unknown — with the rule that an attribution built on a static model is **not documented** until a measurement matches a *prediction*.
5. **The three-number blit law**: a blit has a SOURCE, a CROP and a DESTINATION. Scaling any two is a new defect, not a partial fix.
6. **The latch law**: any value derived from a window's size at bind time is a hidden consumer of that geometry. Ask *when* content was bound, not what the geometry is now.
7. **The sheet's ROLE decides its sizing rule** — and **derive the role lists from the data that binds each sheet; never hand-list them.** Hand lists rot silently and only in the case you needed.
8. **Every rule must be a provable no-op at integer factors.** A fractional-tier metric that reads nonzero at 2x/3x is measuring its own construction. Three separate instruments in one session were doing exactly that, because they were validated against the defect and never against a known-good control of the same shape.
9. **1.5x cannot separate two overlapping elements.** Test at 3x, then dial back.
10. **A plausible name is not evidence.** `mission_selection` is a ground square, `aircraftindicate` is a landing ring, `Tag1x1x3_Helicopter` is a helipad prop — none was the balloon. Six consecutive false attributions came from plausible names.
11. **A "size" field on a world object may also be a spatial-index key.** Inflating one to probe a visual hung the game.
12. **The symbol is the anchor; the line number is not.** Measured: 92% citation rot in one document over weeks.
13. **Two blind instruments agreeing count as one.** Corroboration counts only between independent failure modes.
14. **Lead any published issues page with what is already dead.** Five dead attributions on #176, ten refuted theories on #148, eight on #162, fifteen eliminations on #188. The refutation record is the expensive part, and it is the part that stops a reader repeating the work.
---

## H. 2026-08-19 — #191 (Move In My Sim marker): what this register already knew

⭐ **THIS SECTION EXISTS BECAUSE THE REGISTER WAS NOT CONSULTED AND SHOULD HAVE
BEEN.** Five patches were written for #191 before it was opened. Three rows
already covered the target, the method, and the risk:

| row | what it says | how it applied |
|---|---|---|
| **20** | *MySim head bubble + aircraft landing ring* — **"Free if #8 is done"** | This IS #191. Named, scored, and parked. |
| **8** | *The other six dispatch-indicator categories* — "settles a **printed contradiction**" — "read jump table + 1 suppression launch" | The prescribed method. The "printed contradiction" is exactly what four patches walked into. |
| **18** | *The TagKind sprite's literal size constant* — **"continue `0x00510690` past `0x5106E7`"** | The likely size lever, with the exact resume address. |
| **28** | *The S3D format* — "hand-decode the **244-byte arrow plate**" | The green arrow is already known to be an **S3D mesh**, not a sprite. ⛔ **WRONG, corrected same day (see §H.5): the Move In My Sim green/red arrows are GZWinBMP 2D bitmaps `{46a006b0,13f15213}`/`{...,13f15214}`, not S3D.** Row 28's 244-byte plate is a DIFFERENT arrow — the row-15 neighbor-connection arrow's model — never the Move In marker's. |

**A.4 already documents the TagKind spine** (live-confirmed): 25 `Tag1x1x3_*`
exemplars bind a deliberately **NULL S3D** and carry a TagKind byte (property
`0xABB90E58`, occurring exactly once image-wide at `0x004FBFFC`). Chain:
ctor `0x004FBB40` → visitor `0x004FC710` → builder `0x004FBFE0`
(jump table `0x004FC410` on tag−1) → factory `0x00505370` (`vt+0x3C`) →
creator `0x00510690`.

### H.1 New, measured 2026-08-19 — promote these into §B

| item | status |
|---|---|
| **Move In My Sim click chain** | **SOLVED.** LTEXT `{6a231eaa,4ACE23B5}` → button `0xCA243E0C` (script `I-0a243d80`) → dispatcher `0x00776B43` (`cmp eax,0xCA243E0C ; je 0x00776B92`) → `0x00776B92` → **action `0x007755A0`**. Only TWO refs to the button id image-wide (the dispatcher and the `GetChildWindowFromID` at `0x00775002`), so there is exactly one handler. |
| **Portrait ownership** | **SOLVED.** The 19 faces are preloaded together at `0x00775239` (loop `0x0077521B..`, 48-byte stride, registers each via `call [eax+0x94]`). Owner is a **`0x0077xxxx`** subsystem — the SAME module as the click handler. |
| **Is the marker a window?** | ⛔ **THIS ROW IS WRONG — see §H.5.** "SOLVED — NO" was a false null: the 37-dump diff's baseline (first 5) was taken AFTER the marker's windows already existed (they first appear in dump #5, then persist, toggling `vis` only), so "0 new vs the first 5" could never have detected them. The marker IS a window pair, `0x27DF05BE`/`0x27DF05BF`. |
| **Does the marker route through the `0x0046Cxxx` billboard system?** | **NO — eliminated ON SCREEN.** At 2.00 the log shows category-3 icon 32→64, shared pin quad 64→128, and MYSIMTEX UV divisor 64→128, all applied, with the marker unchanged. |
| **The marker's DRAW and its size lever** | **CLOSED, see §H.5.** `GZWinBMP` children of `0x27DF05BE`/`BF`; the lever was `kBmpxCityRoots` (blit-follows-window-size) plus a size-only skip of `GZWinMoveTo` in `ScalePanelRoot`, not a size constant downstream of `0x007755A0`. |
| **What does `SIGNPOST` (`0x005F20AF`/`0x005F20BF`) actually move?** | **NEW UNKNOWN.** Applies at every tier (`balloon 44→88, raise 150→300` at 2x) across many sessions with **no eyes-on confirmation of its consumer anywhere**. Its own header records the attribution was already corrected once by screen evidence. Same profile as the `0x48E945B4` mislabel. Merge with row 26 ("is `0x5F20A0` live at all"). |
| **`ARTFETCH` cannot see cached consumers** | **NEW STRUCTURAL FACT.** It hooks the fetch; the portraits are cached at load, so the draw never passes through it. Record beside the buffer-class fact in `reference-sc4-ui-sdk-boundary`. |

### H.2 A category the SDK-boundary triage does not name

The triage assumes an element is fully inside or fully outside the SDK. This one
is **art-reachable, geometry-unreachable**:

    (a) never a window in a full-depth dump    YES
    (b) has no art in any dat                  NO  — it IS a staged dat portrait
    (c) overlays the 3D view                   YES

⛔ **Consequence: staging bigger art for such an element changes NOTHING on
screen and reads as "the staging failed".** #190 genuinely staged 72x82
portraits, the game genuinely loads them (ARTFETCH proves the fetch), and the
renderer draws at a size it computes itself — resampling the face back to 1x.

### H.3 Correction to a published reference

`tools/research/CITY-SITUATION-INDICATORS.md` §3 says of `0x0046CCB9`:
*"Patching it resizes unrelated indicators. Never touch it when working on
CSIs."* **It is category 3 only** — proven by exhaustive inbound-edge
enumeration of `0x0046C8B0..0x0046D200`: one edge in, from `cmp [esi+4],4 ; jne`
at `0x0046CC45`. Categories 3 and 4 merge at `0x46CB52` and split later, which
is why the single-`jne` reading was wrong.

### H.4 #191 — families ELIMINATED by cheap identification tests (2026-08-19)

Each of these cost one query and no patch. Recorded so they are never
re-searched, and as the positive controls for the searches themselves.

| family | test | verdict |
|---|---|---|
| **TagKind markers** (row 18's lead, `0x00510690`) | enumerated all 25 `Tag1x1x3_*` exemplar names from the archives | **NOT IT.** Every one is a spawn point or vehicle anchor: AttackHelicopter, CropDuster, Cruiseship, Fireplane, Helipad_Medical, Helipad_News, MarinaUDISpawn, Marinafront1-8, MilitaryJet, Runway, SeaportSpawnPoint, SkyDiver, Stuntplane, UFO, ferryopp/termin/termout. No MySim, no move-in, no query marker. Row 18's size constant is real but serves a different widget. |
| **`Ui8x1x3` in-world UI model family** | regex over all archives for `*Ui\dx\dx\d*` | **NOT IT.** 20 hits, ALL `ConnectArrow_Ui8x1x3_Z{1..5}{S,W,N,E}` — the network connect arrows. |
| **`*arrow*` named resources** | regex over all archives | **NOT IT.** 38 distinct names; the non-ConnectArrow ones are all `onewayarrow_0be35e*` (road one-way markings). |
| **`0x0046Cxxx` dispatch/CSI billboard system** | four patches applied and logged at 2.00 | **NOT IT — eliminated ON SCREEN.** category-3 icon 32→64, shared pin quad 64→128, UV divisor 64→128 all applied, marker unchanged. |
| **the GZWin window layer** | 37 full-depth live dumps with the marker up | **NOT IT.** 0 new windows; positive control = the Select-A-Sim grid appears in exactly one tick. |

⭐ **THE POINT OF THIS TABLE**: five families removed for the cost of four
queries and one ten-second launch, versus four patches + four deploys + four
launches that removed one family and misled three sessions. **An identification
test is an order of magnitude cheaper than a patch, and it is the SAME evidence
either way.**

⚠ **`ConnectArrow_Ui8x1x3_Z1..Z5` IS STILL WORTH KNOWING**: it establishes the
engine's convention for world-space UI markers — **one model per ZOOM level, not
one model scaled**. The Move In marker does NOT follow this convention (see
§H.5) — that hypothesis was tested and refuted, not merely left untested.

**RESOLVED, same day (dep 11:44:06), see §H.5**: what draws the Move In
marker was neither of the three leads below. It is a **GZWin pair**
(`0x27DF05BE`/`0x27DF05BF`) with `GZWinBMP` children — the earlier "SOLVED —
NO" window-layer verdict in §H.1 was itself a false null (baseline taken
after the windows already existed). Leads as they stood at the time, for the
record: (1) the three running traces from `0x007755A0` forward; (2) whether
the marker is an S3D/prop like row 28's 244-byte arrow plate — **refuted,
it is 2D bitmap art**; (3) the `0x0077xxxx` owner class identified from the
preload at `0x00775239` — correct in spirit (the click chain and portrait
preload are real facts about the feature) but not the drawer.

### H.5 CORRECTION — #191's real cause was a GZWin pair, not S3D/renderer-side

Both the §E.1 "Is the marker a window? SOLVED — NO" line and the row-28 cross
reference above are **stale**, superseded the same day by a later, definitive
measurement (`_tests/REGRESSION.md`, "#191 CAUSE FOUND — AND MY OWN TEST WAS
THE FALSE NULL"): the 37-dump window-layer null compared the LAST 8 dumps
against the FIRST 5, and the marker's windows first appear in dump #5 — the
target was baked into its own baseline, and being a persistent show/hide pair
(never destroyed, only toggled `vis`) it could never register as "new". The
marker is in fact **`0x27DF05BE`/`0x27DF05BF`**, parented to the 3D-view
root, each with a `GZWinBMP` plate child (green art `{46a006b0,13f15213}`,
red `{46a006b0,13f15214}`) plus a 36×41 portrait child. Cure: add both roots
to `kBmpxCityRoots` (so the blit hook follows the window size) and skip
`GZWinMoveTo` for them in `ScalePanelRoot` (their left/top are rewritten by
the game every frame, already in final screen space — re-anchoring them is a
second application of the scale). CLOSED 2026-08-19, user-confirmed
("YOU GOT IT"). Register row 20 already carries the correct final summary;
this note exists only so §E's mid-investigation lines stop reading as if the
S3D lead were still open or ever panned out.

### H.5 #191 — the contradiction that is now the sharpest lead (2026-08-19)

USER, on zoom behaviour: *"It works identical to all other items on screen like
the UDriveIt icons."* Constant on-screen size at every zoom = SCREEN-SPACE
billboard, exactly like the CSI/U-Drive-It indicators — which are also NOT
windows, so this is fully consistent with the live-dump null. **The per-zoom
world-geometry hypothesis (E.4) is therefore REFUTED, and the billboard system
is back in play.**

CONFIRMED by disassembly this session:
  * `AddIndicator` `0x0046F240` is __thiscall (`mov ebp,ecx`), category arrives
    as `[esp+0x280]` and indexes per-category slot tables at
    `[ebp + edi*4 + 0x60]` and `[ebp + edi*4 + 0x7C]`.
  * Call sites: `push 3` at `0x004356F5` (MySim module), `push 4` at
    `0x00528F4B` (CSI), `push 5` at `0x00528725`, `push 4`-adjacent at
    `0x005653EA`.

⛔ **SO MYSIM IS CATEGORY 3 — AND PATCHING CATEGORY 3's SIZE DID NOTHING.**
`0x0046CCBA` 32.0f → 64.0f applied at 2.00 (logged) with the marker unchanged.
Both facts are measured. One of these must therefore be false:
  (i) the Move In marker is the category-3 indicator, or
  (ii) `[esi+0xD0]/[esi+0xD4]` is what sizes what we see.

**(ii) IS THE ONE TO ATTACK, and there is a named candidate.** The category
census recorded that within `cSC4DispatchVehicleView::Draw` `0x0046D990`,
*"only `0x0046E8CB` (the record's own **+0x80 array draw**) is category-4
excluded"*. That is a SECOND draw path inside the same drawer, keyed off a
per-record array at `+0x80`, which category 4 does NOT take and category 3 DOES.
If the MySim head bubble draws through the `+0x80` array rather than the
`+0xD0/+0xD4` half-extents, then every size patch aimed at `+0xD0/+0xD4` is
correct for the CSI balloon and structurally invisible here — which is precisely
the observed pattern across four patches.

**NEXT, in order, and NO patch until one is confirmed:**
1. Read `0x0046E8CB` and the `+0x80` array: what populates it, what sizes it.
2. Establish who WRITES `+0x80` on a category-3 record — likely in the
   `0x0046C8B0` builder or in `AddIndicator`'s case-3 arm `0x0046F351`.
3. Only then look for its size lever.

⚠ **DO NOT re-test by patching.** The identification test for this is reading
which of the two draw paths a category-3 record takes — static, and it
distinguishes the hypotheses without a build.


### H.6 #191 CLOSED (2026-08-19, user-confirmed)

Two halves, both required:
  * `0x27DF05BE` / `0x27DF05BF` -> `kBmpxCityRoots`. The sweep always resized
    the window (46x97 -> 92x194); both visible parts are GZWinBMPs, which draw
    dst = src, and these roots were unhooked. The size was never wrong.
  * `I-6a9455c9` -> DialogStatic TARGETS, so the marker is BORN scaled. The tool
    latches `[ctrl+0x44]=GetH()` / `[ctrl+0x48]=GetW()/2` at init, never
    refreshes them, and re-places the window every frame with those offsets - so
    the only cure is to get the right number into the latch. Both roots in
    `kNeverScaleIds` so the born-correct geometry is not doubled.

Shipped bytes: root 69x145 / 92x194 / 138x291, portrait 54x61 / 72x82 /
108x123 at 1.5x / 2x / 3x (stock 46x97 / 36x41).
