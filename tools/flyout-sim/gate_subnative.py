#!/usr/bin/env python3
"""#134 GATE - the sub-flyout NATIVE offset is not factor-independent.

WHAT WAS WRONG. UiSpike.cpp carried `const int kSubNativeDX = 20`, documented
as "factor-independent". 20 is only its f=2 evaluation. The game actually
seats the sub-flyout container 27px left of the button CENTRE, so the offset
grows with the button - 20 at f=2, 43 at f=3.

WHY IT MATTERED, and it was not the ring. Two code paths dock the container:

  born  (SUBBORN2)  moves it from the game's REAL native position
  sweep (the 4x/sec pass) predicts that native as buttonX + kSubNativeDX

At f=2 predicted == real, so they agreed and 2x has always been correct. At
f=3 they differed by 43-20 = 23px, so:
  * the container came to rest 23px right of where the law puts it, which is
    the "ring is off to the right" the user reported; and
  * the sweep then matched the container at NEITHER atNative nor atTarget,
    silently declined it, and never ran - taking with it gSubArrowAbs, the
    back-arrow click zone, which is assigned ONLY inside that sweep.
One stale constant, one visible symptom and one invisible one.

THE FIXTURE BELOW IS A LIVE MEASUREMENT, not a construction. Every number
came from SC4UIScale.log at 3840x2160 (tier 3.00), 2026-08-05 11:45:49:

    SUBBORN2 ... born x3.00: container 129x290 -> 387x870 at (280,207)...
    RCAL #01 buf=387x870  src(0,0) 80x53  dst(0,119) 80x53
    SUBCAND #07 btn=0x00000037 BTN(237,300 141x111) CONT(211,30)
                nat(257,207) tgt(188,30) atNat=0 atTgt=0 NATDX=43
                holeCX=303 elliCX=300 ERR=+3 (DX=17) f=3.00

So the gate's real assertion is: does the corrected law PREDICT (280,207) -
the position the game itself chose - from the button alone? Nothing here is
fitted to make that come out; 27 and 29 are the only free constants and both
are pinned by f=2 as well.

Run:  python gate_subnative.py        (exit 0 = green)
No Pillow, no game, no DBPF - pure arithmetic.
"""
import math
import sys

FAIL = []


def rhu(v):
    """RoundHalfUp - byte-identical to UiSpike.cpp:154 floor(v + 0.5),
    negatives included: rhu(-49.5) = -49, NOT -50."""
    return int(math.floor(v + 0.5))


# ---- the laws under test (mirror UiSpike.cpp exactly) ---------------------
def sub_native_dx(btn_w, k=27):
    """SubNativeDXFor(). Halving is on the SCALED width: 141//2 = 70, which
    is the project's (a>>1) rounding law. rhu(47f/2) would give 71 and miss
    the live measurement by exactly 1 - that variant is a negative control."""
    return btn_w // 2 - k


def btn_w(f):
    return rhu(47.0 * f)


def btn_h(f):
    return rhu(37.0 * f)


def sub_dock_dx(f, k=27):
    # #135: was rhu(-16.5f) - native. The dock now carries the ENTIRE ring
    # alignment so that SubRingDX can be 0 and the ring stays welded to the
    # bar. Solving hole == ellipse with DX = 0 gives rhu(21f) - rhu(25f).
    return rhu(21.0 * f) - rhu(25.0 * f) - sub_native_dx(btn_w(f), k)


def sub_dock_dy(f):
    return 29 - rhu(26.5 * f)


def sub_ring_dx(f):
    # #135: ZERO at every tier. The ring's right edge IS the strip's left edge
    # (both 80f); any nudge drives the connector wedge into the panel and its
    # border lines end mid-panel - the junction seam, visible at 2x for months.
    return 0


def strip_left(f):
    return rhu(80.0 * f)


def ring_right(f):
    return sub_ring_dx(f) + rhu(80.0 * f)


def sub_ring_dy(f):
    return (rhu(15.0 * f) - rhu(37.0 * f) // 2
            + rhu(26.5 * f) - rhu(26.0 * f))


def native_xy(btn_x, btn_y, f, ring_blt_y, place_bias=29, k=27):
    """The game's own placement law for the container."""
    return (btn_x + sub_native_dx(btn_w(f), k),
            btn_y + btn_h(f) // 2 - ring_blt_y - place_bias)


def check(name, got, want):
    ok = got == want
    print("  %-58s %-9s %s" % (name, got, "ok" if ok else "FAIL want %s" % want))
    if not ok:
        FAIL.append(name)
    return ok


# ---- 1. THE LIVE 3x FIXTURE ----------------------------------------------
# Selected button 0x00000037, the one whose natT matched the born native Y.
F3 = 3.0
BTN_X, BTN_Y = 237, 300
BTN_W3, BTN_H3 = 141, 111
RING_BLT_Y3 = 119            # RCAL dst(0,119)
BORN_NATIVE3 = (280, 207)    # SUBBORN2 "at (280,207)"
HOLE_CX, ELLI_CX = 25, 21    # 1x sprite/cell feature centres (derive_subring)

print("#134 gate - sub-flyout native offset + ring derivation")
print()
print("1. LIVE 3x FIXTURE - predict what the game did, from the button alone")
check("button width matches the design cell 47f", btn_w(F3), BTN_W3)
check("button height matches the design cell 37f", btn_h(F3), BTN_H3)
nat3 = native_xy(BTN_X, BTN_Y, F3, RING_BLT_Y3)
check("native X predicted == SUBBORN2 measured", nat3[0], BORN_NATIVE3[0])
check("native Y predicted == SUBBORN2 measured", nat3[1], BORN_NATIVE3[1])
check("SubNativeDX at f=3 == SUBCAND NATDX", sub_native_dx(BTN_W3), 43)

# born and sweep must land on the SAME place - that is the whole defect.
born3 = nat3[0] + sub_dock_dx(F3)
# Written WITHOUT any native-offset term on purpose: born adds SubNativeDX and
# the dock subtracts it, so the two cancel and the sweep target collapses to a
# pure button-relative expression. Keeping this form independent is what makes
# the check meaningful rather than tautological.
# (#135 updated this from the old rhu(-16.5f); the gate caught its own stale
# copy of the law when the dock changed, which is the behaviour we want.)
sweep_tgt3 = BTN_X + rhu(21.0 * F3) - rhu(25.0 * F3)
check("born X == sweep target X (the coupled pair)", born3, sweep_tgt3)
check("docked container X (#135: was 188)", born3, 225)

# ring hole seats on button ellipse, exactly
hole = born3 + 0 + sub_ring_dx(F3) + rhu(HOLE_CX * F3)
elli = BTN_X + rhu(ELLI_CX * F3)
check("ring hole centre == button ellipse centre", hole, elli)
check("residual ERR at f=3 (SUBCAND reported +3 at DX=17)", hole - elli, 0)

# ---- 2. THE f=2 GATE - a user-confirmed tier must not move ---------------
print()
print("2. f=2 REGRESSION - shipping tier, must be bit-identical")
check("SubNativeDX(f=2) == the old hard-coded 20", sub_native_dx(btn_w(2.0)), 20)
# ⚠ #135 CHANGES TWO PREVIOUSLY-SHIPPED f=2 CONSTANTS, DELIBERATELY.
# The old pair (-53, 25) seated the ring correctly but only by sliding it off
# the bar; the user reported that seam and confirmed it predates 3x. The new
# pair (-28, 0) holds BOTH properties. The 2x assembly therefore moves 25px
# right. This assert is updated on purpose - if it ever reads -53 again,
# someone reverted the fix, not restored a baseline.
check("SubDockDX(f=2) #135 was -53, now", sub_dock_dx(2.0), -28)
check("SubDockDY(f=2) == shipped ini -24", sub_dock_dy(2.0), -24)
check("SubRingDX(f=2) #135 was 25, now welded", sub_ring_dx(2.0), 0)
check("SubRingDY(f=2) == shipped ini -6", sub_ring_dy(2.0), -6)

# ---- 3. ALL THREE TIERS -------------------------------------------------
print()
print("3. TIER TABLE (1.5x is the THIRD tier - a two-tier law is unproven)")
print("   ! DockDY is the LEGACY form. With SubMath=1 (the default) the Y")
print("     target comes from SubPlaceTop(), not this column - which is why")
print("     the 3x log shows the born path applying -177, not -51. It is")
print("     asserted at f=2 only, where it must equal the shipped ini -24.")
print("     f      btnW   NATDX   DockDX  DockDY   RingDX  RingDY")
for f in (1.5, 2.0, 3.0):
    print("   %4.2f   %5d   %5d   %6d  %6d   %6d  %6d"
          % (f, btn_w(f), sub_native_dx(btn_w(f)), sub_dock_dx(f),
             sub_dock_dy(f), sub_ring_dx(f), sub_ring_dy(f)))
# self-consistency at every tier: the hole must seat on the ellipse for ANY
# button position and ANY ring row, because both cancel out of the chain.
print()
print("4. ALIGNMENT IDENTITY - must hold for every tier/button/ring row")
bad = 0
checked = 0
for f in (1.5, 2.0, 3.0):
    for bx in range(0, 4000, 37):
        for by in (0, 300, 1047, 2100):
            for rby in (94, 119, 192):
                nx, _ = native_xy(bx, by, f, rby)
                cx = nx + sub_dock_dx(f)
                h = cx + sub_ring_dx(f) + rhu(HOLE_CX * f)
                e = bx + rhu(ELLI_CX * f)
                checked += 1
                if h != e:
                    bad += 1
check("alignment residual over %d button/ring combinations" % checked, bad, 0)

print()
print("4b. THE WELD - ring right edge must BE the strip left edge (#135)")
for f in (1.5, 2.0, 3.0):
    check("f=%.2f  ring right == strip left" % f, ring_right(f), strip_left(f))
    check("f=%.2f  SubRingDX is zero" % f, sub_ring_dx(f), 0)

# ---- 5. NEGATIVE CONTROLS - a gate that cannot fail proves nothing -------
print()
print("5. NEGATIVE CONTROLS (each MUST break something)")


def neg(name, cond):
    print("  %-58s %s" % (name, "ok (detected)" if cond else "FAIL (blind)"))
    if not cond:
        FAIL.append("negative control: " + name)


# 5a. the old constant 20 must NOT reproduce the measured 3x native
old = BTN_X + 20
neg("stale kSubNativeDX=20 misses the measured native", old != BORN_NATIVE3[0])
neg("  ...and by exactly the 23px the log showed",
    BORN_NATIVE3[0] - old == 23)
# 5b. the 27 is pinned at BOTH tiers - perturbing it must break one of them
for k in (26, 28):
    ok3 = native_xy(BTN_X, BTN_Y, F3, RING_BLT_Y3, k=k)[0] == BORN_NATIVE3[0]
    ok2 = sub_native_dx(btn_w(2.0), k) == 20
    neg("k=%d breaks f=2 or f=3" % k, not (ok3 and ok2))
# 5c. the halving variant that looks equivalent but is not
alt = rhu(47.0 * F3 / 2) - 27
neg("rhu(47f/2) variant misses by 1 at f=3", alt != 43 and abs(alt - 43) == 1)
# 5d. ring formula must be pinned by the confirmed f=2 values
neg("RingDX with a dropped term fails f=2",
    (rhu(21.0 * 2) - rhu(25.0 * 2)) != 25)
neg("RingDY with a dropped term fails f=2",
    (rhu(15.0 * 2) - rhu(37.0 * 2) // 2) != -6)
# 5e. the identity sweep must be able to see a break
broke = 0
for f in (1.5, 2.0, 3.0):
    nx, _ = native_xy(0, 0, f, 94)
    if nx + sub_dock_dx(f) + (sub_ring_dx(f) + 1) + rhu(HOLE_CX * f) != rhu(ELLI_CX * f):
        broke += 1
neg("a 1px ring error is caught at all 3 tiers", broke == 3)
# 5f. the weld must be breakable - a nudge of 1 must separate the edges
neg("a 1px nudge breaks the weld at all 3 tiers",
    all(ring_right(f) + 1 != strip_left(f) for f in (1.5, 2.0, 3.0)))
# 5g. the OLD dock cannot satisfy the weld - proves the two are coupled
neg("old dock rhu(-16.5f) cannot hold weld+alignment together",
    all(rhu(-16.5 * f) - sub_native_dx(btn_w(f)) != sub_dock_dx(f)
        for f in (1.5, 2.0, 3.0)))

print()
if FAIL:
    print("RED - %d failure(s):" % len(FAIL))
    for f_ in FAIL:
        print("   - %s" % f_)
    sys.exit(1)
print("GREEN - the corrected law predicts the game's own (280,207) from the")
print("button alone and seats the ring exactly at 1.5x / 2x / 3x, with the")
print("ring welded to the bar (SubRingDX = 0) at every tier.")
print()
print("NOT a no-op at 2x: SubDockDX -53 -> -28 and SubRingDX 25 -> 0 are")
print("DELIBERATE (#135). The old pair seated the ring only by sliding it off")
print("the bar, which is the junction seam the user reported and confirmed")
print("predates 3x. The 2x assembly moves 25px right as a result - that is")
print("the fix, not a regression, and it needs eyes-on at 2x.")
sys.exit(0)
