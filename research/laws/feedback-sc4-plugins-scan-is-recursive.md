---
name: feedback-sc4-plugins-scan-is-recursive
description: "SC4 scans Plugins RECURSIVELY. Moving plugins into a SUBFOLDER of Plugins (e.g. Plugins\\_stock-stash) disables NOTHING - they keep loading. Only an extension rename or a move OUT of the Plugins tree disables a plugin. Cost: an entire stock-baseline investigation plus a full game reinstall, on a premise that was false."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: f1160943-a698-434b-a6bf-d3c3e2971cea
  modified: 2026-08-05T19:20:54.797Z
---

**SC4 loads `Plugins\` RECURSIVELY — every subfolder, at any depth.**

So a "stash" folder *inside* `Plugins\` disables absolutely nothing. There are
only two real ways to take a plugin out of play:

1. **Rename the extension** (`foo.dat` -> `foo.dat.x1-disabled`), or
2. **Move it OUT of the Plugins tree** — a *sibling* of `Plugins`, e.g.
   `Documents\SimCity 4\_stock-stash\`, never a child.

**Why:** on 2026-08-05 `_tests\Set-StockPlugins.ps1` shipped with
`$Stash = Join-Path $DocPlugins "_stock-stash"`. It moved 132 `.dat` (98 MB),
30 `.dll`, and the SC4Lot/Model/Desc content into `Plugins\_stock-stash\` and
reported the game "stock". **All of it kept loading**, through an entire
stock-baseline investigation *and* through a fresh game reinstall — the user
saw plugin fingerprints on screen and said so repeatedly while I argued the
folder was empty. They were right every time.

This is the same failure class as the `zzz-` subfolder gap found 2026-08-02
([[feedback-sc4-scaling-laws]] law 40's corollary) — one directory further out.
It is now the second time the SAME mistake shape has cost a session.

**How to apply:**
* Before believing ANY "stock"/"plugins removed" claim, run the positive
  control: enumerate `.dat/.dll/.sc4*` **recursively** under BOTH Plugins trees
  (`Documents\SimCity 4\Plugins` and `<install>\Plugins`) and require the list
  to be empty. A top-level `Get-ChildItem` is not that check.
* Third-party DLL **logs are the execution proof** — a fresh
  `SC4MoreBuildingStyles.log` / `SC4LuaExtensions.log` timestamp means the DLL
  ran, whatever the folder layout suggests ([[feedback-sc4-scaling-laws]] law 54,
  law 47 installed != executed).
* A user reporting "I can still see plugins" is a MEASUREMENT. Treat it as
  outranking my own folder listing — see [[feedback-check-our-previous-work-first]]
  and [[feedback-null-is-not-evidence]]: my listing found nothing because it
  was looking one level too shallow, which is exactly a probe that could not
  have seen the thing.
* Stock captures taken before 2026-08-05 are ALL suspect — the plugins were
  live. That compounds the third-`FontStyle.ini` contamination already recorded
  in `_tests\REGRESSION.md`.

Related: [[project-sc4-ui-scaling-northstar]], [[reference-sc4-golden-backup]]
(its THREE FontStyle.ini probe sites are the same "one more place than you
think" trap).
