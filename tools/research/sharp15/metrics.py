"""Sharpness / key metrics computed on OUTPUT BYTES, never on an impression.

manufactured  a pixel whose exact RGBA does not occur anywhere in the 1x source.
              At an integer factor nearest is an NxN block replicate, so this is
              0 BY CONSTRUCTION at 2x and 3x - which is precisely why only 1.5x
              looks soft. It is the direct byte-level meaning of "soft edge".

soft_frac     of every strong luma transition along a scanline (total change
              >= 48), the fraction that is spread over MORE THAN ONE pixel step
              instead of being a single hard step. A block replicate scores 0.

key_exact     count of exact FF00FF pixels.
key_near      #181 R1: |R-255|<=8 and G<=8 and |B-255|<=8 without BEING the key.
              Any non-zero value here on a keyed sheet is the #143 pink class.
key_moved     #181 R2: exact-key pixels that differ from the nearest-neighbour
              prediction (set difference, both directions).
"""
import numpy as np

LUMA = np.array([0.299, 0.587, 0.114])


def _pack(a):
    return (a[..., 0].astype(np.uint32) << 24 | a[..., 1].astype(np.uint32) << 16
            | a[..., 2].astype(np.uint32) << 8 | a[..., 3].astype(np.uint32))


def manufactured(out, src):
    s = set(np.unique(_pack(src)).tolist())
    o = _pack(out).ravel()
    uo, inv = np.unique(o, return_inverse=True)
    isnew = np.array([int(v) not in s for v in uo.tolist()], bool)
    return int(isnew[inv].sum())


def _soft_axis(lum):
    """Vectorised. Group consecutive same-sign luma diffs into transitions; a
    transition whose total change is >= 48 counts, and it is SOFT when it needs
    more than one pixel step to cross. A block replicate can only ever produce
    single-step transitions, so this reads 0 at 2x and 3x."""
    d = np.diff(lum, axis=1)
    d = np.concatenate([d, np.zeros((d.shape[0], 1))], axis=1).ravel()
    s = np.sign(np.where(np.abs(d) < 3, 0, d)).astype(np.int8)
    prev = np.concatenate([[0], s[:-1]])
    starts = np.flatnonzero((s != 0) & (s != prev))
    if starts.size == 0:
        return 0, 0
    nxt = np.concatenate([s[1:], [0]])
    ends = np.flatnonzero((s != 0) & (s != nxt)) + 1
    tot = np.add.reduceat(d, starts)
    lens = ends - starts
    keep = np.abs(tot) >= 48
    return int(keep.sum()), int((keep & (lens > 1)).sum())


def soft_frac(out):
    a = out[..., :3].astype(np.float64)
    lum = a @ LUMA
    t1, s1 = _soft_axis(lum)
    t2, s2 = _soft_axis(lum.T)
    t, s = t1 + t2, s1 + s2
    return t, s, (s / t if t else 0.0)


def edge_peak(lum):
    """EDGE TRANSITION WIDTH, and unlike soft_frac it is valid ACROSS factors.

    For each strong transition, peak|dLuma| / total|dLuma|. A block replicate
    crosses in ONE step so the ratio is 1.0 whatever the factor; a 50/50 blend
    crosses in two equal steps so it is 0.50. The reciprocal is the transition
    width in output pixels, which is the literal meaning of "soft edge"."""
    d = np.diff(lum, axis=1)
    d = np.concatenate([d, np.zeros((d.shape[0], 1))], axis=1).ravel()
    s = np.sign(np.where(np.abs(d) < 3, 0, d)).astype(np.int8)
    prev = np.concatenate([[0], s[:-1]])
    starts = np.flatnonzero((s != 0) & (s != prev))
    if starts.size == 0:
        return 0.0, 0
    tot = np.abs(np.add.reduceat(d, starts))
    mx = np.maximum.reduceat(np.abs(d), starts)
    keep = tot >= 48
    if not keep.any():
        return 0.0, 0
    return float((mx[keep] / tot[keep]).sum()), int(keep.sum())


def peak_ratio(out):
    a = out[..., :3].astype(np.float64)
    lum = a @ LUMA
    s1, n1 = edge_peak(lum)
    s2, n2 = edge_peak(lum.T)
    n = n1 + n2
    return ((s1 + s2) / n if n else 1.0), n


def key_masks(a):
    r, g, b = a[..., 0].astype(int), a[..., 1].astype(int), a[..., 2].astype(int)
    exact = (r == 255) & (g == 0) & (b == 255)
    near = (np.abs(r - 255) <= 8) & (g <= 8) & (np.abs(b - 255) <= 8) & ~exact
    return exact, near


def nn_key_prediction(src, ow, oh, factor=1.5):
    h, w = src.shape[:2]
    sx = np.minimum((np.arange(ow) / factor).astype(np.int64), w - 1)
    sy = np.minimum((np.arange(oh) / factor).astype(np.int64), h - 1)
    ex, _ = key_masks(src)
    return ex[sy][:, sx]


def report(out, src, factor=1.5):
    oh, ow = out.shape[:2]
    ex, near = key_masks(out)
    pred = nn_key_prediction(src, ow, oh, factor)
    t, s, sf = soft_frac(out)
    pr, pn = peak_ratio(out)
    man = manufactured(out, src)
    npx = oh * ow
    return dict(px=npx,
                manuf=man, manuf_pm=1000.0 * man / npx,
                edges=t, soft=s, soft_frac=sf,
                key_exact=int(ex.sum()), key_near=int(near.sum()),
                peak_sum=pr * pn, peak_n=pn,
                key_moved=int((ex ^ pred).sum()))


def runs_of(row):
    """Run-length decomposition of one output scanline (packed RGBA)."""
    out, cur = [], 1
    for i in range(1, len(row)):
        if row[i] == row[i - 1]:
            cur += 1
        else:
            out.append(cur)
            cur = 1
    out.append(cur)
    return out
