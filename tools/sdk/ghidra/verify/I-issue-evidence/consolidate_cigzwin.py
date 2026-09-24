r"""One table for an upstream issue: every cIGZWin declaration's compiled slot
against its exe slot, with the exe slot's evidence.

    python tools\sdk\ghidra\verify\I-issue-evidence\consolidate_cigzwin.py

Sources, all committed next door:
  A-full-probe\slots.json    compiled slot of all 147 declarations (MSVC,
                             read two ways), plus exe slots decoded or
                             established for 43 of them
  B-second-class-exe-decode\slot_table.json
                             59 exe slots decoded from the code of 15 window
                             classes, each with its semantics and a verdict
                             against the Mac name at that slot

A declaration's exe slot is A's value when A has one. Otherwise it is the Mac
slot, but only where B decoded that exe slot and B's verdict agrees with the
Mac name. Anything else is UNDECODED: the issue makes no claim about it.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
V = os.path.dirname(HERE)
A = json.load(open(os.path.join(V, "A-full-probe", "slots.json")))["rows"]
BJ = {int(k): v for k, v in json.load(open(os.path.join(V, "B-second-class-exe-decode", "slot_table.json"))).items()}
B = {}
with open(os.path.join(V, "B-second-class-exe-decode", "slot_table.tsv"), encoding="utf-8") as f:
    head = f.readline().rstrip("\n").split("\t")
    for line in f:
        c = line.rstrip("\n").split("\t")
        if c and c[0].isdigit():
            # the last three columns are semantics, verdict, confidence
            B[int(c[0])] = dict(mac=c[2], sem=c[-3], verdict=c[-2], conf=c[-1], ret=BJ.get(int(c[0]), {}).get("ret"))


def b_agrees(slot):
    v = B.get(slot)
    return v is not None and v["verdict"].lower().startswith("agree")


# The gate's table: each row decoded from the exe function's own body. Read
# as data (the gate runs its checks when imported).
import ast
_gate_src = open(os.path.join(V, "..", "..", "..", "..", "_tests", "Test-GZWinHeaderSlots.py"), encoding="utf-8").read()
GATE = next(ast.literal_eval(n.value) for n in ast.parse(_gate_src).body
            if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "EXE_SLOT")
names = [r["name"] for r in A]

# Stack bytes a thiscall callee pops for these argument types (x86).
BYVAL = {"cRZRect": 16, "cRZPoint": 8, "cRZColor": 4, "int64_t": 8, "uint64_t": 8, "double": 8}


def arg_bytes(sig):
    inner = sig[sig.index("(") + 1:sig.rindex(")")].strip()
    if inner in ("", "void"):
        return 0
    total = 0
    for a in inner.split(","):
        a = a.strip()
        if "&" in a or "*" in a:
            total += 4
        else:
            total += BYVAL.get(a.replace("const", "").strip(), 4)
    return total


# Identified from their own bodies in the base vtable 0x00ADC8D8 (2026-09-23):
#   77  0x0099B980  forwards the message to the key accelerator at [this+0x78]
#   80  0x0099BE94  compares own slot 81's answer with [this+0x9C]; ret 8
#   111 0x0099CA91  stores its 4-byte argument at [this+0xD0]; ret 4
#   112 0x0099CA9E  copies [this+0xD0] out through its argument
BODY = {"AccelerateKeyboardMsg": 77, "CheckKeyEquivalent": 80, "SetShadeColor": 111, "GetShadeColor": 112}
# The last 51, read one by one from dump_undecoded.py's output (2026-09-23).
# Each body does what the name says, so the header's slot is right for all 51.
# Where a pair shares a field or calls the other, the pair confirms both.
BODY.update({
    "AddRef": 1,                        # inc [ecx+0xC]; Release (2) decrements it
    "DoMessage": 3,                     # runs the filters at +0x88, then the jump table 0x99CEF9
    "Shutdown": 5,                      # drops the accelerator and filters, HideWindow, deletes children
    "GetWindowManager": 6, "SetWindowManager": 7,       # +0x4
    "GetKeyboard": 8, "SetKeyboard": 9,                 # +0x8
    "SetParentWin": 12,                 # old parent->ChildRemove(this); stores +0x48 (GetParentWin's field)
    "ChildAdd": 14,                     # jmp 0x99E207: IsWindowValid, not already listed, child->SetParentWin(this)
    "ChildRemove": 15,                  # jmp 0x99E2BD: finds the child in the list and removes it
    "ChildDelete": 16,                  # forwards to the window manager's DestroyWindow; message type 1 calls it
    "ChildDeleteAbsolute": 17,          # IsWindowValid, AddRef, Shutdown, ChildRemove, DestroyWindow, Release
    "ChildDeleteAll": 18,               # DestroyWindow on every child
    "IsWinInParentChain": 21,           # walks GetParentWin comparing with the argument
    "IsWinInChildChain": 22,            # recursive walk of the child list
    "PullToFront": 23,                  # parent->ChildToFront(this) (slot 26)
    "SendToBack": 24,                   # parent->ChildToBack(this) (slot 27)
    "ChildToBack": 27,                  # removes the child and re-inserts it at the list's end
    "ChildStepFront": 28,               # swaps with the previous node; the list's head is the front
    "ChildStepBack": 29,                # swaps with the next node
    "MoveRelativeTo": 30,               # parent->ChildMoveRelative(this, arg1, arg2)
    "ChildMoveRelative": 31,            # both arguments must be children; reorders them
    "SortChildren": 33,                 # default comparator 0x99BC0E; needs at least 2 children
    "GetWindowFromPoint": 38,           # forwards to the window manager's GetWindowFromPoint
    "GetChildWindowFromPoint": 39,      # recursive hit test over visible children
    "GetChildWindowFromCursorPoint": 40,  # the same, skipping flag 0x200000
    "WindowToWindowCoordinates": 61,    # this->WindowToScreen (60), other->ScreenToWindow (59)
    "IsPointInWindowScreenCoordinates": 62,  # tests the absolute rect at +0x14, then per-pixel 149
    "GetKeyboardAccelerator": 75, "SetKeyboardAccelerator": 76,   # +0x78, the one AccelerateKeyboardMsg uses
    "GetKeyEquivalent": 78, "SetKeyEquivalent": 79,               # +0x9C, the one CheckKeyEquivalent compares
    "MakeKeyEquivalent": 81,            # (arg2 << 16) | (arg1 & 0xFFFF); CheckKeyEquivalent calls it
    "IsChildKeyEquivalent": 82,         # asks each child's CheckKeyEquivalent (80)
    "ProcessCursorMessage": 83,         # takes a message; routes mouse types 7/8 through the children
    "UpdateCursor": 84,                 # uses the cursor at +0x74, fetching a default when none is set
    "SetCursor": 85,                    # stores +0x74, then UpdateCursor (84) when its bool is set
    "CalcAbsoluteArea": 90,             # rect plus every parent's L/T, written to +0x14
    "GetDrawContext": 93,               # returns +0x6C
    "GetBufferToDrawTo": 94,            # returns +0x68, which SetBufferToDrawTo (95) fills
    "SetBufferToDrawTo": 95,            # own private buffer (101), else the nearest parent's
    "SetBufferToDrawToRecursive": 96,   # 95, then each child's 96
    "SetAreaToDrawTo": 97,              # fills +0x24..0x30, which GetAreaToDrawTo (99) returns
    "SetAreaToDrawToRecursive": 98,     # 97, then each child's 98
    "GetAreaToDrawTo": 99,              # lea eax,[ecx+0x24]
    "PrivateBuffer": 100,               # enables/sizes the private buffer at +0x64
    "GetPrivateBuffer": 101,            # returns +0x64
    "MakeFillColor": 108,               # the draw buffer's (or graphics system's) MakeColor(r,g,b)
    "SetFadeEffectPeriod": 109, "GetFadeEffectPeriod": 110,       # +0x94 / +0x98
    "GetParam": 113, "SetParam": 114,   # the param map at +0x7C
})

rows = []
for r in A:
    exe, src = r["exe"], r["exe_src"]
    mac = r["mac"]
    if exe is None and mac is not None and r.get("mac_count", 1) == 1 and b_agrees(mac):
        exe, src = mac, "B-decoded"
    if exe is None and names.count(r["name"]) == 1 and r["name"] in GATE:
        exe, src = GATE[r["name"]], "gate"
    if exe is None and names.count(r["name"]) == 1 and r["name"] in BODY:
        exe, src = BODY[r["name"]], "body"
    ret = B.get(exe, {}).get("ret") if exe is not None else None
    rows.append(dict(hidx=r["hidx"], sig=r["sig"], compiled=r["compiled"], pm=r["compiled_pm"],
                     exe=exe, src=src, hdr_bytes=arg_bytes(r["sig"]), exe_ret=ret))

wrong = [x for x in rows if x["exe"] is not None and x["exe"] != x["compiled"]]
right = [x for x in rows if x["exe"] is not None and x["exe"] == x["compiled"]]
undec = [x for x in rows if x["exe"] is None]
two_ways = all(x["compiled"] == x["pm"] for x in rows)
print("147 declarations: %d decoded against the exe (%d wrong, %d right), %d undecoded"
      % (len(wrong) + len(right), len(wrong), len(right), len(undec)))
print("compiled slot read two ways (call site, member-pointer thunk) agree on every row: %s" % two_ways)
print("\nWRONG (header hidx: declaration -> compiles to / exe slot [evidence]):")
for x in wrong:
    print("  %3d  %-58s %3d / %3d  [%s]" % (x["hidx"], x["sig"][:58], x["compiled"], x["exe"], x["src"]))
print("\nUNDECODED hidx: %s" % ", ".join(str(x["hidx"]) for x in undec))
abi = [x for x in rows if x["exe_ret"] is not None and x["exe_ret"] != x["hdr_bytes"]]
print("\nARGUMENT BYTES: header vs the exe function's own `ret N` (%d decoded rows carry a ret):"
      % sum(1 for x in rows if x["exe_ret"] is not None))
for x in abi:
    print("  %3d  %-58s header pushes %2d, exe pops %2d" % (x["hidx"], x["sig"][:58], x["hdr_bytes"], x["exe_ret"]))

# The per-slot argument-count census (A-full-probe\exe_argc.txt, every slot whose
# own `ret N` could be read) and the two same-size mismatches that only the
# bodies show: the game takes the colour BY VALUE at 105 and 111.
argc = []
for line in open(os.path.join(V, "A-full-probe", "exe_argc.txt"), encoding="utf-8"):
    if "I-ARGC!" in line:
        argc.append(line.split("|")[2].replace("I-ARGC!", "").split(None, 1)[1].strip())
BYVAL_DEFECTS = {"bool SetFillColor(cRZColor const&)": (105, "0x0099BF5E: mov eax,[esp+4]; mov [ecx+0xD4],eax"),
                 "void SetShadeColor(cRZColor const&)": (111, "0x0099CA91: mov eax,[esp+4]; mov [ecx+0xD0],eax")}
readable = sum(1 for line in open(os.path.join(V, "A-full-probe", "exe_argc.txt"), encoding="utf-8")
               if "exe=" in line and "exe=None" not in line)
print("\nARGUMENT LISTS: %d count mismatches (census of %d slots with a readable ret) + %d by-value colours = %d"
      % (len(argc), readable, len(BYVAL_DEFECTS), len(argc) + len(BYVAL_DEFECTS)))
for s in argc:
    print("  count     " + s)
for s, (slot, why) in BYVAL_DEFECTS.items():
    print("  by value  %s  (game slot %d, %s)" % (s, slot, why))
json.dump(dict(count=argc, byvalue=list(BYVAL_DEFECTS), readable=readable),
          open(os.path.join(HERE, "cigzwin_argument_lists.json"), "w"), indent=1)
json.dump(dict(wrong=wrong, right=right, undecoded=undec),
          open(os.path.join(HERE, "cigzwin_consolidated.json"), "w"), indent=1)
sys.exit(0)
