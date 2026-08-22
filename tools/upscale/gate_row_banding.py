r"""#162 - does the 1.5x upscale THICKEN a thin bright ridge non-uniformly?

⛔ WHY THIS EXISTS, and what it is arguing with. `Upscale2x.cs:76` retired the
upscaler as a suspect for "white streaks at 1.5x" with this argument:

    nearest-neighbour only ever COPIES source pixels. It cannot introduce a
    colour that is not already in the source. So a WHITE line that is not in
    the 1x art can never be an NN resampling artifact.

That is **true about colour and silent about thickness**. NN at f=1.5 duplicates
every other source row. A 1px-thick bright ridge therefore becomes 2px thick on
the duplicated rows and stays 1px elsewhere. On a CURVED highlight - the bevel
of a round button - the near-horizontal part of that curve is where duplication
lands several columns in a row, and a locally-doubled ridge reads on screen as
exactly what the user reported: a SHORT BRIGHT HORIZONTAL SEGMENT.

At an integer factor every row duplicates the same number of times, so the ridge
is uniformly f px thick and no segment can stand out. That is why 2x and 3x are
clean, and it is the control this gate is built around.

WHAT IS MEASURED, per sheet, per tier:

  ridge(x)  = the vertical thickness, in rows, of the local luminance maximum
              in column x (a pixel is on the ridge if it is brighter than the
              pixels 2 rows above and 2 rows below by more than --thresh)
  ratio(x)  = ridge_tier(x) / ridge_1x(x // f)

  UNIFORM   = every column shares one ratio  -> the upscale is faithful
  RAGGED    = ratio varies column to column  -> some columns got a thicker
              ridge than their neighbours, which is the visible dash

The score is the fraction of columns whose ratio differs from the sheet's median
ratio. Integer tiers must score 0.000; that is not a hope, it is arithmetic, and
if they do not the metric is measuring noise and nothing it says about 1.5x
counts (law 88).

    python gate_row_banding.py [tgi ...] [--thresh 12] [--top 8]

With no TGI it runs the two #162 sheets plus a negative control. Offline,
read-only, reads build outputs only.
"""
import os
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
SRC1X = os.path.join(TOOLS, "dbpf", "extracted", "SimCity_1")
SEL = os.path.join(TOOLS, "selective-safe")

TIERS = [(1.5, os.path.join(SEL, "stage-15x")),
         (2.0, os.path.join(SEL, "stage")),
         (3.0, os.path.join(SEL, "stage-3x"))]

# The two buttons the user points at, plus a sheet never complained about.
DEFAULT = ["14015555", "13f15230", "14415860"]
CONTROL = "13d14ca0"

KEY = (255, 0, 255)


def find(d, tgi):
    for fn in os.listdir(d):
        if tgi in fn.lower() and fn.lower().endswith(".png"):
            return os.path.join(d, fn)
    return None


def load(path):
    im = Image.open(path).convert("RGB")
    return im.size[0], im.size[1], im.load()


def lum(p):
    return (p[0] * 299 + p[1] * 587 + p[2] * 114) // 1000


def ridge_profile(w, h, px, thresh, f):
    """thickness of the brightest local-max run in each column.

    ⛔ THE NEIGHBOUR OFFSET MUST SCALE WITH THE TIER. The first version of this
    probed a fixed 2 rows above and below at every factor. That works at 1x and
    breaks everywhere else: once a 1px ridge has been upscaled to f px thick,
    a +-2 probe lands INSIDE the ridge, both neighbours are as bright as the
    centre, and detection collapses - which is why the 3x median ratio came back
    as 0.50 instead of 3, and why 2x and 3x scored as ragged as 1.5x. The
    integer control failing is what caught it; without that control this would
    have shipped as fix number seven.

    Colour-key pixels are excluded: magenta is transparency, not brightness,
    and letting it into a luminance test would make every keyed sheet look
    like it had a ridge down its transparent surround.
    """
    off = max(2, int(round(2 * f)))
    out = [0] * w
    for x in range(w):
        run, bestrun = 0, 0
        for y in range(h):
            p = px[x, y]
            on = False
            if p != KEY and off <= y < h - off:
                a, b, c = lum(px[x, y - off]), lum(p), lum(px[x, y + off])
                if px[x, y - off] != KEY and px[x, y + off] != KEY:
                    on = (b - a) > thresh and (b - c) > thresh
            if on:
                run += 1
                if run > bestrun:
                    bestrun = run
            else:
                run = 0
        out[x] = bestrun
    return out


def score(tgi, thresh, top):
    s = find(SRC1X, tgi)
    if not s:
        print("  %s: no 1x source - REFUSAL, not a pass" % tgi)
        return None
    w1, h1, p1 = load(s)
    r1 = ridge_profile(w1, h1, p1, thresh, 1.0)
    if not any(r1):
        print("  %s: 1x has NO ridge at thresh=%d - the metric cannot see this "
              "sheet, so its verdict at any tier is meaningless" % (tgi, thresh))
        return None
    print("  %s  1x %dx%d  ridge present in %d/%d columns"
          % (tgi, w1, h1, sum(1 for v in r1 if v), w1))
    res = {}
    for f, d in TIERS:
        pth = find(d, tgi)
        if not pth:
            print("     f=%-4s NOT SHIPPED at this tier" % f)
            continue
        w, h, px = load(pth)
        rt = ridge_profile(w, h, px, thresh, f)
        ratios, cols = [], []
        for x in range(w):
            sx = int(x / f)
            if sx >= w1 or not r1[sx] or not rt[x]:
                continue
            ratios.append(rt[x] / r1[sx])
            cols.append(x)
        if not ratios:
            print("     f=%-4s no comparable column - REFUSAL" % f)
            continue
        med = sorted(ratios)[len(ratios) // 2]
        bad = [(cols[i], ratios[i]) for i in range(len(ratios))
               if abs(ratios[i] - med) > 1e-9]
        frac = len(bad) / len(ratios)
        res[f] = frac
        tag = "  <- CONTROL, must be 0.000" if f != 1.5 else "  <- the defect"
        print("     f=%-4s median ridge ratio %.2f   RAGGED %4d/%4d = %.3f%s"
              % (f, med, len(bad), len(ratios), frac, tag))
        if f == 1.5 and bad:
            runs, st = [], bad[0][0]
            for i in range(1, len(bad)):
                if bad[i][0] != bad[i - 1][0] + 1:
                    runs.append((st, bad[i - 1][0]))
                    st = bad[i][0]
            runs.append((st, bad[-1][0]))
            runs.sort(key=lambda r: r[0] - r[1])
            print("            widest thickened spans (x0..x1, len):")
            for a, b in runs[:top]:
                print("              x %4d..%-4d  len %3d" % (a, b, b - a + 1))
    return res


def main():
    thresh = int(sys.argv[sys.argv.index("--thresh") + 1]) if "--thresh" in sys.argv else 12
    top = int(sys.argv[sys.argv.index("--top") + 1]) if "--top" in sys.argv else 8
    args = [a for a in sys.argv[1:] if not a.startswith("--")
            and not a.isdigit()]
    sheets = args if args else DEFAULT + [CONTROL]

    print("ridge-thickness uniformity, thresh=%d\n" % thresh)
    allres = {}
    for t in sheets:
        allres[t] = score(t, thresh, top)
        print()

    ctrl_bad = [t for t, r in allres.items() if r
                and (r.get(2.0, 0) > 0.001 or r.get(3.0, 0) > 0.001)]
    if ctrl_bad:
        print("CONTROL FAILED on %s - an integer factor duplicates every row "
              "the same number of times, so a ragged ridge there is the "
              "METRIC's fault. Nothing this says about 1.5x is usable."
              % ", ".join(ctrl_bad))
        return 1
    hot = [t for t, r in allres.items() if r and r.get(1.5, 0) > 0.001]
    print("controls clean at 2x and 3x on every sheet measured.")
    if hot:
        print("RAGGED AT 1.5x ONLY: %s" % ", ".join(hot))
        return 0
    print("No sheet is ragged at 1.5x. The upscale thickens every ridge "
          "uniformly, so this mechanism is REFUTED and the cause is draw-time.")
    return 0


sys.exit(main())
