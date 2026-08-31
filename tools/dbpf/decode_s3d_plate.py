#!/usr/bin/env python3
r"""Extract + QFS-decompress + hand-decode the ConnectArrow S3D plate.

Written for register #28 ("The S3D format (no reader/writer exists)").
Target: SimCity_1.dat, T=0x5AD0E817 G=0xBADB57F1 I=0x29F10000 (the 244-byte
"arrow plate" cited in tools\research\overlays\row-15-neighbor-connection-arrows.md
and research\UNKNOWNS-AND-NEXT-TARGETS.md row 28). This is the S3D model bound
by the `UI8x1x3_ConnectArrow_29F1` exemplar's RKT property 0x27812821 -- the
neighbor-connection arrow at city edges, NOT the Move-In-a-Sim marker (that
marker is a GZWinBMP-drawn 2D bitmap, closed #191, register row ~20 -- it does
not use this or any S3D).

The 244 bytes the DBPF index reports is the ON-DISK COMPRESSED size. This
resource IS listed in the archive's compression directory (DIR, type
0xE86B1EEF) with declared uncompressed size 336 -- confirmed independently by
the QFS/RefPack header's own embedded 3-byte big-endian size field (also 336,
0x000150). The QfsDecompress algorithm here is a direct Python port of the one
already in tools\dbpf\DbpfExtract.cs (same repo, same header layout: u32 LE
compressed size, 0x10 0xFB signature, 3-byte BE decompressed size, then
codes).

Read-only. Writes only under tools\dbpf\extracted-s3d\ (this directory), never
to the game install.

    python decode_s3d_plate.py
    SC4_GAME_DIR=... python decode_s3d_plate.py      (non-default install)
"""

import os
import struct
import sys

GAME = os.environ.get(
    "SC4_GAME_DIR",
    r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe")

TARGET_T = 0x5AD0E817
TARGET_G = 0xBADB57F1
TARGET_I = 0x29F10000
ARCHIVE = "SimCity_1.dat"

OUT_DIR = os.path.join(os.path.dirname(__file__), "extracted-s3d")


def read_index(path):
    with open(path, "rb") as f:
        hdr = f.read(96)
        if hdr[:4] != b"DBPF":
            raise SystemExit("%s: not DBPF" % path)
        count, idx_off, idx_size = struct.unpack_from("<III", hdr, 0x24)
        f.seek(idx_off)
        blob = f.read(idx_size)
    stride = 20
    for k in range(count):
        yield struct.unpack_from("<IIIII", blob, k * stride)


def find_dir_uncompressed_size(path, t, g, i):
    """Look up (t,g,i) in the type-0xE86B1EEF compression directory, if any."""
    for (dt, dg, di, doff, dsize) in read_index(path):
        if dt == 0xE86B1EEF:
            with open(path, "rb") as f:
                f.seek(doff)
                blob = f.read(dsize)
            # ⛔ DIR RECORDS ARE 16 BYTES, NOT 12. This loop used to step by
            # 12 while unpacking 16 ("<IIII"), so every record overlapped the
            # next by four bytes and the walk was reading garbage that happened
            # to contain the right answer at one misaligned offset.
            #
            # MEASURED on retail SimCity_1.dat: the DIR record is 782,080 bytes.
            # 782080 % 12 = 4, so twelve does not even divide it - the old loop
            # could never have consumed the record cleanly. At 16 it yields
            # 48,880 records and EVERY ONE names a TGI that exists in the
            # archive index (0 failures). That is the positive control: the
            # right stride makes every record resolve; a wrong one cannot.
            assert dsize % 16 == 0, (
                "DIR size %d is not a multiple of 16 - the record layout is "
                "not what this reader assumes; refusing rather than guessing"
                % dsize)
            for k in range(dsize // 16):
                et, eg, ei, esize = struct.unpack_from("<IIII", blob, k * 16)
                if (et, eg, ei) == (t, g, i):
                    return esize
            return None
    return None


def qfs_decompress(src):
    """EA RefPack/QFS. Body: u32 LE compressed size, 0x10 0xFB, 3-byte BE
    uncompressed size, then control codes. Direct port of
    tools\\dbpf\\DbpfExtract.cs QfsDecompress."""
    if len(src) >= 9 and src[4] == 0x10 and src[5] == 0xFB:
        pos = 4
    elif len(src) >= 5 and src[0] == 0x10 and src[1] == 0xFB:
        pos = 0
    else:
        raise ValueError("no QFS 0x10FB signature")
    pos += 2
    out_len = (src[pos] << 16) | (src[pos + 1] << 8) | src[pos + 2]
    pos += 3
    dst = bytearray(out_len)
    out_pos = 0
    while pos < len(src) and out_pos < out_len:
        c0 = src[pos]; pos += 1
        if c0 < 0x80:
            c1 = src[pos]; pos += 1
            num_plain = c0 & 0x03
            num_copy = ((c0 & 0x1C) >> 2) + 3
            copy_off = ((c0 & 0x60) << 3) + c1 + 1
        elif c0 < 0xC0:
            c1 = src[pos]; pos += 1
            c2 = src[pos]; pos += 1
            num_plain = (c1 & 0xC0) >> 6
            num_copy = (c0 & 0x3F) + 4
            copy_off = ((c1 & 0x3F) << 8) + c2 + 1
        elif c0 < 0xE0:
            c1 = src[pos]; pos += 1
            c2 = src[pos]; pos += 1
            c3 = src[pos]; pos += 1
            num_plain = c0 & 0x03
            num_copy = ((c0 & 0x0C) << 6) + c3 + 5
            copy_off = ((c0 & 0x10) << 12) + (c1 << 8) + c2 + 1
        elif c0 < 0xFC:
            num_plain = ((c0 & 0x1F) + 1) << 2
            num_copy = 0
            copy_off = 0
        else:
            num_plain = c0 & 0x03
            dst[out_pos:out_pos + num_plain] = src[pos:pos + num_plain]
            pos += num_plain
            out_pos += num_plain
            break
        dst[out_pos:out_pos + num_plain] = src[pos:pos + num_plain]
        pos += num_plain
        out_pos += num_plain
        frm = out_pos - copy_off
        if num_copy > 0 and frm < 0:
            raise ValueError("copy offset before start")
        for _ in range(num_copy):
            dst[out_pos] = dst[frm]
            out_pos += 1
            frm += 1
    if out_pos != out_len:
        raise ValueError("decompressed %d != expected %d" % (out_pos, out_len))
    return bytes(dst)


def hexdump(data, base=0):
    for i in range(0, len(data), 16):
        chunk = data[i:i + 16]
        hexs = " ".join("%02x" % b for b in chunk)
        asc = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        print("%4d  %-48s  %s" % (base + i, hexs, asc))


def decode_chunks(data):
    """Walk the tag(4 ASCII) + len(u32 LE, includes this 8-byte header)
    + body(len-8) chunk chain starting at offset 8 (after the 3DMD magic +
    its own unresolved 4-byte field). Prints each chunk's span; does not
    interpret body fields (see the write-up in
    tools\\research\\overlays\\row-15-neighbor-connection-arrows.md for the
    field-level decode, including the one anomalous chunk -- ANIM's declared
    length does not match its real span)."""
    print("magic:", data[0:4], "unresolved4 @4-7 (u32 LE):", struct.unpack_from("<I", data, 4)[0])
    pos = 8
    while pos < len(data):
        tag = data[pos:pos + 4]
        if len(tag) < 4 or not all(32 <= b < 127 for b in tag):
            print("stop at %d, remaining %d bytes: %s" % (pos, len(data) - pos, data[pos:].hex()))
            break
        ln = struct.unpack_from("<I", data, pos + 4)[0]
        body_start, body_end = pos + 8, pos + ln
        print("%-4s @%-4d declared_len=%-6d body=[%d:%d] (%d bytes)  hex=%s"
              % (tag.decode(), pos, ln, body_start, body_end, max(0, body_end - body_start),
                 data[body_start:min(body_end, len(data))].hex()))
        if body_end <= pos or body_end > len(data):
            print("  ANOMALY: declared length does not fit the remaining buffer -- "
                  "not following the tag+len(header-inclusive)+body convention here.")
            break
        pos = body_end


def main():
    path = os.path.join(GAME, ARCHIVE)
    if not os.path.isfile(path):
        raise SystemExit("missing %s -- set SC4_GAME_DIR to the install root" % path)

    target = None
    for (t, g, i, off, size) in read_index(path):
        if (t, g, i) == (TARGET_T, TARGET_G, TARGET_I):
            target = (off, size)
            break
    if target is None:
        raise SystemExit("TGI not found in %s" % ARCHIVE)
    off, size = target
    print("%s: T=0x%08X G=0x%08X I=0x%08X off=%d on-disk-size=%d"
          % (ARCHIVE, TARGET_T, TARGET_G, TARGET_I, off, size))

    dir_size = find_dir_uncompressed_size(path, TARGET_T, TARGET_G, TARGET_I)
    print("compression DIR uncompressed-size entry:", dir_size)

    with open(path, "rb") as f:
        f.seek(off)
        raw = f.read(size)

    decompressed = qfs_decompress(raw)
    print("QFS-decompressed length:", len(decompressed),
          "(matches DIR entry: %s)" % (len(decompressed) == dir_size))

    os.makedirs(OUT_DIR, exist_ok=True)
    base = "T-%08x_G-%08x_I-%08x" % (TARGET_T, TARGET_G, TARGET_I)
    raw_path = os.path.join(OUT_DIR, base + ".raw-qfs.bin")
    dec_path = os.path.join(OUT_DIR, base + ".decompressed.bin")
    with open(raw_path, "wb") as f:
        f.write(raw)
    with open(dec_path, "wb") as f:
        f.write(decompressed)
    print("saved", raw_path)
    print("saved", dec_path)

    print("\n--- decompressed hex ---")
    hexdump(decompressed)
    print("\n--- chunk walk ---")
    decode_chunks(decompressed)


if __name__ == "__main__":
    sys.exit(main())
