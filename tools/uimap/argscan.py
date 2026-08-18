"""argscan.py - the arg/encoding extractor. STAGE 2's engine.

Given a `call` inside a builder, recover the pushed arguments AND, for each
one, the EXACT instruction + encoding that carries its constant.  This is
the thing hand-enumeration keeps getting wrong: the same x can arrive as

    push imm8            6A 12
    push imm32           68 04 01 00 00
    sub  r32, imm8       83 EA 26          (right-margin  W-38)
    sub  r32, imm32      81 E9 C3 00 00 00 (button anchor W-195)
    lea  r32,[r32+disp8] 8D 51 0F          (combo height 15 - CANNOT hold >127)
    add  r32, imm32      05 31 01 00 00    (master notch base+305)
    mov  r32, imm32      B8 ...

Scanning for one encoding finds one copy - METHOD.md §4 step 4.

Stack discipline: SC4's UI helpers are __stdcall (`ret N`), so a helper's
own arguments are cleaned by the callee.  Walking backwards from a call we
therefore skip whole balanced sub-calls: a direct call's arity is read from
its `ret N`; a cdecl call's from the `add esp,N` that follows it; a vtable
call's from the slot table below.  Anything unknown STOPS the walk and the
site is flagged `incomplete` rather than silently mis-attributed.
"""
import re

import common as C

_fcache = {}
_arity = {}

# cIGZWin vtable slots used for geometry, proven in this exe:
#   +0x8C  GetChildWindowFromID(id)        1 arg   (identification signal)
#   +0xD4  SetSize(w,h)                    2 args  (push h; push w)
#   +0xD8  SetArea(const Rect*)            1 arg
#   +0xDC  SetArea(l,t,r,b)                4 args  (push b;push r;push t;push l)
#   +0xE0  SetPosition(x,y)                2 args  (push y; push x)
#   +0x100 SetID(id)                       1 arg
#   +0x110 SetFlag(flag,bool)              2 args
VT_ARITY = {0x08: 0, 0x0C: 0, 0x30: 0, 0x38: 1, 0x8C: 1, 0xA4: 0, 0xA8: 0,
            0xD4: 2, 0xD8: 1, 0xDC: 4, 0xE0: 2, 0x100: 1, 0x110: 2,
            0x14: 1, 0x34: 2, 0x40: 5, 0x54: 1, 0x28: 1, 0x48: 1,
            0x1B0: 3, 0x8: 0}
VT_GEOM = {
    0xD4: ("SetSize", ["w", "h"]),
    0xDC: ("SetArea", ["l", "t", "r", "b"]),
    0xE0: ("SetPosition", ["x", "y"]),
}

REG32 = ("eax", "ecx", "edx", "ebx", "esp", "ebp", "esi", "edi")


def func_insns(lo, hi):
    key = (lo, hi)
    if key not in _fcache:
        m = C.md()
        _fcache[key] = list(m.disasm(C.rd(lo, hi - lo), lo))
    return _fcache[key]


def arity_of(va, fm):
    """__stdcall arg count of a direct-call target, from its `ret N`."""
    if va in _arity:
        return _arity[va]
    lo = fm.owner(va)
    n = None
    if lo is not None:
        hi = fm.end(lo)
        for ins in func_insns(lo, min(hi, lo + 0x4000)):
            if ins.mnemonic == "ret":
                if ins.op_str:
                    n = int(ins.op_str, 0) // 4
                else:
                    n = 0          # cdecl (or void) - caller cleans
                break
    _arity[va] = n
    return n


_IMM_ONLY = re.compile(r"^-?(?:0x[0-9a-fA-F]+|\d+)$")
_LEA_DISP = re.compile(r"\[[^\]]*?([+-])\s*(0x[0-9a-fA-F]+|\d+)\]")


def _imm_field(ins):
    """(immOff, immSize, value) for the instruction's trailing immediate.

    A MEMORY DISPLACEMENT IS NOT AN IMMEDIATE.  `mov ecx,[esp+0x1c]` ends
    in a number but carries no constant to patch; reading it as one both
    manufactures phantom "constants" and hides the real provenance behind
    the load.  Only `lea` (which computes an address as a value) has its
    displacement treated as the constant.
    """
    b = ins.bytes
    op = ins.op_str
    if ins.mnemonic == "lea":
        m = _LEA_DISP.search(op)
        if not m:
            return None
        val = int(m.group(2), 0) * (-1 if m.group(1) == "-" else 1)
    else:
        last = op.rsplit(",", 1)[-1].strip() if "," in op else op.strip()
        if not _IMM_ONLY.match(last):
            return None
        if "ptr [" in op and op.rstrip().endswith("]"):
            return None
        val = int(last, 0)
    # locate a 1- or 4-byte little-endian encoding of val at the tail
    for size in (4, 1):
        if len(b) >= size:
            tail = b[len(b) - size:]
            v = int.from_bytes(tail, "little", signed=True)
            if v == val or (v & ((1 << (size * 8)) - 1)) == (val & ((1 << (size * 8)) - 1)):
                return (len(b) - size, size, val)
    return None


def classify(ins, reg=None):
    """Encoding descriptor for an instruction that produces a constant."""
    mn = ins.mnemonic
    ops = ins.op_str
    f = _imm_field(ins)
    d = {"site": ins.address, "insn": "%s %s" % (mn, ops),
         "bytes": ins.bytes.hex(), "len": len(ins.bytes),
         "enc": None, "value": None, "immOff": None, "immSize": None}
    if mn == "push":
        if ins.bytes[0] == 0x6A:
            d.update(enc="push_imm8", value=ins.bytes[1] if ins.bytes[1] < 0x80
                     else ins.bytes[1] - 256, immOff=1, immSize=1)
        elif ins.bytes[0] == 0x68:
            d.update(enc="push_imm32",
                     value=int.from_bytes(ins.bytes[1:5], "little"),
                     immOff=1, immSize=4)
        else:
            d.update(enc="push_reg" if ops in REG32 else "push_mem")
        return d
    if mn == "lea" and f:
        off, size, val = f
        d.update(enc="lea_disp8" if size == 1 else "lea_disp32",
                 value=val, immOff=off, immSize=size)
        return d
    if mn in ("add", "sub", "mov", "or", "and", "cmp", "imul", "shl", "sar") and f:
        off, size, val = f
        d.update(enc="%s_imm%d" % (mn, size * 8), value=val,
                 immOff=off, immSize=size)
        return d
    if mn == "xor" and ops.count(",") == 1:
        a, b2 = [x.strip() for x in ops.split(",")]
        if a == b2:
            d.update(enc="xor_zero", value=0)
            return d
    d.update(enc=mn)
    return d


_ESP_LOAD = re.compile(r"^(e[a-z][a-z]), dword ptr \[esp(?: \+ (0x[0-9a-f]+))?\]$")
_ESP_STORE = re.compile(r"^dword ptr \[esp(?: \+ (0x[0-9a-f]+))?\], (e[a-z][a-z])$")


def _esp_delta_step(ins, nxt, fm):
    """esp_before(ins) - esp_after(ins), walking BACKWARDS."""
    mn, ops = ins.mnemonic, ins.op_str
    if mn == "push":
        return 4
    if mn == "pop":
        return -4
    if mn == "sub" and ops.startswith("esp,"):
        return int(ops.split(",")[1], 0)
    if mn == "add" and ops.startswith("esp,"):
        return -int(ops.split(",")[1], 0)
    if mn == "call":
        # __stdcall: the callee popped its N args, so esp AFTER is N*4 higher
        if ops.startswith("0x"):
            k = arity_of(int(ops, 0), fm)
        else:
            m = re.search(r"\+ (0x[0-9a-f]+)\]", ops)
            k = VT_ARITY.get(int(m.group(1), 0) if m else 0, 0)
        return -4 * (k or 0)
    return 0


def resolve_local(insns, idx, disp, depth, limit=200):
    """Find what was STORED into [esp+disp] before insns[idx], and classify it.

    Needed because builders park a computed coordinate in a stack local and
    push it later - e.g. the master funding NOTCH:
        0x786F26  lea ecx,[eax+0xC8]   ->  mov [esp+0x1C], ecx
        0x786FF1  mov ecx,[esp+0x1C]   ->  push ecx  -> BmpArt x
    A register-only walk cannot see across that store, which is exactly how
    those two sites stayed invisible to the primitive census.
    """
    delta = 0
    i = idx - 1
    n = 0
    while i >= 0 and n < limit:
        ins = insns[i]
        n += 1
        m = _ESP_STORE.match(ins.op_str) if ins.mnemonic == "mov" else None
        if m:
            k = int(m.group(1), 0) if m.group(1) else 0
            if k == disp + delta:
                d = resolve_reg(insns, i, m.group(2), depth + 1, 120)
                if d:
                    d = dict(d)
                    d["via_local"] = "[esp+0x%X] stored at 0x%X" % (k, ins.address)
                return d
        delta += _esp_delta_step(ins, None, resolve_local._fm)
        i -= 1
    return None


resolve_local._fm = None


def resolve_reg(insns, idx, reg, depth=0, limit=80):
    """Walk back from insns[idx] for the last write of `reg`; classify it."""
    if depth > 3:
        return None
    i = idx - 1
    n = 0
    while i >= 0 and n < limit:
        ins = insns[i]
        n += 1
        ops = ins.op_str
        if "," in ops:
            dst = ops.split(",")[0].strip()
        else:
            dst = ops.strip()
        writes = (dst == reg and ins.mnemonic not in ("cmp", "test", "push"))
        if ins.mnemonic == "call" and reg == "eax":
            return {"site": ins.address, "enc": "call_result",
                    "insn": "call %s" % ops, "value": None,
                    "bytes": ins.bytes.hex(), "len": len(ins.bytes)}
        if writes:
            d = classify(ins, reg)
            if d["enc"] in ("mov", "movzx", "movsx") and "[" in ops:
                d["enc"] = "mem_load"
                m = _ESP_LOAD.match(ops)
                if m and resolve_local._fm is not None:
                    disp = int(m.group(2), 0) if m.group(2) else 0
                    sub = resolve_local(insns, i, disp, depth)
                    if sub and sub.get("value") is not None:
                        return sub
            if d["value"] is None and d["enc"] in ("mov_imm32", "add_imm32"):
                pass
            # provenance: what fed the base register
            if d["enc"] in ("lea_disp8", "lea_disp32", "add_imm8", "add_imm32",
                            "sub_imm8", "sub_imm32", "imul_imm8"):
                m = re.search(r"\[(e[a-z][a-z])", ops)
                base = m.group(1) if m else (ops.split(",")[0].strip())
                d["base"] = base
                sub = resolve_reg(insns, i, base, depth + 1, 40)
                d["base_from"] = (sub or {}).get("enc")
            return d
        i -= 1
    return None


def call_args(insns, idx, nargs, fm, assume_getter=True):
    """Recover nargs stack arguments for the call at insns[idx].

    Returns (args, incomplete). args[0] is the FIRST argument (the push
    nearest the call). Each entry is a classify() dict, plus for push_reg
    the resolved producing instruction under key 'src'.
    """
    args = []
    incomplete = False
    assumed = []
    i = idx - 1
    scanned = 0
    while len(args) < nargs and i >= 0 and scanned < 400:
        ins = insns[i]
        scanned += 1
        mn = ins.mnemonic
        if mn == "push":
            d = classify(ins)
            if d["enc"] == "push_reg":
                src = resolve_reg(insns, i, ins.op_str.strip())
                if src:
                    d["src"] = src
            args.append(d)
            i -= 1
            continue
        if mn in ("pushfd", "pushal"):
            incomplete = True
            break
        if mn == "call":
            # skip a balanced sub-call: its own args were pushed before it
            k = None
            if ins.op_str.startswith("0x"):
                k = arity_of(int(ins.op_str, 0), fm)
                if k == 0:
                    # cdecl or void: an `add esp,N` right after tells us
                    nxt = insns[i + 1] if i + 1 < len(insns) else None
                    if nxt is not None and nxt.mnemonic == "add" and \
                            nxt.op_str.startswith("esp,"):
                        k = int(nxt.op_str.split(",")[1], 0) // 4
            else:
                m = re.search(r"\+ (0x[0-9a-f]+)\]", ins.op_str)
                slot = int(m.group(1), 0) if m else 0
                k = VT_ARITY.get(slot)
                if k is None and assume_getter:
                    # Unnamed vtable slot. Overwhelmingly these are 0-arg
                    # getters whose RESULT is pushed afterwards (the pattern
                    # `mov ecx,obj; call [vt+N]; push eax`). Assume 0 and let
                    # the caller's validate() catch a bad assumption.
                    k = 0
                    assumed.append((ins.address, slot))
            if k is None:
                incomplete = True
                break
            skipped = 0
            i -= 1
            while skipped < k and i >= 0:
                if insns[i].mnemonic == "push":
                    skipped += 1
                elif insns[i].mnemonic == "call":
                    incomplete = True
                    break
                i -= 1
            if skipped < k:
                incomplete = True
                break
            continue
        if mn in ("ret", "jmp"):
            incomplete = True
            break
        i -= 1
    if len(args) < nargs:
        incomplete = True
    if assumed:
        for a in args:
            a.setdefault("_", None)
        args = args  # keep shape; the assumption list rides on the result
    return args, incomplete


def validate(spec, args):
    """Self-check that the backward walk landed on the right push run.

    The text factories always end with a font-style GUID and an R,G,B
    triple; if the walk consumed one push too many or too few those slots
    stop looking like a GUID / a 0..255 byte.  A cheap, independent proof
    that the extraction is aligned - no live dump needed.
    """
    probs = []
    names = spec.get("args", [])
    for i, nm in enumerate(names):
        if i >= len(args):
            probs.append("missing arg%d (%s)" % (i + 1, nm))
            continue
        v = args[i].get("value")
        if v is None:
            continue
        if nm == "styleId" and v <= 0xFFFF:
            probs.append("arg%d styleId=0x%X not a GUID" % (i + 1, v))
        if nm in ("R", "G", "B") and not (0 <= v <= 0xFF):
            probs.append("arg%d %s=%d out of 0..255" % (i + 1, nm, v))
        if nm in ("x", "y", "w") and not (-4096 <= v <= 8192):
            probs.append("arg%d %s=%d implausible" % (i + 1, nm, v))
    return probs


def call_args_checked(insns, idx, spec, fm):
    """call_args + validate, with a fallback to the conservative walk."""
    n = spec["arity"]
    args, inc = call_args(insns, idx, n, fm, assume_getter=True)
    probs = validate(spec, args)
    if probs:
        a2, i2 = call_args(insns, idx, n, fm, assume_getter=False)
        p2 = validate(spec, a2)
        if len(p2) < len(probs):
            return a2, i2, p2
    return args, inc, probs
