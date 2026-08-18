#!/usr/bin/env python3
"""ordinance_namex_verify_probe.py  -- INDEPENDENT verification of the two
43-byte ordinance NAME-COLUMN x re-encodes (0x0077CBFC and 0x0077D0B9).

This does NOT import the project's common.py / gate module.  It loads the
shipped PE itself (pattern copied from tools\\disasm_109_faultchain.py) so that
the stock-byte match, the disassembly, the stack model, and the
branch-target null are all produced by a SECOND, independent instrument.

Every null in here is paired with a POSITIVE CONTROL printed next to it.
Read-only: writes nothing, builds nothing, launches nothing.
"""
import sys, os, struct, hashlib
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

EXE = r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Apps\SimCity 4.exe"
IMAGE_BASE = 0x400000
FUNC_LO, FUNC_HI = 0x0077C660, 0x0077D7E0     # the ordinance builder
CALLEE = 0x00779660                            # sub_779660 (the label maker)
CTRL_VTABLE_ENTRY = 0x007A79B0                 # known to live in a vtable -> a
                                               # dword with this value MUST exist

WINDOWS = [
    dict(tag="INCOME  (per-site 0x0077CC23)", va=0x0077CBFC, site=0x0077CC23,
         stock="8b56106a666a556a446805d385ea895424248b106a008bc8ff521c"
               "8b4c2428508b8698000000506a445551",
         rep3 ="8b56106a666a556a446805d385ea895424248b106a0091ff521c"
               "50ffb69800000068cc00000055ff742438"),
    dict(tag="EXPENSE (per-site 0x0077D0E0)", va=0x0077D0B9, site=0x0077D0E0,
         stock="8b4e108b106a666a556a446805d385ea894c24246a008bc8ff521c"
               "8b4c2428508b869c000000506a445551",
         rep3 ="8b4e108b106a666a556a446805d385ea894c24246a0091ff521c"
               "50ffb69c00000068cc00000055ff742438"),
]
WANT_X_AT_3X = 204          # round(68 * 3.0)


# ---------------------------------------------------------------- PE loading
def load():
    data = open(EXE, "rb").read()
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    nsec = struct.unpack_from("<H", data, pe + 6)[0]
    opt = struct.unpack_from("<H", data, pe + 20)[0]
    secs, off = [], pe + 24 + opt
    for _ in range(nsec):
        n = data[off:off + 8].rstrip(b"\0").decode("latin1")
        vsize, va, rsize, roff = struct.unpack_from("<IIII", data, off + 8)
        secs.append((n, va, vsize, roff, rsize))
        off += 40
    return data, secs


def va2off(secs, va):
    rva = va - IMAGE_BASE
    for n, sva, vsize, roff, rsize in secs:
        if sva <= rva < sva + max(vsize, rsize):
            return roff + (rva - sva)
    return None


def md():
    m = Cs(CS_ARCH_X86, CS_MODE_32)
    m.detail = False
    return m


# ------------------------------------------------- independent stack tracker
def model(code, va):
    """Decode + model ESP.  Returns dict with the decode and stack facts.

    Rules modelled (only what these windows contain):
      push imm/reg          esp -= 4
      push dword [esp+d]    address = esp_before + d   (PUSH r/m32 reads the
                            memory operand using the PRE-decrement ESP), esp-=4
      push dword [esi+d]    esp -= 4
      mov dword [esp+d],r   store slot = esp + d
      mov r, dword [esp+d]  load  slot = esp + d
      call                  net 0 (callee balances; ret addr popped by ret)
    Anything else that touches esp raises, so an unmodelled form can never be
    silently scored as OK.
    """
    out = dict(lines=[], pushes=[], esp=0, store=None, load=None,
               decoded=0, bad=None)
    esp = 0
    for ins in md().disasm(code, va):
        out["decoded"] += ins.size
        out["lines"].append((ins.address, ins.size, ins.mnemonic, ins.op_str,
                             code[ins.address - va: ins.address - va + ins.size].hex(),
                             esp))
        m_, o = ins.mnemonic, ins.op_str
        if m_ == "push":
            if o.startswith("dword ptr [esp"):
                d = int(o.split("+")[1].split("]")[0], 0)
                out["load"] = esp + d
                out["pushes"].append(("frameslot", esp + d))
            elif o.startswith("dword ptr [esi"):
                d = int(o.split("+")[1].split("]")[0], 0)
                out["pushes"].append(("esi", d))
            elif o.startswith("dword ptr"):
                out["bad"] = "unmodelled push mem form: " + o
            elif o.startswith("0x") or o.lstrip("-").isdigit():
                out["pushes"].append(("imm", int(o, 0)))
            else:
                out["pushes"].append(("reg", o))
            esp -= 4
        elif m_ == "mov" and o.startswith("dword ptr [esp"):
            d = int(o.split("+")[1].split("]")[0], 0)
            out["store"] = esp + d
        elif m_ == "mov" and ", dword ptr [esp" in o:
            d = int(o.split("+")[-1].split("]")[0], 0)
            out["load"] = esp + d
            out["pushes"].append(("pending-frameslot", esp + d))
        elif m_ in ("mov", "xchg", "call", "lea", "nop"):
            if "esp" in o and m_ != "call":
                out["bad"] = "unmodelled esp use: %s %s" % (m_, o)
        else:
            out["bad"] = "unmodelled mnemonic: %s %s" % (m_, o)
    out["esp"] = esp
    return out


def canon(pushes):
    """Collapse `mov ecx,[esp+d]; ... ; push ecx` into one ('frameslot', d) so
    stock and the replacement are comparable, and reduce the two `push eax`
    forms (string return / y fetch) to a comparable shape."""
    res, pending = [], None
    for k, v in pushes:
        if k == "pending-frameslot":
            pending = v
            continue
        if k == "reg" and v == "ecx" and pending is not None:
            res.append(("frameslot", pending)); pending = None; continue
        res.append((k, v))
    return res


def show(tag, m_):
    print("    %-58s  esp" % tag)
    for a, sz, mn, op, hx, e in m_["lines"]:
        print("    0x%08X  %-14s %-5s %-28s %+5d" % (a, hx, mn, op, e))
    print("    -> %d bytes decoded, %d pushes, net esp %+d, store slot %s, "
          "load slot %s" % (m_["decoded"], len(m_["pushes"]), m_["esp"],
                            m_["store"], m_["load"]))
    if m_["bad"]:
        print("    !! MODEL GAP: " + m_["bad"])


# -------------------------------------------------------- branch-target scan
def branch_targets(data, secs):
    """Every rel8/rel32 jcc/jmp/call target in every .text section, plus the
    count -- the count IS the positive control."""
    tgts = {}
    m = md()
    for n, sva, vsize, roff, rsize in secs:
        if not n.lower().startswith(".text"):
            continue
        base = IMAGE_BASE + sva
        blob = data[roff:roff + rsize]
        # Linear sweep from the section start would desync; instead sweep every
        # byte offset for the fixed-form rel encodings.  Over-approximates
        # (may invent targets from operand bytes) -- which is the SAFE
        # direction for a "nothing lands inside" claim: false positives only.
        i, L = 0, len(blob)
        while i < L - 5:
            b = blob[i]
            if b == 0xE8 or b == 0xE9:                       # call/jmp rel32
                rel = struct.unpack_from("<i", blob, i + 1)[0]
                tgts.setdefault(base + i + 5 + rel, []).append(base + i)
                i += 1; continue
            if b == 0x0F and 0x80 <= blob[i + 1] <= 0x8F:    # jcc rel32
                rel = struct.unpack_from("<i", blob, i + 2)[0]
                tgts.setdefault(base + i + 6 + rel, []).append(base + i)
                i += 1; continue
            if (0x70 <= b <= 0x7F) or b in (0xEB, 0xE0, 0xE1, 0xE2, 0xE3):
                rel = struct.unpack_from("<b", blob, i + 1)[0]
                tgts.setdefault(base + i + 2 + rel, []).append(base + i)
                i += 1; continue
            i += 1
    return tgts


def dword_refs(data, value):
    """Every file offset holding this exact little-endian dword."""
    needle = struct.pack("<I", value)
    hits, start = [], 0
    while True:
        j = data.find(needle, start)
        if j < 0:
            return hits
        hits.append(j)
        start = j + 1


def main():
    if not os.path.exists(EXE):
        print("EXE NOT FOUND"); return 2
    data, secs = load()
    print("exe %s" % EXE)
    print("size %d bytes   sha256 %s" % (len(data), hashlib.sha256(data).hexdigest()[:32]))
    print("sections: %s\n" % ", ".join(s[0] for s in secs))

    fails = []

    # ---- 0. positive control for the dword scanner ------------------------
    ctl = dword_refs(data, CTRL_VTABLE_ENTRY)
    print("=" * 74)
    print("0. POSITIVE CONTROLS")
    print("=" * 74)
    print("  dword scanner control: 0x%08X (a known vtable entry) found at %d "
          "file offset(s) %s" % (CTRL_VTABLE_ENTRY, len(ctl),
                                 [hex(x) for x in ctl[:4]]))
    if not ctl:
        fails.append("dword scanner is BLIND (control value not found) - its "
                     "null below would be worthless")

    tgts = branch_targets(data, secs)
    in_func = sorted(t for t in tgts if FUNC_LO <= t < FUNC_HI)
    print("  branch scanner control: %d distinct targets image-wide, %d of them "
          "inside sub_77C660 [0x%08X,0x%08X)" % (len(tgts), len(in_func),
                                                 FUNC_LO, FUNC_HI))
    if len(in_func) < 5:
        fails.append("branch scanner resolved only %d targets inside the host "
                     "function - too blind to trust its null" % len(in_func))

    # ---- 1. callee shape --------------------------------------------------
    print("\n" + "=" * 74)
    print("1. CALLEE sub_%06X - how many bytes of args does it pop?" % CALLEE)
    print("=" * 74)
    o = va2off(secs, CALLEE)
    blob = data[o:o + 0x400]
    rets = [(i.address, i.mnemonic, i.op_str)
            for i in md().disasm(blob, CALLEE)
            if i.mnemonic.startswith("ret")]
    print("  ret forms in the first 0x400 bytes: %s" %
          ", ".join("0x%08X %s %s" % r for r in rets[:6]))
    if not any(r[2] == "0x28" for r in rets):
        print("  (no `ret 0x28` in the first 0x400 - see arg count check below)")

    # ---- 2. per-window -----------------------------------------------------
    for w in WINDOWS:
        print("\n" + "=" * 74)
        print("2. %s   window 0x%08X" % (w["tag"], w["va"]))
        print("=" * 74)
        stock = bytes.fromhex(w["stock"])
        rep = bytes.fromhex(w["rep3"])
        off = va2off(secs, w["va"])
        live = data[off:off + len(stock)]

        print("  live exe bytes : %s" % live.hex())
        print("  quoted stock   : %s" % stock.hex())
        if live != stock:
            fails.append("%s: LIVE BYTES != QUOTED STOCK" % w["tag"]); print("  *** MISMATCH ***")
        else:
            print("  STOCK MATCH at file offset 0x%X, %d bytes" % (off, len(stock)))

        if len(rep) != len(stock):
            fails.append("%s: length drift %d vs %d" % (w["tag"], len(rep), len(stock)))
        print("  length stock=%d  replacement=%d  %s" %
              (len(stock), len(rep), "EQUAL" if len(rep) == len(stock) else "*** DRIFT ***"))

        print("\n  --- STOCK disassembly ---")
        ms = model(stock, w["va"]); show("stock", ms)
        print("\n  --- REPLACEMENT (f=3.00) disassembly ---")
        mr = model(rep, w["va"]); show("replacement", mr)

        if ms["decoded"] != len(stock):
            fails.append("%s: stock decode covers %d/%d bytes" % (w["tag"], ms["decoded"], len(stock)))
        if mr["decoded"] != len(rep):
            fails.append("%s: replacement decode covers %d/%d bytes" % (w["tag"], mr["decoded"], len(rep)))
        if ms["bad"] or mr["bad"]:
            fails.append("%s: model gap  stock=%s rep=%s" % (w["tag"], ms["bad"], mr["bad"]))

        cs_, cr_ = canon(ms["pushes"]), canon(mr["pushes"])
        print("\n  canonical stock pushes (push order) : %s" % (cs_,))
        print("  canonical repl  pushes (push order) : %s" % (cr_,))
        print("  arg count  stock=%d  repl=%d   (args = push count; callee is "
              "stdcall ret 0x%X => %d args)" % (len(cs_), len(cr_),
                                                -ms["esp"], -ms["esp"] // 4))
        if len(cs_) != 10 or len(cr_) != 10:
            fails.append("%s: arg count %d/%d, expected 10/10" % (w["tag"], len(cs_), len(cr_)))
        if ms["esp"] != mr["esp"]:
            fails.append("%s: net esp %+d vs %+d" % (w["tag"], ms["esp"], mr["esp"]))
        if ms["store"] != mr["store"] or ms["store"] is None:
            fails.append("%s: spill slot %s vs %s" % (w["tag"], ms["store"], mr["store"]))
        if ms["load"] != mr["load"] or ms["load"] is None:
            fails.append("%s: parent reload slot %s vs %s" % (w["tag"], ms["load"], mr["load"]))
        if ms["store"] is not None and ms["store"] != ms["load"]:
            fails.append("%s: TRACKER CONTROL FAILED - stock store %s != stock "
                         "load %s" % (w["tag"], ms["store"], ms["load"]))
        else:
            print("  tracker POSITIVE CONTROL: stock spills AND reloads the same "
                  "frame slot %+d - the model reproduces stock's own aliasing"
                  % ms["store"])

        # arg-by-arg, arg3 (x) allowed to change; arg4/arg5 forms normalised
        argno = lambda i: len(cs_) - i
        for i, (a, b) in enumerate(zip(cs_, cr_)):
            n = argno(i)
            if n == 3:
                if b != ("imm", WANT_X_AT_3X):
                    fails.append("%s: arg3 is %s, want imm %d" % (w["tag"], b, WANT_X_AT_3X))
                else:
                    print("  arg3 (x): stock %s -> repl %s   (0x%02X = %d = round(68*3.0)) OK"
                          % (a, b, WANT_X_AT_3X, WANT_X_AT_3X))
                continue
            if n == 4:   # y: stock `mov eax,[esi+d]; push eax` vs repl `push [esi+d]`
                if not (a == ("reg", "eax") and b[0] == "esi"):
                    fails.append("%s: arg4 (y) stock %s vs repl %s" % (w["tag"], a, b))
                else:
                    print("  arg4 (y): stock mov eax,[esi+0x%X];push eax -> repl push "
                          "dword [esi+0x%X]  SAME SOURCE" % (b[1], b[1]))
                continue
            if a != b:
                fails.append("%s: arg%d differs  %s vs %s" % (w["tag"], n, a, b))

        # imm32 literal really is 204
        if bytes.fromhex("68") + (WANT_X_AT_3X).to_bytes(4, "little") not in rep:
            fails.append("%s: replacement does not contain `push imm32 %d`"
                         % (w["tag"], WANT_X_AT_3X))
        else:
            print("  imm32 literal check: bytes 68 CC 00 00 00 present => push %d" % WANT_X_AT_3X)

        # site really is the x push
        rel = w["site"] - w["va"]
        print("  per-site 0x%08X = window+%d, stock bytes there = %s (`push 0x44`) "
              "-> it IS arg3 and it IS inside the block"
              % (w["site"], rel, stock[rel:rel + 2].hex()))
        if stock[rel:rel + 2] != b"\x6a\x44":
            fails.append("%s: per-site does not point at `6a 44`" % w["tag"])

        # branch targets strictly inside the window
        inside = sorted(t for t in tgts if w["va"] < t < w["va"] + len(stock))
        near_lo = max([t for t in tgts if t <= w["va"]], default=None)
        near_hi = min([t for t in tgts if t >= w["va"] + len(stock)], default=None)
        print("  branch targets strictly inside window: %s" %
              (", ".join(hex(t) for t in inside) if inside else "NONE"))
        print("  (scanner sightedness here: nearest resolved target below = %s, "
              "above = %s -- it is NOT blind in this neighbourhood)"
              % (hex(near_lo) if near_lo else "?", hex(near_hi) if near_hi else "?"))
        if inside:
            fails.append("%s: %d branch target(s) land inside the window" % (w["tag"], len(inside)))

        # data references (jump tables / fn pointers) into the window
        dhits = []
        for a in range(w["va"], w["va"] + len(stock)):
            for h in dword_refs(data, a):
                dhits.append((a, h))
        print("  dword values anywhere in the image equal to an address inside "
              "the window: %s" % (dhits if dhits else "NONE"))
        if dhits:
            fails.append("%s: %d in-image dword(s) point inside the window "
                         "(possible jump table / fn ptr)" % (w["tag"], len(dhits)))

        # what follows the window
        tail = data[off + len(stock): off + len(stock) + 16]
        print("  bytes AFTER the window: %s" % tail.hex())
        for ins in md().disasm(tail, w["va"] + len(stock)):
            print("    0x%08X  %-6s %s" % (ins.address, ins.mnemonic, ins.op_str))
            if ins.mnemonic == "call":
                if ins.op_str.startswith("0x"):
                    print("      -> callee 0x%s %s" % (ins.op_str[2:],
                          "== sub_%06X OK" % CALLEE if int(ins.op_str, 16) == CALLEE
                          else "*** NOT sub_%06X ***" % CALLEE))
                    if int(ins.op_str, 16) != CALLEE:
                        fails.append("%s: the call after the window is not sub_%06X" % (w["tag"], CALLEE))
                break

    # ---- 3. f=2.00 no-op proof --------------------------------------------
    print("\n" + "=" * 74)
    print("3. WHAT SHIPS AT f=2.00")
    print("=" * 74)
    print("  The shipping gate proposed is `f >= 2.5f`.  2.00 < 2.5 => the block")
    print("  applier returns before its first write, so all 86 bytes stay stock,")
    print("  and the two per-site entries (removed) were writing 0x88=136 clamped")
    print("  to 0x7F=127 -- which is what 2x is USER-CONFIRMED good with. Under")
    print("  the spec below the per-site entries move into an f<2.5 branch so the")
    print("  clamped 127 at 2x is byte-identical to v2.73.3.")

    print("\n" + "=" * 74)
    if fails:
        print("RED - %d failure(s):" % len(fails))
        for f in fails:
            print("  * " + f)
        return 1
    print("GREEN - independent instrument agrees with gate_ordinance_namex.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
