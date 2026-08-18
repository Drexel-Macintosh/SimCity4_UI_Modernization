"""wincensus.py - THE FIRST CENSUS OF CODE-CREATED WINDOWS (2026-08-03).

Closes the Q2 denominator blind spot: every coverage figure this project has
ever published ("96.6% of roots") counts only windows DECLARED IN A .UI
SCRIPT. Windows the game constructs in code are absent from that corpus by
definition, so they were absent from every denominator. This builds the
missing half, offline, from the exe only.

------------------------------------------------------------------------
HOW A WINDOW IS BORN IN THIS ENGINE (measured, not assumed)
------------------------------------------------------------------------
Every window object is heap-allocated by the SAME idiom:

    push  <objSize>
    call  0x005E55E0            ; operator new
    test  eax,eax / pop ecx / je fail
    mov   ecx,eax
    call|jmp <CTOR>             ; ctor installs the class vtable at [obj+0]

There are then exactly TWO ways that idiom is reached:

  ROUTE A - via GZCOM.  A registered class factory is a 50-byte thunk that
    does nothing but the idiom above. Callers reach it through
        call 0x0090DDF1                ; GZCOM()
        push <ppv> ; push <iid> ; push <clsid> ; call [reg+0x0C]
    where [reg+0x0C] is cIGZCOM::GetClassObject.
    MEASURED EXEMPLAR: 0x007EF029 creates clsid 0xCA5D3294
    (cSC4WinAlertBorder), then SetArea(0,0,parentW,parentH),
    then `push 0x6a5e44b6 ; call [eax+0x100]` (SetID) at 0x007EF071.

  ROUTE B - direct `new` + ctor inline in the caller (no clsid anywhere).
    The unregistered window classes (cSC4View3DWin, cSC4WinRegionScreen,
    cSC4WinRegionView, the tooltip layer, the flyout container/strip, ...)
    exist ONLY on this route.

------------------------------------------------------------------------
HOW SCRIPT-DRIVEN WINDOWS ARE SUBTRACTED (mechanical, not judgemental)
------------------------------------------------------------------------
The .UI deserializer creates windows through the SAME GetClassObject call,
but the clsid comes from the PARSED SCRIPT NODE, never from an immediate:
    0x00957B5D  in sub_957A9B   clsid = dword ptr [ecx+0x10]
So: a LITERAL clsid push means the CODE named the class => code-created.
A register/memory clsid means the DATA named the class => script-created.
The subtraction is a property of the instruction encoding, not an opinion.

Independent second check: of the 64 distinct window ids set by a literal
`SetID` in .text, 63 appear in ZERO of the 330 extracted .UI scripts.
POSITIVE CONTROL for that scan: the same scan finds 0x6BB92BCB in
I-abb0120f, 0x0987B48F in two scripts, 0x6A414973 in I-2a41436b - so the
empty result is a MEASURED null, not a structural one.

------------------------------------------------------------------------
INSTRUMENTS AND THEIR POSITIVE CONTROLS (state them or the null is worthless)
------------------------------------------------------------------------
1. WINDOW-CLASS VTABLE DETECTOR. A cIGZWin-derived vtable inherits base
   implementations at fixed slots: vt+0xA0 GetChildWindowFromCursorPoint
   0x0099DFA9, +0xA4 GetW 0x0099C81B, +0xA8 GetH 0x0099C82A, +0xAC GetL
   0x0099BC53, +0xB0/+0xC0 GetArea 0x00994EE4/0x0099BCE1, +0xF8 IsPointInMe
   0x0099C97C, +0x15C GZPaint 0x0099BE4C. Require >= 3 markers at the exact
   relative offsets.
   CONTROL: all 12 window vtables independently named in SC4-UI-ENGINE.md
   (0xADF6A0 GZWinBMP, 0xADDAF0 button, 0xAB8628 RCI, 0xABA430 TrendBar,
   0xAB7358 GenTransparent, 0xADFEB8 cGZWinText, 0xAB9658, 0xAB5B48,
   0xAB58B0, 0xAB6AA8, 0xAB6D88, 0xAB6770) are found. Zero of the 111
   detected vtables override GetW, so the detector has no known blind spot
   inside its own class family. RESULT: 111 window-class vtables.

2. DISASSEMBLY SWEEP. Per FUNCTION using funcs.json boundaries, never one
   linear pass: a single linear capstone sweep of .text dies at the first
   non-code byte and yielded 37,426 instructions instead of 2,400,456 -
   and reported ZERO route-A sites. That false null is why every scan here
   carries a control.
   CONTROL: route A must find 0x007EF02E (the AlertBorder push).

3. LITERAL SetID SCAN (`push imm32 ; call [reg+0x100]`).
   CONTROL: must find 0x6A5E44B6 at 0x007EF071.

------------------------------------------------------------------------
WHAT THIS CENSUS CANNOT SEE (stated, not hidden)
------------------------------------------------------------------------
 - A window allocated by an allocator other than 0x005E55E0 (none found,
   but not proven absent), or placement-constructed inside a larger object.
 - A creation site whose ctor is reached through a virtual call or a
   function-pointer table rather than a direct call/jmp.
 - The window's PARENT. Nothing here proves which subtree an instance is
   added to; that needs the live tree (VWKID/MWKID dumps).
 - How many INSTANCES exist at runtime. One site in a loop makes many.
 - Third-party DLL plugins, which create their own windows at runtime.

Usage:
    python wincensus.py            # writes _work/wincensus.json + a summary
"""
import collections
import json
import os
import re
import struct
import sys

import common as C

NEW = 0x5E55E0            # operator new
REG_CALLEE = 0x90E133     # COM class-factory registration callee
GZCOM = 0x90DDF1          # GZCOM() getter

# base cIGZWin implementations -> their vtable offsets (see docstring)
MARKS = {0x99DFA9: 0xA0, 0x99C81B: 0xA4, 0x99C82A: 0xA8, 0x99BC53: 0xAC,
         0x994EE4: 0xB0, 0x99BCE1: 0xC0, 0x99C97C: 0xF8, 0x99BE4C: 0x15C}
CONTROL_VTABLES = [0xADF6A0, 0xADDAF0, 0xAB8628, 0xABA430, 0xAB7358, 0xADFEB8,
                   0xAB9658, 0xAB5B48, 0xAB58B0, 0xAB6AA8, 0xAB6D88, 0xAB6770]


def window_vtables():
    d = C.exe_bytes()
    votes = collections.Counter()
    for fn, off in MARKS.items():
        t = struct.pack("<I", fn)
        i = d.find(t)
        while i != -1:
            va = i + C.IMAGE_BASE
            if va % 4 == 0:
                votes[va - off] += 1
            i = d.find(t, i + 1)
    return set(k for k, v in votes.items() if v >= 3)


def const_ret(m, va):
    """sub_va == `mov eax,imm32 ; ret` -> imm32 (a GetClassID thunk)."""
    try:
        ins = list(m.disasm(C.rd(va, 32), va))
    except Exception:
        return None
    val = None
    for i in ins[:6]:
        if i.mnemonic == "mov" and i.op_str.startswith("eax, 0x"):
            val = int(i.op_str.split(", ")[1], 16)
        elif i.mnemonic == "ret":
            return val
        elif i.mnemonic not in ("push", "nop"):
            if val is None:
                return None
    return val


def registrations(m, fm, edges):
    """{clsid: factoryVA} from every `call 0x90E133` site.

    Two encodings, both handled:
      push <factory> ; push <clsid>      ; mov ecx,X ; call
      push <factory> ; call <GetClassID> ; push eax  ; mov ecx,X ; call
    """
    sites = sorted(s for s, t, k in edges if t == REG_CALLEE and k == "call")
    by_owner = collections.defaultdict(list)
    for s in sites:
        by_owner[fm.owner(s)].append(s)
    out = {}
    unresolved = 0
    for o, ss in sorted(by_owner.items()):
        e = fm.end(o)
        try:
            ins = list(m.disasm(C.rd(o, e - o), o))
        except Exception:
            unresolved += len(ss)
            continue
        idx = {i.address: n for n, i in enumerate(ins)}
        for s in ss:
            n = idx.get(s)
            if n is None:
                unresolved += 1
                continue
            toks = list(reversed(ins[max(0, n - 6):n]))
            imms = []
            for i in toks:
                if i.mnemonic == "push" and i.op_str.startswith("0x"):
                    imms.append(int(i.op_str, 16))
                    if len(imms) == 2:
                        break
                elif i.mnemonic == "call":
                    break
            if len(imms) == 2:
                # A clsid can be registered by MORE THAN ONE factory
                # (0x2AC45173 has 0x4661F0 and 0x998B77). Keeping only the
                # first silently dropped 2 window classes from an earlier run
                # of this file - collect them all.
                out.setdefault(imms[0], set()).add(imms[1])
                continue
            g = f = None
            for i in toks:
                if i.mnemonic == "call" and i.op_str.startswith("0x"):
                    g = int(i.op_str, 16)
                    break
            for i in toks:
                if i.mnemonic == "push" and i.op_str.startswith("0x"):
                    f = int(i.op_str, 16)
                    break
            c = const_ret(m, g) if g else None
            if c is not None:
                out.setdefault(c, set()).add(f)
            else:
                unresolved += 1
    return out, len(sites), unresolved


def make_ctor_vt(m, winvt):
    cache = {}

    def ctor_vt(f, depth=0):
        """Vtable a ctor installs at [reg+0]: the LAST such store in the body
        (C++ writes the base vtable first, the derived one last). Follows a
        tail `jmp` when the thunk itself stores nothing."""
        if not C.va_ok(f):
            return None
        if depth == 0 and f in cache:
            return cache[f]
        if depth > 3:
            return None
        last = tail = None
        try:
            ins = list(m.disasm(C.rd(f, 0x600), f))
        except Exception:
            ins = []
        for i in ins[:220]:
            if (i.mnemonic == "mov" and i.op_str.startswith("dword ptr [")
                    and ", 0x" in i.op_str):
                lhs = i.op_str.split(",")[0]
                try:
                    v = int(i.op_str.rsplit(", ", 1)[1], 16)
                except ValueError:
                    v = None
                if v in winvt and "+" not in lhs:
                    last = v
            elif i.mnemonic == "jmp" and i.op_str.startswith("0x") and last is None:
                tail = int(i.op_str, 16)
                break
            elif i.mnemonic == "ret":
                break
        if last is None and tail is not None:
            last = ctor_vt(tail, depth + 1)
        if depth == 0:
            cache[f] = last
        return last
    return ctor_vt


def factory_ctor(m, f):
    """A registered factory is a 50-byte thunk:
        push <size> ; call 0x5E55E0 ; test/pop/je ; mov ecx,eax ; jmp|call <CTOR>
    Return CTOR. Some thunks CALL the ctor instead of tail-jumping to it, so
    both encodings are accepted (0x7941C0 AlertBorder and 0x9B1E0A GZWinBtn
    are the two that a jmp-only reader silently drops - which is how the first
    run of this file reported 32 window classes instead of 66)."""
    try:
        ins = list(m.disasm(C.rd(f, 0x60), f))
    except Exception:
        return None
    for i in ins[:14]:
        if i.mnemonic in ("jmp", "call") and i.op_str.startswith("0x"):
            t = int(i.op_str, 16)
            if t == NEW:
                continue
            return t
        if i.mnemonic == "ret":
            break
    return None


def alloc_sites(m, fm, edges, ctor_vt):
    """ROUTE B: every `new` that constructs a window."""
    rows = []
    for s in sorted(x for x, t, k in edges if t == NEW):
        o = fm.owner(s)
        if o is None:
            continue
        try:
            ins = list(m.disasm(C.rd(s, 0x60), s))
        except Exception:
            continue
        size = None
        lo = max(o, s - 0x20)
        try:
            pre = list(m.disasm(C.rd(lo, s - lo), lo))
            for i in reversed(pre[-4:]):
                if i.mnemonic == "push" and i.op_str.startswith("0x"):
                    size = int(i.op_str, 16)
                    break
        except Exception:
            pass
        ctor = None
        for i in ins[1:10]:
            if i.mnemonic in ("call", "jmp") and i.op_str.startswith("0x"):
                ctor = int(i.op_str, 16)
                break
            if i.mnemonic == "ret":
                break
        vt = ctor_vt(ctor) if ctor else None
        if vt:
            rows.append({"newsite": s, "owner": o, "size": size,
                         "ctor": ctor, "vt": vt})
    return rows


def sweep(m, fm, want_suffix, back, pred):
    """Per-function scan for `call [reg+<suffix>]` preceded by a push."""
    hits = []
    for o in fm.starts:
        e = min(fm.end(o), o + 0x8000)
        if e <= o:
            continue
        try:
            ins = list(m.disasm(C.rd(o, e - o), o))
        except Exception:
            continue
        for n, i in enumerate(ins):
            if i.mnemonic != "call" or "ptr [" not in i.op_str:
                continue
            if not i.op_str.rstrip().endswith(want_suffix):
                continue
            for j in range(n - 1, max(-1, n - back), -1):
                p = ins[j]
                if p.mnemonic == "push" and p.op_str.startswith("0x"):
                    v = int(p.op_str, 16)
                    if pred(v):
                        hits.append({"call": i.address, "push": p.address,
                                     "value": v, "owner": o})
                    break
                if p.mnemonic == "call":
                    break
    return hits


def class_names():
    """clsid -> name, from GZCLSIDDefs.h plus the exe's own .data registry."""
    names = {}
    hdr = os.path.join(os.path.dirname(C.HERE), "..", "vendor", "gzcom-dll",
                       "gzcom-dll", "include", "GZCLSIDDefs.h")
    hdr = os.path.normpath(hdr)
    if os.path.exists(hdr):
        with open(hdr, "r", encoding="utf-8", errors="replace") as f:
            for mm in re.finditer(r"k(\w+)\s*=\s*(0x[0-9A-Fa-f]+);", f.read()):
                names[int(mm.group(2), 16) & 0xFFFFFFFF] = mm.group(1)
    va = 0xB08F78                       # {clsid -> char* name}, 8-byte stride
    for i in range(400):
        a = va + i * 8
        cls, p = C.dw(a), C.dw(a + 4)
        if p is None or not (0x400000 <= p < 0xC00000):
            break
        s = C.rd(p, 64).split(b"\0")[0].decode("latin1", "replace")
        if not s:
            break
        names.setdefault(cls, s)
    return names


def main():
    m = C.md()
    fm = C.FuncMap()
    edges = C.jload(os.path.join(C.WORK, "edges.json"))
    if edges is None:
        raise SystemExit("_work/edges.json missing - run scan_text.py first")

    winvt = window_vtables()
    missing = [v for v in CONTROL_VTABLES if v not in winvt]
    print("[1] window-class vtables: %d   CONTROL %d/%d known vtables found%s"
          % (len(winvt), len(CONTROL_VTABLES) - len(missing),
             len(CONTROL_VTABLES),
             "" if not missing else "  *** MISSING %s ***"
             % [hex(x) for x in missing]))

    ctor_vt = make_ctor_vt(m, winvt)
    reg, nreg, unres = registrations(m, fm, edges)
    wincls = {}
    for clsid, facs in reg.items():
        for fac in sorted(facs):
            ctor = factory_ctor(m, fac)
            vt = ctor_vt(ctor) if ctor else None
            if vt:
                wincls[clsid] = {"factory": fac, "ctor": ctor, "vt": vt}
                break
    print("[2] COM class registrations: %d sites, %d clsids (%d unresolved); "
          "window-producing clsids: %d" % (nreg, len(reg), unres, len(wincls)))

    A = sweep(m, fm, "+ 0xc]", 8, lambda v: v in wincls)
    ok = any(h["push"] == 0x7EF02E for h in A)
    print("[3] ROUTE A (GetClassObject, LITERAL window clsid): %d sites   "
          "CONTROL 0x7EF02E %s" % (len(A), "FOUND" if ok else "*** MISSING ***"))

    B = alloc_sites(m, fm, edges, ctor_vt)
    facs = set(v["factory"] for v in wincls.values())
    thunk = [r for r in B if any(0 < r["newsite"] - f <= 0x10 for f in facs)]
    direct = [r for r in B if r not in thunk]
    print("[4] ROUTE B (`new` + window ctor): %d sites = %d factory thunks "
          "+ %d DIRECT in code" % (len(B), len(thunk), len(direct)))

    S = sweep(m, fm, "+ 0x100]", 4, lambda v: True)
    ok = any(h["value"] == 0x6A5E44B6 and h["push"] == 0x7EF071 for h in S)
    print("[5] literal SetID sites: %d, distinct ids %d   CONTROL 0x6A5E44B6 "
          "@0x7EF071 %s" % (len(S), len(set(h["value"] for h in S)),
                            "FOUND" if ok else "*** MISSING ***"))

    names = class_names()
    out = {
        "exe": C.EXE, "exeSha256_16": C.exe_fingerprint()[0],
        "windowVtables": sorted(winvt),
        "windowClasses": {"0x%08X" % k: {"name": names.get(k, "?"),
                                         "factory": "0x%X" % v["factory"],
                                         "ctor": "0x%X" % v["ctor"],
                                         "vt": "0x%X" % v["vt"]}
                          for k, v in sorted(wincls.items())},
        "routeA": A, "routeB_direct": direct, "routeB_factoryThunks": thunk,
        "setIds": S,
    }
    p = os.path.join(C.ensure_work(), "wincensus.json")
    C.jdump(p, out)
    print("wrote %s" % p)


if __name__ == "__main__":
    main()
