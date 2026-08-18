# PICKUP — 2026-08-03 session, written before a context compaction

Read this first if you are resuming. It is short on purpose. The long-form briefs are
listed at the bottom.

---

## 1. OPERATIONAL HAZARD — FIX THIS FIRST

**`SC4UIScale.ini` is left MID-BISECT and currently holds the SPINNING combination.**

```
ScaleAll=1  RatingArrowPatch=1  TooltipWrapPatch=1  HtmlSizePatch=1  AdviceRowPatch=1
BudgetDeptPatch=1   OrdinanceInsetPatch=1   BudgetButtonPatch=0
```

`BudgetDeptPatch=1` + `OrdinanceInsetPatch=1` is the pair that makes the game **spin at
~85% of a core after the window closes** (#104). `BudgetButtonPatch=0` also means the
budget Accept/Cancel buttons render wrong.

**DECIDED 2026-08-03 (post-compaction): the user chose LEAVE IT AS-IS.** Do not
restore, do not flip a key, do not re-ask. The bisect combination stays live because no
game launch is planned before the fix lands. **If the game IS launched before then,
expect both defects** — budget Accept/Cancel wrong, and a spinning core after close that
needs End Task.

The two restore paths, kept for when the fix does land:

* **Restore the pre-bisect config** (all patch families ON, i.e. normal shipping state):
  `python <scratchpad>/set_scaleall.py restore` — or copy
  `Documents\SimCity 4\Plugins\SC4UIScale.ini.104-backup` over `SC4UIScale.ini`.
  This restores correct visuals AND the shutdown spin.
* **Or set `OrdinanceInsetPatch=0`** — clean exits, at the cost of the ordinance row
  insets (clipped row text in the Ordinances dialog).

The ini has **no BOM** and must never gain one (the DLL abandons it and boots windowed).

Also: `SC4GraphicsOptions.ini.u1-backup` exists from the 1.5x tier test. The live gfx ini
was already restored to 2400x1600 FullScreen.

---

## 2. THE #104 WORKFLOW — STOPPED, RESTART IT

**STOPPED deliberately before compaction.** Nothing is running. Restart with:

```
Workflow({
  scriptPath: "<HOME>\\.claude\\projects\\<SESSION-DIR>\\f1160943-a698-434b-a6bf-d3c3e2971cea\\workflows\\scripts\\sc4-104-spin-mechanism-wf_4995dc88-f39.js",
  resumeFromRunId: "wf_4995dc88-f39"
})
```

Resume replays any agent whose (prompt, opts) are unchanged from cache — but it was
stopped mid-Mechanism with **0 of 3 agents journaled**, so expect all three to re-run.
Resume is SAME-SESSION only; compaction preserves the session, so this works. If it
fails, just re-invoke with `scriptPath` alone (no resumeFromRunId) — the script file is
self-contained and carries the full brief.

Before resuming, check `journal.jsonl` in
`…\subagents\workflows\wf_4995dc88-f39\` — do not assume cached results are non-empty.

**Everything else is stopped.** `sc4-docs-sweep` (`wf_359f89ae-d96`) and
`sc4-p1p2-parallel-repair` (`wf_7a5334d1-c4a`) both finished ~12:35 and were stopped by
the user; their task ids no longer resolve.

> **INSTRUMENT LESSON, recorded because it burned time twice today.** Neither the
> Background-tasks PANEL nor my journal-watching monitor was authoritative about what was
> live. The panel kept two finished workflows listed as "Running" with a still-incrementing
> wall clock (5h 00m / 4h 54m) hours after they returned; my monitor had earlier flagged a
> deliberately-killed agent as HUNG. **The reliable check is file WRITE TIMES** in
> `…\subagents\workflows\<run>\` — an agent that has written nothing for hours is not
> working. Use that, and corroborate with whether the task id still resolves.

**What it is doing:** finding, offline, why `OrdinanceInsetPatch` + `BudgetDeptPatch`
together cause the shutdown spin, and designing the fix. Three angles:

1. **What the two families share.** Strongest lead: `ApplyOrdinanceInsetScale` runs
   BEFORE `ApplyBudgetFamilyScale` and both use verify-before-write. If one rewrites an
   instruction the other's verify no longer recognises, the second silently DECLINES,
   leaving a **half-patched layout** — a third state distinct from "all on"/"all off",
   which is exactly the shape of a pair-only bug. Site ranges overlap: ordinance
   `0x77C998..0x77D0E0`, budget family `0x0076D3D0..0x00793BA5`.
2. **Which loop spins.** Must satisfy ALL FOUR measured constraints (see §3).
3. **Is the 136→127 clamp load-bearing.** Decisive sub-question: does anything ever READ
   that x back, or is it write-once at creation? If write-once, the clamp cannot cause a
   shutdown spin and that thread is dead.

**A complication the bisect could not split, and the workflow must:**
`settings.spikeBudgetDeptPatch` gates **two** appliers —
`ApplyBudgetFamilyScale` AND `ApplySubFlyoutProviderScale` (the latter only when
`spikeSubFlyoutBorn2x > 0`). The real partner may be either.

**When the result arrives:** do NOT apply a fix that only *fits* the facts. Today's
scoreboard on invented mechanisms is **0 for 2**. Require a positive confirmation, and
require the fix to reduce to stock at f=1 and leave the user-confirmed 2x budget dialogs
(#61–#69) untouched. If it re-encodes an instruction block it must be capstone
round-tripped in a durable artifact — pattern:
`tools\uimap\emu\gate_graphlegend_leftanchor.py`.

---

## 3. #104 — THE BUG, AS MEASURED (13 in-game runs)

Symptom: window closes, **process survives and spins at 84–94% of one core**,
`responding=True` (pump alive → a worker thread, not the UI thread). A deadlock burns no
CPU — that one reading invalidated every hypothesis in the original filing.

Our cleanup is NOT involved. The v2.56.0 probe prints all four stages in the **same
millisecond** and returns: `SHUTDOWN 1/3 … 2/3 … 3/3 … done`.

```
stock (layer off)                    CLEAN     <- so it IS ours
ScaleAll=0 (DLL loaded, no work)     CLEAN     <- subclass/timer/MinHook cleared
all patches off, sweep ON            CLEAN     <- sweep + 17 hooks/vtable copies cleared
full config, Budget NEVER opened     CLEAN     <- the ACTIVITY is required
full config + Budget opened          SPINS     <- first controlled reproduction
Ordinance alone / Dept alone /
  Button alone / Dept+Button /
  Ordinance+Button                   CLEAN
ORDINANCE + DEPT + Budget            SPINS 85% <- CULPRIT PAIR
```

The four constraints any correct mechanism must explain: (1) starts only after
PreAppShutdown returns, (2) needs Budget to have been opened, (3) needs BOTH families,
(4) busy loop with the pump alive.

Preserved logs: `_tests\captures\2026-08-03-104-run6..run13*.log`, each named with its
config and CLEAN/SPIN outcome.

Known anomaly, relevance UNPROVEN: `ordinance inset 136 clamped to 127` at `0x0077CC23`
and `0x0077D0E0` — logged on every 2x boot, the only value we knowingly ship wrong, and
in one of the two interacting families. Suggestive, not established.

---

## 4. WHAT SHIPPED TODAY

* **v2.55.0 — #57 Graphs legend. USER-CONFIRMED "looks fantastic".** The chart does not
  lay out its legend; the PANEL builder `sub_76D3D0` does, from a six-constant
  right-margin budget that never scaled. 8 byte sites patched so the column is born at f.
* **v2.56.0 — #101 dashboard co-anchor + the #104 shutdown probe.** DEPLOYED, hash-verified,
  **NOT yet eyes-on at 1.5x**. Replay-verified as `0 panels move of 39` at 2x.
* **#98 REVERTED** — was never a bug; the runtime already scaled those windows and our
  data-side double landed at 4x.

## 5. CLOSED AS NOT-OURS TODAY (3 for 3 against the "we broke it" instinct)

* **#91** dashboard minimap — stock does it too.
* **#98** Trip Types legend — runtime already scaling; census row was wrong.
* **#103** budget popup X — the game's own dispatch table at `0x78BC28` routes id `0xCC`
  to a branch with no close. Ordinance twin (`0x68`) closes; this one never does, at any
  scale. Also established: **in this engine sprite and hit box are the SAME rect**
  (`SetArea` → `CalcAbsoluteArea` → `[this+0x14]`, which the router reads), so law 43
  can NEVER produce "draws right, doesn't respond".

## 6. OPEN, RANKED

| # | item |
|---|---|
| **104** | culprit pair found; mechanism + fix in flight |
| **101** | shipped, needs 1.5x eyes-on (1400x1050 **Windowed** — fullscreen silently gives tier 2.0) |
| **102** | 2 unreviewed id collisions; gate at exit 1, deliberately unbaselined |
| **98** | reopen only with a screenshot first |
| **99** | `coverage_rederive.py` drops 49 roots |
| **100** | 4x bubble art exists behind `BUBBLE_OVERRIDE_ENABLED=False` |
| **97** | two-knob scaling (UI 1:1 text, separate UDI bubble) |
| **54/75/31/70** | coverage residue, 1.5x rounding, stock-parity passes |

## 7. THE STRUCTURAL FINDING WORTH MORE THAN THE FIX

**Our byte-patch families are NOT independent.** `crosscheck.py` verifies every site in
ISOLATION; nothing anywhere tests families in COMBINATION. #104 is invisible to every
gate we own. Whatever cures it, that gap deserves its own task.

## 8. LONG-FORM BRIEFS FROM TODAY

`tools\research\_incoming\` — `TIER15X-DASHBOARD.md` (#101), `BUDGET-POPUP-X.md` (#103),
`FINAL-3-PERCENT.md`, `MODEC-SESSION.md`, `SHUTDOWN-SPIN.md` (#104, pending).
`tools\research\SCALING-AXES.md` (#97). Oracles/gates:
`tools\uimap\emu\prove_chart_legend.py`, `emu_panel_anchor.py`,
`gate_graphlegend_leftanchor.py`, `_tests\Test-ChartLegendMath.ps1`.
