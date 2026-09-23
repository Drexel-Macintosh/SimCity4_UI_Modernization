"""Step 17: direct (E8 rel32 / E9 rel32) callers of given functions, with context."""
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vfn import *
from s7_sites import synced_start

T = TEXT
blob = RAW[T[3]:T[3] + T[4]]


def callers(target):
    out = []
    for op in (0xE8, 0xE9):
        i = blob.find(bytes([op]))
        while i >= 0:
            if i + 5 <= len(blob):
                rel = struct.unpack_from("<i", blob, i + 1)[0]
                if T[1] + i + 5 + rel == target:
                    out.append((T[1] + i, "call" if op == 0xE8 else "jmp"))
            i = blob.find(bytes([op]), i + 1)
    return out


if __name__ == "__main__":
    for a in sys.argv[1:]:
        t = int(a, 16)
        cs = callers(t)
        print(f"\n== callers of {t:08X}: {len(cs)}")
        for va, k in cs:
            st = synced_start(va, 0x28)
            win = disrange(st, va + 5)
            ok = any(i.address == va for i in win)
            pre = [i for i in win if i.address < va][-6:]
            print(f"  {va:08X} {k} {'(synced)' if ok else '(UNSYNCED - may be data)'}: " + " ; ".join(f"{i.mnemonic} {i.op_str}" for i in pre))
