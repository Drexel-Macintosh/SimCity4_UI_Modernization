# TARGET: Primary: `tools\research\SC4-UI-ENGINE.md` — §4 "Art binding — the four paths a pixel takes to the screen" (blocks A–G below map onto §4 opener, §4.1, new §4.1b, §4.2, §4.3, §4.5, new §4.7). Secondary: `tools\research\UI-ART-BINDING.md` — new addendum at the head (block H). Third: `_tests\REGRESSION.md` — the "RUNTIME-BOUND THUMBS + THE BMPX HOOK" section's *Trap signatures* list (block I).

## SUMMARY
The four paths hold up under verification, but §4 is under-counting the store and under-describing two of them. NEW: type 0x856DDBAC is not "PNG" — it carries four container formats (2,206 PNG / 41 JFIF / 26 SHPI-FSH / 7 BMP), and the twin structure is now exact (1ABE787D is a strict 743/743 subset of 46A006B0; group 0x00000001 is an undocumented THIRD twin, 62/62). A closed census of the 431 `.UI` refs finds exactly 4 DANGLING placeholders (the task-#55 class, now a named Path 1b) and one WRONG-GROUP ref `{82b9b75b,e2b66db8}` whose group exists nowhere while its instance lives under 46A006B0 — the one shipped counter-example to "a ref's GID is honoured", and a case our own builder would misclassify as DANGLING. Path 2 now has a full census: 76 image-request constructor sites (0x602B70 ×50, 0x602B00 ×26), 67 carrying a literal group, spread over seven groups including three (6A1EED2C, AB7E5421, A9179251) that no `.UI` ever references and that no builder stages; one of those sites binds a real 296x222 Photo Album panel image that is 1x in both twins. §4.3's ItemIcon "all 176x44" is true of the 266 exemplar-referenced icons but NOT of the group: 36 of 356 are 356x58 with sequential `0xMM0000NN` instances, bound to the one-widget 89x58 template script `I-ebd0d36d` which carries no `image=` at all. §4.5 is CONTRADICTED on the Sim portraits: the Select-A-Sim picker's 22 cells are ids 0x12340000..15 and DO carry a (dangling) `image=`, not the id-0x2222 / no-image shape the doc describes; live logs also show runtime pixels landing in power-of-two cIGZBuffers (36x41 into 64x64, 152x38 and 91x77 into 256x256), which is the mechanism-level reason a Path-4 `imagerect` must never be doubled. Finally, the BMPX draw log has a GLOBAL 12-line cap that one busy window can exhaust — REGRESSION.md's trap signature "no BMPX draw line means the class is not GZWinBMP" is wrong as written.

## CONTRADICTIONS
- SC4-UI-ENGINE.md §4.5 states the Sim-portrait windows carry "no `image={g,i}` at all" and cites only `I-aa1f1f57` ids `0x22220000..04` + `0x22220055`. TRUE for the HUD panel (0 of those lines carry `image=`), FALSE for the Select-A-Sim picker: `I-0a243d80` has 22 portrait cells with ids `0x12340000..0x12340015`, each carrying `image={46a006b0,ea32f104}` plus `imagerect=(0,0,36,41)`. Path 4 therefore has two sub-shapes (no-ref vs dangling-ref) that need opposite `imagerect` treatment. Live tree confirms: `MWKID 0.27..0.47 id=0x12340000..14 vt=00ADF6A0 (124,76 72x82)` under root `0x6A243D9E` (868x762 = 2x of the script's 434x381).
- SC4-UI-ENGINE.md §4.5 opens "No art pass can ever reach these." Contradicted by our own shipped builder: `build_dialog_static.py`'s `RUNTIME_BOUND_2X` is an art pass that correctly edits Path-4b `imagerect`s for `4bf325e8` (28 rects) and `abfaef15` (14). The pixels are unreachable; the frame around them is not.
- SC4-UI-ENGINE.md §4.1 and UI-ART-BINDING.md §2 both assert "a ref's GID is honoured", citing that refs to 46a006b0/1abe787d/22dec92d/4c06f888 resolve under those exact groups. There is a sixth ref GID: `{82b9b75b,e2b66db8}` (2 occurrences, `I-cb40cfdc`, the "Apply Label"/"Remove Label" buttons). Group `0x82B9B75B` has **0 index entries in all seven shipped archives**, while instance `e2b66db8` is a real strip under `0x46A006B0` referenced by 29 other scripts. Either the engine does not honour the GID, or Maxis shipped a dead ref. Unresolved — and it is the premise clone-retargeting rests on.
- SC4-UI-ENGINE.md §4 and UI-ART-BINDING.md §2 both describe the store as "2,280 PNGs (type 0x856DDBAC)". 74 of the 2,280 are not PNG: 41 JFIF (all of group `0xCA133ECB`), 26 SHPI/FSH (inside `0x46A006B0`), 7 Windows BMP (inside `0x6A1EED2C`). `0x856DDBAC` is a generic image type.
- SC4-UI-ENGINE.md §4 ⛔ box says groups `0x46A006B0` and `0x1ABE787D` are "near-mirror twins — most IIDs exist in both". Measured: `1ABE787D` is a STRICT SUBSET — all 743/743 of its instances also exist under `46A006B0`. And there is an undocumented THIRD twin: all 62/62 members of group `0x00000001` exist under both. "Overriding one without the other" is a three-way problem for those 62.
- SC4-UI-ENGINE.md §4.3 says "all 266 are exactly 176x44". True of the exemplar-referenced icons, but the sentence reads as a property of the ItemIcon group and is false there: group `0x6A386D26` holds 356 images — 320 at 176x44 and **36 at 356x58** with sequential structured instances `0xMM0000NN`, bound to the one-widget 89x58 template script `I-ebd0d36d` (which carries no `image=` at all) and staged by nothing.
- _tests\REGRESSION.md trap signature "a portrait still 1x-in-corner with NO BMPX draw line means its window class is not GZWinBMP" is unsound: `src\UiSpike.cpp:4922` caps `BMPX draw` at 12 lines GLOBALLY for the whole session, never reset. Measured twice on 2026-07-31 — the 11:08 session emitted exactly 12 across two panels while 7 later hook events logged no draws, and in the 11:16 session one window (`0x48E945B4`) consumed 8 of the 12 in 50 ms.
- tools\selective-safe\build_selective_safe.py:872 classifies every ref absent from `store_tgis` as "DANGLING .UI ref - runtime-supplied pixels (task #47 family)". That is wrong for the wrong-group case, which needs a retarget rather than a draw hook. Latent only because `I-cb40cfdc` is in neither stage set. The classifier must test instance-level presence before declaring DANGLING.

## OPEN
- Does the engine honour a `.UI` ref's GROUP? `{82b9b75b,e2b66db8}` names a group that exists nowhere while its instance exists under `0x46A006B0`. Test: at stock resolution, open Signs & Labels and compare "Apply Label" / "Remove Label" (`0x42B7C356` / `0x42B7C353`) against a sibling binding `{46a006b0,e2b66db8}`. Identical art ⇒ the group is NOT honoured ⇒ every SHARED clone-retarget in `build_selective_safe.py` needs re-examining. Different (unskinned) ⇒ dead ref, and the classifier just needs the instance-level test.
- Is the 64x64 `cIGZBuffer` the portrait `GZWinBMP`'s image object? Measured: 36x41 blits into 64x64 buffers at ~6 Hz while portraits are on screen, and 36x41 is exactly the portrait `imagerect`. Not proven — the association is size + timing, not pointer identity. Probe to build: log `[this+0xdc]` (image ptr) inside `BmpDrawThunk` and compare with `self` in `BltClassThunk`. Settling this converts the POT-buffer law from "strongly indicated" to measured, and with it the ban on doubling Path-4 `imagerect`s.
- Do the 36 `356x58` strips in group `0x6A386D26` need 2x? They are staged by nothing, referenced by no exemplar and no `.UI`, and their consumer is the 89x58 template `I-ebd0d36d`. Their absence from every live dump is a STRUCTURAL null — no deployed instrument (MWKID/VWKID/DGPKID) walks the top-level toolbar. Build the toolbar walk first; do not spend a build on a guess.
- The Photo Album code-bound image `{0x856DDBAC, 0x1ABE787D, 0x2558A4CB}` (296x222, site `0x7BC624`) is staged in neither twin and is in no `CODE_BOUND_TGIS`. Is the Photo Album (`I-4a8cc5ea`, root `0x0A8CD3EE`, 683x582) in the scaled set? If yes this is an unfixed 1x backing; if no it is correctly untouched. One `refmap`/`SCALED_WINDOW_IDS` lookup settles it.
- Nine of the 76 image-request call sites take their group from a property or table rather than a literal (`0x5DDE3C`, `0x5DDE4E`, `0x5F4881`, `0x6464EE`, `0x675E0D`, `0x6824B9`, `0x6859C9`, `0x7EEE20`, `0x7F053C`). `0x7F053C` is the known alt-icon path; the other eight are unclassified and are the only remaining places a code-bound art group could hide.
- Groups `0xAB7E5421` (93 images: 84x 64x64, 5x 74x74, 2x 32x32, 3x 256x256; one code site `0x5F12FB`) and `0xA9179251` (4 images; site `0x7DB4E7`) are code-only with zero `.UI` refs. Their content profile reads as cursors/world overlays rather than UI chrome, but neither has been identified. Do not stage blind.
- Does the U-Drive-It vehicle picker actually render 2x thumbs? The whole 112-member `0x4C06F888` group has shipped 2x since v2.25.0 and the `imagerect`s were scaled, but `0xCBF32603` has never been opened in any session on file. Positive control: a `BMPX N instance(s) hooked under 0xCBF32603` line with NO following `BMPX draw` for a `0x2345xxxx` id.
- Should `gBmpDrawLog` become per-window-id? The global 12-line cap currently makes the BMPX instrument unreliable for exactly the verification runs it exists to serve. Small change, but it touches the shipped DLL and belongs in a deliberate build.

---

# ── BLOCK A ─────────────────────────────────────────────────────────────
# SC4-UI-ENGINE.md §4 — REPLACE the opening "The store:" paragraph and the
# ⛔ twins box.

The store: **2,280 entries of type `0x856DDBAC`** in `SimCity_1.dat` across 10
groups. **`0x856DDBAC` is an IMAGE type, not a PNG type** — 74 of the 2,280
carry a different container and every art tool must skip or special-case them:

| Payload | Count | Where |
|---|---|---|
| PNG (`89504E47`) | 2,206 | everywhere |
| JFIF/JPEG (`FFD8FFE0`) | 41 | **all of group `0xCA133ECB`** |
| SHPI/FSH (`53485049`) | 26 | inside `0x46A006B0` (e.g. `4BB0ECF3`, `144161A0`) |
| Windows BMP (`424D`) | 7 | inside `0x6A1EED2C` (`6C3568C4..C9`, 4096x4096 class) |

> EVIDENCE: `tools\dbpf\extracted-png-tgi.csv` `PngMagic` column = `no` on
> exactly 74 rows; first four bytes read back from
> `tools\dbpf\extracted\SimCity_1\T-856ddbac_G-*_I-*.png` — `ffd8ffe0` ×41
> (all `CA133ECB`), `53485049` ×26 (`46A006B0`), `424d38 03`/`424d3603`/
> `424d0803` ×7 (`6A1EED2C`).

None of the 74 is referenced from any `.UI` script and none is staged, so this
is a documented boundary and not a live defect — **but the null has a positive
control**: the same ref-map that returns 0 hits here resolves
`{46a006b0,14416240}` to 5 scripts and `{1abe787d,14416240}` to its twin, so
the matcher demonstrably works.
> EVIDENCE: cross-scan of the 74 against the 431-entry ref map → 0 hits;
> `tools\selective-safe\stage\` contains 0 of them (549 staged TGIs total:
> 433 `46A006B0` + 4 `1ABE787D` + 112 `4C06F888`).

⛔ **THE TWIN STRUCTURE IS EXACT, AND THERE ARE THREE TWINS, NOT TWO.**
`0x1ABE787D` is a **strict subset** of `0x46A006B0`: all **743/743** of its
instances also exist under `46A006B0` (which has 810, i.e. 67 of its own).
**Group `0x00000001` is a third twin**: all **62/62** of its instances exist
under BOTH `46A006B0` and `1ABE787D`. Covering a shared instance therefore
means covering up to three TGIs, not two.
> EVIDENCE: instance→group index built from `extracted-png-tgi.csv`;
> `|46A006B0|=810, |1ABE787D|=743, |∩|=743`; every one of the 62
> `0x00000001` members has `{00000001, 1ABE787D, 46A006B0}` (e.g.
> `I-14416315`).

**How exposed we are to the skew, measured:** 443 twin instances exist that we
do NOT stage (397 under `1ABE787D`, 46 under `0x00000001`) while their
`46A006B0` sibling IS staged 2x. Of those 443, **exactly one is reachable from
a shipped `.UI` ref** — `{00000001,14416315}` in `I-cba9ef16`, which
`refmap.csv` already classifies `UNSCALED / untouched`. So the Path-1 exposure
is nil; the real exposure is (a) the one code site that pushes `1ABE787D`
(§4.2) and (b) third-party scripts that reference the twin.
> EVIDENCE: set difference of `tools\selective-safe\stage\*.png` against the
> instance→group index; `refmap.csv` row
> `0x856DDBAC,0x00000001,0x14416315,UNSCALED,...,untouched`.

# ── BLOCK B ─────────────────────────────────────────────────────────────
# SC4-UI-ENGINE.md §4.1 — APPEND after the existing "No `thumbimage` /
# `containerimage` / `backimage` is in use." sentence.

**`{g,i}` is not a synonym for "art".** Five attributes in the shipped corpus
carry a brace pair, and only one of them is an image:

| Attribute | Occurrences | Distinct | Resource |
|---|---|---|---|
| `image=` | 2,962 | 431 | PNG-family, `0x856DDBAC` |
| `captionres=` | 1,777 | 546 | LTEXT `0x2026960B` |
| `btnclicksnd=` | 1,422 | 19 | sound |
| `tipres=` | 983 | 183 | LTEXT |
| `btnupsnd=` | 49 | 3 | sound |

A naive `\{[0-9a-f]{8},[0-9a-f]{8}\}` grep over a `.UI` therefore over-reports
art refs by **4,231 occurrences / ~751 distinct keys**. Always anchor on
`image=`.
> EVIDENCE: regex `([A-Za-z_]+)=\{...\}` over all 330 extracted scripts;
> 2962 + 1777 + 1422 + 983 + 49 = 7,193 brace pairs, of which 2,962 are art.

**A `.UI` ref can fail in two distinct ways, and they need opposite fixes.**
Of the 431 distinct refs, **4 do not resolve** — verified against the raw index
of all seven shipped archives with **no type filter**
(`tools\dbpf\find_tgi.py`, 108,651 index entries scanned):

| Ref | Used by | Verdict |
|---|---|---|
| `{46a006b0,ea32f104}` | `0a243d80`, `4bf325e8`, `abfaef15` | **DANGLING** — instance absent from every archive, any type |
| `{46a006b0,6b998f30}` | `4bf325e8`, `abfaef15` | **DANGLING** |
| `{46a006b0,ea7f0eae}` | `8aa9aa14` (768x600 splash bg) | **DANGLING** (`ea7f0eaf` is real, 115 KB) |
| `{82b9b75b,e2b66db8}` | `cb40cfdc` | **WRONG GROUP** — see below |

> EVIDENCE: `python find_tgi.py ea32f104 6b998f30 ea7f0eae e2b66db8 ea7f0eaf`
> → three "NOT PRESENT in any shipped archive, under ANY type"; `e2b66db8`
> and `ea7f0eaf` both `SimCity_1.dat T=0x856DDBAC G=0x46A006B0`.

⚠ **THE WRONG-GROUP REF — the one shipped counter-example to "a ref's GID is
honoured".** `cb40cfdc`'s two buttons `0x42B7C356` "Apply Label" and
`0x42B7C353` "Remove Label" (Signs & Labels) bind
`image={82b9b75b,e2b66db8}`. **Group `0x82B9B75B` does not exist in any
archive** (0 index entries across all seven), while instance `e2b66db8` is a
real 4-state strip stored under `0x46A006B0` and referenced by **29 other
scripts**. Either the engine falls back to an instance-level lookup — which
would undercut the retargeting premise this section rests on — or Maxis shipped
a dead ref and those two buttons draw with `style=standard` chrome only
(`showcaption=yes fill=yes`, so a miss is nearly invisible). **Not resolved.**
Test: open the Signs & Labels flyout at stock resolution and compare the two
buttons against a sibling that binds `{46a006b0,e2b66db8}` in the same panel;
identical art ⇒ the group is NOT honoured and every clone-retarget needs
re-examining.
> EVIDENCE: raw index scan for `G==0x82B9B75B` across all seven archives →
> **0 entries**; `T-00000000_G-96a006b0_I-cb40cfdc.ui` lines carrying
> `image={82b9b75b,e2b66db8}`; 29 scripts contain `e2b66db8`.

⛔ **OUR OWN CLASSIFIER MISREADS THIS CASE (latent).**
`build_selective_safe.py:872` labels any ref not in `store_tgis` as
`DANGLING .UI ref - runtime-supplied pixels (task #47 family)`. The wrong-group
ref is not runtime-supplied — its pixels exist, under a different group — so
the warning would send the reader to a draw hook instead of a one-line
retarget. Harmless today only because `cb40cfdc` is in neither stage set; if
Signs & Labels ever enters the scaled set, the classifier must first ask *does
this INSTANCE exist under any group?* before declaring DANGLING.
> EVIDENCE: `tools\selective-safe\build_selective_safe.py:867-877`;
> `ls tools\{selective-safe,dialog-static}\stage\ | grep cb40cfdc` → empty.

# ── BLOCK C ─────────────────────────────────────────────────────────────
# SC4-UI-ENGINE.md — NEW subsection, insert as §4.1b (between 4.1 and 4.2).

### 4.1b Path 1b — the DANGLING placeholder (looks like Path 1, behaves like Path 4)

A widget can carry a perfectly well-formed `image={g,i}` whose TGI is in **no
shipped archive**. The script parses, the ref-map counts it, the classifier
sizes it — and the pixels arrive at runtime from a binder instead. This is the
task-#55 class and it is the single most misleading shape in the engine,
because **every offline instrument reports it as ordinary Path 1**.

**Recognise it from a script:** the `image=` TGI is absent from
`extracted-png-tgi.csv` **and** from a no-type-filter index scan of all seven
archives; the sibling widgets share ONE placeholder TGI across many cells; the
`imagerect` is a bare `(0,0,W,H)` origin rect rather than an atlas crop.
**Recognise it from a build log:** `WARNING LEFT1X {g,i} ... DANGLING`.
**Recognise it in game:** a grid of cells that are correct in geometry but
whose contents are identical/blank until the panel populates.

The three shipped instances:

| Script | Cells | Ids | Placeholder | Runtime source |
|---|---|---|---|---|
| `0a243d80` Select A My Sim | 22 | `0x12340000..0x12340015` | `{46a006b0,ea32f104}` `imagerect=(0,0,36,41)` | **generated** faces (Path 4) |
| `4bf325e8` U-Drive-It vehicle | 28 | `0x23450000+i` | `{...,ea32f104}` / `{...,6b998f30}` | `{0x4C06F888, exemplar prop 0xEBFC5E5E}` |
| `abfaef15` U-Drive-It pedestrian | 14 | `0x23450000+i` | same pair | same |

> EVIDENCE (script): `tools\uiscripts\extracted\T-00000000_G-96a006b0_I-0a243d80.ui`
> lines 23–45 — 22 `GZWinBMP` with `id=0x1234xxxx area=(62,38,98,79)`-class
> 36x41 rects, `image={46a006b0,ea32f104} imagerect=(0,0,36,41)`, root
> `id=0x6a243d9e area=(200,100,634,481)` = 434x381.
> EVIDENCE (binder, disasm, exe 1.1.641): `0x770154 push 0xC12CEA13` (IID
> GZWinBMP) → `0x770159 lea eax,[esi+0x23450000]` → `0x770160 call [edx+0x94]`
> (QI child) → `0x770182 push 0xEBFC5E5E` → `0x770188 call 0x5FD480` (read
> exemplar property) → `0x77019C push 0x4C06F888` → `0x7701A9 call 0x602B70`
> → `0x7701BD call [edx+0x10]` (`SetImage`, IGZWinBMP vt +0x10). Second cell
> path identical at `0x76EEAB/0x76EEC7`.
> EVIDENCE (live, session 2026-07-31 11:08): `MWKID 0 id=0x6A243D9E
> vt=00ADC678 (400,200 868x762)` = the 434x381 root at exactly 2x, with
> children `MWKID 0.27..0.47 id=0x12340000..0x12340014 vt=00ADF6A0
> (124,76 72x82)` = the 36x41 cells at exactly 2x.

**Which levers reach it.** The *rect* is reachable, the *pixels* are not:

- `build_selective_safe.py` cannot stage the placeholder TGI (nothing to
  upscale) but **can** stage the group the binder actually loads — the whole
  112-member `0x4C06F888` group is staged 2x in place.
- `build_dialog_static.py`'s `RUNTIME_BOUND_2X` scales the placeholder
  `imagerect` **only** where the runtime pixels are themselves 2x
  (`4bf325e8` ×28, `abfaef15` ×14). `0a243d80` is deliberately excluded — its
  runtime pixels stay 1x (§4.5), and doubling the rect there reads past the
  end of a 64x64 backing buffer.
- The BMPX draw hook covers whatever is left 1x, self-limiting to a no-op when
  the pixels already fill the cell.

> EVIDENCE: `tools\dialog-static\build_dialog_static.py:314-332`
> (`RUNTIME_BOUND_2X`, with the per-script exclusion of `0a243d80` spelled out
> in the comment); `tools\selective-safe\build_selective_safe.py:401-422`
> (whole-group `0x4C06F888` staging, 616 SelectiveArt entries/tier).

⚠ **STILL UNVERIFIED IN GAME.** The U-Drive-It picker (`0xCBF32603`) was not
opened in any session on file, so the 2x thumbs have never been observed. The
positive control that WOULD prove it: a
`BMPX N instance(s) hooked under 0xCBF32603 (dialog, x2.00)` line with **no**
following `BMPX draw` line for a `0x2345xxxx` id (dst already fills ⇒ m clamps
to 1.0). Absence of both lines today means the panel was never opened, not that
it works.

# ── BLOCK D ─────────────────────────────────────────────────────────────
# SC4-UI-ENGINE.md §4.2 — APPEND after the confirmed-instances table.

**THE CANONICAL PATH-2 STANZA, and its census.** All code-bound art goes
through one of two constructors for an image-request object:

```
push <flags2>                  ; -> [obj+0x2C] (byte)
push <flags1>                  ; -> usually 1
push <instance>                ; -> [obj+0x10]
push <group>                   ; -> [obj+0x0C]
push 0x856DDBAC                ; -> [obj+0x08]   TYPE  (see the type-0 note)
lea  ecx,[esp+..]              ; the request object
call 0x602B70                  ; ctor, __thiscall, ret 0x14
...    call [vt+0x10]          ; SetImage / SetImages on the target window
call 0x602BE0                  ; release the request
```

`0x602B70` writes vtable `0x00A856CC` at `[obj]` and a second vtable
`0x00A80810` at `[obj+0x14]`; the TGI triple lives at `[obj+0x08..0x10]`.
`0x602B00` is the same ctor taking the TGI **by pointer** (`[eax+0]/[eax+4]/
[eax+8]` → `+8/+0xC/+0x10`), used where the triple already sits in a table.
`0x602BE0` is the matching release (99 call sites).

> EVIDENCE: disasm `0x602B70`–`0x602BD8` (`mov [esi],0xA856CC`;
> `mov [esi+8],eax`; `mov [esi+0xc],ecx`; `mov [esi+0x10],edx`;
> `mov [esi+0x14],0xA80810`; `ret 0x14`) and `0x602B00`–`0x602B4A`.
> Worked example `0x7B616E-0x7B6181`: `push 0x4A2805FF; push 0x6A1EED2C;
> push 0x856DDBAC; lea ecx,[esp+0x5c]; call 0x602b70`.

**Census (relocation-free scan of every `E8 rel32` in the image):**

| | |
|---|---|
| `call 0x602B70` | 50 sites |
| `call 0x602B00` | 26 sites |
| **total art-request sites** | **76** |
| with a literal PNG-store group within 72 bytes | **67** |
| group taken from a property / table (no literal) | **9** — `0x5DDE3C`, `0x5DDE4E`, `0x5F4881`, `0x6464EE`, `0x675E0D`, `0x6824B9`, `0x6859C9`, `0x7EEE20`, `0x7F053C` |

Group histogram over the 67: `46A006B0` 53 · **`6A1EED2C` 7** · `4C06F888` 2 ·
`6A386D26` 2 · **`AB7E5421` 1** · `1ABE787D` 1 · **`A9179251` 1**.

> EVIDENCE: byte-window scan of the 72 bytes preceding each call for any
> 4-byte LE value equal to one of the 10 PNG-store groups. A push-only scan
> finds just 46 — the TrendBar site loads its group into a register
> (`0x7ED4B4 mov ebp,0x856DDBAC; 0x7ED4B9 mov edi,0x46A006B0`) and the
> ItemIcon site stamps it to the stack — so **"no push ⇒ no code binding" is
> a false test**; scan for the constant, not the instruction.

**Three groups are bound ONLY from code — they have zero `.UI` refs and are in
no builder's list.** Ref-GID occurrence counts across the whole corpus are
`46A006B0` 2,834 · `1ABE787D` 108 · `22DEC92D` 13 · `4C06F888` 4 ·
`82B9B75B` 2 · `00000001` 1 (= 2,962, closing §4.1's total exactly). Nothing
else. So:

| Group | Stored | `.UI` refs | Code sites | Content (measured dims) | Verdict |
|---|---|---|---|---|---|
| `0x6A1EED2C` | 20 (13 PNG + 7 BMP) | 0 | 7 | 4096x4096 / 3840x3840 BMPs, 512x279, 256x149, 128x128 | **not UI** — splash/loading/world textures. Leave alone. |
| `0xAB7E5421` | 93 | 0 | 1 (`0x5F12FB`) | 84×64x64, 5×74x74, 2×32x32, 3×256x256 | cursor/overlay class. Unclassified — do not stage blind. |
| `0xA9179251` | 4 | 0 | 1 (`0x7DB4E7`) | 2×64x64, 2×32x32 | same. |

⚠ **ONE REAL GAP FOUND.** Site `0x7BC624` loads
`{0x856DDBAC, 0x1ABE787D, 0x2558A4CB}` — a **296x222** image — for the **Photo
Album** panel (`I-4a8cc5ea`, root `0x0A8CD3EE` at 683x582). Neither that TGI
nor its `46A006B0` twin is staged, and neither appears in `CODE_BOUND_TGIS`.
If the Photo Album is ever scaled, this is a 296x222 backing that stays 1x.
> EVIDENCE: disasm `0x7BC611 push 0x2558A4CB; 0x7BC616 push 0x1ABE787D;
> 0x7BC61B push 0x856DDBAC; 0x7BC624 call 0x602B70`, bracketed by
> `push 0x4A8CD356` / `push 0xA8CD3FF` = ids inside
> `T-00000000_G-96a006b0_I-4a8cc5ea.ui` (captions "Photo Album", "Albums",
> "expand", "Close"). Both twins present in `SimCity_1.dat`, both 296x222,
> neither in `tools\selective-safe\stage\`.

**TYPE 0 IS A LEGAL TYPE ARGUMENT.** The two `0x4C06F888` thumbnail sites push
`0` where every other site pushes `0x856DDBAC`, yet the group's only stored
entries are `0x856DDBAC`. Treat `type = 0` as "resolve by group+instance", and
do not assume a plugin override must match a type the caller never supplies.
> EVIDENCE: `0x76EEB0 push 0` and `0x7701A1 push ebx` (ebx = 0, xor'd at
> `0x76FDC3`) as arg1 at both `4C06F888` sites vs `push 0x856DDBAC` at
> `0x7B6178`, `0x777AA1`, `0x7BC61B`, `0x777196`, `0x7B1CC8`, `0x4A6C19`.

# ── BLOCK E ─────────────────────────────────────────────────────────────
# SC4-UI-ENGINE.md §4.3 — APPEND, and CORRECT the "all 266 are exactly
# 176x44" bullet's scope.

The "all 176x44" claim is true of the **266 exemplar-referenced** icons; it is
**not** true of the group. Group `0x6A386D26` holds **356** images in two size
classes:

- **320 × 176x44** — the 4-cell 44x44 ItemIcon strips (266 of them carry an
  exemplar reference; 54 are spares/unused).
- **36 × 356x58** — a completely separate family with **sequential structured
  instances** `0xMM0000NN`: `00000001..0A` (10), `02000001..0B` (11),
  `03000002..05` (4), `04000001..09` (9), `08000001`, `0D000001`. 356/4 = a
  4-cell **89x58** state strip. **No exemplar references any of them and no
  `.UI` script does either** (group `6A386D26` has zero `image=` refs).

Their consumer is a **one-widget template script**: `I-ebd0d36d` is 1,482 bytes
total — a `GZWinGen id=0x000A0000 area=(22,18,111,76)` (89x58) with a single
child `GZWinBtn id=0x000A0002 area=(0,0,89,58) style=toggle showcaption=no`
and **no `image=` attribute at all**. The game stamps this template once per
menu category and supplies the strip from `{0x856DDBAC, 0x6A386D26,
0xMM0000NN}` at runtime — the `MM` byte is a category id, `NN` the slot.
89 px is also exactly the sidebar strip width the dock instruments report
(`DCKID ... W=88`), which places the family on the left toolbar.

> EVIDENCE: PNG IHDR dims over all 356 `T-856ddbac_G-6a386d26_*` files →
> `{176x44: 320, 356x58: 36}`; `tools\itemicons\_work\item_icons.csv` yields
> **266** distinct property values, none below `0x100`, so the sequential
> family is disjoint from the exemplar pool;
> `tools\uiscripts\extracted\T-00000000_G-96a006b0_I-ebd0d36d.ui` (full text
> is two `<LEGACY>` tags); the group constant `0x6A386D26` occurs at exactly
> three code addresses — `0x78EE15`, `0x7ECB50`, `0x7F038F` (the imm32 bytes
> of the instructions §4.2 already lists at `0x78EE11` etc.).

**Coverage:** `z_SC4UIScale_ItemIcons.dat` ships 266 entries at 352x88 — the
36 356x58 strips are staged by **nothing**. Whether they need to be is
UNVERIFIED: no deployed instrument enumerates the top-level toolbar, so their
absence from every live dump is a **structural null**, not a measurement.
The positive control does not exist yet — MWKID/VWKID walk the main window and
the 3D view roots, DGPKID walks flyout containers, and none of them descends
into the toolbar. Build that walk before spending a build on this.
> EVIDENCE: `tools\itemicons\REPORT.md` (266 entries, all 352x88); grep of
> `id=0x000A0000`/`0x000A0002` across the live log and the archived
> `.bak-godfix` dump → 0 hits, from instruments that never visit that subtree.

# ── BLOCK F ─────────────────────────────────────────────────────────────
# SC4-UI-ENGINE.md §4.5 — CORRECT the "My Sims portraits" bullet and APPEND
# the buffer law.

⚠ **CORRECTION.** §4.5 currently says "every portrait window is a `GZWinBMP`
with `imagerect=(0,0,36,41)` and **no `image={g,i}` at all**". That is true of
the **HUD** panel `I-aa1f1f57` (`0x22220000..04` + `0x22220055`, 0 of them
carry `image=`) but **false of the Select-A-Sim picker**: `I-0a243d80`'s 22
portrait cells are ids **`0x12340000..0x12340015`** and every one of them
carries `image={46a006b0,ea32f104}` — a dangling ref (§4.1b). Path 4 has two
sub-shapes and they are distinguished only by whether an `image=` attribute is
present:

- **4a — no `image=` at all.** Nothing for a ref scan to see; the window is
  invisible to `build_selective_safe.py` entirely. (`aa1f1f57` portraits;
  `0x8A1F1EEF` with `imagerect=(0,0,100,100)`.)
- **4b — dangling `image=`.** Counted by every ref scan, warned as
  `LEFT1X ... DANGLING`, and its `imagerect` *is* editable — which is exactly
  the trap, because editing it is right for `4bf325e8`/`abfaef15` and wrong
  for `0a243d80`.

> EVIDENCE: `grep -c "image={"` over the `0x2222` lines of
> `T-00000000_G-96a006b0_I-aa1f1f57.ui` → **0**; the same test over
> `I-0a243d80`'s `0x1234` lines → all 22 carry `{46a006b0,ea32f104}`.

**THE POWER-OF-TWO BUFFER LAW (new, and it is why a Path-4 `imagerect` must
never be doubled).** Runtime-generated pixels are composed into a
**power-of-two `cIGZBuffer`** (class vt `0x00AC1400`) and occupy only a
top-left sub-rect of it. Doubling the widget's `imagerect` therefore does not
sample more picture — it samples **past the live data into the POT padding**.

| Source blit | Destination buffer | Seen |
|---|---|---|
| 36x41 at `dst(0,0,36,41)` | **64x64** | 395 sampled blits (1-in-12 sampling ⇒ ~4,700 real) |
| 152x38 at `dst(0,0,152,38)` | **256x256** | 3 |
| 91x77 at `dst(0,0,91,77)` / 91x51 at `dst(0,205,91,256)` | **256x256** | 25 / 13 |

36x41 is exactly the portrait `imagerect`; the 36x41→64x64 blits repeat at
~6 Hz per portrait and cycle through distinct buffer objects (one per cell)
while the picker is open.
> EVIDENCE: session 2026-07-31 11:08, `SC4UIScale.log` `DCBUF` lines from the
> `cIGZBuffer::Blt` class hook (`kBufClassVt = 0x00AC1400`, slot 29 = `+0x74`;
> `src\UiSpike.cpp:717, 1809-1811, 1046-1057`), e.g.
> `DCBUF self=28DC5F14 dst(0,0,36,41) src 36x41 selfWxH=64x64 cont=0`
> interleaved with the `BMPX draw id=0x12340011..15` lines. ⚠ The live log
> rotates on every game start — these lines are gone from the current file;
> the 11:08 session is the citation.
> HYPOTHESIS (not proven): that the 64x64 buffer IS the image object handed to
> the portrait `GZWinBMP`. The association rests on the exact 36x41 match and
> the co-timing, not on a pointer identity. Positive control to settle it:
> log the `GZWinBMP` image pointer at `[this+0xdc]` inside `BmpDrawThunk` and
> compare it with `self` in `BltClassThunk`. That probe does not exist.

**LIVE CONFIRMATION of "the draw follows the source".** §4.5 derives this from
the `0x9BC325` disasm; the deployed hook now measures it. `BMPX draw
id=0x12340015 img 36x41 win 72x82 -> dst 72x82 (x2.00)` means the pre-hook
destination rect was **36x41 inside a 72x82 window** — dst size == src size,
the window rect unread, exactly as decoded.
> EVIDENCE: session 11:08 lines for `id=0x22220000/0x22220001/0x22220055`
> (HUD) and `0x12340011..15` (picker); the thunk's guard `w == sw && h == sh`
> at `src\UiSpike.cpp:4910` is what makes the printed `img WxH` the *original*
> dst.

⚠ Also soften §4.5's opening: **"No art pass can ever reach these"** is true of
the *pixels* and false of the *frame around them* — `RUNTIME_BOUND_2X` is an
art pass reaching a Path-4b widget, correctly, in two of three cases.

# ── BLOCK G ─────────────────────────────────────────────────────────────
# SC4-UI-ENGINE.md — NEW subsection §4.7, place immediately after §4.6 and
# before the ⛔ "ART AND RUNTIME SCALE MUST MOVE TOGETHER" box.

### 4.7 DECISION PROCEDURE — a widget renders wrong: which path feeds it?

Run these in order. Each step is cheap and each one *excludes* paths, so stop
at the first that answers. Do not skip to step 6 because the symptom "looks
like a draw bug" — four of the six wrong-art bugs in this project were data.

**0. Is the script you are reading the script the game loaded?**
Compare the LIVE root size / child count against the stock script. A mismatch
means a plugin replaced it (§4 load-order law) and every step below must be
re-run against the mod's file.
*Recognise:* `MWKID`/`VWKID`/`DGPKID` root dims ≠ stock `area=` ÷ tier.

**1. Does the widget have an `image=` in its script at all?**
*No* → **Path 4a** (or a template script, §4.3). Skip to 6.
*Yes* → continue.
*Recognise:* anchor the grep on `image=`, never on a bare `{g,i}` — 4,231 of
the 7,193 brace pairs in the corpus are LTEXT or sound.

**2. Does that exact TGI exist in the store?**
`grep` `extracted-png-tgi.csv`.
*Yes* → **Path 1**. Go to 3.
*No* → run `tools\dbpf\find_tgi.py <instance>` (all seven archives, no type
filter) before concluding anything:
 - instance found under a **different group** → **wrong-group ref**; the fix is
   a retarget, not a hook (§4.1);
 - instance found **nowhere** → **Path 1b, dangling**; go to 5.
*Recognise from a build log:* `WARNING LEFT1X ... MISSING-2X` = Path 1 with no
upscale; `WARNING LEFT1X ... DANGLING` = Path 1b **or** a wrong-group ref — the
builder cannot currently tell those apart.

**3. Path 1 confirmed. Is the art staged, and under the right TGI(s)?**
Check `refmap.csv` for the classification and `stage\` for the file. Remember
the three twins: an instance may need `46A006B0`, `1ABE787D` **and**
`0x00000001`.
*Symptom map:* quarter-art with black fill = art and scale disagree;
two icons in one cell = a 1x multi-state strip in a doubled cell
(`imageWidth/4`); sheared 9-slice = `imagerect` not doubled with the art.

**4. Is the widget's `imagerect` consistent with the art it actually got?**
`edgeimage=yes` ⇒ 9-slice insets; `edgeimage=no` + non-origin rect ⇒ atlas
crop; both are bitmap pixels and both must move with the art. For code-BUILT
dialogs the game bypasses our staged script, so the live rect needs the BMPRECT
pass (`[this+0xd8]` flag `0x10`, rect at `[this+0xe8..0xf4]`).

**5. Path 1b. Find the BINDER, not the art.**
Locate the panel's populate function and look for the canonical stanza
(§4.2): `push <inst>; push <group>; push <type>; call 0x602B70` followed by
`call [vt+0x10]`. The group in that push is the group to stage. Then decide the
rect: **double the placeholder `imagerect` iff the runtime pixels are
themselves 2x**; if the pixels are generated (Path 4b), leave the rect alone
and let the draw hook do it.

**6. Path 2 / 2b / 4 — separate them by where the constant lives.**
 - `.text` immediate near a `0x602B70`/`0x602B00` call → **Path 2**. Lever:
   stage 2x in place at the original TGI; there is no rect to retarget.
 - exemplar property (`0x8A2602B8` Item Icon, `0x2BE8E6CB` gauge strips,
   `0xEBFC5E5E` thumbs) with the type+group as exe constants → **Path 2b**.
   Lever: the matching per-property dat (`z_SC4UIScale_ItemIcons*.dat`).
 - `sc4://image/<g>/<i>` inside an LTEXT → **Path 3**. Lever: the art layer,
   but check for a deliberate 1x hole first (`{46a006b0,14416264}`).
 - no TGI anywhere → **Path 4**. Lever: **code only**. Confirm with a
   `BMPX draw id=... img WxH win WxH` line where `img` ≠ `win`.

**7. Only now reach for a hook.** Confirm the class positively before hooking:
`vt == 0x00ADF6A0 && vt[88] ∈ {0x9BC325} ∪ FlashGuard thunks`. And read the
cap note in Block I before treating a missing `BMPX draw` line as evidence.

**What no instrument can tell you today** (build it rather than guessing):
there is **no live probe that reports which TGI a window's image object holds**.
`MWKID`/`VWKID`/`DGPKID` give id + class + rect; `BMPX draw` gives source and
destination *sizes*; `DCBUF` gives buffer blits. The field map to build it is
already known — image pointer at `[this+0xdc]`, flags holder at `[this+0xd8]`
(`vt[10](bit)`: `0x10` = has imagerect, `0x20` = 1:1, `8` = edge), imagerect at
`[this+0xe8..0xf4]`.
> EVIDENCE: `src\UiSpike.cpp:4849-4851, 5086-5107` (field map),
> `src\UiSpike.cpp:6398-6460` (DPROBE is geometry-only).

# ── BLOCK H ─────────────────────────────────────────────────────────────
# UI-ART-BINDING.md — insert as a second addendum immediately below the
# "ADDENDUM 2026-07-29 — TWO LIMITS OF 'SELECTIVE IS ENOUGH'" block.

> ### ADDENDUM 2026-07-31 — THIS DOCUMENT IS THE 2026-07-21 SNAPSHOT
>
> The binding model has since been re-derived from the exe and is maintained
> in **`SC4-UI-ENGINE.md` §4** (paths 1, 1b, 2, 2b, 3, 4a, 4b + the §4.7
> decision procedure). Three statements below are now known to be imprecise;
> read §4 for the current text.
>
> 1. **"PNG, TypeID 0x856DDBAC"** (§2) — `0x856DDBAC` is a generic image type.
>    74 of the 2,280 entries are **JFIF (41, all of group `CA133ECB`), SHPI/FSH
>    (26, inside `46A006B0`) and BMP (7, inside `6A1EED2C`)**. None is
>    `.UI`-referenced, so the selective mechanism is unaffected — but an art
>    tool that assumes PNG will trip over them.
>    EVIDENCE: `PngMagic=no` on 74 rows of `extracted-png-tgi.csv`; magic bytes
>    read back from the extracted payloads.
>
> 2. **"a ref's GID is honored"** (§2) — true for 5 of the 6 ref GIDs.
>    `{82b9b75b,e2b66db8}` in `I-cb40cfdc` names a group that exists in **no
>    archive** while its instance is a real strip under `46A006B0`. Whether
>    the engine falls back or the buttons simply draw unskinned is the one open
>    question that could undermine clone-retargeting.
>    EVIDENCE: raw index scan, 0 entries for `G==0x82B9B75B` across all seven
>    archives.
>
> 3. **"the gap between 2,280 stored and 431 .UI-referenced is the
>    exemplar/code bound majority"** (§2 / reason 4) — correct in shape, and
>    now quantified: 266 exemplar ItemIcons, 61 `sc4://` HTML refs, **76 code
>    image-request sites** across 7 groups, plus three groups
>    (`6A1EED2C`, `AB7E5421`, `A9179251`) that are code-only and largely **not
>    UI at all** (4096x4096 world/loading textures, 64x64 cursors).
>
> **Open question O1 (button-strip vertical stretch, §3) is still open.** No
> test has been run; the shared standard strips are still treated as SHARED.

# ── BLOCK I ─────────────────────────────────────────────────────────────
# _tests\REGRESSION.md — CORRECT the "Trap signatures" bullet in the
# "RUNTIME-BOUND THUMBS + THE BMPX HOOK" section.

⚠ **CORRECTION (2026-07-31): "a portrait still 1x-in-corner with NO BMPX draw
line means its window class is not GZWinBMP" is WRONG AS WRITTEN.** The
`BMPX draw` logger has a **global, session-lifetime cap of 12 lines** shared by
every hooked window. One busy window exhausts it and every later window then
draws correctly while logging nothing.

- Measured, session 2026-07-31 11:08: exactly **12** `BMPX draw` lines
  (`0x22220000/01/55`, then `0x12340011..15`) against **11 city roots + 25
  dialog instances hooked**, with 7 further `BMPX ... hooked under
  0x6A243D9E` events afterwards and no draw line for any of them.
- Measured, session 11:16 (same day, log rotated): the U-Drive-It marker
  `0x48E945B4` alone consumed 8 of the 12 within 50 ms —
  `BMPX draw id=0x48E945B4 img 64x64 win 128x128 -> dst 128x128 (x2.00)` ×8.
  A picker opened after that point would have produced no evidence at all.

> EVIDENCE: `src\UiSpike.cpp:4922` `if (gBmpDrawLog < 12)` — `gBmpDrawLog` is
> a file-scope `int` (`src\UiSpike.cpp:4891`), never reset.

**Corrected signature.** A portrait 1x-in-corner with no `BMPX draw` line means
**one of three things**, in this order of likelihood: (a) the 12-line budget was
already spent — check whether ANY `BMPX draw` lines exist in the session; (b)
the window is under no hooked root — check for the matching
`BMPX N instance(s) hooked under 0x...` line; (c) only then, the class is not
`GZWinBMP`. **Recommended fix:** make the cap per-`gBmpCurId` (or a small
per-id budget) so one window cannot blind the instrument for the rest — the
third instrument of this shape in the project, per METHOD.md "YOUR OWN
INSTRUMENTS CAN LIE".

Also worth adding to the same section: **the live log rotates on every game
start.** The 11:08 evidence above no longer exists in
`Documents\SimCity 4\Plugins\SC4UIScale.log`. Any log line quoted in a doc must
carry its session timestamp, and anything load-bearing must be copied into
`_tests\captures\` before the next launch.

