#!/usr/bin/env python3
"""Rough data-flow trace of the cIGZWinGrid pointer obtained at every 'push 0xDAA6B9BE' site.

For each site: find the out-pointer argument (&p, the push just before 'push iid'), then walk
forward tracking which registers hold p (loads of [loc]) and which hold p's vtable, and print each
'call [vt + X]' made THROUGH THE GRID VTABLE with its Mac slot name and the immediates pushed for it.
Calls through AsIGZWin's result (slot 5) are tagged 'WIN' (cIGZWin slots), not grid slots.

esp-relative locations are tracked with a push/pop/add/sub delta and a callee-pops heuristic, so a
stack-held pointer survives pushes between uses. It is a heuristic: read the disasm for anything
that matters (the script prints the VA of every call it attributes).

    python trace_grid_calls.py [--iid 0xDAA6B9BE] [--n 220]
"""
import argparse
import json
import re

import pe

GDT = r"C:\dev\SC4UIScale\tools\sdk\ghidra\out\SimCity4.gdt.json"
gnames = {}
for t in json.load(open(GDT))["types"]:
    if t["name"] == "vftable_cIGZWinGrid":
        for f in t["fields"]:
            gnames[f["off"]] = f["name"]
WIN = {0x8C: "GetChildWindowFromIDRecursive", 0x90: "GetChildAs", 0x94: "GetChildAsRecursive",
       0xA4: "GetW", 0xA8: "GetH", 0xC0: "GetArea", 0xCC: "SetW", 0xD0: "SetH", 0xD4: "SetSize",
       0xD8: "SetArea(rect&)", 0xDC: "SetArea(l,t,r,b)", 0xE0: "GZWinMoveTo", 0xE4: "GZWinOffset",
       0xFC: "GetID", 0x100: "SetID", 0x10C: "GetFlag", 0x110: "SetFlag", 0x114: "ShowWindow",
       0x118: "HideWindow", 0x158: "SetNotificationTarget", 0x1B0: "(color ctor? slot108)",
       0x1A8: "(slot106 fill colour)"}

ap = argparse.ArgumentParser()
ap.add_argument("--iid", default="0xDAA6B9BE")
ap.add_argument("--n", type=int, default=220)
ap.add_argument("--site", default=None)
a = ap.parse_args()
iid = int(a.iid, 0)

MEM = re.compile(r"^dword ptr \[(\w+)(?: ([+-]) (0x[0-9a-f]+|\d+))?\]$")


def parse_mem(op):
    m = MEM.match(op.strip())
    if not m:
        return None
    base = m.group(1)
    off = int(m.group(3), 0) if m.group(3) else 0
    if m.group(2) == "-":
        off = -off
    return base, off


def trace(site):
    pre = pe.dis(site - 0x40, 0x40 + 0x10)
    # align: find instruction starting exactly at site
    pre = [i for i in pre if i.address < site]
    # the push before 'push iid'
    loc = None
    pushreg = None
    for i in reversed(pre[-6:]):
        if i.mnemonic == "push":
            reg = i.op_str
            pushreg = reg
            # find lea reg, [X] before it
            for j in reversed([k for k in pre if k.address < i.address][-8:]):
                if j.mnemonic == "lea" and j.op_str.startswith(reg + ","):
                    loc = parse_mem("dword ptr " + j.op_str.split(",", 1)[1].strip())
                    break
                if j.mnemonic == "mov" and j.op_str.startswith(reg + ","):
                    break
            break
    if loc is None:
        return None, []
    base, off = loc
    esp_delta = 0  # bytes pushed since the lea (approx: lea happened ~1 push before)
    # the lea was computed before 'push &p' (+4) and 'push iid' (+4): start delta at +8 at site+5
    esp_delta = 8
    ins = pe.dis(site, 0x800)[: a.n]
    holders = {}   # reg -> 'P' (grid ptr) or 'V' (grid vtable) or 'W' (win ptr) or 'WV' or 'A' (&p)
    if pushreg in ("esi", "edi", "ebx", "ebp"):
        holders[pushreg] = "A"
    pending = []   # immediates pushed since last call
    pend_bytes = 0
    out = []
    last_call_ret_is_win = False
    for idx, i in enumerate(ins[1:]):
        mn, op = i.mnemonic, i.op_str
        # stack accounting
        if mn == "push":
            esp_delta += 4
            pend_bytes += 4
            pending.append(op)
        elif mn == "pop":
            esp_delta -= 4
            if pend_bytes:
                pend_bytes -= 4
                pending = pending[:-1]
            holders.pop(op, None)
        elif mn == "add" and op.startswith("esp,"):
            n = int(op.split(",")[1], 0)
            esp_delta -= n
            pend_bytes = max(0, pend_bytes - n)
        elif mn == "sub" and op.startswith("esp,"):
            esp_delta += int(op.split(",")[1], 0)
        if mn == "mov" and "," in op:
            dst, src = [x.strip() for x in op.split(",", 1)]
            pm = parse_mem(src)
            is_p = False
            if pm:
                sb, so = pm
                if sb == base and base != "esp" and so == off:
                    is_p = True
                if sb == "esp" and base == "esp" and so - esp_delta == off - 8 + 0 and False:
                    is_p = True
                if sb == "esp" and base == "esp" and (so - (esp_delta - 8)) == off:
                    is_p = True
                if sb in holders and so == 0 and holders[sb] == "A":
                    holders[dst] = "P"
                    continue
                if sb in holders and so == 0 and holders[sb] == "P":
                    holders[dst] = "V"
                    continue
                if sb in holders and so == 0 and holders[sb] == "W":
                    holders[dst] = "WV"
                    continue
            if is_p:
                holders[dst] = "P"
                continue
            if src in holders:
                holders[dst] = holders[src]
                continue
            holders.pop(dst, None)
        elif mn in ("lea", "xor", "sub", "add", "inc", "dec", "or", "and", "movzx", "movsx", "setne", "sete") and "," in op:
            dst = op.split(",")[0].strip()
            if not dst.startswith("esp"):
                holders.pop(dst, None)
        if mn == "call":
            pm = parse_mem(op)
            tag = None
            if pm and pm[0] in holders and holders[pm[0]] in ("V", "WV"):
                slot_off = pm[1]
                if holders[pm[0]] == "V":
                    tag = ("GRID", slot_off, gnames.get(slot_off, "?"))
                else:
                    tag = ("WIN", slot_off, WIN.get(slot_off, "slot %d" % (slot_off // 4)))
            imms = [p for p in pending]
            if tag:
                out.append((i.address, tag, imms))
                # AsIGZWin returns win ptr in eax
                if tag[0] == "GRID" and tag[1] == 0x14:
                    holders = {k: v for k, v in holders.items() if k not in ("eax", "ecx", "edx")}
                    holders["eax"] = "W"
                    pending, pend_bytes = [], 0
                    continue
            # callee pops (thiscall/stdcall) unless followed by add esp
            nxt = ins[idx + 2] if idx + 2 < len(ins) else None
            if not (nxt and nxt.mnemonic == "add" and nxt.op_str.startswith("esp,")):
                esp_delta -= pend_bytes
            pending, pend_bytes = [], 0
            for r in ("eax", "ecx", "edx"):
                holders.pop(r, None)
        if mn in ("ret", "retn", "jmp") and idx > 3 and mn != "jmp":
            break
    return loc, out


sites = pe.find_push_imm(iid)
if a.site:
    sites = [int(a.site, 0)]
for s in sites:
    loc, calls = trace(s)
    print("site %08X  &p=%s" % (s, loc))
    for ad, tag, imms in calls:
        kind, so, nm = tag
        print("    %08X  %-4s vt+0x%03X slot %3d %-30s args(pushed, last=first arg): %s"
              % (ad, kind, so, so // 4, nm, list(reversed(imms))))
