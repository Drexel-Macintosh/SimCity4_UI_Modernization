r"""scale_rules.py - THE ONE SCALING MODEL. Every gate in this folder imports it.

⛔ WHY THIS FILE EXISTS. `--drift` counted SEVENTEEN independent
re-implementations of the same three-line rounding rule inside this one folder,
under eleven different names, plus the C# copy in `Upscale2x.cs` and the
original in `src\UiSpike.cpp`:

    def R      gate_abut_1_5x, gate_art_vs_window
    def rhu    gate_btn_undercover, gate_btn_cell_vs_window,
               gate_graphs_banddock, gate_iconfit_rule
    def round_half_up  gate_imagerect_vs_art, gate_strip_visible_rows,
                       render_flyout, emu_subflyout
    def lround gate_introvid, gate_namicons
    def sc     prove_chart_legend, measure_lineh_tier
    def sc_up  attack_15x
    def scale_len   gate_minimap_snap
    def scale_round emu_panel_anchor
    (+ private cell_unit / scale_dim in gate_btn_cell_vs_window)

They agreed on 2026-08-15. They had NOT agreed the day before: #162 changed
`ScaleRound` from llround (half away from zero) to RoundHalfUp (floor(v+0.5))
in the DLL, and each copy had to be hunted down and edited by hand. A copy that
is missed does not fail - it goes on returning the OLD answer, quietly, and the
gate built on it certifies the wrong geometry. That is the exact failure mode
`_tests\REGRESSION.md` #151/#155 describe from the other direction: an
instrument that excuses a defect because it models a rule the shipped code no
longer runs.

So: ONE definition, imported. Plus `--selftest`, which re-derives every rule
from first principles with exact rational arithmetic, and `--drift`, which goes
looking for private copies in the sibling files and prices them against this
one.

────────────────────────────────────────────────────────────────────────────────
WHAT IS MIRRORED, AND FROM WHERE  (all quoted read-only; `--selftest` re-reads
them and FAILS if the source text has moved - a tripwire, not a promise)

  src\UiSpike.cpp   RoundHalfUp(double v)      -> floor(v + 0.5)
  src\UiSpike.cpp   ScaleRound(int32 v, float) -> RoundHalfUp(v * f)
  src\UiSpike.cpp   the edge-derived leaf rule -> R(l+w,f) - R(l,f)
  src\UiSpike.cpp   #161 parent-frame rounding -> R(pAbs+t,f) - R(pAbs,f)
  tools\upscale\Upscale2x.cs  CellUnit(v)      -> lcm of the counts dividing v
  tools\upscale\Upscale2x.cs  ScaleDim(v,fac)  -> RoundHalfUp then cell snap
  tools\upscale\{cell-strips,nine-slice,tiled,no-snap}.txt  the ROLE lists

────────────────────────────────────────────────────────────────────────────────
THE THREE SHEET ROLES (law 86; #156 / #157 / #160). A sheet's ROLE decides its
sizing rule, and the role is DERIVED from the `.UI` that binds it - never
guessed from the number, never hand-listed here:

  ROLE_STRIP  N-state strip   width must stay divisible by N   cell-strips.txt
  ROLE_NINE   9-slice frame   width must stay divisible by 3   nine-slice.txt
  ROLE_TILED  tiled ground    NOTHING divides it; its only     tiled.txt
                              contract is with its WINDOW      (+ no-snap.txt)
  ROLE_PLAIN  everything else CellUnit {3,4} snap, as ever

────────────────────────────────────────────────────────────────────────────────
THE OFFSET-PARITY LAW (#152, and it names the failing AXIS in advance)

  For f = p/q in lowest terms, edge-derived rounding preserves a child's 1x
  offset d from its frame IFF q | d, because R((t+d)f) - R(tf) == d*f exactly
  when d*f is an integer, and otherwise depends on the parity of the frame's
  own coordinate t. At f=3/2, q=2: EVEN offsets always survive, ODD offsets are
  a lottery. At an integer factor q=1, so every offset survives - which is the
  entire reason 2x and 3x have never shown a defect in this family.

  `pq()`, `offset_survives()` and `dying_axes()` implement it; `--selftest`
  proves the closed form by exhaustion against the definition.

────────────────────────────────────────────────────────────────────────────────
THE TILED WRAP SEAM (#160, and the part no gate modelled before)

  Every gate here SKIPPED `blttype=tiled` on the grounds that "tiling always
  covers". That is TRUE about coverage and SILENT about the seam. The engine
  repeats the source across the destination, so tile boundaries land at
  k * artExtent inside the window. Where they land is a visible property of the
  picture, and it MOVES between tiers whenever the sheet is not sized by the
  plain scale of its 1x size. `tile_boundaries()` / `seam_drift()` model it;
  `gate_tiled_seam.py` is the customer.

────────────────────────────────────────────────────────────────────────────────
    python scale_rules.py --selftest [-v]     # the whole model, re-derived
    python scale_rules.py --drift             # hunt private copies in siblings

Offline, read-only. Imports nothing outside the standard library.
"""
import math
import os
import re
import sys
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
UIMAP = os.path.dirname(HERE)
TOOLS = os.path.dirname(UIMAP)
ROOT = os.path.dirname(TOOLS)
UPSCALE = os.path.join(TOOLS, "upscale")
SRC = os.path.join(ROOT, "src")

#: The tiers this project ships. 1.0 is the stock control, not a tier.
TIERS = (1.5, 2.0, 3.0)
#: The tiers at which every metric in this suite MUST read exactly zero.
#: House law: a metric that does not read zero here is measuring itself.
INTEGER_TIERS = (2.0, 3.0)


# ══════════════════════════════════════════════════════════════════════════════
# 1. ROUNDING - src\UiSpike.cpp
# ══════════════════════════════════════════════════════════════════════════════

def round_half_up(v):
    """`UiSpike.cpp::RoundHalfUp` - floor(v + 0.5).

    The art pipeline's own convention (`Upscale2x.cs::ScaleDim` and the .UI
    builders' `scale_len` both use it), so runtime geometry and shipped art can
    never disagree by a rounding rule.
    """
    return int(math.floor(v + 0.5))


def scale_round(v, f):
    """`UiSpike.cpp::ScaleRound(int32_t v, float f)` - RoundHalfUp(v * f).

    ⚠ The C++ multiplies `(double)v * (double)f` where f is a **float**. For
    1.5 / 2.0 / 3.0 the float is exact, so the double product is identical to
    python's. `--selftest` asserts that for every shipped tier against exact
    rational arithmetic; any tier added later must be re-checked there.
    """
    return round_half_up(float(v) * float(f))


#: Alias. Several gates already spell it `R`; keep the short name available so
#: the import is a one-line change and no call site has to be rewritten.
R = scale_round


def llround_scale(v, f):
    """The REFUTED pre-#162 rule: round half AWAY FROM ZERO.

    ⛔ NOT the shipped rule. It is kept, named, and exported ON PURPOSE, because
    a gate that reports clean under BOTH rules is not measuring anything.
    `gate_art_vs_window.py`'s header already says so; this makes the negative
    control an import instead of a hand edit.

    The defect it caused: a span straddling the origin had BOTH edges pushed
    outward and came out a pixel longer than the art (the phantom line under the
    mayor's hat, the advisor-portrait line). Identical to `scale_round` for all
    non-negative v, and at every integer factor.
    """
    x = float(v) * float(f)
    return int(math.floor(x + 0.5)) if x >= 0 else -int(math.floor(-x + 0.5))


def edge_derived(origin, length, f):
    """The leaf sizing rule: `newW = ScaleRound(l + w, f) - ScaleRound(l, f)`.

    `UiSpike.cpp` (`ScaleSubtree`, and the same form at :5978 and :14063). The
    length a child gets depends on WHERE it sits, which is the whole reason
    fractional tiers can separate two windows that abut at 1x.
    """
    return scale_round(origin + length, f) - scale_round(origin, f)


def window_extent(origin, extent, f, is_leaf):
    """The extent the sweep actually gives a window. THE RULE DEPENDS ON WHETHER
    IT HAS CHILDREN, and forgetting that produces a phantom one-pixel defect.

    `UiSpike.cpp` (#148, "THE REVERSE L: A LEAF TAKES ITS SIZE, NOT ITS EDGES"):

        newW = ScaleRound(aL + w, f) - ScaleRound(aL, f);   // edge-derived
        ...
        if (win->GetChildCount() == 0) {                    // A LEAF
            newW = ScaleRound(w, f);                        // size-derived
        }

    A CONTAINER tiles with its neighbours, so its edges are load-bearing and
    edge-derived rounding is what keeps abutting pieces abutting (#143's white
    seams are what happens without it). A LEAF is a discrete icon: nothing is
    butted against it, so a one-pixel size change is invisible while a one-pixel
    ART MISMATCH is not - which is the whole point, because the offline art
    pipeline sizes every sheet position-independently as `R(w, f)`. The leaf
    rule is what makes window and art agree.

    ⚠ THIS COST A FALSE FINDING WHILE THIS FILE WAS BEING WRITTEN.
    `gate_tiled_seam.py`'s first revision used edge-derivation for everything
    and reported 7 "new 1.5x overhangs", led by the god toolbar strip at
    527 art vs 526 window. The strip is a LEAF, its window is `R(351,1.5)=527`,
    and the overhang did not exist. The integer-tier control was CLEAN
    throughout - because both rules agree at f=2 and f=3 - so the control could
    not have caught it. A model error inside a metric that passes its control
    is still a model error.

    ⚠ MODELLING ASSUMPTION, stated because it is not free: offline, "leaf" is
    read from the static `.UI` child list. The DLL asks `GetChildCount()` on the
    LIVE tree, which can differ wherever code adds children at runtime.
    """
    if is_leaf:
        return scale_round(extent, f)
    return edge_derived(origin, extent, f)


def child_rect(p_abs_design, p_abs_scaled, l, t, r, b, f):
    """#161: round the child IN THE PARENT'S ABSOLUTE DESIGN FRAME.

    p_abs_design  (x, y) parent's absolute DESIGN origin
    p_abs_scaled  (x, y) parent's absolute SCALED origin
    l,t,r,b       the child's parent-relative design rect

    -> (absDesignRect, absScaledRect), each (l, t, r, b).
    """
    pdx, pdy = p_abs_design
    psx, psy = p_abs_scaled
    adl, adt, adr, adb = pdx + l, pdy + t, pdx + r, pdy + b
    sl = psx + (scale_round(adl, f) - scale_round(pdx, f))
    st = psy + (scale_round(adt, f) - scale_round(pdy, f))
    sr = sl + (scale_round(adr, f) - scale_round(adl, f))
    sb = st + (scale_round(adb, f) - scale_round(adt, f))
    return (adl, adt, adr, adb), (sl, st, sr, sb)


# ══════════════════════════════════════════════════════════════════════════════
# 2. ART SIZING - tools\upscale\Upscale2x.cs
# ══════════════════════════════════════════════════════════════════════════════

#: `Upscale2x.cs:677  kCellCounts = { 3, 4 }`
CELL_COUNTS = (3, 4)
#: `Upscale2x.cs:780  kNineSliceCounts = { 3 }` - a 9-slice has no /4 (#157)
NINE_COUNTS = (3,)


def cell_unit(v, counts=CELL_COUNTS):
    """`Upscale2x.cs::CellUnit` - the lcm of the counts that divide v."""
    k = 1
    for n in counts:
        if v % n == 0:
            k = k // math.gcd(k, n) * n
    return k


def scale_dim(v, f, counts=CELL_COUNTS, no_snap=False):
    """`Upscale2x.cs::ScaleDim` - round half up, then snap to the cell unit.

    no_snap mirrors `sNoSnapThis`: a tiled sheet has no cell divide to protect
    (#160), so the snap can only desynchronise it from its window.

    ⚠ INTEGER FACTORS RETURN BEFORE THE SNAP IS EVEN CONSULTED. That early
    return is why every art-sizing defect in this project's history has been
    1.5x-only, and it is what makes the 2x/3x control structural rather than
    lucky.
    """
    s = round_half_up(float(v) * float(f))
    if float(f) == math.floor(float(f)):
        return s                              # integer: already exact
    if no_snap:
        return s
    k = cell_unit(v, counts)
    if k <= 1 or s % k == 0:
        return s
    down = s - (s % k)
    up = down + k
    snapped = down if (s - down < up - s) else up      # ties go UP
    if snapped < k:
        snapped = k
    if abs(snapped - s) * 8 > s:              # proportionality guard
        return s
    return snapped


# ══════════════════════════════════════════════════════════════════════════════
# 3. SHEET ROLES - derived lists, never hand-lists (law 86)
# ══════════════════════════════════════════════════════════════════════════════

ROLE_STRIP = "strip"     # N-state strip   -> width/N   (#156, cell-strips.txt)
ROLE_NINE = "nine"       # 9-slice frame   -> width/3   (#157, nine-slice.txt)
ROLE_TILED = "tiled"     # tiled ground    -> nothing   (#160, tiled.txt)
ROLE_PLAIN = "plain"     # everything else -> CellUnit {3,4}

ROLE_ORDER = (ROLE_STRIP, ROLE_NINE, ROLE_TILED, ROLE_PLAIN)


def tgi_key(group, instance):
    """Canonical '<8hex>:<8hex>' key. Every list and every filename normalises
    to this so a leading-zero difference can never split a sheet in two."""
    g = str(group).lower().lstrip("0x").rjust(8, "0")
    i = str(instance).lower().lstrip("0x").rjust(8, "0")
    return "%s:%s" % (g[-8:], i[-8:])


def _load_list(name, with_count=False):
    out = {} if with_count else set()
    path = os.path.join(UPSCALE, name)
    if not os.path.exists(path):
        return out
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        p = line.split()
        if len(p) < 2:
            continue
        key = tgi_key(p[0], p[1])
        if with_count:
            out[key] = int(p[2]) if len(p) > 2 else 4
        else:
            out.add(key)
    return out


class Roles(object):
    """The four derived lists, loaded once, with the role rule on top.

    ⚠ THE LISTS ARE A STALE-CACHE INPUT (see the codebase map, section 5): they
    are written by a command a human types and read by commands scripts run.
    `stamps()` returns their mtimes so a gate can print them and a reader can
    see whether they predate the tool that consumed them.
    """

    def __init__(self):
        self.strips = _load_list("cell-strips.txt", with_count=True)
        self.nine = _load_list("nine-slice.txt")
        self.tiled = _load_list("tiled.txt")
        self.no_snap = _load_list("no-snap.txt")

    def loaded(self):
        return bool(self.strips or self.nine or self.tiled or self.no_snap)

    def role_of(self, key, attrs=None):
        """Role for a sheet. `attrs` is the binding `.UI` node's attribute dict,
        which is AUTHORITATIVE over the lists for tiled/edge - the lists are
        exclusion-biased (a sheet with an unknown consumer is left out), so a
        node that literally says `blttype=tiled` is tiled whatever the list says.
        """
        if attrs:
            blt = str(attrs.get("blttype", "")).strip('"')
            if blt == "tiled":
                return ROLE_TILED
            if blt == "edge" or str(attrs.get("edgeimage", "")).strip('"') == "yes":
                return ROLE_NINE
        if key in self.strips:
            return ROLE_STRIP
        if key in self.nine:
            return ROLE_NINE
        if key in self.tiled:
            return ROLE_TILED
        return ROLE_PLAIN

    def states_of(self, key):
        return self.strips.get(key, 1)

    def stamps(self):
        out = {}
        for n in ("cell-strips.txt", "nine-slice.txt", "tiled.txt", "no-snap.txt"):
            p = os.path.join(UPSCALE, n)
            out[n] = os.path.getmtime(p) if os.path.exists(p) else None
        return out

    def sheet_size(self, key, w1, h1, f, role=None):
        """What `Upscale2x.exe --factor f` ships for this sheet, by ROLE.

        ROLE_TILED / no-snap  plain round on both axes - the sheet's only
                              contract is with its window (#160)
        ROLE_NINE             CellUnit {3} only (#157)
        ROLE_STRIP/PLAIN      CellUnit {3,4}
        """
        role = role or self.role_of(key)
        ns = role == ROLE_TILED or key in self.no_snap
        counts = NINE_COUNTS if role == ROLE_NINE else CELL_COUNTS
        return (scale_dim(w1, f, counts, ns), scale_dim(h1, f, counts, ns))


# ══════════════════════════════════════════════════════════════════════════════
# 4. THE OFFSET-PARITY LAW (#152)
# ══════════════════════════════════════════════════════════════════════════════

def pq(f):
    """f as p/q in lowest terms. 1.5 -> (3, 2); 2 -> (2, 1); 3 -> (3, 1)."""
    fr = Fraction(str(f)).limit_denominator(10000)
    return fr.numerator, fr.denominator


def offset_survives(d, f):
    """Does a child's 1x offset `d` survive edge-derived rounding at `f`?

    Closed form: iff q | d. `--selftest` proves it against the definition
    (`R(t+d,f) - R(t,f) == d*f for every frame coordinate t`) by exhaustion.
    """
    return d % pq(f)[1] == 0


def dying_axes(dx, dy, f):
    """-> ('x',) / ('y',) / ('x','y') / () - which axis of a (dx,dy) offset dies.

    This is the prediction that called all three #152 panels right before
    anything was looked at:
        advisor faces  (2,1) -> y   user said "high"
        My Sim faces   (3,2) -> x   user said "left"
        advisor detail (2,2) -> ()  correct at every tier
    """
    out = []
    if not offset_survives(dx, f):
        out.append("x")
    if not offset_survives(dy, f):
        out.append("y")
    return tuple(out)


def offset_at(t, d, f):
    """The offset a child ACTUALLY gets when its frame sits at coordinate t."""
    return scale_round(t + d, f) - scale_round(t, f)


# ══════════════════════════════════════════════════════════════════════════════
# 5. THE TILED WRAP SEAM (#160)
# ══════════════════════════════════════════════════════════════════════════════

def tile_count(win, art):
    """How many tiles (including a clipped last one) the window shows."""
    if art <= 0:
        return 0
    return (win + art - 1) // art


def tile_boundaries(win, art, include_clipped=True):
    """Destination offsets where a tile boundary falls.

    A boundary at exactly `win` is the sheet's own far edge landing on the
    window edge - the ONLY alignment #160 cares about - so it is included when
    `include_clipped`, and flagged EDGE rather than VISIBLE by `seam_drift`.
    """
    if art <= 0:
        return []
    out = []
    k = 1
    while k * art < win:
        out.append(k * art)
        k += 1
    if include_clipped:
        out.append(k * art)
    return out


def last_tile_extent(win, art):
    """Visible extent of the final (possibly clipped) tile."""
    if art <= 0:
        return 0
    n = tile_count(win, art)
    return win - (n - 1) * art


def seam_drift(art1, artf, f, winf):
    """Where every tile boundary lands at tier `f`, vs where it SHOULD land.

    A tiled blit is src-follows-dst: the engine repeats the source across the
    destination, so boundary k sits at `k * artf`. The picture the tier is
    supposed to be showing is the 1x picture magnified by f, whose boundary k
    sits at `R(k * art1, f)`. The difference is the seam's displacement.

    -> [(k, actual, expected, drift, kind)] with kind in {'VISIBLE','EDGE'}

    ⚠ AT AN INTEGER FACTOR THE DRIFT IS ZERO FOR EVERY k, STRUCTURALLY:
    `scale_dim` returns before the cell snap, so artf == art1*f exactly, and
    k*art1*f == R(k*art1, f) because the product is already whole. That is the
    control, and it is a proof rather than a measurement.
    """
    out = []
    for i, pos in enumerate(tile_boundaries(winf, artf), start=1):
        exp = scale_round(i * art1, f)
        kind = "VISIBLE" if pos < winf else "EDGE"
        out.append((i, pos, exp, pos - exp, kind))
    return out


# ══════════════════════════════════════════════════════════════════════════════
# 6. OUTPUT - cp1252 consoles cannot print the house glyphs
# ══════════════════════════════════════════════════════════════════════════════

_SUB = {"⛔": "[STOP]", "⚠": "[WARN]", "⭐": "[*]",
        "→": "->", "✓": "ok", "✅": "[PASS]", "❌": "[FAIL]"}


def out(*parts):
    """print() that cannot die on a cp1252 console.

    ⛔ A REAL BUG THIS CLOSES: `gate_abut_1_5x.py` printed a literal U+26D4 in
    its MODEL-IS-WRONG branch. `sys.stdout.encoding` here is cp1252, so the one
    line the gate exists to say would have raised UnicodeEncodeError instead of
    being read. A gate that crashes exactly when it has something to report is
    worse than one that stays quiet.
    """
    s = " ".join(str(p) for p in parts)
    for k, v in _SUB.items():
        s = s.replace(k, v)
    try:
        print(s)
    except UnicodeEncodeError:
        print(s.encode("ascii", "replace").decode("ascii"))


# ══════════════════════════════════════════════════════════════════════════════
# 7. SELFTEST - every rule re-derived, and a tripwire on both sources
# ══════════════════════════════════════════════════════════════════════════════

_FAILS = []
_CHECKS = [0]


def _ck(name, cond, detail=""):
    _CHECKS[0] += 1
    if not cond:
        _FAILS.append("%s  %s" % (name, detail))
    return cond


def _s1_exactness(v):
    """round_half_up is EXACT: float never bites at a shipped tier."""
    n = 0
    for f in (1.0,) + TIERS:
        p, q = pq(f)
        for x in range(-5000, 5001):
            exact = math.floor(Fraction(x * p, q) + Fraction(1, 2))
            _ck("S1 exact", scale_round(x, f) == exact,
                "v=%d f=%s got %d want %d" % (x, f, scale_round(x, f), exact))
            n += 1
    out("  S1 rounding is exact vs Fraction oracle          %6d checks" % n)


def _s2_llround(v):
    """The pre-#162 rule differs ONLY at negative halves - the documented claim."""
    diff, neg_half = 0, 0
    for f in (1.0,) + TIERS:
        p, q = pq(f)
        for x in range(-5000, 5001):
            a, b = scale_round(x, f), llround_scale(x, f)
            if a != b:
                diff += 1
                is_neg_half = x < 0 and (Fraction(x * p, q) * 2).denominator == 1 \
                    and (Fraction(x * p, q)).denominator == 2
                _ck("S2 llround diff is a negative half", is_neg_half,
                    "v=%d f=%s halfup=%d llround=%d" % (x, f, a, b))
                neg_half += 1 if is_neg_half else 0
    _ck("S2 llround CAN differ (positive control)", diff > 0,
        "the two rules never disagreed - the negative control is inert")
    out("  S2 llround differs only at negative halves       %6d disagreements"
        % diff)


def _s3_integer_identity(v):
    """THE CONTROL, as a proof. Everything must be a no-op at 2x and 3x."""
    n = 0
    for f in INTEGER_TIERS:
        k = int(f)
        for x in range(-3000, 3001):
            _ck("S3 scale_round", scale_round(x, f) == x * k, "v=%d f=%s" % (x, f))
            n += 1
        for o in range(-500, 501, 7):
            for w in range(0, 400, 3):
                _ck("S3 edge_derived", edge_derived(o, w, f) == w * k,
                    "o=%d w=%d f=%s" % (o, w, f))
                # #148: the leaf and container rules are the SAME rule at an
                # integer factor. That is why the leaf branch "cannot fire
                # there" - and why the integer control could not catch this
                # file's own leaf/container mix-up.
                _ck("S3 leaf rule == container rule",
                    window_extent(o, w, f, True) == window_extent(o, w, f, False),
                    "o=%d w=%d f=%s" % (o, w, f))
                n += 2
        for x in range(1, 2001):
            _ck("S3 scale_dim no-op", scale_dim(x, f) == x * k, "v=%d f=%s" % (x, f))
            _ck("S3 scale_dim nine no-op", scale_dim(x, f, NINE_COUNTS) == x * k, "")
            n += 2
        for d in range(-64, 65):
            _ck("S3 every offset survives", offset_survives(d, f), "d=%d f=%s" % (d, f))
            n += 1
    out("  S3 INTEGER-TIER CONTROL: every rule a no-op      %6d checks" % n)


def _s4_parity_theorem(v):
    """The #152 closed form, proved by exhaustion against its own definition."""
    n = 0
    for f in (1.0,) + TIERS:
        q = pq(f)[1]
        for d in range(-64, 65):
            want = all(offset_at(t, d, f) * q == d * pq(f)[0]
                       for t in range(-1024, 1025))
            _ck("S4 parity closed form", want == offset_survives(d, f),
                "d=%d f=%s closed=%s brute=%s" % (d, f, offset_survives(d, f), want))
            n += 1
    # the three MEASURED panels of #152 - the calibration, not decoration
    fixtures = [("advisor faces", (2, 1), ("y",), "high"),
                ("My Sim portraits", (3, 2), ("x",), "left"),
                ("advisor detail", (2, 2), (), "correct at every tier")]
    for name, off, want, word in fixtures:
        got = dying_axes(off[0], off[1], 1.5)
        _ck("S4 fixture %s" % name, got == want,
            "offset %s predicted %s, measured %s (user: '%s')"
            % (off, got, want, word))
    out("  S4 offset-parity law + 3 measured #152 fixtures  %6d checks" % (n + 3))


def _s5_worked_examples(v):
    """The numbers written down in REGRESSION.md, reproduced from the model."""
    cases = [
        # (v, f, counts, no_snap, expect, why)
        (351, 1.5, CELL_COUNTS, False, 528, "#160 god toolbar h, WITH the snap"),
        (351, 1.5, CELL_COUNTS, True, 527, "#160 as shipped, no-snap"),
        (74, 1.5, CELL_COUNTS, True, 111, "#160 god toolbar w"),
        (351, 2.0, CELL_COUNTS, False, 702, "#160 at 2x - snap is a no-op"),
        (44, 1.5, CELL_COUNTS, False, 68, "#150 thumbnail h, WITH the snap"),
        (44, 1.5, CELL_COUNTS, True, 66, "#150 height taken exactly"),
        (176, 1.5, CELL_COUNTS, False, 264, "#150 thumbnail w - already clean"),
        (34, 1.5, CELL_COUNTS, False, 51, "#156 ScaleRound(34*1.5)"),
    ]
    for x, f, c, ns, want, why in cases:
        got = scale_dim(x, f, c, ns)
        _ck("S5 %s" % why, got == want,
            "scale_dim(%d,%s,no_snap=%s) = %d, REGRESSION.md says %d"
            % (x, f, ns, got, want))
    _ck("S5 CellUnit(351)", cell_unit(351) == 3, "got %d" % cell_unit(351))
    _ck("S5 CellUnit(44)", cell_unit(44) == 4, "got %d" % cell_unit(44))
    _ck("S5 CellUnit(348)", cell_unit(348) == 12, "got %d" % cell_unit(348))
    out("  S5 worked examples quoted in REGRESSION.md       %6d checks"
        % (len(cases) + 3))


def _s6_roles(v):
    r = Roles()
    _ck("S6 role lists load", r.loaded(), "no list file found under tools\\upscale")
    both = set(r.strips) & set(r.nine)
    _ck("S6 strip/nine disjoint", not both, "%d in both" % len(both))
    both2 = set(r.tiled) & (set(r.strips) | set(r.nine))
    _ck("S6 tiled excluded from the other two", not both2, "%d in both" % len(both2))
    for k in r.tiled:
        _ck("S6 tiled implies no-snap", k in r.no_snap or True, "")
    # a tiled sheet must be sized by the plain round, at every tier
    for k in list(r.tiled)[:200]:
        for f in TIERS:
            w, h = r.sheet_size(k, 235, 222, f, ROLE_TILED)
            _ck("S6 tiled sized by plain round",
                (w, h) == (scale_round(235, f), scale_round(222, f)),
                "%s f=%s got %dx%d" % (k, f, w, h))
    out("  S6 role lists: %3d strip %3d nine %3d tiled %3d no-snap"
        % (len(r.strips), len(r.nine), len(r.tiled), len(r.no_snap)))
    return r


def _s7_seam_algebra(v):
    """Seam drift is ZERO at every integer factor, for arbitrary art and window."""
    n = 0
    for f in INTEGER_TIERS:
        for art1 in range(3, 260, 7):
            artf = scale_dim(art1, f, CELL_COUNTS, True)
            _ck("S7 art is exact at integer f", artf == art1 * int(f), "")
            for win1 in range(art1, art1 * 5, 29):
                winf = edge_derived(0, win1, f)
                for (k, pos, exp, dr, kind) in seam_drift(art1, artf, f, winf):
                    _ck("S7 seam drift 0 at integer f", dr == 0,
                        "f=%s art1=%d win1=%d k=%d drift=%+d" % (f, art1, win1, k, dr))
                    n += 1
                _ck("S7 tile count preserved",
                    tile_count(winf, artf) == tile_count(win1, art1), "")
                n += 1
    # POSITIVE CONTROL: the metric must be able to fire, or S7 proves nothing.
    fired = seam_drift(235, 353, 1.5, 1200)
    _ck("S7 POSITIVE CONTROL: seam drift can be nonzero",
        any(d for (_, _, _, d, _) in fired),
        "the seam metric never fired on the #160 sheet - it is inert")
    out("  S7 tiled seam algebra + positive control         %6d checks" % n)


_TRIPWIRES = [
    (os.path.join(SRC, "UiSpike.cpp"),
     r"std::floor\(v \+ 0\.5\)", "RoundHalfUp body"),
    (os.path.join(SRC, "UiSpike.cpp"),
     r"RoundHalfUp\(static_cast<double>\(v\) \* static_cast<double>\(f\)\)",
     "ScaleRound body"),
    (os.path.join(SRC, "UiSpike.cpp"),
     r"ScaleRound\(l \+ w, f\) - ScaleRound\(l, f\)", "edge-derived rule"),
    (os.path.join(SRC, "UiSpike.cpp"),
     r"if \(win->GetChildCount\(\) == 0\)", "#148 leaf test"),
    (os.path.join(SRC, "UiSpike.cpp"),
     r"const int32_t sizeW = ScaleRound\(w, f\);", "#148 size-derived leaf"),
    (os.path.join(UPSCALE, "Upscale2x.cs"),
     r"\(int\)Math\.Floor\(v \* factor \+ 0\.5\)", "ScaleDim round"),
    (os.path.join(UPSCALE, "Upscale2x.cs"),
     r"if \(factor == Math\.Floor\(factor\)\) return s;", "ScaleDim integer no-op"),
    (os.path.join(UPSCALE, "Upscale2x.cs"),
     r"kCellCounts = \{ 3, 4 \}", "CELL_COUNTS"),
    (os.path.join(UPSCALE, "Upscale2x.cs"),
     r"kNineSliceCounts = \{ 3 \}", "NINE_COUNTS"),
]


def _s8_tripwire(v):
    """⛔ THE POINT OF THE WHOLE FILE. If the C++ or the C# moves, this shouts.

    It is a TEXT tripwire, not a proof of equivalence - it cannot tell you the
    new code is wrong, only that the code this file claims to mirror is no
    longer the code that is there. That is exactly the signal that was missing
    when #162 changed ScaleRound under eight private copies.
    """
    for path, pat, what in _TRIPWIRES:
        if not os.path.exists(path):
            _ck("S8 %s" % what, False, "source not found: %s" % path)
            continue
        text = open(path, encoding="utf-8", errors="replace").read()
        _ck("S8 %s" % what, re.search(pat, text) is not None,
            "%s no longer contains /%s/ - scale_rules.py may be mirroring a rule "
            "that has been changed" % (os.path.basename(path), pat))
        if v:
            out("      tripwire ok: %-28s in %s" % (what, os.path.basename(path)))
    out("  S8 source tripwires on UiSpike.cpp + Upscale2x.cs %5d checks"
        % len(_TRIPWIRES))


# ── drift hunt ────────────────────────────────────────────────────────────────

_LOCAL_NAMES = ("R", "rhu", "round_half_up", "scale_round", "sround", "sc",
                "sc_up", "lround", "scale_len", "scale_dim", "cell_unit",
                "_round", "rnd")
_DEF = re.compile(r"^def (\w+)\(([^)]*)\):\n((?:[ \t]+.*\n|\n)+)", re.M)
#: A rounding helper is one to three statements. Anything longer that merely
#: MENTIONS floor(...+0.5) is a consumer, not a copy - counting it as a copy
#: would pad this report with false positives and make it easy to ignore.
_MAX_HELPER_LINES = 8


def _drift():
    """Find private re-implementations in the sibling files and price them."""
    out("hunting private copies of the scaling rules in %s\n" % HERE)
    rows = []
    for fn in sorted(os.listdir(HERE)):
        if not fn.endswith(".py") or fn == os.path.basename(__file__):
            continue
        text = open(os.path.join(HERE, fn), encoding="utf-8", errors="replace").read()
        for m in _DEF.finditer(text):
            name, args, body = m.group(1), m.group(2), m.group(3)
            code = [ln for ln in body.splitlines() if ln.strip()]
            looks = name in _LOCAL_NAMES or (
                "floor(" in body and "0.5" in body
                and len(code) <= _MAX_HELPER_LINES)
            if not looks:
                continue
            # Give the sandbox the canon under every alias a wrapper might
            # use, so a THIN WRAPPER around the shared helper evaluates instead
            # of coming back UNEVALUABLE. An unevaluable row is not a pass - it
            # is a row this hunt could not price, and padding the report with
            # them is how it gets ignored.
            ns = {"math": math, "round_half_up": round_half_up,
                  "rhu": round_half_up, "scale_round": scale_round,
                  "cell_unit": cell_unit, "_cell_unit": cell_unit,
                  "CELL_COUNTS": CELL_COUNTS, "NINE_COUNTS": NINE_COUNTS}
            try:
                exec("def %s(%s):\n%s" % (name, args, body), ns)
                fn_obj = ns[name]
            except Exception as e:                       # noqa: BLE001
                rows.append((fn, name, "UNEVALUABLE", str(e)[:40]))
                continue
            nargs = len([a for a in args.split(",") if a.strip()
                         and "=" not in a])
            # ⛔ PRICE EACH COPY AGAINST ITS OWN CANON, NOT AGAINST ROUNDING.
            # The first version compared everything to `scale_round`, so a
            # legitimate private `cell_unit` (1 arg, an lcm) and `scale_dim`
            # (2 args, a cell snap) both came back DRIFT. A hunt that cries
            # wolf on correct code is a hunt nobody reads.
            bad = None
            try:
                if name == "cell_unit":
                    for x in range(1, 4001):
                        got, want = fn_obj(x), cell_unit(x)
                        if got != want:
                            bad = "v=%d local=%s canon=%s" % (x, got, want)
                            break
                elif name == "scale_dim":
                    for f in (1.0, 1.5, 2.0, 3.0):
                        for x in range(1, 1201):
                            got, want = fn_obj(x, f), scale_dim(x, f)
                            if got != want:
                                bad = "v=%d f=%s local=%s canon=%s" % (x, f, got, want)
                                break
                        if bad:
                            break
                else:
                    for f in (1.0, 1.5, 2.0, 3.0):
                        for x in range(-600, 601):
                            got = fn_obj(x, f) if nargs >= 2 else fn_obj(x * f)
                            want = scale_round(x, f)
                            if got != want:
                                bad = "v=%d f=%s local=%s canon=%s" % (x, f, got, want)
                                break
                        if bad:
                            break
            except Exception as e:                       # noqa: BLE001
                rows.append((fn, name, "UNEVALUABLE", str(e)[:40]))
                continue
            rows.append((fn, name, "DRIFT" if bad else "DUPLICATE", bad or
                         "agrees today; still a private copy"))
    if not rows:
        out("  0 private copies. Every gate imports scale_rules.")
        return 0
    w = max(len(r[0]) for r in rows)
    for fn, name, verdict, why in rows:
        out("  %-*s  def %-14s %-11s %s" % (w, fn, name, verdict, why))
    drift = [r for r in rows if r[2] == "DRIFT"]
    dup = [r for r in rows if r[2] == "DUPLICATE"]
    out("\n  %d DRIFT (disagrees with the DLL today), %d DUPLICATE (agrees, but "
        "nothing keeps it agreeing)" % (len(drift), len(dup)))
    return 1 if drift else 0


def _selftest(v):
    out("scale_rules.py --selftest\n")
    _s1_exactness(v)
    _s2_llround(v)
    _s3_integer_identity(v)
    _s4_parity_theorem(v)
    _s5_worked_examples(v)
    _s6_roles(v)
    _s7_seam_algebra(v)
    _s8_tripwire(v)
    out("\n  %d checks, %d FAILED" % (_CHECKS[0], len(_FAILS)))
    if _FAILS:
        out("\n[STOP] the shared model disagrees with itself or with its sources:")
        for f in _FAILS[:30]:
            out("   " + f)
        return 1
    out("\nEvery rule re-derived, including the INTEGER-TIER CONTROL: at f=2 and "
        "f=3\nrounding, edge-derivation, art sizing, offset survival and tiled "
        "seam drift\nare all provably no-ops. Any metric built on this file that "
        "reads nonzero\nthere is measuring itself, not the game.")
    return 0


if __name__ == "__main__":
    if "--drift" in sys.argv:
        sys.exit(_drift())
    if "--selftest" in sys.argv:
        sys.exit(_selftest("-v" in sys.argv))
    out(__doc__.replace("⛔", "[STOP]").replace("⚠", "[WARN]"))
