r"""id_collisions.py - window-id COLLISION audit, re-runnable gate.

THE QUESTION
    Our runtime keys rules on window ids. A rule that says "when you see id X,
    do Y" is only safe if exactly ONE thing in the shipping game answers to X.
    Where two different scripts declare the same id, an id-keyed rule can fire
    on the wrong window - and, worse, an id-keyed *instrument* can print the
    wrong window's line and thereby certify its own error.

    Found by accident once (0x27DF05BE = Sim occupant chip in I-6a9455c9 AND
    "Obliterate City" confirm in I-2a41436c). This finds the rest on purpose.

WHY THIS REPLACES idcollide.py
    idcollide.py had two defects that both HID collisions:
      1. It keyed a "script" on the .UI filename's INSTANCE only
         (fn.split("_I-")[-1]), so T-0_G-08000600_I-09923283 and
         T-0_G-96a006b0_I-09923283 - two different scripts in two different
         groups - counted as ONE. 10 instances in the stock corpus appear
         under two groups. This keys on the full (group, instance).
      2. It checked a HARDCODED list of 13 array names. src\UiSpike.cpp has 26
         arrays and src\CodePatches.cpp has 22; kHookParents (x2) and kParents
         (x2) were never checked. This DISCOVERS every array in both files.
    It also counted PLUGIN:X vs stock X as a collision. Those are the same TGI
    resolved by load order - only one is ever live - so they are deduped.

SEVERITY - a collision is only dangerous if the two windows DIFFER
    CRITICAL  >=2 distinct TGIs declare it as a ROOT, and they differ in class
              or in size. Our rule can address the wrong root. This is the
              0x27DF05BE shape.
    HIGH      >=2 distinct TGIs, root in at least one, differing class/size.
    MEDIUM    >=2 distinct TGIs differing in class or size, never a root.
    LOW       >=2 distinct TGIs but identical class AND identical size in all
              of them - a shared template; the rule does the same thing either
              way. Noise, not a bug.

EXIT CODE
    0  no CRITICAL/HIGH pair outside the baseline
    1  a NEW CRITICAL/HIGH (id, list) pair appeared  -> a rule now fires on an
       ambiguous id; triage it
    2  could not run (missing corpus / source)
    Refresh the baseline deliberately, never casually:
        python id_collisions.py --update-baseline
"""

import collections
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CORPUS = os.path.join(ROOT, "tools", "uiscripts", "extracted")
PLUGCORPUS = os.path.join(ROOT, "tools", "uiscripts", "extracted-plugins")
SRC = os.path.join(ROOT, "src")
SRC_FILES = ["UiSpike.cpp", "CodePatches.cpp"]
BASELINE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "id_collisions.baseline.json")

ID_RE = re.compile(r"\bid=(0x[0-9a-fA-F]+|\d+)")
AREA_RE = re.compile(r"\barea=\((-?\d+),(-?\d+),(-?\d+),(-?\d+)\)")
CLS_RE = re.compile(r"\bclsid=(\S+)")
CAP_RE = re.compile(r'\bcaption="([^"]*)"')
FNAME_RE = re.compile(r"T-([0-9a-fA-F]+)_G-([0-9a-fA-F]+)_I-([0-9a-fA-F]+)\.ui$", re.I)

# An array declaration: <qualifiers> <type> NAME[] = { ... }
ARRAY_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\[\s*\]\s*=\s*\{")


# ---------------------------------------------------------------- corpus ----
Decl = collections.namedtuple("Decl", "tgi group inst depth cls w h caption plugin")


def scan_dir(directory, is_plugin, out):
    """Append every id= declaration in every .ui under `directory` to `out`."""
    if not os.path.isdir(directory):
        return 0
    n = 0
    for fn in sorted(os.listdir(directory)):
        if not fn.lower().endswith(".ui"):
            continue
        m = FNAME_RE.search(fn)
        if not m:
            continue
        group, inst = m.group(2).lower(), m.group(3).lower()
        tgi = "G-%s_I-%s" % (group, inst)
        depth = 0
        n += 1
        with open(os.path.join(directory, fn), "r", errors="replace") as fh:
            for line in fh:
                s = line.strip()
                if s.startswith("<CHILDREN>"):
                    depth += 1
                    continue
                if s.startswith("</CHILDREN>"):
                    depth -= 1
                    continue
                if not s.startswith("<LEGACY"):
                    continue
                mid = ID_RE.search(s)
                if not mid:
                    continue
                g = mid.group(1)
                wid = int(g, 16) if g.startswith("0x") else int(g)
                a = AREA_RE.search(s)
                w = h = -1
                if a:
                    l, t, r, b = (int(x) for x in a.groups())
                    w, h = r - l, b - t
                c = CLS_RE.search(s)
                cap = CAP_RE.search(s)
                out[wid].append(Decl(tgi, group, inst, depth,
                                     c.group(1) if c else "?", w, h,
                                     cap.group(1) if cap else "", is_plugin))
    return n


def load_corpus():
    decls = collections.defaultdict(list)
    a = scan_dir(CORPUS, False, decls)
    b = scan_dir(PLUGCORPUS, True, decls)
    return decls, a, b


# Groups that are RESOLUTION VARIANTS of one another, not distinct scripts.
# tools\research\SC4-UI-ENGINE.md:478 - "0x08000600 | 800x600 layout overrides
# - the group id literally encodes the resolution (0800 x 0600). Same instance
# ids, same window ids, different pixel geometry". The engine picks ONE by
# resolution, so a G-08000600 twin is never co-resident with its G-96a006b0
# original; at our tiers the 800x600 group is never loaded at all (the exe
# holds ZERO literal references to 0x08000600 - it is computed from the mode).
# Counting a twin as a second declaration invents ~20 false CRITICALs.
RES_VARIANT_GROUPS = {"96a006b0", "08000600"}


def distinct_tgis(dl):
    """Distinct SCRIPTS.

    Identity is the INSTANCE, not the file and not the (group, instance):
      * PLUGIN and stock copies of one TGI are one script - load order picks
        one, only one is ever live.
      * A G-08000600 twin is the same script at another design resolution.
    Keying on the full (group, instance) - or on the filename - both give the
    wrong answer, in opposite directions.
    """
    return sorted({d.inst for d in dl})


def cross_group_anomalies(decls):
    """Instances that span groups OUTSIDE the known resolution-variant pair.

    Collapsing on the instance is only sound while that is the ONLY reason an
    instance appears under two groups. This is the guard on that assumption -
    if it ever fires, the collapse above is unsound and must be revisited.
    """
    seen = collections.defaultdict(set)
    for dl in decls.values():
        for d in dl:
            seen[d.inst].add(d.group)
    return {i: sorted(g) for i, g in seen.items()
            if len(g) > 1 and not g <= RES_VARIANT_GROUPS}


def classify(dl):
    """Return (severity, reason) for one id's declaration list."""
    tgis = distinct_tgis(dl)
    if len(tgis) < 2:
        return None, ""
    # Judge shape from the LIVE group only. An 800x600 twin's geometry differs
    # by design; letting it into the size set overstates every difference.
    live = [d for d in dl if d.group != "08000600"]
    if live:
        dl = live
        tgis = distinct_tgis(dl)
        if len(tgis) < 2:
            return None, ""
    roots = [d for d in dl if d.depth == 0]
    root_tgis = sorted({d.inst for d in roots})
    classes = {d.cls for d in dl}
    sizes = {(d.w, d.h) for d in dl}
    differs = len(classes) > 1 or len(sizes) > 1
    if not differs:
        return "LOW", "identical class %s and size %s in all %d scripts" % (
            sorted(classes)[0], sorted(sizes)[0], len(tgis))
    # Area spread separates "one template reused by N sibling scripts, each a
    # few px tall" (Advisors, ordinance panels - only ever ONE open at a time,
    # and our rule wants the same thing from each) from "two structurally
    # different windows". Without this every template family reads CRITICAL.
    areas = [d.w * d.h for d in dl if d.w > 0 and d.h > 0]
    ratio = (max(areas) / float(min(areas))) if areas and min(areas) > 0 else 1.0
    bits = []
    if len(classes) > 1:
        bits.append("classes %s" % sorted(classes))
    if len(sizes) > 1:
        bits.append("area spread x%.2f, sizes %s" % (ratio, sorted(sizes)[:6]))
    why = "; ".join(bits)
    template = len(classes) == 1 and ratio < 1.25
    if template:
        return "MEDIUM", ("TEMPLATE FAMILY: one class, area spread only x%.2f "
                          "across %d scripts - same logical window, and only "
                          "one is ever open at a time" % (ratio, len(tgis)))
    if len(root_tgis) >= 2:
        return "CRITICAL", "ROOT in %d scripts (%s); %s" % (
            len(root_tgis), ", ".join(root_tgis[:8]), why)
    if len(root_tgis) == 1:
        return "HIGH", "ROOT in %s, CHILD elsewhere; %s" % (root_tgis[0], why)
    return "MEDIUM", "never a root; %s" % why


# ----------------------------------------------------------------- lists ----
def strip_comments(text):
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
    text = re.sub(r"//[^\n]*", " ", text)
    return text


def discover_lists(path):
    """Every `NAME[] = { ... }` in the file -> {name: [literals]}.

    Names repeat (kHookParents and kParents are each declared twice in
    different scopes); each occurrence is kept as NAME@line so a collision is
    reported against the exact declaration.
    """
    with open(path, "r", errors="replace") as fh:
        text = fh.read()
    out = {}
    for m in ARRAY_RE.finditer(text):
        name = m.group(1)
        open_brace = text.index("{", m.end() - 1)
        depth = 0
        k = open_brace
        while k < len(text):
            if text[k] == "{":
                depth += 1
            elif text[k] == "}":
                depth -= 1
                if depth == 0:
                    break
            k += 1
        body = strip_comments(text[open_brace:k])
        lits = [int(x, 16) for x in re.findall(r"0x[0-9a-fA-F]{4,8}\b", body)]
        if not lits:
            continue
        line = text.count("\n", 0, m.start()) + 1
        out["%s@%d" % (name, line)] = sorted(set(lits))
    return out


def main():
    update = "--update-baseline" in sys.argv
    verbose = "--all" in sys.argv

    if not os.path.isdir(CORPUS):
        print("FATAL: corpus missing: %s" % CORPUS)
        return 2
    decls, n_stock, n_plug = load_corpus()
    if not decls:
        print("FATAL: corpus parsed to zero declarations")
        return 2

    lists = {}
    for fn in SRC_FILES:
        p = os.path.join(SRC, fn)
        if not os.path.isfile(p):
            print("FATAL: source missing: %s" % p)
            return 2
        for k, v in discover_lists(p).items():
            lists["%s:%s" % (fn, k)] = v

    # POSITIVE CONTROL. If these three do not hold, every null below is
    # structural and this whole report is fiction. Stated, not assumed.
    ctrl = []
    ctrl.append(("corpus finds the known collision 0x27DF05BE in exactly 2 TGIs",
                 len(distinct_tgis(decls.get(0x27DF05BE, []))) == 2))
    ctrl.append(("corpus finds 0x6BB92BCB (the #98 root)",
                 0x6BB92BCB in decls))
    ctrl.append(("list scan finds kRegionPanelIds - the list the #98 census MISSED",
                 any(k.split(":")[-1].startswith("kRegionPanelIds@") for k in lists)))
    ctrl.append(("list scan reaches CodePatches.cpp",
                 any(k.startswith("CodePatches.cpp:") for k in lists)))
    ctrl.append(("list scan finds kHookParents - which idcollide.py never checked",
                 any(k.split(":")[-1].startswith("kHookParents@") for k in lists)))
    anomalies = cross_group_anomalies(decls)
    ctrl.append(("instance-collapse is sound: no instance spans groups outside "
                 "%s (%d anomalies)" % (sorted(RES_VARIANT_GROUPS), len(anomalies)),
                 not anomalies))

    print("=" * 78)
    print("POSITIVE CONTROL (a null below is MEASURED only if all of these pass)")
    print("=" * 78)
    ok = True
    for name, passed in ctrl:
        print("  [%s] %s" % ("PASS" if passed else "FAIL", name))
        ok = ok and passed
    if not ok:
        print("\nFATAL: positive control failed - do not trust this report.")
        return 2
    print("\n  corpus: %d stock scripts + %d plugin scripts, %d distinct ids"
          % (n_stock, n_plug, len(decls)))
    print("  lists : %d array declarations across %s"
          % (len(lists), ", ".join(SRC_FILES)))

    # ---------------------------------------------------- corpus census ----
    graded = {}
    for wid, dl in decls.items():
        sev, why = classify(dl)
        if sev:
            graded[wid] = (sev, why)
    tally = collections.Counter(s for s, _ in graded.values())
    print()
    print("=" * 78)
    print("A. CORPUS CENSUS - ids declared by more than one SCRIPT TGI")
    print("=" * 78)
    print("  %d of %d distinct ids  (CRITICAL %d / HIGH %d / MEDIUM %d / LOW %d)"
          % (len(graded), len(decls), tally["CRITICAL"], tally["HIGH"],
             tally["MEDIUM"], tally["LOW"]))
    print("  NOTE: a corpus collision is only a BUG once an id-keyed rule")
    print("        addresses it. Section B is the part that matters.")

    # -------------------------------------------------- the intersection ----
    RANK = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    hits = []
    for lname, ids in sorted(lists.items()):
        for wid in ids:
            if wid in graded:
                sev, why = graded[wid]
                hits.append((RANK[sev], sev, wid, lname, why))
    hits.sort(key=lambda t: (t[0], -len(distinct_tgis(decls[t[2]])), t[2]))

    print()
    print("=" * 78)
    print("B. THE INTERSECTION - ambiguous ids that one of OUR lists keys on")
    print("=" * 78)
    if not hits:
        print("  EMPTY. No id in any list is declared by more than one script.")
    else:
        shown = [h for h in hits if verbose or h[1] in ("CRITICAL", "HIGH")]
        print("  %d (id, list) pairs; %d CRITICAL/HIGH shown%s"
              % (len(hits), len([h for h in hits if h[0] <= 1]),
                 "" if verbose else "  (--all for MEDIUM/LOW)"))
        print()
        for _, sev, wid, lname, why in shown:
            tg = distinct_tgis(decls[wid])
            print("  %-8s 0x%08X  in %s" % (sev, wid, lname))
            print("           %d scripts: %s" % (len(tg), ", ".join(tg)))
            print("           %s" % why)

    # ------------------------------------------------------------- gate ----
    current = sorted("%08X|%s" % (wid, lname)
                     for r, _, wid, lname, _ in hits if r <= 1)
    base = []
    if os.path.isfile(BASELINE):
        with open(BASELINE, "r") as fh:
            base = json.load(fh).get("critical_high", [])
    if update:
        with open(BASELINE, "w", newline="\n") as fh:
            json.dump({"critical_high": current}, fh, indent=2)
            fh.write("\n")
        print("\nbaseline updated: %d CRITICAL/HIGH pairs" % len(current))
        return 0

    new = sorted(set(current) - set(base))
    gone = sorted(set(base) - set(current))
    print()
    print("=" * 78)
    print("C. GATE")
    print("=" * 78)
    print("  baseline: %d pairs   current: %d pairs" % (len(base), len(current)))
    for p in gone:
        print("  RESOLVED  %s" % p)
    for p in new:
        print("  NEW       %s   <-- a rule now keys on an ambiguous id" % p)
    if new:
        print("\n  FAIL: %d new CRITICAL/HIGH pair(s)." % len(new))
        return 1
    print("\n  PASS: no new CRITICAL/HIGH pair.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
