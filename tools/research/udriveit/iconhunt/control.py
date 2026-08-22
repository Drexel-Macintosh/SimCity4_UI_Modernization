#!/usr/bin/env python3
r"""POSITIVE CONTROL for the iconhunt scorer.

A filter that finds nothing is worthless unless it can be shown to find the
thing when the thing is there.  This plants synthetic targets that match the
user's screenshot description and asserts the scorer ranks them high, plus
NEGATIVE controls (plain square, ring outline, blue sky, noise) that must NOT
score.  Run before believing any "no candidates" result.
"""
import numpy as np
from PIL import Image, ImageDraw

from shape import analyse


def navy_disc_with_car(size=38, navy=(22, 33, 90), rim=(60, 90, 170), pad=6,
                       glyph="car", alpha_bg=0):
    n = size + pad * 2
    im = Image.new("RGBA", (n, n), (0, 0, 0, alpha_bg))
    d = ImageDraw.Draw(im)
    d.ellipse([pad, pad, pad + size - 1, pad + size - 1], fill=rim + (255,))
    d.ellipse([pad + 2, pad + 2, pad + size - 3, pad + size - 3],
              fill=navy + (255,))
    cx = cy = pad + size // 2
    k = size / 38.0                             # glyph scales WITH the disc

    def s(v):
        return int(round(v * k))
    if glyph == "car":
        d.rounded_rectangle([cx - s(11), cy - s(2), cx + s(11), cy + s(5)],
                            max(1, s(2)), fill=(255, 255, 255, 255))
        d.polygon([(cx - s(7), cy - s(2)), (cx - s(4), cy - s(8)),
                   (cx + s(4), cy - s(8)), (cx + s(7), cy - s(2))],
                  fill=(255, 255, 255, 255))
        d.ellipse([cx - s(9), cy + s(3), cx - s(4), cy + s(8)],
                  fill=(255, 255, 255, 255))
        d.ellipse([cx + s(4), cy + s(3), cx + s(9), cy + s(8)],
                  fill=(255, 255, 255, 255))
    else:                                       # helicopter
        d.rectangle([cx - s(12), cy - s(7), cx + s(12), cy - s(5)],
                    fill=(255, 255, 255, 255))
        d.ellipse([cx - s(7), cy - s(3), cx + s(5), cy + s(6)],
                  fill=(255, 255, 255, 255))
        d.polygon([(cx + s(4), cy), (cx + s(12), cy + s(2)),
                   (cx + s(12), cy + s(4)), (cx + s(4), cy + s(4))],
                  fill=(255, 255, 255, 255))
    return np.asarray(im)


def white_roundel_hole(size=38, pad=6):
    n = size + pad * 2
    im = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse([pad, pad, pad + size - 1, pad + size - 1],
              fill=(255, 255, 255, 255))
    cx = cy = pad + size // 2
    d.rounded_rectangle([cx - 10, cy - 2, cx + 10, cy + 5], 2,
                        fill=(0, 0, 0, 0))
    d.polygon([(cx - 7, cy - 2), (cx - 4, cy - 8), (cx + 4, cy - 8),
               (cx + 7, cy - 2)], fill=(0, 0, 0, 0))
    return np.asarray(im)


def white_roundel_dark_glyph(size=38, pad=6):
    n = size + pad * 2
    im = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse([pad, pad, pad + size - 1, pad + size - 1],
              fill=(240, 240, 240, 255))
    cx = cy = pad + size // 2
    d.rounded_rectangle([cx - 10, cy - 2, cx + 10, cy + 5], 2, fill=(20, 20, 20, 255))
    d.polygon([(cx - 7, cy - 2), (cx - 4, cy - 8), (cx + 4, cy - 8),
               (cx + 7, cy - 2)], fill=(20, 20, 20, 255))
    return np.asarray(im)


def in_atlas(tile, W=256, H=256, at=(150, 96)):
    im = np.zeros((H, W, 4), np.uint8)
    th, tw = tile.shape[:2]
    im[at[1]:at[1] + th, at[0]:at[0] + tw] = tile
    return im


def neg_square():
    im = np.zeros((50, 50, 4), np.uint8)
    im[6:44, 6:44] = (22, 33, 90, 255)
    im[20:30, 14:36] = (255, 255, 255, 255)
    return im


def neg_ring():
    im = Image.new("RGBA", (50, 50), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse([6, 6, 43, 43], outline=(22, 33, 90, 255), width=3)
    return np.asarray(im)


def neg_sky():
    im = np.zeros((64, 64, 4), np.uint8)
    im[:, :] = (60, 110, 200, 255)
    return im


def neg_noise():
    rng = np.random.default_rng(7)
    im = np.zeros((64, 64, 4), np.uint8)
    im[:, :, :3] = rng.integers(0, 255, (64, 64, 3), dtype=np.uint8)
    im[:, :, 3] = 255
    return im


CASES = [
    ("POS blue disc + car 38px", navy_disc_with_car(), "blue"),
    ("POS blue disc + heli 38px", navy_disc_with_car(glyph="heli"), "blue"),
    ("POS blue disc 20px", navy_disc_with_car(size=20, pad=4), "blue"),
    ("POS blue disc in 256 atlas", in_atlas(navy_disc_with_car()), "blue"),
    ("POS blue disc opaque black bg", navy_disc_with_car(alpha_bg=255), "blue"),
    ("POS white roundel cut-out car", white_roundel_hole(), "tint"),
    ("POS white roundel dark car", white_roundel_dark_glyph(), "tint"),
    ("POS white roundel in atlas", in_atlas(white_roundel_hole()), "tint"),
    ("NEG blue square + bar", neg_square(), "none"),
    ("NEG blue ring outline", neg_ring(), "none"),
    ("NEG flat blue sky", neg_sky(), "none"),
    ("NEG rgb noise", neg_noise(), "none"),
]

if __name__ == "__main__":
    bad = 0
    for name, img, want in CASES:
        bh, th = analyse(img)
        bs = bh[0]["score"] if bh else 0.0
        ts = th[0]["score"] if th else 0.0
        ok = {"blue": bs >= 0.35, "tint": ts >= 0.35,
              "none": bs < 0.35 and ts < 0.35}[want]
        if not ok:
            bad += 1
        print("%-32s blue=%.3f tint=%.3f  want=%-4s %s"
              % (name, bs, ts, want, "OK" if ok else "*** FAIL ***"))
        if bh:
            print("      blue: bbox=%s area=%d glyph=%.2f aspect=%.2f "
                  "compact=%.2f radial=%.2f"
                  % (bh[0]["bbox"], bh[0]["area"], bh[0]["glyph"],
                     bh[0]["aspect"], bh[0]["compact"], bh[0]["radial"]))
        if th:
            print("      tint: bbox=%s area=%d glyph=%.2f mask=%s"
                  % (th[0]["bbox"], th[0]["area"], th[0]["glyph"],
                     th[0]["mask"]))
    print("\n%d/%d controls behaved" % (len(CASES) - bad, len(CASES)))
    raise SystemExit(1 if bad else 0)
