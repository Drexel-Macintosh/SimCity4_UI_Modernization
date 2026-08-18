---
name: feedback-docs-are-the-sdk
description: "NORTHSTAR METHOD (all projects): our own docs + decompilation ARE the SDK manual. THE LOOP IS MANDATORY AND CLOSED — every bug STARTS by checking it against the SDK lookup, the lessons/laws and the docs, and every fix ENDS by updating the documentation in the same session. Consult in a fixed order before experimenting."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: f1160943-a698-434b-a6bf-d3c3e2971cea
  modified: 2026-08-01T01:00:48.376Z
---

**User order, 2026-07-30 (SC4 UI scaling, after three failed builds):**
*"update your northstars to INCLUDE using all of your documentation /
backward decompiling similar to an SDK guide that provides instructions. If
we have to do something new / novel document it for future use!"* — preceded
by: *"I just feel that you haven't been referring to your own playbooks and
testing. It's like a regression of discipline when you should be checking
your own documentation THAT YOU CREATED."*

**USER ORDER, 2026-07-31 (added after a day in which four wrong theories
shipped on one window because old notes were trusted and new findings were
written late): THE LOOP IS CLOSED AND BOTH ENDS ARE MANDATORY.**

> **EVERY BUG STARTS HERE — before any theory, any agent, any build:**
> 1. **Run the SDK lookup** on the id/art/script involved
>    (`python tools\sdk\lookup.py <id>` in SC4; the equivalent index in any
>    other project). It returns our lists, the declaring script, what we ship
>    at every tier, who wins the load order, and every line already written.
> 2. **Match the symptom to a solved family** in the lessons/laws
>    (`TRIAGE.md`, [[feedback-sc4-scaling-laws]]) — most defects are a
>    repeat, and the cure is usually already named.
> 3. **Check the generation/status docs** (`MECHANISM-GENERATIONS.md`,
>    `REGRESSION.md`) before designing anything.
> 4. **Only then** measure, and only after that build.
>
> **EVERY FIX ENDS HERE — in the SAME session, before moving on:**
> 1. `VERSION-HISTORY.txt` — what changed and WHY, including what was
>    refuted.
> 2. `_tests\REGRESSION.md` — the runbook entry: expected log lines,
>    acceptance, trap signature, revert.
> 3. The mechanism doc (`SC4-UI-ENGINE.md` / the family's own file) — how it
>    actually works.
> 4. `TRIAGE.md` if a new SYMPTOM→cause row was earned; the laws memory if a
>    new LAW was earned; `HANDOFF.md` for the current state.
> 5. **Correct anything the fix PROVED WRONG** — a stale note left standing
>    is a future wrong theory. Say "refuted", name the replacement.
>
> A fix is not done when the code works; it is done when the next reader
> cannot repeat the mistake.

**The three rules (they apply to every project here, not just SC4):**

1. **THE DOCS ARE THE SDK.** These projects reverse-engineer undocumented
   binaries (SC4, Surface 1.0, XNA/WPF ports, GM nav discs). The reference
   docs we wrote ARE the vendor manual — read and QUOTE the element's own
   section before acting. An answer already written down may not be
   rediscovered by experiment.
2. **DECOMPILE FOR INSTRUCTIONS, NOT FOR CLUES.** Read the function, name
   the constant, prove the byte pattern, then patch — offline, verify-before-
   write, values expressed as math (`round(stock × f)`), never a literal.
3. **DOCUMENT THE NOVEL IN THE SAME SESSION** — new mechanism, decoded
   function, new tool, or a failure with a real mechanism behind it. Chat is
   not storage.

**THE INSTRUCTION HIERARCHY — an order, not a menu:**
our docs → the SDK/vendor headers → the live instruments and logs → the
disassembler → a shipped experiment. The last is the most expensive move
available (a build + the user's test session) and is exactly what gets
reached for when the first four are skipped.

**Why:** three ordinance-popup builds were burned while our own
`BUDGET-DETAIL-ANATOMY.md` §1 (written the same day) already recorded the
wrap constant `1000 − textWidth` at `0x77971A`, and `cIGZFont.h` already
carried a wrap API. Both were free to read.

**How to apply:** run the PRE-FLIGHT before touching any UI defect —
re-read + quote the doc → check the failed-attempts table → confirm a STOCK
capture of that exact element exists → measure live rects → state the fix as
math that reduces to stock at f=1 → code → verify from the log → write back
what was novel. Canonical text:
`SC4TouchControls\tools\research\METHOD.md` (§1 hierarchy, §2 pre-flight,
§3 doc routing, §4 decompilation playbook, §5 write-back contract).

Related: [[project-sc4-ui-scaling-northstar]], [[feedback-sc4-measure-dont-infer]],
[[feedback-sc4-scaling-laws]], [[reference-sc4-flyout-hittest-playbook]],
[[feedback-sc4-regression-net]], [[feedback-usb-bundle-self-contained-readmes]].
