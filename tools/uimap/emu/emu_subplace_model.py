"""emu_subplace_model.py - #95 Phase 2: the DLL's sub-flyout placement model,
validated against SimCity 4's OWN sub_79AD00 under Unicorn.

THIS IS THE PERMANENT REGRESSION for SubPlaceTop/SubPlaceLeft in
UiSpike.cpp. If it ever prints REJECTED, the DLL is placing the
sub-flyout by an expression the game does not use. Run after ANY change
to those two functions. f=1 must reproduce stock exactly.

--------------------------------------------------------------------------
SCOPE OF THIS GATE - what a green run actually proves  (audit 2026-08-02)
--------------------------------------------------------------------------
Law: "an offline gate is only as honest as its SCOPE." Until 2026-08-02 this
file computed contentH and then compared ONLY (left, top) - the container's
ORIGIN was gated, its SIZE was not - and it exited 0 whether it printed
VALIDATED or REJECTED, so a CI step calling it could never fail. Both holes
are closed. What is covered NOW, for n in 1..8 x f in {1, 1.5, 2, 3}:

  COVERED   left    == emulated SetArea L
  COVERED   top     == emulated SetArea T
  COVERED   contentH== emulated SetArea (B - T)      <- added 2026-08-02
  EXIT CODE 0 only when all three match in all 32 cases; 1 on ANY mismatch,
            and 1 if the emulator never reached SetArea for a case.

  NOT COVERED  the container WIDTH (SetArea R - L). sub_79AD00 derives R from
            the strip width argument we hand it, so comparing it would only
            re-measure our own input, not the game's arithmetic. `left` is
            the only x-axis quantity the function decides.
  NOT COVERED  everything outside sub_79AD00: the ring blit Y (gSubRingBltY),
            the strip's own item metrics, and the dock MOVE. Those have their
            own instruments - see reference-subflyout-ring-law.

ORIGINAL NOTE:

If this model reproduces the emulator's rect for every n and every f, the same
integer expression can be ported to C++ with confidence. If it does not, the
model is wrong and NOTHING gets ported (the -2 my closed form dropped is
exactly the class of error this catches).
"""
import sys, os, importlib.util
EMU = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("emu_subflyout", os.path.join(EMU, "emu_subflyout.py"))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
import struct

CX, CY, VIEW_H = 198, 560, 1600
RHU = m.round_half_up


def model(n, f):
    """The game's own arithmetic, every metric scaled by f, integer ops kept."""
    F = {k: RHU(v * f) for k, v in m.STOCK_FIELDS.items()}
    itemH = RHU(m.ITEM_H * f)
    itemW = RHU(m.ITEM_W * f)
    spacing = RHU(m.SPACING * f)
    margT = RHU(10 * f)
    margB = VIEW_H - margT

    stripH = (itemH + spacing) * n - spacing
    contentH = max(stripH, F[0xF4]) + 2 * F[0xE8]

    top = (F[0xF4] >> 1) - (contentH >> 1) + CY - F[0x100]
    left = CX - F[0xFC]

    top = max(top, margT)                                   # top margin
    top = min(top, margB - contentH)                        # bottom margin
    top = min(top, CY - F[0x100] - F[0xE8])                 # button not above
    top = max(top, CY + F[0xF4] - contentH + F[0xE8] - F[0x100])  # not below
    return left, top, contentH


def emu_place(emu, n, f):
    from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_ECX
    uc = emu.uc
    obj, vt = m.HEAP + 0x1000, m.HEAP + 0x8000
    uc.mem_write(obj, b"\x00" * 0x400)
    uc.mem_write(vt, b"\x00" * 0x400)
    uc.mem_write(vt + 0xDC, struct.pack("<I", m.SETAREA_STUB))
    uc.mem_write(obj + 4, struct.pack("<I", vt))
    for off, val in m.STOCK_FIELDS.items():
        uc.mem_write(obj + off, struct.pack("<i", RHU(val * f)))
    itemW, itemH, spacing = RHU(m.ITEM_W * f), RHU(m.ITEM_H * f), RHU(m.SPACING * f)
    margT = RHU(10 * f)
    args = (itemW, (itemH + spacing) * n - spacing, CX, CY, margT, VIEW_H - margT)
    esp = m.STACK + m.STACKSZ - 0x100
    for a in reversed(args):
        esp -= 4
        uc.mem_write(esp, struct.pack("<i", a))
    esp -= 4
    uc.mem_write(esp, struct.pack("<I", m.MAGIC_RET))
    uc.reg_write(UC_X86_REG_ESP, esp)
    uc.reg_write(UC_X86_REG_ECX, obj)
    emu.setarea = None
    uc.emu_start(m.PLACE_FN, m.MAGIC_RET)
    return emu.setarea


emu = m.PlaceEmu()
emu.fields = m.STOCK_FIELDS
bad = 0
total = 0
# The emulator's SetArea hook records (l, t, r, b) - emu_subflyout.py:144 - so
# the container HEIGHT the game actually computed is b - t. Comparing our
# contentH against it is the half of the model that used to be computed and
# then thrown away.
print("  f    n | emu (L,T,H)         | model (L,T,H)       | match")
print("-------+---------------------+---------------------+------")
for f in (1.0, 1.5, 2.0, 3.0):
    for n in range(1, 9):
        e = emu_place(emu, n, f)
        mo = model(n, f)
        total += 1
        if e is None:
            # No SetArea reached => the emulation did not exercise the code we
            # claim to model. A silent skip here is exactly the structural null
            # the "NULL IS NOT EVIDENCE" law forbids: fail loudly instead.
            bad += 1
            print("%5.2f  %d | %-19s | (%5d,%5d,%5d) | **NO SETAREA**"
                  % (f, n, "(emulator never set)", mo[0], mo[1], mo[2]))
            continue
        eH = e[3] - e[1]
        okLT = (e[0], e[1]) == (mo[0], mo[1])
        okH = eH == mo[2]
        ok = okLT and okH
        if not ok:
            bad += 1
        why = "OK" if ok else ("**MISMATCH H**" if okLT else "**MISMATCH**")
        print("%5.2f  %d | (%5d,%5d,%5d) | (%5d,%5d,%5d) | %s"
              % (f, n, e[0], e[1], eH, mo[0], mo[1], mo[2], why))
print("\n%d/%d exact (L,T,H). Model %s"
      % (total - bad, total, "VALIDATED" if bad == 0 else "REJECTED"))

if bad == 0:
    print("\n--- the DOCK DELTA our DLL must apply (stock placement -> true f) ---")
    print(" f    n | delta L | delta T")
    for f in (1.5, 2.0, 3.0):
        for n in (1, 4, 8):
            s = emu_place(emu, n, 1.0)
            t = emu_place(emu, n, f)
            print("%4.2f  %d | %7d | %7d" % (f, n, t[0] - s[0], t[1] - s[1]))

# A regression gate that always exits 0 is not a gate - a CI step calling this
# file passed on REJECTED for as long as this file has existed. Exit non-zero
# on ANY mismatch so the caller (and the operator's shell) actually sees it.
if bad:
    print("\nFAIL: %d/%d case(s) disagree with sub_79AD00. Do NOT port or ship "
          "SubPlaceTop/SubPlaceLeft until this reads VALIDATED." % (bad, total))
    sys.exit(1)
sys.exit(0)
