#!/usr/bin/env python3
r"""iconhunt stage 2 - decode EVERY indexed image resource and score it.

Writes rows.tsv (one line per decoded image), fails.tsv (one line per failure,
with the reason) and prints stage counts.  Nothing is sampled and nothing is
group-filtered: the previous three searches were all scope-limited and that
gap is exactly what this is closing.
"""
import os
import pickle
import sys
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

CACHE = os.path.join(HERE, "image-index.pkl")
ROWS = os.path.join(HERE, "rows.tsv")
FAILS = os.path.join(HERE, "fails.tsv")


def work(chunk):
    from imgdec import decode_entry
    from shape import analyse
    rows = []
    fails = []
    ok = 0
    npix = 0
    cur = None
    fh = None
    try:
        for (t, g, i, path, off, sz) in chunk:
            if path != cur:
                if fh:
                    fh.close()
                fh = open(path, "rb")
                cur = path
            fh.seek(off)
            raw = fh.read(sz)
            imgs, fl = decode_entry(t, raw)
            for r in fl:
                fails.append((t, g, i, path, r))
            for n, im in enumerate(imgs):
                ok += 1
                h, w = im.shape[:2]
                npix += h * w
                bh, th = analyse(im)
                bs = bh[0] if bh else None
                ts = th[0] if th else None
                if (bs and bs["score"] >= 0.05) or (ts and ts["score"] >= 0.10):
                    rows.append((t, g, i, path, n, w, h,
                                 bs["score"] if bs else 0.0,
                                 bs["bbox"] if bs else None,
                                 bs["glyph"] if bs else 0.0,
                                 ts["score"] if ts else 0.0,
                                 ts["bbox"] if ts else None,
                                 ts["glyph"] if ts else 0.0,
                                 ts["mask"] if ts else ""))
    finally:
        if fh:
            fh.close()
    return rows, fails, ok, npix


def main():
    with open(CACHE, "rb") as fh:
        d = pickle.load(fh)
    ents = d["entries"]
    ents.sort(key=lambda e: (e[3], e[4]))
    print("indexed image resources: %d" % len(ents))
    CH = 200
    chunks = [ents[k:k + CH] for k in range(0, len(ents), CH)]
    t0 = time.time()
    allrows = []
    allfails = []
    ok = 0
    npix = 0
    done = 0
    with ProcessPoolExecutor(max_workers=8) as ex:
        for (rows, fails, o, p) in ex.map(work, chunks):
            allrows += rows
            allfails += fails
            ok += o
            npix += p
            done += 1
            if done % 25 == 0:
                el = time.time() - t0
                print("  %5d/%d chunks  %7d decoded  %6d fails  %6d rows  "
                      "%.0fs (eta %.0fs)"
                      % (done, len(chunks), ok, len(allfails), len(allrows),
                         el, el / done * (len(chunks) - done)), flush=True)
    with open(ROWS, "w", encoding="utf-8") as fh:
        fh.write("T\tG\tI\tsub\tw\th\tblue\tbluebbox\tblueglyph\ttint\t"
                 "tintbbox\ttintglyph\ttintmask\tarchive\n")
        for r in allrows:
            (t, g, i, path, n, w, h, bs, bb, bg, ts, tb, tg, tm) = r
            fh.write("%08X\t%08X\t%08X\t%d\t%d\t%d\t%.4f\t%s\t%.3f\t%.4f\t%s\t"
                     "%.3f\t%s\t%s\n"
                     % (t, g, i, n, w, h, bs, bb, bg, ts, tb, tg, tm, path))
    fc = Counter(r[4].split(":")[0].split("-")[0] + "|" + r[4]
                 for r in allfails)
    with open(FAILS, "w", encoding="utf-8") as fh:
        fh.write("T\tG\tI\treason\tarchive\n")
        for (t, g, i, path, r) in allfails:
            fh.write("%08X\t%08X\t%08X\t%s\t%s\n" % (t, g, i, r, path))
    tot = ok + len(allfails)
    print()
    print("resources indexed        : %d" % len(ents))
    print("images DECODED           : %d  (%d total pixels)" % (ok, npix))
    print("decode FAILURES          : %d" % len(allfails))
    print("failure rate             : %.2f%%"
          % (100.0 * len(allfails) / max(tot, 1)))
    print("rows kept (score floor)  : %d" % len(allrows))
    print("elapsed                  : %.0fs" % (time.time() - t0))
    print()
    print("failure reasons:")
    for k, c in fc.most_common(20):
        print("   %-40s %d" % (k.split("|", 1)[1], c))


if __name__ == "__main__":
    main()
