# `_incoming\` — raw decode drafts awaiting editorial

15 agent drafts (~430 KB) produced 2026-07-31 by three parallel decode
workflows. **They are RAW: unverified, overlapping, and known to contain
mistakes.** Nothing here is authoritative until it has been checked and moved
into a real doc.

| file | subject |
|---|---|
| `subsystems-01..04` | paint/invalidate pipeline · input routing & hit-testing · the complete `.UI` grammar · transients/dialogs/modality |
| `sdkgaps-01..06` | GZWinBMP class complete · widget catalogue from measurement · region-screen architecture · all art-binding paths · the `census.py` 0xD8 blind spot · the 45 unjudgeable windows |
| `crossfire-01..05` | the task #72 region rating bar, decoded four independent ways + a synthesis |

## Already extracted, verified and applied

- **The vtable slot correction** (header missing a virtual at real 57; slot 88
  is the per-class draw) — independently re-measured, now in
  `SC4-UI-ENGINE.md` §0.
- **The third blit behaviour** (`src-follows-dst`) — now ENGINE §0 + law 35.
- **The `cSC4WinAuraBar` decode** — now `REGRESSION.md` "REGION BUBBLE MAYOR
  RATING BAR"; shipped as v2.37.1.
- **Law 34** (two blind instruments agreeing) — `REGRESSION.md`.

## How to consume the rest — do NOT bulk-paste

The crossfire synthesis found **three of its four angles wrong on at least one
detail** while agreeing on the mechanism, which is the honest baseline for
everything in this folder. Each block must be re-measured before it is
believed; agreement between drafts is not verification (law 34).

Take one block at a time, verify its load-bearing claim yourself, then move it
into the doc its header names and delete it here. A draft that cannot be
verified cheaply belongs in the FAILED-ATTEMPTS or OPEN QUESTIONS list, not in
the reference.
