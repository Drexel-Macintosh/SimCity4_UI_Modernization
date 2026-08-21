r"""#162 - find every place where SHIPPED art cannot cover its SCALED window.

WHY THIS EXISTS. Two hairlines (under the mayor's hat, under the advisor
portraits) survived five fixes and three probes. Every one of those reasoned
from a MECHANISM - art snapping, tiled sizing, 9-slice sizing, a runtime-bitmap
underfill - and every one was wrong. This asks the only question that decides
whether a hairline can exist, and it asks it of the FILES WE SHIP:

    does the art we ship COVER the window the sweep scales it into?

THE .UI IS NOT SCALED. Verified: `stage`, `stage-15x` and `stage-3x` carry
BYTE-IDENTICAL rects to the 1x original (checked on id 0xca9df380 - all three
read (719,87,847,124)). Only the ART is scaled offline; the WINDOW is scaled at
runtime by UiSpike. A first version of this gate compared staged rects against
staged art and reported 287 "underfills" at every tier - that was measuring a 1x
window against 2x art, and it is the reason this warning is here.

So the window side is MODELLED, exactly as UiSpike.cpp::ScaleSubtree does it -
edge-derived, rounded in the parent's ABSOLUTE DESIGN frame (#161):
    newW = R(absL + w) - R(absL),  R = llround
and the art side is MEASURED from the PNG that tier actually ships.

ROLES, because coverage means a different thing for each (law 86):

  blttype=tiled          the engine repeats the source across the dest, so any
                         art covers any window.                      SKIPPED
  blttype=edge / 9-slice cell = W/3 and the three spans are [0,c] [c,W-c]
                         [W-c,W], which tile any width exactly.      SKIPPED
  GZWinBtn state strip   the sheet holds N states side by side; ONE state must
                         cover the window, so artW/N >= winW and artH >= winH.
  everything else        dst-follows-src (law 83): the engine draws the source
                         at the window's origin at its OWN size and never reads
                         the window's size. art < window is an UNCOVERED BAND -
                         the hairline.

CONTROLS, and they are the whole experiment:

  f=1  the stock build. Anything short here is short in the ORIGINAL game and
       is not ours - it is subtracted, never reported as a defect.
  f=2  the user's own words: "the lines don't exist at 2x". At an integer
       factor R is exact and the 2x art is an exact doubling, so every node
       clean at 1x MUST come back clean. If 2x reports a fresh underfill, this
       model is broken and nothing it says about 1.5x is usable (law 88).

    python gate_art_vs_window.py [--top N] [--ui <8hex>] [--all]

Offline, read-only.
"""
import math
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(os.path.dirname(HERE))
SEL = os.path.join(TOOLS, "selective-safe")
UPS = os.path.join(TOOLS, "upscale")

# The 1x art size is derived as art2x/2 - the 2x pass is an exact doubling, so
# this is a division, not an estimate. It saves needing a 1x PNG export that
# this repo does not keep.
STAGE2X = os.path.join(SEL, "stage")
TIERS = [(1.0, STAGE2X, 2), (2.0, STAGE2X, 1),
         (1.5, os.path.join(SEL, "stage-15x"), 1)]

ATTR = re.compile(r'(\w+)=("[^"]*"|\{[^}]*\}|\([^)]*\)|\S+)')
TAG = re.compile(r"<(/?)(LEGACY|CHILDREN)([^>]*)>")
RECT = re.compile(r"\((-?\d+),(-?\d+),(-?\d+),(-?\d+)\)")
IMG = re.compile(r"\{([0-9a-fA-F]+),([0-9a-fA-F]+)\}")


# ONE SOURCE FOR THE SCALING RULES (scale_rules.py). This file used to
# carry its own copy; #162 changed ScaleRound in the DLL and every private
# copy in this folder had to be found by hand. `scale_rules.py --drift`
# hunts any that come back.
# To reproduce the #162 DEFECT (and re-prove this gate can still see it),
# swap the import below for `llround_scale as R` - the refuted pre-#162 rule,
# kept named and exported in scale_rules.py for exactly this purpose. That must
# put node #17 of I-0xc973b411 back on the 1.5x-only list with dH=+1, and must
# leave the f=2 control at 0. A gate that reports clean with BOTH rules is not
# measuring anything.
from scale_rules import scale_round as R          # noqa: E402


def png_size(path):
    with open(path, "rb") as fh:
        head = fh.read(24)
    if len(head) < 24 or head[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    return struct.unpack(">II", head[16:24])


def load_list(name, with_count=False):
    out = {} if with_count else set()
    path = os.path.join(UPS, name)
    if not os.path.exists(path):
        return out
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        p = line.split()
        if len(p) < 2:
            continue
        key = "%s:%s" % (p[0].lower().rjust(8, "0"), p[1].lower().rjust(8, "0"))
        if with_count:
            out[key] = int(p[2]) if len(p) > 2 else 4
        else:
            out.add(key)
    return out


STRIPS = load_list("cell-strips.txt", with_count=True)
NINE = load_list("nine-slice.txt")


def art_index(stage_dir):
    idx = {}
    for fn in os.listdir(stage_dir):
        if not fn.lower().endswith(".png"):
            continue
        m = re.search(r"G-0x([0-9a-fA-F]+)_I-0x([0-9a-fA-F]+)", fn)
        if not m:
            continue
        sz = png_size(os.path.join(stage_dir, fn))
        if not sz:
            continue
        idx["%s:%s" % (m.group(1).lower().rjust(8, "0"),
                       m.group(2).lower().rjust(8, "0"))] = sz
    return idx


# THE COMPARABLE SET IS COMPUTED ONCE, FOR ALL THREE TIERS.
# The first run of this gate built a separate index per tier and derived 1x by
# halving the 2x art INSIDE that pass. Any sheet the 2x package leaves at 1x
# (the LEFT1X cases) has odd dimensions, so it silently dropped out of the f=1
# scan while staying in the f=2 scan - and reappeared as 32 "new at f=2"
# shortfalls, i.e. the control failed for a bookkeeping reason and not a real
# one. A node is only ever compared if EVERY tier can price it.
ART2X = art_index(STAGE2X)
ART15 = art_index(os.path.join(SEL, "stage-15x"))
USABLE = {}
for k, (w2, h2) in ART2X.items():
    if k not in ART15 or w2 % 2 or h2 % 2:
        continue
    USABLE[k] = {1.0: (w2 // 2, h2 // 2), 2.0: (w2, h2), 1.5: ART15[k]}


def walk(text):
    out, depth = [], 0
    for m in TAG.finditer(text):
        close, tag, body = m.group(1), m.group(2), m.group(3)
        if tag == "CHILDREN":
            depth += -1 if close else 1
            continue
        out.append((depth, dict(ATTR.findall(body))))
    return out


def nodes_with_abs(text):
    """-> [(nodeIndex, attrs, absL, absT, w, h)] over the whole file."""
    out = []
    stack = {0: (0, 0)}
    for i, (depth, a) in enumerate(walk(text)):
        m = RECT.match(a.get("area", ""))
        if not m:
            continue
        l, t, r, b = (int(x) for x in m.groups())
        pl, pt = stack.get(depth, (0, 0))
        aL, aT = pl + l, pt + t
        stack[depth + 1] = (aL, aT)
        out.append((i, a, aL, aT, r - l, b - t))
    return out


def scan(f, ui_filter=None):
    """-> (checked, {nodekey: (dW, dH, detail)}) for every image node SHORT."""
    checked, bad = 0, {}
    for fn in sorted(os.listdir(STAGE2X)):
        if not fn.lower().endswith(".ui"):
            continue
        if ui_filter and ui_filter not in fn.lower():
            continue
        text = open(os.path.join(STAGE2X, fn), encoding="latin-1").read()
        for idx, a, aL, aT, w, h in nodes_with_abs(text):
            mi = IMG.search(a.get("image", ""))
            if not mi or w <= 0 or h <= 0:
                continue
            key = "%s:%s" % (mi.group(1).lower().rjust(8, "0"),
                             mi.group(2).lower().rjust(8, "0"))
            if key not in USABLE:
                continue                      # not priceable at every tier
            blt = a.get("blttype", "").strip('"')
            if blt == "tiled":
                continue                      # repeats: always covers
            if blt == "edge" or a.get("edgeimage") == "yes" or key in NINE:
                continue                      # 9-slice: covers any size
            aw, ah = USABLE[key][f]
            # The state count is a property of the SHEET, so it is inferred
            # ONCE from the 1x art against the design width - never per tier,
            # or the same node gets a different n at 1.5x than at 2x and the
            # comparison stops being a comparison.
            w1x = USABLE[key][1.0][0]
            n = STRIPS.get(key, 0)
            if not n:
                n = w1x // w if (w > 0 and w1x >= w and w1x % w == 0
                                 and a.get("clsid") == "GZWinBtn") else 1
            if n > 1 and aw % n:
                continue                      # not a clean strip; not ours
            cellW = aw // n
            winW = R(aL + w, f) - R(aL, f)
            winH = R(aT + h, f) - R(aT, f)
            checked += 1
            dW, dH = winW - cellW, winH - ah
            if dW > 0 or dH > 0:
                bad[(fn, idx)] = (dW, dH,
                                  "%-9s n=%d art %dx%d cell %dx%d  win %dx%d "
                                  "id=%s tgi=%s"
                                  % (a.get("clsid", "?"), n, aw, ah, cellW, ah,
                                     winW, winH, a.get("id", "-"), key))
    return checked, bad


def main():
    top = int(sys.argv[sys.argv.index("--top") + 1]) if "--top" in sys.argv else 40
    uif = sys.argv[sys.argv.index("--ui") + 1].lower() if "--ui" in sys.argv else None
    show_all = "--all" in sys.argv

    if not USABLE:
        print("0 sheets priceable at every tier - a REFUSAL, not a pass.")
        return 1
    print("%d sheets priceable at 1x/1.5x/2x (of %d shipped at 2x)"
          % (len(USABLE), len(ART2X)))
    res = {}
    for f in (1.0, 2.0, 1.5):
        res[f] = scan(f, uif)
        print("f=%-4s %5d image-bound nodes checked, %4d SHORT"
              % (f, res[f][0], len(res[f][1])))

    if res[1.0][0] == 0:
        print("\n0 nodes checked - a REFUSAL, not a pass.")
        return 1

    stock = set(res[1.0][1])
    new2 = set(res[2.0][1]) - stock
    new15 = set(res[1.5][1]) - stock

    print("\nshort at f=1 (STOCK, subtracted)      : %d" % len(stock))
    print("NEW at f=2 (must be 0 - the control)  : %d" % len(new2))
    print("NEW at f=1.5 (the defect)             : %d" % len(new15))

    if new2:
        print("\nCONTROL FAILED: f=2 invented %d shortfalls that stock does "
              "not have. At an integer factor that is impossible, so the model "
              "is wrong and the 1.5x list below is not evidence." % len(new2))
        for k in list(new2)[:10]:
            print("     %s  %s" % (k[0].split("I-0x")[-1][:8], res[2.0][1][k][2]))
        return 1

    rows = sorted(new15, key=lambda k: -(res[1.5][1][k][0] + res[1.5][1][k][1]))
    if not rows:
        print("\nNo 1.5x-only shortfall. The shipped art covers every shipped "
              "window at 1.5x under this model, so the hairline is NOT an "
              "art-vs-window size mismatch - the next instrument must look "
              "somewhere else.")
        return 0

    print("\n1.5x-ONLY shortfalls (window minus art; positive = uncovered):")
    for k in rows[:top]:
        dW, dH, why = res[1.5][1][k]
        print("   %s #%-4d dW=%+d dH=%+d  %s"
              % (k[0].split("I-0x")[-1][:8], k[1], dW, dH, why))
    if show_all and stock:
        print("\nstock shortfalls (informational, NOT ours):")
        for k in list(stock)[:top]:
            dW, dH, why = res[1.0][1][k]
            print("   %s #%-4d dW=%+d dH=%+d  %s"
                  % (k[0].split("I-0x")[-1][:8], k[1], dW, dH, why))
    return 0


sys.exit(main())
