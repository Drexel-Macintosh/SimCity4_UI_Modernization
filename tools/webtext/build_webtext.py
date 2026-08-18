#!/usr/bin/env python3
"""z_SC4UIScale_WebText.dat -- LTEXT overrides matching the WebRedirect DLL.

The SC4UIScale DLL redirects the dead simcity.ea.com website launch to
https://community.simtropolis.com/ (WebRedirect.cpp, active at EVERY tier).
These LTEXT overrides make the visible TEXT match: every locale string that
advertises SimCity.com now says Simtropolis.com. Shipped as an ALWAYS-ON
untagged dat (never gated by ScaleTier -- resolution-independent, exactly
like the redirect itself).

LTEXT binary format (type 0x2026960B, verified against SimCityLocale.DAT):
  uint16 LE character count + bytes 00 10 + UTF-16LE string.

The three strings below are the complete census of SimCity.com mentions
across all 5,962 LTEXT entries in SimCityLocale.DAT (scanned 2026-07-23).
The tooltip's window-side `tiptext=` fallback in the .UI scripts still says
SimCity.com but is dead text -- the tipres LTEXT wins (proven: the rendered
tooltip matches the LTEXT's title|body order, not the inline order).
SimCityscape mentions are left untouched (only the domain swap was asked).
"""
import os
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
PACKER = os.path.join(TOOLS, "dbpf", "DbpfPack.exe")
STAGE = os.path.join(HERE, "stage")
OUT_DAT = os.path.join(HERE, "z_SC4UIScale_WebText.dat")

LTEXT_TYPE = 0x2026960B
GROUP = 0x6A231EAA

# instance -> corrected text (originals from SimCityLocale.DAT with ONLY the
# SimCity.com domain references swapped for Simtropolis.com)
STRINGS = {
    # Region-screen website button tooltip (ESRB notice)
    0x0A5128F3: (
        "ESRB NOTICE: Game Experience May Change During Online Play|"
        "Connect to Simtropolis.com\r\n"
        "Opens your internet browser and connects you directly to "
        "Simtropolis.com."
    ),
    # Import City tooltip
    0x0A6CF0D3: (
        "Import City|Allows you to import a city from another region or one "
        "that you may have downloaded from www.Simtropolis.com.  This will "
        "delete the city that is currently at this location."
    ),
    # Internet Options panel blurb
    0x4A51207B: (
        "Internet Options|From this panel you can connect to "
        "www.Simtropolis.com or directly to SimCityscape and enjoy SimCity "
        "with other fans."
    ),
}


def main():
    os.makedirs(STAGE, exist_ok=True)
    for f in os.listdir(STAGE):
        os.remove(os.path.join(STAGE, f))
    for inst, text in sorted(STRINGS.items()):
        blob = struct.pack("<H", len(text)) + b"\x00\x10" \
            + text.encode("utf-16le")
        name = "T-0x%08x_G-0x%08x_I-0x%08x.bin" % (LTEXT_TYPE, GROUP, inst)
        with open(os.path.join(STAGE, name), "wb") as f:
            f.write(blob)
        print("staged %s (%d chars)" % (name, len(text)))

    r = subprocess.run([PACKER, STAGE, OUT_DAT], capture_output=True, text=True)
    print(r.stdout.strip())
    if r.returncode != 0:
        sys.exit("PACK FAILED:\n" + r.stderr)
    r = subprocess.run([PACKER, "--list", OUT_DAT], capture_output=True, text=True)
    print(r.stdout.strip())
    print("OK: %s (%d bytes)" % (OUT_DAT, os.path.getsize(OUT_DAT)))


if __name__ == "__main__":
    main()
