---
name: feedback-text-scanners-are-blind-to-binaries
description: "Before publishing ANY compiled artifact, byte-scan it — raw AND with NUL bytes stripped. A shipped DLL carried the full build path as a UTF-16 string in .rdata (from assert()/_CRT_WIDE(__FILE__)) after two independent TEXT scanners called the bundle clean. Cure: /d1trimfile. Check: _tests\\Test-BinaryPii.py."
metadata:
  node_type: memory
  type: feedback
  originSessionId: f1160943-a698-434b-a6bf-d3c3e2971cea
  modified: 2026-08-06T13:31:39.515Z
---

# A text scanner cannot see a wide string, and never opens a .dll at all

2026-08-06, one step from the first public GitHub Release. Two independent
privacy scanners had both reported the bundle clean. The shipped DLL contained
this in `.rdata`, as **UTF-16LE**:

    C:\Users\<user>\...\vendor\gzcom-dll\...\cRZCOMDllDirector.cpp

**Where it comes from:** a plain `assert()` in vendored SDK code. Without
`NDEBUG`, MSVC expands assert to `_wassert(..., _CRT_WIDE(__FILE__), __LINE__)`
and `_CRT_WIDE` writes the compiler's **absolute** source path as wide chars.

**Why every earlier check missed it.** `/PDBALTPATH:%_PDB%` had removed the
ASCII PDB path from the debug directory, and the publish plan, the changelog
and the ship manifest all recorded that as *the* fix. It was half of one.
Text scanners read files as text: they cannot see a UTF-16 string, and they do
not open binaries at all. Their "clean" meant *the text files are clean*.

## How to actually check

    python _tests\Test-BinaryPii.py [bundle-dir | bundle.zip]

Read **bytes**, twice — raw, then with NUL bytes stripped. The second pass is
what turns UTF-16 back into something a byte search can find. For a `.zip`,
scan the **central directory** too: entry names are stored in the clear, so a
path inside a *filename* is invisible to a scan of extracted contents.

**Cure at the source:** `/d1trimfile:"<repo root>\\"` in the vcxproj — makes
`__FILE__` relative at compile time, changes no behaviour (asserts still fire).
⚠ The trailing backslash must be **doubled**, or MSVC reads the closing quote
as escaped and the build dies with `D8003: missing source filename` — which
looks like a broken project file, not a quoting bug.

## Two bugs in the new scanner, both found in its first five minutes

* Its auto-picker sorted `...-v2.93.1.zip` above the **folder** of the same
  name. `os.walk` on a file yields nothing, so it scanned **zero files and
  printed CLEAN**. → *Zero items scanned is a REFUSAL, never a pass.*
* It crashed while **printing** a hit (a byte the console codepage could not
  encode), which reads exactly like a crash while **finding** one. → Sanitise
  output; a reporting failure must not be mistakable for a detection failure.

**Always run the negative control.** Point it at a binary known to be dirty
(here: the frozen `dist\SC4TouchControls-v1.0.4/v1.0.5` bundles, which still
embed the path and must never be attached to a Release). A scanner that has
never failed on real input has not been tested.

Related: [[project-sc4uiscale-github-publish]], [[feedback-null-is-not-evidence]],
[[feedback-blind-instruments-agreeing]],
[[feedback-never-repin-a-fingerprint-without-reading-the-bytes]].
