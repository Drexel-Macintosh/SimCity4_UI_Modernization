r"""adjudicate_166_originsnap.py - #166 CURE CANDIDATE: SNAP THE ROUNDING FRAME.

⛔ WHAT IS BEING ADJUDICATED, AND WHAT IT IS NOT
────────────────────────────────────────────────────────────────────────────────
#166 measured a 1px art-vs-window disagreement on a panel ROOT, present only at
the origin THE GAME DOCKS THE PANEL AT. Two cures are on the table:

  LAW "len"   the one ALREADY WRITTEN (unbuilt) into src\UiSpike.cpp - search
              "#166: A PANEL ROOT IS SIZED AS A LENGTH".  newW = R(w,f).
              It changes the ROOT's size and NOTHING ELSE: `rootDesignL` still
              goes to the children as the raw live `l`.

  LAW "snap"  THE CANDIDATE THIS FILE PRICES. Derive ONE q-aligned rounding
              reference and use it for BOTH the root's own extent AND the frame
              handed to ScaleSubtree:
                  q     = denominator of f in lowest terms
                  lRef  = l - (((l % q) + q) % q)        (a multiple of q)
                  newW  = R(lRef + w) - R(lRef)      ( == R(w), provably )
                  rootDesignL = lRef                 ( the new part )
              PLACEMENT (newX/newY, the gaps, the branch, the clamps) keeps the
              RAW l/t - nothing is nudged on screen.

⚠ THIS IS NOT "SNAP THE PANEL'S POSITION". That variant is refuted in the
report, by arithmetic: newX is computed AFTER newW and feeds nothing.

THE ALGEBRA THE WHOLE THING RESTS ON
────────────────────────────────────────────────────────────────────────────────
For f = p/q in lowest terms and R = floor(v*f + 0.5):

        q | a   =>   R(a + d) - R(a) == R(d)     for EVERY d

because a*f is then an exact integer and floors out of the expression. So
translating the rounding frame by a MULTIPLE OF q is a symmetry of the lattice,
and translating it by anything else is not. The game docks panels at arbitrary
offsets, i.e. at an arbitrary PHASE against the lattice the offline art and
every offline gate in this folder are built on. Snapping restores the phase.

At an integer factor q == 1, every integer is a multiple of q, `lRef == l`
IDENTICALLY, and the candidate is textually the shipping code.

MODES
────────────────────────────────────────────────────────────────────────────────
  --corpus     every capture under _tests\captures\, (W,H,f) INFERRED and then
               VERIFIED against the shipping law (a capture that does not
               reproduce 100% is reported and EXCLUDED, never silently used).
  --contract   the #161 edge contract: does a child at local (w,h) still land
               exactly on its parent's scaled extent? Priced per law.
  --dash       the city dashboard subtree, node by node, at the live origin.
  --gates      what the two named invariant gates would report if their root
               frame were re-phased the way the candidate re-phases it.
  --proof      the integer-tier no-op and the lattice theorem, by exhaustion.

Offline, read-only. Writes nothing.
"""
import argparse
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from scale_rules import scale_round as R                      # noqa: E402
from scale_rules import llround_scale as LLR                  # noqa: E402
import emu_panel_anchor as EPA                                # noqa: E402

UIMAP = os.path.dirname(HERE)
TOOLS = os.path.dirname(UIMAP)
ROOT = os.path.dirname(TOOLS)
CAPS = os.path.join(ROOT, "_tests", "captures")
UI_DIR = os.path.join(TOOLS, "uiscripts", "extracted")


# ══════════════════════════════════════════════════════════════════════════════
# q, EXACTLY - and fail-safe to 1 (which makes the candidate a no-op)
# ══════════════════════════════════════════════════════════════════════════════

def denom(f):
    """Smallest power-of-two q with f*q an EXACT integer in double arithmetic.

    Powers of two only, and exactness with NO epsilon: the whole argument needs
    lRef*f to be an exact integer, which for a binary float means q must clear
    the fraction bits. 1.5 -> 2, 1.25 -> 4, 2.0 -> 1, 3.0 -> 1. Anything the
    test cannot certify returns 1, i.e. the candidate degrades to the shipping
    code rather than to a guess."""
    d = float(f)
    q = 1
    while q <= 8:
        p = d * q
        if p == int(p):
            return q
        q *= 2
    return 1


def snap(v, q):
    """Largest multiple of q that is <= v. Correct for NEGATIVE v (design t is
    -5 on the dashboard, -16 on the city mode overlay)."""
    r = v % q
    if r < 0:
        r += q
    return v - r


# ══════════════════════════════════════════════════════════════════════════════
# THE THREE ROOT LAWS. Placement is EPA.anchor's, verbatim, with newW/newH and
# the rounding frame swapped in - so any divergence is the law and not a reimpl.
# ══════════════════════════════════════════════════════════════════════════════

LAWS = ("cur", "len", "snap")


def root_extent(l, t, w, h, f, law):
    """-> (newW, newH, frameL, frameT). frameL/frameT is what goes to the
    subtree as #161's pAbs."""
    if law == "cur":
        return R(l + w, f) - R(l, f), R(t + h, f) - R(t, f), l, t
    if law == "len":
        return R(w, f), R(h, f), l, t          # frame UNCHANGED - the in-file fix
    q = denom(f)
    ls, ts = snap(l, q), snap(t, q)
    return R(ls + w, f) - R(ls, f), R(ts + h, f) - R(ts, f), ls, ts


def place(wid, l, t, w, h, W, H, f, law, fam=True, rr=None):
    """ScalePanelRoot, with the law's extent. Everything else is EPA's model:
    the family branch, the three-way per-axis branch, the four per-edge clamps.

    `fam` / `rr` exist ONLY for BUILD IDENTIFICATION (see verified_captures):
    the corpus spans builds from before the #101 family co-anchor and from
    before #162 swapped llround for half-up. They are never used to price the
    candidate - that is always done with today's rules.
    -> ((x,y,w,h), tag, (frameL, frameT)) or (None, 'SKIP', ...)"""
    global R
    keep, R = R, (rr or R)
    try:
        return _place(wid, l, t, w, h, W, H, f, law, fam)
    finally:
        R = keep


def _place(wid, l, t, w, h, W, H, f, law, fam=True):
    new_w, new_h, fl, ft = root_extent(l, t, w, h, f, law)
    if new_w > W or new_h > H:
        return None, "SKIP", (fl, ft)

    gap_l, gap_r = l, W - (l + w)
    gap_t, gap_b = t, H - (t + h)
    c_min_x, c_min_y = W // 4, H // 4

    if fam and wid in EPA.FAMILY:
        origin = R(EPA.FAM_LEADER_L, f)
        span = R(EPA.FAM_LEADER_R, f) - R(EPA.FAM_LEADER_L, f)
        if origin + span > W:
            origin = W - span
        if origin < 0:
            origin = 0
        new_x, bx = origin + R(l, f) - R(EPA.FAM_LEADER_L, f), "F"
        gap_l = gap_r = -1                       # clampX = false
    elif gap_l > c_min_x and gap_r > c_min_x:
        new_x, bx = l + w // 2 - new_w // 2, "C"
    elif gap_l <= gap_r:
        new_x, bx = R(gap_l, f), "L"
    else:
        new_x, bx = W - R(gap_r, f) - new_w, "R"

    if gap_t > c_min_y and gap_b > c_min_y:
        new_y, by = t + h // 2 - new_h // 2, "C"
    elif gap_t <= gap_b:
        new_y, by = R(gap_t, f), "T"
    else:
        new_y, by = H - R(gap_b, f) - new_h, "B"

    if gap_r >= 0 and new_x + new_w > W:
        new_x, bx = W - new_w, bx + "!"
    if gap_l >= 0 and new_x < 0:
        new_x, bx = 0, bx + "0"
    if gap_b >= 0 and new_y + new_h > H:
        new_y, by = H - new_h, by + "!"
    if gap_t >= 0 and new_y < 0:
        new_y, by = 0, by + "0"
    return (new_x, new_y, new_w, new_h), bx + by, (fl, ft)


# ══════════════════════════════════════════════════════════════════════════════
# CAPTURE DISCOVERY - (W,H,f) inferred, then VERIFIED. Never assumed.
# ══════════════════════════════════════════════════════════════════════════════

RES = re.compile(r"render res = monitor (\d+)x(\d+)")
RES2 = re.compile(r"exceeds frame (\d+)x(\d+)")
FAC = re.compile(r"ScaleFactor[= ](\d+\.\d+)")
FAC2 = re.compile(r" x(\d\.\d\d) ")


def infer(path):
    """-> list of (W,H,f) candidates, most likely first."""
    ws, fs = [], []
    with open(path, encoding="utf-8", errors="replace") as fh:
        head = fh.read()
    for m in RES.finditer(head):
        t = (int(m.group(1)), int(m.group(2)))
        if t not in ws:
            ws.append(t)
    for m in RES2.finditer(head):
        t = (int(m.group(1)), int(m.group(2)))
        if t not in ws:
            ws.append(t)
    for rx in (FAC, FAC2):
        for m in rx.finditer(head):
            v = float(m.group(1))
            if v not in fs and 1.0 <= v <= 4.0:
                fs.append(v)
    # The view3d frame is NOT always the render res (a capture can log a
    # monitor mode the wrapper then letterboxes). Acceptance still demands a
    # 100% reproduction, so offering extra candidates cannot launder anything.
    for t in ((2400, 1600), (1920, 1080), (1600, 1200), (1400, 1050),
              (3840, 2160), (2560, 1440), (1280, 1024)):
        if t not in ws:
            ws.append(t)
    if not fs:
        fs = [1.5, 2.0, 3.0]
    return [(w, h, f) for (w, h) in ws for f in fs]


#: The BUILD VARIANTS the corpus actually spans. Each is a real, dated change
#: to the shipping code, not a fudge factor:
#:   fam   #101 v2.56.0 added the city-HUD co-anchor    (before: generic anchor)
#:   rr    #162          swapped llround for half-up    (before: llround)
BUILD_VARIANTS = [
    ("half-up + family", True, None),
    ("llround  + family", True, LLR),
    ("half-up , generic", False, None),
    ("llround , generic", False, LLR),
]


def verified_captures():
    """Every capture whose panel lines SOME shipping build reproduces 100%.

    ⛔ THE VARIANT IS USED FOR IDENTIFICATION ONLY. Once a capture is
    understood, the blast is priced with TODAY'S rules (half-up + family) on the
    live rects the capture supplies - because the question is what the candidate
    does to the code that ships now, not to the code that wrote the log."""
    good, bad = [], []
    for fn in sorted(os.listdir(CAPS)):
        if not fn.lower().endswith(".log"):
            continue
        path = os.path.join(CAPS, fn)
        caps = EPA.parse_capture(path)
        if not caps:
            continue
        best = None
        for (W, H, f) in infer(path):
            for vname, vfam, vrr in BUILD_VARIANTS:
                n = sum(1 for wid, (d, lg) in caps.items()
                        if place(wid, *d, W, H, f, "cur", vfam, vrr)[0] == lg)
                if best is None or n > best[0]:
                    best = (n, W, H, f, vname)
        if best is None:
            bad.append((fn, len(caps), "no (W,H,f) in the header"))
            continue
        n, W, H, f, vname = best
        if n == len(caps):
            good.append((fn, path, W, H, f, caps, vname))
        else:
            bad.append((fn, len(caps), "best (%dx%d f=%s %s) reproduces %d/%d"
                        % (W, H, f, vname, n, len(caps))))
    return good, bad


# ══════════════════════════════════════════════════════════════════════════════
# MODES
# ══════════════════════════════════════════════════════════════════════════════

def mode_corpus(verbose):
    good, bad = verified_captures()
    print("VERIFIED captures (shipping law reproduces every panel line): %d"
          % len(good))
    print("EXCLUDED: %d" % len(bad))
    for fn, n, why in bad:
        print("   - %-58s %3d lines  %s" % (fn, n, why))

    # per-tier tallies over SIGHTINGS (a root seen in k captures counts k times)
    tal = {}
    movers = {}
    for fn, path, W, H, f, caps, vname in good:
        key = f
        t = tal.setdefault(key, dict(n=0, files=0, len_sz=0, len_pos=0,
                                     snap_sz=0, snap_pos=0, snap_vs_len=0))
        t["files"] += 1
        for wid, (d, lg) in sorted(caps.items()):
            cur = place(wid, *d, W, H, f, "cur")[0]
            ln = place(wid, *d, W, H, f, "len")[0]
            sn = place(wid, *d, W, H, f, "snap")[0]
            t["n"] += 1
            if cur[2:] != ln[2:]:
                t["len_sz"] += 1
            if cur[:2] != ln[:2]:
                t["len_pos"] += 1
            if cur[2:] != sn[2:]:
                t["snap_sz"] += 1
            if cur[:2] != sn[:2]:
                t["snap_pos"] += 1
            if ln != sn:
                t["snap_vs_len"] += 1
            if cur != sn:
                movers.setdefault(f, {}).setdefault(
                    wid, (d, cur, sn, W, H, fn))
    print()
    print("  f     caps  sightings | LEN size  LEN pos | SNAP size  SNAP pos |"
          " SNAP!=LEN")
    for f in sorted(tal):
        t = tal[f]
        print("  %-5s %4d  %9d | %8d  %7d | %9d  %8d | %9d"
              % (f, t["files"], t["n"], t["len_sz"], t["len_pos"],
                 t["snap_sz"], t["snap_pos"], t["snap_vs_len"]))
    print()
    for f in sorted(movers):
        ids = movers[f]
        print("f=%s: %d DISTINCT root ids move under SNAP" % (f, len(ids)))
        if verbose:
            for wid, (d, cur, sn, W, H, fn) in sorted(ids.items()):
                print("   0x%08X design%-22s cur%-22s snap%-22s  %dx%d %s"
                      % (wid, d, cur, sn, W, H, fn))
    return 0


def mode_contract(verbose):
    """#161's contract, priced. A child whose local rect ends exactly on the
    parent's (l == 0, w == parentW) must land on the parent's scaled extent:

        childRight = R(frameL + 0 + w) - R(frameL)   must equal   newW

    Under "cur" that is true BY CONSTRUCTION. Under "len" the extent moved to a
    different lattice while the frame did not, so it can fail. Under "snap" both
    come off the SAME reference, so it is true by construction again."""
    good, _ = verified_captures()
    tal = {}
    ex = {}
    for fn, path, W, H, f, caps, vname in good:
        for wid, (d, lg) in sorted(caps.items()):
            l, t, w, h = d
            for law in LAWS:
                nw, nh, fl, ft = root_extent(l, t, w, h, f, law)
                kx = R(fl + w, f) - R(fl, f)      # child edge, in the ROOT frame
                ky = R(ft + h, f) - R(ft, f)
                bad = (kx != nw) + (ky != nh)
                s = tal.setdefault((f, law), [0, 0])
                s[0] += 1
                s[1] += 1 if bad else 0
                if bad and law == "len":
                    ex.setdefault(f, {})[wid] = (d, nw, nh, kx, ky)
    print("#161 EDGE CONTRACT - a child flush with the parent's edge lands on it?")
    print("  f      law    roots  CONTRACT BROKEN")
    for (f, law) in sorted(tal):
        n, b = tal[(f, law)]
        print("  %-5s  %-5s  %5d  %6d %s" % (f, law, n, b,
              "  <-- " + ("OK" if b == 0 else "REOPENS #161")))
    for f in sorted(ex):
        print("\nf=%s: %d distinct roots where law 'len' breaks it" % (f, len(ex[f])))
        if verbose:
            for wid, (d, nw, nh, kx, ky) in sorted(ex[f].items())[:40]:
                print("   0x%08X design%-22s extent %dx%d  child edge lands %dx%d"
                      % (wid, d, nw, nh, kx, ky))
    return 0


# ---------------------------------------------------------------- dashboard

ATTR = re.compile(r'(\w+)=("[^"]*"|\{[^}]*\}|\([^)]*\)|\S+)')
TAG = re.compile(r"<(/?)(LEGACY|CHILDREN)([^>]*)>")
RECT = re.compile(r"\((-?\d+),(-?\d+),(-?\d+),(-?\d+)\)")
DASH_UI = os.path.join(UI_DIR, "T-00000000_G-96a006b0_I-c973b411.ui")
DASH_ID = 0x0987B48F
DESIGN = (30, -5)
LIVE = (5, 1388)


def parse_tree(path):
    with open(path, encoding="latin-1") as fh:
        text = fh.read()
    root = {"attrs": {}, "kids": []}
    stack = [root]
    last = root
    for m in TAG.finditer(text):
        close, tag, body = m.group(1), m.group(2), m.group(3)
        if tag == "CHILDREN":
            if close:
                stack.pop()
            else:
                stack.append(last)
            continue
        node = {"attrs": dict(ATTR.findall(body)), "kids": []}
        stack[-1]["kids"].append(node)
        last = node
    return root


def find_by_id(node, want):
    for k in node["kids"]:
        v = k["attrs"].get("id", "")
        try:
            if int(v.strip('"'), 0) == want:
                return k
        except ValueError:
            pass
        r = find_by_id(k, want)
        if r:
            return r
    return None


def dash_census(origin, f, law):
    node = find_by_id(parse_tree(DASH_UI), DASH_ID)
    m = RECT.match(node["attrs"]["area"])
    l0, t0, r0, b0 = (int(x) for x in m.groups())
    w0, h0 = r0 - l0, b0 - t0
    L, T = origin
    nw, nh, fl, ft = root_extent(L, T, w0, h0, f, law)
    cen = {"ROOT": (0, 0, nw, nh)}

    def walk(n, p_l, p_t, off, key):
        for i, kid in enumerate(n["kids"]):
            mm = RECT.match(kid["attrs"].get("area", ""))
            if not mm:
                continue
            l, t, r, b = (int(x) for x in mm.groups())
            w, h = r - l, b - t
            a_l, a_t = p_l + l, p_t + t
            nl = R(a_l, f) - R(p_l, f)
            nt = R(a_t, f) - R(p_t, f)
            ww = R(a_l + w, f) - R(a_l, f)
            hh = R(a_t + h, f) - R(a_t, f)
            if not kid["kids"]:                    # #148 leaf rule
                ww, hh = R(w, f), R(h, f)
            lab = "%s/%s" % (key, kid["attrs"].get("id", "#%d" % i))
            cen[lab] = (off[0] + nl, off[1] + nt, ww, hh)
            walk(kid, a_l, a_t, (off[0] + nl, off[1] + nt), lab)

    walk(node, fl, ft, (0, 0), "")
    return cen


def mode_dash(verbose):
    """TWO references, because they are different questions and only one of
    them is the ART's:

      REF-DESIGN  the panel rounded at the origin its .UI declares, (30,-5).
                  This is what gate_abut_1_5x / gate_art_vs_window model. It is
                  NOT automatically the art's frame: -5 is odd, so the .UI's own
                  declared origin is itself off the lattice in Y.
      REF-LATTICE the phase-0 frame: every offset R(l), every leaf R(w). This is
                  what the offline pipeline actually builds - ScaleDim is a pure
                  LENGTH and knows no origin at all - and it is what EVERY OTHER
                  ScaleSubtree entry point in UiSpike.cpp already produces,
                  because they all pass pAbs = 0."""
    print("CITY DASHBOARD 0x%08X - design origin %s, live origin %s" %
          (DASH_ID, DESIGN, LIVE))
    for f in (1.5, 2.0, 3.0):
        refs = (("REF-DESIGN ", dash_census(DESIGN, f, "cur")),
                ("REF-LATTICE", dash_census((0, 0), f, "cur")))
        cur = dash_census(LIVE, f, "cur")
        print("\n f=%s   nodes=%d" % (f, len(cur)))
        for rname, ref in refs:
            row = []
            for law in LAWS:
                live = dash_census(LIVE, f, law)
                # positions only: a lattice reference has a different absolute
                # origin, so compare the SHAPE - offsets within the root - which
                # is what the art has to line up with.
                moved = sum(1 for k in ref if ref[k] != live.get(k))
                szbad = sum(1 for k in ref
                            if ref[k][2:] != live.get(k, (0, 0, 0, 0))[2:])
                row.append("%s %2d (%d sz)" % (law, moved, szbad))
            print("   vs %s : %s" % (rname, "   ".join(row)))
        for law in ("len", "snap"):
            live = dash_census(LIVE, f, law)
            ch = sum(1 for k in cur if cur[k] != live.get(k))
            print("   ON SCREEN vs today: law %-4s moves %2d/%d nodes"
                  % (law, ch, len(cur)))
        if verbose:
            live = dash_census(LIVE, f, "snap")
            for k in sorted(cur):
                if cur[k] != live.get(k):
                    print("        %-44s cur%-20s snap%s"
                          % (k[-44:], cur[k], live.get(k)))
    return 0


# ------------------------------------------------------------------- gates

def gate_rephase_delta():
    """What the two invariant gates would report if the panel-root frame were
    re-phased the way the candidate re-phases it.

    MODELLING NOTE, stated because it is load-bearing: both gates start their
    absolute-origin accumulation at 0 and then apply the FILE ROOT's own `area`,
    so a file root at design l becomes the phase every descendant rounds in.
    The candidate replaces that phase with a multiple of q. Here that is modelled
    by snapping the file root's design origin - which is exactly the runtime
    change, expressed in the gate's own coordinates."""
    files = [f for f in sorted(os.listdir(UI_DIR)) if f.endswith(".ui")]
    odd = 0
    for fn in files:
        with open(os.path.join(UI_DIR, fn), encoding="latin-1") as fh:
            text = fh.read()
        m = None
        for t in TAG.finditer(text):
            if t.group(2) == "LEGACY" and not t.group(1):
                a = dict(ATTR.findall(t.group(3)))
                m = RECT.match(a.get("area", ""))
                break
        if not m:
            continue
        l, t2 = int(m.group(1)), int(m.group(2))
        if snap(l, 2) != l or snap(t2, 2) != t2:
            odd += 1
    print("gate re-phasing: %d of %d .UI file roots sit at an ODD design "
          "origin (q=2), i.e. their whole subtree changes phase under the "
          "candidate; the other %d are already on the lattice and cannot move."
          % (odd, len(files), len(files) - odd))
    return odd, len(files)


def mode_gates(verbose):
    gate_rephase_delta()
    return 0


# ------------------------------------------------------------------- proof

def mode_proof(verbose):
    print("THEOREM  q | a  =>  R(a+d) - R(a) == R(d)   [R = floor(v*f + 0.5)]")
    fails = 0
    checked = 0
    for f in (1.0, 1.25, 1.5, 2.0, 2.5, 3.0):
        q = denom(f)
        for a in range(-400, 4001):
            if a % q:
                continue
            for d in range(-400, 1201):
                checked += 1
                if R(a + d, f) - R(a, f) != R(d, f):
                    fails += 1
                    if fails < 4:
                        print("   FAIL f=%s a=%d d=%d" % (f, a, d))
        print("   f=%-5s q=%d   exhausted a in [-400,4000] on the lattice, "
              "d in [-400,1200]" % (f, q))
    print("   %d pairs checked, %d failures" % (checked, fails))

    print("\nINTEGER-TIER NO-OP, by construction:")
    for f in (2.0, 3.0):
        q = denom(f)
        bad = sum(1 for v in range(-2000, 6001) if snap(v, q) != v)
        print("   f=%-4s q=%d   snap(v,q) != v for %d of 8001 integers  -> "
              "lRef == l IDENTICALLY, so newW/newH/rootDesign* are the "
              "shipping expressions verbatim" % (f, q, bad))

    print("\nAND newW == R(w,f) UNDER THE SNAP, exhaustively:")
    for f in (1.5, 2.0, 3.0):
        q = denom(f)
        bad = 0
        for l in range(-400, 4001):
            ls = snap(l, q)
            for w in (1, 2, 3, 7, 33, 74, 133, 235, 351, 538, 880):
                if R(ls + w, f) - R(ls, f) != R(w, f):
                    bad += 1
        print("   f=%-4s  %d disagreements" % (f, bad))
    return 1 if fails else 0


def mode_blast(a):
    """emu_panel_anchor.py --blast, for this candidate. The named acceptance
    test: the 2400x1600 f=2.0 capture is the USER-CONFIRMED shipping tier and a
    candidate that moves ANY panel there is rejected without a build."""
    path, W, H, f = a.blast[0], int(a.blast[1]), int(a.blast[2]), float(a.blast[3])
    caps = EPA.parse_capture(path)
    for law in ("len", "snap"):
        moved = []
        for wid, (d, lg) in sorted(caps.items()):
            base = place(wid, *d, W, H, f, "cur")[0]
            cand = place(wid, *d, W, H, f, law)[0]
            if base != cand:
                moved.append((wid, base, cand))
        print("%d panels move of %d   (%dx%d f=%s, law %s vs cur)"
              % (len(moved), len(caps), W, H, f, law))
        for wid, b, c in moved:
            print("   MOVES 0x%08X %s -> %s" % (wid, b, c))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--blast", nargs=4, metavar=("LOG", "W", "H", "F"))
    ap.add_argument("--corpus", action="store_true")
    ap.add_argument("--contract", action="store_true")
    ap.add_argument("--dash", action="store_true")
    ap.add_argument("--gates", action="store_true")
    ap.add_argument("--proof", action="store_true")
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args()
    ran = 0
    if a.blast:
        print("\n" + "=" * 78)
        print("BLAST")
        print("=" * 78)
        mode_blast(a)
        ran = 1
    for name in ("proof", "corpus", "contract", "dash", "gates"):
        if getattr(a, name):
            ran = 1
            print("\n" + "=" * 78)
            print(name.upper())
            print("=" * 78)
            globals()["mode_" + name](a.verbose)
    if not ran:
        ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
