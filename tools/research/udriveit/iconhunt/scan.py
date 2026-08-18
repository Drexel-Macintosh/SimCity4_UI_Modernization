#!/usr/bin/env python3
r"""scan.py - decode EVERY FSH + PNG resource in every discovered archive and
score every opaque blob for disc-ness, colour-blind.

Emits scan.tsv (one row per surviving component) and scan-stats.txt (per-stage
counts).  Colour is measured but NEVER used to rank here -- it is recorded so the
report can rank 'actually blue' and 'white/greyscale, would read blue once
tinted' separately.
"""
import io, os, sys, math, struct, traceback
import multiprocessing as mp
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
UD = os.path.dirname(HERE)
sys.path.insert(0, HERE); sys.path.insert(0, UD)
sys.path.insert(0, os.path.join(UD, "..", "..", "uimap", "emu"))

FSH, PNG = 0x7AB50E44, 0x856DDBAC
MAXPX = 1024 * 1024


def analyse(img, tgi, arch, eidx, tag):
    import shapelib
    from qfs_ab import qfs  # noqa
    rows, stat = [], {}
    a = np.asarray(img.convert("RGBA"))
    h, w = a.shape[:2]
    if w * h > MAXPX:
        return rows, {"skip_big": 1}
    al = a[:, :, 3]
    masks = []
    if al.min() < 200:
        masks.append(("A", al > 128))
    # colour-key / opaque fallback: background = modal border colour
    if al.min() >= 200:
        rgb = a[:, :, :3].astype(np.int16)
        border = np.concatenate([rgb[0], rgb[-1], rgb[:, 0], rgb[:, -1]])
        vals, cnt = np.unique(border.reshape(-1, 3), axis=0, return_counts=True)
        bg = vals[cnt.argmax()]
        if cnt.max() >= 0.5 * len(border):
            d = np.abs(rgb - bg).sum(2)
            masks.append(("B", d > 60))
    stat["images"] = 1
    stat["masks"] = len(masks)
    for mtag, m in masks:
        if m.sum() < 40 or m.all():
            continue
        try:
            comps = shapelib.components(m)
        except Exception:
            stat["cc_fail"] = stat.get("cc_fail", 0) + 1
            continue
        stat["comps"] = stat.get("comps", 0) + len(comps)
        for c in comps:
            sc = shapelib.score(c)
            if sc < 0.60:
                continue
            x0, y0, x1, y1 = c["bbox"]
            sub = a[y0:y1, x0:x1]
            sm = m[y0:y1, x0:x1]
            bh, bw = sm.shape
            yy, xx = np.mgrid[0:bh, 0:bw]
            cy, cx = (bh - 1) / 2.0, (bw - 1) / 2.0
            r = np.sqrt(((yy - cy) / (bh / 2.0)) ** 2 + ((xx - cx) / (bw / 2.0)) ** 2)
            rgbf = sub[:, :, :3].astype(np.float32)
            body = sm & (r < 0.60)
            rim = sm & (r >= 0.75) & (r <= 1.0)
            def mc(mm):
                return rgbf[mm].mean(0) if mm.sum() >= 4 else np.array([-1.0, -1, -1])
            bR, bG, bB = mc(body); rR, rG, rB = mc(rim)
            # --- glyph: transparent hole, or luminance-contrasting blob inside
            hole = float(1.0 - c["solidity"])
            inner = sm & (r < 0.72)
            gfrac = 0.0; gblob = 0.0
            if inner.sum() >= 20:
                lum = rgbf[:, :, 0]*0.299 + rgbf[:, :, 1]*0.587 + rgbf[:, :, 2]*0.114
                med = float(np.median(lum[inner]))
                gm = inner & (np.abs(lum - med) > 55)
                gfrac = float(gm.sum()) / float(inner.sum())
                if gm.sum() >= 8:
                    lb, n = shapelib.label(gm)
                    if n:
                        cb = np.bincount(lb.ravel()); cb[0] = 0
                        gblob = float(cb.max()) / float(inner.sum())
            grey = float(np.abs(rgbf[sm] - rgbf[sm].mean(1, keepdims=True)).mean()) if sm.sum() else -1
            rows.append([
                "%08X" % tgi[0], "%08X" % tgi[1], "%08X" % tgi[2], arch, eidx, mtag,
                w, h, x0, y0, bw, bh, c["area"],
                round(c["circ"], 4), round(c["aspect"], 4), round(c["diskfill"], 4),
                round(c["rcv"], 4), round(c["solidity"], 4), round(sc, 4),
                round(hole, 4), round(gfrac, 4), round(gblob, 4), round(grey, 2),
                round(bR, 1), round(bG, 1), round(bB, 1), round(rR, 1), round(rG, 1), round(rB, 1),
            ])
    return rows, stat


def do_archive(path):
    import shapelib, fshlib
    from qfs_ab import qfs
    rows = []
    st = dict(entries=0, decoded=0, decode_fail=0, imgs=0, skip_big=0, rows=0, comps=0)
    try:
        f = open(path, "rb")
    except Exception:
        return rows, st, path
    with f:
        hdr = f.read(96)
        if hdr[:4] != b"DBPF":
            return rows, st, path
        cnt = struct.unpack_from("<I", hdr, 36)[0]
        io_ = struct.unpack_from("<I", hdr, 40)[0]
        isz = struct.unpack_from("<I", hdr, 44)[0]
        if not cnt:
            return rows, st, path
        f.seek(io_); idx = f.read(isz)
        per = isz // cnt
        for k in range(cnt):
            try:
                t, g, i, off, size = struct.unpack_from("<5I", idx, k * per)
            except Exception:
                break
            if t not in (FSH, PNG):
                continue
            st["entries"] += 1
            try:
                f.seek(off); raw = f.read(size)
                if t == PNG:
                    d = raw
                    if d[:4] != b"\x89PNG":
                        dd = qfs(raw)
                        d = dd if dd else raw
                    imgs = [("png", Image.open(io.BytesIO(d)))]
                else:
                    d = qfs(raw) or raw
                    imgs = fshlib.decode_fsh(d)
                st["decoded"] += 1
            except Exception:
                st["decode_fail"] += 1
                continue
            for eidx, (tag, im) in enumerate(imgs):
                st["imgs"] += 1
                try:
                    r, s = analyse(im, (t, g, i), os.path.basename(path), eidx, tag)
                except Exception:
                    continue
                st["skip_big"] += s.get("skip_big", 0)
                st["comps"] += s.get("comps", 0)
                rows.extend(r)
        st["rows"] = len(rows)
    return rows, st, path


HDR = ("type group inst archive entry mask imgw imgh bx by bw bh area circ aspect "
       "diskfill rcv solidity score hole gfrac gblob grey bodyR bodyG bodyB rimR rimG rimB").split()


def main():
    import index_all
    g = index_all.index()
    files = sorted(set(g["files"]))
    print("archives discovered: %d" % len(files))
    tot = dict(entries=0, decoded=0, decode_fail=0, imgs=0, skip_big=0, comps=0)
    out = open(os.path.join(HERE, "scan.tsv"), "w", encoding="utf-8")
    out.write("\t".join(HDR) + "\n")
    nrows = 0
    with mp.Pool(8) as pool:
        for n, (rows, st, path) in enumerate(pool.imap_unordered(do_archive, files), 1):
            for k in tot:
                tot[k] += st.get(k, 0)
            for r in rows:
                out.write("\t".join(str(x) for x in r) + "\n")
            nrows += len(rows)
            if n % 25 == 0 or n == len(files):
                print("  %4d/%d archives | entries %d decoded %d fail %d imgs %d rows %d"
                      % (n, len(files), tot["entries"], tot["decoded"],
                         tot["decode_fail"], tot["imgs"], nrows), flush=True)
    out.close()
    with open(os.path.join(HERE, "scan-stats.txt"), "w") as fh:
        for k, v in tot.items():
            fh.write("%s\t%d\n" % (k, v))
        fh.write("rows\t%d\n" % nrows)
    print("STATS", tot, "rows", nrows)


if __name__ == "__main__":
    main()
