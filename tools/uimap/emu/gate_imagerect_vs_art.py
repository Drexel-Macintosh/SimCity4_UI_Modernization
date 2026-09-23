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

AMENDED 2026-09-01. The three lines above are the PRE-#172 statement and are
kept verbatim - they are what this gate asserted when the thumbnail-split guard
was written. The second HARD FAIL is now CONDITIONAL, and two more were added:

  HARD FAIL  a #172 query-pair state cell is not exactly R(36f) x R(21f)
  HARD FAIL  the #172 tables cannot be read out of `build_selective_safe.py`

THE PIPELINE IS TWO STAGES, NOT ONE   (the amendment, 2026-09-01)
-----------------------------------------------------------------
SUPERSEDED, KEPT: everything above assumed `ScaleDim` alone decides a staged
sheet's size, so the integer-tier control was armed for every sheet. True until
#172; not true now.

    stage 1  tools\upscale\Upscale2x.cs::ScaleDim
             round-half-up, then the CellUnit snap - and it RETURNS EARLY at an
             integer factor, which is exactly what the control tests
    stage 2  tools\selective-safe\build_selective_safe.py::
             clamp_query_pair_cells                              (#172)
             TRIMS two sheets AFTER staging, at EVERY tier

`clamp_query_pair_cells` trims each state cell of {46A006B0,14015547} (Query)
and {46A006B0,4B8DA4A4} (Route Query) down to the scaled design window
R(36f) x R(21f) and repacks the cells at the new pitch. It is deliberately NOT
an integer no-op, because the overhang it removes exists in stock:

    Query        1x 148x21   1.5x 224x33 -> 216x32   2x 296x42 -> 288x42
                                                     3x 444x63 -> 432x63
    Route Query  1x 148x23   1.5x 224x35 -> 216x32   2x 296x46 -> 288x42
                                                     3x 444x69 -> 432x63

    MEASURED 2026-09-01, PNG IHDR of the two sheets in stage-15x\ stage\
    stage-3x\ against tools\dbpf\extracted\SimCity_1\; every staged cell is
    exactly 54x32 / 72x42 / 108x63. CARRIED: the same six numbers are the #172
    acceptance table in _tests\REGRESSION.md, approved 2026-08-16, art
    re-staged 2026-08-30.

So a staged size that differs from round(src1x * f) at 2x/3x is NOT evidence
that ScaleDim failed to return early. For these two sheets it is evidence that
the clamp ran, exactly as designed. Until this amendment the gate read it as a
ScaleDim defect and exited 1 at BOTH integer tiers - attributing a deliberate,
user-approved art repair to a bug in the offline upscaler. ScaleDim had in fact
returned early exactly as modelled; the model had never been told stage 2
exists. THE FIX WAS TO THE MODEL, NOT TO THE ART: no staged byte changed.

WHY THE EXEMPTION IS NOT A HOLE
  * the two sheets are DERIVED from the builder's own
    QUERY_PAIR_SHEETS / QUERY_PAIR_WIN_1X / QUERY_PAIR_STATES, never a
    hand-copied TGI pair - a retyped pair is the defect shape this project
    keeps paying for, because it goes stale silently;
  * what they are exempt FROM is replaced by what the clamp itself promises:
    cell == R(36f) x R(21f), checked at EVERY tier, not only the integer ones;
  * every OTHER sheet keeps the original control, so a genuine integer-tier
    snap is still visible. POSITIVE CONTROL 2026-09-01: pointing the exemption
    at a bogus TGI put both real sheets back in the control population and the
    gate failed at 2x again; an off-by-one design window failed the acceptance
    test; an unreadable builder failed the derivation check. The gate can still
    fail three ways.

(Revision prepared 2026-09-01, lost to commit 0961524, re-verified and
applied 2026-09-23.)

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


# ---------------------------------------------------------------------------
# THE #172 CLAMP STAGE, DERIVED FROM THE BUILDER'S OWN SOURCE (2026-09-01).
#
# Read, never imported: importing build_selective_safe.py executes module-level
# path/FACTOR setup off sys.argv. Read, never RETYPED: a hand-copied TGI pair
# is exactly the defect shape this project keeps paying for - it goes on being
# believed after the build stops agreeing with it.
#
# A failed read returns empty and main() FAILS with that as the stated reason.
# It must never fall through to "no sheets are exempt", because that resurrects
# the false ScaleDim accusation, nor to "everything is exempt", which would
# blind the control.
# ---------------------------------------------------------------------------
SEL_BUILDER = os.path.join(ROOT, "tools", "selective-safe",
                           "build_selective_safe.py")


def query_pair_model():
    """-> (frozenset{(gid, iid)}, (win_w, win_h), n_states), or empty on any
    failure to read. Mirrors build_selective_safe.py::clamp_query_pair_cells.

    The clone duplicates (iid ^ CLONE_XOR) need no entry here: a clone has no
    1x extract under its own iid, so it never reaches `snapped` in the first
    place. Verified 2026-09-01 - no clone of either sheet is staged at any tier.
    """
    try:
        with open(SEL_BUILDER, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except OSError:
        return frozenset(), None, None
    ms = re.search(r"^QUERY_PAIR_SHEETS\s*=\s*\((.*?)^\)", text, re.S | re.M)
    mw = re.search(r"^QUERY_PAIR_WIN_1X\s*=\s*\(\s*(\d+)\s*,\s*(\d+)\s*\)",
                   text, re.M)
    mn = re.search(r"^QUERY_PAIR_STATES\s*=\s*(\d+)", text, re.M)
    if not (ms and mw and mn):
        return frozenset(), None, None
    sheets = frozenset(
        (int(a, 16), int(b, 16))
        for a, b in re.findall(r"\(\s*0x([0-9A-Fa-f]+)\s*,\s*0x([0-9A-Fa-f]+)\s*\)",
                               ms.group(1)))
    if not sheets:
        return frozenset(), None, None
    return sheets, (int(mw.group(1)), int(mw.group(2))), int(mn.group(1))


QP_SHEETS, QP_WIN, QP_N = query_pair_model()


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

    # THE CONTROL POPULATION EXCLUDES THE #172 SHEETS - see the header.
    # `snapped` itself keeps them, so the under-read BASELINE below still
    # counts them and that number cannot move unnoticed.
    exempt = sorted(k for k in snapped if k in QP_SHEETS)
    control = len(snapped) - len(exempt)

    print("  staged images with a 1x source : %d" % considered)
    print("  of those, SNAPPED by ScaleDim  : %d%s"
          % (control,
             "   (expected 0 at an integer factor)" if float(f).is_integer() else ""))
    for gid, iid in exempt:
        o, staged, naive = snapped[(gid, iid)]
        print("    (+ {%08X,%08X} 1x=%dx%d staged=%dx%d vs naive %dx%d - #172 "
              "post-staging clamp, not ScaleDim; checked against the clamp's "
              "own acceptance test below)"
              % (gid, iid, o[0], o[1], staged[0], staged[1], naive[0], naive[1]))

    # ---- 1b. the acceptance test that PAYS FOR that exemption ---------------
    # build_selective_safe.py::clamp_query_pair_cells promises one thing about
    # its output: every state cell is exactly the scaled design window. Armed at
    # EVERY tier - the clamp runs at every tier, so there is no reason to check
    # it only where the control used to fire.
    clamp_bad = []
    tw = th = None
    if QP_SHEETS:
        tw, th = round_half_up(QP_WIN[0] * f), round_half_up(QP_WIN[1] * f)
        for key in sorted(QP_SHEETS):
            a = staged_dims.get(key)
            if a is None:
                clamp_bad.append((key, "is not staged - the clamp would ship "
                                       "silently unapplied"))
            elif a[0] % QP_N:
                clamp_bad.append((key, "staged %dx%d - width not divisible by "
                                       "%d states" % (a[0], a[1], QP_N)))
            elif (a[0] // QP_N, a[1]) != (tw, th):
                clamp_bad.append((key, "cell %dx%d, want %dx%d (sheet %dx%d)"
                                  % (a[0] // QP_N, a[1], tw, th, a[0], a[1])))
        print("  #172 query-pair cell == R(%df)xR(%df) = %dx%d : %s"
              % (QP_WIN[0], QP_WIN[1], tw, th,
                 "OK, %d sheet(s)" % len(QP_SHEETS) if not clamp_bad
                 else "%d WRONG" % len(clamp_bad)))

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
    return len(bad), control, len(spread), clamp_bad


def main():
    tiers = ["15x", "2x", "3x"]
    limit = 15
    if "--tier" in sys.argv:
        tiers = [sys.argv[sys.argv.index("--tier") + 1]]
    if "--list" in sys.argv:
        limit = int(sys.argv[sys.argv.index("--list") + 1])

    # A DERIVATION THAT SILENTLY RETURNS NOTHING IS THE FAILURE, NOT A DEFAULT.
    if not QP_SHEETS:
        print("FAIL")
        print("   could not read QUERY_PAIR_SHEETS / QUERY_PAIR_WIN_1X / "
              "QUERY_PAIR_STATES out of")
        print("   %s" % SEL_BUILDER)
        print("   The #172 exemption and its replacement acceptance test are "
              "DERIVED from that file,")
        print("   never retyped. If the tables were renamed or the clamp was "
              "removed, fix this gate")
        print("   deliberately - do not let it fall back to a control that "
              "cannot see stage 2.")
        sys.exit(1)

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
        nbad, nsnap, nspread, clamp_bad = res
        # nbad is REPORTED, NEVER FAILED ON. Closing that gap is what broke
        # the thumbnails twice; see the header. Left visible so the number
        # cannot drift unnoticed.
        spread_by_tier[tier] = nspread
        # nsnap now EXCLUDES the #172 sheets, so this control still fires on a
        # genuine integer-tier snap by any other sheet.
        if float(STAGE[tier][1]).is_integer() and nsnap:
            fail.append("%s: ScaleDim snapped %d image(s) at an INTEGER factor - "
                        "it is supposed to return early there" % (tier, nsnap))
        for key, why in clamp_bad:
            fail.append("%s: #172 query-pair sheet {%08X,%08X} %s - "
                        "clamp_query_pair_cells promises cell == R(%df)xR(%df)"
                        % (tier, key[0], key[1], why, QP_WIN[0], QP_WIN[1]))

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
