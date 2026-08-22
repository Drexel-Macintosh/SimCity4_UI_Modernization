"""scan_text.py - STAGE 1a: whole-.text call/branch edge index.

Byte-level scan (no disassembly) for the two rel32 forms that carry the
call graph:

    E8 rel32   call    target = site + 5 + rel32
    E9 rel32   jmp     target = site + 5 + rel32   (tail calls / thunks)

Byte scanning finds EVERY encoding of a call regardless of where the
instruction stream happens to be aligned - which is the whole point: the
hand-enumeration this replaces missed sites because it followed one path.
False positives (an 0xE8 byte inside an immediate) are filtered later by
build_funcs.py's plausibility test and finally by census.py, which only
accepts a site that also decodes as a `call` when its owning function is
disassembled linearly.

Work units: one per 64 KB of .text ('shard NNN'), result written to
_work/calls/NNN.json immediately, then marked done in state.json.

Usage:
    python scan_text.py            # from scratch (idempotent)
    python scan_text.py --resume   # skip shards already marked done
"""
import json
import os
import struct
import sys

import common as C


def main():
    resume = "--resume" in sys.argv
    st = C.State()
    out = C.ensure_work("calls")
    blob = C.text_blob()
    n = len(blob)
    nshards = (n + C.SHARD - 1) // C.SHARD

    if not resume:
        st.reset_stage("scan")

    total = 0
    for s in range(nshards):
        unit = "%03d" % s
        path = os.path.join(out, unit + ".json")
        if resume and st.done("scan", unit) and os.path.exists(path):
            continue
        lo = s * C.SHARD
        hi = min(n, lo + C.SHARD)
        edges = []
        # +4 slack so a rel32 that starts in this shard is fully readable
        seg = blob[lo:min(n, hi + 4)]
        for op, kind in ((0xE8, "call"), (0xE9, "jmp")):
            i = seg.find(bytes([op]))
            while i != -1 and i < (hi - lo):
                if i + 5 <= len(seg):
                    rel = struct.unpack_from("<i", seg, i + 1)[0]
                    site = C.TEXT_LO + lo + i
                    tgt = site + 5 + rel
                    if C.va_ok(tgt):
                        edges.append([site, tgt, kind])
                i = seg.find(bytes([op]), i + 1)
        edges.sort()
        C.jdump(path, edges)
        st.mark("scan", unit, "done", edges=len(edges),
                va="0x%X-0x%X" % (C.TEXT_LO + lo, C.TEXT_LO + hi))
        total += len(edges)
        if s % 16 == 0:
            print("  shard %s  0x%X  (%d edges)" % (unit, C.TEXT_LO + lo, len(edges)))

    print("scan_text: %d shards, %d new edges" % (nshards, total))
    print("state:", st.counts("scan"))


if __name__ == "__main__":
    main()
