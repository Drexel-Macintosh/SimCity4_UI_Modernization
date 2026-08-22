#!/usr/bin/env python3
"""Scan every Documents plugin for menu items that CANNOT be reached in game.

THE POLICE BUG, GENERALIZED (2026-07-29). With memo.submenus.dll + CAM, an
item's menu placement is its submenu-parent list (property 0xAA1DD399, the
alternate Occupant Groups list - authoritative source: submenus-dll
MenuIds.h `itemSubmenuParentPropId`). CAM re-parents many STOCK buildings
into CAM submenus, both by overriding exemplars and via EXEMPLAR PATCH
resources (type 0xE86B1EEF; targets in property 0x0062E78A as GroupID,
InstanceID pairs). The submenus DLL then HIDES any submenu button it deems
empty at startup (listed in memo.submenus.log). An item whose parent list
points ONLY at hidden or undefined submenus is unreachable everywhere -
e.g. the small Police Station and Jail vanishing from the Police menu.

This scan rebuilds the whole graph offline and reports every such item:

  1. Extract exemplars (0x6534284A) + patches (0xE86B1EEF) from every dat
     under Documents\Plugins (excluding our own z_/zzz packages).
  2. Parse BOTH exemplar formats (binary EQZB/CQZB and text) for:
     name (0x20), Item Button ID (0x8A2602BB, defines a submenu button),
     submenu parents (0xAA1DD399), occupant groups (0xAA1DD396).
  3. Apply patches: a patch's property values override/extend its targets'.
  4. hidden = the "Hiding empty submenu" list parsed from memo.submenus.log.
     defined = every Item Button ID seen (submenu buttons) + physical menu
     ids from MenuIds.h.
  5. UNREACHABLE item = has a 0xAA1DD399 list whose every entry is hidden
     or undefined. Reported grouped by the dead parent, with names.

Run from tools/itemicons:  python scan_unreachable_items.py [--refresh]
(--refresh re-extracts; otherwise reuses _work/scan-cache/.)
"""
import glob
import os
import re
import struct
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from parse_exemplars import parse_exemplar

import sys as _sys
_TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _TOOLS not in _sys.path:
    _sys.path.insert(0, _TOOLS)
from sc4paths import plugins_dir     # noqa: E402
# Resolved, not hard-coded: $SC4_PLUGINS, else the shell's Documents,
# else the OneDrive-redirected or plain %USERPROFILE% variant. See
# tools/sc4paths.py for why a literal path here was a bug, not a shortcut.
PLUGINS = plugins_dir(require=True)
MEMOLOG = os.path.join(PLUGINS, "memo.submenus.log")
EXTRACT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "..", "dbpf", "DbpfExtract.exe")
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "_work", "scan-cache")

PROP_NAME = 0x20
PROP_BUTTON_ID = 0x8A2602BB
PROP_SUBMENU_PARENT = 0xAA1DD399
PROP_OCC_GROUPS = 0xAA1DD396
PROP_PATCH_TARGETS = 0x0062E78A

# physical menu roots (submenus-dll MenuIds.h) - always visible
ROOTS = {
    0x4A22EA06, 0x29920899, 0xA998AF42, 0xC998AF00, 0x6999BF56, 0x31, 0x29,
    0x299237BF, 0xE99234B3, 0xA99234A6, 0x35, 0x39, 0x40, 0x37, 0x38, 0x42,
    0x89DD5405, 0x09930709, 0x34, 0x3,
}

RX_TEXT_PROP = None  # built per property id


def text_prop_values(data, prop_id):
    """All uint32 values of prop_id in a TEXT exemplar/patch."""
    rx = re.compile(
        (r'0x%08X[^\r\n]*?=[^\r\n]*?\{([^}\r\n]*)\}' % prop_id).encode(),
        re.I)
    vals = []
    for m in rx.findall(data):
        for tok in m.split(b','):
            tok = tok.strip()
            if tok.lower().startswith(b'0x'):
                try:
                    vals.append(int(tok, 16))
                except ValueError:
                    pass
    return vals


def text_prop_string(data, prop_id):
    m = re.search((r'0x%08X[^\r\n]*?=[^\r\n]*?\{"([^"]*)"\}' % prop_id).encode(), data, re.I)
    return m.group(1).decode('ascii', 'replace') if m else None


def parse_any(data):
    """-> dict propId -> list of int values (+ '_name')."""
    out = {}
    if data[:4] in (b'EQZB', b'CQZB'):
        try:
            props = parse_exemplar(data)
        except Exception:
            return out
        for pid in (PROP_BUTTON_ID, PROP_SUBMENU_PARENT, PROP_OCC_GROUPS,
                    PROP_PATCH_TARGETS):
            if pid in props:
                out[pid] = [v & 0xFFFFFFFF for v in props[pid]
                            if isinstance(v, int)]
        if PROP_NAME in props and props[PROP_NAME] and \
                isinstance(props[PROP_NAME][0], bytes):
            out['_name'] = props[PROP_NAME][0].decode('ascii', 'replace')
    else:
        for pid in (PROP_BUTTON_ID, PROP_SUBMENU_PARENT, PROP_OCC_GROUPS,
                    PROP_PATCH_TARGETS):
            v = text_prop_values(data, pid)
            if v:
                out[pid] = v
        n = text_prop_string(data, PROP_NAME)
        if n:
            out['_name'] = n
    return out


def main():
    refresh = '--refresh' in sys.argv
    dats = [p for p in glob.glob(os.path.join(PLUGINS, '**', '*.dat'),
                                 recursive=True)
            if 'z_SC4UIScale' not in p and 'zzz-SC4UIScale' not in p]
    dats += [p for p in glob.glob(os.path.join(PLUGINS, '*.dat'))
             if 'z_SC4UIScale' not in p]
    dats = sorted(set(dats))
    print(f"plugin dats: {len(dats)}")

    if refresh or not os.path.isdir(CACHE):
        import shutil
        if os.path.isdir(CACHE):
            shutil.rmtree(CACHE)
        for i, d in enumerate(dats):
            o = os.path.join(CACHE, f'd{i}')
            os.makedirs(o)
            with open(os.path.join(o, 'SOURCE.txt'), 'w') as fh:
                fh.write(d)
            for t in ('0x6534284A', '0xE86B1EEF'):
                subprocess.run([EXTRACT, d, o, t], capture_output=True)

    # ---- parse everything -------------------------------------------------
    defined = {}      # submenu button id -> name
    items = []        # (tgi, name, parents, src)
    patches = []      # (targets [(g,i)], parents, src)
    for datdir in sorted(glob.glob(os.path.join(CACHE, 'd*'))):
        src = open(os.path.join(datdir, 'SOURCE.txt')).read().strip()
        short = src.split('Plugins')[-1].lstrip('\\/')
        for p in glob.glob(os.path.join(datdir, 'T-*')):
            base = os.path.basename(p)
            data = open(p, 'rb').read()
            props = parse_any(data)
            if not props:
                continue
            name = props.get('_name', base)
            if base.lower().startswith('t-e86b1eef'):
                tg = props.get(PROP_PATCH_TARGETS, [])
                pairs = list(zip(tg[0::2], tg[1::2]))
                if PROP_SUBMENU_PARENT in props:
                    patches.append((pairs, props[PROP_SUBMENU_PARENT],
                                    name, short))
                continue
            if PROP_BUTTON_ID in props and props[PROP_BUTTON_ID]:
                defined[props[PROP_BUTTON_ID][0]] = name
            gi = base.split('_G-')[1]
            g = int(gi.split('_I-')[0], 16)
            inst = int(gi.split('_I-')[1].split('.')[0], 16)
            items.append(((g, inst), name,
                          props.get(PROP_SUBMENU_PARENT, []), short))

    # ---- apply patches (last wins per target) -----------------------------
    patched = {}
    for pairs, parents, pname, psrc in patches:
        for gi in pairs:
            patched[gi] = (parents, pname, psrc)

    hidden = {}
    for line in open(MEMOLOG, encoding='utf-8', errors='replace'):
        m = re.search(r'Button ID (0x[0-9A-Fa-f]+): (\S+)', line)
        if m and 'Hiding empty submenu' in line:
            hidden[int(m.group(1), 16)] = m.group(2)

    visible = (set(defined) | ROOTS) - set(hidden)
    print(f"submenu buttons defined: {len(defined)}  hidden: {len(hidden)}  "
          f"patches: {len(patches)} covering {len(patched)} targets")

    # ---- verdicts ---------------------------------------------------------
    dead = {}
    for tgi, name, parents, src in items:
        if tgi in patched:
            parents = patched[tgi][0]
        if not parents:
            continue
        if all(p not in visible for p in parents):
            for p in parents:
                dead.setdefault(p, []).append((name, src))
    # patch targets that are STOCK exemplars (not in any plugin dat) also
    # need checking - they never appeared in `items`
    seen_tgis = {t for t, _, _, _ in items}
    for gi, (parents, pname, psrc) in patched.items():
        if gi in seen_tgis:
            continue
        if parents and all(p not in visible for p in parents):
            for p in parents:
                dead.setdefault(p, []).append(
                    (f"STOCK exemplar G-{gi[0]:08x} I-{gi[1]:08x} "
                     f"(via patch {pname})", psrc))

    if not dead:
        print("\nNO UNREACHABLE ITEMS - every parented item has a visible "
              "submenu.")
        return 0
    total = sum(len(v) for v in dead.values())
    print(f"\nUNREACHABLE ITEMS: {total}, behind {len(dead)} dead submenus\n")
    for p in sorted(dead):
        label = hidden.get(p) or defined.get(p) or "UNDEFINED SUBMENU"
        state = "HIDDEN-empty" if p in hidden else (
            "defined but unlisted" if p in defined else "NOT DEFINED")
        print(f"0x{p:08X}  {label}  [{state}]  - {len(dead[p])} item(s):")
        for name, src in sorted(set(dead[p]))[:12]:
            print(f"    {name}   [{src}]")
        if len(set(dead[p])) > 12:
            print(f"    ... and {len(set(dead[p])) - 12} more")
        print()
    return 0


if __name__ == '__main__':
    sys.exit(main())
