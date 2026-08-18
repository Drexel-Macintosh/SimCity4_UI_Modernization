r"""Build z_SC4UIScale_CamGraphLabels.dat - supply the LTEXT that CAM binds but
never ships (#147).

⛔ THE DEFECT IS IN CAM'S DATA, NOT OURS, AND WE DO NOT EDIT CAM'S FILE.
`CAM_Extended_Graph.dat` overrides the Power (I=6) and Water (I=7) chart
definition exemplars (T=0x6534284A G=0xCA4AD545) with FOUR series where stock
has two, and its label array (property 0x6A4AEEDC) reads:

    0x0A5D2E9D  0x0A5D2E9E  0xFF5D2E9E  0xFF5D2E9F
    Capacity    CurrentUsage Imported    <-- DOES NOT EXIST

`0xFF5D2E9F` was indexed against 118,896 records across 107 DBPF files - all
nine install archives plus both Plugins trees - with ZERO hits. Positive
controls in the same scan (0x0A5D2E9D, 0xFF5D2E98, 0xFF5D2E9E) were each found
exactly once, so the scanner could see the thing (NULL IS NOT EVIDENCE).

The row COUNT comes from a different property (0x6A4AEE40) than the labels, and
the game bounds-checks each array independently at 0x0076DF79 - which is why
the 4th row renders with a working checkbox and a cyan swatch but NO CAPTION,
instead of not rendering at all.

The intended value is almost certainly `0xFF5D2E98` = "Exported", which CAM
ships and uses correctly at the same slot in its own Garbage chart. `...9F` vs
`...98` is a single nibble.

WHAT THIS SHIPS: one 20-byte LTEXT record at the id CAM actually asks for, so
the lookup succeeds and the row gets its caption. We add a resource; we do not
modify, rename or delete anything of CAM's.

⛔ DELIBERATELY WITHOUT THE TRAILING CRLF. CAM's own 0xFF5D2E97
("Total Garbage\r\n") and 0xFF5D2E98 ("Exported\r\n") both end in CRLF, which
makes those rows render TWO LINES TALL in the Garbage legend. Copying the
string verbatim would import that bug into Power and Water and push the row
pitch from ~25 to ~46 at 1.5x. Caption only, zero layout change.

⚠ GATED ON CAM BY LOCATION: it ships inside `Plugins\zzz-SC4UIScale\`, and it
is inert without CAM because nothing else binds that id. Remove CAM and this
record is simply never looked up.

LTEXT (type 0x2026960B) payload format - READ OFF THE SHIPPED BYTES, not
assumed (the first draft hardcoded the count and was right only by luck):

    u16  CHARACTER COUNT           <-- the count, NOT a constant
    u16  0x1000                    format/flags
    UTF-16LE characters, no terminator      total size = 4 + 2*count

Measured in `CAM_Locale_en.dat`:

    0xFF5D2E97  0F 00 00 10 ...  size 34  'Total Garbage\r\n'   (15 chars)
    0xFF5D2E98  0A 00 00 10 ...  size 24  'Exported\r\n'        (10 chars)
    0xFF5D2E9E  08 00 00 10 ...  size 20  'Imported'            ( 8 chars)

⚠ NOTE THE THIRD ONE. `Imported` is the row DIRECTLY ABOVE ours in the same
Power/Water legend and it carries NO CRLF. So dropping the CRLF is not a
preference - it is what our row's own siblings do.

    python build_cam_graph_labels.py [--out <dir>]

Then: add it to BOTH `_tests\Deploy-OnGameClose.ps1` AND
`_tests\Test-DatIntegrity.ps1`. A package is not finished until it is in both -
three packages have rotted from exactly that omission and every one looked
green.
"""
import argparse
import os
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
PACKER = os.path.join(ROOT, "tools", "dbpf", "DbpfPack.exe")

LTEXT_TYPE = 0x2026960B
GROUP = 0x6A231EAA
INSTANCE = 0xFF5D2E9F          # the id CAM binds and nobody ships
TEXT = "Exported"              # NO trailing \r\n - see the header


def ltext_payload(s):
    """u16 char count, u16 0x1000, UTF-16LE. Count is DERIVED, never fixed."""
    body = s.encode("utf-16-le")
    out = struct.pack("<HH", len(s), 0x1000) + body
    assert len(out) == 4 + 2 * len(s), "LTEXT size must be 4 + 2*chars"
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "tools", "packages",
                                                  "shared"))
    a = ap.parse_args()
    stage = os.path.join(HERE, "stage-camgraph")
    os.makedirs(stage, exist_ok=True)
    os.makedirs(a.out, exist_ok=True)

    blob = ltext_payload(TEXT)
    name = "T-0x%08x_G-0x%08x_I-0x%08x.bin" % (LTEXT_TYPE, GROUP, INSTANCE)
    with open(os.path.join(stage, name), "wb") as f:
        f.write(blob)
    print("staged %s  (%d bytes) = %r" % (name, len(blob), TEXT))

    out_dat = os.path.join(a.out, "z_SC4UIScale_CamGraphLabels.dat")
    r = subprocess.run([PACKER, stage, out_dat], capture_output=True, text=True)
    print(r.stdout.strip())
    if r.returncode != 0:
        sys.exit("PACK FAILED:\n" + r.stderr)
    print("wrote %s (%d bytes)" % (out_dat, os.path.getsize(out_dat)))


main()
