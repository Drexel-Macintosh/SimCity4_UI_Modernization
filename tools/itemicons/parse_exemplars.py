#!/usr/bin/env python3
"""
Parse SC4 binary exemplars (EQZB1###) extracted from SimCity_1.dat and enumerate the
distinct "Item Icon" instance IDs (property 0x8A2602B8).

Authority: tools/research/ITEMICONS.md, appendix "Binary exemplar (EQZB1###) format".
The Item Icon TGI is assembled in the exe as {type 0x856DDBAC, group 0x6A386D26, <B8 value>}.

Usage:
    python parse_exemplars.py <exemplars_dir> <out_csv>

Writes <out_csv> with columns: source_file, item_icon_instance (hex8).
Prints a summary: exemplars parsed, exemplars with B8, distinct B8 values, parse failures.
Reads only; creates no files other than <out_csv>.
"""
import os, sys, struct

PROP_ITEM_ICON = 0x8A2602B8

# valueType -> (struct-fmt-char, byte-width). string (0xC00) handled specially.
VALTYPE = {
    0x100: ('B', 1),   # uint8
    0x200: ('H', 2),   # uint16
    0x300: ('I', 4),   # uint32
    0x700: ('i', 4),   # sint32
    0x800: ('q', 8),   # sint64
    0x900: ('f', 4),   # float32
    0xB00: ('B', 1),   # bool (1 byte)
}

def parse_exemplar(data):
    """Return dict propId -> list of values, or raise ValueError on malformed data."""
    if len(data) < 0x18:
        raise ValueError("too short")
    sig = data[0:8]
    if sig[0:4] not in (b'EQZB', b'CQZB'):
        raise ValueError("bad signature %r" % sig)
    # 0x08..0x14 parent cohort TGI (3 u32) - skip
    prop_count = struct.unpack_from('<I', data, 0x14)[0]
    off = 0x18
    props = {}
    for _ in range(prop_count):
        if off + 8 > len(data):
            raise ValueError("truncated prop header")
        prop_id, val_type, key_type = struct.unpack_from('<IHH', data, off)
        off += 8
        # per ITEMICONS.md format: one pad byte follows the key_type for BOTH
        # single and array records (the documented "pad byte on singles" gotcha).
        if key_type == 0x80:
            # array: [1 pad byte][u32 repCount][repCount values]
            off += 1
            if off + 4 > len(data):
                raise ValueError("truncated array count")
            rep = struct.unpack_from('<I', data, off)[0]
            off += 4
            vals = []
            if val_type == 0xC00:  # string: rep bytes
                s = data[off:off+rep]; off += rep
                vals = [s]
            elif val_type in VALTYPE:
                fmt, w = VALTYPE[val_type]
                for _i in range(rep):
                    if off + w > len(data):
                        raise ValueError("truncated array value")
                    vals.append(struct.unpack_from('<' + fmt, data, off)[0]); off += w
            else:
                raise ValueError("unknown valType 0x%X (array)" % val_type)
            props.setdefault(prop_id, []).extend(vals)
        elif key_type == 0x00:
            # single: [1 pad byte][one value]
            off += 1
            if val_type == 0xC00:
                # a "single" string is unusual; treat remaining until next as 0-len
                props.setdefault(prop_id, []).append(b'')
            elif val_type in VALTYPE:
                fmt, w = VALTYPE[val_type]
                if off + w > len(data):
                    raise ValueError("truncated single value")
                props.setdefault(prop_id, []).append(struct.unpack_from('<' + fmt, data, off)[0]); off += w
            else:
                raise ValueError("unknown valType 0x%X (single)" % val_type)
        else:
            raise ValueError("unknown keyType 0x%X" % key_type)
    return props

def main():
    exdir, out_csv = sys.argv[1], sys.argv[2]
    files = [f for f in os.listdir(exdir)
             if f.lower().endswith('.png') and f.lower() != 'extract-manifest.csv']
    parsed = 0
    failures = []
    with_b8 = 0
    rows = []  # (file, instance)
    distinct = {}
    for f in sorted(files):
        p = os.path.join(exdir, f)
        try:
            with open(p, 'rb') as fh:
                data = fh.read()
            props = parse_exemplar(data)
            parsed += 1
        except Exception as e:
            failures.append((f, str(e)))
            continue
        if PROP_ITEM_ICON in props:
            with_b8 += 1
            for v in props[PROP_ITEM_ICON]:
                inst = v & 0xFFFFFFFF
                rows.append((f, inst))
                distinct[inst] = distinct.get(inst, 0) + 1
    with open(out_csv, 'w', newline='') as out:
        out.write("source_file,item_icon_instance\n")
        for f, inst in rows:
            out.write("%s,0x%08x\n" % (f, inst))
    print("exemplars total      : %d" % len(files))
    print("exemplars parsed OK  : %d" % parsed)
    print("parse failures       : %d" % len(failures))
    print("exemplars with B8    : %d" % with_b8)
    print("total B8 occurrences : %d" % len(rows))
    print("distinct B8 values   : %d" % len(distinct))
    if failures[:5]:
        print("first failures       :")
        for f, e in failures[:5]:
            print("   ", f, "->", e)
    # write distinct list too
    dpath = out_csv.replace('.csv', '_distinct.txt')
    with open(dpath, 'w') as dh:
        for inst in sorted(distinct):
            dh.write("0x%08x\n" % inst)
    print("distinct list written: %s" % dpath)

if __name__ == '__main__':
    main()
