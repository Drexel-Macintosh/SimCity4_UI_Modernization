---
name: feedback-state-machine-derive-diff-commit
description: "SC4 selector: a per-tick megafunction accreted over six generations breeds two-sources-of-truth defects and dead mechanism nobody dares delete. Cure shape = one state struct, one pure derive (spec written FIRST as a python gate), diff-apply (rebuild a combo only when derived rows differ, only on a selection-change tick), commit-at-close writing only changed keys. The player's pick is a REQUEST; effective = request-if-usable-else-Auto, so bounce and un-bounce need no state."
metadata:
  node_type: memory
  type: feedback
  originSessionId: f1160943-a698-434b-a6bf-d3c3e2971cea
  modified: 2026-08-20T00:00:00.000Z
---

The in-game scale selector began as a ~250 ms service function and accreted
six generations of mechanism (~1,400 lines). By the rewrite, a log census
found the generations living together, several measured dead and still
running: a coordinate trace logging every click twice anywhere on screen; a
message trace whose question had been answered; a pointer calibration
feeding only dead paths; a chained winproc whose only outputs had no
readers; an Accept detector keyed on the game writing its graphics ini —
measured dead (3 Accepts, 3 "no write ever seen"). **Accretion does not just
cost CPU; it breeds two-sources-of-truth defects**, and those were the ones
the user actually met:

- Two widgets displaying one fact (a readout label AND a combo showing the
  active tier) — which is how they drift apart.
- An idempotence check keyed on a retired node's id — *"an idempotence check
  that names a retired node is not idempotent, it is OFF"* — so a second
  pass would have injected duplicate controls.
- A refusal that bounced to the previous row and never undid itself (the
  audit finding "the bounce never undoes") — because the bounce was stored
  as STATE instead of derived.

**The cure shape (all of it shipped in one build):**
1. **One state struct.** ALL facts, read at defined moments. Session facts
   cached once (display enumeration from the warm thread, boot mode, package
   census); visit facts read ONCE per open (both inis, the dll, the render
   size); staged requests reset per visit.
2. **One pure derive: `SelDerive(state) -> UI`.** No side effects, no
   syscalls, no logging. Every rule lives here and only here. **The spec was
   written FIRST as a python gate** (`_tests\Test-SelectorDerive.py`,
   transition rows + swept invariants) and the C++ mirrors it row for row —
   the gate is the executable contract, not a retrospective.
3. **Diff-apply.** A combo is rebuilt only when its derived rows DIFFER from
   what was last pushed, and only on a tick a selection changed — which
   implies every drop list is closed, so a rebuild can never mutate an open
   drop. `RemoveAllStrings` exists in exactly ONE function.
4. **Commit at close.** Accept is the only exit (Cancel/Default ship
   disabled), so a close re-reads the controls and writes **only keys whose
   values changed**. An untouched visit writes nothing.
5. **The player's pick is a REQUEST that is never overwritten.** The
   EFFECTIVE row derives fresh each pass as "request if usable else Auto".
   Bounce AND un-bounce need no state machine — stage a small resolution and
   the row falls to Auto; stage the old one back and the request fits again.
   The audit finding closed **by construction**, not by a patch.

**The pair gate:** a source-shape contract gate
(`_tests/Test-SelectorContract.py`) asserts the tick is a poll (no
syscalls/mutations), the derive is pure, the destructive combo call lives in
one function, and the commit writers are called only at close — and its
negative controls trip (an injected write is caught; a commented one is
stripped). A gate that passes on the fixed code proves nothing until it
fails on the broken code.

**How to apply:** when a per-tick function has accreted generations, do not
patch generation seven onto six — strip to a state struct + pure derive,
write the derive's spec as a gate FIRST, diff-apply so mutation happens only
on real change, and commit at the boundary (close), never mid-visit.
Anything that can be derived must not be stored: stored state is the second
source of truth, and the two WILL drift.

Related: [[feedback-selector-freeze-named-by-instrument]],
[[feedback-liveness-guard-stored-window-pointers]],
[[feedback-gate-on-the-condition-you-depend-on]]
