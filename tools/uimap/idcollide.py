r"""idcollide.py - systematic window-id COLLISION audit.

Question: for every id our runtime/builders key a rule on, how many DISTINCT
things in the shipping game answer to that id?

Sources (all live):
  tools\uiscripts\extracted\*.ui        330 stock scripts  (data-declared ids)
  tools\uiscripts\extracted-plugins\    third-party scripts
  tools\uimap\_work\wincensus.json      literal SetID sites in the exe (code ids)
  src\UiSpike.cpp                       every k*Ids list
  tools\selective-safe\build_selective_safe.py  SCALED_WINDOW_IDS
"""
import json, os, re, sys, collections

# ⚠ SUPERSEDED by tools/uimap/id_collisions.py, which asks the same
# question as a re-runnable GATE. Kept as history; not published
# (task #108 NEEDS-HUMAN Q4, answered 2026-08-05).
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
CORPUS = os.path.join(ROOT, "tools", "uiscripts", "extracted")
PLUGCORPUS = os.path.join(ROOT, "tools", "uiscripts", "extracted-plugins")
SRC = os.path.join(ROOT, "src")

# ---------- 1. data-declared ids -------------------------------------------
ID_RE = re.compile(r"\bid=(0x[0-9a-fA-F]+|\d+)")
AREA_RE = re.compile(r"\barea=\((-?\d+),(-?\d+),(-?\d+),(-?\d+)\)")
CLS_RE = re.compile(r"\bclsid=(\S+)")

data_ids = collections.defaultdict(list)   # id -> [(script, depth, cls, w, h)]

def scan_dir(d, tag):
    if not os.path.isdir(d):
        return
    for fn in sorted(os.listdir(d)):
        if not fn.lower().endswith(".ui"):
            continue
        depth = 0
        inst = fn.split("_I-")[-1].replace(".ui", "")
        for line in open(os.path.join(d, fn), "r", errors="replace"):
            s = line.strip()
            if s.startswith("<CHILDREN>"):
                depth += 1
                continue
            if s.startswith("</CHILDREN>"):
                depth -= 1
                continue
            if not s.startswith("<LEGACY"):
                continue
            m = ID_RE.search(s)
            if not m:
                continue
            wid = int(m.group(1), 16) if m.group(1).startswith("0x") else int(m.group(1))
            a = AREA_RE.search(s)
            w = h = -1
            if a:
                l, t, r, b = (int(x) for x in a.groups())
                w, h = r - l, b - t
            c = CLS_RE.search(s)
            data_ids[wid].append((tag + inst, depth, c.group(1) if c else "?", w, h))

scan_dir(CORPUS, "")
scan_dir(PLUGCORPUS, "PLUGIN:")

# ---------- 2. code-declared ids -------------------------------------------
wc = json.load(open(os.path.join(ROOT, "tools", "uimap", "_work", "wincensus.json")))
code_ids = collections.defaultdict(list)
for e in wc["setIds"]:
    # entry shape unknown -> normalise
    wid = e["value"] & 0xFFFFFFFF
    code_ids[wid].append(("call=0x%06X" % e["call"], "owner=sub_%06X" % e["owner"]))

# ---------- 3. our id-keyed lists ------------------------------------------
uis = open(os.path.join(SRC, "UiSpike.cpp"), "r", errors="replace").read()

def grab_list(name, text):
    i = text.find(name)
    out = []
    while i != -1:
        j = text.find("{", i)
        if j == -1:
            break
        # match braces
        depth = 0
        k = j
        while k < len(text):
            if text[k] == "{":
                depth += 1
            elif text[k] == "}":
                depth -= 1
                if depth == 0:
                    break
            k += 1
        body = text[j:k]
        # strip // and /* */ comments
        body = re.sub(r"/\*.*?\*/", " ", body, flags=re.S)
        body = re.sub(r"//[^\n]*", " ", body)
        out += [int(x, 16) for x in re.findall(r"0x[0-9a-fA-F]{6,8}", body)]
        break
    return sorted(set(out))

LISTS = {}
for nm in ["kRegionPanelIds", "kNeverScaleIds", "kGodToolFlyoutIds", "kGodPanelIds",
           "kSubFlyoutIds", "kAlwaysScaleCityIds", "kDataScaledSubtreeIds",
           "kFontSizedIds", "kAdviceListScaleSelfIds", "kAdviceListNeverTouchIds",
           "kBmpxCityRoots", "kBmpxDialogRoots", "kCityDialogIds"]:
    LISTS[nm] = grab_list(nm + "[]", uis) or grab_list(nm + " ", uis)

ss = open(os.path.join(ROOT, "tools", "selective-safe", "build_selective_safe.py"), "r", errors="replace").read()
LISTS["SCALED_WINDOW_IDS"] = grab_list("SCALED_WINDOW_IDS = ", ss)

# ---------- 4. report -------------------------------------------------------
print("=" * 78)
print("A. CORPUS-WIDE: ids declared by MORE THAN ONE script instance")
print("=" * 78)
multi = {k: v for k, v in data_ids.items() if len({x[0] for x in v}) > 1}
print("total distinct ids in corpus: %d ; multi-script ids: %d" % (len(data_ids), len(multi)))
for wid in sorted(multi):
    scripts = sorted({x[0] for x in multi[wid]})
    sizes = sorted({(x[3], x[4]) for x in multi[wid]})
    print("  0x%08X  %d scripts %s  sizes %s" % (wid, len(scripts), scripts, sizes))

print()
print("=" * 78)
print("B. CROSS-LAYER: id declared in DATA *and* stamped by a literal SetID in CODE")
print("=" * 78)
for wid in sorted(set(data_ids) & set(code_ids)):
    print("  0x%08X  scripts=%s  code=%s" % (wid,
          sorted({x[0] for x in data_ids[wid]}), code_ids[wid]))

print()
print("=" * 78)
print("C. CODE-SIDE: id stamped by MORE THAN ONE SetID site")
print("=" * 78)
for wid in sorted(code_ids):
    if len(code_ids[wid]) > 1:
        print("  0x%08X  %s" % (wid, code_ids[wid]))

print()
print("=" * 78)
print("D. OUR LISTS: every entry, with its collision count")
print("=" * 78)
for nm in LISTS:
    ids = LISTS[nm]
    bad = []
    for wid in ids:
        ns = len({x[0] for x in data_ids.get(wid, [])})
        nc = len(code_ids.get(wid, []))
        if ns > 1 or (ns >= 1 and nc >= 1) or nc > 1:
            bad.append((wid, ns, nc))
    print("%-28s %3d entries, %d COLLIDING" % (nm, len(ids), len(bad)))
    for wid, ns, nc in bad:
        scripts = sorted({x[0] for x in data_ids.get(wid, [])})
        sizes = sorted({(x[3], x[4]) for x in data_ids.get(wid, [])})
        print("    !! 0x%08X  scripts=%d %s sizes=%s codeSetID=%d %s"
              % (wid, ns, scripts, sizes, nc, code_ids.get(wid, [])))

print()
print("=" * 78)
print("E. SMALL-INTEGER ids in the corpus (collision-prone by construction)")
print("=" * 78)
for wid in sorted(data_ids):
    if wid < 0x01000000:
        scripts = sorted({x[0] for x in data_ids[wid]})
        sizes = sorted({(x[3], x[4]) for x in data_ids[wid]})
        print("  0x%08X  %2d refs, %2d scripts sizes=%s" % (wid, len(data_ids[wid]), len(scripts), sizes[:6]))
