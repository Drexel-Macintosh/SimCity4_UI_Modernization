#!/usr/bin/env python3
r"""Extract + hand-decode the row-15 ConnectArrow EXEMPLAR, and locate the exact
byte offsets of the three OccupantSize (0x27812810) float32 values inside it.

Target (overlay census row 15, the neighbour-connection arrow plates at a city's
edge):
    EXEMPLAR  T=0x6534284A  G=0xC977C536  I=0x29F10000   in SimCity_1.dat

The S3D model it binds via RKT (0x27812821) is decoded separately by
tools\dbpf\decode_s3d_plate.py -- do not re-derive that here.

WHAT THIS PROVES (and what it does not)
---------------------------------------
This tool is READ-ONLY and makes exactly one structural claim: that the
exemplar's binary property table can be walked field-by-field, and that the
three OccupantSize floats occupy a fixed 12-byte span whose surrounding LENGTH
fields (record length, property count, per-property value count) are all
independent of the VALUES.  That is the precondition for a data-only override
that rewrites the numbers in place without resizing anything.

POSITIVE CONTROLS (each fails DIFFERENTLY from what it certifies):

  C1 walk-exactness  -- the property walk must consume the record to its LAST
                        byte.  A wrong field layout almost never lands exactly
                        on the end; it overruns or leaves a tail.  This fails by
                        an offset mismatch, not by a missing property.
  C2 known-payload   -- 0x27812810 must decode as float32 x3 == {8.0,3.0,1.0}
                        (the value already asserted from the shipped bytes) AND
                        0x27812821 (RKT) must decode as uint32 x3 ==
                        {0x5AD0E817,0xBADB57F1,0x29F10000}, which is a TGI we
                        independently confirmed exists in the archive index.
                        This fails by wrong numbers, not by a bad walk.
  C3 byte-identity   -- re-serialising the decoded property table must reproduce
                        the input record BYTE FOR BYTE.  A decoder that merely
                        "looks right" fails here.  This fails by a diff, not by
                        an exception.
  C4 splice-invariance-- writing new floats into the OccupantSize span must
                        produce a buffer of IDENTICAL LENGTH that differs from
                        the original in EXACTLY the 12 bytes of that span and
                        nowhere else.  This is the actual claim the override
                        depends on, and it fails by a changed length or a stray
                        differing byte.

A negative control is also run: a property id that does NOT exist in the record
(0xDEADBEEF) must not be found.  If the walker "finds" everything, finding
0x27812810 means nothing.

Usage:
    python decode_exemplar.py
    python decode_exemplar.py --dump           # full annotated hexdump
    SC4_GAME_DIR=... python decode_exemplar.py # non-default install

Writes only into this directory (row15-probe\).  Never touches the game install.
"""

import argparse
import os
import struct
import sys

GAME = os.environ.get(
    "SC4_GAME_DIR",
    r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe")

ARCHIVE = "SimCity_1.dat"
TARGET_T = 0x6534284A
TARGET_G = 0xC977C536
TARGET_I = 0x29F10000

PROP_OCCUPANT_SIZE = 0x27812810
PROP_RKT = 0x27812821
PROP_USER_NAME = 0x8A416A99

OUT_DIR = os.path.dirname(os.path.abspath(__file__))

# Exemplar binary value-type codes (u16).  size = bytes per element.
VALUE_TYPES = {
    0x0B00: ("Bool", 1, None),
    0x0B:   ("Bool", 1, None),
    0x0100: ("Uint8", 1, "<B"),
    0x0200: ("Uint16", 2, "<H"),
    0x0300: ("Uint32", 4, "<I"),
    0x0700: ("Sint32", 4, "<i"),
    0x0800: ("Sint64", 8, "<q"),
    0x0900: ("Float32", 4, "<f"),
    0x0C00: ("String", 1, None),
}


# --------------------------------------------------------------------------
# DBPF index / QFS (ports of the same code in DbpfExtract.cs, already used by
# decode_s3d_plate.py -- kept local so this file stands alone)
# --------------------------------------------------------------------------

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
    """Look the entry up in the archive's compression directory (type
    0xE86B1EEF).  Returns the declared uncompressed size, or None if the entry
    is not listed there -- i.e. it is stored UNCOMPRESSED."""
    for (dt, dg, di, doff, dsize) in read_index(path):
        if dt == 0xE86B1EEF:
            with open(path, "rb") as f:
                f.seek(doff)
                blob = f.read(dsize)
            for k in range(dsize // 12):
                et, eg, ei, esize = struct.unpack_from("<IIII", blob, k * 12)
                if (et, eg, ei) == (t, g, i):
                    return esize
            return None
    return None


def has_qfs_signature(raw):
    return (len(raw) >= 9 and raw[4] == 0x10 and raw[5] == 0xFB) or \
           (len(raw) >= 5 and raw[0] == 0x10 and raw[1] == 0xFB)


def qfs_decompress(src):
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


# --------------------------------------------------------------------------
# EXEMPLAR binary decode
# --------------------------------------------------------------------------

class Prop(object):
    """One decoded property, carrying the ABSOLUTE offsets of every field so
    the caller can splice values without recomputing anything."""

    def __init__(self):
        self.off = 0            # start of the property record
        self.pid = 0
        self.pid_off = 0
        self.type_code = 0
        self.type_off = 0
        self.key_type = 0
        self.key_off = 0
        self.unused = 0
        self.count = 0          # element count (1 when key_type == 0x00)
        self.count_off = None   # None when no explicit count field is present
        self.values_off = 0     # first byte of the value payload
        self.values_len = 0
        self.values = []
        self.end = 0

    @property
    def type_name(self):
        return VALUE_TYPES.get(self.type_code, ("Unknown", 0, None))[0]

    def elem_size(self):
        return VALUE_TYPES.get(self.type_code, ("Unknown", 0, None))[1]

    def value_offset(self, k):
        return self.values_off + k * self.elem_size()


def decode_exemplar(buf):
    """Walk the EQZB1### binary exemplar.  Returns (header_dict, [Prop]).

    Layout, as walked here and CONFIRMED by control C3 (byte-identical
    re-serialisation) on the shipped record:

        0x00  8 bytes   magic "EQZB1###" (cohorts use "CQZB1###")
        0x08  u32       parent cohort Type
        0x0C  u32       parent cohort Group
        0x10  u32       parent cohort Instance
        0x14  u32       property count
        0x18  ...       property records, back to back:
                          u32 property id
                          u16 value type code
                          u16 key type   (0x00 = single value, 0x80 = array)
                          u8  unused/pad (0x00)
                          [u32 element count]   <-- ONLY when key type == 0x80
                          element[count]        <-- packed, no padding
    """
    magic = buf[0:8]
    if magic[:4] not in (b"EQZB", b"CQZB", b"EQZT", b"CQZT"):
        raise ValueError("not an exemplar: magic=%r" % magic)
    if magic[:4] in (b"EQZT", b"CQZT"):
        raise ValueError("TEXT exemplar (%r) -- this decoder handles BINARY only"
                         % magic)
    pt, pg, pi, nprops = struct.unpack_from("<IIII", buf, 8)
    hdr = {"magic": magic, "parent_T": pt, "parent_G": pg, "parent_I": pi,
           "prop_count": nprops, "props_start": 0x18}

    props = []
    pos = 0x18
    for _ in range(nprops):
        p = Prop()
        p.off = pos
        p.pid_off = pos
        p.pid = struct.unpack_from("<I", buf, pos)[0]
        p.type_off = pos + 4
        p.type_code = struct.unpack_from("<H", buf, pos + 4)[0]
        p.key_off = pos + 6
        p.key_type = struct.unpack_from("<H", buf, pos + 6)[0]
        p.unused = buf[pos + 8]
        pos += 9
        if p.key_type == 0x80:
            p.count_off = pos
            p.count = struct.unpack_from("<I", buf, pos)[0]
            pos += 4
        elif p.key_type == 0x00:
            p.count_off = None
            p.count = 1
        else:
            raise ValueError("unknown key type 0x%04X at offset %d"
                             % (p.key_type, p.key_off))

        name, esize, fmt = VALUE_TYPES.get(p.type_code, (None, None, None))
        if name is None:
            raise ValueError("unknown value type 0x%04X at offset %d"
                             % (p.type_code, p.type_off))
        p.values_off = pos
        p.values_len = esize * p.count
        raw = buf[pos:pos + p.values_len]
        if len(raw) != p.values_len:
            raise ValueError("property 0x%08X runs past end of record" % p.pid)
        if fmt is not None:
            p.values = [struct.unpack_from(fmt, buf, pos + k * esize)[0]
                        for k in range(p.count)]
        elif name == "String":
            p.values = [raw.decode("latin-1")]
        else:  # Bool
            p.values = list(raw)
        pos += p.values_len
        p.end = pos
        props.append(p)

    hdr["walk_end"] = pos
    return hdr, props


def reserialize(hdr, props, total_len):
    """Rebuild the record from the decoded structure.  Control C3."""
    out = bytearray()
    out += hdr["magic"]
    out += struct.pack("<IIII", hdr["parent_T"], hdr["parent_G"],
                       hdr["parent_I"], hdr["prop_count"])
    for p in props:
        out += struct.pack("<IHHB", p.pid, p.type_code, p.key_type, p.unused)
        if p.count_off is not None:
            out += struct.pack("<I", p.count)
        name, esize, fmt = VALUE_TYPES[p.type_code]
        if fmt is not None:
            for v in p.values:
                out += struct.pack(fmt, v)
        elif name == "String":
            out += p.values[0].encode("latin-1")
        else:
            out += bytes(p.values)
    return bytes(out)


def find_prop(props, pid):
    for p in props:
        if p.pid == pid:
            return p
    return None


def hexdump(data, base=0, mark=None):
    """mark = (start, end) absolute span highlighted with >< in the ascii col."""
    for i in range(0, len(data), 16):
        chunk = data[i:i + 16]
        cells = []
        for k, b in enumerate(chunk):
            a = base + i + k
            if mark and mark[0] <= a < mark[1]:
                cells.append("[%02x]" % b)
            else:
                cells.append(" %02x " % b)
        asc = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        print("%4d  %-64s  %s" % (base + i, "".join(cells), asc))


# --------------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dump", action="store_true",
                    help="print a full annotated hexdump of the record")
    ap.add_argument("--game", default=GAME, help="SimCity 4 install root")
    args = ap.parse_args(argv)

    path = os.path.join(args.game, ARCHIVE)
    if not os.path.isfile(path):
        raise SystemExit("missing %s -- set SC4_GAME_DIR" % path)

    entry = None
    for (t, g, i, off, size) in read_index(path):
        if (t, g, i) == (TARGET_T, TARGET_G, TARGET_I):
            entry = (off, size)
            break
    if entry is None:
        raise SystemExit("exemplar TGI not present in %s" % ARCHIVE)
    off, size = entry
    print("=== LOCATE ===")
    print("%s  T=0x%08X G=0x%08X I=0x%08X  offset=%d  on-disk size=%d"
          % (ARCHIVE, TARGET_T, TARGET_G, TARGET_I, off, size))

    with open(path, "rb") as f:
        f.seek(off)
        raw = f.read(size)

    dir_size = find_dir_uncompressed_size(path, TARGET_T, TARGET_G, TARGET_I)
    sig = has_qfs_signature(raw)
    print("\n=== COMPRESSION ===")
    print("listed in compression DIR (0xE86B1EEF): %s%s"
          % (dir_size is not None,
             "" if dir_size is None else "  (declared uncompressed size=%d)" % dir_size))
    print("QFS 0x10FB signature present in the bytes: %s" % sig)
    if dir_size is not None or sig:
        rec = qfs_decompress(raw)
        compressed = True
        print("-> COMPRESSED. QFS-decompressed to %d bytes" % len(rec))
    else:
        rec = raw
        compressed = False
        print("-> NOT COMPRESSED. record IS the %d on-disk bytes verbatim" % len(rec))
    print("first 8 bytes (magic): %r" % rec[0:8])

    hdr, props = decode_exemplar(rec)
    print("\n=== HEADER ===")
    print("magic          %r" % hdr["magic"])
    print("parent cohort  T=0x%08X G=0x%08X I=0x%08X"
          % (hdr["parent_T"], hdr["parent_G"], hdr["parent_I"]))
    print("property count %d   (table starts at offset 0x%02X = %d)"
          % (hdr["prop_count"], hdr["props_start"], hdr["props_start"]))

    print("\n=== PROPERTY TABLE ===")
    print("%-6s %-12s %-9s %-6s %-6s %-9s %s"
          % ("off", "id", "type", "key", "count", "values@", "values"))
    for p in props:
        vs = p.values
        if p.type_name == "Float32":
            shown = "{%s}" % ", ".join("%g" % v for v in vs)
        elif p.type_name == "String":
            shown = repr(vs[0])
        else:
            shown = "{%s}" % ", ".join("0x%X" % v for v in vs)
        print("%-6d 0x%08X  %-9s 0x%04X %-6d %-9d %s"
              % (p.off, p.pid, p.type_name, p.key_type, p.count,
                 p.values_off, shown))
        print("       raw bytes [%d:%d] = %s"
              % (p.off, p.end, rec[p.off:p.end].hex()))

    # ---------------- controls ----------------
    print("\n=== CONTROLS ===")
    ok = True

    # C1 walk-exactness
    c1 = (hdr["walk_end"] == len(rec))
    print("C1 walk-exactness   : walk ended at %d, record length %d -> %s"
          % (hdr["walk_end"], len(rec), "PASS" if c1 else "FAIL"))
    ok &= c1

    # C2 known payload
    occ = find_prop(props, PROP_OCCUPANT_SIZE)
    rkt = find_prop(props, PROP_RKT)
    c2a = (occ is not None and occ.type_name == "Float32" and occ.count == 3
           and [round(v, 6) for v in occ.values] == [8.0, 3.0, 1.0])
    c2b = (rkt is not None and rkt.count == 3
           and [v & 0xFFFFFFFF for v in rkt.values]
           == [0x5AD0E817, 0xBADB57F1, 0x29F10000])
    print("C2 known-payload    : OccupantSize float32x3 == {8,3,1} -> %s"
          % ("PASS" if c2a else "FAIL (%s)" % (occ.values if occ else "absent")))
    print("                      RKT uint32x3 == the S3D TGI       -> %s"
          % ("PASS" if c2b else "FAIL (%s)" % (rkt.values if rkt else "absent")))
    ok &= c2a and c2b

    # negative control
    neg = find_prop(props, 0xDEADBEEF)
    cneg = neg is None
    print("N  negative control : 0xDEADBEEF absent from the table  -> %s"
          % ("PASS" if cneg else "FAIL"))
    ok &= cneg

    # C3 byte-identity
    rebuilt = reserialize(hdr, props, len(rec))
    c3 = (rebuilt == rec)
    print("C3 byte-identity    : re-serialised %d bytes, identical -> %s"
          % (len(rebuilt), "PASS" if c3 else "FAIL"))
    if not c3:
        for k in range(min(len(rebuilt), len(rec))):
            if rebuilt[k] != rec[k]:
                print("   first difference at offset %d: got %02x want %02x"
                      % (k, rebuilt[k], rec[k]))
                break
    ok &= c3

    # C4 splice-invariance
    if occ is not None:
        span_a, span_b = occ.values_off, occ.values_off + occ.values_len
        probe = bytearray(rec)
        probe[span_a:span_b] = struct.pack("<fff", 16.0, 6.0, 2.0)
        diff = [k for k in range(len(rec)) if probe[k] != rec[k]]
        c4 = (len(probe) == len(rec)
              and diff and min(diff) >= span_a and max(diff) < span_b)
        print("C4 splice-invariance: wrote {16,6,2} into [%d:%d] -> length %d "
              "(was %d), %d differing byte(s), all inside the span -> %s"
              % (span_a, span_b, len(probe), len(rec), len(diff),
                 "PASS" if c4 else "FAIL"))
        # re-decode the spliced buffer: every length field must be unchanged
        h2, p2 = decode_exemplar(bytes(probe))
        c4b = (h2["prop_count"] == hdr["prop_count"]
               and h2["walk_end"] == hdr["walk_end"]
               and len(p2) == len(props)
               and all(a.off == b.off and a.end == b.end and a.count == b.count
                       and a.values_off == b.values_off
                       and a.count_off == b.count_off
                       for a, b in zip(p2, props)))
        print("                      re-decode of the spliced buffer: every "
              "offset/count/length field unchanged -> %s"
              % ("PASS" if c4b else "FAIL"))
        ok &= c4 and c4b

    # -------------- the answer this task exists for --------------
    print("\n=== OccupantSize (0x27812810) FLOAT OFFSETS ===")
    if occ is None:
        print("NOT PRESENT -- nothing to rewrite.")
        ok = False
    else:
        print("property record spans   [%d:%d]  (%d bytes)"
              % (occ.off, occ.end, occ.end - occ.off))
        print("  id        @%-4d  %s" % (occ.pid_off, rec[occ.pid_off:occ.pid_off + 4].hex()))
        print("  typecode  @%-4d  %s  (0x%04X %s)"
              % (occ.type_off, rec[occ.type_off:occ.type_off + 2].hex(),
                 occ.type_code, occ.type_name))
        print("  keytype   @%-4d  %s  (0x%04X %s)"
              % (occ.key_off, rec[occ.key_off:occ.key_off + 2].hex(),
                 occ.key_type, "array" if occ.key_type == 0x80 else "single"))
        print("  unused    @%-4d  %02x" % (occ.off + 8, occ.unused))
        if occ.count_off is not None:
            print("  count     @%-4d  %s  (= %d)  <-- LENGTH FIELD, must not move"
                  % (occ.count_off, rec[occ.count_off:occ.count_off + 4].hex(),
                     occ.count))
        labels = ("X (length)", "Y (height)", "Z (width)")
        for k in range(occ.count):
            a = occ.value_offset(k)
            print("  float[%d]  @%-4d  %s  = %g   %s"
                  % (k, a, rec[a:a + 4].hex(), occ.values[k],
                     labels[k] if k < 3 else ""))
        print("VALUE SPAN TO REWRITE: [%d:%d]  (12 bytes, 3 x float32 LE)"
              % (occ.values_off, occ.values_off + occ.values_len))

    if args.dump:
        print("\n=== ANNOTATED HEXDUMP (OccupantSize value span in [brackets]) ===")
        mark = (occ.values_off, occ.values_off + occ.values_len) if occ else None
        hexdump(rec, 0, mark)

    # save the record for downstream tools
    base = "T-%08x_G-%08x_I-%08x" % (TARGET_T, TARGET_G, TARGET_I)
    raw_path = os.path.join(OUT_DIR, base + ".ondisk.bin")
    dec_path = os.path.join(OUT_DIR, base + ".record.bin")
    with open(raw_path, "wb") as f:
        f.write(raw)
    with open(dec_path, "wb") as f:
        f.write(rec)
    print("\nsaved %s (%d bytes, as stored on disk)" % (raw_path, len(raw)))
    print("saved %s (%d bytes, the record this decode describes)"
          % (dec_path, len(rec)))
    print("compressed on disk: %s" % compressed)

    print("\nALL CONTROLS: %s" % ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
