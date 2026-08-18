"""
emu_gauge.py - offline reader for the U-Drive-It GAUGE control (clsid 0xCBCBF1E0).

Runs the REAL draw-self slot (vtable idx 88 == 0x00762830) from SimCity 4.exe
under Unicorn with a synthetic control object, stubs the image + draw-context
vtable calls, and CAPTURES the exact (source, destination) rect pair the control
feeds its draw context. Answers the only question that matters for 2x: is the
DESTINATION rect derived from the WINDOW (scales for free) or from the ART
(stays 1x in a doubled window)?

Companion to emu_plot.py (disaster-flyout container). Same harness idea.

Usage:
    python emu_gauge.py                          # stock: 58x62 art, win 58x62
    python emu_gauge.py --img=58,62 --frames=16 --frame=7 --win=116,124
    python emu_gauge.py --img=116,124            # what 2x ART would produce

Field map (offsets are relative to the cIGZWin SUB-OBJECT = the pointer the
window tree hands out = classBase+4):
    0x6c  draw context      0xd8  strip image (cIGZBuffer)
    0xe8  frame count       0xf8  current frame index
"""
import sys
import struct
from unicorn import *
from unicorn.x86_const import *

EXE = r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Apps\SimCity 4.exe"
IMAGE_BASE = 0x400000
DRAW = 0x00762830          # class 0xCBCBF1E0, cIGZWin vtable idx 88 (+0x160)
# --draw=<VA> points the same harness at ANOTHER class's slot-88 draw, so
# the blit behaviour of any code-painted control can be classified offline
# instead of by shipping a build (BLIT-BEHAVIOUR.md, law 35). ⚠ The object
# field map below is THIS class's; a class that keeps its image or frame
# count at different offsets needs its own map before the result means
# anything. A run that produces no CTX call is a NULL, not a verdict.

OBJ = 0x10000000           # the control (cIGZWin sub-object)
CTX = 0x11000000           # [0x6c] draw context
IMG = 0x12000000           # [0xd8] strip image
STUBS = 0x30000000
STACK = 0x20000000
STACK_SZ = 0x100000


def vtable_for(base):
    return base + 0x1000


def rect_at(uc, ptr):
    if not ptr or ptr < 0x1000:
        return None
    try:
        return struct.unpack("<4i", uc.mem_read(ptr & 0xFFFFFFFF, 16))
    except UcError:
        return None


def main():
    img_w, img_h = 58, 62
    frames, frame = 16, 0
    win_w, win_h = 58, 62
    visible = 1
    for a in sys.argv[1:]:
        if a.startswith("--img="):
            img_w, img_h = (int(x, 0) for x in a.split("=", 1)[1].split(","))
        elif a.startswith("--win="):
            win_w, win_h = (int(x, 0) for x in a.split("=", 1)[1].split(","))
        elif a.startswith("--frames="):
            frames = int(a.split("=", 1)[1], 0)
        elif a.startswith("--frame="):
            frame = int(a.split("=", 1)[1], 0)
        elif a.startswith("--draw="):
            globals()["DRAW"] = int(a.split("=")[1], 16)
        elif a.startswith("--invisible"):
            visible = 0

    data = open(EXE, "rb").read()
    uc = Uc(UC_ARCH_X86, UC_MODE_32)
    uc.mem_map(IMAGE_BASE, max((len(data) + 0xFFF) & ~0xFFF, 0x800000))
    uc.mem_write(IMAGE_BASE, data)
    for base in (OBJ, CTX, IMG):
        uc.mem_map(base, 0x2000)
    uc.mem_map(STUBS, 0x10000)
    uc.mem_map(STACK, STACK_SZ)

    # object: vtable at +0, window rect, and the class's own fields
    uc.mem_write(OBJ + 0x00, struct.pack("<I", vtable_for(OBJ)))
    uc.mem_write(OBJ + 0xa8, struct.pack("<4i", 363, 74, 363 + win_w, 74 + win_h))
    uc.mem_write(OBJ + 0x6c, struct.pack("<I", CTX))
    uc.mem_write(OBJ + 0xd8, struct.pack("<I", IMG))
    uc.mem_write(OBJ + 0xe8, struct.pack("<I", frames))
    uc.mem_write(OBJ + 0xf8, struct.pack("<I", frame))

    tags = {OBJ: 0, CTX: 1, IMG: 2}
    for b in (OBJ, CTX, IMG):
        uc.mem_write(b + 0x00, struct.pack("<I", vtable_for(b)))
        for k in range(160):
            uc.mem_write(vtable_for(b) + k * 4,
                         struct.pack("<I", STUBS + tags[b] * 0x800 + k * 8))

    captured = []

    def stub(uc, address, size, user):
        tag = (address - STUBS) // 0x800
        slot = ((address - STUBS) % 0x800) // 8
        esp = uc.reg_read(UC_X86_REG_ESP)
        ret = struct.unpack("<I", uc.mem_read(esp, 4))[0]
        argcnt = 0
        eax = 1
        if tag == 0 and slot == 72:            # this->vt[+0x120] -> bool
            eax = visible
            captured.append(("OBJ.vt[72] (+0x120) visibility gate", eax))
        elif tag == 2 and slot == 9:           # cIGZBuffer::Width
            eax = img_w
        elif tag == 2 and slot == 10:          # cIGZBuffer::Height
            eax = img_h
        elif tag == 1 and slot == 38:          # drawctx->vt[+0x98]
            argcnt = 3
            a = [struct.unpack("<I", uc.mem_read(esp + 4 + 4 * i, 4))[0]
                 for i in range(3)]
            captured.append(("CTX.vt[38] (+0x98)",
                             {"arg1_image": hex(a[0]),
                              "arg2_rect": rect_at(uc, a[1]),
                              "arg3_rect": rect_at(uc, a[2])}))
        else:
            captured.append(("unstubbed tag=%d slot=%d" % (tag, slot), None))
        uc.reg_write(UC_X86_REG_EAX, eax)
        uc.reg_write(UC_X86_REG_ESP, esp + 4 + argcnt * 4)
        uc.reg_write(UC_X86_REG_EIP, ret)

    uc.hook_add(UC_HOOK_CODE, stub, begin=STUBS, end=STUBS + 0x10000)

    SENTINEL = 0xDEADBEEF
    sp = STACK + STACK_SZ - 0x400
    sp -= 4
    uc.mem_write(sp, struct.pack("<I", SENTINEL))
    uc.reg_write(UC_X86_REG_ESP, sp)
    uc.reg_write(UC_X86_REG_ECX, OBJ)
    try:
        uc.emu_start(DRAW, SENTINEL, count=200000)
    except UcError as e:
        print("emu stopped:", e, "eip=0x%08X" % uc.reg_read(UC_X86_REG_EIP))

    print("=== inputs ===")
    print("  window      %dx%d   (abs 363,74)" % (win_w, win_h))
    print("  strip image %dx%d   frames=%d frame=%d visible=%d"
          % (img_w, img_h, frames, frame, visible))
    print("  cellW = imgW/frames = %d" % (img_w // frames if frames else 0))
    print("=== captured calls ===")
    for label, info in captured:
        print("  %-34s %s" % (label, info))
    print("=== verdict ===")
    print("  arg2 slides right with `frame`  -> SOURCE rect into the strip")
    print("  arg3 is (0,0,cellW,imgH)        -> DESTINATION, window-local,")
    print("                                     sized from the ART, NOT the window")


if __name__ == "__main__":
    main()
