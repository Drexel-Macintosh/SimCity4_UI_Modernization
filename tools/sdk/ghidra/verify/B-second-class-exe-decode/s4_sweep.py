"""Step 4: linear capstone sweep of .text, saved once as a compact text index
(addr mnemonic ops) so later greps are fast. Writes sweep.txt next to this file.
Linear sweep can desync inside jump tables; it resyncs quickly on x86 and is only
used for FINDING candidate sites, each of which is then read with s3_dis.py."""
import sys
sys.path.insert(0, __file__.rsplit("\\", 1)[0])
from pe import *

out = open(__file__.rsplit("\\", 1)[0] + "\\sweep.txt", "w")
a, b = TEXT[1], TEXT[2]
code = rd(a, b - a)
off = 0
md.skipdata = True
n = 0
for ins in md.disasm(code, a):
    out.write(f"{ins.address:08X} {ins.mnemonic} {ins.op_str}\n")
    n += 1
out.close()
print("instructions", n)
