"""Adversarial verification probe for LANE 1 dock-recess patch spec.
Throwaway. Reads only; writes nothing outside tools\\.
"""
import os
import struct
import sys
import zlib

TOOLS = r"<HOME>\OneDrive\Projects\Surface 1 Project\1 Completed Projects\SC4TouchControls\tools"
SIG = bytes([137, 80, 78, 71, 13, 10, 26, 10])


def chunks(blob):
    if blob[:8] != SIG:
        raise ValueError("not a PNG")
    out, off = [], 8
    while off < len(blob):
        (ln,) = struct.unpack(">I", blob[off:off + 4])
        out.append((blob[off + 4:off + 8], blob[off + 8:off + 8 + ln]))
        off += 12 + ln
    return out


def paeth(a, b, c):
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    return b if pb <= pc else c


def read_rgba(path):
    with open(path, "rb") as f:
        blob = f.read()
    ch = chunks(blob)
    ihdr = next(d for (t, d) in ch if t == b"IHDR")
    w, h, depth, ctype, comp, filt, ilace = struct.unpack(">IIBBBBB", ihdr)
    types = [t.decode("ascii", "replace") for (t, _) in ch]
    if (depth, ctype, comp, filt, ilace) != (8, 6, 0, 0, 0):
        return dict(w=w, h=h, hdr=(depth, ctype, comp, filt, ilace),
                    types=types, px=None)
    raw = zlib.decompress(b"".join(d for (t, d) in ch if t == b"IDAT"))
    stride, bpp = w * 4, 4
    px, pos = bytearray(stride * h), 0
    for y in range(h):
        ft = raw[pos]
        pos += 1
        line = bytearray(raw[pos:pos + stride])
        pos += stride
        ro, po = y * stride, y * stride - stride
        if ft == 1:
            for i in range(bpp, stride):
                line[i] = (line[i] + line[i - bpp]) & 0xFF
        elif ft == 2:
            for i in range(stride):
                line[i] = (line[i] + px[po + i]) & 0xFF
        elif ft == 3:
            for i in range(stride):
                a = line[i - bpp] if i >= bpp else 0
                line[i] = (line[i] + ((a + px[po + i]) >> 1)) & 0xFF
        elif ft == 4:
            for i in range(stride):
                a = line[i - bpp] if i >= bpp else 0
                c = px[po + i - bpp] if i >= bpp else 0
                line[i] = (line[i] + paeth(a, px[po + i], c)) & 0xFF
        elif ft != 0:
            raise ValueError("bad filter %d" % ft)
        px[ro:ro + stride] = line
    return dict(w=w, h=h, hdr=(depth, ctype, comp, filt, ilace),
                types=types, px=px)


def sat(px, stride, x, y):
    o = y * stride + x * 4
    r, g, b = px[o], px[o + 1], px[o + 2]
    if (r, g, b) == (255, 0, 255):
        return 0
    return max(r, g, b) - min(r, g, b)


def satbbox(d, thr=60):
    w, h, px = d["w"], d["h"], d["px"]
    stride = w * 4
    xs, ys, n = [], [], 0
    for y in range(h):
        for x in range(w):
            if sat(px, stride, x, y) > thr:
                xs.append(x)
                ys.append(y)
                n += 1
    if not xs:
        return None, 0
    return (min(xs), min(ys), max(xs), max(ys)), n


def report(tag, path):
    print("=" * 70)
    print(tag)
    print("  path:", path)
    if not os.path.isfile(path):
        print("  MISSING")
        return None
    print("  size on disk:", os.path.getsize(path))
    d = read_rgba(path)
    print("  IHDR w,h =", d["w"], d["h"], " (depth,ctype,comp,filt,ilace) =", d["hdr"])
    print("  chunks:", d["types"])
    if d["px"] is None:
        print("  *** NOT 8-bit RGBA non-interlaced -> patch's _png_read_rgba WOULD RAISE ***")
        return d
    bb, n = satbbox(d)
    print("  saturation bbox (thr>60):", bb, " count:", n)
    if bb:
        l, t, r, b = bb
        print("  -> block %dx%d at (%d,%d)" % (r - l + 1, b - t + 1, l, t))
    return d


one = report("1x EXTRACT {46a006b0,13d14ca0}",
             os.path.join(TOOLS, "dbpf", "extracted", "SimCity_1",
                          "T-856ddbac_G-46a006b0_I-13d14ca0.png"))
alt = report("1x EXTRACT {1abe787d,13d14ca0} (same IID, other group)",
             os.path.join(TOOLS, "dbpf", "extracted", "SimCity_1",
                          "T-856ddbac_G-1abe787d_I-13d14ca0.png"))
st3 = report("STAGED 3x {46a006b0,13d14ca0}",
             os.path.join(TOOLS, "selective-safe", "stage-3x",
                          "T-0x856ddbac_G-0x46a006b0_I-0x13d14ca0.png"))
up3 = report("UPSCALE preview-3x {46a006b0,13d14ca0}",
             os.path.join(TOOLS, "upscale", "preview-3x", "SimCity_1",
                          "T-0x856ddbac_G-0x46a006b0_I-0x13d14ca0.png"))
st2 = report("STAGED 2x {46a006b0,13d14ca0}",
             os.path.join(TOOLS, "selective-safe", "stage",
                          "T-0x856ddbac_G-0x46a006b0_I-0x13d14ca0.png"))
