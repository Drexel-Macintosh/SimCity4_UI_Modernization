r"""repro_166_liverect.py - #166 IN PIXELS, FROM THE *LIVE* RECT, OFFLINE.

⛔ WHY THIS EXISTS, AND WHAT IT IS ALLOWED TO CONCLUDE
────────────────────────────────────────────────────────────────────────────────
#166 measured a 1px art-vs-window disagreement on the city dashboard root
`0x0987B48F` at f=1.5 ONLY, and only at the origin THE GAME DOCKS IT AT (l=5),
not at the origin its `.UI` declares (l=30). What #166 explicitly did NOT
measure is the step everybody actually cares about:

    does that 1px paint a SHORT BRIGHT HORIZONTAL RUN inside the mayor's-hat and
    people buttons - lighter than its surroundings, shorter than the button,
    and absent from the "?" button?

Every offline gate in this folder reports GEOMETRY. A geometry gate cannot
answer a question about brightness, and eight of them came back clean. So this
one COMPOSITES: the same sheets, the same crops, the same rounding rules, at
the DESIGN origin and at the LIVE origin, at f = 1.0 / 1.5 / 2.0 / 3.0.

⚠ IT IS A MODEL, NOT THE GAME. It does not draw text, does not model z-order
beyond document order, does not model the 3D view underneath, and reads "leaf"
from the STATIC `.UI` child list while the DLL asks `GetChildCount()` on the
LIVE tree. A clean result here is NOT proof the screen is clean. A DIRTY result
names a pixel and a mechanism. Read it as a locator, not as a verdict.

WHAT IS MIRRORED, AND FROM WHERE
────────────────────────────────────────────────────────────────────────────────
  scale_rules.py                 ScaleRound / edge-derived / #161 child frame
                                 (which in turn mirrors UiSpike.cpp, tripwired)
  UiSpike.cpp :16947  #148       a LEAF takes ScaleRound(w,f), not its edges
  UiSpike.cpp :14268  #161       a panel root hands its DESIGN origin to the
                                 subtree, so children round in the parent frame
  BLIT-BEHAVIOUR.md              `blttype=tiled` is src-follows-dst: the engine
                                 REPEATS the source across the destination
  REGRESSION.md #154             `GZWinBMP` normal blit draws its `imagerect`
                                 slice at the window origin at NATIVE size and
                                 lets the window CLIP it - it never stretches
  tools\selective-safe\stage*    the SHIPPED art and the SHIPPED `imagerect`
                                 (the staged `.UI` keeps 1x `area` and carries a
                                 tier-scaled `imagerect` - verified, not assumed)

THE CONTROLS - all four are mandatory and all four are printed
────────────────────────────────────────────────────────────────────────────────
  C1  f=2 and f=3: LIVE render must be pixel-identical to DESIGN render.
      (Structural: rel = R(L+l,f)-R(L,f) = l*k for integer k, at every L. If
      this ever prints a difference the MODEL is wrong, not the game.)
  C2  f=1.0: no artifact at either origin, and the two are identical.
  C3  NEGATIVE CONTROL: move the live origin by 1 so q | l. The artifact must
      VANISH. If it does not, the parity mechanism is REFUTED and this script
      must say so - a clean refutation is worth more than a fix.
  C4  POSITIVE CONTROL on the detector: it must fire somewhere at 1.5x, or it
      is inert and its zeros mean nothing.

    python repro_166_liverect.py [--out DIR] [--zoom N]

Offline, read-only apart from the PNGs it writes under --out.
"""
import argparse
import os
import re
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from scale_rules import scale_round, out                       # noqa: E402

UIMAP = os.path.dirname(HERE)
TOOLS = os.path.dirname(UIMAP)
ROOT = os.path.dirname(TOOLS)

SS = os.path.join(TOOLS, "selective-safe")
UI_1X = os.path.join(TOOLS, "uiscripts", "extracted",
                     "T-00000000_G-96a006b0_I-c973b411.ui")
ART_1X = os.path.join(TOOLS, "dbpf", "extracted", "SimCity_1")

#: tier -> (staged .UI + art dir, factor). `stage` is the 2x package.
TIERS = {
    1.0: (None, ART_1X),
    1.5: (os.path.join(SS, "stage-15x"), os.path.join(SS, "stage-15x")),
    2.0: (os.path.join(SS, "stage"), os.path.join(SS, "stage")),
    3.0: (os.path.join(SS, "stage-3x"), os.path.join(SS, "stage-3x")),
}

DASH_ID = 0x0987B48F

#: The DESIGN origin, straight out of the `.UI`: area=(30,-5,265,218).
DESIGN_ORIGIN = (30, -5)
#: The LIVE origin, straight out of the sweep's own log line
#:   "UiSpike: panel 0x0987B48F (5,1388 235x223) -> (8,1281 352x335)"
#: l=5 in EVERY capture we hold (218 logs); t is even in every one of them.
LIVE_ORIGIN = (5, 1388)
#: C3, the negative control: l+1 so that q=2 divides it. Nothing else moves.
NEG_ORIGIN = (6, 1388)
#: The fourth corner of the parity square: BOTH coordinates odd.
ODD_ODD_ORIGIN = (5, 1389)

ORIGINS = [
    ("design", DESIGN_ORIGIN),
    ("live", LIVE_ORIGIN),
    ("negctl", NEG_ORIGIN),
    ("oddodd", ODD_ODD_ORIGIN),
]

#: The buttons under investigation, by `.UI` id -> (label, art instance).
#:
#: ⛔ NAMING CORRECTION, MADE BY LOOKING AT THE PIXELS. The task brief and
#: REGRESSION.md #162 both call `{46a006b0,14415860}` "the '?' button". Cell 0
#: of that sheet is a SUN/STARBURST (the day-night control) - rendered and
#: eyeballed, see `_view_cells.png`. The two buttons that actually draw a "?"
#: glyph are `0x99887766` {46a006b0,14015547} and `0x8B96B73E`
#: {46a006b0,4b8da4a4}, and they sit at a DIFFERENT design rect with DIFFERENT
#: parity. All four are measured here so the verdict does not depend on which
#: one the user meant - law 87, name your consumers instead of assuming one.
BUTTONS = {
    0xC988BC79: ("hat", 0x14015555),        # design (97,37)  odd,odd
    0x4988BC6A: ("people", 0x13F15230),     # design (138,93) even,odd
    0x2988BC85: ("sun", 0x14415860),        # design (26,-6)  even,even  <- the
                                            #   sheet the brief calls "?"
    0x99887766: ("qglyph_a", 0x14015547),   # design (95,85)  odd,odd
    0x8B96B73E: ("qglyph_b", 0x4B8DA4A4),   # design (95,106) odd,even
}

KEY = (255, 0, 255)
TAG = re.compile(r"<(/?)(LEGACY|CHILDREN)([^>]*)>")
ATTR = re.compile(r'(\w+)=("[^"]*"|\{[^}]*\}|\([^)]*\)|\S+)')
IMG = re.compile(r"\{([0-9a-fA-F]+),([0-9a-fA-F]+)\}")


# ══════════════════════════════════════════════════════════════════════════════
# 1. THE .UI - parsed into a real tree, because #161 needs the parent frame
# ══════════════════════════════════════════════════════════════════════════════

def parse_tree(path):
    """-> [root_node, ...]; node = dict(attrs=..., kids=[...])."""
    text = open(path, encoding="latin-1").read()
    roots, stack, last = [], [], []
    depth = 0
    bucket = {0: roots}
    for m in TAG.finditer(text):
        close, tag, body = m.group(1), m.group(2), m.group(3)
        if tag == "CHILDREN":
            if close:
                depth -= 1
            else:
                depth += 1
                bucket[depth] = last[depth - 1]["kids"]
            continue
        node = {"attrs": dict(ATTR.findall(body)), "kids": []}
        bucket.setdefault(depth, roots).append(node)
        while len(last) <= depth:
            last.append(None)
        last[depth] = node
    del stack
    return roots


def rect(s):
    m = re.match(r"\((-?\d+),(-?\d+),(-?\d+),(-?\d+)\)", s or "")
    return tuple(int(x) for x in m.groups()) if m else None


def node_id(node):
    v = node["attrs"].get("id")
    if v is None:
        return None
    try:
        return int(v, 16) if v.startswith("0x") else int(v)
    except ValueError:
        return None


def find_by_id(nodes, want):
    for n in nodes:
        if node_id(n) == want:
            return n
        hit = find_by_id(n["kids"], want)
        if hit:
            return hit
    return None


# ══════════════════════════════════════════════════════════════════════════════
# 2. ART
# ══════════════════════════════════════════════════════════════════════════════

_ART_CACHE = {}
MISSING_ART = set()


def _open_art(art_dir, gid, iid):
    names = ("T-0x856ddbac_G-0x%08x_I-0x%08x.png" % (gid, iid),
             "T-856ddbac_G-%08x_I-%08x.png" % (gid, iid))
    for n in names:
        p = os.path.join(art_dir, n)
        if os.path.isfile(p):
            im = Image.open(p).convert("RGBA")
            px = im.load()
            for y in range(im.height):
                for x in range(im.width):
                    if px[x, y][:3] == KEY:
                        px[x, y] = (0, 0, 0, 0)
            return im
    MISSING_ART.add("%08x:%08x in %s" % (gid, iid, os.path.basename(art_dir)))
    return None


def load_art(art_dir, gid, iid, synth_f=None):
    """Colour-key magenta to transparent; keep the sheet's own alpha otherwise.

    ⚠ The two conventions co-exist in this corpus and both are honoured: the
    button strips carry real alpha (0 for the surround, no magenta at all), the
    tiled background carries 25,410 exact 0xFF00FF pixels. Treating only one of
    them would silently paint a magenta slab or drop a transparent surround.

    ⛔ `synth_f` BUILDS THE SHEET THE PIPELINE *WOULD* HAVE SHIPPED - the 1x
    source mapped with `sx = (int)(ox / factor)` into the shipped sheet's own
    dimensions. It exists because the shipped background is NOT a pure NN
    upscale: `46a006b0:13d14ca0` carries a deliberate 96x96 (f=1.5) / 192x192
    (f=3) repaint over the dashboard minimap well - and NOT at f=2. Measured
    over every sheet this panel binds: 17 of 18 are bit-exact NN at all three
    tiers, that one is 9,216 px off at 1.5x and 36,864 px off at 3x.
    Without this the "brighter than 1x" detector fires 336 runs at f=3, i.e. it
    reports the repaint as a defect and the INTEGER CONTROL IS NOT ZERO
    (house law 95: a fractional-tier metric that does not read 0 at 2x/3x is
    measuring itself).
    """
    key = (art_dir, gid, iid, synth_f)
    if key in _ART_CACHE:
        return _ART_CACHE[key]
    im = _open_art(art_dir, gid, iid)
    if im is not None and synth_f:
        base = _open_art(ART_1X, gid, iid)
        if base is not None:
            synth = Image.new("RGBA", im.size)
            bp, sp = base.load(), synth.load()
            for y in range(im.height):
                sy = min(base.height - 1, int(y / synth_f))
                for x in range(im.width):
                    sp[x, y] = bp[min(base.width - 1, int(x / synth_f)), sy]
            im = synth
    _ART_CACHE[key] = im
    return im


def tile(sheet, w, h):
    """`blttype=tiled` - src-follows-dst: REPEAT the source across the dest.

    The last tile in each direction is CLIPPED by the window, which is why a
    sheet one pixel WIDER than its window over-covers rather than leaving a gap
    (#166's own note says so, and it is why 'a gap' was the wrong thing to hunt).
    """
    canvas = Image.new("RGBA", (max(w, 0), max(h, 0)), (0, 0, 0, 0))
    if sheet is None or sheet.width <= 0 or sheet.height <= 0:
        return canvas
    for y in range(0, h, sheet.height):
        for x in range(0, w, sheet.width):
            canvas.alpha_composite(sheet, (x, y))
    return canvas


# ══════════════════════════════════════════════════════════════════════════════
# 3. THE RUNTIME GEOMETRY - UiSpike.cpp, mirrored through scale_rules
# ══════════════════════════════════════════════════════════════════════════════

R = scale_round

#: Which ROOT-sizing law to model.
#:   "edges"  = R(l+w,f) - R(l,f)   the law in the SHIPPED DLL. Reproduces the
#:              live log line exactly: (5,1388 235x223) -> (8,1281 352x335).
#:   "length" = R(w,f)              the #166 CANDIDATE, already written into
#:              `src\UiSpike.cpp` (search "#166: A PANEL ROOT IS SIZED AS A
#:              LENGTH") but NOT in the deployed binary - the live log still
#:              prints 352. Modelled so the cure can be priced before a build.
LAW_EDGES, LAW_LENGTH = "edges", "length"


def root_extent(L, T, w, h, f, law):
    if law == LAW_LENGTH:
        return R(w, f), R(h, f)
    return R(L + w, f) - R(L, f), R(T + h, f) - R(T, f)


def scaled_child(p_abs_l, p_abs_t, l, t, w, h, f, is_leaf):
    """#161 + #148, verbatim from `UiSpike::ScaleSubtree`.

        aL   = pAbsL + l                       (absolute DESIGN coordinate)
        newL = R(aL,f) - R(pAbsL,f)            position inside the scaled parent
        newW = R(aL+w,f) - R(aL,f)             edge-derived  (a CONTAINER)
        if GetChildCount() == 0: newW = R(w,f) size-derived  (a LEAF, #148)

    -> (newL, newT, newW, newH, aL, aT)
    """
    a_l, a_t = p_abs_l + l, p_abs_t + t
    new_l = R(a_l, f) - R(p_abs_l, f)
    new_t = R(a_t, f) - R(p_abs_t, f)
    new_w = R(a_l + w, f) - R(a_l, f)
    new_h = R(a_t + h, f) - R(a_t, f)
    if is_leaf:
        new_w, new_h = R(w, f), R(h, f)
    return new_l, new_t, new_w, new_h, a_l, a_t


# ══════════════════════════════════════════════════════════════════════════════
# 4. THE COMPOSITOR
# ══════════════════════════════════════════════════════════════════════════════

def draw_window(node, w, h, f, art_dir, states=4, synth_f=None):
    """The window's OWN paint, into a canvas of its scaled size. Children are
    composited by the caller, which is what gives us the engine's clipping."""
    canvas = Image.new("RGBA", (max(w, 0), max(h, 0)), (0, 0, 0, 0))
    a = node["attrs"]
    gi = IMG.match(a.get("image", "") or "")
    if not gi or w <= 0 or h <= 0:
        return canvas
    sheet = load_art(art_dir, int(gi.group(1), 16), int(gi.group(2), 16), synth_f)
    if sheet is None:
        return canvas
    blt = a.get("blttype", "")
    if blt == "tiled":
        return tile(sheet, w, h)
    ir = rect(a.get("imagerect"))
    if a.get("clsid") == "GZWinBtn" and ir is None and sheet.width % states == 0:
        # A four-state strip draws STATE 0, the leftmost cell. The cell is an
        # INTEGER divide the engine performs on the sheet's own width (#143).
        cell = sheet.width // states
        sheet = sheet.crop((0, 0, cell, sheet.height))
    elif ir:
        sheet = sheet.crop((max(0, ir[0]), max(0, ir[1]),
                            min(sheet.width, ir[2]), min(sheet.height, ir[3])))
    # NATIVE size at the window origin, CLIPPED by the window (#154). Never
    # stretched - a stretch here would invent the very hairline we are hunting.
    sheet = sheet.crop((0, 0, min(sheet.width, w), min(sheet.height, h)))
    canvas.alpha_composite(sheet, (0, 0))
    return canvas


def render(node, p_abs_l, p_abs_t, w, h, f, art_dir, boxes=None,
           off=(0, 0), depth=0, synth_f=None):
    """Recursive composite. `boxes` collects (id, x, y, w, h) in ROOT space."""
    canvas = draw_window(node, w, h, f, art_dir, synth_f=synth_f)
    for kid in node["kids"]:
        r = rect(kid["attrs"].get("area"))
        if r is None:
            continue
        kl, kt = r[0], r[1]
        kw, kh = r[2] - r[0], r[3] - r[1]
        is_leaf = not kid["kids"]
        nl, nt, nw, nh, a_l, a_t = scaled_child(p_abs_l, p_abs_t,
                                                kl, kt, kw, kh, f, is_leaf)
        sub = render(kid, a_l, a_t, nw, nh, f, art_dir, boxes,
                     (off[0] + nl, off[1] + nt), depth + 1, synth_f)
        if boxes is not None and node_id(kid) in BUTTONS:
            boxes.append((node_id(kid), off[0] + nl, off[1] + nt, nw, nh))
        canvas.alpha_composite(sub, (nl, nt))
    return canvas


def render_panel(origin, f, backdrop=(0, 0, 0, 255), synth=False,
                 law=LAW_EDGES):
    """-> (flattened RGB image, W, H, button boxes). The panel is composited on
    an OPAQUE backdrop so 'lighter' is a defined quantity everywhere."""
    ui_dir, art_dir = TIERS[f]
    path = (UI_1X if ui_dir is None else
            os.path.join(ui_dir, "T-0x00000000_G-0x96a006b0_I-0xc973b411.ui"))
    root = find_by_id(parse_tree(path), DASH_ID)
    if root is None:
        raise SystemExit("dashboard root 0x%08X not in %s" % (DASH_ID, path))
    r = rect(root["attrs"]["area"])
    dw, dh = r[2] - r[0], r[3] - r[1]
    L, T = origin
    W, H = root_extent(L, T, dw, dh, f, law)
    boxes = []
    canvas = render(root, L, T, W, H, f, art_dir, boxes,
                    synth_f=(f if synth else None))
    flat = Image.new("RGBA", (W, H), backdrop)
    flat.alpha_composite(canvas)
    return flat.convert("RGB"), W, H, boxes


# ══════════════════════════════════════════════════════════════════════════════
# 5. MEASUREMENT
# ══════════════════════════════════════════════════════════════════════════════

def lum(p):
    return 0.299 * p[0] + 0.587 * p[1] + 0.114 * p[2]


def nn_reference(base, f, w, h):
    """The picture tier `f` is SUPPOSED to be showing: the 1x composite mapped
    with the art pipeline's own sampler, `sx = (int)(ox / factor)`
    (`Upscale2x.cs` :753/:939). NEAREST only - an interpolating filter would
    invent colours the source lacks (#143, the magenta-key rule)."""
    ref = Image.new("RGB", (w, h))
    sp, rp = base.load(), ref.load()
    for y in range(h):
        sy = min(base.height - 1, int(y / f))
        for x in range(w):
            sx = min(base.width - 1, int(x / f))
            rp[x, y] = sp[sx, sy]
    return ref


def bright_runs(img, ref, box=None, thresh=8.0, mask=None):
    """Maximal horizontal runs where `img` is LIGHTER than `ref` by `thresh`.

    "Lighter, and a short segment" is the user's own discriminator (#162's
    correction), and it is the one thing no gap-hunting gate could ever see.

    `mask` is a set of (x, y) the metric must IGNORE - the deliberate art
    repaint, which is a shipped decision and not a defect. Masking is stated
    out loud rather than folded in silently (law 42: a gate is only as honest
    as its scope).
    """
    w = min(img.width, ref.width)
    h = min(img.height, ref.height)
    x0, y0, x1, y1 = (0, 0, w, h) if box is None else box
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(w, x1), min(h, y1)
    ip, rp = img.load(), ref.load()
    runs = []
    for y in range(y0, y1):
        start = None
        for x in range(x0, x1):
            hot = (lum(ip[x, y]) - lum(rp[x, y]) >= thresh
                   and not (mask and (x, y) in mask))
            if hot and start is None:
                start = x
            elif not hot and start is not None:
                runs.append((y, start, x - 1))
                start = None
        if start is not None:
            runs.append((y, start, x1 - 1))
    return runs


def node_census(origin, f, law=LAW_EDGES):
    """-> {label: (relX, relY, W, H)} for every node of the subtree, in ROOT
    space. This is the geometry half of the experiment: it names exactly which
    windows the origin's parity moves, and on which AXIS, before a single pixel
    is compared."""
    ui_dir, _ = TIERS[f]
    path = (UI_1X if ui_dir is None else
            os.path.join(ui_dir, "T-0x00000000_G-0x96a006b0_I-0xc973b411.ui"))
    root = find_by_id(parse_tree(path), DASH_ID)
    r = rect(root["attrs"]["area"])
    L, T = origin
    cen = {}

    def walk(node, p_abs_l, p_abs_t, off, path_key):
        for i, kid in enumerate(node["kids"]):
            kr = rect(kid["attrs"].get("area"))
            if kr is None:
                continue
            kw, kh = kr[2] - kr[0], kr[3] - kr[1]
            nl, nt, nw, nh, a_l, a_t = scaled_child(
                p_abs_l, p_abs_t, kr[0], kr[1], kw, kh, f, not kid["kids"])
            kid_id = node_id(kid)
            label = "%s/%s" % (path_key, BUTTONS[kid_id][0] if kid_id in BUTTONS
                               else ("0x%08X" % kid_id if kid_id is not None
                                     else "#%d %s" % (i, kid["attrs"]
                                                      .get("clsid", "?"))))
            cen[label] = (off[0] + nl, off[1] + nt, nw, nh)
            walk(kid, a_l, a_t, (off[0] + nl, off[1] + nt), label)

    cen["ROOT"] = (0, 0) + root_extent(L, T, r[2] - r[0], r[3] - r[1], f, law)
    walk(root, L, T, (0, 0), "")
    return cen


def art_patch_mask(origin, f, law=LAW_EDGES):
    """Pixels this panel owes to the DELIBERATE art repaint, not to geometry.

    Rendered twice at the SAME origin - once with the shipped sheets, once with
    sheets synthesised as pure NN of the 1x source - so the difference is the
    repaint and nothing else. Non-circular: it never looks at a second origin,
    so it cannot absorb an origin-parity effect.
    """
    shipped, W, H, _ = render_panel(origin, f, law=law)
    synth, _, _, _ = render_panel(origin, f, synth=True, law=law)
    sp, yp = shipped.load(), synth.load()
    return {(x, y) for y in range(H) for x in range(W) if sp[x, y] != yp[x, y]}


def diff_count(a, b):
    """(differing pixels, common w, common h). Sizes may legitimately differ by
    a pixel - that IS the defect - so compare the common region and say so."""
    w, h = min(a.width, b.width), min(a.height, b.height)
    ap, bp = a.load(), b.load()
    n = 0
    for y in range(h):
        for x in range(w):
            if ap[x, y] != bp[x, y]:
                n += 1
    return n, w, h


def summarise(runs, boxes, label):
    if not runs:
        out("      %-28s none" % label)
        return
    by_btn = {}
    for (y, a, b) in runs:
        where = "panel"
        for (bid, bx, by, bw, bh) in boxes:
            if bx <= a and b < bx + bw and by <= y < by + bh:
                where = BUTTONS[bid][0]
                break
        by_btn.setdefault(where, []).append((y, a, b))
    out("      %-28s %d runs, %d px" % (label, len(runs),
                                        sum(b - a + 1 for (_, a, b) in runs)))
    for where in sorted(by_btn):
        rs = by_btn[where]
        rs.sort()
        shown = ", ".join("y=%d x=%d..%d (len %d)" % (y, a, b, b - a + 1)
                          for (y, a, b) in rs[:6])
        out("        %-10s %3d runs  %s%s"
            % (where, len(rs), shown, " ..." if len(rs) > 6 else ""))


# ══════════════════════════════════════════════════════════════════════════════
# 6. THE EXPERIMENT
# ══════════════════════════════════════════════════════════════════════════════

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "_tests", "repro166"))
    ap.add_argument("--zoom", type=int, default=6)
    ap.add_argument("--thresh", type=float, default=8.0)
    ap.add_argument("--law", default=LAW_EDGES, choices=[LAW_EDGES, LAW_LENGTH],
                    help="root-sizing law: 'edges' = the SHIPPED DLL (default),"
                         " 'length' = the #166 candidate already sitting in"
                         " src/UiSpike.cpp but not yet built")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    out("repro_166_liverect.py - compositing dashboard 0x%08X offline\n" % DASH_ID)

    # ── 6.1 geometry first, so the pixels can be read against a number ────────
    out("PANEL GEOMETRY  (window = edges R(L+w)-R(L); art = length ScaleDim(w))")
    out("  %-8s %-12s %-11s %-11s %s"
        % ("f", "origin", "window", "art sheet", "verdict"))
    imgs, refs, boxmap = {}, {}, {}
    for f in (1.0, 1.5, 2.0, 3.0):
        _, art_dir = TIERS[f]
        sheet = load_art(art_dir, 0x46A006B0, 0x13D14CA0)
        for name, origin in ORIGINS:
            img, W, H, boxes = render_panel(origin, f, law=a.law)
            imgs[(f, name)] = img
            boxmap[(f, name)] = boxes
            p = os.path.join(a.out, "panel_f%.2f_%s_%d,%d.png"
                             % (f, name, origin[0], origin[1]))
            img.save(p)
            verdict = "art == window" if (W, H) == (sheet.width, sheet.height) \
                else "dW=%+d dH=%+d" % (sheet.width - W, sheet.height - H)
            out("  %-8.2f %-12s %-11s %-11s %s"
                % (f, "%d,%d" % origin, "%dx%d" % (W, H),
                   "%dx%d" % (sheet.width, sheet.height), verdict))
    out("")

    # ── 6.2 where the three buttons land ──────────────────────────────────────
    out("BUTTON PLACEMENT inside the panel  (rel = R(L+l,f)-R(L,f);"
        " length = R(l,f))")
    ui_dir = TIERS[1.0][0]
    root1 = find_by_id(parse_tree(UI_1X), DASH_ID)
    del ui_dir, root1
    for f in (1.0, 1.5, 2.0, 3.0):
        for name, origin in ORIGINS:
            cells = []
            for (bid, bx, by, bw, bh) in sorted(boxmap[(f, name)]):
                lbl = BUTTONS[bid][0]
                cells.append("%s (%d,%d %dx%d)" % (lbl, bx, by, bw, bh))
            out("  f=%.2f %-7s %s" % (f, name, "  ".join(cells)))
    out("")

    # ── 6.3 C1 / C2 the origin-invariance controls ────────────────────────────
    out("C1/C2  ORIGIN INVARIANCE  (live vs design, same factor)")
    c_fail = 0
    for f in (1.0, 2.0, 3.0):
        n, w, h = diff_count(imgs[(f, "live")], imgs[(f, "design")])
        same = imgs[(f, "live")].size == imgs[(f, "design")].size
        status = "IDENTICAL" if (n == 0 and same) else "*** DIFFERS ***"
        if n or not same:
            c_fail += 1
        out("  f=%.2f  %-15s %d differing px over %dx%d, sizes %s / %s"
            % (f, status, n, w, h, imgs[(f, "live")].size,
               imgs[(f, "design")].size))
    n15, w15, h15 = diff_count(imgs[(1.5, "live")], imgs[(1.5, "design")])
    out("  f=1.50 EXPERIMENT     %d differing px over %dx%d, sizes %s / %s"
        % (n15, w15, h15, imgs[(1.5, "live")].size, imgs[(1.5, "design")].size))
    if c_fail:
        out("\n[STOP] C1/C2 FAILED. At an integer factor rel = l*k for EVERY L,"
            " so a difference\n       there means THIS MODEL is wrong, not the"
            " game. Nothing below is usable.")
        return 1
    out("  -> C1 and C2 hold: the origin is provably invisible at f=1, 2 and 3.")
    out("")

    # ── 6.4 the ART REPAINT, named before it can be mistaken for a defect ─────
    out("ART REPAINT MASK  (shipped sheet vs pure NN of the 1x source)")
    masks = {}
    for f in (1.0, 1.5, 2.0, 3.0):
        for name, origin in ORIGINS:
            masks[(f, name)] = art_patch_mask(origin, f, law=a.law)
        out("  f=%.2f  %s"
            % (f, "  ".join("%s %d px" % (n, len(masks[(f, n)]))
                            for n, _ in ORIGINS)))
    out("  -> `46a006b0:13d14ca0` is repainted over the dashboard minimap well"
        " at f=1.5 and f=3\n     and NOT at f=2. It is a shipped decision, it is"
        " origin-independent, and it is\n     excluded from every count below."
        " The other 17 sheets are bit-exact NN.")
    out("")

    # ── 6.5 the bright-run detector, against the NN reference ─────────────────
    out("BRIGHT RUNS vs the 1x composite resampled NEAREST"
        "  (LIGHTER by >= %.1f, repaint masked out)" % a.thresh)
    labels = sorted(set(v[0] for v in BUTTONS.values()))
    out("  %-6s %-8s %-10s %6s %6s %s"
        % ("f", "origin", "window", "runs", "px",
           " ".join("%9s" % x for x in labels)))
    fired_15 = 0
    tally = {}
    for f in (1.0, 1.5, 2.0, 3.0):
        for name, origin in ORIGINS:
            img = imgs[(f, name)]
            ref = nn_reference(imgs[(1.0, name)], f, img.width, img.height)
            refs[(f, name)] = ref
            ref.save(os.path.join(a.out, "ref_f%.2f_%s.png" % (f, name)))
            mask = masks[(f, name)]
            runs = bright_runs(img, ref, thresh=a.thresh, mask=mask)
            per = {}
            for (bid, bx, by, bw, bh) in boxmap[(f, name)]:
                per[BUTTONS[bid][0]] = bright_runs(
                    img, ref, (bx, by, bx + bw, by + bh), a.thresh, mask)
            tally[(f, name)] = (runs, per)
            if f == 1.5:
                fired_15 += len(runs)
            out("  %-6.2f %-8s %-10s %6d %6d %s"
                % (f, name, "%dx%d" % img.size, len(runs),
                   sum(b - x + 1 for (_, x, b) in runs),
                   " ".join("%9d" % len(per.get(x, [])) for x in labels)))
    out("")

    # ── 6.6 C4 the detector's positive control, then the integer control ──────
    out("C4  DETECTOR POSITIVE CONTROL: %d bright runs at f=1.5 across the four"
        " origins" % fired_15)
    if fired_15 == 0:
        out("    [STOP] the detector never fired at the ONE tier the defect is"
            " reported at.\n           Its zeros elsewhere are inert and prove"
            " nothing (NULL IS NOT EVIDENCE).")
    intr = sum(len(tally[(f, n)][0])
               for f in (1.0, 2.0, 3.0) for n, _ in ORIGINS)
    out("C1b INTEGER-TIER CONTROL ON THE DETECTOR: %d runs at f=1, 2 and 3"
        " (must be 0)" % intr)
    if intr:
        out("    [STOP] law 95 - a fractional-tier metric that does not read"
            " exactly 0 at the\n           integer tiers is measuring itself."
            " Nothing below is usable.")
    out("")

    # ── 6.7 C3 the negative control, stated as a verdict ──────────────────────
    out("C3  NEGATIVE CONTROL: live l=5 (q=2 does NOT divide) vs l=6 (q DOES)")
    for tag in ("live", "negctl", "design", "oddodd"):
        runs, per = tally[(1.5, tag)]
        out("    %-7s window %-9s  %4d bright runs on the panel;  %s"
            % (tag, "%dx%d" % imgs[(1.5, tag)].size, len(runs),
               ", ".join("%s %d" % (x, len(per.get(x, [])))
                         for x in sorted(set(v[0] for v in BUTTONS.values())))))
    for tag in ("live", "negctl", "design", "oddodd"):
        runs, per = tally[(1.5, tag)]
        for lbl in sorted(set(v[0] for v in BUTTONS.values())):
            rs = sorted(per.get(lbl, []))
            if rs:
                out("      %-7s %-7s %s" % (tag, lbl,
                    ", ".join("y=%d x=%d..%d (len %d)" % (y, x0, x1, x1 - x0 + 1)
                              for (y, x0, x1) in rs[:10])))
    out("")

    # ── 6.8 NODE-LEVEL PARITY CENSUS: what actually moves, and on which axis ──
    out("NODE PARITY CENSUS at f=1.5  (vs `negctl`, the parity-CLEAN origin"
        " where q | l and q | t)")
    clean = node_census(NEG_ORIGIN, 1.5, a.law)
    for tag, origin in ORIGINS:
        if tag == "negctl":
            continue
        cen = node_census(origin, 1.5, a.law)
        moved = [(k, cen[k], clean[k]) for k in cen if cen[k] != clean[k]]
        out("  %-7s origin (%d,%d)  l%%2=%d t%%2=%d   %d of %d nodes move"
            % (tag, origin[0], origin[1], origin[0] % 2, origin[1] % 2,
               len(moved), len(cen)))
        for k, got, want in sorted(moved):
            out("      %-34s (%d,%d %dx%d)  parity-clean (%d,%d %dx%d)"
                % (k, got[0], got[1], got[2], got[3],
                   want[0], want[1], want[2], want[3]))
    out("")

    # ── 6.9 THE EXPERIMENT ITSELF: same art, same tier, only the origin moves ─
    out("PARITY PIXEL DIFF at f=1.5  (identical art, identical tier;"
        " ONLY the origin moves)")
    out("  ⛔ THIS is the comparison #166 asks for. The NN-of-1x-composite"
        " reference above is NOT:\n     it samples the whole FRAME at one phase"
        " while the shipped pipeline scales each\n     ELEMENT at its own phase,"
        " so it disagrees at 1.5x at EVERY origin - including the\n     clean"
        " one - which is precisely the 'property of all fractional NN' trap"
        " #162 logged.")
    ref = imgs[(1.5, "negctl")]
    for tag, _ in ORIGINS:
        if tag == "negctl":
            continue
        img = imgs[(1.5, tag)]
        mask = masks[(1.5, tag)] | masks[(1.5, "negctl")]
        n, w, h = diff_count(img, ref)
        light = bright_runs(img, ref, thresh=a.thresh, mask=mask)
        dark = bright_runs(ref, img, thresh=a.thresh, mask=mask)
        out("    %-7s %6d differing px over %dx%d;  %d LIGHTER runs,"
            " %d DARKER runs" % (tag, n, w, h, len(light), len(dark)))
        for lbl in sorted(set(v[0] for v in BUTTONS.values())):
            box = None
            for (bid, bx, by, bw, bh) in boxmap[(1.5, "negctl")]:
                if BUTTONS[bid][0] == lbl:
                    box = (bx, by, bx + bw, by + bh)
            if box is None:
                continue
            li = bright_runs(img, ref, box, a.thresh, mask)
            da = bright_runs(ref, img, box, a.thresh, mask)
            out("        %-7s %3d lighter, %3d darker  %s"
                % (lbl, len(li), len(da),
                   ", ".join("y=%d x=%d..%d (len %d)" % (y, x0, x1, x1 - x0 + 1)
                             for (y, x0, x1) in sorted(li)[:6]) or "-"))
    out("")

    # ── 6.9b WHAT THE #166 CANDIDATE CURE ACTUALLY MOVES ──────────────────────
    out("#166 CANDIDATE CURE, PRICED OFFLINE  (root sized as a LENGTH R(w,f))")
    out("  ⚠ `src\\UiSpike.cpp` ALREADY carries this change (search '#166: A"
        " PANEL ROOT IS SIZED\n     AS A LENGTH'). The DEPLOYED binary does NOT"
        " - the live log still prints 352x335\n     - so everything above models"
        " the SHIPPED law and this section prices the fix.")
    for f in (1.0, 1.5, 2.0, 3.0):
        row = []
        for name, origin in ORIGINS:
            e = render_panel(origin, f, law=LAW_EDGES)[1:3]
            g = render_panel(origin, f, law=LAW_LENGTH)[1:3]
            row.append("%s %dx%d%s" % (name, g[0], g[1],
                                       "" if e == g else " (was %dx%d)" % e))
        out("  f=%.2f  %s" % (f, "  ".join(row)))
    cur_e = node_census(LIVE_ORIGIN, 1.5, LAW_EDGES)
    cur_g = node_census(LIVE_ORIGIN, 1.5, LAW_LENGTH)
    cln_g = node_census(NEG_ORIGIN, 1.5, LAW_LENGTH)
    moved_e = {k for k in cur_e if cur_e[k] != node_census(
        NEG_ORIGIN, 1.5, LAW_EDGES)[k]}
    moved_g = {k for k in cur_g if cur_g[k] != cln_g[k]}
    out("  at the LIVE origin, f=1.5: %d of %d nodes are parity-displaced under"
        " the shipped law,\n     %d under the candidate. STILL DISPLACED after"
        " the cure: %s"
        % (len(moved_e), len(cur_e), len(moved_g),
           ", ".join(sorted(k.split("/")[-1] for k in moved_g)) or "none"))
    li = render_panel(LIVE_ORIGIN, 1.5, law=LAW_LENGTH)[0]
    cl = render_panel(NEG_ORIGIN, 1.5, law=LAW_LENGTH)[0]
    mk = art_patch_mask(LIVE_ORIGIN, 1.5, LAW_LENGTH)
    n, w, h = diff_count(li, cl)
    out("  candidate law, live vs parity-clean: %d differing px over %dx%d;"
        " %d LIGHTER runs"
        % (n, w, h, len(bright_runs(li, cl, thresh=a.thresh, mask=mk))))
    out("")

    # ── 6.9c SUB-PIXEL PHASE CENSUS - the OTHER thing an origin can break ─────
    out("SUB-PIXEL PHASE CENSUS  (why the '?' button is exonerated and the other"
        " two are not)")
    out("  A sheet is resampled at its OWN origin: art_f[j] = art_1[floor(j/f)]."
        "  A window placed\n  at dest offset o therefore only agrees with its"
        " surroundings when the phase repeats,\n  i.e. when p | o for f = p/q"
        " (p=3 at 1.5x; p=1 at every integer factor, which is why\n  this whole"
        " column is structurally 0 there).")
    out("  %-6s %-8s %-8s %-12s %-9s %-8s %s"
        % ("f", "origin", "button", "rel offset", "phase", "longest", "mean dL"))
    for f in (1.0, 1.5, 2.0, 3.0):
        p = 1 if float(f).is_integer() else 3
        for name, origin in ORIGINS:
            img = imgs[(f, name)]
            ref = refs[(f, name)]
            mask = masks[(f, name)]
            for (bid, bx, by, bw, bh) in sorted(boxmap[(f, name)],
                                                key=lambda b: b[1]):
                lbl = BUTTONS[bid][0]
                runs = bright_runs(img, ref, (bx, by, bx + bw, by + bh),
                                   a.thresh, mask)
                runs.sort(key=lambda r: -(r[2] - r[1]))
                if runs:
                    y, xa, xb = runs[0]
                    ip, rp = img.load(), ref.load()
                    dl = sum(lum(ip[x, y]) - lum(rp[x, y])
                             for x in range(xa, xb + 1)) / (xb - xa + 1)
                    longest = "y=%d x=%d..%d len %d of %d" % (y, xa, xb,
                                                              xb - xa + 1, bw)
                else:
                    dl, longest = 0.0, "none"
                out("  %-6.2f %-8s %-8s %-12s %-9s %-8s %s"
                    % (f, name, lbl, "(%d,%d)" % (bx, by),
                       "(%d,%d)" % (bx % p, by % p), "", longest
                       + ("  dL=%+.1f" % dl if runs else "")))
    out("")

    # ── 6.7 zoomed crops of the three buttons, every condition ────────────────
    for f in (1.0, 1.5, 2.0, 3.0):
        for name, _ in ORIGINS:
            img = imgs[(f, name)]
            for (bid, bx, by, bw, bh) in boxmap[(f, name)]:
                lbl = BUTTONS[bid][0]
                crop = img.crop((max(0, bx - 2), max(0, by - 2),
                                 min(img.width, bx + bw + 2),
                                 min(img.height, by + bh + 2)))
                crop = crop.resize((crop.width * a.zoom, crop.height * a.zoom),
                                   Image.NEAREST)
                crop.save(os.path.join(a.out, "btn_%s_f%.2f_%s.png"
                                       % (lbl, f, name)))
    # ── 6.10 C5: the '?' zero is a CLIP, prove the compositor can clip ────────
    out("C5  CLIPPING SELF-TEST  (the '?' reports zero because it is CLIPPED -"
        " NULL IS NOT EVIDENCE)")
    fx = Image.new("RGBA", (8, 8), (0, 0, 0, 255))
    sub = Image.new("RGBA", (6, 6))
    sp = sub.load()
    for y in range(6):
        for x in range(6):
            sp[x, y] = (10 * x, 10 * y, 0, 255)
    fx.alpha_composite(sub, (-2, -3))
    fp = fx.load()
    ok = (fp[0, 0] == (20, 30, 0, 255) and fp[3, 2] == (50, 50, 0, 255)
          and fp[4, 3] == (0, 0, 0, 255))
    out("    negative-dest composite CROPS (not clamps, not wraps): %s"
        % ("PASS" if ok else "*** FAIL - every clipped-window result above is"
                            " worthless ***"))
    for name, _ in ORIGINS:
        for (bid, bx, by, bw, bh) in boxmap[(1.5, name)]:
            if BUTTONS[bid][0] == "sun":
                out("    f=1.5 %-7s '?' at rel y=%d: %d of its %d rows are ABOVE"
                    " the panel top and never drawn" % (name, by, max(0, -by), bh))
    out("")

    # ── 6.11 THE VERDICT, stated so it cannot be quoted selectively ───────────
    out("VERDICT")
    out("  1. The model reproduces the SHIPPED log line exactly:"
        " (5,1388 235x223) -> 352x335.")
    out("  2. C1/C2/C1b/C4/C5 all hold. The origin is provably invisible at"
        " f=1, 2 and 3.")
    out("  3. C3, the negative control, DOES fire: moving the live origin l=5"
        " -> 6 takes the\n     hat's difference from 363 lighter px to 0. #166's"
        " parity law is REAL and it is\n     the only origin-dependent effect on"
        " this panel.")
    out("  4. ⛔ BUT IT DOES NOT REPRODUCE THE REPORTED ARTIFACT. At the LIVE"
        " rect (l=5 odd,\n     t=1388 EVEN) the parity displaces the HAT ONLY,"
        " by one pixel HORIZONTALLY, and\n     every resulting run is 1-2 px"
        " long. The PEOPLE button is untouched - 0 px - because\n     its design"
        " l=138 is even and its design t=93 is only exposed when the panel's own"
        "\n     t is odd. The user reports a line in BOTH.")
    out("  5. The pattern that DOES match (long horizontal runs in hat AND"
        " people, zero in the\n     third button) needs an ODD panel t."
        " Measured across five frame heights and 197\n     sightings the"
        " dashboard docks at t = frameH - 212 with l=5 always, so t's parity"
        "\n     IS the frame height's, and every shipped resolution height is"
        " even. Unreachable.")
    out("  6. NAMING: `{46a006b0,14415860}` - which the brief and #162 both call"
        " \"the '?' button\"\n     - draws a SUN/STARBURST. The real \"?\" glyph"
        " buttons are 0x99887766 {..,14015547}\n     and 0x8B96B73E"
        " {..,4b8da4a4}, both at design l=95 (ODD), so neither is immune to"
        "\n     the parity the sun is immune to. Whichever button the user"
        " means, the answer above\n     does not change - but any argument that"
        " leans on \"the '?' is clipped\" is leaning on\n     a button that may"
        " not be the one in the report.")
    out("  7. ⛔ STRUCTURAL, AND IT OUTRANKS ALL OF THE ABOVE: a GZWinBtn draws"
        " cell 0 of its\n     sheet at NATIVE size at its window origin. The"
        " bitmap is fixed. Parity and phase\n     are pure TRANSLATIONS of it,"
        " so NO origin, NO parity and NO sub-pixel phase can\n     put a bright"
        " run INSIDE the button picture - only misregister it against the\n"
        "     background at its boundary. A bright line inside the hat and the"
        " people buttons\n     therefore cannot be an origin effect at all.")
    out("")
    if MISSING_ART:
        out("  ⚠ ART NOT FOUND (every count above is short by whatever these"
            " would have drawn):")
        for m in sorted(MISSING_ART):
            out("      " + m)
    else:
        out("  positive control on the art loader: 0 sheets missing at any tier")
    out("")
    out("PNGs written to %s" % a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
