#!/usr/bin/env python3
"""Dump every slot of the cGZWinGrid cIGZWinGrid vtable (0xADD578) with the Mac name,
the ret-N arg count, the this-relative fields touched, and the first N instructions.

    python dump_slots.py [maxins] > slots.txt
"""
import json
import re
import sys

import pe

VT = 0xADD578
GDT = r"C:\dev\SC4UIScale\tools\sdk\ghidra\out\SimCity4.gdt.json"

maxins = int(sys.argv[1]) if len(sys.argv) > 1 else 80

names = {}
for t in json.load(open(GDT))["types"]:
    if t["name"] == "vftable_cIGZWinGrid":
        for f in t["fields"]:
            names[f["off"] // 4] = f["name"]

mem_re = re.compile(r"\[(e[a-d]x|e[sd]i|ebp)( [+-] (0x[0-9a-f]+|\d+))?\]")

for k in range(142):
    va = pe.u32(VT + 4 * k)
    ins = pe.func(va, 0x1800)
    rets = sorted({(int(i.op_str, 0) if i.op_str else 0) for i in ins if i.mnemonic == "ret"})
    offs = set()
    for i in ins:
        for m in mem_re.finditer(i.op_str):
            if m.group(3) and m.group(1) in ("ecx", "esi", "edi", "eax", "ebx", "edx"):
                offs.add(int(m.group(3), 0))
    print("=" * 78)
    print("slot %3d  +0x%03X  %-34s VA %08X  ret%s  n_ins=%d" % (k, 4 * k, names.get(k, "(beyond Mac)"), va, rets, len(ins)))
    print("   reg-rel offsets: " + " ".join("0x%X" % o for o in sorted(offs) if o >= 0x10))
    for i in ins[:maxins]:
        print("  %08X  %s %s" % (i.address, i.mnemonic, i.op_str))
    if len(ins) > maxins:
        print("  ... (%d more)" % (len(ins) - maxins))
