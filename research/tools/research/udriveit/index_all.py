#!/usr/bin/env python3
r"""ONE-PASS global DBPF index for the whole install + Plugins, cached.

WHY: the existing helpers (s3d_textures.get_s3d, extract_fsh.find_entry) rescan
EVERY archive for EVERY lookup.  That is fine for five ids and hopeless for the
2,392-exemplar marker family -- resolving exemplar -> S3D -> MATS -> FSH for the
whole group is ~7,000 lookups.  This builds {(type,group,inst): (path,off,size)}
plus {(type,inst): [...]} once and pickles it.

⛔ The archive list is DISCOVERED recursively (see census_markers.discover_dbpf),
never hard-coded -- the install ships NINE archives and a written-down list of
seven has already failed silently once (#140, Intro.dat).

POSITIVE CONTROL: the index MUST contain
    {0x6534284A, 0xC977C536, 0x29F10000}  UI8x1x3_ConnectArrow_29F1
    {0x5AD0E817, 0xBADB57F1, 0x29F10400}  its zoom-4 model
    {0x7AB50E44, *,          0x1EE50000}  the texture that model binds
If any is missing the index is broken and every "not found" is meaningless.
"""
import os
import pickle
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", ".."))
from census_markers import dbpf_index, discover_dbpf            # noqa: E402
from sc4paths import plugins_dir, game_dir                      # noqa: E402

CACHE = os.path.join(
    os.environ.get("TEMP", HERE), "sc4-dbpf-global-index.pkl")

T_EXEMPLAR = 0x6534284A
G_MARKER = 0xC977C536
T_S3D = 0x5AD0E817
G_S3D = 0xBADB57F1
T_FSH = 0x7AB50E44

CONTROLS = [
    (T_EXEMPLAR, G_MARKER, 0x29F10000),
    (T_S3D, G_S3D, 0x29F10400),
]


def build(verbose=True):
    roots = [game_dir()]
    p = plugins_dir(require=False)
    if p and os.path.isdir(p):
        roots.append(p)
    by_tgi = {}
    by_ti = {}
    files = []
    for root in roots:
        for path in discover_dbpf(root):
            idx = dbpf_index(path)
            if not idx:
                continue
            files.append(path)
            for (t, g, i, off, sz) in idx:
                by_tgi.setdefault((t, g, i), (path, off, sz))
                by_ti.setdefault((t, i), []).append((g, path, off, sz))
    if verbose:
        print("indexed %d DBPF files, %d distinct TGIs" % (len(files), len(by_tgi)))
    return {"by_tgi": by_tgi, "by_ti": by_ti, "files": files}


_G = None


def index(refresh=False):
    global _G
    if _G is not None:
        return _G
    if not refresh and os.path.exists(CACHE):
        try:
            with open(CACHE, "rb") as fh:
                _G = pickle.load(fh)
            return _G
        except Exception:
            pass
    _G = build()
    try:
        with open(CACHE, "wb") as fh:
            pickle.dump(_G, fh, 2)
    except Exception:
        pass
    return _G


def check_controls():
    g = index()
    ok = True
    for tgi in CONTROLS:
        hit = g["by_tgi"].get(tgi)
        print("CONTROL {0x%08X,0x%08X,0x%08X}: %s"
              % (tgi + (os.path.basename(hit[0]) if hit else "*** MISSING ***",)))
        ok = ok and hit is not None
    fsh = g["by_ti"].get((T_FSH, 0x1EE50000))
    print("CONTROL FSH 0x1EE50000: %s"
          % (", ".join("G=0x%08X %s" % (a, os.path.basename(b))
                       for a, b, _c, _d in fsh) if fsh else "*** MISSING ***"))
    return ok and bool(fsh)


if __name__ == "__main__":
    index(refresh="--refresh" in sys.argv)
    g = _G
    print("files: %d" % len(g["files"]))
    print("TGIs : %d" % len(g["by_tgi"]))
    n_ex = sum(1 for (t, gg, _i) in g["by_tgi"] if t == T_EXEMPLAR and gg == G_MARKER)
    n_s3d = sum(1 for (t, gg, _i) in g["by_tgi"] if t == T_S3D)
    n_fsh = sum(1 for (t, _g, _i) in g["by_tgi"] if t == T_FSH)
    print("exemplars in G=0xC977C536: %d" % n_ex)
    print("S3D resources            : %d" % n_s3d)
    print("FSH resources            : %d" % n_fsh)
    print()
    check_controls()
