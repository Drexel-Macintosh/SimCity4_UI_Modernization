"""Candidate 1.5x resamplers for SC4UIScale. PROTOTYPE ONLY - Upscale2x.cs untouched.

Every candidate takes an HxWx4 uint8 RGBA array + the target (ow,oh) and returns
the output. Target dims are taken from the SHIPPED 1.5x tier so geometry is held
constant and only the SAMPLER varies (compare like with like).
"""
import numpy as np


def _pack(a):
    return (a[..., 0].astype(np.uint64) << 24 | a[..., 1].astype(np.uint64) << 16
            | a[..., 2].astype(np.uint64) << 8 | a[..., 3].astype(np.uint64))


# ---------------------------------------------------------------- shipped paths

def nearest(a, ow, oh, factor=1.5):
    """UpscaleNearest, Upscale2x.cs:1136. FACTOR map (#151), not the size ratio."""
    h, w = a.shape[:2]
    sx = np.minimum((np.arange(ow) / factor).astype(np.int64), w - 1)
    sy = np.minimum((np.arange(oh) / factor).astype(np.int64), h - 1)
    return a[sy][:, sx]


def _weights(n_src, n_out, scale=3):
    """Exact integer weight matrix for the shipped RATIO map: output cell o
    covers x3-grid cells [o*bs//n_out, (o+1)*bs//n_out) and x3 cell i comes from
    source cell i//scale. W[s,o] = how many x3 cells of output o came from s."""
    bs = n_src * scale
    W = np.zeros((n_src, n_out), np.int64)
    cnt = np.zeros(n_out, np.int64)
    for o in range(n_out):
        a0 = int(o * bs // n_out)
        a1 = int((o + 1) * bs // n_out)
        if a1 <= a0:
            a1 = a0 + 1
        a1 = min(a1, bs)
        idx = np.arange(a0, a1) // scale
        np.add.at(W[:, o], idx, 1)
        cnt[o] = a1 - a0
    return W, cnt


def supersample_shipped(a, ow, oh, factor=1.5):
    """UpscaleSupersample, Upscale2x.cs:1387. x3 replicate -> area mean, on the
    RATIO map (x0 = ox*bw//ow, bw = 3w). Vectorised as an exact integer weight
    product - the sum is bit-identical to the C# accumulator, then // n."""
    h, w = a.shape[:2]
    Wx, nx = _weights(w, ow)
    Wy, ny = _weights(h, oh)
    f = a.astype(np.int64)
    s = np.einsum('yh,hwc,wx->yxc', Wy.T, f, Wx, optimize=True)
    n = (ny[:, None] * nx[None, :])[..., None]
    out = (s // n).astype(np.uint8)
    m = (out[..., 0] == 255) & (out[..., 1] == 0) & (out[..., 2] == 255)
    out[..., 1][m] = 1
    return out


def _blocks(w, h, ow, oh):
    """Factor-map x3 block corners: output ox covers x3-columns [2ox, 2ox+2)."""
    cx = np.minimum(np.stack([2 * np.arange(ow), 2 * np.arange(ow) + 1]) // 3, w - 1)
    cy = np.minimum(np.stack([2 * np.arange(oh), 2 * np.arange(oh) + 1]) // 3, h - 1)
    return cx, cy


def supersample_factormap(a, ow, oh, factor=1.5):
    """SS on the FACTOR map: uniform 2x2 blocks on EVERY sheet, and identical
    feature timing to nearest (the #151 map)."""
    h, w = a.shape[:2]
    f = a.astype(np.int64)
    cx, cy = _blocks(w, h, ow, oh)
    acc = np.zeros((oh, ow, 4), np.int64)
    for iy in range(2):
        for ix in range(2):
            acc += f[cy[iy]][:, cx[ix]]
    out = (acc // 4).astype(np.uint8)
    m = (out[..., 0] == 255) & (out[..., 1] == 0) & (out[..., 2] == 255)
    out[..., 1][m] = 1
    return out


# ---------------------------------------------------------------- candidate (1)

def _mode_pick(a, ow, oh):
    """Shared by majority/ss_restore. Returns (srcy, srcx, vote, cand)."""
    h, w = a.shape[:2]
    p = _pack(a)
    cx, cy = _blocks(w, h, ow, oh)
    cand = np.stack([p[cy[iy]][:, cx[ix]] for iy in range(2) for ix in range(2)], -1)
    srcy = np.stack([np.broadcast_to(cy[iy][:, None], (oh, ow))
                     for iy in range(2) for _ in range(2)], -1)
    srcx = np.stack([np.broadcast_to(cx[ix][None, :], (oh, ow))
                     for _ in range(2) for ix in range(2)], -1)
    vote = np.zeros(cand.shape, np.int32)
    for k in range(4):
        vote[..., k] = (cand == cand[..., k:k + 1]).sum(-1)
    return p, cand, srcy, srcx, vote


def majority(a, ow, oh, factor=1.5):
    """x3 replicate -> 2x2 MODE on the factor map. At 1.5x every 2x2 block is
    one of: pure (4xA), x-edge (2A+2B), y-edge (2A+2C), corner (A,B,C,D) - so
    apart from the pure case the vote is ALWAYS A TIE and the tie-break IS the
    algorithm. Break by the 3x3 SOURCE neighbourhood count (locally dominant
    colour wins), then by the nearest-map sample. Output is always a byte-exact
    source pixel: zero manufactured colour."""
    h, w = a.shape[:2]
    p, cand, srcy, srcx, vote = _mode_pick(a, ow, oh)
    pad = np.pad(p, 1, mode='edge')
    nb = np.empty((h, w, 9), np.uint64)
    i = 0
    for dy in range(3):
        for dx in range(3):
            nb[..., i] = pad[dy:dy + h, dx:dx + w]
            i += 1
    loc = np.zeros(cand.shape, np.int32)
    for k in range(4):
        yy, xx = srcy[..., k], srcx[..., k]
        loc[..., k] = (nb[yy, xx] == cand[..., k:k + 1]).sum(-1)
    tiebrk = np.array([3, 2, 1, 0], np.int64)[None, None, :]
    score = vote.astype(np.int64) * 10000 + loc.astype(np.int64) * 10 + tiebrk
    pick = score.argmax(-1)
    py = np.take_along_axis(srcy, pick[..., None], -1)[..., 0]
    px = np.take_along_axis(srcx, pick[..., None], -1)[..., 0]
    return a[py, px]


# ---------------------------------------------------------------- candidate (3)

def _apportion(runs, total):
    """Hamilton/largest-remainder apportionment of `total` output cells over the
    source runs. Equal-length runs get equal quotas by construction; where the
    remainder ties (odd L at 1.5x -> quota .5) the extras are SPREAD EVENLY over
    the tied group rather than handed out front-to-back, so a strip of equal
    ticks alternates 4,5,4,5 instead of clustering every 5 in one half."""
    n = len(runs)
    src = float(sum(runs))
    quota = [r * total / src for r in runs]
    base = [int(np.floor(q)) for q in quota]
    rem = [round(q - b, 9) for q, b in zip(quota, base)]
    extra = total - sum(base)
    out = list(base)
    order = sorted(range(n), key=lambda i: (-rem[i], runs[i], i))
    i = 0
    while extra > 0 and i < n:
        j = i
        key = (rem[order[i]], runs[order[i]])
        while j < n and (rem[order[j]], runs[order[j]]) == key:
            j += 1
        grp = sorted(order[i:j])
        k = min(extra, len(grp))
        if k == len(grp):
            take = grp
        else:
            take = [grp[int((t + 0.5) * len(grp) / k)] for t in range(k)]
        for t in take:
            out[t] += 1
        extra -= k
        i = j
    return out


def _axis_map(lines, total):
    runs, start = [], []
    for i, s in enumerate(lines):
        if i and s == lines[i - 1]:
            runs[-1] += 1
        else:
            runs.append(1)
            start.append(i)
    got = _apportion(runs, total)
    m = []
    for r, s0, g in zip(runs, start, got):
        for t in range(g):
            m.append(s0 + min(int(t * r / g), r - 1))
    m = m[:total]
    while len(m) < total:
        m.append(len(lines) - 1)
    return np.array(m, np.int64)


def even_nearest(a, ow, oh, factor=1.5):
    """PHASE-CORRECTED NEAREST. Plain nearest doubles a FIXED phase (source
    columns 0,2,4,...), so a run's output length depends on THE PARITY OF ITS
    ORIGIN - which is exactly the 13-fours/11-fives split. Here the doubling is
    apportioned over the sheet's actual runs of identical columns/rows, so equal
    runs get equal output length wherever the arithmetic permits. Every output
    pixel is still a byte-exact copy of a source pixel: zero blend."""
    h, w = a.shape[:2]
    cols = [a[:, x].tobytes() for x in range(w)]
    rows = [a[y, :].tobytes() for y in range(h)]
    mx = _axis_map(cols, ow)
    my = _axis_map(rows, oh)
    return a[my][:, mx]


def _axis_map_cells(lines, total, states):
    """Apportion INSIDE each cell. A cell strip's contract is that the engine's
    cellW = img->Width()/count slices the sheet exactly (find_cell_strips.py /
    BuildSampleMap, Upscale2x.cs:912-936). Apportioning across the whole axis
    lets a run straddle a cell edge and drags art out of its own cell - MEASURED
    on 74 strip instances, worst {46a006b0,ac0da30b} 20 of 25 cells. Doing the
    apportionment per cell keeps every boundary on a multiple of outLen/count by
    construction."""
    n = len(lines)
    if states <= 1 or n % states or total % states:
        return _axis_map(lines, total)
    bs, bo = n // states, total // states
    out = []
    for b in range(states):
        sub = _axis_map(lines[b * bs:(b + 1) * bs], bo)
        out.extend((sub + b * bs).tolist())
    return np.array(out, np.int64)


def even_nearest_cells(a, ow, oh, states_x=0, states_y=0):
    """even_nearest with the cell-strip contract honoured on the strip axis."""
    h, w = a.shape[:2]
    cols = [a[:, x].tobytes() for x in range(w)]
    rows = [a[y, :].tobytes() for y in range(h)]
    mx = _axis_map_cells(cols, ow, states_x)
    my = _axis_map_cells(rows, oh, states_y)
    return a[my][:, mx]


# ---------------------------------------------------------------- candidate (2)

def ss_edge_restore(a, ow, oh, factor=1.5):
    """SSF then a SNAP-BACK pass: where one source pixel already owns >= 3 of the
    4 block slots, the output is pulled back to that EXACT source byte; genuine
    2+2 edges and 4-way corners keep the average. This is the 'blur then restore'
    family done losslessly - no unsharp overshoot, so it cannot fringe the key."""
    ss = supersample_factormap(a, ow, oh, factor)
    mj = majority(a, ow, oh, factor)
    _, _, _, _, vote = _mode_pick(a, ow, oh)
    dominant = vote.max(-1) >= 3
    out = ss.copy()
    out[dominant] = mj[dominant]
    return out


# 2026-09-01: the candidate table moved to x3_candidates.py, which adds the
# Scale3x / edge-claim family and wraps the prototypes above in an
# integer-factor refusal (they hard-code the 1.5 block map and were only ever
# run at 1.5). Imported last so the circular import resolves.
try:
    from x3_candidates import CANDIDATES  # noqa: E402
except ImportError:
    # x3_candidates is the module being imported first; it assigns
    # resamplers.CANDIDATES itself once its table exists.
    CANDIDATES = None
