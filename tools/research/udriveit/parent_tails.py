#!/usr/bin/env python3
r"""parent_tails.py - #188 lane: the effdir-dump.txt writer throws away each
parent's TAIL records (the [u32 P][u32 Q][P x {nameLen,name,12B}] block).
Every live-census effect (cargopu1/2, motorcycle, rotor, heliblade,
aircraftindicate, ...) has childCount=0, so ALL of its content is in that tail.
Re-parse the raw EFFDIR and dump the tails with the 12-byte payloads decoded
three ways (3xu32 / 3xf32 / u32+u8s) so the sub-table index is visible.

Read-only. Writes parent-tails.txt.
"""
import os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
EFFDIR = os.path.join(HERE, "..", "effdir", "T-ea5118b0_G-ea5118b1_I-00000001.png")
data = open(EFFDIR, "rb").read()

SEC = 0x9C274
ver, cnt = struct.unpack_from("<HI", data, SEC)
assert ver == 2 and cnt == 0x482, (ver, cnt)

off = SEC + 6
parents = []
for pi in range(cnt):
    p_start = off
    X, A, nchild = struct.unpack_from("<3I", data, off)
    off += 12
    kids = []
    for ci in range(nchild):
        c_start = off
        ln = struct.unpack_from("<I", data, off)[0]
        name = data[off+4:off+4+ln].decode("ascii", "replace")
        off += 4 + ln
        ctype = data[off]
        flags = struct.unpack_from("<I", data, off+1)[0]
        floats = struct.unpack_from("<13f", data, off+5)
        scale_off = off + 5 + 48
        zmin, zmax = data[off+61], data[off+62]
        effidx = struct.unpack_from("<I", data, off+87)[0]
        off += 91
        kids.append(dict(start=c_start, name=name, type=ctype, scale=floats[12],
                         scale_off=scale_off, zmin=zmin, zmax=zmax, effidx=effidx))
    P, Q = struct.unpack_from("<2I", data, off)
    tail_off = off
    off += 8
    tails = []
    for qi in range(P):
        e_off = off
        ln = struct.unpack_from("<I", data, off)[0]
        nm = data[off+4:off+4+ln].decode("ascii", "replace")
        payload = data[off+4+ln:off+4+ln+12]
        tails.append((e_off, nm, payload))
        off += 4 + ln + 12
    off += 12
    parents.append(dict(idx=pi, start=p_start, X=X, A=A, P=P, Q=Q, kids=kids,
                        tail_off=tail_off, tails=tails, end=off))

# name map
names = {}
o = off
while o < len(data):
    save = o
    ln = struct.unpack_from("<I", data, o)[0]
    if not (1 <= ln <= 64): break
    nm = data[o+4:o+4+ln]
    if not all(0x20 <= b < 0x7F for b in nm): break
    o += 4 + ln
    idx = struct.unpack_from("<I", data, o)[0]
    if idx >= cnt:
        o = save; break
    names[nm.decode()] = idx
    o += 4
by_idx = {}
for nm, ix in names.items():
    by_idx.setdefault(ix, []).append(nm)
assert names.get("aircraftindicate") == 0x416

OUT = open(os.path.join(HERE, "parent-tails.txt"), "w", encoding="utf-8")
def W(*a):
    s = " ".join(str(x) for x in a); OUT.write(s+"\n"); print(s)

def show(idx, depth=0, seen=None):
    if seen is None: seen = set()
    if idx in seen:
        W("  "*depth + "  <cycle to parent %d>" % idx); return
    seen = seen | {idx}
    p = parents[idx]
    pad = "  "*depth
    W("%s[%4d @%#08x] %-32s X=%d A=%d children=%d P=%d Q=%d (tail@%#08x, rec ends %#08x)"
      % (pad, idx, p["start"], "/".join(sorted(by_idx.get(idx, ["<unnamed>"]))),
         p["X"], p["A"], len(p["kids"]), p["P"], p["Q"], p["tail_off"], p["end"]))
    for c in p["kids"]:
        W("%s   child %-34r type=%d scale=%g SCALE@%#08x zoom=%d..%d effidx=%d"
          % (pad, c["name"], c["type"], c["scale"], c["scale_off"], c["zmin"], c["zmax"], c["effidx"]))
    for e_off, nm, pl in p["tails"]:
        u = struct.unpack("<3I", pl) if len(pl) == 12 else ()
        fl = struct.unpack("<3f", pl) if len(pl) == 12 else ()
        W("%s   TAIL %-34r @%#08x raw=%s  u32=%s  f32=%s"
          % (pad, nm, e_off, pl.hex(), u, tuple(round(x,4) for x in fl)))
        tix = names.get(nm)
        if tix is not None and depth < 4:
            show(tix, depth+2, seen)
        elif tix is None:
            W("%s     -> %r NOT a visual-effect name" % (pad, nm))

CENSUS = ["cargopu2","motorcycle","cargopu1","rotor","helibladestill","heliblade",
          "helipad","copter_spotlight","heli_closetoground","aircraftindicate"]
W("="*78); W("CENSUS PARENTS - FULL RECORDS (children + tails)"); W("="*78)
for nm in CENSUS:
    W("\n---- %s ----" % nm)
    ix = names.get(nm)
    if ix is None:
        W("   %s: NOT PRESENT in the effdir name map (%d names) -> live lookup ok=0" % (nm, len(names)))
        continue
    show(ix)

# X histogram
import collections
W("\n" + "="*78); W("X-field histogram over all 1154 parents"); W("="*78)
hx = collections.Counter(p["X"] for p in parents)
for x, n in sorted(hx.items()):
    ex = [ "/".join(sorted(by_idx.get(p["idx"], ["?"]))) for p in parents if p["X"] == x ][:6]
    W("  X=%-4d x%-5d e.g. %s" % (x, n, ex))
W("\nP-field histogram:")
hp = collections.Counter(p["P"] for p in parents)
for x, n in sorted(hp.items()): W("  P=%-4d x%d" % (x, n))
W("\nTAIL-name histogram (all parents):")
ht = collections.Counter(nm for p in parents for _, nm, _ in p["tails"])
for nm, n in ht.most_common(60): W("  %-34s x%d" % (nm, n))
OUT.close()
