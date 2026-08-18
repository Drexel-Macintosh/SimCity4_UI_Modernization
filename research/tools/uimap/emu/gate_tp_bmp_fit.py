r"""GATE (#154): scaling a plugin's dialog must not CUT OFF anything new.

⛔ THE OBVIOUS GATE IS THE WRONG GATE, and it took one build to find out.
`GZWinBMP blttype=normal` draws its bitmap at the window origin, at the
bitmap's OWN size, and lets the window CLIP it - it never stretches to fit. So
art and window do NOT scale to the same number and cannot be made to:

    art  285x30 -> 429x45   Upscale2x snaps 285 up (CellUnit 3): 427.5 -> 429
    win  285x30 -> 427x45   edge-derived, ScaleRound PER EDGE - and by the
                            OFFSET-PARITY LAW an odd left edge gives 427 while
                            an even one gives 428, in the SAME dialog

One bitmap cannot be both 427 and 428 wide, so an overhang at f=1.5 is
STRUCTURAL, not a defect. A first version of this gate asserted "no ink may be
clipped" and reported 27 failures on a build that is correct - every one of
them a flat background stripe losing a column identical to the column beside
it. MEASURED, not argued: `bd85e83a` is uniform along x (same three colour
bands in every column, its only feature an icon ending at x=281 of 285), and
CAM itself crops these same strips to 206px in places.

WHAT THIS ASSERTS INSTEAD - the question that decides what the screen looks
like: **the pixels the window cuts away must be a repeat of the last pixels it
keeps.** Cut a flat stripe anywhere and nothing changes; cut through an icon,
a border or a rounded cap and it shows. Evaluated on BOTH axes.

AND IT IS EVALUATED TWICE - at 1x and at the tier - because the mod's own
layout already crops several of these on purpose. We fail only where OUR
scaling loses something 1x kept. A crop CAM already had is reported as
PRE-EXISTING and is not ours to fix (law: a stock/mod control, run before
blaming your own build).

WHERE IT CAME FROM: CAM's city info screen {96a006b0,9b868f68} - the Village
Hall / Town Hall query - shipped at 1x for the whole life of the project while
FontStyle-<tier> scaled its text, so labels clipped mid-word and values
overlapped them. Nothing in the builder ever asked "is a PLUGIN'S OWN dialog
scaled at all?": the winner assert only asks whether one of OUR targets has
been taken over by a mod. This gate covers the art half of that blind spot.

NEGATIVE CONTROL (`--selftest`): for each bitmap find the rightmost column
that DIFFERS from its neighbour, put the window edge exactly there, and the
gate must fail on every such node. Images with no such column (perfectly
uniform) are counted and named as untestable rather than passed. A gate never
seen to fail proves nothing - that law has been paid for twice on this project.

    python gate_tp_bmp_fit.py [--tier 15x|2x|3x|all] [--selftest]

Offline. Reads build outputs only; never touches the game or Plugins.
"""
import os
import re
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(os.path.dirname(HERE))
DS = os.path.join(TOOLS, "dialog-static")
TP_SRC = os.path.join(DS, "thirdparty-src")
TP_ART = os.path.join(DS, "thirdparty-art")
SRC1X = os.path.join(TOOLS, "dbpf", "extracted", "SimCity_1")

MAGENTA = (255, 0, 255)
ALPHA_FLOOR = 8          # at or below this the pixel draws nothing visible
PKGS = ("CamUI", "SaveWarningUI")

NODE_RE = re.compile(r"<LEGACY([^>]*)>")
ATTR_RE = re.compile(r'(\w+)=("[^"]*"|\{[^}]*\}|\([^)]*\)|\S+)')


def bmp_nodes(text):
    """(tgi, (winW,winH), (rectW,rectH) or None) per GZWinBMP blttype=normal.

    Document order is the join key between the 1x source and the staged copy:
    the builder rewrites attributes in place and never reorders or drops a
    node, while the TGI is NOT unique (five nodes share one strip) and can be
    rewritten to a clone id. Order is the only stable identity.

    ⛔ `imagerect` IS NOT OPTIONAL DETAIL - IT IS WHAT ACTUALLY GETS DRAWN.
    The first version of this gate ignored it, passed a build clean, and that
    build shipped stripes two thirds of the way across every row: the window
    was scaled to 428, the bitmap we ship was 429, and `imagerect=(0,0,285,30)`
    - unscaled - sliced a 285px piece out of the middle of it. A gate that
    reads the window and the bitmap but not the CROP BETWEEN THEM is measuring
    two of the three numbers that decide the pixels.
    """
    out = []
    for m in NODE_RE.finditer(text):
        a = dict(ATTR_RE.findall(m.group(1)))
        if a.get("clsid") != "GZWinBMP" or a.get("blttype") != "normal":
            continue
        gi = re.match(r"\{([0-9a-fA-F]+),([0-9a-fA-F]+)\}", a.get("image", ""))
        ar = re.match(r"\((-?\d+),(-?\d+),(-?\d+),(-?\d+)\)", a.get("area", ""))
        if not gi or not ar:
            continue
        l, t, r, b = (int(x) for x in ar.groups())
        rect = None
        ir = re.match(r"\((-?\d+),(-?\d+),(-?\d+),(-?\d+)\)", a.get("imagerect", ""))
        if ir:
            rl, rt, rr, rb = (int(x) for x in ir.groups())
            rect = (rr - rl, rb - rt)
        out.append(((int(gi.group(1), 16), int(gi.group(2), 16)),
                    (r - l, b - t), rect))
    return out


# ---- PNG reader. No PIL, no resampling anywhere near it. ------------------
def _png_raw(path):
    with open(path, "rb") as f:
        data = f.read()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("not a PNG: %s" % path)
    w = h = bitdepth = colortype = None
    idat, plte, trns = bytearray(), None, None
    p = 8
    while p + 8 <= len(data):
        ln = struct.unpack(">I", data[p:p + 4])[0]
        typ = data[p + 4:p + 8]
        body = data[p + 8:p + 8 + ln]
        if typ == b"IHDR":
            w, h, bitdepth, colortype = struct.unpack(">IIBB", body[:10])
        elif typ == b"PLTE":
            plte = body
        elif typ == b"tRNS":
            trns = body
        elif typ == b"IDAT":
            idat += body
        elif typ == b"IEND":
            break
        p += 12 + ln
    if bitdepth != 8:
        raise ValueError("unsupported bit depth %s in %s" % (bitdepth, path))
    chans = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[colortype]
    raw = zlib.decompress(bytes(idat))
    stride = w * chans
    prev = bytearray(stride)
    rows = []
    q = 0
    for _y in range(h):
        ft = raw[q]
        q += 1
        line = bytearray(raw[q:q + stride])
        q += stride
        if ft == 1:
            for i in range(chans, stride):
                line[i] = (line[i] + line[i - chans]) & 0xFF
        elif ft == 2:
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 0xFF
        elif ft == 3:
            for i in range(stride):
                a = line[i - chans] if i >= chans else 0
                line[i] = (line[i] + ((a + prev[i]) >> 1)) & 0xFF
        elif ft == 4:
            for i in range(stride):
                a = line[i - chans] if i >= chans else 0
                c = prev[i - chans] if i >= chans else 0
                b = prev[i]
                pp = a + b - c
                pa, pb, pc = abs(pp - a), abs(pp - b), abs(pp - c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[i] = (line[i] + pr) & 0xFF
        elif ft != 0:
            raise ValueError("bad PNG filter %d in %s" % (ft, path))
        rows.append(line)
        prev = line
    return w, h, chans, colortype, plte, trns, rows


_CACHE = {}


def pixels(path):
    """(w, h, grid) where grid[y][x] is a colour tuple, or None for INVISIBLE.

    Fully transparent and colour-keyed pixels both collapse to None: RGB noise
    hiding under alpha=0 is not something anyone can see, and treating it as a
    difference would make uniform padding look like content.
    """
    if path in _CACHE:
        return _CACHE[path]
    w, h, ch, ct, plte, trns, rows = _png_raw(path)
    grid = []
    for line in rows:
        r_ = []
        for x in range(w):
            o = x * ch
            if ct == 6:
                r, g, b, a = line[o], line[o + 1], line[o + 2], line[o + 3]
            elif ct == 2:
                r, g, b, a = line[o], line[o + 1], line[o + 2], 255
            elif ct == 4:
                r = g = b = line[o]
                a = line[o + 1]
            elif ct == 0:
                r = g = b = line[o]
                a = 255
            else:
                idx = line[o]
                r, g, b = plte[idx * 3], plte[idx * 3 + 1], plte[idx * 3 + 2]
                a = trns[idx] if (trns and idx < len(trns)) else 255
            r_.append(None if (a <= ALPHA_FLOOR or (r, g, b) == MAGENTA)
                      else (r, g, b, a))
        grid.append(r_)
    _CACHE[path] = (w, h, grid)
    return _CACHE[path]


def crop_is_repeat(w, h, grid, win_w, win_h):
    """Does the window cut away only a repeat of the last kept pixels?"""
    vis_w, vis_h = min(w, win_w), min(h, win_h)
    if vis_w <= 0 or vis_h <= 0:
        return False, "window %dx%d shows none of the %dx%d bitmap" % (
            win_w, win_h, w, h)
    for x in range(win_w, w):
        for y in range(vis_h):
            if grid[y][x] != grid[y][vis_w - 1]:
                return False, ("column %d differs from the last kept column %d "
                               "at y=%d" % (x, vis_w - 1, y))
    for y in range(win_h, h):
        for x in range(vis_w):
            if grid[y][x] != grid[vis_h - 1][x]:
                return False, ("row %d differs from the last kept row %d "
                               "at x=%d" % (y, vis_h - 1, x))
    return True, ""


def last_change_col(w, h, grid):
    for x in range(w - 1, 0, -1):
        for y in range(h):
            if grid[y][x] != grid[y][x - 1]:
                return x
    return None


def art_dirs(tag):
    sfx = ("-" + tag) if tag else ""
    d = [os.path.join(DS, "stage-tp-%s%s" % (p, sfx)) for p in PKGS]
    d.append(os.path.join(DS, "stage%s" % sfx))            # in-place + clones
    d.append(os.path.join(TOOLS, "upscale",
                          "preview-%s" % tag if tag else "preview", "SimCity_1"))
    return [x for x in d if os.path.isdir(x)]


def find_art(tgi, dirs):
    names = ["T-0x856ddbac_G-0x%08x_I-0x%08x.png" % tgi,
             "T-856ddbac_G-%08x_I-%08x.png" % tgi]
    for d in dirs:
        for n in names:
            p = os.path.join(d, n)
            if os.path.isfile(p):
                return p
    return None


def check_tier(tag, selftest, report):
    label = tag or "2x"
    sfx = ("-" + tag) if tag else ""
    dirs = art_dirs(tag)
    base_dirs = [TP_ART, SRC1X]
    checked = untestable = preexisting = 0
    for pkg in PKGS:
        sdir = os.path.join(DS, "stage-tp-%s%s" % (pkg, sfx))
        if not os.path.isdir(sdir):
            continue
        for fn in sorted(os.listdir(sdir)):
            if not fn.lower().endswith(".ui"):
                continue
            iid = re.search(r"I-0x([0-9a-f]{8})", fn)
            iid = iid.group(1) if iid else fn
            with open(os.path.join(sdir, fn), "r", encoding="latin-1") as f:
                nodes = bmp_nodes(f.read())
            src = os.path.join(TP_SRC, "T-00000000_G-96a006b0_I-%s.ui" % iid)
            base = []
            if os.path.isfile(src):
                with open(src, "r", encoding="latin-1") as f:
                    base = bmp_nodes(f.read())
            if base and len(base) != len(nodes):
                report.append("%-4s %s: staged has %d GZWinBMP nodes, the 1x "
                              "source has %d - cannot pair them"
                              % (label, iid, len(nodes), len(base)))
                base = []
            for k, (tgi, (ww, wh), rect) in enumerate(nodes):
                path = find_art(tgi, dirs)
                if path is None:
                    report.append("%-4s %s node %d {%08x,%08x}: art NOT FOUND "
                                  "- not checked, not passed"
                                  % ((label, iid, k) + tgi))
                    continue
                w, h, grid = pixels(path)
                checked += 1
                if selftest:
                    lc = last_change_col(w, h, grid)
                    if lc is None:
                        untestable += 1
                        continue
                    ok, why = crop_is_repeat(w, h, grid, lc, h)
                    if ok:
                        report.append("SELFTEST %s %s node %d: cut at column "
                                      "%d was NOT detected" % (label, iid, k, lc))
                    continue

                # ---- A: the crop may not read past the bitmap (#95) --------
                if rect and (rect[0] > w or rect[1] > h):
                    report.append("%-4s %s node %d {%08x,%08x}: imagerect %dx%d "
                                  "OVER-READS a %dx%d bitmap"
                                  % ((label, iid, k) + tgi + (rect[0], rect[1], w, h)))
                    continue

                # ---- B: the drawn slice must still COVER ITS WINDOW --------
                # THE ONE THAT WOULD HAVE CAUGHT THE SHIPPED DEFECT, and the
                # first draft of it asked the wrong question. Comparing the
                # rect to the BITMAP flags the m3 glyph, whose bitmap snapped
                # 20 -> 32 while its rect and window both went 20 -> 30: two
                # pixels of transparent padding go undrawn and nothing is
                # wrong. What actually decides the screen is how much of the
                # WINDOW gets painted:
                #
                #   stripe, shipped : slice min(285,429)=285 in a 428 window
                #                     -> 143px of bare window, the short stripe
                #   stripe, fixed   : slice min(428,429)=428 in a 428 window
                #   m3 glyph        : slice min(30,32)=30  in a 30  window
                #
                # Compare that coverage against 1x. A crop the mod itself made
                # smaller than its window stays legal; losing coverage we had
                # at 1x does not.
                if rect and base:
                    btgi, (bw0, bh0), brect = base[k]
                    bpath = find_art(btgi, base_dirs)
                    if brect and bpath:
                        w1, h1, _g = pixels(bpath)
                        for ax, (sf, wf, s1, w1x) in enumerate(
                                ((min(rect[0], w), ww, min(brect[0], w1), bw0),
                                 (min(rect[1], h), wh, min(brect[1], h1), bh0))):
                            if w1x <= 0 or wf <= 0:
                                continue
                            want = min(wf, int(s1 * wf / float(w1x) + 0.5))
                            if sf < want - 1:
                                report.append(
                                    "%-4s %s node %d {%08x,%08x}: the drawn "
                                    "slice paints %d of the %dpx window %s "
                                    "where 1x painted %d of %d - about %d "
                                    "expected. %dpx of window is left bare."
                                    % ((label, iid, k) + tgi
                                       + (sf, wf, "width" if ax == 0 else "height",
                                          s1, w1x, want, wf - sf)))

                # ---- C: what the WINDOW cuts must repeat the edge ----------
                # The drawn source is the imagerect slice, so clip to it first.
                vis_w = min(w, rect[0]) if rect else w
                vis_h = min(h, rect[1]) if rect else h
                ok, why = crop_is_repeat(vis_w, vis_h, grid, ww, wh)
                if ok:
                    continue
                # Ours, or CAM's own? Re-ask at 1x with the mod's own numbers.
                pre = None
                if base:
                    btgi, (bw, bh), brect = base[k]
                    bpath = find_art(btgi, base_dirs)
                    if bpath:
                        w1, h1, g1 = pixels(bpath)
                        pre, _ = crop_is_repeat(min(w1, brect[0]) if brect else w1,
                                                min(h1, brect[1]) if brect else h1,
                                                g1, bw, bh)
                        pre = not pre
                if pre:
                    preexisting += 1
                    continue
                report.append("%-4s %s node %d {%08x,%08x}: art %dx%d in window "
                              "%dx%d - %s%s"
                              % ((label, iid, k) + tgi + (w, h, ww, wh, why,
                                 "" if base else "  [no 1x baseline]")))
    return checked, untestable, preexisting


def main():
    argv = sys.argv[1:]
    selftest = "--selftest" in argv
    tier = argv[argv.index("--tier") + 1] if "--tier" in argv else "all"
    tags = ["15x", "", "3x"] if tier == "all" else ["" if tier == "2x" else tier]

    print("GATE #154 - a scaled third-party bitmap may only lose a REPEAT of "
          "its own edge")
    if selftest:
        print("NEGATIVE CONTROL: window edge placed on the rightmost column "
              "that differs from its neighbour; every testable node MUST fail")
    total = tested = pre = 0
    report = []
    for tag in tags:
        n, un, px = check_tier(tag, selftest, report)
        total += n
        tested += n - un
        pre += px
        if n:
            print("  %-4s %d GZWinBMP node(s): %d testable, %d pre-existing "
                  "1x crop(s) ignored" % (tag or "2x", n, n - un, px))
    if total == 0:
        sys.exit("REFUSAL: 0 nodes checked - the gate is blind, not green. "
                 "Build the third-party stages first.")
    for line in report:
        print("  " + ("!! " if not selftest else "") + line)
    if selftest:
        if tested == 0:
            sys.exit("SELFTEST INCONCLUSIVE: every bitmap is uniform, so none "
                     "could be made to fail")
        if report:
            sys.exit("SELFTEST FAILED: %d node(s) the comparator should have "
                     "caught went undetected" % len(report))
        print("SELFTEST PASS: all %d testable node(s) failed as required" % tested)
        return
    if report:
        sys.exit("FAIL: %d finding(s)" % len(report))
    print("PASS: %d node(s) across %d tier(s); nothing visible is cut that 1x "
          "kept (%d pre-existing mod crop(s) ignored)"
          % (total, len(tags), pre))


main()
