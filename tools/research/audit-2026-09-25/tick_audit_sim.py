"""Count window visits per IncrementalPass tick from a live full-tree dump.

Tree order = dump order = EnumChildren order = the order cGZWin::
GetChildWindowFromIDRecursive walks (decompiled 0x0099DEC4: post-order,
children first, self last, first match wins).

Usage: python tick_audit_sim.py <log with a full "UI id=..." tree dump> [mayor|god]
The audit (research/AUDIT-2026-09-25-EFFICIENCY.md, A1) ran it on the local-only
capture _tests/captures/SC4UIScale-2026-08-19-105203.log (840-window city tree).
The lookup list mirrors UiSpike.cpp as of commit b3ebfdd; re-derive it after edits.
"""
import re
import sys

LINE = re.compile(r"\] UI (\s*)id=0x([0-9A-Fa-f]{8}) pos\((-?\d+),(-?\d+)\) size\((\d+)x(\d+)\) children=(\d+) vis=(-?\d)")


class Node:
    __slots__ = ("id", "vis", "w", "h", "kids", "parent", "depth")

    def __init__(self, wid, vis, w, h, depth):
        self.id = wid
        self.vis = vis
        self.w = w
        self.h = h
        self.kids = []
        self.parent = None
        self.depth = depth


def parse(path):
    root = None
    stack = []
    for ln in open(path, encoding="utf-8", errors="replace"):
        m = LINE.search(ln)
        if not m:
            continue
        depth = len(m.group(1)) // 2
        n = Node(int(m.group(2), 16), int(m.group(8)), int(m.group(5)), int(m.group(6)), depth)
        if root is None:
            root = n
            stack = [n]
            continue
        while stack and stack[-1].depth >= depth:
            stack.pop()
        n.parent = stack[-1]
        stack[-1].kids.append(n)
        stack.append(n)
    return root


def count(n):
    return 1 + sum(count(k) for k in n.kids)


def rec_find(n, wid, visits):
    """cGZWin::GetChildWindowFromIDRecursive, post-order."""
    visits[0] += 1
    for k in n.kids:
        r = rec_find(k, wid, visits)
        if r is not None:
            return r
    if n.id == wid:
        return n
    return None


def lookup(n, wid):
    v = [0]
    r = rec_find(n, wid, v)
    return r, v[0]


def idcollect(root, wid, mx=4):
    """IdCollectCtx walk: EnumChildren from root, depth<8 recursion,
    stop descending once n==max. Visits = callback invocations."""
    found = []
    visits = [0]

    def enum(node, depth):
        for k in node.kids:
            visits[0] += 1
            if k.id == wid and len(found) < mx:
                found.append(k)
            if depth < 8 and len(found) < mx:
                enum(k, depth + 1)

    enum(root, 0)
    return found, visits[0]


def find_child(n, wid):
    for k in n.kids:
        if k.id == wid:
            return k
    return None


def main(path, mayor):
    main_w = parse(path)
    app = find_child(main_w, 0x6104489A)
    view = find_child(app, 0x9A47B417)
    menu = find_child(view, 0xAA32BCE6)
    total_main = count(main_w)
    total_view = count(view)
    rows = []

    def L(tag, rootname, root, wid):
        r, v = lookup(root, wid)
        rows.append((tag, rootname, "%08X" % wid, "hit" if r else "MISS", v))
        return r

    # --- TickCheck ---
    L("RegionWatchTick region screen", "main", main_w, 0xEA659793)
    # --- ScalePanelsUnder ---
    for tag in ("ApplyPanelDocks#1 (ScalePanelsUnder)", "ApplyPanelDocks#2 (ScaleGodFlyouts)"):
        L(tag + " anchor", "view", view, 0x8A8B5B71)
        L(tag + " child", "view", view, 0x0A4A8176)
        L(tag + " weld dock", "view", view, 0x0987B48F)
        L(tag + " weld comp", "view", view, 0xE9889775)
    L("ScaleGodFlyouts DPROBE probeRoot (== pView)", "view", view, 0x9A47B417)
    L("ScaleGodFlyouts dnTool", "view", view, 0xCA35CB74)
    L("ScaleGodFlyouts mayorBtn1 (UNUSED)", "view", view, 0x8991EE08)
    L("ScaleGodFlyouts mayorHud", "view", view, 0xE9889775)
    L("ScaleGodFlyouts god toolbar", "view", view, 0xC991EDA8)
    L("ScaleGodFlyouts sub-flyout", "view", view, 0x8A6E61E0)
    mayor_only = [(0x69923479, False), (0xC99237A0, False), (0xE992F711, False),
                  (0x699306ED, False), (0x0992FD17, False),
                  (0x8BB27C12, True), (0xAB954023, True)]
    for fid, any_mode in mayor_only:
        if mayor or any_mode:
            L("ScaleGodFlyouts mayor flyout", "view", view, fid)
    for fid in (0x49923239, 0xCA35CBED):
        L("ScaleGodFlyouts god flyout", "view", view, fid)
    L("ScaleGodFlyouts godParent (== pView)", "view", view, 0x9A47B417)
    dock = L("ScalePanelsUnder dock", "view", view, 0x0987B48F)
    if dock:
        L("TryRecreateMinimapSurface minimap", "dock", dock, 0x0BC3B559)
    if menu:
        L("DVMAP 0x4203", "menu", menu, 0x00004203)
    L("UDMAP dash root", "view", view, 0x4BCB938A)
    L("HookDashboardGauges dash root", "view", view, 0x4BCB938A)
    bmpx_city = [0x698894D3, 0xCA1F1D9C, 0xAA1F1EC5, 0xEA1F1E4D, 0x6A61E29F,
                 0xABBAA2D3, 0xEA1F1E4E, 0xEA1F1E5E, 0x8A8B5B71, 0x8A8B5B72,
                 0x0A4A8176, 0x27DF05BE, 0x27DF05BF, 0x48E945B4]
    bmpx_sub = 0
    for wid in bmpx_city:
        r = L("HookRuntimeBmpsUnder city", "view", view, wid)
        if r:
            bmpx_sub += count(r) - 1   # BmpWalkCtx visits every descendant
    L("CHARTGEO graphs root", "view", view, 0x8A8B5B71)
    # --- IncrementalPass tail ---
    for did in (0xAA921F4F, 0x6AAEEC4A, 0xC9264BE2, 0x8926EEBE, 0x4C30E4FA, 0xAA8DEF97):
        f, v = idcollect(main_w, did)
        rows.append(("kCityDialogIds IdCollect walk", "main", "%08X" % did,
                     "%d found" % len(f), v))
    for wid in (0x6A243D9E, 0xCBF32603):
        L("HookRuntimeBmpsUnder dialog", "main", main_w, wid)

    print("tree: main=%d windows, view=%d windows, mode=%s" %
          (total_main, total_view, "mayor" if mayor else "god/not-mayor"))
    tot = 0
    for r in rows:
        tot += r[4]
        print("  %-48s %-5s %s %-8s %6d" % r)
    print("  BmpWalkCtx subtree walks under found BMPX roots: %d" % bmpx_sub)
    # DPROBE explicit walk: every view window to depth 10
    print("  DPROBE explicit walk (2 std::map ops + 1KB memset each): %d" % total_view)
    print("TOTAL id-lookup + IdCollect visits: %d  (= %.1f full main-tree walks)" %
          (tot, tot / float(total_main)))
    print("GRAND TOTAL incl. BmpWalk + DPROBE: %d (= %.1f full walks)" %
          (tot + bmpx_sub + total_view, (tot + bmpx_sub + total_view) / float(total_main)))


T = {'kRegionPanelIds': [196146663, 166455790, 1787943957, 1787943958, 3935087897, 1787943956, 166456901, 166456928, 1807297482], 'kNeverScaleIds': [1782663539, 268435462, 1780759966, 1780759967, 3421709827, 710736684, 2861428631, 206723998, 3374730210, 2301030078, 1245032690, 3932058764, 2863253977, 3395183201, 2324561141, 173349971, 655360, 172083122, 172083123, 2233478158, 668927422, 668927423], 'kGodToolFlyoutIds': [3392523245, 1234317881], 'kGodPanelIds': [1776552479, 3381783976, 2880596750, 175669882], 'kSubFlyoutIds': [2322489824], 'kAlwaysScaleCityIds': [2854425864, 1223247284, 2855976962, 3393991469, 1779812199, 2853564166, 706582193, 1770558675, 3391036828, 2854166213, 3927907917, 1784799903, 2881135315, 3927907918, 3927907934, 3381783976, 1776552479, 175669882, 3918042997, 159888527, 3935087892, 1784996800, 3391811008, 2855451878, 2855976960, 2855976961, 2324388721, 2324388722, 172654966, 3381610993, 1271632778, 2880596750, 2881886674, 3961150655], 'kDataScaledSubtreeIds': [1779812199, 2324388721, 2324388722, 172654966, 1271632778, 3961150655, 2855976962, 3393991469, 2855976961, 2855976960], 'kAdviceListScaleSelfIds': [1780684081, 2854166197, 1780424522, 1048832, 1048833], 'kAdviceListNeverTouchIds': [2853368636], 'mayorOnly': [1771189369, 3381802912, 3918722833, 1771243245, 160627991, 2343730194, 2878685219]}


def sweep_visits(view):
    """Steady-state ScalePanelsUnder panel loop + ScalePanelRoot/ScaleSubtree."""
    sw, sh = view.w, view.h
    god = [g for g in T['kGodPanelIds'] if g != 0xABB26B0E]   # gScaleAbbPanel=0
    visits = [0]
    snaps = [0]

    def sub(n, depth):
        if depth > 8:
            return
        visits[0] += 1                       # Classify: one std::map find
        if n.id in T['kAdviceListNeverTouchIds']:
            return
        if n.id in T['kAdviceListScaleSelfIds']:
            return
        if n.kids:
            snaps[0] += 1                    # ChildSnapshot = {} (1 KB zeroed)
            for k in n.kids:
                sub(k, depth + 1)

    roots = 0
    for p in view.kids:
        i = p.id
        if i in T['kNeverScaleIds'] or i == 0x43 or i in T['kGodToolFlyoutIds'] \
                or i in T['mayorOnly'] or i in T['kSubFlyoutIds']:
            continue
        if not p.vis and i not in T['kRegionPanelIds'] and i not in god \
                and i not in T['kAlwaysScaleCityIds']:
            continue
        if p.w >= sw * 9 // 10 and p.h >= sh * 9 // 10:
            continue
        if p.w <= 0 or p.h <= 0:
            continue
        roots += 1
        visits[0] += 1                       # ScalePanelRoot Classify
        if i in T['kDataScaledSubtreeIds']:
            continue
        if p.kids:
            snaps[0] += 1
            for k in p.kids:
                sub(k, 1)
    return roots, visits[0], snaps[0]


def main2(path):
    main_w = parse(path)
    app = find_child(main_w, 0x6104489A)
    view = find_child(app, 0x9A47B417)
    r, v, s = sweep_visits(view)
    print("SWEEP (deliberate): %d panel roots, %d windows Classify'd, %d child snapshots"
          % (r, v, s))


if __name__ == "__main__":
    main2(sys.argv[1])
    main(sys.argv[1], sys.argv[2] == "mayor" if len(sys.argv) > 2 else True)
