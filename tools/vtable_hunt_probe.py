#!/usr/bin/env python3
"""Which class owns the #109 fault chain? Find the VAs in vtables.

If a function's VA appears as a dword in .rdata/.data, that is (almost always)
a vtable slot, and the neighbouring slots identify the class by shape.

POSITIVE CONTROL BUILT IN: cSC4WinMiniMap's draw override 0x007A79B0 is KNOWN
to sit in a window vtable at +0x160. If this probe cannot find that, it cannot
find anything and every null below is meaningless.
"""
import sys, struct, os

EXE = r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Apps\SimCity 4.exe"
IMAGE_BASE = 0x400000

CHAIN = {
    0x00910003: "memset32",
    0x0079ED90: "rowfill",
    0x007A2380: "mid",
    0x007A2740: "top",
    0x007A79B0: "cSC4WinMiniMap::Draw  <-- POSITIVE CONTROL",
    0x007A7840: "cSC4WinMiniMap::Recompute",
    0x007A7FF0: "cSC4WinMiniMap::Bake",
    0x007A04F0: "DataViews legend re-lay",
}


def load():
    data = open(EXE, "rb").read()
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    nsec = struct.unpack_from("<H", data, pe + 6)[0]
    opt = struct.unpack_from("<H", data, pe + 20)[0]
    secs, off = [], pe + 24 + opt
    for _ in range(nsec):
        n = data[off:off+8].rstrip(b"\0").decode("latin1")
        vsize, va, rsize, roff = struct.unpack_from("<IIII", data, off + 8)
        secs.append((n, va, vsize, roff, rsize))
        off += 40
    return data, secs


def main():
    data, secs = load()
    print("sections:", ", ".join(f"{n}@{IMAGE_BASE+va:#x}" for n, va, *_ in secs), "\n")

    # index every dword in every section that is a plausible code VA
    hits = {va: [] for va in CHAIN}
    for n, sva, vsize, roff, rsize in secs:
        base = IMAGE_BASE + sva
        blob = data[roff:roff+rsize]
        for i in range(0, len(blob) - 4, 4):
            v = struct.unpack_from("<I", blob, i)[0]
            if v in hits:
                hits[v].append((n, base + i))

    ctrl_ok = False
    for va, name in CHAIN.items():
        h = hits[va]
        print(f"{va:#010x}  {name}")
        if not h:
            print("    no dword reference found (reached only by direct call)")
        for sec, at in h[:6]:
            print(f"    referenced at {at:#010x} in {sec}")
            if "CONTROL" in name:
                ctrl_ok = True
            # dump neighbouring slots to fingerprint the vtable
            o = None
            for n2, sva2, vs2, ro2, rs2 in secs:
                if n2 == sec:
                    o = ro2 + (at - (IMAGE_BASE + sva2))
            if o is not None:
                lo = max(0, o - 16)
                ctx = struct.unpack_from("<8I", data, lo)
                idx0 = (lo - o) // 4
                print("        neighbours: " + " ".join(
                    (f"[{idx0+k:+d}]{v:08x}" + ("*" if v == va else ""))
                    for k, v in enumerate(ctx)))
        print()

    print("=" * 70)
    if ctrl_ok:
        print("POSITIVE CONTROL PASSED: the known vtable entry 0x007A79B0 was found,")
        print("so a 'no dword reference' above is a real measurement, not blindness.")
    else:
        print("*** POSITIVE CONTROL FAILED *** - probe could not find the KNOWN")
        print("vtable entry 0x007A79B0. Every null above is worthless. Do not use.")
        return 3

    # The +0x94C question: 0x007A2740 reads [ebx+0x94c]. cSC4WinMiniMap's known
    # fields stop near +0x120, so a +0x94C would rule it out as `this`.
    print()
    print("=" * 70)
    print("THE +0x94C TEST")
    print("cSC4WinMiniMap known fields: blitSize +0xE4, surface +0xF0, zoom +0x104,")
    print("raster +0x114/+0x118/+0x11C, dirty mask +0x120  -> object ends ~+0x130.")
    print("0x007A2740 reads [ebx+0x94C] = offset 2380 decimal, ~18x past that.")
    print("=> INFERENCE (strong): `this` at 0x007A2740 is NOT a cSC4WinMiniMap.")
    print("   Confirm by finding the ctor/size for whatever class owns it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
