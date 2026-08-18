---
name: feedback-sc4-deploy-on-close
description: "SC4 deploys by WAIT-FOR-CLOSE, never by killing the game — it runs elevated and holds the DLL/dats open. Supersedes the old force-close permission."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: f1160943-a698-434b-a6bf-d3c3e2971cea
  modified: 2026-07-31T01:11:12.126Z
---

**Current standing order (supersedes the 2026-07-25 force-close permission,
which is REVOKED):** SimCity 4 runs **ELEVATED** and holds `SC4UIScale.dll`
and the tier dats open. **Never kill it.** Deploy by waiting for the user to
close the game:

`SC4TouchControls\_tests\Deploy-OnGameClose.ps1` — polls every 5 s, then
copies the DLL + SelectiveArt + DialogStatic for all three tiers and asserts
the DLL size matches. Run it in the background with a window long enough for
a real play session (a 5-minute watcher timed out while the user played 13
minutes).

**Why:** killing an elevated process mid-session throws away the user's
in-game state and the session log we are about to read; the whole verify loop
depends on that log. The old permission existed only to unblock a DLL lock —
the watcher solves the lock without the cost.

**How to apply:** build → start the watcher → tell the user the build is
ready → they close the game when they choose → confirm the deploy line
(`deployed ... at HH:MM:SS`) before claiming anything shipped.

**⚠ `_tests\Test-BootMatrix.ps1` IS NOT A ROUTINE CHECK — it violates the rule
above by design.** It LAUNCHES AND KILLS the game once per matrix entry and
rewrites `SC4GraphicsOptions.ini` (800x600 → 1920x1080 → 1600x1200 →
2400x1600), restoring the native resolution only if it runs to completion. Run
it 2026-07-30 and interrupted it: it left the ini at **800x600** and a game
process running. Never launch it as part of a normal "run the suites" pass, and
never while the user may be playing. **The routine suites are OFFLINE:**
`Test-DatIntegrity`, `Test-ScaleTierDecide`, `Test-UiMapDiff`, and the
`tools\uimap\emu\` drivers — the user's standing reminder is *"you don't need
the game open to run your tests, you have the simulator."* If BootMatrix is
ever interrupted, restore `WindowWidth=2400` / `WindowHeight=1600` immediately.

Related: [[project-sc4-ui-scaling-northstar]], [[feedback-docs-are-the-sdk]],
[[feedback-sc4-regression-net]].
