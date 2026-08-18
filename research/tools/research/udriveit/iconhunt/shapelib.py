#!/usr/bin/env python3
r"""shapelib.py - colour-blind roundel detection.

Connected-component labelling implemented with run-length + union-find (numpy is
present, scipy is NOT on this machine).  Per component we fill interior holes
and score DISC-NESS several independent ways so no single noisy statistic can
carry a ranking on its own:

  circ_raw  = 4*pi*A / P^2       with P = count of 4-neighbour background edges
  circ_norm = circ_raw / circ_raw(synthetic disc of the same area)   -> 1.0 disc
  aspect    = min(bw,bh)/max(bw,bh)
  diskfill  = A_filled / (pi/4 * bw * bh)
  radial_cv = std(r_boundary)/mean(r_boundary)     small == round
  solidity  = A_raw / A_filled   1.0 == SOLID interior, <1 == ring/outline

The target is a SOLID roundel, so solidity is reported but never used to reject:
a white disc with a vehicle-shaped transparent hole would have solidity < 1 and
must still rank.
"""
import math
import numpy as np

# ---------------------------------------------------------------- labelling
def label(mask):
    """4-connected CCL via row runs + union-find. mask: bool HxW -> (lab, n)."""
    h, w = mask.shape
    lab = np.zeros((h, w), np.int32)
    parent = [0]
    def find(x):
        r = x
        while parent[r] != r:
            r = parent[r]
        while parent[x] != r:
            parent[x], x = r, parent[x]
        return r
    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)
    prev_runs = []
    for y in range(h):
        row = mask[y]
        if not row.any():
            prev_runs = []
            continue
        d = np.diff(np.concatenate(([0], row.view(np.int8), [0])))
        starts = np.flatnonzero(d == 1)
        ends = np.flatnonzero(d == -1)
        runs = []
        for s, e in zip(starts, ends):
            parent.append(len(parent))
            cur = len(parent) - 1
            for (ps, pe, pl) in prev_runs:
                if ps < e and s < pe:
                    union(cur, pl)
                    cur = find(cur)
            lab[y, s:e] = cur
            runs.append((s, e, cur))
        prev_runs = runs
    if len(parent) == 1:
        return lab, 0
    flat = np.array([0] * len(parent), np.int32)
    for i in range(1, len(parent)):
        flat[i] = find(i)
    uniq, inv = np.unique(flat[1:], return_inverse=True)
    remap = np.zeros(len(parent), np.int32)
    remap[1:] = inv + 1
    lab = remap[lab]
    return lab, len(uniq)


def fill_holes(sub):
    """label the BACKGROUND; any background blob not touching the bbox border is
    an interior hole and gets filled.  (The previous flood-from-border version
    seeded `reach` from an all-False padded border, so it filled the whole bbox
    and made a disc and a square score identically -- caught by the synthetic
    control below.)"""
    bg = ~sub
    if not bg.any():
        return sub.copy()
    lb, n = label(bg)
    if n == 0:
        return sub.copy()
    edge = set(lb[0, :].tolist()) | set(lb[-1, :].tolist())         | set(lb[:, 0].tolist()) | set(lb[:, -1].tolist())
    edge.discard(0)
    keep = np.zeros(n + 1, bool)
    for e in edge:
        keep[e] = True
    outside = keep[lb]
    return sub | (bg & ~outside)


def perimeter(sub):
    p = np.zeros((sub.shape[0] + 2, sub.shape[1] + 2), bool)
    p[1:-1, 1:-1] = sub
    n = 0
    n += (p[1:-1, 1:-1] & ~p[:-2, 1:-1]).sum()
    n += (p[1:-1, 1:-1] & ~p[2:, 1:-1]).sum()
    n += (p[1:-1, 1:-1] & ~p[1:-1, :-2]).sum()
    n += (p[1:-1, 1:-1] & ~p[1:-1, 2:]).sum()
    return int(n)


_DISC_CACHE = {}
def disc_circ(area):
    """circ_raw of a rasterised disc with ~the same area (calibration)."""
    r = max(1.0, math.sqrt(area / math.pi))
    key = int(round(r * 4))
    if key in _DISC_CACHE:
        return _DISC_CACHE[key]
    n = int(math.ceil(r)) * 2 + 3
    yy, xx = np.mgrid[0:n, 0:n]
    c = (n - 1) / 2.0
    d = (yy - c) ** 2 + (xx - c) ** 2 <= r * r
    A = int(d.sum()); P = perimeter(d)
    v = 4 * math.pi * A / (P * P) if P else 0.0
    _DISC_CACHE[key] = v
    return v


def components(mask, min_area=40, max_cand=60):
    """Prefilter cheaply on bincount/bbox, then score only plausible blobs.
    (Scoring every label cost one full-image np.nonzero each -- unusable on
    noisy textures with thousands of specks.)"""
    lab, n = label(mask)
    if n == 0:
        return []
    counts = np.bincount(lab.ravel(), minlength=n + 1)
    ys, xs = np.nonzero(lab)
    if len(ys) == 0:
        return []
    ls = lab[ys, xs]
    big = np.full(n + 1, 1 << 30, np.int64); small = np.full(n + 1, -1, np.int64)
    y0 = big.copy(); y1 = small.copy(); x0 = big.copy(); x1 = small.copy()
    np.minimum.at(y0, ls, ys); np.maximum.at(y1, ls, ys)
    np.minimum.at(x0, ls, xs); np.maximum.at(x1, ls, xs)
    cand = []
    for li in range(1, n + 1):
        area = int(counts[li])
        if area < min_area:
            continue
        bw = int(x1[li] - x0[li] + 1); bh = int(y1[li] - y0[li] + 1)
        if bw < 6 or bh < 6:
            continue
        asp = min(bw, bh) / float(max(bw, bh))
        if asp < 0.60:
            continue
        occ = area / float(bw * bh)
        if occ < 0.28 or occ > 0.93:      # 0.785 == disc; 1.0 == rectangle
            continue
        cand.append((area, li, int(x0[li]), int(y0[li]), bw, bh))
    cand.sort(reverse=True)
    out = []
    for (area, li, cx0, cy0, bw, bh) in cand[:max_cand]:
        sub = (lab[cy0:cy0 + bh, cx0:cx0 + bw] == li)
        filled = fill_holes(sub)
        A = int(filled.sum()); P = perimeter(filled)
        if P == 0:
            continue
        circ_raw = 4 * math.pi * A / (P * P)
        base = disc_circ(A)
        circ = circ_raw / base if base else 0.0
        aspect = min(bw, bh) / float(max(bw, bh))
        diskfill = A / (math.pi / 4.0 * bw * bh)
        pb = np.zeros((bh + 2, bw + 2), bool); pb[1:-1, 1:-1] = filled
        bnd = filled & ~(pb[:-2, 1:-1] & pb[2:, 1:-1] & pb[1:-1, :-2] & pb[1:-1, 2:])
        by, bx = np.nonzero(bnd)
        cy, cxx = np.nonzero(filled)
        ccy, ccx = cy.mean(), cxx.mean()
        rr = np.sqrt((by - ccy) ** 2 + (bx - ccx) ** 2)
        rcv = float(rr.std() / rr.mean()) if len(rr) and rr.mean() > 0 else 9.9
        out.append(dict(area=area, A=A, P=P,
                        bbox=(cx0, cy0, cx0 + bw, cy0 + bh), bw=bw, bh=bh,
                        circ_raw=circ_raw, circ=circ, aspect=aspect,
                        diskfill=diskfill, rcv=rcv, solidity=area / float(A)))
    return out


def score(c):
    """composite disc-ness in [0,1]; every term independent of colour.
    circ and diskfill are penalised in BOTH directions -- clamping circ at 1.0
    gave a perfect square full marks on that term."""
    s_circ = max(0.0, 1.0 - abs(1.0 - c["circ"]) * 2.0)
    s_asp = max(0.0, 1.0 - (1.0 - c["aspect"]) * 3.0)
    s_fill = max(0.0, 1.0 - abs(1.0 - c["diskfill"]) * 2.0)
    s_rcv = max(0.0, 1.0 - c["rcv"] * 6.0)
    return 0.34 * s_circ + 0.20 * s_asp + 0.20 * s_fill + 0.26 * s_rcv
