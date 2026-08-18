#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LANE 2 adversarial verify - step 1: exact oldText occurrence counts.

POSITIVE CONTROL: a deliberately-correct needle (read back out of the file
itself) must report count==1 through the SAME code path, and a deliberately
wrong needle must report 0. If either control fails, this probe is blind and
its nulls mean nothing.
"""
import io, os, sys

ROOT = r"<HOME>\OneDrive\Projects\Surface 1 Project\1 Completed Projects\SC4TouchControls"

def load(rel):
    p = os.path.join(ROOT, rel.replace("/", os.sep))
    with io.open(p, "r", encoding="utf-8", newline="") as f:
        return f.read(), p

OLD_CPP_1 = (
"\t\t// v2.25.28: the ordinance NAME texts are SEPARATE windows (ids\n"
"\t\t// 0xABCDE03+k via sub_779660), created at their own x const 68 -\n"
"\t\t// the v2.25.27 row move landed the row's eye component on them\n"
"\t\t// (MWKID 12:12:09 + screenshot). Stock-coherent 2x is 136 but\n"
"\t\t// push-imm8 caps at 127; the clamp still clears the measured eye\n"
"\t\t// (ends ~104) by 23px. [chk 36..68][eye ~84..104][name 127+].\n"
"\t\t{ 0x77CC23, 0x44, 0x55 }, // income ordinance-name text x\n"
"\t\t{ 0x77D0E0, 0x44, 0x55 }, // expense ordinance-name text x\n"
"\t};")

OLD_CPP_2 = (
"\tvoid ApplyOrdinanceInsetScale(float factor)\n"
"\t{\n"
"\t\tint n = 0;\n"
"\t\tconst uintptr_t base = reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));\n"
"\t\tconst uintptr_t delta = base - kImageBase;\n"
"\n"
"\t\tfor (const InsetSite& s : kOrdinanceInsetSites)\n"
"\t\t{\n"
"\t\t\tlong v = std::lround(s.stock * factor);\n"
"\t\t\tif (v == s.stock)\n"
"\t\t\t{\n"
"\t\t\t\tcontinue; // identity factor: nothing to do\n"
"\t\t\t}\n"
"\t\t\tif (v < 1)\n"
"\t\t\t{\n"
"\t\t\t\tcontinue;\n"
"\t\t\t}\n"
"\t\t\tif (v > 127)\n"
"\t\t\t{\n"
"\t\t\t\t// push imm8 ceiling: clamp rather than skip - a slightly\n"
"\t\t\t\t// tighter indent beats the icon-on-text overlap (the name\n"
"\t\t\t\t// column's ideal 136 at f=2 becomes 127, still 23px clear\n"
"\t\t\t\t// of the measured eye).\n"
"\t\t\t\tLogger::Get().WriteLine(\n"
"\t\t\t\t\tLogLevel::Info,\n"
"\t\t\t\t\t\"CodePatches: ordinance inset %ld clamped to 127 at 0x%08X.\",\n"
"\t\t\t\t\tv, static_cast<uint32_t>(s.site));\n"
"\t\t\t\tv = 127;\n"
"\t\t\t}\n"
"\t\t\tuint8_t* p = reinterpret_cast<uint8_t*>(s.site + delta);\n"
"\t\t\t// push imm8 with the stock inset, pinned by the next opcode byte.\n"
"\t\t\tconst uint8_t expect[3] = { 0x6A, s.stock, s.ctx };\n"
"\t\t\tconst uint8_t repl[3] = { 0x6A, static_cast<uint8_t>(v), s.ctx };\n"
"\t\t\t(void)p;\n"
"\t\t\tif (VerifiedWrite(\"ordinance inset\", s.site, delta, expect, repl, 3)) n++;\n"
"\t\t}\n"
"\t\tif (n)\n"
"\t\t{\n"
"\t\t\tLogger::Get().WriteLine(\n"
"\t\t\t\tLogLevel::Info,\n"
"\t\t\t\t\"CodePatches: ordinance row insets x%.2f (%d of %d sites).\",\n"
"\t\t\t\tfactor, n, static_cast<int>(sizeof(kOrdinanceInsetSites) / sizeof(kOrdinanceInsetSites[0])));\n"
"\t\t}\n"
"\t}")

OLD_H = "\tvoid ApplyOrdinanceInsetScale(float factor);"

OLD_DIR = (
"\t\tif (settings.spikeScaleAll && settings.spikeOrdinanceInsetPatch)\n"
"\t\t{\n"
"\t\t\tCodePatches::ApplyOrdinanceInsetScale(settings.spikeScaleFactor);\n"
"\t\t}")

CASES = [
    ("src/CodePatches.cpp", "P1 name-x tail of kOrdinanceInsetSites", OLD_CPP_1),
    ("src/CodePatches.cpp", "P2 ApplyOrdinanceInsetScale body",       OLD_CPP_2),
    ("src/CodePatches.h",   "P3 header decl",                          OLD_H),
    ("src/SC4UIScaleDllDirector.cpp", "P4 director call site",         OLD_DIR),
]

fail = 0
for rel, label, needle in CASES:
    txt, path = load(rel)
    crlf = txt.count("\r\n")
    n = txt.count(needle)
    print("[%s] %s : count=%d  (file has %d CRLF pairs, %d LF total)"
          % ("OK " if n == 1 else "BAD", label, n, crlf, txt.count("\n")))
    if n != 1:
        fail += 1
        # locate the closest anchor to report what IS there
        first = needle.split("\n")[0]
        idx = txt.find(first.strip())
        if idx >= 0:
            ln = txt[:idx].count("\n") + 1
            print("      nearest anchor %r at line %d" % (first.strip()[:60], ln))
        # progressive prefix match: how many lines of the needle DO match
        lines = needle.split("\n")
        for k in range(len(lines), 0, -1):
            sub = "\n".join(lines[:k])
            if txt.count(sub) >= 1:
                print("      longest matching PREFIX = %d of %d lines" % (k, len(lines)))
                nxt = lines[k] if k < len(lines) else None
                if nxt is not None:
                    # what the file actually has at that point
                    at = txt.find(sub) + len(sub)
                    actual = txt[at:at+160].split("\n")[1] if "\n" in txt[at:at+160] else txt[at:at+160]
                    print("      needle line %d wants: %r" % (k+1, nxt))
                    print("      file  line %d has  : %r" % (k+1, actual))
                break
        else:
            print("      NOT ONE LINE of the needle matches.")

# --- POSITIVE CONTROLS -------------------------------------------------
txt, _ = load("src/CodePatches.cpp")
ctrl_hit = "\t\t{ 0x77CC23, 0x44, 0x55 }, // income ordinance-name text x"
ctrl_miss = "\t\t{ 0xDEADBEE, 0x44, 0x55 }, // this line does not exist"
c1 = txt.count(ctrl_hit)
c2 = txt.count(ctrl_miss)
print("\nPOSITIVE CONTROL  (line known present): count=%d  expect 1 -> %s" % (c1, "PASS" if c1 == 1 else "FAIL"))
print("NEGATIVE CONTROL  (line known absent) : count=%d  expect 0 -> %s" % (c2, "PASS" if c2 == 0 else "FAIL"))
if c1 != 1 or c2 != 0:
    print("PROBE IS BLIND - its nulls are worthless.")
    fail += 99

sys.exit(1 if fail else 0)
