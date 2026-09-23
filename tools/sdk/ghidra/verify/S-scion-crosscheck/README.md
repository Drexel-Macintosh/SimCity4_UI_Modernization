# S-scion-crosscheck — nsgomez/scion against the exe (2026-09-23)

[Scion](https://github.com/nsgomez/scion) (LGPL-2.1-or-later) is Nelson
Gomez's reimplementation of the Maxis GZ framework: COM, message servers,
files, strings, and the DBPF resource reader. He also wrote gzcom-dll. Its
README says it targets the SimCity 4 Deluxe build, and aims where it can for
machine code that matches when built with VS .NET 2003 and STLport.

| script | what |
|---|---|
| `header_diff.py` | Fetches Scion's interface headers into `_scion\` (gitignored), then compares each `cIGZ*` interface that both Scion and our gzcom-dll pin declare. |
| `exe_checks.py` | Settles each disagreement that matters against the exe's own code and our live log. It exits non-zero if the exe stops matching the table in `..\..\README.md`. |

Nothing from Scion is committed or copied into `src\`. The one Scion fact the
checks use is its resource director's ID, `0xC3CAEC3B`, as an anchor into the
exe.
