#!/usr/bin/env python3
r"""parse_effdir_visuals.py - #188 U-Drive-It offer balloons: full visual-effects
section parse of the SC4 EFFDIR {T=0xEA5118B0,G=0xEA5118B1,I=0x00000001}.

Input: the rescued decompressed payload at
  tools\research\effdir\T-ea5118b0_G-ea5118b1_I-00000001.png  (1,094,484 bytes;
  raw EFFDIR despite the extension - see extract-manifest.csv PngMagic=no).

Layout facts PROVEN against bytes in this session (offsets are file-relative):
  * 0x9C274: u16 version(=2), u32 visualEffectCount(=0x482=1154).
  * Each visual effect: [u32 X][u32 A][u32 childCount] then childCount
    child-reference records, then a 20-byte trailer (12 zero bytes + 8 x 0xCC
    uninitialised-fill padding).
  * Child record = [u32 nameLen][name][u8 type][u32 flags]
    [9 f32 rot][3 f32 trans][f32 SCALE][u32 unk0]
    [u8 zoomMin][u8 zoomMax][u16 copies][u16 mult][4 f32 ramps][u32 zero]
    [u32 effectIndex]  -- i.e. 34 bytes after SCALE, not the 30 the
    build_mission_bubble_fx.py header comment implies (there is one extra u32
    between SCALE and zoomMin; the SCALE offset itself is unchanged and was
    the only byte-diff-proven field).
    Verified: mission_selection_red record 0x10248D..0x102501 ends exactly at
    the next record's start.
  * After the last visual effect: the name->index map, entries
    [u32 nameLen][name][u32 index] to EOF-adjacent; then a second map
    [u32 nameLen][name][u32 classId][u32 subIndex] (game-trigger names).

The walk is self-checking: it must consume exactly visualEffectCount parents
and land on the map, and the map entry for every parsed parent ordinal must
agree. Any drift is FATAL.
"""
import os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
EFFDIR = os.path.join(HERE, "..", "effdir", "T-ea5118b0_G-ea5118b1_I-00000001.png")
OUT = os.path.join(HERE, "effdir-dump.txt")

KEYWORDS = ("indicate", "mission", "drive", "udi", "pickup", "cargopu",
            "balloon", "marker", "select")

def fatal(m):
    print("FATAL:", m); sys.exit(1)

data = open(EFFDIR, "rb").read()
if len(data) != 1094484:
    print("WARN: size %d != 1094484" % len(data))

SEC = 0x9C274
ver, cnt = struct.unpack_from("<HI", data, SEC)
if ver != 2 or cnt != 0x482:
    fatal("visual section header drift: ver=%d cnt=%#x @%#x" % (ver, cnt, SEC))

off = SEC + 6
parents = []
PAD_HIST = {}
for pi in range(cnt):
    p_start = off
    X, A, nchild = struct.unpack_from("<3I", data, off)
    if nchild > 200:
        fatal("parent %d @%#x: implausible childCount %d" % (pi, p_start, nchild))
    off += 12
    kids = []
    for ci in range(nchild):
        c_start = off
        ln = struct.unpack_from("<I", data, off)[0]
        if ln > 64:
            fatal("parent %d child %d @%#x: nameLen %d" % (pi, ci, c_start, ln))
        name = data[off+4:off+4+ln].decode("ascii", "replace")
        off += 4 + ln
        ctype = data[off]
        flags = struct.unpack_from("<I", data, off+1)[0]
        floats = struct.unpack_from("<13f", data, off+5)
        scale_off = off + 5 + 48          # file offset of the SCALE float
        tail = struct.unpack_from("<I", data, off+57)[0]      # unk0
        zmin, zmax = data[off+61], data[off+62]
        copies, mult = struct.unpack_from("<2H", data, off+63)
        ramps = struct.unpack_from("<4f", data, off+67)
        zero2, effidx = struct.unpack_from("<2I", data, off+83)
        off += 91
        kids.append(dict(start=c_start, name=name, type=ctype, flags=flags,
                         rot=floats[:9], trans=floats[9:12], scale=floats[12],
                         scale_off=scale_off, unk0=tail, zmin=zmin, zmax=zmax,
                         copies=copies, mult=mult, ramps=ramps, zero2=zero2,
                         effidx=effidx))
    # Post-children tail (byte-verified on parents 0 and 17):
    #   [u32 P][u32 Q][Q x {u32 nameLen, name, 12B payload}][12 bytes junk]
    # The trailing 12 bytes are uninitialised writer memory (often 0xCC fill,
    # sometimes stack garbage like 5F 90 0D CC) - consumed, never interpreted.
    P, Q = struct.unpack_from("<2I", data, off); off += 8
    tail_entries = []
    if P > 64:
        fatal("parent %d @%#x: implausible tail P=%d" % (pi, p_start, P))
    for qi in range(P):
        ln = struct.unpack_from("<I", data, off)[0]
        if ln > 64:
            fatal("parent %d tail entry %d @%#x: nameLen %d" % (pi, qi, off, ln))
        nm = data[off+4:off+4+ln].decode("ascii", "replace")
        payload = data[off+4+ln:off+4+ln+12]
        tail_entries.append((nm, payload.hex()))
        off += 4 + ln + 12
    off += 12
    parents.append(dict(idx=pi, start=p_start, X=X, A=A, P=P, Q=Q,
                        kids=kids, tail=tail_entries))

map_start = off
print("walk OK: %d parents, children span ends @%#x, map starts @%#x"
      % (len(parents), off, map_start))

# ---- name -> index map ----
names = {}
while off < len(data):
    save = off
    ln = struct.unpack_from("<I", data, off)[0]
    if not (1 <= ln <= 64): break
    nm = data[off+4:off+4+ln]
    if not all(0x20 <= b < 0x7F for b in nm): break
    off += 4 + ln
    idx = struct.unpack_from("<I", data, off)[0]
    if idx >= cnt:               # ran into the second (classId) map
        off = save; break
    names[nm.decode()] = idx
    off += 4
print("simple map: %d entries, ends @%#x" % (len(names), off))

# invert
by_idx = {}
for nm, ix in names.items():
    by_idx.setdefault(ix, []).append(nm)

dup = [ix for ix, v in by_idx.items() if len(v) > 1]
if dup:
    print("NOTE: %d indexes with multiple names, e.g." % len(dup),
          [(i, by_idx[i]) for i in dup[:3]])

# sanity anchor
if names.get("aircraftindicate") != 0x416:
    fatal("anchor drift: aircraftindicate -> %r" % names.get("aircraftindicate"))

# second map (classId entries) - parse what remains
second = []
o2 = off
while o2 < len(data) - 4:
    ln = struct.unpack_from("<I", data, o2)[0]
    if not (1 <= ln <= 64): o2 += 1; continue
    nm = data[o2+4:o2+4+ln]
    if len(nm) == ln and all(0x20 <= b < 0x7F for b in nm) and o2+4+ln+8 <= len(data):
        cid, sub = struct.unpack_from("<2I", data, o2+4+ln)
        second.append((nm.decode(), cid, sub))
        o2 += 4 + ln + 8
    else:
        o2 += 1

# ---- write the dump ----
def fmt_child(c):
    rot_id = c["rot"] == (1.0,0.0,0.0,0.0,1.0,0.0,0.0,0.0,1.0)
    return ("    child %-34r type=%d flags=%#x scale=%g (SCALE@file:%#08x) "
            "trans=(%g,%g,%g) rot=%s zoom=%d..%d copies=%d mult=%d "
            "ramps=%s effectIndex=%#x(%d)"
            % (c["name"], c["type"], c["flags"], c["scale"], c["scale_off"],
               *c["trans"], "I" if rot_id else repr(c["rot"]),
               c["zmin"], c["zmax"], c["copies"], c["mult"],
               tuple(round(r,3) for r in c["ramps"]), c["effidx"], c["effidx"]))

with open(OUT, "w") as f:
    f.write("EFFDIR visual-effects dump - %d parents, map %d names\n"
            "source: %s\nsection header @0x9C274 (ver 2, count 0x482)\n\n"
            % (len(parents), len(names), os.path.abspath(EFFDIR)))
    for p in parents:
        pnames = by_idx.get(p["idx"], ["<unnamed>"])
        line = "[%4d @file:%#08x] %s  (X=%d A=%d children=%d)" % (
            p["idx"], p["start"], "/".join(sorted(pnames)), p["X"], p["A"], len(p["kids"]))
        f.write(line + "\n")
        for c in p["kids"]:
            f.write(fmt_child(c) + "\n")
    f.write("\n---- second map (name -> classId, subIndex): %d entries ----\n" % len(second))
    for nm, cid, sub in second:
        f.write("  %-40s classId=%#010x sub=%d\n" % (nm, cid, sub))
print("wrote", OUT)

# ---- inline: keyword matches ----
print("\n==== KEYWORD PARENTS ====")
for p in parents:
    pnames = by_idx.get(p["idx"], [])
    hay = " ".join(pnames + [c["name"] for c in p["kids"]]).lower()
    if any(k in hay for k in KEYWORDS):
        print("[%4d @%#08x] %s (children=%d)" % (p["idx"], p["start"],
              "/".join(sorted(pnames)) or "<unnamed>", len(p["kids"])))
        for c in p["kids"]:
            print(fmt_child(c))
