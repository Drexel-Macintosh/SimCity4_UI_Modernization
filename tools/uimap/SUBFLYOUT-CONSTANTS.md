# SUB-FLYOUT CONSTANTS — the nested plop menus (0x8A6E61E0 / 0x8A2CAD8B)

> **STATUS: SUPERSEDED — kept as the raw first-pass scan.** This document's
> central claim (§0: the container is ART-BOUND) was **refuted** by the full
> decode: the geometry is **CODE-DERIVED** — see `SUBFLYOUT-BUILDER.md`
> (builder identification, verified constant roles) and
> `SUBFLYOUT-ART-VERDICT.md` (8/8 heights reproduced from immediates, three
> independent falsifications of the art hypothesis). The immediate inventory
> in §2 is still valid as a scan; the roles marked UNVERIFIED there are now
> verified, and the function attribution is corrected (the builder is
> `sub_7EAEB0`; `sub_7EAC70` is a different function — see
> `SUBFLYOUT-ART-VERDICT.md` §2.1). Read those two files before acting on
> anything here.

Offline only: exe read-only, game never launched, `src\` untouched.
Produced by the Stage-3 pass in `tools\uimap\emu\`. **The live dump is the
authority; everything labelled HYPOTHESIS stays that way until measured.**

---

## 0. THE ANSWER TO QUESTION 4 FIRST, BECAUSE IT GATES THE OTHER THREE

**The sub-flyout container is ART-BOUND, not code-sized. There is no 258 in
the builder — anywhere.** Do not write a patch table for the container width.

Two independent proofs:

1. **The builder loads a bitmap by TGI immediately before creating the
   container**, using the *same* art key pair as the budget band factory
   `sub_77A390`:

   ```
   0x007EB0C0:  c744243cacdb6d85   mov dword ptr [esp+0x3c], 0x856DDBAC   ; type
   0x007EB0C8:  c7442440b006a046   mov dword ptr [esp+0x40], 0x46A006B0   ; group
   0x007EB0D0:  89442444           mov dword ptr [esp+0x44], eax          ; instance <- varies per menu
   0x007EB0D4:  e8277ae1ff         call 0x00602B00                        ; resource fetch
   0x007EB0DD:  6850010000         push 0x150
   0x007EB0E9:  e8f2a4dfff         call 0x005E55E0                        ; operator new(0x150)
   0x007EB0FB:  e8f0fefaff         call 0x0079AFF0                        ; container ctor
   0x007EB11A:  68e0616e8a         push 0x8A6E61E0
   0x007EB121:  ff9200010000       call dword ptr [edx+0x100]             ; SetID(container)
   ```

   `{0x856DDBAC, 0x46A006B0, inst}` is exactly what `BUDGET-DETAIL-ANATOMY.md`
   §1 documents for the band factory — *"creates an anonymous GZWinBMP sized
   FROM THE ART"*. **Same family, same mechanism.**

2. **The literal 258 (`0x102`) does not occur in the builder's extent.** A
   whole-image scan finds 154 imm32 occurrences of `0x102`; **none** lies in
   `0x007EAC70–0x007EB84C`, and there is no imm8 encoding of 258 (it cannot
   fit one). The width you measured is the art's pixel width, and the varying
   heights (482 / 286 / 206 Freight) are simply different art instances per
   menu — which is precisely why the height varies and the width never does.

**HYPOTHESIS (high confidence, one cheap test in §5):** the cure for the
container is the same as for the budget bands — **ship that art family at
`f`** — not a `CodePatches` table. (This hypothesis was later refuted — see
the status banner above.)

---

## 1. THE BUILDER

| | |
|---|---|
| **Function** | **`sub_7EAC70`** — `0x007EAC70` … `0x007EB84C` (ends at the `int3` pad; ~3.0 KB) |
| Convention | `__thiscall`, `ret 0x18` = **6 stack args** + `this` |
| `this` | the plop/menu controller — reads `[this+0x3B0]`, `[this+0x3B4]`, `[this+0x3D0]`, `[this+0x3D4]`, `[this+0x3D8]`, and writes the built container to `[this+0x1FC]` and `[this+0x204]` |
| Creates | container object `new(0x150)` → `sub_79AFF0`, `SetID(0x8A6E61E0)` @ `0x007EB11A`; item-strip window `SetID(0x8A2CAD8B)` @ `0x007EB1F4`; and a second object `new(0x1B4)` → `sub_799DD0` @ `0x007EAF60`/`0x007EAF7F` |
| Family | `0x0079Axxx–0x0079Bxxx` — the same block as the already-cracked container `Plot 0x0079B0E0`, strip `Plot 0x0079AA70`, container `IsPointInMe 0x0079A180` → claim `0x0079AE30` (`emu_hittest.py`). **This is the disaster/sub-flyout machinery this project already reverse-engineered for hit-testing.** |
| Second strip ref | `0x007E5EB9` also pushes `0x8A2CAD8B` — **a TWIN site outside this builder**; check it before assuming one code path (law 15/16). |

The strip's rect is **not** built from immediates. It is *computed*:

```
0x007EB1D2:  ff5218      call dword ptr [edx+0x18]   ; helper fills a cRZRect at [esp+0x3c]
0x007EB1E5:  ff92d8...   call dword ptr [edx+0xd8]   ; win->SetArea(const cRZRect&)
0x007EB1F4:  68 8bad2c8a push 0x8A2CAD8B
0x007EB1FB:  ff9200...   call dword ptr [edx+0x100]  ; SetID(strip)
```

So even the strip is **helper-derived**, not literal-derived.

---

## 2. THE IMMEDIATES — ROLE UNVERIFIED, DO NOT EMIT A PATCH TABLE FROM THIS

These are every immediate `sub_7EAC70` feeds into a helper call. **I have not
decoded the helper classes, so I cannot tell you which of these is a width, a
pitch, a margin, or something that is not geometry at all.** They are listed so
the next pass starts from data, not from a scan — *not* so they can be
multiplied by `f`.

| VA | Bytes | Enc | Value | Fed to | Role |
|---|---|---|---|---|---|
| `0x007EAEEF` | `6a 05` | imm8 | 5 | `[esi vt+0x30](44,44,5)` | arg3 — UNVERIFIED |
| `0x007EAEF1` | `6a 2c` | imm8 | 44 | same, arg2 | UNVERIFIED (cell size?) |
| `0x007EAEF3` | `6a 2c` | imm8 | 44 | same, arg1 | UNVERIFIED (cell size?) |
| `0x007EAF21` | `bb 01000000` | imm32 | 1 | count floor | **not geometry** |
| `0x007EAF2D` | `bb 08000000` | imm32 | 8 | count ceiling | **not geometry** |
| `0x007EAF3D` | `3d 58020000` | imm32 | **600** | `cmp GetH(), 600` | **screen-height threshold** |
| `0x007EAF49` | `bb 06000000` | imm32 | 6 | count cap when H ≤ 600 | **not geometry** |
| `0x007EAFC9` | `6a 05` | imm8 | 5 | `[…vt+0x14](8,5)` arg2 | UNVERIFIED |
| `0x007EAFCB` | `6a 08` | imm8 | 8 | same, arg1 | UNVERIFIED |
| `0x007EAD4B` | `83 c3 7c` | imm8 | **124** | `add ebx,0x7c` on a computed extent | UNVERIFIED |
| `0x007EB15D` | `6a 1d` | imm8 | 29 | `[ebx vt+0x10](p,53,25,80,53,4,27,29)` arg8 | UNVERIFIED |
| `0x007EB15F` | `6a 1b` | imm8 | 27 | arg7 | UNVERIFIED |
| `0x007EB161` | `6a 04` | imm8 | 4 | arg6 | UNVERIFIED |
| `0x007EB163` | `6a 35` | imm8 | 53 | arg5 | UNVERIFIED |
| `0x007EB165` | `6a 50` | imm8 | **80** | arg4 | UNVERIFIED |
| `0x007EB167` | `6a 19` | imm8 | 25 | arg3 | UNVERIFIED |
| `0x007EB169` | `6a 35` | imm8 | 53 | arg2 | UNVERIFIED |
| `0x007EB17B` | `83 c0 f6` | imm8 | **−10** | `add eax,-0xa` into `[ebx vt+0x14]` | UNVERIFIED |
| `0x007EB183` | `6a 0a` | imm8 | 10 | same call | UNVERIFIED |

Not geometry, recorded so nobody chases them: `0x007EAD4E` / `0x007EAD73`
`push 0x8001` → `[vt+0x18]` / `[vt+0x1C]` on `[this+0x3D0]` — the same
**one-argument** flag pair that `POPUP-VERDICT.md` §5.2 already proved is *not*
`cIGZWinText::SetWinTextFlag` (which takes two).

### 3. imm8 CEILINGS (if any of the above ever turns out to be geometry)

Signed imm8 caps at 127. `round(stock × f)`:

| stock | f=1.5 | f=2 | f=3 | first f that overflows |
|---|---|---|---|---|
| **124** (`0x007EAD4B`) | 186 ✗ | 248 ✗ | ✗ | **f > 1.02** |
| **80** (`0x007EB165`) | 120 ✓ | 160 ✗ | ✗ | **f > 1.58** |
| 53 (×2) | 80 ✓ | 106 ✓ | 159 ✗ | f > 2.39 |
| 44 (×2) | 66 ✓ | 88 ✓ | 132 ✗ | f > 2.88 |
| 29 / 27 / 25 | ✓ | ✓ | ✓ / ✓ / 75 ✓ | ≥ 4.2 |
| 10 / −10 / 8 / 5 / 4 | ✓ | ✓ | ✓ | ≫ |

So **124 and 80 could never be byte-patched at any shipping tier** — they would
need a runtime pin, exactly as the popup height did.

### 4. NO GENERATED C++ TABLE — DELIBERATELY

No `constants.json`-schema output for `gen_codepatches.py` was produced from
this pass, and that is the finding, not a shortfall. Emitting
`{"va": "0x007EB165", "stock": 80, "scale": true}` for a value whose role is
unknown, in a builder believed at the time to be art-sized, is the exact
shape of the three failed popup builds. The rows above all carry
`"role": "UNVERIFIED"` and were not to be scaled until the helper classes at
`[esi vt+0x30/0x34/0x38]` and `[ebx vt+0x10/0x14/0x18]` were decoded — they
since have been, in `SUBFLYOUT-BUILDER.md`, which carries the verified roles.

---

## 5. THE ONE LOG LINE THAT SETTLES IT

At the first sight of `0x8A6E61E0` on a sub-menu open, log — in one line —
the container's own rect **and** the rect of its first `GZWinBMP` child:

```
SUBFLY: cont 0x8A6E61E0 (l,t WxH)  bmpchild 0x%08X (l,t WxH)  strip 0x8A2CAD8B (l,t WxH)
```

* **Predicted (art-derived, §0):** container `W == 258` **and** the BMP
  child's `W == 258` too — the container is the size of its art, and heights
  differ per menu because the art instance differs. Cure = ship that art
  family at `f`; **no patch table**.
* **A wrong prediction looks like this:** the container reads 258 while its
  BMP child reads something else (or there is no BMP child). Then the
  container *is* code-sized, §0 is wrong, and the §2 immediates become live
  candidates — start with `0x007EB165` (80) and `0x007EAD4B` (124), which are
  also the two that cannot be byte-patched.
* Either way this one line also **proves `sub_7EAC70` is the builder that
  runs**: it is the only site in the image that pushes `0x8A6E61E0`
  (whole-image imm32 scan: exactly one hit, `0x007EB11A`). If the container
  appears and the id is set, that function executed. The strip id has
  **two** sites — `0x007EB1F4` here and `0x007E5EB9` elsewhere — so log the
  strip's parent id too if you need to tell those apart.

**Outcome:** the test's "wrong prediction" branch is what happened — the
container is code-sized, §0 is wrong, and the §2 immediates became the live
candidates. The push-site attribution above also moved: the `SetID` at
`0x007EB11A` is inside `sub_7EAEB0`, not `sub_7EAC70`. See
`SUBFLYOUT-BUILDER.md`.

---

## 6. WHAT THIS PASS DID NOT ESTABLISH

* Which helper class `[esi vt+0x30/0x34/0x38]` and `[ebx vt+0x10/0x14/0x18]`
  belong to, and therefore what any §2 immediate means. **This was the
  gating unknown** — resolved in `SUBFLYOUT-BUILDER.md` (both ctors were the
  entry point: `sub_79AFF0` for the `0x150` container, `sub_799DD0` for the
  `0x1B4` object).
* Whether `0x007E5EB9` (the strip-id twin) is a live second path or dead
  (resolved: a lookup helper, creates nothing — `SUBFLYOUT-BUILDER.md` §9).
* The art instance ids per menu — they come from `[esp+0x98]`, a builder
  argument, so they are supplied by the caller, not literal here. Resolved by
  disassembling all seven call sites — `SUBFLYOUT-ART-VERDICT.md` §3.1.
