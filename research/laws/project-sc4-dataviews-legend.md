# Data Views Legend: Scale the Origin, Not the Step

The Data Views legend is re-laid from scratch every time a data view is
selected. The routine that does it is `sub_007A04F0` (`__thiscall`, `ret 4`,
single argument = the data-view id). It is provably the only choke point: the
legend's window ids `0x8A909E00` and `0x8A909E10` appear at exactly four
addresses in the entire 7.87 MB image, and all four are inside that routine.
Nothing else in the executable positions those windows.

## The cure

Scale the routine's four origin constants. That is eight patch sites, not four:
each origin appears **twice** — once in the write that sets the window's left or
top, and once in the `add`/`lea` that computes right or bottom from `GetW()` /
`GetH()`. Patching only the first copy of each produces windows whose position
scales while their extent does not.

## The law: scale the origin, never the step

The row advance is computed, not stored:

```
edi += 18 * ceil(h / 18)     // h = the *measured* height of the row's text
```

Because `h` is measured at layout time from already-scaled text, the pitch
self-scales — it reads 36 at 2x with no patch at all. Two consequences follow,
and both are fatal to the obvious fixes:

1. **Patching the pitch double-scales it.** The step is already correct before
   any patch touches it.
2. **The pitch is not uniform, so a correction table cannot express it.** A
   label that wraps to two lines is given a 72px slot at 2x, not 36px. Any
   post-hoc correction that writes rows from a uniform table flattens that
   double-height slot. Measured case: a nine-row view whose engine layout was
   `24, 60, 96, 132, 168, 240, 276, 312, 348` had eight of its windows dragged
   up 36px by a uniform pin table — a *persistent* wrong layout, not a
   one-frame artifact.

Scaling the origins fixes both, because the engine's own per-row deltas are
left intact and simply start from the right place.

## A reactive pin can be wrong, not merely late

The earlier approach re-positioned the legend reactively after each re-lay, and
its instrumentation burst — a run of `DVPIN` lines followed by silence — had
been written down as the *pass* criterion for the feature. That burst was the
defect itself: it was the uniform table doing the flattening described above.

**An acceptance test that never inspects the transient frame cannot see a
transient defect.** If a feature's correctness lives in the frames between two
steady states, the check has to look there, or it will certify the bug.

## Verification and instrumentation

- Expected result: all 8 sites patched, `DVPIN` count 0 against a baseline of
  198, and both non-uniform (wrapped-label) legends preserved with their
  double-height rows intact.
- `DVLEG born=/rows=/chips=/rowY=[...]` is the positive control for the
  "zero `DVPIN` lines" reading. Zero lines alone proves nothing — it is equally
  consistent with the instrument never running — so the `DVLEG` line must be
  present and must report the correct `rowY` sequence for the null to count as
  evidence.
- Escape hatch: `[UiSpike] DataViewLegendPatch=0`, then restart.

Engine reference: `SC4-UI-ENGINE.md` §4.7, row 3 (the origin constants and the
re-lay note).
