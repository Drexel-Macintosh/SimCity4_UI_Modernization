"""Function-scoped disassembly helpers (verifier's own)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vpe import *


def fn(va, maxins=400, maxbytes=0x1400):
    """Decode from va; track the furthest forward branch target inside the
    window; stop at ret / indirect jmp / out-of-window jmp once no pending
    forward target lies beyond the current instruction."""
    out = []
    far = va
    for ins in md.disasm(rd(va, maxbytes), va):
        out.append(ins)
        if len(out) >= maxins:
            break
        m = ins.mnemonic
        tgt = None
        if m.startswith("j") and ins.op_str.startswith("0x"):
            tgt = int(ins.op_str, 16)
            if va <= tgt < va + maxbytes and tgt > far:
                far = tgt
        end = m in ("ret", "retn") or (m == "jmp" and (tgt is None or not (va <= tgt < va + maxbytes)))
        if m == "jmp" and tgt is not None and tgt <= ins.address:
            end = True  # backward jmp: loop back edge, treat as potential end
        if m == "int3":
            end = True
        if end and ins.address + ins.size > far:
            break
    return out


def fmt(ins_list, ind="  "):
    return "\n".join(f"{ind}{i.address:08X}: {i.bytes.hex():<22} {i.mnemonic} {i.op_str}" for i in ins_list)


def body_str(va, maxins=400):
    return " ; ".join(f"{i.mnemonic} {i.op_str}" for i in fn(va, maxins))


def rets(va):
    return sorted(set((int(i.op_str, 16) if i.op_str else 0) for i in fn(va) if i.mnemonic in ("ret", "retn")))


def resolve(va, trace=None):
    """Follow thunk (sub/add ecx,N ; jmp X) and stub (jmp X) chains.
    Returns (final_va, total_this_delta, chain)."""
    chain = [va]
    delta = 0
    cur = va
    for _ in range(8):
        ins = list(md.disasm(rd(cur, 16), cur))[:2]
        if ins and ins[0].mnemonic == "jmp" and ins[0].op_str.startswith("0x"):
            cur = int(ins[0].op_str, 16)
            chain.append(cur)
            continue
        if len(ins) == 2 and ins[0].mnemonic in ("sub", "add") and ins[0].op_str.startswith("ecx, ") and ins[1].mnemonic == "jmp" and ins[1].op_str.startswith("0x"):
            n = int(ins[0].op_str.split(",")[1], 16)
            delta += -n if ins[0].mnemonic == "sub" else n
            cur = int(ins[1].op_str, 16)
            chain.append(cur)
            continue
        break
    return cur, delta, chain
