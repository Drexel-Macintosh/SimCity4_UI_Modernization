# The Display-Enumeration Freeze

Opening the Graphic Options selector for the first time in a session stalls the
game for roughly three seconds. The cause is a single call: the first
`EnumDisplaySettingsW` enumeration performed through dgVoodoo's virtualized
display device costs about 3.3 seconds. Subsequent enumerations are effectively
free, so a naive cache appears to fix the problem — it does not. It merely
schedules the one expensive call at the first click, which is the moment a
player is guaranteed to be looking at the screen. A once-per-session cost is a
user-visible cost whenever it lands on the first interaction.

## The cure: warm enumeration at DLL load

The enumeration state is tri-state — idle, enumerating, done — and a background
thread kicks it from the director constructor, while the plugin scan is already
running. By the time the selector is first opened the cache is warm and the
dialog builds instantly. The UI thread's wait-for-done path exists only as a
correctness net for the case where the dialog is opened before the warm thread
finishes; it is never the common path.

The "enumerated once" log line carries its own measured duration, so the same
line that proved the defect also proves the cure on every launch. The timing
instrument (`SELPERF`) stays compiled into the shipping build for the same
reason: a performance guarantee that cannot be re-measured is a memory, not a
gate.

## The instrument

Two inference-driven fixes — a one-way ratchet, then a once-per-session cache —
both failed to move the symptom. The build that resolved it changed no behaviour
at all and shipped measurement instead, so the reading could not be contaminated
by a simultaneous fix.

Design constraints that made it usable:

- **In-memory named buckets only.** The leading suspect was file I/O, so the
  instrument must not be built out of the thing it is measuring: no disk writes
  and no log lines inside any timed path. Results are dumped after the fact.
- **Brackets around every named bucket**: dialog find/open/close, combo box
  work, resolution-list build, ini reads and writes, and message dispatch paths.
- **A frame-gap watchdog.** A frame stride longer than 500 ms while the dialog
  is up dumps the bucket deltas accumulated inside that gap. A large gap with
  quiet buckets is itself a finding — it proves the stall is outside the
  bracketed code — not an instrument failure.
- **A pass watchdog.** Any single pass exceeding 25 ms prints its contributors.

One launch produced the pass table `pass took 3266ms. In-pass:
sel.buildResList=3264ms/1`, naming the culprit and its call count together.
Every suspect the standing theories favoured measured innocent in the same
table, and those numbers are worth recording so they are not re-accused later:
the log writer under a sync-filtered folder did 361 writes in 7 ms, the message
path handled 13,203 messages in 6 ms, and the tree walks ran 100 times in
1.3 ms.

## The empty resolution list

The same table exposed a second, unrelated defect: `built 0 row(s) for
Windowed`. The list builder had no Windowed branch at all. Borderless returned
early, Fullscreen had its own block, and Windowed fell through both straight to
the sort with an empty list. A dropdown that appears empty when opened is
ambiguous between "empty at birth" and "mutated while open"; the count-at-build
line settled it in one measured number.

## Applying this

1. After two inference fixes fail against the same symptom, the next build ships
   an instrument rather than a third guess, and ships it with no behaviour
   change so the reading stands on its own.
2. Move a once-per-session cost to load time, onto a background thread, with a
   handshake the UI thread can wait on as a net rather than as its normal path.
3. Publish the exonerated suspects' numbers next to the culprit's; an
   exoneration is part of the result.
4. Leave the instrument armed after the cure lands. The line that proved the
   defect is the only line that can prove the cure still holds.
