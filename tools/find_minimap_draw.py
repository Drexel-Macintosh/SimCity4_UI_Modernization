"""Find cSC4WinMiniMap's vtable and disassemble its Draw method (slot 88).

Uses the class registration pattern from DYNAMIC-CONTROLS.md:
  push <factory>; push <clsid>; mov ecx,esi; call 0x90E133
at VA 0x4662B0 region. clsid = 0xCA318388.
"""
import struct, sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

EXE = r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Apps\SimCity 4.exe"
IMAGE_BASE = 0x400000
CLSID_MINIMAP = 0xCA318388

with open(EXE, "rb") as f:
    data = f.read()

def va_to_off(va):
    return va - IMAGE_BASE

def read_u32(va):
    off = va_to_off(va)
    if 0 <= off < len(data) - 4:
        return struct.unpack_from("<I", data, off)[0]
    return None

# --- Step 1: Find the registration site for clsid 0xCA318388 ---
# Pattern: 68 88 83 31 CA  (push 0xCA318388)
clsid_bytes = struct.pack("<I", CLSID_MINIMAP)
push_pattern = b"\x68" + clsid_bytes

print("=== Searching for push 0x%08X ===" % CLSID_MINIMAP)
sites = []
pos = 0
while True:
    idx = data.find(push_pattern, pos)
    if idx < 0:
        break
    va = idx + IMAGE_BASE
    sites.append(va)
    print("  push clsid @ VA 0x%08X (file off 0x%06X)" % (va, idx))
    pos = idx + 1

# --- Step 2: For each site, look backwards for the factory push ---
# Pattern: 68 <factory_va> 68 <clsid> ... call
for site_va in sites:
    site_off = va_to_off(site_va)
    # Look back 1-10 bytes for another push (0x68)
    for back in range(5, 20):
        off = site_off - back
        if off >= 0 and data[off] == 0x68:
            factory_va = struct.unpack_from("<I", data, off + 1)[0]
            if 0x400000 < factory_va < 0xA00000:
                print("\n  Likely factory: push 0x%08X @ VA 0x%08X" % (factory_va, off + IMAGE_BASE))

                # --- Step 3: Disassemble the factory to find the constructor ---
                md = Cs(CS_ARCH_X86, CS_MODE_32)
                md.detail = True
                f_off = va_to_off(factory_va)
                f_code = data[f_off:f_off + 128]
                print("\n  === Factory @ 0x%08X ===" % factory_va)
                ctor_va = None
                for insn in md.disasm(f_code, factory_va):
                    print("    0x%08X: %s %s" % (insn.address, insn.mnemonic, insn.op_str))
                    # Look for call to constructor (typically: call <ctor>)
                    if insn.mnemonic == "call" and insn.op_str.startswith("0x"):
                        target = int(insn.op_str, 16)
                        if 0x400000 < target < 0xA00000:
                            ctor_va = target
                    if insn.mnemonic == "ret":
                        break

                if ctor_va:
                    print("\n  === Constructor @ 0x%08X ===" % ctor_va)
                    c_off = va_to_off(ctor_va)
                    c_code = data[c_off:c_off + 256]
                    vtable_va = None
                    for insn in md.disasm(c_code, ctor_va):
                        print("    0x%08X: %s %s" % (insn.address, insn.mnemonic, insn.op_str))
                        # vtable set: mov dword ptr [ecx+4], <vtable>
                        # or: mov dword ptr [esi], <vtable>
                        if insn.mnemonic == "mov" and "0x" in insn.op_str:
                            # Check if it's setting a vtable pointer
                            parts = insn.op_str.split(",")
                            if len(parts) == 2:
                                val_str = parts[1].strip()
                                if val_str.startswith("0x"):
                                    val = int(val_str, 16)
                                    # vtable should be in .rdata (0x680000+)
                                    if 0x680000 < val < 0xB00000:
                                        vtable_va = val
                                        print("    ** VTABLE candidate: 0x%08X **" % val)
                        if insn.mnemonic == "ret":
                            break

                    if vtable_va:
                        print("\n  === VTable @ 0x%08X ===" % vtable_va)
                        # Dump first 100 slots
                        for slot in range(100):
                            slot_va = vtable_va + slot * 4
                            fn = read_u32(slot_va)
                            if fn is None or fn < 0x400000 or fn > 0xA00000:
                                print("    slot %d: 0x%08X (end of vtable?)" % (slot, fn if fn else 0))
                                break
                            label = ""
                            if slot == 87: label = " <- GZPaint"
                            elif slot == 88: label = " <- Plot (draw-self)"
                            elif slot == 89: label = " <- CalcAbsoluteArea"
                            elif slot == 90: label = " <- InvalidateSelf"
                            elif slot == 91: label = " <- InvalidateSelfAndParents"
                            print("    slot %d: 0x%08X%s" % (slot, fn, label))

                        # --- Step 4: Disassemble Draw (slot 88) ---
                        draw_va = read_u32(vtable_va + 88 * 4)
                        if draw_va:
                            print("\n  === Draw (slot 88) @ 0x%08X ===" % draw_va)
                            d_off = va_to_off(draw_va)
                            d_code = data[d_off:d_off + 512]
                            for insn in md.disasm(d_code, draw_va):
                                print("    0x%08X: %s %s" % (insn.address, insn.mnemonic, insn.op_str))
                                if insn.mnemonic == "ret":
                                    break
                break
