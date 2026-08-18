# #104 SPINPROBE captures — 2026-08-03

⚠ **`SC4UIScale.log` is RECREATED ON EVERY LAUNCH.** The run-14 spin log was overwritten
by run 15 before it was copied to `_tests\captures\`. Everything below under "run 14" is
recovered from the session transcript, not from a file. **Copy the log to
`_tests\captures\` immediately after every probe run** — the bisect runs 6–13 were
preserved that way and these two nearly were not.

---

## run 14 — 17:16, v2.57.0, `SpinProbe=10` — **SPUN**

Config: `ScaleAll=1 OrdinanceInsetPatch=1 BudgetDeptPatch=1 BudgetButtonPatch=0`, city
loaded, Budget opened (Ordinances sub-dialog visible in the user's screenshot).

Probe positive control: self-test sweep captured **46 samples from 46 threads** — the
instrument could see.

```
SPINPROBE FINAL 1286 samples over 73 sweeps; threads seen 1307, opened 1289,
open-failed 18, ctx-failed 3; 50 distinct EIPs across 47 threads.
  #1  727 hits (56%) eip=0x7700B81C  ntdll.dll     tid 26508
  #2  153 hits (11%) eip=0x76935F7C  win32u.dll    tid 36328
  #3   87 hits ( 6%) eip=0x77009F6C  ntdll.dll     tid 5624
  #4   77 hits ( 5%) eip=0x769311DC  win32u.dll    tid 34712
  #5   71 hits ( 5%) eip=0x7700B6AC  ntdll.dll     tid 11252
  #6   70 hits ( 5%) eip=0x770099DC  ntdll.dll     tid 27604
  #7   12 hits ( 0%) eip=0x7700BE10  ntdll.dll     tid 32184
  #8   11 hits ( 0%) eip=0x009DC087  SimCity 4.exe tid 36888   <-- GAME CODE
  #9   10 hits ( 0%) eip=0x7700B7EC  ntdll.dll     tid 25184
  #10   8 hits ( 0%) eip=0x77009CFC  ntdll.dll     tid 36888
  #11   7 hits ( 0%) eip=0x009DB9CB  SimCity 4.exe tid 36888   <-- GAME CODE
  #12   3 hits ( 0%) eip=0x009DC4AC  SimCity 4.exe tid 36888   <-- GAME CODE
```

**tid 36888 was the only thread executing game code.** Independent corroboration with a
different failure mode: in a `Get-Process().Threads` snapshot the same tid was the only
one in `ThreadState=Running`; all others were `Wait`. Process-level CPU delta measured
**97.2% of one core over 4.02s wall**.

(A per-thread `TotalProcessorTime` delta was also attempted and returned 0 ms for every
thread, contradicting the process-level 97%. That instrument was not measuring — it is
recorded here as discarded, not as evidence.)

Disassembly of the three game EIPs (capstone, verified against the on-disk exe):

* `sub_9DB9B1` — **hash-map find**. `div edi` → `edx = (key>>2) % bucketCount`, then the
  collision-chain walk `cmp [eax+4],esi / mov eax,[eax] / jne` at `0x9DB9D3..0x9DB9DC`.
  **A cycle in a bucket chain makes this non-terminating.**
* `sub_9DC087` — its caller, a Contains/Find predicate: `add ecx,0x44` (**the map lives at
  this+0x44**) then `call 0x9DB9B1`.
* `sub_9DC4AC` — follows a loop at `sub_9DC47B` that iterates the *same* `+0x44` map
  calling `vt[0x16C]` per entry.

`0x99xxxx` is cIGZWin in our notes; `0x9Dxxxx` was previously **unmapped**.

## run 15 — 17:27, v2.57.1, `SpinProbe=120` — **CLEAN**

**Same patch config. Same city. Budget opened (identical screenshot).**

The process exited **~1 second after `PreAppShutdown` returned**. The log holds exactly
one partial report (17:27:53.783) and **no `FINAL` and no `done` line** — the 120 s
sampler thread died with the process long before its deadline.

Probe positive control: self-test captured **47 samples from 47 threads**.
Verdict line: `NO thread sampled inside the game image` — **zero** game-image samples
across all 47 threads in that first second.

Preserved: `_tests\captures\2026-08-03-104-run15-ordinance-plus-dept-budget-CLEAN.log`.

---

## THE FINDING, and what it costs us

**#104 IS INTERMITTENT.** Two runs, identical patch configuration and identical user
actions, opposite outcomes. This is not a config-determined bug.

**Consequence for the 13-run bisect (runs 6–13): its CLEAN verdicts are not sound.**
Each configuration got **one trial**. For an intermittent failure a single clean run is a
coin flip, not evidence — the same "null is not evidence" law we apply to probes applies
to our own experiment design. Specifically:

* "Ordinance alone CLEAN / Dept alone CLEAN / Button alone CLEAN / Dept+Button CLEAN /
  Ordinance+Button CLEAN" may each be a lucky run.
* Therefore **`OrdinanceInsetPatch + BudgetDeptPatch` is NOT established as the culprit
  pair.** It is one config observed to spin at least once.
* The genuinely solid results are the ones where something *was* observed: run 14's spin,
  and the four constraints. Positive observations survive; the nulls do not.

The one bisect null that is still worth something is **"full config, Budget never
opened → CLEAN"**, because it was consistent with the user's lived experience over many
sessions. Even that deserves repetition before it is leaned on.

## THE RUNTIME-COUPLING HYPOTHESIS IS ALSO REFUTED (workflow wf_125cf750-f9e)

The replacement hypothesis I wrote into this plan — "dept scales the Ordinances dialog's
RIGHT margins while ordinance scales its LEFT insets, so `remaining = W − leftInset −
rightMargin` only goes negative when both are on" — **is dead too.** Measured, not argued:

* **The shared factories are not shared.** Direct-call closure of the Ordinances builder
  `sub_77C660` (rebuilt from `tools\uimap\_work\edges.json`): 159 functions reachable;
  `0x7794E0` **False**, `0x7798C0` **False**, `0x78B120` **False**, `0x7EAEB0` **False**.
  *Positive control:* the same closure returns True for `0x779660`, `0x77B960`,
  `0x77BEC0` — two of them patched — so it does find patched functions when present.
  *Scope, stated honestly:* direct edges only; the builder makes 66 indirect calls.
* **No loop on this path can be geometry-terminated.** 1388 instructions disassembled
  across `0x77C660..0x77D7E0`; **5 backward jumps, all count-bounded** (`[esi+0xA0]` =
  ordinance count, reloaded each pass, plus a `cmp eax,9/jae` visible-row cap).
* **The patched values are write-only.** Of 66 indirect calls, **not one** is at a
  geometry-getter offset (`+0xA4/+0xA8/+0xC0/+0xC4/+0xC8/+0xDC`). *Positive control:* the
  scanner does report all 66, so it can see the instruction form and simply finds no
  getters. A coordinate consumed once at creation and never read back cannot become a
  loop bound.
* **`push 0x63` occurs ZERO times** in this builder — and `align==0x63` is the only
  branch of `sub_779660` that converts an inset into a width. The content-box arithmetic
  the squeeze story requires **does not exist here**.
* **The 136→127 clamp is not the differentiator.** run8 (CLEAN) and run13 (SPIN) carry the
  *identical* two clamp lines and the identical `8 of 8 sites`.

**Do not ship the Phase-3 fix shapes.** An imm8→imm32 re-encode would change a
user-confirmed 2x layout on static reasoning alone (the #98 law) and, per the above,
would not touch the spin. "Make one family decline when the other is armed" is worse —
it regresses a confirmed layout to fix nothing.

A pair-only runtime state *does* exist and is measurable at open (checkbox x 36/18/36,
strip x 68/34/68, value texts x 867/834/834, left button x 14/28/28 for
ord-only/dept-only/BOTH) — **but it is not degenerate.** 2500+ rects scanned across all 8
logs: **0 negative, zero or oversize rects in every run**, and the only 0x0 rects appear
in CLEAN runs too.

### Two independent confirmations that the bisect is unsound

Arrived at by completely different routes, which is what makes them worth something:

1. **My route:** re-ran the spin config and got a CLEAN exit (run 15 above).
2. **The workflow's route:** the runs were never controlled. Using MWKID root-dump count
   as an activity proxy — run6=7, run7=8, run8=9, run9=8, run10=10, run11=6, run12=12,
   run13=10 — with wall-clock from 34 s (run8) to ~280 s (run12), and `0x2AAB8CC1` dumped
   4× in run8 but 0× in run9/run13. **run13 differs from runs 8/9 in more than the patch
   config.**

**And the sharpest single observation of the day:** *the preserved logs contain no spin
evidence at all.* All eight end with the same four SHUTDOWN lines in the same
millisecond. **CLEAN/SPIN were operator annotations layered on from outside the log.**
The entire truth table rests on those annotations — which is exactly what #107's recorder
replaces with a measurement.

### "Budget opened" is probably the wrong predicate

run6 is annotated *"Budget NEVER opened"* yet **does** contain `0x0423278F` dialogs at
(700,531 1000x538) and (900,736 600x127). The dialog present in every SPIN and absent
from run6 is the **900x754** instance (`0x0423278F` at 750,423, children = ordinance-data
ids `0x2F6-0x2FF` strips / `0x12F-0x137` checkboxes / `0x551-0x554` texts). But run7
(patches off) opened it and stayed CLEAN — so at best necessary, not sufficient, and on
single trials even that is weak.

⚠ #107's `budgetSeen` column keys on the budget ROOTS (`0xAA3AC000/001/002`,
`0xCA4C332D`). That is still strictly better than an operator annotation, but if the
900x754 dialog is the real predicate the recorder should capture it too.

## NEXT MEASUREMENT

Repetition is now the bottleneck, and it must not cost the user attention. Build an
**append-only outcome recorder**: one line per launch into a file the logger does *not*
recreate (`SC4UIScale-104.csv` beside the log), carrying timestamp, DLL version, the
patch flags in force, whether Budget was opened, and CLEAN vs SPUN. Ordinary play then
accumulates a **rate per configuration** at zero extra effort, and the bisect can be
re-decided on rates instead of single trials.

Only once a rate exists is it worth re-running the pair comparison — and the hash-map
cycle hypothesis stays **PLAUSIBLE, not confirmed**, until a spin run's stack scan shows
the caller chain.
