"""census.py - STAGE 1: the BUILDER CENSUS.

Every call site of the window-create / label / band / stacker primitives in
.text, grouped by the function that owns it, with the owning dialog/panel
identified where determinable.

Outputs
    builders.json         machine-readable census
    BUILDER-CENSUS.md     human, with VAs
    _work/census/*.json   per-unit partials (resume granularity)

Primitive set
    The seven direct-call UI factories decoded from the exe (see
    PRIMITIVES below - each arity is PROVEN by the callee's `ret N`), plus
    the in-builder vtable geometry ops SetSize/SetArea/SetPosition.
    `--discover` additionally reports every OTHER function that both
    (a) drives a window rect (`call [r+0xD4/0xD8/0xDC/0xE0]`) and
    (b) is called from more than one place - i.e. candidate primitives we
    have not named yet.

Every accepted site is double-proven: found by byte scan (scan_text.py) AND
present as a real `call` instruction when its owning function is
disassembled linearly from its own start.

Usage:
    python census.py --resume
    python census.py --resume --discover
"""
import os
import re
import sys
from collections import Counter, defaultdict

import common as C
import argscan as A
import geomextra as G

# --------------------------------------------------------------------------
# THE PRIMITIVES.  arity is proven by the callee's `ret N`; the arg roles by
# reading the callee (see BUILDER-CENSUS.md "Primitive signatures").
# --------------------------------------------------------------------------
PRIMITIVES = {
    0x779660: dict(name="TextLabel", arity=10,
                   args=["parent", "id", "x", "y", "pText", "align",
                         "styleId", "R", "G", "B"],
                   geom={"x": 2, "y": 3},
                   note="autosize to text then SetArea(l=r.right,t=r.top,"
                        "r=1000,b=r.bottom) - the push 0x3e8 at 0x77971A"),
    0x779CA0: dict(name="TextLabelWrap", arity=11,
                   args=["parent", "id", "x", "y", "w", "pText", "align",
                         "styleId", "R", "G", "B"],
                   geom={"x": 2, "y": 3, "w": 4},
                   note="near-clone of sub_779B80 but creates through win-mgr "
                        "vt+0x24 (multi-line/wrapping text) instead of vt+0x34. "
                        "ONE call site: the master-budget row building-name. "
                        "CodePatches.cpp's comments attribute that create to "
                        "sub_779B80 - it is this function."),
    0x779B80: dict(name="TextLabelW", arity=11,
                   args=["parent", "id", "x", "y", "w", "pText", "align",
                         "styleId", "R", "G", "B", "?"],
                   geom={"x": 2, "y": 3, "w": 4},
                   note="explicit width; height = font line height"),
    0x7794E0: dict(name="Slider", arity=9,
                   args=["parent", "id", "x", "y", "w", "a6", "a7", "a8", "a9"],
                   geom={"x": 2, "y": 3, "w": 4},
                   note="height is a HARDCODED 14 - lea edx,[ecx+0xe] at 0x779548"),
    0x7798C0: dict(name="Combo", arity=5,
                   args=["a1", "id", "x", "y", "a5"],
                   geom={"x": 2, "y": 3},
                   note="w=120 lea [edx+0x78] @0x77992F, h=15 lea [ecx+0xf] "
                        "@0x779927 - disp8, cannot hold 2x"),
    0x77A390: dict(name="BandArt", arity=4,
                   args=["instId", "x", "y", "parent"],
                   geom={"x": 1, "y": 2},
                   note="PNG {0x856DDBAC,0x46A006B0,inst}; window sized FROM "
                        "THE ART; returns art height"),
    0x77A250: dict(name="BmpArt", arity=5,
                   args=["instId", "x", "y", "a4", "parent"],
                   geom={"x": 1, "y": 2},
                   note="same TGI family, image assigned to this+0xD8"),
    0x77B960: dict(name="Button", arity=7,
                   args=["parent", "id", "x", "y", "captionTgi", "a6", "a7"],
                   geom={"x": 2, "y": 3},
                   note="Accept/Cancel pairs; size comes from a separate "
                        "GetChildWindowFromID + SetSize(180,30)"),
    0x77B7B0: dict(name="CheckStrip", arity=7,
                   args=["parent", "id", "x", "y", "artTgi", "a6", "state"],
                   geom={"x": 2, "y": 3},
                   note="checkbox / category strip (art-sized); the ordinance "
                        "eye rides these"),
    0x77A6F0: dict(name="BandStacker", arity=3,
                   args=["a1", "a2", "a3"], geom={},
                   note="vertical band stacker for the D-series (500-wide) "
                        "band set: slider departments + Neighbor Deals; "
                        "y-cursor at [builder+0x80]"),
    0x77A480: dict(name="BandStackerOrd", arity=3,
                   args=["a1", "a2", "a3"], geom={},
                   note="band stacker for the F-series (450-wide) Ordinances "
                        "band set"),
    0x77A960: dict(name="BandStackerXfer", arity=2,
                   args=["a1", "a2"], geom={},
                   note="band stacker for the 0x2BFEB0Cx (650-wide) band set "
                        "(Transportation / Master)"),
    0x779850: dict(name="AddChild", arity=2,
                   args=["child", "parent"], geom={},
                   note="reparent helper"),
}

VT_NAME = {0xD4: "SetSize", 0xD8: "SetAreaRect", 0xDC: "SetArea",
           0xE0: "SetPosition"}

# Byte patterns for `call [reg+off]` where off drives a window rect.
# Encoding: FF /2 with a disp32 -> `FF <modrm> <disp32>`, modrm 0x9x =
# mod=10 (disp32), reg=010 (/2 = call), rm = the register below.
# rm=4 (esp) is deliberately absent: it requires a SIB byte, so the 6-byte
# form does not exist for it.
#
# ⚠ GENERATED, NOT HAND-LISTED, and that is the point (v2.38.2). The previous
# hand-written tuple omitted **0xD8 for every register** and **ebp entirely**,
# while the comment above it claimed "dc/d4/d8/e0" coverage. Measured against
# the exe: 180 of 1024 window-rect call sites were invisible - 18%, including
# 73 at edx+0xD8 alone. Every "the offline model found nothing" null for a
# SetArea(const Rect*) builder was therefore worthless. Deriving the set from
# VT_NAME x the register table means the scan cannot silently disagree with
# its own documentation again (cf. task #77, the misleading log lines).
RECT_CALL_REGS = {0x90: "eax", 0x91: "ecx", 0x92: "edx", 0x93: "ebx",
                  0x95: "ebp", 0x96: "esi", 0x97: "edi"}
RECT_CALL_PATS = tuple(bytes([0xFF, modrm, off, 0, 0, 0])
                       for modrm in sorted(RECT_CALL_REGS)
                       for off in sorted(VT_NAME))

# Dialog / family identification.  Art instance -> family -> dialog family,
# straight out of BUDGET-DETAIL-ANATOMY.md §1 (measured, not inferred).
ART_FAMILY = {}
for i in range(0xF0, 0xF8):
    ART_FAMILY[0x140155F0 + (i - 0xF0)] = "Ordinances band set (stock 450 wide)"
for i in range(0xD0, 0xD8):
    ART_FAMILY[0x140155D0 + (i - 0xD0)] = ("slider-department / Neighbor Deals "
                                           "band set (stock 500 wide)")
for i in range(0xC7, 0xD0):
    ART_FAMILY[0x2BFEB0C7 + (i - 0xC7)] = "Transportation / Master band set (stock 650 wide)"

# Identification. Every label carries the evidence that fixes it.  The
# department dispatcher is sub_7876B0: it reads the department TYPE from
# [this+0x20], loads that family's metric art, stores contentWidth into
# [this+0x84] and rowPitch into [this+0x88], then calls the family builder.
KNOWN_BUILDERS = {
    0x77A1A0: "helper - reparent/attach (no geometry constants)",
    0x77A480: "BAND STACKER - Ordinances F-series band set (0x140155F0-F7)",
    0x77A6F0: "BAND STACKER - D-series band set (0x140155D0-D7): slider "
              "departments AND Neighbor Deals (2 consumers)",
    0x77A960: "BAND STACKER - 0x2BFEB0CB-CF band set (650 wide)",
    0x77BEC0: "BUDGET / Business Deals empty box (shared text popup, 2nd path)",
    0x77C660: "BUDGET / City Ordinances detail dialog  [dispatch: "
              "[this+0x20]==1 at 0x787BEA, metric art 0x140155F2, "
              "call 0x787C42]",
    0x77E600: "BUDGET / Neighbor Deals detail dialog (13 static row blocks)  "
              "[dispatch: [this+0x20]==2 at 0x787D04, metric art 0x140155D2, "
              "call 0x787D5D]",
    0x781C90: "BUDGET / department-detail REFRESH pass + Accept/Cancel pair "
              "(36x GetChildAsRecursive iid 0x212CDC1F; creates no text). "
              "Called from the panel message handler 0x78C053 and from the "
              "popup path 0x78B3F5/0x78B4B5. NOTE: CodePatches.cpp comments "
              "call its button sites 'Transportation' - the ADDRESSES are "
              "right, the name is not.",
    0x786690: "BUDGET / the 650-wide band-set department dialog  [dispatch: "
              "[this+0x24]!=0 at 0x787E1B, call 0x787E23].  NAME CONFLICT: "
              "CodePatches.cpp calls it 'Master budget sub-dialogs'; "
              "BUDGET-DETAIL-ANATOMY.md calls the 0x2BFEB0C7-CF art family "
              "'Transportation'. Unresolved offline - needs one live BHDR.",
    0x7876B0: "BUDGET / slider departments (Public Safety, Health&Education, "
              "Utilities, City Beautification, Government) AND the department "
              "DISPATCHER that calls 0x77C660 / 0x77E600 / 0x786690",
    0x78B120: "BUDGET / ordinance DESCRIPTION popup path (shared text popup)",
    0x78BCA0: "BUDGET / panel message handler (DoMessage) - dispatch only, "
              "creates nothing",
}


# --------------------------------------------------------------------------
# PROMOTED BUILDERS (task #96, 2026-08-03)
# --------------------------------------------------------------------------
# `by_target` finds an owner only when it CALLS one of the 13 named
# primitives. A builder that drives rects itself calls none of them and is
# therefore invisible to stage 1 no matter how many times it is re-run -
# which is why constants.json had never seen three families we had already
# SHIPPED fixes for (v2.36.0, v2.37.0, v2.40.2).
#
# Promoting a FUNCTION by hand is the same move as naming a primitive in
# PRIMITIVES above: it seeds the scan, it does not supply the answer. Every
# site and every value below is still derived mechanically from the exe by
# geomextra.py. Nothing here is read from src\CodePatches.cpp - if it were,
# crosscheck.py would be a file comparing itself.
#
# Column 3 is how the function was FOUND, and it matters: the first two were
# produced by `--discover` (they are in builders.json -> discovered), so
# promoting them is mechanical. The third has ZERO direct callers - it is
# entered through a vtable - so no discovery pass can ever list it, and it is
# a genuine hand-seed. Said out loud because it is the weakest link here.
EXTRA_BUILDERS = {
    0x7A04F0: dict(
        label="DATA VIEWS / legend re-lay (chip + row rects, v2.37.0 #78)",
        found="--discover (13 callers, 1520 bytes, rect-driving)",
        geometry="two SetArea(const Rect*) at 0x7A082C / 0x7A0955; the "
                 "constants are the stack-rect member stores"),
    0x7EAEB0: dict(
        label="SUB-FLYOUT provider - nested flyout strip metrics (v2.36.0 #50)",
        found="--discover (7 callers, 1136 bytes, rect-driving)",
        geometry="strip SetItemMetrics(44,44,5) at 0x7EAEF7 (vt+0x30 on "
                 "class 0xAB6D28, NOT a cIGZWin slot)"),
    0x7E7270: dict(
        label="FIRST-LEVEL flyout builder - carries the UNPATCHED twin "
              "copies of the strip metrics",
        found="hand-seeded from SUBFLYOUT-BUILDER.md:201 (1 caller, so "
              "--discover's callers>=2 lid excludes it)",
        geometry="same SetItemMetrics triple at 0x7E72A4/A6/A8. CodePatches "
                 "deliberately does NOT patch these (they are scaled after "
                 "birth; patching both double-scales). Censused so the model "
                 "can SEE them - they are expected to show up as EXTRAS."),
    0x793810: dict(
        label="ADVICE / news list row builder - right-hand column reserve "
              "(v2.40.2 #87/#88)",
        found="HAND-SEEDED ONLY. 0 direct callers (vtable-entered) and its "
              "only geometry is measure-relative, so it fails BOTH "
              "--discover criteria and always will.",
        geometry="`call [edx+0xA4]` (GetW) -> `sub esi,0x3D` at 0x79388F: "
                 "reserve = W-61"),
    0x76D3D0: dict(
        label="GRAPHS panel builder - legend column immediates + 3 rebuilt "
              "swatch/checkbox blocks (v2.55.0 #57)",
        found="HAND-SEEDED per crosscheck.py's DEFERRED table (2026-08-04, "
              "Phase 1a): the #57 fix patched 8 sites inside this builder "
              "two hours AFTER constants.json was last generated, so the "
              "model never censused the owner. This promotion is the ONE "
              "measurement the deferral names; guards G1+G2 revoke the "
              "deferral automatically once the regeneration lands.",
        geometry="five 3-byte immediates at 0x76E233/0x76E239/0x76E23C/"
                 "0x76E2AF/0x76E2C8 (swatch dy/bottom/width, swatch->text "
                 "gap, text right edge) + three whole-block rebuilds at "
                 "0x76E0E8/0x76E145/0x76E1D6 (25/41/42 bytes, rel32 targets "
                 "relocated). The blocks may need an encoding the model "
                 "does not have - if regeneration covers the five "
                 "immediates but not the blocks, that is a MEASUREMENT "
                 "(model needs a block-rewrite schema), not a failure."),
    0x7EAC70: dict(
        label="COST BOX right-align anchor owner (#159, v4.5.x)",
        found="--discover (2 callers, 576 bytes, rect-driving) - measured in "
              "builders.json discovered 2026-08-30; mechanical promotion.",
        geometry="the 8-byte window at 0x7EAD4B (add ebx,0x7C; push 0x8001) "
                 "that kCostOriginSite re-encodes to a cave jmp; censusing "
                 "the owner lets the model hold the stock push imm32 at "
                 "0x7EAD4E independently of CodePatches."),
    0x7EDEB0: dict(
        label="CITY DOCK / cost box builder - cost readout size + "
              "restore-toolbars origin (#159 v4.5.x, v4.5.3)",
        found="HAND-SEEDED 2026-08-30: absent from builders.json discovered "
              "(fails a --discover criterion), said out loud per the "
              "0x793810 precedent. Three patched sites live inside it.",
        geometry="push imm8 32 at 0x7EEF43 (kCostBoxHeightSite), push imm32 "
                 "128 at 0x7EEF54 (kCostBoxWidthSite), and the 6-byte "
                 "sub/push/push block at 0x7EE15A "
                 "(kRestoreToolbarsOriginSite - a block re-encode the "
                 "single-immediate schema may not hold; if the two pushes "
                 "census and the block does not, that is a MEASUREMENT, "
                 "0x76D3D0 precedent)."),
    0x79BDC0: dict(
        label="CHEAT DIALOG Init - entry field rect + clearance pair "
              "(v4.5.6/v4.5.7)",
        found="HAND-SEEDED 2026-08-30: absent from builders.json discovered, "
              "0x793810 precedent. The four rect immediates are ordinary "
              "C7 44 24 imm32 stores the model's schema can hold.",
        geometry="four mov [esp+d8],imm32 (l,t,r,b = 4,6,308,26) in the "
                 "32-byte window at 0x79BE2D (kCheatRectSite) and two "
                 "83 /0 08 adds inside the 39-byte window at 0x79BF63 "
                 "(kCheatClearSite - imm8 adds, may census as imm8 sites)."),
    0x79CFE0: dict(
        label="INTRO VIDEO SetArea + centring (#138 backlog, v2.93.0)",
        found="HAND-SEEDED 2026-08-30: absent from builders.json discovered. "
              "Four single-immediate sites (68 imm32 push / 2D imm32 sub "
              "eax) - if constants.py emits nothing for a video-init path "
              "the emu cannot drive, that is a MEASUREMENT, not a failure.",
        geometry="push 384/768 at 0x79D063/0x79D068 (SetArea w/h), "
                 "sub eax imm32 at 0x79D089/0x79D0A4 (centring "
                 "subtrahends) - kIntroVidSites."),
    0x7E8510: dict(
        label="MAYOR RATING BAR builder - bar length = rating*7px "
              "(kRatingImulSites, SKIPPED->resolved 2026-08-04)",
        found="HAND-SEEDED per crosscheck.py's kRatingImulSites skip "
              "(Phase 1b): the three `imul reg,reg,7` sites feed SetW "
              "(+0xCC, foreign-slot allowlisted) twice and a GZWinMoveTo "
              "coordinate once. The skip's unit worry is answered by "
              "OPACITY, not by guessing: the imuls record with their true "
              "encoding and value, under roles that claim no rect "
              "semantics ('w' from the documented SetW arg spec; 'pushed' "
              "for the coordinate refinement).",
        geometry="imul esi,esi,7 -> push -> SetW at 0x7E87B1; imul "
                 "ecx,ecx,7 -> push -> SetW at 0x7E89D7; imul ecx,ecx,7; "
                 "add ecx,edi; push -> [edx+0xE0] at 0x7E8A02."),
}


def disasm_owner(fm, start):
    return A.func_insns(start, fm.end(start))


def main():
    resume = "--resume" in sys.argv
    discover = "--discover" in sys.argv
    st = C.State()
    fm = C.FuncMap()
    A.resolve_local._fm = fm      # enables stack-local constant provenance
    outdir = C.ensure_work("census")
    edges = C.jload(os.path.join(C.WORK, "edges.json"))

    by_target = defaultdict(list)
    for site, tgt, kind in edges:
        if kind == "call":
            by_target[tgt].append(site)

    # ---------------- unit: one per primitive ----------------
    sites = {}
    for prim, spec in PRIMITIVES.items():
        unit = "prim_%X" % prim
        path = os.path.join(outdir, unit + ".json")
        if resume and st.done("census", unit) and os.path.exists(path):
            sites[prim] = C.jload(path)
            continue
        rows = []
        for site in sorted(by_target.get(prim, [])):
            owner = fm.owner(site)
            if owner is None:
                continue
            insns = disasm_owner(fm, owner)
            idx = None
            for k, ins in enumerate(insns):
                if ins.address == site:
                    idx = k
                    break
            if idx is None or insns[idx].mnemonic != "call":
                rows.append({"site": site, "owner": owner,
                             "status": "byte-scan only (not a real call)"})
                continue
            args, incomplete, probs = A.call_args_checked(insns, idx, spec, fm)
            rows.append({
                "site": site, "owner": owner, "status": "ok",
                "incomplete": incomplete, "validate": probs,
                "args": [{k: v for k, v in a.items()} for a in args],
            })
        C.jdump(path, rows)
        st.mark("census", unit, "done", primitive=spec["name"], sites=len(rows))
        sites[prim] = rows
        print("  %-12s %-10s %3d call sites" % ("prim_%X" % prim, spec["name"], len(rows)))

    # ---------------- unit: vtable geometry ops inside owners ----------------
    owners = set()
    for prim, rows in sites.items():
        for r in rows:
            owners.add(r["owner"])
    # Promoted builders (see EXTRA_BUILDERS): these call no named primitive,
    # so `by_target` can never reach them. They are censused from here on
    # exactly like any other owner.
    owners |= set(EXTRA_BUILDERS)

    # v2 = the geomextra recorders (rect stores / measure-relative /
    # foreign slots) are part of this unit now. The name is bumped so a
    # --resume over a pre-#96 manifest cannot serve the old, thinner rows.
    #
    # v3 (2026-08-04, #57 deferral): the unit key now folds in a DIGEST OF
    # THE OWNER SET. Promoting a builder into EXTRA_BUILDERS used to leave
    # this unit marked done, so `--resume` served the pre-promotion rows and
    # the new owner came out with vtGeom=[] - which is exactly what happened
    # to 0x76D3D0: its `call [ebx+0xDC]` SetArea at 0x76E168 was VISIBLE to
    # the scan (verified by replaying the loop by hand) but the stale unit
    # file was served instead, and constants.py then honestly reported
    # "0 geometry constants" from the empty rows. A model regeneration that
    # can silently exclude the one owner it was run FOR is the same failure
    # class as a stale generated artifact (#58). Any change to the owner set
    # now changes the unit name, so resume can never serve rows computed for
    # a different set. Recorder D/E rows (memberimm.json) ride the same unit.
    odig = "%08x" % (sum(owners) & 0xFFFFFFFF)
    unit = "vtgeom3_%d_%s" % (len(owners), odig)
    vpath = os.path.join(outdir, "vtgeom3.json")
    mpath = os.path.join(outdir, "measurerel.json")
    mipath = os.path.join(outdir, "memberimm.json")
    if resume and st.done("census", unit) and os.path.exists(vpath):
        vt = C.jload(vpath)
        mrel = C.jload(mpath) or {}
        mimm = C.jload(mipath) or {}
    else:
        vt, mrel, mimm = {}, {}, {}
        nrect, nrectfail, nforeign = 0, 0, 0
        for o in sorted(owners):
            insns = disasm_owner(fm, o)
            rows = []
            for k, ins in enumerate(insns):
                if ins.mnemonic != "call" or ins.op_str.startswith("0x"):
                    continue
                m = re.search(r"\+ (0x[0-9a-f]+)\]", ins.op_str)
                if not m:
                    continue
                slot = int(m.group(1), 0)
                if slot not in VT_NAME:
                    continue
                nargs = A.VT_ARITY[slot]
                args, inc = A.call_args(insns, k, nargs, fm)
                row = {"site": ins.address, "op": VT_NAME[slot],
                       "slot": slot, "incomplete": inc, "args": args}
                if slot == G.RECT_SLOT:
                    # SetArea(const Rect*): the ARG IS A POINTER. Never
                    # record it as geometry (that is the phantom-constant
                    # trap in sdkgaps-01.md blind spot 2). Record only the
                    # four member stores, and only if all four resolve.
                    mem, why = G.resolve_rect(insns, k, fm)
                    row["rectMembers"] = {r_: v for r_, v in mem.items()}
                    row["rectUnresolved"] = why
                    if mem:
                        nrect += 1
                    else:
                        nrectfail += 1
                rows.append(row)
            fr = G.foreign_slot_calls(insns, o, fm)
            nforeign += len(fr)
            rows.extend(fr)
            if rows:
                vt[str(o)] = rows
            mr = G.measure_relative(insns, fm)
            if mr:
                mrel[str(o)] = mr
            # Recorders D + E (allowlisted owners only; see geomextra.py).
            mi = G.member_imm_stores(insns, o, fm) \
                + G.stack_pair_diff_imms(insns, o, fm)
            if mi:
                mimm[str(o)] = mi
        C.jdump(vpath, vt)
        C.jdump(mpath, mrel)
        C.jdump(mipath, mimm)
        st.mark("census", unit, "done", owners=len(vt), rectsResolved=nrect,
                rectsUnresolved=nrectfail, foreignSlotCalls=nforeign)
        print("  rect stores  %d SetArea(Rect*) fully resolved, %d left "
              "unrecorded (partial)" % (nrect, nrectfail))
        print("  foreign slot %d SetItemMetrics call(s) in the %d allowlisted "
              "owner(s)" % (nforeign, len(G.FOREIGN_SLOT_OWNERS)))
    print("  vtgeom       %d owner functions carry SetSize/SetArea/SetPosition" % len(vt))
    print("  measure-rel  %d owner functions apply an immediate to GetW/GetH"
          % len(mrel))
    print("  member-imm   %d allowlisted owner(s) carry member-store / "
          "pair-diff geometry (recorders D+E)" % len(mimm))

    # ---------------- unit: identification ----------------
    # Same owner-set digest as vtgeom3 (same staleness bug, same fix).
    unit = "ident3_%d_%s" % (len(owners), odig)
    ipath = os.path.join(outdir, "ident2.json")
    if resume and st.done("census", unit) and os.path.exists(ipath):
        ident = C.jload(ipath)
    else:
        ident = {}
        for o in sorted(owners):
            insns = disasm_owner(fm, o)
            childids, arts, ltexts, styles, bigimm = [], [], [], [], Counter()
            for k, ins in enumerate(insns):
                if ins.mnemonic == "call" and not ins.op_str.startswith("0x"):
                    m = re.search(r"\+ (0x[0-9a-f]+)\]", ins.op_str)
                    slot = int(m.group(1), 0) if m else None
                    if slot in (0x8C, 0x100):
                        a, _ = A.call_args(insns, k, 1, fm)
                        if a and a[0].get("value") is not None:
                            childids.append(a[0]["value"])
                if ins.mnemonic == "push" and ins.bytes[0] == 0x68:
                    v = int.from_bytes(ins.bytes[1:5], "little")
                    if (0x14015500 <= v <= 0x140155FF) or \
                       (0x2BFEB000 <= v <= 0x2BFEB0FF) or v in ART_FAMILY:
                        arts.append(v)
                    elif 0x14400000 <= v <= 0x144FFFFF:
                        ltexts.append(v)
                    elif (v & 0xFF000000) in (0x4A000000, 0xEA000000):
                        styles.append(v)
                    if v > 0xFFFF:
                        bigimm[v] += 1
            fams = sorted(set(ART_FAMILY[a] for a in arts if a in ART_FAMILY))
            ident[str(o)] = {
                "childIds": sorted(set(childids)),
                "artInstances": sorted(set(arts)),
                "artFamilies": fams,
                "ltextTgis": sorted(set(ltexts)),
                "fontStyles": sorted(set(styles)),
                "label": KNOWN_BUILDERS.get(o) or
                (EXTRA_BUILDERS[o]["label"] if o in EXTRA_BUILDERS else None),
            }
        C.jdump(ipath, ident)
        st.mark("census", unit, "done", owners=len(ident))

    # ---------------- optional discovery of unnamed primitives -------------
    disc = {}
    if discover:
        unit = "discover"
        dpath = os.path.join(outdir, "discover.json")
        if resume and st.done("census", unit) and os.path.exists(dpath):
            disc = C.jload(dpath)
        else:
            ncall = Counter()
            for site, tgt, kind in edges:
                if kind == "call":
                    ncall[tgt] += 1
            cand = {}
            for start in fm.starts:
                if fm.meta[start]["callers"] < 2:
                    continue
                hi = fm.end(start)
                if hi - start > 0x1200:
                    continue
                body = C.rd(start, hi - start)
                # call [reg+0xD4/0xD8/0xDC/0xE0] - see RECT_CALL_PATS above for
                # the encoding and for why this is generated rather than listed.
                hit = [s for s in RECT_CALL_PATS if s in body]
                if hit and start not in PRIMITIVES:
                    cand[str(start)] = {"callers": ncall[start],
                                        "size": hi - start,
                                        "arity": A.arity_of(start, fm)}
            disc = cand
            C.jdump(dpath, disc)
            st.mark("census", unit, "done", candidates=len(disc))
        print("  discover     %d unnamed rect-driving helpers with >=2 callers" % len(disc))

    # ---------------- assemble builders.json ----------------
    per_owner = defaultdict(lambda: defaultdict(list))
    for prim, rows in sites.items():
        for r in rows:
            per_owner[r["owner"]][prim].append(r)

    out = {"exe": C.EXE_PROVENANCE, "imageBase": C.IMAGE_BASE,
           "primitives": {("0x%X" % k): v for k, v in PRIMITIVES.items()},
           "promotedBuilders": {("0x%X" % k): v
                                for k, v in EXTRA_BUILDERS.items()},
           "foreignSlots": {("0x%X" % k): v
                            for k, v in G.FOREIGN_SLOTS.items()},
           "foreignSlotOwners": {("0x%X" % k): v
                                 for k, v in G.FOREIGN_SLOT_OWNERS.items()},
           "builders": {}, "discovered": disc}
    for o in sorted(set(per_owner) | set(EXTRA_BUILDERS)):
        idd = ident.get(str(o), {})
        b = {
            "va": "0x%X" % o,
            "end": "0x%X" % fm.end(o),
            "size": fm.end(o) - o,
            "label": idd.get("label"),
            "callers": fm.meta[o]["callers"],
            "promoted": EXTRA_BUILDERS.get(o),
            "identification": idd,
            "primitiveCalls": {},
            "vtGeom": vt.get(str(o), []),
            "measureRel": mrel.get(str(o), []),
            "memberImm": mimm.get(str(o), []),
        }
        for prim, rows in per_owner.get(o, {}).items():
            b["primitiveCalls"][PRIMITIVES[prim]["name"]] = [
                {"site": "0x%X" % r["site"],
                 "incomplete": r.get("incomplete"),
                 "args": r.get("args", [])} for r in rows]
        out["builders"]["0x%X" % o] = b
    C.jdump(os.path.join(C.HERE, "builders.json"), out)
    st.mark("census", "assemble", "done", builders=len(out["builders"]))
    print("builders.json: %d owner functions, %d primitive call sites"
          % (len(out["builders"]), sum(len(v) for v in sites.values())))

    write_md(out, fm)
    st.mark("census", "md", "done")


MD_HEAD = """# BUILDER CENSUS - SimCity 4.exe 1.1.641.0 Steam (STAGE 1)

> GENERATED by `tools\\uimap\\census.py`. Do not hand-edit; re-run instead.
> `python census.py --resume --discover`
>
> This is stage 1 of the offline UI model (`METHOD.md` 6). It answers
> *"which function builds this window, and where exactly does it create
> each child?"* without launching the game. **The live dump is still the
> authority** (`METHOD.md` standing rule); everything below is read out of
> the binary and every claim carries a VA.

## 0. Mapping, and how the sites were proven

`ImageBase 0x400000`. The PE section table gives `.text` VA `0x407000`,
raw `0x7000`, so **file offset = VA - 0x400000** for `.text`, `.rdata`
and `.data` alike (asserted in `common.py`, not assumed).

Every call site below is **double-proven**:

1. found by a byte-level scan of all of `.text` for `E8 rel32`
   (`scan_text.py`, 104 x 64 KB shards, 114,521 call/jmp edges) - a byte
   scan cannot miss a site because it followed the wrong path; and
2. confirmed to decode as a real `call` when its owning function is
   disassembled linearly from the function's own start
   (`build_funcs.py` -> 32,113 functions).

Arguments are recovered by walking back over the push run, skipping whole
balanced sub-calls (a direct call's arity comes from its own `ret N`).
Each extraction is then **self-checked**: the text factories end with a
font-style GUID and an R/G/B triple, so a walk that consumed one push too
many or too few stops looking like one. **189+ sites, 0 incomplete,
0 validation failures.**
"""


def write_md(out, fm):
    L = [MD_HEAD, "", "## 1. Primitive signatures (arity proven by `ret N`)", "",
         "| VA | name | args | geometry args | callers | what it does |",
         "|---|---|---|---|---|---|"]
    for va, spec in sorted(PRIMITIVES.items()):
        geom = ", ".join("%s=arg%d" % (k, v + 1) for k, v in
                         sorted(spec["geom"].items(), key=lambda kv: kv[1]))
        L.append("| `0x%X` | **%s** | %d | %s | %d | %s |" % (
            va, spec["name"], spec["arity"], geom or "-",
            fm.meta[va]["callers"], spec["note"].replace("\n", " ")))
    L += ["", "Vtable geometry slots used inside the builders (proven by "
          "reading the callees):", "",
          "| slot | call | args |", "|---|---|---|",
          "| `+0x8C` | `GetChildWindowFromID(id)` | 1 - the strongest "
          "identification signal |",
          "| `+0xD4` | `SetSize(w,h)` | 2 (`push h; push w`) |",
          "| `+0xD8` | `SetArea(const Rect*)` | 1 |",
          "| `+0xDC` | `SetArea(l,t,r,b)` | 4 |",
          "| `+0xE0` | `SetPosition(x,y)` | 2 (`push y; push x`) |",
          "| `+0x100` | `SetID(id)` | 1 |", ""]

    L += ["## 2. The census, grouped by owning function", ""]
    for va in sorted(out["builders"], key=lambda x: int(x, 16)):
        d = out["builders"][va]
        idd = d["identification"]
        L.append("### `%s` - `%s` .. `%s`  (%d bytes)" %
                 (va, va, d["end"], d["size"]))
        L.append("")
        L.append("**%s**" % (d["label"] or "UNIDENTIFIED - see 4"))
        L.append("")
        # A promoted builder was seeded by hand, not reached by by_target.
        # Say so in the generated doc - a reader must be able to tell which
        # entries the scan FOUND from the ones it was TOLD about.
        if d.get("promoted"):
            p = d["promoted"]
            L.append("> **PROMOTED BUILDER** (calls no named primitive, so "
                     "`by_target` can never reach it).")
            L.append("> How it was found: %s" % p["found"])
            L.append("> Geometry: %s" % p["geometry"])
            L.append("")
        counts = ", ".join("%s x%d" % (k, len(v))
                           for k, v in sorted(d["primitiveCalls"].items()))
        L.append("- creates: %s" % (counts or "-"))
        if d["vtGeom"]:
            ops = {}
            for r in d["vtGeom"]:
                ops[r["op"]] = ops.get(r["op"], 0) + 1
            L.append("- direct rect calls: %s" %
                     ", ".join("%s x%d" % (k, v) for k, v in sorted(ops.items())))
        if idd.get("artFamilies"):
            L.append("- art family: %s" % "; ".join(idd["artFamilies"]))
        if idd.get("artInstances"):
            L.append("- art instances: %s" %
                     " ".join("`0x%08X`" % a for a in idd["artInstances"][:12]))
        if idd.get("childIds"):
            L.append("- window ids touched (`GetChildWindowFromID`/`SetID`): %s"
                     % " ".join("`0x%X`" % i for i in idd["childIds"][:16]))
        if idd.get("ltextTgis"):
            L.append("- caption LTEXTs: %s" %
                     " ".join("`0x%08X`" % i for i in idd["ltextTgis"][:10]))
        L.append("")
        for pname in sorted(d["primitiveCalls"]):
            rows = d["primitiveCalls"][pname]
            spec = next(v for v in out["primitives"].values()
                        if v["name"] == pname)
            L.append("<details><summary>%s - %d call site(s)</summary>" %
                     (pname, len(rows)))
            L.append("")
            L.append("| call | " + " | ".join(spec["args"]) + " |")
            L.append("|---|" + "---|" * len(spec["args"]))
            for r in rows:
                cells = []
                for i in range(len(spec["args"])):
                    if i >= len(r["args"]):
                        cells.append("-")
                        continue
                    a = r["args"][i]
                    if a.get("value") is not None:
                        cells.append("`%d` @`0x%X`" % (a["value"], a["site"]))
                    elif a.get("src") and a["src"].get("value") is not None:
                        cells.append("`%s %d` @`0x%X`" % (
                            a["src"]["enc"], a["src"]["value"], a["src"]["site"]))
                    else:
                        cells.append("_reg_")
                L.append("| `%s` | %s |" % (r["site"], " | ".join(cells)))
            L.append("")
            L.append("</details>")
            L.append("")

    L += ["## 3. Candidate primitives NOT yet named", "",
          "Functions with >=2 callers that drive a window rect "
          "(`call [r+0xD4/0xD8/0xDC/0xE0]`) and are not in the table above. "
          "These are the seeds for extending the model past the budget "
          "family (god flyouts, mayor mode, data views).", "",
          "| VA | callers | size | arity |", "|---|---|---|---|"]
    disc = out.get("discovered") or {}
    for k, v in sorted(disc.items(), key=lambda kv: -kv[1]["callers"])[:40]:
        L.append("| `0x%X` | %d | %d | %s |" %
                 (int(k), v["callers"], v["size"], v["arity"]))
    L += ["", "(full list in `builders.json` -> `discovered`)", "",
          "> ### v2.38.2 - THIS SCAN WAS BLIND TO 18% OF ITS OWN TARGET",
          "> The hand-written pattern tuple omitted **`0xD8` (SetAreaRect) for "
          "every register** and **`ebp` entirely**, while the comment above it "
          "claimed `d4/d8/dc/e0` coverage. Measured against the exe: **180 of "
          "1024** window-rect call sites were unscannable (73 at `edx+0xD8` "
          "alone). The patterns are now GENERATED from `VT_NAME` x the register "
          "table (`RECT_CALL_PATS`), so the scan cannot drift from its "
          "documentation again.",
          ">",
          "> The old patterns were also only 3 bytes, so `call [reg+0x0001D4]` "
          "matched as if it were `+0xD4`. The scan is now the full 6-byte form.",
          ">",
          "> **Result: 101 -> 116 discovered (+20 real, -5 false positives).** "
          "The 20 include `sub_7EAEB0` (the sub-flyout builder fixed by hand in "
          "v2.36.0), `sub_7A04F0` (the Data Views legend re-lay, v2.37.0) and "
          "`sub_78DFF0` (the generic message-box builder) - **builders we had "
          "already shipped fixes for and that this model had never once "
          "seen.** Treat any pre-v2.38.2 \"the offline model found nothing\" "
          "null as worthless.", ""]

    with open(os.path.join(C.HERE, "BUILDER-CENSUS.md"), "w",
              encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print("BUILDER-CENSUS.md written")


if __name__ == "__main__":
    main()
