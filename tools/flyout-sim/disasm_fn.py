"""
disasm_fn.py - reusable function disassembler for SimCity 4.exe.

Uses the SAME 1:1 file-offset == RVA mapping the emulator relies on
(fileoff = VA - IMAGE_BASE), so any address that runs under emu_plot.py
disassembles here identically. Follows the function until the first balanced
`ret`/`retn` at depth 0 (tracks push/pop-less, just stops at ret) or a length
cap. Prints VA, bytes, mnemonic; flags call targets so we can chase helpers.

Usage:  python disasm_fn.py 0x8d8bc0            # arc helper
        python disasm_fn.py 0x8d8bc0 --max=400  # cap instruction count
        python disasm_fn.py 0x79b0e0 --calls    # also list unique call targets
"""
import sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

EXE = r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Apps\SimCity 4.exe"
IMAGE_BASE = 0x400000

def main():
    va = int(sys.argv[1], 0)
    maxins = 4000
    show_calls = "--calls" in sys.argv
    nostop = "--nostop" in sys.argv   # keep going past early-out rets
    grep = None
    for a in sys.argv:
        if a.startswith("--max="):
            maxins = int(a.split("=", 1)[1], 0)
        if a.startswith("--grep="):
            grep = a.split("=", 1)[1]   # only print lines whose op_str/target contains this

    data = open(EXE, "rb").read()
    off = va - IMAGE_BASE
    if off < 0 or off >= len(data):
        print("VA out of file range"); return
    blob = data[off:off + maxins * 8]

    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = True
    calls = []
    n = 0
    depth_ret = 0
    for ins in md.disasm(blob, va):
        n += 1
        b = ins.bytes.hex()
        line = "0x%08X:  %-20s %s %s" % (ins.address, b, ins.mnemonic, ins.op_str)
        # annotate calls to sub_XXXX targets
        if ins.mnemonic == "call" and ins.op_str.startswith("0x"):
            try:
                tgt = int(ins.op_str, 0)
                calls.append(tgt)
                line += "   ; -> sub_%X" % tgt
            except ValueError:
                pass
        if grep is None or grep.lower() in line.lower():
            print(line)
        if ins.mnemonic in ("ret", "retn", "retf"):
            if not nostop:
                # default: stop at first ret. Use --nostop for functions with
                # early-out branches (the ret is not the true end).
                print("--- ret ---")
                break
        if n >= maxins:
            print("--- hit max (%d) ---" % maxins); break

    if show_calls and calls:
        print("\n=== unique call targets ===")
        for t in sorted(set(calls)):
            print("  sub_%X" % t)

if __name__ == "__main__":
    main()
