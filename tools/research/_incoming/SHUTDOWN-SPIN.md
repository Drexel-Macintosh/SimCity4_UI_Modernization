# #104 — SHUTDOWN SPIN: fix brief

**THE MECHANISM IS NOT ESTABLISHED — and as of run15 the CULPRIT PAIR IS REFUTED AS
SUFFICIENT.** No loop has been named. The layout-squeeze mechanism is refuted by
disassembly (three independent passes), and the config premise the whole bisect rested on
is refuted by a measured run: **run15 applied BOTH families, opened the ordinance dialog,
and exited CLEAN.**

**The single cheapest next measurement — one run, ~2 minutes:**

> `OrdinanceInsetPatch=0`, `BudgetDeptPatch=1`, `SpinProbe=10`.
> Open Budget → open **Business Deals** (the 600×127 box) → open **Ordinances** (the
> 900×754 dialog) → quit.
> **If it spins, the ordinance family is exonerated entirely and #104 is a
> BudgetDeptPatch-only bug.** This is the ONLY cell in the 9-run matrix that has never been
> run, and it is the only cell that discriminates the two surviving hypotheses.

**And before that run, do one thing that costs nothing:** copy `SC4UIScale.log` into
`_tests\captures\` **immediately after every capture, before the next launch.** The Logger
opens with `"w"`. The first SPINPROBE capture (run14) found the hot thread — *"46 of 47
threads parked at fixed ntdll/win32u wait addresses and exactly one executing game code"* —
and **that log no longer exists.** All that survives of it is a source comment
(`src\SpinProbe.cpp:24`). We lost the only positive measurement this bug has ever produced.

*Written 2026-08-03, after the runtime-coupling workflow returned and after run15 landed.
Every claim is tagged MEASURED (executed by me or by a named agent) or INFERENCE.*

---

## 0. Status board

| | |
|---|---|
| Spin fixed? | **No.** Nothing in this brief changes game behaviour. |
| Mechanism? | **Unknown.** Layout-squeeze refuted; scoreboard on invented mechanisms today is 0 for 4. |
| "ORDINANCE + DEPT + Budget opened" | **REFUTED as sufficient by run15** (both families, 900×754 opened twice, dept dialog opened, **CLEAN**). |
| Surviving hypothesis | The **600×127 Business-Deals box** must have been displayed *as well as* the 900×754 ordinance dialog. Fits all 9 runs. Untested cell named above. |
| Hot thread | Seen once (run14), **evidence lost to log truncation**. Never re-captured — run15 exited, so there was nothing to sample. |
| Shipping now | Patch A (probe: thread identity), Patch C (comment + clamp logging). Log/comment only. |
| Held | Patch B (the 136→127 re-encode). Gate written and **GREEN**; fixes nothing in #104. |
| New durable artifact | `tools\uimap\emu\gate_ordinance_namex.py` — green first run. |

---

## 1. Mechanism — NOT established

### 1.1 Refuted today, by execution

**MEASURED (three agents independently, `tools\uimap\common.py` + capstone, exe
`1189720d5e15b0e1`):**

* `sub_77C660` (0x0077C660–0x0077D7E0), the Ordinances builder: **1388 instructions, 5
  backward jumps, every one count-bounded** — `0x77C77D` (enumerate, bound = list count),
  `0x77CD5B` / `0x77D273` (row loops, `mov ecx,[esi+0xA0]; inc eax; cmp eax,ecx; jb`, with
  a `cmp eax,9 / jae` visible-row cap), `0x77D41B` / `0x77D599` (string copies). **No loop
  in the ordinance path is geometry-terminated.**
* **`push 0x63` appears ZERO times in the builder.** `align == 0x63` is the *only* branch of
  `sub_779660` that turns an inset into a width (`SetBounds(x, y, parentW − 2·x,
  parentH − y)`). The plan's `remaining = W − leftInset − rightMargin` **has no referent
  here.**
* The builder makes **66 indirect calls, none at a geometry-getter slot**
  (+0xA4/+0xA8/+0xC0/+0xC4/+0xC8/+0xDC). Positive control: the same scanner lists all 66 and
  finds 7 getter calls inside `sub_779660`. The patched x values are **write-once at
  creation, never read back** — such a value cannot become a loop bound.
* Even at the extreme, the arithmetic cannot invert: name column = `W − 203` at 2x with
  both families on, where `W` is art-derived (`template->GetArea()+8` at `0x787C1F`) and
  grows with the factor. There is **no division anywhere** in the ordinance path.
* The three "shared factories" are **not called by the builder.** Its complete direct-callee
  set is `{0x408420, 0x4089B0, 0x4425C0, 0x51CA60, 0x5E55E0, 0x5F9AB0, 0x603580, 0x779660,
  0x77A480, 0x77B7B0, 0x77B960, 0x77BEC0, 0x90CF54, 0x90CF63, 0x9DD1D0, 0x9EEB70,
  0x9F0D10}` — no `sub_7794E0` (slider), no `sub_7798C0` (combo), no `sub_78B120` (shared
  text popup). Positive control: the same closure returns True for `sub_779660`,
  `sub_77B960`, `sub_77BEC0`, two of which are patched. **Scope: direct call edges only**;
  the 66 indirect calls are invisible to it.
* The **136→127 clamp is not the differentiator**: run8 (ordinance-only, CLEAN), run13
  (both, SPIN) and run15 (both, CLEAN) all carry the identical three lines — both clamp
  messages plus `ordinance row insets x2.00 (8 of 8 sites)`.
* `ApplySubFlyoutProviderScale` is **not** the second applier behind `spikeBudgetDeptPatch`.
  Its 3 sites are in `sub_7EAEB0`, whose 7 callers (`0x7EC663`, `0x7EC6C9`, `0x7EC729`,
  `0x7EDDC6`, `0x7F3B8B`, `0x7F3D97`, `0x7F4EE1`) are all flyout code. **The partner is
  `ApplyBudgetFamilyScale`.** *(Split B of the task: answered.)*

### 1.2 What IS positively known

* **MEASURED — the two families rewrite the SAME FUNCTION.** All 8 ordinance sites plus
  **23 budget-family sites** (3 `kDeptImm8Sites`, 2 `kDeptImm32Sites`, 14
  `kBudgetSubImm8Sites`, 4 `kBudgetLeaDisp8Sites`) plus 3 `BudgetButtonPatch` sites live in
  `sub_77C660`. **One builder, three ini flags.** That is the durable structural finding and
  it is what §5.2's gate must catch — independent of #104.
* **MEASURED — at two creation sites the families supply the X and the Y of the same call:**
  ```
  0x0077C994  sub eax, 2      <- BUDGET family    (y)
  0x0077C998  push 0x12       <- ORDINANCE family (x)
  0x0077C9A2  call 0x779660   -> one child window, id 0x0ABCDE01
  ```
  plus the expense twin `0x0077CE3A` / `0x0077CE3E` → `call` at `0x0077CE44`. Two
  independent coordinates of one `SetPosition`, **never one arithmetic expression.**
* **MEASURED — a pair-only runtime state exists at open** (900×754 dialog, from MWKID):
  ```
  ord-only  : checkbox x=36  strip x=68  value texts x=867  left button x=14
  dept-only : checkbox x=18  strip x=34  value texts x=834  left button x=28
  BOTH      : checkbox x=36  strip x=68  value texts x=834  left button x=28
  ```
  **It is not degenerate:** all 2500+ rects across the preserved logs were scanned for
  negative/zero/oversize geometry — **0 anomalous rects in every run**, and the only 0×0
  rects appear in CLEAN runs too. **And run15 shows this exact both-on state exiting
  cleanly**, so this state is not sufficient for the spin.
* **MEASURED once, then LOST — the hot thread is running GAME code.** run14's SPINPROBE
  found 46 of 47 threads parked at fixed ntdll/win32u wait stubs and **exactly one executing
  inside the game image**. The addresses were partly hidden by a top-12 report cap, the log
  was overwritten by run15, and the only surviving record is `src\SpinProbe.cpp:24` and
  `:226`. **This is the single most valuable fact #104 has produced and it must be
  re-captured.** (SpinProbe v2 — `kReportTop=24`, per-thread `gameSamples`, a HOT THREAD
  line, all game-image EIPs printed, plus a stack scan — was written specifically to keep
  that from happening again.)

### 1.3 The shutdown path, so a re-captured EIP reads in seconds

`WinMain` `sub_44C170` → `sub_87B0B9` → **`sub_87AB07` = `cGZFrameWork::Shutdown`**
(framework singleton `[0x00B540AC]`, app `[0x00B540B4]`). Our `PreAppShutdown` returns at
`0x0087AB4B`.

| EIP range | verdict |
|---|---|
| `0x0087AB07`–`0x0087AC20` | `cGZFrameWork::Shutdown` itself (`0x0087AB5F/AB7C/ABA4` = the three service-`Shutdown` bands; `0x0087ABC9` = service-list drain; `0x0087AC02` = Release → `cSC4App` dtor) |
| callee of `0x0087A4B6` / `0x87A527` / `0x87A59F` | **a system service's `Shutdown` is hanging** — the stack scan names it |
| `0x0044A520`–`0x0044A900` | `cSC4App::Shutdown` — its 3 loops are provably bounded, so an EIP here means a callee |
| `0x005051C0`–`0x00505240`, `0x005B9FC0`–`0x005BA010`, `0x005E55B0`, `0x0090CF54/63` | **pool allocator → heap/free-list corruption** (`sub_5051C0` re-reads the size class from `[ptr-1]`) |
| `≥ 0x009E0000` | CRT (`exit()` is called from `0x0087A633`) |
| `0x0077C660`–`0x0077D7E0` | the ordinance builder running **at shutdown** — the surprise ending, and it would instantly explain the dialog prerequisite |

**Why static analysis cannot finish this (structural null, with its control):** the
direct-call closure from all twelve teardown roots reaches **111 functions with 103 backward
jumps — every one a list drain, a `rep`-style CRT loop, or an index-vs-latched-count loop.**
That null is worthless as evidence: the teardown dispatches through service vtables on its
*first hop*, and those same 111 functions contain **176 indirect `call [reg+disp]` sites.**
The instrument could not have seen the loop.

---

## 2. Why the pair — the load-bearing part, and the answer is "it is not the pair"

**MEASURED — every distinct modal root (`MWKID 0 id=0x0423278F`) in all 9 preserved runs.**
This table is the whole argument; it is mechanical `grep` output, not interpretation:

| run | config | **900×754** ordinances | **600×127** biz box | other roots | outcome |
|---|---|:--:|:--:|---|---|
| 6 | full config | — | **yes** | 1000×538 | CLEAN |
| 7 | patches off | yes | — | 300×100 | CLEAN |
| 8 | ordinance only | yes | — | 1000×554, 300×100 | CLEAN |
| 9 | dept only | yes | — | 1000×538, 1000×338 | CLEAN |
| 10 | button only | yes | — | 1000×554, 1000×538 | CLEAN |
| 11 | dept + button | yes | — | 1000×826 | CLEAN |
| 12 | ordinance + button | yes | — | 1000×538, 1000×338 | CLEAN |
| **13** | **ordinance + dept** | **yes** | **yes** | 1000×538 | **SPIN** |
| **15** | **ordinance + dept** | **yes** | **—** | 1000×826 | **CLEAN** |

**Three things fall out, all measured:**

1. **run15 kills the pair as a sufficient condition.** Its `CodePatches:` lines are
   byte-identical to run13's (`ordinance row insets x2.00 (8 of 8 sites)`, `budget family
   x2.00 (54 imm8 + 63 imm32 + 53 sub-imm8 + 17 lea-disp8 + 2 notch sites), bizbox 600x127
   (7 sites)`, both clamp lines), it opened the 900×754 dialog **twice** and a 1000×826
   department dialog — and it exited. *Internal corroboration, independent of the operator's
   CLEAN label:* SpinProbe was armed for **120 s** at 17:27:52.785 and the log contains
   **exactly one** partial report (17:27:53.783) before ending. A surviving process would
   have written ~120. **The process exited about one second after arming.**
2. **run6 was already a warning that went unread.** Its patch set is a strict *superset* of
   run13's (same lines plus `budget buttons 360x60`) and it was CLEAN. The brief recorded it
   as "Budget never opened", but its roots show a 1000×538 Neighbor-Deals dialog and the
   600×127 box — so the thing it actually lacked was **the 900×754 ordinance dialog**, not
   "Budget".
3. **The one condition that separates run13 from all eight CLEAN runs is the
   co-occurrence of the 900×754 ordinance dialog AND the 600×127 box.** No other row has
   both. Note the 600×127 size is produced by **`BudgetDeptPatch`'s bizbox sites** (the
   Business Deals empty box, #63) — 300×100 in runs 7/8 is a *different* dialog, not an
   unscaled version of it (600/2 = 300 but 127/2 ≈ 64, not 100).

**So the honest answer to "why the pair":** *there is no evidence that it is the pair.* The
9 runs are fully explained without the ordinance family playing any causal role at all.

> **H_A (INFERENCE):** the spin needs `BudgetDeptPatch` + the 600×127 box displayed + the
> 900×754 dialog opened. The ordinance family is a passenger.
> **H_B (INFERENCE):** all of H_A *plus* the ordinance family.
>
> **Every one of the 9 runs is consistent with both.** The single run that separates them is
> the one named at the top of this brief: **dept-only, both windows shown.**

**Caveats that bind any reading of that table (MEASURED):** n = 1 per cell; sessions ran
34 s to ~280 s; the interaction was never scripted; MWKID is a change-only dump on a 1–3 s
cadence, so a dialog opened and dismissed inside one interval could be missed (it *did*
print the box in 2 of 9 runs, so it is not blind — but this is not airtight); and CLEAN/SPIN
are operator annotations external to the log for runs 6–13 (run15 is the only one with
internal corroboration). All 8 pre-run15 logs end with the identical four `SHUTDOWN` lines
in the same millisecond — **nothing in the preserved evidence discriminates run13 after
`PreAppShutdown` returns.** Only a re-captured SPINPROBE does.

**One inference is being carried as a measurement and should stop.** Constraint 4 —
"`responding=True`, so it is a worker thread, not the UI thread" — is an inference and
probably false: `Process.Responding` returns **unconditionally `true` when
`MainWindowHandle == 0`**, exactly the state after the window closes. Deleting it re-admits
a **single-threaded spin on the main thread** inside the teardown chain — which is the
natural reading of "the spin starts after `PreAppShutdown` returns", and which run14's "one
thread executing game code" is entirely consistent with. Patch A settles it from inside the
process; the outside control is one line:

```
Get-Process -Id <pid> | Select-Object Responding, MainWindowHandle, Threads
```

---

## 3. The fix

**There is no fix for the spin here, because there is no mechanism.** Three patches follow.
All indentation is **TABS**; match on text, not line numbers. `src\SpinProbe.cpp` is at
**v2** (a parallel session upgraded it after the run14 capture) — these anchors are written
against that live text.

### PATCH A — SHIP NOW. Make SPINPROBE name the thread. (instrument only, no game effect)

v2 already answers *which thread runs game code*. It does **not** answer *is that the main
thread* — the question constraint 4 got wrong. Four small edits.

**A1 — anchor:**
```
	uintptr_t gImgLo = 0;
	uintptr_t gImgHi = 0;

	void InitImageRange()
```
**replacement:**
```
	uintptr_t gImgLo = 0;
	uintptr_t gImgHi = 0;

	// The tid that ARMED us. PreAppShutdown runs on the game's MAIN thread,
	// so this is the UI thread's id, latched before the sampler exists. #104
	// constraint 4 ("message pump alive => a worker thread, not the UI
	// thread") is an INFERENCE from Process.Responding, which returns true
	// unconditionally once MainWindowHandle == 0 - exactly the state after
	// the window closes. The sampler skips only its OWN tid, so the main
	// thread IS sampled: this turns that inference into a measurement.
	volatile DWORD gMainTid = 0;

	void InitImageRange()
```

**A2 — anchor:**
```
				"SPINPROBE %s >>> HOT THREAD tid %u: %u of its %u samples were in the "
				"GAME IMAGE. Every other thread is parked in a wait stub. This is the "
				"thread to explain.",
				tag, hot->tid, hot->gameSamples, hot->samples);
```
**replacement:**
```
				"SPINPROBE %s >>> HOT THREAD tid %u%s: %u of its %u samples were in the "
				"GAME IMAGE. Every other thread is parked in a wait stub. This is the "
				"thread to explain.",
				tag, hot->tid,
				(gMainTid && hot->tid == gMainTid)
					? " [MAIN/UI THREAD - constraint 4 was wrong]" : " [not the main thread]",
				hot->gameSamples, hot->samples);
```

**A3 — anchor:**
```
			"SPINPROBE armed for %ds at %dHz - self-test sweep captured %d "
			"sample(s) from %d thread(s). Sampling begins now; the game's own "
			"teardown is what runs from here.",
			seconds, 1000 / kSampleIntervalMs, first, t.threadCount);
```
**replacement:**
```
			"SPINPROBE armed for %ds at %dHz - self-test sweep captured %d "
			"sample(s) from %d thread(s); arming (MAIN/UI) tid %u. Sampling "
			"begins now; the game's own teardown is what runs from here.",
			seconds, 1000 / kSampleIntervalMs, first, t.threadCount,
			static_cast<unsigned>(gMainTid));
```

**A4 — anchor:**
```
	bool Arm(int seconds)
	{
		if (seconds <= 0) { return false; }
		if (seconds > 120) { seconds = 120; } // hard cap: it is a probe
```
**replacement:**
```
	bool Arm(int seconds)
	{
		if (seconds <= 0) { return false; }
		if (seconds > 120) { seconds = 120; } // hard cap: it is a probe

		// We are on the CALLER's thread here - PreAppShutdown's, i.e. the
		// game's main/UI thread. Latch it BEFORE the sampler exists.
		gMainTid = GetCurrentThreadId();
```

*Values at 1x / 1.5x / 2x / 3x: **not applicable** — Patch A contains no scaled constant. It
is byte-identical at every tier and inert when `SpinProbe = 0`.*

### PATCH B — HELD, DO NOT SHIP YET. The 136→127 re-encode.

**It fixes nothing in #104** — the clamped bytes are identical in run8 (CLEAN), run13 (SPIN)
and run15 (CLEAN). It is a *separate, real, cosmetic* defect that only does material work at
3x.

**Durable round-trip artifact, as required: `tools\uimap\emu\gate_ordinance_namex.py` —
written for this brief, GREEN on first run.** It verifies both stock 43-byte windows against
the shipped exe, tracks ESP through stock *and* replacement, and asserts 43/43 bytes, 10
arguments, identical net ESP (−40) and the same frame slot (+20). **Positive control:** the
tracker must first reproduce *stock's own* spill/reload aliasing, which only holds if the
callee at `[edx+0x1C]` pops nothing — if that model were wrong the gate would go red on the
stock decode. It also reports **84 intra-function branch targets resolved, 0 landing inside
either window.**

Stock bytes (MEASURED, 43 each):
```
income  0x0077CBFC  8b56106a666a556a446805d385ea895424248b106a008bc8ff521c8b4c2428508b8698000000506a445551
expense 0x0077D0B9  8b4e108b106a666a556a446805d385ea894c24246a008bc8ff521c8b4c2428508b869c000000506a445551
```

| f | name-column x | income replacement | expense replacement |
|---|---|---|---|
| 1.0 | 68 (stock) | **NO WRITE** — reduces to stock | **NO WRITE** |
| 1.5 | 102 | **NO WRITE** — imm8 still holds it | **NO WRITE** |
| 2.0 | 136 *(today: 127)* | `8b56106a666a556a446805d385ea895424248b106a0091ff521c50ffb698000000688800000055ff742438` | `8b4e108b106a666a556a446805d385ea894c24246a0091ff521c50ffb69c000000688800000055ff742438` |
| 3.0 | 204 *(today: 127)* | `8b56106a666a556a446805d385ea895424248b106a0091ff521c50ffb69800000068cc00000055ff742438` | `8b4e108b106a666a556a446805d385ea894c24246a0091ff521c50ffb69c00000068cc00000055ff742438` |

The encoding preserves the frame spill `mov [esp+0x24], parent`, swaps `mov ecx,eax` (2
bytes) for `xchg eax,ecx` (1, no flag effects, `eax` dead until the call returns), and folds
two `mov r32,[mem]; push r32` pairs into `push dword [mem]`. Those savings pay for
`push imm32` exactly — no trampoline, no length change.

**Two blockers, both to be discharged before it ships:**

1. **Order dependency / instrument poisoning.** `{ 0x77CC23, 0x44, 0x55 }` and
   `{ 0x77D0E0, 0x44, 0x55 }` lie *inside* the blocks. Block-first → the per-site loop logs
   two `bytes unexpected - skipped` and the health line reads `(6 of 8)` — the exact
   signature that once reported a **real** decline (`0x0077F5B9`, v2.28.2) and the exact line
   #104's bisect used as its no-decline positive control. Per-site-first → the block declines
   and the fix is a **silent no-op**. The two entries **must move out of
   `kOrdinanceInsetSites` and be counted separately**, as `kGraphLegendBlocks` is.
2. **2x is user-confirmed (#61–#69).** Moving 2x from 127 → 136 is a static-only change to a
   confirmed layout — the #98 failure exactly. There is **no 3x eyes-on evidence for this
   dialog anywhere in the captures**. **Recommendation: ship 3x-only, behind eyes-on at 3x,
   leave 2x at 127.** (The "clears the eye by 23 px" figure in our own comment is a
   screenshot claim that cannot be checked offline — the eye's offset lives inside art
   `0x140155B7`, not in the exe.)

### PATCH C — SHIP NOW. Two honesty fixes. (comment + one log line; zero behaviour change)

**C1 — `src\CodePatches.cpp`: correct a comment our own disassembly disproved.** anchor:
```
		// v2.25.28: the ordinance NAME texts are SEPARATE windows (ids
		// 0xABCDE03+k via sub_779660), created at their own x const 68 -
		// the v2.25.27 row move landed the row's eye component on them
		// (MWKID 12:12:09 + screenshot). Stock-coherent 2x is 136 but
		// push-imm8 caps at 127; the clamp still clears the measured eye
		// (ends ~104) by 23px. [chk 36..68][eye ~84..104][name 127+].
```
replacement:
```
		// v2.25.28: the ordinance NAME texts are SEPARATE windows (ids
		// 0xABCDE03+k via sub_779660), created at their own x const 68 -
		// the v2.25.27 row move landed the row's eye component on them
		// (MWKID 12:12:09 + screenshot). Stock-coherent 2x is 136 but
		// push-imm8 caps at 127; the clamp still clears the measured eye
		// (ends ~104) by 23px - a SCREENSHOT claim, not verifiable offline
		// (the eye's offset lives inside art 0x140155B7, not in the exe).
		// [chk 36..68][eye ~84..104][name 127+].
		// 2026-08-03, MEASURED: "SEPARATE" means a separate cIGZWin, NOT a
		// separate parent. arg1 is [esi+0x10] - the DIALOG - the same parent
		// as the checkbox, the strip, the W-38 value column and the 150
		// column. There is no intermediate container, so nothing the budget
		// family moves can "clip" the clamped name: they are siblings in one
		// flat coordinate space. Re-encode candidate + its round-trip gate:
		// tools\uimap\emu\gate_ordinance_namex.py (GREEN). NOT the cause of
		// #104 - these clamped bytes are identical in run8 (CLEAN), run13
		// (SPIN) and run15 (CLEAN).
```

**C2 — `src\CodePatches.cpp`: stop shipping SILENT clamps.** The claim that the ordinance
clamp is "the ONLY place we knowingly ship a value we did not intend" is **false**.
`ApplyBudgetFamilyScale` clamps with **no log line at all**: at f=1.5 *and* f=2.0 it silently
clamps **7 sites** — `0x788D1B`, `0x78916A` (110), `0x787021`, `0x787072` (90), `0x7870DD`
(120), `0x787165`, `0x78724A` (85) — all in the *partner* family, all in user-confirmed 2x
dialogs; at f=3.0, 11 sites plus `0x78B9A1` in the sub-imm8 table. **Every log-based clamp
census we have run was blind to these.**

anchor:
```
			if (v > 127) v = 127; // push imm8 ceiling (slider width at f=2)
```
replacement:
```
			if (v > 127)
			{
				// 2026-08-03: this clamp has shipped SILENTLY since v2.25.29
				// - 7 sites at f=1.5 AND f=2.0, 11 at f=3.0. A clamp census
				// built from the log could not see them. Log it like the
				// ordinance clamp does.
				Logger::Get().WriteLine(
					LogLevel::Info,
					"CodePatches: dept imm8 %ld clamped to 127 at 0x%08X.",
					v, static_cast<uint32_t>(s.site));
				v = 127; // push imm8 ceiling (slider width at f=2)
			}
```

anchor:
```
			if (v > 127) v = 127; // sub imm8 ceiling (f > ~3.3 for 0x26)
```
replacement:
```
			if (v > 127)
			{
				Logger::Get().WriteLine(
					LogLevel::Info,
					"CodePatches: budget sub-imm8 %ld clamped to 127 at 0x%08X.",
					v, static_cast<uint32_t>(s.site));
				v = 127; // sub imm8 ceiling (f > ~3.3 for 0x26)
			}
```

*Values at 1x / 1.5x / 2x / 3x for Patch C: **unchanged at every tier.** C1 is a comment; C2
logs a clamp that already fired. That is the point — it makes existing wrong values visible
instead of changing them.*

---

## 4. The adjudicating probe — pre-committed

**PASS = the process exits (no surviving `SimCity 4.exe`).
FAIL = it survives and burns 84–94 % of one core.**

Deploy with `_tests\Deploy-OnGameClose.ps1` (the game runs elevated and holds the DLL).

**Rule 0, non-negotiable: after EVERY run, copy `SC4UIScale.log` to
`_tests\captures\2026-08-03-104-run<N>-<config>-<CLEAN|SPIN>.log` BEFORE the next launch.**
The Logger opens `"w"`; run14's hot-thread capture was destroyed exactly this way.

**Rule 1: script the interaction and perform it identically in every run.** The 9 existing
runs are not comparable to each other, and that — not the config axis — is what has cost the
most time here.

Script for all runs: `load city → open Budget → open Business Deals (the 600×127 box) →
close it → open Ordinances (the 900×754 dialog) → open one slider department → close all →
quit`.

| # | `[UiSpike]` config | predicted | what it decides |
|---|---|---|---|
| **CONTROL** | `ScaleAll=1, OrdinanceInsetPatch=1, BudgetDeptPatch=1, SpinProbe=10` | **FAIL (spins)** — and the log must show `>>> HOT THREAD` with game-image EIPs | **Run this first.** If it does not spin, the test proves nothing and everything below is void. run15 shows this config CLEAN *without* the box, so the box is now part of the script. Re-run on the OLD build too if any code changed. |
| **DISCRIMINATOR** | `OrdinanceInsetPatch=0, BudgetDeptPatch=1, SpinProbe=10` | **H_A: FAIL. H_B: PASS.** | The never-run cell. FAIL ⇒ the ordinance family is exonerated and #104 becomes a `BudgetDeptPatch`-only bug. |
| **NEGATIVE** | `OrdinanceInsetPatch=1, BudgetDeptPatch=0, SpinProbe=10` | PASS | Confirms the box alone (unscaled) is not enough. |
| **REPEATS** | CONTROL config ×3 | 3× FAIL | n=1 per cell is what let an uncontrolled activity variable masquerade as a config variable for a whole day. |

**Reading the capture (v2 output):**
* `>>> HOT THREAD tid N` + game-image EIPs → read them against §1.3; the stack scan names the
  subsystem. With Patch A the same line says whether N is the **main thread**.
* `>>> NO thread sampled inside the game image` **while the process is still burning CPU** →
  the spin is in a **library**, and #104's framing is wrong. (In run15 that line simply means
  the process exited — an exited process is not a null result.)
* `STRUCTURAL NULL - 0 samples` → **the probe could not see**, not "nothing spun". Fall back
  to `rundll32 comsvcs.dll MiniDump <pid> <path> full`, elevated, while it spins.

**What would make me believe a mechanism:** a hot EIP, in a named function, that changes when
exactly one ini flag changes. Nothing less. Elimination assumes a single culprit, and this
bug has now twice demonstrated that the config it names can be wrong.

---

## 5. The offline gate

### 5.1 Built today: `tools\uimap\emu\gate_ordinance_namex.py` — GREEN

Adjudicates Patch B's *encoding* only: stock bytes, 43/43 length, 10 args, net ESP, frame
slot aliasing, branch targets, no-write at f=1 and f=1.5. **Declared scope:** it proves the
re-encode is *safe to write*. It does not prove the 3x column clears the eye, and it says
nothing about the spin.

### 5.2 Specified, not built: `gate_patch_families_combined.py` (task #106)

**The structural finding this brief exists to record: our byte-patch families are NOT
independent, and `crosscheck.py` verifies every site in ISOLATION.** `sub_77C660` alone is
written by **three ini flags**. Nothing we own tests a combination, so #104 is invisible to
every gate in the repo — and would have been even if the mechanism *had* been the layout
squeeze.

Reuse `crosscheck.parse_codepatches()` (it strips comments before harvesting tables) and
`common.FuncMap`. Assert, non-zero exit on any violation:

1. **Byte-range disjointness across families.** Derive each site's verify- and write-range
   from its *actual encoding width* (2 = `push imm8`, 3 = `sub r32,imm8` / `lea disp8`,
   5 = `push imm32`, block length for a block); fail on any overlap between different ini
   flags. #104 already refuted this as the *cause*, but it is cheap and it is the only thing
   that catches Patch B's ordering trap (§3).
2. **Cross-flag ownership census — the assertion that would have caught this.** Map every
   site to its owning function via `FuncMap`; per function, list the ini flags writing into
   it; **fail any function owned by ≥2 flags** unless it is in a dated, reviewed allowlist.
   First entry: `sub_77C660` — "3 flags: OrdinanceInsetPatch (8), BudgetDeptPatch (23),
   BudgetButtonPatch (3)".
3. **Effect-level pairing.** For each *creation call site* in a patched builder, resolve which
   constants supply its x and its y; **fail any single call whose x and y are owned by
   different flags.** Today that fires on exactly two — `0x0077C9A2` and `0x0077CE44`. A user
   who turns one flag off gets a window positioned half-scaled: a real, shippable, currently
   untested defect class, independent of #104.
4. **Clamp census over the union.** For every imm8-encoded site and every tier
   {1.0, 1.5, 2.0, 3.0}, assert `round(stock*f) <= 127` **or** the site is on a dated CLAMPED
   allowlist **and the applier logs it**. Fires today on 2 ordinance + 7 `kDeptImm8Sites`
   (+4 more and 1 sub-imm8 at 3x) — i.e. it surfaces exactly what Patch C2 exposes.
5. **Reduce-to-stock at f = 1 across ALL flags enabled simultaneously**, not per family.
6. **Positive control, mandatory (`--selftest`):** inject a synthetic overlapping pair and a
   synthetic x/y flag split and assert the gate goes red on both. An unfired guard is
   decoration.

**Declare in the docstring what it still cannot do:** nothing offline can see the runtime
coupling, because the teardown dispatches through 176 indirect vtable edges. A future GREEN
here must never be quoted as "#104 cannot happen again".

---

## 6. What this does NOT fix — explicitly

1. **The shutdown spin.** Unfixed and unexplained. Patch A only makes the next capture
   informative. Interim escape remains `OrdinanceInsetPatch=0` (at the cost of clipped
   ordinance row text) — **but note that running the escape is now the DISCRIMINATOR: if the
   spin survives it, the ordinance family is exonerated outright.**
2. **The lost run14 capture.** The one positive measurement this bug produced is gone.
   Rule 0 in §4 prevents a repeat; it does not restore it.
3. **The 136→127 clamp — a separate, REAL defect.** Cosmetic; materially wrong only at 3x
   (−77 px, where the strip is also 3× wide, so the name almost certainly lands on the
   strip/eye). At 2x the clamp moves the name column *left*, away from the 300 column and
   the W−76 value column: gap 173 px clamped vs 164 px coherent — strictly *more* clearance.
   Held per §3.
4. **The seven silent budget clamps.** C2 makes them visible; it does not correct them.
   Correcting them means re-encoding 9–12 more sites inside user-confirmed 2x dialogs. Own
   ticket.
5. **The uncontrolled activity axis.** n=1 per cell, unscripted interaction, 34 s–280 s
   sessions, change-only dumps. Every conclusion in §2 is a *fit across 9 single trials*.
6. **`crosscheck.py`'s blindness to combinations** — §5.2 is specified, not built (#106).
   Until it exists, every family-level GREEN in this repo means "each site is right on its
   own", nothing more.
7. **The `Responding` artifact.** Patch A settles thread identity; nobody has yet recorded
   `MainWindowHandle` on a spinning process. Until someone does, "the message pump is alive"
   must not be repeated as a measurement.
8. **The comment corpus.** C1 fixes one comment our own disassembly disproved; there are
   others (`src\UiSpike.cpp:3081` was disproved earlier today). Treat every comment as an
   instrument and audit it before quoting it.

---

## Files

* `...\tools\uimap\emu\gate_ordinance_namex.py` — **new, GREEN**, the durable round-trip for Patch B
* `...\src\SpinProbe.cpp` — Patch A anchors (4); v2 comments at `:24` and `:226` are the *only* surviving record of the run14 hot thread
* `...\src\CodePatches.cpp` — Patch C anchors; `kOrdinanceInsetSites`; `ApplyOrdinanceInsetScale`; `ApplyBudgetFamilyScale` (the two silent clamps); `VerifiedWrite`
* `...\src\SC4UIScaleDllDirector.cpp` — arming: `spikeOrdinanceInsetPatch` / `spikeBudgetDeptPatch` / `spikeSpinProbe`
* `...\src\UiSpike.cpp` — MWKID, the change-only dump behind §2's table
* `...\_tests\captures\2026-08-03-104-run{6..13,15}*.log` — every log measurement above; run15 is the one that refutes the pair
* `...\tools\uimap\{common.py, fn.py, crosscheck.py, _work\edges.json, _work\funcs.json}` — all disassembly and call closures

*(Full path prefix: `<PROJECT-ROOT> 1 Project\1 Completed Projects\SC4TouchControls\`)*
