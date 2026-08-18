---
name: feedback-sc4-founded-city-invalidates-notes
description: "SC4 UI scaling: every 'hidden/inert/frozen template/do-not-touch' note in the god-mode research was measured BEFORE a city was founded — several of those windows go LIVE in a founded city. Re-verify before trusting; and there is NO founded-city vanilla reference, so run Set-StockCompare FIRST"
metadata:
  node_type: memory
  type: feedback
  originSessionId: f1160943-a698-434b-a6bf-d3c3e2971cea
  modified: 2026-07-29T01:49:36.630Z
---

Two separate "God Mode is broken in a founded city" bugs on 2026-07-28 had the
SAME root cause: a research note that was accurate when written, and false once
a city existed.

- `0xABB26B0E` — noted as "a frozen hidden template at Y1045", so it was put on
  a scale-in-place (never move the root) list. In a founded city it is the live
  god panel; size-only scaling grew its bottom-anchored stock rect (3,1045)
  157x488 downward to y=2021 on a 1600px screen — 421px off the bottom.
- `0x0A78827A` — noted as "a HIDDEN god sub-tool strip … docking/scaling it
  changes nothing on screen. **Do not re-add this id**", so it sat in
  `kGodToolFlyoutIds`, which makes the city sweep skip it entirely. In a founded
  city it IS the god toolbar (Obliterate City / Reconcile Edges / Disaster /
  Day-Night, script I-aa53e3ea) and rendered at dead stock 74x291.

**Why:** all god-flyout work was done pre-founding, where those tools do not
exist and those windows genuinely are inert. Pre-founding and founded-city are
DIFFERENT WINDOW SETS wearing the same mode name.

**How to apply:**
- Treat every "hidden / never visible / inert / template / do not touch" claim
  in the SC4 research docs as *pre-founding only* until re-measured in a founded
  city. A do-not-touch note is not evidence — it is a dated observation.
- Fix for both was identical: remove from the skip lists, add to `kGodPanelIds`
  (scaled BY ID even while reporting vis=0 — these roots report vis=0 while
  their children draw). The standard panel transform
  `y' = f*y - (f-1)*frameH` reproduced the docks recorded back on 2026-07-24
  exactly — (5,1071)→(10,542) and (3,1045)→(6,490), no tuning.
- **`_vanilla-reference/FINDINGS.md` has NO founded-city data** (captured
  pre-founding at 1280x1024). For any founded-city UI question, run
  `_tests\Set-StockCompare.ps1 -Mode Stock` FIRST. One relaunch answered three
  questions at once: god mode is COLLAPSED BY DEFAULT in stock too (not a bug),
  the expand tab works in stock, and the four tool buttons it reveals NAMED the
  responsible window. Guessing from screenshots first produced two wrong
  theories and took far longer.

Related: [[project-sc4-god-flyouts]], [[reference-sc4-flyout-hittest-playbook]],
[[project-sc4-ui-scaling-northstar]], [[feedback-sc4-regression-net]]
