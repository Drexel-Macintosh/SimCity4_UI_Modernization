r"""One table for an upstream issue: every cIGZWin declaration's compiled slot
against its exe slot, with the exe slot's evidence.

    python tools\sdk\ghidra\verify\I-issue-evidence\consolidate_cigzwin.py

Sources, all committed next door:
  A-full-probe\slots.json    compiled slot of all 147 declarations (MSVC,
                             read two ways), plus exe slots decoded or
                             established for 43 of them
  B-second-class-exe-decode\slot_table.json
                             59 exe slots decoded from the code of 15 window
                             classes, each with its semantics and a verdict
                             against the Mac name at that slot

A declaration's exe slot is A's value when A has one. Otherwise it is the Mac
slot, but only where B decoded that exe slot and B's verdict agrees with the
Mac name. Anything else is UNDECODED: the issue makes no claim about it.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
V = os.path.dirname(HERE)
A = json.load(open(os.path.join(V, "A-full-probe", "slots.json")))["rows"]
BJ = {int(k): v for k, v in json.load(open(os.path.join(V, "B-second-class-exe-decode", "slot_table.json"))).items()}
B = {}
with open(os.path.join(V, "B-second-class-exe-decode", "slot_table.tsv"), encoding="utf-8") as f:
    head = f.readline().rstrip("\n").split("\t")
    for line in f:
        c = line.rstrip("\n").split("\t")
        if c and c[0].isdigit():
            # the last three columns are semantics, verdict, confidence
            B[int(c[0])] = dict(mac=c[2], sem=c[-3], verdict=c[-2], conf=c[-1], ret=BJ.get(int(c[0]), {}).get("ret"))


def b_agrees(slot):
    v = B.get(slot)
    return v is not None and v["verdict"].lower().startswith("agree")


# The gate's table: each row decoded from the exe function's own body. Read
# as data (the gate runs its checks when imported).
import ast
_gate_src = open(os.path.join(V, "..", "..", "..", "..", "_tests", "Test-GZWinHeaderSlots.py"), encoding="utf-8").read()
GATE = next(ast.literal_eval(n.value) for n in ast.parse(_gate_src).body
            if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "EXE_SLOT")
names = [r["name"] for r in A]

# Stack bytes a thiscall callee pops for these argument types (x86).
BYVAL = {"cRZRect": 16, "cRZPoint": 8, "cRZColor": 4, "int64_t": 8, "uint64_t": 8, "double": 8}


def arg_bytes(sig):
    inner = sig[sig.index("(") + 1:sig.rindex(")")].strip()
    if inner in ("", "void"):
        return 0
    total = 0
    for a in inner.split(","):
        a = a.strip()
        if "&" in a or "*" in a:
            total += 4
        else:
            total += BYVAL.get(a.replace("const", "").strip(), 4)
    return total


rows = []
for r in A:
    exe, src = r["exe"], r["exe_src"]
    mac = r["mac"]
    if exe is None and mac is not None and r.get("mac_count", 1) == 1 and b_agrees(mac):
        exe, src = mac, "B-decoded"
    if exe is None and names.count(r["name"]) == 1 and r["name"] in GATE:
        exe, src = GATE[r["name"]], "gate"
    ret = B.get(exe, {}).get("ret") if exe is not None else None
    rows.append(dict(hidx=r["hidx"], sig=r["sig"], compiled=r["compiled"], pm=r["compiled_pm"],
                     exe=exe, src=src, hdr_bytes=arg_bytes(r["sig"]), exe_ret=ret))

wrong = [x for x in rows if x["exe"] is not None and x["exe"] != x["compiled"]]
right = [x for x in rows if x["exe"] is not None and x["exe"] == x["compiled"]]
undec = [x for x in rows if x["exe"] is None]
two_ways = all(x["compiled"] == x["pm"] for x in rows)
print("147 declarations: %d decoded against the exe (%d wrong, %d right), %d undecoded"
      % (len(wrong) + len(right), len(wrong), len(right), len(undec)))
print("compiled slot read two ways (call site, member-pointer thunk) agree on every row: %s" % two_ways)
print("\nWRONG (header hidx: declaration -> compiles to / exe slot [evidence]):")
for x in wrong:
    print("  %3d  %-58s %3d / %3d  [%s]" % (x["hidx"], x["sig"][:58], x["compiled"], x["exe"], x["src"]))
print("\nUNDECODED hidx: %s" % ", ".join(str(x["hidx"]) for x in undec))
abi = [x for x in rows if x["exe_ret"] is not None and x["exe_ret"] != x["hdr_bytes"]]
print("\nARGUMENT BYTES: header vs the exe function's own `ret N` (%d decoded rows carry a ret):"
      % sum(1 for x in rows if x["exe_ret"] is not None))
for x in abi:
    print("  %3d  %-58s header pushes %2d, exe pops %2d" % (x["hidx"], x["sig"][:58], x["hdr_bytes"], x["exe_ret"]))
json.dump(dict(wrong=wrong, right=right, undecoded=undec),
          open(os.path.join(HERE, "cigzwin_consolidated.json"), "w"), indent=1)
sys.exit(0)
