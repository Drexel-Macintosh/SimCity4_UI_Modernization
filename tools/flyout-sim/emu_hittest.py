"""
emu_hittest.py - offline reader for SC4's UI CLICK/HIT-TEST logic.

Companion to emu_plot.py (which models the DRAW). This runs the REAL hit-test
machine code from SimCity 4.exe under Unicorn to map which screen points a
control treats as "inside" (clickable), independent of what it draws. It exists
because the disaster picker (and, ahead, several Mayor-mode controls) has TWO
layers: a drawn layer we scale, and a SEPARATE selectable layer we don't - so a
2x-drawn item can still only be clickable over its 1x footprint.

The chain it models (verified by disassembly):
  container.GetChildWindowFromCursorPoint  ->  child.[vtbl+0xf8]  (IsPointInMe)
    IsPointInMe (0x0099C97C):
      1. is (x,y) inside the coarse AREA rect at [this+0x14]?   (0x00664C60)
      2. does the window carry WinFlag_MouseTrans (0x80000)?    ([vt+0x10c])
         - if NOT: clickable == inside-rect.
         - if YES: transform the point ([vt+0xec]) then call the REFINED
           per-item test slot 149 ([vt+0x254]); the result is INVERTED
           (slot149 returns "is this point TRANSPARENT / pass-through", so
           opaque art => slot149=0 => clickable).
    slot 149 (0x0099BBBE):
      delegates to the sub-object at [this+0x64] (the item's hit MASK/buffer):
      valid? -> lock(0x800) -> mask.HitTest(x,y) -> unlock(0x800).

So the clickable footprint = coarse [0x14] rect INTERSECT (opaque pixels of the
[0x64] mask). Scaling the draw never touched the [0x64] mask -> right-half-only.
The runtime fix forces slot 149 -> 0 (opaque) so the whole [0x14] rect clicks;
this harness reproduces the bug AND proves that fix, with no game launch.

STAGE 0 - THE CONTAINER CLAIM GATE (v2.11.24 discovery). Upstream of all of the
above, the flyout CONTAINER (class vt 0x00AB6AA8) overrides IsPointInMe with
0x0079A180, which transforms the point then tail-calls its slot 121 at
0x0079AE30. That function claims the point ONLY when
    local_x >= (width - [this+0xe0])
i.e. the RIGHTMOST [0xe0] px - the strip column stored as width-from-right-
edge. [0xe0] kept its 1x value (~44-49) while the draw went 2x, so routing died
at the container for the pictures' left half and the strip stages above were
NEVER REACHED there (why the DS62/DS149 hooks stayed silent). The in-game fix
doubles [container+0xe0] (ini ClaimScale=2) AND forces slot 149 open
(SelForce=1). This harness runs the REAL 0x0079AE30 code as stage 0 and chains
it before the strip stages, reproducing the full bug and proving both levers.

Usage:  python emu_hittest.py                 # map the clickable x-range (bug)
        python emu_hittest.py --mask=44        # model a 44px (1x) opaque mask
        python emu_hittest.py --force149        # strip fix lever (slot149->0)
        python emu_hittest.py --claimw=88       # container fix lever ([0xe0]=88)
        python emu_hittest.py --claimw=88 --force149   # BOTH = the v2.11.24 fix
"""
import sys, struct
from unicorn import *
from unicorn.x86_const import *

EXE = r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Apps\SimCity 4.exe"
IMAGE_BASE = 0x400000
ISPOINTINME = 0x0099C97C   # child.[vtbl+0xf8], slot 62 - the routing hit-test
SLOT149     = 0x0099BBBE   # child.[vtbl+0x254] - refined per-item transparency test
RECT_CONTAINS = 0x00664C60 # (rect*, x, y) -> bool ; run for real
CLAIM121    = 0x0079AE30   # container slot 121 - claims rightmost [this+0xe0] px

OBJ    = 0x10000000; OBJ_VT = 0x10001000
SUB    = 0x12000000; SUB_VT = 0x12001000   # the [0x64] hit-mask sub-object
CONT   = 0x14000000                        # the flyout CONTAINER object
STACK  = 0x20000000; STACK_SZ = 0x100000
STUBS  = 0x30000000

# --- the item's real geometry, from the live DSEL/DGEO logs -----------------
RECT = (190, 732, 278, 1310)   # [0x14] coarse AREA rect (L,T,R,B), 88 wide
ITEM_Y = 900                   # a y inside the item band (732..1310)
CONT_RECT = (6, 610, 288, 1310)  # container [0xa8..0xb4] window rect (DCONT)

# model knobs
MASK_W   = 44                  # width of the OPAQUE (clickable) mask, right-aligned
CLAIM_W  = 49                  # container [0xe0]: strip-column claim width (1x bug
                               # value; 288-49=239 = the user-measured threshold)
FORCE149 = "--force149" in sys.argv
for a in sys.argv:
    if a.startswith("--mask="):   MASK_W  = int(a.split("=",1)[1])
    if a.startswith("--claimw="): CLAIM_W = int(a.split("=",1)[1])

test_x = 0   # set per-probe so the modelled mask can answer by x

def main():
    data = open(EXE, "rb").read()
    uc = Uc(UC_ARCH_X86, UC_MODE_32)
    img = (len(data) + 0xFFF) & ~0xFFF
    uc.mem_map(IMAGE_BASE, max(img, 0x800000)); uc.mem_write(IMAGE_BASE, data)
    for base, sz in [(OBJ, 0x2000), (SUB, 0x2000), (CONT, 0x2000), (STUBS, 0x10000)]:
        uc.mem_map(base, sz)
    uc.mem_map(STACK, STACK_SZ)

    # object: vtable ptr, AREA rect at 0x14, sub-object ptr at 0x64
    uc.mem_write(OBJ + 0x00, struct.pack("<I", OBJ_VT))
    uc.mem_write(OBJ + 0x14, struct.pack("<4i", *RECT))
    uc.mem_write(OBJ + 0x64, struct.pack("<I", SUB))
    uc.mem_write(SUB + 0x00, struct.pack("<I", SUB_VT))

    # CONTAINER object for stage 0: [0xa8..0xb4] window rect + [0xe0] claim
    # width. 0x0079AE30 reads only these fields - no vtable needed.
    uc.mem_write(CONT + 0xA8, struct.pack("<4i", *CONT_RECT))
    uc.mem_write(CONT + 0xE0, struct.pack("<i", CLAIM_W))

    # OBJ vtable: point 0x10c/0xec/0x254 at stubs (or the REAL slot149).
    for k in range(200):
        uc.mem_write(OBJ_VT + k*4, struct.pack("<I", STUBS + 0x0000 + k*8))
        uc.mem_write(SUB_VT + k*4, struct.pack("<I", STUBS + 0x4000 + k*8))
    # slot 149 (0x254) -> the REAL refined test, unless we're applying the fix.
    if not FORCE149:
        uc.mem_write(OBJ_VT + 149*4, struct.pack("<I", SLOT149))

    def stub(uc, addr, size, user):
        which = "OBJ" if addr < STUBS + 0x4000 else "SUB"
        slot = ((addr - STUBS) % 0x4000) // 8
        esp = uc.reg_read(UC_X86_REG_ESP)
        ret = struct.unpack("<I", uc.mem_read(esp, 4))[0]
        eax, argc = 1, 0
        if which == "OBJ":
            if slot == 67:  eax, argc = 1, 1          # GetFlag(MouseTrans) -> TRUE
            elif slot == 59: argc = 2; eax = 1        # transform point (identity)
            elif slot == 149: eax, argc = 0, 2        # FORCE149: slot149 -> 0 (opaque)
        else:  # SUB (the [0x64] hit mask)
            if slot == 24: eax, argc = 1, 0           # valid?
            elif slot == 6: eax, argc = 1, 1          # lock(0x800)
            elif slot == 7: eax, argc = 1, 1          # unlock(0x800)
            elif slot == 25:                          # HitTest -> is point TRANSPARENT?
                # TWO args (x,y). The push ebx before the call at 0x0099BBEB is
                # a register SAVE (pop ebx at 0x0099BC04 restores it), NOT an
                # argument - argc=3 ate the saved ebx and faulted EIP=x.
                argc = 2
                # model the 1x opaque mask, right-aligned in the coarse rect:
                # opaque (=> 0/clickable) only in the rightmost MASK_W px.
                opaque = test_x >= (RECT[2] - MASK_W)
                eax = 0 if opaque else 1              # 1 = transparent/pass-through
        uc.reg_write(UC_X86_REG_EAX, eax)
        uc.reg_write(UC_X86_REG_ESP, esp + 4 + argc*4)
        uc.reg_write(UC_X86_REG_EIP, ret)
    uc.hook_add(UC_HOOK_CODE, stub, begin=STUBS, end=STUBS + 0x10000)

    def run_method(entry, this, x, y):
        SENT = 0xDEADBEEF
        sp = STACK + STACK_SZ - 0x400
        sp -= 4; uc.mem_write(sp, struct.pack("<i", y))
        sp -= 4; uc.mem_write(sp, struct.pack("<i", x))
        sp -= 4; uc.mem_write(sp, struct.pack("<I", SENT))
        uc.reg_write(UC_X86_REG_ESP, sp)
        uc.reg_write(UC_X86_REG_ECX, this)
        uc.reg_write(UC_X86_REG_EBX, 0)
        try:
            uc.emu_start(entry, SENT, count=200000)
        except UcError as e:
            if "--debug" in sys.argv:
                print("   emu fault @0x%08X: %s" % (uc.reg_read(UC_X86_REG_EIP), e))
            return None
        return uc.reg_read(UC_X86_REG_EAX) & 0xFF

    def claim(x, y):
        # STAGE 0: the container's slot-121 claim (REAL code 0x0079AE30).
        # Its caller (custom IsPointInMe 0x0079A180) hands it CONTAINER-LOCAL
        # coordinates; model the transform as screen - container origin.
        return run_method(CLAIM121, CONT, x - CONT_RECT[0], y - CONT_RECT[1])

    def in_me(x, y):
        global test_x
        test_x = x
        return run_method(ISPOINTINME, OBJ, x, y)

    L, R = RECT[0], RECT[2]
    print("=== SC4 hit-test emulation: claim(0x%08X) -> IsPointInMe(0x%08X) ===" %
          (CLAIM121, ISPOINTINME))
    print("container rect [0xa8] = %s ; claim width [0xe0] = %d "
          "(claims abs x >= %d)" % (CONT_RECT, CLAIM_W, CONT_RECT[2] - CLAIM_W))
    print("strip coarse rect [0x14] = %s (%d wide)" % (RECT, R - L))
    print("model: MouseTrans set; [0x64] mask opaque only in rightmost %d px%s" %
          (MASK_W, "  ;  FIX: slot149 forced -> opaque(0)" if FORCE149 else ""))
    print("\n x (abs)   claim  strip  final     [strip-local]")
    clickable = []
    for x in range(L - 8, R + 9, 4):
        c = claim(x, ITEM_Y)                # stage 0: container gate (REAL code)
        s = in_me(x, ITEM_Y) if c else 0    # stages 1-2: strip only if routed
        hit = bool(c) and s == 1
        if hit: clickable.append(x)
        print("  %4d      %s      %s     %s  %s   x-L=%d" %
              (x, "#" if c else ".", "#" if s == 1 else ".",
               "#" if hit else ".", "CLICK" if hit else "  -  ", x - L))
    if clickable:
        print("\n=> clickable band: abs %d..%d  (%d px of the %d-wide item)"
              % (min(clickable), max(clickable), max(clickable) - min(clickable) + 4, R - L))
    else:
        print("\n=> clickable band: EMPTY")
    both = CLAIM_W >= (R - L) and FORCE149
    print("=> matches in-game: %s" % ("FULL width (v2.11.24 fix, both levers)" if both
          else "partial (one lever) - see bands above" if (FORCE149 or CLAIM_W > 60)
          else "RIGHT ~%d px only (the bug)" % min(MASK_W, CLAIM_W)))

if __name__ == "__main__":
    main()
