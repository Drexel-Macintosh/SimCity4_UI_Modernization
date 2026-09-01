r"""RENDER A STATIC DIALOG OFFLINE, AT 1x AND AT A TIER, AND DIFF THEM.

WHY THIS EXISTS. Twice on #155 the defect was described as "white lines" /
"tearing to the right of the population" and twice it could not be pinned to a
control from the numbers alone. Every other instrument here reports GEOMETRY -
`emu\README.md` says of the whole suite, "IT NEVER LOOKS AT A PIXEL". A hairline
between two abutting blits is invisible to a geometry gate by construction:
both rectangles are exactly where they should be, and the seam is what is NOT
covered by either.

So this composites the actual bitmaps the way the engine does:

  * node `area=` is RELATIVE TO ITS PARENT - resolved to absolute here
  * `GZWinBMP blttype=normal` draws its `imagerect` slice at the window origin
    at NATIVE SIZE and lets the window CLIP it (never stretches - #154)
  * `GZWinBtn` on an N-state strip draws state 0: the leftmost cell
  * magenta 0xFF00FF is the colour key and composites as transparent

It then renders the SAME dialog from the 1x sources, upscales that reference
with NEAREST (never a resampler - a smooth filter would invent the very
hairlines we are hunting), and reports every pixel that is background in the
tier render but covered in the reference. Those are the seams.

WHAT THIS IS NOT. It is not the game. It ignores z-order subtleties, text,
edge/tiled blits and every runtime-drawn element. A CLEAN result here is NOT
proof the screen is clean; a DIRTY result names a real uncovered pixel and
where it is. Read it as a locator, not as a verdict.

    python render_dialog.py ca539340 [--tier 15x] [--out DIR]

Offline. Reads build outputs only.
"""
import os
import re
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(os.path.dirname(HERE))
DS = os.path.join(TOOLS, "dialog-static")
SRC1X_UI = os.path.join(TOOLS, "uiscripts", "extracted")
TP_SRC_UI = os.path.join(DS, "thirdparty-src")
SRC1X_ART = os.path.join(TOOLS, "dbpf", "extracted", "SimCity_1")
TP_ART = os.path.join(DS, "thirdparty-art")

KEY = (255, 0, 255)
TAG = re.compile(r"<(/?)(LEGACY|CHILDREN)([^>]*)>")
ATTR = re.compile(r'(\w+)=("[^"]*"|\{[^}]*\}|\([^)]*\)|\S+)')


def parse(text):
    """[(depth, attrs)] in document order, with CHILDREN nesting tracked."""
    out, depth = [], 0
    for m in TAG.finditer(text):
        close, tag, body = m.group(1), m.group(2), m.group(3)
        if tag == "CHILDREN":
            depth += -1 if close else 1
            continue
        out.append((depth, dict(ATTR.findall(body))))
    return out


def rect(s):
    m = re.match(r"\((-?\d+),(-?\d+),(-?\d+),(-?\d+)\)", s or "")
    return tuple(int(x) for x in m.groups()) if m else None


def load(path):
    im = Image.open(path).convert("RGBA")
    px = im.load()
    for y in range(im.height):
        for x in range(im.width):
            if px[x, y][:3] == KEY:
                px[x, y] = (0, 0, 0, 0)
    return im


def find_art(dirs, gid, iid):
    for d in dirs:
        for n in ("T-0x856ddbac_G-0x%08x_I-0x%08x.png" % (gid, iid),
                  "T-856ddbac_G-%08x_I-%08x.png" % (gid, iid)):
            p = os.path.join(d, n)
            if os.path.isfile(p):
                return p
    return None


def nine_slice(im, dw, dh, cell=None):
    r"""The engine's 9-slice, mirrored: corners 1:1, edges and centre stretched.

    THE CELL IS TWO NUMBERS, ONE PER AXIS - `(srcW/3, srcH/3)`. Every drawer on
    this path forms the two quotients separately.

    SUPERSEDED 2026-08-31 - kept, per annotate-never-rewrite. This read:
    "`cell` IS A SINGLE NUMBER AND IT COMES FROM THE WIDTH: `img->Width()/3`
    (NineSlice at VA `0x00794100`, one caller). It is applied to BOTH axes, so a
    non-square source does NOT get a proportional vertical band - that is the
    engine's behaviour, not an approximation here." BOTH HALVES ARE WRONG, and
    the code implemented the wrong half:

      * WRONG DRAWER. `0x00794100` is `cSC4WinAlertBorder`'s own slot-88 draw.
        That window is created in code and appears in NO `.UI` script: grep its
        clsid `ca5d3294` over `tools\uiscripts\extracted` - 0 hits in 331 files,
        while the same grep sees 2066 `clsid=GZWinBtn` and 845 `clsid=GZWinBMP`,
        so the null has its positive control. This function only renders nodes
        `is_edge()` picked out of a PARSED SCRIPT, so the alert border can never
        be one. The drawers that can are `GZWinBMP 0x009BC325` (EDGE branch) and
        `GZWinBtn 0x009B05E0`.
      * WRONG ARITHMETIC - on all three drawers. MEASURED 2026-08-31 from the
        shipped exe (`Apps\SimCity 4.exe`, ImageBase 0x00400000):
        `GZWinBMP` EDGE branch (entered at `0x009BC411` off the `jne` at
        `0x009BC3B7`): `idiv ecx` at `0x009BC418` on `[ebp-8]`, again at
        `0x009BC423` on `[ebp-4]`, off ONE shared `push 3; pop ecx`; cell rect
        handed to `0x008D8800` is `(l, t, r/3, b/3)`. `GZWinBtn`: `idiv esi` at
        `0x009B05E9`, `idiv ebx` at `0x009B0602`; its cell is `((r-l)/3,(b-t)/3)`
        based at `(l,t)` - a DIFFERENT expression, do not carry one to the other.
        Even `0x00794100` is per-axis: two `0xAAAAAAAB` magic-multiply `/3` at
        `0x0079414D` and `0x00794161`. Corpus agrees: `SC4-UI-ENGINE.md` 4.6c,
        `BLIT-BEHAVIOUR.md` drawer table, `_tests\REGRESSION.md` "RESOLVED
        2026-08-18 - three addresses, three different JOBS".

    BLAST RADIUS OF THE OLD BEHAVIOUR, measured against the 30 sheets in
    `tools\upscale\nine-slice.txt`: 9 of 30 are non-square. `{46a006b0,4c0f0d31}`
    193x46: engine `(64,15)`, old `(23,23)` - the single number was additionally
    clamped by `im.height // 2`, which coupled the axes and crushed the
    HORIZONTAL cell too. `{46a006b0,144161f1}` 360x144: engine `(120,48)`, old
    `(72,72)`. `{1abe787d,8c0e0f2d}` 411x371: engine `(137,123)`, old
    `(137,137)`. The 21 SQUARE sheets come out byte-identical, so an earlier
    CLEAN result on a square-only dialog still stands.

    STILL OPEN: whether the `imagerect` a script DECLARES is the rect in
    `[this+0xE8]` at draw time (`SDK-GAPS.md` 2.1). The caller crops to
    `imagerect` BEFORE calling here, so an `edgeimage` node with a declared rect
    renders `((r-l)/3,(b-t)/3)`, matching NEITHER reading. Left alone
    DELIBERATELY - switching blind trades one wrong render for another.

    `cell` takes `(cx, cy)`, or `None` to derive `(W/3, H/3)`. A bare int is the
    legacy scalar form and is read as the HORIZONTAL cell ONLY.

    NEAREST for every stretch: an interpolating resize would invent colours the
    source lacks and turn this instrument into a generator of the exact artefact
    it exists to find (#143, the magenta-key rule). The `/3` here is the same
    integer divide that produced #143's 1.5x-only white seams.

    NEAREST for every stretch: an interpolating resize would invent colours the
    source lacks and turn this instrument into a generator of the exact artefact
    it exists to find (#143, the magenta-key rule).
    """
    if cell is None:
        cx, cy = im.width // 3, im.height // 3
    elif isinstance(cell, (tuple, list)):
        cx, cy = cell
    else:
        cx, cy = int(cell), im.height // 3   # legacy scalar: HORIZONTAL only
    # The clamps are an EMULATOR GUARD against a negative middle band, not
    # engine behaviour - and they are PER AXIS. The old shared clamp let a
    # short sheet shrink the horizontal cell (193x46 -> 23 instead of 64).
    cx = max(1, min(cx, im.width // 2, dw // 2))
    cy = max(1, min(cy, im.height // 2, dh // 2))
    out = Image.new("RGBA", (dw, dh), (0, 0, 0, 0))
    sx = [0, cx, im.width - cx, im.width]
    sy = [0, cy, im.height - cy, im.height]
    dx = [0, cx, dw - cx, dw]
    dy = [0, cy, dh - cy, dh]
    for i in range(3):
        for j in range(3):
            sw, sh = sx[i + 1] - sx[i], sy[j + 1] - sy[j]
            tw, th = dx[i + 1] - dx[i], dy[j + 1] - dy[j]
            if sw <= 0 or sh <= 0 or tw <= 0 or th <= 0:
                continue
            piece = im.crop((sx[i], sy[j], sx[i + 1], sy[j + 1]))
            if (tw, th) != (sw, sh):
                piece = piece.resize((tw, th), Image.NEAREST)
            out.alpha_composite(piece, (dx[i], dy[j]))
    return out


def is_edge(a):
    """A node that 9-slices: either script attribute puts it on that path."""
    return a.get("blttype") == "edge" or a.get("edgeimage") == "yes"


def render(nodes, art_dirs, states=4):
    root = rect(nodes[0][1].get("area"))
    W, H = root[2] - root[0], root[3] - root[1]
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    stack = {}                     # depth -> absolute origin of that parent
    stack[0] = (0, 0)
    missing = []
    for depth, a in nodes:
        r = rect(a.get("area"))
        if r is None:
            continue
        ox, oy = stack.get(depth, (0, 0))
        if depth == 0:
            ax, ay = 0, 0          # the root's own area is a screen position
        else:
            ax, ay = ox + r[0], oy + r[1]
        stack[depth + 1] = (ax, ay)
        w, h = r[2] - r[0], r[3] - r[1]
        gi = re.match(r"\{([0-9a-fA-F]+),([0-9a-fA-F]+)\}", a.get("image", ""))
        if not gi:
            continue
        gid, iid = int(gi.group(1), 16), int(gi.group(2), 16)
        p = find_art(art_dirs, gid, iid)
        if p is None:
            missing.append((gid, iid))
            continue
        im = load(p)
        ir = rect(a.get("imagerect"))
        if a.get("clsid") == "GZWinBtn" and ir is None and im.width % states == 0:
            im = im.crop((0, 0, im.width // states, im.height))   # state 0
        elif ir:
            im = im.crop((max(0, ir[0]), max(0, ir[1]),
                          min(im.width, ir[2]), min(im.height, ir[3])))
        if is_edge(a):
            # 9-slice STRETCHES to the window; it never clips. Both nodes of the
            # Reconcile Edges dialog are on this path and were previously
            # rendered here as plain clipped blits - i.e. wrong for exactly the
            # dialog under investigation.
            im = nine_slice(im, w, h, im.width // 3)
        else:
            im = im.crop((0, 0, min(im.width, w), min(im.height, h)))  # clip
        canvas.alpha_composite(im, (ax, ay))
    return canvas, missing


def script_for(iid, tier):
    sub = "stage-%s" % tier if tier != "2x" else "stage"
    for d in [os.path.join(DS, sub)] + [os.path.join(DS, x) for x in os.listdir(DS)
                                        if x.startswith("stage-tp-")]:
        p = os.path.join(d, "T-0x00000000_G-0x96a006b0_I-0x%s.ui" % iid)
        if os.path.isfile(p):
            return p, d
    return None, None


def main():
    iid = sys.argv[1]
    tier = sys.argv[sys.argv.index("--tier") + 1] if "--tier" in sys.argv else "15x"
    out = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else HERE
    f = {"15x": 1.5, "2x": 2.0, "3x": 3.0}[tier]

    sp, sdir = script_for(iid, tier)
    if sp is None:
        sys.exit("no staged script for %s at %s" % (iid, tier))
    one = None
    for cand in (os.path.join(SRC1X_UI, "T-00000000_G-96a006b0_I-%s.ui" % iid),
                 os.path.join(TP_SRC_UI, "T-00000000_G-96a006b0_I-%s.ui" % iid)):
        if os.path.isfile(cand):
            one = cand
            break
    if one is None:
        sys.exit("no 1x source for %s" % iid)

    with open(sp, "r", encoding="latin-1") as fh:
        tier_nodes = parse(fh.read())
    with open(one, "r", encoding="latin-1") as fh:
        one_nodes = parse(fh.read())

    a, miss_a = render(tier_nodes, [sdir, os.path.join(DS, "stage-%s" % tier
                                                       if tier != "2x" else "stage")])
    b, miss_b = render(one_nodes, [SRC1X_ART, TP_ART])
    pa = os.path.join(out, "render-%s-%s.png" % (iid, tier))
    pb = os.path.join(out, "render-%s-1x.png" % iid)
    a.save(pa)
    b.save(pb)
    print("wrote %s  (%dx%d)" % (pa, a.width, a.height))
    print("wrote %s  (%dx%d)" % (pb, b.width, b.height))
    if miss_a or miss_b:
        print("  ! art not found: tier=%s 1x=%s" % (miss_a, miss_b))

    # THE COMPARISON. Reference = the 1x render blown up NEAREST, so every
    # pixel of it is a real 1x pixel and nothing is invented at the edges.
    ref = b.resize((a.width, a.height), Image.NEAREST)
    ap, rp = a.load(), ref.load()
    holes = []
    for y in range(a.height):
        run = None
        for x in range(a.width):
            bad = ap[x, y][3] < 8 and rp[x, y][3] >= 8
            if bad and run is None:
                run = x
            elif not bad and run is not None:
                holes.append((y, run, x - 1))
                run = None
        if run is not None:
            holes.append((y, run, a.width - 1))
    if not holes:
        print("\nNO UNCOVERED PIXELS: every pixel painted at 1x is painted at "
              "%s too." % tier)
        return
    cols, rows = {}, {}
    for y, x0, x1 in holes:
        rows[y] = rows.get(y, 0) + (x1 - x0 + 1)
        for x in range(x0, x1 + 1):
            cols[x] = cols.get(x, 0) + 1
    print("\nUNCOVERED PIXELS (background where 1x had paint): %d px in %d runs"
          % (sum(rows.values()), len(holes)))
    print("  worst COLUMNS (x -> px tall): %s"
          % sorted(cols.items(), key=lambda t: -t[1])[:8])
    print("  worst ROWS    (y -> px wide): %s"
          % sorted(rows.items(), key=lambda t: -t[1])[:8])


main()
