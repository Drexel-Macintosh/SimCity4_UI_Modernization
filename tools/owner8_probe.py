#!/usr/bin/env python3
"""Owner probe #8: final cross-checks.
 1. window-vtable fingerprint on all 5 vtables in play
 2. containing-function of every caller of 0x7A2380 (is the chain closed?)
 3. simulate 0x0079ED90's halving loop -> which (terrainDim, windowPx) survive
Read-only."""
import struct, bisect
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

EXE = r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Apps\SimCity 4.exe"
IB = 0x400000


def load():
    data = open(EXE, "rb").read()
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    nsec = struct.unpack_from("<H", data, pe + 6)[0]
    opt = struct.unpack_from("<H", data, pe + 20)[0]
    secs = []; off = pe + 24 + opt
    for i in range(nsec):
        n = data[off:off+8].rstrip(b"\0").decode("latin1")
        vsize, va, rsize, roff = struct.unpack_from("<IIII", data, off + 8)
        secs.append((n, va, vsize, roff, rsize)); off += 40
    return data, secs


DATA, SECS = load()


def rng(name):
    for n, sva, vsize, roff, rsize in SECS:
        if n.startswith(name):
            return IB + sva, roff, min(vsize, rsize)


TVA, TOFF, TSZ = rng(".text")
RVA, ROFF, RSZ = rng(".rdata")
TEXT = DATA[TOFF:TOFF+TSZ]


def va2off(va):
    rva = va - IB
    for n, sva, vsize, roff, rsize in SECS:
        if sva <= rva < sva + max(vsize, rsize):
            return roff + (rva - sva)
    return None


def dw(va):
    o = va2off(va)
    return struct.unpack_from("<I", DATA, o)[0] if o is not None else None


print("=" * 74)
print("1. WINDOW-VTABLE FINGERPRINT  [vt + 87*4] == 0x0099BE4C")
print("   (our own prior note; used here as the class-kind test)")
print("=" * 74)
for b, what in ((0x00AB7E60, "cSC4WinMapView vptr @ this+0xE0"),
                (0x00AB8150, "cSC4WinMapView vptr @ this+0x00"),
                (0x00AB8140, "cSC4WinMapView vptr @ this+0x04"),
                (0x00AB7EE0, "cSC4WinMapView vptr @ this+0x08"),
                (0x00AB83B8, "cSC4WinMiniMap  (POSITIVE CONTROL)")):
    v = dw(b + 87*4)
    print(f"  {b:08X} {what:<38} [+0x15C] = {v:08X}   "
          f"{'IS-A-WINDOW' if v == 0x0099BE4C else 'not a window vtable'}")
print(f"\n  minimap draw slot check: [0x00AB83B8+0x160] = {dw(0x00AB83B8+0x160):08X} "
      f"(expect 007A79B0)")
print(f"  mapview  draw slot check: [0x00AB7E60+0x160] = {dw(0x00AB7E60+0x160):08X}")

# ---------------------------------------------------------------- 2
ct, jt = {}, {}
for i in range(len(TEXT) - 5):
    b = TEXT[i]
    if b in (0xE8, 0xE9):
        rel = struct.unpack_from("<i", TEXT, i + 1)[0]
        s = TVA + i; t = s + 5 + rel
        if TVA <= t < TVA + TSZ:
            (ct if b == 0xE8 else jt).setdefault(t, []).append(s)
vt = {}
for i in range(0, RSZ - 4, 4):
    d = struct.unpack_from("<I", DATA, ROFF + i)[0]
    if TVA <= d < TVA + TSZ:
        vt.setdefault(d, []).append(RVA + i)
STARTS = sorted(set(ct) | set(vt))


def containing(va):
    i = bisect.bisect_right(STARTS, va) - 1
    return STARTS[i] if i >= 0 else None


print("\n" + "=" * 74)
print("2. IS THE CHAIN CLOSED?  containing-fn of every caller of 0x7A2380")
print("=" * 74)
from collections import Counter
c = Counter(containing(s) for s in ct[0x007A2380])
for f, n in sorted(c.items()):
    print(f"  {n:2} call site(s) inside fn {f:08X}")
print("  callers of 0x7A2740:", [hex(x) for x in ct[0x007A2740]],
      "-> fn", hex(containing(ct[0x007A2740][0])))
print("  callers of 0x79ED90:", [hex(x) for x in ct[0x0079ED90]],
      "-> fn", hex(containing(ct[0x0079ED90][0])))
print("  callers of 0x7A2F60:", [hex(x) for x in ct[0x007A2F60]])
print("  0x007A2F60 in a vtable? ", vt.get(0x007A2F60, "NO"))
print("  0x007A2740 in a vtable? ", vt.get(0x007A2740, "NO"))
print("  0x007A2380 in a vtable? ", vt.get(0x007A2380, "NO"))
print("  0x0079ED90 in a vtable? ", vt.get(0x0079ED90, "NO"))
print("  POSITIVE CONTROL 0x007A79B0 in a vtable?",
      [hex(x) for x in vt.get(0x007A79B0, [])])

# ---------------------------------------------------------------- 3
print("\n" + "=" * 74)
print("3. EXACT SIMULATION OF 0x0079ED90's MULTIPLIER LOOP")
print("   src=terrain dim (a2/a3); dest=buffer extent (a5/a6)")
print("     mul=1; while dest>src: dest>>=1; mul<<=1")
print("   the blit then writes src*mul pixels across a dest-wide buffer")
print("=" * 74)


def mul_for(dest, src):
    m, d = 1, dest
    while d > src:
        d >>= 1
        m <<= 1
    return m


print(f"  {'terrain':>8} {'window':>7} {'mul':>5} {'written':>8} {'buffer':>7}  verdict")
for src in (64, 128, 256):
    for dest in (256, 384, 512, 640, 768, 1024, 1536, 2048):
        m = mul_for(dest, src)
        w = src * m
        ok = (w == dest)
        print(f"  {src:8} {dest:7} {m:5} {w:8} {dest:7}  "
              f"{'SAFE' if ok else 'OVERRUN by %d px/row' % (w - dest)}")
    print()

print("  Crash-report cross-check: ECX (rep stosd count) == 0x10 == 16.")
for src in (64, 128, 256):
    for dest in range(64, 4097):
        if mul_for(dest, src) == 16:
            lo, hi = dest, dest
            break
    hits = [d for d in (256, 384, 512, 640, 768, 1024) if mul_for(d, src) == 16]
    print(f"    terrain {src:3}: mul==16 for window in "
          f"({src*8}, {src*16}]  -> of our tiers: {hits}")

print("\n  Which windows are SAFE, per terrain dim (window == src*2^k):")
for src in (64, 128, 256):
    print(f"    terrain {src:3}: " +
          ", ".join(str(src << k) for k in range(0, 6)))
