r"""gate_offset_parity.py - THE OFFSET-PARITY LAW, machine-checked (#152).

⛔ WHAT THIS LAW IS, AND WHY IT DESERVES A GATE RATHER THAN A PARAGRAPH.

`_tests\REGRESSION.md` #152 states it in closed form:

> For `f = p/q` in lowest terms, edge-derived rounding preserves a child's 1x
> offset `d` from its frame **iff `q | d`**, because
> `round((t+d)f) - round(tf) == df` exactly when `df` is an integer, and
> otherwise depends on the **parity of the frame's own coordinate `t`**.
> At **f=1.5, q=2: even offsets always survive, odd offsets are a lottery.**
> At an integer factor `q=1`, so every offset survives - which is the entire
> reason 2x and 3x have never shown any defect in this family.

It is the only rule in this project that names the FAILING AXIS in advance, and
it called all three measured panels right before anything was looked at:

    advisor faces     offset (2,1)   x even safe, y odd fails   user: "high"
    My Sim portraits  offset (3,2)   x odd fails, y even safe   user: "left"
    advisor detail    offset (2,2)   both even, never fails     correct at all tiers

Until now it lived only in prose. A law that is written down but never
evaluated cannot tell you that the NEXT panel is about to break, and #152 was
found the expensive way - three separate user reports - when the corpus could
have been asked directly.

────────────────────────────────────────────────────────────────────────────────
FOUR PARTS, in increasing order of how much they can be wrong about

  A  THE THEOREM      the closed form vs its own definition, by exhaustion over
                      t in [-2048,2048] x d in [-96,96] x f in {1,1.5,2,3}.
                      This part cannot be wrong; it is arithmetic.
  B  THE FIXTURES     the three MEASURED panels above. The gate must predict the
                      axis the user reported. If it cannot reproduce a defect
                      that was seen on a screen, the law is not calibrated and
                      parts C and D are decoration. FATAL on mismatch.
  C  THE CENSUS       every parent->child offset in the shipped `.UI` corpus,
                      counted per tier. **f=2 and f=3 must read EXACTLY ZERO.**
                      Not approximately - q=1 there, so every offset survives,
                      and a single nonzero means the model is broken (law 88).
  D  THE SEATED       the pairs where a dying offset can actually be SEEN.
     INSETS

────────────────────────────────────────────────────────────────────────────────
⛔ PART D EXISTS BECAUSE THE OBVIOUS FILTER IS THE WRONG ONE, TWICE OVER.

First attempt: parent->child edges whose offset dies. At f=1.5, q=2, and roughly
half of all integers are odd, so that is **3825 of 5635 edges - 67.9% of the
corpus**. A "finding" that names two thirds of everything is a population, not a
triage list.

Second attempt: narrow it to edges where BOTH parent and child bind `image=`.
**It recovered ZERO of the seven measured advisor faces.** Two reasons, and both
are recorded in #152 and were read past:

  1. The faces are `GZWinGen` **SIBLINGS** of their `GZWinBtn` frames, not
     children - `parent->child` is the wrong relation entirely. Measured in
     `T-00000000_G-96a006b0_I-4a160034.ui`: face 0x0A15C7D8 at abs (479,649)
     48x52, frame 0xCA15C7CF at abs (477,648) 55x94, both at depth 1. Offset
     (2,1) is a difference between two SIBLING absolute origins.
  2. The face binds **no art at all** in the `.UI` - its portrait is supplied at
     runtime. Requiring the inset to be art-bound excludes the very case the
     law was derived from.

So the relation that works is CONTAINMENT, derived from the one measured case:
a window B strictly inset inside a window A, where **A** is art-bound (A is what
provides the visible aperture), whatever their tree relationship. That recovers
7 of 7 faces, and the gate ASSERTS it - a filter that cannot see the defect it
was built from is not a filter.

⚠ THE BAND IS A VISIBILITY HEURISTIC AND IS LABELLED AS ONE. The law does not
care about magnitude: an odd offset dies whether it is 1 or 401. What magnitude
changes is whether anyone can SEE it - one pixel on a 2px inset is half the
inset; one pixel on a 400px layout offset is nothing. The band defaults to 3
because that is what the MEASURED cases need: the shipped seats are all (2,1)
and My Sim is (3,2). Widening it does not find more defects, it finds more
population - 10559 contained pairs exist and 7605 carry a dying offset.

⚠ AND AN ENTRY IS STILL ONLY A HYPOTHESIS. It is a window that CAN slip a pixel
inside its aperture at 1.5x, not one that does. `build_selective_safe.py`'s
`ADVISOR_FACE_SEATS` already repairs seven of them by seating each on its
frame's flood-filled art aperture; those are read out of the shipped table and
listed as REPAIRED rather than assumed away. STATIC DEFECT = HYPOTHESIS.

    python gate_offset_parity.py [--top N] [--tier 1.5] [--band N]

Offline, read-only.
"""
import os
import re
import sys

import scale_rules as SR
from scale_rules import out

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(os.path.dirname(HERE))
UI_DIR = os.path.join(TOOLS, "uiscripts", "extracted")
SEL_BUILDER = os.path.join(TOOLS, "selective-safe", "build_selective_safe.py")

ATTR = re.compile(r'(\w+)=("[^"]*"|\{[^}]*\}|\([^)]*\)|\S+)')
TAG = re.compile(r"<(/?)(LEGACY|CHILDREN)([^>]*)>")
RECT = re.compile(r"\((-?\d+),(-?\d+),(-?\d+),(-?\d+)\)")
IMG = re.compile(r"\{([0-9a-fA-F]+),([0-9a-fA-F]+)\}")

FAILS = []
CHECKS = [0]


def ck(name, cond, detail=""):
    CHECKS[0] += 1
    if not cond:
        FAILS.append("%s  %s" % (name, detail))
    return cond


# ── A. the theorem ────────────────────────────────────────────────────────────

def part_a():
    n = 0
    for f in (1.0, 1.5, 2.0, 3.0):
        p, q = SR.pq(f)
        for d in range(-96, 97):
            # THE DEFINITION: the offset survives iff it is the same for EVERY
            # frame coordinate t, and equal to the exact scaled offset d*p/q.
            brute = all(SR.offset_at(t, d, f) * q == d * p
                        for t in range(-2048, 2049))
            ck("A theorem f=%s d=%d" % (f, d), brute == SR.offset_survives(d, f),
               "closed=%s brute=%s" % (SR.offset_survives(d, f), brute))
            n += 1
    out("  A  closed form == definition, by exhaustion   %5d (d,f) pairs "
        "x 4097 frames" % n)


# ── B. the measured fixtures ──────────────────────────────────────────────────

FIXTURES = [
    # (panel, 1x offset, tier, expected dying axes, the user's own word)
    ("advisor faces (7 x 2 scripts)", (2, 1), 1.5, ("y",), "high"),
    ("My Sim portraits (21-face grid)", (3, 2), 1.5, ("x",), "left"),
    ("advisor detail page", (2, 2), 1.5, (), "correct at every tier"),
    ("advisor faces at 2x", (2, 1), 2.0, (), "never reported at 2x"),
    ("My Sim portraits at 3x", (3, 2), 3.0, (), "never reported at 3x"),
]


def part_b():
    for name, off, f, want, word in FIXTURES:
        got = SR.dying_axes(off[0], off[1], f)
        ok = ck("B fixture %s" % name, got == want,
                "offset %s at f=%s predicted %s, MEASURED %s (user: '%s')"
                % (off, f, got, want, word))
        out("     %-34s off=%-6s f=%-4s -> %-9s  %s  (user: \"%s\")"
            % (name, "%d,%d" % off, f, str(got) if got else "(none)",
               "ok" if ok else "MISMATCH", word))
    out("  B  %d measured #152 fixtures reproduced" % len(FIXTURES))


# ── C/D. the corpus ───────────────────────────────────────────────────────────

def walk(text):
    res, depth = [], 0
    for m in TAG.finditer(text):
        close, tag, body = m.group(1), m.group(2), m.group(3)
        if tag == "CHILDREN":
            depth += -1 if close else 1
            continue
        res.append((depth, dict(ATTR.findall(body))))
    return res


def nodes_abs(text):
    """-> [(depth, attrs, absL, absT, absR, absB)] for every node with an area."""
    res = []
    stack = {0: (0, 0)}
    for depth, a in walk(text):
        m = RECT.match(a.get("area", ""))
        if not m:
            continue
        l, t, r, b = (int(x) for x in m.groups())
        pl, pt = stack.get(depth, (0, 0))
        stack[depth + 1] = (pl + l, pt + t)
        res.append((depth, a, pl + l, pt + t, pl + r, pt + b))
    return res


def child_edges(text):
    """-> [(parentAttrs, childAttrs, dx, dy)] for every parent->child edge.

    Part C's population. dx/dy are the child's PARENT-RELATIVE design offset,
    which is exactly the `d` in the law.
    """
    res, stack = [], {}
    for depth, a in walk(text):
        m = RECT.match(a.get("area", ""))
        if not m:
            continue
        l, t, _r, _b = (int(x) for x in m.groups())
        stack[depth] = a
        par = stack.get(depth - 1)
        if par is not None:
            res.append((par, a, l, t))
    return res


def inset_pairs(text):
    """-> [(hostAttrs, insetAttrs, dx, dy)] : B strictly inset inside art-bound A.

    ⛔ CONTAINMENT, NOT PARENTAGE. Derived from the one measured case (#152): the
    advisor face and its frame are SIBLINGS, so any relation keyed on the tree
    misses them. `A` must be art-bound because A is what supplies the visible
    aperture the inset has to register against; `B` need not be, because the
    advisor portrait is supplied at runtime and binds no `image=` in the `.UI`.
    """
    ns = nodes_abs(text)
    res = []
    for _di, ai, al, at, ar, ab in ns:
        if not IMG.search(ai.get("image", "")):
            continue
        for _dj, aj, bl, bt, br, bb in ns:
            if aj is ai:
                continue
            if not (bl >= al and bt >= at and br <= ar and bb <= ab):
                continue
            if (br - bl) >= (ar - al) and (bb - bt) >= (ab - at):
                continue                       # same size: not an inset
            res.append((ai, aj, bl - al, bt - at))
    return res


def repaired_ids():
    """The inset ids the shipped builder already SEATS (#152).

    Read out of `build_selective_safe.py::ADVISOR_FACE_SEATS` rather than
    retyped, so this gate cannot claim a repair the build no longer performs.
    If the table is renamed or removed this returns empty and the REPAIRED
    column goes to zero - visibly, rather than silently.
    """
    ids = set()
    if not os.path.exists(SEL_BUILDER):
        return ids
    text = open(SEL_BUILDER, encoding="utf-8", errors="replace").read()
    m = re.search(r"ADVISOR_FACE_SEATS\s*=\s*\[(.*?)\]", text, re.S)
    if not m:
        return ids
    for row in re.finditer(r"\(\s*0x([0-9A-Fa-f]{8})\s*,", m.group(1)):
        ids.add("0x" + row.group(1).lower())
    return ids


REPAIRED = repaired_ids()


def census(f):
    """Part C: parent->child offsets that die at f."""
    edges, dying = 0, 0
    for fn in sorted(os.listdir(UI_DIR)):
        if not fn.lower().endswith(".ui"):
            continue
        text = open(os.path.join(UI_DIR, fn), encoding="latin-1").read()
        for _par, _kid, dx, dy in child_edges(text):
            edges += 1
            if SR.dying_axes(dx, dy, f):
                dying += 1
    return edges, dying


def seated(f, band):
    """Part D: contained insets whose offset dies at f, within the visibility band.

    -> (total_pairs, dying_pairs, [rows within band])
    """
    total, dying, rows = 0, 0, []
    for fn in sorted(os.listdir(UI_DIR)):
        if not fn.lower().endswith(".ui"):
            continue
        text = open(os.path.join(UI_DIR, fn), encoding="latin-1").read()
        for host, ins, dx, dy in inset_pairs(text):
            total += 1
            axes = SR.dying_axes(dx, dy, f)
            if not axes:
                continue
            dying += 1
            if max(abs(dx), abs(dy)) <= band:
                iid = str(ins.get("id", "-")).lower()
                rows.append((fn, str(host.get("id", "-")), iid, dx, dy, axes,
                             iid in REPAIRED))
    return total, dying, rows


def main():
    top = int(sys.argv[sys.argv.index("--top") + 1]) if "--top" in sys.argv else 25
    tier = float(sys.argv[sys.argv.index("--tier") + 1]) \
        if "--tier" in sys.argv else 1.5
    # 3 = the largest component of any MEASURED seat ((2,1) shipped, (3,2) My
    # Sim). A threshold from the controls, not from taste.
    band = int(sys.argv[sys.argv.index("--band") + 1]) \
        if "--band" in sys.argv else 3

    out("gate_offset_parity.py   -   the #152 law, evaluated\n")
    part_a()
    part_b()

    if not os.path.isdir(UI_DIR):
        out("\n[STOP] no `.UI` corpus at %s - a REFUSAL, not a pass." % UI_DIR)
        return 1
    files = [x for x in os.listdir(UI_DIR) if x.lower().endswith(".ui")]
    if not files:
        out("\n[STOP] 0 `.UI` files - a REFUSAL, not a pass.")
        return 1

    cen = {}
    for f in (1.0, 1.5, 2.0, 3.0):
        cen[f] = census(f)

    out("\n  C  corpus census over %d .UI files, %d parent->child edges\n"
        % (len(files), cen[1.0][0]))
    out("     %-6s %4s %12s   %s" % ("factor", "q", "offsets die", ""))
    for f in (1.0, 2.0, 3.0, 1.5):
        q = SR.pq(f)[1]
        tag = "  <- INTEGER CONTROL: q=1, must be 0" if f in (2.0, 3.0) else (
            "  <- stock identity, must be 0" if f == 1.0
            else "  <- the fractional tier (a POPULATION, not a defect list)")
        out("     f=%-4s %4d %12d%s" % (f, q, cen[f][1], tag))

    for f in (1.0, 2.0, 3.0):
        if cen[f][1]:
            out("\n[STOP] CONTROL FAILED: %d offsets die at f=%s, where q=1 and "
                "every offset\nmust survive. The model is wrong and nothing it "
                "says about 1.5x is usable." % (cen[f][1], f))
            return 1

    ins = {}
    for f in (1.0, 1.5, 2.0, 3.0):
        ins[f] = seated(f, band)

    total, dying, rows = ins[tier]
    rep = [e for e in rows if e[6]]
    cand = [e for e in rows if not e[6]]
    out("\n  D  seated insets: %d contained pairs with an art-bound host; "
        "%d carry a\n     dying offset at f=%s; %d of those are inside the "
        "visibility band (<=%dpx)."
        % (total, dying, tier, len(rows), band))

    # ⛔ THE FILTER'S OWN POSITIVE CONTROL. If the seven MEASURED advisor faces
    # are not in this set, the filter is looking at the wrong relation - which
    # is exactly what happened to its first two revisions.
    got = set(e[2] for e in rows)
    missing = sorted(REPAIRED - got)
    ck("D recovers the measured #152 faces", not missing and bool(REPAIRED),
       ("seat table empty - could not read ADVISOR_FACE_SEATS"
        if not REPAIRED else
        "%d of %d shipped seats NOT recovered: %s"
        % (len(missing), len(REPAIRED), ", ".join(missing))))
    out("     POSITIVE CONTROL: %d of %d shipped ADVISOR_FACE_SEATS recovered "
        "by the filter" % (len(REPAIRED) - len(missing), len(REPAIRED)))

    for f in (1.0, 2.0, 3.0):
        ck("D integer control f=%s" % f, not ins[f][2],
           "%d seated insets die at f=%s where q=1" % (len(ins[f][2]), f))
    out("     INTEGER CONTROL: %d at f=1, %d at f=2, %d at f=3 (all must be 0)"
        % (len(ins[1.0][2]), len(ins[2.0][2]), len(ins[3.0][2])))

    by_axis = {"x": 0, "y": 0, "xy": 0}
    for e in cand:
        by_axis["xy" if len(e[5]) == 2 else e[5][0]] += 1
    out("     predicted failing axis across %d candidates: %d x-only, %d y-only,"
        " %d both" % (len(cand), by_axis["x"], by_axis["y"], by_axis["xy"]))

    if rep:
        out("\n  REPAIRED - named in build_selective_safe.py::ADVISOR_FACE_SEATS,"
            "\n  seated on the frame's flood-filled art aperture:")
        for e in rep[:8]:
            out("     %s  host=%-12s inset=%-12s off=(%3d,%3d)  dies: %s"
                % (e[0][-14:-3], e[1], e[2], e[3], e[4], ",".join(e[5])))

    if cand:
        out("\n  CANDIDATES at f=%s - insets inside an art aperture whose offset "
            "does not\n  survive. A candidate is a HYPOTHESIS: it CAN slip one "
            "pixel inside its\n  aperture; only a screen can say whether it "
            "does." % tier)
        for e in sorted(cand, key=lambda e: max(abs(e[3]), abs(e[4])))[:top]:
            out("     %s  host=%-12s inset=%-12s off=(%3d,%3d)  dies: %s"
                % (e[0][-14:-3], e[1], e[2], e[3], e[4], ",".join(e[5])))
        if len(cand) > top:
            out("     ... %d more (--top N)" % (len(cand) - top))
    edges = cen[1.0][0]

    out("\n  %d checks, %d FAILED" % (CHECKS[0], len(FAILS)))
    if FAILS:
        out("\n[STOP] the law does not reproduce its own measured fixtures:")
        for x in FAILS[:20]:
            out("   " + x)
        return 1
    out("\nThe law holds, reproduces all %d measured fixtures, and reads EXACTLY "
        "ZERO at\nf=1, f=2 and f=3 over %d corpus edges - which is the control, "
        "because q=1\nthere and no offset can die." % (len(FIXTURES), edges))
    return 0


sys.exit(main())
