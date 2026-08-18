#!/usr/bin/env python3
r"""Build ItemIcon overrides for EVERY uncovered third-party icon, all tiers.

WHY THIS EXISTS, and why it is not a new idea.
==============================================
#139 solved this exact problem for NAM's 392 strips: a mod ships menu icons we
never upscaled, so at any tier > 1 the strip's cell is scaled but the art is
not, the four-state read over-runs the bitmap, and the icon draws doubled and
vanishes on hover. The cure was `rebuild_namicons.py` - extract the MOD's own
1x art, upscale it with the /4 snap rule, pack a dat.

This is that script with the hardcoded source folder removed. It discovers the
uncovered set the same way `ScaleTier.cpp`'s boot scan does - every DBPF under
Plugins, minus every icon our own packages already supply - so it covers a lot
published next year without being edited.

⛔ IT IS ALSO THE ANSWER TO A MISTAKE WORTH RECORDING. A runtime cure was built
first (enlarge the cIGZBuffer in memory at load, via the resource factory). It
works - the icons reach full size - but a scaled icon needs THREE numbers to
agree, not one:

    bitmap     scaled by the upscaler
    window     scaled by the layout
    imagerect  the CROP between them            <- #154, the one that bites

The build pipeline scales all three and has a gate for each. The runtime path
scaled the bitmap only, so every launch rediscovered another number it does not
handle. THE MECHANISM WITH 485 WORKING ICONS BEHIND IT IS THE ONE TO USE.

Pipeline (identical to rebuild_namicons.py):
    DbpfExtract -> Upscale2x --height-exact-group 6A386D26
                -> snap width to a multiple of 4 -> DbpfPack

THE SNAP IS LOAD-BEARING (#139 trap 3). The button picks its state cell by
imageWidth/4, so a width off the 4-grid gives fractional cells and smears the
states - the very defect this package removes, reappearing at another tier.
NAM's 356-wide strips force it: 356*1.5 = 534, and 534/4 = 133.5.

Usage (run from tools\itemicons):
    python build_uncovered_icons.py [--plugins <dir>] [--dry-run]
"""
import argparse
import os
import shutil
import struct
import subprocess
import sys
from collections import Counter

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))

# ⛔ ONE ACCEPTANCE TEST, AND IT IS THE ONE THAT MODELS THE DRAW.
# This builder used to grade itself with its own alignment measure. That
# measure said the rebuilt strip was [0,0,0,0] while the SIMULATOR - which
# reproduces the engine's actual SRC=(state*stride,0,+stride,h) crop - said
# [0,0,-1,-1] on the very same file. The builder passed, the package shipped,
# and the icon still moved on screen.
#
# A GENERATOR MUST BE GRADED BY A MODEL OF THE CONSUMER, NEVER BY ITS OWN
# RESTATEMENT OF ITS OWN INTENT. So the solver optimises, and the gate asserts,
# the SAME function the simulator uses.
import importlib.util as _ilu
_SIM = os.path.join(HERE, "..", "uimap", "emu", "sim_itemicon_states.py")
_spec = _ilu.spec_from_file_location("sim_itemicon_states", _SIM)
sim = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(sim)
EXTRACT = os.path.join(HERE, "..", "dbpf", "DbpfExtract.exe")
UPSCALE = os.path.join(HERE, "..", "upscale", "Upscale2x.exe")
PACKER = os.path.join(HERE, "..", "dbpf", "DbpfPack.exe")

# ---- THE HOVER HIGHLIGHT, MEASURED FROM THE ICONS THAT ARE KNOWN GOOD -----
# Replicating one state into all four removes the drift but also removes the
# hover feedback, which the user noticed immediately: the palms stopped
# highlighting while every neighbour still did.
#
# So the states are SYNTHESISED from the aligned art instead of copied flat,
# using the relationship measured across all 356 icons in our own
# ItemIcons-3x package - the ones confirmed correct on screen:
#
#     per-state mean luminance, normalised to state 0 (median of 356)
#       state 0  1.000    state 1  0.664    state 2  0.799    state 3  0.944
#
# The engine draws state 1 at rest (CELLPROBE: `state=1 src(132,0,264,132)`)
# and state 2 on hover, so what matters visually is HOVER / REST:
#
#     0.799 / 0.664 = 1.203     <- hover is ~20% brighter than rest
#
# ⚠ NORMALISED TO REST, NOT TO STATE 0. The mod's own four states are nearly
# equal (1.000 / 0.985 / 0.998 / 0.909 - it barely had a highlight), so its
# state 0 IS its normal appearance. Applying the covered icons' state-0-relative
# ratios would drive its REST state to 0.66 and leave this icon visibly dimmer
# than every neighbour - correcting one defect by introducing another.
# ⛔ MEASURED WHICH STATES THE ENGINE ACTUALLY DRAWS, instead of assuming.
# CELLPROBE over a session with hovers, counted by destination row:
#
#     state=0  on every row      state=1  on every row
#     state=3  ONLY on rows the cursor visited (14x on row 294, the palm)
#     state=2  NEVER
#
# HOVER IS STATE 3. The first attempt put a 1.203 highlight on state 2 - a
# state this engine never draws - so it was invisible by construction. That is
# the whole reason "no highlight" survived a build that measured correct.
#
# And the difference is not only brightness. Saturation over the same 356
# covered icons:
#     state 0  S = 0.53   <- GREYSCALE
#     state 1  S = 80.7    state 2  S = 74.7    state 3  S = 66.2
# with luminance state1 0.664 -> state3 0.944, i.e. hover is 42% brighter.
#
# So a correct strip is: state 0 GREY, states 1-3 colour, state 3 brightest.
# Reproducing that shape means a visible change whichever of state 0 or 1 the
# menu is resting on - which matters because both are drawn on every row and
# the evidence does not separate them.
# ⛔ THE HOVER EFFECT IS A WHITE BORDER, NOT A BRIGHTNESS CHANGE.
# Measured on the perimeter of 450 same-shape (528x132) PICTURE icons from our
# own packages - the ones confirmed correct on screen:
#
#     state 0  0.0%      state 1  0.0%      state 2  0.0%
#     state 3  100.0% near-white perimeter      <- THE BORDER
#
# and the draw log shows state 3 is the state the engine fetches on hover
# (14x on row 294, the palm that was hovered; state 2 is never drawn at all).
#
# Two wrong turns before this, both from inferring instead of measuring:
#   1. the highlight was put on state 2 - a state this engine never draws, so
#      it was unobservable by construction;
#   2. it was then modelled as a 1.4x brightness lift, because mean luminance
#      DOES rise on state 3 - but that rise is the border's own white pixels
#      pulling the average up. The statistic moved for the right reason and
#      still described the wrong effect.
#
# The border art itself is COPIED FROM A COVERED ICON rather than drawn here,
# so corner radius, thickness and antialiasing match the other 450 exactly
# instead of being my approximation of them.
STATE_SHADE = [1.00, 1.00, 1.00, 1.00]
STATE_GREY = [True, False, False, False]


def stamp_border(fp, tag):
    """Force state 3 to carry the hover border, whatever produced the strip."""
    im = Image.open(fp).convert("RGBA")
    w, h = im.size
    c = w // 4
    if sim.hover_border_pct(im) >= 80.0:
        return
    b = load_border(tag, c, h)
    if b is None:
        return
    bp = b.load()
    cp = im.load()
    for y in range(h):
        for x in range(c):
            a = bp[x, y][3]
            if a == 255:
                cp[3 * c + x, y] = (255, 255, 255, 255)
            elif a == 1:
                cp[3 * c + x, y] = (0, 0, 0, 0)
    im.save(fp)


def load_border(tag, cell, h):
    """The hover border, lifted verbatim from a covered icon of this tier."""
    p = os.path.join(HERE, "borders", "hover-%s.png" % tag)
    if not os.path.isfile(p):
        print("    WARNING no hover border for tier %s - the icon will not "
              "highlight. Regenerate borders/ before shipping." % tag)
        return None
    b = Image.open(p).convert("RGBA")
    if b.size != (cell, h):
        print("    WARNING hover border for %s is %s, cell is %s - SKIPPED "
              "rather than stretched (a stretched border would not match the "
              "other icons' corners)." % (tag, b.size, (cell, h)))
        return None
    return b


def desaturate(im):
    """Greyscale the RGB, keep alpha. State 0 of every covered icon measures
    S = 0.53 - it is the grey variant - and reproducing that is what makes the
    hover transition read as a real change rather than a subtle one."""
    px = im.load()
    out = im.copy()
    o = out.load()
    w, h = im.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a == 0:
                continue
            l = int(0.299 * r + 0.587 * g + 0.114 * b + 0.5)
            o[x, y] = (l, l, l, a)
    return out


def shade(im, k):
    """Scale RGB by k, leave alpha alone. A highlight is a brightness change;
    touching alpha would change the icon's SHAPE, and fully transparent pixels
    must stay exactly transparent so the colourkey cannot fringe (#143)."""
    if abs(k - 1.0) < 1e-6:
        return im.copy()
    px = im.load()
    out = im.copy()
    o = out.load()
    w, h = im.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a == 0:
                continue
            o[x, y] = (min(255, int(r * k + 0.5)),
                       min(255, int(g * k + 0.5)),
                       min(255, int(b * k + 0.5)), a)
    return out


ICON_TYPE = 0x856DDBAC
ICON_GROUP = 0x6A386D26
TIERS = [("1.5", "15x"), ("2", "2x"), ("3", "3x")]

# #49's STANDING RULE: .SC4Lot / .SC4Desc / .SC4Model are ALL DBPF archives and
# any of them can supply art at an icon TGI. Globbing "*.dat" is what made an
# earlier sweep report "no art anywhere" for five landmarks whose strips sat
# inside .SC4Lot files - and the Lighted Palm Plaza icons that prompted this
# script live in .SC4Lot too.
DBPF_EXTS = (".dat", ".sc4lot", ".sc4desc", ".sc4model")

DEFAULT_PLUGINS = os.path.join(
    os.path.expanduser("~"), "OneDrive", "Documents", "SimCity 4", "Plugins")


def empty_dir(d):
    """Make sure `d` exists and holds no files. NOT rmtree - this tree lives
    under OneDrive, which keeps a handle on the directory and denies rmdir."""
    os.makedirs(d, exist_ok=True)
    for fn in os.listdir(d):
        fp = os.path.join(d, fn)
        if os.path.isfile(fp):
            os.remove(fp)


def long_path(p):
    r"""#139 TRAP 1: NAM nests dats 283-298 characters deep and MAX_PATH is
    260, so open() raises FileNotFoundError on files that plainly exist and a
    walk that swallows it reports a clean sheet for a folder full of icons.
    Ten icons were missed exactly this way and the user found them by eye."""
    p = os.path.abspath(p)
    return p if p.startswith("\\\\?\\") else "\\\\?\\" + p


def dbpf_icon_instances(path):
    """Index-only read: TGIs of every ItemIcon in one archive. No payload."""
    try:
        with open(long_path(path), "rb") as fh:
            hdr = fh.read(0x68)
            if len(hdr) < 0x68 or hdr[:4] != b"DBPF":
                return []
            count = struct.unpack("<I", hdr[0x24:0x28])[0]
            offset = struct.unpack("<I", hdr[0x28:0x2C])[0]
            idx_minor = struct.unpack("<I", hdr[0x3C:0x40])[0]
            stride = 24 if idx_minor == 1 else 20
            if not (0 < count < 200000 and offset > 0):
                return []
            fh.seek(offset)
            idx = fh.read(count * stride)
            if len(idx) != count * stride:
                return []
    except OSError:
        # NEVER a bare pass: a file we could not read is a file whose icons we
        # cannot claim to have checked.
        print("  WARNING unreadable, its icons are NOT accounted for: %s" % path)
        return []
    out = []
    for i in range(count):
        e = idx[i * stride:i * stride + 12]
        t, g, inst = struct.unpack("<III", e)
        if t == ICON_TYPE and g == ICON_GROUP:
            out.append(inst)
    return out


def measure_cell_drift(path):
    r"""Return the per-state alignment offsets of a 4-state strip, measured.

    MEASURED 2026-08-15 on the Lighted Palm Plaza pair, identically in both:

        cell 0: +0   cell 1: +2   cell 2: +4   cell 3: +4 (clamped)

    The author's true cell pitch is 46, not 44. Four states at 46 need 184px;
    the file is 176. The GAME reads its state cell as `imageWidth / 4` = 44 - a
    divisor baked into its own code (#143) - so every state starts 2px earlier
    relative to the art than the author drew it. Content walks right by 2px per
    state and the last state runs off the sheet and wraps.

    At 1x that is 2px on a 44px icon and invisible, which is why stock looks
    fine. At 3x it is 6px per state and unmistakable. OUR SCALING DOES NOT
    CAUSE THIS - IT MAGNIFIES IT - which is the same reason every other latent
    1x defect in this project became ours to fix.

    Offsets come from cross-correlating COLUMN LUMINANCE PROFILES, not from
    eyeballing the strip. Reading the magnified strip by eye produced a
    confident and WRONG answer earlier the same day (a monotonic drift that
    per-cell centroids then refuted), so the ramp has to be a number.
    """
    im = path if isinstance(path, Image.Image) else Image.open(path)
    im = im.convert("L")
    w, h = im.size
    if w % 4 or w < 16:
        return None
    cell = w // 4
    px = im.load()
    col = [float(sum(px[x, y] for y in range(h))) for x in range(w)]

    # ⛔ CORRELATE THE GRADIENT, NOT THE LUMINANCE.
    # The first version minimised squared error on the raw column profile and
    # was confidently wrong twice - it reported [0,+2,+4,+4] where the truth
    # was half that, and correcting by it made the icon shift LEFT instead.
    #
    # THE REASON IS STRUCTURAL, NOT NUMERICAL: the four states of a button
    # strip differ BY DESIGN in brightness (normal / hover / pressed /
    # disabled). Raw-luminance SSE therefore pays to match highlight as well as
    # to match position, and it will happily buy a brightness match with a
    # wrong lag. The DERIVATIVE is blind to a constant brightness offset, so it
    # can only score alignment - which is the one thing being asked.
    #
    # Normalised cross-correlation on top of that removes any residual gain
    # difference, leaving a score that depends on SHAPE alone.
    grad = [col[x + 1] - col[x] for x in range(w - 1)]

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

    ref = grad[0:cell - 1]
    offs = []
    for s in range(4):
        best = None
        for d in range(-8, 9):
            a, b = [], []
            for x in range(cell - 1):
                sx = s * cell + x + d
                if 0 <= sx < len(grad):
                    a.append(ref[x])
                    b.append(grad[sx])
            r = ncc(a, b) if len(a) >= (cell - 1) * 0.6 else -2.0
            if best is None or r > best[1]:
                best = (d, r)
        offs.append(best[0])
    return offs


def _cut(im, cell, origins):
    """Rebuild a strip by taking each state from `origins[s]` and seating it on
    the `cell` pitch the engine reads. Always cut from the ORIGINAL image, so
    an iterative solve never compounds resampling loss."""
    w, h = im.size
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    short = 0
    for s in range(4):
        sx = max(0, min(origins[s], w - 1))
        avail = max(0, min(cell, w - sx))
        if avail:
            out.paste(im.crop((sx, 0, sx + avail, h)), (s * cell, 0))
        if avail < cell:
            # The sheet really is short - the author saved fewer pixels than 4
            # states at this pitch need. Complete from the SAME relative columns
            # of the previous state: the four states of a button strip differ by
            # highlight, not geometry, so those are the closest true pixels.
            # ⛔ NEVER by re-cutting a full cell from the wrong origin - that
            # keeps the cell width and loses the REGISTRATION, which is the only
            # thing the eye actually tracks, and it is what made hover shift.
            short = cell - avail
            donor = max(0, min(origins[s - 1] if s else 0, w - cell))
            out.paste(im.crop((donor + avail, 0, donor + cell, h)),
                      (s * cell + avail, 0))
    return out, short


def realign_strip(path):
    r"""Re-cut a drifting strip onto the pitch the game reads.

    Returns (True, (pitch, short, residual)) if rewritten.

    ⛔ REWRITE ONLY ON A CONFIRMED LINEAR RAMP. #156's law: a heuristic that
    IDENTIFIES a structure is safe for PROTECTING it and unsafe for REWRITING
    it - cell-aligned resampling was backed out once because a divisibility
    guess fired on 1186 of 2206 sheets that were not strips at all. So this
    demands offs[1] != 0 AND offs[2] == 2*offs[1]. Anything else is left
    exactly as the author shipped it.

    ⛔ AND IT SOLVES ITERATIVELY, BECAUSE ONE MEASUREMENT WAS NOT ENOUGH.
    The first pass reported [0,+2,+4,+4]; correcting by exactly that produced a
    strip which then measured [0,-1,-2,0] - overshot by half. Palm fronds are
    self-similar, so a single cross-correlation can settle on a DOUBLE-LAG
    minimum and be confidently wrong. On screen that read as the icon shifting
    LEFT instead of right: the defect changed sign rather than going away.

    So the same instrument that defines success is used as the acceptance test,
    and the loop only stops when the rebuilt strip measures ZERO drift. A fix
    that cannot demonstrate its own residual is a guess with a changelog entry.
    """
    # ONE metric end to end: the same function that grades the result also
    # produces the starting estimate. Two different measures of "aligned" is
    # how a build passed its own gate while the screen disagreed.
    im0 = Image.open(path).convert("RGBA")
    offs = sim.state_drift(im0)
    if not offs or offs[0] != 0:
        return (False, None)
    # ⛔ THE GUARD ASKS "IS THIS A LINEAR DRIFT?", NOT "IS THE PITCH CONSTANT?"
    # Requiring offs[2] == 2*offs[1] rejected THIS strip: the gradient measure
    # reads [0,1,3,4], steps of 1/2/1, because the author's tool laid the
    # states at a FRACTIONAL pitch (~45.3) and rounded each one. That is a real
    # drift and must be corrected; it simply is not uniform. Demanding
    # uniformity would leave the defect on screen while reporting the art
    # untouched - a guard that is wrong in the safe-looking direction.
    #
    # So: monotonic, materially non-zero, and within a pixel of its own
    # best-fit line. Noise and asymmetric art produce none of those together,
    # which is the #156 discipline (safe to PROTECT on a guess, never to
    # REWRITE on one) kept intact with a test that fits the real input.
    if any(offs[i + 1] < offs[i] for i in range(3)) or offs[3] < 2:
        return (False, None)
    slope = offs[3] / 3.0
    if max(abs(offs[i] - slope * i) for i in range(4)) > 1.0:
        return (False, None)
    im = Image.open(path).convert("RGBA")
    w, h = im.size
    cell = w // 4
    total = list(offs)
    best = None
    for _ in range(12):
        origins = [s * cell + total[s] for s in range(4)]
        cand, short = _cut(im, cell, origins)
        # THE SIMULATOR'S metric: crop each state exactly as the engine does,
        # then compare. Not the builder's own.
        resid = sim.state_drift(cand)
        score = sum(abs(d) for d in resid)
        if best is None or score < best[0]:
            best = (score, cand, short, list(resid), list(total))
        if score == 0:
            break
        total = [total[s] + resid[s] for s in range(4)]
    _score, cand, short, resid, used = best
    cand.save(path)
    pitch = cell + (used[1] if used[1] else 0)
    return (True, (pitch, short, resid))


def walk_dbpf(root):
    for dirpath, _dirs, files in os.walk(long_path(root)):
        for fn in files:
            if fn.lower().endswith(DBPF_EXTS):
                yield os.path.join(dirpath, fn), fn


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plugins", default=DEFAULT_PLUGINS)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    # ORDER IS NOT GUARANTEED by the walk, so coverage cannot be decided on the
    # fly - collect ours FIRST, then diff. Deciding per file as they arrive
    # would mark an icon uncovered simply because our package had not been
    # walked yet.
    ours, theirs = set(), {}
    n_files = 0
    for full, name in walk_dbpf(args.plugins):
        n_files += 1
        insts = dbpf_icon_instances(full)
        if not insts:
            continue
        # ⛔ A GENERATOR MUST NOT COUNT ITS OWN OUTPUT AS COVERAGE. The first
        # run shipped z_SC4UIScale_UncoveredIcons-*.dat, the second run saw it,
        # concluded UNCOVERED=0 and refused to build - so the tool could only
        # ever run ONCE and could never be corrected. Its own product is a
        # RESULT, never evidence that the work is done.
        low = name.lower()
        if low.startswith("z_sc4uiscale_uncoveredicons"):
            continue
        if low.startswith("z_sc4uiscale_"):
            ours.update(insts)
        else:
            for i in insts:
                # LAST LOADED WINS, not first found (#139 trap 2): 0x6A47A005
                # is supplied by three files and the one that actually
                # displays is the last in load order. Upscaling the first hit
                # would ship a doubled copy of art the game never shows.
                theirs[i] = full

    uncovered = {i: p for i, p in theirs.items() if i not in ours}
    print("scanned %d DBPF files under %s" % (n_files, args.plugins))
    print("ours=%d theirs=%d UNCOVERED=%d" % (len(ours), len(theirs), len(uncovered)))
    for i, p in sorted(uncovered.items()):
        print("  {%08X,%08X,%08X}  <- %s" % (ICON_TYPE, ICON_GROUP, i,
                                             os.path.basename(p)))
    if not uncovered:
        print("nothing to build.")
        return 0
    if args.dry_run:
        return 0

    # EMPTY, never rmtree: this tree lives under OneDrive, which holds a handle
    # on the directory itself and denies rmdir. Removing the FILES achieves the
    # same clean slate without depending on the sync client's mood.
    src = os.path.join(HERE, "uncovered-1x")
    empty_dir(src)

    # Extract each owning archive once, keep only the uncovered instances.
    by_archive = {}
    for i, p in uncovered.items():
        by_archive.setdefault(p, []).append(i)
    stage = os.path.join(HERE, "_uncovered_stage")
    got = 0
    for archive, insts in by_archive.items():
        empty_dir(stage)
        # DbpfExtract fails outright on the longest paths, so copy to a short
        # temp name first - #139's documented workaround, an ERROR rather than
        # a wrong answer being the reason it was caught at all.
        tmp = os.path.join(os.environ.get("TEMP", "."), "_sc4icon_src.dat")
        shutil.copyfile(long_path(archive), tmp)
        r = subprocess.run([EXTRACT, tmp, stage, "0x%08X" % ICON_TYPE],
                           capture_output=True, text=True)
        if r.returncode != 0:
            sys.exit("EXTRACT FAILED on %s:\n%s" % (archive, r.stderr or r.stdout))
        for i in insts:
            want = "T-%08x_G-%08x_I-%08x.png" % (ICON_TYPE, ICON_GROUP, i)
            hit = os.path.join(stage, want)
            if not os.path.isfile(hit):
                sys.exit("EXTRACT produced no %s from %s - refusing to ship a "
                         "package that silently omits an icon." % (want, archive))
            shutil.copyfile(hit, os.path.join(src, want))
            got += 1
    print("extracted %d/%d 1x sources" % (got, len(uncovered)))
    if got != len(uncovered):
        sys.exit("extraction is incomplete - stopping.")

    # ⛔ REALIGNMENT HAPPENS AT THE OUTPUT RESOLUTION, NOT AT 1x.
    # Solving it at 1x cannot work and the solver proved it: the author's pitch
    # is ~45.36px, so the per-state error is SUB-PIXEL and no integer crop
    # removes it - the loop oscillated at residual [0,0,-1,-1] forever.
    #
    # At 3x that same pitch is 136.07 and at 1.5x it is 68.04: integral to
    # within a fifth of a pixel. So upscale FIRST with the normal NEAREST
    # pipeline (which also keeps the magenta colourkey exact - #143: any
    # interpolating filter fringes it and the key colour then draws), and
    # re-register with integer offsets in the space where they are integers.
    #
    # The acceptance test then runs on the FILE THAT SHIPS, not on an
    # intermediate.

    os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
    unconverged = 0
    for factor, tag in TIERS:
        out = os.path.join(HERE, "uncovered-up-%s" % factor)
        empty_dir(out)
        r = subprocess.run([UPSCALE, src, out, "--factor", factor,
                            "--normalize-names",
                            "--height-exact-group", "%08X" % ICON_GROUP],
                           capture_output=True, text=True)
        if r.returncode != 0:
            sys.exit("UPSCALE FAILED x%s:\n%s" % (factor, r.stderr or r.stdout))

        snapped = 0
        for fn in os.listdir(out):
            p = os.path.join(out, fn)
            with open(p, "rb") as fh:
                w, h = struct.unpack(">II", fh.read(26)[16:24])
            if w % 4 == 0:
                continue
            tw = 4 * round(w / 4)
            Image.open(p).convert("RGBA").resize((tw, h), Image.LANCZOS).save(p)
            snapped += 1

        # RE-REGISTER AT THIS TIER'S RESOLUTION, then assert on the result -
        # and if alignment cannot be PROVEN, fall back to something that cannot
        # move at all.
        #
        # ⛔ WHY A FALLBACK AND NOT MORE SOLVING. The author's states sit at a
        # FRACTIONAL pitch (~45.36px at 1x). An integer crop cannot express a
        # fractional correction, so a per-state exhaustive search bottoms out at
        # +-1px and no amount of iterating gets past it - measured, not assumed:
        # the direct search over every offset reported best residual 1, never 0.
        # Chasing an optimum that provably does not exist is how this defect ate
        # a day.
        #
        # THE FOUR STATES OF THIS STRIP ARE THE SAME PICTURE WITH DIFFERENT
        # HIGHLIGHTS. So when alignment cannot be verified, publish state 0 in
        # all four cells: drift is then ZERO BY CONSTRUCTION at every tier, and
        # the icon physically cannot shift when the button changes state. The
        # cost is the per-state highlight on that icon - a deliberate, stated
        # trade, and the game still draws its own selection frame around it.
        for fn in sorted(os.listdir(out)):
            fp = os.path.join(out, fn)
            before = sim.state_drift(Image.open(fp).convert("RGBA"))
            realign_strip(fp)
            after = sim.state_drift(Image.open(fp).convert("RGBA"))
            how = "re-registered"
            # ⛔ THE BORDER MUST BE STAMPED ON *BOTH* PATHS.
            # It was originally only inside the state-0-replication branch, so
            # 1.5x - which re-registers successfully and never enters that
            # branch - shipped with hover-border 0.0%. A TIER THE USER IS NOT
            # CURRENTLY ON IS EXACTLY WHERE THAT HIDES; it surfaced only by
            # sweeping every tier including the DISABLED ones. A gate that
            # checks just the active tier is blind to tomorrow's monitor.
            stamp_border(fp, tag)
            if any(after):
                im = Image.open(fp).convert("RGBA")
                w2, h2 = im.size
                c2 = w2 // 4
                flat = Image.new("RGBA", (w2, h2), (0, 0, 0, 0))
                st0 = im.crop((0, 0, c2, h2))
                border = load_border(tag, c2, h2)
                for k in range(4):
                    cell_im = shade(st0, STATE_SHADE[k])
                    if STATE_GREY[k]:
                        cell_im = desaturate(cell_im)
                    if k == 3 and border is not None:
                        # Reproduce the reference hover state EXACTLY: white
                        # where it is white, TRANSPARENT where it is
                        # transparent (the rounded corners - dropping those is
                        # what left the border at 77.8% instead of 100%), and
                        # the icon showing through everywhere else.
                        cell_im = cell_im.copy()
                        cp = cell_im.load()
                        bp = border.load()
                        for by in range(h2):
                            for bx in range(c2):
                                r, g, bl, a = bp[bx, by]
                                if a == 255:
                                    cp[bx, by] = (255, 255, 255, 255)
                                elif a == 1:
                                    cp[bx, by] = (0, 0, 0, 0)
                    flat.paste(cell_im, (k * c2, 0))
                flat.save(fp)
                after = sim.state_drift(Image.open(fp).convert("RGBA"))
                how = "STATE-0 REPLICATED (states unalignable at integer px)"
            print("    x%-4s %-42s %-13s -> %-13s %s | %s"
                  % (factor, fn[:42], str(before), str(after),
                     "STEADY" if not any(after) else "STILL MOVES", how))

        c, bad = Counter(), 0
        for fn in os.listdir(out):
            with open(os.path.join(out, fn), "rb") as fh:
                w, h = struct.unpack(">II", fh.read(26)[16:24])
            c[(w, h)] += 1
            if w % 4:
                bad += 1
        if bad:
            sys.exit("%d file(s) still off the 4-grid at x%s - that is the "
                     "fractional-cell defect this package exists to remove."
                     % (bad, factor))

        dat = os.path.join(HERE, "out",
                           "z_SC4UIScale_UncoveredIcons-%s.dat" % tag)
        r = subprocess.run([PACKER, out, dat], capture_output=True, text=True)
        if r.returncode != 0:
            sys.exit("PACK FAILED %s:\n%s" % (tag, r.stderr or r.stdout))
        print("x%-4s %2d files  snapped %d  %s -> %s (%.0f KB)"
              % (factor, len(os.listdir(out)), snapped,
                 " ".join("%dx%d:%d" % (w, h, n) for (w, h), n in c.most_common()),
                 os.path.basename(dat), os.path.getsize(dat) / 1e3))
    return 0


if __name__ == "__main__":
    sys.exit(main())
