r"""
calibrate_slots.py - how far does the MAC vtable order (sc4-ghidra-symbols
SimCity4.gdt) predict the WINDOWS vtable order?

The control is gzcom-dll: its headers are called through by shipping Windows
DLLs (ours included), so their declaration order IS the Windows slot order.
For every interface present in both, compare slot-by-slot. The agreement rate
is the confidence to attach to a Mac-only interface. Prints disagreements so
the rule (e.g. MSVC grouping overloads) can be read off them.

    python tools\sdk\ghidra\calibrate_slots.py
"""
import json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
INC = os.path.join(ROOT, "vendor", "gzcom-dll", "gzcom-dll", "include")
GDT = os.path.join(HERE, "out", "SimCity4.gdt.json")

def mac_slots(t):
    out = []
    for f in t["fields"]:
        n = f["name"] or "?"
        m = re.match(r"__ZThn\d+_NK?(\d+)", n)
        if m:  # thunk name: class length-prefixed, then method length-prefixed
            rest = n[m.end() + int(m.group(1)):]
            mm = re.match(r"(\d+)", rest)
            n = rest[len(mm.group(1)):len(mm.group(1)) + int(mm.group(1))] if mm else rest
        out.append(re.sub(r"\d+$", "", n))
    return out

def header_slots(path):
    src = open(path, encoding="latin-1").read()
    src = re.sub(r"//.*", "", src); src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    m = re.search(r"class\s+(\w+)\s*:\s*public\s+(\w+)", src)
    base = m.group(2) if m else None
    names = re.findall(r"virtual\s+[^;{(]*?\b(\w+)\s*\(", src)
    names = [n for n in names if not n.startswith("~")]
    return base, names

def full_header(name, seen=None):
    p = os.path.join(INC, name + ".h")
    if not os.path.exists(p): return None
    base, names = header_slots(p)
    if base and base != name:
        b = full_header(base) if base != "cIGZUnknown" else ["QueryInterface", "AddRef", "Release"]
        if b is None: return None
        return b + names
    return names

def main():
    j = json.load(open(GDT, encoding="utf-8"))
    vt = {t["name"][len("vftable_"):]: t for t in j["types"]
          if t["name"].startswith("vftable_") and t.get("fields")}
    tot = agree = 0; ifaces = exact = 0
    for name in sorted(vt):
        h = full_header(name)
        if not h: continue
        m = mac_slots(vt[name])
        ifaces += 1
        n = max(len(h), len(m))
        same = sum(1 for i in range(min(len(h), len(m))) if h[i] == m[i])
        tot += n; agree += same
        if same == n: exact += 1
        else:
            diffs = [(i, m[i] if i < len(m) else "-", h[i] if i < len(h) else "-")
                     for i in range(n) if (m[i] if i < len(m) else None) != (h[i] if i < len(h) else None)]
            print(f"{name}: mac {len(m)} slots, win {len(h)}; {len(diffs)} differ; first: {diffs[:4]}")
    print(f"\nINTERFACES IN BOTH: {ifaces}; slot-exact: {exact}; slots agreeing {agree}/{tot} = {100*agree/max(tot,1):.1f}%")
    if ifaces == 0: sys.exit("no overlap - the instrument saw nothing (check paths)")

main()
