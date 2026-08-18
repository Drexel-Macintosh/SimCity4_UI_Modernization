r"""GATE: the dock minimap always lands on a LEGAL blit size, at every tier.

WHY THIS EXISTS
---------------
`cSC4WinMiniMap` renders through a one-shot surface created at `blitSize`, and
the bake chain can only ever produce `terrainDim << k`. Window and surface must
agree; when they do not you get the #109 family - at best a stride tear, at
worst a heap overrun.

`UiSpike::SnapMiniMapToBake` picks that size. Until 2026-08-06 its search was a
single ASCENDING loop starting at `terrainDim`:

    for (int32_t s = terrainDim; s <= want; s <<= 1) { snap = s; }

which cannot reach a DIVISOR. When the slot the layout reserved is smaller than
`terrainDim`, the loop body never runs, `snap` stays 0, and the caller returns
having corrected nothing - silently.

That is 1.5x's problem and it is structural. The dock recess is 64 design px,
so the slot is 64*f:

    f=2.0 -> 128   terrainDim 64 and 128 both fit
    f=3.0 -> 192   terrainDim 64 -> 128 fits
    f=1.5 ->  96   terrainDim 64 fits (snapping DOWN - no growth is possible,
                   which is just what 1 < 1.5 < 2 means against a power-of-two
                   law), but terrainDim 128 / 256 never entered the loop.

So on any city larger than small, 1.5x left the dock minimap uncorrected.

WHAT THIS GATE ASSERTS
----------------------
  1. NEW picks a legal size (terrainDim << k, k any integer) at every tier and
     every city size, never exceeding the slot or the bake ceiling.
  2. NEGATIVE CONTROL - OLD must FAIL at 1.5x for medium and large cities.
     A gate that cannot fail proves nothing, so this asserts the bug is real
     and that this file would have caught it.
  3. SAFETY PROPERTY - wherever OLD produced a non-zero answer, NEW produces
     the SAME answer. The new branch only runs where the old code did nothing,
     so it cannot regress a tier that already worked.
  4. The dock-recess neutralize gate agrees with the snap result: the fake map
     is stripped exactly when the real map cannot cover the recess.

Offline. No game, no exe read. Exit 0 = pass.
"""
import sys

TERRAIN_DIMS = (64, 128, 256)      # small / medium / large city
FACTORS = (1.5, 2.0, 3.0)
RECESS_DESIGN = 64                 # dock minimap recess, MEASURED (18,71) 64x64
X8 = True                          # #121 extends the bake ceiling to zoom -3


# ONE SOURCE FOR THE SCALING RULES (scale_rules.py). This file used to
# carry its own copy; #162 changed ScaleRound in the DLL and every private
# copy in this folder had to be found by hand. `scale_rules.py --drift`
# hunts any that come back.
from scale_rules import scale_round as scale_len  # noqa: E402


def snap_old(terrain_dim, want):
    """The pre-2026-08-06 ascending-only search."""
    snap = 0
    s = terrain_dim
    while s <= want:
        snap = s
        s <<= 1
    return snap


def snap_new(terrain_dim, want, min_snap=32):
    """Multiples AND divisors - the full legal set."""
    if terrain_dim <= want:
        return snap_old(terrain_dim, want)
    s = terrain_dim
    while s >= min_snap:
        if s <= want:
            return s
        s >>= 1
    return 0


def is_pow2(n):
    return n > 0 and (n & (n - 1)) == 0


def legal(size, terrain_dim):
    """Is `size` of the form terrain_dim << k for some integer k?"""
    if size <= 0:
        return False
    a, b = max(size, terrain_dim), min(size, terrain_dim)
    if b <= 0 or a % b:
        return False
    return is_pow2(a // b)


fail = []
rows = []

for f in FACTORS:
    slot = scale_len(RECESS_DESIGN, f)
    for td in TERRAIN_DIMS:
        ceiling = td * (8 if X8 else 4)
        want = min(slot, ceiling)
        old = snap_old(td, want)
        new = snap_new(td, want)

        # 1. NEW is always legal and fits.
        if not legal(new, td):
            fail.append("f=%g td=%d: NEW picked %d, not a power-of-two "
                        "multiple/divisor of terrainDim" % (f, td, new))
        if new > want:
            fail.append("f=%g td=%d: NEW picked %d > slot/ceiling %d"
                        % (f, td, new, want))

        # 3. SAFETY - agree wherever OLD answered at all.
        if old and new != old:
            fail.append("f=%g td=%d: NEW changed a case OLD already handled "
                        "(%d -> %d). The new branch must only run where OLD "
                        "did nothing." % (f, td, old, new))

        rows.append((f, slot, td, want, old, new))

# 2. NEGATIVE CONTROL. If these ever start passing under OLD, the premise of
#    this whole fix is gone and the gate is lying.
control = []
for td in (128, 256):
    slot = scale_len(RECESS_DESIGN, 1.5)
    want = min(slot, td * (8 if X8 else 4))
    if snap_old(td, want) != 0:
        fail.append("NEGATIVE CONTROL BROKEN: OLD found %d for terrainDim=%d "
                    "at 1.5x; it was supposed to find nothing."
                    % (snap_old(td, want), td))
    else:
        control.append(td)
    if snap_new(td, want) <= 0:
        fail.append("f=1.5 td=%d: NEW found nothing either - the fix does not "
                    "fix the case it was written for." % td)

print("dock minimap blit-size search")
print("=" * 74)
print("%-6s %6s %6s %6s %8s %8s   %s"
      % ("factor", "slot", "tDim", "want", "OLD", "NEW", "verdict"))
print("-" * 74)
for f, slot, td, want, old, new in rows:
    if old == 0 and new > 0:
        note = "<== WAS UNCORRECTED, now fixed"
    elif old == new and old != 0:
        note = "unchanged"
    else:
        note = ""
    print("%-6g %6d %6d %6d %8s %8s   %s"
          % (f, slot, td, want, old if old else "(none)", new, note))

print()
print("negative control: OLD found nothing at 1.5x for terrainDim %s - "
      "confirmed" % (", ".join(str(t) for t in control) if control else "NONE"))

# 4. The neutralize gate must agree with reality.
print()
print("dock recess fake-map neutralize")
print("=" * 74)
print("%-6s %6s %-14s %s" % ("factor", "recess", "pow2?", "action"))
print("-" * 74)
SHIPPED = {1.5: "strip", 2.0: "skip", 3.0: "strip"}
for f in FACTORS:
    recess = scale_len(RECESS_DESIGN, f)
    fillable = is_pow2(recess)
    action = "skip" if fillable else "strip"
    if action != SHIPPED[f]:
        fail.append("f=%g: neutralize gate says %s, shipped behaviour is %s"
                    % (f, action, SHIPPED[f]))
    # Cross-check against the snap: if the real map cannot equal the recess for
    # EVERY city size, something must strip the remainder.
    covers = all(snap_new(td, min(recess, td * (8 if X8 else 4))) == recess
                 for td in TERRAIN_DIMS)
    if covers != fillable:
        fail.append("f=%g: pow2 test (%s) disagrees with the snap result (%s)"
                    % (f, fillable, covers))
    print("%-6g %6d %-14s %s" % (f, recess, "yes" if fillable else "no", action))

print()
if fail:
    print("FAIL (%d)" % len(fail))
    for m in fail:
        print("   " + m)
    sys.exit(1)
print("PASS - every tier lands on a legal blit size; 2x and 3x unchanged; "
      "the 1.5x gap is real and closed.")
sys.exit(0)
