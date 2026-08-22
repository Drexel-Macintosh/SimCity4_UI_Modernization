"""
emu_plot.py - offline reader for SC4 code-painted UI controls.

Executes the REAL Plot() machine code from SimCity 4.exe under the Unicorn CPU
emulator with a synthetic control object, and captures the exact rects it feeds
to each draw call (bar-top blit, circle arc, bar-bottom blit, screen composite).
No game launch needed - vary the object's fields and instantly see how each one
moves/sizes every element. Built for the disaster flyout container Plot()
(0x0079B0E0) but the harness is reusable for any Mayor-mode control.

Usage:  python emu_plot.py            # natural (1x) fields
        python emu_plot.py --fields e0=106,ec=188   # override any field
"""
import sys, struct
from unicorn import *
from unicorn.x86_const import *

EXE = r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Apps\SimCity 4.exe"
IMAGE_BASE = 0x400000
PLOT = 0x0079B0E0
ARC_HELPER = 0x008D8BC0          # circle-arc draw (direct call)
FACTORY = 0x00913C1A             # 0x79b0f6 call -> ebp

# --- memory layout (all in the emulator's address space) -----------------
OBJ      = 0x10000000   # the control object (this)
DRAWCTX  = 0x11000000   # [0xd8] draw context
BUF      = 0x12000000   # [0xdc] cached buffer
DST      = 0x13000000   # [0x68] screen buffer
STACK    = 0x20000000
STACK_SZ = 0x100000
STUBS    = 0x30000000   # one stub addr per (vtable, slot); hooked to fake-return
SCRATCH  = 0x31000000   # scratch rects GetBufferArea can fill

# Each object's vtable lives just after the object; slot k -> a unique stub addr
# so the hook can dispatch by (which object, which slot).
def vtable_for(base):
    return base + 0x1000

# canned buffer geometry (the natural disaster container buffer).
# Overridable with --buf=W,H : our 2x recipe reallocs it to the full 282x678
# window, so pass --buf=282,678 to model the redraw path.
BUF_W, BUF_H = 141, 339

# --- tiler (0x8d8bc0) instrumentation state -------------------------------
# We now RUN the real tiler instead of stubbing it, force its software path,
# and label every per-tile Blt it emits so we can see the spine tile offline.
TILER      = 0x008D8BC0
TILER_RETS = (0x008D8C40, 0x008D8CA7, 0x008D8D3C, 0x008D9012)
IID_HW     = 0xAB300B2B   # QueryInterface IID for the hardware blit path
in_tiler   = False
tiler_info = None         # (destRect, clipRect) of the current tiler call

captured = []   # (label, [rects...])

def rd(uc, addr, n=4):
    return struct.unpack("<i", uc.mem_read(addr, 4))[0] if n == 4 else uc.mem_read(addr, n)

def rect_at(uc, ptr):
    if ptr == 0 or ptr < 0x1000:
        return None
    try:
        a, b, c, d = struct.unpack("<4i", uc.mem_read(ptr & 0xFFFFFFFF, 16))
        return (a, b, c, d)
    except UcError:
        return None

def load_fields(argv):
    # offsets are BYTE offsets into the object; value = int32
    F = {0xa8: 66, 0xac: 682, 0xb0: 348, 0xb4: 1360,      # window rect L,T,R,B
         0xe0: 53, 0xe4: 25, 0xe8: 12, 0xec: 94, 0xf0: 62, 0xf4: 6,
         0x100: 138, 0x118: 0x00000100, 0x11c: 0, 0x120: 0,
         0x114: 1}   # dirty bit set -> take the redraw path
    for a in argv:
        if a.startswith("--fields"):
            spec = a.split("=", 1)[1] if "=" in a else argv[argv.index(a)+1]
            for kv in spec.split(","):
                k, v = kv.split("=")
                F[int(k, 16)] = int(v, 0)
    return F

def main():
    fields = load_fields(sys.argv[1:])
    global BUF_W, BUF_H
    for a in sys.argv:
        if a.startswith("--buf="):
            w, h = a.split("=", 1)[1].split(","); BUF_W, BUF_H = int(w), int(h)
    data = open(EXE, "rb").read()

    uc = Uc(UC_ARCH_X86, UC_MODE_32)
    # map the whole exe image (code + rdata + data) 1:1 at its VA
    img_sz = (len(data) + 0xFFF) & ~0xFFF
    uc.mem_map(IMAGE_BASE, max(img_sz, 0x800000))
    uc.mem_write(IMAGE_BASE, data)

    for base, sz in [(OBJ, 0x2000), (DRAWCTX, 0x2000), (BUF, 0x2000),
                     (DST, 0x2000), (STUBS, 0x10000), (SCRATCH, 0x10000)]:
        uc.mem_map(base, sz)
    uc.mem_map(STACK, STACK_SZ)

    # object fields
    for off, val in fields.items():
        uc.mem_write(OBJ + off, struct.pack("<I", val & 0xFFFFFFFF))
    # object + sub-object vtable pointers
    uc.mem_write(OBJ + 0x00, struct.pack("<I", vtable_for(OBJ)))
    uc.mem_write(OBJ + 0xd8, struct.pack("<I", DRAWCTX))
    uc.mem_write(OBJ + 0xdc, struct.pack("<I", BUF))
    uc.mem_write(OBJ + 0x68, struct.pack("<I", DST))
    buf_index = {DRAWCTX: 0, BUF: 1, DST: 2}
    for b in (DRAWCTX, BUF, DST):
        uc.mem_write(b + 0x00, struct.pack("<I", vtable_for(b)))
        # fill 64 vtable slots with compact unique stub addresses:
        #   stub = STUBS + idx*0x400 + slot*8   (fits in 3*0x400 = 0xC00)
        for k in range(64):
            stub = STUBS + buf_index[b] * 0x400 + k * 8
            uc.mem_write(vtable_for(b) + k * 4, struct.pack("<I", stub))

    def stub_dispatch(uc, address, size, user):
        # address is inside STUBS -> decode (which buffer idx, slot)
        tag = (address - STUBS) // 0x400          # 0=DRAWCTX 1=BUF 2=DST
        slot = ((address - STUBS) % 0x400) // 8
        esp = uc.reg_read(UC_X86_REG_ESP)
        ret = struct.unpack("<I", uc.mem_read(esp, 4))[0]
        # figure out arg count to clean by which method (thiscall = callee cleans)
        # buffer: QueryInterface(0) 2 args; Release(2) 0; Width(9)/Height(10) 0;
        #   Lock(6)/Unlock(7) 1; GetBufferArea(12) is a 0-arg GETTER returning a
        #   rect ptr; [0x48] 2 args; Blt(29) 4 args.
        argcnt = {0:2, 6:1, 7:1, 9:0, 10:0, 12:0, 18:2, 29:4}.get(slot, 0)
        eax = 1
        if slot == 0:  # QueryInterface(IID, &out): FAIL the hardware-blit IID so
            iid = struct.unpack("<I", uc.mem_read(esp + 4, 4))[0]   # the tiler falls into its software (per-tile Blt) path
            eax = 0 if iid == IID_HW else 1
        if slot == 9:  eax = BUF_W
        if slot == 10: eax = BUF_H
        if slot == 12: # bounds getter -> return ptr to a (0,0,W,H) rect
            uc.mem_write(SCRATCH, struct.pack("<4i", 0, 0, BUF_W, BUF_H))
            eax = SCRATCH
        if slot == 29: # Blt(srcSurface, srcRect, dstRect, flags) - CAPTURE
            a = [struct.unpack("<I", uc.mem_read(esp + 4 + 4*i, 4))[0] for i in range(4)]
            if in_tiler:
                which = "spine-tile"
            elif tag == 2:
                which = "screen-composite"
            else:
                which = "buffer-blit"
            captured.append((which, [rect_at(uc, a[1]), rect_at(uc, a[2]), a[0], a[3]]))
        uc.reg_write(UC_X86_REG_EAX, eax)
        uc.reg_write(UC_X86_REG_ESP, esp + 4 + argcnt * 4)   # pop ret + args
        uc.reg_write(UC_X86_REG_EIP, ret)

    uc.hook_add(UC_HOOK_CODE, stub_dispatch, begin=STUBS, end=STUBS + 0x10000)

    # direct calls: factory (return 0) + arc helper (capture its rect arg)
    def at_factory(uc, address, size, user):
        esp = uc.reg_read(UC_X86_REG_ESP)
        ret = struct.unpack("<I", uc.mem_read(esp, 4))[0]
        uc.reg_write(UC_X86_REG_EAX, 0)          # ebp=0 -> skip buffer-release path
        uc.reg_write(UC_X86_REG_ESP, esp + 4)
        uc.reg_write(UC_X86_REG_EIP, ret)
    uc.hook_add(UC_HOOK_CODE, at_factory, begin=FACTORY, end=FACTORY)

    # Tiler watcher: fires at the tiler's entry + every ret. Unlike the old
    # stub, it does NOT alter EIP -> the REAL tiler executes, so we see the
    # actual per-tile Blt fan-out (labelled "spine-tile" by stub_dispatch).
    def tiler_watch(uc, address, size, user):
        global in_tiler, tiler_info
        if address == TILER:
            esp = uc.reg_read(UC_X86_REG_ESP)
            a = [struct.unpack("<I", uc.mem_read(esp + 4 + 4*i, 4))[0] for i in range(7)]
            in_tiler = True
            # a3 = the repeating TILE (modulo divisors); a4 = the DEST fill region
            tile = rect_at(uc, a[2]); dest = rect_at(uc, a[3])
            tiler_info = (tile, dest)
            captured.append(("SPINE-CALL", [tile, dest, a[0], a[3]]))
        elif address in TILER_RETS:
            in_tiler = False
    uc.hook_add(UC_HOOK_CODE, tiler_watch, begin=TILER, end=TILER_RETS[-1])

    # set up the call: push a sentinel return address, ecx=this, eip=Plot
    SENTINEL = 0xDEADBEEF
    sp = STACK + STACK_SZ - 0x400
    sp -= 4; uc.mem_write(sp, struct.pack("<I", SENTINEL))
    uc.reg_write(UC_X86_REG_ESP, sp)
    uc.reg_write(UC_X86_REG_ECX, OBJ)

    try:
        uc.emu_start(PLOT, SENTINEL, count=3000000)
    except UcError as e:
        print("emu stopped:", e, "eip=0x%08X" % uc.reg_read(UC_X86_REG_EIP))

    print("=== fields ===")
    for k in (0xe0,0xe4,0xe8,0xec,0xf0,0xf4,0x100):
        print("  0x%03X = %d" % (k, fields[k]))
    W = fields[0xb0]-fields[0xa8]; H = fields[0xb4]-fields[0xac]
    print("  window %dx%d  buffer %dx%d" % (W, H, BUF_W, BUF_H))
    print("=== captured draw ops ===")
    tiles = 0
    for label, info in captured:
        if label == "spine-tile":
            tiles += 1
            if tiles <= 4 or tiles % 25 == 0:   # sample the tile fan-out
                print("  %-16s[%d] srcRect=%s dstRect=%s" % (label, tiles, info[0], info[1]))
        else:
            print("  %-16s srcRect=%s dstRect=%s (a=0x%X,0x%X)" %
                  (label, info[0], info[1], info[2], info[3]))
    if tiles:
        print("  --> spine drawn as %d tile-Blts (TILING, not stretch)" % tiles)

    # render the dst rects as a labelled, FILLED diagram so we can SEE the
    # layout (element position + size) and compare against the game.
    if any(a.startswith("--png") for a in sys.argv):
        from PIL import Image, ImageDraw
        COL = {"buffer-blit": (230,150,40), "spine-tile": (235,120,25),
               "screen-composite": (70,70,90), "SPINE-CALL": None}
        # auto-fit: scale the whole layout (window WxH) into a fixed canvas so
        # both 282x678 and 564x1356 render comparably.
        winW = fields[0xb0]-fields[0xa8]; winH = fields[0xb4]-fields[0xac]
        CW, CH = 300, 680
        s = min(CW / max(winW,1), CH / max(winH,1))
        img = Image.new("RGB", (int(winW*s)+2, int(winH*s)+22), (36,40,56))
        dr = ImageDraw.Draw(img)
        def S(v): return int(v*s)
        dr.rectangle([0,0,S(winW)+1,S(winH)+1], outline=(80,86,110))
        ti = 0
        for label, info in captured:
            dst = info[1]
            col = COL.get(label, (200,200,200))
            if not dst or col is None:
                continue
            x0,y0,x1,y1 = dst
            r = [S(x0),S(y0),S(x1),S(y1)]
            if label == "spine-tile":
                ti += 1
                # --seams: alternate shade to COUNT/see tiles (a debug view).
                # default: every tile is the SAME source rect -> one solid color,
                # which is what actually reaches the screen.
                if "--seams" in sys.argv:
                    col = (235,120,25) if ti % 2 else (255,165,60)
                    dr.rectangle(r, fill=col, outline=(120,60,10))
                else:
                    dr.rectangle(r, fill=(235,140,35))   # solid, as in-game
            else:
                dr.rectangle(r, fill=col, outline=(255,255,255))
                dr.text((r[0]+3, r[1]+3), "%s\n%dx%d" % (label, x1-x0, y1-y0), fill=(0,0,0))
        # BUFFER-BOUNDS overlay (the composite/clip step the sim used to ignore):
        # the on-screen flyout only shows draws INSIDE the physical buffer
        # (BUF_W x BUF_H). Draw a red dashed line at that edge. This is the whole
        # story of the ring vs bar: the RING (x0-94) sits LEFT of the line at every
        # buffer size, so growing the buffer never changes it; the BAR (x229-282)
        # sits RIGHT of the 141 line, so it only appears once the buffer >= 229.
        if BUF_W < winW:
            bx = S(BUF_W)
            for yy in range(0, S(winH), 10):
                dr.line([bx, yy, bx, yy + 5], fill=(255, 60, 60), width=2)
            dr.text((max(bx - 46, 2), 3), "buf=%d" % BUF_W, fill=(255, 90, 90))
        # OPTIONAL overlay: the disaster PICTURE thumbnails are painted by a
        # SEPARATE control (strip Plot 0x0079AA70), so they never appear in this
        # container run. Draw a labelled placeholder at its captured geometry
        # (88x578 at rel X184 in the 282-wide container) so the diagram shows the
        # WHOLE flyout. Scales with the window so 1x/2x both look right.
        if "--strip" in sys.argv:
            sx = winW/282.0; sy = winH/678.0
            r = [S(184*sx), S(50*sy), S(272*sx), S(628*sy)]
            dr.rectangle(r, fill=(40,150,150), outline=(255,255,255))
            dr.text((r[0]+3, r[1]+3), "pictures\n(strip)\n%dx%d"
                    % (int(88*sx), int(578*sy)), fill=(0,0,0))
        title = "unknown"
        for a in sys.argv:
            if a.startswith("--title="): title = a.split("=",1)[1]
        dr.text((4, S(winH)+6), "win %dx%d buf %dx%d | %d tiles | %s"
                % (winW, winH, BUF_W, BUF_H, ti, title), fill=(200,200,210))
        out = "layout.png"
        for a in sys.argv:
            if a.startswith("--png="): out = a.split("=",1)[1]
        img.save(out)
        print("wrote", out)

if __name__ == "__main__":
    main()
