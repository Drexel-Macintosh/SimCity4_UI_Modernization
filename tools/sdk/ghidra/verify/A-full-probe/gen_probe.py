#!/usr/bin/env python
"""UNIT A-full-probe: measure the COMPILED vtable slot of EVERY virtual in the
vendored gzcom-dll cIGZWin.h (+ the 3 cIGZUnknown base slots).

Two instruments, both read from MSVC's own /FAs listing of one generated TU:
  I1  call-site probe  : extern "C" probe_<Name>_<k>(cIGZWin* w) { w->Name(args); }
                         args synthesised (refs -> *(T*)0, ptrs/scalars -> (T)0,
                         enums/typedefs -> (cIGZWin::T)0). Slot = N/4 of the first
                         'call|jmp DWORD PTR [e??+N]' after the PROC line.
  I2  member-pointer   : a global initialised with
                         static_cast<exact signature>(&cIGZWin::Name). MSVC emits a
                         vcall thunk '??_9cIGZWin@$B...' whose listing header says
                         `vcall'{OFFSET,{flat}}'. Slot = OFFSET/4. This selects the
                         overload by EXACT SIGNATURE, not by argument synthesis, so it
                         independently checks that I1 bound the overload intended.
Then joins: header textual index, Mac slot (vftable_cIGZWin in SimCity4.gdt.json,
name + k-th occurrence), known-exe slot (established 2026-09-23).

Never executed - compile only (cl /c). Writes into this folder only.
"""
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))
INC = os.path.join(ROOT, "vendor", "gzcom-dll", "gzcom-dll", "include")
HDR = os.path.join(INC, "cIGZWin.h")
BASE_HDR = os.path.join(INC, "cIGZUnknown.h")
GDT = os.path.join(ROOT, "tools", "sdk", "ghidra", "out", "SimCity4.gdt.json")
VCVARS = r"C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars32.bat"

NESTED = {"tWinFlag", "EnumChildrenCallback", "SortChildrenCallback", "EnumParamsCallback"}
ENUMS = {"tWinFlag"}

# Known Windows exe slots, MEASURED 2026-09-23 from cSC4WinAlertBorder vtable
# 0x00AB5B48 (SimCity 4.exe 1.1.641). Key = (name, header ordinal).
EXE = {
    ("GetChildWindowFromIDRecursive", 1): 35, ("GetChildAs", 1): 36,
    ("GetChildAsRecursive", 1): 37, ("GetW", 1): 41, ("GetH", 1): 42,
    ("GetArea", 2): 48,                       # GetArea() returning int32* {l,t,r,b}
    ("SetW", 1): 51, ("SetH", 1): 52,
    ("SetSize", 1): 53,                       # SetSize(w,h)
    ("SetArea", 1): 54,                       # SetArea(const cRZRect&)
    ("SetArea", 2): 55,                       # SetArea(l,t,r,b)
    ("GZWinMoveTo", 1): 56, ("FitRectToWindow", 1): 58, ("GetID", 1): 63,
    ("SetID", 1): 64, ("GetFlag", 1): 67, ("SetFlag", 1): 68,
    ("ShowWindow", 1): 69, ("HideWindow", 1): 70,
    ("SetNotificationTarget", 1): 86, ("GetNotificationTarget", 1): 87,
    ("GZPaint", 1): 88,
    ("SetSize", 2): 118,                      # SetSize(const cRZPoint&)
    ("CenterWindowInRect", 1): 119,           # (const cRZRect&)
    ("CenterWindowInRect", 2): 120,           # (cRZRect*) - null-tests its arg
    ("PlotPresent", 1): 124,
}
# Overload-group slots DECODED THIS SESSION (exe_overloads.py -> exe_overloads.txt),
# each told apart by its own code: ret N (args) + what it does with them.
EXE_DECODED = {
    ("ChildExists", 2): 19,        # (uint32_t): walks children comparing child->GetID() (vt+0xFC)
    ("ChildExists", 1): 20,        # (cIGZWin*): pointer lookup via [this+4]->vt+0x60
    ("ChildToFront", 2): 25,       # (uint32_t): GetChildWindowFromID(id) (vt+0x88) then vt+0x68
    ("ChildToFront", 1): 26,       # (cIGZWin*)
    ("GetArea", 1): 47,            # (cRZRect&): copies [this+0xA8..0xB4] to *arg, ret 4
    ("GetAreaAbsolute", 1): 49,    # (cRZRect&): copies [this+0x14..] to *arg, ret 4
    ("GetAreaAbsolute", 2): 50,    # (): lea eax,[this+0x14]; ret
    ("GetFillColor", 1): 102,      # (cRZColor&): *arg = [this+0xD4]; al=1; ret 4
    ("GetFillColor", 2): 103,      # (): converts [this+0xD4] bytes to native, ret 0
    ("GetFillColor", 3): 104,      # (r&,g&,b&): three byte stores, ret 0xC
    ("SetFillColor", 1): 105,      # (color): [this+0xD4] = arg VALUE (no deref!), al=1, ret 4
    ("SetFillColor", 2): 106,      # (uint32_t native): native->rgb, then vt+0x1AC (r,g,b), ret 4
    ("SetFillColor", 3): 107,      # (r,g,b): packs r<<16|g<<8|b into [this+0xD4], ret 0xC
    ("SendMsg", 2): 144,           # (win,type,d1,d2,d3): builds a msg, calls vt+0x244, ret 0x14
    ("SendMsg", 1): 145,           # (win, const cGZMessage&): win->DoMessage(msg), ret 8
    ("PostMsg", 2): 146,           # (win,type,d1,d2,d3): builds a msg, calls vt+0x24C, ret 0x14
    ("PostMsg", 1): 147,           # (win, const cGZMessage&): [this+4]->vt+0x3C(win,msg), ret 8
}


def strip_comments(s):
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
    return re.sub(r"//[^\n]*", "", s)


def split_args(a):
    a = a.strip()
    if a in ("", "void"):
        return []
    return [x.strip() for x in a.split(",")]


def arg_type(arg):
    arg = arg.split("=")[0].strip()
    toks = re.findall(r"[A-Za-z_]\w*|[*&]", arg)
    if len(toks) > 1 and re.match(r"[A-Za-z_]", toks[-1]) and toks[-1] != "const":
        toks = toks[:-1]
    return toks


def qual(tok):
    return "cIGZWin::" + tok if tok in NESTED else tok


def type_str(toks):
    out = ""
    for t in toks:
        if t in "*&":
            out += t
        else:
            out += (" " if out and out[-1] not in "" else "") + qual(t)
    return out.strip()


def synth(toks):
    """Argument expression per the unit's scheme."""
    core = [t for t in toks if t != "const"]
    if core and core[-1] == "&":
        base = type_str(core[:-1])
        return f"*({base}*)0"
    return f"({type_str(core)})0"


def parse(path, cls):
    src = strip_comments(open(path, encoding="latin-1").read())
    m = re.search(r"class\s+" + cls + r"\b[^{;]*\{", src)
    body = src[m.end():]
    decls = []
    for d in re.finditer(r"virtual\s+([^;{}]+?)\s*\(([^()]*)\)\s*(const)?\s*=\s*0\s*;", body):
        head, args, cst = d.group(1), d.group(2), bool(d.group(3))
        hm = re.match(r"(.*?)([A-Za-z_]\w*)$", head.strip(), re.S)
        ret, name = hm.group(1).strip(), hm.group(2)
        at = [arg_type(a) for a in split_args(args)]
        decls.append(dict(name=name, ret=ret, args=at, const=cst,
                          argtext=re.sub(r"\s+", " ", args.strip())))
    return decls


def main():
    base = parse(BASE_HDR, "cIGZUnknown")
    win = parse(HDR, "cIGZWin")
    allv = [dict(d, origin="cIGZUnknown") for d in base] + [dict(d, origin="cIGZWin") for d in win]
    seen = {}
    for i, d in enumerate(allv):
        seen[d["name"]] = seen.get(d["name"], 0) + 1
        d["k"] = seen[d["name"]]
        d["hidx"] = i
        d["tag"] = f'{d["name"]}_{d["k"]}'
        d["sig"] = (f'{d["ret"]} {d["name"]}({", ".join(type_str(a) for a in d["args"])})'
                    + (" const" if d["const"] else ""))
    counts = seen

    # ---- generate the TU --------------------------------------------------
    L = ['// GENERATED by gen_probe.py - compile-only probe of the vendored cIGZWin.h',
         '#include "cIGZWin.h"', '']
    for d in allv:
        a = ", ".join(synth(t) for t in d["args"])
        L.append(f'extern "C" void __cdecl probe_{d["tag"]}(cIGZWin* w) {{ w->{d["name"]}({a}); }}')
    L.append('')
    for d in allv:
        ret = type_str(re.findall(r"[A-Za-z_]\w*|[*&]", d["ret"]))
        params = ", ".join(type_str(t) for t in d["args"])
        cst = " const" if d["const"] else ""
        L.append(f'typedef {ret} (cIGZWin::*PM_{d["tag"]})({params}){cst};')
        L.append(f'extern "C" PM_{d["tag"]} volatile pm_{d["tag"]} = '
                 f'static_cast<PM_{d["tag"]}>(&cIGZWin::{d["name"]});')
    cpp = os.path.join(HERE, "allprobe.cpp")
    open(cpp, "w", newline="\n").write("\n".join(L) + "\n")

    cmd = os.path.join(HERE, "build.cmd")
    open(cmd, "w", newline="\r\n").write(
        "@echo off\n"
        f'call "{VCVARS}" >nul\n'
        f'cd /d "{HERE}"\n'
        f'cl /nologo /c /O2 /FAs /I"{INC}" allprobe.cpp > build.log 2>&1\n'
        "echo EXIT=%ERRORLEVEL% >> build.log\n")
    asm = os.path.join(HERE, "allprobe.asm")
    if os.path.exists(asm):
        os.remove(asm)
    subprocess.run(["cmd", "/c", cmd], cwd=HERE)
    if not os.path.exists(asm):
        print(open(os.path.join(HERE, "build.log")).read())
        sys.exit("FAIL: probe did not compile")

    # ---- read slots out of the listing -------------------------------------
    i1, i2, thunk_of = {}, {}, {}
    cur = None
    lines = open(asm, encoding="latin-1").read().splitlines()
    for ln in lines:
        m = re.match(r"_probe_(\w+)\s+PROC", ln)
        if m:
            cur = m.group(1)
            continue
        if cur:
            if re.match(r"_probe_\w+\s+ENDP", ln):
                cur = None
                continue
            m = re.search(r"\b(call|jmp)\s+DWORD PTR \[(e\w\w)(?:\+(\d+))?\]", ln)
            if m:
                i1[cur] = int(m.group(3) or 0) // 4
                cur = None
    # thunk bodies: "??_9cIGZWin@@$B..@AE PROC ; cIGZWin::`vcall'{OFF}', COMDAT"
    # then "jmp DWORD PTR [eax+OFF]". Both must agree or the thunk is not counted.
    tcur = None
    for ln in lines:
        m = re.match(r"(\?\?_9cIGZ\w+@@\S+)\s+PROC\s*;.*`vcall'\{(\d+)[,}]", ln)
        if m:
            tcur = (m.group(1), int(m.group(2)))
            continue
        if tcur:
            m = re.search(r"\bjmp\s+DWORD PTR \[e\w\w(?:\+(\d+))?\]", ln)
            if m:
                body = int(m.group(1) or 0)
                if body == tcur[1]:
                    thunk_of[tcur[0]] = body // 4
                else:
                    print(f"THUNK MISMATCH {tcur} body {body}")
                tcur = None
    # which thunk each pm_ global points at: "_pm_X DD FLAT:??_9..."
    for ln in lines:
        m = re.match(r"_pm_(\w+)\s+DD\s+FLAT:(\S+)", ln)
        if m and m.group(2) in thunk_of:
            i2[m.group(1)] = thunk_of[m.group(2)]

    # ---- Mac --------------------------------------------------------------
    mac = {}
    g = json.load(open(GDT, encoding="utf-8"))
    vt = next(t for t in g["types"] if t.get("name") == "vftable_cIGZWin")
    occ = {}
    for f in vt["fields"]:
        n = f["name"]
        occ[n] = occ.get(n, 0) + 1
        mac[(n, occ[n])] = f["off"] // 4
    mac_names = {n for (n, _) in mac}
    hdr_names = {d["name"] for d in allv}

    rows = []
    for d in allv:
        key = (d["name"], d["k"])
        rows.append(dict(
            hidx=d["hidx"], name=d["name"], k=d["k"], overloads=counts[d["name"]],
            sig=d["sig"], compiled=i1.get(d["tag"]), compiled_pm=i2.get(d["tag"]),
            mac=mac.get(key), mac_count=occ.get(d["name"], 0),
            exe=EXE.get(key, EXE_DECODED.get(key)),
            exe_src=("established" if key in EXE else "decoded" if key in EXE_DECODED else None)))
    json.dump(dict(rows=rows,
                   mac_only=sorted(mac_names - hdr_names),
                   header_only=sorted(hdr_names - mac_names)),
              open(os.path.join(HERE, "slots.json"), "w"), indent=1)

    # ---- markdown table -----------------------------------------------------
    T = ["| hdr | declaration | compiled | pm-thunk | Mac | exe | flags |",
         "|---:|---|---:|---:|---:|---:|---|"]
    for r in rows:
        fl = []
        if r["compiled"] != r["compiled_pm"]:
            fl.append("I1!=I2")
        if r["compiled"] != r["mac"]:
            fl.append("C!=MAC" + ("(ovl-ordinal)" if r["overloads"] > 1 else ""))
        if r["exe"] is not None and r["compiled"] != r["exe"]:
            fl.append("C!=EXE")
        if r["compiled"] != r["hidx"]:
            fl.append("C!=HDR")
        exe_s = "" if r["exe"] is None else f'{r["exe"]}' + ("d" if r["exe_src"] == "decoded" else "")
        T.append(f'| {r["hidx"]} | `{r["sig"]}` | {r["compiled"]} | {r["compiled_pm"]} | '
                 f'{r["mac"] if r["mac"] is not None else "-"}{"~" if r["overloads"] > 1 else ""} | '
                 f'{exe_s} | {" ".join(fl)} |')
    open(os.path.join(HERE, "slots.md"), "w", newline="\n").write("\n".join(T) + "\n")
    print("\n".join(T))

    # ---- summary ----------------------------------------------------------
    print()
    n_decl = len(allv)
    print(f"declarations: {n_decl} ({len(base)} cIGZUnknown + {len(win)} cIGZWin)")
    print(f"I1 read: {len(i1)}/{n_decl}   I2 read: {len(i2)}/{n_decl}")
    ctl = {("GetID", 1): 63, ("GZPaint", 1): 88, ("GZWinMoveTo", 1): 57}
    for (n, k), want in ctl.items():
        r = next(x for x in rows if x["name"] == n and x["k"] == k)
        print(f"CONTROL {n}: compiled {r['compiled']} (pm {r['compiled_pm']}) want {want} "
              f"-> {'OK' if r['compiled'] == want == r['compiled_pm'] else 'FAIL'}")
    dis = [r for r in rows if r["compiled"] != r["compiled_pm"]]
    print(f"I1 vs I2 disagreements: {len(dis)} {[r['name'] + '_' + str(r['k']) for r in dis]}")
    mm = [r for r in rows if r["compiled"] != r["mac"]]
    print(f"compiled != Mac: {len(mm)}")
    for r in mm:
        print(f"   {r['name']}_{r['k']}  compiled {r['compiled']}  Mac {r['mac']}  hdr {r['hidx']}"
              f"  exe {r['exe'] if r['exe'] is not None else '-'}")
    band = [r for r in mm if r["compiled"] is not None and (53 <= r["compiled"] <= 57 or r["compiled"] >= 118
                                                             or (r["mac"] or 0) >= 118
                                                             or 53 <= (r["mac"] or 0) <= 57)]
    outside = [r for r in mm if r not in band]
    print(f"   in bands 53-57/118+: {len(band)}; OUTSIDE: {len(outside)} "
          f"{[r['name'] + '_' + str(r['k']) for r in outside]}")
    ex = [r for r in rows if r["exe"] is not None and r["compiled"] != r["exe"]]
    print(f"compiled != exe (established+decoded): {len(ex)}")
    for r in ex:
        print(f"   {r['name']}_{r['k']:<3} {r['sig']:60} compiled {r['compiled']:3}  exe {r['exe']:3} ({r['exe_src']})")
    ok = [r for r in rows if r["exe"] is not None and r["compiled"] == r["exe"]]
    print(f"compiled == exe: {len(ok)} of {len(ok) + len(ex)} with an exe slot")
    # ovl: Mac ordinal vs exe decoded
    mo = [r for r in rows if r["overloads"] > 1 and r["exe"] is not None and r["mac"] != r["exe"]]
    print(f"Mac k-th-occurrence != exe (overloads): {[(r['name'] + '_' + str(r['k']), r['mac'], r['exe']) for r in mo]}")
    print(f"Mac-only names: {sorted(mac_names - hdr_names)}   header-only: {sorted(hdr_names - mac_names)}")
    print("overload groups (header order -> compiled slot):")
    for n, c in counts.items():
        if c > 1:
            g_ = [r for r in rows if r["name"] == n]
            print(f"   {n}: " + "; ".join(f'#{r["k"]} {r["sig"].split(n, 1)[1]} -> {r["compiled"]}'
                                          f' (Mac#{r["k"]} {r["mac"]})' for r in g_))


main()
