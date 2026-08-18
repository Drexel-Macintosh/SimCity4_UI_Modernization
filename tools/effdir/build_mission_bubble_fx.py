#!/usr/bin/env python3
r"""build_mission_bubble_fx.py - #188 U-Drive-It START-bubble size, the DATA lever.

WHAT THIS BUILDS. An override dat carrying the game's EFFDIR resource
{T=0xEA5118B0, G=0xEA5118B1, I=0x00000001} with ONE surgical change: the SCALE
float in the 18 `mission_selection_*` child-reference records is set to the
tier factor (1.0 -> f). Everything else in the 1,094,484-byte resource is
byte-identical to the game's own copy.

WHY THIS WORKS (evidence chain, 2026-08-17):
  * The exe spawns the start bubbles BY NAME ("mission_selection_yellow" /
    "..._water_yellow", name table 0xB09AE0) via CreateEffectByName at
    0x52C6E8 -- byte-verified. No pixel- or world-size constant exists in the
    exe for these effects; the size lives in this resource.
  * Inside the resource, each named child reference is packed as
    [u32 nameLen][name][u8 type][u32 flags][9 floats rot 3x3][3 floats
    trans][float SCALE][zoomMin u8][zoomMax u8][u16 copies][u16 mult]
    [4 floats zoom ramps][2 u16 weights][u32 effectIndex]. The layout is
    proven twice over: semantically (windmill_shadow translated (19,0,-9),
    helicopter shadows z-5, zoom-4 grid decals +/-0.25 with zoom-5 exactly
    half) AND by disassembly of the parser (ReadChild 0x5AB690 /
    ReadTransform 0x5DA930: scale read at 0x5DAA2B -> child+0x48).
  * THE SCALE IS CONSUMED -- opcode-verified 2026-08-17: child+0x48 is
    copied to the active entry (0x591D6C), multiplied into the spawn
    transform (0x591FDE/0x591FEA, or copied directly at 0x592071 when the
    instance has no transform of its own), and delivered to the live render
    object at 0x592125. Editing this file byte changes the on-screen size.
  * Editing ONLY the mission_selection records is safe: the exe references
    these names at the five UDI sites only (0x52C6C1/0x52C6B9/0x528BC9/
    0x529DA8/0x529D9C), and in-file they appear only in the mission visual
    effects. Nothing else consumes them.

SOURCE DISCIPLINE (law 64): the resource is freshly QFS-extracted from the
game's SimCity_1.dat on every build -- never from a cached copy. The QFS
decoder is imported from tools\uimap\emu\qfs_ab.py (the proven one).

EVERY assertion here is FATAL. A drifted record count, a non-identity
transform where identity is expected, or a byte-diff outside the predicted
72 bytes (18 records x 4 bytes) refuses the build.

Usage:
    python build_mission_bubble_fx.py --factor 1.5 --out <path.dat>
    python build_mission_bubble_fx.py --all          # 1.5/2/3 into build\
"""
import argparse
import os
import re
import struct
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(TOOLS, "uimap", "emu"))
from qfs_ab import qfs  # noqa: E402  (proven RefPack decoder, read-only)

GAME_DAT = r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\SimCity_1.dat"
TGI = (0xEA5118B0, 0xEA5118B1, 0x00000001)
PRISTINE_DECOMP_SIZE = 1094484  # measured 2026-08-17; warn-only (a repatch could shift it)
PACKER = os.path.join(TOOLS, "dbpf", "DbpfPack.exe")

# The frozen target set. Exactly these 18 child-reference records exist in the
# pristine resource (measured 2026-08-17). FATAL in BOTH directions if the scan
# disagrees -- the #186 routing-gate idiom: drift is a stop, not a warning.
EXPECTED = {
    "mission_selection_red", "mission_selection_hidden_red",
    "mission_selection_green", "mission_selection_hidden_green",
    "mission_selection_blue", "mission_selection_hidden_blue",
    "mission_selection_yellow", "mission_selection_hidden_yellow",
    "mission_selection_red_shrink", "mission_selection_hidden_red_shrink",
    "mission_selection_green_shrink", "mission_selection_hidden_green_shrink",
    "mission_selection_blue_shrink", "mission_selection_hidden_blue_shrink",
    "mission_selection_yellow_shrink", "mission_selection_hidden_yellow_shrink",
    "mission_selection_water_yellow", "mission_selection_water_yellow_shrink",
}
IDENTITY_12 = (1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0)


def fatal(msg):
    print(f"FATAL: {msg}")
    sys.exit(1)


def extract_pristine():
    """Fresh QFS extract of the EFFDIR entry from the game's own archive."""
    if not os.path.isfile(GAME_DAT):
        fatal(f"game archive not found: {GAME_DAT}")
    with open(GAME_DAT, "rb") as f:
        hdr = f.read(96)
        if hdr[:4] != b"DBPF":
            fatal("SimCity_1.dat is not a DBPF archive")
        cnt = struct.unpack_from("<I", hdr, 36)[0]
        io_ = struct.unpack_from("<I", hdr, 40)[0]
        isz = struct.unpack_from("<I", hdr, 44)[0]
        f.seek(io_)
        idx = f.read(isz)
        per = isz // cnt
        for k in range(cnt):
            t, g, i, off, size = struct.unpack_from("<5I", idx, k * per)
            if (t, g, i) == TGI:
                f.seek(off)
                raw = f.read(size)
                out = qfs(raw)
                if out is None:
                    out = raw  # stored uncompressed
                if len(out) != PRISTINE_DECOMP_SIZE:
                    print(f"WARN: decompressed size {len(out)} != recorded "
                          f"{PRISTINE_DECOMP_SIZE} (game files changed?)")
                return bytearray(out)
    fatal("EFFDIR TGI not found in SimCity_1.dat index")


def find_records(data):
    """Locate every mission_selection child-reference record.

    Signature: [u32 nameLen][name][u8 type=1][u32 flags=0][13 packed floats].
    (type 1 = the model/sprite effect class table, mgr+0x10C.)
    Returns {name: name_end_offset} -- the 13 floats start at name_end + 5.
    """
    hits = {}
    for m in re.finditer(rb"mission_selection[a-z_]*", data):
        name = m.group().decode()
        s, e = m.start(), m.end()
        ln = struct.unpack_from("<I", data, s - 4)[0]
        if ln != len(name):
            continue  # a by-name reference elsewhere (e.g. the simple map)
        if data[e:e + 5] != b"\x01\x00\x00\x00\x00":
            continue  # simple-map entry ([name][u32 index]) or other shape
        if name in hits:
            fatal(f"duplicate rich record for {name} at {s:#x} and earlier")
        hits[name] = e
    return hits


def patch(data, factor):
    recs = find_records(data)
    got = set(recs)
    if got != EXPECTED:
        fatal(f"record-set drift: missing={sorted(EXPECTED - got)} "
              f"unexpected={sorted(got - EXPECTED)}")
    fbits = struct.pack("<f", factor)
    sites = []
    for name, ne in sorted(recs.items()):
        floats = struct.unpack_from("<13f", data, ne + 5)
        if tuple(floats[:12]) != IDENTITY_12:
            fatal(f"{name}: rot/translation not identity: {floats[:12]}")
        if floats[12] != 1.0:
            fatal(f"{name}: scale is {floats[12]}, expected pristine 1.0")
        off = ne + 5 + 12 * 4
        data[off:off + 4] = fbits
        sites.append((name, off))
    return sites


def build_one(factor, out_dat, pristine):
    data = bytearray(pristine)  # work on a copy
    sites = patch(data, factor)

    # Global proof: the output differs from pristine at EXACTLY the 72
    # predicted bytes (18 sites x 4), nowhere else.
    diff = [i for i, (a, b) in enumerate(zip(pristine, data)) if a != b]
    want = sorted({o + k for _, o in sites for k in range(4)})
    # (identical bytes inside the float, e.g. the low zeros of 2.0, simply
    #  don't appear in `diff`; every diff position must lie in `want`)
    stray = [i for i in diff if i not in set(want)]
    if stray:
        fatal(f"{len(stray)} byte(s) changed outside predicted sites: "
              f"{[hex(i) for i in stray[:8]]}")
    if not diff:
        fatal("no bytes changed -- factor 1.0? refusing a no-op build")

    stage = tempfile.mkdtemp(prefix="bubblefx_")
    fname = "T-0xEA5118B0_G-0xEA5118B1_I-0x00000001.effdir"
    with open(os.path.join(stage, fname), "wb") as f:
        f.write(data)
    os.makedirs(os.path.dirname(out_dat) or ".", exist_ok=True)
    r = subprocess.run([PACKER, stage, out_dat], capture_output=True, text=True)
    if r.returncode != 0:
        fatal(f"DbpfPack failed: {r.stdout} {r.stderr}")

    # Roundtrip proof: extract from the produced dat, byte-compare.
    rt = tempfile.mkdtemp(prefix="bubblefx_rt_")
    r = subprocess.run([PACKER, "--extract", out_dat, rt],
                       capture_output=True, text=True)
    if r.returncode != 0:
        fatal(f"roundtrip extract failed: {r.stdout} {r.stderr}")
    rt_files = os.listdir(rt)
    if len(rt_files) != 1:
        fatal(f"roundtrip: expected 1 entry, got {rt_files}")
    with open(os.path.join(rt, rt_files[0]), "rb") as f:
        if f.read() != bytes(data):
            fatal("roundtrip payload mismatch")

    print(f"built {out_dat}  factor={factor}  ({len(diff)} bytes differ from "
          f"pristine across {len(sites)} records)")
    for name, off in sites:
        print(f"    {off:#08x} {name}: 1.0 -> {factor}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--factor", type=float)
    ap.add_argument("--out")
    ap.add_argument("--all", action="store_true",
                    help="build 1.5/2/3 tier dats into build\\")
    a = ap.parse_args()
    if not os.path.isfile(PACKER):
        fatal(f"packer not found: {PACKER}")
    pristine = bytes(extract_pristine())
    if a.all:
        for f, tag in ((1.5, "15x"), (2.0, "2x"), (3.0, "3x")):
            build_one(f, os.path.join(HERE, "build",
                      f"SC4UIScale_MissionBubbleFx_{tag}.dat"), pristine)
    else:
        if not (a.factor and a.out):
            ap.error("--factor and --out required (or --all)")
        if not (1.0 < a.factor <= 4.0):
            fatal(f"factor {a.factor} outside sanity range (1,4]")
        build_one(a.factor, a.out, pristine)


if __name__ == "__main__":
    main()
