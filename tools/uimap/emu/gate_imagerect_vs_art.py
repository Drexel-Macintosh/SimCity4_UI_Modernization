r"""GATE: an `imagerect` that was a PARTIAL crop at 1x must stay partial.

READ THIS BEFORE "FIXING" THE UNDER-READ NUMBER THIS GATE PRINTS.

This gate was written to prove a theory about the 1.5x Day/Night trailing-edge
lines. THE THEORY WAS WRONG, and acting on it broke the thumbnail flyouts twice
in one afternoon. The gate survives - inverted - as the guard against that
regression.

THE THEORY (wrong, but very convincing): two independent pieces of code scale
the same thing and stopped agreeing -

    the ART   Upscale2x.cs::ScaleDim  round-half-up, THEN (since #143) SNAPPED
                                      to preserve CellUnit(v), TIES GOING UP
    the RECT  build_selective_safe.py::scale_len   floor(v*f + 0.5) - and it
                                      knows NOTHING about that snap

so at 1.5x ~427 rects sit SHORT of their art, while at 2x/3x `ScaleDim` returns
early and the two agree by construction. "Broken at 1.5x, perfect at 2x" maps
onto that exactly. It is still not the bug:

  * the Day/Night buttons (0xCA35CB74/76/78) carry `image={46a006b0,1441588x}`
    with NO `imagerect` AT ALL, so no rule about rects can reach them;
  * their art is dimensionally clean - 188x37 -> 284x56, 284/4 = 71 exact;
  * both attempts to close the gap DAMAGED the flyout thumbnails:
      tolerance-based  -> "every thumbnail flyout split down the left side"
      exact-1x-based   -> the LAST cell of a strip legitimately ends at the
                          sheet edge, so it alone got widened -> "look at the
                          UFO wrapping around";
  * and the reported lines did not change in either build.

WHAT THIS GATE ASSERTS NOW
--------------------------
  HARD FAIL  a rect that was a PARTIAL crop at 1x now spans the whole sheet
             (the thumbnail-split signature), measured RELATIVE to the integer
             tiers - see the baseline note in main()
  HARD FAIL  `ScaleDim` snapped anything at an INTEGER factor (it must return
             early there; this is the gate's own built-in control)
  REPORT     the under-read count, as a recorded BASELINE only. It is a real
             numeric disagreement and it is NOT the defect. If it ever does need
             closing, close it AT THE SOURCE - one scaler for art and rect -
             not by patching crops afterwards.

Offline. Reads the staged corpus and the 1x extract; no game, no exe.

    python gate_imagerect_vs_art.py [--tier 15x|2x|3x] [--list N]
"""
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
SS = os.path.join(ROOT, "tools", "selective-safe")
SRC1X = os.path.join(ROOT, "tools", "dbpf", "extracted", "SimCity_1")

STAGE = {"15x": ("stage-15x", 1.5), "2x": ("stage", 2.0), "3x": ("stage-3x", 3.0)}

RE_IMAGE = re.compile(r"image=\{([0-9a-fA-Fx]+),([0-9a-fA-Fx]+)\}")
RE_RECT = re.compile(r"imagerect=\((-?\d+),(-?\d+),(-?\d+),(-?\d+)\)")


# ONE SOURCE FOR THE SCALING RULES (scale_rules.py). This file used to
# carry its own copy; #162 changed ScaleRound in the DLL and every private
# copy in this folder had to be found by hand. `scale_rules.py --drift`
# hunts any that come back.
from scale_rules import round_half_up          # noqa: E402


def png_wh(path):
    try:
        with open(path, "rb") as f:
            head = f.read(33)
    except OSError:
        return None
    if len(head) < 33 or head[:8] != b"\x89PNG\r\n\x1a\n" or head[12:16] != b"IHDR":
        return None
    return (int.from_bytes(head[16:20], "big"), int.from_bytes(head[20:24], "big"))


def find(dirpath, gid, iid, spellings):
    for name in spellings:
        p = os.path.join(dirpath, name % (gid, iid))
        if os.path.isfile(p):
            return p
    return None


STAGED_NAMES = ("T-0x856ddbac_G-0x%08x_I-0x%08x.png",
                "T-0x856DDBAC_G-0x%08X_I-0x%08X.png")
SRC_NAMES = ("T-856ddbac_G-%08x_I-%08x.png",
             "T-0x856ddbac_G-0x%08x_I-0x%08x.png")


def run(tier, limit):
    sub, f = STAGE[tier]
    stage = os.path.join(SS, sub)
    if not os.path.isdir(stage):
        print("  SKIP - stage dir missing: %s" % stage)
        return None

    # ---- 1. which staged images were SNAPPED away from round(src*f)? --------
    snapped = {}          # (gid,iid) -> (src1x, staged, naive)
    staged_dims = {}
    considered = 0
    for fn in os.listdir(stage):
        if not fn.lower().endswith(".png"):
            continue
        m = re.match(r"T-0x[0-9a-fA-F]+_G-0x([0-9a-fA-F]+)_I-0x([0-9a-fA-F]+)\.png",
                     fn, re.I)
        if not m:
            continue
        gid, iid = int(m.group(1), 16), int(m.group(2), 16)
        sp = os.path.join(stage, fn)
        swh = png_wh(sp)
        if not swh:
            continue
        staged_dims[(gid, iid)] = swh
        p1 = find(SRC1X, gid, iid, SRC_NAMES)
        if not p1:
            continue
        o = png_wh(p1)
        if not o:
            continue
        considered += 1
        naive = (round_half_up(o[0] * f), round_half_up(o[1] * f))
        if swh != naive:
            snapped[(gid, iid)] = (o, swh, naive)

    print("  staged images with a 1x source : %d" % considered)
    print("  of those, SNAPPED by ScaleDim  : %d%s"
          % (len(snapped),
             "   (expected 0 at an integer factor)" if float(f).is_integer() else ""))

    # ---- 2. do any imagerects still describe the UNSNAPPED size? ------------
    bad = []
    # THE SECOND FAILURE MODE, ADDED AFTER SHIPPING IT (2026-08-06).
    # The first repair used a "short by <= 24px must be a snap" tolerance to
    # decide whether to widen a rect to its art. On a SMALL atlas - 40px wide
    # holding two 20px cells - the first cell is short by 20, passes the
    # tolerance, and gets widened across BOTH cells. Every thumbnail flyout
    # split down the left. A gate that only checks "did the rect follow the
    # art?" cannot see that; it needs the opposite question too:
    #     a rect that did NOT span the bitmap at 1x must NOT span it after.
    spread = []
    rects = 0
    # 1x rects come from the pristine scripts, keyed by TGI -> (r1x, b1x)
    orig_rect = {}
    uidir = os.path.join(ROOT, "tools", "uiscripts", "extracted")
    if os.path.isdir(uidir):
        for fn in os.listdir(uidir):
            if not fn.lower().endswith(".ui"):
                continue
            try:
                with open(os.path.join(uidir, fn), "r", encoding="latin-1") as fh:
                    txt = fh.read()
            except OSError:
                continue
            g = i = None
            for line in txt.splitlines():
                m = RE_IMAGE.search(line)
                if m:
                    try:
                        g, i = int(m.group(1), 16), int(m.group(2), 16)
                    except ValueError:
                        g = i = None
                m = RE_RECT.search(line)
                if m and g is not None:
                    orig_rect.setdefault((g, i),
                                         (int(m.group(3)), int(m.group(4))))
    for fn in os.listdir(stage):
        if not fn.lower().endswith(".ui"):
            continue
        try:
            with open(os.path.join(stage, fn), "r", encoding="latin-1") as fh:
                text = fh.read()
        except OSError:
            continue
        gid = iid = None
        for line in text.splitlines():
            m = RE_IMAGE.search(line)
            if m:
                try:
                    gid, iid = int(m.group(1), 16), int(m.group(2), 16)
                except ValueError:
                    gid = iid = None
            m = RE_RECT.search(line)
            if m and gid is not None:
                rects += 1
                key = (gid, iid)
                l, t, r, b = (int(x) for x in m.groups())

                # (b) OVER-EXTENSION: a crop that was PARTIAL at 1x must stay
                #     partial. If it now spans the whole sheet, the thumbnail
                #     shows two cells at once.
                o1 = orig_rect.get(key)
                a1 = staged_dims.get(key)
                s1 = None
                p1 = find(SRC1X, key[0], key[1], SRC_NAMES) if o1 else None
                if p1:
                    s1 = png_wh(p1)
                if o1 and a1 and s1:
                    was_full_w = (o1[0] == s1[0])
                    was_full_h = (o1[1] == s1[1])
                    if (r == a1[0] and not was_full_w) or \
                       (b == a1[1] and not was_full_h):
                        spread.append((fn, key[0], key[1], (l, t, r, b), a1, s1, o1))

                if key not in snapped:
                    continue
                o, staged, naive = snapped[key]
                # (a) UNDER-READ: the rect matches the size the art WOULD have
                #     had before the snap => scale_len computed it and nothing
                #     reconciled it.
                if (r, b) == naive and (r, b) != staged:
                    bad.append((fn, gid, iid, (l, t, r, b), staged, naive, o))

    print("  imagerects seen                : %d" % rects)
    print("  rects left at the unsnapped size : %d   (BASELINE - not a failure, "
          "see the header)" % len(bad))
    print("  RECTS OVER-EXTENDED ACROSS A CELL: %d%s"
          % (len(spread), "   <== THUMBNAILS WILL SPLIT" if spread else ""))
    for fn, gid, iid, rect, staged, o, orect in spread[:limit]:
        print("     {%08X,%08X} 1x art=%dx%d rect1x r,b=(%d,%d) -> art=%dx%d "
              "rect r,b=(%d,%d)  A PARTIAL CROP WAS WIDENED TO THE WHOLE SHEET"
              % (gid, iid, o[0], o[1], orect[0], orect[1],
                 staged[0], staged[1], rect[2], rect[3]))
    for fn, gid, iid, rect, staged, naive, o in bad[:limit]:
        print("     {%08X,%08X} 1x=%dx%d  art=%dx%d  rect r,b=(%d,%d) "
              "expected (%d,%d)  short by (%d,%d)"
              % (gid, iid, o[0], o[1], staged[0], staged[1], rect[2], rect[3],
                 staged[0], staged[1], staged[0] - rect[2], staged[1] - rect[3]))
    if len(bad) > limit:
        print("     ... and %d more" % (len(bad) - limit))
    return len(bad), len(snapped), len(spread)


def main():
    tiers = ["15x", "2x", "3x"]
    limit = 15
    if "--tier" in sys.argv:
        tiers = [sys.argv[sys.argv.index("--tier") + 1]]
    if "--list" in sys.argv:
        limit = int(sys.argv[sys.argv.index("--list") + 1])

    fail = []
    spread_by_tier = {}
    for tier in tiers:
        print("=" * 76)
        print("TIER %s" % tier)
        print("=" * 76)
        res = run(tier, limit)
        print()
        if res is None:
            continue
        nbad, nsnap, nspread = res
        # nbad is REPORTED, NEVER FAILED ON. Closing that gap is what broke
        # the thumbnails twice; see the header. Left visible so the number
        # cannot drift unnoticed.
        spread_by_tier[tier] = nspread
        if float(STAGE[tier][1]).is_integer() and nsnap:
            fail.append("%s: ScaleDim snapped %d image(s) at an INTEGER factor - "
                        "it is supposed to return early there" % (tier, nsnap))

    # OVER-EXTENSION IS A TIER-RELATIVE TEST, NOT AN ABSOLUTE ONE.
    # A handful of rects have run to the full sheet at EVERY tier since long
    # before this gate existed - e.g. {13F15260} is 367 of a 590 sheet at 1x and
    # ships full-width at 1.5x, 2x AND 3x. 2x and 3x are user-confirmed working
    # and were proven ENTRY-IDENTICAL across this change, so those are settled
    # behaviour, not defects; failing on them would be "fixing" what works.
    # What MUST fail is a fractional tier over-extending MORE than the integer
    # tiers - that is the signature of the tolerance bug that split every
    # thumbnail flyout on 2026-08-06.
    base = max([v for k, v in spread_by_tier.items()
                if float(STAGE[k][1]).is_integer()] or [0])
    for tier, n in spread_by_tier.items():
        if not float(STAGE[tier][1]).is_integer() and n > base:
            fail.append("%s: %d over-extended rects vs %d at the integer tiers "
                        "- a fractional-only over-extension is the thumbnail-"
                        "split bug" % (tier, n, base))
    if spread_by_tier:
        print("over-extension baseline (pre-existing at every tier): %d" % base)

    if fail:
        print("FAIL")
        for m in fail:
            print("   " + m)
        sys.exit(1)
    print("PASS - no fractional tier over-extends a partial crop beyond the "
          "long-standing baseline (the thumbnail-split guard).")
    sys.exit(0)


main()
