r"""Emit the art TGIs that must NOT be cell-snapped, because nothing divides
them and their only contract is with their WINDOW (#160 + #162).

⛔ THE RULE, stated once. `CellUnit` snaps a scaled sheet so a cell count keeps
dividing it evenly. That is right for exactly two roles and wrong for every
other sheet in the game:

    N-state strip    needs width/N   (cell-strips.txt, #156)
    9-slice frame    needs width/3   (nine-slice.txt,  #157)
    EVERYTHING ELSE  needs NOTHING - it needs to MATCH ITS WINDOW

A sheet the `.UI` binds 1:1 to a window (art size == window size at 1x) is drawn
at native size and clipped, so if the snap makes it disagree with the scaled
window by even a pixel you get a clipped edge or an uncovered hairline. The
window scales by a plain round; the art must do the same.

MEASURED: 98 art/window pairs sit flush at 1x AND at 2x and diverge only at
1.5x, by 1-6px. An integer factor makes the snap a provable no-op, which is why
this whole family is invisible at 2x and 3x - and why the user could say of the
symptoms "they don't exist at 2x or I would have noticed them before".

Qualifies here if:
  * a .UI draws it with blttype=tiled (a tiled background has no divide), OR
  * a .UI binds it to a window of EXACTLY the art's 1x size (1:1, so the
    window is the contract);
AND no .UI ever draws it as a GZWinBtn state or as a 9-slice;
AND it is absent from cell-strips.txt and nine-slice.txt.

⚠ EXCLUSION-BIASED, like both siblings. Art binds by TGI and some consumers are
created at runtime and appear in no script (REGRESSION.md #148), so a sheet
nobody proved is snap-free keeps the sizing it has today. An unknown consumer
can be MISSED by this list, never broken by it.

    python find_no_snap.py [--out no-snap.txt]

Read-only apart from its own output file.
"""
import os
import re
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
UI_DIRS = [os.path.join(TOOLS, "uiscripts", "extracted"),
           os.path.join(TOOLS, "dialog-static", "thirdparty-src")]
ART_DIRS = [os.path.join(TOOLS, "dbpf", "extracted", "SimCity_1"),
            os.path.join(TOOLS, "dialog-static", "thirdparty-art")]
SIBLINGS = [os.path.join(HERE, "cell-strips.txt"),
            os.path.join(HERE, "nine-slice.txt")]

ATTR = re.compile(r'(\w+)=("[^"]*"|\{[^}]*\}|\([^)]*\)|\S+)')
IMG = re.compile(r"\{([0-9a-fA-F]+),([0-9a-fA-F]+)\}")
RECT = re.compile(r"\((-?\d+),(-?\d+),(-?\d+),(-?\d+)\)")


def art_size(g, i):
    for d in ART_DIRS:
        for n in ("T-856ddbac_G-%s_I-%s.png" % (g, i),
                  "T-0x856ddbac_G-0x%s_I-0x%s.png" % (g, i)):
            p = os.path.join(d, n)
            if os.path.isfile(p):
                try:
                    return Image.open(p).size
                except Exception:
                    return None
    return None


def scan():
    """(gid,iid) -> {roles}, the set proven 1:1-bound to a window, and the set
    whose 1x imagerect covers the WHOLE sheet."""
    use, oneone, fullcrop, files = {}, set(), set(), 0
    for d in UI_DIRS:
        if not os.path.isdir(d):
            continue
        for fn in os.listdir(d):
            if not fn.endswith(".ui"):
                continue
            files += 1
            with open(os.path.join(d, fn), "r", encoding="latin-1") as fh:
                txt = fh.read()
            for m in re.finditer(r"<LEGACY([^>]*)>", txt):
                a = dict(ATTR.findall(m.group(1)))
                gi = IMG.match(a.get("image", ""))
                if not gi:
                    continue
                k = (gi.group(1).lower(), gi.group(2).lower())
                if a.get("blttype") == "tiled":
                    role = "tiled"
                elif a.get("blttype") == "edge" or a.get("edgeimage") == "yes":
                    role = "edge"
                elif a.get("clsid") == "GZWinBtn":
                    role = "btn"
                else:
                    role = "plain"
                use.setdefault(k, set()).add(role)
                ar = RECT.match(a.get("area", ""))
                if ar and role in ("tiled", "plain"):
                    l, t, r, b = (int(x) for x in ar.groups())
                    sz = art_size(*k)
                    if sz and sz == (r - l, b - t):
                        oneone.add(k)

                # ⛔ FULL-SHEET CROP (#179, 2026-08-16). A node whose imagerect
                # is (0,0,artW,artH) has declared "READ THE WHOLE SHEET". That
                # is a CONTRACT BETWEEN TWO NUMBERS, and the two are produced by
                # DIFFERENT RULES: the builder pre-scales the crop with a plain
                # ScaleRound, while the art goes through ScaleDim, which may
                # SNAP. When they disagree the crop under-reads and the sheet's
                # outer edge is simply never drawn.
                #
                # MEASURED, the polls panel background {46a006b0,2bbeb1af}:
                #     1x   art 516x130   crop 516x130   slack 0
                #     1.5x art 780x195   crop 774x195   slack 6   <- the defect
                #     2x   art 1032x260  crop 1032x260  slack 0
                #     3x   art 1548x390  crop 1548x390  slack 0
                # CellUnit(516) = lcm{3,4} = 12; R(516*1.5) = 774; 774 % 12 = 6,
                # so down=768 / up=780 is an EXACT TIE and "ties go UP" gives
                # 780. The proportionality guard (|780-774|*8 = 48 < 774) does
                # not fire, and build_selective_safe.py only ever CLAMPS a crop
                # to the art (right <= artW, task #95) - it never expands one.
                # The right-hand border fade lives in the 6 lost columns.
                #
                # ⚠ WHY `oneone` DOES NOT ALREADY CATCH IT, and why this is a
                # SECOND rule rather than a widening of the first: `oneone` keys
                # on area == art size. This node's area is 585x130 against 516x130
                # art - the window is deliberately WIDER than the bitmap. Keying
                # the contract on the window was the wrong hook; the contract is
                # between the CROP and the ART. 70 sheets sit in that gap.
                #
                # Integer-tier safe by construction: ScaleDim returns before
                # CellUnit at an integer factor, so crop and art already agree
                # there and this can only be a no-op.
                ir = RECT.match(a.get("imagerect", ""))
                if ir:
                    l, t, r, b = (int(x) for x in ir.groups())
                    sz = art_size(*k)
                    if sz and (l, t) == (0, 0) and (r, b) == sz:
                        fullcrop.add(k)
    return use, oneone, fullcrop, files


def listed():
    out = set()
    for p in SIBLINGS:
        if not os.path.isfile(p):
            continue
        with open(p, "r", encoding="utf-8") as fh:
            for line in fh:
                s = line.strip()
                if not s or s.startswith("#"):
                    continue
                q = s.split()
                if len(q) >= 2:
                    out.add((q[0].lower(), q[1].lower()))
    return out


# ---------------------------------------------------------------------------
# CODE-BOUND SHEETS THE .UI SCAN CANNOT REACH.
#
# ⛔ EVERYTHING ELSE IN THIS FILE IS DERIVED FROM A `.UI` BINDING, WHICH MEANS
# ART WITH NO `.UI` REFERENCE IS INVISIBLE TO IT BY CONSTRUCTION. That is not a
# hypothetical: `cSC4WinTrendBar` (clsid 0xAA5C2F86, Draw 0x7BF0A0) is handed
# its two sheets by the polls controller at 0x7ED4AC via SetImages, and they
# appear in ZERO scripts. So the scan below reports them as "not referenced"
# and they fall through to the default cell-snap.
#
# MEASURED 2026-08-16, and USER-CONFIRMED as the tier signature:
#     14015580  ramp    1x  99x101 -> 1.5x 150x152   proportional 148.5x151.5
#     14015584  marker  1x  42x9   -> 1.5x  63x15    proportional  63.0x13.5
# CellUnit(99) = 3 and CellUnit(9) = 3, so ScaleDim snaps UP to the next
# multiple of three: 148.5 -> 150 and 13.5 -> 15. That last one is +1.5 rows on
# a NINE row sprite - over 11% too tall. Exact at 2x and 3x, because ScaleDim
# returns before CellUnit at an integer factor.
#
# USER-REPORTED: "Mayor rating is broken ... the green bars don't extend top to
# bottom", and "Looks perfect at 2x" - the exact 1.5x-only signature.
#
# ⚠ CORRECTED 2026-08-16 (same day): "NOTHING divides these sheets" was
# written BEFORE the cSC4WinTrendBar draw was disassembled, and it is wrong
# for the fill strip. Draw 0x7BF0A0 computes bandW = fillW/6 (0x7BF0E4 imul
# 0xAAAAAAAB / 0x7BF0F5 shr 2) - **14015584 IS a six-cell strip and the draw
# divides it.** Its correct rule is cell-first (find_cell_strips.py CODE_BOUND,
# states=6 -> 66 wide at 1.5x); listing it here forced ScaleDim's
# conflict branch and silently kept the 63-wide plain rounding. Only the
# GROOVE stays no-snap:
#
# 14015580 (ramp): drawn art-centred at NATIVE width, selected row stretched
# to the window height - no divide on either axis. Byte evidence in the same
# disassembly (grooveX = left+(winW-grooveW)/2; stretch-blt 0x8D8BC0).
#
# Provenance: TrendBar disassembly 2026-08-16 (REGRESSION.md #176(b)) +
# tools/research/SC4-UI-ENGINE.md widget catalogue. Keep this list tiny and
# justify every entry with a measured draw path, never a class-level claim.
CODE_BOUND = [
    ("46a006b0", "14015580"),   # cSC4WinTrendBar ramp - art-centred, no divide
    # SIM PORTRAIT FACES (#190) - 36x41, bound 1:1 to a swept 36x41 slot, so
    # their only contract is to MATCH THEIR WINDOW. They are CODE-BOUND (TGI
    # composed at runtime from the sim exemplar id, see build_selective_safe
    # CODE_BOUND_TGIS), so scan() can never see them - this list is the only
    # way in. WITHOUT THESE the 1.5x tier upscales them 60x62 against a
    # measured 54x62 window and GZWinBMP's SetImage clamp (VA 0x009BC482 /
    # 0x009BC4A4) slices 6 px off the right of every face. Control: the .UI
    # placeholder {1abe787d,ea32f100} is the SAME 36x41 source, is already in
    # this file via scan(), and comes out at the correct 54x62.
    ("46a006b0", "fa8cdfbf"),
    ("46a006b0", "fa8cdfc0"),
    ("46a006b0", "fa8cdfc1"),
    ("46a006b0", "fa8cdfc2"),
    ("46a006b0", "fa8cdfc3"),
    ("46a006b0", "fa8cdfc4"),
    ("46a006b0", "fa8cdfc5"),
    ("46a006b0", "fa8cdfc6"),
    ("46a006b0", "fa8cdfc7"),
    ("46a006b0", "fa8cdfc8"),
    ("46a006b0", "fa8cdfc9"),
    ("46a006b0", "fa8cdfca"),
    ("46a006b0", "fa8cdfcb"),
    ("46a006b0", "fa8cdfcc"),
    ("46a006b0", "fa8cdfcd"),
    ("46a006b0", "fa8cdfce"),
    ("46a006b0", "fa8cdfd0"),
    ("46a006b0", "fa8cdfd1"),
    ("46a006b0", "fa8cdfd2"),
    ("1abe787d", "fa8cdfbf"),
    ("1abe787d", "fa8cdfc0"),
    ("1abe787d", "fa8cdfc1"),
    ("1abe787d", "fa8cdfc2"),
    ("1abe787d", "fa8cdfc3"),
    ("1abe787d", "fa8cdfc4"),
    ("1abe787d", "fa8cdfc5"),
    ("1abe787d", "fa8cdfc6"),
    ("1abe787d", "fa8cdfc7"),
    ("1abe787d", "fa8cdfc8"),
    ("1abe787d", "fa8cdfc9"),
    ("1abe787d", "fa8cdfca"),
    ("1abe787d", "fa8cdfcb"),
    ("1abe787d", "fa8cdfcc"),
    ("1abe787d", "fa8cdfcd"),
    ("1abe787d", "fa8cdfce"),
    ("1abe787d", "fa8cdfd0"),
    ("1abe787d", "fa8cdfd1"),
    ("1abe787d", "fa8cdfd2"),
]


def main():
    out = "no-snap.txt"
    if "--out" in sys.argv:
        out = sys.argv[sys.argv.index("--out") + 1]
    use, oneone, fullcrop, files = scan()
    other = listed()

    picked, rej_role, rej_listed = [], 0, 0
    for k in sorted(use):
        roles = use[k]
        # #179 adds `fullcrop` to this disjunction - see scan().
        if not ({"tiled"} & roles) and k not in oneone and k not in fullcrop:
            continue
        if roles & {"btn", "edge"}:
            rej_role += 1
        elif k in other:
            rej_listed += 1
        else:
            picked.append(k)

    lines = [
        "# Art TGIs that must NOT be cell-snapped (#160 + #162).",
        "# Generated by tools\\upscale\\find_no_snap.py - do not hand-edit.",
        "# Derived, not guessed: a .UI draws the sheet with blttype=tiled, or",
        "# binds it 1:1 to a window of exactly its 1x size - and NO .UI ever",
        "# draws it as a GZWinBtn state or as a 9-slice. Nothing divides these,",
        "# so their only contract is to MATCH THEIR WINDOW, which scales by a",
        "# plain round. Snapping them can only desynchronise the pair.",
        "# <group> <instance>",
    ]
    # the code-bound pair the .UI scan structurally cannot find
    n_code = 0
    for k in CODE_BOUND:
        if k not in picked:
            picked.append(k)
            n_code += 1
    picked.sort()
    lines += ["%s %s" % k for k in picked]
    path = out if os.path.isabs(out) else os.path.join(HERE, out)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")

    print("scanned %d .UI files, %d art TGIs referenced" % (files, len(use)))
    print("  proven 1:1 art==window : %d" % len(oneone))
    print("  EXCLUDED, also btn/edge: %d" % rej_role)
    print("  EXCLUDED, already listed: %d" % rej_listed)
    print("  ADDED, code-bound (no .UI ref possible): %d" % n_code)
    print("no-snap sheets: %d  -> %s" % (len(picked), out))
    if not picked:
        print("REFUSING TO BE QUIET: zero matched - the corpus is missing or the "
              "predicate is wrong. Do NOT read this as 'nothing needs it'.")
        return 1
    return 0


sys.exit(main())
