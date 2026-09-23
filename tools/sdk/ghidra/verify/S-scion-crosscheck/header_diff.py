r"""Scion cross-check, part 1: interface order, Scion vs our gzcom-dll pin.

    python tools\sdk\ghidra\verify\S-scion-crosscheck\header_diff.py

Fetches Scion's interface headers (github.com/nsgomez/scion, LGPL-2.1+) with
`gh api` into `_scion\` (gitignored: never committed), then compares every
cIGZ* interface both projects declare by (name, argument count) in
declaration order, plus its base class.

Both are compiled by MSVC, so identical sequences give identical slots under
any grouping rule. Agreement proves nothing, because one author wrote both.
Only a disagreement is a signal, and exe_checks.py settles those against
the exe.
"""
import base64
import json
import os
import re
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "_scion")
REPO = os.path.normpath(os.path.join(HERE, "..", "..", "..", "..", ".."))
GZ = os.path.join(REPO, "vendor", "gzcom-dll", "gzcom-dll", "include")


def gh(path):
    out = subprocess.run(["gh", "api", path], capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def fetch():
    tree = gh("repos/nsgomez/scion/git/trees/main?recursive=1")["tree"]
    want = [t for t in tree if t["type"] == "blob"
            and re.match(r"src/(framework|gzresource)/include/.*\.h$", t["path"])]
    for t in want:
        dst = os.path.join(CACHE, *t["path"].split("/"))
        if not os.path.exists(dst):
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            blob = gh("repos/nsgomez/scion/git/blobs/" + t["sha"])
            with open(dst, "wb") as f:
                f.write(base64.b64decode(blob["content"]))
    return len(want)


def strip(text):
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
    return re.sub(r"//[^\n]*", " ", text)


def class_body(text, cls):
    m = re.search(r"\b(?:class|struct)\s+(" + cls + r")\b\s*(:[^{;]*)?\{", text, flags=re.I)
    if not m:
        return None, None
    i, depth = m.end(), 1
    while depth and i < len(text):
        depth += {"{": 1, "}": -1}.get(text[i], 0)
        i += 1
    base = re.sub(r"\b(public|protected|private|virtual)\b|:", "", m.group(2) or "")
    return text[m.end():i - 1], " ".join(base.split())


def arity(args):
    args = args.strip()
    if args in ("", "void"):
        return 0
    depth, n = 0, 1
    for ch in args:
        depth += {"<": 1, "(": 1, ">": -1, ")": -1}.get(ch, 0)
        n += ch == "," and depth == 0
    return n


def virtuals(body):
    flat = " ".join(body.split())
    return [(m.group(1), arity(m.group(2))) for m in re.finditer(
        r"\bvirtual\s+[^;{]*?\b(~?\w+)\s*\(([^()]*(?:\([^()]*\)[^()]*)*)\)", flat)]


def index(root):
    return {f.lower(): os.path.join(dp, f) for dp, _, fs in os.walk(root) for f in fs if f.endswith(".h")}


def main():
    print("Scion headers fetched or cached: %d" % fetch())
    sidx = index(CACHE)
    gidx = index(GZ)
    shared = sorted(k for k in sidx if k in gidx and k.startswith("cigz"))
    print("cIGZ headers in both: %d; Scion only: %d" % (
        len(shared), sum(1 for k in sidx if k.startswith("cigz") and k not in gidx)))
    same, diff = [], []
    for key in shared:
        cls = os.path.splitext(key)[0]
        s_text = strip(open(sidx[key], encoding="utf-8", errors="replace").read())
        g_text = strip(open(gidx[key], encoding="utf-8", errors="replace").read())
        sb, sbase = class_body(s_text, cls)
        gb, gbase = class_body(g_text, cls)
        if sb is None or gb is None:
            diff.append((key, "declared only in %s" % ("gzcom-dll" if sb is None else "Scion"), []))
            continue
        sv = [(n.lower(), a) for n, a in virtuals(sb)]
        gv = [(n.lower(), a) for n, a in virtuals(gb)]
        if sv == gv and sbase.lower() == gbase.lower():
            same.append("%s(%d)" % (key[:-2], len(sv)))
            continue
        rows = []
        if sbase.lower() != gbase.lower():
            rows.append("base: Scion %s, gzcom-dll %s" % (sbase, gbase))
        for i in range(max(len(sv), len(gv))):
            a = sv[i] if i < len(sv) else None
            b = gv[i] if i < len(gv) else None
            if a != b:
                rows.append("slot %2d: Scion %-32s gzcom-dll %s" % (
                    i + 3, "%s/%d" % a if a else "-", "%s/%d" % b if b else "-"))
        diff.append((key, "%d vs %d methods" % (len(sv), len(gv)), rows))
    print("\nIDENTICAL (%d): %s" % (len(same), ", ".join(same)))
    print("\nDIFFERENT (%d):" % len(diff))
    for key, head, rows in diff:
        print("  %s  (%s)" % (key[:-2], head))
        for r in rows[:14]:
            print("      " + r)
        if len(rows) > 14:
            print("      ... %d more" % (len(rows) - 14))


if __name__ == "__main__":
    main()
