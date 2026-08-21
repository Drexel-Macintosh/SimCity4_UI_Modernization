#!/usr/bin/env python3
"""gate_iconcentre.py - task #149. ARITHMETIC ONLY; never opens a pixel.

Replays the ICONCENTRE rule (src\\UiSpike.cpp, BltStripThunk) against REAL blit
tuples captured live by the DSTRIP probe, and asserts:

  * every blit whose art is already correct is left EXACTLY untouched
  * every over-reading blit is re-cut to ONE TRUE STATE and centred
  * nothing is ever enlarged: there is no runtime upscaler

WHY THIS FILE EXISTS. The first attempt at this cure shipped a white line
through UI art because its predicate had never been run against a single real
blit: `srcW > stateW && srcW % stateW == 0` is satisfied by an ordinary
FULL-BITMAP draw, since srcW == bmpW is trivially a whole multiple of bmpW/4.
That was catchable at a desk in seconds. Any future edit to the rule must be
run through here first.

Usage:
    python gate_iconcentre.py --log <SC4UIScale.log>
    python gate_iconcentre.py --selftest
"""
import argparse
import re
import sys

# ---------------------------------------------------------------- the rule --
# Mirrors the C++ exactly. Keep them in step; if they diverge this gate is
# theatre.


def iconcentre(tex_w, tex_h, src, dst):
    """Return (new_src, new_dst) or None when the blit must be left alone."""
    sl, st, sr, sb = src
    dl, dt, dr, db = dst
    src_w, src_h = sr - sl, sb - st
    dst_w, dst_h = dr - dl, db - dt

    if not (tex_w > 0 and tex_h > 0 and tex_w % 4 == 0):
        return None
    if not (src_w > 0 and src_h > 0 and dst_w > 0 and dst_h > 0):
        return None

    cell_w = tex_w // 4
    # Act ONLY on an over-read: the stride the engine used is wider than the
    # texture's real state cell, and a whole number of cells at that.
    # srcW != texW is load-bearing: a full-bitmap 1:1 draw is trivially a
    # whole multiple of texW/4. Dropping it reproduces the white line.
    if not (src_w != tex_w and cell_w < src_w and src_w % cell_w == 0):
        return None

    state = sl // src_w
    nl = state * cell_w
    if not (0 <= state < 4 and nl + cell_w <= tex_w):
        return None

    new_src = (nl, 0, nl + cell_w, tex_h)
    ox = max((dst_w - cell_w) // 2, 0)
    oy = max((dst_h - tex_h) // 2, 0)
    new_dst = (dl + ox, dt + oy, dl + ox + cell_w, dt + oy + tex_h)
    return new_src, new_dst


# ------------------------------------------------------------- log fixtures --
LINE = re.compile(
    r"DSTRIP src (\d+)x(\d+) \((-?\d+),(-?\d+),(-?\d+),(-?\d+)\) "
    r"dst (\d+)x(\d+) \((-?\d+),(-?\d+),(-?\d+),(-?\d+)\) "
    r"a1=\w+ srcTex=(\d+)x(\d+) isBuf=(\d)"
)


def parse(path):
    out = []
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for ln in fh:
            m = LINE.search(ln)
            if not m:
                continue
            g = [int(x) for x in m.groups()]
            if g[14] != 1:          # isBuf=0 -> af[] is not a rect, skip
                continue
            out.append(dict(src=(g[2], g[3], g[4], g[5]),
                            dst=(g[8], g[9], g[10], g[11]),
                            tex=(g[12], g[13])))
    return out


def run_log(path):
    rows = parse(path)
    if not rows:
        print("FATAL: 0 DSTRIP tuples parsed from %s" % path)
        print("  A gate with no fixtures cannot fail and proves nothing.")
        return 2
    print("parsed %d DSTRIP blits (isBuf=1)" % len(rows))

    untouched, fixed, bad = 0, 0, []
    by_tex = {}
    for r in rows:
        tw, th = r["tex"]
        res = iconcentre(tw, th, r["src"], r["dst"])
        key = "%dx%d" % (tw, th)
        by_tex.setdefault(key, [0, 0])
        if res is None:
            untouched += 1
            by_tex[key][0] += 1
            # INVARIANT: art whose true cell already equals the read stride
            # must be the untouched set.
            if tw % 4 == 0 and tw // 4 != (r["src"][2] - r["src"][0]):
                bad.append(("left alone but cell != stride", r))
        else:
            fixed += 1
            by_tex[key][1] += 1
            ns, nd = res
            if ns[2] - ns[0] != tw // 4 or ns[3] - ns[1] != th:
                bad.append(("re-cut is not one full state", r))
            if nd[2] - nd[0] > r["dst"][2] - r["dst"][0]:
                bad.append(("ENLARGED the destination", r))
            if nd[0] < r["dst"][0] or nd[1] < r["dst"][1]:
                bad.append(("moved outside the original cell", r))

    print("\n  per texture size:")
    for k in sorted(by_tex):
        print("    %-10s untouched %-4d  re-cut %-4d" % (k, by_tex[k][0], by_tex[k][1]))
    print("\n  TOTAL untouched %d   re-cut %d" % (untouched, fixed))

    if bad:
        print("\nFAIL - %d invariant violations:" % len(bad))
        for why, r in bad[:10]:
            print("   %-34s tex=%s src=%s dst=%s" % (why, r["tex"], r["src"], r["dst"]))
        return 1
    if fixed == 0:
        print("\nFAIL: nothing was re-cut. Either the capture has no broken "
              "blits, or the rule is inert - both make this run worthless.")
        return 1
    print("\nPASS")
    return 0


# ------------------------------------------------------- negative controls --
def selftest():
    """The gate MUST be able to fail. Each case is a real trap we hit."""
    ok = True

    # 1. the 2x case that is ALREADY CORRECT -> must be left alone
    if iconcentre(352, 88, (88, 0, 176, 88), (0, 294, 88, 382)) is not None:
        print("FAIL: touched already-correct 352x88 art"); ok = False

    # 2. the real 1x break -> must be re-cut to one 44px state and centred
    r = iconcentre(176, 44, (88, 0, 176, 88), (0, 392, 88, 480))
    if r is None:
        print("FAIL: did not fix the known-broken 176x44 blit"); ok = False
    else:
        ns, nd = r
        if ns != (44, 0, 88, 44):
            print("FAIL: wrong state cut %s (want (44,0,88,44))" % (ns,)); ok = False
        if (nd[2] - nd[0], nd[3] - nd[1]) != (44, 44):
            print("FAIL: dst not one state %s" % (nd,)); ok = False
        if nd[0] != 22 or nd[1] != 414:   # (88-44)/2 centred in the 88px cell
            print("FAIL: not centred %s" % (nd,)); ok = False

    # 3. THE WHITE LINE. A full-bitmap 1:1 draw must never be touched. The
    #    first attempt fired on exactly these two and clipped real UI art.
    for tw, th in ((300, 120), (152, 38)):
        if iconcentre(tw, th, (0, 0, tw, th), (0, 0, tw, th)) is not None:
            print("FAIL: fired on full-bitmap %dx%d (the white line)" % (tw, th))
            ok = False

    # 4. non-square NAM strips (89x58 cells, 32% of real icons) must work,
    #    and must NOT be reasoned about via width/height.
    r = iconcentre(356, 58, (178, 0, 356, 116), (0, 0, 178, 116))
    if r is None:
        print("FAIL: non-square 356x58 over-read not fixed"); ok = False
    elif r[0] != (89, 0, 178, 58):
        print("FAIL: non-square cut %s (want (89,0,178,58))" % (r[0],)); ok = False

    # 5. never enlarge: art bigger than the read stride is not our business
    if iconcentre(352, 88, (0, 0, 44, 44), (0, 0, 44, 44)) is not None:
        print("FAIL: acted when the read was already smaller than the cell")
        ok = False

    # 6. MUTATION TEST - the gate must FAIL when the rule is broken on
    #    purpose. A gate that cannot fail proves nothing.
    def broken(tex_w, tex_h, src, dst):
        sl, _, sr, _ = src
        cell = tex_w // 4
        return ((0, 0, cell, tex_h), dst) if cell <= (sr - sl) else None
    if broken(300, 120, (0, 0, 300, 120), (0, 0, 300, 120)) is None:
        print("FAIL: mutation control did not reproduce the white-line bug")
        ok = False

    print("SELFTEST " + ("PASS - the gate fires on real breaks, ignores real "
                         "correct blits, and can be made to fail" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--log")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(selftest())
    if not a.log:
        ap.error("--log or --selftest")
    sys.exit(run_log(a.log))
