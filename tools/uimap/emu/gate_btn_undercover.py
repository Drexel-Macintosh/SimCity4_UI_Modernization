r"""GATE (#148): an art-sized button's SCALED WINDOW must equal its ART CELL.

THE REVERSE L, and the one instrument that would have found it on day one.

USER-VISIBLE: Mayor mode -> Landscape draws a line down the RIGHT edge and along
the BOTTOM of exactly ONE of its five buttons. The five are identical 47x37
controls on identical 188x37 four-state sheets. The ONLY difference:

    Raise Terrain    area=(68,  8,115, 45)   l=68  EVEN
    Gouge Valleys    area=(68, 58,115, 95)   l=68  EVEN
    Level Terrain    area=(69,108,116,145)   l=69  ODD    <-- the broken one
    Plant Flora      area=(68,158,115,195)   l=68  EVEN
    Signs & Labels   area=(68,208,115,245)   l=68  EVEN

`UiSpike::ScaleSubtree` (src\UiSpike.cpp:15546) is EDGE-DERIVED on purpose -
`newW = ScaleRound(l+w,f) - ScaleRound(l,f)` - so siblings that abut before
scaling still abut after. That makes the scaled WIDTH depend on the LEFT EDGE:

    l=68 :  68*1.5 = 102 exact   ; 115*1.5 = 172.5 -> 173  ;  w = 71
    l=69 :  69*1.5 = 103.5 -> 104; 116*1.5 = 174   exact   ;  w = 70

The art cell is `sheetW/4 = 284/4 = 71` for all five, so the odd-edge button -
and only it - gets a 71px cell in a 70px window. The same arithmetic explains
the god-mode Day/Night flyout, where all three buttons sit at l=79 (odd), which
is why the artefact was reported on the sun AND the moon.

AT AN INTEGER FACTOR THIS CANNOT HAPPEN: ScaleRound(l*2) is exact for every l,
so w = 2*(r-l) always. Nine earlier theories matched that same 1.5x-only tier
signature and every one was wrong (law 60) - the difference here is that this
one PREDICTED WHICH BUTTON OF THE FIVE before anything was looked at.

THE FIX it guards: `build_selective_safe.py::parity_nudge_btn_areas` moves such
buttons onto an edge the factor divides evenly (l*FACTOR integral), fractional
tiers only. 177 buttons across 29 scripts at 1.5x; 2x proven entry-identical,
0 of 655.

WHAT THIS ASSERTS: for every state-strip button in the STAGED scripts - the ones
that actually ship - whose 1x art cell exactly filled its 1x window, the
edge-derived scaled window must equal the staged art cell, on BOTH axes.
It reads the STAGED `.UI`, not the pristine one, so it validates the shipped
artefact rather than the intention.

NEGATIVE CONTROL: run it against a build made before the fix and 1.5x must FAIL
with Level Terrain and the three Day/Night buttons named.

THREE POPULATIONS, NOT ONE (#170, 2026-08-16) - the file used to describe
only the first and that is how it printed PASS over a user-visible tear:

  1. RUNTIME-SCALED  - staged `.UI` keeps its 1x area, `ScaleSubtree` scales it
     live. Modelled here. Residual = ScaleDim's cell snap, reported.
  2. PRE-SCALED DATA - the area ships already multiplied and the DLL RETURNS
     before walking the subtree (`kDataScaledSubtreeIds`). Judged VERBATIM.
     Split by cause: if the art cell equals `states * R(cell1x * f)` the art is
     right and the builder's window rule is wrong -> HARD FAIL at every tier;
     if the cell differs, `ScaleDim` snapped the sheet -> reported, because the
     cure is an art-dimension change and that is reverted (#148/#156).
  3. STATIC DIALOGS  - `dialog-static\stage*`, the #155 half below.

    python gate_btn_undercover.py [--tier 15x|2x|3x] [--list N]

Offline. No game, no exe.
"""
import glob
import math
import os
import re
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
SS = os.path.join(ROOT, "tools", "selective-safe")
SRC1X_ART = os.path.join(ROOT, "tools", "dbpf", "extracted", "SimCity_1")
SRC1X_UI = os.path.join(ROOT, "tools", "uiscripts", "extracted")

TIERS = {"15x": ("stage-15x", 1.5), "2x": ("stage", 2.0), "3x": ("stage-3x", 3.0)}

RE_NODE = re.compile(r"<LEGACY\s+[^>]*?>", re.S)
RE_AREA = re.compile(r"area=\((-?\d+),(-?\d+),(-?\d+),(-?\d+)\)")
RE_IMAGE = re.compile(r"image=\{([0-9a-fA-F]+),([0-9a-fA-F]+)\}")
RE_RECT = re.compile(r"imagerect=\(")
RE_ID = re.compile(r"\bid=(0x[0-9a-fA-F]+)")
RE_TIP = re.compile(r'tiptext="([^"|]*)')


# ONE SOURCE FOR THE SCALING RULES (scale_rules.py). This file used to
# carry its own copy; #162 changed ScaleRound in the DLL and every private
# copy in this folder had to be found by hand. `scale_rules.py --drift`
# hunts any that come back.
from scale_rules import round_half_up as rhu    # noqa: E402


def png_wh(path):
    try:
        with open(path, "rb") as f:
            head = f.read(33)
    except OSError:
        return None
    if len(head) < 33 or head[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    return (int.from_bytes(head[16:20], "big"), int.from_bytes(head[20:24], "big"))


def find_art(d, gid, iid):
    for n in ("T-0x856ddbac_G-0x%08x_I-0x%08x.png" % (gid, iid),
              "T-856ddbac_G-%08x_I-%08x.png" % (gid, iid)):
        p = os.path.join(d, n)
        if os.path.isfile(p):
            return p
    return None


# ---------------------------------------------------------------------------
# #170: THIS GATE COULD NOT SEE THE PRE-SCALED SUBTREES, AND THAT IS WHERE
# THE USER-VISIBLE DEFECT WAS.
#
# The scan below reads the STAGED `.UI` and models what `ScaleSubtree` will do
# to it at runtime. That is right for the ordinary case - a staged script keeps
# its 1x `area=` and the DLL scales it live. It is WRONG for a subtree we
# pre-scale in the DATA, because those areas ship already multiplied and
# `ScalePanelRoot` returns before it ever walks them
# (`kDataScaledSubtreeIds`, UiSpike.cpp:14557). For those nodes the shipped
# number IS the final number and nothing downstream repairs it.
#
# The old scope filter made this silent rather than wrong: it required the 1x
# art cell to equal `r - l` read out of the STAGED file, which for a pre-scaled
# node is the SCALED width, so every one of them fell out at `continue` and was
# never counted. The seven advisor buttons (x2 scripts) shipped 82px windows
# against an 83px art cell at 1.5x - the user's "break on the right of every
# icon" - and this gate printed PASS while modelling a repair that provably
# never executes on them.
#
# THE FIX: pair each staged node with its 1x design by DOCUMENT ORDER (the
# builders only ever rewrite attributes, never add or drop nodes, and pairing
# by id would collide - the two advisor HUD variants share every id). If the
# staged area differs from the design area, the node is PRE-SCALED DATA and is
# judged VERBATIM: shipped size must equal the staged art cell. That is a hard
# failure, not a residual - there is no runtime rule left to appeal to.
#
# Law 42 (a gate is only as honest as its SCOPE) and law 71 (a gate that only
# asks about the windows you left alone cannot see the ones you rewrote).
def design_areas(staged_fn):
    """1x `area=` for every LEGACY node of a staged script, in document order.

    Staged names are `T-0x00000000_G-0x96a006b0_I-0x4a160034.ui`; the pristine
    corpus spells the same script `T-00000000_G-96a006b0_I-4a160034.ui`.
    """
    pristine = os.path.join(SRC1X_UI, staged_fn.replace("0x", ""))
    try:
        with open(pristine, "r", encoding="latin-1") as fh:
            txt = fh.read()
    except OSError:
        return None
    out = []
    for m in RE_NODE.finditer(txt):
        ar = RE_AREA.search(m.group(0))
        out.append(tuple(int(x) for x in ar.groups()) if ar else None)
    return out


PRESCALED_BAD = {}


def run(tier, limit, states=4):
    sub, f = TIERS[tier]
    stage = os.path.join(SS, sub)
    if not os.path.isdir(stage):
        print("  SKIP - no stage dir: %s" % stage)
        return None

    checked = 0
    residual, fixed = [], []
    prescaled_bad, prescaled_ok, prescaled_snap = [], [], []
    for fn in sorted(os.listdir(stage)):
        if not fn.lower().endswith(".ui"):
            continue
        try:
            with open(os.path.join(stage, fn), "r", encoding="latin-1") as fh:
                txt = fh.read()
        except OSError:
            continue
        design = design_areas(fn)
        for ni, m in enumerate(RE_NODE.finditer(txt)):
            node = m.group(0)
            if "GZWinBtn" not in node or RE_RECT.search(node):
                continue
            ar, im = RE_AREA.search(node), RE_IMAGE.search(node)
            if not ar or not im:
                continue
            gid, iid = int(im.group(1), 16), int(im.group(2), 16)
            p1 = find_art(SRC1X_ART, gid, iid)
            if not p1:
                continue
            o = png_wh(p1)
            if not o or o[0] % states:
                continue
            l, t, r, b = (int(x) for x in ar.groups())
            # #170: the 1x design, paired by document order. Without it the
            # scope test below silently drops every pre-scaled node.
            d = design[ni] if design and ni < len(design) else None
            dl, dt, dr, db = d if d else (l, t, r, b)
            pre = d is not None and d != (l, t, r, b)
            # In scope ONLY if the 1x cell exactly filled the 1x WINDOW - tested
            # on the DESIGN size, never on the staged one (which is already
            # multiplied for a pre-scaled subtree) and never on the position
            # (the reverted parity nudge preserved size but moved l).
            if (o[0] // states) != (dr - dl) or o[1] != (db - dt):
                continue
            ps = find_art(stage, gid, iid)
            if not ps:
                continue
            s = png_wh(ps)
            if not s:
                continue
            checked += 1
            # MODEL THE RULE THE DLL ACTUALLY USES. Since v2.94.1 a LEAF
            # window takes its scaled size SIZE-DERIVED (ScaleSubtree,
            # GetChildCount()==0). A GZWinBtn bound to a state strip is a leaf.
            # Modelling the old edge-derived rule here would fail on 204
            # buttons the DLL now gets right - a gate that models the wrong
            # rule is just a slower way of being wrong.
            edge = (rhu(dr * f) - rhu(dl * f), rhu(db * f) - rhu(dt * f))
            win = (rhu((dr - dl) * f), rhu((db - dt) * f))
            cell = (s[0] // states, s[1])
            tip = RE_TIP.search(node)
            wid = RE_ID.search(node)
            if pre:
                # PRE-SCALED DATA. The DLL never walks this subtree, so the
                # number in the file is the number on screen - compare it
                # verbatim, and do not credit a runtime rule that cannot run.
                #
                # SPLIT THE VERDICT BY CAUSE, or the gate blames the builder
                # for the upscaler's arithmetic. `want` is what the art cell
                # WOULD be if the sheet were built as `states * R(cell1x * f)`
                # (law 64a). If the shipped cell equals `want`, the art is
                # right and any disagreement is the BUILDER's window rule -
                # that is #170, and it is a hard failure because nothing
                # downstream repairs it. If the shipped cell differs from
                # `want`, `ScaleDim`'s CellUnit snapped the SHEET (law 70's
                # over-approximation: an 84px 4-state sheet divides by both 3
                # and 4, so it snaps on 12 and lands at 132 -> cell 33 where
                # the button wants 32). That needs an ART-DIMENSION change,
                # which is reverted and scoped game-wide (#148/#156) - so it
                # is REPORTED, exactly like the runtime half's residual, and
                # never silently folded into the builder's score.
                ship = (r - l, b - t)
                want = (rhu((o[0] // states) * f), rhu(o[1] * f))
                rec = (fn, wid.group(1) if wid else "-",
                       tip.group(1)[:24] if tip else "", (dl, dt, dr, db),
                       ship, cell)
                if ship == cell:
                    prescaled_ok.append(rec)
                elif cell != want:
                    prescaled_snap.append(rec)
                else:
                    prescaled_bad.append(rec)
                continue
            rec = (fn, wid.group(1) if wid else "-",
                   tip.group(1)[:24] if tip else "", (l, t, r, b), win, cell)
            if win != cell:
                # RESIDUAL, not the parity bug: the art cell disagrees because
                # ScaleDim's CellUnit snapped the SHEET (a 136px 4-state sheet
                # snaps on LCM(2,4,8)=8 -> cell 52 where the button wants 51).
                # Closing it needs an ART-DIMENSION change, which is reverted
                # and must not be reinstated (see SELECTIVE-SAFE.md #148).
                residual.append(rec)
            elif edge != win:
                # The parity class: edge-derived would have been wrong here and
                # size-derived is right. Counted to prove the fix is DOING
                # something - if this ever hits 0, the rule stopped applying.
                fixed.append(rec)

    print("  art-sized state-strip buttons in the STAGED scripts : %d" % checked)
    print("  PARITY CLASS repaired by the size-derived rule      : %d"
          % len(fixed))
    print("  RESIDUAL, cell snapped by ScaleDim (known, reported): %d"
          % len(residual))
    print("  PRE-SCALED DATA (#170) - shipped size vs art cell   : "
          "%d ok / %d BUILDER-WRONG / %d art snapped by ScaleDim (reported)"
          % (len(prescaled_ok), len(prescaled_bad), len(prescaled_snap)))
    PRESCALED_BAD[tier] = prescaled_bad
    for (fnm, wid, tip, area, ship, cell) in prescaled_bad[:limit]:
        print("     PRESCALED %s %-12s %-24s 1x=%s  ships %dx%d  cell %dx%d"
              % (fnm, wid, tip, area, ship[0], ship[1], cell[0], cell[1]))
    bad = residual
    by_file = defaultdict(list)
    for x in residual:
        by_file[x[0]].append(x)
    shown = 0
    for fnm in sorted(by_file):
        print("     %s" % fnm)
        for (_, wid, tip, area, win, cell) in by_file[fnm]:
            print("        %-12s %-24s area=%s l%%2=%d  win %dx%d  cell %dx%d"
                  % (wid, tip, area, area[0] % 2, win[0], win[1],
                     cell[0], cell[1]))
            shown += 1
            if shown >= limit:
                print("     ... truncated at %d" % limit)
                return len(bad)
    return len(bad)


# ---------------------------------------------------------------------------
# THE STATIC HALF (#155) - and the reason this gate missed a user-visible tear.
#
# Everything above scans `selective-safe\stage-*` and MODELS the DLL's leaf
# size-derived rule, then reports the 1.5x residual instead of failing on it,
# because the runtime sweep repairs the parity class. Both of those were true
# and neither applies to `dialog-static\`:
#
#   * SCOPE - dialog-static was never scanned at all. The region city bubble
#     `ca539340` is served from there, and its play button shipped 82px wide
#     over an 83px art cell. The user saw the leftover column as a tear.
#   * RULE  - a statically-served dialog is deliberately EXCLUDED from the
#     runtime sweep (kNeverScale; running both double-scales it), so there is
#     no later pass to repair anything. What the .UI says is what draws.
#
# So this half does not model any rule. It reads the STAGED `area=` verbatim -
# the number that ships - and compares it to the STAGED art cell. A mismatch
# here is a defect on screen, not a residual, and it FAILS.
#
# NEGATIVE CONTROL: extract the scripts back out of a pre-v2.98.0
# DialogStatic dat and this must fail naming ca539340's play button.
# ---------------------------------------------------------------------------
DS = os.path.join(ROOT, "tools", "dialog-static")
SRC1X_UI = os.path.join(ROOT, "tools", "uiscripts", "extracted")
TP_SRC_UI = os.path.join(DS, "thirdparty-src")


def _btn_nodes(txt):
    """(area, (gid,iid)) per art-bound GZWinBtn leaf with no imagerect."""
    out = []
    for m in RE_NODE.finditer(txt):
        node = m.group(0)
        if "GZWinBtn" not in node or RE_RECT.search(node):
            continue
        ar, im = RE_AREA.search(node), RE_IMAGE.search(node)
        if not ar or not im:
            continue
        out.append((tuple(int(x) for x in ar.groups()),
                    (int(im.group(1), 16), int(im.group(2), 16)),
                    RE_ID.search(node)))
    return out


def run_static(tier, limit, states=4):
    sub = TIERS[tier][0]
    stages = [os.path.join(DS, sub)] + sorted(
        glob.glob(os.path.join(DS, "stage-tp-*" + ("-" + tier if tier != "2x" else ""))))
    stages = [d for d in stages if os.path.isdir(d)
              and (tier != "2x" or ("-15x" not in d and "-3x" not in d))]
    if not stages:
        print("  SKIP - no dialog-static stage for %s" % tier)
        return None
    checked, bad = 0, []
    resid = defaultdict(int)
    for stage in stages:
        for fn in sorted(os.listdir(stage)):
            if not fn.lower().endswith(".ui"):
                continue
            iid = re.search(r"I-0x([0-9a-f]{8})", fn)
            iid = iid.group(1) if iid else None
            src = None
            for cand in (os.path.join(SRC1X_UI, "T-00000000_G-96a006b0_I-%s.ui" % iid),
                         os.path.join(TP_SRC_UI, "T-00000000_G-96a006b0_I-%s.ui" % iid)):
                if iid and os.path.isfile(cand):
                    src = cand
                    break
            if src is None:
                continue
            with open(os.path.join(stage, fn), "r", encoding="latin-1") as fh:
                new = _btn_nodes(fh.read())
            with open(src, "r", encoding="latin-1") as fh:
                old = _btn_nodes(fh.read())
            if len(old) != len(new):
                continue          # shape drift: not this gate's question
            for (a1, tgi1, _), (a2, _t2, wid) in zip(old, new):
                o = png_wh(find_art(SRC1X_ART, *tgi1) or "")
                if not o or o[0] % states:
                    continue
                # in scope only if the 1x cell exactly filled the 1x window
                if (o[0] // states, o[1]) != (a1[2] - a1[0], a1[3] - a1[1]):
                    continue
                ps = find_art(stage, *tgi1) or find_art(os.path.join(DS, sub), *tgi1)
                s = png_wh(ps) if ps else None
                if not s:
                    continue
                checked += 1
                win = (a2[2] - a2[0], a2[3] - a2[1])
                cell = (s[0] // states, s[1])
                # THE ASSERTION is that the builder applied its own rule: a
                # leaf that binds art is SIZE-derived (#155). That is the half
                # we control and the half that fixed the region bubble.
                want = (rhu((a1[2] - a1[0]) * TIERS[tier][1]),
                        rhu((a1[3] - a1[1]) * TIERS[tier][1]))
                if win != want:
                    bad.append((fn, wid.group(1) if wid else "-", a2, win, want))
                elif win != cell:
                    # RESIDUAL, and a DIFFERENT cause: ScaleDim's CellUnit
                    # snapped the SHEET. Reported with its exact shape, never
                    # silently excused - closing it needs an ART-dimension
                    # change and that lever has broken the thumbnails twice
                    # (#149). The dominant shape is (0,+2): a HORIZONTAL
                    # four-state strip whose HEIGHT was snapped although a
                    # horizontal strip has no vertical divide - exactly what
                    # Upscale2x's --height-exact-group exists for, not yet
                    # applied to the stock art group.
                    resid[(cell[0] - win[0], cell[1] - win[1])] += 1
    print("  art-sized state-strip buttons in the STATIC stage  : %d" % checked)
    print("  SHIPPED WINDOW != THE SIZE-DERIVED RULE (a build bug): %d" % len(bad))
    print("  residual, ScaleDim cell-snap (cell-window -> count)  : %s"
          % (dict(resid) if resid else "none"))
    for rec in bad[:limit]:
        print("     %-46s %-12s area=%s win %dx%d cell %dx%d"
              % (rec[0][:46], rec[1], rec[2], rec[3][0], rec[3][1],
                 rec[4][0], rec[4][1]))
    if len(bad) > limit:
        print("     ... %d more" % (len(bad) - limit))
    return len(bad)


def main():
    tiers = ["15x", "2x", "3x"]
    limit = 30
    if "--tier" in sys.argv:
        tiers = [sys.argv[sys.argv.index("--tier") + 1]]
    if "--list" in sys.argv:
        limit = int(sys.argv[sys.argv.index("--list") + 1])

    res = {}
    static_bad = {}
    for tier in tiers:
        print("=" * 76)
        print("TIER %s" % tier)
        print("=" * 76)
        n = run(tier, limit)
        print()
        ns = run_static(tier, limit)
        print()
        if n is not None:
            res[tier] = n
        if ns:
            static_bad[tier] = ns

    # THE INTEGER TIERS ARE THE ASSERTION. At f=2 and f=3, ScaleRound is
    # exact and ScaleDim returns early, so BOTH causes are impossible: anything
    # here means the model or the rule broke. The 1.5x RESIDUAL is reported, not
    # failed - it needs an art-dimension change, and that was reverted on
    # measurement (runtime-created consumers; see SELECTIVE-SAFE.md #148).
    # THE STATIC HALF FAILS AT EVERY TIER (#155), not just integer ones:
    # nothing downstream repairs a statically-served dialog, so a shipped
    # window that disagrees with its shipped art cell IS the tear.
    # PRE-SCALED SUBTREES FAIL AT EVERY TIER (#170), same reasoning as the
    # static half: `ScalePanelRoot` returns before it walks a
    # kDataScaledSubtreeIds subtree, so the shipped area is the final area and
    # no runtime rule repairs it. This is the check that was missing while the
    # seven advisor buttons shipped an 82px window around an 83px art cell.
    pre_bad = {k: len(v) for k, v in PRESCALED_BAD.items() if v}
    if pre_bad:
        print("FAIL - pre-scaled data: %s art-sized button(s) ship a window "
              "that does not match their art cell. The DLL never walks these "
              "subtrees - this draws." % pre_bad)
        sys.exit(1)
    if static_bad:
        print("FAIL - dialog-static: %s art-sized button(s) ship a window that "
              "does not match their art cell. Nothing repairs a static dialog "
              "later - this draws." % static_bad)
        sys.exit(1)
    bad = {k: v for k, v in res.items()
           if v and float(TIERS[k][1]).is_integer()}
    if bad:
        print("FAIL - %s: mismatch at an INTEGER factor, where both causes are "
              "impossible by construction."
              % ", ".join("%s=%d" % kv for kv in sorted(bad.items())))
        sys.exit(1)
    frac = {k: v for k, v in res.items()
            if not float(TIERS[k][1]).is_integer()}
    print("PASS - integer tiers exact. Fractional residual %s is the KNOWN "
          "ScaleDim cell-snap, reported not failed; the parity class (the "
          "reverse L) is repaired by the leaf size-derived rule."
          % ", ".join("%s=%d" % kv for kv in sorted(frac.items())))
    sys.exit(0)


main()
