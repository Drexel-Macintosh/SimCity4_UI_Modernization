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

md = Cs(CS_ARCH_X86, CS_MODE_32)

# Known: cSC4WinRCI vtable 0xAB8628, clsid 0xC7A0E17E
# Check what slot 0 (0x7A92D0) does - is it GetClassID?
print("=== cSC4WinRCI slot 0 @ 0x7A92D0 ===")
off = va_to_off(0x7A92D0)
code = data[off:off+32]
for insn in md.disasm(code, 0x7A92D0):
    print("  0x%08X: %s %s" % (insn.address, insn.mnemonic, insn.op_str))
    if insn.mnemonic == "ret":
        break

# Check the minimap's GetClassID candidate at 0x7A6581
print("\n=== Minimap GetClassID candidate @ 0x7A6581 ===")
off = va_to_off(0x7A6581)
code = data[off:off+16]
for insn in md.disasm(code, 0x7A6581):
    print("  0x%08X: %s %s" % (insn.address, insn.mnemonic, insn.op_str))
    if insn.mnemonic == "ret":
        break

# Now search all candidate vtables: for each, check if slot 0's function
# body contains the minimap clsid 0xCA318388
print("\n=== Searching vtables for minimap clsid in slot 0 ===")
candidates = [
    0xA8D000, 0xA92F28, 0xAA56C0, 0xAA5920, 0xAAB0F8,
    0xAACE58, 0xAAD130, 0xAAD410, 0xAADAB8, 0xAADEE8,
    0xAAE270, 0xAAE630, 0xAAF510, 0xAAF8E8, 0xAAFC20,
    0xAB46A0, 0xAB4D08, 0xAB58B0, 0xAB5B48, 0xAB5DA8,
    0xAB6010, 0xAB64B8, 0xAB6770, 0xAB6AA8, 0xAB6D88,
    0xAB7078, 0xAB78F0, 0xAB7B58, 0xAB83B8, 0xAB8628,
    0xAB88C0, 0xAB8CD0, 0xAB8F50, 0xAB9260, 0xAB9658,
    0xAB9980, 0xAB9BF8, 0xAB9EB8, 0xABA190, 0xABA430,
    0xABA770, 0xABCBC0, 0xABF210, 0xAC73D0, 0xACD0D8,
    0xAD6AA0, 0xADBC78, 0xADC398, 0xADCF30, 0xADD7B0,
    0xADDAF0, 0xADE188, 0xADE648, 0xADEA90, 0xADEEC0,
    0xADF2E8, 0xADF6A0, 0xADFBD0, 0xADFEB8, 0xAE0240,
    0xAE04D8, 0xAE0810, 0xAE0B90, 0xAE0FB0, 0xAE1300,
    0xAE1780, 0xAE1AC8, 0xAE1D60, 0xAE20A0, 0xAE2398,
    0xAE2648, 0xAE2970, 0xAE2C90, 0xAE2FE0, 0xAE3508,
    0xAE37E8, 0xAE3B28, 0xAE3D88, 0xAE40F0, 0xAE4398,
]

clsid_bytes = struct.pack("<I", 0xCA318388)
for vt in candidates:
    slot0_fn = read_u32(vt)
    if slot0_fn is None:
        continue
    # Read the function body (first 32 bytes) and check for clsid
    fn_off = va_to_off(slot0_fn)
    fn_body = data[fn_off:fn_off + 32]
    if clsid_bytes in fn_body:
        draw_fn = read_u32(vt + 88 * 4)
        print("  FOUND! vtable @ 0x%08X, slot0=0x%08X, Draw=0x%08X" % (vt, slot0_fn, draw_fn))

        # Disassemble the Draw method
        print("\n  === MiniMap Draw @ 0x%08X ===" % draw_fn)
        d_off = va_to_off(draw_fn)
        d_code = data[d_off:d_off + 1024]
        insn_count = 0
        for insn in md.disasm(d_code, draw_fn):
            print("    0x%08X: %-8s %s" % (insn.address, insn.mnemonic, insn.op_str))
            insn_count += 1
            if insn.mnemonic == "ret" or insn_count > 200:
                break
