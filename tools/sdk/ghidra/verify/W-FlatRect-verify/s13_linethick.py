"""Step 13: does the Windows draw context have a line-thickness state that the
FlatRect GZPaint leaves alone?  Mac cIGZDrawContext: slot 25 (vt+0x64)
SetLineThickness, slot 34 (vt+0x88) Line, slot 35 (vt+0x8C) Fill, 20/21 SetColor.
Scan .text for functions that load the DC from [win+0x6C] and call vt+0x64
with an immediate; print them. Positive control: the same scan must find the
FlatRect GZPaint's vt+0x88 Line calls (0x9CD277 etc.)."""
import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vfn import *

T = TEXT
blob = RAW[T[3]:T[3] + T[4]]

def calls_at(disp):
    """call dword ptr [reg+disp] encodings: ff 50+r disp8 (r!=esp) or ff 90+r disp32"""
    out = []
    if disp < 0x80:
        pat = re.compile(rb"\xff[\x50-\x53\x55-\x57]" + bytes([disp]))
    else:
        pat = re.compile(rb"\xff[\x90-\x93\x95-\x97]" + disp.to_bytes(4, "little"))
    for m in pat.finditer(blob):
        out.append(T[1] + m.start())
    return out

line = set(calls_at(0x88))
thick = calls_at(0x64)
print("positive control: FlatRect GZPaint Line calls found:",
      [hex(a) for a in (0x9CD277, 0x9CD2A3, 0x9CD2CB, 0x9CD2F3) if a in line])
# thickness calls within 0x100 bytes BEFORE a Line call, where the instruction
# stream shows a [reg+0x6c] load in between (DC from a cGZWin)
hits = []
for t in thick:
    near = [l for l in line if 0 < l - t < 0x100]
    if not near:
        continue
    # decode window to confirm a push imm before the thickness call and a +0x6c load
    st = t - 0x30
    win = disrange(st, t + 6)
    ok = [i for i in win if i.address == t]
    if not ok:
        continue
    pre = [i for i in win if i.address < t][-6:]
    s = " ; ".join(f"{i.mnemonic} {i.op_str}" for i in pre)
    if "0x6c]" in s:
        hits.append((t, s, near[0]))
print("thickness-candidate calls (vt+0x64 on a [x+0x6c] DC, followed by a vt+0x88 call):", len(hits))
for t, s, l in hits[:40]:
    print(f"  {t:08X}: ... {s}  -> line call {l:08X}")
