# HARDENING PROPOSALS — FUTURE FAILURE MODES

**Written 2026-08-15 night, against v2.99.0 / the v3.0.0 cut.**
~~**Nothing here has been applied.** Every item is a proposal.~~
**2026-08-16 — TRUE ONLY AS WRITTEN 2026-08-15. Three items have LANDED since,
and the item bodies below were NOT updated — every one of them still reads as an
unapplied proposal, so trust this header, not the `CLASS:` line at the foot of
those three items:**
- **C2 in full**, closed as **#163**. `tools\fonts\make_fontstyle.py:171` now
  takes `squeeze` as its own parameter, `:223-225` tests the **tier** factor,
  and `:247` passes `sq` separately; the docstring at `:206` names #163. C2's
  own "MEASURED TONIGHT" block at `:190-195` is stale with it —
  `python fonts\make_fontstyle.py --selfcheck` now exits **0**
  ("reproduces all 88 candidate.ini sizes exactly").
- **N5 item 1** — `tools\packages\PACKAGES.md`'s `⛔ USE THE SCRIPT` block now
  carries the three-flag warning and points at the script instead of the bare
  exe. *(That file was under concurrent edit on 2026-08-16 and its line numbers
  moved three times inside one minute — anchor on the `⛔ USE THE SCRIPT` text,
  never on a line number. Verified by content: `grep -c "Upscale2x.exe dbpf"`
  returns **0**.)*
- **N5 item 2 in substance, not verbatim** — the script shipped as
  `tools\upscale\Rebuild-Corpus.ps1`, **not** the proposed `Rebuild-Previews.ps1`.
  It requires all three lists (`:69-73`), rebuilds all three tiers (`:94-112`)
  and refuses a missing or empty list (`:74-88`) — but it prints per-list
  **entry counts** (`:87`), **not** the SHA-256 this item asked for.
  **N5 item 3 (the tool-drift refusal / `-IAcceptToolDrift`) did NOT land.**
- **N3 item 1 at ONE of its four call sites** —
  `tools\selective-safe\build_selective_safe.py:2276-2277` now passes
  `--cell-strips`. **The other three still do not:**
  `build_dialog_static.py:1823-1828` passes only `--nine-slice` + `--no-snap`,
  and `rebuild_namicons.py` / `build_uncovered_icons.py` pass no derived list at
  all. N3 items 2 and 3 did not land either.

**Because of that last one, the "no builder behaviour was changed" clause in the
next sentence is also no longer true.**

Everything NOT listed above was re-checked on 2026-08-16 and is still a
proposal — spot controls: **P0.1** still red
(`gate_patch_families_combined.py` prints the same five `UNREGISTERED TABLE`
failures), **C3** not landed (`Upscale2x.cs:146-179` still `continue`s past a
malformed line, still exits 0 on zero entries, still no SHA-256 header), **N4**
not landed (`grep -rl "height-exact-strips" tools\` still returns
`Upscale2x.cs` alone — no producer, no `.txt`).

No `src\*.cpp` was
edited, no builder behaviour was changed, no package was rebuilt, nothing was
deployed and the game was not launched.

This document exists because the project's own record says the gates cannot see
a rule that is wrong (START-HERE §"The lesson that generalises"). Everything
below is either a rule that is wrong today, or a rule that will be wrong the
first time someone touches it.

---

## HOW TO READ THIS

Every item carries six fields:

| field | meaning |
|---|---|
| **DEFECT** | what is wrong, with file and line |
| **FAILURE SCENARIO** | the concrete sequence that turns it into a pixel on screen or a dead package |
| **FIX** | what to change, specifically enough to hand to an implementer |
| **BLAST RADIUS** | what else moves when you do |
| **VERIFY OFFLINE** | the check that proves it, including the integer-tier control |
| **CLASS** | **SAFE** (provable offline, landable while the user sleeps) or **BEHAVIOURAL** (changes what the game draws — proposal only, needs eyes-on) |

**House law applied throughout:** an integer factor is structurally immune to
most fractional-tier defects (rule 11). Any metric quoted below reads **exactly
zero at 2× and 3×**, or it is called out as not having that control. Where a
number is quoted it was measured tonight, not inferred.

**Two gates are RED right now.** `gate_patch_families_combined.py` (exit 1) and
`gate_namicons.py` (exit 1). Item **P0** is about that fact itself, and it
outranks every individual defect below.

---

# PART 0 — THE PROCESS DEFECT THAT OUTRANKS EVERY CODE DEFECT

## P0. TWO GATES ARE RED AND THE TREE IS BEING CUT AS v3.0.0 ANYWAY
**Rank: 1 of everything in this document. CLASS: SAFE.**

**DEFECT.** `START-HERE.md` §6 says *"all offline gates green"*. Measured
tonight, two of the seven gates in the START-HERE gate block exit non-zero:

```
$ python tools\uimap\emu\gate_patch_families_combined.py
5 FAILURE(S):
  FAIL UNREGISTERED TABLE kCostBoxHeightSite (1 entries) - add it to WIDTHS with its encoding width, or this gate is silently blind to a whole family.
  FAIL UNREGISTERED TABLE kCostBoxWidthSite  (1 entries) - ...
  FAIL UNREGISTERED TABLE kCostOriginBack    (1 entries) - ...
  FAIL UNREGISTERED TABLE kCostOriginSite    (1 entries) - ...
  FAIL UNREGISTERED TABLE kCostOriginStock   (8 entries) - ...
EXITCODE=1
```

`gate_namicons.py` is red too (392 orphans + 1 losing icon, task #152, open
since 2026-08-05 — **ten days**).

**FAILURE SCENARIO.** This is REGRESSION #150 verbatim, and #150's own summary
is *"a red gate that went unread for two hours"* — one of "the most useful
entries in REGRESSION.md" per START-HERE. Ten days beats two hours by two
orders of magnitude. The mechanism is not that the gate is wrong; it is that a
**permanently red gate is a disabled gate**. The next contributor runs the
START-HERE block, sees two failures, is told "those two are known", and from
that moment the gate cannot deliver a *new* failure because nobody will read
the delta. Both of these gates are the only instrument for their defect class:
`gate_patch_families_combined` is the only thing that can see two byte patches
overlapping, and it is currently blind to the entire #159 cost-box family — the
exact "silently blind to a whole family" state its own error message names.

**FIX.** Two separate, small actions, both SAFE:
1. Register the five #159 tables in `gate_patch_families_combined.py`'s `WIDTHS`
   map with their real encoding widths, then re-run. This is a data addition to
   a gate, not a behaviour change.
2. Either fix `gate_namicons.py`'s pre-#149 assumption (task #152) **or**
   demote it out of the START-HERE block with a one-line reason and a dated
   re-arm condition. What is not acceptable is leaving it in a list titled
   *"offline gates - no game needed, all must exit 0"* while it does not.
3. Add to `START-HERE.md` §3 a one-line rule: **a gate that is red for more
   than one session is either fixed or removed from the block, in that
   session.** A "known red" list does not exist.

**BLAST RADIUS.** None on the game. `gate_patch_families_combined` gains
coverage of 12 previously unscanned bytes; it may go red for a *real* reason
once it can see them, which is the point.

**VERIFY OFFLINE.** The gates are their own verification. Success condition:
`python tools\uimap\emu\gate_patch_families_combined.py; echo $?` prints `0` and
the `WIDTHS` table lists 5 more entries than it does now.

**CLASS: SAFE — land tonight.**

---

# PART 1 — THE SEVEN CONFIRMED FINDINGS

Each survived two independent refutation attempts before reaching me. I
re-verified all seven against the live tree; the verification is recorded under
each one. **Findings are numbered by expected damage, highest first.**

---

## C1. THREE (ACTUALLY FOUR) IMPLEMENTATIONS OF THE ICON-DIMENSION RULE DISAGREE AT 1.5× — AND THE DISAGREEMENT IS ON DISK RIGHT NOW
**Rank: 2. CLASS: BEHAVIOURAL. Severity: critical.**

**DEFECT.** `src\ScaleTier.cpp:971` claims *"Upscale2x.cs::ScaleDim / CellUnit,
matched exactly"*. It is not exact. The C++ port at `ScaleTier.cpp:1005-1019`
carries none of the three per-file switches the offline tool has — no
`sNoHeightSnap` (`--height-exact-group`), no `sNineSliceOnly` (`--nine-slice`),
no `sNoSnapThis` (`--no-snap`). `ScaleTier.cpp:1370` and `:1496` then call
`ScaleDim(sh, factor)` for resources in `kIconGroup = 0x6A386D26`
(`ScaleTier.cpp:617`) — the exact group that
`build_uncovered_icons.py:569` and `rebuild_namicons.py:43` pass to
`--height-exact-group`.

**MEASURED TONIGHT — this is not a model, it is the bytes on disk.** Modal
dimensions of every `*_G-0x6a386d26_*` PNG in the three staging trees that feed
three packages loaded in the same session:

| tier | `preview-*` → **ItemIcons** | `uncovered-up-*` → **UncoveredIcons** | delta |
|---|---|---|---|
| **1.5×** | **264 × 68** (~~640~~ **320** sheets) | **264 × 66** (~~4~~ **2** sheets) | **2 px** |
| 2× | 352 × 88 (~~640~~ **320**) | 352 × 88 (~~4~~ **2**) | **0** ← control |
| 3× | 528 × 132 (~~640~~ **320**) | 528 × 132 (~~4~~ **2**) | **0** ← control |

**2026-08-16 — every sheet count in this table was exactly DOUBLE, and the
cause is a mirror tree.** Re-measured from the PNG IHDRs: `preview-15x\SimCity_1`
holds **356** icon-group sheets in all, **320** of them at 264×68;
`uncovered-up-1.5` holds **2** at 264×66; `nam-up-1.5` holds **122** at 264×66
(of 392 group sheets, the other 270 being 536×87). 640 never existed — the 1x
source `tools\dbpf\extracted\SimCity_1` contains only **356** icon-group PNGs
in total (320 at 176×44, 36 at 356×58), so there is nothing for a 640-sheet
1.5x set to have come from. The doubling is a double-count:
`tools\itemicons\stage-15x` is a **byte-identical mirror** of
`preview-15x\SimCity_1` — 356/356 filenames match and all 356 SHA-256 payloads
are equal — and it too holds 320 at 264×68. The same mirror pairing exists at 2x
(`stage`) and 3x (`stage-3x`), which is why all three rows were doubled by the
same factor. The uncovered column has no mirror at all, so its `4` was simply
wrong.
**The split itself is unchanged and CONFIRMED**: 68 from `preview-*`, 66 from
the two icon builders, and delta **0** at both 2x and 3x — which is what makes
it a defect and not a residual. Only the magnitudes moved; C1 stands.
*(Measuring note: files under `tools\dbpf\extracted\SimCity_1` are named
`T-856ddbac_G-6a386d26_I-...` with **no `0x`** prefix. A grep for
`_G-0x6a386d26_` returns zero there — match both spellings, or you will read a
false null.)*

`nam-up-1.5` carries a further ~~**244 sheets at 264 × 66**~~ **122 sheets at 264 × 66**.
<!-- 2026-08-16: re-measured `tools\itemicons\nam-up-1.5` (flat tree, PNG IHDR read): 392 `_G-0x6a386d26_` sheets in total — 122 at 264 × 66 and 270 at 536 × 87. The 244 was a 2× overcount. `nam-up-2` / `nam-up-3` hold the same 122 at 352 × 88 / 528 × 132, matching `tools\upscale\preview` / `preview-3x`, so the integer-tier delta is still exactly 0 and the defect below stands. -->
So at 1.5× the same
TGI group ships at 68 px tall from one package and 66 px tall from two others,
and the runtime `ScaleTier::ScaleDim` independently computes **68**
(`CellUnit(44)=4`, `66 % 4 = 2`, tie → up). The integer-tier control reads
**exactly zero**, which is what makes this a defect and not a residual.

**FAILURE SCENARIO.** A player at 1.5× with NAM installed opens a transport
flyout. Buttons drawn from `ItemIcons` get a 68 px sheet in a 66 px window (2 px
of art clipped, or the picture sits low with a band — the #150 symptom,
verbatim). Buttons drawn from `NamIcons` get 66 px, which is correct. Buttons
whose art the DLL synthesised at runtime (`IconSynth`, #149) get 68 px again.
**Three heights on one toolbar row.** Nobody has seen it because 1.5× eyes-on
predates #149's uncovered-icon path and because the two packages rarely put
adjacent buttons on the same row.

**FIX.** Do **not** guess 66 or 68. The project's own arbitration already
exists: `Upscale2x.cs:816-834` records *"the picture sat low with a light band
above it"* and cites `gate_namicons.py:131` as the authority for an exact
height; `ScaleTier.cpp:986` argues 68 from *our own art* — which is circular,
because the art it cites is the unflagged half of this same split. So:
1. **Eyes-on control at 1.5×**, one screenshot, one flyout that mixes a stock
   icon and a NAM icon. That settles 66 vs 68 by measurement, per METHOD.
2. Then make it **ONE rule**: give `ScaleTier::ScaleDim` the same three
   per-file switches, or (simpler and preferred) drop the height snap for
   `kIconGroup` in the C++ port so it matches the offline flag unconditionally.
3. Add a **cross-package dimension gate**: for every TGI shipped by more than
   one of our packages, assert identical dimensions at every tier. This gate
   does not exist and its absence is why this shipped.

**BLAST RADIUS.** Option (2b) — dropping the icon-group height snap in the C++
port — moves only heights inside `0x6A386D26`, only at 1.5×, and is a
**provable no-op at 2× and 3×** (`ScaleDim` returns before `CellUnit` is
consulted at an integer factor; the table above confirms it empirically). It
touches `IconSynth`'s born-correct path, which is the #149 mechanism, so it
must be re-eyed at 1.5× with a third-party lot installed.

**VERIFY OFFLINE.** The measurement above is the verification and it is
repeatable in ten seconds — read the PNG IHDR of every `_G-0x6a386d26_` file in
the three source trees and require the modal (w,h) to be identical across trees
at each tier. **Required control: delta 0 at 2× and 3×.**

**CLASS: BEHAVIOURAL. Do NOT land without eyes-on.** The cross-package gate
(step 3) is SAFE and can be built tonight; it will simply report the split until
step 1 happens.

---

## ~~C2. `make_fontstyle.py`'s INTEGER GUARD TESTS THE SQUEEZED FACTOR — `--selfcheck` IS RED AND THE SHIPPED 2×/3× TABLES NO LONGER MATCH THE GENERATOR~~
## C2. ✅ IMPLEMENTED 2026-08-16 (closed as #163) — see `_tests\REGRESSION.md:9896`

**2026-08-16 — LANDED, DO NOT RE-FIX.** `scale_size` now takes the squeeze as a
third argument and the guard tests the RAW TIER factor:
`tools\fonts\make_fontstyle.py:171` `def scale_size(size, factor, squeeze=1.0)`;
`:223` `if float(factor).is_integer():` with the squeeze applied inside BOTH
branches (`:224` round-half-up, `:225` floor); `:246-247`
`sq = SIZE_SQUEEZE.get(name, 1.0)` / `scale_size(old, factor, sq)`. The `eff`
local is gone — the only surviving `eff` in the file is `:208`, inside the
docstring's own record of this defect.

`--selfcheck` exits 0: *"SELFCHECK OK: factor 2 reproduces all 88 candidate.ini
sizes exactly, and the full file BYTE-FOR-BYTE (banner aside), clones included"*.

The byte-identity acceptance test in VERIFY OFFLINE below was RUN and PASSED
(measured 2026-08-16, SHA-256):

```
regenerate 3    56215b25384e2f313251a7258ac1d02623c3e1646fabce3cf869eec98a15de51
  == tools\packages\3x\FontStyle-3x.ini           IDENTICAL
regenerate 1.5  4fa84a8eba0a6346d180ed97f85dcd45508f970ed11725c829023996364e6c6c
  == tools\packages\15x\FontStyle-15x.ini         IDENTICAL
```

Inverted control satisfied: the integer tiers moved (`Legend` 23→24, 35→36) and
the fractional tier did not (17 before and after). `Legend` on disk is 13
(`FontStyle.default.ini:286`), 24 (`FontStyle.candidate.ini:293`), 36
(`tools\packages\3x\FontStyle-3x.ini:293`), 17
(`tools\packages\15x\FontStyle-15x.ini:293`). Zero shipped bytes changed.

The DEFECT / MEASURED / FAILURE SCENARIO text below is retained as the record of
what was wrong, not as a description of the tree — its `:229` and `:206` line
cites describe the pre-#163 file and no longer resolve.

**Rank: 3. CLASS: BEHAVIOURAL (but the artefact is right — see below). Severity: critical.**

**DEFECT.** `tools\fonts\make_fontstyle.py:229` computes
`eff = factor * SIZE_SQUEEZE.get(name, 1.0)` and calls `scale_size(old, eff)`.
`scale_size`'s guard at `:206` is `if float(factor).is_integer()` — but the
value it receives is the **already-squeezed** factor. `Legend` carries
`SIZE_SQUEEZE = 0.92`, so at tier 2 the guard sees `1.84` and at tier 3 it sees
`2.76`. The integer-tier branch **never runs** for the one style that has a
squeeze. The docstring at `:198-204` asserts the exact opposite and even names
this style as the reason the branch exists.

**MEASURED TONIGHT:**

```
$ python tools\fonts\make_fontstyle.py --selfcheck
SELFCHECK FAIL: 1 size mismatches vs candidate.ini:
  Legend gen=23 candidate=24
$ echo $?
1
```

And the arithmetic, against the four files on disk (`Legend` is `13` in
`FontStyle.default.ini`):

```
f      CURRENT  FIXED    SHIPPED  verdict
1.5    17       17       17       cur==  fixed==
2.0    23       24       24       cur!=  fixed==
3.0    35       36       36       cur!=  fixed==

non-squeezed control (old=7, no squeeze) — must not move:
  f=1.5 cur=10 fixed=10
  f=2.0 cur=14 fixed=14
  f=3.0 cur=21 fixed=21
```

**The shipped artefacts are all correct. Only the generator drifted.** The
proposed fix reproduces `FontStyle-15x.ini` (17), `FontStyle-2x.ini` /
`candidate.ini` (24) and `FontStyle-3x.ini` (36) **exactly**, and leaves every
un-squeezed style byte-identical at every tier.

**FAILURE SCENARIO.** Two ways this bites, both silent:
1. Anyone who regenerates a font table for a release — the documented
   `PACKAGES.md` step 2 — ships a `Legend` one point smaller at 2× and 3× than
   the tier that was eyes-on confirmed. `Legend` is the Graphs/Data-Views legend
   face, the exact family #57 spent five versions on.
2. Worse: because the failure is **inside the gate as well as the artefact**,
   it reads as *"the selfcheck is broken"* rather than *"the table is stale"*.
   That is how a contributor rationalises deleting the selfcheck. It is the
   only thing standing between the font pipeline and #142.

**FIX.** Separate the two multipliers at the signature:

```python
def scale_size(size, factor, squeeze):
    if float(factor).is_integer():
        return max(1, int(math.floor(size * factor * squeeze + 0.5)))
    return max(1, int(math.floor(size * factor * squeeze)))
```

and at `:230`, `new = old if name in KEEP_STOCK else scale_size(old, factor, SIZE_SQUEEZE.get(name, 1.0))`.
Delete the `eff` local. Then run `--selfcheck` (must go green) and regenerate
`FontStyle-3x.ini` — **it must come back byte-identical to the shipped
2026-08-03 file.** That byte-identity is the proof that the artefact was right
and only the generator drifted, and it is what makes this landable without
eyes-on.

**BLAST RADIUS.** One style, `Legend`. Every other style has squeeze 1.0 and is
provably unmoved (control above). No `.dat` changes. No DLL change.

**VERIFY OFFLINE.**
```
python tools\fonts\make_fontstyle.py --selfcheck            # must exit 0
python tools\fonts\make_fontstyle.py 3 <tmp>\FontStyle-3x.ini
fc /b <tmp>\FontStyle-3x.ini tools\packages\3x\FontStyle-3x.ini   # must be identical
python tools\fonts\make_fontstyle.py 1.5 <tmp>\FontStyle-15x.ini
fc /b <tmp>\FontStyle-15x.ini tools\packages\15x\FontStyle-15x.ini # must be identical
```
The integer-tier control here is *inverted and stronger than usual*: the fix
must make the **integer** tiers change (23→24, 35→36) and the **fractional**
tier not move at all. If 1.5× moves, the fix is wrong.

**CLASS: BEHAVIOURAL in principle — but the byte-identity check above converts
it to SAFE.** If all three regenerated files are byte-identical to what is
already deployed and eyes-on confirmed, nothing the game draws changes and this
**can be landed tonight**. If any file differs, stop and escalate.

---

## C3. `Upscale2x` TREATS AN EMPTY OR UNPARSEABLE LIST FILE AS SUCCESS
**Rank: 4. CLASS: SAFE. Severity: high.**

**DEFECT.** `tools\upscale\Upscale2x.cs:146-247`, all four list-loading
branches (`--height-exact-strips`, `--cell-strips`, `--nine-slice`,
`--no-snap`). Each validates only `File.Exists`. Inside the parse loop every
malformed line is skipped with a bare `continue`. A file that yields **zero**
usable entries prints `cell-strips: 0 sheet(s) will be sampled PER STATE` and
proceeds to a full, successful, exit-0 run.

Contrast the producer: `find_no_snap.py:162-165` explicitly REFUSES to be quiet
on zero — *"Do NOT read this as nothing needs it"*. **The producer has the
refusal; the consumer does not.**

**FAILURE SCENARIO.** A truncated, half-written, wrong-encoding or
CRLF-mangled `cell-strips.txt` (4,135 bytes today) produces a preview tree with
#156 fully un-shipped, at exit 0, with a stdout line nobody reads (law 54: *no
log line = did not run*; the inverse — a log line saying **0** — is worse,
because it looks like output). Every downstream gate then measures the new tree
against the new tree and stays green. This is the same shape as #150 (six of
nine packages never got the fix) except it needs no human error beyond a
partial file write, and OneDrive is in this path.

**FIX.** In each of the four branches:
* if the file loads **zero** entries → print the path and `return 1`;
* if any non-comment, non-blank line fails to parse → print the offending line
  verbatim and `return 1`.

Additionally: print `SHA-256` of every list file in the run's stdout header, so
a preview tree's provenance is recoverable after the fact. That single line
would have made the "which lists were in force when this tree was built?"
question answerable, which it currently is not for any of the three trees on
disk.

**BLAST RADIUS.** Zero pixels. It can only turn a currently-silent bad run into
a loud failure. Note it will make the **currently absent**
`height-exact-strips.txt` (see N4) fail loudly instead of silently, which is
correct.

**VERIFY OFFLINE.** Feed it `NUL`/an empty file and a file of one garbage line;
require exit 1 on both. Positive control: feed the real
`cell-strips.txt` and require exit 0 and `193 sheet(s)`. Integer-tier control is
not applicable (this is an input validator, not a geometry rule) — say so
rather than inventing one.

**CLASS: SAFE — land tonight.**

---

## C4. `diff.py::scale_round` IS STALE SINCE #162 CHANGED THE DLL's ROUNDING
**Rank: 5. CLASS: SAFE. Severity: high.**

**DEFECT.** `tools\uimap\diff\diff.py:114-116`:

```python
def scale_round(v: int, f: float) -> int:
    """UiSpike.cpp:2806 ScaleRound - llround (half away from zero)."""
    return int(math.floor(v*f + 0.5)) if v >= 0 else -int(math.floor(-v*f + 0.5))
```

~~`src\UiSpike.cpp:5385`~~ **`src\UiSpike.cpp:5677` (2026-08-16: the file grew ~292 lines above this point; `:5385` now lands inside the `kDataScaledSubtreeIds` table comment — an unrelated mechanism)** now defines `ScaleRound(v,f)` as
`RoundHalfUp(double(v)*double(f))` where `RoundHalfUp` (`UiSpike.cpp:177-180`)
is `floor(v + 0.5)` for **all** v. The comment block at ~~`:5372-5384`~~ **`:5639-5676`** says
explicitly that `llround` **was the defect**, and cites
`gate_art_vs_window.py` as the measurement: *"with llround, 1 node is short at
1.5× and 0 at 2×; with half-up, 0 and 0"*.

`diff.py:125 edge_law()` builds the entire runtime size law on top of the stale
rule, and `diff.py` is the Stage-4 harness driven by
`_tests\Test-UiMapDiff.ps1:90`, which fails the suite on a non-zero exit.

**FAILURE SCENARIO.** The divergence is confined to **negative** coordinates —
exactly the 12 nodes with a negative absolute origin that `UiSpike.cpp:5369`
names, and their descendants (8 sizes / 44 positions at f=1.5, 0/0 at f=2 and
f=3). So Stage 4 currently models the *old* DLL for precisely the node set
#162's change was made for. Its 52 predictions are therefore unfalsifiable
against the shipping DLL in the one region that matters, and a future
regression in that region reads as "matches the model".

**FIX.** `return int(math.floor(v * f + 0.5))` for all `v`, docstring citing
`UiSpike.cpp:5385`. Then re-run `Test-UiMapDiff.ps1` **with `--fresh`** —
`state.json` caching will otherwise skip every re-evaluated case (this is the
stale-cache shape and it will hide the fix) — and diff the report against the
previous run to see which of the 52 predictions moved.

**BLAST RADIUS.** Offline only. No shipped artefact. The report changes; that
change is the deliverable.

**VERIFY OFFLINE.** `python -c` over v ∈ [-64, 64], f ∈ {1.0, 1.5, 2.0, 3.0}:
old and new must agree for every `v >= 0` and for every integer `f`, and differ
only for negative `v` at `f = 1.5`. **That is the integer-tier control: zero
differences at f=2 and f=3.** Then `Test-UiMapDiff.ps1 -Fresh` must exit 0.

**CLASS: SAFE — land tonight.**

---

## C5. THE DERIVED STATE COUNT REACHES `Upscale2x`'s SAMPLER BUT NEVER `CellUnit`/`ScaleDim`, AND THE SAMPLER DECLINES SILENTLY
**Rank: 6. CLASS: BEHAVIOURAL. Severity: high.**

**DEFECT.** `cell-strips.txt` carries a per-sheet state count
(`<group> <instance> <states>`), but only `BuildSampleMap`
(`Upscale2x.cs:724-748`) ever reads it. `CellUnit` (~~`:842-857`~~ **2026-08-16: now `:798-807`. `:842-864` is `ScaleDim`, which only *calls* `CellUnit` (`:846`); the `kCellCounts` lookup is at `:802`. FIX item 1 below targets `CellUnit` — an edit at `:842` changes the snap arithmetic instead of the cell unit.**) still consults
the hard-coded `kCellCounts = {3,4}` (`:677`), so `ScaleDim` will not snap a
scaled width to any state count outside that set. `BuildSampleMap` then requires
`src % k == 0 && outLen % k == 0`; when `outLen` fails, it falls through to the
global factor map **with no warning and no counter** — the exact defect #156
exists to remove. The two halves of the file still disagree; #156 only fixed the
cases where `{3,4}` happened to cover the real count.

**FAILURE SCENARIO.** An 8-state sheet 204 px wide. `CellUnit(204)` = lcm of
{3,4} that divide 204 = 12; `204 × 1.5 = 306`; `306 % 12 = 6`, tie → up → 312.
`312 % 8 = 0`, so the sampler *happens* to work. Change the width to one where
it does not and the sampler declines in silence and re-times the cell contents —
which is #151's symptom (*"same dimensions, wrong pixels"*) reappearing on a
sheet the derived list explicitly identified as a strip. The build says nothing.

**FIX.** Two independent halves; do both.
1. **Feed the derived count into the sizing rule.** When `sStripStates > 1`,
   make `CellUnit` return `lcm(CellUnit(v), sStripStates)` so `ScaleDim` snaps
   204 → 208 (26 × 8) instead of 312. ⚠ This is the #149/#16 hazard in
   miniature — LCM-of-everything is safe against cutting and unsafe against
   fitting — so it must be **scoped to the 193 derived sheets only** and never
   to the corpus.
2. **Make the decline LOUD.** If `states > 1` and the per-cell branch is
   declined, write the sheet's TGI and the failing modulus to stderr and count
   it. Print the count in the run summary. This is the `ICONPROBE`
   positive-control pattern (`UiSpike.cpp:12047`) applied to the art pipeline:
   *"the flag was passed"* must be distinguishable from *"the flag did
   anything"*.

**BLAST RADIUS.** Half 2 is zero-pixel and can land alone. Half 1 changes
widths on some subset of the 193 derived sheets **at fractional tiers only** —
`ScaleDim` returns before `CellUnit` at an integer factor, so 2× and 3× are
byte-identical by construction and the rebuild must hash-match. Count the moved
sheets before shipping (rule 22: *count what it fires on*).

**VERIFY OFFLINE.** Rebuild `preview-15x`, `preview`, `preview-3x` with the
change and hash every PNG. **Required: 0 changed files at 2× and 3×**; at 1.5×,
a named list of moved sheets, each of which must be in `cell-strips.txt`. Then
`gate_art_vs_window.py` must stay at 0 new findings at every tier.

**CLASS: half 2 SAFE (land tonight). Half 1 BEHAVIOURAL — proposal only.**

---

## C6. `MatchesAnyTierFontSource` CONFLATES THREE SITUATIONS AND THE #118 TRAP SURVIVES
**Rank: 7. CLASS: SAFE. Severity: medium.**

**DEFECT.** `src\ScaleTier.cpp:111-125` returns `nullptr` in three distinct
situations, and the caller at `:492-512` treats all three as *"not ours,
snapshot it as `.user-original`"*:

1. `srcDir` empty or null;
2. sources present in name only — **every** `FileExists(src)` is false, because
   no `FontStyle<tag>.ini` is in `srcDir` at all;
3. sources readable and none match.

Case 3 is the intended positive. Cases 1 and 2 are **nulls with no positive
control** — the project's own NULL IS NOT EVIDENCE law applied to a file
comparison. And note case 2 is not hypothetical: `kPackages` (`:43-48`) has a
`{4.0f, L"-4x"}` entry, so the loop already probes for a `FontStyle-4x.ini` that
has never existed.

Case 3 additionally mis-fires whenever font **content** changes between builds:
the live file was written by the *previous* build, so it must be compared
against the *previous* build's sources. The comment at `:103-109` asserts the
opposite — *"it stays correct if the font contents change, because the
comparison is always against the sources we shipped WITH this build"* — and that
reasoning has the direction backwards. ~~**C2 above is the live instance:** if the
font fix lands, `Legend` moves 23→24 at 2×, and every existing install's live
`FontStyle.ini` instantly stops matching this build's sources.~~

**2026-08-16 — WRONG INSTANCE, RIGHT MECHANISM.** C2 landed as #163 and moved
**zero shipped bytes**: `23` was only ever the broken *generator's* output. Every
shipped 2× table carries `Legend=24` (line 293; SHA-256 `bce357f3…` for
`FontStyle-2x.ini` in all five dist bundles, v2.85.0 → v3.0.0) and every shipped
3× table carries 36 (`56215b25…`, unchanged across the same five bundles).
Regenerating factors 2, 1.5 and 3 today reproduces `FontStyle.candidate.ini`,
`tools\packages\15x\FontStyle-15x.ini` and `tools\packages\3x\FontStyle-3x.ini`
byte-for-byte, and `--selfcheck` is green
(`tools\fonts\make_fontstyle.py:223-225`, `:247`; `_tests\REGRESSION.md:9899`).
C2 therefore never made any install's live `FontStyle.ini` stop matching.

**⛔ BUT THE SCENARIO BELOW STILL HAS A LIVE TRIGGER — IT IS THE 1.5× TABLE, NOT
`Legend` AT 2×.** `FontStyle-15x.ini` moved between two shipped bundles when
`scale_size` began flooring at non-integer factors (`make_fontstyle.py:174-196`,
a different change from C2's guard fix): **41 style lines differ** between
`dist\SC4UIScale-v2.93.1\Plugins\FontStyle-15x.ini` (2026-08-03, `12c36c3b…`,
the same bytes back to v2.85.0) and `dist\SC4UIScale-v3.0.0\Plugins\FontStyle-15x.ini`
(2026-08-06, `4fa84a8e…`) — `Legend` 18→17, `MayorPop`/`MayorFunds` 20→19,
`BdgtSummaryCurrentBal` 26→25, `RegionLabel` 23→22, `LoadScreenGoofyMessage`
32→31 and 36 more. `src\ScaleTier.cpp:552-560` copies the tagged source to the
live file verbatim, so a 1.5× install of v2.93.1 holds exactly those bytes; on
upgrade to v3.0.0 it matches **none** of the three sources,
`MatchesAnyTierFontSource` returns `nullptr` (`:111-125`), and `:509` snapshots
**our own 1.5× font** as `.user-original`. That is #118 verbatim, from a
legitimate release — so read the scenario below with the 1.5× table substituted
for `Legend`/2×.

**C6 stays ranked and stays open.** Only the sequencing note changes: C2 has
already landed and its byte-identity control is banked
(`_tests\REGRESSION.md:9930-9934`), so FIX 2's stamp can go in whenever.

**FAILURE SCENARIO.** Player installs v2.99.0 at 2×. v3.0.0 ships with the C2
font fix. On first launch: the live `FontStyle.ini` (ours, v2.99.0's `Legend=23`)
matches none of v3.0.0's sources (`Legend=24`) → `nullptr` → it is copied to
`FontStyle.ini.user-original`, which is **never overwritten and never deleted**.
The player later drops to a stock-tier resolution and the mod faithfully
"restores their original" — which is our own v2.99.0 2× font. That is #118, with
the evidence destroyed, triggered by a legitimate release.

**FIX.**
1. **Tri-state the helper.** Return `OURS` / `THEIRS` / `UNDECIDABLE`, where
   `UNDECIDABLE` means *zero tier sources were readable*. On `UNDECIDABLE`
   take **no snapshot** and log loudly — that is the safe outcome the block
   itself already argues for at `:497-500`.
2. **Stamp the file we write.** Emit a comment line carrying the tag and the mod
   version into every generated `FontStyle-<tag>.ini`, and test for that stamp
   *first*. Byte-identity against this build's sources then becomes a secondary
   confirmation rather than the sole authority, and content drift stops being
   fatal. (`make_fontstyle.py` already emits a provenance banner into
   `candidate.ini` — the selfcheck skips `;;` lines — so the mechanism exists.)
3. **Log the positive control unconditionally**, `ICONPROBE`-style:
   `"FONTSRC: probed %d tier sources in %ls, %d readable"`. An empty probe must
   be distinguishable from a probe that never ran.

**BLAST RADIUS.** Touches only the `.user-original` decision. It cannot make
the mod scale differently. The stamp changes the bytes of the three
`FontStyle-<tag>.ini` files, so it must be sequenced **after** C2's
byte-identity proof, not before it — otherwise C2 loses its control.

**VERIFY OFFLINE.** A fixture test, which does not exist today: construct a fake
`liveDir` + `srcDir` for each of five cases —
(a) no sources at all → **no snapshot, `UNDECIDABLE` logged**;
(b) sources present, live matches one → no snapshot;
(c) sources present, live is a stale-but-ours file from a previous build →
**no snapshot** (this is the case that fails today);
(d) sources present, live is a genuine third-party font → snapshot taken;
(e) `srcDir` empty string → `UNDECIDABLE`, no snapshot.
Assert on the presence/absence of `FontStyle.ini.user-original` in each.

**CLASS: SAFE — land tonight, but sequence after C2.**

---

## C7. `build_itemicons_sub.py`'s "CAN NEVER SILENTLY DIVERGE" VERIFICATION COMPARES FILENAMES ONLY
**Rank: 8. CLASS: SAFE. Severity: medium.**

**DEFECT.** `tools\itemicons\build_itemicons_sub.py:116-127`:
`got = sorted(names in stage)`, `ref = sorted(names in _work/pack-sub)`, set
difference, FATAL. The docstring at `:18-24` says this means *"tier packages can
never silently diverge from the user-confirmed 2x contents"*, and `--factor 2`
is labelled **VERIFY-ONLY** — it is the project's only regression detector for
this package.

A name-set comparison is invariant to every dimension and every pixel. This is
the `--normalize-names` shape: **a diff that compares nothing reports
agreement.**

**FAILURE SCENARIO.** `Upscale2x` changes (it changed at 21:03 tonight).
`--factor 2` is run as the regression check. All 130 names match. It prints
`name set == shipped 2x set: OK` and exits 0 while every icon inside is a
different size. Given C1 above — where two of our packages *already* disagree by
2 px on the same group at 1.5× — this is not a theoretical failure mode; it is
the check that would have caught C1 and did not.

**FIX.** Extend the comparison to `(name, width, height)` read from the PNG
IHDR (12 lines, no decode needed), and for `--factor 2` add a **decoded-pixel**
equality assert against `pack-sub`.

⛔ **Do NOT use file-hash equality.** The PNG encoder's deflate output varies
between `Upscale2x` builds while the pixels are identical, so a byte-hash gate
here is a false-alarm machine — and a gate that cries wolf gets deleted (P0).

**BLAST RADIUS.** Zero pixels; it is a verification-only path. It may turn the
current silent pass into a loud failure, which is the point.

**VERIFY OFFLINE.** Run `--factor 2` (VERIFY-ONLY, writes nothing shipped) and
require exit 0 with the new dimension check. Then run `--factor 1.5` and
`--factor 3` and require the dimension sets to differ from 2× **by exactly the
factor** — that is the control: 2× must equal `pack-sub` exactly, and the
fractional tier must not.

**CLASS: SAFE — land tonight.**

---

# PART 2 — NEW FINDINGS FROM THIS PASS

All measured tonight against the live tree. Ranked by expected damage.

---

## N1. `dist\SC4UIScale-v3.0.0\` IS ALREADY STALE — IT PREDATES TONIGHT'S ART AND DLL
**Rank: 2-equal with C1. CLASS: SAFE (delete/rebuild). Severity: critical — this is THE shipping blocker.**

**DEFECT.** A folder named `dist\SC4UIScale-v3.0.0\` exists on disk and is
plausibly one `Compress-Archive` away from being the public release. Measured:

| artefact | in `dist\v3.0.0\` | current build | delta |
|---|---|---|---|
| `SelectiveArt-15x` | 10,722,715 B, **Aug 14 10:01** | ~~10,807,416 B, **Aug 15 21:26**~~ **10,718,552 B, Aug 16 12:16** | ~~**−84,701 B**~~ **+4,163 B** |
| `SC4UIScale.dll` | 444,928 B, **Aug 14 13:37** | ~~467,456 B, **Aug 15 20:37**~~ **481,280 B, Aug 16 11:13** | ~~**−22,528 B**~~ **−36,352 B** |
| `ItemIcons-2x` | Aug 3 23:45 | — | — |
| `WebText.dat` | Jul 22 22:48 | — | — |

**2026-08-16: re-measured. The bundle has NOT moved (both files still Aug 14,
byte-identical); the working tree has moved twice. `SelectiveArt-15x` was
rebuilt at 12:16 by `build_selective_safe.py` (Aug 16 12:11, #170 at
`build_selective_safe.py:704`), and the DLL was rebuilt at 11:13. The bundle is
now TWO defect generations behind — pre-#170 as well as pre-#157/#160 — so this
blocker is stronger, not weaker.**

**⚠ The SIZE delta is no longer the evidence.** The current build *shrank* from
10,807,416 B to 10,718,552 B (−88,864 B) across the Aug 16 rebuild, overshooting
past the bundle, so the bundle is now **4,163 B larger** than current rather than
84 KB smaller. A near-zero size delta here means *nothing* about freshness — the
`Aug 14` **timestamp** is the whole proof. Do not let a small delta talk anyone
into shipping this folder. *(Delta convention in this table is (dist − current);
both original rows reproduce under it, which is why the new SelectiveArt figure
is **+**4,163 and not −4,163.)*

~~The 84 KB gap in `SelectiveArt-15x` is exactly the change that landed when the
preview trees were rebuilt at 21:25-21:26 and weeks of accumulated
`no-snap`/`nine-slice` list edits finally reached the art. **The bundle
therefore carries pre-#157 and pre-#160 art at 1.5×**, plus a DLL that predates
#161 and the current `ScaleRound`.~~
**2026-08-16: that 84 KB gap no longer exists — the Aug 16 12:16 rebuild moved
the current build to 10,718,552 B, 4,163 B *below* the bundle. The bundle still
carries pre-#157/#160 art (Aug 15 21:26 rebuild) and now pre-#170 art (Aug 16
12:16 rebuild) at 1.5×, plus a DLL that predates #161, the current `ScaleRound`,
and both the Aug 15 20:37 and Aug 16 11:13 builds.**

**Also missing from the bundle entirely:** `z_SC4UIScale_MenuFix.dat` (6
entries, untagged, always-on, listed in both `Deploy-OnGameClose.ps1` and
`Test-DatIntegrity.ps1`). `Build-Dist.ps1:94-99` puts it behind
`-IncludeUnbuildable` with the reason *"it rewrites CAM's gameplay data, so
shipping it is a [deliberate omission]"* — that is a **defensible decision**,
but it means every public CAM user keeps ten broken submenu parents and the
README does not say so. `UncoveredIcons-*` is also absent and that one **is**
correct by construction (#149 rediscovers the set from the player's own Plugins
tree at boot).

**FAILURE SCENARIO.** Someone zips `dist\SC4UIScale-v3.0.0\` and uploads it.
Every 1.5× player gets the tiled-background desync (#160) and the 9-slice
overlap (#157) that were closed and user-confirmed **yesterday**, on a build
labelled v3.0.0. Neither `Test-DatIntegrity.ps1` nor any gate looks inside
`dist\`.

**FIX.**
1. **Delete or rename `dist\SC4UIScale-v3.0.0\` now**, before anything else in
   this document. A stale folder with the release name is a loaded gun.
2. Add a `dist\` freshness assertion to `Build-Dist.ps1`: every file it copies
   must be **newer than every input it was built from**, and the run must fail
   otherwise. The manifest law (a package is not done until it is in
   `Deploy-OnGameClose.ps1` AND `Test-DatIntegrity.ps1`) has a missing third
   member: **and the dist bundle is rebuilt from the same inputs in the same
   change**.
3. Have `Test-DatIntegrity.ps1` grow a `-Dist` mode that runs its `$EXPECTED`
   entry counts and `$BUILT_PAIRS` hashes against `dist\<version>\Plugins\`
   rather than the live install. Today `dist\` is the only shipped surface with
   **no integrity check at all**.

**BLAST RADIUS.** None on the working tree.

**VERIFY OFFLINE.** After a rebuild, `SHA256SUMS.txt` inside the bundle must
match `Get-FileHash` of the corresponding `tools\packages\` / `build\Release\`
originals, one pair per file, zero exceptions.

**CLASS: SAFE — do step 1 tonight.**

---

## N2. TWO LOAD-ORDER RESOLVERS STILL HARD-CODE SEVEN ARCHIVES — AND ONE OF THE TWO THEY MISS IS `Intro.dat`, THE FILE THAT CAUSED #140
**Rank: 3-equal. CLASS: SAFE. Severity: critical (it invalidates a quoted claim).**

**DEFECT.** `tools\dbpf\find_tgi.py` was taught to **discover** archives at
#140 (`discover_archives()`, `:46-57`). Two other tools were not:

* `tools\dbpf\who_owns_tgi.py:40` — `ARCHIVES = [7 names]`
* `tools\uiscripts\winning_corpus.py:58` — `ARCHIVES = [7 names]`

Measured tonight against the install:

```
DISCOVERED 9:  EP1.dat  Intro.dat  SimCity_1..5.dat  SimCityLocale.DAT  Sound.dat
HARD-CODED 7
MISSED BY who_owns_tgi.py / winning_corpus.py: ['Intro.dat', 'Sound.dat']
```

This is the project memory's own law — *"⛔ SC4 ships NINE archives, not 7 — a
written-down inventory fails silently, and only in the case you needed.
DISCOVER, don't list"* — unfixed in the two tools whose entire job is **resolving
who wins a TGI**. `find_tgi.py:106-119` even prints a warning telling the reader
to run `who_owns_tgi.py` next, i.e. it hands off to the blind tool.

**FAILURE SCENARIO.** This is not a future failure; it is a **currently
load-bearing claim resting on a blind instrument**. `START-HERE.md` §6 and
standing rule 19 both cite `winning_corpus.py` reporting *"0 third-party
winners: every `.UI` in the load order is the game's or ours"*. That census
never opened `Intro.dat` — and `Intro.dat` is precisely the archive whose
omission produced #140 (the startup splash tiling 2×2). The "0" is therefore a
**null with no positive control**, which is the law the project cites more than
any other. It may well still be 0. It is not evidence that it is.

**FIX.** Both files: replace the literal with
`from find_tgi import discover_archives` (or copy the eight-line function) and
print `"discovered N archive(s)"` at the top of every run, exactly as
`find_tgi.py:89` already does. Then **re-run `winning_corpus.py` and re-quote
its number in `START-HERE.md`** with the archive count beside it.

**BLAST RADIUS.** Offline analysis only. It may change the "0 third-party
winners" figure, which is the reason to do it.

**VERIFY OFFLINE.** Positive control, mandatory: after the change,
`who_owns_tgi.py` asked for a TGI known to live **only** in `Intro.dat` must
report `Intro.dat` as an owner. Before the change it reports nothing — which is
the demonstration that the instrument could not have seen it. Run both, paste
both.

**CLASS: SAFE — land tonight.**

---

## N3. THE TWO IN-BUILDER `Upscale2x` CALL SITES PASS ONLY 2 OF THE 4 DERIVED LISTS — AND THE ICON BUILDERS PASS NONE
**Rank: 4-equal. CLASS: BEHAVIOURAL. Severity: high.**

**DEFECT.** ~~`build_selective_safe.py:2211-2214` and
`build_dialog_static.py:1823-1828` both invoke `Upscale2x.exe` on third-party
art with `--nine-slice` and `--no-snap` — **but not `--cell-strips`** (#156),
and not `--height-exact-strips` (#162).~~

**2026-08-16 — HALF FIXED (#169), AND THE DENOMINATOR WAS WRONG.**
`build_selective_safe.py` **now passes `--cell-strips`**: the call runs
`:2261-2277`, with the flag and its list path at **`:2276-2277`**
(`"--cell-strips", os.path.join(TOOLS, "upscale", "cell-strips.txt")`) under a
`:2267-2275` comment naming the 7 advisor sheets and the 220→332 pitch drift.
`build_dialog_static.py:1823-1828` still passes only `--nine-slice` and
`--no-snap`.

There are **five** in-builder `Upscale2x.exe` call sites, not four, so the count
is **four of five still un-wired**:

* `build_dialog_static.py:1823-1828` — `--nine-slice`, `--no-snap`.
* `rebuild_namicons.py:41-43` — `--height-exact-group 6A386D26` and no derived
  list, then post-snaps the width to a multiple of 4 at `:53-57`.
* `build_uncovered_icons.py:567-569` — same shape, post-snap at `:579-583`.
* **`build_itemicons_sub.py:106-108` — `'--factor'` and `'--normalize-names'`
  ONLY: zero derived lists, not even `--height-exact-group`.** It was missing
  from the original four-item list entirely, and it is a live shipping builder
  (`tools\packages\PACKAGES.md`; `_packaging\Build-PublicRepo.ps1:75`;
  consumer `src\ScaleTier.cpp:537` via `SCALING-AXES.md:188`). This section
  hand-listed its own call sites and came up one short — the same failure N2
  indicts.

`--height-exact-strips` is **not** a missing wiring: it was built 2026-08-15,
shipped, **broke the "?" button `{46a006b0,14415860}`** without moving either
#162 hairline, and was deliberately REMOVED from both builders. The flag
survives unused in `Upscale2x.cs:114,121,142,408,839`. See
`TRIAGE-PLAYBOOK.md:603` (forbidden-cures table), `REGRESSION.md:9764,9791`,
and N4. Do not re-add it to any call site.

The comment above each call says
*"wired so the next one cannot inherit the defect silently"* and *"every
consumer of a shared rule needs its own wiring"* — which is exactly right, and
covers two of four.

Worse, `rebuild_namicons.py` and `build_uncovered_icons.py` call the upscaler
with `--height-exact-group` and **no derived list at all**, then apply their own
`snap width to a multiple of 4` afterwards. That post-snap is what moves the
output width off `w × f` — the precise trigger #156 documents for cell-boundary
drift.

**MEASURED TONIGHT** — per-state cell-start drift under the global factor map
that `BuildSampleMap` falls back to when `states` is 0:

```
src      f      out      states   per-state cell-start check (global factor map)
356      1.5    536      4        DRIFT [(state 3, want src col 267, got 268)]
356      2.0    712      4        OK
356      3.0    1068     4        OK
176      1.5    264      4        OK      <- the working sibling
88       1.5    132      4        OK
200      1.5    300      4        OK
```

**356 is NAM's strip width** — `rebuild_namicons.py:9-11` names it as the case
that forces the snap. So NAM's own 4-state strips lose their leftmost column of
state 3 at 1.5×, and are **exactly correct at 2× and 3×**. The integer-tier
control reads zero. The stock 176-wide family is clean, which is precisely why
nobody has seen it: rule 13's working sibling is sitting right next to it.

**FAILURE SCENARIO.** A 1.5× player with NAM installed: the fourth state
(pressed/disabled) of every 356-wide NAM menu button is shifted one source
column, so its icon is clipped on the left by one pixel and shows one repeated
column on the right. Sub-pixel, but it is the #156 sliver family and #156 was
user-reported.

**FIX.**
1. Pass `--cell-strips tools\upscale\cell-strips.txt` at **all four** builder
   call sites, not two.
2. Make `Upscale2x` refuse a run where the *source group* is a known strip group
   (`0x6A386D26`) and `--cell-strips` was not supplied. A flag that must always
   be passed should not be optional; make the tool say so.
3. Better long-term: move the four list paths into a single
   `upscale\derived-lists.json` and give `Upscale2x` one `--lists <file>` flag,
   so a call site cannot pass a subset. **The current design makes "pass 2 of 4"
   the easy mistake and it has already been made twice.**

**BLAST RADIUS.** `NamIcons-15x` and `UncoveredIcons-15x` change; 2× and 3× must
come out byte-identical (control above). Third-party art staged by
selective-safe/dialog-static: **zero sheets match `cell-strips.txt` today**, so
the change is a no-op *now* and a guard for later — say that explicitly rather
than claiming a fix.

**VERIFY OFFLINE.** Rebuild all three tiers of `NamIcons` and hash. **Required:
0 changed bytes at 2× and 3×.** At 1.5×, the changed set must be exactly the
356-wide sheets, and re-running the drift check above must print `OK` on all
rows. `gate_namicons.py` must then be re-run (it is red for an unrelated reason —
fix P0 first or its output is unreadable).

**CLASS: BEHAVIOURAL — proposal only.**

---

## N4. `--height-exact-strips` IS AN ARMED FLAG WITH NO PRODUCER AND NO LIST FILE
**Rank: 7-equal. CLASS: SAFE. Severity: medium.**

**DEFECT.** `Upscale2x.cs` gained `--height-exact-strips` /
`sHeightExactStrips` tonight (#162). There is:
* no `find_height_exact_strips.py` — `tools\upscale\` has only
  `find_cell_strips.py`, `find_nine_slice.py`, `find_no_snap.py`,
  `find_tiled.py`;
* no `height-exact-strips.txt` anywhere on disk;
* no mention of it in `PACKAGES.md`, any builder, or any gate.

**FAILURE SCENARIO.** This is the **fourth** derived list and it is the first
one with no producer. When #162's cure lands, whoever ships it will either
hand-write the list (which is exactly the heuristic-vs-derived distinction rule
22 was written to kill) or forget the flag entirely (N3's shape). Both failures
are silent.

**FIX.** Either write `find_height_exact_strips.py` deriving the set from the
`.UI` bindings the way its three siblings do, **or delete the flag from
`Upscale2x.cs` until #162's cure is decided**. An armed flag with no producer is
a trap; a missing flag is honest.

**BLAST RADIUS.** None — nothing calls it.

**VERIFY OFFLINE.** `grep -rl "height-exact-strips" tools\` must return either
`Upscale2x.cs` **and** a producer **and** a `.txt`, or nothing at all. Today it
returns `Upscale2x.cs` alone.

**CLASS: SAFE — land tonight (the deletion option is one line).**

---

## N5. `PACKAGES.md`'s DOCUMENTED UPSCALE COMMAND SILENTLY UN-SHIPS THREE CLOSED DEFECTS
**Rank: 5-equal. CLASS: SAFE. Severity: high — this is the single most likely contributor-reintroduction path.**

**DEFECT.** ~~`tools\packages\PACKAGES.md:334-336` documents the preview-tree
rebuild as a bare two-line `Upscale2x.exe` invocation with no `--cell-strips`
(#156), no `--nine-slice` (#157), no `--no-snap` (#160).~~

**2026-08-16 — ITEM 1 LANDED, ITEM 2 MOSTLY, ITEM 3 STILL OPEN.**

*Item 1 — done, and better than proposed.* `PACKAGES.md` no longer contains a
hand-typed exe invocation **anywhere** (`grep -c "Upscale2x.exe dbpf"` against
that file: **0**). Step 1 is now a `⛔ USE THE SCRIPT` block that names all three
lists by flag and defect number and mandates
`powershell -NoProfile -ExecutionPolicy Bypass -File upscale\Rebuild-Corpus.ps1`
(single tier via `-Factor 1.5`). Deleting the command beats correcting it — there
is no longer a copyable wrong thing. *(⚠ Do not cite `PACKAGES.md` by line
number: it was being rewritten by another lane on 2026-08-16 and the block moved
from ~:333 to ~:350 to ~:396 inside one minute. Anchor on the `⛔ USE THE SCRIPT`
text.)*

*Item 2 — the load-bearing half is done; the provenance half is NOT.*
`tools\upscale\Rebuild-Corpus.ps1` regenerates all three tiers in one action
(`:45` default `1.5,2,3`; `:94` maps to `preview-15x` / `preview` / `preview-3x`)
and appends all three flag/path pairs to argv (`:101-102`). It **refuses to run**
on a missing list (`:75-80`) or an empty one (`:81-86`, counting non-blank,
non-`#` lines) — that is C3's refusal, but **at the script layer only**: the
`Upscale2x` binary itself still treats an empty list as success, so a hand-typed
exe call outside this script exits 0 exactly as C3 describes. The refusal is also
escapable with `-AllowEmptyLists` (`:48`). ⚠ Item 2 additionally required the
script to **print the SHA-256 of each list file it used**; it does not.
`Rebuild-Corpus.ps1:87` prints flag / entry-count / filename, and there is no
`Get-FileHash` anywhere under `tools\upscale\`. A count cannot distinguish two
different lists of the same length, which is the whole job of a provenance hash —
treat that sub-item as open. New since N5 was written: `-DryRun` (`:54`,
`:104-107`) prints the exact command line without spending a rebuild, which is
the cheap answer to "did we pass the lists?".

⚠ **ITEM 3 IS STILL OPEN.** `Rebuild-Corpus.ps1` has **no** tool-drift check —
nothing compares `Upscale2x.exe`'s timestamp against `Upscale2x.cs` or against
the list files. `grep -riE "LastWriteTime|Get-FileHash|SHA256|IAcceptToolDrift"
tools\upscale\` returns nothing, so *"NEVER REBUILD A TOOL BINARY AND ITS OUTPUT
IN THE SAME CHANGE"* is still unenforced.

(Also note the script shipped as `Rebuild-Corpus.ps1`, not the
`Rebuild-Previews.ps1` named in the FIX below — it rebuilds the whole corpus,
2x included, not just the fractional previews.)
**Anyone who follows the project's own documentation un-ships three
user-confirmed fixes**, at exit 0, and every downstream gate stays green because
each one measures the new tree against the new tree.

**FAILURE SCENARIO.** This is the highest-probability path in this whole
document because it requires no mistake at all — only obedience. And the
three `preview-*` trees are the loudest instance of the stale-cache shape:
2,207 files each, generated by a **hand-typed** command, read by four automated
builders, with **nothing in the repo that regenerates them**. The 84 KB
`SelectiveArt-15x` jump at 21:26 tonight is the measurement of how far they had
drifted.

Additionally: `cell-strips.txt` (Aug 14 09:46), `nine-slice.txt` (Aug 15
11:25), `no-snap.txt` (Aug 15 18:32) and `tiled.txt` (Aug 15 17:58) are **all
older than the `Upscale2x.cs` / `.exe` rebuild at 21:03**, and the trees were
regenerated 22 minutes after that rebuild — which is the REGRESSION law *"NEVER
REBUILD A TOOL BINARY AND ITS OUTPUT IN THE SAME CHANGE"* being broken tonight,
in this tree.

**FIX.**
1. Correct `PACKAGES.md` to the full four-flag command (this is a doc edit, not
   a behaviour change).
2. Replace the hand-typed command with `tools\upscale\Rebuild-Previews.ps1`
   that regenerates all three trees with every derived list, in one action, and
   prints the SHA-256 of each list file it used. A command a human types feeding
   a command a script runs is the generalised shape of every staleness defect in
   this project; the cure is to make the human's command a script.
3. Make that script refuse to run if `Upscale2x.exe` is newer than
   `Upscale2x.cs`'s last commit **or** if any list file is older than
   `Upscale2x.exe`, unless `-IAcceptToolDrift` is passed. That encodes the
   existing law in the one place it can be enforced.

**BLAST RADIUS.** Doc + a new script. No pixels move until someone runs it,
and when they do the output should be byte-identical to what is on disk now —
**which is the acceptance test.**

**VERIFY OFFLINE.** Run the new script into a scratch directory and hash every
PNG against the live `preview-15x` / `preview` / `preview-3x`. **Required: 0
differences at every tier**, including 1.5×. Any difference means the trees on
disk were not built with the flags the script encodes, and that is a finding in
itself.

**CLASS: SAFE — land tonight.**

---

## N6. NO PATCH-FAMILY SUMMARY LINE — A WRONG EXE DEGRADES SILENTLY, ONE FAMILY AT A TIME
**Rank: 6-equal. CLASS: SAFE. Severity: high (it is the whole "game updates" story).**

**DEFECT.** `src\CodePatches.cpp` has ~~26~~ **22 (2026-08-16 recount, `//` comments stripped: 20 `VerifiedWrite(` + 2 `ScaleSizeTable(`; the two remaining matches, `src\CodePatches.cpp:2617` `bool VerifiedWrite(` and `:2573` `void ScaleSizeTable(`, are the helper DEFINITIONS, not call sites)** `VerifiedWrite` / `ScaleSizeTable`
call sites and **39** distinct `"... skipped."` / `"... DECLINED"` log strings.
*(The **39** figure is left as written — it is UNVERIFIED, not disproven: C
string-literal concatenation across lines defeats a reliable count.)*
Every one logs individually at `LogLevel::Info` and returns false. There is
**no aggregate line** anywhere — nothing says *"N of M patch families applied,
K declined"*.

Two of the families are additionally **ungated** (no ini key can turn them
off): `ApplyGraphLegendBudgetScale` and `ApplyRegionCameraScale`, per
`gate_patch_families_combined.py`'s own ownership dump.

**FAILURE SCENARIO — this is the "what happens when the game updates" answer.**
`SC4VersionDetection.cpp` reads the file version and
`SC4UIScaleDllDirector.cpp:331-338` logs *"Game version %u detected (expected
641)"* at Error — **and continues**. That is the right call (a soft gate beats
refusing to load). But on a re-patched exe — a store re-release, a NoCD/4GB
variant, a community exe patch, or simply another DLL mod that got to the same
bytes first — the window-tree scaling still works, so the game *looks* mostly
right, while some subset of ~270 byte patches quietly declines. The user sees
"the tooltips wrap wrong and the graph legend is at 1×", files a bug, and the
first thing anyone asks is *which patches applied?* — a question the log can
only answer by reading 39 possible lines and knowing which ~~26~~ **22** to expect.

Most fragile families, in order, and what silently kills each:

| family | fragility | what kills it |
|---|---|---|
| `kGraphLegendBlocks` (#57) | **highest** — 3 **re-encoded instruction blocks**, length-exact, with folded `mov`s and a store proven dead by liveness | any recompile of the surrounding function; another mod's hook landing inside the 19-byte window |
| advice-row imm8→imm32 (#136, 3× only) | **highest** — rewrites a 19-byte window at `0x0079388B`, and is **hard-coupled to `SelectiveArt` = 655 entries**. `Test-DatIntegrity.ps1:29-33` says in prose: if the re-encode is refused, the builder filter AND the count must go back to 651 **in the same build** | the re-encode declining. **Nothing checks this coupling** — it is a comment, not a gate |
| `kCostBox*` (#159) | high — newest, and **currently invisible to the overlap gate** (P0) | anything; it is unscanned |
| `kHtmlFontSizeTable` / `kHtmlHeadingSizeTable` | medium — `.rdata` tables, verify-all-7-before-write | a locale/EP variant with different base sizes |
| `kIntroVidSites` (#138) | low — 4 sites, 6 mandatory negative controls in `gate_introvid.py` | already the best-gated family here |

**FIX.**
1. **One summary line, always, at the end of patch application:**
   `"CodePatches: %d of %d families applied; %d declined [names]"`. Log it at
   `LogLevel::Error` when `declined > 0` so it survives any log level a user
   might have set. This is the `ICONPROBE` positive-control pattern applied to
   the patch surface, and it is the single highest-value one-line change in
   `CodePatches.cpp`.
2. **Assert the advice-row coupling in the DLL, not in a comment.** At 3×, if
   the wide re-encode declines and `SelectiveArt` carries the X glyphs, log a
   loud `"#136 COUPLING VIOLATED"`. Better: add the reverse check to
   `Test-DatIntegrity.ps1` so the 655/651 decision is machine-checked.
3. Consider giving the two ungated families an ini key, purely so a user with a
   variant exe has an off switch that is not "uninstall the mod".

**BLAST RADIUS.** Item 1 is log-only — zero pixels. Item 2 is a new assert.
Item 3 adds ini keys, which must then be added to
`_tests\Test-ShippingIniKeys.py`'s expectations (the manifest law applies to ini
keys too).

**VERIFY OFFLINE.** Item 1 needs a launch to see, so ship it and read the log
next session. Item 2 is offline: `Test-DatIntegrity.ps1` can compare the 3×
`SelectiveArt` count against a flag. **Positive control for item 1:** the
summary must print even when `declined == 0`, or an absent line is
indistinguishable from a build that never reached the code.

**CLASS: SAFE (item 1 is log-only). Land item 1 tonight.**

---

## N7. THE `ScaleRound` / `RoundHalfUp` PAIR IS NOT ACTUALLY THE SAME FUNCTION IN THE TWO TRANSLATION UNITS
**Rank: 9. CLASS: SAFE. Severity: medium (latent).**

**DEFECT.** `src\UiSpike.cpp:177-180` — `RoundHalfUp(double v)` returns
`floor(v + 0.5)`. `src\ScaleTier.cpp:966-969` — `RoundHalfUp(float v)` returns
`static_cast<int>(v + 0.5f)`, i.e. **truncation toward zero**, not floor.

For non-negative `v` they agree, and every current caller in `ScaleTier.cpp` is
a dimension, so nothing is wrong today. But #162's whole finding is that
`llround` vs half-up mattered *only for negative values* — and the file that
still uses truncation is the one whose header comment claims the rules are
*"matched exactly"* to `Upscale2x.cs`, which uses `Math.Floor(v*factor + 0.5)`.

**FAILURE SCENARIO.** The first time anyone passes a negative offset through
`ScaleTier::RoundHalfUp` — an anchor, a delta, a `(imgW - winW)/2` that goes
negative on an over-wide sheet — the two translation units disagree by one
pixel, at fractional tiers, in the exact family (#152/#153, the offset-parity
law) that cost two user-reported defects. The bug will look like a parity
defect and it will not be one.

**FIX.** Make `ScaleTier.cpp`'s helper `static_cast<int>(std::floor(double(v) + 0.5))`
and add a static assert / unit check that it agrees with `UiSpike`'s over
v ∈ [-64, 64]. Or better: hoist one definition into a shared header so there is
one function, not two.

**BLAST RADIUS.** Zero today — every present caller passes a positive
dimension, and that is provable by inspection of the 40-odd call sites. It
becomes non-zero the moment someone adds a negative one, which is precisely why
it should be fixed while it is free.

**VERIFY OFFLINE.** A table over v ∈ [-64, 64] × f ∈ {1, 1.5, 2, 3} printing
both implementations; require identical output. **Control: they must already be
identical for all v ≥ 0 — if they are not, the analysis above is wrong and stop.**

**CLASS: SAFE — land tonight.**

---

## N8. `Test-DatIntegrity.ps1`'s `$EXPECTED` HAS NO ENTRY-COUNT ROW FOR `ThirdPartyUI-15x` / `-3x`
**Rank: 10. CLASS: SAFE. Severity: medium.**

**DEFECT.** `$EXPECTED` lists `ThirdPartyUI-2x` (2 entries) and every other
package at all three tiers — but not `ThirdPartyUI-15x` or `ThirdPartyUI-3x`.
Both exist on disk (`tools\packages\15x\`, `tools\packages\3x\`) and both are in
`$BUILT_PAIRS` (lines 370-371), so their built==deployed **hash** is checked.
Their **entry count** is not.

**FAILURE SCENARIO.** Half of the manifest law. A hash check catches
staleness; an entry-count check catches a builder that silently dropped a
resource. `ThirdPartyUI` is the CoriBoom package — the one whose *stale dat with
dangling clone refs* was the root cause of #58. A rebuild that emits 1 entry
instead of 2 passes both halves of the current check (fresh hash, matching
pair) and ships a half-package.

**FIX.** Add the two rows with `entries = 2`. One line each.

**BLAST RADIUS.** None.

**VERIFY OFFLINE.** `Test-DatIntegrity.ps1` after the edit; the two new rows
must report `2`. **Negative control:** temporarily assert `3` and confirm it
goes red — a row that cannot fail is not a check.

**CLASS: SAFE — land tonight.**

---

## N9. THE 3× ItemIcons PAIR HAS NOT BEEN REBUILT SINCE BEFORE #149
**Rank: 11. CLASS: SAFE (probably a no-op — say so honestly). Severity: low-medium.**

**DEFECT.** Measured file dates in `tools\packages\`:

```
3x\z_SC4UIScale_ItemIcons-3x.dat        2026-08-03 23:39
3x\z_SC4UIScale_ItemIconsSub-3x.dat     2026-07-29 22:52
15x\z_SC4UIScale_ItemIcons-15x.dat      2026-08-14 10:03
15x\z_SC4UIScale_ItemIconsSub-15x.dat   2026-08-14 10:03
   ~~...every other 15x/3x dat:           2026-08-15 21:26/21:27~~
   2026-08-16 RE-MEASURE - true only on Aug 15; 6 of 8 rebuilt since:
   15x + 3x DialogStatic                2026-08-15 21:26 / 21:27
   15x + 3x CamUI, SaveWarningUI        2026-08-16 11:42 / 11:43
   15x + 3x SelectiveArt, ThirdPartyUI,
            WarriorUI                   2026-08-16 12:16
   The four ItemIcons rows above are UNCHANGED - the 15x pair is now
   two rebuild rounds stale, not one day.
15x\FontStyle-15x.ini                   2026-08-06 10:59
3x\FontStyle-3x.ini                     2026-08-03 08:03
```

*(Dates verified 2026-08-16 against `tools\packages\15x\` and `tools\packages\3x\`.
DialogStatic is the only pair still bearing the struck line's timestamps.)*

The 3× ItemIcons pair predates #149 (Aug 6), #156 (Aug 14) and #157/#160
(Aug 15). It was built from a `preview-3x` tree that no longer exists.

**HONEST ASSESSMENT — and this is the interesting part.** All four of the
mechanisms that changed since (`--cell-strips` sampling, `--nine-slice`,
`--no-snap`, `CellUnit`) are **provable no-ops at an integer factor**:
`ScaleDim` returns before `CellUnit` is consulted when `factor == floor(factor)`,
and `BuildSampleMap`'s per-block map reduces to the factor map when
`blockOut == blockSrc × factor` exactly. So the 3× pair is *probably*
byte-identical to what a rebuild would produce. **The 15× pair is the one that
matters**: Aug 14 10:03 predates `nine-slice.txt` (Aug 15 11:25) and
`no-snap.txt` (Aug 15 18:32), and those two lists **do** move sheets at 1.5×.

This is rule 11 doing useful work in both directions: it tells you which stale
artefact to ignore and which to chase.

**FIX.** Rebuild all four (both tiers, both packages) and hash. Expect:
**0 changed bytes at 3×** (that is the control that proves the integer-immunity
argument) and a named, small set of changed sheets at 1.5×.

**BLAST RADIUS.** 1.5× menu icons.

**VERIFY OFFLINE.** Rebuild to a scratch dir, hash against the shipped dats.
If 3× differs at all, the integer-immunity claim above is **wrong** and that is
a much bigger finding than the staleness — escalate rather than shipping.

**CLASS: rebuild is BEHAVIOURAL at 1.5×; the hash comparison is SAFE and should
be run first, tonight, because a 0-diff at 3× would close half of this item.**

---

# PART 3 — WHERE THIS PROJECT BREAKS NEXT

Ranked by expected damage = (probability it happens) × (how wrong the screen
looks) × (how long before anyone notices).

---

## B1. A 4TH TIER — AND THE FACT THAT `kPackages` ALREADY DECLARES ONE
**Expected damage: HIGH. Probability: moderate (4K/8K displays are the ask that produces it).**

`src\ScaleTier.cpp:43-48` already contains `{ 4.0f, L"-4x" }`, first in the
list, tried first. It is inert only because `PackageInstalled()` finds no
`z_SC4UIScale_SelectiveArt-4x.dat` on disk. **The moment anyone drops a 4x dat
into Plugins — even as an experiment — the DLL selects tier 4** on any display
≥ 3520×2232, and:

* **Every builder's `_factor_tag()` already handles it.** All five return
  `"4x"` for `4.0` via their `"%dx" % int(round(f))` fallback. So the packages
  would *build* and *be named correctly*, which is the dangerous part — the
  pipeline offers no resistance.
* **Task #100 says explicitly: DO NOT SHIP the 4x bubble art** — *"flipping the
  flag alone predicts 8x at 2x tier (#98's exact shape)"*.
* **Nine of the gates hard-code the tier list**: `FACTORS=(1.5,2,3)`,
  `TIERS=[1.5,2,3]`, `f∈(1,1.5,2,3)`. A 4× build passes every one of them
  **by not being looked at**. That is rule 42 (a gate is only as honest as its
  scope) with a concrete future date on it.
* `prove_chart_legend.py` is already 27% SKIPPED on unmeasured `lineHeight` at
  1.5×/3×; a fourth tier makes that worse, not better.
* `emu_text_extent.py`'s Arta metrics are **measured at 13 pt and 26 pt only**.
  A 4× tier needs ~52 pt and there is no measurement there at all — the model
  would extrapolate silently.

**Hardening, in order:**
1. **Make the dormant entry loud.** If `PackageInstalled({4.0f})` is true, log
   `"ScaleTier: a -4x package is present. This tier is UNVALIDATED (task #100)."`
   at Error, every launch. A dormant code path that will one day wake up should
   announce itself before it does.
2. Give every gate a single shared `TIERS` constant read from one file, so
   adding a tier is one edit rather than nine silent omissions.
3. Measure Arta at a third size before anyone builds 4×, so
   `emu_text_extent.py` interpolates rather than extrapolates.

## B2. A RESOLUTION NOBODY HAS TRIED
**Expected damage: HIGH. Probability: certain, on public release.**

`Decide()` is `largest installed N with 880N ≤ w, 558N ≤ h, N ≤ min(w/800, h/600)`.
Consequences the record does not cover:

* **Ultrawide.** 3440×1440: `capH = 2.4`, so 2× is selected and the UI occupies
  a 1760-px-wide strip of a 3440-px screen. Nothing is *wrong*, but the dock
  anchoring at extreme aspect ratios has never been eyed. 5120×1440 selects 2×
  as well.
* **Exact-boundary resolutions.** 1600×1200 selects 2× with **zero slack**
  (`558×2 = 1116 ≤ 1200`, `min(2.0, 2.0) = 2.0`). #101 was exactly this and was
  resolved by *adjusting the gate*, not by removing the zero-slack case. 1920×1200
  also lands exactly on 2.0. The current monitor at 2400×1600 **overhangs 3× by
  200 px in height** and START-HERE predicts *"expect any 3x breakage at the
  BOTTOM (the dock) first"* — that prediction has still not been tested.
* **DirectX 7's 2048 limit.** The gauge needle strips are already 2805-3740 px
  wide at 1× and must never be stretched. At 3× several more surfaces cross
  2048. #109 (window-vs-surface) was this family.
* **The tier is decided from `SC4GraphicsOptions.ini`, not from the actual
  backbuffer.** `SC4UIScaleDllDirector.cpp:165-166, 298-299` reads
  `WindowWidth`/`WindowHeight`. If dgVoodoo, a driver, or Windows DPI
  virtualisation presents something else, the tier is decided from a number the
  renderer ignored. `ScaleRemap` compensates for the *cursor*, not for the tier
  choice.

**Hardening:** log the decision inputs and the winner as one line —
`"ScaleTier: ini=WxH, client=WxH, cap=%.2f, chose %.2f"` — so a user's bug
report contains the whole decision. Today it takes two log lines 90 lines apart
to reconstruct it, and #111 was closed as REFUTED because someone read exactly
those two lines as evidence.

## B3. A PLUGIN THAT COLLIDES WITH OUR TGIs
**Expected damage: HIGH. Probability: high — this is what a public release IS.**

Everything the project knows about collisions is **offline, `.UI`-only, and
snapshot-dated**:

* `winning_corpus.py` resolves `.UI` scripts. It does not resolve **art** TGIs.
  We override ~655 art resources from the Plugins **root**, and by the
  load-order law *any* mod in *any* subfolder beats us on all of them. A UI
  reskin (there are several on Simtropolis) silently wins ~655 resources and
  the player sees 1× art in 2× windows — the #44/#58 symptom, with no
  instrument that can see it.
* `extracted-plugins\` is dated Jul 31 and **goes stale the moment a mod is
  added or removed**. It is per-install by nature.
* Our four mod-gated packages (`CamUI`, `WarriorUI`, `SaveWarningUI`,
  `ThirdPartyUI`) gate on **exact file size** for three of them. A CAM point
  release changes `CAM_Extended_Essentials.dat` by one byte and our package
  correctly disables — good — but the player just loses those six dialogs with
  no message. `Test-ThirdPartyGates.ps1` covers this offline; the *player* gets
  nothing.

**Hardening, highest value first:**
1. **A runtime collision census, once per session, at PostAppInit.** Walk our
   own shipped TGI list, ask the resource manager who currently owns each, and
   log every one we do **not** win. This is the direction rule 19 names —
   *enumerate what EXISTS and subtract what is handled* — applied to art instead
   of scripts. It is cheap (one `GetResource` per TGI), it needs no plugin
   parsing, and it converts an invisible failure into one log line.
2. **Tell the player when a mod gate fires.** `"z_SC4UIScale_CamUI disabled:
   CAM_Extended_Essentials.dat is 2817431 bytes, expected 2817430. Your CAM was
   updated; this mod's copy would be stale."` at Error.
3. Re-run `winning_corpus.py` **after** the N2 archive fix and re-quote its
   number.

## B4. THE GAME UPDATES, OR dgVoodoo DOES
**Expected damage: MEDIUM-HIGH. Probability: low for the game, moderate for dgVoodoo.**

* **The game.** Covered in N6. The soft version gate is the right design; the
  missing summary line is the gap. Note also that the 4GB/LAA patch has
  **already blinded every exe-pinned gate once** (START-HERE §3), and the
  recorded procedure — *bypass, run every byte assertion, re-pin only if all
  pass, and write down that you did* — exists because someone nearly re-pinned
  on a tool's say-so. That procedure lives in prose in one file. It should be a
  `-Bypass` switch on the gates themselves, so following the law is easier than
  breaking it.
* **dgVoodoo.** The record's own finding: `WindowMode=Windowed` in SC4's ini
  **does nothing on its own**; `Apps\dgVoodoo.conf` `FullScreenMode` overrides
  it. Our tier decision reads SC4's ini and never dgVoodoo's. A dgVoodoo update
  that changes a default, renames a key, or changes its config file layout
  changes what the player actually sees while every number we read stays the
  same. There is **no probe at all** for the wrapper's effective state.
  **Hardening:** log the presence, version and `FullScreenMode`/`CaptureMouse`
  of `dgVoodoo.conf` if it exists beside the exe. Read-only, three lines, and it
  makes the single most confusing class of user report self-diagnosing.

## B5. WHICH BYTE PATCHES BREAK FIRST
Ranked in N6's table. The summary: **the two re-encoded-instruction families
(#57 graph legend, #136 advice row) are an order of magnitude more fragile than
the ~28 constant-rewrite families**, because a constant rewrite fails safe (the
verify-before-write mismatches and it skips) while a block re-encode fails safe
*only if the whole set declines together* — which `CodePatches.cpp:2823-2834`
and `:3101-3126` do correctly, and which is worth preserving explicitly the next
time someone "optimises" a partial application.

The **silent disabler** to watch for is not a game update. It is **another DLL
mod hooking the same function first**. `VerifiedWrite` compares bytes and skips
on mismatch, so we lose gracefully — but we lose *silently*, and the SC4 DLL-mod
ecosystem is growing. N6 item 1 is the entire answer.

## B6. WHERE A FUTURE CONTRIBUTOR REINTRODUCES A FIXED DEFECT
Ranked by *(likelihood) × (would a gate catch them?)*:

| # | the reintroduction | would a gate catch it? |
|---|---|---|
| 1 | ~~**Follows `PACKAGES.md`'s upscale command** and un-ships #156/#157/#160~~ **CLOSED 2026-08-16** — step 1 is now `Rebuild-Corpus.ps1`, which wires all three derived lists into every tier's invocation and throws on a missing or empty one (`PACKAGES.md`'s `⛔ USE THE SCRIPT` block; `tools\upscale\Rebuild-Corpus.ps1:69-88,101-102`; lists present and non-empty: 193 / 30 / 121). Escape hatch: `-AllowEmptyLists` (`:48,:82`). | **NO — and that has NOT changed.** No gate holds a 1x-derived expectation for these three flags (`gate_btn_undercover.py`'s `states * R(cell1x * f)` check is REPORT-ONLY for the pre-scaled population, per its own header), so a flagless rebuild is still invisible; what closed is the *doc-obedience* path, not the gate blindness. N5.1 shipped. N5.2 shipped **as `Rebuild-Corpus.ps1`, not the `Rebuild-Previews.ps1` N5 names, and WITHOUT the SHA-256-per-list provenance line — it prints entry counts (`:87`)**. **N5 item 3 is still unbuilt: no `-IAcceptToolDrift`, no exe-vs-source or list-vs-exe mtime check (`:42-55`), and the drift is still on disk (exe 08-15 21:03, all three lists older).** |
| 2 | **Widens `kCellCounts` beyond {3,4}** — it reads like a tunable, and "safer to include more counts" is the obvious wrong intuition | **NO.** #149's measurement (152 vs 34 mismatches) lives in a comment, not a check. Add an assert that `kCellCounts.Length == 2`. |
| 3 | **Rebuilds `Upscale2x.exe` and its output in one change** | **NO.** It happened tonight (21:03 / 21:26). N5 item 3 is the fix. |
| 4 | **Adds a package and forgets `Test-DatIntegrity.ps1`** | Partly — `$BUILT_PAIRS` catches staleness but not a missing row (N8 is a live instance). |
| 5 | **Adds a byte-patch family and forgets the gate's `WIDTHS`** | **YES** — and this is the model. The gate FAILS on an unregistered table with a message that explains why. Every other gate should copy this. (It is red for exactly this reason right now — P0.) |
| 6 | **"Fixes" the `gate_btn_cell_vs_window` 420 mismatches at 2×/3×** | Partly — the gate documents itself as REPORT-ONLY with an inverted control. Its header is the only defence and headers get skimmed. |
| 7 | **Deletes `make_fontstyle.py --selfcheck` because it is red** | **NO.** C2 is the fix, and the sequencing matters: fix the generator *before* anyone concludes the gate is broken. |

**The generalisable hardening:** the one gate that works (#5) works because it
**fails on the thing it cannot see**, rather than passing on the things it can.
Every other gate in `tools\uimap\emu\` passes when its known inputs are fine.
That asymmetry is the single most transferable idea in this codebase and it
should be written into `METHOD.md`.

---

# PART 4 — SHIPPING BLOCKERS FOR PUBLIC v3.0.0

Ordered. **1-4 are hard blockers.**

| # | blocker | why | class |
|---|---|---|---|
| **1** | **`dist\SC4UIScale-v3.0.0\` is stale** (N1) — pre-#157/#160 art, pre-#161 DLL, and it already carries the release name | Uploading it ships two defects that were closed and user-confirmed yesterday | SAFE — delete tonight |
| **2** | **Two gates red** (P0) — including the only overlap check, currently blind to the #159 family | "All gates green" is in `START-HERE.md` and is false | SAFE |
| **3** | **The 66-vs-68 icon split** (C1) — three packages, two heights, 1.5× only | A public 1.5× user with NAM sees mixed button heights; zero at 2×/3× proves it is a defect | BEHAVIOURAL — needs one eyes-on |
| **4** | **`--selfcheck` red** (C2) — the font generator no longer reproduces its own shipped tables | Anyone who regenerates fonts for the release ships a smaller Legend at 2× and 3× | SAFE once byte-identity is proven |
| 5 | **`winning_corpus.py`'s "0 third-party winners" rests on a 7-of-9 archive scan** (N2) | It is quoted in `START-HERE.md` as a closed finding; it is currently a null with no positive control | SAFE |
| 6 | **`MenuFix` is deliberately excluded from `dist\` and the README does not say so** | Public CAM users keep ten broken submenu parents and have no way to know the fix exists | SAFE — doc |
| 7 | **`dist\` has no integrity check** — `Test-DatIntegrity.ps1` only ever looks at the live install | The only shipped surface with no verification | SAFE |
| 8 | **Near-vanilla verification never done** (existing task #148) | Every eyes-on to date is on one install with CAM + NAM + submenus + warrior. The load-order law means an install *without* them exercises different winners | needs a second machine or a clean profile |
| 9 | **Third-party / Maxis derived-content audit** (existing task #146) | Every shipped `.dat` contains upscaled Maxis art. `NOTICE` and `THIRD-PARTY-NOTICES.md` are thorough about *code*; the position on *art* needs to be stated in one sentence a moderator can read | needs a decision, not a build |
| 10 | **`ThirdPartyUI-15x/-3x` entry counts unchecked** (N8) | Half the manifest law | SAFE |
| 11 | **`--height-exact-strips` armed with no producer** (N4) | A trap for whoever ships #162 | SAFE |
| 12 | **#162 still open** — the cure is a **re-phasing, not an elimination**: it fixes features on even rows and breaks features on odd rows (202 → 114 doubled runs is *net better*, not *fixed*) | Shipping a "fix" that moves the defect is worse than shipping the known one, unless the 114 are enumerated | BEHAVIOURAL |

---

# APPENDIX — WHAT CAN BE LANDED TONIGHT

**SAFE, no eyes-on, no pixel changes.** In dependency order:

1. **P0.2** — delete/rename `dist\SC4UIScale-v3.0.0\`. *(one command)*
2. **P0.1** — register the five #159 tables in
   `gate_patch_families_combined.py`'s `WIDTHS`; re-run to exit 0.
3. **C4** — `diff.py::scale_round` → half-up; re-run `Test-UiMapDiff.ps1 -Fresh`.
4. **C3** — `Upscale2x` list-file validation: zero entries or an unparseable
   line → print it and `return 1`.
5. **N4** — delete `--height-exact-strips` (or write its producer).
6. **N8** — two rows in `Test-DatIntegrity.ps1`.
7. **N7** — `ScaleTier::RoundHalfUp` → `floor`, with the v ≥ 0 agreement check.
8. **N2** — `who_owns_tgi.py` + `winning_corpus.py` → `discover_archives()`,
   **with the `Intro.dat` positive control run and pasted**.
9. **N5.1** — correct `PACKAGES.md`'s upscale command to four flags.
10. **C7** — `build_itemicons_sub.py` compares `(name, w, h)`.
11. **C2** — the font generator fix, **gated on all three regenerated
    `FontStyle-*.ini` coming back byte-identical to the shipped files.** If any
    differs, stop.
12. **C6** — tri-state `MatchesAnyTierFontSource` + the positive-control log
    line. **After C2.**
13. **N6.1** — the patch-family summary line (log-only).
14. **C5 half 2** — make `BuildSampleMap`'s decline loud and counted.
15. **N9's hash comparison** (not the rebuild) — a 0-diff at 3× closes half of
    N9 and independently confirms the integer-immunity argument this document
    leans on in four places.

**BEHAVIOURAL — proposals only, do not apply:**
C1 (the 66-vs-68 decision), C5 half 1 (`CellUnit` × derived states), N3 (the
missing `--cell-strips` at four call sites), N9's actual 1.5× rebuild, and
anything touching #162.

---

## THE ONE-LINE VERSION

The project's instruments are excellent at asking *"is what we built still
correct?"* and structurally unable to ask *"is the rule we built it from still
the rule?"*. Six of the fourteen items above are the second question:
`make_fontstyle`'s guard tests the wrong variable, `diff.py` models a rounding
rule the DLL abandoned, `ScaleTier` claims a port is exact when it is missing
three switches, `PACKAGES.md` documents a command that un-ships three fixes,
two resolvers list seven of nine archives, and a dist folder named v3.0.0
contains yesterday's art. Every one of them passes every gate.
