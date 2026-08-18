#!/usr/bin/env python3
"""
PREDICTIVE DEFECT SWEEP helper -- OFFLINE verification of every CodePatches site.

Two questions, both answerable without launching the game:

  1. VERIFY  -- does each site in CodePatches.cpp actually hold the bytes the
     patcher expects?  A site that does not is a constant left at 1x forever.
     The game logs these ("bytes unexpected - skipped"), but only at runtime and
     only if someone reads the log; this finds them at rest.  It is how D1
     (0x77F5B9 -> 0x77F5B2) was pinned.

  2. TWINS   -- for the fixed-signature tables, scan the WHOLE exe for the same
     byte pattern and report occurrences NOT in the table.  This is laws 15/16
     (missed twins / missed encodings / missed second code path), which
     REGRESSION.md calls the two most expensive bug classes of the project, and
     it is METHOD.md sec.6 stage 2 done for the tables that allow it.

Read-only: opens the exe, never writes it.  Writes nothing outside pds-cache.
"""
import os
import re
import struct
import sys

EXE = r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Apps\SimCity 4.exe"
HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
CPP = os.path.join(PROJ, "src", "CodePatches.cpp")
IMAGE_BASE = 0x400000


# ---------------------------------------------------------------- PE mapping
class PE:
    """VA -> file offset via the real section table.

    The flat `off = VA - 0x400000` shortcut happens to hold for .text in this
    binary but must NOT be assumed for .rdata (the HTML size tables live there).
    """

    def __init__(self, path):
        self.d = open(path, "rb").read()
        pe = struct.unpack_from("<I", self.d, 0x3C)[0]
        assert self.d[pe:pe + 4] == b"PE\0\0"
        nsec = struct.unpack_from("<H", self.d, pe + 6)[0]
        optsz = struct.unpack_from("<H", self.d, pe + 20)[0]
        self.base = struct.unpack_from("<I", self.d, pe + 24 + 28)[0]
        self.secs = []
        for i in range(nsec):
            o = pe + 24 + optsz + i * 40
            name = self.d[o:o + 8].rstrip(b"\0").decode("ascii", "replace")
            vsz, va, rsz, raw = struct.unpack_from("<IIII", self.d, o + 8)
            self.secs.append((name, va, max(vsz, rsz), raw, rsz))

    def off(self, va):
        rva = va - self.base
        for name, sva, vsz, raw, rsz in self.secs:
            if sva <= rva < sva + vsz:
                o = raw + (rva - sva)
                return o if o < raw + rsz else None
        return None

    def read(self, va, n):
        o = self.off(va)
        return None if o is None else self.d[o:o + n]

    def section_of(self, va):
        rva = va - self.base
        for name, sva, vsz, raw, rsz in self.secs:
            if sva <= rva < sva + vsz:
                return name
        return "?"


# ------------------------------------------------------- CodePatches parsing
SRC = open(CPP, encoding="utf-8", errors="replace").read()


def strip_comments(s):
    return re.sub(r"//[^\n]*", "", s)


def table(name):
    i = SRC.index(name + "[] = {")
    return strip_comments(SRC[i:SRC.index("};", i)])


def pairs(name):
    """{ 0xVA, 0xSTOCK } rows."""
    return [(int(a, 16), int(b, 16))
            for a, b in re.findall(r"\{\s*0x([0-9A-Fa-f]+)\s*,\s*0x([0-9A-Fa-f]+)\s*\}",
                                   table(name))]


def triples(name):
    return [(int(a, 16), int(b, 16), int(c, 16))
            for a, b, c in re.findall(
                r"\{\s*0x([0-9A-Fa-f]+)\s*,\s*0x([0-9A-Fa-f]+)\s*,\s*0x([0-9A-Fa-f]+)\s*\}",
                table(name))]


def flat(name):
    return [int(x, 16) for x in re.findall(r"0x([0-9A-Fa-f]+)", table(name))]


def main():
    pe = PE(EXE)
    bad, ok = [], 0

    def check(label, va, cond, got):
        nonlocal ok
        if cond:
            ok += 1
        else:
            bad.append((label, va, got))

    # --- push imm8: 6A <stock>
    for va, stock in pairs("kDeptImm8Sites"):
        b = pe.read(va, 2)
        check("kDeptImm8Sites", va, b and b[0] == 0x6A and b[1] == stock,
              "want 6A %02X got %s" % (stock, b.hex(" ").upper() if b else "??"))

    # --- push imm32: 68 <stock:4>
    for va, stock in pairs("kDeptImm32Sites"):
        b = pe.read(va, 5)
        check("kDeptImm32Sites", va,
              b and b[0] == 0x68 and struct.unpack_from("<I", b, 1)[0] == stock,
              "want 68 %08X got %s" % (stock, b.hex(" ").upper() if b else "??"))

    # --- sub r32,imm8: 83 /5 <stock>
    for va, stock in pairs("kBudgetSubImm8Sites"):
        b = pe.read(va, 3)
        check("kBudgetSubImm8Sites", va,
              b and b[0] == 0x83 and (b[1] & 0xF8) == 0xE8 and b[2] == stock,
              "want 83 /5 %02X got %s" % (stock, b.hex(" ").upper() if b else "??"))

    # --- push imm8 + ctx byte: 6A <stock> <ctx>
    for va, stock, ctx in triples("kOrdinanceInsetSites"):
        b = pe.read(va, 3)
        check("kOrdinanceInsetSites", va,
              b and b[0] == 0x6A and b[1] == stock and b[2] == ctx,
              "want 6A %02X %02X got %s" % (stock, ctx, b.hex(" ").upper() if b else "??"))

    # --- fixed 7/6/3-byte signatures
    SIG = {
        "kBudgetBtnSizeSites": bytes([0x6A, 0x1E, 0x68, 0xB4, 0, 0, 0]),
        "kBudgetBtnXSites": bytes([0x81, 0xE9, 0xC3, 0, 0, 0]),
        "kBizBoxSizeSites": bytes([0x6A, 0x64, 0x68, 0x2C, 0x01, 0, 0]),
    }
    for name, sig in SIG.items():
        for va in flat(name):
            b = pe.read(va, len(sig))
            check(name, va, b == sig,
                  "want %s got %s" % (sig.hex(" ").upper(),
                                      b.hex(" ").upper() if b else "??"))

    for va in flat("kBudgetBtnYSites"):
        b = pe.read(va, 3)
        check("kBudgetBtnYSites", va,
              b and b[0] == 0x83 and (b[1] & 0xF8) == 0xE8 and b[2] == 0x28,
              "want 83 /5 28 got %s" % (b.hex(" ").upper() if b else "??"))

    for va in flat("kRatingImulSites"):
        b = pe.read(va, 3)
        check("kRatingImulSites", va, b and b[0] == 0x6B and b[2] == 0x07,
              "want 6B ?? 07 got %s" % (b.hex(" ").upper() if b else "??"))

    for va in flat("kTipWrapSites"):
        b = pe.read(va, 5)
        check("kTipWrapSites", va,
              b and b[0] == 0x68 and struct.unpack_from("<I", b, 1)[0] == 250,
              "want push 250 got %s" % (b.hex(" ").upper() if b else "??"))

    # --- bizbox close X / Y (single named consts)
    cx = int(re.search(r"kBizBoxCloseX\s*=\s*0x([0-9A-Fa-f]+)", SRC).group(1), 16)
    cy = int(re.search(r"kBizBoxCloseY\s*=\s*0x([0-9A-Fa-f]+)", SRC).group(1), 16)
    b = pe.read(cx, 5)
    check("kBizBoxCloseX", cx, b == bytes([0x68, 0x0D, 0x01, 0, 0]),
          "want 68 0D 01 00 00 got %s" % (b.hex(" ").upper() if b else "??"))
    b = pe.read(cy, 2)
    check("kBizBoxCloseY", cy, b == bytes([0x6A, 0x0B]),
          "want 6A 0B got %s" % (b.hex(" ").upper() if b else "??"))

    # --- master notch raw sites
    for va, immoff, op0, op1, stock in re.findall(
            r"\{\s*0x([0-9A-Fa-f]+)\s*,\s*(\d+)\s*,\s*0x([0-9A-Fa-f]+)\s*,"
            r"\s*0x([0-9A-Fa-f]+)\s*,\s*0x([0-9A-Fa-f]+)\s*\}",
            table("kMasterNotchSites")):
        va, immoff, op0, op1, stock = (int(va, 16), int(immoff), int(op0, 16),
                                       int(op1, 16), int(stock, 16))
        b = pe.read(va, immoff + 4)
        good = (b and b[0] == op0 and (op1 == 0 or b[1] == op1)
                and struct.unpack_from("<I", b, immoff)[0] == stock)
        check("kMasterNotchSites", va, good,
              "want op %02X %02X imm %X got %s" % (op0, op1, stock,
                                                   b.hex(" ").upper() if b else "??"))

    # --- popup style retargets (push imm32 <guid>)
    for va, frm, to in triples("kPopupStyleRetargets"):
        b = pe.read(va, 5)
        check("kPopupStyleRetargets", va,
              b and b[0] == 0x68 and struct.unpack_from("<I", b, 1)[0] == frm,
              "want push %08X got %s" % (frm, b.hex(" ").upper() if b else "??"))

    # --- .rdata HTML size tables (needs the real section mapping)
    for nm, va_re, val_re in (
            ("HTML font-size", r"kHtmlFontSizeTable\s*=\s*0x([0-9A-Fa-f]+)",
             r"kStockHtmlFontSizes\[7\]\s*=\s*\{([^}]*)\}"),
            ("HTML heading", r"kHtmlHeadingSizeTable\s*=\s*0x([0-9A-Fa-f]+)",
             r"kStockHtmlHeadingSizes\[7\]\s*=\s*\{([^}]*)\}")):
        va = int(re.search(va_re, SRC).group(1), 16)
        want = [int(x) for x in re.search(val_re, SRC).group(1).split(",")]
        b = pe.read(va, 28)
        got = list(struct.unpack("<7I", b)) if b else None
        check(nm + " table", va, got == want,
              "want %s got %s (section %s)" % (want, got, pe.section_of(va)))

    print("=" * 78)
    print("SITE VERIFICATION vs the exe on disk")
    print("=" * 78)
    print("sites checked OK : %d" % ok)
    print("sites MISMATCHED : %d" % len(bad))
    for label, va, got in bad:
        print("  !! 0x%08X  %-24s %s" % (va, label, got))

    # ------------------------------------------------------------ TWIN SCAN
    print()
    print("=" * 78)
    print("TWIN SCAN -- whole-exe occurrences of each fixed signature")
    print("(a hit NOT in the table is a missed twin: laws 15/16)")
    print("=" * 78)
    for name, sig in list(SIG.items()) + [
            ("kBizBoxCloseX(sig)", bytes([0x68, 0x0D, 0x01, 0, 0]))]:
        listed = set(flat(name.split("(")[0])) if not name.endswith("(sig)") else {cx}
        hits, i = [], 0
        while True:
            i = pe.d.find(sig, i)
            if i < 0:
                break
            for nm2, sva, vsz, raw, rsz in pe.secs:
                if raw <= i < raw + rsz:
                    hits.append(pe.base + sva + (i - raw))
                    break
            i += 1
        extra = sorted(set(hits) - listed)
        print("%-22s sig %-24s exe hits %2d / table %2d   EXTRA %d %s"
              % (name, sig.hex(" ").upper(), len(hits), len(listed), len(extra),
                 " ".join("0x%08X" % v for v in extra[:8])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
