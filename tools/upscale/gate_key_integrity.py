r"""#181 - COLOUR-KEY INTEGRITY GATE. Magenta-key damage goes RED at build time.

⛔ WHY THIS EXISTS. Magenta 0xFF00FF is this game's TRANSPARENCY KEY, and the
engine's key test is EXACT-MATCH ONLY. Two failure classes have now each cost
real time:

  1. THE PINK CLASS (#143, and again 2026-08-16 on the Options dialog): any
     resampler that lets the key into an average emits NEAR-key pixels
     (0xFE01FE, 0xFF01FF), the key test misses them, and they PAINT PINK on
     screen. Both incidents shipped at exit 0 with every gate green.
  2. THE FALSE-ALARM CLASS (2026-08-16, the "poisoned fill raster" evening):
     a shallow instrument read redraw_ladder.py's deliberate #180 re-lay as
     key-painted-opaque damage, and disproving it took a corpus census. A
     standing gate that KNOWS the two deliberate exceptions is what makes the
     next alarm a one-command answer instead of an evening.

WHAT IS ASSERTED, per output sheet, against the 1x extract as ground truth:

  R1  NEAR-KEY = 0. No pixel may sit within 8 of the key on every channel
      (|R-255|<=8, G<=8, |B-255|<=8) without BEING the exact key.
      ⚠ STOCK IS EXEMPT BY MEASUREMENT, NOT BY HOPE (law 88 - a model that
      would condemn stock is broken). Censused 2026-08-16 over all 2280 1x
      sources: ZERO keyed sources carry a near-key pixel, and exactly ONE
      unkeyed sheet does ({6a386d26,00001111}, 4556 px of stock (252,0,255)
      art - block-replicated onto the user-confirmed 2x/3x tiers, so failing
      it would fail the control). Hence: on KEYED sheets near-key is
      unconditionally fatal; on UNKEYED sheets it is fatal unless
        (a) the pixel is EXACTLY (255,1,255) - the producer's own G=1 nudge
            (Upscale2x.cs:1495, UpscaleSmoothUnkeyed): when Catmull-Rom
            overshoot MANUFACTURES the key on an unkeyed sheet, the producer
            deliberately writes FF01FF so "no new key pixels" is true by
            construction. Counted and reported as NUDGED, never fatal on an
            unkeyed sheet. On KEYED sheets FF01FF gets NO exemption - there
            the same nudge is the documented #175 pink bug (see the
            --smooth-keyed revert in Rebuild-Corpus.ps1); or
        (b) the 1x SOURCE itself carries near-key, in which case the sheet is
            counted and reported as INHERITED. SHEET-LEVEL by measurement: a
            per-pixel source-mapped form (review finding F4) was attempted
            2026-08-16 and reverted the same night - the smooth-unkeyed
            producer's 4x4 Catmull-Rom support puts legitimate inherited
            near-key at positions the NN map does not predict, so the
            per-pixel rule condemned the stock control at f=1.5 (148 px on
            {6a386d26,00001111}; details at the check itself).
  R2  KEY-SET PRESERVED. The output's exact-key pixel set must EQUAL the
      nearest-neighbour prediction under the upscaler's OWN source map
      (mirrored from Upscale2x.cs BuildSampleMap / UpscaleNearest, including
      the per-state block map for sheets in cell-strips.txt - the derived
      list IS the scope, law 94). For an unkeyed sheet the prediction is the
      empty set, so a manufactured key pixel - a silent transparent hole -
      is caught by the same rule.
  R3  INTEGER CONTROL. At f=2 and f=3 the ladder exemption below is REMOVED:
      redraw_ladder.py is byte-identical to NN there by construction (it
      asserts this itself), so the full R2 equality must hold on every sheet.

THE THREE DELIBERATE EXCEPTION CLASSES (each measured, none exempted blindly):

  * The Mayor Rating ladders - redraw_ladder.py's LADDERS list, imported from
    that file (never restated here - a copy would rot, law 94). At fractional
    factors the #180 re-lay moves key pixels ON PURPOSE, so R2 equality is
    replaced by the redraw's own invariants: (a) the key-column set is
    IDENTICAL on every row (the re-lay draws one grid for the whole
    filmstrip), and (b) every non-key colour in output row r appears in
    source row floor(r/f) (the re-lay only ever copies pixels from the same
    source row).
  * The dock sheet {46a006b0,13d14ca0} - build_selective_safe.py's
    minimap-recess neutralisation repaints a 96x96 1x block at (27,107) in
    the STAGED copy. That repaint touches ZERO key pixels, so the sheet gets
    NO exemption: R2 must hold on it, and if the repaint ever grows into the
    key the gate goes red - which is the desired behaviour, not a false
    positive.
  * The city query "?" pair {46a006b0,14015547} + {46a006b0,4b8da4a4} -
    build_selective_safe.py's #172 clamp_query_pair_cells TRIMS each state
    cell to the scaled window and REPACKS the staged sheet, with no NN
    sampling of the 1x, so R2's prediction does not model those bytes (and
    only accidentally matched before this class existed: both sheets happen
    to carry zero key). NOT a blind skip: zero-exact-key ON BOTH SIDES is
    the very invariant that makes the trim key-safe, so the gate asserts it
    on the 1x source AND the output, at every factor, preview and stage
    trees alike. If either side ever grows a key pixel the gate goes red
    demanding a real model of the clamp (review finding F2, 2026-08-16).

⚠ IF --smooth-keyed EVER COMES BACK (Rebuild-Corpus.ps1 reverted it
2026-08-16): a coverage-re-keyed sheet has a key set that is NOT the NN
prediction, so this gate will go red on every sheet that path touches. That
is deliberate - re-enabling it must be a decision made against this gate,
not around it.

Output discipline (law 42: a gate is only as honest as its scope): prints
scanned / keyed / exempt / unverifiable counts per tier and exits NON-ZERO if
any sheet is unverifiable (a silent skip is a failure mode, not a pass) or if
ZERO sheets were scanned (a scan of nothing is a REFUSAL, not a clean bill).

    python gate_key_integrity.py                     # all three preview tiers
    python gate_key_integrity.py --tier 1.5          # one tier (repeatable)
    python gate_key_integrity.py --dir <dir> --factor <f>   # e.g. a stage dir
                                  (stage clone names resolve via I xor
                                   0x53430001, the SELECTIVE-SAFE.md scheme)
    python gate_key_integrity.py --selftest          # prove the gate goes RED

Offline, read-only over the corpora (--selftest writes only under a temp dir).
"""
import ast
import os
import re
import shutil
import sys
import tempfile

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
SRC1X = os.path.join(TOOLS, "dbpf", "extracted", "SimCity_1")

# 2x deliberately lands in `preview\`, not `preview-2x\` - the name is
# load-bearing (the builders default to it). Same map Rebuild-Corpus.ps1 uses.
TIERS = {"1.5": (1.5, os.path.join(HERE, "preview-15x", "SimCity_1")),
         "2":   (2.0, os.path.join(HERE, "preview", "SimCity_1")),
         "3":   (3.0, os.path.join(HERE, "preview-3x", "SimCity_1"))}

# Stage clone TGIs are I xor this (build_selective_safe.py, SELECTIVE-SAFE.md).
CLONE_XOR = 0x53430001

# Exception class 3 (docstring above): the #172 query-pair sheets that
# build_selective_safe.py clamp_query_pair_cells trims+repacks with no NN
# sampling of 1x. R2 is replaced by a zero-exact-key assertion on BOTH sides.
QUERY_PAIR = {(0x46A006B0, 0x14015547),   # Query       "?" - 1x 148x21
              (0x46A006B0, 0x4B8DA4A4)}   # Route Query "?" - 1x 148x23

# Same name pattern the upscaler itself accepts (Upscale2x.cs TgiNameRe).
TGI_RE = re.compile(
    r"^T-(?:0x)?([0-9A-Fa-f]{1,8})_G-(?:0x)?([0-9A-Fa-f]{1,8})"
    r"_I-(?:0x)?([0-9A-Fa-f]{1,8})\.png$", re.IGNORECASE)

NEAR = 8    # the R1 window: within 8 of FF/00/FF per channel, but not exact


def load_ladders():
    """redraw_ladder.py's LADDERS list, read from the file itself.

    ⛔ PARSED, NOT IMPORTED. That module runs sys.exit(main()) at module level
    (it is a script), so `import redraw_ladder` would execute a redraw. The
    AST of its LADDERS assignment is the same single source of truth without
    running anything."""
    path = os.path.join(HERE, "redraw_ladder.py")
    # F11: literal_eval raises ValueError on a non-literal LADDERS (and
    # ast.parse SyntaxError on a broken file) - both must land on the same
    # FATAL as "not found", not a bare traceback.
    try:
        with open(path, "r", encoding="utf-8") as fh:
            tree = ast.parse(fh.read(), path)
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for tgt in node.targets:
                    if isinstance(tgt, ast.Name) and tgt.id == "LADDERS":
                        return set(map(tuple, ast.literal_eval(node.value)))
    except (OSError, SyntaxError, ValueError, TypeError) as e:
        sys.exit("FATAL: LADDERS in redraw_ladder.py could not be read as a "
                 "literal list (%s) - the ladder exemption has no authority "
                 "to import, refusing to guess." % e)
    sys.exit("FATAL: LADDERS not found in redraw_ladder.py - the ladder "
             "exemption has no authority to import, refusing to guess.")


def load_cell_strips():
    """cell-strips.txt -> {(g,i): states}, parsed exactly as Upscale2x.cs does
    (>=3 fields, hex g/i, integer states >= 2; comments and short lines skipped)."""
    strips = {}
    path = os.path.join(HERE, "cell-strips.txt")
    if not os.path.isfile(path):
        sys.exit("FATAL: %s is missing. The NN prediction depends on the "
                 "per-state block map, so gating without it would verify the "
                 "wrong mapping and pass falsely." % path)
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            parts = s.split()
            if len(parts) < 3:
                continue
            try:
                g, i, n = int(parts[0], 16), int(parts[1], 16), int(parts[2])
            except ValueError:
                continue
            if n >= 2:
                strips[(g, i)] = n
    return strips


def index_sources():
    """{(g,i): path} over the 1x extract, recursive (the upscaler recurses)."""
    idx = {}
    for root, _dirs, files in os.walk(SRC1X):
        for fn in files:
            m = TGI_RE.match(fn)
            if m:
                idx[(int(m.group(2), 16), int(m.group(3), 16))] = \
                    os.path.join(root, fn)
    return idx


def sample_map(src, out, factor, states=0):
    """Mirror of Upscale2x.cs BuildSampleMap (X axis; states=0 gives the Y-axis
    rule from UpscaleNearest). The dims are read from the REAL files, so
    whichever snap rule produced `out` (cell-first, no-snap, height-exact...)
    the branch condition below sees exactly what the tool's own map saw."""
    if states > 1 and src % states == 0 and out % states == 0:
        bs, bo = src // states, out // states
        m = np.empty(out, dtype=np.int64)
        for b in range(states):
            blk = b * bs + (np.arange(bo, dtype=np.int64) * bs) // bo
            np.minimum(blk, (b + 1) * bs - 1, out=blk)
            m[b * bo:(b + 1) * bo] = blk
        return m
    o = np.arange(out, dtype=np.int64)
    # factorMap = outLen >= floor(src*f); then (int)(o/f) - i.e. TRUNCATED
    # double division, which is what .astype(int64) does - else the ratio map.
    if out >= int(np.floor(src * factor)):
        m = (o / factor).astype(np.int64)
    else:
        m = (o * src) // out
    return np.minimum(m, src - 1)


def rgb(path):
    """HxWx3 uint8. The key test is RGB-only (the engine and Upscale2x.cs
    HasExactColorKey both mask alpha off), so alpha is dropped deliberately."""
    return np.asarray(Image.open(path).convert("RGB"), dtype=np.uint8)


def key_mask(a):
    return (a[..., 0] == 255) & (a[..., 1] == 0) & (a[..., 2] == 255)


def near_mask(a):
    r = a[..., 0].astype(np.int16)
    g = a[..., 1].astype(np.int16)
    b = a[..., 2].astype(np.int16)
    return (r >= 255 - NEAR) & (g <= NEAR) & (b >= 255 - NEAR) & ~key_mask(a)


def pack(a):
    """RGB rows -> uint32 for set membership tests."""
    return (a[..., 0].astype(np.uint32) << 16) | \
           (a[..., 1].astype(np.uint32) << 8) | a[..., 2].astype(np.uint32)


def first_coords(mask, n=3):
    ys, xs = np.nonzero(mask)
    return ", ".join("(%d,%d)" % (x, y) for x, y in zip(xs[:n], ys[:n]))


def check_ladder(out, act, src, factor, rel, fails):
    """The #180 redraw invariants, in place of R2, at fractional factors only.

    (a) ONE GRID FOR THE WHOLE FILMSTRIP: the re-lay computes its cell grid
        once (source row 0) and draws it on every output row, so the key
        columns must be identical row to row.
    (b) COLOURS COME FROM THE SAME SOURCE ROW: the redraw only ever copies
        pixels from source row floor(r/f) into output row r, so every non-key
        output colour must exist in that source row."""
    h1 = src.shape[0]
    if not act.any():
        fails.append(("LADDER", rel, "no exact-key pixel at all - the ladder "
                      "lost its gaps entirely"))
        return
    if not (act == act[0]).all():
        bad = np.nonzero((act != act[0]).any(axis=1))[0]
        fails.append(("LADDER", rel,
                      "key columns differ from row 0 on %d row(s), first row %d"
                      % (len(bad), int(bad[0]))))
        return
    src_packed = pack(src)
    out_packed = pack(out)
    for oy in range(out.shape[0]):
        sy = min(int(oy / factor), h1 - 1)
        colours = np.unique(out_packed[oy][~act[oy]])
        missing = colours[~np.isin(colours, src_packed[sy])]
        if missing.size:
            fails.append(("LADDER", rel,
                          "out row %d holds colour #%06x absent from source "
                          "row %d (%d foreign colour(s))"
                          % (oy, int(missing[0]), sy, missing.size)))
            return


def gate_dir(out_dir, factor, src_index, strips, ladders, label):
    """Scan one output tree. Returns (fails, unverifiable, counts)."""
    fails, unver, notes = [], [], []
    scanned = keyed = exempt = inherited = nudged = 0
    fractional = (factor != int(factor))

    pngs = []
    for root, _dirs, files in os.walk(out_dir):
        for fn in sorted(files):
            if fn.lower().endswith(".png"):
                pngs.append(os.path.join(root, fn))

    for path in sorted(pngs):
        rel = os.path.relpath(path, out_dir)
        m = TGI_RE.match(os.path.basename(path))
        if not m:
            unver.append((rel, "name does not parse as a TGI"))
            continue
        g, i = int(m.group(2), 16), int(m.group(3), 16)
        # Stage trees hold CLONE copies at I xor CLONE_XOR; the art bytes are
        # the original TGI's, so resolve to the original for source lookup,
        # the cell-strips states AND the ladder exemption.
        if (g, i) in src_index:
            og, oi = g, i
        elif (g, i ^ CLONE_XOR) in src_index:
            og, oi = g, i ^ CLONE_XOR
        else:
            unver.append((rel, "no 1x source for {%08x,%08x} (nor its "
                          "clone-xor twin)" % (g, i)))
            continue
        try:
            out = rgb(path)
        except Exception as e:
            unver.append((rel, "output unreadable: %s" % e))
            continue
        try:
            src = rgb(src_index[(og, oi)])
        except Exception as e:
            unver.append((rel, "1x source unreadable: %s" % e))
            continue

        scanned += 1
        src_key = key_mask(src)
        is_keyed = bool(src_key.any())
        if is_keyed:
            keyed += 1

        h1, w1 = src.shape[:2]
        oh, ow = out.shape[:2]

        # ---- R1: near-key ----
        out_near = near_mask(out)
        if out_near.any():
            if is_keyed:
                # KEYED: unconditionally fatal, FF01FF included - on a keyed
                # sheet the G=1 nudge IS the #175 pink bug, never a sentinel.
                fails.append(("R1", rel, "%d near-key px on a KEYED sheet, "
                              "first %s - the #143 pink class"
                              % (int(out_near.sum()), first_coords(out_near))))
            else:
                # UNKEYED exemption (a): EXACTLY (255,1,255) is the producer's
                # own sentinel - Upscale2x.cs:1495 (UpscaleSmoothUnkeyed)
                # deliberately nudges a Catmull-Rom-manufactured key off to
                # G=1 so an unkeyed sheet can never grow a key pixel. Counted
                # and reported, never fatal here. Every OTHER near-key value
                # stays subject to (b) below.
                nudge = (out[..., 0] == 255) & (out[..., 1] == 1) & \
                        (out[..., 2] == 255) & out_near
                n_nudge = int(nudge.sum())
                if n_nudge:
                    nudged += n_nudge
                    notes.append("NUDGED %d px (producer sentinel, "
                                 "Upscale2x.cs smooth-unkeyed) in %s"
                                 % (n_nudge, rel))
                rest = out_near & ~nudge
                if rest.any():
                    # UNKEYED exemption (b): the 1x source itself carries
                    # near-key -> INHERITED, counted, never fatal.
                    # ⛔ SHEET-LEVEL, NOT PER-PIXEL - MEASURED, NOT PREFERRED
                    # (review finding F4, attempted 2026-08-16 and reverted
                    # the same night): the per-pixel form - fail on
                    # out_near & ~src_near[my][:,mx] - condemns the STOCK
                    # control. {6a386d26,00001111} is smooth-unkeyed at
                    # f=1.5 (Catmull-Rom, 4x4 support), so 148 of its
                    # inherited near-key px land at positions whose NN-mapped
                    # source px sits just OUTSIDE the near window (measured:
                    # out (74,2)=(248,0,251) vs NN src (237,0,240)) while
                    # every one of the 148 has ~10 near-key px inside its own
                    # 4x4 support. 2x/3x pass the per-pixel form (0 non-
                    # mapped px - NN block replicate), so the reviewer's
                    # premise is true exactly where the rule is not needed. A
                    # per-pixel rule here needs a model of the SMOOTH
                    # producer's support, not the NN map; until that model
                    # exists the sheet-level rule stands (law 88 - a model
                    # that would condemn stock is broken). KNOWN BLIND SPOT,
                    # accepted: near-key damage elsewhere on the ONE such
                    # sheet in the census is amnestied by its stock art.
                    if near_mask(src).any():
                        inherited += 1
                    else:
                        fails.append(("R1", rel, "%d near-key px on an "
                                      "unkeyed sheet whose 1x source has "
                                      "NONE, first %s"
                                      % (int(rest.sum()), first_coords(rest))))

        # ---- R2 / ladder invariants: exact-key set ----
        act = key_mask(out)
        if fractional and (og, oi) in ladders:
            exempt += 1
            check_ladder(out, act, src, factor, rel, fails)
            continue
        if (og, oi) in QUERY_PAIR:
            # Exception class 3 (#172, F2): the staged sheets are trims +
            # repacks of the NN output (clamp_query_pair_cells) - no NN map
            # models them. The invariant that makes that clamp key-safe is
            # zero exact-key ON BOTH SIDES, so assert exactly that instead.
            exempt += 1
            if src_key.any() or act.any():
                fails.append(("R2", rel, "query-pair sheet carries %d source "
                              "/ %d output exact-key px - the #172 trim+"
                              "repack (clamp_query_pair_cells) has NO NN "
                              "model and is only key-safe while both sides "
                              "are key-free. Write a real model of the clamp "
                              "before shipping this sheet."
                              % (int(src_key.sum()), int(act.sum()))))
            continue
        mx = sample_map(w1, ow, factor, strips.get((og, oi), 0))
        my = sample_map(h1, oh, factor, 0)
        pred = src_key[my[:, None], mx[None, :]]
        if not np.array_equal(pred, act):
            miss = pred & ~act
            extra = act & ~pred
            det = []
            if miss.any():
                det.append("%d predicted key px NOT key, first %s"
                           % (int(miss.sum()), first_coords(miss)))
            if extra.any():
                det.append("%d key px NOT predicted, first %s"
                           % (int(extra.sum()), first_coords(extra)))
            fails.append(("R2", rel, "; ".join(det)))

    tag = "R3 integer control (ladder exemption REMOVED)" if not fractional \
          else "R2 with ladder invariants"
    print("gate_key_integrity %s  f=%g  [%s]" % (label, factor, tag))
    print("  scanned %d  keyed %d  exempt %d  unverifiable %d"
          "  near-key-inherited-from-stock %d  nudged-sentinel-px %d"
          % (scanned, keyed, exempt, len(unver), inherited, nudged))
    for note in notes:
        print("  %s" % note)
    for rel, why in unver:
        print("  UNVERIFIABLE %s: %s" % (rel, why))
    for rule, rel, why in fails:
        print("  FAIL [%s] %s: %s" % (rule, rel, why))
    if scanned == 0:
        # Zero items scanned is a REFUSAL: an empty tree, a typo'd path and a
        # clean corpus all print "0 failures" - only the counts tell them apart.
        print("  REFUSAL: zero sheets scanned in %s" % out_dir)
    ok = (not fails) and (not unver) and scanned > 0
    print("  %s" % ("PASS - key integrity holds" if ok
                    else "FAIL - do NOT ship this tree"))
    return fails, unver, scanned


def selftest(src_index, strips, ladders):
    """⛔ PROVE THE GATE CAN GO RED (thresholds-from-controls law). Copy a real
    keyed sheet, damage it three ways, and require every damage to be caught.
    A gate that has never failed is a gate that may not be able to."""
    factor, tier_dir = TIERS["1.5"][0], TIERS["1.5"][1]
    candidate = None
    for fn in sorted(os.listdir(tier_dir)):
        m = TGI_RE.match(fn)
        if not m:
            continue
        g, i = int(m.group(2), 16), int(m.group(3), 16)
        if (g, i) in ladders or (g, i) not in src_index:
            continue
        try:
            if key_mask(rgb(src_index[(g, i)])).any():
                candidate = fn
                break
        except Exception:
            continue
    if not candidate:
        print("SELFTEST FAIL: no keyed non-exempt sheet found to damage")
        return 1

    def run_on_copy(mutate, expect_rule, what, fname=None):
        fname = fname or candidate
        tmp = tempfile.mkdtemp(prefix="gate_key_selftest_")
        try:
            dst = os.path.join(tmp, fname)
            shutil.copy2(os.path.join(tier_dir, fname), dst)
            if mutate is not None:
                im = Image.open(dst).convert("RGBA")
                a = np.array(im)
                mutate(a)
                Image.fromarray(a, "RGBA").save(dst)
            print("--- selftest: %s ---" % what)
            fails, unver, _ = gate_dir(tmp, factor, src_index, strips,
                                       ladders, "(selftest tmp)")
            if expect_rule is None:
                return (not fails) and (not unver)
            return any(r == expect_rule for r, _f, _w in fails)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    out = rgb(os.path.join(tier_dir, candidate))
    act = key_mask(out)
    kys, kxs = np.nonzero(act)
    nys, nxs = np.nonzero(~act & ~near_mask(out))
    if not len(kys) or not len(nys):
        print("SELFTEST FAIL: %s has no usable key/non-key pixel" % candidate)
        return 1
    ky, kx = int(kys[len(kys) // 2]), int(kxs[len(kxs) // 2])
    ny, nx = int(nys[len(nys) // 2]), int(nxs[len(nxs) // 2])
    print("selftest sheet: %s  key px (%d,%d)  non-key px (%d,%d)"
          % (candidate, kx, ky, nx, ny))

    def near_key(a):     a[ky, kx, :3] = (254, 1, 254)     # FE01FE, the #143 mutation
    def opaque(a):       a[ky, kx, :3] = (32, 64, 96)      # key painted opaque
    def manufactured(a): a[ny, nx, :3] = (255, 0, 255)     # hole punched in art

    # --- F1/F4 damage classes need UNKEYED sheets: one whose source is clean
    # of near-key (for the producer-sentinel case) and one whose source
    # CARRIES near-key (for the per-pixel inherited case). ---
    unkeyed = inh_cand = None
    for fn in sorted(os.listdir(tier_dir)):
        m = TGI_RE.match(fn)
        if not m:
            continue
        g, i = int(m.group(2), 16), int(m.group(3), 16)
        if (g, i) in ladders or (g, i) in QUERY_PAIR or (g, i) not in src_index:
            continue
        try:
            s = rgb(src_index[(g, i)])
        except Exception:
            continue
        if key_mask(s).any():
            continue
        if near_mask(s).any():
            if inh_cand is None:
                inh_cand = fn
        elif unkeyed is None:
            try:
                if not near_mask(rgb(os.path.join(tier_dir, fn))).any():
                    unkeyed = fn
            except Exception:
                pass
        if unkeyed and inh_cand:
            break
    if not unkeyed or not inh_cand:
        print("SELFTEST FAIL: missing an unkeyed candidate (found %r) or an "
              "inherited-near-key candidate (found %r)" % (unkeyed, inh_cand))
        return 1
    ua = rgb(os.path.join(tier_dir, unkeyed))
    uy, ux = ua.shape[0] // 2, ua.shape[1] // 2
    print("selftest unkeyed sheet: %s  px (%d,%d)" % (unkeyed, ux, uy))
    print("selftest inherited sheet: %s (positive control only - see the F4 "
          "note in gate_dir: per-pixel inherited was reverted by measurement)"
          % inh_cand)

    def nudge_sentinel(a):   a[uy, ux, :3] = (255, 1, 255)   # FF01FF, Upscale2x.cs:1495
    def unkeyed_fe01fe(a):   a[uy, ux, :3] = (254, 1, 254)   # near-key, NOT the sentinel

    results = [
        ("POSITIVE CONTROL (undamaged copy must PASS)",
         run_on_copy(None, None, "undamaged control")),
        ("key px -> near-key FE01FE caught by R1",
         run_on_copy(near_key, "R1", "key -> near-key FE01FE")),
        ("key px -> near-key FE01FE also caught by R2 (key set lost a px)",
         run_on_copy(near_key, "R2", "key -> near-key (R2 view)")),
        ("key px -> opaque caught by R2",
         run_on_copy(opaque, "R2", "key -> opaque")),
        ("non-key px -> exact key caught by R2",
         run_on_copy(manufactured, "R2", "non-key -> exact key")),
        # F1: the producer sentinel passes (as NUDGED) on an unkeyed sheet...
        ("unkeyed px -> FF01FF sentinel PASSES as NUDGED (F1)",
         run_on_copy(nudge_sentinel, None, "unkeyed -> FF01FF sentinel",
                     fname=unkeyed)),
        # ...while any OTHER near-key value on the same sheet stays fatal.
        ("unkeyed px -> near-key FE01FE caught by R1 (F1)",
         run_on_copy(unkeyed_fe01fe, "R1", "unkeyed -> near-key FE01FE",
                     fname=unkeyed)),
        # The stock near-magenta sheet must never be condemned (law 88); this
        # is the control that caught F4's per-pixel form and reverted it.
        ("POSITIVE CONTROL (inherited-near-key sheet must PASS undamaged)",
         run_on_copy(None, None, "undamaged inherited control",
                     fname=inh_cand)),
    ]
    print("\n=== SELFTEST VERDICT ===")
    ok = True
    for what, got in results:
        print("  %s  %s" % ("CAUGHT" if got else "MISSED", what))
        ok = ok and got
    print("SELFTEST %s" % ("PASS - the gate can go red on every damage class"
                           if ok else "FAIL - THE GATE IS BLIND, do not trust "
                           "its green"))
    return 0 if ok else 1


def main():
    argv = sys.argv[1:]
    if "--help" in argv or "-h" in argv:
        sys.exit(__doc__)
    strips = load_cell_strips()
    ladders = load_ladders()
    src_index = index_sources()
    if not src_index:
        sys.exit("FATAL: no TGI-named PNGs under %s - cannot gate against a "
                 "missing ground truth." % SRC1X)

    if "--selftest" in argv:
        return selftest(src_index, strips, ladders)

    # F11: every flag that takes a value is bounds-checked - a trailing flag
    # used to die with a bare IndexError instead of saying what was missing.
    def flag_value(flag):
        j = argv.index(flag)
        if j + 1 >= len(argv):
            sys.exit("%s requires a value" % flag)
        return argv[j + 1]

    runs = []
    if "--dir" in argv:
        d = flag_value("--dir")
        if "--factor" not in argv:
            sys.exit("--dir requires --factor (the NN prediction is "
                     "factor-specific)")
        fv = flag_value("--factor")
        try:
            f = float(fv)
        except ValueError:
            sys.exit("--factor must be a number, got %r" % fv)
        runs.append((f, d, os.path.basename(os.path.normpath(d))))
    else:
        tiers = []
        for j, a in enumerate(argv):
            if a == "--tier":
                if j + 1 >= len(argv):
                    sys.exit("--tier requires a value (1.5, 2 or 3)")
                tiers.append(argv[j + 1])
        for t in (tiers or ["1.5", "2", "3"]):
            try:
                key = "%g" % float(t)
            except ValueError:
                key = None
            if key not in TIERS:
                sys.exit("unknown tier %r (know 1.5, 2, 3)" % t)
            f, d = TIERS[key]
            runs.append((f, d, os.path.relpath(d, HERE)))

    bad = 0
    for f, d, label in runs:
        if not os.path.isdir(d):
            print("gate_key_integrity %s: MISSING DIRECTORY %s" % (label, d))
            bad += 1
            continue
        fails, unver, scanned = gate_dir(d, f, src_index, strips, ladders,
                                         label)
        if fails or unver or scanned == 0:
            bad += 1
        print()
    return 1 if bad else 0


sys.exit(main())
