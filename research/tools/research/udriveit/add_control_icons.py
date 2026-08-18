#!/usr/bin/env python3
r"""Add a POSITIVE CONTROL to the red tracer. Read-only on the game.

    python add_control_icons.py

WHY
---
Tracer v1 reddened 93 signpost sheets and NOTHING on screen changed. That
is worthless as evidence: if none of those 93 is drawn in this city, the
test could not have produced a red pixel no matter what the truth is. A null
without a positive control is not a null (this project's own standing law,
and I broke it designing the test).

So this adds icons the ARTFETCH capture PROVED are fetched live during the
session the user just played (SC4UIScale-2026-08-17-ARTFETCH3.log):

    ret=0x007ED23B  {G=0x46A006B0, I=0x14015549}
    ret=0x007E8B3A  {G=0x46A006B0, I=0x14315E61}
    ret=0x007E8B3A  {G=0x46A006B0, I=0x14315E62}
    ret=0x007B5195  {G=0x46A006B0, I=0x14416327}
    ret=0x0076EB13  {G=0x46A006B0, I=0x13F1525C}

Now the test discriminates:
  controls RED, balloons NOT  -> the override route works and the balloons
                                 are NOT drawn from these PNG groups. A real
                                 null. Pivot to the S3D/FSH world-model
                                 pipeline (the Zot family's shape).
  nothing RED at all          -> the dat is not winning the load order at
                                 all, and every art conclusion today
                                 (including v3.0.23's) needs re-examining.
"""
import glob
import os
import struct
import subprocess
import sys
import tempfile

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
GAME = r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe"
PACKER = os.path.join(PROJ, "tools", "dbpf", "DbpfPack.exe")
ART = os.path.join(HERE, "signpost-art")
OUT = os.path.join(HERE, "build", "SC4UIScale_RedTracer.dat")

PNG_T = 0x856DDBAC
SIGNPOST_G = 0xAB7E5421
ICON_G = 0x46A006B0
CONTROLS = [0x14015549, 0x14315E61, 0x14315E62, 0x14416327, 0x13F1525C]
KEY = (255, 0, 255)


def fatal(m):
    print("FATAL: " + m)
    sys.exit(1)


def index_entries(path):
    with open(path, "rb") as fh:
        head = fh.read(96)
        if head[:4] != b"DBPF":
            return
        cnt = struct.unpack_from("<I", head, 36)[0]
        off = struct.unpack_from("<I", head, 40)[0]
        fh.seek(off)
        raw = fh.read(cnt * 20)
    for k in range(cnt):
        yield struct.unpack_from("<IIIII", raw, k * 20)


def redden_bytes(blob, dst):
    import io
    im = Image.open(io.BytesIO(blob)).convert("RGBA")
    px = im.load()
    w, h = im.size
    n = 0
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a == 0 or (r, g, b) == KEY:
                continue
            px[x, y] = (255, 0, 0, a)
            n += 1
    im.save(dst, "PNG")
    return (w, h), n


def main():
    stage = tempfile.mkdtemp(prefix="tracer2_")
    made = 0

    # (1) the 93 signpost sheets, as before
    for n in sorted(x for x in os.listdir(ART) if x.lower().endswith(".png")):
        inst = int(os.path.splitext(n)[0].split("-")[-1], 16)
        out = "T-0x%08X_G-0x%08X_I-0x%08X.png" % (PNG_T, SIGNPOST_G, inst)
        with open(os.path.join(ART, n), "rb") as fh:
            blob = fh.read()
        redden_bytes(blob, os.path.join(stage, out))
        made += 1

    # (2) THE POSITIVE CONTROLS - pulled fresh from the archives
    want = set(CONTROLS)
    got = {}
    dats = sorted(glob.glob(os.path.join(GAME, "**", "*.dat"), recursive=True)
                  + glob.glob(os.path.join(GAME, "**", "*.DAT"), recursive=True))
    for path in dats:
        for (t, g, i, off, size) in index_entries(path):
            if g == ICON_G and i in want and i not in got:
                with open(path, "rb") as fh:
                    fh.seek(off)
                    blob = fh.read(size)
                if blob[:8] != b"\x89PNG\r\n\x1a\n":
                    print("  control 0x%08X in %s is not raw PNG - skipped"
                          % (i, os.path.basename(path)))
                    continue
                out = "T-0x%08X_G-0x%08X_I-0x%08X.png" % (t, ICON_G, i)
                size2, npx = redden_bytes(blob, os.path.join(stage, out))
                got[i] = (os.path.basename(path), size2, npx, t)
                made += 1

    print("POSITIVE CONTROLS:")
    for i in CONTROLS:
        if i in got:
            src, sz, npx, t = got[i]
            print("  0x%08X  %-16s T=0x%08X %sx%s  %d px reddened"
                  % (i, src, t, sz[0], sz[1], npx))
        else:
            print("  0x%08X  NOT FOUND as raw PNG - not a usable control" % i)
    if not got:
        fatal("no positive control could be built - the test would be "
              "vacuous again; do not ship it")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    if os.path.exists(OUT):
        os.remove(OUT)
    r = subprocess.run([PACKER, stage, OUT], capture_output=True, text=True)
    if r.returncode != 0:
        fatal("DbpfPack failed: %s %s" % (r.stdout, r.stderr))
    print("\nOK: %d entries (%d signpost + %d controls) -> %s (%d bytes)"
          % (made, made - len(got), len(got), OUT, os.path.getsize(OUT)))


if __name__ == "__main__":
    main()
