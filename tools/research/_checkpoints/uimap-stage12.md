# CHECKPOINT - offline UI model STAGE 1 + STAGE 2 (tools\uimap)

**Date 2026-07-30. Written for a COLD agent with no chat context.**
Scope: `METHOD.md` §6 stages 1 (builder census) and 2 (constant map).
Everything is offline; the game was never launched, the exe never written,
`src\*.cpp` never edited.

---

## 1. WHAT IS DONE (all of stage 1 and stage 2)

New folder `tools\uimap\`. Read `tools\uimap\RESUME.md` first - it has the
exact command line, what `state.json` means, and what "done" looks like.

| deliverable | file |
|---|---|
| builder census, machine-readable | `tools\uimap\builders.json` |
| builder census, human | `tools\uimap\BUILDER-CENSUS.md` (641 lines) |
| constant map, machine-readable | `tools\uimap\constants.json` |
| constant map, human | `tools\uimap\CONSTANT-MAP.md` (460 lines) |
| C++ site tables, generated | `tools\uimap\generated-sites-2x.txt` (all 292) |
| ...only what CodePatches lacks | `tools\uimap\generated-NEW-sites-2x.txt` |
| resume contract | `tools\uimap\RESUME.md` |

Pipeline (each script takes `--resume`, each writes `state.json` after
**every** unit, each is idempotent):

```
scan_text.py    104 x 64KB .text shards -> 114,521 call/jmp edges
build_funcs.py  -> funcs.json, 32,113 functions
census.py       -> 192 primitive call sites in 12 owner functions
constants.py    -> 292 geometry constants, 55 twin groups
crosscheck.py   -> model vs src\CodePatches.cpp (read-only)
gen_codepatches.py -> C++ table TEXT (never edits any .cpp)
```

Quality gates, both currently green:
* `census.py`: **0 incomplete, 0 validation failures** over 192 sites.
  Validation is independent of any hand table - the text factories end
  with a font-style GUID and an R/G/B triple, so a push-run walk that
  drifted by one push stops looking like one.
* `crosscheck.py`: **MISSES 0**.

---

## 2. THE MISS / EXTRA RESULT (the acceptance test)

### MISSES - CodePatches patches it, the model did not know it

**One, at first run: `0x77F5B9` (`kDeptImm8Sites`, "deals title y").**
It is a WRONG ADDRESS. Bytes there are `BC 0A` (inside the following
`push 0xABCDE00`); the real `push 8` is at **`0x77F5B2`**, which the model
found. The shipping build logged
`dept imm8 site 0x0077F5B9 bytes unexpected - skipped` at every launch, so
that title's y never doubled.

**A concurrent session fixed exactly this at 18:10 on 2026-07-30**
(`CodePatches.cpp` v2.28.2 stanza, `0x77F5B2`), plus the popup `0x78B9D7`
and `0x78B9A1` the model also surfaced. So the cross-check now reads
**MISSES 0** and the EXTRA count moves as that file is edited. `crosscheck.py`
is the source of truth - re-run it, do not quote a number from here.

### EXTRAS - the model found it, CodePatches does not patch it (81 at last run)

81 = **56 with a non-zero value** + 25 band creates at `x=0` (real sites,
but scaling 0 is a no-op). The 56 actionable ones, grouped:

1. **15 unpatched `sub r32,38` right-margin sites** (the `W-38` right
   column). CodePatches carries 15 of the 30 that exist: the 14 Neighbor
   Deals ones plus `0x7889C0`. Missing: Ordinances `0x77C9D6 0x77CCD7
   0x77CDE6 0x77CE78 0x77D1E5 0x77D2FD`, Deals `0x77F658 0x781879`,
   slider departments `0x788416 0x7885CD 0x7887AE 0x788948 0x788BDA
   0x789038 0x789369`.
2. **5 unpatched button LEFT insets `push 14`** - `0x77D31F 0x78189B
   0x7854F8 0x787292 0x78938A`. The tables scale the RIGHT button's
   `W-195` anchor and both buttons' `H-40` y, but never the left button's
   x, so at 2x the pair is asymmetric.
3. **14 unpatched scroll-arrow y `lea r32,[r32+4]`** - `0x77D618 0x77D65C
   0x77D6A2 0x77D6E6 0x781AC9 0x781B0C 0x781B4E 0x781B91 0x78750D
   0x78754F 0x7895A9 0x7895EE 0x789635 0x78967A`. Their x (`W-33`) is
   patched; their y offset is not.
4. **Dialog titles.** Ordinances' title `(20,8)` at `0x77C928 / 0x77C926`
   is entirely unpatched - every other family's title is. Slider
   departments patch the title x (`0x788395`) but not its y (`0x788393`).
5. **8 unpatched `sub r32,2` y offsets** (`0x77C994 0x77C9D2 0x77CE3A
   0x77CE74 0x77F60A 0x77F654 0x78076F 0x7807B5`).
6. **Two unpatched column twin-pairs**: Ordinances `x=150`
   (`0x77CD9A / 0x77D2B2`), Neighbor Deals `x=250`
   (`0x7806D3 / 0x781820`).
7. **The ordinance/business text popup's own geometry** - see §4.

---

## 3. THINGS THAT SURPRISED ME (read these before extending)

### 3a. A PRIMITIVE WAS MISSING FROM THE PROJECT'S MODEL: `sub_779CA0`

It is a near-clone of `sub_779B80` (same 11 args, same roles) but creates
through win-manager `vt+0x24` (wrapping/multi-line text) instead of
`vt+0x34`. **One call site: `0x786FC2`, the master row building-name.**
`CodePatches.cpp`'s comments attribute that create to `sub_779B80`; the
constants (`0x786FA4` w=177, `0x786FAA` x=21) are right, the attribution
is not. A census that only looked for known primitives would have kept
missing it - it was found by sweeping the whole `0x779000-0x77C700`
factory block for functions that call the window manager AND drive a rect.

**The complete factory block** (this is the useful table):

| VA | arity | callers | role |
|---|---|---|---|
| `0x7794E0` | 9 | 4 | Slider (height 14 hardcoded at `0x779548`) |
| `0x7795A0` | 3 | 4 | property attach, no geometry |
| `0x779660` | 10 | 86 | TextLabel |
| `0x7798C0` | 5 | 12 | Combo (w 120 `0x77992F`, h 15 `0x779927`) |
| `0x779B80` | 11 | 7 | TextLabelW (explicit width) |
| `0x779CA0` | 11 | 1 | TextLabelWrap **(was missing)** |
| `0x77A250` | 5 | 16 | BmpArt |
| `0x77A390` | 4 | 21 | BandArt |
| `0x77A480` | 3 | 1 | band stacker, F-series (Ordinances) |
| `0x77A6F0` | 3 | 2 | band stacker, D-series |
| `0x77A960` | 2 | 1 | band stacker, `0x2BFEB0Cx` |
| `0x77B7B0` | 7 | 2 | CheckStrip (the ordinance checkbox/eye row) |
| `0x77B960` | 7 | 32 | Button |
| `0x77BEC0` | 3 | 4 | Business Deals empty box |

There are **three** band stackers, not one. `BUDGET-DETAIL-ANATOMY.md` §1
names only `0x77A6F0`.

### 3b. A CONSTANT CAN REACH A CREATE THROUGH A STACK LOCAL

`kMasterNotchSites` (`0x786F26 lea ecx,[eax+0xC8]`, `0x786F2C add
eax,0x131`) never touches a push. Both are stored into `[esp+0x1C]` /
`[esp+0x28]` before the row loop and only pushed hundreds of bytes later,
into `BmpArt(0x140155C8)` at `0x787000` / `0x787051`. A register-only
backward walk cannot see across that store. `argscan.resolve_local()`
does, by tracking the esp delta between the load and the store. **If you
extend this model to another family, keep that path** - it is the reason
those two sites were invisible.

### 3c. MY OWN FIRST CLASSIFIER MANUFACTURED PHANTOM CONSTANTS

`mov ecx, dword ptr [esp + 0x1c]` ends in a number. Reading that
displacement as an immediate produced fake "patchable constants" AND hid
the real provenance behind the load. `_imm_field()` now refuses memory
displacements (only `lea` gets its displacement treated as a value).
Anyone writing a scanner for this exe will hit the same trap.

### 3d. FUNCTION BOUNDARIES CORRECT SEVERAL DOC/COMMENT ADDRESSES

Derived from 15,176 call targets + 16,937 vtable-only starts, each
required to be preceded by a terminator byte (`CC` / `C3` / `C2 ii ii` /
`E9` / `EB` / `90`):

| builder | actual extent | what the docs/comments say |
|---|---|---|
| Ordinances | `0x77C660..0x77D7E0` | "~0x77D3xx" |
| Neighbor Deals | `0x77E600..0x781C90` | `0x77E600-0x781C8E` (right) |
| dept REFRESH + Accept/Cancel | `0x781C90..0x785740` (ONE 14.7 KB function, one `ret`) | CodePatches labels its buttons "Transportation" |
| 650-wide band dialog | `0x786690..0x7876B0` | CodePatches: "0x786C00-0x787A00 Master budget" |
| slider departments | `0x7876B0..0x7898A0` | "0x7883xx-0x7896xx" |
| ordinance popup path | `0x78B120..0x78BCA0` | - |
| panel message handler | `0x78BCA0..0x78C200` | - |

`sub_7876B0` is not only the slider-department builder: it is **the
department DISPATCHER**. It switches on `[this+0x20]`, loads that family's
metric art, stores `contentWidth -> [this+0x84]` and `rowPitch(art h/2) ->
[this+0x88]`, then calls the family builder:

* `[this+0x20]==1` at `0x787BEA`, art `0x140155F2` -> `call 0x77C660` (Ordinances)
* `[this+0x20]==2` at `0x787D04`, art `0x140155D2` -> `call 0x77E600` (Neighbor Deals)
* `[this+0x24]!=0` at `0x787E1B` -> `call 0x786690` (650-wide family)

So the metric source has **one copy per branch** (`0x787C1F/0x787C3C`,
`0x787D41/0x787D57`, ...), not the single `0x7881DE` the anatomy doc cites.

### 3e. AN UNRESOLVED NAME CONFLICT (do not guess - one live BHDR settles it)

`0x786690` is the builder for the `0x2BFEB0C7-CF` (650-wide) band family.
`CodePatches.cpp` calls it "Master budget sub-dialogs";
`BUDGET-DETAIL-ANATOMY.md` §1 calls that art family "Transportation".
Both cannot be right. Offline evidence cannot separate them. Labelled
**HYPOTHESIS** in `BUILDER-CENSUS.md`.

---

## 4. THE MOST USEFUL SINGLE RESULT: the text popup's rect, derived offline

`BUDGET-DETAIL-ANATOMY.md` §POPUP records the MEASURED popup as
`(30,176) 840x125`, with the note "height NEVER changes". The exe says
why, at `sub_78B120`:

```
0x78B995  mov ebx,[edi+0x84]     ; contentWidth (the slab-art width)
0x78B99F  push 0x7d              ; h = 125          <- literal, x4 sites
0x78B9A1  sub ebx, 0x3c          ; w = contentWidth - 60
0x78B9A5  call [edx+0xD4]        ; SetSize(contentWidth-60, 125)
0x78B9B0  push 0x7d / push ebx / call [eax+0xD4]   ; same on the content child
0x78B9B9  mov eax,[edi+0x80]     ; dialog height cursor
0x78B9C3  add eax, -0x7d         ; maxY = H - 125   (clamp)
0x78B9D7  push 0x1e / push eax / call [edx+0xE0]   ; SetPosition(30, y)
```

With `contentWidth = 900` that is **`x=30`, `w=840`, `h=125` - the
measured rect, reproduced from the binary alone.** The four `push 0x7d`
sites are `0x78B99F 0x78B9B0 0x78BACE 0x78BAEA` (two branches x two
windows) - a textbook twin group.

`125*2 = 250` and `-125*2 = -250` do **not** fit `imm8`, which is why the
height cannot be patched in place and needs a runtime pin. (The concurrent
v2.28.2 session reached the same conclusion independently and shipped the
x/right-margin patches plus a POPBOX pin.)

---

## 5. WHAT IS IN FLIGHT / NOT DONE

* **Nothing is half-written.** Every unit in `state.json` is `done`; a
  fresh `--resume` run is a no-op that reproduces identical output
  (verified by deleting 3 shards + 1 builder unit and re-running: same
  292 sites, 55 twin groups).
* **Stage 2's coverage limits** (written into `CONSTANT-MAP.md` too):
  constants that reach geometry through an **object field**
  (`mov [esi+0x9C], eax` row cursors) or through more than one local hop
  are not listed. `SetArea(const Rect*)` (`vt+0xD8`) passes a pointer, so
  its components are only caught when register-traceable at the call.
* **Twin liveness is not decided offline.** Twin groups are textual
  (same owner+primitive+role+value+encoding). Which member is dead needs
  the branch condition; the project's rule stands - patch all members.
* **Only the budget family is enumerated.** `BUILDER-CENSUS.md` §3 lists
  101 candidate primitives elsewhere in `.text` (functions with >=2
  callers that drive a rect) - that is the seed for god flyouts, mayor
  mode and data views.

## 6. NEXT ACTION (in order)

1. **Do not paste the generated tables wholesale.** Take
   `generated-NEW-sites-2x.txt` one dialog at a time, eyes-on per
   `METHOD.md` §2, starting with the two lowest-risk and highest-visibility
   groups: the **5 button left insets (`push 14`)** and the **Ordinances
   title `(20,8)`**. Both are pure `push imm8`, both fit at 2x, both have
   an obvious visual acceptance test.
2. Then the **15 missing `W-38` right-margin sites** - same constant and
   same encoding as 15 sites already shipping, so the risk is known.
3. Re-run `crosscheck.py` after every CodePatches edit; `MISSES` must stay
   0 and the EXTRA list is the remaining backlog.
4. Stage 3 (layout emulation under Unicorn) now has everything it needs:
   every primitive's VA, arity and arg roles are in `BUILDER-CENSUS.md`
   §1, and `tools\flyout-sim\emu_plot.py` is the working harness pattern.

## 7. CONSTRAINTS HONOURED

Offline only - the game was never launched or attached to. The exe was
opened read-only and never modified. Nothing outside `tools\uimap\` and
this checkpoint was written: `src\*.cpp`, the then-current HANDOFF.md session
diary (retired 2026-08-06, superseded by `START-HERE.md`; its diary content
was archived to the gitignored `_archive\`, so no file is linkable here),
`README.md`, `_tests\REGRESSION.md`, `VERSION-HISTORY.txt` and `dist\` are
untouched.
`src\CodePatches.cpp` is read by `crosscheck.py` and by nothing else -
note that a **parallel session edited it at 18:10 on 2026-07-30** (v2.28.2)
while this work was running.
