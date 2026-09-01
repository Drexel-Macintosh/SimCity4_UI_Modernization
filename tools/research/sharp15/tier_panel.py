r"""WHOLE-IMAGE, SAME-SHEET COMPARISON ACROSS TIERS - what the user asked for.

    "Not just the edges. The entire images should be compared so you can see
     the quality difference in 1.5x vs 2x vs 3x for the same image."  (2026-09-01)

For each sheet this lays out, left to right, the SAME image as
    1x source | 1.5x shipped | [1.5x candidates...] | 2x shipped | 3x shipped
every pane NEAREST-magnified to a common 6x-of-1x size (1x x6, 1.5x x4, 2x x3,
3x x2) so the eye compares QUALITY at equal physical size and the display
itself introduces no resampling. Under each pane: the whole-image numbers -
invented colours per 1k px, soft-edge fraction, edge width, stroke-width CV -
so the picture and the metric sit side by side.

Sheets wider than --maxw 1x pixels are cropped (stated in the label) unless a
--crop x,y,w,h (1x coordinates) is given.

    python tier_panel.py 46a006b0 14015546 [--cand thin,bold,...] [--crop x,y,w,h]
    python tier_panel.py --set default          # the plan's representative set
    python tier_panel.py --random 8 --seed 3

Output: _tests\captures\tier-panels\<group>_<instance>.png  (gitignored:
these are magnified game art).
"""
import os
import re
import sys
import random

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
UP = os.path.join(REPO, "tools", "upscale")
SRC = os.path.join(REPO, "tools", "dbpf", "extracted", "SimCity_1")
TIER = {"1.5": os.path.join(UP, "preview-15x", "SimCity_1"),
        "2": os.path.join(UP, "preview", "SimCity_1"),
        "3": os.path.join(UP, "preview-3x", "SimCity_1")}
OUT = os.path.join(REPO, "_tests", "captures", "tier-panels")
MAG = {1.0: 6, 1.5: 4, 2.0: 3, 3.0: 2}

sys.path.insert(0, HERE)
import metrics as M            # noqa: E402
import stroke_width as SW      # noqa: E402

# The plan's representative set (class -> TGI). Verified TGIs where the plan
# could; the rest are found by predicate at run time.
DEFAULT_SET = [
    ("toolbar rail (tiled)",   "46a006b0", "14015546"),
    ("mode button strip",      "46a006b0", "14015555"),
    ("mode button strip",      "46a006b0", "13f15230"),
    ("god-mode expand btn",    "46a006b0", "14415860"),
    ("mode button strip",      "46a006b0", "13e14fb3"),
    ("NN-bimodal button",      "46a006b0", "cbcb9a74"),
    ("NN-bimodal button",      "00000001", "144161e0"),
    ("9-slice dialog frame",   "1abe787d", "144161e4"),
    ("advisor face frame",     "46a006b0", "14015571"),
    ("trend bar (even path)",  "46a006b0", "14015584"),
    ("tiled background",       "46a006b0", "13e14f70"),
]


def find(group, inst):
    g, i = group.lower().replace("0x", ""), inst.lower().replace("0x", "")
    src = None
    for n in os.listdir(SRC):
        m = re.match(r"^T-(?:0x)?([0-9a-f]{8})_G-(?:0x)?([0-9a-f]{8})_I-(?:0x)?([0-9a-f]{8})\.png$", n, re.I)
        if m and m.group(2).lower() == g and m.group(3).lower() == i:
            src = n
            break
    if src is None:
        return None
    t = re.match(r"^T-(?:0x)?([0-9a-f]{8})", src, re.I).group(1)
    tier_name = "T-0x%s_G-0x%s_I-0x%s.png" % (t.lower(), g, i)
    paths = {"1": os.path.join(SRC, src)}
    for k, d in TIER.items():
        p = os.path.join(d, tier_name)
        if not os.path.exists(p):
            # some trees keep the un-prefixed name
            p2 = os.path.join(d, src)
            p = p2 if os.path.exists(p2) else None
        paths[k] = p
    return paths


def load(p):
    return np.array(Image.open(p).convert("RGBA"))


def mag(a, k):
    """Nearest magnify for DISPLAY; the FF00FF key composites as transparent
    (it is the engine's transparency, not a colour) and alpha is forced opaque
    elsewhere so a 0-alpha source pixel still shows its RGB."""
    a = a.copy()
    key = (a[..., 0] == 255) & (a[..., 1] == 0) & (a[..., 2] == 255)
    a[..., 3] = 255
    a[key, 3] = 0
    return np.repeat(np.repeat(a, k, 0), k, 1)


def numbers(out, src, f):
    r = M.report(out, src, f)
    sw = SW.sheet_stats(src, out, f)
    return ("inv/1k %.1f soft %.2f ew %.2f" "\n" "swc %.3f cv1 %.2f cv2 %.2f cv3 %.2f"
            % (r["manuf_pm"], r["soft_frac"],
               (r["peak_n"] / r["peak_sum"]) if r["peak_sum"] else 1.0,
               sw["swc"], sw["cv_1"], sw["cv_2"], sw["cv_3"]))


def crop_src(a, crop, maxw):
    h, w = a.shape[:2]
    if crop:
        x, y, cw, ch = crop
        return (x, y, min(cw, w - x), min(ch, h - y)), True
    if w > maxw:
        return (0, 0, maxw, h), True
    return (0, 0, w, h), False


def panel(group, inst, label="", cands=(), crop=None, maxw=240, states=None):
    paths = find(group, inst)
    if not paths or not all(paths.values()):
        print("skip %s %s: missing tier file" % (group, inst), paths)
        return None
    src = load(paths["1"])
    (x, y, cw, ch), cropped = crop_src(src, crop, maxw)
    panes = []
    # 1x
    panes.append(("1x source %dx%d%s" % (src.shape[1], src.shape[0],
                                         " (crop)" if cropped else ""),
                  mag(src[y:y + ch, x:x + cw], MAG[1.0]), ""))
    outs = {}
    for k in ("1.5", "2", "3"):
        o = load(paths[k])
        outs[k] = o
    # candidates at 1.5x, output dims pinned to the shipped 1.5x sheet
    o15 = outs["1.5"]
    oh, ow = o15.shape[:2]
    cand_imgs = []
    if cands:
        import x3_candidates as X
        sx = states or 0
        for c in cands:
            fn = X.CANDIDATES[c]
            try:
                oc = fn(src, ow, oh, factor=1.5, states_x=sx)
            except TypeError:
                oc = fn(src, ow, oh)
            cand_imgs.append((c, oc))

    def tier_pane(name, o, f):
        fy0, fx0 = int(y * f), int(x * f)
        fy1, fx1 = int(np.ceil((y + ch) * f)), int(np.ceil((x + cw) * f))
        sub = o[fy0:fy1, fx0:fx1]
        return (name + " %dx%d" % (o.shape[1], o.shape[0]), mag(sub, MAG[float(f)]),
                numbers(o, src, f))
    panes.append(tier_pane("1.5x shipped", o15, 1.5))
    for c, oc in cand_imgs:
        panes.append(tier_pane("1.5x " + c, oc, 1.5))
    panes.append(tier_pane("2x shipped", outs["2"], 2.0))
    panes.append(tier_pane("3x shipped", outs["3"], 3.0))
    # layout
    gap, top, bottom = 12, 18, 44
    MINW = 200                      # room for the two-line numbers
    H = max(p[1].shape[0] for p in panes)
    W = sum(max(p[1].shape[1], MINW) for p in panes) + gap * (len(panes) - 1)
    canvas = Image.new("RGBA", (W, H + top + bottom), (24, 24, 28, 255))
    d = ImageDraw.Draw(canvas)
    xx = 0
    for name, im, nums in panes:
        canvas.paste(Image.fromarray(im, "RGBA"), (xx, top))
        d.text((xx + 2, 2), name, fill=(235, 235, 225, 255))
        if nums:
            d.text((xx + 2, top + H + 4), nums, fill=(200, 210, 200, 255))
        xx += max(im.shape[1], MINW) + gap
    hdr = "%s  {%s,%s}" % (label, group, inst)
    d.text((W - 8 * len(hdr) - 4, 2) if W > 8 * len(hdr) + 8 else (2, top + H + 16),
           hdr, fill=(255, 200, 120, 255))
    os.makedirs(OUT, exist_ok=True)
    fn = os.path.join(OUT, "%s_%s.png" % (group, inst))
    canvas.save(fn)
    print("wrote", fn, canvas.size, "panes:", [p[0] for p in panes])
    return fn


def main(argv):
    cands = ()
    crop = None
    maxw = 240
    args = list(argv)
    if "--cand" in args:
        i = args.index("--cand")
        cands = tuple(args[i + 1].split(","))
        del args[i:i + 2]
    if "--crop" in args:
        i = args.index("--crop")
        crop = tuple(int(v) for v in args[i + 1].split(","))
        del args[i:i + 2]
    if "--maxw" in args:
        i = args.index("--maxw")
        maxw = int(args[i + 1])
        del args[i:i + 2]
    strips = {}
    try:
        for line in open(os.path.join(UP, "cell-strips.txt"), encoding="utf-8", errors="replace"):
            s = line.strip()
            if s and not s.startswith("#"):
                parts = s.split()
                if len(parts) >= 3:
                    strips[(parts[0].lower(), parts[1].lower())] = int(parts[2])
    except OSError:
        pass
    jobs = []
    if args and args[0] == "--set":
        jobs = list(DEFAULT_SET)
    elif args and args[0] == "--random":
        n = int(args[1])
        seed = int(args[args.index("--seed") + 1]) if "--seed" in args else 7
        names = sorted(os.listdir(TIER["1.5"]))
        random.Random(seed).shuffle(names)
        for nm in names:
            m = re.match(r"^T-(?:0x)?([0-9a-f]{8})_G-(?:0x)?([0-9a-f]{8})_I-(?:0x)?([0-9a-f]{8})\.png$", nm, re.I)
            if m:
                jobs.append(("random", m.group(2).lower(), m.group(3).lower()))
            if len(jobs) >= n:
                break
    elif len(args) >= 2:
        jobs = [("", args[0], args[1])]
    else:
        print(__doc__)
        return 2
    for label, g, i in jobs:
        panel(g, i, label, cands, crop, maxw, strips.get((g.lower(), i.lower())))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
