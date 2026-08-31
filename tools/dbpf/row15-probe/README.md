# Overlay-census row 15 — the neighbour-connection arrow probe (v2)

**What it is:** one data-only plugin DAT, 43 records, that moves five levers at
once so a single play session can say what draws and what sizes the arrow plate
standing at a city's edge where a road / rail / highway / avenue crosses into the
next tile.

**Why it exists:** row 15's channel claim — *"a prop occupant drawn from an S3D
model"* — is graded STRONG_INFERENCE, not proven. Every byte behind it is
CREATION-side (exemplar fetch, position, orient, attribute stamp, grid insert);
not one is DRAW-side. This DAT turns the inference into a measurement.

**Build:** `python build_row15_probe.py` → `zzzz_SC4UIScale_ROW15_PROBE.dat`
(17,824 bytes). The script refuses to leave a file behind unless ~3,700 checks
pass, including six mutations that must each be caught by their named control.
The game install and the Plugins tree are opened **read-only**.

> The DAT's sha256 changes between builds: the DBPF header carries two unix
> timestamps. Everything else is byte-deterministic, and check S7 proves it by
> making `DbpfPack.exe` pack the same staging directory and comparing every byte
> outside those two dwords.

---

## ⚠ READ THIS FIRST — the run is VOID without the baseline pass

The single largest failure mode of this probe is not a wrong lever. It is that
**"I see no change" and "there was nothing there to change" are the same
observation.** No neighbour connection in the city, no zot on screen, wrong
camera — each produces a confident fake null, and that mistake has already cost
this project four play sessions.

So the reading is a **comparison, never a sighting.** Do the baseline first,
with the probe **not** installed:

| # | Baseline step (probe NOT installed) | Why |
|---|---|---|
| 0 | If the city has **no** neighbour connection, build one: any road/rail/avenue/highway run to a city edge that continues into a developed neighbour tile. Confirm the arrow plate appears. | Without this, an arrow null is meaningless. |
| 1 | Screenshot the arrow at **max zoom (Z5)**, then at **Z3**, noting the camera rotation. Do not move the camera afterwards. | Gives a size reference at two of the five zoom models. |
| 2 | Open the cheat box and enter **`TastyZots`** (or leave a lot unpowered). Screenshot a no-power zot balloon at a **fixed zoom you write down**. | The zot is the probe's positive control. Its baseline must be at the same zoom as the reading. |
| 3 | Screenshot the **news-ticker strip** across the bottom of the city HUD. | Baseline for canary K2. |
| 4 | From the region view, click any **unestablished** tile so the **"Establish City"** dialog opens. Screenshot its buttons. Cancel out. | Baseline for canary K1. Harmless. |

Then install, restart SC4, load the **same city**, restore the **same camera**,
and re-take all four shots. Read them side by side.

---

## Install / remove

```
INSTALL   create   <Documents>\SimCity 4\Plugins\zzzz-SC4UIScale-row15-probe\
          copy     zzzz_SC4UIScale_ROW15_PROBE.dat  into it
          restart  SC4 (plugins are read once, at process start)

REMOVE    delete that folder, restart SC4.  Nothing else changes: the DAT
          touches no save, no ini, no game file.  The install was never written
          to at any point.
```

The folder name sorts after `zzz-SC4UIScale`, which matters only for canary K2
(see below). Nothing else in this DAT is contested by any plugin — the builder
asserts that against every one of the 387 DBPF files in the live Plugins tree
and refuses if it ever stops being true.

**Rebuild the probe if you change the SC4UIScale tier.** K2 is shipped at the
dimensions of whatever currently wins the load order for that TGI (measured at
build time: `010-SC4UIScale\z_SC4UIScale_SelectiveArt.dat`, 1514×86, the 2x
tier). Shipping stock's 757×43 where a 1514×86 sheet is live would change the
strip's *geometry* as well as its colour and conflate "the DAT loaded" with "the
HUD broke".

---

## The five overrides

| Role | Records | TGI | Edit | Asks |
|---|---|---|---|---|
| **B** | 20 | `5AD0E817 / BADB57F1 / 29F10000..29F10430` | every position float32 × **3.0** | Is the plate sized by **its own model vertices**? |
| **C** | 1 | `6534284A / C977C536 / 29F10000` | OccupantSize `{8,3,1}` → **`{8,24,1}`** | Is the plate sized **creation-side**, from its occupant footprint? |
| **E** | 20 | `5AD0E817 / BADB57F1 / 0FD10000..0FD10430` | every position float32 × **3.0** | *Control.* Does an S3D override authored by us, from Plugins, reach the model renderer at all? |
| **K1** | 1 | `856DDBAC / 46A006B0 / E2B66DB8` | 120×30 button face → **solid GREEN** | *Control.* Did the DAT load? |
| **K2** | 1 | `856DDBAC / 46A006B0 / 144161F0` | news-ticker strip → **solid ORANGE** | *Control.* Did the DAT load **and** win subfolder precedence? |

### B — all twenty, not one

The arrow is **not one model**. It is a family of twenty — five zooms × four
rotations, each self-naming `29F10000_ConnectArrow_Ui8x1x3_Z1S` …
`…_Z5E`. v1 of this probe overrode one of them, so at nineteen of twenty camera
positions nothing would have changed. v2 covers all twenty, each decoded and
rewritten on its own terms: vertex counts are 4 / 4 / 7 / 7 / 14–15 and
decompressed sizes 336 / 420 / 590 / 622, so no single layout fits all twenty.
438 float32 rewritten; no chunk length, vertex count or record length moves
anywhere (checks S2d, S3, S5).

The scale is **uniform** on purpose. The Z1/Z2 members are camera-tilted plates
whose coordinates do not mean what the Z3–Z5 boxes' do (measured: Z3–Z5 are
clean world geometry with Y = height 4.8 m and a long axis of 11.6 m that swaps
between X and Z with rotation; Z1/Z2 are 4-vertex quads with none of that
structure). An axis-selective edit would therefore mean something *different* at
different zooms and would re-import the camera dependence this rebuild exists to
remove. Expect the far-zoom arrows to **shift as well as grow** — the Z1/Z2 quad
coordinates are offset from the origin, so scaling them translates them. That is
still role B firing, not a separate phenomenon.

### C — anisotropic, and why it is not the `{24,9,3}` that was specified

The rebuild brief asked for OccupantSize `{8,3,1} → {24,9,3}`. **That is a
uniform ×3, and role B is also a uniform ×3.** Shipped in one DAT they produce
one observation — "the arrow is three times bigger" — with two causes and two
different conclusions. That is precisely the disease this rebuild was called to
cure, so it was not built that way.

C is instead **height-only**: `{8,3,1} → {8,24,1}`, an aspect-ratio change no
uniform geometry scale can imitate. **B changes SIZE, C changes SHAPE.**
`build_row15_probe.py` enforces this with check **X0d**, which refuses any
uniformly-scaled OccupantSize and names the collision in its error message —
`--occupant-size 24,9,3` is rejected at check 4, before anything is read.

The axis mapping is measured, not assumed: the model's bounding-box extents are
(long 8.2, height 3.26, thin 1.0) and OccupantSize is (8, 3, 1). Those ratios
force the correspondence — component 1 is height.

**Prior expectation for C is a null**, and that is stated here so a predicted
null is not read as a discovery. `tools/research/overlays/row-23-zots.md` §3
establishes that OccupantSize is simulator-footprint metadata and *not* render
geometry for the zot prop class. C is 180 bytes and fails differently from B, so
it is worth carrying — but it is the weak lever of the two.

### E — the one control that is already proven on screen

E scales the twenty NoPower zot models by the **identical recipe** as B: same
type, same group, same uncompressed shipping into the same DAT, same transform.
Not a similar test — the same test on a different object.

This matters because an E null is not an ambiguous shrug. row-23-zots.md §3
establishes that zot on-screen size comes *"entirely from the S3D vertex
coordinates, in world metres"*, and §5 confirmed it live in a zoom pair that
carried its own negative control in the same two frames (the zots grew with
zoom; the pixel-fixed dispatch balloons in the same frames did not). So if the
zots do **not** change, that is positive evidence our S3D records are not being
accepted or not being used — which is exactly the thing that would otherwise
make a B null uninterpretable.

Expect the zots to look absurd. A 3× zot reaches ~76 world units. That is the
control working, not a fault.

### K1 / K2 — two canaries that fail differently

v1's canary was a `captionres` on a control that also carried an inline
`caption`, so it silently depended on captionres beating the inline caption —
never proven. Both v2 canaries are **images**, and a `.UI` script cannot embed a
bitmap, so the resource is the only possible source and there is no precedence
rule to beat.

* **K1** (`E2B66DB8`, the generic 120×30 button face → **green**) is defined
  **exactly once** in the nine shipped archives and by **zero** of the 387 DBPF
  files in the live Plugins tree — loaded or not, asserted every build (checks
  L1, L2, L2b). It therefore rests on one law only: *a Plugins record beats a
  game-archive record*, the law this whole product already ships on. Costs three
  clicks to read.
* **K2** (`144161F0`, the news-ticker strip → **orange**) is on the city HUD with
  zero navigation, but our own `010-SC4UIScale` pack also defines it, so K2
  additionally depends on subfolder ordering.

That dependence is turned into a measurement rather than hidden. K1 and K2 fail
differently, so the pair **measures** the precedence rule instead of assuming it:
*K1 green + K2 stock* is not a broken probe, it is the finding "we load, but we
lose to 010-SC4UIScale", and it voids nothing, because no plugin contests any
B, C or E record.

**Neither canary is magenta, deliberately.** Magenta/black is this engine's own
missing-texture and wrong-quadrant signature (a 1x imagerect on a 2x sheet reads
the wrong quadrant). A magenta canary would be indistinguishable from an
art-pack failure. Check S2e refuses any magenta canary colour.

K1 is drawn by 28 scripts. **Establish City** is the pinned reading site — both
its buttons carry `winflag_visible=yes` and it opens harmlessly from any
unestablished region tile. Others you may also happen to see it on: Obliterate
City, Select A My Sim, Game Over, Select vehicle/pedestrian style, and the
lot/exemplar developer tools.

---

## THE OUTCOME TABLE

Read in two stages. **Stage 1 decides whether the arrow reading is admissible at
all.** Only then read stage 2.

### Stage 1 — the controls

| K1 button | K2 ticker | E zots | What it PROVES | What it does NOT prove | Verdict |
|---|---|---|---|---|---|
| stock | stock | stock | Nothing reached the screen. Either the DAT never loaded, or every channel in it was rejected. | Nothing about row 15. | **VOID.** Check the folder name, that SC4 restarted, and that you edited the right Plugins tree. Re-read the manifest. |
| stock | stock | **3× bigger** | The DAT loaded and its S3D records reached the renderer, but neither PNG override took. | That the PNG channel is broken in general — only that these two did not take. | **ADMISSIBLE, with a surprise.** Stage 2 is readable. Record the anomaly. |
| stock | **orange** | any | The DAT loaded and won — K2 orange is sufficient on its own. K1 reading stock alongside it has **two** causes and they are not separable from this frame: an authoring/environment error, **or** the Establish City dialog simply does not draw that sheet (see the honesty note below). | That K1's channel failed. | **ADMISSIBLE** on K2's strength. Read stage 2. Record which cause you could rule out. |
| **green** | stock | any | The DAT loaded and beat `SimCity_1.dat`. We lose subfolder precedence to `010-SC4UIScale`. | That anything is wrong with the probe. B/C/E are uncontested and unaffected. | **ADMISSIBLE.** Also a real finding about load order. |
| **green** | **orange** | stock | The DAT loaded, PNG records took, **S3D records did not reach the model renderer** (or were rejected — we ship uncompressed, stock ships QFS). | That the arrow is not an S3D prop. | **STAGE 2 IS VOID.** The arrow result cannot be read. Fix the S3D acceptance path first. |
| **green** | **orange** | **3× bigger** | Full chain confirmed: DAT loads, wins, and our S3D vertex edits reach the renderer. | — | **ADMISSIBLE. Read stage 2.** |

### Stage 2 — the arrow (only if stage 1 says ADMISSIBLE)

| Arrow, vs the baseline shot at the same camera | What it PROVES | What it does NOT prove |
|---|---|---|
| **Unchanged** | The arrow's on-screen size follows **neither** these twenty S3D models' vertices **nor** this OccupantSize. Row 15's channel claim, as stated, is **wrong**. | That the arrow is not a prop, and not that it is not *an* S3D — only that it is not **these twenty**. It could be bound to a different model set, drawn by the network or terrain renderer, or sized by a lever we did not move. |
| **≈3× bigger, same proportions** | ✅ **Row 15 CONFIRMED.** The plate is drawn from its own S3D geometry, sized in world metres by those vertex coordinates. | That OccupantSize does nothing — C's null is separately reported by the absence of the height change, but C is the weak lever and its null was predicted. |
| **Same footprint, ~8× taller** (a tall sliver) | The plate is sized **creation-side, from OccupantSize**, not from raw model vertices. Row 15's "drawn from an S3D model" is at best incomplete. | Which is true underneath: "C drives it" and "C drives it *and* B was normalised away by a scale-to-fit" both land here. Both yield the same conclusion — the raw vertices do not set the size — so the ambiguity does not change the answer. |
| **≈3× bigger AND much taller** | Both levers are live: the model supplies the geometry and OccupantSize scales or bounds it. | Which one dominates, or the composition rule. |
| **Gone / not drawn** | ⚠ Nothing. | **THE ONE AMBIGUOUS OUTCOME.** Causes: C's 8× occupant footprint failing placement or culling, B's scaled geometry leaving the frame, or something else. **Do not interpret it.** Bisect: `--roles C` then `--roles B` (each still ships K1, K2 and E), which costs one more session but returns a defined answer. |
| **Changed, but in none of these ways** | Nothing yet. | Photograph it and bring it back. An unanticipated shape is data, not a failure. |

### What no outcome of this probe can prove

* Nothing here reads the **draw path**. Every result is behavioural. A confirmed
  ✅ says the size follows those vertices; it does not name the function that
  draws them.
* K1/K2 certify that a DBPF authored by us, shipped **uncompressed with no
  compression directory** from a Plugins subfolder, is loaded and beats every
  earlier definition of a **type-0x856DDBAC** record. They say nothing about
  type 0x5AD0E817 or 0x6534284A, which are different acceptance paths — that is
  E's job, and E remains necessary.
* An arrow null does not distinguish "the engine never composes a key into this
  family" from "it composes the key but the size comes from elsewhere".
* Nothing here is evidence about any other census row.

---

### Honesty note on K1's reading site

K1's *ownership* is measured: exactly one definition in the nine archives, zero
in 387 Plugins files, asserted every build. K1's *visibility* is *not*. That the
Establish City dialog draws this sheet is read out of the `.UI` corpus — two
controls on script `96A006B0_2A41436B` reference `{46A006B0, E2B66DB8}` with
`winflag_visible=yes` — and has never been seen on screen. That is one inference
more than K2 carries, and this project has already been handed a
rigorous-looking filter that produced a canary the game never draws.

So the two canaries are asymmetric on purpose and in opposite directions:

* **K1** — ownership proven, visibility inferred.
* **K2** — visibility measured (a runtime window-tree dump in
  `tools/research/CITY-DOCK-OVERLAP.md` puts window `0xCA2AEDC0`, the ticker
  strip, on screen at 757×43; and this project's own art pack already replaces
  this exact TGI and that art is user-confirmed), ownership contested.

Neither is sufficient alone. **Either one reading positive proves the DAT
loaded**, which is all stage 1 needs.

---

## Residual ambiguity, stated plainly

The collision walk over the full observation space found **one** pair of distinct
causes sharing one observation that this DAT cannot separate: **the arrow
vanishing** (role B versus role C). It is declared uninterpretable above rather
than read wrongly, and it has a defined, cheap next action (`--roles`).

A second pair collides on **K1 stock**: "we lost the load order" versus "the
pinned dialog does not draw that sheet". It is disarmed rather than resolved —
K2 orange proves loading on its own, so K1's null never voids a run by itself.
Its cost is only that a *K1-only* verdict is unavailable.

Two further pairs collide on the *observation* but converge on the *same
conclusion*, so they are not defects:

* "C drives the size" vs "C drives it and B was normalised away" — both mean the
  raw vertices do not set the size.
* "DAT never loaded" vs "every channel rejected" — both mean the run is void.

Two more were removed by procedure rather than by bytes, and the procedure is
therefore not optional:

* **"no change" vs "nothing was there"** — removed by the mandatory baseline
  pass. Without it this probe is worthless.
* **"no change" vs "geometry cached in the save"** — if stage 1 is ADMISSIBLE and
  the arrow reads unchanged, before concluding, **build one new neighbour
  connection during the session** and look at the arrow it creates. A
  freshly-created arrow cannot be coming from a stale cache. This costs no extra
  session.

---

## What the builder checks before it will emit anything

| Group | Catches |
|---|---|
| **X0** design gate | A uniformly-scaled OccupantSize (B/C collision), a no-op edit, a geometry scale too close to 1 to judge by eye, a role set with no subject in it. |
| **L** load-order pre-flight | Every probe TGI resolved across the nine shipped archives **and** every DBPF in the live Plugins tree (found by magic bytes, not by extension — the tree holds 100 `.uipay` tier payloads the game never opens, and treating them as live reported six phantom contests). B/C/E must be uncontested; K1 must be uncontested even by files SC4 does not open; K2's live winner is identified by path, size and sha256. |
| **S0** source pins | Every source TGI at its pinned offset, size and stock content. A patched or modded install fails here instead of shipping a probe built from different bytes. |
| **S1** stock re-decode | Each record decodes cleanly *before* it is touched: S3D chunk chain walks exactly to ANIM and the derived stride consumes the VERT payload to its last byte; the exemplar walk lands exactly on the record end; the PNG chunk walk lands exactly on the file end with every CRC verified. |
| **S2** edit invariance | Bytes moved outside the intended value span; any changed length or count field; a changed UV; a changed neighbouring property; a magenta canary; a canary sized to stock rather than to the live winner. |
| **S3** archive structure | Header field-for-field against `DbpfPack.cs`; index offset + size = file size; payloads tile `[96, index)` with no gap or overlap; no duplicate TGI; **no compression directory under either spelling** of the DIR TGI. |
| **S4/S5** read-back | Every record pulled back out of the finished file and compared both as **bytes** (S4) and as re-decoded **values** (S5) — every scaled float at exactly stock × 3, the OccupantSize triple, every canary pixel through our own PNG decoder *and* through Pillow as an independent second decoder. A packer that wrote the right bytes to the wrong entry is caught by S4+S5 together and by neither alone. |
| **S6/S7** second implementation | `DbpfPack.exe` — an independent C# reader/writer older than this script — parses the archive, re-extracts every payload byte-identically, and packs the same staging directory to a byte-identical file outside the two date dwords. |
| **N1/N2** negative controls | A TGI we did not ship must be **absent** from the finished index (so the read-back can come back empty). Six mutations — a byte outside the position span, a moved chunk length, a no-op scale, a grown record, a clobbered exemplar property, a corrupted PNG — must each be caught by their **named** control. A control that has never failed is not known to work. |

Run them without producing a file: `python build_row15_probe.py --check-only`
(it packs a real archive in a scratch directory and never touches the shipping
path).

---

## Note on the DIR record

`tools/dbpf/NOTES-PACK.md` used to claim `SimCity_1.dat` "contains no DIR entry"
and built an argument on it. **False**, and now corrected in that file: the
archive carries a DIR at `{0xE86B1EEF, 0xE86B1EEF, 0x286B1F03}`, 782,080 bytes,
stride 16, listing **48,880 of its 60,440 records** as QFS-compressed (188 of its
2,280 PNGs among them).

What survives is only the packer's *behaviour*: an archive with no compressed
payloads legitimately needs no DIR, and this probe writes none. It must not be
justified by saying SC4 does the same, because it does not.

Two live defects that fall out of the correction, recorded here because they
affect anyone reusing this tooling:

* `DbpfPack.cs` line 44 guards on `0xE86B1EEE` (…EE, not …EF), so its DIR
  refusal would not catch a genuine DIR record. Fixing it needs a rebuild of
  `DbpfPack.exe`. Check **S3i** therefore tests for **both** spellings itself
  rather than trusting that guard.
* `decode_exemplar.py` and `decode_s3d_plate.py` walk that table at **stride 12**
  while unpacking 16 bytes per record, so they misalign after the first entry and
  can report a compressed record as "not listed". Their two published
  conclusions happen to be right, but by luck. `row15-probe/dbpfcore.py:
  read_dir()` walks it at 16 and asserts the stride; use that.

---

## Files

| File | What it is |
|---|---|
| `build_row15_probe.py` | The builder. Refuses rather than emit a bad DAT. |
| `zzzz_SC4UIScale_ROW15_PROBE.dat` | The probe. 43 records, 17,824 bytes. |
| `dbpfcore.py` | Shared read-only DBPF/QFS/exemplar/LTEXT reader. Archives are **discovered**, never listed. |
| `s3d_family.py` | The twenty-variant ConnectArrow reader + its own self-test and mutation harness (`python s3d_family.py --mutation`). |
| `staging/` | The 43 payloads as `T-…_G-…_I-….bin`, kept so `DbpfPack.exe` can re-pack them for check S7. |
| `census_*.py`, `find_canary.py`, `scan_exe.py`, `rkt_family_census.py`, `*.csv` | The decode work the canary and family choices rest on. |
