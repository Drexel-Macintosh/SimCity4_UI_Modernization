#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LANE 2 adversarial verify - step 4: does the C++ edit land in the right
namespace, and is every identifier it uses in scope at that point?

POSITIVE CONTROL: the same tracker must report that VerifiedWrite (line ~817)
IS inside a nested anonymous namespace and that ApplyOrdinanceInsetScale
(line ~911) is NOT - a fact independently visible from the header, which
declares ApplyOrdinanceInsetScale with external linkage. If the tracker
disagrees with the header it is broken and its verdicts are void.
"""
import io, re, sys

P = (r"<PROJECT-ROOT> 1 Project"
     r"\1 Completed Projects\SC4TouchControls\src\CodePatches.cpp")

src = io.open(P, encoding="utf-8").read()
lines = src.split("\n")

STR = re.compile(r'"(?:\\.|[^"\\])*"')
CHR = re.compile(r"'(?:\\.|[^'\\])*'")
NSO = re.compile(r"^\s*namespace\s*(\w*)\s*\{?\s*$")

stack, events, depth = [], [], 0
# ns_at[line] = list of enclosing namespace names at that line
ns_at = {}
cur_ns = []
pend = None            # survives across lines: `namespace` and `{` are often
                       # on separate lines in this file
for ln, line in enumerate(lines, 1):
    s = re.sub(r"//.*$", "", line)
    s = STR.sub('""', s)
    s = CHR.sub("''", s)
    m = NSO.match(s)
    if m:
        pend = (m.group(1) or "<anon>")
    ns_at[ln] = list(cur_ns)
    for ch in s:
        if ch == "{":
            depth += 1
            stack.append((pend, ln))
            if pend:
                events.append(("OPEN", pend, ln, depth))
                cur_ns.append(pend)
                pend = None
        elif ch == "}":
            if stack:
                nm, oln = stack.pop()
                if nm:
                    events.append(("CLOSE", nm, ln, oln))
                    if cur_ns:
                        cur_ns.pop()
            depth -= 1

print("NAMESPACE MAP of CodePatches.cpp")
for e in events:
    if e[0] == "OPEN":
        print("  OPEN  %-10s line %5d  (brace depth %d)" % (e[1], e[2], e[3]))
    else:
        print("  CLOSE %-10s line %5d  (opened %d)" % (e[1], e[2], e[3]))
print("  final brace depth: %d %s" % (depth, "(balanced)" if depth == 0 else "*** UNBALANCED ***"))

def find_line(pat):
    for ln, l in enumerate(lines, 1):
        if pat in l:
            return ln
    return None

probes = [
    ("kOrdinanceInsetSites decl", "const InsetSite kOrdinanceInsetSites[] = {"),
    ("struct InsetSite",          "struct InsetSite { uintptr_t site;"),
    ("VerifiedWrite defn",        "bool VerifiedWrite("),
    ("ApplyOrdinanceInsetScale",  "void ApplyOrdinanceInsetScale(float factor)"),
    ("ApplyGraphLegendBudgetScale", "ApplyGraphLegendBudgetScale"),
    ("gGraphLegendBlocks (latch)", "gGraphLegendBlocks"),
    ("kGraphLegendBlocks table",  "kGraphLegendBlocks[]"),
]
print("\nWHERE EACH RELEVANT SYMBOL LIVES")
for label, pat in probes:
    ln = find_line(pat)
    if ln is None:
        print("  %-30s NOT FOUND" % label)
        continue
    print("  %-30s line %5d  ns=%s" % (label, ln, "::".join(ns_at[ln]) or "<global>"))

# --- POSITIVE CONTROL -------------------------------------------------
vw = find_line("bool VerifiedWrite(")
ap = find_line("void ApplyOrdinanceInsetScale(float factor)")
ctl1 = ns_at[vw] == ["CodePatches", "<anon>"]
ctl2 = ns_at[ap] == ["CodePatches"]
print("\nPOSITIVE CONTROL")
print("  VerifiedWrite ns            = %s   expect CodePatches::<anon>  -> %s"
      % ("::".join(ns_at[vw]), "PASS" if ctl1 else "FAIL"))
print("  ApplyOrdinanceInsetScale ns = %s   expect CodePatches (header "
      "declares it with external linkage) -> %s"
      % ("::".join(ns_at[ap]), "PASS" if ctl2 else "FAIL"))
if not (ctl1 and ctl2):
    print("  TRACKER DISAGREES WITH THE HEADER - verdicts below are void.")
    sys.exit(2)

print("\nWHAT THE PATCH INSERTS, AND WHERE IT LANDS")
ki = find_line("const InsetSite kOrdinanceInsetSites[] = {")
print("  P1 inserts kOrdinanceNameXImm8Sites / OrdinanceNameXUsesBlock /")
print("     kOrdinanceNameXBlocks / kOnxStock* / gOrdinanceNameXBlocks right")
print("     after the kOrdinanceInsetSites close brace -> ns %s"
      % ("::".join(ns_at[ki]) or "<global>"))
print("  P2 inserts ApplyInsetSiteArray + ApplyOrdinanceNameColumnScale in")
print("     place of ApplyOrdinanceInsetScale -> ns %s"
      % ("::".join(ns_at[ap]) or "<global>"))

# reachability: is the P1 namespace visible from the P2 namespace?
print("\n  Is the P1 anonymous namespace an ENCLOSING scope of P2?")
print("    P1 ns = %s" % ("::".join(ns_at[ki]) or "<global>"))
print("    P2 ns = %s" % ("::".join(ns_at[ap]) or "<global>"))
p1 = ns_at[ki]
p2 = ns_at[ap]
# a file-level anonymous namespace at global scope is visible everywhere below
visible = (p1 == ["<anon>"] and p1[0] == "<anon>")
print("    -> %s" % ("YES - a global anonymous namespace's members are found by "
                     "unqualified lookup from any later scope in this TU"
                     if visible else
                     "CHECK MANUALLY - P1 is not a global anonymous namespace"))

# --- the reference template ------------------------------------------
print("\nREFERENCE TEMPLATE the patch claims to copy (graph legend):")
for pat in ("kGraphLegendBlocks[]", "gGraphLegendBlocks = ",
            "int ApplyGraphLegendBudgetScale", "kGlStock"):
    ln = find_line(pat)
    if ln:
        print("  %-32s line %5d  ns=%s" % (pat, ln, "::".join(ns_at[ln]) or "<global>"))
sys.exit(0)
