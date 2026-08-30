"""gate_patch_families_combined.py - task #106.

THE GAP THIS EXISTS TO CLOSE
============================
crosscheck.py verifies every byte-patch site IN ISOLATION. Nothing anywhere
tested families in COMBINATION - so task #104 (a shutdown spin that appeared
only with OrdinanceInsetPatch and BudgetDeptPatch both armed) was invisible to
every gate we owned.

Two independent checks, because "combination" can go wrong in two ways:

  CHECK A - BYTE OVERLAP.  Two families whose write ranges or verify ranges
      touch the same bytes. The one that runs second either fails its
      verify-before-write and silently DECLINES, or writes over the first.
      Either way the shipped .text is a state no single-family test ever saw.

  CHECK B - SPLIT OWNERSHIP.  Two constants that a single builder consumes
      together - a left inset and a right margin of the SAME dialog - owned by
      DIFFERENT ini flags. Then a user (or a bisect) can arm one and not the
      other and get a layout neither family was designed for. This is the
      check that would actually have flagged #104's configuration space,
      because for #104 the byte ranges turned out NOT to overlap at all.

HONEST SCOPE - read before quoting a green run
==============================================
* Check A is EXACT: computed from each encoding's real width.
* Check B is a STRUCTURAL flag, not a defect proof. It reports that a builder's
  constants are split across ini flags. It does NOT prove any particular split
  misbehaves. A static-data finding is a HYPOTHESIS until something on screen
  disagrees (the #98 law - we shipped one of those and broke the user's UI).
* Ownership is read from the CALL SITES in SC4UIScaleDllDirector.cpp, not
  hand-maintained here, so it cannot drift from what actually ships.
* THE ANTI-ROT PROPERTY: every site table found in CodePatches.cpp must appear
  in WIDTHS below. A new table nobody registered FAILS the gate rather than
  being silently skipped - the failure mode that let three packages rot
  (#58, #57 phase 4) was always silent omission, never a loud error.

Usage:  python gate_patch_families_combined.py [--verbose]
Exit 0 only when Check A is clean and every table is registered.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
CODEPATCHES = os.path.join(ROOT, "src", "CodePatches.cpp")
DIRECTOR = os.path.join(ROOT, "src", "SC4UIScaleDllDirector.cpp")
VERBOSE = "--verbose" in sys.argv

# --------------------------------------------------------------------------
# WIDTH REGISTRY. width = bytes the applier VERIFIES and/or WRITES at a site.
# Each entry is (width, how the width is derived) - the note is not decoration,
# it is what lets the next person check the number against the applier.
# "dyn:<field>" means the width comes from a per-entry field plus a constant.
# --------------------------------------------------------------------------
WIDTHS = {
    "kGlRow0Site": (8, "C7 44 24 18 + imm32"),  # lane3 ROW0_TOP re-encode
    "kOrdinanceNameXImm8Sites": (3, "6A <stock> <ctx> push imm8"),  # lane2
    "kRatingImulSites":          (3, "imul r32,r/m32,imm8 - opcode 6B, imm at +2"),
    "kTipWrapSites":             (5, "push imm32 - 68 + dword"),
    "kBudgetBtnSizeSites":       (7, "6a 1e 68 b4 00 00 00 (push h; push w)"),
    "kBudgetBtnXSites":          (6, "81 e9 c3 00 00 00 (sub ecx,195)"),
    "kBudgetBtnYSites":          (3, "83 /5 28 (sub r32,40)"),
    "kOrdinanceInsetSites":      (3, "6a <stock> <ctx> - imm8 pinned by next opcode"),
    "kSubFlyoutProviderSites":   (2, "6a <stock>"),
    "kDeptImm8Sites":            (2, "6a <stock>"),
    "kDeptImm32Sites":           (5, "68 + dword"),
    "kBudgetSubImm8Sites":       (3, "83 <modrm> <stock>"),
    "kBudgetLeaDisp8Sites":      ("dyn:immOff+1", "lea r32,[r32+disp8]; len = immOff+1"),
    "kMasterNotchSites":         ("dyn:immOff+4", "raw imm32 at immOff; len = immOff+4"),
    "kBizBoxSizeSites":          (7, "6a 64 68 2c 01 00 00"),
    "kDataViewLegendLeaSites":   ("dyn:immOff+1", "lea disp8; len = immOff+1"),
    "kDataViewLegendImm32Sites": ("dyn:immOff+4", "raw imm32; len = immOff+4"),
    "kGraphLegendImmSites":      (3, "<b0> <b1> <stock> - 1-byte field at +2"),
    "kGraphLegendBlocks":        ("dyn:len", "equal-length block re-encode; len field"),
    "kPopupStyleRetargets":      (5, "push imm32 guid - 68 + dword"),
    # Scalars, not arrays - handled separately but registered so the anti-rot
    # sweep can account for them.
    "kBizBoxCloseX":             (5, "push imm32"),
    "kBizBoxCloseY":             (2, "6a 0b"),
    # v4.5.3 RESTORE-TOOLBARS ORIGIN. ONE 6-byte block covering BOTH placement
    # constants, deliberately: `83 /5 1C 50 6A 0C` is sub eax,28 / push eax /
    # push 12, the two arguments of the same GZWinMoveTo call. Registering it
    # as a single span rather than two imm8 scalars is what makes a
    # half-applied state unreachable (law 43, both halves or neither) - the
    # encoding enforces the pairing instead of a comment asking for it.
    "kRestoreToolbarsOriginSite": (6, "83 /5 1c 50 6a 0c (sub eax,28; push eax; push 12)"),
    # v4.5.6 CHEAT DIALOG. Two spans, both verified before either is written.
    # The rect block is four adjacent `mov [esp+d8],imm32` writing the field's
    # l/t/r/b into the Init's own stack frame; the clearance block holds the
    # two `add r32,8` that turn that field into the dialog's SetW/SetH. They
    # are registered separately because they are 310 bytes apart, but the
    # patcher treats them as one unit - a rect without its clearance is a
    # state the function makes unreachable.
    "kCheatRectSite":            (32, "4 x C7 44 24 <d8> <imm32> (l,t,r,b into the stack frame)"),
    "kCheatClearSite":           (39, "block holding 2 x 83 /0 08 at +0x0C and +0x24"),
    "kAdviceRowMidSite":         (3, "83 /5 3d (sub r32,61)"),
    # #136: the WIDE form of the SAME patch. 0x0079388B..0x0079389D contains
    # kAdviceRowMidSite (0x0079388F) by construction - the window swallows the
    # imm8 it replaces. That is a DELIBERATE overlap between two MUTUALLY
    # EXCLUSIVE encodings: ApplyAdviceRowScale takes the narrow path when
    # S <= 127 (1.5x, 2x) and the wide path otherwise (3x), never both in one
    # process. Listed here so the anti-rot sweep is not blind to it, and
    # EXCLUDED from the overlap check for that reason - see ALTERNATES.
    "kAdviceRowWinSite":         (19, "6a 08 / 8d b0 imm32 / 2 stores / 3 nop"),
    # #131/#132 REGION FAMILY (v2.81-v2.85). These went unregistered from
    # v2.81.0 and kept this gate RED for four versions - which is exactly the
    # failure the anti-rot property exists to prevent, because a standing red
    # makes every later red look pre-excused (the same note already sits on
    # the x8 family above). Registered now.
    "kRegionIsoSites":           (4, "float32 isometric basis in .rdata - DATA, excluded"),
    "kRegionIso2Sites":          (4, "float32 L2 overlay basis in .rdata - DATA, excluded"),
    "kRegionCamScaleSite":       (5, "push imm32 (0.25f) at 0x7AD0BB"),
    # #138 intro video (v2.93.0). Two opcodes, both 5 bytes: `68 imm32`
    # (push, the SetArea w/h) and `2D imm32` (sub eax, the centring
    # subtrahends). Registered the day the table was written - the anti-rot
    # property caught it unregistered on its FIRST run, which is the property
    # working. The patch APPLIES 4/4 and produces no visible change, so this
    # registration says the WRITES do not collide; it says nothing about the
    # feature, which is BACKLOG.
    "kIntroVidSites":            (5, "68 imm32 (push) or 2D imm32 (sub eax) - both 5"),
    # .rdata tables, not .text sites. Registered and then EXCLUDED from the
    # overlap check because they are data, not instruction streams.
    "kHtmlFontSizeTable":        (28, "7 dwords in .rdata - DATA, excluded"),
    "kHtmlHeadingSizeTable":     (28, "7 dwords in .rdata - DATA, excluded"),
    # 2026-08-30 registration sweep. This gate had been red long enough that
    # the COMPOSITION of its redness drifted (40 unregistered symbols across
    # five feature arcs) - the pre-excused-red failure its own header warns
    # about. Every entry below was classified by reading the applier, not the
    # name: a "Site" suffix does not make a site, and three of these are data.
    # #159 COST BOX (three sites, one feature):
    "kCostBoxHeightSite":        (2, "6a 20 push imm8 - opcode + imm8, refuses >0x7F"),
    "kCostBoxWidthSite":         (5, "68 imm32 push (stock 128)"),
    "kCostOriginSite":           (8, "83 c3 7c / 68 01 80 00 00 -> E9 rel32 + 3 nop (jmp to cave)"),
    # signpost pole-balloon quad (two 68-imm32 float pushes, 16 bytes apart):
    "kSignpostSizeSite":         (5, "68 imm32 (push 44.0f) at 0x5F20AF"),
    "kSignpostRaiseSite":        (5, "68 imm32 (push 150.0f) at 0x5F20BF"),
    # CSI / #191 marker family. kCsiQuad stores IMMEDIATE addresses, not
    # opcode addresses (the applier comment at its declaration says so):
    # width is the 4 float bytes verified and written at each of the 11 sites.
    "kCsiQuad":                  (4, "float imm32 at the IMMEDIATE address (B8 / C7 84 24 forms), 11 .text sites"),
    "kCsiConsts":                (4, "float32 CSI px constants - 4 in .rdata + .data twin 0xB07F80, DATA, excluded"),
    "kVa":                       (4, "imm32 of C7 44 24 18 near 0x0046CCCA - #191 marker tex side"),
    # zoom/pix lookup tables the applier verifies-and-writes whole:
    "kMarkerZoomTableVa":        (20, "5 x float32 zoom multipliers in .rdata 0xAA523C - DATA, excluded"),
    "kPixTableVa":               (40, "10 x float32 px dimensions at 0x00A88170 - DATA, excluded"),
}
RDATA_TABLES = {"kHtmlFontSizeTable", "kHtmlHeadingSizeTable",
                "kRegionIsoSites", "kRegionIso2Sites",
                # 2026-08-30: verified-and-written but data, not instruction
                # streams - must not enter CHECK A's overlap math.
                "kCsiConsts", "kMarkerZoomTableVa", "kPixTableVa"}

# #136: pairs of tables that are MUTUALLY EXCLUSIVE ENCODINGS of one patch.
# They overlap on purpose (the wide window contains the narrow site it
# replaces) and exactly one of them is ever written in a given process, so a
# byte overlap between them is not a double-write. Everything else still
# fails. Keep this set tiny and justify every entry - it is a hole in CHECK A,
# and a hole nobody can see is how CHECK A stops meaning anything.
ALTERNATES = [
    # ApplyAdviceRowScale: narrow `sub esi,imm8` for S<=127 (1.5x/2x),
    # wide `lea esi,[eax-imm32]` window otherwise (3x). Never both.
    {"kAdviceRowMidSite", "kAdviceRowWinSite"},
]


def _are_alternates(t1, t2):
    return any({t1, t2} <= grp for grp in ALTERNATES)

# Tables that are lookup data, carrying no site addresses at all.
NON_SITE_TABLES = {"kGraphLegendStrips", "kStockHtmlFontSizes", "kStockHtmlHeadingSizes",
                   "kGlStockB1", "kGlStockB2", "kGlStockB3",
                   "kGlStockRow0",
                   "kOrdinanceNameXBlocks",
                   # #121 x8 bake family: stock-byte patterns + VA tables for an
                   # in-memory dispatch extension, not imm-site tables. They were
                   # unregistered since v2.71.0 and kept this gate red - which
                   # made every later red look pre-excused (verifier, 2026-08-04).
                   "kX8DispatchStock", "kX8StubStock", "kX8TableStock",
                   # lane2/lane4 (v2.74.0): stock-byte verification patterns
                   "kOnxStockIncome", "kOnxStockExpense", "kRatingUpdateStock",
                   # #131/#132: stock float patterns verified against, and the
                   # cSC4RegionScreen item bitmap FIELD OFFSETS (0x1C..0x28) -
                   # struct offsets, not addresses. Neither is a patch site.
                   "kRegionIsoStock", "kRegionIso2Stock", "kItemBmpOff",
                   # 2026-08-30 sweep: memcmp-verify prologue/stock patterns
                   # gating MinHook installs or cave relocation - byte VALUES,
                   # not site addresses (kX8DispatchStock precedent).
                   "kCostOriginStock",                       # #159 cave verify + reloc source
                   "kSpAttachStock", "kSpBindStock",         # SPPROBE sprite family (#188)
                   "kSpHoverStock", "kSpQuadStock",
                   "kSpTargetStock", "kSpTexStock",
                   "kCreateEffectStock",                     # BUBBLEFX
                   "kMarkerStripStock", "kDrawStock",        # SPSTRIP / DRAWCAP probes
                   "kStockMarkerZoom",                       # zoom-table stock float bits
                   "kAdd", "kSub",                           # DISPATCHQUAD prologues (0x46F240 / 0x7D2990)
                   "kProlog",                                # FONTGUID (#24) SetFontStyleByGUID prologue
                   # 2026-08-30, the overlay-probe build. Same shape again:
                   # memcmp stock prologues gating a MinHook install. The gate
                   # caught all nine of these on the FIRST run after the code
                   # landed, which is the anti-rot property doing exactly its
                   # job on brand-new code rather than months later.
                   "kHighlightStock",                        # HIGHLIGHT  0x5E90E0
                   "kZoneQuadStock",                         # ZONEQUAD   0x6CC970
                   "kNborArrowStock",                        # NBORARROW  0x6D4860
                   "kDotSizeStock"}                          # DOTSIZE    0x5F7810
# Scalars that are NOT patch sites: the module base every site is expressed
# against, and stock-value constants. Excluded by NAME so the anti-rot sweep
# still shouts about anything genuinely new.
NON_SITE_SCALARS = {"kImageBase", "kX8DispatchSite", "kX8StubBlock",
                    "kX8TableVa", "kX8TailVa", "kRatingUpdateVa", "kDeclineStepVa",
                    # #131/#132: DETOUR TARGETS and a vtable identity, not
                    # imm-patch sites - MinHook rewrites the prologue, it does
                    # not edit an immediate, so they have no "encoding width".
                    "kRegionBuildFn", "kRegionItemBuildFn", "kRegionOverlayFn",
                    "kRegionPanClampFn", "kRegionInvalidateFn",
                    "kRegionCamSetScale", "kTileBufVt",
                    # 2026-08-30 sweep: MinHook detour targets (prologue is
                    # rewritten by MinHook, no immediate edited - no encoding
                    # width), one resume VA, one vtable identity.
                    "kCostOriginBack",                        # #159 cave resume VA
                    "kCsiDrawVa",                             # CSIKILL probe target 0x0046D990
                    "kSpAttachVa", "kSpBindVa", "kSpHoverVa", # SPPROBE sprite family (#188)
                    "kSpQuadVa", "kSpTargetVa", "kSpTexVa",
                    "kSpriteFactoryVa", "kCreateEffectVa",    # BALLOONSPRITE / BUBBLEFX
                    "kMarkerStripVa", "kArtFetchVa",          # SPSTRIP / ARTFETCH log probes
                    "kBalloonBuildVa", "kDrawVa",             # BALLOONKIND / DRAWCAP log probes
                    "kSetFontStyleByGuid",                    # FONTGUID (#24) detour target
                    "kWinTextIfaceVt",                        # GZWinText vtable identity 0xAE0118
                    # 2026-08-30 overlay probes: four detour targets and one
                    # .bss singleton pointer. None is an imm-patch site; the
                    # probes read and relay, they do not edit an immediate.
                    "kHighlightVa", "kZoneQuadVa",
                    "kNborArrowVa", "kDotSizeVa",
                    "kZoneManagerPtr"}                        # .bss cISC4ZoneManager* 0xB43D14

# --------------------------------------------------------------------------
FAILURES = []
NOTES = []


def fail(msg):
    FAILURES.append(msg)


def read(path):
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def strip_comments(s):
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
    s = re.sub(r"//[^\n]*", "", s)
    return s


def parse_tables(src):
    """name -> list of dicts with at least 'site'; plus immOff/len when present."""
    out = {}
    body = strip_comments(src)
    # const <Type> <name>[] = { ... };
    for m in re.finditer(r"const\s+(\w+)\s+(k\w+)\s*\[\s*\w*\s*\]\s*=\s*\{(.*?)\}\s*;",
                         body, flags=re.S):
        typ, name, blob = m.group(1), m.group(2), m.group(3)
        if name in NON_SITE_TABLES:
            continue
        entries = []
        if typ in ("uintptr_t", "uint32_t", "uint8_t", "int"):
            for hx in re.finditer(r"0x[0-9A-Fa-f]+", blob):
                entries.append({"site": int(hx.group(0), 16)})
        else:
            for em in re.finditer(r"\{([^{}]*)\}", blob):
                nums = re.findall(r"(?:0x[0-9A-Fa-f]+|-?\d+)", em.group(1))
                if not nums:
                    continue
                vals = [int(n, 16) if n.lower().startswith("0x") else int(n) for n in nums]
                e = {"site": vals[0], "vals": vals}
                entries.append(e)
        if entries:
            out[name] = entries
    # scalar consts
    for m in re.finditer(r"const\s+uintptr_t\s+(k\w+)\s*=\s*(0x[0-9A-Fa-f]+)\s*;", body):
        if m.group(1) in NON_SITE_SCALARS:
            continue
        out[m.group(1)] = [{"site": int(m.group(2), 16)}]
    return out


def field_index(name):
    """Which entry slot holds immOff / len, for the dyn widths."""
    return {
        "kBudgetLeaDisp8Sites": 1,       # {site, immOff, stock}
        "kMasterNotchSites": 1,          # {site, immOff, op0, op1, stock}
        "kDataViewLegendLeaSites": 1,
        "kDataViewLegendImm32Sites": 1,
        "kGraphLegendBlocks": 1,         # {site, len, kind, name}
    }.get(name)


def width_for(name, entry):
    spec = WIDTHS[name][0]
    if isinstance(spec, int):
        return spec
    idx = field_index(name)
    if idx is None or "vals" not in entry or len(entry["vals"]) <= idx:
        return None
    v = entry["vals"][idx]
    if spec == "dyn:immOff+1":
        return v + 1
    if spec == "dyn:immOff+4":
        return v + 4
    if spec == "dyn:len":
        return v
    return None


def parse_ownership(director_src):
    """table-name -> ini flag, derived from the DIRECTOR's actual call sites.

    The gating condition is `settings.spikeScaleAll && settings.spikeXxxPatch`,
    so the SPECIFIC flag is the one that is NOT ScaleAll. An earlier version of
    this function took the first match and therefore labelled every family
    "ScaleAll" - which made CHECK B structurally incapable of reporting a split
    and printed a green that could not have been red. Kept as a comment because
    it is the same failure mode this gate exists to catch: an instrument whose
    negative result is guaranteed by construction.
    """
    body = strip_comments(director_src)
    applier_flag = {}
    for m in re.finditer(r"CodePatches::(Apply\w+)\s*\(", body):
        applier = m.group(1)
        if applier in applier_flag:
            continue
        # Walk back to the nearest enclosing `if (...)` and read every flag in it.
        head = body[max(0, m.start() - 400):m.start()]
        conds = re.findall(r"settings\.spike(\w+)", head)
        specific = [c for c in conds if c != "ScaleAll"]
        if specific:
            applier_flag[applier] = specific[-1]
        elif conds:
            applier_flag[applier] = conds[-1]
    # Which applier iterates which table (read from CodePatches, not guessed).
    cp = strip_comments(read(CODEPATCHES))
    table_applier = {}
    for fm in re.finditer(r"\b(Apply\w+)\s*\(\s*float[^)]*\)\s*\{", cp):
        start = fm.end()
        depth, i = 1, start
        while i < len(cp) and depth:
            if cp[i] == "{":
                depth += 1
            elif cp[i] == "}":
                depth -= 1
            i += 1
        fnbody = cp[start:i]
        for t in WIDTHS:
            if re.search(r"\b" + t + r"\b", fnbody):
                table_applier.setdefault(t, fm.group(1))
    owner = {}
    for t, ap in table_applier.items():
        owner[t] = applier_flag.get(ap, "(ungated:%s)" % ap)
    return owner, table_applier


def main():
    if not os.path.exists(CODEPATCHES):
        print("FATAL: cannot find %s" % CODEPATCHES)
        return 2
    cp_src = read(CODEPATCHES)
    tables = parse_tables(cp_src)
    owner, table_applier = parse_ownership(read(DIRECTOR))

    # ---- anti-rot: every parsed site table must be registered ----
    unregistered = sorted(t for t in tables if t not in WIDTHS)
    for t in unregistered:
        fail("UNREGISTERED TABLE %s (%d entries) - add it to WIDTHS with its "
             "encoding width, or this gate is silently blind to a whole family."
             % (t, len(tables[t])))
    missing = sorted(t for t in WIDTHS if t not in tables)
    for t in missing:
        NOTES.append("registered but not found in source: %s (renamed or removed?)" % t)

    # ---- CHECK A: byte overlap across families ----
    spans = []   # (lo, hi, table, family)
    unknown_width = []
    for name, entries in sorted(tables.items()):
        if name not in WIDTHS or name in RDATA_TABLES:
            continue
        fam = owner.get(name, "(unowned)")
        for e in entries:
            w = width_for(name, e)
            if w is None:
                unknown_width.append((name, e["site"]))
                continue
            spans.append((e["site"], e["site"] + w, name, fam))
    for name, site in unknown_width:
        fail("cannot derive width for %s site 0x%08X - the dyn field is missing, "
             "so this site is UNCHECKED" % (name, site))

    spans.sort()
    overlaps = 0
    for i in range(len(spans) - 1):
        lo1, hi1, t1, f1 = spans[i]
        for j in range(i + 1, len(spans)):
            lo2, hi2, t2, f2 = spans[j]
            if lo2 >= hi1:
                break
            if _are_alternates(t1, t2):
                print("  note: %s / %s overlap by design (mutually exclusive "
                      "encodings of one patch) - not a double-write" % (t1, t2))
                continue
            overlaps += 1
            sev = "CROSS-FAMILY" if f1 != f2 else "same-family"
            msg = ("%s OVERLAP 0x%08X..0x%08X (%s/%s) vs 0x%08X..0x%08X (%s/%s)"
                   % (sev, lo1, hi1, t1, f1, lo2, hi2, t2, f2))
            if f1 != f2:
                fail(msg)
            else:
                fail(msg + "  [same family, still a double-write]")

    print("CHECK A - byte overlap")
    print("  %d site spans across %d tables, %d families"
          % (len(spans), len({s[2] for s in spans}), len({s[3] for s in spans})))
    print("  overlaps: %d" % overlaps)

    # ---- CHECK B: split ownership within one 4KB builder neighbourhood ----
    # Constants a single builder consumes live close together. Bucketing by
    # 4KB is a heuristic PROXY for "same builder" - it is deliberately coarse,
    # and every hit is a QUESTION, not a defect.
    buckets = {}
    for lo, hi, t, f in spans:
        buckets.setdefault(lo >> 12, set()).add(f)
    split = {k: v for k, v in buckets.items() if len(v) > 1}
    print("\nCHECK B - split ownership (STRUCTURAL FLAG, not a defect proof)")
    print("  %d of %d 4KB regions carry constants owned by >1 ini flag:"
          % (len(split), len(buckets)))
    for k in sorted(split):
        fams = sorted(split[k])
        tabs = sorted({t for lo, hi, t, f in spans if (lo >> 12) == k})
        print("    0x%08X..0x%08X  flags={%s}" % (k << 12, ((k + 1) << 12) - 1,
                                                  ", ".join(fams)))
        if VERBOSE:
            print("        tables: %s" % ", ".join(tabs))
    print("  These are CONFIGURATIONS A USER CAN REACH where one builder's")
    print("  constants are half-scaled. #104 lives somewhere in this space.")
    print("  Flagging is not proof: confirm on screen before changing anything.")

    print("\nOWNERSHIP (derived from the director's call sites, not hand-kept)")
    for t in sorted(table_applier):
        print("  %-28s %-26s %s" % (t, table_applier[t], owner.get(t, "?")))

    for n in NOTES:
        print("\nNOTE: %s" % n)

    if FAILURES:
        print("\n%d FAILURE(S):" % len(FAILURES))
        for f in FAILURES:
            print("  FAIL %s" % f)
        return 1
    print("\nPASS - no byte overlap, every site table registered.")
    print("Reminder: Check B findings above are UNRESOLVED BY DESIGN. This gate")
    print("proves the bytes do not collide; it does not prove the CONFIGURATIONS")
    print("are safe. 2026-08-30: this line used to cite #104 as the open proof")
    print("of that - #104 was a teardown spin in the game's own destructors and")
    print("is CURED (SpinFix, default ON); it was never a patch-family defect.")
    print("The standing example is 0x0077C9A2 / 0x0077CE44, where ONE creation")
    print("call takes y from BudgetDeptPatch and x from OrdinanceInsetPatch -")
    print("Check B sees only the 4KB neighbourhood, never the call site.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
