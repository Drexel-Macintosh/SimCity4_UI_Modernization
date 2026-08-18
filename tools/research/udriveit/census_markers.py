#!/usr/bin/env python3
r"""CENSUS of the marker-occupant exemplar family: every resource of type
0x6534284A across EVERY shipped DBPF archive (discovered recursively) plus the
whole Plugins tree.

Why type 0x6534284A: the neighbour-connection arrow -- a proven sibling of the
U-Drive-It offer balloon (same 0x68-byte marker occupant, ctor 0x5EE050) -- is
instantiated from exemplar {T=0x6534284A, G=0xC977C536, I=0x29F10000}, and the
live prop-binder capture shows every marker's PROPSUB carrying a key whose
type+group are exactly 0x6534284A / 0xC977C536.

Read-only on the game install and Documents\SimCity 4.  Writes only under
tools\research\udriveit\.

⛔ The archive list is DISCOVERED, never hard-coded (see tools/dbpf/find_tgi.py
docstring, task #140: the install ships an EIGHTH archive, Intro.dat, that a
hand-written list of seven silently missed).  Here we walk the install root
RECURSIVELY, so Apps\, Plugins\ and Sku_Data\ are covered too.
"""
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", ".."))
from sc4paths import plugins_dir, game_dir  # noqa: E402

T_EXEMPLAR_MARKER = 0x6534284A
T_S3D = 0x5AD0E817
T_FSH = 0x7AB50E44
T_DIR = 0xE86B1EEF

PLUGIN_EXTS = (".dat", ".sc4lot", ".sc4desc", ".sc4model", ".sc4")


# ---------------------------------------------------------------- DBPF index
def dbpf_index(path):
    """Yield (type, group, instance, offset, size) for a DBPF 1.0 index 7.0.

    Returns [] for anything that is not a DBPF (so the caller can walk a tree
    blindly).  Raises nothing.
    """
    try:
        with open(path, "rb") as f:
            hdr = f.read(96)
            if len(hdr) < 96 or hdr[:4] != b"DBPF":
                return []
            count, idx_off, idx_size = struct.unpack_from("<III", hdr, 0x24)
            if not count:
                return []
            stride = idx_size // count
            if stride not in (20, 24):
                return []
            f.seek(idx_off)
            blob = f.read(idx_size)
    except Exception:
        return []
    out = []
    for k in range(count):
        o = k * stride
        if stride == 20:
            t, g, i, off, sz = struct.unpack_from("<IIIII", blob, o)
        else:                      # index 7.1 carries an extra instance-hi dword
            t, g, i, _hi, off, sz = struct.unpack_from("<IIIIII", blob, o)
        out.append((t, g, i, off, sz))
    return out


def read_entry(path, off, size):
    with open(path, "rb") as f:
        f.seek(off)
        return f.read(size)


# ------------------------------------------------------------------- QFS/RefPack
def qfs_decompress(data):
    """SC4 QFS (RefPack).  Header: u32 uncompressed-size-of-container,
    then 0x10 0xFB, then a 3-byte big-endian output length."""
    if len(data) < 9:
        raise ValueError("too short for QFS")
    if data[4:6] == b"\x10\xfb":
        p = 6
    elif data[0:2] == b"\x10\xfb":
        p = 2
    else:
        raise ValueError("not QFS")
    outlen = (data[p] << 16) | (data[p + 1] << 8) | data[p + 2]
    p += 3
    out = bytearray()
    n = len(data)
    done = False
    while p < n and not done:
        cc = data[p]
        if cc < 0x80:
            if p + 1 >= n:
                break
            cc1 = data[p + 1]
            p += 2
            nplain = cc & 0x03
            ncopy = ((cc & 0x1C) >> 2) + 3
            offset = ((cc & 0x60) << 3) + cc1 + 1
        elif cc < 0xC0:
            if p + 2 >= n:
                break
            cc1, cc2 = data[p + 1], data[p + 2]
            p += 3
            nplain = (cc1 >> 6) & 0x03
            ncopy = (cc & 0x3F) + 4
            offset = ((cc1 & 0x3F) << 8) + cc2 + 1
        elif cc < 0xE0:
            if p + 3 >= n:
                break
            cc1, cc2, cc3 = data[p + 1], data[p + 2], data[p + 3]
            p += 4
            nplain = cc & 0x03
            ncopy = ((cc & 0x0C) << 6) + cc3 + 5
            offset = ((cc & 0x10) << 12) + (cc1 << 8) + cc2 + 1
        elif cc < 0xFC:
            nplain = ((cc & 0x1F) + 1) * 4
            ncopy = 0
            offset = 0
            p += 1
        else:                                   # 0xFC..0xFF: terminator
            nplain = cc & 0x03
            ncopy = 0
            offset = 0
            p += 1
            done = True
        if nplain:
            out += data[p:p + nplain]
            p += nplain
        if ncopy:
            start = len(out) - offset
            if start < 0:
                raise ValueError("bad back-reference")
            for k in range(ncopy):
                out.append(out[start + k])
    if len(out) != outlen:
        raise ValueError("QFS length mismatch: got %d want %d" % (len(out), outlen))
    return bytes(out)


def maybe_decompress(raw):
    """Return (payload, was_compressed)."""
    if len(raw) > 9 and raw[4:6] == b"\x10\xfb":
        try:
            return qfs_decompress(raw), True
        except Exception:
            return raw, False
    return raw, False


# ------------------------------------------------------------------- exemplar
VALTYPE = {
    0x100: ("B", 1, "uint8"),
    0x200: ("H", 2, "uint16"),
    0x300: ("I", 4, "uint32"),
    0x700: ("i", 4, "sint32"),
    0x800: ("q", 8, "sint64"),
    0x900: ("f", 4, "float32"),
    0xB00: ("B", 1, "bool"),
    0xC00: (None, 1, "string"),
}


def parse_exemplar_binary(data):
    """Binary EQZB1### / CQZB1### exemplar -> {propId: (typename, [values])}."""
    if len(data) < 0x18:
        raise ValueError("too short")
    sig = data[0:4]
    if sig not in (b"EQZB", b"CQZB"):
        raise ValueError("bad signature %r" % data[0:8])
    parent = struct.unpack_from("<III", data, 0x08)
    prop_count = struct.unpack_from("<I", data, 0x14)[0]
    off = 0x18
    props = {}
    order = []
    for _ in range(prop_count):
        if off + 9 > len(data):
            raise ValueError("truncated prop header at 0x%X" % off)
        prop_id, val_type, key_type = struct.unpack_from("<IHH", data, off)
        off += 8
        off += 1                                   # pad byte on BOTH shapes
        if key_type == 0x80:
            rep = struct.unpack_from("<I", data, off)[0]
            off += 4
        elif key_type == 0x00:
            rep = 1
        else:
            raise ValueError("unknown keyType 0x%X" % key_type)
        fmt, w, tname = VALTYPE.get(val_type, (None, None, None))
        if tname is None:
            raise ValueError("unknown valType 0x%X" % val_type)
        if val_type == 0xC00:
            if key_type == 0x00:
                vals = [b""]
            else:
                vals = [data[off:off + rep]]
                off += rep
        else:
            vals = []
            for _i in range(rep):
                if off + w > len(data):
                    raise ValueError("truncated value")
                vals.append(struct.unpack_from("<" + fmt, data, off)[0])
                off += w
        props[prop_id] = (tname, vals)
        order.append(prop_id)
    return parent, props, order


def parse_exemplar_text(text):
    """Text EQZT1### exemplar.  Returns (parent, {id: (tname, [vals])}, order)."""
    props = {}
    order = []
    parent = (0, 0, 0)
    for line in text.splitlines():
        s = line.strip()
        if s.lower().startswith("parentcohort"):
            hexes = [h for h in s.replace(":", "=").split("=")[-1].split(",")]
            try:
                parent = tuple(int(h.strip().strip("{}"), 16) for h in hexes[:3])
            except Exception:
                pass
            continue
        if not s.startswith("0x"):
            continue
        # 0x00000020:{"ExemplarName"}=String:0:{"Foo"}
        try:
            head, rest = s.split(":", 1)
            pid = int(head, 16)
            after = rest.split("=", 1)[1]
            tname = after.split(":", 1)[0]
            body = after[after.find("{", after.find(":")) + 1:]
            body = body.rsplit("}", 1)[0]
            vals = [v.strip().strip('"') for v in body.split(",")] if body else []
            conv = []
            for v in vals:
                if tname.lower() in ("string",):
                    conv.append(v.encode("latin-1", "replace"))
                elif v.lower().startswith("0x"):
                    conv.append(int(v, 16))
                else:
                    try:
                        conv.append(float(v) if "." in v else int(v))
                    except Exception:
                        conv.append(v)
            props[pid] = (tname, conv)
            order.append(pid)
        except Exception:
            continue
    return parent, props, order


def parse_exemplar(payload):
    if payload[:4] in (b"EQZB", b"CQZB"):
        return parse_exemplar_binary(payload)
    if payload[:4] in (b"EQZT", b"CQZT"):
        return parse_exemplar_text(payload.decode("latin-1", "replace"))
    raise ValueError("unrecognised exemplar signature %r" % payload[:8])


# ------------------------------------------------------------------- discovery
def discover_dbpf(root):
    """Every DBPF-looking file under root, recursively."""
    out = []
    for dirpath, _dirs, files in os.walk(root):
        for fn in files:
            if fn.lower().endswith(PLUGIN_EXTS) or fn.lower().endswith(".dat"):
                out.append(os.path.join(dirpath, fn))
    return sorted(out, key=str.lower)


def main():
    game = game_dir()
    plug = plugins_dir(require=False)
    roots = [("GAME", game)]
    if plug and os.path.isdir(plug):
        roots.append(("PLUGINS", plug))
    files = []
    for label, root in roots:
        for p in discover_dbpf(root):
            files.append((label, root, p))
    print("discovered %d candidate DBPF file(s)" % len(files))
    return files, game, plug


if __name__ == "__main__":
    main()
