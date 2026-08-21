# State, Derive, Diff, Commit

A reusable architecture for an in-game dialog built on this engine. The dialog
owns one state struct with defined read moments, one pure derive function whose
spec is written first as an executable gate, diff-apply so a rebuild can never
mutate an open drop list, commit-at-close that writes only changed keys, and a
request-versus-effective split that removes the need for bounce state.

## Why the shape matters

The in-game scale selector started as a roughly 250 ms service function and
accreted six generations of mechanism, reaching about 1,400 lines. A log census
of the accreted version found the generations coexisting, several of them
measurably dead and still executing every tick:

- A coordinate trace logging every click twice, anywhere on screen.
- A message trace whose question had already been answered.
- A pointer calibration feeding only dead paths.
- A chained window procedure whose only outputs had no readers.
- An Accept detector keyed on the game writing its graphics ini, measured dead
  across three Accepts with three "no write ever seen" results.

Accretion costs CPU, but the expensive failure is different: it breeds
two-sources-of-truth defects. The ones that reached the screen were

- **One fact displayed by two widgets** — a readout label and a combo both
  showing the active tier. Two renderings of one fact drift apart.
- **An idempotence check keyed on a retired node's id.** An idempotence check
  that names a retired node is not idempotent, it is off; a second pass would
  have injected duplicate controls.
- **A refusal that bounced the selection to the previous row and never undid
  itself**, because the bounce was stored as state instead of derived.

## The five parts

1. **One state struct.** Every fact the dialog uses, read at defined moments.
   Session facts are cached once (display enumeration from the warm thread, boot
   mode, package census). Visit facts are read exactly once per open (both inis,
   the DLL, the render size). Staged requests reset per visit.

2. **One pure derive: `SelDerive(state) -> UI`.** No side effects, no syscalls,
   no logging. Every rule lives here and nowhere else. The spec is written first
   as a Python gate (`_tests\Test-SelectorDerive.py`: transition rows plus swept
   invariants) and the C++ mirrors it row for row. The gate is the executable
   contract, not a retrospective description of whatever the code ended up
   doing.

3. **Diff-apply.** A combo is rebuilt only when its derived rows differ from
   what was last pushed, and only on a tick where a selection changed. A
   selection change implies every drop list is closed, so a rebuild can never
   mutate an open drop. `RemoveAllStrings` appears in exactly one function.

4. **Commit at close.** Accept is the only exit — Cancel and Default ship
   disabled — so closing re-reads the controls and writes only the keys whose
   values changed. A visit that touches nothing writes nothing.

5. **The player's pick is a request that is never overwritten.** The effective
   row derives fresh on each pass as "request if usable, else Auto". Bounce and
   un-bounce then need no state machine at all: stage a small resolution and the
   row falls to Auto; stage the old one back and the request fits again. The
   defect closes by construction rather than by a patch.

## The pair gate

A source-shape contract gate (`_tests/Test-SelectorContract.py`) asserts that
the tick is a poll (no syscalls, no mutations), that the derive is pure, that
the destructive combo call lives in one function, and that the commit writers
are called only at close. Its negative controls trip: an injected write is
caught, and a commented-out one is stripped before the check so comments cannot
create a false positive. A gate that passes on the fixed code proves nothing
until it has been shown to fail on the broken code.

## Applying it

When a per-tick function has accreted generations, do not patch generation seven
onto generation six. Strip to a state struct plus a pure derive, write the
derive's spec as a gate first, diff-apply so mutation happens only on real
change, and commit at the boundary (close), never mid-visit.

Anything that can be derived must not be stored. Stored state is the second
source of truth, and the two will drift.
