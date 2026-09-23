"""Step 10: build the .UI keyword-token table from the registration pattern
   push <token> ; push <str> ; lea ecx,[..] ; call 0x408480 ; ... ; call [reg+0xc]
anywhere in .text, then decode the FlatRect applier 0x94E33B."""
import sys, os, struct, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vfn import *

T = TEXT
blob = RAW[T[3]:T[3] + T[4]]
tok = {}
# pattern: 68 <tok4> 68 <str4> 8d 4d xx e8 <rel32 -> 0x408480>
for m in re.finditer(rb"\x68(....)\x68(....)\x8d\x4d.\xe8(....)", blob, re.S):
    va = T[1] + m.start()
    t = struct.unpack("<I", m.group(1))[0]
    s = struct.unpack("<I", m.group(2))[0]
    rel = struct.unpack("<i", m.group(3))[0]
    call_end = va + m.end() - m.start()
    if call_end + rel != 0x408480:
        continue
    if secname(s) != ".rdata":
        continue
    txt = rd(s, 48).split(b"\0")[0]
    try:
        txt = txt.decode("ascii")
    except UnicodeDecodeError:
        continue
    tok.setdefault(t, set()).add(txt)
print("tokens harvested:", len(tok))
for t in (0x104, 0x200, 0x201, 0x202, 0x203, 0x204, 0x205, 0x206, 0x207, 0x208, 0xF005, 0xF006, 0xF007, 0xF00B, 0xF00C, 0xF00D, 0xF00E, 0xF01D):
    print(f"  token {t:#06x}: {sorted(tok.get(t, []))}")
# which token is 'fill', 'autosize', 'sizemode' etc.?
inv = {}
for t, ss in tok.items():
    for s in ss:
        inv.setdefault(s, []).append(t)
for s in ("fill", "nofill", "all", "lrb", "trb", "autosize", "sizemode", "style", "fillcolor", "winflag_sizeable", "raised", "sunken", "left", "right", "top", "bottom"):
    print(f"  '{s}': {[hex(x) for x in inv.get(s, [])]}")

print("\n==== applier 0x94E33B")
print(fmt(fn(0x94E33B, 300), "   "))
