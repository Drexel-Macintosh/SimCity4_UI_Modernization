#!/usr/bin/env python
r"""Gate (register #7): DO THE TWO `ScaleDim`/`CellUnit` COPIES AGREE?

THE TWO COPIES, AND WHY THERE ARE TWO
--------------------------------------
  offline art pipeline   tools\upscale\Upscale2x.cs   ScaleDim / CellUnit
                          - sizes every shipped PNG, incl. the NamIcons
                          override packages (rebuild_namicons.py).
  runtime ICONSYNTH       src\ScaleTier.cpp:1298 CellUnit, :1309 ScaleDim
                          - enlarges THIRD-PARTY ItemIcon strips live at
                          boot, for TGIs {type 0x856DDBAC, group
                          0x6A386D26} our own shipped packages do not
                          cover (ScaleTier.cpp:1656 `k.type != kIconType
                          || k.group != kIconGroup`, the ONLY domain this
                          runtime function is ever called on - grep
                          confirms exactly the two call sites at :1675 and
                          :1801, both height-only).

SC4-UI-ENGINE.md Sec.4.6c.1 already names the risk: "The runtime copy has
no equivalent of sNineSliceOnly / sNoSnapThis / sNoHeightSnap." This gate
turns that into a measurement over the REAL corpus the runtime path
actually touches: `tools\itemicons\nam-1x`, 392 real 1x ItemIcon PNGs of
exactly {0x856DDBAC, 0x6A386D26} scanned from an installed NAM.

MEASURED ANSWER: THEY HAVE DRIFTED. `--height-exact-group 6A386D26`
(rebuild_namicons.py:43, the actual invocation that builds the shipped
NamIcons dats) is precisely `sNoHeightSnap` for this group - the fix for
bug #150 (the disaster flyout thumbnails). The runtime `ScaleDim` has NO
such mode; it always CellUnit-snaps. Over the real 392-file corpus at
f=1.5: 122 sheets (all 176x44, the #150 shape) get height 66 offline and
68 at runtime - a live, reproducible +2px disagreement, not a hypothetical
one. WIDTH agrees on all 392 (CellUnit{3,4}'s lcm is always a multiple of
4, so the two width formulas coincide here - see S5 below for why that is
not a coincidence worth relying on elsewhere).

HOUSE CONTROLS THIS GATE ALSO PROVES
-------------------------------------
  S1  CellUnit(v) agrees for every v, unconditionally (same algorithm).
  S2  ScaleDim(v,f) agrees in the UNMODED case (no snap override) - the
      part of the rule the runtime copy actually implements.
  S3  INTEGER-TIER CONTROL: both copies are a byte-exact no-op at f=2,3.
  S4  STRUCTURAL: Upscale2x.cs HAS the role-scoping fields; ScaleTier.cpp's
      ScaleDim has exactly one 2-argument overload and none of them. Text
      tripwires, not a semantic proof - if either file's shape moves, this
      gate says so rather than silently mirroring stale code (the #162
      failure mode scale_rules.py's own header describes).
  S5  THE ICON DOMAIN: real corpus in, worked answer out (see above).

WHY THIS GATE IS EXPECTED TO BE RED TODAY. S5's height check fails BY
DESIGN: it is reporting a real, currently-shipping disagreement, not a
bug in the gate. Making it pass by loosening the assertion would be the
exact "known residual == not a defect" mistake this project's own laws
name. The fix (port an equivalent of sNoHeightSnap into ScaleTier.cpp's
ScaleDim for group 0x6A386D26, or decide the 2px is acceptable) is an
engineering decision for a human/orchestrator, not this gate's job.

    python _tests\Test-ScaleDimParity.py [-v]

Exit 0 = every check agrees (would mean the drift above has been fixed).
Exit 1 = at least one FAIL - read the printed list.
Exit 2 = SKIP - tools\itemicons\nam-1x is missing (run
         scan_thirdparty_icons.py against an installed NAM first); every
         non-corpus check (S1-S4) still runs and can still fail on its
         own.
"""
import math
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
UPSCALE_CS = os.path.join(REPO, "tools", "upscale", "Upscale2x.cs")
SCALETIER_CPP = os.path.join(REPO, "src", "ScaleTier.cpp")
NAM_1X = os.path.join(REPO, "tools", "itemicons", "nam-1x")
EMU = os.path.join(REPO, "tools", "uimap", "emu")
if EMU not in sys.path:
    sys.path.insert(0, EMU)

# ONE SOURCE FOR THE OFFLINE MODEL (scale_rules.py already mirrors
# Upscale2x.cs's CellUnit/ScaleDim, tripwired against that same source
# text). Reusing it here rather than writing a third private copy is the
# whole point of that file's existence.
import scale_rules as sr  # noqa: E402

ICON_TYPE = 0x856DDBAC     # ScaleTier.cpp:1656 kIconType - runtime's ONLY domain
ICON_GROUP = 0x6A386D26    # ScaleTier.cpp:1656 kIconGroup == rebuild_namicons.py's
                            # "--height-exact-group 6A386D26"

_FAILS = []
_CHECKS = [0]


def check(cond, msg):
    _CHECKS[0] += 1
    print(("   ok   " if cond else "   FAIL ") + msg)
    if not cond:
        _FAILS.append(msg)
    return cond


def section(title):
    print("\n" + title)


# ══════════════════════════════════════════════════════════════════════════
# THE RUNTIME COPY, PORTED HERE FOR COMPARISON (src\ScaleTier.cpp:1270-1323).
# Every line below is a direct transliteration; the tripwires in S4 assert
# the C++ text this was transliterated FROM still reads the way this port
# assumes.
# ══════════════════════════════════════════════════════════════════════════
RUNTIME_CELL_COUNTS = (3, 4)   # ScaleTier.cpp:1294  kCellCounts[] = { 3, 4 }


def runtime_cell_unit(v):
    """ScaleTier.cpp:1298 CellUnit(int v). Identical lcm algorithm to the
    offline copy, with NO role parameter - this is the only table the
    runtime function has ever seen."""
    k = 1
    for n in RUNTIME_CELL_COUNTS:
        if v % n == 0:
            k = k // math.gcd(k, n) * n
    return k


def runtime_round_half_up(v):
    """ScaleTier.cpp:1270 RoundHalfUp(float v) -> static_cast<int>(v+0.5f).

    That is a TRUNCATING cast, not floor(). For every v this project ever
    calls it with (v = dim*factor, dim >= 0, factor >= 1) the argument is
    non-negative, where truncation and floor agree - so modelling it as
    floor here is exact, not an approximation. float(32-bit) vs Python's
    double: 1.5/2.0/3.0 are exactly representable in both, and v*factor
    stays under 2**23 for every dimension this corpus contains, so no
    precision gap opens between the two widths either.
    """
    return int(math.floor(v + 0.5))


def runtime_scale_dim(v, factor):
    """ScaleTier.cpp:1309 ScaleDim(int v, float factor) - literal port.

    THE SIGNATURE IS THE FINDING: exactly (v, factor). No no_snap flag, no
    counts override, no stripAxis. See S4 for the structural proof that
    this is really the only overload in the file.
    """
    s = runtime_round_half_up(v * factor)
    if factor == math.floor(factor):
        return s
    k = runtime_cell_unit(v)
    if k <= 1 or s % k == 0:
        return s
    down = s - (s % k)
    up = down + k
    snapped = down if (s - down) < (up - s) else up   # ties go UP
    if snapped < k:
        snapped = k
    if abs(snapped - s) * 8 > s:                       # proportionality guard
        return s
    return snapped


def runtime_icon_width(w, factor):
    """ScaleTier.cpp:1672-1674 / :1796-1798 - the WIDTH formula actually
    used at both runtime call sites. NOT ScaleDim: a direct cell-first
    computation hard-coded to 4 states (`cell = sw/4; newCell =
    RoundHalfUp(cell*factor); newW = newCell*4`), guarded upstream on
    `sw % 4 == 0`. Ported separately from ScaleDim because the real code
    never routes width through ScaleDim/CellUnit at all.
    """
    cell = w // 4
    new_cell = runtime_round_half_up(cell * factor)
    return new_cell * 4


def offline_icon_width(w, factor):
    """rebuild_namicons.py:41-56 - the REAL invocation that builds the
    shipped NamIcons packages runs Upscale2x WITHOUT --cell-strips, so
    width takes the PLAIN ScaleDim/CellUnit path (no_snap=False, states
    never consulted), then a separate Python post-pass LANCZOS-resizes the
    result to the nearest multiple of 4 if the snap did not already land
    on one (`tw = 4*round(w/4)`). Modelled faithfully rather than assumed
    equal to the runtime formula - see S5's note on why they agree today
    without being the same rule.
    """
    ow = sr.scale_dim(w, factor, sr.CELL_COUNTS, no_snap=False)
    if ow % 4 != 0:
        ow = 4 * round(ow / 4)
    return ow


def offline_icon_height(h, factor):
    """rebuild_namicons.py:43 passes `--height-exact-group 6A386D26` - for
    this exact TGI group that is Upscale2x.cs's sNoHeightSnap (the #150
    fix), i.e. scale_dim(..., no_snap=True) on the HEIGHT axis only.
    """
    return sr.scale_dim(h, factor, sr.CELL_COUNTS, no_snap=True)


# ══════════════════════════════════════════════════════════════════════════
# S1 - CellUnit agreement, unconditional
# ══════════════════════════════════════════════════════════════════════════
def s1_cell_unit(vmax=8000):
    section("S1 - CellUnit(v) agreement, v=1..%d" % vmax)
    bad = 0
    first = None
    for v in range(1, vmax + 1):
        a, b = sr.cell_unit(v), runtime_cell_unit(v)
        if a != b:
            bad += 1
            first = first or (v, a, b)
    check(bad == 0, "CellUnit agrees for all %d values (%d disagree%s)"
          % (vmax, bad, (", first %s" % (first,)) if first else ""))


# ══════════════════════════════════════════════════════════════════════════
# S2 - ScaleDim agreement in the UNMODED case (the part the runtime
# copy actually implements: no no_snap, default counts, no stripAxis).
# ══════════════════════════════════════════════════════════════════════════
def s2_scale_dim_base(vmax=8000):
    section("S2 - ScaleDim(v,1.5) agreement, unmoded case, v=1..%d" % vmax)
    bad = 0
    first = None
    for v in range(1, vmax + 1):
        a = sr.scale_dim(v, 1.5, sr.CELL_COUNTS, no_snap=False)
        b = runtime_scale_dim(v, 1.5)
        if a != b:
            bad += 1
            first = first or (v, a, b)
    check(bad == 0, "ScaleDim(v,1.5) agrees for all %d values with no role "
          "override (%d disagree%s)"
          % (vmax, bad, (", first %s" % (first,)) if first else ""))


# ══════════════════════════════════════════════════════════════════════════
# S3 - THE INTEGER-TIER CONTROL (house law 95 / scale_rules.py S3): a
# metric that is not a provable no-op at f=2/3 is measuring itself.
# ══════════════════════════════════════════════════════════════════════════
def s3_integer_control(vmax=8000):
    section("S3 - integer-tier no-op control, f in (2.0, 3.0)")
    n = 0
    for f in (2.0, 3.0):
        k = int(f)
        bad_cu = bad_sd_off = bad_sd_rt = 0
        for v in range(1, vmax + 1):
            n += 1
            if sr.scale_dim(v, f) != v * k:
                bad_sd_off += 1
            if runtime_scale_dim(v, f) != v * k:
                bad_sd_rt += 1
        check(bad_sd_off == 0,
              "offline ScaleDim(v,%s) == v*%d for all %d values (%d wrong)"
              % (f, k, vmax, bad_sd_off))
        check(bad_sd_rt == 0,
              "runtime ScaleDim(v,%s) == v*%d for all %d values (%d wrong)"
              % (f, k, vmax, bad_sd_rt))
    print("  (%d value*rule evaluations)" % n)


# ══════════════════════════════════════════════════════════════════════════
# S4 - STRUCTURAL: prove the role-scoping gap by reading the source, not
# by asserting prose. Text tripwires only - they cannot prove either side
# is CORRECT, only that this gate is still describing the code that is
# actually there (the #162 failure scale_rules.py's header warns about).
# ══════════════════════════════════════════════════════════════════════════
_TRIPWIRES = [
    (UPSCALE_CS, r"private static bool sNineSliceOnly", "offline HAS sNineSliceOnly"),
    (UPSCALE_CS, r"private static bool sNoSnapThis", "offline HAS sNoSnapThis"),
    (UPSCALE_CS, r"private static bool sNoHeightSnap", "offline HAS sNoHeightSnap"),
    (UPSCALE_CS, r"private static int sStripStates", "offline HAS sStripStates (cell-first states)"),
    (UPSCALE_CS,
     r"private static int ScaleDim\(int v, double factor, bool stripAxis = false\)",
     "offline ScaleDim takes a stripAxis parameter"),
    (SCALETIER_CPP, r"int CellUnit\(int v\)\s*\n\s*\{", "runtime CellUnit(int v) - ONE argument, no role/counts"),
    (SCALETIER_CPP, r"int ScaleDim\(int v, float factor\)\s*\n\s*\{",
     "runtime ScaleDim(int v, float factor) - exactly TWO arguments"),
    (SCALETIER_CPP, r"const int kCellCounts\[\] = \{ 3, 4 \};", "runtime kCellCounts == {3,4} (one table, no nine-slice variant)"),
]


def s4_structural(vv=False):
    section("S4 - structural tripwires (source-text, not semantics)")
    sources = {}
    for path, pat, what in _TRIPWIRES:
        if path not in sources:
            if not os.path.isfile(path):
                sources[path] = None
            else:
                sources[path] = open(path, encoding="utf-8", errors="replace").read()
        text = sources[path]
        ok = text is not None and re.search(pat, text) is not None
        check(ok, "%s  [%s]" % (what, os.path.basename(path)))
        if vv and ok:
            print("        matched /%s/" % pat)

    # The absence checks: these features must NOT appear anywhere near
    # ScaleDim/CellUnit in ScaleTier.cpp. If one ever does, the drift this
    # gate exists to catch has been (at least partly) closed, and S5's
    # expected-red height check below should be revisited.
    if sources.get(SCALETIER_CPP):
        text = sources[SCALETIER_CPP]
        for name in ("sNoHeightSnap", "sNineSliceOnly", "sNoSnapThis", "NoHeightSnap", "HeightExact"):
            check(name not in text,
                  "runtime source has NO '%s' (confirms the missing mode - "
                  "if this ever appears, S5's height check may now be stale)"
                  % name)


# ══════════════════════════════════════════════════════════════════════════
# S5 - THE ICON DOMAIN: real corpus, real answer.
# ══════════════════════════════════════════════════════════════════════════
def _png_dims(path):
    with open(path, "rb") as f:
        b = f.read(26)
    if b[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    return struct.unpack(">II", b[16:24])


_TGI_RE = re.compile(
    r"^T-0x([0-9A-Fa-f]{8})_G-0x([0-9A-Fa-f]{8})_I-0x([0-9A-Fa-f]{8})\.png$")


def s5_icon_domain():
    section("S5 - the icon domain: real corpus vs the two ScaleDim copies, f=1.5")

    # Worked-example anchor, independent of the corpus: this is the exact
    # number pinned in scale_rules.py S5 ("#150 thumbnail h") and quoted
    # in both Upscale2x.cs's sNoHeightSnap comment and ScaleTier.cpp's #158
    # comment - the case that PROVES the two rules can disagree, corpus or
    # not.
    off_44 = offline_icon_height(44, 1.5)
    rt_44 = runtime_scale_dim(44, 1.5)
    check(off_44 == 66, "anchor: offline height-exact(44,1.5) == 66 (got %d)" % off_44)
    check(rt_44 == 68, "anchor: runtime ScaleDim(44,1.5) == 68 (got %d)" % rt_44)
    check(off_44 != rt_44,
          "POSITIVE CONTROL: the anchor case DOES disagree (66 vs 68) - "
          "if this ever reads equal, the drift may have been fixed "
          "upstream and the corpus check below should be re-evaluated")

    if not os.path.isdir(NAM_1X):
        print("\n  SKIP: %s not found." % NAM_1X)
        print("  Run tools\\itemicons\\scan_thirdparty_icons.py against an "
              "installed NAM to populate it, then re-run this gate. The "
              "anchor case above already proves the rule CAN disagree; "
              "this only measures how often it does on live data.")
        return 2

    rows = []
    bad_name = 0
    for fn in sorted(os.listdir(NAM_1X)):
        if not fn.lower().endswith(".png"):
            continue
        m = _TGI_RE.match(fn)
        if not m:
            bad_name += 1
            continue
        t, g, _inst = (int(x, 16) for x in m.groups())
        if t != ICON_TYPE or g != ICON_GROUP:
            bad_name += 1
            continue
        d = _png_dims(os.path.join(NAM_1X, fn))
        if d is None:
            bad_name += 1
            continue
        rows.append((fn, d[0], d[1]))

    check(bad_name == 0,
          "every file in nam-1x is a well-formed {%08X,%08X} PNG (%d were not)"
          % (ICON_TYPE, ICON_GROUP, bad_name))
    check(len(rows) > 0, "nam-1x has at least one usable source (%d found)" % len(rows))
    print("  %d real 1x ItemIcon sheets loaded" % len(rows))

    w_bad, h_bad = [], []
    for fn, w, h in rows:
        ow, rw = offline_icon_width(w, 1.5), runtime_icon_width(w, 1.5)
        if ow != rw:
            w_bad.append((fn, w, ow, rw))
        oh, rh = offline_icon_height(h, 1.5), runtime_scale_dim(h, 1.5)
        if oh != rh:
            h_bad.append((fn, h, oh, rh))

    check(len(w_bad) == 0,
          "WIDTH: offline pipeline (plain ScaleDim + /4 LANCZOS snap) == "
          "runtime cell-first (4*RoundHalfUp(w/4*f)) for all %d sheets "
          "(%d disagree)" % (len(rows), len(w_bad)))
    for fn, w, ow, rw in w_bad[:10]:
        print("        WIDTH  %-46s 1x=%-4d offline=%-4d runtime=%-4d"
              % (fn, w, ow, rw))

    # THE CONFIRMED DEFECT. Not asserted as a pass - reported as a measured
    # fact. See the module docstring for why this is expected to be red.
    ok = len(h_bad) == 0
    check(ok,
          "HEIGHT: offline height-exact-group(h,1.5) == runtime ScaleDim(h,1.5) "
          "for all %d sheets (%d disagree - see docstring: this IS the "
          "register #7 answer, not a gate bug)" % (len(rows), len(h_bad)))
    if h_bad:
        by_shape = {}
        for fn, h, oh, rh in h_bad:
            by_shape.setdefault((h, oh, rh), []).append(fn)
        print("  %d of %d sheets disagree on height:" % (len(h_bad), len(rows)))
        for (h, oh, rh), fns in sorted(by_shape.items()):
            print("        h=%-4d offline=%-4d runtime=%-4d  (%d sheet(s), e.g. %s)"
                  % (h, oh, rh, len(fns), fns[0]))
    return 0


# ══════════════════════════════════════════════════════════════════════════
def main():
    vv = "-v" in sys.argv
    for p in (UPSCALE_CS, SCALETIER_CPP):
        if not os.path.isfile(p):
            print("FAIL: source file not found: %s" % p)
            return 1

    s1_cell_unit()
    s2_scale_dim_base()
    s3_integer_control()
    s4_structural(vv)
    skip = s5_icon_domain() == 2

    print("\n%d checks, %d FAILED" % (_CHECKS[0], len(_FAILS)))
    if _FAILS:
        print("\nFAIL list:")
        for f in _FAILS:
            print("  - " + f)
        return 1
    if skip:
        print("\nEvery runnable check agreed. S5's corpus comparison was "
              "SKIPPED (no nam-1x) - this exit code intentionally stays "
              "nonzero-friendly-but-distinct; treat as INCOMPLETE, not GREEN.")
        return 2
    print("\nAll copies agree, including on the real icon corpus. If you "
          "are seeing this, the height-exact-group drift documented in "
          "this file's docstring has been fixed - update SC4-UI-ENGINE.md "
          "Sec.4.6c.1 and research\\UNKNOWNS-AND-NEXT-TARGETS.md #7 to say so.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
