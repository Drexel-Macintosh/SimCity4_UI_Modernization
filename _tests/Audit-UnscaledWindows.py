#!/usr/bin/env python3
"""
Audit-UnscaledWindows.py - find UI windows the scaler MISSED.

WHY THIS EXISTS (2026-07-28): two founded-city god-mode blockers in one session
were both windows that a stale research note had dismissed as
"hidden/inert/frozen template/do not touch", so they were on a skip list and
rendered at stock 1x while everything around them was 2x. Reading notes to find
more of those is exactly the method that failed. This finds them from DATA:

  live geometry (SC4UIScale.log full-tree dump)  vs
  stock geometry (the extracted .UI scripts)

Any VISIBLE window whose live size still equals its STOCK size, while the UI is
running at 2x, is a miss. Any window at 4x is double-scaled.

Usage:
    python Audit-UnscaledWindows.py [--log PATH] [--scripts DIR] [--factor 2.0]

Reads the LAST full-tree dump in the log, so play into the state you want to
audit (e.g. founded city + god mode), quit, then run this.
"""
import argparse
import os
import re
import sys
from collections import defaultdict

# "UI       id=0xAA231508 pos(260,348) size(880x456) children=4 vis=0 en=1"
LIVE_RE = re.compile(
    r"UI(\s+)id=0x([0-9A-Fa-f]{8}) pos\((-?\d+),(-?\d+)\) size\((\d+)x(\d+)\) "
    r"children=(\d+) vis=(\d)"
)
# <LEGACY ... id=0xca2aedc0 ... area=(270,783,1027,826) ...>
SCRIPT_RE = re.compile(r"id=0x([0-9A-Fa-f]{8})(.*?)area=\((-?\d+),(-?\d+),(-?\d+),(-?\d+)\)")


def load_stock(scripts_dir):
    """id -> set of (w,h) stock sizes seen in any .UI script."""
    stock = defaultdict(set)
    for name in os.listdir(scripts_dir):
        if not name.lower().endswith(".ui"):
            continue
        # 0x08000600 is the native 800x600 layout dialect - a DIFFERENT design,
        # not a stock reference for the 96a006b0 tree. Skip it.
        if "08000600" in name:
            continue
        path = os.path.join(scripts_dir, name)
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except OSError:
            continue
        for m in SCRIPT_RE.finditer(text):
            wid = m.group(1).upper()
            # Generic placeholder ids (0x00000000..0x000000FF) are reused across
            # hundreds of unrelated scripts with different areas, so matching by
            # id alone produces false hits. Skip them - a real miss will always
            # also show up via its named parent.
            if int(wid, 16) <= 0xFF:
                continue
            l, t, r, b = (int(m.group(i)) for i in (3, 4, 5, 6))
            w, h = r - l, b - t
            if w > 0 and h > 0:
                stock[wid].add((w, h))
    return stock


def all_dumps(log_path):
    """
    Every dump block in the log, concatenated, with per-block tree state.

    Scanning only the LAST dump can only ever audit the ONE state the player
    happened to be in when they quit. Mayor mode has many states (each toolbar
    page, budget, graphs, query...), so the useful workflow is: play a grand
    tour touching every panel, quit, then audit the whole session at once.
    """
    with open(log_path, "r", encoding="utf-8", errors="replace") as fh:
        lines = fh.readlines()
    wins = []
    for ln in lines:
        if "dump" in ln and "id=" not in ln:
            wins.append(None)          # block boundary - resets the tree walk
            continue
        m = LIVE_RE.search(ln)
        if m:
            wins.append({
                "depth": len(m.group(1)),
                "id": m.group(2).upper(),
                "x": int(m.group(3)), "y": int(m.group(4)),
                "w": int(m.group(5)), "h": int(m.group(6)),
                "kids": int(m.group(7)), "vis": int(m.group(8)),
            })
    # EFFECTIVE visibility. A window's own vis=1 means nothing if an ancestor
    # is hidden - that is why a naive pass reported hundreds of "visible"
    # windows that are really inside closed dialogs. Indentation gives the
    # tree, so walk it with a stack of (depth, effective_vis).
    #
    # EXCEPTION that matters here: several god/region roots report vis=0 while
    # their children genuinely draw. So also carry an "onscreen-ish" flag that
    # tolerates ONE vis=0 ancestor - those are exactly the windows this project
    # keeps getting burned by, and they must not be filtered away.
    stack = []
    out = []
    for w in wins:
        if w is None:
            stack = []            # new dump block
            continue
        while stack and stack[-1][0] >= w["depth"]:
            stack.pop()
        pvis = stack[-1][1] if stack else True
        pzero = stack[-1][2] if stack else 0
        w["eff_vis"] = bool(pvis and w["vis"])
        w["hidden_ancestors"] = pzero + (0 if w["vis"] else 1)
        stack.append((w["depth"], w["eff_vis"], w["hidden_ancestors"]))
        out.append(w)
    return out


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    proj = os.path.dirname(here)
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", default=os.path.expandvars(
        r"%USERPROFILE%\OneDrive\Documents\SimCity 4\Plugins\SC4UIScale.log"))
    ap.add_argument("--scripts", default=os.path.join(proj, "tools", "uiscripts", "extracted"))
    ap.add_argument("--factor", type=float, default=2.0)
    args = ap.parse_args()

    stock = load_stock(args.scripts)
    wins = all_dumps(args.log)
    if not wins:
        print("No full-tree dump found in the log. Set [UiSpike] LiveDumpMs>0 and replay.")
        return 2
    print(f"stock ids from scripts: {len(stock)}   live windows in last dump: {len(wins)}")

    f = args.factor
    unscaled, doubled_twice, odd = [], [], []
    matched = 0
    for w in wins:
        sizes = stock.get(w["id"])
        w["state"] = "?"
        if not sizes:
            continue
        matched += 1
        lw, lh = w["w"], w["h"]
        if any(lw == sw and lh == sh for sw, sh in sizes):
            w["state"] = "1x"
            unscaled.append(w)
        elif any(abs(lw - sw * f) < 2 and abs(lh - sh * f) < 2 for sw, sh in sizes):
            w["state"] = "2x"
        elif any(abs(lw - sw * f * f) < 3 and abs(lh - sh * f * f) < 3 for sw, sh in sizes):
            w["state"] = "4x"
            doubled_twice.append(w)
        else:
            w["state"] = "odd"
            odd.append((w, sorted(sizes)))
    print(f"matched to a stock size: {matched}\n")

    # Nearest ANCESTOR whose scale state we know. A 1x window sitting inside a
    # correctly-2x parent is the strongest possible signal: the container grew
    # and its content did not (the news-ticker bug - container 757x43 -> 1514x86
    # while all four children stayed stock).
    chain = []
    for w in wins:
        while chain and chain[-1]["depth"] >= w["depth"]:
            chain.pop()
        anc = next((a for a in reversed(chain) if a["state"] in ("1x", "2x", "4x")), None)
        w["parent_state"] = anc["state"] if anc else None
        w["parent_id"] = anc["id"] if anc else None
        chain.append(w)

    def show(title, rows, note):
        print("=" * 72)
        print(f"{title}  ({len(rows)})")
        print(note)
        print("=" * 72)
        for w in rows:
            flag = "ON-SCREEN" if w["eff_vis"] else f"hid_anc={w['hidden_ancestors']}"
            print(f"  {flag:<12} id=0x{w['id']} d{w['depth']:<3} "
                  f"pos({w['x']},{w['y']}) {w['w']}x{w['h']} kids={w['kids']}")
        print()

    # Only report what a user could actually SEE. Everything else is inside a
    # closed dialog and is stock-sized simply because it was never opened -
    # hundreds of those drowned the signal on the first run.
    def dedupe(rows):
        """One row per (id,size). The log dumps ~1/sec, so the same window
        recurs hundreds of times across a session; keep the most-visible
        sighting of each so the report stays readable."""
        best = {}
        for w in rows:
            key = (w["id"], w["w"], w["h"])
            cur = best.get(key)
            if cur is None or (w["eff_vis"], -w["hidden_ancestors"]) > \
                              (cur["eff_vis"], -cur["hidden_ancestors"]):
                best[key] = w
        return list(best.values())

    # A window seen at stock EARLY and correctly scaled LATER is not a miss -
    # it was just caught before the sweep reached it (the sweep runs ~250ms
    # after a panel is born). Only ids that were NEVER once seen at 2x in the
    # whole session are real. Without this, every panel in the game shows up.
    ever_scaled = {w["id"] for w in wins if w["state"] == "2x"}
    unscaled = [w for w in unscaled if w["id"] not in ever_scaled]
    print(f"ids ever seen correctly scaled this session: {len(ever_scaled)} "
          f"(those are excluded below)\n")

    unscaled = dedupe(unscaled)
    doubled_twice = dedupe(doubled_twice)
    onscreen = [w for w in unscaled if w["eff_vis"]]
    # STRONGEST SIGNAL: 1x content inside a 2x container.
    mismatch = [w for w in unscaled if w["parent_state"] == "2x"]
    # The god-toolbar signature: a top-level view child left at stock. Depth 7
    # is a direct child of the 3D view in the LiveDump indentation.
    toplevel = [w for w in unscaled if w["depth"] <= 7]
    for lst in (onscreen, mismatch, toplevel):
        lst.sort(key=lambda w: -(w["w"] * w["h"]))
    show("STILL AT STOCK 1x AND ON SCREEN", onscreen,
         "REAL MISSES: the user can see these at half size.")
    show("1x CONTENT INSIDE A 2x CONTAINER  <-- strongest signal", mismatch,
         "The container was scaled and its content was not. This is the news-ticker\n"
         "bug exactly. Usually a kRootOnlyScaleIds entry whose premise (the game\n"
         "re-lays its children each frame) does not actually hold.")
    show("TOP-LEVEL VIEW CHILD STILL AT STOCK  <-- god-toolbar signature", toplevel,
         "A panel the sweep never touched. Check the id skip-lists FIRST:\n"
         "kGodToolFlyoutIds makes the sweep skip outright; a vis=0 root needs to be\n"
         "in kGodPanelIds to be scaled at all. Both 2026-07-28 blockers were here.")
    show("DOUBLE-SCALED (4x)", doubled_twice,
         "Scaled twice - usually a static .UI dat AND the runtime sweep both\n"
         "acting on it. Needs the root in kNeverScaleIds.")
    if odd:
        print("=" * 72)
        print(f"SIZE DOES NOT MATCH ANY KNOWN MULTIPLE  ({len(odd)})")
        print("Often legitimately content-sized (text/list panes) - inspect.")
        print("=" * 72)
        for w, sizes in odd[:40]:
            flag = "VISIBLE" if w["vis"] else "vis=0  "
            print(f"  {flag} id=0x{w['id']} live {w['w']}x{w['h']}  stock {sizes}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
