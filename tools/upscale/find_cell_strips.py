r"""Emit the list of art TGIs that are PROVABLY horizontal state strips (#156).

⛔ WHY THIS EXISTS. `Upscale2x::CellUnit` guesses "this width divides by 3 or 4,
so it might be a cell strip". That guess is SAFE for its original job -
preserving divisibility costs nothing when it is wrong - and UNSAFE the moment
it is used to re-time pixels: scoped by CellUnit, cell-aligned sampling changed
1186 of 2206 sheets and displaced an advisor frame's flood-filled aperture by a
pixel (the #152 seat guard caught it, see REGRESSION.md #156).

The upscaler cannot know what a sheet is. The `.UI` scripts that BIND it can.
A control that draws one state of a strip is declared with an `area=` whose
size is exactly one cell, so:

    states  = sheetW / windowW      (must divide exactly)
    and       sheetH == windowH     (a horizontal strip is one row of cells)

That is a derivation, not a heuristic: if a script binds a 84x21 sheet to a
21x21 window, the sheet IS four states of 21px. Anything that fails those two
tests is left out and keeps the sampling it has today.

Reads the STOCK corpus and the third-party sources - the same two places the
builders read - and writes `cell-strips.txt`:

    <gid hex> <iid hex> <states>     # one per line, sorted, with a comment

    python find_cell_strips.py [--out cell-strips.txt]

height-exact-strips.txt is written NEXT TO the --out file (same directory,
fixed basename) - hardwiring it here made a --out preview run clobber the
shipped file (review finding F9, 2026-08-16).

Read-only apart from its own two output files.
"""
import os
import re
import struct
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
UI_DIRS = [os.path.join(TOOLS, "uiscripts", "extracted"),
           os.path.join(TOOLS, "dialog-static", "thirdparty-src")]
ART_DIRS = [os.path.join(TOOLS, "dbpf", "extracted", "SimCity_1"),
            os.path.join(TOOLS, "dialog-static", "thirdparty-art")]

NODE = re.compile(r"<LEGACY\s+[^>]*?>", re.S)
AREA = re.compile(r"area=\((-?\d+),(-?\d+),(-?\d+),(-?\d+)\)")
IMAGE = re.compile(r"image=\{([0-9a-fA-F]+),([0-9a-fA-F]+)\}")
RECT = re.compile(r"imagerect=\(")


def png_wh(path):
    try:
        with open(path, "rb") as f:
            head = f.read(24)
    except OSError:
        return None
    if head[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    return struct.unpack(">II", head[16:24])


def find_art(gid, iid):
    for d in ART_DIRS:
        for n in ("T-856ddbac_G-%08x_I-%08x.png" % (gid, iid),
                  "T-0x856ddbac_G-0x%08x_I-0x%08x.png" % (gid, iid)):
            p = os.path.join(d, n)
            if os.path.isfile(p):
                return p
    return None


RECT_FULL = re.compile(r"imagerect=\((-?\d+),(-?\d+),(-?\d+),(-?\d+)\)")


def main():
    out = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv \
        else os.path.join(HERE, "cell-strips.txt")
    # #177: alongside the strip list, derive WHICH strips may take an EXACT
    # height (no vertical cell snap). The blanket form of this was tried as
    # --height-exact-strips over the whole list and reverted for "breaking the
    # ? button {46a006b0,14415860}" - an attribution wrong TWICE: 14415860 is
    # the god-mode toolbar sun button, not the "?", and its sheet is 256x50
    # (CellUnit(50)=1, no snap on either rule), so the flag was a provable
    # no-op for it. The honest form is a DERIVATION (law 94): a strip's height
    # is safe to take exactly iff NOTHING gives the sheet vertical structure -
    # no consumer crops it vertically, and no rule-(b) consumer exists (the
    # engine 9-slices a rule-(b) CELL into its window, which cuts /3
    # VERTICALLY, so those heights must keep the snap).
    # F9: derived from --out's directory (same basename), NOT hardwired to
    # HERE - a --out preview run used to silently clobber the shipped file.
    out_hx = os.path.join(os.path.dirname(os.path.abspath(out)),
                          "height-exact-strips.txt")
    votes = defaultdict(set)          # (gid,iid) -> {states seen}
    binds = defaultdict(int)
    bmp_bound = set()                 # also drawn by a plain GZWinBMP
    vsnap = {}                        # (gid,iid) -> reason its height has structure
    scripts = 0
    for d in UI_DIRS:
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            if not fn.lower().endswith(".ui"):
                continue
            scripts += 1
            with open(os.path.join(d, fn), "r", encoding="latin-1") as fh:
                txt = fh.read()
            for m in NODE.finditer(txt):
                node = m.group(0)
                a, i = AREA.search(node), IMAGE.search(node)
                if not a or not i:
                    continue
                gid, iid = int(i.group(1), 16), int(i.group(2), 16)
                # #177: ANY consumer whose crop covers less than the sheet's
                # full height (t>0, or bottom short of the sheet) proves the
                # height carries structure - stacked cells, a sub-band, a
                # second row. Checked for EVERY clsid, before any filter below
                # drops the node from the STATES vote.
                rc = RECT_FULL.search(node)
                if rc and (gid, iid) not in vsnap:
                    p0 = find_art(gid, iid)
                    wh0 = png_wh(p0) if p0 else None
                    if wh0:
                        _, ct, _, cb = (int(x) for x in rc.groups())
                        if ct > 0 or cb < wh0[1]:
                            vsnap[(gid, iid)] = "partial-height crop %d..%d of %d in %s" % (
                                ct, cb, wh0[1], fn)
                # ⛔ MIXED CONSUMER = HANDS OFF. If a plain GZWinBMP anywhere
                # draws this same sheet, it is not purely a state strip and
                # re-timing it per cell would disturb that other consumer.
                # Same shape as AXIS 10: an art change is scoped to the whole
                # game, never to the script you were looking at.
                if "GZWinBMP" in node:
                    bmp_bound.add((gid, iid))
                    continue
                # A crop means the script picks its own sub-rect; the cell
                # arithmetic below does not describe it.
                if "GZWinBtn" not in node or RECT.search(node):
                    continue
                l, t, r, b = (int(x) for x in a.groups())
                ww, wh = r - l, b - t
                if ww <= 0 or wh <= 0:
                    continue
                p = find_art(gid, iid)
                wh_art = png_wh(p) if p else None
                if not wh_art:
                    continue
                sw, sh = wh_art
                binds[(gid, iid)] += 1
                # THE DERIVATION, strongest form first.
                # (a) ART-SIZED: one row of cells, each exactly the window.
                #     The window measures the cell directly - no assumption.
                if sh == wh and sw % ww == 0 and sw // ww >= 2:
                    votes[(gid, iid)].add(sw // ww)
                # (b) The window does NOT measure the cell (it is bigger, or a
                #     different height - the engine 9-slices the cell into it).
                #     We still know it is a BUTTON STRIP, and the engine's
                #     button path divides the sheet by FOUR (SC4-UI-ENGINE
                #     3.3 "multi-state sheets"; the four-state divide is the
                #     one compiled into the blit). Accept 4 only when the
                #     sheet actually divides by 4 - otherwise leave it alone.
                #     This is the case the region bubble's population rows
                #     fall into: sheet 84x21, window 94x16.
                elif sw % 4 == 0:
                    votes[(gid, iid)].add(4)
                    # #177: a rule-(b) cell is 9-SLICED into its window, and a
                    # 9-slice cuts /3 VERTICALLY - this sheet's height is load-
                    # bearing structure, so it must keep the vertical snap.
                    if (gid, iid) not in vsnap:
                        vsnap[(gid, iid)] = ("rule-(b) consumer %dx%d in %s "
                                             "(cell is 9-sliced)" % (ww, wh, fn))

    strips, conflict, mixed = {}, [], []
    for k, s in votes.items():
        if k in bmp_bound:
            mixed.append(k)
        elif len(s) == 1:
            strips[k] = s.pop()
        else:
            # Two scripts disagree about the cell count. Do NOT pick one -
            # leave the sheet alone; a wrong cell count re-times it just as
            # badly as no cell count at all.
            conflict.append((k, sorted(s)))

    # F3: REFUSE LOUDLY before writing either file. The CODE_BOUND merge below
    # makes both lists never-empty, which defeats Rebuild-Corpus.ps1's
    # empty-list guard - so a run that read zero scripts (an unreachable
    # UI_DIRS is enough) or derived zero strips used to exit 0 with 1-entry
    # lists and silently un-ship #156/#177 at the next corpus rebuild.
    if scripts == 0:
        print("FATAL: ZERO .UI scripts read from %s - the derivation never "
              "ran. Refusing to write cell-strips.txt/height-exact-strips.txt"
              " from CODE_BOUND alone; fix the UI dirs and re-run."
              % " and ".join(UI_DIRS))
        sys.exit(1)
    if not strips:
        print("FATAL: %d script(s) read but ZERO strips derived (the shipped "
              "list has 193). Refusing to write cell-strips.txt/height-exact-"
              "strips.txt from CODE_BOUND alone - a corpus rebuilt from them "
              "would silently un-ship #156/#177." % scripts)
        sys.exit(1)

    # CODE-BOUND strips - zero .UI references, so the derivation above cannot
    # see them BY CONSTRUCTION (same blindness make_no_smooth.py:78 documents).
    # F10 table shape: {(g,i): (states, 'exact'|'snap', reason)} - the height
    # rule is DECLARED per entry with its byte evidence, not defaulted (the
    # old table could only ever land in height-exact, so a code-bound strip
    # needing the vertical snap had no way to say so). 'snap' entries land in
    # vsnap with their reason; add nothing here without a disassembled
    # divisor AND a disassembled height rule.
    CODE_BOUND = {
        (0x46a006b0, 0x14015584): (6, 'exact',
            # cSC4WinTrendBar fill strip (City Opinion Polls). Draw 0x7BF0A0
            # computes bandW = fillW/6 (0x7BF0E4 imul 0xAAAAAAAB, 0x7BF0F5
            # shr edi,2 = the /6 reciprocal) - a SIX-cell strip, 42/6=7 at 1x.
            # Plain rounding ships 63 at 1.5x: floor(63/6)=10 vs painted 10.5
            # pitch = up to 2.5px of neighbour-cell bleed at cell 5.
            # Cell-first gives 6*R(7*1.5)=66, exact. Integer no-op:
            # 6*14=84=42*2, 6*21=126=42*3. (Disassembled 2026-08-16, #176.)
            # Height 'exact': the fill is drawn FULL HEIGHT, centred whole,
            # in the same disassembled draw 0x7BF0A0 - nothing cuts it
            # vertically, so no snap structure exists.
            "cSC4WinTrendBar /6 fill strip, draw 0x7BF0A0 (0x7BF0E4 imul "
            "0xAAAAAAAB + shr edi,2); height full-height-centred in the same "
            "draw"),
    }
    for k, (n, hx_rule, why) in CODE_BOUND.items():
        if k in strips and strips[k] != n:
            conflict.append((k, sorted({strips[k], n})))
            del strips[k]
            continue
        strips[k] = n
        if hx_rule == 'snap' and k not in vsnap:
            vsnap[k] = "CODE_BOUND: " + why

    with open(out, "w", encoding="ascii", newline="\n") as f:
        f.write("# Art TGIs PROVEN to be horizontal state strips (#156).\n")
        f.write("# Generated by tools\\upscale\\find_cell_strips.py - do not "
                "hand-edit.\n")
        f.write("# Derived, not guessed: a .UI binds the sheet to a window\n"
                "# whose HEIGHT equals the sheet's and whose WIDTH divides it.\n")
        f.write("# Code-bound entries (zero .UI refs; byte evidence - F10):\n")
        for (g, i), (n, hx_rule, why) in sorted(CODE_BOUND.items()):
            if (g, i) in strips:
                f.write("#   {%08x,%08x} states=%d height=%s: %s\n"
                        % (g, i, n, hx_rule, why))
        f.write("# <group> <instance> <states>\n")
        for (g, i), n in sorted(strips.items()):
            f.write("%08x %08x %d\n" % (g, i, n))

    # #177: the height-exact SUBSET - strips with NO vertical structure. Fed
    # to Upscale2x --height-exact-strips (2-token format). A strip is exact
    # unless (i) some consumer crops it vertically or (ii) a rule-(b) consumer
    # 9-slices its cell. This replaces the reverted blanket form; the vsnap
    # reasons below are the derivation's own audit trail.
    hx = {k: n for k, n in strips.items() if k not in vsnap}
    with open(out_hx, "w", encoding="ascii", newline="\n") as f:
        f.write("# #177: state strips whose HEIGHT takes plain rounding (no\n"
                "# vertical cell snap). Generated by find_cell_strips.py - do\n"
                "# not hand-edit. A strip is here iff NOTHING gives its sheet\n"
                "# vertical structure: no partial-height imagerect by any\n"
                "# consumer, no rule-(b) (9-sliced cell) consumer.\n"
                "# <group> <instance>\n")
        for (g, i) in sorted(hx):
            f.write("%08x %08x\n" % (g, i))
    print("scripts read            : %d" % scripts)
    print("art-bound button sheets : %d" % len(binds))
    print("PROVEN state strips     : %d  -> %s" % (len(strips), out))
    print("height-exact subset     : %d  -> %s   (vsnap excluded: %d)"
          % (len(hx), out_hx, len([k for k in strips if k in vsnap])))
    for k in sorted(k for k in strips if k in vsnap)[:12]:
        print("  KEEPS SNAP %08x %08x : %s" % (k[0], k[1], vsnap[k]))
    print("state-count histogram   : %s"
          % sorted({n: list(strips.values()).count(n) for n in set(strips.values())}.items()))
    if mixed:
        print("EXCLUDED, also drawn by a plain GZWinBMP (mixed consumer): %d"
              % len(mixed))
    if conflict:
        print("EXCLUDED, scripts disagree on the cell count: %d" % len(conflict))
        for k, s in conflict[:8]:
            print("   {%08x,%08x} seen as %s states" % (k[0], k[1], s))


main()
