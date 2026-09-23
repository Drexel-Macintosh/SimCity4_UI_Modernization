# graph_census.py - independent DBPF + QFS + exemplar reader (written for this verify, no repo imports).
# Lists every exemplar carrying property 0xAA4C0D1B (Graphs chart type) in the given .dat files,
# with the exemplar name (0x00000020) and 0x8A416A99 when present.
# usage: python graph_census.py <file.dat> [more.dat ...]
import struct, sys

PROP_TYPE = 0xAA4C0D1B
PROP_NAME = 0x00000020
PROP_TITLE = 0x8A416A99
EXEMPLAR_T = 0x6534284A
COHORT_T = 0x05342861
DIR_T = 0xE86B1EEF

def qfs(data):
    pos = 0
    if data[4:6] in (b"\x10\xfb", b"\x11\xfb"):
        pos = 4
    elif data[0:2] in (b"\x10\xfb", b"\x11\xfb"):
        pos = 0
    else:
        raise ValueError("not QFS")
    flags = data[pos]
    pos += 2
    if flags & 0x80:
        usize = int.from_bytes(data[pos:pos + 4], "big"); pos += 4
    else:
        usize = int.from_bytes(data[pos:pos + 3], "big"); pos += 3
    if flags & 0x01:
        pos += 3
    out = bytearray()
    n = len(data)
    while pos < n:
        b0 = data[pos]
        if b0 < 0x80:
            b1 = data[pos + 1]; pos += 2
            plain = b0 & 3; count = ((b0 & 0x1C) >> 2) + 3; off = ((b0 & 0x60) << 3) + b1 + 1
        elif b0 < 0xC0:
            b1, b2 = data[pos + 1], data[pos + 2]; pos += 3
            plain = (b1 >> 6) & 3; count = (b0 & 0x3F) + 4; off = ((b1 & 0x3F) << 8) + b2 + 1
        elif b0 < 0xE0:
            b1, b2, b3 = data[pos + 1], data[pos + 2], data[pos + 3]; pos += 4
            plain = b0 & 3; count = ((b0 & 0x0C) << 6) + b3 + 5; off = ((b0 & 0x10) << 12) + (b1 << 8) + b2 + 1
        elif b0 < 0xFC:
            pos += 1
            plain = ((b0 & 0x1F) << 2) + 4; count = 0; off = 0
        else:
            pos += 1
            plain = b0 & 3; count = 0; off = 0
        out += data[pos:pos + plain]; pos += plain
        for _ in range(count):
            out.append(out[-off])
        if b0 >= 0xFC:
            break
    return bytes(out), usize

def read_dbpf(path):
    f = open(path, "rb").read()
    assert f[:4] == b"DBPF", path
    idx_ver = struct.unpack_from("<I", f, 0x20)[0]
    cnt, ioff, isz = struct.unpack_from("<III", f, 0x24)
    minor_idx = struct.unpack_from("<I", f, 0x3C)[0]
    esz = isz // cnt if cnt else 20
    entries = []
    for k in range(cnt):
        o = ioff + k * esz
        if esz == 20:
            t, g, i, off, sz = struct.unpack_from("<IIIII", f, o)
        else:
            t, g, i, i2, off, sz = struct.unpack_from("<IIIIII", f, o)
        entries.append((t, g, i, off, sz))
    comp = set()
    for t, g, i, off, sz in entries:
        if t == DIR_T:
            d = f[off:off + sz]
            step = 16 if (len(d) % 16 == 0) else 20
            for k in range(0, len(d) - step + 1, step):
                ct, cg, ci = struct.unpack_from("<III", d, k)
                comp.add((ct, cg, ci))
    return f, entries, comp

VSIZE = {0x0100: 1, 0x0200: 2, 0x0300: 4, 0x0700: 4, 0x0800: 8, 0x0900: 4, 0x0B00: 1, 0x0C00: 1}
VFMT = {0x0100: "<B", 0x0200: "<H", 0x0300: "<I", 0x0700: "<i", 0x0800: "<q", 0x0900: "<f", 0x0B00: "<?", 0x0C00: None}

def parse_exemplar(b):
    props = {}
    if b[:4] not in (b"EQZB", b"CQZB"):
        if b[:4] in (b"EQZT", b"CQZT"):
            return parse_text_exemplar(b)
        return None
    pos = 8 + 12
    n = struct.unpack_from("<I", b, pos)[0]; pos += 4
    for _ in range(n):
        pid, vt, kt = struct.unpack_from("<IHH", b, pos); pos += 8
        sz = VSIZE.get(vt)
        if sz is None:
            return props
        if kt == 0x80:
            pos += 1
            cnt = struct.unpack_from("<I", b, pos)[0]; pos += 4
            raw = b[pos:pos + cnt * sz]; pos += cnt * sz
            if vt == 0x0C00:
                props[pid] = raw.decode("latin-1")
            else:
                props[pid] = [struct.unpack_from(VFMT[vt], raw, j * sz)[0] for j in range(cnt)]
        else:
            pos += 1
            raw = b[pos:pos + sz]; pos += sz
            props[pid] = raw.decode("latin-1") if vt == 0x0C00 else struct.unpack_from(VFMT[vt], raw, 0)[0]
    return props

def parse_text_exemplar(b):
    import re
    props = {}
    for line in b.decode("latin-1").splitlines():
        m = re.match(r"\s*0x([0-9A-Fa-f]{8})\s*:\s*\{[^}]*\}\s*=\s*(\w+)\s*:\s*\d+\s*:\s*\{(.*)\}", line)
        if m:
            pid = int(m.group(1), 16)
            vals = m.group(3)
            if m.group(2).lower() == "string":
                props[pid] = vals.strip('"')
            else:
                out = []
                for v in vals.split(","):
                    v = v.strip()
                    try:
                        out.append(int(v, 0))
                    except ValueError:
                        try:
                            out.append(float(v))
                        except ValueError:
                            out.append(v)
                props[pid] = out
    return props

for path in sys.argv[1:]:
    f, entries, comp = read_dbpf(path)
    nex = 0
    hits = []
    for t, g, i, off, sz in entries:
        if t not in (EXEMPLAR_T, COHORT_T):
            continue
        nex += 1
        raw = f[off:off + sz]
        if (t, g, i) in comp:
            try:
                raw, _ = qfs(raw)
            except Exception as e:
                continue
        p = parse_exemplar(raw)
        if p and PROP_TYPE in p:
            hits.append((t, g, i, p.get(PROP_TYPE), p.get(PROP_NAME), p.get(PROP_TITLE)))
    print("== %s : %d index entries, %d exemplars/cohorts scanned, %d carry 0xAA4C0D1B" % (path, len(entries), nex, len(hits)))
    for t, g, i, v, nm, ti in sorted(hits, key=lambda h: (h[1], h[2])):
        print("   T=%08X G=%08X I=%08X type=%s name=%r title=%r" % (t, g, i, v, nm, ti))
