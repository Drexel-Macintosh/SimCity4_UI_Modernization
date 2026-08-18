#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Adversarial verify: does every oldText in the LANE 4 spec occur EXACTLY ONCE?"""
import os, sys

SRC = r"<HOME>\OneDrive\Projects\Surface 1 Project\1 Completed Projects\SC4TouchControls\src"

PATCHES = [
 ("CodePatches.h",
  "\tbool MiniMapX8Active();\n}"),
 ("CodePatches.cpp",
  '#include "CodePatches.h"\n#include "Logger.h"\n\n#define WIN32_LEAN_AND_MEAN\n#include <Windows.h>\n\n#include <cmath>\n#include <cstdint>'),
 ("CodePatches.cpp",
  "\tint MiniMapX8Blits() { return static_cast<int>(gX8Blits); }\n\tint MiniMapX8Clips() { return static_cast<int>(gX8Clips); }\n\tbool MiniMapX8Active() { return gX8Applied == 1; }\n}"),
 ("Settings.h",
  "\tbool spikeRatingArrowPatch = true; // byte-patch the Mayor-rating arrow"),
 ("Settings.cpp",
  '\tspikeRatingArrowPatch = GetPrivateProfileIntW(kSpike, L"RatingArrowPatch", spikeRatingArrowPatch ? 1 : 0, iniPath) != 0;'),
 ("SC4UIScaleDllDirector.cpp",
  "\t\tif (settings.spikeScaleAll && settings.spikeRatingArrowPatch)\n\t\t{\n\t\t\tCodePatches::ApplyRatingArrowScale(settings.spikeScaleFactor);\n\t\t}"),
]

# POSITIVE CONTROL: a string we KNOW is in each file must be found, proving
# the reader/encoding path can see text at all.
CONTROLS = {
 "CodePatches.h": "MiniMapX8Blits",
 "CodePatches.cpp": "kRatingImulSites",
 "Settings.h": "spikeScaleFactor",
 "Settings.cpp": "GetPrivateProfileIntW",
 "SC4UIScaleDllDirector.cpp": "CodePatches::",
}

cache = {}
def load(name):
    if name not in cache:
        with open(os.path.join(SRC, name), "rb") as fh:
            cache[name] = fh.read().decode("utf-8", "replace")
    return cache[name]

print("=== POSITIVE CONTROLS ===")
for name, ctl in CONTROLS.items():
    txt = load(name)
    print("  %-28s control %-22s count=%d  %s" %
          (name, repr(ctl), txt.count(ctl),
           "OK" if txt.count(ctl) > 0 else "*** READER BLIND ***"))

print("\n=== oldText MATCHES ===")
fails = 0
for i, (name, old) in enumerate(PATCHES):
    txt = load(name)
    n = txt.count(old)
    status = "OK" if n == 1 else "*** BLOCKER ***"
    print("  [%d] %-28s count=%d  %s" % (i, name, n, status))
    if n != 1:
        fails += 1
        # try to localise the divergence
        for cut in range(len(old), 0, -1):
            if txt.count(old[:cut]) >= 1:
                print("      longest matching prefix = %d/%d chars" % (cut, len(old)))
                print("      prefix ends: %r" % old[max(0, cut-60):cut])
                idx = txt.find(old[:cut])
                print("      file has next: %r" % txt[idx+cut:idx+cut+90])
                break
        else:
            print("      NO prefix of any length matches")
print("\nfails=%d" % fails)
