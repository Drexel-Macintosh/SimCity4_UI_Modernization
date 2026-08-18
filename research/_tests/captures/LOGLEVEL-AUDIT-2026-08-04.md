# LogLevel audit verification — 2026-08-04 (v2.71.5)

Handoff task 2 asked for two runs, one at LogLevel=1 and one at LogLevel=2,
with line counts for both.

## The runs

| Run | LogLevel | Total lines | UiSpike lines | Errors | Capture |
|-----|----------|-------------|---------------|--------|---------|
| 1   | 1 (Info) | **94**      | 53            | 0      | SC4UIScale-2026-08-04-L1-verify.log |
| 2   | 2 (Debug)| **473**     | 432           | 0      | SC4UIScale-2026-08-04-L2-verify.log |

Both sessions were the same shape: launch, load city, browse panels/graphs/
Data Views, quit (~1 minute each). Before the audit, a comparable session
ran to 346+ lines at LogLevel=3 and climbed into the thousands once Data
Views strip-digs were involved (the preserved v2.71.4 session
SC4UIScale-2026-08-04-115814.log is 6,018 lines — 776 of them DSTRIP).

## Level 1 — human-readable, PASSES

Every line is one-shot narrative: settings/tier decision, patch installs,
hook installs (SHOWHOOK/SUBBORN2/FLYOPEN/FLYOPEN2/armed/EARLYBAKE),
MINIMAP + DVMAP surface-recreate headlines (with `x8bake=live blits=16
clips=0`), EARLYDOCK summary, ScaleAll begin/end + 504 windows, DFG class
patches, BMPX per-root hook summaries, EARLYCHART install + born-correct
lines (one per graph open), DLGLISTS once-per-session note, first-visible
kick, shutdown. No per-frame instruments, no dumps, no per-tile rows.
Handoff criterion ("If level 1 still runs to thousands of lines for a
normal session, the job is not done") met.

## Level 2 — every instrument back, PASSES

Tags present ONLY at level 2 (i.e. demoted Info->Debug sites, confirmed
firing): CHARTDIAG, CHARTGEO, DCLASS, DLGBORN, FLASHSET, LEGENDCBOX,
MMBUF, MWKID, RCI, RGKID, VWKID (121 RGKID lines = DumpTree's per-window
rows, 69 VWKID). Tags gated at BOTH levels (EBLT, SBLT, RCAL, DBUF,
DSTRIP, GAUGE, SUBGEO, DHOOK) are interaction-gated, not level-gated: the
preserved LogLevel=3 session shows 0 for the same tags except when the
user actively digs the Data Views strip (776 DSTRIP in that session).
Nothing was deleted — the audit reclassified only.

## Note on the L1 capture

The game recreates SC4UIScale.log at every launch, so the level-1 file was
wiped by the level-2 launch before it could be copied. L1-verify.log is a
faithful reconstruction from the captured tool transcript of that run
(same 94 lines); L2-verify.log is a direct copy.

## Aside worth recording

`StripDump=1` is still on in the deployed ini — a leftover diagnostic the
handoff flags. It contributed nothing to these two sessions (no strip was
dug). Candidate for switching back to 0 with user approval.
