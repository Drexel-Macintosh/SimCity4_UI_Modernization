r"""gate_tiled_seam.py - WHERE THE TILE BOUNDARY LANDS (#160).

⛔ WHY THIS EXISTS, AND WHAT EVERY OTHER GATE IN THIS FOLDER WAS DOING INSTEAD.

`gate_art_vs_window.py:195` reads, in full:

    if blt == "tiled":
        continue                      # repeats: always covers

`gate_btn_undercover.py`, `gate_imagerect_vs_art.py` and `gate_tp_bmp_fit.py`
all skip `blttype=tiled` on the same grounds. THE GROUNDS ARE TRUE AND THEY ARE
NOT THE QUESTION. Tiling does always cover - a repeating source can never leave
an uncovered band, so "does the art cover the window" is answered `yes` before
it is asked, and 169 tiled nodes across 78 distinct window shapes were being
certified by a question that could not fail.

What tiling can still get wrong is WHERE THE SEAM IS. The engine is
src-follows-dst: it repeats the source across the destination, so a tile
boundary falls at every `k * artExtent` inside the window. That boundary is a
visible feature of the picture - it is where the pattern restarts, and on the
god-mode tool column it is literally a white line. #160 is the whole argument:

    god toolbar strip 0xc991eda8, art {46a006b0,14415876}, blttype=tiled
                 window        art          delta
      1x         74x351        74x351        0
      2x        148x702       148x702        0
      1.5x      111x527       111x528       +1     <- USER-REPORTED
        "There's a break in the white line on the left that is
         not in 2x or stock"

`ScaleDim(351,1.5)` = 526.5 -> 527, then `CellUnit(351)=3` snapped it UP to 528
while the window scaled by a plain round to 527. One pixel, one tier, and it was
found by a user's eye rather than by any of the six gates that had looked at
that file.

────────────────────────────────────────────────────────────────────────────────
THE MODEL

For each `blttype=tiled` node: the 1x picture magnified by f is the picture the
tier is SUPPOSED to be showing, so boundary k belongs at `R(k * art1x, f)`.
The tier actually puts it at `k * artF`. The difference is the seam's
displacement, and it ACCUMULATES: the k-th boundary is off by roughly
`k * (artF - art1x*f)`.

THREE PASS/FAIL METRICS, and one CHARACTERISATION that is deliberately not one:

  T2 REPEAT COUNT   (fail) the window must show the same number of repeats it
                    showed at 1x. A count change is a seam appearing or
                    vanishing.
  T4 SHEET SIZING   (fail) `artF == R(art1x, f)`. The tiled contract in one
                    line: nothing divides a tiled sheet, so it must be sized by
                    the plain scale of its 1x size. This is #160 exactly.
  T5 NEW OVERHANG   (fail) `artF <= winF` wherever `art1x <= win1x`. The sheet
                    outgrowing its window at one tier only means its far edge -
                    its border row - is clipped away.
  T1 SEAM DRIFT     (REPORT ONLY, and the reason matters) how far each boundary
                    wanders from the magnified-1x reference. At f=3/2 a sheet
                    of ODD 1x extent has period `art1x*1.5`, which is not an
                    integer, so the period MUST round and the drift accumulates
                    by half a pixel per tile. THAT IS INHERENT TO THE TIER, not
                    a defect, and no sheet size can remove it. Counting it as a
                    failure would condemn the best possible build, which is a
                    broken model rather than a finding (law 88).

⚠ A METRIC THIS GATE HAD AND THREW AWAY. Its first revision carried a
"last-tile phase" check comparing `lastTile(winF, artF)` against
`R(lastTile(win1x, art1x), f)`. It fired 10 times at 1.5x and zero times at 2x
and 3x, which LOOKS like a defect metric passing its control. It was measuring
the WINDOW's own edge-derived rounding (#161) a second time and calling it a
seam: `R(351,1.5)=527` but the window at absT=185 is `R(536,1.5)-R(185,1.5)=526`,
so the expectation was unreachable by construction. Passing the integer-tier
control is necessary and NOT sufficient - a metric can read zero at 2x and 3x
and still be measuring something other than what it names.

────────────────────────────────────────────────────────────────────────────────
THE CONTROLS - and this gate is only worth reading because of them

  f=2, f=3   T2/T4/T5 AND THE T1 DRIFT MUST ALL READ EXACTLY ZERO, after the
             f=1 stock baseline is subtracted per (node, metric, AXIS) - not
             per node, because sixteen of these sheets already exceed their
             window at 1x and a per-node subtraction hides a fresh failure on
             the other axis (measured: it hid four).
             This is a proof, not a measurement:
             `Upscale2x.cs::ScaleDim` returns BEFORE the cell snap
             at an integer factor, so `artF == art1x*f` exactly, and
             `k*art1x*f == R(k*art1x, f)` because the product is already whole.
             If an integer tier reports anything, the model is wrong and nothing
             it says about 1.5x is usable (law 88).

  --pre160   REPRODUCE THE CLOSED DEFECT. Re-sizes every tiled sheet the way
             Upscale2x did before #160 (cell-snapped) instead of reading
             `no-snap.txt`, and the gate must go RED and NAME the god toolbar
             strip. A gate that is green both before and after a known fix has
             not reproduced anything and is not coverage. THIS RUN IS THE
             POSITIVE CONTROL AND IT IS MANDATORY BEFORE QUOTING A CLEAN RESULT.

────────────────────────────────────────────────────────────────────────────────
⚠ ONE NUMBER IN #160'S WRITE-UP DOES NOT SURVIVE THIS MODEL, AND IT MATTERS

`_tests\REGRESSION.md` #160 records the 1.5x window of the god toolbar strip as
**527**, i.e. `R(351,1.5)`. That is the SIZE-DERIVED answer. The strip's `.UI`
gives it a `<CHILDREN>` block containing GZWinBtn tools, so `GetChildCount()`
is not zero, #148's leaf branch cannot fire, and the sweep gives it the
EDGE-DERIVED extent from its absolute origin 185:

    R(185+351, 1.5) - R(185, 1.5)  =  804 - 278  =  526

So the shipped 1.5x sheet is 527 tall and its window is 526 - the sheet's last
row is never drawn. That is the same SHAPE as #160 (art exceeds window, 1.5x
only) arriving by a different route, and it is what T5 reports below. It is a
STATIC PREDICTION, not a sighting: nothing on screen has disagreed yet, and the
house rule is that a static defect is a hypothesis until it does.

    python gate_tiled_seam.py [--top N] [--pre160] [--all] [-v]

Offline, read-only. Art sizes are MEASURED from the PNG each tier ships. Window
sizes are MODELLED exactly as `UiSpike.cpp::ScaleSubtree` does it: edge-derived
in the parent's absolute design frame for CONTAINERS (#161), size-derived for
LEAVES (#148). Getting that split wrong is what made this gate's first revision
report a defect that was not there.
"""
import os
import re
import struct
import sys

import scale_rules as SR
from scale_rules import out

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(os.path.dirname(HERE))
SEL = os.path.join(TOOLS, "selective-safe")
STAGE2X = os.path.join(SEL, "stage")
STAGE15 = os.path.join(SEL, "stage-15x")
STAGE3X = os.path.join(SEL, "stage-3x")

# (factor, staged art dir, divisor applied to the measured PNG size)
# 1x is derived as art2x/2 - the 2x pass is an EXACT doubling, so that is a
# division and not an estimate. Same construction as gate_art_vs_window.py.
TIERS = [(1.0, STAGE2X, 2), (2.0, STAGE2X, 1), (3.0, STAGE3X, 1),
         (1.5, STAGE15, 1)]

ATTR = re.compile(r'(\w+)=("[^"]*"|\{[^}]*\}|\([^)]*\)|\S+)')
TAG = re.compile(r"<(/?)(LEGACY|CHILDREN)([^>]*)>")
RECT = re.compile(r"\((-?\d+),(-?\d+),(-?\d+),(-?\d+)\)")
IMG = re.compile(r"\{([0-9a-fA-F]+),([0-9a-fA-F]+)\}")

ROLES = SR.Roles()


def png_size(path):
    with open(path, "rb") as fh:
        head = fh.read(24)
    if len(head) < 24 or head[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    return struct.unpack(">II", head[16:24])


def art_index(stage_dir):
    idx = {}
    if not os.path.isdir(stage_dir):
        return idx
    for fn in os.listdir(stage_dir):
        if not fn.lower().endswith(".png"):
            continue
        m = re.search(r"G-0x([0-9a-fA-F]+)_I-0x([0-9a-fA-F]+)", fn)
        if not m:
            continue
        sz = png_size(os.path.join(stage_dir, fn))
        if sz:
            idx[SR.tgi_key(m.group(1), m.group(2))] = sz
    return idx


ART = {}
for _f, _d, _div in TIERS:
    _idx = art_index(_d)
    ART[_f] = {k: (w // _div, h // _div) for k, (w, h) in _idx.items()}

# ⛔ A SHEET IS ONLY COMPARED IF EVERY TIER CAN PRICE IT. gate_art_vs_window.py
# paid for this once: deriving 1x by halving inside each tier's own pass dropped
# odd-sized (LEFT1X) sheets out of the f=1 scan while keeping them in the f=2
# scan, and 32 phantom "new at f=2" shortfalls appeared - the control failing
# for a bookkeeping reason. Build the comparable set ONCE.
USABLE = {}
for _k, (_w2, _h2) in ART[2.0].items():
    if _w2 % 2 or _h2 % 2:
        continue
    if _k not in ART[1.5] or _k not in ART[3.0]:
        continue
    USABLE[_k] = {f: ART[f][_k] for f, _, _ in TIERS}


def walk(text):
    res, depth = [], 0
    for m in TAG.finditer(text):
        close, tag, body = m.group(1), m.group(2), m.group(3)
        if tag == "CHILDREN":
            depth += -1 if close else 1
            continue
        res.append((depth, dict(ATTR.findall(body))))
    return res


def tiled_nodes(text):
    """-> [(idx, attrs, absL, absT, w, h, is_leaf)] per blttype=tiled art node.

    The `.UI` attribute is AUTHORITATIVE here, not `tiled.txt`: the list is
    exclusion-biased by construction (`find_tiled.py` drops any TGI also drawn
    as a button or a 9-slice), so a node that literally says `blttype=tiled` is
    a tiled blit whatever the list decided about the sheet.

    ⛔ is_leaf DECIDES WHICH SIZING RULE APPLIES (#148) and is therefore
    load-bearing, not decoration. A node is a leaf iff no node follows it at a
    greater `<CHILDREN>` depth - the static analogue of the DLL's
    `GetChildCount() == 0`.
    """
    nodes = walk(text)
    res = []
    stack = {0: (0, 0)}
    for i, (depth, a) in enumerate(nodes):
        m = RECT.match(a.get("area", ""))
        if not m:
            continue
        l, t, r, b = (int(x) for x in m.groups())
        pl, pt = stack.get(depth, (0, 0))
        stack[depth + 1] = (pl + l, pt + t)
        if str(a.get("blttype", "")).strip('"') != "tiled":
            continue
        if not IMG.search(a.get("image", "")):
            continue                    # no sheet bound: nothing to seam
        is_leaf = not (i + 1 < len(nodes) and nodes[i + 1][0] > depth)
        res.append((i, a, pl + l, pt + t, r - l, b - t, is_leaf))
    return res


def art_for(key, f, pre160):
    """The sheet size this tier ships (or WOULD ship under the pre-#160 rule)."""
    if not pre160:
        return USABLE[key][f]
    w1, h1 = USABLE[key][1.0]
    # The pre-#160 upscaler knew nothing about tiled sheets: full CellUnit {3,4}
    # snap on both axes. Reproduced from Upscale2x.cs::ScaleDim, no_snap=False.
    return (SR.scale_dim(w1, f, SR.CELL_COUNTS, False),
            SR.scale_dim(h1, f, SR.CELL_COUNTS, False))


FAIL_METRICS = ("T2", "T4", "T5")

#: How many DISTINCT window shapes each tiled sheet is bound to.
#: ⛔ THIS IS THE REASON T5 IS HARD TO CURE AND THE GATE SAYS SO. The offline
#: art pipeline sizes a sheet once, position-independently, as `R(w1x, f)`. A
#: CONTAINER's window is edge-derived, so its extent depends on WHERE it sits.
#: For a sheet bound to exactly one window the two can be made to agree; for a
#: sheet bound to six windows at six origins (13d14ca0) no single size can
#: satisfy them all, and a cure has to move the WINDOW or the draw, not the PNG.
BINDINGS = {}


def scan(f, pre160=False, ui_filter=None):
    """-> (checked, findings, drift) ; findings are FAILURES, drift is T1.

    ⛔ FINDINGS ARE KEYED BY (file, node, metric, AXIS), not by node. The
    sibling gates subtract their stock baseline per NODE, which is right for
    them and would be wrong here: sixteen of these sheets are already wider or
    taller than their window AT 1x (stock ships a 74px sheet in a 73px window),
    so a per-node subtraction would swallow the whole node and hide a fresh
    failure on the OTHER axis. Measured: it hid four.
    """
    checked, findings, drift, leaves = 0, {}, [], [0, 0]
    for fn in sorted(os.listdir(STAGE2X)):
        if not fn.lower().endswith(".ui"):
            continue
        if ui_filter and ui_filter not in fn.lower():
            continue
        text = open(os.path.join(STAGE2X, fn), encoding="latin-1").read()
        for idx, a, aL, aT, w, h, is_leaf in tiled_nodes(text):
            mi = IMG.search(a.get("image", ""))
            key = SR.tgi_key(mi.group(1), mi.group(2))
            if key not in USABLE or w <= 0 or h <= 0:
                continue
            aw1, ah1 = USABLE[key][1.0]
            awF, ahF = art_for(key, f, pre160)
            if aw1 <= 0 or ah1 <= 0:
                continue
            checked += 1
            leaves[0 if is_leaf else 1] += 1
            info = (a, key, (w, h), (aw1, ah1), (awF, ahF), is_leaf)

            def hit(metric, axis, why, _i=info, _f=findings, _fn=fn, _x=idx):
                _f[(_fn, _x, metric, axis)] = (_i, why)

            for axis, o, ext, a1, aF in (("x", aL, w, aw1, awF),
                                         ("y", aT, h, ah1, ahF)):
                # #148: leaves take their SIZE, containers their EDGES.
                win1, winF = ext, SR.window_extent(o, ext, f, is_leaf)

                # T4 - the tiled contract, one line (#160)
                want = SR.scale_round(a1, f)
                if aF != want:
                    hit("T4", axis, "%s sheet %d != R(%d,%s)=%d  (%+d px)"
                        % (axis, aF, a1, f, want, aF - want))

                # T5 - the sheet outgrew its window at this tier
                if aF > winF:
                    hit("T5", axis, "%s sheet %d > window %d  (%+d px clipped; "
                        "1x was %d vs %d)%s"
                        % (axis, aF, winF, aF - winF, a1, win1,
                           "" if BINDINGS.get(key, 0) > 1
                           else "   [sheet bound to ONE window only]"))

                # T2 - the number of repeats must not change
                c1, cF = SR.tile_count(win1, a1), SR.tile_count(winF, aF)
                if c1 != cF:
                    hit("T2", axis, "%s repeats %d -> %d" % (axis, c1, cF))

                # T1 - REPORT ONLY. Inherent whenever art1*f is not whole.
                inherent = (a1 * f) != int(a1 * f)
                for k, pos, exp, dr, kind in SR.seam_drift(a1, aF, f, winF):
                    if dr:
                        drift.append((fn, idx, key, axis, k, pos, exp, dr, kind,
                                      inherent))
    return checked, findings, drift, leaves


def counts(keys):
    c = dict((m, 0) for m in FAIL_METRICS)
    for k in keys:
        c[k[2]] += 1
    return c


def short(fn):
    """G/I short name. Two staged .UI files can share an INSTANCE and differ
    only by GROUP, so an instance-only label prints the same row twice and
    reads like a duplicate. Measured: {46a006b0,14015546} does exactly that."""
    m = re.search(r"G-0x([0-9a-fA-F]+)_I-0x([0-9a-fA-F]+)", fn)
    return "%s/%s" % (m.group(1)[-4:], m.group(2)) if m else fn


def show(findings, keys, top, label):
    out("\n%s" % label)
    shown = set()
    for k in sorted(keys)[:top]:
        (a, key, win, a1, aF, is_leaf), why = findings[k]
        node = (k[0], k[1])
        if node not in shown:
            out("   %s #%-4d id=%-12s tgi=%s  %s"
                % (short(k[0]), k[1], a.get("id", "-"), key,
                   "LEAF" if is_leaf else "CONTAINER"))
            out("        window %dx%d(1x)   sheet %dx%d(1x) -> %dx%d"
                % (win[0], win[1], a1[0], a1[1], aF[0], aF[1]))
            shown.add(node)
        out("        %s  %s" % (k[2], why))


def main():
    top = int(sys.argv[sys.argv.index("--top") + 1]) if "--top" in sys.argv else 12
    uif = sys.argv[sys.argv.index("--ui") + 1].lower() if "--ui" in sys.argv else None
    pre160 = "--pre160" in sys.argv
    verbose = "-v" in sys.argv

    if not USABLE:
        out("0 sheets priceable at 1x/1.5x/2x/3x - a REFUSAL, not a pass.")
        return 1
    out("gate_tiled_seam.py%s" % ("   [--pre160: PRE-FIX ART SIZING]" if pre160 else ""))
    out("%d sheets priceable at every tier; role lists: %d tiled, %d no-snap"
        % (len(USABLE), len(ROLES.tiled), len(ROLES.no_snap)))

    # The binding census must exist before the first scan formats a finding.
    for fn in sorted(os.listdir(STAGE2X)):
        if not fn.lower().endswith(".ui"):
            continue
        text = open(os.path.join(STAGE2X, fn), encoding="latin-1").read()
        for _, a, _, _, w, h, _ in tiled_nodes(text):
            mi = IMG.search(a.get("image", ""))
            k = SR.tgi_key(mi.group(1), mi.group(2))
            BINDINGS.setdefault(k, set()).add((w, h))
    for k in list(BINDINGS):
        BINDINGS[k] = len(BINDINGS[k])

    res = {}
    for f, _, _ in TIERS:
        res[f] = scan(f, pre160, uif)
    n1 = res[1.0][0]
    lv = res[1.0][3]
    if n1 == 0:
        out("\n0 tiled nodes checked - a REFUSAL, not a pass. Every other gate "
            "in this folder SKIPS these nodes; if this one sees none either, "
            "nothing is looking at them at all.")
        return 1

    out("\n%d tiled image-bound nodes checked per tier (of %d tiled nodes in "
        "the corpus)" % (n1, _tiled_total()))
    out("   %d LEAF (window = R(w,f), #148)   %d CONTAINER (edge-derived)\n"
        % (lv[0], lv[1]))
    stock = set(res[1.0][1])
    out("   raw = every failing (node, metric, axis); NEW = raw minus the stock "
        "baseline\n")
    out("   %-6s %6s %8s %8s   %s"
        % ("factor", "nodes", "raw", "NEW", "T1 drift (report only)"))
    for f in (1.0, 2.0, 3.0, 1.5):
        new = set(res[f][1]) - stock
        c = counts(new)
        inh = sum(1 for d in res[f][2] if d[9])
        avo = sum(1 for d in res[f][2] if not d[9])
        if f in (2.0, 3.0):
            tag = "  <- INTEGER CONTROL: NEW and drift must both be 0"
        elif f == 1.5:
            tag = "  <- the fractional tier"
        else:
            tag = "  <- stock reference, subtracted from every row"
        out("   f=%-4s %6d %8d %8d   %d inherent / %d avoidable%s"
            % (f, res[f][0], len(res[f][1]), len(new), inh, avo, tag))
        if new:
            out("          %s"
                % "  ".join("%s=%d" % (m, c[m]) for m in FAIL_METRICS if c[m]))

    # ⛔ THE DRIFT CONTROL IS SEPARATE AND JUST AS HARD. At an integer factor
    # artF == art1*f exactly and k*art1*f is already whole, so NO boundary can
    # move. A nonzero here is arithmetically impossible and condemns the model.
    for f in (2.0, 3.0):
        if res[f][2]:
            out("\n[STOP] CONTROL FAILED: f=%s moved %d tile boundary/ies. "
                "Impossible at an\ninteger factor - the model is wrong." % (f, len(res[f][2])))
            for d in res[f][2][:6]:
                out("     %s #%d %s seam#%d at %d, belongs at %d (%+d)"
                    % (short(d[0]), d[1], d[3], d[4], d[5], d[6], d[7]))
            return 1

    bad_int = []
    for f in (2.0, 3.0):
        for k in sorted(set(res[f][1]) - stock):
            bad_int.append((f, k))

    if bad_int:
        out("\n[STOP] CONTROL FAILED: an INTEGER tier produced %d failure(s) "
            "stock does not\nhave. At f=2 and f=3 ScaleDim returns before the "
            "cell snap and every product\nis already whole, so this is "
            "arithmetically impossible. The model is wrong\nand the 1.5x list "
            "is not evidence (law 88)." % len(bad_int))
        for f, k in bad_int[:8]:
            out("     f=%s %s #%d %s  %s"
                % (f, short(k[0]), k[1], k[2], res[f][1][k][1]))
        return 1

    new15 = sorted(set(res[1.5][1]) - stock)
    c15 = counts(new15)
    out("\nFAILURES at 1.5x that stock does not have : %d" % len(new15))
    out("   T2 repeat count %d   T4 sheet sizing %d   T5 new overhang %d"
        % (c15["T2"], c15["T4"], c15["T5"]))

    if verbose:
        d15 = [d for d in res[1.5][2]]
        out("\nT1 seam drift at 1.5x (REPORT ONLY - %d inherent, %d avoidable):"
            % (sum(1 for d in d15 if d[9]), sum(1 for d in d15 if not d[9])))
        for d in d15[:top]:
            out("   %s #%-4d %s %s seam#%d %-7s at %-5d belongs %-5d %+d px %s"
                % (short(d[0]), d[1], d[2], d[3], d[4], d[8],
                   d[5], d[6], d[7], "INHERENT" if d[9] else "AVOIDABLE"))

    if stock and (verbose or "--all" in sys.argv):
        show(res[1.0][1], sorted(stock), top,
             "stock (f=1) findings - NOT ours, subtracted from every row:")

    if pre160:
        # ⛔ THE POSITIVE CONTROL. The pre-#160 sizing MUST resurrect the defect,
        # on the sheet the USER named, via the metric that describes it (T4).
        god = SR.tgi_key("46a006b0", "14415876")
        hit = [k for k in new15
               if res[1.5][1][k][0][1] == god and k[2] == "T4"]
        out("")
        if not new15:
            out("[STOP] --pre160 produced NO 1.5x failures. The pre-fix art "
                "sizing is known\nto have shipped a visible defect on the god "
                "toolbar strip, so a gate that\ncannot see it here cannot see "
                "it anywhere. THIS GATE IS INERT.")
            return 1
        if not hit:
            out("[STOP] --pre160 fired, but not with T4 on {46a006b0,14415876} "
                "- the sheet\nthe user actually reported. It is reproducing "
                "something else.")
            show(res[1.5][1], new15, top, "what it did name:")
            return 1
        out("POSITIVE CONTROL OK: the pre-#160 art sizing puts %d failure(s) "
            "back on the\n1.5x list, including T4 on the god toolbar strip "
            "{46a006b0,14415876} that the\nuser reported as \"a break in the "
            "white line\", and the f=2 / f=3 controls\nstayed at zero "
            "throughout." % len(new15))
        show(res[1.5][1], new15, top, "reproduced 1.5x-only defects:")
        return 1

    out("\n[WARN] THE HONEST GAP, printed whatever the verdict. This gate prices "
        "%d of the\n%d tiled nodes in the corpus: the other %d bind no `image=` "
        "of their own (they\nare mostly clsid 0x89e1567c, which sources its "
        "sheet somewhere this parser\ncannot follow) and NOTHING in this folder "
        "looks at them. It is also blind to\nthe pattern INSIDE a tile - "
        "nearest-neighbour re-phasing, #162 - which is a\ndifferent instrument's "
        "job." % (n1, _tiled_total(), _tiled_total() - n1))

    if not new15:
        out("\nNo 1.5x-only FAILURE. Every priced tiled sheet is sized by the "
            "plain scale of\nits 1x size, still fits its window, and still shows "
            "the same number of repeats.\n\nRun --pre160 before quoting that: a "
            "gate that is green both before and after a\nknown fix has "
            "reproduced nothing and is not coverage.")
        return 0

    show(res[1.5][1], new15, top, "1.5x-ONLY FAILURES:")
    return 1


_TILED_N = [None]


def _tiled_total():
    """Every blttype=tiled node in the corpus, image-bound or not."""
    if _TILED_N[0] is None:
        n = 0
        for fn in sorted(os.listdir(STAGE2X)):
            if not fn.lower().endswith(".ui"):
                continue
            text = open(os.path.join(STAGE2X, fn), encoding="latin-1").read()
            for _, a in walk(text):
                if str(a.get("blttype", "")).strip('"') == "tiled":
                    n += 1
        _TILED_N[0] = n
    return _TILED_N[0]


sys.exit(main())
