#!/usr/bin/env python3
r"""#188 THE FIX: tier-scale the CSI (City Situation Indicator) icon family.

    python build_csi_scaled.py 1.5

WHAT THIS IS
------------
The U-Drive-It offer balloon is a CSI, drawn by cSC4DispatchVehicleView::Draw
(0x0046D990) - CONFIRMED on screen 2026-08-18 by suppressing that draw and
watching the balloons vanish. Its art is named by the automata script itself:

    csi_image = "0x4bb1305d"   -- bitmap used for city mission indicator

Eight icons, PNG type 0x856DDBAC, 152x38 = four 38x38 states
(disabled / normal / hover / pressed).

⚠ EACH ICON EXISTS TWICE, PIXEL-IDENTICAL, IN TWO GROUPS:
      0x46A006B0   and   0x1ABE787D
The 2026-08-17 red-tracer test covered 0x46A006B0 ONLY, which is exactly why
its control icons went red while the balloons did not - the drawer resolves
the 0x1ABE787D twin. BOTH GROUPS MUST BE OVERRIDDEN or the fix is a no-op.
That single scoping error cost most of a day; do not repeat it.

Cell-first sizing (law 89 / the #171 cure): the strip is FOUR states, so the
scaled width is states * round(cell * f), never round(total * f) - otherwise
the cell divide stops being exact and every state samples off-centre.
"""
import glob
import os
import struct
import subprocess
import sys
import tempfile
import io as _io

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
GAME = os.environ.get(
    "SC4_GAME_DIR",
    r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe")
PACKER = os.path.join(PROJ, "tools", "dbpf", "DbpfPack.exe")

PNG_T = 0x856DDBAC
GROUPS = (0x46A006B0, 0x1ABE787D)
STATES = 4
ICONS = {
    0x4BB1305D: "car",        # <- csi_image for 24 automata groups
    0x4BB1305E: "helicopter",
    0x4BB1305F: "police",
    0x4BB13060: "ufo_ferry",
    0x0C0305C3: "boat_sail",
    0x0C0305C4: "airplane",
    0x0C0305C5: "armytank",
    0x0C0305C6: "train",
}


def fatal(m):
    print("FATAL: " + m)
    sys.exit(1)


def entries(path):
    with open(path, "rb") as fh:
        head = fh.read(96)
        if head[:4] != b"DBPF":
            return
        cnt = struct.unpack_from("<I", head, 36)[0]
        off = struct.unpack_from("<I", head, 40)[0]
        fh.seek(off)
        raw = fh.read(cnt * 20)
    for k in range(cnt):
        yield struct.unpack_from("<IIIII", raw, k * 20)


def main():
    factor = float(sys.argv[1]) if len(sys.argv) > 1 else 1.5
    if not (1.01 < factor <= 4.0):
        fatal("factor %.2f outside (1,4]" % factor)
    if not os.path.isfile(PACKER):
        fatal("DbpfPack.exe missing at " + PACKER)

    src = {}
    for p in glob.glob(os.path.join(GAME, "**", "*.dat"), recursive=True):
        for (t, g, i, o, s) in entries(p):
            if t == PNG_T and g in GROUPS and i in ICONS and (g, i) not in src:
                with open(p, "rb") as fh:
                    fh.seek(o)
                    src[(g, i)] = fh.read(s)

    expect = len(GROUPS) * len(ICONS)
    if len(src) != expect:
        fatal("found %d of %d (group,instance) pairs - refusing a partial "
              "override, which is how half a family ends up mismatched"
              % (len(src), expect))

    stage = tempfile.mkdtemp(prefix="csi_")
    made = 0
    for (g, i), blob in sorted(src.items()):
        im = Image.open(_io.BytesIO(blob)).convert("RGBA")
        w, h = im.size
        if w % STATES:
            fatal("0x%08X width %d is not divisible by %d states" % (i, w, STATES))
        cell = w // STATES
        # CELL-FIRST: scale the unit and multiply, never scale the total.
        ncell = int(cell * factor + 0.5)
        nw, nh = ncell * STATES, int(h * factor + 0.5)
        # Resample per CELL so no state can bleed into its neighbour.
        out = Image.new("RGBA", (nw, nh), (0, 0, 0, 0))
        for s in range(STATES):
            box = im.crop((s * cell, 0, (s + 1) * cell, h))
            out.paste(box.resize((ncell, nh), Image.LANCZOS), (s * ncell, 0))
        name = "T-0x%08X_G-0x%08X_I-0x%08X.png" % (PNG_T, g, i)
        out.save(os.path.join(stage, name), "PNG")
        made += 1
        print("  %-11s G=0x%08X I=0x%08X  %dx%d (cell %d) -> %dx%d (cell %d)"
              % (ICONS[i], g, i, w, h, cell, nw, nh, ncell))

    outdir = os.path.join(HERE, "build")
    os.makedirs(outdir, exist_ok=True)
    dat = os.path.join(outdir, "SC4UIScale_CsiIcons.dat")
    if os.path.exists(dat):
        os.remove(dat)
    r = subprocess.run([PACKER, stage, dat], capture_output=True, text=True)
    if r.returncode != 0:
        fatal("DbpfPack failed: %s %s" % (r.stdout, r.stderr))

    rt = tempfile.mkdtemp(prefix="csi_rt_")
    r = subprocess.run([PACKER, "--extract", dat, rt],
                       capture_output=True, text=True)
    if r.returncode != 0:
        fatal("roundtrip extract failed: %s %s" % (r.stdout, r.stderr))
    if len(os.listdir(rt)) != made:
        fatal("roundtrip: staged %d, dat holds %d" % (made, len(os.listdir(rt))))

    print("\nOK: %d entries (%d icons x %d groups) at x%.2f -> %s (%d B)"
          % (made, len(ICONS), len(GROUPS), factor, dat, os.path.getsize(dat)))


if __name__ == "__main__":
    main()
