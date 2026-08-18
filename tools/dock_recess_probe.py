#!/usr/bin/env python3
r"""dock_recess_probe.py - THROWAWAY probe for the dock-sheet minimap recess.

Measures the baked FAKE MAP block in {46a006b0,13d14ca0} and prototypes the
stdlib (zlib+struct) neutralize fill, so the builder patch can be written
against MEASURED numbers instead of asserted ones.

Read-only except for writing prototype PNGs into the scratchpad.
"""
import os
import struct
import sys
import zlib

TOOLS = r"<PROJECT-ROOT> 1 Project\1 Completed Projects\SC4TouchControls\tools"
SRC_1X = os.path.join(TOOLS, "dbpf", "extracted", "SimCity_1",
                      "T-856ddbac_G-46a006b0_I-13d14ca0.png")
UP_3X = os.path.join(TOOLS, "upscale", "preview-3x", "SimCity_1",
                     "T-0x856ddbac_G-0x46a006b0_I-0x13d14ca0.png")
UP_2X = os.path.join(TOOLS, "upscale", "preview", "SimCity_1",
                     "T-0x856ddbac_G-0x46a006b0_I-0x13d14ca0.png")
UP_15X = os.path.join(TOOLS, "upscale", "preview-15x", "SimCity_1",
                      "T-0x856ddbac_G-0x46a006b0_I-0x13d14ca0.png")
SCRATCH = (r"<PROJECT-ROOT>"
           r"\<SESSION-DIR>"
           r"\f1160943-a698-434b-a6bf-d3c3e2971cea\scratchpad")

PNG_SIG = b"\x89PNG\r\n\x1a\n"


# --------------------------------------------------------------------------
# Minimal stdlib PNG read/modify/write, RGBA8 only. This is the EXACT code
# shape proposed for the builder patch, so testing it here tests the patch.
# --------------------------------------------------------------------------
def _png_chunks(blob):
    assert blob[:8] == PNG_SIG, "not a PNG"
    out, off = [], 8
    while off < len(blob):
        (ln,) = struct.unpack(">I", blob[off:off + 4])
        typ = blob[off + 4:off + 8]
        data = blob[off + 8:off + 8 + ln]
        out.append((typ, data))
        off += 12 + ln
    return out


def _paeth(a, b, c):
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    if pb <= pc:
        return b
    return c


def _unfilter(raw, w, h, bpp):
    stride = w * bpp
    out = bytearray(stride * h)
    pos = 0
    for y in range(h):
        ft = raw[pos]
        pos += 1
        line = bytearray(raw[pos:pos + stride])
        pos += stride
        ro = y * stride
        po = ro - stride
        if ft == 0:
            pass
        elif ft == 1:
            for i in range(bpp, stride):
                line[i] = (line[i] + line[i - bpp]) & 0xFF
        elif ft == 2:
            for i in range(stride):
                line[i] = (line[i] + out[po + i]) & 0xFF
        elif ft == 3:
            for i in range(stride):
                a = line[i - bpp] if i >= bpp else 0
                line[i] = (line[i] + ((a + out[po + i]) >> 1)) & 0xFF
        elif ft == 4:
            for i in range(stride):
                a = line[i - bpp] if i >= bpp else 0
                c = out[po + i - bpp] if i >= bpp else 0
                line[i] = (line[i] + _paeth(a, out[po + i], c)) & 0xFF
        else:
            raise ValueError("bad filter %d on row %d" % (ft, y))
        out[ro:ro + stride] = line
    return out, stride


def png_load_rgba(path):
    blob = open(path, "rb").read()
    chunks = _png_chunks(blob)
    ihdr = dict(chunks)[b"IHDR"]
    w, h, depth, ctype, comp, filt, ilace = struct.unpack(">IIBBBBB", ihdr)
    assert (depth, ctype, comp, filt, ilace) == (8, 6, 0, 0, 0), \
        "probe supports 8-bit RGBA non-interlaced only, got %r" % (
            (depth, ctype, comp, filt, ilace),)
    idat = b"".join(d for (t, d) in chunks if t == b"IDAT")
    px, stride = _unfilter(zlib.decompress(idat), w, h, 4)
    return w, h, px, stride, chunks


def png_save_rgba(path, w, h, px, chunks):
    """Rewrite, preserving EVERY ancillary chunk (gAMA/sRGB/pHYs/tRNS...)."""
    stride = w * 4
    raw = bytearray()
    for y in range(h):
        raw.append(0)                      # filter type 0 (None)
        raw += px[y * stride:(y + 1) * stride]
    new_idat = zlib.compress(bytes(raw), 9)
    out = bytearray(PNG_SIG)
    wrote_idat = False
    for (typ, data) in chunks:
        if typ == b"IDAT":
            if wrote_idat:
                continue
            typ, data, wrote_idat = b"IDAT", new_idat, True
        out += struct.pack(">I", len(data)) + typ + data
        out += struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF)
    open(path, "wb").write(bytes(out))


# --------------------------------------------------------------------------
def measure(path, label):
    w, h, px, stride, _ = png_load_rgba(path)

    def rgb(x, y):
        o = y * stride + x * 4
        return px[o], px[o + 1], px[o + 2], px[o + 3]

    def colourful(x, y):
        r, g, b, a = rgb(x, y)
        if (r, g, b) == (255, 0, 255):
            return False
        return max(r, g, b) - min(r, g, b) > 60

    xs = [x for x in range(w) if any(colourful(x, y) for y in range(h))]
    ys = [y for y in range(h) if any(colourful(x, y) for x in range(w))]
    print("[%s] %dx%d  colourful bbox x[%d,%d] y[%d,%d] = %dx%d"
          % (label, w, h, xs[0], xs[-1], ys[0], ys[-1],
             xs[-1] - xs[0] + 1, ys[-1] - ys[0] + 1))
    # contiguity: every column/row in the bbox must be present
    print("    contiguous cols: %s   contiguous rows: %s"
          % (xs == list(range(xs[0], xs[-1] + 1)),
             ys == list(range(ys[0], ys[-1] + 1))))
    return w, h, px, stride, xs[0], ys[0], xs[-1] - xs[0] + 1, ys[-1] - ys[0] + 1


def neutralize(px, stride, w, h, left, top, bw, bh, flank):
    """The proposed fill: per-row median of the flanking plate pixels."""
    changed = 0
    fills = []
    for y in range(top, top + bh):
        samples = []
        for dx in range(1, flank + 1):
            for x in (left - dx, left + bw - 1 + dx):
                if 0 <= x < w:
                    o = y * stride + x * 4
                    samples.append((px[o], px[o + 1], px[o + 2], px[o + 3]))
        assert samples, "no flank samples on row %d" % y
        med = tuple(sorted(s[c] for s in samples)[len(samples) // 2]
                    for c in range(4))
        fills.append(med)
        row = bytes(med) * bw
        o = y * stride + left * 4
        if px[o:o + bw * 4] != row:
            changed += 1
        px[o:o + bw * 4] = row
    return changed, fills


def main():
    print("=== 1x SOURCE ===")
    measure(SRC_1X, "1x")
    print("\n=== 2x / 1.5x / 3x UPSCALES ===")
    for p, lbl in ((UP_15X, "1.5x"), (UP_2X, "2x"), (UP_3X, "3x")):
        measure(p, lbl)

    print("\n=== CHUNK INVENTORY (3x) ===")
    _, _, _, _, chunks = png_load_rgba(UP_3X)
    seen = []
    for (t, d) in chunks:
        tag = t.decode("ascii", "replace")
        if tag == "IDAT":
            if "IDAT" in seen:
                continue
            seen.append("IDAT")
            print("    IDAT (x%d, %d bytes total)"
                  % (sum(1 for (tt, _dd) in chunks if tt == b"IDAT"),
                     sum(len(dd) for (tt, dd) in chunks if tt == b"IDAT")))
            continue
        seen.append(tag)
        print("    %s (%d bytes)" % (tag, len(d)))

    print("\n=== ROUNDTRIP CONTROL (positive control for the writer) ===")
    w, h, px, stride, chunks = png_load_rgba(UP_3X)
    rt = os.path.join(SCRATCH, "rt_3x.png")
    png_save_rgba(rt, w, h, bytearray(px), chunks)
    w2, h2, px2, _, ch2 = png_load_rgba(rt)
    print("    pixels identical after read->write->read: %s"
          % (bytes(px) == bytes(px2) and (w, h) == (w2, h2)))
    print("    ancillary chunk types preserved: %s"
          % ([t.decode() for (t, _d) in chunks if t != b"IDAT"]
             == [t.decode() for (t, _d) in ch2 if t != b"IDAT"]))

    print("\n=== FILL PROTOTYPE @3x ===")
    w, h, px, stride, L, T, BW, BH = measure(UP_3X, "3x-again")
    px = bytearray(px)
    changed, fills = neutralize(px, stride, w, h, L, T, BW, BH, flank=9)
    print("    rect (%d,%d) %dx%d   rows changed: %d/%d" % (L, T, BW, BH, changed, BH))
    print("    fill top    row %d = #%02x%02x%02x a=%d" % ((T,) + fills[0]))
    print("    fill middle row %d = #%02x%02x%02x a=%d"
          % ((T + BH // 2,) + fills[BH // 2]))
    print("    fill bottom row %d = #%02x%02x%02x a=%d" % ((T + BH - 1,) + fills[-1]))
    outp = os.path.join(SCRATCH, "dock3x_neutralized.png")
    png_save_rgba(outp, w, h, px, chunks)
    print("    wrote %s (%d bytes)" % (outp, os.path.getsize(outp)))

    # re-measure the neutralized image: the colourful block must be GONE
    print("\n=== POSITIVE CONTROL: same detector on the FIXED file ===")
    w3, h3, px3, st3, ch3 = png_load_rgba(outp)

    def colourful(x, y):
        o = y * st3 + x * 4
        r, g, b = px3[o], px3[o + 1], px3[o + 2]
        if (r, g, b) == (255, 0, 255):
            return False
        return max(r, g, b) - min(r, g, b) > 60

    n = sum(1 for y in range(T, T + BH) for x in range(L, L + BW)
            if colourful(x, y))
    print("    colourful px inside the recess rect AFTER fill: %d (expect 0)" % n)
    n_out = sum(1 for y in range(h3) for x in range(w3)
                if colourful(x, y) and not (L <= x < L + BW and T <= y < T + BH))
    print("    colourful px anywhere ELSE on the sheet: %d" % n_out)
    # prove the detector still works: it found >0 before
    print("    (the SAME detector found a full 192x192 block before the fill,"
          " so a 0 here is a measured null, not a blind one)")

    # blast radius: how many bytes differ from the staged original?
    a = png_load_rgba(UP_3X)[2]
    diff = sum(1 for i in range(0, len(a), 4)
               if a[i:i + 4] != px3[i:i + 4])
    print("\n=== BLAST RADIUS ===")
    print("    pixels differing from the staged 3x sheet: %d (block is %d)"
          % (diff, BW * BH))
    # every differing pixel must be inside the rect
    bad = 0
    for i in range(0, len(a), 4):
        if a[i:i + 4] != px3[i:i + 4]:
            p = i // 4
            x, y = p % w3, p // w3
            if not (L <= x < L + BW and T <= y < T + BH):
                bad += 1
    print("    differing pixels OUTSIDE the rect: %d (expect 0)" % bad)


if __name__ == "__main__":
    sys.exit(main())
