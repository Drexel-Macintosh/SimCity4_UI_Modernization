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

# Parse PE headers to find section boundaries
pe_off = struct.unpack_from("<I", data, 0x3C)[0]
num_sections = struct.unpack_from("<H", data, pe_off + 6)[0]
opt_hdr_size = struct.unpack_from("<H", data, pe_off + 20)[0]
sect_off = pe_off + 24 + opt_hdr_size
print("PE sections:")
text_start = text_end = rdata_start = rdata_end = 0
for i in range(num_sections):
    off = sect_off + i * 40
    name = data[off:off+8].rstrip(b"\x00").decode("ascii", errors="replace")
    vsize, rva, rawsize, rawptr = struct.unpack_from("<IIII", data, off + 8)
    va_start = IMAGE_BASE + rva
    va_end = va_start + vsize
    print("  %-8s VA 0x%08X-0x%08X  raw 0x%06X sz 0x%06X" % (name, va_start, va_end, rawptr, rawsize))
    if name == ".text":
        text_start, text_end = va_start, va_end
    elif name == ".rdata":
        rdata_start, rdata_end = va_start, va_end

def is_code_ptr(fn):
    return fn is not None and text_start <= fn < text_end

# Dump known vtables with correct range
md = Cs(CS_ARCH_X86, CS_MODE_32)

for name, vt in [("cSC4WinGenTransparent", 0xAB7358), ("cSC4WinRCI", 0xAB8628)]:
    print("\n=== %s vtable @ 0x%08X ===" % (name, vt))
    for slot in range(105):
        fn = read_u32(vt + slot * 4)
        if not is_code_ptr(fn):
            print("  slot %d: 0x%08X (end)" % (slot, fn if fn else 0))
            break
        label = ""
        if slot == 87: label = " GZPaint"
        elif slot == 88: label = " Plot/draw"
        elif slot == 89: label = " CalcAbsArea"
        elif slot == 90: label = " InvalidateSelf"
        elif slot == 91: label = " InvalidateSelfAndParents"
        print("  slot %d: 0x%08X%s" % (slot, fn, label))

# Now find cSC4WinMiniMap vtable: search .rdata for a vtable-sized block
# that has the same base-class slots as cSC4WinGenTransparent but a
# DIFFERENT slot 88 (Draw override).
print("\n=== Searching for minimap vtable ===")
gt_vt = 0xAB7358
# Get the base class slots (0-86 should be shared)
base_slots = []
for slot in range(87):
    fn = read_u32(gt_vt + slot * 4)
    base_slots.append(fn)

# Search .rdata for vtables that match slots 0-10 but differ at slot 88
gt_draw = read_u32(gt_vt + 88 * 4)
print("GenTransparent Draw (slot 88) = 0x%08X" % gt_draw)

pos = va_to_off(rdata_start)
end = va_to_off(rdata_end)
candidates = []
while pos < end - 400:
    # Check if this looks like a vtable: first 4 entries match base class
    match = True
    for slot in range(4):
        fn = struct.unpack_from("<I", data, pos + slot * 4)[0]
        if fn != base_slots[slot]:
            match = False
            break
    if match:
        va = pos + IMAGE_BASE
        draw_fn = struct.unpack_from("<I", data, pos + 88 * 4)[0]
        if is_code_ptr(draw_fn) and draw_fn != gt_draw:
            candidates.append((va, draw_fn))
            print("  candidate vtable @ 0x%08X, Draw=0x%08X" % (va, draw_fn))
    pos += 4

# Disassemble each candidate's Draw method
for vt_va, draw_va in candidates:
    print("\n=== Draw @ 0x%08X (vtable 0x%08X) ===" % (draw_va, vt_va))
    d_off = va_to_off(draw_va)
    d_code = data[d_off:d_off + 600]
    insn_count = 0
    for insn in md.disasm(d_code, draw_va):
        print("  0x%08X: %-8s %s" % (insn.address, insn.mnemonic, insn.op_str))
        insn_count += 1
        if insn.mnemonic == "ret" or insn_count > 120:
            break
