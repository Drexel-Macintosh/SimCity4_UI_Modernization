#!/usr/bin/env python3
r"""Load-order canary candidates: a resource with ONE definition and ONE
consumer whose visibility rests on no unproven precedence rule.

Why images and not strings.  A `captionres=` on a control that also carries an
inline `caption=` needs captionres to WIN, and that precedence has never been
read out of the loader.  Only 3 of the 297 single-consumer captionres controls
in the whole stock corpus have no inline caption, and none of the three is
usable (one is the credits HTML blob, one points at a string that does not
exist, one points at a PNG).  An `image={g,i}` has NO inline alternative --
there is no way to embed a bitmap in a .UI script -- so the resource is the
only possible source and there is nothing to beat.

Filters, each re-checkable:
  1. exactly one .UI control in the whole live corpus references the image
  2. exactly one record defines that (group, instance) across all NINE
     shipped archives
  3. NO file anywhere in the live Plugins tree defines it -- otherwise the
     canary is a race with another mod (or with our own art pack, which does
     ship some of these)
  4. the consuming control's winflag_visible=yes
  5. the root window's winflag_visible is REPORTED, not filtered: a root
     flagged `no` is shown by code, which is a fact about the window, not
     proof that it never appears
  6. the instance id's dword hit count in SimCity 4.exe is REPORTED -- a
     code-bound image would be a second consumer

Read-only on the game install and on Plugins.
"""
import collections
import csv
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dbpfcore as D                                          # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
EXE = os.path.join(D.GAME, "Apps", "SimCity 4.exe")


def plugins_dir():
    if os.environ.get("SC4_PLUGINS"):
        return os.environ["SC4_PLUGINS"]
    for base in (os.path.expanduser(r"~\OneDrive\Documents\SimCity 4\Plugins"),
                 os.path.expanduser(r"~\Documents\SimCity 4\Plugins")):
        if os.path.isdir(base):
            return base
    raise SystemExit("no Plugins folder found")


def main():
    ctrls = list(csv.DictReader(open(os.path.join(HERE, "ui-controls.csv"),
                                     encoding="utf-8")))
    by = collections.defaultdict(dict)
    for r in ctrls:
        by[r["ui"]][int(r["idx"])] = r
    img = collections.defaultdict(list)
    for r in ctrls:
        v = r.get("image") or ""
        if v.startswith("{"):
            g, i = v.strip("{}").split(",")
            img[(int(g, 16), int(i, 16))].append(r)

    single = {k: v[0] for k, v in img.items() if len(v) == 1}

    defs = collections.defaultdict(list)
    for p in D.discover_archives():
        a = D.Archive(p)
        for e in a.index:
            if (e[1], e[2]) in single:
                defs[(e[1], e[2])].append((a.name, e[0], e[4]))
        a.close()

    PL = plugins_dir()
    plugin_owner = collections.defaultdict(list)
    n_arch = 0
    for root, _dirs, files in os.walk(PL):
        for fn in files:
            if not fn.lower().endswith((".dat", ".sc4lot", ".sc4desc",
                                        ".sc4model")):
                continue
            fp = os.path.join(root, fn)
            try:
                a = D.Archive(fp)
            except Exception:
                continue
            n_arch += 1
            for e in a.index:
                if (e[1], e[2]) in single:
                    plugin_owner[(e[1], e[2])].append(os.path.relpath(fp, PL))
            a.close()

    with open(EXE, "rb") as f:
        exe = f.read()

    rows = []
    for k, r in single.items():
        if len(defs.get(k, [])) != 1:
            continue
        if plugin_owner.get(k):
            continue
        if r["visible"] != "yes":
            continue
        root = by[r["ui"]][0]
        rows.append(dict(
            group="%08X" % k[0], instance="%08X" % k[1],
            bytes=defs[k][0][2], ui=r["ui"],
            root_id=root["id"], root_area=root["area"],
            root_visible=root["visible"],
            ctrl_id=r["id"], clsid=r["clsid"], area=r["area"],
            depth=r["depth"],
            exe_dword_hits=exe.count(struct.pack("<I", k[1])),
        ))
    rows.sort(key=lambda x: (-int(x["bytes"])))
    out = os.path.join(HERE, "canary-candidates.csv")
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print("plugin archives scanned: %d under %s" % (n_arch, PL))
    print("single-consumer images: %d" % len(single))
    print("...single definition, no plugin owner, control visible: %d -> %s"
          % (len(rows), out))
    print("...of those with root_visible=yes: %d"
          % sum(1 for r in rows if r["root_visible"] == "yes"))


if __name__ == "__main__":
    main()
