r"""Rebuild drafts\cIGZWin.md from its template and the evidence.

    python tools\sdk\ghidra\verify\I-issue-evidence\assemble_drafts.py

Runs consolidate_cigzwin.py, then make_cigzwin_table.py, and pastes the table
into the template, so no slot number in the draft is typed by hand. Exits
non-zero unless the evidence still gives exactly 40 wrong declarations,
which is the count the draft's prose states.
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable
subprocess.run([PY, os.path.join(HERE, "consolidate_cigzwin.py")], check=True, capture_output=True)
C = json.load(open(os.path.join(HERE, "cigzwin_consolidated.json")))
if len(C["wrong"]) != 40 or len(C["right"]) != 51 or len(C["undecoded"]) != 56:
    sys.exit("evidence changed (%d wrong, %d right, %d undecoded): update the template's prose first"
             % (len(C["wrong"]), len(C["right"]), len(C["undecoded"])))
table = subprocess.run([PY, os.path.join(HERE, "make_cigzwin_table.py")] + sys.argv[1:],
                       check=True, capture_output=True, text=True).stdout.strip()
tpl = open(os.path.join(HERE, "drafts", "cIGZWin.template.md"), encoding="utf-8").read()
out = tpl.replace("{TABLE}", table).replace("Assembled by assemble_drafts.py; edit this template, not the output.",
                                            "Assembled by assemble_drafts.py from cIGZWin.template.md.")
open(os.path.join(HERE, "drafts", "cIGZWin.md"), "w", encoding="utf-8", newline="\n").write(out)
print("drafts\\cIGZWin.md written: %d table rows" % (table.count("\n") - 1))
