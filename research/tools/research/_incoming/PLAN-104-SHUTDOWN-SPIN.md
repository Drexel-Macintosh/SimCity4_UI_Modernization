# PLAN — #104: kill the shutdown spin, then restore the known-good visuals

*2026-08-03, written after the patcher hypothesis was refuted by measurement.
User priority: **fix the hang first, then get back to the good visuals**.*

---

## Where this stands

**Measured, 13 in-game runs.** The window closes, the process survives, one core spins
at 84–94%, `responding=True`. A deadlock burns no CPU — that reading alone invalidated
every hypothesis in the original filing. Our own cleanup is exonerated: the v2.56.0 probe
prints `SHUTDOWN 1/3 … 2/3 … 3/3 … done` in the same millisecond and returns.

```
stock / ScaleAll=0 / all-patches-off      CLEAN
full config, Budget NEVER opened          CLEAN
ORDINANCE + DEPT + Budget opened          SPINS 85%     <- culprit pair
each of the five other pairings           CLEAN
```

**Four constraints any correct mechanism must explain — all of them, not some:**
1. starts only *after* `PreAppShutdown` returns
2. requires the Budget dialog to have been opened
3. requires **both** families
4. busy loop, message pump still alive → a worker thread, not the UI thread

**NEW, and it redirects the whole investigation (2026-08-03, post-compaction).**
The leading hypothesis — "one family's write breaks the other's verify, leaving a
half-patched layout" — is **REFUTED**. Diffing the preserved bisect logs:

| run | ordinance | budget family |
|---|---|---|
| run8 ordinance-only | `8 of 8 sites` | — |
| run9 dept-only | — | `54 imm8 + 63 imm32 + 53 sub-imm8 + 17 lea-disp8 + 2 notch`, bizbox 7 |
| run13 **both — SPINS** | `8 of 8 sites` | **identical: 54 + 63 + 53 + 17 + 2**, bizbox 7 |

Not one site declines. **Positive control for this null** (required — a probe that finds
nothing is not a fact until you show it could have seen the thing): these appliers *do*
log declines, per-site `bytes unexpected - skipped` plus an `(n of 8)` summary, and this
exact format historically reported a real decline at `0x0077F5B9`, fixed in v2.28.2.

> **The interaction is at RUNTIME, not in the patcher.** Both patch sets apply fully and
> identically whether alone or together. Two individually-correct layouts together
> produce a state neither produces alone.

**The coupling shape this implies.** The families' *sites* are disjoint but their
*effects* are not: `ApplyBudgetFamilyScale` patches **ordinance-dialog constants** —
the right margins `0x77C9D6 / 0x77CCD7 / 0x77CDE6 / 0x77CE78 / 0x77D1E5 / 0x77D2FD`
(`W-38`) and the scroll-arrow anchors `0x77D61C / 0x77D661 / 0x77D6A6 / 0x77D6EB`
(`W-33`) — plus the shared factories `sub_7794E0` (slider H) and `sub_7798C0` (combo H)
and the shared text popup `0x0423278D`. So *dept-on* scales the ordinance dialog's
**right** side, *ordinance-on* scales its **left** side, and only with both does its
content box get squeezed from both ends at once. A `remaining = W - leftInset - rightMargin`
that only goes negative when both terms grew is a textbook pair-only bug and fits all four
constraints. **This is a hypothesis with a shape, not a finding. It must be confirmed
positively** — the scoreboard on invented mechanisms today is 0 for 2.

---

## Phase 1 — mechanism, offline *(running)*

Workflow `wf_125cf750-f9e`, relaunched with the refutation baked in so no agent spends
budget re-deriving a dead lead. Three angles: the runtime coupling arithmetic (with the
squeeze calculation above as its first task), which teardown loop can spin, and whether
the `136→127` clamp is load-bearing (decisive sub-question: *is that x ever read back, or
is it write-once at creation?* — if write-once, that thread is dead).

**Gate on the result:** do not accept a mechanism that merely *fits*. Require a positive
confirmation, require it to reduce to stock at f=1, and require it to leave the
user-confirmed 2x budget dialogs (#61–#69) untouched.

## Phase 2 — SPINPROBE: name the loop instead of deducing it — ✅ BUILT v2.57.0

*Status: `src\SpinProbe.{h,cpp}` built clean, armed by `[UiSpike] SpinProbe=10`,
deploying on the next game close. Awaiting one capture run.*


**This is the highest-value step in the plan and it should not wait on Phase 1.** Every
time inference lost to measurement in this project, the fix was to build the instrument.
We have never once looked at *what the spinning thread is actually executing* — and one
address ends the argument.

Our DLL is already inside the process, so no debugger, no elevation dance, no external
tool. Add a watchdog behind `[UiSpike] SpinProbe` (**default 0**):

* arm at the end of `PreAppShutdown`, spawn one sampler thread
* for ~10 s at ~20 Hz: `Thread32Next` over our own process, skip our own tid, then
  `SuspendThread` → `GetThreadContext(CONTEXT_CONTROL)` → **`ResumeThread` immediately**
* buffer EIPs in a fixed array; **never touch the logger while a thread is suspended**
  (that is the one way this probe could itself deadlock shutdown)
* on finish, log a histogram: top EIPs, `eip - imageBase` so it reads straight against
  the disassembly, and the owning tid

Any EIP landing in `0x0077xxxx–0x0079xxxx` names the loop outright. Cost: one build, one
launch, one hang the user already gets for free. Risk: bounded — off by default, no
suspend held across a lock, hard iteration cap.

*Fallback if the in-process probe proves unsafe:* built-in Windows minidump,
`rundll32 comsvcs.dll MiniDump <pid> <path> full`, elevated, while it spins — then parse
`MINIDUMP_THREAD_LIST` thread contexts with a small Python struct reader. No download.
Read-only on an already-stuck process, so it cannot endanger the dats.

## Phase 3 — the fix

Shape depends on what Phases 1–2 name. Pre-committing to the two likely ones:

* **If a computed width inverts** — clamp it at its source (a floor of 0 or a minimum
  content width), not by unscaling a constant. Unscaling regresses a user-confirmed fix.
* **If the `136→127` clamp is load-bearing** — the honest cure is to stop shipping a value
  we did not intend. `push imm8` (`6A xx`, 2 bytes) cannot hold 136 and `push imm32`
  (`68 …`, 5 bytes) does not fit in place, so this becomes either a runtime pin on those
  two name-column windows or a same-length block re-encoding. **A re-encoding must be
  capstone round-tripped in a durable gate before it ships** — pattern:
  `tools\uimap\emu\gate_graphlegend_leftanchor.py` (length, boundary, imm32, branch
  targets).

**Acceptance for the fix — all four, in one launch:**
1. open Budget, open Ordinances, open a slider department, close the game → **clean exit**
2. repeat with a *second* city (address reuse is how #92 hid)
3. ordinance rows, dept sliders and Accept/Cancel all still correct on screen
4. `crosscheck.py` and the born-correct suites still green

## Phase 4 — restore the known-good visuals *(the user's second half)*

Only after Phase 3 passes:

1. restore the full config — `copy SC4UIScale.ini.104-backup → SC4UIScale.ini`, and
   **`BudgetButtonPatch` back to 1** (it is at 0 from the bisect, which is why
   Accept/Cancel currently render wrong). ⚠ **no BOM, ever** — the DLL abandons the file
   and boots windowed.
2. build + deploy via `_tests\Deploy-OnGameClose.ps1`, hash-verify
3. eyes-on sweep: Budget dialogs, Ordinances, Graphs legend (#57), dashboard
4. **two consecutive clean exits** before calling it closed

## Phase 5 — close the gap that let this ship

**Our byte-patch families are not independent, and nothing tests them in combination.**
`crosscheck.py` verifies every site in isolation; #104 is invisible to every gate we own.
Build `tools\uimap\emu\gate_patch_families_combined.py`: parse all site tables out of
`src\CodePatches.cpp`, compute each site's verify-range and write-range from its actual
encoding width, and assert no two ranges overlap across families — then extend it to the
*effect* level, flagging any dialog whose left and right constants are owned by different
ini flags. That second half is the one that would have caught this bug.

---

## Order, and why

Phase 2 is independent of Phase 1 and should be built while the workflow runs — it is the
only step that can *end* the question rather than narrow it. Phase 1 may make it
unnecessary; it may also return three plausible stories, in which case the probe is what
adjudicates between them. Phases 3–4 are strictly gated on a confirmed mechanism.

**Interim escape if the game must be playable before the fix lands:** set
`OrdinanceInsetPatch=0` — clean exits, at the cost of clipped ordinance row text. The
user has chosen to leave the ini mid-bisect for now, so it currently renders budget
buttons wrong *and* hangs.
