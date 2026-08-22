import struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

path = r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Apps\SimCity 4.exe"
data = open(path, "rb").read()
IMAGE_BASE = 0x400000

def va_to_off(va):
    return va - IMAGE_BASE

def read_u32(va):
    off = va_to_off(va)
    if 0 <= off < len(data) - 4:
        return struct.unpack_from("<I", data, off)[0]
    return None

# Approach 1: Search ENTIRE exe for pointer to GetClassID @ 0x7A6581
print("=== Search entire exe for ptr to 0x7A6581 ===")
ptr_bytes = struct.pack("<I", 0x7A6581)
pos = 0
while True:
    idx = data.find(ptr_bytes, pos)
    if idx < 0:
        break
    va = idx + IMAGE_BASE
    print("  ptr @ VA 0x%08X (off 0x%06X)" % (va, idx))
    pos = idx + 1

# Approach 2: The clsid at 0x7A6581 is in a function: mov eax, clsid; ret
# This is likely GetClassID. Search for xrefs (call/jmp to 0x7A6581)
# E8 = call rel32, E9 = jmp rel32
print("\n=== Search for call/jmp to 0x7A6581 ===")
for off in range(len(data) - 5):
    if data[off] in (0xE8, 0xE9):
        rel = struct.unpack_from("<i", data, off + 1)[0]
        target = (off + IMAGE_BASE) + 5 + rel
        if target == 0x7A6581:
            va = off + IMAGE_BASE
            print("  %s @ VA 0x%08X" % ("call" if data[off] == 0xE8 else "jmp", va))

# Approach 3: Use known vtable of cSC4WinGenTransparent (0xAB7358)
# The minimap's parent dock is cSC4WinGenTransparent.
# cSC4WinMiniMap likely has a similar vtable layout.
# Let's dump the cSC4WinGenTransparent vtable to understand the slot layout,
# then search for the minimap's vtable by its unique Draw override.
print("\n=== cSC4WinGenTransparent vtable @ 0xAB7358 ===")
gt_vtable = 0xAB7358
for slot in range(100):
    fn = read_u32(gt_vtable + slot * 4)
    if fn is None or fn < 0x401000 or fn > 0x900000:
        print("  slot %d: 0x%08X (end)" % (slot, fn if fn else 0))
        break
    label = ""
    if slot == 87: label = " GZPaint"
    elif slot == 88: label = " Plot/draw"
    elif slot == 89: label = " CalcAbsArea"
    print("  slot %d: 0x%08X%s" % (slot, fn, label))

# Approach 4: The registration function at 0x4662B0 registers classes.
# Disassemble around there to find the minimap factory.
print("\n=== Registration function @ 0x4662B0 (searching for minimap clsid) ===")
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True
# Search a wider area around 0x4662B0
reg_code = data[va_to_off(0x466200):va_to_off(0x466400)]
for insn in md.disasm(reg_code, 0x466200):
    if "0xca318388" in insn.op_str.lower() or "ca318388" in insn.op_str.lower():
        print("  FOUND: 0x%08X: %s %s" % (insn.address, insn.mnemonic, insn.op_str))
    # Also look for push of the clsid value
    if insn.mnemonic == "push" and "0xca318388" in insn.op_str.lower():
        print("  PUSH CLSID: 0x%08X: %s %s" % (insn.address, insn.mnemonic, insn.op_str))

# Approach 5: Search for the factory by looking for the clsid as an immediate
# in the code section. The pattern might be: push 0xCA318388 (68 88 83 31 CA)
# or mov reg, 0xCA318388 (B8+r 88 83 31 CA or C7 ...)
print("\n=== Search code for clsid immediate ===")
clsid_le = struct.pack("<I", 0xCA318388)
code_start = va_to_off(0x401000)
code_end = va_to_off(0x680000)
pos = code_start
while pos < code_end:
    idx = data.find(clsid_le, pos, code_end)
    if idx < 0:
        break
    va = idx + IMAGE_BASE
    # Show the instruction containing this immediate
    # Disassemble a few bytes before
    start = max(code_start, idx - 6)
    ctx = data[start:idx + 8]
    for insn in md.disasm(ctx, start + IMAGE_BASE):
        if insn.address <= va < insn.address + insn.size:
            print("  0x%08X: %s %s" % (insn.address, insn.mnemonic, insn.op_str))
            break
    pos = idx + 1
