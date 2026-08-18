"""gate_graphlegend_leftanchor.py - the OFFLINE GATE for #57's LEFT-ANCHOR fix.

WHAT THIS ADJUDICATES (law 44 - a probe must adjudicate the FIX, not sight it):

  The candidate is "BUDGET-AT-BIRTH, LEFT-ANCHOR ONLY": patch the 1x legend
  ORIGIN constants inside sub_76D3D0 (the Graphs panel's own builder, the #78
  cure) so the legend column is BORN at f, while DELIBERATELY leaving the
  checkbox window 16 wide / 16 tall in the game's own SetArea call.

  Leaving the checkbox at 16 is the whole point.  Nobody has identified what
  turns the game's 16x16 checkbox into the measured 32x32 (see the brief -
  every named hypothesis is refuted by disassembly).  So the fix is required to
  be CORRECT UNDER EVERY SURVIVING HYPOTHESIS for that writer:

     H_NONE   nothing resizes it     -> checkbox stays round-trip 16 wide
     H_SCALE  something writes W = round(16*f) (or the art cell,
              which is strip_w/8 = 32 / 24 / 48 at 2x / 1.5x / 3x -
              numerically identical at every tier we ship)

  If BOTH hypotheses come back CLEAN at every tier and both legend kinds, the
  unknown writer stops being a blocker for THIS build.  That is the only claim
  this file makes.

GREEN means: every stock byte string still matches the shipped exe, the three
re-encoded regions are byte-exact in length, no branch lands inside them, the
constants reduce EXACTLY to stock at f=1, and verdict() is clean for both
kinds x both hypotheses x f in {1.0, 1.5, 2.0, 3.0}.

SCOPE (law 42): layout + encoding only.  Nothing here proves a rect reaches the
screen, and nothing here identifies the 32x32 writer - it proves the fix does
not DEPEND on identifying it.

Run from the repo root:
    python tools\\uimap\\emu\\gate_graphlegend_leftanchor.py
    python tools\\uimap\\emu\\gate_graphlegend_leftanchor.py --verbose
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.dirname(_HERE))          # tools\uimap (common.py)

import emu_chart_legend as E                        # noqa: E402


# ===========================================================================
# SECTION 1 - THE PATCH SET, as bytes.  Stock strings are VERIFIED, not quoted.
# ===========================================================================

# In-place immediates: (va, stock_bytes, imm_offset, imm_len, stock_value,
#                       lambda f -> new value, name)
IMM_SITES = [
    (0x0076E233, "8d4803",   2, 1, 3,
     lambda f: r(3 * f),                      "SWATCH_DY   lea ecx,[eax+3]"),
    (0x0076E239, "83c009",   2, 1, 9,
     lambda f: r(3 * f) + r(6 * f),           "SWATCH_B    add eax,9"),
    (0x0076E23C, "83c30a",   2, 1, 10,
     lambda f: r(10 * f),                     "SWATCH_W    add ebx,0xa"),
    (0x0076E2AF, "83c104",   2, 1, 4,
     lambda f: r(4 * f),                      "TEXT_GAP    add ecx,4"),
    (0x0076E2C8, "83ea04",   2, 1, 4,
     lambda f: r(4 * f),                      "TEXT_R_MARG sub edx,4"),
]

# Block re-encodings: (va, end_va, stock_bytes, name).  end_va is exclusive and
# must be an instruction boundary the stock code already branches to or falls
# through to.
BLOCKS = [
    (0x0076E0E8, 0x0076E101,
     "8b5c24508b5424488b41442bda83eb6a83f8020f86ff000000",
     "B1 plain swatch anchor  winW-106 -> winW-round(106*f)"),
    (0x0076E145, 0x0076E16E,
     "8b5c24488b5424508b4c241883c110512bd38b188d4aa451"
     "8b4c2420518_3c294528bc8ff93dc000000".replace("_", ""),
     "B2 checkbox rect        L=winW-round(108*f), R=L+16, H=16 (UNSCALED)"),
    (0x0076E1D6, 0x0076E200,
     "8b1e8b178b2b8bcfff520c508bcbff5538"
     "8b4c24488b5c24502bd98d8c24f800000083eb5ae8e049e9ff",
     "B3 AddChildWindow + cbox swatch anchor  winW-90 -> winW-round(90*f)"),
]

# Sites we DELIBERATELY do not touch, and why.  Printed so the exclusion is a
# documented decision rather than an omission (law 22).
NOT_PATCHED = [
    (0x0076DD4E, "sub edx,0x6e", "PLOT_R_MARGIN 110 - owned by EARLYCHART's "
     "ChartStoreThunk (src\\UiSpike.cpp:421). Patching it too DOUBLE-scales "
     "(976-220*2=536)."),
    (0x0076E34B, "lea edx,[ecx+eax+4]", "ROW_PAD 4 - this is the PITCH's "
     "additive term and the pitch is font-derived (#78 rule 1). It is also "
     "the vertical budget that is currently overflowing."),
    (0x0076DE79, "mov [esp+0x18],0x14", "ROW0_TOP 20 - the only patched-class "
     "constant that SPENDS the resource that is overflowing. Held back until "
     "CHARTLEG reports the real bottom."),
    (0x0076E151, "add ecx,0x10", "CBOX_H 16 - see B2: the checkbox size is "
     "left to whatever already doubles it."),
    (0x0076E159, "lea ecx,[edx-0x5c]", "CBOX_R_MARGIN 92 - folded into B2 as "
     "R = L+16 so the checkbox WIDTH never appears twice (law 15/43)."),
]


def r(x):
    """RoundHalfUp, matching src\\UiSpike.cpp's RoundHalfUp."""
    return int(x + 0.5) if x >= 0 else -int(-x + 0.5)


# ===========================================================================
# SECTION 2 - byte verification against the SHIPPED exe
# ===========================================================================

def check_bytes(S, verbose):
    try:
        import common as C
    except Exception as exc:                       # pragma: no cover
        S.skip("exe byte verification (tools\\uimap\\common.py: %s)" % exc)
        return

    for va, stock, off, ln, val, _fn, name in IMM_SITES:
        got = C.rd(va, len(stock) // 2).hex()
        S.eq(got, stock, "IMM  %08X stock bytes  %s" % (va, name))
        enc = int(stock[off * 2:(off + ln) * 2], 16)
        if enc > 127:
            enc -= 256
        S.eq(abs(enc), val, "IMM  %08X immediate == %d" % (va, val))

    for va, end, stock, name in BLOCKS:
        n = end - va
        S.eq(len(stock) // 2, n, "BLK  %08X stock length == %d  %s"
             % (va, n, name))
        got = C.rd(va, n).hex()
        S.eq(got, stock, "BLK  %08X stock bytes" % va)

    # No branch inside a re-encoded region.  Scan every jcc/jmp/call immediate
    # in the whole builder.
    m = C.md()
    lo, hi = 0x0076D3D0, 0x0076E420
    blob = C.rd(lo, hi - lo)
    holes = [(va + 1, end) for va, end, _s, _n in BLOCKS]   # entry is legal
    inside = []
    for i in m.disasm(blob, lo):
        if not (i.mnemonic.startswith("j") or i.mnemonic == "call"):
            continue
        try:
            t = int(i.op_str, 16)
        except ValueError:
            continue
        for a, b in holes:
            if a <= t < b:
                inside.append((i.address, t))
    S.eq(inside, [], "BLK  no branch target lands inside a re-encoded region")

    # The immediates must be patchable in place at every tier we ship.
    for f in (1.0, 1.5, 2.0, 3.0):
        for va, _s, _o, ln, _v, fn, name in IMM_SITES:
            nv = fn(f)
            S.ok(0 <= nv <= 127 if ln == 1 else True,
                 "IMM  %08X f=%.2f -> %d fits imm8  (%s)" % (va, f, nv, name))
        for lbl, v in (("B1 sub ebx", r(106 * f)),
                       ("B2 sub edx", r(108 * f)),
                       ("B3 sub ebx", r(90 * f))):
            S.ok(0 <= v <= 0x7FFFFFFF,
                 "BLK  %s f=%.2f -> %d (imm32 form, no ceiling)"
                 % (lbl, f, v))

    if verbose:
        print("\n  DELIBERATELY NOT PATCHED:")
        for va, asm, why in NOT_PATCHED:
            print("    %08X  %-24s %s" % (va, asm, why))


# ===========================================================================
# SECTION 3 - the constants this patch set produces
# ===========================================================================

# ---------------------------------------------------------------------------
# RECONCILED 2026-08-03 against tools\uimap\emu\prove_chart_legend.py.
#
# This gate originally used STRIP = r(108*f) throughout. That is the candidate
# the acceptance oracle calls E-STRIPxf, and the oracle REJECTS it: at every
# tier above 1x it fails I3 under the RAW font hypothesis, because a box of
# r(72*f) is narrower than the widest label stock keeps on one line. Since U4
# is now RESOLVED to RAW (the legend renders in ChartLabel 0xE9C86B5E at
# 0x0076DD91, NOT in Legend 0xE9C86B5F - so the SIZE_SQUEEZE on "Legend" never
# applied to this chart at all), the RAW column is the shipping one and
# r(108*f) would wrap MORE than stock.
#
# Two gates certifying different targets is worse than one gate: whichever got
# run last would decide what shipped. So this gate now drives off the ORACLE's
# certified strip. The byte-encoding checks in section 2 are unaffected - they
# test instruction LENGTH and imm32 encodability, which do not depend on the
# value - but the layout checks now assert the certified geometry.
#
# STRIP is tabled, not computed, and any factor outside the table DECLINES.
# The oracle derives it as
#     strip(f) = sc(16,f)+sc(2,f)+sc(10,f)+sc(4,f)+box(f)+sc(4,f)
# with box(f) sized from a provable glyph bound (NMAX=33); reproducing that
# derivation here by hand is exactly the "re-derive the number" habit that
# produced four failed patches, so the table below is COPIED from the oracle's
# ACCEPTANCE TARGETS block and must be regenerated from it, never edited by
# hand. Only 1.5 / 2 / 3 ship as packages.
CERTIFIED_STRIP = {1.0: 108, 1.5: 178, 2.0: 240, 3.0: 371}


def strip_for(f):
    key = round(f, 2)
    if key not in CERTIFIED_STRIP:
        raise KeyError(
            "no certified strip for f=%s - the oracle only certifies %s. "
            "A factor with no certified strip must DECLINE, not guess."
            % (f, sorted(CERTIFIED_STRIP)))
    return CERTIFIED_STRIP[key]


def consts_for(f):
    """The Consts the PATCHED sub_76D3D0 writes at scale f."""
    C = E.STOCK.copy()
    strip = strip_for(f)
    # B1 / B3 / B2 - the winW-relative anchors, all derived from ONE number so
    # they cannot drift apart (law 43: the column is a coupled set).
    C.SWATCH_MARGIN_PLAIN = strip - r(2 * f)
    C.SWATCH_MARGIN_CBOX = strip - r(16 * f) - r(2 * f)
    C.CBOX_L_MARGIN = strip
    C.CBOX_R_MARGIN = strip - 16           # B2: R = L + 16, ALWAYS
    C.CBOX_H = 16                          # unscaled, on purpose
    # in-place immediates
    C.SWATCH_DY = r(3 * f)
    C.SWATCH_H = r(6 * f)
    C.SWATCH_W = r(10 * f)
    C.TEXT_GAP = r(4 * f)
    C.TEXT_R_MARGIN = r(4 * f)
    # NOT patched
    C.ROW0_TOP = 20
    C.ROW_PAD = 4
    # EARLYCHART owns the plot rect, but it is now COUPLED to the strip: the
    # oracle's H-EARLYCHART candidate is exactly "adopt the strip, keep the old
    # r(110*f)" and it FAILS I4 - the plot border paints inside the checkbox
    # column. plot.R must clear the strip by the same sc(2,f) it does at stock.
    C.PLOT_L = r(45 * f)
    C.PLOT_T = r(20 * f)
    C.PLOT_R_MARGIN = strip + r(2 * f)
    C.PLOT_B_MARGIN = r(20 * f)
    return C


def apply_writer(lay, f, hypothesis):
    """The unidentified writer, as an OUTPUT edit on the checkbox rect only."""
    if hypothesis == "H_NONE" or lay["cbox_x"] is None:
        return lay
    w = r(16 * f)                       # == art cell strip_w/8 at every tier
    cl = lay["cbox_x"][0]
    lay["cbox_x"] = (cl, cl + w)
    for row in lay["rows"]:
        if row["cbox"]:
            l, t, _rr, _b = row["cbox"]
            row["cbox"] = (l, t, l + w, t + w)
    return lay


def predict(f, rows, hypothesis, win_w=None, win_h=None):
    win_w = win_w if win_w is not None else int(round(E.STOCK_WIN_W * f))
    win_h = win_h if win_h is not None else int(round(E.STOCK_WIN_H * f))
    lay = E.game_layout(win_w, win_h, rows, f, consts_for(f))
    return apply_writer(lay, f, hypothesis)


# ===========================================================================
# SECTION 4 - the checks
# ===========================================================================

def fmt(lay):
    cx = lay["cbox_x"]
    sx = lay["swatch_x"]
    tx = lay["text_x"]
    return ("cbox %s  swatch %d..%d (%dx%d)  text %d..%d (w=%d)  "
            "plotR %d  tops %s  bottom %d/%d"
            % ("%d..%d" % cx if cx else "-",
               sx[0], sx[1], sx[1] - sx[0],
               lay["rows"][0]["swatch"][3] - lay["rows"][0]["swatch"][1],
               tx[0], tx[1], lay["box_w"], lay["plot"][2],
               lay["tops"], lay["bottom"], lay["win_h"]))


def check_stock_reduction(S, verbose):
    """#88's free self-check: at f=1 every patched constant IS the stock one."""
    C = consts_for(1.0)
    for k, v in vars(E.STOCK).items():
        if k.startswith("PLOT_"):
            continue                       # EARLYCHART is a no-op at f=1 too
        S.eq(getattr(C, k), v, "f=1 reduces to stock: %s == %d" % (k, v))

    # And the model must then reproduce the MEASURED stock capture.
    lay = predict(1.0, E.GARBAGE_ROWS, "H_NONE", 488, 256)
    S.eq(lay["cbox_x"], (380, 396), "f=1 cbox columns == measured stock")
    S.eq(lay["swatch_x"], (398, 408), "f=1 swatch columns == measured stock")
    S.eq(lay["text_x"], (412, 484), "f=1 text columns == measured stock")
    S.eq(lay["tops"], [20, 39, 73, 92, 126, 145, 164, 183, 217],
         "f=1 row tops == measured stock")
    plain = predict(1.0, E.PLAIN_ROWS, "H_NONE", 488, 256)
    S.eq(plain["swatch_x"], (382, 392), "f=1 plain swatch == measured stock")
    S.eq(plain["text_x"], (396, 484), "f=1 plain text == measured stock")
    if verbose:
        print("\n  f=1.00 cbox : %s" % fmt(lay))
        print("  f=1.00 plain: %s" % fmt(plain))


def check_tiers(S, verbose):
    for f in (1.0, 1.5, 2.0, 3.0):
        for kind, rows in (("cbox", E.GARBAGE_ROWS), ("plain", E.PLAIN_ROWS)):
            for hyp in ("H_NONE", "H_SCALE"):
                lay = predict(f, rows, hyp)
                ok, bad = E.verdict(lay)
                S.ok(ok, "f=%.2f %-5s %-7s VERDICT CLEAN%s"
                     % (f, kind, hyp, "" if ok else "  -> " + "; ".join(bad)))
                if verbose:
                    print("    f=%.2f %-5s %-7s %s" % (f, kind, hyp, fmt(lay)))


def check_gaps(S, verbose):
    """The three gaps that ARE the bug, at the shipped tier, both hypotheses."""
    for hyp, cw in (("H_NONE", 16), ("H_SCALE", 32)):
        lay = predict(2.0, E.GARBAGE_ROWS, hyp, 976, 512)
        cl, cr = lay["cbox_x"]
        sl, sr = lay["swatch_x"]
        tl, _tr = lay["text_x"]
        S.eq(cr - cl, cw, "2x cbox width == %d under %s" % (cw, hyp))
        S.ok(sl - cr >= 4, "2x %s swatch clears the checkbox by %d px (>=4)"
             % (hyp, sl - cr))
        S.ok(tl - sr >= 8, "2x %s text clears the swatch by %d px (>=8)"
             % (hyp, tl - sr))
        S.ok(cl - lay["plot"][2] >= 4,
             "2x %s checkbox clears the plot edge by %d px (>=4)"
             % (hyp, cl - lay["plot"][2]))
        S.ok(lay["bottom"] <= lay["win_h"],
             "2x %s all %d rows inside the window (bottom %d/%d, %d spare)"
             % (hyp, len(lay["rows"]), lay["bottom"], lay["win_h"],
                lay["win_h"] - lay["bottom"]))


def check_headroom(S, verbose):
    """The vertical claim, stress-tested.  Our own text model is +-4 px, so ask
    how many EXTRA wrapped lines the column can absorb before a row is lost."""
    lay = predict(2.0, E.GARBAGE_ROWS, "H_SCALE", 976, 512)
    lh = lay["lh"]
    spare = lay["win_h"] - lay["bottom"]
    S.ok(spare >= lh,
         "2x vertical headroom %d px >= one extra wrapped line (%d px)"
         % (spare, lh))
    if verbose:
        print("\n  2x lines/row %s (stock pattern %s), spare %d px = %.1f "
              "extra lines" % ([x["lines"] for x in lay["rows"]],
                               [1, 2, 1, 2, 1, 1, 1, 2, 2], spare,
                               spare / float(lh)))


# ===========================================================================

class Suite(object):
    def __init__(self):
        self.n = 0
        self.fail = []

    def ok(self, cond, msg):
        self.n += 1
        if not cond:
            self.fail.append(msg)
        print("  %s %s" % ("PASS" if cond else "FAIL", msg))

    def eq(self, got, want, msg):
        self.ok(got == want, "%s  (got %r)" % (msg, got)
                if got != want else msg)

    def skip(self, msg):
        print("  SKIP %s" % msg)


# ===========================================================================
# SECTION 6 - THE REPLACEMENT BYTES (added 2026-08-03)
#
# The three block re-encodings were disassembled back with capstone when they
# were designed, but that check lived in a session and not in an artifact -
# so nothing durable proved the bytes the DLL is about to write. These blocks
# are the single riskiest edit in the change: they are 25/41/42 bytes of
# re-encoded instructions dropped into a live code path, and a wrong length or
# a wrong rel32 is a crash, not a layout bug.
#
# This section BUILDS the replacement for a given factor exactly as
# CodePatches::ApplyGraphLegendBudgetScale must, then proves it:
#   - length identical to stock (no trampoline, no cave, no shifted boundary)
#   - disassembles cleanly and the last instruction ENDS exactly on end_va
#   - the imm32 equals the intended certified constant
#   - every branch/call target is preserved verbatim
# The emitted hex is printed so the C++ table can be diffed against it.
# ===========================================================================

CALL_602BE0 = 0x00602BE0
JBE_TARGET = 0x0076E200


def _imm32(v):
    return bytes([v & 0xFF, (v >> 8) & 0xFF, (v >> 16) & 0xFF, (v >> 24) & 0xFF])


def _rel32(frm_next, to):
    d = (to - frm_next) & 0xFFFFFFFF
    return _imm32(d)


def build_replacements(f):
    """(va, stock_len, replacement_bytes, label) for B1/B2/B3 at factor f."""
    C = consts_for(f)
    out = []

    # B1 @ 0x0076E0E8..0x0076E101 - plain swatch anchor.
    # Drops the two dead loads (edx reloaded at 0x0076E149/0x0076E214, eax at
    # 0x0076E125/0x0076E200) to buy the 4 bytes imm32 needs, then re-derives
    # winW from the stack rather than carrying it in a register - which is why
    # no new register-liveness assumption is introduced anywhere.
    b1 = (bytes.fromhex("8b5c2450")            # mov ebx,[esp+0x50]
          + bytes.fromhex("2b5c2448")          # sub ebx,[esp+0x48]
          + bytes.fromhex("81eb") + _imm32(C.SWATCH_MARGIN_PLAIN)
          + bytes.fromhex("83794402")          # cmp dword [ecx+0x44],2
          + bytes.fromhex("0f86")
          + _rel32(0x0076E0E8 + 4 + 4 + 6 + 4 + 6, JBE_TARGET)
          + b"\x90")
    out.append((0x0076E0E8, 0x0076E101 - 0x0076E0E8, b1, "B1 plain swatch anchor"))

    # B2 @ 0x0076E145..0x0076E16E - checkbox rect.
    # Width appears ONCE, as L+16, so it can never split from the left edge
    # (law 15/43). H stays 16: the checkbox size is left to whatever already
    # doubles it, which is what makes the fix independent of that writer.
    b2 = (bytes.fromhex("8b542450")            # mov edx,[esp+0x50]
          + bytes.fromhex("2b542448")          # sub edx,[esp+0x48]
          + bytes.fromhex("81ea") + _imm32(C.CBOX_L_MARGIN)
          + bytes.fromhex("8b4c2418")          # mov ecx,[esp+0x18]
          + bytes.fromhex("83c110")            # add ecx,0x10      bottom=y+16
          + bytes.fromhex("51")                # push ecx
          + bytes.fromhex("8d4a10")            # lea ecx,[edx+0x10] right=L+16
          + bytes.fromhex("51")                # push ecx
          + bytes.fromhex("ff742420")          # push [esp+0x20]   top=rowY
          + bytes.fromhex("52")                # push edx          left
          + bytes.fromhex("8b10")              # mov edx,[eax]
          + bytes.fromhex("8bc8")              # mov ecx,eax
          + bytes.fromhex("ff92dc000000"))     # call [edx+0xdc]
    out.append((0x0076E145, 0x0076E16E - 0x0076E145, b2, "B2 checkbox rect"))

    # B3 @ 0x0076E1D6..0x0076E200 - AddChildWindow, then cbox swatch anchor.
    # Uses edx for the chart vtable and drops the ebp load (ebp's last read is
    # 0x0076E1A7, reassigned 0x0076E22D, so it is dead across the seam).
    b3va = 0x0076E1D6
    head = (bytes.fromhex("8b17")              # mov edx,[edi]
            + bytes.fromhex("8bcf")            # mov ecx,edi
            + bytes.fromhex("ff520c")          # call [edx+0xc]
            + bytes.fromhex("50")              # push eax
            + bytes.fromhex("8b0e")            # mov ecx,[esi]
            + bytes.fromhex("8b11")            # mov edx,[ecx]
            + bytes.fromhex("ff5238")          # call [edx+0x38]  AddChildWindow
            + bytes.fromhex("8b5c2450")        # mov ebx,[esp+0x50]
            + bytes.fromhex("2b5c2448")        # sub ebx,[esp+0x48]
            + bytes.fromhex("81eb") + _imm32(C.SWATCH_MARGIN_CBOX)
            + bytes.fromhex("8d8c24f8000000"))  # lea ecx,[esp+0xf8]
    b3 = head + b"\xe8" + _rel32(b3va + len(head) + 5, CALL_602BE0) + b"\x90"
    out.append((b3va, 0x0076E200 - b3va, b3, "B3 AddChild + cbox swatch anchor"))
    return out


def check_replacements(S, verbose):
    try:
        from capstone import Cs, CS_ARCH_X86, CS_MODE_32
    except Exception as e:                                   # pragma: no cover
        S.skip("capstone unavailable (%s) - replacement bytes UNVERIFIED. "
               "Do NOT ship the block re-encodings on this result." % e)
        return
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    for f in (1.5, 2.0, 3.0):
        C = consts_for(f)
        want = {"B1 plain swatch anchor": C.SWATCH_MARGIN_PLAIN,
                "B2 checkbox rect": C.CBOX_L_MARGIN,
                "B3 AddChild + cbox swatch anchor": C.SWATCH_MARGIN_CBOX}
        for va, stock_len, repl, label in build_replacements(f):
            S.ok(len(repl) == stock_len,
                    "f=%.2f %s length %d == stock %d"
                    % (f, label, len(repl), stock_len))
            ins = list(md.disasm(repl, va))
            decoded = sum(i.size for i in ins)
            S.ok(decoded == len(repl),
                    "f=%.2f %s disassembles cleanly and ends on the boundary "
                    "(%d/%d bytes)" % (f, label, decoded, len(repl)))
            found = [i for i in ins
                     if i.mnemonic in ("sub",) and hex(want[label]) in i.op_str]
            S.ok(bool(found),
                    "f=%.2f %s carries the certified imm32 %d"
                    % (f, label, want[label]))
            for i in ins:
                if i.mnemonic == "jbe":
                    S.ok(int(i.op_str, 16) == JBE_TARGET,
                            "f=%.2f %s jbe -> 0x%08X preserved"
                            % (f, label, JBE_TARGET))
                if i.mnemonic == "call" and i.op_str.startswith("0x"):
                    S.ok(int(i.op_str, 16) == CALL_602BE0,
                            "f=%.2f %s call -> 0x%08X preserved"
                            % (f, label, CALL_602BE0))
            if verbose:
                print("      %s f=%.2f  %s" % (label, f, repl.hex()))


def print_cpp_table():
    print("\n[6b] replacement hex for the C++ table (diff against "
          "CodePatches.cpp)")
    for f in (1.5, 2.0, 3.0):
        print("   f=%.2f  strip=%d" % (f, strip_for(f)))
        for va, _n, repl, label in build_replacements(f):
            print("      0x%08X  %-34s %s" % (va, label, repl.hex()))


def main():
    verbose = "--verbose" in sys.argv
    S = Suite()
    print("=== #57 LEFT-ANCHOR gate ===")
    print("\n[1] shipped-exe byte verification")
    check_bytes(S, verbose)
    print("\n[2] f=1 reduction to the MEASURED stock capture")
    check_stock_reduction(S, verbose)
    print("\n[3] every tier x both kinds x both checkbox-writer hypotheses")
    check_tiers(S, verbose)
    print("\n[4] the three gaps that ARE bug #57, at 2x")
    check_gaps(S, verbose)
    print("\n[5] vertical headroom against our own text-model error")
    check_headroom(S, verbose)
    print("\n[6] the REPLACEMENT bytes disassemble back correctly")
    check_replacements(S, verbose)
    if "--emit" in sys.argv:
        print_cpp_table()
    print("\n%d checks, %d failed" % (S.n, len(S.fail)))
    for m in S.fail:
        print("  FAILED: %s" % m)
    print("OVERALL: %s" % ("PASS" if not S.fail else "FAIL"))
    return 0 if not S.fail else 1


if __name__ == "__main__":
    sys.exit(main())
