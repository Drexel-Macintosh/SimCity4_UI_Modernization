#!/usr/bin/env python3
r"""Who NAMES the ConnectArrow S3Ds, and how do the other nineteen get picked?

THE QUESTION THIS ANSWERS
-------------------------
The row-15 exemplar {0x6534284A, 0xC977C536, 0x29F10000} binds a model through
its ResourceKeyType property 0x27812821, and that property names exactly one
S3D: {0x5AD0E817, 0xBADB57F1, 0x29F10000}.  But twenty S3Ds ship in that
instance range, one per zoom level and rotation.  So either

    (a) the single RKT is the only live path, the other nineteen are dead
        weight, and overriding one record is enough; or
    (b) the RKT names a BASE instance and the engine composes the real key at
        draw time from base + zoom + rotation, in which case overriding one
        record changes nothing at nineteen of twenty camera positions.

Getting this wrong in direction (a) costs a play session that produces a
confident fake null.  This script settles it from the shipped bytes.

METHOD
------
Decode every binary exemplar and cohort in every DISCOVERED archive, collect
every ResourceKeyType property that names an S3D, and ask two things:

  Q1  Is any of the nineteen non-base ConnectArrow instances named by ANY RKT,
      anywhere in the install?
  Q2  Across the whole install, when an RKT names an S3D whose instance ends in
      three zero nibbles, how often do all twenty zoom/rotation siblings ship,
      and how often are those siblings themselves named by an RKT?

Q2 is the part that generalises: if the engine did NOT compose keys, the
siblings would have to be named individually, and they would show up as named.

POSITIVE CONTROL
----------------
The census must find the ConnectArrow RKT itself.  A scan that reports "nobody
names the other nineteen" while also failing to see the one reference we KNOW
exists is a blind instrument, and its null means nothing.  The run fails loudly
if that control does not fire.

A byte-level scan for the raw instance dwords was tried first and DISCARDED:
it reports hits for instance ids that do not ship at all (0x29F100E0,
0x29F103E0, ...), so it cannot distinguish a real reference from a coincidence
in compressed or audio data.  Structured decoding is used instead.

READ-ONLY.  Reads the game archives; writes nothing.

    python rkt_family_census.py
    python rkt_family_census.py --csv rkt-census.csv
"""

import argparse
import collections
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import dbpfcore
from dbpfcore import GAME, T_S3D, T_EXEMPLAR, T_COHORT
from s3d_family import (FAMILY_BASE, S3D_GROUP, family_instances, variant_tag)

# ResourceKeyType property ids.  SC4 uses 0x27812820..0x2781282F for the
# "which model" slots; the row-15 exemplar uses 0x27812821.
RKT_IDS = tuple(range(0x27812820, 0x27812830))

EXEMPLAR_TGI = (T_EXEMPLAR, 0xC977C536, 0x29F10000)
ARROW_RKT_ID = 0x27812821


def collect(game=None):
    """Every RKT reference to an S3D in the install.

    Yields dicts.  Two readings of each RKT property are recorded, because the
    RKT value layout varies by form and guessing it would be its own error:

      strict   -- the property holds exactly three uint32s and the first is the
                  S3D type id, so it is unambiguously one TGI.
      scanned  -- the S3D type id appears at some index k and (k+1, k+2) are
                  read as group and instance.  Wider net, some false positives.
    """
    out = []
    stats = collections.Counter()
    for path in dbpfcore.discover_archives(game or GAME):
        arc = dbpfcore.Archive(path)
        for entry in arc.index:
            if entry[0] not in (T_EXEMPLAR, T_COHORT):
                continue
            stats["records"] += 1
            try:
                data, _qfs, _listed = arc.payload(entry)
                _parent, props = dbpfcore.decode_exemplar(data)
            except Exception:
                stats["undecodable"] += 1
                continue
            stats["decoded"] += 1
            for pid in RKT_IDS:
                if pid not in props:
                    continue
                name, vals = props[pid]
                if name != "Uint32":
                    continue
                stats["rkt_props"] += 1
                for k in range(len(vals) - 2):
                    if vals[k] != T_S3D:
                        continue
                    out.append({
                        "archive": arc.name,
                        "owner_type": entry[0],
                        "owner_instance": entry[2],
                        "prop": pid,
                        "index": k,
                        "strict": (len(vals) == 3 and k == 0),
                        "group": vals[k + 1],
                        "instance": vals[k + 2],
                    })
        arc.close()
    return out, stats


def s3d_universe(game=None):
    """{(group, instance)} for every S3D record that ships, anywhere."""
    u = set()
    for path in dbpfcore.discover_archives(game or GAME):
        arc = dbpfcore.Archive(path)
        for (t, g, i, off, size) in arc.index:
            if t == T_S3D:
                u.add((g, i))
        arc.close()
    return u


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--game", default=GAME)
    ap.add_argument("--csv", help="write every RKT->S3D reference to this file")
    args = ap.parse_args(argv)

    refs, stats = collect(args.game)
    ships = s3d_universe(args.game)
    print("exemplar/cohort records seen : %d" % stats["records"])
    print("  decoded                    : %d" % stats["decoded"])
    print("  undecodable (text/other)   : %d" % stats["undecodable"])
    print("RKT properties of type Uint32: %d" % stats["rkt_props"])
    print("RKT references naming an S3D : %d  (strict 3-value form: %d)"
          % (len(refs), sum(1 for r in refs if r["strict"])))
    print("S3D records shipped anywhere : %d" % len(ships))

    resolved = sum(1 for r in refs if (r["group"], r["instance"]) in ships)
    print("references that resolve to a real S3D record: %d/%d"
          % (resolved, len(refs)))

    # ---- POSITIVE CONTROL ----
    print("\n=== POSITIVE CONTROL ===")
    ctrl = [r for r in refs
            if r["owner_instance"] == EXEMPLAR_TGI[2]
            and r["prop"] == ARROW_RKT_ID
            and r["group"] == S3D_GROUP
            and r["instance"] == FAMILY_BASE]
    print("  the row-15 exemplar's own RKT 0x%08X -> "
          "{0x%08X, 0x%08X, 0x%08X}: %s"
          % (ARROW_RKT_ID, T_S3D, S3D_GROUP, FAMILY_BASE,
             "FOUND (%d)" % len(ctrl) if ctrl else "NOT FOUND"))
    if not ctrl:
        print("  the scan cannot see the one reference we know exists -- every")
        print("  null below is meaningless.  ABORTING.")
        return 1
    for r in ctrl:
        print("  owner: %s exemplar I=0x%08X, strict 3-value form=%s"
              % (r["archive"], r["owner_instance"], r["strict"]))

    # ---- Q1 ----
    print("\n=== Q1  IS ANY OF THE TWENTY NAMED BY ANY RKT? ===")
    fam = set(family_instances())
    by_inst = collections.defaultdict(list)
    for r in refs:
        if r["group"] == S3D_GROUP and r["instance"] in fam:
            by_inst[r["instance"]].append(r)
    named = 0
    for inst in family_instances():
        rs = by_inst.get(inst, [])
        named += 1 if rs else 0
        print("  0x%08X %-4s  named by %d RKT reference(s)%s"
              % (inst, variant_tag(inst), len(rs),
                 "" if not rs else "  <- " + ", ".join(
                     "%s exemplar 0x%08X prop 0x%08X"
                     % (x["archive"], x["owner_instance"], x["prop"]) for x in rs)))
    print("  --> %d of the twenty are named by an RKT; %d are not."
          % (named, 20 - named))

    # ---- Q2 ----
    print("\n=== Q2  IS 'NAME THE BASE ONLY' THE INSTALL-WIDE PATTERN? ===")
    strict = [r for r in refs if r["strict"]]
    bases = {(r["group"], r["instance"]) for r in strict
             if (r["instance"] & 0xFFF) == 0}
    named_keys = {(r["group"], r["instance"]) for r in strict}
    print("  strict RKT references naming an S3D          : %d" % len(strict))
    print("  distinct keys named                          : %d" % len(named_keys))
    print("  of those, keys whose low 12 bits are zero    : %d" % len(bases))
    dist = collections.Counter()
    sib_total = sib_named = 0
    for (g, i) in bases:
        n = 0
        for z in range(5):
            for r in range(4):
                k = (g, i + z * 0x100 + r * 0x10)
                if k in ships:
                    n += 1
                    if (z, r) != (0, 0):
                        sib_total += 1
                        if k in named_keys:
                            sib_named += 1
        dist[n] += 1
    print("  how many of the 20 zoom/rotation siblings ship, per named base:")
    for n in sorted(dist, reverse=True):
        bar = "#" * min(60, dist[n] * 60 // max(dist.values()))
        print("    %2d siblings : %5d bases  %s" % (n, dist[n], bar))
    full = dist.get(20, 0)
    print("  bases with the FULL family of 20 present : %d of %d (%.1f%%)"
          % (full, len(bases), 100.0 * full / max(1, len(bases))))
    print("  non-base siblings that ship              : %d" % sib_total)
    print("  ...of those, ever named by any strict RKT: %d (%.2f%%)"
          % (sib_named, 100.0 * sib_named / max(1, sib_total)))

    print("\n=== CONCLUSION ===")
    if named == 1 and sib_total > 0 and sib_named * 20 < sib_total:
        print("  The ConnectArrow RKT names ONLY the base 0x29F10000, and that is")
        print("  the install-wide convention, not a quirk of this one exemplar:")
        print("  %d sibling S3Ds ship that no RKT anywhere names, so the engine"
              % sib_total)
        print("  must compose the real key at draw time from")
        print("      instance = RKT base + (zoom-1)*0x100 + rotation*0x10")
        print("  which is exactly the arithmetic the twenty models' own embedded")
        print("  names spell out (..._Z1S through ..._Z5E).")
        print("  => Overriding the single RKT-named record covers ONE camera")
        print("     position out of twenty.  The override must cover all twenty.")
    else:
        print("  Pattern did not come out as expected -- read the tables above")
        print("  rather than trusting this summary line.")

    if args.csv:
        import csv
        with open(args.csv, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["archive", "owner_type", "owner_instance", "prop",
                        "value_index", "strict", "s3d_group", "s3d_instance",
                        "resolves"])
            for r in refs:
                w.writerow(["%s" % r["archive"], "0x%08X" % r["owner_type"],
                            "0x%08X" % r["owner_instance"], "0x%08X" % r["prop"],
                            r["index"], r["strict"], "0x%08X" % r["group"],
                            "0x%08X" % r["instance"],
                            (r["group"], r["instance"]) in ships])
        print("\nwrote %s (%d rows)" % (args.csv, len(refs)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
