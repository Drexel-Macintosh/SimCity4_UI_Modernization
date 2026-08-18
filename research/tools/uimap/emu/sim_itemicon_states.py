#!/usr/bin/env python3
r"""SIMULATE the engine's four-state icon draw, offline, for every combination.

WHY THIS EXISTS
===============
#149 was declared fixed four times and was wrong on screen four times. Every
one of those claims described what the BUILD did - "realigned", "residual
[0,0,0,0]", "packed 528x132" - and none of them described what the GAME WOULD
DRAW. Those are different statements, and only the second one is the bug.

So this reproduces the engine's own arithmetic, measured from the live blit
(CELLPROBE, 2026-08-15):

    tex=528x132  texW/4=132  stride=132  state=1
    src(132,0,264,132) -> dst(0,147,132,279)

i.e. the draw takes SRC = (state*stride, 0, +stride, texH) with
`stride = imageWidth / 4` (#143 - an integer divide baked into the exe) and
blits it 1:1. So each state is simply a stride-wide window, and TWO STATES LOOK
SHIFTED RELATIVE TO EACH OTHER EXACTLY WHEN THEIR CONTENT IS NOT AT THE SAME
OFFSET INSIDE THEIR OWN WINDOW.

WHAT IT SWEEPS
    - every source it is given (deployed dat, build output, untouched original)
    - every tier package present (1.5x / 2x / 3x)
    - all four states of each
and reports, per state, the alignment of that state's content against state 0.
Nonzero anywhere = the icon will visibly move when the button changes state.

⛔ IT READS THE DEPLOYED DAT, NOT THE BUILD DIRECTORY. A build artefact proves
what was produced; only the deployed file proves what the game can load. Three
packages in this project rotted precisely in that gap.

Usage:
    python sim_itemicon_states.py                 # sweep everything it finds
    python sim_itemicon_states.py --png a.png     # one strip
    python sim_itemicon_states.py --montage out.png
"""
import argparse
import os
import subprocess
import struct
import sys
import tempfile

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
EXTRACT = os.path.join(ROOT, "tools", "dbpf", "DbpfExtract.exe")

ICON_TYPE = 0x856DDBAC
ICON_GROUP = 0x6A386D26
PLUGINS = os.path.join(os.path.expanduser("~"), "OneDrive", "Documents",
                       "SimCity 4", "Plugins")


def grad_profile(im):
    """Column-gradient profile. THE GRADIENT, not the luminance: the four
    states differ BY DESIGN in brightness, so any metric sensitive to a
    constant brightness offset is measuring the highlight instead of the
    position. That error already produced two wrong answers on this art."""
    g = im.convert("L")
    w, h = g.size
    px = g.load()
    col = [float(sum(px[x, y] for y in range(h))) for x in range(w)]
    return [col[x + 1] - col[x] for x in range(w - 1)]


def ncc(a, b):
    n = len(a)
    if n < 4:
        return -2.0
    ma, mb = sum(a) / n, sum(b) / n
    da = [v - ma for v in a]
    db = [v - mb for v in b]
    na = sum(v * v for v in da) ** 0.5
    nb = sum(v * v for v in db) ** 0.5
    if na < 1e-9 or nb < 1e-9:
        return -2.0
    return sum(da[i] * db[i] for i in range(n)) / (na * nb)


def draw_states(im):
    """Return the four images the ENGINE will put on screen, by its own rule:
    SRC = (state*stride, 0, +stride, h) with stride = width/4, blitted 1:1."""
    w, h = im.size
    stride = w // 4
    return [im.crop((s * stride, 0, s * stride + stride, h)) for s in range(4)]


def state_drift(im, span=None):
    """Per-state content offset relative to state 0, measured on what the
    engine actually draws. This is the number that decides whether the user
    sees the icon move."""
    states = draw_states(im)
    if span is None:
        # ⛔ A FIXED SPAN IS A SILENT CLAMP. At 1x the drift was 4px and +-10
        # was ample; at 3x the SAME defect is 12px, the search hit its own
        # edge, and the result [0,3,9,9] then failed a linearity guard - so the
        # strip was reported "not a ramp" and left untouched. The instrument's
        # range must scale with what it measures.
        span = max(12, states[0].size[0] // 2)
    profs = [grad_profile(s) for s in states]
    ref = profs[0]
    n = len(ref)
    out = []
    for p in profs:
        best = None
        for d in range(-span, span + 1):
            a, b = [], []
            for x in range(n):
                sx = x + d
                if 0 <= sx < len(p):
                    a.append(ref[x])
                    b.append(p[sx])
            r = ncc(a, b) if len(a) >= n * 0.6 else -2.0
            if best is None or r > best[1]:
                best = (d, r)
        out.append(best[0])
    return out


def icons_from_dat(path):
    """Extract this package's ItemIcon PNGs. Reads the DEPLOYED file."""
    out = {}
    if not os.path.isfile(path):
        return out
    tmp = tempfile.mkdtemp(prefix="simicon_")
    # Copy to a short path first: DbpfExtract fails outright on the longest
    # names (#139 trap 1), and an error there would look like "no icons".
    short = os.path.join(tempfile.gettempdir(), "_simicon_src.dat")
    with open(path, "rb") as a, open(short, "wb") as b:
        b.write(a.read())
    r = subprocess.run([EXTRACT, short, tmp, "0x%08X" % ICON_TYPE],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print("  EXTRACT FAILED on %s: %s" % (path, (r.stderr or r.stdout)[:200]))
        return out
    for fn in sorted(os.listdir(tmp)):
        if not fn.lower().endswith(".png"):
            continue
        # ⛔ GROUP-SCOPED, because the 4-state model is only TRUE for the menu
        # ItemIcon group. DbpfExtract filters by TYPE, and type 856DDBAC also
        # carries 768x600 backgrounds and 285x30 dialog bands - none of which
        # are strips. Judging those by width/4 is #156's exact mistake (a
        # structural guess applied outside the scope where it holds), and it
        # produced 60+ meaningless BAD lines the first time this ran wide.
        # ⚠ lower-case BOTH sides. The first version compared "_G-..." against
        # fn.lower(), so it matched NOTHING and every icon was filtered out -
        # and the sweep then printed "ALL OK" over an empty set. A VACUOUS PASS
        # IS THE WORST FAILURE A GATE HAS, because it looks exactly like
        # success. Only the CONTROL caught it: "CONTROL DID NOT MOVE" fired
        # while a mod with a known icon was installed, which is impossible if
        # the probe can see anything at all.
        if ("_g-%08x_" % ICON_GROUP) not in fn.lower():
            continue
        try:
            out[fn] = Image.open(os.path.join(tmp, fn)).convert("RGBA")
        except Exception as e:
            print("  unreadable %s: %s" % (fn, e))
    return out


def hover_border_pct(im):
    """% of state 3's perimeter that is near-white - the hover border.
    Measured at 100% on 450 covered picture icons, 0% on states 0-2."""
    w, h = im.size
    c = w // 4
    cr = im.crop((3 * c, 0, 4 * c, h)).convert("RGBA")
    px = cr.load()
    ring = []
    for x in range(c):
        for y in (0, 1, h - 2, h - 1):
            ring.append(px[x, y])
    for y in range(h):
        for x in (0, 1, c - 2, c - 1):
            ring.append(px[x, y])
    return 100.0 * sum(1 for p in ring if min(p[:3]) > 200 and p[3] > 128) / len(ring)


def report(label, name, im):
    w, h = im.size
    stride = w // 4
    drift = state_drift(im)
    # ⛔ STATE 3 IS EXCLUDED FROM THE DRIFT TEST, AND THE CONTROL SAYS WHY.
    # State 3 carries the white hover border, which dominates the column
    # gradient - so correlating its SHAPE against state 0 measures the border,
    # not the icon's position. Measured on 80 known-good covered icons:
    # median |state 3 drift| = 33px, nonzero on 92% of them. Judging our output
    # by that number would mean chasing a defect the correct icons all have.
    #
    # So each state is asked the question it can answer: states 0-2 must not
    # move, and state 3 must HAVE THE BORDER.
    border = hover_border_pct(im)
    # THRESHOLD MEASURED, NOT INVENTED. 120 known-good covered icons all
    # return EXACTLY 81.8% from this function (min = median = p90 = 81.8) -
    # the rounded corners are transparent and never count. A 90% threshold was
    # my guess and would have failed every correct icon in the game.
    bad = any(drift[:3]) or border < 80.0
    print("  %-40s %4dx%-4d stride %3d  states(0-2) %-11s hover-border %5.1f%%  %s"
          % (name[:40], w, h, stride, str(drift[:3]), border,
             "BAD" if bad else "ok"))
    return bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--png", action="append", default=[])
    ap.add_argument("--montage")
    args = ap.parse_args()

    any_bad = False
    ctl_bad = False
    montage_src = []

    if args.png:
        print("SINGLE FILES")
        for p in args.png:
            im = Image.open(p).convert("RGBA")
            any_bad |= report("png", os.path.basename(p), im)
            montage_src.append((os.path.basename(p), im))
    else:
        # THE DEPLOYED PACKAGES - what the game can actually load, all tiers,
        # including the ones currently disabled, because a tier switch must not
        # reintroduce the defect.
        zzz = os.path.join(PLUGINS, "zzz-SC4UIScale")
        cands = []
        if os.path.isdir(zzz):
            for fn in sorted(os.listdir(zzz)):
                if "UncoveredIcons" in fn:
                    cands.append(os.path.join(zzz, fn))
        # THE UNTOUCHED SOURCE - the control. If OUR art measures steady and
        # the screen still moves, the game is not drawing our art, and that is
        # a completely different bug from the one being fixed.
        # ⛔ THE CONTROL MUST NOT BE HARDCODED TO ONE MOD. It matched "palm",
        # which was fine while Lighted Palm Plaza was the only test case and
        # useless the moment another plugin is installed - a probe that can
        # only see the sample you already fixed.
        #
        # So: any third-party DBPF that supplies an ItemIcon our packages do
        # not. That makes this a PRE-FLIGHT CLASSIFIER - run it after
        # installing a mod and it says, before the game is ever launched,
        # whether that mod's strips are well-formed (states steady + border
        # present -> the runtime enlargement alone should suffice) or
        # pathological like the palms (needs build_uncovered_icons.py).
        for dirpath, _d, files in os.walk(PLUGINS):
            for fn in files:
                if not fn.lower().endswith((".dat", ".sc4lot", ".sc4desc",
                                            ".sc4model")):
                    continue
                if fn.lower().startswith("z_sc4uiscale_"):
                    continue
                cands.append(os.path.join(dirpath, fn))

        for c in cands:
            print("\n%s" % os.path.relpath(c, PLUGINS))
            icons = icons_from_dat(c)
            if not icons:
                print("  (no ItemIcon entries)")
                continue
            # ⛔ THE UNTOUCHED SOURCE MUST NOT FAIL THE RUN. It is the CONTROL
            # and it is SUPPOSED to move - that drift is the defect our package
            # exists to override. Counting it would make the gate permanently
            # red and therefore ignored, which is worse than no gate.
            # OURS is decided by NAME, not by extension: third-party mods ship
            # .dat files too, and calling those "ours" put their untouched art
            # into the pass/fail verdict.
            is_control = not os.path.basename(c).lower().startswith(
                "z_sc4uiscale_")
            for name, im in icons.items():
                bad = report(c, name, im)
                if is_control:
                    ctl_bad = ctl_bad or bad
                else:
                    any_bad |= bad
                montage_src.append(("%s :: %s" % (os.path.basename(c), name), im))

    if args.montage and montage_src:
        cellh = max(im.size[1] for _n, im in montage_src)
        rows = []
        for _n, im in montage_src:
            states = draw_states(im)
            sw = states[0].size[0]
            row = Image.new("RGBA", (4 * sw + 3 * 6, cellh), (255, 0, 255, 255))
            for i, st in enumerate(states):
                row.paste(st, (i * (sw + 6), 0))
            rows.append(row)
        W = max(r.size[0] for r in rows)
        out = Image.new("RGBA", (W, sum(r.size[1] + 8 for r in rows)),
                        (20, 20, 20, 255))
        y = 0
        for r in rows:
            out.paste(r, (0, y))
            y += r.size[1] + 8
        out.save(args.montage)
        print("\nmontage -> %s (each row = the 4 states the engine draws)"
              % args.montage)

    print("")
    print("OUR PACKAGES: %s" % ("SOME STATES MOVE - it will shift on screen"
                                if any_bad else
                                "ALL OK in every combination simulated "
                                "(tier x icon x state)"))
    if ctl_bad:
        # ⛔ THE CONTROL IS SUPPOSED TO FAIL. It is the untouched mod art - the
        # defect our packages override - and its failure is what proves this
        # measurement can detect movement at all. Counting it in the verdict
        # would leave the gate permanently red, which is how a gate becomes
        # something everyone learns to ignore.
        print("CONTROL (untouched third-party art): moves, AS REQUIRED - "
              "proof the probe can see the defect it tests for.")
    else:
        print("WARNING: CONTROL DID NOT MOVE - either no third-party icons "
              "are installed, or this probe can no longer detect movement. "
              "Do not trust the PASS above until that is explained.")
    return 1 if any_bad else 0


if __name__ == "__main__":
    sys.exit(main())
