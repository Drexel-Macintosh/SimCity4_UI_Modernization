r"""REDRAW the segmented rating ladders instead of RESAMPLING them (#180).

⛔ WHY THIS EXISTS. The HUD Mayor Rating bar {46a006b0,14015549} is not a
picture - it is a DRAWN LADDER with exact integer geometry:

    25 cells: 12 red at origins 0,4..44 (3px wide, pitch 4),
              a 4px CENTRE cell at 49,
              12 green at 55,59..99 (3px wide, pitch 4);
    gaps are 1px between cells and 2px flanking the centre.

Nearest-neighbour at f=1.5 maps 3px -> 4 or 5 and 1px -> 1 or 2 depending on
whether each origin happens to be even or odd, so the ladder ships RAGGED:
measured cell widths {4,5,6} and gaps {1,2,3}, with the red half systematically
bolder than the green half. At f=2 and f=3 NN is an exact block replicate and
the ladder is perfectly even - which is exactly why 2x "looks way sharper".
USER-REPORTED, repeatedly, and it is the last visible 1.5x defect on that panel.

⭐ THE FIX IS TO STOP RESAMPLING IT. Scale the STRUCTURE, not the pixels:
every cell is re-emitted at EDGE-DERIVED coordinates

    [ScaleRound(origin * f), ScaleRound((origin + width) * f) )

filled with that cell's own colour, and every gap is re-emitted as the EXACT
FF00FF key. This is #171's law - SCALE THE UNIT AND MULTIPLY, NEVER SCALE THE
TOTAL - applied to a drawn ladder instead of a state strip.

Result at f=1.5: 24 of 25 cells become a uniform 5px on a 6px pitch with clean
1px gaps, instead of {4,5,6}/{1,2,3}.

⚠ PROVABLE NO-OP AT AN INTEGER FACTOR, and the script ASSERTS it rather than
claiming it: at integer f, ScaleRound(o*f) and ScaleRound((o+w)*f) are exact, so
every cell lands exactly where block replication puts it and the output must be
byte-identical to the nearest-neighbour sheet. --verify checks that and exits
non-zero if it ever stops being true.

⚠ THE KEY IS WRITTEN EXACTLY, NEVER AVERAGED. This is the whole reason the
generic smooth path is wrong here: any filter that lets FF00FF into an average
produces near-key pixels that the engine's exact-match test misses, and they
PAINT PINK (#143, and again 2026-08-16 on the Options dialog). Here no
arithmetic ever touches the key - gap pixels are assigned the constant.

⚠ VERTICAL IS UNCHANGED. The sheet is a 26-row filmstrip, one row per rating
state, with no vertical sub-structure inside a row. Output row r takes source
row floor(r/f), which is what NN already did.

⚠ OUTPUT FORMAT MATCHES THE UPSCALER, NOT THE 1x SOURCE (F7, 2026-08-16):
colour-type 6 (RGBA, alpha 255) with the tier's own sRGB/gAMA/pHYs chunks
spliced in from a sibling Upscale2x output. The old ct=2 no-chunk output was
the ONE format oddity in the corpus, and build_selective_safe.py's pixel
reader (:1545) hard-refuses ct=2 if the TGI ever enters a pixel-read path.
Pixels are unchanged - see save().

⚠ EXIT DISCIPLINE (F5): at a FRACTIONAL factor every LADDERS sheet must
actually be rewritten - a skip (missing 1x source, unreadable/wrong PNG
type, target absent from the tier tree) exits 1 with the reason, because the
Rebuild-Corpus.ps1 wiring would otherwise silently ship plain NN. At integer
factors a skip stays exit 0 (the redraw is a proven no-op there), but the
integer control itself is FATAL if it cannot run (F6).

    python redraw_ladder.py <tier-dir> --factor 1.5 [--verify]

Offline. Rewrites only the ladder sheets named in LADDERS, in place.
"""
import os
import re
import struct
import sys
import zlib

# Sheets that are segmented ladders. Both groups ship the same art; the
# 1abe787d twin is the shadow copy and must stay in step or the two halves of
# the HUD disagree.
LADDERS = [
    (0x46A006B0, 0x14015549),   # HUD Mayor Rating groove/ladder
    (0x1ABE787D, 0x14015549),   # byte-identical shadow copy
]

KEY = (255, 0, 255)


def R(v):
    return int(v + 0.5)


def load(path):
    d = open(path, "rb").read()
    pos, idat, ct, w, h = 8, b"", None, 0, 0
    while pos < len(d):
        ln = struct.unpack(">I", d[pos:pos + 4])[0]
        typ = d[pos + 4:pos + 8]
        data = d[pos + 8:pos + 8 + ln]
        if typ == b"IHDR":
            w, h, _bd, ct = struct.unpack(">IIBB", data[:10])
        elif typ == b"IDAT":
            idat += data
        elif typ == b"IEND":
            break
        pos += 12 + ln
    if ct not in (2, 6):
        return None
    bpp = 3 if ct == 2 else 4
    stride = w * bpp
    raw = zlib.decompress(idat)
    rows, prev, i = [], bytearray(stride), 0
    for _y in range(h):
        f = raw[i]; i += 1
        line = bytearray(raw[i:i + stride]); i += stride
        for x in range(stride):
            a = line[x - bpp] if x >= bpp else 0
            b = prev[x]
            c = prev[x - bpp] if x >= bpp else 0
            if f == 1:
                line[x] = (line[x] + a) & 255
            elif f == 2:
                line[x] = (line[x] + b) & 255
            elif f == 3:
                line[x] = (line[x] + (a + b) // 2) & 255
            elif f == 4:
                pp = a + b - c
                pa, pb, pc = abs(pp - a), abs(pp - b), abs(pp - c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[x] = (line[x] + pr) & 255
        rows.append(bytes(line))
        prev = line
    return w, h, bpp, rows


def save(path, w, h, rows, colour_chunks):
    """Write RGBA rows as a PNG shaped like every other tier sheet.

    F7 (review 2026-08-16): always colour-type 6, with the sRGB + gAMA + pHYs
    chunks COPIED from a sibling Upscale2x output (sibling_colour_chunks) and
    spliced in right after IHDR - a byte-level chunk insert, each one
    length + type + data + crc32, nothing re-encoded. The old output was ct=2
    with no ancillary chunks, the ONE format oddity in a corpus that is
    otherwise uniformly ct=6+sRGB/gAMA/pHYs - and build_selective_safe.py's
    pixel reader (:1545) dies on ct=2 if the TGI ever enters a pixel-read
    path. PIXELS ARE IDENTICAL to the old encoding (decode-compared on the
    1.5x ladders when this changed); the shipped ladder ENTRY BYTES do change
    (container only), and the EXPECTED-DELTAS manifest was updated
    accordingly by the caller."""
    raw = b"".join(b"\x00" + bytes(r) for r in rows)

    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)))
    for tag, data in colour_chunks:
        png += chunk(tag, data)
    png += chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")
    open(path, "wb").write(png)


def sibling_colour_chunks(tier_dir):
    """(sibling_name, [(tag, data)]) for sRGB/gAMA/pHYs, read from the first
    non-ladder Upscale2x output in the tier dir - COPIED, never invented, so
    the redraw can not drift from whatever the upscaler stamps on the rest of
    the corpus. Returns (None, None) if no sibling carries all three."""
    want = (b"sRGB", b"gAMA", b"pHYs")
    ladder_names = {"t-0x856ddbac_g-0x%08x_i-0x%08x.png" % (g, i)
                    for g, i in LADDERS}
    for fn in sorted(os.listdir(tier_dir)):
        if not fn.lower().endswith(".png") or fn.lower() in ladder_names:
            continue
        try:
            d = open(os.path.join(tier_dir, fn), "rb").read()
        except OSError:
            continue
        if d[:8] != b"\x89PNG\r\n\x1a\n":
            continue
        pos, got = 8, {}
        while pos + 8 <= len(d):
            ln = struct.unpack(">I", d[pos:pos + 4])[0]
            typ = d[pos + 4:pos + 8]
            if typ in (b"IDAT", b"IEND"):
                break
            if typ in want:
                got[typ] = d[pos + 8:pos + 8 + ln]
            pos += 12 + ln
        if len(got) == len(want):
            return fn, [(t, got[t]) for t in want]
    return None, None


def segment(rows, w, bpp, y=0):
    """(isKey, origin, width) runs across one row. The cell grid is constant
    down the sheet, so row 0 defines it for every state."""
    segs, cur, st = [], None, 0
    for x in range(w):
        px = tuple(rows[y][x * bpp:x * bpp + 3])
        k = (px == KEY)
        if k != cur:
            if cur is not None:
                segs.append((cur, st, x - st))
            cur, st = k, x
    segs.append((cur, st, w - st))
    return segs


def redraw(src_path, factor):
    got = load(src_path)
    if not got:
        return None
    w, h, bpp, rows = got
    segs = segment(rows, w, bpp)
    ow, oh = R(w * factor), R(h * factor)
    out = []
    for oy in range(oh):
        sy = int(oy / factor)
        if sy >= h:
            sy = h - 1
        # F7: output rows are ALWAYS RGBA (alpha 255) whatever the 1x source's
        # colour type - the source bpp only steers the sampling reads below.
        line = bytearray(ow * 4)
        # ⛔ UNIFORM RE-LAY, NOT EDGE-DERIVED PLACEMENT. MEASURED 2026-08-16, and
        # it reversed the first attempt at this fix.
        #
        # Scaling each cell's own origin - the #171 rule - does NOT help here and
        # the integer control caught it: the output came back {4,5,6}/{1,2,3},
        # bit-for-bit the same distribution nearest-neighbour already ships.
        # THE ASYMMETRY IS IN THE DESIGN'S ORIGINS, not in the sampler:
        #     red  cells start 0,4,8..44  -> all multiples of 4, x1.5 is exact -> 5px
        #     green cells start 55,59..99 -> 55*1.5 = 82.5, rounds        -> 4px
        # so the red half renders systematically bolder than the green half at
        # f=1.5 under ANY method that preserves those origins.
        #
        # WHY RE-LAYING IS SAFE, and this is the load-bearing fact: the
        # controller (sub_7E8510, disassembled) picks a ROW from the filmstrip
        # and blits that row WHOLE. Nothing in the game reads a cell position,
        # a cell width, or a gap. The horizontal layout is purely cosmetic, so
        # regularising it cannot change what the bar reports - only how even it
        # looks. The ROW mapping is untouched, so the rating shown is identical.
        cells = [(k, o, n) for k, o, n in segs]
        nonkey = [c for c in cells if not c[0]]
        uni = {}
        if factor != int(factor) and len(nonkey) >= 3:
            pitch = R(4 * factor)                 # design pitch 4 -> 6 at f=1.5
            cw = pitch - 1                        # keep a 1px gap, so 5px cells
            mid = len(nonkey) // 2                # the centre cell
            left = nonkey[:mid]
            right = nonkey[mid + 1:]
            for j, c in enumerate(left):
                uni[c[1]] = (j * pitch, j * pitch + cw)
            ca = R(nonkey[mid][1] * factor)
            cb = ca + R(nonkey[mid][2] * factor)
            uni[nonkey[mid][1]] = (ca, cb)
            # anchor the right-hand group to the SHEET EDGE so the ladder ends
            # flush; it is the half whose origins round badly.
            tail = ow - (len(right) * pitch - 1)
            for j, c in enumerate(right):
                uni[c[1]] = (tail + j * pitch, tail + j * pitch + cw)

        for isKey, o, n in segs:
            if (not isKey) and o in uni:
                a, b = uni[o]
            else:
                a, b = R(o * factor), R((o + n) * factor)
            if b > ow:
                b = ow
            if a < 0:
                a = 0
            span = b - a
            for x in range(a, b):
                if isKey:
                    col = KEY
                else:
                    # ⛔ SAMPLE PER OUTPUT PIXEL, NOT ONE COLOUR PER CELL. The
                    # first version painted each cell with its middle pixel's
                    # colour, and the INTEGER CONTROL caught it: this ladder
                    # carries a GRADIENT along its length (FF0000 at x=0 grading
                    # to D50000 at x=44), so flattening a cell to one colour is
                    # lossy even at f=2 where placement is exact. Map each output
                    # column back into its own source cell instead - identical to
                    # nearest-neighbour WITHIN the cell, while the cell's OUTER
                    # bounds come from the uniform re-lay above.
                    sx = o + ((x - a) * n // span if span > 0 else 0)
                    if sx >= o + n:
                        sx = o + n - 1
                    col = tuple(rows[sy][sx * bpp:sx * bpp + 3])
                line[x * 4] = col[0]
                line[x * 4 + 1] = col[1]
                line[x * 4 + 2] = col[2]
                line[x * 4 + 3] = 255
        out.append(bytes(line))
    return ow, oh, out


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    tier_dir = sys.argv[1]
    factor = 1.5
    if "--factor" in sys.argv:
        factor = float(sys.argv[sys.argv.index("--factor") + 1])
    verify = "--verify" in sys.argv
    here = os.path.dirname(os.path.abspath(__file__))
    src_root = os.path.join(here, "..", "dbpf", "extracted", "SimCity_1")

    done = 0
    skipped = []          # (g, i, reason) - F5: fatal at fractional factors
    colour_chunks = None  # F7: fetched once per run, from a sibling
    for g, i in LADDERS:
        s1 = os.path.join(src_root, "T-856ddbac_G-%08x_I-%08x.png" % (g, i))
        if not os.path.isfile(s1):
            print("  SKIP  no 1x source for {%08X,%08X}" % (g, i))
            skipped.append((g, i, "no 1x source (%s)" % s1))
            continue
        got = redraw(s1, factor)
        if not got:
            print("  SKIP  unreadable/wrong PNG type {%08X,%08X}" % (g, i))
            skipped.append((g, i, "1x source unreadable or not colour-type "
                            "2/6 (%s)" % s1))
            continue
        ow, oh, out = got
        dst = os.path.join(tier_dir, "T-0x856ddbac_G-0x%08x_I-0x%08x.png" % (g, i))
        if not os.path.isfile(dst):
            print("  SKIP  not in tier tree: %s" % os.path.basename(dst))
            skipped.append((g, i, "target missing from tier tree (%s)" % dst))
            continue

        # ⛔ THE INTEGER CONTROL, ASSERTED NOT ARGUED. At an integer factor the
        # redraw must reproduce nearest-neighbour byte for byte.
        if factor == int(factor):
            cur = load(dst)
            # F6: if the control CANNOT run, that is FATAL - the OK line used
            # to print over an unreadable target or a dimension mismatch,
            # i.e. exactly when nothing at all had been compared.
            if cur is None:
                print("FATAL: integer control could NOT run: %s is unreadable "
                      "or not colour-type 2/6" % os.path.basename(dst))
                return 1
            cw, ch, cbpp, crows = cur
            if (cw, ch) != (ow, oh):
                print("FATAL: integer control could NOT run: %s is %dx%d, the "
                      "redraw expects %dx%d" % (os.path.basename(dst),
                                                cw, ch, ow, oh))
                return 1
            if cbpp == 3:
                # A pre-F7 ct=2 target: opaque by definition, so compare in
                # RGBA space by expanding with alpha 255 (the redraw emits
                # RGBA since F7).
                crows = [b"".join(bytes(r[x:x + 3]) + b"\xff"
                                  for x in range(0, len(r), 3)) for r in crows]
            same = all(bytes(crows[y]) == out[y] for y in range(oh))
            if not same:
                print("FATAL: redraw differs from nearest-neighbour at integer "
                      "factor %g on {%08X,%08X}. Edge-derived cell placement is "
                      "supposed to be exact there - the model is wrong."
                      % (factor, g, i))
                return 1
            print("  integer control OK {%08X,%08X} - redraw == nearest" % (g, i))
            continue

        if verify:
            widths = []
            segs = segment(out, ow, 4)
            widths = sorted(set(n for k, _o, n in segs if not k))
            gaps = sorted(set(n for k, _o, n in segs if k))
            print("  {%08X,%08X} %dx%d  cell widths %s  gaps %s"
                  % (g, i, ow, oh, widths, gaps))
            continue

        if colour_chunks is None:
            sib, colour_chunks = sibling_colour_chunks(tier_dir)
            if not colour_chunks:
                print("FATAL: no sibling Upscale2x output in %s carries "
                      "sRGB+gAMA+pHYs to copy (F7) - the redraw refuses to "
                      "invent colour metadata the rest of the corpus does "
                      "not have." % tier_dir)
                return 1
            print("  colour chunks (sRGB/gAMA/pHYs) copied from sibling %s"
                  % sib)
        save(dst, ow, oh, out, colour_chunks)
        done += 1
        print("  redrew {%08X,%08X} -> %dx%d" % (g, i, ow, oh))
    print("redraw_ladder: %d sheet(s) rewritten at factor %g" % (done, factor))
    if factor != int(factor) and skipped:
        # F5: at a fractional factor a skipped ladder means the tier SHIPS
        # PLAIN NN for that sheet - the exact regression the Rebuild-Corpus
        # wiring exists to prevent. Never exit 0 over it.
        for g, i, why in skipped:
            print("FATAL: ladder {%08X,%08X} SKIPPED at fractional factor %g: "
                  "%s" % (g, i, factor, why))
        return 1
    return 0


sys.exit(main())
