# field_xref.py - sweep a code range for memory operands whose displacement matches a field
# (object-relative, cIGZGraph-iface-relative = disp-0xD8, line-iface-relative = disp-0x22C).
# Reports reads and writes separately. usage: python field_xref.py 0x120 [start end]
import sys
sys.path.insert(0, r"C:\dev\SC4UIScale\tools\sdk\ghidra\verify\W-Graph-verify")
from vx import *
from capstone.x86 import X86_OP_MEM
from capstone import CS_AC_WRITE, CS_AC_READ

field = int(sys.argv[1], 16)
a = int(sys.argv[2], 16) if len(sys.argv) > 2 else 0x9B1E00
b = int(sys.argv[3], 16) if len(sys.argv) > 3 else 0x9BC100
disps = {field: "obj", field - 0xD8: "igzgraph", field - 0x22C: "iface2"}
md.skipdata = True
WRITE_MN = ("mov", "movsd", "movsb", "movsw", "and", "or", "xor", "add", "sub", "inc", "dec", "fstp", "fst", "fistp", "fist", "setne", "sete", "adc", "sbb", "shl", "shr", "sar", "neg", "not", "stosd", "xchg")
code = rd(a, b - a)
for ins in md.disasm(code, a):
    if ins.mnemonic == ".byte":
        continue
    try:
        ops = ins.operands
    except Exception:
        continue
    for k, op in enumerate(ops):
        if op.type == X86_OP_MEM and op.mem.disp in disps:
            try:
                acc = op.access
            except Exception:
                acc = 0
            kind = "W" if (acc & CS_AC_WRITE) else "R"
            if ins.mnemonic in ("lea",):
                kind = "LEA"
            print("%s %-8s %s" % (kind, disps[op.mem.disp], fmt(ins)))
