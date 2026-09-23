# arity_check.py - compare Mac Itanium parameter counts (from the mangled thunk names in the
# Mac JSON) with the Windows callee-cleanup size (ret N) of every slot of the Windows tables.
# All SC4 graph parameters are 4-byte on x86 (ints, enums, floats, pointers, references).
import sys, json, re
sys.path.insert(0, r"C:\dev\SC4UIScale\tools\sdk\ghidra\verify\W-Graph-verify")
from vx import *

J = json.load(open(r"C:\dev\SC4UIScale\tools\sdk\ghidra\out\SimCity4.gdt.json"))
TYPES = {t["path"]: t for t in J["types"]}

def parse_type(s, i):
    """consume one Itanium <type> starting at s[i]; return new index."""
    c = s[i]
    if c in "vbcahstijlmxyfdenw":
        return i + 1
    if c in "PRK":
        return parse_type(s, i + 1)
    if c == "S":
        # substitution S_ , S0_, S1_ ... or St (std::) prefix, or Sa/Sb/Ss/Si/So/Sd abbreviations
        if s[i + 1] in "abdios":
            j = i + 2
            if j < len(s) and s[j] == "I":
                j = parse_template_args(s, j)
            return j
        if s[i + 1] == "t":
            j = parse_name(s, i + 2)
            if j < len(s) and s[j] == "I":
                j = parse_template_args(s, j)
            return j
        j = i + 1
        while s[j] != "_":
            j += 1
        return j + 1
    if c.isdigit():
        j = parse_name(s, i)
        if j < len(s) and s[j] == "I":
            j = parse_template_args(s, j)
        return j
    if c == "N":
        j = i + 1
        while s[j] != "E":
            if s[j].isdigit():
                j = parse_name(s, j)
            elif s[j] == "I":
                j = parse_template_args(s, j)
            else:
                j += 1
        return j + 1
    raise ValueError("unhandled %r at %d in %s" % (c, i, s))

def parse_name(s, i):
    j = i
    while s[j].isdigit():
        j += 1
    n = int(s[i:j])
    return j + n

def parse_template_args(s, i):
    assert s[i] == "I"
    j = i + 1
    while s[j] != "E":
        j = parse_type(s, j)
    return j + 1

def mac_params(mangled):
    # __ZThn548_N12cGZLineGraph10InsertDataEfmm
    m = re.match(r"__ZThn\d+_N(\d+)", mangled)
    if not m:
        return None, None
    i = mangled.index("_N") + 2
    i = parse_name(mangled, i)            # class
    j = parse_name(mangled, i)            # method
    method = mangled[i:j]
    method = re.sub(r"^\d+", "", method)
    assert mangled[j] == "E", mangled
    k = j + 1
    params = 0
    while k < len(mangled):
        if mangled[k] == "v" and k == len(mangled) - 1:
            break
        k = parse_type(mangled, k)
        params += 1
    return method, params

def win_ret(entry):
    tgt, adj, chain = resolve_thunk(entry)
    r, _ = ret_n(tgt, 400)
    return tgt, (int(r, 16) if r and r.startswith("0x") else int(r)) if r is not None else None

PAIRS = [
    ("/vftable_cIGZLineGraph", 0xAB4B98, "cSC4LineGraph cIGZLineGraph"),
    ("/vftable_cIGZLineGraph", 0xADF5B0, "cGZLineGraph cIGZLineGraph"),
    ("/vftable_cIGZScatterGraph", 0xADED58, "cGZScatterGraph cIGZScatterGraph"),
    ("/vftable_cIGZGraph", 0xAB4C28, "Mac 'cIGZGraph'(Thn580) vs Windows +0xD8 table (expect mismatch)"),
]
for mac_path, wva, label in PAIRS:
    t = TYPES[mac_path]
    print("==== %s  (Mac %s, %d slots) vs Windows 0x%08X" % (label, mac_path, len(t["fields"]), wva))
    ok = bad = 0
    for f in t["fields"]:
        s = f["off"] // 4
        meth, np = mac_params(f["name"])
        entry = u32(wva + 4 * s)
        tgt, r = win_ret(entry)
        exp = 4 * np if np is not None else None
        flag = "ok" if (exp == r) else "MISMATCH"
        if flag == "ok":
            ok += 1
        else:
            bad += 1
        print("  %2d %-24s mac_params=%s exp_ret=%-3s win_ret=%-3s tgt=0x%08X %s" % (s, meth, np, exp, r, tgt, flag))
    print("  -> %d ok, %d mismatch" % (ok, bad))
