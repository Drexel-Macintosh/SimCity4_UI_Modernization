r"""DERIVE `no-smooth.txt`: sheets whose EXACT PIXEL EDGES are measured by a
downstream builder, and which therefore must keep NEAREST-NEIGHBOUR.

⛔ WHY THIS EXISTS (#175, 2026-08-16). The smooth resample was switched on for
every sheet with no colour key, and `build_selective_safe.py` refused the build:

    FATAL seat 0x0A15C7D8: aperture 71x77 != face 72x78

`seat_faces_on_apertures` (#152) does not read the advisor frame's geometry from
the `.UI` - it SCANS THE FRAME PNG for the aperture the 3D head sits in, and
seats the face on what it finds. Catmull-Rom turns that hard aperture edge into
a one-pixel gradient, the scan stops one pixel earlier, and every face would
have been seated wrong. The guard did exactly its job and stopped the build.

So: art that is DRAWN can be smoothed; art that is MEASURED cannot.

⚠ DERIVED, NOT HAND-WRITTEN (law 94). The list is generated from
`ADVISOR_FACE_SEATS` in `build_selective_safe.py`, so if a seat is added or a
frame's TGI changes, this list follows. A hand-list would silently rot and the
failure mode is seven faces seated one pixel off - which is exactly the class of
defect #152 existed to fix.

    python make_no_smooth.py [--check]

`--check` exits non-zero if the file on disk differs from what would be
generated, so a stale list fails a build instead of shipping.

Offline. Reads one source file, writes one list.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
SRC = os.path.join(TOOLS, "selective-safe", "build_selective_safe.py")
OUT = os.path.join(HERE, "no-smooth.txt")

# (faceId, frameId, artGroup, artInstance, (dx,dy))
ROW = re.compile(r"\(\s*0x([0-9A-Fa-f]{8})\s*,\s*0x([0-9A-Fa-f]{8})\s*,"
                 r"\s*0x([0-9A-Fa-f]{8})\s*,\s*0x([0-9A-Fa-f]{8})\s*,")


# ---------------------------------------------------------------------------
# ART THAT IS READ AS DATA, NOT DRAWN AS A PICTURE.
#
# ⛔ THE RULE, and it is the whole point of this file: a smooth resample is safe
# for art the engine BLITS and unsafe for art anything SAMPLES or MEASURES.
# Interpolation changes the value returned at a coordinate, and these sheets are
# consulted for values, not shown to the player.
#
# Two independent members so far, both caught the hard way on 2026-08-16:
#
#  1. ADVISOR FRAMES - MEASURED BY OUR OWN BUILDER. `seat_faces_on_apertures`
#     (#152) scans the frame PNG for the aperture the 3D head sits in. A
#     softened edge moves the scan result and the seat guard refuses the build
#     (`FATAL seat 0x0A15C7D8: aperture 71x77 != face 72x78`). Derived from
#     ADVISOR_FACE_SEATS below, so it tracks that table.
#
#  2. THE TREND-BAR COLOUR RAMP - SAMPLED BY THE GAME. `cSC4WinTrendBar`
#     (clsid 0xAA5C2F86, Draw 0x7BF0A0) is handed {46A006B0,14015580} as a
#     green-to-red LOOKUP GRADIENT and {46A006B0,14015584} as the marker strip,
#     pushed in by the polls controller at 0x7ED4AC via SetImages - they have
#     ZERO .UI refs, so no corpus scan can find them. Blurring a palette changes
#     the colour it returns for a given rating. USER-REPORTED: "The Mayor rating
#     isn't correct it's only half filled". The marker strip is magenta-keyed
#     and was already refused; the ramp had no key and was not.
#
# These two are listed explicitly BECAUSE THEY ARE CODE-BOUND. There is no .UI
# to derive them from - that is exactly why they were missed. Provenance is
# tools\research\SC4-UI-ENGINE.md, widget catalogue, cSC4WinTrendBar row.
#
# ⚠ ADDING HERE IS CHEAP AND REMOVING IS EXPENSIVE. A sheet that stays NEAREST
# merely keeps today's look; a sampled sheet that gets smoothed returns wrong
# values and the failure is silent. When unsure, list it.
DATA_ART = [
    (0x46A006B0, 0x14015580),   # cSC4WinTrendBar green->red lookup gradient
    (0x46A006B0, 0x14015584),   # cSC4WinTrendBar marker strip (keyed anyway)
]


def derive():
    with open(SRC, "r", encoding="utf-8-sig") as fh:
        txt = fh.read()
    m = re.search(r"ADVISOR_FACE_SEATS\s*=\s*\[(.*?)\]", txt, re.S)
    if not m:
        sys.exit("FATAL: ADVISOR_FACE_SEATS not found in %s - the seat table "
                 "moved or was renamed. This list CANNOT be guessed; fix the "
                 "parse rather than hand-writing it." % SRC)
    rows = ROW.findall(m.group(1))
    if not rows:
        sys.exit("FATAL: ADVISOR_FACE_SEATS parsed to ZERO rows. An empty "
                 "no-smooth list would smooth every measured sheet and trip "
                 "the seat guard - refusing to write it.")
    seen, out = set(), []
    for _face, _frame, g, i in rows:
        key = (g.upper(), i.upper())
        if key in seen:
            continue
        seen.add(key)
        out.append(key)
    # the code-bound sampled art, which no .UI scan can reach
    for g, i in DATA_ART:
        key = ("%08X" % g, "%08X" % i)
        if key in seen:
            continue
        seen.add(key)
        out.append(key)
    return out


def render(rows):
    lines = [
        "# no-smooth.txt - GENERATED by make_no_smooth.py. Do not hand-edit.",
        "#",
        "# Sheets whose exact pixel EDGES are measured by a downstream builder,",
        "# so they must keep nearest-neighbour even at a fractional factor.",
        "#",
        "# Sources: build_selective_safe.py::ADVISOR_FACE_SEATS (#152 face",
        "# seat pass SCANS these frame PNGs for the head aperture. A smoothed",
        "# edge moves what it finds and the seat guard refuses the build:",
        "#     FATAL seat 0x0A15C7D8: aperture 71x77 != face 72x78",
        "#",
        "# group    instance",
    ]
    for g, i in rows:
        lines.append("%s %s" % (g.lower(), i.lower()))
    return "\n".join(lines) + "\n"


def main():
    rows = derive()
    text = render(rows)
    if "--check" in sys.argv:
        cur = ""
        if os.path.isfile(OUT):
            with open(OUT, "r", encoding="utf-8") as fh:
                cur = fh.read()
        if cur != text:
            print("STALE: %s does not match ADVISOR_FACE_SEATS "
                  "(regenerate with: python make_no_smooth.py)" % OUT)
            return 1
        print("no-smooth.txt is current (%d sheet(s))" % len(rows))
        return 0
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    print("wrote %s - %d measured sheet(s) will keep NEAREST" % (OUT, len(rows)))
    return 0


sys.exit(main())
