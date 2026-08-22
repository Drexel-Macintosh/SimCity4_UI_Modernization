#!/usr/bin/env python3
r"""PASS 2 of the blue-disc hunt: decode every texture the marker family binds,
crop each model's own sprite out of its atlas by UV, and FILTER BY PIXELS.

Filter (deliberately colour-first, NOT name-first):
    BLUE   hue 190..250 deg, sat >= 0.30, val >= 0.12
    WHITE  sat <= 0.25, val >= 0.70
    survivor: blue_frac >= 0.15 AND white_frac >= 0.02 AND >= 40 visible px

Every sprite's metrics are written to family-pixels.tsv whether it survives or
not, so the filter's behaviour is inspectable and a "0 survivors" or "everything
survives" result is visible as such rather than being reported as a finding.

POSITIVE CONTROLS for the filter itself:
  - Zot_NoCar 0x107A0000 is a GREEN car in a RED ring: it MUST score high red /
    low blue.  If it scores blue, the hue code is wrong.
  - The filter is also run in a 'blue-only' and 'white-only' variant so we can
    see whether each half of the AND is doing any work.

    python render_family.py
"""
import csv
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", ".."))
from PIL import Image                                            # noqa: E402
from census_markers import read_entry, maybe_decompress          # noqa: E402
from index_all import index, T_FSH                               # noqa: E402

TSV_IN = os.path.join(HERE, "family-resolved.tsv")
TSV_OUT = os.path.join(HERE, "family-pixels.tsv")
SPRITE_DIR = os.path.join(HERE, "family-sprites")

BLUE_HUE = (190.0, 250.0)
BLUE_SAT = 0.30
BLUE_VAL = 0.12
WHITE_SAT = 0.25
WHITE_VAL = 0.70
MIN_VIS = 40
KEEP_BLUE = 0.15
KEEP_WHITE = 0.02


# ------------------------------------------------------------------ FSH decode
def decode_fsh(payload):
    """-> list of PIL RGBA images (the image entries only, largest first)."""
    if payload[:4] != b"SHPI":
        return []
    nent = struct.unpack_from("<I", payload, 8)[0]
    if nent > 256:
        return []
    entries = []
    for e in range(nent):
        try:
            off = struct.unpack_from("<I", payload, 20 + 8 * e)[0]
        except Exception:
            break
        if off + 16 > len(payload):
            continue
        entries.append(off)

    # palettes first (an indexed entry borrows the file's palette entry)
    pal = None
    for off in entries:
        code = payload[off] & 0x7F
        if code not in (0x22, 0x24, 0x29, 0x2A, 0x2D):
            continue
        n = struct.unpack_from("<H", payload, off + 4)[0]
        p = off + 16
        cols = []
        try:
            if code == 0x2A:                       # 32-bit BGRA
                for k in range(n):
                    b, g, r, _a = payload[p + k * 4: p + k * 4 + 4]
                    cols.append((r, g, b))
            elif code in (0x24,):                  # 24-bit BGR
                for k in range(n):
                    b, g, r = payload[p + k * 3: p + k * 3 + 3]
                    cols.append((r, g, b))
            elif code == 0x22:                     # 6-bit DOS BGR
                for k in range(n):
                    b, g, r = payload[p + k * 3: p + k * 3 + 3]
                    cols.append((r * 4, g * 4, b * 4))
            else:                                  # 16-bit
                for k in range(n):
                    v = struct.unpack_from("<H", payload, p + k * 2)[0]
                    cols.append((((v >> 10) & 31) * 8, ((v >> 5) & 31) * 8,
                                 (v & 31) * 8))
        except Exception:
            cols = []
        if cols:
            pal = cols
            break

    out = []
    for off in entries:
        code = payload[off] & 0x7F
        w, h = struct.unpack_from("<2H", payload, off + 4)
        if w == 0 or h == 0 or w > 4096 or h > 4096:
            continue
        p = off + 16
        img = None
        try:
            if code == 0x7D:
                img = Image.frombytes("RGBA", (w, h),
                                      payload[p:p + w * h * 4], "raw", "BGRA")
            elif code == 0x7F:
                img = Image.frombytes("RGB", (w, h),
                                      payload[p:p + w * h * 3], "raw", "BGR")
            elif code == 0x78:
                img = Image.frombytes("RGB", (w, h),
                                      payload[p:p + w * h * 2], "raw", "BGR;16")
            elif code == 0x60:
                need = max(1, w // 4) * max(1, h // 4) * 8
                img = Image.frombytes("RGBA", (w, h), payload[p:p + need], "bcn", 1)
            elif code == 0x61:
                need = max(1, w // 4) * max(1, h // 4) * 16
                img = Image.frombytes("RGBA", (w, h), payload[p:p + need], "bcn", 2)
            elif code == 0x7B and pal:
                pix = payload[p:p + w * h]
                if len(pix) < w * h:
                    continue
                im = Image.frombytes("P", (w, h), pix)
                flat = []
                for c in pal[:256]:
                    flat.extend(c)
                flat.extend([0] * (768 - len(flat)))
                im.putpalette(flat)
                img = im.convert("RGBA")
        except Exception:
            img = None
        if img is not None:
            out.append(img.convert("RGBA"))
    out.sort(key=lambda im: -(im.width * im.height))
    return out


_atlas_cache = {}


def atlas(tex, by_ti):
    if tex in _atlas_cache:
        return _atlas_cache[tex]
    hits = by_ti.get((T_FSH, tex))
    im = None
    if hits:
        _g, path, off, sz = hits[0]
        payload, _c = maybe_decompress(read_entry(path, off, sz))
        imgs = decode_fsh(payload)
        im = imgs[0] if imgs else None
    if len(_atlas_cache) > 40:
        _atlas_cache.clear()
    _atlas_cache[tex] = im
    return im


# ------------------------------------------------------------------ scoring
def score(sprite):
    """-> dict of pixel fractions over the VISIBLE (alpha>100, non-black) pixels."""
    rgb = sprite.convert("RGB")
    a = sprite.split()[3]
    hsv = rgb.convert("HSV")
    H, S, V = [list(ch.getdata()) for ch in hsv.split()]
    A = list(a.getdata())
    vis = blue = white = red = 0
    for k in range(len(A)):
        if A[k] <= 100:
            continue
        v = V[k] / 255.0
        if v < 0.05:                     # atlas padding reads as pure black
            continue
        vis += 1
        s = S[k] / 255.0
        hd = H[k] * 360.0 / 255.0
        if BLUE_HUE[0] <= hd <= BLUE_HUE[1] and s >= BLUE_SAT and v >= BLUE_VAL:
            blue += 1
        if s <= WHITE_SAT and v >= WHITE_VAL:
            white += 1
        if (hd <= 20 or hd >= 340) and s >= 0.45 and v >= 0.20:
            red += 1
    if vis == 0:
        return dict(vis=0, blue=0.0, white=0.0, red=0.0)
    return dict(vis=vis, blue=blue / vis, white=white / vis, red=red / vis)


def crop_sprite(im, r):
    W, H = im.size
    for k in ("umin", "umax", "vmin", "vmax"):
        if k not in r:
            raise KeyError(
                "row has no %r column -- crop_sprite would silently return the "
                "WHOLE ATLAS.  Read family-resolved.tsv or the UV-carrying "
                "family-pixels.tsv, not a schema without UVs." % k)
    try:
        umin, umax = float(r["umin"]), float(r["umax"])
        vmin, vmax = float(r["vmin"]), float(r["vmax"])
    except Exception:
        return im.copy(), (0, 0, W, H), False
    if not (0.0 <= umin <= 1.0 and 0.0 <= umax <= 1.0
            and 0.0 <= vmin <= 1.0 and 0.0 <= vmax <= 1.0):
        return im.copy(), (0, 0, W, H), False
    l, rr = int(round(umin * W)), int(round(umax * W))
    t, b = int(round(vmin * H)), int(round(vmax * H))
    l, rr = max(0, min(l, W - 1)), min(W, max(rr, l + 1))
    t, b = max(0, min(t, H - 1)), min(H, max(b, t + 1))
    if (rr - l) < 4 or (b - t) < 4:
        return im.copy(), (0, 0, W, H), False
    return im.crop((l, t, rr, b)), (l, t, rr, b), True


def main():
    g = index()
    by_ti = g["by_ti"]
    rows = list(csv.DictReader(open(TSV_IN, encoding="utf-8"), delimiter="\t"))
    rows.sort(key=lambda r: r["tex"])          # decode each atlas once
    os.makedirs(SPRITE_DIR, exist_ok=True)

    out = []
    n_noatlas = 0
    for k, r in enumerate(rows):
        if k % 200 == 0:
            print("  ...%d/%d" % (k, len(rows)))
        tex = int(r["tex"], 16)
        im = atlas(tex, by_ti)
        if im is None:
            n_noatlas += 1
            continue
        sp, rect, cropped = crop_sprite(im, r)
        if sp.width * sp.height > 512 * 512:
            sp = sp.resize((256, 256), Image.LANCZOS)
        m = score(sp)
        rec = dict(r)
        rec.update(m)
        rec["cropped"] = "1" if cropped else "0"
        rec["w"], rec["h"] = sp.size
        rec["atlas_w"], rec["atlas_h"] = im.size
        rec["_img"] = sp
        out.append(rec)

    with open(TSV_OUT, "w", encoding="utf-8", newline="") as fh:
        # ⛔ THE UV COLUMNS MUST BE CARRIED THROUGH.  They were omitted at first,
        # and because crop_sprite() treats a missing/unparseable UV rect as
        # "use the whole atlas", every downstream consumer of this file
        # (contact_sheet.py, widen_roundel.py) silently scored and displayed
        # 256x256 ATLASES instead of individual sprites.  The shape detector's
        # Zot control caught it; nothing else would have.
        fh.write("ex_inst\tname\tmodel\ttex\tmethod\tcropped\tw\th\tatlas\tvis"
                 "\tblue\twhite\tred\tumin\tumax\tvmin\tvmax\tarchive\n")
        for r in out:
            fh.write("%s\t%s\t%s\t%s\t%s\t%s\t%d\t%d\t%dx%d\t%d\t%.4f\t%.4f\t%.4f"
                     "\t%s\t%s\t%s\t%s\t%s\n"
                     % (r["ex_inst"], r["name"], r["model"], r["tex"], r["method"],
                        r["cropped"], r["w"], r["h"], r["atlas_w"], r["atlas_h"],
                        r["vis"], r["blue"], r["white"], r["red"],
                        r["umin"], r["umax"], r["vmin"], r["vmax"], r["archive"]))

    # ---------------- filter behaviour, stated as counts ----------------
    n = len(out)
    big = [r for r in out if r["vis"] >= MIN_VIS]
    blue_only = [r for r in big if r["blue"] >= KEEP_BLUE]
    white_only = [r for r in big if r["white"] >= KEEP_WHITE]
    keep = [r for r in big if r["blue"] >= KEEP_BLUE and r["white"] >= KEEP_WHITE]
    print()
    print("sprites scored          : %d  (atlas decode failed on %d rows)" % (n, n_noatlas))
    print("  >= %d visible px      : %d" % (MIN_VIS, len(big)))
    print("  blue  >= %.2f alone   : %d" % (KEEP_BLUE, len(blue_only)))
    print("  white >= %.2f alone   : %d" % (KEEP_WHITE, len(white_only)))
    print("  BOTH (survivors)      : %d" % len(keep))
    ctl = [r for r in out if r["ex_inst"] == "107A0000"]
    if ctl:
        c = ctl[0]
        print("FILTER CONTROL Zot_NoCar (green car, RED ring): "
              "blue=%.3f white=%.3f red=%.3f  -> %s"
              % (c["blue"], c["white"], c["red"],
                 "correctly NOT blue" if c["blue"] < KEEP_BLUE
                 else "*** scored BLUE -> hue code is wrong ***"))
    keep.sort(key=lambda r: -(r["blue"] * 2 + r["white"]))
    for r in keep:
        fn = "cand-%s-%s-%s.png" % (r["ex_inst"], r["model"], r["tex"])
        bg = Image.new("RGBA", r["_img"].size, (26, 26, 32, 255))
        bg.alpha_composite(r["_img"])
        bg.save(os.path.join(SPRITE_DIR, fn))
    print("wrote %d candidate PNGs to %s" % (len(keep), SPRITE_DIR))
    return keep


if __name__ == "__main__":
    main()
