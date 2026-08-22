"""geomextra.py - the three geometry recorders census.py did not have.

STAGE 1.5. Added 2026-08-03 for task #96 (crosscheck's 12 MISSES).

`census.py` records geometry only where it arrives through (a) a named
primitive's push run or (b) a cIGZWin `SetSize` / `SetArea(l,t,r,b)` /
`SetPosition` call. Three shapes carry real, patched geometry and fit
neither:

  A. SetArea(const Rect*)  - vt+0xD8 takes a POINTER. The constants that
     built the rect are the four dword stores into the stack local the
     `lea` points at. Recovering them is the "rect-store resolver" named
     as missing in tools\\research\\_incoming\\sdkgaps-01.md OPEN #2.

     ⛔ The forbidden shortcut (sdkgaps-01.md blind spot 2): mapping
     0xD8's single argument to l/t/r/b. At 0x7A082C the pushed value is
     `lea ecx,[esp+0x90]`, which classify() reads as value=0x90 - a
     STACK FRAME OFFSET. Publishing that as "geometry constant 144" is
     a phantom. This module never records the pointer; it records only
     the four stores it resolves, and records NOTHING when it cannot
     resolve all four.

  B. Measure-relative geometry - an immediate applied to the RESULT of a
     cIGZWin size getter. `GetW` is vt+0xA4 and `GetH` is vt+0xA8
     (tools\\research\\SC4-UI-ENGINE.md:249 and DYNAMIC-CONTROLS.md:261,
     from the community cIGZWin.h confirmed against game code - an
     instrument INDEPENDENT of this scan). A value added to or
     subtracted from a measured window dimension is geometry by
     construction: it is a margin. Examples:
         0x79388F  call [edx+0xA4] -> sub esi,0x3D   right reserve W-61
         0x7A07F3  call [eax+0xA4] -> add eax,0x173  legend chip R = L+W
     The rule is deliberately TIGHT: the immediate must act on the
     register that directly received the getter's return value, with no
     intervening write. A looser walk would sweep up every arithmetic
     constant in the function.

  C. Foreign (non-cIGZWin) geometry slots - a documented size-setting
     method on another class. Only one is named today:
         0xAB6D28 +0x30  SetItemMetrics(w, h, gap)
     writing strip[0xF8/0xFC/0x100] (tools\\uimap\\SUBFLYOUT-BUILDER.md:70,
     decoded from sub_79A0E0 - again independent of CodePatches).

     ⚠ SCOPE, AND WHY IT IS NARROW. Slot 0x30 is not reserved: MEASURED,
     the 12 pre-existing census builders contain 14 `call [reg+0x30]`
     sites, none of them this API. Recognising 0x30 everywhere would
     FABRICATE 14 constants. So this recorder is gated on an explicit
     owner allowlist (FOREIGN_SLOT_OWNERS) and every member carries the
     evidence that fixes its receiver class. That is a real narrowing and
     it is reported by crosscheck.py, not hidden.

Nothing in this module reads src\\CodePatches.cpp. Everything is derived
from the exe plus our own decodes, so crosscheck stays a comparison of
two independent enumerations rather than a copy checking itself.
"""
import re

import common as C
import argscan as A

# cIGZWin size getters. Independent source: SC4-UI-ENGINE.md:249.
MEASURE_SLOTS = {0xA4: ("GetW", "w"), 0xA8: ("GetH", "h")}

# Non-cIGZWin geometry methods, keyed by vtable slot.
FOREIGN_SLOTS = {
    0x30: dict(name="SetItemMetrics", arity=3, roles=["w", "h", "gap"],
               vtable=0xAB6D28,
               evidence="SUBFLYOUT-BUILDER.md:70 - sub_79A0E0 writes "
                        "strip[0xF8/0xFC/0x100] from these three args"),
    # 0xCC is cIGZWin::SetW per SC4-UI-ENGINE.md:249 (community cIGZWin.h
    # confirmed against game code). It lives HERE and not in census VT_NAME
    # because the slot is NOT reserved across classes: in sub_76D3D0 the
    # `call [edx+0xCC]` at 0x76E220 is the legend SWATCH ALLOCATOR on iface
    # vt 0x00ADE0DC (SC4-UI-ENGINE.md:1911) - recording that arg as a width
    # would fabricate a constant. Per-owner gating is the scope.
    0xCC: dict(name="SetW", arity=1, roles=["w"], vtable=None,
               evidence="SC4-UI-ENGINE.md:249 - SetW +0xCC on cIGZWin; "
                        "receiver proven per allowlisted owner below"),
}

# Owners whose foreign-slot receivers are PROVEN, and WHICH slots are proven
# there. 2026-08-04: restructured from owner->note to owner->(slots, note) -
# slot 0xCC joined and it must not apply to the 0x30 owners (nor 0x30 to the
# 0xCC owner) without its own proof; a flat owner list would have granted
# every listed owner every listed slot, which is the two-powers trap
# (scaling law: "a list can grant TWO powers").
FOREIGN_SLOT_OWNERS = {
    0x7EAEB0: dict(slots=(0x30,),
                   why="sub-flyout provider - strip built at 0x7EAF05 via "
                       "[edx+0xC] then SetItemMetrics at 0x7EAEF7 "
                       "(SUBFLYOUT-BUILDER.md:91)"),
    0x7E7270: dict(slots=(0x30,),
                   why="first-level flyout builder - carries the SAME three "
                       "constants at 0x7E72A4/A6/A8 and is deliberately NOT "
                       "patched by CodePatches (SUBFLYOUT-BUILDER.md:201). "
                       "It is censused so the model can SEE the unpatched "
                       "twins."),
    0x7E8510: dict(slots=(0xCC,),
                   why="MAYOR RATING BAR builder (the kRatingImulSites "
                       "skip, resolved 2026-08-04). Receiver: the bar child "
                       "window returned by `call [obj+0xC]` immediately "
                       "before each SetW - `imul reg,reg,7; push; call "
                       "[edx+0xCC]` at 0x7E87B1/0x7E89D7 sets the bar WIDTH "
                       "to rating*7px. Independent corroboration: the "
                       "runtime fix that doubles this exact multiplier "
                       "renders the bar correctly on screen (v2.37.1, "
                       "user-confirmed task #72)."),
}

# ---------------------------------------------------------------------------
# Recorders D and E (2026-08-04, Phase 1a - the #57 deferral).
#
# sub_76D3D0 (GRAPHS panel builder) computes the legend row geometry in two
# shapes census.py's other recorders cannot see, MEASURED from the stock exe
# (capstone disasm of the whole owner; every VA below verified there):
#
#   D. OBJECT-MEMBER geometry stores - imm arithmetic whose result lands in
#      a small member offset of an object under construction:
#          76E233  lea ecx,[eax+3]   -> 76E242  mov [ebp+0xc], ecx
#          76E239  add eax,9         -> 76E245  mov [ebp+0x14], eax
#          76E23C  add ebx,0xa       -> 76E23F  mov [ebp+0x10], ebx
#          76E2AF  add ecx,4         -> 76E2B2  mov [edi+0x1c], ecx
#          76E2C8  sub edx,4         -> 76E2CB  mov [edi+0x24], edx
#      ebp/edi are OBJECT pointers here, not frame pointers (the function is
#      FPO - it addresses its frame via esp, and ebp is loaded from an
#      allocation result at 76E22D). The rule stays TIGHT: the imm-arith
#      register must reach a `mov dword ptr [reg+disp], r` with disp in
#      [4, 0x7C] within a short forward window, with no intervening write to
#      it and no intervening call.
#
#   E. STACK-PAIR-DIFFERENCE insets - an immediate applied to the difference
#      of two stack slots. `[esp+0x50] - [esp+0x48]` is a width by
#      construction (right minus left of the same rect), so the imm is a
#      geometry inset the same way recorder B's GetW-relative imms are:
#          76E0F5  sub ebx,0x6a   (ebx = [esp+0x50]-[esp+0x48])
#          76E159  lea ecx,[edx-0x5c]  and  76E162  add edx,-0x6c
#          76E1F8  sub ebx,0x5a
#          76E2C8  sub edx,4      (ALSO derived by D - real corroboration,
#                                  two independent walks, same bytes)
#
# Both are gated on an explicit owner allowlist, exactly like
# FOREIGN_SLOT_OWNERS and for the same reason: applied blindly to every
# censused builder, D would record every struct field assignment and E every
# pointer-difference in the exe. The allowlist is the scope, and crosscheck
# reports it.
#
# Nothing here reads src\CodePatches.cpp. The five member stores and three
# pair-diff runs were decoded from the exe bytes; that the recorded sites
# coincide with kGraphLegendImmSites / kGraphLegendBlocks is the CROSSCHECK
# working, not the input.
MEMBER_STORE_OWNERS = {
    0x76D3D0: "GRAPHS panel builder - legend row objects built by direct "
              "member stores; ebp/edi hold heap objects (FPO function, "
              "frame is esp-relative). Decoded 2026-08-04 for the #57 "
              "deferral; see the recorder D/E note above.",
    0x7E8510: "MAYOR RATING BAR builder (the kRatingImulSites skip). Two of "
              "its three imuls feed SetW directly (recorded via "
              "FOREIGN_SLOT_OWNERS); the third - `imul ecx,ecx,7; add "
              "ecx,edi; push ecx; call [edx+0xE0]` at 0x7E8A02 - refines "
              "the product with a register base before pushing it as a "
              "GZWinMoveTo coordinate, which is why recorder D follows "
              "add/sub-REGISTER refinements and accepts a push terminal.",
}

_MEMBER_STORE = re.compile(
    r"^dword ptr \[(e[a-z][a-z]) \+ (0x[0-9a-f]+|\d+)\], (e[a-z][a-z])$")
_ESP_LOAD = re.compile(
    r"^(e[a-z][a-z]), dword ptr \[esp(?: \+ (0x[0-9a-f]+))?\]$")

_IMM_ENCS = ("add_imm8", "add_imm32", "sub_imm8", "sub_imm32",
             "lea_disp8", "lea_disp32", "imul_imm8")


def _imm_arith_dst(ins):
    """(dstReg, classify-dict) if ins is imm arithmetic in PATCHABLE shape."""
    if ins.mnemonic in ("add", "sub", "imul") and "," in ins.op_str:
        dst = ins.op_str.split(",")[0].strip()
        if dst in A.REG32:
            d = A.classify(ins, dst)
            if d.get("enc") in _IMM_ENCS and d.get("value") is not None:
                return dst, d
    if ins.mnemonic == "lea":
        m = re.match(r"^(e[a-z][a-z]), \[(e[a-z][a-z])( [+-] .+)?\]$",
                     ins.op_str)
        if m and m.group(2) != "esp":
            d = A.classify(ins, m.group(1))
            if d.get("enc") in _IMM_ENCS and d.get("value") is not None:
                return m.group(1), d
    return None, None


def member_imm_stores(insns, owner, fm=None):
    """Recorder D. Yields classify-dicts with 'member' = (baseReg, disp,
    storeVA). Allowlisted owners only."""
    if owner not in MEMBER_STORE_OWNERS:
        return []
    out = []
    for k, ins in enumerate(insns):
        reg, d = _imm_arith_dst(ins)
        if reg is None:
            continue
        j = k + 1
        while j < len(insns) and j - k <= 8:
            ins2 = insns[j]
            if ins2.mnemonic == "call":
                break
            if ins2.mnemonic == "mov":
                m = _MEMBER_STORE.match(ins2.op_str)
                if m and m.group(3) == reg and m.group(1) != "esp":
                    disp = int(m.group(2), 0)
                    if 4 <= disp <= 0x7C:
                        rec = dict(d)
                        rec["member"] = [m.group(1), disp,
                                         "0x%X" % ins2.address]
                        rec["role"] = "m%02X" % disp
                        out.append(rec)
                    break
            # push terminal (0x7E8510's third imul): the value leaves as a
            # call argument. Role stays opaque - the arg's meaning belongs
            # to the callee, and claiming one is how a wrong unit ships.
            if ins2.mnemonic == "push" and ins2.op_str.strip() == reg:
                rec = dict(d)
                rec["role"] = "pushed"
                rec["pushSite"] = "0x%X" % ins2.address
                out.append(rec)
                break
            # add/sub with a REGISTER source refines the value but the imm
            # stays a factor of it - keep following (the 0x7E8A02 shape:
            # imul ecx,ecx,7; add ecx,edi; push ecx).
            dst = ins2.op_str.split(",")[0].strip() if "," in ins2.op_str \
                else ins2.op_str.strip()
            if dst == reg and ins2.mnemonic in ("add", "sub") \
                    and "," in ins2.op_str \
                    and ins2.op_str.split(",")[1].strip() in A.REG32:
                j += 1
                continue
            # any other write to the register kills the chain
            if dst == reg and ins2.mnemonic not in ("cmp", "test", "push"):
                break
            j += 1
    return out


def stack_pair_diff_imms(insns, owner, fm=None):
    """Recorder E. Immediates applied to the difference of two stack slots.

    Tracks registers loaded from [esp+disp]; `sub Ra, Rb` of two DIFFERENT
    tracked slots marks Ra as a pair-difference; add/sub imm or lea [Ra+d]
    while the mark holds records the imm. Any other write clears the state.
    Allowlisted owners only (see the scope note)."""
    if owner not in MEMBER_STORE_OWNERS:
        return []
    out = []
    slot_of = {}    # reg -> esp disp it was loaded from
    diff = set()    # regs currently holding a pair difference
    for ins in insns:
        ops = ins.op_str
        if ins.mnemonic == "call":
            slot_of.clear()
            diff.clear()
            continue
        if ins.mnemonic == "mov":
            m = _ESP_LOAD.match(ops)
            if m:
                slot_of[m.group(1)] = int(m.group(2), 0) if m.group(2) else 0
                diff.discard(m.group(1))
                continue
        if ins.mnemonic == "sub" and "," in ops:
            a, b = [s.strip() for s in ops.split(",", 1)]
            if a in slot_of and b in slot_of and slot_of[a] != slot_of[b]:
                diff.add(a)
                slot_of.pop(a, None)
                continue
        reg, d = _imm_arith_dst(ins)
        if reg is not None:
            src_reg = reg
            if ins.mnemonic == "lea":
                m = re.match(r"^e[a-z][a-z], \[(e[a-z][a-z])", ops)
                src_reg = m.group(1) if m else reg
            if src_reg in diff:
                rec = dict(d)
                rec["role"] = "wdiff"
                rec["pairDiff"] = True
                out.append(rec)
                if ins.mnemonic == "lea" and reg != src_reg:
                    pass          # source keeps its mark; dst is derived
                continue
        # generic kill: a write from anything else clears both states
        if "," in ops:
            dst = ops.split(",")[0].strip()
            if dst in A.REG32 and ins.mnemonic not in ("cmp", "test", "push"):
                if not (ins.mnemonic in ("add", "sub") and dst in diff):
                    slot_of.pop(dst, None)
                    diff.discard(dst)
    return out

RECT_SLOT = 0xD8
RECT_ROLES = ["l", "t", "r", "b"]

_ESP_STORE_REG = re.compile(
    r"^dword ptr \[esp(?: \+ (0x[0-9a-f]+))?\], (e[a-z][a-z])$")
_ESP_STORE_IMM = re.compile(
    r"^dword ptr \[esp(?: \+ (0x[0-9a-f]+))?\], (-?(?:0x[0-9a-f]+|\d+))$")
_LEA_ESP = re.compile(r"^(e[a-z][a-z]), \[esp(?: \+ (0x[0-9a-f]+))?\]$")


def _push_before(insns, idx):
    """Index of the push that supplied the single arg of insns[idx]."""
    i = idx - 1
    while i >= 0 and idx - i < 8:
        if insns[i].mnemonic == "push":
            return i
        if insns[i].mnemonic in ("call", "ret", "jmp"):
            return None
        i -= 1
    return None


def rect_base(insns, idx):
    """(disp, leaIdx) of the stack rect a `call [r+0xD8]` at idx points at.

    Returns None when the pointer is not a stack local - a rect held in an
    object field is out of this resolver's reach and must stay unrecorded.
    """
    p = _push_before(insns, idx)
    if p is None:
        return None
    d = A.classify(insns[p])
    if d["enc"] == "push_reg":
        reg = insns[p].op_str.strip()
        j = p - 1
        while j >= 0 and p - j < 12:
            ins = insns[j]
            if ins.mnemonic == "lea":
                m = _LEA_ESP.match(ins.op_str)
                if m and m.group(1) == reg:
                    return (int(m.group(2), 0) if m.group(2) else 0), j
            if ins.op_str.split(",")[0].strip() == reg and \
                    ins.mnemonic not in ("cmp", "test", "push"):
                return None
            j -= 1
    return None


def resolve_rect(insns, idx, fm):
    """Recover l/t/r/b for the `call [r+0xD8]` at insns[idx].

    Returns (members, why) - members is {role: classify-dict} and is EMPTY
    unless all four were resolved. `why` explains an empty result so the
    null is never silently indistinguishable from "no constants here".
    """
    rb = rect_base(insns, idx)
    if rb is None:
        return {}, "rect pointer is not a `lea r,[esp+disp]` stack local"
    disp, leaIdx = rb
    want = {disp + 4 * m: RECT_ROLES[m] for m in range(4)}
    found = {}
    delta = 0
    i = leaIdx - 1
    n = 0
    while i >= 0 and n < 300 and len(found) < 4:
        ins = insns[i]
        n += 1
        if ins.mnemonic == "mov":
            mi = _ESP_STORE_IMM.match(ins.op_str)
            mr = _ESP_STORE_REG.match(ins.op_str)
            m = mi or mr
            if m:
                k = (int(m.group(1), 0) if m.group(1) else 0) + delta
                role = want.get(k)
                if role and role not in found:
                    if mi:
                        # the constant is IN the store: mov [esp+d], imm32
                        rec = A.classify(ins)
                    else:
                        rec = A.resolve_reg(insns, i, m.group(2), 0, 120)
                    if rec and rec.get("value") is not None and \
                            rec.get("immOff") is not None:
                        rec = dict(rec)
                        rec["rectStore"] = "0x%X" % ins.address
                        found[role] = rec
        delta += A._esp_delta_step(ins, None, fm)
        i -= 1
    if len(found) < 4:
        return {}, ("only %d of 4 rect members resolved (%s) - recording "
                    "none; a partial rect is not a model of a rect"
                    % (len(found), ",".join(sorted(found)) or "-"))
    return found, ""


def measure_relative(insns, fm):
    """Immediates applied directly to a GetW/GetH return value.

    Yields classify-dicts with 'measure' = ('GetW'|'GetH', callVA).
    """
    out = []
    for k, ins in enumerate(insns):
        if ins.mnemonic != "call" or ins.op_str.startswith("0x"):
            continue
        m = re.search(r"\+ (0x[0-9a-f]+)\]", ins.op_str)
        if not m:
            continue
        slot = int(m.group(1), 0)
        if slot not in MEASURE_SLOTS:
            continue
        gname, grole = MEASURE_SLOTS[slot]
        # the return value lives in eax; follow it until eax is rewritten
        live = {"eax"}
        j = k + 1
        while j < len(insns) and j - k < 14 and live:
            ins2 = insns[j]
            ops = ins2.op_str
            dst = ops.split(",")[0].strip() if "," in ops else ops.strip()
            if ins2.mnemonic == "call":
                break
            base = None
            mb = re.search(r"\[(e[a-z][a-z])", ops)
            if ins2.mnemonic == "lea" and mb:
                base = mb.group(1)
            elif ins2.mnemonic in ("add", "sub", "imul"):
                base = dst
            if base in live:
                d = A.classify(ins2, dst)
                if d.get("value") is not None and d.get("immOff") is not None \
                        and d["enc"] in ("add_imm8", "add_imm32", "sub_imm8",
                                         "sub_imm32", "lea_disp8",
                                         "lea_disp32", "imul_imm8"):
                    d = dict(d)
                    d["measure"] = [gname, "0x%X" % ins.address]
                    d["role"] = grole
                    out.append(d)
            # propagate / kill liveness
            if ins2.mnemonic == "mov" and ops.count(",") == 1:
                src = ops.split(",")[1].strip()
                if src in live and dst in A.REG32:
                    live.add(dst)
                elif dst in live:
                    live.discard(dst)
            elif dst in live and ins2.mnemonic not in ("cmp", "test", "push"):
                if ins2.mnemonic in ("add", "sub", "imul", "lea"):
                    pass          # still measure-derived
                else:
                    live.discard(dst)
            j += 1
    return out


def foreign_slot_calls(insns, owner, fm=None):
    """SetItemMetrics/SetW-style calls, ONLY in allowlisted (owner, slot)
    pairs - see the two-powers note on FOREIGN_SLOT_OWNERS."""
    grant = FOREIGN_SLOT_OWNERS.get(owner)
    if not grant:
        return []
    out = []
    for k, ins in enumerate(insns):
        if ins.mnemonic != "call" or ins.op_str.startswith("0x"):
            continue
        m = re.search(r"\+ (0x[0-9a-f]+)\]", ins.op_str)
        if not m:
            continue
        slot = int(m.group(1), 0)
        if slot not in grant["slots"]:
            continue
        spec = FOREIGN_SLOTS.get(slot)
        if not spec:
            continue
        args, inc = A.call_args(insns, k, spec["arity"], fm)
        out.append({"site": ins.address, "op": spec["name"], "slot": slot,
                    "incomplete": inc, "args": args,
                    "roles": spec["roles"]})
    return out
