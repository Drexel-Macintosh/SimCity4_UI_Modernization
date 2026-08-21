r"""GATE: a scaled flyout strip must show the SAME number of rows as stock.

THE DEFECT (user, 1.5x): the last item in every flyout is invisible until you
scroll, and scrolling to the end leaves empty space.

THE DECISION, read out of the strip's own Plot at 0x0079AA70 and recorded at
src\UiSpike.cpp:4927:

    visibleRows = (stripWinH + [0xFC]) / ([0xF8] + [0xFC])       # integer /

Stock metrics are SetItemMetrics(44, 44, 5) -> [0xF8]=44, [0xFC]=5, and every
measured strip window height is EXACTLY 49n - 5 (the live 2x oracle in
emu_subflyout.py: 284/382/578 at 2x = 142/191/289 at 1x = 49*3-5 / 49*4-5 /
49*6-5). So at stock:

    (49n - 5 + 5) / 49 = n     exact, remainder 0, for every n

THERE IS NO SPARE PIXEL ANYWHERE IN THIS CONTROL. The division is exact by
construction, which means ANY upward drift in the denominator costs a whole row.

We scale the three metrics with RoundHalfUp (UiSpike.cpp:2964-2966, 4977-4979,
5023-5028):

    44 * 1.5 = 66.0  exact
    44 * 1.5 = 66.0  exact
     5 * 1.5 =  7.5  <-- THE ONLY .5 IN THE SYSTEM, and RoundHalfUp sends it UP

Rounding 7.5 up makes the denominator 74 where the geometry only supports 73,
and the floor division loses exactly one row. At 2x and 3x every product is an
integer, so the defect is STRUCTURALLY IMPOSSIBLE there - the same shape as
#142 (font sizes) and #143 (cell divides).

THIS GATE ASSERTS:
  1. FLOOR on the step-extra reproduces stock's row count at every tier and
     every strip length.
  2. NEGATIVE CONTROL: RoundHalfUp (what ships today) must FAIL at 1.5x. A gate
     that cannot fail proves nothing.
  3. Integer tiers are byte-identical under both rules - so this cannot regress
     2x or 3x, which are user-confirmed.

Offline. No game, no exe. Exit 0 = pass.
"""
import math
import sys

ITEM = 44          # [0xF8] - gStripBase8
STEP = 5           # [0xFC] - gStripBaseC
FACTORS = (1.5, 2.0, 3.0)
NROWS = range(2, 13)          # real menus run about 3..9; test wider


# ONE SOURCE FOR THE SCALING RULES (scale_rules.py). This file used to
# carry its own copy; #162 changed ScaleRound in the DLL and every private
# copy in this folder had to be found by hand. `scale_rules.py --drift`
# hunts any that come back.
from scale_rules import round_half_up          # noqa: E402


def floor_(v):
    return int(math.floor(v))


def strip_h_1x(n):
    """Every measured strip window height is exactly 49n - 5."""
    return (ITEM + STEP) * n - STEP


def visible_rows(win_h, item, step):
    return (win_h + step) // (item + step)


fail = []
rows_out = []

for f in FACTORS:
    for n in NROWS:
        h1 = strip_h_1x(n)
        stock = visible_rows(h1, ITEM, STEP)
        if stock != n:
            fail.append("premise broken: stock n=%d gives %d" % (n, stock))

        win = round_half_up(h1 * f)          # the window is scaled round-half-up
        item_s = round_half_up(ITEM * f)     # exact at every factor here

        cur = visible_rows(win, item_s, round_half_up(STEP * f))
        fix = visible_rows(win, item_s, floor_(STEP * f))

        if fix != n:
            fail.append("FIX WRONG: f=%g n=%d -> %d rows, want %d" % (f, n, fix, n))
        if float(f).is_integer() and cur != fix:
            fail.append("INTEGER TIER MOVED: f=%g n=%d cur=%d fix=%d"
                        % (f, n, cur, fix))
        rows_out.append((f, n, win, item_s, round_half_up(STEP * f),
                         floor_(STEP * f), stock, cur, fix))

# NEGATIVE CONTROL: today's rule must actually be broken at 1.5x, or this gate
# is testing nothing.
broken_15 = [r for r in rows_out if r[0] == 1.5 and r[7] != r[6]]
if not broken_15:
    fail.append("NEGATIVE CONTROL BROKEN: RoundHalfUp already matches stock at "
                "1.5x, so there was no defect to fix and this gate is a no-op.")

print("strip visible-row count: stock vs shipped vs fix")
print("=" * 86)
print("%-5s %-4s %7s %6s %7s %7s %7s %7s %7s   %s"
      % ("f", "n", "winH", "item", "stepRHU", "stepFL", "stock", "SHIPPED", "FIX", ""))
print("-" * 86)
for f, n, win, item_s, s_rhu, s_fl, stock, cur, fix in rows_out:
    note = ""
    if cur != stock:
        note = "<== SHIPPED LOSES %d ROW(S)" % (stock - cur)
    print("%-5g %-4d %7d %6d %7d %7d %7d %7d %7d   %s"
          % (f, n, win, item_s, s_rhu, s_fl, stock, cur, fix, note))

print()
print("negative control: shipped rule is wrong on %d of %d cases at 1.5x"
      % (len(broken_15), len([r for r in rows_out if r[0] == 1.5])))
print()
if fail:
    print("FAIL (%d)" % len(fail))
    for m in dict.fromkeys(fail):
        print("   " + m)
    sys.exit(1)
print("PASS - FLOOR on the step-extra restores stock's row count at 1.5x and "
      "leaves 2x and 3x bit-identical.")
sys.exit(0)
