#!/usr/bin/env python3
r"""LENS-2 probe: does GZWinBtn's /3 NINE-SLICE FALLBACK fire, and does it paint?

Run from the SC4UIScale project root:
    python probe_btn_nineslice.py            # predicate census + seam-ridge render diff
    python probe_btn_nineslice.py --node 0xc988bc79

WHAT IT MODELS (disassembled from SimCity 4.exe 1.1.641, base 0x00400000)

  0x009B167D  GZWinBtn::Paint
      if ([this+0x158] /*image*/)  0x009B0575  else  0x009B066C
      if ([this+0xdc] & 4)         0x009B1541  (caption text only)

  0x009B1179  SetButtonStyle(n)   n<=3 -> [0x138]=1, divisor 4
                                  n==4 -> [0x138]=2, divisor 8   (style=radiocheck)
  0x009B1227  cell rect, no imagerect:
      [0x13c]=0  [0x140]=0
      [0x144] = img->GetWidth()  / divisor      <-- TRUNCATING div (0x009B1243)
      [0x148] = img->GetHeight()                <-- FULL height, NO vertical divide

  0x009B0C08  Layout(winW=[ebp+8], winH=[ebp+0xc])
      mode 1 (style=standard / style=toggle), case 0x009B0EDC:
          [0x14c] = 0 + k*cellW,  k in {0,1,2,3}   (0x009B0F36/0F3B/0F43)
          [0x150] = 0   (0x009B0F4C)   <-- dx forced to zero
          [0x154] = 0   (0x009B0F53)   <-- dy forced to zero
      modes 0/2/3 instead compute  dy = (winH - cellH)/2  trunc-toward-zero
          (0x009B0CDD, 0x009B0CFF, 0x009B0D6E, 0x009B0E72, 0x009B0ED2: cdq/sub/sar 1)

  0x009B0575  image draw
      srcW = [0x144]-[0x13c]   srcH = [0x148]-[0x140]
      src  = { [0x14c], [0x140], [0x14c]+srcW, [0x148] }
      GATE at 0x009B05AA..0x009B05DE:
          (flags&0x20 && !(flags&4))          -> PLAIN
          winW == srcW                        -> PLAIN
          [0x134] == 4                        -> PLAIN
          otherwise                           -> NINE-SLICE
      PLAIN 0x009B0628: dst = {winL+[0x150], winT+[0x154], +srcW, +srcH}  (dst-follows-src)
      NINE  0x009B05E0: cornerW = srcW/3, cornerH = srcH/3  (idiv 3, 0x009B05E9/0x009B0602)
                        -> 0x008D8800, corners 1:1 via ctx->vt[0x98],
                           edges + middle STRETCHED via ctx->vt[0x9c]
"""
import re, math, glob, os, sys
import numpy as np
from PIL import Image

TIERS = [('1x', 1.0, 'tools/dbpf/extracted'),
         ('1.5x', 1.5, 'tools/selective-safe/stage-15x'),
         ('2x', 2.0, 'tools/selective-safe/stage'),
         ('3x', 3.0, 'tools/selective-safe/stage-3x')]


def R(v, f):                      # UiSpike.cpp ScaleRound == RoundHalfUp
    return math.floor(v * f + 0.5)


IDX = {}
for tier, _f, d in TIERS:
    m = {}
    for p in glob.glob(os.path.join(d, '**', '*.png'), recursive=True):
        b = os.path.basename(p).lower().replace('0x', '')
        g = re.search(r'_g-([0-9a-f]+)_i-([0-9a-f]+)\.png', b)
        if g:
            m.setdefault((g.group(1), g.group(2)), p)
    IDX[tier] = m


def arr(tier, g, i):
    p = IDX[tier].get((g, i))
    return np.asarray(Image.open(p).convert('RGB')).astype(int) if p else None


def stretch(s, w, h):             # ctx->vt[0x9c]
    sh, sw, _ = s.shape
    yi = (np.arange(h) * sh // max(h, 1)).clip(0, sh - 1)
    xi = (np.arange(w) * sw // max(w, 1)).clip(0, sw - 1)
    return s[yi][:, xi]


def nine(cell, W, H):             # 0x009B05E0 -> 0x008D8800
    ch, cw, _ = cell.shape
    kx, ky = cw // 3, ch // 3
    out = np.zeros((H, W, 3), int)
    for dy0, dy1, sy0, sy1 in [(0, ky, 0, ky), (ky, H - ky, ky, ch - ky), (H - ky, H, ch - ky, ch)]:
        for dx0, dx1, sx0, sx1 in [(0, kx, 0, kx), (kx, W - kx, kx, cw - kx), (W - kx, W, cw - kx, cw)]:
            if dy1 > dy0 and dx1 > dx0:
                out[dy0:dy1, dx0:dx1] = stretch(cell[sy0:sy1, sx0:sx1], dx1 - dx0, dy1 - dy0)
    return out


def walk(t):
    """-> [(absL, absT, w, h, rawTag)] for every node in a .UI file."""
    st, pend, out = [(0, 0)], (0, 0), []
    for m in re.finditer(r'<LEGACY[^>]*>|<CHILDREN>|</CHILDREN>', t):
        s = m.group(0)
        if s == '<CHILDREN>':
            st.append(pend)
        elif s == '</CHILDREN>':
            if len(st) > 1:
                st.pop()
        else:
            a = re.search(r'area=\((-?\d+),(-?\d+),(-?\d+),(-?\d+)\)', s)
            if not a:
                continue
            l, tp, r, b = map(int, a.groups())
            pl, pt = st[-1]
            pend = (pl + l, pt + tp)
            out.append((pl + l, pt + tp, r - l, b - tp, s))
    return out


def strips():
    """4-state strips (style=standard|toggle) whose 1x cell already == 1x window."""
    for p in sorted(glob.glob('tools/uiscripts/extracted/*.ui')):
        t = open(p, encoding='latin1').read()
        for aL, aT, w, h, s in walk(t):
            if 'GZWinBtn' not in s or 'imagerect' in s:
                continue
            sy = re.search(r'style=(\w+)', s)
            im = re.search(r'image=\{([0-9a-fA-F]+),([0-9a-fA-F]+)\}', s)
            if not im or not sy or sy.group(1) not in ('standard', 'toggle'):
                continue
            g, i = im.group(1).lower(), im.group(2).lower()
            a1 = arr('1x', g, i)
            if a1 is None or a1.shape[1] % 4 or a1.shape[1] // 4 != w:
                continue
            nid = re.search(r'id=(0x[0-9a-fA-F]+)', s)
            yield (os.path.basename(p), nid.group(1) if nid else '-', aL, aT, w, h, g, i)


def main():
    only = None
    if '--node' in sys.argv:
        only = sys.argv[sys.argv.index('--node') + 1].lower()

    fires = {t: 0 for t, _f, _d in TIERS}
    ridges15 = ridges2 = 0
    seen = []
    for fn, nid, aL, aT, w, h, g, i in strips():
        if only and nid.lower() != only:
            continue
        row = {}
        for tier, f, _d in TIERS:
            A = arr(tier, g, i)
            if A is None:
                row = None
                break
            W = R(aL + w, f) - R(aL, f)
            H = R(aT + h, f) - R(aT, f)
            cw, ch = A.shape[1] // 4, A.shape[0]
            row[tier] = (W, H, cw, ch, A)
            if W != cw:
                fires[tier] += 1
        if not row:
            continue
        if only:
            for tier, _f, _d in TIERS:
                W, H, cw, ch, _A = row[tier]
                print('  %-5s win %dx%-4d cell %dx%-4d  %s' % (
                    tier, W, H, cw, ch,
                    'PLAIN 1:1 (dx=dy=0, mode 1)' if W == cw else 'NINE-SLICE /3 FIRES'))
            continue
        for tier, ctr in (('1.5x', 'a'), ('2x', 'b')):
            W, H, cw, ch, A = row[tier]
            if W == cw:
                continue
            kx, ky = cw // 3, ch // 3
            n = nine(A[:, :cw], W, H)
            lum = n[:, kx:max(kx + 1, W - kx)].sum(2).mean(1) / 3
            rr = [(y, round(float(lum[y] - max(lum[y - 1], lum[y + 1])), 1))
                  for y in range(1, H - 1)
                  if lum[y] - max(lum[y - 1], lum[y + 1]) > 10
                  and (abs(y - ky) <= 2 or abs(y - (H - ky)) <= 2)]
            if tier == '1.5x':
                ridges15 += len(rr)
                if rr:
                    seen.append((fn, nid, W, H, cw, ch, kx, ky, rr))
            else:
                ridges2 += len(rr)

    if only:
        return
    print('NINE-SLICE predicate (winW != cellW) fires at: %s' % fires)
    print('bright seam ridges  1.5x = %d   2x control = %d' % (ridges15, ridges2))
    for s in seen:
        print('  %-42s %-12s win %dx%d cell %dx%d corner %dx%d  rows %s' % s)


if __name__ == '__main__':
    main()
