---
name: project-sc4uiscale-github-publish
description: "✅ PUBLISHED 2026-08-06: github.com/<GH-ACCOUNT>/SC4UIScale (public, 623 files) + Release v2.93.1 with the 82.8 MB installable bundle. Re-publish via _packaging\\EXPORT-PUBLIC.ps1 — an ALLOWLIST export into a fresh dir OUTSIDE OneDrive, then git push from THERE. Never git init in the working tree."
metadata:
  node_type: memory
  type: project
  originSessionId: f1160943-a698-434b-a6bf-d3c3e2971cea
  modified: 2026-08-06T13:43:13.046Z
---

# SC4UIScale on GitHub — LIVE, and the two things that must not happen

## ✅ PUBLISHED 2026-08-06

* **Repo:** <https://github.com/<GH-ACCOUNT>/SC4UIScale> — public, 623
  tracked files, ~9 MB. Account `<GH-ACCOUNT>`, commits authored as
  `88599898+<GH-ACCOUNT>@users.noreply.github.com` (**never the real
  address — GitHub bakes the committer email into history permanently**).
* **Release:** `v2.93.1`, asset `SC4UIScale-v2.93.1.zip`, 82.8 MB, 38 members.
  GitHub's own reported digest matched the locally computed
  `a10ff51a…f6d47a70`, which confirms the uploaded bytes are the ones that were
  scanned.
* Repo name chosen to match the shipped artifacts (`SC4UIScale.dll`,
  `z_SC4UIScale_*.dat`); "SimCity 4 UI Scaler" is the README headline and repo
  description so plain-English search still finds it.

## Re-publishing / updating

```
.\_packaging\EXPORT-PUBLIC.ps1 -PiiToken '<surname>','<handle>'
cd %USERPROFILE%\sc4uiscale-public
git remote add origin https://github.com/<GH-ACCOUNT>/SC4UIScale.git
git add -A && git commit -m "..." && git push
```

`-WhatIfOnly` lists and scans without copying. The exporter **exits 1 and
copies nothing** on any hit. ⚠ The export is a FRESH directory each time —
re-add the remote, or push from a clone instead.

⚠ **Byte-scan every Release asset first**: `python _tests\Test-BinaryPii.py
dist\<bundle>.zip`. A text scan is not enough — see
[[feedback-text-scanners-are-blind-to-binaries]].

## ⛔ Two things that must not happen

**1. Never `git init` in the working tree.** ~988 MB / 30,000 files against
~6.9 MB / 630 published — about **200:1**. A `.gitignore` is a denylist, and
one gap at that ratio puts a leak in the history permanently. Worse,
`tools\research\submenus-dll-src\` holds **memo33's full `.git` clone**, which
an in-place init would embed as a foreign repository. The `.gitignore` ships
anyway as the second line of defence for whatever gets added later — it is not
the thing being trusted.

**2. Never attach a pre-`/PDBALTPATH` binary to a Release.** Everything in
`dist\SC4TouchControls-v1.0.4` / `v1.0.5` and `_working-backup\` embeds the
full build-machine PDB path plus a UTF-16 source path. Those bundles are
**FROZEN** and are not rebuilt or scrubbed. The only public route for a touch
DLL is a fresh build at a bumped version (the vcxproj now carries
`/PDBALTPATH:%_PDB%`), byte-scanned, attached to a Release. Releases are built
artifacts, never tracked files.

## Policy, in one line

**Ship the GENERATOR, never the art.** Nothing derived from the game install
(EA/Maxis) and nothing from other modders (CAM, NAM, warrior, CoriBoom,
cyclone-boom, memo33) is published. A user rebuilds the packages against their
own install.

## Two scrub findings worth remembering

* `tools\privacy_audit.py` **hard-coded the name it was hunting for** — the
  auditor was the leak, and would have shipped in the first commit. Tokens now
  come from `$SC4_PII_TOKENS` or a gitignored `tools\.pii-tokens`, and a run
  with none configured SAYS the by-name rule did not execute.
* `/_reviews/` and ten self-declared THROWAWAY probe scripts were on neither
  the census nor the 54-item worklist. They were caught only by scanning the
  **selected file set** instead of trusting the rules that produced it — which
  is why the exporter now does that on every run.

Related: [[feedback-a-package-is-not-done-until-its-in-the-manifest]],
[[project-sc4-thirdparty-patches]], [[project-sc4-ui-scaling-northstar]],
[[reference-production-version-history]].
