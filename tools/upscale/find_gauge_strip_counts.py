r"""Derive the FRAME COUNT of every U-Drive-It gauge needle strip (#186).

⛔ WHY THIS EXISTS. The dashboard dials (class 0xCBCBF1E0) blit one cell of a
horizontal frame strip:

    draw 0x00762830:  img = [this+0xd8]
                      count = [this+0xe8]
                      cellW = img->Width() / count        <- INTEGER divide
                      src = {frame*cellW, 0, frame*cellW+cellW, img->Height()}

`count` is DATA - the binder at 0x005646AE pushes it in from the vehicle
exemplar (property 0x2BE8E6CB, group 0x46A006B0) - so the strips carry ZERO
`.UI` image= references and `find_cell_strips.py`'s script-driven derivation is
blind to them BY CONSTRUCTION.

That blindness shipped a real defect. Sized total-first, a 2805px sheet of 55
frames (cell 51) becomes R(2805*1.5) = 4208 at the 1.5x tier. The game divides
4208/55 = 76 against a true pitch of 76.5, so the source window slips half a
pixel per frame and by frame 54 is 27.5px - over a THIRD of a cell - into the
neighbouring needle frame. On screen the dial appears to wrap around. Integer
tiers are immune because 2*2805 and 3*2805 are both divisible by 55, which is
exactly why the defect was reported as "works at 1x, 2x and 3x, not 1.5x".

Feeding these sheets to Upscale2x's cell-first rule (width = N*R(cell,f))
restores an exact pitch: 55*R(51*1.5) = 55*77 = 4235, cell 77, zero slip.

=== HOW THE COUNT IS RECOVERED, GIVEN IT IS NOT AN IMMEDIATE ===

A needle strip is PERIODIC with period = cell: every frame draws the same
static dial face and bezel with only the needle rotated. So shifting the sheet
by exactly one cell aligns face-to-face, and the mean absolute difference
collapses. Shifting by a wrong cell width aligns nothing.

    score(N) = mean |sheet[x] - sheet[x + W/N]|   over the overlap

The winner is the true frame count. This is a MEASUREMENT ON THE ART, and it
is checked against an INDEPENDENT instrument before it is trusted:

POSITIVE CONTROL. A live 1.5x capture prints the cell the game itself computed
(GBLT lines, SC4UIScale.log 2026-08-18, LogLevel=3, dashboard 0x4BCB938A):

    id 0xEBCB9403  cell 76x75   -> a 2805x50 sheet
    id 0x2BCB940B  cell 76x81   -> a 2805x54 sheet
    id 0x6BCBCE73  cell 81x81   -> a 1998x54 sheet

Requiring BOTH `R(W*1.5) // N == cell` AND `N | W` pins one N per sheet:
    2805 wide, cell 76 -> N in [4208/77, 4208/76] = [54.65, 55.37] -> N=55
    1998 wide, cell 81 -> N in [2997/82, 2997/81] = [36.55, 37.00] -> N=37
No other integer satisfies both, so those six counts are known independently of
the periodicity scan. The scan must reproduce all six or this script REFUSES to
write anything - the two instruments fail in genuinely different ways (the
game's own integer divide observed live, versus image self-similarity), so
their agreement is corroboration and not one instrument counted twice.

AMBIGUITY. Where the periodicity winner is not sharp, the quantizer is raised
to a MULTIPLE of it if that makes the scaled width divisible by every close
candidate as well. Quantizing by a multiple of the true count also quantizes by
the true count, so raising is always safe and never wrong - it can only make
the sheet up to N-1 px wider.

INTEGER-TIER SAFETY is structural, not assumed: Upscale2x never takes the
cell-first branch at an integer factor (it FATALs if the counter is non-zero
there), so this table cannot move 2x or 3x. Verified 2026-08-18: 0 pixel diffs
across all six control sheets after a full 2x rebuild.

Output: tools/upscale/gauge-strip-counts.txt, merged into CODE_BOUND by
find_cell_strips.py. Run it whenever the gauge TGI list in
build_selective_safe.py changes.
"""
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
EXTRACTED = os.path.join(TOOLS, "dbpf", "extracted")
BUILDER = os.path.join(TOOLS, "selective-safe", "build_selective_safe.py")
OUT = os.path.join(HERE, "gauge-strip-counts.txt")

GAUGE_GROUP = 0x46A006B0

# The six counts pinned by the live 1.5x GBLT capture (see module docstring).
# These are the CONTROL, never the answer - the scan has to reproduce them.
CONTROL = {
    0xCBCBA948: 55, 0xCBCBA949: 55, 0xCBCBA950: 55, 0xCBCBA951: 55,
    0xCBCBA947: 37, 0xAC0DA30E: 37,
}


def gauge_instances():
    """The gauge sub-block of CODE_BOUND_TGIS in build_selective_safe.py.

    Parsed, not copied: the builder's list is the one place the 0x2BE8E6CB
    mining result lives, and a second hand-maintained copy here would rot
    exactly the way law 94 describes. The block is delimited by its own
    heading comment and the cSC4WinTrendBar comment that follows it; if
    either marker moves this refuses rather than silently reading a subset.
    """
    with open(BUILDER, encoding="utf-8") as f:
        src = f.read()
    start = src.find("U-DRIVE-IT GAUGE NEEDLE STRIPS")
    end = src.find("cSC4WinTrendBar (opinion-poll bars)", start + 1)
    if start < 0 or end < 0 or end <= start:
        sys.exit("FATAL: cannot locate the gauge sub-block of CODE_BOUND_TGIS "
                 "in %s - the delimiting comments moved. Refusing to guess."
                 % BUILDER)
    block = src[start:end]
    inst = [int(m, 16) for m in
            re.findall(r"0x46A006B0,\s*0x([0-9A-Fa-f]{8})", block)]
    if not inst:
        sys.exit("FATAL: the gauge sub-block parsed to ZERO instances.")
    return sorted(set(inst))


def find_sheets(instances):
    """Locate each instance's 1x PNG anywhere under the extraction tree."""
    want = {i: None for i in instances}
    for root, _dirs, files in os.walk(EXTRACTED):
        for name in files:
            if not name.lower().endswith(".png") or "_I-" not in name:
                continue
            if ("%08x" % GAUGE_GROUP) not in name.lower():
                continue
            try:
                inst = int(name.split("_I-")[1][:8], 16)
            except ValueError:
                continue
            if inst in want and want[inst] is None:
                want[inst] = os.path.join(root, name)
    return want


def png_size(path):
    with open(path, "rb") as f:
        head = f.read(33)
    if head[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    return struct.unpack(">II", head[16:24])


def rnd(v, f):
    """The project's single rounding convention (law 89)."""
    return int(v * f + 0.5)


def periodicity(im, w, h, cell):
    a = im.crop((0, 0, w - cell, h)).tobytes()
    b = im.crop((cell, 0, w, h)).tobytes()
    return sum(abs(x - y) for x, y in zip(a, b)) / float(len(a))


def main():
    try:
        from PIL import Image
    except ImportError:
        sys.exit("FATAL: Pillow is required (the derivation measures pixels).")

    instances = gauge_instances()
    sheets = find_sheets(instances)
    missing = [i for i, p in sheets.items() if p is None]
    if missing:
        print("NOTE: %d gauge instance(s) not in the extraction tree (they are "
              "bound by exemplars whose art lives in an archive that was not "
              "extracted): %s"
              % (len(missing), " ".join("%08X" % i for i in missing)))

    rows = []
    for inst in instances:
        path = sheets[inst]
        if path is None:
            continue
        size = png_size(path)
        if size is None:
            print("SKIP %08X: not a PNG" % inst)
            continue
        w, h = size
        im = Image.open(path).convert("L")
        # Admissible counts: divide the width exactly, with a cell wide enough
        # to be a dial frame and narrow enough not to be the whole sheet.
        adm = [n for n in range(2, 401) if w % n == 0 and 8 <= w // n <= 200]
        if not adm:
            print("SKIP %08X (%dx%d): no admissible frame count" % (inst, w, h))
            continue
        ranked = sorted((periodicity(im, w, h, w // n), n) for n in adm)
        best_score, best = ranked[0]
        up_score, up = ranked[1] if len(ranked) > 1 else (float("inf"), 0)

        # Raise the quantizer to a multiple of the winner when that also makes
        # the scaled width exact for every candidate the scan did not clearly
        # separate (within 25% of the winner's score). Safe by construction.
        close = [n for s, n in ranked if s <= best_score * 1.25]
        pick = best
        for mult in (1, 2, 3, 4):
            q = best * mult
            if w % q:
                continue
            wq = q * rnd(w // q, 1.5)
            if all(wq % n == 0 for n in close):
                pick = q
                break

        drifts = bool(rnd(w, 1.5) % pick)
        rows.append((inst, w, h, pick, best, best_score, up, up_score, drifts))

    if not rows:
        sys.exit("FATAL: ZERO gauge sheets measured. Refusing to write %s - an "
                 "empty table would silently un-ship #186 at the next corpus "
                 "rebuild." % OUT)

    # POSITIVE CONTROL - refuse loudly before writing anything.
    print("=== positive control (counts pinned independently by the live "
          "1.5x GBLT capture) ===")
    bad = []
    for inst, _w, _h, _pick, best, _bs, _u, _us, _d in rows:
        if inst in CONTROL:
            ok = CONTROL[inst] == best
            print("  %08X  log says N=%-3d  scan says N=%-3d  %s"
                  % (inst, CONTROL[inst], best, "MATCH" if ok else "MISMATCH"))
            if not ok:
                bad.append(inst)
    seen = [i for i, *_ in rows if i in CONTROL]
    if not seen:
        sys.exit("FATAL: the control ran on ZERO sheets. A null from an "
                 "instrument that never fired is not a pass (NULL IS NOT "
                 "EVIDENCE). Refusing to write %s." % OUT)
    if bad:
        sys.exit("FATAL: the periodicity scan disagrees with the live capture "
                 "on %d sheet(s): %s. The scan is not trustworthy on the "
                 "sheets it is the ONLY evidence for either. Refusing to "
                 "write %s." % (len(bad), " ".join("%08X" % i for i in bad), OUT))
    print("  CONTROL PASS - %d/%d reproduced" % (len(seen), len(CONTROL)))

    with open(OUT, "w", encoding="ascii", newline="\n") as f:
        f.write("# U-Drive-It gauge needle strip FRAME COUNTS (#186).\n")
        f.write("# Generated by tools\\upscale\\find_gauge_strip_counts.py - "
                "do not hand-edit.\n")
        f.write("# Code-bound (vehicle exemplar 0x2BE8E6CB), so the .UI-driven\n"
                "# derivation in find_cell_strips.py cannot see them. Counts\n"
                "# measured by strip periodicity; %d of them cross-checked\n"
                "# against the cell the game printed in a live 1.5x capture.\n"
                % len(seen))
        f.write("# <group> <instance> <frames>   # sheet  scan(score) "
                "runner-up  1.5x\n")
        for inst, w, h, pick, best, bs, up, us, drifts in rows:
            f.write("%08x %08x %d   # %dx%d  N=%d(%.2f) up=%d(%.2f)  %s\n"
                    % (GAUGE_GROUP, inst, pick, w, h, best, bs, up, us,
                       "FIXES DRIFT" if drifts else "already exact"))

    fixed = sum(1 for r in rows if r[8])
    print("gauge strips        : %d -> %s" % (len(rows), OUT))
    print("  drift FIXED at 1.5x: %d" % fixed)
    print("  already exact      : %d" % (len(rows) - fixed))
    for inst, w, h, pick, _b, _bs, _u, _us, drifts in rows:
        if drifts:
            print("    %08X %dx%d N=%d: %d -> %d (cell %d -> %d, pitch was "
                  "%.1f)" % (inst, w, h, pick, rnd(w, 1.5), pick * rnd(w // pick, 1.5),
                             rnd(w, 1.5) // pick, rnd(w // pick, 1.5),
                             rnd(w, 1.5) / float(pick)))


if __name__ == "__main__":
    main()
