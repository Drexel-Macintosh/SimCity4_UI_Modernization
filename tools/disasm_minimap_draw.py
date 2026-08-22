import struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

path = r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Apps\SimCity 4.exe"
data = open(path, "rb").read()
IMAGE_BASE = 0x400000

def va_to_off(va):
    return va - IMAGE_BASE

md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

DRAW_VA = 0x7A79B0

print("=== cSC4WinMiniMap Draw @ 0x%08X ===" % DRAW_VA)
d_off = va_to_off(DRAW_VA)
d_code = data[d_off:d_off + 2048]
insn_count = 0
for insn in md.disasm(d_code, DRAW_VA):
    print("  0x%08X: %-8s %s" % (insn.address, insn.mnemonic, insn.op_str))
    insn_count += 1
    if insn.mnemonic == "ret" or insn_count > 300:
        break

# Also check what functions it calls
print("\n=== Call targets ===")
for insn in md.disasm(d_code, DRAW_VA):
    if insn.mnemonic == "call" and insn.op_str.startswith("0x"):
        target = int(insn.op_str, 16)
        print("  call 0x%08X (from 0x%08X)" % (target, insn.address))
    if insn.mnemonic == "ret" or insn_count > 300:
        break
