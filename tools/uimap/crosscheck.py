"""crosscheck.py - does the GENERATED map reproduce the HAND-ENUMERATED one?

Reads src\\CodePatches.cpp (READ ONLY - never written) and compares its
site tables against constants.json.

    MISS  = a site CodePatches patches that the generated map does not know
            about.  Every miss is a hole in the model and must be explained.
    EXTRA = a geometry constant the model found that CodePatches does NOT
            patch.  Extras are the whole point of the exercise: missed
            encodings and dead twins are the two costliest bug classes in
            this project (laws 15/16).

Matching is by BYTE COVERAGE, not by equal addresses: CodePatches writes a
run of bytes from one VA (e.g. 7 bytes for `push h; push w`), so a model
site anywhere inside that run counts as covered.

EXIT CODE: 0 only when MISSES == 0. Extras do not fail the run (an extra is
an unpatched constant, not a hole in the model). Before 2026-08-02 this tool
printed the misses and exited 0, so nothing that called it could tell a clean
model from a 14-hole one.

Usage:  python crosscheck.py [--md]

==========================================================================
FORENSIC RECORD  (2026-08-03 afternoon)  -  why #96's GREEN stopped
reproducing, and what the earlier report actually said
==========================================================================
A workflow reported this gate GREEN "with 3 named skips" this morning, and
by the afternoon it exited 1 with 8 misses. Both are true. Neither report
was wrong, and nothing here was narrowed to hide anything. The measurements:

  1. "3 named skips" and "9 SKIPPED" are the SAME FACT in two units.
     SKIPPED names 3 TABLES holding 9 ENTRIES. There is one skip set, not
     two, and it has not changed. Whoever reads a future report of this
     tool should note which unit it is quoting.

  2. The morning GREEN reproduces EXACTLY. Replayed by running this file
     unmodified against a copy of CodePatches.cpp with the two #57 tables
     textually removed:
         251 checked, 251 passed, 9 skipped, exit 0
     against today's live 259/251/9, exit 1. So it did pass; the scope was
     never narrowed to get there.

  3. WHAT BROKE IT is a file-age race, measured from mtimes:
         tools\\uimap\\constants.json   2026-08-03 09:43:44  <- the model
         src\\CodePatches.cpp           2026-08-03 11:36:12  <- the patch list
     The #57 Graphs-legend fix (v2.55.0) added kGraphLegendImmSites (5) and
     kGraphLegendBlocks (3) at 11:36, TWO HOURS after the model was last
     generated. 8 new patched sites, all in sub_76D3D0, none of which the
     model has ever been rebuilt to see. checked 251 -> 259; misses 0 -> 8.

  4. THE 8 NEW ENTRIES AND THE 8 MISSES ARE THE SAME 8, exactly. Any report
     naming 0x78B9C3 / 0x78B9E4 / 0x78B9E6 / 0x78BA91 / 0x78BA93 / 0x78BACE
     / 0x78BAEA (budget-ordinance popup) or 0x7E72A4/A6/A8 (first-level
     flyout builder) as the FAILURES has misread the output: those are
     EXTRAS, not misses. Extras never fail this run, and 0x7E72A4/A6/A8 are
     extras BY DESIGN - builders.json -> promotedBuilders 0x7E7270 was
     censused precisely so the unpatched twins would show up there. The
     miss list is, and was, 0x76E0E8 / 0x76E145 / 0x76E1D6 / 0x76E233 /
     0x76E239 / 0x76E23C / 0x76E2AF / 0x76E2C8, owner sub_76D3D0.

==========================================================================
THE 8 #57 MISSES ARE DEFERRED, NOT PASSED  (2026-08-03)
==========================================================================
Classification of the 8, per the offline-gate law: they are NOT a scope bug
(this gate should absolutely ask whether the model covers a patched geometry
family) and NOT a real gap this file can close (see below). They are
UNRESOLVABLE HERE, so they become a third, explicitly named bucket -
DEFERRED - which is counted apart from passes and apart from SKIPPED, and
which CANNOT rot, because four measured guards revoke it automatically:

  G1  model age.  Deferral is legal only while constants.json is OLDER than
      CodePatches.cpp. The moment someone regenerates the model, the "the
      model predates the patch" excuse is dead and the entries become
      misses again.
  G2  owner not promoted.  Deferral is legal only while the owning function
      is absent from builders.json -> `builders`. Once it is censused, an
      uncovered site is a real hole, not an age problem.
  G3  POSITIVE CONTROL (this is the one that makes the null a fact).  The
      owner must be present in builders.json -> `discovered`, which proves
      the census's discovery pass CAN see it and that promotion is the only
      missing step. MEASURED: builders.json.discovered["7787472"] =
      {callers: 4, size: 4176, arity: 1}; sub_76D3D0 met both discovery
      criteria (>=2 callers, <=0x1200 bytes, contains a rect-driving
      `call [reg+0xD4..0xE0]`). This is therefore a MEASURED null, not a
      structural one. If the control ever fails, the entries are reported
      as MISSES and the run fails - a deferral with no positive control is
      exactly the lie these headers exist to prevent.
  G4  address whitelist.  Only the eight VAs listed in DEFERRED are
      deferred. A ninth address added to either table later is adjudicated
      normally and will fail until the model learns it.

WHY THIS FILE CANNOT CLOSE THEM (option (a) was attempted and rejected)
  The model reaches a function only through census.py's EXTRA_BUILDERS. So
  clearing these needs an edit to census.py plus a regeneration that
  REWRITES builders.json, constants.json, BUILDER-CENSUS.md and
  CONSTANT-MAP.md. Two reasons not to do it from inside a crosscheck:
  (i) this header has said since #96 that those steps are run deliberately,
  never as a side effect of a gate; (ii) other agents hold this un-versioned
  tree concurrently. And hand-writing the eight rows into constants.json is
  strictly forbidden: it would copy the answer out of CodePatches.cpp and
  destroy the independence that is the only reason this gate's agreement
  means anything.

THE EXACT PROCEDURE THAT CLEARS ALL 8 (one edit, two commands)
  1. census.py EXTRA_BUILDERS - add, alongside 0x7A04F0 / 0x7EAEB0:
         0x76D3D0: dict(
             label="GRAPHS panel builder - legend column born at scale "
                   "(v2.55.0 #57)",
             found="--discover (4 callers, 4176 bytes, rect-driving)",
             geometry="legend column immediates at 0x76E233/239/23C/2AF/2C8 "
                      "and three rebuilt blocks at 0x76E0E8/145/1D6"),
  2. python census.py    --resume --discover
  3. python constants.py --resume --factor 2.0
  Then re-run this file: G1 and G2 both flip, the deferral is revoked
  automatically, and the 8 are adjudicated for real. If constants.py still
  emits nothing for them after that, THAT is a genuine model hole in the
  recorder set (the three blocks in particular are 25/41/42-byte instruction
  replacements with relocated rel32s, and constants.json's `encodings` table
  models single immediates only - it has no schema for a rebuilt block).
  That outcome is a finding, and this gate will report it as 8 misses rather
  than absorb it.

==========================================================================
THE 12 MISSES ARE CLOSED  (task #96, 2026-08-03)  -  0 MISSES, 9 SKIPPED
==========================================================================
Read the block below this one for the original diagnosis; it is kept
because it is the measurement that produced the fix. What changed:

  MISSES 12 -> 0, exit 1 -> 0.  Sites in the model 292 -> 307.

None of it was achieved by deleting a check or widening a matcher. Three
recorders were added (tools\\uimap\\geomextra.py) and four functions were
promoted into the census (census.py EXTRA_BUILDERS):

  8 misses  sub_7A04F0 Data Views legend - SetArea(const Rect*) at 0x7A082C
            and 0x7A0955. The patched constants are the four dword stores
            into the stack rect the call's pointer argument points at.
            geomextra.resolve_rect() walks them back with esp tracking and
            emits NOTHING unless all four resolve. It never reads the
            pointer itself (that is the phantom-constant trap).
  4 of those 8 are ALSO reached a second, independent way: an immediate
            applied to a GetW/GetH (cIGZWin vt+0xA4/+0xA8) return value.
            Both walks agree on enc/value/immOff at all four; the records
            are collapsed to one per instruction by constants.collapse_by_va
            and carry `alsoDerivedBy`. Independent failure modes, so this
            is corroboration and not two blind instruments.
  3 misses  sub_7EAEB0 sub-flyout provider - SetItemMetrics(44,44,5) on
            vt+0x30 of class 0xAB6D28. NOT a cIGZWin slot, so recognition
            is gated on an owner allowlist - see SCOPE below.
  1 miss    sub_793810 advice row - `call [edx+0xA4]` then `sub esi,0x3D`,
            the W-61 right reserve. Measure-relative rule.

INDEPENDENCE OF THE GATE. Nothing added to the model was copied out of
CodePatches.cpp. Only FUNCTION addresses were hand-seeded (the same move
as naming a primitive); every site, value, encoding and immOff was derived
from the exe. The agreement is therefore real: all eight Data Views immOff
values recovered here (7/2/1/3, 4/2/1/3) match the hand table byte for
byte without having seen it.

SCOPE NARROWINGS - stated loudly, per the offline-gate law
  1. vt+0x30 = SetItemMetrics is recognised ONLY inside the two owners in
     geomextra.FOREIGN_SLOT_OWNERS. MEASURED reason: the 12 pre-existing
     census builders contain 14 `call [reg+0x30]` sites, none of them this
     API - slot 0x30 is not reserved, and a blanket rule would FABRICATE
     14 constants. Any future owner must be added with its receiver-class
     evidence.
  2. Nine CodePatches entries in three tables are still not adjudicated by
     this gate. They used to be dropped silently under OUT_OF_SCOPE; they
     are now printed as SKIPPED with the one measurement each needs, and
     they are NOT counted as passes.

==========================================================================
WHY THE 14 MISSES EXIST  (measured 2026-08-02, not inferred)  [HISTORICAL]
==========================================================================
The starting hypothesis was "the generated model simply predates the newer
patch families". The dates support it - but they are NOT the whole story,
and two of the three sub-causes need a different fix:

    tools\\uimap\\constants.json   2026-07-30 18:15   <- the model
    tools\\uimap\\builders.json    2026-07-31 15:19   <- the census it came
                                                         from is NEWER than
                                                         the model built on it
    src\\CodePatches.cpp           2026-07-31 21:44   <- the patch list

Every miss was resolved to its owning function (funcs.json) and checked
against builders.json. Encoding is NOT the blocker anywhere: lea_disp8,
add_imm32, mov_imm32, sub_imm8 and push_imm8 are all already in
constants.json's `encodings` table. The 14 split three ways:

(1) 2 misses that are NOT model holes - they were this tool's own blind spot
    0x779548  lea edx,[ecx+0x0E]   Slider height 14   (inside sub_7794E0)
    0x779927  lea edx,[ecx+0x0F]   Combo  height 15   (inside sub_7798C0)
    Both are immediates in a PRIMITIVE's own body, not at a call site, so
    constants.py records them in constants.json -> `helperConstants`
    (constants.py:61) instead of -> `sites`. crosscheck built its coverage
    map from `sites` alone and therefore called two things holes that the
    model has known all along. FIXED here: helperConstants now counts as
    coverage. 14 -> 12.

(2) 11 misses whose owner IS in the census but only as a CANDIDATE
    0x7A04F0  the Data Views legend re-lay  -> 8 kDataViewLegend* sites
    0x7EAEB0  the sub-flyout provider       -> 3 kSubFlyoutProvider sites
    Measured: both appear in builders.json -> `discovered` (13 and 7 callers
    respectively), so census.py --discover DID see them. But constants.py
    walks only b["builders"] (constants.py:150) - the 12 owners that call a
    named primitive - and neither function calls ANY of the 13 census
    primitives (measured: 0 primitive calls each; they drive rects directly
    via `call [eax+0xD8]`). A discovered candidate never becomes a site, so
    re-running constants.py alone will not clear these.

(3) 1 miss whose owner the census cannot reach at all
    0x79388F  sub esi,0x3D  (inside sub_793810, the advice row)
    In neither `builders` nor `discovered`. Measured on sub_793810: 0 calls
    to any census primitive, 0 `call [reg+0xD4/D8/DC/E0]`, and 0 direct
    E8-rel32 callers - it is entered through a vtable. It fails BOTH
    discovery criteria (rect-driving AND >=2 callers), so no run of the
    census as currently designed will ever list it.

WHAT THE OPERATOR MUST RUN TO CLEAR THE REMAINING 12
    Nothing this tool can do, and NOT just a regeneration: the three owner
    functions must first be made first-class census subjects, because they
    call no named primitive.
      1. Add 0x7A04F0, 0x7EAEB0 and 0x793810 to census.py's builder set
         (0x793810 must be added by hand - discovery cannot find it).
      2. python census.py --resume --discover        (rewrites builders.json,
                                                      BUILDER-CENSUS.md)
      3. python constants.py --resume --factor 2.0   (rewrites constants.json,
                                                      CONSTANT-MAP.md)
    Steps 2 and 3 REWRITE large generated files - run them deliberately, never
    as a side effect of a crosscheck. Until then this tool exits 1, and that
    is the intended pressure: 12 patched families are outside the offline
    model, so the model cannot be used to reason about them.
"""
import os
import re
import sys

import common as C

CP = os.path.abspath(os.path.join(
    C.HERE, "..", "..", "src", "CodePatches.cpp"))

# table name -> bytes written per entry (from CodePatches.cpp's own writes)
TABLE_LEN = {
    "kBudgetBtnSizeSites": 7,
    "kBudgetBtnXSites": 6,
    "kBudgetBtnYSites": 3,
    "kOrdinanceInsetSites": 2,     # writes 3, but byte 3 is the pinning ctx
    "kDeptImm8Sites": 2,
    "kDeptImm32Sites": 5,
    "kBudgetSubImm8Sites": 3,
    "kMasterNotchSites": 6,
    "kBizBoxSizeSites": 7,
    "kBizBoxCloseX": 5,
    "kBizBoxCloseY": 2,
    "kRatingImulSites": 3,
    "kTipWrapSites": 5,
    "kPopupStyleRetargets": 5,
    # #57 (v2.55.0). Both deliberately UNDER-state the run so coverage is
    # never over-claimed: a too-wide run would silently swallow a model site
    # as "covered" and delete it from the EXTRAS report.
    "kGraphLegendImmSites": 3,     # writes exactly 3 bytes (opcode+modrm+imm8)
    # 2026-08-04: was the flat 25 ("the SMALLEST is used"). That was safe
    # under-statement while the table was DEFERRED, but as an adjudicated
    # entry it misgrades: block 3's only geometry imm (`sub ebx,0x5a` at
    # 0x76E1F8) sits at offset 0x22 - inside the real 42-byte block, outside
    # a 25-byte window - so a model that genuinely derives it would still be
    # scored a MISS. Per-entry lengths are the PATCH's true byte extents
    # (25/41/42, the same numbers gate_graphlegend_leftanchor.py length-
    # checks); they describe the write, not the geometry, so recording them
    # here copies no answer out of CodePatches.
    "kGraphLegendBlocks": {0x76E0E8: 25, 0x76E145: 41, 0x76E1D6: 42},
}


def entry_len(name, addr):
    """Byte length of one table entry - flat int, or per-VA dict (#57 blocks)."""
    n = TABLE_LEN.get(name, 4)
    if isinstance(n, dict):
        return n.get(addr, min(n.values()))
    return n
# Tables this gate does NOT adjudicate, and the single thing that would let
# it. Until 2026-08-03 these were dropped silently, which is the failure the
# offline-gate law names: a gate is only as honest as its SCOPE. They are now
# printed as SKIPPED, counted apart from the passes, and never counted as
# passes. Each reason names ONE action - the same promotion that closed the
# 12 misses would close these too, so none of them is unresolvable in
# principle; they are simply not done.
# 2026-08-04 (Phase 1 close-out): the three-entry SKIPPED set is resolved.
#   * kRatingImulSites LEFT this table - it is ADJUDICATED now. 0x7E8510 is
#     promoted into census.EXTRA_BUILDERS; the two SetW imuls record through
#     the foreign-slot recorder (slot 0xCC allowlisted for this owner only -
#     SC4-UI-ENGINE.md:249 names the slot, geomextra.FOREIGN_SLOT_OWNERS
#     carries the receiver proof) and the third through recorder D's push
#     terminal. The old skip's unit worry ("the value is a RATIO") is
#     answered by opacity: the records carry the true encoding and value
#     under roles that claim no rect semantics.
#   * The two remaining entries are PERMANENT, each with the MEASURED reason
#     and the falsifier that would re-open it. A permanent classification
#     with a stated reason is the plan's accepted alternative to coverage;
#     an open-ended "TO RESOLVE" skip is not.
PERMANENT_OUT_OF_SCOPE = {
    "_V274_BLOCK_REENCODE_DOC": (
        "PERMANENT - EQUAL-LENGTH BLOCK RE-ENCODES, adjudicated by their own "
        "byte gates, not by this constant model. v2.74.0 (2026-08-04): "
        "kOrdinanceNameXBlocks re-encodes two 43-byte windows at "
        "0x77CBFC/0x77D0B9 so the ordinance name-label x can carry imm32 204 "
        "at f=3 (the push-imm8 ceiling clamped it to 127 = the eye-icon "
        "overlap the user reported). kGlRow0Site re-encodes the Graphs "
        "legend ROW0_TOP mov [esp+0x18],imm32 at 0x76DE79. Neither is a "
        "single scaled immediate the model's schema can hold - each is a "
        "verified stock-window swap whose OWN gate disassembles the "
        "replacement back and asserts length/ESP/branch-targets: "
        "tools/uimap/emu/gate_ordinance_namex.py and "
        "gate_graphlegend_leftanchor.py. FALSIFIER: either gate red, or a "
        "capture showing the re-encoded site holding a value its gate did "
        "not certify."),
    "_V274_HOOK_VA_DOC": (
        "PERMANENT - CONTROL FLOW, not geometry (the kPopupStyleRetargets "
        "precedent). kRatingUpdateVa/kDeclineStepVa are the MinHook target "
        "VAs for the #130 decline-arrow anchor hook (v2.74.0, log-only by "
        "default). A hook VA holds no rect, size or position. FALSIFIER: a "
        "geometry immediate appearing at either VA."),
    "kTipWrapSites": (
        "PERMANENT - not a window-rect constant. MEASURED from the stock "
        "exe (2026-08-04): both sites are `push 0xfa` feeding "
        "`call [edx+0x1C]` on an object loaded from [esi+0x134]/[esi+0x138] "
        "inside the tip layer's Plot override sub_798710 - a text-measure "
        "call on the HTML engine, not any cIGZWin slot (the cIGZWin rect "
        "family lives at +0xC0..+0xE0; +0x1C on a non-window object is "
        "outside the model's domain by construction). The tip WINDOW's size "
        "is computed downstream from the measure result with no immediate, "
        "so there is nothing for a constant model to hold. FALSIFIER: a "
        "live-log trace showing 250 (or the patched 500) arriving as a "
        "SetSize/SetW immediate on a window would re-open this as a "
        "promotion candidate."),
    "_X8_BAKE_FAMILY_DOC": (
        "PERMANENT - a JUMP-TABLE DISPATCH, not a window-rect constant. "
        "#121 (v2.71.0): the minimap terrain bake picks its per-tile blitter "
        "through `lea ecx,[edx+2]; cmp ecx,4; ja skip; jmp [ecx*4+0x7A8628]` "
        "at 0x7A8560 - an UNSIGNED bound that excludes zoom -3, which is the "
        "zoom our resized Data Views map reaches on a small city tile. We "
        "re-point that one dispatch at a 6-entry DLL table (entry 0 = an x8 "
        "blitter, entries 1..5 = the game's own stubs unchanged). None of "
        "the four sites holds a rect, a size or a position: the dispatch is "
        "control flow, kX8StubBlock/kX8TableVa are VERIFY-ONLY (never "
        "written - they exist so we refuse to patch a build whose blitter "
        "set differs), and kX8TailVa is a jump target. constants.json holds "
        "geometry roles only, so there is nothing here for it to represent - "
        "the same domain boundary as kPopupStyleRetargets above. "
        "ADJUDICATED ELSEWHERE, NOT UNCHECKED: _tests\\Test-MiniMapX8Bake.py "
        "asserts all 15 dispatch bytes, the 0x21-byte stub block, the "
        "blitter ORDER, the 5 table dwords, that the replacement is "
        "length-exact and differs in exactly 6 positions with the `ja` rel8 "
        "untouched, and that 0x7A8628 is referenced exactly ONCE in .text - "
        "with a positive control (an imm32 we proved present) and a "
        "negative control. FALSIFIER: if the model ever grows a control-flow "
        "or dispatch-table domain, promote all four and delete this entry."),
    "kPopupStyleRetargets": (
        "PERMANENT - not geometry at all. The four sites swap a FONT STYLE "
        "GUID (0x4A809914/15 -> 0x5C4B0914/15, MessageHeader/Body -> the "
        "Html variants) in sub_52CC50 / sub_762F20. constants.json holds "
        "only geometry roles; a style-id map is a different model that "
        "does not exist and is not needed - the patch family is byte-"
        "verified by its own gate (verify-before-write in CodePatches). "
        "FALSIFIER: none conceivable within a geometry model; this entry "
        "is the honest boundary of the model's domain."),
    "_V459_HOOK_VA_DOC": (
        "PERMANENT - CONTROL FLOW, not geometry (kRatingUpdateVa precedent, "
        "2026-08-30 sweep). MinHook detour targets for the CSI/sprite/marker "
        "probe arcs (#188/#191), the region-screen rebuild family "
        "(#131/#132), the FONTGUID hook (#24), plus one cave-resume VA "
        "(kCostOriginBack, #159). MinHook rewrites a prologue and a resume "
        "VA is a jump target: neither holds a rect, size or position, so a "
        "geometry model has nothing to represent. Each install is gated by "
        "its own memcmp stock-prologue verify in CodePatches.cpp. "
        "FALSIFIER: a geometry immediate appearing at any of these VAs."),
    "_V459_RENDERER_IMM_DOC": (
        "PERMANENT-UNTIL-DOMAIN-GROWTH - REAL GEOMETRY, WRONG SUBSYSTEM. "
        "These ARE scaled immediates, but they live in the 3D-renderer / "
        "dispatch-view / region-camera code (0x0046xxxx, 0x005Fxxxx, "
        "0x007ACxxx), not in a GZWin builder. The census discovers owners "
        "by the rect-driving cIGZWin call signature (>=2 callers, "
        "<=0x1200 bytes, call [reg+0xD4..0xE0]); MEASURED 2026-08-30: "
        "sub_46C8B0, sub_46D990, sub_5F20A0 and sub_7ACC90 are all absent "
        "from builders.json discovered, so promotion is structurally "
        "unavailable, not merely undone. Adjudicated elsewhere: the "
        "appliers refuse all-or-none against stock float bits, "
        "gate_patch_families_combined.py holds every width "
        "(kCsiQuad 11x4, kVa 4, signposts 2x5, kRegionCamScaleSite 5), and "
        "the attributions are screen-proven in "
        "SC4-WORLD-OVERLAYS.md / CITY-SITUATION-INDICATORS.md. "
        "FALSIFIER: the census growing a renderer domain, or any of these "
        "owners appearing in builders.json discovered - then promote and "
        "delete this entry."),
    "_V459_OWNGATE_DOC": (
        "MEASURED MODEL BOUNDARY, NOT AN AGE PROBLEM (2026-08-30 sweep). "
        "All four owner functions were hand-seeded into "
        "census.py EXTRA_BUILDERS (0x793810 precedent) and the model was "
        "REGENERATED the same day - so these rows are what the regenerated "
        "model measurably could NOT hold, each with the reason: "
        "kCheatRectSite/kCheatClearSite - owner sub_79BDC0 seeded, emu "
        "emitted ZERO constants for it (the dialog Init path does not drive "
        "the recorder set; the census run prints no line for it). "
        "kCostBoxHeightSite/kCostBoxWidthSite - owner sub_7EDEB0 seeded and "
        "censused (4 constants incl. the restore-toolbars pair), but the "
        "cost-readout branch emitted nothing at 0x7EEF43/0x7EEF54 (branch "
        "not driven; the sibling sites in the same owner DID census, which "
        "is the positive control). "
        "kAdviceRowWinSite - owner censused long since; the 19-byte wide "
        "window is an equal-length block re-encode outside the "
        "single-immediate schema, the same class as kOrdinanceNameXBlocks; "
        "it is the mutually-exclusive ALTERNATE of adjudicated "
        "kAdviceRowMidSite (see gate_patch_families_combined.py ALTERNATES). "
        "ADJUDICATED ELSEWHERE, NOT UNCHECKED: _tests/Test-PatchSiteBytes.py "
        "byte-pins kCheatRectSite (32), kCheatClearSite (39) and both "
        "cost-box sites against the shipped exe with positive and mask "
        "controls, and gate_patch_families_combined.py registers every "
        "width. (kIntroVidSites and kRestoreToolbarsOriginSite left this "
        "table on the same regeneration - the model holds all four intro "
        "sites and both restore-origin constants, so they adjudicate for "
        "real now.) FALSIFIER: Test-PatchSiteBytes red, or a regeneration "
        "that emits constants for a site listed here - then delete its row "
        "and let it adjudicate."),
}
SKIPPED = dict(PERMANENT_OUT_OF_SCOPE)   # counting machinery reads SKIPPED

# #121 x8 bake family: four arrays, ONE reason. The gate matches on the array
# NAME, so the shared rationale above is stored once under a _DOC key and
# fanned out here - a single edit keeps all four honest and prevents the
# "same reason drifting into four copies" failure (law 43, coupled pairs).
_X8_BAKE_SITES = ("kX8DispatchSite", "kX8StubBlock", "kX8TableVa", "kX8TailVa")
for _name in _X8_BAKE_SITES:
    SKIPPED[_name] = SKIPPED["_X8_BAKE_FAMILY_DOC"]
del SKIPPED["_X8_BAKE_FAMILY_DOC"]
_V274_BLOCKS = ("kOrdinanceNameXBlocks", "kGlRow0Site")
for _name in _V274_BLOCKS:
    SKIPPED[_name] = SKIPPED["_V274_BLOCK_REENCODE_DOC"]
del SKIPPED["_V274_BLOCK_REENCODE_DOC"]
_V274_HOOKS = ("kRatingUpdateVa", "kDeclineStepVa")
for _name in _V274_HOOKS:
    SKIPPED[_name] = SKIPPED["_V274_HOOK_VA_DOC"]
del SKIPPED["_V274_HOOK_VA_DOC"]
# 2026-08-30 sweep (v4.5.9): the three _DOC groups above, fanned out the same
# way - one rationale per group, matched on the entry name.
_V459_HOOKS = ("kCsiDrawVa", "kSpAttachVa", "kSpBindVa", "kSpHoverVa",
               "kSpQuadVa", "kSpTargetVa", "kSpTexVa", "kSpriteFactoryVa",
               "kCreateEffectVa", "kMarkerStripVa", "kArtFetchVa",
               "kBalloonBuildVa", "kDrawVa", "kSetFontStyleByGuid",
               "kRegionBuildFn", "kRegionItemBuildFn", "kRegionOverlayFn",
               "kRegionPanClampFn", "kRegionInvalidateFn",
               "kRegionCamSetScale", "kCostOriginBack")
for _name in _V459_HOOKS:
    SKIPPED[_name] = SKIPPED["_V459_HOOK_VA_DOC"]
del SKIPPED["_V459_HOOK_VA_DOC"]
_V459_RENDERER = ("kCsiQuad", "kVa", "kSignpostSizeSite",
                  "kSignpostRaiseSite", "kRegionCamScaleSite")
for _name in _V459_RENDERER:
    SKIPPED[_name] = SKIPPED["_V459_RENDERER_IMM_DOC"]
del SKIPPED["_V459_RENDERER_IMM_DOC"]
_V459_OWNGATE = ("kCheatRectSite", "kCheatClearSite",
                 "kCostBoxHeightSite", "kCostBoxWidthSite",
                 "kAdviceRowWinSite")
for _name in _V459_OWNGATE:
    SKIPPED[_name] = SKIPPED["_V459_OWNGATE_DOC"]
del SKIPPED["_V459_OWNGATE_DOC"]

OUT_OF_SCOPE = set(SKIPPED)

# ---------------------------------------------------------------------------
# DEFERRED - in-scope, adjudicable in principle, but the model on disk has not
# been REGENERATED since these sites were patched. This is a different animal
# from SKIPPED (which is about what the model can REPRESENT) and it is not a
# pass. Read the FORENSIC RECORD block at the top of this file first.
#
# Every field below is load-bearing; guards G1-G4 in main() revoke the whole
# deferral the moment any of them stops holding, so this table cannot rot into
# a permanent blind spot the way a silent OUT_OF_SCOPE drop did before #96.
# ---------------------------------------------------------------------------
# CLOSED 2026-08-04: the table is EMPTY because the prescribed procedure ran
# and the guards expired every entry, exactly as designed. Record of what
# closed the 8 (the machinery below stays for the NEXT deferral):
#   * 0x76D3D0 promoted into census.EXTRA_BUILDERS (the one edit this header
#     prescribed). The first `--resume` regeneration then served STALE
#     vtgeom rows - censusing a new owner did not invalidate the vtgeom unit,
#     so the owner came out with vtGeom=[] and constants.py honestly derived
#     0 sites. census.py's vtgeom/ident units now fold an owner-set digest
#     into their resume keys, so promotion can never be silently absorbed by
#     a stale unit again.
#   * The five kGraphLegendImmSites: covered by geomextra RECORDER D
#     (object-member geometry stores - each imm's register reaches a
#     `mov [obj+disp], reg` within a short window; all five verified against
#     the stock exe's dataflow, e.g. 0x76E239 `add eax,9` -> 0x76E245
#     `mov [ebp+0x14], eax`).
#   * The three kGraphLegendBlocks: covered by RECORDER E (stack-pair-
#     difference insets: imm applied to [esp+0x50]-[esp+0x48], a width by
#     construction) plus the census's OWN SetArea recorder finally seeing the
#     4-arg call at 0x76E168 once the stale unit was regenerated. Block 3
#     additionally needed TABLE_LEN to carry the blocks' TRUE per-entry byte
#     extents (25/41/42) instead of the flat minimum - its only geometry imm
#     sits at offset 0x22, outside a 25-byte window.
#   * 0x76E2C8 was derived by BOTH recorders D and E from different
#     instruction shapes - real corroboration, and collapse_by_va confirmed
#     the bytes agree.
# Result: crosscheck went from "251 adjudicated + 8 DEFERRED" to
# "259 adjudicated (259 passed, 0 MISSED) + 0 deferred".
DEFERRED = {}
DEFERRED_VAS = {va: name for name, d in DEFERRED.items() for va in d["sites"]}

# The shape an entry must have, kept as the selftest's SYNTHETIC deferral so
# the guard machinery stays TESTED while the real table is empty (an unfired
# guard is decoration - the selftest's own words). The VAs are real
# kGraphLegendImmSites members, so the synthetic entry exercises the same
# table-lookup paths a live deferral would.
SELFTEST_DEFERRED = {
    "kGraphLegendImmSites": dict(
        owner=0x76D3D0,
        sites=(0x76E233, 0x76E239, 0x76E23C, 0x76E2AF, 0x76E2C8),
        what="SYNTHETIC (selftest only) - the closed #57 deferral's shape.",
        clears="n/a - injected by selftest() to keep guards G1-G4 fired."),
}


def _ts(t):
    import time
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(t))


def deferral_guards(tables, model, helpers, _mtimes=None, _builders=None):
    """G1-G4. Returns (deferrable_vas, notes, revoked).

    `revoked` is the honest outcome: any guard that stops holding turns the
    whole deferral off, the entries go back to being MISSES, and the run
    fails. Nothing here can make a red run green by itself - it can only
    keep a KNOWN, NAMED, dated gap out of the pass count while it lasts.
    """
    notes, revoked = [], []
    cons_p = os.path.join(C.HERE, "constants.json")
    bld_p = os.path.join(C.HERE, "builders.json")

    # G1 - model age. The whole excuse is "the model predates the patch".
    if _mtimes is not None:
        t_model, t_patch = _mtimes
    else:
        try:
            t_model, t_patch = os.path.getmtime(cons_p), os.path.getmtime(CP)
        except OSError:
            t_model = t_patch = None
    if t_model is None:
        g1 = False
        notes.append("G1 model age        : UNMEASURABLE (mtime unavailable)")
    else:
        g1 = t_model < t_patch
        notes.append("G1 model age        : constants.json %s   CodePatches.cpp "
                     "%s  -> model is %s" % (_ts(t_model), _ts(t_patch),
                                             "OLDER (deferral legal)" if g1
                                             else "NEWER OR EQUAL (excuse dead)"))
    if not g1:
        revoked.append("G1: constants.json is no longer older than "
                       "CodePatches.cpp, so 'the model predates the patch' "
                       "is no longer true.")

    # G2/G3 - owner promoted? owner discovered? (the positive control)
    b = _builders if _builders is not None else (C.jload(bld_p) or {})
    promoted = set(b.get("builders") or {})
    discovered = set(b.get("discovered") or {})
    seen_owner = set()
    for name, d in sorted(DEFERRED.items()):
        o = d["owner"]
        first = o not in seen_owner       # one G2/G3 line per OWNER, not per
        seen_owner.add(o)                 # table - two tables share sub_76D3D0
        is_prom = ("0x%X" % o) in promoted
        is_disc = str(o) in discovered
        if first:
            notes.append("G2 owner promoted   : sub_%06X in builders.json"
                         "->builders     = %s"
                         % (o, "YES (excuse dead)" if is_prom
                            else "no  (deferral legal)"))
            notes.append("G3 POSITIVE CONTROL : sub_%06X in builders.json"
                         "->discovered  = %s"
                         % (o, "YES - census CAN see it, so this null is "
                            "MEASURED" if is_disc else
                            "NO - null is STRUCTURAL"))
        if is_prom:
            revoked.append("G2 (%s): owner sub_%06X is now a censused "
                           "builder, so an uncovered site is a real hole, "
                           "not a model-age gap." % (name, o))
        if not is_disc:
            revoked.append("G3 (%s): owner sub_%06X is in neither `builders` "
                           "nor `discovered` - there is no positive control, "
                           "so this gate will NOT claim the model merely "
                           "'has not caught up'." % (name, o))

    # G4 - address whitelist, and auto-expiry when the model does learn a site.
    deferrable, expired, unlisted = set(), [], []
    for name in DEFERRED:
        for a in tables.get(name, []):
            n = entry_len(name, a)
            if a not in DEFERRED_VAS:
                unlisted.append((name, a))
                continue
            if any((a + k) in model or (a + k) in helpers for k in range(n)):
                expired.append((name, a))     # model learned it - adjudicate
            else:
                deferrable.add(a)
    notes.append("G4 whitelist        : %d listed VA(s) deferrable, %d NOT "
                 "listed (adjudicated normally), %d deferral(s) EXPIRED "
                 "(model now covers them)"
                 % (len(deferrable), len(unlisted), len(expired)))
    for name, a in sorted(unlisted, key=lambda t: t[1]):
        notes.append("   0x%08X in %s is NOT on the deferral whitelist - it "
                     "is being adjudicated." % (a, name))
    for name, a in sorted(expired, key=lambda t: t[1]):
        notes.append("   0x%08X in %s: DEFERRAL EXPIRED - the model now "
                     "covers it. Delete it from DEFERRED." % (a, name))

    if revoked:
        deferrable = set()
    return deferrable, notes, revoked


ADDR_RE = r"0x([0-9A-Fa-f]{6,8})\b"
# Only .text VAs are site addresses.  .rdata table bases (0xACD4A0 /
# 0xAB4AD0) and window ids that happen to be 6-8 hex digits are not.
TEXT_LO, TEXT_HI = 0x407000, 0xA7FA2D


def _wrap(text, width):
    out, line = [], ""
    for w in text.split():
        if len(line) + len(w) + 1 > width:
            out.append(line)
            line = w
        else:
            line = (line + " " + w) if line else w
    if line:
        out.append(line)
    return out


def strip_comments(src):
    src = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
    src = re.sub(r"//[^\n]*", " ", src)
    return src


def parse_codepatches():
    """Site tables only - comments are stripped FIRST.

    CodePatches.cpp's comments quote dozens of VAs ('builder 0x77E600-
    0x781C8E', 'create 0x786E48'); counting those as patched sites would
    manufacture phantom misses.
    """
    src = strip_comments(
        open(CP, "r", encoding="utf-8", errors="replace").read())
    tables = {}
    for m in re.finditer(r"k([A-Za-z0-9]+)\s*\[\]\s*=\s*\{(.*?)\};", src, re.S):
        name = "k" + m.group(1)
        addrs = [int(a, 16) for a in re.findall(ADDR_RE, m.group(2))
                 if TEXT_LO <= int(a, 16) < TEXT_HI]
        if addrs:
            tables[name] = addrs
    for m in re.finditer(r"k([A-Za-z0-9]+)\s*=\s*" + ADDR_RE + r"\s*;", src):
        v = int(m.group(2), 16)
        if TEXT_LO <= v < TEXT_HI:
            tables.setdefault("k" + m.group(1), []).append(v)
    return tables


def selftest():
    """NEGATIVE CONTROLS for the deferral. An unfired guard is an untested
    guard, and an untested guard is decoration - it would let the DEFERRED
    bucket quietly become the silent OUT_OF_SCOPE drop that #96 removed.

    Each case below forces exactly one guard to stop holding and asserts the
    deferral collapses (deferrable == 0, i.e. the 8 go back to being MISSES
    and the run goes red). Case 5 is the opposite direction: it proves the
    deferral EXPIRES by itself once the model learns a site.
    """
    tables = parse_codepatches()
    live = C.jload(os.path.join(C.HERE, "builders.json")) or {}
    # 2026-08-04: the real DEFERRED table is EMPTY (the #57 deferral closed).
    # Inject the synthetic entry for the duration so every guard still fires
    # against real table VAs; restored in the finally below.
    global DEFERRED, DEFERRED_VAS
    saved = (DEFERRED, DEFERRED_VAS)
    DEFERRED = SELFTEST_DEFERRED
    DEFERRED_VAS = {va: name for name, d in DEFERRED.items()
                    for va in d["sites"]}
    owners = sorted({d["owner"] for d in DEFERRED.values()})
    n_listed = sum(1 for t in DEFERRED for a in tables.get(t, [])
                   if a in DEFERRED_VAS)
    ok_b = {"builders": {}, "discovered": {str(o): {} for o in owners}}
    fails = []

    def case(label, expect_defer, **kw):
        d, notes, rev = deferral_guards(tables, kw.pop("model", {}),
                                        kw.pop("helpers", {}), **kw)
        got = len(d)
        good = (got == expect_defer)
        print("   %-58s deferrable=%-3d expected=%-3d  %s"
              % (label, got, expect_defer, "PASS" if good else "FAIL"))
        if not good:
            fails.append(label)
        return rev

    print("SELFTEST - can the deferral guards actually fire?")
    print("   (all cases use the REAL CodePatches tables; only the guard "
          "inputs are injected)")
    case("baseline: model older, owner unpromoted+discovered", n_listed,
         _mtimes=(100.0, 200.0), _builders=ok_b)
    case("G1 fires: constants.json NEWER than CodePatches.cpp", 0,
         _mtimes=(300.0, 200.0), _builders=ok_b)
    case("G1 fires: mtimes unmeasurable", 0,
         _mtimes=(None, None), _builders=ok_b)
    case("G2 fires: owner promoted into builders.json->builders", 0,
         _mtimes=(100.0, 200.0),
         _builders={"builders": {"0x%X" % o: {} for o in owners},
                    "discovered": {str(o): {} for o in owners}})
    case("G3 fires: POSITIVE CONTROL absent (owner not discovered)", 0,
         _mtimes=(100.0, 200.0), _builders={"builders": {}, "discovered": {}})
    # G4a - an address NOT on the whitelist must be adjudicated, not deferred
    t4 = dict(tables)
    t4["kGraphLegendImmSites"] = list(t4["kGraphLegendImmSites"]) + [0x76EFFF]
    d4, _, _ = deferral_guards(t4, {}, {}, _mtimes=(100.0, 200.0),
                               _builders=ok_b)
    good4 = (0x76EFFF not in d4 and len(d4) == n_listed)
    print("   %-58s deferrable=%-3d expected=%-3d  %s"
          % ("G4 holds: a NEW unlisted VA in a deferred table is adjudicated",
             len(d4), n_listed, "PASS" if good4 else "FAIL"))
    if not good4:
        fails.append("G4 whitelist")
    # G4b - auto-expiry: the model learning a site must END that deferral
    d5, notes5, _ = deferral_guards(tables, {0x76E233: {}}, {},
                                    _mtimes=(100.0, 200.0), _builders=ok_b)
    good5 = (0x76E233 not in d5 and len(d5) == n_listed - 1
             and any("EXPIRED" in n for n in notes5))
    print("   %-58s deferrable=%-3d expected=%-3d  %s"
          % ("G4 expiry: model covers 0x76E233 -> that deferral ends",
             len(d5), n_listed - 1, "PASS" if good5 else "FAIL"))
    if not good5:
        fails.append("G4 auto-expiry")

    print()
    DEFERRED, DEFERRED_VAS = saved     # restore the (empty) real table
    if fails:
        print("SELFTEST FAILED: %d case(s) - %s" % (len(fails),
                                                    "; ".join(fails)))
        return 1
    print("SELFTEST OK: every guard fires, and the deferral expires by "
          "itself when the model catches up. (Guards exercised against the "
          "SYNTHETIC entry - the real DEFERRED table is empty since "
          "2026-08-04.)")
    return 0


def main():
    if "--selftest" in sys.argv:
        return selftest()
    tables = parse_codepatches()
    cons = C.jload(os.path.join(C.HERE, "constants.json"))
    if cons is None:
        raise SystemExit("constants.json missing - run constants.py first")

    model = {}
    for r in cons["sites"]:
        model[int(r["va"], 16)] = r

    # Constants that live INSIDE a primitive's body (Slider height 14, Combo
    # height 15/width 120, the TextLabel 1000-px anchor) are recorded under
    # `helperConstants`, not `sites` - see header note (1). They are model
    # knowledge, so they count as coverage for the MISS test. They are kept
    # out of `model` so the EXTRAS report keeps its site-record shape; a
    # helper constant CodePatches does not patch is therefore reported in the
    # helper line below rather than in the extras list.
    helpers = {int(h["site"], 16): h for h in cons.get("helperConstants", [])}

    # G1-G4 decide, from measurements, which listed VAs may be deferred.
    # Any guard that stops holding empties this set, so the entries go back
    # to being MISSES and the run goes red again.
    deferrable, guard_notes, revoked = deferral_guards(tables, model, helpers)

    covered = {}
    inscope, outscope, deferred_n = 0, 0, 0
    for name, addrs in tables.items():
        for a in addrs:
            n = entry_len(name, a)
            for k in range(n):
                covered[a + k] = name
            if name in OUT_OF_SCOPE:
                outscope += 1
            elif a in deferrable:
                deferred_n += 1
            else:
                inscope += 1

    # MISS: a CodePatches entry with no model site inside its byte run
    misses = []
    deferred_revoked = 0
    for name, addrs in tables.items():
        if name in OUT_OF_SCOPE:
            continue
        for a in addrs:
            n = entry_len(name, a)
            if a in deferrable:
                continue
            if not any((a + k) in model or (a + k) in helpers
                       for k in range(n)):
                misses.append((name, a))
                if a in DEFERRED_VAS:
                    deferred_revoked += 1

    # EXTRA: a model site not covered by any CodePatches byte run
    extras = [r for va, r in sorted(model.items()) if va not in covered]

    # ---- the one line a future reader must not be able to misread -------
    # "passed" counts only entries this gate actually adjudicated. A SKIPPED
    # entry is never folded into it: a narrowed gate that reports 100% is
    # exactly the lie this header exists to prevent.
    checked = inscope
    passed = inscope - len(misses)
    total = inscope + deferred_n + outscope
    print("SUMMARY: %d CodePatches entries = %d adjudicated (%d passed, %d "
          "MISSED) + %d deferred + %d skipped"
          % (total, checked, passed, len(misses), deferred_n, outscope))
    print("         a SKIPPED entry is NOT a pass - it is a question this "
          "gate does not ask.")
    print("         a DEFERRED entry is NOT a pass either - it is a question "
          "this gate asks but")
    print("         cannot yet answer because the model on disk predates the "
          "patch. Guards below.")
    print()
    print("CodePatches.cpp tables parsed: %d (%d adjudicated entries, %d "
          "deferred, %d out-of-scope)"
          % (len(tables), inscope, deferred_n, outscope))
    for name in sorted(tables):
        tag = ("  [out of scope]" if name in OUT_OF_SCOPE else
               "  [DEFERRED]" if name in DEFERRED else "")
        print("   %-24s %3d entries%s" % (name, len(tables[name]), tag))
    print()
    # ---- the deferral, its four guards, and every measurement behind them --
    print("DEFERRED (%d entries - in scope, NOT adjudicated, NOT passes):"
          % deferred_n)
    if not deferred_n and not revoked:
        print("   none.")
    for name in sorted(DEFERRED):
        d = DEFERRED[name]
        n_def = sum(1 for a in tables.get(name, []) if a in deferrable)
        if not n_def:
            continue
        print("   %-24s %d entries  owner sub_%06X" % (name, n_def, d["owner"]))
        for line in _wrap("WHAT: " + d["what"], 68):
            print("      %s" % line)
        for line in _wrap("TO RESOLVE: " + d["clears"], 68):
            print("      %s" % line)
    print()
    print("   GUARDS - the deferral above is legal only while ALL of these hold:")
    for line in guard_notes:
        print("      %s" % line)
    if revoked:
        print()
        print("   DEFERRAL REVOKED - %d guard(s) no longer hold. Every listed "
              "entry has been" % len(revoked))
        print("   put back into the adjudicated set and counted as a MISS:")
        for r in revoked:
            for line in _wrap(r, 66):
                print("      %s" % line)
    print()
    print("SKIPPED (%d entries this gate does NOT adjudicate - not passes):"
          % outscope)
    for name in sorted(SKIPPED):
        n_ent = len(tables.get(name, []))
        if not n_ent:
            continue
        print("   %-24s %d entries" % (name, n_ent))
        for line in _wrap(SKIPPED[name], 68):
            print("      %s" % line)
    print()
    print("helper constants in the model: %d (%d also patched by CodePatches)"
          % (len(helpers), sum(1 for va in helpers if va in covered)))
    print()
    print("MISSES (CodePatches patches it, the model does not know it): %d" % len(misses))
    # Print the OWNING FUNCTION with each miss: every miss diagnosed on
    # 2026-08-02 turned out to be a whole uncovered owner, not a lone stray
    # instruction, and the owner is what an operator has to act on.
    owner_of = None
    try:
        owner_of = C.FuncMap().owner
    except SystemExit:
        pass          # funcs.json absent - degrade to the old one-line form
    for name, a in sorted(misses, key=lambda t: t[1]):
        ins = C.rd(a, 8).hex()
        own = ("  owner sub_%06X" % owner_of(a)) if owner_of else ""
        print("   0x%08X  %-26s bytes %s%s" % (a, name, ins, own))
    print()
    print("EXTRAS (the model found it, CodePatches does NOT patch it): %d" % len(extras))
    for r in extras:
        print("   %s  %-12s %-6s %-11s val=%-6d twins=%s  %s"
              % (r["va"], r["via"], r["role"], r["enc"], r["value"],
                 ",".join(r["twins"]) or "-", r["ownerLabel"][:44]))

    C.jdump(os.path.join(C.HERE, "_work", "crosscheck.json"),
            {"totalEntries": total,
             "checked": checked, "passed": passed,
             "deferred": deferred_n, "skipped": outscope,
             "misses": [{"table": n, "va": "0x%X" % a} for n, a in misses],
             "extras": [r["va"] for r in extras],
             "skippedTables": {n: {"entries": len(tables.get(n, [])),
                                   "reason": why}
                               for n, why in SKIPPED.items()
                               if tables.get(n)},
             "deferredTables": {n: {"entries": sum(1 for a in tables.get(n, [])
                                                   if a in deferrable),
                                    "owner": "0x%X" % d["owner"],
                                    "what": d["what"], "clears": d["clears"]}
                                for n, d in DEFERRED.items()
                                if any(a in deferrable
                                       for a in tables.get(n, []))},
             "deferralGuards": guard_notes,
             "deferralRevoked": revoked,
             "inScopeEntries": inscope})
    st = C.State()
    st.mark("crosscheck", "run", "done", checked=checked, passed=passed,
            deferred=deferred_n, skipped=outscope, misses=len(misses),
            extras=len(extras))

    # A miss means CodePatches is rewriting bytes the offline model has never
    # seen: any conclusion the model offers about that family is a guess. Fail
    # the run. Extras are informational - an unpatched constant is a finding,
    # not a hole (laws 15/16).
    if misses:
        print()
        print("FAIL: %d patched site(s) are outside the offline model. The "
              "model cannot be used" % len(misses))
        print("      to reason about the families listed above.")
        if revoked:
            print("      %d of them arrived here by DEFERRAL REVOCATION - a "
                  "guard printed above stopped" % deferred_revoked)
            print("      holding, so entries this gate used to defer are now "
                  "adjudicated and failing.")
        print("      Read the FORENSIC RECORD and 'WHY THE 14 MISSES EXIST' "
              "blocks at the top of")
        print("      this file for the diagnosis and the exact commands that "
              "clear each family.")
        return 1
    print()
    print("OK: %d of %d adjudicated CodePatches sites are covered by the "
          "model." % (passed, checked))
    print("    %d DEFERRED + %d SKIPPED = %d of %d total entries were NOT "
          "adjudicated and are" % (deferred_n, outscope,
                                   deferred_n + outscope, total))
    print("    NOT counted as passes - see the two blocks above. This gate is "
          "GREEN over its")
    print("    stated scope, which is narrower than 'all of CodePatches.cpp' "
          "by %d entries." % (deferred_n + outscope))
    return 0


if __name__ == "__main__":
    sys.exit(main())
