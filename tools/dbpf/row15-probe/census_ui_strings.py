#!/usr/bin/env python3
r"""Census every string reference in the live .UI corpus.

Reads the type-0x00000000 records straight out of the shipped archives (not a
snapshot folder), parses the text ones into a control tree, and writes:

  ui-controls.csv     one row per <LEGACY> control, with its full ancestor
                      chain, its inline caption (if any) and every *res= TGI
                      reference it makes
  ui-strres.csv       one row per (attribute, group, instance) string-resource
                      reference, with the number of DISTINCT consumers

Read-only on the game install; writes only into this directory.
"""
import codecs
import collections
import csv
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dbpfcore as D                                          # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))

TAG = re.compile(rb"<(/?)(LEGACY|CHILDREN)\b([^>]*)>", re.I)
# attr=value  where value is "quoted", {a,b}, (a,b,c,d) or a bare token
ATTR = re.compile(r'(\w+)=("(?:[^"]*)"|\{[^}]*\}|\([^)]*\)|[^\s>]*)')
RESREF = re.compile(r"^\{([0-9a-fA-F]+),([0-9a-fA-F]+)\}$")


def parse_ui(text):
    """Yield (idx, parent_idx, attrs) for every <LEGACY> tag.

    The tree is rebuilt from the <CHILDREN> nesting, and every control gets a
    SEQUENTIAL index -- ids repeat and are sometimes absent, so an id is not a
    key.  A control's parent is the last control opened at the enclosing
    depth.
    """
    depth = 0
    last_at_depth = {}
    out = []
    for m in TAG.finditer(text.encode("latin-1")):
        closing = m.group(1) == b"/"
        kind = m.group(2).decode().upper()
        body = m.group(3).decode("latin-1")
        if kind == "CHILDREN":
            depth += -1 if closing else 1
            continue
        if closing:
            continue
        attrs = {}
        for a in ATTR.finditer(body):
            k = a.group(1).lower()
            v = a.group(2)
            if v.startswith('"'):
                v = v[1:-1]
            attrs[k] = (attrs[k] + "|" + v) if k in attrs else v
        idx = len(out)
        parent = last_at_depth.get(depth - 1, -1) if depth else -1
        last_at_depth[depth] = idx
        out.append((idx, parent, depth, attrs))
    return out


def main():
    ctrl_rows = []
    refs = collections.defaultdict(list)        # (attr,g,i) -> [consumer key]
    n_text = n_bin = 0
    for p in D.discover_archives():
        a = D.Archive(p)
        for e in a.by_type(D.T_UI):
            buf, _q, _l = a.payload(e)
            body = buf
            if body[:3] == codecs.BOM_UTF8:      # one record ships a UTF-8 BOM
                body = body[3:]                  # (96A006B0/CA551016)
            if not body.lstrip()[:1] in (b"#", b"<"):
                n_bin += 1
                continue
            n_text += 1
            text = body.decode("latin-1")
            ui_key = "%s:%08X_%08X" % (a.name, e[1], e[2])
            for idx, parent, depth, attrs in parse_ui(text):
                row = dict(ui=ui_key, ui_group="%08X" % e[1],
                           ui_inst="%08X" % e[2], depth=depth,
                           idx=idx, parent=parent,
                           id=attrs.get("id", ""), clsid=attrs.get("clsid", ""),
                           iid=attrs.get("iid", ""), area=attrs.get("area", ""),
                           visible=attrs.get("winflag_visible", ""),
                           caption=attrs.get("caption", ""),
                           has_caption="caption" in attrs)
                for k, v in attrs.items():
                    if k.endswith("res") or k in ("image", "tip"):
                        row[k] = v
                        m = RESREF.match(v)
                        if m:
                            g = int(m.group(1), 16)
                            i = int(m.group(2), 16)
                            refs[(k, g, i)].append("%s#%d" % (ui_key, idx))
                ctrl_rows.append(row)
        a.close()

    cols = ["ui", "ui_group", "ui_inst", "idx", "parent", "depth", "id", "clsid",
            "iid", "area", "visible", "has_caption", "caption",
            "captionres", "tipres", "iconres", "tip", "image"]
    with open(os.path.join(HERE, "ui-controls.csv"), "w", newline="",
              encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in ctrl_rows:
            w.writerow(r)

    with open(os.path.join(HERE, "ui-strres.csv"), "w", newline="",
              encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["attr", "group", "instance", "n_refs", "n_distinct_consumers",
                    "consumers"])
        for (k, g, i), cons in sorted(refs.items()):
            w.writerow([k, "%08X" % g, "%08X" % i, len(cons),
                        len(set(cons)), ";".join(sorted(set(cons)))])

    print("text .UI records parsed: %d   non-text skipped: %d" % (n_text, n_bin))
    print("controls: %d   distinct resource refs: %d" % (len(ctrl_rows), len(refs)))
    attrs = collections.Counter(k for (k, _g, _i) in refs)
    print("ref attributes:", attrs.most_common())


if __name__ == "__main__":
    main()
