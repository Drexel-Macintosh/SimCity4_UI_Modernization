"""constants.py - STAGE 2: the CONSTANT MAP.

For every builder found by census.py, every immediate that feeds an
x / y / width / height / margin, WITH ITS ENCODING and its twin site.

    input  : builders.json  (census.py)
    output : constants.json, CONSTANT-MAP.md

WHY ENCODING IS THE POINT (METHOD.md §4.4)
    The same x arrives as `push imm8`, `push imm32`, `sub r32,imm8`,
    `sub r32,imm32`, `lea r32,[r32+disp8]`, `add r32,imm32`.  A scan for
    one encoding finds one copy - and `imm8`/`disp8` cap at 127, so a
    value that cannot re-encode needs a runtime pin instead of a patch.
    Every site below therefore carries enc, immOff, immSize, the expected
    original bytes, and a `ceiling` verdict at the requested factor.

WHY TWINS ARE THE POINT (laws 15/16)
    Many creates exist twice - group-1 / group-2 branches, one of them
    dead for a given department.  A patch that "did nothing" hit the dead
    one.  Twin sets are computed mechanically here:
    same owner + same primitive + same arg role + same value + same
    encoding  =>  one twin group; the project's rule is to patch all
    members (patching a dead site is harmless, missing the live one is
    not).

Work units: one per builder function, written to _work/constants/*.json
after each, so an interruption costs at most one builder.

Usage:
    python constants.py --resume [--factor 2.0]
"""
import os
import sys
from collections import defaultdict

import common as C
import argscan as A

# "gap" joins the set for task #96: SetItemMetrics(w, h, gap) - the strip
# row spacing is a patched geometry constant (kSubFlyoutProviderSites) and
# the strip height is literally count*(cellH+gap)-gap, so a model that
# holds w and h but not gap cannot predict the strip.
GEOM_ROLES = {"x", "y", "w", "h", "l", "t", "r", "b", "gap"}

# Encodings whose immediate can be rewritten IN PLACE, and their field width.
PATCHABLE = {
    "push_imm8":  (1, "6A ii"),
    "push_imm32": (4, "68 ii ii ii ii"),
    "sub_imm8":   (1, "83 /5 ii"),
    "sub_imm32":  (4, "81 /5 ii ii ii ii"),
    "add_imm8":   (1, "83 /0 ii"),
    "add_imm32":  (4, "05 or 81 /0 ii ii ii ii"),
    "lea_disp8":  (1, "8D /r ii"),
    "lea_disp32": (4, "8D /r ii ii ii ii"),
    "mov_imm32":  (4, "B8+r ii ii ii ii"),
    "imul_imm8":  (1, "6B /r ii"),
    "or_imm8":    (1, "83 /1 ii"),
    "and_imm8":   (1, "83 /4 ii"),
}
CEILING = {1: 127, 4: 0x7FFFFFFF}

# Constants that live INSIDE the shared factories, not in a builder.
# Proven by reading each callee (VAs quoted); they apply to EVERY caller,
# which is exactly why they cannot be scoped per dialog.
HELPER_CONSTANTS = [
    dict(helper=0x779660, name="TextLabel wrap/anchor width", value=1000,
         site=0x77971A, enc="push_imm32",
         note="SetArea(l=r.right,t=r.top,r=1000,b=r.bottom). SHARED by all 86 "
              "TextLabel sites - align-6 labels position at x-windowWidth, so "
              "a blind change shifts every right-aligned column. Scope per "
              "call site (detour) or not at all. (BUDGET-DETAIL-ANATOMY §POPUP Q2)"),
    dict(helper=0x7798C0, name="Combo width", value=120, site=0x77992F,
         enc="lea_disp8",
         note="lea edi,[edx+0x78]. disp8 CEILING 127 -> 2x (240) CANNOT be "
              "encoded in place; shipped as a runtime width pin in UiSpike."),
    dict(helper=0x7798C0, name="Combo height", value=15, site=0x779927,
         enc="lea_disp8",
         note="lea edx,[ecx+0xf]. Same disp8 limit; 2x (30) DOES fit."),
    dict(helper=0x7794E0, name="Slider height", value=14, site=0x779548,
         enc="lea_disp8",
         note="lea edx,[ecx+0xe]. Shared by all 4 Slider sites; 2x (28) fits. "
              "NOT currently patched by CodePatches.cpp."),
]


def role_of(spec, i):
    a = spec["args"]
    return a[i] if i < len(a) else "a%d" % (i + 1)


def site_records(owner, label, prim_name, spec, row):
    """Geometry sites contributed by one primitive call."""
    out = []
    for i, arg in enumerate(row["args"]):
        role = role_of(spec, i)
        if role not in GEOM_ROLES:
            continue
        # the constant may be in the push itself, or in the instruction that
        # produced the pushed register
        cands = [arg]
        if arg.get("src"):
            cands.append(arg["src"])
        for c in cands:
            if c.get("enc") in PATCHABLE and c.get("value") is not None:
                out.append(dict(
                    va=c["site"], owner=owner, ownerLabel=label,
                    via="%s(arg%d)" % (prim_name, i + 1), role=role,
                    enc=c["enc"], value=c["value"],
                    immOff=c["immOff"], immSize=c["immSize"],
                    bytes=c["bytes"], insn=c["insn"], callSite=row["site"],
                    baseFrom=c.get("base_from")))
    return out


def rect_records(owner, label, rows):
    """l/t/r/b recovered from the stack rect a SetArea(const Rect*) points at.

    The 0xD8 argument itself is NEVER read here - it is a pointer, and
    classify() would report its `lea r,[esp+0x90]` as "value 144", a stack
    frame offset masquerading as a coordinate (sdkgaps-01.md blind spot 2).
    census.py -> geomextra.resolve_rect() already refused to emit anything
    unless all four member stores resolved, so an empty rectMembers is a
    recorded null, not a silent drop.
    """
    out = []
    for r in rows:
        if r["op"] != "SetAreaRect":
            continue
        for role, c in sorted(r.get("rectMembers", {}).items()):
            if c.get("enc") not in PATCHABLE or c.get("value") is None:
                continue
            out.append(dict(
                va=c["site"], owner=owner, ownerLabel=label,
                via="SetArea(Rect.%s)" % role, role=role,
                enc=c["enc"], value=c["value"], immOff=c["immOff"],
                immSize=c["immSize"], bytes=c["bytes"], insn=c["insn"],
                callSite=r["site"], baseFrom=c.get("base_from"),
                rectStore=c.get("rectStore")))
    return out


def mrel_records(owner, label, rows):
    """Immediates applied to a GetW (vt+0xA4) / GetH (vt+0xA8) result.

    A margin measured off the live window dimension. See geomextra.py for
    why the walk is kept tight (it must be the register that directly
    received the getter's return value).
    """
    out = []
    for c in rows:
        if c.get("enc") not in PATCHABLE or c.get("value") is None:
            continue
        out.append(dict(
            va=c["site"], owner=owner, ownerLabel=label,
            via="%s%+d" % (c["measure"][0], c["value"]
                           if c["enc"].startswith(("add", "lea"))
                           else -c["value"]),
            role=c["role"], enc=c["enc"], value=c["value"],
            immOff=c["immOff"], immSize=c["immSize"], bytes=c["bytes"],
            insn=c["insn"], callSite=int(c["measure"][1], 16),
            baseFrom="measure", measure=c["measure"]))
    return out


def memberimm_records(owner, label, rows):
    """Recorder D/E rows (geomextra.member_imm_stores / stack_pair_diff_imms).

    D rows carry 'member' = [baseReg, disp, storeVA] and role 'mNN' - an
    object member offset, deliberately NOT translated to x/y/w/h: claiming a
    semantic unit for an anonymous member is how a wrong unit ships (the
    kRatingImulSites lesson). E rows carry 'pairDiff' and role 'wdiff' - the
    imm is an inset on a width formed from two frame slots. Both are real,
    patchable geometry immediates; the emulator must treat the roles as
    opaque (they anchor coverage, not layout prediction - layout for this
    family is certified by the #57 oracle, Test-ChartLegendMath.ps1)."""
    out = []
    for c in rows:
        if c.get("enc") not in PATCHABLE or c.get("value") is None:
            continue
        rec = dict(
            va=c["site"], owner=owner, ownerLabel=label,
            via=("member[%s+0x%02X]" % (c["member"][0], c["member"][1]))
                if c.get("member") else "pairdiff",
            role=c["role"], enc=c["enc"], value=c["value"],
            immOff=c["immOff"], immSize=c["immSize"], bytes=c["bytes"],
            insn=c["insn"],
            callSite=int(c["member"][2], 16) if c.get("member") else c["site"],
            baseFrom="memberimm")
        if c.get("member"):
            rec["member"] = c["member"]
        if c.get("pairDiff"):
            rec["pairDiff"] = True
        out.append(rec)
    return out


def vt_records(owner, label, rows):
    out = []
    from census import VT_NAME
    for r in rows:
        # SetAreaRect is handled by rect_records(); SetItemMetrics carries
        # its own role list from geomextra.FOREIGN_SLOTS.
        if r["op"] == "SetAreaRect":
            continue
        roles = r.get("roles") or \
            {"SetSize": ["w", "h"], "SetArea": ["l", "t", "r", "b"],
             "SetPosition": ["x", "y"]}.get(r["op"], [])
        for i, arg in enumerate(r["args"]):
            role = roles[i] if i < len(roles) else "a%d" % (i + 1)
            if role not in GEOM_ROLES:
                continue
            cands = [arg]
            if arg.get("src"):
                cands.append(arg["src"])
            for c in cands:
                if c.get("enc") in PATCHABLE and c.get("value") is not None:
                    out.append(dict(
                        va=c["site"], owner=owner, ownerLabel=label,
                        via="%s(arg%d)" % (r["op"], i + 1), role=role,
                        enc=c["enc"], value=c["value"],
                        immOff=c["immOff"], immSize=c["immSize"],
                        bytes=c["bytes"], insn=c["insn"], callSite=r["site"],
                        baseFrom=c.get("base_from")))
    return out


CONFLICTS = []


def collapse_by_va(rows):
    """One INSTRUCTION = one patch site, however many ways we derived it.

    Task #96 gave four sites two independent derivations: the rect-store
    resolver reads the stack stores a `SetArea(const Rect*)` consumes, and
    the measure-relative rule reads the dataflow out of `GetW`/`GetH`.
    They are independent failure modes (different instruction shapes,
    different walks), so agreement is real corroboration - but two records
    for one VA would make gen_codepatches.py emit the same patch twice, and
    the second VerifiedWrite would then fail against bytes the first had
    already rewritten.

    So: collapse to one record, and ASSERT the derivations agree on the
    bytes to be written. A disagreement is a finding, not a tie to break -
    it is collected into CONFLICTS and reported loudly rather than silently
    resolved by ordering.
    """
    byva = {}
    for r in rows:
        v = r["va"]
        if v not in byva:
            byva[v] = r
            continue
        a = byva[v]
        same = (a["enc"], a["value"], a["immOff"], a["immSize"]) == \
               (r["enc"], r["value"], r["immOff"], r["immSize"])
        if not same:
            CONFLICTS.append((v, a["via"], a["enc"], a["value"],
                              r["via"], r["enc"], r["value"]))
        a.setdefault("alsoDerivedBy", []).append(r["via"])
        a["corroborated"] = same
    return [byva[k] for k in sorted(byva)]


def main():
    resume = "--resume" in sys.argv
    factor = 2.0
    for i, a in enumerate(sys.argv):
        if a == "--factor":
            factor = float(sys.argv[i + 1])
    st = C.State()
    outdir = C.ensure_work("constants")
    b = C.jload(os.path.join(C.HERE, "builders.json"))
    if b is None:
        raise SystemExit("builders.json missing - run census.py first")
    prims = {int(k, 16): v for k, v in b["primitives"].items()}

    allsites = []
    for ova in sorted(b["builders"], key=lambda x: int(x, 16)):
        d = b["builders"][ova]
        # v2: rect-store + measure-relative + foreign-slot records joined
        # this stage (task #96). Bumped so --resume cannot serve pre-#96
        # partials that were written without them.
        # v3 (2026-08-04): member-imm / pair-diff records joined (recorders
        # D+E, the #57 deferral) - bumped again for the same reason.
        unit = "b3_%s" % ova
        path = os.path.join(outdir, unit + ".json")
        if resume and st.done("constants", unit) and os.path.exists(path):
            allsites.extend(C.jload(path))
            continue
        owner = int(ova, 16)
        label = d.get("label") or "(unidentified)"
        recs = []
        for pname, rows in d["primitiveCalls"].items():
            spec = next(v for v in prims.values() if v["name"] == pname)
            for r in rows:
                r2 = dict(r)
                r2["site"] = int(r["site"], 16)
                recs.extend(site_records(owner, label, pname, spec, r2))
        recs.extend(vt_records(owner, label, d.get("vtGeom", [])))
        recs.extend(rect_records(owner, label, d.get("vtGeom", [])))
        recs.extend(mrel_records(owner, label, d.get("measureRel", [])))
        recs.extend(memberimm_records(owner, label, d.get("memberImm", [])))
        # de-dup: one instruction can feed two args (rare) - keep first
        seen, uniq = set(), []
        for r in sorted(recs, key=lambda r: r["va"]):
            k = (r["va"], r["role"], r["via"])
            if k in seen:
                continue
            seen.add(k)
            uniq.append(r)
        uniq = collapse_by_va(uniq)
        C.jdump(path, uniq)
        st.mark("constants", unit, "done", sites=len(uniq), owner=ova)
        allsites.extend(uniq)
        print("  %s  %-4d geometry constants   %s" % (ova, len(uniq), label))

    # ---------------- twin grouping ----------------
    groups = defaultdict(list)
    for r in allsites:
        groups[(r["owner"], r["via"].split("(")[0], r["role"], r["value"],
                r["enc"])].append(r["va"])
    twin_of = {}
    twin_groups = []
    for k, vas in groups.items():
        if len(vas) > 1:
            twin_groups.append({"owner": "0x%X" % k[0], "primitive": k[1],
                                "role": k[2], "value": k[3], "enc": k[4],
                                "sites": ["0x%X" % v for v in sorted(vas)]})
            for v in vas:
                twin_of[v] = sorted(set(vas) - {v})
    for r in allsites:
        r["twins"] = ["0x%X" % v for v in twin_of.get(r["va"], [])]

    # ---------------- ceiling verdict at the requested factor -------------
    for r in allsites:
        scaled = round(r["value"] * factor)
        cap = CEILING[r["immSize"]]
        r["scaledAt%g" % factor] = scaled
        r["fits"] = bool(scaled <= cap and scaled >= -cap - 1)
        r["ceiling"] = cap
        if not r["fits"]:
            r["ceilingNote"] = ("%s cannot hold %d (max %d) - clamp or use a "
                                "runtime pin" % (r["enc"], scaled, cap))

    out = {
        "exe": C.EXE_PROVENANCE, "imageBase": C.IMAGE_BASE, "factorUsedForVerdict": factor,
        "encodings": {k: {"immSize": v[0], "pattern": v[1],
                          "ceiling": CEILING[v[0]]} for k, v in PATCHABLE.items()},
        "helperConstants": [dict(hc, helper="0x%X" % hc["helper"],
                                 site="0x%X" % hc["site"])
                            for hc in HELPER_CONSTANTS],
        "twinGroups": sorted(twin_groups,
                             key=lambda g: (g["owner"], g["role"], g["value"])),
        "sites": sorted(allsites, key=lambda r: r["va"]),
    }
    for r in out["sites"]:
        r["va"] = "0x%X" % r["va"]
        r["owner"] = "0x%X" % r["owner"]
        r["callSite"] = "0x%X" % r["callSite"]
    C.jdump(os.path.join(C.HERE, "constants.json"), out)
    st.mark("constants", "assemble", "done", sites=len(allsites),
            twinGroups=len(twin_groups))
    print("constants.json: %d geometry constant sites, %d twin groups"
          % (len(allsites), len(twin_groups)))
    nofit = [r for r in out["sites"] if not r["fits"]]
    print("  %d site(s) cannot encode round(stock*%g)" % (len(nofit), factor))
    corro = [r for r in out["sites"] if r.get("alsoDerivedBy")]
    print("  %d site(s) derived TWICE by independent walks (%d agree)"
          % (len(corro), sum(1 for r in corro if r.get("corroborated"))))
    if CONFLICTS:
        print("  *** %d DERIVATION CONFLICT(S) - two walks disagree about the "
              "same instruction:" % len(CONFLICTS))
        for c in CONFLICTS:
            print("      %s  %s %s=%s  VS  %s %s=%s" % c)
    write_md(out, factor)
    st.mark("constants", "md", "done")


MD_HEAD = """# CONSTANT MAP - SimCity 4.exe 1.1.641.0 Steam (STAGE 2)

> GENERATED by `tools\\uimap\\constants.py`. Do not hand-edit; re-run.
> `python constants.py --resume --factor 2.0`
> C++ tables: `python gen_codepatches.py --factor 2.0 --out gen.txt`
>
> Every immediate that feeds an x / y / width / height / margin in every
> builder found by stage 1, **with its encoding** and **its twin site**.
> This is the generated replacement for the hand-enumerated tables in
> `src\\CodePatches.cpp`. It is a READ of the exe - nothing here has been
> shipped, and the live dump remains the authority.

## Why encoding, and why twins

`METHOD.md` 4.4: the same x arrives as `push imm8`, `push imm32`,
`sub r32,imm8`, `sub r32,imm32`, `lea r32,[r32+disp8]`, `add r32,imm32`.
**Scanning for one encoding finds one copy.** `imm8`/`disp8` also cap at
127, so a value that cannot re-encode needs a runtime pin, not a patch.

`METHOD.md` 4.3 (laws 15/16): the same create often exists twice, one
branch dead. A patch that "did nothing" hit the dead one. Twin sets below
are computed mechanically - same owner + same primitive + same arg role +
same value + same encoding - and the project's rule is to patch **all**
members: patching a dead site is harmless, missing the live one is not.

## Encodings seen, and their field limits

| encoding | bytes | field | max |
|---|---|---|---|
"""


def write_md(out, factor):
    L = [MD_HEAD.rstrip()]
    for k, v in sorted(out["encodings"].items()):
        used = sum(1 for s in out["sites"] if s["enc"] == k)
        if used:
            L.append("| `%s` | `%s` | %d byte | %d |" %
                     (k, v["pattern"], v["immSize"], v["ceiling"]))
    L += ["", "## Shared FACTORY constants - one site, EVERY caller", "",
          "These live inside the primitives themselves, so they cannot be "
          "scoped to one dialog. Two of them are `disp8` and therefore have "
          "a hard 127 ceiling.", "",
          "| what | value | site | encoding | note |", "|---|---|---|---|---|"]
    for hc in out["helperConstants"]:
        L.append("| %s | %d | `%s` | `%s` | %s |" %
                 (hc["name"], hc["value"], hc["site"], hc["enc"],
                  hc["note"].replace("\n", " ")))

    L += ["", "## Sites, by owning builder", ""]
    byowner = {}
    for s in out["sites"]:
        byowner.setdefault((s["owner"], s["ownerLabel"]), []).append(s)
    for (ova, label), rows in sorted(byowner.items(),
                                     key=lambda kv: int(kv[0][0], 16)):
        L.append("### `%s` - %s" % (ova, label))
        L.append("")
        L.append("| site | role | value | x%g | encoding | bytes | feeds | "
                 "twins | note |" % factor)
        L.append("|---|---|---|---|---|---|---|---|---|")
        for s in sorted(rows, key=lambda r: int(r["va"], 16)):
            note = s.get("ceilingNote", "")
            if s.get("baseFrom") == "mem_load":
                note = (note + " " if note else "") + "base is runtime (W/H/cursor)"
            if s["value"] == 0:
                note = (note + " " if note else "") + "zero - scaling is a no-op"
            L.append("| `%s` | %s | %d | %d | `%s` | `%s` | %s | %s | %s |" %
                     (s["va"], s["role"], s["value"],
                      round(s["value"] * factor), s["enc"], s["bytes"],
                      s["via"], " ".join("`%s`" % t for t in s["twins"]) or "-",
                      note))
        L.append("")

    L += ["## Twin groups", "",
          "| owner | primitive | role | value | encoding | sites |",
          "|---|---|---|---|---|---|"]
    for g in out["twinGroups"]:
        L.append("| `%s` | %s | %s | %d | `%s` | %s |" %
                 (g["owner"], g["primitive"], g["role"], g["value"], g["enc"],
                  " ".join("`%s`" % s for s in g["sites"])))
    L += ["", "## Known limits of this map (label these HYPOTHESIS-adjacent)",
          "",
          "1. It covers constants that reach a create through a **push**, a "
          "**register** written nearby, or **one stack local**. A constant "
          "that reaches geometry through an object field (`mov [esi+0x9C], "
          "eax` row cursors) or through more than one local hop is not "
          "listed.",
          "2. `SetArea(const Rect*)` (`vt+0xD8`) passes a pointer; the "
          "constants that built the rect are found only when they are "
          "register-traceable at the call.",
          "3. Twin detection is textual (same value+encoding+role+owner). It "
          "does not prove which twin is LIVE - offline that needs the "
          "branch condition, and the project's rule is to patch both.",
          "4. Only the budget family's primitives are enumerated. The "
          "candidate list in `BUILDER-CENSUS.md` 3 is the seed for the rest "
          "of the exe.", ""]
    with open(os.path.join(C.HERE, "CONSTANT-MAP.md"), "w",
              encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print("CONSTANT-MAP.md written")


if __name__ == "__main__":
    main()
