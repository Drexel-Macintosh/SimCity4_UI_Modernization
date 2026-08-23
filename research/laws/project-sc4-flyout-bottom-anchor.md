# Law: Sub-flyout placement is bottom-anchored, and the anchor is a MEASURED game parameter, never inferred

**Date:** 2026-08-23
**Status:** ROOT-CAUSE FIX IMPLEMENTED, offline-verified, NOT YET live-tested
(see "Attempt 4" below — this supersedes "The fix: SubSharedBottom()" as
what actually ships; disaster twin still NOT fixed — see "What is still
open")
**Scope:** Sub-flyout `0x8A6E61E0` (shared second-level menu, builder `sub_7EAEB0`,
`SubPlaceDetour` in `src/UiSpike.cpp`); the same defect shape — and this same
method — applies to any other menu family where content of varying size
should dock to one shared edge.

## The rule

**Corrected 2026-08-23 (adversarial review) - what actually ships is
narrower than the headline below originally claimed.** The bottom is
"identical in all of these menus" only for menus whose own content is
tall enough to clamp against the game's real bottom margin (`mB`) in the
first place — Build Park/Green Spaces/Sports Grounds/Plazas (all spawned
from the same "Parks" bar, cy=997) all reach it, so they share 1166.
Police (cy=397, a DIFFERENT bar) does not reach it at any of its own
counts, so a cnt=5 Police sub-menu and a cnt=3 sibling on the SAME button
do NOT share a bottom with each other (682 vs 684) — they simply both
center on their own button. This is still correct and still satisfies
every measurement on record; it is the ORIGINAL headline claim ("regardless
of how many items... every menu spawned from a given first-level flyout
button") that overstated the scope. The real rule:

A sub-flyout's SCALED bottom edge is the SAME absolute position for every
menu spawned from a given first-level flyout button **whenever that
bottom is bound by the game's own screen margin** — which is what "short
strips grow upward from that shared bottom" actually describes: the
CLAMP is shared (one `mB`, one margin, for every menu off one button),
not a hand-picked target every menu is forced toward regardless of
whether its own geometry would ever reach it. This is the user's law,
stated twice in plain language:

> "The bottom part of the flyout should be identical in all of these
> menus. Basically it should build from that bottom and fill in above it."

The shared bottom is **derived from the game's own `Place()` parameters**
(`mB`, the native bottom-margin clamp), never from a per-container
"recovered" position, a per-button reference chain, or a hand-tuned pixel
constant. See "The measurement that actually solved it" below for why the
first two of those three all failed or would have produced a DIFFERENT
bottom per menu — violating the law by construction, not by bug.

## What the defect looked like

At 2x, **Sports Grounds** (5-item strip) and **Plazas** (mayor column)
attached the ring's arm too high, with the strip's bottom item(s) clipped
by the container edge. **Build Park** (11-item) and **Green Spaces**
(12-item) were correct. Screenshots (2026-08-23): Sports Grounds' picker
visibly stopped short of the screen-bottom docking line every OTHER flyout
used; Green Spaces reached that same line with its ring arm correctly
seated beside the top item.

## What was tried and failed

### Attempt 1 — the "recovered cy" per-container inversion (shipped since v2.46.0, present through v4.0.35)

The birth hook has no direct access to the spawning button's screen
position, so it INVERTED the game's own placement formula from the
container's own native top:

```
nativeTop = (53>>1) - (ch>>1) + cy - 29
=> cy      = nativeTop + (ch>>1) + 3
```

...then ran a "self-check" (`check == nativeT`) before trusting the result,
with a comment claiming: *"If it does not [reproduce nativeTop], a 1x
clamp fired and the inversion is not valid — fall back to the constant
delta."*

**This self-check is an unconditional algebraic tautology.** Substitute the
`cy` expression into `check`: the `(ch>>1)` terms cancel and the constants
collapse to exactly `nativeT`, for every value of `ch` and `nativeT`. It
can never be false — confirmed by an independent adversarial code review,
2026-08-23. The "fallback for an invalid inversion" it was written to gate
has never once triggered, in any build, since v2.46.0.

Worse: the recovered `cy` this technique produces is **not the game's real
`cy`** whenever the container's native placement was actually bound by a
clamp (as Build Park/Green Spaces' was — see below). It happens to
reproduce the correct SCALED answer for the cnt≥8 case through a
*different* clamp inside the scaled model (coincidentally), which is why
that case looked "approved" for years while the underlying technique was
already unsound. This is exactly the trap law 112 describes: *"a patch
that provably ran and changed nothing on screen eliminates its layer"* —
except inverted here: a patch that ran and produced the RIGHT answer for
one input family says nothing about its correctness for another.

### Attempt 2 — bottom-anchor via a hand-derived formula (v4.0.36-attempt-1, rolled back within the hour)

`bottom = SubPlaceTop(full8H, cy, viewH, f) + full8H`, forgetting that the
approved chain also subtracts the empirical bornshift
(`SubContainerShiftPx()`, 232px at 2x) before adding the container height.
Every 8-row menu dropped exactly 232px. **The law was right; the reference
constant was wrong** — this is why the fix below is proven against an
offline gate (`_tests/Test-SubFlyoutPlacement.py`) BEFORE any deploy.

### Attempt 3 — reusing the SAME button's own 8-row-equivalent chain (rejected on paper, before ever being built)

The obvious next idea: for a short-count container, compute what an 8-row
container FROM THE SAME BUTTON would have gotten, using that same button's
OWN recovered `cy`, and target that bottom instead. Worked out by hand
against the measured constants: `SubPlaceTop(874, cy=997) − 232 + 874 =
1197`, not the approved `1150`. **A per-button reference bottom gives a
DIFFERENT bottom per button** (1197 for Sports Grounds' button vs. 1150 for
Build Park's), which directly violates "identical in all of these menus."
This is not a bug to fix — it is a structural reason this whole APPROACH
(reference-chain-per-button) cannot satisfy the law, no matter how
carefully the reference chain is computed. Confirmed independently by the
offline gate's negative-control-style check before any live build.

## The measurement that actually solved it

`SubPlaceDetour`'s Place() call receives `(w, h, cx, cy, mT, mB)` — and
`cy`, `mT`, and `mB` had **never been logged**, in any build, ever. A
one-line diagnostic (`SUBPLACE`, log-only, no behavior change) fixed that.
Live capture, one session, 2026-08-23, 2x, 7 sub-flyout opens spanning
Build Park (cnt=11), Green Spaces (cnt=12) and Sports Grounds (cnt=5):

```
cx=205 cy=997 mT=10 mB=1166      <- IDENTICAL on every single open
```

**`cx`/`cy`/`mT`/`mB` belong to the first-level flyout BAR, not to the
individual clicked button.** This was never suspected before this
measurement — every prior attempt (including both failed ones above)
implicitly assumed `cy` was per-button and tried to recover or reuse it
per-container.

Cross-checking `mB` against the measured native container positions
confirms `mB` IS the game's own native bottom-margin clamp:

```
Build Park/Green Spaces:  native top 729, native h 437  -> 729 + 437 = 1166 = mB  (clamp2 BINDS)
Sports Grounds:            native top 849, native h 290  -> 849 + 290 = 1139 < 1166 (clamp2 does NOT bind)
```

Both native positions fall out of the SAME formula with the SAME shared
`cy=997, mT=10, mB=1166` — confirming they really are one shared anchor,
not three coincidentally-equal buttons.

## The fix: `SubSharedBottom()`

`src/UiSpike.cpp`, beside `SubContainerShiftFromGeo` (~line 1330):

```cpp
inline int32_t SubSharedBottom(int32_t mB, int32_t viewH, float f)
{
    const int32_t full8H_1x = 2 * 25 + 8 * (44 + 5) - 5;   // = 437
    const int32_t hypotheticalNativeT8 = mB - full8H_1x;
    const int32_t cyRef =
        hypotheticalNativeT8 + (full8H_1x >> 1) + 3;
    const int32_t capHs = RoundHalfUp(25.0 * f);
    const int32_t itemHs = RoundHalfUp(44.0 * f);
    const int32_t spacingS = RoundHalfUp(5.0 * f);
    const int32_t full8H_scaled =
        2 * capHs + 8 * (itemHs + spacingS) - spacingS;
    const int32_t modelTop8 =
        SubPlaceTop(full8H_scaled, cyRef, viewH, f);
    return modelTop8 - SubContainerShiftPx() + full8H_scaled;
}
```

Usage in the birth hook (regular sub-flyout only — see below):

```cpp
const int32_t sharedBottom = SubSharedBottom(mB, gLastViewH, gTierF);
const int32_t top = sharedBottom - newH;
dy = top - nativeT;                 // ABSOLUTE -> RELATIVE (GZWinMoveTo moves BY)
gSubRingAutoY = legDY - dy;         // recompute AFTER, so the ring stays pinned
```

**Why this reuses `mB` directly and re-derives a HYPOTHETICAL 8-row
container's native top, instead of measuring a real one:** it needs no
live sibling. Any button's own `mB` (already in scope as a `Place()`
parameter — no recovery, no inversion) tells you exactly where an 8-row
container FROM THAT SAME BUTTON would clamp to, without one ever needing
to exist. For an ACTUAL 8-row container this is mathematically a no-op —
its own native top already equals `mB - full8H_1x` by construction — which
is why it changes nothing for the already-approved Build Park/Green
Spaces case (verified bit-exact: dy=-453, bottom=1150, `_tests/Test-SubFlyoutPlacement.py`).

**Two independent derivations agree.** The predicted Sports Grounds fix
(top 470→570, bottom 1150) matches an estimate written down in
`HANDOFF-2026-08-23.md` HOURS before this measurement existed, from a
completely different (and, per Attempt 3 above, ultimately WRONG for the
general case) per-button reasoning chain. Two different methods landing on
the same number for the one case both could check is strong evidence the
number is right — it does not certify the METHOD; only `SubSharedBottom`'s
byte-exact reproduction of the cnt≥8 case does that.

## Attempt 4 — the ACTUAL root cause (2026-08-23, third pass): SubPlaceTop's own margin was wrong

The `SubSharedBottom()` fix above (Attempt "the fix that shipped") reproduced
the approved Build Park/Green Spaces case byte-exact, but a fresh 1x/2x
click-through census of all seven Civic Tools buttons — Police/Fire/
Education/Hospitals (all cnt<8) versus Landmarks/Rewards/Parks (all
capped at 8 rows for display) — showed the short ones were **still
reported broken**, unchanged from before that fix. `SubBarClampsAt8Rows`
correctly gates on the ONE bar that clamps (Parks, cy=997); every other
bar — including all four broken ones — falls through to the plain
per-button formula, which `SubSharedBottom` never touched. The fix's own
scope was one bar; the defect was universal.

Deriving all seven buttons' predicted screen positions by hand (not
eyeballing) turned up an inconsistent, non-monotonic pattern relative to
"pure native centering on `cy`" — some bars off by 8px, one by 134px, one
going 130px NEGATIVE (off the top of the screen). That inconsistency,
not a clean sign or magnitude, was the tell that something structural was
wrong, not just under-tuned.

**The actual bug:** `SubPlaceTop()`'s bottom margin is
`margB = viewH - marginT`, where `viewH` is `gLastViewH` — **the desktop
resolution** (1600 on a 2400x1600 screen). But `tools/uimap/
SUBFLYOUT-BUILDER.md` §3.1 (disassembly of `sub_7EAEB0`, the real
builder) shows the game computes `cy`/`margB` from the **live button and
3D-view positions**: `margB = viewY - 10`, where `viewY =
this[0x18C]->GetY()` is the 3D view's own Y-extent — not the desktop
height. Measured 2026-08-23: raw `mB = 1166` while `gLastViewH = 1600` —
a 434px gap that is the game's own bottom HUD/toolbar reserving screen
space, not a scaling artifact. `SubPlaceTop`'s internal re-derivation of
`margB` from `viewH` was never the game's real margin; it happened to be
close enough, for ONE content height (874, the 8-row cap), that the
empirical bornshift (`SubContainerShiftPx()`, tuned by eye against
exactly that case) could paper over the gap. For any other content
height the same flat shift does not close the same gap, which is exactly
why Police/Fire/Education/Hospitals stayed broken through two "fixes."

**Ground-truth verification, before writing a line of C++:** queried the
real, disassembled `sub_79AD00` directly under Unicorn (`tools/uimap/emu/
emu_subplace_model.py`'s harness), feeding it fully-f-scaled item metrics
and the RAW measured `mT=10`/`mB=1166` (never re-derived) for all seven
Civic Tools `cy` values. The emulator's output matched a hand-derived
Python model bit-exact in every case — the model was then encoded as
`SubPlaceTopMb()` and used in `_tests/Test-SubFlyoutPlacement.py` before
any DLL change.

**The fix — `SubPlaceTopMb()`, `src/UiSpike.cpp` (beside `SubPlaceTop`):**

```cpp
inline int32_t SubPlaceTopMb(int32_t contentH, int32_t cy, int32_t mT,
    int32_t mB, float f)
{
    const int32_t fE8  = RoundHalfUp(25 * f);
    const int32_t fF4  = RoundHalfUp(53 * f);
    const int32_t f100 = RoundHalfUp(29 * f);
    int32_t top = (fF4 >> 1) - (contentH >> 1) + cy - f100;
    if (top < mT) { top = mT; }
    if (top > mB - contentH) { top = mB - contentH; }
    if (top > cy - f100 - fE8) { top = cy - f100 - fE8; }
    const int32_t floorT = cy + fF4 - contentH + fE8 - f100;
    if (top < floorT) { top = floorT; }
    return top;
}
```

The SAME four clamps as `SubPlaceTop`, but `mT`/`mB` are the raw, LIVE
Place() parameters — already in scope as `SubPlaceDetour`'s own function
arguments, no recovery, no re-derivation, no hardcoded constant. Usage in
the birth hook, replacing the entire `SubSharedBottom`/
`SubBarClampsAt8Rows`/`SubContainerShiftPx` chain for the regular
(non-disaster) path:

```cpp
const int32_t nativeT = win->GetT();
const int32_t top = SubPlaceTopMb(newH, cy, mT, mB, gTierF);
dy = top - nativeT;                 // ABSOLUTE -> RELATIVE
gSubRingAutoY = legDY - dy;
```

`newH` is the bar's OWN real, already-in-scope content height
(`ScaleRound(t+ch,f) - ScaleRound(t,f)`, computed a few lines earlier in
`SubPlaceDetour` from the game's own native `ch`) — never a hypothetical
8-row height, never a per-bar clamp-detection gate.

**Why this fixes BOTH classes of bug with ONE formula, no branching:**
with `margB = mB` used directly, any bar whose own real content is tall
enough that its natural (unclamped) top would push past `mB` clamps
there automatically — giving Landmarks/Rewards/Parks (cy=797/895/997, all
capped at 8 rows) the identical bottom (1166) with **no per-bar gate, no
hypothetical container, no empirical shift constant.** This is the user's
law ("the bottom part of the flyout should be identical in all of these
menus") falling out of the corrected formula for free — not something a
special case has to enforce. Bars whose content never reaches that
margin (Police/Fire/Education/Hospitals, cy=397/497/595/697) simply
center on their own button, landing within 5px of their own `cy` — the
same 5px integer-rounding drift for all four, not the inconsistent
8–134px spread the broken formula produced.

**Confirmed four independent ways** before any deploy: (1) hand
arithmetic; (2) the real disassembled `sub_79AD00` under Unicorn,
bit-exact; (3) at f=1, `SubPlaceTopMb` is algebraically identical to the
old formula for any case that never reaches the margin clamp, and
reproduces three numbers ALREADY on record from a completely different
measurement — Hospitals top=598, Education top=423, Rewards top=674 (see
`_tests/Test-SubFlyoutPlacement.py`'s NAMED_UNCLAMPED_CASES, unchanged
since the original discovery); (4) every cnt>=8 Civic Tools button
independently converges on the same bottom with no shared code path
between them other than the plain formula.

**Known, deliberate, NOT YET visually reconfirmed side effect:** the
Build Park/Green Spaces/Sports Grounds/Plazas family's shared bottom
moves from **1150 (the old, empirically-tuned value) to 1166** (the
value the corrected formula derives from the measured `mB` with zero
tuning) — a 16px difference, about 1% of a 1600px-tall screen. This is
flagged, not hidden: 1150 was never proven exactly correct, only
"close enough to look right" against one eyeballed case; 1166 is
derived, not tuned, and satisfies the same "identical bottom" law. This
needs the user's own eyes-on confirmation before being treated as
correct, per the standing rule that a live/visual claim is never
resolved solo.

**What this retires, and what it does not touch:** `SubSharedBottom`,
`SubBarClampsAt8Rows`, and the `SubContainerShiftPx()` bornshift are no
longer called from the regular sub-flyout birth path. They are left
defined (dead code, not deleted) so a fallback costs a one-line revert,
not a re-derivation, until this fix is live-verified.

**CORRECTION (adversarial review, 2026-08-23, same session as the fix):**
the paragraph that used to be here claimed "the disaster twin is
untouched — it still uses the original recovered-cy chain, unchanged."
**That was never true**, and saying so was itself a bug this fix
inherited rather than introduced. Control-flow analysis of
`SubPlaceDetour` proves the `else if (isDisaster)` branch containing that
chain is UNREACHABLE: the disaster twin is fully docked (via the GODDOCK
block) and unconditionally `return`s tens of lines earlier in the same
function, so `isDisaster` is always `false` by the time execution reaches
the dock section this fix edited. That dead branch has never run, on any
build back to at least v2.39.0 — this is not new information about the
fix, it is a correction to something this project has been saying wrong
for a while. **The disaster twin's actual, live docking logic (GODDOCK)
was not examined or changed by this fix and is out of scope**, same as
before — just for a different, now-correct reason.

**CONFIRMED, NOT FIXED (same review) — the sweep-time mirror now
genuinely disagrees with birth, and feeds a real (if already-dormant)
interactive control.** A second, independent `SubPlaceTop` call inside
the periodic sweep (search `SubPlaceTop(sub->GetH()` in `UiSpike.cpp`)
still uses the OLD viewH-margin formula plus `SubContainerShiftFromGeo` —
neither retired by this fix. For any cnt>=8 bar (Landmarks/Rewards/Parks)
birth now lands at 292 while the sweep's own `tgtT` sits near 276-ish, so
the sweep's `atNative`/`atTarget` candidate-match (`if (!atNative &&
!atTarget) continue;`) fails for every candidate, exactly as it already
did before this fix — that failure is what `SUBGEO BTN` count staying 0
for the whole instrumented session was recording. The consequence is not
cosmetic: `gSubArrowAbs[]` (the back-arrow click zone) and
`gSubBtnCX/CY` (the forward-click target) are written ONLY inside that
match's success path, so they never refresh for any sub-flyout opened
under `SubBornDock=1` (the shipping default) — the back-arrow scroll
control and click-forwarding on the sub-flyout have been silently inert
this whole time, not just after this fix. Verified safe in the sense that
matters most: the consumers gate on a `-1` sentinel
(`gSubBtnCX >= 0`, reset to `-1` on every menu close) rather than trusting
a possibly-stale rect blindly, so the failure mode is "the feature does
nothing," not "a click somewhere else on screen gets misattributed to a
stale arrow position." **This is a real, separate, pre-existing defect,
now confirmed rather than merely suspected — it deserves its own fix
(mirror `SubPlaceTopMb` into the sweep AND retire
`SubContainerShiftFromGeo` there, so birth and sweep agree again), and
should not be assumed fixed by anything in this document.**

## What is still open (this is what "more menus like that" refers to)

**CORRECTED, 2026-08-23 (adversarial review):** this section used to
claim "the disaster-twin flyout still uses the OLD 'recovered cy'
technique, unchanged, including the tautological self-check." That is
false, and always has been — see "What this retires" above for the
control-flow proof. The disaster twin never reaches that code at all; it
is docked entirely by the GODDOCK block and returns before the recovered-
cy branch is reachable. The self-check really is a tautology (that part
was correct), but calling out a tautological self-check inside dead code
as the twin's "live path" compounded one inaccuracy with another.

**The disaster-twin flyout's REAL docking logic (GODDOCK,
`src/UiSpike.cpp`, inside the `if (isDisaster) {...}` block inside
`SubPlaceDetour`) has not been examined for this defect class at all.**
It was deliberately left alone this session: this session's `SUBPLACE`
capture only recorded `kind=SUB` events — nobody opened Create Disasters
while the diagnostic build was live, so there is no measured `mT`/`mB`/`cy`
for that twin, and porting a fix onto unmeasured code is the exact
mistake Attempt 2 already made once. Whether Create Disasters even HAS
an analogous short-strip defect is unknown; find out by measuring, not by
assuming the mechanism described below still applies to it.

**To extend this fix to Create Disasters (or any other menu family that
should share a bottom, dock line, or other structural edge):**

1. Confirm the diagnostic-only `SUBPLACE` log line (see
   `src/UiSpike.cpp`, `SubPlaceDetour`, right after the id/return-address
   identification) still fires for that family — it is gated on `isDisaster
   || (!isDisaster && win->GetID()==0x8A6E61E0)`, so a genuinely different
   window class needs its own log line, not a reused one.
2. Open every affected menu in ONE session; read the log; confirm the raw
   `cx/cy/mT/mB` tuple really is shared (do not assume it — SUB's tuple
   being shared was a discovery, not a given).
3. Cross-check the shared `mB` against that family's own measured native
   `(nativeT, ch)` pairs the SAME way this file does above — if
   `nativeT + ch != mB` for whichever container is currently "approved,"
   the anchor relationship is different and `SubSharedBottom` cannot be
   reused as-is; re-derive the analogous formula for that family's own
   constants (cap height, item height, spacing, row cap) instead of
   assuming 25/44/5/8 apply.
4. Prove the new formula against the OLD family's approved case in
   `_tests/Test-SubFlyoutPlacement.py` (or a sibling gate) BEFORE building
   — this is what caught Attempt 2 and ruled out Attempt 3 for the SUB
   case, and it is the reusable part of this whole exercise, not just the
   numbers.

**The general, reusable method — the actual "referencable" part of this
work — is not the constants (25/44/5/8/1166), which are specific to this
one window class. It is the ORDER OF OPERATIONS:**

1. Find the raw, game-supplied placement parameters actually in scope at
   the hook site — log them RAW, unmodified, before any of the mod's own
   math touches them.
2. Check whether they are IDENTICAL across the cases that currently behave
   differently. If they are, the differing behavior comes entirely from
   something else (here: content height) feeding a SHARED formula, and any
   fix must operate on that shared formula, not on a per-case reconstruction.
3. Reject any candidate formula, even one that "sounds right," that
   produces a DIFFERENT target per case when the law demands a SHARED one
   — Attempt 3 was rejected this way, on paper, before it cost a build.
4. Prove the winning formula reproduces every already-approved case
   byte-exact in an offline model before touching the DLL.

## Related laws

- `project-sc4-flyout-never-shift-strip-independently.md` — the strip
  child window is never the lever; the container/ring is.
- `project-sc4-flyout-never-prescroll.md` — scroll state is never the fix
  for a positioning symptom either (**NOTE, 2026-08-23 review**: this
  file's own "what actually fixes this class" section still prescribes
  `StripShiftRows`, which was retired dead in v4.0.30 — needs its own
  correction pass, tracked separately from this fix).
- `reference-sc4-subflyout-ring-law.md` — the ring/strip/bar as one welded
  shape; `gSubRingAutoY` is the ring's own, independent lever.
- `SUBFLYOUT-BUILDER.md` — builder constants and the `Place()` formula this
  law's `mT`/`mB`/`cy` parameters come from.
