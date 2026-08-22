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

# GetClassID for cSC4WinMiniMap is at VA 0x7A6581
# (mov eax, 0xCA318388; ret)
GETCLASSID_VA = 0x7A6581

# Search for a pointer to this function in .rdata (vtable area 0x680000-0xB00000)
print("Searching for vtable pointer to GetClassID @ 0x%08X..." % GETCLASSID_VA)
ptr_bytes = struct.pack("<I", GETCLASSID_VA)
pos = va_to_off(0x680000)
end = va_to_off(0xB00000)
vtable_candidates = []
while pos < end:
    idx = data.find(ptr_bytes, pos, end)
    if idx < 0:
        break
    va = idx + IMAGE_BASE
    vtable_candidates.append(va)
    print("  ptr @ VA 0x%08X" % va)
    pos = idx + 1

# For each candidate, the vtable starts some slots before GetClassID
# GetClassID is typically a high slot. Let's dump the area around each candidate.
md = Cs(CS_ARCH_X86, CS_MODE_32)

for cand_va in vtable_candidates:
    print("\n=== VTable candidate @ 0x%08X ===" % cand_va)
    # GetClassID is at some slot. Let's figure out which slot.
    # Walk backwards from the candidate to find the start of the vtable
    # (first entry that points into .text)
    for back in range(120):
        slot_va = cand_va - back * 4
        fn = read_u32(slot_va)
        if fn is None or fn < 0x401000 or fn > 0x900000:
            # Found the boundary
            vtable_start = slot_va + 4
            getclassid_slot = back - 1
            print("  VTable starts @ 0x%08X (GetClassID at slot %d)" % (vtable_start, getclassid_slot))

            # Dump slots 85-95 (the draw area)
            print("\n  Draw-area slots:")
            for slot in range(max(0, getclassid_slot - 10), getclassid_slot + 3):
                fn = read_u32(vtable_start + slot * 4)
                label = ""
                if slot == getclassid_slot:
                    label = " <- GetClassID"
                elif slot == 87:
                    label = " <- GZPaint (idx 87)"
                elif slot == 88:
                    label = " <- Plot/draw-self (idx 88)"
                elif slot == 89:
                    label = " <- CalcAbsoluteArea (idx 89)"
                print("    slot %3d: 0x%08X%s" % (slot, fn if fn else 0, label))

            # Disassemble slot 88 (draw-self)
            draw_va = read_u32(vtable_start + 88 * 4)
            if draw_va and 0x401000 < draw_va < 0x900000:
                print("\n  === Draw (slot 88) @ 0x%08X ===" % draw_va)
                d_off = va_to_off(draw_va)
                d_code = data[d_off:d_off + 600]
                insn_count = 0
                for insn in md.disasm(d_code, draw_va):
                    print("    0x%08X: %-8s %s" % (insn.address, insn.mnemonic, insn.op_str))
                    insn_count += 1
                    if insn.mnemonic == "ret" or insn_count > 120:
                        break

            # Also disassemble slot 87 (GZPaint)
            gzpaint_va = read_u32(vtable_start + 87 * 4)
            if gzpaint_va and 0x401000 < gzpaint_va < 0x900000:
                print("\n  === GZPaint (slot 87) @ 0x%08X ===" % gzpaint_va)
                g_off = va_to_off(gzpaint_va)
                g_code = data[g_off:g_off + 200]
                insn_count = 0
                for insn in md.disasm(g_code, gzpaint_va):
                    print("    0x%08X: %-8s %s" % (insn.address, insn.mnemonic, insn.op_str))
                    insn_count += 1
                    if insn.mnemonic == "ret" or insn_count > 40:
                        break
            break
