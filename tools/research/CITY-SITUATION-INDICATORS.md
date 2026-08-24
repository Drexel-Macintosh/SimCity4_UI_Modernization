# City Situation Indicators (CSI) — the U-Drive-It offer balloon

**SimCity 4 Deluxe 1.1.641.** Everything here is byte-verified against the
shipped executable and confirmed on screen. Addresses are virtual addresses at
the default image base `0x00400000`.

The CSI is the blue disc that floats above a parked U-Drive-It vehicle offering
a mission. It is the **only in-world overlay in SimCity 4 that the player
clicks**, which makes its geometry unusually load-bearing: the same numbers
that size the art also size the hit box.

---

## 1. What a CSI actually is

A CSI is **category 4** of a general "dispatch indicator" system owned by
`cSC4DispatchVehicleView`. Other categories in the same system draw the
dispatch/emergency markers. The category test is:

```
0046DD6C   cmp ecx, 4          ; 4 == CSI
```

> **Ownership.** The police/fire dispatch markers belong to THIS system, not to
> the marker-strip builder `0x5F5FB0` (`SC4-WORLD-OVERLAYS.md` §2.5). They draw
> through the SHARED pin quad below and scale with it.

The indicator is keyed on the **automaton** (the vehicle), not on a lot or a
building — `QueryInterface` for iid `0xA9B40F05` at `0x0046DDBD`. That is why
the balloon tracks a moving vehicle instead of sitting on a tile.

| thing | value |
|---|---|
| manager | `cSC4CitySituationManager`, CID `0x0BB14381`, vtable `0x00A97E58` |
| view object | `[0x00B43D04]->vt+0x58` = `cISC4DispatchManager::GetDispatchVehicleView` |
| drawer | `cSC4DispatchVehicleView::Draw` = **`0x0046D990`** (5,656 bytes, `ret 4`, reached via vtable — no direct callers) |
| geometry builder | **`0x0046C8B0`**, called from `AddIndicator` at `0x0046F616` |
| AddIndicator | `0x0046F240` — builds a ~`0x110`-byte record on its own stack, 7-way jump table at `0x0046F71C`, case 4 = CSI at `0x0046F3A2` |
| max-CSI setter | `0x00524BF0` (writes global byte `0x00B21D34`) |
| visibility setter | `0x00524C20` |
| Lua `show_CSI` | `0x00524880` |
| cheat string | `NoCSI` at `0x00A95358` |

---

## 2. The art

Eight icons, declared by the **automata scripts** in a field named
`csi_image`. Each is a PNG (`type 0x856DDBAC`) strip of **152×38 = four 38×38
hover states**, and each exists **twice, pixel-identical**, in two groups.

| instance | icon | referenced by |
|---|---|---|
| `0x4BB1305D` | car | 24 vehicle types |
| `0x4BB1305E` | helicopter | 1 |
| `0x4BB1305F` | police | 3 |
| `0x4BB13060` | ferry / UFO | 1 |
| `0x0C0305C3` | sailboat | 4 |
| `0x0C0305C4` | airplane | 2 |
| `0x0C0305C5` | tank | 1 |
| `0x0C0305C6` | train | 6 |

Groups: **`0x46A006B0`** (the one actually drawn) and **`0x1ABE787D`**.
All sixteen entries live in `SimCity_1.dat`. There is no FSH or S3D twin —
PNG only, verified by enumerating every entry with those instance ids.

> **The dual-group duplication is a trap.** A tracer that instruments only one
> of the two groups cannot exclude the art: it never touches the copy that
> draws. Enumerate *every* copy of a resource id before ruling art out.

The counts above come from measurement: all four automata LUA resources
(`type 0xCA63E2A3`, group `0x4A5E8F3F`) were QFS-decompressed and every
`csi_image` value extracted — 8 distinct values, 8 covered, 0 missing.

Field offsets in the parsed automata struct (parser `0x00521C70`):
`playerdrive` `+0x64`, `csi_image` `+0x68`, `source_building` `+0x6C`.

---

## 3. The geometry — TWO quads, not one

This is the part that matters and the part that is easy to get wrong. The
drawer emits **two** screen-space textured quads per indicator, both through
`call 0x007D2990(6 = GL_QUADS, 2, 4, &verts)`, which tail-calls the DX7
GDriver's `DrawArrays` (`[[this+0x30]]+0x0C`).

### Quad A — the pin / backing plate

64×64, UVs pinned 0..1, rotated to point at the vehicle, textured from
`[esi+0x2C]`. Its corners are **eight inline immediates** written as
`mov dword ptr [esp+disp32], imm32` (`C7 84 24 …`, imm at instruction+7):

| imm address | slot | value |
|---|---|---|
| `0x0046EABD` | V0.x | `-32.0f` |
| `0x0046EACA` | V0.y | `-32.0f` |
| `0x0046EAF6` | V1.x | `-32.0f` |
| `0x0046EB01` | V1.y | `+32.0f` |
| `0x0046EB2D` | V2.x | `+32.0f` |
| `0x0046EB38` | V2.y | `+32.0f` |
| `0x0046EB64` | V3.x | `+32.0f` |
| `0x0046EB6F` | V3.y | `-32.0f` |

The vertex array is at `[esp+0x150]`, stride `0x14`, layout `{x, y, z, u, v}`.
It is transformed in place by the loop at `0x0046ED10` (4 iterations,
`eax` 0→`0x50` step `0x14`) using a sin/cos basis built at `0x0046EB9F`.

### Quad B — the ICON, and the CLICK BOX

**`0x0046CC47: mov eax, 0x420C0000` (35.0f)** — imm32 at **`0x0046CC48`**.

It sits inside the CSI-only branch of the builder:

```
0046CC41   cmp dword ptr [esi+4], 4     ; category 4 == CSI
0046CC47   mov eax, 0x420C0000          ; 35.0f   <-- THE ICON SIZE
0046CC4D   mov [esi+0xD0], eax          ; record width
0046CC53   mov [esi+0xD4], eax          ; record height
```

`Draw` reads both fields at `0x0046EC2C` / `0x0046EC38`, multiplies by `0.5`
(`[0x00A84D2C]`) and writes ±17.5 as the corners of the second vertex array at
`[esp+0x1AC]`. That array's **UVs** come from the record at
`+0x3C/0x40`, `+0x50/0x54`, `+0x64/0x68`, `+0x78/0x7C` — per-record, which is
why those offsets look like positions and are not. The texture is `[esi+0x0C]`,
the slot holding the CSI icon TGI.

Because `+0xD0`/`+0xD4` are also what the hit test consumes, **the drawn icon
and the clickable area are the same rectangle.** Confirmed on screen: only the
inner glyph is clickable, not the surrounding pin.

> **Law:** `0x0046CCB9` is the identical instruction shape holding `32.0f` on the
> NON-CSI branch. Patching it resizes unrelated indicators.
> Never touch it when working on CSIs.
>
> ✅ **RE-VERIFIED 2026-08-24 — the law as written above is CORRECT, and a
> "widening" correction posted earlier the same day was WRONG and has been
> reverted.** A decode lane claimed this `32.0f` was shared by all six non-CSI
> categories; an adversarial verifier refuted it and a hand byte-check settled it.
> The real size assignment, exhaustively scanned over the builder
> `0x46C8B0-0x46D0F0` (every write to `+0xD0`/`+0xD4` — there are exactly four
> pairs, no more):
>
> | category | `+0xD0` / `+0xD4` | site |
> |---|---|---|
> | 0/1/2 — the **numbered** fire/police/dormant squad pins | computed text width, then `14.0f` | `fstp` `0x46CAFD` + `0x46CB03` |
> | **3 — MySim head bubble** | **`32.0f` in both** | `0x46CCB9` → `0x46CCBE`/`0x46CCC4` |
> | 4 — **the CSI** | `35.0f` + computed NextPow2 | `0x46CC47` → `0x46CC4D`/`0x46CC53` |
> | 5/6 — driving bubble, player-vehicle plumb bob | **zero** (`edx`, cleared at `0x46C920`) | `0x46CB39`/`0x46CB3F` |
>
> Why: the size block is reachable **only** through the icon path, whose sole
> entries are the two `je 0x46CB52` at `0x46C928` and `0x46C931` — taken on
> `category == 3` and `category == 4` respectively (`mov eax,[esi+4]` @`0x46C922`,
> then `cmp eax,3` / `cmp eax,4`). The number path and the no-flag path exit with
> `jmp 0x46CCE2` @`0x46CB34` and `jmp 0x46CCDA` @`0x46CB4D`, both of which **jump
> past** the block. Inside it, `cmp dword[esi+4],4` @`0x46CC41` sends 4 to the
> 35.0f store and everything reaching there otherwise — i.e. only 3 — to
> `0x46CCB9`.
>
> ⇒ `0x46CCB9` is the **MySim head bubble's** size. Patching it does **not** touch
> fire/police numbers, the driving bubble, or the plumb bob. Still never touch it
> when working on CSIs — the reason is unchanged, the blast radius is one visual.

---

## 4. Constants that are NOT the size

Scaling any of these leaves the CSI's size unchanged. What each one actually
feeds is the useful part:

| address | value | what it really does |
|---|---|---|
| `0x00A8819C` | `42.0f` | **quad TRANSLATION**, not extent. Drawn centre = `x0 + 42/2`. Scaling it 42→63 moves the balloon ~10 px and changes no size. Read at `0x0046E392`/`0x0046E3A0`; the reads at `0x0046E04E`/`0x0046E05C` are on a branch that does not run for these balloons. |
| `0x00A881A0` | `50.0f` | orbit radius — only visible when several indicators stack on one target |
| `0x00A88260` | `43.0f` | leader / pole |
| `0x00A88268` | `21.0f` | centring offset |
| `0x00A88170` | `{20,30,40,50,60,60,14,32,35,64}` | per-zoom pixel table, consumed at `0x0046CD03`. **Not the CSI path** — the CSI is pixel-fixed at every camera zoom. |
| `0x00A881AC` | `01 01 01 01 02 02 03 FF` | style byte per kind. Never scale. |

A constant can be **live and still be the wrong constant**. The 42.0f applies
cleanly, reads back correctly, and produces no visible change — which is
indistinguishable from a dead patch without knowing what it feeds.

---

## 5. How to scale a CSI

Multiply all nine immediates by the tier factor. They are `float32` inside the
instruction stream, so this is a code patch, not a data patch.

```
0x0046CC48   35.0f   ->  35.0f * f     (icon + hit box)
0x0046EABD  -32.0f   -> -32.0f * f     (pin, 8 sites)
0x0046EACA  -32.0f
0x0046EAF6  -32.0f
0x0046EB01  +32.0f
0x0046EB2D  +32.0f
0x0046EB38  +32.0f
0x0046EB64  +32.0f
0x0046EB6F  -32.0f
```

**Both-or-neither.** Scaling only the pin gives a huge plate around a tiny
glyph; scaling only the icon gives a glyph that overflows its plate. Verify
every value before writing any of them.

Supply matching art at `cell * f` — the source is scaled to fit the destination
rect, so larger art changes sharpness, never size.

Implementation: `ApplyCsiIndicatorScale` in `src/CodePatches.cpp`.

---

## 6. Method notes

Recorded because the failure modes generalise.

1. **An `.rdata` constant sweep is blind to inline immediates.** Both levers are
   `imm32` fields inside instructions. A sweep that does not scan `.text`
   immediates returns a filtered null, not a negative result.

2. **Suppression identifies; scaling does not.** A test that makes the balloons
   vanish names the drawer in one launch; a test that makes them bigger
   produces an ambiguous *no change*.

3. **When two elements overlap at similar sizes, 1.5× cannot separate them.**
   A 3× probe answers the same question immediately. Exaggerate the probe, then
   dial back.

4. **Do not judge size relationships by eye from a compressed screenshot.**
   Change one thing and ask which element moved.

5. **Names describe the owning subsystem, not the visual.** `mission_selection`
   is a ground square. `aircraftindicate` is a landing ring.
   `Tag1x1x3_Helicopter` is a helipad marker. None of them is the balloon.

6. **A capped log channel is not a null channel.** A 12-line cap consumed by the
   city-load burst hides click events that did register.

7. **Instrument the art to measure, not just to colour.** Replacing the icons
   with a solid block filling the cell turns the destination rect into
   something directly readable off one screenshot. A *hollow* frame is better
   still — it measures the art while leaving whatever is behind it visible.


---

## 5. ⚠ THE COUNT PLATE IS CENTRED — why scaling its height moved the number INTO the hat

**User-reported at 2x, 2026-08-24, and byte-proven the same day.** On the fire /
police dispatch pins the **deployment digit overlaps the helmet art**; it should
sit below it. At 1x the same pins render correctly.

**This is the second failure of the same constant, and the history matters.**
`kCsiQuad` already carries `{ 0x0046CB09, 14.0f, "count plate height (text
categories)" }`, added because at 2x the font-scaled glyphs were twice as tall
inside a quad still 14 units high, so *the number disappeared*. That fix is
applied and live (`CSI indicators x2.00 … count plate height 14.0 -> 28.0 px`).
It made the number visible and **moved the defect rather than removing it.**

**The mechanism, from the consumer at `0x0046EC2C`:**

```
0x0046EC2C  fld  [esi+0xD0]      ; plate WIDTH
0x0046EC32  fmul [0xA84D2C]      ; x 0.5   -> half width
0x0046EC38  fld  [esi+0xD4]      ; plate HEIGHT
0x0046EC3E  fmul [0xA84D2C]      ; x 0.5   -> half height
0x0046EC44  fld st(1) / fchs     ; -half...
0x0046EC4F  fld st(1) / fchs
```

`0xA84D2C = 0.5`. **The quad is built as ± half-extents, i.e. CENTRED on its
anchor.** Therefore scaling the height grows the plate **symmetrically, up and
down** — at f=2 the top edge rises by `(14f − 14)/2 = 7` and collides with the
icon above it.

> ### ⭐ THE LAW THIS MINTS
> **Scaling a CENTRED quad moves two edges, not one.** A size constant whose
> consumer multiplies by 0.5 and negates is a half-extent: changing it is a
> change to POSITION as well as SIZE. Before scaling any such constant, find its
> consumer and check for the `fmul 0.5` / `fchs` pair — and if it is centred,
> pair every size change with an anchor shift of **half the delta**, or the
> element grows into its neighbour.

**The fix shape (derived, NOT yet built):** hold the top edge still by moving the
plate's anchor **down by half the height increase**, `7·(f−1)` in plate units.
Scaling the height alone is necessary (the glyphs need the room) and provably
insufficient.

**Do not** simply revert `0x0046CB09` — that restores the ORIGINAL defect, where
the number is clipped out of existence. The two failure modes are opposite ends
of the same missing anchor term.

**Controls already in hand:** a 1x capture (correct: helmet above, digit below,
clearly separated) and a 2x capture (overlapping). Any candidate fix must
reproduce the 1x relationship at 2x, with the 1x shot unchanged.


## 5b. ✅ RESOLVED 2026-08-24 — the overlap was never inside the record

§5's centred-quad analysis is byte-true but was aimed at the WRONG mechanism, and
the live A/B proved it: holding the plate height at stock 14 (override log-proven)
changed nothing on screen. The full decode (adversarially verified, 6/6 claims,
verdict SHIP) found:

- **A record's two quads share ONE centre** — the pin quad and the digit quad are
  translated to the identical point (the 42×42 box centre). No intra-record term
  separates digit from helmet, so a single record is scale-invariant and can never
  produce a tier-dependent overlap.
- **The digit lives in a SECOND indicator record**, stacked onto the helmet
  record's anchor by the COLLISION probe: overlapping boxes displace the newcomer
  by **43.0f (`.rdata 0xA88260`)**, probing down/up/right/left (down first,
  `0x46E52A`). That 43 is screen pixels and was the one unscaled term.
- The numbers reproduce everything: 1x balloon [ay−11, ay+53] vs digit
  [ay+57, ay+71] = 4px clear; 2x balloon [ay−43, ay+85] covers digit
  [ay+50, ay+78] = the defect; plate-held-at-14 leaves the digit band covered =
  the A/B null, forced.
- **Fix SHIPPED: `ApplyStackShift`** — scale `0xA88260` by the tier factor
  (86.0 at 2x), same gate as the CSI patches, never-repin stock check
  (`0x422C0000`), log line `STACKSHIFT 0x00A88260 x%.2f`. Sole consumer proven:
  exactly 8 `.text` refs, all four probe pairs inside the dispatch view's Draw.
  Solo indicators never read it ⇒ CSI/MySim/pin and 1x are pixel-identical by
  construction; stacked separations scale with the art, which is correct.

⚠ The §5 law (centred quads: size is also position) STANDS as a law — it just
was not this defect's mechanism. Residual, stated honestly: the two-record
stacking premise is elimination-forced and matches both screenshots, but the
specific record pairing has not been logged live; the shipped patch's on-screen
result is the discriminator (digit drops exactly 43px further at 2x).
