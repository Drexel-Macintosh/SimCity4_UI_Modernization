r"""Test-SubBirthOwnsDock.py - the sub-flyout sweep must not re-decide what birth decided.

THE DEFECT (2026-09-25, found while testing the memo33/submenus-dll PR).
Utilities -> Power -> the 5-item memo.submenus power submenu, 3x tier: the strip
sits right, but the ring + back arrow sometimes jump one row DOWN, to the Water
button. Every SC4UIScale log of it (either submenus DLL) shows the first sweep
tick with the ring at the birth pin (AUTO 244, RINGa 567 = Power) and every later
tick at AUTO 392 / RINGa 715 = Water; the player sees it only when the container
repaints after that tick - hence "intermittent".

THE CAUSE. Birth (SubPlaceDetour) and the sweep's candidate loop decide the same
three things - WHICH button, WHERE the container goes, the ring PIN - with two
formulas that disagree (SubPlaceTopMb vs SubPlaceTop minus the SUBSHIFT). For the
5-item strip the sweep's +-3 px match lands on WATER and rewrites the pin; for 6+
items it matches nothing (dead back-arrow zone). research/laws/
project-sc4-flyout-bottom-anchor.md had it as "CONFIRMED, NOT FIXED".

THE FIX. "Birth owns the dock": birth records its anchor (the game's Place() cy),
top and pin; the sweep claims a born container only by that anchor, uses that top,
keeps that pin. The record is cleared on EVERY sub-builder Place(), before any
early return (review 2026-09-25: a late clear let a live SubBornScale=0 leak one
open's anchor into a recycled container of the same height).

SCOPE (law 42 - what this can and cannot see). It is an OUTCOME model of the
DLL's decisions in the same integer arithmetic (src/UiSpike.cpp): it simulates
Place() + sweep events and judges what the player gets - where the ring is drawn,
which button the back-arrow forwards to, where the container rests. It does NOT
read or run the DLL; the in-game SUBOWN / SUBGEO2 log lines are the check on the
real binary. Its teeth are the MUTANTS: four deliberately broken variants of the
decision logic (the old sweep, no anchor filter, a frame sign error, the late
clear) must each FAIL here, or this gate proves nothing (law 26).

    python _tests/Test-SubBirthOwnsDock.py        exit 0 = all expectations hold
"""
import math
import sys

FAILS = []


def expect(cond, what):
    if not cond:
        FAILS.append(what)
        print("  FAIL  " + what)
    return cond


def rhu(v):                                       # RoundHalfUp
    return int(math.floor(v + 0.5))


# ---- the DLL's arithmetic --------------------------------------------------
K_PLACE_BIAS = 29                                 # kSubPlaceBias
K_ARM_TARGET_BOTTOM = 1.50                        # kSubArmTargetBottom
MAX_ITEMS = 8                                     # the builder's row cap


def content_h1(n):                                # the game's 1x item-column height
    return max(49 * n - 5, 53) + 50


def ring_blt_y(n):                                # latched from 1x: (a>>1)-(b>>1)
    return (content_h1(n) >> 1) - (53 >> 1)


def new_h(n, f):                                  # born height, edge-rounded (SUBBORN2 129x290 -> 387x870)
    return rhu(content_h1(n) * f)


def native_dx(btn_w):                             # SubNativeDXFor: game seats the container 27 left of centre
    return btn_w // 2 - 27


def dock_dx(f, btn_w):                            # SubDockDXEff()
    return rhu(21 * f) - rhu(25 * f) - native_dx(btn_w)


def dock_dy(f):                                   # SubDockDYEff()
    return K_PLACE_BIAS - rhu(26.5 * f)


def ring_dy(f):                                   # SubRingDYEff() - the derived Y nudge
    return rhu(15 * f) - rhu(37 * f) // 2 + rhu(26.5 * f) - rhu(26 * f)


def place_top(content_h, cy, view_h, f):          # SubPlaceTop (the sweep's OLD formula)
    fe8, ff4, f100 = rhu(25 * f), rhu(53 * f), rhu(29 * f)
    marg_t = rhu(10 * f)
    marg_b = view_h - marg_t
    top = (ff4 >> 1) - (content_h >> 1) + cy - f100
    if top < marg_t:
        top = marg_t
    if view_h > 0 and top > marg_b - content_h:
        top = marg_b - content_h
    if top > cy - f100 - fe8:
        top = cy - f100 - fe8
    floor_t = cy + ff4 - content_h + fe8 - f100
    if top < floor_t:
        top = floor_t
    return top


def place_top_mb(content_h, cy, m_t, m_b, f):     # SubPlaceTopMb; at f=1 it IS the game's Place()
    fe8, ff4, f100 = rhu(25 * f), rhu(53 * f), rhu(29 * f)
    top = (ff4 >> 1) - (content_h >> 1) + cy - f100
    if top < m_t:
        top = m_t
    if top > m_b - content_h:
        top = m_b - content_h
    if top > cy - f100 - fe8:
        top = cy - f100 - fe8
    floor_t = cy + ff4 - content_h + fe8 - f100
    if top < floor_t:
        top = floor_t
    return top


def shift_from_geo(ring_y, auto_y0, cnt, f):      # SubContainerShiftFromGeo
    if f <= 1.0 or cnt < 1:
        return 0
    ring_hs, cap_hs = rhu(53 * f), rhu(25 * f)
    s_item, s_sp = rhu(44 * f), rhu(5 * f)
    pitch = s_item + s_sp
    vis = cnt if cnt < 8 else 8
    strip_h = pitch * cnt - s_sp
    content_h = (strip_h if strip_h > ring_hs else ring_hs) + 2 * cap_hs
    strip_top = (content_h - strip_h) // 2
    natural = (ring_y + auto_y0 + ring_hs // 2 - strip_top) / pitch
    needed = (vis - K_ARM_TARGET_BOTTOM) - natural
    return 0 if needed <= 0 else rhu(needed * pitch)


# ---- a tiny simulation of the DLL's state and events ------------------------
class Container:                                  # the shared 0x8A6E61E0 window (parent frame coords)
    def __init__(self):
        self.l = self.t = self.h = self.n = 0


class Dll:
    """SubPlaceDetour + the sweep's candidate loop. `mutant` swaps in one broken variant."""

    def __init__(self, f, m_t, m_b, view_h, parent_off=0, mutant=None):
        self.f, self.m_t, self.m_b, self.view_h = f, m_t, m_b, view_h
        self.parent_off = parent_off              # the container's parent's absolute top
        self.mutant = mutant
        self.born_scale_on = True
        self.sub_math = True
        self.record = None                        # (win, cy, top_rel, auto_y, h)
        self.auto_y = 0                           # gSubRingAutoY
        self.btn_ctr = None                       # gSubBtnCX/CY (the back-arrow forward target)

    def place(self, win, n, spawn, column):
        """The builder lays the container out at 1x around the spawn button, then our detour runs."""
        f = self.f
        bl, bt, bw, bh = spawn
        cy = bt + bh // 2 - self.parent_off       # Place() works in the PARENT frame
        win.n = n
        win.h = content_h1(n)
        win.t = place_top_mb(content_h1(n), cy, self.m_t, self.m_b, 1.0)   # the game's own 1x Place
        win.l = bl + native_dx(bw)
        if self.mutant != "late_clear":
            self.record = None                    # THE FIX: cleared before any early return
        if not self.born_scale_on or f <= 1.01:
            win.h = new_h(n, f)                   # the sweep's ScaleSubtree gives it the same height later
            return
        if self.mutant == "late_clear":
            self.record = None                    # the reviewed defect: cleared only past the early return
        win.h = new_h(n, f)
        native_t = win.t
        leg_dy = dock_dy(f)
        self.auto_y = 0
        if self.sub_math:
            top = place_top_mb(win.h, cy, self.m_t, self.m_b, f)
            dy = top - native_t
            self.auto_y = leg_dy - dy
            self.record = (win, cy, top, self.auto_y, win.h)
        else:
            dy = leg_dy
        win.l += dock_dx(f, bw)
        win.t += dy

    def sweep(self, win, column):
        """One sweep tick of the candidate loop (column in the game's enumeration order)."""
        f = self.f
        sl = win.l
        st = win.t + self.parent_off
        born = (self.mutant != "old_sweep" and self.sub_math and self.record is not None
                and self.record[0] is win and self.record[4] == win.h)
        parent_abs_t = st - win.t                 # st - sub->GetT()
        if born:
            cy_abs = self.record[1] + (-parent_abs_t if self.mutant == "sign" else parent_abs_t)
            top_abs = self.record[2] + parent_abs_t
        ry = ring_blt_y(win.n)
        for bl, bt, bw, bh in column:
            bcy = bt + bh // 2
            if born and self.mutant != "no_anchor" and abs(bcy - cy_abs) > 2:
                continue
            nat_l = bl + native_dx(bw)
            nat_t = bt + bh // 2 - ry - K_PLACE_BIAS
            leg_l, leg_t = nat_l + dock_dx(f, bw), nat_t + dock_dy(f)
            tgt_l = leg_l
            if born:
                tgt_t = top_abs
            else:
                tgt_t = place_top(win.h, bcy, self.view_h, f) if self.sub_math else leg_t
                if f > 1.0:
                    s = shift_from_geo(ry, leg_t - tgt_t, win.n, f)
                    if s > 0:
                        tgt_t -= s
            at_nat = abs(sl - nat_l) <= 3 and abs(st - nat_t) <= 3
            at_tgt = abs(sl - tgt_l) <= 3 and abs(st - tgt_t) <= 3
            if not at_nat and not at_tgt:
                continue
            self.auto_y = self.record[3] if born else ((leg_t - tgt_t) if self.sub_math else 0)
            self.btn_ctr = (bl + bw // 2, bcy)
            if at_nat:
                win.l, win.t = tgt_l, tgt_t - self.parent_off
            return
        # no claim: the pin stays whatever it was, the arrow zone is not refreshed


def outcome(dll, win, spawn):
    """What the player gets, judged against the legacy pin on the SPAWN button."""
    f = dll.f
    bl, bt, bw, bh = spawn
    ring = win.t + dll.parent_off + ring_blt_y(win.n) + dll.auto_y + ring_dy(f)
    native_t_abs = place_top_mb(content_h1(win.n), bt + bh // 2 - dll.parent_off,
                                dll.m_t, dll.m_b, 1.0) + dll.parent_off
    want_ring = native_t_abs + dock_dy(f) + ring_blt_y(win.n) + ring_dy(f)   # the player-confirmed pin
    return dict(ring=ring, want_ring=want_ring, fwd=dll.btn_ctr, want_fwd=(bl + bw // 2, bt + bh // 2))


def open_and_sweep(dll, win, n, spawn, column, ticks=3):
    dll.btn_ctr = None
    dll.place(win, n, spawn, column)
    for _ in range(ticks):
        dll.sweep(win, column)
    return outcome(dll, win, spawn)


def good(o):
    return o["ring"] == o["want_ring"] and o["fwd"] == o["want_fwd"]


# ---- 1. the LIVE records (SC4UIScale.session3-release.log, 3x, 3840x2160) ----
print("1  the diagnosis: measured births reproduced, the old sweep's logged claims reproduced")
F, MT, MB, VIEW = 3.0, 10, 1514, 2160
BW, BH = rhu(47 * F), rhu(37 * F)
UTIL = [(237, 900, BW, BH), (237, 750, BW, BH), (237, 600, BW, BH)]   # SUBCAND order: bottom-up
BY_CY = {655: UTIL[2], 805: UTIL[1], 955: UTIL[0]}
LIVE = [  # (n, cy, newH, nativeT, top, dy) from SUBANCHOR, and the old sweep's claim from SUBGEO/SUBCAND
    (3, 655, 576, 556, 359, -197, 600),
    (5, 655, 870, 507, 212, -295, 750),     # the jump: Water claims the Power strip
    (1, 655, 309, 601, 493, -108, 600),
    (6, 805, 1017, 633, 289, -344, None),   # no claim: dead back-arrow zone
    (1, 805, 309, 751, 643, -108, 750),
    (3, 955, 576, 856, 659, -197, 900),
    (2, 805, 429, 731, 583, -148, 750),
]
for n, cy, h, nat, top, dy, logged_bt in LIVE:
    spawn = BY_CY[cy]
    for mutant in ("old_sweep", None):
        dll, win = Dll(F, MT, MB, VIEW, mutant=mutant), Container()
        dll.place(win, n, spawn, UTIL)
        got = (win.h, win.t - dy, win.t, dy)
        expect(got == (h, nat, top, dy), "birth n=%d cy=%d reproduces SUBANCHOR %s (got %s)" % (
            n, cy, (h, nat, top, dy), got))
        dll.sweep(win, UTIL)
        claim_bt = None if dll.btn_ctr is None else dll.btn_ctr[1] - BH // 2
        if mutant == "old_sweep":
            expect(claim_bt == logged_bt, "old sweep n=%d cy=%d claims bt=%s as logged (model: %s)" % (
                n, cy, logged_bt, claim_bt))
        else:
            o = outcome(dll, win, spawn)
            expect(good(o), "fix n=%d cy=%d: ring %d (want %d), forward %s (want %s)" % (
                n, cy, o["ring"], o["want_ring"], o["fwd"], o["want_fwd"]))
dll, win = Dll(F, MT, MB, VIEW, mutant="old_sweep"), Container()
o = open_and_sweep(dll, win, 5, UTIL[2], UTIL)
expect(o["ring"] == 715 and o["want_ring"] == 567 and dll.auto_y == 392,
       "POSITIVE CONTROL: the old sweep draws the 5-item ring at 715 (Water), the pin is 567")

# ---- 2. the grid: tiers x counts x spawn buttons x margins, fix and mutants ----
print("2  grid: the fix gives the player-confirmed ring and forward target; the mutants do not")
GRID = []
for f, view, m_bs in ((1.5, 1200, (880,)), (2.0, 1600, (1166,)), (3.0, 2160, (1514,))):
    bw, bh, pitch = rhu(47 * f), rhu(37 * f), rhu(50 * f)
    for top0 in (rhu(150 * f), rhu(300 * f)):
        column = [(rhu(79 * f), top0 + i * pitch, bw, bh) for i in range(7)]
        order = list(reversed(column))                    # the game enumerates bottom-up
        for m_b in m_bs:
            for n in range(1, MAX_ITEMS + 1):
                for spawn in column:
                    if spawn[1] + spawn[3] // 2 < m_b:
                        GRID.append((f, view, m_b, n, spawn, order))
bad = {None: 0, "old_sweep": 0, "no_anchor": 0}
for f, view, m_b, n, spawn, order in GRID:
    for mutant in bad:
        dll, win = Dll(f, 10, m_b, view, mutant=mutant), Container()
        if not good(open_and_sweep(dll, win, n, spawn, order)):
            bad[mutant] += 1
print("   %d cases.  fix: %d wrong.  old sweep: %d wrong.  no anchor filter: %d wrong." % (
    len(GRID), bad[None], bad["old_sweep"], bad["no_anchor"]))
expect(bad[None] == 0, "the fix is right in every grid case")
expect(bad["old_sweep"] > 0, "MUTANT old sweep is caught (the defect class is visible)")
expect(bad["no_anchor"] > 0, "MUTANT without the anchor filter is caught")

# ---- 3. frames: a container parent that is NOT at the top of the screen ------
print("3  frames: parent offset 40, fix vs a sign error in st - sub->GetT()")
for mutant, want_good in ((None, True), ("sign", False)):
    ok = 0
    for n in range(1, MAX_ITEMS + 1):
        dll, win = Dll(3.0, 10, 1514, 2160, parent_off=40, mutant=mutant), Container()
        ok += good(open_and_sweep(dll, win, n, UTIL[2], UTIL))
    expect((ok == MAX_ITEMS) == want_good, "%s: %d/%d right" % (mutant or "fix", ok, MAX_ITEMS))

# ---- 4. lifecycle: the reviewed stale record (live SubBornScale=0 + a recycled address) ----
print("4  lifecycle: born open, SubBornScale=0 live, next open on the SAME container object")
for mutant, want_good in ((None, True), ("late_clear", False)):
    dll, win = Dll(3.0, 10, 1514, 2160, mutant=mutant), Container()
    open_and_sweep(dll, win, 3, UTIL[2], UTIL)          # born 3-item from Power: record set
    dll.born_scale_on = False                            # LiveTune: SubBornScale=0
    o = open_and_sweep(dll, win, 3, UTIL[0], UTIL)       # 3-item from Garbage, recycled address, same H
    expect(good(o) == want_good, "%s: ring %d (want %d), forward %s (want %s)" % (
        mutant or "fix", o["ring"], o["want_ring"], o["fwd"], o["want_fwd"]))

print()
if FAILS:
    print("%d FAILED" % len(FAILS))
    sys.exit(1)
print("ALL EXPECTATIONS HOLD")
