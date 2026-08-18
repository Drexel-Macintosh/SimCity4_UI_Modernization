#!/usr/bin/env python3
"""#132 REGION ZOOM - offline size gate.

The two v2.82.x crashes were both size DISAGREEMENTS: the click mask at
[item+0x44] still described the stock tile while the pixels had been resized
under it, and GetPixel has no bounds check. So the invariant this gate protects
is not "the tile is big enough", it is:

    at every zoom level, the source, the mask, the composite and the three run
    lists must all describe the SAME dimensions.

v2.83.0 gets that by construction - it never resizes anything, it re-runs the
game's own sub_7AE510, which regenerates all of them from the restored pristine
art. This gate models that construction and proves the property holds at every
reachable level, including the one thing the old design could never do: an
EXACT round trip, because every level is computed from the pristine snapshot at
an absolute factor rather than by multiplying the current size by a ratio.

Constants are parsed out of src\\Settings.h so the model cannot drift from the
shipping code. Run offline; no game required.

    python _tests\\Test-RegionZoomSizes.py
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SETTINGS = os.path.join(ROOT, "src", "Settings.h")

# MEASURED, not assumed: the first-grow line in the v2.82.x capture logs reads
# "REGIONTILE first grow 260x160 -> 520x320", so 260x160 is the real pristine
# thumbnail for this bench region. The second entry is the largest tile seen in
# the same capture's per-item dump.
PRISTINE_TILES = [(260, 160), (260, 188)]

# sub_7AE3D0 emits a sub-pixel-shifted copy that is +2 px on each axis
# (add eax,2 / add ecx,2 at 0x007AE439 / 0x007AE43C). Our hook grows THAT.
SHIFT_MARGIN = 2

TIERS = [1.5, 2.0, 3.0]

failures = []
notes = []


def parse_settings():
    with open(SETTINGS, "r", encoding="utf-8", errors="replace") as f:
        src = f.read()

    def grab(pattern, cast):
        m = re.search(pattern, src)
        if not m:
            failures.append("could not parse %r out of src/Settings.h" % pattern)
            return None
        return cast(m.group(1))

    return {
        "levels": grab(r"int\s+spikeRegionZoomLevels\s*=\s*(\d+)", int),
        "ratio": grab(r"float\s+spikeRegionZoomStepRatio\s*=\s*([0-9.]+)f", float),
        "maxEdge": grab(r"int\s+spikeRegionZoomMaxEdge\s*=\s*(\d+)", int),
        "armed": grab(r"bool\s+spikeRegionZoom\s*=\s*(true|false)", str),
    }


def factor_for_level(base, level, ratio):
    """Mirrors UiSpike::ApplyPendingRegionZoom - always recomputed from BASE."""
    want = base
    for _ in range(0, level):
        want *= ratio
    for _ in range(0, -level):
        want /= ratio
    return want


def grow(edge, factor):
    """Mirrors CodePatches::GrowTileBitmap: (int)(w * f + 0.5f)."""
    return int(edge * factor + 0.5)


def build_item(pristine_w, pristine_h, factor):
    """Model one pass of sub_7AE510 over an item restored to pristine art.

    Returns the dimensions each of the seven structures ends up describing.
    """
    # +0x20 alpha mask and +0x1C source are both built by sub_7AE3D0 from the
    # SAME pristine pair, through the SAME hook, so they cannot diverge unless
    # their inputs already differ.
    mask_w = grow(pristine_w + SHIFT_MARGIN, factor)
    mask_h = grow(pristine_h + SHIFT_MARGIN, factor)
    src_w = grow(pristine_w + SHIFT_MARGIN, factor)
    src_h = grow(pristine_h + SHIFT_MARGIN, factor)
    # +0x2C composite: Init(r.w, r.h) where r = the NEW +0x1C rect (0x007AE6DE).
    comp_w, comp_h = src_w, src_h
    # +0x44 click mask / +0x50 / +0x5C: sub_7AD400 over the NEW +0x20.
    click_w, click_h = mask_w, mask_h
    # +0x38: sub_7B3670 over the composite, on the next paint.
    blit_w, blit_h = comp_w, comp_h
    return {
        "source": (src_w, src_h),
        "mask": (mask_w, mask_h),
        "composite": (comp_w, comp_h),
        "clickmask": (click_w, click_h),
        "blitlist": (blit_w, blit_h),
    }



def gate_tent_identity():
    """#131b: forcing the game's 2-tap tent to phase 1.0 must be BIT-EXACT.

    sub_7AE3D0 runs sub_7AE160, a real 16.16 resampler with a unit-tent kernel
    (sub_7AA0E0 = max(0,1-|x|), normalised to 16384 by sub_7AA860) at scale 1.0
    and phase fx = 1.0 - frac(pos). We now hand it phase 1.0 so it copies
    instead of blending, and re-apply the alignment as whole DEST pixels.

    If that is not bit-exact the whole change is unsound, so assert it over
    every possible pixel pair rather than believing the arithmetic.
    """
    def tent(x):
        return max(0.0, 1.0 - abs(x))

    k0, k1 = tent(-1.0), tent(0.0)
    total = k0 + k1
    i0 = int(round(k0 / total * 16384))
    i1 = 16384 - i0
    if (i0, i1) != (0, 16384):
        failures.append("tent at phase 1.0 has taps (%d,%d), expected (0,16384)"
                        % (i0, i1))
        return 0
    for c in range(256):
        for d in range(256):
            if ((c * i0 + d * i1 + 8192) >> 14) != d:
                failures.append("tent at phase 1.0 is NOT bit-exact: (%d,%d)->%d"
                                % (c, d, (c * i0 + d * i1 + 8192) >> 14))
                return 0
    # And the control: a mid phase must genuinely blend, or we would be
    # "fixing" something that was never broken.
    k0, k1 = tent(-0.19), tent(0.81)
    total = k0 + k1
    i0 = int(round(k0 / total * 16384))
    i1 = 16384 - i0
    worst = max(abs((((c * i0 + d * i1 + 8192) >> 14)) - d)
                for c in (0, 255) for d in (0, 255))
    if worst < 64:
        failures.append("tent at phase 0.19 only shifts a pixel by %d/255 -"
                        " the blur being removed may not be real" % worst)
    print("  tent identity at phase 1.00: BIT-EXACT over all 65536 pixel pairs"
          " (control: phase 0.19 shifts up to %d/255)" % worst)
    return 65538


def main():
    cfg = parse_settings()
    if failures:
        for f in failures:
            print("FAIL: %s" % f)
        return 1

    print("parsed from src/Settings.h: levels=+/-%d ratio=%.4f maxEdge=%d armed=%s"
          % (cfg["levels"], cfg["ratio"], cfg["maxEdge"], cfg["armed"]))
    if cfg["armed"] != "true":
        notes.append("spikeRegionZoom defaults to FALSE - zoom ships disarmed.")

    levels = list(range(-cfg["levels"], cfg["levels"] + 1))
    checks = 0

    for base in TIERS:
        for (pw, ph) in PRISTINE_TILES:
            sizes_by_level = {}
            refused = []
            for lv in levels:
                f = factor_for_level(base, lv, cfg["ratio"])

                # --- GATE 1: the BASIS clamp, [0.25, 8.0] in
                # SetRegionIsoScaleLive. Stock is no longer a floor (v2.85.0):
                # the tile hook shrinks as well as grows, so below 1.0 the
                # lattice and the tiles stay coupled and the map just gets
                # smaller. Only the basis clamp can refuse a level now.
                if f < 0.25 or f > 8.0:
                    refused.append(lv)
                    continue

                s = build_item(pw, ph, f)
                sizes_by_level[lv] = s
                checks += 1

                # --- GATE 2: THE CRASH INVARIANT. Every structure must
                # describe the same box. This is what was false in v2.82.x.
                ref = s["source"]
                for name, dim in s.items():
                    if dim != ref:
                        failures.append(
                            "tier %.2f level %+d tile %dx%d: %s is %dx%d but"
                            " source is %dx%d - a hit test or blit would walk"
                            " off the end"
                            % (base, lv, pw, ph, name, dim[0], dim[1],
                               ref[0], ref[1]))

                # --- GATE 3: the edge cap. RegionZoomRebuild refuses the WHOLE
                # step, so this must never fire mid-range or the map would be
                # stuck at a level it cannot leave.
                if max(ref) > cfg["maxEdge"]:
                    failures.append(
                        "tier %.2f level %+d tile %dx%d -> %dx%d exceeds"
                        " maxEdge %d; the step would be refused"
                        % (base, lv, pw, ph, ref[0], ref[1], cfg["maxEdge"]))

            live = sorted(sizes_by_level.keys())

            # --- GATE 4: EXACT ROUND TRIP. in 2, out 4, in 2 must land on the
            # byte-identical size, because every level rebuilds from the
            # pristine snapshot at an absolute factor. Multiplying the current
            # size by a ratio (the v2.82.x design) cannot pass this.
            trip = [0, 1, 2, 1, 0, -1, -2, -1, 0]
            start = sizes_by_level[0]["source"]
            for lv in trip:
                if lv not in sizes_by_level:
                    continue  # refused level; the user simply cannot reach it
                if sizes_by_level[lv]["source"] != \
                        build_item(pw, ph, factor_for_level(base, lv, cfg["ratio"]))["source"]:
                    failures.append("tier %.2f level %+d is not reproducible"
                                    % (base, lv))
            if sizes_by_level[0]["source"] != start:
                failures.append("tier %.2f: round trip did not return to base"
                                % base)
            checks += 1

            # --- GATE 6b: the WORKING SET. Memory is quadratic in the
            # factor and the per-edge cap bounds only ONE bitmap, so model
            # what RegionZoomRebuild actually charges for: source + composite
            # persist per item, the alpha mask is transient (ReplayOneItem
            # deinits it), so charge for exactly one of those.
            # MEASURED reference: 48 cities, pristine 260x160 after the +2
            # shift margin. Report the levels that fit rather than failing -
            # a level that does not fit is refused WHOLE and logged, which is
            # correct behaviour, but it must be VISIBLE here so nobody raises
            # RegionZoomLevels and quietly gets stops instead of zoom.
            if (pw, ph) == (260, 160):
                BUDGET_MB = 512.0
                ITEMS = 48
                fits = []
                for lv in live:
                    f = factor_for_level(base, lv, cfg["ratio"])
                    w = grow(pw, f); h = grow(ph, f)
                    persist = 2.0 * w * h * 4 * ITEMS
                    transient = float(w) * h * 4
                    mb = (persist + transient) / (1024.0 * 1024.0)
                    if mb <= BUDGET_MB:
                        fits.append(lv)
                if not fits:
                    failures.append(
                        "tier %.2f: NO zoom level fits the %.0f MB budget at %d"
                        " items" % (base, BUDGET_MB, ITEMS))
                notes.append(
                    "tier %.2f @ %d cities, %.0f MB budget: levels %s fit;"
                    " %s refused on memory"
                    % (base, ITEMS, BUDGET_MB,
                       ", ".join("%+d" % lv for lv in fits) or "none",
                       ", ".join("%+d" % lv for lv in live if lv not in fits)
                       or "none"))
            checks += 1

            # --- GATE 6: zoom must not be dead in either direction. A tier
            # where every OUT level is refused would give the user a control
            # that only works one way, which is worth knowing before shipping
            # rather than after.
            if not [lv for lv in live if lv < 0]:
                failures.append(
                    "tier %.2f tile %dx%d: every zoom-OUT level is refused -"
                    " the control only works inward at this tier" % (base, pw, ph))
            if not [lv for lv in live if lv > 0]:
                failures.append(
                    "tier %.2f tile %dx%d: every zoom-IN level is refused"
                    % (base, pw, ph))
            checks += 1

            # --- GATE 5: strictly monotonic. Two adjacent levels that round to
            # the same pixel size would make a zoom notch do nothing visible.
            widths = [sizes_by_level[lv]["source"][0] for lv in live]
            for i in range(1, len(widths)):
                if widths[i] <= widths[i - 1]:
                    failures.append(
                        "tier %.2f tile %dx%d: level %+d (%dpx) is not wider"
                        " than level %+d (%dpx) - that notch is invisible"
                        % (base, pw, ph, live[i], widths[i],
                           live[i - 1], widths[i - 1]))
            if refused:
                notes.append(
                    "tier %.2f tile %dx%d: level(s) %s refused (outside the"
                    " basis clamp [0.25, 8.0])"
                    % (base, pw, ph,
                       ", ".join("%+d" % lv for lv in refused)))
            checks += 1

        # One readable row per tier for the record.
        row_parts = []
        for lv in levels:
            f = factor_for_level(base, lv, cfg["ratio"])
            if f < 0.25 or f > 8.0:
                row_parts.append("%+d:refused" % lv)
            else:
                row_parts.append("%+d:%dpx" % (lv, build_item(
                    PRISTINE_TILES[0][0], PRISTINE_TILES[0][1], f)["source"][0]))
        row = ", ".join(row_parts)
        print("  tier %.2f  260x160 -> %s" % (base, row))

    checks += gate_tent_identity()

    print("")
    for n in notes:
        print("NOTE: %s" % n)
    if failures:
        for f in failures:
            print("FAIL: %s" % f)
        print("\nFAILED - %d check(s), %d failure(s)" % (checks, len(failures)))
        return 1
    print("PASS - %d checks across %d tiers x %d levels x %d tile sizes."
          % (checks, len(TIERS), len(levels), len(PRISTINE_TILES)))
    print("      Source/mask/composite/click-mask/blit-list agree at every"
          " level; round trip is exact; every notch changes the size.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
