#!/usr/bin/env python3
r"""POSITIVE CONTROL for the DECODER: pull a handful of known-good textures
straight out of the index and render them into one strip.

If these come out as noise, every "no candidate" verdict downstream is
meaningless - a decoder that silently produces garbage looks exactly like a
corpus with no icon in it.
"""
import os
import pickle
import sys
from collections import Counter

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from imgdec import decode_entry, payload           # noqa: E402

d = pickle.load(open(os.path.join(HERE, "image-index.pkl"), "rb"))
ents = d["entries"]

# code histogram over a sample, so "unhandled" cannot hide
codes = Counter()
import struct
for (t, g, i, path, off, sz) in ents[::37]:
    if t != 0x7AB50E44:
        continue
    with open(path, "rb") as fh:
        fh.seek(off)
        raw = fh.read(sz)
    try:
        data = payload(raw)
    except Exception:
        continue
    if data[:4] != b"SHPI":
        codes["not-SHPI"] += 1
        continue
    n = struct.unpack_from("<I", data, 8)[0]
    for e in range(min(n, 64)):
        try:
            o = struct.unpack_from("<I", data, 20 + 8 * e)[0]
            codes["0x%02X" % (data[o] & 0x7F)] += 1
        except Exception:
            codes["bad-dir"] += 1
print("FSH pixel codes over a 1-in-37 sample of FSH entries:")
for k, c in codes.most_common():
    print("   %-10s %d" % (k, c))

WANT = [0x1EE50000]                                # proven marker texture
picks = []
for (t, g, i, path, off, sz) in ents:
    if t == 0x7AB50E44 and i in WANT:
        picks.append((t, g, i, path, off, sz))
        break
# plus the first FSH of each of the five biggest archives
seen = set()
for e in ents:
    if e[0] == 0x7AB50E44 and e[3] not in seen:
        seen.add(e[3])
        picks.append(e)
    if len(picks) > 9:
        break

tiles = []
for (t, g, i, path, off, sz) in picks:
    with open(path, "rb") as fh:
        fh.seek(off)
        raw = fh.read(sz)
    imgs, f = decode_entry(t, raw)
    print("%08X %08X %s -> %d images %s"
          % (g, i, os.path.basename(path), len(imgs), f))
    if imgs:
        im = Image.fromarray(imgs[0], "RGBA")
        k = max(1, 128 // max(im.size))
        tiles.append(im.resize((im.width * k, im.height * k), Image.NEAREST))
if tiles:
    W = sum(t.width for t in tiles) + 8 * len(tiles)
    H = max(t.height for t in tiles) + 8
    strip = Image.new("RGB", (W, H), (20, 20, 26))
    x = 4
    for t in tiles:
        strip.paste(t, (x, 4), t)
        x += t.width + 8
    strip.save(os.path.join(HERE, "decoder-control.png"))
    print("wrote decoder-control.png")
