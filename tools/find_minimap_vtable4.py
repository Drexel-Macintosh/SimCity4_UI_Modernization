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

text_start, text_end = 0x407000, 0xA7FA2D
rdata_start, rdata_end = 0xA80000, 0xB06A2A

def is_code_ptr(fn):
    return fn is not None and text_start <= fn < text_end

# Shared base class signature: slots 6-10 from known vtables
# slot 6=0x9D7E63, 7=0x99CA0B, 8=0x9C32AC, 9=0x99BF01, 10=0x99BE2A
base_sig = [0x9D7E63, 0x99CA0B, 0x9C32AC, 0x99BF01, 0x99BE2A]
default_draw = 0x9995E7  # GenTransparent's slot 88 (base default)

md = Cs(CS_ARCH_X86, CS_MODE_32)

print("Searching .rdata for cIGZWin vtables with custom Draw...")
pos = va_to_off(rdata_start)
end = va_to_off(rdata_end)
found = []
while pos < end - 420:  # need at least 105 slots
    # Check slots 6-10 match base signature
    match = True
    for i, expected in enumerate(base_sig):
        fn = struct.unpack_from("<I", data, pos + (6 + i) * 4)[0]
        if fn != expected:
            match = False
            break
    if match:
        vt_va = pos + IMAGE_BASE
        draw_fn = struct.unpack_from("<I", data, pos + 88 * 4)[0]
        if is_code_ptr(draw_fn) and draw_fn != default_draw:
            # Also get slot 0 (destructor/GetClassID area) for identification
            slot0 = struct.unpack_from("<I", data, pos)[0]
            slot87 = struct.unpack_from("<I", data, pos + 87 * 4)[0]
            found.append((vt_va, draw_fn, slot0, slot87))
            print("  vtable @ 0x%08X  Draw=0x%08X  slot0=0x%08X  GZPaint=0x%08X" %
                  (vt_va, draw_fn, slot0, slot87))
    pos += 4

print("\nFound %d vtables with custom Draw" % len(found))

# Disassemble each unique Draw
seen_draws = set()
for vt_va, draw_va, slot0, slot87 in found:
    if draw_va in seen_draws:
        continue
    seen_draws.add(draw_va)
    print("\n=== Draw @ 0x%08X (vtable 0x%08X) ===" % (draw_va, vt_va))
    d_off = va_to_off(draw_va)
    d_code = data[d_off:d_off + 800]
    insn_count = 0
    for insn in md.disasm(d_code, draw_va):
        print("  0x%08X: %-8s %s" % (insn.address, insn.mnemonic, insn.op_str))
        insn_count += 1
        if insn.mnemonic == "ret" or insn_count > 150:
            break
