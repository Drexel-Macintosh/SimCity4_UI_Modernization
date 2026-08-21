# Byte-Scan the Compiled Artifacts

A text scanner cannot see a wide string, and it never opens a `.dll` at all. Any
privacy or secret check that reports a release bundle "clean" without reading
the compiled files as bytes has reported only that *the text files* are clean.

## How an absolute build path gets into a shipped DLL

A plain `assert()` in vendored SDK code is enough. Without `NDEBUG`, MSVC
expands `assert` to `_wassert(..., _CRT_WIDE(__FILE__), __LINE__)`, and
`_CRT_WIDE` bakes the compiler's **absolute** source path into `.rdata` as
UTF-16LE. The string is real, complete, and invisible to every scanner that
reads files as text, because each ASCII character is separated by a NUL byte.

`/PDBALTPATH:%_PDB%` does not fix this. It removes the ASCII PDB path from the
debug directory — a different string, in a different place. Treating it as *the*
fix for build-path leakage covers half the problem and leaves the wide string
untouched.

## The cure at the source

Add to the `.vcxproj` compiler options:

    /d1trimfile:"<repo root>\\"

This makes `__FILE__` relative at compile time. Behaviour is unchanged; asserts
still fire with the same line numbers.

The trailing backslash must be **doubled**. With a single backslash, MSVC reads
the closing quote as escaped and the build fails with
`D8003: missing source filename` — which looks like a corrupt project file
rather than a quoting bug, and sends the investigation in the wrong direction.

## How to actually check

Read the artifact as **bytes**, twice:

1. **Raw** — catches ASCII paths, PDB references, plain-text secrets.
2. **With NUL bytes stripped** — this pass is what turns a UTF-16LE string back
   into something a byte search can match.

For a `.zip`, scan the **central directory** as well. Entry names are stored in
the clear, so a path embedded in a *filename* is invisible to a scan of the
extracted contents.

## Two failure modes a binary scanner is prone to

**Zero items scanned is a refusal, never a pass.** An auto-picker that sorts a
`...-v2.93.1.zip` above the folder of the same name will hand `os.walk` a file
path; `os.walk` on a file yields nothing, the loop body never runs, and the tool
prints CLEAN having examined zero bytes. Any scanner must report its item count
and fail loudly when that count is zero.

**A reporting failure must not be mistakable for a detection failure.** A
scanner that crashes while *printing* a hit — for example on a byte the console
codepage cannot encode — is indistinguishable, from the outside, from a scanner
that crashed while *finding* one. Sanitise all output before writing it.

## Always run the negative control

Point the scanner at a binary known to be dirty — an older bundle that still
embeds a build path — and confirm it fails. A scanner that has never failed on
real input has not been tested, and its "clean" carries no information.
