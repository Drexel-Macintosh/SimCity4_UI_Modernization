"""gate_103_closepath.py  (#103 STOCK LENS, READ-ONLY)

CLAIM UNDER TEST
    Every control the budget dialog wires to itself as a dismiss control must
    reach a handler branch that actually removes the popup [this+0x14] from
    its parent.  If the empty-ledger box's own X (id 0xCC) and backdrop
    (id 0x385) do NOT reach such a branch, the box cannot be closed by its own
    chrome -- in STOCK, at any scale.

POSITIVE CONTROL (mandatory, law: a null is not evidence)
    The ORDINANCE description popup is built by the SAME dialog class and its
    close is USER-CONFIRMED WORKING (v2.28.x).  Its X is id 0x68 and its
    backdrop is id 0x384.  This gate must classify BOTH of those as CLOSING.
    If it does not, the classifier is blind and its verdict on 0xCC is void.

METHOD
    1. decode the handler's jump tables (idx 0x78BC28 / jmp 0x78BC08, base id
       0x67, 0x69 entries) plus the three explicit compares in sub_78B120;
    2. for each branch target, linearly disassemble until the first `ret 8`
       and look for the close idiom:
            mov <r>, [edi+0x14]      ; the popup member
            call [<r>+0x3c]          ; cIGZWin::ChildRemove   (vt index 15)
       edi == `this` throughout sub_78B120 (set at 0x78B135 `mov edi, ecx`).
"""
import os, sys, struct
_HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(_HERE))
import common as C
import capstone

d = C.exe_bytes(); B = 0x400000
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32); md.skipdata = True

IDX, JMP, BASE, N = 0x78BC28, 0x78BC08, 0x67, 0x69

def branch_body(va, limit=0x200):
    out = []
    for ins in md.disasm(d[va-B:va-B+limit], va):
        out.append(ins)
        if ins.mnemonic == "ret":
            break
    return out

def classifies_as_closing(va):
    """True iff the branch reads [edi+0x14] and calls a +0x3c slot on it."""
    ins = branch_body(va)
    saw_member = False
    for i in ins:
        if "[edi + 0x14]" in i.op_str:
            saw_member = True
        if saw_member and i.mnemonic == "call" and "+ 0x3c]" in i.op_str:
            return True, len(ins)
        # a jmp out of the branch: follow one hop
        if i.mnemonic == "jmp" and i.op_str.startswith("0x"):
            t = int(i.op_str, 16)
            if 0x78B120 <= t < 0x78BCA0:
                r, _ = classifies_as_closing(t)
                if r:
                    return True, len(ins)
    return False, len(ins)

idx = d[IDX-B:IDX-B+N]
jt = [struct.unpack_from("<I", d, JMP-B+4*i)[0] for i in range(max(idx)+1)]

targets = {}
for i, b in enumerate(idx):
    targets.setdefault(jt[b], []).append(BASE+i)
# explicit compares in sub_78B120 (verified by disassembly)
for iid, tgt in ((0x384, 0x78B287), (0x385, 0x78B406), (0x451, 0x78B36F),
                 (0x453, 0x78B423), (0x454, 0x78BB6C), (0x42B7C353, 0x78B26E)):
    targets.setdefault(tgt, []).append(iid)

print("exe fingerprint:", C.exe_fingerprint())
print()
verdict = {}
for tgt in sorted(targets):
    closing, n = classifies_as_closing(tgt)
    ids = sorted(set(targets[tgt]))
    shown = ", ".join("0x%X" % i for i in ids[:6]) + (" ..(%d ids)" % len(ids) if len(ids) > 6 else "")
    print("  branch 0x%08X  %-11s  ids: %s" % (tgt, "CLOSES" if closing else "does NOT", shown))
    for i in ids:
        verdict[i] = closing

print()
POS = {0x68: "ordinance popup close-X  (USER-CONFIRMED WORKING)",
       0x384: "ordinance popup backdrop (USER-CONFIRMED WORKING)"}
ok = True
for i, why in POS.items():
    got = verdict.get(i)
    print("  POSITIVE CONTROL id 0x%03X %-42s -> %s" % (i, why, "CLOSES  PASS" if got else "does NOT  *** CLASSIFIER BLIND ***"))
    ok = ok and bool(got)

print()
SUBJ = {0xCC: "empty-ledger box close-X   (sub_77BEC0 @0x77C2C1 -> notify target @0x77C342)",
        0x385: "empty-ledger box backdrop  (sub_77BEC0 @0x77C2A3 -> notify target @0x77C325)"}
for i, why in SUBJ.items():
    print("  SUBJECT          id 0x%03X %s\n%50s-> %s" % (i, why, "", "CLOSES" if verdict.get(i) else "does NOT close the popup"))

print()
if not ok:
    print("OVERALL: VOID - positive control failed, no conclusion may be drawn.")
else:
    print("OVERALL: within its scope, the COMMAND dispatch has no close for 0xCC/0x385.")

print("""
*** SCOPE CORRECTION 2026-08-03 (task #110). READ BEFORE QUOTING THIS GATE. ***

This gate decodes ONE path: the command handler sub_78B120 and its id->branch
tables. It does that correctly. It was then quoted for a claim it CANNOT make -
"the X cannot close the box" - and #103 was closed NOT-A-BUG on that basis.

THAT VERDICT IS REFUTED BY MEASUREMENT. With the whole scaling layer parked
(Set-StockCompare -Mode Stock, 1024x768) the close-X on the empty-ledger box
CLOSES IT. User-confirmed 2026-08-03. So a click on that X does not arrive here
as command 0xCC at all - it travels another route (the notification target the
builder wires at 0x77C342 is the obvious candidate; NOT traced).

The real cause was OURS and is fixed in v2.63.0: the POPBOX pin applied the
ORDINANCE twin's stock height (125) to the empty-ledger twin (stock 100), whose
host IS the 600x127 box, so the y clamp resolved to 127-250 = -123 and put the
close-X at host-local y=-101 - above the host rect, where the router's hit walk
never descends. Logged 19 times as `POPBOX 600x127 -> 600x250 at y=-123`.
Confirmed by isolation: PopupWrap=0 at 2x restored the X (and reintroduced the
ordinance twin's text clip, which is why the cure is per-twin).

THE LESSON, and it is the third time today: a gate that answers its own question
correctly still says NOTHING about a question nobody checked it could answer.
The positive control here proved the CLASSIFIER could spot a close idiom. It
never proved this handler is the path a mouse click takes.
""")
