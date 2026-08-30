"""subflyout_builder.py - STAGE 2 extension: the SUB-FLYOUT builder family.

Offline and read-only with respect to the game: the exe is opened 'rb' by
common.py and never written.  No game file, no src\\*.cpp, no dist\\ file is
touched.  Nothing durable lives in the scratchpad.

WHAT IT COVERS
--------------
The shared second-level menu container `0x8A6E61E0` and its item strip
`0x8A2CAD8B` are created by ONE function, `sub_7EAEB0`, and its twin
`sub_7E7270` builds the first-level (disaster) flyout from the same two
classes with its own copies of every constant.  Neither window has a `.UI`
script; both are pure code.  Full derivation: `SUBFLYOUT-BUILDER.md`.

This module is the machine-readable half: it re-reads every site out of the
exe, ASSERTS the expected original bytes, computes round(stock*f) and the
field-ceiling verdict, and emits

    subflyout-builder.json                 (same site schema as constants.json)
    generated-subflyout-builder-<tier>.txt (C++ site-table TEXT; never edits .cpp)

USAGE
-----
    python subflyout_builder.py --resume --factor 2.0
    python subflyout_builder.py --factor 1.5 --out generated-subflyout-builder-1.5x.txt

Every unit is persisted to `subflyout-builder.state.json` IMMEDIATELY after it
finishes (atomic replace), so an interruption loses at most one unit.  It uses
its OWN state file, not the shared `state.json`, so it cannot disturb stages
1+2 or a sibling session.
"""
import json
import os
import sys
import time

import common as C

HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(HERE, "subflyout-builder.state.json")
JSON_OUT = os.path.join(HERE, "subflyout-builder.json")

# --------------------------------------------------------------------------
# encodings (same table as constants.json)
# --------------------------------------------------------------------------
ENC = {
    "push_imm8":  {"immSize": 1, "pattern": "6A ii",       "ceiling": 127, "floor": -128},
    "push_imm32": {"immSize": 4, "pattern": "68 ii*4",     "ceiling": 2147483647, "floor": -2147483648},
    "add_imm8":   {"immSize": 1, "pattern": "83 /0 ii",    "ceiling": 127, "floor": -128},
    "cmp_imm8":   {"immSize": 1, "pattern": "83 /7 ii",    "ceiling": 127, "floor": -128},
    "cmp_imm32":  {"immSize": 4, "pattern": "3D ii*4",     "ceiling": 2147483647, "floor": -2147483648},
    "mov_imm32":  {"immSize": 4, "pattern": "B8+r ii*4",   "ceiling": 2147483647, "floor": -2147483648},
}

# --------------------------------------------------------------------------
# THE SITE TABLE.
#
# Each row: (va, enc, immOff, expectedBytesHex, stock, owner, role, note, scale)
#   scale = True  -> a geometry constant; the applier writes round(stock*f)
#   scale = False -> policy / allocation / font id; NEVER scale (documented so
#                    the next reader does not "complete the set")
# --------------------------------------------------------------------------
SUB = "0x7EAEB0"   # second-level menu builder  (container 0x8A6E61E0)
TOP = "0x7E7270"   # first-level flyout builder (same classes, id 0)

OWNER_LABEL = {
    SUB: "SUB-FLYOUT builder - shared 2nd-level menu container 0x8A6E61E0 + strip 0x8A2CAD8B",
    TOP: "FIRST-LEVEL flyout builder (disaster / tool flyout) - same classes, container has NO id",
}

SITES = [
    # ---------------- sub_7EAEB0 : item metrics -> strip.SetItemMetrics (0x79A0E0)
    (0x7EAEF3, "push_imm8", 1, "6a2c", 44, SUB, "itemW",
     "SetItemMetrics arg1 -> strip[0xF8]; also the strip window's WIDTH "
     "(GetDesiredSize returns it verbatim) and the icon hit cell", True),
    (0x7EAEF1, "push_imm8", 1, "6a2c", 44, SUB, "itemH",
     "SetItemMetrics arg2 -> strip[0xFC]; row pitch = itemH + spacing", True),
    (0x7EAEEF, "push_imm8", 1, "6a05", 5, SUB, "itemSpacing",
     "SetItemMetrics arg3 -> strip[0x100]; stripH = (itemH+spacing)*n - spacing", True),

    # ---------------- sub_7EAEB0 : container layout fields -> 0x79AC60 (vt+0x10)
    (0x7EB169, "push_imm8", 1, "6a35", 53, SUB, "barW/claimW ([0xE4])",
     "arg2. Bar art width, drawn FLUSH RIGHT; ALSO the IsPointInMe claim width "
     "(0x79AE30 reads win+0xE0 == obj+0xE4). Feeds container WIDTH.", True),
    (0x7EB167, "push_imm8", 1, "6a19", 25, SUB, "barCapH/vMargin ([0xE8])",
     "arg3. Bar end-cap height AND the container's vertical padding: "
     "contentH = max(stripH,[0xF4]) + 2*[0xE8].", True),
    (0x7EB165, "push_imm8", 1, "6a50", 80, SUB, "ringW ([0xF0])",
     "arg4. Ring/keyring sprite width; container WIDTH = [0xF0]-[0xF8]+[0xE4].", True),
    (0x7EB163, "push_imm8", 1, "6a35", 53, SUB, "ringH/minContentH ([0xF4])",
     "arg5. Ring sprite height AND the floor on content height (the 258x206 "
     "minimum menu) AND the vertical centring datum.", True),
    (0x7EB161, "push_imm8", 1, "6a04", 4, SUB, "ringBarOverlap ([0xF8])",
     "arg6. Subtracted from the width sum: W = ringW - overlap + barW.", True),
    (0x7EB15F, "push_imm8", 1, "6a1b", 27, SUB, "xAnchor ([0xFC])",
     "arg7. left = spawnButtonAbsCentreX - [0xFC].", True),
    (0x7EB15D, "push_imm8", 1, "6a1d", 29, SUB, "yAnchor ([0x100])",
     "arg8. top datum = spawnButtonAbsCentreY - [0x100] (then centred+clamped).", True),

    # ---------------- sub_7EAEB0 : screen-edge margins -> 0x79AD00 (vt+0x14)
    (0x7EB183, "push_imm8", 1, "6a0a", 10, SUB, "topScreenMargin",
     "arg5 of the place call: top >= 10.", True),
    (0x7EB17B, "add_imm8", 2, "83c0f6", -10, SUB, "bottomScreenMargin",
     "arg6 = viewY - 10: top <= (viewY-10) - containerH.", True),

    # ---------------- sub_7EAEB0 : POLICY constants - documented, NEVER scaled
    (0x7EAF3D, "cmp_imm32", 1, "3d58020000", 600, SUB, "!viewHeightGate",
     "if view height <= 600 the visible row cap drops 8 -> 6. Screen pixels, "
     "not UI units: scaling it would CUT rows on a real 1600px screen.", False),
    (0x7EAF28, "cmp_imm8", 2, "83fb08", 8, SUB, "!maxRows",
     "row-count cap, not geometry.", False),
    (0x7EAF44, "cmp_imm8", 2, "83fb06", 6, SUB, "!maxRowsSmallScreen",
     "row-count cap, not geometry.", False),
    (0x7EAF1C, "cmp_imm8", 2, "83fb01", 1, SUB, "!minRows",
     "row-count floor, not geometry.", False),

    # ---------------- sub_7E7270 : the TWIN (first-level flyout)
    (0x7E72A8, "push_imm8", 1, "6a2c", 44, TOP, "itemW", "SetItemMetrics arg1 (twin of 0x7EAEF3).", True),
    (0x7E72A6, "push_imm8", 1, "6a2c", 44, TOP, "itemH", "SetItemMetrics arg2 (twin of 0x7EAEF1).", True),
    (0x7E72A4, "push_imm8", 1, "6a05", 5, TOP, "itemSpacing", "SetItemMetrics arg3 (twin of 0x7EAEEF).", True),
    (0x7E74A9, "push_imm8", 1, "6a35", 53, TOP, "barW/claimW ([0xE4])", "arg2 (twin of 0x7EB169, SAME value).", True),
    (0x7E74A7, "push_imm8", 1, "6a19", 25, TOP, "barCapH/vMargin ([0xE8])", "arg3 (twin of 0x7EB167, SAME value).", True),
    (0x7E74A5, "push_imm8", 1, "6a5e", 94, TOP, "ringW ([0xF0])", "arg4. First-level container W = 94-6+53 = 141.", True),
    (0x7E74A3, "push_imm8", 1, "6a3e", 62, TOP, "ringH/minContentH ([0xF4])", "arg5.", True),
    (0x7E74A1, "push_imm8", 1, "6a06", 6, TOP, "ringBarOverlap ([0xF8])", "arg6.", True),
    (0x7E749F, "push_imm8", 1, "6a28", 40, TOP, "xAnchor ([0xFC])", "arg7.", True),
    (0x7E749D, "push_imm8", 1, "6a22", 34, TOP, "yAnchor ([0x100])", "arg8.", True),
    (0x7E74C3, "push_imm8", 1, "6a0a", 10, TOP, "topScreenMargin", "twin of 0x7EB183.", True),
    (0x7E74BB, "add_imm8", 2, "83c0f6", -10, TOP, "bottomScreenMargin", "twin of 0x7EB17B.", True),
    (0x7E72DF, "cmp_imm8", 2, "83f806", 6, TOP, "!maxRows",
     "first-level flyouts are ALWAYS capped at 6 rows (no screen test).", False),
    (0x7E72D3, "cmp_imm8", 2, "83f801", 1, TOP, "!minRows", "row-count floor.", False),
]

# roles that pair across the two builders
TWIN_OF = {}
for _r in set(s[6] for s in SITES):
    _g = [s[0] for s in SITES if s[6] == _r]
    if len(_g) == 2:
        TWIN_OF[_g[0]] = ["0x%X" % _g[1]]
        TWIN_OF[_g[1]] = ["0x%X" % _g[0]]


# --------------------------------------------------------------------------
def load_state():
    if os.path.exists(STATE):
        try:
            with open(STATE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"units": {}}


def _atomic_write(path, text):
    """Atomic replace, with a retry + direct-write fallback.

    OneDrive/AV can hold a transient lock on the destination and make
    os.replace raise WinError 5; the state file is a resume aid, so a
    direct rewrite is an acceptable degradation - losing atomicity is
    strictly better than losing the run.
    """
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        f.write(text)
    for _ in range(5):
        try:
            os.replace(tmp, path)
            return
        except PermissionError:
            time.sleep(0.15)
    try:
        os.remove(tmp)
    except OSError:
        pass
    with open(path, "w") as f:
        f.write(text)


def save_state(st):
    _atomic_write(STATE, json.dumps(st, indent=1))


def sround(v, f):
    """round-half-away-from-zero, matching the CodePatches convention."""
    return int(v * f + (0.5 if v >= 0 else -0.5))


def build(factor, resume):
    st = load_state()
    out = []
    problems = []
    for (va, enc, immOff, want, stock, owner, role, note, scale) in SITES:
        unit = "site/0x%X" % va
        e = ENC[enc]
        raw = C.rd(va, len(want) // 2).hex()
        ok = (raw == want)
        if not ok:
            problems.append("0x%X expected %s got %s" % (va, want, raw))
        # read the immediate back out of the exe rather than trusting the table
        immBytes = C.rd(va + immOff, e["immSize"])
        got = int.from_bytes(immBytes, "little", signed=True)
        if got != stock:
            problems.append("0x%X imm expected %d got %d" % (va, stock, got))
        scaled = sround(stock, factor) if scale else stock
        fits = (e["floor"] <= scaled <= e["ceiling"])
        rec = {
            "va": "0x%X" % va,
            "owner": owner,
            "ownerLabel": OWNER_LABEL[owner],
            "via": "SetItemMetrics(0x79A0E0)" if "item" in role else (
                   "ContainerSetLayout(0x79AC60)" if "0x" in role else
                   "ContainerPlace(0x79AD00)"),
            "role": role,
            "enc": enc,
            "value": stock,
            "immOff": immOff,
            "immSize": e["immSize"],
            "bytes": raw,
            "note": note,
            "scale": scale,
            "twins": TWIN_OF.get(va, []),
            "scaled": scaled,
            "fits": fits,
            "ceiling": e["ceiling"],
            "verified": ok and got == stock,
        }
        out.append(rec)
        st["units"][unit] = {"status": "done" if rec["verified"] else "failed",
                             "ts": time.strftime("%Y-%m-%dT%H:%M:%S")}
        save_state(st)          # persist after EACH unit
    doc = {
        "exe": C.EXE_PROVENANCE,
        "imageBase": C.IMAGE_BASE,
        "factorUsedForVerdict": factor,
        "encodings": ENC,
        "builders": {
            SUB: {"extent": ["0x7EAEB0", "0x7EB320"],
                  "creates": ["0x8A6E61E0 (container, SetID @0x7EB121)",
                              "0x8A2CAD8B (strip, SetID @0x7EB1FB)"],
                  "containerWidth": 80 - 4 + 53,
                  "callers": ["0x7EC663", "0x7EC6C9", "0x7EC729", "0x7EDDC6",
                              "0x7F3B8B", "0x7F3D97", "0x7F4EE1"]},
            TOP: {"extent": ["0x7E7270", "0x7E75B0"],
                  "creates": ["container with NO id (anonymous)"],
                  "containerWidth": 94 - 6 + 53,
                  "callers": ["0x7F4D2C"]},
        },
        "geometryEngine": {
            "containerCtor": "0x79AFF0",
            "containerPrimaryVtable": "0xAB6D04",
            "containerWinVtable": "0xAB6AA8",
            "setLayout": "0x79AC60 (vt+0x10, ret 0x20, 8 args)",
            "place": "0x79AD00 (vt+0x14, ret 0x18, 6 args) - the ONLY SetArea",
            "getStripRect": "0x79B050 (vt+0x18) - copies obj[0x108..0x114]",
            "stripCtor": "0x79B500",
            "stripPrimaryVtable": "0xAB6D28",
            "stripWinVtable": "0xAB6D88",
            "setItemMetrics": "0x79A0E0 (vt+0x30)",
            "getDesiredSize": "0x79A620 (vt+0x34)",
            "formulas": {
                "stripW": "itemW",
                "stripH": "(itemH + spacing)*n - spacing",
                "containerW": "[0xF0] - [0xF8] + [0xE4]",
                "containerH": "max(stripH, [0xF4]) + 2*[0xE8]",
                "containerLeft": "btnAbsCentreX - [0xFC]",
                "containerTop": "clamp(([0xF4]>>1) - (containerH>>1) + btnAbsCentreY - [0x100])",
                "stripLeft": "containerW - (([0xE4] + stripW) >> 1) - 1",
                "stripTop": "(containerH - stripH) >> 1",
            },
        },
        "sites": out,
        "problems": problems,
    }
    _atomic_write(JSON_OUT, json.dumps(doc, indent=1))
    return doc


CPP_HEAD = """// ==========================================================
// GENERATED by tools\\uimap\\subflyout_builder.py - DO NOT HAND EDIT.
//   source : subflyout-builder.json
//   exe    : SimCity 4.exe 1.1.641.0 Steam, ImageBase 0x400000
//   factor : %(f)s   (values below are the STOCK numbers; the applier
//            writes round(stock * factor), exactly as the existing
//            CodePatches tables do)
//   family : the SHARED SUB-FLYOUT container 0x8A6E61E0 + strip 0x8A2CAD8B
//            (builder 0x7EAEB0) and its FIRST-LEVEL twin (builder 0x7E7270)
// Every entry lists its EXPECTED ORIGINAL BYTES: verify before write,
// mismatch = skip + log, never force.  (METHOD.md 4.5)
//
// !! READ SUBFLYOUT-BUILDER.md 7 BEFORE ENABLING THE 0x7E7270 BLOCK !!
// The first-level flyout is ALREADY scaled by ScaleGodFlyouts / the mayor
// dock. Patching its builder as well double-scales it.
// ==========================================================

struct Imm8Site    { uintptr_t site; uint8_t stock; };  // 6A ii
struct AddImm8Site { uintptr_t site; uint8_t stock; };  // 83 /0 ii
"""


def emit_cpp(doc, path):
    f = doc["factorUsedForVerdict"]
    L = [CPP_HEAD % {"f": ("%g" % f)}]
    for enc, struct, arr in (("push_imm8", "Imm8Site", "kSubFlyoutImm8Sites"),
                             ("add_imm8", "AddImm8Site", "kSubFlyoutAddImm8Sites")):
        rows = [s for s in doc["sites"] if s["enc"] == enc and s["scale"]]
        if not rows:
            continue
        L.append("\nconst %s %s[] = {" % (struct, arr))
        for owner in (SUB, TOP):
            grp = [s for s in rows if s["owner"] == owner]
            if not grp:
                continue
            L.append("\t// ---- %s  (builder %s) ----" % (OWNER_LABEL[owner], owner))
            for s in sorted(grp, key=lambda r: int(r["va"], 16)):
                warn = "" if s["fits"] else ("  !! %d EXCEEDS the 1-byte field "
                                             "(max %d): needs a RUNTIME PIN, not a patch"
                                             % (s["scaled"], s["ceiling"]))
                tw = ("  twins %s" % ",".join(s["twins"])) if s["twins"] else ""
                L.append("\t{ %s, 0x%02X },%s// %s (%d -> %d); bytes %s%s%s" % (
                    s["va"], s["value"] & 0xFF,
                    " " * max(1, 26 - len(s["va"])),
                    s["role"], s["value"], s["scaled"], s["bytes"], tw, warn))
        L.append("};")
    L.append("\n// ---- NOT SCALED (policy / row-count; documented so nobody 'completes the set') ----")
    for s in doc["sites"]:
        if not s["scale"]:
            L.append("//   %s  %-22s stock %-4d  %s" % (s["va"], s["role"], s["value"], s["note"].split(".")[0]))
    L.append("")
    with open(path, "w") as fh:
        fh.write("\n".join(L))


def main():
    factor = 2.0
    out = None
    resume = "--resume" in sys.argv
    for a in sys.argv[1:]:
        if a.startswith("--factor"):
            factor = float(a.split("=", 1)[1]) if "=" in a else float(sys.argv[sys.argv.index(a) + 1])
        if a.startswith("--out="):
            out = a.split("=", 1)[1]
    if out is None:
        out = os.path.join(HERE, "generated-subflyout-builder-%gx.txt" % factor)
    doc = build(factor, resume)
    emit_cpp(doc, out)
    bad = [s for s in doc["sites"] if not s["verified"]]
    print("subflyout_builder: %d sites, %d scaled, %d policy, %d byte-verify FAILURES"
          % (len(doc["sites"]),
             sum(1 for s in doc["sites"] if s["scale"]),
             sum(1 for s in doc["sites"] if not s["scale"]),
             len(bad)))
    for p in doc["problems"]:
        print("  PROBLEM:", p)
    over = [s for s in doc["sites"] if s["scale"] and not s["fits"]]
    print("  sites that CANNOT hold round(stock*%g) in their field: %d" % (factor, len(over)))
    for s in over:
        print("    %s %-24s %d -> %d  (%s, max %d)" % (
            s["va"], s["role"], s["value"], s["scaled"], s["enc"], s["ceiling"]))
    print("  wrote", JSON_OUT)
    print("  wrote", out)


if __name__ == "__main__":
    main()
