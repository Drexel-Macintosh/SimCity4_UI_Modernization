---
name: feedback-selector-freeze-named-by-instrument
description: "SC4 selector: two inference 'fixes' for the Graphic Options freeze both missed; one in-memory timing instrument named the cause in a single launch (EnumDisplaySettingsW, 3.3s, first enumeration through dgVoodoo's virtualized display). Cure = warm the enumeration at DLL load on a background thread with a tri-state handshake; the instrument stayed in the build."
metadata:
  node_type: memory
  type: feedback
  originSessionId: f1160943-a698-434b-a6bf-d3c3e2971cea
  modified: 2026-08-20T00:00:00.000Z
---

The Graphic Options selector froze the game for seconds on first open. Two
builds shipped inference fixes — a one-way-ratchet fix, then a once-per-
session cache — and the user reported after both: *"It still isn't working /
is still freezing up."* The third build shipped **measurement instead of a
third guess, with no behaviour change at all**, and one launch ended it.

**The instrument, and why it is shaped this way:**
- **In-memory named buckets only.** The leading suspect was file I/O (the
  whole Plugins tree sits under a sync-filtered Documents folder), so the
  instrument must not be made of the thing it measures — no disk writes, no
  log lines in the timed path.
- Brackets around every named bucket (dialog find/open/close, combo work,
  resolution-list build, ini reads/writes, message paths).
- A **frame-gap watchdog** (a >500 ms stride with the dialog up dumps the
  in-gap bucket deltas — a big gap with quiet buckets means the stall is
  OUTSIDE the bracketed code, which is a finding, not a failure) and a
  **pass watchdog** (any single pass >25 ms names its contributors).

**One launch named both defects:**
1. ⭐ **THE FREEZE = `EnumDisplaySettingsW`, 3,264 ms, ONCE.** The pass
   table read `pass took 3266ms. In-pass: sel.buildResList=3264ms/1` — the
   FIRST enumeration through dgVoodoo's virtualized display costs 3.3 s on
   this machine, and the previous build's cache had correctly made it
   once-per-session… **scheduled at the one moment the user is guaranteed to
   be watching: the first click.** Every suspect the theories favoured
   measured INNOCENT in the same table (sync-filter logger: 361 writes =
   7 ms; message path: 13,203 messages = 6 ms; tree walks: 100 = 1.3 ms).
2. ⛔ **"built 0 row(s) for Windowed" — the list builder HAD NO WINDOWED
   BRANCH.** Borderless returned early, Fullscreen had its block, Windowed
   fell through both to the sort with an empty list. The user's screenshot
   of an open-and-empty dropdown was the list being empty AT BIRTH — the
   mid-drop-mutation theory died in one measured line.

**The cure (user direction: "load the resolutions during game startup when
the DLL loads"):** the enumeration state is **tri-state** (idle /
enumerating / done) and a warm thread kicks it in the director constructor,
during plugin scan. The first open finds the cache warm; the UI thread's
only race path is a correctness net that waits. The enumerated-ONCE log line
now carries its own duration, so **the cure is measurable in the same line
that proved the defect** — and the whole instrument stayed in the build
(SELPERF), because a performance guarantee you cannot re-measure is a
memory, not a gate.

**How to apply:**
1. After two inference fixes fail the same symptom, the next build ships an
   instrument, not a third guess — and no behaviour change, so the
   instrument's reading cannot be contaminated by the fix.
2. A once-per-session cost is a **user-visible** cost if it lands on the
   first interaction. Move it to load time, off the UI thread, with a
   handshake the UI thread can wait on as a net, never as the common path.
3. Exonerated suspects are part of the result — publish their numbers beside
   the culprit so the next session does not re-accuse them.
4. Keep the instrument armed after the cure. The line that proved the defect
   is the only line that can prove the cure.

Related: [[feedback-sc4-measure-dont-infer]],
[[feedback-state-machine-derive-diff-commit]],
[[feedback-null-is-not-evidence]]
