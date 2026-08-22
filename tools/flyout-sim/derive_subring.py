#!/usr/bin/env python3
"""Derive [Flyout] SubRingDX/SubRingDY from measured art - no dialling.

THE PROBLEM. The shared sub-flyout container (0x8A6E61E0: zone density, road
types...) draws its selection ring as an 80x53 sprite at buffer dst (0,94).
The DLL doubles that sprite (SUB-FLYOUT RING 2x in UiSpike.cpp) and offsets it
by SubRingDX/SubRingDY buffer px. Those two values were the last hand-dialled
numbers in the project (26,-4, fitted by eye 2026-07-29). This script derives
them from first principles so they are MEASURED, not guessed.

THE SPRITE IS NOT A PADDED CIRCLE. The earlier "asymmetric transparent
padding" theory (recorded in the ini at v2.15.3) is WRONG - rendered, the
sprite is a green KEYRING: an annulus on the left whose magenta HOLE shows the
selected button through it, merging into a full-height connector wedge that
runs to the sprite's right edge with ZERO padding. The correct alignment is
therefore feature-to-feature:

    ring HOLE centre  ==  button ELLIPSE centre

both of which are measurable from extracted DBPF art:

  * Ring atlas: T-856ddbac G-1abe787d I-14215ed0..ed5 (292x53, one per menu
    family; all SIX share one identical magenta mask). Matches the live DCTX
    trace: "area[0x14..0x20]=(0,0,292,53)". Hole = flood-fill enclosed
    magenta in the top-left 80x53 -> centre (25,26), a 31x21 ellipse.
  * Button art: T-856ddbac G-46a006b0 I-14215e40..42 (188x37 = 4 states of
    47x37). The visible ellipse does NOT fill the cell: bbox (1,0)..(41,30)
    against the near-black backdrop -> centre (21,15), offset (-2,-3) from
    the cell centre. THIS off-centre ellipse is why a naive box-centre
    derivation is 4-5px off and why the eye-dial "looked low".

THE CHAIN (all screen px in the 2x world; buffer px == screen px):

    container C   = btn + (nx,ny) + (SubDockDX,SubDockDY)   game native + our dock
    hole centre   = C + (rx + DX + 2*hx + 0.5,  ry + DY + 2*hy + 0.5)
    ellipse ctr   = btn + (2*ex + 0.5, 2*ey + 0.5)
    solve hole centre == ellipse centre for (DX,DY); the 0.5s cancel:

    SubRingDX = 2*ex - (nx + SubDockDX + rx + 2*hx)
    SubRingDY = 2*ey - (ny + SubDockDY + ry + 2*hy)

Inputs and where each was measured:
    (hx,hy) = (25,26)  hole centre, flood fill on I-14215ed0 (this script)
    (ex,ey) = (21,15)  ellipse centre, luminance bbox on I-14215e40 (this script)
    (nx,ny) = (20,-86) game's native container offset, live SUBDOCK log
    (rx,ry) = (0,94)   ring dst in buffer, live RCAL log
    SubDock = (-53,-24) from SC4UIScale.ini (the user-approved assembly dock)

Result: SubRingDX=25, SubRingDY=-6.  The 2026-07-29 eye-dial was (26,-4):
the derivation confirms it to 1-2px and replaces it.

Run from tools/flyout-sim:  python derive_subring.py [--factor F]
Needs ../dbpf/extracted (the full UI-art extraction) and Pillow.

FACTOR GENERALIZATION (tier fix B7, 2026-07-29). Every 2* in the chain is the
tier factor f, and the three "live-measured constants" are themselves the f=2
evaluations of factor-forms:
    ringBltY(f)   = RoundHalfUp(47*f)     (zones ring row; 2x measured 94)
    NATIVE_DY(f)  = RoundHalfUp(37*f)//2 - ringBltY(f) - 29   (2x measured -86)
    SubDock(f)    = (RoundHalfUp(-16.5*f) - 20,  29 - RoundHalfUp(26.5*f))
                    (the DLL's derived defaults, = ini -53,-24 at f=2)
The f=2 expectation (25,-6) is EXACT and hard-asserted (2x is the shipping,
user-confirmed tier). Non-2 factors print DERIVED, PROVISIONAL values that
must be confirmed live (SubBltLog/RingCal) before going into a tier's ini -
the audit's own first cut quoted different approximations (1.5x ~(-10,3),
3x ~(40,-24)), so treat every non-2 number here as a starting point, not truth.
"""
import argparse
import math
import os
import sys
from collections import deque

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
EXTRACTED = os.path.join(HERE, '..', 'dbpf', 'extracted', 'SimCity_1')

RING_ATLASES = ['T-856ddbac_G-1abe787d_I-14215ed%d.png' % i for i in range(6)]
BUTTON_ART = 'T-856ddbac_G-46a006b0_I-14215e40.png'
MAGENTA = (255, 0, 255)

_ap = argparse.ArgumentParser(description="SubRing derivation (factor-parametric).")
_ap.add_argument("--factor", type=float, default=2.0,
                 help="UI tier factor: 2 (default, exact-asserted), 1.5, or 3")
_args, _ = _ap.parse_known_args()
FACTOR = _args.factor


def rhu(v):
    """Round-half-up, the project-wide art/geometry rounding rule."""
    return int(math.floor(v + 0.5))


# Factor-parametric constants (see module docstring). At f=2 these evaluate to
# the live-measured 2x values recorded in the original script: (20,-86), (0,94),
# (-53,-24). NATIVE_DY + RING_RY is factor-only (btnH//2 - 29), so the derived
# SubRing values remain UNIVERSAL across menus at any one factor.
# ⚠ #134 (2026-08-05): NATIVE_DX was `20  # factor-independent`. IT IS NOT.
# SUBCAND measured the game's own native container X at 3840x2160 as
# BTN(237) + 43, i.e. the container is seated 27px left of the button CENTRE
# and that 27 is unscaled:  btnW//2 - 27  ->  94//2-27 = 20 (f=2, the old
# constant reproduced) and 141//2-27 = 43 (f=3, measured). Believing the old
# comment is what left 3x mis-docked by 23px - see gate_subnative.py, which
# predicts the game's measured (280,207) from the button alone.
# Note the halving is on the SCALED width: rhu(47f)//2 = 70 at f=3, whereas
# rhu(47f/2) = 71 and misses the measurement by one.
NATIVE_DX = rhu(47 * FACTOR) // 2 - 27
RING_RX = 0
# RING_RY is the ring's row inside the container buffer, read LIVE by the DLL
# (gSubRingBltY) because it differs per menu - RCAL has measured 94, 119 and
# 192 on different menus at f=3 alone. The value below is only a stand-in for
# printing: RING_RY appears in NATIVE_DY with the opposite sign, so it CANCELS
# out of both derived nudges. That cancellation is why this stand-in being
# imperfect never produced a wrong shipped number - do not read it as a claim
# about how the ring row scales, which is unmeasured at more than one tier.
RING_RY = rhu(47 * FACTOR)                       # stand-in only; cancels below
NATIVE_DY = rhu(37 * FACTOR) // 2 - RING_RY - 29 # placement law (2x: -86)
SUBDOCK_DX = rhu(-16.5 * FACTOR) - NATIVE_DX     # DLL derived default (2x: -53)
SUBDOCK_DY = 29 - rhu(26.5 * FACTOR)             # DLL derived default (2x: -24)

# Per-tier expectation table (replaces the single hard (25,-6) assert).
# exact=True rows are user-confirmed live and hard-fail on mismatch; the rest
# are None = print-only (PROVISIONAL - confirm live before shipping).
EXPECTED = {
    2.0: (25.0, -6.0),   # exact, shipping tier
    1.5: None,           # provisional until measured live
    3.0: None,           # provisional until measured live
}


def hole_centre(path):
    """Flood-fill enclosed magenta inside the top-left 80x53 = the hole."""
    px = Image.open(path).convert('RGB').load()
    W, H = 80, 53
    mag = [[px[x, y] == MAGENTA for x in range(W)] for y in range(H)]
    outside = [[False] * W for _ in range(H)]
    q = deque()
    for x in range(W):
        for y in (0, H - 1):
            if mag[y][x]:
                outside[y][x] = True
                q.append((x, y))
    for y in range(H):
        for x in (0, W - 1):
            if mag[y][x] and not outside[y][x]:
                outside[y][x] = True
                q.append((x, y))
    while q:
        x, y = q.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < W and 0 <= ny < H and mag[ny][nx] and not outside[ny][nx]:
                outside[ny][nx] = True
                q.append((nx, ny))
    xs, ys = [], []
    for y in range(H):
        for x in range(W):
            if mag[y][x] and not outside[y][x]:
                xs.append(x)
                ys.append(y)
    if not xs:
        return None
    return ((min(xs) + max(xs)) / 2.0, (min(ys) + max(ys)) / 2.0)


def ellipse_centre(path):
    """Visible-ellipse bbox centre in button-cell state 0 (47x37)."""
    px = Image.open(path).convert('RGB').load()
    x0 = y0 = 10 ** 9
    x1 = y1 = -1
    for y in range(37):
        for x in range(47):
            r, g, b = px[x, y]
            if r + g + b > 90:      # ellipse vs near-black cell backdrop
                x0 = min(x0, x); x1 = max(x1, x)
                y0 = min(y0, y); y1 = max(y1, y)
    return ((x0 + x1) / 2.0, (y0 + y1) / 2.0)


def main():
    fails = 0

    centres = set()
    for name in RING_ATLASES:
        c = hole_centre(os.path.join(EXTRACTED, name))
        centres.add(c)
        print('%-40s hole centre %s' % (name, c))
    if centres != {(25.0, 26.0)}:
        print('FAIL: ring hole centre moved (expected exactly (25,26) in all 6)')
        fails += 1

    ex, ey = ellipse_centre(os.path.join(EXTRACTED, BUTTON_ART))
    print('%-40s ellipse centre (%s,%s)' % (BUTTON_ART, ex, ey))
    if (ex, ey) != (21.0, 15.0):
        print('FAIL: button ellipse centre moved (expected (21,15))')
        fails += 1

    hx, hy = 25, 26
    f = FACTOR
    dx = f * ex - (NATIVE_DX + SUBDOCK_DX + RING_RX + f * hx)
    dy = f * ey - (NATIVE_DY + SUBDOCK_DY + RING_RY + f * hy)
    print()
    print('factor = %g   (SubDock %d,%d  native %d,%d  ring %d,%d)'
          % (f, SUBDOCK_DX, SUBDOCK_DY, NATIVE_DX, NATIVE_DY, RING_RX, RING_RY))
    print('SubRingDX = %g*%g - (%d + %d + %d + %g) = %g'
          % (f, ex, NATIVE_DX, SUBDOCK_DX, RING_RX, f * hx, dx))
    print('SubRingDY = %g*%g - (%d + %d + %d + %g) = %g'
          % (f, ey, NATIVE_DY, SUBDOCK_DY, RING_RY, f * hy, dy))

    expect = EXPECTED.get(f, None)
    if expect is not None:
        if (dx, dy) != expect:
            print('FAIL: derived values changed (expected %g,%g at f=%g) - if'
                  % (expect + (f,)))
            print('      SubDock was retuned on purpose, update the ini AND')
            print('      this expectation table.')
            fails += 1
    else:
        print('PROVISIONAL (f=%g has no live-confirmed expectation): confirm'
              ' with SubBltLog/RingCal before shipping these in a tier ini.' % f)

    print()
    print('ALL PASS - ini values: SubRingDX=%d SubRingDY=%d' % (rhu(dx), rhu(dy))
          if not fails else 'FAILURES: %d' % fails)
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
