#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""
emu_trip_legend.py - ADJUDICATING probe for the Trip Types legend (task #54).

WHAT THIS SETTLES
-----------------
The coverage census lists 0x6BB92BCB (script I-abb0120f, "Trip Types" legend,
181x296) as THE ONE GENUINE LIVE DEFECT: "2x art ships but the staged .UI still
carries the 1x root area, and the id is in NO runtime list".

That framing rests on an id that DOES NOT EXIST AT RUNTIME.

MEASURED, from the retained log
_working-backup\GOLDEN-2x-DirectX-2026-07-22\Documents-Plugins\SC4UIScale.log:

    UI id=0xEA659793 ... children=13            <- view host
    UI   id=0x0BB0F5E7 pos(2243,1392) size(152x203) children=9   <- legend BODY
    UI   id=0x6BB92BCA pos(2356,1558) size(34x32)  children=1    <- minimised bar
    UiSpike: panel 0x0BB0F5E7 (2243,1392 152x203) -> (2086,1184 304x406)
    UiSpike: region panel 0x0BB0F5E7 - 10 windows scaled.
    UiSpike: panel 0x6BB92BCA (2356,1558 34x32) -> (2312,1516 68x64)

0x6BB92BCB never appears. The game PROMOTES the script root's two children to
direct view children and discards the design container. Both promoted roots are
named in kRectPanelIds (UiSpike.cpp:3063-3064) and both are measured doubling
EXACTLY 2x, children included (0x4BB0F5F7 101x20 -> 202x40, and 7 more).

So the "no runtime list" half of the census entry is a PHANTOM-ID artefact.
What is NOT settled, and what this probe exists for:

  the region instance creates only 9 of the script's 29 children - the 8 text
  labels and the minimise button. The 12 GZWinBMP mode icons, the 9 radio
  checks and the 2 commute toggles are created ON DEMAND, i.e. AFTER the sweep
  has already doubled their parent. That is the exact family as #47 (My Sims
  portraits) and #55 (picker icons): a child born at 1x design size inside an
  already-2x parent.

  And per BLIT-BEHAVIOUR.md LAW 35, GZWinBMP is dst-follows-src: the staged
  script carries imagerect=(0,0,36,28) on every icon whose area is 18x14, so a
  window that never gets doubled draws its 36x28 art OUT of an 18x14 box - 2x
  art overflowing a 1x window, which is precisely the artefact the census
  describes, just reached by a different mechanism than it claimed.

MODES
-----
  python emu_trip_legend.py
        DATA self-check only (offline, no log). Proves the expected sizes this
        probe asserts are DERIVED from the shipped .UI, not invented.

  python emu_trip_legend.py --log <SC4UIScale.log>
        Full adjudication against a live capture.

EXIT CODES
----------
  0  OVERALL: PASS      every instantiated node is at its 2x size
  1  OVERALL: FAIL      at least one node measured at 1x  -> real defect
  2  OVERALL: UNKNOWN   structural null: the probe never saw the subtree.
                        NOT a pass. See "POSITIVE CONTROL" below.
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))

STAGED = os.path.join(REPO, "tools", "selective-safe", "stage",
                      "T-0x00000000_G-0x96a006b0_I-0xabb0120f.ui")
STOCK = os.path.join(REPO, "tools", "uiscripts", "extracted",
                     "T-00000000_G-96a006b0_I-abb0120f.ui")

SCALE = 2  # tier for 2400x1600

# --- the two roots the game actually instantiates (measured, see docstring) ---
BODY_ROOT = 0x0BB0F5E7
MIN_ROOT = 0x6BB92BCA
PHANTOM_ROOT = 0x6BB92BCB   # script-only; must never be expected in a log

# The 8 text labels the region instance DOES create. These are the POSITIVE
# CONTROL: they are known-live and known-doubling, so if the probe reports them
# it demonstrably CAN see this subtree.
CONTROL_TEXT_IDS = [
    0x4BB0F5F7,  # "Trip Types" title
    0x8BB0F5FF,  # Pedestrian
    0x0BB0F607,  # Car
    0xABB0F60E,  # Bus
    0x8BB9130F,  # Sub/El Train
    0xEBB912FE,  # Freight Truck
    0x6BB91308,  # Freight Train
    0x2BB0F616,  # Passenger Train (id ALSO used by a text and a button in
                 #    the same script - collision, see note in report())
]

# Populated by data_selfcheck() from the shipped script: every window id that
# carries a baked imagerect, i.e. every node the ABSOLUTE test can judge.
ICON_IDS = set()

LINE_RX = re.compile(
    r"UI\s+id=0x([0-9A-Fa-f]{8})\s+pos\((-?\d+),(-?\d+)\)\s+size\((\d+)x(\d+)\)")
PANEL_RX = re.compile(
    r"panel 0x([0-9A-Fa-f]{8}) \((-?\d+),(-?\d+) (\d+)x(\d+)\) -> "
    r"\((-?\d+),(-?\d+) (\d+)x(\d+)\)")

NODE_RX = re.compile(r"<LEGACY\s+(.*?)>", re.S)
ATTR_RX = {
    "clsid": re.compile(r"clsid=(\S+)"),
    "id": re.compile(r"\bid=(0x[0-9a-fA-F]+)"),
    "area": re.compile(r"area=\((-?\d+),(-?\d+),(-?\d+),(-?\d+)\)"),
    "imagerect": re.compile(r"imagerect=\((\d+),(\d+),(\d+),(\d+)\)"),
}


def parse_script(path):
    """Return list of dicts: clsid, id, w, h, irw, irh (design units)."""
    txt = open(path, encoding="utf-8", errors="replace").read()
    out = []
    for body in NODE_RX.findall(txt):
        m = ATTR_RX["area"].search(body)
        if not m:
            continue
        l, t, r, b = (int(x) for x in m.groups())
        node = {
            "clsid": (ATTR_RX["clsid"].search(body).group(1)
                      if ATTR_RX["clsid"].search(body) else "?"),
            "id": (int(ATTR_RX["id"].search(body).group(1), 16)
                   if ATTR_RX["id"].search(body) else None),
            "w": r - l, "h": b - t,
            "irw": None, "irh": None,
        }
        ir = ATTR_RX["imagerect"].search(body)
        if ir:
            a, c, d, e = (int(x) for x in ir.groups())
            node["irw"], node["irh"] = d - a, e - c
        out.append(node)
    return out


# --------------------------------------------------------------------------
# SECTION 1 - DATA SELF-CHECK (offline; no log required)
# --------------------------------------------------------------------------
def data_selfcheck():
    """Prove the expected live sizes are derived from shipped data.

    The whole probe hinges on 'a correctly swept icon window is 36x28'. That
    number must come from the file we ship, never from a guess. This section
    re-derives it and fails loudly if the shipped data ever changes.
    """
    print("=" * 72)
    print("SECTION 1 - DATA SELF-CHECK (offline)")
    print("=" * 72)
    checks = fails = 0

    for p in (STAGED, STOCK):
        if not os.path.exists(p):
            print("  MISSING: %s" % p)
            return None, 1, 1

    stock = parse_script(STOCK)
    stage = parse_script(STAGED)

    checks += 1
    if len(stock) != len(stage):
        fails += 1
        print("  FAIL  node count differs: stock %d vs staged %d"
              % (len(stock), len(stage)))
    else:
        print("  ok    node count identical (%d nodes)" % len(stage))

    # 1a. geometry in the staged copy is UNCHANGED from stock. This is the
    #     design: the runtime sweep supplies geometry, the data supplies art.
    checks += 1
    same_geom = all(a["w"] == b["w"] and a["h"] == b["h"]
                    for a, b in zip(stock, stage))
    if same_geom:
        print("  ok    staged geometry == stock geometry (runtime-scaled family)")
    else:
        fails += 1
        print("  FAIL  staged geometry was statically altered - this family is "
              "runtime-swept; static doubling would DOUBLE-SCALE it")

    # 1b. every imagerect in the staged copy is exactly SCALE x its own window.
    #     This is the dst-follows-src correctness condition (LAW 35) and it is
    #     what makes '36x28' a measurement rather than an assumption.
    expect = {}
    for a, b in zip(stock, stage):
        if b["irw"] is None:
            continue
        checks += 1
        want_w, want_h = a["w"] * SCALE, a["h"] * SCALE
        if (b["irw"], b["irh"]) == (want_w, want_h):
            if b["id"] is not None:
                expect[b["id"]] = (want_w, want_h)
                ICON_IDS.add(b["id"])
        else:
            fails += 1
            print("  FAIL  id=0x%08X imagerect %sx%s != %d x design %dx%d"
                  % (b["id"] or 0, b["irw"], b["irh"], SCALE, a["w"], a["h"]))
    print("  ok    %d imagerect(s) == %dx their own design area  ->  a correctly"
          % (len(expect), SCALE))
    print("        swept icon window MUST measure exactly that, or the art "
          "overflows")

    # 1c. buttons/texts carry no imagerect; derive their expectation from area.
    for a, b in zip(stock, stage):
        if b["irw"] is None and b["id"] is not None:
            expect.setdefault(b["id"], (a["w"] * SCALE, a["h"] * SCALE))

    # 1d. the phantom. State it out loud so nobody re-adds it to a runtime list.
    checks += 1
    print("  ok    0x%08X is the SCRIPT root; the game promotes 0x%08X + "
          "0x%08X" % (PHANTOM_ROOT, BODY_ROOT, MIN_ROOT))
    print("        and never instantiates the container - do NOT list it")

    print("  SECTION 1: %d checked / %d passed / %d failed"
          % (checks, checks - fails, fails))
    return expect, checks, fails


# --------------------------------------------------------------------------
# SECTION 2 - POSITIVE CONTROL
# --------------------------------------------------------------------------
def positive_control(nodes, panels):
    """NULL IS NOT EVIDENCE. Prove the log COULD have shown the defect."""
    print()
    print("=" * 72)
    print("SECTION 2 - POSITIVE CONTROL")
    print("=" * 72)
    seen_ctrl = [i for i in CONTROL_TEXT_IDS if i in nodes]
    print("  control text rows present in this log: %d of %d"
          % (len(seen_ctrl), len(CONTROL_TEXT_IDS)))
    if BODY_ROOT in nodes:
        w, h = nodes[BODY_ROOT][0]
        print("  legend BODY 0x%08X present, size %dx%d" % (BODY_ROOT, w, h))
    else:
        print("  legend BODY 0x%08X ABSENT" % BODY_ROOT)
    if PHANTOM_ROOT in nodes:
        print("  0x%08X APPEARS IN THIS LOG - the phantom finding is wrong, "
              "re-open it" % PHANTOM_ROOT)
    swept = [p for p in panels if p[0] in (BODY_ROOT, MIN_ROOT)]
    for pid, sw, sh, dw, dh in swept:
        print("  sweep touched 0x%08X: %dx%d -> %dx%d (ratio %.2f x %.2f)"
              % (pid, sw, sh, dw, dh, dw / max(sw, 1), dh / max(sh, 1)))

    ok = len(seen_ctrl) >= 4 and BODY_ROOT in nodes
    print("  POSITIVE CONTROL: %s"
          % ("SATISFIED - the probe can see this subtree" if ok
             else "NOT SATISFIED - any null below is STRUCTURAL, not measured"))
    return ok


# --------------------------------------------------------------------------
# SECTION 3 - THE ADJUDICATOR
# --------------------------------------------------------------------------
def adjudicate(nodes, expect, first_seen):
    """Two discriminators, because the two classes need different ones.

    THE TRAP THIS PROBE ALREADY FELL INTO ONCE. The first version scored
    every node against 2 x its DESIGN area and produced 10 false FAILs on the
    golden log. The game RE-LAYS this panel: the "Pedestrian" label is
    111x18 in the script but 60x17 live, because GZWinText is re-sized to its
    rendered caption. 2 x design is therefore NOT the expected live size for
    any text or button here, and quoting it as one would have been an
    inference written down as a measurement.

    A - ABSOLUTE (GZWinBMP icons only). LAW 35: GZWinBMP is dst-follows-src,
        so the destination rect is computed from the ART. The staged script
        bakes imagerect=(0,0,36,28) into every icon, so a correct window is
        EXACTLY 36x28 no matter how the panel was re-laid. Design-free,
        relayout-proof, and it is the class that carries the reported
        artefact. This is the real adjudicator.

    B - RATIO (everything else). Compare the settled size to the SAME id's
        own earliest size in the SAME log. Must be exactly SCALE x. Also
        design-free. Runs only when the log caught the node before the sweep;
        otherwise it is skipped and SAID to be skipped, never silently passed.
    """
    print()
    print("=" * 72)
    print("SECTION 3 - ADJUDICATION")
    print("=" * 72)
    checks = fails = 0
    onex = []

    print("  A - ABSOLUTE (GZWinBMP: window must equal its baked imagerect)")
    abs_seen = 0
    for wid, (ew, eh) in sorted(expect.items()):
        if not expect[wid] or wid not in nodes:
            continue
        if wid not in ICON_IDS:
            continue
        w, h = nodes[wid][-1]
        checks += 1
        abs_seen += 1
        if (w, h) == (ew, eh):
            print("      PASS  0x%08X %dx%d" % (wid, w, h))
        elif (w * SCALE, h * SCALE) == (ew, eh):
            fails += 1
            onex.append(wid)
            print("      FAIL  0x%08X %dx%d  <- STILL 1x. Its %dx%d art will "
                  "overdraw this window." % (wid, w, h, ew, eh))
        else:
            fails += 1
            onex.append(wid)
            print("      FAIL  0x%08X %dx%d  <- art is %dx%d; mismatch either "
                  "way" % (wid, w, h, ew, eh))
    if abs_seen == 0:
        print("      (no icon window was instantiated in this capture - see "
              "the verdict note)")

    print("  B - RATIO (re-laid controls: settled size vs own pre-sweep size)")
    rat_seen = skipped = 0
    for wid in sorted(expect):
        if wid in ICON_IDS or wid not in nodes:
            continue
        base = first_seen.get(wid)
        cur = nodes[wid][-1]
        if base is None or base == cur:
            skipped += 1
            continue
        checks += 1
        rat_seen += 1
        if (base[0] * SCALE, base[1] * SCALE) == cur:
            print("      PASS  0x%08X %dx%d -> %dx%d (exactly %dx)"
                  % (wid, base[0], base[1], cur[0], cur[1], SCALE))
        else:
            fails += 1
            onex.append(wid)
            print("      FAIL  0x%08X %dx%d -> %dx%d (not %dx)"
                  % (wid, base[0], base[1], cur[0], cur[1], SCALE))
    if skipped:
        print("      SKIPPED %d node(s): this capture never saw them before "
              "the sweep, so no ratio exists. NOT counted as passes." % skipped)

    print("  SECTION 3: %d checked / %d passed / %d failed"
          % (checks, checks - fails, fails))
    return checks, fails, onex, abs_seen


def load_log(path):
    nodes, panels = {}, []
    for line in open(path, encoding="utf-8", errors="replace"):
        m = LINE_RX.search(line)
        if m:
            wid = int(m.group(1), 16)
            nodes.setdefault(wid, []).append((int(m.group(4)), int(m.group(5))))
        p = PANEL_RX.search(line)
        if p:
            panels.append((int(p.group(1), 16), int(p.group(4)), int(p.group(5)),
                           int(p.group(8)), int(p.group(9))))
    # A log normally contains SEVERAL dumps - at minimum one before the sweep
    # and one after, plus every periodic LiveDumpMs tick. The verdict is about
    # the SETTLED state, so keep the LAST size seen per id; keep the full
    # history separately so a 1x -> 2x transition can be reported as the
    # architectural open-flash rather than mis-scored as a defect.
    settled = {k: [v[-1]] for k, v in nodes.items()}
    first_seen = {k: v[0] for k, v in nodes.items()}
    history = {k: v for k, v in nodes.items() if len(set(v)) > 1}
    return settled, panels, history, first_seen


def main():
    log = None
    if "--log" in sys.argv:
        log = sys.argv[sys.argv.index("--log") + 1]

    expect, c1, f1 = data_selfcheck()
    if expect is None:
        print("\nOVERALL: FAIL (shipped data missing)")
        return 1
    if f1:
        print("\nOVERALL: FAIL (shipped data no longer supports the expected "
              "values - fix section 1 before trusting any live verdict)")
        return 1

    if not log:
        print()
        print("OVERALL: PASS (data self-check only - NOT a live verdict).")
        print("Re-run with --log <SC4UIScale.log> captured per PROBE RECIPE "
              "below to adjudicate.")
        print()
        print("PROBE RECIPE (no rebuild required):")
        print("  1. In Documents\\SimCity 4\\Plugins\\SC4UIScale.ini set")
        print("       [Spike]")
        print("       LiveDumpMs=3000")
        print("     (Settings.cpp:70. AutoScale only forces DumpTree off at")
        print("      tier 1; at 2400x1600 the tier is 2 and both stay live.")
        print("      Write it WITHOUT a BOM.)")
        print("  2. Load a FOUNDED city with some road traffic.")
        print("  3. Pick the Query tool, click a road/rail tile so the Route")
        print("     Query 'Trip Types' legend opens, and leave it open ~10 s")
        print("     so at least three periodic dumps land.")
        print("  4. Close the game (Deploy-OnGameClose.ps1 rules apply), copy")
        print("     SC4UIScale.log out, and run this script with --log.")
        return 0

    nodes, panels, history, first_seen = load_log(log)
    ok = positive_control(nodes, panels)
    c3, f3, onex, abs_seen = adjudicate(nodes, expect, first_seen)
    flashed = [k for k in history if k in expect]
    if flashed:
        print()
        print("  NOTE - %d node(s) changed size within this capture: %s"
              % (len(flashed), ", ".join("0x%08X %s" % (k, history[k])
                                         for k in sorted(flashed))))
        print("  A 1x -> 2x transition is the KNOWN architectural open-flash "
              "(panels are born 1x), not a separate defect. Scored on the "
              "settled size only.")

    print()
    print("=" * 72)
    print("TOTAL: %d checked / %d passed / %d failed"
          % (c1 + c3, (c1 - f1) + (c3 - f3), f1 + f3))
    if not ok:
        print("OVERALL: UNKNOWN")
        print("  STRUCTURAL NULL - this capture never contained the legend "
              "subtree, so it is evidence of nothing. Re-capture per the")
        print("  PROBE RECIPE with the Route Query legend actually OPEN.")
        return 2
    if abs_seen == 0 and not f3:
        print("OVERALL: UNKNOWN")
        print("  The RATIO half passed, but ZERO icon windows were "
              "instantiated, so the ABSOLUTE test - the one that judges the "
              "reported artefact - never ran.")
        print("  This is a STRUCTURAL NULL on the exact question asked. The "
              "capture almost certainly did not have the Route Query legend "
              "OPEN with its mode rows populated.")
        print("  Re-capture per the PROBE RECIPE (run with no --log to print "
              "it).")
        return 2
    if f3:
        print("OVERALL: FAIL")
        print("  %d node(s) measured at 1x inside a swept 2x parent: %s"
              % (len(onex), ", ".join("0x%08X" % i for i in onex)))
        print("  Family: #47 / #55 (child born after the parent was doubled).")
        print("  Cure candidates, in order: add 0x%08X to the leaf-kick that "
              "closed #47; or born-2x in data + kDataScaledSubtreeIds, BOTH "
              "HALVES TOGETHER (law 43)." % BODY_ROOT)
        return 1
    print("OVERALL: PASS")
    print("  The Trip Types legend is correct at %dx. The census entry for "
          "0x%08X should be reclassified NOT-A-DEFECT (phantom id)."
          % (SCALE, PHANTOM_ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
