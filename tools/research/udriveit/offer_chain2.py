#!/usr/bin/env python3
r"""offer_chain2.py - #188 lane, corrected. Re-parses the raw EFFDIR (the
effdir-dump.txt child lines are padded and were mis-regexed) and:
  1. lists every parent matching the offer/mission/advice keyword set
  2. follows the live-census effects' type-2 chains to their type-0/type-1 leaves
  3. reports f0 + file offset for every type-1 leaf on the offer chain
Read-only. Writes offer-chain2.txt.
"""
import os, re, struct, sys, collections

HERE = os.path.dirname(os.path.abspath(__file__))
EFFDIR = os.path.join(HERE, "..", "effdir", "T-ea5118b0_G-ea5118b1_I-00000001.png")
data = open(EFFDIR, "rb").read()

SEC = 0x9C274
ver, cnt = struct.unpack_from("<HI", data, SEC)
assert ver == 2 and cnt == 0x482

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
        f = struct.unpack_from("<13f", data, off+5)
        scale_off = off + 5 + 48
        zmin, zmax = data[off+61], data[off+62]
        copies, mult = struct.unpack_from("<2H", data, off+63)
        effidx = struct.unpack_from("<I", data, off+87)[0]
        off += 91
        kids.append(dict(start=c_start, name=name, type=ctype, flags=flags,
                         trans=f[9:12], scale=f[12], scale_off=scale_off,
                         zmin=zmin, zmax=zmax, copies=copies, effidx=effidx))
    P, Q = struct.unpack_from("<2I", data, off); off += 8
    tails = []
    for qi in range(P):
        ln = struct.unpack_from("<I", data, off)[0]
        nm = data[off+4:off+4+ln].decode("ascii", "replace")
        tails.append(nm)
        off += 4 + ln + 12
    off += 12
    parents.append(dict(idx=pi, start=p_start, X=X, A=A, kids=kids, tails=tails))

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
    if idx >= cnt: o = save; break
    names[nm.decode()] = idx; o += 4
assert names.get("aircraftindicate") == 0x416
by_idx = {}
for nm, ix in names.items(): by_idx.setdefault(ix, []).append(nm)
lower = {k.lower(): v for k, v in names.items()}

# ---- type-1 table ----
T1_RE = re.compile(r"^\s*(\d+) @file:(0x[0-9a-f]+) rid=([0-9A-F]{8}) flags=(\S+) b8=(\d+) b9=(\d+) f0=(\S+)\s+cols=(\[.*?\]) tail=\((.*?)\)")
t1 = {}
for line in open(os.path.join(HERE, "type1-table.txt"), encoding="utf-8"):
    m = T1_RE.match(line)
    if m:
        t1[int(m.group(1))] = dict(off=int(m.group(2),16), rid=m.group(3),
                                   flags=m.group(4), f0=m.group(7), cols=m.group(8))

OUT = open(os.path.join(HERE, "offer-chain2.txt"), "w", encoding="utf-8")
def W(*a):
    s=" ".join(str(x) for x in a); OUT.write(s+"\n"); print(s)

TYPENAME = {0:"t0 PARTICLE-SYS", 1:"t1 DECAL/SPRITE", 2:"t2 SPAWN-EFFECT-BY-NAME",
            3:"t3", 4:"t4 SOUND", 5:"t5", 6:"t6", 7:"t7", 8:"t8 (idx-only)", 9:"t9", 10:"t10"}

leaves = collections.OrderedDict()   # (t1 index) -> set of chain paths
def walk(nm, depth=0, seen=frozenset(), root=""):
    pad = "  "*depth
    ix = lower.get(nm.lower())
    if ix is None:
        W("%s%-34r -> NOT IN EFFDIR (live lookup would return ok=0)" % (pad, nm)); return
    if ix in seen:
        W("%s%-34r -> <cycle, parent %d>" % (pad, nm, ix)); return
    seen = seen | {ix}
    p = parents[ix]
    W("%s%-34r parent %d @%#08x X=%d A=%d children=%d"
      % (pad, nm, ix, p["start"], p["X"], p["A"], len(p["kids"])))
    for c in p["kids"]:
        extra = ""
        if c["type"] == 1:
            e = t1.get(c["effidx"])
            if e:
                extra = ("   <<T1 LEAF #%d @file:%#08x  f0=%s  rid=%s  cols=%s>>"
                         % (c["effidx"], e["off"], e["f0"], e["rid"], e["cols"]))
                leaves.setdefault(c["effidx"], set()).add(root or nm)
            else:
                extra = "   <<T1 #%d NOT IN 310-ENTRY TABLE>>" % c["effidx"]
        W("%s  - %-32r %-22s scale=%g trans=%s zoom=%d..%d copies=%d effidx=%d%s"
          % (pad, c["name"], TYPENAME.get(c["type"], "t%d"%c["type"]), c["scale"],
             tuple(round(x,3) for x in c["trans"]), c["zmin"], c["zmax"],
             c["copies"], c["effidx"], extra))
        if c["type"] == 2 and c["name"] and depth < 6:
            walk(c["name"], depth+2, seen, root or nm)
    for t in p["tails"]:
        W("%s  ~ TAIL-effect %r" % (pad, t))

# ================= 1. keyword parents =================
KW = ["indicate","advice","offer","avail","opportun","reward","task","job",
      "deliver","pickup","pu1","pu2","tour","race","scenario"]
W("="*80); W("1. PARENTS MATCHING THE OFFER/MISSION/ADVICE KEYWORD SET"); W("="*80)
for k in KW:
    hit = sorted((ix, n) for n, ix in names.items() if k in n.lower())
    W("\n--- %-10r : %d parent(s) ---" % (k, len(hit)))
    for ix, n in hit:
        p = parents[ix]
        W("   [%4d @%#08x] %-36s X=%-4d children=%d types=%s"
          % (ix, p["start"], n, p["X"], len(p["kids"]),
             sorted(set(c["type"] for c in p["kids"]))))

W("\n" + "="*80)
W("1b. EXTRA NAME SWEEP - mission/udi/drive/bubble/balloon/marker/select/sign/icon/arrow")
W("="*80)
for k in ["mission","udi","udrive","drive","bubble","balloon","marker","select",
          "sign","icon","arrow","bounce","float","hover","query","prize","goal"]:
    hit = sorted((ix, n) for n, ix in names.items() if k in n.lower())
    if hit:
        W("\n--- %-10r : %d ---" % (k, len(hit)))
        for ix, n in hit:
            p = parents[ix]
            W("   [%4d @%#08x] %-36s X=%-4d children=%d types=%s"
              % (ix, p["start"], n, p["X"], len(p["kids"]),
                 sorted(set(c["type"] for c in p["kids"]))))

# ================= 2. census chains =================
W("\n" + "="*80); W("2. LIVE-CENSUS EFFECT CHAINS, type-2 followed to leaves"); W("="*80)
for nm in ["cargopu2","motorcycle","cargopu1","rotor","helibladestill","heliblade",
           "helipad","copter_spotlight","heli_closetoground","aircraftindicate"]:
    W("\n-------- %s --------" % nm)
    leaves.clear() if False else None
    walk(nm)

# ================= 3. offer-suspect chains =================
W("\n" + "="*80); W("3. MISSION/SELECTION FAMILY CHAINS"); W("="*80)
for nm in sorted(n for n in names if "mission" in n.lower() or "select" in n.lower()):
    W("\n-------- %s --------" % nm)
    walk(nm)

# ================= 4. leaf summary =================
W("\n" + "="*80); W("4. EVERY TYPE-1 LEAF REACHED, with f0 and file offset"); W("="*80)
for ix in sorted(leaves):
    e = t1[ix]
    W("   T1 #%-3d @file:%#08x  f0=%-8s rid=%s flags=%s cols=%-46s  via %s"
      % (ix, e["off"], e["f0"], e["rid"], e["flags"], e["cols"], sorted(leaves[ix])))

# ================= 5. who else uses 144161D2 =================
W("\n" + "="*80); W("5. ALL TYPE-1 ENTRIES USING THE mission-bubble TEXTURE 144161D2"); W("="*80)
users = [i for i, e in t1.items() if e["rid"] == "144161D2"]
for i in users:
    e = t1[i]
    refs = []
    for p in parents:
        for c in p["kids"]:
            if c["type"] == 1 and c["effidx"] == i:
                refs.append("%s::%s" % ("/".join(by_idx.get(p["idx"],["?"])), c["name"]))
    W("   T1 #%-3d @file:%#08x f0=%-8s cols=%-30s refs=%s" % (i, e["off"], e["f0"], e["cols"], refs))
OUT.close()
