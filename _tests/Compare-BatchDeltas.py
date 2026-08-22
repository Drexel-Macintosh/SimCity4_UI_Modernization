r"""Entry-payload diff of two DBPF dats, judged against an EXPECTED-DELTAS manifest.

⛔ WHY THIS EXISTS (2026-08-16 batch, #172/#177). The integer-tier control used
to be a human reading a diff dump and deciding "that looks like what we meant".
This run's batch DELIBERATELY changes integer tiers (#172's stock overhang), so
"zero diffs at 2x/3x" is no longer the pass condition - the pass condition is
"EXACTLY the diffs the manifest predicted, nothing more, nothing less". A human
eyeballing that across nine packages will miss one line; this will not.

LAW 98: DBPF file hashes are NOT reproducible (2-byte header timestamp at
offsets 25/29). Compare ENTRY PAYLOADS keyed by TGI, never file bytes.

    python Compare-BatchDeltas.py <old.dat> <new.dat> [--expect g:i g:i ...]

Exit 0 iff the changed-entry TGI set == the --expect set (added/removed always
fail unless expected is extended to cover them - this batch predicts none).
"""
import hashlib
import struct
import sys


def read_entries(path):
    data = open(path, "rb").read()
    if data[:4] != b"DBPF":
        sys.exit("not a DBPF: " + path)
    # header: index entry count @36, index offset @40, index size @44 (v1.x)
    n = struct.unpack_from("<I", data, 36)[0]
    off = struct.unpack_from("<I", data, 40)[0]
    entries = {}
    p = off
    for _ in range(n):
        t, g, i, o, s = struct.unpack_from("<IIIII", data, p)
        p += 20
        entries[(t, g, i)] = hashlib.sha1(data[o:o + s]).hexdigest()
    return entries


def main():
    old_p, new_p = sys.argv[1], sys.argv[2]
    expect = set()
    expect_removed = set()
    argv = sys.argv
    if "--expect-removed" in argv:
        k = argv.index("--expect-removed")
        for tok in argv[k + 1:]:
            if tok.startswith("--"):
                break
            g, i = tok.split(":")
            expect_removed.add((int(g, 16), int(i, 16)))
        argv = argv[:k + 1]   # keep flag position; tokens consumed above
    if "--expect" in argv:
        for tok in sys.argv[sys.argv.index("--expect") + 1:]:
            if tok.startswith("--"):
                break
            g, i = tok.split(":")
            expect.add((int(g, 16), int(i, 16)))
    old, new = read_entries(old_p), read_entries(new_p)
    added = sorted(set(new) - set(old))
    removed = sorted(set(old) - set(new))
    changed = sorted(k for k in set(old) & set(new) if old[k] != new[k])
    changed_gi = {(g, i) for (_, g, i) in changed}
    unexpected = sorted(changed_gi - expect)
    missing = sorted(expect - changed_gi)
    print("%s vs %s" % (old_p, new_p))
    print("  entries %d -> %d | added %d removed %d changed %d (expected %d)"
          % (len(old), len(new), len(added), len(removed), len(changed),
             len(expect)))
    for k in added:
        print("  ADDED   %08x %08x %08x" % k)
    for k in removed:
        print("  REMOVED %08x %08x %08x" % k)
    for k in changed:
        tag = "expected" if (k[1], k[2]) in expect else "*** UNEXPECTED ***"
        print("  CHANGED %08x %08x %08x  %s" % (k[0], k[1], k[2], tag))
    for g, i in missing:
        print("  MISSING expected change: %08x %08x (fix failed to land?)"
              % (g, i))
    # --subset: the expected set is a TIER-WIDE superset and this dat may
    # legitimately carry only part of it (the #177 sheets are spread across
    # packages). Changed must still be a SUBSET of expected; "missing" is
    # judged by the caller across the UNION of all packages, not per dat.
    subset = "--subset" in sys.argv
    removed_gi = {(g, i) for (_, g, i) in removed}
    bad_removed = removed_gi - expect_removed
    ok = not added and not bad_removed and not unexpected \
        and (subset or not missing)
    print("  VERDICT: " + ("PASS" if ok else "FAIL")
          + (" (subset mode)" if subset else ""))
    return 0 if ok else 1


sys.exit(main())
