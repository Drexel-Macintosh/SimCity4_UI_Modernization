"""x3-GRID CANDIDATES for the "ragged strokes" report (2026-09-01 plan).

Every candidate takes (a, ow, oh, factor=1.5, states_x=0, states_y=0,
wrap=False, tol=0) and REFUSES ITSELF AT AN INTEGER FACTOR by returning
nearest() - the lab form of Upscale2x.cs's FATAL "smoothing fired at an integer
factor". theorem_check.py asserts it.

The x3 grid: source pixel (y,x) owns x3 cells [3y,3y+3) x [3x,3x+3). At f=1.5
an output pixel (oy,ox) is the 2x2 block of x3 cells [2oy,2oy+2) x [2ox,2ox+2)
- the FACTOR map, so feature timing is identical to nearest (#151: the ratio
map re-times features). The x3 intermediate is either a plain replicate
(copies only) or the Scale3x reconstruction (still copies only: Scale3x never
invents a colour).

THE ODD/EVEN THEOREM this file exists to beat. At 3/2 a run of width w wants
1.5w pixels, an integer only for even w. Plain nearest is consistent for even
widths (2->3, 4->6) and a coin-flip for odd ones (1->1|2, 3->4|5). A naive
"give the tie to the longer run" fixes odd widths and breaks even ones. The
EDGE-CLAIM rule below is consistent for both: an even short run at half-offset
owns TWO tie blocks and takes exactly its left/top one (net 1.5w, exact); an
odd short run owns exactly ONE tie block and the policy decides it (thin:
never, bold: always); long runs (>= LONG_RUN) never claim and absorb the
remainder, where a +-1 is invisible.
"""
import numpy as np

from resamplers import (nearest, _pack, supersample_shipped, supersample_factormap,
                        majority, even_nearest, ss_edge_restore)

LONG_RUN = 5   # a run this wide absorbs a +-1 without the eye noticing
KEY = np.array([255, 0, 255, 255], np.uint8)


def _is_int(f):
    return float(f) == float(int(f))


def _runlen_x(p):
    """Length of the horizontal run containing each pixel of packed HxW."""
    h, w = p.shape
    start = np.ones((h, w), bool)
    start[:, 1:] = p[:, 1:] != p[:, :-1]
    ids = np.cumsum(start.ravel()) - 1
    lens = np.bincount(ids)
    return lens[ids].reshape(h, w)


SALIENT_LUMA = 48   # metrics.py's "strong transition"; a run is a STROKE when it
                    # contrasts with BOTH neighbours by at least this much
LUMA = np.array([0.299, 0.587, 0.114])


def _run_maps(p, rgba):
    """Per pixel, along rows: (run length, is-salient-stroke). Salient = the
    run's luma differs from the run to its left AND to its right by >=
    SALIENT_LUMA; runs touching the sheet edge are never salient."""
    h, w = p.shape
    start = np.ones((h, w), bool)
    start[:, 1:] = p[:, 1:] != p[:, :-1]
    flat_start = start.ravel()
    ids = np.cumsum(flat_start) - 1
    lens = np.bincount(ids)
    starts = np.flatnonzero(flat_start)
    ends = starts + lens
    lum = (rgba[..., :3].astype(np.float64) @ LUMA).ravel()
    run_lum = lum[starts]
    scol = starts % w
    ecol = ends - (starts - scol)          # end column (exclusive) within the row
    has_l = scol > 0
    has_r = ecol < w
    ll = np.where(has_l, lum[np.maximum(starts - 1, 0)], run_lum)
    rl = np.where(has_r, lum[np.minimum(ends, lum.size - 1)], run_lum)
    sal = has_l & has_r & (np.abs(run_lum - ll) >= SALIENT_LUMA) & (np.abs(run_lum - rl) >= SALIENT_LUMA)
    return lens[ids].reshape(h, w), sal[ids].reshape(h, w)


def scale3x(a, tol=0, pad="edge"):
    """Clean-room Scale3x (AdvanceMAME / EPX family), written from the published
    rule description; no reference code consulted or vendored (the reference
    is GPL, this repo is CC0). `tol` = max-channel |difference| that still
    counts as "equal" (0 = exact). Copies pixels only - zero invented colours;
    the FF00FF key is a colour and only ever equals itself."""
    h, w = a.shape[:2]
    P = np.pad(a, ((1, 1), (1, 1), (0, 0)), mode=pad)
    A, B, C = P[0:h, 0:w], P[0:h, 1:w + 1], P[0:h, 2:w + 2]
    D, E, F = P[1:h + 1, 0:w], P[1:h + 1, 1:w + 1], P[1:h + 1, 2:w + 2]
    G, H, I = P[2:h + 2, 0:w], P[2:h + 2, 1:w + 1], P[2:h + 2, 2:w + 2]
    if tol == 0:
        def eq(p, q):
            return np.all(p == q, axis=-1)
    else:
        def eq(p, q):
            return np.abs(p.astype(np.int16) - q.astype(np.int16)).max(-1) <= tol
    act = ~eq(B, H) & ~eq(D, F)
    DB, BF, DH, HF = eq(D, B), eq(B, F), eq(D, H), eq(H, F)
    EC, EA, EG, EI = eq(E, C), eq(E, A), eq(E, G), eq(E, I)
    out = np.empty((h, 3, w, 3, 4), np.uint8)
    out[...] = E[:, None, :, None, :]

    def put(iy, ix, cond, src):
        m = act & cond
        v = out[:, iy, :, ix, :]
        v[m] = src[m]
        out[:, iy, :, ix, :] = v
    put(0, 0, DB, D)
    put(0, 1, (DB & ~EC) | (BF & ~EA), B)
    put(0, 2, BF, F)
    put(1, 0, (DB & ~EG) | (DH & ~EA), D)
    put(1, 2, (BF & ~EI) | (HF & ~EC), F)
    put(2, 0, DH, D)
    put(2, 1, (DH & ~EI) | (HF & ~EG), H)
    put(2, 2, HF, F)
    return out.reshape(3 * h, 3 * w, 4)


def _x3_replicate(a):
    return np.repeat(np.repeat(a, 3, 0), 3, 1)


def _block_cells(X, ow, oh):
    """The four x3 cells of every output block (factor map, clamped).
    Returns array (oh, ow, 4, 4): cells in order c00, c01, c10, c11."""
    H3, W3 = X.shape[:2]
    cy = np.minimum(np.stack([2 * np.arange(oh), 2 * np.arange(oh) + 1]), H3 - 1)
    cx = np.minimum(np.stack([2 * np.arange(ow), 2 * np.arange(ow) + 1]), W3 - 1)
    return np.stack([X[cy[iy]][:, cx[ix]] for iy in range(2) for ix in range(2)], 2)


def _box2(X, ow, oh):
    """Exact 2:1 area reduce of the x3 grid on the factor map, KEY-AWARE the
    way UpscaleSupersample is (Upscale2x.cs:1522-1534): key cells carry zero
    weight, each output divides by the coverage it accumulated, and a block
    the key owns by half or more is re-emitted as EXACT FF00FF."""
    cells = _block_cells(X, ow, oh).astype(np.int64)          # oh,ow,4,4
    key = (cells[..., 0] == 255) & (cells[..., 1] == 0) & (cells[..., 2] == 255)
    nkey = key.sum(-1)
    wgt = (~key).astype(np.int64)
    s = (cells * wgt[..., None]).sum(2)
    n = np.maximum(wgt.sum(-1), 1)
    out = (s // n[..., None]).astype(np.uint8)
    keyout = nkey * 2 >= 4
    out[keyout] = KEY
    # never let an average land ON the key by accident (the G=1 nudge the
    # shipped path uses)
    acc = (out[..., 0] == 255) & (out[..., 1] == 0) & (out[..., 2] == 255) & ~keyout
    out[..., 1][acc] = 1
    return out


def _pack64(cells):
    return (cells[..., 0].astype(np.uint64) << np.uint64(24)
            | cells[..., 1].astype(np.uint64) << np.uint64(16)
            | cells[..., 2].astype(np.uint64) << np.uint64(8)
            | cells[..., 3].astype(np.uint64))


def _decide(pick, tie, wP, wQ, salP, salQ, policy, left_idx, right_idx):
    """Apply the claim rule on the tie mask. P = left/top run (this tie is its
    RIGHT/BOTTOM edge), Q = right/bottom run (this tie is its LEFT/TOP edge).

    A run CLAIMS only if it is a salient short stroke (contrasts with both of
    its neighbours by >= SALIENT_LUMA and is < LONG_RUN wide). Everything else
    - a long run, or a gradient step whose neighbours are close in luma - is
    an ABSORBER: a +-1 there is invisible. (First version keyed on run length
    alone and found no absorber inside a bevel gradient, where every run is
    1px, so it fell back to nearest on exactly the strokes the user sees.)"""
    bold = policy == "bold"
    cP = salP & (wP < LONG_RUN)
    cQ = salQ & (wQ < LONG_RUN)
    evenP, evenQ = (wP % 2 == 0), (wQ % 2 == 0)
    out = pick.copy()
    # 1. structural: a salient even run takes its LEFT/TOP tie (Q here)
    m = tie & cQ & evenQ
    out[m] = right_idx
    rest = tie & ~m
    # 2. odd claimants under the policy
    P_odd, Q_odd = cP & ~evenP, cQ & ~evenQ
    if bold:
        out[rest & P_odd & ~Q_odd] = left_idx
        out[rest & Q_odd & ~P_odd] = right_idx
        # both odd claimants -> nearest sample (left cell), pick already holds it
        rest2 = rest & ~P_odd & ~Q_odd
    else:
        # thin: an odd claimant refuses; the other side absorbs unless it is
        # itself a refusing claimant (-> nearest)
        out[rest & P_odd & ~Q_odd] = right_idx
        out[rest & Q_odd & ~P_odd] = left_idx
        rest2 = rest & ~P_odd & ~Q_odd
    # 3. P is a salient even run: this is its RIGHT tie, it does not claim ->
    #    Q absorbs (Q is not a claimant here, or it would have been handled)
    out[rest2 & cP & evenP] = right_idx
    # 4. neither side claims -> nearest sample (left cell)
    return out


def _claim(X, src, ow, oh, policy, return_mask=False):
    """EDGE-CLAIM tie rule on the x3 grid - copy-only, and consistent for
    every stroke width <= 4 (theorem_check.py prints the table):

      block has a strict majority colour   -> that colour
      2+2 tie across a genuine SOURCE edge -> _decide (the claim rule)
      anything else (diagonal 2+2, 2+1+1, 4 distinct, a tie that is not a
      source edge because Scale3x rewrote a corner) -> nearest sample (c00)

    src: the UNPADDED source cell the grid X was built from (for run widths).
    """
    h, w = src.shape[:2]
    p = _pack(src).astype(np.uint64)
    rlx, slx = _run_maps(p, src)
    rly, sly = _run_maps(np.ascontiguousarray(p.T), np.ascontiguousarray(np.transpose(src, (1, 0, 2))))
    rly, sly = rly.T, sly.T
    cells = _block_cells(X, ow, oh)                                # oh,ow,4,4
    pc = _pack64(cells)                                             # oh,ow,4
    c00, c01, c10, c11 = pc[..., 0], pc[..., 1], pc[..., 2], pc[..., 3]
    pick = np.zeros((oh, ow), np.int64)                            # default c00
    for k in range(4):
        same = sum((pc[..., j] == pc[..., k]).astype(np.int64) for j in range(4))
        pick[same >= 3] = k
    H3, W3 = X.shape[:2]
    oyi = np.arange(oh)[:, None]
    oxi = np.arange(ow)[None, :]
    r0 = np.broadcast_to(np.minimum(2 * oyi, H3 - 1) // 3, (oh, ow))
    r1 = np.broadcast_to(np.minimum(2 * oyi + 1, H3 - 1) // 3, (oh, ow))
    q0 = np.broadcast_to(np.minimum(2 * oxi, W3 - 1) // 3, (oh, ow))
    q1 = np.broadcast_to(np.minimum(2 * oxi + 1, W3 - 1) // 3, (oh, ow))
    # x-tie across a genuine source edge
    xtie = (c00 == c10) & (c01 == c11) & (c00 != c01) & (q1 == q0 + 1)
    xtie &= (c00 == p[r0, q0]) & (c01 == p[r0, q1])
    pick = _decide(pick, xtie, rlx[r0, q0], rlx[r0, q1], slx[r0, q0], slx[r0, q1], policy, 0, 1)
    # y-tie across a genuine source edge
    ytie = (c00 == c01) & (c10 == c11) & (c00 != c10) & (r1 == r0 + 1)
    ytie &= (c00 == p[r0, q0]) & (c10 == p[r1, q0])
    pick = _decide(pick, ytie, rly[r0, q0], rly[r1, q0], sly[r0, q0], sly[r1, q0], policy, 0, 2)
    out = np.take_along_axis(cells, pick[..., None, None], 2)[:, :, 0, :]
    if not return_mask:
        return out
    # HYBRID mask: a block is COPY-decided when it has a majority or sits on a
    # STRAIGHT tie - the same tie (same colour pair, same orientation) in the
    # neighbouring block along the edge. An isolated tie is a staircase step
    # of a diagonal or a curve: those blocks take the area average instead,
    # which is how a vector UI renders at 150%: straight edges snap to the
    # pixel grid, curves get anti-aliased.
    maj = np.zeros((oh, ow), bool)
    for k in range(4):
        same = sum((pc[..., j] == pc[..., k]).astype(np.int64) for j in range(4))
        maj |= same >= 3
    def straight(tie, axis):
        up = np.roll(tie, 1, axis=axis) & np.roll(c00, 1, axis=axis).__eq__(c00)             & (np.roll(c01 if axis == 0 else c10, 1, axis=axis) == (c01 if axis == 0 else c10))
        dn = np.roll(tie, -1, axis=axis) & (np.roll(c00, -1, axis=axis) == c00)             & (np.roll(c01 if axis == 0 else c10, -1, axis=axis) == (c01 if axis == 0 else c10))
        return tie & (up | dn)
    copy = maj | straight(xtie, 0) | straight(ytie, 1)
    return out, copy


def _per_cell(a, ow, oh, states_x, states_y, fn):
    """Run fn(cell, cell_ow, cell_oh) per state cell so a cell can never see
    its neighbour (#169). Falls back to whole-sheet when the counts do not
    divide both source and output."""
    h, w = a.shape[:2]
    sx = states_x if (states_x > 1 and w % states_x == 0 and ow % states_x == 0) else 1
    sy = states_y if (states_y > 1 and h % states_y == 0 and oh % states_y == 0) else 1
    if sx == 1 and sy == 1:
        return fn(a, ow, oh)
    bs, bo = w // sx, ow // sx
    hs, ho = h // sy, oh // sy
    rows = []
    for j in range(sy):
        cols = []
        for i in range(sx):
            cell = a[j * hs:(j + 1) * hs, i * bs:(i + 1) * bs]
            cols.append(fn(cell, bo, ho))
        rows.append(np.concatenate(cols, 1))
    return np.concatenate(rows, 0)


def _make(reconstruct, mode):
    def cand(a, ow, oh, factor=1.5, states_x=0, states_y=0, wrap=False, tol=0):
        if _is_int(factor):
            return nearest(a, ow, oh, factor)
        if abs(factor - 1.5) > 1e-9:
            raise ValueError("x3-grid candidates are defined for f=1.5 only")
        pad = "wrap" if wrap else "edge"

        def one(cell, cw, ch):
            X = scale3x(cell, tol, pad) if reconstruct else _x3_replicate(cell)
            if mode == "box":
                return _box2(X, cw, ch)
            if mode.endswith("_h"):
                # HYBRID: copy where the edge is straight, average elsewhere
                cp, mask = _claim(X, cell, cw, ch, mode[:-2], return_mask=True)
                bx = _box2(X, cw, ch)
                return np.where(mask[..., None], cp, bx)
            return _claim(X, cell, cw, ch, mode)
        return _per_cell(a, ow, oh, states_x, states_y, one)
    cand.__name__ = ("scale3x_" if reconstruct else "") + mode
    return cand


thin = _make(False, "thin")
bold = _make(False, "bold")
box = _make(False, "box")            # == area-average on the factor map
thin_h = _make(False, "thin_h")      # hybrid: straight edges copy (thin), curves average
bold_h = _make(False, "bold_h")      # hybrid: straight edges copy (bold), curves average
scale3x_thin = _make(True, "thin")
scale3x_bold = _make(True, "bold")
scale3x_box = _make(True, "box")


def _guard(fn):
    """Integer-factor refusal for the 2026-08 prototypes, which were only
    ever run at 1.5 and hard-code the x3 block map."""
    def g(a, ow, oh, factor=1.5, **kw):
        if _is_int(factor):
            return nearest(a, ow, oh, factor)
        return fn(a, ow, oh, factor)
    g.__name__ = fn.__name__
    return g


CANDIDATES = {
    'nearest':      nearest,
    'ss_shipped':   _guard(supersample_shipped),
    'ss_factormap': _guard(supersample_factormap),
    'majority':     _guard(majority),
    'even_nearest': _guard(even_nearest),
    'ss_restore':   _guard(ss_edge_restore),
    'box':          box,
    'thin':         thin,
    'bold':         bold,
    'thin_h':       thin_h,
    'bold_h':       bold_h,
    'scale3x_box':  scale3x_box,
    'scale3x_thin': scale3x_thin,
    'scale3x_bold': scale3x_bold,
}

# whichever module was imported first, both end with the same table
import resamplers as _R  # noqa: E402
_R.CANDIDATES = CANDIDATES
