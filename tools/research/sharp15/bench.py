"""Bench the 1.5x candidates on REAL sheets, against the shipped tiers.

Output geometry is pinned to the shipped 1.5x sheet for every candidate, so the
only thing that varies is the sampler. The 2x and 3x rows are the CONTROL: at an
integer factor nearest is an exact NxN replicate, so manufactured and soft MUST
read 0 there - if they do not, the metric is broken, not the tier.
"""
import os, sys, random
import numpy as np
from PIL import Image
import resamplers as R
import metrics as M
import stroke_width as SW

UP = r"C:\dev\SC4UIScale\tools\upscale"
SRC = r"C:\dev\SC4UIScale\tools\dbpf\extracted\SimCity_1"
TIER = {"1.5": os.path.join(UP, "preview-15x", "SimCity_1"),
        "2":   os.path.join(UP, "preview", "SimCity_1"),
        "3":   os.path.join(UP, "preview-3x", "SimCity_1")}
LADDERS = {"14015549"}          # redraw_ladder.py post-step; not the resampler


def load(p):
    return np.array(Image.open(p).convert("RGBA"))


def sample(n_unkeyed, n_keyed, seed=7, maxpx=400000):
    names = sorted(os.listdir(TIER["1.5"]))
    rnd = random.Random(seed)
    rnd.shuffle(names)
    uk, kk = [], []
    for n in names:
        iid = n.split("I-")[1][:-4].replace("0x","",1)
        if iid in LADDERS:
            continue
        sp = os.path.join(SRC, n.replace("0x", ""))
        if not os.path.exists(sp):
            continue
        if not all(os.path.exists(os.path.join(TIER[t], n)) for t in TIER):
            continue
        try:
            im = Image.open(sp)
        except Exception:
            continue
        if im.size[0] * im.size[1] > maxpx or im.size[0] < 8 or im.size[1] < 8:
            continue
        a = load(sp)
        keyed = bool(((a[..., 0] == 255) & (a[..., 1] == 0) & (a[..., 2] == 255)).any())
        if keyed and len(kk) < n_keyed:
            kk.append((n, a))
        elif not keyed and len(uk) < n_unkeyed:
            uk.append((n, a))
        if len(uk) >= n_unkeyed and len(kk) >= n_keyed:
            break
    return uk, kk


def agg(rows):
    px = sum(r["px"] for r in rows)
    e = sum(r["edges"] for r in rows)
    return dict(
        sheets=len(rows), px=px,
        manuf=sum(r["manuf"] for r in rows),
        manuf_pm=1000.0 * sum(r["manuf"] for r in rows) / max(px, 1),
        soft_frac=sum(r["soft"] for r in rows) / max(e, 1),
        edge_w=(sum(r["peak_n"] for r in rows)
                / max(sum(r["peak_sum"] for r in rows), 1e-9)),
        key_near=sum(r["key_near"] for r in rows),
        key_moved=sum(r["key_moved"] for r in rows),
        key_exact=sum(r["key_exact"] for r in rows))


def run(group, label):
    print("\n===== %s  (%d sheets) =====" % (label, len(group)))
    print("%-22s %10s %8s %9s %9s %9s %9s %7s %6s %6s %6s" %
          ("path", "manuf/1k", "edge_w", "soft_frac", "key_near", "key_moved",
           "key_exact", "swc", "cv1", "cv2", "cv3"))
    # controls first
    for t in ("2", "3"):
        rows, sws = [], []
        for n, a in group:
            o = load(os.path.join(TIER[t], n))
            rows.append(M.report(o, a, float(t)))
            sws.append(SW.sheet_stats(a, o, float(t)))
        g = agg(rows)
        sp = SW.pool(sws)
        print("%-22s %10.3f %8.3f %9.4f %9d %9s %9d %7.3f %6.2f %6.2f %6.2f" %
              ("CONTROL shipped " + t + "x", g["manuf_pm"], g["edge_w"],
               g["soft_frac"], g["key_near"], "n/a", g["key_exact"],
               sp["swc"], sp["cv_1"], sp["cv_2"], sp["cv_3"]))
    rows, sws = [], []
    for n, a in group:
        o = load(os.path.join(TIER["1.5"], n))
        rows.append(M.report(o, a))
        sws.append(SW.sheet_stats(a, o, 1.5))
    g = agg(rows)
    sp = SW.pool(sws)
    print("%-22s %10.3f %8.3f %9.4f %9d %9d %9d %7.3f %6.2f %6.2f %6.2f" %
          ("SHIPPED 1.5x", g["manuf_pm"], g["edge_w"], g["soft_frac"],
           g["key_near"], g["key_moved"], g["key_exact"],
           sp["swc"], sp["cv_1"], sp["cv_2"], sp["cv_3"]))
    out = {"SHIPPED 1.5x": g}
    for k, fn in R.CANDIDATES.items():
        rows, sws = [], []
        for n, a in group:
            oh, ow = load(os.path.join(TIER["1.5"], n)).shape[:2]
            o = fn(a, ow, oh)
            rows.append(M.report(o, a))
            sws.append(SW.sheet_stats(a, o, 1.5))
        g = agg(rows)
        sp = SW.pool(sws)
        g.update(swc=sp["swc"], cv_1=sp["cv_1"], cv_2=sp["cv_2"], cv_3=sp["cv_3"])
        out[k] = g
        print("%-22s %10.3f %8.3f %9.4f %9d %9d %9d %7.3f %6.2f %6.2f %6.2f" %
              ("  " + k, g["manuf_pm"], g["edge_w"], g["soft_frac"],
               g["key_near"], g["key_moved"], g["key_exact"],
               g["swc"], g["cv_1"], g["cv_2"], g["cv_3"]))
    return out


if __name__ == "__main__":
    nu = int(sys.argv[1]) if len(sys.argv) > 1 else 120
    nk = int(sys.argv[2]) if len(sys.argv) > 2 else 60
    uk, kk = sample(nu, nk)
    run(uk, "UNKEYED sheets  (shipped path = --supersample)")
    run(kk, "KEYED sheets    (shipped path = plain NEAREST; --smooth-keyed OFF)")
