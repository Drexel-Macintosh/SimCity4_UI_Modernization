"""Adversarial probe #2: pixel-diff staged vs upscale source; simulate the
proposed neutralize_dock_recess() on a scratch copy at f=3 and f=2.
Throwaway. Writes only under the scratchpad.
"""
import math
import os
import shutil
import struct
import sys
import zlib

TOOLS = r"<PROJECT-ROOT> 1 Project\1 Completed Projects\SC4TouchControls\tools"
SCRATCH = r"<PROJECT-ROOT>"
SIG = bytes([137, 80, 78, 71, 13, 10, 26, 10])


def chunks(blob):
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
    return w, h, px, ch


def write_rgba(path, w, h, px, ch):
    stride = w * 4
    raw = bytearray()
    for y in range(h):
        raw.append(0)
        raw += px[y * stride:(y + 1) * stride]
    new_idat, wrote = zlib.compress(bytes(raw), 9), False
    out = bytearray(SIG)
    for (typ, data) in ch:
        if typ == b"IDAT":
            if wrote:
                continue
            data, wrote = new_idat, True
        out += struct.pack(">I", len(data)) + typ + data
        out += struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF)
    with open(path, "wb") as f:
        f.write(bytes(out))


ST3 = os.path.join(TOOLS, "selective-safe", "stage-3x",
                   "T-0x856ddbac_G-0x46a006b0_I-0x13d14ca0.png")
UP3 = os.path.join(TOOLS, "upscale", "preview-3x", "SimCity_1",
                   "T-0x856ddbac_G-0x46a006b0_I-0x13d14ca0.png")
EX1 = os.path.join(TOOLS, "dbpf", "extracted", "SimCity_1",
                   "T-856ddbac_G-46a006b0_I-13d14ca0.png")

print("### A. staged-3x vs upscale-preview-3x pixel diff")
w1, h1, p1, _ = read_rgba(ST3)
w2, h2, p2, _ = read_rgba(UP3)
print("  dims", (w1, h1), (w2, h2))
diff = sum(1 for i in range(len(p1)) if p1[i] != p2[i])
print("  differing BYTES: %d of %d  -> pixels identical: %s"
      % (diff, len(p1), diff == 0))

print("\n### B. is the 3x an exact 3x3 block replicate of the 1x extract?")
w0, h0, p0, _ = read_rgba(EX1)
bad = 0
for y in range(h1):
    for x in range(w1):
        so = (y // 3) * (w0 * 4) + (x // 3) * 4
        do = y * (w1 * 4) + x * 4
        if p1[do:do + 4] != p0[so:so + 4]:
            bad += 1
print("  1x %dx%d -> 3x %dx%d ; mismatching pixels: %d" % (w0, h0, w1, h1, bad))

print("\n### C. plate gradient check: is there a HORIZONTAL component?")
# left flank cols 45..53, right flank cols 246..254, rows 213..404 at 3x
stride = w1 * 4
worst = 0
for y in range(213, 405):
    lo = [p1[y * stride + x * 4:y * stride + x * 4 + 4] for x in range(45, 54)]
    ro = [p1[y * stride + x * 4:y * stride + x * 4 + 4] for x in range(246, 255)]
    for c in range(4):
        lm = sorted(v[c] for v in lo)[len(lo) // 2]
        rm = sorted(v[c] for v in ro)[len(ro) // 2]
        worst = max(worst, abs(lm - rm))
print("  worst |left-median - right-median| across 192 rows, all 4 channels:", worst)
top = p1[213 * stride + 45 * 4:213 * stride + 45 * 4 + 4]
bot = p1[404 * stride + 45 * 4:404 * stride + 45 * 4 + 4]
print("  plate top px  RGBA:", tuple(top))
print("  plate bot px  RGBA:", tuple(bot))

print("\n### D. simulate the PROPOSED fill (f=3) on a scratch copy")
os.makedirs(SCRATCH, exist_ok=True)
scr = os.path.join(SCRATCH, "dock3x_scratch.png")
shutil.copy2(ST3, scr)


def scale_len(v, F):
    return int(math.floor(v * F + 0.5))


def sat(px, stride, x, y):
    o = y * stride + x * 4
    r, g, b = px[o], px[o + 1], px[o + 2]
    if (r, g, b) == (255, 0, 255):
        return 0
    return max(r, g, b) - min(r, g, b)


for F in (1.0, 1.5, 2.0, 2.5, 3.0, 4.0):
    l, t = scale_len(18, F), scale_len(71, F)
    bw, bh = scale_len(64, F), scale_len(64, F)
    fl = max(1, scale_len(3, F))
    print("  f=%-4s rect=(%d,%d) %dx%d flank=%d   gate f<2.5 -> %s"
          % (F, l, t, bw, bh, fl, "SKIP" if F < 2.5 else "RUN"))

F = 3.0
w, h, px, ch = read_rgba(scr)
stride = w * 4
left, top_, bw, bh = scale_len(18, F), scale_len(71, F), scale_len(64, F), scale_len(64, F)
flank = max(1, scale_len(3, F))
probe = [(x, y) for y in range(top_, top_ + bh, 4) for x in range(left, left + bw, 4)]
n_sat = sum(1 for (x, y) in probe if sat(px, stride, x, y) > 60)
print("  pre-fill probe: %d/%d saturated (%.1f%%), threshold 60%%  -> %s"
      % (n_sat, len(probe), 100.0 * n_sat / len(probe),
         "PASS" if n_sat >= len(probe) * 0.6 else "ABORT"))
fills = []
seam = 0
for y in range(top_, top_ + bh):
    s = []
    for dx in range(1, flank + 1):
        for x in (left - dx, left + bw - 1 + dx):
            o = y * stride + x * 4
            s.append((px[o], px[o + 1], px[o + 2], px[o + 3]))
    med = bytes(sorted(v[c] for v in s)[len(s) // 2] for c in range(4))
    fills.append(med)
    # seam: compare med to the immediate neighbour pixel on both sides
    for x in (left - 1, left + bw):
        o = y * stride + x * 4
        for c in range(4):
            seam = max(seam, abs(med[c] - px[o + c]))
    o = y * stride + left * 4
    px[o:o + bw * 4] = med * bw
print("  worst seam delta vs immediate neighbour: %d/255" % seam)
print("  fill top RGBA %s  bottom RGBA %s" % (tuple(fills[0]), tuple(fills[-1])))
write_rgba(scr, w, h, px, ch)
print("  rewritten size: %d bytes (was %d)" % (os.path.getsize(scr), os.path.getsize(ST3)))
w2_, h2_, px2, ch2 = read_rgba(scr)
rem = sum(1 for y in range(top_, top_ + bh) for x in range(left, left + bw)
          if sat(px2, w2_ * 4, x, y) > 60)
print("  post-fill saturated px inside rect: %d  (positive control: was %d sampled)" % (rem, n_sat))
print("  chunks preserved:", [t.decode() for (t, _) in ch2])
# whole-sheet saturation after fill (are there OTHER saturated regions?)
allsat = sum(1 for y in range(h2_) for x in range(w2_) if sat(px2, w2_ * 4, x, y) > 60)
print("  saturated px anywhere on sheet AFTER fill:", allsat)
