"""Step 6: FlatRect GZPaint 0x9CD1FF, DoMessage 0x9CD718, OnKeyDown/Up 0x9CD75C/0x9CD789,
dtor 0x9CD6FC / 0x9CD1B2, base QI fallthrough."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vfn import *

for va, name in ((0x9CD1FF, "GZPaint (class slot 88)"), (0x9CD718, "DoMessage (class slot 3)"),
                 (0x9CD75C, "slot 130"), (0x9CD789, "slot 131"), (0x9CD6FC, "slot 148 scalar dtor"),
                 (0x9CD1B2, "dtor body")):
    print(f"\n==== {name} {va:08X} rets={rets(va)}")
    print(fmt(fn(va, 200), "   "))
