#!/usr/bin/env python3
r"""Which marker-family exemplar INSTANCE ids are hard-coded in the exe?

The neighbour-connection arrow is created by 0x6D4860 which PUSHES the literal
0x29F10000 (@0x6D4A66).  So the engine hard-codes the instance id of the
markers it spawns itself.  Sweep every dword in .text/.rdata/.data against the
set of instance ids the census found, and report the hits.

POSITIVE CONTROL: 0x29F10000 (ConnectArrow) MUST appear at 0x6D4A66.
If it does not, the sweep is broken and every miss below is meaningless.

    python exe_instance_sweep.py [--group C977C536]
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", ".."))
from census_markers import (dbpf_index, read_entry, maybe_decompress,   # noqa: E402
                            parse_exemplar, discover_dbpf,
                            T_EXEMPLAR_MARKER)
from sc4paths import plugins_dir, game_dir                              # noqa: E402

EXE = os.path.join(game_dir(), "Apps", "SimCity 4.exe")


def load_pe(path):
    data = open(path, "rb").read()
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    nsec = struct.unpack_from("<H", data, pe + 6)[0]
    optsz = struct.unpack_from("<H", data, pe + 20)[0]
    base = struct.unpack_from("<I", data, pe + 24 + 28)[0]
    secs = []
    for i in range(nsec):
        o = pe + 24 + optsz + i * 40
        name = data[o:o + 8].rstrip(b"\0").decode("latin1")
        vs, va, rs, ra = struct.unpack_from("<IIII", data, o + 8)
        secs.append((name, va, vs, ra, rs))
    return data, base, secs


def build_name_map(group_filter):
    game = game_dir()
    plug = plugins_dir(require=False)
    names = {}
    for root in [game] + ([plug] if plug else []):
        for p in discover_dbpf(root):
            for (t, g, i, off, sz) in dbpf_index(p):
                if t != T_EXEMPLAR_MARKER:
                    continue
                if group_filter is not None and g != group_filter:
                    continue
                if i in names:
                    continue
                try:
                    payload, _ = maybe_decompress(read_entry(p, off, sz))
                    _parent, props, _o = parse_exemplar(payload)
                except Exception:
                    continue
                nm = ""
                if 0x20 in props:
                    v = props[0x20][1][0]
                    nm = v.decode("latin-1", "replace") if isinstance(v, bytes) else str(v)
                names[i] = (g, nm, os.path.basename(p))
    return names


def main():
    group = 0xC977C536
    if "--group" in sys.argv:
        group = int(sys.argv[sys.argv.index("--group") + 1], 16)
    if "--allgroups" in sys.argv:
        group = None
    names = build_name_map(group)
    print("census instance ids in scope: %d (group %s)"
          % (len(names), "ALL" if group is None else "0x%08X" % group))
    data, base, secs = load_pe(EXE)
    strict = "--loose" not in sys.argv
    hits = []
    for sname, sva, vs, ra, rs in secs:
        if sname not in (".text", ".rdata", ".data"):
            continue
        end = ra + rs
        for off in range(ra, end - 4):
            v = struct.unpack_from("<I", data, off)[0]
            if v not in names:
                continue
            if strict and sname == ".text":
                # only accept an id that is an actual IMMEDIATE operand:
                #   68 imm32            push imm32
                #   B8..BF imm32        mov r32, imm32
                #   C7 /0 ... imm32     mov r/m32, imm32   (2- and 3-byte forms)
                #   3D imm32            cmp eax, imm32
                #   81 /x modrm imm32   cmp/add/sub r/m32, imm32
                prev = data[off - 1] if off else 0
                prev2 = data[off - 2] if off > 1 else 0
                prev3 = data[off - 3] if off > 2 else 0
                ok = (prev == 0x68 or 0xB8 <= prev <= 0xBF or prev == 0x3D
                      or prev2 == 0xC7 or prev3 == 0xC7
                      or prev2 == 0x81 or prev3 == 0x81)
                if not ok:
                    continue
            va = base + sva + (off - ra)
            hits.append((va, sname, v))
    print("dword hits: %d  (%s)"
          % (len(hits), "immediate-operand filtered in .text"
             if strict else "raw, unfiltered"))
    print()
    seen = {}
    for va, sname, v in hits:
        seen.setdefault(v, []).append((va, sname))
    for v in sorted(seen):
        g, nm, src = names[v]
        locs = seen[v]
        print("0x%08X  %-46s [%s]" % (v, nm[:46], src))
        for va, sname in locs[:8]:
            print("            @ 0x%08X (%s)" % (va, sname))
        if len(locs) > 8:
            print("            ... %d more" % (len(locs) - 8))
    print()
    # The doc cites the PUSH instruction at 0x6D4A66; this sweep reports the
    # IMMEDIATE's address, one byte later (opcode 0x68 + imm32).  Accept either.
    ctl = seen.get(0x29F10000, [])
    ok = any(va in (0x006D4A66, 0x006D4A67) for va, _s in ctl)
    print("POSITIVE CONTROL 0x29F10000 (push @0x6D4A66, imm @0x6D4A67): %s "
          "(%d site(s) total)"
          % ("PASS" if ok else "*** FAIL - sweep is broken ***", len(ctl)))


if __name__ == "__main__":
    main()
