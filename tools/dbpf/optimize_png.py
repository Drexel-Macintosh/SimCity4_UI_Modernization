"""optimize_png.py - re-deflate staged PNGs at maximum compression.

WHY THIS EXISTS
    Every PNG we ship was written by the .NET System.Drawing encoder in
    tools\\upscale\\Upscale2x.cs, which deflates at FLEVEL=1 ("fast").  A
    census of the first IDAT's zlib header across all 1,019 shipped images
    found 100% at FLEVEL=1.  Re-deflating the SAME pixel bytes at level 9
    recovers ~11% of the art payload for zero visual change.

    The dats store entries UNCOMPRESSED by design (tools\\dbpf\\NOTES-PACK.md:
    the compression directory is absent and must stay absent), so a smaller
    PNG is a smaller dat, byte for byte.

WHY IT IS SAFE, BY CONSTRUCTION
    This tool never touches pixels.  It decompresses the IDAT stream,
    recompresses the IDENTICAL bytes, and then ASSERTS that the new file
    decompresses back to exactly the original bytes.  A mismatch aborts
    without writing.  Every other chunk (IHDR, sRGB, gAMA, pHYs, tRNS, PLTE)
    is copied through untouched - dropping gAMA/sRGB would change how the
    game renders the colours, which is a pixel change by another name.

    Pure standard library (zlib, struct, os, sys).  Nothing to pip install -
    that property is load-bearing for the generator we ship to users.

USAGE
    python optimize_png.py <dir> [<dir> ...]        # rewrite in place
    python optimize_png.py --dry-run <dir> ...      # report only
"""
import os
import sys
import zlib
import struct

PNG_SIG = b"\x89PNG\r\n\x1a\n"


def _chunks(buf):
    """Yield (type, data) for each chunk. Raises on a malformed file."""
    if not buf.startswith(PNG_SIG):
        raise ValueError("not a PNG")
    off = len(PNG_SIG)
    while off < len(buf):
        (ln,) = struct.unpack_from(">I", buf, off)
        ctype = buf[off + 4:off + 8]
        data = buf[off + 8:off + 8 + ln]
        if len(data) != ln:
            raise ValueError("truncated chunk %r" % ctype)
        yield ctype, data
        off += 12 + ln          # len + type + data + crc


def _chunk(ctype, data):
    return (struct.pack(">I", len(data)) + ctype + data
            + struct.pack(">I", zlib.crc32(ctype + data) & 0xFFFFFFFF))


def _best_deflate(raw):
    """Smallest level-9 stream across all three strategies. stdlib only."""
    best = None
    for strategy in (zlib.Z_DEFAULT_STRATEGY, zlib.Z_FILTERED, zlib.Z_RLE):
        co = zlib.compressobj(9, zlib.DEFLATED, 15, 9, strategy)
        out = co.compress(raw) + co.flush()
        if best is None or len(out) < len(best):
            best = out
    return best


def optimize(path, dry_run=False):
    """Returns (before, after). after == before when nothing was gained."""
    with open(path, "rb") as f:
        buf = f.read()
    before = len(buf)

    idat = b""
    others = []
    for ctype, data in _chunks(buf):
        if ctype == b"IDAT":
            idat += data
        elif ctype == b"IEND":
            pass
        else:
            others.append((ctype, data))

    raw = zlib.decompress(idat)
    packed = _best_deflate(raw)
    if len(packed) >= len(idat):
        return before, before          # already optimal, leave the file alone

    out = bytearray(PNG_SIG)
    for ctype, data in others:
        out += _chunk(ctype, data)
    out += _chunk(b"IDAT", packed)
    out += _chunk(b"IEND", b"")

    # THE ASSERTION. A pixel change here would be invisible until it shipped.
    check = b""
    for ctype, data in _chunks(bytes(out)):
        if ctype == b"IDAT":
            check += data
    if zlib.decompress(check) != raw:
        raise AssertionError("PIXELS CHANGED - refusing to write %s" % path)

    if not dry_run:
        with open(path, "wb") as f:
            f.write(out)
    return before, len(out)


def main(argv):
    dry = "--dry-run" in argv
    dirs = [a for a in argv[1:] if not a.startswith("--")]
    if not dirs:
        print(__doc__)
        return 2

    tot_before = tot_after = n = shrunk = 0
    failed = []
    for d in dirs:
        for root, _, files in os.walk(d):
            for fn in files:
                if not fn.lower().endswith(".png"):
                    continue
                p = os.path.join(root, fn)
                try:
                    b, a = optimize(p, dry)
                except Exception as e:                       # noqa: BLE001
                    failed.append((p, str(e)))
                    continue
                n += 1
                tot_before += b
                tot_after += a
                if a < b:
                    shrunk += 1

    saved = tot_before - tot_after
    pct = (100.0 * saved / tot_before) if tot_before else 0.0
    print("PNG re-deflate%s" % (" (DRY RUN)" if dry else ""))
    print("  files scanned : %d" % n)
    print("  files shrunk  : %d" % shrunk)
    print("  before        : %d bytes" % tot_before)
    print("  after         : %d bytes" % tot_after)
    print("  saved         : %d bytes (%.1f%%)" % (saved, pct))
    if failed:
        print("  FAILED        : %d" % len(failed))
        for p, e in failed[:10]:
            print("     %s: %s" % (p, e))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
