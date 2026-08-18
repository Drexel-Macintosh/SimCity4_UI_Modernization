---
name: project-sc4-projects-split-and-entry-point
description: "SC4UIScale and SC4Touch are now SEPARATE folders sharing zero files (split 2026-08-06). START-HERE.md is the project entry point, not HANDOFF.md. Publishing goes through _packaging\\Build-PublicRepo.ps1 (explicit manifest) gated by Test-NoForeignContent.py. The working folder is still misnamed SC4TouchControls."
metadata:
  node_type: memory
  type: project
  originSessionId: f1160943-a698-434b-a6bf-d3c3e2971cea
  modified: 2026-08-06T14:31:14.707Z
---

# Two projects, two folders, nothing shared

```
1 Completed Projects\
   SC4UIScale\   <- the UI scaler (renamed from SC4TouchControls 2026-08-06)
   SC4Touch\     <- touch plugin + both frozen dist bundles
```

Split **2026-08-06** after the shared tree repeatedly leaked touch and
Microsoft-Surface content into SC4UIScale's public release — including a README
paragraph about a Surface table, and `[TouchControls]`/`[Gestures]` config the
UI scaler parsed and never used. Touch got its own copies of `Logger`,
`Settings` and `ScaleRemap`; the touch settings were deleted from SC4UIScale
outright. **SC4Touch will not build as-is — that is intentional**, it is slated
for a rewrite independent of UI scaling.

✅ **The rename is DONE** (2026-08-06). Nothing broke: all 10 offline gates,
`Test-DatIntegrity`, `Test-ThirdPartyGates`, a full MSBuild rebuild and the
public-tree build all pass from the new path, because every script resolves its
paths at run time rather than hard-coding them.

⚠ It failed from inside this session with `Access to the path ... is denied`,
three retries, no process holding it by path — OneDrive was syncing the tree.
**The user ran the identical command from their own shell and it worked
first time.** If a rename ever refuses again, that is the fix: hand it over
rather than force-closing their sync.

## Entry point

**`START-HERE.md`** — what the project is, where things are, the first
commands, which document answers which question, the standing rules, and the
current open list. Written to be the *only* thing a fresh instance needs to
find. It replaced `HANDOFF.md`, whose 2,691-line session diary is now in
`_archive\`.

`_archive\` holds process records (old handoffs, one-off reviews, executed
plans). **History, not instructions** — its own README says so.

## Publishing

* `_packaging\Build-PublicRepo.ps1` — an **explicit manifest**, every path
  named. It replaced an allowlist *filter*, which is how 623 internal files got
  published: they passed a privacy audit, so they shipped. **Passing a privacy
  audit is not an argument for inclusion** — "safe to publish" and "belongs in
  a release" are different questions.
* `_packaging\Test-NoForeignContent.py <tree>` — proves no other project's
  content is present. HARD patterns (names that can only mean another project)
  fail the run; SOFT ones (the word "untouched", a DirectDraw "surface") are
  reported for one human read, because a checker that cries wolf gets ignored —
  which is exactly how the real hits survived three hand-checks.
* Curated tree: **388 files / 2.6 MB** — 52 ours, 336 vendored SDK.

Related: [[project-sc4uiscale-github-publish]],
[[feedback-text-scanners-are-blind-to-binaries]],
[[feedback-a-package-is-not-done-until-its-in-the-manifest]].
