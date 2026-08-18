---
name: feedback-batch-files-need-crlf
description: "Every .cmd/.bat I write MUST have CRLF line endings - the Write tool emits LF, and cmd.exe silently jumps to the wrong place on call:/goto in LF-only batch files"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 66d6eac4-ae37-47e9-a7a4-29cbe477699e
  modified: 2026-07-31T01:18:55.250Z
---

Any `.cmd` / `.bat` file must be written with **CRLF** line endings. The Write tool emits
bare LF, and cmd.exe mis-executes LF-only batch files: `call :label` / `goto :label` land at
the **wrong byte offset**, so control jumps into unrelated blocks. It fails *silently* — no
error, the script just does the wrong things.

**Why:** cmd.exe seeks batch files by byte offset and its line handling assumes CRLF. This
cost a long misdiagnosis on `Apps-x64\2b Install-Apps-VISTA.cmd` / `3b Uninstall-Apps-VISTA.cmd`:
the reported "dies after ~6 apps" and "the script loops and does odd things" were BOTH this,
not the logic. I wrongly blamed `goto :eof` inside a called routine and restructured both
routines into if/else chains — that changed nothing. Proof: identical script, LF = 42 app
lines / 3 summary blocks / 2 apps repeated; CRLF = 41 / 1 / 0.

**How to apply:** after writing any .cmd/.bat, convert it:
`$t=[IO.File]::ReadAllText($p); [IO.File]::WriteAllText($p, $t.Replace("`r`n","`n").Replace("`n","`r`n"))`
then assert zero bare LF: `([regex]::Matches($t,"(?<!\r)\n")).Count -eq 0`.
Scripts with no labels (plain wrappers) survive LF by luck — fix them anyway.
`.ps1` is unaffected; PowerShell reads LF fine.

**SAME FAMILY — the tool's default encoding silently breaks a Windows consumer.
Cost a live debugging round 2026-07-30: NEVER repair a game config file with
`Set-Content` / `Out-File -Encoding utf8`.** In this environment that emits a
**UTF-8 BOM** onto line 1. SimCity 4's `SC4GraphicsOptions.dll` v1.4.0 then
logged `<unspecified file>(1): '=' character not found in line`, abandoned the
whole file and booted **windowed at the wrong resolution** — the user had to
notice, nothing else reported it. `Get-Content | Set-Content` also silently
rewrites LF → CRLF across the file (+86 bytes there).
**To repair any game ini: `Copy-Item` the known-good file byte-for-byte and
hash-verify, or write raw bytes — never round-trip through a text cmdlet.**
Afterwards check the first three bytes (`ef bb bf` = broken). And read the
consumer's OWN log first (`SC4GraphicsOptions.log`): it named the failing line
number immediately, before any theorising.

Related: [[feedback-usb-bundle-self-contained-readmes]], [[project-touch-pack-win11]],
[[reference-sc4-golden-backup]], [[reference-sc4-resolution-control]]
