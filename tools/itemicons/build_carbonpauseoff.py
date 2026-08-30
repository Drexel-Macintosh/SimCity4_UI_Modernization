#!/usr/bin/env python3
r"""Build z_SC4UIScale_ZCarbonPauseOff - the package that stops US repainting
the yellow pause border over a remover the player installed on purpose.

THE DEFECT THIS CURES
    z_SC4UIScale_ZCarbonArt carries a 240x240 SOLID GOLD copy of the pause
    border {856DDBAC, 46A006B0, 14315E61} - our upscale of Scoty's own re-skin
    from scoty_carbon_PNG.dat, so the art itself is legitimate. But
    zzz-SC4UIScale\ outranks every mod folder, so with the Carbon Skin
    installed our copy beats ANY pause remover and the border comes back.

    MEASURED 2026-08-30 across all 25 Carbon dats: this TGI appears in exactly
    two of them - scoty_carbon_PNG.dat (the gold re-skin) and
    y_scoty_Carbon_Yellow-pause-remover.dat. SCOTY SHIPS HIS OWN REMOVER. So
    this was never "our override versus some third-party mod": it is our copy
    of Scoty's art defeating Scoty's own remover, with the player's choice
    between the two being the thing overridden.

WHY A SECOND PACKAGE AND NOT AN EDIT TO ZCarbonArt
    Dropping the TGI from ZCarbonArt would cost the players who WANT the
    border its 2x sharpness - the gold art is correct for them. What is wrong
    is only that we win when they have asked for it to be gone. So the border
    stays in ZCarbonArt, and this package - which sorts AFTER it ('P' > 'A') -
    lays a FULLY TRANSPARENT sheet over the top, armed ONLY when a remover is
    actually installed. Both player choices are then served, and neither is
    decided by us.

    Additive by construction: it changes no existing package, no enrollment,
    and no builder. The whole cure is one transparent PNG and an arming
    condition.

WHY TRANSPARENT AND NOT ABSENT
    The drawer nine-slices this sheet (cell = img/3) into the full view rect;
    no geometry is derived from the art. A fully transparent sheet therefore
    draws nothing at all, which is exactly what both removers do - SMP's is
    120x120 with all 14,400 pixels at alpha 0, measured.

Run from tools\itemicons.
"""
import os
import struct
import subprocess
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
PACKER = os.path.join(HERE, "..", "dbpf", "DbpfPack.exe")
OUT = os.path.join(HERE, "out")
# Stock is 120x120; our carbon copy is that x f. Matched per tier purely so a
# reader comparing the two packages sees the same dimensions - a transparent
# sheet would draw nothing at any size.
TIERS = [("15x", 180), ("2x", 240), ("3x", 360)]
NAME = "T-0x856DDBAC_G-0x46A006B0_I-0x14315E61.png"


def transparent_png(side):
    """A side x side RGBA PNG, every pixel (255,255,255,0). Written by hand so
    the build needs no image library and the bytes are auditable."""
    def chunk(tag, data):
        c = tag + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c))

    ihdr = struct.pack(">IIBBBBB", side, side, 8, 6, 0, 0, 0)   # 8-bit RGBA
    row = b"\x00" + b"\xff\xff\xff\x00" * side                  # filter 0 + pixels
    idat = zlib.compress(row * side, 9)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", idat) + chunk(b"IEND", b""))


def main():
    os.makedirs(OUT, exist_ok=True)
    for tag, side in TIERS:
        work = os.path.join(HERE, "carbonpauseoff-%s" % tag)
        os.makedirs(work, exist_ok=True)
        for f in os.listdir(work):
            os.remove(os.path.join(work, f))

        blob = transparent_png(side)
        with open(os.path.join(work, NAME), "wb") as f:
            f.write(blob)

        # POSITIVE CONTROL, in the builder rather than in a comment: read the
        # bytes back and assert the sheet really is fully transparent. A cure
        # that silently emitted an opaque sheet would REPAINT the border it
        # exists to suppress - the exact defect, inverted.
        with open(os.path.join(work, NAME), "rb") as f:
            back = f.read()
        assert back[:8] == b"\x89PNG\r\n\x1a\n", "not a PNG"
        w, h = struct.unpack(">II", back[16:24])
        assert (w, h) == (side, side), "wrong dimensions %dx%d" % (w, h)
        raw = zlib.decompress(back[back.index(b"IDAT") + 4:][:-12])
        # Each scanline is 1 filter byte + side*4 pixel bytes, so the alpha of
        # pixel p on row r sits at r*stride + 1 + p*4 + 3. Indexing the stream
        # as a flat RGBA array skips that filter byte and reads colour bytes as
        # alpha - which is exactly what the first version of this check did,
        # and it reported {0,255} on a sheet that is in fact fully transparent.
        stride = 1 + side * 4
        assert len(raw) == stride * side, "unexpected raw size %d" % len(raw)
        alphas = {raw[r * stride + 1 + p * 4 + 3]
                  for r in range(side) for p in range(side)}
        assert alphas == {0}, "NOT fully transparent: alphas %s" % sorted(alphas)
        filters = {raw[r * stride] for r in range(side)}
        assert filters == {0}, "unexpected PNG row filters %s" % sorted(filters)

        dat = os.path.join(OUT, "z_SC4UIScale_ZCarbonPauseOff-%s.dat" % tag)
        r = subprocess.run([PACKER, work, dat], capture_output=True, text=True)
        if r.returncode != 0:
            sys.exit("PACK FAILED %s:\n%s" % (tag, r.stderr or r.stdout))
        print("x%-4s %dx%d fully transparent (verified) -> %s (%.1f KB)"
              % (tag, side, side, os.path.basename(dat),
                 os.path.getsize(dat) / 1e3))
    return 0


if __name__ == "__main__":
    sys.exit(main())
