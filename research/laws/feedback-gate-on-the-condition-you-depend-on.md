# Gate on the Condition You Depend On

Bolting new work onto a convenient existing function makes that work inherit the
function's gate, silently.

## The failure

An uncovered-icon scan was folded into `SyncStaticLayers`, on the reasoning that
this was already the boot point deciding which art the game sees. But
`SyncStaticLayers` only runs on the **AutoScale** path; manual tier mode places
its packages by hand and never calls it. The scan therefore inherited the
AutoScale gate it had no relationship to.

With `AutoScale=0` — a supported setting, not a misconfiguration — the scan never
ran, the count came back 0, and the following stage logged *"nothing uncovered,
no work to do."* The entire cure was off and the log read as healthy.

This is nasty because **a scan that never runs reports zero findings, which is
byte-identical to a clean result.** It is the same shape as any null result: an
absence of findings is not evidence until the probe is proven capable of seeing
the thing.

## The rule

- Gate a subsystem on the condition **it** depends on, and nothing else. The
  scan above depended only on `factor > 1`; it never cared how the factor was
  chosen.
- Before adding work to an existing function, ask what that function is gated
  on and whether the new work genuinely shares that condition. If it does not,
  the work needs its own entry point.
- Suspect an inherited gate whenever a feature works in the default
  configuration and vanishes in a supported alternative one: manual mode, a
  flag, a second monitor, a clean install.
- Give a scan a positive control, or make a zero result distinguishable from a
  skipped run — log "scanned N candidates, 0 uncovered" rather than "no work to
  do", so the absence of the scan is visible in the absence of the line.

The generalization: code that assumes the common case fails only in the
alternative one, where nobody is looking. Deploy steps that hard-copy an
optional package, and integrity gates that assert a fixed count of something
that varies per installation, are the same defect wearing different clothes.
