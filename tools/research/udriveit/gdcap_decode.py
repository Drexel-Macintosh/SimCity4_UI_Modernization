#!/usr/bin/env python3
r"""Decode a gdcap.cpp capture and rank the candidates for #188's balloon.

    python gdcap_decode.py gdcap.bin                      # census + top quads
    python gdcap_decode.py gdcap.bin --caller 0x6A9139    # one drawer's draws
    python gdcap_decode.py gdcap.bin --near X Y Z --r 40  # world-space match

WHAT THIS IS FOR
The probe logs, for every primitive SC4 submitted in the captured frames, the
RETURN ADDRESS of the code that submitted it. That address is the drawer. It
cannot be a misleading name, because it is not a name - it is the instruction
after the call.

BALLOON SIGNATURE (derived from the DrawArrays jump table at 0x008859DC and
the gdPrimType->D3DPRIMITIVETYPE map at 0x00AC44CC, see gdcap.cpp header):
    prim == 6 (GL_QUADS) and verts == 4  =>  exactly one textured quad.
A billboard that is NOT batched looks like nothing else in the log.

READING THE CENSUS FIRST IS NOT OPTIONAL. `total driver calls` is the positive
control: a capture with 0 calls proves nothing about the balloon, it only
proves the hook never ran.
"""
import argparse
import struct
import collections

REC = struct.Struct("<IIIHHIIII" + "6f" + "3f")   # 64 bytes
assert REC.size == 64, REC.size

PRIM = {0: "TRIANGLES", 1: "TRI_STRIP", 2: "TRI_FAN", 3: "POINTS",
        4: "LINES", 5: "LINE_STRIP", 6: "QUADS", 7: "QUAD_STRIP"}


def load(path):
    d = open(path, "rb").read()
    magic, ver, n, calls = struct.unpack_from("<IIII", d, 0)
    if magic != 0x50414347:
        raise SystemExit("not a gdcap capture (bad magic %#x)" % magic)
    recs = []
    off = 16
    for _ in range(n):
        f = REC.unpack_from(d, off)
        off += REC.size
        recs.append(dict(
            frame=f[0], seq=f[1], caller=f[2], prim=f[3], verts=f[4],
            fmt=f[5], stride=f[6], tex0=f[7], tex1=f[8],
            bb=f[9:15], v0=f[15:18]))
    return recs, ver, calls


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("bin")
    ap.add_argument("--caller", help="show only this return address")
    ap.add_argument("--near", nargs=3, type=float, metavar=("X", "Y", "Z"))
    ap.add_argument("--r", type=float, default=32.0)
    ap.add_argument("--top", type=int, default=40)
    a = ap.parse_args()

    recs, ver, calls = load(a.bin)
    print("capture v%d: %d records, %d total driver calls (POSITIVE CONTROL)"
          % (ver, len(recs), calls))
    if calls == 0:
        print("!! 0 driver calls: the hook never ran. Nothing here is evidence.")
        return
    frames = len(set(r["frame"] for r in recs))
    print("   frames: %d   calls/frame: %.0f" % (frames, calls / max(frames, 1)))

    by_prim = collections.Counter(r["prim"] for r in recs)
    print("   by primitive:", {PRIM.get(k, k): v for k, v in sorted(by_prim.items())})

    if a.caller:
        want = int(a.caller, 0)
        recs = [r for r in recs if r["caller"] == want]
        print("   filtered to caller %#010x: %d records" % (want, len(recs)))

    if a.near:
        cx, cy, cz = a.near
        def hit(r):
            b = r["bb"]
            return (b[0] - a.r <= cx <= b[3] + a.r and
                    b[1] - a.r <= cy <= b[4] + a.r and
                    b[2] - a.r <= cz <= b[5] + a.r)
        recs = [r for r in recs if hit(r)]
        print("   filtered to bbox within %g of (%g,%g,%g): %d records"
              % (a.r, cx, cy, cz, len(recs)))

    # The prize: single quads, grouped by drawer.
    quads = [r for r in recs if r["prim"] == 6 and r["verts"] == 4]
    print("\nSINGLE QUADS (prim=QUADS, verts=4): %d" % len(quads))
    grp = collections.Counter(r["caller"] for r in quads)
    print("  drawers, most-drawn first  ->  feed each VA to disasm_at.py")
    for caller, n in grp.most_common(a.top):
        ex = next(r for r in quads if r["caller"] == caller)
        b = ex["bb"]
        print("   %#010x  x%-5d tex0=%#010x fmt=%#x stride=%d"
              % (caller, n, ex["tex0"], ex["fmt"], ex["stride"]))
        print("               bbox (%.1f,%.1f,%.1f)-(%.1f,%.1f,%.1f)  size %.2f x %.2f x %.2f"
              % (b[0], b[1], b[2], b[3], b[4], b[5],
                 b[3] - b[0], b[4] - b[1], b[5] - b[2]))

    # Everything else, by drawer, so a batched balloon still names its batcher.
    print("\nALL DRAWERS (any primitive):")
    allg = collections.Counter(r["caller"] for r in recs)
    for caller, n in allg.most_common(a.top):
        print("   %#010x  x%d" % (caller, n))


if __name__ == "__main__":
    main()
