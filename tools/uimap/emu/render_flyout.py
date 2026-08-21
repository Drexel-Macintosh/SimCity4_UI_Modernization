r"""RENDER a flyout offline, from the SHIPPED art, and LOOK AT IT.

WHY THIS EXISTS. Every other gate in this directory is arithmetic - the
README says so itself: "IT NEVER LOOKS AT A PIXEL... 'the model passes' and
'the screen is right' are different claims." That gap cost nine failed fixes on
the 1.5x Day/Night trailing-edge lines, because every theory was checked against
a number instead of against an image.

This composites ONE window subtree the way GZWinBMP/GZWinBtn do, into a PNG:

  * a child's pixels come from `image={g,i}`, cropped by `imagerect` if present
  * a GZWinBtn with NO `imagerect` uses the WHOLE sheet as a 4-state strip and
    draws cell `state` of width `sheetW/4` (`states=4` is the SC4 default; the
    8-state and 2-state variants take --states)
  * MAGENTA 0xFF00FF is SC4's colour KEY, not a colour - it is punched to alpha
  * the blit is 1:1 into the child's top-left and CLIPPED to the child rect;
    it is NOT stretched to fit

It renders the same subtree at more than one candidate geometry rule, because
the staged `.UI` keeps 1x areas at the fractional tiers (geometry is applied at
runtime by ScaleSubtree) and the exact rounding rule is the thing in question:

    edges  left,top,right,bottom each RoundHalfUp(v*f)   -> size can drift +-1
    size   left,top RoundHalfUp, then w,h RoundHalfUp    -> size never drifts

A magenta 1px frame is drawn around each child rect so a mismatch between the
window box and the art it holds is VISIBLE rather than inferred.

    python render_flyout.py --script T-00000000_G-96a006b0_I-aa356502.ui \
                            --tier 15x --out daynight-15x.png
    python render_flyout.py --script ... --tier 1x --out daynight-1x.png

Offline. No game, no exe, no DLL.
"""
import argparse
import os
import re
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
SS = os.path.join(ROOT, "tools", "selective-safe")
SRC1X_UI = os.path.join(ROOT, "tools", "uiscripts", "extracted")
SRC1X_ART = os.path.join(ROOT, "tools", "dbpf", "extracted", "SimCity_1")

TIERS = {"1x": (None, 1.0), "15x": ("stage-15x", 1.5),
         "2x": ("stage", 2.0), "3x": ("stage-3x", 3.0)}

MAGENTA = (255, 0, 255)

RE_NODE = re.compile(r"<LEGACY\s+(.*?)>", re.S)
RE_ATTR_AREA = re.compile(r"area=\((-?\d+),(-?\d+),(-?\d+),(-?\d+)\)")
RE_ATTR_IMAGE = re.compile(r"image=\{([0-9a-fA-Fx]+),([0-9a-fA-Fx]+)\}")
RE_ATTR_RECT = re.compile(r"imagerect=\((-?\d+),(-?\d+),(-?\d+),(-?\d+)\)")
RE_ATTR_ID = re.compile(r"\bid=(0x[0-9a-fA-F]+)")
RE_ATTR_CLS = re.compile(r"clsid=(\S+)")
RE_VISIBLE = re.compile(r"winflag_visible=(\w+)")


# ONE SOURCE FOR THE SCALING RULES (scale_rules.py). This file used to
# carry its own copy; #162 changed ScaleRound in the DLL and every private
# copy in this folder had to be found by hand. `scale_rules.py --drift`
# hunts any that come back.
from scale_rules import round_half_up          # noqa: E402


def art_dir(tier):
    sub = TIERS[tier][0]
    return SRC1X_ART if sub is None else os.path.join(SS, sub)


def load_art(tier, gid, iid):
    d = art_dir(tier)
    names = ["T-0x856ddbac_G-0x%08x_I-0x%08x.png" % (gid, iid),
             "T-856ddbac_G-%08x_I-%08x.png" % (gid, iid),
             "T-0x856DDBAC_G-0x%08X_I-0x%08X.png" % (gid, iid)]
    for n in names:
        p = os.path.join(d, n)
        if os.path.isfile(p):
            return Image.open(p).convert("RGBA")
    # a tier package only carries the art it REPLACES; fall back to 1x so a
    # missing override shows up as a too-small icon rather than a blank hole
    if tier != "1x":
        return load_art("1x", gid, iid)
    return None


def key_out(im):
    """Punch SC4's magenta colour key to alpha. Exact match only - any
    tolerance here would eat real pixels, and an interpolating resampler is
    already banned upstream for exactly that reason."""
    px = im.load()
    w, h = im.size
    n = 0
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if (r, g, b) == MAGENTA:
                px[x, y] = (0, 0, 0, 0)
                n += 1
    return n


def parse(path):
    with open(path, "r", encoding="latin-1") as f:
        txt = f.read()
    nodes = []
    for m in RE_NODE.finditer(txt):
        a = m.group(1)
        ar = RE_ATTR_AREA.search(a)
        if not ar:
            continue
        node = {
            "area": tuple(int(x) for x in ar.groups()),
            "id": RE_ATTR_ID.search(a).group(1) if RE_ATTR_ID.search(a) else "-",
            "cls": RE_ATTR_CLS.search(a).group(1) if RE_ATTR_CLS.search(a) else "?",
            "visible": (RE_VISIBLE.search(a).group(1) == "yes"
                        if RE_VISIBLE.search(a) else True),
            "image": None, "rect": None,
        }
        im = RE_ATTR_IMAGE.search(a)
        if im:
            node["image"] = (int(im.group(1), 16), int(im.group(2), 16))
        rc = RE_ATTR_RECT.search(a)
        if rc:
            node["rect"] = tuple(int(x) for x in rc.groups())
        nodes.append(node)
    return nodes


def scale_area(area, f, rule):
    l, t, r, b = area
    if f == 1.0:
        return l, t, r, b
    if rule == "edges":
        return (round_half_up(l * f), round_half_up(t * f),
                round_half_up(r * f), round_half_up(b * f))
    sl, st = round_half_up(l * f), round_half_up(t * f)
    return (sl, st,
            sl + round_half_up((r - l) * f), st + round_half_up((b - t) * f))


def render(script, tier, rule, states, out):
    f = TIERS[tier][1]
    src = os.path.join(SRC1X_UI, script)
    if not os.path.isfile(src):
        sys.exit("no such 1x script: " + src)
    nodes = parse(src)
    if not nodes:
        sys.exit("no LEGACY nodes parsed")

    root, children = nodes[0], nodes[1:]
    rl, rt, rr, rb = scale_area(root["area"], f, rule)
    W, H = rr - rl, rb - rt
    canvas = Image.new("RGBA", (W + 40, H + 40), (32, 32, 40, 255))
    print("  root %s area=%s -> %dx%d  (rule=%s, f=%s)"
          % (root["id"], root["area"], W, H, rule, f))

    frame = Image.new("RGBA", (W + 40, H + 40), (0, 0, 0, 0))
    for n in children:
        if not n["visible"] or not n["image"]:
            continue
        cl, ct, cr, cb = scale_area(n["area"], f, rule)
        cw, ch = cr - cl, cb - ct
        art = load_art(tier, *n["image"])
        if art is None:
            print("     {%08x,%08x}  ART MISSING" % n["image"])
            continue
        aw, ah = art.size
        if n["rect"]:
            l, t, r, b = n["rect"]
            if f != 1.0:
                l, t, r, b = (round_half_up(l * f), round_half_up(t * f),
                              round_half_up(r * f), round_half_up(b * f))
            r, b = min(r, aw), min(b, ah)
            cell = art.crop((l, t, r, b))
            note = "rect=(%d,%d,%d,%d) art=%dx%d%s" % (
                l, t, r, b, aw, ah,
                "   <-- RECT SHORT OF ART by (%d,%d)" % (aw - r, ah - b)
                if (r < aw or b < ah) else "")
        else:
            cwid = aw // states
            cell = art.crop((0, 0, cwid, ah))
            note = "strip %dx%d /%d -> cell %dx%d%s" % (
                aw, ah, states, cwid, ah,
                "   <-- CELL WIDER THAN WINDOW by %d" % (cwid - cw)
                if cwid > cw else
                ("   <-- WINDOW WIDER THAN CELL by %d" % (cw - cwid)
                 if cw > cwid else ""))
            if ah > ch:
                note += "   <-- CELL TALLER THAN WINDOW by %d" % (ah - ch)
            elif ch > ah:
                note += "   <-- WINDOW TALLER THAN CELL by %d" % (ch - ah)
        key_out(cell)
        canvas.alpha_composite(cell, (20 + cl, 20 + ct))
        # window box, so a size disagreement is VISIBLE
        # CLAMP BOTH ENDS, NOT JUST THE TOP-LEFT. `max(0, ct)` guarded the top
        # edge but `min(H-1, cb-1)` can still go NEGATIVE for a window that sits
        # entirely above/left of the frame origin, and PIL then raises
        # IndexError. MEASURED 2026-08-16: this crashed the compositor on the
        # city HUD scripts (T-00000000_G-96a006b0_I-2bc90671.ui), which is why
        # the HUD had never been rendered offline - the tool looked like it did
        # not support the HUD when in fact it just fell over on one marker.
        def _cy(v):
            return 20 + min(H - 1, max(0, v))

        def _cx(v):
            return 20 + min(W - 1, max(0, v))

        for x in range(max(0, cl), min(W, cr)):
            frame.putpixel((_cx(x), _cy(ct)), (0, 255, 128, 200))
            frame.putpixel((_cx(x), _cy(cb - 1)), (0, 255, 128, 200))
        for y in range(max(0, ct), min(H, cb)):
            frame.putpixel((_cx(cl), _cy(y)), (0, 255, 128, 200))
            frame.putpixel((_cx(cr - 1), _cy(y)), (0, 255, 128, 200))
        print("     %-10s win=(%d,%d,%d,%d) %dx%d  %s"
              % (n["id"], cl, ct, cr, cb, cw, ch, note))

    flat = canvas.copy()
    flat.alpha_composite(frame)
    scale = 3 if max(W, H) < 400 else 2
    flat = flat.resize((flat.width * scale, flat.height * scale), Image.NEAREST)
    canvas = canvas.resize((canvas.width * scale, canvas.height * scale),
                           Image.NEAREST)
    canvas.convert("RGB").save(out)
    boxed = os.path.splitext(out)[0] + "-boxes.png"
    flat.convert("RGB").save(boxed)
    print("  wrote %s  and  %s  (x%d nearest)" % (out, boxed, scale))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--script", required=True)
    ap.add_argument("--tier", default="15x", choices=sorted(TIERS))
    ap.add_argument("--rule", default="edges", choices=("edges", "size"))
    ap.add_argument("--states", type=int, default=4)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    render(a.script, a.tier, a.rule, a.states, a.out)


main()
