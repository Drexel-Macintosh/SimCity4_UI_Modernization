"""gate_ordinance_namex.py - the OFFLINE GATE for the ordinance NAME-COLUMN x
re-encode (the 136 -> 127 push-imm8 clamp at 0x0077CC23 / 0x0077D0E0).

STATUS OF THE THING IT GATES: HELD, NOT SHIPPING.  This gate exists so the
re-encode is *ready* and can never ship un-round-tripped, per the standing law
that a block re-encode must be capstone round-tripped in a durable artifact
(pattern: gate_graphlegend_leftanchor.py).  See
tools\\research\\_incoming\\SHUTDOWN-SPIN.md section 3 for why it is held.

WHAT THIS ADJUDICATES (law 44 - a probe must adjudicate the FIX, not sight it)

  Two 43-byte windows create the ordinance NAME text of the income and expense
  sections via sub_779660, passing x as `push 0x44` (68).  At f=2 the intended
  value is 136 and `push imm8` cannot hold it, so the shipped applier clamps to
  127; at f=3 it wants 204 and still ships 127 (-77 px).  The candidate cure
  re-encodes each 43-byte window so x becomes `push imm32`, IN PLACE, with the
  same length, the same ten arguments in the same order, the same final ESP,
  and the frame spill/reload preserved.

  This file asserts exactly that, and NOTHING about how the result looks on
  screen.  SCOPE (law 42): encoding + stack shape only.  It cannot tell you the
  name column clears the eye at 3x; only eyes-on can, and the #98 law says a
  static-only layout change must not ship without it.

GREEN means, for both windows and every tier in {1.0, 1.5, 2.0, 3.0}:
  * the stock 43 bytes still match the shipped exe (fingerprint pinned)
  * the model's ESP tracker reproduces stock's own spill/reload aliasing -
    the POSITIVE CONTROL that the tracker can see this class of bug at all
  * f = 1.0 and f = 1.5 emit NO write (reduce-to-stock / imm8 still fits)
  * the replacement decodes to exactly 43 bytes, 10 pushes, identical
    argument values except arg3 (x), identical net ESP delta
  * the replacement's spill store and reload resolve to the SAME frame slot
    as stock's do
  * no branch anywhere in sub_77C660 targets an address inside either window

Run from the repo root:
    python tools\\uimap\\emu\\gate_ordinance_namex.py
    python tools\\uimap\\emu\\gate_ordinance_namex.py --verbose
Exit code 0 = green.
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))          # tools\uimap (common.py)

import common                                        # noqa: E402

# ⚠ RE-PINNED 2026-08-05 (was 1189720d5e15b0e1). The game was wiped and
# reinstalled from Steam, and the new exe is a DIFFERENT binary of the same
# size (7,876,608) - so the build this gate was originally derived from no
# longer exists on disk and cannot be diffed against.
# THE RE-PIN WAS EARNED, NOT ASSUMED: every byte-level site assertion in this
# gate was run against the new exe FIRST, with the fingerprint check bypassed,
# and all of them passed - the instructions this gate reasons about are
# identical. Re-pinning a fingerprint because a tool said no, without checking
# the bytes, is exactly how the #140 splash shipped CAM art. Do not do it.
# The value below is the LAA-MASKED hash (see common.exe_fingerprint): the
# 4GB patch flips one header bit and used to move this hash on its own.
EXPECT_FP = "f9b059d29940d1a2"
FUNC_LO, FUNC_HI = 0x0077C660, 0x0077D7E0            # the ordinance builder

# --------------------------------------------------------------------------
# THE TWO WINDOWS.  Stock bytes are VERIFIED against the exe, never quoted.
# --------------------------------------------------------------------------
WINDOWS = [
    dict(
        name="income  ordinance-name x  (site 0x0077CC23)",
        va=0x0077CBFC, length=43, site=0x0077CC23, y_disp=0x98,
        stock="8b56106a666a556a446805d385ea895424248b106a008bc8ff521c"
              "8b4c2428508b8698000000506a445551",
    ),
    dict(
        name="expense ordinance-name x  (site 0x0077D0E0)",
        va=0x0077D0B9, length=43, site=0x0077D0E0, y_disp=0x9C,
        stock="8b4e108b106a666a556a446805d385ea894c24246a008bc8ff521c"
              "8b4c2428508b869c000000506a445551",
    ),
]

STOCK_X = 68          # push 0x44
IMM8_CEIL = 127       # what a push imm8 can hold
TIERS = (1.0, 1.5, 2.0, 3.0)


def r(v):
    """The project's rounding, matching CodePatches' round(stock * f)."""
    return int(v + 0.5)


def wanted_x(f):
    return r(STOCK_X * f)


def should_reencode(f):
    """The gate the fix ships behind: only when imm8 cannot hold the value."""
    return wanted_x(f) > IMM8_CEIL


# --------------------------------------------------------------------------
# THE REPLACEMENT ENCODING (hand-assembled, then DECODED back below).
#
# Both windows keep every stock effect:
#   * the frame spill `mov [esp+0x24], <parent>` is PRESERVED (the variant
#     that dropped it took an unproven semantic delta for no gain)
#   * `mov ecx, eax` becomes `xchg eax, ecx` (91) - one byte instead of two,
#     no flag effects, and eax is dead until the call returns
#   * the reload+push pair `mov ecx,[esp+0x28]; push ecx` becomes
#     `push dword [esp+0x38]` - PUSH r/m32 computes its address from the
#     PRE-decrement ESP, which is what makes the displacement 0x38 land on
#     the same frame slot
#   * `mov eax,[esi+disp]; push eax` becomes `push dword [esi+disp]`
# The 3 bytes those savings buy are exactly what `push imm32` costs over
# `push imm8`.
# --------------------------------------------------------------------------
def build_replacement(w, x):
    b = bytearray()
    if w["y_disp"] == 0x98:                      # income
        b += bytes.fromhex("8b5610")             # mov edx,[esi+0x10]   parent
        pre_vt = False
    else:                                        # expense
        b += bytes.fromhex("8b4e10")             # mov ecx,[esi+0x10]   parent
        b += bytes.fromhex("8b10")               # mov edx,[eax]        vtable
        pre_vt = True
    b += bytes.fromhex("6a66")                   # push 0x66   arg10 c3
    b += bytes.fromhex("6a55")                   # push 0x55   arg9  c2
    b += bytes.fromhex("6a44")                   # push 0x44   arg8  c1
    b += bytes.fromhex("6805d385ea")             # push 0xEA85D305  arg7 style
    b += bytes.fromhex("89542424" if not pre_vt else "894c2424")   # spill
    if not pre_vt:
        b += bytes.fromhex("8b10")               # mov edx,[eax]        vtable
    b += bytes.fromhex("6a00")                   # push 0      arg6 align
    b += bytes.fromhex("91")                     # xchg eax,ecx        this
    b += bytes.fromhex("ff521c")                 # call [edx+0x1C]     name str
    b += bytes.fromhex("50")                     # push eax    arg5 string
    b += bytes.fromhex("ffb6") + bytes([w["y_disp"], 0, 0, 0])     # arg4 y
    b += bytes.fromhex("68") + int(x).to_bytes(4, "little")        # arg3 x
    b += bytes.fromhex("55")                     # push ebp    arg2 id
    b += bytes.fromhex("ff742438")               # push [esp+0x38]  arg1 parent
    return bytes(b)


# --------------------------------------------------------------------------
# A tiny ESP tracker.  It models only what this window does: pushes, the one
# virtual call, and ESP-relative stores/loads.  Its job is to prove the
# replacement's frame aliasing matches stock's - and its POSITIVE CONTROL is
# that it reproduces stock's own aliasing, which only holds if the callee at
# [edx+0x1C] pops nothing (a thiscall getter with no stack args).  If that
# assumption were wrong, stock's reload would NOT resolve to stock's store and
# this gate would go red on the stock decode itself.
# --------------------------------------------------------------------------
def trace(code, va):
    """-> (args pushed in push order, esp delta, store slot, load slot)."""
    md = common.md()
    esp = 0
    args, store, load = [], None, None
    for ins in md.disasm(code, va):
        m = ins.mnemonic
        op = ins.op_str
        if m == "push":
            if op.startswith("dword ptr [esp"):
                # address computed from PRE-decrement esp
                disp = int(op.split("+")[1].rstrip("]"), 0)
                load = esp + disp
                args.append(("slot", load))
            elif op.startswith("dword ptr [esi"):
                disp = int(op.split("+")[1].rstrip("]"), 0)
                args.append(("esi", disp))
            elif op.startswith("0x") or op.lstrip("-").isdigit():
                args.append(("imm", int(op, 0)))
            else:
                args.append(("reg", op))
            esp -= 4
        elif m == "mov" and op.startswith("dword ptr [esp"):
            disp = int(op.split("+")[1].split("]")[0], 0)
            store = esp + disp
        elif m == "mov" and ", dword ptr [esp" in op:
            disp = int(op.split("+")[-1].rstrip("]"), 0)
            load = esp + disp
            args.append(("pending-slot", load))     # stock: reloaded, then pushed
        elif m == "call":
            pass                                     # callee pops nothing
    return args, esp, store, load


def normalize(args):
    """Collapse stock's reload-then-push-reg into the same shape as the
    replacement's direct push, so the two argument lists are comparable."""
    out = []
    pending = None
    for kind, val in args:
        if kind == "pending-slot":
            pending = val
            continue
        if kind == "reg" and val == "ecx" and pending is not None:
            out.append(("slot", pending))
            pending = None
            continue
        if kind == "reg" and val == "eax":
            out.append(("eax-or-esi", None))         # string OR the y fetch
            continue
        out.append((kind, val))
    return out


def stock_args_normalized(args):
    """Stock pushes `mov eax,[esi+d]; push eax` for y and `push eax` for the
    string; both surface as ('eax-or-esi', None) after normalize(), which is
    exactly how the replacement's `push [esi+d]` must be normalized too."""
    return args


def branch_targets_in(lo, hi):
    md = common.md()
    blob = common.rd(FUNC_LO, FUNC_HI - FUNC_LO)
    hits, seen = [], 0
    for ins in md.disasm(blob, FUNC_LO):
        if ins.mnemonic[0] == "j" or ins.mnemonic in ("loop", "loope", "loopne"):
            op = ins.op_str
            if op.startswith("0x"):
                t = int(op, 16)
                seen += 1
                if lo < t < hi:
                    hits.append((ins.address, t))
    return hits, seen


def main():
    verbose = "--verbose" in sys.argv
    fails = []
    notes = []

    fp = common.exe_fingerprint()
    fp_s = fp[0] if isinstance(fp, (tuple, list)) else str(fp)
    if EXPECT_FP not in str(fp_s):
        fails.append("EXE FINGERPRINT %s != expected %s - every address here "
                     "describes bytes in ONE build." % (fp_s, EXPECT_FP))
        print("FAIL: " + fails[-1])
        return 1
    print("exe fingerprint %s OK" % EXPECT_FP)

    # positive control for the branch scanner: it must see plenty of targets.
    _, seen_all = branch_targets_in(0, 0)
    print("branch scanner: %d intra-function branch targets resolved in "
          "sub_77C660 (positive control)" % seen_all)
    if seen_all < 20:
        fails.append("branch scanner resolved only %d targets - it is blind, "
                     "so its null below is worthless" % seen_all)

    for w in WINDOWS:
        print("\n=== %s ===" % w["name"])
        live = common.rd(w["va"], w["length"])
        want = bytes.fromhex(w["stock"])
        if live != want:
            fails.append("%s: STOCK BYTES MOVED at 0x%08X" % (w["name"], w["va"]))
            print("  FAIL stock bytes: %s" % live.hex())
            continue
        print("  stock %d bytes at 0x%08X verified" % (w["length"], w["va"]))

        # the site the per-site applier currently writes must be inside the
        # window - if the block ships, that entry MUST leave kOrdinanceInsetSites
        if not (w["va"] <= w["site"] < w["va"] + w["length"]):
            fails.append("%s: site 0x%08X outside its own window" %
                         (w["name"], w["site"]))
        else:
            print("  NOTE  per-site 0x%08X lies INSIDE this block - shipping the "
                  "block REQUIRES removing that kOrdinanceInsetSites entry, or "
                  "the '(n of 8)' health line goes to 6 of 8." % w["site"])

        s_args, s_esp, s_store, s_load = trace(want, w["va"])
        s_norm = normalize(s_args)
        if s_store is None or s_load is None or s_store != s_load:
            fails.append("%s: TRACKER POSITIVE CONTROL FAILED - stock store %s "
                         "!= stock reload %s" % (w["name"], s_store, s_load))
            print("  FAIL tracker control: store=%s load=%s" % (s_store, s_load))
        else:
            print("  tracker control OK: stock spills and reloads frame slot "
                  "%+d (proves the [edx+0x1C] callee pops nothing)" % s_store)
        if len(s_norm) != 10:
            fails.append("%s: stock decodes to %d args, expected 10 "
                         "(sub_779660 is ret 0x28)" % (w["name"], len(s_norm)))
        print("  stock: %d args, net esp %+d" % (len(s_norm), s_esp))

        b_hits, _ = branch_targets_in(w["va"], w["va"] + w["length"])
        if b_hits:
            fails.append("%s: %d branches land INSIDE the window: %s" %
                         (w["name"], len(b_hits),
                          ", ".join("0x%08X->0x%08X" % h for h in b_hits)))
            print("  FAIL branch targets inside: %s" % b_hits)
        else:
            print("  no branch in sub_77C660 targets 0x%08X..0x%08X"
                  % (w["va"], w["va"] + w["length"] - 1))

        for f in TIERS:
            x = wanted_x(f)
            if not should_reencode(f):
                clamp = "" if x <= IMM8_CEIL else " (WOULD CLAMP)"
                print("  f=%.2f  x=%-4d  NO WRITE (imm8 holds it)%s" % (f, x, clamp))
                if x > IMM8_CEIL:
                    fails.append("%s: f=%.2f wants %d but the gate declines to "
                                 "re-encode - that is the clamp, unfixed"
                                 % (w["name"], f, x))
                continue
            rep = build_replacement(w, x)
            if len(rep) != w["length"]:
                fails.append("%s f=%.2f: replacement is %d bytes, need %d"
                             % (w["name"], f, len(rep), w["length"]))
                continue
            r_args, r_esp, r_store, r_load = trace(rep, w["va"])
            r_norm = normalize(r_args)
            problems = []
            if len(r_norm) != len(s_norm):
                problems.append("arg count %d != %d" % (len(r_norm), len(s_norm)))
            if r_esp != s_esp:
                problems.append("net esp %+d != %+d" % (r_esp, s_esp))
            if r_store != s_store:
                problems.append("spill slot %s != %s" % (r_store, s_store))
            if r_load != s_load:
                problems.append("parent slot %s != %s" % (r_load, s_load))
            # arg-by-arg, allowing arg3 (x) to differ and allowing the
            # eax/[esi+d] normalization on the string and y arguments.
            if len(r_norm) == len(s_norm):
                for i, (sa, ra) in enumerate(zip(s_norm, r_norm)):
                    argno = len(s_norm) - i          # pushed right-to-left
                    if argno == 3:
                        if ra != ("imm", x):
                            problems.append("arg3 is %s, expected imm %d"
                                            % (ra, x))
                        continue
                    if argno == 4:
                        if not (sa[0] == "eax-or-esi" and ra[0] == "esi"
                                and ra[1] == w["y_disp"]):
                            problems.append("arg4 (y) %s vs %s" % (sa, ra))
                        continue
                    if sa != ra:
                        problems.append("arg%d %s vs %s" % (argno, sa, ra))
            if problems:
                fails.append("%s f=%.2f: %s" % (w["name"], f, "; ".join(problems)))
                print("  f=%.2f  x=%-4d  FAIL: %s" % (f, x, "; ".join(problems)))
            else:
                print("  f=%.2f  x=%-4d  43/43 bytes, 10 args, esp %+d, slot %+d"
                      "  OK" % (f, x, r_esp, r_store))
                if verbose:
                    print("        %s" % rep.hex())

    print("\n" + "=" * 70)
    if fails:
        print("RED - %d failure(s):" % len(fails))
        for m in fails:
            print("  * " + m)
        return 1
    print("GREEN - encoding + stack shape adjudicated for both windows at "
          "f in %s." % (TIERS,))
    print("SCOPE: this proves the re-encode is SAFE TO WRITE. It does NOT "
          "prove the 3x name column clears the eye, and it says nothing about "
          "#104's shutdown spin - the clamped bytes are byte-identical in a "
          "CLEAN run (run8) and a SPINNING run (run13).")
    for n in notes:
        print("NOTE " + n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
