---
name: feedback-a-package-is-not-done-until-its-in-the-manifest
description: "THREE SC4UIScale packages have now rotted the same way — hand-placed on the day they were built, never added to Deploy-OnGameClose.ps1 or Test-DatIntegrity.ps1, and silently frozen at that build epoch. #58 ThirdPartyUI, #116 ItemIcons/Sub, #139 NamIcons. A package is finished when it is in the deploy manifest AND the integrity test, not when it builds."
metadata:
  node_type: memory
  type: feedback
  originSessionId: f1160943-a698-434b-a6bf-d3c3e2971cea
  modified: 2026-08-06T04:15:10.400Z
---

# A package is not done when it builds. It is done when it is in the manifest.

Three times now, in three different sessions:

| task | package | how it surfaced |
|---|---|---|
| #58 | ThirdPartyUI | grey radio rows on Building Style Control — the frozen script referenced clone TGIs that had stopped shipping |
| #116 | ItemIcons + ItemIconsSub | a re-deflate pass rebuilt every package; the live icons silently kept the old bytes |
| #139 | NamIcons ×3 | `Build-Dist.ps1` produced a 30-file bundle **with no NamIcons at all**, while the live install had all three tiers |

The shape is identical every time and it is always silent:

    hand-placed once  ->  never refreshed  ->  frozen at that build epoch
                      ->  ships stale, or does not ship

Nothing goes red. The deploy reports success — it just never mentions the file.
`Test-DatIntegrity` passes — it never asserts a file it does not know about.

**Why it keeps happening:** the package gets built and copied in the same
breath as testing it, the test passes, and the session moves on. The copy that
made it work was a *manual* act, and manual acts leave no trace in the two
files that describe what a correct install contains.

**Why: `Deploy-OnGameClose.ps1` is the ONE manifest.** `Build-Dist.ps1` parses
it rather than keeping its own list, precisely so a second hand-maintained
inventory cannot drift. A package outside it is invisible to both the deploy
and the packager.

**How to apply:** when a new package ships, three edits go in the SAME change —

1. `_tests\Deploy-OnGameClose.ps1` — the `Copy-Item` lines (all tiers).
2. `_tests\Test-DatIntegrity.ps1` — a `$BUILT_PAIRS` row per tier, so
   **deployed == built** is asserted by content hash. Sizes and entry counts
   are NOT enough: #58's stale and fresh dats were byte-identical in length.
3. `ScaleTier.cpp` — the `SyncDat` call, if it is tier- or mod-gated.

If you find yourself typing a `Copy-Item` into a terminal to make something
work, that is the signal: the manifest is now wrong, and it will look right.

Related: [[feedback-sc4-regression-net]], [[project-sc4-thirdparty-patches]],
[[feedback-sc4-scaling-laws]] (law 40).
