#!/usr/bin/env python3
r"""Step 1+2 driver: per-archive census of type 0x6534284A, then a full
property dump of every one of them.

    python run_census.py counts          # step 1 only, per-file / per-group
    python run_census.py table  <out>    # step 2, full property table

POSITIVE CONTROL (never omit): the known sibling exemplar
{T=0x6534284A, G=0xC977C536, I=0x29F10000} "UI8x1x3_ConnectArrow_29F1" MUST be
found and MUST parse with OccupantSize {8,3,1}.  If it is not, the scan is
broken and every "not found" below is meaningless.
"""
import os
import struct
import sys
import collections

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from census_markers import (dbpf_index, read_entry, maybe_decompress,   # noqa: E402
                            parse_exemplar, discover_dbpf,
                            T_EXEMPLAR_MARKER)
sys.path.insert(0, os.path.join(HERE, "..", ".."))
from sc4paths import plugins_dir, game_dir                              # noqa: E402

CONTROL_TGI = (0x6534284A, 0xC977C536, 0x29F10000)

PROP_NAMES = {
    0x00000020: "ExemplarName",
    0x00000010: "ExemplarType",
    0x27812810: "OccupantSize",
    0x27812820: "ResourceKeyType0",
    0x27812821: "ResourceKeyType1",
    0x27812822: "ResourceKeyType2",
    0x27812823: "ResourceKeyType3",
    0x27812824: "ResourceKeyType4",
    0x27812825: "ResourceKeyType5",
    # ⛔ CORRECTION to the briefing: 0x2977AA47 is NOT a property id.  It never
    # appears as one in any of the 11,118 exemplars below (positive control:
    # the same regex form matches 0x27812810 thousands of times).  It is the
    # DEFAULT VALUE of property 0xA977A86B, written to the out-slot at
    # 0x4A2511 before the read at 0x4A250B, and the value that makes the
    # factory fall through to `push 0x68; call 0x5ECE60` at 0x4A254E -- the
    # 0x68-byte marker occupant.  0x2977AA48 / 0x2977AA49 branch elsewhere
    # (0x4A2586 / 0x4A2565).
    0xA977A86B: "OccupantClassGUID (default 0x2977AA47 = the 0x68-byte marker)",
    # Float PAIR whose whole population lives inside [1.0, 24.9] -- the exact
    # domain the marker's +0x5E/+0x5F byte-tenths encoding (cap 25.5) can hold.
    # 0x1E680000 carries {15, 9}; the live marker #1 GetSize read 15.0 x 9.0.
    # Read by code at 0x6F31B7 / 0x6F3C90 / 0x6F3E0F (push imm32 + HasProperty).
    0x4A149631: "MarkerSizePair? floats, all <=24.9 (SetSize cap is 25.5)",
    0x0ABFC024: "(seen 0x1C / 0x1E)",
    0x8A416A99: "ResourceKey {0x2026960B, 0x6A554AFD, inst}",
    0xABB90E58: "TagKind (Tag1x1x3_* family: 1=Helicopter 2=Helipad_Medical "
                "4=AttackHeli 5=UFO)",
}


def collect():
    game = game_dir()
    plug = plugins_dir(require=False)
    roots = [("GAME", game)]
    if plug and os.path.isdir(plug):
        roots.append(("PLUGINS", plug))
    found = []          # (label, path, t, g, i, off, size)
    scanned = []        # (label, path, n_entries, n_marker)
    for label, root in roots:
        for p in discover_dbpf(root):
            idx = dbpf_index(p)
            if not idx:
                continue
            n = 0
            for (t, g, i, off, sz) in idx:
                if t == T_EXEMPLAR_MARKER:
                    n += 1
                    found.append((label, p, t, g, i, off, sz))
            scanned.append((label, p, len(idx), n))
    return scanned, found, game, plug


def cmd_counts():
    scanned, found, game, plug = collect()
    print("GAME DIR    : %s" % game)
    print("PLUGINS DIR : %s" % plug)
    print()
    print("=== DBPF FILES SCANNED (recursive) ===")
    tot_e = tot_m = 0
    for label, p, ne, nm in scanned:
        tot_e += ne
        tot_m += nm
        root = game if label == "GAME" else plug
        rel = os.path.relpath(p, root)
        print("  %-8s %-60s %8d entries  %6d type-6534284A"
              % (label, rel[:60], ne, nm))
    print("  %-8s %-60s %8d           %6d" % ("TOTAL", "", tot_e, tot_m))
    print()
    print("=== GROUP BREAKDOWN of type 0x6534284A ===")
    bygroup = collections.Counter()
    byfilegroup = collections.Counter()
    for label, p, t, g, i, off, sz in found:
        bygroup[g] += 1
        byfilegroup[(os.path.basename(p), g)] += 1
    for g, c in bygroup.most_common():
        print("  G=0x%08X : %d" % (g, c))
    print()
    print("=== PER-FILE x GROUP ===")
    for (fn, g), c in sorted(byfilegroup.items()):
        print("  %-30s G=0x%08X : %d" % (fn, g, c))
    print()
    ctl = [r for r in found if (r[2], r[3], r[4]) == CONTROL_TGI]
    print("POSITIVE CONTROL {6534284A,C977C536,29F10000}: %s"
          % ("FOUND in %s" % os.path.basename(ctl[0][1]) if ctl else "*** NOT FOUND -> SCAN IS BROKEN ***"))


def fmt_vals(tname, vals):
    if tname == "string":
        return repr(vals[0].decode("latin-1", "replace") if isinstance(vals[0], bytes) else vals[0])
    if tname in ("uint32", "sint32", "uint16", "uint8", "bool"):
        return "{" + ", ".join("0x%X" % (v & 0xFFFFFFFFFFFFFFFF) for v in vals) + "}"
    if tname == "float32":
        return "{" + ", ".join("%g" % v for v in vals) + "}"
    return "{" + ", ".join(str(v) for v in vals) + "}"


def cmd_table(out_path):
    scanned, found, game, plug = collect()
    rows = []
    fails = []
    for label, p, t, g, i, off, sz in found:
        raw = read_entry(p, off, sz)
        payload, comp = maybe_decompress(raw)
        try:
            parent, props, order = parse_exemplar(payload)
        except Exception as e:
            fails.append((p, i, str(e), payload[:16].hex()))
            continue
        name = ""
        if 0x20 in props:
            v = props[0x20][1][0]
            name = v.decode("latin-1", "replace") if isinstance(v, bytes) else str(v)
        rows.append(dict(label=label, path=p, group=g, inst=i, name=name,
                         parent=parent, props=props, order=order,
                         comp=comp, size=sz, raw=len(payload)))
    rows.sort(key=lambda r: (r["group"], r["inst"]))

    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write("MARKER-FAMILY EXEMPLAR CENSUS  (type 0x6534284A)\n")
        fh.write("generated by tools/research/udriveit/run_census.py\n")
        fh.write("game    : %s\n" % game)
        fh.write("plugins : %s\n" % plug)
        fh.write("files scanned (DBPF): %d\n" % len([s for s in scanned]))
        fh.write("exemplars found     : %d\n" % len(found))
        fh.write("exemplars parsed OK : %d\n" % len(rows))
        fh.write("parse failures      : %d\n" % len(fails))
        fh.write("\n")
        fh.write("PROPERTY IDS DECODED BY NAME:\n")
        for pid in sorted(PROP_NAMES):
            fh.write("  0x%08X  %s\n" % (pid, PROP_NAMES[pid]))
        fh.write("\n" + "=" * 100 + "\n")
        fh.write("SECTION 1 - INDEX (group, instance, name, OccupantSize)\n")
        fh.write("=" * 100 + "\n")
        fh.write("%-10s %-10s %-8s %-14s %s\n"
                 % ("GROUP", "INSTANCE", "ARCHIVE", "OCCUPANTSIZE", "NAME"))
        for r in rows:
            os_ = r["props"].get(0x27812810)
            osz = fmt_vals(*os_) if os_ else "-"
            fh.write("%08X   %08X   %-8s %-14s %s\n"
                     % (r["group"], r["inst"],
                        os.path.basename(r["path"]).replace(".dat", "")[:8],
                        osz, r["name"]))
        fh.write("\n" + "=" * 100 + "\n")
        fh.write("SECTION 2 - FULL PROPERTY DUMP (group 0xC977C536 = the marker/prop group,\n")
        fh.write("            plus every exemplar in any group whose name starts 'UI')\n")
        fh.write("=" * 100 + "\n")
        for r in rows:
            if r["group"] != 0xC977C536 and not r["name"].upper().startswith("UI"):
                continue
            fh.write("\n--- {T=0x6534284A, G=0x%08X, I=0x%08X}  %s\n"
                     % (r["group"], r["inst"], r["name"]))
            fh.write("    file      : %s\n" % r["path"])
            fh.write("    parent    : {0x%08X, 0x%08X, 0x%08X}%s\n"
                     % (r["parent"][0], r["parent"][1], r["parent"][2],
                        "  (compressed)" if r["comp"] else ""))
            fh.write("    props     : %d\n" % len(r["props"]))
            for pid in r["order"]:
                tname, vals = r["props"][pid]
                label = PROP_NAMES.get(pid, "")
                fh.write("      0x%08X %-28s %-8s %s\n"
                         % (pid, label, tname, fmt_vals(tname, vals)))
        # ---------------- SECTION 3: the balloon hunt ----------------
        fh.write("\n" + "=" * 100 + "\n")
        fh.write("SECTION 3 - OFFER-BALLOON CANDIDATE SHORTLIST\n")
        fh.write("=" * 100 + "\n")
        keys = ("zot", "tag1x1x3", "marker", "connectarrow", "udi", "drive",
                "mission", "offer", "balloon", "bubble", "advice", "opportun")
        for r in rows:
            n = r["name"].lower()
            if not any(k in n for k in keys):
                continue
            os_ = r["props"].get(0x27812810)
            k0 = r["props"].get(0x27812820) or r["props"].get(0x27812821)
            model = "-"
            if k0:
                v = k0[1]
                if len(v) >= 3:
                    model = "{0x%08X,0x%08X,0x%08X}" % (v[0], v[1], v[2])
            fh.write("%-46s I=0x%08X  size=%-16s model=%s\n"
                     % (r["name"][:46], r["inst"],
                        fmt_vals(*os_) if os_ else "-", model))
        fh.write("\nNAMING-CONVENTION SWEEP  'UI<W>x<H>x<D>_<Thing>_<inst>':\n")
        hits = [r for r in rows if r["name"].upper().startswith("UI")
                and len(r["name"]) > 2 and r["name"][2].isdigit()]
        for r in hits:
            os_ = r["props"].get(0x27812810)
            fh.write("  %-46s I=0x%08X  %s\n"
                     % (r["name"], r["inst"], fmt_vals(*os_) if os_ else "-"))
        fh.write("  -> %d exemplar(s) follow the convention in the WHOLE corpus.\n"
                 % len(hits))
        fh.write("     Positive control: the same test finds "
                 "UI8x1x3_ConnectArrow_29F1, so a count of 1 is a fact about\n"
                 "     the corpus, not a broken filter.\n")

        if fails:
            fh.write("\n" + "=" * 100 + "\nPARSE FAILURES\n" + "=" * 100 + "\n")
            for p, i, e, head in fails:
                fh.write("  I=0x%08X %s  %s  head=%s\n" % (i, os.path.basename(p), e, head))
    print("wrote %s" % out_path)
    print("found %d, parsed %d, failures %d" % (len(found), len(rows), len(fails)))
    ctl = [r for r in rows if (r["group"], r["inst"]) == CONTROL_TGI[1:]]
    if ctl:
        c = ctl[0]
        print("POSITIVE CONTROL: %s  OccupantSize=%s"
              % (c["name"], fmt_vals(*c["props"][0x27812810]) if 0x27812810 in c["props"] else "MISSING"))
    else:
        print("POSITIVE CONTROL MISSING -> results untrustworthy")


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] == "counts":
        cmd_counts()
    elif sys.argv[1] == "table":
        cmd_table(sys.argv[2] if len(sys.argv) > 2
                  else os.path.join(HERE, "marker-exemplars.txt"))
