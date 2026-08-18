#!/usr/bin/env python3
r"""offer_chain.py - #188 lane: find the OFFER-INDICATOR parent effect and its
size chain. Reads effdir-dump.txt + type1-table.txt (already produced), builds a
parent->child graph, follows type=2 (spawn-another-effect-by-name) chains to
their type-0/type-1 leaves, and reports f0 + file offset for every type-1 leaf.

Read-only. Writes offer-chain.txt next to this script.
"""
import os, re, sys, json, collections

HERE = os.path.dirname(os.path.abspath(__file__))
DUMP = os.path.join(HERE, "effdir-dump.txt")
T1   = os.path.join(HERE, "type1-table.txt")

# ---------------- parse effdir-dump.txt ----------------
P_RE = re.compile(r"^\[\s*(\d+) @file:(0x[0-9a-f]+)\] (.*?)\s+\(X=(-?\d+) A=(-?\d+) children=(\d+)\)$")
C_RE = re.compile(r"^    child (?:'(.*?)'|\"(.*?)\") type=(\d+) flags=(\S+) scale=(\S+) \(SCALE@file:(0x[0-9a-f]+)\) "
                  r"trans=\((\S+?),(\S+?),(\S+?)\) rot=(\S+|\(.*?\)) zoom=(\d+)\.\.(\d+) copies=(\d+) mult=(\d+) "
                  r"ramps=\((.*?)\) effectIndex=(0x[0-9a-f]+)\((\d+)\)$")

parents = {}          # idx -> dict
byname  = {}          # lowercase name -> idx
second  = []          # (name, classId, sub)

cur = None
in_second = False
for line in open(DUMP, encoding="utf-8", errors="replace"):
    line = line.rstrip("\n")
    if line.startswith("---- second map"):
        in_second = True; continue
    if in_second:
        m = re.match(r"^  (\S+)\s+classId=(0x[0-9a-f]+) sub=(-?\d+)$", line)
        if m: second.append((m.group(1), int(m.group(2), 16), int(m.group(3))))
        continue
    m = P_RE.match(line)
    if m:
        idx = int(m.group(1))
        names = m.group(3).split("/")
        cur = dict(idx=idx, off=int(m.group(2), 16), names=names,
                   X=int(m.group(4)), A=int(m.group(5)), kids=[])
        parents[idx] = cur
        for n in names:
            byname[n.lower()] = idx
        continue
    m = C_RE.match(line)
    if m and cur is not None:
        nm = m.group(1) if m.group(1) is not None else m.group(2)
        cur["kids"].append(dict(name=nm, type=int(m.group(3)),
                                flags=m.group(4), scale=m.group(5),
                                scale_off=int(m.group(6), 16),
                                trans=(m.group(7), m.group(8), m.group(9)),
                                zmin=int(m.group(11)), zmax=int(m.group(12)),
                                copies=int(m.group(13)), mult=int(m.group(14)),
                                ramps=m.group(15), effidx=int(m.group(17))))
        continue

sys.stderr.write("parsed %d parents, %d names, %d second-map entries\n"
                 % (len(parents), len(byname), len(second)))

# ---------------- parse type1-table.txt ----------------
T1_RE = re.compile(r"^\s*(\d+) @file:(0x[0-9a-f]+) rid=([0-9A-F]{8}) flags=(\S+) b8=(\d+) b9=(\d+) f0=(\S+)\s+cols=(\[.*?\]) tail=\((.*?)\)")
t1 = {}
for line in open(T1, encoding="utf-8", errors="replace"):
    m = T1_RE.match(line)
    if m:
        t1[int(m.group(1))] = dict(off=int(m.group(2), 16), rid=m.group(3),
                                   flags=m.group(4), b8=int(m.group(5)),
                                   b9=int(m.group(6)), f0=m.group(7),
                                   cols=m.group(8), tail=m.group(9))
sys.stderr.write("parsed %d type-1 entries\n" % len(t1))

OUT = open(os.path.join(HERE, "offer-chain.txt"), "w", encoding="utf-8")
def W(*a):
    s = " ".join(str(x) for x in a)
    OUT.write(s + "\n")
    print(s)

# ---------------- 1. keyword parents ----------------
KW = ["indicate", "advice", "offer", "avail", "opportun", "reward", "task",
      "job", "deliver", "pickup", "pu1", "pu2", "tour", "race", "scenario"]
W("="*78)
W("1. PARENTS WHOSE NAME MATCHES OFFER/MISSION/ADVICE KEYWORDS")
W("="*78)
hits = collections.OrderedDict()
for idx, p in sorted(parents.items()):
    for n in p["names"]:
        ln = n.lower()
        for k in KW:
            if k in ln:
                hits.setdefault(k, []).append((idx, n, p))
                break
for k in KW:
    lst = hits.get(k, [])
    W("\n--- keyword %r : %d parent(s) ---" % (k, len(lst)))
    for idx, n, p in lst:
        W("  [%4d @%#08x] %-34s children=%d  types=%s"
          % (idx, p["off"], n, len(p["kids"]),
             sorted(set(c["type"] for c in p["kids"]))))

# ---------------- child-name keyword sweep too ----------------
W("\n" + "="*78)
W("1b. PARENTS WITH A KEYWORD-MATCHING CHILD NAME (parent name may differ)")
W("="*78)
seen = set()
for idx, p in sorted(parents.items()):
    for c in p["kids"]:
        ln = c["name"].lower()
        if any(k in ln for k in KW) and (idx, c["name"]) not in seen:
            seen.add((idx, c["name"]))
            W("  [%4d] %-30s -> child %-32r type=%d effidx=%d"
              % (idx, "/".join(p["names"]), c["name"], c["type"], c["effidx"]))

# ---------------- f0 histogram ----------------
W("\n" + "="*78)
W("1c. TYPE-1 f0 HISTOGRAM (which f0 values are rare = candidate special sizes)")
W("="*78)
h = collections.Counter(e["f0"] for e in t1.values())
for v, n in sorted(h.items(), key=lambda kv: -kv[1]):
    W("   f0=%-10s x%d" % (v, n))
rare = {v for v, n in h.items() if n <= 4}
W("\n   rare f0 values (<=4 uses): %s" % sorted(rare))
for i, e in sorted(t1.items()):
    if e["f0"] in rare:
        W("     entry %3d @%#08x rid=%s f0=%-8s cols=%s" % (i, e["off"], e["rid"], e["f0"], e["cols"]))

# ---------------- who references each type-1 entry ----------------
W("\n" + "="*78)
W("1d. PARENTS REFERENCING A TYPE-1 CHILD WITH A NON-COMMON f0")
W("="*78)
COMMON = {v for v, n in h.items() if n >= 20}
W("   (common f0 = %s)" % sorted(COMMON))
for idx, p in sorted(parents.items()):
    for c in p["kids"]:
        if c["type"] == 1:
            e = t1.get(c["effidx"])
            if e and e["f0"] not in COMMON:
                W("  [%4d] %-30s child %-30r t1#%d f0=%-8s rid=%s cols=%s"
                  % (idx, "/".join(p["names"]), c["name"], c["effidx"],
                     e["f0"], e["rid"], e["cols"]))

# ---------------- 2. census chains ----------------
CENSUS = ["cargopu2", "motorcycle", "cargopu1", "rotor", "helibladestill",
          "heliblade", "helipad", "copter_spotlight", "heli_closetoground",
          "aircraftindicate"]

def dump_tree(name, depth=0, path=(), seen_names=None):
    if seen_names is None: seen_names = set()
    pad = "  " * depth
    key = name.lower()
    if key in seen_names:
        W("%s%s  <cycle>" % (pad, name)); return
    seen_names = seen_names | {key}
    idx = byname.get(key)
    if idx is None:
        W("%s%s -> NOT IN EFFDIR (lookup would fail, ok=0)" % (pad, name))
        return
    p = parents[idx]
    W("%s%s  [parent %d @%#08x] X=%d A=%d children=%d"
      % (pad, name, idx, p["off"], p["X"], p["A"], len(p["kids"])))
    for c in p["kids"]:
        tag = {0:"type0 PARTICLE", 1:"type1 DECAL/SPRITE", 2:"type2 SPAWN-BY-NAME",
               3:"type3", 4:"type4", 5:"type5", 6:"type6", 7:"type7 SOUND?",
               8:"type8", 9:"type9"}.get(c["type"], "type%d" % c["type"])
        extra = ""
        if c["type"] == 1:
            e = t1.get(c["effidx"])
            if e:
                extra = ("  <<LEAF type1 t1#%d @file:%#08x f0=%s rid=%s cols=%s>>"
                         % (c["effidx"], e["off"], e["f0"], e["rid"], e["cols"]))
            else:
                extra = "  <<type1 idx %d OUT OF TABLE>>" % c["effidx"]
        W("%s  - %-30r %s scale=%s trans=%s zoom=%d..%d copies=%d effidx=%d%s"
          % (pad, c["name"], tag, c["scale"], c["trans"], c["zmin"], c["zmax"],
             c["copies"], c["effidx"], extra))
        if c["type"] == 2 and c["name"]:
            dump_tree(c["name"], depth + 2, path + (name,), seen_names)

W("\n" + "="*78)
W("2. LIVE-CENSUS EFFECT CHAINS (type2 followed to leaves)")
W("="*78)
for nm in CENSUS:
    W("\n---------------- %s ----------------" % nm)
    dump_tree(nm)

# ---------------- 3. what asks for helipad ----------------
W("\n" + "="*78)
W("3. 'helipad' presence check")
W("="*78)
for nm in sorted(byname):
    if "heli" in nm or "pad" in nm or "copter" in nm or "rotor" in nm:
        W("   effdir name: %-34s -> parent %d" % (nm, byname[nm]))
W("   second-map entries containing heli/pad/copter:")
for nm, cid, sub in second:
    l = nm.lower()
    if "heli" in l or "pad" in l or "copter" in l:
        W("     %-36s classId=%#010x sub=%d" % (nm, cid, sub))

OUT.close()
