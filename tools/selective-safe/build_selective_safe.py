#!/usr/bin/env python3
r"""
Selective-safe 2x UI art override builder for SC4 UI scaling.

Implements the mechanism in tools\research\UI-ART-BINDING.md section 6:
  - Parse ALL .UI layout scripts (G-96A006B0 x271 + G-08000600 x10).
  - Mark the subtrees of the runtime-scaled windows (15 known window IDs).
  - Ref map: every image={gid,iid} occurrence -> EXCLUSIVE / SHARED / UNSCALED.
  - EXCLUSIVE + 2x available  -> stage 2x PNG at ORIGINAL TGI (in-place override).
  - SHARED    + 2x available  -> stage 2x PNG clone at NEW IID = orig ^ 0x53430001,
                                 retarget only the scaled-subtree refs at the clone.
  - Double imagerect=(l,t,r,b) on every scaled-subtree control whose art went 2x
    (imagerect is bitmap-pixel LTRB; it must double when the bitmap doubles).
  - Ship every scaled-window .UI file EDITED at its ORIGINAL TGI.
  - CODE-BOUND art (tools\research\DYNAMIC-CONTROLS.md): TGIs the exe binds by
    constant, invisible to the .UI scan. Staged 2x in-place at the ORIGINAL TGI
    (no clone, no imagerect edit -- code-bound art has no .UI rect), but ONLY if
    the TGI is absent from every parsed .UI ref; a TGI referenced by
    unscaled-only .UI files is reported as a conflict and left alone.
  - Pack everything into one z_SC4UIScale_SelectiveArt.dat.

No game files are touched; everything happens under tools\.
"""

import argparse
import csv
import math
import os
import re
import shutil
import struct
import subprocess
import sys
import zlib
from collections import defaultdict

# Derived from this file's own location - a literal repo path here both
# published a username and broke for anyone who cloned elsewhere.
TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UI_DIR = os.path.join(TOOLS, "uiscripts", "extracted")
PNG_TGI_CSV = os.path.join(TOOLS, "dbpf", "extracted-png-tgi.csv")

# Both of the above are DERIVED from the player's own game install and are
# deliberately not committed. A cold-clone test (2026-08-18) found this file
# dying on a bare FileNotFoundError naming a path the reader had never heard
# of. corpus_inputs derives the csv if it can and otherwise names the exact
# command to run. Import BEFORE any module-level read of either path.
sys.path.insert(0, TOOLS)
import corpus_inputs  # noqa: E402
corpus_inputs.ensure_png_tgi_csv()
corpus_inputs.require_ui_corpus()
PACKER = os.path.join(TOOLS, "dbpf", "DbpfPack.exe")
OUT_DIR = os.path.join(TOOLS, "selective-safe")

# ---------------------------------------------------------------------------
# Scale factor N (default 2, which keeps every output bit-identical to the
# original 2x build). N=1.5 and N=3 emit factor-tagged packages into
# tools\packages\<tag>\ without touching the 2x artifacts. The tag goes in the
# BASE filename before .dat (e.g. z_SC4UIScale_SelectiveArt-15x.dat) -- the DLL
# tier loader relies on that convention.
#   imagerect (bitmap-pixel LTRB) scales by N with round-half-up
#   (floor(v*N + 0.5)); for N=2/3 that is exactly v*N. The upscaler uses the
#   same rule for the PNG dimensions, so 9-slice insets never leave the art.
#   Clone-IID scheme and font-GUID conversion are unchanged (factor-independent).
# ---------------------------------------------------------------------------
_ap = argparse.ArgumentParser(description="Selective-safe UI art override builder (factor-parametric).")
_ap.add_argument("--factor", type=float, default=2.0,
                 help="scale factor: 2 (default, bit-identical), 1.5, or 3")
_args, _ = _ap.parse_known_args()
FACTOR = _args.factor


def _factor_tag(f):
    if abs(f - 2.0) < 1e-9:
        return ""      # default 2x path keeps the original untagged filenames
    if abs(f - 1.5) < 1e-9:
        return "15x"
    if abs(f - 3.0) < 1e-9:
        return "3x"
    if abs(f - round(f)) < 1e-9:
        return "%dx" % int(round(f))
    return ("%gx" % f).replace(".", "_")


TAG = _factor_tag(FACTOR)


def scale_len(v):
    """Scale a pixel length by FACTOR, round-half-up. v*N exactly for integer N."""
    return int(math.floor(v * FACTOR + 0.5))


if TAG:
    UPSCALE_DIR = os.path.join(TOOLS, "upscale", "preview-%s" % TAG, "SimCity_1")
    PKG_DIR = os.path.join(TOOLS, "packages", TAG)
    STAGE = os.path.join(OUT_DIR, "stage-%s" % TAG)
    OUT_DAT = os.path.join(PKG_DIR, "z_SC4UIScale_SelectiveArt-%s.dat" % TAG)
    REFMAP_CSV = os.path.join(OUT_DIR, "refmap-%s.csv" % TAG)
    PKG_LIST = os.path.join(OUT_DIR, "package-list-%s.txt" % TAG)
else:
    UPSCALE_DIR = os.path.join(TOOLS, "upscale", "preview", "SimCity_1")
    STAGE = os.path.join(OUT_DIR, "stage")
    OUT_DAT = os.path.join(OUT_DIR, "z_SC4UIScale_SelectiveArt.dat")
    REFMAP_CSV = os.path.join(OUT_DIR, "refmap.csv")
    PKG_LIST = os.path.join(OUT_DIR, "package-list.txt")

PNG_TYPE = 0x856DDBAC
UI_TYPE = 0x00000000
CLONE_XOR = 0x53430001  # "SC" 0x5343 + 0x0001 marker; documented in SELECTIVE-SAFE.md

# Window IDs the runtime scaling layer doubles (city-HUD panels + subtrees).
SCALED_WINDOW_IDS = {
    0xE9889775, 0x6A64E3C0, 0xCA2AEDC0, 0x0987B48F, 0x69E40A1F, 0xEA8CAD14,
    # panel variants
    0x6A15C767, 0xAA3AC000, 0xABC619D2, 0x0A4A8176, 0x8A8B5B71, 0xC98F49F1,
    0x699306ED, 0xCA35CBED, 0x0A78827A,
    # GOD-MODE toolbar cluster (2026-07-24, runtime-scaled in SC4UIScale
    # v2.7.14/15): 0xC991EDA8 is the root of BOTH god toolbar scripts
    # (I-69e3d347 expanded tiles + I-a991ed83 collapsed column - the twin
    # pair). Without it, shared art like the end-cap sun {46a006b0,14415870}
    # classified "shared with unscaled 69e3d347" -> cloned for the flyout,
    # ORIGINAL left 1x for the toolbar = the ghost-sun duplicate. Also the
    # remaining god flyout roots (terrain-fx + day/night).
    # (0xABB26B0E used to be duplicated here; its real entry with the real
    # comment is the "Sim-mode left sidebar" one below. Harmless to python -
    # a set literal dedups - but two comment blocks claiming one id is drift
    # bait. Test-BornCorrectCoverage.ps1 warns on duplicates now.)
    0xC991EDA8, 0x49923239,
    # region screen panels (host 0xEA659793; RegionWatchTick scales these,
    # flyouts included once they turn visible)
    0x0BB0F5E7, 0x09EBE9EE, 0x6A91DC15, 0x6A91DC16, 0xEA8CAD19, 0x6A91DC14,
    0x09EBEE45, 0x09EBEE60, 0x6BB92BCA,
    # NEWS READER (2026-07-28). Second root of script I-2a2aed99 -- the twin of
    # the ticker root 0xCA2AEDC0, which has been listed above since 2026-07-23.
    # The DLL now scales the reader's GEOMETRY deterministically (880x456 = 2x
    # of stock 440x228, confirmed in SC4UIScale.log), but its header BMP still
    # carried imagerect=(16,6,440,228) -- a 1x source rect inside a 2x window,
    # which is the partial header art + untextured top-right patch. Runtime must
    # never touch imagerect (project rule), so the ART layer is fixed here:
    # {46a006b0,144161f8} header/frame becomes EXCLUSIVE 2x-in-place, and the
    # close button {46a006b0,144161f9} (88 refs across 46 files, all others
    # unscaled) is cloned+retargeted so no other dialog is disturbed.
    #
    # NOTE: this builder scales imagerect= and art ONLY -- it never edits
    # area= (see build_dialog_static.py for the full-static contract). So both
    # 0xCA2AEDC0 and 0xAA231508 MUST REMAIN runtime-scaled by the DLL for their
    # geometry; putting either in kNeverScaleIds would leave a 1x window holding
    # 2x art and a 2x source rect.
    0xAA231508,
    # MAYOR-MODE LEFT-TOOLBAR FLYOUTS (2026-07-28). Their siblings were already
    # here and render correctly - 0x49923239 (Landscape) and 0x699306ED (Civic)
    # came in with the 2026-07-24 god-cluster fix - while these three were
    # missed, which is the whole bug: the Zone flyout's selection ring drew at
    # HALF SIZE and in the WRONG BAND (on toolbar button 1 instead of button 2),
    # the signature of 1x art + a 1x imagerect inside a correctly-placed 2x
    # window. User-confirmed in game.
    #
    # Safe to add: this builder scales imagerect= and art ONLY, never area=
    # (see the note above), and these flyouts' GEOMETRY is docked at runtime by
    # the DLL via the alignment-marker rule (kMayorFlyoutDock in UiSpike.cpp).
    # So there is no 4x double-scale risk, and they must NOT go in kNeverScaleIds.
    0x69923479,   # Zone Tools       (script I-e9949936, off button 2 0x0991EE13)
    0xC99237A0,   # Transportation   (script I-e99237ff, off button 3 0xA994824D)
    0xE992F711,   # Utilities        (script I-4992f764, off button 4 0xE991EE2F)
    0x0992FD17,   # Emergency Tools  (script I-899302fc, off button 7 0x6991EE42)
                  # 2026-07-29: the LAST missed mayor flyout - same symptom as
                  # the three above (1x ring bitmap 0x2992FD21 GZWinBMP
                  # image={46a006b0,14215e2c} drawn in the wrong band). Its
                  # panel class 0x00ADF6A0 sizes the draw FROM THE SOURCE
                  # IMAGE (Plot 0x9BC325: dst = origin + srcWxH), so 2x art =
                  # 2x draw with no code hook.
    # BUDGET family (2026-07-29 evening, user report "black areas when the
    # budget expands"): the compact bar 0xAA3AC000 above was already handled,
    # but its three siblings in scripts I-aa3acdfe/I-cbc3c2b9 were not. All
    # measured runtime-scaled live (expanded root 1116x1010, rows 938x36 -
    # geometry perfect) with 1x art -> the backgrounds (140155b5/b6/c9/ca/
    # cb/cc, previously CONFLICT-listed in the code-bound pass because these
    # very scripts referenced them unscaled) covered a quarter of the window
    # and the rest painted black fill. Taxes/Loan are pre-scaled while
    # hidden by kAlwaysScaleCityIds in UiSpike.cpp (added same day) - the
    # art and the runtime scale must move together.
    0xAA3AC001,   # expanded Monthly Budget panel (558x505 design)
    0xAA3AC002,   # Taxes editor popup
    0xCA4C332D,   # Take Out A Loan popup
    # ADVISOR BRIEFING panels (2026-07-29 late, user report "advisor page
    # corrupted"): the Advisors console strip 0x6A15C767 above was already
    # handled (2x faces), but the per-advisor briefing views in the same
    # scripts (I-cbc905cd + I-4a160034) were not - their 1x tiled/edge art
    # repeated inside the runtime-doubled windows (repeating back/expand
    # buttons, overlapping background; worse when expanded). Both panels'
    # AdviceList children 0x00100100/0x00100101 are guarded never-recurse
    # in UiSpike.cpp (kAdviceListScaleSelfIds), and all three advisor roots
    # are pre-scaled while hidden (kAlwaysScaleCityIds) - the strip's
    # first-open quarter-zoomed faces were the missing pre-scale.
    0xAA15EF06,   # advisor briefing panel (compact)
    0x2A1D96B1,   # advisor briefing panel (expanded)
    # DATA VIEWS fold-out panel (task #45) - ATTEMPTED v2.21.0, REVERTED
    # v2.21.1 the same night. Root 0xAA32BCE6 (live script I-2bc9060f, the
    # one whose rects match the runtime dump; I-ea287193 / I-0b72f276 are
    # stale copies sharing the root id) was added here + the city-sweep
    # id-skip removed: the COMPACT panel then rendered correctly at 2x
    # (user-confirmed) but EXPANDING it shifted the panel right and CRASHED
    # the game - the expand path repositions/re-sizes with 1x metrics and
    # its draw path dies with 2x children present (suspect: code-painted
    # data-map child 0x00004203, the minimap-surface problem class).
    # RE-LANDED v2.21.2 (same night): offline disassembly proved the crash
    # was the map child 0x00004203 - a SECOND cSC4WinMiniMap instance
    # (GetClassID 0x7A6580 returns clsid 0xCA318388; renderer sub_7A2F60
    # fetches it via iid 0xCA318385) whose one-shot display surface stayed
    # 256 while the renderer built window-sized buffers. The DLL now runs
    # the dock-minimap surface-recreate lever on it (DVMAP block in
    # UiSpike.cpp). Note {46a006b0,14416264} + 140155ec become SHARED
    # (Audio Options I-ca53f06e still 1x) - clone path handles them, never
    # force in-place.
    0xAA32BCE6,   # Data Views panel (compact bar + expanded pages + flyout)
    # U-DRIVE-IT DASHBOARD (task #46 part 2, v2.21.5, user report "entering
    # U-Drive-It mode gives a broken controls screen"): the driving console
    # at screen bottom - root 0x4BCB938A, four variant scripts
    # (I-0bec56c1/c2 + I-0c05bcf0/I-0c0734e6, ~463x132 design). The sweep
    # doubles its geometry but the shell/gauge-face art was 1x -> black
    # fill + quarter art (the budget-panel signature: ART AND RUNTIME MOVE
    # TOGETHER). Its embedded minimap (clsid 0xca318388 id 0x0BC3B559 -
    # SAME id as the dock minimap, third cSC4WinMiniMap instance) gets the
    # surface-recreate lever in UiSpike.cpp (UDMAP block).
    0x4BCB938A,   # U-Drive-It dashboard console (all four variant scripts)
    # #93 (v2.48.0): THE FIFTH CONSOLE VARIANT. I-8c1a5c9f declares root
    # 0xEC1A5CBF at area=(18,15,481,147) = 463x132 - the SAME design
    # footprint as the four scripts above - but it is not one of them, and
    # it was in NO list on either side. Its root carries winflag_pbuff=yes,
    # so its private buffer is sized at FIRST PAINT: unlisted, the game
    # paints it 1x, the runtime sweep then doubles the window, and later
    # draws go 2x into a 1x buffer = the v2.21.0 heap-overrun shape.
    # Doubling it here is HALF the cure; the other half is 0xEC1A5CBF in
    # kDataScaledSubtreeIds so the sweep stops at the root (law 43 - the
    # pair ships together or the fix is the bug). âš  Insurance, not a
    # sighting: no session has ever logged this id, so it may never load.
    # If it never loads this entry is inert; if it does, it is born correct.
    0xEC1A5CBF,   # U-Drive-It console VARIANT (I-8c1a5c9f, 463x132, pbuff)
    # MY SIMS family (task #46 unblock, v2.22.0, user report "MySims menus
    # corrupted and crashing"): script I-aa1f1f57 (both resolution groups)
    # holds THREE top-level roots that compose via an 0x0000AAAA marker.
    # The old kNeverScaleIds deferral of 0x698894D3 tore the composition
    # apart once the sweep scaled sibling 0xCA1F1D9C - and three family
    # arts (ABB172FA/FB, 8BB230D4) were already 2x-in-place via the swept
    # Sim-mode panels, so 1x was unreachable. All three roots mark scaled;
    # runtime side un-deferred the same build. PORTRAITS are runtime-
    # generated (not in any dat) - if they tile in doubled slots, that is
    # the original deferral concern (slot-pitch code hook).
    0x698894D3,   # My Sims outer root
    0xCA1F1D9C,   # My Sims content panel
    0xAA1F1EC5,   # My Sims dialog
    # v2.22.2 CORRECTION: I-aa1f1f57 has NINE marker-composed top-level roots.
    # v2.22.0 listed the three CATALOG ones; every TGI reachable only through
    # the DETAIL roots therefore stayed "UNSCALED untouched" (13F15261 story
    # bg, 13F15260 profile bg, 0BBA7A64 actions bg, 13F15249 evict,
    # 8B7866F1 dispatch, 2BC1198A drive, CBC26C9A/B change house/job, the two
    # 42x42 {4C06F888} style thumbs, {1ABE787D,6C29491F} toggle frames - all
    # with twox_available=yes) AND the SHARED clones were retargeted only
    # inside the scaled subtrees, so the detail roots still pointed at 1x
    # originals. Doubled window + 1x art = quarter-art/black-fill.
    0xEA1F1E4D,   # Sim detail / news strip
    0x6A61E29F,   # Sim detail / profile strip
    0xABBAA2D3,   # Sim detail / actions strip
    0xEA1F1E4E,   # find-sim overlay
    0xEA1F1E5E,   # evict-confirm (v2.22.3 audit: the NINTH root - the last
                  # unlisted member of the composition; art was 1x on both
                  # its refs while eight siblings went 2x)
    # GRAPHS / data-view MIDDLE root (v2.22.3 audit): script I-6bc9065a /
    # I-ea2871aa has THREE top-level roots; 0x8A8B5B71 and 0x0A4A8176 were
    # listed but 0x8A8B5B72 (546x152, winflag_visible=yes in the A variant)
    # was not - so the sweep doubled its frame against a wholly 1x art
    # subtree (14015557 + ABBEAD86 both UNSCALED-untouched; 14015556/
    # 140155ED/14416241/144161E0 clone-retargeted only inside MARKED
    # subtrees, so this one still pointed at the 1x originals) = the
    # budget-panel black-fill signature. This is the Graphs panel the user
    # reported as broken in mayor mode.
    0x8A8B5B72,
    0xABB26B0E,   # Sim-mode left sidebar (swept live; art only - this builder
                  # never edits area=, so the ScaleGodPanelABB=0 "do not MOVE
                  # it" rule in the ini is unaffected)
    # COVERAGE-AUDIT LIVE BUG (2026-07-29 night): tool flyout columns the
    # sweep ALREADY doubles (log: "panel 0x8BB27C12 (26,772 125x249) ->
    # (52,647 250x498)", 7 windows) while ALL their art refs (ebb27830,
    # cbb16e5e/5d/5c, 0c0d45f9) were UNSCALED-untouched = black-fill live
    # today. Their 0x0000AAAA markers are also ignored by the generic
    # anchor, so PLACEMENT may still be wrong after this art fix - the dock
    # decision is separate and must be measured (MCAL/StripDump), but art
    # and runtime must move together FIRST.
    0x8BB27C12,   # tool flyout column A (script I-6bb27447)
    0xAB954023,   # tool flyout column B, twin (script I-cb95403e)
}

UI_GROUPS = ("96a006b0", "08000600")

# Font-token conversion (FONTS-AND-DIALOGS.md): the GZWinText .UI
# deserializer (VA 0x94e516) only honors GUID-valued font= tokens; string
# names silently fail to resolve, so those texts ignored the doubled
# FontStyle.ini styles. EVERY name-form token in every edited script is
# converted to its GUID using the style table itself.
FONTSTYLE_INI = os.path.join(TOOLS, "fonts", "FontStyle.candidate.ini")
FONT_NAME_RE = re.compile(r"font=([A-Za-z][A-Za-z0-9_]*)")


def load_font_guids():
    """name -> 0x-GUID from '<name> = <faces>, <size>, <params>, <GUID>'."""
    guids = {}
    with open(FONTSTYLE_INI, "r", encoding="latin-1") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith(";") or line.startswith("`") or "=" not in line:
                continue
            name, _, rest = line.partition("=")
            name = name.strip()
            m = re.search(r"(0x[0-9a-fA-F]{8})\s*$", rest.strip())
            if m and re.match(r"^[A-Za-z][A-Za-z0-9_]*$", name):
                guids[name] = m.group(1).lower()
    return guids

# ---------------------------------------------------------------------------
# CODE-BOUND art TGIs (group, instance), all type 0x856DDBAC.
# Source: tools\research\DYNAMIC-CONTROLS.md -- art bound by exe code constants,
# never referenced by any .UI script, so the reference scan above cannot see it.
# Each entry is checked against the parsed .UI refs before staging (safety):
#   - referenced by UNSCALED-only files -> CONFLICT, not staged (an in-place 2x
#     would corrupt that unscaled context);
#   - referenced by any scaled file    -> already handled by the normal
#     exclusive/shared logic, skipped here;
#   - absent from all refs             -> staged 2x in-place at the original TGI.
# ---------------------------------------------------------------------------
CODE_BOUND_TGIS = [
    # U-DRIVE-IT GAUGE NEEDLE STRIPS (2026-07-30, "split/swapped dials").
    # Bound from the VEHICLE EXEMPLARS (property 0x2BE8E6CB, binder VA
    # 0x005646AE) - never referenced by any .UI, so the reference-driven
    # pass could not reach them. All 16 distinct instances mined from the
    # 110 vehicle exemplars. WHY 2x MATTERS BEYOND CRISPNESS: the strips
    # are 2805-3740 px wide (PAST the 2048 texture-tile limit) and stock
    # only ever CELL-COPIES from them; the DLL's dst-stretch of a tiled
    # source is what produced the split/side-swapped dial. With 2x strips
    # the game's own dst = cellW math yields a pure copy again and the
    # DLL's stretch snaps to 1.0 (no stretch path at all).
    (0x46A006B0, 0xCBCBA952), (0x46A006B0, 0xCBCB6E9F),
    (0x46A006B0, 0xABEC941C), (0x46A006B0, 0xCBCBA949),
    (0x46A006B0, 0xCBCBA948), (0x46A006B0, 0x0BEB3DBF),
    (0x46A006B0, 0x0C0729AB), (0x46A006B0, 0xEBCBB93F),
    (0x46A006B0, 0xCBCBA947), (0x46A006B0, 0xAC0DA30B),
    (0x46A006B0, 0xAC0DA30C), (0x46A006B0, 0xAC0DA30D),
    (0x46A006B0, 0xAC0DA30E), (0x46A006B0, 0xCBCBA950),
    (0x46A006B0, 0x0C0729AA), (0x46A006B0, 0xCBE99A5E),
    # cSC4WinTrendBar (opinion-poll bars): groove + fill, loaded by the polls
    # controller at VA 0x7ED4AC and passed via cISC4WinTrendBar::SetImages.
    (0x46A006B0, 0x14015580),  # TrendBar groove
    (0x46A006B0, 0x14015584),  # TrendBar fill (3-band green/yellow/red)
    # ALERT BORDER SHEETS - the screen-edge frame + corner badge (task #59,
    # 2026-07-31). THREE sheets, one per state, swapped by UpdateAlertBorder
    # at VA 0x007E8A90 (called from the HUD DoMessage at 0x7F57B4 / 0x7F58A3):
    #     disaster ongoing -> 0x14315E60  RED
    #     city situation   -> 0x14315E62  GREEN
    #     simulator PAUSED -> 0x14315E61  GOLD  (badge = the pause glyph)
    # Precedence is disaster > situation > paused; with none of them the code
    # calls SetImage(NULL) and the window draws nothing.
    #
    # âš  THE FIRST TWO WERE ADDED HERE MISLABELLED AS "Mayor rating face state
    # A/B" AND THE MIDDLE SHEET WAS DROPPED - an off-by-one across a 3-sheet
    # family. That is the whole of task #59: red and green have been drawing
    # at 2x since they were staged, and ONLY the pause border stayed 1x, which
    # is why it was the only one anyone ever reported. The cited VAs were
    # right; the interpretation was not.
    #
    # WHY 2x ART IS THE ENTIRE FIX (no code, no hook). The drawer is
    # cSC4WinAlertBorder (clsid 0xCA5D3294, name string at 0x00A895FC, window
    # id 0x6A5E44B6, vtable 0x00AB5B48). Its slot-88 draw 0x00794100 carries
    # ZERO layout constants:
    #     cell = (img->Width()/3, img->Height()/3)     ; 0x79414D / 0x794161
    #     NineSlice(dst, img, &cell, &this->area, 0)   ; call 0x008D9550
    # and 0x008D9550 blits the CORNERS unstretched (only the edge runs stretch,
    # and only ALONG the run - the band thickness is still the cell). So the
    # drawn stroke thickness and the badge size are EXACTLY the art pixels:
    # 120x120 stock -> 40x40 cell -> 3px stroke / 31px badge (measured, and it
    # matches the user's "2-3px frame + ~24px badge"). At 240x240 the border
    # is 6px with a 62px badge. There is no resolution term to patch.
    #
    # Gate (not pause - a global): the byte at [pRenderProps+0x0C]+0x45C is the
    # bool render property kDisplayAlertBorders, id 0x22 (record stride 0x20,
    # value at base + 0x1C + id*0x20 = 0x45C exactly).
    (0x46A006B0, 0x14315E60),  # alert border RED   - disaster ongoing
    (0x46A006B0, 0x14315E61),  # alert border GOLD  - PAUSED (task #59)
    (0x46A006B0, 0x14315E62),  # alert border GREEN - city situation
    # REGION CITY-BUBBLE MAYOR RATING BAR (task #72, 2026-07-31, "drawn
    # twice"). cSC4WinAuraBar - clsid 0xAA5D16A9, iid IGZWinCustom, window id
    # 0x4A553000, declared 102x11 in the bubble script I-ca539340 and doubled
    # to 204x22 by our DialogStatic clone. Its art is CODE-BOUND: SetImage
    # {46a006b0,0x14416327} at VA 0x7B517E-0x7B51A7, and the instance appears
    # EXACTLY ONCE in the whole 7.87 MB image (0x7B517F) and in ZERO of the
    # 330 extracted .UI scripts - so the reference-driven pass could never see
    # it. Nine of the bubble's ten arts already ship 2x; this was the tenth.
    #
    # WHY 2x FIXES IT, from the class's own draw (vtable 0x00AB64B8 +0x160 =
    # 0x00797CC0, disassembled): the source rect's WIDTH comes from the
    # WINDOW, not the art -
    #     src.L = (imgW - winW) >> 1        (0x797D26  D1 FF  sar edi,1)
    #     src.R = winW + src.L              (0x797D57  03 CF  add ecx,edi)
    #     src.T = ftol(frac*(imgH-1)+0.5), src.B = src.T + 1
    #     dst   = the FULL window rect      (0x797D60  53     push ebx)
    # With the stock 102-wide art in the doubled 204-wide window that is
    # src.L = -51, src.R = 153: a 204-wide read across a 102-wide image, i.e.
    # TWO copies of the segment ladder. At 204x52 it becomes src.L = 0,
    # src.R = 204 - an exact 1:1 - and the row divisor (imgH-1) scales with
    # the sheet, so the fill level is unchanged. No code patch is needed or
    # wanted: nothing else in the image consumes this TGI.
    #
    # NOT the HUD bar. That one is a different subsystem (groove 0x14015549
    # + controller 0x7E86C0-0x7E8A80 with the imul-7 sites we already patch)
    # and it renders correctly - which is why the 2026-07-30 A/B with
    # RatingArrowPatch=0 changed nothing and was misread as "not ours".
    (0x46A006B0, 0x14416327),  # region bubble AuraBar sheet (102x26, 24 cells)
    # Audio Options playlist grid: per-row checkbox strip (128x16, 8 states of
    # 16x16), loaded by the audio controller at VA 0x4F4B78 / 0x4F4E37 with
    # explicit group 0x46A006B0 (the 0x1ABE787D twin is not loaded by this
    # path). Zero .UI refs (corpus-verified 2026-07-23). Instance is ONE below
    # the .UI-bound radiocheck button strip 0x14416245 (which is clone-handled
    # by dialog-static).
    (0x46A006B0, 0x14416244),  # playlist row checkbox strip
    # Restore Toolbars button (id=0x00000043): code-created by dock controller
    # at VA 0x602B00.  Icon set via SetImage with group 0x46A006B0, instance
    # 0x53244588 (4-state strip: normal/hover/pressed/disabled).  The hide
    # button (id=0x44) uses 0x13D14C10 which IS .UI-referenced and already
    # handled; the restore button is invisible to .UI scan.
    (0x46A006B0, 0x53244588),  # restore-toolbars icon (4-state)
    # U-DRIVE-IT mission bubble (task #46, user report "extremely small on
    # the map"). The in-world bubble is window 0x48E945B4 (32x32 design,
    # runtime-doubled to 64x64 by the sweep - log line exists) whose art is
    # code-bound: {46a006b0,094ac89a} pushed beside the window id at VA
    # 0x4B8314 / 0x7AC651. Emergency-Tools draw pattern (dst sized from the
    # SOURCE image), so 2x art = 2x bubble with no code hook. Zero .UI refs
    # (corpus-verified). The glyph drawn over the bubble comes from the
    # per-mission icon table at VA 0x44DEC7-0x44E268 (push inst / push
    # group / push PNG-type stanzas, 15 entries) - staged with it so the
    # glyph scales with its bubble. Safety classifier still applies to each.
    # #186 (2026-08-17): this family's ART SCALE is now PINNED at x3-of-design
    # ("fixed 96" - the 32x32 bubble ships 96x96) at EVERY tier. See the
    # MISSION_BUBBLE_FIXED96 doctrine block below CODE_BOUND_FORCE for the
    # mechanism, the excluded pair, and the four .UI-routed members the
    # classifier keeps on its own rule.
    (0x46A006B0, 0x094AC89A),  # mission bubble base (32x32)
    (0x46A006B0, 0x46A006A2),  # mission icon table @0x44DEC7
    (0x46A006B0, 0x144161EA),
    (0x46A006B0, 0x82B99D9D),
    (0x46A006B0, 0x62B99D31),
    (0x46A006B0, 0x42E55FD4),
    (0x46A006B0, 0xE78FFC90),
    (0x46A006B0, 0xC2B66DAA),
    (0x46A006B0, 0x46A006A4),
    (0x46A006B0, 0x46A006A6),
    (0x46A006B0, 0x46A006A7),
    (0x46A006B0, 0x46A006A8),
    # SIM PORTRAIT FACES (#190). The 19 named-Sim head shots, 36x41 RGB,
    # shipped TWICE in SimCity_1.dat: G=0x46A006B0 (offsets 54,714,699..
    # 54,767,511) and G=0x1ABE787D (64,502,102..64,554,914). Instance ids run
    # 0xFA8CDFBF..0xFA8CDFD2 with 0xFA8CDFCF ABSENT - 19 members, not 20;
    # 0xFA8CDFBE and 0xFA8CDFD3 are absent too, so the block is bounded.
    # Verified against all 9 shipped archives with tools\dbpf\find_tgi.py.
    #
    # WHY THE REF-MAP NEVER SAW THEM, and why that is not a ref-map bug: the
    # TGI is COMPOSED AT RUNTIME as {group, sim-exemplar-instance}. The sim
    # exemplars are type 0x6534284A group 0x6A297266, loaded at VA 0x0043B710
    # (`cmp [edi+4], 0x6a297266` at 0x0043B718 - the ONLY site of that
    # constant in .text) into 0x30-byte records; the exemplar carries a name
    # LTEXT (prop 0xCA416B3F) and the sim id (prop 0xEA296F8D) but NO image
    # property. Neither 0xFA8CDFBF nor 0xFA8CDFD2 exists as a constant
    # anywhere in the 7.87 MB image. So no .UI names them, the corpus scan
    # cannot reach them, and refmap.csv correctly holds zero rows - law 107,
    # a .UI-keyed derivation is BLIND to code-bound art. (Positive control:
    # all 431 refmap rows ARE literally present in the 330-file corpus.)
    #
    # WHY 2x-IN-PLACE CANNOT DOUBLE-APPLY (#197's trap), by arithmetic:
    # every consumer is a GZWinBMP (class vt 0x00ADF6A0) whose 36x41 slot is
    # declared in the .UI and resized by the SWEEP, never by the art.
    # GZWinBMP::SetImage (0x009BC57E) calls 0x009BC447, which sets
    # imagerect = {0,0,winW,winH} then CLAMPS it down to the image
    # (0x009BC482 / 0x009BC4A4), so src = min(win, img) and a stale crop is
    # impossible. Live BMPX captures on the 20 picker slots measure the
    # window at EXACTLY floor(v*f+0.5): 54x62 @1.5x, 72x82 @2x, 108x123 @3x.
    # Feed art of that same size and BmpCtxBltThunk computes m=f, sees
    # w*f > winW, clamps m to winW/w = 1.0, and `m > 1.001f` is FALSE - the
    # hook returns untouched. The factor is applied exactly once, by the
    # sweep, to the window.
    #
    # SHIPS WITH the find_no_snap.py CODE_BOUND entry. Without it the 1.5x
    # preview art is 60x62 against a 54x62 window and SetImage's clamp slices
    # 6 px off the right of every face - at the 1.5x tier ONLY (law 92).
    (0x46A006B0, 0xFA8CDFBF), (0x46A006B0, 0xFA8CDFC0),
    (0x46A006B0, 0xFA8CDFC1), (0x46A006B0, 0xFA8CDFC2),
    (0x46A006B0, 0xFA8CDFC3), (0x46A006B0, 0xFA8CDFC4),
    (0x46A006B0, 0xFA8CDFC5), (0x46A006B0, 0xFA8CDFC6),
    (0x46A006B0, 0xFA8CDFC7), (0x46A006B0, 0xFA8CDFC8),
    (0x46A006B0, 0xFA8CDFC9), (0x46A006B0, 0xFA8CDFCA),
    (0x46A006B0, 0xFA8CDFCB), (0x46A006B0, 0xFA8CDFCC),
    (0x46A006B0, 0xFA8CDFCD), (0x46A006B0, 0xFA8CDFCE),
    (0x46A006B0, 0xFA8CDFD0), (0x46A006B0, 0xFA8CDFD1),
    (0x46A006B0, 0xFA8CDFD2),
    (0x1ABE787D, 0xFA8CDFBF), (0x1ABE787D, 0xFA8CDFC0),
    (0x1ABE787D, 0xFA8CDFC1), (0x1ABE787D, 0xFA8CDFC2),
    (0x1ABE787D, 0xFA8CDFC3), (0x1ABE787D, 0xFA8CDFC4),
    (0x1ABE787D, 0xFA8CDFC5), (0x1ABE787D, 0xFA8CDFC6),
    (0x1ABE787D, 0xFA8CDFC7), (0x1ABE787D, 0xFA8CDFC8),
    (0x1ABE787D, 0xFA8CDFC9), (0x1ABE787D, 0xFA8CDFCA),
    (0x1ABE787D, 0xFA8CDFCB), (0x1ABE787D, 0xFA8CDFCC),
    (0x1ABE787D, 0xFA8CDFCD), (0x1ABE787D, 0xFA8CDFCE),
    (0x1ABE787D, 0xFA8CDFD0), (0x1ABE787D, 0xFA8CDFD1),
    (0x1ABE787D, 0xFA8CDFD2),
    # DEFAULT / PLACEHOLDER SIM FACES (2026-08-19). Same 36x41 shape as the 19
    # named portraits, in both the same groups, but OUTSIDE the FA8CDFBF..D2
    # block - so #190 missed them, and a sim that resolves to a default face
    # kept a 36x41 source while the named ones became 72x82.
    #
    # THAT MISMATCH IS NOT COSMETIC, it is the whole "top-left quarter"
    # defect. The category-3 indicator divides its UVs by a SINGLE texture side
    # (0x0046CCCE, which we set to NextPow2(max(36f,41f))). A 36x41 face uploads
    # into a 64 square while a 72x82 face uploads into 128, so with two source
    # sizes in play ONE immediate cannot be right for both: the 64-texture sims
    # get their UVs halved and draw magnified. Staging these makes every
    # portrait texture the same size again, which is what the single divisor
    # requires.
    #
    # LAW: IF A CONSUMER DIVIDES BY ONE TEXTURE SIZE, EVERY SOURCE IT CAN
    # BIND MUST BE THE SAME SIZE. Staging "the 19 portraits" was staging a
    # FAMILY, not a SET - the fallback members are part of the contract.
    # ARTFETCH proves the game loads these two beside the 19 (ret=0x00775239
    # and 0x00775854).
    (0x46A006B0, 0xEA32F100), (0x1ABE787D, 0xEA32F100),
    (0x46A006B0, 0xEA32F101), (0x1ABE787D, 0xEA32F101),
    # (0x46A006B0, 0xE2B66DB8) REVERTED same session (task #87): staged on the
    # law-13 inference that the news row X is a clone born at this art's size.
    # Eyes-on refuted it, and the REAL mechanism refuted the follow-up theory
    # too: the row X is not a window at all - it is an HTML <IMG> (see the
    # 1441625x block below). The strip's scripted consumers are window-fitted,
    # so the 2x copy changed nothing anywhere; reverted per the revert law.
    (0x46A006B0, 0x46A006A5),
    (0x46A006B0, 0xE2B14588),
    (0x46A006B0, 0x62B19CE9),  # mission icon table @0x44E268
] + [
    # NEWS/ADVICE ROW FURNITURE (task #87, 2026-07-31, measured end-to-end):
    # the per-headline bullet/expander/close glyphs are HTML <IMG> elements -
    # sixteen .rdata template strings at VA 0x00A83560-0x00A83820 read
    #   <IMG SRC="sc4://HTML/46a006b0/1441625X">   (X = 0..F)
    # with NO width/height attributes, so the HTML renderer draws each at its
    # art's intrinsic size: 18x18 stock = the 1x glyphs the user photographed
    # inside 2x rows (twice - the first two theories were a scrollbar and a
    # cloned button, both refuted by eyes-on; the glyph sheet is visual proof:
    # bullet / right-arrow / down-arrow / X in four severity colours).
    # HTML-only references are invisible to the .UI reference pass AND to the
    # census, which is why they were never staged. No .UI referrer exists
    # (corpus grep: zero hits), so there is no cross-referrer conflict and no
    # FORCE entry is needed. Same furniture serves the advisor briefings and
    # My Sims story rows - one range fixes the family.
    #
    # â›” PER-TIER SPLIT, AND ONLY ALONGSIDE THE CODE PATCH (task #88).
    # SIXTEEN glyphs at 1.5x/2x; TWELVE at 3x - the four X glyphs
    # (...53/57/5B/5F) ship scaled below the tier ceiling and stock above it,
    # because 83 EE ib sign-extends so the row reserve S must stay <= 127
    # (all sixteen need S=165 at 3x). Do not "complete" the range at 3x.
    #
    # âš  this comment used to say the X
    # glyphs "stay at stock 18px at EVERY tier ... a hard design constraint",
    # which was retired v2.40.0 wording contradicted by the v2.40.2 block ~25
    # lines below AND by the shipped counts (655/655/651). Two contradicting
    # comments in one file is how a future session picks the wrong one.
    #
    # WHY THE X USED TO VANISH. cSC4WinAdviceList::Refresh (0x00793810) is the
    # single emitter for every advice list in the game. It writes each row as
    # a three-column HTML table:
    #     <TR><TD WIDTH="18">arrow</TD>
    #         <TD WIDTH="%d">headline</TD>            %d = pane->GetW() - 61
    #         <TD WIDTH="18"><A HREF=...close...>X</A></TD></TR>
    # 61 = 18 + 18 + a flat 25px reserve, so the declared total is always
    # GetW() - 25. Column width is the MEASURED cell rect, not the declared
    # one (declared WIDTH= lands in col+0x08/+0x0C, which the distribution
    # loop never reads), and a container's rect is the UNION of its children
    # with no clamp - so a 36px <IMG> really does grow its cell. The arrow
    # column then eats the 25px reserve and the X cell lands past the pane's
    # content edge. That is why reverting only the X glyphs did nothing: the
    # excess came from the ARROW column, and the X is simply last in the row.
    #
    # THE CURE, shipped with these entries: CodePatches::ApplyAdviceRowScale
    # rewrites the 61 to round(18*f) + 43, restoring the declared total to
    # the stock GetW() - 25 by taking the arrow's extra width out of the
    # HEADLINE column instead of out of the X's position.
    #
    # SIXTEEN AT <=2x, TWELVE AT 3x - AND THE SPLIT IS FORCED BY AN ENCODING
    # CEILING, NOT BY TASTE (v2.40.2). `83 EE ib` sign-extends its imm8, so
    # the subtrahend must stay <= 127:
    #     X at stock 18: S = round(18f) + 18 + 9 + round(16f)
    #                      = 61 / 78 / 95 / 129*   (1x / 1.5x / 2x / 3x)
    #     X scaled too:  S = 2*round(18f) + 9 + round(16f)
    #                      = 61 / 87 / 113 / 165   -> 3x cannot be encoded
    # Both forms declare the SAME row total (W - 9 - round(16f)), so scaling
    # the X changes only how the width is divided between the X and the
    # headline - it cannot affect whether the row fits. That is why the
    # bigger X is safe to ship at the tiers whose S is encodable.
    # A 36px dismiss X is a real click target at 3x; an 18px one is
    # not, and this is a touch mod.
    # `* 129 clamps to 127 at 3x (~2px of X clipped, logged).
    #
    # âš  THE DLL MIRRORS THIS EXACT RULE - CodePatches::ApplyAdviceRowScale
    # scales its X column iff factor <= 2.0. If you change the condition
    # here, change it there in the SAME build or the budget and the art
    # disagree and the X is clipped again.
    #
    # âš  HARD COUPLING - ART AND PATCH SHIP TOGETHER AND REVERT TOGETHER. If
    # ApplyAdviceRowScale is ever removed, disabled, or logs a skip on this
    # exe, these entries must come out in the SAME build. Art without the
    # patch is precisely the task-#88 defect.
    (0x46A006B0, i) for i in range(0x14416250, 0x1441625F + 1)
    # #136 (2026-08-05): the `or FACTOR <= 2.0` tail is GONE. It existed
    # only because the row's width budget lived in a sign-extended imm8
    # that could not encode S=165 at 3x. CodePatches now re-encodes that
    # window to `lea esi,[eax-imm32]` when it must, so every tier can
    # carry the scaled X and 3x ships the same 655 entries as 1.5x/2x.
    # âš  STILL A HARD COUPLING, just with a different condition: if the
    # wide re-encode is ever removed or starts logging REFUSED, this
    # filter has to come back in the SAME build or the X clips again.
    if True
] + [
    # News window + advisor panels: art bound by TGI constants in code at
    # VA 0x77A495-0x77A837 and 0x780952-0x78910C (DYNAMIC-CONTROLS.md Q4 bonus
    # finding: instances 0x140155b4..0x140155f7 incl. c8, cb, cc, d0-d7).
    # Instances in this span that ARE .UI-referenced are filtered out by the
    # safety check; instances with no 2x asset are reported missing.
    (0x46A006B0, i) for i in range(0x140155B4, 0x140155F7 + 1)
] + [
    # MASTER BUDGET BAND FAMILY (2026-07-30, v2.26.1 - user report: "the
    # subflyouts you get to using the eye are not scaled"). The eye icon on
    # a budget category opens Master Power / Master Police / Master Fire /
    # ... - built by the third band stacker sub_77A960 (caller 0x786C83)
    # from a 650-wide art family that sits OUTSIDE the 0x140155xx span
    # above, so every earlier art pass missed it. Per the decoded engine
    # (BUDGET-DETAIL-ANATOMY.md) a dialog's W/H is the SUM OF ITS BAND ART
    # SIZES: unstaged 1x bands = a 1x-sized window holding 2x text, which
    # is exactly the reported overlap. Staging these five at 2x resizes the
    # whole dialog with no code hook, the same way D0-D7 fixed the
    # departments. CB=header 650x23, CC=slab 650x36, CD=cap 650x41,
    # CE=footer 650x40, CF=title 650x29.
    (0x46A006B0, 0x2BFEB0CB), (0x46A006B0, 0x2BFEB0CC),
    (0x46A006B0, 0x2BFEB0CD), (0x46A006B0, 0x2BFEB0CE),
    (0x46A006B0, 0x2BFEB0CF),
] + [
    # HTML-page art referenced by sc4://image/<group>/<instance> URLs inside
    # LTEXT story/tutorial resources (SimCityLocale.DAT, harvested 2026-07-29
    # into html-image-refs.txt by the task #42 news work; 0x14416264
    # html_TextBG_General alone backs 188 pages). Rendered by the HTML engine
    # whose text the DLL now scales (CodePatches::ApplyHtmlSizeScale) - the
    # backgrounds must scale with it. Same safety filtering as above.
    (int(g, 16), int(i, 16))
    for g, i, _n in (
        line.split()
        for line in open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                      "html-image-refs.txt"), encoding="ascii")
        if line.strip() and not line.startswith("#")
    )
] + [
    # THE ENTIRE 42x42 THUMBNAIL GROUP 0x4C06F888 (task #55/#47, 2026-07-29
    # night "picker icons duplicated" + "car/bike pictures don't fill").
    # 112 entries, all type 0x856DDBAC, all in SimCity_1.dat (archive index
    # scanned with tools\dbpf\find_tgi.py - no other archive carries the
    # group under ANY type). The U-Drive-It vehicle/ped picker cells are
    # GZWinBMP placeholders whose .UI image= {46a006b0,ea32f104} /
    # {46a006b0,6b998f30} is DANGLING (present in NO shipped archive): the
    # picker binder at VA 0x76FDB0 QIs child 0x23450000+i (iid 0xC12CEA13 =
    # GZWinBMP) and SetImages {0x4C06F888, <vehicle-exemplar property
    # 0xEBFC5E5E>} through loader 0x602B70 - the same code-bound shape as
    # the gauge strips. Staging the WHOLE group beats mining the property:
    # it covers every instance any binder can pick. Corpus-verified: the
    # only .UI refs to this group are the two My Sims style thumbs inside
    # already-scaled subtrees (the classifier resolves those as EXCLUSIVE
    # on their own), so in-place 2x is collision-free.
    (0x4C06F888, int(row.split(",")[2], 16))
    for row in open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 "..", "dbpf", "extracted-png-tgi.csv"),
                    encoding="ascii")
    if ",0x4C06F888," in row
]

# TGIs that must be staged 2x in-place at the ORIGINAL TGI even when the
# normal shared/exclusive logic would handle them via a clone.  This is
# needed for code-created controls that load the original TGI at runtime
# and cannot be retargeted to a clone IID.  Unscaled .UI buttons that
# share these TGIs typically use fill=yes, so the 2x art is downscaled
# to fit their 1x slots (acceptable visual result).
CODE_BOUND_FORCE = {
    (0x46A006B0, 0x53244588),  # restore-toolbars icon: code-created button
    # 0xE2B66DB8 was here for one build (task #82/#87) on the inference that
    # the news row X is a clone born at that art's size. TWICE refuted by
    # eyes-on: the row X is an HTML <IMG> (see the 1441625x CODE_BOUND range),
    # not a window. Reverted per the revert law.
}

# ---------------------------------------------------------------------------
# #186 - U-DRIVE-IT MISSION BUBBLE: PIN THE FAMILY'S ART AT x3-OF-DESIGN
# ("FIXED 96"), EVERY TIER. USER DECISION 2026-08-17: "all tiers, grow for
# clickability".
#
# THE f-SQUARED COMPOUNDING (measured at 2x, scoped 2026-08-17): the in-world
# bubble window 0x48E945B4 is a code-created GZWinBMP BORN at its bound art's
# size, then swept x f like any window, and the BMPX draw sizes the dest from
# the SOURCE image scaled by f, reduced until it fits the live window
# (UiSpike.cpp kBmpxCityRoots, task #60: 64px staged art measured live in a
# 128x128 window at the 2x tier). So on-screen = artPx x f, and TIER art
# (artPx = 32f) compounds to 32f^2:
#   tier art:  48/64/96  -> on-screen  72/128/288  (1.5x/2x/3x)
#   fixed 96:  96/96/96  -> on-screen 144/192/288  - grow-or-keep at every
#                                                    tier, uniform x3 relation
# The 2x tier ALREADY runtime-stretches its art x2 (64 art in a 128 window,
# user-confirmed look), so the stretch-quality relation is the accepted
# baseline; the 3x tier is byte-for-byte UNCHANGED by this pin (see below).
#
# LAW 64 - REGENERATE FROM PRISTINE, NEVER RESIZE A RESIZED: the family is
# built from the 1x extract by the CANONICAL resampler (Upscale2x.exe with
# the Rebuild-Corpus.ps1 flag set) at the FIXED factor 3, whatever tier is
# being built - build_mission_bubble_fixed96(). At integer f=3 every list
# treatment and --smooth-unkeyed refuse themselves, so the output is the
# plain NN corpus product - VERIFIED byte-identical to preview-3x\ for all 13
# members (2026-08-17). Consequences worth stating out loud:
#   * all three tier packages carry the SAME family bytes;
#   * the 3x package's family payloads DO NOT change (it already ships 96);
#   * only the 1.5x and 2x packages differ - 9 pinned entries each.
#
# COMPANION GATES THAT MOVE WITH THIS PIN (recorded in REGRESSION.md #186):
#   * Test-DatIntegrity.ps1's #100 bubble payload assertion expects
#     32*factor per tier and MUST be re-pointed to fixed 96 in the same
#     batch, or it goes red on a correct build;
#   * two family sheets are KEYED (e78ffc90: 12 exact-key px, 46a006a5:
#     879), so the #181 key gate runs the pinned members at their OWN
#     producing factor - see the gate split at the pack step.
#
# MEMBERSHIP = the mission-bubble block in CODE_BOUND_TGIS above, minus the
# deliberate exclusions. The classifier still routes each member (the block's
# own words: "Safety classifier still applies to each"), and the #186 routing
# gate in main() FATALs if the routing ever drifts from the ledger below.
# Dims in the comments are informational; the CODE measures each 1x source
# and demands output == 3 x measured, never assuming 32.
# #197 (2026-08-18): WAS 3 - a flat 3x overshoot at every tier, because the
# window is BORN at the art's pixel size and the sweep then multiplies it by f
# again (on-screen = 32*a*f). The user's rule is that scale must equal the
# factor exactly, so the art multiplier is now the FACTOR itself and the
# window is excluded from the sweep (0x48E945B4 in kNeverScaleIds). Art scaled
# offline + window never swept is the DialogStatic pattern; it yields 32*f
# exactly AND keeps the art crisp, which a=1 would not.
# BOTH HALVES OR NEITHER. Art-at-f without the never-scale entry restores
# the pre-#186 f-squared state; never-scale without art-at-f pins it at 1x.
MISSION_BUBBLE_FIXED96_MULT = FACTOR   # = f: 48 / 64 / 96 px on the 32px base
# ONE SHEET, NOT THE FAMILY (adversarial review 2026-08-17, finding 1 -
# the reviewer RENDERED the candidates). The other twelve "family" members
# are the engine's CLASS-DEFAULT WIDGET sheets registered at VA 0x44DEC7:
# checkbox/radio strips (46a006a2), dropdown arrows (62b99d31), message-box
# severity icons (42e55fd4), edit-field background (e78ffc90), the VERTICAL
# SLIDER track (46a006a8 - the twin of the 46a006a7 the #60 block excludes
# BY NAME), the file-browser icon row (46a006a5), and window chrome
# (62b19ce9). They carry zero .UI refs because CLASS-DEFAULT ART IS
# REGISTERED, NOT REFERENCED - their consumers are still tier-sized, so a
# 3x pin breaks message boxes / Load-Save / sliders at 1.5x AND 2x. "No .UI
# refs" was the wrong membership test; the ONLY sheet whose consumer is the
# bubble window itself is the base the #100 hazard analysis and the
# Test-DatIntegrity #100 gate already treat as THE bubble size lever.
# CONTINGENCY, stated up front: #60-era notes record one old attempt where
# overriding 094AC89A alone "did not move the marker". If the eyes-on BMPX
# line still reads img 48x48 after this pin, the binding is another sheet
# and the log names it - iterate from the measurement, never re-widen this
# set on inference.
MISSION_BUBBLE_FIXED96 = {
    (0x46A006B0, 0x094AC89A),  # bubble base 32x32 -> 96x96
}
# EXCLUDED - NOT in the set above, and the guard below keeps it that way:
# 46A006A4 and 46A006A6 carry UNSCALED-only .UI refs (refmap: aa5e60d1.ui /
# ebd0d36c.ui), so the classifier conflict-skips them from code-bound staging
# and pinning them would break those consumers. They stay the known
# possibly-small glyphs for whichever mission types use them.
MISSION_BUBBLE_FIXED96_EXCLUDED = {
    (0x46A006B0, 0x46A006A4),
    (0x46A006B0, 0x46A006A6),
}
# .UI-ROUTED - family members the classifier hands to the .UI logic, NOT to
# code-bound staging, so the fixed-96 pin structurally cannot reach them (and
# must not: their scripted consumers size to TIER windows - task #60's own
# warning that doubling shared glyph art "would resize every spinner/slider
# in the game"; per UiSpike.cpp:11214 the "15-entry glyph table" at VA
# 0x44DEC7 is in fact a REGISTRATION table for spinner/slider art, so these
# four may never draw on a bubble at all - eyes-on adjudicates). Measured
# 2026-08-17 against refmap-15x.csv:
#   144161EA  EXCLUSIVE, 4 refs in scaled 6bc61f19.ui (Building Style panel);
#             also a cell-strips.txt 4-state member -> tier 2x-in-place
#   82B99D9D  EXCLUSIVE, 24 refs in 3 scaled files (spinner arrow strip)
#             -> tier 2x-in-place
#   46A006A7  SHARED, 2 scaled + 16 unscaled files (slider art) -> clone for
#             the scaled refs; the ORIGINAL TGI stays STOCK for the unscaled
#   E2B14588  EXCLUSIVE, 1 ref in the G-08000600 twin 2bc90671.ui
#             -> tier 2x-in-place
# Their mission glyphs (if any) therefore stay tier-sized (A7's stays stock)
# - ledgered with A4/A6 in REGRESSION.md #186.
# REDUCED with the set above (review finding 1): the routed four never
# belonged to a "bubble family" either - they are widget art whose scripted
# consumers already size to tier windows. Kept as an EMPTY ledger so the
# subset guard below still parses; the class-default widget sheets
# (46a006a2/62b99d31/42e55fd4/e78ffc90/46a006a8/46a006a5/62b19ce9/c2b66daa)
# stay on plain tier-scaled code-bound staging exactly as before #186.
MISSION_BUBBLE_FIXED96_UI_ROUTED = set()
if MISSION_BUBBLE_FIXED96 & MISSION_BUBBLE_FIXED96_EXCLUDED:
    sys.exit("FATAL #186: excluded mission-bubble glyph(s) %s in the fixed-96 "
             "override set - 46A006A4/46A006A6 have unscaled .UI consumers "
             "and must never ride the pin."
             % ", ".join("%08x/%08x" % t for t in sorted(
                 MISSION_BUBBLE_FIXED96 & MISSION_BUBBLE_FIXED96_EXCLUDED)))
if not MISSION_BUBBLE_FIXED96_UI_ROUTED <= MISSION_BUBBLE_FIXED96:
    sys.exit("FATAL #186: the UI-routed ledger names TGIs outside the "
             "fixed-96 family - fix the ledger, it has no authority to "
             "invent members")


class Node:
    __slots__ = ("clsid", "wid", "images", "imagerect", "edgeimage",
                 "children", "parent", "tag_start", "tag_end", "scaled")

    def __init__(self):
        self.clsid = None
        self.wid = None            # id=0x........ or None
        self.images = []           # list of (gid, iid, val_start, val_end) abs offsets of "{...}"
        self.imagerect = None      # ((l,t,r,b), val_start, val_end) abs offsets of "(...)"
        self.edgeimage = None
        self.children = []
        self.parent = None
        self.tag_start = 0
        self.tag_end = 0
        self.scaled = False


ATTR_NAME_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def fresh_dir(path):
    """Ensure an EMPTY directory at path, without removing the directory.

    These trees live under OneDrive, which keeps a handle on folders: a plain
    shutil.rmtree deletes the files and then fails with WinError 5 on the
    rmdir. Clearing the contents in place is equivalent for our staging use
    and cannot fail that way.
    """
    if not os.path.isdir(path):
        os.makedirs(path)
        return
    for entry in os.listdir(path):
        p = os.path.join(path, entry)
        if os.path.isdir(p):
            shutil.rmtree(p, ignore_errors=True)
        else:
            os.remove(p)


def double_subtree_areas(text, root_id_hex, scale_fn):
    """Scale area=(l,t,r,b) on every DESCENDANT of one root window.

    Used where the game reads a child's geometry BEFORE any runtime sweep can
    run (advisor 3D head framing, task #43): the child geometry must already
    be scaled in the DATA. Returns (new_text, n_edits). The root's own area is
    NOT touched - the DLL still scales the root at runtime so its HUD
    anchoring is preserved (see kDataScaledSubtreeIds in UiSpike.cpp).

    VERIFIED EXACT (2026-07-29): every child of the advisor strip in a live
    2x dump equals 2 x its design area, e.g. face button design
    (309,35,364,129) -> live pos(618,70) size 110x188; hidden marker
    (229,63,257,91) -> pos(458,126) 56x56; title BMP (286,6,832,136) ->
    pos(572,12) 1092x260. So this transform reproduces the runtime result.
    """
    m = re.search(r"<LEGACY[^>]*\sid=0x%s\b[^>]*>" % root_id_hex, text, re.I)
    if not m:
        return text, 0, 0
    cs = text.find("<CHILDREN>", m.end())
    if cs == -1:
        return text, 0, 0
    depth = 0
    i = cs
    end = -1
    while True:
        nxt_open = text.find("<CHILDREN>", i)
        nxt_close = text.find("</CHILDREN>", i)
        if nxt_close == -1:
            break
        if nxt_open != -1 and nxt_open < nxt_close:
            depth += 1
            i = nxt_open + len("<CHILDREN>")
        else:
            depth -= 1
            i = nxt_close + len("</CHILDREN>")
            if depth == 0:
                end = nxt_close
                break
    if end == -1:
        return text, 0, 0

    n = [0]
    nleaf = [0]
    span_text = text[cs:end]

    def rep_tag(mt):
        tag = mt.group(0)
        # ALIGNMENT MARKERS (id 0x0000AAAA) are POSITIONING DATA, not
        # geometry: the game computes the panel's placement as
        # anchor - markerDesignOffset IN NATIVE UNITS (the flyout
        # alignment-marker law). Doubling the strip's marker (229,63)
        # shifted the whole Advisors box by exactly -(229,63) - proven
        # live 2026-07-29 (native pos (209,1412) -> (-20,1349)). Leave
        # markers at 1x; the runtime root-scale doubles the RESULTING
        # position, as it always did.
        if re.search(r"\sid=0x0000aaaa\b", tag, re.I):
            return tag

        # #170: AN ART LEAF IS SIZED AS A LENGTH, NOT BY ITS EDGES.
        #
        # Scaling all four coordinates independently makes a child's SIZE
        # depend on its POSITION: at f=1.5 an odd left edge with an even right
        # edge loses the half pixel, `R(r*f) - R(l*f)` = 82 where the art cell
        # is `R(w*f)` = 83. The seven advisor buttons (x2 HUD scripts) are all
        # at odd left edges, which is why the whole row broke and why the user
        # saw a break on the RIGHT of every icon - the art cell and the window
        # disagreed by exactly one column.
        #
        # This is #148's leaf rule, already live in `ScaleSubtree` since
        # v2.94.1 and in `build_dialog_static.py::leaf_art_sized` since #155.
        # It never reached HERE, and here is the one place it is not optional:
        # a pre-scaled subtree is in `kDataScaledSubtreeIds`, so
        # `ScalePanelRoot` RETURNS before it walks the children
        # (UiSpike.cpp:14557) and nothing downstream repairs the number we
        # write. Law 75 - when a cure lands in one path, name every other path
        # that needs it.
        #
        # SCOPE is the same predicate as #155, and deliberately not "every
        # leaf": a node with NO CHILDREN, an `image={g,i}`, and NO
        # `imagerect`. Those are exactly the windows whose size the art
        # dictates. A node with children is a panel whose edges are
        # load-bearing (that is what edge-derived protects, and #143's white
        # seams are the failure mode); an `imagerect` crop is registered
        # against the node's own l,t and scales with the art already.
        #
        # POSITION NEVER MOVES - only the extent, by at most one pixel. The
        # reverted parity nudge (below) moved things and was judged by its
        # densest neighbourhood; this is the lever that comment names instead.
        #
        # PROVABLE NO-OP AT AN INTEGER FACTOR: scale_fn(v) = v*N exactly, so
        # N*l + N*(r-l) == N*r identically. 2x and 3x cannot move, and
        # `gate_btn_undercover.py` asserts it (0 mismatched at 2x and 3x).
        rest = span_text[mt.end():]
        art_leaf = (not rest.lstrip().startswith("<CHILDREN>")
                    and RE_N_IMAGE.search(tag) is not None
                    and RE_N_RECT.search(tag) is None)

        def rep(mm):
            n[0] += 1
            l, t, r, b = (int(x) for x in mm.group(1, 2, 3, 4))
            if art_leaf:
                nl, nt = scale_fn(l), scale_fn(t)
                na = (nl, nt, nl + scale_fn(r - l), nt + scale_fn(b - t))
                if na != (nl, nt, scale_fn(r), scale_fn(b)):
                    nleaf[0] += 1
                return "area=(%d,%d,%d,%d)" % na
            vals = [scale_fn(l), scale_fn(t), scale_fn(r), scale_fn(b)]
            return "area=(%d,%d,%d,%d)" % tuple(vals)

        return re.sub(r"area=\((-?\d+),(-?\d+),(-?\d+),(-?\d+)\)", rep, tag)

    span = re.sub(r"<LEGACY[^>]*>", rep_tag, span_text)
    if nleaf[0] and FACTOR == math.floor(FACTOR):
        sys.exit("FATAL: the #170 art-leaf size rule changed %d area(s) at "
                 "integer factor %g under root 0x%s - it MUST be a no-op there"
                 % (nleaf[0], FACTOR, root_id_hex))
    return text[:cs] + span + text[end:], n[0], nleaf[0]


# ---------------------------------------------------------------------------
# SEAT A CHILD ON ITS FRAME'S MEASURED ART APERTURE  (#152, 2026-08-09)
#
# THE LAW THIS EXISTS FOR - it is closed form, and it predicts WHICH AXIS
# breaks on WHICH panel:
#
#     For f = p/q in lowest terms, edge-derived rounding preserves a child's
#     1x offset d from its frame IFF q | d.
#         round((t+d)*f) - round(t*f) == d*f  exactly when d*f is an integer;
#         otherwise it depends on the PARITY of the frame's own coordinate t.
#     At f = 1.5, q = 2: EVEN offsets are always safe, ODD offsets are a
#     lottery on t. At an integer factor q = 1, so EVERY offset is safe -
#     which is the whole reason 2x and 3x have never shown any of this.
#
# Verified on three panels, and it called the axis right every time:
#     advisor faces     offset (2,1)  x even safe, y ODD  -> 1px HIGH
#     My Sim picker     offset (3,2)  x ODD  fails, y even -> 1px LEFT
#     advisor detail    offset (2,2)  both even            -> never fails
# The two defects read on screen as "high" and "left" respectively.
#
# THE ANCHOR IS THE FRAME; THE SAFETY NET IS THE MEASURED APERTURE. Not parity,
# not floor(), not containment detection. Rejected alternatives, measured:
#     ungated anchored rule inside double_subtree_areas -> moves 456 dashboard
#         windows (up to 2px) and 3 in the live balance bar. REJECT.
#     floor() for positions -> moves 373/531 budget+graphs, 718/957 dashboard,
#         26 row-pitch changes. REJECT - worst available.
# Both would have broken the Monthly Budget, which the report describes fixed.
#
# TRANSLATES ONLY. Width and height are never touched, and the delta is
# capped at 1px (G5) - #148's lesson that a fix which MOVES things is judged by
# its densest neighbourhood. This one moves 14 windows, all in two files.
_SEAT_AREA = r"area=\((-?\d+),(-?\d+),(-?\d+),(-?\d+)\)"

# (face id, frame id, art group, art instance, 1x offset). The SAME 7 ids
# appear in both advisor scripts. All 14 occur EXACTLY ONCE in exactly 2 of the
# 330 corpus scripts - counted, not assumed - so even an unscoped application
# would touch nothing protected.
ADVISOR_FACE_SEATS = [
    (0x0A15C7D8, 0xCA15C7CF, 0x46A006B0, 0x14015571, (2, 1)),
    (0xEA15C7FA, 0x2A15C7F1, 0x46A006B0, 0x14015570, (2, 1)),
    (0x8A15C80C, 0x8A15C802, 0x46A006B0, 0x14015573, (2, 1)),
    (0x4A15C7C6, 0x6A15C7BE, 0x46A006B0, 0x14015574, (2, 1)),
    (0x6A15C7B5, 0x6A15C7AA, 0x46A006B0, 0x14015576, (2, 1)),
    (0x6A15C7EA, 0xAA15C7E2, 0x46A006B0, 0x14015575, (2, 1)),
    (0x0A15C7A1, 0xAA15C795, 0x46A006B0, 0x14015572, (2, 1)),
]


def _seat_one_tag(text, wid):
    """The ONLY tag carrying this id, or FATAL. Ids are NOT keys in general -
    0x0000AAAA appears 3x and 0x6A15C782 twice in these very files - so this
    asserts uniqueness rather than trusting it."""
    pat = re.compile(r"<LEGACY[^>]*\sid=0x%08x\b[^>]*>" % wid, re.I)
    hits = pat.findall(text)
    if len(hits) != 1:
        sys.exit("FATAL seat: id 0x%08X occurs %d times (need exactly 1)"
                 % (wid, len(hits)))
    m = pat.search(text)
    ma = re.search(_SEAT_AREA, m.group(0))
    if not ma:
        sys.exit("FATAL seat: id 0x%08X has no area=" % wid)
    return m, tuple(int(x) for x in ma.groups())


def _seat_aperture_state0(stage_dir, gid, iid, nstates=4):
    """Interior transparent hole of the state-0 cell of the sheet WE SHIP.

    Flood-fills the OUTSIDE transparency from the border, so what remains is
    the enclosed hole the portrait shows through. Same build-time pixel read
    that neutralize_dock_recess() already does."""
    names = [tgi_png_name(gid, iid), tgi_png_name(gid, iid ^ CLONE_XOR)]
    hits = [n for n in names if os.path.isfile(os.path.join(stage_dir, n))]
    if not hits:
        return None, None
    w, h, px, _ = _png_read_rgba(os.path.join(stage_dir, hits[0]))
    cw = w // nstates
    tr = [[px[(y * w + x) * 4 + 3] < 32 for x in range(cw)] for y in range(h)]
    seen = [[False] * cw for _ in range(h)]
    st = [(x, y) for x in range(cw) for y in (0, h - 1) if tr[y][x]]
    st += [(x, y) for y in range(h) for x in (0, cw - 1) if tr[y][x]]
    for (x, y) in st:
        seen[y][x] = True
    while st:
        x, y = st.pop()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < cw and 0 <= ny < h and tr[ny][nx] and not seen[ny][nx]:
                seen[ny][nx] = True
                st.append((nx, ny))
    pts = [(x, y) for y in range(h) for x in range(cw)
           if tr[y][x] and not seen[y][x]]
    if not pts:
        return None, (cw, h)
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return (min(xs), min(ys), max(xs) - min(xs) + 1,
            max(ys) - min(ys) + 1), (cw, h)


def seat_faces_on_apertures(text, seats, stage_dir, fn):
    """Seat a child on its frame's MEASURED ART APERTURE instead of on its own
    independently-rounded edge. Run AFTER double_subtree_areas.

    Every guard below FAILS THE BUILD rather than degrading quietly: if the art
    ever moves, this must stop, not silently seat a face onto a hole that is no
    longer there.
    """
    moved = []
    for (face_id, frame_id, gid, iid, off1x) in seats:
        _, fr = _seat_one_tag(text, frame_id)
        mfa, fa = _seat_one_tag(text, face_id)
        frw, frh = fr[2] - fr[0], fr[3] - fr[1]
        faw, fah = fa[2] - fa[0], fa[3] - fa[1]
        ap, cell = _seat_aperture_state0(stage_dir, gid, iid)
        if ap is None:
            sys.exit("FATAL seat 0x%08X: no interior aperture in staged sheet "
                     "0x%08X/0x%08X (cell %s) - art moved or is not staged"
                     % (face_id, gid, iid, cell))
        cw, ch = cell
        want_off = (scale_len(off1x[0]), scale_len(off1x[1]))
        # G1 the ART's aperture is where the art says it is - and the FLOOD FILL
        #    is the authority, not ScaleRound. ScaleRound is the sanity bound.
        #
        #    RELAXED 2026-08-14 (#156), deliberately, with the reason:
        #    cell-aligned sampling scales each STATE from its own cell, so a
        #    55px cell becomes 83 (not 82.5) and source column 2 first appears
        #    at output 4 where the old global map put it at 3. The art is
        #    correct; the exact-equality model described the OLD sampler. A
        #    guard that encodes one sampler's rounding will fire on every
        #    future sampler change whether or not anything is wrong.
        #    Still FATAL beyond one pixel: that is the #151 class (a sampler
        #    that re-times the sheet), which must never pass silently.
        if abs(ap[0] - want_off[0]) > 1 or abs(ap[1] - want_off[1]) > 1:
            sys.exit("FATAL seat 0x%08X: aperture origin %s != "
                     "ScaleRound(%s,%g)=%s"
                     % (face_id, ap[:2], off1x, FACTOR, want_off))
        # G2 UNIT SOUNDNESS: only compare art ROWS to window ROWS when the cell
        #    height EQUALS the window height (141==141 at 1.5x; exact at 2x/3x).
        #    Without this the y arithmetic is comparing two different spaces.
        if ch != frh:
            sys.exit("FATAL seat 0x%08X: art cell h %d != frame window h %d - "
                     "y is not 1:1, an aperture row is not a window row"
                     % (face_id, ch, frh))
        # G3 the x squeeze is at most 1px over the whole cell (83->82 at 1.5x),
        #    below one pixel of aperture offset under floor OR centre sampling.
        if not 0 <= cw - frw <= 1:
            sys.exit("FATAL seat 0x%08X: art cell w %d vs frame window w %d - "
                     "x squeeze outside [0,1]" % (face_id, cw, frw))
        # G4 the face is sized to the hole.
        if (ap[2], ap[3]) != (faw, fah):
            sys.exit("FATAL seat 0x%08X: aperture %dx%d != face %dx%d"
                     % (face_id, ap[2], ap[3], faw, fah))
        d = (fr[0] + want_off[0] - fa[0], fr[1] + want_off[1] - fa[1])
        if d == (0, 0):
            continue                    # INTEGER TIER: NOTHING IS WRITTEN
        # G5 a seat, never a nudge (#148).
        if abs(d[0]) > 1 or abs(d[1]) > 1:
            sys.exit("FATAL seat 0x%08X: delta %s exceeds 1px" % (face_id, d))
        new = (fa[0] + d[0], fa[1] + d[1], fa[2] + d[0], fa[3] + d[1])
        newtag = re.sub(_SEAT_AREA, "area=(%d,%d,%d,%d)" % new,
                        mfa.group(0), count=1)
        text = text[:mfa.start()] + newtag + text[mfa.end():]
        moved.append((face_id, fa[:2], new[:2], d))
    return text, moved


def double_one_window_area(text, win_id_hex, scale_fn):
    """Scale area=(l,t,r,b) on ONE window, by id. Returns (new_text, n_edits).

    Narrower sibling of double_subtree_areas, added 2026-08-01 (task #89).
    That function needs a matching kDataScaledSubtreeIds entry, which makes
    ScalePanelRoot RETURN EARLY at the root - and for the HUD dock that also
    stopped the god/mayor flyout DOCKING that runs inside the child recursion,
    breaking every flyout (v2.41.1, reverted same session).

    A single window instead pairs with kDataScaledWindowIds: the sweep skips
    only that window and keeps walking, so no sibling behaviour changes.

    Position is included on purpose: `area=` is PARENT-RELATIVE, and the sweep
    scales a child's l/t by the same factor, so pre-doubling here reproduces
    exactly what the sweep would have produced.
    """
    n = [0]

    def rep_tag(mt):
        tag = mt.group(0)
        if not re.search(r"\sid=0x%s\b" % win_id_hex, tag, re.I):
            return tag

        def rep(mm):
            n[0] += 1
            vals = [scale_fn(int(x)) for x in mm.group(1, 2, 3, 4)]
            return "area=(%d,%d,%d,%d)" % tuple(vals)

        return re.sub(r"area=\((-?\d+),(-?\d+),(-?\d+),(-?\d+)\)", rep, tag)

    return re.sub(r"<LEGACY[^>]*>", rep_tag, text), n[0]


def parse_tag_attrs(text, tag_start, tag_end, node):
    """Parse attributes inside one <LEGACY ...> tag. Offsets are absolute."""
    i = tag_start + len("<LEGACY")
    end = tag_end - 1  # position of the closing '>'
    while i < end:
        ch = text[i]
        if ch in " \t\r\n":
            i += 1
            continue
        m = ATTR_NAME_RE.match(text, i)
        if not m:
            i += 1
            continue
        name = m.group(0)
        i = m.end()
        if i >= end or text[i] != "=":
            continue  # bare token, not name=value
        i += 1
        # value
        if i < end and text[i] == '"':
            j = text.index('"', i + 1)
            i = j + 1
            continue  # quoted values (captions/tips) never carry image data
        vstart = i
        while i < end and text[i] not in " \t\r\n":
            i += 1
        vend = i
        val = text[vstart:vend]
        if name == "id" and val.startswith("0x"):
            try:
                node.wid = int(val, 16)
            except ValueError:
                pass
        elif name == "clsid":
            node.clsid = val
        elif name == "image" and val.startswith("{") and val.endswith("}"):
            inner = val[1:-1].split(",")
            if len(inner) == 2:
                try:
                    gid = int(inner[0], 16)
                    iid = int(inner[1], 16)
                    node.images.append((gid, iid, vstart, vend))
                except ValueError:
                    pass
        elif name == "imagerect" and val.startswith("(") and val.endswith(")"):
            try:
                nums = tuple(int(x) for x in val[1:-1].split(","))
                if len(nums) == 4:
                    node.imagerect = (nums, vstart, vend)
            except ValueError:
                pass
        elif name == "edgeimage":
            node.edgeimage = val


def parse_ui(text):
    """Parse LEGACY markup -> list of root Nodes. Character scan, quote-aware."""
    roots = []
    stack = []          # parents whose <CHILDREN> block we're inside
    last_control = None
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch == "#" and (i == 0 or text[i - 1] == "\n"):
            j = text.find("\n", i)
            i = n if j < 0 else j + 1
            continue
        if ch == "<":
            if text.startswith("<LEGACY", i):
                # find matching '>' outside quotes
                j = i + 7
                inq = False
                while j < n:
                    c = text[j]
                    if c == '"':
                        inq = not inq
                    elif c == ">" and not inq:
                        break
                    j += 1
                if j >= n:
                    raise ValueError("unterminated <LEGACY tag at offset %d" % i)
                node = Node()
                node.tag_start, node.tag_end = i, j + 1
                parse_tag_attrs(text, i, j + 1, node)
                parent = stack[-1] if stack else None
                node.parent = parent
                (parent.children if parent else roots).append(node)
                last_control = node
                i = j + 1
                continue
            if text.startswith("<CHILDREN>", i):
                if last_control is None:
                    raise ValueError("<CHILDREN> without preceding control at %d" % i)
                stack.append(last_control)
                i += len("<CHILDREN>")
                continue
            if text.startswith("</CHILDREN>", i):
                if not stack:
                    raise ValueError("unbalanced </CHILDREN> at %d" % i)
                parent = stack.pop()
                last_control = parent  # siblings after this block belong to parent's level
                i += len("</CHILDREN>")
                continue
        i += 1
    if stack:
        raise ValueError("unclosed <CHILDREN> block(s): %d" % len(stack))
    return roots


def walk(nodes):
    for nd in nodes:
        yield nd
        yield from walk(nd.children)


def mark_scaled(roots):
    """Mark subtrees of every node whose window id is in SCALED_WINDOW_IDS."""
    def mark(nd):
        nd.scaled = True
        for c in nd.children:
            mark(c)
    hit = False
    for nd in walk(roots):
        if nd.wid is not None and nd.wid in SCALED_WINDOW_IDS:
            mark(nd)
            hit = True
    return hit


# ---------------------------------------------------------------------------
# THE IMAGERECT INVARIANT (task #95, 2026-08-02)
# ---------------------------------------------------------------------------
# imagerect is a BITMAP-PIXEL crop. GZWinBMP's plain path is dst-follows-src
# (BLIT-BEHAVIOUR.md): the drawn size comes from the SOURCE rect, and the
# window is never read. So a rect that asks for more pixels than the bitmap
# HAS cannot draw them - the strip simply stops short, which is exactly the
# "break in the green strip" the report describes on the warrior columns.
#
# We shipped that break ourselves: warrior's own script over-reads its art
# (imagerect (0,0,178,269) over a 170x248 bitmap), and we FAITHFULLY DOUBLED
# the over-read to (0,0,356,538) over 340x496 - 42px of rail that can never
# exist. Doubling an upstream bug is still our bug.
#
# INVARIANT: right <= artW and bottom <= artH, always. We CLAMP (never
# propagate) and we LOG every clamp - a silent clamp would read as "the art
# is fine" while the rail is short.
def png_wh(path):
    """(w,h) from a PNG IHDR, or None. No PIL dependency."""
    try:
        with open(path, "rb") as f:
            head = f.read(33)
        PNG_SIG = bytes([137, 80, 78, 71, 13, 10, 26, 10])
        if len(head) < 33 or head[:8] != PNG_SIG or head[12:16] != b"IHDR":
            return None
        return (int.from_bytes(head[16:20], "big"),
                int.from_bytes(head[20:24], "big"))
    except OSError:
        return None


_rect_clamped = []          # (gid, iid, asked, actual) for the report


SRC1X_DIR = os.path.join(TOOLS, "dbpf", "extracted", "SimCity_1")
_src1x_cache = {}


def _src1x_path(gid, iid):
    """Path of the PRISTINE 1x art for a TGI, or None. The extract carries
    two name spellings; accept both, same as src1x_wh()."""
    for name in ("T-856ddbac_G-%08x_I-%08x.png" % (gid, iid),
                 "T-0x856ddbac_G-0x%08x_I-0x%08x.png" % (gid, iid)):
        p = os.path.join(SRC1X_DIR, name)
        if os.path.isfile(p):
            return p
    return None


def src1x_wh(gid, iid):
    """(w,h) of the PRISTINE 1x art for a TGI, or None."""
    key = (gid, iid)
    if key in _src1x_cache:
        return _src1x_cache[key]
    p = _src1x_path(gid, iid)
    wh = png_wh(p) if p else None
    _src1x_cache[key] = wh
    return wh


# ---------------------------------------------------------------------------
# ODD-EDGE PARITY NUDGE - REVERTED 2026-08-06, THE SAME DAY IT SHIPPED.
# NOT CALLED. Kept because the DIAGNOSIS below is correct and load-bearing; only
# the LEVER was wrong.
#
# WHAT IT DID: moved a button so its left/top edge landed where the factor
# divides evenly, making the edge-derived scaled width equal the art cell.
# 177 buttons across 29 scripts at 1.5x. It DID fix the reported reverse L.
#
# WHY IT WAS REVERTED: user-reported within minutes - "In Select A My Sim all
# the faces are shifted to the left". A nudge is up to q-1 px at 1x, which is
# up to 2px at 1.5x, and the densest grid in the game (aa1f1f57, 24 and 28
# nudges - the most of any script) puts that shift right next to its own frame
# where it is obvious. On an isolated button it is invisible; in a packed grid
# it is a misalignment.
#
# THE LAW: A FIX THAT MOVES THINGS IS JUDGED BY ITS DENSEST NEIGHBOURHOOD,
# NOT BY THE CASE THAT REPORTED THE BUG. The Landscape flyout has five buttons
# with 50px of air between them; "Select A My Sim" has twenty-one faces in a
# grid. Same edit, one is invisible and one is a defect.
#
# THE CORRECT LEVER IS THE WIDTH, NOT THE POSITION - and it lives in the DLL,
# not here. See `kLeafSizeDerived` in src\UiSpike.cpp: for a LEAF window
# (GetChildCount() == 0, i.e. a discrete icon rather than a panel that tiles
# with its neighbours) the scaled size is taken SIZE-DERIVED,
# ScaleRound(w, f), instead of edge-derived. The position never moves; only the
# width/height changes, and only by at most one pixel. Containers keep
# edge-derived rounding, so abutting panel pieces still abut and the #143 white
# seams cannot come back.
#
# THE DIAGNOSIS, WHICH REMAINS CORRECT:
#
# â›” THE DEFECT, MEASURED AND PREDICTED BEFORE IT WAS LOOKED AT. Mayor mode ->
# Landscape shows a line down the RIGHT edge and along the BOTTOM of exactly
# ONE of its five buttons. The five are identical 47x37 controls on identical
# 188x37 four-state sheets. The only thing that differs:
#
#     Raise Terrain    area=(68,  8,115, 45)      l=68  EVEN
#     Gouge Valleys    area=(68, 58,115, 95)      l=68  EVEN
#     Level Terrain    area=(69,108,116,145)      l=69  ODD   <-- the broken one
#     Plant Flora      area=(68,158,115,195)      l=68  EVEN
#     Signs & Labels   area=(68,208,115,245)      l=68  EVEN
#
# `UiSpike::ScaleSubtree` (src\UiSpike.cpp:15546) is EDGE-DERIVED on purpose -
# `newW = ScaleRound(l+w, f) - ScaleRound(l, f)` - so siblings that abut before
# scaling still abut after. That makes the scaled WIDTH depend on the LEFT EDGE:
#
#     l even:  68*1.5 = 102 exact ; 115*1.5 = 172.5 -> 173 ;  w = 71
#     l odd :  69*1.5 = 103.5 -> 104 ; 116*1.5 = 174 exact ;  w = 70
#
# The art cell is `sheetW/4 = 284/4 = 71` for all five. So the odd-edge button -
# and only it - gets a 71px cell in a 70px window. The same rule explains the
# god-mode Day/Night flyout, where ALL THREE buttons sit at l=79 (odd) and the
# user reported the artefact on the sun AND the moon.
#
# âš  INTEGER FACTORS CANNOT SHOW THIS. At f=2, ScaleRound(l*2) is exact for every
# l, so w = 2*(r-l) always. That is why 2x and 3x are perfect and why this hid
# behind nine wrong theories that all matched the same tier signature (law 60).
#
# THE FIX IS ONE PIXEL OF POSITION, NOT A PIXEL OF ART. Move the button so its
# left/top edge lands where the factor divides evenly - l*FACTOR integral - and
# the edge-derived width becomes the size-derived width, which is exactly what
# the art was built for. For f = p/q in lowest terms that means l must be a
# multiple of q (q=2 at 1.5x, i.e. "make it even").
#
# SCOPE, deliberately narrow:
#   * FRACTIONAL FACTORS ONLY - at an integer factor this is a no-op by
#     construction, so 2x and 3x stay BYTE-IDENTICAL. Proven per build.
#   * GZWinBtn only, with `image={g,i}` and NO `imagerect` (an imagerect crop
#     is a different mechanism and must not be touched - see #148 dead end 3).
#   * only where the 1x art cell EXACTLY filled the 1x window. If the sheet was
#     already a different size from its button at 1x, the engine has always
#     stretched it and there is nothing to align.
#   * never the hidden alignment markers 0x0000AAAA (they carry no image, so
#     they are excluded anyway - but doubling one once shifted a whole box by
#     -(229,63), so this is stated rather than assumed).
# The nudge is at most q-1 px at 1x scale and moves the whole control, so its
# size is preserved exactly.
RE_BTN_NODE = re.compile(r"<LEGACY\s+[^>]*?>", re.S)
RE_N_AREA = re.compile(r"area=\((-?\d+),(-?\d+),(-?\d+),(-?\d+)\)")
RE_N_IMAGE = re.compile(r"image=\{([0-9a-fA-F]+),([0-9a-fA-F]+)\}")
RE_N_RECT = re.compile(r"imagerect=\(")
RE_N_ID = re.compile(r"\bid=(0x[0-9a-fA-F]+)")

_parity_nudged = []          # (fn, id, axis, old, new) for the report


def _edge_period(f):
    """Smallest q>0 with q*f integral: the spacing of 'safe' edges."""
    from fractions import Fraction
    return Fraction(f).limit_denominator(1000).denominator


def parity_nudge_btn_areas(text, fn, states=4):
    """Move state-strip buttons onto an edge where FACTOR divides evenly."""
    if FACTOR == math.floor(FACTOR):
        return text, 0                      # integer factor: nothing to align
    q = _edge_period(FACTOR)
    if q <= 1:
        return text, 0
    n = [0]

    def fix(m):
        node = m.group(0)
        if "GZWinBtn" not in node or RE_N_RECT.search(node):
            return node
        ar, im = RE_N_AREA.search(node), RE_N_IMAGE.search(node)
        if not ar or not im:
            return node
        gid, iid = int(im.group(1), 16), int(im.group(2), 16)
        o = src1x_wh(gid, iid)
        if not o or o[0] % states:
            return node
        l, t, r, b = (int(x) for x in ar.groups())
        # in scope only if the 1x cell exactly filled the 1x window
        if (o[0] // states) != (r - l) or o[1] != (b - t):
            return node
        nl = l - (l % q) if (l % q) * 2 <= q else l + (q - l % q)
        nt = t - (t % q) if (t % q) * 2 <= q else t + (q - t % q)
        if nl == l and nt == t:
            return node
        wid = RE_N_ID.search(node)
        _parity_nudged.append((fn, wid.group(1) if wid else "-",
                               (l, t), (nl, nt)))
        n[0] += 1
        return node[:ar.start()] + "area=(%d,%d,%d,%d)" % (
            nl, nt, nl + (r - l), nt + (b - t)) + node[ar.end():]

    return RE_BTN_NODE.sub(fix, text), n[0]


# ---------------------------------------------------------------------------
# STATE-STRIP FIT  (#148, 2026-08-06) - the SECOND cause of the reverse L.
#
# The parity nudge above fixes the buttons whose WINDOW lost a pixel. This fixes
# the ones whose ART gained one.
#
# `Upscale2x.cs::ScaleDim` snaps a scaled dimension to a multiple of
# `CellUnit(v)` = the LCM of every count in {2,3,4,6,8,12,16,24} that divides v.
# That was #143's cure for cell divides and it is a GUESS, because the upscaler
# runs over a directory and cannot know which button binds which sheet:
#
#   a 136px 4-state sheet: CellUnit(136) = LCM(2,4,8) = 8, so 136*1.5 = 204
#   snaps to 208 and the cell becomes 52 - but its 34px button scales to
#   ScaleRound(34*1.5) = 51. 204 was already divisible by 4. The 8 came from
#   the sheet's width happening to divide by 8, NOT from it having 8 states.
#
#   worse on the other axis: a horizontal 4-state strip needs NO vertical cell
#   division at all, yet a 50px-tall sheet snaps 75 -> 76 and every button on it
#   is one row short of its art.
#
# THE BUILDER KNOWS WHAT THE UPSCALER CANNOT: it parses the `.UI`, so it knows
# the sheet's consumer and its exact scaled window. The required size is not a
# guess at all:
#
#       sheetW = states * ScaleRound(buttonW * FACTOR)
#       sheetH =          ScaleRound(buttonH * FACTOR)
#
# âš  INTEGER FACTORS ARE UNTOUCHED BY CONSTRUCTION. At f=2, ScaleRound(w*2) = 2w
# exactly, so the required size IS what ScaleDim already produced. Proven per
# build: 2x came out entry-identical, 0 of 655 changed.
#
# â›” REGENERATE FROM THE 1x SOURCE, NEVER RESAMPLE THE UPSCALED SHEET. Resampling
# an already-upscaled image twice compounds the error and can smear the magenta
# colour key across a boundary - the exact failure that made the --hq experiment
# ship a pink Mayor Rating bar.
#
# The mapping below is UpscaleNearest's, restated: `sx = ox * srcW / dstW`
# (integer division), which is why PIL is used only to decode and encode - never
# to resize. A resampler with its own rounding would be a second art pipeline.
# REVERTED 2026-08-06, SAME DAY IT SHIPPED. DO NOT REINSTATE WITHOUT
# ANSWERING THE QUESTION AT THE BOTTOM OF THIS BLOCK.
#
# `fit_state_strips_to_windows` used to live here. It regenerated every
# art-sized 4-state sheet at exactly `states * ScaleRound(w*f)` x
# `ScaleRound(h*f)`, because `Upscale2x.cs::ScaleDim` snaps on `CellUnit(v)` -
# the LCM of every count in {2,3,4,6,8,12,16,24} that divides the width - which
# is a GUESS: a 136px FOUR-state sheet snaps on 8 and lands at 208 (cell 52)
# when its 34px button wants 51, and it snaps HEIGHTS, which a horizontal strip
# never needs. 61 sheets were rebuilt. The arithmetic was right.
#
# IT STILL BROKE THE GAME. User-reported within minutes: hovering a disaster
# flyout thumbnail made the picture slide right and WRAP inside its frame, with
# a 1px light border appearing on the top and left.
#
# WHY - AND THIS IS THE PART WORTH KEEPING:
#
#   THE FLYOUT STRIP ITEMS ARE CREATED AT RUNTIME, NOT DECLARED IN ANY .UI.
#   (item-create does `SetArea(0, 0, GetW(), GetH())` on the container; see
#   SC4-UI-ENGINE.md.) They bind their art BY TGI, exactly like a scripted
#   button does.
#
#   So a sheet can have consumers this builder CANNOT SEE. The parity nudge is
#   safe because it only moves `area=` inside a .UI, and a window that is not
#   in a .UI cannot be moved by editing one. Resizing the ART is not safe: it
#   reaches every consumer of that TGI, including the invisible ones, and the
#   conflict check only ever compared the .UI consumers against each other.
#   It reported 0 conflicts and was wrong.
#
#   (The first suspicion was that an `imagerect` crop elsewhere still described
#   the old sheet size. MEASURED AND REFUTED: of 115 art-sized strips in scope,
#   ZERO are also referenced by an imagerect. Recorded so it is not re-tried.)
#
# THE LAW: EDITING GEOMETRY IN A .UI HAS THE SCOPE OF THAT .UI. EDITING ART
# HAS THE SCOPE OF THE WHOLE GAME. They are not the same blast radius and must
# not be judged by the same evidence.
#
# WHAT WAS LOST BY REVERTING: 152 art-sized buttons at EVEN left edges still
# have a cell one pixel off their window at 1.5x. NONE of them has ever been
# reported, and the reported defect (#148, the reverse L on Level Terrain and
# on the Day/Night sun and moon) is fixed by the PARITY NUDGE ALONE - all eight
# of those buttons come out 71x56 against a 71x56 cell with the nudge and
# nothing else. `gate_btn_undercover.py` reports the 152 as a known residual.
#
# TO REINSTATE, ANSWER FIRST: how does the builder enumerate the RUNTIME
# consumers of a TGI? Until there is an instrument that can answer that, any
# art-dimension change is unbounded.

def clamp_rect_to_art(l, t, r, b, art_path, gid, iid):
    """Scale a rect by FACTOR and clamp it DOWN to the art that exists.

    â›”â›” DEAD END, PAID FOR TWICE - 2026-08-06. DO NOT ADD AN "EXTEND" BRANCH
    HERE. Both attempts are recorded below so the idea cannot come back.

    THE THEORY (wrong): two independent pieces of code scale the same thing -
    the ART via `Upscale2x.cs::ScaleDim` (round-half-up, then since #143 SNAPPED
    to preserve CellUnit(v), ties going UP) and the RECT via `scale_len()`
    (floor(v*FACTOR + 0.5), which knows nothing about that snap). At 1.5x the
    two disagree on 427 rects; at 2x/3x `ScaleDim` returns early so they agree
    by construction. That maps perfectly onto "broken at 1.5x, perfect at 2x",
    which is exactly why it was so convincing.

    IT IS STILL WRONG. Extending a short rect to the art edge BREAKS THE FLYOUT
    THUMBNAILS, in two different ways, and fixed nothing:

      attempt 1  "short by <= 24px must be a snap" tolerance
                 -> a SMALL atlas (40px wide, two 20px cells) has its first cell
                    short of the sheet by 20, passes the tolerance, and the crop
                    widens across BOTH cells.
                 -> "you broke every thumbnail flyout, they're all split on the
                    left side"
      attempt 2  exact test - extend only if the rect spanned the bitmap at 1x
                 -> still wrong: on a multi-cell strip the LAST cell legitimately
                    ends at the sheet edge (r == ow), so it alone gets widened
                    while its scaled left edge stays put. One cell ends up wider
                    than its neighbours and the image wraps.
                 -> "the thumbnails are broken, look at the UFO wrapping around"

    AND IT WAS NEVER THE REPORTED BUG. The Day/Night buttons this was chasing
    (0xCA35CB74/76/78) carry `image={46a006b0,1441588x}` with NO `imagerect` at
    all, so no rule in this function can reach them. Their art is dimensionally
    clean: 188x37 -> 284x56, and 284/4 = 71 exactly.

    A short rect is a symptom, not the disease. If the art and the rect ever do
    need to agree, make them agree AT THE SOURCE - one scaler - rather than
    patching the crop after the fact.

    What remains here is the original one-directional clamp, the #95 law: never
    propagate an over-read.
    """
    sl, st, sr, sb = scale_len(l), scale_len(t), scale_len(r), scale_len(b)
    wh = png_wh(art_path) if art_path else None
    if wh:
        aw, ah = wh
        if sr > aw or sb > ah:
            # OVER-READ (#95): the upstream script asks for pixels the bitmap
            # does not have. Clamp and log; never propagate an over-read.
            _rect_clamped.append((gid, iid, (sr, sb), (aw, ah)))
            sr, sb = min(sr, aw), min(sb, ah)
    return sl, st, sr, sb


def tgi_png_name(gid, iid):
    return "T-0x%08x_G-0x%08x_I-0x%08x.png" % (PNG_TYPE, gid, iid)


FONT_GUIDS = load_font_guids()


# ---------------------------------------------------------------------------
# DOCK MINIMAP RECESS - neutralize the baked FAKE MAP (3x tier and up).
#
# The dock artwork sheet {46a006b0,13d14ca0} (1x = 235x222) carries a
# DECORATIVE terrain thumbnail baked into the minimap recess. MEASURED on the
# shipped 1x extract
#     tools\dbpf\extracted\SimCity_1\T-856ddbac_G-46a006b0_I-13d14ca0.png
# by saturation bbox (max(r,g,b)-min(r,g,b) > 60, magenta colour-key excluded):
# it occupies EXACTLY x[18,81] y[71,134] = 64x64, contiguous in both axes, and
# it is the ONLY saturated block on the entire sheet (0 saturated pixels
# anywhere else).
#
# The real minimap the game blits into that recess can only ever be a
# power-of-two multiple of the city tile:
#     f=2.00 -> recess 128x128, real map 128 -> EXACT fit, fake map invisible
#     f=3.00 -> recess 192x192, real map 128 -> a 32px ring of fake terrain
# That ring is the artefact the user has reported four times.
#
# FIX: repaint the block with the recess plate that surrounds it. MEASURED:
# the plate is a PURE VERTICAL GRADIENT - the pixels immediately LEFT of the
# block and immediately RIGHT of it agree to within 1-2/255 on every one of
# the 64 rows, so there is no horizontal component to reproduce. A per-row
# median of the flanking pixels therefore reconstructs the plate exactly;
# worst measured seam delta against the immediate neighbour pixel is 2/255.
# (A flat single-colour fill would be WRONG here - the recess is a gradient
# running #a2b5bc at the top to #c7d4d8 at the bottom.)
#
# The rect is DERIVED, not baked: scale_len() over the measured 1x rect
# reproduces the independently-measured block at ALL THREE shipped tiers -
#     1.5x  measured (27,107) 96x96    scale_len -> (27,107) 96x96
#     2.0x  measured (36,142) 128x128  scale_len -> (36,142) 128x128
#     3.0x  measured (54,213) 192x192  scale_len -> (54,213) 192x192
# so the derivation is confirmed at a THIRD tier, not only at the 2x blind
# spot where competing laws agree (scaling law 53).
#
# GATE (rewritten 2026-08-06 - see below). The gate used to be a bare
# `FACTOR >= 2.5` threshold, justified as: "at f=2 the fill would still rewrite
# 128x128 pixels (invisibly, since the real 128 map covers them exactly), so 2x
# parity rests entirely on returning before a single byte is read."
#
# â›” THAT JUSTIFICATION IS TRUE AT f=2 AND FALSE AT f=1.5, and the threshold
# quietly carried 1.5x along with 2x on 2x's reasoning. The recess is 64*f:
#     f=2.0 -> 128 : the real map IS 128. Covers it exactly. Nothing to strip.
#     f=1.5 ->  96 : the real map can only be 64 (the next legal size, 128,
#                    does not fit in 96). It covers 64 of 96, leaving a 32px
#                    ring of BAKED FAKE TERRAIN visible around the real map.
# That ring reads on screen as a "green grid" in the dashboard
# minimap - greens 7C9B00 / 75B564 are this very block's own measured palette.
#
# THE GATE NOW EXPRESSES THE CONDITION IT WAS ALWAYS REACHING FOR: skip only
# when the real map can cover the recess EXACTLY. The real map's edge is always
# `terrainDim << k`, and every SC4 terrainDim (64 / 128 / 256) is a power of
# two - so the real map's edge is always a power of two, and it can tile the
# recess exactly if and only if THE RECESS EDGE IS ITSELF A POWER OF TWO:
#     f=1.5 ->  96  not a power of two -> NEUTRALIZE
#     f=2.0 -> 128  power of two       -> SKIP  (2x bytes stay identical)
#     f=3.0 -> 192  not a power of two -> NEUTRALIZE  (as already shipped)
# This reproduces the shipped behaviour at 2x and 3x exactly while fixing 1.5x,
# and it is derivable from the art instead of being a threshold nobody can
# re-derive. The builder never needs to know the city size to decide.
#
# Idempotency: the staging step re-copies the pristine upscaled sheet from
# UPSCALE_DIR before this runs, so a repeat build always starts from unfixed
# art. Running this twice WITHOUT that re-copy trips the pre-fill assertion
# and aborts - loudly, which is the intended failure mode.
# ---------------------------------------------------------------------------
DOCK_SHEET = (0x46A006B0, 0x13D14CA0)
DOCK_FAKEMAP_1X = (18, 71, 64, 64)   # left, top, w, h - MEASURED, see above


def _is_pow2(n):
    return n > 0 and (n & (n - 1)) == 0


def dock_recess_exactly_fillable():
    """Can the REAL minimap cover the whole recess at this factor?

    The real map's edge is always `terrainDim << k`, and every SC4 terrainDim
    (64 / 128 / 256) is a power of two - so the real map's edge is always a
    power of two, whatever the city size. It can therefore cover the recess
    exactly if and only if the recess edge is itself a power of two. When it
    cannot, whatever the real map does not cover stays visible, and what is
    underneath is the baked fake terrain - so the fake map must be stripped.

    True  -> skip the fill, the sheet's bytes are left untouched (f=2.0).
    False -> strip the fake map (f=1.5, f=3.0).
    """
    return _is_pow2(scale_len(DOCK_FAKEMAP_1X[2]))
_PNG_SIG = bytes([137, 80, 78, 71, 13, 10, 26, 10])


def _png_chunks(blob):
    """[(type, data)] in file order. Stdlib only - same no-PIL contract as png_wh."""
    if blob[:8] != _PNG_SIG:
        raise ValueError("not a PNG")
    out, off = [], 8
    while off < len(blob):
        (ln,) = struct.unpack(">I", blob[off:off + 4])
        out.append((blob[off + 4:off + 8], blob[off + 8:off + 8 + ln]))
        off += 12 + ln
    return out


def _paeth(a, b, c):
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    return b if pb <= pc else c


def _png_read_rgba(path):
    """(w, h, bytearray of RGBA rows, chunks). 8-bit RGBA, non-interlaced only."""
    with open(path, "rb") as f:
        blob = f.read()
    chunks = _png_chunks(blob)
    ihdr = next(d for (t, d) in chunks if t == b"IHDR")
    w, h, depth, ctype, comp, filt, ilace = struct.unpack(">IIBBBBB", ihdr)
    if (depth, ctype, comp, filt, ilace) != (8, 6, 0, 0, 0):
        raise ValueError("%s: need 8-bit RGBA non-interlaced, got %r"
                         % (os.path.basename(path),
                            (depth, ctype, comp, filt, ilace)))
    raw = zlib.decompress(b"".join(d for (t, d) in chunks if t == b"IDAT"))
    stride, bpp = w * 4, 4
    px, pos = bytearray(stride * h), 0
    for y in range(h):
        ft = raw[pos]
        pos += 1
        line = bytearray(raw[pos:pos + stride])
        pos += stride
        ro, po = y * stride, y * stride - stride
        if ft == 1:
            for i in range(bpp, stride):
                line[i] = (line[i] + line[i - bpp]) & 0xFF
        elif ft == 2:
            for i in range(stride):
                line[i] = (line[i] + px[po + i]) & 0xFF
        elif ft == 3:
            for i in range(stride):
                a = line[i - bpp] if i >= bpp else 0
                line[i] = (line[i] + ((a + px[po + i]) >> 1)) & 0xFF
        elif ft == 4:
            for i in range(stride):
                a = line[i - bpp] if i >= bpp else 0
                c = px[po + i - bpp] if i >= bpp else 0
                line[i] = (line[i] + _paeth(a, px[po + i], c)) & 0xFF
        elif ft != 0:
            raise ValueError("%s: bad PNG filter %d on row %d"
                             % (os.path.basename(path), ft, y))
        px[ro:ro + stride] = line
    return w, h, px, chunks


def _png_write_rgba(path, w, h, px, chunks):
    """Rewrite with filter 0 rows, PRESERVING every ancillary chunk. Dropping
    gAMA/sRGB would change how the game renders the colours (see
    tools/dbpf/optimize_png.py), so they are copied through untouched."""
    stride = w * 4
    raw = bytearray()
    for y in range(h):
        raw.append(0)
        raw += px[y * stride:(y + 1) * stride]
    new_idat, wrote = zlib.compress(bytes(raw), 9), False
    out = bytearray(_PNG_SIG)
    for (typ, data) in chunks:
        if typ == b"IDAT":
            if wrote:
                continue
            data, wrote = new_idat, True
        out += struct.pack(">I", len(data)) + typ + data
        out += struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF)
    with open(path, "wb") as f:
        f.write(bytes(out))


def _dock_sat(px, stride, x, y):
    """Saturation of one pixel; 0 for the magenta colour key. Terrain is
    saturated, the grey recess plate is not."""
    o = y * stride + x * 4
    r, g, b = px[o], px[o + 1], px[o + 2]
    if (r, g, b) == (255, 0, 255):
        return 0
    return max(r, g, b) - min(r, g, b)


def neutralize_dock_recess():
    """Repaint the baked fake map in the STAGED dock sheet with the recess
    plate. Hard no-op (nothing read, nothing written) when the real map covers
    the recess exactly - see dock_recess_exactly_fillable()."""
    recess = scale_len(DOCK_FAKEMAP_1X[2])
    if dock_recess_exactly_fillable():
        print("Dock recess: SKIPPED at factor %g - recess edge %d is a power "
              "of two, so the real map covers it exactly; sheet bytes untouched"
              % (FACTOR, recess))
        return
    print("Dock recess: fake map WILL be stripped at factor %g - recess edge "
          "%d is not a power of two, so the real map cannot cover it and the "
          "remainder would show baked terrain" % (FACTOR, recess))
    gid, iid = DOCK_SHEET
    names = [tgi_png_name(gid, iid), tgi_png_name(gid, iid ^ CLONE_XOR)]
    hits = [n for n in names if os.path.isfile(os.path.join(STAGE, n))]
    if not hits:
        sys.exit("FATAL: dock sheet %08x/%08x is not staged, so the recess fix "
                 "would ship silently unapplied. Looked for %s in %s"
                 % (gid, iid, " / ".join(names), STAGE))
    l0, t0, w0, h0 = DOCK_FAKEMAP_1X
    left, top = scale_len(l0), scale_len(t0)
    bw, bh = scale_len(w0), scale_len(h0)
    flank = max(1, scale_len(3))          # 3 source px each side, in output px
    for name in hits:
        path = os.path.join(STAGE, name)
        w, h, px, chunks = _png_read_rgba(path)
        stride = w * 4
        if left - flank < 0 or left + bw + flank > w or top < 0 or top + bh > h:
            sys.exit("FATAL: dock recess rect (%d,%d) %dx%d +/-%d flank does "
                     "not fit the staged sheet %dx%d (%s)"
                     % (left, top, bw, bh, flank, w, h, name))
        # VERIFY BEFORE WRITE: the rect must actually BE the fake map. If the
        # art is ever re-extracted and the block moves, abort rather than paint
        # grey over the wrong pixels.
        probe = [(x, y) for y in range(top, top + bh, 4)
                 for x in range(left, left + bw, 4)]
        n_sat = sum(1 for (x, y) in probe if _dock_sat(px, stride, x, y) > 60)
        if n_sat < len(probe) * 0.6:
            sys.exit("FATAL: dock recess rect (%d,%d) %dx%d holds only %d/%d "
                     "saturated probe px - that is not the baked fake map. "
                     "Re-measure DOCK_FAKEMAP_1X against the 1x extract."
                     % (left, top, bw, bh, n_sat, len(probe)))
        fills = []
        for y in range(top, top + bh):
            s = []
            for dx in range(1, flank + 1):
                for x in (left - dx, left + bw - 1 + dx):
                    o = y * stride + x * 4
                    s.append((px[o], px[o + 1], px[o + 2], px[o + 3]))
            med = bytes(sorted(v[c] for v in s)[len(s) // 2] for c in range(4))
            fills.append(med)
            o = y * stride + left * 4
            px[o:o + bw * 4] = med * bw
        _png_write_rgba(path, w, h, px, chunks)
        # POSITIVE CONTROL: the same detector that just found a full block of
        # saturated pixels must now find none inside the rect.
        w2, h2, px2, _ = _png_read_rgba(path)
        s2 = w2 * 4
        rem = sum(1 for y in range(top, top + bh) for x in range(left, left + bw)
                  if _dock_sat(px2, s2, x, y) > 60)
        if rem:
            sys.exit("FATAL: dock recess still holds %d saturated px after the "
                     "fill (%s)" % (rem, name))
        print("Dock recess NEUTRALIZED in %s: rect (%d,%d) %dx%d, %d rows "
              "filled from the plate gradient #%02x%02x%02x (top) .. "
              "#%02x%02x%02x (bottom); %d saturated px found before, 0 after"
              % (name, left, top, bw, bh, bh,
                 fills[0][0], fills[0][1], fills[0][2],
                 fills[-1][0], fills[-1][1], fills[-1][2], n_sat))


# ---------------------------------------------------------------------------
# #172 - THE CITY QUERY "?" PAIR: CLAMP THE ART CELLS TO THE WINDOW.
# USER DECISION 2026-08-16: "Fix it - clamp to the window" - scoped to THIS
# BUTTON PAIR ONLY, keyed to exactly two TGIs. NOT a general rule.
#
# The "?" control is TWO stacked GZWinBtns in I-c973b411 (G-96a006b0, the
# active layout; the G-08000600 twin is the engine's 800x600-only variant and
# no tier package is ever loaded at 800x600, so it cannot meet this art):
#     Query       0x99887766  area=(95, 85,131,106)  ->  36x21 window
#     Route Query 0x8b96b73e  area=(95,106,131,127)  ->  36x21 window
# abutting at y=106 - the abutment IS the divider line. Their 4-state sheets
# exceed that window IN STOCK:
#     {46a006b0,14015547}  148x21, cell 37x21  ->  +1 col
#     {46a006b0,4b8da4a4}  148x23, cell 37x23  ->  +1 col, +2 rows
# The blit is anchored at the window origin, so the overhang spills RIGHT and
# DOWN, and the scale factor multiplies it (+3/+6 at 3x, also present at
# 1.5x). CURE: trim each state cell of the STAGED sheet down to the scaled
# window R(36f) x R(21f), keeping the TOP-LEFT of every cell - the trimmed
# pixels are exactly the ones that land outside the window today, so nothing
# inside the window changes. Output cells are repacked at the new pitch
# (state k starts at k * R(36f)); every output cell's content comes solely
# from its own input cell, top-left anchored - content never crosses a cell
# boundary and no pixel is repainted, so the colour key is untouched by
# construction (proven by the byte-equality control below).
#
# NOT AN INTEGER NO-OP, BY DESIGN: the overhang exists in stock, so 2x/3x
# bytes change for these two sheets and only these two:
#     1.5x  224x33 -> 216x32   224x35 -> 216x32
#     2x    296x42 -> 288x42   296x46 -> 288x42
#     3x    444x63 -> 432x63   444x69 -> 432x63
# That is the approved fix, not drift.
#
# THE CONSUMER SET IS CLOSED AND PROVEN (2026-08-16): grep of all extracted
# .UI scripts (G-96a006b0 x271 + G-08000600 x10) finds only the c973b411
# pair; src\*.cpp|*.h has no code-bound ref; the builder's code-bound list
# has neither TGI; the {1abe787d} same-instance duplicates are referenced by
# nothing and are not staged. That closure is what makes a consumer-window-
# sized art edit legal HERE while the general rule stays reverted (#148/#156:
# runtime-created consumers this builder cannot see). Do not generalize.
#
# This is the OPPOSITE operation of clamp_rect_to_art's dead end: that
# tripwire forbids EXTENDING a crop to reach art the window never showed.
# This TRIMS art down to the window - same direction as law #95 (never
# propagate an over-read). If the premise ever inverts (art smaller than the
# window), this function aborts rather than extend.
#
# KNOWN RESIDUAL (report, don't chase): at 1.5x the active Query window is
# edge-derived 54x31 (85*1.5 = 127.5 rounds UP; ScaleSubtree is edge-derived
# so abutment survives), one row shorter than R(21*1.5) = 32, so one
# trimmed-cell row still lands on Route Query's first row - which draws
# AFTER Query (later sibling) and covers it. The pair's outer envelope is
# exact at every tier.
# ---------------------------------------------------------------------------
QUERY_PAIR_WIN_1X = (36, 21)   # the pair's design window (active G-96a006b0 layout)
QUERY_PAIR_STATES = 4
QUERY_PAIR_SHEETS = (
    (0x46A006B0, 0x14015547),  # Query       0x99887766 - 1x 148x21, cell 37x21
    (0x46A006B0, 0x4B8DA4A4),  # Route Query 0x8b96b73e - 1x 148x23, cell 37x23
)


def clamp_query_pair_cells():
    """#172: trim each state cell of the two staged query-pair sheets to the
    scaled window R(36f) x R(21f). Top-left kept, right/bottom overhang
    dropped, cells repacked at the new pitch. Idempotent: a sheet already at
    the target passes through untouched (unlike the dock fill, which relies
    on the stage re-copy and asserts on a second run)."""
    n = QUERY_PAIR_STATES
    tw, th = scale_len(QUERY_PAIR_WIN_1X[0]), scale_len(QUERY_PAIR_WIN_1X[1])
    for gid, iid in QUERY_PAIR_SHEETS:
        names = [tgi_png_name(gid, iid), tgi_png_name(gid, iid ^ CLONE_XOR)]
        hits = [nm for nm in names if os.path.isfile(os.path.join(STAGE, nm))]
        if not hits:
            sys.exit("FATAL #172: query-pair sheet %08x/%08x is not staged - "
                     "the clamp would ship silently unapplied. Looked for %s "
                     "in %s" % (gid, iid, " / ".join(names), STAGE))
        # PREMISE CHECK against the pristine 1x extract: the overhang being
        # trimmed must exist in STOCK. If the art is ever re-extracted
        # differently, abort rather than trim the wrong pixels.
        src1x = os.path.join(TOOLS, "dbpf", "extracted", "SimCity_1",
                             "T-%08x_G-%08x_I-%08x.png" % (PNG_TYPE, gid, iid))
        wh1 = png_wh(src1x)
        if not wh1:
            sys.exit("FATAL #172: 1x extract missing/unreadable for %08x/%08x "
                     "(%s) - cannot verify the stock-overhang premise"
                     % (gid, iid, src1x))
        w1, h1 = wh1
        if w1 % n:
            sys.exit("FATAL #172: 1x sheet %s is %dx%d - width not divisible "
                     "by %d states" % (os.path.basename(src1x), w1, h1, n))
        ov_w = w1 // n - QUERY_PAIR_WIN_1X[0]
        ov_h = h1 - QUERY_PAIR_WIN_1X[1]
        if ov_w < 0 or ov_h < 0:
            sys.exit("FATAL #172: 1x cell %dx%d is SMALLER than the %dx%d "
                     "window - the stock premise inverted. Extending art is "
                     "the reverted #148/#156; never do it here."
                     % (w1 // n, h1, QUERY_PAIR_WIN_1X[0], QUERY_PAIR_WIN_1X[1]))
        for nm in hits:
            path = os.path.join(STAGE, nm)
            w, h, px, chunks = _png_read_rgba(path)
            if w % n:
                sys.exit("FATAL #172: staged %s width %d not divisible by %d "
                         "states" % (nm, w, n))
            cw = w // n
            if cw == tw and h == th:
                print("#172 query-pair clamp: %s already %dx%d (cell %dx%d) - "
                      "no-op" % (nm, w, h, cw, h))
                continue
            if cw < tw or h < th:
                sys.exit("FATAL #172: staged %s cell %dx%d is SMALLER than "
                         "the scaled window %dx%d - this clamp only ever "
                         "TRIMS; an extend branch is the dead end paid for "
                         "twice (see clamp_rect_to_art)."
                         % (nm, cw, h, tw, th))
            # Trim bound. F14 (review 2026-08-16): the "+2px snap slack"
            # exists ONLY for fractional factors (the 1.5x CellUnit snap adds
            # at most that here). At an INTEGER factor scale_len is exact
            # multiplication and the snap is a no-op, so the trim is PROVABLY
            # the scaled stock overhang - assert equality there; slack at 2x/
            # 3x would just mask real art drift.
            if abs(FACTOR - round(FACTOR)) < 1e-9:
                if (cw - tw, h - th) != (scale_len(ov_w), scale_len(ov_h)):
                    sys.exit("FATAL #172: staged %s cell %dx%d vs window "
                             "%dx%d - trim (%d,%d) != stock overhang (%d,%d) "
                             "scaled, at an INTEGER factor where the trim is "
                             "provably exact (no snap, no slack); the art "
                             "moved, re-measure before trimming."
                             % (nm, cw, h, tw, th,
                                cw - tw, h - th, ov_w, ov_h))
            elif (cw - tw) > scale_len(ov_w) + 2 or (h - th) > scale_len(ov_h) + 2:
                sys.exit("FATAL #172: staged %s cell %dx%d vs window %dx%d - "
                         "trim (%d,%d) exceeds stock overhang (%d,%d) scaled "
                         "+ 2px snap slack; the art moved, re-measure before "
                         "trimming." % (nm, cw, h, tw, th,
                                        cw - tw, h - th, ov_w, ov_h))
            key_trim = 0   # colour-key px in the DISCARDED region (informational)
            stride = w * 4
            for s in range(n):
                for y in range(h):
                    for x in range(cw):
                        if x < tw and y < th:
                            continue
                        o = y * stride + (s * cw + x) * 4
                        if px[o] == 255 and px[o + 1] == 0 and px[o + 2] == 255:
                            key_trim += 1
            nw = n * tw
            nstride = nw * 4
            out = bytearray(nstride * th)
            for s in range(n):
                sx, dx = s * cw * 4, s * tw * 4
                for y in range(th):
                    o_in = y * stride + sx
                    o_out = y * nstride + dx
                    out[o_out:o_out + tw * 4] = px[o_in:o_in + tw * 4]
            # Patch IHDR to the new dimensions; every other chunk (gAMA/sRGB
            # included - see _png_write_rgba) passes through untouched.
            new_chunks = [(typ, struct.pack(">II", nw, th) + data[8:]
                           if typ == b"IHDR" else data)
                          for (typ, data) in chunks]
            _png_write_rgba(path, nw, th, out, new_chunks)
            # POSITIVE CONTROL: re-read; dimensions must be the target and
            # every kept pixel must equal its source byte-for-byte - a trim
            # never repaints (this is also the colour-key-untouched proof).
            w2, h2, px2, _ = _png_read_rgba(path)
            if (w2, h2) != (nw, th):
                sys.exit("FATAL #172: %s reads back %dx%d, wanted %dx%d"
                         % (nm, w2, h2, nw, th))
            for s in range(n):
                sx, dx = s * cw * 4, s * tw * 4
                for y in range(th):
                    if (px2[y * nstride + dx:y * nstride + dx + tw * 4]
                            != px[y * stride + sx:y * stride + sx + tw * 4]):
                        sys.exit("FATAL #172: %s state %d row %d differs from "
                                 "its source after the trim" % (nm, s, y))
            print("#172 query-pair clamp: %s %dx%d (cell %dx%d) -> %dx%d "
                  "(cell %dx%d); trimmed %d col(s) right + %d row(s) bottom "
                  "per state; %d colour-key px in the discarded region"
                  % (nm, w, h, cw, h, nw, th, tw, th,
                     cw - tw, h - th, key_trim))


# ---------------------------------------------------------------------------
# #186 - generation half of the fixed-96 pin. Doctrine lives with the
# MISSION_BUBBLE_FIXED96 constants; the staging half is in main()'s
# code-bound loop, the honesty half is the routing gate after it, and the
# key-integrity half is the gate split at the pack step.
def build_mission_bubble_fixed96():
    """Regenerate the mission-bubble family from the PRISTINE 1x sources at
    the FIXED x3 design multiple, via the canonical resampler with the
    Rebuild-Corpus.ps1 flag set. Returns {(gid, iid): generated PNG path}
    for EVERY family member - the staging loop pins the code-bound ones; the
    .UI-routed ones are generated too (which pre-verifies their dims) but
    never staged from here.

    FATAL, never quiet: a missing 1x source, a failed resampler run, a
    missing output, or an output whose dims are not EXACTLY
    MISSION_BUBBLE_FIXED96_MULT x the MEASURED 1x dims each abort the build.
    """
    sfx = ("-%s" % TAG) if TAG else ""
    src_tmp = os.path.join(OUT_DIR, "bubble96-src" + sfx)
    out_dir = os.path.join(OUT_DIR, "bubble96" + sfx)
    fresh_dir(src_tmp)
    fresh_dir(out_dir)
    src_wh = {}
    for (gid, iid) in sorted(MISSION_BUBBLE_FIXED96):
        p = _src1x_path(gid, iid)
        if p is None:
            sys.exit("FATAL #186: pristine 1x source missing for %08x/%08x "
                     "in %s - cannot regenerate (law 64: from pristine, "
                     "never a resize of a resize)" % (gid, iid, SRC1X_DIR))
        wh = png_wh(p)
        if wh is None:
            sys.exit("FATAL #186: 1x source unreadable for %08x/%08x (%s)"
                     % (gid, iid, p))
        src_wh[(gid, iid)] = wh
        shutil.copy2(p, os.path.join(src_tmp, os.path.basename(p)))
    up = os.path.join(TOOLS, "upscale")
    # The Rebuild-Corpus.ps1 flag set (F12: all five derived lists + the #185
    # slab second occurrence + --smooth-unkeyed). At integer factor 3 each
    # treatment refuses itself / no-ops, so the result is the plain NN corpus
    # product (verified byte-identical to preview-3x, 2026-08-17) - but the
    # full set rides anyway so this invocation can never drift from the
    # canonical one silently.
    # Review finding 2: a released-repo user hits this path via
    # docs\BUILDING.md, so every input is preflighted with the FATAL idiom
    # instead of an unhandled traceback, and the exe location error names
    # the build step. (Build-PublicRepo.ps1's manifest now ships all six
    # list files - the companion change of the same finding.)
    exe = os.path.join(up, "Upscale2x.exe")
    if not os.path.isfile(exe):
        sys.exit("FATAL #186: %s missing - build it first (upscale\\Build.ps1,"
                 " or csc with the output placed in tools\\upscale\\)" % exe)
    lists186 = [("--cell-strips", "cell-strips.txt"),
                ("--nine-slice", "nine-slice.txt"),
                ("--no-snap", "no-snap.txt"),
                ("--no-smooth", "no-smooth.txt"),
                ("--height-exact-strips", "height-exact-strips.txt"),
                ("--height-exact-strips", "height-exact-slabs.txt")]
    argv186 = [exe, src_tmp, out_dir,
               "--factor", str(MISSION_BUBBLE_FIXED96_MULT),
               "--normalize-names"]
    for flag, name in lists186:
        lp = os.path.join(up, name)
        if not os.path.isfile(lp):
            sys.exit("FATAL #186: derived list %s missing - regenerate it "
                     "(find_cell_strips.py and friends) or restore it from "
                     "the release archive; building without it un-ships a "
                     "confirmed fix." % lp)
        argv186 += [flag, lp]
    argv186.append("--smooth-unkeyed")
    try:
        r = subprocess.run(argv186, capture_output=True, text=True)
    except OSError as e:
        sys.exit("FATAL #186: could not run %s (%s)" % (exe, e))
    if r.returncode != 0:
        sys.exit("FATAL #186: fixed-96 regeneration failed (exit "
                 "%d):\n%s%s" % (r.returncode, r.stderr, r.stdout))
    out = {}
    # %d on a float printed "x1" while staging x1.5 - an instrument lying
    # in its own favour, the fifth caught on 2026-08-18. %g prints 1.5.
    print("#186 mission-bubble family (x%g of measured 1x, every "
          "tier):" % MISSION_BUBBLE_FIXED96_MULT)
    for (gid, iid) in sorted(MISSION_BUBBLE_FIXED96):
        p = os.path.join(out_dir, tgi_png_name(gid, iid))
        wh = png_wh(p) if os.path.isfile(p) else None
        w1, h1 = src_wh[(gid, iid)]
        want = (MISSION_BUBBLE_FIXED96_MULT * w1,
                MISSION_BUBBLE_FIXED96_MULT * h1)
        if wh is None:
            sys.exit("FATAL #186: %08x/%08x missing from the resampler "
                     "output (%s)" % (gid, iid, out_dir))
        if wh != want:
            sys.exit("FATAL #186: %08x/%08x came out %dx%d, need EXACTLY "
                     "%dx%d = %d x the measured 1x %dx%d - a list rule moved "
                     "the dims; re-measure before shipping"
                     % (gid, iid, wh[0], wh[1], want[0], want[1],
                        MISSION_BUBBLE_FIXED96_MULT, w1, h1))
        out[(gid, iid)] = p
        print("   %08x/%08x  1x %dx%d -> %dx%d"
              % (gid, iid, w1, h1, wh[0], wh[1]))
    return out


def main():
    print("Scale factor: %g  (tag %r)  ->  %s"
          % (FACTOR, TAG or "(none, 2x default)", os.path.basename(OUT_DAT)))
    print("Upscaled art dir: %s" % UPSCALE_DIR)
    print("Font style GUIDs loaded: %d" % len(FONT_GUIDS))
    if not os.path.isdir(UPSCALE_DIR):
        sys.exit("FATAL: upscaled art dir not found for factor %g: %s" % (FACTOR, UPSCALE_DIR))
    os.makedirs(OUT_DIR, exist_ok=True)
    if TAG:
        os.makedirs(PKG_DIR, exist_ok=True)
    if os.path.isdir(STAGE):
        for fn in os.listdir(STAGE):  # empty in place; OneDrive may lock the dir itself
            os.remove(os.path.join(STAGE, fn))
    else:
        os.makedirs(STAGE)

    # ---- load the PNG store TGI list (collision checks) ----
    store_tgis = set()
    with open(PNG_TGI_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            store_tgis.add((int(row["GroupID"], 16), int(row["InstanceID"], 16)))
    print("PNG store TGIs loaded: %d" % len(store_tgis))

    # ---- discover + parse all layout .UI files ----
    ui_files = []
    for g in UI_GROUPS:
        ui_files += sorted(
            fn for fn in os.listdir(UI_DIR)
            if fn.startswith("T-00000000_G-%s_I-" % g) and fn.endswith(".ui")
        )
    print("UI layout files: %d" % len(ui_files))

    parsed = {}      # fname -> (text, roots)
    scaled_files = []
    for fn in ui_files:
        with open(os.path.join(UI_DIR, fn), "r", encoding="latin-1", newline="") as f:
            text = f.read()
        roots = parse_ui(text)
        if mark_scaled(roots):
            scaled_files.append(fn)
        parsed[fn] = (text, roots)

    print("Scaled-window files (set S): %d" % len(scaled_files))
    for fn in scaled_files:
        print("   " + fn)

    # ---- ref map ----
    # ref (gid,iid) -> {"scaled": set(files), "unscaled": set(files), "count": n}
    refs = defaultdict(lambda: {"scaled": set(), "unscaled": set(), "count": 0})
    for fn, (text, roots) in parsed.items():
        for nd in walk(roots):
            for (gid, iid, _, _) in nd.images:
                rec = refs[(gid, iid)]
                rec["count"] += 1
                (rec["scaled"] if nd.scaled else rec["unscaled"]).add(fn)

    exclusive, shared, unscaled_only = [], [], []
    for tgi, rec in refs.items():
        if rec["scaled"] and rec["unscaled"]:
            shared.append(tgi)
        elif rec["scaled"]:
            exclusive.append(tgi)
        else:
            unscaled_only.append(tgi)
    print("Distinct image refs: %d  (exclusive %d / shared %d / unscaled-only %d)"
          % (len(refs), len(exclusive), len(shared), len(unscaled_only)))

    # ---- 2x availability ----
    def has_2x(gid, iid):
        return os.path.isfile(os.path.join(UPSCALE_DIR, tgi_png_name(gid, iid)))

    avail = {tgi: has_2x(*tgi) for tgi in refs}

    # ---- collision checks for the clone scheme ----
    clones = {}  # (gid,iid) -> (gid, iid^XOR)
    for (gid, iid) in shared:
        if not avail[(gid, iid)]:
            continue
        c = (gid, iid ^ CLONE_XOR)
        if c in store_tgis:
            sys.exit("FATAL: clone TGI %08x/%08x collides with the game PNG store" % c)
        if c in refs:
            sys.exit("FATAL: clone TGI %08x/%08x collides with a referenced TGI" % c)
        clones[(gid, iid)] = c
    clone_vals = list(clones.values())
    if len(set(clone_vals)) != len(clone_vals):
        sys.exit("FATAL: clone TGIs collide with each other")
    for c in clone_vals:
        if c in [(g, i) for (g, i) in exclusive]:
            sys.exit("FATAL: clone TGI collides with an exclusive original TGI")
    print("Shared clones planned: %d (no collisions)" % len(clones))

    # #186: regenerate the fixed-96 mission-bubble family BEFORE the
    # code-bound pass stages it. Factor-independent by design - the same x3
    # bytes at every tier.
    fixed96_art = build_mission_bubble_fixed96()
    fixed96_pinned = []

    # ---- code-bound art (never visible to the .UI scan) ----
    clone_targets = set(clones.values())
    cb_staged, cb_conflict, cb_handled, cb_missing = [], [], [], []
    for (gid, iid) in CODE_BOUND_TGIS:
        rec = refs.get((gid, iid)) if (gid, iid) in refs else None
        if rec is not None:
            if rec["scaled"] and (gid, iid) not in CODE_BOUND_FORCE:
                cb_handled.append((gid, iid))   # exclusive/shared logic covers it
                continue
            elif not rec["scaled"]:
                cb_conflict.append((gid, iid))  # UNSCALED-only: leave untouched
                continue
            # else: rec["scaled"] but in CODE_BOUND_FORCE â€” fall through to stage
        if not has_2x(gid, iid):
            cb_missing.append((gid, iid))
            continue
        if (gid, iid) in clone_targets:
            sys.exit("FATAL: code-bound TGI %08x/%08x collides with a planned clone TGI"
                     % (gid, iid))
        # ART SOURCE OVERRIDE (task #60, USER-DIRECTED 2026-07-30): the
        # U-Drive-It mission bubble base draws its WINDOW from the source
        # image size (art-sized, zero .UI refs), and the report describes it 2x
        # its already-scaled size for large-map visibility. Stage it from
        # the pre-generated double-of-tier art (bubble4x[-tag]/, built by
        # Upscale2x --factor 2 over the tier preview). DELIBERATE
        # stock-parity deviation, recorded in REGRESSION.md. The 15 glyph
        # table entries stay at tier scale - they are SHARED generic art
        # (82B99D9D is the spinner arrow strip; 46A006A7 the slider art)
        # and doubling them would resize every spinner/slider in the game.
        # DISABLED 2026-07-30 (same day): the deployed 128x128 bubble did NOT
        # change the map circles (user-verified) - the blue map markers are
        # NOT this TGI (likely world-layer billboards scaled by the renderer,
        # not art-sized UI). 0x094AC89A is some OTHER bubble, and leaving it
        # 4x risks an oversized surprise wherever it actually draws. Re-enable
        # only after the real map-marker sprite is identified (task #60).
        BUBBLE_OVERRIDE_ENABLED = False
        override_dir = os.path.join(OUT_DIR, "bubble4x" + ("-%s" % TAG if TAG else ""))
        override = os.path.join(override_dir, tgi_png_name(gid, iid))
        if (gid, iid) in MISSION_BUBBLE_FIXED96:
            # #186: FIXED x3-of-design art, same bytes at every tier. This
            # replaces the disabled #60 "bubble4x" experiment below for
            # this family (#60 was 2x-OF-TIER, i.e. 4x-of-design at the 2x
            # tier - the very shape #100's payload gate exists to block;
            # fixed-96 is 3x-of-design everywhere and tier-invariant).
            shutil.copy2(fixed96_art[(gid, iid)],
                         os.path.join(STAGE, tgi_png_name(gid, iid)))
            fixed96_pinned.append((gid, iid))
            print("   #186 FIXED-96 %08x/%08x staged (x%d of 1x at every "
                  "tier)" % (gid, iid, MISSION_BUBBLE_FIXED96_MULT))
        elif (BUBBLE_OVERRIDE_ENABLED
                and (gid, iid) == (0x46A006B0, 0x094AC89A)
                and os.path.isfile(override)):
            shutil.copy2(override, os.path.join(STAGE, tgi_png_name(gid, iid)))
            print("   ART OVERRIDE %08x/%08x staged from %s (2x-of-tier)"
                  % (gid, iid, os.path.basename(override_dir)))
        else:
            shutil.copy2(os.path.join(UPSCALE_DIR, tgi_png_name(gid, iid)),
                         os.path.join(STAGE, tgi_png_name(gid, iid)))
        cb_staged.append((gid, iid))

    print("\nCode-bound art (DYNAMIC-CONTROLS.md): %d candidates" % len(CODE_BOUND_TGIS))
    for label, lst in (("STAGED 2x in-place", cb_staged),
                       ("CONFLICT (UNSCALED-only .UI ref, untouched)", cb_conflict),
                       ("already handled by .UI logic (scaled ref)", cb_handled),
                       ("missing 2x asset, skipped", cb_missing)):
        print("   %s: %d" % (label, len(lst)))
        for (gid, iid) in lst:
            print("      %08x/%08x" % (gid, iid))

    # #186 ROUTING GATE - the pin is only honest if the classifier's routing
    # matches the ledger (law 42: a gate is only as honest as its scope).
    # Two failure directions, both FATAL:
    #   * a member that should pin never reached code-bound staging (a new
    #     .UI ref appeared, or its tier asset vanished) -> the fix would
    #     ship silently absent (law 54);
    #   * a UI-ROUTED member DID pin (its .UI refs vanished from the corpus)
    #     -> 96px art would silently reach consumers nobody re-scoped
    #     (laws 42/94).
    _f96_pinned = set(fixed96_pinned)
    for tgi in sorted(MISSION_BUBBLE_FIXED96):
        if tgi in _f96_pinned:
            if tgi in MISSION_BUBBLE_FIXED96_UI_ROUTED:
                sys.exit("FATAL #186: %08x/%08x is on the UI-ROUTED ledger "
                         "but was PINNED - its .UI consumers disappeared "
                         "from the corpus; re-scope (would 96px art still "
                         "break anything?) before shipping." % tgi)
        elif tgi in MISSION_BUBBLE_FIXED96_UI_ROUTED:
            print("   #186 ledger: %08x/%08x NOT pinned - .UI consumers "
                  "keep it on the classifier's rule; its mission glyph (if "
                  "any) stays tier-sized (46a006a7: stock)" % tgi)
        else:
            sys.exit("FATAL #186: family member %08x/%08x never reached "
                     "code-bound staging (classifier routing moved, or the "
                     "tier asset is missing) - the fixed-96 pin would ship "
                     "silently absent; re-scope before building." % tgi)

    # ---- stage PNGs ----
    n_excl_staged = n_excl_missing = 0
    for (gid, iid) in sorted(exclusive):
        if avail[(gid, iid)]:
            shutil.copy2(os.path.join(UPSCALE_DIR, tgi_png_name(gid, iid)),
                         os.path.join(STAGE, tgi_png_name(gid, iid)))
            n_excl_staged += 1
        else:
            n_excl_missing += 1
    n_shared_staged = 0
    n_shared_missing = sum(1 for t in shared if not avail[t])
    for (gid, iid), (cg, ci) in sorted(clones.items()):
        shutil.copy2(os.path.join(UPSCALE_DIR, tgi_png_name(gid, iid)),
                     os.path.join(STAGE, tgi_png_name(cg, ci)))
        n_shared_staged += 1
    print("Staged: %d exclusive in-place PNGs (%d no-2x skipped), %d shared clones (%d no-2x skipped)"
          % (n_excl_staged, n_excl_missing, n_shared_staged, n_shared_missing))

    # Post-upscale art repair: erase the decorative fake map baked into the
    # dock's minimap recess. 3x tier and up only - see the block comment above.
    neutralize_dock_recess()

    # #172: clamp the city query "?" pair's art cells to their window - see
    # the block comment above. NOT an integer no-op, by design: stock art
    # overhangs the window, so 2x/3x bytes change for those two sheets.
    clamp_query_pair_cells()

    # ---- edit the scaled-window .UI files ----
    edit_stats = []   # (fname, n_retargets, n_rect_doubles, unchanged)
    edge_no_rect = 0  # scaled edgeimage=yes controls with no imagerect attr (nothing to edit)
    left_1x_controls = 0
    left_1x_warned = set()   # (gid, iid, kind) - deduped build-time warnings
    for fn in scaled_files:
        text, roots = parsed[fn]
        edits = []  # (start, end, replacement)
        n_ret = n_dbl = 0
        for nd in walk(roots):
            if not nd.scaled or not nd.images:
                if nd.scaled and nd.edgeimage == "yes" and nd.imagerect is None:
                    edge_no_rect += 1
                continue
            control_art_doubled = False
            last_art = None      # #95: the ref whose art this rect crops
            for (gid, iid, vs, ve) in nd.images:
                if not avail[(gid, iid)]:
                    left_1x_controls += 1
                    # Task #55 lesson (Grutzehaus + the U-Drive-It pickers,
                    # 2026-07-29): a 1x ref inside a frame we scale is a BUG
                    # SHAPE, not a safe fallback - surface it at build time.
                    # Two classes:  DANGLING (TGI absent from the game's PNG
                    # store; the game supplies pixels at runtime -> needs the
                    # runtime-image treatment, task #47) vs MISSING-2X (real
                    # 1x art with no upscale -> will tile/corner-draw in the
                    # scaled frame; generate the 2x).
                    kind = ("DANGLING .UI ref - runtime-supplied pixels "
                            "(task #47 family)"
                            if (gid, iid) not in store_tgis
                            else "MISSING-2X - 1x art WILL draw wrong in a "
                                 "scaled frame")
                    left_1x_warned.add((gid, iid, kind))
                    continue  # art stays 1x for this ref: no retarget, and no rect doubling below
                control_art_doubled = True
                last_art = (gid, iid)
                if (gid, iid) in clones:
                    cg, ci = clones[(gid, iid)]
                    edits.append((vs, ve, "{%08x,%08x}" % (cg, ci)))
                    n_ret += 1
            if control_art_doubled and nd.imagerect is not None:
                (l, t, r, b), vs, ve = nd.imagerect
                # #95: clamp to the art that exists (see THE IMAGERECT
                # INVARIANT). last_art is the ref this control resolved to.
                ap = None
                if last_art is not None:
                    ag, ai = last_art
                    if (ag, ai) in clones:
                        ag, ai = clones[(ag, ai)]
                    # F8 (review 2026-08-16): measure the art that SHIPS. The
                    # STAGE copy can differ from UPSCALE_DIR post-#172 (the
                    # query-pair trim rewrites staged sheets), so prefer it
                    # and fall back to the pristine upscale - the same
                    # two-candidate pattern as the tp_stage lookup below.
                    for cand in (os.path.join(STAGE, tgi_png_name(ag, ai)),
                                 os.path.join(UPSCALE_DIR, tgi_png_name(ag, ai))):
                        if os.path.isfile(cand):
                            ap = cand
                            break
                cl, ct, cr, cb2 = clamp_rect_to_art(
                    l, t, r, b, ap,
                    last_art[0] if last_art else 0,
                    last_art[1] if last_art else 0)
                edits.append((vs, ve, "(%d,%d,%d,%d)" % (cl, ct, cr, cb2)))
                n_dbl += 1
        new_text = text
        for (s, e, rep) in sorted(edits, key=lambda x: -x[0]):
            new_text = new_text[:s] + rep + new_text[e:]

        def font_sub(m2):
            name = m2.group(1)
            guid = FONT_GUIDS.get(name)
            if guid:
                font_sub.converted[name] = font_sub.converted.get(name, 0) + 1
                return "font=" + guid
            font_sub.unknown.add(name)
            return m2.group(0)
        font_sub.converted = {}
        font_sub.unknown = set()
        # TICKER MARQUEE DESIGN WIDTH (task #42, v2.19.1): the game re-imposes
        # the marquee's init-cached geometry every roll tick, so the DLL's
        # runtime width scale is undone within a frame (proven live
        # 2026-07-29: one "width 676 -> 1352" apply, then 676 again -> the 2x
        # HTML headline wrapped mid-word). Ship the DESIGN width scaled
        # instead: the cache then STARTS scaled and every game-side reset
        # re-imposes the scaled value. Height stays 1x - ticker init
        # recomputes it from the font (3 x lineHeight). This is the ONE
        # deliberate exception to "this builder never edits area=".
        if fn.endswith("_I-2a2aed99.ui"):
            def widen_marquee(mm):
                l, t, r, b = (int(x) for x in mm.group(2, 3, 4, 5))
                return "%sarea=(%d,%d,%d,%d)" % (
                    mm.group(1), l, t, l + scale_len(r - l), b)
            new_text, n_marq = re.subn(
                r'(id=0xaa12f33c\s+)area=\((\d+),(\d+),(\d+),(\d+)\)',
                widen_marquee, new_text)
            if n_marq != 1:
                sys.exit("FATAL: marquee area edit matched %d times in %s"
                         % (n_marq, fn))
            print("   marquee 0xaa12f33c design width x%g in %s" % (FACTOR, fn))
        # #172 QUERY-PAIR TWIN HARMONIZATION (companion to
        # clamp_query_pair_cells; user decision 2026-08-16). In the 800x600
        # layout twin the pair is internally inconsistent IN STOCK: Query
        # 0x99887766 is 37 wide (95..132) while Route Query 0x8b96b73e
        # directly below is 36 (95..131) - and the ACTIVE G-96a006b0 layout
        # has both at 36. The #172 art clamp sizes the shared sheets to the
        # ruling 36x21 window, which would underfill the twin's 37px window
        # by R(f) px, and gate_btn_undercover rightly flags that at integer
        # tiers (the twin Query is the ONE button whose 1x cell exactly
        # filled its 1x window). Harmonize the twin to the pair width.
        # Scope: this .UI only (law 66), and the layout is unreachable
        # anyway - no tier package ever loads at 800x600. This is the second
        # deliberate area= exception after the marquee above.
        if fn.endswith("_G-08000600_I-c973b411.ui"):
            new_text, n_qp = re.subn(
                r'(id=0x99887766\s+)area=\(95,85,132,106\)',
                r'\g<1>area=(95,85,131,106)', new_text)
            if n_qp != 1:
                sys.exit("FATAL #172: query twin harmonization matched %d "
                         "times in %s (expected exactly 1 - the pristine "
                         "script changed, re-verify the pair's areas before "
                         "shipping the art clamp)" % (n_qp, fn))
            print("   #172 query pair: twin Query 0x99887766 width 37 -> 36 "
                  "((95,85,132,106) -> (95,85,131,106)) in %s" % fn)
        # #184 HUD PLATE TEXT SEAT (2026-08-17, refereed). The city HUD's
        # funds label 0x09e418fe and population label 0xc9e41918 in
        # I-2bc90671 ship align=lefttop, so the glyphs stay seated at the
        # TOP of a box the sweep scales - the user's "centered at 1x,
        # top-anchored scaled". The engine's CENTER mode is SELF-SCALING:
        # seat = (GetH()-textH)>>1, recomputed on every SetArea (0x9C20D3),
        # and the corpus uses the leftcenter token 533 times, so the token
        # path is proven. lefttop -> leftcenter, EXACTLY one attribute per
        # node, both nodes, BOTH GROUPS (G-96a006b0 active + the G-08000600
        # 800x600 twin - the #172 twin-edit pattern: an endswith on the
        # instance catches both, and the count guard is per file). The
        # [^<>]*? bridge cannot escape the node: every LEGACY node is
        # '<'...'>' delimited, and id= precedes align= inside the node.
        if fn.endswith("_I-2bc90671.ui"):
            new_text, n_seat = re.subn(
                r'(id=0x(?:09e418fe|c9e41918)\s[^<>]*?)align=lefttop',
                r'\g<1>align=leftcenter', new_text)
            if n_seat != 2:
                sys.exit("FATAL #184: HUD plate align rewrite matched %d "
                         "node(s) in %s (expected exactly 2: funds "
                         "0x09e418fe + population 0xc9e41918). The pristine "
                         "script changed - re-verify the plate labels "
                         "before shipping." % (n_seat, fn))
            print("   #184 HUD plate: funds 0x09e418fe + population "
                  "0xc9e41918 align lefttop -> leftcenter (2 nodes) in %s"
                  % fn)
        # #183 REGION BUBBLE POPULATION SEAT (2026-08-17, refereed). The
        # region-view city bubble's population figure 0xc9e41918 in
        # I-aa920991 ships align=lefttop where the 1x look seats it at the
        # BOTTOM of its 18px box. leftbottom is valign token 2,
        # byte-verified in the align deserializer at 0xAD584C-0xAD58A4;
        # ZERO stock uses of the token is fine and expected (documented -
        # the deserializer, not the corpus, is the proof it parses).
        # SCOPE STRICTLY BY SCRIPT, NEVER BY ID: the SAME id value
        # 0xc9e41918 is #184's population label in I-2bc90671 (leftcenter,
        # above) and also lives in I-898897de - a global rewrite of this id
        # would misalign both. The endswith covers the G-08000600 twin IF
        # one ever stages (none exists in the corpus today, checked
        # 2026-08-17), with the count guard per file.
        # KNOWN CONTINGENCY (documented for the eyes-on): if the runtime
        # sweep does not scale this label's own rect, bottom-align inside
        # an 18px box is a visual NO-OP - the safe direction; the eyes-on
        # adjudicates.
        if fn.endswith("_I-aa920991.ui"):
            new_text, n_bub = re.subn(
                r'(id=0xc9e41918\s[^<>]*?)align=lefttop',
                r'\g<1>align=leftbottom', new_text)
            if n_bub != 1:
                sys.exit("FATAL #183: region bubble align rewrite matched "
                         "%d node(s) in %s (expected exactly 1: population "
                         "0xc9e41918). The pristine script changed - "
                         "re-verify before shipping." % (n_bub, fn))
            print("   #183 region bubble: population 0xc9e41918 align "
                  "lefttop -> leftbottom (1 node) in %s" % fn)
        # ADVISOR STRIP SUBTREE (task #43, v2.20.0). The 7 advisor faces are
        # LIVE 3D head renders, and the game frames each head ONCE when it
        # BINDS it to its viewport window (binder exe 0x41DE20, slot-reuse on
        # later entries) - which happens during CITY LOAD, before any sweep of
        # ours can run. So a runtime-doubled button always framed from stale
        # 1x geometry -> quarter-zoomed faces until an advisor view switch
        # re-bound them (v2.19.3/.4/.5 chased this at runtime and could only
        # paper over it with a click flash the user could screenshot).
        # PROOF the bind-time geometry is what matters: the BRIEFING portrait
        # renders correctly, and its head is bound when the briefing is first
        # opened - i.e. after scaling.
        # Fix: ship the whole strip subtree pre-scaled, so the buttons are
        # already 2x when the heads are bound. The DLL makes the strip
        # root-only (kDataScaledSubtreeIds) so children are not scaled twice.
        if fn.endswith("_I-cbc905cd.ui") or fn.endswith("_I-4a160034.ui"):
            new_text, n_adv, lf_adv = double_subtree_areas(new_text, "6a15c767",
                                                   scale_len)
            if n_adv < 15:
                sys.exit("FATAL: advisor strip subtree matched only %d area= "
                         "in %s (expected >=15)" % (n_adv, fn))
            print("   advisor strip 0x6a15c767 subtree areas x%g (%d, %d art leaf/leaves SIZE-derived - #170) in %s"
                  % (FACTOR, n_adv, lf_adv, fn))
            # #152: the 7 faces are children of the SAME parent as their
            # frames, so double_subtree_areas rounded each independently and
            # their odd 1x y-offset of 1 did not survive f=1.5. Seat them on
            # the frame's MEASURED art aperture. Runs after the subtree scale
            # and after the art is staged (STAGE is filled well before the .UI
            # loop opens), so the pixels it measures are the ones we ship.
            new_text, seated = seat_faces_on_apertures(
                new_text, ADVISOR_FACE_SEATS, STAGE, fn)
            print("   advisor faces seated on art aperture x%g (%d moved) in %s"
                  % (FACTOR, len(seated), fn))
            # THE NO-OP AT AN INTEGER FACTOR IS ASSERTED, NOT ASSUMED.
            # For integer N, scale_len(v) = vN exactly, so
            # N*frame + N*(face-frame) == N*face and every delta is (0,0).
            # If that ever stops being true the build STOPS - 2x and 3x are
            # user-confirmed and must not move.
            if abs(FACTOR - round(FACTOR)) < 1e-9 and seated:
                sys.exit("FATAL: seat pass moved %d windows at integer factor "
                         "%g - it MUST be a no-op there" % (len(seated), FACTOR))
            if abs(FACTOR - 1.5) < 1e-9 and len(seated) != 7:
                sys.exit("FATAL: seat pass moved %d/7 at 1.5x in %s"
                         % (len(seated), fn))
        # MONTHLY BUDGET FAMILY (v2.25.24, final architecture): a MULTI-ROOT
        # COMPOSED PANEL like Graphs. BOTH scripts carry FOUR top-level
        # roots (Taxes editor popup 0xAA3AC002, "Take Out A Loan" popup
        # 0xCA4C332D, expanded/department detail frame 0xAA3AC001, balance
        # bar 0xAA3AC000) which the game composes,
        # -- #102 COMMENT-ONLY CORRECTION (2026-08-03): this block used to
        # say "income 0xAA3AC002, expense 0xCA4C332D", contradicting
        # SCALED_WINDOW_IDS above IN THIS SAME FILE (line ~169) which has
        # always said "Taxes editor popup" / "Take Out A Loan popup".
        # Decided by live capture (0xAA3AC002 arrives 500x464 at (158,40) =
        # I-cbc3c2b9 to the pixel) plus that script's own captions
        # ("Taxes", per-RCI rate editors, Accept/Cancel). NO GENERATED
        # OUTPUT CHANGES - the four root ids and the doubling are untouched.
        # anchors and re-lays at runtime from script-cached geometry -
        # children must be BORN 2x in DATA (markers stay 1x; the doubler
        # skips them) while the sweep scales + anchors each root
        # (kDataScaledSubtreeIds). Full static doubling of any root broke
        # the composition; runtime child-scaling never stuck.
        if fn.endswith("_I-aa3acdfe.ui") or fn.endswith("_I-cbc3c2b9.ui"):
            for broot in ("aa3ac002", "ca4c332d", "aa3ac001", "aa3ac000"):
                new_text, n_bud, lf_bud = double_subtree_areas(new_text, broot,
                                                       scale_len)
                if n_bud < 5:
                    sys.exit("FATAL: budget subtree 0x%s matched only %d "
                             "area= in %s (expected >=5)" % (broot, n_bud, fn))
                print("   budget 0x%s subtree areas x%g (%d, %d art leaf SIZE-derived) in %s"
                      % (broot, FACTOR, n_bud, lf_bud, fn))
        # GRAPHS panel (2026-07-30, user report "Graphs flyout still broken").
        # Log-proven double-scale: the deployed build's own DGPKID dumps show
        # all three roots perfectly placed (5b72 at 5b71+(0,604), band at
        # +(10,648)) while "incremental panel 0x8A8B5B71 - 1 windows scaled"
        # fires every 1-2 s - the game RE-CREATES a chart child per data
        # refresh, born at live (already-2x) size, and the sweep doubled it
        # again: the 4x canvas is the off-screen white sheet (design
        # (14,32,502,288) x4 -> right edge ~2998 at root abs 990), and the
        # radio columns sat at x4 offsets (design 0/170/340 -> live 0/680/
        # 1360). Same class as the advisor strip: children must be BORN 2x in
        # DATA and the runtime sweep must stop at the root
        # (kDataScaledSubtreeIds in UiSpike.cpp - all three roots added).
        # Markers (0x0000AAAA) stay 1x per the alignment-marker law (the
        # doubler skips them).
        if fn.endswith("_I-6bc9065a.ui") or fn.endswith("_I-ea2871aa.ui"):
            for groot, floor_n in (("8a8b5b71", 8), ("8a8b5b72", 4),
                                   ("0a4a8176", 15)):
                new_text, n_g, lf_g = double_subtree_areas(new_text, groot,
                                                    scale_len)
                if n_g < floor_n:
                    sys.exit("FATAL: Graphs subtree 0x%s matched only %d "
                             "area= in %s (expected >=%d)"
                             % (groot, n_g, fn, floor_n))
                print("   Graphs 0x%s subtree areas x%g (%d) in %s"
                      % (groot, FACTOR, n_g, fn))
        # U-DRIVE-IT DASHBOARD FAMILY (2026-07-30, "duplicate dials"). The
        # gauge windows' PIXEL BUFFER ([win+0x6c], GetBufferToDrawTo) is
        # allocated at FIRST PAINT from the window's then-current size. The
        # consoles were runtime-swept, so the game painted once at 1x before
        # the sweep doubled the windows -> every gauge pbuff born 71x71 ->
        # the hook's correct 136x120 needle draws CLIP into it -> at REST the
        # engine composites the clipped buffer = the small top-left dial;
        # while DRIVING the active draws go direct = the full dial (GBLT-
        # measured: 30/30 Plot draws scaled, artifact persists at rest).
        # Same born-2x law as the advisor strip / Graphs: children must be
        # 2x in DATA so first paint allocates a 2x buffer. Applies to ALL 43
        # console scripts (root 0x4BCB938A); the DLL adds the root to
        # kDataScaledSubtreeIds. Markers stay 1x (doubler skips them).
        if "id=0x4bcb938a" in new_text:
            new_text, n_dash, lf_dash = double_subtree_areas(new_text, "4bcb938a",
                                                    scale_len)
            if n_dash < 3:
                sys.exit("FATAL: dashboard subtree matched only %d area= "
                         "in %s (expected >=3)" % (n_dash, fn))
            print("   dashboard 0x4bcb938a subtree areas x%g (%d, %d art leaf SIZE-derived) in %s"
                  % (FACTOR, n_dash, lf_dash, fn))
        # #93 (v2.48.0) THE FIFTH CONSOLE VARIANT. I-8c1a5c9f declares its
        # OWN root id 0xEC1A5CBF (463x132 - the same design footprint as the
        # four scripts above, and like them winflag_pbuff=yes), so the
        # `id=0x4bcb938a` test right above never matches it. It was in NO
        # list on EITHER side: no data doubling and no runtime entry, so a
        # swept 2x root would sit over 1x children - the same clipped-buffer
        # defect the 43 siblings had before v2.25.14 (child pbuffs allocated
        # at first paint from 1x geometry, correct 2x draws clipping into
        # them). Same cure, both halves: children 2x in DATA here, root in
        # kDataScaledSubtreeIds so the sweep scales the root and stops.
        # âš  EXPECT 1, NOT 3. double_subtree_areas deliberately does NOT
        # touch the root's own area (the DLL scales the root at runtime to
        # keep its HUD anchoring), and this script is root + ONE button - so
        # exactly ONE descendant area=. Reusing the dashboard's >=3 would
        # FATAL the build on a correct file: an expectation belongs to the
        # file it describes. (The first draft of this guard said >=2 and the
        # build stopped - the guard working, not the data being wrong.)
        if "id=0xec1a5cbf" in new_text:
            new_text, n_var, lf_var = double_subtree_areas(new_text, "ec1a5cbf",
                                                   scale_len)
            if n_var < 1:
                sys.exit("FATAL: console-variant 0xec1a5cbf subtree matched "
                         "no area= in %s (expected >=1)" % fn)
            print("   console variant 0xec1a5cbf subtree areas x%g (%d, %d art leaf SIZE-derived) in %s"
                  % (FACTOR, n_var, lf_var, fn))
        # HUD DOCK FAMILY (2026-08-01, task #89: "corrupted map on city
        # open"). The dock's art ships DOUBLED IN PLACE from package load
        # (sheet 0x13D14CA0 is EXCLUSIVE/2x-in-place, and 0x0987B48F is in
        # SCALED_WINDOW_IDS above), but its WINDOWS stayed at design size
        # until the runtime sweep - which was MEASURED at +766ms to +2250ms
        # after city arm. For that whole interval 2x art draws into 1x-sized
        # windows, and that is the corruption the user sees.
        #
        # It cannot be fixed by running the sweep sooner: a posted-WM_APP
        # channel beat WM_TIMER by 15ms (one timer period) because the game
        # does not pump messages at all during the load tail. Refuted and
        # reverted in v2.41.0; see _tests\REGRESSION.md task #89.
        #
        # So it is cured the way the advisor faces were (task #43): the
        # children ship ALREADY 2x, and the DLL scales the ROOT only
        # (0x0987B48F added to kDataScaledSubtreeIds). Same split as the
        # U-Drive-It dashboard above. BOTH HALVES SHIP TOGETHER - data-
        # doubled children plus a recursing sweep is 4x. Markers 0x0000AAAA
        # stay 1x (the doubler skips them - doubling the advisor strip's
        # marker shifted its whole box by -(229,63)).
        # â›” DO NOT DATA-DOUBLE ANYTHING IN THE HUD DOCK (0x0987B48F).
        # Tried BOTH forms on 2026-08-01 (task #89) and both broke the dock:
        #   * whole subtree + kDataScaledSubtreeIds (v2.41.1) -> ScalePanelRoot
        #     RETURNS EARLY at the root, which also killed the god/mayor flyout
        #     DOCKING that runs inside that child recursion. Every flyout came
        #     unstuck from its spawn button.
        #   * the minimap ALONE + kDataScaledWindowIds (v2.41.2) -> the dock's
        #     rect is the UNION OF ITS CHILDREN WITH NO CLAMP
        #     (CITY-DOCK-OVERLAP.md). A child pre-doubled to (36,144)-(164,272)
        #     hangs past the 235x223 design frame, the union grows, and the
        #     bottom-anchored dock drags the map outside the window.
        # Both reverted in v2.41.3. The dock is runtime-scaled ONLY. Any future
        # attempt must first answer what the union rect does at load time.
        # THE PARITY NUDGE WAS CALLED HERE AND IS REVERTED (2026-08-06, same
        # day). See parity_nudge_btn_areas for the measurement and the reason.
        # The same defect is now fixed in the DLL, by changing the WIDTH instead
        # of the POSITION - see UiSpike.cpp, kLeafSizeDerived.
        new_text = FONT_NAME_RE.sub(font_sub, new_text)
        if font_sub.converted:
            print("   font-token GUIDs %s: %s" % (fn, ", ".join(
                "%s x%d" % kv for kv in sorted(font_sub.converted.items()))))
        if font_sub.unknown:
            print("   font-token UNMAPPED in %s: %s" % (fn, ", ".join(sorted(font_sub.unknown))))
        m = re.match(r"T-00000000_G-([0-9a-f]{8})_I-([0-9a-f]{8})\.ui", fn)
        out_name = "T-0x%08x_G-0x%s_I-0x%s.ui" % (UI_TYPE, m.group(1), m.group(2))
        # BUDGET MASTERS ARE OWNED BY DIALOG-STATIC (2026-07-30). This dat
        # previously shipped its clone-retargeted (1x-geometry) copies of
        # these two scripts AND loads after DialogStatic alphabetically, so
        # it silently OVERRODE the doubled versions - the entire "budget
        # dialogs bypass the override" mystery was this dat winning the load
        # race against our own DialogStatic. dialog-static's copies are
        # self-consistent (its own global art plan retargets/doubles the
        # same refs), so this builder simply must not emit them.
        # (v2.25.24: the budget scripts ship from HERE again, with all four
        # roots' children data-doubled above - dialog-static is fully out
        # of the budget family.)
        with open(os.path.join(STAGE, out_name), "w", encoding="latin-1", newline="") as f:
            f.write(new_text)
        edit_stats.append((fn, n_ret, n_dbl, new_text == text))

    print("\nEdited .UI files (%d):" % len(edit_stats))
    for fn, n_ret, n_dbl, same in edit_stats:
        print("   %-42s retargets=%-3d rectx2=%-3d%s"
              % (fn, n_ret, n_dbl, "  [UNCHANGED]" if same else ""))
    if edge_no_rect:
        print("note: %d scaled edgeimage=yes controls have no imagerect attr" % edge_no_rect)
    if left_1x_controls:
        print("note: %d scaled image refs left at 1x (no 2x asset in upscale set)" % left_1x_controls)
    for (gid, iid, kind) in sorted(left_1x_warned):
        print("WARNING LEFT1X {%08x,%08x} in a SCALED frame: %s" % (gid, iid, kind))

    # ---- refmap.csv ----
    with open(REFMAP_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["TypeID", "GroupID", "InstanceID", "classification", "occurrences",
                    "n_files", "scaled_files", "unscaled_files", "twox_available",
                    "action", "clone_GroupID", "clone_InstanceID"])
        for (gid, iid) in sorted(refs):
            rec = refs[(gid, iid)]
            if (gid, iid) in clones:
                cls, act = "SHARED", "clone+retarget"
                cg, ci = clones[(gid, iid)]
                cg, ci = "0x%08X" % cg, "0x%08X" % ci
            elif rec["scaled"] and rec["unscaled"]:
                cls, act, cg, ci = "SHARED", "left-1x (no 2x asset)", "", ""
            elif rec["scaled"]:
                cls = "EXCLUSIVE"
                act = "2x-in-place" if avail[(gid, iid)] else "left-1x (no 2x asset)"
                cg = ci = ""
            else:
                cls, act, cg, ci = "UNSCALED", "untouched", "", ""
            w.writerow(["0x%08X" % PNG_TYPE, "0x%08X" % gid, "0x%08X" % iid, cls,
                        rec["count"], len(rec["scaled"] | rec["unscaled"]),
                        ";".join(sorted(rec["scaled"])), ";".join(sorted(rec["unscaled"])),
                        "yes" if avail[(gid, iid)] else "no", act, cg, ci])
    print("\nWrote " + REFMAP_CSV)

    # ---- THIRD-PARTY .UI OVERRIDES (task #44, 2026-07-29) ---------------
    # A plugin can REPLACE a stock .UI script wholesale. CoriBoom's 36 Slot
    # Building Styles UI (shipped inside the allow-more-building-styles-dll
    # sc4pac) overrides {0,0x96A006B0,0x6BC61F19} - the Building Style
    # Control panel - from Plugins\150-mods\, a SUBFOLDER. By the LOAD-ORDER
    # LAW (root files load BEFORE subfolders) our root package can never win,
    # so the 2x edit of the STOCK script above has NEVER taken effect: the
    # game builds the mod's 73-window layout with 1x imagerects while the
    # sweep doubles the windows and our 2x art lands underneath. Symptoms
    # (user 2026-07-29): checkbox rows overlapping, the expanded style list
    # floating over a pale box, its second column hidden, and the mod's own
    # checkboxes stranded over the terrain (background art covering only the
    # top-left quarter of each doubled window).
    #
    # Fix: take the MOD's script as the source (never the stock one - that
    # would revert its 36-slot UI), apply the SAME transformations, and ship
    # it from zzz-SC4UIScale\ which sorts after 150-mods\. Same mechanism as
    # the ItemIconsSub icon overrides.
    # STANDING ORDER: this overrides another mod's data -> memory entry +
    # tools\research\UPSTREAM-CAM-REPORT.md-style developer callout.
    # v2.43.0 (task #94): the flow below is now PER MOD GROUP, because each
    # override must be GATED ON ITS OWN MOD (ScaleTier::kThirdPartyDeps). One
    # shared package would disable CoriBoom's Building Styles copy when the
    # warrior terraforming mod is removed, and vice versa - the gate would be
    # lying about which dependency it holds.
    #   thirdparty-ui\*.ui              -> z_SC4UIScale_ThirdPartyUI.dat  (legacy,
    #                                       CoriBoom; art from thirdparty-art\*.png)
    #   thirdparty-ui\<Name>\*.ui       -> z_SC4UIScale_<Name>.dat
    #                                       (art from thirdparty-art\<Name>\*.png)
    # Adding a mod = drop its scripts+art in a NEW subfolder and add its
    # kThirdPartyDeps row IN THE SAME CHANGE (standing order).
    tp_src_dir = os.path.join(OUT_DIR, "thirdparty-ui")
    tp_art_root = os.path.join(OUT_DIR, "thirdparty-art")
    tp_groups = []   # (pkg_base_name, [ui paths], art_dir_or_None, stage_suffix)
    if os.path.isdir(tp_src_dir):
        legacy_ui = [os.path.join(tp_src_dir, f)
                     for f in sorted(os.listdir(tp_src_dir)) if f.endswith(".ui")]
        if legacy_ui:
            tp_groups.append(("ThirdPartyUI", legacy_ui,
                              tp_art_root if os.path.isdir(tp_art_root) else None,
                              ""))
        for sub in sorted(os.listdir(tp_src_dir)):
            subdir = os.path.join(tp_src_dir, sub)
            if not os.path.isdir(subdir):
                continue
            uis = [os.path.join(subdir, f)
                   for f in sorted(os.listdir(subdir)) if f.endswith(".ui")]
            if not uis:
                continue
            art = os.path.join(tp_art_root, sub)
            tp_groups.append((sub, uis, art if os.path.isdir(art) else None,
                              "-" + sub.lower()))

    for (tp_pkg_name, tp_ui_files, tp_art_dir, tp_sfx) in tp_groups:
        tp_stage = os.path.join(OUT_DIR,
                                "stage-thirdparty" + tp_sfx + ("-" + TAG if TAG else ""))
        # Clear CONTENTS, never the directory itself: these trees live under
        # OneDrive, which holds a handle on the folder and makes rmdir fail with
        # WinError 5 even though the files delete fine.
        fresh_dir(tp_stage)
        tp_stats = []
      # #95: the art is upscaled BEFORE the scripts are edited - the
      # imagerect invariant clamps against the art that will SHIP, and
      # doing this after the script loop silently compared the MOD's
      # rect against the STOCK upscale (the clamp report caught it).
        tp_art_src = tp_art_dir
        n_tp_art = 0
        if tp_art_src and os.path.isdir(tp_art_src) and [f for f in os.listdir(tp_art_src) if f.lower().endswith(".png")]:
            up_tmp = os.path.join(OUT_DIR, "thirdparty-art-up" + tp_sfx
                                + (("-" + TAG) if TAG else ""))
            fresh_dir(up_tmp)
            # #157: see the twin call in build_dialog_static.py. A third-party
            # 9-slice frame must be sized by CellUnit {3} like a stock one.
            # Zero third-party sheets match today - wired so the next one cannot
            # inherit the defect silently.
            r = subprocess.run([os.path.join(TOOLS, "upscale", "Upscale2x.exe"),
                                tp_art_src, up_tmp, "--factor", str(FACTOR),
                                "--normalize-names", "--nine-slice",
                                os.path.join(TOOLS, "upscale", "nine-slice.txt"),
                                "--no-snap",
                                os.path.join(TOOLS, "upscale", "no-snap.txt"),
                                # #169: an N-state strip's contract is
                                # cell == round(w1x * f) PER STATE. Without the
                                # derived state count the sheet is scaled as ONE
                                # image and then snapped to stay divisible by N,
                                # which restores divisibility while breaking the
                                # PITCH: the 7 advisor sheets went 220 -> 332, so
                                # the engine's 332/4 = 83 cut drifted against the
                                # true 82.5 and every state bled a sliver of the
                                # next one to the RIGHT of its icon.
                                "--cell-strips",
                                os.path.join(TOOLS, "upscale", "cell-strips.txt"),
                                # F12 (review 2026-08-16): the corpus rebuild
                                # (Rebuild-Corpus.ps1) treats all five derived
                                # lists as mandatory; this invocation carried
                                # only three, so a third-party strip would
                                # ship a DIFFERENT HEIGHT than the stock rule
                                # (#177) and a seat-measured sheet could be
                                # smoothed out from under its scan (#175).
                                "--no-smooth",
                                os.path.join(TOOLS, "upscale", "no-smooth.txt"),
                                "--height-exact-strips",
                                os.path.join(TOOLS, "upscale",
                                             "height-exact-strips.txt"),
                                # #185 second occurrence (review finding 6):
                                # the hand-authored slab table rides the same
                                # flag - the parser appends per occurrence.
                                "--height-exact-strips",
                                os.path.join(TOOLS, "upscale",
                                             "height-exact-slabs.txt")],
                             capture_output=True, text=True)
            if r.returncode != 0:
                sys.exit("THIRD-PARTY ART UPSCALE FAILED:\n" + r.stderr + r.stdout)
            for f in sorted(os.listdir(up_tmp)):
                if f.lower().endswith(".png"):
                    shutil.copy2(os.path.join(up_tmp, f),
                               os.path.join(tp_stage, f))
                    n_tp_art += 1
            print("   third-party ART upscaled x%g and staged: %d file(s)"
                % (FACTOR, n_tp_art))

        for tp_path in tp_ui_files:
            tp_fn = os.path.basename(tp_path)
            m = re.match(r"T-(\w{8})_G-(\w{8})_I-(\w{8})\.ui", tp_fn)
            if not m:
                sys.exit("FATAL: third-party UI name not TGI-shaped: " + tp_fn)
            with open(tp_path, "r", encoding="latin-1") as f:
                tp_text = f.read()
            tp_roots = parse_ui(tp_text)
            # Every window in a third-party override is treated as scaled: the
            # DLL scales this panel's whole subtree at runtime (73 windows,
            # confirmed live), so every imagerect in it must follow its art.
            tp_edits = []
            n_ret = n_dbl = 0
            for nd in walk(tp_roots):
                if not nd.images:
                    continue
                art_doubled = False
                tp_last_art = None       # #95
                for (gid, iid, vs, ve) in nd.images:
                    key = (gid, iid)
                    if key in clones:
                        cg, ci = clones[key]
                        tp_edits.append((vs, ve, "{%08x,%08x}" % (cg, ci)))
                        n_ret += 1
                        art_doubled = True
                    elif key in refs and avail.get(key) and key in exclusive:
                        art_doubled = True       # 2x in place at the same TGI
                    elif key in [(g, i) for (g, i) in cb_staged]:
                        art_doubled = True       # code-bound, staged 2x in place
                    if art_doubled and tp_last_art is None:
                        tp_last_art = key
                if art_doubled and nd.imagerect is not None:
                    (l, t, r, b), vs, ve = nd.imagerect
                    # #95 THE IMAGERECT INVARIANT. This is the site that
                    # shipped the warrior rail 42px short: the mod's own
                    # script over-reads its bitmap and we doubled the
                    # over-read. Clamp to the art we actually staged.
                    ap = None
                    if tp_last_art is not None:
                        ag, ai = tp_last_art
                        if (ag, ai) in clones:
                            ag, ai = clones[(ag, ai)]
                        for cand in (os.path.join(tp_stage, tgi_png_name(ag, ai)),
                                     os.path.join(UPSCALE_DIR, tgi_png_name(ag, ai))):
                            if os.path.isfile(cand):
                                ap = cand
                                break
                    cl, ct, cr, cb2 = clamp_rect_to_art(
                        l, t, r, b, ap,
                        tp_last_art[0] if tp_last_art else 0,
                        tp_last_art[1] if tp_last_art else 0)
                    tp_edits.append((vs, ve, "(%d,%d,%d,%d)" % (cl, ct, cr, cb2)))
                    n_dbl += 1
            tp_new = tp_text
            for (s, e, rep) in sorted(tp_edits, key=lambda x: -x[0]):
                tp_new = tp_new[:s] + rep + tp_new[e:]

            def tp_font_sub(m2):
                guid = FONT_GUIDS.get(m2.group(1))
                return ("font=" + guid) if guid else m2.group(0)
            tp_new = FONT_NAME_RE.sub(tp_font_sub, tp_new)
            out_name = "T-0x%s_G-0x%s_I-0x%s.ui" % (m.group(1), m.group(2), m.group(3))
            with open(os.path.join(tp_stage, out_name), "w",
                    encoding="latin-1", newline="") as f:
                f.write(tp_new)
            tp_stats.append((tp_fn, n_ret, n_dbl))
            print("   third-party UI %s: retargets=%d rectx%g=%d"
                % (tp_fn, n_ret, FACTOR, n_dbl))
        # THIRD-PARTY ART (2026-07-29, the second half of task #44). A plugin can
        # also ship its OWN version of a stock art TGI, and by the same load-order
        # law that beats our root package. CoriBoom ships
        # {0x856DDBAC,0x46A006B0,0xCBC3C2B9} at 516x654 - TALLER than the stock
        # 516x396, because its panel has 36 style slots - so our root 2x copy
        # (built from the stock art) lost, and the game drew a 1x background in
        # the correctly-doubled 2x window: art present only in the top-left
        # ~516x654 corner, the rest bare. MEASURED, not guessed: DPROBE showed the
        # background window 0xEBC619DC at 1038x1308 (exact 2x) while the drawn art
        # covered ~516x654.
        # Fix: upscale the MOD'S OWN art with the project upscaler and ship it in
        # the same zzz- package as the script. Any art dropped in thirdparty-art\
        # is handled; drop in the mod's original PNG (its real dimensions matter -
        # never the stock one).

        if tp_stats or n_tp_art:
            tp_out = os.path.join(
                PKG_DIR if TAG else OUT_DIR,
                "z_SC4UIScale_%s%s.dat" % (tp_pkg_name, ("-" + TAG) if TAG else ""))
            r = subprocess.run([PACKER, tp_stage, tp_out],
                             capture_output=True, text=True)
            if r.returncode != 0:
                sys.exit("THIRD-PARTY PACK FAILED:\n" + r.stderr)
            print("   packed %s (%d entries: %d script(s) + %d art)"
                % (os.path.basename(tp_out), len(tp_stats) + n_tp_art,
                   len(tp_stats), n_tp_art))

    # ---- pack ----
    n_staged = len(os.listdir(STAGE))
    if _rect_clamped:
        print("IMAGERECT CLAMPED (#95 invariant - the rect asked for pixels the")
        print("art does not have; propagating it draws a SHORT strip):")
        for (g, i, asked, actual) in _rect_clamped:
            print("   {%08x,%08x}: asked %dx%d -> art is %dx%d"
                  % (g, i, asked[0], asked[1], actual[0], actual[1]))
        print("   (%d clamp(s). Upstream over-reads are clamped, never doubled.)"
              % len(_rect_clamped))
    if _parity_nudged:
        # NEVER SILENT. A position change nobody printed is how a 1px defect
        # survives nine sessions.
        print("PARITY-NUDGED state-strip buttons (#148, fractional tiers only - "
              "l*%g must be integral or the edge-derived width loses a pixel):"
              % FACTOR)
        for (fnm, wid, old, new) in _parity_nudged[:10]:
            print("   %-42s %-12s (%d,%d) -> (%d,%d)"
                  % (fnm, wid, old[0], old[1], new[0], new[1]))
        if len(_parity_nudged) > 10:
            print("   ... and %d more" % (len(_parity_nudged) - 10))
        print("   (%d nudge(s). EXPECT 0 AT AN INTEGER FACTOR.)"
              % len(_parity_nudged))
    # #181 COLOUR-KEY INTEGRITY GATE - the stage is the last stop before the
    # pack, so key damage caught here can never ship. Magenta 0xFF00FF is the
    # engine's EXACT-match transparency key: the gate fails the build on any
    # near-key pixel (the #143 "pink" class - an averaged key the exact-match
    # test misses and DRAWS) and on any drift of a sheet's exact-key pixel set
    # from the upscaler's own nearest-neighbour map. It resolves our clone
    # TGIs (I xor CLONE_XOR) back to their 1x sources, honours the #180 ladder
    # re-lay at fractional factors, and demands full key-set equality on the
    # dock sheet - so if neutralize_dock_recess() above ever grows into a key
    # pixel this goes red BY DESIGN, not as a false positive. Proves its own
    # teeth via --selftest; see _tests\REGRESSION.md #181.
    _gate = os.path.join(TOOLS, "upscale", "gate_key_integrity.py")
    # #186: the pinned family is a FACTOR-3 corpus product at EVERY tier, and
    # two of its sheets are KEYED (e78ffc90: 12 px, 46a006a5: 879 px), so the
    # tier-factor NN key model cannot describe them at 1.5x/2x and R2 would
    # go red on CORRECT art. GATE ON THE CONDITION YOU DEPEND ON: the
    # condition is "output == NN(source) at the factor that PRODUCED it",
    # and this family's producing factor is pinned at 3. So the pinned
    # members get their own run at factor 3 - same instrument, full R1+R2
    # teeth, and integer f=3 is the STRICTER R3 control (ladder exemption
    # removed) - while the rest of the stage keeps the tier-factor run
    # unchanged. No exemption class, no skipped sheet: every staged PNG
    # passes through exactly one full gate run.
    _gate_runs = [("stage", STAGE, FACTOR)]
    _pin_gate_dir = None
    if fixed96_pinned:
        _pin_gate_dir = os.path.join(
            OUT_DIR, "stage-bubble96-gate" + (("-" + TAG) if TAG else ""))
        fresh_dir(_pin_gate_dir)
        for (g2, i2) in fixed96_pinned:
            os.replace(os.path.join(STAGE, tgi_png_name(g2, i2)),
                       os.path.join(_pin_gate_dir, tgi_png_name(g2, i2)))
        _gate_runs.append(("#186 pinned fixed-96 family", _pin_gate_dir,
                           float(MISSION_BUBBLE_FIXED96_MULT)))
    for (_gl, _gd, _gf) in _gate_runs:
        r = subprocess.run([sys.executable, _gate, "--dir", _gd,
                            "--factor", str(_gf)],
                           capture_output=True, text=True)
        if r.stdout:
            print(r.stdout.rstrip())
        if r.returncode != 0:
            sys.exit("KEY-INTEGRITY GATE FAILED on %s (exit %d): the staged "
                     "art carries colour-key damage - NOT packing. Fix the "
                     "corpus (or the gate's model, if the corpus is proven "
                     "right), then rebuild.\n%s"
                     % (_gl, r.returncode, r.stderr))
    if _pin_gate_dir:
        # Put the pinned members back before the pack sees the stage.
        for (g2, i2) in fixed96_pinned:
            os.replace(os.path.join(_pin_gate_dir, tgi_png_name(g2, i2)),
                       os.path.join(STAGE, tgi_png_name(g2, i2)))
    print("Stage files total: %d -> packing..." % n_staged)
    r = subprocess.run([PACKER, STAGE, OUT_DAT], capture_output=True, text=True)
    print(r.stdout.strip())
    if r.returncode != 0:
        sys.exit("PACK FAILED:\n" + r.stderr)
    r = subprocess.run([PACKER, "--list", OUT_DAT], capture_output=True, text=True)
    listing = r.stdout
    n_listed = sum(1 for line in listing.splitlines()
                   if re.match(r"0x[0-9A-Fa-f]{8} 0x[0-9A-Fa-f]{8} 0x[0-9A-Fa-f]{8} ", line))
    size = os.path.getsize(OUT_DAT)
    print("Packed %s: %d entries listed (staged %d), %d bytes"
          % (os.path.basename(OUT_DAT), n_listed, n_staged, size))
    with open(PKG_LIST, "w", encoding="utf-8") as f:
        f.write(listing)

    # ---- summary ----
    print("\n=== SUMMARY ===")
    print("UI files parsed: %d ; scaled-window files: %d" % (len(ui_files), len(scaled_files)))
    print("Distinct refs: %d = exclusive %d + shared %d + unscaled-only %d"
          % (len(refs), len(exclusive), len(shared), len(unscaled_only)))
    print("Exclusive 2x staged: %d (missing 2x: %d)" % (n_excl_staged, n_excl_missing))
    print("Shared clones staged: %d (missing 2x: %d)" % (n_shared_staged, n_shared_missing))
    print("Code-bound 2x staged: %d (conflict %d / already-handled %d / missing 2x %d)"
          % (len(cb_staged), len(cb_conflict), len(cb_handled), len(cb_missing)))
    print("Edited .UI staged: %d" % len(edit_stats))
    print("Package: %s (%d bytes, %d entries)" % (OUT_DAT, size, n_listed))


if __name__ == "__main__":
    main()
