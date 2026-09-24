# I-issue-evidence: the upstream gzcom-dll report, and its fix (2026-09-23)

Everything a report to nsgomez/gzcom-dll claims, re-derived from the
committed evidence and the user's own exe. There is also a checker for the
fix branch.

**Nothing has been posted upstream.** The draft and the fix branch wait for
the user.

| script | what it proves |
|---|---|
| `consolidate_cigzwin.py` | cIGZWin: **all 147 positions identified**. 40 of the 144 own methods are wrong and 104 right. There are 9 argument-list mismatches: 7 counts from the `ret N` census of 142 slots, plus 2 colours passed by value, read from the code. |
| `dump_undecoded.py` | Prints the bodies of rows not yet identified, for a person to read. The last 51 were identified from its output and recorded in `consolidate_cigzwin.py`'s `BODY` table, one line of evidence each. |
| `regression_387a9751.py` | Everything upstream `387a9751` changed. It broke 47-50, 102-107 and `CenterWindowInRect(cRZRect*)`, fixed `SetArea(l,t,r,b)`, and left `SetArea(rect)` wrong before and after. It fetches the three header versions into `_cache\` (gitignored). |
| `app_director.py` | cIGZApp: all 15 slots of the live app object; 8 of the header's 12 methods sit on the wrong slot. cIGZCOMDirector: slot 13 is `GetDirectorID` in all 26 concrete directors. |
| `verify_fixed_headers.py` | Checks the fix branch (`C:\dev\gzcom-dll-fork`, pushed to `Drexel-Macintosh/gzcom-dll` as `fix-vtable-order`). Every method compiles to the game's slot with the game's argument bytes, cIGZApp and the director classes match, and all 31 `src\*.cpp` still compile. |
| `make_cigzwin_table.py`, `assemble_drafts.py` | Build `drafts\ISSUE.md` from `drafts\ISSUE.template.md` and the evidence, so no slot number is typed by hand. |

What the report does **not** claim: the order of cIGZApp's three identical
no-op hooks (slots 11-13) cannot be observed in this exe, so it comes from
the Mac symbols. It also covers only the Steam 1.1.641 exe, with GOG
spot-checked at 6 addresses.
