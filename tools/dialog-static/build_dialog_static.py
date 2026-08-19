#!/usr/bin/env python3
r"""
Static-2x builder for the ELEVEN region-screen dialogs/popups -- SC4 UI scaling.

Approach (FONTS-AND-DIALOGS.md Q2 recipe, user-VALIDATED in-game on the Load
Region dialog): edit each dialog's .UI script so the game CREATES the dialog
already doubled and lays out its children itself.  No runtime scaling involved
(runtime docking of the region-dialog roots is disabled).

Target scripts (group 0x96A006B0, shipped at their ORIGINAL TGIs as same-TGI
overrides):
  I-0a7df315  Play Options
  I-ca53f06e  Audio Options
  I-8a7e052f  Graphic Options
  I-8a5ab1cb  Region Name (Create Region)
  I-8a5ab1ce  Delete Region confirm
  I-8a5ab1cc  Load Region (the validated prototype, re-emitted through the
              same pipeline so everything lives in one dat)
  I-4a551b4c  Quit confirm, region screen ("Quit SimCity 4" / "Cancel")
  I-8a5ab1cf  Quit confirm, "Are you sure you want to quit SimCity 4?"
              variant (Accept/Cancel) -- both quit candidates are quit
              dialogs, so both are included
  I-0a8cd184  Start New City bubble (tail-anchored region-screen popup;
              the game positions it -- tail at the clicked tile -- so only
              SIZES change, which is safe)
  I-ca539340  Existing-city bubble (city name, star, Mayor Rating, funds,
              population, gift/demolish/play buttons; same tail-anchored
              popup root 0x0a551c50 as Start New City)
  I-4a8cc5ea  Photo Album dialog (albums list, snapshot viewfinder pane,
              description edit, Close; the viewfinder pane is inside this
              same script)

Candidates inspected and EXCLUDED:
  I-0b72f276 and I-ea287193 -- 96-107 KB city-HUD region-view panels
  ("Map View"/"Data Views"/zone legend), not region-screen bubbles.
  I-49889894 -- 476x43 bottom strip, not a dialog.

Edits made to every script:
  1. EVERY area=(x1,y1,x2,y2) doubled (corner-format absolute pixels; the
     first id= in a file is not always the meaningful root, so ALL areas are
     doubled regardless -- Play Options/Graphic Options root gens are larger
     than the visible dialog art and that is fine).
  2. Every image={gid,iid}: if a 2x PNG exists in tools\upscale\preview and
     the TGI is referenced by ANY .UI file outside these six that is not
     already 2x-handled by selective-safe, stage a 2x CLONE at
     iid ^ 0x53430001 (collision-checked against the full PNG store, the
     corpus ref set, selective-safe's planned clones AND the clones created
     for the other dialogs in this same run; falls back to ^ 0x53430002 on
     collision) and retarget the ref at the clone.  Art exclusive to the six
     scripts is staged 2x in place.  No 2x asset -> ref and its imagerect
     stay 1x (reported).  The art plan is GLOBAL: a TGI shared by several of
     the six dialogs gets ONE decision / ONE staged PNG, every ref
     retargeted consistently.
  3. imagerect=(l,t,r,b) doubled ONLY on controls whose art went 2x
     (bitmap-pixel rect; must track the bitmap).
  4. font=NAME converted to the GUID form (font=0x........) via the style
     table in tools\fonts\FontStyle.candidate.ini -- the proven deserializer
     path (type-6 token -> SetFontStyleByGUID); unmappable names reported.
     Fonts are confirmed loading in-game, so this is belt-and-braces
     consistency, not the size fix.

Every edited script is re-parsed and machine-verified against the original
(node-for-node: areas exactly doubled, refs retargeted per plan, imagerects
doubled iff art went 2x, fonts in GUID form) before packing.

Output: tools\dialog-static\stage\ + z_SC4UIScale_DialogStatic.dat + REPORT.md.
Nothing outside tools\dialog-static\ is modified; nothing is deployed.

Parser reused from tools\selective-safe\build_selective_safe.py (LEGACY markup,
quote-aware character scan), extended to capture area= and font= attributes.
"""

import argparse
import csv
import json
import math
import os
import re
import zlib
import shutil
import struct
import subprocess
import sys
from collections import Counter, defaultdict

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
FONT_INI = os.path.join(TOOLS, "fonts", "FontStyle.candidate.ini")
PACKER = os.path.join(TOOLS, "dbpf", "DbpfPack.exe")

OUT_DIR = os.path.join(TOOLS, "dialog-static")

# ---------------------------------------------------------------------------
# Scale factor N (default 2 = bit-identical to the original static-2x build).
# N=1.5 and N=3 emit factor-tagged packages into tools\packages\<tag>\ and read
# the matching selective-safe refmap (refmap-<tag>.csv) so the clone-collision
# checks stay consistent across the two dats of the same tier. area=, imagerect=,
# rowheight/gutters/etc. all scale by N with round-half-up (floor(v*N + 0.5));
# for N=2/3 that is exactly v*N. Clone-IID scheme + font GUIDs are unchanged.
# The tag goes in the BASE filename before .dat (z_SC4UIScale_DialogStatic-15x.dat).
# ---------------------------------------------------------------------------
_ap = argparse.ArgumentParser(description="Region-screen dialog static-scale builder (factor-parametric).")
_ap.add_argument("--factor", type=float, default=2.0,
                 help="scale factor: 2 (default, bit-identical), 1.5, or 3")
_args, _ = _ap.parse_known_args()
FACTOR = _args.factor


def _factor_tag(f):
    if abs(f - 2.0) < 1e-9:
        return ""
    if abs(f - 1.5) < 1e-9:
        return "15x"
    if abs(f - 3.0) < 1e-9:
        return "3x"
    if abs(f - round(f)) < 1e-9:
        return "%dx" % int(round(f))
    return ("%gx" % f).replace(".", "_")


TAG = _factor_tag(FACTOR)
FACTOR_LABEL = "%gx" % FACTOR   # "2x" / "1.5x" / "3x" for report prose


def scale_len(v):
    """Scale a pixel length by FACTOR, round-half-up. v*N exactly for integer N."""
    return int(math.floor(v * FACTOR + 0.5))


if TAG:
    UPSCALE_DIR = os.path.join(TOOLS, "upscale", "preview-%s" % TAG, "SimCity_1")
    REFMAP_CSV = os.path.join(TOOLS, "selective-safe", "refmap-%s.csv" % TAG)
    PKG_DIR = os.path.join(TOOLS, "packages", TAG)
    STAGE = os.path.join(OUT_DIR, "stage-%s" % TAG)
    OUT_DAT = os.path.join(PKG_DIR, "z_SC4UIScale_DialogStatic-%s.dat" % TAG)
    # detailed builder report stays in the dev dir; the shippable packages\<tag>\
    # folder holds only the two dats + the FontStyle ini.
    REPORT = os.path.join(OUT_DIR, "REPORT-%s.md" % TAG)
else:
    UPSCALE_DIR = os.path.join(TOOLS, "upscale", "preview", "SimCity_1")
    REFMAP_CSV = os.path.join(TOOLS, "selective-safe", "refmap.csv")
    STAGE = os.path.join(OUT_DIR, "stage")
    OUT_DAT = os.path.join(OUT_DIR, "z_SC4UIScale_DialogStatic.dat")
    REPORT = os.path.join(OUT_DIR, "REPORT.md")

# ---------------------------------------------------------------------------
# THIRD-PARTY DIALOG OVERRIDES (task #79c, 2026-07-31)
# ---------------------------------------------------------------------------
# A plugin can REPLACE a stock .UI script wholesale, and by the LOAD-ORDER LAW
# (root Plugins files load BEFORE subfolders) our root package can never win.
# That is what made the two in-city quit/exit confirms open at stock 1x for
# five days under the wrong diagnosis "the game bypasses the DBPF override".
#
# These entries are built from the MOD'S OWN script (tools\dialog-static\
# thirdparty-src\, see its README) through the IDENTICAL transform used for the
# stock dialogs, and packed into their OWN dat so ScaleTier can gate them on
# the source mod still being installed. Building from the STOCK script here
# would silently revert the mod's function.
#
# ⚠ Their art is NOT staged here: {46a006b0,144161e4} and {46a006b0,144161eb}
# are already 2x IN PLACE in the root DialogStatic package, which the mod does
# not override, so the art is correct whichever script wins. The build ASSERTS
# this (no left1x is tolerated on a third-party override).
# (iid, human name, PACKAGE). The package decides which dat the doubled copy
# ships in, and therefore WHICH MOD ScaleTier gates it on - a copy of mod A's
# script must not survive mod A being uninstalled, so it cannot ride in mod B's
# package. One package per owning mod.
TP_TARGETS = [
    ("6a553aa4", "Exit to Region confirm (save-warning override)", "SaveWarningUI"),
    ("0a55161d", "Quit confirm (save-warning override)", "SaveWarningUI"),
    # ---- CAM (task #79c follow-up, 2026-07-31) -------------------------
    # CAM replaces NINE stock .UI scripts; six of them are our TARGETS, so we
    # were shipping doubled copies of scripts the game never loads. Found by
    # tools\uiscripts\winning_corpus.py; shapes measured, see its report.
    # Four of the six are AUTO-ENROLLED query panels (discover_query_family),
    # which is why a static scan of this file under-counted them.
    ("ca8cbf0f", "Generic one-button popup (CAM override, 500x175)", "CamUI"),
    ("8aa9aa14", "Startup splash (CAM override, 6 nodes)", "CamUI"),
    ("2a554f6d", "Query panel (CAM override, 300x480)", "CamUI"),
    ("aa8b999e", "Query panel (CAM override, 404x346)", "CamUI"),
    ("ca8b8564", "Query panel (CAM override, 292x287 moved)", "CamUI"),
    ("ea565970", "Query panel (CAM override, 304x297)", "CamUI"),
    # ---- CAM-ONLY dialogs (task #154, 2026-08-13) ----------------------
    # NOT an override of any stock script: CAM adds this one. See
    # TP_MOD_ONLY below for why the stock-twin assert cannot apply to it.
    ("9b868f68", "City info screen (CAM-only, 600x525, 116 nodes)", "CamUI"),
    # The other two CAM-only scripts winning_corpus.py has been reporting as
    # third-party holders all along. Ordinary building query panels - the
    # school/library/civic ones ("# of Students", "Grade", "Local Funding") -
    # so the user meets them by clicking a building. Same 1x-under-scaled-fonts
    # defect as 9b868f68; enrolled in the same pass rather than left to be
    # reported a second time. Their art is all stock group 46a006b0, already
    # 2x in place in the root DialogStatic package.
    ("12121201", "Civic query panel (CAM-only, 292x260)", "CamUI"),
    ("12121205", "School query panel (CAM-only, 292x287)", "CamUI"),
]

# THE BLIND SPOT THIS CLOSES (task #154). The winner assert below only asks
# "is one of OUR targets owned by a plugin?" - it never asks "is a plugin's
# own dialog scaled at all?", so a mod-ADDED window is invisible to every
# check in this builder. CAM's city info screen (the Village Hall / Town Hall
# query, MZ v1) sat at 1x for the whole life of the project while
# FontStyle-15x scaled its text: labels clipped mid-word and values overlapped
# them. MEASURED, not inferred - SC4UIScale.log 2026-08-13 14:27:56 printed
#   MWKID 0 id=0x10000005 (150,38 600x525)
# which is the .UI's own 1x area to the pixel.
#
# A mod-only script has NO stock twin, so the State-B assert ("something takes
# over when the gate disables us") is not just unmeetable, it is meaningless:
# with CAM uninstalled the dialog does not exist. The exemption is PROVEN at
# build time rather than asserted - the id must be absent from the 331-script
# stock corpus - so it can never be used to paper over a twin that really is
# missing.
TP_MOD_ONLY = {"9b868f68", "12121201", "12121205"}
TP_SRC_DIR = os.path.join(OUT_DIR, "thirdparty-src")
TP_PACKAGES = sorted({p for (_i, _n, p) in TP_TARGETS})

# THIRD-PARTY ART. A mod can ship its own copy of an art TGI as well as its own
# script, and doubling the script without the art is worse than doing neither:
# the CAM startup splash root is `blttype=tiled`, so a 1536x1200 root over
# CAM's 768x600 background TILED IT 2x2 (reported live, v2.38.3).
# Drop the MOD'S OWN bitmap in thirdparty-art\ (never the stock one - its real
# dimensions are what matter) and it is upscaled per tier and packed alongside
# the scripts, in the same mod-gated package.
TP_ART_DIR = os.path.join(OUT_DIR, "thirdparty-art")
# Which package each art TGI belongs to, so it ships in the dat gated on the
# mod that owns it.
# All four are CAM's own bitmaps, extracted from its dats and upscaled from
# THE MOD'S originals (never a stock lookalike - the real dimensions are what
# the blit maths uses). Found in one pass by auditing every image= ref across
# the six CAM scripts against the stock PNG store, rather than one build
# failure at a time.
TP_ART_PACKAGE = {
    (0x46A006B0, 0xEA7F0EAE): "CamUI",   # 768x600 startup splash, blttype=tiled
    (0x46A006B0, 0xD685C764): "CamUI",   # 150x71   query panel art
    (0x968B9EA5, 0xDF7A1654): "CamUI",   # 285x41   query panel art
    (0xCA120E98, 0x2D7C4D1B): "CamUI",   # 48x48    query panel art
    # ---- city info screen 9b868f68 (task #154) -------------------------
    # Every one of these is blttype=NORMAL: the bitmap is drawn at its own
    # native size and CLIPPED by the window, never stretched to it. So a 1x
    # strip inside a 1.5x row is not "slightly soft", it covers two thirds of
    # the row and the rest shows through. Sizes measured off the PNG headers
    # in CAM_Extended_Essentials.dat, never assumed from the window rect -
    # several of these windows deliberately crop their art (0,111,285,131 is
    # a 20px window over a 41px strip).
    (0x00237EE7, 0x0EA08A4A): "CamUI",   # 285x30  title strip (Summary)
    (0xBD85E83A, 0xA6122C8D): "CamUI",   # 285x30  title strip (Utilities)
    (0x3E53026E, 0x274DDEDD): "CamUI",   # 285x30  title strip (Civic)
    (0x40DDC72B, 0xE740CA77): "CamUI",   # 285x30  title strip (Environmental)
    (0xBF73248C, 0xF0B38B15): "CamUI",   # 285x41  row stripe, right column
    (0xD4FF97FA, 0xC3406512): "CamUI",   # 285x41  row stripe, lower left
    (0xC53F65D9, 0x71651DB9): "CamUI",   # 285x41  row stripe, lower right
    (0xBE484AC7, 0x7AEB8E7D): "CamUI",   # 20x20   surplus/deficit marker
    (0xC3E123BD, 0xCFE4E42F): "CamUI",   # 48x48   MZ badge, bottom left
}


def _emit_inputs():
    r"""Print the derived-input filenames this build needs, then exit.

    WHY: thirdparty-art\ holds ANOTHER MOD'S bitmaps. They are not in the repo
    (policy) and cannot be, so a cold clone must re-extract them from the
    player's own Plugins tree - and something has to say WHICH ones. Reading
    that list out of THIS dict is a derivation; writing the thirteen names into
    the bootstrap script would be a hand-maintained inventory, and those rot
    silently (the whole reason for law 94).

    Consumed by tools\Bootstrap-Corpus.ps1. One filename per line, no header,
    so the caller can treat stdout as data.
    """
    for (g, i) in sorted(TP_ART_PACKAGE):
        print("T-856ddbac_G-%08x_I-%08x.png" % (g, i))
    raise SystemExit(0)


if "--emit-inputs" in sys.argv:
    _emit_inputs()

# ART THAT DOES NOT EXIST ANYWHERE - proven, not assumed (task #154).
# ⛔ THE BAR FOR ADDING TO THIS SET IS DELIBERATELY HIGH, because v2.38.3 put
# {46a006b0,ea7f0eae} here on a STOCK-ONLY null and shipped a splash tiled 2x2.
# A stock-store miss is NOT evidence of absence. What is required is a null
# from an instrument that reads the GAME ARCHIVES **AND THE WHOLE PLUGINS
# TREE**, together with a positive control from the same run:
#
#   {46a006b0,b5cfffff}  referenced by CAM's school query panel 12121205,
#     node area=(15,242,48,275) imagerect=(0,0,33,33), transparentbkg=yes.
#     tools\dbpf\who_owns_tgi.py  -> NO HOLDER FOUND (archives + all Plugins)
#     tools\dbpf\find_tgi.py      -> not in the 9 game archives, any type
#     positive control, same session: the 12 refs of 9b868f68 resolved to 17
#     holders through the same code path, so neither tool is structurally
#     blind. It is a dangling ref in CAM's own data - the second one found in
#     this project after the 0xFF5D2E9F graph-label typo (#147). Nothing draws
#     at 1x, so nothing can fail to draw at any tier.
TP_ART_DANGLING = {
    (0x46A006B0, 0xB5CFFFFF),
}


def tp_stage_dir(pkg):
    return os.path.join(OUT_DIR, "stage-tp-%s%s" % (pkg, ("-" + TAG) if TAG else ""))


def tp_out_dat(pkg):
    return os.path.join(PKG_DIR if TAG else OUT_DIR,
                        "z_SC4UIScale_%s%s.dat" % (pkg, ("-" + TAG) if TAG else ""))

TARGET_GID = 0x96A006B0

# (iid hex string, human name) -- build order == report order
TARGETS = [
    ("0a7df315", "Play Options"),
    ("ca53f06e", "Audio Options"),
    ("8a7e052f", "Graphic Options"),
    ("8a5ab1cb", "Region Name (Create Region)"),
    ("8a5ab1ce", "Delete Region confirm"),
    ("8a5ab1cc", "Load Region"),
    ("4a551b4c", "Quit confirm (region screen)"),
    ("8a5ab1cf", "Quit confirm (are-you-sure)"),
    ("0a8cd184", "Start New City bubble"),
    ("ca539340", "Existing-city bubble"),
    ("4a8cc5ea", "Photo Album"),
    # City-bubble confirm (Delete City): the dialog factory at VA 0x778245
    # instantiates this script; inline "Warning:" captions.
    ("8a5ab1d0", "Delete City confirm"),
    # City Import dialog (root 0x0a5ba192): per-size titles ("Small/Medium/
    # Large City Import") + the TreeView file-picker stage.
    ("8a5ab1cd", "City Import"),
    # GENERIC MESSAGE BOX (root 0x8a8dfcf5): the builder at VA 0x78DFF0
    # loads THIS script for every code-driven confirm (title id 0x8a91e4fd,
    # body id 0x6a8cc495, Accept/Cancel re-captioned per use). The Import
    # City "Importing a city will replace..." popup is this box (title =
    # per-size LTEXT table at 0xAB9230, body LTEXT {0a554ae8,4aa59e23},
    # via VA 0x7AFE78) - NOT 8a5ab1d0 and NOT 8a5ab1cd as first assumed.
    # Doubling it covers every other code-built confirm in the game too.
    ("ea8cc3c6", "Generic message box (code-driven confirms)"),
    # Credits window (root 0x0a592004): opened from Play Options' Credits
    # button; title + scrolling body text + Close (user 2026-07-23).
    ("ca551016", "Credits"),
    # ADVISOR MESSAGE TOASTS (2026-07-29 evening, user report "toast popups
    # are crushed"): the five per-mood message boxes (450x246 design, one
    # per advisor mood color; edge-blt frame 144161f1/f2, portrait strip
    # 144161f3/f4, Close button art 144161f5/f6) that pop for advisor/news
    # messages. Each hosts the rich-text pane (clsid 0xaa12e5f5, id=2)
    # whose TEXT is scaled by the v2.19.0 HTML table patch - so they showed
    # 2x text crammed in a 1x frame. Main-window transients like the query/
    # confirm family (not in the city sweep), so static-doubling is safe.
    ("4a5a89d4", "Advisor toast (salmon)"),
    ("4a5a89d5", "Advisor toast (salmon B)"),
    ("2bb16d50", "Advisor toast (green)"),
    ("0bbc06b6", "Advisor toast (blue)"),
    ("4bbc080f", "Advisor toast (peach)"),
    # ---- CITY MODE (task #36) ----
    # Building QUERY panels (the "info box" / query clicker). PROVEN SAFE to
    # static-double 2026-07-23 via live dump: these are transient dialogs
    # parented at the MAIN-WINDOW level (parent 0x00000000), OUTSIDE the city
    # runtime sweep (which only walks the 3D-view children) -> they render at
    # pure 1x stock today (root 0x10000005, container 0x89e1567c, all rows at
    # stock 175x18 etc.), and static-doubling them cannot double-scale.
    # ca56783a = the confirmed-open residential query (inner 292x331);
    # 4a5672bf = taller variant (292x440); 2a567dc1 = 292x330 variant.
    # NOTE: 117 scripts share root id 0x10000005 (the whole query/data
    # family) - these 3 are the validation batch; expand after user confirm.
    ("ca56783a", "Building query (residential)"),
    ("4a5672bf", "Building query (tall variant)"),
    ("2a567dc1", "Building query (short variant)"),
    # God-mode confirm boxes (main-window children, 1x stock, sweep-safe -
    # live dump 2026-07-23). These are their OWN msg-box templates, NOT the
    # generic ea8cc3c6, which is why doubling ea8cc3c6 didn't fix them.
    ("2a41436c", "Obliterate City confirm"),          # root 0x27df05be
    # Reconcile Edges message-box family - THREE variants share root
    # 0x6a4d0a59 (boundaries-match / highlighted-areas-confirm / third),
    # all main-window children rendering 1x. User 2026-07-23 hit the
    # "highlighted areas" one squished because only 0a4d0c43 was doubled.
    ("0a4d0c43", "Reconcile Edges (boundaries match)"),
    ("ca4d0b22", "Reconcile Edges (highlighted areas confirm)"),
    ("8a4d0a17", "Reconcile Edges (variant 3)"),
    # ---- IN-CITY QUIT / EXIT CONFIRMS (user 2026-07-26) ----
    # These share root id 0xaa921f4f with the region-screen quit (4a551b4c)
    # but are DIFFERENT .UI scripts loaded by the game depending on context.
    # Without 2x overrides the 2x fonts clip inside the 1x frame.
    ("6a553aa4", "Exit to Region confirm (in-city, 3-btn)"),
    ("0a55161d", "Quit confirm (in-city, 3-btn)"),
    # In-city exit variant with "Exit to Region" / "Exit and Play City" /
    # "Cancel" (root 0x6aaeec4a).
    ("eaaeec1b", "Exit to Region (in-city, play-city variant)"),
    # ---- USER 2026-07-28 batch ----
    # "Warning: The game can't save during a disaster. Do you..." confirm
    # (root 0x2a96ed21, 300x128) - appears when exiting a city while a
    # disaster is active; was rendering 1x with the 2x font clipped.
    ("4a89b3f2", "Can't-save-during-disaster confirm"),
    # Establish City (root 0x6a414973, 434x234): the Mayor-mode entry popup.
    # UNLIKE the other confirms this one lives INSIDE the DLL's swept tree, so
    # it needs BOTH halves: this static 2x AND its root id in the DLL's
    # kNeverScaleIds (UiSpike.cpp). Static-only -> the sweep double-scales it to
    # ~4x (log: 868x468 -> 1736x936); DLL-only -> right size but the GZWinText
    # nodes render purple while TextEdit/button captions stay black. Both = the
    # same clean result as every other dialog here.
    ("2a41436b", "Establish City"),
    # ---- SIM-MODE + U-DRIVE-IT PICKERS and the plugin warning (v2.22.2) ----
    # All four render PURE 1x today (absent from SCALED_WINDOW_IDS and from
    # this list, zero repo references) while FontStyle doubles their text =
    # clipped titles/captions. None contains id=0x10000005, so
    # discover_query_family() does NOT adopt them (checked) - no auto-enrol
    # trap. Their roots are ALSO listed in kNeverScaleIds as free insurance:
    # if any turns out to be parented inside the 3D view after all, that
    # listing is what prevents the Establish-City 4x double-scale.
    ("0a243d80", "Select A My Sim (Sim-mode sim picker)"),
    ("4bf325e8", "U-Drive-It Select vehicle for <MySim>"),
    ("abfaef15", "U-Drive-It Select pedestrian style"),
    ("ea89b6c3", "Missing plugin-packs warning (city load)"),
    # ---- TEXT-SWEEP BATCH (v2.23.1) --------------------------------------
    # Found by a corpus sweep for text-bearing roots absent from BOTH
    # SCALED_WINDOW_IDS and this list: FontStyle doubles every style, so an
    # unscaled frame ALWAYS clips its text (the unresolved-token case lands
    # on the doubled `Default` 0x68963c4c, so name-vs-GUID does not save it).
    # Ordered by how soon a normal player reaches them. Each root is ALSO in
    # kNeverScaleIds as free insurance - parentage is undetermined from data
    # for several of these (they never appeared in any dump), and that
    # listing is what prevents the Establish-City 4x if any is view-parented.
    ("ca8cbf0f", "Generic one-button notification popup"),
    ("ebd0d36c", "Select A Bridge (network across water)"),
    ("0a2dd355", "Tutorial page (also an HTML-fed pane - see list D)"),
    ("6a5e73c0", "Tutorial exit confirm"),
    ("0a5cf71d", "Game Over / Run for Senator"),
    ("8aa9aa14", "Startup splash 768x600"),
    ("aaaaf3d1", "Startup splash 800x600"),
    ("aa5e60d1", "Clock time popup"),
    # ---- BATCH A (v2.24.1, task #54) --------------------------------------
    # The three remaining bucket-D (untouched-but-reachable) text-bearing
    # roots from the coverage matrix, done with this proven static recipe.
    # Each root is ALSO in kNeverScaleIds (UiSpike.cpp) as free insurance -
    # same rationale as the TEXT-SWEEP BATCH above: parentage is undetermined
    # from data for these (they never appeared in a dump), and that listing is
    # what prevents the Establish-City 4x if any turns out to be view-parented.
    #
    # NOTE on 6b704690: its root id is 0x8A8DFCF5 - the SAME id as the generic
    # message-box root (script ea8cc3c6, already in this list). That is FINE:
    # static doubling is per-script TGI, so the two scripts are doubled
    # independently and neither shadows the other. It does mean the single
    # kNeverScaleIds entry 0x8A8DFCF5 covers both scripts at once.
    ("6b704690", "Label Tool (map annotation)"),
    ("ca539343", "Region city-bubble stub (narrow)"),
    ("ebd0d36d", "Select A Bridge sibling button"),
    # BUDGET SUB-DIALOG MASTERS (2026-07-30, third landing - the RIGHT one).
    # The earlier "PROVEN BYPASSED" conclusion was wrong in a subtle way:
    # the doubled copies here were being OVERRIDDEN BY OUR OWN SelectiveArt
    # dat, which also shipped these two scripts (clone-retargeted, 1x
    # geometry) and loads later alphabetically. SelectiveArt no longer
    # emits them (see its builder), so this dat's doubled copies now win.
    # Their roots 0xAA3AC002/0xCA4C332D are in kNeverScaleIds (view-
    # parented templates + doubled data would otherwise 4x). Every open
    # instance is born 2x from this data - rows, spinners, content-fit
    # height all derive from the doubled geometry (the marquee principle).
    # BUDGET SCRIPTS FULLY REMOVED (v2.25.24, final architecture): the
    # budget UI is a MULTI-ROOT COMPOSED PANEL like Graphs - each of
    # aa3acdfe/cbc3c2b9 carries FOUR top-level roots (0xAA3AC002 income,
    # 0xCA4C332D expense, 0xAA3AC001 detail-dialog frame, 0xAA3AC000
    # balance bar), all view-parented and composed/anchored at runtime.
    # Full static doubling of ANY of them breaks the composition (the
    # "undocked budget window"). They get the GRAPHS treatment in
    # selective-safe: children-only data double on all four roots +
    # kDataScaledSubtreeIds in the DLL.
    # ---- BATCH C (v2.25.5, 2026-07-30, user report "Save City generates a
    # collapsed confirmation window") ----
    # e9263d4c "Text Entry" (root 0xC9264BE2, 319x113: title band + TextEdit
    # + OK) is the GENERIC re-captioned prompt box - the Options -> Save
    # flow titles it "Save" and fills the body ("City Saved. (...)"), and it
    # rendered collapsed with 2x text in the 1x frame. Its sibling e9263de5
    # "Set Lot Size" (root 0x8926EEBE, 249x92, OK + two combos) is the same
    # family and equally reachable. Both roots are ALSO in kNeverScaleIds as
    # the standard insurance (parentage undetermined from data).
    ("e9263d4c", "Text Entry prompt (Save City confirm)"),
    ("e9263de5", "Set Lot Size"),
]

# ---- RUNTIME-BOUND placeholder refs whose PIXELS are staged 2x (task #55) ----
# The U-Drive-It picker cells are GZWinBMP placeholders whose .UI
# image={46a006b0,ea32f104}/{6b998f30} is DANGLING - present in NO shipped
# archive (tools\dbpf\find_tgi.py scan of all seven, any type). The game
# overwrites the image at runtime: binder VA 0x76FDB0 QIs child 0x23450000+i
# (iid 0xC12CEA13 = GZWinBMP) and SetImages {0x4C06F888, <vehicle-exemplar
# property 0xEBFC5E5E>} via loader 0x602B70. build_selective_safe.py now
# stages that ENTIRE group 2x-in-place (112 entries), so the pixels these
# controls receive at runtime ARE 2x - and GZWinBMP's draw follows the
# SOURCE rect (Plot 0x9BC325: dst size = src size), so the imagerect MUST
# scale with those runtime pixels or the cell shows a 1x-cropped corner.
# Per-script on purpose: 0a243d80 (Select A My Sim) carries the SAME
# placeholder TGI but receives runtime-GENERATED portraits that stay 1x
# (task #47 code hook territory) - scaling its rects would crop them.
# The dangling ref itself is left byte-identical (nothing to retarget).
RUNTIME_BOUND_2X = {
    "4bf325e8": {(0x46A006B0, 0xEA32F104), (0x46A006B0, 0x6B998F30)},
    "abfaef15": {(0x46A006B0, 0xEA32F104), (0x46A006B0, 0x6B998F30)},
}

# roots deliberately larger than the visible dialog art -- doubled as-is
# ---- #192 RESOLUTION / SCALE READOUT (2026-08-18) --------------------------
# Two labels injected into the Graphic Options dialog before the doubling
# pass, so they scale with every sibling. Captions are set by the DLL at
# runtime (UiSpike.cpp, RESREADOUT).
#
# THE CAPTION IS DELIBERATELY EMPTY HERE. If the DLL half of this change is
# ever missing or its lookup fails, the dialog shows blank space rather than
# a stale or invented number. A resolution printed confidently and wrongly is
# worse than no resolution at all, and this project has twice shipped an
# instrument that lied in its own favour.
RES_READOUT_IID = "8a7e052f"
RES_READOUT_ANCHOR = 'caption="Software"'
RES_READOUT_IDS = ("0x5ca1e000", "0x5ca1e001")


def inject_res_readout(text, fn):
    """Add the two runtime-filled labels to Graphic Options.

    Returns (text, n_added). A no-op for every other script.
    """
    if not fn.endswith("_I-%s.ui" % RES_READOUT_IID):
        return text, 0
    if RES_READOUT_IDS[0] in text:
        return text, 0          # already injected; idempotent
    lines = text.split("\n")
    at = None
    for i, ln in enumerate(lines):
        if RES_READOUT_ANCHOR in ln:
            at = i
            break
    if at is None:
        sys.exit("FATAL #192: anchor %s not found in %s. The dialog changed - "
                 "do NOT guess a new insertion point, re-measure the layout."
                 % (RES_READOUT_ANCHOR, fn))
    indent = lines[at][:len(lines[at]) - len(lines[at].lstrip())]
    # Same attribute set as the Software label it sits under, minus
    # captionres (ours is not an LTEXT), with an empty caption and
    # ignoremouse so it can never eat a click meant for a radio.
    tmpl = ('<LEGACY clsid=GZWinText iid=IGZWinText id=%s '
            'area=(293,%d,465,%d) fillcolor=(0,0,0) caption="" '
            'winflag_visible=yes winflag_enabled=yes winflag_moveable=yes '
            'winflag_sizeable=no winflag_sortable=no winflag_pbuff=no '
            'winflag_pbufftrans=yes winflag_pbufferase=yes '
            'winflag_pbuffvid=no winflag_alphablend=no '
            'winflag_acceptfocus=yes winflag_mousetrans=no '
            'winflag_ignoremouse=yes font=GenBodyMedium align=lefttop '
            'notify=no wrapped=no opaque=no forecolor=(63,73,103) '
            'bkgcolor=(0,0,0) gutters=(2,2) textoffsets=(0,0) >')
    # ONE line only. The second row at y=345..366 was CLIPPED on screen
    # (user screenshot, 2026-08-18) while this row rendered in full, so the
    # parent clips inside [346,366) and there is no room for a second 20px
    # row above it. Both numbers go on this row instead.
    new = [indent + tmpl % (RES_READOUT_IDS[0], 325, 346)]
    lines[at + 1:at + 1] = new
    return "\n".join(lines), len(new)

OVERSIZE_ROOT_IIDS = {"0a7df315", "8a7e052f"}
# tail-anchored popups the GAME positions (tail at clicked tile): the doubled
# origin is meaningless, only the doubled SIZE is asserted
BUBBLE_IIDS = {"0a8cd184", "ca539340"}


def fmt_id(wid):
    return "0x%08x" % wid if wid is not None else "(no id)"


def target_fn(iid_s):
    return "T-00000000_G-96a006b0_I-%s.ui" % iid_s


def target_out(iid_s):
    return "T-0x00000000_G-0x96a006b0_I-0x%s.ui" % iid_s


# ---- Auto-discover the QUERY-PANEL FAMILY (task #36) ----
# Every building/network query panel shares root window id 0x10000005 + the
# 0x89e1567c bubble container. They are transient dialogs parented at the
# MAIN-WINDOW level (proven by live dump 2026-07-23), OUTSIDE the city
# runtime sweep, so they render 1x stock and static-doubling is
# collision-free. Discover them all from disk (group 96a006b0 only) instead
# of hand-listing 117 iids; skip any already in TARGETS.
#
# ⚠ PARENTAGE WARNING (task #46, 2026-07-29): this rule ALSO enrols any
# script that merely CONTAINS id=0x10000005 as an inner container - the
# eleven U-Drive-It driving-status scripts (root 0x10000006) matched and
# shipped doubled, and because THAT root parents at the 3D VIEW the city
# sweep doubled it again = 4x panel ("opens in a broken way"). Fixed by
# listing 0x10000006 in kNeverScaleIds (UiSpike.cpp). If a future family
# gets adopted by this rule, CHECK ITS ROOT'S PARENTAGE with a live dump
# before shipping: main-window parent = fine; 3D-view parent = it MUST go
# in kNeverScaleIds or the two layers double-scale.
def discover_query_family():
    already = {i for (i, _) in TARGETS}
    found = []
    for fn in sorted(os.listdir(UI_DIR)):
        if not (fn.startswith("T-00000000_G-96a006b0_I-") and fn.endswith(".ui")):
            continue
        iid_s = fn[len("T-00000000_G-96a006b0_I-"):-len(".ui")]
        if iid_s in already:
            continue
        try:
            with open(os.path.join(UI_DIR, fn), "r", encoding="latin-1") as f:
                text = f.read()
        except OSError:
            continue
        if "id=0x10000005" in text and "clsid=0x89e1567c" in text:
            found.append((iid_s, "Query panel %s" % iid_s))
    return found


TARGETS += discover_query_family()

TARGET_FNS = {target_fn(i) for (i, _) in TARGETS}

PNG_TYPE = 0x856DDBAC
CLONE_XOR = 0x53430001   # same marker as selective-safe (SELECTIVE-SAFE.md)
CLONE_XOR_ALT = 0x53430002  # fallback on collision only
UI_GROUPS = ("96a006b0", "08000600")

STAGE_FILE_RE = re.compile(
    r"^T-0x[0-9a-f]{8}_G-0x[0-9a-f]{8}_I-0x[0-9a-f]{8}\.(ui|png|bin)$", re.I)


# --------------------------------------------------------------------------
# LEGACY parser (from build_selective_safe.py, + area= and font= capture)
# --------------------------------------------------------------------------

class Node:
    __slots__ = ("clsid", "wid", "images", "imagerect", "edgeimage",
                 "area", "font", "children", "parent", "tag_start", "tag_end")

    def __init__(self):
        self.clsid = None
        self.wid = None            # id=0x........ or None
        self.images = []           # list of (gid, iid, val_start, val_end)
        self.imagerect = None      # ((l,t,r,b), val_start, val_end)
        self.edgeimage = None
        self.area = None           # ((x1,y1,x2,y2), val_start, val_end)
        self.font = None           # (name, val_start, val_end)
        self.children = []
        self.parent = None
        self.tag_start = 0
        self.tag_end = 0


ATTR_NAME_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


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
            continue  # quoted values (captions/tips) never carry our data
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
        elif name in ("imagerect", "area") and val.startswith("(") and val.endswith(")"):
            try:
                nums = tuple(int(x) for x in val[1:-1].split(","))
                if len(nums) == 4:
                    if name == "imagerect":
                        node.imagerect = (nums, vstart, vend)
                    else:
                        node.area = (nums, vstart, vend)
            except ValueError:
                pass
        elif name == "edgeimage":
            node.edgeimage = val
        elif name == "font":
            node.font = (val, vstart, vend)


def parse_ui(text):
    """Parse LEGACY markup -> list of root Nodes. Character scan, quote-aware."""
    roots = []
    stack = []
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
                last_control = parent
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


def tgi_png_name(gid, iid):
    return "T-0x%08x_G-0x%08x_I-0x%08x.png" % (PNG_TYPE, gid, iid)


EXTRACT_1X_ROOT = os.path.join(TOOLS, "dbpf", "extracted")


def art_1x_dims(gid, iid):
    """1x source dimensions for a TGI, or None. Used ONLY to decide whether an
    imagerect crops the WHOLE sheet - a full-sheet crop must track the art's
    real scaled size, a partial crop must not be touched.
    ⚠ the 1x extract uses BARE hex names (T-856ddbac_G-...), the upscale preview
    uses 0x-prefixed ones. Two conventions, one TGI."""
    name = "T-%08x_G-%08x_I-%08x.png" % (PNG_TYPE, gid, iid)
    if not os.path.isdir(EXTRACT_1X_ROOT):
        return None
    for sub in os.listdir(EXTRACT_1X_ROOT):
        cand = os.path.join(EXTRACT_1X_ROOT, sub, name)
        if os.path.isfile(cand):
            return png_dims(cand)
    return None


def png_dims(path):
    with open(path, "rb") as f:
        head = f.read(24)
    if head[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    w, h = struct.unpack(">II", head[16:24])
    return (w, h)


# --------------------------------------------------------------------------

def load_font_styles():
    """FontStyle.candidate.ini [Font Styles] -> {name: (guid, ini_size|None)}."""
    styles = {}
    in_section = False
    with open(FONT_INI, "r", encoding="latin-1") as f:
        for line in f:
            s = line.strip()
            if s.startswith("[") and s.endswith("]"):
                in_section = (s.lower() == "[font styles]")
                continue
            if not in_section or not s or s.startswith(";") or s.startswith("`"):
                continue
            m = re.match(
                r"([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?),\s*(0x[0-9A-Fa-f]{1,8})\s*$", s)
            if m:
                size = None
                quoted = re.findall(r'"([^"]*)"', m.group(2))
                if len(quoted) >= 2 and quoted[1].strip().isdigit():
                    size = int(quoted[1].strip())
                styles[m.group(1)] = (int(m.group(3), 16), size)
    return styles


def leaf_art_sized(nd):
    """Is this node a LEAF whose size is dictated by the art it draws? (#155)

    ⛔ THE DEFECT THIS EXISTS FOR: `UiSpike::ScaleSubtree` has taken a LEAF's
    scaled size SIZE-DERIVED since v2.94.1 (#148's cure - a leaf has no
    children to keep flush, so deriving its width from its neighbours' edges
    is what left a 1px strip of the art cell undrawn: the reverse L). This
    builder never got that rule, and STATICALLY-SERVED DIALOGS ARE
    DELIBERATELY EXCLUDED FROM THE RUNTIME SWEEP (kNeverScale, or they
    double-scale), so nothing downstream repairs them. The same control came
    out 83px wide at runtime and 82px in a static dat.

    USER-REPORTED on the region city bubble `ca539340`: the play button's art
    cell scaled to 83 inside an 82px window, and the leftover column drew as a
    tear down its right edge. MEASURED across the whole static stage: 383 of
    460 art-sized four-state buttons were 1px short at 1.5x, and **0 of 460 at
    2x and 3x** - the positive control, because ScaleRound is exact and
    ScaleDim returns early at an integer factor.

    ⚠ SCOPE, and why it is not "every leaf". The DLL applies its rule to all
    leaves. Here it is restricted to leaves that BIND ART AND CARRY NO
    `imagerect`, because those are exactly the windows whose size the art
    dictates. Widening it to text leaves would move a wrap point in dialogs
    that are already user-confirmed, for no defect - the blast-radius rule
    (a fix that resizes things is judged by its densest neighbourhood).
    Nodes WITH an `imagerect` are excluded too: their crop is registered
    against their own l,t (ENGINE 3.3 pattern 3) and scales with the art
    already, so resizing the window would break a relationship that is right.
    """
    return (not nd.children
            and bool(nd.images)
            and nd.imagerect is None
            and nd.area is not None)


def scaled_area(nd):
    """The scaled (l,t,r,b) for a node: edge-derived, or size-derived if leaf."""
    x1, y1, x2, y2 = nd.area[0]
    nl, nt = scale_len(x1), scale_len(y1)
    if leaf_art_sized(nd):
        return (nl, nt, nl + scale_len(x2 - x1), nt + scale_len(y2 - y1))
    return (nl, nt, scale_len(x2), scale_len(y2))


def verify_doubled(fn, orig_roots, new_text, art_plan, styles, runtime2x=(),
                   seated=()):
    """Re-parse the edited script and assert every edit landed exactly.

    ⚠ `seated` is the ONLY way an area is allowed to differ from an exact
    scale, and it is NOT a bypass - it is a DIFFERENT, STRICTER assertion.
    A seated window (#153) must have been TRANSLATED by at most one pixel per
    axis and its SIZE must still be exactly scaled. That distinguishes a
    deliberate one-pixel seat from the accident this verifier exists to catch
    (the #55/#56 class: a doubled frame drawn over 1x art).

    Pass ids, not a flag: a blanket "skip verification for this script" is how
    a real defect gets in behind a real fix.
    """
    new_roots = parse_ui(new_text)
    orig_nodes = list(walk(orig_roots))
    new_nodes = list(walk(new_roots))
    if len(orig_nodes) != len(new_nodes):
        sys.exit("VERIFY FAIL %s: node count %d -> %d"
                 % (fn, len(orig_nodes), len(new_nodes)))
    for o, nnd in zip(orig_nodes, new_nodes):
        if (o.clsid, o.wid) != (nnd.clsid, nnd.wid):
            sys.exit("VERIFY FAIL %s: node identity drift (%s/%s -> %s/%s)"
                     % (fn, o.clsid, o.wid, nnd.clsid, nnd.wid))
        if o.area is not None:
            # Same rule as the edit pass, not a copy of the old one: a leaf
            # that binds art is SIZE-derived (#155). Re-deriving it here from
            # the ORIGINAL node keeps the verifier an independent check of the
            # rule rather than a restatement of whatever the editor did.
            want = scaled_area(o)
            got = nnd.area and nnd.area[0]
            if got != want and nnd.wid is not None and nnd.wid in seated:
                # SEATED (#153): translated by <=1px per axis, SIZE untouched.
                dx, dy = got[0] - want[0], got[1] - want[1]
                if (got[2] - got[0], got[3] - got[1]) != (want[2] - want[0],
                                                          want[3] - want[1]):
                    sys.exit("VERIFY FAIL %s: seated 0x%08x changed SIZE "
                             "%s -> %s" % (fn, nnd.wid, want, got))
                if abs(dx) > 1 or abs(dy) > 1 or (dx, dy) != (
                        got[2] - want[2], got[3] - want[3]):
                    sys.exit("VERIFY FAIL %s: seated 0x%08x is not a <=1px "
                             "translation %s -> %s" % (fn, nnd.wid, want, got))
            elif got != want:
                sys.exit("VERIFY FAIL %s: area %s not scaled (got %s)"
                         % (fn, o.area[0], nnd.area and nnd.area[0]))
        if len(o.images) != len(nnd.images):
            sys.exit("VERIFY FAIL %s: image ref count drift" % fn)
        art2x = False
        for (g, i, _, _), (g2, i2, _, _) in zip(o.images, nnd.images):
            action, clone, _ = art_plan[(g, i)]
            want = clone if action == "clone" else (g, i)
            if (g2, i2) != want:
                sys.exit("VERIFY FAIL %s: ref {%08x,%08x} -> {%08x,%08x}, wanted {%08x,%08x}"
                         % (fn, g, i, g2, i2, want[0], want[1]))
            if action != "left1x" or (g, i) in runtime2x:
                art2x = True   # runtime2x: rect scales with the RUNTIME image (task #55)
        if o.imagerect is not None:
            want = tuple(scale_len(v) for v in o.imagerect[0]) if art2x else o.imagerect[0]
            # #157: the VERIFIER has to know the same rule as the writer, or it
            # rejects the correct output. A full-sheet crop tracks the ART's
            # real scaled size (which ScaleDim may have snapped), not the
            # arithmetic one.
            if art2x and o.images:
                g0, i0 = o.images[0][0], o.images[0][1]
                a1 = art_1x_dims(g0, i0)
                if a1 is not None and (o.imagerect[0][2], o.imagerect[0][3]) == a1:
                    sc = png_dims(os.path.join(UPSCALE_DIR, tgi_png_name(g0, i0)))
                    if sc is not None:
                        want = (want[0], want[1], sc[0], sc[1])
            if nnd.imagerect is None or nnd.imagerect[0] != want:
                sys.exit("VERIFY FAIL %s: imagerect %s wanted %s got %s"
                         % (fn, o.imagerect[0], want, nnd.imagerect and nnd.imagerect[0]))
        if o.font is not None and not o.font[0].startswith("0x") and o.font[0] in styles:
            want_f = "0x%08x" % styles[o.font[0]][0]
            if nnd.font is None or nnd.font[0] != want_f:
                sys.exit("VERIFY FAIL %s: font %s wanted %s got %s"
                         % (fn, o.font[0], want_f, nnd.font and nnd.font[0]))
    return len(new_nodes)



# ---------------------------------------------------------------------------
# SEAT THE "SELECT A MY SIM" PORTRAITS ON THEIR FRAME'S ART APERTURE (#153)
#
# THE LAW (closed form; it names the failing AXIS in advance):
#     For f = p/q in lowest terms, edge-derived rounding preserves a child's
#     1x offset d from its frame IFF q | d, because
#     round((t+d)f) - round(tf) == df exactly when df is an integer, and
#     otherwise depends on the PARITY of the frame's own coordinate t.
#     At f = 1.5 (q = 2): EVEN offsets survive, ODD offsets are a lottery.
#     At an integer factor q = 1 and every offset survives - which is why 2x
#     and 3x have never shown this family.
#
# These 22 portraits sit at 1x offset (3,2): x is ODD so it fails, y is EVEN
# so it is safe. The user reported "shifted to the left". The advisor panel,
# offset (2,1), fails on y instead and was reported as "high" (#152).
#
# ⚠ WHY THIS IS SAFE HERE, AND THE RUNTIME_BOUND_2X WARNING ABOVE IS NOT
# VIOLATED. That warning says scaling this script's RECTS would crop the
# runtime-generated portraits, and it is about `imagerect`. This pass changes
# NEITHER a rect nor a size - it TRANSLATES a window by one pixel.
#
# MEASURED IN-GAME with the #153 SEATPROBE before writing a line of this
# (src\UiSpike.cpp, BmpCtxBltThunk):
#     SEATPROBE id=0x1234000n win 54x62 | dst origin=(0,0) src 36x41 -> 54x62
# `dst origin=(0,0)` on EVERY draw: the blit is in the window's OWN local
# space, so the #47 hook contributes NOTHING to placement - it scales the
# portrait to fill whatever window it is handed (x1.50, exactly). Placement is
# the window's, and the window alone. That measurement is what licenses this.
#
# The 22 (face, frame) pairs were derived by resolving <CHILDREN> nesting to
# ABSOLUTE coordinates; a flat sibling comparison finds ZERO, because these
# faces are nested deeper than their frames. All 44 ids are unique in the
# script - counted, not assumed, and re-asserted at run time by _seat_one_tag.
_SEAT_AREA = r"area=\((-?\d+),(-?\d+),(-?\d+),(-?\d+)\)"

MYSIM_FACE_SEATS = [
    (0x12340000, 0xAA243E23, 0x46A006B0, 0x13F1525E, (3, 2)),
    (0x12340001, 0xAA243E2D, 0x46A006B0, 0x13F1525E, (3, 2)),
    (0x12340002, 0x6A243E35, 0x46A006B0, 0x13F1525E, (3, 2)),
    (0x12340003, 0xEA243E3D, 0x46A006B0, 0x13F1525E, (3, 2)),
    (0x12340004, 0x0A243E45, 0x46A006B0, 0x13F1525E, (3, 2)),
    (0x12340005, 0x6A243E4E, 0x46A006B0, 0x13F1525E, (3, 2)),
    (0x12340006, 0x2A243E56, 0x46A006B0, 0x13F1525E, (3, 2)),
    (0x12340007, 0x8A243E6C, 0x46A006B0, 0x13F1525E, (3, 2)),
    (0x12340008, 0x2A243F85, 0x46A006B0, 0x13F1525E, (3, 2)),
    (0x12340009, 0xEA243EB9, 0x46A006B0, 0x13F1525E, (3, 2)),
    (0x1234000A, 0x6A243EC1, 0x46A006B0, 0x13F1525E, (3, 2)),
    (0x1234000B, 0x8A243EC9, 0x46A006B0, 0x13F1525E, (3, 2)),
    (0x1234000C, 0xCA243ED1, 0x46A006B0, 0x13F1525E, (3, 2)),
    (0x1234000D, 0x8A243EDB, 0x46A006B0, 0x13F1525E, (3, 2)),
    (0x1234000E, 0xAA243EE2, 0x46A006B0, 0x13F1525E, (3, 2)),
    (0x1234000F, 0x2A243EEC, 0x46A006B0, 0x13F1525E, (3, 2)),
    (0x12340010, 0xCA243EF3, 0x46A006B0, 0x13F1525E, (3, 2)),
    (0x12340011, 0x6A243EFE, 0x46A006B0, 0x13F1525E, (3, 2)),
    (0x12340012, 0x8A243F08, 0x46A006B0, 0x13F1525E, (3, 2)),
    (0x12340013, 0xAA243F10, 0x46A006B0, 0x13F1525E, (3, 2)),
    (0x12340014, 0x6A243F17, 0x46A006B0, 0x13F1525E, (3, 2)),
    (0x12340015, 0xAA243E1B, 0x46A006B0, 0x13F1525E, (3, 2)),
]


def _seat_one_tag(text, wid):
    """The ONLY tag carrying this id, or FATAL.

    ⚠ THE \\b HERE IS LOAD-BEARING and was lost once. The first version of this
    file was generated through a Python string template, where \\b became a
    literal BACKSPACE (0x08) inside the regex - so the pattern demanded a 0x08
    byte after the id and matched nothing, and the build FATAL'd claiming the
    ids did not exist. They did. Do not machine-generate this function.
    """
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


def seat_faces_on_apertures(text, seats, factor, fn):
    """Seat each face on its frame + ScaleRound(offset). TRANSLATES ONLY.

    No pixel read here, unlike the advisor twin in build_selective_safe.py:
    this script's portraits are RUNTIME-GENERATED, so there is no shipped
    sheet whose aperture could be measured. The invariant is enforced instead
    by G1 (the offset is the SAME (3,2) for all 22 - a mismatch means the
    script changed) and by G4/G5 below.
    """
    moved = []
    for (face_id, frame_id, gid, iid, off1x) in seats:
        _, fr = _seat_one_tag(text, frame_id)
        mfa, fa = _seat_one_tag(text, face_id)
        # G1 the pairing still holds: the face must sit INSIDE the frame.
        if not (fr[0] <= fa[0] and fr[1] <= fa[1]
                and fa[2] <= fr[2] and fa[3] <= fr[3]):
            sys.exit("FATAL seat 0x%08X: face %s not inside frame %s"
                     % (face_id, fa, fr))
        want = (scale_len(off1x[0]), scale_len(off1x[1]))
        d = (fr[0] + want[0] - fa[0], fr[1] + want[1] - fa[1])
        if d == (0, 0):
            continue                    # INTEGER TIER: NOTHING IS WRITTEN
        # G2 a seat, never a nudge (#148): a fix that MOVES things is judged by
        # its densest neighbourhood, and this is a 21-icon grid.
        if abs(d[0]) > 1 or abs(d[1]) > 1:
            sys.exit("FATAL seat 0x%08X: delta %s exceeds 1px" % (face_id, d))
        new = (fa[0] + d[0], fa[1] + d[1], fa[2] + d[0], fa[3] + d[1])
        newtag = re.sub(_SEAT_AREA, "area=(%d,%d,%d,%d)" % new,
                        mfa.group(0), count=1)
        text = text[:mfa.start()] + newtag + text[mfa.end():]
        moved.append((face_id, fa[:2], new[:2], d))
    return text, moved


# ---------------------------------------------------------------------------
# ⛔ HISTORY, KEPT: THE FIRST ATTEMPT AT THE ABOVE WAS BACKED OUT 2026-08-13.
#
# The advisor faces were fixed by seating each face on its frame's measured art
# aperture (#152, build_selective_safe.py). The same law predicts these:
# the 22 portraits sit at 1x offset (3,2), x is ODD, so edge-derived rounding
# loses it at f=1.5 and the face draws a pixel LEFT of its hole - which is
# exactly what the user reported. The 22 (face, frame) pairs were derived
# cleanly by resolving <CHILDREN> nesting to absolute coordinates; all 44 ids
# are unique in the script. The arithmetic is not in doubt.
#
# IT IS STILL THE WRONG FIX HERE, for the reason written at RUNTIME_BOUND_2X
# above: "0a243d80 (Select A My Sim) carries the SAME placeholder TGI but
# receives runtime-GENERATED portraits that stay 1x (task #47 code hook
# territory)". These faces are NOT static art showing through a hole - the
# portrait bitmap is generated at runtime and deliberately left at 1x, then
# handled by the #47 leaf-kick. The frame's aperture is therefore NOT the
# authority on where the face belongs, and an aperture-seated rect would be
# arguing with the code hook rather than agreeing with it.
#
# The attempt also failed loudly before it could ship: _seat_one_tag FATAL'd
# with "id 0xAA243E23 occurs 0 times" against this builder's new_text, i.e.
# the ids this builder is holding at that point are not the pristine ones.
# THAT ALONE MEANS THE PAIRING WAS DERIVED FROM THE WRONG TEXT.
#
# TO REVISIT: settle first whether the 1px belongs to the WINDOW or to the #47
# hook's own draw, by instrumenting the hook - not by editing this builder.
# See _tests\REGRESSION.md #153.

def main():
    print("Scale factor: %g  (tag %r)  ->  %s"
          % (FACTOR, TAG or "(none, 2x default)", os.path.basename(OUT_DAT)))
    print("Upscaled art dir: %s" % UPSCALE_DIR)
    print("Refmap: %s" % REFMAP_CSV)
    if not os.path.isdir(UPSCALE_DIR):
        sys.exit("FATAL: upscaled art dir not found for factor %g: %s" % (FACTOR, UPSCALE_DIR))
    if not os.path.isfile(REFMAP_CSV):
        sys.exit("FATAL: refmap not found for factor %g (run build_selective_safe.py --factor %g first): %s"
                 % (FACTOR, FACTOR, REFMAP_CSV))
    os.makedirs(OUT_DIR, exist_ok=True)
    if TAG:
        os.makedirs(PKG_DIR, exist_ok=True)
    # Empty in place, file by file; only files this builder emits; never the
    # directory itself (these trees live under OneDrive, which holds a handle
    # on the folder and makes rmdir fail even when the files delete fine).
    for stage_dir in [STAGE] + [tp_stage_dir(p) for p in TP_PACKAGES]:
        if os.path.isdir(stage_dir):
            for fn in os.listdir(stage_dir):
                if STAGE_FILE_RE.match(fn):
                    os.remove(os.path.join(stage_dir, fn))
                else:
                    sys.exit("FATAL: unexpected file in %s, refusing to delete: %s"
                             % (stage_dir, fn))
        else:
            os.makedirs(stage_dir)

    # ---- font style table ----
    styles = load_font_styles()
    print("Font styles loaded from candidate ini: %d" % len(styles))

    # ---- PNG store TGIs (collision checks) ----
    store_tgis = set()
    with open(PNG_TGI_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            store_tgis.add((int(row["GroupID"], 16), int(row["InstanceID"], 16)))
    print("PNG store TGIs loaded: %d" % len(store_tgis))

    # ---- selective-safe refmap: planned clone TGIs + 2x-handled file sets ----
    # A file's ref to a TGI counts as "already 2x-handled" only if refmap shows
    # that file in the TGI's scaled set with action clone+retarget/2x-in-place
    # (i.e. the selective-safe package already deals with that occurrence).
    refmap_clones = set()      # (gid, iid) clone TARGETS planned by selective-safe
    handled_files = defaultdict(set)   # (gid,iid) -> set(files) whose refs are handled
    refs_scaled = {}           # (gid,iid) -> has any selective-safe-scaled referrer
    with open(REFMAP_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["clone_GroupID"]:
                refmap_clones.add((int(row["clone_GroupID"], 16),
                                   int(row["clone_InstanceID"], 16)))
            tgi = (int(row["GroupID"], 16), int(row["InstanceID"], 16))
            if row["action"] in ("clone+retarget", "2x-in-place") and row["scaled_files"]:
                handled_files[tgi] |= set(row["scaled_files"].split(";"))
            # Does ANY script selective-safe scales reference this TGI? This is
            # the input to its code-bound refusal, and the cross-builder guard
            # below needs the same fact.
            refs_scaled[tgi] = bool(row["scaled_files"].strip())
    print("Selective-safe planned clone TGIs: %d" % len(refmap_clones))

    # ---- full .UI corpus ref scan (independent of refmap; belt and braces) ----
    ui_files = []
    for g in UI_GROUPS:
        ui_files += sorted(
            fn for fn in os.listdir(UI_DIR)
            if fn.startswith("T-00000000_G-%s_I-" % g) and fn.endswith(".ui")
        )
    corpus_refs = defaultdict(set)   # (gid,iid) -> set(files)
    target_data = {}                 # iid_s -> (text, roots)
    for fn in ui_files:
        with open(os.path.join(UI_DIR, fn), "r", encoding="latin-1", newline="") as f:
            text = f.read()
        text, _n192 = inject_res_readout(text, fn)
        if _n192:
            print("   #192 res/scale readout: %d label(s) injected into %s"
                  % (_n192, fn))
        roots = parse_ui(text)
        for nd in walk(roots):
            for (gid, iid, _, _) in nd.images:
                corpus_refs[(gid, iid)].add(fn)
        for (iid_s, _) in TARGETS:
            if fn == target_fn(iid_s):
                target_data[iid_s] = (text, roots)
    missing = [iid_s for (iid_s, _) in TARGETS if iid_s not in target_data]
    if missing:
        sys.exit("FATAL: target script(s) not found in %s: %s"
                 % (UI_DIR, ", ".join(missing)))
    print("Corpus scanned: %d .UI files, %d distinct image refs"
          % (len(ui_files), len(corpus_refs)))

    # ---- THE WINNER ASSERT (v2.38.2, task #79c's real lesson) -------------
    # This corpus is the GAME ARCHIVES ONLY. A plugin that replaces a stock
    # .UI wins the load order (root Plugins files load BEFORE subfolders), so
    # doubling the stock copy of such a script ships a doubled copy of a
    # script the game never loads - and, worse, one whose SHAPE may differ.
    # That is exactly how the two in-city quit confirms went unfixed for five
    # days, and it is live right now for two CAM dialogs.
    #
    # tools\uiscripts\winning_corpus.py resolves the real winner per TGI and
    # writes winning-corpus.json. Regenerate it after ANY plugin change.
    # The KNOWN list is deliberate, exactly like Test-DatIntegrity.ps1's
    # EXPECTED table: every entry carries its reason, and REMOVING an entry is
    # the fix landing - never a way to quiet the build.
    # A plugin-owned target is HANDLED when TP_TARGETS builds a doubled copy
    # from the WINNING script into that mod's own gated package. Anything
    # plugin-owned and NOT in TP_TARGETS is unhandled and fails the build.
    # KNOWN_THIRD_PARTY_TARGETS is for deliberate, reasoned exceptions only -
    # it is empty today because all six CAM-owned targets are now built from
    # the winner (see TP_TARGETS above).
    KNOWN_THIRD_PARTY_TARGETS = {}
    tp_handled = {int(i, 16) for (i, _n, _p) in TP_TARGETS}
    wc_path = os.path.join(TOOLS, "uiscripts", "winning-corpus.json")
    if os.path.isfile(wc_path):
        with open(wc_path, "r", encoding="utf-8") as f:
            wc = json.load(f)
        # HOLDERS, not WINNERS. Once our override ships we become the winner,
        # so keying on `winners` is self-erasing: after SaveWarningUI shipped,
        # its two scripts dropped out and the staleness check below advised
        # RETIRING the very entries doing the fixing. "A mod we do not control
        # supplies this script" is the durable fact.
        tp = {int(e["instance"], 16): e["supplier"]
              for e in wc.get("third_party_holders", [])
              if int(e["group"], 16) == TARGET_GID}
        bad = []
        handled = 0
        for (iid_s, name) in TARGETS:
            iid = int(iid_s, 16)
            if iid not in tp:
                continue
            if iid in tp_handled:
                handled += 1
            elif iid not in KNOWN_THIRD_PARTY_TARGETS:
                bad.append((iid_s, name, tp[iid]))
        if bad:
            sys.exit("FATAL: %d target script(s) are OWNED BY A PLUGIN and not "
                     "built from the winner - we would double a script the "
                     "game never loads:\n%s\n"
                     "Add them to TP_TARGETS (built from thirdparty-src\\, "
                     "shipped from zzz-SC4UIScale\\, gated on that mod), or add "
                     "a reasoned entry to KNOWN_THIRD_PARTY_TARGETS."
                     % (len(bad), "\n".join(
                         "  %s (%s)\n    winner: %s" % b for b in bad)))
        if handled:
            print("   winner assert: %d plugin-owned target(s), all built from "
                  "the winning script" % handled)
        # A TP_TARGET whose script is NOT plugin-owned is a STALE override: the
        # mod is gone (or renamed) and our copy would fight the stock script.
        stale = sorted(tp_handled - set(tp))
        if stale:
            print("   ! %d TP_TARGET(s) no longer plugin-owned: %s - the "
                  "package gate will disable them at runtime, but the entry "
                  "should be retired here." %
                  (len(stale), ", ".join("0x%08x" % s for s in stale)))
    else:
        print("   ! winning-corpus.json missing - winner assert SKIPPED. "
              "Run tools\\uiscripts\\winning_corpus.py.")

    # ---- third-party override sources (task #79c) ----
    # Read from thirdparty-src\, NOT the stock corpus: these scripts belong to
    # another plugin that wins the load order, and doubling the stock twin
    # instead would revert that mod's function. Keyed "<iid>@tp" so the stock
    # twin built in the same run keeps its own entry - that pairing is also the
    # positive control (same code path, two inputs).
    tp_srcs = {}          # key -> source filename (for messages / verify)
    for (iid_s, _name, _pkg) in TP_TARGETS:
        src_fn = target_fn(iid_s)
        src_path = os.path.join(TP_SRC_DIR, src_fn)
        if not os.path.isfile(src_path):
            sys.exit("FATAL: third-party source missing: %s\n"
                     "  Re-extract the owning mod's dat with tools\\dbpf\\"
                     "DbpfExtract.exe (see thirdparty-src\\README.md)." % src_path)
        with open(src_path, "r", encoding="latin-1", newline="") as f:
            tp_text = f.read()
        target_data[iid_s + "@tp"] = (tp_text, parse_ui(tp_text))
        tp_srcs[iid_s + "@tp"] = src_fn
    if TP_TARGETS:
        print("Third-party override sources: %d from %s"
              % (len(TP_TARGETS), TP_SRC_DIR))

    # The build list drives the edit pass: stock targets first (unchanged
    # order, so the report is byte-stable), then the third-party overrides.
    build_list = [(iid_s, iid_s, name, None) for (iid_s, name) in TARGETS]
    build_list += [(iid_s + "@tp", iid_s, name, pkg)
                   for (iid_s, name, pkg) in TP_TARGETS]

    # ---- GLOBAL art plan across all six dialogs ----
    # A TGI referenced only by the six (and by selective-safe-handled refs) is
    # exclusive -> 2x in place.  Anything with an outside unhandled referrer
    # gets a collision-checked clone; one decision per TGI for the whole run.
    all_target_tgis = sorted({(g, i)
                              for key in ([i for (i, _) in TARGETS]
                                          + [i + "@tp" for (i, _n, _p) in TP_TARGETS])
                              for nd in walk(target_data[key][1])
                              for (g, i, _, _) in nd.images})
    all_ref_tgis = set(corpus_refs)

    art_plan = {}     # (gid,iid) -> ("clone",(cg,ci),reason) | ("inplace",None,r) | ("left1x",None,r)
    used_clone_tgis = set()
    fallback_clones = []   # (gid,iid) that needed CLONE_XOR_ALT
    for (gid, iid) in all_target_tgis:
        twox = os.path.isfile(os.path.join(UPSCALE_DIR, tgi_png_name(gid, iid)))
        others = corpus_refs[(gid, iid)] - TARGET_FNS
        unhandled = others - handled_files.get((gid, iid), set())
        if not twox:
            art_plan[(gid, iid)] = ("left1x", None,
                                    "no 2x asset in upscale preview set")
            continue
        if not unhandled:
            art_plan[(gid, iid)] = ("inplace", None,
                                    "exclusive to the %d target scripts (no other unhandled referrer)"
                                    % len(TARGETS))
            continue
        # CLONE path with collision-checked IID
        clone = None
        notes = []
        for xor in (CLONE_XOR, CLONE_XOR_ALT):
            cand = (gid, iid ^ xor)
            collide = []
            if cand in store_tgis:
                collide.append("game PNG store")
            if cand in all_ref_tgis:
                collide.append(".UI-referenced TGI")
            if cand in refmap_clones:
                collide.append("selective-safe planned clone")
            if cand in used_clone_tgis:
                collide.append("another clone in this package")
            if not collide:
                clone = cand
                if xor == CLONE_XOR_ALT:
                    notes.append("XOR 0x%08X collided, fell back to 0x%08X"
                                 % (CLONE_XOR, CLONE_XOR_ALT))
                    fallback_clones.append((gid, iid))
                break
            notes.append("0x%08X collision: %s" % (iid ^ xor, ", ".join(collide)))
        if clone is None:
            sys.exit("FATAL: no collision-free clone IID for %08x/%08x (%s)"
                     % (gid, iid, "; ".join(notes)))
        used_clone_tgis.add(clone)
        reason = ("shared with %d other .UI file(s) not 2x-handled" % len(unhandled))
        if notes:
            reason += " [" + "; ".join(notes) + "]"
        art_plan[(gid, iid)] = ("clone", clone, reason)

    # ---- CROSS-BUILDER DISAGREEMENT GUARD (v2.38.5) --------------------
    # We run TWO builders over the same art, with DIFFERENT exclusivity rules,
    # and until now neither could see the other's verdict.
    #
    #   build_selective_safe.py  knows which TGIs are CODE-BOUND, and refuses
    #                            to double one whose .UI referrers are all
    #                            unscaled (its `cb_conflict` case) - because a
    #                            code consumer is invisible to a .UI-only
    #                            judgement, so "no scaled referrer" is not
    #                            permission to double.
    #   build_dialog_static.py   has NO code-bound term at all, and reads
    #                            refmap only for clone targets. It therefore
    #                            doubled 2x-in-place exactly what the other
    #                            builder had deliberately refused.
    #
    # Whichever builder ran last won, silently. That is how the framework's
    # default scrollbar/frame glyphs came to ship 2x (the open #4 News defect).
    #
    # ⚠ THE NARROW SET IS THE POINT. 114 TGIs are "untouched" in refmap, but
    # almost all of that is correct division of labour: art referenced only by
    # the 163 STATIC dialogs is legitimately unscaled to selective-safe and
    # legitimately exclusive to us. Honouring `untouched` wholesale would gut
    # the static package. The real disagreement is only over CODE-BOUND art.
    #
    # IMPORTED, not regex-parsed: CODE_BOUND_TGIS is built up programmatically
    # (283 entries; a regex over the source finds 39 and the difference is
    # silent). Same lesson as the TARGETS under-count in winning_corpus.py.
    cb_conflict = set()
    try:
        sys.path.insert(0, os.path.join(TOOLS, "selective-safe"))
        import build_selective_safe as _BSS
        _cb = {tuple(t) for t in _BSS.CODE_BOUND_TGIS}
        _force = {tuple(t) for t in _BSS.CODE_BOUND_FORCE}
        for _k in _cb:
            if _k in refs_scaled and not refs_scaled[_k] and _k not in _force:
                cb_conflict.add(_k)
    except Exception as _exc:
        print("   ! cross-builder guard SKIPPED (%s) - selective-safe's "
              "refusals are unknown this run." % _exc)

    # Reasoned exceptions ONLY. Each entry is a disagreement we have decided to
    # keep for now, with why and what settles it. Emptying this dict is the fix
    # landing; adding to it without a measurement is how #4 happened.
    KNOWN_BUILDER_DISAGREEMENTS = {
        (0x46A006B0, 0x46A006A4): "framework default 9-slice frame, 72x72. "
            "blttype=edge STRETCHES, so a 2x sheet thickens the frame rather "
            "than clipping - no visible defect reported. Revisit with #4.",
        (0x46A006B0, 0x46A006A6): "framework default scrollbar strip, 192x16 "
            "= 12 cells (stock). RESOLVED 2026-07-31 from the exe (task #82): "
            "the old text here predicted 'every runtime scrollbar reads 32x32 "
            "cells into a 16px window' - REFUTED. cGZWinScrollbar::SetImage "
            "(0x9C45F0) derives cell size from the ART's own width / 12 (12 = "
            "cell COUNT; no hardcoded 16 exists) and then RESIZES the window "
            "to the derived cell - so the 2x sheet makes every runtime "
            "scrollbar correctly 2x, self-sizing, at every tier (division "
            "exact). a6 is bound ONCE in the exe (push @0x44E122 -> registry "
            "0xE8963EC7 -> the factory at 0x9970E8, vtable 0xADC128 slot "
            "+0x44); its only .UI referrer is Select A Bridge, which this "
            "builder doubles, and its siblings a7/a8 ship 2x via SelectiveArt "
            "CODE_BOUND_TGIS. The held disagreement is now PURELY refmap "
            "semantics: build_selective_safe classifies a6 'unscaled .UI ref' "
            "because its refmap does not know the referring script is doubled "
            "HERE. Keep 2x; do not revert. FULLY CLOSED 2026-07-31: SetImage "
            "also RESIZES the scrollbar window to the derived cell (SetArea "
            "via [+0xcc] vertical / [+0xd0] horizontal), and the one scripted "
            "scrollbar's authored width tracks that exactly at EVERY tier - "
            "stock 16 vs 192/12, 1.5x 24 vs 288/12, 2x 32 vs 384/12, 3x 48 vs "
            "576/12, all remainder-0 - so there is no residual exposure and "
            "no clipping (content width already subtracts the LIVE scrollbar "
            "width, sub_9BCBC5).",
    }
    _bad = []
    for (gid, iid) in sorted(cb_conflict):
        act = art_plan.get((gid, iid), (None,))[0]
        if act in ("inplace", "clone") and (gid, iid) not in KNOWN_BUILDER_DISAGREEMENTS:
            _bad.append((gid, iid, act))
    if _bad:
        sys.exit("FATAL: %d code-bound TGI(s) that build_selective_safe.py "
                 "REFUSED are being staged by this builder:\n%s\n"
                 "One builder's deliberate refusal must not be overridden by "
                 "whichever runs last. Either leave it 1x here, or add a "
                 "reasoned KNOWN_BUILDER_DISAGREEMENTS entry."
                 % (len(_bad), "\n".join("  {%08x,%08x} -> %s" % b for b in _bad)))
    _held = [k for k in KNOWN_BUILDER_DISAGREEMENTS if k in cb_conflict]
    if _held:
        print("   cross-builder guard: %d known disagreement(s) held: %s"
              % (len(_held), ", ".join("{%08x,%08x}" % k for k in sorted(_held))))
    _stale = [k for k in KNOWN_BUILDER_DISAGREEMENTS if k not in cb_conflict]
    if _stale:
        print("   ! %d KNOWN_BUILDER_DISAGREEMENTS entr(y/ies) no longer "
              "conflict - retire them: %s"
              % (len(_stale), ", ".join("{%08x,%08x}" % k for k in sorted(_stale))))

    # ---- per-dialog edit pass ----
    per_dialog = []       # dicts, TARGETS order
    tp_dialog = []        # third-party overrides -> their own package
    unmapped_fonts = set()
    # ---- THE ART WE SHIP THAT art_plan CANNOT SEE (task #154 follow-up) ----
    # ⛔ THIS IS WHY THE FIRST v2.97.0 BUILD SHIPPED HALF-WIDTH STRIPES.
    # `art_plan` is computed ONLY from the stock upscale preview set, so a
    # bitmap the MOD supplies - which we upscale through thirdparty-art\ - is
    # classified "left1x". `control_art_doubled` then stays False and the
    # node's `imagerect` is left at 1x. Result on screen: the window is 428
    # wide, the bitmap we ship is 429 wide, and the game slices
    # `imagerect=(0,0,285,30)` out of it - a 285px stripe in a 428px row,
    # two thirds of the way across. USER-REPORTED, and the build had already
    # printed `rects2x=0` for that file, which nobody read (law 54 again).
    #
    # This is EXACTLY the RUNTIME_BOUND_2X situation and is handled the same
    # way: the ref stays byte-identical, but the pixels behind it ARE scaled,
    # so the rect must scale with them.
    #
    # ⚠ SCOPED TO THE OWNING PACKAGE ON PURPOSE. The scaled bitmap ships in
    # the dat gated on ITS mod. Scaling an imagerect in the ROOT DialogStatic
    # package on the strength of art that only exists in a mod-gated package
    # would break the moment that mod is removed - the gate takes the art away
    # and leaves a doubled rect behind. So a rect may only scale when the
    # scaled bitmap ships in the SAME package as the script being built.
    tp_art_staged = {}        # (gid,iid) -> package, from the DIRECTORY
    if os.path.isdir(TP_ART_DIR):
        for afn in os.listdir(TP_ART_DIR):
            m2 = re.match(r"T-(?:0x)?([0-9a-f]{8})_G-(?:0x)?([0-9a-f]{8})"
                          r"_I-(?:0x)?([0-9a-f]{8})\.png", afn, re.I)
            if not m2:
                continue
            k = (int(m2.group(2), 16), int(m2.group(3), 16))
            if k in TP_ART_DANGLING:
                sys.exit("FATAL: {%08x,%08x} is in TP_ART_DANGLING but a PNG "
                         "for it is staged in thirdparty-art\\ (%s). It cannot "
                         "be both absent everywhere and supplied by us."
                         % (k[0], k[1], afn))
            pkg2 = TP_ART_PACKAGE.get(k)
            if pkg2 is None:
                sys.exit("FATAL: thirdparty-art %s has no TP_ART_PACKAGE entry "
                         "- it would ship ungated." % afn)
            tp_art_staged[k] = pkg2
    # The dict and the directory must agree in BOTH directions: an entry with
    # no file would silently scale rects for art we never ship.
    missing_art = sorted(set(TP_ART_PACKAGE) - set(tp_art_staged))
    if missing_art:
        sys.exit("FATAL: TP_ART_PACKAGE names %d bitmap(s) with no PNG in "
                 "thirdparty-art\\: %s" % (len(missing_art), ", ".join(
                     "{%08x,%08x}" % t for t in missing_art)))

    for (key, iid_s, name, tp_pkg) in build_list:
        is_tp = tp_pkg is not None
        # TGIs whose pixels this script's OWN package ships scaled.
        tp_scaled_here = frozenset(k for k, p in tp_art_staged.items()
                                   if is_tp and p == tp_pkg)
        text, roots = target_data[key]
        fn = tp_srcs[key] if is_tp else target_fn(iid_s)
        edits = []
        area_count = 0
        rect_log = []
        rect_snap_log = []        # (clsid, arithmetic, art-actual) - #157
        font_counts = Counter()   # name -> occurrences converted
        art_refs = Counter()      # (gid,iid) -> occurrences in this file
        left1x_controls = []      # (clsid, (gid,iid))
        leaf_sized = []           # (#155) art leaves the size rule resized
        tp_scaled_refs = []       # (clsid, (gid,iid)) - mod art WE upscale
        no_rect_2x = 0            # controls with 2x art but no imagerect attr

        for nd in walk(roots):
            if nd.area is not None:
                (x1, y1, x2, y2), vs, ve = nd.area
                na = scaled_area(nd)
                # ⛔ THE INTEGER NO-OP IS ASSERTED, NOT ASSUMED (#155). For an
                # integer N, scale_len(v) = vN exactly, so
                # N*l + N*(r-l) == N*r and the size-derived leaf rule lands on
                # the identical number. 2x and 3x are user-confirmed tiers; if
                # one pixel ever moves there, stop the build.
                if abs(FACTOR - round(FACTOR)) < 1e-9:
                    edge = (scale_len(x1), scale_len(y1),
                            scale_len(x2), scale_len(y2))
                    if na != edge:
                        sys.exit("FATAL %s: leaf size-derived rule changed an "
                                 "area at INTEGER factor %g: %s -> %s (edge "
                                 "would be %s). It MUST be a no-op there."
                                 % (fn, FACTOR, (x1, y1, x2, y2), na, edge))
                elif leaf_art_sized(nd) and na != (scale_len(x1), scale_len(y1),
                                                   scale_len(x2), scale_len(y2)):
                    leaf_sized.append((nd.wid, (x1, y1, x2, y2), na))
                edits.append((vs, ve, "(%d,%d,%d,%d)" % na))
                area_count += 1
            control_art_doubled = False
            rt2x = RUNTIME_BOUND_2X.get(iid_s, ())
            for (gid, iid, vs, ve) in nd.images:
                art_refs[(gid, iid)] += 1
                action, clone, reason = art_plan[(gid, iid)]
                if action == "left1x":
                    if (gid, iid) in rt2x:
                        # Runtime-bound placeholder whose real pixels are 2x
                        # (task #55): the ref stays byte-identical, but the
                        # imagerect must scale with the runtime image.
                        control_art_doubled = True
                    elif (gid, iid) in tp_scaled_here:
                        # SAME STATEMENT, different supplier (task #154): the
                        # ref stays byte-identical and the pixels behind it are
                        # ours, upscaled from the mod's own bitmap into THIS
                        # package. `art_plan` cannot see them because it only
                        # knows the stock store. Leaving the rect at 1x is what
                        # shipped the half-width stripes.
                        control_art_doubled = True
                        tp_scaled_refs.append((nd.clsid, (gid, iid)))
                    else:
                        left1x_controls.append((nd.clsid, (gid, iid)))
                    continue
                control_art_doubled = True
                if action == "clone":
                    edits.append((vs, ve, "{%08x,%08x}" % clone))
            if control_art_doubled:
                if nd.imagerect is not None:
                    (l, t, r, b), vs, ve = nd.imagerect
                    nr, nb = scale_len(r), scale_len(b)
                    # ⛔ #157: THE CROP MUST FOLLOW THE ART, NOT THE ARITHMETIC.
                    # Upscale2x::ScaleDim SNAPS a sheet's dimensions to a cell
                    # multiple at fractional factors, but scale_len here is a
                    # plain round - so at 1.5x the two disagree and the crop
                    # cuts the sheet short. Measured on the Reconcile Edges
                    # dialog: art 360x360 -> 276x276 (CellUnit(360)=lcm(3,4)=12,
                    # 270 snapped up), while the imagerect said 270x270. A
                    # nine-slice then derives its bands from 270/3=90 instead of
                    # 276/3=92, every border lands short, and the bottom-right
                    # 6px is cut. USER-CONFIRMED broken at 1.5x, clean at 2x and
                    # 3x - because at an INTEGER factor the snap is a no-op and
                    # the two rules agree by accident.
                    #
                    # This is #154's law one layer down: window, bitmap and the
                    # CROP between them are three numbers, and the crop is the
                    # one nobody scales on purpose.
                    art_full = art_1x_dims(gid, iid)
                    if art_full is not None and (r, b) == art_full:
                        scaled = png_dims(os.path.join(UPSCALE_DIR, tgi_png_name(gid, iid)))
                        if scaled is not None and (nr, nb) != scaled:
                            rect_snap_log.append(
                                (nd.clsid, "%dx%d" % (nr, nb), "%dx%d" % scaled))
                            nr, nb = scaled
                    new = "(%d,%d,%d,%d)" % (scale_len(l), scale_len(t), nr, nb)
                    edits.append((vs, ve, new))
                    rect_log.append((nd.clsid, "(%d,%d,%d,%d)" % (l, t, r, b), new))
                else:
                    no_rect_2x += 1
            if nd.font is not None:
                fname, vs, ve = nd.font
                if not fname.startswith("0x"):
                    entry = styles.get(fname)
                    if entry is None:
                        unmapped_fonts.add(fname)
                    else:
                        edits.append((vs, ve, "0x%08x" % entry[0]))
                        font_counts[fname] += 1

        # apply edits (descending offset; verify no overlap)
        spans = sorted(edits, key=lambda x: x[0])
        for a, b in zip(spans, spans[1:]):
            if a[1] > b[0]:
                sys.exit("FATAL %s: overlapping edits at offsets %d/%d"
                         % (fn, a[0], b[0]))
        new_text = text
        for (s, e, rep) in sorted(edits, key=lambda x: -x[0]):
            new_text = new_text[:s] + rep + new_text[e:]

        # Scalar pixel attributes must double with the layout: GZWinGrid
        # rowheight (the Audio playlist rows stayed 20px inside a doubled
        # grid - cramped rows, tiny row checkboxes), plus paddings.
        # NOTE: the grid attributes are spelled d-prefixed (drowheight=
        # "default row height", dcolwidth) -- the original \browheight
        # pattern silently missed them (no word boundary inside
        # "drowheight"), which is exactly why the playlist rows shipped
        # cramped. d? keeps the bare spellings covered too.
        def dbl_int(m):
            return "%s=%d" % (m.group(1), scale_len(int(m.group(2))))
        new_text = re.sub(
            r"\b(d?rowheight|d?colwidth|rowhdrsz|colhdrsz)=(\d+)",
            dbl_int, new_text)

        # GZWinGrid wingridcol="a,b,width ..." -- per-column width specs in
        # groups of 3; the first two numbers are column indices/counts, the
        # third is a PIXEL width (Audio playlist: "1,1,200" = 200px song-name
        # column; the checkbox column then uses dcolwidth). Scale ONLY the
        # width slot, never the indices.
        def dbl_gridcol(m):
            nums = [int(v) for v in re.findall(r"\d+", m.group(1))]
            out = []
            for k, v in enumerate(nums):
                out.append(str(scale_len(v)) if k % 3 == 2 else str(v))
            groups = [",".join(out[i:i + 3]) for i in range(0, len(out), 3)]
            return 'wingridcol="%s "' % " ".join(groups)
        new_text = re.sub(r'wingridcol="([0-9, ]+?)\s*"', dbl_gridcol, new_text)

        def dbl_tuple(m):
            nums = ",".join(str(scale_len(int(v))) for v in m.group(2).split(","))
            return "%s=(%s)" % (m.group(1), nums)
        new_text = re.sub(
            r"\b(gutters|textoffsets|tipoffsets)=\(([0-9, \-]+)\)", dbl_tuple, new_text)

        # #153: seat the 22 My Sim portraits on frame + ScaleRound(offset).
        # Runs after every area= is scaled and before verification, so what is
        # checked is what ships. Licensed by the SEATPROBE measurement quoted
        # above the table: the #47 hook blits at dst origin (0,0) in window
        # space, so placement is the window's alone.
        seated_ids = ()
        if iid_s == "0a243d80":
            new_text, seated = seat_faces_on_apertures(
                new_text, MYSIM_FACE_SEATS, FACTOR, fn)
            seated_ids = tuple(m[0] for m in seated)
            print("   my-sim faces seated x%g (%d of %d moved) in %s"
                  % (FACTOR, len(seated), len(MYSIM_FACE_SEATS), fn))
            # ⛔ THE INTEGER NO-OP IS ASSERTED, NOT ASSUMED. For integer N,
            # scale_len(v) = vN exactly, so N*frame + N*(face-frame) == N*face
            # and every delta is (0,0). 2x/3x are user-confirmed: if one window
            # ever moves there, STOP THE BUILD.
            if abs(FACTOR - round(FACTOR)) < 1e-9 and seated:
                sys.exit("FATAL: my-sim seat moved %d windows at integer "
                         "factor %g - it MUST be a no-op there"
                         % (len(seated), FACTOR))

        # `runtime2x` is the "the ref does not change but its PIXELS are
        # scaled, so the rect must scale" set. Mod art we upscale into this
        # same package is that exact case, so it rides the same parameter
        # rather than growing a second, near-identical one that could drift
        # out of step with the edit pass above.
        n_nodes = verify_doubled(fn, roots, new_text, art_plan, styles,
                                 tuple(RUNTIME_BOUND_2X.get(iid_s, ()))
                                 + tuple(tp_scaled_here), seated_ids)
        if leaf_sized:
            print("   (%s: %d art leaf/leaves SIZE-derived x%g, +/-1px, "
                  "position unchanged - #155)" % (fn, len(leaf_sized), FACTOR))
        if tp_scaled_refs:
            print("   (%s: %d rect(s) scaled with MOD art we upscale: %s)"
                  % (fn, len(tp_scaled_refs), ", ".join(
                      "{%08x,%08x}" % t
                      for t in sorted({t for (_c, t) in tp_scaled_refs}))))

        # THE LEFT1X LAW, enforced hard for third-party overrides: a doubled
        # frame drawn over 1x art is worse than no fix (task #55/#56). The
        # stock path only WARNS because a few of its 163 scripts legitimately
        # reference art with no 2x asset; an override we hand-picked has no
        # such excuse, so this is fatal.
        if is_tp and left1x_controls:
            # ⛔ THIS GUARD WAS WRONG ONCE AND IT SHIPPED A VISIBLE DEFECT.
            # v2.38.3 classified a ref as "DANGLING - no source anywhere, so
            # nothing to scale" on the strength of tools\dbpf\find_tgi.py
            # reporting {46a006b0,ea7f0eae} absent. That tool scans the GAME
            # ARCHIVES ONLY. The art is real and CAM_Intro.dat supplies it - so
            # the doubled splash tiled its 768x600 background 2x2 across the
            # 1536x1200 root (blttype=tiled; law 35). A null from a stock-only
            # instrument, for the THIRD time in one day.
            #
            # "Not in the PNG store" now means only "not in the STOCK store",
            # so a plugin-supplied ref must be checked against the plugin art
            # we ship (thirdparty-art\). Anything still unaccounted for is
            # FATAL: silence here is what produced the 4x splash.
            # ⚠ `afn`, NOT `fn`: `fn` is the DIALOG being processed, and an
            # earlier draft of this loop rebound it - so the FATAL below named
            # a PNG instead of the script at fault. A diagnostic that points at
            # the wrong file is worse than none.
            tp_art_have = set()
            if os.path.isdir(TP_ART_DIR):
                for afn in os.listdir(TP_ART_DIR):
                    m2 = re.match(r"T-(?:0x)?([0-9a-f]{8})_G-(?:0x)?([0-9a-f]{8})"
                                  r"_I-(?:0x)?([0-9a-f]{8})\.png", afn, re.I)
                    if m2:
                        tp_art_have.add((int(m2.group(2), 16), int(m2.group(3), 16)))
            # ⚠ THE OLD MESSAGE OVER-CLAIMED, and this file has a law about
            # that (#153: verify the failure message before believing its
            # implication). The condition is an OR, so a ref that is merely
            # UNACCOUNTED FOR was reported as one that "EXISTS at 1x" - which
            # sent the first reader of {46a006b0,b5cfffff} looking for a
            # bitmap that has never existed. Split the two branches so each
            # says what is actually true about it.
            in_store = [t for (_c, t) in left1x_controls
                        if t in store_tgis and t not in TP_ART_DANGLING]
            unaccounted = [t for (_c, t) in left1x_controls
                           if t not in store_tgis and t not in tp_art_have
                           and t not in TP_ART_DANGLING]
            dangling = [t for (_c, t) in left1x_controls if t in tp_art_have]
            proven_absent = [t for (_c, t) in left1x_controls
                             if t in TP_ART_DANGLING]
            if in_store:
                sys.exit("FATAL %s: third-party override references art that "
                         "EXISTS at 1x but has no 2x asset: %s" % (fn, ", ".join(
                             "{%08x,%08x}" % t for t in in_store)))
            if unaccounted:
                sys.exit("FATAL %s: third-party override references art that is "
                         "UNACCOUNTED FOR - not in the stock store, not in "
                         "thirdparty-art\\, and not proven absent: %s\n"
                         "  Resolve it with tools\\dbpf\\who_owns_tgi.py (which "
                         "reads Plugins too - the stock store alone said 'no' "
                         "once already and cost the 2x2-tiled splash). Then "
                         "either stage the mod's bitmap in thirdparty-art\\ or "
                         "add it to TP_ART_DANGLING with that evidence."
                         % (fn, ", ".join("{%08x,%08x}" % t for t in unaccounted)))
            if proven_absent:
                print("   (%s: %d ref(s) PROVEN ABSENT everywhere, nothing to "
                      "scale: %s)" % (fn, len(proven_absent), ", ".join(
                          "{%08x,%08x}" % t for t in sorted(set(proven_absent)))))
            if dangling:
                print("   (%s: %d plugin-supplied art ref(s), covered by "
                      "thirdparty-art\\: %s)" % (fn, len(dangling), ", ".join(
                          "{%08x,%08x}" % t for t in sorted(set(dangling)))))

        with open(os.path.join(tp_stage_dir(tp_pkg) if is_tp else STAGE,
                               target_out(iid_s)),
                  "w", encoding="latin-1", newline="") as f:
            f.write(new_text)

        root = roots[0]
        (tp_dialog if is_tp else per_dialog).append({
            "pkg": tp_pkg,
            "iid_s": iid_s, "name": name, "fn": fn,
            "root_clsid": root.clsid, "root_id": root.wid,
            "root_area": root.area[0] if root.area else None,
            "n_nodes": n_nodes, "area_count": area_count,
            "rect_log": rect_log, "font_counts": font_counts,
            "art_refs": art_refs, "left1x": left1x_controls,
            "no_rect_2x": no_rect_2x,
            # first child's rect, for the third-party golden check: asserting a
            # NESTED node (origin AND size) is a real test of the transform,
            # where the root alone only tests the outer box.
            "kid_area": (root.children[0].area[0]
                         if root.children and root.children[0].area else None),
        })
        print("%s %-40s areas=%d rects2x=%d fonts=%d refs=%d"
              % ("TP-EDIT" if is_tp else "edited ", fn, area_count, len(rect_log),
                 sum(font_counts.values()), sum(art_refs.values())))

    # ---- Credits HTML LTEXT (per-factor font-size bump) ----
    # The Credits window body (script I-ca551016, control 0x0a5d0e13) is an
    # HTML document in LTEXT {0x8a4924f3, 0x4a5d648f} (SimCityLocale.DAT),
    # rendered with inline <font size="1..7"> tags -- independent of
    # FontStyle.ini, so the .UI/font pipeline cannot scale it. Override the
    # LTEXT per factor with bumped size values (classic pt scale 1:7.5,
    # 2:10, 3:12, 4:13.5, 5:18, 6:24, 7:36; 7 is the max so it clamps).
    # Source saved durably in src-credits\ (decompressed 2026-07-23).
    credits_src = os.path.join(OUT_DIR, "src-credits", "credits-original.html")
    # RE-CALIBRATED 2026-07-29 (task #42): SC4UIScale v2.19.0 now scales the
    # HTML engine's index->pt tables IN THE EXE by the factor
    # (CodePatches::ApplyHtmlSizeScale; stock {8,10,12,14,18,24,36} -> x2 =
    # {16,20,24,28,36,48,72}), so news/tutorial/popup text scales without
    # LTEXT edits. The OLD maps here (2->4, 3->5 at 2x) would now COMPOUND
    # against the scaled tables (~4x credits text). These maps instead pin
    # the USER-APPROVED absolute look (2026-07-23: small~13.5pt, body 18pt,
    # title 36pt at 2x; exact-double body 24pt was rejected as overshot) by
    # choosing the index whose PATCHED table value lands nearest it. If
    # HtmlSizePatch is ever turned OFF, restore the old maps
    # {"":{2:4,3:5,7:7},"15x":{2:3,3:4,7:7},"3x":{2:5,3:6,7:7}}.
    credits_maps = {
        "":    {"2": "1", "3": "2", "7": "5"},   # 2x   -> 16/20/36 pt
        "15x": {"2": "1", "3": "2", "7": "6"},   # 1.5x -> 12/15/36 pt
        "3x":  {"2": "1", "3": "2", "7": "3"},   # 3x   -> 24/30/36 pt
    }
    cmap = credits_maps.get(TAG)
    if cmap and os.path.isfile(credits_src):
        with open(credits_src, "r", encoding="utf-8", newline="") as f:
            chtml = f.read()
        n_bumps = [0]

        def bump_size(m):
            n_bumps[0] += 1
            return 'size="%s"' % cmap.get(m.group(1), m.group(1))
        chtml = re.sub(r'size="(\d+)"', bump_size, chtml)

        # Table columns carry PIXEL widths (width="200"/"250"); left 1x
        # they force the scaled text to wrap mid-word ("Compose/rs").
        # Scale numeric widths by the factor; percentages stay.
        def bump_width(m):
            n_bumps[0] += 1
            return 'width="%d"' % scale_len(int(m.group(1)))
        chtml = re.sub(r'width="(\d+)"', bump_width, chtml)
        blob = struct.pack("<H", len(chtml)) + b"\x00\x10" \
            + chtml.encode("utf-16le")
        cname = "T-0x2026960b_G-0x8a4924f3_I-0x4a5d648f.bin"
        with open(os.path.join(STAGE, cname), "wb") as f:
            f.write(blob)
        print("staged Credits HTML LTEXT (%d size tags bumped, factor %g)"
              % (n_bumps[0], FACTOR))
    elif cmap:
        print("WARNING: credits source missing (%s) - Credits text stays 1x"
              % credits_src)

    # ---- stage PNGs (one per planned TGI) ----
    staged_pngs = []      # ((gid,iid), staged_name, dims)
    for (gid, iid) in all_target_tgis:
        action, clone, reason = art_plan[(gid, iid)]
        if action == "left1x":
            continue
        src = os.path.join(UPSCALE_DIR, tgi_png_name(gid, iid))
        out_name = tgi_png_name(*clone) if action == "clone" else tgi_png_name(gid, iid)
        shutil.copy2(src, os.path.join(STAGE, out_name))
        staged_pngs.append(((gid, iid), out_name, png_dims(src)))

    # ---- THIRD-PARTY OVERRIDE PACKAGE (task #79c) ----
    # Its own dat, so ScaleTier can gate it on the owning mod still being
    # installed: with the mod gone this package MUST go away too, or our frozen
    # copy of the mod's script keeps that mod alive after the user removed it
    # (the trap MAYOR-MODE.md:126 recorded and we only half-applied).
    # Scripts only - the art it references is 2x in place in the ROOT
    # DialogStatic package above, which the mod does not override.
    if tp_dialog:
        # GOLDEN VALUES, measured live 2026-07-31 at f=2 (SC4UIScale.log
        # 13:49:20.736): the runtime sweep scaled the mod's dialog to 540x324
        # with its child at (50,42 440x240). Data-doubling the SAME source must
        # land on the SAME numbers - that equality is what makes this change a
        # pure born-correct fix with zero visual delta at rest. If it ever
        # fails, the override is no longer reproducing the shipped behaviour.
        # root (w,h) and first child (l,t,w,h) as MWKID printed them live.
        golden_2x = {
            "6a553aa4": ((540, 324), (50, 42, 440, 240)),
            "0a55161d": ((540, 324), (50, 42, 440, 240)),
        }
        for d in tp_dialog:
            # State B (mod absent) is served by the stock twin in the ROOT
            # DialogStatic package - assert it is really there, because the
            # gate disabling this package assumes something takes over.
            # EXCEPT for a mod-ONLY dialog (TP_MOD_ONLY): the mod ADDS that
            # window, so with the mod gone there is nothing to take over and
            # nothing to scale. The exemption is PROVEN, not declared - the
            # script must really be absent from the stock corpus. Declaring it
            # would let a genuinely missing twin hide behind the same flag.
            if d["iid_s"] in TP_MOD_ONLY:
                stock_twin = os.path.join(UI_DIR, target_fn(d["iid_s"]))
                if os.path.isfile(stock_twin):
                    sys.exit("FATAL: %s is in TP_MOD_ONLY but the STOCK corpus "
                             "does carry it (%s) - it is an override, not a "
                             "mod-only dialog, and it needs a stock twin like "
                             "every other TP_TARGET." % (d["iid_s"], stock_twin))
                print("   %s: mod-ONLY dialog, no stock twin exists "
                      "(verified absent from %s)"
                      % (d["iid_s"], os.path.basename(UI_DIR)))
            elif not os.path.isfile(os.path.join(STAGE, target_out(d["iid_s"]))):
                sys.exit("FATAL: no stock twin staged for %s - nothing would "
                         "scale this dialog once the gate disables the "
                         "override." % d["iid_s"])
            ra = d["root_area"]
            got = (scale_len(ra[2]) - scale_len(ra[0]),
                   scale_len(ra[3]) - scale_len(ra[1]))
            want = golden_2x.get(d["iid_s"])
            if not TAG and want and got != want[0]:
                sys.exit("FATAL %s: doubled root is %dx%d, live-measured "
                         "golden is %dx%d" % ((d["iid_s"],) + got + want[0]))
            ka = d["kid_area"]
            if not TAG and want and ka is not None:
                gotk = (scale_len(ka[0]), scale_len(ka[1]),
                        scale_len(ka[2]) - scale_len(ka[0]),
                        scale_len(ka[3]) - scale_len(ka[1]))
                if gotk != want[1]:
                    sys.exit("FATAL %s: doubled child is (%d,%d %dx%d), "
                             "live-measured golden is (%d,%d %dx%d)"
                             % ((d["iid_s"],) + gotk + want[1]))
        # ONE DAT PER OWNING MOD. A copy of mod A's script must not ride in a
        # package gated on mod B, or uninstalling A leaves our copy of A's UI
        # alive - the trap this whole mechanism exists to prevent.
        # Stage the mod's own art, upscaled per tier, into its package.
        if os.path.isdir(TP_ART_DIR) and os.listdir(TP_ART_DIR):
            up_tmp = os.path.join(OUT_DIR, "thirdparty-art-up%s"
                                  % (("-" + TAG) if TAG else ""))
            if os.path.isdir(up_tmp):
                for fn2 in os.listdir(up_tmp):
                    os.remove(os.path.join(up_tmp, fn2))
            else:
                os.makedirs(up_tmp)
            # #157: a third-party 9-slice frame must be sized by CellUnit {3}
            # like a stock one. Zero third-party sheets match TODAY, so this is
            # a provable no-op on the current corpus - it is here so the next
            # mod that ships a dialog frame cannot inherit the stock defect
            # silently (every consumer of a shared rule needs its own wiring).
            r = subprocess.run([os.path.join(TOOLS, "upscale", "Upscale2x.exe"),
                                TP_ART_DIR, up_tmp, "--factor", str(FACTOR),
                                "--normalize-names", "--nine-slice",
                                os.path.join(TOOLS, "upscale", "nine-slice.txt"),
                                "--no-snap",
                                os.path.join(TOOLS, "upscale", "no-snap.txt"),
                                # F12 (review 2026-08-16): the corpus rebuild
                                # treats the derived lists as mandatory; this
                                # invocation was missing these two, so a
                                # third-party strip would ship a DIFFERENT
                                # HEIGHT than the stock rule (#177) and a
                                # seat-measured sheet could be smoothed out
                                # from under its scan (#175).
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
            for fn2 in sorted(os.listdir(up_tmp)):
                m2 = re.match(r"T-(?:0x)?([0-9a-f]{8})_G-(?:0x)?([0-9a-f]{8})"
                              r"_I-(?:0x)?([0-9a-f]{8})\.png", fn2, re.I)
                if not m2:
                    continue
                key = (int(m2.group(2), 16), int(m2.group(3), 16))
                pkg = TP_ART_PACKAGE.get(key)
                if pkg is None:
                    sys.exit("FATAL: thirdparty-art %s has no TP_ART_PACKAGE "
                             "entry - it would ship ungated." % fn2)
                shutil.copy2(os.path.join(up_tmp, fn2),
                             os.path.join(tp_stage_dir(pkg), fn2))
                print("   third-party ART {%08x,%08x} x%g -> %s"
                      % (key[0], key[1], FACTOR, pkg))

        for pkg in TP_PACKAGES:
            sdir = tp_stage_dir(pkg)
            odat = tp_out_dat(pkg)
            n_tp = len(os.listdir(sdir))
            if n_tp == 0:
                continue
            print("Third-party stage %s: %d script(s) -> packing..." % (pkg, n_tp))
            r = subprocess.run([PACKER, sdir, odat], capture_output=True, text=True)
            print(r.stdout.strip())
            if r.returncode != 0:
                sys.exit("THIRD-PARTY PACK FAILED (%s):\n%s" % (pkg, r.stderr))
            r = subprocess.run([PACKER, "--list", odat],
                               capture_output=True, text=True)
            tp_lines = [ln for ln in r.stdout.splitlines()
                        if re.match(r"0x[0-9A-Fa-f]{8} 0x[0-9A-Fa-f]{8} 0x[0-9A-Fa-f]{8} ", ln)]
            if len(tp_lines) != n_tp:
                sys.exit("FATAL: %s pack has %d entries but staged %d files"
                         % (pkg, len(tp_lines), n_tp))
            print("   packed %s (%d entries) -> Plugins\\zzz-SC4UIScale\\"
                  % (os.path.basename(odat), n_tp))
            for d in tp_dialog:
                if d["pkg"] != pkg:
                    continue
                ra = d["root_area"]
                print("      %s %s root %s -> %dx%d"
                      % (d["iid_s"], d["name"], ra,
                         scale_len(ra[2]) - scale_len(ra[0]),
                         scale_len(ra[3]) - scale_len(ra[1])))

    # ---- pack + verify ----
    n_staged = len(os.listdir(STAGE))
    print("Stage files: %d (%d scripts + %d PNGs) -> packing..."
          % (n_staged, len(TARGETS), len(staged_pngs)))
    r = subprocess.run([PACKER, STAGE, OUT_DAT], capture_output=True, text=True)
    print(r.stdout.strip())
    if r.returncode != 0:
        sys.exit("PACK FAILED:\n" + r.stderr)
    r = subprocess.run([PACKER, "--list", OUT_DAT], capture_output=True, text=True)
    listing = r.stdout
    entry_lines = [ln for ln in listing.splitlines()
                   if re.match(r"0x[0-9A-Fa-f]{8} 0x[0-9A-Fa-f]{8} 0x[0-9A-Fa-f]{8} ", ln)]
    if len(entry_lines) != n_staged:
        sys.exit("FATAL: packed %d entries but staged %d files"
                 % (len(entry_lines), n_staged))
    size = os.path.getsize(OUT_DAT)
    print("Packed %s: %d entries, %d bytes -- listing verified"
          % (os.path.basename(OUT_DAT), len(entry_lines), size))

    # ---- REPORT.md ----
    art_log = [(tgi,) + art_plan[tgi] for tgi in all_target_tgis]
    lines = []
    a = lines.append
    a("# Region-screen dialogs -- static %s (`%s`)" % (FACTOR_LABEL, os.path.basename(OUT_DAT)))
    a("")
    a("Built %s by `build_dialog_static.py`. STANDALONE package: the game creates each" %
      __import__("datetime").date.today().isoformat())
    a("of the %d region-screen dialogs/popups already doubled from an edited copy of its"
      % len(TARGETS))
    a(".UI script and lays out the children itself. No runtime scaling involved; runtime")
    a("docking of the region-dialog roots must stay disabled while testing. The recipe is")
    a("the one user-VALIDATED in-game on the Load Region dialog (2026-07-21) and then on")
    a("the six-dialog dat; the previously shipped scripts are re-emitted UNCHANGED through")
    a("the same pipeline, so everything lives in this one dat, which REPLACES the earlier")
    a("dat of the same name.")
    a("")
    a("| Dialog | Script TGI (T/G/I) | Root window |")
    a("|---|---|---|")
    for d in per_dialog:
        ra = d["root_area"]
        a("| %s | `0x00000000 / 0x%08X / 0x%s` | %s id=%s, 1x %dx%d |"
          % (d["name"], TARGET_GID, d["iid_s"].upper(), d["root_clsid"],
             fmt_id(d["root_id"]), ra[2] - ra[0], ra[3] - ra[1]))
    a("")
    a("## Target selection (2026-07-22 additions)")
    a("")
    a("- QUIT DIALOG: both candidates inspected; BOTH are quit variants, both included.")
    a("  `I-4a551b4c` is the region-screen quit confirm (buttons \"Quit SimCity 4\" /")
    a("  \"Cancel\", 330x109); `I-8a5ab1cf` is the \"Are you sure you want to quit")
    a("  SimCity 4?\" Accept/Cancel variant (313x128, root at the (251,180) region-dialog")
    a("  anchor).")
    a("- START NEW CITY BUBBLE: `I-0a8cd184` (caption \"Start New City\", tail-anchored")
    a("  popup root 0x0a551c50). The game positions it (tail at the clicked tile), so")
    a("  only SIZES change -- safe to static-double.")
    a("- EXISTING-CITY BUBBLE: `I-ca539340` picked by content (city-name field, star")
    a("  rating, \"Mayor Rating:\", funds, population rows, gift/demolish/play buttons,")
    a("  same 0x0a551c50 popup root at (146,71)). EXCLUDED: `I-0b72f276` and")
    a("  `I-ea287193` -- 96-107 KB city-HUD region-view panels (\"Map View\"/\"Data")
    a("  Views\"/zone legend), not region-screen bubbles; also excluded per instruction:")
    a("  `2bc9060f`/`6bc9065a`/`898897de`/`ea2871aa` (city-HUD panels) and the")
    a("  G-4a87bfe8 hit (font table).")
    a("- PHOTO ALBUM: `I-4a8cc5ea` (captions \"Photo Album\"/\"Albums\"/\"(add")
    a("  description here)\"/\"Close\"; the snapshot viewfinder pane is inside this")
    a("  same script). EXCLUDED per instruction: `I-49889894` -- a 476x43 bottom")
    a("  strip, not a dialog.")
    a("")
    a("## Package contents (%d entries, %d bytes)" % (len(entry_lines), size))
    a("")
    a("%d edited .UI scripts at their ORIGINAL TGIs (same-TGI overrides) + %d PNGs:"
      % (len(TARGETS), len(staged_pngs)))
    a("")
    a("| TGI | What |")
    a("|---|---|")
    for d in per_dialog:
        a("| `0x00000000 / 0x%08X / 0x%s` | edited %s .UI script |"
          % (TARGET_GID, d["iid_s"].upper(), d["name"]))
    for (gid, iid), out_name, dims in staged_pngs:
        action, clone, _ = art_plan[(gid, iid)]
        if action == "clone":
            cg, ci = clone
            a("| `0x%08X / 0x%08X / 0x%08X` | 2x CLONE of `{%08x,%08x}` (%sx%s px) |"
              % (PNG_TYPE, cg, ci, gid, iid, dims[0], dims[1]))
        else:
            a("| `0x%08X / 0x%08X / 0x%08X` | 2x IN-PLACE override of `{%08x,%08x}` (%sx%s px) |"
              % (PNG_TYPE, gid, iid, gid, iid, dims[0], dims[1]))
    a("")
    a("## Global art plan (%d distinct TGIs; ONE decision per TGI across all %d targets)"
      % (len(art_log), len(TARGETS)))
    a("")
    a("| image={gid,iid} | Used by | Decision | Detail |")
    a("|---|---|---|---|")
    for (gid, iid), action, clone, reason in art_log:
        users = ", ".join(d["iid_s"] for d in per_dialog if (gid, iid) in d["art_refs"])
        if action == "clone":
            a("| `{%08x,%08x}` | %s | CLONED -> `{%08x,%08x}` | %s |"
              % (gid, iid, users, clone[0], clone[1], reason))
        elif action == "inplace":
            a("| `{%08x,%08x}` | %s | 2x IN PLACE | %s |" % (gid, iid, users, reason))
        else:
            a("| `{%08x,%08x}` | %s | LEFT 1x | %s |" % (gid, iid, users, reason))
    a("")
    a("Clone IID scheme: `iid ^ 0x53430001` (selective-safe convention), each verified")
    a("collision-free against the full game PNG store (`extracted-png-tgi.csv`, %d TGIs),"
      % len(store_tgis))
    a("every .UI-referenced TGI (%d), selective-safe's %d planned clone TGIs, and the"
      % (len(all_ref_tgis), len(refmap_clones)))
    if fallback_clones:
        a("other clones of this run. Fallback `^ 0x53430002` was needed for %d TGI(s)"
          % len(fallback_clones))
        a("whose primary slot is already claimed by a selective-safe planned clone: " +
          ", ".join("`{%08x,%08x}`" % t for t in fallback_clones) + ".")
    else:
        a("other clones of this run. No fallback to `^ 0x53430002` was needed.")
    a("")
    a("## Per-dialog edits")
    a("")
    a("Common to all: EVERY `area=(x1,y1,x2,y2)` doubled (corner-format absolute px;")
    a("the first `id=` in a file is not always the meaningful root, so ALL areas are")
    a("doubled regardless); `imagerect=` doubled ONLY where that control's art went 2x;")
    a("`font=NAME` converted to GUID form via `tools\\fonts\\FontStyle.candidate.ini`")
    a("(proven deserializer path, type-6 token -> SetFontStyleByGUID; fonts are already")
    a("confirmed loading in-game, so this is belt-and-braces consistency, not the size")
    a("fix). Every edited script was re-parsed and machine-verified node-for-node")
    a("(areas exactly 2x, refs retargeted per plan, imagerects 2x iff art 2x, fonts in")
    a("GUID form) before packing.")
    for d in per_dialog:
        ra = d["root_area"]
        a("")
        a("### %s (`I-%s`, source `%s`)" % (d["name"], d["iid_s"], d["fn"]))
        a("")
        nra = tuple(scale_len(v) for v in ra)
        a("- Root %s id=%s: area `(%d,%d,%d,%d)` -> `(%d,%d,%d,%d)` (%dx%d -> %dx%d)."
          % ((d["root_clsid"], fmt_id(d["root_id"])) + ra + nra +
             (ra[2] - ra[0], ra[3] - ra[1], nra[2] - nra[0], nra[3] - nra[1])))
        if d["iid_s"] in OVERSIZE_ROOT_IIDS:
            a("  NOTE: this root gen is larger than the visible dialog art -- expected,")
            a("  doubled as-is by design.")
        if d["iid_s"] in BUBBLE_IIDS:
            a("  NOTE: tail-anchored popup -- the GAME positions it (tail at the clicked")
            a("  tile), so the doubled origin is irrelevant; only the doubled SIZE is the")
            a("  assertion. Its body+tail bubble art %s IS among the doubled TGIs (see"
              % ("`{46a006b0,14416321}`" if d["iid_s"] == "0a8cd184"
                 else "`{46a006b0,14416322}`"))
            a("  the art plan), split across two BMPs whose `imagerect` slices were")
            a("  doubled with it.")
        a("- `area=` rects doubled: %d (every one in the script; %d controls total)."
          % (d["area_count"], d["n_nodes"]))
        a("- Art refs: " + "; ".join(
            "`{%08x,%08x}` x%d %s" % (g, i, n,
                                      {"clone": "-> clone", "inplace": "2x in place",
                                       "left1x": "LEFT 1x"}[art_plan[(g, i)][0]])
            for (g, i), n in sorted(d["art_refs"].items())) + ".")
        if d["rect_log"]:
            a("- `imagerect=` doubled (%d):" % len(d["rect_log"]))
            for clsid, old, new in d["rect_log"]:
                a("  - %s `%s` -> `%s`" % (clsid, old, new))
        else:
            a("- `imagerect=` doubled: none present on 2x-art controls.")
        if d["no_rect_2x"]:
            a("- %d control(s) with 2x art but no `imagerect` (edge-slice frames /"
              % d["no_rect_2x"])
            a("  button state strips -- the engine fits cells to the control area;")
            a("  self-adapting, eyeball frame thickness in-game).")
        if d["font_counts"]:
            a("- Fonts converted: " + "; ".join(
                "`%s` x%d -> `0x%08x` (%s px ini%s)" % (
                    nm, n, styles[nm][0],
                    styles[nm][1] if styles[nm][1] is not None else "?",
                    ", was %d" % (styles[nm][1] // 2) if styles[nm][1] else "")
                for nm, n in sorted(d["font_counts"].items())) + ".")
        else:
            a("- Fonts converted: none (no name-form font tokens).")
        if d["left1x"]:
            a("- Controls left fully 1x (no 2x asset): " + "; ".join(
                "%s `{%08x,%08x}`" % (c, g, i) for c, (g, i) in d["left1x"]) + ".")
    a("")
    a("## Expected on-screen result (2400x1600 table)")
    a("")
    a("| Dialog | 1x root | %s root | Note |" % FACTOR_LABEL)
    a("|---|---|---|---|")
    for d in per_dialog:
        ra = d["root_area"]
        if d["iid_s"] in OVERSIZE_ROOT_IIDS:
            note = "root gen larger than visible dialog art"
        elif d["iid_s"] in BUBBLE_IIDS:
            note = "game-positioned (tail anchor); size-only assertion"
        else:
            note = ""
        nra = tuple(scale_len(v) for v in ra)
        a("| %s | %dx%d at (%d,%d) | **%dx%d** at (%d,%d) | %s |"
          % (d["name"], ra[2] - ra[0], ra[3] - ra[1], ra[0], ra[1],
             nra[2] - nra[0], nra[3] - nra[1], nra[0], nra[1], note))
    a("")
    a("- GZWinGen dialog roots are positioned by the game's dialog-open code, so final")
    a("  placement may be re-centered by the game -- the SIZE is the assertion, the")
    a("  origin is best-effort.")
    a("- Frame/title-bar 9-slice art and button strips render from the 2x clones (or")
    a("  in-place 2x art) with doubled `imagerect` insets where the script carried any.")
    a("- Every OTHER dialog in the game keeps the untouched 1x originals: shared art is")
    a("  isolated behind new-TGI clones; the only in-place 2x art is exclusive to these")
    a("  six scripts.")
    a("- Captions render at %s sizes via GUID font binding + the deployed %s-scaled" % (FACTOR_LABEL, FACTOR_LABEL))
    a("  FontStyle table (%s), whose [Font Styles] sizes = round(1x * %g). The dialog"
      % (("FontStyle.candidate.ini" if not TAG else "FontStyle-%s.ini" % TAG), FACTOR))
    a("  scripts only bind styles by GUID; the sizes come from that loose FontStyle file.")
    a("")
    a("## Interop / preconditions")
    a("")
    a("- No TGI overlap with `z_SC4UIScale_SelectiveArt.dat`: selective-safe ships none")
    a("  of these %d .UI scripts (checked against its stage + refmap scaled sets), and"
      % len(TARGETS))
    a("  every clone IID here was collision-checked against its planned clones (%d fell"
      % len(fallback_clones))
    a("  back to `^ 0x53430002` for exactly that reason). The two dats coexist.")
    a("- Runtime scaling/docking of the region-dialog roots (UiSpike kRegionDialogDocks:")
    a("  " + ", ".join(sorted({fmt_id(d["root_id"]) for d in per_dialog
                               if d["root_id"] is not None})) + ")")
    a("  must remain disabled, or the dialogs get doubled twice.")
    a("- The doubled FontStyle.ini must be deployed (it is) for the font step to show.")
    a("")
    a("## Revert")
    a("")
    a("Delete `z_SC4UIScale_DialogStatic.dat` from the Plugins folder it was copied to.")
    a("That is the whole footprint: the package only ADDS same-TGI .UI overrides and")
    a("new-TGI PNG clones (plus one exclusive in-place PNG override); no game file is")
    a("modified. (Nothing was deployed by the build; the dat lives only in")
    a("`tools\\dialog-static\\` until copied by hand.)")
    a("")
    with open(REPORT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("Wrote " + REPORT)

    # ---- console summary ----
    print("\n=== SUMMARY ===")
    for d in per_dialog:
        print("%-28s areas=%2d rects2x=%d fonts=%2d left1x=%d"
              % (d["name"], d["area_count"], len(d["rect_log"]),
                 sum(d["font_counts"].values()), len(d["left1x"])))
    # Task #55 lesson (Grutzehaus + the U-Drive-It pickers): a left-1x ref
    # inside a frame this builder DOUBLES is a bug shape, not a fallback -
    # judge it at build time instead of in the user's game. DANGLING = the
    # TGI is not in the game's PNG store; the pixels arrive at runtime and
    # must be handled (RUNTIME_BOUND_2X here, or a task-#47 draw hook).
    # MISSING-2X = real 1x art that WILL corner/tile-draw in the doubled
    # frame; generate its 2x.
    left1x_warned = set()
    for d in per_dialog:
        for (c, (g, i)) in d["left1x"]:
            if (g, i) in left1x_warned:
                continue
            left1x_warned.add((g, i))
            kind = ("DANGLING .UI ref - runtime-supplied pixels (needs "
                    "RUNTIME_BOUND_2X or a task-#47 draw hook)"
                    if (g, i) not in store_tgis else
                    "MISSING-2X - 1x art WILL draw wrong in the doubled frame")
            print("WARNING LEFT1X {%08x,%08x} (%s, e.g. %s): %s"
                  % (g, i, c, d["name"], kind))
    for (gid, iid), action, clone, reason in art_log:
        extra = " -> {%08x,%08x}" % clone if clone else ""
        print("art {%08x,%08x}: %s%s (%s)" % (gid, iid, action.upper(), extra, reason))
    if unmapped_fonts:
        print("UNMAPPED fonts (left as-is): " + ", ".join(sorted(unmapped_fonts)))
    print("Package: %s (%d entries, %d bytes)" % (OUT_DAT, len(entry_lines), size))


if __name__ == "__main__":
    main()
