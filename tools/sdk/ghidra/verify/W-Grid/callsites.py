#!/usr/bin/env python3
"""List every 'push 0xDAA6B9BE' (cIGZWinGrid IID) site in SimCity 4.exe, the call that consumes
it (GetChildAs vt+0x90 / GetChildAsRecursive vt+0x94 / QueryInterface vt+0 / other), and the
vtable offsets called afterwards (a rough trace of the obtained grid pointer's slot use).

Positive control: run with --iid 0xC2AFA76F and the FlatRect sites 0x47B993 / 0x4861D7 appear.
"""
import argparse
import json
import re

import pe

GDT = r"C:\dev\SC4UIScale\tools\sdk\ghidra\out\SimCity4.gdt.json"
names = {}
for t in json.load(open(GDT))["types"]:
    if t["name"] == "vftable_cIGZWinGrid":
        for f in t["fields"]:
            names[f["off"]] = f["name"]

ap = argparse.ArgumentParser()
ap.add_argument("--iid", default="0xDAA6B9BE")
ap.add_argument("--after", type=int, default=90)
ap.add_argument("-v", action="store_true")
a = ap.parse_args()
iid = int(a.iid, 0)

sites = pe.find_push_imm(iid)
call_re = re.compile(r"dword ptr \[(e[a-d]x|e[sd]i|ebx|ebp)( \+ (0x[0-9a-f]+))?\]")
for s in sites:
    ins = pe.dis(s, 0x300)[: a.after]
    consumer = None
    later = []
    for i in ins[1:]:
        if i.mnemonic == "call":
            m = call_re.search(i.op_str)
            off = int(m.group(3), 16) if (m and m.group(3)) else (0 if m else None)
            if consumer is None:
                consumer = (i.address, i.op_str, off)
                continue
            if off is not None:
                later.append((i.address, off))
            else:
                later.append((i.address, i.op_str))
    kind = {0x90: "GetChildAs", 0x94: "GetChildAsRecursive", 0: "QueryInterface"}.get(consumer[2] if consumer else None, "?")
    print("push@%08X  consumer %08X call %-28s => %s" % (s, consumer[0], consumer[1], kind))
    if a.v:
        for ad, off in later[:14]:
            if isinstance(off, int):
                print("      %08X  vt+0x%03X  %s" % (ad, off, names.get(off, "")))
            else:
                print("      %08X  %s" % (ad, off))
