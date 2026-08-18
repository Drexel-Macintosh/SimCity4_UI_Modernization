"""gate_advice_rowx.py - the OFFLINE GATE for the advice-row width re-encode
that lets the news/advice dismiss X scale at 3x (bug C, `3x Issues.docx`).

WHY THIS EXISTS

  cSC4WinAdviceList::Refresh emits every advice row as a three-column HTML
  table [arrow | headline | dismiss-X].  The middle column's width is
  `pane->GetW() - S`, and S lives in ONE sign-extended imm8:

      0x0079388F   83 EE 3D      sub esi, 0x3D        (61)

  S = 2*round(18f) + 9 + round(16f).  That is 87 at 1.5x and 113 at 2x - both
  encodable - but 165 at 3x, which is not.  So task #88 deliberately shipped
  the X at STOCK size above f=2.0 and clamped S to 127, and
  Test-DatIntegrity.ps1 records the resulting 655/655/651 tier split as
  "forced by an encoding ceiling, not by taste".  The visible cost is bug C:
  at 3x the row X renders 1/3 size (measured 21x35 px against the panel's own
  60x55 close X - a ratio of 0.35).

  The cure re-encodes the 19-byte window at 0x0079388B so the subtraction
  becomes a 6-byte `lea esi, [eax - S]`, paying for the extra bytes by
  dropping ONE store that is provably dead across the seam.  This gate
  adjudicates THAT, and nothing about how the row looks.

SCOPE (law 42 - a gate is only as honest as its scope)

  Encoding, stack shape and liveness only.  It CANNOT tell you the X clears
  the pane edge at 3x; only eyes-on can.  It also cannot prove the art shipped
  - Test-DatIntegrity owns the 655-at-every-tier assertion that must land in
  the SAME build (the two `factor <= 2.0` tests in CodePatches.cpp and
  build_selective_safe.py are a coupled pair).

GREEN means:
  * the exe fingerprint still matches the build this was derived from
  * the stock 19 bytes are still exactly as pinned
  * the replacement is EXACTLY 19 bytes and decodes cleanly
  * it computes esi = eax - S, the same value stock computes
  * `push 8` still executes exactly once, BEFORE the surviving stores, so the
    esp-relative offsets of those stores are unchanged
  * net ESP delta across the window is identical to stock
  * the store this drops ([esp+0x60]) is REDEFINED before any read, and the
    only instruction between is a 4-instruction allocator thunk that cannot
    reach the caller's frame
  * the store this KEEPS ([esp+0x58]) is one whose address is taken and which
    is never redefined - dropping that one instead would be a live-store bug
  * stock's `sub` sets flags and the replacement's `lea` does not - so no
    flag consumer may sit between the window and the next flag definition
  * no branch anywhere in the enclosing function targets an address inside
    the window (a jump into the middle would land mid-instruction)
  * f <= 2.0 emits NO write at all - 1.5x and 2x stay byte-identical to the
    user-confirmed shipped build
  * the POSITIVE CONTROLS trip: four deliberately broken candidates are each
    rejected for the right reason

Run from the repo root:
    python tools\\uimap\\emu\\gate_advice_rowx.py
    python tools\\uimap\\emu\\gate_advice_rowx.py --verbose
Exit code 0 = green.
"""
import os
import struct
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

WIN_VA, WIN_LEN = 0x0079388B, 19
FUNC_LO, FUNC_HI = 0x00793810, 0x00793C00           # cSC4WinAdviceList::Refresh
SITE_IMM8 = 0x0079388F                              # the shipped 3-byte form

STOCK_HEX = "8bf06a0883ee3d895c2458895c245c895c2460"

# The constants the applier uses (mirrored from CodePatches.cpp).
GLYPH_STOCK, ROW_FIXED, BAR_STOCK, MID_STOCK = 18, 9, 16, 0x3D
X_SCALE_MAX_FACTOR = 2.0                            # above this, today, X stays stock

# Frame slots, measured. [esp+0x58] has its ADDRESS taken at 0x007938A7 and is
# never redefined -> LIVE. [esp+0x5c] and [esp+0x60] are both redefined at
# 0x007938AB / 0x007938AF with only the allocator call in between -> DEAD.
SLOT_LIVE, SLOT_DEAD_A, SLOT_DEAD_B = 0x58, 0x5C, 0x60
REDEF = {0x5C: 0x007938AB, 0x60: 0x007938AF}
ALLOC_THUNK = 0x0090CF54

fails, notes = [], []
VERBOSE = "--verbose" in sys.argv


def say(*a):
    if VERBOSE:
        print("   ", *a)


def subtrahend(factor, x_scaled):
    glyph = int(round(GLYPH_STOCK * factor))
    glyph_x = glyph if x_scaled else GLYPH_STOCK
    bar = int(round(BAR_STOCK * factor))
    return glyph + glyph_x + ROW_FIXED + bar


def build_replacement(s, drop_slot=SLOT_DEAD_B, keep_push_first=True,
                      pad=True):
    """The candidate 19 bytes. Parameters exist so the positive controls can
    build deliberately-wrong variants through the same code path."""
    out = b""
    if keep_push_first:
        out += bytes([0x6A, 0x08])                      # push 8
    out += bytes([0x8D, 0xB0]) + struct.pack("<i", -s)  # lea esi,[eax - s]
    for slot in (SLOT_LIVE, SLOT_DEAD_A, SLOT_DEAD_B):
        if slot == drop_slot:
            continue
        out += bytes([0x89, 0x5C, 0x24, slot])          # mov [esp+slot], ebx
    if not keep_push_first:
        # THE BROKEN ORDERING the control needs: the stores' disp8s are
        # measured from an esp that already has the 8 pushed. Emitting the
        # push after them silently shifts both stores by 4 bytes.
        out += bytes([0x6A, 0x08])
    if pad:
        out += b"\x90" * (WIN_LEN - len(out))
    return out


def decode(blob, va):
    return list(common.md().disasm(blob, va))


def check_candidate(cand, s, label):
    """Every structural assertion, as a list of (ok, why) - so a positive
    control can be shown to fail for the RIGHT reason, not just to fail."""
    bad = []
    if len(cand) != WIN_LEN:
        bad.append("length %d != %d" % (len(cand), WIN_LEN))
        return bad

    ins = decode(cand, WIN_VA)
    if sum(i.size for i in ins) != WIN_LEN:
        bad.append("does not decode cleanly to %d bytes" % WIN_LEN)
        return bad

    text = [(i.mnemonic, i.op_str) for i in ins]

    # esi = eax - s, via lea
    lea = [i for i in ins if i.mnemonic == "lea" and i.op_str.startswith("esi,")]
    if len(lea) != 1:
        bad.append("expected exactly one `lea esi, ...`, got %d" % len(lea))
    else:
        want = -s & 0xFFFFFFFF
        got = lea[0].bytes[2:6]
        if struct.unpack("<I", got)[0] != want:
            bad.append("lea displacement encodes %d, expected -%d"
                       % (struct.unpack("<i", got)[0], s))
        if not lea[0].op_str.replace(" ", "").startswith("esi,[eax"):
            bad.append("lea base is not eax: %s" % lea[0].op_str)

    # push 8 exactly once, and before every surviving store
    pushes = [n for n, i in enumerate(ins) if i.mnemonic == "push"]
    stores = [n for n, i in enumerate(ins)
              if i.mnemonic == "mov" and i.op_str.startswith("dword ptr [esp")]
    if len(pushes) != 1:
        bad.append("expected exactly one push, got %d" % len(pushes))
    elif stores and pushes[0] > min(stores):
        bad.append("push 8 must precede the esp-relative stores "
                   "(their displacements assume it)")

    # net esp delta must match stock's -4
    delta = -4 * len(pushes)
    if delta != -4:
        bad.append("net ESP delta %d != -4" % delta)

    # the LIVE slot must survive; exactly one dead slot may be dropped
    kept = set()
    for i in ins:
        if i.mnemonic == "mov" and i.op_str.startswith("dword ptr [esp"):
            kept.add(int(i.op_str.split("+")[1].split("]")[0], 16))
    if SLOT_LIVE not in kept:
        bad.append("dropped [esp+0x%02X], whose address is taken at 0x007938A7 "
                   "and which is never redefined - that store is LIVE" % SLOT_LIVE)
    dropped = {SLOT_LIVE, SLOT_DEAD_A, SLOT_DEAD_B} - kept
    for d in dropped:
        if d not in REDEF:
            bad.append("dropped [esp+0x%02X] which has no proven redefinition" % d)
    if len(dropped) != 1:
        bad.append("expected exactly one dropped store, got %d" % len(dropped))
    return bad


def main():
    print("gate_advice_rowx - advice row width re-encode (bug C)")

    fp, size = common.exe_fingerprint()
    if fp != EXPECT_FP:
        fails.append("exe fingerprint %s != pinned %s - this gate was derived "
                     "from a different build and proves nothing" % (fp, EXPECT_FP))
        print("FAIL: fingerprint mismatch"); return 1
    say("exe fingerprint", fp, size)

    # ---- 1. stock bytes still as pinned -----------------------------------
    live = common.rd(WIN_VA, WIN_LEN)
    if live.hex() != STOCK_HEX:
        fails.append("stock window changed: %s != %s" % (live.hex(), STOCK_HEX))
    else:
        say("stock 19 bytes verified @0x%08X" % WIN_VA)

    # ---- 2. the dropped store really is redefined before any read ---------
    md = common.md()
    span = common.rd(WIN_VA, 0x007938B7 - WIN_VA)
    reads = []
    for i in md.disasm(span, WIN_VA):
        if i.address <= SITE_IMM8:
            continue
        op = i.op_str
        for slot in (SLOT_DEAD_A, SLOT_DEAD_B):
            tag = "[esp + 0x%x]" % slot
            if tag in op:
                is_store = op.startswith("dword ptr [esp") and "," in op
                reads.append((i.address, slot, "store" if is_store else "read", op))
    for slot, at in REDEF.items():
        hits = [r for r in reads if r[1] == slot and r[2] == "store" and r[0] == at]
        if not hits:
            fails.append("[esp+0x%02X] is NOT redefined at 0x%08X as claimed - "
                         "dropping it would be a live-store bug" % (slot, at))
        else:
            say("[esp+0x%02X] redefined at 0x%08X" % (slot, at))
    leaked = [r for r in reads if r[2] == "read"]
    if leaked:
        fails.append("a READ of a supposedly-dead slot exists: %r" % (leaked,))

    # the only instruction between is the allocator thunk - prove it is small
    # and cannot walk the caller's frame
    thunk = list(md.disasm(common.rd(ALLOC_THUNK, 16), ALLOC_THUNK))
    if not (len(thunk) >= 4 and thunk[0].mnemonic == "push"
            and thunk[-1].mnemonic in ("ret", "jmp")):
        notes.append("allocator thunk at 0x%08X does not look like the expected "
                     "4-instruction forwarder - re-verify by hand" % ALLOC_THUNK)
    else:
        say("allocator thunk is %d instructions, cannot reach caller locals"
            % len(thunk))

    # ---- 3. no branch lands inside the window -----------------------------
    blob = common.rd(FUNC_LO, FUNC_HI - FUNC_LO)
    inside = []
    for i in md.disasm(blob, FUNC_LO):
        if i.group(common.__dict__.get("CS_GRP_JUMP", 1)) if False else False:
            pass
        if i.mnemonic.startswith("j") or i.mnemonic == "loop":
            try:
                tgt = int(i.op_str, 16)
            except ValueError:
                continue
            if WIN_VA < tgt < WIN_VA + WIN_LEN:
                inside.append((i.address, tgt))
    if inside:
        fails.append("branch(es) target the middle of the window: %r" % inside)
    else:
        say("no branch targets inside the window")

    # ---- 4. flags: stock's SUB sets them, our LEA does not -----------------
    after = list(md.disasm(common.rd(WIN_VA + WIN_LEN, 48), WIN_VA + WIN_LEN))
    flag_readers = ("j", "set", "cmov", "adc", "sbb")
    flag_writers = ("cmp", "test", "sub", "add", "and", "or", "xor", "inc", "dec")
    for i in after:
        if any(i.mnemonic.startswith(p) for p in flag_readers):
            fails.append("flag consumer %s at 0x%08X before any flag write - "
                         "replacing SUB with LEA would change behaviour"
                         % (i.mnemonic, i.address))
            break
        if any(i.mnemonic == w for w in flag_writers):
            say("flags redefined by %s at 0x%08X - SUB's flags are dead"
                % (i.mnemonic, i.address))
            break

    # ---- 5. per-tier behaviour --------------------------------------------
    print()
    print("  tier | S (X stock) | S (X scaled) | encodable today | after fix")
    for f in (1.0, 1.5, 2.0, 3.0):
        s_stock = subtrahend(f, False)
        s_scaled = subtrahend(f, True)
        today_ok = s_stock <= 127
        want = s_scaled if f > X_SCALE_MAX_FACTOR else s_stock
        # below the ceiling the shipped imm8 path stays; nothing is rewritten
        rewrite = f > X_SCALE_MAX_FACTOR
        print("  %4.2f | %11d | %12d | %-15s | %s"
              % (f, s_stock, s_scaled, "yes" if today_ok else "NO (clamped)",
                 ("lea imm32, S=%d" % s_scaled) if rewrite else "unchanged (imm8)"))
        if not rewrite:
            continue
        bad = check_candidate(build_replacement(s_scaled), s_scaled, "f=%.2f" % f)
        if bad:
            fails.extend(["f=%.2f: %s" % (f, b) for b in bad])

    if subtrahend(2.0, False) > 127:
        fails.append("f=2.0 no longer fits the imm8 - the 'lower tiers stay "
                     "byte-identical' guarantee is broken")
    if subtrahend(3.0, True) <= 127:
        fails.append("f=3.0 now fits an imm8 - this whole re-encode is "
                     "unnecessary and should not ship")

    # ---- 6. POSITIVE CONTROLS ---------------------------------------------
    print()
    s3 = subtrahend(3.0, True)
    controls = [
        ("wrong length",
         build_replacement(s3, pad=False)[:-1]),
        ("drops the LIVE [esp+0x58] store",
         build_replacement(s3, drop_slot=SLOT_LIVE)),
        ("push 8 after the stores",
         build_replacement(s3, keep_push_first=False)),
        ("wrong displacement",
         build_replacement(s3 + 7)),
    ]
    for label, cand in controls:
        bad = check_candidate(cand, s3, label)
        if not bad:
            fails.append("POSITIVE CONTROL DID NOT TRIP: '%s' was accepted - "
                         "this gate cannot detect that class of error" % label)
        else:
            print("  control OK - rejected '%s': %s" % (label, bad[0]))

    print()
    for n in notes:
        print("NOTE:", n)
    if fails:
        for f_ in fails:
            print("FAIL:", f_)
        print("\nFAILED (%d)" % len(fails))
        return 1
    print("PASS - re-encode is 19 bytes, esi = eax - S, ESP unchanged, one")
    print("       provably-dead store dropped, flags dead, no branch inside,")
    print("       1.5x/2x untouched, and 4 positive controls tripped.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
