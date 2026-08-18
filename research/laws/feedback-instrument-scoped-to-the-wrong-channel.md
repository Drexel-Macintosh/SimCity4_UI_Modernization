---
name: feedback-instrument-scoped-to-the-wrong-channel
description: "A TRUE null from an instrument watching the wrong CHANNEL — before trusting silence, prove the API in question even routes through the thing you hooked"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: aa142a6f-fa68-43ea-b5e2-aa20527140e0
  modified: 2026-08-12T12:22:28.228Z
---

Silence from an instrument is only evidence about the channel that instrument watches. Before
concluding "the program never asks for X", establish that a request for X would **travel through
the hook at all** — not merely that the hook fires for other traffic.

**Why:** SimCity Deluxe's text fields were dead. Every keyboard instrument was sound — unconditional
log lines, on the same `Log()` channel that was demonstrably emitting other lines in the same run —
and every one measured perfect silence. The silence was TRUE. The game genuinely never called the
keyboard API. It reached text input through a **Marmalade EDK extension fetched at runtime by
hash**, which by construction appears in none of the 278 bound imports, so an import-scoped
instrument could not have seen it under any circumstances. Three diagnoses died against that
correct-but-irrelevant null, and each one cost a build.

The tell was available and I walked past it: the game asked an availability question, got "no", and
branched past the whole feature. **A program doing NOTHING on an input is more often a disabled
feature than a broken handler.** Silence downstream of a capability check tells you about the
check, not the handler.

**How to apply:**
- A null result needs two positive controls, not one: (1) the instrument fires for *some* traffic,
  and (2) the traffic you are hunting **would use this channel**. The second is the one that gets
  skipped. See [[feedback-null-is-not-evidence]] and [[feedback-blind-instruments-agreeing]].
- When a feature is inert rather than wrong, look for the **guard**, not the implementation: find
  what the code asks before doing the work, and check what we answer. Grep the binary for the
  feature's error strings — `"error loading extension: <name>"` named the whole mechanism and sat
  next to the hash in the same literal pool.
- Enumerate a boundary's SIDE CHANNELS once, up front: dynamic/plugin/extension dispatch, function
  tables, vtables, hash lookups, `dlsym`. An import list is one channel among several, and a
  hand-written inventory of what exists fails silently in exactly the case you needed
  ([[reference-sc4-intro-dat-is-the-eighth-archive]]).
- Related: [[feedback-text-scanners-are-blind-to-binaries]] — same family, different blind spot.
  Details of this instance in [[project-simcity-deluxe-apk-64bit]].
