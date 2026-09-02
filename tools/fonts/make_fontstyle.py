#!/usr/bin/env python3
r"""
FontStyle-<factor>.ini generator for the SC4 UI-scaling tiers.

Derives a scaled Font Table from the PRISTINE 1x table `FontStyle.default.ini`
(byte-verified identical to the DBPF Font Table TGI 0x00000000,0x4A87BFE8,
0x2A87BFFC extracted from SimCity_1.dat). The ONLY change per line is the size
field -- the 2nd double-quoted token in each [Font Styles] entry
(`name = "<faces>", "<size>", "<params>", <GUID>`). Faces, params, GUIDs,
aliases, directories, comments, whitespace and CRLF line endings are preserved
byte-for-byte -- exactly the transform that produced the shipped 2x
FontStyle.candidate.ini (sizes * 2).

Scaling rule (scale_size): the guard tests the TIER factor, never the
squeezed product (#163).
  integer factor  -> new = floor(size * factor * squeeze + 0.5)  (round-half-up)
     factor 2  -> size*2   (bit-identical to FontStyle.candidate.ini; self-checked)
     factor 3  -> size*3
  non-integer     -> new = floor(size * factor * squeeze)        (FLOOR)
     factor 1.5-> the six odd 1x sizes (11,13,15,17,19,21) land on .5 and
              round DOWN (16,19,22,25,28,31). The DAT builders scale every
              area= rect by EXACTLY f, so a font may never exceed the box's
              own factor; rounding half-up overshot it on every odd size and
              clipped long labels at 1.5x (2026-08-06). See scale_size() for
              the measurements and the #142 / #163 history.

Usage: make_fontstyle.py <factor> <out.ini>
       make_fontstyle.py --selfcheck      (verify factor 2 == candidate.ini)
"""

import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_INI = os.path.join(HERE, "FontStyle.default.ini")
CANDIDATE_INI = os.path.join(HERE, "FontStyle.candidate.ini")

# a [Font Styles] entry: name = "faces", "SIZE", ...  -- capture the SIZE token.
STYLE_SIZE_RE = re.compile(
    r'^(?P<pre>\s*[A-Za-z_][A-Za-z0-9_]*\s*=\s*"[^"]*"\s*,\s*")(?P<size>\d+)(?P<post>"\s*,)')


# Styles whose size must STAY STOCK at every tier (v2.25.2, 2026-07-30).
# ChartTickText (0xE9C86B6E) is painted INSIDE the Graphs chart window by the
# chart controller (creation site exe 0x76D3D0 fetches it by GUID via the
# style manager), which right-aligns the tick numbers into a label column
# whose width is a HARDCODED 1x code constant - a doubled tick font clips to
# ")000" garbage (user screenshot 2026-07-30). Same reasoning as the HTML
# engine's stock-size clone styles: text drawn inside 1x-constant code
# geometry keeps its stock size until that code geometry itself is patched.
# . This comment used to end "(ChartLabel/Legend
# keep scaling: their regions have room - verified in the same screenshots.)"
# A user screenshot REFUTES that for Legend: at 26px the chart legend reads
# "Income / Expense s" - the word wraps, because the legend column is a 1x
# code constant exactly like the tick gutter. ChartLabel is still fine.
# Legend is NOT added to KEEP_STOCK yet: whether the right answer is to pin it
# (data-only, small but unwrapped) or to patch the 1x column constant is being
# decided against a real stock capture (task #57, graphs-stock-ref.png).
# Do not "verify" a region has room by looking at a screenshot that happens to
# contain a short string.
# CORRECTED AGAIN 2026-08-03 (#57 closed, v2.55.0). The 08-02 correction
# above got the DIAGNOSIS right and the STYLE wrong, in both directions:
#   - the wrapping text in that screenshot is NOT the Legend style. The Graphs
#     legend row text is ChartLabel (0xE9C86B5E), byte-verified at 0x0076DD91;
#   - so "ChartLabel is still fine" is exactly backwards - ChartLabel is the
#     style that was wrapping, at its raw 26pt;
#   - "the legend column is a 1x code constant" IS right, and that is what got
#     fixed: SIX unscaled constants in the panel builder sub_76D3D0, patched
#     at birth by CodePatches::ApplyGraphLegendBudgetScale (v2.55.0,
#     user-confirmed). Neither style was pinned. See SIZE_SQUEEZE below.
# The lesson that survives both corrections: identify the STYLE by the GUID
# the drawing code actually pushes, not by the name that sounds right.
#
# ---- v2.51.1 (#57): UNPINNED, MEASURED, REFUTED, RE-PINNED IN ONE HOUR ----
# v2.51.0 removed ChartTickText from this set on the theory that the tick
# GUTTER is derived from the tick FONT (sub_9B799D builds the plot's left
# edge from labelW + titleH + tickLen), so pinning the font had pinned the
# gutter into a deadlock. The change shipped with a stated falsifiable
# prediction: "IF THE ')000' CLIP RETURNS, the gutter did NOT grow with the
# font and the pin must come back."
#
# IT RETURNED. MEASURED, one build apart, same chart, same city:
#     ChartTickText 10pt -> CHARTGEO PLOT[0xE0](45,20,866,492)   gutter 45
#     ChartTickText 20pt -> CHARTGEO PLOT[0xE0](45,20,866,492)   gutter 45
# Byte-identical. The gutter is INVARIANT to the tick font size, and the
# user's screen showed "8000"/"4000" with their left halves sheared off
# (a clipped 8 reads as 3, a clipped 4 as 1).
#
# ⇒ THE "GUTTER IS TEXT-DERIVED" BELIEF IS DEAD. It was in the v2.25.2 note,
#   it was in the disassembly reading, and two live measurements refute it.
#   The most likely survivor: the plot rect is computed ONCE per chart object
#   (sentinel at chart+0xE0, which NOTHING in the module ever re-arms), so
#   whatever the first paint decided is frozen for that object's life -
#   which would make ANY font change structurally unable to move it.
#   The gutter needs a GEOMETRY lever, not a font one. The measured target is
#   recorded next to the disabled write path in UiSpike.cpp:
#       stock plot (78,21,408,234)/488x256  ->  x2 (156,42,816,468)/976x512
#
# v2.53.2 (2026-08-03): THE GEOMETRY FIX LANDED, SO THE PIN COMES OFF -
# exactly the condition the warning below demanded. The repaint mechanism was
# found (dirty byte cIGZWin+0x70, set only via vt+0x170) and v2.53.1 scales
# the plot margins per chart object: gutter is now 90px (user-confirmed
# on-screen, CHARTSCALE log 7/7 charts). 20pt digits ("8000" ~48px + tick 8)
# fit in 90 with a third to spare. The v2.51.0 shear happened because the
# gutter was still 45 - the font was never the blocker, the frozen rect was,
# and the rect is no longer frozen.
# (Historical warning kept for the record:)
# DO NOT UNPIN THIS AGAIN WITHOUT A GEOMETRY FIX LANDING FIRST. The font
#    is not the blocker; the frozen rect is.
KEEP_STOCK = set()

# ---- v2.53.2: PER-STYLE SQUEEZE (measured, not aesthetic) ---------------
# Legend is drawn RIGHT-ANCHORED from the chart window edge using the
# MEASURED text width, wrap-limited by the legend rect right edge (winW-4).
# MEASURED at 2x: "Expenses" at 26pt needs ~93px but the draw box leaves
# ~92px - a few-pixel shortfall, so the final "s" wraps ("Expense / s", the
# user's original report). Stock has 60% slack at 13pt because the WINDOW
# edge did not scale with the font. 0.92 x f (26 -> 24pt at 2x) buys ~7px
# and lands inside the box at every tier; visually indistinguishable from
# full 2x. Paired with the +4px legend-rect widening in UiSpike's
# CHARTSCALE block - the two together clear the shortfall with margin.
#
# ================= ===================
# THE PARAGRAPH ABOVE NAMES THE WRONG SCREEN. It is kept because the
# arithmetic in it is right; what is wrong is WHICH legend it describes.
#
# THIS SQUEEZE DOES NOT TOUCH THE GRAPHS CHART LEGEND, AND NEVER HAS.
# It keys on the STYLE NAME "Legend" = GUID 0xE9C86B5F, which is the
# DATA VIEWS legend (fetched at exe 0x007A0747).
# The GRAPHS chart legend renders in a DIFFERENT style: ChartLabel,
# GUID 0xE9C86B5E - BYTE-VERIFIED at exe 0x0076DD91, where the Graphs
# panel builder sub_76D3D0 pushes that GUID for the legend row text.
# Consequence: the chart legend has always rendered at ChartLabel's RAW
# size (20 / 26 / 39 pt at 1.5x / 2x / 3x), never at the squeezed Legend
# size (18 / 24 / 36). Anyone who computed chart text widths from the
# squeezed number was two points light at 2x and was reasoning about the
# wrong style. (This resolved open unknown U4 in the acceptance oracle,
# tools\uimap\emu\prove_chart_legend.py.)
#
# DO NOT REMOVE OR RETUNE THE SQUEEZE. It is still correct for its real
# target, the Data Views legend, which was measured and confirmed.
#
# The Graphs chart is fixed by GEOMETRY as of v2.55.0, not by type size:
# CodePatches::ApplyGraphLegendBudgetScale scales the panel builder's
# six-constant right-margin budget (plot-right reserve 110, checkbox left
# 108, swatch left 90/106, swatch 10x6, gap 4, text right 4) so the whole
# legend column is BORN at f. The real defect was never the font: the
# swatch never moved, its BUDGET was eaten - stock packs 16+2+10+3 = 31px
# into a 110px gutter, and at 2x a 32px checkbox plus a 2x text box put
# 52px into the SAME unscaled 110px.
#
# AND THE SQUEEZE'S OWN STATED MECHANISM IS A WARNING, NOT A RECIPE:
# a text box of round(stockBox * f) does NOT hold the same string, because
# glyph advance is NOT linear in point size. MEASURED over 17 strings at
# both 13pt and 26pt (tools\uimap\emu\emu_text_extent.py, PAIRS_13_26):
# ink grows x2.130 mean, sd 0.026 (pooled 2080/975 = 2.133; spread 2.085
# "Air Pollution" .. 2.188 "Commute Time"). NOT x2.00. That ~6% is exactly
# the shortfall this squeeze was invented to paper over. Size a box from
# the FONT, not from f (law L48).
# INFERENCE, not measurement: that ratio is a 13->26pt result. It has
# NOT been re-measured at the 1.5x/3x sizes; assuming it holds at 15/20/39
# pt is a model assumption.
#
# WHY WE CANNOT JUST ASK A FONT LIBRARY: the shipped faces are Monotype
# MicroType Express containers, <install>\Fonts\*.mxf (magic 'MXFN').
# There is NO .ttf/.otf anywhere in the install or this repo, so PIL /
# FreeType cannot be pointed at the real Arta - every metric we have is
# measured out of the game's own rendered pixels, residual +-3.8px.
# Note also that `Arta (Bold).mxf` DOES NOT EXIST (regular + italic only),
# so this style's `bold` param cannot change its metrics.
SIZE_SQUEEZE = {"Legend": 0.92}


def scale_size(size, factor, squeeze=1.0):
    r"""Scale a point size WITHOUT ever exceeding the box's own scale factor.

    THIS USED TO ROUND (floor(size*f + 0.5)) AND THAT CLIPPED EVERY LONG
    LABEL AT 1.5x (2026-08-06, found by the first eyes-on of that tier).

    The package builders scale every `area=` rect by EXACTLY f. Rounding the
    font can only ever push it the other way:

        stock  7 -> round 11 = x1.571   (+4.8% vs the box's x1.500)
        stock  9 -> round 14 = x1.556   (+3.7%)
        stock 11 -> round 17 = x1.545   (+3.0%)
        stock 13 -> round 20 = x1.538   (+2.6%)

    Every ODD size overshoots; even sizes are exact. Add the measured ink
    nonlinearity (~2.13x per doubling, not 2.00 - see emu_text_extent.py) and
    the longest strings overflow their box by ~9%, which is precisely the
    observed symptom: "Passenger Train", "Abandoned Buildings" and "No Kick Out
    Lower Wealth" clipped while "Ferry", "Water" and "Monorail" were fine.

    WHY NOBODY SAW IT FOR MONTHS. At 2x and 3x this CANNOT happen - doubling
    or tripling an integer never rounds, so the font ratio is exactly the box
    ratio and the only residual is the ink term, which the stock design's
    padding absorbs. 1.5x is the ONLY tier that can round, and it was the only
    tier never checked by eye. A defect that one tier is structurally immune to
    is invisible until a THIRD tier looks (law 53).

    THE FIX IS SCOPED TO NON-INTEGER FACTORS ONLY. Flooring everything looked
    equivalent at 2x - floor(n*2) == round(n*2) for whole n - but the selfcheck
    caught `Legend` changing 24 -> 23, because that style carries a deliberate
    SIZE_SQUEEZE that makes its product non-integer even at factor 2. So an
    integer factor keeps the original rounding, byte for byte, and only the
    tiers that can actually overshoot change. (The selfcheck earned its keep:
    "looks equivalent" was wrong within one line of code.)

    THE GUARD MUST TEST THE TIER FACTOR, NOT THE SQUEEZED PRODUCT (#163).
    This function used to take ONE argument, and `generate()` handed it
    `eff = factor * SIZE_SQUEEZE[name]`. So for the one style that carries a
    squeeze - Legend, 0.92 - the guard saw 1.84 at tier 2 and 2.76 at tier 3,
    never recognised an integer tier, and floored. That is the exact opposite of
    what the paragraph above promises, and it broke the artefact the paragraph
    was written to protect: `--selfcheck` has been RED ever since with
    `Legend gen=23 candidate=24`, and the shipped 3x table (Legend 36) could no
    longer be reproduced by its own generator (35).

    The failure was recorded in REGRESSION.md #142 as a "PRE-EXISTING selfcheck
    failure ... the factor-2 output cannot have moved". Both halves of that were
    wrong: it was INTRODUCED by #142's own edit, and factor-2 output is exactly
    what moved. Measured after this fix: all three tiers regenerate BYTE-
    IDENTICAL to the files that ship today, which is the proof that the tables
    were always right and only the generator drifted.
    """
    if float(factor).is_integer():
        return max(1, int(math.floor(size * factor * squeeze + 0.5)))
    return max(1, int(math.floor(size * factor * squeeze)))


def generate(factor):
    """Return (out_bytes, [(name, old, new), ...]) from the pristine table."""
    with open(DEFAULT_INI, "r", encoding="latin-1", newline="") as f:
        lines = f.read().splitlines(keepends=True)
    out = []
    changes = []
    in_styles = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            in_styles = (stripped.lower() == "[font styles]")
            out.append(line)
            continue
        if in_styles:
            m = STYLE_SIZE_RE.match(line)
            if m:
                old = int(m.group("size"))
                name = line.split("=", 1)[0].strip()
                sq = SIZE_SQUEEZE.get(name, 1.0)
                new = old if name in KEEP_STOCK else scale_size(old, factor, sq)
                changes.append((name, old, new))
                line = m.group("pre") + str(new) + m.group("post") + line[m.end():]
        out.append(line)
        # v2.49.0: emit the two stock-size HTML clone styles right after
        # their anchor, so generator output IS the shippable file (see
        # HTML_CLONE_BLOCK). Never scaled, at any tier.
        if in_styles and line.startswith(HTML_CLONE_ANCHOR):
            out.append(HTML_CLONE_BLOCK)
    blob = "".join(out).encode("latin-1")
    # Fail loudly rather than ship a file missing them - this whole block
    # exists because the miss was SILENT for five weeks.
    for nm in ("MessageHeaderHtml", "MessageBodyHtml"):
        if nm not in blob.decode("latin-1"):
            raise SystemExit("FATAL: %s missing from generated output - the "
                             "anchor %r was not found in FontStyle.default.ini"
                             % (nm, HTML_CLONE_ANCHOR))
    return blob, changes


def parse_sizes(path):
    """name -> size for every [Font Styles] entry (for the self-check)."""
    sizes = {}
    in_styles = False
    with open(path, "r", encoding="latin-1", newline="") as f:
        for line in f:
            s = line.strip()
            if s.startswith("[") and s.endswith("]"):
                in_styles = (s.lower() == "[font styles]")
                continue
            if not in_styles:
                continue
            m = STYLE_SIZE_RE.match(line)
            if m:
                sizes[line.split("=", 1)[0].strip()] = int(m.group("size"))
    return sizes


# Styles that exist ONLY in candidate.ini, never in the pristine default:
# the two stock-size HTML clone styles added by the task #42 news work (the
# HTML engine's size tables are .rdata-patched; these clones keep the popup
# body/header at stock size - see FONTSTYLE-RESEARCH.md / the HTML memory).
# The self-check tolerates exactly these; anything else is still a FAIL.
CANDIDATE_ONLY = {"MessageBodyHtml", "MessageHeaderHtml"}

# ---- v2.49.0 (#57 phase 4): THE GENERATOR NOW EMITS THE CLONES ----------
# These two styles used to be HAND-ADDED to candidate.ini AFTER generation,
# which made the generator's output UNSHIPPABLE and nobody noticed:
# PACKAGES.md's documented command
#     python fonts\make_fontstyle.py 3 packages\3x\FontStyle-3x.ini
# silently produced a file with NO clones, and CodePatches' popup retarget
# (0x52CCEE MessageHeader -> MessageHeaderHtml, src/CodePatches.cpp:56-62)
# then pointed at styles that do not exist. It "degrades softly", i.e. fails
# invisibly. MEASURED 2026-08-02: the deployed FontStyle-15x.ini and
# FontStyle-3x.ini had 62 styles and ZERO clones, while 2x had 64 - so the
# 1.5x and 3x tiers have been shipping that regression since v2.25.2.
#
# THEY ARE NEVER SCALED, AT ANY TIER. The game derives an HTML size index
# from these (idx=(4*size+8)/18) and the DLL scales the HTML size TABLE
# instead; scaling the style too would compound. That is why they are
# emitted verbatim rather than run through scale_size().
HTML_CLONE_ANCHOR = "MessageBodyUnderline"
HTML_CLONE_BLOCK = (
    '; HTML-index sources for the advisor/news message popups (SC4UIScale v2.19.0):\r\n'
    '; the game derives an HTML SIZE index from these (idx=(4*size+8)/18) and the\r\n'
    '; DLL scales the HTML size TABLE, so these must stay at STOCK sizes at every\r\n'
    '; tier or popup text compounds. The DLL retargets the popup builders from\r\n'
    '; MessageHeader/MessageBody to these clones (CodePatches::ApplyHtmlSizeScale).\r\n'
    'MessageHeaderHtml    = "StocletITC TT",    "16",  "bold|aa=bg|linespacing=2|xscale=1.2",   0x5c4b0914\r\n'
    'MessageBodyHtml      = "Arta",             "14",  "aa=bg|linespacing=2|xscale=0.95|xadvancescale=0.99",           0x5c4b0915\r\n'
)


def selfcheck():
    gen_bytes, changes = generate(2.0)
    gen_sizes = {name: new for (name, _old, new) in changes}
    cand_sizes = parse_sizes(CANDIDATE_INI)
    if gen_sizes.keys() != (cand_sizes.keys() - CANDIDATE_ONLY):
        print("SELFCHECK FAIL: style-name set differs from candidate.ini")
        print("  only in gen :", sorted(set(gen_sizes) - set(cand_sizes)))
        print("  only in cand:",
              sorted(set(cand_sizes) - set(gen_sizes) - CANDIDATE_ONLY))
        return 1
    cand_sizes = {n: v for n, v in cand_sizes.items() if n not in CANDIDATE_ONLY}
    mism = [(n, gen_sizes[n], cand_sizes[n]) for n in gen_sizes if gen_sizes[n] != cand_sizes[n]]
    if mism:
        print("SELFCHECK FAIL: %d size mismatches vs candidate.ini:" % len(mism))
        for n, g, c in mism:
            print("  %s gen=%d candidate=%d" % (n, g, c))
        return 1
    # v2.49.0: the STRONG check. Since the generator now emits the HTML clone
    # block itself, factor 2 must reproduce candidate.ini BYTE FOR BYTE apart
    # from candidate's hand-written 5-line ";;" provenance banner. A size-only
    # check passed happily while the clones were missing entirely - which is
    # exactly how the 1.5x/3x regression shipped.
    cand_raw = open(CANDIDATE_INI, "r", encoding="latin-1", newline="").read()
    cand_lines = cand_raw.splitlines(keepends=True)
    n_banner = 0
    while n_banner < len(cand_lines) and cand_lines[n_banner].startswith(";;"):
        n_banner += 1
    cand_body = "".join(cand_lines[n_banner:])
    gen_body = gen_bytes.decode("latin-1")
    if gen_body != cand_body:
        print("SELFCHECK FAIL: factor 2 output is not byte-identical to "
              "candidate.ini (ignoring its %d-line banner)" % n_banner)
        import difflib
        for l in list(difflib.unified_diff(
                cand_body.splitlines(), gen_body.splitlines(),
                "candidate", "generated", lineterm="", n=0))[:20]:
            print("  " + l)
        return 1
    for nm in sorted(CANDIDATE_ONLY):
        if nm not in gen_body:
            print("SELFCHECK FAIL: %s absent from generated output" % nm)
            return 1
    print("SELFCHECK OK: factor 2 reproduces all %d candidate.ini sizes exactly,"
          % len(gen_sizes))
    print("              and the full file BYTE-FOR-BYTE (banner aside), "
          "clones included.")
    return 0


def main():
    if len(sys.argv) == 2 and sys.argv[1] == "--selfcheck":
        sys.exit(selfcheck())
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    factor = float(sys.argv[1])
    out_path = sys.argv[2]
    out_bytes, changes = generate(factor)
    with open(out_path, "wb") as f:
        f.write(out_bytes)
    news = [c[2] for c in changes]
    print("Wrote %s  (factor %g, %d styles, size range %d..%d)"
          % (out_path, factor, len(changes), min(news), max(news)))
    # report the half-integer cases for 1.5x
    halfups = [(n, o, v) for (n, o, v) in changes if abs(o * factor - math.floor(o * factor)) > 1e-9]
    if halfups:
        seen = sorted({(o, v) for (_n, o, v) in halfups})
        print("  round-half-up applied to %d entries; 1x->scaled: %s"
              % (len(halfups), ", ".join("%d->%d" % (o, v) for o, v in seen)))


if __name__ == "__main__":
    main()
