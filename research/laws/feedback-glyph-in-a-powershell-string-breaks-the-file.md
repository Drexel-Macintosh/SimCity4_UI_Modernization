# ⛔ A ⛔/⚠ GLYPH INSIDE A POWERSHELL *STRING* SILENTLY BREAKS THE FILE

Put one in a comment and nothing happens. Put the same glyph inside a quoted
string and the script stops parsing — with an error that points at a line
nowhere near the glyph and describes something you did not write.

Found 2026-08-29 while updating `_tests/Toggle-SaveWarningUI.ps1`.

## The mechanism

The `.ps1` files in this repo carry **no BOM**, so Windows PowerShell 5.1
decodes them as ANSI, not UTF-8. A `⛔` is `E2 9B 94` in UTF-8, and read as
ANSI (cp1252) that becomes:

```
E2  ->  â
9B  ->  ›
94  ->  ”      <- U+201D RIGHT DOUBLE QUOTATION MARK
```

**PowerShell accepts U+201D as a closing double quote.** So the string ends in
the middle of the line, and everything after it — your prose — is parsed as
code. The reported error is whatever that prose happens to look like:

```
"⛔ do not 'fix' this"      ->   Missing statement body in do loop
```

The error names `do`, a keyword that appears only because the sentence
contained the word "do".

## Why comments get away with it

A comment runs to end-of-line, so the mangled bytes are consumed harmlessly.
That is the whole reason the house style — which uses these glyphs constantly
in comments — has never tripped over this. The rule is not "no glyphs"; it is
**glyphs live in comments, never inside quotes**.

## The rule

* Non-ASCII in a `.ps1` **comment**: fine, and keep doing it.
* Non-ASCII in a `.ps1` **string literal**: don't. Write the word.
  `Write-Output "REFUSING: ..."`, not `Write-Output "⛔ REFUSING: ..."`.
* If a `.ps1` must carry non-ASCII in a string, the file needs a UTF-8 BOM —
  and then every other tool that reads it has to agree, which is a bigger
  change than the glyph is worth.

## The tell

An error that names a keyword you never typed, on a line whose code looks
fine, in a file you just added a glyph to. Before debugging the logic, run:

```powershell
Select-String -Path .\script.ps1 -Pattern '[^\x00-\x7F]' |
    Where-Object { $_.Line -notmatch '^\s*#' }
```

Anything that returns is a candidate. An empty result is only evidence if the
same command DOES return the glyphs in your comment lines — drop the
`Where-Object` to prove the scan works before believing the zero.

## The general shape

⭐ **AN ENCODING MISMATCH DOES NOT FAIL AT THE BYTE THAT IS WRONG.** It fails
wherever the mis-decoded byte happens to mean something to the parser, which
can be lines away and in an unrelated construct. This project has now paid for
this twice in one day, in two languages: here, and in the `\010-` octal escape
that put a literal backspace into five published paths (see the v4.4.0
commit). Both times the symptom pointed somewhere other than the cause.

Context: [[arming-must-be-additive-and-pre-scan]]
