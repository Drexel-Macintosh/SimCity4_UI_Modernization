#!/usr/bin/env python3
r"""Carbon-sourced small-art package: z_SC4UIScale_ZCarbonIcons-<tag>.dat

    python build_carbon_icons.py 1.5

The 18-PNG package that re-wins the small-art collisions when Scoty Carbon
Skin is installed (see CARBON-COMPAT.md):

- 8 CSI balloon icons {856DDBAC, 46A006B0} from Carbon, duplicated into BOTH
  twin groups (46A006B0 + 1ABE787D) because the drawer resolves the 1ABE787D
  twin and Carbon ships none of them (verified 0 of 8) - the exact scoping
  error that cost a day in #188. Cell-first NEAREST per law 89/#171 and #200,
  identical to build_csi_scaled.py.
- ItemIcons strip {856DDBAC, 6A386D26, 00001111} and the Missing Thumb
  {856DDBAC, 6A386D26, 144161EC} from Carbon, scaled with Upscale2x.exe
  exactly as build_itemicons_sub.py does (same NN + snap rules the .UI side
  expects).

Name note: the base is deliberately Z-late ("ZCarbonIcons") so it sorts
AFTER z_SC4UIScale_CsiIcons / ItemIconsSub inside zzz-SC4UIScale\ and wins
their shared TGIs when armed; the gate (carbon absent -> disarmed) hands
those TGIs straight back to the stock-derived packages. Base name must stay
purely alphanumeric after z_SC4UIScale_ (Test-DatIntegrity drift regex).

Source payloads: tools\research\carbon\extracted-plain\ (winner-resolved,
QFS-decoded; built by carbon_stage.py from the local mirror in source\).
"""
import io as _io
import os
import shutil
import struct
import subprocess
import sys
import tempfile

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
PLAIN = os.path.join(HERE, "extracted-plain")
PACKER = os.path.join(PROJ, "tools", "dbpf", "DbpfPack.exe")
UPSCALE = os.path.join(PROJ, "tools", "upscale", "Upscale2x.exe")

PNG_T = 0x856DDBAC
CSI_GROUPS = (0x46A006B0, 0x1ABE787D)
STATES = 4
CSI_ICONS = {
    0x4BB1305D: "car",
    0x4BB1305E: "helicopter",
    0x4BB1305F: "police",
    0x4BB13060: "ufo_ferry",
    0x0C0305C3: "boat_sail",
    0x0C0305C4: "airplane",
    0x0C0305C5: "armytank",
    0x0C0305C6: "train",
}
ITEM_GROUP = 0x6A386D26
ITEM_STRIPS = (0x00001111, 0x144161EC)


def fatal(m):
    print("FATAL: " + m)
    sys.exit(1)


def tag_of(f):
    if abs(f - 1.5) < 1e-9:
        return "-15x"
    if abs(f - 2.0) < 1e-9:
        return "-2x"
    if abs(f - 3.0) < 1e-9:
        return "-3x"
    fatal("no tag for factor %r" % f)


def plain(t, g, i):
    p = os.path.join(PLAIN, "T-0x%08X_G-0x%08X_I-0x%08X.bin" % (t, g, i))
    if not os.path.isfile(p):
        fatal("carbon payload missing: " + p)
    b = open(p, "rb").read()
    if b[:8] != b"\x89PNG\r\n\x1a\n":
        fatal("not PNG bytes (image-magic law): " + p)
    return b


def main():
    factor = float(sys.argv[1]) if len(sys.argv) > 1 else 1.5
    tag = tag_of(factor)
    for exe in (PACKER, UPSCALE):
        if not os.path.isfile(exe):
            fatal("missing tool " + exe)

    stage = tempfile.mkdtemp(prefix="zcarb_")
    made = 0

    # --- CSI family: carbon blob -> both twin groups, cell-first NEAREST ---
    for inst, name in sorted(CSI_ICONS.items()):
        blob = plain(PNG_T, 0x46A006B0, inst)
        im = Image.open(_io.BytesIO(blob)).convert("RGBA")
        w, h = im.size
        if w % STATES:
            fatal("0x%08X width %d not divisible by %d states" % (inst, w, STATES))
        cell = w // STATES
        ncell = int(cell * factor + 0.5)
        nw, nh = ncell * STATES, int(h * factor + 0.5)
        out = Image.new("RGBA", (nw, nh), (0, 0, 0, 0))
        for s in range(STATES):
            box = im.crop((s * cell, 0, (s + 1) * cell, h))
            # #200: NEAREST. LANCZOS softened these at every tier while the
            # corpus beside them is pixel-exact at 2x/3x; cell-first sizing
            # makes the divide exact so no averaging is needed for evenness.
            out.paste(box.resize((ncell, nh), Image.NEAREST), (s * ncell, 0))
        for g in CSI_GROUPS:
            out.save(os.path.join(
                stage, "T-0x%08X_G-0x%08X_I-0x%08X.png" % (PNG_T, g, inst)), "PNG")
            made += 1
        print("  csi %-10s I=0x%08X  %dx%d (cell %d) -> %dx%d (cell %d) x2 groups"
              % (name, inst, w, h, cell, nw, nh, ncell))

    # --- Item strips: Upscale2x recipe (build_itemicons_sub convention) ---
    tmp1x = tempfile.mkdtemp(prefix="zcarb1x_")
    for inst in ITEM_STRIPS:
        blob = plain(PNG_T, ITEM_GROUP, inst)
        with open(os.path.join(
                tmp1x, "T-0x%08X_G-0x%08X_I-0x%08X.png" % (PNG_T, ITEM_GROUP, inst)),
                "wb") as f:
            f.write(blob)
    up = tempfile.mkdtemp(prefix="zcarbup_")
    r = subprocess.run([UPSCALE, tmp1x, up, "--factor", "%g" % factor,
                        "--normalize-names"], capture_output=True, text=True)
    if r.returncode != 0:
        fatal("Upscale2x failed: %s %s" % (r.stdout, r.stderr))
    for fn in os.listdir(up):
        if not fn.endswith(".png"):
            continue
        shutil.copy2(os.path.join(up, fn), os.path.join(stage, fn))
        d = open(os.path.join(up, fn), "rb").read(33)
        w, h = struct.unpack(">II", d[16:24])
        made += 1
        print("  item %s -> %dx%d" % (fn, w, h))

    if made != len(CSI_ICONS) * len(CSI_GROUPS) + len(ITEM_STRIPS):
        fatal("staged %d, expected %d - refusing a partial family"
              % (made, len(CSI_ICONS) * len(CSI_GROUPS) + len(ITEM_STRIPS)))

    # House emit convention (CamUI pattern): untagged 2x in the builder's own
    # dir, tagged tiers in tools\packages\<tag>\. All dats are gitignored
    # (allowlist + global *.dat) - carbon pixels never reach the public repo.
    if tag == "-2x":
        outdir = HERE
        dat = os.path.join(outdir, "z_SC4UIScale_ZCarbonIcons.dat")
    else:
        outdir = os.path.join(PROJ, "tools", "packages", tag.lstrip("-"))
        os.makedirs(outdir, exist_ok=True)
        dat = os.path.join(outdir, "z_SC4UIScale_ZCarbonIcons%s.dat" % tag)
    if os.path.exists(dat):
        os.remove(dat)
    r = subprocess.run([PACKER, stage, dat], capture_output=True, text=True)
    if r.returncode != 0:
        fatal("DbpfPack failed: %s %s" % (r.stdout, r.stderr))

    rt = tempfile.mkdtemp(prefix="zcarb_rt_")
    r = subprocess.run([PACKER, "--extract", dat, rt], capture_output=True, text=True)
    if r.returncode != 0:
        fatal("roundtrip extract failed: %s %s" % (r.stdout, r.stderr))
    got = len([f for f in os.listdir(rt) if f.endswith(".bin")])
    if got != made:
        fatal("roundtrip: staged %d, dat holds %d" % (made, got))

    print("\nOK: %d entries at x%.2f -> %s (%d B)"
          % (made, factor, dat, os.path.getsize(dat)))


if __name__ == "__main__":
    main()
