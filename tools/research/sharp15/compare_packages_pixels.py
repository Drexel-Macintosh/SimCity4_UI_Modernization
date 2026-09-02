r"""PIXEL-LEVEL compare of two built dats, entry by entry - the honest delta
between what the user judged on screen and what ships.

    python compare_packages_pixels.py <dat_a> <dat_b> [--label-a X --label-b Y]

Decodes every PNG entry (type 0x856ddbac) from both DBPF indexes and reports,
per package: bytes-identical entries, pixel-identical entries (RGBA, alpha
included - review 2026-09-01: an alpha-blind compare understated a 200k-pixel
alpha flip), entries that differ, and for those the count of differing pixels
split into COLOUR differences and ALPHA-ONLY differences (RGB equal, A not).
Also lists how many of the alpha-only differences sit on colour-key pixels.

Offline. Reads two dats. Exit 0 always (this is a report, not a gate).
"""
import io
import struct
import sys

import numpy as np
from PIL import Image

PNG_TYPE = 0x856DDBAC


def entries(path):
    d = open(path, 'rb').read()
    count, offset, size = struct.unpack_from('<III', d, 0x24)
    out = {}
    for k in range(count):
        t, g, i, off, sz = struct.unpack_from('<IIIII', d, offset + k * 20)
        out[(t, g, i)] = d[off:off + sz]
    return out


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    a, b = entries(argv[0]), entries(argv[1])
    la = argv[argv.index('--label-a') + 1] if '--label-a' in argv else 'A'
    lb = argv[argv.index('--label-b') + 1] if '--label-b' in argv else 'B'
    same = set(a) & set(b)
    stats = dict(entries=len(same), only_a=len(set(a) - set(b)), only_b=len(set(b) - set(a)),
                 bytes_same=0, px_same=0, px_diff=0, nonpng_diff=0,
                 colour_px=0, alpha_only_px=0, alpha_only_on_key=0, dims_diff=0)
    worst = []
    for k in sorted(same):
        if a[k] == b[k]:
            stats['bytes_same'] += 1
            continue
        if k[0] != PNG_TYPE:
            stats['nonpng_diff'] += 1
            continue
        ia = np.array(Image.open(io.BytesIO(a[k])).convert('RGBA'))
        ib = np.array(Image.open(io.BytesIO(b[k])).convert('RGBA'))
        if ia.shape != ib.shape:
            stats['dims_diff'] += 1
            stats['px_diff'] += 1
            continue
        d_rgb = np.any(ia[..., :3] != ib[..., :3], axis=-1)
        d_a = ia[..., 3] != ib[..., 3]
        if not d_rgb.any() and not d_a.any():
            stats['px_same'] += 1
            continue
        stats['px_diff'] += 1
        colour = int(d_rgb.sum())
        alpha_only = int((d_a & ~d_rgb).sum())
        key = (ia[..., 0] == 255) & (ia[..., 1] == 0) & (ia[..., 2] == 255)
        stats['colour_px'] += colour
        stats['alpha_only_px'] += alpha_only
        stats['alpha_only_on_key'] += int((d_a & ~d_rgb & key).sum())
        worst.append((colour + alpha_only, '%08x/%08x' % (k[1], k[2]), colour, alpha_only, ia.shape[1], ia.shape[0]))
    worst.sort(reverse=True)
    print('%s vs %s: %d common entries (%d only in %s, %d only in %s)'
          % (la, lb, stats['entries'], stats['only_a'], la, stats['only_b'], lb))
    print('  bytes-identical %d | pixel-identical %d | differ %d (dims differ %d, non-PNG %d)'
          % (stats['bytes_same'], stats['px_same'], stats['px_diff'], stats['dims_diff'], stats['nonpng_diff']))
    print('  differing pixels: COLOUR %d | ALPHA-ONLY %d (of which on colour-key pixels %d)'
          % (stats['colour_px'], stats['alpha_only_px'], stats['alpha_only_on_key']))
    for tot, name, c, al, w, h in worst[:8]:
        print('    %-18s %4dx%-4d colour %6d  alpha-only %6d' % (name, w, h, c, al))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
