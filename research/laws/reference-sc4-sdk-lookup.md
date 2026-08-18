---
name: reference-sc4-sdk-lookup
description: "SC4 findings are queryable, not just prose — run `python tools\\sdk\\lookup.py <id|tgi|script>` FIRST for any window/art/script question; it answers from LIVE sources and refuses to quote the frozen _HANDOFF-* doc snapshots (which are verified stale)."
metadata: 
  node_type: memory
  type: reference
  originSessionId: f1160943-a698-434b-a6bf-d3c3e2971cea
  modified: 2026-08-01T00:59:41.979Z
---

**Built 2026-07-31 in answer to "can we treat our findings more like an SDK".**
The prose was right but slow and rot-prone: four wrong theories shipped in one
day because notes were older than the code they described.

```
python tools\sdk\lookup.py 0xAA8DEF97      window id
python tools\sdk\lookup.py 46a006a6        art instance
python tools\sdk\lookup.py ca8cbf0f        .UI script instance
python tools\sdk\lookup.py 0x0079AD00      code VA
```

Five sections, all GENERATED from live sources, nothing hand-maintained:
1. **our source** — which `k*Ids` list claims it + the surrounding comment
2. **.UI corpus** — which script declares it (with its 1x design size + class)
   or references it as art
3. **what we ship** — staged copies at every tier, with sizes (it also folds in
   the DECLARING SCRIPT's instance, because staged files are named by script,
   not window id — omitting that produced a false "we stage nothing" on the
   very first run)
4. **load order** — the `who_owns_tgi.py` command that names the winner
5. **what we already wrote** — every hit with file:line

**Two design rules that make it trustworthy:**
- **It excludes `_HANDOFF-SimCity4-Complete\`, `dist\`, `_working-backup\`,
  `superseded\`** — frozen snapshots holding July 21-24 copies of live docs
  (the bundled `GOD-MODE-FLYOUTS.md` still calls Create Disaster "UNSOLVED").
  Those folders now carry `_STALE-SNAPSHOT-DO-NOT-READ.md`. A lookup tool that
  reads stale prose just launders it.
- **It labels `_incoming\` / `_checkpoints\` as RAW AGENT OUTPUT** — leads, not
  evidence — rather than hiding them.
- **The file contains no FACTS, only how to find facts**, so it cannot rot the
  way the prose did.

Wired in as step 0 of `TRIAGE.md` and `METHOD.md`, and the first line of
`HANDOFF.md`. Related: [[feedback-check-our-previous-work-first]],
[[feedback-sc4-scaling-laws]] (laws 20/22: the older the note, the more
confidently wrong), [[feedback-docs-are-the-sdk]].
