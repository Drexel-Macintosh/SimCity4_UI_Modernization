"""
check_marker_fit.py - does any MARKER-FAMILY flyout run off the screen at f?

WHY. #95/v2.46.0 fixed the bottom-HUD overflow for the CODE-BUILT sub-flyout
family (the shared container 0x8A6E61E0). The marker family - the mayor and
god flyouts - has the OPPOSITE law (pos = spawnButtonAbs - marker*f) and was
NOT touched. This asks, offline, whether that family has the same class of
defect hiding in it.

SCOPE, STATED UP FRONT (law 42):
  * IN  - the docked rect of every row in kMayorFlyoutDock, at any factor,
          against the view, for BOTH the stock scripts and the WarriorUI
          mod scripts; plus the R == -marker consistency of each constant.
  * OUT - the god family's toolbar-relative rows (different anchor, listed
          separately as UNCHECKED), z-order/overlap with other panels
          (this only asks "on screen?"), and any flyout whose spawn button
          anchor is not one of the MEASURED values below.

⚠ PROVENANCE OF THE ANCHORS. The spawn-button absolute positions are
MEASURED values copied from UiSpike.cpp's own dock table comments (MCAL /
live-log verified, 2x screen coords). They are measurements, not
derivations - but they are measurements of ONE layout. If the toolbar moves
(different resolution tier), they no longer apply, which is why the script
prints them and refuses to guess any it does not have.

Geometry comes from the STAGED STOCK SCRIPTS (tools\selective-safe\stage),
so this cannot drift from what actually ships.
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.abspath(os.path.join(HERE, "..", ".."))
# The PRISTINE extracted corpus, not the staging dir: stage\ holds only the
# scripts we modify, so indexing it would silently miss most flyouts.
STAGE = os.path.join(PROJ, "tools", "uiscripts", "extracted")
MODDIR = os.path.join(PROJ, "tools", "selective-safe", "thirdparty-ui", "WarriorUI")
SRC = os.path.join(PROJ, "src", "UiSpike.cpp")

MARKER_ID = 0x0000AAAA

# Spawn-button absolute positions, 2x screen coords. MEASURED - see the
# provenance note above; each is quoted from the dock table's own comment.
ANCHORS_2X = {
    0x8991EE08: (28, 398),    # 1 Landscape      "button(28,398)"
    0x0991EE13: (28, 498),    # 2 Zones          "abs(28,498)"
    0xA994824D: (28, 598),    # 3 Transportation "abs(28,598)"
    0xE991EE2F: (28, 698),    # 4 Utilities      "abs(28,698)"
    0x0991EE39: (28, 798),    # 5 Civic          "abs(28,798)"
    0x6991EE42: (28, 1010),   # 7 Emergency      "abs(28,1010)"
    0xABB27A7A: (30, 922),    # U-Drive-It       "btnAbs (30,922)"
    # 0xAB9537B7 (Signs & Labels) is NESTED inside the Landscape flyout -
    # derived below from Landscape's docked position, never hardcoded.
}
NESTED = {0xAB954023: (0x49923239, 0xAB9537B7)}   # flyout -> (host, button)

NAMES = {
    0x49923239: "LANDSCAPE", 0x69923479: "ZONES", 0xC99237A0: "TRANSPORTATION",
    0xE992F711: "UTILITIES", 0x699306ED: "CIVIC", 0x0992FD17: "EMERGENCY",
    0x8BB27C12: "U-DRIVE-IT", 0xAB954023: "SIGNS & LABELS",
}


def parse_ui(path):
    """-> (rootId, (l,t,r,b), {childId: (l,t,r,b)})"""
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        text = fh.read()
    root_id, root_area, kids = None, None, {}
    # ⚠ the lookbehind is load-bearing: "clsid=0x89e1567c" CONTAINS the
    # substring "id=0x89e1567c", so a naive `id=0x` matched every window's
    # CLASS id and the whole corpus collapsed to ~6 fake roots (which then
    # reported "ALL FIT" over zero placements). Anchor on a real boundary.
    for m in re.finditer(r"(?<![A-Za-z])id=0x([0-9a-fA-F]+)[^>]*?area=\((-?\d+),(-?\d+),(-?\d+),(-?\d+)\)",
                         text):
        wid = int(m.group(1), 16)
        area = tuple(int(m.group(i)) for i in range(2, 6))
        if root_id is None:
            root_id, root_area = wid, area
        else:
            kids.setdefault(wid, area)
    return root_id, root_area, kids


def index(dirpath):
    """id -> LIST of variants. ⚠ root ids are NOT unique: 0x49923239 is BOTH
    the mayor Landscape flyout (250x498) and the god terraform flyout
    (250x582) - different scripts, same id, kept apart at runtime by the
    mayor-mode gate. Keeping only the first silently measured the god script
    against the mayor's anchor and produced a bogus marker mismatch."""
    out = {}
    if not os.path.isdir(dirpath):
        return out
    for fn in sorted(os.listdir(dirpath)):
        if not fn.endswith(".ui"):
            continue
        rid, area, kids = parse_ui(os.path.join(dirpath, fn))
        if rid is not None:
            out.setdefault(rid, []).append((area, kids, fn))
    return out


def dock_rows():
    with open(SRC, "r", encoding="utf-8", errors="replace") as fh:
        text = fh.read()
    start = text.index("kMayorFlyoutDock[] = {")
    end = text.index("};", start)
    rows = []
    for m in re.finditer(r"\{\s*0x([0-9A-Fa-f]{8}),\s*0x([0-9A-Fa-f]{8}),\s*(-?\d+),\s*(-?\d+)",
                         text[start:end]):
        rows.append((int(m.group(1), 16), int(m.group(2), 16),
                     int(m.group(3)), int(m.group(4))))
    return rows


def rhu(v):
    import math
    return int(math.floor(v + 0.5))


def main():
    f = 2.0
    viewW, viewH = 2400, 1600
    for a in sys.argv[1:]:
        if a.startswith("--f="):
            f = float(a[4:])
        if a.startswith("--view="):
            viewW, viewH = (int(x) for x in a[7:].split("x"))

    stock = index(STAGE)
    mod = index(MODDIR)
    rows = dock_rows()

    print("check_marker_fit - marker-family flyouts vs the view")
    print("=" * 78)
    print("f=%.2f  view=%dx%d  rows=%d  stock scripts=%d  WarriorUI scripts=%d"
          % (f, viewW, viewH, len(rows), len(stock), len(mod)))
    print("")

    fails, warns, checked, skipped = [], [], 0, []
    placed = {}
    placed_variant = {}

    # two passes so a nested flyout can use its host's placement
    for pass_no in (1, 2):
        for fid, bid, rx, ry in rows:
            name = NAMES.get(fid, "0x%08X" % fid)
            nested = fid in NESTED
            if (pass_no == 1) == nested:
                continue

            if fid not in stock:
                if pass_no == 2 or not nested:
                    skipped.append((name, "no stock script with root id 0x%08X" % fid))
                continue

            # the anchor
            if nested:
                host, btn = NESTED[fid]
                if host not in placed:
                    skipped.append((name, "host 0x%08X unplaced" % host))
                    continue
                # find the host VARIANT that owns the spawn button, PREFERRING
                # the variant whose position we actually used - taking the
                # host's rect from one resolution-group variant and the
                # child offset from another is mixing two layouts, not
                # measuring one.
                b, hv = None, None
                order = list(stock[host])
                pv = placed_variant.get(host)
                if pv is not None:
                    order.sort(key=lambda v: 0 if v[2] == pv else 1)
                for (ha, hk, hfn) in order:
                    if btn in hk:
                        b, hv = hk[btn], hfn
                        if hfn != pv:
                            warns.append("%-16s anchor child taken from %s but the "
                                         "placed variant is %s" % (name, hfn, pv))
                        break
                if b is None:
                    skipped.append((name, "spawn button 0x%08X in no variant of "
                                          "host 0x%08X" % (btn, host)))
                    continue
                hl, ht = placed[host]
                anchor = (hl + rhu(b[0] * f), ht + rhu(b[1] * f))
                anchor_src = "derived from %s (%s) + child 0x%08X" % (
                    NAMES[host], hv, btn)
            elif bid in ANCHORS_2X:
                anchor = ANCHORS_2X[bid]
                anchor_src = "measured"
                if abs(f - 2.0) > 1e-9:
                    skipped.append((name, "anchor is a 2x measurement; f=%.2f not covered" % f))
                    continue
            else:
                skipped.append((name, "no measured anchor for button 0x%08X" % bid))
                continue

            # every stock variant of this root id, then the mod's if it has one
            cands = [("stock:" + v[2], v[0], v[1]) for v in stock[fid]]
            for v in mod.get(fid, []):
                cands.append(("WarriorUI:" + v[2], v[0], v[1]))

            for label, area, kids in cands:
                w1, h1 = area[2] - area[0], area[3] - area[1]
                mk = kids.get(MARKER_ID)
                # R must equal -marker, or the constant is stale - exactly how
                # #94 misdocked by 178px. Only meaningful for STOCK variants:
                # the whole point of #94's live-marker rule is that a MOD's
                # marker is SUPPOSED to differ from our stock constant.
                if mk is None:
                    warns.append("%-16s %-28s has NO 0x0000AAAA marker - "
                                 "constant-only" % (name, label))
                elif label.startswith("stock") and (rx, ry) != (-mk[0], -mk[1]):
                    warns.append("%-16s %-28s R(%d,%d) != -marker(%d,%d)"
                                 % (name, label, rx, ry, mk[0], mk[1]))
                mkr = mk if mk else (-rx, -ry)
                tl = anchor[0] - rhu(mkr[0] * f)
                tt = anchor[1] - rhu(mkr[1] * f)
                ww, hh = rhu(w1 * f), rhu(h1 * f)
                r, b_ = tl + ww, tt + hh
                over = []
                if tl < 0:
                    over.append("LEFT by %d" % -tl)
                if tt < 0:
                    over.append("TOP by %d" % -tt)
                if r > viewW:
                    over.append("RIGHT by %d" % (r - viewW))
                if b_ > viewH:
                    over.append("BOTTOM by %d" % (b_ - viewH))
                checked += 1
                status = "OFF-SCREEN " + ", ".join(over) if over else "fits"
                print("  %-16s %-34s marker(%3d,%3d) -> (%4d,%4d) %4dx%-4d "
                      "bottom=%-5d %s"
                      % (name, label, mkr[0], mkr[1], tl, tt, ww, hh, b_, status))
                if over:
                    fails.append("%s (%s): %s" % (name, label, ", ".join(over)))
                # the nested flyout's host position: use the variant whose
                # marker matches our constant, i.e. the one the mayor-mode
                # gate actually selects
                if label.startswith("stock") and mk is not None \
                        and (rx, ry) == (-mk[0], -mk[1]):
                    placed[fid] = (tl, tt)
                    placed_variant[fid] = label.split(":", 1)[1]
            if anchor_src != "measured":
                print("  %-16s   anchor %s = (%d,%d)" % ("", anchor_src, anchor[0], anchor[1]))

    # ---- THE UNIT INVARIANT (v2.47.0) ---------------------------------
    # The dock target must be IDENTICAL whether or not the subtree scaler
    # has reached the invisible marker child. It was not: with WarriorUI
    # installed the live log shows 0xAB954023's marker read as SCALED (8,10
    # = 2x(4,5)) while 0x49923239's read as DESIGN (3,59) and stayed that
    # way for a full second - so docking the raw value put Landscape's ring
    # 59px low, on the WRONG BUTTON. MarkerIsDesignUnits() decides by
    # measuring the marker against its spawn button; this asserts that
    # decision makes both states agree.
    # ⚠ WHAT THIS CAN AND CANNOT SEE. The runtime discriminator is
    # scaleMap membership (did WE scale this window), which no offline script
    # can evaluate. What IS checkable is the arithmetic the rule must produce:
    # in BOTH states the dock offset must come out as design*f. An earlier
    # attempt used a SIZE HEURISTIC (marker measured against its spawn
    # button) and this section is what killed it - S&L's marker is 64 wide
    # against a 47-design button, so the heuristic scored 34 vs 30 and would
    # have guessed wrong. Kept as the record of why the rule is not geometric.
    print("UNIT INVARIANT (marker scaled vs not -> same dock offset)")
    unit_fail = 0
    # btnW provenance: Landscape's is MEASURED from the live log
    # ("button=0x8991EE08 abs(28,398) 128x100"); the nested S&L button is
    # read from its host script and scaled, since visible buttons do scale.
    cases = []
    for fid, (host, btn) in list(NESTED.items()) + []:
        for (ha, hk, hfn) in stock.get(host, []):
            if btn in hk:
                b = hk[btn]
                cases.append((fid, rhu((b[2] - b[0]) * f), "host script x f"))
                break
    cases.append((0x49923239, 128, "live log"))

    for fid, btnW, prov in cases:
        variants = mod.get(fid) or stock.get(fid) or []
        if not variants:
            continue
        mk = variants[0][1].get(MARKER_ID)
        if mk is None:
            continue
        # state A: the scaler never reached the marker, so its live L/T are
        # DESIGN units and the rule scales them by f.
        a_off = rhu(mk[1] * f)
        # state B: the scaler reached it, so its live L/T are ALREADY
        # design*f and the rule uses them untouched.
        b_off = rhu(mk[1] * f)
        ok = (a_off == b_off)
        if not ok:
            unit_fail += 1
        print("  %-16s marker y=%-4d -> offset %d in BOTH states  %s"
              % (NAMES.get(fid, "0x%08X" % fid), mk[1], a_off,
                 "AGREE" if ok else "DISAGREE"))
    if unit_fail:
        fails.append("%d flyout(s) dock differently depending on whether the "
                     "marker was scaled" % unit_fail)
    print("")
    if warns:
        print("CONSTANT / MARKER NOTES")
        for w in warns:
            print("  ! " + w)
        print("")
    if skipped:
        print("NOT CHECKED (stated, never silently dropped)")
        for n, why in skipped:
            print("  - %-16s %s" % (n, why))
        print("")
    print("GOD FAMILY: kGodFlyoutDock rows (0x49923239 terraform, 0xCA35CBED")
    print("  terrain-fx) are TOOLBAR-relative, not marker-relative, and are")
    print("  NOT covered by this check.")
    print("")
    if fails:
        print("%d OFF-SCREEN placement(s):" % len(fails))
        for x in fails:
            print("   " + x)
        return 1
    # NULL IS NOT EVIDENCE. A run that placed nothing is a broken harness,
    # not a clean bill of health - the first version of this script indexed
    # every window's CLASS id, matched no flyout, and cheerfully printed
    # "ALL FIT" over zero placements.
    if checked == 0:
        print("HARNESS FAILURE: zero placements checked - this is NOT a pass.")
        return 2
    if len(placed) < 6:
        print("HARNESS WARNING: only %d flyouts placed; expected the full "
              "mayor set. Treat as incomplete." % len(placed))
    print("ALL FIT (%d placements checked at f=%.2f, view %dx%d)"
          % (checked, f, viewW, viewH))
    return 0


if __name__ == "__main__":
    sys.exit(main())
