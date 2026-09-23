# I-issue-evidence: what an upstream gzcom-dll report would claim (2026-09-23)

Everything a report to nsgomez/gzcom-dll would claim, re-derived from the
committed evidence and the user's own exe. **Nothing here has been posted.**
The drafts wait for the user.

| script | what it proves |
|---|---|
| `consolidate_cigzwin.py` | cIGZWin: 91 of 147 declarations are decoded against the exe. **40 are wrong, 51 right**, and 56 are undecoded (no claim is made about those). It also finds the 5 input handlers whose argument bytes differ from the exe's own `ret N`. |
| `regression_387a9751.py` | Upstream `387a9751` turned 47-50 and 102-107 from right to wrong. The check compiles the probe against `4669fa92`, `387a9751` and HEAD, fetched into `_cache\` (gitignored). |
| `app_director.py` | cIGZApp: all 15 slots of the live app object, each identified by its code and its callers. 8 of the header's 12 methods sit on the wrong slot. cIGZCOMDirector: slot 13 is `GetDirectorID` in all 26 concrete directors. |
| `make_cigzwin_table.py`, `assemble_drafts.py` | Build `drafts\cIGZWin.md` from the evidence, so no slot number is typed by hand. |

The drafts are in `drafts\`. Each states its scope: undecoded rows and the
order of cIGZApp's three identical no-op hooks are named as not observable,
not claimed.
