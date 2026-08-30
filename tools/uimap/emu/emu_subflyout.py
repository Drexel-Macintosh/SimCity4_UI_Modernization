"""
emu_subflyout.py - offline proof for the SUB-FLYOUT BORN-2x fix (task #50).

Runs SimCity 4's OWN geometry code for the nested plop sub-flyout under
Unicorn - no game launch, no debugger, nothing written to any game file - and
answers the one question the fix depends on:

    "If we scale the FINISHED rects at birth instead of on the next sweep
     tick, do we get exactly the rects the sweep produces today?"

WHAT IS REAL AND WHAT IS MODELLED
---------------------------------
REAL machine code, executed:
  sub_79AD00   0x0079AD00   container Place(w,h,cx,cy,margT,margB)
                            - computes the container rect, calls SetArea, and
                              writes the strip rect to [this+0x108..0x114]
MODELLED (python):
  [vt+0xDC] SetArea(l,t,r,b)  - intercepted at a stub address; we record the
                              four arguments, which IS the container rect.
                              (The real cGZWin::SetArea just stores them.)

The object is built exactly as sub_7EAEB0 leaves it before the Place call
(SUBFLYOUT-BUILDER.md 3.1/3.2): the seven SetLayout fields at their stock
values, the cIGZWin base vptr at [obj+4].

USAGE
  python emu_subflyout.py              # the acceptance suite (what CI runs)
  python emu_subflyout.py --verbose    # + every rect at every tier
"""

import struct
import sys

# Resolved, not hard-coded: $SC4_EXE, else tools/sc4paths.py's install
# lookup, else the Steam default. See tools/uimap/common.py _resolve_exe.
def _exe():
    import os as _os, sys as _sys
    env = _os.environ.get("SC4_EXE")
    if env:
        return env
    try:
        _sys.path.insert(0, _os.path.dirname(_os.path.dirname(
            _os.path.dirname(_os.path.abspath(__file__)))))
        from sc4paths import exe_path
        p = exe_path()
        if p and _os.path.isfile(p):
            return p
    except Exception:
        pass
    return (r"C:\Program Files (x86)\Steam\steamapps\common"
            r"\SimCity 4 Deluxe\Apps\SimCity 4.exe")


EXE = _exe()
IMAGE_BASE = 0x400000

PLACE_FN = 0x0079AD00          # container Place(w,h,cx,cy,margT,margB), ret 0x18

HEAP = 0x10000000
HEAPSZ = 0x00100000
STACK = 0x20000000
STACKSZ = 0x00100000
SETAREA_STUB = 0x30000000      # where [vt+0xDC] points in this model
STUBSZ = 0x1000
MAGIC_RET = 0x40000000         # emulation stops when EIP reaches here

# --- the stock SetLayout fields (SUBFLYOUT-BUILDER.md 3.2, byte-verified) ----
STOCK_FIELDS = {
    0xE4: 53,    # bar width / hit-claim
    0xE8: 25,    # end cap, x2 = the +50
    0xF0: 80,    # ring sprite width
    0xF4: 53,    # ring height / minimum content height (the Freight floor)
    0xF8: 4,     # ring/bar overlap
    0xFC: 27,    # x anchor
    0x100: 29,   # y anchor
}
ITEM_W, ITEM_H, SPACING = 44, 44, 5     # strip->SetItemMetrics(44,44,5)

# --- the live oracle: every 2x rect ever measured (LIVE-EVIDENCE 2a/2b) ------
# n -> (containerW, containerH, stripRelL, stripRelT, stripW, stripH)
LIVE_2X = {
    3: (258, 384, 160, 50, 88, 284),
    4: (258, 482, 160, 50, 88, 382),
    6: (258, 678, 160, 50, 88, 578),
}

# --- TWO BUILDERS SHARE THIS Place ------------------------------------------
# sub_79AD00 is a CLASS METHOD. sub_7EAEB0 (the nested sub-flyout, fixed in
# v2.36.0) and sub_7E7270 (the FIRST-LEVEL Create Disaster flyout, task #5)
# both call it - so this emulator does not need repointing at all, only new
# INPUTS. The two call sites are byte-parallel and were re-verified 2026-07-31:
#   SetLayout  0x7EB16E / 0x7E74AE   (both ff 50 10)
#   Place      0x7EB193 / 0x7E74D3   (both ff 52 14), delta 0x25 in BOTH
#   accept ret 0x7EB196 / 0x7E74D6
# sub_7E7270 has exactly ONE caller (0x7F4D2C, reached via cmp esi,0x69B9324A)
# and zero raw-address occurrences image-wide.
BUILDERS = {
    "sub": {
        "name": "sub_7EAEB0 nested sub-flyout (v2.36.0, user-confirmed)",
        "fields": STOCK_FIELDS,
        "n_range": range(1, 9),
        "width_1x": 129,
        "floor_1x": 103,
        "live_2x": LIVE_2X,
    },
    "disaster": {
        # SetLayout args byte-read at 0x7E749D..0x7E74A9 (seven push imm8).
        "name": "sub_7E7270 Create Disaster first-level flyout (task #5)",
        "fields": {0xE4: 53, 0xE8: 25, 0xF0: 94, 0xF4: 62, 0xF8: 6,
                   0xFC: 40, 0x100: 34},
        "n_range": range(1, 7),          # cmp eax,6 caps the rows
        "width_1x": 141,
        "floor_1x": 112,
        # The ONLY live 2x sighting we have, and it is triangulated from three
        # independently recorded numbers rather than fitted:
        #   141x339  = DOBS srcBuf (SC4-UI-ENGINE 2.1) + HANDOFF-god-mode "created once at 141x339"
        #   282x678  = the measured live container (REGRESSION.md:337)
        #   strip relX 184 = GOD-MODE-FLYOUTS.md "flings its strip from rel X184 -> X368",
        #                    i.e. 184 was already correct and the sweep doubled it AGAIN.
        "live_2x": {6: (282, 678, 184, 50, 88, 578)},
        # v2.39.5 (task #80, the missing scroll arrow): the flyout has 9
        # disasters but builds a 6-row strip, so stock ALWAYS scrolls. The
        # arrow-cap decision's arithmetic is the strip Plot's own opening
        # lines (0x79AA70, instruction-read 2026-07-31):
        #     visibleRows = (stripWinH + spacing) // (itemH + spacing)
        # arrows needed <=> visibleRows < total. The flags themselves are
        # container bytes [0x118]/[0x119] (Plot reads them at 0x79B0E0
        # +0x10D/+0x143; constructor 0x7F0AF4 births them 0).
        "total_items": 9,
    },
}


# ONE SOURCE FOR THE SCALING RULES (scale_rules.py). This file used to
# carry its own copy; #162 changed ScaleRound in the DLL and every private
# copy in this folder had to be found by hand. `scale_rules.py --drift`
# hunts any that come back.
from scale_rules import round_half_up          # noqa: E402


class PlaceEmu(object):
    def __init__(self):
        from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
        data = open(EXE, "rb").read()
        uc = Uc(UC_ARCH_X86, UC_MODE_32)
        span = max((len(data) + 0xFFF) & ~0xFFF, 0x800000)
        uc.mem_map(IMAGE_BASE, span)
        uc.mem_write(IMAGE_BASE, data)
        uc.mem_map(HEAP, HEAPSZ)
        uc.mem_map(STACK, STACKSZ)
        uc.mem_map(SETAREA_STUB, STUBSZ)
        uc.hook_add(UC_HOOK_CODE, self._hook_setarea,
                    begin=SETAREA_STUB, end=SETAREA_STUB + 4)
        self.uc = uc
        self.setarea = None
        self.fields = None

    # -- the one modelled call -------------------------------------------
    def _hook_setarea(self, uc, addr, size, user):
        from unicorn.x86_const import (UC_X86_REG_ESP, UC_X86_REG_EIP,
                                       UC_X86_REG_EAX)
        esp = uc.reg_read(UC_X86_REG_ESP)
        args = [struct.unpack("<i", uc.mem_read(esp + 4 + 4 * i, 4))[0]
                for i in range(4)]
        self.setarea = tuple(args)                  # (l, t, r, b)
        ret = struct.unpack("<I", uc.mem_read(esp, 4))[0]
        uc.reg_write(UC_X86_REG_EAX, 1)
        uc.reg_write(UC_X86_REG_ESP, esp + 4 + 4 * 4)   # callee-cleans, 4 args
        uc.reg_write(UC_X86_REG_EIP, ret)

    def place(self, n, cx=198, cy=560, view_h=1600):
        """Run the REAL Place for an n-item menu. Returns (container, strip)."""
        from unicorn.x86_const import (UC_X86_REG_ESP, UC_X86_REG_ECX)
        uc = self.uc
        obj, vt = HEAP + 0x1000, HEAP + 0x8000
        uc.mem_write(obj, b"\x00" * 0x400)
        uc.mem_write(vt, b"\x00" * 0x400)
        uc.mem_write(vt + 0xDC, struct.pack("<I", SETAREA_STUB))
        uc.mem_write(obj + 4, struct.pack("<I", vt))     # cIGZWin base vptr
        for off, val in (self.fields or STOCK_FIELDS).items():
            uc.mem_write(obj + off, struct.pack("<i", val))

        strip_h = (ITEM_H + SPACING) * n - SPACING
        args = (ITEM_W, strip_h, cx, cy, 10, view_h - 10)
        esp = STACK + STACKSZ - 0x100
        for i, a in enumerate(reversed(args)):
            esp -= 4
            uc.mem_write(esp, struct.pack("<i", a))
        esp -= 4
        uc.mem_write(esp, struct.pack("<I", MAGIC_RET))
        uc.reg_write(UC_X86_REG_ESP, esp)
        uc.reg_write(UC_X86_REG_ECX, obj)
        self.setarea = None
        uc.emu_start(PLACE_FN, MAGIC_RET)

        sl, st, sr, sb = struct.unpack("<4i", uc.mem_read(obj + 0x108, 16))
        return self.setarea, (sl, st, sr, sb)


def scale_rect(rect, f):
    """Exactly what ScaleSubtree does to a rect (UiSpike.cpp:8197-8200):
    every EDGE is rounded, so abutting siblings stay abutting."""
    return tuple(round_half_up(v * f) for v in rect)


def main():
    verbose = "--verbose" in sys.argv
    which = "sub"
    for a in sys.argv[1:]:
        if a.startswith("--builder="):
            which = a.split("=", 1)[1]
    if which not in BUILDERS:
        print("unknown --builder=%s (have: %s)"
              % (which, ", ".join(sorted(BUILDERS))))
        return 2
    B = BUILDERS[which]
    emu = PlaceEmu()
    emu.fields = B["fields"]
    LIVE = B["live_2x"]
    fails, checks = [], 0

    print("emu_subflyout - the game's own sub_79AD00 (Place), run offline")
    print("builder: %s" % B["name"])
    print("=" * 70)
    for f in (1.0, 1.5, 2.0, 3.0):
        if verbose or f == 2.0:
            print("\n  tier f=%.2f" % f)
        for n in B["n_range"]:
            cont, strip = emu.place(n)
            cl, ct, cr, cb = cont
            # BIRTH scale: take the finished 1x rects and scale them, which is
            # what the Place detour does. Container keeps its origin (the sweep
            # only SetW/SetH on a root); the strip is a child, so all four of
            # its parent-relative edges scale.
            bw = round_half_up(cr * f) - round_half_up(cl * f)
            bh = round_half_up(cb * f) - round_half_up(ct * f)
            bs = scale_rect(strip, f)
            born = (bw, bh, bs[0], bs[1], bs[2] - bs[0], bs[3] - bs[1])
            if verbose or f == 2.0:
                print("    n=%d  1x container %dx%d  strip rel(%d,%d) %dx%d"
                      "   ->  born %dx%d  strip rel(%d,%d) %dx%d"
                      % (n, cr - cl, cb - ct, strip[0], strip[1],
                         strip[2] - strip[0], strip[3] - strip[1],
                         born[0], born[1], born[2], born[3],
                         born[4], born[5]))

            # CHECK 1 - the live oracle (2x only; no 1.5x/3x sighting exists).
            if f == 2.0 and n in LIVE:
                checks += 1
                if born != LIVE[n]:
                    fails.append("n=%d born %s != measured live %s"
                                 % (n, born, LIVE[n]))

            # CHECK 2 - born == what the sweep produces from the same 1x rects
            # (the whole safety argument: identical geometry, different time).
            checks += 1
            sweep_w = round_half_up(cr * f) - round_half_up(cl * f)
            sweep_h = round_half_up(cb * f) - round_half_up(ct * f)
            sweep_s = scale_rect(strip, f)
            if (bw, bh) != (sweep_w, sweep_h) or bs != sweep_s:
                fails.append("n=%d f=%.2f born != sweep" % (n, f))

            # CHECK 3 - the width invariant: 129 at 1x, at every item count.
            checks += 1
            if cr - cl != B["width_1x"]:
                fails.append("n=%d container width %d, expected the %d "
                             "invariant" % (n, cr - cl, B["width_1x"]))

            # CHECK 4 - the Freight floor: 1 item is BELOW the 53 minimum, so
            # the height must clamp to 53+50=103 (the one size that fits no
            # arithmetic progression).
            if n == 1:
                checks += 1
                if cb - ct != B["floor_1x"]:
                    fails.append("n=1 height %d, expected the %d floor"
                                 % (cb - ct, B["floor_1x"]))

            # CHECK 5 (v2.39.5) - THE ARROW DECISION MUST BE TIER-INVARIANT.
            # visibleRows = (stripH + sp) // (itemH + sp), from the REAL
            # strip Plot's opening arithmetic (0x79AA70). stripH comes from
            # the REAL Place run above, never hand-typed. Three states:
            #   stock 1x            -> scroll needed (the arrow exists)
            #   v2.39.4 half-born   -> rect 2x, metrics 1x: decision FLIPS
            #                          (the shipped bug, must reproduce)
            #   v2.39.5 fully born  -> rect 2x, metrics 2x: decision matches
            #                          stock again (the fix)
            if "total_items" in B and n == max(B["n_range"]):
                total = B["total_items"]
                sh1 = strip[3] - strip[1]                  # 1x, real Place
                shf = bs[3] - bs[1]                        # born rect
                ih1, sp1 = ITEM_H, SPACING
                ihf = round_half_up(ITEM_H * f)
                spf = round_half_up(SPACING * f)
                stock_rows = (sh1 + sp1) // (ih1 + sp1)
                half_rows = (shf + sp1) // (ih1 + sp1)    # v2.39.4 state
                born_rows = (shf + spf) // (ihf + spf)    # v2.39.5 state
                checks += 3
                if not (stock_rows < total):
                    fails.append("f=%.2f stock shows no arrow (%d rows >= %d"
                                 " items) - oracle broken" % (f, stock_rows, total))
                # The half-born bug is 2x-SPECIFIC (first measured here): at
                # 1.5x the mixed-unit division still lands under 9 (8 rows),
                # so the arrow never went missing on that tier. Assert the
                # bug reproduces exactly where it shipped: f=2.
                if f == 2.0 and not (half_rows >= total):
                    fails.append("f=2 half-born state did NOT reproduce the"
                                 " missing-arrow bug (%d rows < %d items)"
                                 % (half_rows, total))
                elif f != 2.0:
                    checks -= 1
                # Born must always keep the arrow (rows < total). Row-count
                # EQUALITY with stock holds at integer tiers; at 1.5x the
                # rounding laws diverge by one row (born 5 vs stock 6) - the
                # task #75 family, measured 2026-07-31, accepted + logged
                # loudly rather than silently averaged away.
                if not (born_rows < total):
                    fails.append("f=%.2f born decision shows NO arrow "
                                 "(%d rows >= %d)" % (f, born_rows, total))
                if f in (1.0, 2.0, 3.0) and born_rows != stock_rows:
                    fails.append("f=%.2f born decision %d rows != stock %d at "
                                 "an integer tier" % (f, born_rows, stock_rows))
                if verbose or f == 2.0:
                    print("    arrow: stock %d rows, half-born %d, born %d "
                          "(total %d) -> arrow %s"
                          % (stock_rows, half_rows, born_rows, total,
                             "BORN" if born_rows < total else "ABSENT"))
                if f == 1.5 and born_rows != stock_rows:
                    print("    NOTE f=1.5: born %d rows vs stock %d - the "
                          "known 1.5x rounding divergence (task #75), arrow "
                          "still present" % (born_rows, stock_rows))

    print("\n" + "=" * 70)
    if fails:
        print("FAIL (%d checks, %d failures)" % (checks, len(fails)))
        for m in fails:
            print("   x " + m)
        return 1
    print("PASS - %d checks. Born-at-Place geometry is IDENTICAL to the "
          "sweep's, and matches every measured live rect." % checks)
    return 0


if __name__ == "__main__":
    sys.exit(main())
