r"""Rebuild drafts\ISSUE.md from its template and the evidence.

    python tools\sdk\ghidra\verify\I-issue-evidence\assemble_drafts.py

Runs consolidate_cigzwin.py, then make_cigzwin_table.py, and pastes the table
into drafts\ISSUE.template.md, so no slot number in the table is typed by
hand. It exits non-zero unless the evidence still gives exactly what the
prose states: all 147 positions identified, 40 wrong and 107 right, and 9
argument-list mismatches.
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable
subprocess.run([PY, os.path.join(HERE, "consolidate_cigzwin.py")], check=True, capture_output=True)
C = json.load(open(os.path.join(HERE, "cigzwin_consolidated.json")))
L = json.load(open(os.path.join(HERE, "cigzwin_argument_lists.json")))
if (len(C["wrong"]), len(C["right"]), len(C["undecoded"])) != (40, 107, 0) \
        or len(L["count"]) + len(L["byvalue"]) != 9 or L["readable"] != 142:
    sys.exit("evidence changed (%d wrong, %d right, %d undecoded, %d argument lists, %d readable): "
             "update the template's prose first" % (len(C["wrong"]), len(C["right"]), len(C["undecoded"]),
                                                    len(L["count"]) + len(L["byvalue"]), L["readable"]))
table = subprocess.run([PY, os.path.join(HERE, "make_cigzwin_table.py")] + sys.argv[1:],
                       check=True, capture_output=True, text=True).stdout.strip()
tpl = open(os.path.join(HERE, "drafts", "ISSUE.template.md"), encoding="utf-8").read()
out = tpl.replace("{TABLE}", table).replace(
    "Assembled by assemble_drafts.py; edit this template, not the output.",
    "Assembled by assemble_drafts.py from ISSUE.template.md.")
open(os.path.join(HERE, "drafts", "ISSUE.md"), "w", encoding="utf-8", newline="\n").write(out)
print("drafts\\ISSUE.md written: %d table rows" % (table.count("\n") - 1))
