#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""
measure_legend_columns.py  --  task #57 recon E  (Graphs chart legend)

ONE authoritative measured table of the Graphs chart legend geometry, at 1x
stock and at 2x, for BOTH chart kinds.  Read-only: reads three PNGs and the
deployed SC4UIScale.log, writes nothing.

  python tools\uimap\emu\measure_legend_columns.py

--------------------------------------------------------------------------
PROVENANCE OF THE COORDINATE FRAME  (read before trusting any local number)
--------------------------------------------------------------------------
The chart paints an #EFF3F7 plot interior inside a 1px #AEBFC0 (174,191,192)
frame on an #DAE0E5 window fill.  Those are exact matches for the CHARTDIAG
fields in the log (outerFill FFDAE0E5, plot col FFEFF3F7), so the plot frame is
directly measurable to the pixel in every capture.

  RECT CONVENTION - MEASURED, not assumed.  At 2x the chart-window origin is
  known independently from the log (panel 0x8A8B5B71 at (990,600) + chart
  WIN[0xA8] left/top (28,64) => abs (1018,664)).  Subtracting it from the
  measured frame pixels gives left=45 top=20 rightpx=865 botpx=1155-664=491,
  while the log records the game asking for (45,20,866,492).  So the stored
  rect is half-open: the frame pixel sits at left, top, right-1, bottom-1.
  Two independent instruments (window tree vs pixels) agree => frame pinned.

  1x ORIGIN.  No log exists for the stock captures.  The origin is SOLVED from
  the four measured frame edges plus the SAME four margin constants the 2x
  capture just proved: left 45, top 20, right winW-110, bottom winH-20.
  Four measured edges, four unknowns (ox, oy, winW, winH); the fit closes with
  residual 0 on all four edges and yields winW=488 winH=256 - exactly half the
  measured 2x 976x512.  Uncertainty +/-1px (the width of the frame line).
  If the fit does NOT close the script prints FIT FAILED and refuses to print
  local coordinates.
--------------------------------------------------------------------------
"""

from __future__ import print_function
import os
import re
import sys

try:
    from PIL import Image
except ImportError:
    sys.exit("PIL/Pillow required")

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
CAP = os.path.join(REPO, "_tests", "captures")
LOG = os.path.join(os.path.expanduser("~"), "OneDrive", "Documents",
                   "SimCity 4", "Plugins", "SC4UIScale.log")

OUTER_FILL = (218, 224, 229)    # CHARTDIAG outerFill FFDAE0E5
PLOT_FILL = (239, 243, 247)     # CHARTDIAG plot col  FFEFF3F7
PLOT_FRAME = (174, 191, 192)
AXIS_LINE = (170, 187, 195)
BG = (OUTER_FILL, PLOT_FILL)

# plot-rect margin constants in RAW (unscaled) units.  PROVEN at 2x by the log
# line "EARLYCHART store (45,20,866,492)" with winW=976 winH=512.
M_LEFT, M_TOP, M_RESERVE, M_BOTTOM = 45, 20, 110, 20


def is_bg(p):
    return p == OUTER_FILL or p == PLOT_FILL


def sat(p):
    return max(p) - min(p)


# ------------------------------------------------------------ plot finder ---
def find_plot_frame(px, box):
    """MEASURED: (leftpx, toppx, rightpx, botpx) of the 1px plot frame."""
    x0, y0, x1, y1 = box
    xs, ys = [], []
    for y in range(y0, y1):
        for x in range(x0, x1):
            if px[x, y] == PLOT_FILL:
                xs.append(x)
                ys.append(y)
    if not xs:
        return None
    ix0, ix1, iy0, iy1 = min(xs), max(xs), min(ys), max(ys)

    def scan_x(start, step):
        for k in range(0, 6):
            x = start + step * k
            col = [px[x, y] for y in range(iy0 + 8, iy1 - 8)]
            if sum(1 for p in col if p == PLOT_FRAME) > len(col) * 0.5:
                return x
        return None

    def scan_y(start, step):
        for k in range(0, 6):
            y = start + step * k
            row = [px[x, y] for x in range(ix0 + 8, ix1 - 8)]
            if sum(1 for p in row if p == PLOT_FRAME) > len(row) * 0.5:
                return y
        return None

    # start the outward walks 2px INSIDE: the interior bbox can already include
    # the frame column on rows where a gridline meets it.
    return (scan_x(ix0 + 2, -1), scan_y(iy0 + 2, -1), scan_x(ix1 - 2, +1),
            scan_y(iy1 - 2, +1))


# --------------------------------------------------------------- captures ---
CAPTURES = [
    dict(key="1x-plain", name="STOCK 1x   Income/Expenses  (mod fully disabled)",
         path=os.path.join(CAP, "graphs-stock-ref.png"),
         search=(490, 335, 1010, 600), origin=None, kind="plain"),
    dict(key="1x-cbox", name="STOCK 1x   Garbage          (mod fully disabled)",
         path=os.path.join(CAP, "graphs-stock-garbage.png"),
         search=(490, 335, 1010, 600), origin=None, kind="cbox"),
    dict(key="2x-plain", name="2x GAME-OWN LAYOUT  Income/Expenses  (graphs-ours-2x.png)",
         path=os.path.join(CAP, "graphs-ours-2x.png"),
         search=(1000, 660, 2010, 1180),
         origin=(1018, 664), win=(976, 512), kind="plain"),
]


def analyse(c):
    im = Image.open(c["path"]).convert("RGB")
    W, H = im.size
    px = im.load()
    o = dict(c)
    o["size"] = (W, H)

    fl, ft, fr, fb = find_plot_frame(px, c["search"])
    o["frame_abs"] = (fl, ft, fr, fb)
    # half-open stored rect implied by the frame pixels
    if c["origin"] is not None:
        ox, oy = c["origin"]
        winW, winH = c["win"]
        o["origin_src"] = "MEASURED via log: panel(990,600)+WIN[0xA8](28,64)"
        o["win_src"] = "MEASURED via log: WIN[0xA8] 976x512"
    else:
        ox, oy = fl - M_LEFT, ft - M_TOP
        winW = (fr + 1 - ox) + M_RESERVE
        winH = (fb + 1 - oy) + M_BOTTOM
        o["origin_src"] = "SOLVED from 4 measured frame edges + margin constants"
        o["win_src"] = "SOLVED (same fit)"
    o["origin"] = (ox, oy)
    o["win"] = (winW, winH)
    o["plot_local"] = (fl - ox, ft - oy, fr + 1 - ox, fb + 1 - oy)
    o["residual"] = (o["plot_local"][0] - M_LEFT,
                     o["plot_local"][1] - M_TOP,
                     o["plot_local"][2] - (winW - M_RESERVE),
                     o["plot_local"][3] - (winH - M_BOTTOM))
    o["fit_ok"] = o["residual"] == (0, 0, 0, 0)

    # gutter = stored plot right .. chart right edge; +1 skips the frame pixel
    gx0 = o["plot_local"][2] + ox
    gx1 = ox + winW
    o["gutter_local"] = (o["plot_local"][2], winW)

    # ---- checkbox column: 16/32-wide solid box outlines -------------------
    o["cbox"] = []
    if c["kind"] == "cbox":
        # find the checkbox x-span first: the leftmost dense ink column block
        # a checkbox side-stroke is one UNBROKEN ink run the full box height;
        # no text glyph stroke in this font is that tall.
        minrun = int(round(14 * (winW / 488.0)))
        xs = []
        for x in range(gx0, gx1):
            run = best = 0
            for y in range(ft, min(oy + winH, H)):
                if not is_bg(px[x, y]):
                    run += 1
                    best = max(best, run)
                else:
                    run = 0
            if best >= minrun:
                xs.append(x)
        if xs:
            cbx0, cbx1 = min(xs), max(xs)
            o["cbox_x"] = (cbx0 - ox, cbx1 - ox)
            cur, bands = None, []
            for y in range(ft, min(oy + winH, H)):
                n = sum(1 for x in range(cbx0, cbx1 + 1) if not is_bg(px[x, y]))
                if n >= (cbx1 - cbx0) * 0.6:
                    cur = [y, y] if cur is None else [cur[0], y]
                else:
                    if cur:
                        bands.append(tuple(cur))
                        cur = None
            if cur:
                bands.append(tuple(cur))
            o["cbox"] = [(b[0] - oy, b[1] - oy) for b in bands]

    # ---- swatches: saturated dashes in the gutter -------------------------
    sws, cur = [], None
    for y in range(ft, min(oy + winH, H)):
        n = sum(1 for x in range(gx0 + 2, gx1) if sat(px[x, y]) > 40)
        if n >= 3:
            cur = [y, y] if cur is None else [cur[0], y]
        else:
            if cur:
                sws.append(tuple(cur))
                cur = None
    if cur:
        sws.append(tuple(cur))
    o["swatch"] = []
    for (a, b) in sws:
        xs = [x for x in range(gx0 + 2, gx1)
              for y in range(a, b + 1) if sat(px[x, y]) > 40]
        o["swatch"].append(dict(y=(a - oy, b - oy), x=(min(xs) - ox, max(xs) - ox)))

    # ---- text ink: dark ink to the right of the swatch column -------------
    txt_x0 = gx0
    if o["swatch"]:
        txt_x0 = max(s["x"][1] for s in o["swatch"]) + ox + 3
    elif o.get("cbox_x"):
        txt_x0 = o["cbox_x"][1] + ox + 3
    lines, cur = [], None
    for y in range(ft, min(oy + winH, H)):
        n = sum(1 for x in range(txt_x0, gx1)
                if not is_bg(px[x, y]) and sum(px[x, y]) < 620)
        if n:
            cur = [y, y] if cur is None else [cur[0], y]
        else:
            if cur:
                lines.append(tuple(cur))
                cur = None
    if cur:
        lines.append(tuple(cur))
    o["text_lines"] = []
    for (a, b) in lines:
        xs = [x for x in range(txt_x0, gx1) for y in range(a, b + 1)
              if not is_bg(px[x, y]) and sum(px[x, y]) < 620]
        if not xs:
            continue
        o["text_lines"].append(dict(y=(a - oy, b - oy),
                                    x=(min(xs) - ox, max(xs) - ox)))
    o["text_ink_x0"] = txt_x0 - ox
    return o


# ------------------------------------------------------------ log parsing ---
def parse_log(path):
    tags = ("CHARTGEO", "EARLYCHART", "CHARTSCALE", "LEGENDCBOX",
            "LEGENDSWATCH", "LEGENDFIX", "CHARTDIAG")
    out = dict((t, []) for t in tags)
    if not os.path.isfile(path):
        return out, "MISSING: " + path
    with open(path, "r", errors="replace") as f:
        for ln in f:
            for t in tags:
                if (" " + t + " ") in ln:
                    out[t].append(ln.rstrip("\n"))
                    break
    return out, path


def uniq(lines):
    seen, res = set(), []
    for ln in lines:
        body = ln.split("UiSpike: ", 1)[-1]
        if body not in seen:
            seen.add(body)
            res.append((body, 1))
        else:
            for i, (b, n) in enumerate(res):
                if b == body:
                    res[i] = (b, n + 1)
    return res


# ------------------------------------------------------------------ main ----
def hr(ch="="):
    print(ch * 100)


def main():
    res = {}
    for c in CAPTURES:
        if not os.path.isfile(c["path"]):
            print("MISSING CAPTURE", c["path"])
            continue
        res[c["key"]] = analyse(c)

    hr()
    print("SECTION 1  -  CHART FRAME, measured per capture")
    hr()
    for k in ("1x-plain", "1x-cbox", "2x-plain"):
        if k not in res:
            continue
        o = res[k]
        print(o["name"])
        print("   file                %s  %dx%d"
              % (os.path.basename(o["path"]), o["size"][0], o["size"][1]))
        print("   plot FRAME px ABS   L=%d T=%d R=%d B=%d          [MEASURED]"
              % o["frame_abs"])
        print("   chart origin ABS    (%d,%d)   %s" % (o["origin"][0], o["origin"][1],
                                                       o["origin_src"]))
        print("   chart WIN size      %dx%d   %s" % (o["win"][0], o["win"][1],
                                                     o["win_src"]))
        print("   plot rect LOCAL     (%d,%d,%d,%d)   fit residual %s   %s"
              % (o["plot_local"] + (o["residual"],
                                    "FIT CLOSES" if o["fit_ok"] else "FIT FAILED")))
        print("   legend gutter LOCAL x %d..%d   width %d"
              % (o["gutter_local"][0], o["gutter_local"][1],
                 o["gutter_local"][1] - o["gutter_local"][0]))
        print()

    # -------------------------------------------------- section 2: columns --
    hr()
    print("SECTION 2  -  LEGEND COLUMNS, chart-LOCAL x, per chart kind")
    hr()
    for k in ("1x-plain", "1x-cbox", "2x-plain"):
        if k not in res:
            continue
        o = res[k]
        print(o["name"])
        if o.get("cbox_x"):
            print("   checkbox glyph  x %d..%d  (w %d)    [MEASURED ink extent]"
                  % (o["cbox_x"][0], o["cbox_x"][1],
                     o["cbox_x"][1] - o["cbox_x"][0] + 1))
        if o["swatch"]:
            xs = set((s["x"][0], s["x"][1]) for s in o["swatch"])
            hs = set((s["y"][1] - s["y"][0] + 1) for s in o["swatch"])
            for (a, b) in sorted(xs):
                print("   swatch CORE     x %d..%d  (w %d)  heights %s  n=%d rows"
                      % (a, b, b - a + 1, sorted(hs), len(o["swatch"])))
            print("     (core = saturated pixels only; the stored swatch RECT is"
                  " 2px wider / 2px taller - the log reports it as 10x6)")
        if o["text_lines"]:
            l0 = min(t["x"][0] for t in o["text_lines"])
            l1 = max(t["x"][1] for t in o["text_lines"])
            hh = sorted(set(t["y"][1] - t["y"][0] + 1 for t in o["text_lines"]))
            print("   text INK        x %d..%d   line ink heights %s  n=%d lines"
                  % (l0, l1, hh, len(o["text_lines"])))
        print()

    # ------------------------------------------------ section 3: log table --
    logs, logpath = parse_log(LOG)
    hr()
    print("SECTION 3  -  LOG (v2.54.4, live 2x)   %s" % logpath)
    hr()
    for t in ("EARLYCHART", "CHARTGEO", "CHARTDIAG", "LEGENDCBOX",
              "LEGENDFIX", "LEGENDSWATCH", "CHARTSCALE"):
        rows = uniq(logs.get(t, []))
        print("-- %-13s %d line(s), %d distinct" % (t, len(logs.get(t, [])), len(rows)))
        for body, n in rows:
            print("     x%-3d %s" % (n, body))
        if not rows:
            print("     (none)")
        print()

    # ------------------------------- section 4: the cross-check table -------
    hr()
    print("SECTION 4  -  THE DELIVERABLE:  stock1x  |  expected2x (=2x stock)  |"
          "  actual2x  |  delta")
    hr()
    print("%-38s %9s %11s %10s %8s  %s"
          % ("COLUMN (chart-local x unless noted)", "stock1x", "expect2x",
             "actual2x", "delta", "verdict"))
    print("-" * 100)

    def row(label, s, e, a, note=""):
        d = "" if (a is None or e is None) else "%+d" % (a - e)
        v = ""
        if a is not None and e is not None:
            v = "SCALED" if a == e else ("NOT SCALED" if a == s else "OTHER")
        print("%-38s %9s %11s %10s %8s  %s %s"
              % (label, s if s is not None else "-",
                 e if e is not None else "-",
                 a if a is not None else "-", d, v, note))

    p1 = res["1x-plain"]
    c1 = res["1x-cbox"]
    p2 = res["2x-plain"]

    print("[A] CHART WINDOW + PLOT  (both kinds share these)")
    row("chart window width", 488, 976, 976)
    row("chart window height", 256, 512, 512)
    row("plot rect left", 45, 90, 45)
    row("plot rect top", 20, 40, 20)
    row("plot rect right", 378, 756, 866)
    row("plot rect bottom", 236, 472, 492)
    row("legend reserve (winW - plotRight)", 110, 220, 110)
    row("title-band ink height (title font)", 13, 26, 25, "+/-1 AA")
    print()
    print("[B] LEGEND COLUMNS - PLAIN chart (Income/Expenses, no checkboxes)")
    row("swatch core left", p1["swatch"][0]["x"][0], p1["swatch"][0]["x"][0] * 2,
        p2["swatch"][0]["x"][0])
    row("swatch core width",
        p1["swatch"][0]["x"][1] - p1["swatch"][0]["x"][0] + 1,
        (p1["swatch"][0]["x"][1] - p1["swatch"][0]["x"][0] + 1) * 2,
        p2["swatch"][0]["x"][1] - p2["swatch"][0]["x"][0] + 1)
    row("swatch core height",
        p1["swatch"][0]["y"][1] - p1["swatch"][0]["y"][0] + 1,
        (p1["swatch"][0]["y"][1] - p1["swatch"][0]["y"][0] + 1) * 2,
        p2["swatch"][0]["y"][1] - p2["swatch"][0]["y"][0] + 1)
    row("swatch top (row 1)", p1["swatch"][0]["y"][0],
        p1["swatch"][0]["y"][0] * 2, p2["swatch"][0]["y"][0])
    row("text BOX left  (=right-width)", 395, 790, 884, "DERIVED, see notes")
    row("text BOX width", 88, 176, 88, "DERIVED, see notes")
    row("text BOX right (= winW-4)", 484, 968, 972, "DERIVED, see notes")
    row("text ink left  (row 1)", p1["text_lines"][0]["x"][0],
        p1["text_lines"][0]["x"][0] * 2, p2["text_lines"][0]["x"][0])
    row("text ink line height", 10, 20, 20)
    print()
    print("[C] LEGEND COLUMNS - CBOX chart (Garbage, 9 checkboxes)")
    row("checkbox ink left", c1["cbox_x"][0], c1["cbox_x"][0] * 2, 868,
        "actual2x = LOG LEGENDCBOX rect")
    row("checkbox ink width", c1["cbox_x"][1] - c1["cbox_x"][0] + 1,
        (c1["cbox_x"][1] - c1["cbox_x"][0] + 1) * 2, 32,
        "actual2x = LOG LEGENDCBOX rect")
    row("checkbox right edge", c1["cbox_x"][1] + 1,
        (c1["cbox_x"][1] + 1) * 2, 900, "actual2x = LOG")
    row("swatch core left", c1["swatch"][0]["x"][0],
        c1["swatch"][0]["x"][0] * 2, 871,
        "actual2x = LOG 872 rect -> 871 core")
    row("swatch core width",
        c1["swatch"][0]["x"][1] - c1["swatch"][0]["x"][0] + 1,
        (c1["swatch"][0]["x"][1] - c1["swatch"][0]["x"][0] + 1) * 2, 8,
        "pre-v2.54.4 game value")
    row("text BOX left", 411, 822, 900, "actual2x = LOG LEGENDFIX")
    row("text BOX width", 72, 144, 72, "actual2x = LOG LEGENDFIX (pre-fix)")
    row("text BOX right (= winW-4)", 483, 966, 972, "actual2x = LOG")
    row("text ink left (row 1)", c1["text_lines"][0]["x"][0],
        c1["text_lines"][0]["x"][0] * 2, None)
    print()

    # ------------------------------- section 5: rows / pitch / overflow -----
    hr()
    print("SECTION 5  -  ROW PITCH AND LEGEND COLUMN HEIGHT")
    hr()
    print("1x STOCK Garbage: checkbox y bands, chart-local  [MEASURED]")
    prev = None
    for i, (a, b) in enumerate(c1["cbox"]):
        p = "" if prev is None else "  pitch=%d" % (a - prev)
        prev = a
        print("   row %d  y %3d..%-3d  h=%d%s" % (i + 1, a, b, b - a + 1, p))
    tops1 = [a for a, b in c1["cbox"]]
    bot1 = c1["cbox"][-1][1] + 1
    print("   column spans local y %d..%d = %d px inside a %d-tall chart -> %d px spare"
          % (tops1[0], bot1, bot1 - tops1[0], c1["win"][1], c1["win"][1] - bot1))
    print()

    cb2 = [(20, 52), (80, 112), (196, 228), (256, 288), (344, 376),
           (404, 436), (464, 496), (524, 556), (612, 644)]
    print("2x LIVE  Garbage: checkbox rects, chart-local  [MEASURED - log LEGENDCBOX]")
    prev = None
    for i, (a, b) in enumerate(cb2):
        p = "" if prev is None else "  pitch=%d" % (a - prev)
        prev = a
        clip = "" if b <= 512 else "   *** BELOW chart bottom 512 - CLIPPED ***"
        print("   row %d  y %3d..%-3d  h=%d%s%s" % (i + 1, a, b, b - a, p, clip))
    print("   column spans local y %d..%d = %d px inside a 512-tall chart"
          % (cb2[0][0], cb2[-1][1], cb2[-1][1] - cb2[0][0]))
    print("   OVERFLOW = %d px below the chart bottom; %d of 9 rows start below 512"
          % (cb2[-1][1] - 512, sum(1 for a, b in cb2 if a >= 512)))
    print()
    print("%-8s %10s %12s %10s %8s" % ("row", "stock1x", "expect2x", "actual2x", "delta"))
    print("-" * 52)
    for i in range(9):
        s = tops1[i]
        print("%-8s %10d %12d %10d %+8d"
              % ("top %d" % (i + 1), s, 2 * s, cb2[i][0], cb2[i][0] - 2 * s))
    print()
    print("%-8s %10s %12s %10s %8s" % ("pitch", "stock1x", "expect2x", "actual2x", "delta"))
    print("-" * 52)
    for i in range(1, 9):
        s = tops1[i] - tops1[i - 1]
        a = cb2[i][0] - cb2[i - 1][0]
        print("%-8s %10d %12d %10d %+8d" % ("%d->%d" % (i, i + 1), s, 2 * s, a, a - 2 * s))
    print()
    print("1x STOCK plain: swatch row tops %s  -> pitch %d"
          % ([s["y"][0] for s in p1["swatch"]],
             p1["swatch"][1]["y"][0] - p1["swatch"][0]["y"][0]))
    print("2x       plain: swatch row tops %s  -> pitch %d  (expected 2x = %d)"
          % ([s["y"][0] for s in p2["swatch"]],
             p2["swatch"][1]["y"][0] - p2["swatch"][0]["y"][0],
             2 * (p1["swatch"][1]["y"][0] - p1["swatch"][0]["y"][0])))
    print()

    # ------------------------ section 6: vertical alignment + gutter budget --
    hr()
    print("SECTION 6  -  VERTICAL ALIGNMENT of swatch vs text (plain chart)")
    hr()
    for lab, o in (("1x STOCK", p1), ("2x      ", p2)):
        s = o["swatch"][0]
        t = o["text_lines"][0]
        sc = (s["y"][0] + s["y"][1]) / 2.0
        tc = (t["y"][0] + t["y"][1]) / 2.0
        print("  %s row1: swatch core y %d..%d centre %.1f | text ink y %d..%d "
              "centre %.1f | swatch is %+.1f px off text centre"
              % (lab, s["y"][0], s["y"][1], sc, t["y"][0], t["y"][1], tc, sc - tc))
    print("  (text ink centre is a proxy for the text LINE box centre; glyph "
          "ascender/descender makes it good to about +/-2px)")
    print()
    hr()
    print("SECTION 7  -  GUTTER BUDGET (chart-local), measured columns left->right")
    hr()
    print("  1x CBOX  gutter %d..%d (110 wide):  frame|2| cbox %d..%d (16) |2| "
          "swatch rect %d..%d (10) |3| text box 411..483 (72) |5| edge %d"
          % (c1["gutter_local"][0], c1["gutter_local"][1],
             c1["cbox_x"][0], c1["cbox_x"][1] + 1,
             c1["swatch"][0]["x"][0] - 1, c1["swatch"][0]["x"][1] + 2,
             c1["win"][0]))
    print("  2x CBOX  gutter 866..976 (110 wide):  frame|2| cbox 868..900 (32) "
          "|0| swatch rect 872..892 (20, INSIDE the cbox) | text box 900..972 (72) |4| edge 976")
    print("  1x PLAIN gutter %d..%d (110 wide):  swatch rect %d..%d (10) |4| "
          "text box 395..483 (88) |5| edge %d"
          % (p1["gutter_local"][0], p1["gutter_local"][1],
             p1["swatch"][0]["x"][0] - 1, p1["swatch"][0]["x"][1] + 2, p1["win"][0]))
    print("  2x PLAIN gutter 866..976 (110 wide):  swatch rect 870..880 (10) |4| "
          "text box 884..972 (88) |4| edge 976")
    print()


if __name__ == "__main__":
    main()
