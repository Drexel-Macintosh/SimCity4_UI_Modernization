#!/usr/bin/env python3
r"""MODAL DIALOG PLACEMENT — where SC4 puts a modal dialog, predicted offline.

WHY THIS EXISTS
---------------
v2.37.5 forced the quit/exit confirms to the true screen centre because they
"looked high and left". They looked high because SC4 deliberately places modal
dialogs a little above centre — and once the dialog started being born at its
true SIZE (v2.38.0), that forced centring showed up as a 213px JUMP on the
first open of every session. The cure was to DELETE our centring (v2.38.1).

Had this rule been in the model, the centring would have been obviously wrong
before it shipped. So it lives here now, as executable arithmetic with an
assertion suite, not as a sentence in a document.

THE RULE, read out of the game's own code (not inferred):

    0x0078E3DF   sub edi,eax ; mov eax,0x55555556 ; imul edi ; ...
                                                    ->  y = (H - h) / 3
    0x0078E409   cdq ; sub eax,edx ; sar eax,1      ->  x = (W - w) / 2

i.e. horizontally centred, vertically ONE THIRD down the free space.

    python placement.py --selftest      # rule vs 3 measured births + the exe

Offline. The exe is opened read-only; the game is never launched.
"""

import os
import sys

EXE = r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Apps\SimCity 4.exe"
IMAGE_BASE = 0x400000

# The two code sites, with the exact bytes we decoded them from. If the exe ever
# differs here, the RULE BELOW IS NOT THIS BINARY'S RULE and every prediction
# made from it is void - so the self-test refuses to pass rather than quietly
# predicting from a stale decode.
SITES = [
    (0x0078E3E1, bytes.fromhex("b8565555 55f7ef8b cac1e91f 03ca".replace(" ", "")),
     "vertical: imul 0x55555556 -> (H-h)/3"),
    (0x0078E409, bytes.fromhex("992bc2d1f8"),
     "horizontal: cdq ; sub eax,edx ; sar eax,1 -> (W-w)/2"),
]

# Births measured live at 2400x1600, from SC4UIScale.log. Three different
# dialogs, three different heights - the rule was fitted to two and then
# predicted the third, which is why it is trusted.
MEASURED = [
    # (screenW, screenH, w, h, expect_x, expect_y, what)
    (2400, 1600, 270, 162, 1065, 479, "quit confirm, pre-v2.38.0 (1x birth)"),
    (2400, 1600, 500, 175,  950, 475, "Save box 0xAA8DEF97 (MWKID 2026-07-30)"),
    (2400, 1600, 540, 324,  930, 425, "quit confirm, data-born (DLGBORN)"),
]


def modal_origin(screen_w, screen_h, w, h):
    """Where SC4 places a modal dialog of size (w,h). Integer division, as the
    machine code does it (both results are non-negative here)."""
    return ((screen_w - w) // 2, (screen_h - h) // 3)


def check_exe():
    """The rule is only this binary's rule if the bytes still match."""
    if not os.path.isfile(EXE):
        return None
    with open(EXE, "rb") as f:
        img = f.read()
    bad = []
    for va, want, label in SITES:
        got = img[va - IMAGE_BASE: va - IMAGE_BASE + len(want)]
        if got != want:
            bad.append("  %08X %s\n    want %s\n    got  %s"
                       % (va, label, want.hex(" "), got.hex(" ")))
    return bad


def selftest():
    fails = []
    bad = check_exe()
    if bad is None:
        print("! exe not found - byte check SKIPPED (predictions unverified)")
    elif bad:
        fails.append("EXE BYTES CHANGED - the decoded rule is not this "
                     "binary's rule:\n" + "\n".join(bad))
    else:
        print("exe byte check: both placement sites match the decode")

    for (sw, sh, w, h, ex, ey, what) in MEASURED:
        gx, gy = modal_origin(sw, sh, w, h)
        ok = (gx, gy) == (ex, ey)
        print("  %-42s %4dx%-4d -> (%4d,%4d) %s"
              % (what, w, h, gx, gy, "ok" if ok else "MISMATCH (%d,%d)" % (ex, ey)))
        if not ok:
            fails.append("%s: predicted (%d,%d), measured (%d,%d)"
                         % (what, gx, gy, ex, ey))

    # A dialog is never centred vertically: y = (H-h)/3 is always ABOVE
    # (H-h)/2. Asserting the inequality states the shape of the rule, so a
    # future "just centre it" change fails here instead of in the user's face.
    for (sw, sh, w, h, _x, _y, what) in MEASURED:
        _gx, gy = modal_origin(sw, sh, w, h)
        if gy >= (sh - h) // 2:
            fails.append("%s: not above centre - rule shape broken" % what)

    if fails:
        print("\n".join("FAIL: " + f for f in fails))
        return 1
    print("ALL PASS (%d measured births + exe byte check + above-centre shape)"
          % len(MEASURED))
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    if len(sys.argv) == 5:
        print("%d,%d" % modal_origin(*(int(a) for a in sys.argv[1:5])))
        sys.exit(0)
    print(__doc__)
    print("usage: placement.py --selftest | placement.py <scrW> <scrH> <w> <h>")
    sys.exit(2)
