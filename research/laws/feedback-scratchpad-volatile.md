---
name: scratchpad-volatile
description: NORTHSTAR - the session scratchpad gets wiped without warning; keep NOTHING load-bearing there, and re-evaluate the location whenever something stops being throwaway
metadata: 
  node_type: memory
  type: feedback
  originSessionId: f1160943-a698-434b-a6bf-d3c3e2971cea
  modified: 2026-07-21T13:06:14.978Z
---

**NORTHSTAR, ALL PROJECTS. The scratchpad is DISPOSABLE. Anything left there will eventually
be destroyed with no warning and no backup.**

`...\Temp\claude\<project>\<session>\scratchpad` is NOT safe storage. Observed erasures:
- **2026-07-21**, twice mid-session: once by a subagent whose cleanup `rm` resolved onto the
  real scratchpad through Windows case-insensitive paths, once from the user's parallel
  session. Sibling `tasks\` output files vanished too.
- **Surface Casino**: another Claude Code process's startup cleanup wiped the whole folder,
  destroying roughly **3.5 MILLION assertions** of verification code - every rules suite, the
  adversarial audits that had just found 21 real bugs, the conservation harnesses, the RTP
  oracles, the independent evaluators written to cross-check the engines. The product
  survived because it lived in the project. The evidence did not.

**Why:** multiple Claude sessions run at once, agents get near-identical temp paths differing
only in case, and any cleanup that deletes a DIRECTORY (rather than its own named files) can
nuke another session's workspace. Windows treats those paths as the same.

**How to apply:**

1. **Ask "would I be annoyed to lose this?" every time.** If yes, it is not scratch. Move it
   into the project NOW, not later.

2. **RE-EVALUATE when the value changes.** This is the failure mode that actually bit. The
   first Surface Casino harness genuinely WAS a throwaway probe, so scratch was right. It
   then grew into the project's entire regression net - and the location was never revisited,
   because the same scratchpath kept being pasted into every worker brief mechanically for a
   whole session. **Scratch is a decision, not a default.**

3. **Durable homes, excluded from the build:**
   - test suites and harnesses -> `<Project>\_tests\`
   - reusable tools and gates  -> `<Project>\_packaging\` (Check-VistaSafe.ps1, Audit-Layout.ps1)
   - dev-only material that must not ship -> `_not-for-deployment\`
   - captures/analysis outputs -> the project tree (e.g. `SC4TouchControls\tools\capture\out\`),
     preserved logs as `*.bak-<reason>` beside the live log
   Then CONFIRM they cannot leak into the shipped artifact: check the csproj has no wildcard
   includes and installer globs do not pick them up.

4. **Every subagent prompt involving temp files must say:** clean up ONLY files you created,
   by exact name - NEVER `rm` / `Remove-Item -Recurse` a scratchpad or temp DIRECTORY. And
   tell workers where the DURABLE home is, not just where scratch is.

5. **Assume it can vanish between any two tool calls** - recreate the directory before writing.
   Background-task output under `tasks\` is equally volatile: act on results promptly after
   the completion notification, and copy anything needed later into the project.

6. **Genuinely fine in scratch:** one-shot probes, throwaway diffs, intermediate dumps,
   anything regenerable in seconds from something durable.

**A green build is not evidence, and neither is a passing suite you can no longer run.** The
point of a regression net is the next change - which is exactly when scratch will have been
cleaned.

Related: [[feedback-usb-bundle-self-contained-readmes]],
[[reference-deployment-ready-structure]], [[project-surface-casino]].
